"""
routes_alerts.py - /api/alerts/* : list / create / detail / delete / triage / explain / expert Q&A,
plus /api/ai/status. See docs/ARCHITECTURE_CONTRACT.md §4 "Alerts".

Every served alert is enriched with: triage {status, owner, notes, updated_at}, days_to_effective,
pillar, impacted_products (+ impacted_products_count), market_count, is_user_created.
"""
import datetime as _dt
import re

from flask import Response, jsonify, request

import ai_bridge
import alert_explainer
import expert_advisor
import reg_surveillance
from store import ALERT_STATUSES

SEVERITIES = ("Critical", "Warning", "Info")
PILLARS = ("Safety", "EMC", "Environmental", "Cyber", "All")
SORTS = ("newest", "deadline", "severity")
_URL_RE = re.compile(r"^https?://[^\s<>\"']+$", re.I)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _q(name, default=""):
    return (request.args.get(name, default) or "").strip()


def _days_until(iso):
    try:
        d = _dt.date.fromisoformat(str(iso)[:10])
        return (d - _dt.date.today()).days
    except (TypeError, ValueError):
        return None


def _utc_now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def register(app, ctx):
    store = ctx["store"]
    db = ctx["db"]
    seed_ids = {a.get("id") for a in getattr(db, "REGULATION_ALERTS", [])}
    advisor = expert_advisor.get_expert_advisor()

    # ------------------------------------------------------------------ enrichment
    def _is_user_created(alert):
        return alert.get("id") not in seed_ids

    def _market_codes(alert):
        try:
            return sorted(c for c in reg_surveillance._alert_country_codes(alert, db.COUNTRIES_DB) if c in db.COUNTRIES_DB)
        except Exception:
            return []

    def _impacts(alert, products):
        cats = alert.get("affected_categories") or ["all_storage_categories"]
        cc = str(alert.get("country_code") or "").upper()
        if not cc:
            codes = _market_codes(alert)
            if len(codes) >= len(db.COUNTRIES_DB) * 0.9:
                cc = "GLOBAL"
            elif len(codes) == 1:
                cc = codes[0]
            elif codes and set(codes) <= reg_surveillance.EU_COUNTRIES:
                cc = "EU"
            else:
                cc = "GLOBAL" if not codes else ""
        try:
            return reg_surveillance.resolve_product_impacts(cats, country_code=cc, region=alert.get("region") or alert.get("country") or "Global", products=products)
        except Exception:
            return []

    def _enrich(alert, states=None, products=None):
        a = dict(alert)
        states = states if states is not None else store.all_alert_states()
        products = products if products is not None else store.products()
        st = dict(states.get(a.get("id"), {}) or {})
        a["triage"] = {"status": st.get("status", "New"), "owner": st.get("owner", ""), "notes": st.get("notes", ""), "updated_at": st.get("updated_at")}
        a["days_to_effective"] = _days_until(a.get("effective_date"))
        a["pillar"] = a.get("pillar") if a.get("pillar") in PILLARS else reg_surveillance.infer_pillar(a)
        codes = _market_codes(a)
        a["market_count"] = len(codes)
        a["market_codes"] = codes if len(codes) <= 40 else codes[:40]
        a["impacted_products"] = _impacts(a, products)
        a["impacted_products_count"] = len(a["impacted_products"])
        a["is_user_created"] = _is_user_created(a)
        a["deadline_status"] = ("Passed" if a["days_to_effective"] is not None and a["days_to_effective"] < 0
                                else "Imminent" if a["days_to_effective"] is not None and a["days_to_effective"] <= 90
                                else "Approaching" if a["days_to_effective"] is not None and a["days_to_effective"] <= 365
                                else "Planned" if a["days_to_effective"] is not None
                                else ("In force" if str(a.get("effective_date") or "").lower().startswith("enforc") else "Unscheduled"))
        return a

    def _find(alert_id):
        return store.get_alert(alert_id)

    # ------------------------------------------------------------------ list
    @app.get("/api/alerts")
    def alerts_list():
        category = _q("category").lower()
        severity = _q("severity").lower()
        region = _q("region").lower()
        search = _q("search").lower()
        status = _q("status")
        pillar = _q("pillar")
        impacts_portfolio = _q("impacts_portfolio").lower() in ("1", "true", "yes")
        product_id = _q("product_id")
        sort = _q("sort", "newest").lower()
        if sort not in SORTS:
            sort = "newest"

        states = store.all_alert_states()
        products = store.products()
        out = []
        for raw in store.alerts():
            a = _enrich(raw, states, products)
            cats = [str(c) for c in (a.get("affected_categories") or [])]
            universal = any(c in ("all", "all_storage_categories", "all_categories") for c in cats)
            if category and category != "all" and not universal and category not in [c.lower() for c in cats]:
                continue
            if severity and severity != "all" and str(a.get("severity", "")).lower() != severity:
                continue
            if region and region != "all":
                hay = f"{a.get('region', '')} {a.get('country', '')}".lower()
                # word-boundary match so 'asia' does not hit 'Eurasia'
                if not re.search(r"(?<![a-z])" + re.escape(region), hay):
                    continue
            if status and status != "all" and a["triage"]["status"] != status:
                continue
            if pillar and pillar != "all" and pillar != "All" and a["pillar"] not in (pillar, "All"):
                continue
            if impacts_portfolio and not a["impacted_products"]:
                continue
            if product_id and product_id != "all" and not any(p.get("id") == product_id for p in a["impacted_products"]):
                continue
            if search:
                hay = " ".join(str(a.get(k, "")) for k in ("id", "title", "summary", "standard", "country", "region", "source", "detailed_summary", "technical_impact")).lower()
                hay += " " + " ".join(p.get("sku", "") for p in a["impacted_products"]).lower()
                if search not in hay:
                    continue
            out.append(a)

        if sort == "deadline":
            out.sort(key=lambda a: (a["days_to_effective"] is None, a["days_to_effective"] if a["days_to_effective"] is not None else 10 ** 6))
        elif sort == "severity":
            rank = {"Critical": 0, "Warning": 1, "Info": 2}
            out.sort(key=lambda a: (rank.get(a.get("severity"), 3), a["days_to_effective"] if a["days_to_effective"] is not None else 10 ** 6))
        # "newest": store order (user/surveillance alerts first, then seed) - keep as is
        return jsonify(out)

    # ------------------------------------------------------------------ create
    @app.post("/api/alerts")
    def alerts_create():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "JSON body required"}), 400
        title = str(data.get("title") or "").strip()
        summary = str(data.get("summary") or "").strip()
        if not title or not summary:
            return jsonify({"error": "title and summary are required"}), 400
        severity = data.get("severity") if data.get("severity") in SEVERITIES else "Warning"
        eff = str(data.get("effective_date") or "").strip()
        if eff and not _DATE_RE.match(eff):
            return jsonify({"error": "effective_date must be YYYY-MM-DD"}), 400
        source_url = str(data.get("source_url") or "").strip()
        if source_url and not _URL_RE.match(source_url):
            return jsonify({"error": "source_url must be an http(s) URL"}), 400
        cats_in = data.get("affected_categories") or []
        if isinstance(cats_in, str):
            cats_in = [cats_in]
        cats = [c for c in cats_in if c in db.PRODUCT_CATEGORIES]
        if not cats:
            cats = ["all_storage_categories"]

        country = str(data.get("country") or "").strip()[:120]
        region = str(data.get("region") or "").strip()[:80]
        country_code = ""
        if country:
            for code, c in db.COUNTRIES_DB.items():
                if c.get("name", "").lower() == country.lower() or code.lower() == country.lower():
                    country_code, country = code, c.get("name", country)
                    region = region or c.get("region", "")
                    break
            if not country_code and country.lower() in ("eu", "european union", "european union (eu 27)", "eu 27"):
                country_code, country = "EU", "European Union (EU 27)"
                region = region or "Europe & Eurasia"
            if not country_code and country.lower() in ("global", "worldwide", "all", "all countries"):
                country_code, country = "ALL", "All 205 global jurisdictions"
                region = "Global"
        if not country:
            country = "Global"
            country_code = "ALL"
            region = region or "Global"
        region = region or "Global"

        base = {"title": title[:200], "summary": summary[:2000], "standard": str(data.get("standard") or "").strip()[:160],
                "technical_impact": str(data.get("technical_impact") or "").strip()[:4000]}
        pillar = data.get("pillar") if data.get("pillar") in PILLARS else reg_surveillance.infer_pillar(base)
        standard = base["standard"] or {"Safety": "National safety standard update", "EMC": "National EMC standard update",
                                        "Environmental": "Environmental / substance regulation update", "Cyber": "Product cybersecurity requirement",
                                        "All": "Multi-pillar regulatory update"}[pillar]
        today = _dt.date.today()
        eff_date = _dt.date.fromisoformat(eff) if eff else None
        gap_date = max(today, eff_date - _dt.timedelta(days=180)) if eff_date else today + _dt.timedelta(days=30)
        action_required = str(data.get("action_required") or "").strip()[:1000] or (
            f"Assess every affected SKU against {standard}; update test evidence, declarations and labels before {eff or 'the enforcement date is confirmed'}.")
        source = str(data.get("source") or "").strip()[:160] or "Manually published alert"
        detailed = str(data.get("detailed_summary") or "").strip()[:6000] or (
            f"This alert was published manually on {today.isoformat()} for {country}. It records a {pillar.lower() if pillar != 'All' else 'multi-pillar'} "
            f"regulatory change referenced as {standard}.\n\n{summary}\n\n"
            f"Products in the affected categories that are placed on the market after the effective date must conform to the new requirement; "
            f"products already placed on the market are normally unaffected unless the notice states otherwise. Verify the scope against the official source.")
        technical_impact = base["technical_impact"] or (
            f"Pillar: {pillar}\nReference: {standard}\nApplies to: {', '.join(cats)}\nJurisdiction: {country}\n"
            f"Enforcement: {eff or 'to be confirmed'}\nEvidence expected: updated test reports / declarations / labels as applicable to the pillar.")
        checklist_by_pillar = {
            "Safety": [f"Map each affected SKU and its power adapter to {standard} and list the clauses that changed",
                       "Ask the certification body whether existing reports can be updated with a delta report or need a full re-test",
                       "Book laboratory capacity and prepare samples", "Re-issue the Declaration of Conformity and update labels / technical file"],
            "EMC": [f"Confirm which interfaces and operating modes must be tested under {standard}", "Run a pre-compliance scan on the highest-speed SKU",
                    "Book the formal EMC test and update the registration", "Update labels with the new registration number and re-issue the declaration"],
            "Environmental": ["Request material declarations from component and packaging suppliers", "Screen high-risk materials for the restricted substances",
                              "Update packaging artwork / portal registrations as required", "Archive supplier evidence in the technical file"],
            "Cyber": ["Inventory firmware components and generate a machine-readable SBOM", "Verify secure boot / signed update chain on every controller platform",
                      "Publish the vulnerability-disclosure policy and support period", "Update the technical file and conformity statement"],
            "All": ["Run a gap assessment across safety, EMC and environmental evidence", "Bundle lab testing to avoid duplicate sample builds",
                    "Update supplier declarations and packaging", "Re-issue all declarations and brief the channel"],
        }
        checklist = data.get("compliance_checklist") if isinstance(data.get("compliance_checklist"), list) else None
        checklist = [str(x)[:300] for x in checklist if str(x).strip()] if checklist else checklist_by_pillar[pillar]
        milestones = [{"phase": "Alert published in GCM Platform", "date": today.isoformat(), "status": "Completed"},
                      {"phase": "Recommended internal gap assessment complete", "date": gap_date.isoformat(), "status": "Recommended"}]
        if eff_date:
            milestones.append({"phase": "Enforcement / effective date", "date": eff, "status": "Enforcement Deadline"})
        links = []
        if source_url:
            links.append({"label": f"{source} – official source", "url": source_url})
        products = store.products()
        alert = {
            "id": None, "title": base["title"], "region": region, "country": country, "country_code": country_code or None,
            "standard": standard, "severity": severity, "effective_date": eff or "To be confirmed",
            "affected_categories": cats, "summary": base["summary"], "action_required": action_required,
            "status": "User-published", "source": source, "source_url": source_url or None,
            "detailed_summary": detailed, "technical_impact": technical_impact, "timeline_milestones": milestones,
            "official_links": links, "compliance_checklist": checklist, "pillar": pillar,
            "created_by": "user", "created_at": _utc_now(),
        }
        alert["impacted_products"] = _impacts(alert, products)
        alert["impacted_products_count"] = len(alert["impacted_products"])
        saved = store.add_alert(alert)
        return jsonify({"success": True, "alert": _enrich(saved)}), 201

    # ------------------------------------------------------------------ detail / delete
    @app.get("/api/alerts/<alert_id>")
    def alerts_detail(alert_id):
        a = _find(alert_id)
        if not a:
            return jsonify({"error": "Alert not found"}), 404
        return jsonify(_enrich(a))

    @app.delete("/api/alerts/<alert_id>")
    def alerts_delete(alert_id):
        a = _find(alert_id)
        if not a:
            return jsonify({"error": "Alert not found"}), 404
        if alert_id in seed_ids:
            return jsonify({"error": "Seeded knowledge-base alerts cannot be deleted; close them via triage instead."}), 403
        if not store.delete_alert(alert_id):
            return jsonify({"error": "Alert could not be deleted"}), 500
        try:
            ai_bridge.clear_cache(alert_id)
        except Exception:
            pass
        return jsonify({"success": True, "deleted": alert_id})

    # ------------------------------------------------------------------ triage
    @app.patch("/api/alerts/<alert_id>/triage")
    def alerts_triage(alert_id):
        a = _find(alert_id)
        if not a:
            return jsonify({"error": "Alert not found"}), 404
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "JSON body required"}), 400
        fields = {}
        if "status" in data:
            if data["status"] not in ALERT_STATUSES:
                return jsonify({"error": f"status must be one of {list(ALERT_STATUSES)}"}), 400
            fields["status"] = data["status"]
        if "owner" in data:
            fields["owner"] = str(data.get("owner") or "")[:80]
        if "notes" in data:
            fields["notes"] = str(data.get("notes") or "")[:2000]
        if not fields:
            return jsonify({"error": "Provide at least one of status, owner, notes"}), 400
        st = store.set_alert_state(alert_id, **fields)
        return jsonify({"success": True, "triage": {"status": st.get("status", "New"), "owner": st.get("owner", ""), "notes": st.get("notes", ""), "updated_at": st.get("updated_at")}})

    # ------------------------------------------------------------------ explain
    def _explain(alert, audience, refresh=False, allow_ai=True):
        rules = alert_explainer.explain_alert(alert, ctx, audience)
        if refresh:
            try:
                ai_bridge.clear_cache(alert.get("id"))
            except Exception:
                pass
        result = None
        if allow_ai and ai_bridge.is_active():
            try:
                result = ai_bridge.enhance_explanation(alert, rules, audience, use_cache=not refresh)
            except Exception as e:  # belt and braces - the bridge already swallows errors
                ai_bridge._set_error(f"{type(e).__name__}: {e}")
                result = None
        out = result or rules
        st = ai_bridge.status()
        out["ai_status"] = {"active": st["active"], "configured": st["configured"], "enabled": st["enabled"], "model": st["model"], "last_error": st["last_error"]}
        if not result and st["active"] and st["last_error"]:
            out["ai_note"] = f"Claude enhancement unavailable ({st['last_error']}); showing the rules-engine explanation."
        return out

    @app.get("/api/alerts/<alert_id>/explain")
    def alerts_explain(alert_id):
        a = _find(alert_id)
        if not a:
            return jsonify({"error": "Alert not found"}), 404
        audience = _q("audience", "simple").lower()
        if audience not in alert_explainer.AUDIENCES:
            return jsonify({"error": f"audience must be one of {list(alert_explainer.AUDIENCES)}"}), 400
        refresh = _q("refresh") in ("1", "true", "yes")
        allow_ai = _q("ai", "1") not in ("0", "false", "no")
        result = _explain(_enrich(a), audience, refresh=refresh, allow_ai=allow_ai)
        if _q("format").lower() == "text":
            return Response(alert_explainer.brief_text(result), mimetype="text/plain; charset=utf-8")
        return jsonify(result)

    # ------------------------------------------------------------------ expert (kept)
    @app.get("/api/alerts/<alert_id>/expert-consult")
    def alerts_expert_consult(alert_id):
        a = _find(alert_id)
        if not a:
            return jsonify({"error": "Alert not found"}), 404
        brief = advisor.consult_expert_on_alert(_enrich(a))
        brief["generated_by"] = "rules+web"
        return jsonify(brief)

    @app.post("/api/alerts/<alert_id>/expert-chat")
    def alerts_expert_chat(alert_id):
        a = _find(alert_id)
        if not a:
            return jsonify({"error": "Alert not found"}), 404
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "JSON body required"}), 400
        question = str(data.get("question") or "").strip()
        if not question:
            return jsonify({"error": "question is required"}), 400
        if len(question) > 2000:
            return jsonify({"error": "question too long (max 2000 characters)"}), 400
        history = data.get("history") if isinstance(data.get("history"), list) else []
        audience = data.get("audience") if data.get("audience") in alert_explainer.AUDIENCES else "engineer"
        enriched = _enrich(a)
        explanation = alert_explainer.explain_alert(enriched, ctx, audience)
        answer = advisor.answer_custom_question(enriched, question, explanation=explanation, history=history, ctx=ctx)
        return jsonify(answer)

    # ------------------------------------------------------------------ AI status
    @app.get("/api/ai/status")
    def alerts_ai_status():
        st = ai_bridge.status()
        return jsonify({"enabled": st["enabled"], "configured": st["configured"], "model": st["model"], "provider": st["provider"],
                        "sdk_available": st["sdk_available"], "sdk_version": st["sdk_version"], "active": st["active"],
                        "engine": st["engine"], "last_error": st["last_error"], "last_call_at": st["last_call_at"], "calls": st["calls"]})

    @app.post("/api/ai/cache/clear")
    def alerts_ai_cache_clear():
        ai_bridge.clear_cache()
        return jsonify({"success": True})

    register_research(app, ctx)


# ---------------------------------------------------------------------- Ask the Expert (general research)
def register_research(app, ctx):
    """General regulatory research assistant (not tied to one alert). See expert_research.py."""
    import expert_research

    @app.post("/api/expert/research")
    def research_ask():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "JSON body required"}), 400
        question = re.sub(r"\s+", " ", str(data.get("question") or "")).strip()
        if not question:
            return jsonify({"error": "question is required"}), 400
        if len(question) > expert_research.MAX_QUESTION:
            return jsonify({"error": f"question too long (max {expert_research.MAX_QUESTION} characters)"}), 400
        history = data.get("history") if isinstance(data.get("history"), list) else []
        history = [h for h in history if isinstance(h, dict) and h.get("role") in ("user", "assistant") and isinstance(h.get("content"), str)][-8:]
        allow_ai = data.get("ai", True) not in (False, 0, "0", "false", "no")
        allow_web = data.get("web", True) not in (False, 0, "0", "false", "no")
        try:
            result = expert_research.research(question, history=history, ctx=ctx, allow_ai=allow_ai, allow_web=allow_web)
        except Exception as e:  # never 500 without JSON
            return jsonify({"error": f"research failed: {type(e).__name__}: {e}"}), 500
        if (data.get("format") or "").lower() == "text":
            return Response(expert_research.brief_text(result), mimetype="text/plain; charset=utf-8")
        return jsonify(result)

    @app.get("/api/expert/suggestions")
    def research_suggestions():
        return jsonify({"suggestions": expert_research.suggestions()})
