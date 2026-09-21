"""
SanDisk Global Compliance Management (GCM) Platform
Document Audit & Regulatory Impact Engine (doc_audit_engine.py)

Performs automated multi-format document ingestion (PDF, DOCX, XLSX, TXT, JSON),
extracts cited technical standards, product SKUs, report numbers, issuing test labs,
and cross-references them against active regulatory alerts and 205-country requirements
to generate actionable document revision directives.
"""

import os
import re
import io
import json
import zipfile
import datetime
from typing import List, Dict, Any, Optional

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

import compliance_db as db

# ----------------------------------------------------------------------
# Regulatory Alert Rulebook Mapping
# ----------------------------------------------------------------------
SUPERSEDED_STANDARDS = {
    # Electrical Safety
    "IEC 60950-1": {
        "new_standard": "IEC 62368-1:2023 (Edition 4.0)",
        "alert_id": "ALERT-2026-02",
        "tier": "retesting_required",
        "action": "Complete hardware safety transition test from legacy standard to IEC 62368-1 Edition 4.0.",
        "cost": "$4,500 - $7,500",
        "turnaround": "6 - 8 Weeks"
    },
    "IEC 62368-1:2014": {
        "new_standard": "IEC 62368-1:2023 (Edition 4.0)",
        "alert_id": "ALERT-2026-02",
        "tier": "retesting_required",
        "action": "Edition 2.0 sunset. Submit sample for laboratory gap testing (Clauses 4.1.2 and 5.4.1).",
        "cost": "$2,500 - $4,500",
        "turnaround": "4 - 6 Weeks"
    },
    "EN 62368-1:2014": {
        "new_standard": "EN IEC 62368-1:2020+A11:2020 / EN IEC 62368-1:2024",
        "alert_id": "ALERT-2026-02",
        "tier": "doc_amendment",
        "action": "Update EU Declaration of Conformity with current Official Journal (OJEU) cited harmonized standard.",
        "cost": "$0 (Administrative)",
        "turnaround": "1 - 2 Weeks"
    },
    "IEC 62368-1:2018": {
        "new_standard": "IEC 62368-1:2023 (Edition 4.0)",
        "alert_id": "ALERT-2026-02",
        "tier": "doc_amendment",
        "action": "Conduct CB test report review against 4th edition amendments and national deviations.",
        "cost": "$1,000 - $2,000",
        "turnaround": "2 - 3 Weeks"
    },
    # EMC / Radio
    "EN 55022": {
        "new_standard": "EN 55032:2015+A11:2020 / CISPR 32 Edition 3.0",
        "alert_id": "ALERT-2026-03",
        "tier": "retesting_required",
        "action": "EN 55022 is permanently withdrawn. Re-test radiated and conducted emissions under CISPR 32 Class B.",
        "cost": "$3,000 - $5,000",
        "turnaround": "3 - 5 Weeks"
    },
    "CISPR 22": {
        "new_standard": "CISPR 32:2015 / CISPR 32:2026 (Edition 3.0)",
        "alert_id": "ALERT-2026-03",
        "tier": "retesting_required",
        "action": "Legacy multimedia emissions standard superseded. Complete emissions test under CISPR 32.",
        "cost": "$3,000 - $5,000",
        "turnaround": "3 - 5 Weeks"
    },
    # Environmental & Chemical
    "DIRECTIVE 2011/65/EU": {
        "new_standard": "EU RoHS 3 (Directive 2011/65/EU + 2015/863 10 Substances) & RoHS 4 Recast (TBBP-A / MCCPs)",
        "alert_id": "ALERT-ENV-07",
        "tier": "doc_amendment",
        "action": "Verify bill of materials includes testing for 4 phthalates (DEHP, BBP, DBP, DIBP) and flame retardant TBBP-A.",
        "cost": "$500 - $1,500",
        "turnaround": "2 - 3 Weeks"
    },
    "SJ/T 11364-2006": {
        "new_standard": "SJ/T 11364-2014 / China RoHS 2 Order 32 (EFUP Table & Green/Orange Logo)",
        "alert_id": "ALERT-2026-09",
        "tier": "packaging_update",
        "action": "Replace China RoHS 1 symbol with Order 32 EFUP table in manual and packaging label.",
        "cost": "Factory Print Cost",
        "turnaround": "3 - 4 Weeks"
    }
}

# Regex Patterns for Regulatory Standards Extraction
STANDARD_PATTERNS = [
    # Safety
    (r"IEC[\s\-_]?62368[\s\-_]?1(?::\s*(?:2014|2018|2023))?", "IEC 62368-1"),
    (r"EN[\s\-_]?(?:IEC[\s\-_]?)?62368[\s\-_]?1(?::\s*(?:2014|2020|2024))?", "EN 62368-1"),
    (r"UL[\s\-_]?62368[\s\-_]?1", "UL 62368-1"),
    (r"IEC[\s\-_]?60950[\s\-_]?1", "IEC 60950-1"),
    (r"EN[\s\-_]?60950[\s\-_]?1", "EN 60950-1"),
    (r"IS[\s\-_]?13252(?:\s*\([Pp]art\s*1\))?", "IS 13252"),
    (r"GB[\s\-_]?4943(?:\.1)?", "GB 4943.1"),
    (r"CNS[\s\-_]?14336(?:\-1)?", "CNS 14336-1"),
    (r"K[\s\-_]?60950[\s\-_]?1", "K 60950-1"),

    # EMC / Radio
    (r"CISPR[\s\-_]?32(?::\s*(?:2015|2026))?", "CISPR 32"),
    (r"EN[\s\-_]?55032(?::\s*(?:2015|2020))?", "EN 55032"),
    (r"EN[\s\-_]?55022", "EN 55022"),
    (r"CISPR[\s\-_]?22", "CISPR 22"),
    (r"FCC[\s\-_]?(?:47[\s\-_]?CFR[\s\-_]?)?Part[\s\-_]?15(?:\s*Subpart\s*B)?", "FCC Part 15B"),
    (r"VCCI[\s\-_]CISPR[\s\-_]?32", "VCCI-CISPR 32"),
    (r"KN[\s\-_]?32", "KN 32"),
    (r"CNS[\s\-_]?13438", "CNS 13438"),
    (r"GB(?:/T)?[\s\-_]?9254(?:\.1)?", "GB/T 9254.1"),

    # Environmental & Chemical
    (r"(?:Directive[\s\-_]?)?2011/65/EU", "Directive 2011/65/EU (RoHS 2)"),
    (r"(?:Directive[\s\-_]?)?2015/863", "Directive (EU) 2015/863 (RoHS 3)"),
    (r"RoHS[\s\-_]?[234]?", "RoHS"),
    (r"REACH[\s\-_]?(?:Regulation[\s\-_]?)?(?:\(EC\)[\s\-_]?No[\s\-_]?1907/2006)?", "REACH (EC 1907/2006)"),
    (r"TSCA[\s\-_]?(?:Section[\s\-_]?)?8\(a\)\(7\)", "TSCA Section 8(a)(7) (PFAS)"),
    (r"TSCA[\s\-_]?40[\s\-_]?CFR[\s\-_]?(?:Part[\s\-_]?)?705", "TSCA 40 CFR Part 705"),
    (r"SJ/T[\s\-_]?11364(?:\-20[0-9]{2})?", "SJ/T 11364 (China RoHS)"),
    (r"CNS[\s\-_]?15663(?:\s*Section\s*5)?", "CNS 15663 (Taiwan RoHS)"),
    (r"SASO[\s\-_]RoHS", "SASO RoHS (SABER)"),

    # Packaging & Plastics
    (r"Triman", "France Triman Logo (AGEC)"),
    (r"Info[\s\-_]?tri", "France Info-tri Signage"),
    (r"Decree[\s\-_]?2021[\s\-_]?835", "French Decree 2021-835"),
    (r"(?:Legislative[\s\-_]?)?Decree[\s\-_]?116/2020", "Italy D.Lgs 116/2020"),
    (r"Decision[\s\-_]?129/97/EC", "Decision 129/97/EC (Packaging Material Coding)"),
    (r"VerpackG", "Germany VerpackG (LUCID)"),
    (r"PPWR", "EU Packaging & Packaging Waste Regulation (PPWR)"),

    # EPR & WEEE
    (r"WEEE[\s\-_]?(?:Directive[\s\-_]?)?(?:2012/19/EU)?", "WEEE Directive 2012/19/EU"),
    (r"E[\s\-_]?Waste[\s\-_]?Rules[\s\-_]?2022", "India E-Waste Management Rules 2022"),
    (r"CPCB", "India Central Pollution Control Board (CPCB)")
]

PRODUCT_SKU_PATTERNS = [
    (r"SDSSDE61[A-Z0-9\-]*", "SDSSDE61", "SanDisk Extreme Portable SSD (Bus-Powered)"),
    (r"SDPHF1A[A-Z0-9\-]*", "SDPHF1A", "SanDisk Professional G-DRIVE Enterprise (Mains-Powered)"),
    (r"WDS[0-9]{3}[A-Z0-9\-]*", "WDS200T2X0E", "WD_BLACK SN850X NVMe SSD"),
    (r"SDSDXEP[A-Z0-9\-]*", "SDSDXEP", "SanDisk Extreme PRO SDXC UHS-II"),
    (r"SDSQXAV[A-Z0-9\-]*", "SDSQXAV", "SanDisk Extreme MicroSDXC UHS-I"),
    (r"SDEX[A-Z0-9\-]*", "SDEX-256G", "SanDisk SD Express Next-Gen PCIe"),
    (r"SDCFE[A-Z0-9\-]*", "SDCFE-512G", "SanDisk Professional PRO-CINEMA CFexpress"),
    (r"WDBMPH[A-Z0-9\-]*", "WDBMPH0010", "WD_BLACK C50 Xbox Expansion Card"),
    (r"SDDDC4[A-Z0-9\-]*", "SDDDC4", "SanDisk Ultra Dual Drive Luxe USB-C"),
    (r"WUS5EA[A-Z0-9\-]*", "WUS5EA", "Ultrastar DC SN655 Enterprise SSD"),
    (r"SDDR[\-_]?489[A-Z0-9\-]*", "SDDR-489", "SanDisk ImageMate PRO Multi-Card Reader")
]

LAB_NAMES = [
    "UL Solutions", "UL LLC", "TÜV SÜD", "TÜV Rheinland", "SGS",
    "Intertek", "Bureau Veritas", "Element Materials", "DEKRA", "Eurofins",
    "BVCPS", "Sporton", "Audix", "SanDisk Internal Compliance Lab"
]

# ----------------------------------------------------------------------
# Text Extractor Functions
# ----------------------------------------------------------------------
def extract_text_from_file(file_path: str) -> str:
    """Extracts raw string content from PDF, DOCX, XLSX, or plain text files."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(file_path)
    elif ext in [".xlsx", ".xls"]:
        return extract_text_from_xlsx(file_path)
    else:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

def extract_text_from_pdf(file_path: str) -> str:
    """Extracts text from a PDF file."""
    text_chunks = []
    if HAS_PYPDF:
        try:
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text_chunks.append(t)
        except Exception as e:
            pass

    # Fallback to regex stream search on binary data if text is empty
    if not text_chunks:
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
            found = re.findall(b"[a-zA-Z0-9\\.\\-\\:\\/\\s]{4,}", raw_bytes)
            text_chunks.append(" ".join(b.decode('ascii', errors='ignore') for b in found))
        except Exception:
            pass

    return "\n".join(text_chunks)

def extract_text_from_docx(file_path: str) -> str:
    """Extracts text from a DOCX file using python-docx or zipfile fallback."""
    if HAS_DOCX:
        try:
            doc = docx.Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs if p.text])
        except Exception:
            pass

    try:
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read("word/document.xml").decode("utf-8", errors="ignore")
            return re.sub(r"<[^>]+>", " ", xml_content)
    except Exception:
        return ""

def extract_text_from_xlsx(file_path: str) -> str:
    """Extracts text from an Excel spreadsheet."""
    if HAS_OPENPYXL:
        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            chunks = []
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                for row in ws.iter_rows(values_only=True):
                    row_str = " ".join([str(cell) for cell in row if cell is not None])
                    if row_str.strip():
                        chunks.append(row_str)
            return "\n".join(chunks)
        except Exception:
            pass
    return ""

# ----------------------------------------------------------------------
# Regulatory Entity Extraction
# ----------------------------------------------------------------------
def extract_metadata(text: str, filename: str) -> Dict[str, Any]:
    """Scans document text to extract standards, lab, product model, report number, dates."""
    meta = {
        "filename": os.path.basename(filename),
        "standards_detected": [],
        "product_sku": "General / Multi-Product",
        "product_name": "SanDisk Storage Product",
        "issuing_lab": "Unknown Test Body",
        "report_number": "N/A",
        "doc_type": "UNKNOWN_DOCUMENT",
        "issue_date": "Undated"
    }

    combined_text = filename + "\n" + text

    # 1. Detect Standards Cited
    detected_stds = set()
    for pattern, std_name in STANDARD_PATTERNS:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            matched_str = match.group(0).strip()
            detected_stds.add(matched_str)
    meta["standards_detected"] = sorted(list(detected_stds))

    # 2. Detect Product Model / SKU
    for pattern, sku, name in PRODUCT_SKU_PATTERNS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            meta["product_sku"] = sku
            meta["product_name"] = name
            break

    # 3. Detect Issuing Lab
    for lab in LAB_NAMES:
        if re.search(r"\b" + re.escape(lab) + r"\b", combined_text, re.IGNORECASE):
            meta["issuing_lab"] = lab
            break

    # 4. Detect Report / Certificate Number
    rep_match = re.search(r"(?:Report\s*(?:No|Number|#)?|Certificate\s*(?:No|#)?|Ref\s*(?:No)?)\s*[:.]?\s*([A-Z0-9\-_/]{5,25})", combined_text, re.IGNORECASE)
    if rep_match:
        meta["report_number"] = rep_match.group(1).strip()
    else:
        fn_match = re.search(r"([A-Z0-9]{3,}-[A-Z0-9]{3,}-[A-Z0-9]{2,})", filename)
        if fn_match:
            meta["report_number"] = fn_match.group(1)

    # 5. Classify Document Type
    upper_text = combined_text.upper()
    if "DECLARATION OF CONFORMITY" in upper_text or " EU DOC " in upper_text or "UKCA DOC" in upper_text:
        meta["doc_type"] = "EU_DECLARATION_OF_CONFORMITY" if "EU" in upper_text else "UKCA_DECLARATION_OF_CONFORMITY"
    elif "CB TEST CERTIFICATE" in upper_text or "CB SCHEME" in upper_text:
        meta["doc_type"] = "CB_TEST_CERTIFICATE"
    elif "TEST REPORT" in upper_text and ("62368" in upper_text or "60950" in upper_text or "SAFETY" in upper_text):
        meta["doc_type"] = "SAFETY_TEST_REPORT"
    elif "EMC" in upper_text or "FCC" in upper_text or "55032" in upper_text or "CISPR" in upper_text:
        meta["doc_type"] = "EMC_LAB_REPORT"
    elif "ROHS" in upper_text or "SUBSTANCE" in upper_text or "CHEMICAL" in upper_text or "FMD" in upper_text:
        meta["doc_type"] = "ROHS_CHEMICAL_REPORT"
    elif "PACKAGING" in upper_text or "TRIMAN" in upper_text or "ARTWORK" in upper_text or "DIE-LINE" in upper_text:
        meta["doc_type"] = "PACKAGING_ARTWORK_SPEC"
    elif "BIS" in upper_text or "CRS" in upper_text:
        meta["doc_type"] = "BIS_REGISTRATION_GRANT"
    else:
        meta["doc_type"] = "TECHNICAL_COMPLIANCE_FILE"

    # 6. Detect Date
    date_match = re.search(r"\b(20[12][0-9]-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01]))\b", combined_text)
    if date_match:
        meta["issue_date"] = date_match.group(1)
    else:
        yr_match = re.search(r"\b(20[12][0-9])\b", combined_text)
        if yr_match:
            meta["issue_date"] = yr_match.group(1)

    return meta

# ----------------------------------------------------------------------
# Impact Inference Engine
# ----------------------------------------------------------------------
def evaluate_document_impact(meta: Dict[str, Any], file_text: str) -> Dict[str, Any]:
    """Compares document metadata against active alerts and standards to evaluate regulatory impact."""
    impact = {
        "is_impacted": False,
        "impact_tier": "compliant",
        "severity": "Low",
        "trigger_alert_id": None,
        "trigger_alert_title": None,
        "obsolete_standard_cited": None,
        "required_standard": None,
        "action_directive": "Document remains valid under current regulatory framework.",
        "enforcement_deadline": "Ongoing",
        "estimated_effort": "None",
        "estimated_cost": "$0"
    }

    stds = meta.get("standards_detected", [])
    stds_str = " ".join(stds).upper()
    doc_type = meta.get("doc_type", "")
    full_text_upper = file_text.upper()

    # RULE 1: Legacy Safety Standards (IEC 60950-1 or IEC 62368-1:2014)
    if any(obs in stds_str for obs in ["60950-1", "62368-1:2014", "62368-1 2014", "EN 60950"]):
        impact["is_impacted"] = True
        if doc_type in ["EU_DECLARATION_OF_CONFORMITY", "UKCA_DECLARATION_OF_CONFORMITY"]:
            impact["impact_tier"] = "doc_amendment"
            impact["severity"] = "Warning"
            impact["trigger_alert_id"] = "ALERT-2026-02"
            impact["trigger_alert_title"] = "IEC 62368-1:2023 (4th Edition) Transition Roadmap & National Deviations"
            impact["obsolete_standard_cited"] = "EN 62368-1:2014+A11:2017 (Edition 2.0)"
            impact["required_standard"] = "EN IEC 62368-1:2020+A11:2020 / EN IEC 62368-1:2024"
            impact["enforcement_deadline"] = "2026-12-31"
            impact["action_directive"] = "EU/UKCA Declaration of Conformity cites withdrawn 2014 edition. Re-sign and issue revised DoC citing current harmonized standard EN IEC 62368-1:2020+A11:2020."
            impact["estimated_effort"] = "1 - 2 Weeks"
            impact["estimated_cost"] = "$0 (Administrative)"
            return impact
        else:
            impact["impact_tier"] = "retesting_required"
            impact["severity"] = "Critical"
            impact["trigger_alert_id"] = "ALERT-2026-02"
            impact["trigger_alert_title"] = "IEC 62368-1:2023 (4th Edition) Transition Roadmap & National Deviations"
            impact["obsolete_standard_cited"] = "IEC 60950-1 / IEC 62368-1:2014 (Edition 2.0)"
            impact["required_standard"] = "IEC 62368-1:2023 (Edition 4.0)"
            impact["enforcement_deadline"] = "2026-12-31"
            impact["action_directive"] = "Legacy safety standard has reached full global sunset. Must dispatch production hardware to accredited lab (UL/TÜV) for complete Edition 4.0 safety testing."
            impact["estimated_effort"] = "6 - 8 Weeks"
            impact["estimated_cost"] = "$4,500 - $7,000"
            return impact

    # RULE 2: Safety 3rd Edition (IEC 62368-1:2018) -> 4th Edition Gap Analysis
    if "62368-1:2018" in stds_str or ("62368-1" in stds_str and "2023" not in stds_str and "2024" not in stds_str):
        impact["is_impacted"] = True
        if doc_type in ["SAFETY_TEST_REPORT", "CB_TEST_CERTIFICATE"]:
            impact["impact_tier"] = "retesting_required"
            impact["severity"] = "Warning"
            impact["trigger_alert_id"] = "ALERT-2026-02"
            impact["trigger_alert_title"] = "IEC 62368-1:2023 (4th Edition) Transition Roadmap & National Deviations"
            impact["obsolete_standard_cited"] = "IEC 62368-1:2018 (Edition 3.0)"
            impact["required_standard"] = "IEC 62368-1:2023 (Edition 4.0)"
            impact["enforcement_deadline"] = "2027-06-30"
            impact["action_directive"] = "CB Safety Report cites 3rd Edition. Order laboratory gap analysis for Edition 4.0 amendments (thermal classification Clause 5.4 and enclosure fire barriers)."
            impact["estimated_effort"] = "3 - 4 Weeks"
            impact["estimated_cost"] = "$1,500 - $3,000"
            return impact
        elif doc_type in ["EU_DECLARATION_OF_CONFORMITY", "UKCA_DECLARATION_OF_CONFORMITY"]:
            impact["impact_tier"] = "doc_amendment"
            impact["severity"] = "Warning"
            impact["trigger_alert_id"] = "ALERT-2026-02"
            impact["trigger_alert_title"] = "IEC 62368-1:2023 (4th Edition) Transition Roadmap & National Deviations"
            impact["obsolete_standard_cited"] = "EN 62368-1:2014+A11:2017"
            impact["required_standard"] = "EN IEC 62368-1:2020+A11:2020 / EN IEC 62368-1:2024"
            impact["enforcement_deadline"] = "2026-12-31"
            impact["action_directive"] = "EU/UKCA Declaration of Conformity cites obsolete standard. Re-issue and digitally sign updated DoC citing EN IEC 62368-1:2020+A11:2020."
            impact["estimated_effort"] = "1 - 2 Weeks"
            impact["estimated_cost"] = "$0 (Internal)"
            return impact

    # RULE 3: Legacy Multimedia Emissions (EN 55022 / CISPR 22)
    if "55022" in stds_str or "CISPR 22" in stds_str or "CISPR-22" in stds_str:
        impact["is_impacted"] = True
        impact["impact_tier"] = "retesting_required"
        impact["severity"] = "Critical"
        impact["trigger_alert_id"] = "ALERT-2026-03"
        impact["trigger_alert_title"] = "ETSI EN 303 645 & RED Article 3.3 Cybersecurity & Emissions Directives"
        impact["obsolete_standard_cited"] = "EN 55022 / CISPR 22"
        impact["required_standard"] = "CISPR 32:2015+A1:2019 / EN 55032:2015+A11:2020 Class B"
        impact["enforcement_deadline"] = "Immediate (Withdrawn)"
        impact["action_directive"] = "Report cites withdrawn standard. Radiated and conducted emissions re-test required under CISPR 32 Class B."
        impact["estimated_effort"] = "3 - 5 Weeks"
        impact["estimated_cost"] = "$3,500 - $5,000"
        return impact

    # RULE 4: US TSCA Section 8(a)(7) PFAS Substance Reporting
    if ("NOT EVALUATED" in full_text_upper or "POTENTIAL FLUOROPOLYMER" in full_text_upper or 
        ((doc_type in ["ROHS_CHEMICAL_REPORT", "TECHNICAL_COMPLIANCE_FILE"] or "ROHS" in stds_str) and "PFAS" not in full_text_upper and "TSCA" not in full_text_upper)):
        impact["is_impacted"] = True
        impact["impact_tier"] = "doc_amendment"
        impact["severity"] = "Critical"
        impact["trigger_alert_id"] = "ALERT-ENV-01"
        impact["trigger_alert_title"] = "US EPA TSCA Section 8(a)(7) — Mandatory Reporting of PFAS in Electronic Articles"
        impact["obsolete_standard_cited"] = "TSCA Historic Baseline (Unscreened Fluoropolymers)"
        impact["required_standard"] = "TSCA 40 CFR Part 705 (PFAS Reporting Rule)"
        impact["enforcement_deadline"] = "2026-05-08"
        impact["action_directive"] = "BOM disclosure contains unverified fluoropolymers/PFAS in thermal gap pads or wire jackets. Issue IPC-1752A Class D chemical inquiries to vendors for EPA CDX reporting."
        impact["estimated_effort"] = "3 - 4 Weeks"
        impact["estimated_cost"] = "$800 - $1,500"
        return impact

    # RULE 5: Packaging Artwork Missing Triman or Material Coding
    if doc_type == "PACKAGING_ARTWORK_SPEC" or "PACKAGING" in full_text_upper or "DIE-LINE" in full_text_upper:
        missing_items = []
        if "TRIMAN" not in full_text_upper and "INFO-TRI" not in full_text_upper:
            missing_items.append("France Triman / Info-tri sorting logo (Decree 2021-835)")
        if "PAP 20" not in full_text_upper and "129/97/EC" not in full_text_upper and "116/2020" not in full_text_upper:
            missing_items.append("Italy alphanumeric material identification (PAP 20 / Decision 129/97/EC)")

        if missing_items:
            impact["is_impacted"] = True
            impact["impact_tier"] = "packaging_update"
            impact["severity"] = "Critical"
            impact["trigger_alert_id"] = "ALERT-ENV-03"
            impact["trigger_alert_title"] = "France AGEC Law & Italy Legislative Decree 116/2020 Packaging Mandates"
            impact["obsolete_standard_cited"] = "Generic Mobius Loop / Uncoded Plastic Packaging"
            impact["required_standard"] = "Triman Info-tri (France) & Alphanumeric Coding PAP 20 (Italy D.Lgs 116/2020)"
            impact["enforcement_deadline"] = "Active Enforcement"
            impact["action_directive"] = f"Master retail packaging artwork is missing mandatory European sorting marks: {'; '.join(missing_items)}. Issue revised vector die-line to factory printer."
            impact["estimated_effort"] = "2 - 3 Weeks"
            impact["estimated_cost"] = "Printer Plate Fee (~$400)"
            return impact

    # RULE 6: India BIS / CRS Expiry or Amendment
    if doc_type == "BIS_REGISTRATION_GRANT" or "BIS" in stds_str or "IS 13252" in stds_str:
        if "AMENDMENT" not in full_text_upper and ("2021" in full_text_upper or "2022" in full_text_upper or "2023" in full_text_upper):
            impact["is_impacted"] = True
            impact["impact_tier"] = "portal_filing"
            impact["severity"] = "Warning"
            impact["trigger_alert_id"] = "ALERT-ENV-05"
            impact["trigger_alert_title"] = "India E-Waste Management Rules 2022 & BIS CRS Surveillance"
            impact["obsolete_standard_cited"] = "IS 13252 (Part 1):2010 Baseline"
            impact["required_standard"] = "IS 13252:2010 / Gazette Renewal & CPCB EPR Portal Linkage"
            impact["enforcement_deadline"] = "2026-10-31"
            impact["action_directive"] = "Certificate requires annual renewal verification and linkage to the centralized CPCB Extended Producer Responsibility portal."
            impact["estimated_effort"] = "2 Weeks"
            impact["estimated_cost"] = "Statutory BIS Fee (~$350)"
            return impact

    # If standards cited match modern baseline, mark compliant
    if any(good in stds_str for good in ["62368-1:2023", "CISPR 32:2015", "2015/863", "TRIMAN", "705"]):
        impact["action_directive"] = "Document verified compliant against modern harmonized technical regulations."

    return impact

# ----------------------------------------------------------------------
# Folder Scanner Orchestrator
# ----------------------------------------------------------------------
def scan_directory(folder_path: str) -> Dict[str, Any]:
    """
    Recursively scans a directory on the local Windows device,
    parses all documents, and returns an executive regulatory audit report.
    """
    if not os.path.isdir(folder_path):
        return {
            "error": f"Folder '{folder_path}' does not exist or is not a valid directory.",
            "total_documents": 0,
            "impacted_documents": 0,
            "documents": []
        }

    supported_exts = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".json", ".csv", ".xml"}
    
    total_scanned = 0
    impacted_count = 0
    tier_counts = {
        "retesting_required": 0,
        "doc_amendment": 0,
        "packaging_update": 0,
        "portal_filing": 0,
        "compliant": 0
    }
    
    results = []

    for root, _, files in os.walk(folder_path):
        for f in sorted(files):
            ext = os.path.splitext(f)[1].lower()
            if ext in supported_exts:
                total_scanned += 1
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, folder_path)
                file_size = os.path.getsize(full_path)

                # Extract text
                text = extract_text_from_file(full_path)

                # Extract metadata
                meta = extract_metadata(text, f)
                meta["file_path"] = full_path
                meta["relative_path"] = rel_path
                meta["file_size_kb"] = round(file_size / 1024, 1)

                # Evaluate Impact
                impact = evaluate_document_impact(meta, text)

                if impact["is_impacted"]:
                    impacted_count += 1

                tier_counts[impact["impact_tier"]] = tier_counts.get(impact["impact_tier"], 0) + 1

                combined_record = {
                    "metadata": meta,
                    "impact": impact
                }
                results.append(combined_record)

    def sort_key(item):
        tier = item["impact"]["impact_tier"]
        tier_order = {
            "retesting_required": 0,
            "packaging_update": 1,
            "doc_amendment": 2,
            "portal_filing": 3,
            "compliant": 4
        }
        return (tier_order.get(tier, 5), item["metadata"]["filename"])

    results.sort(key=sort_key)

    return {
        "folder_path": folder_path,
        "scan_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_documents": total_scanned,
        "impacted_documents": impacted_count,
        "tier_summary": tier_counts,
        "documents": results
    }

# ----------------------------------------------------------------------
# Excel Export Generator
# ----------------------------------------------------------------------
def export_audit_to_excel(audit_data: Dict[str, Any]) -> io.BytesIO:
    """Generates an executive Excel workbook containing the Document Revision Directive."""
    output = io.BytesIO()
    if not HAS_OPENPYXL:
        return output

    wb = openpyxl.Workbook()
    
    # Sheet 1: Executive Summary
    ws_sum = wb.active
    ws_sum.title = "Executive Summary"
    ws_sum.append(["SanDisk Global Compliance Management (GCM) Platform"])
    ws_sum.append(["Document-Level Regulatory Impact Audit Directive"])
    ws_sum.append([])
    ws_sum.append(["Scanned Directory:", audit_data.get("folder_path", "N/A")])
    ws_sum.append(["Audit Date & Time:", audit_data.get("scan_timestamp", "N/A")])
    ws_sum.append(["Total Compliance Documents Scanned:", audit_data.get("total_documents", 0)])
    ws_sum.append(["Total Documents Requiring Immediate Revision:", audit_data.get("impacted_documents", 0)])
    ws_sum.append([])
    ws_sum.append(["Impact Tier Breakdown:", "Document Count"])
    
    tiers = audit_data.get("tier_summary", {})
    ws_sum.append(["🔴 Full Laboratory Re-Testing Required (Safety / EMC)", tiers.get("retesting_required", 0)])
    ws_sum.append(["📦 Packaging Artwork & Sorting Mark Revisions", tiers.get("packaging_update", 0)])
    ws_sum.append(["🟡 Paperwork & DoC Amendments (Declarations / Standards)", tiers.get("doc_amendment", 0)])
    ws_sum.append(["🔵 Government Portal & Registration Filings", tiers.get("portal_filing", 0)])
    ws_sum.append(["🟢 Compliant / Valid (No Action Required)", tiers.get("compliant", 0)])

    # Sheet 2: Action Directive Table
    ws_det = wb.create_sheet(title="Document Revision Directive")
    headers = [
        "File Name",
        "Document Type",
        "Product Model / SKU",
        "Issuing Body / Lab",
        "Report Number",
        "Impact Tier",
        "Severity",
        "Trigger Alert ID",
        "Obsolete Standard Cited",
        "Required Modern Standard",
        "Enforcement Deadline",
        "Action Directive for Engineering / Lab",
        "Est. Effort",
        "Est. Cost"
    ]
    ws_det.append(headers)

    for item in audit_data.get("documents", []):
        m = item["metadata"]
        imp = item["impact"]
        row = [
            m.get("filename", ""),
            m.get("doc_type", ""),
            f"{m.get('product_name', '')} ({m.get('product_sku', '')})",
            m.get("issuing_lab", ""),
            m.get("report_number", ""),
            imp.get("impact_tier", "").replace("_", " ").title(),
            imp.get("severity", ""),
            imp.get("trigger_alert_id", ""),
            imp.get("obsolete_standard_cited", "N/A"),
            imp.get("required_standard", "N/A"),
            imp.get("enforcement_deadline", ""),
            imp.get("action_directive", ""),
            imp.get("estimated_effort", ""),
            imp.get("estimated_cost", "")
        ]
        ws_det.append(row)

    for ws in [ws_sum, ws_det]:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 60)

    wb.save(output)
    output.seek(0)
    return output

def make_multiline_pdf(lines: list) -> bytes:
    """Helper to synthesize valid single-page PDF with text stream."""
    escaped_cmds = ["BT /F1 10 Tf 14 TL 50 740 Td"]
    for line in lines:
        escaped_line = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        escaped_cmds.append(f"({escaped_line}) '")
    escaped_cmds.append("ET")
    
    stream_data = "\n".join(escaped_cmds).encode('latin-1', 'replace')
    obj4 = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream_data), stream_data)
    
    parts = []
    parts.append(b"%PDF-1.4\n")
    
    offsets = []
    offsets.append(len(b"".join(parts)))
    parts.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    
    offsets.append(len(b"".join(parts)))
    parts.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    
    offsets.append(len(b"".join(parts)))
    parts.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")
    
    offsets.append(len(b"".join(parts)))
    parts.append(b"4 0 obj\n" + obj4 + b"\nendobj\n")
    
    offsets.append(len(b"".join(parts)))
    parts.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    
    xref_offset = len(b"".join(parts))
    parts.append(b"xref\n0 6\n0000000000 65535 f \n")
    for off in offsets:
        parts.append(f"{off:010d} 00000 n \n".encode('ascii'))
        
    parts.append(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode('ascii'))
    return b"".join(parts)

def generate_sample_compliance_docs(target_dir=r"C:\SanDisk\Compliance_Docs"):
    """Generates authentic SanDisk compliance files for testing."""
    os.makedirs(target_dir, exist_ok=True)

    # 1. Obsolete Safety Report (Triggers Full Lab Re-Testing)
    p1 = os.path.join(target_dir, "CB_Report_E143284_SanDisk_Extreme_SSD_E61.pdf")
    lines1 = [
        "UL Solutions CB Scheme Test Certificate & Report",
        "Report Number: E143284-A6012-CB-1",
        "Applicant: Western Digital Technologies, Inc.",
        "Product: SanDisk Extreme Portable SSD (Bus-Powered) Model SDSSDE61",
        "Harmonized Technical Standard: IEC 62368-1:2014 (Second Edition)",
        "Issuing Body: UL Solutions Northbrook Laboratory",
        "Ratings: 5V DC, 2.5A SELV (Class III)",
        "Issue Date: 2019-08-14",
        "Status: Test report evaluated under legacy Edition 2.0."
    ]
    with open(p1, "wb") as f:
        f.write(make_multiline_pdf(lines1))

    # 2. Obsolete EU Declaration of Conformity (Triggers DoC Revision)
    p2 = os.path.join(target_dir, "EU_Declaration_of_Conformity_G-DRIVE_Enterprise.pdf")
    lines2 = [
        "EU DECLARATION OF CONFORMITY (DoC Ref: DOC-EU-2022-GDRIVE)",
        "Manufacturer: Western Digital Technologies, Inc.",
        "Product Name: SanDisk Professional G-DRIVE Enterprise Desktop (18TB)",
        "Model / SKU: SDPHF1A-018T-NBAAD",
        "Low Voltage Directive 2014/35/EU: Harmonized Standard EN 62368-1:2014+A11:2017",
        "EMC Directive 2014/30/EU: Harmonized Standard EN 55032:2015 Class B",
        "RoHS Directive 2011/65/EU on the restriction of hazardous substances",
        "Authorized Signatory: Global Regulatory Compliance Director, SanDisk",
        "Date of Issue: 2022-03-10"
    ]
    with open(p2, "wb") as f:
        f.write(make_multiline_pdf(lines2))

    # 3. Modern Compliant EMC Lab Report (Triggers Compliant)
    p3 = os.path.join(target_dir, "EMC_Test_Report_WD_BLACK_SN850X_NVMe.pdf")
    lines3 = [
        "TUV SUD America Test Report Ref: EMC-TR-2024-9182",
        "Client: Western Digital Corporation",
        "Product: WD_BLACK SN850X NVMe SSD (2TB)",
        "Model / SKU: WDS200T2X0E",
        "Tested Standards:",
        "- CISPR 32:2015+A1:2019 Class B (Radio Disturbance Characteristics)",
        "- FCC Part 15B Class B Unintentional Radiators",
        "- EN 55032:2015+A11:2020",
        "Laboratory: TUV SUD San Diego Testing Facility",
        "Date of Test: 2024-02-18",
        "Result: PASS - Fully Compliant with Modern Emissions Limits."
    ]
    with open(p3, "wb") as f:
        f.write(make_multiline_pdf(lines3))

    # 4. Packaging Artwork Spec Missing France Triman & Italy Coding (Triggers Packaging Revision)
    p4 = os.path.join(target_dir, "Packaging_Artwork_Spec_Extreme_PRO_SDXC.docx")
    if HAS_DOCX:
        doc = docx.Document()
        doc.add_heading("SanDisk Retail Packaging Master Specification", 0)
        doc.add_paragraph("Product Family: SanDisk Extreme PRO SDXC UHS-II (512GB)")
        doc.add_paragraph("Master SKU: SDSDXEP-512G-GN4IN")
        doc.add_paragraph("Packaging Substrate: SBS Bleached Sulfate Paperboard (Inner Blister: Thermoformed PET)")
        doc.add_paragraph("Regulatory Marking Requirements on Exterior Carton:")
        doc.add_paragraph("- CE Mark minimum height: 5.0 mm")
        doc.add_paragraph("- UKCA Mark minimum height: 5.0 mm")
        doc.add_paragraph("- WEEE Crossed-Out Wheelie Bin Symbol (Directive 2012/19/EU)")
        doc.add_paragraph("- Standard Mobius Loop generic recycling symbol")
        doc.add_paragraph("Notice: Document does not contain France Triman logo or Italy alphanumeric packaging material identification code.")
        doc.save(p4)

    # 5. India BIS CRS Letter Needing Renewal Verification (Triggers Portal Filing)
    p5 = os.path.join(target_dir, "BIS_CRS_Registration_Grant_G-DRIVE_India.pdf")
    lines5 = [
        "BUREAU OF INDIAN STANDARDS (Central Marks Department)",
        "Registration Grant Letter Ref: BIS/CRS/REG-41009823",
        "Manufacturer: Western Digital Technologies, Inc.",
        "Standard: IS 13252 (Part 1):2010 Safety of Information Technology Equipment",
        "Product: External Storage Drive (Mains-Powered)",
        "Brand: SanDisk Professional Model SDPHF1A",
        "Date of Grant: 2021-11-20",
        "Renewal Status: Requires annual renewal verification under E-Waste Rules 2022."
    ]
    with open(p5, "wb") as f:
        f.write(make_multiline_pdf(lines5))

    # 6. Full Material Disclosure (FMD) Spreadsheet (Triggers TSCA PFAS Audit)
    p6 = os.path.join(target_dir, "Full_Material_Disclosure_FMD_C50_Xbox.xlsx")
    if HAS_OPENPYXL:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BOM Substance Disclosure"
        ws.append(["Component Name", "Part Number", "Supplier", "Material Classification", "RoHS Compliance", "REACH SVHC Status", "TSCA PFAS Disclosure"])
        ws.append(["NAND Flash Wafer", "05436-128G", "Kioxia / SanDisk JV", "Epoxy Molding Compound", "RoHS Compliant", "No SVHC >0.1%", "Not Evaluated"])
        ws.append(["Velocity ASIC Controller", "20-82-01048-A1", "TSMC", "Semiconductor Silicon", "RoHS Compliant", "No SVHC >0.1%", "Not Evaluated"])
        ws.append(["FR-4 Printed Circuit Board", "PCB-C50-REV3", "AT&S", "Copper Clad Laminate / Glass Fiber", "RoHS Compliant", "TBBP-A Present in Resin", "Not Evaluated"])
        ws.append(["Thermal Gap Pad", "TP-3000-05", "Bergquist", "Silicone Polymer", "RoHS Compliant", "No SVHC", "Potential Fluoropolymer Content"])
        ws.append(["Aluminum Enclosure Heatsink", "ENC-AL-C50", "Foxconn", "Aluminum 6063-T6", "RoHS Compliant", "No SVHC", "PFAS Free"])
        wb.save(p6)

    return target_dir

