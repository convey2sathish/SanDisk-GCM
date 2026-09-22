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
