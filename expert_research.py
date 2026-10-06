"""
expert_research.py - general "Ask the Expert" regulatory research assistant (not tied to one alert).

research(question, history=None, ctx=None) -> dict
    1. Understand  - extract countries, product category, standards, pillar and intent.
    2. Internal    - requirement engine (country x category), country records, matching alerts,
                     glossary, curated alert knowledge and the built-in STANDARDS_PRIMER.
    3. Web         - 2-3 targeted DuckDuckGo queries via expert_advisor (<= 10 s total budget).
    4. Synthesize  - deterministic brief; optionally rewritten by Claude (ai_bridge) grounded
                     ONLY on the gathered material.

Everything works offline; the web step is additive and never blocks beyond its budget.
No URL is ever invented: web_sources come from live search results or the advisor's curated
authoritative fallbacks; alert links come from the alert records themselves.
"""
import datetime as _dt
import json
import re

import ai_bridge
import alert_explainer
import compliance_db as _db
import expert_advisor
import reg_surveillance

ENGINE_VERSION = "1.0.0"
MAX_QUESTION = 1000
WEB_BUDGET_S = 10.0
MAX_COUNTRIES = 4

INTENTS = ("requirements", "exemption", "standard", "deadline", "cost", "marks", "documents", "comparison", "definition", "general")

# --------------------------------------------------------------------------- entity dictionaries
# Authority / scheme / colloquial names -> ISO code ("EU" = the 27 member states as a bloc).
COUNTRY_SYNONYMS = {
    "eu": "EU", "europe": "EU", "european union": "EU", "european": "EU", "ce mark": "EU", "ce marking": "EU", "eea": "EU", "eu27": "EU", "eu 27": "EU",
    "us": "US", "usa": "US", "u.s.": "US", "united states": "US", "america": "US", "american": "US", "fcc": "US", "osha": "US", "epa": "US", "california": "US", "tsca": "US",
    "uk": "GB", "u.k.": "GB", "britain": "GB", "united kingdom": "GB", "great britain": "GB", "england": "GB", "ukca": "GB", "psti": "GB", "opss": "GB",
    "germany": "DE", "german": "DE", "france": "FR", "french": "FR", "triman": "FR", "agec": "FR", "citeo": "FR", "italy": "IT", "spain": "ES", "netherlands": "NL", "poland": "PL",
    "sweden": "SE", "belgium": "BE", "austria": "AT", "ireland": "IE", "denmark": "DK", "finland": "FI", "portugal": "PT", "greece": "GR", "czech": "CZ",
    "japan": "JP", "japanese": "JP", "vcci": "JP", "pse": "JP", "meti": "JP",
    "korea": "KR", "korean": "KR", "south korea": "KR", "kc": "KR", "kc mark": "KR", "rra": "KR", "kats": "KR", "kn 32": "KR", "kn 35": "KR",
    "taiwan": "TW", "taiwanese": "TW", "bsmi": "TW",
    "china": "CN", "chinese": "CN", "prc": "CN", "ccc": "CN", "cnca": "CN", "cqc": "CN", "samr": "CN",
    "india": "IN", "indian": "IN", "bis": "IN", "meity": "IN", "crs": "IN", "nabl": "IN",
    "brazil": "BR", "brazilian": "BR", "anatel": "BR", "inmetro": "BR",
    "mexico": "MX", "mexican": "MX", "nom": "MX", "nyce": "MX", "ance": "MX",
    "australia": "AU", "australian": "AU", "acma": "AU", "rcm": "AU", "eess": "AU", "new zealand": "NZ",
    "saudi": "SA", "saudi arabia": "SA", "ksa": "SA", "saso": "SA", "saber": "SA",
    "uae": "AE", "emirates": "AE", "dubai": "AE", "tdra": "AE", "ecas": "AE", "esma": "AE", "moiat": "AE",
    "canada": "CA", "canadian": "CA", "ised": "CA", "ices-003": "CA", "ices 003": "CA",
    "singapore": "SG", "imda": "SG", "malaysia": "MY", "sirim": "MY", "indonesia": "ID", "sdppi": "ID", "sni": "ID",
    "vietnam": "VN", "thailand": "TH", "tisi": "TH", "philippines": "PH",
    "south africa": "ZA", "sabs": "ZA", "nrcs": "ZA", "icasa": "ZA", "nigeria": "NG", "soncap": "NG", "kenya": "KE", "kebs": "KE", "egypt": "EG", "goeic": "EG", "nrta": "EG",
    "russia": "RU", "russian": "RU", "eac": "RU", "eaeu": "RU", "eurasian": "RU", "kazakhstan": "KZ", "belarus": "BY",
    "argentina": "AR", "iram": "AR", "chile": "CL", "colombia": "CO", "israel": "IL", "sii": "IL", "turkey": "TR", "turkiye": "TR", "switzerland": "CH", "norway": "NO",
}
# 2-letter tokens that are too ambiguous to read as ISO codes when they appear in a sentence.
_AMBIGUOUS_ISO = {"IS", "IN", "AS", "AT", "BE", "BY", "DO", "IT", "ME", "NO", "SO", "TO", "AM", "PM", "OR", "AN", "ON", "IF", "OF", "US", "UP", "MY", "GO", "ID", "TV", "AD", "AI", "PR", "SA", "LA", "DE", "ES", "SD", "CF", "TF", "AC", "DC", "PC", "HD", "IO", "RF", "CE", "CB", "EN", "UL", "KC"}

EU_CODES_ORDER = ["DE", "FR", "IT", "ES", "NL", "PL", "SE", "BE", "AT", "IE"]

# (regex, category_id) - first match wins; ordered specific -> generic.
CATEGORY_PATTERNS = [
    (r"bus[- ]?powered|portable ssd|external ssd|usb[- ]?c ssd|usb ssd|portable (?:hard )?drive|pocket ssd", "external_ssd_bus"),
    (r"(?:ac|power|mains|wall)[- ]?(?:adapt|supply|brick)|mains[- ]?powered|desktop (?:ssd|drive|storage|hdd|raid|das)|external desktop|with (?:an? )?adapt", "external_ssd_powered"),
    (r"sd ?express|sd 7\.|sd 8\.|sd 9\.|pcie sd", "sd_express"),
    (r"micro[- ]?sd|microsdxc|microsdhc|\btf card", "micro_sd"),
    (r"cf ?express|cfast|compact ?flash|\bcf card|\bcfx", "cf_card"),
    (r"gaming|xbox|playstation|\bps5\b|nintendo|switch (?:2 )?card|expansion card", "gaming_card"),
    (r"usb (?:flash |thumb |pen )?(?:drive|stick|key)|thumb ?drive|flash ?drive|pen ?drive|memory stick|usb memory", "usb_drive"),
    (r"\bsd card|\bsdxc|\bsdhc|\bsduc|secure digital|memory card|flash card|\bsd memory", "sd_card"),
    (r"enterprise|data ?cent(?:er|re)|server ssd|hyperscale|\bu\.2\b|\bu\.3\b|e1\.s|e3\.s|\bedsff", "enterprise_ssd"),
    (r"card ?reader|\breader\b|\bhub\b|\bdock", "card_reader"),
    (r"internal|\bm\.2\b|nvme ssd|sata ssd|client ssd|oem ssd|2\.5\"? ssd|\bnvme\b", "internal_ssd"),
    (r"\bssd\b|solid[- ]state", "external_ssd_bus"),
]
CATEGORY_SHORT = {
    "sd_card": "SD card", "micro_sd": "microSD card", "sd_express": "SD Express card", "cf_card": "CF / CFexpress card", "gaming_card": "gaming expansion card",
    "usb_drive": "USB flash drive", "internal_ssd": "internal SSD", "external_ssd_bus": "bus-powered external SSD", "external_ssd_powered": "mains-powered desktop SSD",
    "enterprise_ssd": "enterprise SSD", "card_reader": "card reader / hub",
}

_STD_RX = re.compile(
    r"(?:IS/IEC|IEC|EN(?:\s?IEC)?|UL|CSA|CISPR|KS\s?C|KN|CNS|GB/T|GB|SJ/T|AS/NZS|ABNT NBR IEC|J)\s?\d{3,6}(?:[-.]\d+)*(?::\d{4})?"
    r"|\bIS\s?13252\b|NOM-\d{3}-[A-Z]{3,5}-\d{4}|47 CFR (?:Part )?15(?:\.\d+)?|FCC Part 15[A-Z]?(?: Subpart [A-Z])?|Part 15(?: Subpart)? ?[AB]\b|ICES-?003"
    r"|Regulation \(EU\) \d{4}/\d+|Directive \d{4}/\d+/EU|\(EU\) \d{4}/\d+|TR CU \d{3}/\d{4}|10 CFR (?:Part )?430|40 CFR (?:Part )?705",
    re.I)
_NAMED_STD = [
    (r"\brohs\b", "RoHS"), (r"\breach\b|\bsvhc\b", "REACH"), (r"\bpfas\b", "PFAS"), (r"\btsca\b", "TSCA"), (r"\bweee\b", "WEEE"), (r"\bppwr\b|packaging and packaging waste", "PPWR"),
    (r"\bcra\b|cyber resilience act", "EU CRA"), (r"\bpsti\b", "UK PSTI"), (r"\berp\b|ecodesign", "ErP"), (r"\bagec\b|\btriman\b", "AGEC / Triman"), (r"\bvcci\b", "VCCI"),
    (r"\blevel vi\b|\bdoe\b", "DoE Level VI"), (r"\bprop(?:osition)? 65\b", "Prop 65"), (r"\bcb scheme\b|\bcb report\b|\bcb certificate\b", "CB Scheme"), (r"\bnrtl\b", "NRTL"),
    (r"\bsdoc\b|supplier'?s declaration", "SDoC"), (r"\bdoc\b|declaration of conformity", "DoC"), (r"\beac\b", "EAC"), (r"\bsaber\b|\bsaso\b", "SASO / SABER"), (r"\binmetro\b", "INMETRO"),
    (r"\bgpsr\b|general product safety", "GPSR"), (r"\blvd\b|low voltage directive", "LVD"), (r"\bemcd\b|emc directive", "EMCD"), (r"\bukca\b", "UKCA"), (r"\brcm\b", "RCM"),
    (r"\bkc\b", "KC"), (r"\bccc\b", "CCC"), (r"\bbis\b|\bcrs\b", "BIS CRS"), (r"\bbsmi\b", "BSMI"), (r"\bpse\b", "PSE"), (r"\bscip\b", "SCIP"), (r"\ben 18031\b", "EN 18031"),
]

PILLAR_RX = [
    ("Cyber", r"\bcyber|firmware|sbom|vulnerab|password|security update|\bcra\b|\bpsti\b|en 18031"),
    ("Environmental", r"\brohs\b|\breach\b|\bsvhc\b|\bpfas\b|\btsca\b|\bweee\b|\bppwr\b|packag|hazardous|substance|chemical|recycl|triman|\bagec\b|prop 65|\bepr\b|e-waste|lead|cadmium|phthalate"),
    ("EMC", r"\bemc\b|emission|immunity|interference|cispr|\bfcc\b|part 15|en 5503|\bkn 3|ks c 983|vcci|ices|gb/t 9254|cns 15936|class a|class b|radiated|conducted"),
    ("Safety", r"\bsafety\b|62368|60950|touch temperature|thermal|burn|shock|\bselv\b|\bes1\b|\bps1\b|mains|\blvd\b|ul 62368|gb 4943|cns 15598|is 13252|\bnrtl\b|\bpse\b|energy source"),
]

INTENT_RULES = [
    ("comparison", r"\bdifference\b|\bdiffer|\bvs\.?\b|\bversus\b|\bcompare|\bcompared\b|\bbetween\b.*\band\b"),
    ("exemption", r"\bexempt|\bexemption|\bwaive|\bnot required\b|\bdo(?:es)?n'?t need\b|\boutside (?:the )?scope\b|\bout of scope\b|\bskip (?:the )?test"),
    ("deadline", r"\bby when\b|\bdeadline|\bwhen (?:does|do|will|is|are)\b|\beffective\b|\benforce|\btimeline\b|\baffected\b|\bimpact(?:ed|s)? (?:by|our)\b|\bwhich of our\b|\bour products\b|\bgrace period\b|\btransition"),
    ("cost", r"\bcost|\bprice|\bfee\b|\bfees\b|\bhow much\b|\blead[- ]time|\bhow long\b|\bweeks\b|\bbudget\b|\bexpensive"),
    ("marks", r"\bmarks?\b|\blogo|\blabel|\bsymbol|\bemblem|\bmarking"),
    ("documents", r"\bdocument|\bpaperwork|\bcertificate|\btest report|\bdossier|\bdeclaration\b|\btechnical file|\bwhat (?:do i|should i|must i) (?:prepare|submit|file)|\bevidence\b"),
    ("standard", r"\bclause\b|\blimit\b|\bexplain\b|\bwhat is\b|\bwhat are\b|\bwhat does\b|\bedition|\bscope of\b|\bcover|\bmean"),
    ("requirements", r"\bneed|\brequire|\bmandatory|\bmust\b|\bcertif|\bapprov|\bsell|\bship|\bexport|\bimport|\bplace on the market|\blaunch|\benter|\bregist|\bhomolog|\bcomply|\bcompliant|\bwhat applies"),
]
REG_RELEVANCE_RX = re.compile(
    r"complian|regulat|certif|standard|\btest|\bmark\b|\bmarks\b|label|safety|\bemc\b|emission|immunity|rohs|reach|pfas|packag|cyber|firmware|customs|import|export|directive|\blab\b|approv|conformity|declaration|homolog|exempt|clause|requirement|\bsell\b|\bship\b|authority|register|registration|recycl|waste|hazard|substance|voltage|temperature|\bcb\b|\bdoc\b|sdoc|tariff|audit|alert|deadline|enforce|ssd|usb|sd card|memory card|flash|storage|drive",
    re.I)

# --------------------------------------------------------------------------- standards primer
# Factual, concise. "facts" are (regex, text) pairs matched against the question for the
# "Specific point" detail; keep clause numbers only where they are well established.
STANDARDS_PRIMER = {
    "iec_62368_1": {
        "title": "IEC 62368-1 - Audio/video, information and communication technology equipment: safety requirements",
        "aliases": [r"62368", r"hazard[- ]based", r"\bhbse\b", r"energy source", r"touch temperature", r"\bes1\b|\bes2\b|\bes3\b", r"\bps1\b|\bps2\b|\bps3\b", r"\bts1\b|\bts2\b"],
        "pillar": "Safety",
        "summary": "The hazard-based safety engineering (HBSE) standard for AV/ICT equipment that replaced IEC 60950-1 (ITE) and IEC 60065 (AV). Instead of prescribing constructions it classifies every energy source and requires safeguards proportionate to the class. Editions: Ed.2 (2014), Ed.3 (2018) and Ed.4 (2023); Europe adopts it as EN IEC 62368-1 (2024 for Ed.4), North America as UL/CSA 62368-1, India as IS/IEC 62368-1:2023, China's GB 4943.1-2022 and Taiwan's CNS 15598-1 are national adaptations.",
        "points": [
            "Five energy-source families, each in class 1 (not painful), 2 (painful, no injury) or 3 (injury): ES electrical, PS power/fire, MS mechanical, TS thermal, RS radiation.",
            "ES1 steady-state limits are 60 V DC / 30 V rms AC (42.4 V peak) - USB-, SD- and PCIe-powered storage devices are ES1 and in most countries outside mandatory mains-safety certification (the external power adapter, when any, is the certified item).",
            "PS1 is a power source of at most 15 W (measured after 3 s), PS2 at most 100 W, PS3 above 100 W; PS1 circuits need no fire enclosure.",
            "Clause 5 electrically-caused injury, Clause 6 electrically-caused fire, Clause 7 hazardous substances, Clause 8 mechanical, Clause 9 thermal burn injury, Clause 10 radiation.",
            "Safeguards: basic, supplemental and reinforced equipment safeguards, plus instructional (markings/manual) and behavioural safeguards for skilled/instructed persons.",
            "Certification route: IECEE CB Scheme test report (TRF) with national differences, then national marks (NRTL listing, KC, BIS, CCC for adapters, BSMI RPC).",
        ],
        "facts": [
            (r"touch temperature|\bts1\b|\bts2\b|clause 9|thermal burn|how hot|surface temperature|burn",
             "Clause 9 (thermally-caused injury) classifies accessible surfaces as TS1, TS2 or TS3 against Table 38 touch-temperature limits, which depend on the material (metal / glass-ceramic / plastic-rubber-wood) and how long the part is touched. TS1 (normal operating) limits for metal: 48 °C for handles or parts held continuously, 70 °C for external enclosure surfaces touched in normal use (80 °C glass, 95 °C plastic). TS2 limits are higher (e.g. 58 °C for metal parts held continuously) and require an instructional safeguard; anything above the TS2 limit is TS3 and needs a safeguard preventing contact. For a metal bus-powered SSD the practical target is to keep the enclosure at or below 70 °C under the worst-case sustained write workload at the rated ambient; always confirm against the Table 38 row and edition you are certifying to."),
            (r"energy source|\bes1\b|\bes2\b|\bselv\b|voltage limit|electric shock|clause 5",
             "Clause 5 defines electrical energy sources: ES1 (at most 60 V DC or 30 V rms / 42.4 V peak AC steady state, with touch-current and charge limits) is not hazardous to an ordinary person and needs no shock safeguard; ES2 is painful but not injurious and needs one basic safeguard; ES3 requires double or reinforced safeguards. SELV/Class III in IEC 60950-1 terms maps to ES1 - which is why USB, SD and PCIe bus-powered storage products are treated as low-risk."),
            (r"\bps1\b|\bps2\b|\bps3\b|fire enclosure|clause 6|power source",
             "Clause 6 (electrically-caused fire) classifies power sources: PS1 up to 15 W, PS2 up to 100 W, PS3 above 100 W (measured 3 s after the worst-case fault). PS1 circuits do not require a fire enclosure; PS2 needs one or flammability-rated materials (V-1); PS3 needs a fire enclosure. Bus-powered USB (up to 15 W on 5 V / 3 A) and SD devices are normally PS1 or PS2 depending on the USB-PD contract."),
            (r"edition|ed\.? ?4|4th|third|3rd|2023|2018|transition|withdraw",
             "Edition 3 (IEC 62368-1:2018) is the basis of EN IEC 62368-1:2020 and UL/CSA 62368-1 3rd edition; Edition 4 (IEC 62368-1:2023) is adopted in Europe as EN IEC 62368-1:2024 and by the CB Scheme. Certifiers normally allow an existing CB report to be upgraded by a gap evaluation when the construction is unchanged; Europe withdraws presumption of conformity for the superseded harmonised standard on its date of withdrawal published in the OJEU."),
        ],
    },
    "iec_60950_1": {
        "title": "IEC 60950-1 - Information technology equipment: safety (legacy)",
        "aliases": [r"60950"], "pillar": "Safety",
        "summary": "The prescriptive ITE safety standard (2nd edition 2005 + A1:2009 + A2:2013) that preceded IEC 62368-1. EN 60950-1 lost presumption of conformity under the Low Voltage Directive on 20 December 2020; UL/CSA 60950-1 reached its US/Canada effective date the same month. Still referenced in some legacy national schemes - notably India's IS 13252 (Part 1):2010 under BIS CRS, which migrates to IS/IEC 62368-1:2023.",
        "points": ["Defined SELV (safety extra-low voltage) circuits: at most 42.4 V peak / 60 V DC - the ancestor of ES1 in IEC 62368-1.", "Limited Power Source (LPS, Clause 2.5) concept maps approximately to PS2 in IEC 62368-1.", "Reports to 60950-1 are generally not accepted for new certifications; a 62368-1 delta evaluation is required."],
    },
    "cispr_32": {
        "title": "CISPR 32 - Electromagnetic compatibility of multimedia equipment: emission requirements",
        "aliases": [r"cispr ?32", r"class a vs|class b vs|class a and class b|class a or class b", r"cispr ?22"], "pillar": "EMC",
        "summary": "The international emission standard for multimedia equipment (ITE, AV, broadcast receivers) that replaced CISPR 22 and CISPR 13. It defines two classes: Class B for equipment intended for residential environments (stricter limits) and Class A for all other (commercial/industrial) environments. Adopted as EN 55032 (EU), KS C 9832 / KN 32 (Korea), CNS 15936 (Taiwan), GB/T 9254.1 (China), VCCI-CISPR 32 (Japan), AS/NZS CISPR 32 (Australia/NZ) and accepted by Canada (ICES-003).",
        "points": [
            "Class B radiated emission limits at 10 m: 30 dB(uV/m) quasi-peak 30-230 MHz and 37 dB(uV/m) 230-1000 MHz; Class A: 40 and 47 dB(uV/m) - i.e. Class A is 10 dB more lenient.",
            "Class B conducted emissions on the mains port 150 kHz-30 MHz: 66-56 dB(uV) QP (decreasing with log frequency) to 0.5 MHz, 56 dB(uV) 0.5-5 MHz, 60 dB(uV) 5-30 MHz; Class A: 79 and 73 dB(uV).",
            "Above 1 GHz (up to 6 GHz) measurements apply when the highest internal clock frequency exceeds 108 MHz - relevant to PCIe/NVMe and USB 3.x storage.",
            "Class A equipment must carry a warning that it may cause radio interference in a residential environment; consumer storage products are always Class B.",
            "Bus-powered storage devices are tested with a representative host; passive memory cards with no oscillator are generally treated as part of the host.",
        ],
        "facts": [
            (r"class a|class b",
             "Class B is for equipment that may be used in a residential (domestic) environment and is the stricter class; Class A is for commercial, light-industrial and industrial environments and its limits are about 10 dB higher. Radiated at 10 m: Class B 30 / 37 dB(uV/m) (30-230 / 230-1000 MHz) versus Class A 40 / 47 dB(uV/m). Conducted on the mains port: Class B 66-56 / 56 / 60 dB(uV) QP versus Class A 79 / 73 dB(uV). Class A products must carry the residential-interference warning statement; consumer memory cards, USB drives and portable SSDs are marketed as Class B everywhere (FCC Part 15 Class B, KC Class B, VCCI Class B)."),
        ],
    },
    "cispr_35": {
        "title": "CISPR 35 - Electromagnetic compatibility of multimedia equipment: immunity requirements",
        "aliases": [r"cispr ?35", r"cispr ?24", r"\bimmunity\b"], "pillar": "EMC",
        "summary": "The companion immunity standard to CISPR 32 (replaced CISPR 24 and CISPR 20). It applies IEC 61000-4-x basic tests (ESD -2, radiated RF -3, EFT/burst -4, surge -5, conducted RF -6, power-frequency magnetic -8, dips/interruptions -11) with performance criteria A/B/C by function. Adopted as EN 55035 (EU/UK), KS C 9835 / KN 35 (Korea) and AS/NZS CISPR 35. The US FCC has no immunity requirement.",
        "points": ["Immunity is mandatory wherever an EMC directive/act regulates immunity: EU, UK, Korea, Australia (partially), EAEU; not in the US, Canada, Japan (VCCI is emissions only).", "Storage devices are usually assessed for data-integrity performance criterion B (temporary degradation allowed, no data loss)."],
    },
    "en_55032": {"title": "EN 55032 - European adoption of CISPR 32", "aliases": [r"en ?55032"], "pillar": "EMC",
                 "summary": "EN 55032:2015 (+A11:2020, +A1:2020) is the harmonised emission standard under the EMC Directive 2014/30/EU and UK EMC Regulations 2016 for multimedia equipment. It replaced EN 55022 and EN 55013; citing it in the EU Declaration of Conformity gives presumption of conformity for emissions.",
                 "points": ["Pair with EN 55035 (immunity) and EN IEC 61000-3-2/-3-3 (harmonics/flicker) for mains-powered products.", "Class B applies to consumer storage products."]},
    "en_55035": {"title": "EN 55035 - European adoption of CISPR 35", "aliases": [r"en ?55035"], "pillar": "EMC",
                 "summary": "EN 55035:2017 (+A11:2020) is the harmonised immunity standard for multimedia equipment under the EMC Directive 2014/30/EU (replaced EN 55024 and EN 55020).",
                 "points": ["Required alongside EN 55032 for the EU/UK Declaration of Conformity of any active (bus-powered or mains-powered) storage device."]},
    "fcc_part_15b": {
        "title": "FCC 47 CFR Part 15 Subpart B - Unintentional radiators (digital devices)",
        "aliases": [r"\bfcc\b", r"part 15", r"47 cfr", r"15\.103", r"15\.107|15\.109", r"\bsdoc\b", r"ansi c63"], "pillar": "EMC",
        "summary": "US rules for digital devices that are not radio transmitters. Since 2 November 2017 the only authorisation route for unintentional radiators is the Supplier's Declaration of Conformity (SDoC, 47 CFR 2.906/2.1077): the responsible party (which must be located in the US) tests to ANSI C63.4 and keeps the test report and a compliance information statement; no FCC filing or FCC ID is needed. Certification via a Telecommunication Certification Body (TCB) is only required for intentional radiators (Wi-Fi, Bluetooth) or chosen voluntarily.",
        "points": [
            "Class B (residential) radiated limits at 3 m: 40 dB(uV/m) 30-88 MHz, 43.5 dB(uV/m) 88-216 MHz, 46 dB(uV/m) 216-960 MHz, 54 dB(uV/m) above 960 MHz; Class A is measured at 10 m with 39 / 43.5 / 46.4 / 49.5 dB(uV/m).",
            "Conducted limits (15.107) match CISPR 22/32 Class A/B values; the FCC accepts CISPR 32 test methods/limits as an alternative per 15.109(g).",
            "47 CFR 15.103 exempts: digital devices used exclusively in a transportation vehicle; industrial/commercial/medical test equipment; appliance digital devices; specialised medical devices; devices consuming at most 6 nW; passive add-on controllers such as joysticks/mice without digital circuitry; devices with clock below 1.705 MHz not using AC mains; and the Commission may exempt other devices unlikely to cause interference.",
            "Passive sub-assemblies (memory cards, media without their own oscillator) are not themselves authorised - the host digital device that contains them is; active bus-powered drives and SSDs with their own clock are digital devices and need SDoC.",
            "Labelling: the FCC logo is optional under SDoC; the Part 15 compliance statement and the responsible-party identification must be provided (in the manual or electronically for small devices).",
        ],
        "facts": [
            (r"exempt|15\.103|passive|sd card|memory card",
             "Under 47 CFR 15.103 the FCC exempts specific digital devices from the technical standards of Part 15 Subpart B (transportation-vehicle devices, industrial/commercial/medical test equipment, appliances, specialised medical devices, devices consuming at most 6 nW, passive add-on controllers without digital circuitry, devices with a clock below 1.705 MHz not connected to AC mains, and devices the Commission exempts case by case). Passive flash memory cards (SD/microSD/CF) have no free-running oscillator of their own - the host that clocks them is the digital device subject to 15.107/15.109 testing - so they are treated as passive sub-assemblies with no SDoC of their own. Active devices with an onboard clock (USB drives with a bridge controller, portable SSDs) do need an SDoC test report."),
            (r"sdoc|certification|declaration|authori[sz]ation|fcc id",
             "Two authorisation procedures exist in Part 2: Supplier's Declaration of Conformity (SDoC) and Certification. Unintentional radiators (digital devices) use SDoC: the responsible party, located in the US, tests the product (ANSI C63.4), keeps the report and a compliance information statement, and labels the product; no FCC ID, no TCB and no filing. Certification by a TCB (with an FCC ID) is mandatory only for intentional radiators, i.e. transmitters."),
        ],
    },
    "ices_003": {"title": "ICES-003 - Canada: Information Technology Equipment (including digital apparatus)", "aliases": [r"ices", r"\bised\b"], "pillar": "EMC",
                 "summary": "ISED Canada's interference-causing equipment standard for ITE/digital apparatus (currently Issue 7). Limits and methods are aligned with CISPR 32 and FCC Part 15 B; a FCC or CISPR 32 report is accepted as evidence. Compliance is by supplier declaration with the marking 'CAN ICES-003(B)/NMB-003(B)' for Class B; no registration or Canadian representative filing is needed for unintentional radiators.",
                 "points": ["Class B for residential use; immunity is not regulated in Canada.", "Keep the test report for the life of the product plus one year after the last unit is shipped."]},
    "kn_32_35": {"title": "KN 32 / KN 35 (now KS C 9832 / KS C 9835) - Korea KC EMC standards", "aliases": [r"kn ?32", r"kn ?35", r"ks ?c ?983[25]", r"\bkc\b.*(?:emc|registration)", r"conformity registration", r"\brra\b"], "pillar": "EMC",
                 "summary": "Korea's national adoption of CISPR 32 (emissions, KS C 9832, formerly KN 32) and CISPR 35 (immunity, KS C 9835, formerly KN 35) under the Radio Waves Act administered by the National Radio Research Agency (RRA). ITE such as SSDs, USB drives and card readers is subject to KC Conformity Registration: a test report from an RRA-designated (KOLAS) laboratory or an MRA-recognised foreign lab is filed by a Korean entity and a registration number (R-R-xxx-yyyy) is issued; the KC mark with that number must be applied.",
                 "points": ["The KC mark covers two different laws: EMC/radio (RRA, Radio Waves Act) and electrical safety (KATS, Electrical Appliances and Consumer Products Safety Control Act). A bus-powered drive needs only the RRA EMC registration; the AC adapter of a desktop drive additionally needs KC safety certification.", "Passive memory cards without their own oscillator are generally not subject to RRA registration.", "Registration is permanent but the registrant must be a Korean legal entity; label must show KC mark, registration number, model, importer and origin; Korean-language user information is required."]},
    "ks_c_9832_9835": {"title": "KS C 9832 / KS C 9835 - Korean standards for CISPR 32 / CISPR 35", "aliases": [r"ks ?c ?9832", r"ks ?c ?9835"], "pillar": "EMC",
                       "summary": "The current KS designations of Korea's EMC emission (KS C 9832 = CISPR 32) and immunity (KS C 9835 = CISPR 35) standards used for KC Conformity Registration of ITE; test reports often still quote the former KN 32 / KN 35 numbers.",
                       "points": ["Class B applies to consumer storage products.", "Korean reports must be issued by an RRA-designated lab or a lab recognised under an MRA (e.g. US, EU, Vietnam, Chile) for the KC registration to be accepted."]},
    "vcci": {"title": "VCCI - Japan voluntary EMC conformity (VCCI-CISPR 32)", "aliases": [r"vcci"], "pillar": "EMC",
             "summary": "The Voluntary Control Council for Interference by Information Technology Equipment operates Japan's EMC scheme for ITE. Technical requirements are VCCI-CISPR 32 (Class A/B); a member company files a Conformity Verification Report based on a test from a VCCI-registered lab and applies the VCCI mark. It is not law, but Japanese retailers and OEMs require it. Electrical safety of AC adapters falls under the DENAN (PSE) law; the storage drive itself is not a PSE-specified product.",
             "points": ["Membership of VCCI (or use of a member importer) is required to use the mark.", "VCCI covers emissions only - there is no immunity requirement in Japan."]},
    "gb_4943_1": {"title": "GB 4943.1-2022 - China: AV/ICT equipment safety (CCC)", "aliases": [r"gb ?4943", r"\bccc\b"], "pillar": "Safety",
                  "summary": "China's mandatory safety standard for AV/ICT equipment, aligned with IEC 62368-1:2018 and in force since 1 August 2023 (replacing GB 4943.1-2011, which was based on IEC 60950-1). It is applied through China Compulsory Certification (CCC) for products listed in the CCC catalogue - external power adapters (category 0907) and computers/servers are listed; standalone SSDs, memory cards and USB drives are generally not in the catalogue and need no CCC certificate, while a bundled adapter does.",
                  "points": ["CCC requires testing at a CNCA-designated Chinese lab (CQC, CVC, etc.), an initial factory inspection and annual follow-up.", "EMC for CCC products is tested to GB/T 9254.1 (CISPR 32); environmental marking follows China RoHS SJ/T 11364."]},
    "gbt_9254_1": {"title": "GB/T 9254.1-2021 - China adoption of CISPR 32", "aliases": [r"gb/?t ?9254", r"gb ?9254"], "pillar": "EMC",
                   "summary": "China's EMC emission standard for multimedia equipment, equivalent to CISPR 32:2015, which replaced GB 9254-2008 (CISPR 22); it is used for the EMC part of CCC certification of ITE in the catalogue and for voluntary CQC marks.",
                   "points": ["GB/T 9254.2 adopts CISPR 35 (immunity).", "Products outside the CCC catalogue (most standalone storage media) have no mandatory Chinese EMC filing."]},
    "cns_15598_1": {"title": "CNS 15598-1 - Taiwan: AV/ICT equipment safety (BSMI)", "aliases": [r"cns ?15598", r"\bbsmi\b.*safety"], "pillar": "Safety",
                    "summary": "Taiwan's adoption of IEC 62368-1 (CNS 15598-1:2020 corresponds to IEC 62368-1:2018), applied by the Bureau of Standards, Metrology and Inspection (BSMI) to listed commodities such as power supplies, computers and ITE through Registration of Product Certification (RPC) or Type Approval. Safety testing must be done by a BSMI-designated lab (CB reports accepted with Taiwan differences).",
                    "points": ["The BSMI Commodity Inspection Mark with an R-number (RPC) or T-number is applied to certified products.", "Bus-powered storage media are typically outside the mandatory safety scope; the adapter of a desktop drive is in scope."]},
    "cns_15936": {"title": "CNS 15936 - Taiwan adoption of CISPR 32 (BSMI EMC)", "aliases": [r"cns ?15936", r"cns ?13438"], "pillar": "EMC",
                  "summary": "Taiwan's emission standard for multimedia equipment (equivalent to CISPR 32), replacing CNS 13438 (CISPR 22). It forms the EMC part of BSMI RPC for ITE in the inspection list; testing is done at BSMI-designated labs and the product carries the BSMI mark with its registration number.",
                  "points": ["Removable memory cards are generally exempt from BSMI commodity inspection as passive media; active drives/readers in listed categories need RPC."]},
    "cns_15663": {"title": "CNS 15663 - Taiwan RoHS (marking of presence of restricted substances)", "aliases": [r"cns ?15663", r"taiwan rohs"], "pillar": "Environmental",
                  "summary": "Taiwan's RoHS standard. For products under BSMI inspection, Section 5 requires marking the presence of the six restricted substances (lead, mercury, cadmium, hexavalent chromium, PBB, PBDE) at the EU RoHS limits (0.1 % / cadmium 0.01 %) in a table on the product, packaging, manual or a website, declared as part of the BSMI application.",
                  "points": ["Only applies to commodities under BSMI inspection; it is a declaration/marking requirement, not a test program."]},
    "is_13252": {"title": "IS 13252 (Part 1) / IS/IEC 62368-1 - India BIS Compulsory Registration (CRS)", "aliases": [r"is ?13252", r"is/iec ?62368", r"\bbis\b", r"\bcrs\b", r"r-number", r"\bmeity\b"], "pillar": "Safety",
                 "summary": "Under MeitY's Electronics and IT Goods (Requirement for Compulsory Registration) Order, listed products must be tested in a BIS-recognised NABL lab in India and registered with the Bureau of Indian Standards, receiving an R-number and the BIS Standard Mark. IS 13252 (Part 1):2010 is the Indian adoption of IEC 60950-1; it is being replaced by IS/IEC 62368-1:2023 (the KB's alert gives the transition date). Listed products include power adapters, laptops, servers and some storage; standalone memory cards and USB flash drives are not in the list.",
                 "points": ["Testing must be in-country (foreign CB reports are not accepted as the sole basis).", "An Authorised Indian Representative (AIR) is required for foreign manufacturers; registration is per brand/factory and renewed every two years."]},
    "ul_62368_1": {"title": "UL 62368-1 / CSA C22.2 No. 62368-1 - North American national version", "aliases": [r"ul ?62368", r"csa ?62368", r"\bnrtl\b", r"\bculus\b|\bc-ul\b"], "pillar": "Safety",
                   "summary": "The US/Canadian national adoption of IEC 62368-1 with national differences (3rd edition 2019 aligned to IEC Ed.3; a 4th edition aligned to IEC Ed.4 has been published - check the current effective date with your NRTL). Used by OSHA-recognised NRTLs (UL, Intertek/ETL, CSA, TÜV) for Listing/Recognition. There is no federal law requiring NRTL marks on consumer ITE, but workplace use (OSHA), retailers and AHJs expect them, and the external power adapter is always expected to be NRTL-listed.",
                   "points": ["Bus-powered storage devices are typically covered by the host or by a component Recognition at most.", "Pair with FCC Part 15 B SDoC (EMC) and DoE Level VI (adapter efficiency)."]},
    "asnzs_62368_1": {"title": "AS/NZS 62368.1 - Australia / New Zealand safety and the RCM", "aliases": [r"as/nzs ?62368", r"\brcm\b", r"\beess\b", r"\bacma\b"], "pillar": "Safety",
                      "summary": "Australia/New Zealand adopt IEC 62368-1 as AS/NZS 62368.1. Under the Electrical Equipment Safety System (EESS) in-scope equipment is Level 1-3; external power supplies are Level 3 'declared articles' needing a certificate of conformity and registration on the EESS database, while low-voltage bus-powered devices are outside the electrical safety scope. EMC (AS/NZS CISPR 32) is regulated by the ACMA; the single Regulatory Compliance Mark (RCM) covers both safety and EMC and requires an Australian/NZ responsible supplier.",
                      "points": ["RCM labelling and supplier registration are mandatory before supply.", "Test reports to CISPR 32 / EN 55032 from any accredited lab are accepted for EMC."]},
    "rohs": {"title": "EU RoHS - Directive 2011/65/EU as amended by (EU) 2015/863", "aliases": [r"\brohs\b", r"2011/65", r"2015/863", r"restricted substances"], "pillar": "Environmental",
             "summary": "Restricts ten substances in electrical and electronic equipment placed on the EU market: lead, mercury, hexavalent chromium, PBB and PBDE at 0.1 % by weight in any homogeneous material, cadmium at 0.01 %, and since 22 July 2019 the four phthalates DEHP, BBP, DBP and DIBP at 0.1 %. RoHS is a CE-marking directive: the EU Declaration of Conformity must cite it, and the technical documentation follows EN IEC 63000 (material declarations, supplier evidence, test data where risk warrants).",
             "points": ["Open scope (category 11) since 22 July 2019 - storage products have been in scope since 2006 as IT equipment (category 3).", "Exemptions in Annex III/IV (e.g. 7(a) lead in high-melting-point solders, 7(c)-I lead in glass/ceramic of electronic components, 6(c) copper alloy up to 4 % lead) have individual expiry dates.", "Similar regimes: UK RoHS (UKCA), China RoHS (marking), Korea RoHS, Taiwan CNS 15663, EAEU TR CU 037/2016, UAE/Saudi RoHS, India E-Waste Rules."],
             "facts": [(r"substance|limit|which|list|phthalate|lead|cadmium", "The ten EU RoHS substances and limits per homogeneous material: lead 0.1 %, mercury 0.1 %, cadmium 0.01 %, hexavalent chromium 0.1 %, PBB 0.1 %, PBDE 0.1 %, DEHP 0.1 %, BBP 0.1 %, DBP 0.1 %, DIBP 0.1 %. Compliance is demonstrated by technical documentation to EN IEC 63000 and declared in the EU DoC; exemptions (Annex III/IV) must be cited explicitly where used.")]},
    "reach_svhc": {"title": "EU REACH - Regulation (EC) No 1907/2006: SVHC Candidate List and Article 33", "aliases": [r"\breach\b", r"\bsvhc\b", r"candidate list", r"1907/2006", r"\bscip\b", r"article 33"], "pillar": "Environmental",
                   "summary": "REACH applies to articles such as storage products through Article 33: when a Substance of Very High Concern (SVHC) on the ECHA Candidate List is present above 0.1 % weight/weight in an article, the supplier must inform the recipient (and consumers on request within 45 days) and, since 5 January 2021, notify the ECHA SCIP database. The 0.1 % threshold applies to each article as such (component level, 'once an article always an article' - CJEU 2015), not to the finished product. The Candidate List is updated twice a year (January and June) and has more than 240 entries.",
                   "points": ["Article 67 / Annex XVII restrictions (e.g. phthalates, PAHs, lead in consumer articles) are separate and binding limits.", "Request Full Material Disclosures or supplier declarations against the latest Candidate List version at each update."],
                   "facts": [(r"0\.1|threshold|limit|how much", "REACH Article 33 duty applies when an SVHC exceeds 0.1 % w/w of an article; the threshold is assessed for each individual article (every component that keeps its shape/function), not diluted across the whole product.")]},
    "china_rohs": {"title": "China RoHS - SJ/T 11364-2014 marking and GB/T 26572 limits", "aliases": [r"china rohs", r"sj/?t ?11364", r"\befup\b", r"gb/?t ?26572"], "pillar": "Environmental",
                   "summary": "The Administrative Measures for the Restriction of Hazardous Substances in Electrical and Electronic Products (China RoHS 2, 2016) require marking per SJ/T 11364-2014: the green 'e' logo when no restricted substance exceeds the GB/T 26572 limits, or the orange Environment-Friendly Use Period (EFUP) logo with a number of years plus a hazardous-substances table (in Chinese) in the manual. Products in the Conformity Assessment Catalogue (computers, printers, monitors, phones, etc.) additionally need a conformity assessment (voluntary certification or self-declaration on the public platform) since November 2019; standalone memory cards and drives are not in the catalogue but still require marking.",
                   "points": ["Same six substances and limits as EU RoHS 1 (no phthalates).", "EFUP for storage products is commonly declared as 10 or 20 years."]},
    "tsca_8a7": {"title": "US TSCA Section 8(a)(7) - PFAS reporting rule (40 CFR Part 705)", "aliases": [r"\btsca\b", r"8\(a\)\(7\)", r"40 cfr ?705", r"pfas report"], "pillar": "Environmental",
                 "summary": "An EPA one-time reporting and recordkeeping rule requiring anyone who manufactured or imported PFAS - including PFAS contained in imported articles such as SSDs, cables and packaging - in any year from 2011 to 2022 to report uses, volumes, exposures and disposal through the CDX portal. There is no de minimis volume threshold or article exemption in the final rule as published. The submission window has been postponed more than once; confirm the currently applicable EPA dates (this knowledge base tracks them in alert ALERT-ENV-01).",
                 "points": ["Reporting is to the extent 'known or reasonably ascertainable' - document the supplier enquiries you made.", "Fluoropolymers (PTFE wire insulation, PVDF coatings/binders, fluorinated lubricants) are the typical PFAS carriers in storage hardware."]},
    "pfas": {"title": "PFAS - per- and polyfluoroalkyl substances in electronics", "aliases": [r"\bpfas\b", r"forever chemical", r"fluoropolymer", r"\bptfe\b", r"\bpfoa\b|\bpfos\b"], "pillar": "Environmental",
             "summary": "A family of several thousand fluorinated substances (any molecule with at least one fully fluorinated carbon under the OECD/EPA structural definitions). In storage hardware they appear as PTFE/FEP wire insulation, PVDF and fluorinated coatings, lubricants and some labels. Regulation is fragmented: US EPA TSCA 8(a)(7) reporting, US state bans (Maine, Minnesota) on products with intentionally added PFAS, the EU universal PFAS restriction proposal under REACH (ECHA, 2023, under evaluation), existing POPs bans on PFOA/PFOS/PFHxS, and Korea's K-REACH / POPs controls.",
             "points": ["Ask suppliers for a Full Material Disclosure plus a PFAS declaration against the OECD definition; screen high-risk polymers by Total Organic Fluorine analysis.", "Many retailers now require 'no intentionally added PFAS' attestations for packaging."]},
    "weee": {"title": "EU WEEE - Directive 2012/19/EU", "aliases": [r"\bweee\b", r"wheelie bin", r"e-?waste", r"take[- ]back", r"2012/19"], "pillar": "Environmental",
             "summary": "Producers of electrical and electronic equipment must register in every EU member state where they sell, report quantities, finance collection and recycling (EPR) and mark products with the crossed-out wheeled bin (EN 50419) plus a producer identifier. Storage products fall under category 6 (small IT and telecommunication equipment) in the open scope applicable since 15 August 2018. Non-EU sellers must appoint an authorised representative in each member state.",
             "points": ["Marketplaces are increasingly obliged to check WEEE registration numbers (Germany, France, Austria).", "Equivalent EPR schemes exist in the UK (WEEE Regulations 2013), India (E-Waste Rules 2022), Korea (KECO) and many other markets."]},
    "ppwr": {"title": "EU PPWR - Packaging and Packaging Waste Regulation (EU) 2025/40", "aliases": [r"\bppwr\b", r"2025/40", r"packaging regulation", r"packaging waste"], "pillar": "Environmental",
             "summary": "The regulation replacing the Packaging Directive 94/62/EC. Published 22 January 2025, in force 11 February 2025, it applies from 12 August 2026 with staged obligations: all packaging recyclable by design (grades from 2030, 2038), minimum recycled content for plastic packaging from 2030, harmonised material-composition labelling for packaging (pictograms) applicable 42 months after entry into force (August 2028), restrictions on substances of concern, empty-space ratio limits (40 % for grouped/transport/e-commerce packaging from 2030), and EPR via national registers.",
             "points": ["Conformity is declared in an EU DoC for packaging with technical documentation - a new obligation for electronics brands.", "National labels such as the French Triman/Info-tri will be superseded by the harmonised EU labels once they apply."]},
    "agec_triman": {"title": "France AGEC law - Triman logo and Info-tri sorting instructions", "aliases": [r"\btriman\b", r"\bagec\b", r"info-?tri", r"\bciteo\b", r"2021-835"], "pillar": "Environmental",
                    "summary": "Under France's anti-waste law (Loi AGEC 2020-105) and Decree 2021-835 (Article 17 of the Environmental Code implementation), products and household packaging subject to an EPR scheme must display the Triman logo together with the Info-tri sorting instructions (pictograms showing which element goes in which bin), on the product, packaging or documents. Mandatory since 2022 (with stock sell-through until March 2023); CITEO is the packaging EPR scheme that publishes the artwork guides. Fines apply per non-compliant reference.",
                    "points": ["Digital-only display via QR code is not accepted for household packaging.", "Spain and Italy have their own packaging labelling rules; the EU PPWR will harmonise labels from 2028."]},
    "eu_cra": {"title": "EU Cyber Resilience Act - Regulation (EU) 2024/2847", "aliases": [r"\bcra\b", r"cyber resilience", r"2024/2847", r"products with digital elements", r"\bsbom\b"], "pillar": "Cyber",
               "summary": "Horizontal cybersecurity requirements for all 'products with digital elements' placed on the EU market - any hardware or software with a data connection, which includes SSDs, USB drives and card readers with firmware-bearing controllers. Entered into force 10 December 2024; vulnerability and incident reporting obligations (Art. 14) apply from 11 September 2026; the full obligations (essential requirements of Annex I, conformity assessment, CE marking, technical documentation) apply from 11 December 2027. Manufacturers must deliver secure-by-default products, handle vulnerabilities for a support period of at least five years (or the expected lifetime), provide an SBOM in the technical documentation, and report actively exploited vulnerabilities to ENISA within 24 hours.",
               "points": ["Storage devices are 'default' category products: conformity assessment by internal control (Module A) using harmonised standards once cited; 'important' class I/II and 'critical' products need third-party assessment.", "Harmonised standards are under development (CEN-CENELEC JTC 13); EN 18031-1/-2/-3, harmonised for the Radio Equipment Directive's cyber rules, are the baseline many labs apply today.", "The EU DoC must cite the CRA from 11 December 2027; the CE mark then also attests cybersecurity compliance."],
               "facts": [(r"when|deadline|date|apply|by when|affected", "CRA dates: published 20 November 2024; entry into force 10 December 2024; notification-body provisions from 11 June 2026; Article 14 reporting of actively exploited vulnerabilities and severe incidents from 11 September 2026; full application of all manufacturer obligations (Annex I essential requirements, conformity assessment, CE marking) from 11 December 2027. Products placed on the market before that date are only caught when substantially modified.")]},
    "uk_psti": {"title": "UK PSTI - Product Security and Telecommunications Infrastructure Act 2022", "aliases": [r"\bpsti\b", r"consumer connectable", r"default password", r"\bopss\b"], "pillar": "Cyber",
                "summary": "In force since 29 April 2024 (PSTI (Security Requirements for Relevant Connectable Products) Regulations 2023). It applies to consumer 'connectable' products - internet- or network-connectable devices - and requires: no universal default passwords, a published vulnerability disclosure policy with contact point, and a published minimum period of security updates. Manufacturers issue a Statement of Compliance that must accompany the product; the OPSS enforces with fines up to GBP 10 million or 4 % of worldwide revenue.",
                "points": ["A USB drive, SD card or SSD without network connectivity is not a 'connectable product' and is out of scope; NAS devices and Wi-Fi drives are in scope.", "Importers and distributors must verify the Statement of Compliance."]},
    "doe_level_vi": {"title": "US DoE Level VI - external power supply efficiency (10 CFR Part 430)", "aliases": [r"level vi", r"\bdoe\b", r"10 cfr ?430", r"external power suppl", r"\beps\b"], "pillar": "Environmental",
                     "summary": "US Department of Energy efficiency standards for external power supplies (EPS), mandatory for units manufactured or imported since 10 February 2016. They set minimum average active-mode efficiency and a maximum no-load power by nameplate output (e.g. no-load at or below 0.100 W for single-voltage adapters of 1-49 W). Compliant adapters carry the Roman numeral 'VI' marking protocol; the storage drive itself is not covered - only the adapter shipped with a desktop drive.",
                     "points": ["Also register with the California Energy Commission (CEC) appliance efficiency database when sold in California.", "The EU counterpart is Ecodesign Regulation (EU) 2019/1782; Korea (KEMCO MEPS), Australia (MEPS) and China have equivalent schemes."]},
    "erp_2019_1782": {"title": "EU Ecodesign - Regulation (EU) 2019/1782 for external power supplies", "aliases": [r"2019/1782", r"\berp\b", r"ecodesign", r"278/2009"], "pillar": "Environmental",
                      "summary": "Ecodesign requirements for external power supplies placed on the EU market from 1 April 2020 (replacing Regulation 278/2009): minimum average active efficiency and efficiency at 10 % load, maximum no-load power (0.10 W for most low-power adapters, 0.21 W for higher power), plus nameplate information (output power, average efficiency, no-load power). It is declared in the EU DoC under the Ecodesign framework and is compulsory for any adapter bundled with a desktop drive; bus-powered products have no ErP obligation.",
                      "points": ["Not applicable to USB-PD power supplies with multi-voltage negotiation in some respects - check the latest Commission guidance.", "Being replaced by the Ecodesign for Sustainable Products Regulation (ESPR) framework over time."]},
    "cb_scheme": {"title": "IECEE CB Scheme - CB Test Certificate and Test Report Form (TRF)", "aliases": [r"cb scheme", r"cb test", r"cb report", r"cb certificate", r"\btrf\b", r"\biecee\b", r"national differences"], "pillar": "Safety",
                  "summary": "A multilateral mutual-recognition system in which a National Certification Body issues a CB Test Certificate backed by a CB Test Report (in the standard TRF format for the standard, e.g. IEC 62368-1) from a CB Testing Laboratory. The report is accepted by certification bodies in 50+ member countries as the basis for their national marks (KC, BIS where allowed, BSMI, NRTL listing, EAC, SASO/SABER), usually with only national-difference testing added. It does not itself grant market access - the national certificate or mark is still required.",
                  "points": ["Ask the lab to include the national differences of every target market in the TRF when first testing.", "India (BIS CRS) and China (CCC) require in-country testing regardless of the CB report; Korea accepts CB reports for safety certification of adapters."]},
    "nrtl": {"title": "NRTL - Nationally Recognized Testing Laboratory (US OSHA)", "aliases": [r"\bnrtl\b", r"\bul listed\b|\betl\b", r"29 cfr 1910"], "pillar": "Safety",
             "summary": "OSHA recognises laboratories (UL, Intertek/ETL, CSA, TÜV SÜD/Rheinland, SGS, etc.) to test and certify products to US safety standards such as UL 62368-1 under 29 CFR 1910.7. An NRTL Listing mark (e.g. cULus, ETL) is required by OSHA for electrical equipment used in workplaces and is demanded by US/Canadian retailers and AHJs; it is the de facto US safety mark for AC adapters. There is no federal pre-market safety approval for consumer ITE.",
             "points": ["Canada recognises the same certification through the SCC (c-marks).", "Bus-powered storage devices normally rely on the host's or adapter's certification; component Recognition (UR) can be offered for OEM sales."]},
    "sdoc_vs_doc": {"title": "SDoC vs DoC - supplier/manufacturer declarations of conformity", "aliases": [r"\bsdoc\b", r"\bdoc\b", r"declaration of conformity", r"self[- ]declar"], "pillar": "All",
                    "summary": "A Declaration of Conformity (DoC) is the manufacturer's legally binding statement that a product meets specified legislation and standards - in the EU it is the CE-marking document (LVD, EMCD, RoHS, RED, CRA, Ecodesign) listing the exact standard editions and the responsible person. 'SDoC' (Supplier's Declaration of Conformity) is the FCC's term (47 CFR 2.906) for the same self-declaration route for digital devices, requiring a US-located responsible party and an ANSI C63.4 test report, with no FCC filing. Both routes mean no third-party certificate; the evidence is the technical file / test report kept by the declarant.",
                    "points": ["Market surveillance can request the DoC/SDoC and technical documentation at any time (EU: 10 years after the last unit).", "Korea, Taiwan, China, India and others do not accept self-declaration for regulated ITE - they require registration/certification."]},
    "eac": {"title": "EAC - Eurasian Conformity mark (EAEU technical regulations)", "aliases": [r"\beac\b", r"\beaeu\b", r"tr cu", r"customs union"], "pillar": "All",
            "summary": "The conformity mark of the Eurasian Economic Union (Russia, Belarus, Kazakhstan, Armenia, Kyrgyzstan). Relevant technical regulations: TR CU 004/2011 (low-voltage equipment safety, 50-1000 V AC / 75-1500 V DC - adapters, not 5 V bus-powered devices), TR CU 020/2011 (EMC - all electronic equipment capable of causing disturbance), and TR EAEU 037/2016 (restriction of hazardous substances, in force since 1 March 2020). Compliance is by declaration (most ITE) or certification, registered by an applicant that is a legal entity in an EAEU member state.",
            "points": ["Bus-powered drives: EAC declaration under TR CU 020 (EMC) and TR EAEU 037 (RoHS); desktop drives add TR CU 004 for the adapter.", "Test reports from accredited EAEU labs are generally required; CB reports help but are not sufficient alone."]},
    "saber": {"title": "SASO / SABER - Saudi Arabia conformity (PCoC / SCoC)", "aliases": [r"\bsaber\b", r"\bsaso\b", r"\bpcoc\b|\bscoc\b", r"g-?mark"], "pillar": "All",
              "summary": "The Saudi Standards, Metrology and Quality Organization requires regulated products to be registered on the SABER platform: a Product Certificate of Conformity (PCoC, valid one year, issued by a SASO-approved body against the applicable technical regulations - e.g. Low Voltage Equipment TR, EMC TR, RoHS TR) and a Shipment Certificate of Conformity (SCoC) for every consignment before customs clearance. Mains adapters fall under the LV/EMC technical regulations (and the GCC G-mark for listed low-voltage equipment); bus-powered storage media are usually registered for RoHS/EMC declaration only.",
              "points": ["Only the Saudi importer can create the SABER request; the manufacturer supplies test reports and declarations.", "The UAE equivalent is ECAS/EQM administered by MoIAT (formerly ESMA)."]},
    "nom_001": {"title": "NOM-001-SCFI-2018 - Mexico: safety of electronic equipment", "aliases": [r"nom-?001", r"nom-?019", r"\bnom\b", r"\bnyce\b|\bance\b"], "pillar": "Safety",
                "summary": "Mexico's mandatory safety standard for electronic apparatus and their power supplies connected to the mains (based on IEC 60950-1/60065 constructions), which replaced NOM-019-SCFI-1998 for ITE. Certification is issued by accredited bodies (ANCE, NYCE, UL de Mexico) with testing in Mexican-accredited labs; the NOM mark and Spanish labelling (NOM-024-SCFI for commercial information) are required at customs. Products operating below the mains voltage range without an adapter are outside NOM-001 scope.",
                "points": ["Certificates are valid one year (or longer with surveillance) and must be held by the Mexican importer.", "EMC is not mandatory for ITE in Mexico; IFT rules apply only to radio devices."]},
    "inmetro": {"title": "INMETRO / ANATEL - Brazil conformity", "aliases": [r"\binmetro\b", r"\banatel\b", r"portaria", r"abnt nbr"], "pillar": "All",
                "summary": "INMETRO (Instituto Nacional de Metrologia) runs Brazil's compulsory safety certification: ordinances (Portarias) require certification of power supplies/adapters and listed IT equipment to ABNT NBR IEC 62368-1, with testing in Brazilian accredited labs, a factory audit and annual maintenance, plus the INMETRO mark and Portuguese labelling. ANATEL homologation applies to telecommunications and radio products; wired storage devices need no ANATEL certificate but importers often present an exemption attestation. Environmental: Brazil's RoHS-type rules and the national e-waste reverse-logistics (Sistema REP) obligations.",
                "points": ["Bus-powered storage devices below 50 V DC are outside INMETRO's mains-safety ordinances; the adapter of a desktop drive is in scope.", "Local legal representative/importer is mandatory for both schemes."]},
    "en_18031": {"title": "EN 18031-1/-2/-3 - cybersecurity standards for RED (and CRA baseline)", "aliases": [r"en ?18031", r"red delegated", r"2022/30", r"article 3\.3"], "pillar": "Cyber",
                 "summary": "CEN/CENELEC standards (2024) for the Radio Equipment Directive's cybersecurity requirements (Delegated Regulation (EU) 2022/30, Article 3(3)(d)(e)(f): network protection, personal data/privacy, fraud protection), applicable to internet-connected radio equipment since 1 August 2025 and cited in the OJEU with restrictions (notified-body involvement where passwords or parental controls are user-configurable). Storage devices without radio are not RED products, but these standards are the de facto baseline test programs that labs apply while CRA harmonised standards are developed.",
                 "points": ["Mechanisms assessed include access control, authentication, secure update, secure storage, secure communication, resilience, logging and deletion.", "Firmware-signed update and no default credentials map directly to CRA Annex I requirements."]},
    "kc_scheme": {"title": "KC certification - Korea (KATS safety + RRA EMC)", "aliases": [r"\bkc\b", r"kc mark", r"kc certification", r"\bkats\b", r"korea.*certif"], "pillar": "All",
                  "summary": "The Korea Certification (KC) mark is one emblem used by several laws. For storage products two matter: (1) electrical safety under the Electrical Appliances and Consumer Products Safety Control Act administered by KATS - applies to the AC/DC power adapter (safety certification at a designated lab, standard KC 62368-1), not to DC bus-powered devices; (2) EMC under the Radio Waves Act administered by the RRA - Conformity Registration against KS C 9832/9835 (formerly KN 32/35) for ITE with a clock/oscillator, giving an R-R- registration number. A Korean legal entity must hold the registration and the label must show the KC mark, registration number, model, importer and country of origin, with Korean-language user information.",
                  "points": ["Passive memory cards are generally outside RRA registration; USB drives, portable SSDs, card readers and desktop drives are inside.", "Lead time is typically 4-6 weeks for EMC registration; adapter safety certification adds in-country testing time."]},
    "bsmi_scheme": {"title": "BSMI - Taiwan Bureau of Standards, Metrology and Inspection", "aliases": [r"\bbsmi\b", r"\brpc\b", r"commodity inspection"], "pillar": "All",
                    "summary": "BSMI administers Taiwan's commodity inspection. Listed ITE needs Registration of Product Certification (RPC) covering safety (CNS 15598-1) and EMC (CNS 15936) with a Taiwan RoHS declaration (CNS 15663 Section 5); test reports come from BSMI-designated labs (overseas CB reports accepted for safety with national differences). The BSMI mark with the registration number is affixed before import; a Taiwanese applicant (importer or local representative) is required. Removable memory cards and other passive media are generally exempt from inspection.",
                    "points": ["Registration validity follows the standard version; re-registration is needed when the CNS standard is updated.", "Traditional-Chinese labelling and manual are required."]},
    "pse": {"title": "PSE - Japan DENAN (Electrical Appliance and Material Safety Act)", "aliases": [r"\bpse\b", r"\bdenan\b", r"\bmeti\b", r"diamond pse|circle pse"], "pillar": "Safety",
            "summary": "METI's DENAN law requires 'specified' electrical appliances (diamond PSE, third-party conformity assessment by a registered body such as JET/JQA) and 'non-specified' appliances (circle PSE, self-declaration) to be certified before sale. AC adapters/switching power supplies are specified products (diamond PSE); storage drives themselves are not PSE-listed products. The Japanese importer registers with METI and bears responsibility for the mark. EMC is handled separately through VCCI.",
            "points": ["Technical standard is J62368-1 (Japanese version of IEC 62368-1) via the Appendix 12 route.", "Energy efficiency of adapters is covered by the Top Runner programme."]},
    "ukca": {"title": "UKCA marking - Great Britain conformity after Brexit", "aliases": [r"\bukca\b", r"uk conformity", r"great britain market"], "pillar": "All",
             "summary": "The UK Conformity Assessed mark was introduced for Great Britain in 2021 to replace CE marking under UK versions of the EU directives (Electrical Equipment (Safety) Regulations 2016, EMC Regulations 2016, RoHS Regulations 2012, etc.). The UK government has since legislated indefinite recognition of CE marking for most of these product regulations, so products legitimately CE-marked can continue to be placed on the GB market; UKCA remains available and may be required where UK rules diverge. Northern Ireland follows EU rules (CE, or UKNI with CE).",
             "points": ["A UK-based importer/responsible person address must appear on the product or documents.", "UK REACH and UK RoHS run in parallel to the EU regimes with separate SVHC/exemption lists over time."]},
    "rcm": {"title": "RCM - Regulatory Compliance Mark (Australia / New Zealand)", "aliases": [r"\brcm\b", r"responsible supplier", r"\bacma\b"], "pillar": "All",
            "summary": "A single mark showing compliance with ACMA EMC/telecom/radio rules and, where applicable, the EESS electrical safety requirements. The responsible supplier (an Australian or NZ entity) registers on the national database, keeps the compliance records (CISPR 32/EN 55032 reports; EESS certificate for Level 3 articles such as power supplies) and applies the RCM. Bus-powered storage devices need only the EMC declaration; desktop drives add adapter safety.",
            "points": ["No in-country testing is required - accredited overseas reports are accepted.", "Registration must precede supply; records are kept for five years."]},
    "prop_65": {"title": "California Proposition 65 - Safe Drinking Water and Toxic Enforcement Act", "aliases": [r"prop(?:osition)? ?65", r"california warning"], "pillar": "Environmental",
                "summary": "Requires a 'clear and reasonable' warning before exposing Californians to any of roughly 900 listed chemicals (lead, DEHP, BPA, nickel compounds, etc.) above safe-harbour levels. Electronics sold into California commonly carry the warning (on packaging, product or online listing) for lead in solder/PVC cables or phthalates in cable jackets. Enforcement is by private 60-day notices; there is no pre-market approval.",
                "points": ["Use the short-form or long-form warning with the warning symbol and the named chemical.", "RoHS compliance does not by itself remove the exposure warning need."]},
    "lvd_emcd": {"title": "EU Low Voltage Directive 2014/35/EU and EMC Directive 2014/30/EU", "aliases": [r"\blvd\b", r"low voltage directive", r"2014/35", r"\bemcd\b", r"emc directive", r"2014/30", r"inherently benign"], "pillar": "All",
                 "summary": "LVD applies to electrical equipment rated 50-1000 V AC or 75-1500 V DC - the AC adapter of a desktop drive is in scope, a 5 V bus-powered drive is not (it falls under the General Product Safety Regulation (EU) 2023/988 for consumers, with IEC/EN 62368-1 as the state-of-the-art reference). EMCD applies to any apparatus liable to generate electromagnetic disturbance or be affected by it; 'inherently benign' equipment (such as passive media with no active electronics) is excluded. Both are CE-marking directives declared in the EU DoC with EN IEC 62368-1 and EN 55032/EN 55035 as harmonised standards.",
                 "points": ["EU importers must have a responsible economic operator address on the product or packaging (Market Surveillance Regulation 2019/1020).", "Technical documentation is kept for 10 years after the last unit is placed on the market."]},
    "en_iec_63000": {"title": "EN IEC 63000 - technical documentation for RoHS", "aliases": [r"63000", r"en ?50581"], "pillar": "Environmental",
                     "summary": "The harmonised standard (replacing EN 50581, withdrawn November 2021) describing how to assemble the RoHS technical documentation: a supplier-information strategy based on material risk, declarations, analytical test data where risk is high, and a review process. Citing it in the EU DoC gives presumption of conformity for the documentation requirement of RoHS Article 7.",
                     "points": ["Does not require testing every material - a documented risk-based approach is sufficient.", "Keep supplier declarations current with RoHS exemption expiries."]},
    "gpsr": {"title": "EU General Product Safety Regulation (EU) 2023/988", "aliases": [r"\bgpsr\b", r"2023/988", r"general product safety"], "pillar": "Safety",
             "summary": "Applicable since 13 December 2024 (replacing Directive 2001/95/EC), the GPSR is the safety net for consumer products not fully covered by harmonised legislation - e.g. bus-powered storage devices outside the LVD voltage range. It requires a risk analysis and technical documentation, an EU-based responsible economic operator whose contact details appear on the product/packaging, traceability (type/batch), accident reporting via the Safety Business Gateway, and online marketplace due diligence.",
             "points": ["Using EN IEC 62368-1 as the design/test reference demonstrates state of the art for bus-powered products.", "Applies to all consumer products sold online into the EU, including via marketplaces."]},
}

# --------------------------------------------------------------------------- helpers
def _now_iso():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today():
    return _dt.date.today()


def _days_until(iso):
    try:
        return (_dt.date.fromisoformat(str(iso)[:10]) - _today()).days
    except (TypeError, ValueError):
        return None


def _rel(iso):
    n = _days_until(iso)
    if n is None:
        return str(iso or "date not fixed")
    if n == 0:
        return f"{iso} (today)"
    if n > 0:
        return f"{iso} (in {n} days)"
    return f"{iso} ({-n} days ago)"


def _norm_std(s):
    s = re.sub(r"\s+", " ", str(s or "").strip().upper())
    s = re.sub(r"^(IEC|EN|UL|CISPR|CNS|GB|KN|CSA)(\d)", r"\1 \2", s)
    s = s.replace("EN IEC", "EN IEC").replace("KS C", "KS C")
    return s


def _dedup(seq):
    out, seen = [], set()
    for x in seq:
        k = json.dumps(x, sort_keys=True, default=str) if isinstance(x, (dict, list)) else str(x).strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(x)
    return out


def _tokens(text):
    return [w for w in re.findall(r"[a-z0-9][a-z0-9\-/\.]+", str(text or "").lower()) if len(w) > 2 and w not in alert_explainer.STOPWORDS]


def _db_of(ctx):
    return (ctx or {}).get("db") or _db


# --------------------------------------------------------------------------- 1. understand
def understand(question, history=None, ctx=None):
    db = _db_of(ctx)
    q = str(question or "").strip()
    ql = " " + q.lower() + " "
    trail = []

    # countries
    codes = []
    for syn, code in sorted(COUNTRY_SYNONYMS.items(), key=lambda kv: -len(kv[0])):
        if re.search(r"(?<![a-z0-9])" + re.escape(syn) + r"(?![a-z0-9])", ql):
            if code not in codes:
                codes.append(code)
    for code, c in db.COUNTRIES_DB.items():
        name = str(c.get("name", "")).lower()
        if len(name) > 3 and re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", ql) and code not in codes:
            codes.append(code)
    for m in re.finditer(r"(?<![A-Za-z])([A-Z]{2})(?![A-Za-z0-9/-])(?!\s?\d)", q):
        code = m.group(1)
        if code in db.COUNTRIES_DB and code not in _AMBIGUOUS_ISO and code not in codes:
            codes.append(code)
    if "EU" in codes and any(c in codes for c in db.COUNTRIES_DB if str(db.COUNTRIES_DB[c].get("bloc", "")).startswith("EU")):
        codes.remove("EU")  # a member state was named explicitly

    # category
    category = None
    for rx, cid in CATEGORY_PATTERNS:
        if re.search(rx, ql):
            category = cid
            break
    if "card" in ql and category in ("usb_drive", "internal_ssd", "external_ssd_bus") and re.search(r"\bsd\b|memory card", ql):
        category = "sd_card"

    # standards
    stds = [_norm_std(m.group(0)) for m in _STD_RX.finditer(q)]
    for rx, label in _NAMED_STD:
        if re.search(rx, ql):
            stds.append(label)
    stds = _dedup(stds)

    # pillar
    pillar = None
    for p, rx in PILLAR_RX:
        if re.search(rx, ql):
            pillar = p
            break
    if re.search(r"\bkc\b|\bbsmi\b|\bccc\b|\bbis\b|\beac\b|\bsaber\b", ql) and not re.search(r"\bemc\b|safety", ql):
        pillar = None  # multi-pillar schemes

    # follow-up inheritance from history
    inherited = []
    if history and not codes and not category:
        prev = [h.get("content") for h in history if isinstance(h, dict) and h.get("role") == "user" and h.get("content")]
        if prev and re.search(r"\b(it|that|this|there|they|them|same|also|and what|how about|what about)\b", ql):
            pu = understand(prev[-1], None, ctx)
            if pu["countries"] and not codes:
                codes = [c["code"] for c in pu["countries"]]
                inherited.append("countries")
            if pu["category"] and not category:
                category = pu["category"]["id"]
                inherited.append("category")
            if pu["standards"] and not stds and re.search(r"\b(it|that|this)\b", ql):
                stds = pu["standards"]
                inherited.append("standards")
    if inherited:
        trail.append("Treated as a follow-up: inherited " + ", ".join(inherited) + " from the previous question.")

    # intent
    intent = "general"
    aspects = []
    for name, rx in INTENT_RULES:
        if re.search(rx, ql):
            aspects.append(name)
    if "comparison" in aspects and len(stds) >= 2 or ("comparison" in aspects and re.search(r"class a|class b", ql)):
        intent = "comparison"
    elif "exemption" in aspects:
        intent = "exemption"
    elif "deadline" in aspects and re.search(r"by when|deadline|affected|which of our|our products|when (?:does|do|will|is|are)|timeline|transition|effective", ql):
        intent = "deadline"
    elif "cost" in aspects:
        intent = "cost"
    elif "marks" in aspects or "documents" in aspects:
        intent = "marks" if "marks" in aspects and "documents" not in aspects else "documents"
    elif ("standard" in aspects) and (stds or _primer_hits(ql, stds)) and not (codes and category):
        intent = "standard"
    elif "requirements" in aspects and (codes or category):
        intent = "requirements"
    elif stds or _primer_hits(ql, stds):
        intent = "standard"
    elif codes or category:
        intent = "requirements"
    elif "standard" in aspects and _glossary_hits(q):
        intent = "definition"
    countries = []
    for code in codes[:MAX_COUNTRIES + 1]:
        if code == "EU":
            countries.append({"code": "EU", "name": "European Union (27 member states)"})
        elif code in db.COUNTRIES_DB:
            countries.append({"code": code, "name": db.COUNTRIES_DB[code].get("name", code)})
    cat = db.PRODUCT_CATEGORIES.get(category) if category else None
    trail.insert(0, "Parsed the question - countries: " + (", ".join(c["name"] for c in countries) or "none") + "; category: " + (cat["name"] if cat else "none")
                 + "; standards: " + (", ".join(stds) or "none") + "; pillar: " + (pillar or "any") + "; intent: " + intent + (" (" + ", ".join(a for a in aspects if a != intent) + ")" if [a for a in aspects if a != intent] else "") + ".")
    return {"countries": countries, "category": {"id": cat["id"], "name": cat["name"]} if cat else None, "standards": stds, "pillar": pillar,
            "intent": intent, "aspects": aspects, "trail": trail}


def _primer_hits(ql, stds):
    hits = []
    text = ql + " " + " ".join(stds).lower()
    for key, entry in STANDARDS_PRIMER.items():
        for alias in entry["aliases"]:
            if re.search(alias, text):
                hits.append(key)
                break
    return hits


def _glossary_hits(text, limit=10):
    out, seen = [], set()
    for term, rx, short, meaning in alert_explainer._GLOSSARY_COMPILED:
        if term in seen:
            continue
        if rx.search(text or ""):
            seen.add(term)
            out.append({"term": term, "meaning": meaning})
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------- 2. internal research
def _requirement_rows(understood, ctx, trail):
    db = _db_of(ctx)
    cat = understood.get("category")
    if not cat:
        return []
    rows = []
    for c in understood["countries"][:MAX_COUNTRIES]:
        code = c["code"]
        lookup = EU_CODES_ORDER[0] if code == "EU" else code
        try:
            r = db.get_country_product_requirement(lookup, cat["id"])
        except Exception:
            r = None
        if not r:
            continue
        label = c["name"] if code != "EU" else "European Union (harmonised CE rules; evaluated via Germany)"
        pillars = [{"pillar": x.get("pillar"), "status": x.get("status"), "standard": x.get("standard"), "route": x.get("route"), "note": x.get("note")} for x in r.get("applicable_requirements", [])]
        rows.append({
            "country": label, "country_code": code, "category": cat["name"], "category_id": cat["id"],
            "requirement_type": r.get("requirement_type"), "testing_location": r.get("testing_location"), "pillars": pillars,
            "documents": list(r.get("required_documents") or []), "marks": list(r.get("applicable_marks") or []),
            "lead_time": r.get("lead_time"), "local_rep_required": bool(r.get("local_rep_required")), "notes": r.get("notes") or "",
            "summary": r.get("applicable_summary") or "", "authority": r.get("authority"),
        })
        trail.append(f"Knowledge base: get_country_product_requirement({lookup}, {cat['id']}) -> {r.get('requirement_type')}; " + "; ".join(f"{p['pillar']} {p['status']}" for p in pillars) + ".")
    return rows


def _country_profiles(understood, ctx):
    db = _db_of(ctx)
    out = []
    for c in understood["countries"][:MAX_COUNTRIES]:
        code = EU_CODES_ORDER[0] if c["code"] == "EU" else c["code"]
        rec = db.COUNTRIES_DB.get(code)
        if rec:
            out.append({"code": c["code"], "name": c["name"], "record": rec})
    return out


def _match_alerts(question, understood, ctx, trail, limit=5):
    store = (ctx or {}).get("store")
    db = _db_of(ctx)
    try:
        alerts = store.alerts() if store else list(getattr(db, "REGULATION_ALERTS", []))
    except Exception:
        alerts = list(getattr(db, "REGULATION_ALERTS", []))
    q_tokens = set(_tokens(question))
    codes = {c["code"] for c in understood["countries"]}
    eu_set = {c for c, v in db.COUNTRIES_DB.items() if str(v.get("bloc", "")).startswith("EU")}
    stds = [s.lower() for s in understood["standards"]]
    cat = understood["category"]["id"] if understood["category"] else None
    scored = []
    for a in alerts:
        text = " ".join(str(a.get(k) or "") for k in ("title", "standard", "summary", "country", "region", "detailed_summary")).lower()
        score = 0.0
        why = []
        for s in stds:
            key = s.replace("eu cra", "cyber resilience").replace("uk psti", "psti")
            if key and (key in text or key.replace(" ", "") in text.replace(" ", "")):
                score += 3
                why.append(s.upper() if len(s) <= 5 else s)
        try:
            a_codes = reg_surveillance._alert_country_codes(a, db.COUNTRIES_DB)
        except Exception:
            a_codes = set()
        if codes:
            if "EU" in codes and (a_codes & eu_set) and len(a_codes) < len(db.COUNTRIES_DB):
                score += 2
                why.append("EU scope")
            hit = (codes - {"EU"}) & a_codes
            if hit and len(a_codes) < len(db.COUNTRIES_DB):
                score += 2
                why.append("market " + "/".join(sorted(hit)))
        cats = a.get("affected_categories") or []
        if cat and (cat in cats or any(c in alert_explainer.UNIVERSAL_TOKENS for c in cats)):
            score += 0.5 if any(c in alert_explainer.UNIVERSAL_TOKENS for c in cats) else 1.5
        overlap = q_tokens & set(_tokens(a.get("title", "") + " " + a.get("standard", "")))
        if len(overlap) >= 2:
            score += min(3, len(overlap)) * 0.8
            why.append("keywords " + ", ".join(sorted(overlap)[:3]))
        if understood.get("pillar") and ((a.get("pillar") or reg_surveillance.infer_pillar(a)) == understood["pillar"]):
            score += 1.0
        if score >= 3.0:
            scored.append((score, a, why))
    scored.sort(key=lambda t: -t[0])
    out = []
    for score, a, why in scored[:limit]:
        out.append({"id": a.get("id"), "title": a.get("title"), "severity": a.get("severity"), "standard": a.get("standard"), "country": a.get("country"),
                    "effective_date": a.get("effective_date"), "days_to_effective": _days_until(a.get("effective_date")), "summary": a.get("summary"),
                    "action_required": a.get("action_required"), "affected_categories": a.get("affected_categories") or [],
                    "milestones": [m for m in (a.get("timeline_milestones") or []) if isinstance(m, dict)],
                    "links": [l for l in (a.get("official_links") or []) if isinstance(l, dict) and l.get("url")],
                    "pillar": a.get("pillar") or reg_surveillance.infer_pillar(a), "why": why, "score": round(score, 1), "_raw": a})
    if out:
        trail.append(f"Matched {len(out)} alert(s) in the alert register: " + "; ".join(f"{x['id']} ({', '.join(x['why'])})" for x in out) + ".")
    else:
        trail.append("Searched the alert register - no alert matches the countries/standards/keywords of the question.")
    return out


def _impacted_products(alert_row, ctx):
    store = (ctx or {}).get("store")
    try:
        products = store.products() if store else None
    except Exception:
        products = None
    a = alert_row["_raw"]
    try:
        return reg_surveillance.resolve_product_impacts(a.get("affected_categories") or ["all_storage_categories"], a.get("country_code") or "Global", a.get("region") or "Global", products)
    except Exception:
        return []


def _primer_entries(understood, question):
    ql = question.lower()
    keys = _primer_hits(ql, understood["standards"])
    out = []
    for k in keys:
        e = STANDARDS_PRIMER[k]
        facts = [t for rx, t in e.get("facts", []) if re.search(rx, ql)]
        out.append({"key": k, "title": e["title"], "pillar": e["pillar"], "summary": e["summary"], "points": e["points"], "facts": facts})
    # specific standards first, then scheme-level entries
    out.sort(key=lambda e: (0 if e["facts"] else 1, 0 if re.search(r"\d", e["title"]) else 1))
    return out[:4]


def _curated(alerts):
    out = []
    for a in alerts:
        k = expert_advisor.CURATED_EXPERT_KNOWLEDGE.get(a["id"])
        if k:
            out.append({"alert_id": a["id"], **{kk: vv for kk, vv in k.items() if kk != "suggested_questions"}})
    return out


# --------------------------------------------------------------------------- 3. web research
def _web_queries(question, understood):
    qs = [question[:200]]
    cs = understood["countries"]
    cat = understood["category"]
    stds = understood["standards"]
    if cs and cat:
        c = cs[0]
        qs.append(f"{c['name'].split(' (')[0]} {CATEGORY_SHORT.get(cat['id'], cat['name'])} certification requirements {understood['pillar'] or ''}".strip())
    if stds:
        qs.append(f"{stds[0]} standard scope requirements" + (f" {cs[0]['name'].split(' (')[0]}" if cs else ""))
    elif cs and not cat:
        qs.append(f"{cs[0]['name'].split(' (')[0]} electronics product compliance marks storage devices")
    return _dedup(qs)[:3]


def _web_research(question, understood, trail):
    advisor = expert_advisor.get_expert_advisor()
    budget = expert_advisor._Budget(WEB_BUDGET_S)
    queries = _web_queries(question, understood)
    results = []
    live_any = False
    for q in queries:
        if budget.remaining() < 0.8:
            break
        fallback_urls = {s["url"] for s in advisor._get_fallback_authoritative_sources(q)}
        before = advisor.last_network_status
        try:
            found = advisor.search_internet(q, num_results=5, budget=budget)
        except Exception:
            found = []
        if advisor.last_network_status == "online" and found and any(f["url"] not in fallback_urls for f in found):
            live_any = True
        for f in found:
            if f.get("url") and not any(r["url"] == f["url"] for r in results):
                results.append({"title": f.get("title") or f["url"], "url": f["url"], "snippet": (f.get("snippet") or "")[:300],
                                "kind": "curated" if f["url"] in fallback_urls else "web", "query": q})
        _ = before
    status = "online" if live_any else "offline"
    live = [r for r in results if r["kind"] == "web"]
    curated = [r for r in results if r["kind"] == "curated"]
    if live_any:
        trail.append(f"Web research (online): {len(queries)} queries, {len(live)} live results plus {len(curated)} curated authoritative sources, de-duplicated.")
    else:
        trail.append("Web research returned no live results (offline, or the search endpoint is blocked/rate-limited) - relied on internal sources" + (f" and {len(curated)} curated authoritative references." if curated else "."))
    return results[:8], status


# --------------------------------------------------------------------------- 4. synthesis
def _focus_pillars(understood, question):
    ql = question.lower()
    if understood.get("pillar"):
        return [understood["pillar"]]
    if re.search(r"\bkc\b|\bbsmi\b|\bccc\b|\bbis\b|\beac\b|certif|approv|test", ql):
        return ["Safety", "EMC"]
    return ["Safety", "EMC", "Environmental", "Labelling"]


def _an(noun):
    return ("an " if re.match(r"^(?:[aeiou]|sd |s\.|m\.2|ssd|nvme|cf |cfexpress|enterprise|internal|external|usb)", str(noun).lower()) and not str(noun).lower().startswith("usb ") else "a ") + str(noun)


def _pillar_line(p):
    st = p.get("status")
    if st == "Exempt":
        return f"{p['pillar']}: Exempt - {p.get('note') or 'no national requirement for this product'}"
    if st == "Required":
        bits = [p.get("standard") or ""]
        if p.get("route"):
            bits.append(f"via {p['route']}")
        s = f"{p['pillar']}: Required - " + " ".join(b for b in bits if b).strip()
        if p.get("note") and p["pillar"] not in ("Environmental",):
            s += f" ({p['note']})"
        return s
    return f"{p['pillar']}: {st or 'n/a'}" + (f" - {p['note']}" if p.get("note") else "")


def _direct_from_rows(rows, understood, question):
    focus = _focus_pillars(understood, question)
    row = rows[0]
    status = {p["pillar"]: p for p in row["pillars"]}
    cat = CATEGORY_SHORT.get(row["category_id"], row["category"])
    cname = row["country"].split(" (")[0]
    req = [p for p in focus if status.get(p, {}).get("status") == "Required"]
    exm = [p for p in focus if status.get(p, {}).get("status") == "Exempt"]
    intent = understood["intent"]
    if intent == "exemption":
        if exm and not req:
            lead = "Yes - exempt."
        elif req and not exm:
            lead = "No - not exempt."
        else:
            lead = "It depends on the pillar."
    else:
        if req and not exm:
            lead = "Yes."
        elif exm and not req:
            lead = "No - not for this product."
        else:
            lead = "It depends on which approval you mean."
    parts = [lead, f"In {cname} {_an(cat)} is classified '{row['requirement_type']}'."]
    if req:
        parts.append("Required: " + "; ".join(_pillar_line(status[p]) for p in req) + ".")
    if exm:
        parts.append("Exempt: " + "; ".join(f"{p} ({status[p].get('note') or 'SELV / passive media'})" for p in exm) + ".")
    other_req = [p["pillar"] for p in row["pillars"] if p["status"] == "Required" and p["pillar"] not in focus]
    if other_req and intent in ("exemption", "requirements"):
        parts.append("Independently of certification, " + ", ".join(other_req) + " obligations still apply.")
    if len(rows) > 1:
        parts.append(f"See the table for {', '.join(r['country'].split(' (')[0] for r in rows[1:])}.")
    return " ".join(parts)


def _marks_docs_answer(rows, understood):
    row = rows[0]
    cname = row["country"].split(" (")[0]
    cat = CATEGORY_SHORT.get(row["category_id"], row["category"])
    req_marks = [m["mark"] for m in row["marks"] if m.get("status") == "Required"]
    no_marks = [f"{m['mark']} ({m.get('reason') or 'not applicable'})" for m in row["marks"] if m.get("status") != "Required"]
    env = next((p for p in row["pillars"] if p["pillar"] == "Environmental"), None)
    lab = next((p for p in row["pillars"] if p["pillar"] == "Labelling"), None)
    parts = [f"For {_an(cat)} in {cname} ('{row['requirement_type']}'):"]
    if understood["intent"] in ("marks", "documents") or "marks" in understood["aspects"]:
        parts.append("Marks required: " + (", ".join(req_marks) if req_marks else "no national approval mark for this product") + (f"; not required: {', '.join(no_marks)}" if no_marks else "") + ".")
        if lab and lab.get("note"):
            parts.append(lab["note"].rstrip(".") + ".")
    docs = row["documents"]
    if docs:
        parts.append(f"Documents to prepare ({len(docs)}): " + "; ".join(docs[:4]) + (f"; plus {len(docs) - 4} more in the table" if len(docs) > 4 else "") + ".")
    if env and env.get("standard"):
        parts.append(f"Environmental declarations: {env['standard']}.")
    return " ".join(parts)


def _alerts_answer(alerts, understood, ctx, products_cache):
    top = alerts[0]
    parts = []
    n = len(alerts)
    parts.append(f"{n} matching alert{'s' if n != 1 else ''} in the register. Most relevant: {top['id']} - {top['title']} ({top['severity']}), effective {_rel(top['effective_date'])}.")
    if understood["intent"] == "deadline" or re.search(r"our products|which of our|affected", " ".join(understood["aspects"])):
        prods = products_cache.get(top["id"])
        if prods is None:
            prods = _impacted_products(top, ctx)
            products_cache[top["id"]] = prods
        if prods:
            names = [f"{p.get('sku') or p.get('id')} ({p.get('name')})" for p in prods[:6]]
            parts.append(f"Affected portfolio products ({len(prods)}): " + ", ".join(names) + (f" and {len(prods) - 6} more" if len(prods) > 6 else "") + ".")
        else:
            parts.append("No product in the current portfolio is mapped to the affected categories/markets of this alert.")
    upcoming = [m for m in top["milestones"] if _days_until(m.get("date")) is not None and _days_until(m.get("date")) >= 0]
    if upcoming:
        m = upcoming[0]
        parts.append(f"Next milestone: {m.get('phase')} - {_rel(m.get('date'))}.")
    if top.get("action_required"):
        parts.append(f"Action required: {top['action_required']}")
    return " ".join(parts)


def _country_answer(profiles, understood):
    p = profiles[0]
    r = p["record"]
    bits = [f"{p['name']} - authority: {r.get('authority')}. Safety: {r.get('safety_std')}; EMC: {r.get('emc_std')}; environmental: {r.get('env_std')}.",
            f"CB Scheme accepted: {'yes' if r.get('cb_scheme_accepted') else 'no'}; in-country testing: {'required' if r.get('in_country_testing') else 'not required'}; local representative: {'required' if r.get('local_rep_required') else 'not required'}; marks: {', '.join(r.get('marks') or []) or 'none'}; typical lead time {r.get('lead_time_weeks')} weeks."]
    if r.get("notes"):
        bits.append(str(r["notes"]))
    bits.append("Name the product type (e.g. bus-powered SSD, SD card, desktop SSD with adapter) to get the exact requirement split.")
    return " ".join(bits)


def _profile_details(profiles):
    out = []
    for p in profiles:
        r = p["record"]
        body = "\n".join([
            f"Authority: {r.get('authority')} · Region: {r.get('region')} · Bloc: {r.get('bloc')}",
            f"Safety standard: {r.get('safety_std')} · EMC standard: {r.get('emc_std')} · Environmental: {r.get('env_std')}",
            f"RoHS: {r.get('rohs_std') or '-'} · PFAS/chemicals: {r.get('pfas_std') or '-'}",
            f"Packaging: {r.get('packaging_std') or '-'} · EPR/WEEE: {r.get('epr_std') or '-'}",
            f"CB Scheme accepted: {'yes' if r.get('cb_scheme_accepted') else 'no'} · In-country testing: {'yes' if r.get('in_country_testing') else 'no'} · Local representative: {'yes' if r.get('local_rep_required') else 'no'} · Certificate validity: {r.get('cert_validity') or '-'}",
            f"Marks: {', '.join(r.get('marks') or []) or 'none'} · Lead time: {r.get('lead_time_weeks')} weeks",
            f"Notes: {r.get('notes')}" if r.get("notes") else "",
        ])
        out.append({"heading": f"Country profile: {p['name']}", "body": body.strip()})
    return out


def _requirement_details(rows, understood):
    details = []
    for row in rows:
        cat = CATEGORY_SHORT.get(row["category_id"], row["category"])
        cname = row["country"]
        lines = [f"Classification: {row['requirement_type']}" + (f" · Testing location: {row['testing_location']}" if row.get("testing_location") else "")]
        lines += ["- " + _pillar_line(p) for p in row["pillars"]]
        if row.get("notes"):
            lines.append(f"Notes: {row['notes']}")
        details.append({"heading": f"Applicable requirements in {cname} for a {cat}", "body": "\n".join(lines)})
    ex = []
    for row in rows:
        for p in row["pillars"]:
            if p["status"] == "Exempt":
                ex.append(f"- {row['country'].split(' (')[0]} · {p['pillar']}: {p.get('note') or 'exempt'}")
    if ex:
        details.append({"heading": "Exemptions", "body": "\n".join(ex) + "\nExemption from safety/EMC approval never removes RoHS/REACH-type substance declarations, statutory labelling (importer, model, origin) or packaging/EPR duties."})
    marks = []
    for row in rows:
        for m in row["marks"]:
            marks.append(f"- {row['country'].split(' (')[0]} · {m['mark']}: {m.get('status')}" + (f" - {m['reason']}" if m.get("reason") else ""))
        lab = next((p for p in row["pillars"] if p["pillar"] == "Labelling"), None)
        if lab and lab.get("note"):
            marks.append(f"  Label content: {lab['note']}")
    if marks:
        details.append({"heading": "Marks & labelling", "body": "\n".join(marks)})
    docs = []
    for row in rows:
        if row["documents"]:
            docs.append(f"{row['country'].split(' (')[0]}:\n" + "\n".join(f"- {d}" for d in row["documents"]))
    if docs:
        details.append({"heading": "Documents to prepare", "body": "\n\n".join(docs)})
    lt = []
    for row in rows:
        drivers = []
        if "Testing Required" in (row["requirement_type"] or ""):
            drivers.append("in-country laboratory testing (ship samples, lab queue)")
        if row.get("local_rep_required"):
            drivers.append("local representative / importer agreement")
        if "Document Required" in (row["requirement_type"] or ""):
            drivers.append("registration filing with an accepted test report")
        if "Supplier Declaration" in (row["requirement_type"] or ""):
            drivers.append("self-declaration - cost limited to the test report and technical file")
        lt.append(f"- {row['country'].split(' (')[0]}: typical lead time {row['lead_time']} weeks" + (f"; cost drivers: {', '.join(drivers)}" if drivers else "") + ".")
    if lt:
        details.append({"heading": "Cost & lead time", "body": "\n".join(lt) + "\nBudget figures depend on lab quotes and sample counts; the alert explainer gives per-alert estimates where a regulatory change is involved."})
    return details


def _primer_details(primers, understood):
    details = []
    for e in primers:
        if e["facts"]:
            details.append({"heading": f"Specific point - {e['title'].split(' - ')[0]}", "body": "\n\n".join(e["facts"])})
    for e in primers:
        details.append({"heading": f"Standard explained: {e['title']}", "body": e["summary"] + "\n" + "\n".join(f"- {p}" for p in e["points"])})
    if understood["intent"] == "comparison" and len(primers) >= 2:
        a, b = primers[0], primers[1]
        details.insert(0, {"heading": f"Key differences: {a['title'].split(' - ')[0]} vs {b['title'].split(' - ')[0]}",
                           "body": f"{a['title'].split(' - ')[0]}: {a['summary'].split('. ')[0]}.\n{b['title'].split(' - ')[0]}: {b['summary'].split('. ')[0]}.\nPillar: {a['pillar']} vs {b['pillar']}."})
    return details


def _alert_details(alerts, ctx, products_cache):
    lines = []
    for a in alerts:
        l = [f"{a['id']} · {a['title']} · {a['severity']} · {a.get('pillar') or ''}", f"Effective: {_rel(a['effective_date'])} · Standard: {a.get('standard') or '-'} · Scope: {a.get('country') or '-'}"]
        if a.get("summary"):
            l.append(str(a["summary"]))
        ms = [m for m in a["milestones"] if m.get("date")]
        if ms:
            l.append("Milestones: " + "; ".join(f"{m.get('phase')} ({m.get('date')})" for m in ms[-4:]))
        prods = products_cache.get(a["id"])
        if prods is None:
            prods = _impacted_products(a, ctx)
            products_cache[a["id"]] = prods
        if prods:
            l.append(f"Portfolio products affected ({len(prods)}): " + ", ".join(f"{p.get('sku') or p.get('id')}" for p in prods[:10]))
        lines.append("\n".join(l))
    return [{"heading": "Deadlines & alerts", "body": "\n\n".join(lines)}] if lines else []


def _followups(understood, rows, primers, alerts):
    out = []
    cs = understood["countries"]
    cat = understood["category"]
    cn = cs[0]["name"].split(" (")[0] if cs else None
    cshort = CATEGORY_SHORT.get(cat["id"], cat["name"]) if cat else None
    if cn and cshort:
        out += [f"What documents do I need for a {cshort} in {cn}?", f"Is a {cshort} exempt from safety testing in {cn}?", f"What is the lead time and who must hold the registration in {cn}?", f"Which alerts affect {cshort}s sold in {cn}?"]
    elif cn:
        out += [f"Does a bus-powered SSD need certification in {cn}?", f"What marks are required to sell an SD card in {cn}?", f"Which alerts affect {cn}?"]
    elif cshort:
        out += [f"Which countries require in-country testing for a {cshort}?", f"What marks does a {cshort} need in Korea, Taiwan and Brazil?"]
    for e in primers[:2]:
        t = e["title"].split(" - ")[0]
        out.append(f"Which of our markets adopt {t}?")
        if e["pillar"] == "Safety":
            out.append(f"Does {t} apply to bus-powered storage devices?")
    for a in alerts[:1]:
        out.append(f"Which of our products are affected by {a['id']} and by when?")
    if not out:
        out = ["Does a bus-powered SSD need KC certification in Korea?", "What is the touch temperature limit in IEC 62368-1?", "Which of our products are affected by the EU Cyber Resilience Act and by when?"]
    return _dedup(out)[:4]


def _confidence(understood, rows, primers, alerts, profiles, web_status, out_of_scope):
    if out_of_scope:
        return {"level": "Low", "basis": "The question does not match any country, product category, standard or alert in the knowledge base."}
    direct_fact = any(e["facts"] for e in primers)
    if rows and understood["intent"] in ("requirements", "exemption", "marks", "documents", "cost"):
        return {"level": "High", "basis": "Answered from the shipped requirement engine (country x product category rules) and the country record" + ("; corroborated by web sources." if web_status == "online" else " (offline - no web corroboration).")}
    if direct_fact:
        return {"level": "High", "basis": "Answered from the built-in standards primer entry that specifically covers this point."}
    if alerts and understood["intent"] == "deadline":
        return {"level": "High" if alerts[0]["score"] >= 4 else "Medium", "basis": f"Dates and scope taken from alert {alerts[0]['id']} in the register."}
    if primers or profiles:
        return {"level": "Medium", "basis": "Answered from general primer/country-record material; the exact point may need verification in the standard or regulation text."}
    if alerts:
        return {"level": "Medium", "basis": "Only alert-register material matched the question."}
    return {"level": "Low", "basis": "No specific internal evidence; the answer is a general orientation."}


def _evidence(rows, primers, alerts, profiles, curated, limit=10):
    ev = []
    for row in rows[:2]:
        if row.get("notes"):
            ev.append({"text": row["notes"], "source": f"Knowledge base - requirement engine ({row['country'].split(' (')[0]} x {CATEGORY_SHORT.get(row['category_id'], row['category'])})"})
        if row.get("summary"):
            ev.append({"text": row["summary"], "source": "Knowledge base - requirement engine summary"})
    for e in primers[:2]:
        for f in e["facts"][:1]:
            ev.append({"text": f[:400] + ("…" if len(f) > 400 else ""), "source": f"Standards primer - {e['title'].split(' - ')[0]}"})
        if not e["facts"]:
            ev.append({"text": e["summary"].split(". ")[0] + ".", "source": f"Standards primer - {e['title'].split(' - ')[0]}"})
    for a in alerts[:2]:
        if a.get("summary"):
            ev.append({"text": str(a["summary"])[:400], "source": f"Alert register - {a['id']}"})
    for p in profiles[:1]:
        if p["record"].get("notes"):
            ev.append({"text": p["record"]["notes"], "source": f"Country record - {p['name']}"})
    for c in curated[:1]:
        if c.get("engineering_guidance"):
            ev.append({"text": c["engineering_guidance"], "source": f"Curated expert knowledge - {c['alert_id']}"})
    return _dedup(ev)[:limit]


RESEARCH_SYSTEM = (
    "You are a senior regulatory compliance researcher for flash-memory and solid-state storage products (SD/microSD, USB drives, portable and desktop SSDs, "
    "NVMe/enterprise SSDs, card readers) sold worldwide. You receive a user question plus research material gathered by a deterministic engine: "
    "requirement-engine rows, standards-primer entries, matching alerts, country records, glossary and web snippets, and a draft brief. "
    "Write the final brief grounded ONLY on that material.\n"
    "Rules:\n- Return ONLY one JSON object: {\"direct_answer\": string, \"details\": [{\"heading\": string, \"body\": string}], \"confidence\": {\"level\": \"High|Medium|Low\", \"basis\": string}, \"suggested_followups\": [string]}.\n"
    "- direct_answer: 2-4 sentences, start with Yes / No / It depends when the question is a yes/no question.\n"
    "- Cite sources inline by their label in square brackets, e.g. [Knowledge base], [Standards primer - IEC 62368-1], [Alert ALERT-2026-01], [Web: title].\n"
    "- Keep every number, date, limit, clause, standard edition and product/market list exactly as given. Never invent clause numbers, dates, fines or URLs.\n"
    "- If the material does not answer the question, say so plainly and state what evidence to obtain.\n"
    "- Keep the requirement rows' Required/Exempt statuses unchanged; you may reorganise and explain them."
)


def _claude_rewrite(question, understood, draft, material, history):
    if not ai_bridge.is_active():
        return None
    hist = [{"role": h["role"], "content": str(h["content"])[:1200]} for h in (history or [])[-6:] if isinstance(h, dict) and h.get("role") in ("user", "assistant") and h.get("content")]
    payload = {"question": question, "understood": {k: v for k, v in understood.items() if k != "trail"}, "conversation_so_far": hist, "draft_brief": draft, "material": material}
    text = ai_bridge._call(RESEARCH_SYSTEM, json.dumps(payload, ensure_ascii=False, default=str), max_tokens=3000)
    if not text:
        return None
    data = ai_bridge._parse_json(text)
    if not isinstance(data, dict):
        return None
    da = ai_bridge._clean_str(data.get("direct_answer"), 2000)
    if not da:
        return None
    details = []
    for d in (data.get("details") or [])[:8]:
        if isinstance(d, dict) and d.get("heading") and d.get("body"):
            details.append({"heading": ai_bridge._clean_str(d["heading"], 120), "body": ai_bridge._clean_str(d["body"], 3000)})
    conf = data.get("confidence") if isinstance(data.get("confidence"), dict) else {}
    level = conf.get("level") if conf.get("level") in ("High", "Medium", "Low") else None
    return {"direct_answer": da, "details": details, "confidence": {"level": level, "basis": ai_bridge._clean_str(conf.get("basis"), 400)} if level else None,
            "suggested_followups": ai_bridge._clean_list(data.get("suggested_followups"), 4, 200) or []}


# --------------------------------------------------------------------------- public API
def research(question, history=None, ctx=None, allow_ai=True, allow_web=True):
    question = re.sub(r"\s+", " ", str(question or "")).strip()[:MAX_QUESTION]
    db = _db_of(ctx)
    understood = understand(question, history, ctx)
    trail = list(understood.pop("trail"))
    aspects = understood.get("aspects", [])

    rows = _requirement_rows(understood, ctx, trail)
    profiles = _country_profiles(understood, ctx) if not rows else _country_profiles(understood, ctx)
    primers = _primer_entries(understood, question)
    if primers:
        trail.append("Standards primer: matched " + ", ".join(e["title"].split(" - ")[0] for e in primers) + (" with a specific fact for this question." if any(e["facts"] for e in primers) else "."))
    alerts = _match_alerts(question, understood, ctx, trail)
    curated = _curated(alerts)
    if curated:
        trail.append("Pulled curated expert knowledge for " + ", ".join(c["alert_id"] for c in curated) + ".")
    glossary = _glossary_hits(question)
    relevant = bool(rows or primers or alerts or profiles or glossary or understood["standards"] or REG_RELEVANCE_RX.search(question))
    out_of_scope = not relevant or (not rows and not primers and not alerts and not profiles and not understood["standards"] and not understood["category"] and len(glossary) == 0 and not REG_RELEVANCE_RX.search(question))
    if out_of_scope:
        trail.append("No regulatory entity, standard or alert recognised - the question is outside the scope of this knowledge base.")

    web_sources, network_status = ([], "offline")
    if allow_web and not out_of_scope:
        web_sources, network_status = _web_research(question, understood, trail)
    elif out_of_scope:
        trail.append("Web research skipped: out-of-scope question.")

    products_cache = {}
    details = []
    if out_of_scope:
        direct = ("This question appears to be outside the scope of the regulatory knowledge base (product safety, EMC, environmental and cybersecurity compliance for storage products). "
                  "I could not find a country, product category, standard or alert that matches it, so I will not guess. "
                  "Try naming a market, a product type (e.g. bus-powered SSD, SD card) or a standard/regulation.")
    elif rows and understood["intent"] in ("marks", "documents"):
        direct = _marks_docs_answer(rows, understood)
    elif rows and understood["intent"] in ("requirements", "exemption", "cost", "general"):
        direct = _direct_from_rows(rows, understood, question)
        if understood["intent"] == "cost":
            direct += f" Typical lead time in {rows[0]['country'].split(' (')[0]}: {rows[0]['lead_time']} weeks" + (" with a local representative required." if rows[0]["local_rep_required"] else ".")
    elif alerts and understood["intent"] == "deadline":
        direct = _alerts_answer(alerts, understood, ctx, products_cache)
    elif primers and (understood["intent"] in ("standard", "comparison", "definition") or not rows):
        e = primers[0]
        if e["facts"]:
            direct = e["facts"][0]
        elif understood["intent"] == "comparison" and len(primers) >= 2:
            direct = f"{primers[0]['title'].split(' - ')[0]}: {primers[0]['summary'].split('. ')[0]}. {primers[1]['title'].split(' - ')[0]}: {primers[1]['summary'].split('. ')[0]}."
        else:
            direct = e["summary"]
        if rows:
            direct += " " + _direct_from_rows(rows, understood, question)
    elif rows:
        direct = _direct_from_rows(rows, understood, question)
    elif alerts:
        direct = _alerts_answer(alerts, understood, ctx, products_cache)
    elif profiles:
        direct = _country_answer(profiles, understood)
    elif glossary:
        g = glossary[0]
        direct = f"{g['term']}: {g['meaning']}"
    else:
        direct = ("I recognised a regulatory question but found no specific match in the knowledge base. "
                  + ("Web sources are listed below for orientation. " if web_sources else "")
                  + "Add a market, product type or standard number for a precise answer.")

    if not out_of_scope:
        if rows:
            details += _requirement_details(rows, understood)
        if primers:
            details += _primer_details(primers, understood)
        if alerts:
            details += _alert_details(alerts, ctx, products_cache)
        if profiles and not rows:
            details += _profile_details(profiles)
        if curated:
            for c in curated[:2]:
                body = "\n".join(f"{k.replace('_', ' ').capitalize()}: {v if not isinstance(v, list) else '; '.join(v)}" for k, v in c.items() if k != "alert_id")
                details.append({"heading": f"Curated expert notes - {c['alert_id']}", "body": body})

    all_text = direct + " " + " ".join(d["body"] for d in details)
    glossary = _dedup(glossary + _glossary_hits(direct + " " + " ".join(d["body"] for d in details[:2]), 10))[:8]
    evidence = _evidence(rows, primers, alerts, profiles, curated)
    confidence = _confidence(understood, rows, primers, alerts, profiles, network_status, out_of_scope)
    followups = _followups(understood, rows, primers, alerts) if not out_of_scope else [
        "Does a bus-powered SSD need KC certification in Korea?", "What marks and documents do I need to sell a USB flash drive in Brazil?", "What is the touch temperature limit in IEC 62368-1?"]

    generated_by = "rules"
    if allow_ai and not out_of_scope and ai_bridge.is_active():
        material = {"requirements_table": rows, "primer": [{k: v for k, v in e.items() if k != "key"} for e in primers], "alerts": [{k: v for k, v in a.items() if k != "_raw"} for a in alerts],
                    "country_records": [{"name": p["name"], **{k: v for k, v in p["record"].items() if k in ("authority", "safety_std", "emc_std", "env_std", "cb_scheme_accepted", "in_country_testing", "local_rep_required", "marks", "lead_time_weeks", "notes")}} for p in profiles],
                    "glossary": glossary, "curated": curated, "web_sources": web_sources, "evidence": evidence}
        try:
            ai = _claude_rewrite(question, understood, {"direct_answer": direct, "details": details}, material, history)
        except Exception as e:  # never let the bridge break the brief
            ai_bridge._set_error(f"{type(e).__name__}: {e}")
            ai = None
        if ai:
            direct = ai["direct_answer"]
            if ai["details"]:
                details = ai["details"]
            if ai["confidence"]:
                confidence = ai["confidence"]
            if ai["suggested_followups"]:
                followups = ai["suggested_followups"]
            generated_by = ai_bridge._model()
            trail.append(f"Claude ({generated_by}) wrote the narrative, grounded on the gathered material only.")
        else:
            st = ai_bridge.status()
            trail.append("Claude narrative unavailable" + (f" ({st['last_error']})" if st.get("last_error") else "") + " - deterministic brief shown.")
    else:
        trail.append("Brief written by the deterministic rules engine (grounded)." if not out_of_scope else "Brief: out-of-scope notice.")

    table = [{k: v for k, v in r.items() if k not in ("summary", "authority", "testing_location")} for r in rows]
    return {
        "question": question,
        "understood": {k: understood[k] for k in ("countries", "category", "standards", "pillar", "intent")},
        "direct_answer": direct,
        "details": details,
        "requirements_table": table,
        "evidence": evidence,
        "web_sources": [{k: v for k, v in s.items() if k != "query"} for s in web_sources],
        "alerts": [{"id": a["id"], "title": a["title"], "severity": a["severity"], "effective_date": a["effective_date"], "days_to_effective": a["days_to_effective"]} for a in alerts],
        "glossary": glossary,
        "confidence": confidence,
        "research_trail": trail,
        "suggested_followups": followups,
        "out_of_scope": out_of_scope,
        "generated_by": generated_by,
        "network_status": network_status,
        "engine_version": ENGINE_VERSION,
        "answered_at": _now_iso(),
    }


def suggestions():
    return [
        "Does a bus-powered SSD need KC certification in Korea?",
        "What marks and documents do I need to sell a USB flash drive in Brazil?",
        "What is the touch temperature limit in IEC 62368-1?",
        "Is an SD card exempt from FCC testing?",
        "Difference between CISPR 32 Class A and Class B",
        "Which of our products are affected by the EU Cyber Resilience Act and by when?",
        "Does a desktop SSD with an AC adapter need BIS registration in India?",
        "What are the RoHS substance limits and which documents prove compliance in the EU?",
    ]


def brief_text(r):
    """Plain-text rendering for 'Copy brief'."""
    lines = [f"Q: {r.get('question')}", "", f"Answer: {r.get('direct_answer')}", ""]
    for d in r.get("details") or []:
        lines += [d["heading"].upper(), d["body"], ""]
    if r.get("evidence"):
        lines.append("EVIDENCE")
        lines += [f'- "{e["text"]}" - {e["source"]}' for e in r["evidence"]]
        lines.append("")
    if r.get("web_sources"):
        lines.append("WEB SOURCES")
        lines += [f"- {s['title']} - {s['url']}" for s in r["web_sources"]]
        lines.append("")
    c = r.get("confidence") or {}
    lines.append(f"Confidence: {c.get('level')} - {c.get('basis')}")
    lines.append(f"Generated by: {r.get('generated_by')} · web: {r.get('network_status')} · {r.get('answered_at')}")
    return "\n".join(lines)
