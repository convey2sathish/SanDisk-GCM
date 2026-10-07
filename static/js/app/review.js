/* review.js - human approval workflow: queue, verification, proposals, audit trail */
(function () {
  'use strict';
  const GCM = window.GCM;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => GCM.ui.esc(s);
  let stats = null; let loaded = false;

  const safeUrl = (u) => (/^https?:\/\//i.test(String(u || '')) ? String(u) : '#');
  const FIELD_LABEL = (f) => (stats && stats.fields && stats.fields[f] && stats.fields[f].label) || f;
  const fmtVal = (v) => (v === true ? 'Yes' : v === false ? 'No' : (v === null || v === undefined || v === '') ? '(empty)' : String(v));

  /* ------------------------------------------------------------- shared helpers (used by matrix.js) */
  const STATUS_CLASS = { 'Verified': 'badge badge-success', 'Needs re-verification': 'badge badge-warning', 'Partly verified': 'badge badge-info', 'Needs review': 'badge badge-warning', 'Unverified': 'badge badge-neutral' };
  function verifyBadge(v, status) {
    const st = status || (v && v.overall) || 'Unverified';
    let title = '';
    if (st === 'Verified' && v) {
      const when = v.verified_on; const who = v.verified_by;
      title = `Verified${when ? ' on ' + when : ''}${who ? ' by ' + who : ''} (self-declared reviewer)`;
    } else if (st === 'Needs re-verification') title = 'Verified more than 12 months ago or past its expiry: check it again';
    else if (st === 'Partly verified') title = 'Some pillars are verified, others are not';
    else if (st === 'Needs review') title = 'A reviewer flagged this for review';
    else title = 'No human reviewer has verified this record against an official source';
    const date = st === 'Verified' && v && v.verified_on ? `<span class="font-normal opacity-80"> ${esc(v.verified_on)}</span>` : '';
    return `<span class="${STATUS_CLASS[st] || STATUS_CLASS.Unverified}" title="${esc(title)}">${esc(st)}${date}</span>`;
  }
  function sourceLinks(v, max) {
    const list = ((v && v.sources) || []).slice(0, max || 3);
    if (!list.length) return '<span class="text-[10px] text-slate-500">No source recorded</span>';
    return list.map(s => `<div class="leading-tight"><a href="${esc(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer" class="text-[11px] text-sky-400 hover:underline" title="${esc(s.url)}">${esc(s.label)}</a> <span class="text-[9px] text-slate-500">${esc(s.kind || '')}</span></div>`).join('');
  }
  GCM.ui.verifyBadge = verifyBadge; GCM.ui.sourceLinks = sourceLinks;

  function reviewer() { return (GCM.state.settings && GCM.state.settings.reviewer_name) || ''; }
  function reviewerLabel() { return reviewer() || '(not set: add it in Settings)'; }

  /* ------------------------------------------------------------- badges / stats */
  async function refreshStats() {
    try {
      stats = await GCM.api.get('/api/review/stats');
      const p = stats.pending || 0;
      const b = $('badge-review-pending'); if (b) { b.textContent = p; b.classList.toggle('hidden', p === 0); }
      const s = $('surv-pending-review'); if (s) s.textContent = p;
    } catch (_) { /* offline */ }
    return stats;
  }

  /* ------------------------------------------------------------- verify dialog */
  function openVerify(code, scope) {
    const m = $('modal-review-verify'); if (!m) return;
    const c = GCM.state.countries[code] || {};
    m.dataset.code = code;
    m.querySelector('[data-role=country]').textContent = `${c.name || code} (${code})`;
    m.querySelector('[data-role=reviewer]').textContent = reviewerLabel();
    m.querySelector('[name=scope]').value = ['Safety', 'EMC', 'Environmental', 'Record'].includes(scope) ? scope : 'Safety';
    m.querySelector('[name=status]').value = 'Verified';
    ['source_url', 'source_label', 'note'].forEach(n => { m.querySelector(`[name=${n}]`).value = ''; });
    GCM.ui.openModal('modal-review-verify');
  }
  async function submitVerify() {
    const m = $('modal-review-verify'); const q = (n) => m.querySelector(`[name=${n}]`).value.trim();
    const code = m.dataset.code;
    const body = { scope: q('scope'), status: q('status'), source_url: q('source_url'), source_label: q('source_label'), note: q('note') };
    if (body.status === 'Verified' && !/^https?:\/\//i.test(body.source_url)) { GCM.ui.toast('Citation URL required', 'Verified needs an http(s) link to the official source.', 'warning'); return; }
    try {
      await GCM.api.post(`/api/verification/${encodeURIComponent(code)}`, body);
      GCM.ui.closeModal('modal-review-verify'); GCM.ui.toast('Verification recorded', `${code} · ${body.scope}: ${body.status}`);
      afterChange({ countries: true });
    } catch (e) { GCM.ui.toast('Could not save verification', e.message, 'error'); }
  }

  /* ------------------------------------------------------------- propose dialog */
  function syncProposeField() {
    const m = $('modal-review-propose'); const f = m.querySelector('[name=field]').value; const meta = (stats && stats.fields && stats.fields[f]) || {};
    const cur = (GCM.state.countries[m.dataset.code] || {})[f];
    m.querySelector('[data-role=current]').textContent = fmtVal(cur);
    const isBool = meta.type === 'bool';
    m.querySelector('[name=bool]').classList.toggle('hidden', !isBool); m.querySelector('[name=value]').classList.toggle('hidden', isBool);
    m.querySelector('[name=value]').type = meta.type === 'int' ? 'number' : 'text';
    if (isBool) m.querySelector('[name=bool]').value = cur ? 'false' : 'true';
    else m.querySelector('[name=value]').value = cur === undefined || cur === null ? '' : String(cur);
  }
  async function openPropose(code, field) {
    const m = $('modal-review-propose'); if (!m) return;
    if (!stats) await refreshStats();
    const c = GCM.state.countries[code] || {};
    m.dataset.code = code;
    m.querySelector('[data-role=country]').textContent = `${c.name || code} (${code})`;
    m.querySelector('[data-role=reviewer]').textContent = reviewerLabel();
    const sel = m.querySelector('[name=field]');
    sel.innerHTML = Object.entries((stats && stats.fields) || {}).map(([k, v]) => `<option value="${esc(k)}">${esc(v.label)} (${esc(v.pillar)})</option>`).join('');
    if (field && (stats.fields || {})[field]) sel.value = field;
    ['reason', 'source_url', 'source_label'].forEach(n => { m.querySelector(`[name=${n}]`).value = ''; });
    syncProposeField();
    GCM.ui.openModal('modal-review-propose');
  }
  async function submitPropose() {
    const m = $('modal-review-propose'); const q = (n) => m.querySelector(`[name=${n}]`).value.trim();
    const field = q('field'); const meta = (stats.fields || {})[field] || {};
    const value = meta.type === 'bool' ? q('bool') === 'true' : q('value');
    if (!q('reason')) { GCM.ui.toast('Reason required', 'Say why the record should change.', 'warning'); return; }
    if (!/^https?:\/\//i.test(q('source_url'))) { GCM.ui.toast('Source URL required', 'Provide an http(s) link to the source you relied on.', 'warning'); return; }
    try {
      const r = await GCM.api.post('/api/review/proposals', { country_code: m.dataset.code, changes: { [field]: value }, reason: q('reason'), source_url: q('source_url'), source_label: q('source_label') });
      GCM.ui.closeModal('modal-review-propose');
      GCM.ui.toast('Submitted for review', `${r.item.id} is waiting in the Review tab.`, 'info', { label: 'Open Review', run: () => GCM.tabs.switchTo('review') });
      afterChange({});
    } catch (e) { GCM.ui.toast('Could not submit', e.message, 'error'); }
  }

  function afterChange({ countries, alerts }) {
    GCM.bus.emit('review:changed');
    if (alerts) GCM.bus.emit('alerts:changed');
    if (countries) GCM.bus.emit('countries:changed');
  }

  /* ------------------------------------------------------------- rendering */
  function noticeCard(it) {
    const p = it.payload || {};
    const codes = p.country_code || 'GLOBAL';
    return `<div class="rounded-xl border border-slate-700 bg-slate-900/70 p-4 space-y-2" data-item="${esc(it.id)}">
      <div class="flex flex-wrap items-center gap-2"><span class="badge badge-info">Surveillance notice</span><span class="mono text-[10px] text-slate-500">${esc(it.id)}</span><span class="text-[10px] text-slate-500">detected ${esc(GCM.ui.fmtDateTime(it.created_at))}</span></div>
      <div class="text-sm font-semibold text-white">${esc(p.summary || p.event_id)}</div>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-2 text-[11px]">
        <div><div class="text-slate-500">Authority</div><div class="text-slate-200">${esc(p.authority || p.source_name || '')}</div></div>
        <div><div class="text-slate-500">Pillar</div><div class="text-slate-200">${esc(p.pillar || '')} · ${esc(p.severity || '')}</div></div>
        <div><div class="text-slate-500">Detected standard</div><div class="text-emerald-300 font-semibold">${esc(p.new_standard || '')}</div></div>
        <div><div class="text-slate-500">Source</div>${it.source_url ? `<a href="${esc(safeUrl(it.source_url))}" target="_blank" rel="noopener noreferrer" class="text-sky-400 hover:underline">${esc(p.source_name || 'Open notice')}</a>` : '<span class="text-slate-500">none</span>'}</div>
      </div>
      <div class="text-[11px] text-slate-400 bg-slate-800/50 rounded-lg px-3 py-2"><span class="text-slate-300 font-semibold">If approved:</span> a ledger entry and an alert are created for ${esc(codes)} (effective ${esc(p.effective_date || 'n/a')}). Country requirement records are not edited. If rejected: nothing is created and this notice is not queued again.</div>
      ${decisionRow(it)}</div>`;
  }
  function changeCard(it) {
    const p = it.payload || {}; const ch = p.changes || {};
    const rows = Object.entries(ch).map(([f, x]) => `<div class="text-[11px]"><span class="text-slate-500">${esc(FIELD_LABEL(f))}:</span> <span class="text-slate-400 line-through">${esc(fmtVal(x.before))}</span> <span class="text-slate-500">to</span> <span class="text-emerald-300 font-semibold">${esc(fmtVal(x.after))}</span></div>`).join('');
    return `<div class="rounded-xl border border-slate-700 bg-slate-900/70 p-4 space-y-2" data-item="${esc(it.id)}">
      <div class="flex flex-wrap items-center gap-2"><span class="badge badge-warning">Proposed change</span><span class="mono text-[10px] text-slate-500">${esc(it.id)}</span><span class="text-[10px] text-slate-500">by ${esc(it.proposed_by)} · ${esc(GCM.ui.fmtDateTime(it.created_at))}</span></div>
      <div class="text-sm font-semibold text-white">${GCM.ui.flag(p.country_code)} ${esc(p.country_name || p.country_code)} <span class="mono text-[10px] text-slate-500">${esc(p.country_code)}</span></div>
      <div class="space-y-1">${rows}</div>
      <div class="text-[11px] text-slate-300"><span class="text-slate-500">Reason:</span> ${esc(p.reason || '')}</div>
      <div class="text-[11px]"><span class="text-slate-500">Citation:</span> <a href="${esc(safeUrl(it.source_url))}" target="_blank" rel="noopener noreferrer" class="text-sky-400 hover:underline break-all">${esc(p.source_label || it.source_url)}</a></div>
      ${decisionRow(it)}</div>`;
  }
  function decisionRow(it) {
    return `<div class="flex flex-col sm:flex-row gap-2 pt-1"><input class="input flex-1" data-role="note" maxlength="500" placeholder="Decision note (required to reject)" autocomplete="off">
      <button type="button" class="btn btn-success btn-sm" data-action="review-approve" data-arg="${esc(it.id)}"><i data-lucide="check" class="w-3.5 h-3.5"></i>Approve</button>
      <button type="button" class="btn btn-danger btn-sm" data-action="review-reject" data-arg="${esc(it.id)}"><i data-lucide="x" class="w-3.5 h-3.5"></i>Reject</button></div>`;
  }
  function itemSummary(it) {
    const p = it.payload || {};
    if (it.type === 'kb_change') return `${p.country_name || p.country_code}: ${Object.keys(p.changes || {}).map(FIELD_LABEL).join(', ')}`;
    return p.summary || p.event_id || '';
  }
  const STATUS_BADGE = { Approved: 'badge-success', Rejected: 'badge-critical', Pending: 'badge-warning' };

  function render(items, audit) {
    const pend = items.filter(i => i.status === 'Pending');
    $('review-pending-label').textContent = pend.length ? `${pend.length} waiting` : '';
    $('review-pending').innerHTML = pend.length ? pend.map(i => (i.type === 'kb_change' ? changeCard(i) : noticeCard(i))).join('')
      : GCM.ui.empty('Nothing is waiting for review. Scan the feeds, or propose a change from a country fact sheet.', 'check-check');
    const done = items.filter(i => i.status !== 'Pending').sort((a, b) => String(b.decided_on).localeCompare(String(a.decided_on)));
    $('review-history').innerHTML = done.length ? done.map(i => `<tr><td class="mono text-[10px] text-slate-400 whitespace-nowrap">${esc(GCM.ui.fmtDateTime(i.decided_on))}</td><td class="mono text-[10px]">${esc(i.id)}<div class="text-slate-500">${i.type === 'kb_change' ? 'change' : 'notice'}</div></td><td class="text-[11px] text-slate-200 max-w-md">${esc(itemSummary(i))}</td><td><span class="badge ${STATUS_BADGE[i.status] || 'badge-neutral'}">${esc(i.status)}</span></td><td class="text-[11px]">${esc(i.proposed_by)}</td><td class="text-[11px]">${esc(i.decided_by)}</td><td class="text-[11px] text-slate-400 max-w-xs">${esc(i.decision_note)}</td></tr>`).join('')
      : `<tr><td colspan="7">${GCM.ui.empty('No decisions yet.')}</td></tr>`;
    const brief = (v) => (v && typeof v === 'object') ? Object.entries(v).map(([k, x]) => `${k}: ${fmtVal(x)}`).join('; ') : fmtVal(v);
    const ae = audit.entries || [];
    $('review-audit').innerHTML = ae.length ? ae.map(e => `<tr><td class="mono text-[10px] text-slate-400 whitespace-nowrap">${esc(GCM.ui.fmtDateTime(e.when))}</td><td class="text-[11px]">${esc(e.who)}</td><td class="text-[11px] text-slate-200">${esc(e.what)}</td><td class="mono text-[10px]">${esc(e.item_id || '')}</td><td class="mono text-[10px]">${esc(e.country_code || '')}</td><td class="text-[10px] text-slate-400 max-w-sm">${e.before == null && e.after == null ? '' : `${esc(brief(e.before))} <span class="text-slate-500">to</span> ${esc(brief(e.after))}`}</td><td class="text-[10px] text-slate-400 max-w-xs">${esc(e.detail)}</td><td class="mono text-[10px] text-slate-500" title="${esc(e.hash)}">${esc((e.hash || '').slice(0, 10))}…</td></tr>`).join('')
      : `<tr><td colspan="8">${GCM.ui.empty('The audit trail is empty.')}</td></tr>`;
    const ab = $('review-audit-badge'); ab.textContent = audit.ok ? `Integrity verified · ${audit.total} entries` : `Integrity FAILED at entry ${audit.first_bad_index}`;
    ab.className = audit.ok ? 'badge badge-success' : 'badge badge-critical';
  }

  function renderKpis() {
    if (!stats) return;
    $('review-kpi-pending').textContent = stats.pending; $('review-kpi-approved').textContent = stats.approved; $('review-kpi-rejected').textContent = stats.rejected;
    const c = stats.coverage || {}; const pct = c.key_markets_total ? Math.round(100 * c.verified / c.key_markets_total) : 0;
    $('review-kpi-coverage').textContent = `${pct}%`;
    $('review-kpi-coverage-sub').textContent = `${c.verified}/${c.key_markets_total} key markets verified · ${c.needs_reverification} need re-verification`;
    const a = $('review-kpi-audit'); a.textContent = stats.audit_ok ? 'OK' : 'FAILED'; a.className = `kpi-value ${stats.audit_ok ? 'text-emerald-400' : 'text-rose-400'}`;
    $('review-kpi-audit-sub').textContent = `${stats.audit_entries} entries, hash-chained`;
    $('review-reviewer').textContent = stats.reviewer_name || '(not set)';
  }

  async function load() {
    try {
      const [q, , a] = await Promise.all([GCM.api.get('/api/review/queue?status=all'), refreshStats(), GCM.api.get('/api/review/audit?limit=200')]);
      renderKpis(); render(q.items || [], a); loaded = true; GCM.ui.icons();
    } catch (e) { $('review-pending').innerHTML = `<div class="text-rose-400 text-xs">${esc(e.message)}</div>`; }
  }

  async function decide(id, kind, el) {
    const card = el.closest('[data-item]'); const note = (card.querySelector('[data-role=note]').value || '').trim();
    if (kind === 'reject' && !note) { GCM.ui.toast('Note required', 'Explain why you are rejecting this item.', 'warning'); card.querySelector('[data-role=note]').focus(); return; }
    GCM.ui.setLoading(el, true, kind === 'approve' ? 'Approving…' : 'Rejecting…');
    try {
      const r = await GCM.api.post(`/api/review/queue/${encodeURIComponent(id)}/${kind}`, { note });
      GCM.ui.toast(kind === 'approve' ? 'Approved and applied' : 'Rejected', r.item.id, kind === 'approve' ? 'success' : 'info');
      afterChange({ alerts: kind === 'approve', countries: kind === 'approve' });
    } catch (e) { GCM.ui.setLoading(el, false); GCM.ui.toast(kind === 'approve' ? 'Could not approve' : 'Could not reject', e.message, 'error'); }
  }

  GCM.review = { openVerify, openPropose, refreshStats };
  GCM.modules.review = {
    init() {
      GCM.bus.on('action:review-approve', ({ arg, el }) => decide(arg, 'approve', el));
      GCM.bus.on('action:review-reject', ({ arg, el }) => decide(arg, 'reject', el));
      GCM.bus.on('action:review-refresh', load);
      GCM.bus.on('action:review-verify', ({ arg, el }) => openVerify(arg, el && el.dataset.scope));
      GCM.bus.on('action:review-propose', ({ arg, el }) => openPropose(arg, el && el.dataset.field));
      GCM.bus.on('action:review-verify-submit', submitVerify);
      GCM.bus.on('action:review-propose-submit', submitPropose);
      const sel = document.querySelector('#modal-review-propose [name=field]'); if (sel) sel.addEventListener('change', syncProposeField);
      GCM.bus.on('review:changed', () => { if (loaded) load(); else refreshStats(); });
      GCM.bus.on('settings:changed', () => { refreshStats(); });
      GCM.palette.register({ label: 'Open Review queue (pending approvals)', icon: 'clipboard-check', keywords: ['review', 'approve', 'queue', 'verify'], run: () => GCM.tabs.switchTo('review') });
      refreshStats();
    },
    onShow() { load(); },
  };
})();
