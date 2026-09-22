"""
surveillance_data.py - static knowledge used by the surveillance engine:
monitored source gateways, storage-relevance keywords and realistic demo scenarios.
(Extracted verbatim from the original reg_surveillance.py so logic and data evolve separately.)
"""

STORAGE_RELEVANCE_KEYWORDS = [
    "recognized testing laborator", "equipment authorization", "unintentional radiator", "declaration of conformity",
    "electromagnetic", "radio frequency device", "tsca", "pfas", "per- and polyfluoroalkyl", "restriction of hazardous",
    "low voltage", "ecodesign", "cyber resilience", "product security", "e-waste", "packaging", "batteries", "wireless",
    "solid state", "ssd", "flash memory", "sd card", "microsd", "memory card",
    "usb drive", "flash drive", "storage device", "card reader", "nvme", "pcie",
    "62368", "60950", "cispr 32", "part 15", "rohs", "power adapter", "external power supply",
    "selv", "information technology equipment", "audio/video, information", "cns 15598",
    "cns 15936", "kn 32", "kn 35", "reach", "weee", "prop 65", "tbt", "hazardous substances"
]

GLOBAL_MONITORED_SOURCES = [
    {
        "id": "SRC-WTO-TBT",
        "name": "WTO ePing Technical Barriers to Trade (TBT) Global Early Warning",
        "scope": "All 205 Jurisdictions (164 Member Nations + 41 Observer/Bilateral Territories)",
        "region": "Global Clearinghouse",
        "pillars": ["Safety", "EMC", "Environmental"],
        "url": "https://epingalert.org",
        "feed_type": "api",
        "endpoint": "https://epingalert.org/api/v1/notifications?topic=electronics&scope=tbt",
        "status": "Monitored Active",
        "jurisdictions_covered": "All 205 Global Jurisdictions"
    },
    {
        "id": "SRC-IECEE-CTL",
        "name": "IECEE CB Scheme & CTL Standards Decisions",
        "scope": "54+ Member Nations & 90+ National Certification Bodies (NCBs)",
        "region": "Global Multilateral",
        "pillars": ["Safety", "EMC"],
        "url": "https://www.iecee.org",
        "feed_type": "api",
        "endpoint": "https://www.iecee.org/dyn/www/f?p=106:1:0:::::",
        "status": "Monitored Active",
        "jurisdictions_covered": "Global CB Scheme Network"
    },
    {
        "id": "SRC-EU-EURLEX",
        "name": "European Commission EUR-Lex & CENELEC (Official Journal L-Series)",
        "scope": "Europe & Eurasia (50+ Countries: EU 27, EEA/EFTA, UK, Western Balkans)",
        "region": "Europe & Eurasia",
        "pillars": ["Safety (LVD)", "EMC (EMCD)", "Environmental (RoHS/REACH/CRA)"],
        "url": "https://eur-lex.europa.eu",
        "feed_type": "rss",
        "endpoint": "https://eur-lex.europa.eu/EN/display-rss.html?rssType=OJ_L",
        "status": "Monitored Active",
        "jurisdictions_covered": "50+ European Countries"
    },
    {
        "id": "SRC-EAEU-EEC",
        "name": "Eurasian Economic Commission (EAEU Technical Regulations)",
        "scope": "Russia, Belarus, Kazakhstan, Armenia, Kyrgyzstan (TR CU 004, TR CU 020, TR EAEU 037/2016)",
        "region": "Eurasia (CIS)",
        "pillars": ["Safety", "EMC", "EAEU RoHS"],
        "url": "https://eec.eaeunion.org",
        "feed_type": "gazette_scraper",
        "endpoint": "https://eec.eaeunion.org/comission/department/deptexreg/tr/",
        "status": "Monitored Active",
        "jurisdictions_covered": "5 EAEU Member States"
    },
    {
        "id": "SRC-US-FR",
        "name": "US Federal Register - OSHA NRTL recognitions (UL/CSA 62368-1)",
        "scope": "United States & North America (FCC Part 15B, UL 62368-1, TSCA PFAS, Prop 65)",
        "region": "Americas",
        "pillars": ["Safety", "EMC", "Environmental"],
        "url": "https://www.federalregister.gov",
        "feed_type": "api",
        "endpoint": "https://www.federalregister.gov/api/v1/documents.json?per_page=20&order=newest&conditions[agencies][]=occupational-safety-and-health-administration&conditions[term]=%22nationally+recognized+testing+laboratory%22+62368",
        "status": "Monitored Active",
        "jurisdictions_covered": "United States & Territories"
    },
    {
        "id": "SRC-US-FCC",
        "name": "US Federal Register - FCC equipment authorization & Part 15 rulemaking",
        "scope": "United States (FCC Part 15B unintentional radiators, SDoC, KDB, Covered List)",
        "region": "Americas",
        "pillars": ["EMC", "Cyber"],
        "url": "https://www.fcc.gov/engineering-technology/laboratory-division",
        "feed_type": "api",
        "endpoint": "https://www.federalregister.gov/api/v1/documents.json?per_page=20&order=newest&conditions[agencies][]=federal-communications-commission&conditions[term]=%22equipment+authorization%22",
        "status": "Monitored Active",
        "jurisdictions_covered": "United States & Territories"
    },
    {
        "id": "SRC-US-EPA",
        "name": "US Federal Register - EPA TSCA chemicals & PFAS reporting",
        "scope": "United States (TSCA Section 8(a)(7) PFAS, Section 6 restrictions, Prop 65 interplay)",
        "region": "Americas",
        "pillars": ["Environmental"],
        "url": "https://www.epa.gov/assessing-and-managing-chemicals-under-tsca",
        "feed_type": "api",
        "endpoint": "https://www.federalregister.gov/api/v1/documents.json?per_page=20&order=newest&conditions[agencies][]=environmental-protection-agency&conditions[term]=PFAS+TSCA+%22electronic%22",
        "status": "Monitored Active",
        "jurisdictions_covered": "United States"
    },
    {
        "id": "SRC-COPANT-LATAM",
        "name": "Pan American Standards Commission (COPANT) & Mercosur Watcher",
        "scope": "Latin America & Caribbean (45+ Countries: Brazil ANATEL/INMETRO, Mexico NOM, Argentina, Chile, Colombia)",
        "region": "Americas",
        "pillars": ["Safety", "EMC", "Environmental"],
        "url": "https://www.copant.org",
        "feed_type": "gazette_scraper",
        "endpoint": "https://www.copant.org/index.php/en/standards",
        "status": "Monitored Active",
        "jurisdictions_covered": "45+ Pan-American Countries"
    },
    {
        "id": "SRC-IN-BIS",
        "name": "India MeitY / BIS Gazette & E-Waste Surveillance",
        "scope": "India (Compulsory Registration Scheme - IS/IEC 62368-1 & India E-Waste/RoHS)",
        "region": "Asia-Pacific",
        "pillars": ["Safety", "EMC", "Environmental (E-Waste)"],
        "url": "https://www.crsbis.in",
        "feed_type": "gazette_scraper",
        "endpoint": "https://www.crsbis.in/BIS/gazetteNotifications",
        "status": "Monitored Active",
        "jurisdictions_covered": "India (IN)"
    },
    {
        "id": "SRC-KR-RRA",
        "name": "South Korea RRA & KATS Gazette Surveillance",
        "scope": "South Korea (RRA KC Conformity Registration, KN 32/35, KC 62368-1, K-REACH)",
        "region": "Asia-Pacific",
        "pillars": ["Safety", "EMC", "Environmental (K-REACH)"],
        "url": "https://www.rra.go.kr",
        "feed_type": "gazette_scraper",
        "endpoint": "https://www.rra.go.kr/en/notice/notice_list.do",
        "status": "Monitored Active",
        "jurisdictions_covered": "South Korea (KR)"
    },
    {
        "id": "SRC-TW-BSMI",
        "name": "Taiwan BSMI Commodity Inspection Announcements",
        "scope": "Taiwan (BSMI RPC, CNS 15598-1, CNS 15936, CNS 15663 RoHS)",
        "region": "Asia-Pacific",
        "pillars": ["Safety", "EMC", "Environmental (CNS 15663)"],
        "url": "https://www.bsmi.gov.tw",
        "feed_type": "gazette_scraper",
        "endpoint": "https://www.bsmi.gov.tw/wSite/lp?ctNode=8644",
        "status": "Monitored Active",
        "jurisdictions_covered": "Taiwan (TW)"
    },
    {
        "id": "SRC-CN-SAMR",
        "name": "China SAMR / CNCA / MIIT Standards Implementation Portal",
        "scope": "China (CCC GB 4943.1-2022, GB/T 9254.1, China RoHS SJ/T 11364)",
        "region": "Asia-Pacific",
        "pillars": ["Safety (CCC)", "EMC", "China RoHS (EFUP)"],
        "url": "https://www.cnca.gov.cn",
        "feed_type": "gazette_scraper",
        "endpoint": "https://www.cnca.gov.cn/zwxx/gg/",
        "status": "Monitored Active",
        "jurisdictions_covered": "China (CN)"
    },
    {
        "id": "SRC-GSO-GULF",
        "name": "Gulf Standardization Organization (GSO) & SASO/MoIAT",
        "scope": "Middle East (7 GCC Countries: Saudi Arabia, UAE, Qatar, Kuwait, Oman, Bahrain, Yemen)",
        "region": "Middle East",
        "pillars": ["Safety (GCTS)", "EMC", "SASO / Gulf RoHS"],
        "url": "https://www.gso.org.sa",
        "feed_type": "gazette_scraper",
        "endpoint": "https://www.gso.org.sa/en/standards/",
        "status": "Monitored Active",
        "jurisdictions_covered": "7 Gulf States & Middle East"
    },
    {
        "id": "SRC-ARSO-AFRICA",
        "name": "African Organisation for Standardisation (ARSO) & National Bodies",
        "scope": "Africa (45+ Countries: South Africa SABS/ICASA, Nigeria SON, Kenya KEBS, Egypt NTRA, Ghana, Tanzania)",
        "region": "Africa",
        "pillars": ["Safety", "EMC", "Environmental / E-Waste"],
        "url": "https://www.arso-oran.org",
        "feed_type": "gazette_scraper",
        "endpoint": "https://www.arso-oran.org/harmonised-standards/",
        "status": "Monitored Active",
        "jurisdictions_covered": "45+ African Countries"
    }
]

AUTO_SIMULATED_SCENARIOS = [
    {
        "id_key": "IN-BIS-62368",
        "country_code": "IN",
        "country_name": "India",
        "authority": "Bureau of Indian Standards (BIS) / MeitY",
        "pillar": "Safety",
        "new_standard": "IS/IEC 62368-1:2023 Amendment 2",
        "deadline": "2028-11-01",
        "affected_categories": ["external_ssd_powered", "external_ssd_bus", "internal_ssd"],
        "severity": "Critical",
        "summary": "BIS Gazette Mandate: Compulsory in-country safety testing for AC/DC power adapters under IS/IEC 62368-1:2023 and updated thermal dissipation thresholds under Clause 9.",
        "action_required": "Submit bundled AC/DC power adapters for Clause 9 touch temperature & energy hazard tests in NABL lab; update BIS R-number endorsement before cutover.",
        "source_name": "MeitY Gazette Order (CRS Phase VII Enforcement)",
        "source_url": "https://www.crsbis.in/BIS/circulars/2026_62368_transition.pdf",
        "detailed_summary": "The Ministry of Electronics and Information Technology (MeitY) and the Bureau of Indian Standards (BIS) have issued an authoritative gazette notification mandating the complete transition from legacy IS 13252 (Part 1):2010 to hazard-based IS/IEC 62368-1:2023.\n\nAll external solid-state drives, USB peripherals with power supplies, and high-performance storage systems must obtain test reports from NABL-accredited Indian laboratories verifying electrical energy hazards (ES1/ES2/ES3) and touch temperatures under full operational workload.",
        "technical_impact": "• IS/IEC 62368-1:2023 Clause 5.4.1 electric shock protection.\n• Clause 9 thermal limit: Accessible external enclosure <70°C for metal, <85°C for plastic.\n• Mains adapters must hold separate BIS CRS registration under Category R-41000000.",
        "timeline_milestones": [
            {"phase": "BIS Gazette Published", "date": "2026-09-15", "status": "Active"},
            {"phase": "NABL Lab Accreditation Active", "date": "2027-01-01", "status": "Upcoming"},
            {"phase": "Mandatory IS 13252 Sunset", "date": "2028-11-01", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "Bureau of Indian Standards (BIS) Official CRS Portal", "url": "https://www.crsbis.in/BIS/"},
            {"label": "MeitY Compulsory Registration Scheme Gazette Circular", "url": "https://www.meity.gov.in/esdm/standards"}
        ],
        "compliance_checklist": [
            "Audit active Indian R-numbers held by Authorized Indian Representative (AIR)",
            "Identify bundled AC/DC power supplies currently certified under legacy IS 13252",
            "Ship physical test samples to NABL-accredited laboratory in India for testing",
            "Submit Form I endorsement on BIS portal prior to the November 1, 2028 sunset deadline"
        ]
    },
    {
        "id_key": "EU-CRA-2024",
        "country_code": "EU",
        "country_name": "European Union",
        "authority": "European Commission / ENISA",
        "pillar": "Safety",
        "new_standard": "Regulation (EU) 2024/2847 (Cyber Resilience Act) / EN 18031",
        "deadline": "2027-12-11",
        "affected_categories": ["internal_ssd", "enterprise_ssd", "sd_express"],
        "severity": "Critical",
        "summary": "EU Cyber Resilience Act enforces mandatory signed cryptographic bootloader firmware, machine-readable SBOM (CycloneDX / SPDX), and 24h vulnerability disclosure SLA for all PCIe NVMe drives.",
        "action_required": "Implement hardware Root-of-Trust (RoT) cryptographic signature validation in firmware release pipeline and generate CycloneDX SBOM for controller firmware.",
        "source_name": "Official Journal of the European Union (OJ L 2024/2847)",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847",
        "detailed_summary": "Regulation (EU) 2024/2847 on horizontal cybersecurity requirements for products with digital elements (Cyber Resilience Act) establishes essential cybersecurity requirements for storage hardware with microcontrollers and programmable flash firmware.\n\nAll internal NVMe SSDs, Enterprise storage arrays, and SD Express cards marketed in the EU must feature cryptographic secure boot, automated vulnerability monitoring, and a Software Bill of Materials (SBOM).",
        "technical_impact": "• Annex I Essential Cybersecurity Requirements (Hardware Root of Trust & ECDSA/RSA-3072 signing).\n• Article 14 mandatory vulnerability reporting within 24 hours to ENISA CSIRT.\n• Mandatory CycloneDX or SPDX SBOM export embedded in technical documentation files.",
        "timeline_milestones": [
            {"phase": "CRA Entered into Force", "date": "2024-12-11", "status": "Completed"},
            {"phase": "Notified Bodies Operational", "date": "2026-06-11", "status": "Active"},
            {"phase": "Mandatory Full Enforcement", "date": "2027-12-11", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "EUR-Lex Official Legal Text: Regulation (EU) 2024/2847", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847"},
            {"label": "ENISA Cyber Resilience Act Standardization Request", "url": "https://www.enisa.europa.eu/topics/cybersecurity-policy/cyber-resilience-act"}
        ],
        "compliance_checklist": [
            "Enable hardware cryptographic signature verification on all controller bootloaders",
            "Generate machine-readable SBOM in CycloneDX 1.5 JSON for all shipping firmware builds",
            "Establish 24-hour vulnerability notification pipeline to European CSIRT registry",
            "Update EU Declaration of Conformity with CRA harmonized standard EN 18031"
        ]
    },
    {
        "id_key": "US-FCC-15B",
        "country_code": "US",
        "country_name": "United States",
        "authority": "Federal Communications Commission (FCC OET)",
        "pillar": "EMC",
        "new_standard": "FCC Part 15 Subpart B / ANSI C63.4a-2026",
        "deadline": "2026-12-31",
        "affected_categories": ["sd_express", "cf_card", "card_reader"],
        "severity": "Warning",
        "summary": "FCC OET Bulletin: Mandating radiated emissions measurement expansion up to 6 GHz for PCIe Gen4/Gen5 clock harmonics on external storage media and readers.",
        "action_required": "Perform 1 GHz to 6 GHz radiated emissions scans at NVLAP accredited lab; ensure Supplier's Declaration of Conformity (SDoC) includes test records retention.",
        "source_name": "FCC Office of Engineering & Technology (OET KDB 971168)",
        "source_url": "https://www.fcc.gov/engineering-technology/laboratory-division/general/equipment-authorization",
        "detailed_summary": "The FCC Office of Engineering and Technology has issued revised guidance on unintentional radiators operating with internal clocks exceeding 108 MHz, specifically covering high-speed PCIe Gen4/Gen5 storage peripherals, CFexpress cards, and USB multi-slot card readers.\n\nRadiated emission testing must be conducted up to the 5th harmonic or 6 GHz, ensuring compliance with § 15.109 Class B digital device limits.",
        "technical_impact": "• 47 CFR § 15.109 Radiated emission limits up to 6 GHz.\n• Class B limit: 54 dBµV/m at 3 meters (average) / 74 dBµV/m (peak).\n• SDoC compliance statement must be included in user manual accompanying retail packaging.",
        "timeline_milestones": [
            {"phase": "FCC OET Bulletin Released", "date": "2026-07-01", "status": "Completed"},
            {"phase": "Laboratory Guidance In Effect", "date": "2026-09-01", "status": "Active"},
            {"phase": "Mandatory SDoC Cutover", "date": "2026-12-31", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "FCC OET Equipment Authorization Guidance", "url": "https://www.fcc.gov/engineering-technology/laboratory-division/general/equipment-authorization"},
            {"label": "eCFR Title 47 Part 15 Subpart B (Digital Devices)", "url": "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-B"}
        ],
        "compliance_checklist": [
            "Perform radiated emission scans from 1 GHz to 6 GHz at NVLAP accredited 3-meter chamber",
            "Verify spread-spectrum clocking (SSC) attenuation on PCIe reference clocks",
            "Retain test report in corporate compliance repository for minimum 10 years",
            "Verify FCC Part 15 SDoC disclosure statement is printed in the product quick start guide"
        ]
    },
    {
        "id_key": "KR-RRA-EMC",
        "country_code": "KR",
        "country_name": "South Korea",
        "authority": "National Radio Research Agency (RRA) / KATS",
        "pillar": "EMC",
        "new_standard": "KS C 9832:2026 / KN 32 Class B",
        "deadline": "2026-11-15",
        "affected_categories": ["usb_drive", "external_ssd_bus"],
        "severity": "Warning",
        "summary": "RRA Korea mandates updated ESD immunity testing (KS C 9835 / Contact 4kV, Air 8kV) and verified SDoC registration for dual-connector USB Type-C flash drives.",
        "action_required": "Update KC conformity certificate filing with RRA portal and ensure KC mark and certification number are laser-etched onto the metal USB-C housing.",
        "source_name": "RRA Public Notification No. 2026-52",
        "source_url": "https://www.rra.go.kr/en/notice/view.do",
        "detailed_summary": "The National Radio Research Agency (RRA) of South Korea has issued an enforcement update to KS C 9832 (CISPR 32) and KS C 9835 (CISPR 35) covering bus-powered USB storage devices and multi-port portable flash drives.\n\nAll external drives with USB-C high-speed interfaces must undergo rigorous electrostatic discharge (ESD) immunity testing and maintain active conformity registration on the RRA portal.",
        "technical_impact": "• KS C 9832 Class B radiated & conducted emission thresholds.\n• KS C 9835 ESD: ±4 kV contact discharge / ±8 kV air discharge with no permanent data corruption.\n• KC mark and 14-character alphanumeric certificate ID must be permanently legible on product body.",
        "timeline_milestones": [
            {"phase": "RRA Gazette Published", "date": "2026-06-15", "status": "Completed"},
            {"phase": "Conformity Registration Open", "date": "2026-08-01", "status": "Active"},
            {"phase": "Customs Import Enforcement", "date": "2026-11-15", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "National Radio Research Agency (RRA) Korea Portal", "url": "https://www.rra.go.kr"},
            {"label": "Korea Agency for Technology and Standards (KATS)", "url": "https://www.kats.go.kr"}
        ],
        "compliance_checklist": [
            "Verify ESD immunity test reports meet ±4kV contact and ±8kV air requirements",
            "Update KC certification record with Korean Authorized Representative",
            "Confirm KC logo and R-R-XXX registration string is visible on product labeling",
            "Notify Korean retail distribution partners of updated certificate validity"
        ]
    },
    {
        "id_key": "SA-SASO-ROHS",
        "country_code": "SA",
        "country_name": "Saudi Arabia",
        "authority": "Saudi Standards, Metrology and Quality Organization (SASO)",
        "pillar": "Environmental",
        "new_standard": "SASO RoHS Technical Regulation M.A-172-18-04-02",
        "deadline": "2027-01-01",
        "affected_categories": ["sd_card", "micro_sd", "usb_drive"],
        "severity": "Critical",
        "summary": "SASO terminates Annex III exemption 7(c)-I for removable NAND flash packages; requires full 10-substance laboratory test report uploaded to SABER portal.",
        "action_required": "Obtain third-party IEC 62321 test reports from flash packaging suppliers and register Product Certificate of Conformity (PCoC) via SABER platform.",
        "source_name": "SASO Circular No. M.A-172 (SABER Platform Enforcement)",
        "source_url": "https://saber.sa",
        "detailed_summary": "The Saudi Standards, Metrology and Quality Organization (SASO) has announced the termination of exemption 7(c)-I regarding electrical and electronic components containing lead in glass or ceramic.\n\nAll removable memory cards (SD/MicroSD) and USB flash drives exported to the Kingdom of Saudi Arabia must prove lead levels below 0.1% (1000 ppm) via ISO 17025 accredited laboratory test reports registered on SABER.",
        "technical_impact": "• SASO RoHS restricts 10 hazardous substances (Lead, Mercury, Cadmium, CrVI, PBB, PBDE, DEHP, BBP, DBP, DIBP).\n• Elimination of exemption 7(c)-I for passive electronic components on card substrates.\n• Mandatory Product Certificate of Conformity (PCoC) and Shipment CoC (SCoC) on SABER.",
        "timeline_milestones": [
            {"phase": "SASO Technical Board Decision", "date": "2026-05-10", "status": "Completed"},
            {"phase": "SABER System Ingestion Active", "date": "2026-09-01", "status": "Active"},
            {"phase": "Full Customs Border Enforcement", "date": "2027-01-01", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "SABER Electronic Conformity Platform (Saudi Arabia)", "url": "https://saber.sa"},
            {"label": "SASO Technical Regulations Library", "url": "https://www.saso.gov.sa"}
        ],
        "compliance_checklist": [
            "Collect complete IEC 62321 test reports for all 10 RoHS substances from substrate suppliers",
            "Audit lead content in ceramic capacitors and resistor terminations on flash cards",
            "Upload technical file and accredited laboratory reports to SABER portal",
            "Generate annual SABER PCoC certificates for each affected product SKU"
        ]
    },
    {
        "id_key": "TW-BSMI-CNS15936",
        "country_code": "TW",
        "country_name": "Taiwan",
        "authority": "Bureau of Standards, Metrology and Inspection (BSMI)",
        "pillar": "EMC",
        "new_standard": "CNS 15936 (CISPR 32) & CNS 15663 Section 5",
        "deadline": "2027-03-31",
        "affected_categories": ["gaming_card", "external_ssd_bus"],
        "severity": "Warning",
        "summary": "BSMI mandates CNS 15936 for proprietary gaming expansion storage cartridges and requires QR code linking to Section 5 presence condition on retail packaging.",
        "action_required": "Renew BSMI Registration of Product Certification (RPC) under CNS 15936 and update retail packaging with Section 5 QR code.",
        "source_name": "BSMI Gazette Announcement No. 1150029",
        "source_url": "https://www.bsmi.gov.tw",
        "detailed_summary": "Taiwan's Bureau of Standards, Metrology and Inspection (BSMI) has enacted a mandatory standard cutover from legacy CNS 13438 to CNS 15936 for all external solid-state storage and dedicated gaming storage expansion media.\n\nFurthermore, all retail boxes must provide a prominent RoHS Section 5 declaration or a high-resolution QR code pointing directly to the manufacturer's Taiwanese compliance declaration webpage.",
        "technical_impact": "• CNS 15936 (CISPR 32 Edition 2.0) Class B radiated & conducted emissions.\n• CNS 15663 Section 5 'Marking of Presence' declaration for 6 restricted chemical substances.\n• BSMI R-number must appear adjacent to the BSMI Commodity Inspection Mark.",
        "timeline_milestones": [
            {"phase": "BSMI Announcement Published", "date": "2026-04-12", "status": "Completed"},
            {"phase": "Voluntary RPC Migration Window", "date": "2026-08-01", "status": "Active"},
            {"phase": "Mandatory Sunset of CNS 13438", "date": "2027-03-31", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "BSMI Taiwan Official Certification System", "url": "https://www.bsmi.gov.tw"},
            {"label": "Taiwan Standards Information Service (CNS Catalog)", "url": "https://www.cnsonline.com.tw"}
        ],
        "compliance_checklist": [
            "Test gaming expansion cards and external bus-powered SSDs to CNS 15936 at BSMI-recognized lab",
            "Prepare Taiwanese traditional Chinese Section 5 RoHS Presence Declaration Table",
            "Update artwork packaging with BSMI mark, R-number, and RoHS declaration URL/QR",
            "File certificate extension with BSMI prior to March 31, 2027"
        ]
    },
    {
        "id_key": "EU-ECHA-PFAS",
        "country_code": "EU",
        "country_name": "European Union",
        "authority": "European Chemicals Agency (ECHA) / DG GROW",
        "pillar": "Environmental",
        "new_standard": "EU RoHS 2011/65/EU + Delegated Directive 2026/PFAS",
        "deadline": "2027-06-30",
        "affected_categories": ["all_storage_categories"],
        "severity": "Critical",
        "summary": "Universal restriction on per- and polyfluoroalkyl substances (PFAS > 25 ppb) across semiconductor thermal interface materials, labels, and conformal coatings.",
        "action_required": "Audit Bill of Materials with Tier-1 and Tier-2 component suppliers; verify zero intentionally added PFAS in thermal pads and adhesive films.",
        "source_name": "Official Journal of the European Union (OJ L 2026/PFAS-RoHS)",
        "source_url": "https://echa.europa.eu/hot-topics/perfluoroalkyl-chemicals-pfas",
        "detailed_summary": "The European Commission and ECHA have finalized a landmark delegated directive adding universal per- and polyfluoroalkyl substances (PFAS) restrictions to the EU RoHS and REACH Annex XVII scope for electronic hardware.\n\nDue to extreme environmental persistence ('forever chemicals'), thermal interface materials (TIM), silicon heat spreader gap pads, and release liners used in high-capacity flash storage must not exceed 25 ppb for targeted PFAS.",
        "technical_impact": "• Universal limit of 25 ppb for any single PFAS; 250 ppb for sum of PFAS substances.\n• Applies universally across all 11 storage and memory device categories sold in the EU/EEA.\n• Mandatory full material disclosure (FMD) declaration in the EU SCIP / ECHA database.",
        "timeline_milestones": [
            {"phase": "ECHA RAC & SEAC Scientific Opinion", "date": "2026-03-20", "status": "Completed"},
            {"phase": "Delegated Directive Published", "date": "2026-07-01", "status": "Active"},
            {"phase": "Universal EU Ban & Market Enforcement", "date": "2027-06-30", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "ECHA PFAS Restriction Proposal & Consultations", "url": "https://echa.europa.eu/hot-topics/perfluoroalkyl-chemicals-pfas"},
            {"label": "EUR-Lex EU RoHS Directive Consolidated Framework", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02011L0065-20230301"}
        ],
        "compliance_checklist": [
            "Request PFAS analytical test reports (Total Fluorine TF & targeted LC/MS) from suppliers",
            "Identify thermal pad gap fillers in external SSDs and enterprise U.2/U.3 enclosures",
            "Transition to certified PFAS-free silicone or graphite thermal interface solutions",
            "Update corporate Full Material Disclosure (FMD) declarations in ECHA SCIP portal"
        ]
    },
    {
        "id_key": "JP-METI-PSE",
        "country_code": "JP",
        "country_name": "Japan",
        "authority": "Ministry of Economy, Trade and Industry (METI) / VCCI",
        "pillar": "Safety",
        "new_standard": "PSE Electrical Appliance and Material Safety Law / J62368-1",
        "deadline": "2026-11-30",
        "affected_categories": ["external_ssd_powered", "card_reader"],
        "severity": "Warning",
        "summary": "METI updates PSE circular for multi-port USB-PD desktop storage docks with power delivery exceeding 60W, requiring Diamond PSE certification for bundled power supply.",
        "action_required": "Verify Japanese importer notification (Todokede) and ensure AC adapter carries Diamond PSE mark with JET/JQA registered laboratory test report.",
        "source_name": "METI METI Notice No. 2026-104 (DENAN Law Revision)",
        "source_url": "https://www.meti.go.jp/english/policy/economy/consumer/safety/index.html",
        "detailed_summary": "Japan's Ministry of Economy, Trade and Industry (METI) has issued revised enforcement rules under the Electrical Appliance and Material Safety Act (DENAN Law) for high-power external storage docks and desktop drives.\n\nBundled AC adapters delivering higher wattage through USB-C PD must obtain Category A 'Specified Electrical Appliance' certification (Diamond PSE) issued by a registered conformity assessment body such as JET or JQA.",
        "technical_impact": "• Mandatory Diamond PSE mark for AC/DC power brick under Appendix Table 8.\n• Circle PSE or VCCI Class B declaration required for the storage docking unit.\n• Japanese domestic importer of record must submit formal notification of business commencement.",
        "timeline_milestones": [
            {"phase": "METI Ministerial Ordinance Issued", "date": "2026-05-25", "status": "Completed"},
            {"phase": "Conformity Assessment Grace Period", "date": "2026-08-01", "status": "Active"},
            {"phase": "Mandatory Customs Enforcement", "date": "2026-11-30", "status": "Enforcement Deadline"}
        ],
        "official_links": [
            {"label": "METI Japan Electrical Appliance and Material Safety Portal", "url": "https://www.meti.go.jp/english/policy/economy/consumer/safety/index.html"},
            {"label": "Japan Electrical Safety & Environment Technology Laboratories (JET)", "url": "https://www.jet.or.jp/en/"}
        ],
        "compliance_checklist": [
            "Confirm bundled 19V external power adapter holds valid Diamond PSE certificate from JET/JQA",
            "Verify Japanese importer Todokede registration has been submitted to METI Kanto bureau",
            "Ensure Diamond PSE emblem, importer business name, and rated voltage are printed on rating plate",
            "File VCCI Class B voluntary registration for multi-port docking unit"
        ]
    }
]

