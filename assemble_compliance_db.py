import json

# Read the countries data
with open("countries_data.json", "r", encoding="utf-8") as f:
    countries_dict = json.load(f)

with open("compliance_db.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
existing_content = "".join(lines[:156])

# Build the rest of compliance_db.py
rest_of_code = '''
import os
import json

# ==========================================
# 2. COMPLETE 205 COUNTRIES & TERRITORIES
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
COUNTRIES_DATA_PATH = os.path.join(CURRENT_DIR, "countries_data.json")

if os.path.exists(COUNTRIES_DATA_PATH):
    with open(COUNTRIES_DATA_PATH, "r", encoding="utf-8") as f:
        COUNTRIES_DB = json.load(f)
else:
    COUNTRIES_DB = {}

# ==========================================
# 3. REGULATORY INTELLIGENCE & NEW REGULATION ALERTS
# ==========================================
REGULATION_ALERTS = [
    {
        "id": "ALERT-2026-01",
        "title": "EU Cyber Resilience Act (CRA) - Mandatory Security Standards for Storage & ITE",
        "region": "Europe & Eurasia",
        "country": "European Union (EU 27)",
        "standard": "Regulation (EU) 2024/2847 / EN 18031",
        "severity": "Critical",
        "effective_date": "2027-01-01",
        "affected_categories": ["internal_ssd", "external_ssd_bus", "external_ssd_powered", "enterprise_ssd", "usb_drive"],
        "summary": "The EU Cyber Resilience Act mandates horizontal cybersecurity rules for products with digital elements. Hardware storage devices with onboard microcontrollers must feature vulnerability reporting mechanisms, secure default firmware, and Software Bill of Materials (SBOM).",
        "action_required": "Establish SBOM documentation and ensure cryptographically signed firmware procedures are documented for Technical Documentation File.",
        "status": "Upcoming Mandatory",
        "source": "European Commission / Official Journal L"
    },
    {
        "id": "ALERT-2026-02",
        "title": "IEC 62368-1:2023 (4th Edition) Transition Roadmap & National Deviations",
        "region": "Global",
        "country": "IECEE CB Scheme (54+ Member Countries)",
        "standard": "IEC 62368-1:2023 (4th Edition)",
        "severity": "Warning",
        "effective_date": "2026-12-31",
        "affected_categories": ["external_ssd_powered", "enterprise_ssd", "internal_ssd", "sd_express"],
        "summary": "IECEE CB Scheme published transition guidelines for IEC 62368-1:2023. Key revisions affect touch temperature limits on high-speed bus-powered devices (e.g. SD Express / external SSDs) and DC-DC power delivery circuit evaluations.",
        "action_required": "Review thermal touch temperature data for SD Express cards and bus-powered SSDs. Plan CB report updates for upcoming 2026-2027 product revisions.",
        "status": "Active Transition",
        "source": "IECEE Committee of Testing Laboratories (CTL)"
    },
    {
        "id": "ALERT-2026-03",
        "title": "India BIS CRS Phase VII - Clarification on Solid State Storage & Bundled Power Adapters",
        "region": "Asia-Pacific",
        "country": "India",
        "standard": "IS 13252 (Part 1):2010 / IS 16169",
        "severity": "Critical",
        "effective_date": "2026-11-15",
        "affected_categories": ["external_ssd_powered", "external_ssd_bus", "internal_ssd"],
        "summary": "Ministry of Electronics and Information Technology (MeitY) and BIS issued strict customs advisory requiring independent BIS R-numbers for all bundled AC/DC power adapters. Desktop external drives cannot be cleared without valid in-country test reports from NABL accredited laboratories.",
        "action_required": "Audit Indian Authorized Representative (AIR) agreements and ensure all external power supplies bundled with desktop SSDs maintain active BIS registration.",
        "status": "Critical Enforcement",
        "source": "Bureau of Indian Standards (BIS) / MeitY"
    },
    {
        "id": "ALERT-2026-04",
        "title": "EU RoHS Directive / PFAS Universal Restriction Proposal",
        "region": "Europe & Eurasia",
        "country": "European Union (EU 27)",
        "standard": "EU RoHS 2011/65/EU / REACH Annex XVII",
        "severity": "Warning",
        "effective_date": "2027-06-30",
        "affected_categories": ["sd_card", "micro_sd", "sd_express", "cf_card", "gaming_card", "usb_drive", "internal_ssd", "external_ssd_bus", "external_ssd_powered", "enterprise_ssd", "card_reader"],
        "summary": "ECHA universal PFAS restriction proposal under REACH impacts fluoropolymers used in semiconductor packaging, thermal interface materials, and high-frequency cabling for SSDs and memory cards.",
        "action_required": "Request Full Material Declarations (FMD / IPC-1752A) from NAND flash, controller, and connector vendors to identify potential PFAS chemistries.",
        "status": "Regulatory Proposal",
        "source": "European Chemicals Agency (ECHA)"
    },
    {
        "id": "ALERT-2026-05",
        "title": "US FCC KDB 986446 - Equipment Authorization Covered List Supply Chain Attestation",
        "region": "Americas",
        "country": "United States",
        "standard": "47 CFR 2.911(d)(5) / (d)(7)",
        "severity": "Critical",
        "effective_date": "2026-08-01",
        "affected_categories": ["sd_card", "micro_sd", "sd_express", "cf_card", "gaming_card", "usb_drive", "internal_ssd", "external_ssd_bus", "external_ssd_powered", "enterprise_ssd", "card_reader"],
        "summary": "FCC mandates signed legal attestations certifying that equipment and sub-assemblies (including ASIC flash memory controllers and encryption chips) do not contain covered equipment from entities on the FCC Covered List.",
        "action_required": "Ensure all ASIC controller vendors submit updated 2.911(d)(5) non-covered equipment certifications for FCC filing packages.",
        "status": "Immediate Compliance",
        "source": "Federal Communications Commission (FCC)"
    },
    {
        "id": "ALERT-2026-06",
        "title": "Saudi Arabia SASO / SABER - Mandatory RoHS Enforcement on Removable Media",
        "region": "Middle East & North Africa",
        "country": "Saudi Arabia",
        "standard": "SASO RoHS Technical Regulation (M.A-179-21-09-01)",
        "severity": "Warning",
        "effective_date": "2026-10-01",
        "affected_categories": ["sd_card", "micro_sd", "cf_card", "usb_drive", "gaming_card", "card_reader"],
        "summary": "SASO has extended mandatory RoHS certificate uploads to all HS codes under 8523.51 (Solid-State Non-Volatile Storage) on the SABER portal. Shipments lacking certified laboratory test reports will be detained at Saudi ports.",
        "action_required": "Upload valid ISO 17025 accredited RoHS test reports on SABER to obtain Product Certificates of Conformity (PCoC) before shipping.",
        "status": "Enforcement Notice",
        "source": "Saudi Standards, Metrology and Quality Organization (SASO)"
    },
    {
        "id": "ALERT-2026-07",
        "title": "South Korea KATS / RRA - KC EMC & Safety Harmonization with CISPR 32:2019",
        "region": "Asia-Pacific",
        "country": "South Korea",
        "standard": "KS C 9832:2019 / KS C 9835:2019",
        "severity": "Info",
        "effective_date": "2026-12-01",
        "affected_categories": ["external_ssd_powered", "external_ssd_bus", "sd_express", "enterprise_ssd"],
        "summary": "National Radio Research Agency (RRA) finalized technical amendments for high-speed multi-lane interfaces (>1GHz clock). Introduces refined conducted and radiated emissions test setups for USB 3.2 Gen2x2 and PCIe interfaces.",
        "action_required": "Ensure future KC EMC filings performed at Korean accredited partner labs apply the latest KS C 9832 test procedures.",
        "status": "Active Guidance",
        "source": "National Radio Research Agency (RRA)"
    },
    {
        "id": "ALERT-2026-08",
        "title": "Taiwan BSMI CNS 15663 Section 5 - Marking Presence Condition Scrutiny",
        "region": "Asia-Pacific",
        "country": "Taiwan",
        "standard": "CNS 15663 Section 5 / CNS 13438",
        "severity": "Warning",
        "effective_date": "2026-09-30",
        "affected_categories": ["internal_ssd", "external_ssd_bus", "external_ssd_powered", "usb_drive", "card_reader"],
        "summary": "BSMI initiated market surveillance focusing on the declaration of presence condition of restricted substances. Packaging must carry the BSMI mark with RoHS identification (e.g. D33008 RoHS) and direct QR link to the declaration table.",
        "action_required": "Audit retail packaging artwork and verify web hosting of CNS 15663 presence declaration tables for all BSMI-registered SKUs.",
        "status": "Market Surveillance",
        "source": "Bureau of Standards, Metrology and Inspection (BSMI)"
    },
    {
        "id": "ALERT-2026-09",
        "title": "China RoHS Phase 2 Catalog & CCC Implementation on High-Power External Storage",
        "region": "Asia-Pacific",
        "country": "China",
        "standard": "GB 4943.1-2022 / SJ/T 11364-2014",
        "severity": "Critical",
        "effective_date": "2026-10-31",
        "affected_categories": ["external_ssd_powered", "enterprise_ssd"],
        "summary": "SAMR issued updated mandatory certification catalog. Desktop storage devices bundled with AC/DC power adapters exceeding 65W require updated CCC certification under the revised GB 4943.1-2022 safety standard.",
        "action_required": "Complete CCC certificate standard version upgrades with CQC or CTTL laboratory for all active external power supplies.",
        "status": "Mandatory Standard Transition",
        "source": "State Administration for Market Regulation (SAMR) / CQC"
    },
    {
        "id": "ALERT-2026-10",
        "title": "UK PSTI Act (Product Security and Telecommunications Infrastructure) Enforcement",
        "region": "Europe & Eurasia",
        "country": "United Kingdom",
        "standard": "UK PSTI Act 2022 / Regulations 2023",
        "severity": "Critical",
        "effective_date": "Enforced",
        "affected_categories": ["external_ssd_bus", "external_ssd_powered", "enterprise_ssd", "card_reader"],
        "summary": "UK law requires all connectable consumer hardware products sold in Great Britain to have a published Statement of Compliance (SoC), explicit vulnerability disclosure policy, and a defined minimum support period for security patches.",
        "action_required": "Maintain up-to-date Statements of Compliance on public website and verify packaging includes customer support URLs.",
        "status": "Active Enforcement",
        "source": "Office for Product Safety and Standards (OPSS)"
    }
]

# ==========================================
# 4. PRE-SEEDED PRODUCT PORTFOLIO (11 PRODUCTS)
# ==========================================
SAMPLE_PRODUCTS = [
    {
        "id": "PROD-001",
        "sku": "SDSDXEP-512G-GN4IN",
        "name": "SanDisk Extreme PRO SDXC UHS-II (512GB)",
        "category_id": "sd_card",
        "category_name": "SD Card (Standard / UHS-I / UHS-II)",
        "hw_revision": "Rev B.2",
        "controller": "Western Digital 20-82-01048-A1",
        "nand": "BiCS6 3D TLC NAND (162-Layer)",
        "power_source": "Bus-powered 3.3V / 1.8V (<2.5W)",
        "target_markets": ["US", "DE", "FR", "GB", "JP", "KR", "TW", "CN", "IN", "AU", "SA", "BR", "CA", "MX"],
        "compliance_status": "Certified",
        "active_certs_count": 14,
        "readiness_pct": 100
    },
    {
        "id": "PROD-002",
        "sku": "SDSQXAV-1T00-GN6MA",
        "name": "SanDisk Extreme MicroSDXC UHS-I (1TB)",
        "category_id": "micro_sd",
        "category_name": "MicroSD Card",
        "hw_revision": "Rev C.1",
        "controller": "Western Digital 20-82-01024-B0",
        "nand": "BiCS5 3D TLC NAND (112-Layer)",
        "power_source": "Bus-powered 3.3V / 1.8V (<1.8W)",
        "target_markets": ["US", "DE", "FR", "GB", "JP", "KR", "TW", "CN", "IN", "AU", "SA", "BR", "CA", "MX", "ZA", "SG"],
        "compliance_status": "Certified",
        "active_certs_count": 16,
        "readiness_pct": 100
    },
    {
        "id": "PROD-003",
        "sku": "SDEX-256G-GN9EX",
        "name": "SanDisk SD Express Next-Gen PCIe NVMe (256GB)",
        "category_id": "sd_express",
        "category_name": "SD Express Card (PCIe / NVMe)",
        "hw_revision": "Rev A.1",
        "controller": "SanDisk PCIe Gen4x1 NVMe Low-Power ASIC",
        "nand": "BiCS8 3D QLC/TLC NAND (218-Layer)",
        "power_source": "Bus-powered (3.3V / 1.8V, up to 4.2W)",
        "target_markets": ["US", "DE", "FR", "GB", "JP", "KR", "TW", "CN", "IN", "AU"],
        "compliance_status": "Testing In Progress",
        "active_certs_count": 7,
        "readiness_pct": 70
    },
    {
        "id": "PROD-004",
        "sku": "SDCFE-512G-ZN4NN",
        "name": "SanDisk Professional PRO-CINEMA CFexpress Type B (512GB)",
        "category_id": "cf_card",
        "category_name": "CF / CFexpress Card",
        "hw_revision": "Rev B.0",
        "controller": "Western Digital PCIe Gen3x2 NVMe ASIC",
        "nand": "BiCS5 TLC NAND",
        "power_source": "Bus-powered 3.3V (3.3W max)",
        "target_markets": ["US", "DE", "FR", "GB", "JP", "KR", "TW", "CN", "CA", "AU"],
        "compliance_status": "Certified",
        "active_certs_count": 10,
        "readiness_pct": 100
    },
    {
        "id": "PROD-005",
        "sku": "WDBMPH0010BNC-WASN",
        "name": "WD_BLACK C50 Expansion Card for Xbox (1TB)",
        "category_id": "gaming_card",
        "category_name": "Gaming Storage Expansion Card",
        "hw_revision": "Rev A.3",
        "controller": "Custom Western Digital Velocity NVMe ASIC",
        "nand": "BiCS5 3D TLC NAND",
        "power_source": "Host-powered 3.3V (<4.0W)",
        "target_markets": ["US", "CA", "MX", "DE", "FR", "GB", "IT", "ES", "JP", "KR", "AU", "NZ", "BR", "SA", "AE"],
        "compliance_status": "Certified",
        "active_certs_count": 15,
        "readiness_pct": 100
    },
    {
        "id": "PROD-006",
        "sku": "SDDDC4-256G-G46",
        "name": "SanDisk Ultra Dual Drive Luxe USB Type-C (256GB)",
        "category_id": "usb_drive",
        "category_name": "USB Flash Drive",
        "hw_revision": "Rev D.0",
        "controller": "SanDisk USB 3.2 Gen 1 Native Bridge ASIC",
        "nand": "BiCS5 3D TLC NAND",
        "power_source": "5V Bus-powered (<3.0W)",
        "target_markets": ["US", "DE", "FR", "GB", "JP", "KR", "TW", "CN", "IN", "AU", "BR", "ZA", "SA", "AE"],
        "compliance_status": "Certified",
        "active_certs_count": 14,
        "readiness_pct": 100
    },
    {
        "id": "PROD-007",
        "sku": "WDS200T2X0E",
        "name": "WD_BLACK SN850X NVMe SSD (2TB)",
        "category_id": "internal_ssd",
        "category_name": "Internal SSD (M.2 NVMe / 2.5-inch SATA)",
        "hw_revision": "Rev B.1",
        "controller": "Western Digital 20-82-20035-B1 Proprietary NVMe",
        "nand": "BiCS5 112-Layer 3D TLC",
        "power_source": "Host internal 3.3V (7.5W peak)",
        "target_markets": ["US", "CA", "DE", "FR", "GB", "JP", "KR", "TW", "CN", "AU", "MA", "IN"],
        "compliance_status": "Certified",
        "active_certs_count": 12,
        "readiness_pct": 100
    },
    {
        "id": "PROD-008",
        "sku": "SDSSDE61-2T00-G25",
        "name": "SanDisk Extreme Portable SSD (2TB - Bus-Powered)",
        "category_id": "external_ssd_bus",
        "category_name": "External SSD (Without Power Adaptor - Bus-Powered)",
        "hw_revision": "Rev C.2",
        "controller": "WD NVMe Controller + ASMedia ASM2362 USB Bridge",
        "nand": "BiCS5 3D TLC NAND",
        "power_source": "USB-C Bus-powered (5V @ up to 2.5A, 12.5W max)",
        "target_markets": ["US", "CA", "MX", "DE", "FR", "GB", "IT", "JP", "KR", "TW", "CN", "IN", "AU", "BR", "SA", "AE", "SG"],
        "compliance_status": "Certified",
        "active_certs_count": 17,
        "readiness_pct": 100
    },
    {
        "id": "PROD-009",
        "sku": "SDPHF1A-018T-NBAAD",
        "name": "SanDisk Professional G-DRIVE Enterprise Desktop (18TB - Powered)",
        "category_id": "external_ssd_powered",
        "category_name": "External SSD (With Power Adaptor - Mains Powered)",
        "hw_revision": "Rev A.4",
        "controller": "Enterprise RAID/SATA to USB 3.2 Gen2 Bridge ASIC",
        "nand": "Enterprise Ultrastar 7200RPM HDD / SSD Hybrid Stack",
        "power_source": "External 100-240V AC/DC Power Brick (19V / 3.42A, 65W Level VI DoE)",
        "target_markets": ["US", "CA", "MX", "DE", "FR", "GB", "JP", "KR", "TW", "CN", "IN", "AU", "BR"],
        "compliance_status": "Certified",
        "active_certs_count": 13,
        "readiness_pct": 100
    },
    {
        "id": "PROD-010",
        "sku": "WUS5EA1A1CSP7D3",
        "name": "Ultrastar DC SN655 NVMe Enterprise SSD (15.36TB)",
        "category_id": "enterprise_ssd",
        "category_name": "Enterprise SSD (U.2, U.3, E1.S, E3.S)",
        "hw_revision": "Rev B.0",
        "controller": "Enterprise Dual-Port PCIe Gen4 NVMe Controller",
        "nand": "BiCS5 Enterprise TLC with Hardware Power Loss Protection",
        "power_source": "Server 12V Main + 3.3V Aux (25W maximum server workload)",
        "target_markets": ["US", "CA", "DE", "FR", "GB", "JP", "KR", "TW", "CN", "AU"],
        "compliance_status": "Certified",
        "active_certs_count": 10,
        "readiness_pct": 100
    },
    {
        "id": "PROD-011",
        "sku": "SDDR-489-G47",
        "name": "SanDisk ImageMate PRO Multi-Card USB-C Reader",
        "category_id": "card_reader",
        "category_name": "Memory Card Reader (Multi-Card / USB-C)",
        "hw_revision": "Rev B.1",
        "controller": "Genesys Logic GL3224 Multi-LUN Card Reader Controller",
        "nand": "None (Passive Media Transceiver)",
        "power_source": "5V Bus-powered via USB Type-C (<5.0W)",
        "target_markets": ["US", "CA", "DE", "FR", "GB", "JP", "KR", "TW", "CN", "AU", "SA"],
        "compliance_status": "Certified",
        "active_certs_count": 11,
        "readiness_pct": 100
    }
]

# ==========================================
# 5. SAMPLE CERTIFICATE VAULT RECORDS
# ==========================================
SAMPLE_CERTIFICATES = [
    {
        "id": "CERT-001",
        "cert_no": "DE 2-034821-M1",
        "scheme": "IECEE CB Scheme",
        "standard": "IEC 62368-1:2018 (3rd Edition)",
        "issuing_body": "TÜV SÜD Product Service GmbH",
        "product_id": "PROD-009",
        "product_name": "SanDisk Professional G-DRIVE Enterprise Desktop (18TB)",
        "country_coverage": "54 CB Scheme Member Countries",
        "issue_date": "2023-04-12",
        "expiry_date": "2028-04-11",
        "status": "Valid",
        "document_type": "CB Test Certificate & Test Report (TRF)",
        "notes": "Includes national deviations for USA, Canada, Japan, EU, China, India, Australia."
    },
    {
        "id": "CERT-002",
        "cert_no": "R-41098234",
        "scheme": "BIS CRS (Compulsory Registration Scheme)",
        "standard": "IS 13252 (Part 1):2010",
        "issuing_body": "Bureau of Indian Standards (MeitY)",
        "product_id": "PROD-009",
        "product_name": "SanDisk Professional G-DRIVE Enterprise Desktop (18TB)",
        "country_coverage": "India",
        "issue_date": "2024-11-20",
        "expiry_date": "2026-11-19",
        "status": "Expiring Soon",
        "document_type": "BIS Registration Certificate",
        "notes": "Renewal application must be submitted 90 days prior to expiry via AIR."
    },
    {
        "id": "CERT-003",
        "cert_no": "2023010901238910",
        "scheme": "CCC (China Compulsory Certification)",
        "standard": "GB 4943.1-2022 / GB/T 9254.1-2021",
        "issuing_body": "China Quality Certification Centre (CQC)",
        "product_id": "PROD-009",
        "product_name": "SanDisk Professional G-DRIVE Enterprise Desktop (18TB)",
        "country_coverage": "China",
        "issue_date": "2023-08-15",
        "expiry_date": "2028-08-14",
        "status": "Valid",
        "document_type": "CCC Certificate",
        "notes": "Annual factory surveillance audit required."
    },
    {
        "id": "CERT-004",
        "cert_no": "PSE-JET-29831",
        "scheme": "Japan PSE Mark (Diamond)",
        "standard": "J62368-1 (H30) / Ordinance Article 1",
        "issuing_body": "Japan Electrical Safety & Environment Technology Laboratories (JET)",
        "product_id": "PROD-009",
        "product_name": "SanDisk Professional G-DRIVE Enterprise Desktop (18TB)",
        "country_coverage": "Japan",
        "issue_date": "2023-06-01",
        "expiry_date": "2026-10-15",
        "status": "Critical",
        "document_type": "PSE Certificate of Conformity",
        "notes": "Renewal evaluation required before October 2026."
    },
    {
        "id": "CERT-005",
        "cert_no": "US-FCC-WD-2024-889",
        "scheme": "FCC Supplier Declaration of Conformity (SDoC)",
        "standard": "FCC 47 CFR Part 15 Subpart B (Class B)",
        "issuing_body": "Sporton International Inc. (FCC Accredited Lab)",
        "product_id": "PROD-008",
        "product_name": "SanDisk Extreme Portable SSD (2TB)",
        "country_coverage": "United States",
        "issue_date": "2024-02-10",
        "expiry_date": "2029-02-09",
        "status": "Valid",
        "document_type": "FCC Test Report & SDoC Form",
        "notes": "Includes Section 2.911(d)(5) covered list attestation."
    },
    {
        "id": "CERT-006",
        "cert_no": "EU-CE-SD-8821",
        "scheme": "EU CE Declaration of Conformity (DoC)",
        "standard": "EN 55032:2015+A11 / EN 55035:2017 / RoHS 2011/65/EU",
        "issuing_body": "Western Digital Technologies Inc. (Self-Declaration)",
        "product_id": "PROD-008",
        "product_name": "SanDisk Extreme Portable SSD (2TB)",
        "country_coverage": "European Union (EU 27) + EEA",
        "issue_date": "2024-01-15",
        "expiry_date": "Permanent (Design Life)",
        "status": "Valid",
        "document_type": "EU Declaration of Conformity",
        "notes": "Technical Documentation File stored under EU Authorized Rep."
    },
    {
        "id": "CERT-007",
        "cert_no": "R-R-WDC-SN850X",
        "scheme": "South Korea KC Conformity Assessment",
        "standard": "KS C 9832 / KS C 9835 (EMC)",
        "issuing_body": "National Radio Research Agency (RRA)",
        "product_id": "PROD-007",
        "product_name": "WD_BLACK SN850X NVMe SSD (2TB)",
        "country_coverage": "South Korea",
        "issue_date": "2022-09-01",
        "expiry_date": "Permanent",
        "status": "Valid",
        "document_type": "KC Registration Certificate",
        "notes": "Component evaluation inside representative host system."
    },
    {
        "id": "CERT-008",
        "cert_no": "R33008-RoHS",
        "scheme": "Taiwan BSMI RPC Certification",
        "standard": "CNS 13438 / CNS 15663 Section 5",
        "issuing_body": "Bureau of Standards, Metrology and Inspection (BSMI)",
        "product_id": "PROD-007",
        "product_name": "WD_BLACK SN850X NVMe SSD (2TB)",
        "country_coverage": "Taiwan",
        "issue_date": "2023-03-10",
        "expiry_date": "2026-03-09",
        "status": "Expired",
        "document_type": "BSMI Product Certification",
        "notes": "Renewal application pending BSMI review."
    },
    {
        "id": "CERT-009",
        "cert_no": "ERAC-RCM-99231",
        "scheme": "Australia / New Zealand RCM Registration",
        "standard": "AS/NZS CISPR 32:2015",
        "issuing_body": "Electrical Regulatory Authorities Council (ERAC)",
        "product_id": "PROD-001",
        "product_name": "SanDisk Extreme PRO SDXC UHS-II (512GB)",
        "country_coverage": "Australia & New Zealand",
        "issue_date": "2022-05-18",
        "expiry_date": "2027-05-17",
        "status": "Valid",
        "document_type": "RCM Responsible Supplier Declaration",
        "notes": "Registered by local Australian Responsible Supplier."
    },
    {
        "id": "CERT-010",
        "cert_no": "SABER-2024-8812",
        "scheme": "Saudi Arabia SABER PCoC & SCoC",
        "standard": "SASO RoHS / SASO IEC 62368-1",
        "issuing_body": "TÜV Rheinland Middle East (SASO Approved Notified Body)",
        "product_id": "PROD-006",
        "product_name": "SanDisk Ultra Dual Drive Luxe USB Type-C (256GB)",
        "country_coverage": "Saudi Arabia",
        "issue_date": "2024-03-01",
        "expiry_date": "2025-02-28",
        "status": "Expired",
        "document_type": "SABER Product Certificate of Conformity",
        "notes": "Annual renewal on SABER platform required for customs shipment release."
    },
    {
        "id": "CERT-011",
        "cert_no": "NIST-CMVP-4412",
        "scheme": "FIPS 140-3 Cryptographic Module Validation",
        "standard": "FIPS 140-3 Level 2 (Security / Cryptography)",
        "issuing_body": "NIST Cryptographic Module Validation Program (CMVP)",
        "product_id": "PROD-010",
        "product_name": "Ultrastar DC SN655 NVMe Enterprise SSD (15.36TB)",
        "country_coverage": "United States & Canada (Federal & Enterprise)",
        "issue_date": "2023-10-05",
        "expiry_date": "2028-10-04",
        "status": "Valid",
        "document_type": "NIST Validation Certificate",
        "notes": "Cryptographic hardware engine validation for Self-Encrypting Drive (SED)."
    }
]

# ==========================================
# 6. ECO / ECN COMPLIANCE IMPACT ANALYZER ENGINE
# ==========================================
def evaluate_eco_impact(category_id, component_type, change_description, target_countries):
    """
    Evaluates the compliance impact of an Engineering Change Order (ECO)
    across the selected target countries for a specific product category.
    """
    category = PRODUCT_CATEGORIES.get(category_id, {})
    results = []
    overall_severity = "Minor"

    # Rules definition
    # Critical triggers:
    # 1. Power adapter change on external_ssd_powered: Mandatory Safety re-test across all mains regulated countries.
    # 2. Controller ASIC change: Delta EMC emissions test across FCC, CE, VCCI, KC, BSMI.
    # 3. NAND flash revision: Delta radiated emissions & internal verification.
    # 4. Enclosure resin: Flammability rating check (UL94 V-0 vs HB).
    # 5. Firmware crypto: FIPS / SED re-evaluation for Enterprise SSD.

    for country_code in target_countries:
        country = COUNTRIES_DB.get(country_code, {
            'code': country_code, 'name': country_code, 'region': 'Unknown',
            'authority': 'National Agency', 'marks': ['CE']
        })

        action_level = "No Action Required"
        details = "Internal engineering verification records only. No agency filing needed."
        authority_to_notify = "None"
        lead_time = "0 weeks"

        if component_type == 'power_adapter':
            if category_id == 'external_ssd_powered':
                overall_severity = "Critical"
                if country_code in ['IN', 'CN', 'JP', 'MX', 'BR', 'US', 'CA', 'KR', 'TW', 'SG', 'MY', 'SA', 'ZA']:
                    action_level = "Critical: Mandatory Safety Re-test & Certificate Amendment"
                    authority_to_notify = country['authority']
                    lead_time = f"{country.get('lead_time_weeks', 6)} weeks"
                    if country_code == 'IN':
                        details = "New external power supply requires independent testing at BIS-recognized Indian lab and endorsement on existing R-number."
                    elif country_code == 'CN':
                        details = "CCC safety certificate amendment required. Model additions/alternate power supply testing at CNAS lab."
                    elif country_code == 'JP':
                        details = "PSE Diamond certification for the AC adapter must be issued by a METI-registered Conformity Assessment Body."
                    elif country_code == 'US' or country_code == 'CA':
                        details = "UL/cUL NRTL file review and DoE Level VI energy efficiency test report update."
                    else:
                        details = f"Safety certificate amendment required with national deviation testing under {country.get('safety_std', 'IEC 62368-1')}."
                else:
                    action_level = "Moderate: CB Scheme Test Report Update"
                    details = "Issue CB Test Report amendment reflecting new power supply model ratings and thermal limits."
                    lead_time = "3-4 weeks"
            else:
                action_level = "Not Applicable"
                details = "Device is bus-powered; external power adapter change does not directly affect this SKU."

        elif component_type == 'controller_asic':
            if overall_severity != "Critical":
                overall_severity = "Moderate"
            if country_code in ['US', 'DE', 'FR', 'GB', 'JP', 'KR', 'TW', 'CN', 'AU', 'CA']:
                action_level = "Moderate: Delta EMC Testing & Permissive Change"
                authority_to_notify = country['authority']
                lead_time = "3-5 weeks"
                if country_code == 'US':
                    details = "Perform radiated and conducted emissions testing. Class II Permissive Change or SDoC technical documentation update."
                elif country_code == 'TW':
                    details = "BSMI RPC report amendment with delta EMC emissions test data."
                elif country_code == 'KR':
                    details = "KC EMC technical document modification filing with RRA accredited test laboratory report."
                else:
                    details = "Delta radiated emissions test up to highest clock harmonic. Update CE Technical Construction File (TCF)."
            else:
                action_level = "Minor: Documentation Update"
                details = "Update BOM and technical specs in national customs file."
                lead_time = "1-2 weeks"

        elif component_type == 'nand_flash':
            action_level = "Minor: Engineering Verification & RoHS Update"
            authority_to_notify = "Internal Compliance Archive"
            details = "Verify RoHS/REACH full material disclosure for new NAND die/packaging. Delta spot-check for radiated emissions."
            lead_time = "1-2 weeks"

        elif component_type == 'enclosure_material':
            if category_id in ['external_ssd_powered', 'enterprise_ssd']:
                overall_severity = "Moderate" if overall_severity != "Critical" else "Critical"
                action_level = "Moderate: Flammability & Thermal Audit"
                authority_to_notify = "UL / CB Scheme Notified Body"
                details = "Verify new resin maintains required UL94 flame rating (UL94 V-0 or V-1). Submit Yellow Card to safety test lab."
                lead_time = "2-3 weeks"
            else:
                action_level = "Minor: RoHS / Halogen-Free Verification"
                details = "Obtain supplier certificate of compliance for RoHS, REACH, and California Proposition 65."
                lead_time = "1 week"

        elif component_type == 'firmware_crypto':
            if category_id == 'enterprise_ssd' or 'encrypted' in category.get('name', '').lower():
                overall_severity = "Critical"
                action_level = "Critical: FIPS 140-3 / TCG Security Re-evaluation"
                authority_to_notify = "NIST CMVP / Accredited Cryptographic Lab"
                details = "Modifications to cryptographic boundary or encryption keys require regression testing under FIPS 140-3 Sub-Module."
                lead_time = "8-16 weeks"
            else:
                action_level = "No Action Required"
                details = "Standard storage firmware update without RF or cryptographic module changes does not trigger regulatory re-filing."
                lead_time = "0 weeks"

        elif component_type == 'pcb_layout':
            overall_severity = "Moderate" if overall_severity != "Critical" else "Critical"
            action_level = "Moderate: EMC Radiated Emissions Delta Test"
            authority_to_notify = "EMC Lab / Internal TCF"
            details = "PCB trace re-routing can alter radiated emissions profile. Delta testing recommended before mass production release."
            lead_time = "2-4 weeks"

        elif component_type == 'passive_components':
            action_level = "No Action Required"
            details = "Second-sourcing pin-compatible passive components (capacitors, resistors) does not require agency notification if ratings are identical."
            lead_time = "0 weeks"

        else:
            action_level = "Minor: Review Required"
            details = "General component change review. Check RoHS and safety file impact."
            lead_time = "1 week"

        results.append({
            'country_code': country_code,
            'country_name': country.get('name', country_code),
            'region': country.get('region', 'Global'),
            'authority': country.get('authority', 'Agency'),
            'action_level': action_level,
            'details': details,
            'authority_to_notify': authority_to_notify,
            'lead_time': lead_time
        })

    return {
        'overall_severity': overall_severity,
        'category_id': category_id,
        'category_name': category.get('name', category_id),
        'component_type': component_type,
        'change_description': change_description,
        'countries_analyzed': len(target_countries),
        'results': results
    }
'''

with open("compliance_db.py", "w", encoding="utf-8") as f:
    f.write(existing_content + "\n" + rest_of_code)

print("Successfully assembled full compliance_db.py!")
