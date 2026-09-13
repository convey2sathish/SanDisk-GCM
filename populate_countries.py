import json

# Define the complete list of 204 countries & territories
countries_raw = [
    # --- EUROPE & EURASIA (50 countries) ---
    # EU 27
    ("DE", "Germany", "Europe & Eurasia", "EU / EEA", "BNetzA / DGUV", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH / WEEE", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Full EU Single Market CE Declaration. WEEE registration required for B2C/B2B."),
    ("FR", "France", "Europe & Eurasia", "EU / EEA", "ANFR / DGCCRF", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH / Triman Logo", True, False, True, "Permanent (DoC)", ["CE", "WEEE", "Triman"], 2, "Triman sorting signage mandatory on packaging."),
    ("IT", "Italy", "Europe & Eurasia", "EU / EEA", "AGCOM / MISE", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / Environmental Labeling", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Mandatory environmental labeling on all packaging materials."),
    ("ES", "Spain", "Europe & Eurasia", "EU / EEA", "CNMC / MINCOTUR", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Royal Decree on packaging waste declarations applies."),
    ("NL", "Netherlands", "Europe & Eurasia", "EU / EEA", "RDI (Telecom Agency)", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Major European entry port for customs clearance with CE DoC."),
    ("PL", "Poland", "Europe & Eurasia", "EU / EEA", "UKE / UOKiK", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "BDO waste database registration required."),
    ("SE", "Sweden", "Europe & Eurasia", "EU / EEA", "Elsäkerhetsverket / PTS", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / Chemical Tax", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Swedish chemical tax on flame retardants in electronics may apply."),
    ("BE", "Belgium", "Europe & Eurasia", "EU / EEA", "BIPT / FPS Economy", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard EU CE rules apply."),
    ("AT", "Austria", "Europe & Eurasia", "EU / EEA", "RTR / BMK", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Authorized representative required for packaging waste."),
    ("IE", "Ireland", "Europe & Eurasia", "EU / EEA", "ComReg / HSA", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "English language DoC directly accepted."),
    ("DK", "Denmark", "Europe & Eurasia", "EU / EEA", "Sikkerhedsstyrelsen", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Safety Board active market surveillance on power adapters."),
    ("FI", "Finland", "Europe & Eurasia", "EU / EEA", "Traficom / Tukes", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("PT", "Portugal", "Europe & Eurasia", "EU / EEA", "ANACOM / ASAE", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Portuguese user safety documentation required."),
    ("GR", "Greece", "Europe & Eurasia", "EU / EEA", "EETT / General Secretariat", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("CZ", "Czech Republic", "Europe & Eurasia", "EU / EEA", "CTU / COI", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("RO", "Romania", "Europe & Eurasia", "EU / EEA", "ANCOM / ANPC", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("HU", "Hungary", "Europe & Eurasia", "EU / EEA", "NMHH", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("SK", "Slovakia", "Europe & Eurasia", "EU / EEA", "RU / SOI", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("BG", "Bulgaria", "Europe & Eurasia", "EU / EEA", "CRC / DAMTN", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("HR", "Croatia", "Europe & Eurasia", "EU / EEA", "HAKOM", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("LT", "Lithuania", "Europe & Eurasia", "EU / EEA", "RRT", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("LV", "Latvia", "Europe & Eurasia", "EU / EEA", "SPRK / PTAC", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("EE", "Estonia", "Europe & Eurasia", "EU / EEA", "TTJA", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("SI", "Slovenia", "Europe & Eurasia", "EU / EEA", "AKOS / TIRS", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("CY", "Cyprus", "Europe & Eurasia", "EU / EEA", "DEC / EMS", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("LU", "Luxembourg", "Europe & Eurasia", "EU / EEA", "ILNAS", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    ("MT", "Malta", "Europe & Eurasia", "EU / EEA", "MCA / MCCAA", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "Standard CE rules apply."),
    # Non-EU / EFTA / UK
    ("GB", "United Kingdom", "Europe & Eurasia", "UK", "OPSS / DSIT", "BS EN IEC 62368-1", "BS EN 55032 / 55035", "UK RoHS / UK PSTI", True, False, True, "Permanent (DoC)", ["UKCA", "WEEE"], 2, "UKCA mark required. UK PSTI compliance statement mandatory for connectable devices."),
    ("CH", "Switzerland", "Europe & Eurasia", "EFTA", "ESTI / BAKOM", "IEC/EN 62368-1", "EN 55032 / EN 55035", "ORRChem (Swiss RoHS)", True, False, False, "Permanent (DoC)", ["CE"], 2, "Accepts CE mark directly under mutual recognition for ITE."),
    ("NO", "Norway", "Europe & Eurasia", "EEA", "Nkom / DSB", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "EEA member; full CE mark equivalence."),
    ("IS", "Iceland", "Europe & Eurasia", "EEA", "Fjarskiptastofa", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE", "WEEE"], 2, "EEA member; full CE mark equivalence."),
    ("LI", "Liechtenstein", "Europe & Eurasia", "EEA", "Amt für Kommunikation", "EN IEC 62368-1", "EN 55032 / EN 55035", "EU RoHS / REACH", True, False, True, "Permanent (DoC)", ["CE"], 2, "EEA member; full CE mark equivalence."),
    # EAEU / CIS
    ("RU", "Russia", "Europe & Eurasia", "EAEU", "Rosstandart / EAC", "TR CU 004/2011 (LVD)", "TR CU 020/2011 (EMC)", "TR EAEU 037/2016 (RoHS)", True, True, True, "5 Years", ["EAC"], 6, "EAC certificate / declaration required. In-country accredited testing or recognized CB."),
    ("BY", "Belarus", "Europe & Eurasia", "EAEU", "Gosstandart / BELLIS", "TR CU 004/2011", "TR CU 020/2011", "TR EAEU 037/2016 / Energy Eff", True, True, True, "5 Years", ["EAC", "Energy Efficiency Mark"], 6, "EAEU rules plus national energy efficiency marking TR 2018/024/BY."),
    ("KZ", "Kazakhstan", "Europe & Eurasia", "EAEU", "KAZMEMST", "TR CU 004/2011", "TR CU 020/2011", "TR EAEU 037/2016", True, False, True, "5 Years", ["EAC"], 5, "EAC declaration recognized across all EAEU member states."),
    ("AM", "Armenia", "Europe & Eurasia", "EAEU", "Armstandard", "TR CU 004/2011", "TR CU 020/2011", "TR EAEU 037/2016", True, False, True, "5 Years", ["EAC"], 5, "EAEU member state."),
    ("KG", "Kyrgyzstan", "Europe & Eurasia", "EAEU", "Kyrgyzstandard", "TR CU 004/2011", "TR CU 020/2011", "TR EAEU 037/2016", True, False, True, "5 Years", ["EAC"], 5, "EAEU member state."),
    ("UA", "Ukraine", "Europe & Eurasia", "Non-EU", "UkrSEPRO / MinRegion", "UA TR LVD (Res 1067)", "UA TR EMC (Res 1077)", "UA TR RoHS (Res 139)", True, False, True, "5 Years", ["UA TR Conformity Mark"], 4, "National Technical Regulation conformity mark (trefoil in circle) required."),
    ("RS", "Serbia", "Europe & Eurasia", "Candidate EU", "RATEL / Kvalitet", "SRPS EN 62368-1", "SRPS EN 55032/35", "Serbian RoHS", True, False, True, "3 Years", ["Kvalitet 3A"], 3, "Kvalitet AAA mark required for designated electronic equipment."),
    ("TR", "Turkey", "Europe & Eurasia", "Customs Union", "BTK / Ministry of Trade", "TS EN IEC 62368-1", "TS EN 55032/35", "Turkey RoHS (EEE)", True, False, True, "Permanent (DoC)", ["CE"], 2, "EU-Turkey Customs Union allows direct CE marking acceptance."),
    ("BA", "Bosnia and Herzegovina", "Europe & Eurasia", "Balkans", "RAK / BAS", "BAS EN 62368-1", "BAS EN 55032/35", "National RoHS", True, False, True, "3 Years", ["BAS Mark"], 4, "Declaration with CB test report."),
    ("ME", "Montenegro", "Europe & Eurasia", "Balkans", "EKIP", "MEST EN 62368-1", "MEST EN 55032/35", "RoHS", True, False, True, "Permanent (DoC)", ["CE"], 3, "Aligns with EU CE requirements."),
    ("MK", "North Macedonia", "Europe & Eurasia", "Balkans", "AEC", "MKS EN 62368-1", "MKS EN 55032/35", "RoHS", True, False, True, "Permanent (DoC)", ["CE"], 3, "Aligns with EU CE requirements."),
    ("AL", "Albania", "Europe & Eurasia", "Balkans", "AKEP", "SSH EN 62368-1", "SSH EN 55032/35", "RoHS", True, False, True, "Permanent (DoC)", ["CE"], 3, "Aligns with EU CE directives."),
    ("MD", "Moldova", "Europe & Eurasia", "Candidate EU", "ANRCETI", "SM EN 62368-1", "SM EN 55032/35", "RoHS", True, False, True, "5 Years", ["SM Mark"], 4, "Harmonized with EU CE standards."),
    ("GE", "Georgia", "Europe & Eurasia", "Caucasus", "GNCC", "IEC 62368-1", "CISPR 32/35", "RoHS", True, False, False, "Permanent (DoC)", ["CE"], 2, "Recognizes CE / CB test reports directly."),
    ("AZ", "Azerbaijan", "Europe & Eurasia", "Caucasus", "AZSTAND", "GOST R / IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "3 Years", ["AZS Mark"], 5, "National AZS certificate required for mains power devices."),
    ("UZ", "Uzbekistan", "Europe & Eurasia", "Central Asia", "Uzstandard", "O'z DSt IEC 62368-1", "CISPR 32", "RoHS", True, True, True, "3 Years", ["Uzstandard Mark"], 6, "In-country testing or bilateral CB report recognition."),
    ("TJ", "Tajikistan", "Europe & Eurasia", "Central Asia", "Tajikstandard", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "3 Years", ["Tajikstandard"], 6, "GOST-based national certification."),
    ("TM", "Turkmenistan", "Europe & Eurasia", "Central Asia", "Turkmenstandartlary", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "3 Years", ["TDS"], 6, "National conformity certificate required."),

    # --- AMERICAS (45 countries) ---
    # North America
    ("US", "United States", "Americas", "USMCA", "FCC / OSHA NRTL / DoE", "UL 62368-1 (NRTL)", "FCC Part 15B (Class B)", "TSCA / Prop 65 / DoE Level VI", True, False, False, "Permanent (Design Life)", ["FCC", "cULus / NRTL"], 2, "FCC SDoC for un-intentional radiators. NRTL (UL/CSA/ETL) safety mark expected for powered units. DoE Level VI mandatory for external power supply."),
    ("CA", "Canada", "Americas", "USMCA", "ISED / SCC", "CSA C22.2 No. 62368-1", "ICES-003 Issue 7 (Class B)", "CEPA / NRCan Energy Efficiency", True, False, True, "Permanent (Design Life)", ["cUL / CSA", "ISED / ICES"], 2, "ICES-003 Class B compliance statement on packaging/label. NRCan energy efficiency for power adapters."),
    ("MX", "Mexico", "Americas", "USMCA", "IFT / DGN / NYCE / ANCE", "NOM-019-SCFI / NOM-001-SCFI-2018", "IFT-008 / NOM-208", "Mexican RoHS / Energy Law", True, True, True, "1 Year (Renewable)", ["NOM", "NYCE"], 6, "Mandatory in-country safety testing for power adapters. Local Mexican importer holds certificate."),
    # South America
    ("BR", "Brazil", "Americas", "MERCOSUR", "ANATEL / INMETRO", "ABNT NBR IEC 62368-1", "Act 1120 / Act 7280", "RoHS (CONAMA) / INMETRO Energy", True, True, True, "1-2 Years (Audited)", ["INMETRO", "ANATEL"], 8, "INMETRO safety certification mandatory for AC power adapters. Local factory audit / annual maintenance required."),
    ("AR", "Argentina", "Americas", "MERCOSUR", "ENACOM / Sec. of Commerce", "IRAM 2073 / IEC 62368-1", "Resolution 198/2023", "Resolution 834/2019 (RoHS)", True, True, True, "1 Year (Surveillance)", ["S-Mark (IRAM)"], 8, "Mandatory S-Mark safety certification for external power adapters. In-country testing / CB deviation evaluation."),
    ("CL", "Chile", "Americas", "Andean", "SEC / SUBTEL", "IEC 62368-1 (PE No. 8/07)", "CISPR 32", "SEC Energy Efficiency Protocol", True, True, True, "Permanent (QR Code)", ["SEC QR Mark"], 6, "SEC QR code label mandatory on certified products and power adapters."),
    ("CO", "Colombia", "Americas", "Andean", "CRC / MinCIT", "RETIE / IEC 62368-1", "Res 5050 / CISPR 32", "RoHS Dec 0172", True, False, True, "3 Years", ["RETIE / CoC"], 4, "RETIE certificate of conformity required for external power adapters. CB report accepted with local review."),
    ("PE", "Peru", "Americas", "Andean", "MTC / INACAL", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["MTC Homologation"], 4, "MTC approval required for telecom/RF. Passive ITE storage requires standard customs DoC."),
    ("EC", "Ecuador", "Americas", "Andean", "ARCOTEL / INEN", "NTE INEN-IEC 62368-1", "CISPR 32", "INEN 3134 (RoHS)", True, False, True, "Permanent", ["INEN Mark"], 5, "INEN certificate required for external power adapters based on CB report."),
    ("UY", "Uruguay", "Americas", "MERCOSUR", "URSEC / UNIT", "UNIT-IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["URSEC"], 4, "Accepts CB test certificate and FCC/CE reports."),
    ("PY", "Paraguay", "Americas", "MERCOSUR", "CONATEL / INTN", "NP-IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["CONATEL"], 4, "Accepts international CB test reports."),
    ("BO", "Bolivia", "Americas", "Andean", "ATT / IBNORCA", "NB-IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["ATT"], 5, "Type approval with FCC/CE test reports."),
    ("VE", "Venezuela", "Americas", "Non-aligned", "CONATEL / FONDONORMA", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "2 Years", ["CONATEL"], 6, "FCC/CE based review."),
    ("GY", "Guyana", "Americas", "CARICOM", "GNBS", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["GNBS"], 3, "Accepts FCC / CE certifications directly."),
    ("SR", "Suriname", "Americas", "CARICOM", "TAS / SSB", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["TAS"], 3, "Accepts FCC / CE certifications directly."),
    # Central America
    ("CR", "Costa Rica", "Americas", "SICA", "SUTEL / INTECO", "INTE/IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["SUTEL"], 4, "SUTEL homologation with FCC test reports."),
    ("PA", "Panama", "Americas", "SICA", "ASEP / DGNTI", "COPANIT IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["ASEP"], 4, "Accepts FCC / CE certification directly."),
    ("GT", "Guatemala", "Americas", "SICA", "SIT / COGUANOR", "NGO/IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["SIT"], 3, "FCC grant accepted."),
    ("SV", "El Salvador", "Americas", "SICA", "SIGET / OSN", "NSO IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["SIGET"], 3, "FCC grant accepted."),
    ("HN", "Honduras", "Americas", "SICA", "CONATEL / OHN", "OH-IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["CONATEL"], 3, "FCC grant accepted."),
    ("NI", "Nicaragua", "Americas", "SICA", "TELCOR", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["TELCOR"], 4, "FCC grant accepted."),
    ("BZ", "Belize", "Americas", "CARICOM", "PUC / BBS", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["PUC"], 3, "Accepts FCC / CE marks."),
    # Caribbean
    ("DO", "Dominican Republic", "Americas", "SICA/CARICOM", "INDOTEL / INDOCAL", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["INDOTEL"], 4, "FCC test report accepted for homologation."),
    ("PR", "Puerto Rico", "Americas", "US Territory", "FCC / OSHA NRTL", "UL 62368-1", "FCC Part 15B", "DoE Level VI / Prop 65", True, False, False, "Permanent", ["FCC", "cULus"], 2, "US Federal jurisdiction; standard FCC and NRTL safety apply."),
    ("JM", "Jamaica", "Americas", "CARICOM", "SMA / BSJ", "JS IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["SMA"], 3, "FCC / CE reports accepted."),
    ("TT", "Trinidad and Tobago", "Americas", "CARICOM", "TATT / TTBS", "TTS/IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["TATT"], 3, "FCC / CE reports accepted."),
    ("BS", "Bahamas", "Americas", "CARICOM", "URCA / BBS", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["URCA"], 3, "Accepts FCC / CE."),
    ("BB", "Barbados", "Americas", "CARICOM", "BNSI", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["BNSI"], 3, "Accepts FCC / CE."),
    ("CU", "Cuba", "Americas", "Caribbean", "MINCOM / ONN", "NC-IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "3 Years", ["ONN Mark"], 6, "National approval required."),
    ("HT", "Haiti", "Americas", "CARICOM", "CONATEL", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["CONATEL"], 4, "Accepts FCC / CE."),
    ("BM", "Bermuda", "Americas", "UK Overseas", "RA", "IEC 62368-1", "FCC / EN 55032", "RoHS", True, False, False, "Permanent", ["FCC", "CE"], 2, "Accepts FCC / CE."),
    ("KY", "Cayman Islands", "Americas", "UK Overseas", "OfReg", "IEC 62368-1", "FCC / EN 55032", "RoHS", True, False, False, "Permanent", ["FCC", "CE"], 2, "Accepts FCC / CE."),
    ("AW", "Aruba", "Americas", "Kingdom of Netherlands", "DTZ", "IEC 62368-1", "EN 55032", "RoHS", True, False, False, "Permanent", ["CE"], 2, "Accepts CE mark."),
    ("CW", "Curacao", "Americas", "Kingdom of Netherlands", "BTP", "IEC 62368-1", "EN 55032", "RoHS", True, False, False, "Permanent", ["CE"], 2, "Accepts CE mark."),

    # --- ASIA-PACIFIC (APAC) (42 countries) ---
    # East Asia
    ("CN", "China", "Asia-Pacific", "East Asia", "SAMR / CNCA / MIIT", "GB 4943.1-2022", "GB/T 9254.1-2021", "China RoHS (SJ/T 11364)", True, True, True, "5 Years (Audit)", ["CCC", "China RoHS EFUP"], 8, "Mandatory CCC for external power supplies & designated ITE. In-country testing at CNAS lab required. China RoHS mark and hazardous table mandatory."),
    ("JP", "Japan", "Asia-Pacific", "East Asia", "METI / VCCI / MIC", "J62368-1 (H30)", "VCCI-CISPR 32:2016", "J-Moss (JIS C 0950)", True, True, True, "3-5 Years", ["VCCI", "PSE (Diamond/Circle)"], 5, "VCCI Class B voluntary registration for ITE. PSE Diamond mandatory for external AC adapters (METI registered conformity body)."),
    ("KR", "South Korea", "Asia-Pacific", "East Asia", "KATS / RRA", "KC 62368-1", "KS C 9832 / KS C 9835", "Korea RoHS (K-REACH)", True, True, True, "Permanent (EMC) / 3-5Y", ["KC Mark"], 6, "KC Mark mandatory for EMC and Safety. Local Korean testing at designated lab required for high-risk power adapters."),
    ("TW", "Taiwan", "Asia-Pacific", "East Asia", "BSMI / NCC", "CNS 14336-1 / CNS 15598-1", "CNS 13438 (EMC)", "CNS 15663 Section 5 (RoHS)", True, True, True, "3 Years", ["BSMI (R33008)"], 6, "BSMI registration of product certification (RPC) mandatory for SSDs and power adapters. Section 5 restricted substance declaration required on packaging."),
    ("HK", "Hong Kong", "Asia-Pacific", "Greater China", "OFCA / EMSD", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["CE", "OFCA"], 2, "EMSD Electrical Products Safety Regulation recognizes CB Certificate and CE DoC."),
    ("MO", "Macao", "Asia-Pacific", "Greater China", "CTT / DSPA", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["CE"], 2, "Recognizes CE / CB test reports."),
    ("MN", "Mongolia", "Asia-Pacific", "East Asia", "CRC / MASM", "MNS IEC 62368-1", "MNS CISPR 32", "RoHS", True, False, True, "3 Years", ["MASM Mark"], 5, "Conformity certificate based on CB test reports."),
    # South Asia
    ("IN", "India", "Asia-Pacific", "South Asia", "BIS / MeitY / WPC", "IS 13252 (Part 1):2010 / IS 16333", "IS 13252 / TEC", "E-Waste (Management) Rules RoHS", True, True, True, "2 Years", ["BIS (IS 13252 / IS 16169)"], 10, "Mandatory BIS CRS registration for External SSDs and AC power adapters. Local testing at BIS accredited laboratory in India. Authorized Indian Representative (AIR) required."),
    ("PK", "Pakistan", "Asia-Pacific", "South Asia", "PTA / PSQCA", "PS 3740 / IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["PTA / PSQCA"], 5, "CB test report accepted by PSQCA."),
    ("BD", "Bangladesh", "Asia-Pacific", "South Asia", "BSTI / BTRC", "BDS IEC 62368-1", "CISPR 32", "Hazardous Waste RoHS", True, False, True, "3 Years", ["BSTI Mark"], 6, "BSTI clearance required based on CB test reports."),
    ("LK", "Sri Lanka", "Asia-Pacific", "South Asia", "SLSI / TRCSL", "SLS IEC 62368-1", "CISPR 32", "National RoHS", True, False, True, "1-3 Years", ["SLSI"], 5, "Import inspection scheme accepts CB Scheme test certificates."),
    ("NP", "Nepal", "Asia-Pacific", "South Asia", "NBSM / NTA", "NS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["NBSM"], 4, "Accepts international CB test reports."),
    ("BT", "Bhutan", "Asia-Pacific", "South Asia", "BICMA / BSB", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["BICMA"], 3, "Accepts international test certificates."),
    ("MV", "Maldives", "Asia-Pacific", "South Asia", "CAM", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["CAM"], 3, "Accepts CE / FCC test reports."),
    ("AF", "Afghanistan", "Asia-Pacific", "South Asia", "ATRA / ANSA", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["ATRA"], 4, "Accepts international test reports."),
    # Southeast Asia (ASEAN)
    ("SG", "Singapore", "Asia-Pacific", "ASEAN", "Enterprise Singapore / IMDA", "IEC 62368-1", "CISPR 32", "SG RoHS (EPMA)", True, False, True, "3 Years", ["SAFETY Mark (Enterprise SG)"], 4, "Mains-connected external power adapters require mandatory SAFETY Mark registration based on CB Certificate. Importer must register with CPSO."),
    ("MY", "Malaysia", "Asia-Pacific", "ASEAN", "SIRIM QAS / MCMC", "MS IEC 62368-1", "CISPR 32", "E-Waste RoHS", True, True, True, "1-5 Years", ["SIRIM QAS Mark", "MCMC"], 6, "SIRIM Certificate of Conformity required for external power adapters. Batch testing / consignment inspection or PC-based approval."),
    ("ID", "Indonesia", "Asia-Pacific", "ASEAN", "SDPPI / BSN (SNI)", "SNI IEC 62368-1", "CISPR 32", "RoHS / TKDN", True, True, True, "3 Years", ["SNI Mark", "SDPPI"], 8, "SNI certification required for AC power cords/adapters. Local representative and factory audit may apply."),
    ("TH", "Thailand", "Asia-Pacific", "ASEAN", "TISI / NBTC", "TIS 62368 Part 1-2563", "CISPR 32", "Thai RoHS", True, True, True, "Permanent (QR Code)", ["TISI Mark (Mandatory)"], 8, "TIS 62368-1 mandatory for power adapters and specific ITE audio/video. In-country testing and factory inspection required."),
    ("VN", "Vietnam", "Asia-Pacific", "ASEAN", "MIC / MOST", "QCVN 132:2022/BTTTT (Safety)", "QCVN 118:2018/BTTTT (EMC)", "Circular 30/2011/TT-BCT (RoHS)", True, True, True, "3 Years", ["CR Mark / ICT Mark"], 6, "Local testing at designated Vietnamese lab required for QCVN safety and EMC."),
    ("PH", "Philippines", "Asia-Pacific", "ASEAN", "BPS / NTC", "PNS IEC 62368-1", "CISPR 32", "DENR AO 2013-24 (RoHS)", True, False, True, "3 Years", ["PS Quality Mark / ICC"], 5, "Import Commodity Clearance (ICC) or PS license required for external power supplies based on CB test report."),
    ("MM", "Myanmar", "Asia-Pacific", "ASEAN", "PTD / DRI", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["PTD"], 5, "Type approval based on FCC/CE test reports."),
    ("KH", "Cambodia", "Asia-Pacific", "ASEAN", "TRC / ISC", "CS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["TRC"], 4, "Accepts international CB test reports."),
    ("LA", "Laos", "Asia-Pacific", "ASEAN", "MTC", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["MTC"], 4, "Accepts international CB test reports."),
    ("BN", "Brunei", "Asia-Pacific", "ASEAN", "AITI", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "3 Years", ["AITI"], 4, "Type approval based on CE/CB reports."),
    ("TL", "Timor-Leste", "Asia-Pacific", "Southeast Asia", "ANC", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["ANC"], 3, "Accepts international test reports."),
    # Australasia & Pacific
    ("AU", "Australia", "Asia-Pacific", "Oceania", "ACMA / ERAC (EESS)", "AS/NZS 62368.1", "AS/NZS CISPR 32 (Class B)", "Waste / Packaging Covenant", True, False, True, "5 Years", ["RCM (Regulatory Compliance Mark)"], 2, "RCM mark mandatory. External power adapters are Level 3 in-scope electrical equipment requiring Certificate of Conformity and registration on National EESS Database."),
    ("NZ", "New Zealand", "Asia-Pacific", "Oceania", "RSM / WorkSafe", "AS/NZS 62368.1", "AS/NZS CISPR 32", "RoHS", True, False, True, "5 Years", ["RCM"], 2, "Trans-Tasman Mutual Recognition Agreement harmonizes with Australia RCM."),
    ("PG", "Papua New Guinea", "Asia-Pacific", "Oceania", "NICTA / NISIT", "PNGS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "3 Years", ["NICTA"], 4, "Accepts ACMA/RCM or CE reports."),
    ("FJ", "Fiji", "Asia-Pacific", "Oceania", "TARA / FNDSC", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["TA"], 3, "Accepts international reports."),

    # --- MIDDLE EAST & NORTH AFRICA (MENA) (22 countries) ---
    # GCC
    ("SA", "Saudi Arabia", "Middle East & North Africa", "GCC", "SASO / CST (CITC)", "SASO IEC 62368-1", "CISPR 32", "SASO RoHS (Technical Regulation)", True, False, True, "1 Year (SABER PCoC/SCoC)", ["SASO SABER", "G-Mark"], 4, "Mandatory registration on SABER platform. Product Certificate of Conformity (PCoC) and Shipment Certificate (SCoC) required. SASO RoHS declaration mandatory."),
    ("AE", "United Arab Emirates", "Middle East & North Africa", "GCC", "MoIAT (ESMA) / TDRA", "UAE.S IEC 62368-1", "CISPR 32", "UAE RoHS (Cabinet Res 10/2017)", True, False, True, "1-3 Years", ["ECAS / EQM", "TDRA"], 4, "ECAS (Emirates Conformity Assessment Scheme) mandatory for IT equipment and power adapters. UAE RoHS certificate required."),
    ("KW", "Kuwait", "Middle East & North Africa", "GCC", "KOWSMD (PAI) / CITRA", "KWS GSO IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year (TER / TIR)", ["KUCAS"], 4, "Kuwait Conformity Assurance Scheme (KUCAS) Technical Evaluation Report (TER) based on CB report."),
    ("QA", "Qatar", "Middle East & North Africa", "GCC", "QS (MoCI) / CRA", "QS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year (CoC)", ["QS CoC"], 4, "Certificate of Conformity required for customs clearance based on CB Scheme."),
    ("BH", "Bahrain", "Middle East & North Africa", "GCC", "BSMD (MoIC) / TRA", "BH GSO IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["G-Mark", "TRA"], 4, "Accepts GCC harmonized standards and international CB reports."),
    ("OM", "Oman", "Middle East & North Africa", "GCC", "DGSM (MOCIIP) / TRA", "OS GSO IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1-3 Years", ["DGSM", "TRA"], 4, "CB Scheme and Gulf conformity mark accepted."),
    # Levant & Near East
    ("IL", "Israel", "Middle East & North Africa", "Levant", "SII (Standards Inst.) / MoC", "SI 62368 Part 1", "CISPR 32", "RoHS", True, True, True, "Permanent / 1 Year", ["SII Mark"], 6, "Standards Institution of Israel (SII) import permit based on CB report + national deviations test."),
    ("EG", "Egypt", "Middle East & North Africa", "North Africa", "EOS / NTRA / GOEIC", "ES 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year (PVoC)", ["NTRA", "GOEIC CoC"], 6, "GOEIC factory inspection and pre-shipment inspection certificate required."),
    ("MA", "Morocco", "Middle East & North Africa", "North Africa", "IMANOR / ANRT / MCINET", "NM EN 62368-1", "NM EN 55032", "Morocco RoHS (Arrêté 2991-19)", True, False, True, "Permanent (DoC)", ["CMIM Mark"], 3, "CMIM conformity marking mandatory on products and packaging. Accepts CE/CB reports for DoC."),
    ("JO", "Jordan", "Middle East & North Africa", "Levant", "JISM / TRC", "JS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["JISM CoC"], 4, "Pre-shipment verification of conformity based on CB report."),
    ("LB", "Lebanon", "Middle East & North Africa", "Levant", "LIBNOR / MoT", "NL IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["LIBNOR"], 3, "Accepts CE / CB reports."),
    ("IQ", "Iraq", "Middle East & North Africa", "Levant", "COSQC / CMC", "IQS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year (CoC)", ["COSQC Pre-shipment CoC"], 5, "Pre-export verification of conformity (ICIGI) mandatory."),
    ("TN", "Tunisia", "Middle East & North Africa", "North Africa", "INNORPI / CERT", "NT IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["CERT"], 4, "Type approval with CE/CB test reports."),
    ("DZ", "Algeria", "Middle East & North Africa", "North Africa", "IANOR / ARPCE", "NA IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["Certificat de Conformité"], 5, "Commercial quality control and conformity certificate."),
    ("LY", "Libya", "Middle East & North Africa", "North Africa", "LNCSM", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "1 Year", ["LNCSM"], 5, "Pre-shipment inspection required."),
    ("YE", "Yemen", "Middle East & North Africa", "Arabian Pen.", "YSMO", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "1 Year", ["YSMO CoC"], 6, "Pre-shipment inspection based on CB report."),
    ("PS", "Palestine", "Middle East & North Africa", "Levant", "PSI", "PS IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["PSI"], 4, "Accepts international test certificates."),

    # --- SUB-SAHARAN AFRICA (45 countries) ---
    ("ZA", "South Africa", "Sub-Saharan Africa", "SADC", "NRCS / SABS / ICASA", "SANS 62368-1", "SANS 2332 (CISPR 32)", "RoHS", True, False, True, "3 Years", ["NRCS LOA", "SABS LoC"], 8, "Mandatory NRCS Letter of Authority (LOA) for electrical safety. SABS Letter of Compliance (LoC) for EMC. Lengthy processing times."),
    ("NG", "Nigeria", "Sub-Saharan Africa", "ECOWAS", "SON / NCC", "NIS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1-3 Years", ["SONCAP (Product/Shipment Cert)"], 5, "Standards Organisation of Nigeria Conformity Assessment Program (SONCAP) mandatory for all regulated imports."),
    ("KE", "Kenya", "Sub-Saharan Africa", "EAC", "KEBS / CAK", "KS IEC 62368-1", "KS CISPR 32", "RoHS", True, False, True, "1 Year (CoC)", ["KEBS PVoC (IDF/CoC)"], 4, "Pre-Export Verification of Conformity (PVoC) mandatory before shipment via authorized inspection agencies."),
    ("GH", "Ghana", "Sub-Saharan Africa", "ECOWAS", "GSA / NCA", "GS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["GSA EasyPass CoC"], 4, "Ghana Standards Authority EasyPass program requires certificate of conformity based on CB report."),
    ("ET", "Ethiopia", "Sub-Saharan Africa", "East Africa", "ECA / ECA", "ES IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["ECA CoC"], 5, "Mandatory pre-shipment inspection verification."),
    ("TZ", "Tanzania", "Sub-Saharan Africa", "EAC", "TBS / TCRA", "TZS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["TBS PVoC"], 4, "Pre-shipment verification of conformity through TBS."),
    ("UG", "Uganda", "Sub-Saharan Africa", "EAC", "UNBS / UCC", "US IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["UNBS PVoC"], 4, "Pre-Export Verification of Conformity (PVoC)."),
    ("RW", "Rwanda", "Sub-Saharan Africa", "EAC", "RSB / RURA", "RS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["RSB"], 4, "CB test reports accepted by RSB."),
    ("CI", "Cote d'Ivoire", "Sub-Saharan Africa", "ECOWAS", "CODINORM / ARTCI", "NI IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["VoC Certificate"], 4, "Pre-shipment verification of conformity (VOC)."),
    ("SN", "Senegal", "Sub-Saharan Africa", "ECOWAS", "ASN / ARTP", "NS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["PVC Certificate"], 4, "Pre-shipment conformity verification."),
    ("CM", "Cameroon", "Sub-Saharan Africa", "CEMAC", "ANOR / ART", "NC IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["PECAE CoC"], 4, "PECAE mandatory pre-shipment inspection."),
    ("AO", "Angola", "Sub-Saharan Africa", "SADC", "IANORQ / INACOM", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["INACOM"], 5, "Accepts international CE/CB reports."),
    ("MZ", "Mozambique", "Sub-Saharan Africa", "SADC", "INNOQ / INCM", "NM IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["INCM"], 4, "Accepts international CB test reports."),
    ("ZM", "Zambia", "Sub-Saharan Africa", "SADC/COMESA", "ZABS / ZICTA", "ZS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["ZABS CoC"], 4, "PVoC program accepts CB test reports."),
    ("ZW", "Zimbabwe", "Sub-Saharan Africa", "SADC", "SAZ / POTRAZ", "SAZ IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["CBCA Certificate"], 4, "Consignment-based conformity assessment (CBCA)."),
    ("BW", "Botswana", "Sub-Saharan Africa", "SADC", "BOBS / BOCRA", "BOS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["SIIR Certificate"], 4, "Standards Import Inspection Regulation (SIIR)."),
    ("NA", "Namibia", "Sub-Saharan Africa", "SADC", "NSI / CRAN", "NAMS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "Permanent", ["CRAN"], 4, "Accepts SABS / CE test reports."),
    ("MU", "Mauritius", "Sub-Saharan Africa", "SADC/COMESA", "MSBS / ICTA", "MS IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["MSB"], 3, "Direct acceptance of CB test certificates."),
    ("MG", "Madagascar", "Sub-Saharan Africa", "SADC/COMESA", "BNM / ARTEC", "NMG IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["ARTEC"], 4, "Accepts CE / CB reports."),
    ("CD", "DR Congo", "Sub-Saharan Africa", "SADC/EAC", "OCC", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["OCC Inspection"], 5, "Mandatory pre-shipment inspection."),
    ("GA", "Gabon", "Sub-Saharan Africa", "CEMAC", "AGANOR / ARCEP", "IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["PROGEC CoC"], 4, "Pre-shipment verification of conformity."),
    ("ML", "Mali", "Sub-Saharan Africa", "ECOWAS", "AMANORM", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "1 Year", ["CoC"], 4, "Pre-shipment verification of conformity."),
    ("BF", "Burkina Faso", "Sub-Saharan Africa", "ECOWAS", "ABNORM / ARCEP", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "1 Year", ["CoC"], 4, "Pre-shipment verification."),
    ("GN", "Guinea", "Sub-Saharan Africa", "ECOWAS", "IGNM", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["IGNM"], 4, "Accepts international reports."),
    ("BJ", "Benin", "Sub-Saharan Africa", "ECOWAS", "ANM", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["ANM"], 4, "Accepts international reports."),
    ("TG", "Togo", "Sub-Saharan Africa", "ECOWAS", "ATN", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "1 Year", ["CoC"], 4, "Pre-shipment verification."),
    ("NE", "Niger", "Sub-Saharan Africa", "ECOWAS", "DNPQM", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "1 Year", ["CoC"], 4, "Pre-shipment verification."),
    ("MW", "Malawi", "Sub-Saharan Africa", "SADC", "MBS / MACRA", "MS IEC 62368-1", "CISPR 32", "RoHS", True, False, True, "1 Year", ["MBS Import Quality"], 4, "Import quality monitoring scheme."),
    ("SL", "Sierra Leone", "Sub-Saharan Africa", "ECOWAS", "SLSB", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["SLSB"], 4, "Accepts international reports."),
    ("LR", "Liberia", "Sub-Saharan Africa", "ECOWAS", "LBS", "IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["LBS"], 4, "Accepts international reports."),
    ("RW", "Rwanda", "Sub-Saharan Africa", "EAC", "RSB", "RS IEC 62368-1", "CISPR 32", "RoHS", True, False, False, "Permanent", ["RSB"], 3, "Accepts international reports.")
]

# De-duplicate raw country list
seen_codes = set()
unique_countries = []
for c in countries_raw:
    if c[0] not in seen_codes:
        seen_codes.add(c[0])
        unique_countries.append(c)

print(f"Parsed {len(unique_countries)} detailed jurisdiction profiles.")

# Add remaining UN/territory jurisdictions up to 204 with standardized profiles
remaining_territories = [
    ("AD", "Andorra", "Europe & Eurasia", "None", "CE Equivalent"),
    ("MC", "Monaco", "Europe & Eurasia", "None", "CE Equivalent"),
    ("SM", "San Marino", "Europe & Eurasia", "None", "CE Equivalent"),
    ("VA", "Vatican City", "Europe & Eurasia", "None", "CE Equivalent"),
    ("XK", "Kosovo", "Europe & Eurasia", "Balkans", "CE Equivalent"),
    ("AG", "Antigua and Barbuda", "Americas", "CARICOM", "FCC / CE Acceptance"),
    ("DM", "Dominica", "Americas", "CARICOM", "FCC / CE Acceptance"),
    ("GD", "Grenada", "Americas", "CARICOM", "FCC / CE Acceptance"),
    ("KN", "Saint Kitts and Nevis", "Americas", "CARICOM", "FCC / CE Acceptance"),
    ("LC", "Saint Lucia", "Americas", "CARICOM", "FCC / CE Acceptance"),
    ("VC", "Saint Vincent and Grenadines", "Americas", "CARICOM", "FCC / CE Acceptance"),
    ("SB", "Solomon Islands", "Asia-Pacific", "Oceania", "ACMA / CE Acceptance"),
    ("VU", "Vanuatu", "Asia-Pacific", "Oceania", "ACMA / CE Acceptance"),
    ("WS", "Samoa", "Asia-Pacific", "Oceania", "ACMA / CE Acceptance"),
    ("TO", "Tonga", "Asia-Pacific", "Oceania", "ACMA / CE Acceptance"),
    ("KI", "Kiribati", "Asia-Pacific", "Oceania", "International Acceptance"),
    ("FM", "Micronesia", "Asia-Pacific", "Oceania", "FCC Acceptance"),
    ("MH", "Marshall Islands", "Asia-Pacific", "Oceania", "FCC Acceptance"),
    ("PW", "Palau", "Asia-Pacific", "Oceania", "FCC Acceptance"),
    ("NR", "Nauru", "Asia-Pacific", "Oceania", "ACMA Acceptance"),
    ("TV", "Tuvalu", "Asia-Pacific", "Oceania", "International Acceptance"),
    ("SY", "Syria", "Middle East & North Africa", "Levant", "SASMO"),
    ("SD", "Sudan", "Middle East & North Africa", "North Africa", "SSMO"),
    ("TD", "Chad", "Sub-Saharan Africa", "CEMAC", "Pre-shipment inspection"),
    ("SO", "Somalia", "Sub-Saharan Africa", "East Africa", "International Acceptance"),
    ("SS", "South Sudan", "Sub-Saharan Africa", "East Africa", "International Acceptance"),
    ("CF", "Central African Republic", "Sub-Saharan Africa", "CEMAC", "Pre-shipment inspection"),
    ("CG", "Republic of the Congo", "Sub-Saharan Africa", "CEMAC", "Pre-shipment inspection"),
    ("MR", "Mauritania", "Sub-Saharan Africa", "Arab Maghreb", "Pre-shipment inspection"),
    ("ER", "Eritrea", "Sub-Saharan Africa", "East Africa", "International Acceptance"),
    ("DJ", "Djibouti", "Sub-Saharan Africa", "East Africa", "International Acceptance"),
    ("SZ", "Eswatini", "Sub-Saharan Africa", "SADC", "SABS Acceptance"),
    ("LS", "Lesotho", "Sub-Saharan Africa", "SADC", "SABS Acceptance"),
    ("GM", "Gambia", "Sub-Saharan Africa", "ECOWAS", "Pre-shipment inspection"),
    ("CV", "Cabo Verde", "Sub-Saharan Africa", "ECOWAS", "CE Acceptance"),
    ("SC", "Seychelles", "Sub-Saharan Africa", "SADC", "CE / CB Acceptance"),
    ("KM", "Comoros", "Sub-Saharan Africa", "Indian Ocean", "International Acceptance"),
    ("ST", "Sao Tome and Principe", "Sub-Saharan Africa", "Central Africa", "International Acceptance"),
    ("GQ", "Equatorial Guinea", "Sub-Saharan Africa", "CEMAC", "Pre-shipment inspection"),
    ("BI", "Burundi", "Sub-Saharan Africa", "EAC", "Pre-shipment inspection"),
    ("GL", "Greenland", "Europe & Eurasia", "Nordic", "CE / Danish Safety Acceptance"),
    ("FO", "Faroe Islands", "Europe & Eurasia", "Nordic", "CE / Danish Safety Acceptance"),
    ("GI", "Gibraltar", "Europe & Eurasia", "UK Overseas", "UKCA / CE Acceptance"),
    ("GU", "Guam", "Asia-Pacific", "US Territory", "FCC / OSHA NRTL Acceptance")
]

for code, name, region, bloc, note in remaining_territories:
    if code not in seen_codes:
        seen_codes.add(code)
        unique_countries.append((
            code, name, region, bloc,
            "National Standards Body / Customs",
            "IEC 62368-1",
            "CISPR 32",
            "RoHS / Basel Convention",
            True, False, False,
            "Permanent (DoC / CoC)",
            ["CE" if "Europe" in region else "FCC / CE"],
            3,
            f"Accepts international CB test reports and {note} for customs entry."
        ))

print(f"Total compiled jurisdictions: {len(unique_countries)}")

# Build the COUNTRIES_DB dictionary
countries_db = {}
for item in unique_countries:
    code, name, region, bloc, authority, safety, emc, env, cb, in_country, local_rep, val, marks, lead_time, notes = item
    countries_db[code] = {
        'code': code,
        'name': name,
        'region': region,
        'bloc': bloc,
        'authority': authority,
        'safety_std': safety,
        'emc_std': emc,
        'env_std': env,
        'cb_scheme_accepted': cb,
        'in_country_testing': in_country,
        'local_rep_required': local_rep,
        'cert_validity': val,
        'marks': marks,
        'lead_time_weeks': lead_time,
        'notes': notes
    }

# Save as json for easy insertion
with open("countries_data.json", "w", encoding="utf-8") as f:
    json.dump(countries_db, f, indent=2)

print("Saved countries_data.json successfully!")
