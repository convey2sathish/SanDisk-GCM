/* matrix.js - product-based testing vs document matrix + country fact sheet */
(function () {
  'use strict';
  const GCM = window.GCM;
  const $ = (id) => document.getElementById(id);
  let data = null; let debounce = null;

  function params(exportAll) {
    const p = new URLSearchParams({
      category: $('matrix-product-selector')?.value || 'external_ssd_powered',
      type: exportAll ? 'all' : ($('matrix-type-filter')?.value || 'all'),
      region: exportAll ? 'all' : ($('matrix-region-filter')?.value || 'all'),
      search: exportAll ? '' : ($('matrix-search-input')?.value || ''),
    });
    if (exportAll) p.set('export_all', 'true');
    return p;
  }

  function reqBadge(req) {
    if (req.includes('Testing Required')) return 'badge badge-critical';
    if (req.includes('Document Required')) return 'badge badge-warning';
    if (req.includes('Supplier Declaration')) return 'badge badge-success';
    return 'badge badge-neutral';
  }

  function transitionHtml(c) {
    const tr = (c.transitions || []).filter(t => t.to);
    if (!tr.length) return '';
    return tr.slice(-3).map(t => `<div class="mt-1.5 flex items-start gap-1.5 text-[10px] bg-indigo-950/50 border border-indigo-800/60 rounded-lg px-2 py-1"><i data-lucide="git-branch" class="w-3 h-3 text-indigo-300 shrink-0 mt-0.5"></i><span class="text-indigo-200"><strong>${GCM.ui.esc(t.pillar)} transition:</strong> ${GCM.ui.esc(t.from || 'current')} → <strong>${GCM.ui.esc(t.to)}</strong>${t.deadline ? ` by <span class="mono">${GCM.ui.esc(t.deadline)}</span> (${GCM.ui.relDays(t.deadline)})` : ''}</span></div>`).join('');
  }

  const PILLAR_PILL = {
    Safety: 'text-rose-300 border-rose-800', EMC: 'text-sky-300 border-sky-800', Environmental: 'text-emerald-300 border-emerald-800',
    Energy: 'text-amber-300 border-amber-800', Cyber: 'text-violet-300 border-violet-800', Labelling: 'text-indigo-300 border-indigo-800',
  };

  function requirementsHtml(c) {
    const reqs = (c.applicable_requirements || []).filter(r => r.status !== 'Not applicable');
    if (!reqs.length) {
      return `<div class="flex items-center gap-1.5"><span class="pill ${PILLAR_PILL.Safety}">Safety</span><span class="text-white text-[11px]">${GCM.ui.esc(c.safety_std || '')}</span></div>
        <div class="flex items-center gap-1.5"><span class="pill ${PILLAR_PILL.EMC}">EMC</span><span class="text-slate-200 text-[11px]">${GCM.ui.esc(c.emc_std || '')}</span></div>`;
    }
    return reqs.map(r => {
      if (r.status === 'Exempt') {
        return `<div class="flex items-start gap-1.5"><span class="pill text-slate-400 border-slate-700 shrink-0">${GCM.ui.esc(r.pillar)}</span><span class="pill text-emerald-400 border-emerald-900 bg-emerald-950/40 shrink-0">Exempt</span><span class="text-slate-400 text-[10px] italic leading-tight">${GCM.ui.esc(r.note || '')}</span></div>`;
      }
      const std = r.standard ? `<span class="text-white text-[11px]">${GCM.ui.esc(r.standard)}</span>` : '';
      const route = r.route ? `<span class="mono text-[9px] text-slate-400 border border-slate-700 rounded px-1 py-px shrink-0">${GCM.ui.esc(r.route)}</span>` : '';
      const note = r.pillar === 'Environmental' || !r.note ? '' : `<div class="text-[10px] text-slate-500 leading-tight">${GCM.ui.esc(r.note)}</div>`;
      return `<div class="flex items-start gap-1.5"><span class="pill ${PILLAR_PILL[r.pillar] || ''} shrink-0">${GCM.ui.esc(r.pillar)}</span><div class="min-w-0"><div class="flex items-center gap-1.5 flex-wrap">${std}${route}</div>${note}</div></div>`;
    }).join('');
  }

  function rowHtml(c) {
    const docs = (c.required_documents || []).map(d => `<span class="inline-block px-2 py-0.5 m-0.5 rounded bg-slate-800/90 border border-slate-700 text-slate-200 text-[10px] leading-tight">${GCM.ui.esc(d)}</span>`).join('');
    return `<tr>
      <td class="whitespace-nowrap"><div class="flex items-center gap-2"><span class="text-lg">${GCM.ui.flag(c.country_code)}</span><div><div class="font-semibold text-white">${GCM.ui.esc(c.country_name)} <span class="mono text-slate-500 text-[10px]">${GCM.ui.esc(c.country_code)}</span></div><div class="text-[10px] text-slate-500">${GCM.ui.esc(c.region)}${c.bloc && c.bloc !== 'None' ? ` · ${GCM.ui.esc(c.bloc)}` : ''}</div></div></div></td>
      <td class="text-slate-300 max-w-[180px]">${GCM.ui.esc(c.authority)}</td>
      <td class="whitespace-nowrap"><span class="${reqBadge(c.requirement_type)}">${GCM.ui.esc(c.requirement_type)}</span><div class="text-[10px] text-slate-500 mt-1 max-w-[200px] whitespace-normal">${GCM.ui.esc(c.testing_location || '')}</div></td>
      <td class="min-w-[260px]"><div class="space-y-1">
        ${c.last_surveilled_date ? `<div class="inline-flex items-center gap-1.5 text-[9px] text-emerald-300 mono bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>Surveilled ${GCM.ui.esc(c.last_surveilled_date)} [${GCM.ui.esc(c.last_surveilled_pillar || 'All')}]</div>` : ''}
        ${requirementsHtml(c)}
        ${c.applicable_summary ? `<div class="text-[10px] text-slate-400 leading-tight pt-1 border-t border-slate-800/80">${GCM.ui.esc(c.applicable_summary)}</div>` : ''}
        <div class="pt-1.5 mt-1 border-t border-slate-800/80 space-y-1">
          <div class="flex items-start gap-1.5"><span class="pill text-emerald-300 border-emerald-800 shrink-0">RoHS</span><span class="text-slate-300 text-[10px] leading-tight">${GCM.ui.esc(c.rohs_std || c.env_std)}</span></div>
          ${c.pfas_std ? `<div class="flex items-start gap-1.5"><span class="pill text-teal-300 border-teal-800 shrink-0">PFAS / Chem</span><span class="text-teal-200/90 text-[10px] leading-tight">${GCM.ui.esc(c.pfas_std)}</span></div>` : ''}
          ${c.packaging_std ? `<div class="flex items-start gap-1.5"><span class="pill text-amber-300 border-amber-800 shrink-0">Packaging</span><span class="text-amber-200/90 text-[10px] leading-tight">${GCM.ui.esc(c.packaging_std)}</span></div>` : ''}
          ${c.epr_std ? `<div class="flex items-start gap-1.5"><span class="pill text-indigo-300 border-indigo-800 shrink-0">EPR / WEEE</span><span class="text-indigo-200/90 text-[10px] leading-tight">${GCM.ui.esc(c.epr_std)}</span></div>` : ''}
        </div>
        ${transitionHtml(c)}
      </div></td>
      <td><div class="max-w-md">${docs}</div></td>
      <td class="text-center whitespace-nowrap">${c.local_rep_required ? '<span class="badge badge-critical">Mandatory</span>' : '<span class="text-slate-500 text-[10px]">No</span>'}</td>
      <td class="text-center whitespace-nowrap mono text-slate-300">${GCM.ui.esc(c.lead_time)} wk</td>
      <td class="text-right whitespace-nowrap"><div class="flex flex-col gap-1 items-end"><button class="btn btn-secondary btn-sm" data-action="country-factsheet" data-arg="${GCM.ui.esc(c.country_code)}">Fact sheet</button><button class="btn btn-ghost btn-sm" data-action="deeplink-country" data-arg="${GCM.ui.esc(c.country_code)}"><i data-lucide="globe-2" class="w-3.5 h-3.5"></i>Map</button></div></td>
    </tr>`;
  }

  async function load() {
    const tbody = $('matrix-table-body'); if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="8">${GCM.ui.skeleton(4)}</td></tr>`;
    try {
      data = await GCM.api.get(`/api/gma/by-product?${params(false)}`);
      const s = data.summary || {};
      $('kpi-total').textContent = s.total ?? '—'; $('kpi-testing').textContent = s.testing_required ?? 0; $('kpi-document').textContent = s.document_required ?? 0;
      $('kpi-sdoc').textContent = (s.sdoc_required || 0) + (s.exempt || 0);
      $('kpi-transition').textContent = (data.countries || []).filter(c => (c.transitions || []).length).length + (($('matrix-type-filter').value !== 'all' || $('matrix-search-input').value || $('matrix-region-filter').value !== 'all') ? '*' : '');
      $('matrix-display-count').textContent = data.countries.length; $('matrix-cat-name').textContent = data.category_name;
      tbody.innerHTML = data.countries.length ? data.countries.map(rowHtml).join('') : `<tr><td colspan="8">${GCM.ui.empty('No jurisdictions match the current filters.', 'filter-x')}</td></tr>`;
      GCM.ui.icons();
    } catch (e) { tbody.innerHTML = `<tr><td colspan="8" class="text-center text-rose-400 py-6">${GCM.ui.esc(e.message)}</td></tr>`; }
  }

  function exportExcel(all) { GCM.api.download(`/api/gma/export-excel?${params(!!all)}`, all ? 'Exporting all 205 jurisdictions…' : 'Exporting current view…'); }

  /* ------------------------------------------------------------- country fact sheet */
  async function openFactSheet(code) {
    const cat = $('matrix-product-selector')?.value || 'external_ssd_powered';
    GCM.ui.openModal('modal-country-factsheet');
    const body = $('factsheet-body'); body.innerHTML = GCM.ui.skeleton(4);
    try {
      const d = await GCM.api.get(`/api/countries/${code}`);
      const c = d.country; const rules = d.category_rules || {};
      $('factsheet-flag').textContent = GCM.ui.flag(c.code); $('factsheet-country-name').textContent = `${c.name} (${c.code})`;
      $('factsheet-country-region').textContent = `${c.region} · ${c.authority} · Bloc: ${c.bloc || 'None'}`;
      $('factsheet-open-map').onclick = () => { GCM.ui.closeModal('modal-country-factsheet'); GCM.deeplink.country(c.code); };
      const kv = (k, v, cls = '') => `<div class="bg-slate-800/70 border border-slate-700 p-3 rounded-lg"><div class="text-[10px] uppercase font-semibold text-slate-400">${k}</div><div class="text-xs font-bold mt-1 ${cls}">${v}</div></div>`;
      const transitions = (c.transitions || []).slice(-6).reverse();
      body.innerHTML = `
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          ${kv('CB Scheme', c.cb_scheme_accepted ? 'Accepted (national deviations)' : 'Not recognised', c.cb_scheme_accepted ? 'text-emerald-300' : 'text-rose-300')}
          ${kv('In-country testing', c.in_country_testing ? 'Mandatory local lab' : 'Not required (CB / DoC)', c.in_country_testing ? 'text-rose-300' : 'text-emerald-300')}
          ${kv('Local representative', c.local_rep_required ? 'Local legal entity mandatory' : 'Foreign applicant accepted', c.local_rep_required ? 'text-amber-300' : 'text-slate-200')}
          ${kv('Certificate validity', GCM.ui.esc(c.cert_validity || '—'), 'text-slate-200')}
        </div>
        <div class="card !p-4 space-y-2">
          <div class="section-title text-sky-400">Mandatory technical standards</div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div><div class="text-[11px] text-slate-400">Safety</div><div class="text-slate-100 font-semibold">${GCM.ui.esc(c.safety_std)}</div>${c.safety_std_next ? `<div class="text-[10px] text-indigo-300 mt-0.5">→ ${GCM.ui.esc(c.safety_std_next)} by ${GCM.ui.esc(c.safety_std_transition_deadline || '')}</div>` : ''}</div>
            <div><div class="text-[11px] text-slate-400">EMC / Radio</div><div class="text-slate-100 font-semibold">${GCM.ui.esc(c.emc_std)}</div>${c.emc_std_next ? `<div class="text-[10px] text-indigo-300 mt-0.5">→ ${GCM.ui.esc(c.emc_std_next)} by ${GCM.ui.esc(c.emc_std_transition_deadline || '')}</div>` : ''}</div>
            <div><div class="text-[11px] text-slate-400">Environmental</div><div class="text-slate-100 font-semibold">${GCM.ui.esc(c.env_std)}</div>${c.env_std_next ? `<div class="text-[10px] text-indigo-300 mt-0.5">→ ${GCM.ui.esc(c.env_std_next)} by ${GCM.ui.esc(c.env_std_transition_deadline || '')}</div>` : ''}</div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 text-[11px] text-slate-300">
            <div><span class="text-slate-500">RoHS:</span> ${GCM.ui.esc(c.rohs_std || '—')}</div><div><span class="text-slate-500">PFAS / chemicals:</span> ${GCM.ui.esc(c.pfas_std || '—')}</div>
            <div><span class="text-slate-500">Packaging:</span> ${GCM.ui.esc(c.packaging_std || '—')}</div><div><span class="text-slate-500">EPR / WEEE:</span> ${GCM.ui.esc(c.epr_std || '—')}</div>
          </div>
        </div>
        <div><div class="section-title mb-2">Mandatory marks</div><div class="flex flex-wrap gap-2">${(c.marks || []).map(m => `<span class="px-3 py-1 rounded-lg bg-sky-950 border border-sky-800 text-sky-300 mono font-bold text-xs">${GCM.ui.esc(m)}</span>`).join('') || '<span class="text-slate-500 text-xs">None</span>'}</div></div>
        <div><div class="section-title mb-2">Requirement by product category</div><div class="table-wrap"><table class="table"><thead><tr><th>Category</th><th>Route</th><th>Applicable requirements &amp; exemptions</th><th>Lead time</th><th>Key documents</th></tr></thead><tbody>
          ${Object.entries(rules).map(([id, r]) => `<tr class="${id === cat ? 'bg-amber-950/30' : ''}"><td class="font-medium text-white">${GCM.ui.esc(r.category_name)}${id === cat ? ' <span class="pill text-amber-300 border-amber-700">active in matrix</span>' : ''}</td><td><span class="${reqBadge(r.requirement_type || '')}">${GCM.ui.esc(r.requirement_type)}</span></td><td class="text-[11px] text-slate-300 max-w-[260px] whitespace-normal">${GCM.ui.esc(r.applicable_summary || '—')}</td><td class="mono text-slate-400">${GCM.ui.esc(r.lead_time)}</td><td class="text-[11px] text-slate-300">${(r.required_documents || []).slice(0, 3).map(GCM.ui.esc).join(' · ')}${(r.required_documents || []).length > 3 ? ` · +${r.required_documents.length - 3} more` : ''}</td></tr>`).join('')}
        </tbody></table></div></div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="card !p-4"><div class="section-title text-rose-400 mb-2">Active alerts for this market (${(d.alerts || []).length})</div>${(d.alerts || []).length ? d.alerts.slice(0, 8).map(a => `<button class="w-full text-left flex items-center justify-between gap-2 py-1.5 border-b border-slate-800 last:border-0 hover:text-sky-300" data-action="deeplink-alert" data-arg="${GCM.ui.esc(a.id)}"><span class="text-[11px] text-slate-200 truncate">${GCM.ui.esc(a.title)}</span>${GCM.ui.badge(a.severity, a.severity)}</button>`).join('') : '<div class="text-[11px] text-slate-500">No active alerts target this market.</div>'}</div>
          <div class="card !p-4"><div class="section-title text-emerald-400 mb-2">Portfolio products sold here (${(d.products || []).length})</div>${(d.products || []).length ? d.products.map(p => `<button class="w-full text-left flex items-center justify-between gap-2 py-1.5 border-b border-slate-800 last:border-0 hover:text-sky-300" data-action="deeplink-product" data-arg="${GCM.ui.esc(p.id)}"><span class="text-[11px] text-slate-200 truncate">${GCM.ui.esc(p.name)}</span><span class="mono text-[10px] text-slate-500">${GCM.ui.esc(p.sku)}</span></button>`).join('') : '<div class="text-[11px] text-slate-500">No portfolio product targets this market.</div>'}</div>
        </div>
        ${transitions.length ? `<div class="card !p-4"><div class="section-title text-indigo-300 mb-2">Regulatory transitions recorded by surveillance</div><div class="timeline">${transitions.map(t => `<div class="timeline-item" style="--dot:#818cf8"><div class="text-xs text-white font-semibold">${GCM.ui.esc(t.pillar)}: ${GCM.ui.esc(t.from || 'current')} → ${GCM.ui.esc(t.to)}</div><div class="text-[11px] text-slate-400">Deadline ${GCM.ui.esc(t.deadline || '—')} · ${GCM.ui.esc(t.source || '')} · recorded ${GCM.ui.esc(t.applied_at || '')}</div></div>`).join('')}</div></div>` : ''}
        <div class="bg-slate-800/40 border border-slate-700/60 rounded-lg p-3 text-xs text-slate-300"><div class="font-bold text-slate-200 flex items-center gap-1.5 mb-1"><i data-lucide="alert-circle" class="w-3.5 h-3.5 text-amber-400"></i>Regulatory guidance &amp; customs advisory</div><p class="text-slate-400">${GCM.ui.esc(c.notes || '')}</p></div>
        <div class="flex justify-end gap-2 no-print"><button class="btn btn-secondary btn-sm" data-action="action-for-country" data-arg="${GCM.ui.esc(c.code)}"><i data-lucide="plus-square" class="w-3.5 h-3.5 text-emerald-300"></i>Create action</button></div>`;
      GCM.ui.icons();
    } catch (e) { body.innerHTML = `<div class="text-rose-400 text-xs">${GCM.ui.esc(e.message)}</div>`; }
  }

  GCM.modules.matrix = {
    init() {
      const sel = $('matrix-product-selector');
      sel.innerHTML = GCM.state.categories.map(c => `<option value="${GCM.ui.esc(c.id)}" ${c.id === (GCM.state.settings.default_category || 'external_ssd_powered') ? 'selected' : ''}>${GCM.ui.esc(c.name)}</option>`).join('');
      sel.addEventListener('change', load);
      $('matrix-type-filter').addEventListener('change', load); $('matrix-region-filter').addEventListener('change', load);
      $('matrix-search-input').addEventListener('input', () => { clearTimeout(debounce); debounce = setTimeout(load, 250); });
      $('matrix-kpi-banner').addEventListener('click', (e) => { const b = e.target.closest('[data-mfilter]'); if (b) { $('matrix-type-filter').value = b.dataset.mfilter; load(); } });
      GCM.bus.on('action:matrix-export-view', () => exportExcel(false)); GCM.bus.on('action:matrix-export-all', () => exportExcel(true)); GCM.bus.on('matrix:export', (all) => exportExcel(!!all));
      GCM.bus.on('action:country-factsheet', ({ arg }) => openFactSheet(arg)); GCM.bus.on('country:factsheet', (code) => openFactSheet(code));
      GCM.bus.on('action:action-for-country', ({ arg }) => GCM.actions.createFor('country', arg, { title: `Review market access requirements for ${GCM.state.countries[arg]?.name || arg}` }));
      GCM.bus.on('matrix:search', (q) => { $('matrix-search-input').value = q || ''; $('matrix-type-filter').value = 'all'; load(); });
      GCM.bus.on('matrix:category', (id) => { if ([...sel.options].some(o => o.value === id)) { sel.value = id; load(); } });
      GCM.bus.on('countries:changed', () => { if (data) load(); });
      GCM.palette.register({ label: 'Export all 205 markets for current product (.xlsx)', icon: 'download', keywords: ['excel', 'export', '205'], run: () => exportExcel(true) });
    },
    onFirstShow() { load(); },
    reload: load, openFactSheet,
  };
})();
