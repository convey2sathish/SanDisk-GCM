/* map.js - jsVectorMap world map with compliance heat layers + country dossier */
(function () {
  'use strict';
  const GCM = window.GCM;
  const $ = (id) => document.getElementById(id);
  let mapInst = null; let alerts = []; let selected = 'US'; let markers = []; let colorMap = {};
  const QUICK = ['US', 'DE', 'IN', 'CN', 'JP', 'KR', 'SG', 'BR', 'SA', 'GB'];
  const FOCUS = { americas: ['US', 'CA', 'MX', 'BR', 'AR', 'CL'], europe: ['DE', 'FR', 'GB', 'IT', 'ES', 'PL', 'SE'], asia: ['CN', 'IN', 'JP', 'KR', 'AU', 'SG', 'ID'], middle_east: ['SA', 'AE', 'ZA', 'EG', 'IL', 'TR', 'NG', 'KE'] };

  const countries = () => GCM.state.countries;
  const prodId = () => $('map-product-select')?.value || 'external_ssd_bus';

  async function loadMarkers() {
    try {
      const m = await GCM.api.get('/static/js/vendor/island_markers.json');
      markers = Object.entries(m).map(([code, v]) => ({ code, name: `${v.name} (${code})`, coords: v.coords }));
    } catch (_) { markers = []; }
  }

  async function loadAlerts() { try { alerts = await GCM.api.get('/api/alerts'); } catch (_) { alerts = []; } }

  function alertsFor(code) {
    const c = countries()[code]; if (!c) return [];
    const pid = prodId();
    return alerts.filter(a => {
      const cats = a.affected_categories || [];
      const catOk = !cats.length || cats.includes(pid) || cats.some(x => ['all', 'all_storage_categories', 'all_categories'].includes(x));
      if (!catOk) return false;
      const codes = a.market_codes || null;
      if (codes) return codes.includes(code);
      const cc = String(a.country_code || '').toUpperCase(); const cl = String(a.country || '').toLowerCase(); const rl = String(a.region || '').toLowerCase();
      if (['ALL', 'GLOBAL', 'WORLDWIDE'].includes(cc) || cl.startsWith('all 205')) return true;
      if (cc && cc.length === 2) return cc === code;
      if (cl.includes('european union') || cc === 'EU') return (c.bloc || '').includes('EU');
      if (cl.includes('iecee') || cl.includes('cb scheme')) return !!c.cb_scheme_accepted;
      if (cl.includes(c.name.toLowerCase())) return true;
      return rl && rl !== 'global' && (c.region || '').toLowerCase().includes(rl.split(' ')[0]);
    });
  }

  function statusFor(code) {
    const c = countries()[code]; if (!c) return { status: 'Certified', color: '#10b981', tone: 'success' };
    const list = alertsFor(code);
    if (list.some(a => a.severity === 'Critical')) return { status: 'Action required (critical alert)', color: '#f43f5e', tone: 'critical', alerts: list };
    if (list.some(a => a.severity === 'Warning')) return { status: 'Review required (warning)', color: '#f59e0b', tone: 'warning', alerts: list };
    if ((c.transitions || []).length) return { status: 'Standard transition pending', color: '#818cf8', tone: 'info', alerts: list };
    return { status: 'Certified / market ready', color: '#10b981', tone: 'success', alerts: list };
  }

  function computeColors(metric) {
    const cm = {}; const k = { a: 0, b: 0, c: 0, d: 0 };
    for (const [code, c] of Object.entries(countries())) {
      let color = '#1e293b';
      if (metric === 'readiness') {
        const s = statusFor(code); color = s.color; if (s.tone === 'critical') k.c++; else if (s.tone === 'warning' || s.tone === 'info') k.b++; else k.a++; if (c.in_country_testing) k.d++;
      } else if (metric === 'testing_barrier') {
        if (c.in_country_testing) { color = '#f43f5e'; k.a++; } else { color = '#10b981'; k.b++; } if (c.local_rep_required) k.c++; if (c.cb_scheme_accepted) k.d++;
      } else if (metric === 'lead_time') {
        const w = c.lead_time_weeks || 4; if (w < 4) { color = '#10b981'; k.a++; } else if (w <= 8) { color = '#0284c7'; k.b++; } else if (w <= 12) { color = '#f59e0b'; k.c++; } else { color = '#a855f7'; k.d++; }
      } else if (metric === 'environmental') {
        const p = (c.pfas_std || '').toLowerCase(), pk = (c.packaging_std || '').toLowerCase(), r = (c.rohs_std || '').toLowerCase();
        if (/tsca|ban|annex xv|cscl class i|restriction/.test(p) && !/aligned\)/.test(p)) { color = '#059669'; k.a++; }
        else if (/triman|verpackg|plastic|116\/2020|ppwr|agec|conai/.test(pk)) { color = '#0891b2'; k.b++; }
        else if (/china rohs|saso|bsmi|k-reach|eaeu|cns 15663|sj\/t/.test(r)) { color = '#d97706'; k.c++; }
        else { color = '#334155'; k.d++; }
      } else if (metric === 'alerts') {
        const list = alertsFor(code);
        if (list.some(a => a.severity === 'Critical')) { color = '#f43f5e'; k.a++; } else if (list.some(a => a.severity === 'Warning')) { color = '#f59e0b'; k.b++; } else if (list.length) { color = '#38bdf8'; k.c++; } else { k.d++; }
      } else if (metric === 'transitions') {
        const tr = c.transitions || [];
        if (!tr.length) { color = '#1e293b'; k.d++; } else { const soonest = Math.min(...tr.map(t => GCM.ui.daysUntil(t.deadline) ?? 9999)); if (soonest < 180) { color = '#f43f5e'; k.a++; } else if (soonest < 365) { color = '#f59e0b'; k.b++; } else { color = '#818cf8'; k.c++; } }
      }
      cm[code] = color;
    }
    return { cm, k };
  }

  const KPI = {
    readiness: [['Certified & market ready', 'check-circle-2', 'text-emerald-400'], ['Review / transition pending', 'clock', 'text-amber-400'], ['Critical alert action', 'alert-triangle', 'text-rose-400'], ['In-country lab barrier', 'flask-conical', 'text-cyan-400']],
    testing_barrier: [['Mandatory local lab', 'shield-alert', 'text-rose-400'], ['CB / DoC accepted', 'shield-check', 'text-emerald-400'], ['Local rep mandate', 'user-check', 'text-amber-400'], ['CB Scheme recognised', 'globe', 'text-sky-400']],
    lead_time: [['Fast track (<4 wks)', 'zap', 'text-emerald-400'], ['Standard (4-8 wks)', 'calendar', 'text-sky-400'], ['Extended (8-12 wks)', 'hourglass', 'text-amber-400'], ['Critical path (>12 wks)', 'alert-octagon', 'text-purple-400']],
    environmental: [['PFAS mandates & bans', 'leaf', 'text-emerald-400'], ['Packaging & plastics laws', 'package', 'text-cyan-400'], ['Dedicated RoHS regimes', 'test-tube-2', 'text-amber-400'], ['Baseline environmental', 'globe-2', 'text-slate-400']],
    alerts: [['Critical alerts', 'flame', 'text-rose-400'], ['Warning notices', 'alert-circle', 'text-amber-400'], ['Informational', 'info', 'text-sky-400'], ['No active alerts', 'check', 'text-emerald-400']],
    transitions: [['Cutover < 180 days', 'alarm-clock', 'text-rose-400'], ['Cutover < 1 year', 'calendar-clock', 'text-amber-400'], ['Cutover later', 'git-branch', 'text-indigo-400'], ['No pending transition', 'check', 'text-emerald-400']],
  };
  const LEGEND = {
    readiness: [['bg-emerald-500', 'Certified / compliant'], ['bg-amber-500', 'Warning or transition pending'], ['bg-rose-500', 'Critical alert – action required']],
    testing_barrier: [['bg-rose-500', 'Mandatory in-country lab testing'], ['bg-emerald-500', 'CB Scheme / SDoC accepted']],
    lead_time: [['bg-emerald-500', '< 4 weeks'], ['bg-sky-600', '4 – 8 weeks'], ['bg-amber-500', '8 – 12 weeks'], ['bg-purple-500', '> 12 weeks']],
    environmental: [['bg-emerald-600', 'PFAS bans & TSCA reporting'], ['bg-cyan-600', 'Packaging (Triman, AGEC, PPWR)'], ['bg-amber-600', 'Dedicated RoHS marks'], ['bg-slate-600', 'International baseline']],
    alerts: [['bg-rose-500', 'Critical'], ['bg-amber-500', 'Warning'], ['bg-sky-500', 'Informational'], ['bg-slate-700', 'None']],
    transitions: [['bg-rose-500', 'Cutover < 180 days'], ['bg-amber-500', 'Cutover < 1 year'], ['bg-indigo-400', 'Cutover later'], ['bg-slate-700', 'None recorded']],
  };

  function render() {
    if (!mapInst) return;
    const metric = $('map-metric-select')?.value || 'readiness';
    const { cm, k } = computeColors(metric); colorMap = cm;
    for (const [code, color] of Object.entries(cm)) { const p = document.querySelector(`.jvm-region[data-code="${code}"]`); if (p) { p.setAttribute('fill', color); p.style.fill = color; } }
    markers.forEach((m, i) => { const c = document.querySelector(`.jvm-marker[data-index="${i}"]`); const col = cm[m.code] || '#38bdf8'; if (c) { c.setAttribute('fill', col); c.style.fill = col; } });
    const vals = [k.a, k.b, k.c, k.d];
    $('map-kpi-bar').innerHTML = KPI[metric].map(([label, icon, cls], i) => `<div class="bg-slate-800/70 border border-slate-700/80 rounded-lg p-2.5"><div class="flex items-center justify-between text-xs text-slate-400 mb-1"><span>${label}</span><i data-lucide="${icon}" class="w-3.5 h-3.5 ${cls}"></i></div><div class="text-xl font-bold ${cls} mono">${vals[i]} <span class="text-xs text-slate-500 font-normal">/ ${Object.keys(countries()).length}</span></div></div>`).join('');
    $('map-legend').innerHTML = `<div class="flex flex-wrap items-center gap-4"><span class="section-title">Legend</span>${LEGEND[metric].map(([c, l]) => `<span class="inline-flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm ${c}"></span><span class="text-slate-300">${l}</span></span>`).join('')}</div><div class="text-[11px] text-slate-500">${markers.length} island / microstate markers · layer: ${metric.replace('_', ' ')}</div>`;
    GCM.ui.icons();
  }

  function tooltipHtml(code) {
    const c = countries()[code]; if (!c) return code;
    const s = statusFor(code);
    return `<div style="font-family:inherit;font-size:11px;line-height:1.4"><div style="font-weight:700;color:#38bdf8;font-size:12px;margin-bottom:3px;display:flex;justify-content:space-between;gap:8px"><span>${GCM.ui.esc(c.name)} (${code})</span><span style="font-size:10px;padding:1px 5px;border-radius:4px;background:#1e293b;color:#94a3b8">${GCM.ui.esc(c.region || '')}</span></div>
      <div><b style="color:#f1f5f9">Marks:</b> ${GCM.ui.esc((c.marks || []).join(', ') || 'SDoC')}</div>
      <div><b style="color:#f1f5f9">Testing:</b> ${c.in_country_testing ? '<span style="color:#f43f5e;font-weight:600">Mandatory in-country lab</span>' : '<span style="color:#10b981">CB / SDoC accepted</span>'}</div>
      <div><b style="color:#f1f5f9">Lead time:</b> ${c.lead_time_weeks || 4} weeks</div>
      <div><b style="color:#f1f5f9">Status:</b> <span style="color:${s.color};font-weight:600">${s.status}</span></div>
      ${(s.alerts || []).length ? `<div style="color:#fb7185;font-weight:600;font-size:10px">⚠ ${s.alerts.length} active alert(s) for this product</div>` : ''}
      ${(c.transitions || []).length ? `<div style="color:#a5b4fc;font-size:10px">🔄 ${c.transitions.length} pending standard transition(s)</div>` : ''}
      <div style="font-size:9px;color:#64748b;margin-top:4px;border-top:1px solid #334155;padding-top:2px">Click to open the compliance dossier</div></div>`;
  }

  async function init() {
    const container = $('world-map'); if (!container || mapInst || typeof window.jsVectorMap === 'undefined') return;
    await loadMarkers(); await loadAlerts();
    try {
      mapInst = new window.jsVectorMap({
        selector: '#world-map', map: 'world', backgroundColor: '#0b101b', draggable: true, zoomButtons: true, zoomOnScroll: true, zoomMax: 12, zoomMin: 1,
        regionStyle: { initial: { fill: '#1e293b', stroke: '#334155', strokeWidth: 0.5, fillOpacity: 1 }, hover: { fill: '#38bdf8', cursor: 'pointer' } },
        markers: markers.map(m => ({ name: m.name, coords: m.coords })),
        markerStyle: { initial: { r: 4.5, fill: '#38bdf8', stroke: '#0369a1', strokeWidth: 1.5, fillOpacity: 0.95 }, hover: { r: 7, fill: '#f43f5e', stroke: '#fff', strokeWidth: 2, cursor: 'pointer' } },
        onRegionTooltipShow(_e, tooltip, code) { tooltip.text(tooltipHtml(code), true); },
        onRegionClick(_e, code) { openDossier(code); },
        onMarkerTooltipShow(_e, tooltip, index) { const m = markers[index]; if (m) tooltip.text(tooltipHtml(m.code), true); },
        onMarkerClick(_e, index) { const m = markers[index]; if (m) openDossier(m.code); },
      });
    } catch (e) { console.error('map init', e); container.innerHTML = GCM.ui.empty('Map library failed to load.', 'map-off'); return; }
    render(); openDossier(selected);
  }

  async function openDossier(code) {
    selected = String(code || '').toUpperCase();
    const el = $('country-dossier-content'); if (!el) return;
    let c = countries()[selected];
    if (!c) { el.innerHTML = GCM.ui.empty(`No compliance data for ${selected}`, 'map-pin-off'); GCM.ui.icons(); return; }
    const s = statusFor(selected); const list = s.alerts || [];
    const pid = prodId(); const prod = GCM.state.categories.find(x => x.id === pid);
    let rule = null; try { const d = await GCM.api.get(`/api/countries/${selected}`); rule = (d.category_rules || {})[pid]; c = d.country || c; el.dataset.products = JSON.stringify(d.products || []); } catch (_) { /* keep base data */ }
    const products = JSON.parse(el.dataset.products || '[]');
    el.innerHTML = `
      <div class="border-b border-slate-800 pb-3">
        <div class="flex items-start justify-between gap-2">
          <div><div class="flex items-center gap-2"><span class="text-2xl">${GCM.ui.flag(selected)}</span><h3 class="text-lg font-bold text-white tracking-tight">${GCM.ui.esc(c.name)}</h3><span class="pill mono text-sky-400">${GCM.ui.esc(c.code)}</span></div><p class="text-xs text-slate-400 mt-0.5">${GCM.ui.esc(c.authority || '')} · ${GCM.ui.esc(c.region || '')}${c.bloc && c.bloc !== 'None' ? ` · ${GCM.ui.esc(c.bloc)}` : ''}</p></div>
          <span class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold text-right" style="background:${s.color}20;color:${s.color};border:1px solid ${s.color}60">${s.status}</span>
        </div>
        <div class="flex flex-wrap gap-1.5 mt-2.5">${(c.marks || []).map(m => `<span class="pill text-sky-300 border-sky-800 mono font-bold">${GCM.ui.esc(m)}</span>`).join('')}</div>
      </div>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="bg-slate-800/60 border border-slate-700/60 rounded-lg p-2.5"><div class="text-[10px] text-slate-400 uppercase font-semibold">Testing scheme</div><div class="font-medium ${c.in_country_testing ? 'text-rose-400' : 'text-emerald-400'}">${c.in_country_testing ? '🔴 Mandatory in-country lab' : '🟢 CB / SDoC accepted'}</div></div>
        <div class="bg-slate-800/60 border border-slate-700/60 rounded-lg p-2.5"><div class="text-[10px] text-slate-400 uppercase font-semibold">Lead time</div><div class="font-medium text-slate-200">⏱ ${c.lead_time_weeks || 4} weeks</div></div>
        <div class="bg-slate-800/60 border border-slate-700/60 rounded-lg p-2.5"><div class="text-[10px] text-slate-400 uppercase font-semibold">CB recognition</div><div class="font-medium text-slate-200">${c.cb_scheme_accepted ? '✅ Accepted (deviations)' : '❌ Not recognised'}</div></div>
        <div class="bg-slate-800/60 border border-slate-700/60 rounded-lg p-2.5"><div class="text-[10px] text-slate-400 uppercase font-semibold">Local representative</div><div class="font-medium text-slate-200">${c.local_rep_required ? '⚠️ Mandatory' : 'Not required'}</div></div>
      </div>
      ${rule ? `<div class="bg-amber-950/20 border border-amber-900/50 rounded-lg p-3 text-xs"><div class="section-title text-amber-300 mb-1">For ${GCM.ui.esc(prod?.name || pid)}</div><div class="flex items-center gap-2 mb-1"><span class="${rule.requirement_type && rule.requirement_type.includes('Testing') ? 'badge badge-critical' : rule.requirement_type && rule.requirement_type.includes('Document') ? 'badge badge-warning' : 'badge badge-success'}">${GCM.ui.esc(rule.requirement_type || '')}</span><span class="text-[11px] text-slate-400">${GCM.ui.esc(rule.testing_location || '')}</span></div><div class="text-[11px] text-slate-300">${GCM.ui.esc(rule.notes || '')}</div><div class="mt-1.5 flex flex-wrap gap-1">${(rule.required_documents || []).slice(0, 4).map(d => `<span class="pill">${GCM.ui.esc(d)}</span>`).join('')}${(rule.required_documents || []).length > 4 ? `<span class="pill">+${rule.required_documents.length - 4} more</span>` : ''}</div></div>` : ''}
      <div class="space-y-2 text-xs">
        <div class="section-title">Regulatory standards dossier</div>
        <div class="bg-slate-800/40 border border-slate-800 rounded-lg p-2.5"><div class="flex items-center justify-between text-[10px] uppercase font-semibold mb-1"><span class="flex items-center gap-1 text-amber-400"><i data-lucide="zap" class="w-3 h-3"></i>Electrical safety</span></div><div class="text-slate-200 mono text-[11px]">${GCM.ui.esc(c.safety_std || '')}</div>${c.safety_std_next ? `<div class="text-[10px] text-indigo-300 mt-1">→ ${GCM.ui.esc(c.safety_std_next)} by ${GCM.ui.esc(c.safety_std_transition_deadline || '')}</div>` : ''}</div>
        <div class="bg-slate-800/40 border border-slate-800 rounded-lg p-2.5"><div class="flex items-center justify-between text-[10px] uppercase font-semibold mb-1"><span class="flex items-center gap-1 text-sky-400"><i data-lucide="radio" class="w-3 h-3"></i>EMC &amp; radio</span></div><div class="text-slate-200 mono text-[11px]">${GCM.ui.esc(c.emc_std || '')}</div>${c.emc_std_next ? `<div class="text-[10px] text-indigo-300 mt-1">→ ${GCM.ui.esc(c.emc_std_next)} by ${GCM.ui.esc(c.emc_std_transition_deadline || '')}</div>` : ''}</div>
        <div class="bg-emerald-950/20 border border-emerald-900/40 rounded-lg p-2.5 space-y-1 text-[11px]"><div class="text-[10px] uppercase font-semibold text-emerald-400 flex items-center gap-1"><i data-lucide="leaf" class="w-3 h-3"></i>Environmental &amp; material pillars</div>
          <div><span class="text-teal-300">RoHS:</span> <span class="text-slate-300">${GCM.ui.esc(c.rohs_std || c.env_std || '')}</span></div><div><span class="text-emerald-300">PFAS / hazmat:</span> <span class="text-slate-300">${GCM.ui.esc(c.pfas_std || '')}</span></div><div><span class="text-amber-300">Packaging:</span> <span class="text-slate-300">${GCM.ui.esc(c.packaging_std || '')}</span></div><div><span class="text-cyan-300">EPR / WEEE:</span> <span class="text-slate-300">${GCM.ui.esc(c.epr_std || '')}</span></div></div>
      </div>
      ${list.length ? `<div class="space-y-1.5"><div class="section-title text-rose-400"><i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i>Active alerts (${list.length})</div><div class="space-y-1.5 max-h-44 overflow-y-auto scrollbar pr-1">${list.map(a => `<button class="w-full text-left p-2.5 rounded-lg border ${a.severity === 'Critical' ? 'bg-rose-950/40 border-rose-900/80' : 'bg-amber-950/30 border-amber-900/60'} text-xs hover:border-sky-500/60" data-action="deeplink-alert" data-arg="${GCM.ui.esc(a.id)}"><div class="flex items-center justify-between gap-2"><span class="mono text-[10px] text-slate-400">${GCM.ui.esc(a.id)}</span>${GCM.ui.badge(a.severity, a.severity)}</div><div class="text-[11px] text-slate-200 mt-1 line-clamp-2">${GCM.ui.esc(a.title)}</div>${a.effective_date ? `<div class="text-[10px] text-slate-400 mt-0.5">${GCM.ui.fmtDate(a.effective_date)} · ${GCM.ui.relDays(a.effective_date)}</div>` : ''}</button>`).join('')}</div></div>` : ''}
      ${products.length ? `<div><div class="section-title text-emerald-400 mb-1.5"><i data-lucide="hard-drive" class="w-3.5 h-3.5"></i>Portfolio exposure (${products.length} products)</div><div class="flex flex-wrap gap-1">${products.map(p => `<button class="pill hover:text-white" data-action="deeplink-product" data-arg="${GCM.ui.esc(p.id)}">${GCM.ui.esc(p.sku)}</button>`).join('')}</div></div>` : ''}
      <div class="pt-3 border-t border-slate-800 grid grid-cols-2 gap-2 no-print">
        <button class="btn btn-secondary btn-sm" data-action="country-factsheet" data-arg="${GCM.ui.esc(c.code)}"><i data-lucide="file-text" class="w-3.5 h-3.5"></i>Full fact sheet</button>
        <button class="btn btn-secondary btn-sm" data-action="map-to-matrix" data-arg="${GCM.ui.esc(c.code)}"><i data-lucide="table" class="w-3.5 h-3.5"></i>View in matrix</button>
        <button class="btn btn-secondary btn-sm" data-action="simulate-for-country" data-arg="${GCM.ui.esc(c.code)}"><i data-lucide="flask-conical" class="w-3.5 h-3.5 text-amber-300"></i>Simulate notice</button>
        <button class="btn btn-secondary btn-sm" data-action="action-for-country" data-arg="${GCM.ui.esc(c.code)}"><i data-lucide="plus-square" class="w-3.5 h-3.5 text-emerald-300"></i>Create action</button>
      </div>`;
    GCM.ui.icons();
    try { mapInst && mapInst.setSelectedRegions && mapInst.setSelectedRegions([selected]); } catch (_) { /* ignore */ }
  }

  function focusRegion(r) {
    if (!mapInst) return;
    try { if (r === 'global') mapInst.reset(); else mapInst.setFocus({ regions: FOCUS[r] || [], animate: true }); } catch (e) { /* ignore */ }
  }

  GCM.modules.map = {
    init() {
      const sel = $('map-product-select');
      sel.innerHTML = GCM.state.categories.map(c => `<option value="${GCM.ui.esc(c.id)}" ${c.id === 'external_ssd_bus' ? 'selected' : ''}>${GCM.ui.esc(c.name)}</option>`).join('');
      sel.addEventListener('change', () => { render(); openDossier(selected); });
      $('map-metric-select').addEventListener('change', render);
      $('map-reset').addEventListener('click', () => { focusRegion('global'); $('map-search-input').value = ''; });
      $('map-focus-bar').addEventListener('click', (e) => { const b = e.target.closest('[data-focus]'); if (b) focusRegion(b.dataset.focus); });
      $('map-search-input').addEventListener('input', (e) => {
        const q = e.target.value.trim().toLowerCase(); if (q.length < 2) return;
        const f = Object.values(countries()).find(c => c.code.toLowerCase() === q || c.name.toLowerCase().includes(q) || (c.authority || '').toLowerCase().includes(q));
        if (f) { openDossier(f.code); try { mapInst && mapInst.setFocus({ regions: [f.code], animate: true }); } catch (_) { /* ignore */ } }
      });
      $('map-quick-countries').innerHTML = QUICK.map(c => `<button class="pill hover:text-white" data-action="map-select" data-arg="${c}">${GCM.ui.flag(c)} ${GCM.ui.esc(countries()[c]?.name || c)}</button>`).join('');
      GCM.bus.on('action:map-select', ({ arg }) => openDossier(arg));
      GCM.bus.on('action:map-to-matrix', ({ arg }) => { GCM.tabs.switchTo('matrix'); GCM.bus.emit('matrix:search', countries()[arg]?.name || arg); });
      GCM.bus.on('map:focus', async (code) => { if (!mapInst) await init(); openDossier(code); try { mapInst && mapInst.setFocus({ regions: [code], animate: true }); } catch (_) { /* ignore */ } });
      GCM.bus.on('alerts:changed', async () => { await loadAlerts(); if (mapInst) { render(); openDossier(selected); } });
      GCM.bus.on('countries:changed', async () => { try { const list = await GCM.api.get('/api/countries'); GCM.state.countries = {}; list.forEach(c => { GCM.state.countries[c.code] = c; }); } catch (_) { /* ignore */ } if (mapInst) { render(); openDossier(selected); } });
    },
    async onFirstShow() { await init(); },
    onShow() { if (mapInst) setTimeout(render, 80); },
  };
})();
