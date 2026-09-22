"""
routes_core.py - Overview, categories, matrix, countries, products, certificates,
eco analysis, readiness, surveillance, settings, actions, global search, health.
"""
import datetime as _dt
import time

from flask import jsonify, request, send_file

import config
import excel_export
import reg_surveillance
from store import ALERT_STATUSES, ACTION_STATUSES, verify_ledger

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _q(name, default=""):
    return (request.args.get(name, default) or "").strip()


def _days_until(iso):
    try:
        d = _dt.date.fromisoformat(str(iso)[:10])
        return (d - _dt.date.today()).days
    except (TypeError, ValueError):
        return None


def register(app, ctx):
    store = ctx["store"]
    surveillance = ctx["surveillance"]
    db = ctx["db"]

    # ------------------------------------------------------------------ health / settings
    @app.get("/api/health")
    def core_health():
        return jsonify({
            "status": "ok", "version": config.APP_VERSION, "codename": config.APP_CODENAME,
            "frozen": config.IS_FROZEN, "data_dir": config.DATA_DIR,
            "uptime_s": round(time.time() - ctx.get("started_at", time.time())),
            "countries": len(db.COUNTRIES_DB), "alerts": len(store.alerts()),
        })

    @app.get("/api/settings")
    def core_settings_get():
        return jsonify(config.public_settings())

    @app.post("/api/settings")
    def core_settings_post():
        data = request.get_json(silent=True) or {}
        allowed = {}
        for k in ("company_name", "ai_model", "ai_enabled", "anthropic_api_key", "surveillance_auto_scan_hours", "open_browser", "default_category", "port"):
            if k in data:
                allowed[k] = data[k]
        if "surveillance_auto_scan_hours" in allowed:
            try:
                allowed["surveillance_auto_scan_hours"] = max(0, min(168, float(allowed["surveillance_auto_scan_hours"])))
            except (TypeError, ValueError):
                return jsonify({"error": "surveillance_auto_scan_hours must be a number"}), 400
        if "ai_model" in allowed and allowed["ai_model"] not in ("claude-opus-5", "claude-sonnet-5", "claude-fable-5-1"):
            return jsonify({"error": "Unsupported model"}), 400
        config.save_settings(allowed)
        return jsonify({"success": True, "settings": config.public_settings()})

    @app.get("/api/backup")
    def core_backup():
        """Zip of the whole data folder (knowledge-base working copy, ledger, user data, settings)."""
        import io
        import os
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(config.DATA_DIR):
                for name in files:
                    if name.endswith(".tmp"):
                        continue
                    full = os.path.join(root, name)
                    zf.write(full, os.path.relpath(full, config.DATA_DIR))
        buf.seek(0)
        stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M")
        return send_file(buf, as_attachment=True, download_name=f"GCM_Platform_backup_{stamp}.zip", mimetype="application/zip")

    # ------------------------------------------------------------------ overview
    @app.get("/api/overview")
    def core_overview():
        alerts = store.alerts()
        states = store.all_alert_states()
        products = store.products()
        certs = store.certificates()
        actions = store.actions()

        sev = {"Critical": 0, "Warning": 0, "Info": 0}
        pillar_counts = {}
        triage_counts = {s: 0 for s in ALERT_STATUSES}
        for a in alerts:
            sev[a.get("severity", "Info")] = sev.get(a.get("severity", "Info"), 0) + 1
            p = a.get("pillar") or reg_surveillance.infer_pillar(a)
            pillar_counts[p] = pillar_counts.get(p, 0) + 1
            st = states.get(a.get("id"), {}).get("status", "New")
            triage_counts[st] = triage_counts.get(st, 0) + 1

        regions_count = {}
        in_country = 0
        for c in db.COUNTRIES_DB.values():
            reg = c.get("region", "Other")
            regions_count[reg] = regions_count.get(reg, 0) + 1
            if c.get("in_country_testing"):
                in_country += 1

        expiring = [c for c in certs if c.get("status") in ("Expiring Soon", "Critical", "Expired")]
        recent = []
        for a in alerts[:6]:
            recent.append({
                "id": a.get("id"), "title": a.get("title"), "severity": a.get("severity"), "country": a.get("country"),
                "standard": a.get("standard"), "summary": a.get("summary"), "effective_date": a.get("effective_date"),
                "days_to_effective": _days_until(a.get("effective_date")),
                "pillar": a.get("pillar") or reg_surveillance.infer_pillar(a),
                "triage_status": states.get(a.get("id"), {}).get("status", "New"),
            })

        return jsonify({
            "total_countries": len(db.COUNTRIES_DB),
            "total_categories": len(db.PRODUCT_CATEGORIES),
            "total_products": len(products),
            "total_certificates": len(certs),
            "in_country_testing_markets": in_country,
            "active_alerts_count": len(alerts),
            "critical_alerts_count": sev.get("Critical", 0),
            "warning_alerts_count": sev.get("Warning", 0),
            "info_alerts_count": sev.get("Info", 0),
            "open_actions_count": sum(1 for x in actions if x.get("status") != "Done"),
            "overdue_actions_count": sum(1 for x in actions if x.get("status") != "Done" and (_days_until(x.get("due_date")) or 0) < 0 and x.get("due_date")),
            "expiring_certificates_count": len(expiring),
            "regions_count": regions_count,
            "pillar_counts": pillar_counts,
            "triage_counts": triage_counts,
            "recent_alerts": recent,
            "surveillance_status": surveillance.get_status(light=True),
            "company": config.load_settings().get("company_name", "SanDisk"),
            "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    # ------------------------------------------------------------------ categories & matrix
    @app.get("/api/categories")
    def core_categories():
        return jsonify(list(db.PRODUCT_CATEGORIES.values()))

    def _filter_matrix(category_id, type_filter, region, search):
        breakdown = db.get_product_market_breakdown(category_id)
        type_filter = (type_filter or "all").lower()
        region = (region or "all").lower()
        search = (search or "").lower()
        out = []
        for c in breakdown["countries"]:
            req = c["requirement_type"]
            if type_filter == "testing" and "Testing Required" not in req:
                continue
            if type_filter == "document" and "Document Required" not in req:
                continue
            if type_filter == "sdoc" and ("Supplier Declaration" not in req and "Exempt" not in req):
                continue
            if type_filter == "local_rep" and not c.get("local_rep_required"):
                continue
            if type_filter == "transition" and not c.get("transitions"):
                continue
            if region not in ("", "all") and region not in c["region"].lower():
                continue
            if search:
                hay = " ".join(str(c.get(k, "")) for k in (
                    "country_name", "country_code", "authority", "safety_std", "national_safety_std", "emc_std", "env_std",
                    "rohs_std", "pfas_std", "packaging_std", "epr_std", "notes", "bloc")).lower()
                hay += " " + " ".join(c.get("required_documents", [])).lower() + " " + " ".join(c.get("marks", [])).lower()
                if search not in hay:
                    continue
            out.append(c)
        return breakdown, out

    @app.get("/api/gma/by-product")
    def core_gma_by_product():
        cat_id = _q("category", "external_ssd_powered")
        if cat_id not in db.PRODUCT_CATEGORIES:
            return jsonify({"error": f"Unknown category '{cat_id}'"}), 400
        breakdown, filtered = _filter_matrix(cat_id, _q("type", "all"), _q("region", "all"), _q("search"))
        return jsonify({
            "category_id": breakdown["category_id"], "category_name": breakdown["category_name"],
            "summary": breakdown["summary"], "countries_count": len(filtered), "countries": filtered,
        })

    @app.get("/api/gma/export-excel")
    def core_export_excel():
        cat_id = _q("category", "external_ssd_powered")
        if cat_id not in db.PRODUCT_CATEGORIES:
            return jsonify({"error": f"Unknown category '{cat_id}'"}), 400
        export_all = _q("export_all", "false").lower() == "true"
        buf, filename = excel_export.export_product_matrix_excel(
            category_id=cat_id, type_filter=_q("type", "all"), region_filter=_q("region", "all"),
            search=_q("search"), export_all=export_all,
        )
        return send_file(buf, as_attachment=True, download_name=filename, mimetype=XLSX)

    # ------------------------------------------------------------------ countries
    @app.get("/api/countries")
    def core_countries():
        region_filter = _q("region").lower()
        bloc_filter = _q("bloc").lower()
        query = _q("search").lower()
        out = []
        for c in db.COUNTRIES_DB.values():
            if region_filter and region_filter != "all" and region_filter not in c.get("region", "").lower():
                continue
            if bloc_filter and bloc_filter != "all" and bloc_filter not in (c.get("bloc") or "").lower():
                continue
            if query and not (query in c.get("name", "").lower() or query in c.get("code", "").lower()
                              or query in c.get("authority", "").lower() or any(query in m.lower() for m in c.get("marks", []))):
                continue
            out.append(c)
        out.sort(key=lambda x: x.get("name", ""))
        return jsonify(out)

    @app.get("/api/countries/<code>")
    def core_country_detail(code):
        code = code.upper()
        country = db.COUNTRIES_DB.get(code)
        if not country:
            return jsonify({"error": "Country not found"}), 404
        category_rules = {}
        for cat_id, cat in db.PRODUCT_CATEGORIES.items():
            rule = db.get_country_product_requirement(code, cat_id) or {}
            category_rules[cat_id] = {
                "category_name": cat["name"], "requirement_type": rule.get("requirement_type"),
                "is_exempt_from_mains_safety": rule.get("is_safety_exempt"), "safety_status": rule.get("safety_status"),
                "testing_location": rule.get("testing_location"), "badge": rule.get("badge"),
                "applicable_marks": country.get("marks", []), "lead_time": f"{rule.get('lead_time', country.get('lead_time_weeks', 2))} weeks",
                "required_documents": rule.get("required_documents", []), "notes": rule.get("notes"),
            }
        alerts = [a for a in store.alerts() if reg_surveillance.alert_matches_country(a, country)]
        products = [p for p in store.products() if code in [m.upper() for m in p.get("target_markets", [])]]
        return jsonify({"country": country, "category_rules": category_rules,
                        "alerts": [{"id": a["id"], "title": a["title"], "severity": a.get("severity"), "effective_date": a.get("effective_date"),
                                    "standard": a.get("standard"), "pillar": a.get("pillar") or reg_surveillance.infer_pillar(a)} for a in alerts],
                        "products": [{"id": p["id"], "sku": p["sku"], "name": p["name"], "category_id": p["category_id"]} for p in products]})

    # ------------------------------------------------------------------ products & certificates
    @app.get("/api/products")
    def core_products():
        return jsonify(store.products())

    @app.post("/api/products")
    def core_create_product():
        data = request.get_json(silent=True) or {}
        cat_id = data.get("category_id", "sd_card")
        cat = db.PRODUCT_CATEGORIES.get(cat_id)
        if not cat:
            return jsonify({"error": f"Unknown category '{cat_id}'"}), 400
        if not str(data.get("name", "")).strip():
            return jsonify({"error": "Product name is required"}), 400
        markets = [str(m).upper()[:2] for m in (data.get("target_markets") or ["US", "DE", "JP", "GB", "CN", "IN"])]
        markets = [m for m in markets if m in db.COUNTRIES_DB]
        prod = store.add_product({
            "sku": str(data.get("sku") or "NEW-SKU").strip()[:40], "name": str(data.get("name")).strip()[:120],
            "category_id": cat_id, "category_name": cat["name"], "hw_revision": str(data.get("hw_revision") or "Rev A.0")[:20],
            "controller": str(data.get("controller") or "Standard Controller ASIC")[:120], "nand": str(data.get("nand") or "3D NAND Flash")[:120],
            "power_source": cat.get("power_type", "Bus-powered"), "target_markets": markets,
            "compliance_status": "Planning / Scoping", "active_certs_count": 0, "readiness_pct": 0,
        })
        return jsonify({"success": True, "product": prod}), 201

    @app.get("/api/certificates")
    def core_certificates():
        status = _q("status").lower()
        prod_id = _q("product_id")
        search = _q("search").lower()
        out = []
        for c in store.certificates():
            if status and status != "all" and c.get("status", "").lower() != status:
                continue
            if prod_id and prod_id != "all" and c.get("product_id") != prod_id:
                continue
            if search and not any(search in str(c.get(k, "")).lower() for k in ("cert_no", "scheme", "product_name", "country_coverage", "standard", "issuing_body")):
                continue
            c = dict(c)
            c["days_to_expiry"] = _days_until(c.get("expiry_date"))
            out.append(c)
        return jsonify(out)

    @app.post("/api/certificates")
    def core_create_certificate():
        data = request.get_json(silent=True) or {}
        if not str(data.get("cert_no", "")).strip():
            return jsonify({"error": "Certificate number is required"}), 400
        product = next((p for p in store.products() if p["id"] == data.get("product_id")), None)
        cert = store.add_certificate({
            "cert_no": str(data["cert_no"]).strip()[:60], "scheme": str(data.get("scheme") or "CE Declaration of Conformity")[:120],
            "standard": str(data.get("standard") or "EN 62368-1 / EN 55032")[:160], "issuing_body": str(data.get("issuing_body") or "Accredited Lab / Self-Declaration")[:120],
            "product_id": data.get("product_id") or (product or {}).get("id") or "PROD-001", "product_name": (product or {}).get("name") or str(data.get("product_name") or "Storage Product")[:120],
            "country_coverage": str(data.get("country_coverage") or "Global")[:160], "issue_date": str(data.get("issue_date") or _dt.date.today().isoformat())[:10],
            "expiry_date": str(data.get("expiry_date") or "")[:10], "status": data.get("status") if data.get("status") in ("Valid", "Expiring Soon", "Critical", "Expired") else "Valid",
            "document_type": str(data.get("document_type") or "Test Certificate")[:120], "notes": str(data.get("notes") or "")[:500],
        })
        return jsonify({"success": True, "certificate": cert}), 201

    # ------------------------------------------------------------------ eco & readiness (kept)
    @app.post("/api/eco/analyze")
    def core_eco_analyze():
        data = request.get_json(silent=True) or {}
        category_id = data.get("category_id", "external_ssd_powered")
        if category_id not in db.PRODUCT_CATEGORIES:
            return jsonify({"error": f"Unknown category '{category_id}'"}), 400
        targets = [str(c).upper() for c in (data.get("target_countries") or ["US", "DE", "FR", "GB", "JP", "KR", "TW", "CN", "IN", "AU", "BR", "MX"])]
        return jsonify(db.evaluate_eco_impact(category_id, data.get("component_type", "power_adapter"),
                                              data.get("change_description", "Component substitution"), targets))

    @app.post("/api/gma/readiness")
    def core_gma_readiness():
        data = request.get_json(silent=True) or {}
        product = next((p for p in store.products() if p["id"] == data.get("product_id")), None)
        if not product:
            return jsonify({"error": "Product not found"}), 404
        import risk_engine
        codes = [str(c).upper() for c in (data.get("countries") or product.get("target_markets", []))]
        evals = risk_engine.readiness_for_product(product, codes, store.certificates(), db)
        ready = sum(1 for e in evals if e["badge"] in ("success", "info"))
        total = len(evals)
        return jsonify({"product": product, "total_target_markets": total, "ready_count": ready, "pending_count": total - ready,
                        "readiness_percentage": round(ready / total * 100) if total else 0, "evaluations": evals})

    # ------------------------------------------------------------------ surveillance
    @app.get("/api/surveillance/status")
    def core_surv_status():
        return jsonify(surveillance.get_status())

    @app.post("/api/surveillance/scan")
    def core_surv_scan():
        result = surveillance.scan_all_sources()
        return jsonify({"result": result, "status": surveillance.get_status(light=True), "alerts_count": len(store.alerts())})

    @app.get("/api/surveillance/log")
    def core_surv_log():
        try:
            limit = max(1, min(500, int(_q("limit", "100"))))
        except ValueError:
            limit = 100
        entries = surveillance.get_audit_log(limit=limit)
        ok, bad = verify_ledger(surveillance.get_audit_log(limit=100000))
        return jsonify({"audit_log": entries, "status": surveillance.get_status(light=True), "ledger_ok": ok, "ledger_first_bad_index": bad,
                        "ledger_entries": len(surveillance.get_audit_log(limit=100000))})

    @app.post("/api/surveillance/simulate")
    def core_surv_simulate():
        data = request.get_json(silent=True) or {}
        cc = str(data.get("country_code") or "ALL").upper().strip()
        if cc not in ("ALL", "GLOBAL", "WORLDWIDE", "ALL_COUNTRIES") and cc not in db.COUNTRIES_DB:
            return jsonify({"error": f"Unknown country code '{cc}'"}), 400
        cats = data.get("affected_categories") or ["external_ssd_powered", "external_ssd_bus", "internal_ssd", "usb_drive"]
        cats = [c for c in cats if c in db.PRODUCT_CATEGORIES or c in ("all", "all_storage_categories")] or ["all_storage_categories"]
        pillar = data.get("pillar", "Safety")
        if pillar not in ("Safety", "EMC", "Environmental", "Cyber", "All"):
            pillar = "Safety"
        event = surveillance.simulate_gazette_update(
            country_code=cc, authority=str(data.get("authority") or "National Regulatory Authority")[:160],
            new_standard=str(data.get("new_standard") or "IEC 62368-1:2023 (Edition 4.0)")[:160],
            deadline=str(data.get("deadline") or "2028-11-01")[:10],
            summary=str(data.get("summary") or "Official Gazette Notification: mandatory transition to updated standard.")[:2000],
            affected_categories=cats, pillar=pillar, source_url=(data.get("source_url") or None),
        )
        return jsonify({"success": True, "event": event, "alert": event.get("alert"),
                        "affected_countries_count": event.get("affected_countries_count", 1),
                        "impacted_products_count": event.get("impacted_products_count", 0),
                        "total_alerts_count": len(store.alerts()), "status": surveillance.get_status(light=True)})

    @app.route("/api/surveillance/auto-simulate/next", methods=["GET", "POST"])
    def core_surv_auto_next():
        event = surveillance.auto_simulate_next_event(products=store.products())
        return jsonify({"success": True, "event": event, "alert": event.get("alert"),
                        "impacted_products": event.get("impacted_products", []), "impacted_products_count": event.get("impacted_products_count", 0),
                        "status": surveillance.get_status(light=True), "total_alerts_count": len(store.alerts())})

    @app.post("/api/surveillance/reset-knowledge-base")
    def core_surv_reset():
        """Restore the working copy of the country knowledge base from the shipped seed."""
        result = surveillance.reset_to_seed()
        return jsonify({"success": True, **result})

    # ------------------------------------------------------------------ actions
    def _action_view(a):
        a = dict(a)
        a["days_to_due"] = _days_until(a.get("due_date"))
        a["overdue"] = bool(a.get("due_date")) and a.get("status") != "Done" and (a["days_to_due"] or 0) < 0
        return a

    @app.get("/api/actions")
    def core_actions():
        status = _q("status")
        linked_type = _q("linked_type")
        linked_id = _q("linked_id")
        out = []
        for a in store.actions():
            if status and status != "all" and a.get("status") != status:
                continue
            if linked_type and a.get("linked_type") != linked_type:
                continue
            if linked_id and a.get("linked_id") != linked_id:
                continue
            out.append(_action_view(a))
        return jsonify({"actions": out, "count": len(out), "statuses": list(ACTION_STATUSES)})

    @app.post("/api/actions")
    def core_action_create():
        data = request.get_json(silent=True) or {}
        title = str(data.get("title", "")).strip()
        if not title:
            return jsonify({"error": "Title is required"}), 400
        action = store.add_action({
            "title": title[:200], "status": data.get("status") if data.get("status") in ACTION_STATUSES else "Open",
            "priority": data.get("priority") if data.get("priority") in ("Critical", "High", "Medium", "Low") else "Medium",
            "owner": str(data.get("owner") or "")[:80], "due_date": str(data.get("due_date") or "")[:10],
            "linked_type": data.get("linked_type"), "linked_id": data.get("linked_id"), "notes": str(data.get("notes") or "")[:2000],
        })
        return jsonify({"success": True, "action": _action_view(action)}), 201

    @app.patch("/api/actions/<action_id>")
    def core_action_update(action_id):
        data = request.get_json(silent=True) or {}
        fields = {k: data.get(k) for k in ("title", "status", "priority", "owner", "due_date", "notes") if k in data}
        if "status" in fields and fields["status"] not in ACTION_STATUSES:
            return jsonify({"error": f"status must be one of {ACTION_STATUSES}"}), 400
        updated = store.update_action(action_id, **fields)
        if not updated:
            return jsonify({"error": "Action not found"}), 404
        return jsonify({"success": True, "action": _action_view(updated)})

    @app.delete("/api/actions/<action_id>")
    def core_action_delete(action_id):
        if not store.delete_action(action_id):
            return jsonify({"error": "Action not found"}), 404
        return jsonify({"success": True})

    # ------------------------------------------------------------------ global search
    @app.get("/api/search")
    def core_search():
        q = _q("q").lower()
        if len(q) < 2:
            return jsonify({"results": []})
        results = []
        for c in db.COUNTRIES_DB.values():
            if q in c.get("name", "").lower() or q == c.get("code", "").lower() or q in c.get("authority", "").lower():
                results.append({"type": "country", "id": c["code"], "title": f"{c['name']} ({c['code']})", "subtitle": f"{c.get('authority', '')} · {c.get('region', '')}", "tab": "map"})
        for a in store.alerts():
            hay = f"{a.get('title', '')} {a.get('standard', '')} {a.get('country', '')} {a.get('summary', '')}".lower()
            if q in hay:
                results.append({"type": "alert", "id": a["id"], "title": a["title"], "subtitle": f"{a.get('severity')} · {a.get('country')} · {a.get('standard')}", "tab": "alerts"})
        for p in store.products():
            if q in f"{p.get('name', '')} {p.get('sku', '')} {p.get('category_name', '')}".lower():
                results.append({"type": "product", "id": p["id"], "title": p["name"], "subtitle": f"{p.get('sku')} · {p.get('category_name')}", "tab": "portfolio"})
        standards = set()
        for c in db.COUNTRIES_DB.values():
            for k in ("safety_std", "emc_std", "env_std", "rohs_std", "pfas_std", "packaging_std", "epr_std"):
                v = c.get(k)
                if v and q in v.lower():
                    standards.add(v)
        for s in sorted(standards)[:8]:
            results.append({"type": "standard", "id": s, "title": s, "subtitle": "Search the matrix for this standard", "tab": "matrix"})
        for a in store.actions():
            if q in f"{a.get('title', '')} {a.get('owner', '')}".lower():
                results.append({"type": "action", "id": a["id"], "title": a["title"], "subtitle": f"{a.get('status')} · {a.get('owner') or 'unassigned'}", "tab": "overview"})
        return jsonify({"results": results[:40]})
