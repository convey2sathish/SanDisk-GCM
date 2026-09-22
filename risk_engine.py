"""
risk_engine.py - Compliance Risk Index, Regulatory Horizon, certificate health and
portfolio readiness for the GCM Platform.

Pure functions: no Flask, no I/O. Everything is derived from the Store (alerts,
triage state, products, certificates, actions), the compliance knowledge base
(compliance_db) and - optionally - the surveillance ledger.

=====================================================================================
COMPLIANCE RISK INDEX - how it is calculated (0 = no exposure, 100 = maximum risk)
=====================================================================================

1. Every open regulatory alert gets a raw score:

       alert_score = severity_weight x urgency x exposure x triage_factor

   severity_weight   Critical 10 | Warning 5 | Info 2
   urgency           overdue (deadline passed) 1.5 | <= 90 days 1.3 | <= 365 days 1.0
                     | > 365 days 0.7 | no usable date 0.8
   exposure          1 + 0.15 x impacted_products + 0.002 x affected_markets, capped at 3.0
   triage_factor     New 1.0 | Acknowledged 0.9 | In Progress 0.6 | Closed 0 (drops out)

2. A product's raw risk is the sum of the alert scores of every alert that hits it
   (category match AND at least one of its target markets is in the alert's scope),
   plus certificate penalties: expired certificate +8, certificate expiring within
   90 days +4 (per certificate).

3. Raw values are mapped onto 0-100 with a soft cap so that a few very large numbers
   cannot saturate the scale:

       risk_score = 100 x (1 - e^(-raw / 200))

   Grades: A < 20, B < 40, C < 60, D < 75, E < 90, F >= 90.

4. The portfolio index blends the market-weighted mean of the product scores
   (weight = number of target markets - a product sold in 17 markets counts more than
   one sold in 6) with the portfolio-wide alert pressure (all open alert scores mapped
   through the same soft cap with divisor 300):

       compliance_risk_index = 0.7 x weighted_mean(product risk) + 0.3 x alert_pressure

   Region and pillar scores use the same soft cap over the alert scores that touch
   them (regions: alert score x share of the region's jurisdictions covered).
"""
import datetime as _dt
import math
import re

try:
    import reg_surveillance as _rs
except Exception:  # pragma: no cover - keeps the module importable in isolation
    _rs = None

SEVERITY_WEIGHT = {"Critical": 10.0, "Warning": 5.0, "Info": 2.0}
TRIAGE_FACTOR = {"New": 1.0, "Acknowledged": 0.9, "In Progress": 0.6, "Closed": 0.0}
CERT_PENALTY_EXPIRED = 8.0
CERT_PENALTY_EXPIRING = 4.0
EXPOSURE_CAP = 3.0
PRODUCT_SOFT_CAP = 200.0
PRESSURE_SOFT_CAP = 300.0
REGION_SOFT_CAP = 60.0
PILLAR_SOFT_CAP = 120.0
GRADE_BANDS = ((20, "A"), (40, "B"), (60, "C"), (75, "D"), (90, "E"), (10 ** 9, "F"))
PRIORITY_SEVERITY = {"Critical": "Critical", "High": "Warning", "Medium": "Info", "Low": "Info"}
UNIVERSAL = ("all", "all_storage_categories", "all_categories")
GLOBAL_CODES = ("ALL", "GLOBAL", "WORLDWIDE", "ALL_COUNTRIES", "INTERNATIONAL")
EU_CODES = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT",
            "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE", "IS", "NO", "LI"}

FORMULA = {
    "title": "Compliance Risk Index (0-100, higher = riskier)",
    "steps": [
        "Each open alert: score = severity weight (Critical 10 / Warning 5 / Info 2) x urgency (overdue 1.5, <=90 d 1.3, <=365 d 1.0, >365 d 0.7, no date 0.8) x exposure (1 + 0.15 x impacted products + 0.002 x markets, capped at 3.0) x triage factor (New 1.0, Acknowledged 0.9, In Progress 0.6, Closed 0).",
        "Each product: raw risk = sum of scores of alerts hitting it (category AND target-market match) + 8 per expired certificate + 4 per certificate expiring within 90 days.",
        "Soft cap onto 0-100: risk = 100 x (1 - e^(-raw / 200)). Grades A < 20, B < 40, C < 60, D < 75, E < 90, F >= 90.",
        "Index = 0.7 x market-weighted mean of product risk (weight = number of target markets) + 0.3 x portfolio alert pressure (all alert scores, soft cap 300).",
        "Regions: alert score x share of the region's jurisdictions in scope, soft cap 60. Pillars: sum of alert scores per pillar, soft cap 120.",
    ],
    "severity_weight": SEVERITY_WEIGHT,
    "triage_factor": TRIAGE_FACTOR,
    "urgency": {"overdue": 1.5, "within_90_days": 1.3, "within_365_days": 1.0, "beyond_365_days": 0.7, "no_date": 0.8},
    "exposure": "1 + 0.15 x impacted_products + 0.002 x affected_markets (cap 3.0)",
    "certificate_penalties": {"expired": CERT_PENALTY_EXPIRED, "expiring_within_90_days": CERT_PENALTY_EXPIRING},
    "soft_cap": "100 x (1 - exp(-raw / 200))",
    "index_blend": "0.7 x weighted product mean + 0.3 x alert pressure",
}


# ------------------------------------------------------------------------------ helpers
def _today():
    return _dt.date.today()


def parse_date(value):
    """Return a date for 'YYYY-MM-DD…' strings, else None (handles 'Enforced', 'Permanent', None)."""
    if not value:
        return None
    s = str(value).strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return None
    try:
        return _dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def days_until(value, today=None):
    d = parse_date(value)
    if d is None:
        return None
    return (d - (today or _today())).days


def _now_iso():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def soft_cap(raw, divisor):
    raw = max(0.0, float(raw or 0))
    return round(100.0 * (1.0 - math.exp(-raw / divisor)), 1)


def grade_for(score):
    for limit, g in GRADE_BANDS:
        if score < limit:
            return g
    return "F"


def urgency_factor(days):
    if days is None:
        return 0.8
    if days < 0:
        return 1.5
    if days <= 90:
        return 1.3
    if days <= 365:
        return 1.0
    return 0.7


def _pillar(alert):
    p = alert.get("pillar")
    if p in ("Safety", "EMC", "Environmental", "Cyber", "All"):
        return p
    if _rs is not None:
        try:
            return _rs.infer_pillar(alert)
        except Exception:
            pass
    return "Safety"


def _pillar_from_text(text):
    if _rs is not None:
        try:
            return _rs.infer_pillar(str(text or ""))
        except Exception:
            pass
    return "Safety"


def _alert_codes(alert, db):
    countries = getattr(db, "COUNTRIES_DB", {}) or {}
    if _rs is not None:
        try:
            return set(_rs._alert_country_codes(alert, countries))
        except Exception:
            pass
    cc = str(alert.get("country_code") or "").upper()
    if cc in GLOBAL_CODES:
        return set(countries.keys())
    return {cc} if cc in countries else set()


def _is_global_scope(alert, codes, db):
    total = len(getattr(db, "COUNTRIES_DB", {}) or {})
    cc = str(alert.get("country_code") or "").upper()
    return cc in GLOBAL_CODES or (total and len(codes) >= total)


def _impacted_products(alert, codes, products, db):
    """Products hit by an alert: category match AND market intersection (category-only when the market is unknown)."""
    cats = alert.get("affected_categories") or []
    if isinstance(cats, str):
        cats = [cats]
    universal = (not cats) or any(c in UNIVERSAL for c in cats)
    global_scope = _is_global_scope(alert, codes, db)
    out = []
    for p in products:
        if not (universal or p.get("category_id") in cats):
            continue
        targets = {str(m).upper() for m in (p.get("target_markets") or [])}
        if global_scope or not codes or not targets or (targets & codes):
            out.append(p)
    return out


def _severity(alert):
    s = str(alert.get("severity") or "Info").title()
    return s if s in SEVERITY_WEIGHT else "Info"


def _cert_status(cert, today=None):
    """Recompute status from expiry date. Returns (status, days_to_expiry)."""
    exp = str(cert.get("expiry_date") or "")
    d = days_until(exp, today)
    if d is None:
        if re.search(r"perman|lifetime|design life|indefinite|n/a", exp, re.I) or not exp:
            return "Valid", None
        return (cert.get("status") if cert.get("status") in ("Valid", "Expiring Soon", "Critical", "Expired") else "Valid"), None
    if d < 0:
        return "Expired", d
    if d <= 30:
        return "Critical", d
    if d <= 90:
        return "Expiring Soon", d
    return "Valid", d


PENDING_WORDS = ("deadline", "upcoming", "cutover", "target", "cutoff", "anticipated", "projected", "future", "mandatory", "sunset")


def _milestone_pending(status):
    """A milestone still counts as a pending deadline when its status reads like one (not 'Completed' / 'Active ...')."""
    st = str(status or "").strip().lower()
    if not st:
        return True
    if st.startswith(("complet", "done", "closed", "active", "recorded", "published", "ongoing", "in progress", "recommended")):
        return False
    return any(w in st for w in PENDING_WORDS)


def _tone_for(severity, days, closed=False):
    if closed:
        return "success"
    if days is not None and days < 0:
        return "critical"
    if severity == "Critical":
        return "critical"
    if severity == "Warning" or (days is not None and days <= 90):
        return "warning"
    return "info"


# ------------------------------------------------------------------------------ core analysis
def _analyse(store, db, today=None):
    """Shared per-alert / per-product analysis used by every public function."""
    today = today or _today()
    products = list(store.products())
    certificates = list(store.certificates())
    states = store.all_alert_states() if hasattr(store, "all_alert_states") else {}
    countries = getattr(db, "COUNTRIES_DB", {}) or {}
    total_countries = max(1, len(countries))

    alerts = []
    for a in store.alerts():
        if not isinstance(a, dict) or not a.get("id"):
            continue
        triage = (states.get(a["id"]) or {}).get("status", "New")
        if triage not in TRIAGE_FACTOR:
            triage = "New"
        codes = _alert_codes(a, db)
        impacted = _impacted_products(a, codes, products, db)
        sev = _severity(a)
        # Informational notices (e.g. live-detected NRTL recognitions) carry a publication date, not a
        # cutover deadline: treat them as "no date" so they never count as overdue enforcement.
        days = None if a.get("no_deadline") else days_until(a.get("effective_date"), today)
        market_count = len(codes)
        exposure = min(EXPOSURE_CAP, 1.0 + 0.15 * len(impacted) + 0.002 * market_count)
        urg = urgency_factor(days)
        score = SEVERITY_WEIGHT[sev] * urg * exposure * TRIAGE_FACTOR[triage]
        alerts.append({
            "alert": a, "id": a["id"], "title": a.get("title") or a["id"], "severity": sev, "pillar": _pillar(a),
            "codes": codes, "market_count": market_count, "global": _is_global_scope(a, codes, db),
            "impacted": impacted, "impacted_ids": [p.get("id") for p in impacted], "triage": triage,
            "days": days, "urgency": urg, "exposure": round(exposure, 3), "score": round(score, 2),
            "open": triage != "Closed", "effective_date": a.get("effective_date"),
            "country": a.get("country") or a.get("region") or "Global", "region": a.get("region") or "Global",
        })

    certs_by_product = {}
    for c in certificates:
        status, d = _cert_status(c, today)
        cc = dict(c)
        cc["declared_status"] = c.get("status")
        cc["status"] = status
        cc["days_to_expiry"] = d
        certs_by_product.setdefault(c.get("product_id"), []).append(cc)

    per_product = []
    for p in products:
        pid = p.get("id")
        hits = [x for x in alerts if x["open"] and pid in x["impacted_ids"]]
        raw = sum(x["score"] for x in hits)
        contributions = [{"kind": "alert", "label": x["title"], "score": x["score"], "ref_id": x["id"], "severity": x["severity"], "due": x["effective_date"]} for x in hits]
        pcerts = certs_by_product.get(pid, [])
        expired = [c for c in pcerts if c["status"] == "Expired"]
        expiring = [c for c in pcerts if c["status"] in ("Critical", "Expiring Soon")]
        for c in expired:
            raw += CERT_PENALTY_EXPIRED
            contributions.append({"kind": "certificate", "label": f"Expired certificate {c.get('cert_no')} ({c.get('scheme')})", "score": CERT_PENALTY_EXPIRED, "ref_id": c.get("id"), "severity": "Critical", "due": c.get("expiry_date")})
        for c in expiring:
            raw += CERT_PENALTY_EXPIRING
            contributions.append({"kind": "certificate", "label": f"Certificate {c.get('cert_no')} expires in {c['days_to_expiry']} days", "score": CERT_PENALTY_EXPIRING, "ref_id": c.get("id"), "severity": "Warning", "due": c.get("expiry_date")})
        contributions.sort(key=lambda x: -x["score"])
        score = soft_cap(raw, PRODUCT_SOFT_CAP)
        upcoming = sorted([x for x in hits if x["days"] is not None and x["days"] >= 0], key=lambda x: x["days"])
        cert_dates = sorted([c for c in pcerts if c["days_to_expiry"] is not None and c["days_to_expiry"] >= 0], key=lambda c: c["days_to_expiry"])
        next_deadline, next_days, next_label = None, None, None
        if upcoming:
            next_deadline, next_days, next_label = upcoming[0]["effective_date"], upcoming[0]["days"], upcoming[0]["title"]
        if cert_dates and (next_days is None or cert_dates[0]["days_to_expiry"] < next_days):
            next_deadline, next_days, next_label = cert_dates[0]["expiry_date"], cert_dates[0]["days_to_expiry"], f"Certificate {cert_dates[0].get('cert_no')} expiry"
        if pcerts:
            if expired:
                cert_health = "Expired"
            elif any(c["status"] == "Critical" for c in pcerts):
                cert_health = "Critical"
            elif expiring:
                cert_health = "Expiring Soon"
            else:
                cert_health = "Valid"
        else:
            cert_health = "No certificates"
        per_product.append({
            "id": pid, "sku": p.get("sku"), "name": p.get("name"), "category_id": p.get("category_id"),
            "category_name": p.get("category_name"), "risk_score": score, "grade": grade_for(score), "raw_score": round(raw, 2),
            "open_alerts": len(hits), "critical_alerts": sum(1 for x in hits if x["severity"] == "Critical"),
            "overdue_alerts": sum(1 for x in hits if x["days"] is not None and x["days"] < 0),
            "next_deadline": next_deadline, "days_to_next_deadline": next_days, "next_deadline_label": next_label,
            "cert_health": cert_health, "certificates_count": len(pcerts),
            "expired_certificates": len(expired), "expiring_certificates": len(expiring),
            "market_count": len(p.get("target_markets") or []),
            "drivers": [{"label": c["label"], "score": round(c["score"], 1), "kind": c["kind"], "ref_id": c["ref_id"], "severity": c["severity"]} for c in contributions[:3]],
            "contributions": contributions,
        })
    per_product.sort(key=lambda x: (-x["risk_score"], x["name"] or ""))

    return {
        "today": today, "products": products, "certificates": certificates, "alerts": alerts,
        "certs_by_product": certs_by_product, "per_product": per_product, "countries": countries,
        "total_countries": total_countries, "states": states,
    }


def _index_from(per_product, alerts):
    weights = [(x["risk_score"], max(1, x["market_count"])) for x in per_product]
    wsum = sum(w for _, w in weights)
    weighted_mean = (sum(s * w for s, w in weights) / wsum) if wsum else 0.0
    pressure = soft_cap(sum(x["score"] for x in alerts if x["open"]), PRESSURE_SOFT_CAP)
    index = 0.7 * weighted_mean + 0.3 * pressure
    return round(max(0.0, min(100.0, index))), round(weighted_mean, 1), pressure


# ------------------------------------------------------------------------------ public API
def compute_risk_summary(store, db, surveillance=None):
    ctx = _analyse(store, db)
    alerts, per_product, countries = ctx["alerts"], ctx["per_product"], ctx["countries"]
    today = ctx["today"]
    open_alerts = [x for x in alerts if x["open"]]
    index, weighted_mean, pressure = _index_from(per_product, alerts)

    # ---- regions
    region_countries = {}
    for code, c in countries.items():
        region_countries.setdefault(c.get("region") or "Other", set()).add(code)
    portfolio_markets = set()
    for p in ctx["products"]:
        portfolio_markets.update(str(m).upper() for m in (p.get("target_markets") or []))
    per_region = []
    for region, codes in sorted(region_countries.items()):
        raw, n_alerts, crit = 0.0, 0, 0
        for x in open_alerts:
            hit = codes if x["global"] else (x["codes"] & codes)
            if not hit:
                continue
            n_alerts += 1
            crit += x["severity"] == "Critical"
            coverage = max(0.2, min(1.0, len(hit) / max(1, len(codes))))
            raw += x["score"] * coverage
        markets = codes & portfolio_markets
        score = soft_cap(raw, REGION_SOFT_CAP)
        per_region.append({
            "region": region, "risk_score": score, "grade": grade_for(score), "alerts": n_alerts, "critical_alerts": crit,
            "markets": len(markets), "market_codes": sorted(markets), "jurisdictions": len(codes),
            "in_country_testing_markets": sum(1 for m in markets if (countries.get(m) or {}).get("in_country_testing")),
        })
    per_region.sort(key=lambda r: -r["risk_score"])

    # ---- pillars
    pillar_raw = {}
    for x in open_alerts:
        d = pillar_raw.setdefault(x["pillar"], {"pillar": x["pillar"], "alerts": 0, "critical": 0, "raw": 0.0, "products": set()})
        d["alerts"] += 1
        d["critical"] += x["severity"] == "Critical"
        d["raw"] += x["score"]
        d["products"].update(x["impacted_ids"])
    per_pillar = []
    for pl in ("Safety", "EMC", "Environmental", "Cyber", "All"):
        d = pillar_raw.get(pl)
        if not d:
            per_pillar.append({"pillar": pl, "alerts": 0, "critical": 0, "risk_score": 0.0, "products_impacted": 0})
            continue
        per_pillar.append({"pillar": pl, "alerts": d["alerts"], "critical": d["critical"], "risk_score": soft_cap(d["raw"], PILLAR_SOFT_CAP), "products_impacted": len(d["products"])})

    # ---- top risks (alerts, certificates, overdue actions)
    top = []
    for x in open_alerts:
        why = []
        if x["days"] is not None and x["days"] < 0:
            why.append(f"deadline passed {-x['days']} days ago")
        elif x["days"] is not None:
            why.append(f"deadline in {x['days']} days")
        else:
            why.append("no firm enforcement date")
        why.append(f"{len(x['impacted_ids'])} product{'s' if len(x['impacted_ids']) != 1 else ''} impacted")
        why.append("all jurisdictions" if x["global"] else f"{x['market_count']} market{'s' if x['market_count'] != 1 else ''}")
        why.append(f"triage: {x['triage']}")
        top.append({"title": x["title"], "score": soft_cap(x["score"], 20.0), "raw": x["score"], "reason": "; ".join(why),
                    "ref_type": "alert", "ref_id": x["id"], "severity": x["severity"], "due": x["effective_date"], "pillar": x["pillar"],
                    "country": x["country"], "product_ids": x["impacted_ids"]})
    for pid, certs in ctx["certs_by_product"].items():
        for c in certs:
            if c["status"] == "Expired":
                raw = 40 + min(20, (-(c["days_to_expiry"] or 0)) / 30)
                top.append({"title": f"Expired: {c.get('scheme')} {c.get('cert_no')}", "score": soft_cap(raw, 20.0), "raw": raw,
                            "reason": f"expired {-(c['days_to_expiry'] or 0)} days ago; {c.get('country_coverage')}; {c.get('product_name')}",
                            "ref_type": "certificate", "ref_id": c.get("id"), "severity": "Critical", "due": c.get("expiry_date"),
                            "pillar": _pillar_from_text(f"{c.get('standard')} {c.get('scheme')}"), "country": c.get("country_coverage"), "product_ids": [pid]})
            elif c["status"] in ("Critical", "Expiring Soon"):
                raw = 25 if c["status"] == "Critical" else 12
                top.append({"title": f"Renewal due: {c.get('scheme')} {c.get('cert_no')}", "score": soft_cap(raw, 20.0), "raw": raw,
                            "reason": f"expires in {c['days_to_expiry']} days; {c.get('country_coverage')}; {c.get('product_name')}",
                            "ref_type": "certificate", "ref_id": c.get("id"), "severity": "Warning" if c["status"] == "Expiring Soon" else "Critical",
                            "due": c.get("expiry_date"), "pillar": _pillar_from_text(f"{c.get('standard')} {c.get('scheme')}"), "country": c.get("country_coverage"), "product_ids": [pid]})
    for a in store.actions():
        if a.get("status") == "Done":
            continue
        d = days_until(a.get("due_date"), today)
        if d is None or d >= 0:
            continue
        pr = a.get("priority") or "Medium"
        raw = {"Critical": 30, "High": 20, "Medium": 12, "Low": 6}.get(pr, 12) + min(15, -d / 7)
        top.append({"title": f"Overdue action: {a.get('title')}", "score": soft_cap(raw, 20.0), "raw": raw,
                    "reason": f"{pr} priority; {-d} days overdue; owner {a.get('owner') or 'unassigned'}; status {a.get('status')}",
                    "ref_type": a.get("linked_type") or "action", "ref_id": a.get("linked_id") or a.get("id"), "action_id": a.get("id"),
                    "severity": PRIORITY_SEVERITY.get(pr, "Info"), "due": a.get("due_date"), "pillar": None, "country": None,
                    "product_ids": [a.get("linked_id")] if a.get("linked_type") == "product" else []})
    top.sort(key=lambda t: (-t["raw"], t["title"]))
    top_risks = [{k: v for k, v in t.items() if k != "raw"} for t in top[:12]]

    # ---- trend note (what-if: triage every New critical alert into "In Progress")
    n_new_crit = sum(1 for x in open_alerts if x["severity"] == "Critical" and x["triage"] == "New")
    overdue = sum(1 for x in open_alerts if x["days"] is not None and x["days"] < 0)
    due_90 = sum(1 for x in open_alerts if x["days"] is not None and 0 <= x["days"] <= 90)
    expired_certs = sum(1 for cs in ctx["certs_by_product"].values() for c in cs if c["status"] == "Expired")
    what_if = None
    if n_new_crit:
        sim_alerts = []
        for x in alerts:
            y = dict(x)
            if y["open"] and y["severity"] == "Critical" and y["triage"] == "New":
                y["score"] = round(y["score"] * TRIAGE_FACTOR["In Progress"], 2)
            sim_alerts.append(y)
        sim_products = []
        for p in per_product:
            raw = sum(y["score"] for y in sim_alerts if y["open"] and p["id"] in y["impacted_ids"])
            raw += p["expired_certificates"] * CERT_PENALTY_EXPIRED + p["expiring_certificates"] * CERT_PENALTY_EXPIRING
            sim_products.append({"risk_score": soft_cap(raw, PRODUCT_SOFT_CAP), "market_count": p["market_count"]})
        what_if, _, _ = _index_from(sim_products, sim_alerts)
    worst = per_product[0] if per_product else None
    worst_pillar = max(per_pillar, key=lambda p: p["risk_score"]) if per_pillar else None
    parts = [f"{len(open_alerts)} open alert{'s' if len(open_alerts) != 1 else ''}"]
    if overdue:
        parts.append(f"{overdue} past enforcement date")
    if due_90:
        parts.append(f"{due_90} due within 90 days")
    if expired_certs:
        parts.append(f"{expired_certs} expired certificate{'s' if expired_certs != 1 else ''}")
    note = ", ".join(parts) + "."
    if worst and worst["risk_score"] > 0:
        note += f" Highest exposure: {worst['name']} ({worst['risk_score']:.0f}, grade {worst['grade']})."
    if worst_pillar and worst_pillar["risk_score"] > 0:
        note += f" Dominant pillar: {worst_pillar['pillar']}."
    if what_if is not None and what_if < index:
        note += f" Triaging the {n_new_crit} untouched critical alert{'s' if n_new_crit != 1 else ''} into 'In Progress' would lower the index to {what_if}."
    elif not open_alerts:
        note = "No open regulatory alerts. The index reflects certificate health only."

    return {
        "compliance_risk_index": index, "grade": grade_for(index),
        "components": {"weighted_product_mean": weighted_mean, "alert_pressure": pressure, "open_alerts": len(open_alerts),
                       "critical_open_alerts": sum(1 for x in open_alerts if x["severity"] == "Critical"),
                       "overdue_alerts": overdue, "due_within_90": due_90, "expired_certificates": expired_certs,
                       "what_if_triage_index": what_if},
        "trend_note": note, "formula": FORMULA,
        "per_product": [{k: v for k, v in p.items() if k != "contributions"} for p in per_product],
        "per_region": per_region, "per_pillar": per_pillar, "top_risks": top_risks,
        "generated_at": _now_iso(),
    }


def build_horizon(store, db, surveillance=None, days=365, types=None, pillar=None, product_id=None):
    """Regulatory horizon: every dated item that matters, sorted ascending, bucketed."""
    ctx = _analyse(store, db)
    today = ctx["today"]
    try:
        days = int(days) if days is not None else 365
    except (TypeError, ValueError):
        days = 365
    limit = None if days <= 0 else today + _dt.timedelta(days=days)
    type_filter = {t.strip() for t in (types or []) if t and t.strip()} or None
    pillar = (pillar or "").strip() or None
    product_id = (product_id or "").strip() or None
    products_by_id = {p.get("id"): p for p in ctx["products"]}

    events = []
    seen = set()

    def push(ev):
        key = (ev.get("ref_id"), ev.get("date"), ev.get("title"))
        if key in seen:
            return
        seen.add(key)
        d = parse_date(ev["date"])
        ev["days_remaining"] = (d - today).days if d else None
        ev.setdefault("product_ids", [])
        ev.setdefault("subtitle", "")
        ev["product_count"] = len(ev["product_ids"])
        ev["tone"] = ev.get("tone") or _tone_for(ev.get("severity"), ev["days_remaining"], ev.get("closed", False))
        ev["id"] = f"{ev['type']}:{ev.get('ref_id')}:{ev['date']}:{abs(hash(ev['title'])) % 10 ** 6}"
        events.append(ev)

    for x in ctx["alerts"]:
        a = x["alert"]
        pid_list = x["impacted_ids"]
        closed = not x["open"]
        eff = parse_date(a.get("effective_date"))
        if eff and a.get("no_deadline"):
            # publication of an informational notice -> history, not a deadline
            push({"type": "surveillance", "date": eff.isoformat(), "title": x["title"], "subtitle": a.get("source") or a.get("standard") or "",
                  "severity": x["severity"], "ref_type": "alert", "ref_id": x["id"], "product_ids": pid_list, "country": x["country"],
                  "country_code": a.get("country_code"), "pillar": x["pillar"], "closed": True, "actionable": False, "triage": x["triage"]})
            eff = None
        if eff:
            push({"type": "alert_deadline", "date": eff.isoformat(), "title": x["title"], "subtitle": a.get("standard") or "",
                  "severity": x["severity"], "ref_type": "alert", "ref_id": x["id"], "product_ids": pid_list, "country": x["country"],
                  "country_code": (a.get("country_code") or (next(iter(x["codes"])) if len(x["codes"]) == 1 else None)),
                  "pillar": x["pillar"], "closed": closed, "actionable": not closed, "triage": x["triage"]})
        for m in a.get("timeline_milestones") or []:
            if not isinstance(m, dict):
                continue
            md = parse_date(m.get("date"))
            if not md or (eff and md == eff):
                continue
            done = not _milestone_pending(m.get("status"))
            push({"type": "milestone", "date": md.isoformat(), "title": str(m.get("phase") or "Milestone"), "subtitle": x["title"],
                  "severity": "Info" if done else ("Warning" if x["severity"] == "Critical" else "Info"), "ref_type": "alert", "ref_id": x["id"],
                  "product_ids": pid_list, "country": x["country"], "country_code": a.get("country_code"), "pillar": x["pillar"],
                  "closed": done or closed, "actionable": not (done or closed), "milestone_status": m.get("status")})

    for pid, certs in ctx["certs_by_product"].items():
        for c in certs:
            d = parse_date(c.get("expiry_date"))
            if not d:
                continue
            prod = products_by_id.get(pid) or {}
            sev = "Critical" if c["status"] in ("Expired", "Critical") else ("Warning" if c["status"] == "Expiring Soon" else "Info")
            push({"type": "cert_expiry", "date": d.isoformat(), "title": f"{c.get('scheme')} · {c.get('cert_no')}",
                  "subtitle": f"{prod.get('name') or c.get('product_name') or pid} · {c.get('issuing_body') or ''}".strip(" ·"),
                  "severity": sev, "ref_type": "certificate", "ref_id": c.get("id"), "product_ids": [pid] if pid else [],
                  "country": c.get("country_coverage") or "", "pillar": _pillar_from_text(f"{c.get('standard')} {c.get('scheme')}"),
                  "closed": False, "actionable": True, "cert_status": c["status"]})

    for a in store.actions():
        d = parse_date(a.get("due_date"))
        if not d:
            continue
        done = a.get("status") == "Done"
        pr = a.get("priority") or "Medium"
        push({"type": "action_due", "date": d.isoformat(), "title": a.get("title") or a.get("id"),
              "subtitle": f"{pr} · {a.get('owner') or 'unassigned'} · {a.get('status')}", "severity": PRIORITY_SEVERITY.get(pr, "Info"),
              "ref_type": "action", "ref_id": a.get("id"), "linked_type": a.get("linked_type"), "linked_id": a.get("linked_id"),
              "product_ids": [a.get("linked_id")] if a.get("linked_type") == "product" and a.get("linked_id") else [],
              "country": (a.get("linked_id") if a.get("linked_type") == "country" else ""), "pillar": None,
              "closed": done, "actionable": not done, "action_status": a.get("status")})

    if surveillance is not None and hasattr(surveillance, "get_audit_log"):
        try:
            ledger = surveillance.get_audit_log(1000) or []
        except Exception:
            ledger = []
        for e in ledger:
            if not isinstance(e, dict):
                continue
            d = parse_date(e.get("timestamp")) or parse_date(e.get("effective_date"))
            if not d:
                continue
            std = e.get("new_standard") or e.get("event_type") or "Regulatory notice"
            title = f"{e.get('country_name') or e.get('country_code') or 'Global'}: {std}"
            push({"type": "surveillance", "date": d.isoformat(), "title": title, "subtitle": (e.get("summary") or "")[:160],
                  "severity": str(e.get("severity") or "Info").title(), "ref_type": "surveillance", "ref_id": e.get("event_id"),
                  "alert_id": f"ALERT-SURV-{str(e.get('event_id', '')).split('-')[-1]}" if e.get("event_id") else None,
                  "product_ids": [p.get("id") for p in (e.get("impacted_products") or []) if isinstance(p, dict) and p.get("id")],
                  "country": e.get("country_name") or "", "country_code": e.get("country_code"), "pillar": e.get("pillar"),
                  "closed": True, "actionable": False, "tone": "info", "authority": e.get("authority"),
                  "deadline": e.get("withdrawal_deadline")})

    # filters
    def keep(ev):
        if type_filter and ev["type"] not in type_filter:
            return False
        if pillar and pillar != "all" and (ev.get("pillar") or "") != pillar and not (pillar == "All" and ev.get("pillar") == "All"):
            return False
        if product_id and product_id != "all" and product_id not in (ev.get("product_ids") or []):
            return False
        d = parse_date(ev["date"])
        if limit and d and d > limit:
            return False
        return True

    events = [e for e in events if keep(e)]
    events.sort(key=lambda e: (e["date"], {"critical": 0, "warning": 1, "info": 2, "success": 3}.get(e["tone"], 9), e["title"]))

    buckets = {k: {"count": 0, "ids": []} for k in ("overdue", "next_30", "next_90", "next_365", "beyond", "history")}
    for e in events:
        n = e["days_remaining"]
        if n is None:
            continue
        if n < 0:
            key = "overdue" if e.get("actionable") else "history"
        elif n <= 30:
            key = "next_30"
        elif n <= 90:
            key = "next_90"
        elif n <= 365:
            key = "next_365"
        else:
            key = "beyond"
        e["bucket"] = key
        buckets[key]["count"] += 1
        buckets[key]["ids"].append(e["id"])

    # month heat strip: 12 months starting this month
    months = []
    y, m = today.year, today.month
    for i in range(12):
        mm = (m - 1 + i) % 12 + 1
        yy = y + (m - 1 + i) // 12
        months.append({"month": f"{yy:04d}-{mm:02d}", "count": 0, "critical": 0})
    month_idx = {x["month"]: x for x in months}
    for e in events:
        k = e["date"][:7]
        if k in month_idx:
            month_idx[k]["count"] += 1
            month_idx[k]["critical"] += e["tone"] == "critical"

    type_counts = {}
    for e in events:
        type_counts[e["type"]] = type_counts.get(e["type"], 0) + 1

    return {
        "events": events, "buckets": buckets, "months": months, "type_counts": type_counts,
        "range_days": days, "today": today.isoformat(), "total": len(events),
        "filters": {"types": sorted(type_filter) if type_filter else None, "pillar": pillar, "product_id": product_id},
        "generated_at": _now_iso(),
    }


def certificate_health(store):
    today = _today()
    out = []
    counts = {"expiring_30": 0, "expiring_90": 0, "expired": 0, "valid": 0, "permanent": 0}
    for c in store.certificates():
        status, d = _cert_status(c, today)
        cc = dict(c)
        cc["declared_status"] = c.get("status")
        cc["status"] = status
        cc["days_to_expiry"] = d
        cc["is_permanent"] = d is None and status == "Valid"
        if status == "Expired":
            counts["expired"] += 1
        elif status == "Critical":
            counts["expiring_30"] += 1
            counts["expiring_90"] += 1
        elif status == "Expiring Soon":
            counts["expiring_90"] += 1
        else:
            counts["valid"] += 1
            if cc["is_permanent"]:
                counts["permanent"] += 1
        out.append(cc)
    out.sort(key=lambda c: (c["days_to_expiry"] is None, c["days_to_expiry"] if c["days_to_expiry"] is not None else 0))
    return {"certificates": out, "total": len(out), **counts, "generated_at": _now_iso()}


def _coverage_matches(cert, country):
    """Return 'national' (country-specific coverage), 'scheme' (CB Scheme / global umbrella) or None."""
    cov = str(cert.get("country_coverage") or "")
    cl = cov.lower()
    code = str(country.get("code") or "").upper()
    name = str(country.get("name") or "").lower()
    if not cov:
        return None
    if name and name in cl:
        return "national"
    if code and re.search(rf"(?<![A-Z]){re.escape(code)}(?![A-Z])", cov):
        return "national"
    bloc = str(country.get("bloc") or "")
    if ("eu" in re.split(r"[^a-z0-9]+", cl) or "european union" in cl or "eea" in cl) and (code in EU_CODES or "EU" in bloc or "EEA" in bloc):
        return "national"
    if code == "CA" and "canada" in cl:
        return "national"
    if code == "NZ" and "new zealand" in cl:
        return "national"
    if code in ("AE", "SA", "QA", "KW", "OM", "BH") and ("gcc" in cl or "gulf" in cl):
        return "national"
    if any(w in cl for w in ("global", "worldwide", "all countries", "all markets", "international")):
        return "scheme"
    if "cb scheme" in cl and country.get("cb_scheme_accepted"):
        return "scheme"
    return None


def readiness_for_product(product, codes, certificates, db):
    """Per-market readiness for a product. badge: success | info | warning | danger."""
    if not product:
        return []
    today = _today()
    cat_id = product.get("category_id")
    pid = product.get("id")
    countries = getattr(db, "COUNTRIES_DB", {}) or {}
    my_certs = [c for c in (certificates or []) if c.get("product_id") == pid]
    out = []
    for raw_code in codes or []:
        code = str(raw_code or "").upper().strip()
        if not code:
            continue
        country = countries.get(code) or {"code": code, "name": code, "region": "Unknown", "marks": ["CE"], "authority": "National authority"}
        rule = {}
        try:
            rule = db.get_country_product_requirement(code, cat_id) or {}
        except Exception:
            rule = {}
        req = rule.get("requirement_type") or ""
        marks = country.get("marks") or ["local mark"]
        primary_mark = marks[0] if marks else "local mark"
        matched = [(c, _coverage_matches(c, country)) for c in my_certs]
        matching = [c for c, kind in matched if kind]
        national = [c for c, kind in matched if kind == "national"]
        scheme_only = [c for c, kind in matched if kind == "scheme"]
        needs_local = "Testing Required" in req
        statuses = [(_cert_status(c, today)[0], c) for c in matching]
        valid = [c for s_, c in statuses if s_ in ("Valid", "Expiring Soon")]
        critical = [c for s_, c in statuses if s_ == "Critical"]
        expired = [c for s_, c in statuses if s_ == "Expired"]
        national_live = [c for c in national if _cert_status(c, today)[0] != "Expired"]

        if (valid or critical) and (not needs_local or national_live):
            if critical and not valid:
                status, badge = "Certified – renewal due", "warning"
                c = critical[0]
                action = f"{c.get('scheme')} {c.get('cert_no')} expires on {c.get('expiry_date')}; file the renewal with {c.get('issuing_body') or country.get('authority')} now."
            else:
                status, badge, action = "Ready / Certified", "success", "All regulatory filings up to date."
                if critical:
                    action = f"Certified; note {critical[0].get('scheme')} {critical[0].get('cert_no')} expires within 30 days."
        elif needs_local and (valid or critical) and scheme_only and not national_live:
            status, badge = "CB Report held – local approval pending", "warning"
            c = scheme_only[0]
            action = f"{c.get('scheme')} {c.get('cert_no')} covers the base standard, but {country.get('name')} requires in-country testing at {rule.get('testing_location') or 'an accredited local lab'} and {primary_mark} registration via {country.get('authority')}."
        elif expired and not (valid or critical):
            status, badge = "Certificate Expired", "danger"
            c = expired[0]
            action = f"{c.get('scheme')} {c.get('cert_no')} expired on {c.get('expiry_date')}. Re-certify before shipping to {country.get('name')}."
        elif "Exempt" in req or "Supplier Declaration" in req or (
                cat_id in ("sd_card", "micro_sd", "usb_drive") and not country.get("in_country_testing") and not needs_local):
            status, badge = "Ready (SDoC Route)", "info"
            action = "Standard Declaration of Conformity and RoHS/REACH pack in place; no third-party filing required."
        elif needs_local:
            status, badge = "In-Country Testing Required", "danger"
            action = f"Mandatory local testing at {rule.get('testing_location') or 'an accredited in-country lab'} under {rule.get('safety_std') or country.get('safety_std') or 'the national safety standard'}; apply for {primary_mark}."
        elif "Document Required" in req:
            status, badge = "Filing Required", "warning"
            action = f"Submit CB Report / technical file to {country.get('authority')} and apply for {primary_mark} registration."
        else:
            status, badge = "Action Required", "danger"
            if cat_id == "external_ssd_powered" and country.get("in_country_testing"):
                action = f"Mandatory local safety testing required under {country.get('safety_std')}."
            else:
                action = f"Submit CB Report and apply for {primary_mark} registration."
        out.append({
            "country_code": country.get("code", code), "country_name": country.get("name", code), "region": country.get("region", "Unknown"),
            "status": status, "badge": badge, "action_needed": action, "authority": country.get("authority"),
            "required_marks": marks, "requirement_type": req or "Unclassified", "in_country_testing": bool(country.get("in_country_testing")),
            "local_rep_required": bool(rule.get("local_rep_required", country.get("local_rep_required", False))),
            "lead_time_weeks": rule.get("lead_time_weeks", country.get("lead_time_weeks")),
            "certificates": [c.get("id") for c in matching],
        })
    return out


def portfolio(store, db):
    summary = compute_risk_summary(store, db)
    risk_by_id = {p["id"]: p for p in summary["per_product"]}
    ctx_certs = certificate_health(store)["certificates"]
    certs_by_product = {}
    for c in ctx_certs:
        certs_by_product.setdefault(c.get("product_id"), []).append(c)
    categories = getattr(db, "PRODUCT_CATEGORIES", {}) or {}
    products = []
    for p in store.products():
        pid = p.get("id")
        r = risk_by_id.get(pid, {})
        cat = categories.get(p.get("category_id"), {})
        markets = [str(m).upper() for m in (p.get("target_markets") or [])]
        readiness = readiness_for_product(p, markets, store.certificates(), db)
        ready = sum(1 for e in readiness if e["badge"] in ("success", "info"))
        pct = round(ready / len(readiness) * 100) if readiness else 0
        certs = certs_by_product.get(pid, [])
        products.append({
            **p, "target_markets": markets,
            "category": {"id": cat.get("id", p.get("category_id")), "name": cat.get("name", p.get("category_name")), "icon": cat.get("icon", "hard-drive"),
                         "risk_tier": cat.get("risk_tier", "Medium"), "power_type": cat.get("power_type", p.get("power_source"))},
            "risk_score": r.get("risk_score", 0.0), "grade": r.get("grade", "A"), "open_alerts": r.get("open_alerts", 0),
            "critical_alerts": r.get("critical_alerts", 0), "drivers": r.get("drivers", []), "cert_health": r.get("cert_health", "No certificates"),
            "certificates_count": len(certs), "active_certs_count": sum(1 for c in certs if c["status"] != "Expired"), "certificates": certs,
            "next_deadline": r.get("next_deadline"), "days_to_next_deadline": r.get("days_to_next_deadline"), "next_deadline_label": r.get("next_deadline_label"),
            "readiness": [{"market_code": e["country_code"], **e} for e in readiness],
            "readiness_pct": pct, "ready_markets": ready, "declared_readiness_pct": p.get("readiness_pct"),
        })
    total = len(products)
    return {
        "products": products, "total": total,
        "kpis": {
            "products": total, "certificates": len(ctx_certs),
            "expiring_90": sum(1 for c in ctx_certs if c["status"] in ("Critical", "Expiring Soon")),
            "expired": sum(1 for c in ctx_certs if c["status"] == "Expired"),
            "avg_readiness": round(sum(p["readiness_pct"] for p in products) / total) if total else 0,
            "avg_risk": round(sum(p["risk_score"] for p in products) / total, 1) if total else 0.0,
            "compliance_risk_index": summary["compliance_risk_index"], "grade": summary["grade"],
        },
        "generated_at": _now_iso(),
    }


def product_detail(store, db, product_id, surveillance=None):
    """Single product: portfolio row + linked alerts (with triage) + horizon events."""
    pf = portfolio(store, db)
    prod = next((p for p in pf["products"] if p.get("id") == product_id), None)
    if not prod:
        return None
    ctx = _analyse(store, db)
    linked = []
    for x in ctx["alerts"]:
        if product_id in x["impacted_ids"]:
            a = x["alert"]
            linked.append({"id": x["id"], "title": x["title"], "severity": x["severity"], "pillar": x["pillar"], "country": x["country"],
                           "standard": a.get("standard"), "effective_date": a.get("effective_date"), "days_to_effective": x["days"],
                           "triage_status": x["triage"], "score": x["score"], "action_required": a.get("action_required")})
    linked.sort(key=lambda a: (-a["score"], a["title"]))
    horizon = build_horizon(store, db, surveillance=surveillance, days=0, product_id=product_id)
    actions = [a for a in store.actions() if a.get("linked_type") == "product" and a.get("linked_id") == product_id]
    return {"product": prod, "alerts": linked, "events": horizon["events"][:60], "buckets": horizon["buckets"], "actions": actions,
            "generated_at": _now_iso()}
