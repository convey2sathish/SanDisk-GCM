/* =====================================================================
   GCM Platform 2.0 - docaudit.js
   Document Impact Audit workspace: intake (folder scan / browser upload),
   health gauge + KPIs, filterable document list with explanations,
   gap analysis matrix, remediation plan, standards index, Excel export.
   ===================================================================== */
(function () {
  'use strict';
  const GCM = window.GCM;
  if (!GCM) return;
  const esc = (s) => GCM.ui.esc(s);
  const $ = (id) => document.getElementById(id);

  const TIER = {
    retesting_required: { label: 'Re-testing required', badge: 'badge badge-critical', icon: 'flask-conical', text: 'text-rose-300', border: 'border-rose-500/40', glow: 'rgba(244,63,94,.22)', short: 'Re-test' },
    doc_amendment: { label: 'Document amendment', badge: 'badge badge-warning', icon: 'file-signature', text: 'text-amber-300', border: 'border-amber-500/40', glow: 'rgba(245,158,11,.22)', short: 'Re-sign' },
    packaging_update: { label: 'Packaging update', badge: 'badge badge-purple', icon: 'package', text: 'text-purple-300', border: 'border-purple-500/40', glow: 'rgba(168,85,247,.22)', short: 'Packaging' },
    portal_filing: { label: 'Portal filing / renewal', badge: 'badge badge-info', icon: 'globe-2', text: 'text-sky-300', border: 'border-sky-500/40', glow: 'rgba(56,189,248,.22)', short: 'Portal' },
    compliant: { label: 'Compliant', badge: 'badge badge-success', icon: 'check-circle-2', text: 'text-emerald-300', border: 'border-emerald-500/30', glow: 'rgba(52,211,153,.2)', short: 'Compliant' },
    unreadable: { label: 'Unreadable', badge: 'badge badge-neutral', icon: 'file-x', text: 'text-slate-300', border: 'border-slate-600', glow: 'rgba(148,163,184,.15)', short: 'Unreadable' },
  };
  const GRADE_COLOR = { A: '#34d399', B: '#4ade80', C: '#fbbf24', D: '#fb923c', F: '#f43f5e' };
  const TIER_ORDER = { retesting_required: 4, packaging_update: 3, doc_amendment: 2, portal_filing: 1, compliant: 0, unreadable: -1 };
  const SEV_ORDER = { Critical: 3, Warning: 2, Info: 1, None: 0 };
  const TYPE_LABEL = {
    CB_TEST_CERTIFICATE: 'CB Test Certificate', SAFETY_TEST_REPORT: 'Safety Test Report', EMC_LAB_REPORT: 'EMC Lab Report', EU_DECLARATION_OF_CONFORMITY: 'EU Declaration of Conformity',
    UKCA_DECLARATION_OF_CONFORMITY: 'UKCA Declaration of Conformity', FCC_SDOC: "FCC Supplier's DoC", PACKAGING_ARTWORK_SPEC: 'Packaging Artwork Spec', ROHS_CHEMICAL_REPORT: 'RoHS / Chemical Report',
    FMD_BOM_DISCLOSURE: 'Full Material Disclosure', BIS_REGISTRATION_GRANT: 'BIS CRS Registration', KC_CERTIFICATE: 'KC Certificate', BSMI_CERTIFICATE: 'BSMI Certificate', CCC_CERTIFICATE: 'CCC Certificate',
    PSE_CERTIFICATE: 'PSE Certificate', SASO_SABER_CERTIFICATE: 'SASO / SABER Certificate', ENERGY_EFFICIENCY_REPORT: 'Energy Efficiency Report', CYBERSECURITY_SBOM: 'Cybersecurity / SBOM',
    TECHNICAL_COMPLIANCE_FILE: 'Technical Compliance File', UNKNOWN: 'Unclassified',
  };

  const state = { report: null, expanded: new Set(), explanations: {}, gapSel: null, busy: false };

  /* ------------------------------------------------------------------ helpers */
  const typeLabel = (t) => TYPE_LABEL[t] || String(t || '').replace(/_/g, ' ');
  const tierMeta = (t) => TIER[t] || TIER.unreadable;
  const tierBadge = (t) => `<span class="${tierMeta(t).badge}"><i data-lucide="${tierMeta(t).icon}" class="w-3 h-3"></i>${esc(tierMeta(t).label)}</span>`;
  const sevBadge = (s) => (s && s !== 'None') ? GCM.ui.badge(s, s.toLowerCase()) : '';
  const money = (lo, hi) => (lo == null && hi == null) ? '—' : (!hi && !lo) ? '$0' : GCM.ui.money(lo || 0, hi || 0);
  const flag = (code) => code === 'EU' ? '🇪🇺' : GCM.ui.flag(code);
  const marketName = (code) => code === 'EU' ? 'European Union' : ((GCM.state.countries || {})[code] || {}).name || code;
  const daysLabel = (n) => n === null || n === undefined ? '' : n < 0 ? `${-n} days overdue` : n === 0 ? 'due today' : `${n} days left`;
  const deadlineTone = (n) => n === null || n === undefined ? 'neutral' : n < 0 ? 'critical' : n <= 90 ? 'warning' : n <= 365 ? 'info' : 'success';
  const toneBadge = (text, tone) => `<span class="badge badge-${tone}">${esc(text)}</span>`;

  function expiryChip(m) {
    if (!m.expiry_date) return '';
    const n = m.days_to_expiry;
    const tone = n === null ? 'neutral' : n < 0 ? 'critical' : n <= 90 ? 'warning' : n <= 365 ? 'info' : 'success';
    const txt = n === null ? `expiry ${GCM.ui.fmtDate(m.expiry_date)}` : n < 0 ? `expired ${-n}d ago` : `expires in ${n}d`;
    return `<span class="badge badge-${tone}" title="Expiry ${esc(m.expiry_date)}${m.expiry_inferred ? ' (inferred from typical validity - the file states no expiry)' : ' (stated in the file)'}"><i data-lucide="${n !== null && n < 0 ? 'calendar-x' : 'calendar-clock'}" class="w-3 h-3"></i>${esc(txt)}${m.expiry_inferred ? '<span class="opacity-70">*</span>' : ''}</span>`;
  }

  function standardChips(m, limit = 6) {
    const eds = m.standards_editions || [];
    const supersededSet = new Set((state.report && state.report.standards_index || []).filter(s => s.status === 'superseded').map(s => s.standard));
    const obsolete = String((m._impact || {}).obsolete_standard_cited || '');
    const chips = eds.slice(0, limit).map(e => {
      const raw = e.raw || e.standard;
      const bad = (obsolete && obsolete.includes(raw)) || (supersededSet.has(e.standard) && e.edition_year && stdIsSuperseded(e.standard, e.edition_year));
      return `<span class="pill ${bad ? '!bg-rose-950/60 !text-rose-300 !border-rose-800' : ''}" title="${esc(e.standard)}${e.edition_year ? ' edition ' + e.edition_year : ''}">${bad ? '<i data-lucide="alert-triangle" class="w-3 h-3 mr-1"></i>' : ''}${esc(raw)}</span>`;
    });
    if (eds.length > limit) chips.push(`<span class="pill">+${eds.length - limit} more</span>`);
    return chips.join(' ');
  }
  function stdIsSuperseded(std, year) {
    const row = (state.report.standards_index || []).find(s => s.standard === std);
    if (!row || row.status !== 'superseded') return false;
    const bad = row.superseded_editions || [];
    return bad.length ? bad.includes(year) : true;
  }

  /* ------------------------------------------------------------------ data loading */
  async function loadLast() {
    try {
      const r = await GCM.api.get('/api/documents/last-report');
      if (r && Array.isArray(r.documents) && r.documents.length) { render(r, { silent: true }); }
      else showEmpty();
    } catch (e) { showEmpty(); }
  }

  function showEmpty() {
    $('da-empty').classList.remove('hidden');
    $('da-results').classList.add('hidden');
    $('da-export-btn').classList.add('hidden');
    $('da-last-scan').textContent = '';
    GCM.ui.icons();
  }

  function setBusy(on, label) {
    state.busy = on;
    GCM.ui.setLoading($('da-scan-btn'), on, label || 'Scanning…');
    const dz = $('da-dropzone'); if (dz) dz.classList.toggle('opacity-60', on);
  }

  async function scanFolder() {
    if (state.busy) return;
    const folder = $('da-folder-path').value.trim();
    if (!folder) { GCM.ui.toast('Folder path needed', 'Type or browse to the folder that holds your compliance documents.', 'warning'); $('da-folder-path').focus(); return; }
    setBusy(true, 'Scanning folder…');
    try {
      const r = await GCM.api.post('/api/documents/scan-folder', { folder_path: folder, recursive: $('da-recursive').checked });
      try { localStorage.setItem('gcm.docaudit.folder', folder); } catch (_) { /* ignore */ }
      render(r);
      GCM.ui.toast('Audit complete', `${r.total_documents} documents · ${r.impacted_documents} need action · health ${r.health_score}/100 (${r.health_grade})`, r.impacted_documents ? 'warning' : 'success');
    } catch (e) {
      GCM.ui.toast('Scan failed', e.message, 'error');
    } finally { setBusy(false); }
  }

  async function loadSamples() {
    if (state.busy) return;
    const btn = document.querySelector('[data-da=samples]');
    GCM.ui.setLoading(btn, true, 'Creating samples…'); setBusy(true, 'Auditing samples…');
    try {
      const r = await GCM.api.post('/api/documents/generate-samples', {});
      if (r.target_dir) $('da-folder-path').value = r.target_dir;
      render(r.report);
      GCM.ui.toast('Sample documents loaded', r.message, 'success');
    } catch (e) {
      GCM.ui.toast('Could not create samples', e.message, 'error');
    } finally { GCM.ui.setLoading(btn, false); setBusy(false); }
  }

  async function browse() {
    const btn = document.querySelector('[data-da=browse]');
    GCM.ui.setLoading(btn, true, 'Opening…');
    try {
      const cur = $('da-folder-path').value.trim();
      const r = await GCM.api.get('/api/documents/browse-dialog' + (cur ? `?initial=${encodeURIComponent(cur)}` : ''));
      if (r.success && r.folder_path) { $('da-folder-path').value = r.folder_path; $('da-folder-path').focus(); }
      else if (r.error && !/No folder selected/i.test(r.error)) GCM.ui.toast('Folder picker unavailable', r.error, 'warning');
    } catch (e) { GCM.ui.toast('Folder picker unavailable', e.message, 'warning'); }
    finally { GCM.ui.setLoading(btn, false); }
  }

  function exportExcel() {
    if (!state.report || !state.report.documents || !state.report.documents.length) { GCM.ui.toast('Nothing to export', 'Run a scan first.', 'warning'); return; }
    GCM.api.download('/api/documents/export-audit', 'Document Revision Directive');
  }

  /* ------------------------------------------------------------------ browser upload with progress */
  const SUPPORTED = /\.(pdf|docx?|xlsx|xlsm|xls|csv|txt|json|xml|md)$/i;
  function uploadFiles(files) {
    if (state.busy) return;
    const list = Array.from(files || []).filter(f => f && f.name && !/(^|\/)\./.test(f.webkitRelativePath || f.name));
    if (!list.length) { GCM.ui.toast('No files selected', '', 'warning'); return; }
    const supported = list.filter(f => SUPPORTED.test(f.name));
    if (!supported.length) { GCM.ui.toast('No supported files', 'Supported: PDF, DOCX, XLSX/XLSM, CSV, TXT, JSON, XML, MD.', 'warning'); return; }
    const total = supported.reduce((a, f) => a + f.size, 0);
    if (total > 500 * 1024 * 1024) { GCM.ui.toast('Selection too large', 'Please upload less than 500 MB at a time (or scan the folder path instead).', 'warning'); return; }
    const fd = new FormData();
    supported.forEach(f => fd.append('files', f, f.webkitRelativePath || f.relativePath || f.name));
    const prog = $('da-upload-progress'), bar = $('da-upload-bar'), pct = $('da-upload-pct'), lbl = $('da-upload-label');
    prog.classList.remove('hidden'); bar.style.width = '0%'; pct.textContent = '0%'; lbl.textContent = `Uploading ${supported.length} file${supported.length === 1 ? '' : 's'}…`;
    setBusy(true, 'Uploading…');
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/documents/upload-scan');
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) { const p = Math.round(e.loaded / e.total * 100); bar.style.width = p + '%'; pct.textContent = p + '%'; if (p >= 100) { lbl.textContent = 'Analysing documents…'; pct.textContent = ''; bar.classList.add('animate-pulse'); } } };
    xhr.onload = () => {
      bar.classList.remove('animate-pulse'); prog.classList.add('hidden'); setBusy(false);
      let data = null; try { data = JSON.parse(xhr.responseText); } catch (_) { data = null; }
      if (xhr.status >= 200 && xhr.status < 300 && data) {
        render(data);
        const skipped = list.length - supported.length;
        GCM.ui.toast('Audit complete', `${data.total_documents} documents audited${skipped ? ` · ${skipped} unsupported file${skipped === 1 ? '' : 's'} skipped` : ''} · health ${data.health_score}/100`, data.impacted_documents ? 'warning' : 'success');
      } else GCM.ui.toast('Upload failed', (data && data.error) || `${xhr.status} ${xhr.statusText}`, 'error');
    };
    xhr.onerror = () => { prog.classList.add('hidden'); setBusy(false); GCM.ui.toast('Upload failed', 'Server unreachable. Is the GCM Platform still running?', 'error'); };
    xhr.send(fd);
  }

  // Drag & drop with directory traversal (Chromium / Edge)
  function readEntries(entry, path, out) {
    return new Promise((resolve) => {
      if (entry.isFile) { entry.file(f => { try { Object.defineProperty(f, 'relativePath', { value: path + f.name }); } catch (_) { /* ignore */ } out.push(f); resolve(); }, () => resolve()); }
      else if (entry.isDirectory) {
        const reader = entry.createReader(); const all = [];
        const readBatch = () => reader.readEntries(async (ents) => { if (!ents.length) { for (const e of all) await readEntries(e, path + entry.name + '/', out); resolve(); } else { all.push(...ents); readBatch(); } }, () => resolve());
        readBatch();
      } else resolve();
    });
  }
  async function handleDrop(e) {
    e.preventDefault(); $('da-dropzone').classList.remove('border-purple-400', 'bg-purple-500/10');
    const items = e.dataTransfer && e.dataTransfer.items;
    const out = [];
    if (items && items.length && items[0].webkitGetAsEntry) {
      const entries = Array.from(items).map(it => it.webkitGetAsEntry && it.webkitGetAsEntry()).filter(Boolean);
      for (const en of entries) await readEntries(en, '', out);
    }
    if (!out.length && e.dataTransfer && e.dataTransfer.files) out.push(...Array.from(e.dataTransfer.files));
    uploadFiles(out);
  }

  /* ------------------------------------------------------------------ rendering */
  function render(report, opts = {}) {
    if (!report || !Array.isArray(report.documents)) { showEmpty(); return; }
    state.report = report; state.expanded = new Set(); state.explanations = {}; state.gapSel = null;
    report.documents.forEach((d, i) => { d._idx = i; d.metadata._impact = d.impact; });
    $('da-empty').classList.add('hidden'); $('da-results').classList.remove('hidden'); $('da-export-btn').classList.remove('hidden');
    $('da-last-scan').textContent = `Last audit: ${GCM.ui.fmtDateTime(report.scan_timestamp)} · ${report.folder_path || ''}`;
    if (report.folder_path && !/^Browser upload/.test(report.folder_path) && !$('da-folder-path').value) $('da-folder-path').value = report.folder_path;
    renderHealth(report); renderKpis(report); renderAlertChips(report); populateFilters(report); renderDocs(); renderGap(report); renderPlan(report); renderStandards(report); renderDuplicates(report); renderStats(report);
    GCM.ui.icons();
    if (!opts.silent) GCM.bus.emit('audit:completed', report);
  }

  function renderHealth(r) {
    const score = Number(r.health_score || 0), grade = r.health_grade || 'F', n = r.total_documents || 0;
    const g = $('da-gauge'); g.style.setProperty('--value', String(score)); g.style.setProperty('--color', GRADE_COLOR[grade] || '#38bdf8');
    $('da-gauge-score').textContent = n ? String(score) : '–'; $('da-gauge-grade').textContent = n ? grade : '–';
    const verdict = !n ? 'No supported documents were found in this location.'
      : score >= 90 ? 'Evidence is current. Keep an eye on expiries and re-check after the next alert scan.'
      : score >= 80 ? 'Mostly current – a few documents need administrative updates.'
      : score >= 65 ? 'Several files are stale or expired; plan the amendments this quarter.'
      : score >= 50 ? 'Significant exposure: superseded standards or expired approvals affect market access.'
      : 'Critical exposure. Lab re-tests and/or expired approvals put shipments at risk in the affected markets.';
    $('da-health-verdict').textContent = verdict;
    $('da-cost').textContent = money((r.cost_rollup || {}).low, (r.cost_rollup || {}).high) + ' USD';
    $('da-cost').title = (r.cost_rollup || {}).basis || '';
    $('da-expiry-kpi').textContent = `${r.expired_documents || 0} / ${r.expiring_90d_documents || 0}`;
    $('da-health-formula').textContent = r.health_formula ? `Score = ${r.health_formula}.` : '';
  }

  function renderKpis(r) {
    const ts = r.tier_summary || {};
    const tiles = [
      { label: 'Documents scanned', value: r.total_documents, icon: 'files', glow: 'rgba(148,163,184,.18)', cls: 'text-white', filter: '' },
      { label: 'Need action', value: r.impacted_documents, icon: 'alert-octagon', glow: 'rgba(244,63,94,.2)', cls: 'text-rose-300', filter: 'impacted' },
      { label: 'Re-testing', value: ts.retesting_required || 0, icon: 'flask-conical', glow: TIER.retesting_required.glow, cls: TIER.retesting_required.text, filter: 'retesting_required' },
      { label: 'Document amendment', value: ts.doc_amendment || 0, icon: 'file-signature', glow: TIER.doc_amendment.glow, cls: TIER.doc_amendment.text, filter: 'doc_amendment' },
      { label: 'Packaging update', value: ts.packaging_update || 0, icon: 'package', glow: TIER.packaging_update.glow, cls: TIER.packaging_update.text, filter: 'packaging_update' },
      { label: 'Portal filing', value: ts.portal_filing || 0, icon: 'globe-2', glow: TIER.portal_filing.glow, cls: TIER.portal_filing.text, filter: 'portal_filing' },
      { label: 'Compliant', value: ts.compliant || 0, icon: 'check-circle-2', glow: TIER.compliant.glow, cls: TIER.compliant.text, filter: 'compliant' },
      { label: 'Unreadable', value: ts.unreadable || 0, icon: 'file-x', glow: TIER.unreadable.glow, cls: TIER.unreadable.text, filter: 'unreadable' },
    ];
    $('da-kpis').innerHTML = tiles.map(t => `
      <button type="button" class="kpi text-left w-full" style="--kpi-glow:${t.glow}" data-da="kpi-filter" data-arg="${esc(t.filter)}" title="Filter the list">
        <div class="flex items-center justify-between"><span class="kpi-label">${esc(t.label)}</span><i data-lucide="${t.icon}" class="w-4 h-4 ${t.cls}"></i></div>
        <div class="kpi-value ${t.cls}">${GCM.ui.num(t.value)}</div>
      </button>`).join('');
  }

  function renderAlertChips(r) {
    const list = r.alerts_triggered || [];
    $('da-alerts-card').classList.toggle('hidden', !list.length && !(r.scan_stats || {}).alerts_in_rulebook);
    $('da-alert-chips').innerHTML = list.length ? list.map(a => `
      <button type="button" class="pill hover:!bg-slate-700 hover:!text-white transition gap-1.5" data-action="deeplink-alert" data-arg="${esc(a.alert_id)}" title="${esc(a.title || '')} · open in Alerts">
        <span class="w-1.5 h-1.5 rounded-full ${a.severity === 'Critical' ? 'bg-rose-400' : a.severity === 'Warning' ? 'bg-amber-400' : 'bg-sky-400'}"></span>
        <span class="mono">${esc(a.alert_id)}</span><span class="text-slate-300 max-w-[260px] truncate">${esc(a.title || '')}</span><span class="text-slate-500">×${a.count}</span></button>`).join('')
      : `<span class="text-[11px] text-slate-500">No document was linked to a live alert. ${(r.scan_stats || {}).alerts_in_rulebook || 0} alerts were in the rulebook during this scan.</span>`;
  }

  function populateFilters(r) {
    const docs = r.documents;
    const fill = (id, values, fmt) => {
      const sel = $(id); const cur = sel.value; const first = sel.options[0].outerHTML;
      sel.innerHTML = first + values.map(v => `<option value="${esc(v)}">${esc(fmt ? fmt(v) : v)}</option>`).join('');
      if ([...sel.options].some(o => o.value === cur)) sel.value = cur;
    };
    fill('da-f-type', [...new Set(docs.map(d => d.metadata.doc_type))].sort(), typeLabel);
    fill('da-f-product', [...new Set(docs.map(d => d.metadata.product_sku).filter(Boolean))].sort(), v => { const d = docs.find(x => x.metadata.product_sku === v); return v === 'General / Multi-Product' ? 'Not matched to a product' : `${v} · ${(d && d.metadata.product_name) || ''}`; });
    fill('da-f-market', [...new Set(docs.flatMap(d => d.metadata.markets_detected || []))].sort(), v => `${flag(v)} ${marketName(v)}`);
  }

  function filteredDocs() {
    const r = state.report; if (!r) return [];
    const tier = $('da-f-tier').value, type = $('da-f-type').value, prod = $('da-f-product').value, mk = $('da-f-market').value, q = $('da-f-search').value.trim().toLowerCase(), sort = $('da-f-sort').value;
    let out = r.documents.filter(d => {
      const m = d.metadata, i = d.impact;
      if (tier === 'impacted' ? !i.is_impacted : tier && i.impact_tier !== tier) return false;
      if (type && m.doc_type !== type) return false;
      if (prod && m.product_sku !== prod) return false;
      if (mk && !(m.markets_detected || []).includes(mk)) return false;
      if (q) {
        const hay = [m.filename, m.relative_path, m.product_sku, m.product_name, m.issuing_lab, m.report_number, (m.standards_editions || []).map(e => e.raw).join(' '), i.action_directive, i.trigger_alert_id, i.obsolete_standard_cited, i.required_standard, typeLabel(m.doc_type)].join(' ').toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    const big = 1e9;
    const sorters = {
      urgency: (a, b) => (TIER_ORDER[b.impact.impact_tier] - TIER_ORDER[a.impact.impact_tier]) || (SEV_ORDER[b.impact.severity] - SEV_ORDER[a.impact.severity]) || ((a.impact.days_to_deadline ?? big) - (b.impact.days_to_deadline ?? big)),
      deadline: (a, b) => ((a.impact.days_to_deadline ?? big) - (b.impact.days_to_deadline ?? big)),
      expiry: (a, b) => ((a.metadata.days_to_expiry ?? big) - (b.metadata.days_to_expiry ?? big)),
      cost: (a, b) => (b.impact.cost_high || 0) - (a.impact.cost_high || 0),
      name: (a, b) => a.metadata.filename.localeCompare(b.metadata.filename),
      product: (a, b) => (a.metadata.product_name || '').localeCompare(b.metadata.product_name || '') || a.metadata.filename.localeCompare(b.metadata.filename),
    };
    out.sort(sorters[sort] || sorters.urgency);
    return out;
  }

  function renderDocs() {
    const docs = filteredDocs();
    $('da-showing').textContent = `${docs.length} of ${state.report.documents.length}`;
    const host = $('da-doclist');
    if (!docs.length) { host.innerHTML = GCM.ui.empty('No documents match these filters.', 'filter-x'); GCM.ui.icons(); return; }
    host.innerHTML = docs.map(docRow).join('');
    GCM.ui.icons();
  }

  function docRow(d) {
    const m = d.metadata, i = d.impact, t = tierMeta(i.impact_tier), open = state.expanded.has(d._idx);
    const dl = i.days_to_deadline;
    const deadline = i.enforcement_deadline && !['Ongoing', 'n/a'].includes(i.enforcement_deadline)
      ? `<span class="badge badge-${deadlineTone(dl)}" title="Enforcement / renewal deadline"><i data-lucide="calendar" class="w-3 h-3"></i>${esc(/^\d{4}-\d{2}-\d{2}$/.test(i.enforcement_deadline) ? GCM.ui.fmtDate(i.enforcement_deadline) : i.enforcement_deadline)}${dl !== null && dl !== undefined ? ` · ${esc(daysLabel(dl))}` : ''}</span>` : '';
    const productLine = m.product_id
      ? `<button type="button" class="hover:text-white underline decoration-dotted" data-action="deeplink-product" data-arg="${esc(m.product_id)}" title="Open in Portfolio">${esc(m.product_name)}</button> <span class="mono text-slate-500">${esc(m.product_sku)}</span>`
      : `<span class="text-slate-500">Not matched to a portfolio product${m.product_sku && m.product_sku !== 'General / Multi-Product' ? ` (SKU ${esc(m.product_sku)})` : ''}</span>`;
    return `
    <article class="card !p-0 overflow-hidden border-l-4 ${t.border} ${open ? 'ring-1 ring-slate-600' : ''}" id="da-doc-${d._idx}" data-idx="${d._idx}">
      <div class="w-full text-left p-4 flex flex-col lg:flex-row lg:items-center gap-3 cursor-pointer hover:bg-slate-800/30 transition" data-da="toggle" data-arg="${d._idx}" role="button" tabindex="0" aria-expanded="${open}">
        <div class="flex items-start gap-3 min-w-0 flex-1">
          <div class="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0"><i data-lucide="${t.icon}" class="w-4 h-4 ${t.text}"></i></div>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-sm font-semibold text-white break-all">${esc(m.filename)}</span>
              <span class="pill">${esc(typeLabel(m.doc_type))}</span>
              ${m.relative_path && m.relative_path !== m.filename ? `<span class="text-[10px] text-slate-500 mono truncate max-w-[280px]" title="${esc(m.relative_path)}">${esc(m.relative_path)}</span>` : ''}
            </div>
            <div class="text-[11px] text-slate-400 mt-1 flex flex-wrap gap-x-3 gap-y-1">
              <span><i data-lucide="hard-drive" class="w-3 h-3 inline -mt-0.5 text-slate-500"></i> ${productLine}</span>
              <span title="Issuing lab / body"><i data-lucide="building-2" class="w-3 h-3 inline -mt-0.5 text-slate-500"></i> ${esc(m.issuing_lab || 'Not identified')}</span>
              <span title="Report / certificate number"><i data-lucide="hash" class="w-3 h-3 inline -mt-0.5 text-slate-500"></i> <span class="mono">${esc(m.report_number || 'N/A')}</span></span>
              ${m.issue_date ? `<span title="Issue date"><i data-lucide="calendar-days" class="w-3 h-3 inline -mt-0.5 text-slate-500"></i> ${esc(GCM.ui.fmtDate(m.issue_date))}</span>` : ''}
              ${(m.markets_detected || []).length ? `<span title="Markets referenced: ${esc((m.markets_detected || []).map(marketName).join(', '))}">${(m.markets_detected || []).slice(0, 8).map(c => flag(c)).join(' ')}${m.markets_detected.length > 8 ? ` +${m.markets_detected.length - 8}` : ''}</span>` : ''}
            </div>
            <div class="mt-2 flex flex-wrap gap-1.5 items-center">${standardChips(m)}${expiryChip(m)}</div>
          </div>
        </div>
        <div class="flex flex-wrap lg:flex-col lg:items-end gap-1.5 shrink-0">
          <div class="flex items-center gap-1.5">${tierBadge(i.impact_tier)}${sevBadge(i.severity)}</div>
          <div class="flex items-center gap-1.5">${deadline}${i.cost_high ? `<span class="pill mono" title="${esc(i.estimated_cost)}">${esc(money(i.cost_low, i.cost_high))}</span>` : ''}</div>
          <i data-lucide="${open ? 'chevron-up' : 'chevron-down'}" class="w-4 h-4 text-slate-500 hidden lg:block"></i>
        </div>
      </div>
      ${open ? docDetail(d) : ''}
    </article>`;
  }

  function docDetail(d) {
    const m = d.metadata, i = d.impact, ex = state.explanations[d._idx];
    const findings = i.findings || [];
    return `
    <div class="border-t border-slate-800 bg-slate-950/40 p-4 grid grid-cols-1 xl:grid-cols-12 gap-4">
      <div class="xl:col-span-7 space-y-3">
        <div>
          <div class="section-title mb-1"><i data-lucide="target" class="w-3.5 h-3.5 text-rose-400"></i> Action directive</div>
          <p class="text-xs text-slate-100 leading-relaxed">${esc(i.action_directive)}</p>
        </div>
        ${(i.rationale || []).length ? `<div><div class="section-title mb-1"><i data-lucide="help-circle" class="w-3.5 h-3.5 text-sky-400"></i> Why</div><ul class="text-xs text-slate-300 space-y-1 list-disc pl-4 leading-relaxed">${i.rationale.map(r => `<li>${esc(r)}</li>`).join('')}</ul></div>` : ''}
        ${findings.length > 1 ? `<div><div class="section-title mb-1"><i data-lucide="layers" class="w-3.5 h-3.5 text-amber-400"></i> All findings (${findings.length})</div><div class="space-y-1">${findings.map(f => `<div class="flex items-start gap-2 text-[11px] text-slate-300 rounded-lg bg-slate-900/70 border border-slate-800 p-2">${tierBadge(f.impact_tier)}<div class="min-w-0"><div>${esc(f.action_directive)}</div><div class="text-slate-500 mt-0.5">${f.trigger_alert_id ? `alert <span class="mono">${esc(f.trigger_alert_id)}</span> · ` : ''}confidence ${esc(f.confidence)} · ${esc(money(f.cost_low, f.cost_high))}</div></div></div>`).join('')}</div></div>` : ''}
        ${i.impact_tier === 'unreadable' && m.unreadable_reason ? `<div class="text-[11px] text-slate-400">Reason: <span class="mono text-slate-300">${esc(m.unreadable_reason)}</span></div>` : ''}
        <div id="da-explain-${d._idx}">${ex ? explanationPanel(ex) : ''}</div>
      </div>
      <div class="xl:col-span-5 space-y-3">
        <div class="grid grid-cols-2 gap-2 text-[11px]">
          <div class="rounded-lg bg-slate-900/70 border border-slate-800 p-2.5"><div class="text-slate-500 uppercase tracking-wider text-[9px]">Cited (obsolete)</div><div class="text-slate-100 mt-0.5 break-words">${esc(i.obsolete_standard_cited || '—')}</div></div>
          <div class="rounded-lg bg-slate-900/70 border border-slate-800 p-2.5"><div class="text-slate-500 uppercase tracking-wider text-[9px]">Required now</div><div class="text-emerald-300 mt-0.5 break-words">${esc(i.required_standard || '—')}</div></div>
          <div class="rounded-lg bg-slate-900/70 border border-slate-800 p-2.5"><div class="text-slate-500 uppercase tracking-wider text-[9px]">Indicative cost</div><div class="text-slate-100 mono mt-0.5">${esc(i.estimated_cost || '$0')}</div></div>
          <div class="rounded-lg bg-slate-900/70 border border-slate-800 p-2.5"><div class="text-slate-500 uppercase tracking-wider text-[9px]">Effort</div><div class="text-slate-100 mt-0.5">${esc(i.estimated_effort || 'None')}</div></div>
          <div class="rounded-lg bg-slate-900/70 border border-slate-800 p-2.5"><div class="text-slate-500 uppercase tracking-wider text-[9px]">Deadline</div><div class="text-slate-100 mt-0.5">${esc(i.enforcement_deadline || 'Ongoing')}${i.days_to_deadline !== null && i.days_to_deadline !== undefined ? `<div class="text-[10px] ${i.days_to_deadline < 0 ? 'text-rose-300' : 'text-slate-400'}">${esc(daysLabel(i.days_to_deadline))}</div>` : ''}</div></div>
          <div class="rounded-lg bg-slate-900/70 border border-slate-800 p-2.5"><div class="text-slate-500 uppercase tracking-wider text-[9px]">Expiry</div><div class="text-slate-100 mt-0.5">${m.expiry_date ? esc(GCM.ui.fmtDate(m.expiry_date)) + (m.expiry_inferred ? ' <span class="text-slate-500" title="Inferred from typical validity">(inferred)</span>' : '') : '—'}</div></div>
        </div>
        ${i.trigger_alert_id ? `<button type="button" class="w-full text-left rounded-lg border border-rose-900/60 bg-rose-950/30 hover:bg-rose-950/50 p-2.5 text-[11px] transition" data-action="deeplink-alert" data-arg="${esc(i.trigger_alert_id)}"><div class="flex items-center gap-1.5 text-rose-300 font-semibold"><i data-lucide="bell-ring" class="w-3.5 h-3.5"></i>Triggered by alert <span class="mono">${esc(i.trigger_alert_id)}</span><i data-lucide="arrow-up-right" class="w-3 h-3 ml-auto"></i></div><div class="text-slate-300 mt-0.5">${esc(i.trigger_alert_title || '')}</div></button>` : ''}
        <div class="text-[11px] text-slate-400 space-y-0.5">
          <div><span class="text-slate-500">All standards:</span> ${(m.standards_editions || []).map(e => `<span class="mono text-slate-300">${esc(e.raw || e.standard)}</span>`).join(', ') || '—'}</div>
          <div><span class="text-slate-500">Markets:</span> ${(m.markets_detected || []).map(c => `${flag(c)} ${esc(marketName(c))}`).join(', ') || '—'}</div>
          <div><span class="text-slate-500">File:</span> <span class="mono">${esc(m.relative_path || m.filename)}</span> · ${esc(String(m.file_size_kb || 0))} KB · classification confidence ${esc(String(m.doc_type_confidence || 0))}%</div>
        </div>
        <div class="flex flex-wrap gap-2 pt-1">
          <button type="button" class="btn btn-indigo btn-sm" data-da="explain" data-arg="${d._idx}"><i data-lucide="message-circle-question" class="w-3.5 h-3.5"></i>${ex ? 'Refresh explanation' : 'Explain in plain English'}</button>
          ${i.impact_tier !== 'compliant' ? `<button type="button" class="btn btn-secondary btn-sm" data-da="create-action" data-arg="${d._idx}"><i data-lucide="plus-square" class="w-3.5 h-3.5 text-emerald-400"></i>Create action</button>` : ''}
          <button type="button" class="btn btn-ghost btn-sm" data-da="copy" data-arg="${d._idx}" title="Copy the directive to the clipboard"><i data-lucide="clipboard-copy" class="w-3.5 h-3.5"></i>Copy directive</button>
        </div>
      </div>
    </div>`;
  }

  function explanationPanel(ex) {
    return `
    <div class="rounded-xl border border-indigo-800/60 bg-indigo-950/30 p-3.5 space-y-2.5">
      <div class="flex items-center gap-2 text-indigo-300 text-[11px] font-bold uppercase tracking-wider"><i data-lucide="sparkles" class="w-3.5 h-3.5"></i> In plain English</div>
      <div class="text-sm font-semibold text-white leading-snug">${esc(ex.headline)}</div>
      <p class="text-xs text-slate-200 leading-relaxed">${esc(ex.plain_english)}</p>
      ${(ex.why || []).length ? `<div><div class="text-[10px] uppercase tracking-wider text-slate-400 mb-1">Why this matters</div><ul class="text-xs text-slate-300 list-disc pl-4 space-y-0.5">${ex.why.map(w => `<li>${esc(w)}</li>`).join('')}</ul></div>` : ''}
      ${(ex.next_steps || []).length ? `<div><div class="text-[10px] uppercase tracking-wider text-slate-400 mb-1">Next steps</div><ol class="text-xs text-slate-200 list-decimal pl-4 space-y-0.5">${ex.next_steps.map(s => `<li>${esc(s)}</li>`).join('')}</ol></div>` : ''}
      ${(ex.glossary || []).length ? `<div><div class="text-[10px] uppercase tracking-wider text-slate-400 mb-1">Jargon buster</div><div class="flex flex-wrap gap-1.5">${ex.glossary.map(g => `<span class="pill cursor-help" title="${esc(g.meaning)}">${esc(g.term)}</span>`).join('')}</div></div>` : ''}
    </div>`;
  }

  async function explain(idx) {
    const host = $(`da-explain-${idx}`); if (!host) return;
    host.innerHTML = '<div class="skeleton h-24 w-full rounded-xl"></div>';
    try {
      const ex = await GCM.api.post('/api/documents/explain', { index: idx });
      state.explanations[idx] = ex;
      const el = $(`da-doc-${idx}`), d = state.report.documents[idx];
      if (el && d) el.outerHTML = docRow(d); else host.innerHTML = explanationPanel(ex);
    } catch (e) { host.innerHTML = `<div class="text-xs text-rose-300">Could not explain: ${esc(e.message)}</div>`; }
    GCM.ui.icons();
  }

  function createAction(idx) {
    const d = state.report.documents[idx]; if (!d) return;
    const m = d.metadata, i = d.impact, t = tierMeta(i.impact_tier);
    const due = /^\d{4}-\d{2}-\d{2}$/.test(i.enforcement_deadline || '') ? i.enforcement_deadline : (m.expiry_date && m.days_to_expiry !== null && m.days_to_expiry < 0 ? new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10) : '');
    GCM.actions.createFor('document', m.filename, {
      title: `${t.short}: ${m.filename}`.slice(0, 200),
      priority: i.severity === 'Critical' ? 'Critical' : i.severity === 'Warning' ? 'High' : 'Medium',
      due_date: due,
      notes: [i.action_directive, i.trigger_alert_id ? `Alert: ${i.trigger_alert_id} - ${i.trigger_alert_title || ''}` : '', i.cost_high ? `Indicative cost ${money(i.cost_low, i.cost_high)}, effort ${i.estimated_effort}` : '', m.product_sku ? `Product: ${m.product_name} (${m.product_sku})` : ''].filter(Boolean).join('\n').slice(0, 1900),
    });
  }

  function toggle(idx) {
    if (state.expanded.has(idx)) state.expanded.delete(idx); else state.expanded.add(idx);
    const el = $(`da-doc-${idx}`); const d = state.report.documents[idx];
    if (el && d) { el.outerHTML = docRow(d); GCM.ui.icons(); }
  }

  /* ------------------------------------------------------------------ gap analysis */
  function renderGap(r) {
    const rows = r.gap_analysis || [], gs = r.gap_summary || {};
    const host = $('da-gap-matrix'); $('da-gap-detail').classList.add('hidden');
    $('da-gap-summary').innerHTML = rows.length ? [
      toneBadge(`${gs.coverage_pct || 0}% covered`, (gs.coverage_pct || 0) >= 80 ? 'success' : (gs.coverage_pct || 0) >= 40 ? 'warning' : 'critical'),
      `<span class="pill">${esc(String(gs.products || 0))} products</span>`, `<span class="pill">${esc(String(gs.markets || 0))} product × market pairs</span>`,
      `<span class="pill">${esc(String(gs.missing || 0))} missing</span>`, `<span class="pill" title="Administrative / commercial paperwork the scanner cannot assess">${esc(String(gs.not_assessed || 0))} not assessed</span>`,
      `<span class="pill" title="Scope of the analysis">${esc(gs.scope || '')}</span>`].join('') : '';
    if (!rows.length) { host.innerHTML = GCM.ui.empty('No portfolio products with target markets to analyse.', 'grid-3x3'); return; }
    const products = []; const byP = {};
    rows.forEach(g => { if (!byP[g.product_id]) { byP[g.product_id] = { id: g.product_id, name: g.product_name, sku: g.product_sku, cells: {} }; products.push(byP[g.product_id]); } byP[g.product_id].cells[g.market_code] = g; });
    const markets = [...new Set(rows.map(g => g.market_code))].sort();
    const cellClass = (g) => g.coverage_pct >= 80 ? 'bg-emerald-950/60 text-emerald-300 border-emerald-900' : g.coverage_pct >= 40 ? 'bg-amber-950/50 text-amber-300 border-amber-900' : 'bg-rose-950/50 text-rose-300 border-rose-900';
    host.innerHTML = `
      <table class="table text-[11px]">
        <thead><tr><th class="!min-w-[220px]">Product</th>${markets.map(c => `<th class="text-center !px-2" title="${esc(marketName(c))}">${flag(c)}<div class="mono">${esc(c)}</div></th>`).join('')}</tr></thead>
        <tbody>${products.map(p => `<tr>
          <td><div class="font-semibold text-slate-100 leading-snug">${esc(p.name)}</div><div class="mono text-slate-500 text-[10px]">${esc(p.sku || '')}</div></td>
          ${markets.map(c => { const g = p.cells[c]; if (!g) return '<td class="text-center text-slate-700">·</td>'; const tot = g.covered_documents.length + g.missing_documents.length; const sel = state.gapSel && state.gapSel.p === p.id && state.gapSel.m === c;
            return `<td class="text-center !p-1"><button type="button" class="w-full rounded-md border px-1.5 py-1.5 mono font-bold transition hover:brightness-125 ${cellClass(g)} ${sel ? 'ring-2 ring-white/70' : ''}" data-da="gap-cell" data-p="${esc(p.id)}" data-m="${esc(c)}" title="${esc(g.market_name)} · ${g.coverage_pct}% · ${esc(g.requirement_type || '')}">${g.covered_documents.length}/${tot}</button></td>`; }).join('')}
        </tr>`).join('')}</tbody>
      </table>`;
  }

  function gapDetail(pid, code) {
    const g = (state.report.gap_analysis || []).find(x => x.product_id === pid && x.market_code === code); if (!g) return;
    state.gapSel = { p: pid, m: code };
    const box = $('da-gap-detail'); box.classList.remove('hidden');
    box.innerHTML = `
      <div class="flex flex-wrap items-start justify-between gap-3 mb-3">
        <div><div class="text-sm font-semibold text-white">${flag(code)} ${esc(g.market_name)} · ${esc(g.product_name)}</div><div class="text-[11px] text-slate-400 mt-0.5">${esc(g.requirement_type || '')} · ${g.coverage_pct}% of assessable documents covered</div></div>
        <div class="flex items-center gap-2"><button type="button" class="btn btn-secondary btn-sm" data-action="deeplink-country" data-arg="${esc(code)}"><i data-lucide="globe-2" class="w-3.5 h-3.5"></i>Country dossier</button><button type="button" class="btn btn-secondary btn-sm" data-action="deeplink-product" data-arg="${esc(pid)}"><i data-lucide="hard-drive" class="w-3.5 h-3.5"></i>Product</button><button type="button" class="btn btn-ghost btn-sm" data-da="gap-close"><i data-lucide="x" class="w-3.5 h-3.5"></i></button></div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        <div><div class="section-title text-rose-300 mb-1.5"><i data-lucide="file-minus" class="w-3.5 h-3.5"></i> Missing (${g.missing_documents.length})</div>${g.missing_documents.length ? `<ul class="space-y-1">${g.missing_documents.map(x => `<li class="flex items-start gap-1.5 text-slate-200"><i data-lucide="circle-alert" class="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5"></i><span>${esc(x)}</span></li>`).join('')}</ul><button type="button" class="btn btn-secondary btn-sm mt-2" data-da="gap-action" data-p="${esc(pid)}" data-m="${esc(code)}"><i data-lucide="plus-square" class="w-3.5 h-3.5 text-emerald-400"></i>Create action for these gaps</button>` : '<div class="text-slate-500">Nothing missing among assessable documents.</div>'}</div>
        <div><div class="section-title text-emerald-300 mb-1.5"><i data-lucide="file-check-2" class="w-3.5 h-3.5"></i> Covered (${g.covered_documents.length})</div>${g.covered_documents.length ? `<ul class="space-y-1">${g.covered_documents.map(x => `<li class="flex items-start gap-1.5 text-slate-300"><i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5"></i><span>${esc(x)}${(g.evidence || {})[x] ? `<div class="text-[10px] text-slate-500 mono">${esc(g.evidence[x])}</div>` : ''}</span></li>`).join('')}</ul>` : '<div class="text-slate-500">No file in this folder covers a requirement for this market.</div>'}</div>
        <div><div class="section-title mb-1.5"><i data-lucide="file-question" class="w-3.5 h-3.5"></i> Not assessed (${(g.not_assessed || []).length})</div><div class="text-[10px] text-slate-500 mb-1">Commercial / administrative paperwork the file scanner cannot verify.</div><ul class="space-y-1">${(g.not_assessed || []).map(x => `<li class="text-slate-400">· ${esc(x)}</li>`).join('')}</ul></div>
      </div>`;
    renderGap(state.report); box.classList.remove('hidden'); GCM.ui.icons();
    box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  /* ------------------------------------------------------------------ plan / standards / dups / stats */
  function renderPlan(r) {
    const plan = r.remediation_plan || [];
    $('da-plan').innerHTML = plan.length ? plan.map((g, gi) => { const t = tierMeta(g.tier); return `
      <details class="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden" ${gi === 0 ? 'open' : ''}>
        <summary class="cursor-pointer list-none p-3 flex flex-wrap items-center gap-3 hover:bg-slate-800/40">
          <div class="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center"><i data-lucide="${t.icon}" class="w-4 h-4 ${t.text}"></i></div>
          <div class="flex-1 min-w-[200px]"><div class="text-sm font-semibold text-white">${esc(g.label)} <span class="text-slate-400 font-normal">· ${g.count} document${g.count === 1 ? '' : 's'}</span></div><div class="text-[11px] text-slate-400">Owner: ${esc(g.owner_hint || '')}</div></div>
          <div class="flex items-center gap-2 text-[11px]"><span class="pill mono">${esc(money(g.cost_low, g.cost_high))}</span><span class="pill">${g.effort_weeks} wk critical path</span><span class="pill" title="If done one after another">${g.effort_weeks_serial} wk serial</span></div>
        </summary>
        <div class="border-t border-slate-800 divide-y divide-slate-800/70">${g.items.map(it => `
          <div class="p-3 flex flex-col md:flex-row md:items-center gap-2 text-xs">
            <div class="flex-1 min-w-0"><button type="button" class="font-semibold text-slate-100 hover:text-white underline decoration-dotted text-left break-all" data-da="focus" data-arg="${it.index}">${esc(it.filename)}</button><div class="text-slate-400 text-[11px] mt-0.5 leading-snug">${esc(it.action_directive)}</div></div>
            <div class="flex flex-wrap items-center gap-1.5 shrink-0">${sevBadge(it.severity)}${it.enforcement_deadline && !['Ongoing', 'n/a'].includes(it.enforcement_deadline) ? toneBadge(it.enforcement_deadline, deadlineTone(it.days_to_deadline)) : ''}<span class="pill mono">${esc(money(it.cost_low, it.cost_high))}</span><span class="pill">${it.effort_weeks} wk</span>${it.trigger_alert_id ? `<button type="button" class="pill hover:!text-white" data-action="deeplink-alert" data-arg="${esc(it.trigger_alert_id)}">${esc(it.trigger_alert_id)}</button>` : ''}</div>
          </div>`).join('')}</div>
      </details>`; }).join('') : GCM.ui.empty('Nothing to remediate - every readable document is compliant.', 'party-popper');
  }

  function renderStandards(r) {
    const idx = r.standards_index || [];
    $('da-standards').innerHTML = idx.length ? idx.map(s => {
      const cls = s.status === 'superseded' ? '!bg-rose-950/60 !text-rose-300 !border-rose-800' : s.status === 'unknown' ? '' : '!bg-emerald-950/40 !text-emerald-300 !border-emerald-900';
      const tip = `${s.standard}${s.editions && s.editions.length ? ' · editions ' + s.editions.join(', ') : ''} · ${s.status}${s.replacement ? ' → ' + s.replacement : ''} · in ${(s.documents || []).length} file(s)`;
      return `<button type="button" class="pill ${cls} hover:brightness-125 gap-1" data-da="std-filter" data-arg="${esc(s.standard)}" title="${esc(tip)}">${s.status === 'superseded' ? '<i data-lucide="alert-triangle" class="w-3 h-3"></i>' : ''}${esc(s.standard)}${s.editions && s.editions.length ? `<span class="opacity-70">:${esc(s.editions.join('/'))}</span>` : ''}<span class="opacity-60">×${s.count}</span></button>`;
    }).join('') : '<span class="text-[11px] text-slate-500">No standards were detected.</span>';
  }

  function renderDuplicates(r) {
    const d = r.duplicates || [];
    $('da-duplicates').innerHTML = d.length ? `<div class="flex items-start gap-2 text-amber-300 text-[11px] mb-2"><i data-lucide="alert-triangle" class="w-3.5 h-3.5 shrink-0 mt-0.5"></i>${d.length} pair${d.length === 1 ? '' : 's'} share a report number or file name stem - keep one master copy in the technical file.</div>` + d.map(p => `<div class="rounded-lg bg-slate-900/70 border border-slate-800 p-2 mono text-[10px] text-slate-300 break-all">${esc(p[0])}<div class="text-slate-500">↔ ${esc(p[1])}</div></div>`).join('')
      : '<div class="text-[11px] text-slate-500 flex items-center gap-1.5"><i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400"></i>No duplicate report numbers or file stems found.</div>';
  }

  function renderStats(r) {
    const s = r.scan_stats || {};
    $('da-scan-stats').innerHTML = [
      `<span><i data-lucide="folder" class="w-3 h-3 inline -mt-0.5"></i> ${esc(r.folder_path || '')}</span>`,
      `<span>${esc(String(s.files_seen ?? r.total_documents))} files seen</span>`, `<span>${esc(String(s.files_supported ?? r.total_documents))} supported</span>`,
      `<span>${esc(String(s.files_unreadable ?? 0))} unreadable</span>`, s.files_skipped_unsupported ? `<span>${esc(String(s.files_skipped_unsupported))} skipped (unsupported type)</span>` : '',
      `<span>${esc(String(s.duration_s ?? 0))} s</span>`, `<span>${esc(String(s.alerts_in_rulebook ?? 0))} live alerts in rulebook</span>`, `<span>${esc(String(s.products_in_portfolio ?? 0))} portfolio products</span>`,
      `<span>engine v${esc(r.engine_version || '')}</span>`, `<span>${esc(GCM.ui.fmtDateTime(r.scan_timestamp))}</span>`].filter(Boolean).join('');
  }

  /* ------------------------------------------------------------------ focus / deep link */
  function focusDoc(idx) {
    if (!state.report || !state.report.documents[idx]) return;
    ['da-f-tier', 'da-f-type', 'da-f-product', 'da-f-market'].forEach(id => { $(id).value = ''; }); $('da-f-search').value = '';
    state.expanded.add(idx); renderDocs();
    const el = $(`da-doc-${idx}`); if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.classList.add('ring-2', 'ring-purple-400'); setTimeout(() => el.classList.remove('ring-2', 'ring-purple-400'), 2200); }
  }

  /* ------------------------------------------------------------------ wiring */
  function wire() {
    const root = $('docaudit-root'); if (!root) return;
    root.addEventListener('click', (e) => {
      const el = e.target.closest('[data-da]'); if (!el || !root.contains(el)) return;
      const act = el.dataset.da, arg = el.dataset.arg;
      switch (act) {
        case 'scan': scanFolder(); break;
        case 'samples': loadSamples(); break;
        case 'browse': browse(); break;
        case 'export': exportExcel(); break;
        case 'pick-folder': e.stopPropagation(); $('da-folder-input').click(); break;
        case 'pick-files': e.stopPropagation(); $('da-files-input').click(); break;
        case 'toggle': if (e.target.closest('[data-action]')) return; toggle(Number(arg)); break;
        case 'explain': explain(Number(arg)); break;
        case 'create-action': createAction(Number(arg)); break;
        case 'copy': { const d = state.report.documents[Number(arg)]; if (d) GCM.ui.copy(`${d.metadata.filename}\n${d.impact.action_directive}`); break; }
        case 'focus': focusDoc(Number(arg)); break;
        case 'kpi-filter': $('da-f-tier').value = arg || ''; renderDocs(); $('da-filters').scrollIntoView({ behavior: 'smooth', block: 'start' }); break;
        case 'std-filter': $('da-f-search').value = arg || ''; renderDocs(); $('da-doclist').scrollIntoView({ behavior: 'smooth', block: 'start' }); break;
        case 'clear-filters': ['da-f-tier', 'da-f-type', 'da-f-product', 'da-f-market'].forEach(id => { $(id).value = ''; }); $('da-f-search').value = ''; $('da-f-sort').value = 'urgency'; renderDocs(); break;
        case 'gap-cell': gapDetail(el.dataset.p, el.dataset.m); break;
        case 'gap-close': state.gapSel = null; $('da-gap-detail').classList.add('hidden'); renderGap(state.report); break;
        case 'gap-action': { const g = (state.report.gap_analysis || []).find(x => x.product_id === el.dataset.p && x.market_code === el.dataset.m); if (g) GCM.actions.createFor('product', g.product_id, { title: `Close ${g.missing_documents.length} document gap${g.missing_documents.length === 1 ? '' : 's'} for ${g.market_code} - ${g.product_sku}`.slice(0, 200), priority: 'High', notes: `${g.product_name} · ${g.market_name} (${g.requirement_type})\nMissing:\n${g.missing_documents.map(x => '- ' + x).join('\n')}`.slice(0, 1900) }); break; }
        default: break;
      }
    });
    root.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      const el = e.target.closest('[data-da=toggle]'); if (!el || e.target !== el) return;
      e.preventDefault(); toggle(Number(el.dataset.arg));
    });
    ['da-f-tier', 'da-f-type', 'da-f-product', 'da-f-market', 'da-f-sort'].forEach(id => $(id).addEventListener('change', renderDocs));
    let t = null; $('da-f-search').addEventListener('input', () => { clearTimeout(t); t = setTimeout(renderDocs, 150); });
    $('da-folder-path').addEventListener('keydown', (e) => { if (e.key === 'Enter') scanFolder(); });
    $('da-folder-input').addEventListener('change', (e) => { uploadFiles(e.target.files); e.target.value = ''; });
    $('da-files-input').addEventListener('change', (e) => { uploadFiles(e.target.files); e.target.value = ''; });
    const dz = $('da-dropzone');
    dz.addEventListener('click', (e) => { if (e.target.closest('[data-da]')) return; $('da-folder-input').click(); });
    dz.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $('da-folder-input').click(); } });
    ['dragenter', 'dragover'].forEach(ev => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add('border-purple-400', 'bg-purple-500/10'); }));
    ['dragleave', 'dragend'].forEach(ev => dz.addEventListener(ev, () => dz.classList.remove('border-purple-400', 'bg-purple-500/10')));
    dz.addEventListener('drop', handleDrop);
    try { const saved = localStorage.getItem('gcm.docaudit.folder'); if (saved && !$('da-folder-path').value) $('da-folder-path').value = saved; } catch (_) { /* ignore */ }
    if (!$('da-folder-path').value) $('da-folder-path').value = 'C:\\SanDisk\\Compliance_Docs';
  }

  GCM.modules.docaudit = {
    init() {
      wire();
      GCM.palette.register({ label: 'Scan compliance folder…', hint: 'Document Impact Audit', icon: 'file-search-2', keywords: ['document', 'audit', 'scan', 'folder', 'docaudit'], run: () => { GCM.tabs.switchTo('docaudit'); setTimeout(() => { const f = $('da-folder-path'); if (f) { f.focus(); f.select(); } }, 150); } });
      GCM.palette.register({ label: 'Load sample compliance documents', hint: 'Creates 10 demo files and audits them', icon: 'sparkles', keywords: ['sample', 'demo', 'document', 'audit'], run: () => { GCM.tabs.switchTo('docaudit'); setTimeout(loadSamples, 150); } });
      GCM.palette.register({ label: 'Export document revision directive (Excel)', hint: 'Last audit report', icon: 'file-spreadsheet', keywords: ['export', 'excel', 'directive', 'document'], run: exportExcel });
      GCM.bus.on('docaudit:focus', (idx) => { const go = () => focusDoc(Number(idx)); if (state.report) go(); else loadLast().then(go); });
      GCM.bus.on('action:docaudit-scan', scanFolder);
    },
    onFirstShow() { loadLast(); },
    onShow() { GCM.ui.icons(); },
    scan: scanFolder, loadSamples, exportExcel, render,
  };
})();
