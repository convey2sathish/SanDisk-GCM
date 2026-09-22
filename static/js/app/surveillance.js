/* surveillance.js - surveillance bar (scan / status) and ledger modal */
(function () {
  'use strict';
  const GCM = window.GCM;
  const $ = (id) => document.getElementById(id);

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
          <td class="mono text-[10px] text-slate-400 whitespace-nowrap">${GCM.ui.esc(GCM.ui.fmtDateTime(it.timestamp))}</td>
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

  GCM.modules.surveillance = {
    init() {
      GCM.bus.on('action:surveillance-scan', scan);
      GCM.bus.on('surveillance:scan', scan);
      GCM.bus.on('action:surveillance-log', openLedger);
      GCM.bus.on('surveillance:log', openLedger);
      loadStatus();
      setInterval(loadStatus, 120000);
    },
    loadStatus,
  };
})();
