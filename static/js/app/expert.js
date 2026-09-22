/* =====================================================================
   GCM Platform 2.0 - expert.js
   "Explain in plain English" modal: audience toggle (simple / executive /
   engineer), engine pill (rules vs Claude), sections, per-step action
   creation, key dates, cost & effort, risks, glossary, confidence & sources,
   and the expert Q&A console (suggested questions, chat, streaming-like reveal).
   Exposes GCM.explain.open(alertId, audience, {section:'qa'}).
   ===================================================================== */
(function () {
  'use strict';
  const GCM = window.GCM; if (!GCM) return;
  const esc = (s) => GCM.ui.esc(s);
  const $ = (id) => document.getElementById(id);

  const ROLE_ICON = { 'Regulatory Compliance Engineer': 'clipboard-check', 'Test-Lab Coordinator': 'flask-conical', 'Firmware Security': 'lock', 'Packaging & Artwork': 'package', 'Supply-Chain & BOM': 'truck', 'Legal & Trade Compliance': 'scale', 'Local Representative': 'user-check' };
  const STATUS_CLS = { Passed: 'badge-neutral', Imminent: 'badge-critical', Approaching: 'badge-warning', Planned: 'badge-info' };
  const STATUS_DOT = { Passed: '#64748b', Imminent: '#f43f5e', Approaching: '#f59e0b', Planned: '#38bdf8' };
  const CONF_CLS = { High: 'badge-success', Medium: 'badge-warning', Low: 'badge-critical' };
  const PILLAR_CLS = { Safety: 'text-rose-300 border-rose-800/80', EMC: 'text-sky-300 border-sky-800/80', Environmental: 'text-emerald-300 border-emerald-800/80', Cyber: 'text-indigo-300 border-indigo-800/80', All: 'text-purple-300 border-purple-800/80' };

  const S = { alertId: null, audience: 'simple', alert: null, data: null, history: [], busy: false, seq: 0, aiStatus: null };

  /* ------------------------------------------------------------------ small renderers */
  const list = (items, cls = '') => Array.isArray(items) ? items : (items ? [String(items)] : []);
  function section(title, icon, bodyHtml, extraCls = '', tone = '') {
    return `<section class="explain-section ${extraCls}"><div class="section-title ${tone}"><i data-lucide="${icon}" class="w-3.5 h-3.5"></i>${esc(title)}</div>${bodyHtml}</section>`;
  }
  function paras(items, cls = 'text-slate-200') {
    return `<div class="space-y-2 text-[12px] leading-relaxed ${cls}">${list(items).map(p => {
      const m = String(p).match(/^([A-Z][A-Za-z' \-&/]{2,40}):\s(.*)$/s);
      return m ? `<p><strong class="text-white">${esc(m[1])}:</strong> ${esc(m[2])}</p>` : `<p>${esc(p)}</p>`;
    }).join('')}</div>`;
  }
  function enginePill(d) {
    const el = $('explain-engine'); if (!el) return;
    const ai = d && d.generated_by && d.generated_by !== 'rules';
    el.innerHTML = ai
      ? `<span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span><span>Claude · ${esc(d.generated_by)}${d.cache_hit ? ' · cached' : ''}</span>`
      : `<span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span><span>Rules engine v${esc((d && d.engine_version) || '2')}</span>`;
    el.title = ai ? 'Narrative refined by Claude; scope, dates and costs from the rules engine.' : 'Deterministic GCM explainer (works offline).';
    const foot = $('explain-footnote');
    if (foot) {
      const st = (d && d.ai_status) || {};
      foot.textContent = ai ? (d.ai_note || 'Narrative refined by Claude on the same facts.')
        : st.active ? (d && d.ai_note ? d.ai_note : 'Claude is configured - press Regenerate to refine this brief.')
        : st.configured && !st.enabled ? 'Claude is configured but disabled in Settings; showing the rules-engine explanation.'
        : 'Deterministic explainer works offline. Add an Anthropic API key in Settings to refine narratives with Claude.';
    }
    const rb = $('explain-refresh'); if (rb) rb.title = (d && d.ai_status && d.ai_status.active) ? 'Regenerate with Claude (bypasses cache)' : 'Re-run the rules engine';
  }

  /* ------------------------------------------------------------------ sections */
  function heroHtml(d, a) {
    const n = GCM.ui.daysUntil(a.effective_date);
    return `
      <div class="rounded-2xl p-5 bg-gradient-to-br from-indigo-950/80 via-slate-900 to-slate-900 border border-indigo-800/50 shadow-lg shadow-indigo-950/40">
        <div class="text-[10px] uppercase tracking-[.14em] font-bold text-indigo-300 mb-2 flex items-center gap-2"><i data-lucide="megaphone" class="w-3.5 h-3.5"></i>The headline</div>
        <h2 class="text-lg md:text-xl font-bold text-white leading-snug">${esc(d.headline)}</h2>
        <p class="text-[12.5px] text-slate-300 leading-relaxed mt-3">${esc(d.one_liner)}</p>
        ${d.analogy ? `<div class="mt-3 flex items-start gap-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-[12px] text-slate-200"><i data-lucide="lightbulb" class="w-4 h-4 text-amber-300 shrink-0 mt-0.5"></i><span><strong class="text-amber-200">Analogy:</strong> ${esc(d.analogy)}</span></div>` : ''}
        ${d.decision ? `<div class="mt-3 flex items-start gap-2.5 p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-[12px] text-emerald-100"><i data-lucide="gavel" class="w-4 h-4 text-emerald-300 shrink-0 mt-0.5"></i><span>${esc(d.decision)}</span></div>` : ''}
        <div class="flex flex-wrap gap-2 mt-4 text-[11px]">
          <span class="badge badge-${GCM.ui.deadlineTone(a.effective_date)}"><i data-lucide="calendar-clock" class="w-3 h-3"></i>${n === null ? esc(a.effective_date || 'Date TBC') : n < 0 ? 'Deadline passed ' + GCM.ui.relDays(a.effective_date) : n + ' days left'}</span>
          <span class="pill"><i data-lucide="hard-drive" class="w-3 h-3 mr-1"></i>${(d.who_is_affected || {}).products ? d.who_is_affected.products.length : 0} products</span>
          <span class="pill"><i data-lucide="globe-2" class="w-3 h-3 mr-1"></i>${(d.who_is_affected || {}).market_count || 0} markets</span>
          <span class="pill"><i data-lucide="coins" class="w-3 h-3 mr-1"></i>${esc((d.cost_effort_estimate || {}).cost_range || '—')}</span>
          <span class="badge ${CONF_CLS[(d.confidence || {}).level] || 'badge-neutral'}" title="${esc((d.confidence || {}).basis || '')}">Confidence: ${esc((d.confidence || {}).level || '—')}</span>
        </div>
      </div>`;
  }
  function whoHtml(w) {
    w = w || {};
    const cats = (w.categories || []).map(c => `<span class="pill">${esc(c.name)}</span>`).join('') || '<span class="text-slate-500">—</span>';
    const prods = (w.products || []).length ? `<div class="grid grid-cols-1 md:grid-cols-2 gap-1.5 mt-1">${w.products.map(p => `<button type="button" data-action="deeplink-product" data-arg="${esc(p.id)}" class="text-left flex items-center gap-2 p-2 rounded-lg bg-slate-950/70 border border-slate-800 hover:border-emerald-600/60 transition"><i data-lucide="hard-drive" class="w-3.5 h-3.5 text-emerald-400 shrink-0"></i><div class="min-w-0"><div class="text-[11px] font-semibold text-slate-100 truncate">${esc(p.name)}</div><div class="text-[10px] text-slate-400 mono truncate">${esc(p.sku)}${p.market_label ? ' · ' + esc(p.market_label) : ''}</div></div></button>`).join('')}</div>`
      : `<div class="text-[11px] text-slate-500 italic mt-1">No product in the current portfolio is hit by this alert's categories and markets.</div>`;
    const mk = w.markets || []; const shown = mk.slice(0, 30);
    const markets = w.market_count >= 150 ? `<div class="text-[11px] text-slate-300">Applies in <strong class="text-white">all ${w.market_count} jurisdictions</strong> tracked by the platform.</div>`
      : `<div class="flex flex-wrap gap-1 mt-1">${shown.map(m => `<button type="button" data-action="deeplink-country" data-arg="${esc(m.code)}" class="pill hover:border-sky-500/60" title="${esc(m.name)}">${GCM.ui.flag(m.code)} ${esc(m.code)}</button>`).join('')}${mk.length > shown.length ? `<span class="pill">+${mk.length - shown.length} more</span>` : ''}${!mk.length ? '<span class="text-slate-500 text-[11px]">No specific market resolved.</span>' : ''}</div>`;
    return `<div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-[12px]">
      <div><div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1">Product categories (${(w.categories || []).length})</div><div class="flex flex-wrap gap-1">${cats}</div></div>
      <div><div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1">Our products (${(w.products || []).length})</div>${prods}</div>
      <div><div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1">Markets (${w.market_count || 0})${w.jurisdiction ? ` · ${esc(w.jurisdiction)}` : ''}</div>${markets}</div>
    </div>`;
  }
  function stepsHtml(steps) {
    return `<ol class="space-y-2">${list(steps).map((s, i) => `
      <li class="flex items-start gap-3 p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-indigo-700/50 transition">
        <div class="step-num">${i + 1}</div>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-1.5"><span class="text-[12.5px] font-semibold text-white">${esc(s.step)}</span></div>
          <p class="text-[11.5px] text-slate-300 leading-relaxed mt-1">${esc(s.detail)}</p>
          <div class="flex flex-wrap items-center gap-1.5 mt-2 text-[10.5px]">
            <span class="pill gap-1"><i data-lucide="${ROLE_ICON[s.owner_role] || 'user'}" class="w-3 h-3"></i>${esc(s.owner_role)}</span>
            <span class="badge badge-${GCM.ui.deadlineTone(s.due_by)}"><i data-lucide="calendar" class="w-3 h-3"></i>Due ${esc(GCM.ui.fmtDate(s.due_by))} · ${esc(GCM.ui.relDays(s.due_by))}</span>
            <span class="pill">Effort ${esc(s.effort)}</span>
          </div>
        </div>
        <button type="button" data-act="step-action" data-idx="${i}" class="btn btn-secondary btn-sm shrink-0" title="Create an action item for this step"><i data-lucide="plus" class="w-3.5 h-3.5 text-emerald-400"></i>Action</button>
      </li>`).join('')}</ol>`;
  }
  function deadlinesHtml(items) {
    return `<div class="timeline mt-1">${list(items).map(d => `
      <div class="timeline-item" style="--dot:${STATUS_DOT[d.status] || '#64748b'}">
        <div class="flex flex-wrap items-center gap-2"><span class="text-[12px] font-semibold ${d.kind === 'effective' ? 'text-white' : 'text-slate-100'}">${esc(d.label)}</span><span class="badge ${STATUS_CLS[d.status] || 'badge-neutral'}">${esc(d.status)}</span>${d.kind === 'effective' ? '<span class="pill text-rose-300 border-rose-900/60">Enforcement</span>' : ''}</div>
        <div class="text-[11px] text-slate-400 mono">${esc(d.date || 'TBC')}${d.days_remaining !== null && d.days_remaining !== undefined ? ` · ${d.days_remaining < 0 ? Math.abs(d.days_remaining) + ' days ago' : d.days_remaining + ' days remaining'}` : ''}${d.original_status ? ` · notice: ${esc(d.original_status)}` : ''}</div>
      </div>`).join('')}</div>`;
  }
  function costHtml(c) {
    c = c || {};
    return `<div class="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div class="kpi" style="--kpi-glow: rgba(99,102,241,.25)"><div class="kpi-label">Indicative cost</div><div class="kpi-value !text-xl">${esc(c.cost_range || '—')}</div><div class="kpi-sub">USD, external spend only</div></div>
      <div class="kpi" style="--kpi-glow: rgba(56,189,248,.25)"><div class="kpi-label">Elapsed effort</div><div class="kpi-value !text-xl">${esc((c.effort_range || '—').split(' ')[0])}</div><div class="kpi-sub">${esc((c.effort_range || '').replace(/^\S+\s*/, '') || 'weeks')}</div></div>
      <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-[11px] text-slate-300 leading-relaxed"><strong class="text-white">Basis:</strong> ${esc(c.basis || '')}</div>
    </div>`;
  }
  function risksHtml(items) {
    return `<ul class="space-y-1.5">${list(items).map(r => `<li class="flex items-start gap-2 text-[12px] text-slate-200"><i data-lucide="alert-triangle" class="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5"></i><span>${esc(r)}</span></li>`).join('')}</ul>`;
  }
  function glossaryHtml(items) {
    items = list(items);
    if (!items.length) return '<div class="text-[11px] text-slate-500">No specialist terms detected in this alert.</div>';
    return `<details class="group"><summary class="cursor-pointer text-[12px] text-indigo-300 hover:text-white flex items-center gap-1.5 select-none"><i data-lucide="book-open" class="w-3.5 h-3.5"></i>${items.length} term${items.length === 1 ? '' : 's'} explained - click to expand</summary>
      <dl class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3">${items.map(g => `<div class="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800"><dt class="text-[11.5px] font-bold text-white">${esc(g.term)}</dt><dd class="text-[11px] text-slate-300 leading-relaxed mt-0.5">${esc(g.meaning)}</dd></div>`).join('')}</dl></details>`;
  }
  function sourcesHtml(d) {
    const conf = d.confidence || {};
    const links = list(d.sources).map(s => s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-300 border border-slate-700 hover:border-sky-500/60 text-[11px] font-medium transition"><i data-lucide="globe" class="w-3.5 h-3.5"></i>${esc(s.label)}<i data-lucide="external-link" class="w-3 h-3 text-slate-500"></i></a>` : `<span class="pill text-slate-400">${esc(s.label)}</span>`).join('');
    return `<div class="flex flex-col md:flex-row md:items-start gap-3">
      <div class="flex items-start gap-2 md:w-1/3"><span class="badge ${CONF_CLS[conf.level] || 'badge-neutral'} mt-0.5">${esc(conf.level || '—')}</span><p class="text-[11px] text-slate-300 leading-relaxed">${esc(conf.basis || '')}</p></div>
      <div class="flex flex-wrap gap-1.5 md:w-2/3">${links || '<span class="text-slate-500 text-[11px]">No links recorded.</span>'}</div>
    </div>`;
  }
  function qaHtml(d) {
    const chips = list(d.suggested_questions).map(q => `<button type="button" data-act="ask-chip" class="pill-filter text-left !rounded-xl !py-1.5 !text-[11px] !font-medium hover:border-indigo-500/70" title="Ask this">${esc(q)}</button>`).join('');
    return `<section class="explain-section border-indigo-800/50" id="explain-qa">
      <div class="flex items-center justify-between gap-2 mb-2"><div class="section-title text-indigo-300"><i data-lucide="message-circle-question" class="w-3.5 h-3.5"></i>Ask the expert</div><span class="text-[10px] text-slate-500">Answers are grounded on this alert${S.aiStatus && S.aiStatus.active ? ' and refined by Claude' : ' (rules engine + curated knowledge)'}</span></div>
      <div class="flex flex-wrap gap-1.5 mb-3" id="explain-qa-chips">${chips}</div>
      <div id="explain-qa-msgs" class="space-y-2 max-h-[360px] overflow-y-auto scrollbar pr-1"></div>
      <form id="explain-qa-form" class="mt-3 flex items-center gap-2">
        <input id="explain-qa-input" class="input flex-1" placeholder="Ask anything about this alert - lab costs, grandfathering, which clause applies…" autocomplete="off" maxlength="2000">
        <button type="submit" class="btn btn-indigo"><i data-lucide="send" class="w-3.5 h-3.5"></i><span>Ask</span></button>
      </form>
    </section>`;
  }

  function renderAll() {
    const body = $('explain-body'); const d = S.data; const a = S.alert; if (!body || !d || !a) return;
    body.innerHTML = [
      heroHtml(d, a),
      `<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">${section('What changed', 'git-compare-arrows', paras(d.what_changed), '', 'text-sky-300')}${section('Why it matters', 'target', paras(d.why_it_matters), '', 'text-amber-300')}</div>`,
      section('Who is affected', 'users', whoHtml(d.who_is_affected), '', 'text-emerald-300'),
      section('What to do - in order', 'list-ordered', stepsHtml(d.what_to_do), '', 'text-indigo-300'),
      `<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">${section('Key dates', 'calendar-days', deadlinesHtml(d.deadlines), '', 'text-rose-300')}${section('Risk if ignored', 'shield-alert', risksHtml(d.risk_if_ignored), '', 'text-rose-300')}</div>`,
      section('Cost & effort (indicative)', 'coins', costHtml(d.cost_effort_estimate), '', 'text-amber-300'),
      section('Jargon explained', 'book-open', glossaryHtml(d.jargon_glossary), '', 'text-slate-300'),
      section('Confidence & sources', 'badge-check', sourcesHtml(d), '', 'text-slate-300'),
      qaHtml(d),
      `<div class="text-[10px] text-slate-500 text-right">Generated ${esc(GCM.ui.fmtDateTime(d.generated_at))} · ${esc(d.generated_by)} · audience: ${esc(d.audience)} · ${esc(a.id)}</div>`,
    ].join('');
    renderHistory();
    GCM.ui.icons(body);
  }

  /* ------------------------------------------------------------------ loading / errors */
  function skeleton() {
    return `<div class="space-y-4">
      <div class="rounded-2xl p-5 border border-slate-800 space-y-3"><div class="skeleton h-4 w-32 rounded"></div><div class="skeleton h-7 w-3/4 rounded"></div><div class="skeleton h-4 w-full rounded"></div><div class="skeleton h-4 w-5/6 rounded"></div></div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">${GCM.ui.skeleton(1)}${GCM.ui.skeleton(1)}</div>
      ${GCM.ui.skeleton(2)}
      <div class="text-center text-[11px] text-slate-500 flex items-center justify-center gap-2"><i data-lucide="loader-2" class="w-4 h-4 animate-spin text-indigo-400"></i><span id="explain-loading-note">Reading every field of the alert and building the brief…</span></div>
    </div>`;
  }
  function errorState(msg) {
    return `<div class="card border-rose-900/60"><div class="flex items-start gap-3"><i data-lucide="alert-triangle" class="w-5 h-5 text-rose-400 shrink-0"></i><div><div class="text-sm font-bold text-white">Could not build the explanation</div><div class="text-xs text-slate-400 mt-1">${esc(msg)}</div><button type="button" data-act="retry" class="btn btn-secondary btn-sm mt-3"><i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>Retry</button></div></div></div>`;
  }

  async function fetchAlert(id) {
    const cached = (GCM.state.alerts || []).find(a => a.id === id);
    if (cached && cached.triage) return cached;
    return GCM.api.get(`/api/alerts/${encodeURIComponent(id)}`);
  }
  function setHeader(a) {
    const sev = $('explain-severity'); if (sev) { sev.className = GCM.ui.severityClass(a.severity); sev.textContent = a.severity || '—'; }
    const pil = $('explain-pillar'); if (pil) { pil.className = `pill ${PILLAR_CLS[a.pillar] || ''}`; pil.textContent = a.pillar || 'Safety'; }
    const t = $('explain-title'); if (t) t.textContent = a.title || 'Alert';
    const sub = $('explain-subtitle'); if (sub) sub.textContent = [a.country || a.region, a.standard, a.effective_date ? `effective ${a.effective_date}` : ''].filter(Boolean).join(' · ');
  }
  function setAudienceButtons() {
    document.querySelectorAll('#explain-audience .aud-btn').forEach(b => b.classList.toggle('active', b.dataset.aud === S.audience));
  }

  async function loadExplanation({ refresh = false, section = null } = {}) {
    const body = $('explain-body'); if (!body || !S.alertId) return;
    const seq = ++S.seq;
    body.innerHTML = skeleton(); GCM.ui.icons(body);
    const note = $('explain-loading-note');
    const timer = setTimeout(() => { if (note && seq === S.seq) note.textContent = refresh ? 'Asking Claude to refine the brief - this can take up to a minute…' : 'Still working - Claude refinement can take up to a minute…'; }, 3500);
    try {
      const [alert, data, ai] = await Promise.all([
        S.alert && S.alert.id === S.alertId ? Promise.resolve(S.alert) : fetchAlert(S.alertId),
        GCM.api.get(`/api/alerts/${encodeURIComponent(S.alertId)}/explain?audience=${encodeURIComponent(S.audience)}${refresh ? '&refresh=1' : ''}`),
        S.aiStatus ? Promise.resolve(S.aiStatus) : GCM.api.get('/api/ai/status').catch(() => null),
      ]);
      if (seq !== S.seq) return; // superseded by a newer request
      S.alert = alert; S.data = data; S.aiStatus = ai || data.ai_status || S.aiStatus;
      setHeader(alert); enginePill(data); renderAll();
      if (section !== 'qa') body.scrollTop = 0;
      if (refresh) GCM.ui.toast(data.generated_by === 'rules' ? 'Explanation regenerated (rules engine)' : `Refined by ${data.generated_by}`, data.ai_note || '', 'success');
      if (section === 'qa') setTimeout(() => { const qa = $('explain-qa'); if (qa) { qa.scrollIntoView({ behavior: 'smooth', block: 'start' }); const inp = $('explain-qa-input'); if (inp) inp.focus(); } }, 80);
    } catch (e) {
      if (seq !== S.seq) return;
      body.innerHTML = errorState(e.message); GCM.ui.icons(body);
    } finally { clearTimeout(timer); }
  }

  /* ------------------------------------------------------------------ Q&A */
  function renderHistory() {
    const host = $('explain-qa-msgs'); if (!host) return;
    host.innerHTML = S.history.length ? S.history.map(m => msgHtml(m)).join('') : `<div class="text-[11px] text-slate-500 italic px-1">No questions yet - pick a suggestion above or type your own.</div>`;
    host.scrollTop = host.scrollHeight; GCM.ui.icons(host);
  }
  function msgHtml(m) {
    if (m.role === 'user') return `<div class="qa-msg qa-user">${esc(m.content)}</div>`;
    const meta = m.meta || {};
    const isAi = meta.generated_by && !/^rules/i.test(meta.generated_by);
    return `<div class="qa-msg qa-bot">
      <div class="flex items-center gap-1.5 mb-1 text-[10px] text-slate-400"><i data-lucide="${isAi ? 'sparkles' : 'brain'}" class="w-3 h-3 text-indigo-300"></i>${isAi ? 'Claude · ' + esc(meta.generated_by) : esc(meta.generated_by || 'Rules engine (grounded)')}${meta.network_status ? ` · web: ${esc(meta.network_status.split(' ')[0])}` : ''}</div>
      <div data-role="text">${esc(m.content)}</div>
      ${evidenceHtml(meta.evidence, meta.confidence)}
      ${meta.cited_clauses && meta.cited_clauses.length ? `<div class="flex flex-wrap gap-1 mt-2">${meta.cited_clauses.map(c => `<span class="pill mono text-sky-300">${esc(c)}</span>`).join('')}</div>` : ''}
      ${meta.action_advice ? `<div class="mt-2 flex items-start gap-1.5 text-[11px] text-emerald-200"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5"></i><span><strong>Do next:</strong> ${esc(meta.action_advice)}</span></div>` : ''}
      ${meta.sources && meta.sources.length ? `<div class="flex flex-wrap gap-1 mt-2">${meta.sources.slice(0, 3).map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer" class="pill hover:border-sky-500/60 text-sky-300 max-w-[260px] truncate" title="${esc(s.title)}"><i data-lucide="globe" class="w-3 h-3 mr-1"></i>${esc(s.title)}</a>`).join('')}</div>` : ''}
    </div>`;
  }
  function evidenceHtml(evidence, confidence) {
    const ev = Array.isArray(evidence) ? evidence : [];
    const conf = confidence && confidence.level ? `<span class="badge ${CONF_CLS[confidence.level] || 'badge-neutral'}" title="${esc(confidence.basis || '')}">Confidence: ${esc(confidence.level)}</span>` : '';
    if (!ev.length) return conf ? `<div class="mt-2">${conf}</div>` : '';
    const line = (e) => `<div class="flex items-start gap-1.5 text-[10.5px] text-slate-400 leading-snug"><i data-lucide="quote" class="w-3 h-3 text-indigo-400 shrink-0 mt-0.5"></i><span>“${esc(e.text)}” <span class="text-slate-500">— ${esc(e.source)}</span></span></div>`;
    const head = `<div class="flex items-center gap-2 mt-2 mb-1">${conf}<span class="text-[10px] uppercase tracking-wider font-bold text-slate-500">Evidence (${ev.length})</span></div>`;
    if (ev.length <= 2) return `<div class="mt-1 border-t border-slate-800 pt-1.5">${head}<div class="space-y-1">${ev.map(line).join('')}</div></div>`;
    return `<div class="mt-1 border-t border-slate-800 pt-1.5">${head}<div class="space-y-1">${ev.slice(0, 2).map(line).join('')}</div><details class="mt-1"><summary class="cursor-pointer text-[10.5px] text-indigo-300 hover:text-white select-none">Show ${ev.length - 2} more evidence line${ev.length - 2 === 1 ? '' : 's'}</summary><div class="space-y-1 mt-1">${ev.slice(2).map(line).join('')}</div></details></div>`;
  }
  function revealText(el, text) {
    // streaming-like reveal: chunks of words
    const words = String(text).split(/(\s+)/); let i = 0; el.textContent = '';
    const host = $('explain-qa-msgs');
    const tick = () => { const n = Math.min(words.length, i + 4); el.textContent += words.slice(i, n).join(''); i = n; if (host) host.scrollTop = host.scrollHeight; if (i < words.length) setTimeout(tick, 18); };
    tick();
  }
  async function ask(question) {
    question = String(question || '').trim(); if (!question || S.busy || !S.alertId) return;
    S.busy = true;
    const input = $('explain-qa-input'); if (input) { input.value = ''; input.disabled = true; }
    const host = $('explain-qa-msgs');
    S.history.push({ role: 'user', content: question });
    if (host) { if (S.history.length === 1) host.innerHTML = ''; host.insertAdjacentHTML('beforeend', msgHtml({ role: 'user', content: question })); host.insertAdjacentHTML('beforeend', `<div class="qa-msg qa-bot" id="explain-qa-typing"><span class="typing-dot"></span> <span class="typing-dot"></span> <span class="typing-dot"></span> <span class="text-[10px] text-slate-500 ml-2">consulting the alert${S.aiStatus && S.aiStatus.active ? ' and Claude' : ' and curated knowledge'}…</span></div>`); host.scrollTop = host.scrollHeight; }
    try {
      const historyForApi = S.history.slice(0, -1).slice(-6).map(m => ({ role: m.role, content: m.content }));
      const r = await GCM.api.post(`/api/alerts/${encodeURIComponent(S.alertId)}/expert-chat`, { question, history: historyForApi, audience: S.audience });
      const msg = { role: 'assistant', content: r.answer || r.expert_answer || 'No answer produced.', meta: { generated_by: r.generated_by, cited_clauses: r.cited_clauses || [], action_advice: r.action_advice || '', sources: r.web_sources_consulted || [], network_status: r.network_status, evidence: r.evidence || [], confidence: r.confidence || null } };
      S.history.push(msg);
      const typing = $('explain-qa-typing');
      if (typing) { typing.outerHTML = msgHtml(msg); const last = host && host.lastElementChild; const txt = last && last.querySelector('[data-role=text]'); if (txt) revealText(txt, msg.content); GCM.ui.icons(host); }
    } catch (e) {
      const typing = $('explain-qa-typing'); if (typing) typing.remove();
      S.history.push({ role: 'assistant', content: `Sorry - the expert could not answer: ${e.message}`, meta: {} });
      if (host) { host.insertAdjacentHTML('beforeend', msgHtml(S.history[S.history.length - 1])); GCM.ui.icons(host); }
      GCM.ui.toast('Expert unavailable', e.message, 'error');
    } finally { S.busy = false; if (input) { input.disabled = false; input.focus(); } }
  }

  /* ------------------------------------------------------------------ actions */
  function stepAction(idx) {
    const s = (S.data && S.data.what_to_do || [])[idx]; const a = S.alert; if (!s || !a) return;
    GCM.actions.createFor('alert', a.id, {
      title: `${s.step}`.slice(0, 180), priority: a.severity === 'Critical' ? 'Critical' : a.severity === 'Warning' ? 'High' : 'Medium',
      owner: s.owner_role, due_date: s.due_by, notes: `${s.detail}\n\nEffort: ${s.effort}\nAlert: ${a.title} (${a.id})\nStandard: ${a.standard || '—'} · effective ${a.effective_date || 'TBC'}`,
    });
  }
  async function copyBrief() {
    if (!S.alertId) return;
    try {
      const res = await fetch(`/api/alerts/${encodeURIComponent(S.alertId)}/explain?audience=${encodeURIComponent(S.audience)}&format=text`);
      const text = await res.text();
      await navigator.clipboard.writeText(text);
      GCM.ui.toast('Brief copied', `${text.length.toLocaleString()} characters · paste into email or a ticket`, 'success');
    } catch (e) { GCM.ui.toast('Copy failed', e.message, 'error'); }
  }
  function print() {
    document.body.classList.add('printing-explain');
    const done = () => { document.body.classList.remove('printing-explain'); window.removeEventListener('afterprint', done); };
    window.addEventListener('afterprint', done);
    setTimeout(() => { try { window.print(); } finally { setTimeout(done, 1500); } }, 50);
  }

  /* ------------------------------------------------------------------ public API */
  GCM.explain = {
    open(alertId, audience = 'simple', opts = {}) {
      if (!alertId) return;
      const same = S.alertId === alertId;
      S.alertId = alertId; S.audience = ['simple', 'executive', 'engineer'].includes(audience) ? audience : 'simple';
      if (!same) { S.alert = null; S.data = null; S.history = []; }
      setAudienceButtons();
      const t = $('explain-title'); if (t && !same) t.textContent = 'Explaining alert…';
      GCM.ui.openModal('modal-explain');
      const body = $('explain-body'); if (body) body.scrollTop = 0; // never inherit the previous alert's scroll position
      loadExplanation({ section: opts.section || null });
    },
    setAudience(aud) { if (!S.alertId || aud === S.audience) return; S.audience = aud; setAudienceButtons(); loadExplanation(); },
    regenerate() { if (S.alertId) loadExplanation({ refresh: true }); },
    ask,
    state: S,
  };

  GCM.modules.expert = {
    init() {
      const aud = $('explain-audience'); if (aud) aud.addEventListener('click', e => { const b = e.target.closest('[data-aud]'); if (b) GCM.explain.setAudience(b.dataset.aud); });
      const rb = $('explain-refresh'); if (rb) rb.addEventListener('click', () => GCM.explain.regenerate());
      const cb = $('explain-copy'); if (cb) cb.addEventListener('click', copyBrief);
      const pb = $('explain-print'); if (pb) pb.addEventListener('click', print);
      const ca = $('explain-create-action'); if (ca) ca.addEventListener('click', () => { if (S.alert) GCM.actions.createFor('alert', S.alert.id, { title: `Compliance plan: ${S.alert.title}`.slice(0, 180), priority: S.alert.severity === 'Critical' ? 'Critical' : 'High', due_date: (S.data && S.data.what_to_do && S.data.what_to_do[0] || {}).due_by || '', notes: S.data ? `${S.data.headline}\n${S.data.one_liner}` : '' }); });
      const body = $('explain-body');
      if (body) {
        body.addEventListener('click', e => {
          const el = e.target.closest('[data-act]'); if (!el) return;
          switch (el.dataset.act) {
            case 'step-action': stepAction(+el.dataset.idx); break;
            case 'ask-chip': ask(el.textContent.trim()); break;
            case 'retry': loadExplanation(); break;
            default: break;
          }
        });
        body.addEventListener('submit', e => { const f = e.target.closest('#explain-qa-form'); if (!f) return; e.preventDefault(); const inp = $('explain-qa-input'); if (inp) ask(inp.value); });
      }
      GCM.bus.on('settings:changed', () => { S.aiStatus = null; });
      GCM.bus.on('alerts:changed', () => { if (S.alert) S.alert = null; });
    },
  };
})();
