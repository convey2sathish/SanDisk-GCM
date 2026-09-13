# Storage & Memory Global Compliance Management (GCM) Platform

An enterprise-grade **Global Compliance Management (GCM)** system built specifically for **Information Technology Equipment (ITE)**, focusing on Flash Memory, Removable Media, Solid State Drives, and Storage Peripherals.

Covering **205 countries and territories** across all 3 key compliance pillars: **Electrical Safety**, **EMC & Radio Frequency**, and **Environmental & Chemical Regulations (RoHS / REACH / EPR)**.

---

## Key Capabilities

### 1. 205 Countries & Jurisdictions Directory (GMA Matrix)
* Full international market access coverage across:
  * **Americas (45+ countries)**: US (FCC/NRTL), Canada (ISED/CSA), Mexico (NOM/NYCE), Brazil (ANATEL/INMETRO), Argentina (ENACOM/IRAM), Chile, Colombia, etc.
  * **Europe & Eurasia (50+ countries)**: EU 27 (CE: LVD, EMCD, RED, RoHS, CRA), UK (UKCA), Switzerland, Norway, EAEU (EAC TR CU 004/020/037: Russia, Belarus, Kazakhstan, Armenia, Kyrgyzstan), Ukraine, Turkey, etc.
  * **Asia-Pacific (42+ countries)**: China (CCC, China RoHS), India (BIS CRS, WPC, TEC), Japan (VCCI, PSE, JATE), South Korea (KC Safety & EMC), Taiwan (BSMI, NCC), Australia/NZ (RCM), Singapore (Safety Mark, IMDA), Malaysia (SIRIM), Vietnam, etc.
  * **Middle East & North Africa (22+ countries)**: Saudi Arabia (SASO SABER, CITC), UAE (MoIAT ECAS, TDRA), Israel (SII), Egypt (NTRA, GOIEC), Qatar, Kuwait, etc.
  * **Sub-Saharan Africa (45+ countries)**: South Africa (SABS, ICASA, NRCS), Nigeria (SONCAP), Kenya (KEBS), Ghana, etc.
* Tailored requirement classification for each country: **Testing Required**, **Document / CB Scheme Acceptance**, or **Supplier's Declaration of Conformity (SDoC) / Exemption**.

### 2. 11 Specialized Storage & Memory Product Classifications
1. **SD Card** (Standard, UHS-I, UHS-II)
2. **MicroSD Card**
3. **SD Express Card** (PCIe Gen3/Gen4 NVMe protocol over SD 7.0/8.0/9.0, thermal & high-frequency RF emission profile)
4. **CF / CFexpress Card** (CompactFlash, CFast, CFexpress Type A/B/C)
5. **Gaming Expansion Card** (Dedicated console NVMe cartridges, e.g., Xbox Velocity / PS5)
6. **USB Flash Drive** (USB 3.2 Gen 1/2, Type-C Dual Drive, encrypted FIPS drives)
7. **Internal SSD** (M.2 NVMe, 2.5-inch SATA)
8. **External SSD (Without Power Adaptor)** (Host bus-powered via USB-C / Thunderbolt)
9. **External SSD (With Power Adaptor)** (Mains-powered desktop units triggering mandatory in-country safety: BIS, CCC, PSE, NOM, UL, and US DoE Level VI energy efficiency)
10. **Enterprise SSD** (U.2, U.3, E1.S, E3.S, SED / TCG Enterprise / FIPS 140-3)
11. **Memory Card Reader** (Multi-slot USB-C peripheral reader docking stations)

### 3. Autonomous Real-Time Regulatory Surveillance Engine
* **Multi-Gateway Crawler**: Continuously monitors global regulatory gazettes, government portals, and standards clearinghouses:
  * **WTO TBT Early Warning System (ePing)**: Technical barriers to trade notices across 164+ WTO member states.
  * **US Federal Register API**: Live FCC (Part 15B/RF), OSHA NRTL (UL 62368-1), EPA/RoHS.
  * **EU EUR-Lex / Official Journal**: CE Directives (LVD, EMCD, RED, RoHS, Cyber Resilience Act, Ecodesign).
  * **India MeitY / BIS Watcher**: IS/IEC 62368-1, Compulsory Registration Scheme (CRS) additions.
  * **East Asia Watchers**: South Korea RRA/KATS notices, Taiwan BSMI announcements.
* **Auto-Ingestion & Ledger**: Automatically parses standards, transition dates, and affected categories, updating the matrix and logging an immutable audit trail (surveillance_log.json).

### 4. Interactive Expandable Regulatory Alerts & Official Source Links
* **Compact View**: Instant high-level alert summary, severity status, jurisdiction, and engineering action.
* **Expandable Intelligence Briefs**: One-click deep-dive accordion providing:
  * **In-Depth Legal Context & Scope**: Full regulatory background and legal mandate.
  * **Specific Testing Clauses & Thresholds**: Specific test parameters (e.g. Clause 9 touch temperatures: 70°C metal / 85°C plastic; high-frequency PCIe radiated emissions up to 6 GHz).
  * **Enforcement Timeline Milestones**: Chronological phases with status badges (Draft, Active, Recommended, Mandatory Cutover).
  * **Direct Official Links**: Instant access to official gazette circulars and regulatory portals (EUR-Lex, BIS, FCC, SASO SABER, BSMI, RRA).
  * **Actionable Engineering Verification Checklist**: 4-step actionable audit and testing procedures.

### 5. 14-Column Excel Compliance Matrix Export
* Generates an audit-ready compliance matrix spreadsheet with product specifications, country requirements, test standards, sample requirements, lead times, certificate validity, and **Column 14: Live Surveillance Source Stamp**.

---

## System Architecture

* **Backend**: Python 3.10+ / Flask / openpyxl
* **Frontend**: HTML5, Tailwind CSS, Lucide Icons, Vanilla JavaScript
* **Database**: In-memory compliance knowledge graph with JSON persistence (compliance_db.py, countries_data.json)
* **Surveillance**: Autonomous asynchronous polling engine (eg_surveillance.py)

---

## Quick Start Guide

### Prerequisites
* Python 3.10 or higher
* pip

### Installation & Run
1. Clone the repository:
   `ash
   git clone https://github.com/convey2sathish/SanDisk-GCM.git
   cd SanDisk-GCM
   `
2. Install dependencies:
   `ash
   pip install -r requirements.txt
   `
3. Run the application:
   `ash
   python app.py
   `
4. Access the platform in your browser at:
   `
   http://localhost:5000
   `

### Standalone Executable (Windows)
To build a portable zero-install single-file executable for corporate laptops without Python:
`ash
pyinstaller GCM_Platform.spec --clean -y
`
The compiled binary will be generated in dist/GCM_Platform.exe.
