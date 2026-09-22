/* =====================================================================
   GCM Platform 2.0 - core.js
   Shared runtime: API client, UI helpers, tabs, modals, toasts, event bus,
   command palette, settings, actions drawer, deep links.
   Every feature module registers itself on GCM.modules.<name>.
   ===================================================================== */
(function () {
  'use strict';

  const GCM = (window.GCM = window.GCM || {});
  GCM.modules = GCM.modules || {};
  GCM.state = { categories: [], countries: {}, settings: {}, alerts: [], ready: false };

  /* ------------------------------------------------------------------ bus */
  const listeners = {};
  GCM.bus = {
    on(evt, fn) { (listeners[evt] = listeners[evt] || []).push(fn); return () => GCM.bus.off(evt, fn); },
    off(evt, fn) { listeners[evt] = (listeners[evt] || []).filter(f => f !== fn); },
    emit(evt, payload) { (listeners[evt] || []).forEach(fn => { try { fn(payload); } catch (e) { console.error(`[bus:${evt}]`, e); } }); },
  };

  /* ------------------------------------------------------------------ api */
  async function request(method, url, body, opts = {}) {
    const init = { method, headers: {} };
    if (body instanceof FormData) { init.body = body; }
    else if (body !== undefined) { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(body); }
    let res;
    try { res = await fetch(url, init); }
    catch (e) { const err = new Error('Server unreachable. Is the GCM Platform still running?'); err.status = 0; throw err; }
    let data = null;
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) { try { data = await res.json(); } catch (_) { data = null; } }
    else if (!opts.raw) { try { data = { text: await res.text() }; } catch (_) { data = null; } }
    if (!res.ok) {
      const err = new Error((data && (data.error || data.message)) || `${res.status} ${res.statusText}`);
      err.status = res.status; err.data = data; throw err;
    }
    return data;
  }
  GCM.api = {
    get: (url) => request('GET', url),
    post: (url, body) => request('POST', url, body === undefined ? {} : body),
    patch: (url, body) => request('PATCH', url, body || {}),
    del: (url) => request('DELETE', url),
    upload: (url, formData) => request('POST', url, formData),
    download(url, label) {
      GCM.ui.toast(label || 'Preparing download…', 'Your file will download in a moment.', 'info');
      const a = document.createElement('a'); a.href = url; a.download = ''; a.rel = 'noopener';
      document.body.appendChild(a); a.click(); a.remove();
    },
  };

  /* ------------------------------------------------------------------ ui */
  const SEV = {
    critical: 'badge badge-critical', warning: 'badge badge-warning', info: 'badge badge-info',
    success: 'badge badge-success', neutral: 'badge badge-neutral',
  };
  GCM.ui = {
    esc(s) {
      if (s === null || s === undefined) return '';
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    },
    icons(root) {
      if (!window.lucide) return;
      try { root ? window.lucide.createIcons({ nameAttr: 'data-lucide' }) : window.lucide.createIcons(); } catch (e) { /* ignore */ }
    },
    severityClass(sev) {
      const k = String(sev || '').toLowerCase();
      if (k.startsWith('crit')) return SEV.critical;
      if (k.startsWith('warn') || k === 'high' || k === 'medium') return SEV.warning;
      if (k.startsWith('info') || k === 'low') return SEV.info;
      if (k === 'success' || k.startsWith('compl') || k === 'done' || k === 'valid') return SEV.success;
      return SEV.neutral;
    },
    badge(text, kind) { return `<span class="${SEV[kind] || GCM.ui.severityClass(kind || text)}">${GCM.ui.esc(text)}</span>`; },
    fmtDate(iso) {
      if (!iso) return '—';
      const d = new Date(String(iso).length === 10 ? iso + 'T00:00:00' : iso);
      if (isNaN(d)) return String(iso);
      return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: '2-digit' });
    },
    fmtDateTime(iso) {
      if (!iso) return '—';
      const d = new Date(iso); if (isNaN(d)) return String(iso);
      return d.toLocaleString(undefined, { year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    },
    daysUntil(iso) {
      if (!iso || !/^\d{4}-\d{2}-\d{2}/.test(String(iso))) return null;
      const d = new Date(String(iso).slice(0, 10) + 'T00:00:00');
      const t = new Date(); t.setHours(0, 0, 0, 0);
      return Math.round((d - t) / 86400000);
    },
    relDays(iso) {
      const n = GCM.ui.daysUntil(iso);
      if (n === null) return '';
      if (n === 0) return 'today';
      if (n > 0) return `in ${n} day${n === 1 ? '' : 's'}`;
      return `${-n} day${n === -1 ? '' : 's'} ago`;
    },
    deadlineTone(iso) {
      const n = GCM.ui.daysUntil(iso);
      if (n === null) return 'neutral';
      if (n < 0) return 'critical';
      if (n <= 90) return 'warning';
      if (n <= 365) return 'info';
      return 'success';
    },
    flag(code) {
      if (!code || String(code).length !== 2 || !/^[A-Za-z]{2}$/.test(code)) return '🌐';
      // Windows has no colour flag emoji font; regional indicators render as bare letters, so show nothing there.
      if (/Win/i.test(navigator.platform || '')) return '';
      return String.fromCodePoint(...code.toUpperCase().split('').map(c => 127397 + c.charCodeAt(0)));
    },
    num(n) { return (n === null || n === undefined || isNaN(n)) ? '—' : Number(n).toLocaleString(); },
    money(low, high) {
      const f = v => '$' + Math.round(v).toLocaleString();
      if (low == null && high == null) return '—';
      if (high == null || high === low) return f(low);
      return `${f(low)} – ${f(high)}`;
    },
    skeleton(rows = 3) {
      return Array.from({ length: rows }).map(() => '<div class="skeleton h-14 w-full rounded-xl"></div>').join('');
    },
    empty(msg, icon = 'inbox') {
      return `<div class="empty-state"><i data-lucide="${GCM.ui.esc(icon)}" class="w-8 h-8 text-slate-600 mx-auto mb-2"></i><div>${GCM.ui.esc(msg)}</div></div>`;
    },
    toast(title, sub, kind = 'success') {
      const host = document.getElementById('toast-host'); if (!host) return;
      const colors = { success: 'border-emerald-500 text-emerald-300', info: 'border-sky-500 text-sky-300', warning: 'border-amber-500 text-amber-300', error: 'border-rose-500 text-rose-300' };
      const icons = { success: 'check-circle-2', info: 'info', warning: 'alert-triangle', error: 'x-circle' };
      const el = document.createElement('div');
      el.className = `toast ${colors[kind] || colors.info}`;
      el.innerHTML = `<i data-lucide="${icons[kind] || 'info'}" class="w-5 h-5 shrink-0"></i><div class="min-w-0"><div class="text-xs font-bold text-white truncate">${GCM.ui.esc(title)}</div>${sub ? `<div class="text-[11px] text-slate-300 leading-snug">${GCM.ui.esc(sub)}</div>` : ''}</div><button class="ml-2 text-slate-400 hover:text-white" aria-label="Dismiss"><i data-lucide="x" class="w-4 h-4"></i></button>`;
      el.querySelector('button').onclick = () => el.remove();
      host.appendChild(el); GCM.ui.icons();
      setTimeout(() => { el.classList.add('toast-out'); setTimeout(() => el.remove(), 300); }, kind === 'error' ? 8000 : 4500);
    },
    notify({ title, body, scope, actions = [] }) {
      const banner = document.getElementById('top-notification'); if (!banner) return;
      banner.querySelector('[data-role=title]').textContent = title || 'Notification';
      banner.querySelector('[data-role=body]').textContent = body || '';
      banner.querySelector('[data-role=scope]').textContent = scope || '';
      banner.querySelector('[data-role=time]').textContent = new Date().toLocaleTimeString();
      const act = banner.querySelector('[data-role=actions]'); act.innerHTML = '';
      actions.forEach(a => { const b = document.createElement('button'); b.className = 'btn btn-sm btn-secondary'; b.textContent = a.label; b.onclick = () => { banner.classList.add('hidden'); a.run && a.run(); }; act.appendChild(b); });
      banner.classList.remove('hidden'); GCM.ui.icons();
      clearTimeout(banner._t); banner._t = setTimeout(() => banner.classList.add('hidden'), 9000);
    },
    openModal(id) { const el = document.getElementById(id); if (!el) return; el.classList.remove('hidden'); el.setAttribute('aria-hidden', 'false'); document.body.classList.add('modal-open'); GCM.ui.icons(); const f = el.querySelector('[autofocus]'); if (f) setTimeout(() => f.focus(), 50); },
    closeModal(id) { const el = document.getElementById(id); if (!el) return; el.classList.add('hidden'); el.setAttribute('aria-hidden', 'true'); if (!document.querySelector('.modal:not(.hidden)')) document.body.classList.remove('modal-open'); },
    confirm(message, { title = 'Please confirm', okLabel = 'Confirm', danger = false } = {}) {
      return new Promise(resolve => {
        const m = document.getElementById('modal-confirm'); if (!m) return resolve(window.confirm(message));
        m.querySelector('[data-role=title]').textContent = title;
        m.querySelector('[data-role=message]').textContent = message;
        const ok = m.querySelector('[data-role=ok]'); ok.textContent = okLabel; ok.className = `btn ${danger ? 'btn-danger' : 'btn-primary'}`;
        const done = v => { GCM.ui.closeModal('modal-confirm'); resolve(v); };
        ok.onclick = () => done(true); m.querySelector('[data-role=cancel]').onclick = () => done(false);
        GCM.ui.openModal('modal-confirm');
      });
    },
    setLoading(btn, loading, label) {
      if (!btn) return;
      if (loading) { btn.dataset.orig = btn.innerHTML; btn.disabled = true; btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>${GCM.ui.esc(label || 'Working…')}</span>`; }
      else { btn.disabled = false; if (btn.dataset.orig) btn.innerHTML = btn.dataset.orig; }
      GCM.ui.icons();
    },
    copy(text) { try { navigator.clipboard.writeText(text); GCM.ui.toast('Copied to clipboard'); } catch (_) { /* ignore */ } },
  };

  /* ------------------------------------------------------------------ tabs */
  const shown = new Set();
  GCM.tabs = {
    current: 'overview',
    switchTo(id, opts = {}) {
      const target = document.getElementById(`tab-content-${id}`);
      const btn = document.getElementById(`tab-btn-${id}`);
      if (!target || !btn) return;
      document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(el => { el.classList.remove('active'); el.setAttribute('aria-selected', 'false'); });
      target.classList.remove('hidden'); btn.classList.add('active'); btn.setAttribute('aria-selected', 'true');
      GCM.tabs.current = id;
      if (!opts.silent) { try { history.replaceState(null, '', `#${id}`); } catch (_) { /* ignore */ } }
      const mod = GCM.modules[id];
      if (mod) {
        if (!shown.has(id)) { shown.add(id); try { mod.onFirstShow && mod.onFirstShow(); } catch (e) { console.error(e); } }
        try { mod.onShow && mod.onShow(); } catch (e) { console.error(e); }
      }
      GCM.bus.emit('tab:shown', id); GCM.ui.icons();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
  };

  /* ------------------------------------------------------------------ deep links */
  GCM.deeplink = {
    alert(id) { GCM.tabs.switchTo('alerts'); setTimeout(() => GCM.bus.emit('alerts:focus', id), 120); },
    country(code) { GCM.tabs.switchTo('map'); setTimeout(() => GCM.bus.emit('map:focus', code), 200); },
    product(id) { GCM.tabs.switchTo('portfolio'); setTimeout(() => GCM.bus.emit('portfolio:focus', id), 120); },
    document(idx) { GCM.tabs.switchTo('docaudit'); setTimeout(() => GCM.bus.emit('docaudit:focus', idx), 120); },
  };

  /* ------------------------------------------------------------------ command palette */
  const commands = [];
  GCM.palette = {
    register(cmd) { commands.push(cmd); },
    open() { const m = document.getElementById('modal-palette'); if (!m) return; GCM.ui.openModal('modal-palette'); const inp = m.querySelector('input'); inp.value = ''; renderPalette(''); inp.focus(); },
  };
  let paletteResults = []; let paletteIdx = 0; let paletteTimer = null;
  async function renderPalette(q) {
    const list = document.getElementById('palette-results'); if (!list) return;
    const ql = q.trim().toLowerCase();
    let items = commands.filter(c => !ql || c.label.toLowerCase().includes(ql) || (c.keywords || []).some(k => k.includes(ql)))
      .slice(0, ql ? 6 : 10).map(c => ({ type: 'command', title: c.label, subtitle: c.hint || '', icon: c.icon || 'command', run: c.run }));
    if (ql.length >= 2) {
      try {
        const r = await GCM.api.get(`/api/search?q=${encodeURIComponent(ql)}`);
        (r.results || []).slice(0, 14).forEach(x => items.push({
          type: x.type, title: x.title, subtitle: x.subtitle || '', icon: x.icon || ({ country: 'globe', alert: 'bell', product: 'hard-drive', standard: 'book-open', document: 'file-text', action: 'check-square' }[x.type] || 'search'),
          run: () => {
            if (x.type === 'country') GCM.deeplink.country(x.id);
            else if (x.type === 'alert') GCM.deeplink.alert(x.id);
            else if (x.type === 'product') GCM.deeplink.product(x.id);
            else if (x.type === 'standard') { GCM.tabs.switchTo('matrix'); GCM.bus.emit('matrix:search', x.title); }
            else if (x.tab) GCM.tabs.switchTo(x.tab);
          },
        }));
      } catch (_) { /* offline search unavailable */ }
    }
    paletteResults = items; paletteIdx = 0;
    list.innerHTML = items.length ? items.map((it, i) => `
      <button class="palette-item ${i === 0 ? 'active' : ''}" data-idx="${i}">
        <i data-lucide="${GCM.ui.esc(it.icon)}" class="w-4 h-4 text-slate-400 shrink-0"></i>
        <div class="min-w-0 flex-1"><div class="text-xs font-semibold text-slate-100 truncate">${GCM.ui.esc(it.title)}</div>${it.subtitle ? `<div class="text-[11px] text-slate-400 truncate">${GCM.ui.esc(it.subtitle)}</div>` : ''}</div>
        <span class="pill">${GCM.ui.esc(it.type)}</span></button>`).join('') : GCM.ui.empty('No matches. Try a country, standard, SKU or alert keyword.', 'search');
    list.querySelectorAll('.palette-item').forEach(b => b.onclick = () => runPalette(+b.dataset.idx));
    GCM.ui.icons();
  }
  function runPalette(i) { const it = paletteResults[i]; if (!it) return; GCM.ui.closeModal('modal-palette'); try { it.run && it.run(); } catch (e) { console.error(e); } }
  function paletteKey(e) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault(); const n = paletteResults.length; if (!n) return;
      paletteIdx = (paletteIdx + (e.key === 'ArrowDown' ? 1 : n - 1)) % n;
      document.querySelectorAll('.palette-item').forEach((b, i) => b.classList.toggle('active', i === paletteIdx));
    } else if (e.key === 'Enter') { e.preventDefault(); runPalette(paletteIdx); }
  }

  /* ------------------------------------------------------------------ actions (tasks) */
  GCM.actions = {
    createFor(linked_type, linked_id, defaults = {}) {
      const m = document.getElementById('modal-action'); if (!m) return;
      m.querySelector('[name=title]').value = defaults.title || '';
      m.querySelector('[name=priority]').value = defaults.priority || 'High';
      m.querySelector('[name=owner]').value = defaults.owner || '';
      m.querySelector('[name=due_date]').value = defaults.due_date || '';
      m.querySelector('[name=notes]').value = defaults.notes || '';
      m.dataset.linkedType = linked_type || ''; m.dataset.linkedId = linked_id || '';
      m.querySelector('[data-role=linked]').textContent = linked_type ? `${linked_type}: ${linked_id}` : 'Not linked';
      GCM.ui.openModal('modal-action');
    },
    async submit() {
      const m = document.getElementById('modal-action'); if (!m) return;
      const title = m.querySelector('[name=title]').value.trim();
      if (!title) { GCM.ui.toast('Title required', 'Give the action a short, clear title.', 'warning'); return; }
      const body = {
        title, priority: m.querySelector('[name=priority]').value, owner: m.querySelector('[name=owner]').value.trim(),
        due_date: m.querySelector('[name=due_date]').value, notes: m.querySelector('[name=notes]').value.trim(),
        linked_type: m.dataset.linkedType || null, linked_id: m.dataset.linkedId || null,
      };
      try { await GCM.api.post('/api/actions', body); GCM.ui.closeModal('modal-action'); GCM.ui.toast('Action created', title); GCM.bus.emit('actions:changed'); }
      catch (e) { GCM.ui.toast('Could not create action', e.message, 'error'); }
    },
  };

  /* ------------------------------------------------------------------ settings */
  GCM.settings = {
    async load() { try { GCM.state.settings = await GCM.api.get('/api/settings'); } catch (_) { GCM.state.settings = {}; } return GCM.state.settings; },
    async open() {
      await GCM.settings.load();
      const s = GCM.state.settings; const m = document.getElementById('modal-settings'); if (!m) return;
      m.querySelector('[name=company_name]').value = s.company_name || '';
      m.querySelector('[name=ai_model]').value = s.ai_model || 'claude-opus-5';
      m.querySelector('[name=ai_enabled]').checked = s.ai_enabled !== false;
      m.querySelector('[name=anthropic_api_key]').value = '';
      m.querySelector('[name=anthropic_api_key]').placeholder = s.api_key_configured ? `Configured (${s.anthropic_api_key})${s.api_key_from_env ? ' via environment variable' : ''} — leave blank to keep` : 'sk-ant-… (optional: enables Claude AI explanations)';
      m.querySelector('[name=surveillance_auto_scan_hours]').value = s.surveillance_auto_scan_hours || 0;
      m.querySelector('[data-role=data-dir]').textContent = s.data_dir || '';
      m.querySelector('[data-role=version]').textContent = `v${s.version || ''} ${s.codename ? '“' + s.codename + '”' : ''} ${s.frozen ? '(standalone build)' : '(developer mode)'}`;
      GCM.ui.openModal('modal-settings');
    },
    async save() {
      const m = document.getElementById('modal-settings'); if (!m) return;
      const body = {
        company_name: m.querySelector('[name=company_name]').value.trim(),
        ai_model: m.querySelector('[name=ai_model]').value,
        ai_enabled: m.querySelector('[name=ai_enabled]').checked,
        surveillance_auto_scan_hours: Number(m.querySelector('[name=surveillance_auto_scan_hours]').value) || 0,
      };
      const key = m.querySelector('[name=anthropic_api_key]').value.trim();
      if (key) body.anthropic_api_key = key;
      if (m.querySelector('[name=clear_key]').checked) body.anthropic_api_key = '';
      try {
        const r = await GCM.api.post('/api/settings', body);
        GCM.state.settings = r.settings || GCM.state.settings;
        GCM.ui.closeModal('modal-settings'); GCM.ui.toast('Settings saved'); GCM.bus.emit('settings:changed', GCM.state.settings); refreshAiPill();
      } catch (e) { GCM.ui.toast('Could not save settings', e.message, 'error'); }
    },
  };
  async function refreshAiPill() {
    const pill = document.getElementById('ai-mode-pill'); if (!pill) return;
    try {
      const st = await GCM.api.get('/api/ai/status');
      pill.innerHTML = st.enabled && st.configured
        ? `<span class="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span><span>AI: ${GCM.ui.esc(st.model)}</span>`
        : `<span class="w-1.5 h-1.5 rounded-full bg-slate-500"></span><span>AI: rules engine</span>`;
      pill.title = st.enabled && st.configured ? 'Claude-enhanced explanations are active' : 'Built-in deterministic explainer active. Add an Anthropic API key in Settings to enable Claude.';
    } catch (_) { pill.innerHTML = '<span>AI: rules engine</span>'; }
  }

  /* ------------------------------------------------------------------ bootstrap */
  async function loadBaseState() {
    const [cats, countries] = await Promise.all([
      GCM.api.get('/api/categories').catch(() => []),
      GCM.api.get('/api/countries').catch(() => []),
    ]);
    GCM.state.categories = Array.isArray(cats) ? cats : [];
    GCM.state.countries = {};
    (Array.isArray(countries) ? countries : []).forEach(c => { GCM.state.countries[c.code] = c; });
    await GCM.settings.load();
  }

  function wireGlobalHandlers() {
    // delegated data-action buttons
    document.addEventListener('click', (e) => {
      const el = e.target.closest('[data-action]'); if (!el) return;
      const act = el.dataset.action; const arg = el.dataset.arg;
      switch (act) {
        case 'tab': GCM.tabs.switchTo(arg); break;
        case 'open-modal': GCM.ui.openModal(arg); break;
        case 'close-modal': GCM.ui.closeModal(arg || el.closest('.modal')?.id); break;
        case 'palette': GCM.palette.open(); break;
        case 'settings': GCM.settings.open(); break;
        case 'settings-save': GCM.settings.save(); break;
        case 'action-submit': GCM.actions.submit(); break;
        case 'new-action': GCM.actions.createFor(null, null, {}); break;
        case 'dismiss-notification': document.getElementById('top-notification')?.classList.add('hidden'); break;
        case 'backup-download': GCM.api.download('/api/backup', 'Preparing backup…'); break;
        case 'deeplink-alert': GCM.deeplink.alert(arg); break;
        case 'deeplink-country': GCM.deeplink.country(arg); break;
        case 'deeplink-product': GCM.deeplink.product(arg); break;
        default: GCM.bus.emit(`action:${act}`, { arg, el, event: e });
      }
    });
    // close modal on backdrop click / Escape
    document.addEventListener('click', (e) => { if (e.target.classList && e.target.classList.contains('modal')) GCM.ui.closeModal(e.target.id); });
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); GCM.palette.open(); return; }
      if (e.key === 'Escape') { const open = [...document.querySelectorAll('.modal:not(.hidden)')].pop(); if (open) GCM.ui.closeModal(open.id); return; }
      if (e.target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
      const tabKeys = { '1': 'overview', '2': 'matrix', '3': 'map', '4': 'alerts', '5': 'horizon', '6': 'portfolio', '7': 'docaudit' };
      if (e.altKey && tabKeys[e.key]) { e.preventDefault(); GCM.tabs.switchTo(tabKeys[e.key]); }
      if (e.key === '?' ) { GCM.ui.openModal('modal-help'); }
    });
    const pInput = document.querySelector('#modal-palette input');
    if (pInput) {
      pInput.addEventListener('input', () => { clearTimeout(paletteTimer); paletteTimer = setTimeout(() => renderPalette(pInput.value), 120); });
      pInput.addEventListener('keydown', paletteKey);
    }
    // hash deep-link on load
    window.addEventListener('hashchange', () => { const id = location.hash.replace('#', ''); if (id && document.getElementById(`tab-content-${id}`)) GCM.tabs.switchTo(id, { silent: true }); });
  }

  function registerCoreCommands() {
    const tabs = [['overview', 'Go to Overview', 'layout-dashboard'], ['matrix', 'Go to Testing vs. Document Matrix', 'layers'], ['map', 'Go to Global Access Map', 'globe-2'],
      ['alerts', 'Go to Regulation Alerts', 'bell'], ['horizon', 'Go to Regulatory Horizon & Risk', 'radar'], ['portfolio', 'Go to Product Portfolio', 'hard-drive'], ['docaudit', 'Go to Document Impact Audit', 'file-search-2']];
    tabs.forEach(([id, label, icon]) => GCM.palette.register({ label, hint: `Alt+${tabs.findIndex(t => t[0] === id) + 1}`, icon, keywords: [id, 'tab', 'go'], run: () => GCM.tabs.switchTo(id) }));
    GCM.palette.register({ label: 'Open Settings', icon: 'settings', keywords: ['settings', 'api key', 'claude', 'ai'], run: () => GCM.settings.open() });
    GCM.palette.register({ label: 'Create action item', icon: 'plus-square', keywords: ['task', 'todo', 'action'], run: () => GCM.actions.createFor(null, null, {}) });
    GCM.palette.register({ label: 'Export compliance matrix to Excel (current view)', icon: 'file-spreadsheet', keywords: ['excel', 'export', 'xlsx', 'matrix'], run: () => GCM.bus.emit('matrix:export', false) });
    GCM.palette.register({ label: 'Scan regulatory feeds now', icon: 'radar', keywords: ['surveillance', 'scan', 'feeds'], run: () => GCM.bus.emit('surveillance:scan') });
    GCM.palette.register({ label: 'Open surveillance ledger', icon: 'scroll-text', keywords: ['ledger', 'audit log', 'surveillance'], run: () => GCM.bus.emit('surveillance:log') });
    GCM.palette.register({ label: 'Keyboard shortcuts & help', icon: 'keyboard', keywords: ['help', 'shortcuts'], run: () => GCM.ui.openModal('modal-help') });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    GCM.ui.icons();
    wireGlobalHandlers();
    registerCoreCommands();
    try { await loadBaseState(); } catch (e) { console.error('Base state failed', e); }
    Object.entries(GCM.modules).forEach(([name, mod]) => { try { mod.init && mod.init(); } catch (e) { console.error(`[${name}.init]`, e); } });
    GCM.state.ready = true; GCM.bus.emit('ready');
    refreshAiPill();
    const initial = location.hash.replace('#', '');
    GCM.tabs.switchTo(initial && document.getElementById(`tab-content-${initial}`) ? initial : 'overview', { silent: true });
    // first-run help
    try { if (!localStorage.getItem('gcm.seen.v2')) { localStorage.setItem('gcm.seen.v2', '1'); setTimeout(() => GCM.ui.openModal('modal-help'), 600); } } catch (_) { /* ignore */ }
  });
})();
