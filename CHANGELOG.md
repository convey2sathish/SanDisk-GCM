# Changelog

## 2.0.0 "Horizon" — 2026-09-22

A ground-up rebuild on the same knowledge base. See `docs/REVIEW_REPORT.md` for every defect that
was found in 1.0 and how it was fixed.

### Fixed
* Overview panels never rendered (JS crash on a missing element).
* Document Impact Audit tab was non-functional (handlers never defined).
* Map “Simulate notice” did not pre-select the country.
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

### Changed
* Modular architecture: `config.py`, `store.py`, `routes_*.py`, JS modules under `static/js/app/`, Jinja partials.
* All mutable data lives in `%LOCALAPPDATA%\GCM_Platform\data` (or `GCM_DATA_DIR`); shipped data is read-only.
* Server binds to localhost by default (`GCM_HOST`, `GCM_PORT` to override).

## 1.0.0
* Initial release (single-file Flask app, 205 countries, 11 categories, alerts, map, Excel export, surveillance simulation).
