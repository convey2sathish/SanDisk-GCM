/* =====================================================================
   GCM Platform 2.0 - alerts.js
   Regulation Alerts tab: list, filters, pillar chips, triage, cards with
   deadline countdown + impacted products, details panel, publish-alert form,
   deep-link focus, palette commands. Explanation modal lives in expert.js.
   ===================================================================== */
(function () {
  'use strict';
  const GCM = window.GCM; if (!GCM) return;
  const esc = (s) => GCM.ui.esc(s);

  const PILLAR_STYLE = {
    Safety: { cls: 'bg-rose-950/60 text-rose-300 border-rose-800/80', icon: 'shield', stripe: 'from-rose-600 to-orange-500' },
    EMC: { cls: 'bg-sky-950/60 text-sky-300 border-sky-800/80', icon: 'radio', stripe: 'from-sky-500 to-cyan-400' },
    Environmental: { cls: 'bg-emerald-950/60 text-emerald-300 border-emerald-800/80', icon: 'leaf', stripe: 'from-emerald-500 to-teal-400' },
    Cyber: { cls: 'bg-indigo-950/60 text-indigo-300 border-indigo-800/80', icon: 'lock', stripe: 'from-indigo-500 to-purple-500' },
    All: { cls: 'bg-purple-950/60 text-purple-300 border-purple-800/80', icon: 'layers', stripe: 'from-purple-500 via-sky-400 to-emerald-400' },
  };
  const SEV_STRIPE = { Critical: 'from-rose-600 via-rose-500 to-amber-500', Warning: 'from-amber-500 to-yellow-400', Info: 'from-sky-500 to-cyan-400' };
  const TRIAGE = ['New', 'Acknowledged', 'In Progress', 'Closed'];
  const TRIAGE_CLS = { New: 'badge-critical', Acknowledged: 'badge-warning', 'In Progress': 'badge-info', Closed: 'badge-success' };

  const S = { alerts: [], pillar: 'all', expanded: new Set(), productsOpen: new Set(), loaded: false, loading: false, registeredCmds: new Set(), pendingFocus: null };

  /* ------------------------------------------------------------------ helpers */
  const $ = (id) => document.getElementById(id);
  const filters = () => ({
    search: ($('alerts-f-search') || {}).value || '',
    category: ($('alerts-f-category') || {}).value || 'all',
    severity: ($('alerts-f-severity') || {}).value || 'all',
    region: ($('alerts-f-region') || {}).value || 'all',
    status: ($('alerts-f-status') || {}).value || 'all',
    sort: ($('alerts-f-sort') || {}).value || 'newest',
    impacts_portfolio: !!(($('alerts-f-portfolio') || {}).checked),
    pillar: S.pillar,
  });
  const filtersActive = (f) => f.search || f.category !== 'all' || f.severity !== 'all' || f.region !== 'all' || f.status !== 'all' || f.impacts_portfolio || f.pillar !== 'all';

  function pillarChip(p) {
    const st = PILLAR_STYLE[p] || PILLAR_STYLE.All;
    return `<span class="badge ${st.cls}"><i data-lucide="${st.icon}" class="w-3 h-3"></i>${esc(p || 'Safety')}</span>`;
  }
  function deadlineChip(a) {
    const iso = a.effective_date;
    const n = GCM.ui.daysUntil(iso);
    if (n === null) {
      const inForce = /^enforc/i.test(String(iso || ''));
      return `<span class="badge ${inForce ? 'badge-critical' : 'badge-neutral'}" title="Effective date: ${esc(iso || 'not set')}"><i data-lucide="${inForce ? 'gavel' : 'calendar'}" class="w-3 h-3"></i>${inForce ? 'In force now' : esc(iso || 'Date TBC')}</span>`;
    }
    const tone = GCM.ui.deadlineTone(iso);
    const label = n < 0 ? `Deadline passed ${GCM.ui.relDays(iso)}` : n === 0 ? 'Deadline today' : `${n} day${n === 1 ? '' : 's'} left`;
    return `<span class="badge badge-${tone}" title="Effective ${esc(GCM.ui.fmtDate(iso))}"><i data-lucide="${n < 0 ? 'alarm-clock-off' : n <= 90 ? 'alarm-clock' : 'calendar-clock'}" class="w-3 h-3"></i>${esc(label)}</span>`;
  }
  function flagFor(a) {
    const codes = a.market_codes || [];
    if (a.country_code && a.country_code.length === 2) return GCM.ui.flag(a.country_code);
    if (codes.length === 1) return GCM.ui.flag(codes[0]);
    if (/european union|eu 27/i.test(a.country || '')) return '🇪🇺';
    return '🌐';
  }
  function milestoneStatus(m) {
    const n = GCM.ui.daysUntil(m.date);
    if (n === null) return { label: m.status || 'Planned', cls: 'badge-neutral', dot: '#64748b' };
    if (n < 0) return { label: 'Passed', cls: 'badge-neutral', dot: '#64748b' };
    if (n <= 90) return { label: `Imminent · ${n}d`, cls: 'badge-critical', dot: '#f43f5e' };
    if (n <= 365) return { label: `Approaching · ${n}d`, cls: 'badge-warning', dot: '#f59e0b' };
    return { label: `Planned · ${n}d`, cls: 'badge-info', dot: '#38bdf8' };
  }

  /* ------------------------------------------------------------------ rendering */
  function renderTriageSummary(list) {
    const host = $('alerts-triage-summary'); if (!host) return;
    const counts = { New: 0, Acknowledged: 0, 'In Progress': 0, Closed: 0 };
    list.forEach(a => { const s = (a.triage || {}).status || 'New'; counts[s] = (counts[s] || 0) + 1; });
    host.innerHTML = TRIAGE.map(s => `<button type="button" class="badge ${TRIAGE_CLS[s]} cursor-pointer hover:brightness-125" data-act="triage-filter" data-arg="${esc(s)}" title="Show ${esc(s)} alerts">${esc(s)} <span class="mono ml-1">${counts[s]}</span></button>`).join('')
      + `<span class="pill ml-1" title="Critical alerts in this view">${list.filter(a => a.severity === 'Critical').length} critical</span>`;
  }

  function productsList(a) {
    const ps = a.impacted_products || [];
    if (!ps.length) return `<div class="text-[11px] text-slate-500 italic">No product in the current portfolio matches this alert's categories and markets.</div>`;
    return `<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-1.5">${ps.map(p => `
      <button type="button" data-action="deeplink-product" data-arg="${esc(p.id)}" class="text-left flex items-center gap-2 p-2 rounded-lg bg-slate-950/70 border border-slate-800 hover:border-emerald-600/60 transition">
        <i data-lucide="hard-drive" class="w-3.5 h-3.5 text-emerald-400 shrink-0"></i>
        <div class="min-w-0"><div class="text-[11px] font-semibold text-slate-100 truncate">${esc(p.name)}</div><div class="text-[10px] text-slate-400 mono truncate">${esc(p.sku)} · ${esc(p.market_label || p.category_name || '')}</div></div>
      </button>`).join('')}</div>`;
  }

  function detailsPanel(a) {
    const ms = (a.timeline_milestones || []).map(m => { const st = milestoneStatus(m); return `
      <div class="timeline-item" style="--dot:${st.dot}">
        <div class="flex flex-wrap items-center gap-2"><span class="text-xs font-semibold text-slate-100">${esc(m.phase)}</span><span class="badge ${st.cls}">${esc(st.label)}</span></div>
        <div class="text-[11px] text-slate-400 mono">${esc(m.date || 'TBC')}${m.status ? ` · notice says: ${esc(m.status)}` : ''}</div>
      </div>`; }).join('');
    const links = (a.official_links || []).filter(l => l && l.url).map(l => `<a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-300 border border-slate-700 hover:border-sky-500/60 text-[11px] font-medium transition"><i data-lucide="globe" class="w-3.5 h-3.5"></i>${esc(l.label || l.url)}<i data-lucide="external-link" class="w-3 h-3 text-slate-500"></i></a>`).join('');
    const checklist = (a.compliance_checklist || []).map(c => `<div class="flex items-start gap-2 p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-[11px] text-slate-300"><i data-lucide="check-square" class="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5"></i><span>${esc(c)}</span></div>`).join('');
    return `
      <div class="mt-3 pt-3 border-t border-slate-800 grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div class="xl:col-span-2 space-y-4">
          <div><div class="section-title text-sky-400 mb-1.5"><i data-lucide="file-text" class="w-3.5 h-3.5"></i>Regulatory context</div><div class="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-[12px] text-slate-200 leading-relaxed whitespace-pre-line">${esc(a.detailed_summary || a.summary)}</div></div>
          ${a.technical_impact ? `<div><div class="section-title text-amber-400 mb-1.5"><i data-lucide="cpu" class="w-3.5 h-3.5"></i>Technical impact &amp; test clauses</div><div class="p-3.5 rounded-xl bg-amber-950/20 border border-amber-900/40 text-[12px] text-amber-100/90 leading-relaxed whitespace-pre-line mono">${esc(a.technical_impact)}</div></div>` : ''}
          ${a.action_required ? `<div class="flex items-start gap-2.5 p-3 rounded-xl bg-emerald-950/30 border border-emerald-900/50 text-[12px]"><i data-lucide="check-circle-2" class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5"></i><div><strong class="text-white">Required action:</strong> <span class="text-slate-200">${esc(a.action_required)}</span></div></div>` : ''}
          ${checklist ? `<div><div class="section-title text-emerald-400 mb-1.5"><i data-lucide="list-checks" class="w-3.5 h-3.5"></i>Compliance checklist</div><div class="grid grid-cols-1 md:grid-cols-2 gap-1.5">${checklist}</div></div>` : ''}
        </div>
        <div class="space-y-4">
          ${ms ? `<div><div class="section-title mb-2"><i data-lucide="milestone" class="w-3.5 h-3.5"></i>Milestones (status recomputed today)</div><div class="timeline">${ms}</div></div>` : ''}
          ${links ? `<div><div class="section-title text-sky-400 mb-1.5"><i data-lucide="link" class="w-3.5 h-3.5"></i>Official sources</div><div class="flex flex-wrap gap-1.5">${links}</div></div>` : `<div class="text-[11px] text-slate-500 italic">No official link recorded for this alert.</div>`}
          <div class="text-[11px] text-slate-500 space-y-0.5"><div>Source: <span class="text-slate-300">${esc(a.source || '—')}</span></div><div>Status: <span class="text-slate-300">${esc(a.status || '—')}</span></div><div>Alert ID: <span class="mono text-slate-300">${esc(a.id)}</span></div>${a.market_count ? `<div>Markets in scope: <span class="text-slate-300">${a.market_count}</span></div>` : ''}</div>
        </div>
      </div>`;
  }

  function card(a) {
    const pillar = a.pillar || 'Safety';
    const stripe = SEV_STRIPE[a.severity] || SEV_STRIPE.Info;
    const open = S.expanded.has(a.id);
    const prodOpen = S.productsOpen.has(a.id);
    const cats = a.affected_categories || [];
    const catLabel = cats.some(c => /^all/.test(c)) ? 'All 11 storage categories' : `${cats.length} categor${cats.length === 1 ? 'y' : 'ies'}`;
    const triage = (a.triage || {}).status || 'New';
    return `
    <article class="card alert-card !p-0 overflow-hidden" id="alert-card-${esc(a.id)}" data-id="${esc(a.id)}">
      <div class="h-1 bg-gradient-to-r ${stripe}"></div>
      <div class="p-4 space-y-3">
        <div class="flex flex-col lg:flex-row lg:items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-1.5 mb-2">
              ${GCM.ui.badge(a.severity, a.severity)}
              ${pillarChip(pillar)}
              <span class="pill gap-1"><span>${flagFor(a)}</span><span class="truncate max-w-[220px]">${esc(a.country || a.region || 'Global')}</span></span>
              ${a.standard ? `<span class="pill mono text-sky-300 border-sky-900/60 max-w-[320px] truncate" title="${esc(a.standard)}">${esc(a.standard)}</span>` : ''}
              ${a.is_user_created ? `<span class="pill text-amber-300 border-amber-900/60">${/^ALERT-SURV/.test(a.id) ? 'Surveillance' : 'Published by user'}</span>` : ''}
            </div>
            <h3 class="text-sm font-bold text-white leading-snug">${esc(a.title)}</h3>
            <p class="text-xs text-slate-300 leading-relaxed mt-1.5">${esc(a.summary)}</p>
          </div>
          <div class="flex flex-row lg:flex-col items-start lg:items-end gap-1.5 shrink-0">
            ${deadlineChip(a)}
            <span class="text-[11px] text-slate-400 whitespace-nowrap">Effective <span class="mono text-slate-200">${esc(GCM.ui.fmtDate(a.effective_date) === '—' ? (a.effective_date || 'TBC') : /^\d{4}-\d{2}-\d{2}/.test(a.effective_date || '') ? GCM.ui.fmtDate(a.effective_date) : a.effective_date)}</span></span>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-1.5 text-[11px]">
          <button type="button" data-act="toggle-products" class="badge ${a.impacted_products_count ? 'badge-success' : 'badge-neutral'} cursor-pointer hover:brightness-125" title="Show impacted portfolio products"><i data-lucide="hard-drive" class="w-3 h-3"></i>${a.impacted_products_count || 0} product${a.impacted_products_count === 1 ? '' : 's'} impacted<i data-lucide="${prodOpen ? 'chevron-up' : 'chevron-down'}" class="w-3 h-3"></i></button>
          <span class="pill"><i data-lucide="boxes" class="w-3 h-3 mr-1"></i>${esc(catLabel)}</span>
          ${a.market_count ? `<span class="pill"><i data-lucide="globe-2" class="w-3 h-3 mr-1"></i>${a.market_count} market${a.market_count === 1 ? '' : 's'}</span>` : ''}
          <span class="text-slate-500 hidden md:inline truncate max-w-[260px]" title="${esc(a.source || '')}">Source: ${esc(a.source || 'Regulatory gazette')}</span>
        </div>
        <div class="${prodOpen ? '' : 'hidden'}" data-role="products">${prodOpen ? productsList(a) : ''}</div>

        <div class="flex flex-col md:flex-row md:items-center justify-between gap-2 pt-2 border-t border-slate-800/80">
          <div class="flex items-center gap-2">
            <label class="text-[10px] uppercase tracking-wider font-bold text-slate-500">Triage</label>
            <select data-act="triage" class="select !w-auto !py-1 !text-[11px]" aria-label="Triage status">${TRIAGE.map(t => `<option ${t === triage ? 'selected' : ''}>${t}</option>`).join('')}</select>
            <span class="badge ${TRIAGE_CLS[triage]}" data-role="triage-badge">${esc(triage)}</span>
            ${(a.triage || {}).owner ? `<span class="pill" title="Owner">${esc(a.triage.owner)}</span>` : ''}
          </div>
          <div class="flex flex-wrap items-center gap-1.5">
            <button type="button" data-act="explain" class="btn btn-indigo btn-sm"><i data-lucide="sparkles" class="w-3.5 h-3.5"></i>Explain in plain English</button>
            <button type="button" data-act="ask" class="btn btn-secondary btn-sm"><i data-lucide="message-circle-question" class="w-3.5 h-3.5 text-indigo-300"></i>Ask the expert</button>
            <button type="button" data-act="action" class="btn btn-ghost btn-sm"><i data-lucide="plus-square" class="w-3.5 h-3.5 text-emerald-400"></i>Create action</button>
            <button type="button" data-act="details" class="btn btn-ghost btn-sm"><span>${open ? 'Hide details' : 'Details'}</span><i data-lucide="${open ? 'chevron-up' : 'chevron-down'}" class="w-3.5 h-3.5"></i></button>
            ${a.is_user_created ? `<button type="button" data-act="delete" class="btn btn-ghost btn-sm text-rose-300" title="Delete this alert"><i data-lucide="trash-2" class="w-3.5 h-3.5"></i></button>` : ''}
          </div>
        </div>
        <div class="${open ? '' : 'hidden'}" data-role="details">${open ? detailsPanel(a) : ''}</div>
      </div>
    </article>`;
  }

  function render() {
    const host = $('alerts-list'); if (!host) return;
    const f = filters();
    const label = $('alerts-count-label');
    if (label) label.textContent = `${S.alerts.length} alert${S.alerts.length === 1 ? '' : 's'}${filtersActive(f) ? ' (filtered)' : ''} · ${S.alerts.filter(a => a.impacted_products_count).length} touch the portfolio`;
    if (!S.alerts.length) {
      host.innerHTML = `<div class="card">${GCM.ui.empty(filtersActive(f) ? 'No alerts match these filters. Reset the filters or publish a new alert.' : 'No alerts yet. Publish one or run a surveillance scan.', 'bell-off')}</div>`;
    } else {
      host.innerHTML = S.alerts.map(card).join('');
    }
    renderTriageSummary(S.alerts);
    const lbl = $('alerts-expand-label'); if (lbl) lbl.textContent = S.expanded.size && S.expanded.size >= S.alerts.length ? 'Collapse all' : 'Expand all';
    GCM.ui.icons();
  }

  /* ------------------------------------------------------------------ data */
  async function load(opts = {}) {
    const host = $('alerts-list'); if (!host) return;
    if (S.loading) return;
    S.loading = true;
    if (!S.loaded || opts.skeleton) host.innerHTML = GCM.ui.skeleton(4);
    const f = filters();
    const qs = new URLSearchParams();
    Object.entries(f).forEach(([k, v]) => { if (v && v !== 'all' && v !== false) qs.set(k, v === true ? '1' : v); });
    try {
      const list = await GCM.api.get(`/api/alerts${qs.toString() ? '?' + qs : ''}`);
      S.alerts = Array.isArray(list) ? list : [];
      S.loaded = true;
      if (!filtersActive(f)) { GCM.state.alerts = S.alerts; updateBadge(S.alerts); registerAlertCommands(S.alerts); }
      else refreshBadge();
      render();
      if (S.pendingFocus) { const id = S.pendingFocus; S.pendingFocus = null; focusAlert(id); }
    } catch (e) {
      host.innerHTML = `<div class="card border-rose-900/60"><div class="flex items-start gap-3"><i data-lucide="alert-triangle" class="w-5 h-5 text-rose-400 shrink-0"></i><div><div class="text-sm font-bold text-white">Could not load alerts</div><div class="text-xs text-slate-400 mt-1">${esc(e.message)}</div><button type="button" data-action="alerts-refresh" class="btn btn-secondary btn-sm mt-3"><i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>Retry</button></div></div></div>`;
      GCM.ui.icons();
    } finally { S.loading = false; }
  }
  function updateBadge(list) {
    const b = $('badge-alert-count'); if (!b) return;
    const open = list.filter(a => ((a.triage || {}).status || 'New') !== 'Closed').length;
    b.textContent = String(open); b.title = `${open} open alert${open === 1 ? '' : 's'} (${list.length} total)`;
  }
  async function refreshBadge() {
    try { const all = await GCM.api.get('/api/alerts'); if (Array.isArray(all)) { GCM.state.alerts = all; updateBadge(all); registerAlertCommands(all); } } catch (_) { /* ignore */ }
  }
  function registerAlertCommands(list) {
    list.slice(0, 40).forEach(a => {
      if (S.registeredCmds.has(a.id)) return; S.registeredCmds.add(a.id);
      GCM.palette.register({ label: `Explain alert: ${a.title}`, hint: `${a.severity} · ${a.country || a.region}`, icon: 'sparkles',
        keywords: ['explain', 'alert', String(a.id).toLowerCase(), String(a.standard || '').toLowerCase(), String(a.country || '').toLowerCase()],
        run: () => GCM.explain && GCM.explain.open(a.id, 'simple') });
    });
  }
  const alertById = (id) => S.alerts.find(a => a.id === id) || (GCM.state.alerts || []).find(a => a.id === id);

  /* ------------------------------------------------------------------ interactions */
  async function setTriage(id, status, selectEl) {
    try {
      const r = await GCM.api.patch(`/api/alerts/${encodeURIComponent(id)}/triage`, { status });
      const a = alertById(id); if (a) a.triage = Object.assign(a.triage || {}, r.triage);
      const cardEl = $(`alert-card-${id}`);
      if (cardEl) { const b = cardEl.querySelector('[data-role=triage-badge]'); if (b) { b.className = `badge ${TRIAGE_CLS[status]}`; b.textContent = status; } }
      renderTriageSummary(S.alerts); updateBadge(GCM.state.alerts && GCM.state.alerts.length ? GCM.state.alerts.map(x => x.id === id ? Object.assign({}, x, { triage: r.triage }) : x) : S.alerts);
      GCM.state.alerts = (GCM.state.alerts || []).map(x => x.id === id ? Object.assign({}, x, { triage: r.triage }) : x);
      GCM.ui.toast('Triage updated', `${status} · ${id}`, 'success');
      GCM.bus.emit('alerts:triaged', { id, triage: r.triage });
    } catch (e) { GCM.ui.toast('Could not update triage', e.message, 'error'); if (selectEl) load(); }
  }
  function toggleDetails(id, force) {
    const a = alertById(id); const cardEl = $(`alert-card-${id}`); if (!a || !cardEl) return;
    const willOpen = force !== undefined ? force : !S.expanded.has(id);
    if (willOpen) S.expanded.add(id); else S.expanded.delete(id);
    const panel = cardEl.querySelector('[data-role=details]');
    if (panel) { panel.innerHTML = willOpen ? detailsPanel(a) : ''; panel.classList.toggle('hidden', !willOpen); }
    const btn = cardEl.querySelector('[data-act=details]');
    if (btn) btn.innerHTML = `<span>${willOpen ? 'Hide details' : 'Details'}</span><i data-lucide="${willOpen ? 'chevron-up' : 'chevron-down'}" class="w-3.5 h-3.5"></i>`;
    const lbl = $('alerts-expand-label'); if (lbl) lbl.textContent = S.expanded.size >= S.alerts.length && S.alerts.length ? 'Collapse all' : 'Expand all';
    GCM.ui.icons();
  }
  function toggleProducts(id) {
    const a = alertById(id); const cardEl = $(`alert-card-${id}`); if (!a || !cardEl) return;
    const willOpen = !S.productsOpen.has(id);
    if (willOpen) S.productsOpen.add(id); else S.productsOpen.delete(id);
    const panel = cardEl.querySelector('[data-role=products]');
    if (panel) { panel.innerHTML = willOpen ? productsList(a) : ''; panel.classList.toggle('hidden', !willOpen); }
    GCM.ui.icons();
  }
  function createActionFor(a) {
    const n = GCM.ui.daysUntil(a.effective_date);
    const due = (n !== null && n > 30) ? new Date(Date.now() + (Math.max(7, Math.round(n * 0.6))) * 86400000).toISOString().slice(0, 10) : (n !== null && n >= 0 ? a.effective_date : '');
    GCM.actions.createFor('alert', a.id, {
      title: `${a.standard ? a.standard + ': ' : ''}${a.action_required ? a.action_required.split(/[.;]/)[0] : 'Gap assessment for ' + a.title}`.slice(0, 180),
      priority: a.severity === 'Critical' ? 'Critical' : a.severity === 'Warning' ? 'High' : 'Medium',
      due_date: due, notes: `${a.title}\n${a.country || ''} · effective ${a.effective_date || 'TBC'}\n${a.summary || ''}`,
    });
  }
  async function deleteAlert(a) {
    const ok = await GCM.ui.confirm(`Delete "${a.title}"? This removes the alert and its triage state.`, { title: 'Delete alert', okLabel: 'Delete', danger: true });
    if (!ok) return;
    try { await GCM.api.del(`/api/alerts/${encodeURIComponent(a.id)}`); GCM.ui.toast('Alert deleted', a.id, 'info'); GCM.bus.emit('alerts:changed'); }
    catch (e) { GCM.ui.toast('Could not delete', e.message, 'error'); }
  }
  function focusAlert(id) {
    const el = $(`alert-card-${id}`);
    if (!el) {
      if (!S.loaded || S.loading) { S.pendingFocus = id; return; }
      if (filtersActive(filters())) { resetFilters(false); S.pendingFocus = id; load({ skeleton: true }); return; }
      GCM.ui.toast('Alert not found', id, 'warning'); return;
    }
    toggleDetails(id, true);
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    document.querySelectorAll('.alert-card.focused').forEach(x => x.classList.remove('focused'));
    el.classList.add('focused'); setTimeout(() => el.classList.remove('focused'), 4000);
  }
  function resetFilters(reload = true) {
    ['alerts-f-search'].forEach(id => { const el = $(id); if (el) el.value = ''; });
    ['alerts-f-category', 'alerts-f-severity', 'alerts-f-region', 'alerts-f-status'].forEach(id => { const el = $(id); if (el) el.value = 'all'; });
    const sort = $('alerts-f-sort'); if (sort) sort.value = 'newest';
    const pf = $('alerts-f-portfolio'); if (pf) pf.checked = false;
    setPillar('all', false);
    if (reload) load({ skeleton: true });
  }
  function setPillar(p, reload = true) {
    S.pillar = p;
    document.querySelectorAll('#alerts-pillar-chips [data-pillar]').forEach(b => b.classList.toggle('active', b.dataset.pillar === p));
    if (reload) load({ skeleton: true });
  }

  /* ------------------------------------------------------------------ publish-alert form */
  function populateForm() {
    const cats = GCM.state.categories || [];
    const sel = document.querySelector('#modal-add-alert select[name=affected_categories]');
    if (sel && !sel.options.length) cats.forEach(c => { const o = document.createElement('option'); o.value = c.id; o.textContent = c.name; sel.appendChild(o); });
    const dl = $('country-datalist');
    if (dl && !dl.options.length) {
      const names = Object.values(GCM.state.countries || {}).map(c => c.name).filter(Boolean).sort();
      ['European Union', 'Global'].concat(names).forEach(n => { const o = document.createElement('option'); o.value = n; dl.appendChild(o); });
    }
    const fc = $('alerts-f-category');
    if (fc && fc.options.length <= 1) cats.forEach(c => { const o = document.createElement('option'); o.value = c.id; o.textContent = c.name; fc.appendChild(o); });
    const fr = $('alerts-f-region');
    if (fr && fr.options.length <= 1) {
      const regions = [...new Set(Object.values(GCM.state.countries || {}).map(c => c.region).filter(Boolean))].sort();
      ['Global'].concat(regions).forEach(r => { const o = document.createElement('option'); o.value = r; o.textContent = r; fr.appendChild(o); });
    }
  }
  async function submitAlertForm(form) {
    const fd = new FormData(form);
    const body = {};
    ['title', 'country', 'region', 'severity', 'pillar', 'standard', 'effective_date', 'summary', 'action_required', 'source_url'].forEach(k => { body[k] = String(fd.get(k) || '').trim(); });
    body.affected_categories = [...form.querySelectorAll('select[name=affected_categories] option:checked')].map(o => o.value);
    if (!body.title || !body.summary) { GCM.ui.toast('Title and summary are required', 'Describe what changed in one or two sentences.', 'warning'); return; }
    const btn = form.querySelector('button[type=submit]'); GCM.ui.setLoading(btn, true, 'Publishing…');
    try {
      const r = await GCM.api.post('/api/alerts', body);
      GCM.ui.closeModal('modal-add-alert'); form.reset();
      GCM.ui.toast('Alert published', `${r.alert.id} · ${r.alert.impacted_products_count || 0} portfolio product(s) impacted`, 'success');
      resetFilters(false);
      S.pendingFocus = r.alert.id;
      GCM.bus.emit('alerts:changed', { id: r.alert.id, created: true });
      GCM.tabs.switchTo('alerts');
    } catch (e) { GCM.ui.toast('Could not publish alert', e.message, 'error'); }
    finally { GCM.ui.setLoading(btn, false); }
  }

  /* ------------------------------------------------------------------ module */
  GCM.modules.alerts = {
    init() {
      populateForm();
      GCM.bus.on('ready', populateForm);
      GCM.bus.on('countries:changed', populateForm);
      // filters
      let t = null;
      const search = $('alerts-f-search'); if (search) search.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => load(), 220); });
      ['alerts-f-category', 'alerts-f-severity', 'alerts-f-region', 'alerts-f-status', 'alerts-f-sort', 'alerts-f-portfolio'].forEach(id => { const el = $(id); if (el) el.addEventListener('change', () => load({ skeleton: true })); });
      const chips = $('alerts-pillar-chips'); if (chips) chips.addEventListener('click', e => { const b = e.target.closest('[data-pillar]'); if (b) setPillar(b.dataset.pillar); });
      // header buttons (delegated through core's data-action -> bus)
      GCM.bus.on('action:alerts-refresh', () => load({ skeleton: true }));
      GCM.bus.on('action:alerts-reset-filters', () => resetFilters());
      GCM.bus.on('action:alerts-expand-all', () => { const all = S.expanded.size >= S.alerts.length && S.alerts.length; S.alerts.forEach(a => toggleDetails(a.id, !all)); });
      // card actions
      const list = $('alerts-list');
      if (list) {
        list.addEventListener('click', e => {
          const el = e.target.closest('[data-act]'); if (!el) return;
          const cardEl = el.closest('.alert-card'); const id = cardEl ? cardEl.dataset.id : null; const a = id ? alertById(id) : null;
          switch (el.dataset.act) {
            case 'explain': if (a) GCM.explain.open(a.id, 'simple'); break;
            case 'ask': if (a) GCM.explain.open(a.id, 'simple', { section: 'qa' }); break;
            case 'action': if (a) createActionFor(a); break;
            case 'details': if (a) toggleDetails(a.id); break;
            case 'toggle-products': if (a) toggleProducts(a.id); break;
            case 'delete': if (a) deleteAlert(a); break;
            default: break;
          }
        });
        list.addEventListener('change', e => { const sel = e.target.closest('select[data-act=triage]'); if (!sel) return; const cardEl = sel.closest('.alert-card'); if (cardEl) setTriage(cardEl.dataset.id, sel.value, sel); });
      }
      const summary = $('alerts-triage-summary');
      if (summary) summary.addEventListener('click', e => { const b = e.target.closest('[data-act=triage-filter]'); if (!b) return; const st = $('alerts-f-status'); if (st) { st.value = st.value === b.dataset.arg ? 'all' : b.dataset.arg; load({ skeleton: true }); } });
      // publish form
      const form = $('add-alert-form'); if (form) form.addEventListener('submit', e => { e.preventDefault(); submitAlertForm(form); });
      // bus
      GCM.bus.on('alerts:changed', () => { S.loaded ? load({ skeleton: false }) : refreshBadge(); });
      GCM.bus.on('alerts:focus', id => { if (!id) return; if (!S.loaded) { S.pendingFocus = id; load(); } else focusAlert(id); });
      GCM.bus.on('actions:changed', () => { /* nothing to reload; action drawer owns its state */ });
      // palette
      GCM.palette.register({ label: 'Publish a regulatory alert', icon: 'megaphone', keywords: ['alert', 'publish', 'new', 'create'], run: () => GCM.ui.openModal('modal-add-alert') });
      GCM.palette.register({ label: 'Explain an alert in plain English…', hint: 'Open the alerts tab and pick one', icon: 'sparkles', keywords: ['explain', 'plain english', 'alert', 'ai'], run: () => { GCM.tabs.switchTo('alerts'); setTimeout(() => { const s = $('alerts-f-search'); if (s) s.focus(); GCM.ui.toast('Pick an alert', 'Press "Explain in plain English" on any card, or type "Explain alert:" in the palette.', 'info'); }, 150); } });
      GCM.palette.register({ label: 'Show only alerts impacting my portfolio', icon: 'hard-drive', keywords: ['portfolio', 'alerts', 'impact'], run: () => { GCM.tabs.switchTo('alerts'); const pf = $('alerts-f-portfolio'); if (pf) { pf.checked = true; load({ skeleton: true }); } } });
      // badge early (before first show)
      refreshBadge();
    },
    onFirstShow() { populateForm(); load(); },
    onShow() { if (S.loaded && !S.loading) load(); },
  };
})();
