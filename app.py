import os
import sys
import json
from flask import Flask, render_template, request, jsonify, send_file
import compliance_db as db
import excel_export
import reg_surveillance

surveillance_engine = reg_surveillance.get_surveillance_engine(db)

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    bundle_dir = sys._MEIPASS
    app = Flask(__name__, 
                template_folder=os.path.join(bundle_dir, "templates"), 
                static_folder=os.path.join(bundle_dir, "static"))
else:
    app = Flask(__name__, template_folder="templates", static_folder="static")

# In-memory working copies of data (can be modified at runtime)
products_store = list(db.SAMPLE_PRODUCTS)
certificates_store = list(db.SAMPLE_CERTIFICATES)
alerts_store = list(db.REGULATION_ALERTS)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/overview")
def api_overview():
    total_countries = len(db.COUNTRIES_DB)
    total_categories = len(db.PRODUCT_CATEGORIES)
    total_products = len(products_store)
    total_certificates = len(certificates_store)
    critical_alerts = sum(1 for a in alerts_store if a.get("severity") == "Critical")
    expiring_certs = sum(1 for c in certificates_store if c.get("status") in ["Expiring Soon", "Critical", "Expired"])

    # Regional distribution count
    regions_count = {}
    for c in db.COUNTRIES_DB.values():
        reg = c.get("region", "Other")
        regions_count[reg] = regions_count.get(reg, 0) + 1

    return jsonify({
        "total_countries": total_countries,
        "total_categories": total_categories,
        "total_products": total_products,
        "total_certificates": total_certificates,
        "active_alerts_count": len(alerts_store),
        "critical_alerts_count": critical_alerts,
        "expiring_certificates_count": expiring_certs,
        "regions_count": regions_count,
        "recent_alerts": alerts_store[:4],
        "expiring_certificates": [c for c in certificates_store if c.get("status") in ["Expiring Soon", "Critical", "Expired"]]
    })

@app.route("/api/categories")
def api_categories():
    return jsonify(list(db.PRODUCT_CATEGORIES.values()))

@app.route("/api/gma/by-product")
def api_gma_by_product():
    cat_id = request.args.get("category", "external_ssd_powered").strip()
    type_filter = request.args.get("type", "all").strip().lower()
    region = request.args.get("region", "all").strip().lower()
    search = request.args.get("search", "").strip().lower()

    breakdown = db.get_product_market_breakdown(cat_id)

    filtered_countries = []
    for c in breakdown["countries"]:
        req_type = c["requirement_type"]
        if type_filter != "all" and type_filter != "":
            if type_filter == "testing" and "Testing Required" not in req_type:
                continue
            elif type_filter == "document" and "Document Required" not in req_type:
                continue
            elif type_filter == "sdoc" and ("Supplier Declaration" not in req_type and "Exempt" not in req_type):
                continue
        if region != "all" and region != "" and region not in c["region"].lower():
            continue
        if search:
            match = (
                search in c["country_name"].lower() or
                search in c["country_code"].lower() or
                search in c["authority"].lower() or
                search in c.get("safety_std", "").lower() or
                search in c.get("national_safety_std", "").lower() or
                search in c.get("emc_std", "").lower() or
                search in c.get("env_std", "").lower() or
                any(search in d.lower() for d in c["required_documents"]) or
                any(search in m.lower() for m in c["marks"])
            )
            if not match:
                continue
        filtered_countries.append(c)

    return jsonify({
        "category_id": breakdown["category_id"],
        "category_name": breakdown["category_name"],
        "summary": breakdown["summary"],
        "countries_count": len(filtered_countries),
        "countries": filtered_countries
    })

@app.route("/api/gma/export-excel")
def api_export_excel():
    category_id = request.args.get("category", "external_ssd_powered").strip()
    type_filter = request.args.get("type", "all").strip()
    region = request.args.get("region", "all").strip()
    search = request.args.get("search", "").strip()
    export_all = request.args.get("export_all", "false").strip().lower() == "true"

    buf, filename = excel_export.export_product_matrix_excel(
        category_id=category_id,
        type_filter=type_filter,
        region_filter=region,
        search=search,
        export_all=export_all
    )

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/api/countries")
def api_countries():
    region_filter = request.args.get("region", "").strip().lower()
    bloc_filter = request.args.get("bloc", "").strip().lower()
    query = request.args.get("search", "").strip().lower()

    filtered = []
    for c in db.COUNTRIES_DB.values():
        if region_filter and region_filter != "all":
            if c.get("region", "").lower() != region_filter:
                continue
        if bloc_filter and bloc_filter != "all":
            if bloc_filter not in c.get("bloc", "").lower():
                continue
        if query:
            match = (
                query in c.get("name", "").lower() or
                query in c.get("code", "").lower() or
                query in c.get("authority", "").lower() or
                any(query in m.lower() for m in c.get("marks", []))
            )
            if not match:
                continue
        filtered.append(c)

    # Sort alphabetically by country name
    filtered.sort(key=lambda x: x.get("name", ""))
    return jsonify(filtered)

@app.route("/api/countries/<code>")
def api_country_detail(code):
    country = db.COUNTRIES_DB.get(code.upper())
    if not country:
        return jsonify({"error": "Country not found"}), 404

    # Calculate compliance behavior for all 11 product categories in this country
    category_rules = {}
    for cat_id, cat in db.PRODUCT_CATEGORIES.items():
        if cat_id == "external_ssd_powered":
            req_type = "Mandatory Safety & EMC"
            lead_time = f"{country.get('lead_time_weeks', 6)} weeks"
            notes = f"Requires safety certification under {country.get('safety_std')} + EMC under {country.get('emc_std')}. Energy efficiency required for external AC adapter."
            is_exempt = False
        elif cat_id in ["internal_ssd", "enterprise_ssd"]:
            req_type = "Component Safety & EMC"
            lead_time = "2-4 weeks"
            notes = "Treated as component inside host system. Requires EMC compliance and UL/CB recognition report."
            is_exempt = False
        elif cat_id == "sd_express":
            req_type = "High-Speed EMC & Thermal Review"
            lead_time = "2-3 weeks"
            notes = "High-frequency radiated emissions (PCIe clock harmonics) reviewed under CISPR 32 Class B. SELV safety."
            is_exempt = False
        else:
            # Bus-powered flash cards / USB drives / readers
            req_type = "EMC Class B & RoHS (SDoC)"
            lead_time = "1-2 weeks"
            notes = f"Exempt from mains safety. Requires EMC Class B ({country.get('emc_std')}) and environmental compliance ({country.get('env_std')})."
            is_exempt = True

        category_rules[cat_id] = {
            "category_name": cat["name"],
            "requirement_type": req_type,
            "is_exempt_from_mains_safety": is_exempt,
            "applicable_marks": country.get("marks", []),
            "lead_time": lead_time,
            "notes": notes
        }

    return jsonify({
        "country": country,
        "category_rules": category_rules
    })

@app.route("/api/alerts")
def api_alerts():
    category = request.args.get("category", "").strip().lower()
    severity = request.args.get("severity", "").strip().lower()
    region = request.args.get("region", "").strip().lower()
    search = request.args.get("search", "").strip().lower()

    results = []
    for a in alerts_store:
        if severity and severity != "all" and a.get("severity", "").lower() != severity:
            continue
        if region and region != "all" and region not in a.get("region", "").lower():
            continue
        if category and category != "all":
            if category not in a.get("affected_categories", []):
                continue
        if search:
            match = (
                search in a.get("title", "").lower() or
                search in a.get("summary", "").lower() or
                search in a.get("detailed_summary", "").lower() or
                search in a.get("technical_impact", "").lower() or
                search in a.get("standard", "").lower() or
                search in a.get("country", "").lower() or
                search in a.get("source", "").lower()
            )
            if not match:
                continue
        results.append(a)

    return jsonify(results)

@app.route("/api/alerts", methods=["POST"])
def api_create_alert():
    data = request.json or {}
    new_alert = {
        "id": f"ALERT-2026-{len(alerts_store)+1:02d}",
        "title": data.get("title", "Regulatory Update"),
        "region": data.get("region", "Global"),
        "country": data.get("country", "Global"),
        "standard": data.get("standard", "General Regulation"),
        "severity": data.get("severity", "Warning"),
        "effective_date": data.get("effective_date", "2026-12-31"),
        "affected_categories": data.get("affected_categories", list(db.PRODUCT_CATEGORIES.keys())),
        "summary": data.get("summary", "New regulatory bulletin logged."),
        "action_required": data.get("action_required", "Review product compliance file."),
        "status": "Active Advisory",
        "source": data.get("source", "Internal Regulatory Intelligence"),
        "detailed_summary": data.get("detailed_summary") or data.get("summary") or "Detailed technical brief logged for internal regulatory assessment.",
        "technical_impact": data.get("technical_impact") or f"Pillar requirements: {data.get('standard', 'General Standard')}. Audit BOM components and product marking.",
        "timeline_milestones": data.get("timeline_milestones") or [
            {"phase": "Advisory Notification Published", "date": data.get("effective_date", "2026-09-11"), "status": "Active"},
            {"phase": "Mandatory Technical Cutover", "date": data.get("effective_date", "2026-12-31"), "status": "Enforcement Deadline"}
        ],
        "official_links": data.get("official_links") or [
            {"label": "Regulatory Body Official Gazette Portal", "url": f"https://www.google.com/search?q={data.get('country', 'Global')}+{data.get('standard', 'Standard')}"}
        ],
        "compliance_checklist": data.get("compliance_checklist") or [
            f"Review testing requirements against {data.get('standard', 'standard')}",
            "Perform gap assessment on current technical file and reports",
            "Update Declaration of Conformity and regional distributor packaging"
        ]
    }
    alerts_store.insert(0, new_alert)
    return jsonify({"success": True, "alert": new_alert})

@app.route("/api/products")
def api_products():
    return jsonify(products_store)

@app.route("/api/products", methods=["POST"])
def api_create_product():
    data = request.json or {}
    cat_id = data.get("category_id", "sd_card")
    cat = db.PRODUCT_CATEGORIES.get(cat_id, {})
    new_prod = {
        "id": f"PROD-{len(products_store)+1:03d}",
        "sku": data.get("sku", "NEW-SKU-001"),
        "name": data.get("name", "New Storage Device"),
        "category_id": cat_id,
        "category_name": cat.get("name", cat_id),
        "hw_revision": data.get("hw_revision", "Rev A.0"),
        "controller": data.get("controller", "Standard Controller ASIC"),
        "nand": data.get("nand", "3D NAND Flash"),
        "power_source": cat.get("power_type", "Bus-powered"),
        "target_markets": data.get("target_markets", ["US", "DE", "JP", "GB", "CN", "IN"]),
        "compliance_status": "Planning / Scoping",
        "active_certs_count": 0,
        "readiness_pct": 0
    }
    products_store.append(new_prod)
    return jsonify({"success": True, "product": new_prod})

@app.route("/api/certificates")
def api_certificates():
    status = request.args.get("status", "").strip().lower()
    prod_id = request.args.get("product_id", "").strip()
    search = request.args.get("search", "").strip().lower()

    results = []
    for c in certificates_store:
        if status and status != "all" and c.get("status", "").lower() != status:
            continue
        if prod_id and prod_id != "all" and c.get("product_id") != prod_id:
            continue
        if search:
            match = (
                search in c.get("cert_no", "").lower() or
                search in c.get("scheme", "").lower() or
                search in c.get("product_name", "").lower() or
                search in c.get("country_coverage", "").lower()
            )
            if not match:
                continue
        results.append(c)

    return jsonify(results)

@app.route("/api/certificates", methods=["POST"])
def api_create_certificate():
    data = request.json or {}
    new_cert = {
        "id": f"CERT-{len(certificates_store)+1:03d}",
        "cert_no": data.get("cert_no", "NEW-CERT-000"),
        "scheme": data.get("scheme", "CE Declaration of Conformity"),
        "standard": data.get("standard", "EN 62368-1 / EN 55032"),
        "issuing_body": data.get("issuing_body", "Accredited Lab / Self-Declaration"),
        "product_id": data.get("product_id", "PROD-001"),
        "product_name": data.get("product_name", "Storage Product"),
        "country_coverage": data.get("country_coverage", "Global"),
        "issue_date": data.get("issue_date", "2026-01-01"),
        "expiry_date": data.get("expiry_date", "2029-01-01"),
        "status": data.get("status", "Valid"),
        "document_type": data.get("document_type", "Test Certificate"),
        "notes": data.get("notes", "")
    }
    certificates_store.append(new_cert)
    return jsonify({"success": True, "certificate": new_cert})

@app.route("/api/eco/analyze", methods=["POST"])
def api_eco_analyze():
    data = request.json or {}
    category_id = data.get("category_id", "external_ssd_powered")
    component_type = data.get("component_type", "power_adapter")
    change_desc = data.get("change_description", "Component substitution")
    target_countries = data.get("target_countries", ["US", "DE", "FR", "GB", "JP", "KR", "TW", "CN", "IN", "AU", "BR", "MX"])

    if not target_countries:
        target_countries = ["US", "DE", "GB", "JP", "CN", "IN"]

    analysis = db.evaluate_eco_impact(category_id, component_type, change_desc, target_countries)
    return jsonify(analysis)

@app.route("/api/gma/readiness", methods=["POST"])
def api_gma_readiness():
    data = request.json or {}
    product_id = data.get("product_id")
    target_country_codes = data.get("countries", [])

    product = next((p for p in products_store if p["id"] == product_id), None)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    cat_id = product.get("category_id")

    # Evaluate readiness per target country
    country_evals = []
    ready_count = 0

    for code in target_country_codes:
        country = db.COUNTRIES_DB.get(code.upper(), {
            "code": code, "name": code, "region": "Unknown", "marks": ["CE"]
        })

        # Check existing certificates for this product and country
        certs_for_country = [
            c for c in certificates_store
            if c.get("product_id") == product_id and (
                code in c.get("country_coverage", "") or
                "Global" in c.get("country_coverage", "") or
                ("EU" in c.get("country_coverage", "") and country.get("bloc") == "EU / EEA") or
                ("CB Scheme" in c.get("country_coverage", "") and country.get("cb_scheme_accepted"))
            )
        ]

        if certs_for_country and any(c.get("status") == "Valid" for c in certs_for_country):
            status = "Ready / Certified"
            badge = "success"
            ready_count += 1
            action_needed = "All regulatory filings up-to-date."
        elif cat_id in ["sd_card", "micro_sd", "usb_drive"] and not country.get("in_country_testing"):
            # Low-risk SDoC products
            status = "Ready (SDoC Route)"
            badge = "info"
            ready_count += 1
            action_needed = "Standard Declaration of Conformity and RoHS pack in place."
        else:
            status = "Action Required"
            badge = "danger"
            if cat_id == "external_ssd_powered" and country.get("in_country_testing"):
                action_needed = f"Mandatory local safety testing required under {country.get('safety_std')}."
            else:
                action_needed = f"Submit CB Report and apply for {country.get('marks', ['local mark'])[0]} registration."

        country_evals.append({
            "country_code": country.get("code"),
            "country_name": country.get("name"),
            "region": country.get("region"),
            "status": status,
            "badge": badge,
            "action_needed": action_needed,
            "authority": country.get("authority"),
            "required_marks": country.get("marks", [])
        })

    total = len(target_country_codes)
    readiness_pct = round((ready_count / total * 100) if total > 0 else 0)

    return jsonify({
        "product": product,
        "total_target_markets": total,
        "ready_count": ready_count,
        "pending_count": total - ready_count,
        "readiness_percentage": readiness_pct,
        "evaluations": country_evals
    })

# ==========================================
# AUTONOMOUS REGULATORY SURVEILLANCE ROUTES
# ==========================================
@app.route("/api/surveillance/status")
def api_surveillance_status():
    return jsonify(surveillance_engine.get_status())

@app.route("/api/surveillance/scan", methods=["POST"])
def api_surveillance_scan():
    result = surveillance_engine.scan_all_sources()
    global alerts_store
    alerts_store = list(db.REGULATION_ALERTS)
    return jsonify({
        "result": result,
        "status": surveillance_engine.get_status(),
        "alerts_count": len(alerts_store)
    })

@app.route("/api/surveillance/log")
def api_surveillance_log():
    limit = int(request.args.get("limit", 50))
    return jsonify({
        "audit_log": surveillance_engine.get_audit_log(limit=limit),
        "status": surveillance_engine.get_status()
    })

@app.route("/api/surveillance/simulate", methods=["POST"])
def api_surveillance_simulate():
    data = request.get_json() or {}
    cc = data.get("country_code", "IN")
    authority = data.get("authority", "Bureau of Indian Standards")
    new_std = data.get("new_standard", "IS/IEC 62368-1:2023 Amendment 2")
    deadline = data.get("deadline", "2028-11-01")
    summary = data.get("summary", "Official Gazette Notification: Mandating updated safety testing requirements.")
    cats = data.get("affected_categories", ["external_ssd_powered", "external_ssd_bus"])
    source_url = data.get("source_url")
    pillar = data.get("pillar", "Safety")

    event = surveillance_engine.simulate_gazette_update(
        country_code=cc,
        authority=authority,
        new_standard=new_std,
        deadline=deadline,
        summary=summary,
        affected_categories=cats,
        pillar=pillar,
        source_url=source_url
    )
    global alerts_store
    alerts_store = list(db.REGULATION_ALERTS)
    return jsonify({
        "success": True,
        "event": event,
        "status": surveillance_engine.get_status()
    })

if __name__ == "__main__":
    import webbrowser
    import threading

    def open_browser():
        webbrowser.open("http://localhost:5000")

    threading.Timer(1.2, open_browser).start()
    is_frozen = getattr(sys, 'frozen', False)
    app.run(host="0.0.0.0", port=5000, debug=not is_frozen)
