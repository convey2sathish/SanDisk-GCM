"""
doc_audit_engine.py - Document Impact Audit engine v2 (GCM Platform 2.0).

Ingests a folder (or an uploaded set) of compliance documents - CB certificates,
safety / EMC test reports, declarations of conformity, packaging artwork specs,
RoHS / FMD chemical disclosures, national registrations (BIS, KC, BSMI, CCC, PSE,
SASO), energy-efficiency reports, SBOM / cybersecurity files - extracts their
regulatory metadata, evaluates each one against a *dynamic rulebook* built from
static standards knowledge plus the platform's live regulatory alerts, and
produces the "Audit report v2" described in docs/ARCHITECTURE_CONTRACT.md §4.

Public API (kept from v1, extended with keyword arguments):
    extract_text_from_file(path) -> str
    extract_metadata(text, filename, products=None) -> dict
    evaluate_document_impact(meta, text, alerts=None, products=None) -> dict
    scan_directory(folder_path, recursive=True, alerts=None, products=None) -> report
    scan_files(paths, alerts=None, products=None, display_root=None) -> report
    explain_document(doc_record, alerts=None) -> dict
    export_audit_to_excel(report) -> io.BytesIO
    generate_sample_compliance_docs(target_dir) -> list[str]
    make_multiline_pdf(lines) -> bytes

All cost figures produced by this module are indicative planning estimates in USD
(typical third-party lab / agency fees), not quotations. Regulatory dates that come
from live alerts are taken from the alert's `effective_date`; static fallbacks are
documented next to each rule.
"""
import datetime as _dt
import io
import json
import os
import re
import time
import zipfile
from typing import Any, Dict, List, Optional, Tuple

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:  # pragma: no cover
    pypdf = None
    HAS_PYPDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:  # pragma: no cover
    docx = None
    HAS_DOCX = False

try:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:  # pragma: no cover
    openpyxl = None
    HAS_OPENPYXL = False

import compliance_db as db

try:
    import reg_surveillance as _rs
except Exception:  # pragma: no cover
    _rs = None

ENGINE_VERSION = "2.0.0"
MAX_FILE_BYTES = 50 * 1024 * 1024
SUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".xlsx", ".xlsm", ".xls", ".csv", ".txt", ".json", ".xml", ".md"}
LEGACY_BINARY_EXTS = {".doc", ".xls"}

TIERS = ("retesting_required", "doc_amendment", "packaging_update", "portal_filing", "compliant", "unreadable")
TIER_LABELS = {
    "retesting_required": "Laboratory re-testing required",
    "doc_amendment": "Document amendment / re-sign",
    "packaging_update": "Packaging artwork update",
    "portal_filing": "Portal filing / renewal",
    "compliant": "Compliant - no action",
    "unreadable": "Unreadable - manual review",
}
TIER_RANK = {"retesting_required": 4, "packaging_update": 3, "doc_amendment": 2, "portal_filing": 1, "compliant": 0, "unreadable": 0}
SEVERITY_RANK = {"Critical": 3, "Warning": 2, "Info": 1, "None": 0}
CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}

EU_COUNTRIES = set(getattr(_rs, "EU_COUNTRIES", {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
                                                 "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}))
EEA_EXTRA = {"IS", "NO", "LI", "CH"}
FIRMWARE_CATEGORIES = {"internal_ssd", "external_ssd_bus", "external_ssd_powered", "enterprise_ssd", "usb_drive", "card_reader", "sd_express"}

# --------------------------------------------------------------------------- document types
DOC_TYPES = (
    "CB_TEST_CERTIFICATE", "SAFETY_TEST_REPORT", "EMC_LAB_REPORT", "EU_DECLARATION_OF_CONFORMITY",
    "UKCA_DECLARATION_OF_CONFORMITY", "FCC_SDOC", "PACKAGING_ARTWORK_SPEC", "ROHS_CHEMICAL_REPORT",
    "FMD_BOM_DISCLOSURE", "BIS_REGISTRATION_GRANT", "KC_CERTIFICATE", "BSMI_CERTIFICATE", "CCC_CERTIFICATE",
    "PSE_CERTIFICATE", "SASO_SABER_CERTIFICATE", "ENERGY_EFFICIENCY_REPORT", "CYBERSECURITY_SBOM",
    "TECHNICAL_COMPLIANCE_FILE", "UNKNOWN",
)
DOC_TYPE_LABELS = {
    "CB_TEST_CERTIFICATE": "CB Test Certificate", "SAFETY_TEST_REPORT": "Safety Test Report", "EMC_LAB_REPORT": "EMC Lab Report",
    "EU_DECLARATION_OF_CONFORMITY": "EU Declaration of Conformity", "UKCA_DECLARATION_OF_CONFORMITY": "UKCA Declaration of Conformity",
    "FCC_SDOC": "FCC Supplier's DoC", "PACKAGING_ARTWORK_SPEC": "Packaging Artwork Spec", "ROHS_CHEMICAL_REPORT": "RoHS / Chemical Report",
    "FMD_BOM_DISCLOSURE": "Full Material Disclosure (BOM)", "BIS_REGISTRATION_GRANT": "BIS CRS Registration", "KC_CERTIFICATE": "KC Certificate (Korea)",
    "BSMI_CERTIFICATE": "BSMI Certificate (Taiwan)", "CCC_CERTIFICATE": "CCC Certificate (China)", "PSE_CERTIFICATE": "PSE Certificate (Japan)",
    "SASO_SABER_CERTIFICATE": "SASO / SABER Certificate", "ENERGY_EFFICIENCY_REPORT": "Energy Efficiency Report", "CYBERSECURITY_SBOM": "Cybersecurity / SBOM",
    "TECHNICAL_COMPLIANCE_FILE": "Technical Compliance File", "UNKNOWN": "Unclassified document",
}
# doc class drives which tier a superseded-standard citation maps to
DOC_CLASS = {
    "CB_TEST_CERTIFICATE": "report", "SAFETY_TEST_REPORT": "report", "EMC_LAB_REPORT": "report", "ENERGY_EFFICIENCY_REPORT": "report",
    "ROHS_CHEMICAL_REPORT": "report",
    "EU_DECLARATION_OF_CONFORMITY": "declaration", "UKCA_DECLARATION_OF_CONFORMITY": "declaration", "FCC_SDOC": "declaration",
    "TECHNICAL_COMPLIANCE_FILE": "declaration", "FMD_BOM_DISCLOSURE": "declaration", "CYBERSECURITY_SBOM": "declaration",
    "BIS_REGISTRATION_GRANT": "registration", "KC_CERTIFICATE": "registration", "BSMI_CERTIFICATE": "registration",
    "CCC_CERTIFICATE": "registration", "PSE_CERTIFICATE": "registration", "SASO_SABER_CERTIFICATE": "registration",
    "PACKAGING_ARTWORK_SPEC": "packaging", "UNKNOWN": "declaration",
}
CLASS_TIER = {"report": "retesting_required", "declaration": "doc_amendment", "registration": "portal_filing", "packaging": "packaging_update"}
DOC_TYPE_PILLARS = {
    "CB_TEST_CERTIFICATE": {"Safety"}, "SAFETY_TEST_REPORT": {"Safety"}, "EMC_LAB_REPORT": {"EMC"}, "FCC_SDOC": {"EMC"},
    "EU_DECLARATION_OF_CONFORMITY": {"Safety", "EMC", "Environmental", "Cyber"}, "UKCA_DECLARATION_OF_CONFORMITY": {"Safety", "EMC", "Environmental", "Cyber"},
    "PACKAGING_ARTWORK_SPEC": {"Environmental"}, "ROHS_CHEMICAL_REPORT": {"Environmental"}, "FMD_BOM_DISCLOSURE": {"Environmental"},
    "BIS_REGISTRATION_GRANT": {"Safety"}, "KC_CERTIFICATE": {"Safety", "EMC"}, "BSMI_CERTIFICATE": {"Safety", "EMC", "Environmental"},
    "CCC_CERTIFICATE": {"Safety"}, "PSE_CERTIFICATE": {"Safety"}, "SASO_SABER_CERTIFICATE": {"Environmental", "Safety"},
    "ENERGY_EFFICIENCY_REPORT": {"Environmental"}, "CYBERSECURITY_SBOM": {"Cyber"}, "TECHNICAL_COMPLIANCE_FILE": {"Safety", "EMC", "Environmental", "Cyber"},
    "UNKNOWN": set(),
}
# typical validity used when the document does not state an expiry (marked expiry_inferred)
INFERRED_VALIDITY_YEARS = {
    "CB_TEST_CERTIFICATE": 3,        # CB certificates carry no formal expiry; 3 years is the common NCB review horizon
    "BIS_REGISTRATION_GRANT": 2,     # BIS CRS registrations are granted for 2 years (renewable)
    "KC_CERTIFICATE": 5,             # KC safety certificates: periodic factory surveillance; 5-year renewal is common practice
    "BSMI_CERTIFICATE": 3,           # BSMI RPC certificates are valid 3 years
    "CCC_CERTIFICATE": 5,            # CCC certificates are valid 5 years subject to annual follow-up inspection
    "SASO_SABER_CERTIFICATE": 1,     # SABER Product CoC is valid 1 year
}

# keyword scoring for classification: (doc_type, [(regex, weight), ...]); threshold applied in classify_doc_type
DOC_TYPE_RULES = [
    ("CB_TEST_CERTIFICATE", [(r"CB\s+test\s+certificate", 6), (r"\bCB\s+scheme\b", 3), (r"\bIECEE\b", 3), (r"test\s+report\s+form|\bTRF\b", 2), (r"\bNCB\b", 2), (r"CB[\s_-]report", 3)]),
    ("SAFETY_TEST_REPORT", [(r"safety\s+test\s+report", 6), (r"\btest\s+report\b", 2), (r"\bsafety\b", 1), (r"6236[8]-1|60950-1|13252|4943|15598", 2), (r"\bLVD\b|low\s+voltage\s+directive", 1)]),
    ("EMC_LAB_REPORT", [(r"EMC\s+test\s+report", 6), (r"\bEMC\b", 2), (r"emissions?\b", 2), (r"\bCISPR\b", 2), (r"5503[25]|55022|9254|KN\s?3[25]|CNS\s?15936|C63\.4", 2), (r"radiated|conducted", 1), (r"immunity", 1)]),
    ("EU_DECLARATION_OF_CONFORMITY", [(r"EU\s+declaration\s+of\s+conformity", 7), (r"declaration\s+of\s+conformity", 3), (r"2014/30/EU|2014/35/EU|2011/65/EU|2014/53/EU", 2), (r"\bCE\s+mark", 1), (r"harmoni[sz]ed\s+standard", 1)]),
    ("UKCA_DECLARATION_OF_CONFORMITY", [(r"UK(?:CA)?\s+declaration\s+of\s+conformity", 7), (r"\bUKCA\b", 4), (r"Regulations\s+2016|S\.I\.\s+2016", 2), (r"BS\s+EN\s+\d{5}", 1)]),
    ("FCC_SDOC", [(r"supplier'?s?\s+declaration\s+of\s+conformity", 6), (r"\bSDoC\b", 4), (r"\bFCC\b", 2), (r"47\s+CFR|\bPart\s+15\b", 2), (r"responsible\s+party", 2), (r"unintentional\s+radiator", 1)]),
    ("PACKAGING_ARTWORK_SPEC", [(r"packaging", 3), (r"artwork", 3), (r"die[\s-]?line", 3), (r"\bcarton\b", 2), (r"\bblister\b", 1), (r"Triman|Info[\s-]?tri", 2), (r"recycl", 1), (r"\bPAP\s?2[0-2]\b", 2)]),
    ("FMD_BOM_DISCLOSURE", [(r"full\s+material\s+disclosure", 6), (r"\bFMD\b", 4), (r"bill\s+of\s+materials|\bBOM\b", 3), (r"IPC[\s-]?1752", 3), (r"substance\s+disclosure", 2), (r"homogeneous\s+material", 1)]),
    ("ROHS_CHEMICAL_REPORT", [(r"RoHS\s+test\s+report", 6), (r"\bRoHS\b", 2), (r"IEC\s?62321", 3), (r"\bXRF\b|ICP[\s-]?OES", 2), (r"hazardous\s+substances?", 2), (r"chemical\s+(?:test|analysis)", 2), (r"\bSVHC\b", 1)]),
    ("BIS_REGISTRATION_GRANT", [(r"Bureau\s+of\s+Indian\s+Standards", 6), (r"\bBIS\b", 2), (r"\bCRS\b", 2), (r"registration\s+(?:grant|letter|no)", 2), (r"\bR-\d{8}\b", 3), (r"IS\s?13252|IS/IEC\s?62368", 2), (r"\bMeitY\b|\bNABL\b", 1)]),
    ("KC_CERTIFICATE", [(r"KC\s+(?:safety\s+)?certificate|certificate\s+of\s+KC", 6), (r"\bKC\s+mark\b", 2), (r"\bKATS\b|\bRRA\b", 3), (r"\bR-R-[A-Z0-9]", 3), (r"\bKorea\b", 1), (r"KN\s?3[25]|KS\s?C\s?98", 2), (r"conformity\s+registration", 1)]),
    ("BSMI_CERTIFICATE", [(r"\bBSMI\b", 5), (r"Bureau\s+of\s+Standards,?\s+Metrology", 6), (r"CNS\s?1(?:5936|5598|3438|5663)", 2), (r"\bRPC\b", 2), (r"\bTaiwan\b", 1)]),
    ("CCC_CERTIFICATE", [(r"China\s+Compulsory\s+Certification", 6), (r"\bCCC\b", 4), (r"\bCQC\b|\bCNCA\b", 3), (r"GB\s?4943", 2), (r"\bChina\b", 1)]),
    ("PSE_CERTIFICATE", [(r"Electrical\s+Appliance\s+and\s+Material\s+Safety", 6), (r"\bPSE\b", 4), (r"\bMETI\b", 3), (r"\bDENAN\b", 3), (r"J\s?62368", 2), (r"\bJapan\b", 1)]),
    ("SASO_SABER_CERTIFICATE", [(r"\bSABER\b", 5), (r"\bSASO\b", 4), (r"\bPCoC\b|\bSCoC\b", 3), (r"Saudi", 1), (r"\bGSO\b", 1)]),
    ("ENERGY_EFFICIENCY_REPORT", [(r"energy\s+efficiency", 4), (r"Level\s+VI", 4), (r"10\s+CFR\s+(?:Part\s+)?430", 4), (r"2019/1782", 4), (r"no[\s-]load\s+power", 3), (r"\bErP\b|Ecodesign", 2), (r"\bMEPS\b|\bCEC\b\s+Title\s+20", 2)]),
    ("CYBERSECURITY_SBOM", [(r"\bSBOM\b", 5), (r"software\s+bill\s+of\s+materials", 5), (r"CycloneDX|\bSPDX\b", 4), (r"EN\s?18031|2024/2847|Cyber\s+Resilience", 3), (r"vulnerab", 2), (r"firmware\s+sign", 2), (r"\bPSTI\b", 3), (r"EN\s?303\s?645", 3)]),
    ("TECHNICAL_COMPLIANCE_FILE", [(r"technical\s+(?:construction\s+)?file", 5), (r"technical\s+documentation", 3), (r"risk\s+assessment", 1), (r"compliance\s+file", 3)]),
]
DOC_TYPE_THRESHOLD = 4

# --------------------------------------------------------------------------- standards catalog
# canonical -> knowledge. `current`: edition years considered current; `superseded`: {year: replacement text};
# `withdrawn`: the whole standard is withdrawn (any edition superseded); `replacement`: text used when withdrawn.
STANDARDS_CATALOG = {
    "IEC 62368-1": {"pillar": "Safety", "current": [2023], "superseded": {2014: "IEC 62368-1:2023 (Edition 4.0)", 2018: "IEC 62368-1:2023 (Edition 4.0)"},
                    "edition_years": {2: 2014, 3: 2018, 4: 2023}, "alert_keywords": ["62368-1:2023", "4th Edition"]},
    "EN 62368-1": {"pillar": "Safety", "current": [2020, 2024], "superseded": {2014: "EN IEC 62368-1:2020+A11:2020"}, "edition_years": {2: 2014, 3: 2020},
                   "alert_keywords": ["62368-1:2023", "4th Edition"]},
    "UL 62368-1": {"pillar": "Safety", "current": [2019, 2023], "superseded": {2014: "UL 62368-1 Third Edition (2019) / Fourth Edition (2023)"}, "alert_keywords": ["62368-1:2023"]},
    "CSA C22.2 No. 62368-1": {"pillar": "Safety", "current": [2019, 2023], "superseded": {}, "alert_keywords": ["62368-1:2023"]},
    "IEC 60950-1": {"pillar": "Safety", "withdrawn": True, "replacement": "IEC 62368-1:2023 (Edition 4.0)", "alert_keywords": ["62368-1:2023", "60950"]},
    "EN 60950-1": {"pillar": "Safety", "withdrawn": True, "replacement": "EN IEC 62368-1:2020+A11:2020", "alert_keywords": ["62368-1:2023", "60950"]},
    "UL 60950-1": {"pillar": "Safety", "withdrawn": True, "replacement": "UL 62368-1", "alert_keywords": ["62368-1:2023", "60950"]},
    "IS 13252 (Part 1)": {"pillar": "Safety", "withdrawn": True, "replacement": "IS/IEC 62368-1:2023 (BIS CRS transition, concurrent running until 2028-11-01)", "alert_keywords": ["IS 13252", "IS/IEC 62368-1"]},
    "IS/IEC 62368-1": {"pillar": "Safety", "current": [2023], "superseded": {}, "alert_keywords": ["IS/IEC 62368-1"]},
    "GB 4943.1": {"pillar": "Safety", "current": [2022], "superseded": {2011: "GB 4943.1-2022"}, "alert_keywords": ["GB 4943.1-2022"]},
    "CNS 14336-1": {"pillar": "Safety", "withdrawn": True, "replacement": "CNS 15598-1", "alert_keywords": ["CNS 15598"]},
    "CNS 15598-1": {"pillar": "Safety", "current": [2020], "superseded": {}, "alert_keywords": ["CNS 15598"]},
    "KC 62368-1": {"pillar": "Safety", "current": [], "superseded": {}, "alert_keywords": ["KC 62368"]},
    "K 60950-1": {"pillar": "Safety", "withdrawn": True, "replacement": "KC 62368-1", "alert_keywords": ["KC 62368", "60950"]},
    "J62368-1": {"pillar": "Safety", "current": [2020, 2023], "superseded": {}, "alert_keywords": ["J62368"]},
    "AS/NZS 62368.1": {"pillar": "Safety", "current": [2018, 2022], "superseded": {}, "alert_keywords": ["62368.1"]},
    "CISPR 32": {"pillar": "EMC", "current": [2015], "superseded": {2012: "CISPR 32:2015+A1:2019"}, "alert_keywords": ["CISPR 32"]},
    "EN 55032": {"pillar": "EMC", "current": [2015], "superseded": {2012: "EN 55032:2015+A11:2020"}, "alert_keywords": ["EN 55032", "CISPR 32"]},
    "CISPR 35": {"pillar": "EMC", "current": [2016], "superseded": {}, "alert_keywords": ["CISPR 35"]},
    "EN 55035": {"pillar": "EMC", "current": [2017], "superseded": {}, "alert_keywords": ["EN 55035"]},
    "CISPR 22": {"pillar": "EMC", "withdrawn": True, "replacement": "CISPR 32:2015+A1:2019 Class B", "alert_keywords": ["CISPR 32"]},
    "EN 55022": {"pillar": "EMC", "withdrawn": True, "replacement": "EN 55032:2015+A11:2020 Class B", "alert_keywords": ["CISPR 32", "EN 55032"]},
    "EN 55024": {"pillar": "EMC", "withdrawn": True, "replacement": "EN 55035:2017+A11:2020", "alert_keywords": ["EN 55035"]},
    "FCC Part 15B": {"pillar": "EMC", "current": [], "superseded": {}, "alert_keywords": ["47 CFR", "FCC"]},
    "ANSI C63.4": {"pillar": "EMC", "current": [2014], "superseded": {2009: "ANSI C63.4-2014"}, "alert_keywords": ["C63.4"]},
    "ICES-003": {"pillar": "EMC", "current": [], "superseded": {}, "alert_keywords": ["ICES-003"]},
    "VCCI-CISPR 32": {"pillar": "EMC", "current": [2016], "superseded": {}, "alert_keywords": ["VCCI"]},
    "KN 32": {"pillar": "EMC", "withdrawn": True, "replacement": "KS C 9832:2019", "alert_keywords": ["KS C 9832", "CISPR 32:2019"]},
    "KN 35": {"pillar": "EMC", "withdrawn": True, "replacement": "KS C 9835:2019", "alert_keywords": ["KS C 9835"]},
    "KS C 9832": {"pillar": "EMC", "current": [2019], "superseded": {}, "alert_keywords": ["KS C 9832"]},
    "KS C 9835": {"pillar": "EMC", "current": [2019], "superseded": {}, "alert_keywords": ["KS C 9835"]},
    "CNS 13438": {"pillar": "EMC", "withdrawn": True, "replacement": "CNS 15936", "alert_keywords": ["CNS 15936", "CNS 13438"]},
    "CNS 15936": {"pillar": "EMC", "current": [2016], "superseded": {}, "alert_keywords": ["CNS 15936"]},
    "GB/T 9254.1": {"pillar": "EMC", "current": [2021], "superseded": {}, "alert_keywords": ["9254"]},
    "GB 9254": {"pillar": "EMC", "withdrawn": True, "replacement": "GB/T 9254.1-2021", "alert_keywords": ["9254"]},
    "AS/NZS CISPR 32": {"pillar": "EMC", "current": [2015], "superseded": {}, "alert_keywords": ["CISPR 32"]},
    "EN 61000-3-2": {"pillar": "EMC", "current": [2014, 2019], "superseded": {}, "alert_keywords": ["61000-3-2"]},
    "EN 61000-3-3": {"pillar": "EMC", "current": [2013], "superseded": {}, "alert_keywords": ["61000-3-3"]},
    "Directive 2011/65/EU (RoHS 2)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["2011/65/EU", "RoHS"]},
    "Directive (EU) 2015/863 (RoHS 3)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["2015/863", "RoHS"]},
    "RoHS": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["RoHS"]},
    "EN IEC 63000": {"pillar": "Environmental", "current": [2018], "superseded": {}, "alert_keywords": ["63000"]},
    "IEC 62321": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["62321"]},
    "REACH (EC 1907/2006)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["REACH"]},
    "TSCA Section 8(a)(7) (PFAS)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["TSCA", "PFAS"]},
    "TSCA 40 CFR Part 705": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["705", "PFAS"]},
    "SJ/T 11364 (China RoHS)": {"pillar": "Environmental", "current": [2014], "superseded": {2006: "SJ/T 11364-2014 (China RoHS 2, EFUP table)"}, "alert_keywords": ["SJ/T 11364"]},
    "GB/T 26572": {"pillar": "Environmental", "current": [2011], "superseded": {}, "alert_keywords": ["26572"]},
    "CNS 15663 (Taiwan RoHS)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["CNS 15663"]},
    "SASO RoHS (SABER)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["SASO RoHS"]},
    "California Proposition 65": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["Prop 65"]},
    "France Triman (AGEC)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["Triman", "AGEC"]},
    "France Info-tri": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["Info-tri", "AGEC"]},
    "French Decree 2021-835": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["2021-835"]},
    "Italy D.Lgs 116/2020": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["116/2020"]},
    "Decision 97/129/EC (Packaging Material Coding)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["97/129", "129/97"]},
    "Germany VerpackG (LUCID)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["VerpackG"]},
    "Directive 94/62/EC (Packaging)": {"pillar": "Environmental", "withdrawn": True, "replacement": "Regulation (EU) 2025/40 (PPWR)", "alert_keywords": ["PPWR", "94/62"]},
    "Regulation (EU) 2025/40 (PPWR)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["PPWR"]},
    "WEEE Directive 2012/19/EU": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["WEEE"]},
    "India E-Waste (Management) Rules 2022": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["E-Waste"]},
    "CPCB EPR Portal": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["CPCB"]},
    "Regulation (EU) 2024/2847 (CRA)": {"pillar": "Cyber", "current": [], "superseded": {}, "alert_keywords": ["2024/2847", "Cyber Resilience"]},
    "EN 18031": {"pillar": "Cyber", "current": [2024], "superseded": {}, "alert_keywords": ["EN 18031"]},
    "ETSI EN 303 645": {"pillar": "Cyber", "current": [], "superseded": {}, "alert_keywords": ["303 645"]},
    "UK PSTI Act 2022": {"pillar": "Cyber", "current": [], "superseded": {}, "alert_keywords": ["PSTI"]},
    "FIPS 140-3": {"pillar": "Cyber", "current": [], "superseded": {}, "alert_keywords": ["FIPS"]},
    "FIPS 140-2": {"pillar": "Cyber", "withdrawn": True, "replacement": "FIPS 140-3 (FIPS 140-2 certificates moved to historical list 2026-09-21)", "alert_keywords": ["FIPS"]},
    "US DoE Level VI (10 CFR 430)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["Level VI", "10 CFR 430"]},
    "Regulation (EU) 2019/1782 (EPS Ecodesign)": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["2019/1782"]},
    "CEC Title 20": {"pillar": "Environmental", "current": [], "superseded": {}, "alert_keywords": ["Title 20"]},
    "LVD 2014/35/EU": {"pillar": "Safety", "current": [], "superseded": {}, "alert_keywords": ["2014/35/EU"]},
    "EMCD 2014/30/EU": {"pillar": "EMC", "current": [], "superseded": {}, "alert_keywords": ["2014/30/EU"]},
    "RED 2014/53/EU": {"pillar": "EMC", "current": [], "superseded": {}, "alert_keywords": ["2014/53/EU"]},
}

# regex -> canonical. Order matters: more specific first. Edition years are captured separately (see _edition_after).
STANDARD_PATTERNS = [
    (r"IS\s*/\s*IEC[\s\-_]?62368[\s\-_]?1", "IS/IEC 62368-1"),
    (r"EN[\s\-_]?(?:IEC[\s\-_]?)?62368[\s\-_]?1", "EN 62368-1"),
    (r"UL[\s\-_]?62368[\s\-_]?1", "UL 62368-1"),
    (r"CSA[\s\-_]?(?:C22\.2\s*No\.?\s*)?62368[\s\-_]?1", "CSA C22.2 No. 62368-1"),
    (r"KC[\s\-_]?62368[\s\-_]?1", "KC 62368-1"),
    (r"J[\s\-_]?62368[\s\-_]?1", "J62368-1"),
    (r"AS/NZS[\s\-_]?62368\.1", "AS/NZS 62368.1"),
    (r"IEC[\s\-_]?62368[\s\-_]?1", "IEC 62368-1"),
    (r"(?<![A-Z] )(?<![A-Z])(?<![A-Z][\-_/])62368[\s\-_]?1(?![\d])", "IEC 62368-1"),
    (r"EN[\s\-_]?60950[\s\-_]?1", "EN 60950-1"),
    (r"UL[\s\-_]?60950[\s\-_]?1", "UL 60950-1"),
    (r"K[\s\-_]?60950[\s\-_]?1", "K 60950-1"),
    (r"IEC[\s\-_]?60950[\s\-_]?1|(?<![A-Z] )(?<![A-Z])(?<![A-Z][\-_/])60950[\s\-_]?1", "IEC 60950-1"),
    (r"IS[\s\-_]?13252(?:\s*\(?\s*Part\s*1\s*\)?)?", "IS 13252 (Part 1)"),
    (r"GB[\s\-_]?4943(?:\.1)?", "GB 4943.1"),
    (r"CNS[\s\-_]?14336(?:[\s\-_]?1)?", "CNS 14336-1"),
    (r"CNS[\s\-_]?15598(?:[\s\-_]?1)?", "CNS 15598-1"),
    (r"VCCI[\s\-_]?CISPR[\s\-_]?32", "VCCI-CISPR 32"),
    (r"AS/NZS[\s\-_]?CISPR[\s\-_]?32", "AS/NZS CISPR 32"),
    (r"CISPR[\s\-_]?32", "CISPR 32"),
    (r"CISPR[\s\-_]?35", "CISPR 35"),
    (r"CISPR[\s\-_]?22", "CISPR 22"),
    (r"(?:BS\s+)?EN[\s\-_]?55032", "EN 55032"),
    (r"(?:BS\s+)?EN[\s\-_]?55035", "EN 55035"),
    (r"(?:BS\s+)?EN[\s\-_]?55022", "EN 55022"),
    (r"(?:BS\s+)?EN[\s\-_]?55024", "EN 55024"),
    (r"EN[\s\-_]?(?:IEC[\s\-_]?)?61000[\s\-_]?3[\s\-_]?2", "EN 61000-3-2"),
    (r"EN[\s\-_]?(?:IEC[\s\-_]?)?61000[\s\-_]?3[\s\-_]?3", "EN 61000-3-3"),
    (r"FCC[\s\-_]?(?:47[\s\-_]?CFR[\s\-_]?)?Part[\s\-_]?15(?:\s*,?\s*Subpart\s*B|\s*B\b|\.\d+)?|47\s*CFR\s*(?:Part\s*)?15\b", "FCC Part 15B"),
    (r"ANSI[\s\-_]?C63\.4", "ANSI C63.4"),
    (r"ICES[\s\-_]?003", "ICES-003"),
    (r"KN[\s\-_]?32", "KN 32"),
    (r"KN[\s\-_]?35", "KN 35"),
    (r"KS[\s\-_]?C[\s\-_]?9832", "KS C 9832"),
    (r"KS[\s\-_]?C[\s\-_]?9835", "KS C 9835"),
    (r"CNS[\s\-_]?13438", "CNS 13438"),
    (r"CNS[\s\-_]?15936", "CNS 15936"),
    (r"GB/T[\s\-_]?9254(?:\.1)?", "GB/T 9254.1"),
    (r"GB[\s\-_]?9254", "GB 9254"),
    (r"(?:Directive[\s\-_]?)?2011/65/EU", "Directive 2011/65/EU (RoHS 2)"),
    (r"(?:Directive[\s\-_]?)?(?:\(EU\)\s*)?2015/863", "Directive (EU) 2015/863 (RoHS 3)"),
    (r"\bRoHS\b", "RoHS"),
    (r"EN[\s\-_]?(?:IEC[\s\-_]?)?63000", "EN IEC 63000"),
    (r"IEC[\s\-_]?62321", "IEC 62321"),
    (r"\bREACH\b(?:\s*Regulation)?(?:\s*\(EC\)\s*(?:No\.?\s*)?1907/2006)?|\(EC\)\s*(?:No\.?\s*)?1907/2006", "REACH (EC 1907/2006)"),
    (r"TSCA[\s\-_]?(?:Section[\s\-_]?)?8\s*\(a\)\s*\(7\)", "TSCA Section 8(a)(7) (PFAS)"),
    (r"40[\s\-_]?CFR[\s\-_]?(?:Part[\s\-_]?)?705", "TSCA 40 CFR Part 705"),
    (r"SJ/T[\s\-_]?11364", "SJ/T 11364 (China RoHS)"),
    (r"GB/T[\s\-_]?26572", "GB/T 26572"),
    (r"CNS[\s\-_]?15663(?:\s*Section\s*5)?", "CNS 15663 (Taiwan RoHS)"),
    (r"SASO[\s\-_]RoHS|M\.A-179-21", "SASO RoHS (SABER)"),
    (r"Prop(?:osition)?\.?\s*65", "California Proposition 65"),
    (r"\bTriman\b", "France Triman (AGEC)"),
    (r"Info[\s\-_]?tri\b", "France Info-tri"),
    (r"Decree[\s\-_]?(?:No\.?\s*)?2021[\s\-_]?835", "French Decree 2021-835"),
    (r"(?:Legislative[\s\-_]?)?Decree[\s\-_]?(?:No\.?\s*)?116/2020|D\.?\s?Lgs\.?\s*116/2020", "Italy D.Lgs 116/2020"),
    (r"Decision[\s\-_]?(?:97/129/EC|129/97/EC)|\b97/129/EC\b", "Decision 97/129/EC (Packaging Material Coding)"),
    (r"\bVerpackG\b|\bLUCID\b", "Germany VerpackG (LUCID)"),
    (r"(?:Directive\s*)?94/62/EC", "Directive 94/62/EC (Packaging)"),
    (r"\bPPWR\b|(?:Regulation\s*)?\(EU\)\s*2025/40\b", "Regulation (EU) 2025/40 (PPWR)"),
    (r"\bWEEE\b(?:[\s\-_]?Directive)?(?:[\s\-_]?2012/19/EU)?|2012/19/EU", "WEEE Directive 2012/19/EU"),
    (r"E[\s\-_]?Waste[\s\-_]?(?:\(Management\)\s*)?Rules,?[\s\-_]?2022", "India E-Waste (Management) Rules 2022"),
    (r"\bCPCB\b", "CPCB EPR Portal"),
    (r"(?:Regulation\s*)?\(EU\)\s*2024/2847|Cyber\s+Resilience\s+Act|\bCRA\b(?=.{0,40}(?:EU|cyber))", "Regulation (EU) 2024/2847 (CRA)"),
    (r"EN[\s\-_]?18031(?:[\s\-_]?\d)?", "EN 18031"),
    (r"(?:ETSI\s*)?EN[\s\-_]?303[\s\-_]?645", "ETSI EN 303 645"),
    (r"\bPSTI\b", "UK PSTI Act 2022"),
    (r"FIPS[\s\-_]?140[\s\-_]?3", "FIPS 140-3"),
    (r"FIPS[\s\-_]?140[\s\-_]?2", "FIPS 140-2"),
    (r"Level\s+VI\b|10[\s\-_]?CFR[\s\-_]?(?:Part[\s\-_]?)?430", "US DoE Level VI (10 CFR 430)"),
    (r"(?:Regulation\s*)?\(EU\)\s*2019/1782", "Regulation (EU) 2019/1782 (EPS Ecodesign)"),
    (r"CEC\s+Title\s+20|Title\s+20\s+Appliance", "CEC Title 20"),
    (r"2014/35/EU", "LVD 2014/35/EU"),
    (r"2014/30/EU", "EMCD 2014/30/EU"),
    (r"2014/53/EU", "RED 2014/53/EU"),
]
_COMPILED_STANDARDS = [(re.compile(p, re.IGNORECASE), name) for p, name in STANDARD_PATTERNS]
_EDITION_AFTER = re.compile(r"^\s*[:\-–]\s*((?:19|20)\d{2})((?:\s*[+/]\s*A\d{0,2}\s*[:\-]?\s*(?:19|20)\d{2})*)")
_AMEND_YEARS = re.compile(r"A\d{0,2}\s*[:\-]?\s*((?:19|20)\d{2})")
_EDITION_WORD = re.compile(r"^.{0,40}?(?:\b(?:Ed(?:ition)?\.?\s*(\d)(?:\.\d)?)\b|\b(\d)(?:st|nd|rd|th)\s+Edition\b|\b(Second|Third|Fourth|Fifth)\s+Edition\b)", re.IGNORECASE | re.DOTALL)
_WORD_EDITION = {"second": 2, "third": 3, "fourth": 4, "fifth": 5}

# v1-compatible rulebook of superseded standards (kept as the *static* seed of the dynamic rulebook).
# key: "CANONICAL" (any edition) or "CANONICAL:YEAR". tier_by_class overrides CLASS_TIER when present.
SUPERSEDED_STANDARDS = {
    "IEC 60950-1": {"new_standard": "IEC 62368-1:2023 (Edition 4.0)", "alert_id": "ALERT-2026-02", "alert_keywords": ["62368-1:2023"], "deadline": "2026-12-31",
                    "severity": "Critical", "cost": (4500, 7500), "weeks": (6, 8),
                    "why": "IEC/EN 60950-1 has been fully withdrawn; it ceased to give presumption of conformity in the EU on 20 December 2020 and CB certificates are no longer issued against it."},
    "EN 60950-1": {"new_standard": "EN IEC 62368-1:2020+A11:2020", "alert_id": "ALERT-2026-02", "alert_keywords": ["62368-1:2023"], "deadline": "2026-12-31",
                   "severity": "Critical", "cost": (4500, 7500), "weeks": (6, 8),
                   "why": "EN 60950-1 was removed from the Official Journal (date of withdrawal 20 December 2020); a DoC or report relying on it no longer supports CE marking."},
    "UL 60950-1": {"new_standard": "UL 62368-1", "alert_id": "ALERT-2026-02", "alert_keywords": ["62368-1:2023"], "deadline": "2026-12-31",
                   "severity": "Critical", "cost": (4500, 7500), "weeks": (6, 8),
                   "why": "UL 60950-1 was withdrawn as an NRTL listing standard (effective 20 December 2020); new listings and follow-up require UL 62368-1."},
    "K 60950-1": {"new_standard": "KC 62368-1", "alert_id": "ALERT-2026-07", "alert_keywords": ["KC"], "deadline": None,
                  "severity": "Warning", "cost": (3500, 6500), "weeks": (6, 10), "why": "Korea's KATS safety scheme has moved from K 60950-1 to KC 62368-1."},
    "IEC 62368-1:2014": {"new_standard": "IEC 62368-1:2023 (Edition 4.0)", "alert_id": "ALERT-2026-02", "alert_keywords": ["62368-1:2023"], "deadline": "2026-12-31",
                         "severity": "Critical", "cost": (4500, 7500), "weeks": (6, 8),
                         "why": "Edition 2.0 (2014) is two editions behind; national certification bodies no longer accept Ed. 2 CB reports for new or renewed national approvals."},
    "IEC 62368-1:2018": {"new_standard": "IEC 62368-1:2023 (Edition 4.0)", "alert_id": "ALERT-2026-02", "alert_keywords": ["62368-1:2023"], "deadline": "2026-12-31",
                         "severity": "Warning", "cost": (1500, 3000), "weeks": (3, 4), "tier_by_class": {"report": "retesting_required"},
                         "why": "Edition 3.0 (2018) is being replaced by Edition 4.0 (2023) across the CB Scheme; a delta (gap) assessment with limited re-testing is needed to keep the CB certificate usable for national approvals."},
    "EN 62368-1:2014": {"new_standard": "EN IEC 62368-1:2020+A11:2020", "alert_id": "ALERT-2026-02", "alert_keywords": ["62368-1:2023"], "deadline": "2026-12-31",
                        "severity": "Warning", "cost": (0, 500), "weeks": (1, 2),
                        "why": "EN 62368-1:2014+A11:2017 no longer gives presumption of conformity under the Low Voltage Directive; the harmonised reference is EN IEC 62368-1:2020+A11:2020."},
    "UL 62368-1:2014": {"new_standard": "UL 62368-1 (2019 / 2023 edition)", "alert_id": "ALERT-2026-02", "alert_keywords": ["62368-1:2023"], "deadline": "2026-12-31",
                        "severity": "Warning", "cost": (1500, 3500), "weeks": (3, 5), "why": "The 2014 (2nd) edition of UL 62368-1 has been superseded."},
    "IS 13252 (Part 1)": {"new_standard": "IS/IEC 62368-1:2023", "alert_id": "ALERT-2026-03", "alert_keywords": ["IS/IEC 62368-1", "IS 13252"], "deadline": "2028-11-01",
                          "severity": "Warning", "cost": (2500, 5000), "weeks": (6, 10), "tier_by_class": {"registration": "portal_filing", "report": "retesting_required"},
                          "why": "BIS is migrating the CRS scheme from IS 13252 (Part 1):2010 [IEC 60950-1] to IS/IEC 62368-1:2023, with concurrent running until 1 November 2028. Registrations must be re-filed with an NABL in-country report to the new standard."},
    "GB 4943.1:2011": {"new_standard": "GB 4943.1-2022", "alert_id": "ALERT-2026-09", "alert_keywords": ["GB 4943.1-2022"], "deadline": "2026-10-31",
                       "severity": "Critical", "cost": (6000, 12000), "weeks": (8, 12), "tier_by_class": {"registration": "retesting_required"},
                       "why": "GB 4943.1-2022 replaced GB 4943.1-2011 (implemented 1 August 2023); CCC certificates must be converted with in-country testing at a CNCA-designated lab."},
    "CNS 14336-1": {"new_standard": "CNS 15598-1:2020", "alert_id": None, "alert_keywords": ["CNS 15598"], "deadline": None,
                    "severity": "Warning", "cost": (2500, 5000), "weeks": (6, 8), "why": "Taiwan BSMI replaced CNS 14336-1 (IEC 60950-1 based) with CNS 15598-1 (IEC 62368-1 based)."},
    "EN 55022": {"new_standard": "EN 55032:2015+A11:2020 Class B", "alert_id": None, "alert_keywords": ["CISPR 32", "EN 55032"], "deadline": None,
                 "severity": "Critical", "cost": (3000, 5000), "weeks": (3, 5),
                 "why": "EN 55022 was withdrawn from the Official Journal on 2 March 2017; emissions must be shown against EN 55032."},
    "CISPR 22": {"new_standard": "CISPR 32:2015+A1:2019 Class B", "alert_id": None, "alert_keywords": ["CISPR 32"], "deadline": None,
                 "severity": "Critical", "cost": (3000, 5000), "weeks": (3, 5), "why": "CISPR 22 was withdrawn and replaced by CISPR 32 for multimedia equipment."},
    "EN 55024": {"new_standard": "EN 55035:2017+A11:2020", "alert_id": None, "alert_keywords": ["EN 55035"], "deadline": None,
                 "severity": "Warning", "cost": (2500, 4500), "weeks": (3, 5), "why": "EN 55024 (ITE immunity) has been superseded by EN 55035 for multimedia equipment."},
    "CISPR 32:2012": {"new_standard": "CISPR 32:2015+A1:2019", "alert_id": None, "alert_keywords": ["CISPR 32"], "deadline": None,
                      "severity": "Warning", "cost": (2500, 4500), "weeks": (3, 4), "why": "CISPR 32 Edition 1 (2012) has been superseded by Edition 2 (2015) and its amendment A1:2019."},
    "EN 55032:2012": {"new_standard": "EN 55032:2015+A11:2020", "alert_id": None, "alert_keywords": ["EN 55032"], "deadline": None,
                      "severity": "Warning", "cost": (2500, 4500), "weeks": (3, 4), "why": "EN 55032:2012 has been superseded by EN 55032:2015 (+A11:2020) in the Official Journal."},
    "KN 32": {"new_standard": "KS C 9832:2019", "alert_id": "ALERT-2026-07", "alert_keywords": ["KS C 9832"], "deadline": "2026-12-01",
              "severity": "Info", "cost": (1500, 3500), "weeks": (3, 6), "tier_by_class": {"registration": "portal_filing", "report": "retesting_required"},
              "why": "Korea harmonised KN 32 into KS C 9832:2019 (CISPR 32 based); RRA registrations citing KN 32 should be updated at the next change or renewal."},
    "KN 35": {"new_standard": "KS C 9835:2019", "alert_id": "ALERT-2026-07", "alert_keywords": ["KS C 9835"], "deadline": "2026-12-01",
              "severity": "Info", "cost": (1500, 3500), "weeks": (3, 6), "tier_by_class": {"registration": "portal_filing"},
              "why": "KN 35 has been harmonised into KS C 9835:2019."},
    "CNS 13438": {"new_standard": "CNS 15936", "alert_id": "ALERT-2026-08", "alert_keywords": ["CNS 15936", "CNS 13438"], "deadline": "2026-09-30",
                  "severity": "Warning", "cost": (2000, 4000), "weeks": (3, 6), "tier_by_class": {"registration": "portal_filing"},
                  "why": "BSMI replaced CNS 13438 with CNS 15936 (CISPR 32 based) for ITE / multimedia equipment."},
    "GB 9254": {"new_standard": "GB/T 9254.1-2021", "alert_id": None, "alert_keywords": ["9254"], "deadline": None,
                "severity": "Warning", "cost": (2000, 4000), "weeks": (3, 5), "why": "GB 9254 has been superseded by GB/T 9254.1-2021 (CISPR 32 based)."},
    "SJ/T 11364 (China RoHS):2006": {"new_standard": "SJ/T 11364-2014 (China RoHS 2 EFUP table & logo)", "alert_id": "ALERT-2026-09", "alert_keywords": ["SJ/T 11364"], "deadline": "2026-10-31",
                                     "severity": "Warning", "cost": (400, 1500), "weeks": (3, 4), "tier_by_class": {"declaration": "packaging_update", "report": "packaging_update"},
                                     "why": "SJ/T 11364-2006 marking has been replaced by SJ/T 11364-2014 (Order 32 EFUP table and green/orange logo)."},
    "Directive 94/62/EC (Packaging)": {"new_standard": "Regulation (EU) 2025/40 (PPWR)", "alert_id": "ALERT-ENV-02", "alert_keywords": ["PPWR"], "deadline": "2026-08-12",
                                       "severity": "Warning", "cost": (400, 2500), "weeks": (2, 4), "tier_by_class": {"declaration": "packaging_update", "report": "packaging_update"},
                                       "why": "The Packaging Directive 94/62/EC is repealed by the Packaging & Packaging Waste Regulation (EU) 2025/40, which applies from 12 August 2026."},
    "FIPS 140-2": {"new_standard": "FIPS 140-3", "alert_id": None, "alert_keywords": ["FIPS"], "deadline": "2026-09-21",
                   "severity": "Warning", "cost": (0, 500), "weeks": (1, 2), "why": "FIPS 140-2 validation certificates move to the NIST historical list on 21 September 2026; procurement references should cite FIPS 140-3."},
}

# --------------------------------------------------------------------------- products, labs, markets
# Extra aliases for the seed portfolio (in addition to SKU prefixes / names derived from the live product list)
# Optional extra aliases per product id (e.g. marketing names) - empty by default. Product matching is
# built dynamically from the live product list (sku + name, regex-escaped, case-insensitive); no SKUs are hard-coded.
PRODUCT_ALIASES: Dict[str, List[str]] = {}
PRODUCT_SKU_PATTERNS: List[Tuple[str, str, str]] = []  # kept for API compatibility; intentionally empty

LAB_NAMES = [
    ("UL Solutions", [r"UL\s+Solutions", r"UL\s+LLC", r"Underwriters\s+Laboratories", r"\bUL\s+(?:Northbrook|India|Japan|International)"]),
    ("TÜV SÜD", [r"T[UÜ]V\s*S[UÜ]D"]), ("TÜV Rheinland", [r"T[UÜ]V\s*Rheinland"]), ("TÜV NORD", [r"T[UÜ]V\s*NORD"]),
    ("SGS", [r"\bSGS\b"]), ("Intertek", [r"\bIntertek\b"]), ("Bureau Veritas", [r"Bureau\s+Veritas", r"\bBVCPS\b"]),
    ("Element Materials Technology", [r"Element\s+Materials"]), ("DEKRA", [r"\bDEKRA\b"]), ("Eurofins", [r"\bEurofins\b"]),
    ("Nemko", [r"\bNemko\b"]), ("CSA Group", [r"\bCSA\s+Group\b"]), ("MET Laboratories", [r"\bMET\s+Lab"]),
    ("Sporton", [r"\bSporton\b"]), ("Audix", [r"\bAudix\b"]), ("BACL", [r"\bBACL\b", r"Bay\s+Area\s+Compliance"]),
    ("Cerpass", [r"\bCerpass\b"]), ("SIQ", [r"\bSIQ\b"]), ("KTL (Korea Testing Laboratory)", [r"\bKTL\b", r"Korea\s+Testing\s+Laboratory"]),
    ("KTC", [r"\bKTC\b", r"Korea\s+Testing\s+Certification"]), ("KTR", [r"\bKTR\b"]), ("JET", [r"\bJET\b", r"Japan\s+Electrical\s+Safety"]),
    ("JQA", [r"\bJQA\b"]), ("CQC", [r"\bCQC\b", r"China\s+Quality\s+Certification"]), ("CTTL", [r"\bCTTL\b"]),
    ("Bureau of Indian Standards", [r"Bureau\s+of\s+Indian\s+Standards"]), ("ETL / Intertek", [r"\bETL\b"]),
    ("In-house compliance laboratory", [r"In-?house\s+(?:Compliance|EMC|Safety)\s+Lab", r"Internal\s+Compliance\s+Lab"]),
]
_COMPILED_LABS = [(name, [re.compile(p, re.IGNORECASE) for p in pats]) for name, pats in LAB_NAMES]

MARKET_ALIASES = {
    "US": [r"\bUnited\s+States\b", r"\bUSA\b", r"\bU\.S\.A?\.?\b", r"\bFCC\b", r"\b47\s+CFR\b", r"\bTSCA\b", r"\bNRTL\b", r"\bcULus\b", r"\bUL\s+Listed\b", r"\bDoE\s+Level\s+VI\b", r"\bProp(?:osition)?\s*65\b"],
    "CA": [r"\bCanada\b", r"\bISED\b", r"\bICES-003\b", r"\bcUL\b", r"\bCSA\s+C22"],
    "EU": [r"\bEuropean\s+Union\b", r"\bEU\b", r"\bCE\s+mark", r"\b20\d\d/\d+/EU\b", r"\b2011/65/EU\b", r"\bEN\s?(?:IEC\s?)?\d{5}\b", r"\bEUR-?Lex\b", r"\bOJEU\b", r"\bOfficial\s+Journal\b", r"\bPPWR\b", r"\bWEEE\b", r"\bREACH\b"],
    "DE": [r"\bGermany\b", r"\bDeutschland\b", r"\bVerpackG\b", r"\bLUCID\b"],
    "FR": [r"\bFrance\b", r"\bTriman\b", r"\bInfo[\s-]?tri\b", r"\bAGEC\b", r"\b2021-835\b"],
    "IT": [r"\bItaly\b", r"\bItalia\b", r"\bD\.?\s?Lgs\b", r"\b116/2020\b"],
    "ES": [r"\bSpain\b"], "NL": [r"\bNetherlands\b"], "PL": [r"\bPoland\b"], "SE": [r"\bSweden\b"],
    "GB": [r"\bUnited\s+Kingdom\b", r"\bUK\b", r"\bUKCA\b", r"\bPSTI\b", r"\bGreat\s+Britain\b", r"\bBS\s+EN\b"],
    "JP": [r"\bJapan\b", r"\bPSE\b", r"\bMETI\b", r"\bVCCI\b", r"\bJ-Moss\b", r"\bDENAN\b"],
    "KR": [r"\bKorea\b", r"\bKC\s+Mark\b", r"\bKATS\b", r"\bRRA\b", r"\bKN\s?3[25]\b", r"\bKS\s?C\s?98", r"\bK-REACH\b", r"\bKC\s+(?:safety\s+)?certif"],
    "TW": [r"\bTaiwan\b", r"\bBSMI\b", r"\bCNS\s?\d{5}\b"],
    "CN": [r"\bChina\b", r"\bCCC\b", r"\bCQC\b", r"\bCNCA\b", r"\bGB\s?4943", r"\bGB/T\s?9254", r"\bSJ/T\s?11364", r"\bGACC\b", r"\bEFUP\b"],
    "IN": [r"\bIndia\b", r"\bBIS\b", r"\bCRS\b", r"\bNABL\b", r"\bCPCB\b", r"\bIS\s?13252\b", r"\bMeitY\b", r"\bIS/IEC\s?62368"],
    "AU": [r"\bAustralia\b", r"\bACMA\b", r"\bRCM\b", r"\bAS/NZS\b"], "NZ": [r"\bNew\s+Zealand\b", r"\bAS/NZS\b"],
    "SA": [r"\bSaudi\b", r"\bSASO\b", r"\bSABER\b", r"\bKSA\b"], "AE": [r"\bUAE\b", r"\bUnited\s+Arab\s+Emirates\b", r"\bECAS\b", r"\bESMA\b", r"\bMoIAT\b"],
    "BR": [r"\bBrazil\b", r"\bBrasil\b", r"\bINMETRO\b", r"\bANATEL\b", r"\bSISCOMEX\b"], "MX": [r"\bMexico\b", r"\bNOM-?\d{3}\b", r"\bNYCE\b"],
    "SG": [r"\bSingapore\b", r"\bIMDA\b"], "ZA": [r"\bSouth\s+Africa\b", r"\bNRCS\b", r"\bICASA\b"], "MA": [r"\bMorocco\b", r"\bCMIM\b"],
    "RU": [r"\bRussia\b", r"\bEAC\b", r"\bEAEU\b"], "KZ": [r"\bKazakhstan\b"], "BY": [r"\bBelarus\b"], "TR": [r"\bTurkey\b", r"\bTürkiye\b"],
    "IL": [r"\bIsrael\b", r"\bSII\b"], "EG": [r"\bEgypt\b", r"\bNTRA\b"], "AR": [r"\bArgentina\b", r"\bIRAM\b"], "CL": [r"\bChile\b", r"\bSEC\b\s+Chile"],
    "VN": [r"\bVietnam\b", r"\bMIC\s+Vietnam\b"], "TH": [r"\bThailand\b", r"\bTISI\b"], "MY": [r"\bMalaysia\b", r"\bSIRIM\b"], "ID": [r"\bIndonesia\b", r"\bSDPPI\b"],
    "HK": [r"\bHong\s+Kong\b"], "PH": [r"\bPhilippines\b"],
}
_COMPILED_MARKETS = [(code, [re.compile(p, re.IGNORECASE if code not in ("EU", "GB", "US") else 0) for p in pats]) for code, pats in MARKET_ALIASES.items()]
_COUNTRY_NAME_STOPLIST = {"Georgia", "Jersey", "Jordan", "Guinea", "Turkey", "Niger", "Chad", "Togo", "Mali", "Cuba", "Iran", "Iraq", "Oman", "Peru", "Fiji", "Laos", "Guernsey", "Reunion"}
MARKET_NAMES = {"EU": "European Union"}

_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_DATE_ISO = re.compile(r"\b((?:19|20)\d{2})[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])\b")
_DATE_DMY_TEXT = re.compile(r"\b(0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?,?\s+((?:19|20)\d{2})\b", re.IGNORECASE)
_DATE_MDY_TEXT = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?,?\s+((?:19|20)\d{2})\b", re.IGNORECASE)
_DATE_DMY_NUM = re.compile(r"\b(0?[1-9]|[12]\d|3[01])[./-](0?[1-9]|1[0-2])[./-]((?:19|20)\d{2})\b")
_ISSUE_LABELS = re.compile(r"(?:date\s+of\s+(?:issue|grant|test|registration|certification|signature)|issue\s+date|issued\s+on|issued|dated|date\s+of\s+report|report\s+date|signed\s+on|date)\s*[:\-]?\s*", re.IGNORECASE)
_EXPIRY_LABELS = re.compile(r"(?:valid\s+(?:until|till|to|through|thru)|expir(?:y|es|ation)(?:\s+date)?|date\s+of\s+expiry|validity\s+(?:until|to)|renew(?:al)?\s+(?:by|before|due))\s*[:\-]?\s*", re.IGNORECASE)


# =============================================================================
# 1. TEXT EXTRACTION
# =============================================================================
def _today() -> _dt.date:
    return _dt.date.today()


def _printable_from_bytes(raw: bytes, min_len: int = 4) -> str:
    """Best-effort recovery of readable strings from a binary blob (PDF streams, legacy .doc/.xls)."""
    parts = []
    # PDF literal strings "(...)" first - they carry the actual text in uncompressed content streams
    for m in re.findall(rb"\(((?:[^()\\]|\\.)*)\)", raw[:4_000_000]):
        s = m.decode("latin-1", errors="ignore").replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
        if len(s.strip()) >= min_len and re.search(r"[A-Za-z]", s):
            parts.append(s)
    if not parts:
        pattern = rb"[A-Za-z0-9 \.\-\:/,;\(\)\+&%#]{" + str(min_len).encode() + rb",}"
        for m in re.findall(pattern, raw[:4_000_000]):
            s = m.decode("ascii", errors="ignore")
            if re.search(r"[A-Za-z]{3}", s):
                parts.append(s)
    return "\n".join(parts)


def extract_text_from_pdf(file_path: str) -> Tuple[str, Optional[str]]:
    chunks, err = [], None
    if HAS_PYPDF:
        try:
            reader = pypdf.PdfReader(file_path, strict=False)
            if getattr(reader, "is_encrypted", False):
                try:
                    reader.decrypt("")
                except Exception:
                    pass
            for page in reader.pages[:400]:
                try:
                    t = page.extract_text() or ""
                except Exception:
                    t = ""
                if t.strip():
                    chunks.append(t)
        except Exception as e:  # corrupt / not a PDF
            err = f"pypdf: {type(e).__name__}: {str(e)[:120]}"
    else:
        err = "pypdf not installed"
    text = "\n".join(chunks)
    if len(text.strip()) < 40:
        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            if not raw.startswith(b"%PDF"):
                err = (err + "; " if err else "") + "file does not start with a %PDF header"
            fallback = _printable_from_bytes(raw)
            real_words = len(re.findall(r"\b[A-Za-z]{4,}\b", fallback))
            if len(fallback.strip()) >= 40 and real_words >= 8 and raw.startswith(b"%PDF"):
                return fallback, None
        except Exception as e:
            err = (err + "; " if err else "") + f"read error: {e}"
        return text, err or "no extractable text (scanned image PDF?)"
    return text, None


def extract_text_from_docx(file_path: str) -> Tuple[str, Optional[str]]:
    err = None
    if HAS_DOCX:
        try:
            d = docx.Document(file_path)
            parts = [p.text for p in d.paragraphs if p.text and p.text.strip()]
            for tbl in d.tables:
                for row in tbl.rows:
                    cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
                    if cells:
                        parts.append(" | ".join(cells))
            for section in d.sections:
                try:
                    for p in list(section.header.paragraphs) + list(section.footer.paragraphs):
                        if p.text.strip():
                            parts.append(p.text)
                except Exception:
                    pass
            if parts:
                return "\n".join(parts), None
        except Exception as e:
            err = f"python-docx: {type(e).__name__}: {str(e)[:120]}"
    try:
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read("word/document.xml").decode("utf-8", errors="ignore")
            text = re.sub(r"</w:p>", "\n", xml_content)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"[ \t]+", " ", text)
            if text.strip():
                return text, None
            return "", err or "empty document body"
    except Exception as e:
        return "", err or f"not a valid DOCX package: {type(e).__name__}"


def extract_text_from_xlsx(file_path: str) -> Tuple[str, Optional[str]]:
    if not HAS_OPENPYXL:
        return "", "openpyxl not installed"
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        chunks = []
        for ws in wb.worksheets:
            chunks.append(f"[Sheet: {ws.title}]")
            rows = 0
            for row in ws.iter_rows(values_only=True):
                vals = [str(c).strip() for c in row if c is not None and str(c).strip()]
                if vals:
                    chunks.append(" | ".join(vals))
                    rows += 1
                if rows > 20000:
                    break
        try:
            wb.close()
        except Exception:
            pass
        return "\n".join(chunks), None
    except Exception as e:
        return "", f"openpyxl: {type(e).__name__}: {str(e)[:120]}"


def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
    """Return (text, error). error is None when the file could be read; otherwise a plain-English reason."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        size = os.path.getsize(file_path)
    except OSError as e:
        return "", f"cannot access file: {e}"
    if size == 0:
        return "", "file is empty (0 bytes)"
    if size > MAX_FILE_BYTES:
        return "", f"file is {size / 1024 / 1024:.0f} MB - larger than the {MAX_FILE_BYTES // 1024 // 1024} MB scan limit"
    try:
        if ext == ".pdf":
            return extract_text_from_pdf(file_path)
        if ext == ".docx":
            return extract_text_from_docx(file_path)
        if ext in (".xlsx", ".xlsm"):
            return extract_text_from_xlsx(file_path)
        if ext in LEGACY_BINARY_EXTS:
            with open(file_path, "rb") as f:
                raw = f.read()
            if raw[:2] == b"PK":  # actually an OOXML package with the wrong extension
                return extract_text_from_docx(file_path) if ext == ".doc" else extract_text_from_xlsx(file_path)
            text = _printable_from_bytes(raw, min_len=6)
            if len(text.strip()) < 80:
                return "", f"legacy binary {ext} format is not supported - re-save as {'.docx' if ext == '.doc' else '.xlsx'}"
            return text, None
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read(8_000_000)
        if ext == ".json":
            try:
                text = json.dumps(json.loads(text), ensure_ascii=False, indent=1)
            except Exception:
                pass
        if not text.strip():
            return "", "file contains no text"
        return text, None
    except Exception as e:
        return "", f"{type(e).__name__}: {str(e)[:140]}"


def extract_text_from_file(file_path: str) -> str:
    """v1-compatible wrapper: text only ('' when unreadable)."""
    return extract_text(file_path)[0]


# =============================================================================
# 2. METADATA EXTRACTION
# =============================================================================
def _edition_after(text: str, end: int) -> Tuple[Optional[int], List[int]]:
    tail = text[end:end + 60]
    m = _EDITION_AFTER.match(tail)
    if m:
        year = int(m.group(1))
        amends = [int(y) for y in _AMEND_YEARS.findall(m.group(2) or "")]
        return year, amends
    return None, []


def _edition_word(text: str, end: int, canonical: str) -> Optional[int]:
    """'Edition 4.0' / '3rd Edition' / 'Second Edition' -> year via catalog edition_years."""
    years = (STANDARDS_CATALOG.get(canonical) or {}).get("edition_years")
    if not years:
        return None
    m = _EDITION_WORD.match(text[end:end + 60])
    if not m:
        return None
    num = m.group(1) or m.group(2) or (_WORD_EDITION.get((m.group(3) or "").lower()))
    try:
        return years.get(int(num))
    except (TypeError, ValueError):
        return None


def detect_standards(text: str) -> List[Dict[str, Any]]:
    """Return [{standard, edition_year, amendments[], raw}] - one entry per canonical standard+edition."""
    found: Dict[Tuple[str, Optional[int]], Dict[str, Any]] = {}
    for rx, canonical in _COMPILED_STANDARDS:
        for m in rx.finditer(text):
            year, amends = _edition_after(text, m.end())
            ed_len = 0
            em = _EDITION_AFTER.match(text[m.end():m.end() + 60])
            if em:
                ed_len = em.end()
            if year is None:
                year = _edition_word(text, m.end(), canonical)
                if year:
                    wm = _EDITION_WORD.match(text[m.end():m.end() + 60])
                    ed_len = wm.end() if wm else 0
            key = (canonical, year)
            raw = re.sub(r"\s+", " ", text[m.start():m.end() + ed_len]).strip()[:48]
            if key not in found:
                found[key] = {"standard": canonical, "edition_year": year, "amendments": amends, "raw": raw}
            elif amends and not found[key]["amendments"]:
                found[key]["amendments"] = amends
    # If a bare mention (no year) co-exists with a dated mention of the same standard, drop the bare one
    dated = {k[0] for k in found if k[1] is not None}
    out = [v for k, v in found.items() if not (k[1] is None and k[0] in dated)]
    out.sort(key=lambda x: (x["standard"], x["edition_year"] or 0))
    return out


def classify_doc_type(text: str, filename: str = "") -> Tuple[str, Dict[str, int]]:
    hay = (filename.replace("_", " ").replace("-", " ") + "\n" + text)[:60000]
    scores: Dict[str, int] = {}
    for dtype, rules in DOC_TYPE_RULES:
        s = 0
        for pat, w in rules:
            n = len(re.findall(pat, hay, re.IGNORECASE))
            if n:
                s += w * min(n, 3) if w >= 3 else w * min(n, 2)
        if s:
            scores[dtype] = s
    if not scores:
        return "UNKNOWN", scores
    order = [d for d, _ in DOC_TYPE_RULES]
    best = max(scores, key=lambda k: (scores[k], -order.index(k)))
    if scores[best] < DOC_TYPE_THRESHOLD:
        return "UNKNOWN", scores
    return best, scores


def _product_index(products: Optional[List[Dict[str, Any]]]):
    """Build [(regex, weight, product)] matchers from the live product list (+ aliases)."""
    matchers = []
    for p in products or []:
        sku = str(p.get("sku") or "").strip()
        if sku:
            prefix = sku.split("-")[0] if "-" in sku else sku[:7]
            if len(prefix) >= 4:
                matchers.append((re.compile(r"(?<![A-Z0-9])" + re.escape(prefix) + r"[A-Z0-9\-]*", re.IGNORECASE), 3, p))
            matchers.append((re.compile(re.escape(sku), re.IGNORECASE), 4, p))
        name = str(p.get("name") or "")
        base = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
        if len(base) >= 8:
            matchers.append((re.compile(re.escape(base).replace(r"\ ", r"\s+"), re.IGNORECASE), 3, p))
        for alias in PRODUCT_ALIASES.get(p.get("id"), []):
            matchers.append((re.compile(r"(?<![A-Za-z0-9])" + re.escape(alias), re.IGNORECASE), 2, p))
    return matchers


def match_product(text: str, products: Optional[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    scores: Dict[str, int] = {}
    byid: Dict[str, Dict[str, Any]] = {}
    for rx, w, p in _product_index(products):
        if rx.search(text):
            pid = p.get("id") or p.get("sku")
            scores[pid] = scores.get(pid, 0) + w
            byid[pid] = p
    if scores:
        best = max(scores, key=scores.get)
        return byid[best]
    return None  # no static fallback: unknown products are reported as unmatched


def detect_lab(text: str) -> Optional[str]:
    for name, pats in _COMPILED_LABS:
        if any(rx.search(text) for rx in pats):
            return name
    m = re.search(r"(?:Laboratory|Test\s+Lab|Issuing\s+Body|Issued\s+by|Testing\s+Facility)\s*[:\-]\s*([A-Z][A-Za-z0-9&,\.\- ]{3,60})", text)
    if m:
        return m.group(1).strip().rstrip(".,")
    return None


_REPORT_NO = re.compile(r"(?:Report\s*(?:No\.?|Number|#|Ref\.?)?|Certificate\s*(?:No\.?|Number|#)?|Registration\s*(?:No\.?|Number|Grant\s+Letter\s+Ref\.?)?|Grant\s+Letter\s+Ref\.?|Ref\.?\s*(?:No\.?)?|DoC\s+Ref)\s*[:.]?\s*([A-Z][A-Z0-9][A-Z0-9\-_/\.]{3,30}\d[A-Z0-9\-_/\.]*)", re.IGNORECASE)


def detect_report_number(text: str, filename: str) -> Optional[str]:
    for m in _REPORT_NO.finditer(text[:20000]):
        cand = m.group(1).strip().rstrip(".,;)")
        if re.search(r"\d", cand) and not re.fullmatch(r"(?:19|20)\d{2}[-/]\d{2}[-/]\d{2}", cand) and cand.upper() not in ("NUMBER", "DATE"):
            return cand
    m = re.search(r"\b(R-R-[A-Za-z0-9]+-[A-Za-z0-9\-]+|R-\d{8}|E\d{6}(?:-[A-Z0-9]+)*)\b", text)
    if m:
        return m.group(1)
    m = re.search(r"([A-Z0-9]{2,}-[A-Z0-9]{3,}(?:-[A-Z0-9]{2,})+)", filename.upper())
    if m:
        return m.group(1)
    return None


def _parse_dates(segment: str) -> List[Tuple[int, _dt.date]]:
    """All dates in a text segment as (position, date), earliest position first."""
    out = []
    for m in _DATE_ISO.finditer(segment):
        try:
            out.append((m.start(), _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))))
        except ValueError:
            pass
    for m in _DATE_DMY_TEXT.finditer(segment):
        try:
            out.append((m.start(), _dt.date(int(m.group(3)), _MONTHS[m.group(2)[:3].lower()], int(m.group(1)))))
        except (ValueError, KeyError):
            pass
    for m in _DATE_MDY_TEXT.finditer(segment):
        try:
            out.append((m.start(), _dt.date(int(m.group(3)), _MONTHS[m.group(1)[:3].lower()], int(m.group(2)))))
        except (ValueError, KeyError):
            pass
    for m in _DATE_DMY_NUM.finditer(segment):
        try:
            out.append((m.start(), _dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))))
        except ValueError:
            pass
    out.sort(key=lambda x: x[0])
    return out


def _labelled_date(text: str, label_rx: re.Pattern) -> Optional[_dt.date]:
    for m in label_rx.finditer(text):
        dates = _parse_dates(text[m.end():m.end() + 40])
        if dates and dates[0][0] <= 12:
            return dates[0][1]
    return None


def detect_dates(text: str) -> Tuple[Optional[str], Optional[str], bool]:
    """Return (issue_date, expiry_date, expiry_explicit)."""
    issue = _labelled_date(text, _ISSUE_LABELS)
    expiry = _labelled_date(text, _EXPIRY_LABELS)
    if issue is None:
        all_dates = [d for _, d in _parse_dates(text[:30000])]
        past = [d for d in all_dates if d <= _today() + _dt.timedelta(days=30) and d != expiry]
        if past:
            issue = max(past)
    if expiry is not None and issue is not None and expiry < issue:
        expiry = None
    return (issue.isoformat() if issue else None, expiry.isoformat() if expiry else None, expiry is not None)


def detect_markets(text: str) -> List[str]:
    codes = set()
    for code, pats in _COMPILED_MARKETS:
        if any(rx.search(text) for rx in pats):
            codes.add(code)
    for code, c in db.COUNTRIES_DB.items():
        if code in codes:
            continue
        name = c.get("name", "")
        if len(name) >= 6 and name not in _COUNTRY_NAME_STOPLIST and re.search(r"\b" + re.escape(name) + r"\b", text):
            codes.add(code)
    return sorted(codes)


def market_name(code: str) -> str:
    if code in MARKET_NAMES:
        return MARKET_NAMES[code]
    return (db.COUNTRIES_DB.get(code) or {}).get("name", code)


def extract_metadata(text: str, filename: str, products: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Regulatory metadata for one document (contract §4 metadata shape + a few helpful extras)."""
    combined = f"{os.path.basename(filename)}\n{text}"
    stds = detect_standards(combined)
    doc_type, type_scores = classify_doc_type(text, os.path.basename(filename))
    product = match_product(combined, products)
    issue_date, expiry_date, expiry_explicit = detect_dates(text)
    expiry_inferred = False
    if expiry_date is None and issue_date and doc_type in INFERRED_VALIDITY_YEARS:
        try:
            d = _dt.date.fromisoformat(issue_date)
            expiry_date = d.replace(year=d.year + INFERRED_VALIDITY_YEARS[doc_type]).isoformat()
            expiry_inferred = True
        except ValueError:
            pass
    days_to_expiry = None
    if expiry_date:
        try:
            days_to_expiry = (_dt.date.fromisoformat(expiry_date) - _today()).days
        except ValueError:
            pass
    return {
        "filename": os.path.basename(filename),
        "doc_type": doc_type,
        "doc_type_label": DOC_TYPE_LABELS.get(doc_type, doc_type),
        "doc_type_confidence": min(100, int(type_scores.get(doc_type, 0) * 10)) if doc_type != "UNKNOWN" else 0,
        "standards_detected": sorted({s["standard"] for s in stds}),
        "standards_editions": [{"standard": s["standard"], "edition_year": s["edition_year"], "amendments": s["amendments"], "raw": s["raw"]} for s in stds],
        "product_id": (product or {}).get("id"),
        "product_sku": (product or {}).get("sku") or "General / Multi-Product",
        "product_name": (product or {}).get("name") or "Not matched to portfolio",
        "product_category_id": (product or {}).get("category_id"),
        "issuing_lab": detect_lab(combined) or "Not identified",
        "report_number": detect_report_number(text, os.path.basename(filename)) or "N/A",
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "expiry_inferred": expiry_inferred,
        "expiry_explicit": expiry_explicit,
        "days_to_expiry": days_to_expiry,
        "markets_detected": detect_markets(combined),
        "text_chars": len(text),
    }



# =============================================================================
# 3. IMPACT EVALUATION - dynamic rulebook
# =============================================================================
def _alert_by_id(alerts, alert_id):
    if not alert_id:
        return None
    for a in alerts or []:
        if a.get("id") == alert_id:
            return a
    return None


def _alert_by_keywords(alerts, keywords, pillar=None):
    """Find the live alert whose title/standard mentions all keywords (case-insensitive); newest first."""
    kws = [k.lower() for k in (keywords or []) if k]
    if not kws:
        return None
    for a in alerts or []:
        hay = f"{a.get('title', '')} {a.get('standard', '')} {a.get('summary', '')}".lower()
        if all(k in hay for k in kws):
            if pillar and _alert_pillar(a) not in (pillar, "All"):
                continue
            return a
    return None


def _resolve_alert(alerts, alert_id=None, keywords=None, pillar=None):
    return _alert_by_id(alerts, alert_id) or _alert_by_keywords(alerts, keywords, pillar)


def _alert_pillar(alert):
    if alert.get("pillar"):
        return alert["pillar"]
    if _rs is not None:
        try:
            return _rs.infer_pillar(alert)
        except Exception:
            pass
    return "All"


def _alert_markets(alert) -> set:
    if _rs is not None and hasattr(_rs, "_alert_country_codes"):
        try:
            codes = set(_rs._alert_country_codes(alert, db.COUNTRIES_DB))
            if codes & EU_COUNTRIES and len(codes & EU_COUNTRIES) >= 20:
                codes.add("EU")
            return codes
        except Exception:
            pass
    cc = str(alert.get("country_code") or "").upper()
    if cc and cc in db.COUNTRIES_DB:
        return {cc}
    cl = str(alert.get("country") or "").lower()
    if "european union" in cl or "eu 27" in cl:
        return set(EU_COUNTRIES) | {"EU"}
    return {code for code, c in db.COUNTRIES_DB.items() if c.get("name", "").lower() in cl} or set(db.COUNTRIES_DB.keys())


def _alert_deadline(alert, fallback=None):
    d = str((alert or {}).get("effective_date") or "")[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        return d
    return fallback


def _days_to(iso):
    try:
        return (_dt.date.fromisoformat(str(iso)[:10]) - _today()).days
    except (TypeError, ValueError):
        return None


def _deadline_label(iso, alert=None):
    if iso:
        return iso
    eff = str((alert or {}).get("effective_date") or "").strip()
    if eff and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", eff):
        return eff  # e.g. "Enforced"
    return "Ongoing"


def _severity_from_deadline(base, days):
    """Escalate severity when the deadline is close or already passed."""
    if days is None:
        return base
    if days < 0:
        return "Critical"
    if days <= 180 and base == "Info":
        return "Warning"
    if days <= 90 and base == "Warning":
        return "Critical"
    return base


def _finding(rule_id, tier, severity, directive, rationale, cost=(0, 0), weeks=(1, 2), alert=None, deadline=None,
             obsolete=None, required=None, confidence="high", source="static"):
    lo, hi = cost
    w_lo, w_hi = weeks
    dl = _alert_deadline(alert, deadline) if alert else deadline
    return {
        "rule_id": rule_id, "impact_tier": tier, "severity": severity, "action_directive": directive,
        "rationale": [r for r in rationale if r][:4], "cost_low": int(lo), "cost_high": int(hi),
        "effort_weeks_low": w_lo, "effort_weeks_high": w_hi,
        "trigger_alert_id": (alert or {}).get("id"), "trigger_alert_title": (alert or {}).get("title"),
        "enforcement_deadline": _deadline_label(dl, alert), "days_to_deadline": _days_to(dl),
        "obsolete_standard_cited": obsolete, "required_standard": required, "confidence": confidence, "source": source,
    }


def _doc_class(doc_type):
    return DOC_CLASS.get(doc_type, "declaration")


def _tier_for(rule, doc_type):
    cls = _doc_class(doc_type)
    return (rule.get("tier_by_class") or {}).get(cls) or CLASS_TIER[cls]


def _cost_for_class(rule, doc_type):
    """Declarations / registrations do not pay lab fees for a superseded citation: scale the rule cost down."""
    lo, hi = rule.get("cost", (0, 0))
    tier = _tier_for(rule, doc_type)
    if tier == "doc_amendment":
        return (0, min(hi, 500)), (1, 2)
    if tier == "portal_filing":
        return (min(lo, 300), min(hi, 2500)), (2, 4)
    if tier == "packaging_update":
        return (400, max(1500, min(hi, 2500))), (2, 4)
    return (lo, hi), rule.get("weeks", (3, 6))


def _superseded_rule_for(std_name, year):
    """Look up the static rulebook: exact 'STD:YEAR' beats 'STD' (any edition); then catalog knowledge."""
    if year is not None and f"{std_name}:{year}" in SUPERSEDED_STANDARDS:
        return SUPERSEDED_STANDARDS[f"{std_name}:{year}"], f"{std_name}:{year}"
    if std_name in SUPERSEDED_STANDARDS and (STANDARDS_CATALOG.get(std_name, {}).get("withdrawn") or year is None):
        return SUPERSEDED_STANDARDS[std_name], std_name
    cat = STANDARDS_CATALOG.get(std_name) or {}
    if cat.get("withdrawn"):
        return {"new_standard": cat.get("replacement"), "alert_id": None, "alert_keywords": cat.get("alert_keywords"), "deadline": None,
                "severity": "Warning", "cost": (2500, 5000), "weeks": (3, 6), "why": f"{std_name} has been withdrawn and replaced by {cat.get('replacement')}."}, std_name
    if year is not None and year in (cat.get("superseded") or {}):
        return {"new_standard": cat["superseded"][year], "alert_id": None, "alert_keywords": cat.get("alert_keywords"), "deadline": None,
                "severity": "Warning", "cost": (2000, 4500), "weeks": (3, 6), "why": f"{std_name}:{year} is a superseded edition; the current edition is {cat['superseded'][year]}."}, f"{std_name}:{year}"
    return None, None


def standard_status(std_name, year=None):
    """current | superseded | unknown (+ replacement)."""
    cat = STANDARDS_CATALOG.get(std_name)
    if not cat:
        return "unknown", None
    if cat.get("withdrawn"):
        return "superseded", cat.get("replacement")
    if year is not None:
        if year in (cat.get("superseded") or {}):
            return "superseded", cat["superseded"][year]
        if cat.get("current") and year < min(cat["current"]):
            return "superseded", f"{std_name}:{max(cat['current'])}"
        return "current", None
    return "current", None


def _doc_pillars(meta):
    pillars = set(DOC_TYPE_PILLARS.get(meta.get("doc_type"), set()))
    for s in meta.get("standards_detected", []):
        p = (STANDARDS_CATALOG.get(s) or {}).get("pillar")
        if p:
            pillars.add(p)
    return pillars


def _markets_of_doc(meta, product):
    mk = set(meta.get("markets_detected") or [])
    if "EU" in mk:
        mk |= EU_COUNTRIES
    if product and not mk:
        mk = {m.upper() for m in product.get("target_markets", [])}
    return mk


def _product_for(meta, products):
    pid = meta.get("product_id")
    for p in products or []:
        if p.get("id") == pid:
            return p
    return None


def _sells_in(product, codes):
    if not product:
        return True  # unknown product: do not suppress
    return bool({m.upper() for m in product.get("target_markets", [])} & set(codes))


def _has(text_upper, *terms):
    return any(t.upper() in text_upper for t in terms)


# ---------------------------------------------------------------- rule groups
def _rules_superseded_standards(meta, T, alerts):
    out = []
    for ed in meta.get("standards_editions", []):
        rule, key = _superseded_rule_for(ed["standard"], ed.get("edition_year"))
        if not rule:
            continue
        doc_type = meta["doc_type"]
        tier = _tier_for(rule, doc_type)
        cost, weeks = _cost_for_class(rule, doc_type)
        alert = _resolve_alert(alerts, rule.get("alert_id"), rule.get("alert_keywords"))
        cited = ed["raw"] or key
        cls = _doc_class(doc_type)
        if cls == "report":
            directive = f"Re-test / re-evaluate against {rule['new_standard']} and obtain an updated report or CB certificate; the current document cites {cited}."
        elif cls == "declaration":
            directive = f"Re-issue and re-sign this declaration citing {rule['new_standard']} (currently cites {cited}); attach the supporting current-edition report to the technical file."
        elif cls == "registration":
            directive = f"File an update / re-registration with the national scheme so the certificate references {rule['new_standard']} instead of {cited}; supply the supporting test report to the new standard."
        else:
            directive = f"Update the artwork / marking specification to {rule['new_standard']} (currently references {cited})."
        deadline = rule.get("deadline")
        sev = rule.get("severity", "Warning")
        eff_days = _days_to(_alert_deadline(alert, deadline) if alert else deadline)
        out.append(_finding(
            f"superseded:{key}", tier, _severity_from_deadline(sev, eff_days), directive,
            [rule.get("why"),
             f"This document cites '{cited}', which is no longer the current reference for this requirement.",
             f"Because it is a {_soft_lower(DOC_TYPE_LABELS.get(doc_type, doc_type))}, the required action is: {TIER_LABELS[tier].lower()}.",
             f"Linked live alert: {alert['title']} (deadline {alert.get('effective_date')})." if alert else "No live alert currently tracks this transition; the deadline shown is the engine's static knowledge."],
            cost=cost, weeks=weeks, alert=alert, deadline=deadline, obsolete=cited, required=rule["new_standard"], confidence="high", source="static+alert" if alert else "static"))
    return out


def _rules_expiry(meta, T, alerts):
    days = meta.get("days_to_expiry")
    if days is None:
        return []
    doc_type = meta["doc_type"]
    cls = _doc_class(doc_type)
    inferred = meta.get("expiry_inferred")
    label = _soft_lower(DOC_TYPE_LABELS.get(doc_type, doc_type))
    basis = "an inferred validity period (the file states no expiry date)" if inferred else "the expiry date stated in the file"
    if days < 0:
        tier = "portal_filing" if cls == "registration" else "doc_amendment"
        out = _finding(
            "expiry:expired", tier, "Critical" if not inferred else "Warning",
            f"Renew this {label} - it expired on {meta['expiry_date']} ({-days} days ago). " + ("Submit the renewal on the national scheme portal with current test evidence." if cls == "registration" else "Obtain a re-issued document from the issuer (a review against the current standard edition is usually required)."),
            [f"Expiry {meta['expiry_date']} is based on {basis}.",
             "An expired certificate or registration cannot be presented at customs or to a market-surveillance authority; shipments may be held.",
             "Renewal is typically cheaper and faster than a fresh application if the product is unchanged - start with the issuer." if cls == "registration" else "Confirm with the issuer whether a simple re-issue is possible or whether a current-edition review is needed.",
             f"Typical validity for a {label}: {INFERRED_VALIDITY_YEARS.get(doc_type)} year(s) (renewable)." if inferred else None],
            cost=(300, 2000) if cls == "registration" else (0, 800), weeks=(2, 6), deadline=meta["expiry_date"], confidence="medium" if inferred else "high", source="expiry")
        out["renewal"] = True
        return [out]
    if days <= 90:
        tier = "portal_filing" if cls == "registration" else "doc_amendment"
        out = _finding(
            "expiry:expiring", tier, "Warning",
            f"Start the renewal now - this {label} expires on {meta['expiry_date']} (in {days} days).",
            [f"Expiry {meta['expiry_date']} is based on {basis}.", "Renewal lead times of 4-8 weeks are common for national registrations; leaving it later risks a gap in market access.",
             "Check whether the standard edition cited is still current before renewing, or the renewal may be refused."],
            cost=(300, 2000) if cls == "registration" else (0, 800), weeks=(2, 6), deadline=meta["expiry_date"], confidence="medium" if inferred else "high", source="expiry")
        out["renewal"] = True
        return [out]
    return []


def _rules_content_checks(meta, T, alerts, product):
    """Curated requirement checks (the task's explicit rules), each tied to the live alert that tracks it."""
    out = []
    dt = meta["doc_type"]
    markets = _markets_of_doc(meta, product)
    cat_id = (product or {}).get("category_id") or meta.get("product_category_id")

    # FCC SDoC: responsible-party statement (47 CFR 2.1077) + covered-list attestation
    if dt == "FCC_SDOC":
        if not _has(T, "RESPONSIBLE PARTY"):
            alert = _resolve_alert(alerts, None, ["FCC"], "EMC") or _resolve_alert(alerts, "ALERT-2026-05")
            out.append(_finding("fcc:responsible_party", "doc_amendment", "Warning",
                                "Add the responsible-party compliance statement (US-based responsible party name, address and telephone/email per 47 CFR 2.1077(a)(3)) and re-issue the SDoC.",
                                ["An FCC Supplier's Declaration of Conformity must identify a responsible party located in the United States; this document contains no responsible-party statement.",
                                 "Without it the SDoC is incomplete and the product cannot be lawfully marketed under Part 15 Subpart B.",
                                 f"Related live alert: {alert['title']}." if alert else None],
                                cost=(0, 300), weeks=(1, 1), alert=alert, required="47 CFR 2.1077 compliance information", confidence="high", source="content"))
        if not _has(T, "COVERED LIST", "2.911", "SECURE AND TRUSTED", "KDB 986446"):
            alert = _resolve_alert(alerts, "ALERT-2026-05", ["Covered List"])
            if alert:
                out.append(_finding("fcc:covered_list", "doc_amendment", "Info",
                                    "Add the Covered List (47 CFR 2.911(d)(5)/(d)(7)) supply-chain attestation to the SDoC file at the next revision.",
                                    ["The live alert requires equipment-authorisation records to include an attestation that no Covered List components are used.",
                                     "The SDoC text contains no reference to the Covered List or 47 CFR 2.911."],
                                    cost=(0, 300), weeks=(1, 1), alert=alert, confidence="medium", source="alert"))

    # EU DoC content
    if dt == "EU_DECLARATION_OF_CONFORMITY":
        if not _has(T, "2011/65/EU", "ROHS"):
            alert = _resolve_alert(alerts, "ALERT-2026-04", ["RoHS"], "Environmental") or _resolve_alert(alerts, "ALERT-ENV-07")
            out.append(_finding("eudoc:rohs_missing", "doc_amendment", "Warning",
                                "Add the RoHS Directive 2011/65/EU (as amended by (EU) 2015/863) clause with EN IEC 63000 as the harmonised standard, then re-sign the DoC.",
                                ["Every EU DoC for electrical and electronic equipment must declare conformity with RoHS Directive 2011/65/EU; this declaration does not mention it.",
                                 "Market-surveillance authorities routinely reject DoCs that omit RoHS.",
                                 "REACH is not declared on the DoC itself, but the technical file should hold the SVHC attestation." if not _has(T, "REACH") else None],
                                cost=(0, 300), weeks=(1, 2), alert=alert, required="Directive 2011/65/EU + EN IEC 63000:2018", confidence="high", source="content"))
        if cat_id in FIRMWARE_CATEGORIES and not _has(T, "2024/2847", "CYBER RESILIENCE", "EN 18031"):
            alert = _resolve_alert(alerts, "ALERT-2026-01", ["Cyber Resilience"])
            out.append(_finding("eudoc:cra_missing", "doc_amendment", (alert or {}).get("severity", "Warning"),
                                "Plan the DoC update to reference Regulation (EU) 2024/2847 (Cyber Resilience Act) and add the SBOM / vulnerability-handling evidence to the technical file before the CRA conformity-assessment date.",
                                ["This product category carries firmware (a 'product with digital elements'), so the Cyber Resilience Act applies to it in the EU.",
                                 "The DoC does not reference the CRA or EN 18031; from the alert's enforcement date the CE marking must also cover cybersecurity.",
                                 f"Live alert deadline: {alert.get('effective_date')}." if alert else "No live CRA alert found - static knowledge used (CRA obligations apply from 11 December 2027; reporting from 11 September 2026)."],
                                cost=(1500, 6000), weeks=(4, 8), alert=alert, deadline="2027-12-11", required="Regulation (EU) 2024/2847 + EN 18031 series", confidence="medium", source="alert"))

    # UKCA DoC for connectable products: PSTI
    if dt == "UKCA_DECLARATION_OF_CONFORMITY" and cat_id in FIRMWARE_CATEGORIES and not _has(T, "PSTI", "PRODUCT SECURITY AND TELECOMMUNICATIONS"):
        alert = _resolve_alert(alerts, "ALERT-2026-10", ["PSTI"])
        if alert:
            out.append(_finding("ukdoc:psti", "doc_amendment", "Warning",
                                "Add a UK PSTI statement of compliance (security requirements schedule) to the UKCA technical file if the product is 'connectable'.",
                                ["The UK PSTI regime is enforced for internet-connectable consumer products; the UKCA DoC and technical file contain no PSTI statement.",
                                 "Storage products that are not network-connectable may be out of scope - confirm and record the scoping decision."],
                                cost=(0, 800), weeks=(1, 3), alert=alert, confidence="low", source="alert"))

    # Packaging artwork checks
    if dt == "PACKAGING_ARTWORK_SPEC":
        missing = []
        if (not markets or markets & {"FR", "EU"} or "EU" in meta.get("markets_detected", [])) and not _has(T, "TRIMAN", "INFO-TRI", "INFO TRI"):
            missing.append(("fr", "France Triman logo + Info-tri sorting instructions (Decree 2021-835 / AGEC)", _resolve_alert(alerts, "ALERT-ENV-03", ["Triman"])))
        if (not markets or markets & {"IT", "EU"}) and not _has(T, "116/2020", "97/129", "129/97", "PAP 2", "PET 1", "HDPE 2", "LDPE 4", "PP 5", "PS 6"):
            missing.append(("it", "Italy alphanumeric material identification code (D.Lgs 116/2020 / Decision 97/129/EC, e.g. PAP 21)", _resolve_alert(alerts, "ALERT-ENV-04", ["116/2020"])))
        if (not markets or markets & (EU_COUNTRIES | {"EU"})) and not _has(T, "PPWR", "2025/40", "RECYCLED CONTENT", "HEAVY METAL"):
            missing.append(("ppwr", "EU PPWR statement (recycled-content share, heavy-metal limits, harmonised labelling - Regulation (EU) 2025/40)", _resolve_alert(alerts, "ALERT-ENV-02", ["PPWR"])))
        if missing:
            primary_alert = next((a for _, _, a in missing if a), None)
            sev = "Critical" if any(k in ("fr", "it") for k, _, _ in missing) else "Warning"
            out.append(_finding("packaging:marks_missing", "packaging_update", sev,
                                "Issue a revised die-line / artwork adding: " + "; ".join(m for _, m, _ in missing) + ". Send to the printer and update the packaging spec revision.",
                                [f"The artwork specification lists its regulatory marks explicitly but is missing: {'; '.join(m.split(' (')[0] for _, m, _ in missing)}.",
                                 "France and Italy actively enforce their sorting / material-coding marks at retail; non-conforming packaging can be refused by distributors.",
                                 "The EU PPWR applies from 12 August 2026 and harmonises labelling and recycled-content declarations - plan one artwork change that covers all three." if any(k == "ppwr" for k, _, _ in missing) else None,
                                 f"Live alert: {primary_alert['title']}." if primary_alert else None],
                                cost=(400, 2500), weeks=(2, 4), alert=primary_alert, obsolete="Generic Mobius loop / uncoded packaging", required="Triman + Info-tri; Italian material coding; PPWR labelling", confidence="high", source="content+alert"))

    # FMD / RoHS reports: PFAS
    if dt in ("FMD_BOM_DISCLOSURE", "ROHS_CHEMICAL_REPORT"):
        not_eval = _has(T, "NOT EVALUATED", "POTENTIAL FLUOROPOLYMER", "NOT ASSESSED", "TBD")
        no_pfas = not _has(T, "PFAS", "PER- AND POLYFLUORO", "PERFLUORO", "TSCA")
        if not_eval or no_pfas:
            alert = _resolve_alert(alerts, "ALERT-ENV-01", ["PFAS"], "Environmental")
            state_alert = _resolve_alert(alerts, "ALERT-ENV-06", ["Maine"])
            out.append(_finding("chem:pfas", "doc_amendment", (alert or {}).get("severity", "Warning") if _sells_in(product, {"US"}) else "Warning",
                                "Issue PFAS declaration requests (IPC-1752A Class D or equivalent) to the suppliers of the undeclared parts, then re-issue the disclosure with a per-part PFAS status.",
                                ["PFAS status is missing or marked 'not evaluated' for one or more parts (typical suspects: thermal pads, PTFE wire jackets, fluoropolymer coatings)." if not_eval else "The disclosure does not mention PFAS or TSCA at all, so PFAS content cannot be demonstrated as declared.",
                                 f"US TSCA 8(a)(7) requires manufacturers/importers of articles containing PFAS to report to EPA (live alert deadline {alert.get('effective_date')})." if alert else "US TSCA Section 8(a)(7) requires reporting of PFAS in imported articles.",
                                 f"US state bans (Maine / Minnesota) also require PFAS knowledge for products sold there ({state_alert['title']})." if state_alert else None,
                                 "The EU universal PFAS restriction proposal (REACH Annex XVII) will need the same data - collecting it once serves both."],
                                cost=(800, 2500), weeks=(3, 6), alert=alert, required="TSCA 40 CFR Part 705 PFAS declaration per part", confidence="high" if not_eval else "medium", source="content+alert"))

    # BIS grant: CPCB EPR linkage
    if dt == "BIS_REGISTRATION_GRANT" and not _has(T, "CPCB", "EPR"):
        alert = _resolve_alert(alerts, "ALERT-ENV-05", ["CPCB"])
        if alert:
            out.append(_finding("bis:cpcb_epr", "portal_filing", "Warning",
                                "Register / link the producer on the CPCB EPR portal and record the EPR registration number alongside this BIS grant.",
                                ["India's E-Waste (Management) Rules 2022 require producers to hold a CPCB EPR registration; this BIS file has no CPCB / EPR reference.",
                                 f"Live alert deadline: {alert.get('effective_date')}."],
                                cost=(300, 900), weeks=(2, 4), alert=alert, confidence="medium", source="alert"))

    # BSMI: CNS 15663 table
    if dt == "BSMI_CERTIFICATE" and not _has(T, "CNS 15663", "15663"):
        alert = _resolve_alert(alerts, "ALERT-2026-08", ["CNS 15663"])
        if alert:
            out.append(_finding("bsmi:cns15663", "doc_amendment", "Warning",
                                "Add the CNS 15663 Section 5 'marking of presence' RoHS table to the BSMI technical file / product marking.",
                                ["BSMI is scrutinising the CNS 15663 Section 5 table; the certificate file has no RoHS presence-condition declaration.", f"Live alert deadline: {alert.get('effective_date')}."],
                                cost=(300, 1200), weeks=(2, 4), alert=alert, confidence="medium", source="alert"))

    # SASO / SABER: RoHS test evidence
    if dt == "SASO_SABER_CERTIFICATE" and not _has(T, "ROHS", "62321"):
        alert = _resolve_alert(alerts, "ALERT-2026-06", ["SASO"])
        if alert:
            out.append(_finding("saso:rohs", "portal_filing", "Warning",
                                "Upload an IEC 62321 RoHS test report to the SABER product record before the next shipment certificate (SCoC) request.",
                                ["SASO enforces its RoHS technical regulation through SABER; this certificate file shows no RoHS test evidence.", f"Live alert deadline: {alert.get('effective_date')}."],
                                cost=(600, 1800), weeks=(2, 4), alert=alert, confidence="medium", source="alert"))

    # SBOM file quality
    if dt == "CYBERSECURITY_SBOM" and not _has(T, "CYCLONEDX", "SPDX"):
        alert = _resolve_alert(alerts, "ALERT-2026-01", ["Cyber Resilience"])
        out.append(_finding("sbom:format", "doc_amendment", "Info",
                            "Export the SBOM in a machine-readable format (CycloneDX or SPDX) and store it with the technical documentation.",
                            ["The CRA expects a machine-readable SBOM; this file does not indicate CycloneDX or SPDX format."], cost=(0, 500), weeks=(1, 2), alert=alert, confidence="low", source="alert"))
    return out


_CURATED_ALERT_IDS = {"ALERT-2026-01", "ALERT-2026-02", "ALERT-2026-03", "ALERT-2026-04", "ALERT-2026-05", "ALERT-2026-06", "ALERT-2026-07", "ALERT-2026-08",
                      "ALERT-2026-09", "ALERT-2026-10", "ALERT-ENV-01", "ALERT-ENV-02", "ALERT-ENV-03", "ALERT-ENV-04", "ALERT-ENV-05", "ALERT-ENV-06", "ALERT-ENV-07"}


def _rules_live_alerts(meta, T, alerts, product):
    """Generic rules derived from *every* live alert (seed alerts are covered by the curated checks above,
    so this mainly picks up surveillance / user-created alerts):
      (a) edition rule  - the alert names STANDARD:YEAR and the document cites STANDARD with an older year
      (b) gap rule      - alert markets ∩ document markets, pillar match, category match, and no evidence
                          of the alert's standard in the document text."""
    out = []
    doc_pillars = _doc_pillars(meta)
    doc_markets = _markets_of_doc(meta, product)
    cat_id = (product or {}).get("category_id") or meta.get("product_category_id")
    doc_type = meta["doc_type"]
    if doc_type == "UNKNOWN":
        return out
    cited = {(e["standard"], e.get("edition_year")) for e in meta.get("standards_editions", [])}
    for alert in alerts or []:
        aid = alert.get("id")
        if not aid or aid in _CURATED_ALERT_IDS:
            continue
        a_stds = detect_standards(f"{alert.get('standard', '')}\n{alert.get('title', '')}")
        a_pillar = _alert_pillar(alert)
        # applicability gate shared by both rules: pillar, product category, markets
        if a_pillar not in ("All",) and a_pillar not in doc_pillars:
            continue
        if cat_id and alert.get("affected_categories") and not any(c in ("all", "all_storage_categories") or c == cat_id for c in alert["affected_categories"]):
            continue
        a_markets = _alert_markets(alert)
        if doc_markets and not (a_markets & doc_markets):
            continue
        # (a) edition rule
        for a in a_stds:
            if a.get("edition_year") is None:
                continue
            for (s, y) in cited:
                if s == a["standard"] and y is not None and y < a["edition_year"]:
                    tier = CLASS_TIER[_doc_class(doc_type)]
                    cost = (2500, 5000) if tier == "retesting_required" else (0, 800) if tier == "doc_amendment" else (300, 2000)
                    out.append(_finding(f"alert-edition:{aid}", tier, _severity_from_deadline(alert.get("severity", "Warning"), _days_to(_alert_deadline(alert))),
                                        f"Update this {_soft_lower(DOC_TYPE_LABELS.get(doc_type, doc_type))} from {s}:{y} to {a['raw']} as required by alert {aid}.",
                                        [f"Live alert '{alert.get('title')}' mandates {a['raw']}; this document cites the older {s}:{y}.",
                                         f"Applies from {alert.get('effective_date')} in {alert.get('country') or alert.get('region')}.",
                                         "Rule derived automatically from the alert's standard reference - confirm the edition mapping with the issuing lab."],
                                        cost=cost, weeks=(2, 6) if tier != "retesting_required" else (4, 8), alert=alert, obsolete=f"{s}:{y}", required=a["raw"], confidence="medium", source="alert-dynamic"))
                    break
        # (b) market x pillar gap rule (no evidence of the alert's standard anywhere in the text)
        evidence = [a["standard"] for a in a_stds] + [str(alert.get("standard") or "")[:40]]
        if any(e and e.upper() in T for e in evidence if len(e) >= 4) or any((s, None) in cited or s in {c[0] for c in cited} for s in evidence):
            continue
        if any(f["trigger_alert_id"] == aid for f in out):
            continue
        tier = CLASS_TIER[_doc_class(doc_type)]
        base_sev = {"Critical": "Warning", "Warning": "Info", "Info": "Info"}.get(alert.get("severity"), "Info")
        out.append(_finding(f"alert-gap:{aid}", tier, base_sev,
                            f"Review this document against alert {aid} ({alert.get('standard')}) and add evidence of the new requirement if it applies.",
                            [f"Live alert '{alert.get('title')}' applies to this document's markets ({', '.join(sorted(a_markets & doc_markets)[:6]) or 'all'}) and pillar ({a_pillar}).",
                             f"The document shows no reference to '{alert.get('standard')}'.",
                             "This is an inferred gap (no explicit superseded citation) - a compliance engineer should confirm applicability."],
                            cost=(0, 1500), weeks=(1, 4), alert=alert, required=alert.get("standard"), confidence="low", source="alert-dynamic"))
    return out[:3]


def evaluate_document_impact(meta: Dict[str, Any], file_text: str, alerts: Optional[List[Dict[str, Any]]] = None,
                             products: Optional[List[Dict[str, Any]]] = None, unreadable_reason: Optional[str] = None) -> Dict[str, Any]:
    """Run the dynamic rulebook for one document and return the contract impact shape.

    The primary finding (the one that sets impact_tier / severity / directive) is the highest-ranked by
    (tier rank, confidence, severity). All findings are kept in `findings[]` for transparency."""
    if unreadable_reason:
        return {
            "is_impacted": False, "impact_tier": "unreadable", "severity": "Info", "trigger_alert_id": None, "trigger_alert_title": None,
            "obsolete_standard_cited": None, "required_standard": None,
            "action_directive": f"File could not be read ({unreadable_reason}). Open it manually, or re-export it as a text-based PDF / DOCX / XLSX and re-scan.",
            "enforcement_deadline": "n/a", "days_to_deadline": None, "estimated_effort": "Manual review (0.5 day)", "estimated_cost": "$0",
            "cost_low": 0, "cost_high": 0, "effort_weeks": 0,
            "rationale": ["The scanner could not extract any text from this file, so its regulatory content is unknown.",
                          "Scanned-image PDFs need OCR before they can be audited; corrupt or legacy binary files should be re-exported.",
                          "Unreadable files count against the folder health score until they are resolved."],
            "findings": [], "confidence": "high",
        }
    T = (file_text or "").upper()
    product = _product_for(meta, products)
    findings = []
    findings += _rules_superseded_standards(meta, T, alerts)
    findings += _rules_expiry(meta, T, alerts)
    findings += _rules_content_checks(meta, T, alerts, product)
    findings += _rules_live_alerts(meta, T, alerts, product)
    # de-duplicate by rule_id
    seen, uniq = set(), []
    for f in findings:
        if f["rule_id"] in seen:
            continue
        seen.add(f["rule_id"])
        uniq.append(f)
    findings = uniq
    findings.sort(key=lambda f: (TIER_RANK.get(f["impact_tier"], 0), CONFIDENCE_RANK.get(f["confidence"], 0), SEVERITY_RANK.get(f["severity"], 0)), reverse=True)

    if not findings:
        current = [e for e in meta.get("standards_editions", []) if standard_status(e["standard"], e.get("edition_year"))[0] == "current" and e.get("edition_year")]
        rationale = ["No superseded or withdrawn standard is cited.",
                     "No live alert rule matched this document's markets, pillar and product category without evidence in the text.",
                     f"Current editions cited: {', '.join(e['raw'] for e in current[:3])}." if current else "No dated standard editions were found - the document was checked on content and expiry only.",
                     f"Valid until {meta['expiry_date']}{' (inferred)' if meta.get('expiry_inferred') else ''}." if meta.get("expiry_date") else None]
        return {
            "is_impacted": False, "impact_tier": "compliant", "severity": "None", "trigger_alert_id": None, "trigger_alert_title": None,
            "obsolete_standard_cited": None, "required_standard": None,
            "action_directive": "No action required - the document cites current standards and no active alert rule applies. Re-check after the next alert scan.",
            "enforcement_deadline": "Ongoing", "days_to_deadline": None, "estimated_effort": "None", "estimated_cost": "$0",
            "cost_low": 0, "cost_high": 0, "effort_weeks": 0, "rationale": [r for r in rationale if r], "findings": [], "confidence": "high",
        }
    p = findings[0]
    cost_low = sum(f["cost_low"] for f in findings)
    cost_high = sum(f["cost_high"] for f in findings)
    weeks_hi = max(f["effort_weeks_high"] for f in findings)
    weeks_lo = max(f["effort_weeks_low"] for f in findings)
    extra = len(findings) - 1
    directive = p["action_directive"] + (f" (+{extra} further finding{'s' if extra > 1 else ''} - see rationale)" if extra else "")
    return {
        "is_impacted": True, "impact_tier": p["impact_tier"], "severity": p["severity"],
        "trigger_alert_id": p["trigger_alert_id"], "trigger_alert_title": p["trigger_alert_title"],
        "obsolete_standard_cited": p["obsolete_standard_cited"], "required_standard": p["required_standard"],
        "action_directive": directive, "enforcement_deadline": p["enforcement_deadline"], "days_to_deadline": p["days_to_deadline"],
        "estimated_effort": f"{weeks_lo} - {weeks_hi} weeks" if weeks_hi != weeks_lo else f"{weeks_hi} week{'s' if weeks_hi != 1 else ''}",
        "estimated_cost": f"${cost_low:,} - ${cost_high:,} (indicative)" if cost_high else "$0 (internal effort)",
        "cost_low": cost_low, "cost_high": cost_high, "effort_weeks": weeks_hi,
        "rationale": p["rationale"], "findings": findings, "confidence": p["confidence"],
    }



# =============================================================================
# 4. REPORT ASSEMBLY - health score, gap analysis, remediation plan, indexes
# =============================================================================
HEALTH_PENALTY = {"retesting_required": 25, "packaging_update": 12, "doc_amendment": 8, "portal_filing": 6, "unreadable": 3, "compliant": 0}
EXPIRED_PENALTY = 15
PER_DOC_CAP = 25


def health_score(documents: List[Dict[str, Any]]) -> Tuple[int, str]:
    """Folder health 0-100.

    Each document contributes a penalty = tier penalty (retest 25, packaging 12, doc amendment 8, portal 6,
    unreadable 3, compliant 0) + 15 if its certificate/registration is already expired, capped at 25 per
    document. The score is the share of the maximum possible penalty (25 x number of documents) that was
    *not* incurred:  score = 100 x (1 - sum(min(25, penalty_d)) / (25 x N)).  Scaling by N means one bad
    file in a large, otherwise healthy folder lowers the score proportionally instead of zeroing it.
    Grades: A >= 90, B >= 80, C >= 65, D >= 50, F below 50. An empty folder scores 0 / F (nothing verified)."""
    n = len(documents)
    if n == 0:
        return 0, "F"
    total = 0.0
    for d in documents:
        tier = d["impact"]["impact_tier"]
        pen = HEALTH_PENALTY.get(tier, 0)
        days = d["metadata"].get("days_to_expiry")
        if days is not None and days < 0 and tier != "unreadable":
            pen += EXPIRED_PENALTY
        total += min(PER_DOC_CAP, pen)
    score = int(round(100 * (1 - total / (PER_DOC_CAP * n))))
    score = max(0, min(100, score))
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 65 else "D" if score >= 50 else "F"
    return score, grade


# Gap analysis: requirement text -> which scanned documents satisfy it.
# Each entry: (regex on the requirement string, predicate(doc_meta) -> bool). First match wins.
def _std_family(meta, *canon_prefixes):
    return any(any(s.startswith(p) for p in canon_prefixes) for s in meta.get("standards_detected", []))


def _mk(meta, *codes):
    mk = set(meta.get("markets_detected", []))
    return bool(mk & set(codes)) or not mk


GAP_COVERAGE_RULES = [
    (r"customs|commercial invoice|packing list|certificate of origin|import(?:er)?\b.*(?:agreement|license|licence|documents|verification|notification|registration)|business (?:license|registration)|KYC|representative|user (?:manual|guide)|instructions|entry summary|CBP Form|todokede|exemption (?:declaration|attestation|review)|migration plan|factory (?:inspection|audit)|local legal|responsible supplier registration|ERAC|producer registration|national producer",
     None),  # administrative / commercial paperwork - not assessable from a document scan
    (r"CB test certificate|IECEE|CB scheme|CB component|CB report", lambda m: m["doc_type"] == "CB_TEST_CERTIFICATE" or (m["doc_type"] == "SAFETY_TEST_REPORT" and _std_family(m, "IEC 62368-1", "IEC 60950-1"))),
    (r"UL Recognized|NRTL|Bauart|cULus|Safety Listing", lambda m: m["doc_type"] in ("SAFETY_TEST_REPORT", "CB_TEST_CERTIFICATE") and _std_family(m, "UL 62368-1", "CSA", "IEC 62368-1", "UL 60950-1")),
    (r"KC (?:Safety )?Certificate|KC Conformity|KC Component|KC Regulatory Label|KC Mark", lambda m: m["doc_type"] == "KC_CERTIFICATE"),
    (r"KN 3[25]|KS C 98", lambda m: m["doc_type"] in ("KC_CERTIFICATE", "EMC_LAB_REPORT") and (_std_family(m, "KN 32", "KN 35", "KS C") or _mk(m, "KR"))),
    (r"BSMI", lambda m: m["doc_type"] == "BSMI_CERTIFICATE"),
    (r"CNS 15936|CNS 13438", lambda m: m["doc_type"] in ("BSMI_CERTIFICATE", "EMC_LAB_REPORT") and (_std_family(m, "CNS 15936", "CNS 13438") or _mk(m, "TW"))),
    (r"CNS 15663|Taiwan RoHS", lambda m: m["doc_type"] in ("BSMI_CERTIFICATE", "ROHS_CHEMICAL_REPORT", "FMD_BOM_DISCLOSURE") and (_std_family(m, "CNS 15663") or _mk(m, "TW"))),
    (r"CCC|China Compulsory", lambda m: m["doc_type"] == "CCC_CERTIFICATE"),
    (r"GB/T 9254|GB 9254", lambda m: m["doc_type"] in ("CCC_CERTIFICATE", "EMC_LAB_REPORT") and (_std_family(m, "GB/T 9254.1", "GB 9254") or _mk(m, "CN"))),
    (r"China RoHS|SJ/T 11364|EFUP", lambda m: _std_family(m, "SJ/T 11364") or (m["doc_type"] in ("ROHS_CHEMICAL_REPORT", "FMD_BOM_DISCLOSURE", "PACKAGING_ARTWORK_SPEC") and _mk(m, "CN"))),
    (r"China Energy Label", lambda m: m["doc_type"] == "ENERGY_EFFICIENCY_REPORT" and _mk(m, "CN")),
    (r"PSE", lambda m: m["doc_type"] == "PSE_CERTIFICATE"),
    (r"VCCI", lambda m: _std_family(m, "VCCI-CISPR 32") or (m["doc_type"] == "EMC_LAB_REPORT" and _mk(m, "JP"))),
    (r"J-Moss|Japan RoHS", lambda m: m["doc_type"] in ("ROHS_CHEMICAL_REPORT", "FMD_BOM_DISCLOSURE") and _mk(m, "JP")),
    (r"BIS", lambda m: m["doc_type"] == "BIS_REGISTRATION_GRANT"),
    (r"NABL|IS/IEC 62368|IS 13252", lambda m: m["doc_type"] in ("SAFETY_TEST_REPORT", "CB_TEST_CERTIFICATE", "BIS_REGISTRATION_GRANT") and (_std_family(m, "IS 13252", "IS/IEC 62368-1") or _mk(m, "IN"))),
    (r"E-Waste|CPCB", lambda m: _std_family(m, "India E-Waste", "CPCB") or (m["doc_type"] in ("ROHS_CHEMICAL_REPORT", "FMD_BOM_DISCLOSURE") and _mk(m, "IN"))),
    (r"SABER|SASO|ECAS|PCoC|SCoC", lambda m: m["doc_type"] == "SASO_SABER_CERTIFICATE"),
    (r"FCC.*SDoC|Supplier'?s Declaration of Conformity \(SDoC\)|FCC Compliance Statement", lambda m: m["doc_type"] == "FCC_SDOC"),
    (r"ANSI C63\.4|FCC Part 15|Part 15 Class", lambda m: m["doc_type"] in ("EMC_LAB_REPORT", "FCC_SDOC") and (_std_family(m, "FCC Part 15B", "ANSI C63.4") or _mk(m, "US"))),
    (r"DoE|Level VI|10 CFR|Energy Efficiency|ErP|Ecodesign|2019/1782|MEPS|Energy Conservation|KEMCO|Top Runner|Efficiency (?:Registration|Statement|Attestation)", lambda m: m["doc_type"] == "ENERGY_EFFICIENCY_REPORT"),
    (r"TSCA|Prop(?:osition)? 65", lambda m: m["doc_type"] in ("ROHS_CHEMICAL_REPORT", "FMD_BOM_DISCLOSURE") and (_std_family(m, "TSCA", "California Proposition 65") or _mk(m, "US"))),
    (r"EU Declaration of Conformity|DoC\) covering|under EMC Directive|Declaration of Conformity \(DoC\) under", lambda m: m["doc_type"] == "EU_DECLARATION_OF_CONFORMITY"),
    (r"UK(?:CA)? Declaration|UKCA", lambda m: m["doc_type"] == "UKCA_DECLARATION_OF_CONFORMITY"),
    (r"UK RoHS", lambda m: m["doc_type"] in ("ROHS_CHEMICAL_REPORT", "FMD_BOM_DISCLOSURE") and _mk(m, "GB", "EU")),
    (r"EN 55032|EN 55035|CISPR 32|AS/NZS CISPR|EMC (?:Class B )?(?:Laboratory |Lab )?Test Report|Emissions Test Report|Radiated Emissions|Local EMC|Accredited EMC|Host Integration Safety & EMC", lambda m: m["doc_type"] == "EMC_LAB_REPORT"),
    (r"RoHS|REACH|SVHC|Material Disclosure|EN IEC 63000|Hazardous|Chemical|Halogen|Environmental", lambda m: m["doc_type"] in ("ROHS_CHEMICAL_REPORT", "FMD_BOM_DISCLOSURE")),
    (r"Safety Test Report|Safety Certificate|In-Country Safety|Safety & EMC File", lambda m: m["doc_type"] in ("SAFETY_TEST_REPORT", "CB_TEST_CERTIFICATE")),
    (r"Certificate of Conformity|CoC|National Certificate|Conformity Assessment", lambda m: m["doc_type"] in ("SASO_SABER_CERTIFICATE", "CB_TEST_CERTIFICATE", "KC_CERTIFICATE", "BSMI_CERTIFICATE", "CCC_CERTIFICATE", "PSE_CERTIFICATE")),
    (r"(?:Supplier|Manufacturer|ACMA|Declaration of Conformity)", lambda m: m["doc_type"] in ("EU_DECLARATION_OF_CONFORMITY", "UKCA_DECLARATION_OF_CONFORMITY", "FCC_SDOC", "TECHNICAL_COMPLIANCE_FILE")),
    (r"Packaging|Label(?:ing|ling)?|Mark(?:ing)? on|Wheelie Bin|Importer Address|Importer Identification|CE Mark|Identification Label|Commodity Inspection Mark|Standard Mark", lambda m: m["doc_type"] == "PACKAGING_ARTWORK_SPEC"),
    (r"SBOM|Cyber|PSTI|TCG Opal|FIPS", lambda m: m["doc_type"] == "CYBERSECURITY_SBOM"),
    (r"SD Association|SD Express|CFA|Compliance Attestation", lambda m: m["doc_type"] == "TECHNICAL_COMPLIANCE_FILE"),
]
_GAP_RULES = [(re.compile(p, re.IGNORECASE), fn) for p, fn in GAP_COVERAGE_RULES]
CRA_REQUIREMENT = "EU Cyber Resilience Act technical documentation & SBOM (Regulation (EU) 2024/2847, conformity assessment from 2027-12-11)"


def _coverage_predicate(requirement: str):
    """Return (assessable: bool, predicate or None)."""
    for rx, fn in _GAP_RULES:
        if rx.search(requirement):
            return (fn is not None), fn
    return True, None


def gap_analysis(documents: List[Dict[str, Any]], products: List[Dict[str, Any]], max_rows: int = 250) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Product x target market coverage. A required document counts as covered when at least one readable
    scanned document (matched to that product, or not matched to any product) satisfies the requirement's
    keyword mapping (GAP_COVERAGE_RULES). Administrative/commercial paperwork is reported as not assessed."""
    readable = [d for d in documents if d["impact"]["impact_tier"] != "unreadable"]
    if not readable:
        return [], {"products": 0, "markets": 0, "required": 0, "covered": 0, "missing": 0, "not_assessed": 0, "coverage_pct": 0,
                    "scope": "no readable documents - nothing to compare against market requirements"}
    matched_ids = {d["metadata"].get("product_id") for d in readable if d["metadata"].get("product_id")}
    scope = [p for p in products if p.get("id") in matched_ids] or list(products)
    rows, summary = [], {"products": len(scope), "markets": 0, "required": 0, "covered": 0, "missing": 0, "not_assessed": 0, "scope": "matched products" if matched_ids else "entire portfolio (no product matched in the folder)"}
    for p in scope:
        docs_for_p = [d["metadata"] for d in readable if d["metadata"].get("product_id") in (p.get("id"), None)]
        for code in p.get("target_markets", []):
            code = code.upper()
            rule = db.get_country_product_requirement(code, p.get("category_id"))
            if not rule:
                continue
            reqs = list(rule.get("required_documents", []))
            if code in EU_COUNTRIES and p.get("category_id") in FIRMWARE_CATEGORIES:
                reqs.append(CRA_REQUIREMENT)
            covered, missing, na, evidence = [], [], [], {}
            for r in reqs:
                assessable, pred = _coverage_predicate(r)
                if not assessable:
                    na.append(r)
                    continue
                hit = None
                if pred is not None:
                    for m in docs_for_p:
                        try:
                            if pred(m):
                                hit = m["filename"]
                                break
                        except Exception:
                            continue
                if hit:
                    covered.append(r)
                    evidence[r] = hit
                else:
                    missing.append(r)
            summary["markets"] += 1
            summary["required"] += len(covered) + len(missing)
            summary["covered"] += len(covered)
            summary["missing"] += len(missing)
            summary["not_assessed"] += len(na)
            rows.append({
                "product_id": p.get("id"), "product_sku": p.get("sku"), "product_name": p.get("name"), "category_id": p.get("category_id"),
                "market_code": code, "market_name": rule.get("country_name", market_name(code)), "requirement_type": rule.get("requirement_type"),
                "badge": rule.get("badge"), "missing_documents": missing, "covered_documents": covered, "not_assessed": na, "evidence": evidence,
                "coverage_pct": int(round(100 * len(covered) / (len(covered) + len(missing)))) if (covered or missing) else 100,
            })
            if len(rows) >= max_rows:
                break
        if len(rows) >= max_rows:
            summary["truncated"] = True
            break
    summary["coverage_pct"] = int(round(100 * summary["covered"] / summary["required"])) if summary["required"] else 0
    rows.sort(key=lambda r: (r["coverage_pct"], r["product_name"], r["market_name"]))
    return rows, summary


def remediation_plan(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for idx, d in enumerate(documents):
        tier = d["impact"]["impact_tier"]
        if tier == "compliant":
            continue
        groups.setdefault(tier, []).append({
            "index": idx, "filename": d["metadata"]["filename"], "product_sku": d["metadata"].get("product_sku"), "product_name": d["metadata"].get("product_name"),
            "action_directive": d["impact"]["action_directive"], "severity": d["impact"]["severity"], "enforcement_deadline": d["impact"]["enforcement_deadline"],
            "days_to_deadline": d["impact"].get("days_to_deadline"), "cost_low": d["impact"].get("cost_low", 0), "cost_high": d["impact"].get("cost_high", 0),
            "effort_weeks": d["impact"].get("effort_weeks", 0), "trigger_alert_id": d["impact"].get("trigger_alert_id"),
        })
    order = ["retesting_required", "packaging_update", "doc_amendment", "portal_filing", "unreadable"]
    plan = []
    for tier in order:
        items = groups.get(tier)
        if not items:
            continue
        items.sort(key=lambda i: (SEVERITY_RANK.get(i["severity"], 0), -(i["days_to_deadline"] if i["days_to_deadline"] is not None else 9999)), reverse=True)
        plan.append({
            "tier": tier, "label": TIER_LABELS[tier], "count": len(items), "items": items,
            "cost_low": sum(i["cost_low"] for i in items), "cost_high": sum(i["cost_high"] for i in items),
            "effort_weeks": max((i["effort_weeks"] for i in items), default=0),
            "effort_weeks_serial": sum(i["effort_weeks"] for i in items),
            "owner_hint": {"retesting_required": "Compliance engineering + accredited lab", "packaging_update": "Packaging / artwork + printer", "doc_amendment": "Regulatory affairs (document owner / signatory)",
                           "portal_filing": "Regulatory affairs + local representative", "unreadable": "Document control"}[tier],
        })
    return plan


def standards_index(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for d in documents:
        for e in d["metadata"].get("standards_editions", []):
            s = e["standard"]
            row = idx.setdefault(s, {"standard": s, "count": 0, "editions": set(), "superseded_editions": set(), "documents": set(), "status": "current", "replacement": None, "pillar": (STANDARDS_CATALOG.get(s) or {}).get("pillar")})
            row["count"] += 1
            row["documents"].add(d["metadata"]["filename"])
            if e.get("edition_year"):
                row["editions"].add(e["edition_year"])
            st, repl = standard_status(s, e.get("edition_year"))
            if st == "superseded":
                row["status"], row["replacement"] = "superseded", repl
                if e.get("edition_year"):
                    row["superseded_editions"].add(e["edition_year"])
            elif st == "unknown" and row["status"] != "superseded":
                row["status"] = "unknown"
    out = []
    for row in idx.values():
        row["editions"] = sorted(row["editions"])
        row["superseded_editions"] = sorted(row["superseded_editions"])
        row["documents"] = sorted(row["documents"])
        out.append(row)
    out.sort(key=lambda r: ({"superseded": 0, "unknown": 1, "current": 2}[r["status"]], -r["count"], r["standard"]))
    return out


def _stem_key(filename: str) -> str:
    stem = os.path.splitext(filename)[0].lower()
    stem = re.sub(r"[\s_\-]*(?:\(\d+\)|copy|final|draft|v\d+|rev\s*[a-z0-9]+|signed|scan(?:ned)?)$", "", stem)
    return re.sub(r"[^a-z0-9]", "", stem)


def find_duplicates(documents: List[Dict[str, Any]]) -> List[List[str]]:
    pairs, seen = [], set()
    by_rep: Dict[str, List[str]] = {}
    by_stem: Dict[str, List[str]] = {}
    for d in documents:
        m = d["metadata"]
        rep = m.get("report_number")
        if rep and rep != "N/A" and len(rep) >= 6:
            by_rep.setdefault(rep.upper(), []).append(m["relative_path"])
        by_stem.setdefault(_stem_key(m["filename"]), []).append(m["relative_path"])
    for group in list(by_rep.values()) + list(by_stem.values()):
        if len(group) > 1:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    key = tuple(sorted((group[i], group[j])))
                    if key not in seen and key[0] != key[1]:
                        seen.add(key)
                        pairs.append(list(key))
    return pairs[:50]


def alerts_triggered(documents: List[Dict[str, Any]], alerts) -> List[Dict[str, Any]]:
    counts: Dict[str, Dict[str, Any]] = {}
    for d in documents:
        ids = set()
        for f in d["impact"].get("findings", []):
            if f.get("trigger_alert_id"):
                ids.add((f["trigger_alert_id"], f.get("trigger_alert_title")))
        if d["impact"].get("trigger_alert_id"):
            ids.add((d["impact"]["trigger_alert_id"], d["impact"].get("trigger_alert_title")))
        for aid, title in ids:
            row = counts.setdefault(aid, {"alert_id": aid, "title": title, "count": 0, "severity": None, "effective_date": None})
            row["count"] += 1
    for aid, row in counts.items():
        a = _alert_by_id(alerts, aid)
        if a:
            row["title"] = a.get("title") or row["title"]
            row["severity"] = a.get("severity")
            row["effective_date"] = a.get("effective_date")
    return sorted(counts.values(), key=lambda r: -r["count"])


def _sort_documents(documents):
    documents.sort(key=lambda d: (TIER_RANK.get(d["impact"]["impact_tier"], 0) if d["impact"]["impact_tier"] != "unreadable" else -1,
                                  SEVERITY_RANK.get(d["impact"]["severity"], 0), -(d["impact"].get("days_to_deadline") if d["impact"].get("days_to_deadline") is not None else 99999)), reverse=True)


def _process_file(full_path: str, rel_path: str, alerts, products) -> Dict[str, Any]:
    try:
        size_kb = round(os.path.getsize(full_path) / 1024, 1)
    except OSError:
        size_kb = 0
    text, err = extract_text(full_path)
    try:
        meta = extract_metadata(text if not err else "", os.path.basename(full_path), products)
    except Exception as e:  # never let one bad file kill the scan
        meta = extract_metadata("", os.path.basename(full_path), products)
        err = err or f"metadata extraction failed: {type(e).__name__}: {e}"
    meta["relative_path"] = rel_path.replace("\\", "/")
    meta["file_size_kb"] = size_kb
    meta["extension"] = os.path.splitext(full_path)[1].lower()
    meta["unreadable_reason"] = err
    try:
        impact = evaluate_document_impact(meta, text, alerts=alerts, products=products, unreadable_reason=err)
    except Exception as e:
        impact = evaluate_document_impact(meta, "", alerts=alerts, products=products, unreadable_reason=f"impact evaluation failed: {type(e).__name__}: {e}")
    return {"metadata": meta, "impact": impact}


def build_report(documents: List[Dict[str, Any]], folder_path: str, alerts, products, stats: Dict[str, Any]) -> Dict[str, Any]:
    _sort_documents(documents)
    tier_summary = {t: 0 for t in TIERS}
    for d in documents:
        tier_summary[d["impact"]["impact_tier"]] = tier_summary.get(d["impact"]["impact_tier"], 0) + 1
    score, grade = health_score(documents)
    plan = remediation_plan(documents)
    gaps, gap_summary = gap_analysis(documents, products or [])
    expired = sum(1 for d in documents if (d["metadata"].get("days_to_expiry") is not None and d["metadata"]["days_to_expiry"] < 0))
    expiring = sum(1 for d in documents if (d["metadata"].get("days_to_expiry") is not None and 0 <= d["metadata"]["days_to_expiry"] <= 90))
    return {
        "folder_path": folder_path,
        "scan_timestamp": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine_version": ENGINE_VERSION,
        "total_documents": len(documents),
        "impacted_documents": sum(1 for d in documents if d["impact"]["is_impacted"]),
        "health_score": score, "health_grade": grade,
        "health_formula": "100 x (1 - sum(min(25, tier penalty + 15 if expired)) / (25 x documents)); retest 25, packaging 12, doc amendment 8, portal 6, unreadable 3",
        "tier_summary": tier_summary,
        "expired_documents": expired, "expiring_90d_documents": expiring,
        "documents": documents,
        "gap_analysis": gaps, "gap_summary": gap_summary,
        "remediation_plan": plan,
        "cost_rollup": {"low": sum(g["cost_low"] for g in plan), "high": sum(g["cost_high"] for g in plan), "currency": "USD",
                        "basis": "Indicative third-party lab / agency fee ranges for the listed actions; excludes internal engineering time, samples and shipping. Not a quotation."},
        "standards_index": standards_index(documents),
        "duplicates": find_duplicates(documents),
        "alerts_triggered": alerts_triggered(documents, alerts),
        "scan_stats": stats,
    }


def _iter_files(folder_path: str, recursive: bool):
    if recursive:
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in ("__pycache__", "node_modules", "$recycle.bin", "system volume information")]
            for f in sorted(files):
                yield os.path.join(root, f)
    else:
        try:
            for f in sorted(os.listdir(folder_path)):
                p = os.path.join(folder_path, f)
                if os.path.isfile(p):
                    yield p
        except OSError:
            return


def scan_directory(folder_path: str, recursive: bool = True, alerts=None, products=None) -> Dict[str, Any]:
    """Scan a local folder. Never raises for individual bad files; returns {"error": ...} only if the folder is invalid."""
    started = time.time()
    if not folder_path or not os.path.isdir(folder_path):
        return {"error": f"Folder '{folder_path}' does not exist or is not a directory.", "total_documents": 0, "impacted_documents": 0, "documents": []}
    if products is None:
        products = list(getattr(db, "SAMPLE_PRODUCTS", []))
    alerts = alerts or list(getattr(db, "REGULATION_ALERTS", []))
    files_seen, supported, unreadable, skipped_large = 0, 0, 0, 0
    docs = []
    for full in _iter_files(folder_path, recursive):
        files_seen += 1
        ext = os.path.splitext(full)[1].lower()
        if ext not in SUPPORTED_EXTS or os.path.basename(full).startswith("~$"):
            continue
        supported += 1
        try:
            if os.path.getsize(full) > MAX_FILE_BYTES:
                skipped_large += 1
        except OSError:
            pass
        rec = _process_file(full, os.path.relpath(full, folder_path), alerts, products)
        rec["metadata"]["file_path"] = full
        if rec["impact"]["impact_tier"] == "unreadable":
            unreadable += 1
        docs.append(rec)
        if len(docs) >= 2000:
            break
    stats = {"files_seen": files_seen, "files_supported": supported, "files_unreadable": unreadable, "files_over_limit": skipped_large,
             "files_skipped_unsupported": files_seen - supported, "duration_s": round(time.time() - started, 2), "recursive": bool(recursive),
             "alerts_in_rulebook": len(alerts), "products_in_portfolio": len(products)}
    return build_report(docs, folder_path, alerts, products, stats)


def scan_files(paths: List[str], alerts=None, products=None, display_root: Optional[str] = None, folder_label: Optional[str] = None) -> Dict[str, Any]:
    """Scan an explicit list of files (used by browser upload). relative_path is computed from display_root."""
    started = time.time()
    if products is None:
        products = list(getattr(db, "SAMPLE_PRODUCTS", []))
    alerts = alerts or list(getattr(db, "REGULATION_ALERTS", []))
    docs, supported, unreadable = [], 0, 0
    for full in paths:
        if not os.path.isfile(full):
            continue
        ext = os.path.splitext(full)[1].lower()
        if ext not in SUPPORTED_EXTS:
            continue
        supported += 1
        rel = os.path.relpath(full, display_root) if display_root else os.path.basename(full)
        rec = _process_file(full, rel, alerts, products)
        if rec["impact"]["impact_tier"] == "unreadable":
            unreadable += 1
        docs.append(rec)
    stats = {"files_seen": len(paths), "files_supported": supported, "files_unreadable": unreadable, "files_over_limit": 0,
             "files_skipped_unsupported": len(paths) - supported, "duration_s": round(time.time() - started, 2), "recursive": True,
             "alerts_in_rulebook": len(alerts), "products_in_portfolio": len(products)}
    return build_report(docs, folder_label or f"Browser upload ({supported} files)", alerts, products, stats)


# =============================================================================
# 5. PLAIN-LANGUAGE EXPLANATION
# =============================================================================
MINI_GLOSSARY = {
    "CB Scheme": "The IECEE CB Scheme: one safety test report (TRF) and certificate accepted by 50+ countries' certification bodies, so you do not re-test in each country.",
    "DoC": "Declaration of Conformity - the manufacturer's signed statement listing the directives and standards a product meets. The EU and UK versions are legal documents.",
    "SDoC": "Supplier's Declaration of Conformity - the FCC's self-declaration route for unintentional radiators; needs a US-based responsible party.",
    "Harmonised standard": "A European standard listed in the Official Journal; citing it gives 'presumption of conformity' with the directive.",
    "Edition": "Standards are re-issued as numbered editions (e.g. IEC 62368-1 Ed. 4 = 2023). Certifiers stop accepting old editions after a transition period.",
    "RoHS": "EU Directive 2011/65/EU restricting lead, cadmium, mercury, chromium VI, PBB/PBDE and four phthalates in electronics.",
    "REACH": "EU chemicals regulation (EC) 1907/2006 - substances of very high concern (SVHC) above 0.1% must be communicated.",
    "PFAS": "'Forever chemicals' (per- and polyfluoroalkyl substances). US TSCA and several states require reporting or ban them in articles.",
    "FMD": "Full Material Disclosure - a per-part list of every substance in a product, used to prove RoHS / REACH / PFAS status.",
    "Triman": "France's mandatory sorting logo (with Info-tri instructions) on consumer packaging under the AGEC law.",
    "PPWR": "EU Packaging & Packaging Waste Regulation (EU) 2025/40 - harmonised labels, recycled-content and heavy-metal rules from August 2026.",
    "CRA": "EU Cyber Resilience Act (Regulation (EU) 2024/2847) - cybersecurity and vulnerability-handling duties for products with firmware.",
    "SBOM": "Software Bill of Materials - a machine-readable inventory of firmware components (CycloneDX / SPDX).",
    "BIS CRS": "India's Compulsory Registration Scheme run by the Bureau of Indian Standards; registration numbers (R-xxxxxxxx) must appear on the product.",
    "KC": "Korea Certification mark - safety (KATS) and EMC (RRA) approvals required before customs clearance.",
    "BSMI": "Taiwan's Bureau of Standards, Metrology and Inspection - product registration and the commodity inspection mark.",
    "CCC": "China Compulsory Certification - mandatory for mains-powered adapters; needs testing at a CNCA-designated lab.",
    "PSE": "Japan's electrical safety mark under the DENAN law (diamond PSE for adapters).",
    "SABER": "Saudi Arabia's online conformity platform: a product certificate (PCoC) plus a per-shipment certificate (SCoC).",
    "NRTL": "Nationally Recognized Testing Laboratory (e.g. UL, CSA, Intertek) accepted by OSHA for US safety listings.",
    "CISPR 32": "The international EMC emissions standard for multimedia equipment (replaced CISPR 22 / EN 55022).",
    "Responsible party": "Under FCC rules, the US-located entity that stands behind an SDoC and can be contacted by the FCC.",
    "EPR": "Extended Producer Responsibility - the producer funds take-back and recycling (e.g. WEEE, India CPCB portal).",
}


def _glossary_for(text_blob: str) -> List[Dict[str, str]]:
    t = text_blob.lower()
    out = []
    for term, meaning in MINI_GLOSSARY.items():
        key = term.lower().replace("bis crs", "bis")
        if key in t or (term == "Edition" and "edition" in t) or (term == "Harmonised standard" and "harmoni" in t):
            out.append({"term": term, "meaning": meaning})
    return out[:8]


def _soft_lower(label: str) -> str:
    """Lower-case a label but keep acronyms: 'CB Test Certificate' -> 'CB test certificate'."""
    return " ".join(w if (w.isupper() and len(w) > 1) or any(ch.isupper() for ch in w[1:]) else w.lower() for w in label.split())


def explain_document(doc_record: Dict[str, Any], alerts=None) -> Dict[str, Any]:
    """Short plain-language explanation of one document's situation."""
    m = doc_record.get("metadata", {})
    imp = doc_record.get("impact", {})
    tier = imp.get("impact_tier", "compliant")
    label = _soft_lower(DOC_TYPE_LABELS.get(m.get("doc_type"), "document"))
    product = m.get("product_name") if m.get("product_id") else "a product that could not be matched to your portfolio"
    findings = imp.get("findings", [])
    alert = _alert_by_id(alerts, imp.get("trigger_alert_id")) if alerts else None
    glossary_src = " ".join([label, " ".join(m.get("standards_detected", [])), imp.get("action_directive", ""), " ".join(imp.get("rationale", []))])
    try:  # reuse the alerts module glossary if the platform ships it
        import alert_explainer  # type: ignore
        extra = getattr(alert_explainer, "GLOSSARY", None) or getattr(alert_explainer, "JARGON_GLOSSARY", None)
        if isinstance(extra, dict):
            for k, v in extra.items():
                MINI_GLOSSARY.setdefault(k, v if isinstance(v, str) else str(v))
    except Exception:
        pass

    if tier == "unreadable":
        return {"headline": f"We could not read {m.get('filename')}.", "plain_english": f"The scanner opened the file but found no text ({m.get('unreadable_reason')}). Until it can be read, nobody can tell which standards or products it covers.",
                "why": ["Scanned-image PDFs contain pictures of pages, not text.", "Corrupt downloads or legacy .doc/.xls binaries cannot be parsed."],
                "next_steps": ["Open the file manually and check it is intact.", "Re-export it as a text-based PDF (or run OCR) and drop it back into the folder.", "Re-run the scan."],
                "glossary": [], "tier": tier}
    if tier == "compliant":
        return {"headline": f"{m.get('filename')} is in good standing.",
                "plain_english": f"This {label} for {product} cites current standards ({', '.join(m.get('standards_detected', [])[:4]) or 'none dated'}) and no active regulation alert requires a change to it.",
                "why": imp.get("rationale", []),
                "next_steps": ["Keep it in the technical file.", f"Re-check after the next alert scan; expiry {m.get('expiry_date')}{' (inferred)' if m.get('expiry_inferred') else ''}." if m.get("expiry_date") else "Re-check after the next alert scan."],
                "glossary": _glossary_for(glossary_src), "tier": tier}

    tier_plain = {
        "retesting_required": "the product has to go back to a laboratory, because the report or certificate is based on a standard edition that certifiers no longer accept",
        "doc_amendment": "the paperwork itself must be corrected and re-signed - no lab work is needed for this document alone",
        "packaging_update": "the retail packaging artwork must be changed and re-printed",
        "portal_filing": "a filing or renewal must be made with a government scheme or its online portal",
    }.get(tier, "action is needed")
    why = list(imp.get("rationale", []))
    if len(findings) > 1:
        why.append(f"There are {len(findings)} separate findings on this file; the most serious one sets the action above. Others: " + "; ".join(f["action_directive"].split(".")[0] for f in findings[1:3]) + ".")
    steps = [imp.get("action_directive", "").split(" (+")[0]]
    if imp.get("cost_high"):
        steps.append(f"Budget roughly ${imp.get('cost_low', 0):,}-${imp.get('cost_high', 0):,} and {imp.get('estimated_effort')} (indicative, external fees only).")
    if imp.get("enforcement_deadline") and imp.get("enforcement_deadline") not in ("Ongoing", "n/a"):
        d = imp.get("days_to_deadline")
        steps.append(f"Deadline {imp['enforcement_deadline']}" + (f" - {'overdue by ' + str(-d) + ' days' if d is not None and d < 0 else str(d) + ' days left'}." if d is not None else "."))
    if alert:
        steps.append(f"Read alert {alert['id']} ('{alert['title']}') for the full regulatory context and checklist.")
    steps.append("Create an action item so the work is tracked to an owner and due date.")
    return {
        "headline": f"{m.get('filename')}: {TIER_LABELS.get(tier, tier)}.",
        "plain_english": f"This is a {label} for {product}. In plain terms, {tier_plain}. " + (f"The trigger is the cited '{imp.get('obsolete_standard_cited')}', which should now read '{imp.get('required_standard')}'." if imp.get("obsolete_standard_cited") and imp.get("required_standard") else (f"What is missing or expired: {imp.get('required_standard')}." if imp.get("required_standard") else "")),
        "why": why[:5], "next_steps": steps[:5], "glossary": _glossary_for(glossary_src), "tier": tier, "severity": imp.get("severity"),
    }



# =============================================================================
# 6. EXCEL EXPORT - same visual language as excel_export.py
# =============================================================================
_NAVY = "0F172A"
_HEADER = "1E293B"
_SUB = "F8FAFC"
_TIER_FILL = {
    "retesting_required": ("FEE2E2", "991B1B"), "packaging_update": ("EDE9FE", "5B21B6"), "doc_amendment": ("FEF3C7", "92400E"),
    "portal_filing": ("DBEAFE", "1E40AF"), "compliant": ("D1FAE5", "065F46"), "unreadable": ("E2E8F0", "334155"),
}
_STATUS_FILL = {"superseded": ("FEE2E2", "991B1B"), "current": ("D1FAE5", "065F46"), "unknown": ("E2E8F0", "334155")}


def _xl_styles():
    thin = Side(border_style="thin", color="CBD5E1")
    return {
        "navy": PatternFill(start_color=_NAVY, end_color=_NAVY, fill_type="solid"),
        "header": PatternFill(start_color=_HEADER, end_color=_HEADER, fill_type="solid"),
        "sub": PatternFill(start_color=_SUB, end_color=_SUB, fill_type="solid"),
        "title_font": Font(name="Calibri", size=13, bold=True, color="FFFFFF"),
        "sub_font": Font(name="Calibri", size=10, italic=True, color="334155"),
        "hdr_font": Font(name="Calibri", size=10, bold=True, color="FFFFFF"),
        "body": Font(name="Calibri", size=9), "body_bold": Font(name="Calibri", size=10, bold=True), "mono": Font(name="Consolas", size=9),
        "border": Border(left=thin, right=thin, top=thin, bottom=thin),
        "hdr_border": Border(left=thin, right=thin, top=thin, bottom=Side(border_style="medium", color=_NAVY)),
        "wrap": Alignment(horizontal="left", vertical="top", wrap_text=True),
        "center": Alignment(horizontal="center", vertical="center", wrap_text=True),
        "left": Alignment(horizontal="left", vertical="center"),
    }


def _banner(ws, st, title, subtitle, ncols):
    last = get_column_letter(ncols)
    ws.merge_cells(f"A1:{last}1")
    c = ws["A1"]
    c.value, c.font, c.fill = title, st["title_font"], st["navy"]
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 34
    ws.merge_cells(f"A2:{last}2")
    c = ws["A2"]
    c.value, c.font, c.fill = subtitle, st["sub_font"], st["sub"]
    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 20
    ws.row_dimensions[3].height = 6


def _header_row(ws, st, row, headers, center_cols=()):
    ws.row_dimensions[row].height = 30
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=i, value=h)
        c.font, c.fill, c.border = st["hdr_font"], st["header"], st["hdr_border"]
        c.alignment = Alignment(horizontal="center" if i in center_cols else "left", vertical="center", wrap_text=True)


def _tier_cell(c, tier, st):
    fill, color = _TIER_FILL.get(tier, _TIER_FILL["unreadable"])
    c.fill = PatternFill(start_color=fill, end_color=fill, fill_type="solid")
    c.font = Font(name="Calibri", size=9, bold=True, color=color)
    c.alignment = st["center"]
    c.border = st["border"]


def _widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def export_audit_to_excel(report: Dict[str, Any]) -> io.BytesIO:
    """4-sheet Document Revision Directive workbook."""
    out = io.BytesIO()
    if not HAS_OPENPYXL:
        return out
    st = _xl_styles()
    wb = openpyxl.Workbook()
    ts = report.get("scan_timestamp", "")
    scope = f"Folder: {report.get('folder_path', 'n/a')}   |   Scanned: {ts}   |   Engine v{report.get('engine_version', ENGINE_VERSION)}"

    # ---- Sheet 1: Executive Summary
    ws = wb.active
    ws.title = "Executive Summary"
    _banner(ws, st, "GLOBAL COMPLIANCE MANAGEMENT (GCM) - DOCUMENT IMPACT AUDIT: EXECUTIVE SUMMARY", scope, 4)
    r = 4
    kpis = [
        ("Documents scanned", report.get("total_documents", 0)), ("Documents impacted", report.get("impacted_documents", 0)),
        ("Health score (0-100)", report.get("health_score", 0)), ("Health grade", report.get("health_grade", "")),
        ("Expired certificates / registrations", report.get("expired_documents", 0)), ("Expiring within 90 days", report.get("expiring_90d_documents", 0)),
        ("Indicative remediation cost (USD, low)", report.get("cost_rollup", {}).get("low", 0)), ("Indicative remediation cost (USD, high)", report.get("cost_rollup", {}).get("high", 0)),
        ("Files seen / supported / unreadable", f"{report.get('scan_stats', {}).get('files_seen', 0)} / {report.get('scan_stats', {}).get('files_supported', 0)} / {report.get('scan_stats', {}).get('files_unreadable', 0)}"),
    ]
    _header_row(ws, st, r, ["Key figure", "Value", "", ""])
    for label, val in kpis:
        r += 1
        a = ws.cell(row=r, column=1, value=label); a.font, a.border, a.alignment = st["body_bold"], st["border"], st["left"]
        b = ws.cell(row=r, column=2, value=val); b.font, b.border, b.alignment = st["body"], st["border"], st["left"]
        if isinstance(val, int) and "cost" in label.lower():
            b.number_format = '"$"#,##0'
    r += 2
    _header_row(ws, st, r, ["Impact tier", "Documents", "Cost low (USD)", "Cost high (USD)"], center_cols=(2, 3, 4))
    plan_by = {g["tier"]: g for g in report.get("remediation_plan", [])}
    for tier in TIERS:
        r += 1
        g = plan_by.get(tier, {})
        c = ws.cell(row=r, column=1, value=TIER_LABELS[tier]); _tier_cell(c, tier, st); c.alignment = st["left"]
        for col, val in ((2, report.get("tier_summary", {}).get(tier, 0)), (3, g.get("cost_low", 0)), (4, g.get("cost_high", 0))):
            cc = ws.cell(row=r, column=col, value=val); cc.font, cc.border, cc.alignment = st["body"], st["border"], st["center"]
            if col > 2:
                cc.number_format = '"$"#,##0'
    r += 2
    _header_row(ws, st, r, ["Alert triggered", "Documents", "Severity", "Effective date"], center_cols=(2, 3, 4))
    for a in report.get("alerts_triggered", []):
        r += 1
        for col, val in ((1, f"{a.get('alert_id')} - {a.get('title')}"), (2, a.get("count")), (3, a.get("severity") or ""), (4, a.get("effective_date") or "")):
            cc = ws.cell(row=r, column=col, value=val); cc.font, cc.border = st["body"], st["border"]
            cc.alignment = st["wrap"] if col == 1 else st["center"]
    r += 2
    note = ws.cell(row=r, column=1, value=f"Health formula: {report.get('health_formula', '')}.  Cost basis: {report.get('cost_rollup', {}).get('basis', '')}")
    note.font = Font(name="Calibri", size=9, italic=True, color="475569"); note.alignment = st["wrap"]
    ws.merge_cells(start_row=r, start_column=1, end_row=r + 1, end_column=4)
    ws.row_dimensions[r].height = 30
    _widths(ws, [58, 22, 20, 20])

    # ---- Sheet 2: Revision Directive
    ws = wb.create_sheet("Revision Directive")
    headers = ["#", "File", "Folder path", "Document type", "Product / SKU", "Issuing lab", "Report no.", "Standards cited", "Markets", "Issue date", "Expiry", "Days to expiry",
               "Impact tier", "Severity", "Trigger alert", "Obsolete standard cited", "Required standard", "Deadline", "Action directive", "Rationale", "Effort", "Cost low (USD)", "Cost high (USD)", "Confidence"]
    _banner(ws, st, "DOCUMENT REVISION DIRECTIVE - ONE ROW PER DOCUMENT (sorted by urgency)", scope, len(headers))
    _header_row(ws, st, 4, headers, center_cols=(1, 12, 13, 14, 21, 22, 23, 24))
    row = 5
    for i, d in enumerate(report.get("documents", []), 1):
        m, imp = d["metadata"], d["impact"]
        vals = [i, m.get("filename"), m.get("relative_path"), DOC_TYPE_LABELS.get(m.get("doc_type"), m.get("doc_type")), f"{m.get('product_name')} ({m.get('product_sku')})",
                m.get("issuing_lab"), m.get("report_number"), "; ".join(e.get("raw") or e["standard"] for e in m.get("standards_editions", [])) or "-",
                ", ".join(m.get("markets_detected", [])) or "-", m.get("issue_date") or "-", (m.get("expiry_date") or "-") + (" (inferred)" if m.get("expiry_inferred") else ""),
                m.get("days_to_expiry") if m.get("days_to_expiry") is not None else "-", TIER_LABELS.get(imp.get("impact_tier"), imp.get("impact_tier")), imp.get("severity"),
                imp.get("trigger_alert_id") or "-", imp.get("obsolete_standard_cited") or "-", imp.get("required_standard") or "-", imp.get("enforcement_deadline"),
                imp.get("action_directive"), "\n".join(f"- {x}" for x in imp.get("rationale", [])), imp.get("estimated_effort"), imp.get("cost_low", 0), imp.get("cost_high", 0), imp.get("confidence", "")]
        for col, val in enumerate(vals, 1):
            c = ws.cell(row=row, column=col, value=val)
            c.border = st["border"]
            if col == 13:
                _tier_cell(c, imp.get("impact_tier"), st)
            elif col in (1, 12, 14, 21, 24):
                c.font, c.alignment = st["body"], st["center"]
            elif col in (7, 15):
                c.font, c.alignment = st["mono"], st["left"]
            elif col in (22, 23):
                c.font, c.alignment, c.number_format = st["body"], st["center"], '"$"#,##0'
            else:
                c.font, c.alignment = st["body"], st["wrap"]
        ws.row_dimensions[row].height = 72
        row += 1
    ws.freeze_panes = "C5"
    if row > 5:
        ws.auto_filter.ref = f"A4:{get_column_letter(len(headers))}{row - 1}"
    _widths(ws, [5, 34, 30, 22, 30, 18, 20, 34, 14, 12, 14, 9, 22, 10, 16, 28, 30, 13, 56, 60, 12, 12, 12, 11])

    # ---- Sheet 3: Gap Analysis
    ws = wb.create_sheet("Gap Analysis")
    headers = ["Product", "SKU", "Market", "ISO", "Requirement type", "Coverage %", "Missing documents", "Covered documents (evidence file)", "Not assessed by scanner"]
    gs = report.get("gap_summary", {})
    _banner(ws, st, "GAP ANALYSIS - REQUIRED DOCUMENTS PER PRODUCT x TARGET MARKET vs. DOCUMENTS FOUND",
            f"{scope}   |   Scope: {gs.get('scope', '')}   |   {gs.get('covered', 0)} covered / {gs.get('missing', 0)} missing / {gs.get('not_assessed', 0)} not assessable", len(headers))
    _header_row(ws, st, 4, headers, center_cols=(4, 6))
    row = 5
    for g in report.get("gap_analysis", []):
        ev = g.get("evidence", {})
        vals = [g.get("product_name"), g.get("product_sku"), g.get("market_name"), g.get("market_code"), g.get("requirement_type"), g.get("coverage_pct"),
                "\n".join(f"- {x}" for x in g.get("missing_documents", [])) or "-",
                "\n".join(f"- {x}  [{ev.get(x, '')}]" for x in g.get("covered_documents", [])) or "-",
                "\n".join(f"- {x}" for x in g.get("not_assessed", [])) or "-"]
        for col, val in enumerate(vals, 1):
            c = ws.cell(row=row, column=col, value=val)
            c.border = st["border"]
            if col == 6:
                pct = int(val or 0)
                fill, color = ("D1FAE5", "065F46") if pct >= 80 else ("FEF3C7", "92400E") if pct >= 40 else ("FEE2E2", "991B1B")
                c.fill = PatternFill(start_color=fill, end_color=fill, fill_type="solid"); c.font = Font(name="Calibri", size=9, bold=True, color=color); c.alignment = st["center"]
            elif col == 4:
                c.font, c.alignment = st["mono"], st["center"]
            else:
                c.font, c.alignment = st["body"], st["wrap"]
        ws.row_dimensions[row].height = max(30, 14 * max(1, len(g.get("missing_documents", [])), len(g.get("covered_documents", [])), len(g.get("not_assessed", []))))
        row += 1
    ws.freeze_panes = "A5"
    if row > 5:
        ws.auto_filter.ref = f"A4:{get_column_letter(len(headers))}{row - 1}"
    _widths(ws, [36, 20, 18, 6, 30, 11, 60, 60, 44])

    # ---- Sheet 4: Standards Index
    ws = wb.create_sheet("Standards Index")
    headers = ["Standard", "Pillar", "Citations", "Editions seen", "Status", "Replacement / current reference", "Documents"]
    _banner(ws, st, "STANDARDS INDEX - EVERY STANDARD CITED ACROSS THE FOLDER", scope, len(headers))
    _header_row(ws, st, 4, headers, center_cols=(3, 5))
    row = 5
    for s in report.get("standards_index", []):
        vals = [s["standard"], s.get("pillar") or "-", s["count"], ", ".join(str(y) for y in s.get("editions", [])) or "-", s["status"].title(), s.get("replacement") or "-", "\n".join(s.get("documents", []))]
        for col, val in enumerate(vals, 1):
            c = ws.cell(row=row, column=col, value=val)
            c.border = st["border"]
            if col == 5:
                fill, color = _STATUS_FILL.get(s["status"], _STATUS_FILL["unknown"])
                c.fill = PatternFill(start_color=fill, end_color=fill, fill_type="solid"); c.font = Font(name="Calibri", size=9, bold=True, color=color); c.alignment = st["center"]
            elif col == 3:
                c.font, c.alignment = st["body"], st["center"]
            else:
                c.font, c.alignment = st["body"], st["wrap"]
        ws.row_dimensions[row].height = max(18, 13 * len(s.get("documents", [])))
        row += 1
    ws.freeze_panes = "A5"
    if row > 5:
        ws.auto_filter.ref = f"A4:{get_column_letter(len(headers))}{row - 1}"
    _widths(ws, [40, 14, 10, 16, 12, 48, 50])

    wb.save(out)
    out.seek(0)
    return out


# =============================================================================
# 7. GENERIC EXAMPLE DOCUMENTS
# =============================================================================
def make_multiline_pdf(lines: list) -> bytes:
    """Synthesize a valid single-page, uncompressed PDF with a Helvetica text stream."""
    cmds = ["BT /F1 10 Tf 14 TL 50 740 Td"]
    for line in lines:
        esc = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        cmds.append(f"({esc}) '")
    cmds.append("ET")
    stream = "\n".join(cmds).encode("latin-1", "replace")
    obj4 = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream)
    parts, offsets = [b"%PDF-1.4\n"], []
    for body in (b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
                 b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
                 b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
                 b"4 0 obj\n" + obj4 + b"\nendobj\n",
                 b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"):
        offsets.append(len(b"".join(parts)))
        parts.append(body)
    xref = len(b"".join(parts))
    parts.append(b"xref\n0 6\n0000000000 65535 f \n")
    for off in offsets:
        parts.append(f"{off:010d} 00000 n \n".encode("ascii"))
    parts.append(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return b"".join(parts)


def generate_sample_compliance_docs(target_dir=None) -> List[str]:
    """Create 10 GENERIC example files exercising every impact tier. Returns the list of paths written.

    All names, model numbers, report numbers and laboratories are fictitious placeholders
    ("Example Manufacturer Ltd.", "EXAMPLE-RPT-0001", "Accredited Test Laboratory (example)") that match
    the generic example products in compliance_db.SAMPLE_PRODUCTS. They do not describe any real product.
    """
    target_dir = target_dir or os.path.join(os.path.expanduser("~"), "GCM_Example_Documents")
    os.makedirs(target_dir, exist_ok=True)
    created = []
    MFR = "Example Manufacturer Ltd."
    LAB = "Accredited Test Laboratory (example)"
    NCB = "Accredited certification body (example)"

    def pdf(name, lines):
        p = os.path.join(target_dir, name)
        with open(p, "wb") as f:
            f.write(make_multiline_pdf(lines))
        created.append(p)

    # 1. Obsolete CB report (Ed. 2) -> retesting_required
    pdf("CB_Report_EXAMPLE-RPT-0001_Portable_SSD.pdf", [
        f"{LAB} - CB Scheme Test Certificate & Report", "Report Number: EXAMPLE-RPT-0001", f"Applicant: {MFR}",
        "Product: Example product - portable SSD (bus-powered) Model EXAMPLE-PSSD-01", "Harmonized Technical Standard: IEC 62368-1:2014 (Second Edition)",
        f"Issuing Body: {LAB}", "Ratings: 5V DC, 2.5A SELV (Class III)", "Issue Date: 2019-08-14", "Status: Test report evaluated under legacy Edition 2.0."])
    # 2. EU DoC citing EN 62368-1:2014 -> doc_amendment
    pdf("EU_Declaration_of_Conformity_Desktop_Drive.pdf", [
        "EU DECLARATION OF CONFORMITY (DoC Ref: EXAMPLE-DOC-0002)", f"Manufacturer: {MFR}",
        "Product Name: Example product - desktop storage drive (mains-powered)", "Model / SKU: EXAMPLE-DSSD-01",
        "Low Voltage Directive 2014/35/EU: Harmonized Standard EN 62368-1:2014+A11:2017", "EMC Directive 2014/30/EU: Harmonized Standard EN 55032:2015 Class B",
        "RoHS Directive 2011/65/EU on the restriction of hazardous substances", f"Authorized Signatory: Regulatory Compliance Director, {MFR}", "Date of Issue: 2022-03-10"])
    # 3. Modern EMC report -> compliant
    pdf("EMC_Test_Report_EXAMPLE-RPT-0003_Internal_SSD.pdf", [
        f"{LAB} Test Report Ref: EXAMPLE-RPT-0003", f"Client: {MFR}", "Product: Example product - internal SSD (M.2 NVMe)", "Model / SKU: EXAMPLE-SSD-01",
        "Tested Standards:", "- CISPR 32:2015+A1:2019 Class B (Radio Disturbance Characteristics)", "- FCC Part 15B Class B Unintentional Radiators", "- EN 55032:2015+A11:2020",
        f"Laboratory: {LAB}", "Date of Test: 2024-02-18", "Result: PASS - Fully Compliant with Modern Emissions Limits."])
    # 4. Packaging spec missing Triman / Italy coding / PPWR -> packaging_update
    p4 = os.path.join(target_dir, "Packaging_Artwork_Spec_SD_Card.docx")
    if HAS_DOCX:
        d = docx.Document()
        d.add_heading("Retail Packaging Master Specification (example)", 0)
        for t in ["Product Family: Example product - SD card (UHS-II)", "Master SKU: EXAMPLE-SD-01", "Markets: European Union (France, Italy, Germany), United Kingdom",
                  "Packaging Substrate: SBS Bleached Sulfate Paperboard (Inner Blister: Thermoformed PET)", "Regulatory Marking Requirements on Exterior Carton:",
                  "- CE Mark minimum height: 5.0 mm", "- UKCA Mark minimum height: 5.0 mm", "- WEEE Crossed-Out Wheelie Bin Symbol (Directive 2012/19/EU)",
                  "- Standard Mobius Loop generic recycling symbol", "Artwork revision: Rev C, 2023-05-02"]:
            d.add_paragraph(t)
        d.save(p4)
        created.append(p4)
    # 5. BIS CRS grant citing IS 13252, granted 2021 (expired by inference) -> portal_filing
    pdf("BIS_CRS_Registration_Grant_Desktop_Drive_India.pdf", [
        "BUREAU OF INDIAN STANDARDS (Central Marks Department)", "Registration Grant Letter Ref: EXAMPLE-REG-0005", "Registration No: R-00000005",
        f"Manufacturer: {MFR}", "Standard: IS 13252 (Part 1):2010 Safety of Information Technology Equipment",
        "Product: External Storage Drive (Mains-Powered)", "Brand: Example Manufacturer, Model EXAMPLE-DSSD-01", "Date of Grant: 2021-11-20",
        "Renewal Status: Requires renewal under the Compulsory Registration Scheme."])
    # 6. FMD spreadsheet with PFAS not evaluated -> doc_amendment
    p6 = os.path.join(target_dir, "Full_Material_Disclosure_FMD_Gaming_Card.xlsx")
    if HAS_OPENPYXL:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BOM Substance Disclosure"
        ws.append(["Full Material Disclosure - Example product - gaming storage expansion card - SKU EXAMPLE-GXC-01 - Markets: United States, European Union"])
        ws.append(["Component Name", "Part Number", "Supplier", "Material Classification", "RoHS Compliance", "REACH SVHC Status", "TSCA PFAS Disclosure"])
        for row in [["NAND Flash Package", "EX-NAND-128G", "NAND supplier (example)", "Epoxy Molding Compound", "RoHS Compliant", "No SVHC >0.1%", "Not Evaluated"],
                    ["NVMe Controller ASIC", "EX-CTRL-01", "Controller supplier (example)", "Semiconductor Silicon", "RoHS Compliant", "No SVHC >0.1%", "Not Evaluated"],
                    ["FR-4 Printed Circuit Board", "EX-PCB-REV3", "PCB supplier (example)", "Copper Clad Laminate / Glass Fiber", "RoHS Compliant", "TBBP-A Present in Resin", "Not Evaluated"],
                    ["Thermal Gap Pad", "EX-TIM-05", "Thermal materials supplier (example)", "Silicone Polymer", "RoHS Compliant", "No SVHC", "Potential Fluoropolymer Content"],
                    ["Aluminum Enclosure Heatsink", "EX-ENC-AL", "Enclosure supplier (example)", "Aluminum 6063-T6", "RoHS Compliant", "No SVHC", "PFAS Free"]]:
            ws.append(row)
        wb.save(p6)
        created.append(p6)
    # 7. Compliant CB certificate citing Edition 4 -> compliant
    pdf("CB_Certificate_IEC62368-1_Ed4_Portable_SSD_2025.pdf", [
        "IECEE CB SCHEME - CB TEST CERTIFICATE", "Certificate No: EXAMPLE-CB-0007", "Report Number: EXAMPLE-RPT-0007", f"NCB: {NCB}",
        f"Applicant: {MFR}", "Product: Example product - portable SSD (bus-powered), Model EXAMPLE-PSSD-01",
        "Standard: IEC 62368-1:2023 (Edition 4.0) Audio/video, information and communication technology equipment - Safety requirements",
        "National differences: US, CA, EU group, JP, KR, CN, IN, AU", "Ratings: 5 V DC, 2.5 A (USB Type-C bus powered)", "Date of Issue: 2025-03-06", "Valid until: 2028-03-05"])
    # 8. Expired KC certificate -> portal_filing (renewal)
    pdf("KC_Safety_Certificate_Desktop_Drive_Adapter_Korea.pdf", [
        "KC SAFETY CERTIFICATE (Korea Certification)", "Certificate No: EXAMPLE-KC-0008", "Issued under the Electrical Appliances and Consumer Products Safety Control Act",
        f"Certification Body: {NCB}, designated by KATS", f"Applicant: {MFR}",
        "Product: AC/DC Power Adapter for Example product - desktop storage drive (mains-powered), Model EXAMPLE-DSSD-01 (adapter model EXAMPLE-PSU-65)",
        "Standard: KC 62368-1 (K 62368-1:2019)", "EMC Registration: R-R-EXM-DSSD01 (KN 32 / KN 35)", "Date of Issue: 2022-06-30", "Valid until: 2025-06-29",
        "Country: Republic of Korea"])
    # 9. FCC SDoC without responsible-party statement -> doc_amendment
    pdf("FCC_SDoC_Card_Reader.pdf", [
        "FCC SUPPLIER'S DECLARATION OF CONFORMITY (SDoC)", "47 CFR Part 15 Subpart B - Unintentional Radiators", "Product: Example product - multi-card reader (USB-C)",
        "Model: EXAMPLE-RDR-01", "Test Report No: EXAMPLE-RPT-0009 (ANSI C63.4-2014, Class B)", f"Test Laboratory: {LAB}",
        "This device complies with Part 15 of the FCC Rules. Operation is subject to the following two conditions: (1) this device may not cause harmful interference,",
        "and (2) this device must accept any interference received, including interference that may cause undesired operation.", "Date: 2024-09-12"])
    # 10. Corrupt PDF -> unreadable
    p10 = os.path.join(target_dir, "Scanned_Legacy_Safety_Report_Corrupt.pdf")
    with open(p10, "wb") as f:
        f.write(b"%PDF-1.4\n" + os.urandom(1800) + b"\n%%EOF\n")
    created.append(p10)
    return created

