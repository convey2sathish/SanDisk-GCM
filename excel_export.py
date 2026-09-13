"""
Excel Export Engine for Global Compliance Management (GCM)
Generates professionally formatted, styled .xlsx workbooks for
the Product-Based Testing vs. Document Compliance Matrix.
"""

import io
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import compliance_db as db

def export_product_matrix_excel(category_id="external_ssd_powered", type_filter="all", region_filter="all", search="", export_all=False):
    """
    Generates an Excel workbook (.xlsx) for the compliance matrix of a given product category.
    Supports filtering by requirement type, region, and search term.
    Returns (io.BytesIO, filename_string).
    """
    breakdown = db.get_product_market_breakdown(category_id)
    cat_name = breakdown.get("category_name", category_id)
    summary = breakdown.get("summary", {})
    all_countries = breakdown.get("countries", [])

    # Filter countries unless export_all is True
    if export_all:
        filtered_countries = list(all_countries)
        filter_desc = "All 205 Jurisdictions (Unfiltered)"
    else:
        filtered_countries = []
        tf = (type_filter or "all").lower().strip()
        rf = (region_filter or "all").lower().strip()
        sq = (search or "").lower().strip()

        filter_parts = []
        if tf != "all":
            filter_parts.append(f"Type: {tf.title()}")
        if rf != "all":
            filter_parts.append(f"Region: {rf.title()}")
        if sq:
            filter_parts.append(f"Search: '{sq}'")
        filter_desc = " | ".join(filter_parts) if filter_parts else "All 205 Jurisdictions"

        for c in all_countries:
            req = c["requirement_type"].lower()
            if tf == "testing" and "testing required" not in req:
                continue
            elif tf == "document" and "document required" not in req:
                continue
            elif tf == "sdoc" and not ("supplier declaration" in req or "exempt" in req):
                continue

            if rf != "all" and rf not in c["region"].lower():
                continue

            if sq:
                match = (
                    sq in c["country_name"].lower() or
                    sq in c["country_code"].lower() or
                    sq in c["authority"].lower() or
                    sq in c.get("safety_std", "").lower() or
                    sq in c.get("emc_std", "").lower() or
                    sq in c.get("env_std", "").lower() or
                    any(sq in d.lower() for d in c.get("required_documents", [])) or
                    any(sq in m.lower() for m in c.get("marks", []))
                )
                if not match:
                    continue

            filtered_countries.append(c)

    # Initialize OpenPyXL Workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Compliance Matrix"
    ws.views.sheetView[0].showGridLines = True

    # Palette Definitions (Corporate Dark Navy & Professional Accents)
    navy_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    subhdr_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    testing_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    testing_font = Font(name="Calibri", size=10, bold=True, color="991B1B")

    doc_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    doc_font = Font(name="Calibri", size=10, bold=True, color="92400E")

    sdoc_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
    sdoc_font = Font(name="Calibri", size=10, bold=True, color="065F46")

    exempt_fill = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")
    exempt_font = Font(name="Calibri", size=10, bold=True, color="0369A1")

    thin_border_side = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    header_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=Side(border_style="medium", color="0F172A"))

    # 1. Main Title Banner (Row 1)
    ws.merge_cells("A1:N1")
    title_cell = ws["A1"]
    title_cell.value = "GLOBAL COMPLIANCE MANAGEMENT (GCM) - PRODUCT COMPLIANCE & TESTING MATRIX"
    title_cell.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    title_cell.fill = navy_fill
    title_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 34

    # 2. Metadata Banner (Row 2)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    ws.merge_cells("A2:N2")
    sub_cell = ws["A2"]
    sub_cell.value = f"Product Classification: {cat_name.upper()}   |   Active Scope: {filter_desc}   |   Export Date: {now_str}"
    sub_cell.font = Font(name="Calibri", size=10, italic=True, color="334155")
    sub_cell.fill = subhdr_fill
    sub_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 20

    # 3. Category Executive Summary Counts (Row 3)
    ws.merge_cells("A3:N3")
    stats_cell = ws["A3"]
    stats_cell.value = (
        f"Category Metrics: {len(filtered_countries)} jurisdictions displayed.  "
        f"[In-Country Testing Required: {summary.get('testing_required', 0)}]   "
        f"[Document Acceptance / CB Scheme: {summary.get('document_required', 0)}]   "
        f"[Supplier Declaration (SDoC): {summary.get('sdoc_required', 0)}]   "
        f"[Exempt / Standard Customs: {summary.get('exempt', 0)}]"
    )
    stats_cell.font = Font(name="Calibri", size=10, bold=True, color="0F172A")
    stats_cell.fill = subhdr_fill
    stats_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[3].height = 22

    # Row 4: Spacer
    ws.row_dimensions[4].height = 6

    # 4. Table Column Headers (Row 5)
    headers = [
        "ISO Code",
        "Jurisdiction",
        "Region",
        "Regulatory Authority",
        "Requirement Status",
        "Applicable Safety Standard",
        "Applicable EMC Standard",
        "Environmental / Chemical",
        "Mandatory Documentation Checklist",
        "Local Rep Required",
        "Est. Lead Time (Wks)",
        "Compliance Marks",
        "Regulatory Notes & Scope",
        "Live Surveillance Source"
    ]

    ws.row_dimensions[5].height = 28
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_idx, value=h)
        cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center" if col_idx in [1, 5, 10, 11] else "left", vertical="center", wrap_text=True)
        cell.border = header_border

    # 5. Populate Data Rows (Starting Row 6)
    row_idx = 6
    for c in filtered_countries:
        ws.row_dimensions[row_idx].height = 24

        # Col 1: ISO Code
        code_cell = ws.cell(row=row_idx, column=1, value=c["country_code"])
        code_cell.alignment = Alignment(horizontal="center", vertical="center")
        code_cell.font = Font(name="Consolas", size=9, bold=True)
        code_cell.border = cell_border

        # Col 2: Country Name
        name_cell = ws.cell(row=row_idx, column=2, value=c["country_name"])
        name_cell.alignment = Alignment(horizontal="left", vertical="center")
        name_cell.font = Font(name="Calibri", size=10, bold=True)
        name_cell.border = cell_border

        # Col 3: Region
        reg_cell = ws.cell(row=row_idx, column=3, value=c["region"])
        reg_cell.alignment = Alignment(horizontal="left", vertical="center")
        reg_cell.font = Font(name="Calibri", size=9)
        reg_cell.border = cell_border

        # Col 4: Authority
        auth_cell = ws.cell(row=row_idx, column=4, value=c["authority"])
        auth_cell.alignment = Alignment(horizontal="left", vertical="center")
        auth_cell.font = Font(name="Calibri", size=9)
        auth_cell.border = cell_border

        # Col 5: Requirement Status (Color-coded badge)
        req_val = c["requirement_type"]
        req_cell = ws.cell(row=row_idx, column=5, value=req_val)
        req_cell.alignment = Alignment(horizontal="center", vertical="center")
        req_cell.border = cell_border
        if "Testing Required" in req_val:
            req_cell.fill = testing_fill
            req_cell.font = testing_font
        elif "Document Required" in req_val:
            req_cell.fill = doc_fill
            req_cell.font = doc_font
        elif "Supplier Declaration" in req_val:
            req_cell.fill = sdoc_fill
            req_cell.font = sdoc_font
        else:
            req_cell.fill = exempt_fill
            req_cell.font = exempt_font

        # Col 6: Applicable Safety Standard
        safety_cell = ws.cell(row=row_idx, column=6, value=c.get("safety_std", "Exempt"))
        safety_cell.alignment = Alignment(horizontal="left", vertical="center")
        safety_cell.font = Font(name="Calibri", size=9)
        safety_cell.border = cell_border

        # Col 7: Applicable EMC Standard
        emc_cell = ws.cell(row=row_idx, column=7, value=c.get("emc_std", "CISPR 32 Class B"))
        emc_cell.alignment = Alignment(horizontal="left", vertical="center")
        emc_cell.font = Font(name="Calibri", size=9)
        emc_cell.border = cell_border

        # Col 8: Environmental / Chemical
        env_cell = ws.cell(row=row_idx, column=8, value=c.get("env_std", "RoHS / REACH"))
        env_cell.alignment = Alignment(horizontal="left", vertical="center")
        env_cell.font = Font(name="Calibri", size=9)
        env_cell.border = cell_border

        # Col 9: Documentation Checklist
        docs_str = "; ".join(c.get("required_documents", []))
        docs_cell = ws.cell(row=row_idx, column=9, value=docs_str)
        docs_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        docs_cell.font = Font(name="Calibri", size=9)
        docs_cell.border = cell_border

        # Col 10: Local Rep Required
        rep_str = "Mandatory (Yes)" if c.get("local_rep_required") else "No"
        rep_cell = ws.cell(row=row_idx, column=10, value=rep_str)
        rep_cell.alignment = Alignment(horizontal="center", vertical="center")
        rep_cell.font = Font(name="Calibri", size=9, bold=(rep_str != "No"), color="991B1B" if rep_str != "No" else "475569")
        rep_cell.border = cell_border

        # Col 11: Est. Lead Time
        lead_cell = ws.cell(row=row_idx, column=11, value=c.get("lead_time", 2))
        lead_cell.alignment = Alignment(horizontal="center", vertical="center")
        lead_cell.font = Font(name="Calibri", size=9)
        lead_cell.border = cell_border

        # Col 12: Compliance Marks
        marks_str = ", ".join(c.get("marks", []))
        marks_cell = ws.cell(row=row_idx, column=12, value=marks_str)
        marks_cell.alignment = Alignment(horizontal="left", vertical="center")
        marks_cell.font = Font(name="Consolas", size=9)
        marks_cell.border = cell_border

        # Col 13: Regulatory Notes & Scope
        notes_cell = ws.cell(row=row_idx, column=13, value=c.get("notes", ""))
        notes_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        notes_cell.font = Font(name="Calibri", size=9, color="475569")
        notes_cell.border = cell_border

        # Col 14: Live Surveillance Source
        surv_pillar = c.get('last_surveilled_pillar', 'Multi-Pillar')
        surv_source = f"Auto-Surveilled [{surv_pillar}] ({c.get('last_surveilled_date')}) via {c.get('surveillance_source')}" if c.get("last_surveilled_date") else "WTO TBT Global Early Warning Verified (Safety • EMC • Environmental)"
        surv_cell = ws.cell(row=row_idx, column=14, value=surv_source)
        surv_cell.alignment = Alignment(horizontal="left", vertical="center")
        surv_cell.font = Font(name="Calibri", size=9, color="047857" if c.get("last_surveilled_date") else "64748B")
        surv_cell.border = cell_border

        row_idx += 1

    # Freeze header panes (Freeze at row 6, col 1)
    ws.freeze_panes = "A6"

    # Auto-filter on data table headers
    if row_idx > 6:
        ws.auto_filter.ref = f"A5:N{row_idx-1}"

    # Optimized Column Widths
    col_widths = {
        1: 10,   # ISO Code
        2: 24,   # Country Name
        3: 20,   # Region
        4: 25,   # Authority
        5: 28,   # Requirement Status
        6: 32,   # Safety Standard
        7: 28,   # EMC Standard
        8: 24,   # Env / Chemical
        9: 48,   # Documentation Checklist
        10: 18,  # Local Rep
        11: 16,  # Lead Time
        12: 20,  # Marks
        13: 42,  # Notes
        14: 36   # Live Surveillance Source
    }
    for col_num, width in col_widths.items():
        col_letter = get_column_letter(col_num)
        ws.column_dimensions[col_letter].width = width

    # Save to BytesIO buffer
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    # Clean file name
    date_stamp = datetime.datetime.now().strftime("%Y%m%d")
    clean_cat_id = category_id.replace(" ", "_").lower()
    filename = f"GCM_Compliance_Matrix_{clean_cat_id}_{date_stamp}.xlsx"

    return buf, filename
