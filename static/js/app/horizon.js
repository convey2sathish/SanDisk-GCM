/* =====================================================================
   GCM Platform 2.0 - horizon.js
   Horizon & Risk tab: Compliance Risk Index gauge, KPIs, regulatory
   horizon timeline (month-grouped, heat-strip, filters, CSV export) and
   the risk breakdown by product / region / pillar plus top risks.
   Data: /api/risk/summary, /api/horizon, /api/certificates/health
   ===================================================================== */
(function () {
  'use strict';
  const GCM = window.GCM;
  if (!GCM) return;
  const esc = (s) => GCM.ui.esc(s);

  const GRADE_COLOR = { A: '#10b981', B: '#34d399', C: '#facc15', D: '#fb923c', E: '#f43f5e', F: '#e11d48' };
  const GRADE_LABEL = { A: 'Low risk', B: 'Controlled', C: 'Elevated', D: 'High', E: 'Severe', F: 'Critical' };
  const GRADE_BADGE = {
    A: 'badge badge-success', B: 'badge badge-success', C: 'badge badge-warning',
    D: 'badge badge-warning', E: 'badge badge-critical', F: 'badge badge-critical',
  };
  const GRADE_BAR = {
    A: 'bg-gradient-to-r from-emerald-600 to-emerald-400', B: 'bg-gradient-to-r from-emerald-600 to-teal-400',
    C: 'bg-gradient-to-r from-amber-600 to-yellow-400', D: 'bg-gradient-to-r from-orange-600 to-amber-400',
    E: 'bg-gradient-to-r from-rose-700 to-orange-500', F: 'bg-gradient-to-r from-rose-800 to-rose-500',
  };
  const TONE_DOT = { critical: '#f43f5e', warning: '#f59e0b', info: '#38bdf8', success: '#10b981' };
  const TONE_BADGE = { critical: 'badge badge-critical', warning: 'badge badge-warning', info: 'badge badge-info', success: 'badge badge-success' };
  const TYPE_META = {
    alert_deadline: { icon: 'bell', label: 'Enforcement deadline', cls: 'text-rose-300 bg-rose-950/60 border-rose-800/60' },
    milestone: { icon: 'flag', label: 'Milestone', cls: 'text-sky-300 bg-sky-950/60 border-sky-800/60' },
    cert_expiry: { icon: 'file-badge', label: 'Certificate expiry', cls: 'text-amber-300 bg-amber-950/60 border-amber-800/60' },
    action_due: { icon: 'check-square', label: 'Action due', cls: 'text-emerald-300 bg-emerald-950/60 border-emerald-800/60' },
    surveillance: { icon: 'scroll-text', label: 'Surveillance ledger', cls: 'text-indigo-300 bg-indigo-950/60 border-indigo-800/60' },
  };
  const PILLAR_CHIP = {
    Safety: 'border-rose-700/60 bg-rose-950/40 text-rose-200 hover:border-rose-500',
    EMC: 'border-sky-700/60 bg-sky-950/40 text-sky-200 hover:border-sky-500',
    Environmental: 'border-emerald-700/60 bg-emerald-950/40 text-emerald-200 hover:border-emerald-500',
    Cyber: 'border-indigo-700/60 bg-indigo-950/40 text-indigo-200 hover:border-indigo-500',
    All: 'border-purple-700/60 bg-purple-950/40 text-purple-200 hover:border-purple-500',
  };
  const PILLAR_ICON = { Safety: 'shield', EMC: 'radio', Environmental: 'leaf', Cyber: 'lock', All: 'refresh-cw' };
  const PILLAR_PILL = {
    Safety: 'badge badge-critical', EMC: 'badge badge-info', Environmental: 'badge badge-success', Cyber: 'badge badge-indigo', All: 'badge badge-purple',
  };
  const BUCKET_META = [
    ['overdue', 'Overdue', 'badge badge-critical'], ['next_30', '≤ 30 days', 'badge badge-warning'], ['next_90', '31–90 days', 'badge badge-warning'],
    ['next_365', '91–365 days', 'badge badge-info'], ['beyond', 'Beyond a year', 'badge badge-neutral'], ['history', 'History', 'badge badge-success'],
  ];
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  const state = {
    loaded: false, loading: false, days: 365, pillar: '', product: '',
    types: new Set(['alert_deadline', 'milestone', 'cert_expiry', 'action_due']),
    showHistory: false, bucketFilter: null, summary: null, horizon: null, health: null, products: [],
  };
  let refreshTimer = null;
  const $ = (id) => document.getElementById(id);

  /* ------------------------------------------------------------------ data */
  function horizonQuery() {
    const p = new URLSearchParams();
    p.set('days', String(state.days));
    const types = [...state.types];
    if (types.length) p.set('types', types.join(','));
    if (state.pillar) p.set('pillar', state.pillar);
    if (state.product) p.set('product_id', state.product);
    return p.toString();
  }

  async function loadAll() {
    if (state.loading) return;
    state.loading = true;
    try {
      const [summary, health, horizon] = await Promise.all([
        GCM.api.get('/api/risk/summary'),
        GCM.api.get('/api/certificates/health'),
        GCM.api.get(`/api/horizon?${horizonQuery()}`),
      ]);
      state.summary = summary; state.health = health; state.horizon = horizon; state.loaded = true;
      renderIndex(); renderKpis(); renderProductFilter(); renderHorizon(); renderBreakdown();
    } catch (e) {
      console.error('[horizon] load failed', e);
      $('hz-timeline').innerHTML = GCM.ui.empty(`Could not load the horizon: ${e.message}`, 'wifi-off');
      GCM.ui.toast('Horizon unavailable', e.message, 'error');
    } finally { state.loading = false; GCM.ui.icons(); }
  }

  async function loadHorizonOnly() {
    const host = $('hz-timeline');
    if (!state.types.size) {
      state.horizon = { events: [], buckets: {}, months: (state.horizon && state.horizon.months || []).map(m => ({ ...m, count: 0, critical: 0 })), today: state.horizon && state.horizon.today };
      renderHorizon(); return;
    }
    host.setAttribute('aria-busy', 'true');
    try {
      state.horizon = await GCM.api.get(`/api/horizon?${horizonQuery()}`);
      renderHorizon();
    } catch (e) {
      host.innerHTML = GCM.ui.empty(`Could not load the horizon: ${e.message}`, 'wifi-off');
    } finally { host.removeAttribute('aria-busy'); GCM.ui.icons(); }
  }

  function scheduleRefresh() {
    if (!state.loaded) return;
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(loadAll, 450);
  }

  /* ------------------------------------------------------------------ index gauge & KPIs */
  function renderIndex() {
    const s = state.summary; if (!s) return;
    const grade = s.grade || 'A'; const color = GRADE_COLOR[grade] || '#38bdf8';
    const gauge = $('hz-gauge');
    gauge.style.setProperty('--value', String(Math.max(0, Math.min(100, s.compliance_risk_index || 0))));
    gauge.style.setProperty('--color', color);
    gauge.setAttribute('aria-label', `Compliance Risk Index ${s.compliance_risk_index} of 100, grade ${grade}`);
    $('hz-index-glow').style.background = color;
    $('hz-index-value').textContent = String(s.compliance_risk_index ?? '—');
    $('hz-index-value').style.color = color;
    $('hz-index-grade').textContent = `GRADE ${grade}`;
    $('hz-index-label').innerHTML = `<span style="color:${color}">${esc(GRADE_LABEL[grade] || '')}</span> <span class="text-slate-500 font-normal text-xs">· 0 = no exposure, 100 = maximum risk</span>`;
    $('hz-trend-note').textContent = s.trend_note || '';
    $('hz-index-updated').textContent = s.generated_at ? `as of ${GCM.ui.fmtDateTime(s.generated_at)}` : '';
    const c = s.components || {};
    const comps = [
      ['Product mean', c.weighted_product_mean, 'market-weighted mean of product risk scores (70 % of the index)'],
      ['Alert pressure', c.alert_pressure, 'all open alert scores through the soft cap (30 % of the index)'],
      ['What-if', c.what_if_triage_index, 'index if every untouched critical alert were moved to In Progress'],
    ].filter(x => x[1] !== null && x[1] !== undefined);
    $('hz-index-components').innerHTML = comps.map(([l, v, t]) => `<span class="pill gap-1" title="${esc(t)}">${esc(l)} <strong class="text-white mono">${esc(v)}</strong></span>`).join('');
    const f = s.formula || {};
    $('hz-formula').innerHTML = `
      <div class="section-title text-sky-300"><i data-lucide="calculator" class="w-3.5 h-3.5"></i>${esc(f.title || 'How the index is calculated')}</div>
      <ol class="list-decimal pl-4 space-y-1.5 text-slate-300">${(f.steps || []).map(st => `<li>${esc(st)}</li>`).join('')}</ol>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1">
        ${Object.entries(f.severity_weight || {}).map(([k, v]) => `<div class="rounded-lg border border-slate-800 bg-slate-900/60 px-2 py-1.5"><div class="text-[10px] uppercase text-slate-500">Severity ${esc(k)}</div><div class="mono text-white">× ${esc(v)}</div></div>`).join('')}
        ${Object.entries(f.triage_factor || {}).map(([k, v]) => `<div class="rounded-lg border border-slate-800 bg-slate-900/60 px-2 py-1.5"><div class="text-[10px] uppercase text-slate-500">Triage ${esc(k)}</div><div class="mono text-white">× ${esc(v)}</div></div>`).join('')}
      </div>
      <p class="text-slate-500">Every number on this page can be traced back to a specific alert, certificate or action: open "Top risks" or expand a product row to see the drivers.</p>`;
  }

  function renderKpis() {
    const s = state.summary || {}; const h = state.health || {}; const hb = (state.horizon && state.horizon.buckets) || {};
    const c = s.components || {};
    const overdue = hb.overdue ? hb.overdue.count : (c.overdue_alerts || 0);
    const due30 = hb.next_30 ? hb.next_30.count : 0;
    const due90 = due30 + (hb.next_90 ? hb.next_90.count : 0);
    const tiles = [
      { label: 'Overdue items', value: overdue, sub: 'deadlines passed, still open', glow: 'rgba(244,63,94,.28)', icon: 'alarm-clock-off', bucket: 'overdue', tone: overdue ? 'text-rose-300' : 'text-white' },
      { label: 'Due ≤ 30 days', value: due30, sub: 'need a decision this month', glow: 'rgba(245,158,11,.28)', icon: 'calendar-clock', bucket: 'next_30', tone: due30 ? 'text-amber-300' : 'text-white' },
      { label: 'Due ≤ 90 days', value: due90, sub: 'inside a typical lab lead time', glow: 'rgba(56,189,248,.22)', icon: 'calendar-range', bucket: 'next_90', tone: 'text-white' },
      { label: 'Expiring certificates', value: (h.expiring_90 || 0) + (h.expired || 0), sub: `${h.expired || 0} expired · ${h.expiring_30 || 0} within 30 d`, glow: 'rgba(251,146,60,.25)', icon: 'file-badge', tab: 'portfolio', tone: (h.expired || 0) ? 'text-orange-300' : 'text-white' },
      { label: 'Open critical alerts', value: c.critical_open_alerts || 0, sub: `${c.open_alerts || 0} open alerts in total`, glow: 'rgba(225,29,72,.28)', icon: 'siren', tab: 'alerts', tone: (c.critical_open_alerts || 0) ? 'text-rose-300' : 'text-white' },
    ];
    $('hz-kpis').innerHTML = tiles.map(t => `
      <button type="button" class="kpi text-left w-full" style="--kpi-glow:${t.glow}" data-hz="${t.bucket ? 'kpi-bucket' : 'kpi-tab'}" data-arg="${esc(t.bucket || t.tab)}" title="${t.bucket ? 'Filter the horizon to this bucket' : 'Open tab'}">
        <div class="flex items-center justify-between"><div class="kpi-label">${esc(t.label)}</div><i data-lucide="${t.icon}" class="w-4 h-4 text-slate-500"></i></div>
        <div class="kpi-value ${t.tone}">${esc(t.value)}</div>
        <div class="kpi-sub">${esc(t.sub)}</div>
      </button>`).join('');
  }

  function renderProductFilter() {
    const sel = $('hz-product'); if (!sel) return;
    const products = (state.summary && state.summary.per_product) || [];
    state.products = products;
    const cur = state.product;
    sel.innerHTML = '<option value="">All products</option>' + products.slice().sort((a, b) => String(a.name).localeCompare(String(b.name)))
      .map(p => `<option value="${esc(p.id)}" ${p.id === cur ? 'selected' : ''}>${esc(p.name)} · ${esc(p.sku)}</option>`).join('');
  }

  /* ------------------------------------------------------------------ horizon timeline */
  function visibleEvents() {
    const h = state.horizon; if (!h) return [];
    return (h.events || []).filter(e => {
      if (!state.showHistory && e.bucket === 'history') return false;
      if (state.bucketFilter && e.bucket !== state.bucketFilter) return false;
      return true;
    });
  }

  function renderHeat() {
    const h = state.horizon; const host = $('hz-heat'); if (!h || !host) return;
    const months = h.months || []; const max = Math.max(1, ...months.map(m => m.count));
    host.innerHTML = months.map(m => {
      const [y, mm] = m.month.split('-'); const label = `${MONTHS[+mm - 1]} ${String(y).slice(2)}`;
      const intensity = m.count ? 0.25 + 0.75 * (m.count / max) : 0;
      const bg = !m.count ? 'rgba(30,41,59,.7)' : m.critical ? `rgba(244,63,94,${intensity.toFixed(2)})` : `rgba(56,189,248,${intensity.toFixed(2)})`;
      return `<button type="button" class="rounded-lg border border-slate-800 hover:border-slate-500 px-1.5 py-1.5 text-center transition-colors" style="background:${bg}" data-hz="month" data-arg="${esc(m.month)}" title="${esc(label)}: ${m.count} item${m.count === 1 ? '' : 's'}${m.critical ? `, ${m.critical} critical` : ''}">
        <div class="text-[10px] font-semibold ${m.count ? 'text-white' : 'text-slate-500'}">${esc(label)}</div>
        <div class="text-sm font-black tabular-nums ${m.count ? 'text-white' : 'text-slate-600'}">${m.count}</div>
      </button>`;
    }).join('');
  }

  function renderBuckets() {
    const h = state.horizon; const host = $('hz-buckets'); if (!h || !host) return;
    const b = h.buckets || {};
    host.innerHTML = BUCKET_META.map(([key, label, cls]) => {
      const n = b[key] ? b[key].count : 0; const active = state.bucketFilter === key;
      return `<button type="button" class="${cls} !normal-case !tracking-normal !text-[11px] !py-1 !px-2.5 gap-1.5 transition-all ${active ? 'ring-2 ring-white/60' : (n ? '' : 'opacity-40')}" data-hz="bucket" data-arg="${key}" aria-pressed="${active}" title="${active ? 'Clear filter' : 'Show only this bucket'}">${esc(label)} <strong class="mono">${n}</strong></button>`;
    }).join('') + (state.bucketFilter ? `<button type="button" class="btn btn-ghost btn-sm" data-hz="bucket" data-arg="${esc(state.bucketFilter)}"><i data-lucide="x" class="w-3 h-3"></i>Clear</button>` : '');
  }

  function countdown(e) {
    const n = e.days_remaining;
    if (n === null || n === undefined) return '<span class="badge badge-neutral">no date</span>';
    const cls = TONE_BADGE[e.tone] || 'badge badge-neutral';
    if (n === 0) return `<span class="${cls}">today</span>`;
    if (n < 0) return `<span class="${cls}">${e.bucket === 'history' ? `${-n} d ago` : `${-n} d overdue`}</span>`;
    return `<span class="${cls}">in ${n} d</span>`;
  }

  function flagFor(e) {
    if (e.country_code && /^[A-Za-z]{2}$/.test(e.country_code) && !['EU', 'AL'].includes(e.country_code.toUpperCase())) return GCM.ui.flag(e.country_code);
    const c = String(e.country || '');
    if (/european union|eu 27|\bEU\b/i.test(c)) return '🇪🇺';
    const hit = Object.values(GCM.state.countries || {}).find(x => x.name && c.toLowerCase().startsWith(x.name.toLowerCase()));
    return hit ? GCM.ui.flag(hit.code) : '🌐';
  }

  function eventRow(e) {
    const meta = TYPE_META[e.type] || { icon: 'circle', label: e.type, cls: 'text-slate-300 bg-slate-800 border-slate-700' };
    const dot = TONE_DOT[e.tone] || '#38bdf8';
    const pillar = e.pillar ? `<span class="${PILLAR_PILL[e.pillar] || 'badge badge-neutral'} !normal-case !tracking-normal">${esc(e.pillar)}</span>` : '';
    const products = e.product_count ? `<span class="pill gap-1" title="${esc((e.product_ids || []).join(', '))}"><i data-lucide="hard-drive" class="w-3 h-3"></i>${e.product_count} product${e.product_count === 1 ? '' : 's'}</span>` : '';
    const extra = e.type === 'milestone' && e.milestone_status ? `<span class="pill">${esc(e.milestone_status)}</span>` : e.type === 'alert_deadline' && e.triage ? `<span class="pill">triage: ${esc(e.triage)}</span>` : e.type === 'action_due' && e.action_status ? `<span class="pill">${esc(e.action_status)}</span>` : e.type === 'cert_expiry' && e.cert_status ? `<span class="pill">${esc(e.cert_status)}</span>` : '';
    const dateObj = new Date(e.date + 'T00:00:00');
    return `
      <div class="timeline-item" style="--dot:${dot}" data-month="${esc(e.date.slice(0, 7))}">
        <button type="button" class="w-full text-left rounded-xl border border-slate-800/80 bg-slate-900/50 hover:bg-slate-800/60 hover:border-slate-600 transition-colors px-3 py-2.5 ${e.bucket === 'history' ? 'opacity-70' : ''}" data-hz="open" data-idx="${e._idx}">
          <div class="flex items-start gap-3">
            <div class="shrink-0 w-12 text-center">
              <div class="text-[10px] uppercase font-bold text-slate-500">${MONTHS[dateObj.getMonth()]}</div>
              <div class="text-lg font-black text-white leading-none tabular-nums">${String(dateObj.getDate()).padStart(2, '0')}</div>
            </div>
            <div class="shrink-0 w-8 h-8 rounded-lg border flex items-center justify-center ${meta.cls}" title="${esc(meta.label)}"><i data-lucide="${meta.icon}" class="w-4 h-4"></i></div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 flex-wrap">
                ${countdown(e)}
                <span class="text-xs font-semibold text-white truncate max-w-full">${esc(e.title)}</span>
              </div>
              ${e.subtitle ? `<div class="text-[11px] text-slate-400 truncate mt-0.5">${esc(e.subtitle)}</div>` : ''}
              <div class="flex items-center gap-1.5 flex-wrap mt-1.5 text-[10px] text-slate-400">
                <span class="inline-flex items-center gap-1"><span class="text-sm leading-none">${flagFor(e)}</span>${esc(e.country || 'Global')}</span>
                ${pillar}${products}${extra}
              </div>
            </div>
            <i data-lucide="chevron-right" class="w-4 h-4 text-slate-600 shrink-0 mt-2"></i>
          </div>
        </button>
      </div>`;
  }

  function renderHorizon() {
    renderHeat(); renderBuckets(); renderKpis();
    const host = $('hz-timeline'); const h = state.horizon; if (!host || !h) return;
    (h.events || []).forEach((e, i) => { e._idx = i; });
    const events = visibleEvents();
    if (!events.length) {
      host.innerHTML = GCM.ui.empty(state.bucketFilter ? 'Nothing in this bucket for the current filters.' : 'No dated items match the current filters. Widen the range or enable more item types.', 'calendar-x');
      GCM.ui.icons(); return;
    }
    const today = h.today || new Date().toISOString().slice(0, 10);
    let html = '<div class="timeline">'; let curMonth = null; let todayPlaced = false;
    const todayMarker = `<div class="timeline-item" style="--dot:#ffffff"><div class="flex items-center gap-2 -mt-1 mb-1"><span class="badge badge-neutral !bg-white !text-slate-900 !border-white">Today</span><span class="text-[11px] text-slate-400">${esc(GCM.ui.fmtDate(today))}</span><span class="flex-1 h-px bg-gradient-to-r from-slate-500 to-transparent"></span></div></div>`;
    events.forEach(e => {
      if (!todayPlaced && e.date >= today) { html += todayMarker; todayPlaced = true; curMonth = null; }
      const mk = e.date.slice(0, 7);
      if (mk !== curMonth) {
        curMonth = mk; const [y, m] = mk.split('-'); const n = events.filter(x => x.date.slice(0, 7) === mk).length;
        html += `<div class="flex items-center gap-2 mb-2 mt-1" id="hz-month-${mk}"><span class="section-title">${MONTHS[+m - 1]} ${y}</span><span class="pill">${n}</span><span class="flex-1 h-px bg-slate-800"></span></div>`;
      }
      html += eventRow(e);
    });
    if (!todayPlaced) html += todayMarker;
    html += '</div>';
    host.innerHTML = html;
    GCM.ui.icons();
  }

  function openEvent(e) {
    if (!e) return;
    switch (e.type) {
      case 'alert_deadline': case 'milestone': GCM.deeplink.alert(e.ref_id); break;
      case 'cert_expiry': if (e.product_ids && e.product_ids[0]) GCM.deeplink.product(e.product_ids[0]); else GCM.tabs.switchTo('portfolio'); break;
      case 'action_due':
        if (e.linked_type === 'product' && e.linked_id) GCM.deeplink.product(e.linked_id);
        else if (e.linked_type === 'alert' && e.linked_id) GCM.deeplink.alert(e.linked_id);
        else if (e.linked_type === 'country' && e.linked_id) GCM.deeplink.country(e.linked_id);
        else { GCM.bus.emit('actions:focus', e.ref_id); GCM.bus.emit('actions:open', e.ref_id); }
        break;
      case 'surveillance':
        if (e.alert_id && (state.summary && state.summary.top_risks || []).some(t => t.ref_id === e.alert_id)) GCM.deeplink.alert(e.alert_id);
        else GCM.bus.emit('surveillance:log', e.ref_id);
        break;
      default: break;
    }
  }

  /* ------------------------------------------------------------------ breakdown */
  function renderBreakdown() {
    const s = state.summary; if (!s) return;
    // products
    const prods = s.per_product || [];
    $('hz-products').innerHTML = prods.length ? prods.map((p, i) => {
      const g = p.grade || 'A';
      const drivers = (p.drivers || []).map(d => `<li class="flex items-start gap-2"><span class="mono text-slate-500 w-10 shrink-0 text-right">+${esc(d.score)}</span><span class="${GCM.ui.severityClass(d.severity)} !normal-case !tracking-normal shrink-0">${esc(d.kind)}</span><span class="text-slate-300">${esc(d.label)}</span></li>`).join('');
      return `<details class="group rounded-xl border border-slate-800/80 bg-slate-900/40 hover:border-slate-600 transition-colors">
        <summary class="list-none cursor-pointer px-3 py-2.5 select-none">
          <div class="flex items-center gap-3">
            <span class="mono text-[10px] text-slate-500 w-4 text-right">${i + 1}</span>
            <div class="min-w-0 flex-1">
              <div class="flex items-center justify-between gap-2">
                <button type="button" class="text-xs font-semibold text-white hover:text-sky-300 truncate text-left" data-hz="product" data-arg="${esc(p.id)}" title="Open in portfolio">${esc(p.name)}</button>
                <div class="flex items-center gap-1.5 shrink-0"><span class="${GRADE_BADGE[g]}">${g}</span><span class="text-sm font-black tabular-nums" style="color:${GRADE_COLOR[g]}">${esc(Math.round(p.risk_score))}</span></div>
              </div>
              <div class="progress mt-1.5 !h-2"><div class="progress-bar ${GRADE_BAR[g]}" style="width:${Math.max(2, Math.min(100, p.risk_score))}%"></div></div>
              <div class="flex items-center gap-1.5 flex-wrap mt-1.5 text-[10px] text-slate-400">
                <span class="mono">${esc(p.sku)}</span>
                <span class="pill">${esc(p.open_alerts)} open</span>
                ${p.critical_alerts ? `<span class="badge badge-critical">${esc(p.critical_alerts)} critical</span>` : ''}
                ${p.overdue_alerts ? `<span class="badge badge-warning">${esc(p.overdue_alerts)} overdue</span>` : ''}
                <span class="pill ${p.cert_health === 'Expired' ? '!text-rose-300 !border-rose-800' : p.cert_health === 'Critical' || p.cert_health === 'Expiring Soon' ? '!text-amber-300 !border-amber-800' : ''}">certs: ${esc(p.cert_health)}</span>
                ${p.next_deadline ? `<span class="pill" title="${esc(p.next_deadline_label || '')}">next: ${esc(GCM.ui.fmtDate(p.next_deadline))} (${esc(GCM.ui.relDays(p.next_deadline))})</span>` : ''}
              </div>
            </div>
            <i data-lucide="chevron-down" class="w-4 h-4 text-slate-600 group-open:rotate-180 transition-transform shrink-0"></i>
          </div>
        </summary>
        <div class="px-3 pb-3 pt-1 border-t border-slate-800/80 text-[11px]">
          <div class="section-title mb-1.5">Top drivers <span class="text-slate-600 normal-case tracking-normal font-normal">· raw score ${esc(p.raw_score)} → ${esc(p.risk_score)} after soft cap</span></div>
          <ul class="space-y-1">${drivers || '<li class="text-slate-500">No open alerts or certificate issues touch this product.</li>'}</ul>
          <div class="mt-2 flex gap-2"><button type="button" class="btn btn-secondary btn-sm" data-hz="product" data-arg="${esc(p.id)}"><i data-lucide="hard-drive" class="w-3.5 h-3.5"></i>Open product</button><button type="button" class="btn btn-ghost btn-sm" data-hz="filter-product" data-arg="${esc(p.id)}"><i data-lucide="filter" class="w-3.5 h-3.5"></i>Filter horizon</button></div>
        </div>
      </details>`;
    }).join('') : GCM.ui.empty('No products in the portfolio yet.', 'hard-drive');

    // regions
    const regions = s.per_region || [];
    $('hz-regions').innerHTML = regions.length ? regions.map(r => {
      const g = r.grade || 'A';
      return `<button type="button" class="text-left rounded-xl border border-slate-800 bg-slate-900/50 hover:border-cyan-600/60 transition-colors p-3 relative overflow-hidden" data-hz="region" data-arg="${esc(r.region)}" title="Open the Global Access Map">
        <div class="absolute inset-x-0 bottom-0 h-1 ${GRADE_BAR[g]}" style="width:${Math.max(3, r.risk_score)}%"></div>
        <div class="flex items-start justify-between gap-2">
          <div class="text-xs font-semibold text-white leading-snug">${esc(r.region)}</div>
          <div class="text-right shrink-0"><div class="text-xl font-black tabular-nums leading-none" style="color:${GRADE_COLOR[g]}">${esc(Math.round(r.risk_score))}</div><div class="text-[10px] text-slate-500">grade ${g}</div></div>
        </div>
        <div class="grid grid-cols-3 gap-1 mt-2 text-[10px] text-slate-400">
          <div><div class="text-white font-bold text-sm tabular-nums">${esc(r.alerts)}</div>alerts${r.critical_alerts ? ` <span class="text-rose-300">(${esc(r.critical_alerts)} crit.)</span>` : ''}</div>
          <div><div class="text-white font-bold text-sm tabular-nums">${esc(r.markets)}</div>your markets</div>
          <div><div class="${r.in_country_testing_markets ? 'text-amber-300' : 'text-white'} font-bold text-sm tabular-nums">${esc(r.in_country_testing_markets)}</div>in-country testing</div>
        </div>
        <div class="mt-2 flex flex-wrap gap-1">${(r.market_codes || []).slice(0, 12).map(c => `<span class="text-sm leading-none" title="${esc((GCM.state.countries[c] || {}).name || c)}">${GCM.ui.flag(c)}</span>`).join('')}${(r.market_codes || []).length > 12 ? `<span class="pill">+${r.market_codes.length - 12}</span>` : ''}</div>
      </button>`;
    }).join('') : GCM.ui.empty('No regional data.', 'globe-2');

    // pillars
    const pillars = s.per_pillar || [];
    $('hz-pillars').innerHTML = pillars.map(p => {
      const active = state.pillar === p.pillar;
      return `<button type="button" class="rounded-xl border px-3 py-2 text-left transition-colors ${PILLAR_CHIP[p.pillar] || 'border-slate-700 bg-slate-800/40 text-slate-200'} ${active ? 'ring-2 ring-white/60' : ''} ${p.alerts ? '' : 'opacity-50'}" data-hz="pillar" data-arg="${esc(p.pillar)}" aria-pressed="${active}">
        <div class="flex items-center gap-2"><i data-lucide="${PILLAR_ICON[p.pillar] || 'circle'}" class="w-4 h-4"></i><span class="text-xs font-bold">${esc(p.pillar === 'All' ? 'Multi-pillar' : p.pillar)}</span><span class="text-lg font-black tabular-nums ml-1">${esc(Math.round(p.risk_score))}</span></div>
        <div class="text-[10px] opacity-80 mt-0.5">${esc(p.alerts)} alert${p.alerts === 1 ? '' : 's'}${p.critical ? ` · ${esc(p.critical)} critical` : ''} · ${esc(p.products_impacted)} product${p.products_impacted === 1 ? '' : 's'}</div>
      </button>`;
    }).join('');

    // top risks
    const top = s.top_risks || [];
    $('hz-top-count').textContent = `${top.length} ranked`;
    $('hz-top-risks').innerHTML = top.length ? top.map((t, i) => {
      const refIcon = { alert: 'bell', certificate: 'file-badge', product: 'hard-drive', action: 'check-square', country: 'globe', document: 'file-text' }[t.ref_type] || 'circle';
      const dueTxt = t.due && GCM.ui.daysUntil(t.due) !== null ? `${GCM.ui.fmtDate(t.due)} · ${GCM.ui.relDays(t.due)}` : (t.due || 'no date');
      const actionTitle = t.ref_type === 'certificate' ? `Renew ${t.title.replace(/^(Expired|Renewal due): /, '')}` : t.ref_type === 'alert' ? `Close gap: ${t.title}` : t.title.replace(/^Overdue action: /, '');
      const due = t.due && GCM.ui.daysUntil(t.due) !== null && GCM.ui.daysUntil(t.due) > 0 ? t.due : '';
      return `<div class="flex items-start gap-3 py-2.5">
        <div class="shrink-0 w-9 text-center"><div class="text-lg font-black tabular-nums" style="color:${t.score >= 75 ? '#f43f5e' : t.score >= 50 ? '#f59e0b' : '#38bdf8'}">${esc(Math.round(t.score))}</div><div class="text-[9px] uppercase text-slate-500">#${i + 1}</div></div>
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="${GCM.ui.severityClass(t.severity)}">${esc(t.severity)}</span>
            <span class="pill gap-1"><i data-lucide="${refIcon}" class="w-3 h-3"></i>${esc(t.ref_type)}</span>
            ${t.pillar ? `<span class="${PILLAR_PILL[t.pillar] || 'badge badge-neutral'} !normal-case !tracking-normal">${esc(t.pillar)}</span>` : ''}
            <button type="button" class="text-xs font-semibold text-white hover:text-sky-300 text-left" data-hz="open-ref" data-ref-type="${esc(t.ref_type)}" data-ref-id="${esc(t.ref_id)}" data-pid="${esc((t.product_ids || [])[0] || '')}">${esc(t.title)}</button>
          </div>
          <div class="text-[11px] text-slate-400 mt-1">${esc(t.reason)}${t.country ? ` · ${esc(t.country)}` : ''} · due ${esc(dueTxt)}</div>
        </div>
        <button type="button" class="btn btn-secondary btn-sm shrink-0" data-hz="create-action" data-ref-type="${esc(t.ref_type)}" data-ref-id="${esc(t.ref_id)}" data-title="${esc(actionTitle)}" data-priority="${esc(t.severity === 'Critical' ? 'Critical' : t.severity === 'Warning' ? 'High' : 'Medium')}" data-due="${esc(due)}" data-notes="${esc(t.reason)}"><i data-lucide="plus-square" class="w-3.5 h-3.5"></i>Create action</button>
      </div>`;
    }).join('') : GCM.ui.empty('Nothing is driving risk right now. Nice.', 'party-popper');
    GCM.ui.icons();
  }

  /* ------------------------------------------------------------------ interaction */
  function syncTypeButtons() {
    document.querySelectorAll('[data-hz="type"]').forEach(b => {
      const on = state.types.has(b.dataset.type);
      b.setAttribute('aria-pressed', String(on)); b.classList.toggle('opacity-50', !on);
    });
    const hb = document.querySelector('[data-hz="history"]');
    if (hb) { hb.setAttribute('aria-pressed', String(state.showHistory)); hb.classList.toggle('opacity-50', !state.showHistory); }
    document.querySelectorAll('[data-hz="range"]').forEach(b => b.classList.toggle('active', Number(b.dataset.days) === state.days));
  }

  function onClick(e) {
    const el = e.target.closest('[data-hz]'); if (!el || !$('horizon-root').contains(el)) return;
    const kind = el.dataset.hz; const arg = el.dataset.arg;
    switch (kind) {
      case 'toggle-formula': { const f = $('hz-formula'); f.classList.toggle('hidden'); GCM.ui.icons(); break; }
      case 'range': state.days = Number(el.dataset.days) || 0; syncTypeButtons(); loadHorizonOnly(); break;
      case 'type': {
        const t = el.dataset.type;
        if (state.types.has(t)) state.types.delete(t); else state.types.add(t);
        if (t === 'surveillance' && state.types.has(t)) state.showHistory = true;
        syncTypeButtons(); loadHorizonOnly(); break;
      }
      case 'history': state.showHistory = !state.showHistory; syncTypeButtons(); renderHorizon(); break;
      case 'bucket': state.bucketFilter = state.bucketFilter === arg ? null : arg; if (arg === 'history' && state.bucketFilter) state.showHistory = true; syncTypeButtons(); renderHorizon(); break;
      case 'kpi-bucket': state.bucketFilter = arg; if (arg === 'overdue') state.showHistory = false; renderHorizon(); $('hz-timeline-card').scrollIntoView({ behavior: 'smooth', block: 'start' }); break;
      case 'kpi-tab': GCM.tabs.switchTo(arg); break;
      case 'month': { const target = $(`hz-month-${arg}`); if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' }); else GCM.ui.toast('Quiet month', 'No items scheduled for that month under the current filters.', 'info'); break; }
      case 'open': openEvent((state.horizon.events || [])[Number(el.dataset.idx)]); break;
      case 'export': GCM.api.download(`/api/horizon/export.csv?${horizonQuery()}`, 'Exporting regulatory horizon'); break;
      case 'product': GCM.deeplink.product(arg); break;
      case 'filter-product': state.product = arg; renderProductFilter(); loadHorizonOnly(); $('hz-timeline-card').scrollIntoView({ behavior: 'smooth', block: 'start' }); break;
      case 'region': GCM.tabs.switchTo('map'); break;
      case 'pillar': state.pillar = state.pillar === arg ? '' : arg; $('hz-pillar').value = state.pillar; renderBreakdown(); loadHorizonOnly(); break;
      case 'open-ref': {
        const rt = el.dataset.refType; const rid = el.dataset.refId;
        if (rt === 'alert') GCM.deeplink.alert(rid);
        else if (rt === 'product') GCM.deeplink.product(rid);
        else if (rt === 'country') GCM.deeplink.country(rid);
        else if (rt === 'certificate') { if (el.dataset.pid) GCM.deeplink.product(el.dataset.pid); else GCM.tabs.switchTo('portfolio'); }
        else if (rt === 'document') GCM.deeplink.document(rid);
        else { GCM.bus.emit('actions:focus', rid); GCM.bus.emit('actions:open', rid); }
        break;
      }
      case 'create-action':
        GCM.actions.createFor(el.dataset.refType, el.dataset.refId, { title: el.dataset.title, priority: el.dataset.priority, due_date: el.dataset.due, notes: el.dataset.notes });
        break;
      default: break;
    }
  }

  /* ------------------------------------------------------------------ module */
  GCM.modules.horizon = {
    init() {
      document.addEventListener('click', onClick);
      const pillarSel = $('hz-pillar'); if (pillarSel) pillarSel.addEventListener('change', () => { state.pillar = pillarSel.value; renderBreakdown(); loadHorizonOnly(); });
      const prodSel = $('hz-product'); if (prodSel) prodSel.addEventListener('change', () => { state.product = prodSel.value; loadHorizonOnly(); });
      ['alerts:changed', 'actions:changed', 'products:changed', 'audit:completed', 'countries:changed'].forEach(evt => GCM.bus.on(evt, scheduleRefresh));
      GCM.bus.on('horizon:filter', (payload = {}) => {
        if (payload.product_id !== undefined) state.product = payload.product_id || '';
        if (payload.pillar !== undefined) state.pillar = payload.pillar || '';
        if (payload.days !== undefined) state.days = Number(payload.days) || 0;
        syncTypeButtons(); if (state.loaded) { renderProductFilter(); loadHorizonOnly(); }
      });
      GCM.palette.register({ label: 'Export regulatory horizon (CSV)', icon: 'download', keywords: ['horizon', 'csv', 'export', 'deadline', 'timeline'], run: () => GCM.api.download(`/api/horizon/export.csv?${horizonQuery()}`, 'Exporting regulatory horizon') });
      GCM.palette.register({ label: 'How is the Compliance Risk Index calculated?', icon: 'calculator', keywords: ['risk', 'index', 'formula', 'score', 'grade'], run: () => { GCM.tabs.switchTo('horizon'); setTimeout(() => { $('hz-formula').classList.remove('hidden'); $('hz-index-card').scrollIntoView({ behavior: 'smooth' }); GCM.ui.icons(); }, 150); } });
      GCM.palette.register({ label: 'Show overdue compliance items', icon: 'alarm-clock-off', keywords: ['overdue', 'late', 'deadline', 'horizon'], run: () => { GCM.tabs.switchTo('horizon'); state.bucketFilter = 'overdue'; if (state.loaded) renderHorizon(); } });
      syncTypeButtons();
    },
    onFirstShow() { loadAll(); },
    onShow() { if (state.loaded && !state.loading) scheduleRefresh(); GCM.ui.icons(); },
    refresh: loadAll,
  };
})();
