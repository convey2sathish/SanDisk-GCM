/* overview.js - executive command centre */
(function () {
  'use strict';
  const GCM = window.GCM;
  const $ = (id) => document.getElementById(id);
  const PILLAR_STYLE = { Safety: ['bg-rose-500', 'text-rose-300'], EMC: ['bg-sky-500', 'text-sky-300'], Environmental: ['bg-emerald-500', 'text-emerald-300'], Cyber: ['bg-indigo-500', 'text-indigo-300'], All: ['bg-purple-500', 'text-purple-300'] };
  let timer = null; let overdueActions = 0; let overdueHorizon = 0;
  function renderOverdue() { const el = $('ov-overdue'); if (el) el.textContent = `${overdueActions} actions, ${overdueHorizon} horizon`; }

  function setText(id, v) { const el = $(id); if (el) el.textContent = (v === null || v === undefined) ? '—' : v; }

  async function loadOverview() {
    try {
      const d = await GCM.api.get('/api/overview');
      setText('ov-company', d.company); setText('ov-updated', GCM.ui.fmtDateTime(d.generated_at));
      setText('ov-countries', d.total_countries); setText('hdr-countries', d.total_countries); setText('ov-in-country', d.in_country_testing_markets);
      setText('ov-alerts', d.active_alerts_count); setText('ov-critical', d.critical_alerts_count); setText('ov-warning', d.warning_alerts_count);
      setText('ov-products', d.total_products); setText('ov-certs', d.total_certificates); setText('ov-expiring', d.expiring_certificates_count);
      setText('ov-actions', d.open_actions_count); overdueActions = d.overdue_actions_count || 0; renderOverdue();
      const badge = $('badge-alert-count'); if (badge) badge.textContent = d.active_alerts_count;
      const tri = d.triage_counts || {}; setText('ov-triage', `${tri.New || 0} new · ${tri['In Progress'] || 0} in progress · ${tri.Closed || 0} closed`);
      // pillars
      const total = Object.values(d.pillar_counts || {}).reduce((a, b) => a + b, 0) || 1;
      $('ov-pillars').innerHTML = Object.entries(d.pillar_counts || {}).sort((a, b) => b[1] - a[1]).map(([p, n]) => {
        const [bar, txt] = PILLAR_STYLE[p] || ['bg-slate-500', 'text-slate-300'];
        return `<button class="w-full text-left group" data-action="alerts-pillar" data-arg="${GCM.ui.esc(p)}"><div class="flex items-center justify-between text-xs"><span class="font-medium ${txt}">${GCM.ui.esc(p)}</span><span class="text-slate-400"><strong class="text-white">${n}</strong> alerts</span></div><div class="progress mt-1"><div class="progress-bar ${bar}" style="width:${Math.round(n / total * 100)}%"></div></div></button>`;
      }).join('') || GCM.ui.empty('No alerts');
      // regions
      const regions = Object.entries(d.regions_count || {}).sort((a, b) => b[1] - a[1]);
      setText('ov-regions-total', `${d.total_countries} jurisdictions`);
      $('ov-regions').innerHTML = regions.map(([r, n]) => `<div><div class="flex items-center justify-between text-xs"><span class="text-slate-300">${GCM.ui.esc(r)}</span><span class="font-bold text-sky-400">${n}</span></div><div class="progress mt-1"><div class="progress-bar" style="width:${Math.round(n / d.total_countries * 100)}%"></div></div></div>`).join('');
      // recent alerts
      $('ov-recent').innerHTML = (d.recent_alerts || []).map(a => `
        <button class="text-left p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 hover:border-sky-500/60 hover:bg-slate-800 transition group" data-action="deeplink-alert" data-arg="${GCM.ui.esc(a.id)}">
          <div class="flex items-center justify-between gap-2"><div class="flex items-center gap-2">${GCM.ui.badge(a.severity, a.severity)}<span class="pill">${GCM.ui.esc(a.pillar || '')}</span></div><span class="text-[11px] text-slate-400 truncate max-w-[45%]">${GCM.ui.esc(a.country)}</span></div>
          <div class="font-bold text-white text-xs leading-snug mt-2 group-hover:text-sky-300 transition-colors">${GCM.ui.esc(a.title)}</div>
          <p class="text-slate-400 text-[11px] line-clamp-2 leading-relaxed mt-1">${GCM.ui.esc(a.summary)}</p>
          <div class="pt-2 mt-2 border-t border-slate-700/50 flex items-center justify-between text-[10px]"><span class="text-slate-500 mono truncate max-w-[55%]">${GCM.ui.esc(a.standard)}</span><span class="${GCM.ui.deadlineTone(a.effective_date) === 'critical' ? 'text-rose-300' : GCM.ui.deadlineTone(a.effective_date) === 'warning' ? 'text-amber-300' : 'text-sky-300'} font-semibold">${a.effective_date ? `${GCM.ui.fmtDate(a.effective_date)} · ${GCM.ui.relDays(a.effective_date)}` : ''}</span></div>
        </button>`).join('') || GCM.ui.empty('No alerts yet');
      GCM.ui.icons();
    } catch (e) { console.error('overview', e); GCM.ui.toast('Overview failed to load', e.message, 'error'); }
  }

  async function loadRisk() {
    try {
      const r = await GCM.api.get('/api/risk/summary');
      const idx = Math.round(r.compliance_risk_index ?? 0);
      const el = $('ov-risk'); el.textContent = `${idx}`; el.className = `kpi-value ${idx >= 70 ? 'text-rose-400' : idx >= 40 ? 'text-amber-300' : 'text-emerald-400'}`;
      const sub = $('ov-risk-sub'); sub.textContent = `Grade ${r.grade || '—'} · 0 = no exposure, 100 = maximum`; sub.title = r.trend_note || '';
    } catch (e) { setText('ov-risk', '—'); setText('ov-risk-sub', 'Risk engine unavailable'); }
  }

  async function loadHorizon() {
    try {
      const h = await GCM.api.get('/api/horizon?days=90');
      const b = h.buckets || {};
      const cnt = (x) => (x && typeof x === 'object') ? (x.count ?? (Array.isArray(x.ids) ? x.ids.length : 0)) : (x || 0);
      setText('ov-due90', cnt(b.next_30) + cnt(b.next_90));
      overdueHorizon = cnt(b.overdue); renderOverdue();
      const items = (h.events || []).filter(e => e.type !== 'surveillance' && e.bucket !== 'history' && e.actionable !== false && e.closed !== true
        && (e.days_remaining === null || e.days_remaining === undefined || e.days_remaining <= 120)).slice(0, 8);
      $('ov-attention').innerHTML = items.length ? items.map(e => {
        const tone = e.days_remaining < 0 ? 'critical' : e.days_remaining <= 30 ? 'critical' : e.days_remaining <= 90 ? 'warning' : 'info';
        const icon = { alert_deadline: 'bell', milestone: 'milestone', cert_expiry: 'badge-check', action_due: 'check-square' }[e.type] || 'calendar';
        const act = e.ref_type === 'alert' ? 'deeplink-alert' : e.ref_type === 'product' ? 'deeplink-product' : e.ref_type === 'certificate' ? 'tab' : 'tab';
        const arg = e.ref_type === 'alert' || e.ref_type === 'product' ? e.ref_id : (e.ref_type === 'certificate' ? 'portfolio' : 'horizon');
        return `<button class="w-full text-left flex items-center gap-3 p-3 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-slate-600 transition" data-action="${act}" data-arg="${GCM.ui.esc(arg)}">
          <div class="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center shrink-0"><i data-lucide="${icon}" class="w-4 h-4 ${tone === 'critical' ? 'text-rose-400' : tone === 'warning' ? 'text-amber-400' : 'text-sky-400'}"></i></div>
          <div class="flex-1 min-w-0"><div class="text-xs font-semibold text-white truncate">${GCM.ui.esc(e.title)}</div><div class="text-[11px] text-slate-400 truncate">${GCM.ui.esc((e.type || '').replace(/_/g, ' '))}${e.country ? ` · ${GCM.ui.flag(e.country_code || '')} ${GCM.ui.esc(e.country)}` : ''}${e.pillar ? ` · ${GCM.ui.esc(e.pillar)}` : ''}${(e.product_ids || []).length ? ` · ${e.product_ids.length} products` : ''}</div></div>
          <div class="text-right shrink-0"><div class="text-[11px] mono text-slate-300">${GCM.ui.fmtDate(e.date)}</div><span class="badge badge-${tone}">${e.days_remaining < 0 ? `${-e.days_remaining}d overdue` : e.days_remaining === 0 ? 'today' : `${e.days_remaining}d left`}</span></div>
        </button>`;
      }).join('') : GCM.ui.empty('Nothing due in the next 120 days. Great position.', 'party-popper');
      GCM.ui.icons();
    } catch (e) { $('ov-attention').innerHTML = GCM.ui.empty('Horizon unavailable', 'radar'); setText('ov-due90', '—'); GCM.ui.icons(); }
  }

  async function loadActions() {
    await GCM.actionsPanel.load();
    const f = $('ov-actions-filter')?.value || 'open';
    GCM.actionsPanel.render($('ov-actions-list'), f === 'open' ? { showDone: false } : f === 'all' ? { showDone: true } : { filter: f });
  }

  function refreshAll() { clearTimeout(timer); timer = setTimeout(() => { loadOverview(); loadRisk(); loadHorizon(); loadActions(); }, 150); }

  GCM.modules.overview = {
    init() {
      GCM.bus.on('alerts:changed', refreshAll); GCM.bus.on('actions:changed', () => loadActions()); GCM.bus.on('products:changed', refreshAll);
      GCM.bus.on('audit:completed', refreshAll); GCM.bus.on('countries:changed', refreshAll);
      GCM.bus.on('action:matrix-export', () => GCM.bus.emit('matrix:export', false));
      GCM.bus.on('action:alerts-pillar', ({ arg }) => { GCM.tabs.switchTo('alerts'); GCM.bus.emit('alerts:filter', { pillar: arg }); });
      $('ov-actions-filter')?.addEventListener('change', loadActions);
    },
    onFirstShow() { loadOverview(); loadRisk(); loadHorizon(); loadActions(); },
    onShow() { if (GCM.state.ready) { loadRisk(); loadHorizon(); } },
    refresh: refreshAll,
  };
})();
