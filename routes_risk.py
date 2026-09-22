"""
routes_risk.py - Compliance Risk Index, Regulatory Horizon, certificate health and
Product Portfolio endpoints (see docs/ARCHITECTURE_CONTRACT.md §4 "Risk").

  GET /api/risk/summary
  GET /api/horizon?days=365&types=alert_deadline,milestone,cert_expiry,action_due,surveillance&pillar=&product_id=
  GET /api/horizon/export.csv?...same filters
  GET /api/certificates/health
  GET /api/portfolio
  GET /api/portfolio/<product_id>
"""
import csv
import datetime as _dt
import io

from flask import Response, jsonify, request

import risk_engine

HORIZON_TYPES = ("alert_deadline", "milestone", "cert_expiry", "action_due", "surveillance")


def _q(name, default=""):
    return (request.args.get(name, default) or "").strip()


def _horizon_params():
    days_raw = _q("days", "365").lower()
    if days_raw in ("all", "0", "any", ""):
        days = 0
    else:
        try:
            days = max(0, min(3650, int(float(days_raw))))
        except ValueError:
            raise ValueError("days must be an integer number of days, or 'all'")
    types = [t.strip() for t in _q("types").split(",") if t.strip()]
    bad = [t for t in types if t not in HORIZON_TYPES]
    if bad:
        raise ValueError(f"Unknown horizon type(s): {', '.join(bad)}. Valid: {', '.join(HORIZON_TYPES)}")
    pillar = _q("pillar")
    if pillar.lower() == "all":
        pillar = ""
    if pillar and pillar not in ("Safety", "EMC", "Environmental", "Cyber", "All"):
        raise ValueError("pillar must be one of Safety, EMC, Environmental, Cyber, All")
    product_id = _q("product_id")
    if product_id.lower() == "all":
        product_id = ""
    return days, types, pillar, product_id


def register(app, ctx):
    store = ctx["store"]
    surveillance = ctx.get("surveillance")
    db = ctx["db"]

    @app.get("/api/risk/summary")
    def risk_summary():
        return jsonify(risk_engine.compute_risk_summary(store, db, surveillance))

    @app.get("/api/horizon")
    def risk_horizon():
        try:
            days, types, pillar, product_id = _horizon_params()
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        if product_id and not any(p.get("id") == product_id for p in store.products()):
            return jsonify({"error": f"Product '{product_id}' not found"}), 404
        return jsonify(risk_engine.build_horizon(store, db, surveillance=surveillance, days=days, types=types or None,
                                                 pillar=pillar or None, product_id=product_id or None))

    @app.get("/api/horizon/export.csv")
    def risk_horizon_export():
        try:
            days, types, pillar, product_id = _horizon_params()
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        data = risk_engine.build_horizon(store, db, surveillance=surveillance, days=days, types=types or None,
                                         pillar=pillar or None, product_id=product_id or None)
        products = {p.get("id"): p for p in store.products()}
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["Date", "Days remaining", "Bucket", "Type", "Severity", "Title", "Detail", "Jurisdiction", "Pillar",
                    "Products impacted", "Product SKUs", "Reference type", "Reference id"])
        for e in data["events"]:
            skus = "; ".join(str((products.get(pid) or {}).get("sku") or pid) for pid in (e.get("product_ids") or []))
            w.writerow([e.get("date"), e.get("days_remaining"), e.get("bucket", ""), e.get("type"), e.get("severity"), e.get("title"),
                        e.get("subtitle", ""), e.get("country", ""), e.get("pillar") or "", e.get("product_count", 0), skus,
                        e.get("ref_type"), e.get("ref_id")])
        stamp = _dt.date.today().isoformat()
        suffix = "all" if not days else f"{days}d"
        filename = f"GCM_Regulatory_Horizon_{suffix}_{stamp}.csv"
        return Response("﻿" + buf.getvalue(), mimetype="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})

    @app.get("/api/certificates/health")
    def risk_certificates_health():
        data = risk_engine.certificate_health(store)
        status = _q("status").lower()
        product_id = _q("product_id")
        if status and status != "all":
            data["certificates"] = [c for c in data["certificates"] if str(c.get("status", "")).lower() == status]
        if product_id and product_id != "all":
            data["certificates"] = [c for c in data["certificates"] if c.get("product_id") == product_id]
        data["count"] = len(data["certificates"])
        return jsonify(data)

    @app.get("/api/portfolio")
    def risk_portfolio():
        data = risk_engine.portfolio(store, db)
        category = _q("category")
        search = _q("search").lower()
        if category and category != "all":
            data["products"] = [p for p in data["products"] if p.get("category_id") == category]
        if search:
            data["products"] = [p for p in data["products"] if search in f"{p.get('name', '')} {p.get('sku', '')} {p.get('category_name', '')} {p.get('controller', '')}".lower()]
        data["count"] = len(data["products"])
        return jsonify(data)

    @app.get("/api/portfolio/<product_id>")
    def risk_portfolio_detail(product_id):
        detail = risk_engine.product_detail(store, db, product_id, surveillance=surveillance)
        if not detail:
            return jsonify({"error": f"Product '{product_id}' not found"}), 404
        return jsonify(detail)
