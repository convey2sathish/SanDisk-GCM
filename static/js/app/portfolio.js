/* =====================================================================
   GCM Platform 2.0 - portfolio.js
   Product Portfolio tab: KPIs, product cards (risk, readiness, markets,
   alerts, certificates), product detail drawer (readiness table, linked
   alerts, certificates, upcoming dates, ECO impact analyser), certificate
   health table, "Add product" / "Add certificate" forms.
   Data: /api/portfolio, /api/portfolio/<id>, /api/certificates/health,
         POST /api/products, POST /api/certificates, POST /api/eco/analyze
   ===================================================================== */
(function () {
  'use strict';
  const GCM = window.GCM;
  if (!GCM) return;
  const esc = (s) => GCM.ui.esc(s);
  const $ = (id) => document.getElementById(id);

  const GRADE_COLOR = { A: '#10b981', B: '#34d399', C: '#facc15', D: '#fb923c', E: '#f43f5e', F: '#e11d48' };
  const GRADE_BADGE = { A: 'badge badge-success', B: 'badge badge-success', C: 'badge badge-warning', D: 'badge badge-warning', E: 'badge badge-critical', F: 'badge badge-critical' };
  const READY_BAR = (pct) => pct >= 90 ? 'bg-gradient-to-r from-emerald-600 to-emerald-400' : pct >= 60 ? 'bg-gradient-to-r from-sky-600 to-cyan-400' : pct >= 30 ? 'bg-gradient-to-r from-amber-600 to-yellow-400' : 'bg-gradient-to-r from-rose-700 to-rose-500';
  const READINESS_BADGE = { success: 'badge badge-success', info: 'badge badge-info', warning: 'badge badge-warning', danger: 'badge badge-critical' };
  const CERT_BADGE = { Valid: 'badge badge-success', 'Expiring Soon': 'badge badge-warning', Critical: 'badge badge-critical', Expired: 'badge badge-critical' };
  const TIER_CLS = { Low: 'badge badge-success', 'Low-Medium': 'badge badge-info', Medium: 'badge badge-warning', High: 'badge badge-critical' };
  const PILLAR_PILL = { Safety: 'badge badge-critical', EMC: 'badge badge-info', Environmental: 'badge badge-success', Cyber: 'badge badge-indigo', All: 'badge badge-purple' };
  const PRESET_MARKETS = ['US', 'CA', 'MX', 'BR', 'GB', 'DE', 'FR', 'IT', 'ES', 'JP', 'KR', 'TW', 'CN', 'IN', 'SG', 'AU', 'NZ', 'SA', 'AE', 'ZA'];

  const state = {
    loaded: false, loading: false, portfolio: null, health: null, search: '', category: '', sort: 'risk', certFilter: '',
    detail: null, detailTab: 'readiness', ecoMarkets: new Set(), pendingFocus: null, ecoLast: null,
  };
  let refreshTimer = null;

  /* ------------------------------------------------------------------ data */
  async function loadAll() {
    if (state.loading) return;
    state.loading = true;
    try {
      const [pf, health] = await Promise.all([GCM.api.get('/api/portfolio'), GCM.api.get('/api/certificates/health')]);
      state.portfolio = pf; state.health = health; state.loaded = true;
      renderKpis(); renderCategoryFilter(); renderGrid(); renderCerts();
      if (state.pendingFocus) { const id = state.pendingFocus; state.pendingFocus = null; openDetail(id); }
    } catch (e) {
      console.error('[portfolio] load failed', e);
      $('pf-grid').innerHTML = GCM.ui.empty(`Could not load the portfolio: ${e.message}`, 'wifi-off');
      GCM.ui.toast('Portfolio unavailable', e.message, 'error');
    } finally { state.loading = false; GCM.ui.icons(); }
  }
  function scheduleRefresh() { if (!state.loaded) return; clearTimeout(refreshTimer); refreshTimer = setTimeout(loadAll, 450); }

  function products() { return (state.portfolio && state.portfolio.products) || []; }
  function productById(id) { return products().find(p => p.id === id); }
  function countryName(code) { return ((GCM.state.countries || {})[code] || {}).name || code; }

  /* ------------------------------------------------------------------ header */
  function renderKpis() {
    const k = (state.portfolio && state.portfolio.kpis) || {}; const h = state.health || {};
    const tiles = [
      { label: 'Products', value: k.products || 0, sub: `${GCM.state.categories.length || 11} categories available`, glow: 'rgba(16,185,129,.25)', icon: 'hard-drive' },
      { label: 'Certificates', value: k.certificates || 0, sub: `${h.valid || 0} valid · ${h.permanent || 0} permanent`, glow: 'rgba(56,189,248,.22)', icon: 'file-badge' },
      { label: 'Expiring ≤ 90 days', value: (k.expiring_90 || 0) + (k.expired || 0), sub: `${k.expired || 0} already expired · ${h.expiring_30 || 0} within 30 d`, glow: 'rgba(245,158,11,.28)', icon: 'alarm-clock', tone: (k.expired || 0) ? 'text-rose-300' : (k.expiring_90 || 0) ? 'text-amber-300' : 'text-white' },
      { label: 'Average readiness', value: `${k.avg_readiness || 0}%`, sub: `portfolio risk index ${k.compliance_risk_index ?? '—'} (grade ${k.grade || '—'})`, glow: 'rgba(99,102,241,.25)', icon: 'gauge' },
    ];
    $('pf-kpis').innerHTML = tiles.map(t => `<div class="kpi" style="--kpi-glow:${t.glow}"><div class="flex items-center justify-between"><div class="kpi-label">${esc(t.label)}</div><i data-lucide="${t.icon}" class="w-4 h-4 text-slate-500"></i></div><div class="kpi-value ${t.tone || ''}">${esc(t.value)}</div><div class="kpi-sub">${esc(t.sub)}</div></div>`).join('');
  }

  function renderCategoryFilter() {
    const sel = $('pf-category'); if (!sel) return;
    const cats = GCM.state.categories || [];
    sel.innerHTML = '<option value="">All categories</option>' + cats.map(c => `<option value="${esc(c.id)}" ${state.category === c.id ? 'selected' : ''}>${esc(c.name)}</option>`).join('');
  }

  /* ------------------------------------------------------------------ product cards */
  function filteredProducts() {
    const q = state.search.toLowerCase();
    let list = products().filter(p => (!state.category || p.category_id === state.category) &&
      (!q || `${p.name} ${p.sku} ${p.category_name} ${p.controller} ${p.nand}`.toLowerCase().includes(q)));
    const sorters = {
      risk: (a, b) => b.risk_score - a.risk_score || a.name.localeCompare(b.name),
      readiness: (a, b) => a.readiness_pct - b.readiness_pct || b.risk_score - a.risk_score,
      deadline: (a, b) => (a.days_to_next_deadline ?? 1e9) - (b.days_to_next_deadline ?? 1e9),
      name: (a, b) => a.name.localeCompare(b.name),
    };
    return list.sort(sorters[state.sort] || sorters.risk);
  }

  function productCard(p) {
    const g = p.grade || 'A'; const cat = p.category || {};
    const flags = (p.target_markets || []).map(c => `<button type="button" class="text-base leading-none hover:scale-125 transition-transform" data-pf="factsheet" data-arg="${esc(c)}" title="${esc(countryName(c))} – open fact sheet">${GCM.ui.flag(c)}</button>`).join('');
    const nextDl = p.next_deadline ? `<span class="pill gap-1 ${GCM.ui.deadlineTone(p.next_deadline) === 'critical' ? '!text-rose-300 !border-rose-800' : GCM.ui.deadlineTone(p.next_deadline) === 'warning' ? '!text-amber-300 !border-amber-800' : ''}" title="${esc(p.next_deadline_label || 'Next deadline')}"><i data-lucide="calendar-clock" class="w-3 h-3"></i>${esc(GCM.ui.relDays(p.next_deadline))}</span>` : '';
    const certTone = p.cert_health === 'Expired' ? 'badge badge-critical' : (p.cert_health === 'Critical' || p.cert_health === 'Expiring Soon') ? 'badge badge-warning' : p.cert_health === 'Valid' ? 'badge badge-success' : 'badge badge-neutral';
    return `<article class="card !p-0 overflow-hidden flex flex-col hover:border-emerald-700/60 transition-colors relative" data-product="${esc(p.id)}">
      <div class="absolute top-0 left-0 right-0 h-1" style="background:${GRADE_COLOR[g]}"></div>
      <div class="p-4 flex items-start gap-3">
        <div class="w-11 h-11 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0"><i data-lucide="${esc(cat.icon || 'hard-drive')}" class="w-5 h-5 text-emerald-400"></i></div>
        <div class="min-w-0 flex-1">
          <button type="button" class="text-sm font-bold text-white hover:text-emerald-300 text-left leading-snug" data-pf="detail" data-arg="${esc(p.id)}">${esc(p.name)}</button>
          <div class="text-[11px] text-slate-400 mono truncate mt-0.5">${esc(p.sku)} · ${esc(p.hw_revision || '')}</div>
          <div class="flex items-center gap-1.5 flex-wrap mt-1.5"><span class="pill">${esc(cat.name || p.category_name)}</span><span class="${TIER_CLS[cat.risk_tier] || 'badge badge-neutral'} !normal-case !tracking-normal">${esc(cat.risk_tier || 'Medium')} tier</span></div>
        </div>
        <div class="text-right shrink-0">
          <div class="text-2xl font-black tabular-nums leading-none" style="color:${GRADE_COLOR[g]}" title="Risk score (0–100, higher = riskier)">${esc(Math.round(p.risk_score))}</div>
          <span class="${GRADE_BADGE[g]} mt-1">Risk ${g}</span>
        </div>
      </div>
      <div class="px-4 pb-3 space-y-3 flex-1">
        <div>
          <div class="flex items-center justify-between text-[10px] text-slate-400 mb-1"><span class="uppercase tracking-wider font-bold">Market readiness</span><span class="mono text-white">${esc(p.ready_markets)}/${esc((p.target_markets || []).length)} · ${esc(p.readiness_pct)}%</span></div>
          <div class="progress"><div class="progress-bar ${READY_BAR(p.readiness_pct)}" style="width:${Math.max(2, p.readiness_pct)}%"></div></div>
        </div>
        <div class="flex flex-wrap gap-1">${flags || '<span class="text-slate-500 text-[11px]">No target markets defined</span>'}</div>
        <div class="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
          <div class="flex items-center gap-1.5 truncate" title="${esc(p.power_source || cat.power_type || '')}"><i data-lucide="zap" class="w-3.5 h-3.5 text-amber-400 shrink-0"></i><span class="truncate">${esc((p.power_source || cat.power_type || '—').split('(')[0].trim())}</span></div>
          <div class="flex items-center gap-1.5 truncate" title="${esc(p.controller || '')}"><i data-lucide="cpu" class="w-3.5 h-3.5 text-sky-400 shrink-0"></i><span class="truncate">${esc(p.controller || '—')}</span></div>
        </div>
      </div>
      <div class="px-4 py-3 border-t border-slate-800 bg-slate-950/40 flex items-center gap-1.5 flex-wrap">
        <button type="button" class="pill gap-1 hover:border-rose-500 ${p.open_alerts ? '!text-slate-100' : ''}" data-pf="alerts" data-arg="${esc(p.id)}" title="Show this product's alerts"><i data-lucide="bell" class="w-3 h-3"></i>${esc(p.open_alerts)} open</button>
        ${p.critical_alerts ? `<button type="button" class="badge badge-critical hover:brightness-125" data-pf="alerts" data-arg="${esc(p.id)}">${esc(p.critical_alerts)} critical</button>` : ''}
        <span class="${certTone} !normal-case !tracking-normal" title="Certificate health (recomputed from expiry dates)"><i data-lucide="file-badge" class="w-3 h-3"></i>${esc(p.certificates_count)} cert${p.certificates_count === 1 ? '' : 's'}${p.certificates_count ? ` · ${esc(p.cert_health)}` : ''}</span>
        ${nextDl}
        <span class="flex-1"></span>
        <button type="button" class="btn btn-secondary btn-sm" data-pf="detail" data-arg="${esc(p.id)}">Details<i data-lucide="arrow-right" class="w-3.5 h-3.5"></i></button>
      </div>
    </article>`;
  }

  function renderGrid() {
    const list = filteredProducts();
    $('pf-count').textContent = `${list.length} of ${products().length} products`;
    $('pf-grid').innerHTML = list.length ? list.map(productCard).join('') : `<div class="md:col-span-2 xl:col-span-3">${GCM.ui.empty(products().length ? 'No products match your search.' : 'No products yet. Add your first product to see readiness and risk.', 'hard-drive')}</div>`;
    GCM.ui.icons();
  }

  /* ------------------------------------------------------------------ certificates table */
  function certExpiryCell(c) {
    if (c.days_to_expiry === null || c.days_to_expiry === undefined) return `<span class="text-slate-300">${esc(c.expiry_date || 'Permanent')}</span><div class="text-[10px] text-slate-500">no expiry</div>`;
    const n = c.days_to_expiry; const cls = n < 0 ? 'text-rose-300' : n <= 30 ? 'text-rose-300' : n <= 90 ? 'text-amber-300' : 'text-slate-300';
    return `<span class="${cls}">${esc(GCM.ui.fmtDate(c.expiry_date))}</span><div class="text-[10px] ${cls}">${n < 0 ? `expired ${-n} d ago` : n === 0 ? 'expires today' : `in ${n} d`}</div>`;
  }

  function renderCerts() {
    const h = state.health || {}; const all = h.certificates || [];
    const counts = { all: all.length };
    all.forEach(c => { counts[c.status] = (counts[c.status] || 0) + 1; });
    document.querySelectorAll('#pf-cert-filters [data-count]').forEach(el => { el.textContent = counts[el.dataset.count] || 0; });
    document.querySelectorAll('#pf-cert-filters [data-pf="cert-filter"]').forEach(b => b.classList.toggle('ring-2', b.dataset.arg === state.certFilter));
    document.querySelectorAll('#pf-cert-filters [data-pf="cert-filter"]').forEach(b => b.classList.toggle('ring-white/60', b.dataset.arg === state.certFilter));
    const list = state.certFilter ? all.filter(c => c.status === state.certFilter) : all;
    $('pf-cert-tbody').innerHTML = list.length ? list.map(c => {
      const prod = productById(c.product_id);
      const renew = (c.status !== 'Valid') ? `<button type="button" class="btn btn-secondary btn-sm" data-pf="renew" data-arg="${esc(c.id)}" title="Create a renewal action for this certificate"><i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>Renewal action</button>` : '';
      const mismatch = c.declared_status && c.declared_status !== c.status ? `<div class="text-[10px] text-slate-500 mt-0.5" title="Status as declared in the record">declared: ${esc(c.declared_status)}</div>` : '';
      return `<tr>
        <td><span class="${CERT_BADGE[c.status] || 'badge badge-neutral'}">${esc(c.status)}</span>${mismatch}</td>
        <td><div class="mono text-white">${esc(c.cert_no)}</div><div class="text-[10px] text-slate-500">${esc(c.document_type || '')}</div></td>
        <td><div class="text-slate-200">${esc(c.scheme)}</div><div class="text-[10px] text-slate-500">${esc(c.standard || '')}${c.issuing_body ? ` · ${esc(c.issuing_body)}` : ''}</div></td>
        <td>${prod ? `<button type="button" class="text-sky-300 hover:text-sky-200 text-left" data-pf="detail" data-arg="${esc(prod.id)}">${esc(prod.name)}</button><div class="text-[10px] text-slate-500 mono">${esc(prod.sku)}</div>` : `<span class="text-slate-400">${esc(c.product_name || c.product_id || '—')}</span>`}</td>
        <td class="text-slate-300">${esc(c.country_coverage || '—')}</td>
        <td class="text-slate-400 whitespace-nowrap">${esc(GCM.ui.fmtDate(c.issue_date))}</td>
        <td class="whitespace-nowrap">${certExpiryCell(c)}</td>
        <td class="text-right whitespace-nowrap">${renew}</td>
      </tr>`;
    }).join('') : `<tr><td colspan="8">${GCM.ui.empty(state.certFilter ? `No certificates with status "${state.certFilter}".` : 'No certificates recorded yet.', 'file-badge')}</td></tr>`;
    GCM.ui.icons();
  }

  function renewalAction(cert) {
    const prod = productById(cert.product_id);
    const n = cert.days_to_expiry;
    const due = n !== null && n !== undefined && n > 14 ? new Date(Date.now() + Math.max(7, n - 30) * 86400000).toISOString().slice(0, 10) : new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
    GCM.actions.createFor('certificate', cert.id, {
      title: `Renew ${cert.scheme} ${cert.cert_no}${prod ? ` – ${prod.name}` : ''}`,
      priority: cert.status === 'Expired' || cert.status === 'Critical' ? 'Critical' : 'High',
      due_date: due,
      notes: `${cert.status === 'Expired' ? 'Expired on' : 'Expires on'} ${cert.expiry_date}. Coverage: ${cert.country_coverage}. Issuing body: ${cert.issuing_body || 'n/a'}. Standard: ${cert.standard || 'n/a'}.`,
    });
  }

  /* ------------------------------------------------------------------ product detail drawer */
  async function openDetail(id, tab) {
    if (!state.loaded) { state.pendingFocus = id; return; }
    const p = productById(id);
    if (!p) { GCM.ui.toast('Product not found', id, 'warning'); return; }
    state.detailTab = tab || 'readiness';
    state.ecoLast = null;
    $('pd-name').textContent = p.name;
    $('pd-sub').textContent = `${p.sku} · ${p.hw_revision || ''} · ${p.category_name} · ${p.compliance_status || ''}`;
    $('pd-icon-wrap').innerHTML = `<i data-lucide="${esc((p.category || {}).icon || 'hard-drive')}" class="w-5 h-5 text-emerald-400"></i>`;
    const g = p.grade || 'A';
    $('pd-risk').innerHTML = `<div class="text-xl font-black tabular-nums leading-none" style="color:${GRADE_COLOR[g]}">${esc(Math.round(p.risk_score))}</div><div class="text-[10px] text-slate-400">risk · grade ${g}</div>`;
    $('pd-foot').textContent = `Readiness ${p.readiness_pct}% (${p.ready_markets}/${(p.target_markets || []).length} markets) · ${p.open_alerts} open alerts · ${p.certificates_count} certificates · controller ${p.controller || '—'} · NAND ${p.nand || '—'}`;
    const modal = $('modal-product-detail'); modal.dataset.productId = id;
    document.querySelectorAll('[data-pd-panel]').forEach(el => { if (el.dataset.pdPanel !== 'eco') el.innerHTML = GCM.ui.skeleton(3); });
    selectDetailTab(state.detailTab);
    setupEco(p);
    GCM.ui.openModal('modal-product-detail');
    try {
      const d = await GCM.api.get(`/api/portfolio/${encodeURIComponent(id)}`);
      if (modal.dataset.productId !== id) return;
      state.detail = d;
      renderDetail(d);
    } catch (e) {
      document.querySelector('[data-pd-panel="readiness"]').innerHTML = GCM.ui.empty(`Could not load details: ${e.message}`, 'wifi-off');
    }
    GCM.ui.icons();
  }

  function selectDetailTab(tab) {
    state.detailTab = tab;
    document.querySelectorAll('#pd-tabs [data-pf="pd-tab"]').forEach(b => { const on = b.dataset.arg === tab; b.classList.toggle('active', on); b.setAttribute('aria-selected', String(on)); });
    document.querySelectorAll('[data-pd-panel]').forEach(el => el.classList.toggle('hidden', el.dataset.pdPanel !== tab));
    GCM.ui.icons();
  }

  function renderDetail(d) {
    const p = d.product; const readiness = p.readiness || [];
    const cnt = (k, v) => { const el = document.querySelector(`[data-pd-count="${k}"]`); if (el) el.textContent = v; };
    cnt('readiness', readiness.length); cnt('alerts', d.alerts.length); cnt('certs', (p.certificates || []).length); cnt('horizon', d.events.filter(e => e.bucket !== 'history').length);

    // readiness
    const ready = readiness.filter(r => r.badge === 'success' || r.badge === 'info').length;
    const byBadge = { danger: 0, warning: 0, info: 0, success: 0 }; readiness.forEach(r => { byBadge[r.badge] = (byBadge[r.badge] || 0) + 1; });
    document.querySelector('[data-pd-panel="readiness"]').innerHTML = `
      <div class="flex flex-col md:flex-row md:items-center gap-3 mb-3">
        <div class="flex-1"><div class="flex items-center justify-between text-[10px] text-slate-400 mb-1"><span class="uppercase tracking-wider font-bold">Overall readiness</span><span class="mono text-white">${ready}/${readiness.length} markets · ${esc(p.readiness_pct)}%</span></div><div class="progress !h-2"><div class="progress-bar ${READY_BAR(p.readiness_pct)}" style="width:${Math.max(2, p.readiness_pct)}%"></div></div></div>
        <div class="flex gap-1.5 flex-wrap"><span class="badge badge-success">${byBadge.success} certified</span><span class="badge badge-info">${byBadge.info} SDoC</span><span class="badge badge-warning">${byBadge.warning} filing / renewal</span><span class="badge badge-critical">${byBadge.danger} blocked</span></div>
      </div>
      ${readiness.length ? `<div class="table-wrap max-h-[440px]"><table class="table"><thead><tr><th>Market</th><th>Requirement</th><th>Status</th><th>Action needed</th><th>Authority</th><th>Marks</th></tr></thead><tbody>
        ${readiness.slice().sort((a, b) => ({ danger: 0, warning: 1, info: 2, success: 3 }[a.badge] - { danger: 0, warning: 1, info: 2, success: 3 }[b.badge]) || a.country_name.localeCompare(b.country_name)).map(r => `<tr>
          <td class="whitespace-nowrap"><button type="button" class="flex items-center gap-2 text-white hover:text-sky-300" data-pf="factsheet" data-arg="${esc(r.country_code)}" title="Open country fact sheet"><span class="text-base leading-none">${GCM.ui.flag(r.country_code)}</span><span class="font-semibold">${esc(r.country_name)}</span></button><div class="text-[10px] text-slate-500 pl-7">${esc(r.region || '')}${r.in_country_testing ? ' · in-country testing' : ''}${r.local_rep_required ? ' · local rep' : ''}</div></td>
          <td class="text-slate-300 max-w-[180px]">${esc(r.requirement_type)}${r.lead_time_weeks ? `<div class="text-[10px] text-slate-500">lead time ~${esc(r.lead_time_weeks)} wk</div>` : ''}</td>
          <td><span class="${READINESS_BADGE[r.badge] || 'badge badge-neutral'} !normal-case !tracking-normal">${esc(r.status)}</span></td>
          <td class="text-slate-300 max-w-[320px] leading-relaxed">${esc(r.action_needed)}</td>
          <td class="text-slate-400 max-w-[160px]">${esc(r.authority || '—')}</td>
          <td class="text-slate-400">${(r.required_marks || []).map(m => `<span class="pill mr-1 mb-1">${esc(m)}</span>`).join('')}</td>
        </tr>`).join('')}</tbody></table></div>` : GCM.ui.empty('This product has no target markets yet.', 'globe-2')}`;

    // alerts
    document.querySelector('[data-pd-panel="alerts"]').innerHTML = d.alerts.length ? `<div class="divide-y divide-slate-800/80">${d.alerts.map(a => `
      <div class="py-2.5 flex items-start gap-3">
        <div class="shrink-0 w-10 text-center"><div class="text-base font-black tabular-nums text-slate-200" title="Contribution to this product's raw risk">+${esc(a.score)}</div><div class="text-[9px] uppercase text-slate-500">score</div></div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap"><span class="${GCM.ui.severityClass(a.severity)}">${esc(a.severity)}</span><span class="${PILLAR_PILL[a.pillar] || 'badge badge-neutral'} !normal-case !tracking-normal">${esc(a.pillar)}</span><button type="button" class="text-xs font-semibold text-white hover:text-sky-300 text-left" data-action="deeplink-alert" data-arg="${esc(a.id)}">${esc(a.title)}</button></div>
          <div class="text-[11px] text-slate-400 mt-1">${esc(a.country || '')}${a.standard ? ` · ${esc(a.standard)}` : ''} · ${a.effective_date && GCM.ui.daysUntil(a.effective_date) !== null ? `${esc(GCM.ui.fmtDate(a.effective_date))} (${esc(GCM.ui.relDays(a.effective_date))})` : esc(a.effective_date || 'no date')} · triage: <span class="text-slate-200">${esc(a.triage_status)}</span></div>
          ${a.action_required ? `<div class="text-[11px] text-slate-500 mt-0.5 line-clamp-2">${esc(a.action_required)}</div>` : ''}
        </div>
        <button type="button" class="btn btn-ghost btn-sm shrink-0" data-pf="alert-action" data-arg="${esc(a.id)}" data-title="${esc(a.title)}" data-sev="${esc(a.severity)}" data-due="${esc(a.effective_date && GCM.ui.daysUntil(a.effective_date) > 0 ? a.effective_date : '')}"><i data-lucide="plus-square" class="w-3.5 h-3.5"></i>Action</button>
      </div>`).join('')}</div>` : GCM.ui.empty('No open regulatory alerts touch this product.', 'bell-off');

    // certs
    const certs = p.certificates || [];
    document.querySelector('[data-pd-panel="certs"]').innerHTML = `<div class="flex justify-end mb-2"><button type="button" class="btn btn-secondary btn-sm" data-pf="open-add-cert" data-arg="${esc(p.id)}"><i data-lucide="file-plus-2" class="w-3.5 h-3.5"></i>Add certificate for this product</button></div>` + (certs.length ? `<div class="table-wrap"><table class="table"><thead><tr><th>Status</th><th>Certificate</th><th>Scheme &amp; standard</th><th>Coverage</th><th>Expires</th><th class="text-right"></th></tr></thead><tbody>${certs.map(c => `<tr>
        <td><span class="${CERT_BADGE[c.status] || 'badge badge-neutral'}">${esc(c.status)}</span></td>
        <td><div class="mono text-white">${esc(c.cert_no)}</div><div class="text-[10px] text-slate-500">${esc(c.document_type || '')}</div></td>
        <td><div class="text-slate-200">${esc(c.scheme)}</div><div class="text-[10px] text-slate-500">${esc(c.standard || '')}${c.issuing_body ? ` · ${esc(c.issuing_body)}` : ''}</div></td>
        <td class="text-slate-300">${esc(c.country_coverage || '—')}</td>
        <td class="whitespace-nowrap">${certExpiryCell(c)}</td>
        <td class="text-right whitespace-nowrap">${c.status !== 'Valid' ? `<button type="button" class="btn btn-secondary btn-sm" data-pf="renew" data-arg="${esc(c.id)}"><i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>Renewal action</button>` : ''}</td>
      </tr>`).join('')}</tbody></table></div>` : GCM.ui.empty('No certificates recorded for this product. Markets will show as SDoC, filing required or blocked until one is added.', 'file-badge'));

    // horizon (upcoming dates)
    const events = d.events.filter(e => e.bucket !== 'history');
    const toneDot = { critical: '#f43f5e', warning: '#f59e0b', info: '#38bdf8', success: '#10b981' };
    const typeLabel = { alert_deadline: 'Enforcement deadline', milestone: 'Milestone', cert_expiry: 'Certificate expiry', action_due: 'Action due', surveillance: 'Surveillance' };
    document.querySelector('[data-pd-panel="horizon"]').innerHTML = events.length ? `<div class="timeline">${events.map(e => `
      <div class="timeline-item" style="--dot:${toneDot[e.tone] || '#38bdf8'}">
        <div class="flex items-start gap-3">
          <div class="w-24 shrink-0"><div class="text-white font-semibold">${esc(GCM.ui.fmtDate(e.date))}</div><div class="text-[10px] ${e.days_remaining < 0 ? 'text-rose-300' : 'text-slate-500'}">${e.days_remaining < 0 ? `${-e.days_remaining} d overdue` : e.days_remaining === 0 ? 'today' : `in ${e.days_remaining} d`}</div></div>
          <div class="min-w-0 flex-1"><div class="flex items-center gap-2 flex-wrap"><span class="pill">${esc(typeLabel[e.type] || e.type)}</span>${e.ref_type === 'alert' ? `<button type="button" class="text-white font-semibold hover:text-sky-300 text-left" data-action="deeplink-alert" data-arg="${esc(e.ref_id)}">${esc(e.title)}</button>` : `<span class="text-white font-semibold">${esc(e.title)}</span>`}</div>${e.subtitle ? `<div class="text-[11px] text-slate-400 mt-0.5">${esc(e.subtitle)}</div>` : ''}</div>
        </div>
      </div>`).join('')}</div><div class="text-[10px] text-slate-500 mt-2">See the Horizon &amp; Risk tab for the full portfolio timeline. <button type="button" class="text-sky-300 hover:underline" data-pf="horizon-filter" data-arg="${esc(p.id)}">Open horizon filtered to this product</button></div>` : GCM.ui.empty('No upcoming dated items for this product.', 'calendar-check');
    GCM.ui.icons();
  }

  /* ------------------------------------------------------------------ ECO analyser */
  function setupEco(p) {
    state.ecoMarkets = new Set(p.target_markets || []);
    renderEcoMarkets(p);
    $('eco-description').value = '';
    $('eco-component').value = (p.category_id === 'external_ssd_powered') ? 'power_adapter' : (p.category_id === 'enterprise_ssd' ? 'firmware_crypto' : 'controller_asic');
    $('eco-results').innerHTML = '<div class="empty-state"><i data-lucide="git-branch" class="w-8 h-8 text-slate-600 mx-auto mb-2"></i><div>Pick the component that changes and run the analysis to see the regulatory impact per market.</div></div>';
  }
  function renderEcoMarkets(p) {
    const codes = (p.target_markets || []).slice();
    ['US', 'DE', 'GB', 'JP', 'KR', 'TW', 'CN', 'IN'].forEach(c => { if (!codes.includes(c)) codes.push(c); });
    $('eco-markets').innerHTML = codes.map(c => { const on = state.ecoMarkets.has(c); return `<button type="button" class="pill gap-1 ${on ? '!bg-indigo-900/60 !border-indigo-500 !text-white' : 'opacity-60'}" data-pf="eco-market" data-arg="${esc(c)}" aria-pressed="${on}" title="${esc(countryName(c))}${(p.target_markets || []).includes(c) ? ' (target market)' : ''}">${GCM.ui.flag(c)} ${esc(c)}</button>`; }).join('');
  }
  async function runEco(btn) {
    const p = productById($('modal-product-detail').dataset.productId); if (!p) return;
    const targets = [...state.ecoMarkets];
    if (!targets.length) { GCM.ui.toast('Pick at least one market', 'Select the markets the changed product ships to.', 'warning'); return; }
    const body = { category_id: p.category_id, component_type: $('eco-component').value, change_description: $('eco-description').value.trim() || 'Component substitution', target_countries: targets };
    GCM.ui.setLoading(btn, true, 'Analysing…');
    try {
      const r = await GCM.api.post('/api/eco/analyze', body);
      state.ecoLast = r; renderEcoResults(r, p);
    } catch (e) { $('eco-results').innerHTML = GCM.ui.empty(`Analysis failed: ${e.message}`, 'x-circle'); }
    finally { GCM.ui.setLoading(btn, false); GCM.ui.icons(); }
  }
  function levelTone(level) {
    const l = String(level || '').toLowerCase();
    if (l.startsWith('critical')) return { badge: 'badge badge-critical', row: 'bg-rose-950/20', rank: 0 };
    if (l.startsWith('moderate')) return { badge: 'badge badge-warning', row: 'bg-amber-950/10', rank: 1 };
    if (l.startsWith('minor')) return { badge: 'badge badge-info', row: '', rank: 2 };
    if (l.startsWith('not applicable')) return { badge: 'badge badge-neutral', row: 'opacity-70', rank: 4 };
    return { badge: 'badge badge-success', row: '', rank: 3 };
  }
  function renderEcoResults(r, p) {
    const sev = String(r.overall_severity || 'Minor');
    const banner = sev === 'Critical' ? 'border-rose-500/60 bg-rose-950/40 text-rose-100' : sev === 'Moderate' ? 'border-amber-500/60 bg-amber-950/40 text-amber-100' : 'border-emerald-500/60 bg-emerald-950/40 text-emerald-100';
    const icon = sev === 'Critical' ? 'siren' : sev === 'Moderate' ? 'alert-triangle' : 'check-circle-2';
    const results = (r.results || []).slice().sort((a, b) => levelTone(a.action_level).rank - levelTone(b.action_level).rank || a.country_name.localeCompare(b.country_name));
    const counts = results.reduce((acc, x) => { const k = String(x.action_level).split(':')[0]; acc[k] = (acc[k] || 0) + 1; return acc; }, {});
    const compLabel = $('eco-component').selectedOptions[0]?.textContent || r.component_type;
    $('eco-results').innerHTML = `
      <div class="rounded-xl border p-4 flex items-start gap-3 ${banner}">
        <i data-lucide="${icon}" class="w-6 h-6 shrink-0"></i>
        <div class="min-w-0 flex-1">
          <div class="text-sm font-bold">Overall impact: ${esc(sev)}</div>
          <div class="text-[11px] opacity-90 mt-0.5">${esc(compLabel)} · ${esc(r.change_description || '')} · ${esc(r.countries_analyzed)} market${r.countries_analyzed === 1 ? '' : 's'} evaluated for ${esc(r.category_name || p.category_name)}</div>
          <div class="flex flex-wrap gap-1.5 mt-2">${Object.entries(counts).map(([k, v]) => `<span class="${levelTone(k).badge}">${esc(v)} ${esc(k)}</span>`).join('')}</div>
        </div>
        <button type="button" class="btn btn-secondary btn-sm shrink-0" data-pf="eco-action"><i data-lucide="plus-square" class="w-3.5 h-3.5"></i>Create ECO action</button>
      </div>
      <div class="table-wrap mt-3 max-h-[420px]"><table class="table"><thead><tr><th>Market</th><th>Action level</th><th>What is required</th><th>Authority to notify</th><th>Lead time</th></tr></thead><tbody>
        ${results.map(x => { const t = levelTone(x.action_level); return `<tr class="${t.row}">
          <td class="whitespace-nowrap"><button type="button" class="flex items-center gap-2 text-white hover:text-sky-300" data-pf="factsheet" data-arg="${esc(x.country_code)}"><span class="text-base leading-none">${GCM.ui.flag(x.country_code)}</span><span class="font-semibold">${esc(x.country_name)}</span></button><div class="text-[10px] text-slate-500 pl-7">${esc(x.region || '')}</div></td>
          <td><span class="${t.badge} !normal-case !tracking-normal !whitespace-normal">${esc(x.action_level)}</span></td>
          <td class="text-slate-300 max-w-[360px] leading-relaxed">${esc(x.details)}</td>
          <td class="text-slate-400 max-w-[180px]">${esc(x.authority_to_notify || '—')}</td>
          <td class="text-slate-300 whitespace-nowrap">${esc(x.lead_time || '—')}</td>
        </tr>`; }).join('')}</tbody></table></div>`;
    GCM.ui.icons();
  }

  /* ------------------------------------------------------------------ forms */
  function fillAddProductForm() {
    const form = $('pf-add-product-form');
    const sel = form.querySelector('[name=category_id]');
    sel.innerHTML = (GCM.state.categories || []).map(c => `<option value="${esc(c.id)}" ${c.id === (GCM.state.settings.default_category || 'external_ssd_powered') ? 'selected' : ''}>${esc(c.name)} · ${esc(c.risk_tier)} tier</option>`).join('');
    const input = form.querySelector('[name=target_markets]');
    const renderPresets = () => {
      const chosen = new Set(parseMarkets(input.value));
      $('pf-market-presets').innerHTML = PRESET_MARKETS.map(c => `<button type="button" class="pill gap-1 ${chosen.has(c) ? '!bg-emerald-900/60 !border-emerald-500 !text-white' : 'opacity-60'}" data-pf="preset-market" data-arg="${esc(c)}" title="${esc(countryName(c))}">${GCM.ui.flag(c)} ${esc(c)}</button>`).join('');
    };
    input.oninput = renderPresets; renderPresets();
    $('pf-add-product-error').classList.add('hidden');
  }
  function parseMarkets(text) { return [...new Set(String(text || '').toUpperCase().split(/[^A-Z]+/).filter(x => x.length === 2))]; }
  async function submitAddProduct(e) {
    e.preventDefault();
    const form = $('pf-add-product-form'); const err = $('pf-add-product-error');
    const data = Object.fromEntries(new FormData(form).entries());
    const markets = parseMarkets(data.target_markets).filter(c => GCM.state.countries[c]);
    if (!data.name.trim()) { err.textContent = 'Give the product a name.'; err.classList.remove('hidden'); return; }
    if (!markets.length) { err.textContent = 'Enter at least one valid ISO country code (e.g. US, DE, JP).'; err.classList.remove('hidden'); return; }
    const btn = form.querySelector('[type=submit]'); GCM.ui.setLoading(btn, true, 'Creating…');
    try {
      const r = await GCM.api.post('/api/products', { ...data, target_markets: markets });
      GCM.ui.closeModal('modal-add-product'); form.reset();
      GCM.ui.toast('Product created', `${r.product.name} · ${markets.length} target markets`);
      GCM.bus.emit('products:changed', r.product);
      await loadAll(); openDetail(r.product.id);
    } catch (ex) { err.textContent = ex.message; err.classList.remove('hidden'); }
    finally { GCM.ui.setLoading(btn, false); }
  }
  function fillAddCertForm(productId) {
    const form = $('pf-add-cert-form');
    const sel = form.querySelector('[name=product_id]');
    sel.innerHTML = products().map(p => `<option value="${esc(p.id)}" ${p.id === productId ? 'selected' : ''}>${esc(p.name)} · ${esc(p.sku)}</option>`).join('');
    form.querySelector('[name=issue_date]').value = new Date().toISOString().slice(0, 10);
    $('pf-add-cert-error').classList.add('hidden');
  }
  async function submitAddCert(e) {
    e.preventDefault();
    const form = $('pf-add-cert-form'); const err = $('pf-add-cert-error');
    const data = Object.fromEntries(new FormData(form).entries());
    if (!data.cert_no.trim()) { err.textContent = 'A certificate number is required.'; err.classList.remove('hidden'); return; }
    if (!data.product_id) { err.textContent = 'Pick the product this certificate belongs to.'; err.classList.remove('hidden'); return; }
    if (data.expiry_date && data.issue_date && data.expiry_date < data.issue_date) { err.textContent = 'Expiry date must be after the issue date.'; err.classList.remove('hidden'); return; }
    if (!data.expiry_date) data.expiry_date = 'Permanent';
    const btn = form.querySelector('[type=submit]'); GCM.ui.setLoading(btn, true, 'Saving…');
    try {
      const r = await GCM.api.post('/api/certificates', data);
      GCM.ui.closeModal('modal-add-cert'); form.reset();
      GCM.ui.toast('Certificate saved', `${r.certificate.scheme} · ${r.certificate.cert_no}`);
      GCM.bus.emit('products:changed', { certificate: r.certificate });
      await loadAll();
      if (!$('modal-product-detail').classList.contains('hidden')) openDetail(r.certificate.product_id, 'certs');
    } catch (ex) { err.textContent = ex.message; err.classList.remove('hidden'); }
    finally { GCM.ui.setLoading(btn, false); }
  }

  /* ------------------------------------------------------------------ interaction */
  function showAlertsFor(productId) {
    GCM.tabs.switchTo('alerts');
    setTimeout(() => GCM.bus.emit('alerts:filter', { product_id: productId }), 120);
  }

  function onClick(e) {
    const el = e.target.closest('[data-pf]'); if (!el) return;
    const kind = el.dataset.pf; const arg = el.dataset.arg;
    switch (kind) {
      case 'detail': openDetail(arg); break;
      case 'factsheet': GCM.bus.emit('country:factsheet', arg); break;
      case 'alerts': showAlertsFor(arg); break;
      case 'pd-alerts': showAlertsFor($('modal-product-detail').dataset.productId); break;
      case 'pd-action': { const p = productById($('modal-product-detail').dataset.productId); if (p) GCM.actions.createFor('product', p.id, { title: `${p.name}: `, priority: p.critical_alerts ? 'Critical' : 'High', notes: `SKU ${p.sku} · readiness ${p.readiness_pct}% · risk ${Math.round(p.risk_score)} (grade ${p.grade})` }); break; }
      case 'pd-tab': selectDetailTab(arg); break;
      case 'renew': { const c = ((state.health || {}).certificates || []).find(x => x.id === arg) || ((state.detail || {}).product || {}).certificates?.find(x => x.id === arg); if (c) renewalAction(c); break; }
      case 'alert-action': GCM.actions.createFor('alert', arg, { title: `Close gap: ${el.dataset.title}`, priority: el.dataset.sev === 'Critical' ? 'Critical' : 'High', due_date: el.dataset.due || '', notes: `Product: ${$('pd-name').textContent}` }); break;
      case 'horizon-filter': GCM.ui.closeModal('modal-product-detail'); GCM.tabs.switchTo('horizon'); setTimeout(() => GCM.bus.emit('horizon:filter', { product_id: arg, days: 0 }), 150); break;
      case 'cert-filter': state.certFilter = arg; renderCerts(); break;
      case 'open-add-product': fillAddProductForm(); GCM.ui.openModal('modal-add-product'); break;
      case 'open-add-cert': fillAddCertForm(arg || $('modal-product-detail').dataset.productId); GCM.ui.openModal('modal-add-cert'); break;
      case 'preset-market': {
        const input = $('pf-add-product-form').querySelector('[name=target_markets]'); const set = new Set(parseMarkets(input.value));
        if (set.has(arg)) set.delete(arg); else set.add(arg);
        input.value = [...set].join(', '); input.dispatchEvent(new Event('input')); break;
      }
      case 'eco-market': { if (state.ecoMarkets.has(arg)) state.ecoMarkets.delete(arg); else state.ecoMarkets.add(arg); const p = productById($('modal-product-detail').dataset.productId); if (p) renderEcoMarkets(p); break; }
      case 'eco-all': { const p = productById($('modal-product-detail').dataset.productId); if (p) { state.ecoMarkets = new Set([...(p.target_markets || []), 'US', 'DE', 'GB', 'JP', 'KR', 'TW', 'CN', 'IN']); renderEcoMarkets(p); } break; }
      case 'eco-none': { const p = productById($('modal-product-detail').dataset.productId); state.ecoMarkets = new Set(); if (p) renderEcoMarkets(p); break; }
      case 'eco-run': runEco(el); break;
      case 'eco-action': {
        const p = productById($('modal-product-detail').dataset.productId); const r = state.ecoLast; if (!p || !r) break;
        const crit = (r.results || []).filter(x => String(x.action_level).startsWith('Critical')).map(x => x.country_code);
        GCM.actions.createFor('product', p.id, {
          title: `ECO ${r.component_type.replace(/_/g, ' ')} – ${p.sku}: ${r.overall_severity} regulatory impact`,
          priority: r.overall_severity === 'Critical' ? 'Critical' : r.overall_severity === 'Moderate' ? 'High' : 'Medium',
          notes: `${r.change_description}. ${r.countries_analyzed} markets analysed.${crit.length ? ` Re-test / certificate amendment required in: ${crit.join(', ')}.` : ''}`,
        });
        break;
      }
      default: break;
    }
  }

  /* ------------------------------------------------------------------ module */
  GCM.modules.portfolio = {
    init() {
      document.addEventListener('click', onClick);
      $('pf-search').addEventListener('input', () => { state.search = $('pf-search').value.trim(); renderGrid(); });
      $('pf-category').addEventListener('change', () => { state.category = $('pf-category').value; renderGrid(); });
      $('pf-sort').addEventListener('change', () => { state.sort = $('pf-sort').value; renderGrid(); });
      $('pf-add-product-form').addEventListener('submit', submitAddProduct);
      $('pf-add-cert-form').addEventListener('submit', submitAddCert);
      ['alerts:changed', 'actions:changed', 'audit:completed', 'countries:changed'].forEach(evt => GCM.bus.on(evt, scheduleRefresh));
      GCM.bus.on('products:changed', () => { if (!state.loading) scheduleRefresh(); });
      GCM.bus.on('portfolio:focus', (id) => { if (!id) return; if (state.loaded) openDetail(id); else { state.pendingFocus = id; loadAll(); } });
      GCM.palette.register({ label: 'Add product', icon: 'plus', keywords: ['product', 'sku', 'new', 'portfolio'], run: () => { GCM.tabs.switchTo('portfolio'); fillAddProductForm(); GCM.ui.openModal('modal-add-product'); } });
      GCM.palette.register({ label: 'Add certificate', icon: 'file-plus-2', keywords: ['certificate', 'cert', 'registration', 'new'], run: async () => { GCM.tabs.switchTo('portfolio'); if (!state.loaded) await loadAll(); fillAddCertForm(); GCM.ui.openModal('modal-add-cert'); } });
      GCM.palette.register({ label: 'Analyse engineering change (ECO)…', icon: 'git-branch', hint: 'Impact of a component change per market', keywords: ['eco', 'engineering change', 'component', 'adapter', 'controller', 'impact'], run: async () => { GCM.tabs.switchTo('portfolio'); if (!state.loaded) await loadAll(); const top = filteredProducts()[0] || products()[0]; if (top) openDetail(top.id, 'eco'); else GCM.ui.toast('No products yet', 'Add a product first to analyse an engineering change.', 'info'); } });
      GCM.palette.register({ label: 'Show expiring certificates', icon: 'alarm-clock', keywords: ['certificate', 'expiring', 'expired', 'renewal'], run: () => { GCM.tabs.switchTo('portfolio'); state.certFilter = 'Expiring Soon'; if (state.loaded) { renderCerts(); $('pf-cert-card').scrollIntoView({ behavior: 'smooth' }); } } });
    },
    onFirstShow() { loadAll(); },
    onShow() { if (state.loaded && !state.loading) scheduleRefresh(); GCM.ui.icons(); },
    refresh: loadAll, openDetail,
  };
})();
