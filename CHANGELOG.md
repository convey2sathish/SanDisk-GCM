# Changelog

## Unreleased — Traceable, human-controlled regulatory content

### Added
* **Review tab** (Alt+8): a human approval queue. Nothing changes the knowledge base or creates an alert until a person approves it. KPI strip, pending cards, history, hash-chained audit trail with integrity badge.
* **Source & verification column** in the matrix (and Excel: final column "Verification & sources") and per-pillar verification in every country fact sheet. Status is Verified / Needs re-verification / Partly verified / Unverified.
* **Authority portals** (`kb_sources.json`, shipped): official home pages of the competent authorities for the key markets (US, CA, MX, BR, AR, CL, CO, GB, EU via one shared entry, CH, NO, TR, EAEU, UA, IN, CN, JP, KR, TW, AU/NZ, SG, MY, TH, VN, ID, SA, AE, IL, EG, ZA, NG, KE). They are starting points, not citations of a specific rule; countries without an entry show "No source recorded".
* **Verification** by a human reviewer with a mandatory citation URL; expires after 12 months. **Proposals** to change a country field (reason + source URL required) become *edited & approved* overrides (`kb_overrides.json`) on top of the read-only seed when approved, and can be reverted.
* Settings: **reviewer name** (self-declared, no logins in this tool) and optional **second-reviewer rule**.
* API: `/api/review/queue|stats|audit|proposals`, `/api/review/queue/<id>/approve|reject`, `/api/verification/<code>`, `/api/overrides/<code>/<field>`; `verification` block on `/api/gma/by-product` rows and `/api/countries/<code>`.

### Changed
* Surveillance scans now **queue** detected notices for review (`queued_for_review`) instead of writing ledger entries and alerts directly; approval applies them. Rejected notices are never re-queued.
* New data files in the data folder: `kb_overrides.json`, `kb_verification.json`, `review_queue.json`, `audit_trail.json`.

## 2.0.0 "Horizon" — 2026-09-22

A ground-up rebuild on the same knowledge base. See `docs/REVIEW_REPORT.md` for every defect that
was found in 1.0 and how it was fixed.

### Fixed
* Overview panels never rendered (JS crash on a missing element).
* Document Impact Audit tab was non-functional (handlers never defined).
* Executable depended on internet CDNs for styling and icons; now fully offline.
* Shipped country data had every standard overwritten by a simulation; regenerated from source.
* Ledger contained simulation artefacts; replaced by a clean, hash-chained seed.
* Persistent data was written into the PyInstaller temp folder and lost on exit.
* Debug server exposed on all interfaces; XSS in dynamic rendering; non-atomic writes; race conditions.
* Non-deterministic surveillance ids created duplicate events on every scan.
* Notices overwrote current standards instead of recording a transition.
* Excel export label/filters/columns; fact-sheet vs. matrix inconsistency; missing requirements.

### Added
* **Alert Explainer** — every alert explained in plain English for three audiences with who/what/when/cost/risk/glossary/confidence, plus grounded Q&A. Optional Claude enhancement (Settings → API key).
* **Alert triage** (New → Acknowledged → In Progress → Closed) with owner and notes.
* **Action items** linked to alerts, documents, products and countries; tracked on the Overview.
* **Regulatory Horizon** timeline (deadlines, milestones, certificate expiries, actions, ledger history).
* **Compliance Risk Index** per product, region and pillar with an explainable formula.
* **Product Portfolio** with readiness per market, certificate health and ECO change-impact analyser.
* **Document Audit v2** — health score, dynamic rulebook, gap analysis per product × market, remediation plan, browser folder upload, multi-sheet Excel directive, plain-English explanation per document.
* **Command palette** (Ctrl+K) global search; keyboard shortcuts; first-run guide.
* **Tamper-evident ledger** with integrity verification and a “reset knowledge base to seed” maintenance action.
* **Standard transitions** shown in the matrix, map, fact sheets and Excel.
* Settings (company name, AI model/key, auto-scan interval) stored in the local data folder.
* Cyber pillar; pending-transition heat layer on the map; new matrix filters.

### Removed
* Gazette-notice simulator and all seeded/simulated surveillance data (the ledger now starts empty and is filled only by live scanning).

### Changed
* Built-in example products, certificates and audit documents are now clearly labelled generic placeholders (`is_example`); no real product models, brands or certificate numbers are shipped.
* Modular architecture: `config.py`, `store.py`, `routes_*.py`, JS modules under `static/js/app/`, Jinja partials.
* All mutable data lives in `%LOCALAPPDATA%\GCM_Platform\data` (or `GCM_DATA_DIR`); shipped data is read-only.
* Server binds to localhost by default (`GCM_HOST`, `GCM_PORT` to override).

## 1.0.0
* Initial release (single-file Flask app, 205 countries, 11 categories, alerts, map, Excel export, surveillance simulation).
