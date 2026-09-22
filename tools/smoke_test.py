"""
Integration smoke test for the GCM Platform 2.0 API.

Usage:  python tools/smoke_test.py [base_url]     (default http://127.0.0.1:5000)
Exits non-zero if any check fails. Read-only except for a few reversible writes
(an action item that is deleted again, a triage change that is reverted).
"""
import json
import sys
import time

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
FAILS = []


def check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}{(' - ' + str(detail)[:160]) if detail and not cond else ''}")
    if not cond:
        FAILS.append(label)


def get(path, **kw):
    return requests.get(BASE + path, timeout=kw.pop("timeout", 60), **kw)


def post(path, body=None, **kw):
    return requests.post(BASE + path, json=body if body is not None else {}, timeout=kw.pop("timeout", 120), **kw)


def keys(d, *ks):
    return all(k in d for k in ks)


def main():
    for _ in range(30):
        try:
            get("/api/health", timeout=3)
            break
        except Exception:
            time.sleep(1)

    # ---- core
    h = get("/api/health").json()
    check("health", h.get("status") == "ok" and h.get("countries") == 205, h)
    ov = get("/api/overview").json()
    check("overview shape", keys(ov, "total_countries", "active_alerts_count", "regions_count", "recent_alerts", "pillar_counts", "triage_counts"), list(ov)[:10])
    cats = get("/api/categories").json()
    check("categories = 11", isinstance(cats, list) and len(cats) == 11)
    m = get("/api/gma/by-product?category=external_ssd_powered&type=testing").json()
    check("matrix testing filter", m.get("countries_count", 0) > 0 and all("Testing Required" in c["requirement_type"] for c in m["countries"]))
    check("matrix bad category -> 400", get("/api/gma/by-product?category=nope").status_code == 400)
    x = get("/api/gma/export-excel?category=sd_card&export_all=true")
    check("matrix excel", x.status_code == 200 and x.headers.get("Content-Type", "").startswith("application/vnd.openxml") and len(x.content) > 10000)
    cl = get("/api/countries").json()
    check("countries list 205", isinstance(cl, list) and len(cl) == 205)
    cd = get("/api/countries/IN").json()
    check("country detail", keys(cd, "country", "category_rules", "alerts", "products") and len(cd["category_rules"]) == 11)
    check("country 404", get("/api/countries/ZZ").status_code == 404)
    check("products list", len(get("/api/products").json()) >= 11)
    check("certificates list", len(get("/api/certificates").json()) >= 11)
    st = get("/api/settings").json()
    check("settings", keys(st, "company_name", "ai_model", "data_dir", "version"))
    s = get("/api/search?q=india").json()
    check("search", any(r["type"] == "country" for r in s.get("results", [])) and any(r["type"] == "alert" for r in s.get("results", [])))

    # ---- actions (create -> patch -> delete)
    a = post("/api/actions", {"title": "smoke-test action", "priority": "Low"})
    check("action create 201", a.status_code == 201, a.text)
    aid = a.json().get("action", {}).get("id")
    if aid:
        check("action patch", requests.patch(BASE + f"/api/actions/{aid}", json={"status": "Done"}, timeout=30).status_code == 200)
        check("action bad status 400", requests.patch(BASE + f"/api/actions/{aid}", json={"status": "x"}, timeout=30).status_code == 400)
        check("action delete", requests.delete(BASE + f"/api/actions/{aid}", timeout=30).status_code == 200)

    # ---- surveillance
    sv = get("/api/surveillance/status").json()
    check("surveillance status", sv.get("engine_state") == "ACTIVE_LISTENING" and sv.get("ledger_ok") is True, sv)
    lg = get("/api/surveillance/log?limit=5").json()
    check("ledger verified", lg.get("ledger_ok") is True and lg.get("ledger_entries", 0) >= 3)
    check("simulate bad country 400", post("/api/surveillance/simulate", {"country_code": "ZZ"}).status_code == 400)

    # ---- alerts
    al = get("/api/alerts")
    check("alerts list", al.status_code == 200 and isinstance(al.json(), list) and len(al.json()) >= 17, al.status_code)
    alerts = al.json() if al.status_code == 200 else []
    if alerts:
        a0 = alerts[0]
        check("alert enriched", keys(a0, "triage", "days_to_effective", "pillar", "impacted_products"), list(a0)[:20])
        for aud in ("simple", "executive", "engineer"):
            r = get(f"/api/alerts/ALERT-2026-03/explain?audience={aud}", timeout=120)
            ok = r.status_code == 200
            d = r.json() if ok else {}
            need = ["headline", "one_liner", "what_changed", "why_it_matters", "who_is_affected", "what_to_do", "deadlines",
                    "cost_effort_estimate", "risk_if_ignored", "jargon_glossary", "confidence", "sources", "suggested_questions", "generated_by"]
            missing = [k for k in need if k not in d]
            check(f"explain {aud}", ok and not missing and d["who_is_affected"].get("products") is not None and len(d["what_to_do"]) >= 3, missing or r.text[:200])
        check("explain 404", get("/api/alerts/NOPE/explain").status_code == 404)
        tr = requests.patch(BASE + "/api/alerts/ALERT-2026-03/triage", json={"status": "Acknowledged", "owner": "smoke"}, timeout=30)
        check("triage patch", tr.status_code == 200 and tr.json().get("triage", {}).get("status") == "Acknowledged", tr.text[:200])
        requests.patch(BASE + "/api/alerts/ALERT-2026-03/triage", json={"status": "New", "owner": ""}, timeout=30)
        check("triage bad 400", requests.patch(BASE + "/api/alerts/ALERT-2026-03/triage", json={"status": "Bogus"}, timeout=30).status_code == 400)
        q = post("/api/alerts/ALERT-2026-03/expert-chat", {"question": "Do we need in-country testing for bus-powered SSDs?"}, timeout=120)
        check("expert chat", q.status_code == 200 and q.json().get("expert_answer") or q.json().get("answer"), q.text[:200])
        check("expert chat empty 400", post("/api/alerts/ALERT-2026-03/expert-chat", {"question": ""}).status_code == 400)
        bad = post("/api/alerts", {"title": ""})
        check("create alert validation 400", bad.status_code == 400, bad.text[:200])
        ai = get("/api/ai/status").json()
        check("ai status", keys(ai, "enabled", "configured", "model"), ai)

    # ---- risk / horizon / portfolio
    rs = get("/api/risk/summary")
    check("risk summary", rs.status_code == 200 and keys(rs.json(), "compliance_risk_index", "grade", "per_product", "per_region", "per_pillar", "top_risks") and 0 <= rs.json()["compliance_risk_index"] <= 100, rs.text[:200])
    hz = get("/api/horizon?days=365")
    check("horizon", hz.status_code == 200 and keys(hz.json(), "events", "buckets") and all(k in hz.json()["buckets"] for k in ("overdue", "next_30", "next_90", "next_365", "beyond")), hz.text[:200])
    ch = get("/api/certificates/health")
    check("certificate health", ch.status_code == 200 and keys(ch.json(), "certificates", "expiring_90", "expired", "valid"), ch.text[:200])
    pf = get("/api/portfolio")
    check("portfolio", pf.status_code == 200 and len(pf.json().get("products", [])) >= 11 and keys(pf.json()["products"][0], "risk_score", "readiness"), pf.text[:200])
    rd = post("/api/gma/readiness", {"product_id": "PROD-009", "countries": ["IN", "US", "DE"]})
    check("readiness", rd.status_code == 200 and len(rd.json().get("evaluations", [])) == 3, rd.text[:200])
    eco = post("/api/eco/analyze", {"category_id": "external_ssd_powered", "component_type": "power_adapter", "target_countries": ["IN", "US"]})
    check("eco analyze", eco.status_code == 200 and eco.json().get("overall_severity") == "Critical", eco.text[:200])

    # ---- documents
    gs = post("/api/documents/generate-samples", {"target_dir": "C:\\GCM Tool\\.devdata\\smoke_samples"}, timeout=180)
    check("generate samples", gs.status_code == 200 and gs.json().get("report", {}).get("total_documents", 0) >= 6, gs.text[:200])
    rep = post("/api/documents/scan-folder", {"folder_path": "C:\\GCM Tool\\.devdata\\smoke_samples"}, timeout=180)
    ok = rep.status_code == 200
    d = rep.json() if ok else {}
    check("scan report shape", ok and keys(d, "health_score", "health_grade", "tier_summary", "documents", "gap_analysis", "remediation_plan", "cost_rollup", "standards_index"), rep.text[:200])
    if ok and d.get("documents"):
        m0 = d["documents"][0]
        check("document record shape", keys(m0, "metadata", "impact") and keys(m0["impact"], "impact_tier", "rationale", "cost_low", "cost_high"), list(m0.get("impact", {}))[:20])
        tiers = {x["impact"]["impact_tier"] for x in d["documents"]}
        check("tiers demonstrated", {"retesting_required", "doc_amendment", "packaging_update", "compliant"} <= tiers, tiers)
        ex = post("/api/documents/explain", {"index": 0})
        check("document explain", ex.status_code == 200 and ex.json().get("plain_english"), ex.text[:200])
    check("scan bad folder 400", post("/api/documents/scan-folder", {"folder_path": "C:\\definitely\\not\\here"}).status_code == 400)
    xa = get("/api/documents/export-audit")
    check("audit excel", xa.status_code == 200 and len(xa.content) > 8000)
    lr = get("/api/documents/last-report")
    check("last report", lr.status_code == 200 and "documents" in lr.json())

    print("\n" + ("ALL CHECKS PASSED" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}"))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
