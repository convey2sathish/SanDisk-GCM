# GCM Platform 2.0 — User Guide

*A five-minute tour for compliance engineers, product managers and directors.*

## Start
Double-click `GCM_Platform.exe` (or run `run.bat` from source). Your browser opens at
`http://localhost:5000`. Nothing leaves your laptop; the platform works without internet.
Press `?` at any time for shortcuts, `Ctrl+K` to search anything.

## 1. Overview — the compliance command centre
* **KPI tiles**: jurisdictions covered, active alerts (critical / warning), the **Compliance Risk Index**
  (0 = no exposure, 100 = maximum; graded A–F), what is due in the next 90 days, portfolio size and
  open action items.
* **Needs attention now**: the next deadlines, certificate expiries and overdue actions, each one
  clickable.
* **Alert pressure by pillar** and **regional coverage** show where the regulatory load sits.
* **Action items**: the team's to-do list. Create one from anywhere (alert, document, product, country)
  with the “+ Action” buttons or `Action` in the header.

## 2. Testing vs. Document Matrix
1. Choose a **product classification** (e.g. *External SSD with power adaptor*).
2. Read the counters: how many of the 205 markets need **in-country testing**, a **document / CB
   Scheme filing**, or only a **supplier declaration**; how many have a **pending standard transition**.
3. Filter by requirement, region, or search any country, authority, standard, document or mark
   (e.g. `PFAS`, `Triman`, `UKCA`, `62368`).
4. Every row shows the authority, the route, the standards for Safety, EMC, RoHS, PFAS, packaging and
   EPR, the mandatory document checklist, the local-representative rule and lead time.
5. **Fact sheet** opens the full country dossier (all categories, alerts, products, transitions).
   **Export view / All 205** downloads a formatted Excel workbook.

## 3. Global Access Map
Pick a **target product** and a **heat layer**: readiness, testing barrier, lead time, environmental
regimes, active alerts or pending transitions. Hover for a summary, click for the dossier on the right.
Use *Focus* to jump to a region, or type a country in *Quick search*.

## 4. Regulation Alerts — and the Explainer
Each card shows severity, pillar, jurisdiction, standard, a **countdown to the deadline**, and how many
of your products are affected. Set the **triage status** (New → Acknowledged → In Progress → Closed).

Click **Explain in plain English**. Choose the audience:
* **Simple** – short sentences, every acronym expanded, one analogy.
* **Executive** – what / so what / now what, money, dates, owner.
* **Engineer** – clause-level detail, editions, test requirements.

The brief always contains: headline, what changed, why it matters, who is affected (categories,
SKUs, markets), what to do (numbered steps with owner role, due-by and effort), key dates, cost &
effort estimate, risk if ignored, jargon explained, confidence and sources. Turn any step into an
**action item**, and ask follow-up questions in the **Q&A console**. If an Anthropic API key is
configured in Settings, Claude refines the brief; otherwise the built-in engine answers offline. The
brief states which engine produced it.

**Publish alert** lets you add a notice by hand; missing fields are enriched automatically.

## 5. Horizon & Risk
* **Compliance Risk Index** gauge with a “how is this calculated?” explanation.
* **Regulatory Horizon**: every deadline, milestone, certificate expiry, action due date and
  surveillance event on one timeline (90 / 180 / 365 days / all), filterable by type, pillar and
  product; export to CSV.
* **Risk breakdown** per product (with the drivers), per region and per pillar; **top risks** with a
  one-click action.

## 6. Product Portfolio
Product cards with SKU, risk grade, readiness bar and target markets; open a product for readiness per
market, linked alerts, certificates (with expiry countdown) and the **engineering-change (ECO) impact
analyser** — pick the component you are changing (power adapter, controller, NAND, enclosure, firmware
crypto, PCB…) and see which markets need re-testing, an amendment or nothing. Add products and
certificates with the buttons at the top.

## 7. Document Impact Audit
1. Enter a folder path (or **Browse…**), or drag a folder into the browser, or click **Load sample
   documents** to try it.
2. Click **Scan & audit**. The engine reads PDF / DOCX / XLSX / CSV / TXT, detects standards and their
   editions, labs, report numbers, SKUs, markets and expiry dates.
3. Read the **health score** (A–F) and the tier counters: full lab re-testing, DoC re-signing,
   packaging artwork update, portal filing, compliant, unreadable.
4. Each document shows *why* it is impacted (rationale), the obsolete vs. required standard, the
   deadline, estimated effort and cost, and the alert that triggers it. **Explain** gives a plain-English
   paragraph; **Create action** schedules the fix.
5. **Gap analysis** lists, per product and market, the documents you should have but do not.
6. **Remediation plan** groups the work by tier with a cost roll-up; **Export directive (Excel)**
   produces a four-sheet workbook for the lab and the DoC signatories.

## 8. Regulatory Surveillance
The bar under the header shows the engine status. **Scan feeds now** queries the monitored gateways
(WTO TBT, US Federal Register – OSHA NRTL / FCC / EPA, EUR-Lex, EAEU, GSO, …); relevant notices are
scored, recorded in the **ledger** and turned into alerts with product impact. The ledger starts empty
and is hash-chained; the dialog shows whether its integrity verifies. Settings → *Reset knowledge base*
removes detected transitions from the country records.

## Settings
Company name, Anthropic API key and model (optional), auto-scan interval. The data folder path is shown;
copying that folder is a full backup.

## Keyboard shortcuts
`Ctrl+K` search · `Alt+1…7` tabs · `Esc` close · `?` help
