# GCM Platform 2.0 — Architecture & Integration Contract

This document is the single source of truth for how backend modules, API routes and
frontend modules fit together. Every contributor (human or agent) must follow it so the
pieces integrate without conflicts.

## 1. Ground rules

* **Offline first.** No CDN, no external `<script src="https://…">`. All assets are served
  from `/static`. Tailwind is compiled to `static/css/app.css` (see §7). Icons are the
  vendored Lucide build at `static/js/vendor/lucide.min.js`.
* **Never write into the bundle directory.** Use `config.data_path(...)` for anything
  mutable; `config.bundle_path(...)` for shipped read-only assets.
* **All user-visible data goes through `store.get_store()`** (alerts, products,
  certificates, actions, alert triage state, last audit report, countries working copy).
  `compliance_db` tables are seed/read-only knowledge.
* **Every JSON API returns a JSON object** (never a bare list) except the legacy
  `/api/alerts`, `/api/countries`, `/api/categories`, `/api/products`, `/api/certificates`
  which keep returning lists for compatibility.
* **Errors:** `{"error": "<message>"}` with a proper HTTP status (400/404/500). Never let an
  exception 500 without JSON.
* **Escape everything** rendered into HTML from data: use `GCM.ui.esc()`.
* **No inline `onclick` in *new* code**; use `data-action="..."` + delegated listeners, or
  attach listeners in the module. (Existing ported code may keep `onclick` short term.)
* Python: standard library + Flask + openpyxl + python-docx + pypdf. `anthropic` is optional
  (import inside try/except).
* Dates are ISO `YYYY-MM-DD`; timestamps ISO-8601 UTC with `Z`.

## 2. Backend module map

| Module | Owner area | Responsibility |
|---|---|---|
| `config.py` | core | paths, settings, atomic JSON IO |
| `store.py` | core | persisted mutable state + hash-chained ledger helpers |
| `compliance_db.py` | core | seed knowledge (categories, countries, alerts, products, certs) + requirement engine |
| `reg_surveillance.py` | core | surveillance engine (scan, ledger) |
| `excel_export.py` | core | compliance-matrix workbook |
| `routes_core.py` | core | overview, categories, matrix, countries, surveillance, settings, actions, products, certificates |
| `alert_explainer.py` | alerts | deterministic "explain this alert in simple terms" engine |
| `ai_bridge.py` | alerts | optional Claude enhancement (model `claude-opus-5`) |
| `expert_advisor.py` | alerts | web search + Q&A (existing, fixed) |
| `routes_alerts.py` | alerts | `/api/alerts/*` (list/create/triage/explain/ask) |
| `doc_audit_engine.py` | docaudit | document ingestion, metadata, impact, gap analysis, Excel |
| `routes_docaudit.py` | docaudit | `/api/documents/*` |
| `risk_engine.py` | risk | Compliance Risk Index, regulatory horizon, certificate health, portfolio readiness |
| `routes_risk.py` | risk | `/api/risk/*`, `/api/horizon`, `/api/portfolio` |
| `kb_review.py` | review | overrides, verification, review queue, hash-chained audit trail (all persisted in DATA_DIR; reads shipped `kb_sources.json`) |
| `routes_review.py` | review | `/api/review/*`, `/api/verification/*`, `/api/overrides/*` |
| `app.py` | core | Flask app creation; imports each `routes_*.py` and calls `register(app, ctx)` |

Each `routes_*.py` exposes exactly:

```python
def register(app, ctx):
    """ctx = {"store": Store, "surveillance": RegulatorySurveillanceEngine, "db": compliance_db}"""
```

Routes must be defined with unique endpoint function names (prefix them by module, e.g.
`alerts_explain`, `docaudit_scan`).

## 3. Shared data shapes

### Alert (seed + runtime)
```
id, title, region, country, country_code?, standard, severity (Critical|Warning|Info),
effective_date (YYYY-MM-DD), affected_categories [category_id | "all_storage_categories"],
summary, action_required, status, source, detailed_summary?, technical_impact?,
timeline_milestones [{phase, date, status}], official_links [{label, url}],
compliance_checklist [str], impacted_products? [{id, sku, name, category_id, ...}],
pillar? (Safety|EMC|Environmental|Cyber|All)
```
Runtime enrichment added by `routes_alerts` when serving: `triage: {status, owner, notes,
updated_at}`, `days_to_effective` (int, negative if past), `impacted_products` (resolved via
`reg_surveillance.resolve_product_impacts`).

### Product
```
id, sku, name, category_id, category_name, hw_revision, controller, nand, power_source,
target_markets [ISO2], compliance_status, active_certs_count, readiness_pct
```

### Certificate
```
id, cert_no, scheme, standard, issuing_body, product_id, product_name, country_coverage,
issue_date, expiry_date, status (Valid|Expiring Soon|Critical|Expired), document_type, notes
```

### Action item
```
id, title, status (Open|In Progress|Blocked|Done), priority (Critical|High|Medium|Low),
owner, due_date, linked_type (alert|document|certificate|product|country), linked_id,
notes, created_at, updated_at
```

### Country (COUNTRIES_DB[code])
See `countries_data.json`: code, name, region, bloc, authority, safety_std, emc_std, env_std,
cb_scheme_accepted, in_country_testing, local_rep_required, cert_validity, marks[],
lead_time_weeks, notes, rohs_std, pfas_std, packaging_std, epr_std,
last_surveilled_date?, last_surveilled_pillar?, surveillance_source?

## 4. API surface

### Core (`routes_core.py`)
| Method | Path | Returns |
|---|---|---|
| GET | `/` | index.html |
| GET | `/api/health` | `{status, version, frozen, data_dir, uptime_s}` |
| GET | `/api/overview` | `{total_countries, total_categories, total_products, total_certificates, active_alerts_count, critical_alerts_count, warning_alerts_count, open_actions_count, regions_count{}, recent_alerts[], pillar_counts{}, surveillance_status{}, triage_counts{}}` |
| GET | `/api/categories` | list of category objects |
| GET | `/api/gma/by-product?category&type&region&search` | `{category_id, category_name, summary{}, countries_count, countries[]}` |
| GET | `/api/gma/export-excel?...` | xlsx |
| GET | `/api/countries?region&bloc&search` | list |
| GET | `/api/countries/<code>` | `{country, category_rules{}, alerts[], products[]}` |
| GET | `/api/products` | list |
| POST | `/api/products` | `{success, product}` |
| GET | `/api/certificates?status&product_id&search` | list |
| POST | `/api/certificates` | `{success, certificate}` |
| POST | `/api/eco/analyze` | eco impact |
| POST | `/api/gma/readiness` | readiness |
| GET | `/api/surveillance/status` | engine status |
| POST | `/api/surveillance/scan` | `{result, status, alerts_count}` |
| GET | `/api/surveillance/log?limit` | `{audit_log[], status, ledger_ok, ledger_entries}` |
| GET/POST | `/api/settings` | public settings / `{success, settings}` |
| GET | `/api/actions` | `{actions[]}` |
| POST | `/api/actions` | `{success, action}` |
| PATCH | `/api/actions/<id>` | `{success, action}` |
| DELETE | `/api/actions/<id>` | `{success}` |
| GET | `/api/search?q=` | `{results: [{type, id, title, subtitle, tab, payload}]}` (countries, alerts, products, standards) |

### Review (`routes_review.py`)
Reviewer = `settings.reviewer_name` (self-declared; 400 "Set your reviewer name in Settings" when empty). With `settings.require_second_reviewer` the approver must differ from `proposed_by`.

| Method | Path | Returns |
|---|---|---|
| GET | `/api/review/queue?status=Pending\|Approved\|Rejected\|all` | `{items[], count, counts{}}` item = `{id "REV-xxxxxxxx", type surveillance_notice\|kb_change, status, created_at, proposed_by, payload, source_url, decided_by, decided_on, decision_note}` |
| GET | `/api/review/stats` | `{pending, approved, rejected, coverage{key_markets_total, verified, needs_reverification, unverified}, audit_ok, audit_entries, reviewer_name, require_second_reviewer, global_sources[], fields{}}` |
| GET | `/api/review/audit?limit` | `{entries[], total, ok, first_bad_index}` (entries `{audit_id, when, who, what, item_id, country_code, before, after, detail, prev_hash, hash}`) |
| POST | `/api/review/proposals` `{country_code, changes{field: value}, reason, source_url, source_label?}` | `{success, item}` (201, Pending). Fields: safety_std, emc_std, env_std, rohs_std, pfas_std, packaging_std, epr_std, notes, authority, in_country_testing, local_rep_required, lead_time_weeks, cert_validity, cb_scheme_accepted |
| POST | `/api/review/queue/<id>/approve` `{note?}` | `{success, item}`. kb_change: write override + apply in memory + mark the pillar(s) Verified with the item's source. surveillance_notice: ledger entry + enriched alert. 409 if already decided |
| POST | `/api/review/queue/<id>/reject` `{note}` (required) | `{success, item}`; rejected notices are never re-queued |
| POST | `/api/verification/<code>` `{scope Safety\|EMC\|Environmental\|Record, status Verified\|Needs review, source_url (required for Verified), source_label?, note?}` | `{success, entry, verification}` |
| DELETE | `/api/overrides/<code>/<field>` | `{success, restored, verification}`; restores the shipped seed value, marks a Verified pillar "Needs review" |

`verification` block (on `/api/gma/by-product` rows and `/api/countries/<code>`): `{overall: Verified\|Needs re-verification\|Partly verified\|Unverified, per_pillar{Safety,EMC,Environmental,Record}, sources[{label,url,kind}], overrides[fields], verified_on, verified_by}`. Source `kind` is "Reviewer citation" (human-recorded) or "Authority portal" (shipped starting point, not a rule citation).

Data files (DATA_DIR): `kb_overrides.json`, `kb_verification.json`, `review_queue.json`, `audit_trail.json`. Shipped (read-only): `kb_sources.json`. `POST /api/surveillance/scan` now returns `queued_for_review`; detected notices are queued, not applied.

### Alerts (`routes_alerts.py`)
| Method | Path | Returns |
|---|---|---|
| GET | `/api/alerts?category&severity&region&search&status&pillar&impacts_portfolio&product_id` | list of enriched alerts |
| POST | `/api/alerts` | `{success, alert}` (enriches sparse input into a full alert) |
| GET | `/api/alerts/<id>` | enriched alert |
| PATCH | `/api/alerts/<id>/triage` body `{status?, owner?, notes?}` | `{success, triage}` |
| GET | `/api/alerts/<id>/explain?audience=simple|executive|engineer&refresh=1` | Explanation (below) |
| GET | `/api/alerts/<id>/expert-consult` | existing expert brief (kept) |
| POST | `/api/alerts/<id>/expert-chat` body `{question}` | existing Q&A (kept) |
| GET | `/api/ai/status` | `{enabled, configured, model, provider, last_error?}` |

**Explanation shape** (`alert_explainer.explain_alert(alert, ctx, audience)`):
```
{
  alert_id, audience, generated_by: "rules" | "claude-opus-5", generated_at,
  headline,                 # one plain sentence, <= 20 words
  one_liner,                # "In one sentence: ..."
  what_changed,             # 2-4 short paragraphs / bullets, plain English
  why_it_matters,           # business + engineering consequences
  who_is_affected: {categories: [{id, name}], products: [{id, sku, name}], markets: [{code, name}], market_count},
  what_to_do: [{step, detail, owner_role, due_by, effort}],
  deadlines: [{label, date, days_remaining, status}],
  cost_effort_estimate: {cost_range, effort_range, basis},
  risk_if_ignored: [str],
  jargon_glossary: [{term, meaning}],
  confidence: {level: High|Medium|Low, basis},
  sources: [{label, url}],
  suggested_questions: [str],
  analogy?                  # only for audience=simple
}
```

### Documents (`routes_docaudit.py`)
| Method | Path | Returns |
|---|---|---|
| POST | `/api/documents/scan-folder` `{folder_path, recursive=true}` | Audit report v2 |
| POST | `/api/documents/upload-scan` multipart `files[]` | Audit report v2 (files processed in a temp dir) |
| GET | `/api/documents/last-report` | last report or `{documents: []}` |
| GET | `/api/documents/export-audit` | xlsx (multi-sheet) |
| POST | `/api/documents/generate-samples` `{target_dir?}` | `{success, message, report}` |
| GET | `/api/documents/browse-dialog` | `{success, folder_path}` |
| POST | `/api/documents/explain` `{index}` | plain-language explanation of one document's impact |

**Audit report v2 shape:**
```
{
  folder_path, scan_timestamp, engine_version,
  total_documents, impacted_documents, health_score (0-100), health_grade (A-F),
  tier_summary {retesting_required, doc_amendment, packaging_update, portal_filing, compliant, unreadable},
  documents: [{metadata:{filename, relative_path, file_size_kb, doc_type, standards_detected[],
               standards_editions[{standard, edition_year?}], product_sku, product_name, product_id?,
               issuing_lab, report_number, issue_date, expiry_date?, days_to_expiry?, markets_detected[]},
              impact:{is_impacted, impact_tier, severity, trigger_alert_id, trigger_alert_title,
               obsolete_standard_cited, required_standard, action_directive, enforcement_deadline,
               days_to_deadline?, estimated_effort, estimated_cost, cost_low, cost_high, rationale[]}}],
  gap_analysis: [{product_id, product_name, market_code, market_name, missing_documents[], covered_documents[]}],
  remediation_plan: [{tier, label, count, items[], cost_low, cost_high, effort_weeks}],
  cost_rollup: {low, high, currency: "USD"},
  standards_index: [{standard, count, status: current|superseded|unknown, replacement?}],
  duplicates: [[filename, filename]],
  alerts_triggered: [{alert_id, title, count}]
}
```

### Risk (`routes_risk.py`)
| Method | Path | Returns |
|---|---|---|
| GET | `/api/risk/summary` | `{compliance_risk_index (0-100, higher = riskier), grade (A-F), trend_note, per_product[], per_region[], per_pillar[], top_risks[], generated_at}` |
| GET | `/api/horizon?days=365` | `{events[], buckets{overdue, next_30, next_90, next_365, beyond}, generated_at}` where event = `{id, type: alert_deadline|milestone|cert_expiry|surveillance, date, days_remaining, title, severity, ref_type, ref_id, product_ids[], country, pillar}` |
| GET | `/api/certificates/health` | `{certificates[], expiring_30, expiring_90, expired, valid}` |
| GET | `/api/portfolio` | `{products: [{...product, risk_score, open_alerts, critical_alerts, certificates_count, next_deadline, readiness: [{market_code, status, badge}]}]}` |

## 5. Frontend contract

`templates/index.html` is the shell. Each tab is a Jinja partial in `templates/partials/`:

| Tab id | Partial | JS module | Owner |
|---|---|---|---|
| `overview` | `tab_overview.html` | `overview.js` | core |
| `matrix` | `tab_matrix.html` | `matrix.js` | core |
| `map` | `tab_map.html` | `map.js` | core |
| `alerts` | `tab_alerts.html` + `modal_explain.html` | `alerts.js`, `expert.js` | alerts |
| `horizon` | `tab_horizon.html` | `horizon.js` | risk |
| `portfolio` | `tab_portfolio.html` | `portfolio.js` | risk |
| `docaudit` | `tab_docaudit.html` | `docaudit.js` | docaudit |
| `review` | `tab_review.html` + `modal_review.html` | `review.js` | review |

Shared modals (core): settings, surveillance log, add alert, actions drawer,
command palette, toast/notification.

Each JS module file registers itself:

```js
GCM.modules.alerts = {
  init() {},          // called once after DOMContentLoaded, all modules loaded
  onShow() {},        // called every time the tab becomes visible
  onFirstShow() {},   // called the first time only (lazy data load)
};
```

`core.js` provides (global `GCM`):

```js
GCM.api.get(url) -> Promise<json>            // throws Error with .status and .message on !ok
GCM.api.post(url, body) / GCM.api.patch(url, body) / GCM.api.del(url)
GCM.api.upload(url, formData)
GCM.api.download(url, filename?)             // triggers browser download + toast
GCM.ui.esc(str)                              // HTML escape
GCM.ui.icons(root?)                          // lucide.createIcons scoped
GCM.ui.toast(title, sub?, kind?, action?)    // kind: success|info|warning|error; action: {label, run}
GCM.ui.notify({title, body, scope?, actions?[]})   // top banner
GCM.ui.openModal(id) / GCM.ui.closeModal(id)
GCM.ui.confirm(message) -> Promise<bool>
GCM.ui.severityClass(sev) -> tailwind classes for a badge
GCM.ui.badge(text, kind) -> html
GCM.ui.fmtDate(iso), GCM.ui.daysUntil(iso) -> int|null, GCM.ui.relDays(iso) -> "in 42 days"/"12 days ago"
GCM.ui.skeleton(rows) -> html, GCM.ui.empty(msg, icon?) -> html
GCM.ui.flag(code) -> emoji
GCM.tabs.switchTo(id), GCM.tabs.current
GCM.state.categories[], GCM.state.countries{code: country}, GCM.state.settings{}
GCM.bus.on(evt, fn), GCM.bus.emit(evt, payload)
   events: 'alerts:changed', 'countries:changed', 'products:changed', 'actions:changed',
           'audit:completed', 'settings:changed', 'tab:shown', 'review:changed'
GCM.palette.register({label, hint, keywords[], run})  // command palette (Ctrl+K)
GCM.actions.createFor(linked_type, linked_id, defaults)  // opens the "new action" drawer prefilled
GCM.deeplink.alert(id) / GCM.deeplink.country(code) / GCM.deeplink.product(id)
```

Design-system classes (in `static/css/custom.css`, usable alongside Tailwind utilities):
`.card`, `.card-header`, `.card-title`, `.btn`, `.btn-primary`, `.btn-secondary`,
`.btn-ghost`, `.btn-danger`, `.btn-sm`, `.input`, `.select`, `.badge`,
`.badge-critical|warning|info|success|neutral`, `.kpi`, `.kpi-value`, `.kpi-label`,
`.table`, `.pill`, `.section-title`, `.skeleton`, `.glass`, `.tab-btn`, `.tab-btn.active`,
`.scrollbar`, `.timeline`, `.progress`, `.progress-bar`.

Color language: Critical = rose, Warning = amber, Info = sky, Success/Compliant = emerald,
Environmental = emerald/teal, EMC = sky, Safety = rose/orange, Cyber = indigo, Packaging = amber,
neutral = slate. Background slate-950, cards slate-900 with slate-800 borders.

## 6. Where files go

```
templates/index.html
templates/partials/*.html
static/css/app.css        (generated - do not edit by hand)
static/css/custom.css     (hand-written design system)
static/js/vendor/lucide.min.js, jsvectormap.min.js, world.js
static/js/app/core.js, overview.js, matrix.js, map.js, alerts.js, expert.js,
              horizon.js, portfolio.js, docaudit.js, surveillance.js, actions.js
```

## 7. Building CSS

`build_assets.bat` (or `npm run build:css` in `tools/`) runs Tailwind v4 CLI:
`tailwindcss -i static/css/tailwind.src.css -o static/css/app.css --minify`.
Tailwind scans `templates/**` and `static/js/app/**`. Any class used only in Python strings
must also appear in `static/css/safelist.txt` (one class per line) - keep server-rendered
classes to the design-system classes above to avoid this.

## 8. Testing checklist (per module)

1. `python -c "import <module>"` succeeds.
2. Route returns JSON and correct status for happy path and invalid input.
3. Tab renders with no console errors; empty states handled; every button does something.
4. Works offline (no network calls on page load except to `/api/...`).
