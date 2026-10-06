# Regulatory Content Audit — 2026-10-06

Scope: the country knowledge base (205 records), the requirement engine (11 categories × 205
countries) and the 17 built-in regulation alerts. Method: automated consistency checks across all
2,255 combinations, then a fact check of the key markets against regulations as known up to
mid-2026. Items marked **Verify** could not be confirmed and should be checked against the primary
source before being relied on for a shipment decision.

## 1. Corrections applied in this audit

| Area | Before | After | Basis |
|---|---|---|---|
| EU Cyber Resilience Act (ALERT-2026-01) | Full application 2027-01-01; reporting 2026-05-11 | Entry into force 2024-12-10; CAB provisions 2026-06-11; reporting obligations 2026-09-11; **full application 2027-12-11** | Regulation (EU) 2024/2847, Art. 71 |
| EU PPWR (ALERT-ENV-02) | OJ "2024-12-01", enforcement 2026-12-31 | Regulation (EU) 2025/40 published 2025-01-22, in force 2025-02-11, **applies 2026-08-12**; recycled-content targets 2030 | Regulation (EU) 2025/40, Art. 71 |
| US TSCA 8(a)(7) PFAS (ALERT-ENV-01) | Deadline 2026-05-08 | Submission period **2026-04-13 → 2026-10-13**; small-business article importers to 2027-04-13 | EPA 40 CFR 705 as amended (2025 extension rule) |
| "EU RoHS 4" (ALERT-ENV-07) | Presented as a recast with a 2027 cutover | Re-labelled as the **proposed** RoHS review; dates marked indicative | No RoHS recast has been adopted |
| UK PSTI (ALERT-2026-10) | Implied all storage in scope | Scope note added: applies to internet/network-connectable products; plain USB/SD storage is out of scope | PSTI Regulations 2023, Sch. 3 |
| Taiwan EMC | CNS 13438 (CISPR 22 based, withdrawn) | **CNS 15936 (CISPR 32)**; safety CNS 15598-1 only (CNS 14336-1 withdrawn) | BSMI commodity inspection standards |
| Mexico safety | NOM-019-SCFI (cancelled) listed alongside NOM-001 | **NOM-001-SCFI-2018** only | DOF cancellation of NOM-019-SCFI-1998 |
| India | "IS 16333" (a mobile-phone standard) and "IS 13252 / TEC" as EMC | IS 13252 (Part 1):2010 with CRS transition to IS/IEC 62368-1; no mandatory EMC approval for wired storage | BIS CRS scope; TEC MTCTE covers telecom equipment |
| United States local representative | "Not required" | **Required**: FCC SDoC needs a US-based responsible party (47 CFR 2.1077) | FCC SDoC rules (2017 onwards) |
| Speculative dates | Shown as hard deadlines | Marked **Indicative** with "confirm with …": IEC 62368-1 Ed.3 sunset 2026-12-31, FCC annual re-verification 2026-08-01, SASO customs date 2026-10-01, China CCC transition 2026-10-31 | No primary source found |

## 2. Confirmed as correct (sample of key markets)

* EU/EEA: EN IEC 62368-1, EN 55032 / EN 55035, RoHS 2011/65/EU + 2015/863, REACH, WEEE, CE DoC, EU responsible economic operator (Reg. 2019/1020).
* UK: BS EN IEC 62368-1, UKCA, UK RoHS, UK responsible person.
* USA: UL 62368-1 (NRTL for mains units), FCC Part 15B SDoC, DoE Level VI for external power supplies, Prop 65.
* Canada: CSA C22.2 No. 62368-1, ICES-003 Issue 7.
* China: GB 4943.1-2022 (mandatory since 2023-08-01), GB/T 9254.1-2021, China RoHS SJ/T 11364 (EFUP), CCC for power adapters only.
* Japan: PSE (Diamond) for the AC adapter, VCCI-CISPR 32 Class B for the storage unit, J-Moss.
* Korea: KC 62368-1 (safety for adapters), KS C 9832 / 9835 (EMC), KC EMC registration by a Korean entity; passive media exempt.
* Taiwan: CNS 15598-1, CNS 15936, CNS 15663 Section 5 RoHS marking, BSMI RPC/DoC.
* Australia/NZ: AS/NZS 62368.1, AS/NZS CISPR 32, RCM, responsible supplier registration.
* Saudi Arabia / UAE: SASO IEC 62368-1 / SABER (PCoC + SCoC), UAE ECAS; no in-country testing.
* EAEU: TR CU 004/2011, TR CU 020/2011, TR EAEU 037/2016 (EAC).
* Brazil: ABNT NBR IEC 62368-1 / INMETRO for power supplies; ANATEL not applicable to non-RF storage.
* Vietnam QCVN 132:2022 / QCVN 118:2018; Thailand TIS 62368 Part 1-2563; Singapore IEC 62368-1 Safety Mark and SG RoHS (EPMA).
* Product-classification logic: bus-powered devices and passive media exempt from mains safety (SELV / Class III); passive media exempt from KC, BSMI, FCC (47 CFR 15.103(h)) EMC registration; mains-powered external drives trigger in-country safety (BIS, CCC, PSE, NOM, KC, BSMI).
* France AGEC / Triman + Info-tri (stock exhaustion 2023-03-09), Italy D.Lgs 116/2020 (in force 2023-01-01), UK PSTI in force 2024-04-29, India E-Waste Rules 2022 (effective 2023-04-01).

## 3. Items to verify with the primary source

| Item | Why |
|---|---|
| India: Indian Standard number adopting IEC 62368-1 and the MeitY cutover date (alert shows 2028-11-01) | The IS number and the gazette date could not be confirmed; check the latest MeitY CRS order and BIS product manual. |
| Japan J62368-1 edition | Tool shows J62368-1 (H30); a J62368-1 (2023) edition exists — confirm which the Conformity Assessment Body applies. |
| Canada local representative | Shown as required; ISED/CSA do not formally require a Canadian representative for these products — confirm before quoting. |
| Argentina "Resolution 198/2023", Egypt "ES 62368-1" | Reference numbers taken from the original knowledge base; not independently confirmed. |
| IEC 62368-1 Ed.4 national cut-over dates (US/Canada, EU DoW, CB) | Vary by NCB; marked indicative. |
| TSCA 8(a)(7): EPA's 2025 proposal to exempt imported articles | If adopted, the article-importer obligation may fall away; re-check EPA before filing. |
| SASO RoHS phase dates for HS 8523.51 media | Marked indicative. |
| China CCC certificate transition date for GB 4943.1-2022 | Marked indicative. |
| State PFAS packaging laws (Maine, Minnesota, California) | Several were amended in 2024–2025 (exemptions, phased dates); treat the alert as a pointer, not a deadline. |
| Lead times (weeks) and certificate validity periods | Indicative planning figures from the original knowledge base. |

## 4. How to keep it current

* The surveillance scan (US Federal Register – OSHA/FCC/EPA, EUR-Lex, EAEU, GSO, WTO TBT) adds new
  notices as alerts; it does not rewrite country records. Review new alerts and update the country
  knowledge base (`countries_data.json`, `compliance_db.py`) deliberately.
* Re-run this audit before any customer-facing use: `python tools/smoke_test.py` for integrity, then
  spot-check the markets you ship to against the authority's portal.
