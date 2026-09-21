"""
Storage & Memory Global Compliance Management (GCM) Database
Comprehensive database for Information Technology Equipment (ITE) focusing on
11 Memory & Storage product categories, 204 Countries & Territories,
Live Regulatory Intelligence Alerts, and ECO Change Impact Assessment Rules.
"""

# ==========================================
# 1. THE 11 STORAGE & MEMORY PRODUCT CATEGORIES
# ==========================================
PRODUCT_CATEGORIES = {
    'sd_card': {
        'id': 'sd_card',
        'name': 'SD Card (Standard / UHS-I / UHS-II)',
        'description': 'Full-size secure digital flash memory cards for cameras, broadcast, laptops, and industrial devices.',
        'interface': 'SD Bus Protocol (UHS-I / UHS-II)',
        'power_type': 'Bus-powered (3.3V / 1.8V, <2.5W)',
        'safety_class': 'SELV / Class III (Exempt from mains safety testing in almost all jurisdictions)',
        'emc_class': 'Class B (Consumer / Residential)',
        'environmental': ['EU RoHS 2/3 (10 substances)', 'REACH SVHC', 'Halogen-Free', 'China RoHS', 'Prop 65'],
        'consortium': 'SD Association (SDA Compliance / HALT)',
        'icon': 'credit-card',
        'risk_tier': 'Low'
    },
    'micro_sd': {
        'id': 'micro_sd',
        'name': 'MicroSD Card',
        'description': 'Ultra-compact removable flash memory for smartphones, action cameras, drones, and IoT edge devices.',
        'interface': 'MicroSD Bus (UHS-I / UHS-II)',
        'power_type': 'Bus-powered (3.3V / 1.8V, <2.0W)',
        'safety_class': 'SELV / Class III',
        'emc_class': 'Class B',
        'environmental': ['EU RoHS', 'REACH', 'Halogen-Free', 'China RoHS', 'Prop 65'],
        'consortium': 'SD Association (SDA Compliance)',
        'icon': 'microchip',
        'risk_tier': 'Low'
    },
    'sd_express': {
        'id': 'sd_express',
        'name': 'SD Express Card (PCIe / NVMe)',
        'description': 'Next-gen SD card leveraging PCIe Gen3/Gen4 and NVMe protocol (SD 7.0/8.0/9.0) achieving speeds up to 4GB/s.',
        'interface': 'PCIe Gen3x1/Gen4x1/Gen4x2 & NVMe protocol',
        'power_type': 'Bus-powered (3.3V / 1.8V / optional 12V supply pin, up to 4.32W), higher thermal dissipation',
        'safety_class': 'SELV / Class III (Thermal touch temperature verification required)',
        'emc_class': 'Class B (Strict high-frequency radiated emissions review up to 6GHz due to PCIe clocking)',
        'environmental': ['EU RoHS', 'REACH', 'China RoHS', 'Halogen-Free'],
        'consortium': 'SD Association & PCI-SIG',
        'icon': 'zap',
        'risk_tier': 'Low-Medium'
    },
    'cf_card': {
        'id': 'cf_card',
        'name': 'CF / CFexpress Card',
        'description': 'High-throughput professional removable media (CompactFlash, CFast, CFexpress Type A/B/C) for cinema & DSLR cameras.',
        'interface': 'PCIe Gen3/Gen4 x2/x4 NVMe or SATA (CFast)',
        'power_type': 'Bus-powered (3.3V, up to 3.5W)',
        'safety_class': 'SELV / Class III',
        'emc_class': 'Class B',
        'environmental': ['EU RoHS', 'REACH', 'China RoHS', 'Prop 65'],
        'consortium': 'CompactFlash Association (CFA)',
        'icon': 'hard-drive',
        'risk_tier': 'Low-Medium'
    },
    'gaming_card': {
        'id': 'gaming_card',
        'name': 'Gaming Storage Expansion Card',
        'description': 'Proprietary / custom form-factor NVMe storage expansion cartridges designed for gaming consoles (Xbox Velocity / PS5).',
        'interface': 'Custom PCIe Gen4 x2 NVMe interface',
        'power_type': 'Host-powered (3.3V, up to 4.5W)',
        'safety_class': 'SELV / Class III',
        'emc_class': 'Class B',
        'environmental': ['EU RoHS', 'REACH', 'WEEE', 'Prop 65'],
        'consortium': 'Console OEM Specification / PCI-SIG',
        'icon': 'gamepad-2',
        'risk_tier': 'Medium'
    },
    'usb_drive': {
        'id': 'usb_drive',
        'name': 'USB Flash Drive',
        'description': 'Portable thumb drives with USB Type-A, Type-C, dual interfaces, or hardware encryption.',
        'interface': 'USB 3.2 Gen 1 / Gen 2 / USB-C',
        'power_type': '5V Bus-powered via USB port (<4.5W)',
        'safety_class': 'SELV / Class III',
        'emc_class': 'Class B',
        'environmental': ['EU RoHS', 'REACH', 'China RoHS', 'WEEE', 'Prop 65'],
        'consortium': 'USB-IF (USB-IF TID Certification), optional FIPS 140-3 for secure drives',
        'icon': 'usb',
        'risk_tier': 'Low'
    },
    'internal_ssd': {
        'id': 'internal_ssd',
        'name': 'Internal SSD (M.2 NVMe / 2.5" SATA)',
        'description': 'Solid-state drives mounted inside consumer laptops, desktop PCs, and commercial workstations.',
        'interface': 'M.2 PCIe Gen4/Gen5 x4 NVMe or 2.5-inch SATA 6Gbps',
        'power_type': 'Host internal 3.3V (M.2) or 5V (2.5"), 3W-8.5W peak',
        'safety_class': 'UL Recognized Component (UL 62368-1) / TUV Bauart Mark',
        'emc_class': 'Class B (tested inside representative host ITE chassis)',
        'environmental': ['EU RoHS', 'REACH', 'China RoHS', 'WEEE'],
        'consortium': 'PCI-SIG, NVM Express Organization, SATA-IO',
        'icon': 'cpu',
        'risk_tier': 'Medium'
    },
    'external_ssd_bus': {
        'id': 'external_ssd_bus',
        'name': 'External SSD (Without Power Adaptor - Bus-Powered)',
        'description': 'Pocketable and rugged external solid state drives powered directly by host USB-C or Thunderbolt cable.',
        'interface': 'USB 3.2 Gen2x2 (20Gbps), USB4 / Thunderbolt 4 (40Gbps)',
        'power_type': 'Bus-powered via USB Type-C (5V @ up to 3A, 15W max)',
        'safety_class': 'IEC/EN/UL 62368-1 (Low risk / CB Report required for customs clearance)',
        'emc_class': 'Class B (Strict radiated emissions on high-speed USB-C cables)',
        'environmental': ['EU RoHS', 'REACH', 'Packaging EPR', 'WEEE', 'Prop 65'],
        'consortium': 'USB-IF, Intel/Apple Thunderbolt',
        'icon': 'layers',
        'risk_tier': 'Medium'
    },
    'external_ssd_powered': {
        'id': 'external_ssd_powered',
        'name': 'External SSD (With Power Adaptor - Mains Powered)',
        'description': 'High-capacity desktop external SSDs, multi-bay RAID enclosures, and studio drives with AC/DC power brick.',
        'interface': 'USB 3.2 / Thunderbolt 3/4 / Hubs with Power Delivery pass-through',
        'power_type': '100-240V AC Mains External Power Supply (EPS) 12V/19V DC Output (18W to 90W+)',
        'safety_class': 'Full Mandatory Safety: UL/cUL 62368-1, CE LVD, BIS (India), CCC (China), PSE (Japan), NOM (Mexico), KC (Korea)',
        'emc_class': 'Class B + Mains Harmonics (EN 61000-3-2) & Voltage Flicker (EN 61000-3-3)',
        'environmental': ['EU RoHS', 'REACH', 'WEEE', 'US DoE Level VI Energy Efficiency', 'EU ErP 2019/1782', 'NRCan'],
        'consortium': 'USB-IF, Thunderbolt',
        'icon': 'plug',
        'risk_tier': 'High'
    },
    'enterprise_ssd': {
        'id': 'enterprise_ssd',
        'name': 'Enterprise SSD (U.2, U.3, E1.S, E3.S)',
        'description': 'Data center and hyperscale server NVMe solid state drives with high endurance, power-loss protection, and hardware encryption.',
        'interface': 'PCIe Gen4/Gen5 Dual-Port NVMe, EDSFF (E1.S, E1.L, E3.S, E3.L) or U.2/U.3',
        'power_type': 'Server backplane 12V Main + 3.3V Aux (15W-40W under maximum datacenter load)',
        'safety_class': 'UL/cUL Recognized Component (UL 62368-1), CB Scheme',
        'emc_class': 'Class A (Commercial / Datacenter) or Class B, CISPR 32, FCC Part 15 Class A/B',
        'environmental': ['EU RoHS', 'REACH', 'Halogen-Free', 'Conflict Minerals (3TG)'],
        'consortium': 'PCI-SIG, NVMe, OCP (Open Compute Project), TCG Enterprise / FIPS 140-3',
        'icon': 'server',
        'risk_tier': 'High'
    },
    'card_reader': {
        'id': 'card_reader',
        'name': 'Memory Card Reader (Multi-Card / USB-C)',
        'description': 'Peripheral reader docking stations with slots for SD, MicroSD, CFexpress, and SD Express cards.',
        'interface': 'USB 3.2 Gen2 / USB-C host to card media slots',
        'power_type': '5V Bus-powered via USB port (<7.5W)',
        'safety_class': 'IEC/EN 62368-1',
        'emc_class': 'Class B',
        'environmental': ['EU RoHS', 'REACH', 'WEEE', 'China RoHS'],
        'consortium': 'USB-IF, SD Association, CompactFlash Association',
        'icon': 'inbox',
        'risk_tier': 'Low-Medium'
    }
}



import os
import sys
import json

# ==========================================
# 2. COMPLETE 205 COUNTRIES & TERRITORIES
# ==========================================
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    CURRENT_DIR = sys._MEIPASS
else:
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
        "source": "European Commission / Official Journal L",
        "detailed_summary": "The European Union has enacted Regulation (EU) 2024/2847 (Cyber Resilience Act), introducing the world's first mandatory horizontal cybersecurity baseline for hardware products with digital elements placed on the EU Single Market. For solid-state drives, external drives, and intelligent USB storage controllers, the regulation imposes legal duty-of-care obligations throughout the product lifecycle. Manufacturers must certify that flash microcontrollers are designed without known exploitable vulnerabilities, incorporate secure boot mechanisms, support cryptographically authenticated firmware updates, and maintain a verifiable Software Bill of Materials (SBOM). Furthermore, manufacturers are legally required to report actively exploited vulnerabilities to ENISA and relevant national CSIRTs within 24 hours of discovery.",
        "technical_impact": "Requires hardware root-of-trust or authenticated ECDSA/RSA firmware signing keys on flash memory controllers (NVMe/SATA/USB bridge ASICs). Unsigned firmware flashing via DFU or vendor diagnostic commands must be permanently disabled in production SKUs. SBOM must be maintained in CycloneDX or SPDX machine-readable formats covering all firmware components.",
        "timeline_milestones": [
            {"phase": "Regulation Entry into Force", "date": "2024-11-20", "status": "Completed"},
            {"phase": "Mandatory Vulnerability Reporting to ENISA (24hr SLA)", "date": "2026-05-11", "status": "Upcoming"},
            {"phase": "Full Mandatory Conformity Assessment & CE Marking Enforcement", "date": "2027-01-01", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "Official Journal Regulation (EU) 2024/2847 (EUR-Lex)", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847"},
            {"label": "European Commission CRA Implementation Portal", "url": "https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act"},
            {"label": "ENISA Vulnerability Disclosure Guidelines", "url": "https://www.enisa.europa.eu/topics/cybersecurity-education/vulnerability-disclosure"}
        ],
        "compliance_checklist": [
            "Generate machine-readable Software Bill of Materials (SBOM) for all NAND controller firmware builds",
            "Implement signed cryptographic firmware update verification inside ROM bootloader",
            "Establish 10-year vulnerability disclosure and security patch support policy published on support portal",
            "Update EU Declaration of Conformity (DoC) to reference Regulation (EU) 2024/2847 prior to Jan 1, 2027"
        ]
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
        "source": "IECEE Committee of Testing Laboratories (CTL)",
        "detailed_summary": "The International Electrotechnical Commission (IEC) and the IECEE Committee of Testing Laboratories (CTL) have finalized the global application guidelines for IEC 62368-1:2023 (Edition 4.0). This edition introduces critical clarifications specifically targeting high-power bus-powered peripherals, USB Type-C Power Delivery (USB-PD) storage, and high-speed removable media like SD Express. Unlike Edition 3, Edition 4 refines Clause 9 (Thermal Burn Injury Hazard), introducing stringent external enclosure temperature limits under maximum continuous sustained read/write workloads (e.g., TS2 temperature class limits of 70°C for metal surfaces and 85°C for plastic). It also harmonizes outdoor/ruggedized enclosure requirements and DC-DC converter fault condition testing under single-component breakdown scenarios.",
        "technical_impact": "Thermal evaluation must be conducted under worst-case 100% duty cycle data transfer at 35°C ambient. Metal enclosures on bus-powered external SSDs exceeding 70°C will fail Clause 9 unless firmware thermal throttling actively caps surface temperatures. Requires updated CB Test Certificates and Test Reports (TRF) covering national deviations for USA, EU, Japan, China, and India.",
        "timeline_milestones": [
            {"phase": "Publication of IEC 62368-1:2023 Standard", "date": "2023-05-26", "status": "Completed"},
            {"phase": "IECEE CTL TRF 62368-1_4 Available for Lab Accreditation", "date": "2024-03-15", "status": "Active"},
            {"phase": "CENELEC Harmonization in Europe (EN IEC 62368-1:2024)", "date": "2025-12-31", "status": "In Progress"},
            {"phase": "Mandatory Sunset of Edition 3 in Major NCBs", "date": "2026-12-31", "status": "Target Cutover"}
        ],
        "official_links": [
            {"label": "IECEE CB Scheme Official CTL Portal", "url": "https://www.iecee.org/dyn/www/f?p=106:1:0:::::"},
            {"label": "IEC 62368-1:2023 Standard Specification (IEC Webstore)", "url": "https://webstore.iec.ch/publication/67537"},
            {"label": "UL Solutions Technical Guidance on IEC 62368-1 4th Edition", "url": "https://www.ul.com/services/iec-62368-1-testing-and-certification"}
        ],
        "compliance_checklist": [
            "Execute thermal profile logging on metal enclosure external SSDs during continuous IOMeter test loops",
            "Verify thermal throttling algorithms engage before surface touches exceed 70°C (TS2 metal touch limit)",
            "Coordinate with accredited CB testing laboratory (e.g. TÜV / UL / SGS) to update baseline CB reports to Edition 4",
            "Audit national deviations for upcoming target export countries (US UL 62368-1, Japan J62368-1, Korea KC)"
        ]
    },
    {
        "id": "ALERT-2026-03",
        "title": "India BIS CRS: Mandatory Migration from IS 13252 (Part 1) [IEC 60950] to IS/IEC 62368-1:2023",
        "region": "Asia-Pacific",
        "country": "India",
        "standard": "IS/IEC 62368-1:2023 (Replacing IS 13252 Part 1:2010)",
        "severity": "Critical",
        "effective_date": "2028-11-01",
        "affected_categories": ["external_ssd_powered", "external_ssd_bus", "internal_ssd"],
        "summary": "Bureau of Indian Standards (BIS) and MeitY officially mandated the migration of all ICT equipment, solid-state storage, and external power supplies from legacy IEC 60950-1 (IS 13252 Part 1:2010) to the hazard-based safety standard IS/IEC 62368-1:2023. A concurrent running period is active until 01 November 2028, after which all legacy IS 13252 R-numbers will be cancelled and withdrawn.",
        "action_required": "Initiate safety re-testing with NABL-accredited Indian laboratories for external power adapters and desktop drives to IS/IEC 62368-1:2023 ahead of the 01 Nov 2028 deadline. Ensure Authorized Indian Representative (AIR) files change requests on the BIS portal.",
        "status": "Concurrent Migration Active",
        "source": "Bureau of Indian Standards (BIS) / MeitY Gazette Notification",
        "detailed_summary": "The Bureau of Indian Standards (BIS), acting under executive orders from the Ministry of Electronics and Information Technology (MeitY), published Gazette Notification CMD-III/16:IS/IEC 62368-1, establishing the mandatory adoption of IS/IEC 62368-1:2023 as the single harmonized standard for Information Technology and Audio/Video equipment. This officially initiates the phase-out of IS 13252 (Part 1):2010 (which was based on the legacy, superseded IEC 60950-1 standard). While bus-powered peripherals (such as USB flash drives and bus-powered SSDs) remain classified as SELV exempt unless bundled with a mains adapter, all external AC/DC power adapters and mains-powered storage enclosures holding active BIS R-numbers must undergo transition testing. A concurrent transition window has been granted until 01 November 2028.",
        "technical_impact": "External power adapters bundled with storage systems must be tested to IS/IEC 62368-1:2023 at an in-country NABL-accredited laboratory in India. In-country testing covers energy source classification (ES1/ES2/ES3), electrical strength, clearance/creepage distances, and fault conditions. Existing R-number registrations can be endorsed to IS/IEC 62368-1 by submitting supplementary NABL delta test reports.",
        "timeline_milestones": [
            {"phase": "BIS Gazette Notification of IS/IEC 62368-1:2023", "date": "2023-11-15", "status": "Completed"},
            {"phase": "NABL Lab Accreditation & Dual-Running Commences", "date": "2024-06-01", "status": "Active"},
            {"phase": "Recommended Cutover for All New Registrations", "date": "2026-11-01", "status": "Recommended"},
            {"phase": "Mandatory Withdrawal Date for Legacy IS 13252:2010", "date": "2028-11-01", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "Bureau of Indian Standards (BIS) Official CRS Portal", "url": "https://www.crsbis.in/BIS/"},
            {"label": "MeitY Compulsory Registration Scheme Gazette Circulars", "url": "https://www.meity.gov.in/esdm/standards"},
            {"label": "BIS Product Manual & Scope for IS/IEC 62368-1:2023", "url": "https://www.bis.gov.in/standards/standards-formulation/"}
        ],
        "compliance_checklist": [
            "Audit all active Indian R-numbers held by Authorized Indian Representative (AIR)",
            "Identify bundled AC/DC power supplies currently certified under IS 13252 (Part 1):2010",
            "Ship physical test samples (typically 2-4 units) to NABL-accredited laboratory in India for IS/IEC 62368-1 testing",
            "Submit Form I change request on BIS CRS portal to endorse R-number before the November 1, 2028 deadline"
        ]
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
        "source": "European Chemicals Agency (ECHA)",
        "detailed_summary": "The European Chemicals Agency (ECHA), in partnership with five national authorities (Germany, the Netherlands, Denmark, Sweden, and Norway), has published a universal restriction dossier under REACH Annex XVII concerning per- and polyfluoroalkyl substances (PFAS). This restriction encompasses over 10,000 synthetic organofluorine chemical compounds widely utilized in the electronics supply chain for fluoropolymer dielectrics, thermal interface materials (TIMs), fluorinated surfactants in semiconductor photolithography, and mold compounds for NAND flash packages. If enacted without broad industrial exemptions, manufacturers placing storage devices and flash media on the European market must demonstrate non-use above the proposed detection threshold (25 ppb for individual PFAS, 250 ppb for sum of PFAS).",
        "technical_impact": "Requires component-level chemical mass spectrometry audits. Flash memory packaging epoxy mold compounds (EMC), internal thermal silicone pads, and low-friction connector coatings must be screened for polytetrafluoroethylene (PTFE) and perfluorooctanoic acid (PFOA) derivatives. IPC-1752A Class D Full Material Declarations are required from foundries.",
        "timeline_milestones": [
            {"phase": "ECHA RAC and SEAC Scientific Opinion Finalization", "date": "2025-09-30", "status": "In Progress"},
            {"phase": "European Commission Draft Implementing Regulation", "date": "2026-06-30", "status": "Upcoming"},
            {"phase": "Earliest Enactment & Transition Period (18-36 Month Derogation)", "date": "2027-06-30", "status": "Projected Milestone"}
        ],
        "official_links": [
            {"label": "ECHA Universal PFAS Restriction Proposal Dossier", "url": "https://echa.europa.eu/hot-topics/perfluoroalkyl-chemicals-pfas"},
            {"label": "European Commission REACH Restriction Registry", "url": "https://ec.europa.eu/environment/chemicals/reach/reach_en.htm"},
            {"label": "IPC-1752A Materials Declaration Standard Resource", "url": "https://www.ipc.org/ipc-1752a"}
        ],
        "compliance_checklist": [
            "Issue chemical inquiry requests to raw wafer foundries, substrate vendors, and packaging houses",
            "Collect IPC-1752A Class D XML full material declarations for all active controller and NAND SKUs",
            "Screen bill of materials (BOM) for high-risk components (thermal pads, connectors, label adhesives)",
            "Track ECHA SEAC committee opinions regarding specific semiconductor derogation exemptions"
        ]
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
        "source": "Federal Communications Commission (FCC)",
        "detailed_summary": "The Federal Communications Commission (FCC) adopted Order FCC 22-84 (Protecting Against National Security Threats to the Communications Supply Chain through the Equipment Authorization Program), codified under 47 CFR Part 2. All equipment authorization applications—including Supplier's Declaration of Conformity (SDoC) technical files for unintentional radiators such as storage drives, USB flash devices, and memory cards—must contain formal, signed legal attestations from both the applicant and their US agent. Specifically, Section 2.911(d)(5) mandates written certification under penalty of perjury that the equipment does not contain hardware or sub-assemblies produced by any entity named on the FCC Covered List (e.g., Huawei, ZTE, Hytera, Hikvision, Dahua, and their subsidiaries). Section 2.911(d)(7) requires designation of an irrevocable US agent for service of process.",
        "technical_impact": "Even unbranded ASIC controllers, bridge chips, and third-party encryption modules must be certified via component supply-chain trace records. Customs and Border Protection (CBP) and FCC compliance audits cross-check vendor CAGE codes and parent entities against the active Covered List.",
        "timeline_milestones": [
            {"phase": "FCC 22-84 Order Effective Date", "date": "2023-02-06", "status": "Completed"},
            {"phase": "KDB 986446 D01 Attestation Procedures Enforced", "date": "2024-01-01", "status": "Active"},
            {"phase": "Mandatory Annual Re-Verification of US Agent & Attestations", "date": "2026-08-01", "status": "Annual Audit"}
        ],
        "official_links": [
            {"label": "FCC Official Covered List Database", "url": "https://www.fcc.gov/supplychain/coveredlist"},
            {"label": "FCC OET Knowledge Database (KDB) Publication 986446", "url": "https://apps.fcc.gov/oetcf/kdb/forms/FTSSearchResultPage.cfm?switch=P&id=28828"},
            {"label": "e-CFR: 47 CFR 2.911 Equipment Authorization Requirements", "url": "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-2/subpart-J/section-2.911"}
        ],
        "compliance_checklist": [
            "Obtain signed 47 CFR 2.911(d)(5)(i) and (ii) Covered List attestations from all silicon controller suppliers",
            "Maintain valid 47 CFR 2.911(d)(7) US Agent for Service of Process legal agreements on file",
            "Archive signed attestations within internal FCC SDoC Technical Construction Files (TCF)",
            "Audit supply chain vendors against monthly FCC Covered List updates published by Public Safety Bureau"
        ]
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
        "source": "Saudi Standards, Metrology and Quality Organization (SASO)",
        "detailed_summary": "The Saudi Standards, Metrology and Quality Organization (SASO) has entered Phase 4 enforcement of the Technical Regulation for the Restriction of Hazardous Substances (SASO RoHS). All solid-state storage products classified under HS Code 8523.51 (including SD/MicroSD cards, CFexpress cards, and USB flash memory) are now required to maintain active Product Certificates of Conformity (PCoC) issued by a SASO-approved Notified Body via the electronic SABER platform. Each PCoC filing requires a comprehensive hazardous substances evaluation report demonstrating compliance with restricted thresholds (Lead < 0.1%, Cadmium < 0.01%, Mercury < 0.1%, Hexavalent Chromium < 0.1%, PBBs/PBDEs < 0.1%, and Phthalates DEHP/BBP/DBP/DIBP < 0.1%). Shipments arriving at Saudi ports without a corresponding Shipment Certificate of Conformity (SCoC) linked to a valid PCoC will be held by Zakat, Tax and Customs Authority (ZATCA).",
        "technical_impact": "Testing must be performed by an accredited ISO/IEC 17025 laboratory using IEC 62321 test methods (XRF screening and GC-MS confirmatory testing). Certificates are valid for 1 year and must be renewed annually on SABER.",
        "timeline_milestones": [
            {"phase": "SASO RoHS Technical Regulation Publication", "date": "2021-07-09", "status": "Completed"},
            {"phase": "Phase 1-3 IT Equipment Enforcement", "date": "2022-2024", "status": "Completed"},
            {"phase": "Mandatory Customs Enforcement on All 8523.51 Storage SKUs", "date": "2026-10-01", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "Saudi Standards (SASO) Official Portal", "url": "https://www.saso.gov.sa/en/pages/default.aspx"},
            {"label": "SABER Electronic Conformity Assessment Platform", "url": "https://saber.sa"},
            {"label": "SASO RoHS Technical Regulation Document (Arabic/English)", "url": "https://saber.sa/Home/Regulations"}
        ],
        "compliance_checklist": [
            "Confirm all commercial invoices cite accurate 10-digit Saudi Tariff HS Codes (8523.51.xx.xx)",
            "Engage SASO-approved Notified Body (e.g. TÜV Rheinland / Intertek / SGS) for SABER PCoC issuance",
            "Upload ISO 17025 accredited IEC 62321 test reports covering all 10 RoHS substances",
            "Generate pre-clearance Shipment Certificate of Conformity (SCoC) on SABER prior to vessel departure"
        ]
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
        "source": "National Radio Research Agency (RRA)",
        "detailed_summary": "The National Radio Research Agency (RRA) of South Korea, operating under the Ministry of Science and ICT (MSIT), issued technical standard notice MSIT-RRA-2025-91 harmonizing Korean National Standards KS C 9832 (EMC Emissions) and KS C 9835 (EMC Immunity) with CISPR 32:2019 Edition 2.1. The updated test standard introduces specialized measurement methods for high-speed differential bus lines operating with internal fundamental clock frequencies exceeding 1 GHz. This directly impacts PCI Express NVMe drives (including SD Express cards and Thunderbolt/USB4 external storage). Radiated emissions must be measured up to 6 GHz with precise antenna positioning and continuous exerciser traffic. While passive memory cards (standard SD/MicroSD) remain exempt under Radio Waves Act Article 3, active bus-powered SSDs and card readers require conformity registration.",
        "technical_impact": "Testing must be conducted at an RRA-designated in-country laboratory or an international lab accredited under a bilateral Mutual Recognition Agreement (MRA). Radiated emissions above 1 GHz must comply with Class B average limits of 50 dB(uV/m) and peak limits of 70 dB(uV/m) at 3 meters. KC mark label must include the RRA registration number in format R-R-xxx-xxxx.",
        "timeline_milestones": [
            {"phase": "RRA Public Consultation Notice", "date": "2025-06-12", "status": "Completed"},
            {"phase": "Adoption of KS C 9832:2019 Amendments", "date": "2026-01-01", "status": "Active"},
            {"phase": "Mandatory Application for All New KC EMC Conformity Registrations", "date": "2026-12-01", "status": "Mandatory Cutover"}
        ],
        "official_links": [
            {"label": "National Radio Research Agency (RRA) Official Portal", "url": "https://www.rra.go.kr/en/index.do"},
            {"label": "Korea Agency for Technology and Standards (KATS)", "url": "https://www.kats.go.kr/en"},
            {"label": "RRA Law & Technical Regulations Database", "url": "https://www.rra.go.kr/en/notice/notice_list.do"}
        ],
        "compliance_checklist": [
            "Ensure laboratory test plans execute continuous read/write exerciser scripts during EMC scans",
            "Verify high-frequency radiated emissions sweeps are conducted up to 6 GHz for PCIe NVMe products",
            "Review exterior packaging artwork to confirm authorized Korean importer contact and KC emblem formatting",
            "Register final KC certificate under local Korean business entity prior to customs clearance"
        ]
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
        "source": "Bureau of Standards, Metrology and Inspection (BSMI)",
        "detailed_summary": "The Bureau of Standards, Metrology and Inspection (BSMI) of the Ministry of Economic Affairs (MOEA) has launched a targeted market inspection campaign enforcing compliance with standard CNS 15663 (Guidance on reduction of restricted chemical substances in electrical and electronic equipment), Section 5 (Marking of Presence). Under BSMI Registration of Product Certification (RPC) rules, all registered solid-state drives, USB flash drives, and memory readers must explicitly disclose the presence condition (either 'exceeding 0.1 wt%' or 'not exceeding 0.1 wt%') for 6 hazardous substances: Lead, Mercury, Cadmium, Hexavalent Chromium, PBB, and PBDE. The BSMI Commodity Inspection Mark displayed on the retail package must bear the RoHS identification code (e.g., 'R33008 RoHS' or 'D33008 RoHS'). In addition, a direct URL or QR code linking to the full CNS 15663 Section 5 declaration table must be accessible to Taiwanese consumers.",
        "technical_impact": "Packaging labeling non-compliance triggers administrative fines up to NT$ 1,000,000 under the Commodity Inspection Act and potential revocation of the BSMI RPC certificate. Web pages hosting the CNS 15663 declaration table must remain active throughout the product commercial lifecycle.",
        "timeline_milestones": [
            {"phase": "CNS 15663 Section 5 Initial Mandatory Date", "date": "2018-01-01", "status": "Completed"},
            {"phase": "BSMI Market Surveillance Enforcement Campaign", "date": "2025-10-01", "status": "Active"},
            {"phase": "Strict Customs Audit Deadline for Retail Packaging QR/RoHS Marks", "date": "2026-09-30", "status": "Target Enforcement"}
        ],
        "official_links": [
            {"label": "Taiwan BSMI Official Portal (MOEA)", "url": "https://www.bsmi.gov.tw/wSite/mp?mp=2"},
            {"label": "BSMI Commodity Inspection Regulations Database", "url": "https://www.bsmi.gov.tw/wSite/lp?ctNode=8644"},
            {"label": "CNS 15663 Section 5 Guidance & FAQ", "url": "https://www.bsmi.gov.tw/wSite/ct?xItem=63953&ctNode=4583"}
        ],
        "compliance_checklist": [
            "Audit all Taiwan retail packaging box art for correct BSMI emblem and 'Rxxxxx RoHS' marking",
            "Verify presence of Traditional Chinese product name, model number, rated voltage, and local importer details",
            "Ensure URL/QR code linking to the official CNS 15663 Section 5 table is live on public corporate domain",
            "Verify chemical test reports from ISO 17025 lab confirming substance presence percentages"
        ]
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
        "source": "State Administration for Market Regulation (SAMR) / CQC",
        "detailed_summary": "The State Administration for Market Regulation (SAMR) and the Certification and Accreditation Administration of the PRC (CNCA) announced implementation milestones for the unified safety standard GB 4943.1-2022 (Audio/video, information and communication technology equipment - Part 1: Safety requirements), which superseded GB 4943.1-2011. While standalone bus-powered storage devices (such as portable USB drives and flash memory cards) are not listed in the mandatory CCC catalog, bundled AC/DC power adapters and high-power desktop external storage arrays fall under mandatory CCC certification (Category 0807 / 0907). All active CCC certificates must be upgraded from the 2011 edition to the 2022 edition through supplementary delta testing. Furthermore, China RoHS (SJ/T 11364) Phase 2 compliance mandates the display of the green/orange Environmental Friendly Use Period (EFUP 10/20) emblem with the Table of Hazardous Substances in Simplified Chinese.",
        "technical_impact": "GB 4943.1-2022 introduces stricter requirements for high-altitude use (up to 5000m clearance multiplication factors) and tropical climate conditions. Power adapters must demonstrate safety compliance under in-country testing at an accredited Chinese test lab (e.g. CQC / CTTL / CESI). Annual factory surveillance audits are required to maintain CCC validity.",
        "timeline_milestones": [
            {"phase": "Publication of GB 4943.1-2022", "date": "2022-07-19", "status": "Completed"},
            {"phase": "Mandatory Implementation for New Submissions", "date": "2023-08-01", "status": "Completed"},
            {"phase": "Final Transition Deadline for Existing CCC Certificate Upgrades", "date": "2026-10-31", "status": "Cutoff Deadline"}
        ],
        "official_links": [
            {"label": "State Administration for Market Regulation (SAMR)", "url": "https://www.samr.gov.cn"},
            {"label": "China Quality Certification Centre (CQC) CCC Portal", "url": "https://www.cqc.com.cn"},
            {"label": "China Standard Service Network (GB 4943.1-2022)", "url": "https://openstd.samr.gov.cn"}
        ],
        "compliance_checklist": [
            "Submit CCC certificate standard version conversion applications to CQC for all external power supplies",
            "Conduct delta safety evaluations (thermal, 5000m altitude multiplier, and creepage) at designated lab",
            "Audit product body and packaging for Simplified Chinese markings and EFUP circular logo",
            "Prepare manufacturing facility for scheduled annual CCC factory surveillance audit"
        ]
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
        "source": "Office for Product Safety and Standards (OPSS)",
        "detailed_summary": "The UK Product Security and Telecommunications Infrastructure Act 2022 (PSTI) and the Product Security and Telecommunications Infrastructure (Security Requirements for Relevant Connectable Products) Regulations 2023 are in active legal enforcement across Great Britain (England, Scotland, and Wales). The law establishes mandatory minimum security baselines for all consumer connectable products, including external solid-state storage, network-attached drives, and microcontroller-driven USB interfaces that communicate over internet protocols or local computer buses. Manufacturers are legally prohibited from selling products in the UK unless each product is accompanied by a formal UK PSTI Statement of Compliance (SoC) signed by an authorized company officer. The manufacturer must maintain a public vulnerability disclosure policy and guarantee a defined minimum security update support period (stating the exact end-date in years and months).",
        "technical_impact": "Non-compliance constitutes a criminal offense under UK law, subjecting manufacturers to civil penalties up to £10,000,000 or 4% of worldwide turnover. Trading Standards officers conduct retail audits. The Statement of Compliance must accompany the product in the box or be immediately accessible via a dedicated UK URL printed on the packaging.",
        "timeline_milestones": [
            {"phase": "UK PSTI Regulations 2023 Laid Before Parliament", "date": "2023-09-14", "status": "Completed"},
            {"phase": "Mandatory Legal Enforcement Across Great Britain", "date": "2024-04-29", "status": "Active Legal Enforcement"},
            {"phase": "OPSS Retail Market Surveillance Audits Active", "date": "2026-01-01", "status": "Ongoing Scrutiny"}
        ],
        "official_links": [
            {"label": "UK Government PSTI Act 2022 Legislation", "url": "https://www.legislation.gov.uk/ukpga/2022/46/enacted"},
            {"label": "Office for Product Safety and Standards (OPSS) Guidance", "url": "https://www.gov.uk/guidance/product-security-and-telecommunications-infrastructure-act-2022"},
            {"label": "DSIT Security Requirements for Consumer Connectable Products", "url": "https://www.gov.uk/government/publications/consumer-connectable-product-safety"}
        ],
        "compliance_checklist": [
            "Draft and sign legal UK PSTI Statement of Compliance (SoC) for all active external storage SKUs",
            "Publish public Vulnerability Disclosure Policy (VDP) with security@sandisk.com contact point",
            "State explicit 'Defined Support Period' for security maintenance on public support documentation",
            "Provide physical or digital access to the Statement of Compliance with every UK retail shipment"
        ]
    },
    {
        "id": "ALERT-ENV-01",
        "title": "US EPA TSCA Section 8(a)(7) — Mandatory Reporting of PFAS in Electronic Articles & Storage Peripherals",
        "region": "Americas",
        "country": "United States",
        "standard": "TSCA 40 CFR Part 705 (PFAS Reporting Rule)",
        "severity": "Critical",
        "effective_date": "2026-05-08",
        "affected_categories": ["sd_card", "micro_sd", "sd_express", "cf_card", "gaming_card", "usb_drive", "internal_ssd", "external_ssd_bus", "external_ssd_powered", "enterprise_ssd", "card_reader"],
        "summary": "EPA final rule under TSCA Section 8(a)(7) mandates one-time retrospective reporting of manufactured or imported articles containing per- and polyfluoroalkyl substances (PFAS) since 2011, including electronic storage drives, cables, and packaging.",
        "action_required": "Execute supply chain chemical inquiry to identify all PFAS-containing components (thermal pads, fluoropolymer wire jackets, lubricants, mold compounds) and prepare EPA CDX reporting submission.",
        "status": "Mandatory Filing Window",
        "source": "US Environmental Protection Agency (EPA)",
        "detailed_summary": "The US Environmental Protection Agency (EPA) published its landmark Final Rule under Section 8(a)(7) of the Toxic Substances Control Act (TSCA), codified at 40 CFR Part 705. The rule establishes unprecedented reporting obligations for any entity that has manufactured or imported for commercial purposes any chemical substance, mixture, or article containing per- and polyfluoroalkyl substances (PFAS) in any year since January 1, 2011. Crucially for the electronics and storage industry, the rule contains NO de minimis threshold exemption and applies fully to 'article importers'. Solid-state drives, USB thumb drives, memory cards, and their peripheral cables frequently incorporate PFAS chemistries in fluoropolymer wire insulations (e.g. PTFE/FEP), thermal interface materials (TIMs), anti-friction coatings on mechanical connectors, and printed circuit board solder masks.",
        "technical_impact": "Article importers must report chemical identity, specific CAS numbers, trade names, quantities imported per year since 2011, customer exposure scenarios, and disposal pathways using EPA Central Data Exchange (CDX). Due diligence requires issuing IPC-1752A Class D inquiries to all NAND wafer suppliers, PCB assemblers, and enclosure molders.",
        "timeline_milestones": [
            {"phase": "EPA TSCA 8(a)(7) Final Rule Promulgation", "date": "2023-10-11", "status": "Completed"},
            {"phase": "EPA Central Data Exchange (CDX) Portal Opens for Submissions", "date": "2025-11-12", "status": "Active"},
            {"phase": "Mandatory Electronic Submission Deadline for Article Importers", "date": "2026-05-08", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "US EPA TSCA Section 8(a)(7) Official PFAS Reporting Portal", "url": "https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/tsca-section-8a7-reporting-and-recordkeeping-requirements"},
            {"label": "e-CFR 40 CFR Part 705 Full Legal Text", "url": "https://www.ecfr.gov/current/title-40/chapter-I/subchapter-R/part-705"},
            {"label": "EPA Central Data Exchange (CDX) Submission System", "url": "https://cdx.epa.gov"}
        ],
        "compliance_checklist": [
            "Issue chemical due diligence questionnaires to all component vendors for PFAS CAS numbers",
            "Screen Bill of Materials (BOM) for high-frequency cables (PTFE), thermal gap pads, and connector platings",
            "Calculate annual historical US import volumes in kilograms for all solid-state storage SKUs since 2011",
            "Submit completed Form U reporting packages via EPA Central Data Exchange (CDX) prior to cutover deadline"
        ]
    },
    {
        "id": "ALERT-ENV-02",
        "title": "EU Packaging & Packaging Waste Regulation (PPWR) — Recycled Plastic Content & Heavy Metal Limits",
        "region": "Europe & Eurasia",
        "country": "European Union (EU 27)",
        "standard": "EU PPWR (Repealing Directive 94/62/EC)",
        "severity": "Critical",
        "effective_date": "2026-12-31",
        "affected_categories": ["sd_card", "micro_sd", "sd_express", "cf_card", "gaming_card", "usb_drive", "internal_ssd", "external_ssd_bus", "external_ssd_powered", "card_reader"],
        "summary": "European Parliament and Council adopted the new Packaging and Packaging Waste Regulation (PPWR). Mandates 100% recyclable packaging by 2030, minimum post-consumer recycled plastic thresholds, and strict ban on PFAS in food/consumer contact packaging.",
        "action_required": "Redesign retail blister packs and drive cartons to incorporate minimum 35% post-consumer recycled (PCR) plastic content, eliminate unnecessary voids (>50% empty space ban), and audit heavy metal limits (<100 ppm).",
        "status": "Final Adoption Active",
        "source": "European Parliament / Council of the European Union",
        "detailed_summary": "The European Union has finalized the definitive Packaging and Packaging Waste Regulation (PPWR), replacing the legacy Directive 94/62/EC with directly applicable statutory obligations across all 27 EU Member States. Designed to combat escalating packaging waste and fossil plastic dependency, the PPWR establishes binding targets for electronic equipment packaging: (1) All packaging must be designed for recycling (DfR) and achieve recyclability performance grades A, B, or C by 2030; (2) Plastic packaging components must contain mandatory minimum post-consumer recycled (PCR) plastic percentages (35% target); (3) Maximum empty space ratio of 50% for e-commerce and retail multipacks, eliminating oversized display packaging; (4) Total concentration of heavy metals (Lead, Cadmium, Mercury, Hexavalent Chromium) must not exceed 100 mg/kg; (5) Explicit ban on intentional PFAS addition in packaging materials.",
        "technical_impact": "Requires transition from virgin thermoformed PVC/PET blister trays to verified post-consumer recycled (rPET) or certified cellulose/paper pulp trays. Packaging engineering must recalculate box volume-to-drive ratios to satisfy maximum 50% void ratio limits.",
        "timeline_milestones": [
            {"phase": "EU Council & Parliament Formal Political Agreement", "date": "2024-04-24", "status": "Completed"},
            {"phase": "Official Journal Publication & 18-Month Entry into Force", "date": "2024-12-01", "status": "Active"},
            {"phase": "Mandatory Packaging Heavy Metal & Empty Space Ratio Enforcement", "date": "2026-12-31", "status": "Enforcement Cutover"},
            {"phase": "Mandatory Minimum Recycled Plastic Content Enforcement", "date": "2030-01-01", "status": "Future Target"}
        ],
        "official_links": [
            {"label": "European Commission Packaging Waste Policy Portal", "url": "https://environment.ec.europa.eu/topics/waste-and-recycling/packaging-waste_en"},
            {"label": "EUR-Lex Legislative Observatory on PPWR", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52022PC0677"},
            {"label": "EPR Packaging Producer Compliance Register Guidelines", "url": "https://www.pro-e.org"}
        ],
        "compliance_checklist": [
            "Audit all retail blister packs and clamshell packaging for heavy metals (< 100 ppm total Pb/Cd/Hg/Cr VI)",
            "Obtain third-party Chain of Custody certification (ISO 14021) for recycled plastic (rPET) content in drive packaging",
            "Perform void-space volume calculation ensuring package-to-product ratio complies with 50% limit",
            "Register packaging volumes and pay Extended Producer Responsibility (EPR) eco-fees across all EU sales countries"
        ]
    },
    {
        "id": "ALERT-ENV-03",
        "title": "France AGEC Law — Mandatory Triman Logo & Info-tri Material Sorting Signage on Packaging",
        "region": "Europe & Eurasia",
        "country": "France",
        "standard": "Decree No. 2021-835 / French Environmental Code (AGEC Law)",
        "severity": "Warning",
        "effective_date": "Enforced",
        "affected_categories": ["sd_card", "micro_sd", "sd_express", "cf_card", "gaming_card", "usb_drive", "internal_ssd", "external_ssd_bus", "external_ssd_powered", "card_reader"],
        "summary": "French customs (DGCCRF) actively enforces mandatory Triman logo combined with harmonized Info-tri sorting signage on all consumer packaging, electronics, and accessories placed on the French market. Non-compliant artwork triggers port seizures and fines up to €15,000 per SKU.",
        "action_required": "Review packaging artwork for all SanDisk products distributed in France to verify valid Triman logo, separation symbols (Bac Jaune sorting instructions), and Eco-Emballages producer ID.",
        "status": "Active Customs Enforcement",
        "source": "French Ministry of Ecological Transition / DGCCRF",
        "detailed_summary": "Under Article L. 541-9-3 of the French Environmental Code and Decree No. 2021-835 issued under the AGEC Law (Anti-Waste for a Circular Economy), any consumer product subject to Extended Producer Responsibility (EPR) distributed in France must display the standardized Triman logo accompanied by the 'Info-tri' waste sorting signage. For storage hardware (flash cards, SSDs, USB drives), this signage must explicitly decompose the packaging elements into their respective sorting streams (e.g. Cardboard box -> Bac Jaune / Yellow Sorting Bin; Plastic blister tray -> Bac Jaune / Tri de tous les emballages). If the surface area of the largest face of the packaging is under 10 cm², sorting information may be provided digitally via website, but products with package faces between 10 cm² and 20 cm² must still carry the Triman emblem physically.",
        "technical_impact": "Artwork compliance requires obtaining the official vectorized graphical charters from certified French Producer Responsibility Organizations (Citeo for packaging, Ecosystem or Ecologic for electronic hardware WEEE). Absence of the Info-tri banner triggers fines up to €3,000 for an individual and €15,000 for a legal entity per non-compliant SKU.",
        "timeline_milestones": [
            {"phase": "Publication of Decree No. 2021-835", "date": "2021-06-29", "status": "Completed"},
            {"phase": "Transition Deadline for Existing Stock Exhaustion", "date": "2023-03-09", "status": "Completed"},
            {"phase": "Active Customs (DGCCRF) Market Audits & Fines Enforced", "date": "2026-01-01", "status": "Active Enforcement"}
        ],
        "official_links": [
            {"label": "Citeo Official Info-tri Packaging Guidelines & Graphics Charter", "url": "https://www.citeo.com/info-tri"},
            {"label": "ADEME French Agency for Ecological Transition", "url": "https://www.ademe.fr/en"},
            {"label": "Legifrance Decree No. 2021-835 Full Statutory Text", "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000043714227"}
        ],
        "compliance_checklist": [
            "Verify presence of Triman logo and Info-tri sorting pictogram on outer retail cardboard and plastic blisters",
            "Confirm corporate Unique Identification Number (Identifiant Unique - IDU) issued by ADEME is displayed on invoices",
            "Audit packaging size; ensure products with packaging face > 20 cm² carry full physical Info-tri artwork",
            "Submit annual packaging tonnage declarations to Citeo / Adelphe before statutory deadlines"
        ]
    },
    {
        "id": "ALERT-ENV-04",
        "title": "Italy Legislative Decree 116/2020 — Mandatory Alphanumeric Packaging Material Identification Coding",
        "region": "Europe & Eurasia",
        "country": "Italy",
        "standard": "Legislative Decree 116/2020 (Decision 129/97/EC Material Coding)",
        "severity": "Warning",
        "effective_date": "Enforced",
        "affected_categories": ["sd_card", "micro_sd", "sd_express", "cf_card", "gaming_card", "usb_drive", "internal_ssd", "external_ssd_bus", "external_ssd_powered", "card_reader"],
        "summary": "Italian environmental law strictly mandates alphanumeric material identification coding in accordance with Decision 129/97/EC on all packaging components (e.g. PAP 20, PAP 21, PET 1, LDPE 4) plus consumer collection guidance in Italian.",
        "action_required": "Ensure all product packaging intended for the Italian market incorporates statutory material codes (e.g. 'Scatola: PAP 21 - Carta', 'Blister: PET 1 - Plastica', 'Raccolta differenziata').",
        "status": "Active Legal Enforcement",
        "source": "Italian Ministry of Environment and Energy Security (MASE) / CONAI",
        "detailed_summary": "Legislative Decree No. 116 of 3 September 2020, implementing European Directives (EU) 2018/851 on waste and (EU) 2018/852 on packaging waste, mandates comprehensive environmental labeling on all packaging released for consumption in Italy. All primary, secondary, and tertiary packaging must carry the alphanumeric material identification code established by Commission Decision 129/97/EC. For consumer packaging (B2C), the labeling must also clearly identify the material family (e.g. Carta, Plastica) and instruct the consumer on the correct waste collection stream ('Raccolta differenziata: Verifica le disposizioni del tuo Comune'). Non-compliant packaging faces severe administrative financial penalties ranging from €5,200 to €40,000 per violation.",
        "technical_impact": "Each separate separable component of the drive packaging must be labeled individually. For example, if an SSD package consists of a printed cardboard outer box (PAP 21), a transparent thermoformed plastic insert (PET 1), and a polyethylene cable wrap (LDPE 4), each material must be identified with its specific alphanumeric code on the packaging or via an accessible Italian digital QR link.",
        "timeline_milestones": [
            {"phase": "Publication of Legislative Decree 116/2020", "date": "2020-09-03", "status": "Completed"},
            {"phase": "Suspension Period Exhausted & Entry into Force", "date": "2023-01-01", "status": "Completed"},
            {"phase": "CONAI & Customs Market Surveillance Audits Active", "date": "2026-01-01", "status": "Active Legal Enforcement"}
        ],
        "official_links": [
            {"label": "CONAI Environmental Labeling Portal (e-Label Guidance)", "url": "https://www.etichetta-conai.com/en/"},
            {"label": "Commission Decision 129/97/EC Material Identification System", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:31997D0129"},
            {"label": "Italian Ministry of Environment (MASE) Official Circular", "url": "https://www.mase.gov.it"}
        ],
        "compliance_checklist": [
            "Decompose bill of materials for drive packaging into discrete separable components",
            "Assign valid alphanumeric codes according to Decision 129/97/EC (e.g. Cardboard box: PAP 21; Tray: PET 1)",
            "Include Italian consumer disposal phrasing: 'Raccolta differenziata. Verifica le disposizioni del tuo Comune'",
            "Verify digital QR code alternative complies with CONAI guidelines if physical package area is constrained"
        ]
    },
    {
        "id": "ALERT-ENV-05",
        "title": "India E-Waste Management Rules 2022 — Mandatory CPCB EPR Producer Portal Registration & RoHS Audit",
        "region": "Asia-Pacific",
        "country": "India",
        "standard": "E-Waste (Management) Rules 2022 (CPCB Schedule II RoHS)",
        "severity": "Critical",
        "effective_date": "2026-07-01",
        "affected_categories": ["external_ssd_powered", "external_ssd_bus", "internal_ssd", "usb_drive", "enterprise_ssd"],
        "summary": "Central Pollution Control Board (CPCB) mandates all producers and importers of IT & Telecom storage equipment (Item Code ITEW) to hold valid EPR registration certificates and purchase electronic Extended Producer Responsibility credits to meet statutory recycling targets.",
        "action_required": "File annual returns on the CPCB EPR portal, purchase required EPR recycling certificates for prior year import volumes, and maintain Schedule II RoHS technical files.",
        "status": "Mandatory Annual Compliance",
        "source": "Central Pollution Control Board (CPCB) / Ministry of Environment, Forest and Climate Change (MoEFCC)",
        "detailed_summary": "The Ministry of Environment, Forest and Climate Change (MoEFCC) notified the E-Waste (Management) Rules 2022, establishing an electronic credit-based Extended Producer Responsibility (EPR) mechanism overseen by the Central Pollution Control Board (CPCB). Under Category ITEW (Information Technology and Telecommunication Equipment), manufacturers and commercial brand owners of storage units, solid-state drives, and server memory modules must register as 'Producers' on the CPCB centralized online portal. Producers are assigned statutory annual e-waste recycling targets (graduating to 70% and 80% of historical sales tonnage). To meet targets, producers must purchase EPR certificates from CPCB-registered recyclers. Import consignments without active CPCB EPR registration numbers will be blocked at Indian ports by Customs ICEGATE. In addition, Chapter V mandates adherence to Schedule II substance limits (equivalent to EU RoHS 10 substances), requiring self-declarations and component laboratory test files.",
        "technical_impact": "Non-compliance triggers Environmental Compensation charges levied on producers per ton of unfulfilled recycling targets, alongside customs holds. Manufacturers must track historical shipment weights by SKU in metric tons and upload quarterly sales data to the CPCB portal.",
        "timeline_milestones": [
            {"phase": "Notification of E-Waste (Management) Rules 2022", "date": "2022-11-02", "status": "Completed"},
            {"phase": "Online CPCB EPR Portal Launch & Registration Mandate", "date": "2023-04-01", "status": "Completed"},
            {"phase": "Statutory Target Audit & Mandatory Annual Return Filing Deadline", "date": "2026-07-01", "status": "Enforcement Cutover"}
        ],
        "official_links": [
            {"label": "CPCB Centralized EPR Portal for E-Waste", "url": "https://eprewastecpcb.in"},
            {"label": "MoEFCC Gazette Notification E-Waste Rules 2022", "url": "https://cpcb.nic.in/e-waste/"},
            {"label": "CPCB Standard Operating Procedure (SOP) for Producers", "url": "https://cpcb.nic.in/uploads/Projects/E-Waste/SOP_E_Waste_Rules_2022.pdf"}
        ],
        "compliance_checklist": [
            "Maintain valid CPCB EPR Registration Certificate on Centralized Portal",
            "Calculate annual net sales weight of storage equipment imported into India (ITEW category)",
            "Purchase authenticated EPR recycling credits from registered recyclers to satisfy 70% target",
            "Maintain Schedule II RoHS compliance declarations with ISO 17025 test reports for Lead, Cadmium, and Phthalates"
        ]
    },
    {
        "id": "ALERT-ENV-06",
        "title": "US State-Level PFAS Bans — Maine LD 1503 & Minnesota Amara's Law Prohibitions in Electronic Packaging",
        "region": "Americas",
        "country": "United States (Maine / Minnesota / California)",
        "standard": "Maine LD 1503 / Minnesota Ch. 60 (Amara's Law) / CA AB 1817",
        "severity": "Critical",
        "effective_date": "2026-01-01",
        "affected_categories": ["sd_card", "micro_sd", "sd_express", "cf_card", "gaming_card", "usb_drive", "internal_ssd", "external_ssd_bus", "external_ssd_powered", "card_reader"],
        "summary": "State laws in Maine and Minnesota prohibit the commercial sale of any product or packaging containing intentionally added PFAS chemicals. Affects thermal greases, anti-fingerprint coatings, fluoropolymer cables, and packaging moisture barriers.",
        "action_required": "Conduct vendor screening to certify zero intentionally added PFAS in all consumer packaging materials, retail boxes, and exterior enclosure surface treatments.",
        "status": "State Enforcement Active",
        "source": "Maine DEP / Minnesota Pollution Control Agency (MPCA)",
        "detailed_summary": "State legislative bodies across the United States have bypassed federal timelines by enacting direct commercial sales prohibitions on products containing intentionally added per- and polyfluoroalkyl substances (PFAS). Under Minnesota's Amara's Law (Minn. Stat. § 116.943) and Maine Public Law 2021, c. 477 (as amended by LD 1537), manufacturers are legally barred from offering for sale in those states products containing intentionally added PFAS, with early bans specifically targeting packaging, carpets, and cookware, followed by broad electronic product cutovers by 2030. California AB 1817 and AB 652 establish complementary chemical bans. Crucially for solid-state storage, fluorinated coatings, fluorinated barrier films in drive packaging, low-surface-energy surface treatments on USB shells, and PTFE-infused internal structural plastics must be tested to prove total organic fluorine (TOF) content is below statutory thresholds (typically 50-100 ppm).",
        "technical_impact": "Requires total organic fluorine (TOF) combustion ion chromatography testing (EN 14582 / ASTM D7359). Manufacturers must furnish signed Non-Use Certifications from packaging converters and substrate molders.",
        "timeline_milestones": [
            {"phase": "Enactment of Maine LD 1503 and Minnesota Amara's Law", "date": "2021-2023", "status": "Completed"},
            {"phase": "Mandatory Prohibition on PFAS in All Product Packaging Across 12+ US States", "date": "2024-01-01", "status": "Active"},
            {"phase": "Mandatory State Reporting & Electronic Component Scrutiny", "date": "2026-01-01", "status": "Active Enforcement"}
        ],
        "official_links": [
            {"label": "Maine Department of Environmental Protection (DEP) PFAS in Products Portal", "url": "https://www.maine.gov/dep/spills/topics/pfas/PFAS-products/index.html"},
            {"label": "Minnesota Pollution Control Agency (MPCA) Amara's Law Guidelines", "url": "https://www.pca.state.mn.us/air-water-land-cleanup/pfas-in-products"},
            {"label": "Toxics in Packaging Clearinghouse (TPCH) Model Legislation", "url": "https://toxicsinpackaging.org"}
        ],
        "compliance_checklist": [
            "Obtain signed certifications from box and blister tray suppliers confirming zero intentionally added PFAS",
            "Perform Total Organic Fluorine (TOF) laboratory testing on high-risk packaging barrier layers",
            "Screen thermal interface materials (TIMs) used in external SSD heatsinks for fluorinated polymers",
            "Maintain state compliance certification records ready for inspection by state Attorneys General"
        ]
    },
    {
        "id": "ALERT-ENV-07",
        "title": "EU RoHS Recast (RoHS 4) & REACH Candidate List — Restrictions on TBBP-A and MCCPs in PCBAs",
        "region": "Europe & Eurasia",
        "country": "European Union (EU 27)",
        "standard": "RoHS Recast Review (Directive 2011/65/EU Amendment) / REACH SVHC",
        "severity": "Warning",
        "effective_date": "2027-01-01",
        "affected_categories": ["sd_card", "micro_sd", "sd_express", "cf_card", "gaming_card", "usb_drive", "internal_ssd", "external_ssd_bus", "external_ssd_powered", "enterprise_ssd", "card_reader"],
        "summary": "European Commission study for RoHS review recommends restricting two key electronics industry chemicals: Tetrabromobisphenol A (TBBP-A flame retardant used in FR-4 PCB laminates) and Medium-Chain Chlorinated Paraffins (MCCPs used in cable jacketing).",
        "action_required": "Engage printed circuit board (PCB) laminate suppliers and cable assembly houses to qualify halogen-free FR-4 alternatives and non-chlorinated elastomer jackets.",
        "status": "Regulatory Impact Assessment",
        "source": "European Commission DG Environment / Oeko-Institut",
        "detailed_summary": "Under the mandatory periodic review of the EU RoHS Directive (Directive 2011/65/EU), the European Commission and technical consultants (Oeko-Institut / Fraunhofer IZM) have finalized the prioritization assessment for restricting additional hazardous substances in electrical and electronic equipment ('RoHS 4'). Among the prioritized candidate substances, two chemicals are ubiquitous in storage and computing hardware: (1) Tetrabromobisphenol A (TBBP-A, CAS 79-94-7), a brominated flame retardant reacted into epoxy resins for FR-4 printed circuit board laminates; (2) Medium-Chain Chlorinated Paraffins (MCCPs, chloroalkanes C14-C17), used as plasticizers and flame retardant additives in flexible PVC and synthetic rubber cables. Both substances are identified as Substances of Very High Concern (SVHC) under REACH due to persistent, bioaccumulative, and toxic (PBT) properties.",
        "technical_impact": "If restricted under RoHS with a typical 0.1% (1,000 ppm) maximum concentration threshold, PCB fabricators must transition to phosphorus-based or alternative halogen-free flame retardant prepregs. Cable manufacturers must transition from plasticized PVC to thermoplastic elastomers (TPE) or polyurethane (TPU) without chlorinated paraffin additives.",
        "timeline_milestones": [
            {"phase": "Oeko-Institut Pack 15 Chemical Assessment Final Report", "date": "2021-03-01", "status": "Completed"},
            {"phase": "European Commission RoHS Review Public Consultation", "date": "2024-06-30", "status": "Completed"},
            {"phase": "Draft Delegated Directive for Substance Inclusion", "date": "2026-06-30", "status": "Upcoming"},
            {"phase": "Earliest Enforcement Date with Typical 24-Month Transition Window", "date": "2027-01-01", "status": "Anticipated Cutover"}
        ],
        "official_links": [
            {"label": "European Commission RoHS Directive Evaluation & Review", "url": "https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en"},
            {"label": "ECHA Candidate List of Substances of Very High Concern (SVHC)", "url": "https://echa.europa.eu/candidate-list-table"},
            {"label": "Oeko-Institut RoHS Substance Review Study Portal", "url": "https://rohs.oeko.info"}
        ],
        "compliance_checklist": [
            "Conduct chemical audit of FR-4 printed circuit board laminate specifications with fab houses",
            "Evaluate halogen-free laminate alternatives (e.g. DOPO-based resin chemistries) for SSD PCBAs",
            "Screen USB-C interface cable jackets for medium-chain chlorinated paraffins (MCCPs)",
            "Verify all components on active BOM comply with REACH SVHC Candidate List (< 0.1% w/w threshold)"
        ]
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
        "standard": "IS/IEC 62368-1:2023 (Migrated from IS 13252)",
        "issuing_body": "Bureau of Indian Standards (MeitY)",
        "product_id": "PROD-009",
        "product_name": "SanDisk Professional G-DRIVE Enterprise Desktop (18TB)",
        "country_coverage": "India",
        "issue_date": "2024-11-20",
        "expiry_date": "2026-11-19",
        "status": "Valid",
        "document_type": "BIS Registration Certificate",
        "notes": "Migrated to IS/IEC 62368-1:2023 ahead of the Nov 1, 2028 mandatory deadline via AIR."
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

# ==========================================
# 7. PRODUCT-BASED TESTING VS DOCUMENT MATRIX ENGINE
# ==========================================
def get_country_product_requirement(country_code, category_id):
    """
    Evaluates whether a specific product category in a given country requires:
    - Testing Required (In-Country Lab Testing)
    - Document Required (CB Scheme / National Certification Filing)
    - Supplier Declaration (SDoC / DoC)
    - Exempt / Standard Customs
    """
    country = COUNTRIES_DB.get(country_code.upper())
    if not country:
        return None

    cat = PRODUCT_CATEGORIES.get(category_id)
    cat_id = category_id if cat else 'all'
    code = country_code.upper()
    c_name = country.get('name', code)
    auth = country.get('authority', 'National Authority')
    marks = country.get('marks', [])
    primary_mark = marks[0] if marks else 'National Mark'
    nat_safety = country.get('safety_std', 'IEC 62368-1')
    nat_emc = country.get('emc_std', 'CISPR 32 Class B')
    nat_env = country.get('env_std', 'RoHS / REACH')
    bloc = country.get('bloc', '')
    is_eu = "EU" in bloc or "EEA" in bloc or country.get('region') == "Europe & Eurasia"
    cb_accepted = country.get('cb_scheme_accepted', False)

    # -------------------------------------------------------------
    # CASE 1: External SSD (With Power Adaptor - Mains Powered)
    # -------------------------------------------------------------
    if cat_id == 'external_ssd_powered':
        in_country_testing_codes = [
            'IN', 'CN', 'JP', 'MX', 'BR', 'KR', 'AR', 'TH', 'VN', 'ID',
            'MY', 'ZA', 'RU', 'BY', 'KZ', 'AM', 'KG', 'CL', 'CO', 'IL',
            'UZ', 'TJ', 'TM', 'AZ', 'EC', 'PE', 'RS', 'UA', 'EG', 'DZ',
            'TN', 'NG', 'KE', 'GH', 'TZ', 'UG', 'CU', 'IQ'
        ]
        is_safety_exempt = False
        safety_status = "Mandatory Mains Safety"
        applicable_safety = nat_safety
        applicable_emc = nat_emc

        if code == 'KR':
            req_type = "Testing Required (In-Country Lab)"
            testing_loc = "KATS / RRA Designated Korean Lab"
            badge = "danger"
            docs = [
                "KC Safety Certificate for AC/DC Adapter (KC 62368-1 / KATS designated lab)",
                "KC Conformity Registration Certificate for Storage Unit (RRA Registration)",
                "KN 32 / KN 35 In-Country EMC Laboratory Test Report",
                "KC Regulatory Label Specification (KC Mark, Registration No. R-R-xxx, Safety ID)",
                "Korean User Manual & Instructions (Statutory Radio Waves warning notices in Korean)",
                "External Power Supply Energy Efficiency Registration (KEMCO / MEPS)",
                "Authorized Korean Importer Business License & Local Representative Agreement"
            ]
            notes = "Mandatory in-country safety testing for AC/DC power adapter at KATS-designated Korean lab and mandatory KC EMC Conformity Registration for storage unit with RRA under KN 32/35. Certificate must be held by local Korean entity prior to customs clearance."

        elif code == 'CN':
            req_type = "Testing Required (In-Country Lab)"
            testing_loc = "CQC / CNCA Accredited Lab"
            badge = "danger"
            docs = [
                "China Compulsory Certification (CCC) Certificate for Power Adapter (GB 4943.1-2022)",
                "GB/T 9254.1 (CISPR 32) In-Country EMC Test Report",
                "China RoHS SJ/T 11364 Environmental Labeling (EFUP 10/20 Logo & Hazardous Substances Table)",
                "CCC Mark on Power Supply & Drive Labeling Specification",
                "Simplified Chinese User Manual & Safety Information",
                "China Energy Label / Efficiency Test Report for Power Supply"
            ]
            notes = "Mandatory CCC certification for bundled external power adapter under GB 4943.1-2022 and in-country EMC test report under GB/T 9254.1. Factory audit required for initial CCC grant."

        elif code == 'IN':
            req_type = "Testing Required (In-Country Lab)"
            testing_loc = "NABL Accredited Lab (BIS CRS)"
            badge = "danger"
            applicable_safety = "IS/IEC 62368-1:2023 (or IS 13252 until Nov 2028)"
            applicable_emc = "IS/IEC 62368-1 / CISPR 32"
            docs = [
                "BIS CRS Registration Letter (R-number) for External Power Adaptor (IS/IEC 62368-1:2023 / IS 13252)",
                "BIS CRS Registration Letter (R-number) for External Solid State Storage Unit",
                "NABL Accredited In-Country Safety Test Report (IS/IEC 62368-1:2023 / IS 13252)",
                "BIS Standard Mark Labeling Specification (IS Number & Registration Number R-xxxxxxx)",
                "BIS Standard Migration Plan (Mandatory transition to IS/IEC 62368-1 by Nov 1, 2028)",
                "Authorized Indian Representative (AIR) Agreement & Indian Entity KYC Documents"
            ]
            notes = "MeitY and BIS have transitioned from legacy IS 13252 (Part 1):2010 [IEC 60950-1] to IS/IEC 62368-1:2023. A concurrent running period is active until 01 November 2028. Testing must be executed in an in-country NABL-accredited laboratory."

        elif code == 'JP':
            req_type = "Testing Required (In-Country Lab)"
            testing_loc = "METI Registered CAB / VCCI Lab"
            badge = "danger"
            applicable_safety = "J62368-1 (2020)"
            applicable_emc = "VCCI-CISPR 32:2016"
            docs = [
                "Diamond PSE Mark Certificate for AC Adapter (METI Registered CAB / IEC 62368-1 Appendix J)",
                "VCCI Conformity Verification Report (VCCI-CISPR 32 Class B) for Storage Drive",
                "PSE & VCCI Mark Labeling Specification",
                "Japan Energy Conservation Law (Top Runner Program) Efficiency Statement",
                "Japanese User Manual & Local Reporting Importer Notification (METI Todokede)"
            ]
            notes = "Mandatory Diamond PSE certification for external AC adapter via METI registered conformity assessment body (e.g. JET/JQA). Storage drive evaluated under VCCI-CISPR 32 Class B."

        elif code == 'TW':
            req_type = "Testing Required (In-Country Lab)"
            testing_loc = "BSMI Designated Lab"
            badge = "danger"
            applicable_safety = "CNS 15598-1:2020"
            applicable_emc = "CNS 15936:2016"
            docs = [
                "BSMI Registration of Product Certification (RPC) Certificate (CNS 15598-1:2020)",
                "CNS 15936 (CISPR 32) EMC In-Country Laboratory Test Report",
                "CNS 15663 Section 5 RoHS Table of Presence (Marking of Presence of Restricted Substances)",
                "BSMI Commodity Inspection Mark (R-number Rxxxxx)",
                "Traditional Chinese User Manual & Packaging Labeling",
                "Taiwanese Registered Importer / Local Legal Representative Agreement"
            ]
            notes = "Mandatory BSMI RPC certification covering both safety (CNS 15598-1:2020) and EMC (CNS 15936), with mandatory Taiwan RoHS declaration table (CNS 15663). Must be held by a local Taiwanese company."

        elif code == 'US':
            req_type = "Supplier Declaration (SDoC / NRTL)"
            testing_loc = "OSHA NRTL Accredited Lab"
            badge = "warning"
            docs = [
                "OSHA NRTL Safety Listing Certificate (UL 62368-1 / CSA 62368-1)",
                "FCC Part 15B Supplier's Declaration of Conformity (SDoC) Certificate & Test Report",
                "US Department of Energy (DoE) Level VI Energy Efficiency Compliance Statement (10 CFR Part 430)",
                "California Energy Commission (CEC) Title 20 Appliance Efficiency Registration",
                "EPA TSCA Section 6 Compliance Attestation",
                "cULus Listing Mark on Product & Adapter Label"
            ]
            notes = "Mains power adapter requires OSHA NRTL certification (cULus) and mandatory US DoE Level VI energy efficiency verification. Storage drive evaluated under FCC Part 15B SDoC."

        elif is_eu or code in ['IS', 'NO', 'CH', 'LI']:
            req_type = "Document Required (CB Scheme / CE)"
            testing_loc = "Any ISO 17025 / CB Accredited Lab (Overseas)"
            badge = "warning"
            docs = [
                "EU Declaration of Conformity (DoC) covering LVD (2014/35/EU) and EMCD (2014/30/EU)",
                "IECEE CB Test Certificate & TRF (IEC 62368-1 3rd/4th Edition)",
                "EN 55032 / EN 55035 Class B Laboratory Test Report",
                "EU Ecodesign (ErP Directive 2009/125/EC - Regulation 2019/1782) Energy Efficiency Test Report",
                "EU RoHS 2/3 Full Material Disclosure (EN IEC 63000) & REACH SVHC Declaration",
                "CE Mark, WEEE Wheelie Bin, and EU Single Market Importer Address on Packaging"
            ]
            notes = "Complete CE conformity documentation required covering Low Voltage Directive, EMC Directive, RoHS, and ErP external power supply efficiency. IECEE CB report accepted with EU national deviations."

        elif code in in_country_testing_codes:
            req_type = "Testing Required (In-Country Lab)"
            testing_loc = f"In-Country Accredited Lab ({auth})"
            badge = "danger"
            docs = [
                f"In-Country Safety Test Report ({nat_safety})",
                f"Local EMC Test Report ({nat_emc})",
                f"{primary_mark} Certificate of Conformity / License",
                "Factory Inspection Report (CIG 021 / National Factory Audit)",
                "External Power Supply Energy Efficiency Report (DoE/ErP/MEPS)",
                f"{c_name} Local Representative / Authorized Importer Documents"
            ]
            notes = f"Mandatory in-country testing required for AC/DC power supply and storage unit under {nat_safety}. Cannot import using overseas test report alone."

        elif cb_accepted:
            req_type = "Document Required (CB Scheme)"
            testing_loc = "Any ISO 17025 / CB Accredited Lab (Overseas)"
            badge = "warning"
            docs = [
                "IECEE CB Test Certificate & TRF (IEC 62368-1)",
                f"Accredited EMC Test Report ({nat_emc})",
                f"National Certificate of Conformity ({primary_mark})",
                "External Power Supply Energy Efficiency Test Report (DoE Level VI / ErP)",
                f"{c_name} Customs Declaration & Local Importer Verification",
                "RoHS 2/3 & REACH Full Material Disclosure"
            ]
            notes = f"Accepts international IECEE CB Scheme test reports with national deviations. No local safety re-testing needed."

        else:
            req_type = "Supplier Declaration (SDoC)"
            testing_loc = "Accredited Lab / Manufacturer SDoC"
            badge = "success"
            docs = [
                f"Supplier Declaration of Conformity ({primary_mark})",
                f"Safety Test Report ({nat_safety})",
                f"EMC Class B Test Report ({nat_emc})",
                "External Power Supply Energy Efficiency Attestation",
                "RoHS / Environmental Compliance Declaration"
            ]
            notes = f"Standard manufacturer declaration of conformity and technical construction file under {nat_safety}."

    # -------------------------------------------------------------
    # CASE 2: Active Bus-Powered Peripherals (External SSD Bus, Card Reader, USB Flash Drive)
    # -------------------------------------------------------------
    elif cat_id in ['external_ssd_bus', 'card_reader', 'usb_drive']:
        is_safety_exempt = True
        safety_status = "Exempt (SELV / Class III)"
        applicable_safety = "Exempt (SELV / Class III - No Mains Safety)"
        applicable_emc = f"{nat_emc} (Class B)"

        if code == 'KR':
            req_type = "Document Required (KC Registration)"
            testing_loc = "RRA Designated / Accredited MRA Lab"
            badge = "warning"
            docs = [
                "KC Conformity Registration Certificate (RRA Radio Equipment Registration)",
                "KN 32 / KN 35 Accredited EMC Laboratory Test Report",
                "KC Regulatory Label Specification (KC Mark emblem, Registration No. R-R-xxx-xxxxxx, Model, Origin)",
                "Korean User Manual & Safety Information (Statutory Radio Waves warning statements in Korean)",
                "Authorized Korean Importer / Local Business Registration Certificate",
                "Korea RoHS / K-REACH Hazardous Substances Declaration"
            ]
            notes = "Exempt from electrical safety (KATS) as a SELV Class III bus-powered device. Mandatory KC Conformity Registration for EMC with RRA under KN 32/35. Testing at RRA-designated or recognized MRA lab required. Must be registered under Korean local business entity before customs clearance."

        elif code == 'TW':
            req_type = "Document Required (BSMI RPC/DoC)"
            testing_loc = "BSMI Designated / Accredited ISO 17025 Lab"
            badge = "warning"
            docs = [
                "BSMI Registration of Product Certification (RPC) / DoC Certificate",
                "CNS 15936 (CISPR 32) EMC Laboratory Test Report",
                "CNS 15663 Section 5 RoHS Table of Presence (Marking of Presence of Restricted Substances)",
                "BSMI Commodity Inspection Mark (R-number Rxxxxx or D-number)",
                "Traditional Chinese User Manual & Packaging Labeling",
                "Taiwanese Local Representative / Registered Importer"
            ]
            notes = "Exempt from mains safety. Mandatory BSMI EMC (CNS 15936) and RoHS declaration (CNS 15663) required by Bureau of Standards, Metrology and Inspection."

        elif code == 'JP':
            req_type = "Supplier Declaration (SDoC / VCCI)"
            testing_loc = "VCCI Registered Accredited Lab"
            badge = "success"
            docs = [
                "VCCI Conformity Verification Report (VCCI-CISPR 32 Class B)",
                "VCCI Mark Product & Packaging Labeling",
                "Japan RoHS / J-Moss Material Declaration",
                "Japanese User Guide & Customs Import Entry"
            ]
            notes = "SELV bus-powered device exempt from PSE mains electrical safety. Evaluated under VCCI-CISPR 32 Class B voluntary control rules for ITE."

        elif code == 'CN':
            req_type = "Supplier Declaration (SDoC / RoHS)"
            testing_loc = "Accredited EMC Lab"
            badge = "success"
            docs = [
                "China RoHS SJ/T 11364 Environmental Labeling (EFUP 10/20 Logo & Hazardous Substance Disclosure Table)",
                "GB/T 9254.1 (CISPR 32) EMC Test Report",
                "Simplified Chinese User Manual & Packaging Labeling",
                "China Customs Import Declaration (GACC)"
            ]
            notes = "Exempt from mandatory CCC safety certification as a bus-powered SELV device. Mandatory China RoHS labeling (EFUP logo and hazardous substance disclosure) and GB/T 9254.1 EMC compliance."

        elif code == 'US':
            req_type = "Supplier Declaration (SDoC)"
            testing_loc = "ISO 17025 Accredited EMC Lab"
            badge = "success"
            docs = [
                "FCC Part 15B Supplier's Declaration of Conformity (SDoC) Certificate",
                "ANSI C63.4 / FCC Part 15 Class B Test Report",
                "FCC Compliance Statement in User Manual",
                "EPA TSCA Section 6 Chemical Attestation",
                "California Proposition 65 Material Review"
            ]
            notes = "SELV bus-powered device exempt from OSHA NRTL mains safety. Authorized under FCC Part 15B SDoC with accredited lab test report on file."

        elif is_eu or code in ['IS', 'NO', 'CH', 'LI']:
            req_type = "Supplier Declaration (SDoC / CE)"
            testing_loc = "ISO 17025 Accredited Lab"
            badge = "success"
            docs = [
                "EU Declaration of Conformity (DoC) under EMC Directive (2014/30/EU)",
                "EN 55032 / EN 55035 Class B Laboratory Test Report",
                "EU RoHS 2/3 (Directive 2011/65/EU) Full Material Disclosure (EN IEC 63000)",
                "REACH SVHC Candidate List Chemical Attestation",
                "WEEE Wheelie Bin Symbol & National Producer Registration",
                "CE Mark & EU Importer Identification on Product Packaging"
            ]
            notes = "Exempt from Low Voltage Directive (LVD <75V DC). Requires CE Mark under EMC Directive 2014/30/EU and RoHS Directive 2011/65/EU. Technical Construction File must be maintained by EU responsible entity."

        elif code == 'GB':
            req_type = "Supplier Declaration (SDoC / UKCA)"
            testing_loc = "ISO 17025 Accredited Lab"
            badge = "success"
            docs = [
                "UK Declaration of Conformity (UKCA DoC) under Electromagnetic Compatibility Regulations 2016",
                "BS EN 55032 / BS EN 55035 Class B Test Report",
                "UK RoHS Regulations 2012 Technical Documentation (BS EN IEC 63000)",
                "UKCA Mark & UK Importer Address on Packaging"
            ]
            notes = "Exempt from Electrical Equipment (Safety) Regulations 2016 (<75V DC). Self-declaration under UKCA for EMC and UK RoHS."

        elif code in ['AU', 'NZ']:
            req_type = "Supplier Declaration (SDoC / RCM)"
            testing_loc = "Accredited EMC Lab"
            badge = "success"
            docs = [
                "ACMA Supplier Declaration of Conformity (SDoC)",
                "AS/NZS CISPR 32 Class B Test Report",
                "Regulatory Compliance Mark (RCM) on Label",
                "Australian / NZ Responsible Supplier Registration (ERAC database)"
            ]
            notes = "Exempt from electrical safety approval (SELV Class III). Authorized under ACMA EMC regulatory framework using the RCM mark."

        elif code in ['SA', 'AE']:
            req_type = "Document Required (SABER / ECAS)"
            testing_loc = "Accredited Lab (RoHS / EMC Testing)"
            badge = "warning"
            docs = [
                "SABER / ECAS Product Certificate of Conformity (PCoC)",
                "SABER Shipment Certificate of Conformity (SCoC)",
                "SASO / UAE RoHS Laboratory Test Report (IEC 62321)",
                "Arabic User Manual & Statutory Labeling",
                "Certificate of Origin"
            ]
            notes = "Exempt from electrical safety testing (SELV). Mandatory portal registration and uploaded RoHS chemical test reports."

        elif code == 'IN':
            req_type = "Supplier Declaration (SDoC) / Customs"
            testing_loc = "Accredited EMC Lab"
            badge = "success"
            docs = [
                "Customs Import Declaration & Commercial Invoice",
                "CISPR 32 / EN 55032 Class B EMC Test Report",
                "India E-Waste (Management) Rules RoHS Compliance Declaration",
                "Certificate of Origin"
            ]
            notes = "Standalone bus-powered external drives/readers are exempt from mandatory BIS CRS safety registration (provided no external AC/DC adapter is bundled). Requires customs entry and India E-Waste declaration."

        elif code == 'BR':
            req_type = "Exempt / Standard Customs"
            testing_loc = "None (SELV Exemption)"
            badge = "info"
            docs = [
                "Customs Import Declaration (DI / SISCOMEX)",
                "ANATEL Exemption Attestation (No RF/Wireless Transceiver)",
                "INMETRO Ordinance Safety Exemption Review (SELV <50V DC)",
                "Portuguese Product Identification Label",
                "Commercial Invoice & Packing List"
            ]
            notes = "Exempt from ANATEL telecommunications homologation (passive/wired USB without RF) and exempt from INMETRO electrical safety. Standard Brazilian customs entry with Portuguese statutory labeling."

        else:
            req_type = "Supplier Declaration (SDoC) / Customs"
            testing_loc = "Accredited Lab / Manufacturer SDoC"
            badge = "success" if cb_accepted else "info"
            docs = [
                f"Commercial Invoice & Customs Import Declaration ({auth})",
                f"EMC Class B Laboratory Test Report ({nat_emc})",
                f"Environmental / RoHS Chemical Attestation ({nat_env})",
                f"Manufacturer Declaration of Conformity ({primary_mark})",
                "Certificate of Origin"
            ]
            notes = f"SELV Class III bus-powered device exempt from mains electrical safety. Evaluated under EMC Class B ({nat_emc}) and national environmental rules."

    # -------------------------------------------------------------
    # CASE 3: SD Express (High-Speed PCIe / NVMe Bus-Powered)
    # -------------------------------------------------------------
    elif cat_id == 'sd_express':
        is_safety_exempt = True
        safety_status = "Exempt (SELV)"
        applicable_safety = "Exempt (SELV) - Thermal Clause 9"
        applicable_emc = f"{nat_emc} (to 6GHz)"

        if code == 'KR':
            req_type = "Testing Required (High-Speed EMC)"
            testing_loc = "RRA Designated / Local Accredited EMC Lab"
            badge = "danger"
            docs = [
                "KC Conformity Registration Certificate (RRA Radio Equipment Registration)",
                "KN 32 High-Frequency EMC Test Report up to 6GHz (PCIe clock harmonics)",
                "KN 35 Electrostatic Discharge (ESD) & Immunity Test Report",
                "KC Regulatory Label (KC Mark & Registration ID: R-R-xxx)",
                "Korean User Guide & Specification Sheet",
                "SD Association SD Express Physical & Electrical Compliance Attestation"
            ]
            notes = "High-speed PCIe bus-powered interface operates at GHz frequencies, requiring RRA KC Conformity Registration with radiated emissions evaluated up to 6GHz under KN 32. SELV safety exempt."

        elif code == 'TW':
            req_type = "Testing Required (High-Speed EMC)"
            testing_loc = "BSMI Designated EMC Lab"
            badge = "danger"
            docs = [
                "BSMI Registration of Product Certification (RPC)",
                "CNS 15936 EMC Test Report up to 6GHz (High-Frequency Radiated Emissions)",
                "CNS 15663 Section 5 RoHS Table of Presence",
                "BSMI Commodity Mark (Rxxxxx)",
                "SD Association SD Express Test Verification"
            ]
            notes = "High-speed PCIe bus-powered media tested up to 6GHz radiated emissions under BSMI CNS 15936."

        else:
            req_type = "Document Required"
            testing_loc = "Any Accredited ISO 17025 EMC Lab"
            badge = "warning"
            docs = [
                "Radiated Emissions Test Report up to 6GHz (CISPR 32 Class B)",
                "SD Association SD Express Spec Verification",
                f"EMC Test Report ({nat_emc})",
                f"RoHS / REACH Chemical Test Report ({nat_env})",
                f"Declaration of Conformity ({primary_mark})"
            ]
            notes = "Exempt from mains safety. Requires high-frequency laboratory test reports up to 6GHz (PCIe clock harmonics) and RoHS."

    # -------------------------------------------------------------
    # CASE 4: Internal SSD & Enterprise SSD (Client / Data Center Components)
    # -------------------------------------------------------------
    elif cat_id in ['internal_ssd', 'enterprise_ssd']:
        is_safety_exempt = False
        safety_status = "Component Recognition"
        applicable_safety = f"Component Level ({nat_safety})"
        applicable_emc = nat_emc

        if code == 'KR':
            req_type = "Testing Required (Component EMC)"
            testing_loc = "RRA Designated / Accredited EMC Lab"
            badge = "danger"
            docs = [
                "KC Conformity Registration Certificate (RRA Radio Equipment Registration)",
                "In-Country / MRA EMC Test Report (KN 32 Class B / Class A)",
                "UL Recognized Component Certificate (UL 62368-1 / CB Scheme TRF)",
                "KC Component Label Specification (KC Mark & ID R-R-xxx)",
                "Korea RoHS / K-REACH Chemical Substances Declaration",
                "TCG Opal / FIPS 140-3 Validation Certificate (if SED enterprise drive)"
            ]
            notes = "Internal SSD components sold as retail kits or standalone modules require KC EMC Conformity Registration with RRA under KN 32. UL 62368-1 recognized component status required for host system integration."

        elif code == 'TW':
            req_type = "Document Required (BSMI RPC/DoC)"
            testing_loc = "BSMI Accredited Lab"
            badge = "warning"
            docs = [
                "BSMI Registration Certificate / DoC",
                "CNS 15936 EMC Test Report",
                "CNS 15663 Section 5 RoHS Table of Presence",
                "UL Recognized Component Certificate"
            ]
            notes = "Component-level BSMI compliance required for standalone commercialization."

        elif cb_accepted:
            req_type = "Document Required"
            testing_loc = "Any ISO 17025 Accredited Lab (Overseas)"
            badge = "warning"
            docs = [
                "UL Recognized Component Certificate (UL 62368-1)",
                "TUV Bauart Mark / CB Component Test Report",
                f"EMC Laboratory Test Report ({nat_emc})",
                "RoHS 2/3 & REACH SVHC Declaration",
                "TCG Opal / FIPS 140-3 Validation (if SED enterprise drive)"
            ]
            notes = "Recognized as sub-assembly component. Documentation file accepted."

        else:
            req_type = "Supplier Declaration (SDoC)"
            testing_loc = "Internal / Accredited Lab"
            badge = "success"
            docs = [
                f"Declaration of Conformity ({primary_mark})",
                "Host Integration Safety & EMC File",
                "RoHS / Halogen-Free Attestation"
            ]
            notes = "Covered under host computer system conformity."

    # -------------------------------------------------------------
    # CASE 5: Passive Removable Flash Media (SD, MicroSD, CF, Gaming Card)
    # -------------------------------------------------------------
    else:
        is_safety_exempt = True
        safety_status = "Exempt (SELV / Class III)"
        applicable_safety = "Exempt (SELV / Class III - No Mains Safety)"
        applicable_emc = f"{nat_emc} (Class B)"

        if code == 'KR':
            req_type = "Supplier Declaration (SDoC) / Customs"
            testing_loc = "None (Passive Media Exemption)"
            badge = "success"
            docs = [
                "Commercial Invoice & Customs Import Declaration (Korea Customs Service - KCS)",
                "Korea RoHS / K-REACH Hazardous Chemical Compliance Declaration",
                "Korean Packaging & Identification Label (Statutory Korean label: Importer name, contact, model, origin)",
                "Manufacturer Quality & Specification Compliance Attestation (SD Association / CFA)",
                "Certificate of Origin (Korea Customs / FTA preference attestation)"
            ]
            notes = "Exempt from KC Electrical Safety (KATS) and standalone KC EMC registration (passive media under RRA Article 3 exemption rules). Korean customs strictly mandates Korean-language exterior packaging labeling (authorized importer contact, model, origin) and K-REACH/RoHS environmental compliance."

        elif code == 'JP':
            req_type = "Supplier Declaration (SDoC) / Customs"
            testing_loc = "None (Passive Media Exemption)"
            badge = "success"
            docs = [
                "Commercial Invoice & Customs Declaration",
                "VCCI Exemption Declaration (Passive Removable Media)",
                "Japan RoHS / J-Moss Chemical Attestation",
                "Japanese Packaging Label (Importer contact & Origin)"
            ]
            notes = "Exempt from METI PSE electrical safety and VCCI EMC registration. Requires Japanese packaging label and import customs clearance."

        elif code == 'CN':
            req_type = "Supplier Declaration (SDoC) / Customs"
            testing_loc = "None (SELV Exemption)"
            badge = "success"
            docs = [
                "China Customs Import Declaration (GACC)",
                "China RoHS SJ/T 11364 Environmental Labeling (EFUP 10/20 Logo & Hazardous Substance Table in Chinese)",
                "Certificate of Origin",
                "Commercial Invoice & Packing List"
            ]
            notes = "Exempt from mandatory CCC. Mandatory China RoHS labeling (EFUP logo and disclosure table in Chinese on packaging) and standard commercial import clearance."

        elif code == 'TW':
            req_type = "Supplier Declaration (SDoC) / Customs"
            testing_loc = "None (BSMI Exemption)"
            badge = "success"
            docs = [
                "Taiwan Customs Import Declaration",
                "Traditional Chinese Product Packaging Label (Importer contact & Origin)",
                "Taiwan RoHS Environmental Declaration",
                "Certificate of Origin"
            ]
            notes = "Exempt from BSMI certification. Requires Traditional Chinese product identification on retail packaging and Taiwan RoHS compliance."

        elif code == 'US':
            req_type = "Supplier Declaration (SDoC)"
            testing_loc = "None (FCC Passive Exemption)"
            badge = "success"
            docs = [
                "US Customs Commercial Invoice & Entry Summary (CBP Form 7501)",
                "FCC Exemption Declaration (47 CFR 15.103(h) Passive Storage Sub-Assembly)",
                "EPA TSCA Section 6 Chemical Compliance Attestation",
                "California Proposition 65 Material Review"
            ]
            notes = "Exempt from FCC Part 15 equipment authorization (passive sub-assembly/memory card) and exempt from OSHA NRTL safety. Standard commercial customs entry."

        elif is_eu or code in ['IS', 'NO', 'CH', 'LI']:
            req_type = "Supplier Declaration (SDoC / CE)"
            testing_loc = "None (SELV Exemption)"
            badge = "success"
            docs = [
                "EU Customs Declaration & Commercial Invoice",
                "EU RoHS 2/3 (Directive 2011/65/EU) Full Material Disclosure (EN IEC 63000)",
                "REACH SVHC Candidate List Chemical Declaration",
                "CE Mark on Retail Packaging",
                "WEEE Wheelie Bin Symbol & Producer Registration",
                "EU Importer Address on Packaging"
            ]
            notes = "Exempt from Low Voltage Directive (LVD <75V DC). Complies with EU RoHS Directive 2011/65/EU and REACH. Requires CE and WEEE marks on retail packaging and EU importer address."

        elif code == 'GB':
            req_type = "Supplier Declaration (SDoC / UKCA)"
            testing_loc = "None (SELV Exemption)"
            badge = "success"
            docs = [
                "UK Customs Import Declaration & Commercial Invoice",
                "UK RoHS Regulations 2012 Compliance Documentation",
                "UKCA Mark on Retail Packaging",
                "UK Importer Details on Packaging"
            ]
            notes = "Exempt from UK safety regulations (<75V DC). Requires UKCA packaging mark and UK RoHS compliance."

        elif code in ['SA', 'AE']:
            req_type = "Document Required (SABER / ECAS)"
            testing_loc = "Accredited Lab (RoHS Testing)"
            badge = "warning"
            docs = [
                "SABER / ECAS Product Certificate of Conformity (PCoC)",
                "SABER Shipment Certificate of Conformity (SCoC)",
                "SASO / UAE RoHS Laboratory Test Report (IEC 62321)",
                "Arabic Product Label & User Instructions",
                "Certificate of Origin"
            ]
            notes = "Exempt from electrical safety; requires mandatory SABER registration and uploaded SASO RoHS lab test reports."

        elif code == 'IN':
            req_type = "Supplier Declaration (SDoC) / Customs"
            testing_loc = "None (BIS Exemption)"
            badge = "success"
            docs = [
                "Customs Import Declaration & Commercial Invoice",
                "India E-Waste (Management) Rules RoHS Attestation",
                "BIS Exemption Attestation (Passive Removable Storage Media)",
                "Certificate of Origin"
            ]
            notes = "Exempt from mandatory BIS CRS safety registration. Standard customs clearance with India E-Waste/RoHS declaration."

        elif code == 'BR':
            req_type = "Exempt / Standard Customs"
            testing_loc = "None (SELV Exemption)"
            badge = "info"
            docs = [
                "Customs Import Declaration (DI / SISCOMEX)",
                "ANATEL Exemption Attestation (Passive Storage Media)",
                "Portuguese Packaging Label & Commercial Invoice",
                "Certificate of Origin"
            ]
            notes = "Exempt from ANATEL telecommunications homologation and INMETRO safety. Standard Brazilian commercial customs clearance."

        else:
            req_type = "Exempt / Standard Customs"
            testing_loc = "None"
            badge = "info"
            docs = [
                f"Commercial Invoice & Customs Declaration ({auth})",
                f"Environmental / RoHS Chemical Attestation ({nat_env})",
                f"{c_name} Statutory Packaging Label (Importer details & Origin)",
                "Certificate of Origin"
            ]
            notes = f"Exempt from mandatory national technical certifications (passive SELV storage media). Standard commercial customs entry with statutory packaging labeling and environmental compliance."

    return {
        'country_code': country['code'],
        'country_name': country['name'],
        'region': country['region'],
        'bloc': country.get('bloc', 'None'),
        'authority': country['authority'],
        'category_id': cat_id,
        'category_name': cat['name'] if cat else 'All Products',
        'requirement_type': req_type,
        'testing_location': testing_loc,
        'badge': badge,
        'required_documents': docs,
        'local_rep_required': country.get('local_rep_required', False),
        'lead_time': country.get('lead_time_weeks', 2),
        'marks': country.get('marks', []),
        'notes': notes,
        'is_safety_exempt': is_safety_exempt,
        'safety_status': safety_status,
        'safety_std': applicable_safety,
        'national_safety_std': nat_safety,
        'emc_std': applicable_emc,
        'env_std': nat_env,
        'rohs_std': country.get('rohs_std', nat_env),
        'pfas_std': country.get('pfas_std', 'PFAS Reporting & Screening'),
        'packaging_std': country.get('packaging_std', 'Packaging Heavy Metals & Recycled Content'),
        'epr_std': country.get('epr_std', 'WEEE / E-Waste Producer Responsibility'),
        'last_surveilled_date': country.get('last_surveilled_date'),
        'last_surveilled_pillar': country.get('last_surveilled_pillar'),
        'surveillance_source': country.get('surveillance_source')
    }

def get_product_market_breakdown(category_id):
    """
    Evaluates all 205 countries for a given product category,
    returning overall testing vs. document counts and detailed rows.
    """
    results = []
    counts = {
        'total': len(COUNTRIES_DB),
        'testing_required': 0,
        'document_required': 0,
        'sdoc_required': 0,
        'exempt': 0
    }

    for code in sorted(COUNTRIES_DB.keys(), key=lambda k: COUNTRIES_DB[k]['name']):
        rule = get_country_product_requirement(code, category_id)
        if not rule:
            continue

        req = rule['requirement_type']
        if "Testing Required" in req:
            counts['testing_required'] += 1
        elif "Document Required" in req:
            counts['document_required'] += 1
        elif "Supplier Declaration" in req:
            counts['sdoc_required'] += 1
        else:
            counts['exempt'] += 1

        results.append(rule)

    return {
        'category_id': category_id,
        'category_name': PRODUCT_CATEGORIES.get(category_id, {}).get('name', 'All Categories'),
        'summary': counts,
        'countries': results
    }

