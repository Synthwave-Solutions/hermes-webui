/* Studio "Roadmap" (22 Nov 2026): the quickscan roadmap, with proof that it runs.

   The roadmap that belongs to a quickscan (months and weeks, a start group
   and one group per block, steering sessions, a card per block, systems and
   process diagrams) is kept by the server (/api/studio/roadmap). Each row
   and each block can be linked to what exists in this environment: scheduled
   tasks, bots, skills, use cases and playbooks. The server works out the
   evidence and the status of every row on each read; nothing here decides
   a status or access.

   The Gantt reuses the chart of the backlog roadmap (static/studio_roadmap.js,
   the .rm classes). Process diagrams go through the app's own Mermaid
   renderer, the link fields through the shared picker. The opportunity tree
   and the impact and effort matrix are not repeated here: they live in each
   use case, one click away. */
(function(){
  'use strict';
  const NL = {
    tab_plan: 'Roadmap', tab_systems: 'Systemen', tab_diagrams: 'Procesdiagrammen',
    intro: 'De roadmap uit de quickscan, met per onderdeel wat er in deze omgeving echt draait.',
    empty_h: 'Nog geen roadmap', empty: 'Zodra de roadmap uit de quickscan is geladen, zie je hier de planning en wat er al draait.',
    empty_edit: 'Laad de roadmap uit de quickscan als JSON. Daarna koppel je per onderdeel de taken, bots en skills die het uitvoeren.',
    import: 'Roadmap laden', import_h: 'Roadmap laden uit JSON', import_p: 'Plak het JSON-document van de roadmap of kies een bestand. Een bestaande roadmap wordt vervangen.',
    import_go: 'Laden', import_file: 'Kies bestand', import_bad: 'Dit is geen geldig JSON-document.', imported: 'Roadmap geladen', export: 'Download JSON', cancel: 'Annuleren',
    running: '{a} van {b} onderdelen draaien', built_n: '{n} gebouwd, nog niet gedraaid', planned_n: '{n} gepland',
    measured: 'Gemeten besparing per week', baseline: 'Volgens het ontwerp', hours: 'uur', version: 'Rapportversie', updated: 'bijgewerkt',
    wk: 'Week', today: 'Vandaag', steering: 'Stuurgroep', legend: 'Legenda', plan_of: 'Planning in {n} weken',
    k_fundament: 'Fundament', k_agent: 'Agent', k_werksessie: 'Werksessie', k_borging: 'Borging',
    s_planned: 'Gepland', s_in_progress: 'In uitvoering', s_built: 'Gebouwd', s_live: 'Draait', s_parked: 'Geparkeerd',
    derived: 'Afgeleid uit wat er draait', manual: 'Handmatig gezet', differs: 'Handmatig stond dit op {s}',
    weeks: 'week {a} tot en met {b}', week_one: 'week {a}', delivered: 'Opgeleverd op', note: 'Notitie', status: 'Status', save: 'Opslaan', close: 'Sluiten', saved: 'Opgeslagen',
    card: 'Blok', prerequisites: 'Randvoorwaarden', human_role: 'Rol van de mens', steps: 'Werkwijze', pilot: 'Pilotcriteria', ready_when: 'Klaar als',
    evidence: 'Bewijs', no_links: 'Nog niets gekoppeld. Koppel een taak, bot, skill of use case om te laten zien dat dit onderdeel draait.',
    links: 'Koppelingen', l_job: 'Geplande taken', l_bot: 'Bots', l_skill: 'Skills', l_use_case: 'Use cases', l_playbook: 'Playbooks', pick: 'Kies uit de lijst',
    t_job: 'Taak', t_bot: 'Bot', t_skill: 'Skill', t_use_case: 'Use case', t_playbook: 'Playbook',
    missing: 'Bestaat niet meer', hidden: 'Niet zichtbaar voor jou', on: 'Staat aan', off: 'Staat uit', never: 'Nog niet gedraaid', last_run: 'Laatste run',
    ok: 'gelukt', failed: 'mislukt', runs_30: '{n} runs in 30 dagen', saved_30: '{h} uur bespaard in 30 dagen', active: 'Actief', inactive: 'Niet actief in 30 dagen',
    tasks_n: 'taken: {n}', installed: 'Geïnstalleerd', disabled: 'Uitgezet', saves_week: 'bespaart {h} uur per week volgens het ontwerp',
    published: 'Gepubliceerd', draft: 'Concept', followed: '{n} keer gevolgd', open: 'Open',
    p_discover: 'Ontdekken', p_design: 'Inrichten', p_playbook: 'Bouwplan', p_build: 'Bouwen', p_measure: 'Meten',
    sys_name: 'Systeem', sys_status: 'Status', sys_note: 'Toelichting', sys_empty: 'Geen systemen in deze roadmap.',
    y_te_valideren: 'Te valideren', y_te_bevestigen: 'Te bevestigen', y_voorgesteld: 'Voorgesteld', y_onbekend: 'Onbekend', y_alleen_genoemd: 'Alleen genoemd', y_bevestigd: 'Bevestigd',
    dia_empty: 'Geen procesdiagrammen in deze roadmap.', notes: 'Bij deze planning', open_points: 'Governance, privacy en adoptie', pilot_all: 'Pilotcriteria',
    tree_hint: 'De kansenboom en de matrix van impact en moeite staan per use case in Studio.', tree_open: 'Naar de use cases',
    block_status: 'Blok', loading: 'Laden…', failed_load: 'De roadmap kon niet geladen worden.'
  };
  const EN = {
    tab_plan: 'Roadmap', tab_systems: 'Systems', tab_diagrams: 'Process diagrams',
    intro: 'The roadmap from the quickscan, with what really runs in this environment per part.',
    empty_h: 'No roadmap yet', empty: 'Once the roadmap from the quickscan is loaded, the planning and what already runs show here.',
    empty_edit: 'Load the roadmap from the quickscan as JSON. Then link the tasks, bots and skills that carry out each part.',
    import: 'Load roadmap', import_h: 'Load roadmap from JSON', import_p: 'Paste the JSON document of the roadmap or choose a file. An existing roadmap is replaced.',
    import_go: 'Load', import_file: 'Choose file', import_bad: 'This is not a valid JSON document.', imported: 'Roadmap loaded', export: 'Download JSON', cancel: 'Cancel',
    running: '{a} of {b} parts are running', built_n: '{n} built, not run yet', planned_n: '{n} planned',
    measured: 'Measured saving per week', baseline: 'By design', hours: 'hours', version: 'Report version', updated: 'updated',
    wk: 'Week', today: 'Today', steering: 'Steering session', legend: 'Legend', plan_of: 'Planning in {n} weeks',
    k_fundament: 'Foundation', k_agent: 'Agent', k_werksessie: 'Team session', k_borging: 'Safeguarding',
    s_planned: 'Planned', s_in_progress: 'In progress', s_built: 'Built', s_live: 'Running', s_parked: 'Parked',
    derived: 'Derived from what runs', manual: 'Set by hand', differs: 'By hand this was {s}',
    weeks: 'week {a} to {b}', week_one: 'week {a}', delivered: 'Delivered on', note: 'Note', status: 'Status', save: 'Save', close: 'Close', saved: 'Saved',
    card: 'Block', prerequisites: 'Prerequisites', human_role: 'Role of the human', steps: 'Way of working', pilot: 'Pilot criteria', ready_when: 'Ready when',
    evidence: 'Evidence', no_links: 'Nothing linked yet. Link a task, bot, skill or use case to show that this part runs.',
    links: 'Links', l_job: 'Scheduled tasks', l_bot: 'Bots', l_skill: 'Skills', l_use_case: 'Use cases', l_playbook: 'Playbooks', pick: 'Pick from the list',
    t_job: 'Task', t_bot: 'Bot', t_skill: 'Skill', t_use_case: 'Use case', t_playbook: 'Playbook',
    missing: 'No longer exists', hidden: 'Not visible to you', on: 'Switched on', off: 'Switched off', never: 'Not run yet', last_run: 'Last run',
    ok: 'completed', failed: 'failed', runs_30: '{n} runs in 30 days', saved_30: '{h} hours saved in 30 days', active: 'Active', inactive: 'Not active in 30 days',
    tasks_n: 'tasks: {n}', installed: 'Installed', disabled: 'Switched off', saves_week: 'saves {h} hours per week by design',
    published: 'Published', draft: 'Draft', followed: 'followed {n} times', open: 'Open',
    p_discover: 'Discover', p_design: 'Design', p_playbook: 'Build plan', p_build: 'Build', p_measure: 'Measure',
    sys_name: 'System', sys_status: 'Status', sys_note: 'Explanation', sys_empty: 'No systems in this roadmap.',
    y_te_valideren: 'To validate', y_te_bevestigen: 'To confirm', y_voorgesteld: 'Proposed', y_onbekend: 'Unknown', y_alleen_genoemd: 'Only mentioned', y_bevestigd: 'Confirmed',
    dia_empty: 'No process diagrams in this roadmap.', notes: 'About this planning', open_points: 'Governance, privacy and adoption', pilot_all: 'Pilot criteria',
    tree_hint: 'The opportunity tree and the impact and effort matrix live in each use case in Studio.', tree_open: 'To the use cases',
    block_status: 'Block', loading: 'Loading…', failed_load: 'The roadmap could not be loaded.'
  };
  const lang = () => ((document.documentElement.lang || 'nl').toLowerCase().startsWith('en') ? 'en' : 'nl');
  const w = (k, v) => { let s = (lang() === 'en' ? EN : NL)[k] || NL[k] || k; if (v) for (const [a, b] of Object.entries(v)) s = s.replace('{' + a + '}', b); return s; };
  const H = v => (typeof esc === 'function' ? esc(String(v ?? '')) : String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])));
  const call = (p, o) => api(p, Object.assign({ timeoutToast: false }, o || {}));
  const post = (p, b) => call(p, { method: 'POST', body: JSON.stringify(b) });
  const toast = m => { if (typeof showToast === 'function') showToast(m); };
  const errMsg = e => (e && e.message) || String(e);
  const DAY = 86400000;
  const LINK_TYPES = ['job', 'bot', 'skill', 'use_case', 'playbook'];
  const loc = () => (lang() === 'en' ? 'en-GB' : 'nl-NL');
  const num = v => Number(v || 0).toLocaleString(loc(), { maximumFractionDigits: 1 });
  const day = s => new Date(String(s).slice(0, 10) + 'T00:00:00Z');
  const fmt = (d, o) => new Intl.DateTimeFormat(loc(), Object.assign({ timeZone: 'UTC' }, o)).format(d);
  const when = ts => (ts ? fmt(new Date(ts * 1000), { day: 'numeric', month: 'short', year: 'numeric' }) : '');

  const P = { host: null, data: null, tab: 'plan', open: '', error: '', importing: false, importError: '', options: null, token: 0 };

  // ── Reading ────────────────────────────────────────────────────────────────
  async function load(){
    const token = ++P.token;
    try { const d = await call('/api/studio/roadmap'); if (token !== P.token) return; P.data = d; P.error = ''; }
    catch (e) { if (token !== P.token) return; P.data = null; P.error = errMsg(e) || w('failed_load'); }
    paint();
  }
  function roadmap(){ return P.data && P.data.roadmap; }
  function rowState(id){ return ((P.data && P.data.rows) || {})[id] || { status: 'planned', manual: 'planned', derived: false, differs: false, evidence: [] }; }
  function phaseOf(group){ const r = roadmap(); return group && group.phase ? (r.phases || []).find(p => p.id === group.phase) || null : null; }
  function findRow(id){
    for (const g of roadmap().groups || []) for (const row of g.rows || []) if (row.id === id) return { row, group: g };
    return null;
  }

  // ── Top strip ──────────────────────────────────────────────────────────────
  function stripHtml(){
    const u = P.data.rollup, r = roadmap();
    const tile = (label, value, unit, sub) => `<div class="rm-tile"><span class="rm-tile-label">${H(label)}</span><span class="rm-tile-value">${H(value)}${unit ? `<small>${H(unit)}</small>` : ''}</span>${sub ? `<span class="pl-tile-sub">${H(sub)}</span>` : ''}</div>`;
    return `<div class="rm-tiles pl-strip" data-tour="studio-plan-strip">
      ${tile(w('running', { a: String(u.rows_live), b: String(u.rows_total) }), String(u.rows_live), '/ ' + u.rows_total, w('built_n', { n: String(u.rows_built) }) + ' · ' + w('planned_n', { n: String(u.rows_planned) }))}
      ${tile(w('measured'), num(u.measured_hours_week_saved), w('hours'), u.baseline_hours_week_saved ? w('baseline') + ': ' + num(u.baseline_hours_week_saved) + ' ' + w('hours') : '')}
      ${tile(w('version'), r.report_version, '', r.updated_at ? w('updated') + ' ' + when(r.updated_at) : '')}</div>`;
  }

  // ── Gantt ──────────────────────────────────────────────────────────────────
  function headHtml(r, weeks, nowIndex){
    const months = [];
    for (const d of weeks) {
      const key = d.getUTCFullYear() + '-' + d.getUTCMonth(), last = months[months.length - 1];
      if (last && last.key === key) last.span++; else months.push({ key, span: 1, d });
    }
    const steer = new Set(r.steering_weeks || []);
    return `<div class="rm-row rm-head" aria-hidden="true"><div class="rm-left"></div><div class="rm-track rm-months">${months.map((m, i) =>
        `<span style="grid-column:span ${m.span}">${m.span > 1 ? H(fmt(m.d, { month: 'long' }) + (m.d.getUTCMonth() === 0 || i === 0 ? ' ' + m.d.getUTCFullYear() : '')) : ''}</span>`).join('')}</div></div>
      <div class="rm-row rm-head rm-weeks" aria-hidden="true"><div class="rm-left">${H(w('wk'))}</div><div class="rm-track">${weeks.map((d, i) =>
        `<span class="${i === nowIndex ? 'now' : ''}" title="${H(fmt(d, { day: 'numeric', month: 'short' }))}">${i + 1}</span>`).join('')}</div></div>
      <div class="rm-row rm-head pl-steering"><div class="rm-left">${H(w('steering'))}</div><div class="rm-track">${weeks.map((_d, i) =>
        steer.has(i + 1) ? `<span class="pl-star" style="grid-column:${i + 1}" title="${H(w('steering'))}, ${H(w('week_one', { a: String(i + 1) }).toLowerCase())}" role="img" aria-label="${H(w('steering'))}, ${H(w('week_one', { a: String(i + 1) }).toLowerCase())}">★</span>` : '').join('')}</div></div>`;
  }
  function span(row){ return row.weeks > 1 ? w('weeks', { a: String(row.start_week), b: String(row.start_week + row.weeks - 1) }) : w('week_one', { a: String(row.start_week) }); }
  function rowHtml(row, group, todayPct){
    const st = rowState(row.id), open = P.open === row.id;
    const label = `${row.name}: ${w('k_' + row.kind)}, ${w('s_' + st.status)}, ${span(row)}`;
    return `<div class="rm-row rm-item${open ? ' open' : ''}" data-pl-row="${H(row.id)}"><div class="rm-left">
        <button type="button" class="rm-title" data-pl-open="${H(row.id)}" aria-expanded="${open}">${H(row.name)}</button>
        <span class="rm-sub"><span>${H(w('k_' + row.kind))}</span>${(row.links || []).length ? `<span class="om-chip pl-linked">${(row.links || []).length} ${H(w('links').toLowerCase())}</span>` : ''}${st.differs ? `<span class="om-badge warn pl-differs" title="${H(w('differs', { s: w('s_' + st.manual).toLowerCase() }))}">!</span>` : ''}</span></div>
      <div class="rm-track" style="--rm-today:${todayPct}">
        <button type="button" class="rm-bar pl-bar s-${H(st.status)} k-${H(row.kind)}" style="grid-column:${row.start_week} / span ${row.weeks}" data-pl-open="${H(row.id)}" aria-expanded="${open}" aria-label="${H(label)}" title="${H(label)}"><span>${row.weeks >= 3 ? H(w('s_' + st.status)) : ''}</span></button>
      </div></div>${open ? panelHtml(row, group) : ''}`;
  }
  function ganttHtml(){
    const r = roadmap(), first = day(r.start_date);
    const weeks = Array.from({ length: r.weeks }, (_x, i) => new Date(first.getTime() + i * 7 * DAY));
    const today = day(P.data.today || new Date().toISOString());
    const pos = (today - first) / DAY / (r.weeks * 7);
    const todayPct = pos >= 0 && pos <= 1 ? (pos * 100).toFixed(3) + '%' : '-10%';
    const nowIndex = pos >= 0 && pos < 1 ? Math.floor(pos * r.weeks) : -1;
    const blocks = Object.fromEntries((P.data.rollup.blocks || []).map(b => [b.id, b]));
    return `<div class="rm-scroll"><div class="rm-chart pl-chart" style="--rm-n:${r.weeks}" role="group" aria-label="${H(w('plan_of', { n: String(r.weeks) }))}">${headHtml(r, weeks, nowIndex)}
        ${(r.groups || []).map(g => { const b = blocks[g.id] || { rows_total: 0, rows_live: 0 }; return `<section class="rm-group"><div class="rm-row rm-group-head"><div class="rm-left"><strong>${H(g.name)}</strong></div><div class="rm-track pl-group-track"><span class="pl-group-count">${H(w('running', { a: String(b.rows_live), b: String(b.rows_total) }))}</span></div></div>
          ${(g.rows || []).map(row => rowHtml(row, g, todayPct)).join('')}</section>`; }).join('')}</div></div>
      <div class="rm-legend" aria-label="${H(w('legend'))}">${['planned', 'in_progress', 'built', 'live', 'parked'].map(s => `<span><i class="rm-bar pl-bar s-${s}"></i>${H(w('s_' + s))}</span>`).join('')}
        <span><i class="rm-bar pl-bar s-planned k-fundament"></i>${H(w('k_fundament'))}</span><span><span class="pl-star" aria-hidden="true">★</span>${H(w('steering'))}</span><span><i class="rm-now"></i>${H(w('today'))}</span></div>`;
  }

  // ── Side panel of a row ────────────────────────────────────────────────────
  function evidenceHtml(e){
    const type = `<span class="om-badge">${H(w('t_' + e.type))}</span>`;
    const head = (name, dot) => `<span class="om-dot ${dot}"></span><div class="om-row-main"><div class="om-row-title">${H(name)} ${type}</div>`;
    if (!e.found) return `<div class="om-row pl-ev">${head(e.ref, 'error')}<div class="om-row-sub">${H(w('missing'))}</div></div></div>`;
    if (!e.visible) return `<div class="om-row pl-ev">${head(w('t_' + e.type), e.live ? 'ok' : 'new')}<div class="om-row-sub">${H(w('hidden'))}</div></div></div>`;
    let sub = [], dot = 'new', go = '';
    if (e.type === 'job') {
      dot = e.live ? 'ok' : e.last_result === 'failed' ? 'error' : 'new';
      sub = [e.enabled ? w('on') : w('off'), e.schedule, e.last_run_at ? `${w('last_run')}: ${when(e.last_run_at)}${e.last_result ? ' (' + w(e.last_result === 'ok' ? 'ok' : 'failed') + ')' : ''}` : w('never'),
             w('runs_30', { n: String(e.runs_30d || 0) }), e.hours_saved_30d ? w('saved_30', { h: num(e.hours_saved_30d) }) : ''];
      go = 'tasks';
    } else if (e.type === 'bot') {
      dot = e.active ? 'ok' : 'new';
      sub = [e.active ? w('active') : w('inactive'), w('tasks_n', { n: String(e.tasks_total || 0) }), (e.tasks || []).slice(0, 3).map(t => t.name).join(', ')];
      go = 'profiles';
    } else if (e.type === 'skill') {
      dot = e.enabled ? 'ok' : 'new';
      sub = [w('installed'), e.enabled ? w('on') : w('disabled')];
      go = 'skills';
    } else if (e.type === 'use_case') {
      dot = e.phase === 'measure' || e.phase === 'build' ? 'ok' : 'new';
      sub = [w('p_' + (e.phase || 'discover')), e.hours_week_saved != null ? w('saves_week', { h: num(e.hours_week_saved) }) : ''];
    } else {
      dot = e.published ? 'ok' : 'new';
      sub = [e.published ? w('published') : w('draft'), w('followed', { n: String(e.runs || 0) })];
    }
    const action = go ? `data-pl-nav="${go}"` : `data-pl-go="${H(e.type)}" data-pl-ref="${H(e.ref)}"`;
    return `<div class="om-row pl-ev">${head(e.name || e.ref, dot)}<div class="om-row-sub">${H(sub.filter(Boolean).join(' · '))}</div></div>
      <div class="om-row-actions"><button type="button" class="sm-btn" ${action}>${H(w('open'))}</button></div></div>`;
  }
  function listHtml(title, items){
    return items && items.length ? `<div class="pl-card-part"><h5>${H(title)}</h5><ul>${items.map(i => `<li>${H(i)}</li>`).join('')}</ul></div>` : '';
  }
  function cardHtml(phase){
    if (!phase) return '';
    const ps = ((P.data.phases || {})[phase.id]) || { status: 'planned', evidence: [] };
    return `<section class="pl-card"><h4>${H(w('card'))}: ${H(phase.name)} <span class="om-badge pl-s s-${H(ps.status)}">${H(w('s_' + ps.status))}</span></h4>
      ${phase.summary ? `<p>${H(phase.summary)}</p>` : ''}
      ${listHtml(w('prerequisites'), phase.prerequisites)}
      ${phase.human_role ? `<div class="pl-card-part"><h5>${H(w('human_role'))}</h5><p>${H(phase.human_role)}</p></div>` : ''}
      ${listHtml(w('steps'), phase.steps)}${listHtml(w('pilot'), phase.pilot_criteria)}
      ${phase.ready_when ? `<div class="pl-card-part pl-ready"><h5>${H(w('ready_when'))}</h5><p>${H(phase.ready_when)}</p></div>` : ''}
      ${(ps.evidence || []).length ? `<div class="pl-card-part"><h5>${H(w('evidence'))}</h5><div class="om-list">${ps.evidence.map(evidenceHtml).join('')}</div></div>` : ''}</section>`;
  }
  function editHtml(row){
    const csv = t => (row.links || []).filter(l => l.type === t).map(l => l.ref).join(',');
    return `<form class="pl-edit" data-pl-form="${H(row.id)}">
      <div class="rm-edit-fields">
        <label>${H(w('status'))}<select name="status" class="om-select">${(P.data.statuses || []).map(s => `<option value="${H(s)}" ${row.status === s ? 'selected' : ''}>${H(w('s_' + s))}</option>`).join('')}</select></label>
        <label>${H(w('delivered'))}<input type="date" name="delivered_at" value="${H(row.delivered_at || '')}"></label>
        <label class="pl-wide">${H(w('note'))}<input type="text" name="note" maxlength="400" value="${H(row.note || '')}"></label>
      </div>
      <div class="rm-edit-fields pl-links">${LINK_TYPES.map(t => `<label>${H(w('l_' + t))}<input name="link_${t}" data-sp-picker data-sp-source="plan:${t}" data-sp-multi="1" data-sp-custom="0" placeholder="${H(w('pick'))}" value="${H(csv(t))}"></label>`).join('')}</div>
      <div class="rm-edit-actions"><button type="submit" class="sm-btn primary">${H(w('save'))}</button><button type="button" class="sm-btn" data-pl-close>${H(w('close'))}</button></div></form>`;
  }
  function panelHtml(row, group){
    const st = rowState(row.id);
    const facts = [w('k_' + row.kind), span(row), row.delivered_at ? w('delivered').toLowerCase() + ' ' + row.delivered_at : ''].filter(Boolean).join(' · ');
    return `<div class="rm-edit pl-panel" data-pl-panel role="region" aria-label="${H(row.name)}">
      <div class="pl-panel-head"><span class="om-badge pl-s s-${H(st.status)}">${H(w('s_' + st.status))}</span><span class="om-small om-muted">${H(st.derived ? w('derived') : w('manual'))}${st.differs ? ' · ' + H(w('differs', { s: w('s_' + st.manual).toLowerCase() })) : ''}</span>
        ${P.data.editable ? '' : `<button type="button" class="sm-btn pl-panel-close" data-pl-close>${H(w('close'))}</button>`}</div>
      <p class="rm-edit-facts">${H(facts)}${row.note ? ' · ' + H(row.note) : ''}</p>
      <div class="pl-panel-grid"><section><h4>${H(w('evidence'))}</h4>${st.evidence.length ? `<div class="om-list">${st.evidence.map(evidenceHtml).join('')}</div>` : `<p class="om-small om-muted">${H(w('no_links'))}</p>`}
        ${P.data.editable ? editHtml(row) : ''}</section>${cardHtml(phaseOf(group))}</div></div>`;
  }

  // ── Other tabs ─────────────────────────────────────────────────────────────
  function systemsHtml(){
    const rows = roadmap().systems || [];
    if (!rows.length) return `<div class="om-empty"><p>${H(w('sys_empty'))}</p></div>`;
    return `<div class="om-table-wrap"><table class="om-table pl-systems"><thead><tr><th>${H(w('sys_name'))}</th><th>${H(w('sys_status'))}</th><th>${H(w('sys_note'))}</th></tr></thead>
      <tbody>${rows.map(s => `<tr><td><strong>${H(s.name)}</strong></td><td><span class="om-badge ${s.status === 'bevestigd' ? 'ok' : s.status === 'onbekend' ? 'warn' : ''}">${H(w('y_' + s.status))}</span></td><td class="pl-wrap">${H(s.note || '')}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function diagramsHtml(){
    const rows = roadmap().diagrams || [];
    if (!rows.length) return `<div class="om-empty"><p>${H(w('dia_empty'))}</p></div>`;
    const phases = Object.fromEntries((roadmap().phases || []).map(p => [p.id, p.name]));
    return rows.map(d => `<section class="om-card pl-diagram"><h4>${H(d.title)}${d.phase && phases[d.phase] ? ` <span class="om-badge">${H(phases[d.phase])}</span>` : ''}</h4>
      <div class="mermaid-block" data-mermaid-id="plan-${H(d.id)}">${H(d.source)}</div></section>`).join('');
  }
  function notesHtml(){
    const r = roadmap(), n = r.notes || {};
    const texts = [r.planning_note, n.proposal, n.estimate, n.start].filter(Boolean);
    const part = (title, items) => (items && items.length ? `<div class="pl-card-part"><h5>${H(title)}</h5><ul>${items.map(i => `<li>${H(i)}</li>`).join('')}</ul></div>` : '');
    const body = (texts.length ? `<div class="pl-card-part"><h5>${H(w('notes'))}</h5>${texts.map(t => `<p>${H(t)}</p>`).join('')}</div>` : '') + part(w('prerequisites'), r.prerequisites) + part(w('pilot_all'), r.pilot_criteria) + part(w('open_points'), r.open_points);
    return `<section class="om-card pl-notes">${body}<div class="pl-card-part pl-tree-hint"><p>${H(w('tree_hint'))}</p><button type="button" class="sm-btn" data-pl-usecases>${H(w('tree_open'))}</button></div></section>`;
  }
  function importHtml(){
    return `<section class="om-card pl-import" data-pl-import><h4>${H(w('import_h'))}</h4><p class="om-small om-muted">${H(w('import_p'))}</p>
      <textarea rows="8" spellcheck="false" aria-label="${H(w('import_h'))}" data-pl-json placeholder='{"report_version": "1.0", "start_date": "2026-12-07", "weeks": 20, "groups": []}'></textarea>
      ${P.importError ? `<p class="pl-import-error" role="alert">${H(P.importError)}</p>` : ''}
      <div class="rm-edit-actions"><button type="button" class="sm-btn primary" data-pl-import-go>${H(w('import_go'))}</button>
        <label class="sm-btn pl-file">${H(w('import_file'))}<input type="file" accept="application/json,.json" data-pl-file hidden></label>
        <button type="button" class="sm-btn" data-pl-import-cancel>${H(w('cancel'))}</button></div></section>`;
  }

  // ── Paint ──────────────────────────────────────────────────────────────────
  function paint(){
    const host = P.host;
    if (!host || !host.isConnected) return;
    if (P.error) { host.innerHTML = `<div class="rm pl"><div class="om-empty"><p>${H(P.error)}</p></div></div>`; return; }
    if (!P.data) { host.innerHTML = `<div class="rm pl"><div class="wp-skeleton" aria-busy="true" aria-label="${H(w('loading'))}"><span></span><span></span></div></div>`; return; }
    const editable = !!P.data.editable;
    if (!roadmap()) {
      host.innerHTML = `<div class="rm pl"><p class="om-intro">${H(w('intro'))}</p>${P.importing ? importHtml() : `<div class="om-empty"><h3>${H(w('empty_h'))}</h3><p>${H(w(editable ? 'empty_edit' : 'empty'))}</p>${editable ? `<div class="om-actions"><button type="button" class="sm-btn primary" data-pl-import-open>${H(w('import'))}</button></div>` : ''}</div>`}</div>`;
      return;
    }
    const tabs = `<div class="om-seg pl-tabs" role="tablist">${[['plan', 'tab_plan'], ['systems', 'tab_systems'], ['diagrams', 'tab_diagrams']].map(([k, l]) => `<button type="button" role="tab" aria-selected="${P.tab === k}" aria-pressed="${P.tab === k}" data-pl-tab="${k}">${H(w(l))}</button>`).join('')}</div>`;
    const actions = editable ? `<span class="pl-actions"><button type="button" class="sm-btn" data-pl-import-open>${H(w('import'))}</button><button type="button" class="sm-btn" data-pl-export>${H(w('export'))}</button></span>` : '';
    const main = P.tab === 'systems' ? systemsHtml() : P.tab === 'diagrams' ? diagramsHtml() : ganttHtml() + notesHtml();
    host.innerHTML = `<div class="rm pl" data-tour="studio-plan"><p class="om-intro">${H(w('intro'))}</p>${stripHtml()}
      <div class="rm-bar-row">${tabs}${actions}</div>${P.importing ? importHtml() : ''}${main}</div>`;
    if (P.tab === 'diagrams' && typeof renderMermaidBlocks === 'function') { try { renderMermaidBlocks(host); } catch (_e) {} }
    if (P.open && editable) void mountPickers();
  }
  async function mountPickers(){
    if (!window.SpPicker) return;
    if (!P.options) { try { P.options = await call('/api/studio/roadmap/options'); } catch (_e) { P.options = {}; } }
    for (const t of LINK_TYPES) window.SpPicker.sources['plan:' + t] = () => (P.options[t] || []);
    const form = P.host && P.host.querySelector('[data-pl-form]');
    if (form) window.SpPicker.mountAll(form);
  }

  // ── Changing ───────────────────────────────────────────────────────────────
  async function send(body, okMsg){
    try { P.data = await post('/api/studio/roadmap', body); toast(okMsg || w('saved')); return true; }
    catch (e) { return errMsg(e); }
  }
  async function runImport(text){
    let doc;
    try { doc = JSON.parse(text); } catch (_e) { P.importError = w('import_bad'); paint(); return; }
    if (doc && typeof doc === 'object' && doc.roadmap && !doc.groups) doc = doc.roadmap;
    if (doc && typeof doc === 'object') { delete doc.updated_at; delete doc.updated_by; delete doc.version; }
    const result = await send({ op: 'import', roadmap: doc }, w('imported'));
    if (result === true) { P.importing = false; P.importError = ''; P.open = ''; P.options = null; }
    else P.importError = result;
    paint();
  }
  function exportJson(){
    const blob = new Blob([JSON.stringify(roadmap(), null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'roadmap.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  async function go(type, ref){
    if (type === 'use_case' && window.SPStudio) return window.SPStudio.openUseCase(ref);
    if (type === 'playbook' && window.SPLibrary) { if (window.SPStudio) window.SPStudio.setTab('playbooks'); return window.SPLibrary.openPlaybook(ref); }
  }
  function bind(host){
    if (host.dataset.plBound) return;
    host.dataset.plBound = '1';
    host.addEventListener('click', async ev => {
      const el = ev.target.closest('button');
      if (!el || !host.contains(el)) return;
      if (el.dataset.plTab) { P.tab = el.dataset.plTab; P.open = ''; paint(); return; }
      if (el.dataset.plOpen) {
        const id = el.dataset.plOpen;
        P.open = P.open === id ? '' : id; paint();
        const focus = P.open ? host.querySelector('[data-pl-panel] select, [data-pl-panel] button') : host.querySelector(`[data-pl-row="${CSS.escape(id)}"] .rm-title`);
        if (focus) focus.focus();
        return;
      }
      if (el.hasAttribute('data-pl-close')) { const id = P.open; P.open = ''; paint(); const back = host.querySelector(`[data-pl-row="${CSS.escape(id)}"] .rm-title`); if (back) back.focus(); return; }
      if (el.hasAttribute('data-pl-import-open')) { P.importing = true; P.importError = ''; paint(); const ta = host.querySelector('[data-pl-json]'); if (ta) ta.focus(); return; }
      if (el.hasAttribute('data-pl-import-cancel')) { P.importing = false; P.importError = ''; paint(); return; }
      if (el.hasAttribute('data-pl-import-go')) { el.disabled = true; await runImport((host.querySelector('[data-pl-json]') || {}).value || ''); return; }
      if (el.hasAttribute('data-pl-export')) { exportJson(); return; }
      if (el.hasAttribute('data-pl-usecases')) { if (window.SPStudio) window.SPStudio.setTab('usecases'); return; }
      if (el.dataset.plNav) { if (typeof switchPanel === 'function') await switchPanel(el.dataset.plNav); return; }
      if (el.dataset.plGo) { await go(el.dataset.plGo, el.dataset.plRef); }
    });
    host.addEventListener('change', ev => {
      const input = ev.target;
      if (!input.hasAttribute || !input.hasAttribute('data-pl-file') || !input.files || !input.files[0]) return;
      const reader = new FileReader();
      reader.onload = () => { const ta = host.querySelector('[data-pl-json]'); if (ta) ta.value = String(reader.result || ''); };
      reader.readAsText(input.files[0]);
    });
    host.addEventListener('submit', async ev => {
      const form = ev.target.closest('[data-pl-form]');
      if (!form) return;
      ev.preventDefault();
      const fd = new FormData(form), links = [];
      for (const t of LINK_TYPES) for (const ref of String(fd.get('link_' + t) || '').split(',').map(s => s.trim()).filter(Boolean)) links.push({ type: t, ref });
      const result = await send({ op: 'update', target: 'row', id: form.dataset.plForm, status: String(fd.get('status') || 'planned'),
                                  delivered_at: String(fd.get('delivered_at') || ''), note: String(fd.get('note') || ''), links });
      if (result !== true) toast(result);
      paint();
    });
    host.addEventListener('keydown', ev => { if (ev.key === 'Escape' && P.open && ev.target.closest('[data-pl-panel]') && !ev.target.closest('.sp-picker')) { ev.stopPropagation(); const id = P.open; P.open = ''; paint(); const back = host.querySelector(`[data-pl-row="${CSS.escape(id)}"] .rm-title`); if (back) back.focus(); } });
  }

  async function render(host){
    P.host = host;
    bind(host);
    paint();                 // at once with what is known, then the fresh evidence
    await load();
  }
  window.SPPlan = { render, title: () => w('tab_plan') };
})();
