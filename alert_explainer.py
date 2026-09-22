"""
alert_explainer.py - Deterministic "explain this regulatory alert in plain English" engine.

Reads *every* field of an alert (title, summary, detailed_summary, technical_impact,
standard, country / region, severity, effective_date, timeline_milestones,
official_links, compliance_checklist, affected_categories, action_required, source,
pillar) and produces the Explanation shape defined in docs/ARCHITECTURE_CONTRACT.md §4.

Design:
  * constants and rule tables at the top (roles, glossary, cost table, risk library,
    analogies), small pure functions below, one public entry point: explain_alert().
  * works fully offline, never fabricates URLs or fine amounts - every penalty figure
    quoted comes from the alert text itself.
  * robust to sparse alerts (surveillance-detected or user-created) - every field of the
    output is always present and non-empty.
  * ai_bridge.py may *enhance* the narrative fields of this result; numeric and date
    fields always come from here.
"""
import datetime as _dt
import re

import compliance_db as _db
import reg_surveillance as _rs

ENGINE_VERSION = "2.0.0"

# --------------------------------------------------------------------------- roles & audiences
ROLE_RCE = "Regulatory Compliance Engineer"
ROLE_LAB = "Test-Lab Coordinator"
ROLE_FW = "Firmware Security"
ROLE_PKG = "Packaging & Artwork"
ROLE_SCM = "Supply-Chain & BOM"
ROLE_LEGAL = "Legal & Trade Compliance"
ROLE_REP = "Local Representative"
AUDIENCES = ("simple", "executive", "engineer")

# --------------------------------------------------------------------------- action types
# Each action type: keywords that reveal it in the alert text, the owning role, an
# effort bucket and the cost rule (per product family, USD) - see estimate_cost().
ACTION_TYPES = {
    "retest": {
        "label": "laboratory re-testing",
        "keywords": (r"re-?test", r"\btesting\b", r"test reports?", r"laborator", r"\bnabl\b", r"cb (?:test )?(?:report|certificate)", r"\btrf\b",
                     r"delta (?:test|report|evaluation)", r"in-country", r"thermal", r"emissions?\b", r"immunity", r"\bsamples?\b", r"test slot", r"accredited lab"),
        "role": ROLE_LAB, "effort": ("L", 8, 16),
        "cost": {"Safety": (6000, 14000), "EMC": (4500, 9500), "Environmental": (3000, 7000), "Cyber": (8000, 18000), "All": (7000, 16000)},
    },
    "firmware": {
        "label": "firmware security & SBOM work",
        "keywords": (r"\bfirmware\b", r"\bsbom\b", r"secure boot", r"vulnerab", r"signed firmware", r"cryptographic", r"bootloader", r"\bcyber",
                     r"security (?:update|patch)", r"software bill", r"\bpsti\b", r"resilience act", r"security patch", r"root-of-trust"),
        "role": ROLE_FW, "effort": ("L", 12, 24),
        "cost": {"*": (25000, 80000)}, "per_product": (3000, 8000),
    },
    "packaging": {
        "label": "packaging & artwork changes",
        "keywords": (r"\bpackaging\b", r"\bartwork\b", r"\blabel(?:s|ling|ing)?\b", r"\bmarkings?\b", r"\blogo\b", r"\bemblem\b", r"pictogram", r"qr code", r"blister",
                     r"\bcarton", r"die-line", r"box art", r"triman", r"info-tri", r"\bsorting\b", r"recycled", r"\bvoid\b", r"\befup\b"),
        "role": ROLE_PKG, "effort": ("M", 4, 8),
        "cost": {"*": (2500, 6000)}, "market_scaled": True,
    },
    "portal": {
        "label": "portal registration / filing",
        "keywords": (r"(?:crs|saber|cdx|cpcb|epr|bis|registration|online|electronic|centralized|national) portal", r"\bregistration\b", r"\bregister(?:ed)?\b", r"\bsaber\b", r"\bcdx\b", r"\bcpcb\b",
                     r"r-?numbers?", r"\bfiling\b", r"certificates? of conformity", r"\bpcoc\b", r"\bscoc\b", r"form u\b", r"form i\b", r"annual returns?", r"\bupload"),
        "role": ROLE_REP, "effort": ("S", 3, 8),
        "cost": {"*": (1200, 3500)}, "market_scaled": True,
    },
    "supply_chain": {
        "label": "supplier declarations & chemical screening",
        "keywords": (r"\bsuppliers?\b", r"\bvendors?\b", r"bill of materials", r"\bbom\b", r"material declarations?", r"ipc-?1752", r"\bfmd\b",
                     r"cas numbers?", r"\bsubstances?\b", r"\bpfas\b", r"\brohs\b", r"\breach\b", r"phthalate", r"flame retardant", r"laminate",
                     r"fluorine", r"\bxrf\b", r"gc-ms", r"\bchemical", r"attestations?", r"covered list", r"cage codes?"),
        "role": ROLE_SCM, "effort": ("M", 6, 12),
        "cost": {"*": (3000, 9000)}, "program": (8000, 25000),
    },
    "document": {
        "label": "document / declaration amendment",
        "keywords": (r"declaration of conformity", r"\bdoc\b", r"technical file", r"technical documentation", r"statement of compliance",
                     r"technical construction file", r"\btcf\b", r"\bamend", r"update declaration", r"self-declaration", r"\bdocumentation\b"),
        "role": ROLE_RCE, "effort": ("S", 2, 4),
        "cost": {"*": (1500, 4000)},
    },
}
ACTION_ORDER = ("retest", "firmware", "supply_chain", "portal", "packaging", "document")
for _spec in ACTION_TYPES.values():
    _spec["rx"] = [re.compile(k, re.I) for k in _spec["keywords"]]

# --------------------------------------------------------------------------- pillar knowledge
PILLAR_META = {
    "Safety": {
        "plain": "electrical safety",
        "business": "Safety approvals are the passport for anything with a mains adapter: without an updated certificate the "
                    "product cannot be imported, listed by retailers or shipped to enterprise customers in the affected markets.",
        "engineering": "Safety changes usually mean new thermal, electrical-energy and fault-condition tests on the adapter and "
                       "enclosure - the physical hardware, not just paperwork - so lab slots, samples and sometimes a redesign "
                       "of heatsinks or firmware throttling are on the critical path.",
        "risks": ["Import refusal or customs hold for products whose safety certificate cites the withdrawn standard",
                  "Retailer and distributor de-listing once the old certificate is no longer accepted",
                  "Liability exposure if a thermal or electrical incident occurs on a product certified only to the superseded edition"],
        "analogy": "Think of it like a driving licence renewal: your old licence was valid, but the test has changed, and after "
                   "the cut-off date the border guard only accepts the new one.",
    },
    "EMC": {
        "plain": "electromagnetic compatibility (radio interference)",
        "business": "EMC registration is checked at import and by market-surveillance labs buying retail units; a failed or "
                    "outdated registration blocks customs clearance and can trigger a mandatory recall notice.",
        "engineering": "New EMC test methods change how emissions are measured (frequency range, traffic load, antenna set-up), "
                       "so a product that passed before can fail now - plan a pre-scan before booking the formal test.",
        "risks": ["Customs clearance refused for shipments without a valid in-scope EMC registration",
                  "Retail market-surveillance test failure leading to sales suspension and corrective action",
                  "Registration number invalid on the label - a labelling offence in most markets"],
        "analogy": "It is like a noise ordinance for electronics: the city changed how loud is 'too loud' and how they measure it, "
                   "so every device needs a fresh reading.",
    },
    "Environmental": {
        "plain": "environmental & chemical substance rules",
        "business": "Environmental rules are enforced at the border and on the shelf: shipments without the right certificate, "
                    "label or portal registration are detained, and fines are levied per SKU - which multiplies quickly across a "
                    "retail range.",
        "engineering": "Chemical rules push work down into the supply chain: full material declarations from NAND, controller, "
                       "PCB and cable suppliers, screening tests on high-risk materials and, where limits are exceeded, a "
                       "qualified alternative material.",
        "risks": ["Shipments detained at the port until the missing certificate, label or registration is produced",
                  "Per-SKU administrative fines that scale with the size of the retail range",
                  "Forced re-packaging or product withdrawal of stock already in the channel"],
        "analogy": "It is like an ingredients label on food: the regulator wants to know exactly what is inside and on the box, "
                   "and will stop the product at the door if the label is missing or wrong.",
    },
    "Cyber": {
        "plain": "product cybersecurity",
        "business": "Cybersecurity laws treat the firmware inside a drive as part of the product: no compliant firmware "
                    "process and no signed statement means the product legally cannot be sold, and the penalties are set as a "
                    "share of company turnover rather than a flat fee.",
        "engineering": "Cyber requirements reach into silicon and firmware: secure boot with signed images, disabled debug "
                       "back-doors, a machine-readable list of every software component (SBOM), a vulnerability-reporting "
                       "channel and a defined security-update support period.",
        "risks": ["Market withdrawal orders for products lacking the required security paperwork or firmware controls",
                  "Turnover-based fines and, in some jurisdictions, criminal liability for company officers",
                  "Mandatory 24-hour incident reporting - missing it is a separate offence"],
        "analogy": "It is like building codes for a house: locks on the doors, a list of the materials used, and a promise to "
                   "fix structural problems for a set number of years - now written into law for the software inside a drive.",
    },
    "All": {
        "plain": "safety, electromagnetic compatibility and environmental rules together",
        "business": "A multi-pillar change means several certificates, labels and registrations expire together, so the "
                    "market-access window closes all at once unless the work streams are run in parallel.",
        "engineering": "Expect parallel work streams: safety and EMC re-tests in the lab, supplier declarations for "
                       "substances, and packaging artwork updates - coordinated so a single new technical file is issued.",
        "risks": ["Total loss of market access for the affected range when several approvals lapse on the same date",
                  "Customs detention and retailer de-listing across the affected jurisdictions",
                  "Duplicated lab spend if safety, EMC and environmental testing are not bundled"],
        "analogy": "It is like a car's annual inspection where brakes, lights and emissions are all checked on the same day - "
                   "fail one and the car stays off the road.",
    },
}

# --------------------------------------------------------------------------- consequence detectors
# (regex on alert text, plain-English risk sentence). Only used when the pattern really
# appears in the alert, so jurisdiction-specific consequences are never invented.
CONSEQUENCE_PATTERNS = [
    (r"detain|held by|customs hold|blocked at .{0,40}port|import embargo|customs seizure|seiz", "Shipments will be detained or seized at the border until compliant paperwork is produced"),
    (r"cancel(?:led|ed)? and withdrawn|r-numbers? will be cancel|registrations? .{0,30}cancel", "Existing registrations (R-numbers) are cancelled on the deadline - legacy certificates stop working overnight"),
    (r"revocation|revoked|revoke", "The existing certificate can be revoked, removing market access for every SKU on it"),
    (r"recall", "Product recall from retail channels"),
    (r"criminal offen[cs]e|penalty of perjury|criminal", "Personal / criminal liability for the signing officers, not just a corporate fine"),
    (r"de-?list|cannot be sold|prohibited from selling|legally barred|sales? (?:stop|ban|prohibition)", "Sales stop: the product may no longer legally be offered in the affected market"),
    (r"market withdrawal|withdraw(?:n|al) from the market", "Market-withdrawal order for non-conforming products already on sale"),
    (r"environmental compensation", "Environmental Compensation charges levied per tonne of unmet recycling target"),
    (r"market surveillance|factory surveillance|retail (?:market )?audits?|compliance audits?|customs [^.]{0,30}audit|audits? (?:by|cross-check)|trading standards", "Regulator audits (factory, retail or documentation) that require evidence on demand"),
    (r"24[- ]?h(?:ou)?r", "A 24-hour reporting clock for exploited vulnerabilities - missing it is a separate breach"),
    (r"annual(?:ly)? (?:re-?verification|renew|return|surveillance)|renewed annually|every year", "The obligation recurs every year - a one-off fix is not enough"),
]
MONEY_RE = re.compile(r"(?:€|£|\$|NT\$|US\$|USD|EUR|GBP|INR|₹)\s?\d[\d,\.]*(?:\s?(?:million|m|bn|billion|k))?|\d[\d,\.]*\s?(?:%|percent) of (?:worldwide |global |annual )?turnover", re.I)

# --------------------------------------------------------------------------- glossary
# (term, regex, short plain gloss for inline expansion, full meaning). Short acronym
# patterns are case-sensitive; multi-word phrases are case-insensitive.
GLOSSARY = [
    ("SDoC", r"\bSDoC\b|Supplier'?s Declaration of Conformity", "a self-declaration by the supplier", "Supplier's Declaration of Conformity - the US FCC route where the manufacturer tests the product and signs its own statement that it meets the rules, instead of getting a certificate from the FCC."),
    ("DoC", r"\bDoC\b|Declaration of Conformity", "the signed compliance statement", "Declaration of Conformity - the legally binding document a manufacturer signs stating which laws and standards the product meets. It must list the exact standard editions used."),
    ("CB Scheme", r"CB Scheme|CB Test Certificate|CB report|CB certificate", "the international safety-report passport", "IECEE CB Scheme - a mutual-recognition system in which one accredited lab's safety test report (with a CB Test Certificate) is accepted by certification bodies in 50+ countries, avoiding a full re-test in each."),
    ("IECEE", r"\bIECEE\b", "the body running the CB Scheme", "IEC System of Conformity Assessment Schemes for Electrotechnical Equipment - the organisation that operates the CB Scheme for electrical safety and EMC test reports."),
    ("TRF", r"\bTRF\b|Test Report Form", "the standard lab report template", "Test Report Form - the standardised report template labs must use under the CB Scheme so that another country's certifier can read and accept the results."),
    ("NRTL", r"\bNRTL\b", "a US-recognised safety lab", "Nationally Recognized Testing Laboratory - a lab (UL, Intertek, TÜV, CSA, etc.) recognised by US OSHA to certify products to US safety standards."),
    ("SELV", r"\bSELV\b", "very low voltage that cannot shock", "Safety Extra-Low Voltage - a circuit whose voltage is so low it cannot cause an electric shock. Bus-powered USB drives and memory cards are SELV, which is why most countries exempt them from mains-safety testing."),
    ("Class III", r"Class III", "equipment powered only from safe low voltage", "Class III equipment - protected against electric shock because it is powered only from a SELV source (for example a USB port) and has no mains connection."),
    ("ES1/ES2/ES3", r"\bES[123]\b", "energy-hazard classes in the safety standard", "Energy Source classes in IEC 62368-1: ES1 is safe to touch, ES2 may hurt but not injure, ES3 can injure. The class decides how much protection (insulation, enclosure) the design must provide."),
    ("TS1/TS2", r"\bTS[12]\b", "touch-temperature classes", "Thermal Source classes in IEC 62368-1: TS1 surfaces are safe to hold, TS2 may cause pain on prolonged contact. Each class has a maximum surface temperature that depends on the material (metal, plastic, glass)."),
    ("LVD", r"\bLVD\b|Low Voltage Directive", "the EU electrical-safety law", "Low Voltage Directive 2014/35/EU - the EU law covering electrical safety of equipment operating between 50 and 1000 V AC. Mains adapters fall under it; bus-powered drives do not."),
    ("EMCD", r"\bEMCD\b|EMC Directive", "the EU interference law", "EMC Directive 2014/30/EU - the EU law requiring products neither to emit excessive electromagnetic interference nor to be unduly disturbed by it."),
    ("RED", r"\bRED\b|Radio Equipment Directive", "the EU law for anything with a radio", "Radio Equipment Directive 2014/53/EU - applies to products with wireless functions. Wired storage is normally outside it unless it contains Wi-Fi or Bluetooth."),
    ("RoHS", r"\bRoHS\b", "the ban on hazardous substances in electronics", "Restriction of Hazardous Substances - a limit (usually 0.1 %, cadmium 0.01 %) on ten substances such as lead, mercury and certain flame retardants and plasticisers in every homogeneous material of an electronic product. Adopted with local variations in the EU, China, India, Saudi Arabia, Taiwan and elsewhere."),
    ("REACH", r"\bREACH\b", "the EU chemicals law", "Registration, Evaluation, Authorisation and Restriction of Chemicals - the EU chemicals regulation. Annex XVII lists restricted substances; the Candidate List (SVHC) triggers a duty to inform customers above 0.1 %."),
    ("SVHC", r"\bSVHC\b|Substances? of Very High Concern", "chemicals flagged for eventual phase-out", "Substance of Very High Concern - a chemical on the REACH Candidate List because it is carcinogenic, toxic to reproduction, or persistent and bio-accumulative. Presence above 0.1 % in an article must be communicated down the supply chain."),
    ("PFAS", r"\bPFAS\b", "'forever chemicals' used in coatings and cables", "Per- and polyfluoroalkyl substances - thousands of fluorinated chemicals (PTFE, FEP, PVDF and more) used in cable insulation, coatings, thermal pads and packaging barriers. They do not break down in nature, so regulators are restricting or demanding reporting of them."),
    ("TSCA", r"\bTSCA\b", "the US chemicals law", "Toxic Substances Control Act - the US federal chemicals law administered by the EPA. Section 8(a)(7) created the one-time PFAS reporting duty for manufacturers and importers of articles."),
    ("EPR", r"\bEPR\b|Extended Producer Responsibility", "the producer pays for recycling", "Extended Producer Responsibility - the principle that whoever puts a product or packaging on the market must register, report volumes and pay for its collection and recycling at end of life."),
    ("WEEE", r"\bWEEE\b", "the e-waste recycling law", "Waste Electrical and Electronic Equipment Directive - EU rules requiring producers to finance the collection and recycling of used electronics and to mark products with the crossed-out wheelie bin."),
    ("Triman", r"Triman", "France's mandatory recycling logo", "Triman - the French recycling pictogram that must appear on consumer products and packaging subject to EPR, together with Info-tri sorting instructions."),
    ("Info-tri", r"Info-tri", "France's sorting-instruction label", "Info-tri - the harmonised French signage telling consumers which bin each packaging component goes in (for example 'Bac Jaune' for cardboard and plastics)."),
    ("PPWR", r"\bPPWR\b", "the new EU packaging regulation", "Packaging and Packaging Waste Regulation - the EU regulation replacing Directive 94/62/EC, setting recyclability grades, minimum recycled-plastic content, empty-space limits and substance limits for all packaging."),
    ("AGEC", r"\bAGEC\b", "France's anti-waste law", "Loi Anti-Gaspillage pour une Économie Circulaire - France's 2020 anti-waste and circular-economy law, the legal basis for Triman/Info-tri labelling and repairability rules."),
    ("CRA", r"\bCRA\b|Cyber Resilience Act", "the EU product-cybersecurity law", "Cyber Resilience Act, Regulation (EU) 2024/2847 - the first EU-wide law imposing cybersecurity requirements on all products with digital elements, including secure-by-default firmware, vulnerability handling and an SBOM."),
    ("SBOM", r"\bSBOM\b|Software Bill of Materials", "a list of all software inside the product", "Software Bill of Materials - a machine-readable inventory (SPDX or CycloneDX format) of every software component and library inside a product's firmware, so vulnerabilities can be traced."),
    ("SPDX / CycloneDX", r"SPDX|CycloneDX", "the two standard SBOM file formats", "SPDX and CycloneDX - the two machine-readable formats regulators accept for a Software Bill of Materials."),
    ("ENISA", r"\bENISA\b", "the EU cybersecurity agency", "European Union Agency for Cybersecurity - receives mandatory vulnerability and incident reports under the Cyber Resilience Act and coordinates with national CSIRTs."),
    ("CSIRT", r"\bCSIRTs?\b", "a national cyber-incident response team", "Computer Security Incident Response Team - the national body (for example BSI in Germany, ANSSI in France) that must be notified of actively exploited vulnerabilities."),
    ("BIS", r"\bBIS\b", "India's standards body", "Bureau of Indian Standards - India's national standards and certification body, which runs the Compulsory Registration Scheme for electronics."),
    ("CRS", r"\bCRS\b|Compulsory Registration Scheme", "India's mandatory registration scheme", "Compulsory Registration Scheme - the Indian scheme under which listed electronic products must be tested in a BIS-recognised Indian lab and registered (receiving an R-number) before import or sale."),
    ("NABL", r"\bNABL\b", "India's lab accreditation body", "National Accreditation Board for Testing and Calibration Laboratories - the Indian accreditation body; BIS only accepts test reports from NABL-accredited, BIS-recognised labs located in India."),
    ("R-number", r"R-?number|R-8400|R-4\d{7}|R-xxx", "the Indian registration number printed on the label", "R-number - the BIS registration number (format R-xxxxxxxx) that must be printed on the product together with the Standard Mark. Each registration is tied to one standard edition, so a standard change requires a change request."),
    ("AIR", r"\bAIR\b|Authori[sz]ed Indian Representative", "the mandatory Indian legal representative", "Authorised Indian Representative - the Indian legal entity a foreign manufacturer must appoint to hold BIS registrations and file change requests on its behalf."),
    ("MeitY", r"\bMeitY\b", "India's IT ministry", "Ministry of Electronics and Information Technology - the Indian ministry that decides which electronic products fall under the Compulsory Registration Scheme."),
    ("KC mark", r"\bKC\b", "Korea's mandatory conformity mark", "KC (Korea Certification) mark - Korea's single conformity mark for safety and EMC. Active bus-powered storage needs KC EMC Conformity Registration with an RRA registration number on the label."),
    ("RRA", r"\bRRA\b", "Korea's radio & EMC regulator", "National Radio Research Agency - the Korean agency that sets EMC test standards and issues KC EMC registrations."),
    ("KATS", r"\bKATS\b", "Korea's standards & safety agency", "Korea Agency for Technology and Standards - Korea's national standards body responsible for the safety side of the KC mark."),
    ("KN 32 / KN 35", r"KN ?32|KN ?35|KS C 983[25]", "Korea's EMC emission/immunity standards", "KN 32 / KS C 9832 (emissions) and KN 35 / KS C 9835 (immunity) - the Korean adoptions of CISPR 32 and CISPR 35 used for KC EMC registration."),
    ("BSMI", r"\bBSMI\b", "Taiwan's product-inspection authority", "Bureau of Standards, Metrology and Inspection - Taiwan's certification and market-surveillance authority for electrical products."),
    ("RPC", r"\bRPC\b|Registration of Product Certification", "Taiwan's product registration scheme", "Registration of Product Certification - the BSMI scheme under which IT products are registered (with an R- or D-prefixed number) after type testing."),
    ("CNS 15663", r"CNS ?15663", "Taiwan's RoHS marking standard", "CNS 15663 - Taiwan's standard on reduction of restricted chemical substances; Section 5 requires a 'presence condition' table and the RoHS marking next to the BSMI mark."),
    ("CCC", r"\bCCC\b", "China's compulsory certificate", "China Compulsory Certification - the mandatory certification (CCC mark) for products in the CNCA catalogue, including power adapters; requires in-country testing and annual factory inspection."),
    ("CNCA", r"\bCNCA\b", "China's certification administrator", "Certification and Accreditation Administration of China - the body under SAMR that defines the CCC catalogue and implementation rules."),
    ("SAMR", r"\bSAMR\b", "China's market regulator", "State Administration for Market Regulation - China's top market-supervision authority, parent of CNCA and the CCC scheme."),
    ("CQC", r"\bCQC\b", "China's main CCC certification body", "China Quality Certification Centre - the largest CNCA-designated certification body issuing CCC certificates."),
    ("SJ/T 11364", r"SJ/T ?11364", "the China RoHS marking standard", "SJ/T 11364 - the China RoHS marking standard requiring the Environmental Friendly Use Period logo and a hazardous-substance table in Simplified Chinese."),
    ("EFUP", r"\bEFUP\b|Environmental Friendly Use Period", "China's 'safe-use years' logo", "Environmental Friendly Use Period - the China RoHS logo (a number inside a circle, e.g. 10 or 20 years) stating how long the product can be used before hazardous substances may leak."),
    ("PSE", r"\bPSE\b", "Japan's electrical-safety mark", "PSE mark - Japan's mandatory Product Safety Electrical Appliance & Materials mark (diamond or circle) under the DENAN law, mainly relevant to mains adapters."),
    ("VCCI", r"\bVCCI\b", "Japan's voluntary EMC mark", "Voluntary Control Council for Interference - Japan's industry EMC scheme; the VCCI mark is expected by Japanese retailers for IT equipment."),
    ("METI", r"\bMETI\b", "Japan's industry ministry", "Ministry of Economy, Trade and Industry - the Japanese ministry administering the DENAN electrical-safety law."),
    ("SASO", r"\bSASO\b", "Saudi Arabia's standards body", "Saudi Standards, Metrology and Quality Organization - Saudi Arabia's standards and conformity authority that runs the SABER platform."),
    ("SABER", r"\bSABER\b", "Saudi Arabia's online conformity portal", "SABER - the Saudi electronic platform where importers register products, upload test reports and obtain certificates before each shipment."),
    ("PCoC", r"\bPCoC\b", "the Saudi product certificate", "Product Certificate of Conformity - the SABER certificate for a product model, issued by an approved certification body and valid for one year."),
    ("SCoC", r"\bSCoC\b", "the Saudi per-shipment certificate", "Shipment Certificate of Conformity - the SABER certificate that must be issued for every individual shipment, linked to a valid PCoC, before customs clearance."),
    ("GSO", r"\bGSO\b", "the Gulf standards organisation", "GCC Standardization Organization - the Gulf states' standards body whose technical regulations (e.g. G-mark for low-voltage equipment) apply across the Gulf."),
    ("INMETRO", r"\bINMETRO\b", "Brazil's certification authority", "Instituto Nacional de Metrologia - Brazil's national metrology and certification body, mandatory for power adapters."),
    ("ANATEL", r"\bANATEL\b", "Brazil's telecom regulator", "Agência Nacional de Telecomunicações - Brazil's telecom regulator, relevant for products with radio functions."),
    ("NOM", r"\bNOM\b", "Mexico's mandatory standards", "Norma Oficial Mexicana - Mexico's mandatory technical standards (e.g. NOM-019 for IT equipment safety), certified by accredited Mexican bodies."),
    ("RCM", r"\bRCM\b", "Australia/New Zealand's compliance mark", "Regulatory Compliance Mark - the single mark for electrical safety and EMC in Australia and New Zealand, with registration on the national database."),
    ("ACMA", r"\bACMA\b", "Australia's EMC/radio regulator", "Australian Communications and Media Authority - regulates EMC and radio compliance in Australia."),
    ("UKCA", r"\bUKCA\b", "Great Britain's conformity mark", "UK Conformity Assessed - the Great Britain equivalent of CE marking after Brexit (CE remains accepted under current UK policy)."),
    ("PSTI", r"\bPSTI\b", "the UK connected-product security law", "Product Security and Telecommunications Infrastructure Act 2022 - the UK law requiring a Statement of Compliance, a vulnerability-disclosure policy and a stated security-update period for consumer connectable products."),
    ("OPSS", r"\bOPSS\b", "the UK product-safety regulator", "Office for Product Safety and Standards - the UK regulator enforcing PSTI and product-safety law."),
    ("IEC 62368-1", r"62368-1", "the current safety standard for IT and AV equipment", "IEC 62368-1 - the hazard-based safety standard for audio/video and IT equipment that replaced IEC 60950-1. Edition 4 (2023) tightens touch-temperature and USB Power Delivery fault testing."),
    ("IEC 60950-1", r"60950-1|IS 13252", "the withdrawn legacy IT safety standard", "IEC 60950-1 (and national adoptions such as India's IS 13252) - the old prescriptive IT safety standard, withdrawn internationally in 2020 and now being phased out by the last countries still accepting it."),
    ("CISPR 32", r"CISPR ?32", "the international emissions standard for multimedia", "CISPR 32 - the international EMC emissions standard for multimedia equipment (Class B for residential use), adopted as EN 55032, KN 32, CNS 15936 and others."),
    ("EN 55032", r"EN ?55032", "the EU version of CISPR 32", "EN 55032 - the European harmonised emissions standard for multimedia equipment giving presumption of conformity with the EMC Directive."),
    ("FCC Part 15B", r"Part 15|unintentional radiator", "US rules for devices that emit radio noise unintentionally", "FCC Part 15 Subpart B - US rules for unintentional radiators (digital devices); storage products use the Supplier's Declaration of Conformity route."),
    ("KDB", r"\bKDB\b", "an FCC guidance document", "Knowledge Database publication - the FCC's numbered guidance documents that explain how equipment authorisation rules must be applied."),
    ("Covered List", r"Covered List", "the US list of banned telecom vendors", "FCC Covered List - the list of companies (Huawei, ZTE, Hikvision, Dahua, Hytera and affiliates) whose equipment cannot receive FCC authorisation; applicants must attest their products contain none of it."),
    ("Prop 65", r"Prop(?:osition)? 65", "California's chemical warning law", "California Proposition 65 - requires a warning label on products that expose consumers to listed carcinogenic or reproductive-toxic chemicals."),
    ("SCIP", r"\bSCIP\b", "the EU database of hazardous substances in articles", "Substances of Concern In articles as such or in complex objects (Products) - the ECHA database where EU suppliers must notify articles containing SVHC above 0.1 %."),
    ("CPCB", r"\bCPCB\b", "India's pollution regulator", "Central Pollution Control Board - the Indian regulator that runs the e-waste EPR portal and sets recycling targets for producers."),
    ("E-Waste Rules", r"E-Waste \(Management\) Rules|E-Waste Rules", "India's e-waste and RoHS regulation", "India E-Waste (Management) Rules 2022 - require producers to register with CPCB, buy EPR recycling certificates against targets and comply with RoHS-equivalent substance limits (Schedule II)."),
    ("Level VI", r"Level VI", "the US efficiency grade for power adapters", "Level VI - the US Department of Energy efficiency marking for external power supplies; adapters must print the Roman numeral VI."),
    ("ErP", r"\bErP\b", "the EU eco-design energy rules", "Energy-related Products Directive 2009/125/EC - EU eco-design rules including standby power and external power-supply efficiency."),
    ("TCF", r"\bTCF\b|Technical Construction File", "the internal evidence file for a declaration", "Technical Construction File - the folder of test reports, drawings, attestations and risk assessments that backs a self-declaration and must be produced on request."),
    ("Technical File", r"Technical (?:Documentation )?File|technical file|Technical Documentation", "the evidence folder behind the declaration", "Technical File - the documentation (design, test reports, risk analysis, declarations) that a manufacturer must keep for 10 years and show to a regulator on request."),
    ("Placing on the market", r"plac(?:ed|ing) on the (?:EU )?(?:Single )?[Mm]arket|placed on the market|made available", "the legal moment a unit becomes subject to the rules", "Placing on the market - the first time an individual unit is made available in a jurisdiction (typically customs clearance). Units placed before a deadline can usually still be sold; units after it must meet the new rule."),
    ("Harmonised standard", r"[Hh]armoni[sz]ed standard", "a national/regional adoption of the international standard", "Harmonised standard - a national or regional standard adopted to be technically identical to the international one. In the EU it also means a standard listed in the Official Journal, which gives presumption of conformity with the corresponding directive."),
    ("Presumption of conformity", r"[Pp]resumption of conformity", "legal benefit of using the listed standard", "Presumption of conformity - the legal assumption that a product tested to the listed harmonised standard meets the law; it lapses when the standard's reference is withdrawn."),
    ("Notified Body", r"Notified Body", "an EU-appointed third-party certifier", "Notified Body - an independent organisation designated by an EU member state to assess conformity where third-party assessment is required (e.g. CRA Module B for important products)."),
    ("Module A/B/C", r"Module [ABC]\b", "the conformity-assessment routes", "Conformity-assessment modules: Module A is internal control (self-assessment); Module B is EU-type examination by a Notified Body; Module C is conformity to the examined type."),
    ("USB-PD", r"USB-PD|USB Type-C Power Delivery|Power Delivery", "high-power charging over USB-C", "USB Power Delivery - the USB-C protocol negotiating up to 240 W; safety standards now test fault conditions at the maximum negotiated power."),
    ("IPC-1752A", r"IPC-?1752A?", "the standard supplier material-declaration form", "IPC-1752A - the electronics-industry XML format for material declarations; Class D means full material disclosure down to substance level."),
    ("FMD", r"\bFMD\b|Full Material Declaration", "a complete substance-level parts list", "Full Material Declaration - a supplier document listing every substance and its concentration in a component, needed to prove RoHS/REACH/PFAS compliance."),
    ("XRF / GC-MS", r"\bXRF\b|GC-MS", "chemical screening test methods", "X-ray fluorescence (XRF) is a quick screening test for heavy metals; gas chromatography-mass spectrometry (GC-MS) confirms organic substances such as phthalates and flame retardants (IEC 62321 methods)."),
    ("TOF", r"\bTOF\b|Total Organic Fluorine", "the lab test used to detect PFAS", "Total Organic Fluorine - a combustion ion-chromatography test (EN 14582 / ASTM D7359) measuring all fluorine bound in organic compounds, used as a screening proxy for PFAS."),
    ("CAS number", r"CAS numbers?|\bCAS\b", "the unique ID of a chemical", "Chemical Abstracts Service registry number - the unique identifier for a chemical substance, required in chemical inquiries and regulatory filings."),
    ("ISO/IEC 17025", r"ISO(?:/IEC)? ?17025", "the accreditation standard for test labs", "ISO/IEC 17025 - the international standard for the competence of testing laboratories; regulators only accept reports from labs accredited to it."),
    ("MRA", r"\bMRA\b|Mutual Recognition Agreement", "a treaty to accept foreign test reports", "Mutual Recognition Agreement - a bilateral agreement under which one country's accredited lab results are accepted by another's regulator."),
    ("DGCCRF", r"\bDGCCRF\b", "France's consumer-protection enforcement agency", "Direction générale de la concurrence, de la consommation et de la répression des fraudes - the French agency inspecting products and packaging for compliance."),
    ("CITEO", r"\bCiteo\b|\bCITEO\b", "France's packaging EPR organisation", "Citeo - the French producer-responsibility organisation for household packaging that issues the Info-tri graphics charter and collects eco-contributions."),
    ("CONAI", r"\bCONAI\b", "Italy's packaging consortium", "Consorzio Nazionale Imballaggi - Italy's national packaging consortium that publishes environmental-labelling guidance and collects packaging fees."),
    ("ZATCA", r"\bZATCA\b", "Saudi customs authority", "Zakat, Tax and Customs Authority - the Saudi customs body that holds shipments lacking a SABER shipment certificate."),
    ("HS code", r"HS [Cc]odes?|8523\.51|tariff", "the customs classification number", "Harmonised System code - the international customs classification (8523.51 = solid-state non-volatile storage). Regulators attach requirements to HS codes, so a wrong code can trigger the wrong checks."),
    ("CDX", r"\bCDX\b|Central Data Exchange", "the EPA's online filing system", "Central Data Exchange - the US EPA's electronic reporting portal used for TSCA submissions such as PFAS Form U."),
    ("PCR content", r"\bPCR\b|post-consumer recycled", "recycled plastic from used products", "Post-consumer recycled content - plastic recovered from products already used by consumers, as opposed to factory scrap; PPWR sets minimum PCR percentages."),
    ("De minimis", r"de minimis", "a threshold below which a rule does not apply", "De minimis exemption - a minimum quantity below which reporting is not required. The TSCA PFAS rule has none, so even trace amounts must be reported."),
    ("Blue Guide", r"Blue Guide", "the EU's official guide to product rules", "EU Blue Guide - the European Commission's official guidance on how product legislation applies, including what 'placing on the market' means."),
    ("CAGE code", r"CAGE codes?", "a supplier identification code", "Commercial and Government Entity code - a unique identifier for suppliers used to trace parts back to the manufacturing entity and check it against sanctions or covered lists."),
    ("Secure boot", r"secure boot|root-of-trust|signed firmware|firmware signing|ECDSA|RSA-3072", "firmware that only runs if cryptographically signed", "Secure boot - a hardware root-of-trust in the controller verifies a cryptographic signature (ECDSA / RSA) on the firmware before executing it, so tampered firmware cannot run."),
    ("Gazette", r"[Gg]azette", "the official government publication", "Gazette - the official journal in which a government publishes laws and notifications; the gazette date is usually the legal start of a transition period."),
    ("Concurrent running", r"[Cc]oncurrent (?:running|migration|transition)|[Dd]ual-?running|transition (?:window|period)", "both old and new rules accepted for a while", "Concurrent running - a transition period during which both the old and the new standard are accepted; certificates to the old standard stop being valid at its end."),
    ("Delta testing", r"[Dd]elta (?:test|evaluation|report)", "testing only the differences between two standard editions", "Delta testing - re-testing only the clauses that changed between two editions of a standard, using the existing report for everything else; far cheaper than a full re-test."),
    ("Statement of Compliance", r"Statement of Compliance", "the UK PSTI signed statement", "Statement of Compliance - the signed document required by UK PSTI stating the product meets the security requirements and giving the defined security-update period."),
    ("VDP", r"\bVDP\b|[Vv]ulnerability [Dd]isclosure [Pp]olicy", "a published way to report security bugs", "Vulnerability Disclosure Policy - a public policy and contact point through which researchers can report security flaws, required by PSTI and the CRA."),
    ("TBBP-A", r"TBBP-?A|Tetrabromobisphenol", "a flame retardant in circuit boards", "Tetrabromobisphenol A - the brominated flame retardant reacted into most FR-4 circuit-board laminates; proposed for RoHS restriction."),
    ("MCCP", r"MCCPs?|[Cc]hlorinated [Pp]araffins", "a plasticiser in PVC cables", "Medium-chain chlorinated paraffins - plasticisers and flame retardants used in flexible PVC cable jackets; listed as SVHC and proposed for RoHS restriction."),
    ("PBB / PBDE", r"PBBs?|PBDEs?", "brominated flame retardants restricted by RoHS", "Polybrominated biphenyls and diphenyl ethers - flame retardants restricted to 0.1 % by every RoHS-type regulation."),
    ("Phthalates", r"[Pp]hthalates?|DEHP|DBP|BBP|DIBP", "plasticisers restricted since RoHS 3", "Phthalates (DEHP, BBP, DBP, DIBP) - plasticisers used to soften PVC, restricted to 0.1 % under EU RoHS since 2019 and by Saudi and Indian RoHS."),
    ("FR-4", r"FR-?4", "the standard circuit-board material", "FR-4 - the glass-reinforced epoxy laminate used for almost all printed circuit boards; its flame retardant (TBBP-A) is under review."),
    ("TIM", r"\bTIMs?\b|[Tt]hermal [Ii]nterface [Mm]aterial|thermal pad", "heat-transfer pads inside a drive", "Thermal interface material - pads or greases that carry heat from the controller to the enclosure; often silicone- or fluoropolymer-based and therefore in scope for PFAS rules."),
    ("Class B", r"Class B", "the stricter emissions limit for home use", "Class B - the EMC emissions limit class for equipment used in residential environments (stricter than Class A for industrial use)."),
    ("Market surveillance", r"[Mm]arket [Ss]urveillance", "regulators buying and testing products in shops", "Market surveillance - authorities purchasing products from retail, testing them and checking paperwork; failures lead to sales bans or recalls."),
]
_GLOSSARY_COMPILED = [(t, re.compile(p, 0 if (len(t) <= 6 and t.isupper()) else re.I), s, m) for t, p, s, m in GLOSSARY]

# Category grouping used to describe products in plain English
CATEGORY_GROUPS = [
    ("memory cards", {"sd_card", "micro_sd", "sd_express", "cf_card", "gaming_card"}),
    ("USB drives", {"usb_drive"}),
    ("portable SSDs", {"external_ssd_bus"}),
    ("desktop drives with a power adapter", {"external_ssd_powered"}),
    ("internal and data-centre SSDs", {"internal_ssd", "enterprise_ssd"}),
    ("card readers", {"card_reader"}),
]
UNIVERSAL_TOKENS = {"all", "all_storage_categories", "all_categories"}


# =========================================================================== small helpers
def _today():
    return _dt.date.today()


def _parse_date(value):
    """Best-effort ISO date from 'YYYY-MM-DD', 'YYYY', 'YYYY-YYYY' or free text. Returns date|None."""
    s = str(value or "").strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.match(r"^(\d{4})\s*[-–]\s*(\d{4})$", s)
    if m:
        return _dt.date(int(m.group(2)), 12, 31)
    m = re.match(r"^(\d{4})$", s)
    if m:
        return _dt.date(int(m.group(1)), 12, 31)
    return None


def _days_until(d):
    return (d - _today()).days if d else None


def _deadline_status(days, raw=""):
    if days is None:
        r = str(raw or "").lower()
        if any(w in r for w in ("enforced", "active", "completed", "in force", "immediate", "ongoing", "permanent")):
            return "Passed"
        return "Planned"
    if days < 0:
        return "Passed"
    if days <= 90:
        return "Imminent"
    if days <= 365:
        return "Approaching"
    return "Planned"


def _fmt_month(d):
    return d.strftime("%B %Y") if d else "an unspecified date"


def _fmt_date(d):
    return d.strftime("%d %b %Y") if d else "TBC"


def _sentences(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])(?<!\bNo\.)(?<!\bLeg\.)(?<!\bArt\.)(?<!\bSec\.)(?<!e\.g\.)(?<!i\.e\.)(?<!\bvs\.)(?<!\bcf\.)\s+(?=[A-Z(\"'0-9])", text)
    return [p.strip() for p in parts if len(p.strip()) > 12]


def _first_sentence(text, fallback=""):
    s = _sentences(text)
    return s[0] if s else fallback


def _shorten(text, max_words):
    words = str(text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(",;:") + "…"


def _dedup(seq):
    seen, out = set(), []
    for x in seq:
        k = re.sub(r"\W+", " ", str(x)).strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(x)
    return out


def _alert_text(alert):
    """Every textual content field of the alert concatenated - the corpus every detector reads.
    (Link labels are deliberately excluded: 'Portal' in a link title is not an obligation.)"""
    parts = [alert.get(k, "") for k in ("title", "standard", "summary", "detailed_summary", "technical_impact", "action_required", "source", "country", "status")]
    parts += [str(x) for x in (alert.get("compliance_checklist") or [])]
    parts += [str(m.get("phase", "")) for m in (alert.get("timeline_milestones") or []) if isinstance(m, dict)]
    return " ".join(str(p) for p in parts if p)


def _round_money(v):
    step = 500 if v < 20000 else 1000
    return int(round(v / step) * step)


def _money(low, high):
    return f"${low:,.0f} – ${high:,.0f}"


# =========================================================================== scope resolution
def _categories(alert, db):
    cats = alert.get("affected_categories") or []
    if not cats or any(str(c) in UNIVERSAL_TOKENS for c in cats):
        ids = list(db.PRODUCT_CATEGORIES.keys())
    else:
        ids = [c for c in cats if c in db.PRODUCT_CATEGORIES]
        ids += [c for c in cats if c not in db.PRODUCT_CATEGORIES]  # keep unknown ids visible
    return [{"id": c, "name": db.PRODUCT_CATEGORIES.get(c, {}).get("name", str(c).replace("_", " ").title())} for c in ids]


def _product_phrase(category_ids, db):
    ids = set(category_ids)
    if len(ids) >= len(db.PRODUCT_CATEGORIES) - 1:
        return "all our memory cards, USB drives and SSDs"
    groups = [label for label, members in CATEGORY_GROUPS if ids & members]
    if not groups:
        return "the affected storage products"
    if len(groups) == 1:
        return "our " + groups[0]
    return "our " + ", ".join(groups[:-1]) + " and " + groups[-1]


def _market_codes(alert, db):
    try:
        codes = _rs._alert_country_codes(alert, db.COUNTRIES_DB)
    except Exception:
        codes = set()
    if not codes and not any(alert.get(k) for k in ("country", "region", "country_code")):
        codes = set(db.COUNTRIES_DB.keys())  # no jurisdiction stated at all -> assume it applies everywhere
    return sorted(c for c in codes if c in db.COUNTRIES_DB)


def _scope_code(alert, codes, db):
    """Country code to feed resolve_product_impacts()."""
    cc = str(alert.get("country_code") or "").upper()
    if cc:
        return cc
    if len(codes) >= len(db.COUNTRIES_DB) * 0.9:
        return "GLOBAL"
    if len(codes) == 1:
        return codes[0]
    if codes and set(codes) <= _rs.EU_COUNTRIES:
        return "EU"
    return "GLOBAL" if not codes else "REGION"


def _jurisdiction_phrase(alert, codes, db):
    country = str(alert.get("country") or "").strip()
    cl = country.lower()
    if "iecee" in cl or "cb scheme" in cl:
        return "the 50+ countries that accept CB Scheme safety reports"
    if not country or len(codes) >= len(db.COUNTRIES_DB) * 0.9:
        return "every market we sell in"
    if "european union" in cl or "eu 27" in cl or cl == "eu":
        return "the European Union"
    if len(codes) == 1:
        name = db.COUNTRIES_DB[codes[0]].get("name", country)
        return "the " + name if name.startswith(("United", "Netherlands", "Philippines", "Czech")) else name
    return country


def _impacted_products(alert, codes, ctx, db):
    products = None
    try:
        if ctx and ctx.get("store"):
            products = ctx["store"].products()
    except Exception:
        products = None
    if products is None:
        products = list(getattr(db, "SAMPLE_PRODUCTS", []))
    cats = alert.get("affected_categories") or ["all_storage_categories"]
    cc = _scope_code(alert, codes, db)
    region = alert.get("region") or alert.get("country") or "Global"
    try:
        impacted = _rs.resolve_product_impacts(cats, country_code=cc if cc != "REGION" else "", region=region, products=products)
    except Exception:
        impacted = []
    if cc == "REGION" and codes:
        # multi-country scope that is not EU/global: intersect target markets with the code set
        codeset = set(codes)
        impacted = [p for p in products if (p.get("category_id") in cats or any(c in UNIVERSAL_TOKENS for c in cats))
                    and codeset & {m.upper() for m in p.get("target_markets", [])}]
        impacted = [{"id": p.get("id"), "sku": p.get("sku"), "name": p.get("name"), "category_id": p.get("category_id"),
                     "category_name": p.get("category_name"), "market_label": alert.get("region") or "Regional"} for p in impacted]
    return [{"id": p.get("id"), "sku": p.get("sku"), "name": p.get("name"), "category_id": p.get("category_id"),
             "category_name": p.get("category_name"), "market_label": p.get("market_label")} for p in impacted]


# =========================================================================== detectors
def _detect_action_types(alert):
    """Rank the kinds of work the alert demands. Word-boundary regexes keep 'designed' from
    triggering 'signed', and secondary types need at least two hits to count."""
    text = _alert_text(alert)
    pillar = alert.get("pillar") if alert.get("pillar") in _rs.PILLARS else _rs.infer_pillar(alert)
    scores = {key: sum(len(rx.findall(text)) for rx in spec["rx"]) for key, spec in ACTION_TYPES.items()}
    if pillar in ("Safety", "EMC"):
        scores["retest"] = max(scores["retest"], 2)
    if pillar == "Cyber" and (scores["firmware"] > 0 or max(v for k, v in scores.items() if k != "firmware") == 0):
        scores["firmware"] = max(scores["firmware"], 2)
    if pillar == "Environmental" and scores["supply_chain"] == 0 and scores["packaging"] == 0:
        scores["supply_chain"] = 2
    if pillar != "Cyber" and scores["firmware"] < 3:
        scores["firmware"] = 0  # a stray 'cyber'/'firmware' mention in a safety notice is not a firmware programme
    # 'document' work is implied by every change, so it never outranks a concrete work stream
    ranked = sorted((k for k in scores if scores[k] > 0 and k != "document"), key=lambda k: (-scores[k], ACTION_ORDER.index(k)))
    primary = ranked[:1]
    secondary = [k for k in ranked[1:] if scores[k] >= 2]
    out = primary + secondary[:2]
    if not out:
        out = ["document"]
    if "document" not in out:
        out.append("document")  # every regulatory change ends in an updated declaration / technical file
    return out


def _supply_flavour(alert):
    """Supply-chain work is either chemical (substances) or vendor-origin (attestations)."""
    text = _alert_text(alert).lower()
    chem = sum(text.count(k) for k in ("substance", "pfas", "rohs", "reach", "chemical", "phthalate", "flame retardant", "fluor", "cas number", "ppm"))
    vendor = sum(text.count(k) for k in ("covered list", "attestation", "cage code", "entity", "perjury", "sanction"))
    return "vendor" if vendor > chem else "chemical"


HARD_CONSEQUENCE_WORDS = ("detain", "seized", "cancel", "revoked", "recall", "criminal", "sales stop", "withdrawal", "compensation", "penalt")


def _hard_consequence(consequences, pillar):
    for c in consequences:
        if any(w in c.lower() for w in HARD_CONSEQUENCE_WORDS):
            return c.split(" - ")[0].split(":")[0].rstrip(".")
    return PILLAR_META.get(pillar, PILLAR_META["Safety"])["risks"][0]


def _glossary_for(alert):
    text = _alert_text(alert)
    hits = []
    for term, rx, short, meaning in _GLOSSARY_COMPILED:
        m = rx.search(text)
        if m:
            hits.append((m.start(), term, short, meaning))
    hits.sort()
    return [{"term": t, "meaning": m, "short": s} for _, t, s, m in hits]


def _expand_acronyms(text, glossary):
    """Simple audience: first occurrence of each acronym gets its plain meaning in brackets."""
    out = str(text or "")
    for g in glossary:
        term = g["term"]
        rx = next((c for c in _GLOSSARY_COMPILED if c[0] == term), None)
        if not rx:
            continue
        m = rx[1].search(out)
        if not m:
            continue
        matched = m.group(0)
        if len(matched) > 22:
            continue  # already a spelled-out phrase
        # extend to the end of the token so 'R-numbers' / '62368-1:2023' stay intact
        end = m.end()
        tail = re.match(r"[\w:./-]*", out[end:])
        if tail:
            end += tail.end()
        if out[end:end + 2].strip().startswith("("):
            continue  # already explained in the source text
        out = out[:end] + f" ({g['short']})" + out[end:]
    return out


def _extract_numbers(text):
    """Thresholds worth remembering: temperatures, ppm, %, dB, W, voltages, sizes."""
    rx = re.compile(r"(?:<|>|≤|≥|up to |maximum |minimum |below |above )?\d[\d,\.]*\s?(?:°C|ppm|ppb|%|wt%|dB\(?u?V/m\)?|dB|W\b|GHz|MHz|V\b|cm²|mg/kg|kg|m\b|years?|months?|hours?|hr)", re.I)
    found = []
    for m in rx.finditer(text or ""):
        start = max(0, m.start() - 60)
        ctxt = text[start:m.end() + 40]
        ctxt = re.sub(r"\s+", " ", ctxt).strip(" ,;(")
        found.append((m.group(0).strip(), ctxt))
    return found


def _obligation_sentences(alert, limit=3):
    corpus = " ".join(str(alert.get(k, "")) for k in ("detailed_summary", "technical_impact", "summary"))
    out = []
    for s in _sentences(corpus):
        sl = s.lower()
        if any(w in sl for w in (" must ", "mandat", "require", "shall", "prohibit", "banned", "no longer", "cannot", "legally")):
            out.append(s)
    return _dedup(out)[:limit]


def _exemption_sentences(alert, limit=2):
    corpus = " ".join(str(alert.get(k, "")) for k in ("detailed_summary", "technical_impact", "summary"))
    out = [s for s in _sentences(corpus) if re.search(r"\bexempt\b(?!ions?)|not listed in|remain(?:s)? (?:classified|outside|valid)|are not (?:listed|subject|covered)|out of scope|do(?:es)? not (?:apply|fall)", s, re.I)]
    return _dedup(out)[:limit]


def _consequences_in_text(alert):
    corpus = _alert_text(alert)
    low = corpus.lower()
    found = []
    for rx, sentence in CONSEQUENCE_PATTERNS:
        if re.search(rx, low):
            found.append(sentence)
    money = _dedup(m.group(0).strip() for m in MONEY_RE.finditer(corpus))
    if money:
        # quote the alert's own sentence containing the first monetary figure
        for s in _sentences(corpus):
            if MONEY_RE.search(s):
                found.append("Penalties cited in the notice: " + _shorten(s, 40))
                break
    return _dedup(found)


# =========================================================================== deadlines & schedule
def _deadlines(alert):
    out = []
    eff_raw = alert.get("effective_date")
    eff = _parse_date(eff_raw)
    eff_days = _days_until(eff)
    label = "Enforcement / effective date"
    if not eff and str(eff_raw or "").strip():
        label = f"Enforcement / effective date ({eff_raw})"
    out.append({"label": label, "date": eff.isoformat() if eff else None, "days_remaining": eff_days,
                "status": _deadline_status(eff_days, eff_raw), "kind": "effective"})
    for m in alert.get("timeline_milestones") or []:
        if not isinstance(m, dict):
            continue
        d = _parse_date(m.get("date"))
        days = _days_until(d)
        # a milestone dated today (e.g. "notice published") has happened - only the effective date counts as imminent at 0 days
        status = "Passed" if days is not None and days <= 0 else _deadline_status(days, m.get("status") or m.get("date"))
        out.append({"label": str(m.get("phase") or "Milestone"), "date": d.isoformat() if d else None,
                    "days_remaining": days, "status": status,
                    "kind": "milestone", "original_status": m.get("status")})
    # dedup identical (label,date)
    seen, uniq = set(), []
    for d in out:
        k = (d["label"].lower(), d["date"])
        if k not in seen:
            seen.add(k)
            uniq.append(d)
    uniq.sort(key=lambda d: (d["date"] is None, d["date"] or ""))
    return uniq


def _schedule(effective):
    """Back-scheduled due dates. Offsets are days before the effective date; squeezed when
    the runway is short and flipped to a forward plan when the date is past / unknown."""
    today = _today()
    offsets = {"assess": 180, "engage": 150, "execute": 60, "document": 30, "verify": 0, "monitor": -90}
    forward = {"assess": 14, "engage": 45, "execute": 90, "document": 120, "verify": 150, "monitor": 240}
    days = _days_until(effective) if effective else None
    plan = {}
    for k, off in offsets.items():
        if days is None or days <= 0:
            d = today + _dt.timedelta(days=forward[k])
        elif days >= 200:
            d = effective - _dt.timedelta(days=off)
        else:
            # proportional squeeze: keep ordering, land 'verify' on the effective date
            frac = max(0.0, 1 - off / 200.0)
            d = today + _dt.timedelta(days=int(round(days * frac))) if off > 0 else effective + _dt.timedelta(days=-off)
        if d < today:
            d = today
        plan[k] = d
    return plan


def _role_for(text, default=ROLE_RCE):
    t = str(text or "").lower()
    rules = [
        (ROLE_FW, ("firmware", "sbom", "secure boot", "bootloader", "vulnerab", "signed", "security patch", "support period", "vdp", "security@")),
        (ROLE_LAB, ("laborator", " lab", "test", "nabl", "cb report", "thermal", "emission", "sample", "iometer", "sweep", "trf", "exerciser")),
        (ROLE_LEGAL, ("tonnage", "annual return", "perjury", "statement of compliance", "epr", "eco-fee", "invoice", "hs code", "attestation", "identification number", "attorney", "penalt")),
        (ROLE_PKG, ("packaging", "artwork", "label", "logo", "emblem", "pictogram", "qr", "box", "blister", "carton", "die-line", "marking", "void", "recycled")),
        (ROLE_SCM, ("supplier", "vendor", "bill of materials", "bom", "material declaration", "ipc-1752", "cas number", "laminate", "cable", "foundr", "substance", "screen", "chemical", "attestation")),
        (ROLE_REP, ("representative", " air ", "importer", "local entity", "korean business", "us agent", "agent for service", "portal", "saber", "cpcb", "r-number", "registration certificate", "register")),
        (ROLE_LEGAL, ("legal", "sign", "statement of compliance", "perjury", "epr", "tonnage", "annual return", "fees", "penalt", "attorney", "invoice", "hs code", "customs", "declaration", "policy")),
    ]
    for role, kws in rules:
        if any(k in t for k in kws):
            return role
    return default


def _effort_for(role):
    return {ROLE_LAB: "L (8–16 weeks)", ROLE_FW: "L (12–24 weeks)", ROLE_PKG: "M (4–8 weeks)", ROLE_SCM: "M (6–12 weeks)",
            ROLE_LEGAL: "S (1–3 weeks)", ROLE_REP: "S (2–4 weeks)", ROLE_RCE: "S (2–4 weeks)"}.get(role, "M (3–6 weeks)")


def _phase_for_role(role):
    return {ROLE_LAB: "execute", ROLE_FW: "execute", ROLE_SCM: "engage", ROLE_PKG: "execute", ROLE_REP: "document",
            ROLE_LEGAL: "document", ROLE_RCE: "document"}.get(role, "execute")


def _what_to_do(alert, action_types, products, markets, standard, plan, product_phrase):
    steps = []
    n_prod = len(products)
    std = standard or "the new requirement"
    steps.append({
        "step": "Run a gap assessment against the new requirement",
        "detail": (f"Compare the current technical files of the {n_prod} impacted product{'s' if n_prod != 1 else ''} with {std}: "
                   f"which existing reports, declarations and labels still hold, and which clauses are new. Output: a delta list per SKU."),
        "owner_role": ROLE_RCE, "due_by": plan["assess"].isoformat(), "effort": "S (1–2 weeks)",
    })
    checklist = [str(x) for x in (alert.get("compliance_checklist") or []) if str(x).strip()]
    for item in checklist[:6]:
        role = _role_for(item)
        steps.append({"step": _shorten(item.rstrip("."), 12), "detail": item.rstrip(".") + ".", "owner_role": role,
                      "due_by": plan[_phase_for_role(role)].isoformat(), "effort": _effort_for(role)})
    if not checklist:
        # sparse alert: build a plan from the detected action types
        for a in action_types:
            spec = ACTION_TYPES[a]
            role = spec["role"]
            detail = {
                "retest": f"Book an accredited laboratory slot and ship samples so {product_phrase} are tested to {std}; ask the lab whether a delta report against the existing certificate is acceptable.",
                "firmware": f"Confirm secure-boot, signed firmware updates and a machine-readable SBOM for every controller platform in {product_phrase}; publish the vulnerability-disclosure contact and support period.",
                "packaging": f"Update retail artwork and labels for {product_phrase} to carry the markings required by {std}; validate proofs before printing.",
                "portal": f"File the registration / certificate update required by {std} through the local representative so the new certificate is live before the deadline.",
                "supply_chain": (f"Collect signed origin attestations from every silicon and sub-assembly supplier for {product_phrase} and check them against the restricted-vendor list."
                                 if _supply_flavour(alert) == "vendor" else
                                 f"Send material-declaration requests to every component supplier for {product_phrase} and screen high-risk materials for the restricted substances."),
                "document": f"Amend the Declaration of Conformity and technical file for {product_phrase} to cite {std}, and archive the evidence.",
            }[a]
            steps.append({"step": spec["label"].capitalize(), "detail": detail, "owner_role": role,
                          "due_by": plan[_phase_for_role(role)].isoformat(), "effort": _effort_for(role)})
    action_req = str(alert.get("action_required") or "").strip()
    if action_req and not any(action_req[:40].lower() in s["detail"].lower() for s in steps):
        role = _role_for(action_req)
        steps.append({"step": "Complete the required action named in the notice", "detail": action_req.rstrip(".") + ".",
                      "owner_role": role, "due_by": plan[_phase_for_role(role)].isoformat(), "effort": _effort_for(role)})
    steps.append({
        "step": "Update declarations, labels and the technical file; brief the channel",
        "detail": (f"Re-issue the Declaration of Conformity / statements citing {std}, update labels and packaging where needed, "
                   f"archive the new evidence and brief distributors and local representatives in {len(markets)} market{'s' if len(markets) != 1 else ''} on the cut-over date."),
        "owner_role": ROLE_RCE, "due_by": plan["document"].isoformat(), "effort": "S (1–2 weeks)",
    })
    steps.append({
        "step": "Verify readiness on the effective date and keep monitoring",
        "detail": "Confirm every impacted SKU has compliant paperwork before the deadline, run out non-compliant stock before it, and track the regulator's follow-up notices (amendments, FAQ, enforcement campaigns).",
        "owner_role": ROLE_RCE, "due_by": plan["verify"].isoformat(), "effort": "S (ongoing)",
    })
    # de-duplicate by step text, keep order, sort by due date but keep gap assessment first / verify last
    seen, uniq = set(), []
    for s in steps:
        k = s["step"].lower()
        if k not in seen:
            seen.add(k)
            uniq.append(s)
    middle = sorted(uniq[1:-1], key=lambda s: s["due_by"])
    ordered = [uniq[0]] + middle + [uniq[-1]]
    return ordered[:9]


# =========================================================================== cost model
def estimate_cost(pillar, action_types, n_products, n_markets, in_country, alert):
    """Rule-table estimate. Returns dict(cost_range, effort_range, basis, low, high)."""
    n_eff = 1 + 0.6 * (max(1, n_products) - 1)  # product families share test reports & declarations
    market_factor = 1 + 0.05 * min(max(0, n_markets - 1), 20)
    low = high = 0.0
    lines = []
    for a in action_types:
        spec = ACTION_TYPES[a]
        cost = spec["cost"].get(pillar) or spec["cost"].get("*") or (2000, 6000)
        lo, hi = cost
        if a == "firmware":
            platforms = max(1, min(3, int(round(n_products / 3.0)) or 1))
            l, h = lo * platforms, hi * platforms
            pl, ph = spec["per_product"]
            l += pl * n_eff
            h += ph * n_eff
            lines.append(f"{spec['label']}: {platforms} controller platform(s) × ${lo:,}–${hi:,} plus ${pl:,}–${ph:,} per product for documentation")
        elif a == "retest":
            factor = 1.5 if in_country else 1.0
            l, h = lo * n_eff * factor, hi * n_eff * factor
            lines.append(f"{spec['label']}: ${lo:,}–${hi:,} per product family{' ×1.5 for mandatory in-country testing' if in_country else ''}")
        elif spec.get("market_scaled"):
            l, h = lo * n_eff * market_factor, hi * n_eff * market_factor
            lines.append(f"{spec['label']}: ${lo:,}–${hi:,} per product, scaled ×{market_factor:.2f} for {n_markets} market(s)")
        elif a == "supply_chain":
            pl, ph = spec["program"]
            l, h = lo * n_eff + pl, hi * n_eff + ph
            lines.append(f"{spec['label']}: ${lo:,}–${hi:,} per product plus ${pl:,}–${ph:,} for the supplier-inquiry programme")
        else:
            l, h = lo * n_eff, hi * n_eff
            lines.append(f"{spec['label']}: ${lo:,}–${hi:,} per product")
        low += l
        high += h
    low, high = _round_money(low), _round_money(max(high, low + 1000))
    primary = ACTION_TYPES[action_types[0]]["effort"]
    weeks_low = primary[1]
    weeks_high = max(ACTION_TYPES[a]["effort"][2] for a in action_types)
    basis = (f"Indicative order-of-magnitude only, from the GCM rule table (pillar {pillar}). Assumes {n_products} impacted product(s) "
             f"treated as {n_eff:.1f} effective families sharing reports, {n_markets} market(s). Components: " + "; ".join(lines) +
             ". Excludes internal engineering time, sample hardware, travel, lost sales and any redesign found necessary by testing. "
             "Confirm with lab and certification-body quotations before budgeting.")
    return {"cost_range": _money(low, high), "effort_range": f"{weeks_low}–{weeks_high} weeks elapsed (work streams in parallel)",
            "basis": basis, "low": low, "high": high, "weeks_low": weeks_low, "weeks_high": weeks_high}


# =========================================================================== narrative builders
def _headline(alert, pillar, action_types, product_phrase, jurisdiction, eff, eff_raw):
    primary = action_types[0]
    plural_subject = jurisdiction.lower().startswith(("the 50+", "all "))
    req = "require" if plural_subject else "requires"
    supply = ("proof that {p} contain no parts from banned vendors" if _supply_flavour(alert) == "vendor"
              else "proof that {p} contain no restricted chemicals")
    verb = {
        "retest": f"{req} {product_phrase} to pass new {PILLAR_META.get(pillar, PILLAR_META['Safety'])['plain']} tests",
        "firmware": f"{req} provable firmware security and paperwork for {product_phrase}",
        "packaging": f"{req} new packaging markings on {product_phrase}",
        "portal": f"{req} a new registration before {product_phrase} can be shipped",
        "supply_chain": f"{req} " + supply.format(p=product_phrase),
        "document": f"{req} updated compliance paperwork for {product_phrase}",
    }[primary]
    subject = jurisdiction[0].upper() + jurisdiction[1:] if jurisdiction else "Regulators"
    if eff and _days_until(eff) >= 0:
        tail = f" by {_fmt_month(eff)}."
    elif eff:
        tail = f" — the {_fmt_month(eff)} deadline has passed."
    elif str(eff_raw or "").lower().startswith("enforc"):
        tail = " — already in force."
    else:
        tail = "."
    short_phrase = "our affected drives and cards"
    candidates = [
        f"{subject} {verb}{tail}",
        f"{subject} {verb.replace(product_phrase, short_phrase)}{tail}",
        f"{subject} {verb.replace(product_phrase, 'our products')}{tail}",
        f"{subject} {verb.replace(product_phrase, 'our products')}.",
    ]
    for text in candidates:
        if len(text.split()) <= 20:
            return text
    return " ".join(candidates[-1].split()[:19]).rstrip(",.") + "."


def _one_liner(alert, pillar, action_types, product_phrase, jurisdiction, eff, eff_raw, n_products, consequences, standard):
    src = str(alert.get("source") or "the regulator").strip()
    src = re.sub(r"\s*/\s*.*$", "", src) if len(src) > 45 else src  # keep the first named authority
    when = (f"from {_fmt_date(eff)}" if eff and _days_until(eff) >= 0 else "already in force" if (eff or str(eff_raw or "").lower().startswith("enforc")) else "on a date still to be confirmed")
    work = {
        "retest": "have their safety/EMC test reports and certificates re-issued to the new standard",
        "firmware": "prove secure firmware, publish a software inventory and keep security paperwork",
        "packaging": "carry new markings on the retail packaging",
        "portal": "be registered with the authority before shipment",
        "supply_chain": ("come with signed supplier attestations about where every component comes from" if _supply_flavour(alert) == "vendor"
                         else "come with supplier evidence that restricted substances are absent or declared"),
        "document": "have their declarations and technical files updated",
    }[action_types[0]]
    cons = _hard_consequence(consequences, pillar)
    cons = cons[0].lower() + cons[1:]
    std = f" under {standard}" if standard and len(standard) < 60 else ""
    n_txt = f"{n_products} of our products are" if n_products != 1 else "1 of our products is"
    return (f"In one sentence: {src} now requires {product_phrase} sold in {jurisdiction} to {work}{std}, {when}; "
            f"{n_txt} affected and, if we do nothing, the likely outcome is: {cons}.")


def _what_changed(alert, audience, glossary, pillar, product_phrase, jurisdiction, n_products, n_markets, eff, eff_raw, standard):
    summary = re.sub(r"^\[[^\]]+\]\s*", "", str(alert.get("summary") or "")).strip()
    detailed = str(alert.get("detailed_summary") or "").strip()
    tech = str(alert.get("technical_impact") or "").strip()
    obligations = _obligation_sentences(alert)
    exemptions = _exemption_sentences(alert)
    numbers = _extract_numbers(tech + " " + detailed)
    when = (f"The rule bites on {_fmt_date(eff)} ({_days_until(eff)} days from today)." if eff and _days_until(eff) >= 0
            else f"The rule has been in force since {_fmt_date(eff)}." if eff
            else "The rule is already in force." if str(eff_raw or "").lower().startswith("enforc")
            else "The enforcement date has not been fixed yet - treat it as imminent until the regulator confirms.")
    paras = []
    if audience == "executive":
        paras.append(f"What: {summary or alert.get('title', '')}")
        paras.append(f"Scope: {product_phrase} sold in {jurisdiction} - {n_products} of our products across {n_markets} market(s). {when}")
        if alert.get("action_required"):
            paras.append("Now what: " + _shorten(str(alert.get("action_required")), 45))
        elif obligations:
            paras.append("New obligation: " + _shorten(obligations[0], 45))
        if exemptions:
            paras.append("Not covered: " + _shorten(exemptions[0], 40))
    elif audience == "engineer":
        paras.append(f"Change: {summary or alert.get('title', '')} Reference: {standard or 'see notice'}.")
        paras.append(f"Scope: {product_phrase}; {n_products} SKU(s) in the portfolio; {n_markets} jurisdiction(s). {when}")
        if tech:
            paras.append("Technical impact: " + tech)
        for s in obligations[:2]:
            if s not in tech:
                paras.append("Obligation: " + s)
        if numbers:
            key = _dedup(n for n, _ in numbers)[:8]
            paras.append("Key figures in the notice: " + ", ".join(key) + ".")
        if exemptions:
            paras.append("Out of scope / exemptions: " + " ".join(exemptions))
    else:  # simple
        paras.append("The change: " + (summary or alert.get("title", "")))
        paras.append(f"Who and where: it applies to {product_phrase} sold in {jurisdiction}. {n_products} of our products and {n_markets} market{'s are' if n_markets != 1 else ' is'} affected. {when}")
        if alert.get("action_required"):
            paras.append("What we now have to do: " + str(alert.get("action_required")))
        elif obligations:
            paras.append("What we now have to do: " + _shorten(obligations[0], 50))
        detail_obl = [s for s in obligations if s not in (alert.get("summary") or "") and re.search(r"\bmust\b|required to|shall", s)]
        if detail_obl:
            paras.append("In the regulator's words: " + _shorten(detail_obl[0], 55))
        if exemptions:
            paras.append("Good news - what is NOT covered: " + _shorten(exemptions[0], 45))
        if numbers:
            key = _dedup(n for n, _ in numbers)[:5]
            paras.append("Numbers to remember: " + ", ".join(key) + ".")
        paras = [_expand_acronyms(p, glossary) for p in paras]
    return [p for p in paras if p and len(p) > 8]


def _why_it_matters(alert, audience, pillar, products, markets, consequences, cost, eff, action_types, glossary):
    meta = PILLAR_META.get(pillar, PILLAR_META["Safety"])
    n, m = len(products), len(markets)
    skus = ", ".join(p.get("sku") or p.get("name", "") for p in products[:3]) + (f" and {n - 3} more" if n > 3 else "")
    days = _days_until(eff)
    out = []
    if audience == "executive":
        out.append(f"Money: {cost['cost_range']} indicative programme cost, {cost['effort_range']}; the downside is losing access for {n} product(s) in {m} market(s).")
        out.append("So what: " + meta["business"])
        if consequences:
            out.append("Enforcement risk named in the notice: " + "; ".join(c.split(" - ")[0] for c in consequences[:2]) + ".")
        in_force = str(alert.get("effective_date") or "").lower().startswith("enforc")
        timing = ("deadline passed - exposure is live" if days is not None and days < 0
                  else f"{days} days of runway" if days is not None
                  else "already in force - exposure is live today" if in_force
                  else "date unconfirmed - plan as if imminent")
        out.append(f"Timing: {timing}; work streams: " + ", ".join(ACTION_TYPES[a]["label"] for a in action_types) + ".")
    elif audience == "engineer":
        out.append("Engineering: " + meta["engineering"])
        out.append(f"Affected hardware: {n} SKU(s){' - ' + skus if skus.strip() else ''}; work streams: " + ", ".join(ACTION_TYPES[a]["label"] for a in action_types) + ".")
        out.append("Business: " + meta["business"])
        if consequences:
            out.append("Enforcement consequences stated in the notice: " + "; ".join(consequences[:3]) + ".")
    else:
        out.append("For the business: " + meta["business"])
        if n:
            out.append(f"For us specifically: {n} product{'s' if n != 1 else ''} ({skus}) sold in {m} market{'s' if m != 1 else ''} depend on getting this right"
                       + (f", and there are {days} days left." if days is not None and days >= 0 else "."))
        out.append("For engineering: " + meta["engineering"])
        if consequences:
            out.append("What the regulator says happens otherwise: " + _hard_consequence(consequences, pillar) + ".")
        out = [_expand_acronyms(p, glossary) for p in out]
    return out


def _risks(alert, pillar, consequences, products, markets, eff):
    meta = PILLAR_META.get(pillar, PILLAR_META["Safety"])
    risks = list(consequences)

    def _stems(s):
        return {w[:6] for w in re.findall(r"[a-z]{6,}", s.lower())}

    for r in meta["risks"]:
        # skip a generic pillar risk when the notice-derived list already says the same thing
        if any(len(_stems(r) & _stems(x)) >= 2 for x in risks):
            continue
        risks.append(r)
    days = _days_until(eff)
    if days is not None and 0 <= days <= 120 and any(a in ("retest",) for a in _detect_action_types(alert)):
        risks.append(f"Lab capacity crunch: with {days} days left, accredited labs are already booked by competitors facing the same deadline")
    if len(products) >= 5:
        risks.append(f"Portfolio-wide exposure: {len(products)} products share this obligation, so a single missed deadline hits several revenue lines at once")
    return _dedup(risks)[:7]


def _suggested_questions(alert, pillar, standard, jurisdiction, product_phrase, eff, n_products, action_types):
    try:
        import expert_advisor
        cur = expert_advisor.CURATED_EXPERT_KNOWLEDGE.get(alert.get("id"), {}).get("suggested_questions")
        if cur:
            return list(cur)[:6]
    except Exception:
        pass
    std = standard or "this requirement"
    when = _fmt_date(eff) if eff else "the deadline"
    qs = [
        f"Which of our {n_products} impacted products need physical re-testing versus a paperwork-only update for {std}?",
        f"Can existing test reports or certificates be amended with a delta report instead of a full re-test under {std}?",
        f"What happens to stock already cleared through customs in {jurisdiction} on {when}?",
        f"What is a realistic lab lead time and budget for {product_phrase} in {jurisdiction}?",
    ]
    if "portal" in action_types or "packaging" in action_types:
        qs.append(f"Who must sign or file the paperwork in {jurisdiction}, and does it need a local representative?")
    if pillar in ("Environmental",):
        qs.append("Which components are the most likely sources of the restricted substances, and what evidence do suppliers need to provide?")
    if pillar == "Cyber":
        qs.append("Does this require third-party assessment or can we self-declare, and what must the SBOM contain?")
    return _dedup(qs)[:6]


def _confidence(alert, seed_ids, sources):
    aid = str(alert.get("id") or "")
    status = str(alert.get("status") or "").lower()
    rich = bool(alert.get("detailed_summary")) and bool(alert.get("technical_impact")) and bool(alert.get("compliance_checklist"))
    if aid in seed_ids and sources:
        return {"level": "High", "basis": f"Curated seed alert with {len(sources)} official source link(s), detailed legal summary, technical impact and checklist reviewed by the GCM knowledge base."}
    if aid.startswith("ALERT-SURV") or "surveillance" in status or alert.get("surveillance_event_id"):
        return {"level": "Medium", "basis": "Detected by the surveillance engine from a feed or gazette notice; fields were auto-enriched and should be verified against the official text before budgeting."}
    if rich and sources:
        return {"level": "Medium", "basis": "User-published alert with detailed content and source link; not yet cross-checked against the official gazette."}
    return {"level": "Low", "basis": "Sparse user-created alert - explanation is built from the title, summary and generic pillar knowledge. Add the official source, detailed summary and dates to raise confidence."}


def _sources(alert):
    out = []
    for l in alert.get("official_links") or []:
        if isinstance(l, dict) and l.get("url"):
            out.append({"label": str(l.get("label") or l["url"]), "url": str(l["url"])})
    su = alert.get("source_url")
    if su and not any(s["url"] == su for s in out):
        out.append({"label": f"{alert.get('source') or 'Notice'} – source", "url": str(su)})
    if not out:
        out.append({"label": f"No official link recorded - source cited as: {alert.get('source') or 'not stated'}", "url": ""})
    return out


# =========================================================================== public API
def explain_alert(alert, ctx=None, audience="simple"):
    """Build the Explanation shape (ARCHITECTURE_CONTRACT §4) for one alert."""
    if not isinstance(alert, dict):
        raise ValueError("alert must be a dict")
    audience = audience if audience in AUDIENCES else "simple"
    db = (ctx or {}).get("db") or _db
    pillar = alert.get("pillar") if alert.get("pillar") in _rs.PILLARS else _rs.infer_pillar(alert)
    standard = str(alert.get("standard") or "").strip()
    eff_raw = alert.get("effective_date")
    eff = _parse_date(eff_raw)

    categories = _categories(alert, db)
    cat_ids = [c["id"] for c in categories]
    product_phrase = _product_phrase(cat_ids, db)
    codes = _market_codes(alert, db)
    markets = [{"code": c, "name": db.COUNTRIES_DB[c].get("name", c)} for c in codes]
    jurisdiction = _jurisdiction_phrase(alert, codes, db)
    products = _impacted_products(alert, codes, ctx, db)
    action_types = _detect_action_types(alert)
    glossary = _glossary_for(alert)
    consequences = _consequences_in_text(alert)
    in_country = bool(re.search(r"in-country|nabl|designated (?:in-country )?lab|accredited chinese|rra-designated", _alert_text(alert), re.I)) or \
        (len(codes) == 1 and bool(db.COUNTRIES_DB.get(codes[0], {}).get("in_country_testing")) and "retest" in action_types)
    cost = estimate_cost(pillar, action_types, len(products), len(markets), in_country, alert)
    plan = _schedule(eff)
    seed_ids = {a.get("id") for a in getattr(db, "REGULATION_ALERTS", [])}
    sources = _sources(alert)
    deadlines = _deadlines(alert)

    result = {
        "alert_id": alert.get("id"),
        "audience": audience,
        "generated_by": "rules",
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine_version": ENGINE_VERSION,
        "pillar": pillar,
        "severity": alert.get("severity"),
        "title": alert.get("title"),
        "headline": _headline(alert, pillar, action_types, product_phrase, jurisdiction, eff, eff_raw),
        "one_liner": _one_liner(alert, pillar, action_types, product_phrase, jurisdiction, eff, eff_raw, len(products), consequences, standard),
        "what_changed": _what_changed(alert, audience, glossary, pillar, product_phrase, jurisdiction, len(products), len(markets), eff, eff_raw, standard),
        "why_it_matters": _why_it_matters(alert, audience, pillar, products, markets, consequences, cost, eff, action_types, glossary),
        "who_is_affected": {"categories": categories, "products": products, "markets": markets, "market_count": len(markets),
                            "product_phrase": product_phrase, "jurisdiction": jurisdiction},
        "what_to_do": _what_to_do(alert, action_types, products, markets, standard, plan, product_phrase),
        "deadlines": deadlines,
        "cost_effort_estimate": {k: cost[k] for k in ("cost_range", "effort_range", "basis", "low", "high")},
        "risk_if_ignored": _risks(alert, pillar, consequences, products, markets, eff),
        "jargon_glossary": [{"term": g["term"], "meaning": g["meaning"]} for g in glossary][:24],
        "confidence": _confidence(alert, seed_ids, [s for s in sources if s.get("url")]),
        "sources": sources,
        "suggested_questions": _suggested_questions(alert, pillar, standard, jurisdiction, product_phrase, eff, len(products), action_types),
        "action_types": action_types,
    }
    if audience == "simple":
        result["analogy"] = PILLAR_META.get(pillar, PILLAR_META["Safety"])["analogy"]
    if audience == "executive":
        owner = ACTION_TYPES[action_types[0]]["role"]
        result["decision"] = (f"Decision needed: approve {cost['cost_range']} and assign {owner} as lead; first checkpoint "
                              f"{plan['assess'].strftime('%d %b %Y')}, all evidence in place by {plan['document'].strftime('%d %b %Y')}.")
    return result


def brief_text(explanation):
    """Plain-text brief (for the 'Copy brief' button / clipboard / email)."""
    e = explanation or {}
    lines = [e.get("headline", ""), "", e.get("one_liner", ""), ""]
    lines += ["WHAT CHANGED"] + [f"- {p}" for p in e.get("what_changed", [])] + [""]
    lines += ["WHY IT MATTERS"] + [f"- {p}" for p in e.get("why_it_matters", [])] + [""]
    w = e.get("who_is_affected", {})
    lines += ["WHO IS AFFECTED",
              "- Categories: " + ", ".join(c.get("name", "") for c in w.get("categories", [])),
              "- Products: " + (", ".join(f"{p.get('sku')} ({p.get('name')})" for p in w.get("products", [])) or "none in portfolio"),
              f"- Markets: {w.get('market_count', 0)}", ""]
    lines += ["WHAT TO DO"] + [f"{i + 1}. {s.get('step')} — {s.get('owner_role')} — due {s.get('due_by')} — {s.get('effort')}\n   {s.get('detail')}" for i, s in enumerate(e.get("what_to_do", []))] + [""]
    lines += ["KEY DATES"] + [f"- {d.get('label')}: {d.get('date') or 'TBC'} ({d.get('status')})" for d in e.get("deadlines", [])] + [""]
    c = e.get("cost_effort_estimate", {})
    lines += ["COST & EFFORT", f"- {c.get('cost_range')} · {c.get('effort_range')}", f"- Basis: {c.get('basis')}", ""]
    lines += ["RISK IF IGNORED"] + [f"- {r}" for r in e.get("risk_if_ignored", [])] + [""]
    lines += ["SOURCES"] + [f"- {s.get('label')}: {s.get('url')}" for s in e.get("sources", [])]
    conf = e.get("confidence", {})
    lines += ["", f"Confidence: {conf.get('level')} — {conf.get('basis')}", f"Generated by: {e.get('generated_by')} at {e.get('generated_at')}"]
    return "\n".join(str(x) for x in lines)


# =========================================================================== grounded Q&A (offline)
# Answers a free-text question about one alert from evidence only: the alert's own text, the
# curated expert knowledge, the country records and the requirement-engine rules for the
# markets/categories the alert resolves to. No boilerplate: when the material does not say,
# the answer says so.
STOPWORDS = set("""a an the and or of to in on for with by at from as is are was were be been being do does did can could
should would will may might must our we us you your it its this that these those there their they them what which who whom
how when where why any all some not no yes if then than into over under about after before between during without within
also just only very more most much many still per via etc need needs needed get got have has had make made use used using
directly direct please tell me know""".split())
SYNONYM_GROUPS = {
    "accept": ["accept", "accepted", "acceptance", "recognise", "recognize", "recognised", "recognized", "valid", "validity", "honour", "honor", "overseas", "foreign", "abroad", "international"],
    "grandfather": ["grandfather", "grandfathered", "legacy", "stock", "inventory", "existing", "already", "shipped", "warehouse", "placed", "market", "transition", "concurrent", "sunset", "withdrawn", "cancelled", "canceled", "continue"],
    "adapter": ["adapter", "adaptor", "adapters", "psu", "mains", "charger", "powersupply", "ac/dc", "power"],
    "drive": ["drive", "drives", "ssd", "ssds", "storage", "unit", "device", "enclosure", "bus-powered", "buspowered", "selv", "exempt"],
    "rep": ["air", "representative", "importer", "agent", "local", "entity", "kyc", "authorised", "authorized"],
    "cost": ["cost", "costs", "fee", "fees", "price", "budget", "expensive", "charge", "usd", "$", "quote", "spend"],
    "sample": ["sample", "samples", "units", "prototypes", "golden"],
    "time": ["leadtime", "long", "weeks", "turnaround", "duration", "timeline", "slot", "slots", "schedule", "backlog", "months"],
    "test": ["test", "tests", "testing", "tested", "retest", "re-test", "laboratory", "lab", "labs", "report", "reports", "nabl", "cbscheme", "cb", "incountry", "accredited", "certificate", "certification"],
    "label": ["label", "labels", "labelling", "labeling", "marking", "markings", "mark", "marks", "print", "printed", "packaging", "logo", "artwork", "box", "carton", "symbol", "pictogram", "emblem", "qr", "blister"],
    "deadline": ["deadline", "date", "cutover", "cut-off", "cutoff", "effective", "enforce", "enforcement", "mandatory", "until"],
    "penalty": ["fine", "fines", "penalty", "penalties", "consequence", "consequences", "seizure", "seized", "detained", "detention", "customs", "risk", "happens", "ignore", "non-compliant", "noncompliant", "prohibited"],
    "document": ["document", "documents", "documentation", "declaration", "declarations", "file", "files", "paperwork", "doc", "technical", "form", "portal", "registration", "register", "filing"],
    "product": ["product", "products", "sku", "skus", "affected", "portfolio", "impacted", "models", "range"],
    "firmware": ["firmware", "sbom", "software", "vulnerability", "vulnerabilities", "secure", "boot", "signed", "patch", "update", "updates", "cyber"],
    "chemical": ["pfas", "substance", "substances", "chemical", "chemicals", "rohs", "reach", "material", "materials", "ppm", "fluorine", "phthalate"],
}
_SYN_INDEX = {w: g for g, ws in SYNONYM_GROUPS.items() for w in ws}
PHRASE_NORMALISE = [
    (r"power suppl(?:y|ies)", "powersupply adapter"), (r"lead[- ]time", "leadtime"), (r"how long", "leadtime"), (r"how much", "cost"),
    (r"cb[- ]scheme", "cbscheme"), (r"in[- ]country", "incountry"), (r"bus[- ]powered", "buspowered"), (r"test reports?", "testreport test report"),
    (r"placed on the market", "placed market grandfather"), (r"after the deadline", "deadline grandfather"), (r"what happens", "happens penalty"),
    (r"local rep(?:resentative)?", "representative rep"), (r"authori[sz]ed indian representative", "representative air"),
]
INTENT_RULES = [
    ("cb_acceptance", {"accept", "test"}, {"cb", "cbscheme", "overseas", "foreign", "accept", "accepted", "recognise", "recognize"}),
    ("what_tested", {"adapter", "drive", "test"}, {"adapter", "drive", "only", "or"}),
    ("grandfather", {"grandfather"}, {"stock", "inventory", "grandfather", "legacy", "already", "existing", "shipped"}),
    ("local_rep", {"rep"}, {"representative", "air", "importer", "agent", "rep"}),
    ("cost_lead", {"cost", "time", "sample"}, {"cost", "fee", "price", "leadtime", "long", "weeks", "turnaround", "sample", "budget", "take"}),
    ("labels", {"label"}, {"label", "labels", "packaging", "print", "printed", "marking", "markings", "mark", "marks", "logo", "artwork", "box"}),
    ("penalty", {"penalty"}, {"fine", "fines", "penalty", "penalties", "consequence", "consequences", "happens", "risk", "ignore", "seized", "detained"}),
    ("deadline", {"deadline"}, {"deadline", "when", "date", "cutover", "effective", "until"}),
    ("products", {"product"}, {"which", "products", "product", "sku", "skus", "affected", "impacted", "portfolio"}),
    ("documents", {"document"}, {"documents", "document", "paperwork", "declaration", "file", "form", "portal", "registration"}),
    ("firmware", {"firmware"}, {"firmware", "sbom", "software", "vulnerability", "vulnerabilities", "secure", "boot", "signed", "patch"}),
    ("chemical", {"chemical"}, {"pfas", "substance", "substances", "chemical", "chemicals", "rohs", "reach", "material", "materials"}),
]
BUS_POWERED_CATEGORIES = {"sd_card", "micro_sd", "sd_express", "cf_card", "gaming_card", "usb_drive", "external_ssd_bus", "card_reader"}
MAINS_CATEGORIES = {"external_ssd_powered"}
HOST_POWERED_CATEGORIES = {"internal_ssd", "enterprise_ssd"}
_STANDARD_RX = re.compile(r"(?:IS/IEC|IEC|EN(?: IEC)?|UL|CISPR|KS C|CNS|GB|SJ/T|IS)\s?\d{3,6}(?:[-.]\d+)*(?::\d{4})?|Clause \d+(?:\.\d+)*|Article \d+(?:\(\d+\))?|Annex [A-Z]\b|Section \d+(?:\(\w\)(?:\(\d+\))?)?|\d{2} CFR (?:Part )?\d+(?:\.\d+)?|Regulation \(EU\) \d{4}/\d+|Directive \d{4}/\d+/EU|Decree No\.? \d{4}-\d+|Decision \d+/\d+/EC|Schedule II|Form [IU]\b|KDB \d+", re.I)


def _stem(w):
    w = w.lower()
    if len(w) > 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 5 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 4 and w.endswith("ed"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _tokens(text):
    t = str(text or "").lower()
    for rx, rep in PHRASE_NORMALISE:
        t = re.sub(rx, rep, t)
    raw = re.findall(r"[a-z0-9][a-z0-9\-/\.]*[a-z0-9]|[a-z0-9]", t)
    return [w for w in raw if w not in STOPWORDS and len(w) >= 2]


def _sig(tokens):
    """(stems, synonym groups) for a token list."""
    stems, groups = set(), set()
    for w in tokens:
        stems.add(_stem(w))
        g = _SYN_INDEX.get(w) or _SYN_INDEX.get(_stem(w))
        if g:
            groups.add(g)
    return stems, groups


def _primary_markets(alert, codes, db):
    cc = str(alert.get("country_code") or "").upper()
    if cc in db.COUNTRIES_DB:
        return [cc]
    if len(codes) == 1:
        return codes
    if codes and set(codes) <= _rs.EU_COUNTRIES:
        pref = [c for c in ("DE", "FR", "IT", "NL", "ES") if c in codes]
        return (pref + [c for c in codes if c not in pref])[:3]
    if len(codes) >= len(db.COUNTRIES_DB) * 0.9:
        return [c for c in ("US", "DE", "IN") if c in db.COUNTRIES_DB]
    return codes[:3]


def _rule_categories(alert, db):
    cats = [c for c in (alert.get("affected_categories") or []) if c in db.PRODUCT_CATEGORIES]
    if not cats:
        cats = ["external_ssd_powered", "external_ssd_bus", "usb_drive", "sd_card", "internal_ssd"]
    ordered = [c for c in cats if c in MAINS_CATEGORIES] + [c for c in cats if c in BUS_POWERED_CATEGORIES] + [c for c in cats if c in HOST_POWERED_CATEGORIES]
    return _dedup(ordered)[:5]


def build_evidence_corpus(alert, ctx=None):
    """List of {text, source, kind} sentences that may answer questions about this alert."""
    db = (ctx or {}).get("db") or _db
    corpus = []

    def add(text, source, kind, para=None):
        sents = _sentences(text) or ([str(text).strip()] if str(text or "").strip() else [])
        for s in sents:
            if len(s) >= 12:
                corpus.append({"text": s, "source": source, "kind": kind, "para": para if len(sents) == 1 else None})

    add(alert.get("title"), "alert title", "alert")
    add(alert.get("summary"), "alert summary", "alert")
    add(alert.get("detailed_summary"), "alert detailed summary", "alert")
    add(alert.get("technical_impact"), "alert technical impact", "alert")
    add(alert.get("action_required"), "alert required action", "alert")
    for c in alert.get("compliance_checklist") or []:
        add(str(c).rstrip(".") + ".", "alert checklist", "alert")
    for m in alert.get("timeline_milestones") or []:
        if isinstance(m, dict):
            d = _parse_date(m.get("date"))
            when = f"{m.get('date')}" + (f" ({_days_until(d)} days from today)" if d and _days_until(d) >= 0 else " (already passed)" if d else "")
            add(f"Timeline milestone: {m.get('phase')} - {when}; notice status: {m.get('status')}.", "alert timeline", "alert",
                para=f"the notice's milestone '{m.get('phase')}' is dated {when}")
    for l in alert.get("official_links") or []:
        if isinstance(l, dict) and l.get("label"):
            add(f"Official source: {l.get('label')}.", "alert official link", "link")
    try:
        import expert_advisor
        cur = expert_advisor.CURATED_EXPERT_KNOWLEDGE.get(alert.get("id"), {})
    except Exception:
        cur = {}
    for key, label in (("legal_authority", "Legal basis"), ("enforcing_body", "Enforcing body"), ("testing_standards", "Test standards"), ("hardware_scope", "Hardware in scope")):
        if cur.get(key):
            add(f"{label}: {cur[key]}.", "curated knowledge", "curated")
    for clause in cur.get("technical_clauses") or []:
        add(str(clause).rstrip(".") + ".", "curated knowledge", "curated")
    add(cur.get("engineering_guidance"), "curated knowledge (engineering guidance)", "curated")
    add(cur.get("lab_recommendations"), "curated knowledge (lab recommendation)", "curated")
    codes = _market_codes(alert, db)
    markets = _primary_markets(alert, codes, db)
    cats = _rule_categories(alert, db)
    for code in markets:
        c = db.COUNTRIES_DB.get(code) or {}
        name = c.get("name", code)
        src = f"{name} country record"
        add(c.get("notes"), src, "country")
        if c.get("in_country_testing"):
            cb_txt = "CB Scheme test reports count only as supporting evidence because in-country testing is required" if c.get("cb_scheme_accepted") else "CB Scheme test reports are not accepted and in-country testing is required"
        else:
            cb_txt = "CB Scheme test reports are accepted and in-country testing is not required" if c.get("cb_scheme_accepted") else "CB Scheme test reports are not accepted, although in-country testing is not required either"
        add(f"In {name} the authority is {c.get('authority', 'the national regulator')}; {cb_txt}.", src, "country")
        add(f"In {name} a local representative is {'required' if c.get('local_rep_required') else 'not required'}; typical certification lead time is {c.get('lead_time_weeks', 'n/a')} weeks and certificates are valid for {c.get('cert_validity', 'the stated period')}.", src, "country")
        if c.get("marks"):
            add(f"Marks / labels applicable in {name}: {', '.join(c.get('marks'))}.", src, "country")
        for k, label in (("safety_std", "safety standard"), ("emc_std", "EMC standard"), ("rohs_std", "RoHS standard"), ("packaging_std", "packaging rule"), ("epr_std", "EPR rule")):
            if c.get(k):
                add(f"The {label} on file for {name} is: {c[k]}.", src, "country", para=f"the {label} on file for {name} is {c[k]}")
        for cat in cats:
            try:
                rule = db.get_country_product_requirement(code, cat) or {}
            except Exception:
                rule = {}
            if not rule:
                continue
            cname = rule.get("category_name") or db.PRODUCT_CATEGORIES.get(cat, {}).get("name", cat)
            rsrc = f"requirement rule: {cname} in {name}"
            add(f"For {cname} in {name} the requirement is '{rule.get('requirement_type')}' with testing location '{rule.get('testing_location')}' and safety status '{rule.get('safety_status')}'.", rsrc, "rule",
                para=f"for {cname} in {name} the requirement is '{rule.get('requirement_type')}' with testing at {rule.get('testing_location')}")
            docs = rule.get("required_documents") or []
            if docs:
                add(f"Documents required for {cname} in {name}: {'; '.join(docs)}.", rsrc, "rule_docs",
                    para=f"the {cname} rule for {name} lists these documents: {'; '.join(docs[:4])}{'; …' if len(docs) > 4 else ''}")
            if rule.get("notes"):
                add(rule.get("notes"), rsrc, "rule")
    seen, out = set(), []
    for e in corpus:
        k = re.sub(r"\W+", " ", e["text"]).strip().lower()
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out


def _score_sentence(q_stems, q_groups, sentence):
    s_stems, s_groups = _sig(_tokens(sentence))
    exact = len(q_stems & s_stems)
    syn = len(q_groups & s_groups)
    return exact * 1.0 + syn * 0.6, exact


def detect_intent(question):
    toks = _tokens(question)
    stems, groups = _sig(toks)
    words = set(toks) | stems
    best, best_score = "generic", 0
    for intent, need_groups, cue_words in INTENT_RULES:
        score = len(groups & need_groups) * 1.0 + len(words & cue_words) * 1.5
        if intent == "what_tested" and not ({"adapter", "drive"} & groups):
            score = 0
        if intent == "cb_acceptance" and not ({"cb", "cbscheme", "overseas", "foreign", "accept", "accepted", "recognise", "recognize", "recognised", "recognized"} & words):
            score = 0
        if score > best_score:
            best, best_score = intent, score
    return best if best_score >= 1.5 else "generic"


INTENT_FOCUS = {  # sentences matching the intent's focus regex are what a human would quote
    "cb_acceptance": r"cb scheme|cb test|in-country|nabl|accredited lab|overseas|accepted|recogni|test reports? (?:must|are)",
    "what_tested": r"adapter|power suppl|bus-powered|selv|exempt|enclosure|must be tested|tested to",
    "grandfather": r"placed on the (?:eu )?(?:single )?market|made available|stock|inventory|concurrent|transition|withdraw|cancel|legacy|sunset|grace|clear(?:ed|ing) customs",
    "local_rep": r"representative|importer|agent|local entity|kyc|\bair\b",
    "cost_lead": r"lead time|weeks|cost|fee|samples?|units|backlog|slot|turnaround",
    "labels": r"label|mark(?:ing|s)?\b|logo|packag|print|pictogram|emblem|qr|triman|info-tri|coding|artwork",
    "deadline": r"deadline|milestone|effective|cutover|cut-off|\d{4}-\d{2}-\d{2}|sunset",
    "penalty": r"fine|penalt|seiz|detain|customs|revoc|recall|criminal|prohibit|blocked|held",
    "products": r"products?|sku|categor|scope|applies to",
    "documents": r"document|declaration|certificate|report|technical file|form|portal|registration",
    "firmware": r"firmware|sbom|secure boot|vulnerab|sign|software|patch",
    "chemical": r"substance|pfas|rohs|reach|chemical|material|ppm|phthalate|fluor|flame retardant",
}


def _rank_evidence(question, corpus, intent, limit=4):
    q_stems, q_groups = _sig(_tokens(question))
    boost_kind = {"cb_acceptance": ("alert", "rule"), "what_tested": ("alert", "rule"), "local_rep": ("country", "rule"), "cost_lead": ("country", "curated"),
                  "labels": ("alert",), "documents": ("rule", "alert"), "deadline": ("alert",), "penalty": ("alert",), "grandfather": ("alert",)}.get(intent, ("alert",))
    focus = re.compile(INTENT_FOCUS[intent], re.I) if intent in INTENT_FOCUS else None
    docs_ok = intent in ("documents", "local_rep")
    scored = []
    for e in corpus:
        if e["kind"] == "rule_docs" and not docs_ok:
            continue  # long document lists only answer 'which documents' questions
        score, exact = _score_sentence(q_stems, q_groups, e["text"])
        if e["source"] == "alert title":
            score -= 0.4  # titles are headlines, not evidence
        if focus and focus.search(e["text"]):
            score += 1.5
        elif focus:
            score -= 0.5
        if e["kind"] in boost_kind:
            score += 0.5
        if e["kind"] == "link":
            score -= 1.0
        n_tok = len(_tokens(e["text"]))
        if n_tok > 28:  # long document lists collect synonym hits without being more relevant
            score -= 0.03 * (n_tok - 28)
        if score > 0.6:
            scored.append((score, exact, e))
    scored.sort(key=lambda x: (-x[0], -x[1], len(x[2]["text"])))
    picked, seen_text = [], set()
    for score, exact, e in scored:
        if e["text"] in seen_text:
            continue
        seen_text.add(e["text"])
        picked.append({"text": e["text"], "source": e["source"], "kind": e["kind"], "para": e.get("para"), "score": round(score, 2), "exact": exact})
        if len(picked) >= limit:
            break
    return picked


def grounded_answer(alert, question, ctx=None, explanation=None):
    """Offline, evidence-grounded answer. Returns dict(expert_answer, direct_answer, evidence,
    cited_clauses, action_advice, confidence, intent, generated_by)."""
    db = (ctx or {}).get("db") or _db
    question = str(question or "").strip()
    intent = detect_intent(question)
    corpus = build_evidence_corpus(alert, ctx)
    evidence = _rank_evidence(question, corpus, intent)
    strong = [e for e in evidence if e["exact"] >= 2 or e["score"] >= 2.4]
    codes = _market_codes(alert, db)
    markets = _primary_markets(alert, codes, db)
    primary = db.COUNTRIES_DB.get(markets[0]) if markets else None
    pname = (primary or {}).get("name") or str(alert.get("country") or "the market")
    pillar = alert.get("pillar") if alert.get("pillar") in _rs.PILLARS else _rs.infer_pillar(alert)
    standard = str(alert.get("standard") or "the referenced standard")
    cats = [c for c in (alert.get("affected_categories") or []) if c in db.PRODUCT_CATEGORIES]
    universal = not cats or any(c in UNIVERSAL_TOKENS for c in (alert.get("affected_categories") or []))
    eff = _parse_date(alert.get("effective_date"))
    days = _days_until(eff)
    in_force_raw = str(alert.get("effective_date") or "").lower().startswith("enforc")
    eff_txt = _fmt_date(eff) if eff else ("already in force" if in_force_raw else "a date not yet fixed")
    rules = {}
    for cat in _rule_categories(alert, db):
        if markets:
            try:
                rules[cat] = db.get_country_product_requirement(markets[0], cat) or {}
            except Exception:
                rules[cat] = {}
    in_country_rule = any("in-country" in str(r.get("requirement_type", "")).lower() or "in-country" in str(r.get("testing_location", "")).lower() for r in rules.values())
    in_country = bool((primary or {}).get("in_country_testing")) or in_country_rule or bool(re.search(r"in-country|nabl-accredited|accredited chinese|rra-designated", _alert_text(alert), re.I))
    cb_ok = bool((primary or {}).get("cb_scheme_accepted", True))
    text_lower = _alert_text(alert).lower()

    direct, support, advice, clauses, level = "", [], "", [], None

    if intent == "cb_acceptance":
        if pillar not in ("Safety", "EMC"):
            art = "an" if pillar.lower()[0] in "aeiou" else "a"
            direct = f"Not in the usual sense - this is {art} {pillar.lower()} requirement, so CB Scheme safety reports are not the evidence the regulator asks for here."
            support.append(f"What is required instead: {_shorten(alert.get('action_required') or alert.get('summary') or '', 40)}")
            level = "Medium"
        elif in_country:
            direct = (f"No - {pname} requires the {'safety' if pillar == 'Safety' else 'EMC'} test to be run in an in-country accredited laboratory, so an overseas CB Scheme report cannot be accepted directly; "
                      f"it can only support the technical file and shorten the local delta test.")
            level = "High" if (strong or in_country_rule) else "Medium"
        elif cb_ok:
            direct = f"Yes - {pname} accepts CB Scheme test reports, so an existing CB report and certificate to the mandated edition of {standard} can be used for the national approval without a new full test."
            level = "High" if strong else "Medium"
        else:
            direct = f"It depends - the country record for {pname} does not confirm CB Scheme acceptance; treat the report as supporting evidence only and confirm the route with the certification body."
            level = "Medium"
        r = next((r for r in rules.values() if r.get("testing_location") and (in_country_rule is False or "in-country" in str(r.get("requirement_type", "")).lower() or "in-country" in str(r.get("testing_location", "")).lower())), None)
        if r and pillar in ("Safety", "EMC"):
            support.append(f"The requirement rule for {r.get('category_name')} in {pname} reads '{r.get('requirement_type')}' with testing at {r.get('testing_location')}.")
        advice = ("Ship samples to the accredited local lab early and ask it to issue a delta report against the existing CB report to shorten the test plan." if in_country
                  else "Ask the certification body to convert the existing CB Test Certificate; check that the report edition matches the edition the regulator now mandates.")

    elif intent == "what_tested":
        mains = [c for c in cats if c in MAINS_CATEGORIES] or (["external_ssd_powered"] if universal else [])
        bus = [c for c in cats if c in BUS_POWERED_CATEGORIES] or (sorted(BUS_POWERED_CATEGORIES) if universal else [])
        host = [c for c in cats if c in HOST_POWERED_CATEGORIES]
        if pillar == "Safety":
            if mains and (bus or host):
                direct = (f"Mainly the power adapter and the mains-powered enclosure - bus-powered drives and cards are SELV (safe extra-low voltage) and stay exempt from mains-safety testing unless bundled with a mains adapter; "
                          f"the adapter and the powered desktop unit must be tested to {standard}.")
            elif mains:
                direct = f"The mains adapter and the powered enclosure - that is what {standard} safety testing covers for this alert; nothing in the notice extends mains-safety testing to bus-powered products."
            else:
                direct = f"For these bus-powered categories the drive itself is normally SELV-exempt from mains-safety testing; this alert targets {', '.join(db.PRODUCT_CATEGORIES.get(c, {}).get('name', c) for c in cats[:3]) or 'the listed categories'} - check the scope sentence quoted below."
            for cat in ("external_ssd_bus", "external_ssd_powered"):
                r = rules.get(cat)
                if r:
                    support.append(f"Requirement rule for {r.get('category_name')} in {pname}: {r.get('safety_status')} - {r.get('requirement_type')}.")
            level = "High" if (rules.get("external_ssd_powered") or strong) else "Medium"
            advice = "List every SKU bundled with an AC/DC adapter; those adapters (and any mains-powered enclosure) go to the lab, bus-powered SKUs only need a scope confirmation in the technical file."
        elif pillar == "EMC":
            direct = f"The drive - EMC emissions come from the storage device's controller and interface, so the unit itself, exercised with continuous traffic, is tested to {standard}; a bundled adapter is tested as part of the system."
            level = "High" if strong else "Medium"
            advice = "Prepare test firmware that runs continuous read/write traffic on the highest-speed interface during the EMC scan."
        elif pillar == "Cyber":
            direct = "The drive - specifically its firmware and controller: secure boot, signed updates, SBOM and vulnerability handling are assessed; a passive power adapter has no digital element and is out of scope."
            level = "High" if strong else "Medium"
            advice = "Document the controller platforms behind each SKU; one technical file per platform covers all SKUs sharing it."
        else:
            direct = "Both, in a different way - substance rules apply to every material in the finished article (drive, adapter, cable) and to its packaging, so the evidence is supplier material declarations rather than a lab test of one part."
            level = "Medium"
            advice = "Request material declarations per component (PCBA, enclosure, cable, adapter, packaging) rather than per finished product."

    elif intent == "grandfather":
        cancel = any(k in text_lower for k in ("cancelled and withdrawn", "cancel", "withdrawn", "revoked"))
        concurrent = any(k in text_lower for k in ("concurrent", "dual-running", "transition window", "transition period"))
        if eff and days is not None and days >= 0:
            direct = (f"Units placed on the market (cleared through customs / made available) before {eff_txt} can normally continue to be sold; anything clearing customs after that date must meet {standard}"
                      + (" - and the notice says legacy registrations are cancelled on that date, so the old certificate stops working overnight." if cancel else "."))
        elif eff or in_force_raw:
            direct = f"The rule is already in force, so there is no further grace period: stock placed on the market before the enforcement date may sell through, but every new shipment must comply with {standard} now."
        else:
            direct = "The notice does not fix an enforcement date yet, so there is no legal cut-over to grandfather against; plan for stock run-out once the date is published."
        if concurrent:
            support.append("The notice describes a concurrent-running period during which both the old and the new standard are accepted.")
        if days is not None and days >= 0:
            support.append(f"That leaves {days} days to sell through or re-certify non-compliant inventory.")
        level = "High" if (strong or cancel or concurrent) else "Medium"
        advice = "Schedule inventory run-out so no non-compliant batch is in transit in the transition month, and keep customs-clearance dates as evidence of when units were placed on the market."
        clauses.append("EU Blue Guide §2.1 - placing on the market" if (codes and set(codes) <= _rs.EU_COUNTRIES) else "Placing-on-the-market principle (customs clearance date)")

    elif intent == "local_rep":
        req = bool((primary or {}).get("local_rep_required"))
        docs = []
        for r in rules.values():
            docs += [d for d in (r.get("required_documents") or []) if re.search(r"representative|agent|importer|kyc", d, re.I)]
        docs = _dedup(docs)
        direct = (f"Yes - {pname} requires a local representative to hold the registration and file changes on the manufacturer's behalf." if req
                  else f"The country record for {pname} does not flag a mandatory local representative, but an importer of record is still needed for customs and any portal filings.")
        if docs:
            support.append("Documents tied to the representative: " + "; ".join(docs[:3]) + ".")
        level = "High" if (req and (docs or strong)) else "Medium"
        advice = "Confirm the representative agreement and the local entity's registration documents are current before filing the change request."

    elif intent == "cost_lead":
        expl = explanation or explain_alert(alert, ctx, "engineer")
        cost = expl.get("cost_effort_estimate", {})
        lt = (primary or {}).get("lead_time_weeks")
        samples = re.search(r"(\d+(?:\s?(?:-|–|to)\s?\d+)?)\s?(?:test )?(?:samples?|units)\b", _alert_text(alert), re.I)
        direct = (f"Plan on roughly {cost.get('effort_range', 'several weeks')}, and an indicative external spend of {cost.get('cost_range', 'to be quoted')} for the impacted products"
                  + (f"; the {pname} country record gives a typical certification lead time of {lt} weeks." if lt else "."))
        if samples:
            support.append(f"The notice mentions {samples.group(0)} for testing.")
        assumes = re.search(r"Assumes .*?market\(s\)\.", cost.get("basis", ""))
        support.append(("Cost basis: " + assumes.group(0) if assumes else "Cost basis: GCM rule table.") + " External spend only - internal engineering time and any redesign are excluded.")
        level = "High" if strong else "Medium"
        advice = "Get written quotations from two accredited labs / certification bodies and book the slot before the gap assessment finishes - lab capacity is the usual bottleneck."

    elif intent == "labels":
        marks = (primary or {}).get("marks") or []
        label_rx = re.compile(r"label|mark(?:ing|s)?\b|logo|packag|print|pictogram|emblem|qr|triman|info-tri|coding|artwork", re.I)
        strong_rx = re.compile(r"logo|pictogram|symbol|signage|emblem|\bmarks?\b|marking|printed|display|coding|\bqr\b|triman|info-tri|label|wheelie|efup|artwork", re.I)
        alert_labels = [e for e in evidence if e["kind"] in ("alert", "curated") and e["source"] != "alert title" and label_rx.search(e["text"])]
        alert_labels.sort(key=lambda e: -len(strong_rx.findall(e["text"])))  # the sentence that says most about the marking itself
        country_labels = [e for e in evidence if e["kind"] == "country" and label_rx.search(e["text"])]
        if alert_labels:
            quote = alert_labels[0]["text"].rstrip(".") + "."
            direct = f"The notice is specific about the markings: {quote}"
            if marks:
                support.append(f"National marks already applicable in {pname}: {', '.join(marks)}.")
            level = "High" if len(alert_labels) >= 2 else "Medium"
        else:
            direct = (f"The alert itself does not prescribe packaging content - it is {'an' if pillar.lower()[0] in 'aeiou' else 'a'} {pillar.lower()} notice. "
                      + (f"The existing marks for {pname} remain: {', '.join(marks)}." if marks else f"No national mark is recorded for {pname}.")
                      + (f" Also on file: {(country_labels[0].get('para') or country_labels[0]['text']).rstrip('.')}." if country_labels else ""))
            level = "Medium" if (marks or country_labels) else "Low"
            evidence = [e for e in evidence if e["kind"] != "rule"]  # rule sentences do not speak to packaging
        evidence = alert_labels + [e for e in evidence if e not in alert_labels]
        advice = "Update the artwork die-lines once, validate proofs against the official graphics charter / portal, then release to print."

    elif intent == "penalty":
        cons = _consequences_in_text(alert)
        if cons:
            direct = "According to the notice itself: " + "; ".join(c.split(" - ")[0] for c in cons[:3]) + "."
            level = "High" if len(cons) >= 2 else "Medium"
        else:
            direct = "The alert material does not state specific penalties; the general consequence for this pillar is loss of market access for non-conforming units. Verify enforcement practice with the certification body or local counsel."
            level = "Low"
        advice = "Record these consequences in the risk register and use them to justify the budget request."

    elif intent == "deadline":
        ms = [d for d in _deadlines(alert) if d.get("date")]
        upcoming = [d for d in ms if d["days_remaining"] is not None and d["days_remaining"] >= 0]
        direct = f"The enforcement date is {eff_txt}" + (f" - {days} days from today." if days is not None and days >= 0 else "." if eff else ", and it applies now.")
        if upcoming:
            support.append("Next milestones: " + "; ".join(f"{d['label']} on {d['date']} ({d['days_remaining']} days)" for d in upcoming[:3]) + ".")
        level = "High" if (eff or ms) else "Medium"
        advice = "Work back from the enforcement date: gap assessment at T-180 days, lab booking at T-150, evidence complete at T-30."

    elif intent == "products":
        expl = explanation or explain_alert(alert, ctx, "engineer")
        prods = expl.get("who_is_affected", {}).get("products", [])
        catnames = [c["name"] for c in expl.get("who_is_affected", {}).get("categories", [])]
        if prods:
            direct = f"{len(prods)} product{'s' if len(prods) != 1 else ''} in the current portfolio: " + "; ".join(f"{p.get('name')} ({p.get('sku')})" for p in prods[:8]) + ("." if len(prods) <= 8 else f"; and {len(prods) - 8} more.")
        else:
            direct = "No product in the current portfolio matches this alert's categories and markets, so the exposure is future launches only."
        support.append(f"Affected categories: {', '.join(catnames[:6])}{'…' if len(catnames) > 6 else ''}.")
        level = "High"
        advice = "Cross-check the list against SKUs launching in the next 12 months - new products inherit the same obligation."

    elif intent == "documents":
        docs = []
        for r in rules.values():
            docs += r.get("required_documents") or []
        docs = _dedup(docs)
        if docs:
            direct = f"For {pname} the requirement engine lists: " + "; ".join(docs[:6]) + ("." if len(docs) <= 6 else f"; plus {len(docs) - 6} more.")
            level = "High"
        else:
            direct = "The alert material does not enumerate documents beyond the checklist; the checklist items below are the closest evidence."
            level = "Medium" if evidence else "Low"
        advice = "Assemble the technical file first (test reports, declarations, representative agreement); portal filings are rejected without it."

    elif intent == "firmware":
        fw = [e for e in evidence if re.search(r"firmware|sbom|secure|vulnerab|sign", e["text"], re.I)]
        if fw:
            direct = f"Yes, the notice addresses this directly: {fw[0]['text']}"
            level = "High" if len(fw) >= 2 else "Medium"
        else:
            direct = "The alert material does not impose firmware or software requirements; this is not a cybersecurity notice."
            level = "Medium"
        advice = "Generate the SBOM from the build pipeline and keep signing-key custody evidence in the technical file."

    elif intent == "chemical":
        ch = [e for e in evidence if re.search(r"substance|pfas|rohs|reach|chemical|material|ppm|phthalate|fluor", e["text"], re.I)]
        if ch:
            direct = f"The notice states: {ch[0]['text']}"
            level = "High" if len(ch) >= 2 else "Medium"
        else:
            direct = "The alert material does not restrict specific substances; verify with the environmental compliance team whether another regulation applies."
            level = "Low"
        advice = "Request supplier material declarations (IPC-1752A) for the components named and screen high-risk materials first."

    else:  # generic - evidence only
        if strong:
            direct = f"The alert material addresses this: {strong[0]['text']}"
            level = "High" if len(strong) >= 2 else "Medium"
        elif evidence and evidence[0]["exact"] >= 1:
            direct = f"The closest statement in the alert material is: {evidence[0]['text']}"
            level = "Medium"
        else:
            level = "Low"
        advice = "If this point is decision-critical, confirm it with the certification body or the official source linked on the alert."

    if level == "Low" and intent not in ("penalty", "labels", "chemical"):
        direct = ("The alert material does not state this; verify with the certification body or the official source linked on the alert."
                  + (f" Nearest related statement: {evidence[0]['text']}" if evidence else ""))

    if intent not in ("products", "cost_lead", "deadline"):  # structured answers above are already complete
        seen_shape = set()
        for e in evidence:  # paraphrased support from the top evidence not already used
            if len(support) >= 3:
                break
            para = e.get("para") or "\x00"
            if e["kind"] == "link" or e["text"] in direct or para in direct or any(e["text"] in s or para in s for s in support):
                continue
            shape = re.sub(r"\b(?:in|for) [A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)?\b", "", e.get("para") or e["text"])  # same fact for another market
            if shape in seen_shape:
                continue
            seen_shape.add(shape)
            lead = {"alert": "The alert states that", "curated": "Curated guidance adds that", "country": "The country record shows that", "rule": "The requirement rule shows that"}.get(e["kind"], "The material notes that")
            t = (e.get("para") or e["text"]).rstrip(".")
            if not e.get("para") and t and t[0].isupper() and not t[:2].isupper():
                t = t[0].lower() + t[1:]
            support.append(f"{lead} {t}.")

    blob = " ".join([direct] + support)
    for m in _STANDARD_RX.finditer(blob):
        clauses.append(m.group(0).strip())
    clauses = _dedup(clauses)[:5]
    basis = {"High": "Direct match between the question and at least two statements in the alert, country record or requirement rule.",
             "Medium": "Answered from structured country / requirement data with partial support in the alert text.",
             "Low": "The alert material does not cover this point."}[level]
    return {
        "expert_answer": " ".join([direct] + support).strip(),
        "direct_answer": direct,
        "evidence": [{"text": e["text"], "source": e["source"]} for e in evidence],
        "cited_clauses": clauses,
        "action_advice": advice,
        "confidence": {"level": level, "basis": basis},
        "intent": intent,
        "generated_by": "rules engine (grounded)",
    }
