/* surveillance.js - surveillance bar, ledger modal, gazette-notice simulator */
(function () {
  'use strict';
  const GCM = window.GCM;
  const $ = (id) => document.getElementById(id);

  const PRESETS = {
    safety_62368: { pillar: 'Safety', authority: 'International Electrotechnical Commission (IEC) & harmonised national bodies', standard: 'IEC 62368-1:2023 (Edition 4.0)', deadline: '2028-12-31',
      summary: 'Worldwide harmonisation notice: mandatory transition to IEC 62368-1 4th Edition covering updated touch-temperature thresholds, external power adapter test limits and fire-enclosure barriers.' },
    emc_cispr32: { pillar: 'EMC', authority: 'CISPR / ITU & national communications authorities', standard: 'CISPR 32:2026 Class B (harmonised)', deadline: '2027-09-30',
      summary: 'Gazette circular mandating updated radiated-emissions limits and measurement methods above 1 GHz for multimedia and solid-state storage equipment.' },
    env_rohs: { pillar: 'Environmental', authority: 'Environmental protection & chemicals agencies (ECHA / EPA aligned)', standard: 'RoHS 4 / universal PFAS restriction', deadline: '2027-03-01',
      summary: 'Environmental directive prohibiting intentionally added PFAS in components and packaging and adding revised MCCP / TBBP-A restriction thresholds for electronics.' },
    tri_pillar: { pillar: 'All', authority: 'WTO-TBT global regulatory harmonisation framework', standard: 'IEC 62368-1 / CISPR 32 / RoHS 4 harmonised package', deadline: '2028-06-30',
      summary: 'Synchronised multi-pillar mandate updating safety, EMC and environmental standards across all market-access jurisdictions.' },
  };

  async function loadStatus() {
    try {
      const s = await GCM.api.get('/api/surveillance/status');
      const badge = $('surv-status-badge');
      if (badge) { badge.textContent = s.ledger_ok === false ? 'Ledger tamper detected' : 'Listening'; badge.className = s.ledger_ok === false ? 'badge badge-critical' : 'badge badge-success'; }
      if ($('surv-last-scan')) $('surv-last-scan').textContent = s.last_scan_time ? GCM.ui.fmtDateTime(s.last_scan_time) : 'not yet this session';
      if ($('surv-sources-count')) $('surv-sources-count').textContent = s.monitored_sources_count || 12;
      return s;
    } catch (e) { return null; }
  }

  async function scan() {
    const btn = $('btn-surv-scan');
    GCM.ui.setLoading(btn, true, 'Scanning gateways…');
    try {
      const r = await GCM.api.post('/api/surveillance/scan', {});
      const res = r.result || {};
      const online = res.network_reachable;
      GCM.ui.toast(online ? 'Feed scan complete' : 'Scan finished offline',
        online ? `${(res.sources_reachable || []).length}/${res.sources_scanned} gateways reachable · ${res.notices_detected} relevant notices · ${res.newly_applied_count} new` : 'No gateway reachable (offline or proxy). Knowledge base unchanged.', online ? 'success' : 'warning');
      if (res.newly_applied_count > 0) {
        GCM.ui.notify({ title: `${res.newly_applied_count} new regulatory notice(s) ingested`, body: (res.new_events || []).map(e => e.summary).join(' · ').slice(0, 220), scope: 'Applied to matrix, alerts and ledger', actions: [{ label: 'View alerts', run: () => GCM.tabs.switchTo('alerts') }] });
        GCM.bus.emit('alerts:changed'); GCM.bus.emit('countries:changed');
      }
      await loadStatus();
    } catch (e) { GCM.ui.toast('Scan failed', e.message, 'error'); }
    finally { GCM.ui.setLoading(btn, false); }
  }

  async function openLedger() {
    GCM.ui.openModal('modal-surveillance-log');
    const tbody = $('surveillance-log-tbody'); const integ = $('ledger-integrity');
    tbody.innerHTML = `<tr><td colspan="7">${GCM.ui.skeleton(3)}</td></tr>`;
    try {
      const data = await GCM.api.get('/api/surveillance/log?limit=200');
      integ.textContent = data.ledger_ok ? `Integrity verified · ${data.ledger_entries} entries` : `Integrity FAILED at entry ${data.ledger_first_bad_index}`;
      integ.className = data.ledger_ok ? 'badge badge-success' : 'badge badge-critical';
      const rows = data.audit_log || [];
      if (!rows.length) { tbody.innerHTML = `<tr><td colspan="7">${GCM.ui.empty('No surveillance records yet.')}</td></tr>`; GCM.ui.icons(); return; }
      const pillarBadge = (p) => ({ Safety: 'badge-critical', EMC: 'badge-info', Environmental: 'badge-success', Cyber: 'badge-indigo', All: 'badge-purple' }[p] || 'badge-neutral');
      tbody.innerHTML = rows.map(it => `
        <tr>
          <td class="mono text-[10px] text-slate-400 whitespace-nowrap">${GCM.ui.esc(GCM.ui.fmtDateTime(it.timestamp))}${it.simulated ? '<div><span class="pill">simulated</span></div>' : ''}</td>
          <td class="whitespace-nowrap"><span class="mr-1">${GCM.ui.flag(it.country_code)}</span><span class="font-semibold text-white">${GCM.ui.esc(it.country_name)}</span> <span class="text-[10px] text-slate-500 mono">(${GCM.ui.esc(it.country_code)})</span>${it.affected_countries_count > 1 ? `<div class="text-[10px] text-emerald-400">${it.affected_countries_count} jurisdictions</div>` : ''}</td>
          <td><div class="text-slate-200 font-medium">${GCM.ui.esc(it.authority)}</div><a href="${GCM.ui.esc(it.source_url || '#')}" target="_blank" rel="noopener noreferrer" class="text-[10px] text-sky-400 hover:underline">${GCM.ui.esc(it.source_name)}</a></td>
          <td><span class="badge ${pillarBadge(it.pillar)}">${GCM.ui.esc(it.pillar || 'Safety')}</span></td>
          <td><div class="text-emerald-300 font-semibold">${GCM.ui.esc(it.new_standard)}</div><div class="text-[10px] text-slate-400">Deadline: <span class="text-rose-300 mono">${GCM.ui.esc(it.withdrawal_deadline || '—')}</span></div>${it.impacted_products_count ? `<div class="text-[10px] text-amber-300">${it.impacted_products_count} products impacted</div>` : ''}</td>
          <td class="text-[11px] text-slate-300 max-w-md">${GCM.ui.esc(it.summary)}</td>
          <td class="mono text-[10px] text-slate-500" title="${GCM.ui.esc(it.hash || '')}">${it.hash ? GCM.ui.esc(it.hash.slice(0, 12)) + '…' : '<span class="text-slate-600">legacy</span>'}</td>
        </tr>`).join('');
      GCM.ui.icons();
    } catch (e) { tbody.innerHTML = `<tr><td colspan="7" class="text-rose-400 text-center py-6">${GCM.ui.esc(e.message)}</td></tr>`; }
  }

  function fillSimulator() {
    const sel = $('sim-country'); const cats = $('sim-categories');
    if (sel && sel.options.length <= 1) {
      Object.values(GCM.state.countries).sort((a, b) => a.name.localeCompare(b.name)).forEach(c => { const o = document.createElement('option'); o.value = c.code; o.textContent = `${GCM.ui.flag(c.code)} ${c.name} (${c.code})`; sel.appendChild(o); });
    }
    if (cats && !cats.options.length) {
      GCM.state.categories.forEach(c => { const o = document.createElement('option'); o.value = c.id; o.textContent = c.name; o.selected = ['external_ssd_powered', 'external_ssd_bus', 'internal_ssd', 'usb_drive'].includes(c.id); cats.appendChild(o); });
    }
  }

  function applyPreset(key) {
    const p = PRESETS[key]; if (!p) return;
    $('sim-pillar').value = p.pillar; $('sim-authority').value = p.authority; $('sim-standard').value = p.standard; $('sim-deadline').value = p.deadline; $('sim-summary').value = p.summary;
  }

  async function submitSim(e) {
    e.preventDefault();
    const btn = $('btn-sim-submit'); GCM.ui.setLoading(btn, true, 'Ingesting…');
    const cc = $('sim-country').value;
    const payload = {
      country_code: cc, pillar: $('sim-pillar').value, authority: $('sim-authority').value.trim(), new_standard: $('sim-standard').value.trim(),
      deadline: $('sim-deadline').value, summary: $('sim-summary').value.trim(),
      affected_categories: [...$('sim-categories').selectedOptions].map(o => o.value),
    };
    try {
      const r = await GCM.api.post('/api/surveillance/simulate', payload);
      GCM.ui.closeModal('modal-simulate-notice');
      const n = r.affected_countries_count || 1;
      GCM.ui.notify({ title: `Gazette notice ingested: ${payload.new_standard}`, body: `${payload.pillar} transition recorded for ${n} jurisdiction${n === 1 ? '' : 's'}; ${r.impacted_products_count || 0} portfolio products impacted. A new alert was created and the ledger updated.`, scope: cc === 'ALL' ? 'All 205 jurisdictions' : `${GCM.state.countries[cc]?.name || cc}`,
        actions: [{ label: 'Explain the alert', run: () => GCM.deeplink.alert(r.alert && r.alert.id) }, { label: 'View matrix', run: () => GCM.tabs.switchTo('matrix') }] });
      GCM.bus.emit('alerts:changed'); GCM.bus.emit('countries:changed', { codes: cc === 'ALL' ? null : [cc] });
      await loadStatus();
    } catch (err) { GCM.ui.toast('Simulation failed', err.message, 'error'); }
    finally { GCM.ui.setLoading(btn, false); }
  }

  GCM.modules.surveillance = {
    init() {
      GCM.bus.on('action:surveillance-scan', scan);
      GCM.bus.on('surveillance:scan', scan);
      GCM.bus.on('action:surveillance-log', openLedger);
      GCM.bus.on('surveillance:log', openLedger);
      GCM.bus.on('action:surveillance-simulate', () => { fillSimulator(); GCM.ui.openModal('modal-simulate-notice'); });
      GCM.bus.on('surveillance:simulate-country', (code) => { fillSimulator(); $('sim-country').value = code; $('sim-scope-status').innerHTML = `<span class="w-2 h-2 rounded-full bg-sky-400 animate-pulse"></span>Target: ${GCM.ui.esc(GCM.state.countries[code]?.name || code)}`; GCM.ui.openModal('modal-simulate-notice'); });
      const form = $('sim-form'); if (form) form.addEventListener('submit', submitSim);
      const presets = $('sim-presets'); if (presets) presets.addEventListener('click', (e) => { const b = e.target.closest('[data-preset]'); if (b) applyPreset(b.dataset.preset); });
      const sel = $('sim-country'); if (sel) sel.addEventListener('change', () => { const v = sel.value; $('sim-scope-status').innerHTML = v === 'ALL' ? '<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>Target: all 205 countries' : `<span class="w-2 h-2 rounded-full bg-sky-400 animate-pulse"></span>Target: ${GCM.ui.esc(GCM.state.countries[v]?.name || v)}`; });
      GCM.palette.register({ label: 'Simulate a gazette notice (what-if)', icon: 'flask-conical', keywords: ['simulate', 'gazette', 'what if'], run: () => { fillSimulator(); GCM.ui.openModal('modal-simulate-notice'); } });
      loadStatus();
      setInterval(loadStatus, 120000);
    },
    loadStatus,
  };
})();
