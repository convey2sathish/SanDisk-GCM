# Autonomous Real-Time Regulatory Surveillance Engine

## Architecture & Global Coverage

The **Regulatory Surveillance Engine** (eg_surveillance.py) provides 24/7 automated intelligence gathering across all **205 recognized jurisdictions** and across all three compliance pillars:

`
                  ┌──────────────────────────────────────────────┐
                  │ 205 Global Jurisdictions Real-Time Listening │
                  └──────────────────────┬───────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
  [Safety Pillar]                  [EMC & RF Pillar]           [Environmental Pillar]
  IEC 62368-1 (Ed 3 & 4),         CISPR 32 / 35, KN 32/35,     RoHS 10 substances, REACH
  UL 62368-1, IS/IEC 62368,       FCC Part 15B, VCCI-CISPR 32, SVHC, PFAS restrictions,
  GB 4943.1, CNS 15598-1          CNS 15936, KS C 9832         EPR packaging mandates
`

---

## 1. Multi-Gateway Harvesting Network

The engine operates 12 primary and regional crawling gateways:

1. **WTO TBT Early Warning System (ePing Feed)**:
   * Covers standard changes, technical barriers, and national technical regulations for **164+ WTO member nations**.
2. **US Federal Register API**:
   * Continuous surveillance of FCC (Title 47 CFR Part 15B/RF), OSHA NRTL recognitions (UL 62368-1), and EPA TSCA/RoHS rulemakings.
3. **EU EUR-Lex / Official Journal of the European Union (OJEU)**:
   * Direct parsing of CE marking directives: Low Voltage Directive (LVD 2014/35/EU), EMC Directive (2014/30/EU), Radio Equipment Directive (RED 2014/53/EU), RoHS (2011/65/EU), Cyber Resilience Act (Regulation (EU) 2024/2847), and Ecodesign for Enterprise / Client NVMe SSDs.
4. **India MeitY / BIS Gazette Circulars**:
   * Live tracking of MeitY notifications, Compulsory Registration Scheme (CRS) Phase orders, and Bureau of Indian Standards (BIS) product manuals.
5. **East Asia Regional Authorities**:
   * **South Korea**: National Radio Research Agency (RRA) notices for KC EMC & KATS notices for KC Safety.
   * **Taiwan**: Bureau of Standards, Metrology and Inspection (BSMI) commodity inspection gazettes.
   * **Japan**: METI PSE & VCCI Council announcements.
   * **China**: State Administration for Market Regulation (SAMR) & CNCA announcements for CCC and China RoHS.
6. **Americas & MENA Regional Watchers**:
   * **Saudi Arabia SASO / SABER Qima**: SASO RoHS, IECEE recognition circulars.
   * **Brazil ANATEL / INMETRO**: Telecommunication act updates and mandatory safety certifications.

---

## 2. Real-Time Entity Extraction & Classification

When a gazette circular or standard revision is published:
1. **Pillar Detection**: Text is parsed to determine whether the change impacts **Safety**, **EMC**, or **Environmental** compliance.
2. **Standard & Scope Matching**: Matches affected storage hardware (External SSDs, MicroSD, SD Express, Enterprise NVMe, CFexpress, Card Readers).
3. **Transition Milestone Extraction**: Identifies the publication date, voluntary transition window, and mandatory sunset/withdrawal date.
4. **Official Source Link Generation**: Captures direct links to official government gazette circulars, standard specification portals, or authority websites.
5. **Actionable Checklist Construction**: Generates a 4-step engineering verification action plan.

---

## 3. Database Upsert & Audit Trail

* Updates countries_data.json and in-memory compliance_db.COUNTRIES_DB.
* Records each transaction in the immutable audit ledger surveillance_log.json.
* Appends **Column 14: Live Surveillance Source** in all exported Excel matrices.
