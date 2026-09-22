# Storage & Memory GCM Platform 2.0 “Horizon”

**Global Compliance Management for flash memory, SSDs and storage peripherals — 205 jurisdictions,
11 product categories, four regulatory pillars (Safety · EMC · Environmental · Cyber), fully offline,
one executable.**

> Built for compliance engineers, test-lab coordinators, packaging teams and directors who need one
> answer to three questions for every market: *What applies? What changed? What do we do, by when?*

---

## What it does

| Area | What you get |
|---|---|
| **Compliance Command Centre** (Overview) | Live KPIs, Compliance Risk Index, everything due in the next 90 days, alert pressure by pillar, regional coverage, action items. |
| **Testing vs. Document Matrix** | For any product category, every jurisdiction's route: in-country lab testing, document / CB Scheme filing, or supplier declaration — with the exact document checklist, standards for all pillars, local-representative rule, lead time and pending standard transitions. One-click Excel export (18 columns). |
| **Global Access Map** | Heat layers for readiness, testing barriers, lead time, environmental regimes, active alerts and pending transitions. Click any of 205 territories (incl. 39 island markers) for its dossier. |
| **Regulation Alerts + Explainer** | Every alert explained in plain English for three audiences (simple / executive / engineer): what changed, why it matters, who is affected (categories, SKUs, markets), what to do by when, cost & effort, risk if ignored, jargon glossary, confidence and sources — plus a grounded Q&A console. Triage workflow and one-click action items. Optional Claude enhancement. |
| **Regulatory Horizon & Risk** | One timeline of deadlines, milestones, certificate expiries, actions and surveillance history; Compliance Risk Index per product, region and pillar with an explainable formula; top risks. |
| **Product Portfolio** | Products with readiness per market, certificates health (expiry countdown), linked alerts, and an engineering-change (ECO) impact analyser. |
| **Document Impact Audit** | Point at a folder (or drag one into the browser). The engine reads PDFs, DOCX, XLSX, CSV/TXT, identifies standards & editions, labs, SKUs, markets and expiry dates, and produces a health score, a re-test / re-sign / packaging / portal directive per document, a gap analysis per product × market, a remediation plan with cost roll-up and a four-sheet Excel directive. |
| **Regulatory Surveillance** | Scans WTO TBT, US Federal Register (OSHA NRTL, FCC, EPA), EUR-Lex, EAEU, GSO and national gazettes for storage-relevant notices; records them as standard *transitions* in a tamper-evident, hash-chained ledger; creates fully enriched alerts with product impact. |
| **Everywhere** | Ctrl+K search across countries, standards, alerts, SKUs and actions; keyboard shortcuts; deep links; first-run guide; all data persisted locally and preserved across upgrades. |

## Quick start

### Standalone (no Python needed)
Run `GCM_Platform.exe`. A console window shows the local address (default `http://localhost:5000`) and
the browser opens automatically. Your data lives in `%LOCALAPPDATA%\GCM_Platform\data`.

### From source
```bash
git clone https://github.com/convey2sathish/SanDisk-GCM.git
cd SanDisk-GCM
pip install -r requirements.txt
python app.py            # or run.bat on Windows
```
Environment variables: `GCM_PORT` (default 5000), `GCM_HOST` (default 127.0.0.1), `GCM_DATA_DIR`
(default `./data` in source mode), `GCM_NO_BROWSER=1` (don't auto-open a browser),
`ANTHROPIC_API_KEY` (enables Claude-enhanced explanations; can also be set in Settings).

### Build the executable
```bash
build_exe.bat            # = pip install -r requirements.txt, build_assets.bat, pyinstaller GCM_Platform.spec
```
Output: `dist\GCM_Platform.exe`.

### Rebuild the stylesheet (after editing templates or JS)
```bash
build_assets.bat         # Tailwind v4 CLI -> static/css/app.css (needs Node.js once, to install the CLI)
```

## Architecture

```
app.py                 Flask composition root: registers routes_core / routes_alerts / routes_docaudit / routes_risk
config.py              bundle vs. data directory, settings, atomic JSON IO
store.py               thread-safe persisted state (user alerts, triage, products, certificates, actions, last audit) + ledger hashing
compliance_db.py       seed knowledge base: 11 categories, 205 countries, 17 alerts, portfolio, requirement engine
reg_surveillance.py    surveillance engine (scan / transitions / hash-chained ledger)
surveillance_data.py   monitored gateways, relevance keywords, demo scenarios
alert_explainer.py     deterministic plain-English explanation engine
ai_bridge.py           optional Claude enhancement (anthropic SDK, claude-opus-5, server-side fallbacks)
expert_advisor.py      web-search-backed expert brief and Q&A
doc_audit_engine.py    document ingestion, metadata, dynamic rulebook, gap analysis, Excel directive
risk_engine.py         Compliance Risk Index, horizon, certificate health, portfolio readiness
excel_export.py        compliance matrix workbook
templates/             index.html shell + partials/ per tab and shared modals
static/js/app/         core.js runtime + one module per tab
static/css/            tailwind.src.css -> app.css (generated), custom.css (design system)
docs/                  ARCHITECTURE_CONTRACT.md, REVIEW_REPORT.md
```

Design rules: no external network calls except optional surveillance scans and the optional Claude
API; never write into the bundle directory; every dynamic string is HTML-escaped; every API error is
JSON with a correct status code. See `docs/ARCHITECTURE_CONTRACT.md`.

## Data & privacy

* The shipped knowledge base (`countries_data.json`, alerts, portfolio) is read-only. Everything you
  change is stored in the local data folder and merged on read, so upgrading the executable never
  loses your work. Settings → “data folder” shows the location.
* The surveillance ledger is hash-chained (SHA-256). Integrity is verified on every read and shown in
  the ledger dialog. “Reset knowledge base” restores the shipped country data without touching the ledger.
* An Anthropic API key, if provided, is stored only in that local folder and used only for the calls
  you trigger (explain / ask). Without a key, the built-in explainer does everything offline.

## Versioning

See `CHANGELOG.md`. The 1.0 defects and how they were fixed are documented in `docs/REVIEW_REPORT.md`.

## License / trademarks

Internal tool. SanDisk, WD_BLACK, G-DRIVE and Ultrastar are trademarks of their respective owners;
standards names (IEC, CISPR, EN, UL, GB, CNS, KS, IS) belong to their issuing bodies.
