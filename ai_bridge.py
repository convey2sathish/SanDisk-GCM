"""
ai_bridge.py - Optional Claude enhancement for alert explanations and grounded Q&A.

The deterministic rules engine (alert_explainer.py) is always the source of truth for
numbers, dates, scope and cost. When an Anthropic API key is configured and AI is enabled
in settings, this module asks Claude to improve the *narrative* fields of the explanation
and to answer follow-up questions grounded on the alert facts.

Guarantees:
  * never raises to the caller - every public function returns None on any failure and
    records the reason in `last_error` (visible through status() / /api/ai/status)
  * never logs or returns the API key
  * 60 s client timeout, one retry, refusal stop_reason handled
  * results cached in memory and persisted to DATA_DIR/explanations_cache.json
"""
import datetime as _dt
import hashlib
import json
import re
import threading

import config

try:  # optional dependency (contract §1)
    import anthropic  # noqa: F401
    _SDK_AVAILABLE = True
    _SDK_VERSION = getattr(anthropic, "__version__", "unknown")
except Exception:  # pragma: no cover - SDK missing in some builds
    anthropic = None
    _SDK_AVAILABLE = False
    _SDK_VERSION = None

PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-opus-5"
ALLOWED_MODELS = ("claude-opus-5", "claude-sonnet-5", "claude-fable-5-1")
BETAS = ["server-side-fallback-2026-07-01"]
TIMEOUT_S = 60.0
CACHE_FILE = "explanations_cache.json"

# Narrative keys Claude may improve; everything else always comes from the rules engine.
NARRATIVE_STR_KEYS = ("headline", "one_liner", "analogy", "decision")
NARRATIVE_LIST_KEYS = ("what_changed", "why_it_matters", "risk_if_ignored", "suggested_questions")

_lock = threading.RLock()
_state = {"last_error": None, "last_call_at": None, "calls": 0}
_cache = None  # loaded lazily


# --------------------------------------------------------------------------- settings / status
def _settings():
    try:
        return config.load_settings()
    except Exception:
        return dict(config.DEFAULT_SETTINGS)


def _model():
    m = str(_settings().get("ai_model") or DEFAULT_MODEL).strip()
    return m if m in ALLOWED_MODELS else DEFAULT_MODEL


def is_configured():
    try:
        return bool(config.get_anthropic_api_key())
    except Exception:
        return False


def is_enabled():
    return bool(_settings().get("ai_enabled", True))


def is_active():
    return _SDK_AVAILABLE and is_enabled() and is_configured()


def status():
    return {
        "enabled": is_enabled(),
        "configured": is_configured(),
        "model": _model(),
        "provider": PROVIDER,
        "sdk_available": _SDK_AVAILABLE,
        "sdk_version": _SDK_VERSION,
        "active": is_active(),
        "last_error": _state["last_error"],
        "last_call_at": _state["last_call_at"],
        "calls": _state["calls"],
        "engine": _model() if is_active() else "rules",
    }


def _set_error(msg):
    with _lock:
        _state["last_error"] = str(msg)[:400] if msg else None


# --------------------------------------------------------------------------- cache
def _load_cache():
    global _cache
    with _lock:
        if _cache is None:
            data = config.read_json(config.data_path(CACHE_FILE), {})
            _cache = data if isinstance(data, dict) else {}
        return _cache


def _save_cache():
    with _lock:
        try:
            cache = _load_cache()
            # keep the file bounded: newest 200 entries
            if len(cache) > 200:
                items = sorted(cache.items(), key=lambda kv: kv[1].get("cached_at", ""), reverse=True)[:200]
                cache.clear()
                cache.update(dict(items))
            config.atomic_write_json(config.data_path(CACHE_FILE), cache)
        except Exception as e:  # cache is best-effort
            _set_error(f"cache write failed: {e}")


def _alert_hash(alert):
    raw = json.dumps(alert, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()


def cache_key(alert, audience):
    return f"{alert.get('id')}|{audience}|{_alert_hash(alert)}|{_model()}"


def cached_explanation(alert, audience):
    entry = _load_cache().get(cache_key(alert, audience))
    return dict(entry["explanation"]) if entry and isinstance(entry.get("explanation"), dict) else None


def clear_cache(alert_id=None):
    with _lock:
        cache = _load_cache()
        if alert_id is None:
            cache.clear()
        else:
            for k in [k for k in cache if k.startswith(f"{alert_id}|")]:
                cache.pop(k, None)
        _save_cache()


# --------------------------------------------------------------------------- Claude call
def _client():
    key = config.get_anthropic_api_key()
    if not key:
        raise RuntimeError("No Anthropic API key configured")
    return anthropic.Anthropic(api_key=key, timeout=TIMEOUT_S, max_retries=1)


def _call(system, user_content, max_tokens=6000):
    """One Messages API call. Returns response text or None (error recorded)."""
    if not _SDK_AVAILABLE:
        _set_error("anthropic SDK not installed")
        return None
    try:
        client = _client()
        response = client.beta.messages.create(
            model=_model(),
            max_tokens=max_tokens,
            betas=BETAS,
            fallbacks="default",
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        with _lock:
            _state["calls"] += 1
            _state["last_call_at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if getattr(response, "stop_reason", None) == "refusal":
            details = getattr(response, "stop_details", None)
            _set_error(f"model declined the request ({getattr(details, 'category', None) or 'refusal'})")
            return None
        text = "".join(getattr(b, "text", "") for b in (response.content or []) if getattr(b, "type", "") == "text")
        if not text.strip():
            _set_error("empty response from model")
            return None
        if getattr(response, "stop_reason", None) == "max_tokens":
            _set_error("response truncated (max_tokens) - using rules result")
            return None
        _set_error(None)
        return text
    except Exception as e:  # network, auth, rate limit, bad request ... all degrade to rules
        name = type(e).__name__
        msg = str(e)
        msg = re.sub(r"sk-ant-[A-Za-z0-9_\-]+", "sk-ant-…", msg)  # never leak a key
        _set_error(f"{name}: {msg[:300]}")
        return None


def _parse_json(text):
    """Defensive JSON extraction: strips code fences and leading prose."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.I)
    t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except ValueError:
        pass
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(t[start:end + 1])
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------- prompts
EXPLAIN_SYSTEM = (
    "You are a senior regulatory compliance expert for flash-memory and solid-state storage products "
    "(SD/microSD cards, USB drives, portable and desktop SSDs, NVMe/enterprise SSDs, card readers) sold worldwide. "
    "You rewrite a deterministic, rules-based explanation of a regulatory alert so that it reads naturally for the requested audience, "
    "while staying strictly grounded in the alert facts and the rules result you are given.\n\n"
    "Rules:\n"
    "- Return ONLY one JSON object, no prose, no code fences.\n"
    "- Improve wording, structure and insight of the narrative fields. Do not invent facts, dates, fine amounts, URLs, clause numbers or product names that are not in the material.\n"
    "- Keep every number, date, cost and product/market list exactly as given by the rules result; you may quote them.\n"
    "- Audience 'simple': short sentences, every acronym expanded on first use, one concrete analogy in 'analogy'.\n"
    "- Audience 'executive': decision-oriented - what, so what, now what, money, dates, owner; include a one-sentence 'decision'.\n"
    "- Audience 'engineer': clause-level detail from technical_impact, standard editions, test set-ups, sample counts where present.\n"
    "- If something is unknown or not in the material, say so plainly rather than guessing."
)

QA_SYSTEM = (
    "You are a senior regulatory compliance expert for flash-memory and solid-state storage products. Answer the user's question "
    "using ONLY the alert facts and the rules-based explanation provided. Be concise and practical (max ~180 words). "
    "If the material does not contain the answer, say clearly that it is not covered in the alert and suggest what evidence to obtain. "
    "Never invent fine amounts, dates, URLs or clause numbers.\n"
    "Return ONLY a JSON object: {\"answer\": string, \"cited_clauses\": [string], \"action_advice\": string}."
)


def _slim_alert(alert):
    keep = ("id", "title", "region", "country", "country_code", "standard", "severity", "effective_date", "affected_categories",
            "summary", "action_required", "status", "source", "detailed_summary", "technical_impact", "timeline_milestones",
            "official_links", "compliance_checklist", "pillar", "source_url")
    return {k: alert.get(k) for k in keep if alert.get(k) not in (None, "", [], {})}


# --------------------------------------------------------------------------- public API
def enhance_explanation(alert, rules_explanation, audience="simple", use_cache=True):
    """Return an AI-enhanced copy of rules_explanation, or None (caller keeps the rules result)."""
    if not is_active() or not isinstance(rules_explanation, dict):
        return None
    if use_cache:
        hit = cached_explanation(alert, audience)
        if hit:
            hit["cache_hit"] = True
            return hit
    payload = {
        "audience": audience,
        "alert": _slim_alert(alert),
        "rules_explanation": {k: v for k, v in rules_explanation.items() if k not in ("jargon_glossary",)},
        "glossary_terms_present": [g.get("term") for g in rules_explanation.get("jargon_glossary", [])],
        "instructions": (
            "Return a JSON object with these keys only: headline (<=20 words), one_liner, what_changed (list of 2-5 strings), "
            "why_it_matters (list of 2-4 strings), what_to_do (list with the SAME length and order as the rules list; for each item "
            "you may improve 'step' and 'detail' only), risk_if_ignored (list), suggested_questions (list of 4-6), "
            "jargon_glossary (list of {term, meaning}; only terms from glossary_terms_present, meanings improved for the audience)"
            + (", analogy (string)" if audience == "simple" else "")
            + (", decision (string)" if audience == "executive" else "") + "."
        ),
    }
    text = _call(EXPLAIN_SYSTEM, json.dumps(payload, ensure_ascii=False, default=str), max_tokens=6000)
    data = _parse_json(text) if text else None
    if not isinstance(data, dict):
        if text:
            _set_error("model returned non-JSON content - using rules result")
        return None
    merged = _merge(rules_explanation, data)
    merged["generated_by"] = _model()
    merged["generated_at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    merged["ai_note"] = "Narrative refined by Claude; scope, dates, costs and deadlines from the GCM rules engine."
    conf = dict(merged.get("confidence") or {})
    conf["basis"] = (conf.get("basis") or "") + " Narrative refined by Claude on the same facts."
    merged["confidence"] = conf
    with _lock:
        _load_cache()[cache_key(alert, audience)] = {"cached_at": merged["generated_at"], "explanation": merged}
    _save_cache()
    return merged


def _clean_str(v, max_len=2000):
    return str(v).strip()[:max_len] if isinstance(v, (str, int, float)) and str(v).strip() else None


def _clean_list(v, max_items=10, max_len=1200):
    if not isinstance(v, list):
        return None
    out = [_clean_str(x, max_len) for x in v]
    out = [x for x in out if x]
    return out[:max_items] or None


def _merge(rules, ai):
    merged = dict(rules)
    for k in NARRATIVE_STR_KEYS:
        v = _clean_str(ai.get(k), 600)
        if v and (k in rules or k in ("analogy", "decision")):
            if k == "headline" and len(v.split()) > 22:
                continue
            merged[k] = v
    for k in NARRATIVE_LIST_KEYS:
        v = _clean_list(ai.get(k))
        if v:
            merged[k] = v
    steps = ai.get("what_to_do")
    if isinstance(steps, list) and len(steps) == len(rules.get("what_to_do", [])):
        new_steps = []
        for orig, upd in zip(rules["what_to_do"], steps):
            s = dict(orig)
            if isinstance(upd, dict):
                st = _clean_str(upd.get("step"), 160)
                dt = _clean_str(upd.get("detail"), 900)
                if st:
                    s["step"] = st
                if dt:
                    s["detail"] = dt
            new_steps.append(s)
        merged["what_to_do"] = new_steps
    gl = ai.get("jargon_glossary")
    if isinstance(gl, list):
        allowed = {g.get("term"): g for g in rules.get("jargon_glossary", [])}
        new_gl = []
        for g in gl:
            if isinstance(g, dict) and g.get("term") in allowed:
                meaning = _clean_str(g.get("meaning"), 600)
                new_gl.append({"term": g["term"], "meaning": meaning or allowed[g["term"]].get("meaning")})
        if new_gl:
            seen = {g["term"] for g in new_gl}
            new_gl += [g for t, g in allowed.items() if t not in seen]
            merged["jargon_glossary"] = new_gl
    return merged


def answer_question(alert, explanation, question, history=None):
    """Grounded Q&A. Returns {answer, cited_clauses, action_advice, generated_by} or None."""
    if not is_active():
        return None
    q = str(question or "").strip()
    if not q:
        return None
    hist = []
    for h in (history or [])[-6:]:
        if isinstance(h, dict) and h.get("role") in ("user", "assistant") and h.get("content"):
            hist.append({"role": h["role"], "content": str(h["content"])[:1500]})
    slim_expl = {k: v for k, v in (explanation or {}).items()
                 if k in ("headline", "one_liner", "what_changed", "why_it_matters", "what_to_do", "deadlines", "cost_effort_estimate",
                          "risk_if_ignored", "who_is_affected", "sources", "confidence")}
    payload = {"alert": _slim_alert(alert), "rules_explanation": slim_expl, "conversation_so_far": hist, "question": q}
    text = _call(QA_SYSTEM, json.dumps(payload, ensure_ascii=False, default=str), max_tokens=1500)
    if not text:
        return None
    data = _parse_json(text)
    if not isinstance(data, dict):
        # tolerate a plain-text answer
        return {"answer": text.strip()[:3000], "cited_clauses": [], "action_advice": "", "generated_by": _model()}
    answer = _clean_str(data.get("answer"), 3000)
    if not answer:
        return None
    return {
        "answer": answer,
        "cited_clauses": _clean_list(data.get("cited_clauses"), 8, 300) or [],
        "action_advice": _clean_str(data.get("action_advice"), 800) or "",
        "generated_by": _model(),
    }
