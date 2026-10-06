/* =====================================================================
   GCM Platform 2.0 - research.js
   "Ask the Expert" - general regulatory research assistant (not tied to
   one alert). Chat-style transcript, animated research steps, structured
   brief (direct answer, collapsible details, requirements table with
   matrix-style pillar pills, evidence, web sources, glossary, confidence,
   research trail, follow-ups), copy brief, create action.
   Exposes GCM.research.open(question?) and listens to bus 'expert:open'.
   ===================================================================== */
(function () {
  'use strict';
  const GCM = window.GCM; if (!GCM) return;
  const esc = (s) => GCM.ui.esc(s);
  const $ = (id) => document.getElementById(id);
  const MODAL = 'modal-expert-research';

  const PILLAR_PILL = {
    Safety: 'text-rose-300 border-rose-800', EMC: 'text-sky-300 border-sky-800', Environmental: 'text-emerald-300 border-emerald-800',
    Energy: 'text-amber-300 border-amber-800', Cyber: 'text-violet-300 border-violet-800', Labelling: 'text-indigo-300 border-indigo-800',
  };
  const CONF_CLS = { High: 'badge-success', Medium: 'badge-warning', Low: 'badge-critical' };
  const STEPS = ['Understanding question', 'Consulting knowledge base', 'Searching the web', 'Writing brief'];
  const SECTION_ICON = [[/requirement/i, 'clipboard-check'], [/exempt/i, 'shield-off'], [/mark|label/i, 'tag'], [/document/i, 'file-text'], [/cost|lead/i, 'wallet'], [/standard|specific|differen/i, 'book-open'], [/deadline|alert/i, 'bell'], [/country|profile/i, 'globe'], [/curated/i, 'library']];

  const S = { history: [], busy: false, aiStatus: null, last: null, suggestions: [], seq: 0 };

  /* ------------------------------------------------------------------ renderers */
  function reqBadge(req) {
    const r = String(req || '');
    if (r.includes('Testing Required')) return 'badge badge-critical';
    if (r.includes('Document Required')) return 'badge badge-warning';
    if (r.includes('Supplier Declaration')) return 'badge badge-success';
    return 'badge badge-neutral';
  }
  function pillarCell(p) {
    if (p.status === 'Exempt') {
      return `<div class="flex items-start gap-1.5"><span class="pill text-slate-400 border-slate-700 shrink-0">${esc(p.pillar)}</span><span class="pill text-emerald-400 border-emerald-900 bg-emerald-950/40 shrink-0">Exempt</span><span class="text-slate-400 text-[10px] italic leading-tight">${esc(p.note || '')}</span></div>`;
    }
    if (p.status !== 'Required') {
      return `<div class="flex items-start gap-1.5"><span class="pill text-slate-500 border-slate-800 shrink-0">${esc(p.pillar)}</span><span class="text-slate-500 text-[10px]">${esc(p.status || 'n/a')}</span></div>`;
    }
    const std = p.standard ? `<span class="text-white text-[11px]">${esc(p.standard)}</span>` : '';
    const route = p.route ? `<span class="pill text-slate-300 border-slate-600">${esc(p.route)}</span>` : '';
    const note = p.pillar === 'Environmental' || !p.note ? '' : `<div class="text-[10px] text-slate-500 leading-tight">${esc(p.note)}</div>`;
    return `<div class="flex items-start gap-1.5"><span class="pill ${PILLAR_PILL[p.pillar] || ''} shrink-0">${esc(p.pillar)}</span><div class="min-w-0"><div class="flex items-center gap-1.5 flex-wrap">${std}${route}</div>${note}</div></div>`;
  }
  function tableHtml(rows) {
    if (!Array.isArray(rows) || !rows.length) return '';
    const body = rows.map(r => `<tr>
      <td><div class="font-semibold text-white">${esc(r.country)}</div><div class="text-[10px] text-slate-500">${esc(r.category)}</div><div class="mt-1"><span class="${reqBadge(r.requirement_type)}">${esc(r.requirement_type || '')}</span></div></td>
      <td><div class="space-y-1">${(r.pillars || []).map(pillarCell).join('')}</div></td>
      <td>${(r.marks || []).length ? (r.marks || []).map(m => `<div class="flex items-center gap-1 flex-wrap"><span class="pill ${m.status === 'Required' ? 'text-amber-300 border-amber-800' : 'text-slate-500 border-slate-800 line-through'}">${esc(m.mark)}</span>${m.status !== 'Required' ? `<span class="text-[10px] text-slate-500">${esc(m.reason || 'not required')}</span>` : ''}</div>`).join('') : '<span class="text-slate-500">none</span>'}</td>
      <td>${(r.documents || []).length ? `<ul class="list-disc pl-3 space-y-0.5">${(r.documents || []).map(d => `<li>${esc(d)}</li>`).join('')}</ul>` : '—'}</td>
      <td class="mono whitespace-nowrap">${esc(r.lead_time)} wk${r.local_rep_required ? '<div class="text-[10px] text-amber-300">local rep</div>' : ''}</td></tr>`).join('');
    return `<div class="overflow-x-auto rounded-lg border border-slate-800 mt-2"><table class="rs-table w-full min-w-[700px]"><thead><tr><th>Market · product</th><th>Pillars</th><th>Marks</th><th>Documents</th><th>Lead</th></tr></thead><tbody>${body}</tbody></table></div>`;
  }
  function sectionHtml(d, open) {
    const icon = (SECTION_ICON.find(([rx]) => rx.test(d.heading || '')) || [null, 'list'])[1];
    return `<details class="rs-section" ${open ? 'open' : ''}><summary><i data-lucide="${icon}" class="w-3.5 h-3.5 text-indigo-300 shrink-0"></i><span>${esc(d.heading)}</span><i data-lucide="chevron-down" class="w-3.5 h-3.5 rs-chev"></i></summary><div class="rs-body">${esc(d.body)}</div></details>`;
  }
  function evidenceHtml(ev) {
    if (!Array.isArray(ev) || !ev.length) return '';
    const line = (e) => `<div class="flex items-start gap-1.5 text-[10.5px] text-slate-400 leading-snug"><i data-lucide="quote" class="w-3 h-3 text-indigo-400 shrink-0 mt-0.5"></i><span>“${esc(e.text)}” <span class="text-slate-500">— ${esc(e.source)}</span></span></div>`;
    return `<details class="rs-section"><summary><i data-lucide="quote" class="w-3.5 h-3.5 text-indigo-300"></i><span>Evidence (${ev.length})</span><i data-lucide="chevron-down" class="w-3.5 h-3.5 rs-chev"></i></summary><div class="rs-body !whitespace-normal space-y-1">${ev.map(line).join('')}</div></details>`;
  }
  function sourcesHtml(ws, alerts) {
    const web = Array.isArray(ws) ? ws : [];
    const al = Array.isArray(alerts) ? alerts : [];
    if (!web.length && !al.length) return '';
    const webHtml = web.map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer" class="pill hover:border-sky-500/60 ${s.kind === 'curated' ? 'text-emerald-300' : 'text-sky-300'} max-w-[320px] truncate" title="${esc(s.snippet || s.title)}"><i data-lucide="${s.kind === 'curated' ? 'book-marked' : 'globe'}" class="w-3 h-3 mr-1 shrink-0"></i>${esc(s.title)}</a>`).join('');
    const alHtml = al.map(a => `<button type="button" class="pill hover:border-amber-500/60 text-amber-300 max-w-[320px] truncate" data-rs-alert="${esc(a.id)}" title="Open alert ${esc(a.id)}"><i data-lucide="bell" class="w-3 h-3 mr-1 shrink-0"></i>${esc(a.id)} · ${esc(a.title)}</button>`).join('');
    return `<div class="mt-2 space-y-1.5">${al.length ? `<div class="flex flex-wrap gap-1 items-center"><span class="text-[10px] uppercase tracking-wider font-bold text-slate-500 mr-1">Alerts</span>${alHtml}</div>` : ''}${web.length ? `<div class="flex flex-wrap gap-1 items-center"><span class="text-[10px] uppercase tracking-wider font-bold text-slate-500 mr-1">Sources</span>${webHtml}</div>` : ''}</div>`;
  }
  function glossaryHtml(items) {
    if (!Array.isArray(items) || !items.length) return '';
    return `<div class="flex flex-wrap gap-1 mt-2">${items.map(g => `<span class="pill text-slate-300 border-slate-600 cursor-help" title="${esc(g.meaning)}"><i data-lucide="book-a" class="w-3 h-3 mr-1 text-indigo-300"></i>${esc(g.term)}</span>`).join('')}</div>`;
  }
  function understoodHtml(u) {
    if (!u) return '';
    const bits = [];
    (u.countries || []).forEach(c => bits.push(`<span class="pill text-sky-300 border-sky-800"><i data-lucide="globe" class="w-3 h-3 mr-1"></i>${esc(c.name)}</span>`));
    if (u.category) bits.push(`<span class="pill text-amber-300 border-amber-800"><i data-lucide="hard-drive" class="w-3 h-3 mr-1"></i>${esc(u.category.name)}</span>`);
    (u.standards || []).forEach(s => bits.push(`<span class="pill mono text-indigo-300 border-indigo-800">${esc(s)}</span>`));
    if (u.pillar) bits.push(`<span class="pill ${PILLAR_PILL[u.pillar] || ''}">${esc(u.pillar)}</span>`);
    if (u.intent) bits.push(`<span class="pill text-slate-400 border-slate-700">intent: ${esc(u.intent)}</span>`);
    return bits.length ? `<div class="flex flex-wrap gap-1 mb-2"><span class="text-[10px] uppercase tracking-wider font-bold text-slate-500 self-center mr-1">Understood</span>${bits.join('')}</div>` : '';
  }
  function answerHtml(r, idx) {
    const isAi = r.generated_by && !/^rules/i.test(r.generated_by);
    const conf = r.confidence && r.confidence.level ? `<span class="badge ${CONF_CLS[r.confidence.level] || 'badge-neutral'}" title="${esc(r.confidence.basis || '')}">Confidence: ${esc(r.confidence.level)}</span>` : '';
    const details = (r.details || []).map((d, i) => sectionHtml(d, i === 0)).join('');
    const trail = (r.research_trail || []).length ? `<details class="rs-section"><summary><i data-lucide="footprints" class="w-3.5 h-3.5 text-indigo-300"></i><span>Research trail (${r.research_trail.length} steps)</span><i data-lucide="chevron-down" class="w-3.5 h-3.5 rs-chev"></i></summary><div class="rs-body !whitespace-normal"><ol class="list-decimal pl-4 space-y-1">${r.research_trail.map(t => `<li>${esc(t)}</li>`).join('')}</ol></div></details>` : '';
    const follow = (r.suggested_followups || []).length ? `<div class="mt-3 flex flex-wrap gap-1.5">${r.suggested_followups.map(q => `<button type="button" class="rs-chip" data-rs-ask="${esc(q)}"><i data-lucide="corner-down-right" class="w-3 h-3"></i>${esc(q)}</button>`).join('')}</div>` : '';
    return `<div class="rs-msg rs-bot" data-rs-idx="${idx}">
      <div class="flex items-center gap-1.5 mb-2 text-[10px] text-slate-400 flex-wrap">
        <i data-lucide="${isAi ? 'sparkles' : 'brain'}" class="w-3 h-3 text-indigo-300"></i>${isAi ? 'Claude · ' + esc(r.generated_by) : 'Rules engine (grounded)'}
        <span>· web: ${esc(r.network_status || 'offline')}</span>${r.answered_at ? `<span>· ${esc(GCM.ui.fmtDateTime(r.answered_at))}</span>` : ''}<span class="ml-auto">${conf}</span></div>
      ${understoodHtml(r.understood)}
      <div class="text-[12.5px] text-white leading-relaxed ${r.out_of_scope ? 'text-amber-200' : ''}" data-role="direct">${esc(r.direct_answer)}</div>
      ${tableHtml(r.requirements_table)}
      ${details ? `<div class="mt-3 space-y-1.5">${details}</div>` : ''}
      <div class="mt-2 space-y-1.5">${evidenceHtml(r.evidence)}${trail}</div>
      ${sourcesHtml(r.web_sources, r.alerts)}
      ${glossaryHtml(r.glossary)}
      ${follow}
    </div>`;
  }
  function userHtml(q) { return `<div class="rs-msg rs-user">${esc(q)}</div>`; }
  function loadingHtml(id) {
    return `<div class="rs-msg rs-bot" id="${id}"><div class="space-y-1.5">${STEPS.map((s, i) => `<div class="rs-step ${i === 0 ? 'active' : ''}" data-step="${i}"><span class="dot"></span><span>${esc(s)}…</span></div>`).join('')}</div></div>`;
  }
  function welcomeHtml() {
    return `<div class="rs-msg rs-bot">
      <div class="flex items-center gap-1.5 mb-1 text-[10px] text-slate-400"><i data-lucide="brain" class="w-3 h-3 text-indigo-300"></i>Research assistant</div>
      <div class="text-white">Ask me anything about market access for storage products - certification needs, exemptions, marks and documents, standard clauses and limits, deadlines, or which of your products an alert touches.</div>
      <div class="text-slate-400 mt-1">I always start from the shipped knowledge base (205 jurisdictions × 11 product categories, alert register, standards primer) and add web sources when the machine is online. Every brief shows its evidence and research trail.</div>
    </div>`;
  }

  /* ------------------------------------------------------------------ state & flow */
  function transcript() { return $('rs-transcript'); }
  function scrollEnd() { const t = transcript(); if (t) t.scrollTop = t.scrollHeight; }
  function renderSuggestions() {
    const host = $('rs-suggestions'); if (!host) return;
    if (S.history.length || !S.suggestions.length) { host.innerHTML = ''; return; }
    host.innerHTML = `<span class="text-[10px] uppercase tracking-wider font-bold text-slate-500 self-center mr-1">Try</span>` + S.suggestions.map(q => `<button type="button" class="rs-chip" data-rs-ask="${esc(q)}"><i data-lucide="sparkles" class="w-3 h-3"></i>${esc(q)}</button>`).join('');
    GCM.ui.icons(host);
  }
  async function loadSuggestions() {
    if (S.suggestions.length) return;
    try { const r = await GCM.api.get('/api/expert/suggestions'); S.suggestions = Array.isArray(r.suggestions) ? r.suggestions : []; } catch (_) { S.suggestions = []; }
  }
  async function refreshPills() {
    const ep = $('rs-engine-pill'); const np = $('rs-net-pill');
    try {
      const st = await GCM.api.get('/api/ai/status'); S.aiStatus = st;
      if (ep) {
        ep.innerHTML = st.active ? `<span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span><span>Engine: Claude · ${esc(st.model)}</span>` : `<span class="w-1.5 h-1.5 rounded-full bg-slate-500"></span><span>Engine: rules (grounded)</span>`;
        ep.title = st.active ? 'Claude writes the narrative, grounded only on gathered material.' : 'Deterministic grounded brief. Add an Anthropic API key in Settings to let Claude write the narrative.';
      }
    } catch (_) { if (ep) ep.innerHTML = '<span>Engine: rules (grounded)</span>'; }
    if (np) {
      const ns = S.last && S.last.network_status;
      np.innerHTML = ns === 'online' ? `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span><span>Web: online</span>` : ns === 'offline' ? `<span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span><span>Web: offline</span>` : `<span class="w-1.5 h-1.5 rounded-full bg-slate-500"></span><span>Web: checked on first question</span>`;
      np.title = ns === 'online' ? 'Live web research succeeded on the last question.' : ns === 'offline' ? 'Web search unavailable - briefs rely on internal sources and curated references.' : 'Web availability is tested when you ask.';
    }
  }
  function setBusy(b) {
    S.busy = b;
    const inp = $('rs-input'); const btn = $('rs-send');
    if (inp) inp.disabled = b;
    if (btn) GCM.ui.setLoading(btn, b, 'Researching…');
  }
  function animateSteps(id) {
    let i = 0;
    const t = setInterval(() => {
      const box = $(id); if (!box) { clearInterval(t); return; }
      const steps = box.querySelectorAll('.rs-step');
      if (i < steps.length - 1) { steps[i].classList.remove('active'); steps[i].classList.add('done'); i++; steps[i].classList.add('active'); }
    }, 1400);
    return () => clearInterval(t);
  }
  function revealText(el, text) {
    const words = String(text).split(/(\s+)/); let i = 0; el.textContent = '';
    const tick = () => { const n = Math.min(words.length, i + 5); el.textContent += words.slice(i, n).join(''); i = n; scrollEnd(); if (i < words.length) setTimeout(tick, 14); };
    tick();
  }

  async function ask(question) {
    question = String(question || '').replace(/\s+/g, ' ').trim().slice(0, 1000);
    if (!question || S.busy) return;
    const inp = $('rs-input'); if (inp) { inp.value = ''; updateCount(); }
    setBusy(true);
    const t = transcript();
    if (!S.history.length && t) t.innerHTML = '';
    S.history.push({ role: 'user', content: question });
    renderSuggestions();
    const loadId = `rs-loading-${++S.seq}`;
    if (t) { t.insertAdjacentHTML('beforeend', userHtml(question)); t.insertAdjacentHTML('beforeend', loadingHtml(loadId)); scrollEnd(); }
    const stop = animateSteps(loadId);
    try {
      const historyForApi = S.history.slice(0, -1).slice(-6).map(m => ({ role: m.role, content: m.content }));
      const r = await GCM.api.post('/api/expert/research', { question, history: historyForApi });
      stop();
      S.last = r;
      S.history.push({ role: 'assistant', content: r.direct_answer || '', meta: r });
      const box = $(loadId);
      if (box) {
        box.outerHTML = answerHtml(r, S.history.length - 1);
        const last = t && t.lastElementChild; const direct = last && last.querySelector('[data-role=direct]');
        if (direct) revealText(direct, r.direct_answer || '');
        GCM.ui.icons(t);
      }
      $('rs-copy').disabled = false; $('rs-action').disabled = false;
      refreshPills();
    } catch (e) {
      stop();
      const box = $(loadId); if (box) box.remove();
      S.history.push({ role: 'assistant', content: `Sorry - the research assistant could not answer: ${e.message}`, meta: null });
      if (t) { t.insertAdjacentHTML('beforeend', `<div class="rs-msg rs-bot text-rose-200"><i data-lucide="alert-triangle" class="w-3.5 h-3.5 inline -mt-0.5 mr-1 text-rose-400"></i>${esc(S.history[S.history.length - 1].content)}</div>`); GCM.ui.icons(t); }
      GCM.ui.toast('Research unavailable', e.message, 'error');
    } finally { setBusy(false); scrollEnd(); const i2 = $('rs-input'); if (i2) i2.focus(); }
  }

  function clearThread() {
    S.history = []; S.last = null;
    const t = transcript(); if (t) { t.innerHTML = welcomeHtml(); GCM.ui.icons(t); }
    $('rs-copy').disabled = true; $('rs-action').disabled = true;
    renderSuggestions();
  }
  function copyBrief() {
    const r = S.last; if (!r) return;
    const lines = [`Q: ${r.question}`, '', `Answer: ${r.direct_answer}`, ''];
    (r.details || []).forEach(d => { lines.push(String(d.heading || '').toUpperCase()); lines.push(d.body || ''); lines.push(''); });
    (r.requirements_table || []).forEach(row => {
      lines.push(`${row.country} · ${row.category} · ${row.requirement_type}`);
      (row.pillars || []).forEach(p => lines.push(`  - ${p.pillar}: ${p.status}${p.standard ? ' - ' + p.standard : ''}${p.route ? ' via ' + p.route : ''}${p.note ? ' (' + p.note + ')' : ''}`));
      if ((row.documents || []).length) { lines.push('  Documents:'); row.documents.forEach(d => lines.push(`    - ${d}`)); }
      lines.push('');
    });
    if ((r.evidence || []).length) { lines.push('EVIDENCE'); r.evidence.forEach(e => lines.push(`- "${e.text}" - ${e.source}`)); lines.push(''); }
    if ((r.web_sources || []).length) { lines.push('SOURCES'); r.web_sources.forEach(s => lines.push(`- ${s.title} - ${s.url}`)); lines.push(''); }
    if (r.confidence) lines.push(`Confidence: ${r.confidence.level} - ${r.confidence.basis || ''}`);
    lines.push(`Generated by: ${r.generated_by} · web: ${r.network_status} · ${r.answered_at}`);
    GCM.ui.copy(lines.join('\n'));
  }
  function createAction() {
    const r = S.last; if (!r) return;
    const u = r.understood || {};
    const c = (u.countries || [])[0]; const cat = u.category;
    const alertId = (r.alerts || [])[0] && r.alerts[0].id;
    const title = `Research follow-up: ${r.question}`.slice(0, 120);
    const notes = `${r.direct_answer}\n\nConfidence: ${r.confidence ? r.confidence.level : '—'}. Source: Ask the Expert (${r.generated_by}, web ${r.network_status}).`;
    const linked_type = alertId ? 'alert' : (c && c.code && c.code !== 'EU' ? 'country' : null);
    const linked_id = alertId || (c && c.code !== 'EU' ? c.code : null);
    GCM.actions.createFor(linked_type, linked_id, { title, notes, priority: r.alerts && r.alerts.length ? 'High' : 'Medium', owner: '' });
    void cat;
  }
  function updateCount() { const i = $('rs-input'); const c = $('rs-count'); if (i && c) c.textContent = `${i.value.length} / 1000`; }

  async function open(question) {
    GCM.ui.openModal(MODAL);
    const t = transcript();
    if (t && !t.children.length) { t.innerHTML = welcomeHtml(); GCM.ui.icons(t); }
    await loadSuggestions(); renderSuggestions(); refreshPills();
    const inp = $('rs-input');
    if (question) { if (inp) inp.value = String(question); ask(question); }
    else if (inp) setTimeout(() => inp.focus(), 60);
  }

  GCM.research = { open, ask, clear: clearThread };

  GCM.modules.research = {
    init() {
      const form = $('rs-form');
      if (form) form.addEventListener('submit', (e) => { e.preventDefault(); ask($('rs-input').value); });
      const inp = $('rs-input');
      if (inp) {
        inp.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(inp.value); } });
        inp.addEventListener('input', updateCount);
      }
      const t = transcript();
      if (t) t.addEventListener('click', (e) => {
        const chip = e.target.closest('[data-rs-ask]'); if (chip) { ask(chip.dataset.rsAsk); return; }
        const al = e.target.closest('[data-rs-alert]'); if (al) { GCM.ui.closeModal(MODAL); GCM.deeplink.alert(al.dataset.rsAlert); }
      });
      const sug = $('rs-suggestions');
      if (sug) sug.addEventListener('click', (e) => { const chip = e.target.closest('[data-rs-ask]'); if (chip) ask(chip.dataset.rsAsk); });
      const cp = $('rs-copy'); if (cp) cp.addEventListener('click', copyBrief);
      const ac = $('rs-action'); if (ac) ac.addEventListener('click', createAction);
      const cl = $('rs-clear'); if (cl) cl.addEventListener('click', clearThread);
      GCM.bus.on('action:open-expert', () => open());
      GCM.bus.on('expert:open', (q) => open(typeof q === 'string' ? q : (q && q.question) || ''));
      GCM.bus.on('settings:changed', () => { S.aiStatus = null; refreshPills(); });
      GCM.palette.register({ label: 'Ask the Expert (regulatory research)', hint: 'Any question', icon: 'sparkles', keywords: ['expert', 'ask', 'research', 'question', 'assistant', 'ai'], run: () => open() });
    },
  };
})();
