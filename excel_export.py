"""
Excel Export Engine for the GCM Platform compliance matrix.

The workbook mirrors the on-screen matrix one-to-one: same rows (same filters), same
columns in the same order, same applicable-requirements / exemption wording and the
same applicable marks, so what you see in the browser is what you get in Excel.
"""
import datetime
import io

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import compliance_db as db
import kb_review

HEADERS = [
    ("ISO", 8), ("Jurisdiction", 22), ("Region", 20), ("Regulatory Authority", 24),
    ("Requirement Route", 30), ("Testing Location", 26),
    ("Applicable Requirements & Exemptions", 60), ("Applicable Summary", 42),
    ("Mandatory Documentation", 60), ("Applicable Marks / Logos", 30),
    ("Verification & sources", 48),
    ("Local Rep", 12), ("Lead Time (wks)", 10),
    ("RoHS", 34), ("PFAS / Chemicals", 34), ("Packaging", 34), ("EPR / WEEE", 34),
    ("Regulatory Notes & Scope", 50),
]


def filter_countries(countries, type_filter="all", region_filter="all", search=""):
    """Same filter semantics as the matrix API so the export matches the display."""
    tf = (type_filter or "all").lower().strip()
    rf = (region_filter or "all").lower().strip()
    sq = (search or "").lower().strip()
    out = []
    for c in countries:
        req = c["requirement_type"]
        if tf == "testing" and "Testing Required" not in req:
            continue
        if tf == "document" and "Document Required" not in req:
            continue
        if tf == "sdoc" and ("Supplier Declaration" not in req and "Exempt" not in req):
            continue
        if tf == "local_rep" and not c.get("local_rep_required"):
            continue
        if rf not in ("", "all") and rf not in c["region"].lower():
            continue
        if sq:
            hay = " ".join(str(c.get(k, "")) for k in (
                "country_name", "country_code", "authority", "safety_std", "national_safety_std", "emc_std", "env_std",
                "rohs_std", "pfas_std", "packaging_std", "epr_std", "notes", "bloc", "applicable_summary")).lower()
            hay += " " + " ".join(c.get("required_documents", [])).lower() + " " + " ".join(c.get("marks", [])).lower()
            if sq not in hay:
                continue
        out.append(c)
    return out


def _requirements_text(c):
    lines = []
    for r in c.get("applicable_requirements") or []:
        if r.get("status") == "Not applicable":
            continue
        if r.get("status") == "Exempt":
            lines.append(f"{r['pillar']}: EXEMPT – {r.get('note') or 'not applicable to this product'}")
        else:
            std = r.get("standard") or "—"
            route = f" [{r['route']}]" if r.get("route") else ""
            note = f" – {r['note']}" if r.get("note") and r.get("pillar") != "Environmental" else ""
            lines.append(f"{r['pillar']}: Required – {std}{route}{note}")
    if not lines:
        lines = [f"Safety: {c.get('safety_std', '')}", f"EMC: {c.get('emc_std', '')}", f"Environmental: {c.get('env_std', '')}"]
    return "\n".join(lines)


def _marks_text(c):
    marks = c.get("applicable_marks") or [{"mark": m, "status": "Required"} for m in c.get("marks", [])]
    req = [m["mark"] for m in marks if m.get("status") == "Required"]
    not_req = [m["mark"] for m in marks if m.get("status") != "Required"]
    txt = ", ".join(req) if req else "No national mark required"
    if not_req:
        txt += "\nNot required for this product: " + ", ".join(not_req)
    return txt


def _verification_text(c):
    v = c.get("verification") or {}
    lines = [f"Status: {v.get('overall', 'Unverified')}"]
    if v.get("verified_on"):
        lines.append(f"Verified {v['verified_on']} by {v.get('verified_by') or 'n/a'}")
    per = v.get("per_pillar") or {}
    lines.append("Pillars: " + ", ".join(f"{k} {per[k].get('status', 'Unverified')}" for k in per))
    if v.get("overrides"):
        lines.append("Edited & approved fields: " + ", ".join(v["overrides"]))
    srcs = v.get("sources") or []
    if srcs:
        lines.extend(f"{s.get('kind', 'Source')}: {s.get('label', '')} - {s.get('url', '')}" for s in srcs)
    else:
        lines.append("No source recorded")
    return "\n".join(lines)


def export_product_matrix_excel(category_id="external_ssd_powered", type_filter="all", region_filter="all", search="", export_all=False):
    """Returns (io.BytesIO, filename) for the filtered (or full) matrix of one product category."""
    breakdown = db.get_product_market_breakdown(category_id)
    cat_name = breakdown.get("category_name", category_id)
    summary = breakdown.get("summary", {})
    all_countries = kb_review.attach(breakdown.get("countries", []))

    if export_all:
        rows = list(all_countries)
        filter_desc = "All 205 jurisdictions (unfiltered)"
    else:
        rows = filter_countries(all_countries, type_filter, region_filter, search)
        parts = []
        if (type_filter or "all").lower() != "all":
            parts.append(f"Requirement: {type_filter}")
        if (region_filter or "all").lower() != "all":
            parts.append(f"Region: {region_filter}")
        if (search or "").strip():
            parts.append(f"Search: '{search.strip()}'")
        filter_desc = " | ".join(parts) if parts else "All 205 jurisdictions"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Compliance Matrix"

    navy = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    sub_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fills = {
        "testing": (PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid"), Font(name="Calibri", size=10, bold=True, color="991B1B")),
        "document": (PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid"), Font(name="Calibri", size=10, bold=True, color="92400E")),
        "sdoc": (PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid"), Font(name="Calibri", size=10, bold=True, color="065F46")),
        "exempt": (PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid"), Font(name="Calibri", size=10, bold=True, color="0369A1")),
    }
    thin = Side(border_style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    last_col = get_column_letter(len(HEADERS))

    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"].value = "GCM PLATFORM – PRODUCT TESTING vs. DOCUMENT COMPLIANCE MATRIX (SAFETY | EMC | ENVIRONMENTAL | CYBER)"
    ws["A1"].font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    ws["A1"].fill = navy
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 32

    ws.merge_cells(f"A2:{last_col}2")
    ws["A2"].value = (f"Product classification: {cat_name}   |   Scope: {filter_desc}   |   Exported: "
                      f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} (local time)   |   Rows: {len(rows)}")
    ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="334155")
    ws["A2"].fill = sub_fill
    ws["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)

    ws.merge_cells(f"A3:{last_col}3")
    ws["A3"].value = (f"Category totals (all 205): In-country testing {summary.get('testing_required', 0)}  |  "
                      f"Document / CB Scheme {summary.get('document_required', 0)}  |  Supplier declaration {summary.get('sdoc_required', 0)}  |  "
                      f"Exempt / customs {summary.get('exempt', 0)}.  'EXEMPT' entries mean the pillar does not apply to this product in that market; "
                      f"struck marks are listed under 'Not required for this product'.")
    ws["A3"].font = Font(name="Calibri", size=9, color="0F172A")
    ws["A3"].fill = sub_fill
    ws["A3"].alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
    ws.row_dimensions[3].height = 30
    ws.row_dimensions[4].height = 6

    for col, (title, width) in enumerate(HEADERS, 1):
        cell = ws.cell(row=5, column=col, value=title)
        cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center" if col in (1, 5, 12, 13) else "left", vertical="center", wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[5].height = 28

    body = Font(name="Calibri", size=9)
    r_idx = 6
    for c in rows:
        req = c["requirement_type"]
        key = "testing" if "Testing Required" in req else "document" if "Document Required" in req else "sdoc" if "Supplier Declaration" in req else "exempt"
        values = [
            c["country_code"], c["country_name"], c["region"], c["authority"],
            req, c.get("testing_location", ""),
            _requirements_text(c), c.get("applicable_summary", ""),
            "\n".join(f"• {d}" for d in c.get("required_documents", [])),
            _marks_text(c),
            _verification_text(c),
            "Mandatory" if c.get("local_rep_required") else "No",
            c.get("lead_time", ""),
            c.get("rohs_std") or c.get("env_std", ""), c.get("pfas_std", ""), c.get("packaging_std", ""), c.get("epr_std", ""),
            c.get("notes", ""),
        ]
        for col, v in enumerate(values, 1):
            cell = ws.cell(row=r_idx, column=col, value=v)
            cell.font = body
            cell.border = border
            cell.alignment = Alignment(horizontal="center" if col in (1, 5, 12, 13) else "left", vertical="top", wrap_text=col not in (1, 2, 3))
        fill, font = fills[key]
        ws.cell(row=r_idx, column=5).fill = fill
        ws.cell(row=r_idx, column=5).font = font
        ws.cell(row=r_idx, column=2).font = Font(name="Calibri", size=10, bold=True)
        ws.cell(row=r_idx, column=1).font = Font(name="Consolas", size=9, bold=True)
        if c.get("local_rep_required"):
            ws.cell(row=r_idx, column=12).font = Font(name="Calibri", size=9, bold=True, color="991B1B")
        n_lines = max(_requirements_text(c).count("\n"), len(c.get("required_documents", [])) - 1, 2) + 1
        ws.row_dimensions[r_idx].height = min(15 * n_lines + 6, 220)
        r_idx += 1

    ws.freeze_panes = "C6"
    if r_idx > 6:
        ws.auto_filter.ref = f"A5:{last_col}{r_idx - 1}"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    scope = "all205" if export_all else "view"
    return buf, f"GCM_Compliance_Matrix_{category_id}_{scope}_{stamp}.xlsx"
