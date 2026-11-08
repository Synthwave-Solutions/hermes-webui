/* Studio: use-case backlog and the organisation's Playbooks (8 Nov 2026).

   Backlog: every idea worth keeping, ranked by drag and drop (or the arrow
   buttons for keyboard users), with status, team, impact and effort. "Work it
   out" opens a Studio use case; "Let the agent make it" runs the design and
   build-plan steps in the background and leaves the use case at the dry run.

   Playbooks: how the organisation does a process now with the Super Agent.
   Steps with text, screenshots (upload or paste), screen recordings and voice
   notes, stored inside SynthPulse and shown only to those who may see the
   playbook. Published playbooks are visible to the organisation or the team. */
(function(){
  'use strict';
  const NL = {
    backlog_intro: 'Alle ideeën voor AI in de organisatie, op volgorde van prioriteit. Sleep om te ordenen.',
    add_idea: 'Idee toevoegen', idea_ph: 'Wat zou de Super Agent kunnen overnemen?', all_teams: 'Alle teams', all_status: 'Alle statussen',
    s_idea: 'Idee', s_chosen: 'Gekozen', s_design: 'In ontwerp', s_built: 'Gebouwd', s_live: 'Live', s_parked: 'Geparkeerd',
    work_out: 'Uitwerken', open_uc: 'Open use case', agent_make: 'Laat de agent het maken', agent_busy: 'Agent werkt…', agent_done: 'Klaar voor jouw controle', agent_failed: 'Mislukt',
    up: 'Omhoog', down: 'Omlaag', impact: 'Impact', effort: 'Moeite', team: 'Team', none: 'Geen team', remove: 'Verwijderen', undo: 'Ongedaan maken', removed: 'Idee verwijderd',
    empty_backlog: 'Nog geen ideeën. Voeg er een toe, of zet kansen uit een use case in de backlog.',
    pb_intro: 'Hoe wij processen uitvoeren met de Super Agent: stap voor stap, met screenshots en opnames.',
    new_pb: 'Nieuw playbook', search: 'Zoek in playbooks', steps: 'stappen', media: 'media', draft: 'Concept', published: 'Gepubliceerd',
    empty_pb: 'Nog geen playbooks. Maak er een, of laat de Super Agent er een schrijven vanuit een gebouwde use case.',
    title: 'Titel', summary: 'Samenvatting', trigger: 'Wanneer gebruik je dit?', visibility: 'Zichtbaar voor', category: 'Categorie', no_category: 'Zonder categorie', no_team: 'Zonder team', group_by: 'Groeperen', g_category: 'Categorie', g_team: 'Team', g_none: 'Geen', all_categories: 'Alle categorieën', v_org: 'Hele organisatie', v_team: 'Alleen het team', v_private: 'Alleen ik',
    publish: 'Publiceren', unpublish: 'Terug naar concept', save: 'Opslaan', saved: 'Opgeslagen', back: 'Alle playbooks', add_step: 'Stap toevoegen',
    step_title: 'Stap', actor: 'Wie', text: 'Wat doe je precies?', add_image: 'Screenshot', record_screen: 'Schermopname', record_voice: 'Spraaknotitie', stop_rec: 'Stop opname',
    recording: 'Opname loopt… maximaal 2 minuten', media_note: 'Opnames en afbeeldingen blijven binnen SynthPulse en zijn alleen zichtbaar voor wie dit playbook mag zien.',
    uploading: 'Uploaden…', too_big: 'Bestand is te groot (maximaal 14 MB)', remove_media: 'Verwijder', paste_hint: 'Tip: plak een screenshot direct in een stap (Ctrl+V).',
    links: 'Gebruikt', bots: 'Bots', tasks: 'Taken', skills: 'Skills', delete_pb: 'Playbook verwijderen', confirm_delete_pb: 'Dit playbook verwijderen voor iedereen? Dit kan niet ongedaan worden.',
    by: 'door', updated: 'bijgewerkt', from_uc: 'Uit use case',
    save_prompt: 'Bewaar als prompt', prompt_saved_team: 'Bewaard bij de prompts van het team', prompt_saved_org: 'Bewaard bij de prompts van de organisatie',
    prompt: 'Prompt voor de Super Agent (optioneel)', try_chat: 'Probeer in de chat', run: 'Uitvoeren', run_intro: 'Vink af wat je gedaan hebt. De tijd loopt mee; zo zien we wat dit proces nu kost.', finish: 'Afronden', note: 'Notitie (optioneel)', cancel: 'Annuleren', run_saved: 'Uitvoering vastgelegd', runs: 'keer uitgevoerd', avg: 'gem.', min: 'min', elapsed: 'Verstreken'
  };
  const EN = {
    backlog_intro: 'Every idea for AI in the organisation, in priority order. Drag to reorder.',
    add_idea: 'Add idea', idea_ph: 'What could the Super Agent take over?', all_teams: 'All teams', all_status: 'All statuses',
    s_idea: 'Idea', s_chosen: 'Chosen', s_design: 'In design', s_built: 'Built', s_live: 'Live', s_parked: 'Parked',
    work_out: 'Work it out', open_uc: 'Open use case', agent_make: 'Let the agent make it', agent_busy: 'Agent working…', agent_done: 'Ready for your review', agent_failed: 'Failed',
    up: 'Up', down: 'Down', impact: 'Impact', effort: 'Effort', team: 'Team', none: 'No team', remove: 'Delete', undo: 'Undo', removed: 'Idea deleted',
    empty_backlog: 'No ideas yet. Add one, or put opportunities from a use case on the backlog.',
    pb_intro: 'How we run processes with the Super Agent: step by step, with screenshots and recordings.',
    new_pb: 'New playbook', search: 'Search playbooks', steps: 'steps', media: 'media', draft: 'Draft', published: 'Published',
    empty_pb: 'No playbooks yet. Create one, or let the Super Agent write one from a built use case.',
    title: 'Title', summary: 'Summary', trigger: 'When do you use this?', visibility: 'Visible to', category: 'Category', no_category: 'No category', no_team: 'No team', group_by: 'Group by', g_category: 'Category', g_team: 'Team', g_none: 'None', all_categories: 'All categories', v_org: 'Whole organisation', v_team: 'Team only', v_private: 'Only me',
    publish: 'Publish', unpublish: 'Back to draft', save: 'Save', saved: 'Saved', back: 'All playbooks', add_step: 'Add step',
    step_title: 'Step', actor: 'Who', text: 'What exactly do you do?', add_image: 'Screenshot', record_screen: 'Screen recording', record_voice: 'Voice note', stop_rec: 'Stop recording',
    recording: 'Recording… at most 2 minutes', media_note: 'Recordings and images stay inside SynthPulse and are visible only to those who may see this playbook.',
    uploading: 'Uploading…', too_big: 'File is too large (at most 14 MB)', remove_media: 'Remove', paste_hint: 'Tip: paste a screenshot straight into a step (Ctrl+V).',
    links: 'Uses', bots: 'Bots', tasks: 'Tasks', skills: 'Skills', delete_pb: 'Delete playbook', confirm_delete_pb: 'Delete this playbook for everyone? This cannot be undone.',
    by: 'by', updated: 'updated', from_uc: 'From use case',
    save_prompt: 'Save as prompt', prompt_saved_team: 'Saved to the team prompts', prompt_saved_org: 'Saved to the organisation prompts',
    prompt: 'Prompt for the Super Agent (optional)', try_chat: 'Try in chat', run: 'Run it', run_intro: 'Tick what you did. The clock runs along; that shows what this process costs now.', finish: 'Finish', note: 'Note (optional)', cancel: 'Cancel', run_saved: 'Run recorded', runs: 'runs', avg: 'avg.', min: 'min', elapsed: 'Elapsed'
  };
  const lang = () => ((document.documentElement.lang || 'nl').toLowerCase().startsWith('en') ? 'en' : 'nl');
  const w = k => (lang() === 'en' ? EN : NL)[k] || NL[k] || k;
  const H = v => (typeof esc === 'function' ? esc(String(v ?? '')) : String(v ?? ''));
  const toast = m => { if (typeof showToast === 'function') showToast(m); };
  const call = (p, o) => api(p, Object.assign({ timeoutToast: false }, o || {}));
  const post = (p, b) => call(p, { method: 'POST', body: JSON.stringify(b) });
  const errMsg = e => (e && e.message) || String(e);
  const STATUSES = ['idea', 'chosen', 'design', 'built', 'live', 'parked'];
  const BLOCK = { task: 'Geplande taak', skill: 'Skill', bot: 'Bot', human: 'Mens', connection: 'Koppeling', custom: 'Maatwerk' };

  const L = { cat: '', group: (() => { try { return localStorage.getItem('sp-pb-group') || 'category'; } catch (_e) { return 'category'; } })(),
    runMode: null, body: null, tab: '', teams: [], items: [], team: '', status: '', pbs: [], q: '', pb: null, poll: null, rec: null, removedItem: null };
  const teamName = k => (L.teams.find(t => t.key === k) || {}).name || '';
  const mediaUrl = (pb, f) => '/api/studio/media?pb=' + encodeURIComponent(pb) + '&f=' + encodeURIComponent(f);

  async function render(body, tab, teams){
    L.body = body; L.tab = tab; L.teams = teams || L.teams;
    bind(body.closest('#mainStudio'));
    if (tab === 'backlog') { await loadBacklog(); paintBacklog(); }
    else if (L.pb) paintPlaybook();
    else { await loadPlaybooks(); if (L.pb) paintPlaybook(); else paintPlaybooks(); }
  }

  // ── Backlog ────────────────────────────────────────────────────────────────
  async function loadBacklog(){ try { L.items = (await call('/api/studio/backlog')).items || []; } catch (e) { toast(errMsg(e)); L.items = []; } }
  function itemRow(it, i, n){
    const ap = it.autopilot;
    const apHtml = ap ? (ap.failed ? `<span class="om-badge error" title="${H(ap.message)}">${H(w('agent_failed'))}</span>` : ap.done ? `<span class="om-badge ok">${H(w('agent_done'))}</span>` : `<span class="om-badge warn st-pulse">${H(w('agent_busy'))} ${H(ap.message || '')}</span>`) : '';
    const score = (it.impact || 3) - (it.effort || 3);
    return `<li class="bl-item" draggable="${it.editable ? 'true' : 'false'}" data-bl="${H(it.id)}">
      <span class="bl-grip" aria-hidden="true">⋮⋮</span><span class="st-num">${i + 1}</span>
      <div class="om-row-main"><div class="om-row-title">${H(it.title)}</div>
        <div class="om-row-sub">${H(it.pain || it.why || '')}</div>
        <div class="om-chips"><span class="om-chip">${H(BLOCK[it.building_block] || it.building_block)}</span><span class="om-chip">${H(w('impact'))} ${it.impact} · ${H(w('effort'))} ${it.effort}</span>${score >= 2 ? '<span class="om-chip bl-quick">Quick win</span>' : ''}${it.team ? `<span class="om-chip">${H(teamName(it.team) || it.team)}</span>` : ''}${apHtml}</div></div>
      <div class="om-row-actions">
        <span class="bl-secondary">
        ${it.editable ? `<select class="om-select" data-bl-status aria-label="Status">${STATUSES.map(s => `<option value="${s}" ${it.status === s ? 'selected' : ''}>${H(w('s_' + s))}</option>`).join('')}</select>
        <button type="button" class="sm-btn bl-arrow" data-bl-move="-1" ${i === 0 ? 'disabled' : ''} aria-label="${H(w('up'))}">↑</button><button type="button" class="sm-btn bl-arrow" data-bl-move="1" ${i === n - 1 ? 'disabled' : ''} aria-label="${H(w('down'))}">↓</button>` : ''}
        ${it.use_case ? '' : `<button type="button" class="sm-btn" data-bl-work>${H(w('work_out'))}</button>`}
        ${it.editable ? `<button type="button" class="sm-btn bl-arrow" data-bl-remove aria-label="${H(w('remove'))}">✕</button>` : ''}
        </span>
        ${it.editable ? '' : `<span class="om-badge">${H(w('s_' + it.status))}</span>`}
        ${it.use_case ? `<button type="button" class="sm-btn" data-bl-open="${H(it.use_case)}">${H(w('open_uc'))}</button>` : ''}
        ${!it.use_case || (ap && ap.failed) ? `<button type="button" class="sm-btn ${i === 0 ? 'primary' : ''}" data-bl-agent>✨ ${H(w('agent_make'))}</button>` : ''}
      </div></li>`;
  }
  function paintBacklog(){
    const items = L.items.filter(i => (!L.team || i.team === L.team) && (!L.status || i.status === L.status));
    L.body.innerHTML = `<p class="om-intro">${H(w('backlog_intro'))}</p>
      <form class="bl-add om-card" data-bl-add data-tour="studio-backlog-add"><input name="title" required maxlength="140" placeholder="${H(w('idea_ph'))}" aria-label="${H(w('idea_ph'))}">
        <select name="team" class="om-select" aria-label="${H(w('team'))}"><option value="">${H(w('none'))}</option>${L.teams.map(t => `<option value="${H(t.key)}">${H(t.name)}</option>`).join('')}</select>
        <button type="submit" class="sm-btn primary">${H(w('add_idea'))}</button></form>
      <div class="bl-filters"><select class="om-select" data-bl-filter-team><option value="">${H(w('all_teams'))}</option>${L.teams.map(t => `<option value="${H(t.key)}" ${L.team === t.key ? 'selected' : ''}>${H(t.name)}</option>`).join('')}</select>
        <select class="om-select" data-bl-filter-status><option value="">${H(w('all_status'))}</option>${STATUSES.map(s => `<option value="${s}" ${L.status === s ? 'selected' : ''}>${H(w('s_' + s))}</option>`).join('')}</select></div>
      ${items.length ? `<ol class="bl-list" data-tour="studio-backlog">${items.map((it, i) => itemRow(it, i, items.length)).join('')}</ol>` : `<div class="om-empty"><p>${H(w('empty_backlog'))}</p></div>`}`;
    const busy = L.items.some(i => i.autopilot && !i.autopilot.done);
    clearTimeout(L.poll);
    if (busy) L.poll = setTimeout(async () => { if (L.tab === 'backlog' && document.body.contains(L.body)) { await loadBacklog(); paintBacklog(); } }, 3000);
  }
  async function saveOrder(ids){ try { await post('/api/studio/backlog/order', { ids }); } catch (e) { toast(errMsg(e)); } await loadBacklog(); paintBacklog(); }

  // ── Playbooks list ─────────────────────────────────────────────────────────
  async function loadPlaybooks(){ try { L.pbs = (await call('/api/studio/playbooks')).playbooks || []; } catch (e) { toast(errMsg(e)); L.pbs = []; } }
  function pbCard(p){
    return `<button type="button" class="pb-card" data-pb-open="${H(p.id)}">
          <span class="pb-cover">${p.cover ? `<img src="${H(mediaUrl(p.id, p.cover))}" alt="" loading="lazy">` : '<span class="pb-cover-icon" aria-hidden="true">📘</span>'}</span>
          <span class="pb-body"><span class="pb-title">${H(p.title)}</span><span class="om-small om-muted pb-summary">${H(p.summary || '')}</span>
          <span class="om-chips">${L.group !== 'team' && p.team ? `<span class="om-chip">${H(teamName(p.team) || p.team)}</span>` : ''}${L.group !== 'category' && p.category ? `<span class="om-chip">${H(p.category)}</span>` : ''}<span class="om-chip">${p.steps} ${H(w('steps'))}</span>${p.media ? `<span class="om-chip">${p.media} ${H(w('media'))}</span>` : ''}${p.stats && p.stats.complete ? `<span class="om-chip">${p.stats.complete}× · ${H(w('avg'))} ${p.stats.avg_minutes ?? '·'} ${H(w('min'))}</span>` : ''}<span class="om-badge ${p.status === 'published' ? 'ok' : ''}">${H(w(p.status === 'published' ? 'published' : 'draft'))}</span></span></span>
        </button>`;
  }
  function paintPlaybooks(){
    const q = L.q.toLowerCase();
    const rows = L.pbs.filter(p => (!L.team || p.team === L.team) && (!L.cat || (p.category || '') === L.cat) && (!q || (p.title + ' ' + (p.summary || '') + ' ' + (p.category || '')).toLowerCase().includes(q)));
    const cats = [...new Set(L.pbs.map(p => p.category).filter(Boolean))].sort();
    const keyOf = p => L.group === 'team' ? (teamName(p.team) || (p.team ? p.team : w('no_team'))) : L.group === 'category' ? (p.category || w('no_category')) : '';
    const groups = new Map();
    for (const p of rows) { const k = keyOf(p); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(p); }
    const last = k => k === w('no_category') || k === w('no_team');
    const ordered = [...groups.entries()].sort((a, b) => last(a[0]) - last(b[0]) || a[0].localeCompare(b[0]));
    let open = {}; try { open = JSON.parse(localStorage.getItem('sp-pb-open') || '{}') || {}; } catch (_e) {}
    const grid = list => `<div class="pb-grid">${list.map(pbCard).join('')}</div>`;
    L.body.innerHTML = `<p class="om-intro">${H(w('pb_intro'))}</p>
      <div class="bl-filters"><input class="om-select pb-search" type="search" data-pb-q value="${H(L.q)}" placeholder="${H(w('search'))}" aria-label="${H(w('search'))}">
        <select class="om-select" data-pb-team><option value="">${H(w('all_teams'))}</option>${L.teams.map(t => `<option value="${H(t.key)}" ${L.team === t.key ? 'selected' : ''}>${H(t.name)}</option>`).join('')}</select>
        ${cats.length ? `<select class="om-select" data-pb-cat><option value="">${H(w('all_categories'))}</option>${cats.map(c => `<option value="${H(c)}" ${L.cat === c ? 'selected' : ''}>${H(c)}</option>`).join('')}</select>` : ''}
        <div class="om-seg" role="group" aria-label="${H(w('group_by'))}">${['category', 'team', 'none'].map(g => `<button type="button" aria-pressed="${L.group === g}" data-pb-group="${g}">${H(w('g_' + g))}</button>`).join('')}</div>
        <button type="button" class="sm-btn primary" data-pb-new data-tour="studio-playbook-new" style="margin-left:auto">${H(w('new_pb'))}</button></div>
      ${!rows.length ? `<div class="om-empty"><p>${H(w('empty_pb'))}</p><div class="om-actions"><button type="button" class="sm-btn primary" data-pb-new>${H(w('new_pb'))}</button></div></div>`
        : L.group === 'none' ? grid(rows)
        : `<div class="pb-groups" data-tour="studio-playbooks">${ordered.map(([k, list]) => { const id = L.group + ':' + k; return `<details class="pb-group" data-pb-gopen="${H(id)}" ${open[id] === false ? '' : 'open'}>
            <summary><span class="om-chev" aria-hidden="true"></span><strong>${H(k)}</strong><span class="om-side-count">${list.length}</span></summary>${grid(list)}</details>`; }).join('')}</div>`}`;
  }

  // ── One playbook ───────────────────────────────────────────────────────────
  async function openPlaybook(id){
    try { L.pb = await call('/api/studio/playbook?id=' + encodeURIComponent(id)); } catch (e) { toast(errMsg(e)); return; }
    if (window.SPStudio && L.tab !== 'playbooks') { window.SPStudio.setTab('playbooks'); return; }
    paintPlaybook();
  }
  function mediaHtml(m, i, j, editable){
    const url = mediaUrl(L.pb.id, m.file);
    const el = m.kind === 'video' ? `<video src="${H(url)}" controls preload="metadata"></video>` : m.kind === 'audio' ? `<audio src="${H(url)}" controls preload="metadata"></audio>` : `<a href="${H(url)}" target="_blank" rel="noopener"><img src="${H(url)}" alt="${H(m.caption || '')}" loading="lazy"></a>`;
    return `<figure class="pb-media">${el}${editable ? `<figcaption><input data-pb-caption="${i}:${j}" value="${H(m.caption || '')}" placeholder="Bijschrift" aria-label="Bijschrift"><button type="button" class="sm-btn" data-pb-media-remove="${i}:${j}">${H(w('remove_media'))}</button></figcaption>` : (m.caption ? `<figcaption>${H(m.caption)}</figcaption>` : '')}</figure>`;
  }
  function promptBox(s, i){
    return s.prompt ? `<div class="pb-prompt"><code>${H(s.prompt)}</code><button type="button" class="sm-btn" data-pb-try="${i}">💬 ${H(w('try_chat'))}</button><button type="button" class="sm-btn" data-pb-save-prompt="${i}">${H(w('save_prompt'))}</button></div>` : '';
  }
  function statsLine(pb){
    const st = pb.stats || {};
    return st.complete ? `<span class="om-small om-muted">${st.complete} ${H(w('runs'))} · ${H(w('avg'))} ${st.avg_minutes ?? '·'} ${H(w('min'))}</span>` : '';
  }
  function paintRun(){
    const pb = L.pb, r = L.runMode;
    const mins = Math.max(0, Math.round((Date.now() - r.started) / 60000));
    L.body.innerHTML = `<div class="pb-toolbar"><button type="button" class="sm-btn" data-pb-run-cancel>${H(w('cancel'))}</button><strong>${H(pb.title)}</strong><span style="margin-left:auto" class="om-badge warn">${H(w('elapsed'))}: <span data-pb-clock>${mins}</span> ${H(w('min'))}</span></div>
      <p class="om-intro">${H(w('run_intro'))}</p>
      <ol class="pb-steps">${(pb.steps || []).map((s, i) => `<li class="pb-step pb-run-step ${r.done.has(i) ? 'done' : ''}"><label class="pb-check"><input type="checkbox" data-pb-done="${i}" ${r.done.has(i) ? 'checked' : ''}><span class="st-num">${i + 1}</span><strong>${H(s.title)}</strong>${s.actor ? `<span class="om-badge">${H(s.actor)}</span>` : ''}</label>
        <div class="pb-text">${H(s.text)}</div>${promptBox(s, i)}<div class="pb-media-row">${(s.media || []).map((m, j) => mediaHtml(m, i, j, false)).join('')}</div></li>`).join('')}</ol>
      <label class="om-field wide">${H(w('note'))}<input data-pb-run-note maxlength="400"></label>
      <div class="om-value-actions"><button type="button" class="sm-btn primary" data-pb-run-finish>${H(w('finish'))}</button></div>`;
    clearInterval(r.tick);
    r.tick = setInterval(() => { const c = L.body.querySelector('[data-pb-clock]'); if (!c || !L.runMode) { clearInterval(r.tick); return; } c.textContent = Math.max(0, Math.round((Date.now() - r.started) / 60000)); }, 15000);
  }
  async function tryInChat(text){
    if (typeof switchPanel === 'function') await switchPanel('chat');
    if (typeof newSession === 'function') await newSession(false);
    const box = document.getElementById('msg');
    if (box) { box.value = text; box.focus(); if (typeof autoResize === 'function') autoResize(); }
  }
  function paintPlaybook(){
    if (L.runMode) { paintRun(); return; }
    const pb = L.pb; const ed = !!pb.editable;
    const links = pb.links || {};
    const linkHtml = ['bots', 'tasks', 'skills'].filter(k => (links[k] || []).length).map(k => `<span class="om-small"><strong>${H(w(k))}:</strong> ${H(links[k].join(', '))}</span>`).join(' · ');
    if (!ed) {
      L.body.innerHTML = `<div class="pb-toolbar"><button type="button" class="sm-btn" data-pb-back>← ${H(w('back'))}</button>${statsLine(pb)}<button type="button" class="sm-btn primary" data-pb-run style="margin-left:auto">▶ ${H(w('run'))}</button></div>
        <article class="pb-read"><h2>${H(pb.title)}</h2><p class="om-intro">${H(pb.summary || '')}</p>${pb.trigger ? `<p class="om-small"><strong>${H(w('trigger'))}</strong> ${H(pb.trigger)}</p>` : ''}${linkHtml ? `<p>${linkHtml}</p>` : ''}
        <ol class="pb-steps">${(pb.steps || []).map((s, i) => `<li class="pb-step"><div class="pb-step-head"><span class="st-num">${i + 1}</span><strong>${H(s.title)}</strong>${s.actor ? `<span class="om-badge">${H(s.actor)}</span>` : ''}</div><div class="pb-text">${H(s.text)}</div>${promptBox(s, i)}<div class="pb-media-row">${(s.media || []).map((m, j) => mediaHtml(m, i, j, false)).join('')}</div></li>`).join('')}</ol></article>`;
      return;
    }
    L.body.innerHTML = `<div class="pb-toolbar"><button type="button" class="sm-btn" data-pb-back>← ${H(w('back'))}</button>
        <span class="om-badge ${pb.status === 'published' ? 'ok' : ''}">${H(w(pb.status === 'published' ? 'published' : 'draft'))}</span>
        ${statsLine(pb)}<span style="margin-left:auto"></span><button type="button" class="sm-btn" data-pb-run>▶ ${H(w('run'))}</button><button type="button" class="sm-btn danger" data-pb-delete>${H(w('delete_pb'))}</button>
        <button type="button" class="sm-btn" data-pb-publish>${H(w(pb.status === 'published' ? 'unpublish' : 'publish'))}</button><button type="button" class="sm-btn primary" data-pb-save>${H(w('save'))}</button></div>
      <div class="om-value-form pb-meta">
        <label class="om-field wide">${H(w('title'))}<input data-pb-f="title" value="${H(pb.title)}"></label>
        <label class="om-field wide">${H(w('summary'))}<textarea data-pb-f="summary" rows="2">${H(pb.summary || '')}</textarea></label>
        <label class="om-field wide">${H(w('trigger'))}<input data-pb-f="trigger" value="${H(pb.trigger || '')}"></label>
        <label class="om-field">${H(w('team'))}<select data-pb-f="team"><option value="">${H(w('none'))}</option>${L.teams.map(t => `<option value="${H(t.key)}" ${pb.team === t.key ? 'selected' : ''}>${H(t.name)}</option>`).join('')}</select></label>
        <label class="om-field">${H(w('category'))}<input data-pb-f="category" list="pbCategories" maxlength="60" value="${H(pb.category || '')}"><datalist id="pbCategories">${[...new Set(L.pbs.map(p => p.category).filter(Boolean))].sort().map(c => `<option value="${H(c)}">`).join('')}</datalist></label>
        <label class="om-field">${H(w('visibility'))}<select data-pb-f="visibility">${['org', 'team', 'private'].map(v => `<option value="${v}" ${pb.visibility === v ? 'selected' : ''}>${H(w('v_' + v))}</option>`).join('')}</select></label>
      </div>
      ${linkHtml ? `<p>${H(w('links'))}: ${linkHtml}</p>` : ''}
      <p class="om-small om-muted">${H(w('media_note'))} ${H(w('paste_hint'))}</p>
      <ol class="pb-steps" data-tour="studio-playbook-steps">${(pb.steps || []).map((s, i) => `<li class="pb-step" data-pb-step="${i}">
        <div class="pb-step-head"><span class="st-num">${i + 1}</span><input class="pb-step-title" data-pb-s="${i}:title" value="${H(s.title)}" placeholder="${H(w('step_title'))}" aria-label="${H(w('step_title'))}"><input class="pb-actor" data-pb-s="${i}:actor" value="${H(s.actor || '')}" placeholder="${H(w('actor'))}" aria-label="${H(w('actor'))}"></div>
        <textarea data-pb-s="${i}:text" rows="3" placeholder="${H(w('text'))}" aria-label="${H(w('text'))}">${H(s.text || '')}</textarea>
        <div class="pb-prompt-edit"><textarea data-pb-s="${i}:prompt" rows="2" placeholder="${H(w('prompt'))}" aria-label="${H(w('prompt'))}">${H(s.prompt || '')}</textarea>${s.prompt ? `<button type="button" class="sm-btn" data-pb-try="${i}">💬 ${H(w('try_chat'))}</button><button type="button" class="sm-btn" data-pb-save-prompt="${i}">${H(w('save_prompt'))}</button>` : ''}</div>
        <div class="pb-media-row">${(s.media || []).map((m, j) => mediaHtml(m, i, j, true)).join('')}</div>
        <div class="pb-step-actions"><label class="sm-btn pb-file">🖼 ${H(w('add_image'))}<input type="file" accept="image/*,video/webm,video/mp4" data-pb-file="${i}" hidden></label>
          <button type="button" class="sm-btn" data-pb-rec="screen:${i}">${L.rec && L.rec.step === i && L.rec.kind === 'screen' ? '⏹ ' + H(w('stop_rec')) : '🎥 ' + H(w('record_screen'))}</button>
          <button type="button" class="sm-btn" data-pb-rec="voice:${i}">${L.rec && L.rec.step === i && L.rec.kind === 'voice' ? '⏹ ' + H(w('stop_rec')) : '🎙 ' + H(w('record_voice'))}</button>
          ${L.rec && L.rec.step === i ? `<span class="om-small pb-rec-note">● ${H(w('recording'))}</span>` : ''}
          <button type="button" class="sm-btn" data-pb-step-up="${i}" ${i === 0 ? 'disabled' : ''} aria-label="${H(w('up'))}">↑</button><button type="button" class="sm-btn" data-pb-step-remove="${i}" aria-label="${H(w('remove'))}">✕</button></div>
      </li>`).join('')}</ol>
      <button type="button" class="sm-btn" data-pb-add-step>＋ ${H(w('add_step'))}</button>`;
  }
  function collectPb(){
    const pb = L.pb;
    L.body.querySelectorAll('[data-pb-f]').forEach(el => { pb[el.dataset.pbF] = el.value; });
    L.body.querySelectorAll('[data-pb-s]').forEach(el => { const [i, k] = el.dataset.pbS.split(':'); if (pb.steps[i]) pb.steps[i][k] = el.value; });
    L.body.querySelectorAll('[data-pb-caption]').forEach(el => { const [i, j] = el.dataset.pbCaption.split(':').map(Number); if (pb.steps[i] && pb.steps[i].media[j]) pb.steps[i].media[j].caption = el.value; });
    return pb;
  }
  async function savePb(extra, quiet){
    const pb = collectPb();
    try {
      L.pb = await post('/api/studio/playbook', Object.assign({ id: pb.id, title: pb.title, summary: pb.summary, trigger: pb.trigger, team: pb.team, category: pb.category || '', visibility: pb.visibility, steps: pb.steps }, extra || {}));
      if (!quiet) toast(w('saved'));
    } catch (e) { toast(errMsg(e)); }
    paintPlaybook();
  }
  function blobToB64(blob){ return new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(',')[1] || ''); r.onerror = rej; r.readAsDataURL(blob); }); }
  async function addMedia(step, blob, type){
    if (blob.size > 14 * 1024 * 1024) { toast(w('too_big')); return; }
    collectPb();
    toast(w('uploading'));
    try {
      const m = await post('/api/studio/media', { playbook: L.pb.id, type: type || blob.type, data: await blobToB64(blob) });
      L.pb.steps[step].media = (L.pb.steps[step].media || []).concat([{ file: m.file, kind: m.kind, caption: '' }]);
      await savePb({}, true);
    } catch (e) { toast(errMsg(e)); }
  }
  async function toggleRecord(kind, step){
    if (L.rec) { const r = L.rec; L.rec = null; try { r.recorder.stop(); } catch (_e) {} r.stream.getTracks().forEach(t => t.stop()); clearTimeout(r.timer); paintPlaybook(); return; }
    let stream;
    try { stream = kind === 'screen' ? await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 12 }, audio: false }) : await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch (e) { toast(errMsg(e)); return; }
    const mime = kind === 'screen' ? (MediaRecorder.isTypeSupported('video/webm;codecs=vp9') ? 'video/webm;codecs=vp9' : 'video/webm') : 'audio/webm';
    const recorder = new MediaRecorder(stream, kind === 'screen' ? { mimeType: mime, videoBitsPerSecond: 900000 } : { mimeType: mime, audioBitsPerSecond: 64000 });
    const chunks = [];
    recorder.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
    recorder.onstop = async () => { const blob = new Blob(chunks, { type: mime.split(';')[0] }); if (blob.size) await addMedia(step, blob, mime.split(';')[0]); };
    stream.getVideoTracks().forEach(t => t.addEventListener('ended', () => { if (L.rec && L.rec.recorder === recorder) toggleRecord(kind, step); }));
    recorder.start(1000);
    L.rec = { kind, step, recorder, stream, timer: setTimeout(() => { if (L.rec && L.rec.recorder === recorder) toggleRecord(kind, step); }, 120000) };
    paintPlaybook();
  }

  // ── Events ─────────────────────────────────────────────────────────────────
  function bind(root){
    if (!root || root.dataset.slBound) return;
    root.dataset.slBound = '1';
    let dragId = null;
    root.addEventListener('dragstart', ev => { const li = ev.target.closest('.bl-item'); if (li) { dragId = li.dataset.bl; li.classList.add('dragging'); ev.dataTransfer.effectAllowed = 'move'; } });
    root.addEventListener('dragend', ev => { const li = ev.target.closest('.bl-item'); if (li) li.classList.remove('dragging'); });
    root.addEventListener('dragover', ev => { const li = ev.target.closest('.bl-item'); if (li && dragId) { ev.preventDefault(); const list = li.parentNode; const dragged = list.querySelector(`[data-bl="${dragId}"]`); if (dragged && dragged !== li) { const after = ev.clientY > li.getBoundingClientRect().top + li.offsetHeight / 2; list.insertBefore(dragged, after ? li.nextSibling : li); } } });
    root.addEventListener('drop', async ev => { if (!dragId) return; ev.preventDefault(); dragId = null; const ids = [...root.querySelectorAll('.bl-item')].map(li => li.dataset.bl); await saveOrder(ids); });
    root.addEventListener('paste', async ev => {
      const step = ev.target.closest && ev.target.closest('[data-pb-step]');
      if (!step || !L.pb) return;
      const file = [...(ev.clipboardData && ev.clipboardData.files || [])].find(f => f.type.startsWith('image/'));
      if (file) { ev.preventDefault(); await addMedia(Number(step.dataset.pbStep), file); }
    });
    root.addEventListener('submit', async ev => {
      if (!ev.target.hasAttribute('data-bl-add')) return;
      ev.preventDefault();
      const fd = new FormData(ev.target);
      try { await post('/api/studio/backlog', { title: String(fd.get('title') || ''), team: String(fd.get('team') || '') }); } catch (e) { toast(errMsg(e)); }
      await loadBacklog(); paintBacklog();
    });
    root.addEventListener('change', async ev => {
      const el = ev.target;
      if (el.hasAttribute('data-bl-filter-team')) { L.team = el.value; paintBacklog(); return; }
      if (el.hasAttribute('data-bl-filter-status')) { L.status = el.value; paintBacklog(); return; }
      if (el.hasAttribute('data-pb-team')) { L.team = el.value; paintPlaybooks(); return; }
      if (el.hasAttribute('data-pb-cat')) { L.cat = el.value; paintPlaybooks(); return; }
      if (el.hasAttribute('data-bl-status')) { const id = el.closest('[data-bl]').dataset.bl; try { await post('/api/studio/backlog', { id, status: el.value }); } catch (e) { toast(errMsg(e)); } await loadBacklog(); paintBacklog(); return; }
      if (el.dataset.pbDone !== undefined && L.runMode) { const i = Number(el.dataset.pbDone); if (el.checked) L.runMode.done.add(i); else L.runMode.done.delete(i); el.closest('.pb-step').classList.toggle('done', el.checked); return; }
      if (el.dataset.pbFile !== undefined && el.files && el.files[0]) { await addMedia(Number(el.dataset.pbFile), el.files[0]); }
    });
    root.addEventListener('toggle', ev => {
      const d = ev.target;
      if (!d || !d.dataset || !d.dataset.pbGopen) return;
      let open = {}; try { open = JSON.parse(localStorage.getItem('sp-pb-open') || '{}') || {}; } catch (_e) {}
      open[d.dataset.pbGopen] = d.open; try { localStorage.setItem('sp-pb-open', JSON.stringify(open)); } catch (_e) {}
    }, true);
    root.addEventListener('input', ev => { if (ev.target.hasAttribute('data-pb-q')) { L.q = ev.target.value; const pos = ev.target.selectionStart; paintPlaybooks(); const q = L.body.querySelector('[data-pb-q]'); if (q) { q.focus(); q.setSelectionRange(pos, pos); } } });
    root.addEventListener('click', async ev => {
      const b = ev.target.closest('button');
      if (!b || !L.body || !L.body.contains(b)) return;
      const li = b.closest('[data-bl]');
      if (b.dataset.pbGroup) { L.group = b.dataset.pbGroup; try { localStorage.setItem('sp-pb-group', L.group); } catch (_e) {} paintPlaybooks(); return; }
      if (b.dataset.blMove && li) { const ids = L.items.filter(i => (!L.team || i.team === L.team) && (!L.status || i.status === L.status)).map(i => i.id); const k = ids.indexOf(li.dataset.bl); const t = k + Number(b.dataset.blMove); if (t >= 0 && t < ids.length) { [ids[k], ids[t]] = [ids[t], ids[k]]; await saveOrder(ids); const nb = L.body.querySelector(`[data-bl="${li.dataset.bl}"] [data-bl-move="${b.dataset.blMove}"]`); if (nb && !nb.disabled) nb.focus(); } return; }
      if (b.hasAttribute('data-bl-remove') && li) {
        const item = L.items.find(i => i.id === li.dataset.bl);
        try { await post('/api/studio/backlog', { id: item.id, delete: true }); } catch (e) { toast(errMsg(e)); return; }
        L.removedItem = item; await loadBacklog(); paintBacklog();
        if (typeof showToast === 'function') showToast(w('removed'));
        const undo = document.createElement('button'); undo.type = 'button'; undo.className = 'sm-btn bl-undo'; undo.textContent = w('undo');
        undo.onclick = async () => { const it = L.removedItem; L.removedItem = null; undo.remove(); if (it) { await post('/api/studio/backlog', { title: it.title, pain: it.pain, why: it.why, goal: it.goal, impact: it.impact, effort: it.effort, building_block: it.building_block, team: it.team || '', status: it.status }); await loadBacklog(); paintBacklog(); } };
        L.body.prepend(undo); setTimeout(() => undo.remove(), 10000);
        return;
      }
      if (b.dataset.blOpen) { if (window.SPStudio) await window.SPStudio.openUseCase(b.dataset.blOpen); return; }
      if (b.hasAttribute('data-bl-work') && li) {
        const it = L.items.find(i => i.id === li.dataset.bl);
        try {
          const doc = await post('/api/studio/usecase', { title: it.title, team: it.team || '', opportunities: [{ id: 'o1', title: it.title, pain: it.pain, why: it.why, goal: it.goal, impact: it.impact, effort: it.effort, building_block: it.building_block }], selected: 'o1', phase: 'design', goals: [{ name: it.goal || it.title, kpi: '' }] });
          await post('/api/studio/backlog', { id: it.id, status: 'design', use_case: doc.id });
          if (window.SPStudio) await window.SPStudio.openUseCase(doc.id);
        } catch (e) { toast(errMsg(e)); }
        return;
      }
      if (b.hasAttribute('data-bl-agent') && li) { b.disabled = true; try { await post('/api/studio/autopilot', { id: li.dataset.bl }); } catch (e) { toast(errMsg(e)); } await loadBacklog(); paintBacklog(); return; }
      if (b.hasAttribute('data-pb-new')) { try { L.pb = await post('/api/studio/playbook', { title: w('new_pb'), team: L.team || '', steps: [{ title: '', actor: '', text: '', prompt: '', media: [] }] }); paintPlaybook(); } catch (e) { toast(errMsg(e)); } return; }
      if (b.dataset.pbOpen) { await openPlaybook(b.dataset.pbOpen); return; }
      if (b.hasAttribute('data-pb-back')) { if (L.rec) await toggleRecord(); L.runMode = null; L.pb = null; await loadPlaybooks(); paintPlaybooks(); return; }
      if (b.hasAttribute('data-pb-save')) { await savePb(); return; }
      if (b.hasAttribute('data-pb-publish')) { await savePb({ status: L.pb.status === 'published' ? 'draft' : 'published' }); return; }
      if (b.hasAttribute('data-pb-delete')) { if (!confirm(w('confirm_delete_pb'))) return; try { await post('/api/studio/playbook/delete', { id: L.pb.id }); } catch (e) { toast(errMsg(e)); return; } L.pb = null; await loadPlaybooks(); paintPlaybooks(); return; }
      if (b.hasAttribute('data-pb-add-step')) { collectPb(); L.pb.steps.push({ title: '', actor: '', text: '', media: [] }); paintPlaybook(); const last = L.body.querySelectorAll('.pb-step-title'); if (last.length) last[last.length - 1].focus(); return; }
      if (b.dataset.pbStepRemove !== undefined) { collectPb(); L.pb.steps.splice(Number(b.dataset.pbStepRemove), 1); paintPlaybook(); return; }
      if (b.dataset.pbStepUp !== undefined) { collectPb(); const i = Number(b.dataset.pbStepUp); [L.pb.steps[i - 1], L.pb.steps[i]] = [L.pb.steps[i], L.pb.steps[i - 1]]; paintPlaybook(); return; }
      if (b.dataset.pbMediaRemove) { collectPb(); const [i, j] = b.dataset.pbMediaRemove.split(':').map(Number); L.pb.steps[i].media.splice(j, 1); await savePb({}, true); return; }
      if (b.dataset.pbSavePrompt !== undefined) {
        if (!L.runMode && L.pb.editable) collectPb();
        const st = L.pb.steps[Number(b.dataset.pbSavePrompt)];
        if (st && st.prompt && window.SPPrompts) { try { await window.SPPrompts.saveFromStep(L.pb, st); toast(w(L.pb.team ? 'prompt_saved_team' : 'prompt_saved_org')); } catch (e) { toast(errMsg(e)); } }
        return;
      }
      if (b.dataset.pbTry !== undefined) { if (!L.runMode && L.pb.editable) collectPb(); const s = L.pb.steps[Number(b.dataset.pbTry)]; if (s && s.prompt) await tryInChat(s.prompt); return; }
      if (b.hasAttribute('data-pb-run')) { if (L.pb.editable) collectPb(); L.runMode = { started: Date.now(), done: new Set() }; paintPlaybook(); return; }
      if (b.hasAttribute('data-pb-run-cancel')) { clearInterval(L.runMode && L.runMode.tick); L.runMode = null; paintPlaybook(); return; }
      if (b.hasAttribute('data-pb-run-finish')) {
        const r = L.runMode; clearInterval(r.tick);
        const note = (L.body.querySelector('[data-pb-run-note]') || {}).value || '';
        try { await post('/api/studio/playbook/run', { id: L.pb.id, minutes: Math.max(1, Math.round((Date.now() - r.started) / 60000)), done: [...r.done], note }); toast(w('run_saved')); L.pb = await call('/api/studio/playbook?id=' + encodeURIComponent(L.pb.id)); }
        catch (e) { toast(errMsg(e)); }
        L.runMode = null; paintPlaybook(); return;
      }
      if (b.dataset.pbRec) { const [kind, i] = b.dataset.pbRec.split(':'); await toggleRecord(kind, Number(i)); return; }
    });
  }

  window.SPLibrary = { reset: () => { L.pb = null; L.runMode = null; }, render, openPlaybook: async (id) => { L.pb = null; try { L.pb = await call('/api/studio/playbook?id=' + encodeURIComponent(id)); } catch (e) { toast(errMsg(e)); } if (window.SPStudio) window.SPStudio.setTab('playbooks'); } };
})();
