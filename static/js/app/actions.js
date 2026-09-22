/* actions.js - action-item (task) tracker widget used by the Overview tab; exposes GCM.actionsPanel.render(container) */
(function () {
  'use strict';
  const GCM = window.GCM;
  const STATUSES = ['Open', 'In Progress', 'Blocked', 'Done'];
  const PRIO = { Critical: 'badge-critical', High: 'badge-warning', Medium: 'badge-info', Low: 'badge-neutral' };
  let cache = [];

  async function load() {
    try { const r = await GCM.api.get('/api/actions'); cache = r.actions || []; } catch (e) { cache = []; }
    return cache;
  }

  function linkedLabel(a) {
    if (!a.linked_type) return '';
    const t = a.linked_type; const id = a.linked_id || '';
    const act = { alert: 'deeplink-alert', product: 'deeplink-product', country: 'deeplink-country' }[t];
    return act ? `<button class="pill hover:text-white" data-action="${act}" data-arg="${GCM.ui.esc(id)}">${GCM.ui.esc(t)}: ${GCM.ui.esc(id)}</button>` : `<span class="pill">${GCM.ui.esc(t)}: ${GCM.ui.esc(id)}</span>`;
  }

  function render(container, opts = {}) {
    if (!container) return;
    const showDone = opts.showDone !== false;
    let items = cache.filter(a => showDone || a.status !== 'Done');
    if (opts.filter && opts.filter !== 'all') items = items.filter(a => a.status === opts.filter);
    items.sort((a, b) => (a.status === 'Done') - (b.status === 'Done') || (b.overdue - a.overdue) || String(a.due_date || '9999').localeCompare(String(b.due_date || '9999')));
    if (!items.length) { container.innerHTML = GCM.ui.empty('No action items yet. Create one from any alert, document or risk.', 'check-square'); GCM.ui.icons(); return; }
    container.innerHTML = items.map(a => `
      <div class="flex items-start gap-3 p-3 rounded-xl border ${a.overdue ? 'border-rose-800/70 bg-rose-950/20' : 'border-slate-800 bg-slate-900/60'} ${a.status === 'Done' ? 'opacity-60' : ''}" data-id="${GCM.ui.esc(a.id)}">
        <div class="pt-0.5"><span class="badge ${PRIO[a.priority] || 'badge-neutral'}">${GCM.ui.esc(a.priority || 'Medium')}</span></div>
        <div class="flex-1 min-w-0">
          <div class="text-xs font-semibold text-white ${a.status === 'Done' ? 'line-through' : ''}">${GCM.ui.esc(a.title)}</div>
          <div class="flex flex-wrap items-center gap-2 mt-1 text-[11px] text-slate-400">
            ${a.owner ? `<span class="flex items-center gap-1"><i data-lucide="user" class="w-3 h-3"></i>${GCM.ui.esc(a.owner)}</span>` : '<span class="text-slate-500">unassigned</span>'}
            ${a.due_date ? `<span class="flex items-center gap-1 ${a.overdue ? 'text-rose-300 font-semibold' : ''}"><i data-lucide="calendar" class="w-3 h-3"></i>${GCM.ui.fmtDate(a.due_date)} · ${GCM.ui.relDays(a.due_date)}</span>` : ''}
            ${linkedLabel(a)}
          </div>
          ${a.notes ? `<div class="text-[11px] text-slate-500 mt-1 line-clamp-2">${GCM.ui.esc(a.notes)}</div>` : ''}
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <select class="select !w-auto !py-1 !text-[11px]" data-role="status">${STATUSES.map(s => `<option ${s === a.status ? 'selected' : ''}>${s}</option>`).join('')}</select>
          <button class="btn btn-ghost btn-sm" data-role="delete" title="Delete"><i data-lucide="trash-2" class="w-3.5 h-3.5"></i></button>
        </div>
      </div>`).join('');
    container.querySelectorAll('[data-role=status]').forEach(sel => sel.onchange = async () => {
      const id = sel.closest('[data-id]').dataset.id;
      try { await GCM.api.patch(`/api/actions/${id}`, { status: sel.value }); GCM.ui.toast('Action updated', sel.value); await load(); GCM.bus.emit('actions:changed'); }
      catch (e) { GCM.ui.toast('Update failed', e.message, 'error'); }
    });
    container.querySelectorAll('[data-role=delete]').forEach(btn => btn.onclick = async () => {
      const id = btn.closest('[data-id]').dataset.id;
      if (!(await GCM.ui.confirm('Delete this action item? This cannot be undone.', { title: 'Delete action', okLabel: 'Delete', danger: true }))) return;
      try { await GCM.api.del(`/api/actions/${id}`); await load(); GCM.bus.emit('actions:changed'); } catch (e) { GCM.ui.toast('Delete failed', e.message, 'error'); }
    });
    GCM.ui.icons();
  }

  GCM.actionsPanel = { load, render, get items() { return cache; } };
  GCM.modules.actions = { init() { load(); } };
})();
