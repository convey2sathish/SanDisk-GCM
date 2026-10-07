"""
routes_review.py - Human approval workflow for the knowledge base.

  /api/review/queue, /api/review/stats, /api/review/audit, /api/review/proposals,
  /api/review/queue/<id>/approve|reject, /api/verification/<code>, /api/overrides/<code>/<field>

Reviewer identity is the self-declared settings.reviewer_name (single-user tool, no logins).
"""
from flask import jsonify, request

import kb_review as kb


def _err(msg, status=400):
    return jsonify({"error": msg}), status


def register(app, ctx):
    db = ctx["db"]
    surveillance = ctx["surveillance"]

    def _who():
        who = kb.reviewer_name()
        if not who:
            return None, _err("Set your reviewer name in Settings")
        return who, None

    def _body():
        return request.get_json(silent=True) or {}

    def _clean(s, limit):
        return str(s or "").strip()[:limit]

    # ------------------------------------------------------------------ reads
    @app.get("/api/review/queue")
    def review_queue():
        status = (request.args.get("status") or "all").strip()
        items = kb.queue_items()
        if status.lower() != "all":
            if status not in ("Pending", "Approved", "Rejected"):
                return _err("status must be Pending, Approved, Rejected or all")
            items = [i for i in items if i.get("status") == status]
        return jsonify({"items": items, "count": len(items), "counts": kb.queue_counts()})

    @app.get("/api/review/stats")
    def review_stats():
        c = kb.queue_counts()
        ok, _bad = kb.audit_ok()
        return jsonify({"pending": c.get("Pending", 0), "approved": c.get("Approved", 0), "rejected": c.get("Rejected", 0),
                        "coverage": kb.coverage(), "audit_ok": ok, "audit_entries": len(kb.audit_entries()),
                        "reviewer_name": kb.reviewer_name(), "require_second_reviewer": kb.second_reviewer_required(),
                        "global_sources": kb.global_sources(),
                        "fields": {f: {"type": t, "pillar": p, "label": lbl} for f, (t, p, lbl) in kb.FIELDS.items()}})

    @app.get("/api/review/audit")
    def review_audit():
        try:
            limit = max(1, min(1000, int(request.args.get("limit", "100"))))
        except ValueError:
            limit = 100
        entries = kb.audit_entries()
        ok, bad = kb.audit_ok()
        return jsonify({"entries": entries[:limit], "total": len(entries), "ok": ok, "first_bad_index": bad})

    # ------------------------------------------------------------------ propose
    @app.post("/api/review/proposals")
    def review_propose():
        data = _body()
        who, err = _who()
        if err:
            return err
        code = _clean(data.get("country_code"), 3).upper()
        if code not in db.COUNTRIES_DB:
            return _err("Unknown country_code")
        raw = data.get("changes")
        if not isinstance(raw, dict) or not raw:
            return _err("changes must be a non-empty object {field: value}")
        changes = {}
        for f, v in raw.items():
            if f not in kb.FIELDS:
                return _err(f"Field '{f}' cannot be changed. Allowed: {', '.join(kb.FIELDS)}")
            nv, e = kb.normalise_value(f, v)
            if e:
                return _err(e)
            if nv == kb.current_value(code, f):
                return _err(f"'{f}' already has that value")
            changes[f] = nv
        reason = _clean(data.get("reason"), 1000)
        if not reason:
            return _err("A reason is required")
        url = _clean(data.get("source_url"), 500)
        if not kb.is_http_url(url):
            return _err("A source URL (http/https) is required so the change can be checked")
        item = kb.enqueue_change(code, changes, reason, url, _clean(data.get("source_label"), 120), who)
        kb.audit_append(who, "propose_change", item["id"], code, {f: x["before"] for f, x in item["payload"]["changes"].items()},
                        changes, reason)
        return jsonify({"success": True, "item": item}), 201

    # ------------------------------------------------------------------ approve / reject
    def _load_pending(item_id):
        it = kb.find_item(item_id)
        if not it:
            return None, _err("Review item not found", 404)
        if it.get("status") != "Pending":
            return None, _err(f"Item is already {it.get('status')}", 409)
        return it, None

    @app.post("/api/review/queue/<item_id>/approve")
    def review_approve(item_id):
        data = _body()
        item, err = _load_pending(item_id)
        if err:
            return err
        who, err = _who()
        if err:
            return err
        if kb.second_reviewer_required() and who.lower() == str(item.get("proposed_by") or "").strip().lower():
            return _err("A second reviewer is required: the approver must differ from the person who proposed this item")
        note = _clean(data.get("note"), 500)
        if item["type"] == "kb_change":
            p = item["payload"]
            code = p["country_code"]
            if code not in db.COUNTRIES_DB:
                return _err("Country no longer exists", 404)
            changes = {f: x["after"] for f, x in p["changes"].items()}
            diff = kb.set_overrides(code, changes)
            pillars = sorted({kb.FIELDS[f][1] for f in changes})
            for scope in pillars:
                kb.set_verification(code, scope, "Verified", item.get("source_url"), p.get("source_label") or "Source cited in approved change",
                                    f"Approved change {item['id']}: {p.get('reason', '')}"[:500], who)
            kb.audit_append(who, "approve_change", item["id"], code, {f: d["before"] for f, d in diff.items()},
                            {f: d["after"] for f, d in diff.items()}, f"Verified: {', '.join(pillars)}. {note}".strip())
        elif item["type"] == "surveillance_notice":
            event = dict(item["payload"])
            event.pop("alert", None)
            event["status"] = "Approved by human review"
            event["reviewed_by"] = who
            event["review_item_id"] = item["id"]
            applied = surveillance.apply_approved_event(event)
            kb.audit_append(who, "approve_notice", item["id"], event.get("country_code"), None,
                            {"event_id": event.get("event_id"), "alert_id": (applied.get("alert") or {}).get("id"),
                             "standard": event.get("new_standard")}, note or event.get("summary", ""))
        else:
            return _err("Unsupported item type")
        item = kb.decide(item_id, "Approved", who, note)
        return jsonify({"success": True, "item": item})

    @app.post("/api/review/queue/<item_id>/reject")
    def review_reject(item_id):
        data = _body()
        item, err = _load_pending(item_id)
        if err:
            return err
        note = _clean(data.get("note"), 500)
        if not note:
            return _err("A note explaining the rejection is required")
        who, err = _who()
        if err:
            return err
        item = kb.decide(item_id, "Rejected", who, note)
        payload = item.get("payload") or {}
        kb.audit_append(who, "reject_change" if item["type"] == "kb_change" else "reject_notice", item_id,
                        payload.get("country_code"), None, None, note)
        return jsonify({"success": True, "item": item})

    # ------------------------------------------------------------------ verification / overrides
    @app.post("/api/verification/<code>")
    def review_verify(code):
        code = code.upper()
        if code not in db.COUNTRIES_DB:
            return _err("Country not found", 404)
        data = _body()
        who, err = _who()
        if err:
            return err
        scope = data.get("scope")
        if scope not in kb.SCOPES:
            return _err(f"scope must be one of {', '.join(kb.SCOPES)}")
        status = data.get("status", "Verified")
        if status not in kb.VERIFY_STATUSES:
            return _err("status must be 'Verified' or 'Needs review'")
        url = _clean(data.get("source_url"), 500)
        if status == "Verified" and not kb.is_http_url(url):
            return _err("A citation URL (http/https) is required to mark a record Verified")
        if url and not kb.is_http_url(url):
            return _err("source_url must be an http/https URL")
        before, entry = kb.set_verification(code, scope, status, url, _clean(data.get("source_label"), 120), _clean(data.get("note"), 500), who)
        kb.audit_append(who, "set_verification", None, code, (before or {}).get("status", "Unverified"), f"{scope}: {status}",
                        f"{url} {entry['note']}".strip())
        return jsonify({"success": True, "entry": entry, "verification": kb.verification_for(code)})

    @app.delete("/api/overrides/<code>/<field>")
    def review_revert_override(code, field):
        code = code.upper()
        if code not in db.COUNTRIES_DB:
            return _err("Country not found", 404)
        if field not in kb.FIELDS:
            return _err("Unknown field")
        who, err = _who()
        if err:
            return err
        diff = kb.revert_override(code, field)
        if diff is None:
            return _err("No override exists for that field", 404)
        scope = kb.FIELDS[field][1]
        prev = (kb.verification_data().get(code) or {}).get(scope)
        if prev and prev.get("status") == "Verified":
            kb.set_verification(code, scope, "Needs review", prev.get("source_url"), prev.get("source_label"),
                                f"Override on {field} reverted to the shipped value; re-check the record.", who)
        kb.audit_append(who, "revert_override", None, code, {field: diff["before"]}, {field: diff["after"]}, "Restored shipped seed value")
        return jsonify({"success": True, "restored": diff, "verification": kb.verification_for(code)})
