# GCM Platform — Full Review & Remediation Report (v1.0 → v2.0)

Scope: the shipped executable `GCM_Platform (4).exe` (PyInstaller, Python 3.11) and the source in
https://github.com/convey2sathish/SanDisk-GCM (commit a23ea2a). The executable was unpacked and
its bytecode disassembled to confirm it matched the repository; the repository was then used as the
source of truth. Every finding below was verified by reading the code or reproducing it.

## 1. Visible defects (what a user would notice)

| # | Area | Finding | Fix in v2.0 |
|---|---|---|---|
| V1 | Overview | `loadOverview()` wrote to a non-existent element (`stat-alerts-hdr`), throwing before rendering. The **regional distribution and “latest bulletins” panels were always empty**. | Rewritten Overview with null-safe rendering; new KPI, risk, horizon and action widgets. |
| V2 | Document Impact Audit | The tab's six buttons called JavaScript functions that were **never defined** (`runDocumentAudit`, `browseLocalFolder`, `generateSampleDocs`, `handleBrowserFolderUpload`, `filterDocAudit`, `initDocAuditTab`). Every click raised `ReferenceError`; the feature was decorative. | Complete Document Audit v2 module (backend + UI). |
| V3 | Map dossier | “Simulate Notice” called undefined `setSimTargetScope` and element `sim-country-select`; the country was never pre-selected. | Simulator is driven through the event bus with the country pre-filled. |
| V4 | Whole UI | Styling and icons were loaded from **cdn.tailwindcss.com and unpkg.com**. On an office laptop without internet (or with CDN blocking) the executable rendered as unstyled text without icons. | Tailwind compiled to a local stylesheet; Lucide icons vendored. Zero external requests. |
| V5 | Matrix, Map, Excel | The shipped `countries_data.json` had **all 205 countries' Safety, EMC and Environmental standards overwritten** with the literal string “IEC 62368-1 / CISPR 32 / RoHS 4 Harmonized” (a past “simulate all 205” run wrote into the seed file and the corrupted file was committed and bundled). Every export and fact sheet showed the same fake standard. | Seed regenerated from the original per-country source data (161 countries) with region-based inference for 44 micro-states; simulation artefacts removed. Simulations now write to a user data folder, never to the seed. |
| V6 | Surveillance ledger | Shipped with 28 simulation artefacts (“SURV-SIM…”, “All 205 Global Jurisdictions”) presented as real surveillance history. | Clean, hash-chained seed ledger with three baseline events; simulated events are labelled `simulated`. |
| V7 | Alerts | Badge counts were hard-coded (“10”) while 17 alerts existed; several header numbers were static text. | All counts computed from the API. |
| V8 | Matrix | The “Environmental / PFAS focus” filter did nothing (matched everything). | Replaced by working filters (local-rep mandatory, pending transition) and full-text search across all pillars. |
| V9 | Excel export | Timestamp labelled “UTC” but was local time; searched fewer fields than the UI; no PFAS/packaging/EPR columns. | Fixed label, filter parity, four new columns incl. pending standard transitions. |
| V10 | Publish alert | New alerts were given a **Google search URL as their “official gazette portal”** (fabricated source) and an id pattern that collided with seeded ids. | Sources only from user input or surveillance; unique ids; input validation. |
| V11 | Fact sheet vs matrix | Country fact-sheet rules were computed by a simplified branch in `app.py` that disagreed with the matrix engine (e.g. SD Express “High-Speed EMC & Thermal Review” vs “Document Required”). | Fact sheet now uses the same requirement engine as the matrix. |
| V12 | Ledger dialog | Literal `\n` text rendered inside the table header. | Rebuilt. |

## 2. Hidden defects (correctness, data integrity, security)

| # | Area | Finding | Fix in v2.0 |
|---|---|---|---|
| H1 | Persistence | `surveillance_log.json` and `countries_data.json` were written next to the code. In a one-file PyInstaller build that folder is a **temporary directory deleted on exit**, so every ingested notice was lost; in development it silently mutated the seed data (root cause of V5/V6). | `config.py` separates the read-only bundle from a writable data folder (`%LOCALAPPDATA%\GCM_Platform\data`), seeded on first run. |
| H2 | Security | `app.run(host="0.0.0.0", debug=True)` in development exposed the Werkzeug debugger (remote code execution) to the network; the exe also listened on all interfaces with no authentication. | Binds to `127.0.0.1` by default, debugger off, security headers added. |
| H3 | XSS | Country names, notes, standards and alert titles were injected into `innerHTML` unescaped in many places. A surveillance-ingested gazette title containing HTML would execute in the browser. | Every dynamic string passes through `GCM.ui.esc()`. |
| H4 | Concurrency | Module-level lists rebound with `global` from request handlers under a threaded server; JSON written non-atomically (a crash mid-write corrupts the file). | Thread-safe `Store` with `RLock`; atomic write-and-replace. |
| H5 | Surveillance ids | Event ids used Python's `hash(title)` which is randomised per process, so **every re-scan created duplicate events**. | Content-hash ids (SHA-1) — idempotent scans. |
| H6 | Regulatory semantics | A detected/simulated notice **overwrote the country's current standard** with free text. Regulations have transition periods; the current standard remains valid until the deadline. | Notices are recorded as *transitions* (from → to, deadline, source); current standards are preserved and the matrix/map/Excel show the pending change. |
| H7 | Ledger integrity | The “immutable ledger” was a plain JSON list anyone could edit. | SHA-256 hash chain per entry; integrity verified on every read and shown in the UI. |
| H8 | Pillar detection | Any ambiguous text defaulted to “Safety”; no Cyber pillar although three seeded alerts are cyber-security laws. | Scored classifier with Safety / EMC / Environmental / Cyber / All. |
| H9 | Product impact | Region matching compared raw strings (“ASIA-PACIFIC” never equalled “ASIA”), so regional alerts missed APAC products; the logic was duplicated in two places and had diverged. | Single `resolve_product_impacts` with region market tables; used everywhere. |
| H10 | Readiness API | `country.get("marks", ["local mark"])[0]` raised `IndexError` for countries with an empty marks list. | Guarded; logic moved to the risk engine. |
| H11 | Document audit rules | Rule 4 flagged **every** RoHS/technical document that did not contain the word “PFAS” as a *Critical* TSCA impact — mass false positives. Rule 2 treated any “62368-1” without a year as an obsolete edition. Trigger alert ids were hard-coded and one mapped to the wrong alert title. | Edition-aware detection, dynamic rulebook driven by live alerts, documented health-score formula. |
| H12 | Dependencies | `requirements.txt` omitted `pypdf` and `python-docx` although the audit engine depended on them; a clean `pip install -r requirements.txt` produced silently empty PDF/DOCX extraction. | Requirements completed. |
| H13 | Dead / brittle code | `ai_expert.py` (Bing scraping) was never imported; `expert_advisor.py` scraped DuckDuckGo with brittle regexes and printed errors; `datetime.utcnow()` is deprecated. | Dead code archived; advisor hardened; optional Claude integration with deterministic fallback. |
| H14 | Validation | No POST body validation anywhere; unknown category ids raised `KeyError` → HTTP 500 with an HTML stack trace. | Every route validates input and returns JSON errors with correct status codes. |
| H15 | Dev server | `debug=not frozen` enabled the auto-reloader, which starts the process twice (duplicate browser-open timers, duplicate engines). | Reloader disabled; explicit `GCM_NO_BROWSER` / `GCM_PORT` / `GCM_DATA_DIR` controls. |
| H16 | Excel audit export | If nothing had been scanned, export silently scanned a hard-coded `C:\SanDisk\Compliance_Docs`. | Returns a clear 404 JSON error until a scan exists. |
| H17 | Docs | README referred to a non-existent `eg_surveillance.py` and “10 alerts”. | Rewritten documentation. |

## 3. Product gaps versus C2P, UL GCM and OnRule (closed in v2.0)

* No plain-language explanation of alerts → **Explainer engine** (simple / executive / engineer) with who-is-affected, what-to-do-by-when, cost/effort, risk-if-ignored, jargon glossary, confidence and sources; optional Claude enhancement.
* No triage workflow → alert statuses (New / Acknowledged / In Progress / Closed) with owner and notes.
* No task management → **Action items** linked to alerts, documents, products and countries.
* No timeline → **Regulatory Horizon**: every deadline, milestone, certificate expiry and action on one timeline with buckets.
* No quantified risk → **Compliance Risk Index** (0–100, graded) per product, region and pillar with an explainable formula.
* No portfolio view → Product Portfolio with readiness per market, certificates health and an ECO change-impact analyser (the backend for this existed but had no UI).
* No document intelligence → Document Audit v2 with health score, gap analysis per product×market, remediation plan and multi-sheet Excel directive; browser folder upload.
* No global search → command palette (Ctrl+K) across countries, standards, alerts, products and actions.
* No evidence of integrity → hash-chained ledger with verification.
* Not usable offline → fully offline; single executable; user data preserved across upgrades.

## 4. Method

1. Extracted the PyInstaller archive (custom stdlib-only extractor) and disassembled the Python 3.11
   bytecode of `app`, `compliance_db`, `reg_surveillance`, `doc_audit_engine`, `excel_export` to
   confirm the executable's behaviour; recovered all data tables.
2. Cloned the GitHub repository and diffed it against the executable (the repo added the expert
   advisor; everything else was identical).
3. Static cross-checks: every `onclick` handler vs. defined functions, every `getElementById` vs.
   existing ids, every API path used by the UI vs. registered routes.
4. Data audit of `countries_data.json` against `populate_countries.py`.
5. Re-architecture and rebuild (see `docs/ARCHITECTURE_CONTRACT.md`, `CHANGELOG.md`).
