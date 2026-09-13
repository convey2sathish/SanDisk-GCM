# Storage & Memory Global Compliance Management (GCM) Platform — Walkthrough

## Feature Overview: Expandable Regulatory Alerts & Official Source Linking

In response to the requirement for detailed technical depth on compliance mandates, the **Regulation Alerts** system has been upgraded from brief short notices to an **interactive, expandable accordion intelligence brief**. Engineers and compliance officers can now immediately expand any alert to view multi-paragraph legal context, specific testing thresholds, transition timeline milestones, direct official government gazette links, and actionable verification checklists.

---

## 1. Interactive Expandable Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               REGULATION ALERT CARD (DEFAULT / COMPACT VIEW)                          │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [CRITICAL] [IS/IEC 62368-1:2023]  India BIS CRS: Mandatory Migration from IS 13252 to IS/IEC 62368-1   │
│ Jurisdiction: India • Effective: 2028-11-01 (Mandatory IS 13252 Sunset)                                 │
│ Summary: BIS Gazette circular mandates IS/IEC 62368-1:2023 for all imported storage drives & adapters. │
│ Required Engineering Action: Test external power adapters to IS/IEC 62368-1:2023 in NABL lab.          │
│ Affected Hardware: [external ssd powered] [external ssd bus] [usb drive]   Source: BIS Gazette Feed    │
│                                                                                                        │
│   [▾ View Detailed Regulatory Brief & Official Sources]  <-- ACCORDION TOGGLE                         │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                          EXPANDED DEEP-DIVE TECHNICAL BRIEF (UPON CLICK)                               │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. 📖 IN-DEPTH REGULATORY CONTEXT & LEGAL SCOPE                                                        │
│    Full multi-paragraph legal brief covering the Bureau of Indian Standards Compulsory Registration   │
│    Scheme (CRS), transition period under MeitY notifications, and co-existence guidelines.             │
│                                                                                                        │
│ 2. ⚡ SPECIFIC TESTING CLAUSES, THRESHOLDS & ENGINEERING IMPACTS                                       │
│    Highlighted technical callout detailing Clause 5.4.1 electric shock energy hazard limits, Clause 6  │
│    fire resistance class requirements, and NABL test report submission procedures.                     │
│                                                                                                        │
│ 3. 🗓️ ENFORCEMENT TIMELINE & TRANSITION MILESTONES                                                    │
│    [Phase 01: BIS Gazette Published (2023-11-15) - Completed]                                         │
│    [Phase 02: NABL Lab Accreditation Active (2024-06-01) - Active]                                     │
│    [Phase 03: Recommended Cutover (2026-11-01) - Recommended]                                          │
│    [Phase 04: Mandatory Sunset of IS 13252 (2028-11-01) - Enforcement Deadline]                        │
│                                                                                                        │
│ 4. 🌐 OFFICIAL GOVERNMENT GAZETTE CIRCULARS & AUTHORITY LINKS (CLICKABLE DIRECT ACCESS)                │
│    • 🔗 [Bureau of Indian Standards (BIS) Official CRS Portal] (https://www.crsbis.in/BIS/)            │
│    • 🔗 [MeitY Compulsory Registration Scheme Gazette Circulars] (https://www.meity.gov.in/...)       │
│    • 🔗 [BIS Product Manual & Scope for IS/IEC 62368-1:2023] (https://www.bis.gov.in/...)             │
│                                                                                                        │
│ 5. ✅ ACTIONABLE COMPLIANCE VERIFICATION CHECKLIST                                                      │
│    ☑ Audit active Indian R-numbers held by Authorized Indian Representative (AIR)                      │
│    ☑ Identify bundled AC/DC power supplies currently certified under legacy IS 13252                   │
│    ☑ Ship physical test samples to NABL-accredited laboratory in India for testing                     │
│    ☑ Submit Form I endorsement on BIS portal prior to the November 1, 2028 sunset deadline             │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Enhancements

### A. Expandable Alert Accordion (`templates/index.html`)
* **Per-Card Expand/Collapse**: Each card features a styled toggle button with animated chevron rotation (`rotate-180`), toggling between `"View Detailed Regulatory Brief & Official Sources"` and `"Hide Detailed Regulatory Brief & Official Sources"`.
* **Global Controls**: Header toolbar includes **"Expand All Briefs"** and **"Collapse All"** buttons for one-click inspection across all active mandates.
* **Deep Linking from Overview**: Clicking any recent alert card on the Dashboard smoothly transitions to the Regulation Alerts tab, opens the expanded brief, and scrolls directly to the card with an attention highlight.

### B. Enriched Authoritative Metadata (`compliance_db.py`)
All 10 pre-seeded global alerts have been upgraded with rich, technical compliance parameters:
1. **EU CRA (Cyber Resilience Act)**: Mandatory SBOM generation, signed cryptographic bootloader verification, vulnerability disclosure SLA, and official links to EUR-Lex Regulation (EU) 2024/2847.
2. **IEC 62368-1:2023 (4th Edition)**: Touch temperature limits under Clause 9 (70°C metal, 85°C plastic) for high-performance external SSDs, CB CTL TRF milestones, and direct link to IEC Webstore.
3. **India BIS CRS Migration**: IS 13252 sunset deadline (November 1, 2028), NABL testing requirements, and direct portal links to MeitY and BIS.
4. **US FCC Part 15B / RF Equipment Authorization**: Supply chain prohibition list (covered list audits), Supplier's Declaration of Conformity (SDoC) test records retention, and direct eCFR links.
5. **Saudi Arabia SASO RoHS & SABER**: 10 hazardous substance limit verification (lead, cadmium, phthalates) on flash assemblies, SABER Qima platform links, and NB testing rules.
6. **South Korea KC EMC (KN 32/35 & KS C 9832)**: RRA radiated emissions up to 6 GHz for high-frequency PCIe storage controllers and direct RRA portal links.
7. **Taiwan BSMI Commodity Inspection**: CNS 15598-1/CNS 15936 safety/EMC verification, Section 5 Ro-HS declaration tables, and direct BSMI gazette links.
8. **EU Ecodesign & Right-to-Repair**: Firmware sanitization standards, repairability scorecards, and EUR-Lex circular links.
9. **China CCC & RoHS Phase II**: Mandatory China RoHS testing, GB 4943.1-2022 safety standards, and CNCA gazette notices.
10. **WPC India Wireless Import Licensing**: Equipment Type Approval (ETA) exemptions for short-range accessories, Saral Sanchar portal links.

### C. Live Autonomous Surveillance Integration (`reg_surveillance.py`)
* When autonomous surveillance detects a new regulatory circular or when a simulated notice is injected, the engine automatically populates:
  - `detailed_summary`: Auto-generated technical brief describing the issuing authority, pillar, and impact.
  - `technical_impact`: Specific standard clause callouts and cutover deadlines.
  - `timeline_milestones`: Ingest date and enforcement deadline phases.
  - `official_links`: Direct link to the official gazette PDF or circular URL.
  - `compliance_checklist`: 4-step engineering verification action plan.

---

## 3. Verification & Live Validation

| Scenario | Test Method | Outcome | Details |
| :--- | :--- | :--- | :--- |
| **Enriched Data Verification** | `scratch/check_all_alerts.py` | **PASSED** | All 10 alerts verified with `detailed_summary`, `technical_impact`, 3+ `official_links`, 3+ `milestones`, and 4 `checklist` items. |
| **Live API Serving** | `scratch/test_api_alerts.py` | **PASSED** | `GET /api/alerts` returned HTTP 200 with complete nested metadata. |
| **Surveillance Ingestion & Enrichment** | `scratch/test_simulate_alert.py` | **PASSED** | Ingested `IS 15936 / CISPR 32:2026` notice for India EMC, auto-generating all 5 enriched sections. |
| **UI Accordion Toggle** | Browser inspection | **PASSED** | Smooth expand/collapse animation, chevron rotation, and clickable external links opening in new tabs (`target="_blank"`). |
| **Overview Deep-Link** | `goToAlert(id)` | **PASSED** | Seamlessly switches tabs, auto-expands the brief, and highlights the target alert card. |
