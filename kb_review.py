"""
kb_review.py - Human-controlled knowledge-base review: overrides, verification, review queue, audit trail.

Design rules
  * The shipped seed (countries_data.json, kb_sources.json) is read-only. Every human decision is stored
    in config.DATA_DIR and applied on top of the in-memory db.COUNTRIES_DB.
  * Pre-filled source links are AUTHORITY PORTALS (starting points), never citations of a specific rule.
    A pillar is "Verified" only when a human reviewer records it together with a citation URL.
  * Reviewer identity is a self-declared name (settings.reviewer_name). There are no logins in this
    single-user tool, so the audit trail proves *what* was decided and that it was not altered, not *who*.

Files (DATA_DIR): kb_overrides.json, kb_verification.json, review_queue.json, audit_trail.json
Shipped (bundle): kb_sources.json
"""
import datetime as _dt
import hashlib
import json
import re
import threading
import uuid

import config
import store as store_module

SCOPES = ("Safety", "EMC", "Environmental", "Record")
CORE_SCOPES = ("Safety", "EMC", "Environmental")
VERIFY_STATUSES = ("Verified", "Needs review")
REVERIFY_DAYS = 365

# field -> (type, pillar scope, label)
FIELDS = {
    "safety_std": ("str", "Safety", "Safety standard"),
    "emc_std": ("str", "EMC", "EMC / radio standard"),
    "env_std": ("str", "Environmental", "Environmental standard"),
    "rohs_std": ("str", "Environmental", "RoHS"),
    "pfas_std": ("str", "Environmental", "PFAS / chemicals"),
    "packaging_std": ("str", "Environmental", "Packaging"),
    "epr_std": ("str", "Environmental", "EPR / WEEE"),
    "notes": ("text", "Record", "Regulatory notes"),
    "authority": ("str", "Record", "Regulatory authority"),
    "in_country_testing": ("bool", "Record", "In-country testing mandatory"),
    "local_rep_required": ("bool", "Record", "Local representative required"),
    "lead_time_weeks": ("int", "Record", "Lead time (weeks)"),
    "cert_validity": ("str", "Record", "Certificate validity"),
    "cb_scheme_accepted": ("bool", "Record", "CB Scheme accepted"),
}

_lock = threading.RLock()
_db = None
_sources_cache = None


# ---------------------------------------------------------------------------------------- helpers
def utc_now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today():
    return _dt.date.today().isoformat()


def _path(name):
    return config.data_path(name)


def _read(name, default):
    data = config.read_json(_path(name), default)
    return data if isinstance(data, type(default)) else default


def _write(name, payload):
    config.atomic_write_json(_path(name), payload)


def is_http_url(url):
    return bool(re.match(r"^https?://[^\s/$.?#][^\s]*$", str(url or "").strip(), re.I)) and len(str(url)) <= 500


def reviewer_name():
    return str(config.load_settings().get("reviewer_name") or "").strip()[:60]


def second_reviewer_required():
    return bool(config.load_settings().get("require_second_reviewer"))


# ---------------------------------------------------------------------------------------- init / overrides
def init(db_module):
    """Remember the db module and apply stored overrides on top of the seed in memory."""
    global _db
    _db = db_module
    apply_all_overrides()


def _seed_countries():
    data = config.read_json(config.bundle_path("countries_data.json"), {})
    return data if isinstance(data, dict) else {}


def overrides():
    with _lock:
        return _read("kb_overrides.json", {})


def apply_all_overrides():
    with _lock:
        for code, fields in overrides().items():
            c = _db.COUNTRIES_DB.get(code)
            if not c or not isinstance(fields, dict):
                continue
            for f, v in fields.items():
                if f in FIELDS:
                    c[f] = v


def normalise_value(field, value):
    """Validate and coerce a proposed value. Returns (value, error)."""
    kind = FIELDS[field][0]
    if kind in ("str", "text"):
        if not isinstance(value, str) or not value.strip():
            return None, f"'{field}' must be a non-empty text value"
        v = value.strip()
        limit = 2000 if kind == "text" else 500
        if len(v) > limit:
            return None, f"'{field}' is too long (max {limit} characters)"
        return v, None
    if kind == "bool":
        if isinstance(value, bool):
            return value, None
        if isinstance(value, str) and value.strip().lower() in ("true", "false", "yes", "no"):
            return value.strip().lower() in ("true", "yes"), None
        return None, f"'{field}' must be true or false"
    if kind == "int":
        try:
            if isinstance(value, bool):
                raise ValueError
            n = int(float(value))
        except (TypeError, ValueError):
            return None, f"'{field}' must be a whole number"
        if not 0 <= n <= 104:
            return None, f"'{field}' must be between 0 and 104"
        return n, None
    return None, "Unsupported field"


def current_value(code, field):
    c = _db.COUNTRIES_DB.get(code) or {}
    return c.get(field)


def set_overrides(code, changes):
    """Persist overrides and apply them in memory. Returns {field: {before, after}}."""
    with _lock:
        ov = overrides()
        cur = ov.setdefault(code, {})
        diff = {}
        c = _db.COUNTRIES_DB[code]
        for f, v in changes.items():
            diff[f] = {"before": c.get(f), "after": v}
            cur[f] = v
            c[f] = v
        _write("kb_overrides.json", ov)
        return diff


def revert_override(code, field):
    """Delete one override and restore the shipped seed value. Returns {before, after} or None."""
    with _lock:
        ov = overrides()
        if code not in ov or field not in ov[code]:
            return None
        del ov[code][field]
        if not ov[code]:
            del ov[code]
        _write("kb_overrides.json", ov)
        c = _db.COUNTRIES_DB.get(code)
        before = c.get(field) if c else None
        seed = _seed_countries().get(code, {})
        if c is not None:
            if field in seed:
                c[field] = seed[field]
            else:
                c.pop(field, None)
        return {"before": before, "after": seed.get(field)}


# ---------------------------------------------------------------------------------------- sources
def _sources_doc():
    global _sources_cache
    if _sources_cache is None:
        data = config.read_json(config.bundle_path("kb_sources.json"), {})
        _sources_cache = data if isinstance(data, dict) else {}
    return _sources_cache


def authority_sources(code):
    doc = _sources_doc()
    out = [dict(x) for x in (doc.get("countries", {}).get(code) or [])]
    for g in (doc.get("groups") or {}).values():
        if code in (g.get("members") or []):
            out.extend(dict(x) for x in g.get("sources", []))
    seen, uniq = set(), []
    for x in out:
        if x["url"] not in seen:
            seen.add(x["url"])
            uniq.append(x)
    return uniq


def global_sources():
    return [dict(x) for x in (_sources_doc().get("global") or [])]


def key_market_codes():
    doc = _sources_doc()
    codes = set(doc.get("countries", {}))
    for g in (doc.get("groups") or {}).values():
        codes.update(g.get("members") or [])
    return sorted(c for c in codes if _db is None or c in _db.COUNTRIES_DB)


# ---------------------------------------------------------------------------------------- verification
def verification_data():
    with _lock:
        return _read("kb_verification.json", {})


def _expired(entry):
    if entry.get("status") != "Verified":
        return False
    today_d = _dt.date.today()
    try:
        if entry.get("expires_on") and _dt.date.fromisoformat(entry["expires_on"][:10]) < today_d:
            return True
        return (today_d - _dt.date.fromisoformat(str(entry.get("verified_on"))[:10])).days > REVERIFY_DAYS
    except (TypeError, ValueError):
        return True


def verification_for(code, vdata=None):
    """{overall, per_pillar, sources, overrides, verified_on, verified_by} for one country."""
    vdata = verification_data() if vdata is None else vdata
    stored = vdata.get(code) or {}
    per, fresh, stale, latest = {}, 0, 0, None
    for scope in SCOPES:
        e = stored.get(scope)
        if not e:
            per[scope] = {"status": "Unverified"}
            continue
        e = dict(e)
        if e.get("status") == "Verified":
            if _expired(e):
                e["status"] = "Needs re-verification"
                stale += 1
            else:
                fresh += 1
                if latest is None or str(e.get("verified_on")) > str(latest.get("verified_on")):
                    latest = e
        per[scope] = e
    core_ok = all(per[s]["status"] == "Verified" for s in CORE_SCOPES)
    if core_ok or per["Record"]["status"] == "Verified":
        overall = "Verified"
    elif fresh == 0 and stale > 0:
        overall = "Needs re-verification"
    elif fresh > 0 or stale > 0:
        overall = "Partly verified"
    else:
        overall = "Unverified"
    portals = authority_sources(code)
    citations, seen = [], set()
    for scope in SCOPES:
        e = per[scope]
        if e.get("source_url") and e["status"] in ("Verified", "Needs re-verification") and e["source_url"] not in seen:
            seen.add(e["source_url"])
            citations.append({"label": e.get("source_label") or f"{scope} citation", "url": e["source_url"], "kind": "Reviewer citation"})
    return {
        "overall": overall, "per_pillar": per, "sources": citations + [p for p in portals if p["url"] not in seen],
        "has_portal_sources": bool(portals), "overrides": sorted((overrides().get(code) or {}).keys()),
        "verified_on": (latest or {}).get("verified_on"), "verified_by": (latest or {}).get("verified_by"),
    }


def attach(rows):
    """Add a 'verification' block to matrix rows (dicts with country_code) in place."""
    vdata, ov = verification_data(), overrides()
    cache = {}
    for r in rows:
        code = r.get("country_code") or r.get("code")
        if code not in cache:
            v = verification_for(code, vdata)
            v["overrides"] = sorted((ov.get(code) or {}).keys())
            cache[code] = v
        r["verification"] = cache[code]
    return rows


def set_verification(code, scope, status, source_url, source_label, note, who):
    with _lock:
        data = verification_data()
        before = (data.get(code) or {}).get(scope)
        entry = {"status": status, "source_url": source_url or "", "source_label": source_label or "",
                 "verified_by": who, "verified_on": today(), "note": note or ""}
        data.setdefault(code, {})[scope] = entry
        _write("kb_verification.json", data)
        return before, entry


def coverage():
    codes = key_market_codes()
    vdata = verification_data()
    ver = stale = 0
    for c in codes:
        o = verification_for(c, vdata)["overall"]
        if o == "Verified":
            ver += 1
        elif o == "Needs re-verification":
            stale += 1
    return {"key_markets_total": len(codes), "verified": ver, "needs_reverification": stale,
            "unverified": len(codes) - ver - stale}


# ---------------------------------------------------------------------------------------- queue
def queue_items():
    with _lock:
        return _read("review_queue.json", [])


def _event_item_id(event_id):
    return "REV-" + hashlib.sha1(str(event_id).encode("utf-8", "ignore")).hexdigest()[:8].upper()


def find_item(item_id):
    for it in queue_items():
        if it.get("id") == item_id:
            return it
    return None


def queued_event_ids():
    """Event ids of surveillance notices in ANY state (pending, approved, rejected) - never re-queue."""
    return {(it.get("payload") or {}).get("event_id") for it in queue_items() if it.get("type") == "surveillance_notice"}


def enqueue_notice(event):
    """Queue a detected surveillance event. Returns the item, or None if it was already queued."""
    with _lock:
        items = queue_items()
        eid = event.get("event_id")
        if any(it.get("type") == "surveillance_notice" and (it.get("payload") or {}).get("event_id") == eid for it in items):
            return None
        item = {"id": _event_item_id(eid), "type": "surveillance_notice", "status": "Pending", "created_at": utc_now(),
                "proposed_by": "Surveillance engine", "payload": event, "source_url": event.get("source_url") or "",
                "decided_by": None, "decided_on": None, "decision_note": ""}
        items.insert(0, item)
        _write("review_queue.json", items)
        return item


def enqueue_change(code, changes, reason, source_url, source_label, who):
    """changes: {field: normalised value}. Returns the queued item."""
    with _lock:
        c = _db.COUNTRIES_DB[code]
        items = queue_items()
        item = {"id": "REV-" + uuid.uuid4().hex[:8].upper(), "type": "kb_change", "status": "Pending", "created_at": utc_now(),
                "proposed_by": who,
                "payload": {"country_code": code, "country_name": c.get("name", code), "reason": reason,
                            "source_label": source_label or "",
                            "changes": {f: {"before": c.get(f), "after": v} for f, v in changes.items()}},
                "source_url": source_url, "decided_by": None, "decided_on": None, "decision_note": ""}
        items.insert(0, item)
        _write("review_queue.json", items)
        return item


def decide(item_id, status, who, note):
    with _lock:
        items = queue_items()
        for it in items:
            if it.get("id") == item_id:
                it.update({"status": status, "decided_by": who, "decided_on": utc_now(), "decision_note": note or ""})
                _write("review_queue.json", items)
                return it
        return None


def queue_counts():
    out = {"Pending": 0, "Approved": 0, "Rejected": 0}
    for it in queue_items():
        out[it.get("status")] = out.get(it.get("status"), 0) + 1
    return out


# ---------------------------------------------------------------------------------------- audit trail
def audit_entries():
    """Newest first; hash chain runs oldest -> newest (same convention as the surveillance ledger)."""
    with _lock:
        return _read("audit_trail.json", [])


def audit_append(who, what, item_id=None, country_code=None, before=None, after=None, detail=""):
    with _lock:
        log = audit_entries()
        prev = log[0].get("hash") if log else None
        entry = {"audit_id": "AUD-" + uuid.uuid4().hex[:8].upper(), "when": utc_now(), "who": who or "unknown", "what": what,
                 "item_id": item_id, "country_code": country_code, "before": before, "after": after, "detail": str(detail or "")[:500]}
        entry["prev_hash"] = prev
        entry["hash"] = store_module.ledger_hash(entry, prev)
        log.insert(0, entry)
        _write("audit_trail.json", log)
        return entry


def audit_ok():
    return store_module.verify_ledger(audit_entries())
