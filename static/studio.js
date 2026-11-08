/* Use Case Studio (8 Nov 2026): discover, design, playbook, build, measure.

   Left: the conversation (type, or speak with the browser's dictation).
   Right: the canvas of the current phase. Model steps run on the server
   (/api/studio/step); building runs here through the existing routes so it
   happens under the person's own rights and governance:
     task       POST /api/crons/create (paused, with value, team, category)
     skill      POST /api/skills/save (non-admin skills wait for approval)
     human      POST /api/kanban/tasks
     connection a link to Connections (people connect accounts themselves)
   Nothing is enabled or sent without a click. */
(function(){
  'use strict';
  const NL = {
    n_goal: 'Gewenst doel', n_pain: 'Knelpunt', n_opp: 'Kans', n_sol: 'Oplossing', untitled: 'Naamloze use case', cause: 'Oorzaak', test: 'Kleinste test',
    q_quick: 'Snelle winst', q_big: 'Grote inzet', q_fill: 'Opvulling', q_pit: 'Geldput',
    tab_uc: 'Use cases', tab_backlog: 'Backlog', tab_pb: 'Playbooks', nav_work: 'Werk', nav_me: 'Over jou', nav_prompts: 'Prompts', nav_profile: 'Organisatieprofiel', nav_org: 'Organisatie', nav_chart: 'Organigram', nav_teams: 'Teams beheren', nav_mgmt: 'Management', nav_recent: 'Recent', nav_help: 'Uitleg over dit scherm', conv_hide: 'Gesprek verbergen', conv_show: 'Gesprek tonen', view_matrix: 'Matrix', view_tree: 'Boom', to_backlog: 'Naar backlog', in_backlog: 'In backlog', all_to_backlog: 'Alle kansen naar de backlog', make_pb: 'Maak er een Playbook van', no_goal: 'Overig',
    studio: 'Studio', intro: 'Ontdek waar AI je werk overneemt, richt het proces in en laat de Super Agent het bouwen.',
    new_uc: 'Nieuwe use case', team: 'Team', none: 'Geen team', title_ph: 'Naam van deze use case', back: 'Use cases',
    p_discover: 'Ontdekken', p_design: 'Inrichten', p_playbook: 'Bouwplan', p_build: 'Bouwen', p_measure: 'Meten',
    conv: 'Gesprek', send: 'Verstuur', speak: 'Praten', listening: 'Luistert…', thinking: 'De Super Agent denkt na…',
    ph_discover: 'Vertel over je werk: wat doe je elke week, wat kost veel tijd, wat gaat er mis?',
    ph_design: 'Beschrijf hoe het proces nu loopt, stap voor stap: wie doet wat, in welk systeem, hoe lang?',
    ph_playbook: 'Extra wensen voor het bouwplan (optioneel), bijvoorbeeld ritme of wie het nakijkt.',
    g_processes: 'Huidige processen', g_processes_d: 'Beschrijf wat je team dagelijks doet',
    g_pain: 'Knelpunten', g_pain_d: 'Wat kost te veel tijd of moeite?', g_goals: 'Doelen', g_goals_d: 'Wat zou je willen verbeteren?',
    topics: 'Voorbeeldonderwerpen', t1: 'E-mail en communicatie afhandelen', t2: 'Documenten verwerken en beoordelen',
    t3: 'Gegevens invoeren en rapporteren', t4: 'Klanten opvolgen',
    goals: 'Doelen', opps: 'Kansen en oplossingen', impact: 'Impact', effort: 'Moeite', choose: 'Kies', chosen: 'Gekozen',
    quick_win: 'Snel resultaat', next_design: 'Verder naar inrichten', next_playbook: 'Maak het bouwplan', next_build: 'Droogrun',
    as_is: 'Zoals het nu gaat', to_be: 'Zoals het wordt', metrics: 'Succesmetingen', reuse: 'Bestaat al',
    bl_title: 'Nulmeting', bl_freq: 'Hoe vaak', bl_freq_unknown: 'nog bepalen', bl_min: 'Handwerk per keer', bl_hours: 'Uren per week', freq_day: 'per dag', freq_week: 'per week', freq_month: 'per maand', decision: 'Beslissing', replaces: 'Vervangt stap', data: 'Data', d_public: 'Openbaar', d_internal: 'Intern', d_confidential: 'Vertrouwelijk', d_personal: 'Persoonsgegevens', open_q: 'Nog nodig voor het bouwen',
    a_bot: 'Nieuwe bot, alleen voor jou zichtbaar, werkt voor het team', instructions: 'Instructies', live: 'Live praten', live_stop: 'Stop live', live_on: 'Live gesprek met de Super Agent: hij vult het werkvlak terwijl je praat. Wat je zegt komt ook in het tekstvak.', open_work: 'Open werk', conn_ok: 'Al verbonden', conn_req: 'Aangevraagd bij beheer', conn_none: 'Niet in de catalogus; vraag het aan via Verbindingen',
    b_task: 'Geplande taak', b_skill: 'Skill', b_bot: 'Bot', b_human: 'Blijft mens', b_connection: 'Koppeling', b_custom: 'Maatwerk',
    include: 'Meenemen', name: 'Naam', schedule: 'Ritme (cron)', prompt: 'Opdracht', before: 'Min. eerst', now: 'Min. nu', per: 'Per',
    per_run: 'keer', per_day: 'dag', per_week: 'week', description: 'Beschrijving', content: 'Werkwijze', who: 'Wie', what: 'Wat',
    provider: 'Systeem', save: 'Opslaan', saved: 'Opgeslagen', regenerate: 'Opnieuw voorstellen',
    dry_title: 'Droogrun: dit gaat er gebeuren', dry_note: 'Taken worden gepauzeerd aangemaakt. Niets wordt verstuurd of aangezet tot jij dat doet.',
    a_task: 'Nieuwe geplande taak, gepauzeerd, met waarde', a_skill: 'Nieuwe skill (bij niet-beheerders eerst ter goedkeuring)',
    a_human: 'Taak op het Kanban-bord voor een mens', a_connection: 'Koppeling: zelf verbinden via Verbindingen', a_reuse: 'Hergebruik bestaand',
    build: 'Bouwen', building: 'Bezig met bouwen…', built: 'Klaar', failed: 'Mislukt', skipped: 'Overgeslagen',
    confirm_build: 'Weet je het zeker? De onderdelen hieronder worden aangemaakt onder jouw rechten.',
    open_task: 'Open taken', open_skills: 'Open skills', open_kanban: 'Open Kanban', open_conn: 'Open Verbindingen', open_mgmt: 'Open Management',
    measure_intro: 'Wat deze use case oplevert, zie je per team in Management zodra de taken draaien. Zet ze aan in Taken na een testrun.',
    discuss: 'Bespreek in chat', delete: 'Verwijderen', confirm_delete: 'Use case verwijderen?', empty_list: 'Nog geen use cases. Begin met een gesprek over je werk.',
    components: 'onderdelen', built_n: 'gebouwd', need_input: 'Vertel eerst iets, dan gaat de Super Agent aan de slag.',
    chat_prompt: 'Ik werk in Studio aan de use case "{t}". Help me verder: {s}'
  };
  const EN = {
    n_goal: 'Desired outcome', n_pain: 'Pain point', n_opp: 'Opportunity', n_sol: 'Solution', untitled: 'Untitled use case', cause: 'Cause', test: 'Smallest test',
    q_quick: 'Quick wins', q_big: 'Big bets', q_fill: 'Fill-ins', q_pit: 'Money pit',
    tab_uc: 'Use cases', tab_backlog: 'Backlog', tab_pb: 'Playbooks', nav_work: 'Work', nav_me: 'About you', nav_prompts: 'Prompts', nav_profile: 'Organisation profile', nav_org: 'Organisation', nav_chart: 'Org chart', nav_teams: 'Manage teams', nav_mgmt: 'Management', nav_recent: 'Recent', nav_help: 'How this screen works', conv_hide: 'Hide conversation', conv_show: 'Show conversation', view_matrix: 'Matrix', view_tree: 'Tree', to_backlog: 'To backlog', in_backlog: 'In backlog', all_to_backlog: 'All opportunities to the backlog', make_pb: 'Turn it into a Playbook', no_goal: 'Other',
    studio: 'Studio', intro: 'Discover where AI takes work off your hands, design the process and let the Super Agent build it.',
    new_uc: 'New use case', team: 'Team', none: 'No team', title_ph: 'Name of this use case', back: 'Use cases',
    p_discover: 'Discover', p_design: 'Design', p_playbook: 'Build plan', p_build: 'Build', p_measure: 'Measure',
    conv: 'Conversation', send: 'Send', speak: 'Speak', listening: 'Listening…', thinking: 'The Super Agent is thinking…',
    ph_discover: 'Tell about your work: what do you do every week, what takes a lot of time, what goes wrong?',
    ph_design: 'Describe how the process runs now, step by step: who does what, in which system, how long?',
    ph_playbook: 'Extra wishes for the build plan (optional), for example rhythm or who reviews.',
    g_processes: 'Current processes', g_processes_d: 'Describe what your team does every day',
    g_pain: 'Pain points', g_pain_d: 'What takes too much time or effort?', g_goals: 'Goals', g_goals_d: 'What would you like to improve?',
    topics: 'Example topics', t1: 'Handling email and communication', t2: 'Processing and reviewing documents',
    t3: 'Entering data and reporting', t4: 'Following up customers',
    goals: 'Goals', opps: 'Opportunities and solutions', impact: 'Impact', effort: 'Effort', choose: 'Choose', chosen: 'Chosen',
    quick_win: 'Quick win', next_design: 'Continue to design', next_playbook: 'Make the build plan', next_build: 'Dry run',
    as_is: 'As it is', to_be: 'As it will be', metrics: 'Success measures', reuse: 'Already exists',
    bl_title: 'Baseline', bl_freq: 'How often', bl_freq_unknown: 'to be determined', bl_min: 'Manual work per run', bl_hours: 'Hours per week', freq_day: 'per day', freq_week: 'per week', freq_month: 'per month', decision: 'Decision', replaces: 'Replaces step', data: 'Data', d_public: 'Public', d_internal: 'Internal', d_confidential: 'Confidential', d_personal: 'Personal data', open_q: 'Still needed to build',
    a_bot: 'New bot, visible to you only, works for the team', instructions: 'Instructions', live: 'Talk live', live_stop: 'Stop live', live_on: 'Live conversation with the Super Agent: it fills the canvas while you talk. What you say also lands in the text box.', open_work: 'Open work', conn_ok: 'Already connected', conn_req: 'Requested from admins', conn_none: 'Not in the catalogue; request it in Connections',
    b_task: 'Scheduled task', b_skill: 'Skill', b_bot: 'Bot', b_human: 'Stays human', b_connection: 'Connection', b_custom: 'Custom',
    include: 'Include', name: 'Name', schedule: 'Rhythm (cron)', prompt: 'Instruction', before: 'Min. before', now: 'Min. now', per: 'Per',
    per_run: 'run', per_day: 'day', per_week: 'week', description: 'Description', content: 'Way of working', who: 'Who', what: 'What',
    provider: 'System', save: 'Save', saved: 'Saved', regenerate: 'Propose again',
    dry_title: 'Dry run: this is what will happen', dry_note: 'Tasks are created paused. Nothing is sent or switched on until you do it.',
    a_task: 'New scheduled task, paused, with its value', a_skill: 'New skill (for non-admins first for approval)',
    a_human: 'Task on the Kanban board for a person', a_connection: 'Connection: connect yourself in Connections', a_reuse: 'Reuse existing',
    build: 'Build', building: 'Building…', built: 'Done', failed: 'Failed', skipped: 'Skipped',
    confirm_build: 'Are you sure? The parts below are created under your own rights.',
    open_task: 'Open tasks', open_skills: 'Open skills', open_kanban: 'Open Kanban', open_conn: 'Open Connections', open_mgmt: 'Open Management',
    measure_intro: 'What this use case delivers shows per team in Management once the tasks run. Switch them on in Tasks after a test run.',
    discuss: 'Discuss in chat', delete: 'Delete', confirm_delete: 'Delete this use case?', empty_list: 'No use cases yet. Start with a conversation about your work.',
    components: 'components', built_n: 'built', need_input: 'Tell something first, then the Super Agent gets to work.',
    chat_prompt: 'I am working in Studio on the use case "{t}". Help me further: {s}'
  };
  const lang = () => ((document.documentElement.lang || 'nl').toLowerCase().startsWith('en') ? 'en' : 'nl');
  const w = (k, v) => { let s = (lang() === 'en' ? EN : NL)[k] || NL[k] || k; if (v) for (const [a, b] of Object.entries(v)) s = s.replace('{' + a + '}', b); return s; };
  const H = v => (typeof esc === 'function' ? esc(String(v ?? '')) : String(v ?? ''));
  const $id = id => document.getElementById(id);
  const toast = m => { if (typeof showToast === 'function') showToast(m); };
  const call = (p, o) => api(p, Object.assign({ timeoutToast: false }, o || {}));
  const post = (p, b) => call(p, { method: 'POST', body: JSON.stringify(b) });
  const errMsg = e => (e && e.message) || String(e);
  const PHASES = ['discover', 'design', 'playbook', 'build', 'measure'];

  const St = { list: null, teams: [], doc: null, busy: false, listening: false, rec: null, draft: '', building: false, presetTeam: '', tab: 'usecases', oppView: 'matrix', backlogged: new Set(), counts: {}, me: null,
    convOpen: (() => { try { return localStorage.getItem('sp-studio-conv') !== '0'; } catch (_e) { return true; } })() };

  function root(){ return $id('mainStudio'); }
  function head(actions, title){
    const r = root();
    if (!r) return null;
    if (!r.querySelector('.main-view-body')) r.innerHTML = `<div class="main-view-header"><div><div class="main-view-title" data-st-title-h></div></div><div class="om-head-actions" data-st-actions></div></div><div class="main-view-body"><div class="om-wrap st-wrap" data-st-body></div></div>`;
    r.querySelector('[data-st-title-h]').textContent = title || w('tab_uc');
    r.querySelector('[data-st-actions]').innerHTML = actions || '';
    return r.querySelector('[data-st-body]');
  }

  async function loadList(){
    try { const d = await call('/api/studio/usecases'); St.list = d.usecases || []; St.teams = d.teams || []; }
    catch (e) { St.list = []; toast(errMsg(e)); }
  }
  async function loadCounts(){
    const [bl, pb, me, pr, pf, pm] = await Promise.all([
      call('/api/studio/backlog').catch(() => null), call('/api/studio/playbooks').catch(() => null),
      St.me ? Promise.resolve(St.me) : call('/api/org/structure/me').catch(() => ({ can_view: false, can_manage: false })),
      call('/api/studio/prompts').catch(() => null), call('/api/studio/profile').catch(() => null), call('/api/studio/profile?who=me').catch(() => null)]);
    St.personEmpty = !!pm && !pm.updated_at;
    St.counts = { backlog: bl ? (bl.items || []).filter(i => !['live', 'parked'].includes(i.status)).length : null, playbooks: pb ? (pb.playbooks || []).length : null,
                  prompts: pr ? (pr.prompts || []).length : null };
    St.profileEmpty = !!pf && !pf.context;
    St.profileEditable = !!(pf && pf.editable);
    St.me = me;
  }
  async function open(id){
    try { St.doc = await call('/api/studio/usecase?id=' + encodeURIComponent(id)); St.draft = ''; if (St.doc.ui_view) St.oppView = St.doc.ui_view; }
    catch (e) { toast(errMsg(e)); St.doc = null; }
    render();
  }
  async function save(fields, quiet){
    try { St.doc = Object.assign(await post('/api/studio/usecase', Object.assign({ id: St.doc.id }, fields)), {}); if (!quiet) toast(w('saved')); }
    catch (e) { toast(errMsg(e)); }
    if ('title' in fields || 'phase' in fields) { await loadList(); renderSide(); }
  }
  async function step(name, input){
    if (St.busy) return;
    St.busy = true; render();
    try { St.doc = await post('/api/studio/step', { id: St.doc.id, step: name, input: input || '' }); St.draft = ''; if (St.doc.ui_view) St.oppView = St.doc.ui_view; }
    catch (e) { toast(errMsg(e)); }
    finally { St.busy = false; render(); }
    await loadList(); renderSide();
  }

  // ── Landing ────────────────────────────────────────────────────────────────
  function tabsHtml(){
    return `<div class="om-seg st-tabs" role="tablist">${[['usecases', 'tab_uc'], ['backlog', 'tab_backlog'], ['playbooks', 'tab_pb']].map(([k, l]) => `<button type="button" role="tab" aria-selected="${St.tab === k}" aria-pressed="${St.tab === k}" data-st-tab="${k}">${H(w(l))}</button>`).join('')}</div>`;
  }
  function renderList(){
    if ((St.tab === 'me' || St.tab === 'profile') && window.SPIntake) {
      const body = head('', w(St.tab === 'me' ? 'nav_me' : 'nav_profile'));
      if (body) window.SPIntake.render(body, St.tab === 'me' ? 'me' : 'org');
      return;
    }
    if (St.tab === 'prompts' && window.SPPrompts) {
      const body = head('', w('nav_prompts'));
      if (body) window.SPPrompts.render(body, 'prompts');
      return;
    }
    if (St.tab !== 'usecases' && window.SPLibrary) {
      const body = head('', w(St.tab === 'backlog' ? 'tab_backlog' : 'tab_pb'));
      if (body) window.SPLibrary.render(body, St.tab, St.teams);
      return;
    }
    const body = head(`<button type="button" class="sm-btn primary" data-st-new>${H(w('new_uc'))}</button>`, w('tab_uc'));
    if (!body) return;
    const rows = St.list || [];
    const teamName = k => (St.teams.find(t => t.key === k) || {}).name || '';
    body.innerHTML = `<p class="om-intro">${H(w('intro'))}</p>
      ${St.personEmpty && window.SPIntake ? `<div class="om-card st-profile-hint st-me-hint"><span>${H(window.SPIntake.hintMe())}</span><button type="button" class="sm-btn primary" data-st-hub-go="me">${H(window.SPIntake.openMe())}</button></div>` : ''}
      ${St.profileEmpty && St.profileEditable && window.SPPrompts ? `<div class="om-card st-profile-hint st-org-hint"><span>${H(window.SPPrompts.pfHint())}</span><button type="button" class="sm-btn" data-st-hub-go="profile">${H(window.SPPrompts.pfOpen())}</button></div>` : ''}
      ${rows.length ? `<div class="st-cards" data-tour="studio-usecases">${rows.map(r => `<button type="button" class="st-card" data-st-open="${H(r.id)}">
          <span class="st-card-title ${r.title ? '' : 'st-side-untitled'}">${H(r.title || w('untitled'))}</span>
          <span class="om-muted om-small">${H(teamName(r.team) || w('none'))} · ${H(w('p_' + (r.phase || 'discover')))}</span>
          <span class="st-card-meta"><span class="om-badge">${H(r.components || 0)} ${H(w('components'))}</span>${r.built ? `<span class="om-badge ok">${H(r.built)} ${H(w('built_n'))}</span>` : ''}</span>
        </button>`).join('')}</div>`
      : `<div class="om-empty" data-tour="studio-usecases"><h3>${H(w('new_uc'))}</h3><p>${H(w('empty_list'))}</p><div class="om-actions"><button type="button" class="sm-btn primary" data-st-new>${H(w('new_uc'))}</button></div></div>`}`;
  }

  // ── Use case ───────────────────────────────────────────────────────────────
  function stepper(doc){
    const cur = PHASES.indexOf(doc.phase || 'discover');
    return `<ol class="st-stepper" data-tour="studio-steps">${PHASES.map((p, i) => `<li><button type="button" data-st-phase="${p}" aria-current="${i === cur ? 'step' : 'false'}" class="${i < cur ? 'done' : ''}" ${i > cur + 1 ? 'disabled' : ''}><span>${i + 1}</span>${H(w('p_' + p))}</button></li>`).join('')}</ol>`;
  }
  function convHtml(doc){
    const notes = doc.notes || [];
    const ph = doc.phase === 'design' ? 'ph_design' : doc.phase === 'playbook' ? 'ph_playbook' : 'ph_discover';
    const canSend = ['discover', 'design', 'playbook'].includes(doc.phase || 'discover');
    const hasSpeech = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    return `<section class="st-conv" data-tour="studio-conversation" aria-label="${H(w('conv'))}">
      <div class="st-notes" aria-live="polite">${notes.map(n => `<div class="st-note ${n.role}">${H(n.text)}</div>`).join('')}${St.busy ? `<div class="st-note agent st-thinking">${H(w('thinking'))}</div>` : ''}</div>
      ${St.live ? `<p class="om-small st-live-note">${H(w('live_on'))}</p>` : ''}
      ${St.live && St.live.tasks.length ? `<div class="st-live-tasks">${St.live.tasks.map(tk => `<div class="om-row"><span class="om-dot ${tk.status === 'done' ? 'ok' : tk.status === 'error' ? 'error' : 'new'}"></span><div class="om-row-main"><div class="om-row-title">${H(tk.title || '')}</div><div class="om-row-sub">${H(tk.status || '')}</div></div>${tk.session_id ? `<button type="button" class="sm-btn" data-st-open-session="${H(tk.session_id)}">${H(w('open_work'))}</button>` : ''}</div>`).join('')}</div>` : ''}
      ${canSend ? `<form class="st-compose" data-st-send>
        <textarea name="input" rows="4" placeholder="${H(w(ph))}" aria-label="${H(w(ph))}">${H(St.draft)}</textarea>
        <div class="st-compose-actions">
          ${window.synPulseVoice ? `<button type="button" class="sm-btn" data-st-live aria-pressed="${!!St.live}">🎧 ${H(St.live ? w('live_stop') : w('live'))}</button>` : ''}
          ${hasSpeech ? `<button type="button" class="sm-btn" data-st-mic aria-pressed="${St.listening}">🎙 ${H(St.listening ? w('listening') : w('speak'))}</button>` : ''}
          <button type="button" class="sm-btn" data-st-chat>${H(w('discuss'))}</button>
          <button type="submit" class="sm-btn primary" ${St.busy ? 'disabled' : ''}>${H(w('send'))}</button>
        </div></form>` : ''}
    </section>`;
  }
  function guideHtml(){
    return `<div class="st-guide">${[['g_processes', 'g_processes_d'], ['g_pain', 'g_pain_d'], ['g_goals', 'g_goals_d']].map(([a, b]) => `<div class="om-card"><strong>${H(w(a))}</strong><p class="om-muted om-small">${H(w(b))}</p></div>`).join('')}</div>
      <p class="om-small om-muted" style="margin-top:14px">${H(w('topics'))}</p><div class="om-chips">${['t1', 't2', 't3', 't4'].map(k => `<button type="button" class="om-chip st-topic" data-st-topic="${H(w(k))}">${H(w(k))}</button>`).join('')}</div>`;
  }
  function allSolutions(doc){
    const out = [];
    (doc.opportunities || []).forEach((o, i) => (o.solutions || []).forEach((s, j) => out.push(Object.assign({}, s, { opp: o, label: (i + 1) + '.' + (j + 1) }))));
    return out;
  }
  function solRow(doc, s){
    const sel = doc.selected === s.id;
    const key = doc.id + ':' + s.id;
    return `<div class="om-row ${sel ? 'st-row-sel' : ''}"><span class="st-num st-num-wide">${H(s.label)}</span>
      <div class="om-row-main"><div class="om-row-title">${H(s.title)}</div><div class="om-row-sub">${H(s.how || '')}${s.test ? ' · ' + H(w('test')) + ': ' + H(s.test) : ''}</div></div>
      <div class="om-row-actions"><span class="om-badge">${H(w('b_' + s.building_block))}</span><span class="om-small om-muted">${H(w('impact'))} ${s.impact} · ${H(w('effort'))} ${s.effort}</span>
        <button type="button" class="sm-btn" data-st-backlog="${H(s.id)}" ${St.backlogged.has(key) ? 'disabled' : ''}>${H(St.backlogged.has(key) ? w('in_backlog') : w('to_backlog'))}</button>
        <button type="button" class="sm-btn ${sel ? 'primary' : ''}" data-st-select="${H(s.id)}">${H(sel ? w('chosen') : w('choose'))}</button></div></div>`;
  }
  function matrixHtml(doc){
    const sols = allSolutions(doc);
    const pos = o => `left:${(o.effort - 1) / 4 * 86 + 4}%;bottom:${(o.impact - 1) / 4 * 82 + 6}%`;
    return `<div class="st-matrix" role="group" aria-label="${H(w('impact'))} / ${H(w('effort'))}">
        <span class="st-quad q1">${H(w('q_quick'))}</span><span class="st-quad q2">${H(w('q_big'))}</span><span class="st-quad q3">${H(w('q_fill'))}</span><span class="st-quad q4">${H(w('q_pit'))}</span>
        <span class="st-axis y" style="top:auto;bottom:50%;left:4px;writing-mode:vertical-rl;transform:rotate(180deg)">${H(w('impact'))} ↑</span><span class="st-axis x" style="bottom:4px;right:50%;transform:translateX(50%)">${H(w('effort'))} →</span>
        ${sols.map(s => `<button type="button" class="st-dot ${doc.selected === s.id ? 'sel' : ''}" style="${pos(s)}" data-st-select="${H(s.id)}" title="${H(s.title + ' (' + s.opp.title + ')')}">${H(s.label)}</button>`).join('')}
      </div>
      <div class="st-opp-list">${(doc.opportunities || []).map((o, i) => `<div class="om-card st-opp-card"><div class="st-opp-head"><span class="st-node-kind">${H(w('n_opp'))} ${i + 1}</span><strong>${H(o.title)}</strong>${o.cause ? `<span class="om-small om-muted">${H(w('cause'))}: ${H(o.cause)}</span>` : ''}</div>
        ${allSolutions(doc).filter(s => s.opp.id === o.id).map(s => solRow(doc, s)).join('')}</div>`).join('')}</div>`;
  }
  function treeHtml(doc){
    const goals = (doc.goals || []).map(g => g.name);
    const groups = {};
    for (const o of doc.opportunities || []) {
      const g = goals.includes(o.goal) ? o.goal : (goals.length === 1 ? goals[0] : w('no_goal'));
      (groups[g] = groups[g] || []).push(o);
    }
    const order = goals.concat(Object.keys(groups).filter(k => !goals.includes(k)));
    const sols = allSolutions(doc);
    return `<div class="st-tree" role="tree">${order.filter(g => groups[g]).map(g => {
      const goal = (doc.goals || []).find(x => x.name === g) || {};
      return `<div class="st-tree-goal" role="treeitem" aria-expanded="true"><div class="st-node goal"><span class="st-node-kind">${H(w('n_goal'))}</span><strong>${H(g)}</strong>${goal.kpi ? `<span class="om-small om-muted">${H(goal.kpi)}${goal.baseline || goal.target ? ' · ' + H(goal.baseline || '?') + ' → ' + H(goal.target || '?') : ''}</span>` : ''}</div>
        <div class="st-tree-children" role="group">${groups[g].map(o => `<div class="st-tree-opp">
          <div class="st-node pain"><span class="st-node-kind">${H(w('n_opp'))}</span><strong>${H(o.title)}</strong>${o.cause ? `<span class="om-small om-muted">${H(w('cause'))}: ${H(o.cause)}</span>` : ''}</div>
          <div class="st-tree-sols">${sols.filter(s => s.opp.id === o.id).map(s => `<div class="st-node sol bb-${H(s.building_block)} ${doc.selected === s.id ? 'sel' : ''}">
            <span class="st-node-kind">${H(w('n_sol'))} ${H(s.label)}</span><strong>${H(s.title)}</strong>
            <span class="st-node-meta"><span class="om-badge">${H(w('b_' + s.building_block))}</span><span>${H(w('impact'))} ${s.impact}</span><span>${H(w('effort'))} ${s.effort}</span></span>
            ${s.test ? `<span class="om-small om-muted">${H(w('test'))}: ${H(s.test)}</span>` : ''}
            <span class="st-node-actions"><button type="button" class="sm-btn ${doc.selected === s.id ? 'primary' : ''}" data-st-select="${H(s.id)}">${H(doc.selected === s.id ? w('chosen') : w('choose'))}</button><button type="button" class="sm-btn" data-st-backlog="${H(s.id)}" ${St.backlogged.has(doc.id + ':' + s.id) ? 'disabled' : ''}>${H(St.backlogged.has(doc.id + ':' + s.id) ? w('in_backlog') : w('to_backlog'))}</button></span></div>`).join('')}</div>
        </div>`).join('')}</div></div>`;
    }).join('')}</div>`;
  }
  function discoverHtml(doc){
    if (!(doc.opportunities || []).length) return guideHtml();
    return `<h3>${H(w('goals'))}</h3><div class="st-goals">${(doc.goals || []).map(g => `<div class="om-card st-goal"><span class="st-node-kind">${H(w('n_goal'))}</span><strong>${H(g.name)}</strong><span class="om-muted om-small">${H(g.kpi)}</span>${g.baseline || g.target ? `<span class="st-kpi"><b>${H(g.baseline || '?')}</b> → <b>${H(g.target || '?')}</b></span>` : ''}</div>`).join('')}</div>
      <div class="om-section-head" style="margin-top:20px" data-tour="studio-opportunities"><h3>${H(w('opps'))}</h3><div class="om-seg" style="margin-left:auto">${['matrix', 'tree'].map(v => `<button type="button" aria-pressed="${St.oppView === v}" data-st-oppview="${v}">${H(w('view_' + v))}</button>`).join('')}</div></div>
      ${St.oppView === 'tree' ? treeHtml(doc) : matrixHtml(doc)}
      <div class="om-value-actions" style="margin-top:8px"><button type="button" class="sm-btn" data-st-backlog-all>${H(w('all_to_backlog'))}</button></div>
      <div class="om-value-actions"><button type="button" class="sm-btn primary" data-st-goto="design" ${doc.selected ? '' : 'disabled'}>${H(w('next_design'))}</button></div>`;
  }
  function laneHtml(steps, toBe){
    return `<div class="st-lane">${(steps || []).map((s, i) => `<div class="st-step ${toBe ? 'bb-' + (s.building_block || 'human') : ''} ${!toBe && s.pain ? 'has-pain' : ''}">
        <span class="st-step-n">${i + 1}${!toBe && s.decision ? ` <span class="om-badge st-decision">${H(w('decision'))}</span>` : ''}</span><strong>${H(s.step)}</strong>
        <span class="om-small om-muted">${H(s.actor)}${s.minutes ? ' · ' + s.minutes + ' min' : ''}</span>
        ${!toBe && (s.tools || []).length ? `<span class="st-tools">${s.tools.map(t => `<span class="st-tool">${H(t)}</span>`).join('')}</span>` : ''}
        ${!toBe && s.pain ? `<span class="om-small st-pain">${H(s.pain)}</span>` : ''}
        ${toBe ? `<span class="om-badge">${H(w('b_' + (s.building_block || 'human')))}</span>${s.note ? `<span class="om-small">${H(s.note)}</span>` : ''}${(s.replaces || []).length ? `<span class="om-small om-muted">${H(w('replaces'))} ${H(s.replaces.join(', '))}</span>` : ''}${(s.reuse || []).length ? `<span class="om-small st-reuse">${H(w('reuse'))}: ${H(s.reuse.join(', '))}</span>` : ''}` : ''}
      </div>`).join('')}</div>`;
  }
  const num = v => Number(v || 0).toLocaleString(lang() === 'en' ? 'en-GB' : 'nl-NL', {maximumFractionDigits: 1});
  function baselineHtml(p){
    const b = p.baseline || {}, f = p.frequency || {};
    if (!b.minutes_before && !p.data_sensitivity) return '';
    const freq = f.count ? `${f.count} ${w('freq_' + (f.per || 'week'))}` : w('bl_freq_unknown');
    const cell = (label, before, after) => `<div class="om-card st-bl"><span class="st-node-kind">${H(label)}</span><span class="st-kpi"><b>${H(before)}</b>${after !== undefined ? ` → <b>${H(after)}</b>` : ''}</span></div>`;
    return `<h3>${H(w('bl_title'))}</h3><div class="st-bl-row" data-tour="studio-baseline">
      ${cell(w('bl_freq'), freq)}
      ${b.minutes_before ? cell(w('bl_min'), b.minutes_before + ' min', (b.minutes_after || 0) + ' min') : ''}
      ${b.hours_week_before != null ? cell(w('bl_hours'), num(b.hours_week_before) + ' u', num(b.hours_week_after) + ' u') : ''}
      ${p.data_sensitivity ? `<div class="om-card st-bl st-data-${H(p.data_sensitivity)}"><span class="st-node-kind">${H(w('data'))}</span><b>${H(w('d_' + p.data_sensitivity))}</b>${p.data_note ? `<span class="om-small om-muted">${H(p.data_note)}</span>` : ''}</div>` : ''}
    </div>`;
  }
  function designHtml(doc){
    const p = doc.process || {};
    const chosen = allSolutions(doc).find(s => s.id === doc.selected) || allSolutions(doc).find(s => s.opp.id === doc.selected);
    const head = chosen ? `<div class="st-chosen"><span class="st-node-kind">${H(w('n_opp'))}</span> ${H(chosen.opp.title)}<br><span class="st-node-kind">${H(w('n_sol'))}</span> <strong>${H(chosen.title)}</strong> <span class="om-badge">${H(w('b_' + chosen.building_block))}</span></div>` : '';
    if (!(p.to_be || []).length) return `${head}<p class="om-muted">${H(w('ph_design'))}</p>`;
    return `${head}${baselineHtml(p)}<h3 style="margin-top:18px">${H(w('as_is'))}</h3>${laneHtml(p.as_is)}<h3 style="margin-top:18px">${H(w('to_be'))}</h3>${laneHtml(p.to_be, true)}
      ${(p.metrics || []).length ? `<h3 style="margin-top:18px">${H(w('metrics'))}</h3><div class="st-goals">${p.metrics.map(m => `<div class="om-card st-goal"><strong>${H(m.name)}</strong><span class="om-small om-muted">${H(m.baseline)} → ${H(m.target)}</span></div>`).join('')}</div>` : ''}
      ${(p.questions || []).length ? `<div class="om-card st-questions"><strong>${H(w('open_q'))}</strong><ul>${p.questions.map(q => `<li>${H(q)}</li>`).join('')}</ul></div>` : ''}
      <div class="om-value-actions"><button type="button" class="sm-btn primary" data-st-make-playbook>${H(w('next_playbook'))}</button></div>`;
  }
  function compHtml(c, i){
    const f = (k, label, type, extra) => `<label class="om-field">${H(label)}<input data-st-f="${k}" data-i="${i}" ${type ? 'type="' + type + '"' : ''} value="${H(c[k] ?? '')}" ${extra || ''}></label>`;
    let fields = '';
    if (c.type === 'task') fields = f('name', w('name')) + f('schedule', w('schedule')) + f('before_minutes', w('before'), 'number', 'min="0"') + f('review_minutes', w('now'), 'number', 'min="0"')
      + `<label class="om-field">${H(w('per'))}<select data-st-f="per" data-i="${i}">${['run', 'day', 'week'].map(p => `<option value="${p}" ${c.per === p ? 'selected' : ''}>${H(w('per_' + p))}</option>`).join('')}</select></label>`
      + `<label class="om-field wide">${H(w('prompt'))}<textarea data-st-f="prompt" data-i="${i}" rows="4">${H(c.prompt)}</textarea></label>`;
    else if (c.type === 'bot') fields = f('name', w('name')) + f('description', w('description')) + `<label class="om-field wide">${H(w('instructions'))}<textarea data-st-f="instructions" data-i="${i}" rows="4">${H(c.instructions)}</textarea></label>`;
    else if (c.type === 'skill') fields = f('name', w('name')) + f('description', w('description')) + `<label class="om-field wide">${H(w('content'))}<textarea data-st-f="content" data-i="${i}" rows="5">${H(c.content)}</textarea></label>`;
    else if (c.type === 'human') fields = f('name', w('name')) + f('who', w('who')) + f('what', w('what'));
    else fields = f('name', w('name')) + f('provider', w('provider')) + f('why', w('what'));
    return `<div class="st-comp om-card ${c.include ? '' : 'off'}"><div class="st-comp-head"><span class="om-badge">${H(w('b_' + c.type))}</span><strong>${H(c.name)}</strong>
        ${c.reuse ? `<span class="om-small st-reuse">${H(w('reuse'))}: ${H(c.reuse)}</span>` : ''}
        <label class="st-include"><input type="checkbox" data-st-include="${i}" ${c.include ? 'checked' : ''}> ${H(w('include'))}</label></div>
      <div class="om-value-form">${fields}</div></div>`;
  }
  function playbookHtml(doc){
    const comps = (doc.playbook || {}).components || [];
    if (!comps.length) return `<p class="om-muted">${H(w('ph_playbook'))}</p><div class="om-value-actions"><button type="button" class="sm-btn primary" data-st-make-playbook>${H(w('next_playbook'))}</button></div>`;
    return `<p class="om-small om-muted">v${H((doc.playbook || {}).version)}</p><div class="st-comps" data-tour="studio-plan">${comps.map(compHtml).join('')}</div>
      <div class="om-value-actions"><button type="button" class="sm-btn" data-st-save-playbook>${H(w('save'))}</button><button type="button" class="sm-btn" data-st-make-playbook>${H(w('regenerate'))}</button><button type="button" class="sm-btn primary" data-st-goto="build">${H(w('next_build'))}</button></div>`;
  }
  function buildHtml(doc){
    const comps = ((doc.playbook || {}).components || []).filter(c => c.include);
    const log = {};
    for (const b of doc.build_log || []) log[b.key] = b;
    const done = (doc.build_log || []).length > 0;
    return `<h3>${H(w('dry_title'))}</h3><p class="om-small om-muted">${H(w('dry_note'))}</p>
      <div class="om-card" style="padding:4px 0">${comps.map(c => { const b = log[c.key]; return `<div class="om-row">
        <span class="om-dot ${b ? (b.status === 'ok' ? 'ok' : b.status === 'failed' ? 'error' : 'paused') : 'new'}"></span>
        <div class="om-row-main"><div class="om-row-title">${H(c.name)}</div><div class="om-row-sub">${H(c.reuse ? w('a_reuse') + ': ' + c.reuse + ' · ' : '')}${H(w('a_' + c.type))}${c.type === 'task' ? ` · ${c.before_minutes}→${c.review_minutes} min/${w('per_' + c.per)}` : ''}</div></div>
        <div class="om-row-actions">${b ? `<span class="om-badge ${b.status === 'ok' ? 'ok' : b.status === 'failed' ? 'error' : ''}">${H(w(b.status === 'ok' ? 'built' : b.status))}</span>${b.error ? `<span class="om-small om-muted">${H(b.error)}</span>` : ''}` : ''}</div></div>`; }).join('')}</div>
      ${St.building ? `<p class="om-small">${H(w('building'))}</p>` : done
        ? `<div class="om-value-actions"><button type="button" class="sm-btn" data-st-nav="tasks">${H(w('open_task'))}</button><button type="button" class="sm-btn" data-st-nav="skills">${H(w('open_skills'))}</button><button type="button" class="sm-btn" data-st-nav="kanban">${H(w('open_kanban'))}</button>${comps.some(c => c.type === 'connection') ? `<button type="button" class="sm-btn" data-st-nav="integrations">${H(w('open_conn'))}</button>` : ''}<button type="button" class="sm-btn primary" data-st-goto="measure">${H(w('p_measure'))}</button></div>`
        : `<div class="st-confirm" data-tour="studio-build"><span>${H(w('confirm_build'))}</span><button type="button" class="sm-btn primary" data-st-build>${H(w('build'))}</button></div>`}`;
  }
  function measureHtml(doc){
    const ok = (doc.build_log || []).filter(b => b.status === 'ok');
    return `<p class="om-intro">${H(w('measure_intro'))}</p><div class="om-card" style="padding:4px 0">${ok.map(b => `<div class="om-row"><span class="om-dot ok"></span><div class="om-row-main"><div class="om-row-title">${H(b.ref)}</div><div class="om-row-sub">${H(w('b_' + b.type))}</div></div></div>`).join('')}</div>
      <div class="om-value-actions"><button type="button" class="sm-btn primary" data-st-make-pb>${H(w('make_pb'))}</button><button type="button" class="sm-btn" data-st-nav="tasks">${H(w('open_task'))}</button><button type="button" class="sm-btn" data-st-nav="management">${H(w('open_mgmt'))}</button></div>`;
  }
  function renderDoc(){
    const doc = St.doc;
    const body = head(`<button type="button" class="sm-btn" data-st-conv-toggle aria-pressed="${St.convOpen}">${H(St.convOpen ? w('conv_hide') : w('conv_show'))}</button>${doc.editable ? `<button type="button" class="sm-btn st-quiet-danger" data-st-delete>${H(w('delete'))}</button>` : ''}`,
      w('tab_uc'));
    const r = root(); const t = r && r.querySelector('[data-st-title-h]');
    if (t && !(document.activeElement && document.activeElement.matches && document.activeElement.matches('[data-st-title]'))) t.innerHTML = `<button type="button" class="st-crumb" data-st-back>${H(w('back'))}</button><span class="st-crumb-sep" aria-hidden="true">/</span><input class="st-crumb-input" data-st-title value="${H(doc.title)}" placeholder="${H(w('title_ph'))}" aria-label="${H(w('title_ph'))}" ${doc.editable ? '' : 'readonly'}>`;
    if (!body) return;
    const canvas = { discover: discoverHtml, design: designHtml, playbook: playbookHtml, build: buildHtml, measure: measureHtml }[doc.phase || 'discover'](doc);
    body.innerHTML = `<div class="st-top">${stepper(doc)}
        <label class="om-inline-form om-small om-muted st-team-pick">${H(w('team'))} <select class="om-select" data-st-team><option value="">${H(w('none'))}</option>${St.teams.map(t => `<option value="${H(t.key)}" ${doc.team === t.key ? 'selected' : ''}>${H(t.name)}</option>`).join('')}</select></label></div>
      <div class="st-layout ${St.convOpen || St.live ? '' : 'conv-closed'}">${St.convOpen || St.live ? convHtml(doc) : ''}<section class="st-canvas" aria-live="polite">${canvas}</section></div>`;
    const notes = body.querySelector('.st-notes');
    if (notes) notes.scrollTop = notes.scrollHeight;
  }
  function section(){
    const cur = typeof _currentPanel === 'string' ? _currentPanel : 'studio';
    if (cur === 'management') return 'mgmt';
    if (cur === 'organisation') return window.SPOrg && window.SPOrg.view && window.SPOrg.view() === 'manage' ? 'teams' : 'chart';
    return St.tab;
  }
  function renderSide(){
    const panel = $id('panelStudio');
    if (!panel) return;
    let box = panel.querySelector('.om-side');
    if (!box) {
      box = document.createElement('nav'); box.className = 'om-side st-hub-nav'; box.id = 'studioHubNav'; panel.append(box);
      box.addEventListener('click', async ev => {
        const b = ev.target.closest('button');
        if (!b) return;
        const go = b.dataset.stHub;
        if ((go || b.dataset.stSideOpen || b.hasAttribute('data-st-side-new')) && typeof _isDesktopWidth === 'function' && !_isDesktopWidth() && typeof closeMobileSidebar === 'function') closeMobileSidebar();
        if (go === 'usecases' || go === 'backlog' || go === 'playbooks' || go === 'prompts' || go === 'profile' || go === 'me') {
          St.tab = go; St.doc = null;
          if (window.SPLibrary && window.SPLibrary.reset) window.SPLibrary.reset();
          if (_currentPanel !== 'studio' && typeof switchPanel === 'function') await switchPanel('studio'); else { await loadList(); render(); }
          return;
        }
        if (go === 'chart' || go === 'teams') { if (window.SPOrg && window.SPOrg.show) await window.SPOrg.show(go === 'teams' ? 'manage' : 'chart'); renderSide(); return; }
        if (go === 'mgmt') { if (typeof switchPanel === 'function') await switchPanel('management'); renderSide(); return; }
        if (b.dataset.stSideOpen) { St.tab = 'usecases'; if (_currentPanel !== 'studio' && typeof switchPanel === 'function') await switchPanel('studio'); await open(b.dataset.stSideOpen); return; }
        if (b.hasAttribute('data-st-side-new')) {
          St.tab = 'usecases';
          if (_currentPanel !== 'studio' && typeof switchPanel === 'function') await switchPanel('studio');
          try { St.doc = await post('/api/studio/usecase', {}); } catch (e) { toast(errMsg(e)); }
          render();
        }
      });
    }
    const sec = section();
    const me = St.me || {};
    const item = (key, label, count, flag) => `<button type="button" data-st-hub="${key}" aria-current="${sec === key && !(key === 'usecases' && St.doc)}">${flag ? '<span class="om-side-flag" aria-hidden="true"></span>' : ''}${H(label)}${count != null ? `<span class="om-side-count">${H(count)}</span>` : ''}</button>`;
    const rows = (St.list || []).slice(0, 5);
    box.setAttribute('aria-label', w('studio'));
    box.innerHTML = `<button type="button" class="st-side-new" data-st-side-new>＋ ${H(w('new_uc'))}</button>
      <div class="om-side-label">${H(w('nav_work'))}</div>
      ${item('me', w('nav_me'), null, St.personEmpty)}${item('usecases', w('tab_uc'), (St.list || []).length || null)}${item('backlog', w('tab_backlog'), St.counts.backlog || null)}${item('playbooks', w('tab_pb'), St.counts.playbooks || null)}${item('prompts', w('nav_prompts'), St.counts.prompts || null)}
      <div class="om-side-label">${H(w('nav_org'))}</div>${item('profile', w('nav_profile'), null, St.profileEmpty && me.can_manage)}${me.can_view ? item('chart', w('nav_chart')) : ''}${me.can_manage ? item('teams', w('nav_teams')) + item('mgmt', w('nav_mgmt')) : ''}
      ${rows.length ? `<div class="om-side-label">${H(w('nav_recent'))}</div>` + rows.map(r => `<button type="button" class="st-side-recent" data-st-side-open="${H(r.id)}" aria-current="${!!(St.doc && St.doc.id === r.id && sec === 'usecases')}"><span class="st-side-recent-title ${r.title ? '' : 'st-side-untitled'}">${H(r.title || w('untitled'))}</span><span class="om-side-count">${H(w('p_' + (r.phase || 'discover')))}</span></button>`).join('') : ''}
      <button type="button" class="st-side-help" data-help-guide="${sec === 'mgmt' ? 'management' : (sec === 'chart' || sec === 'teams') ? 'organisation' : 'studio'}">${H(w('nav_help'))}</button>`;
  }
  function render(){ if (St.doc) renderDoc(); else renderList(); renderSide(); }

  // ── Building ───────────────────────────────────────────────────────────────
  async function runBuild(){
    const doc = St.doc;
    const order = { bot: 0, skill: 1, task: 2, human: 3, connection: 4 };
    const comps = ((doc.playbook || {}).components || []).filter(c => c.include).sort((a, b) => (order[a.type] ?? 9) - (order[b.type] ?? 9));
    St.building = true; render();
    const log = [];
    const botSlugs = {};
    const slug = s => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    let catalog = null, connections = null;
    const teamName = (St.teams.find(t => t.key === doc.team) || {}).name || '';
    for (const c of comps) {
      const row = { key: c.key, type: c.type, status: 'ok', ref: c.name, at: Date.now() / 1000 };
      try {
        if (c.type === 'bot') {
          // A short suffix keeps the profile id unique: a deleted profile leaves a
          // tombstone that blocks reusing the same id.
          const name = ('studio-' + slug(c.name)).slice(0, 54) + '-' + Math.random().toString(36).slice(2, 6);
          await post('/api/bots/builder', { name, title: c.name, description: c.description || '', skills: [], mcp_servers: [], cli_tools: [], allowed_users: [], allowed_groups: [], default_model: '', model_provider: '',
            system_prompt: `${c.instructions || c.description || c.name}\n\nJe bent gemaakt in Studio voor de use case "${doc.title}". Je verstuurt nooit zelf iets naar anderen; je maakt concepten en vraagt eerst.` });
          botSlugs[slug(c.name)] = name;
          if (doc.team) {
            // The builder may finish creating the profile home a moment later.
            let placed = false;
            for (let attempt = 0; attempt < 8 && !placed; attempt++) {
              try {
                const list = await call('/api/profiles?fast=1');
                const prof = ((list && list.profiles) || []).find(p => p.name === name) || {};
                await post('/api/profile/appearance', { name, revision: prof.bot_revision || 0, bot: { serves: [doc.team], kind: 'bot' } });
                placed = true;
              } catch (_e) { await new Promise(r => setTimeout(r, 1000)); }
            }
            if (!placed) row.error = 'Team niet gezet; kies het in de bot-editor';
          }
          row.ref = 'bot ' + name;
        } else if (c.type === 'task') {
          const value = c.before_minutes > 0
            ? { before_minutes: c.before_minutes, review_minutes: Math.min(c.review_minutes || 0, c.before_minutes), per: c.per || 'run', task: c.name, source: 'playbook', confidence: 'estimated' }
            : { unknown: true, unknown_reason: 'Nog in te vullen na de testrun', task: c.name, source: 'playbook' };
          if (doc.team) value.team = doc.team;
          const prompt = `${c.prompt}\n\nCATEGORY: ${teamName || 'Studio'}`;
          const res = await post('/api/crons/create', { name: c.name, prompt, schedule: c.schedule, deliver: 'local', enabled: false, value, category: teamName || 'Studio' });
          row.ref = (res.job && res.job.name) || c.name;
          const bot = c.bot && botSlugs[slug(c.bot)];
          if (bot && res.job) {
            await post('/api/crons/assign', { job_id: res.job.id, owner_profile: res.job.owner_profile || 'default', bot });
            row.ref += ' → ' + bot;
          }
        } else if (c.type === 'skill') {
          const slug = String(c.name || c.key).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48) || c.key;
          const content = `---\nname: ${slug}\ndescription: ${String(c.description || c.name).replace(/\n/g, ' ')}\nmetadata:\n  studio_use_case: ${doc.id}\n  studio_component: ${c.key}\n---\n\n${c.content || ''}\n`;
          const res = await post('/api/skills/save', { name: slug, category: 'studio', content });
          row.ref = 'skill ' + (res.name || slug);
        } else if (c.type === 'human') {
          await post('/api/kanban/tasks', { title: c.name, body: `${c.what || ''}\n\nWie: ${c.who || ''}\nUit Studio: ${doc.title}`, created_by: 'studio', idempotency_key: doc.id + ':' + c.key });
        } else {
          if (catalog === null) { try { catalog = (await call('/api/integrations/catalog')).providers || []; } catch (_e) { catalog = []; } }
          if (connections === null) { try { connections = (await call('/api/integrations/connections')).connections || []; } catch (_e) { connections = []; } }
          const want = slug(c.provider || c.name);
          const match = catalog.find(p => [p.key, p.unique_key, p.display_name].some(v => slug(v) === want));
          const connected = match && connections.some(x => [match.key, match.unique_key].includes(x.provider_config_key));
          if (connected) { row.ref = (match.display_name || c.name) + ': ' + w('conn_ok'); }
          else if (match) { await post('/api/integrations/request', { provider_config_key: match.unique_key || match.key }); row.ref = (match.display_name || c.name) + ': ' + w('conn_req'); }
          else { row.status = 'skipped'; row.error = w('conn_none'); }
        }
      } catch (e) { row.status = 'failed'; row.error = errMsg(e).slice(0, 280); }
      log.push(row);
      St.doc.build_log = log.slice(); render();
    }
    St.building = false;
    await save({ build_log: log, phase: 'build' }, true);
    render();
  }

  // ── Events ─────────────────────────────────────────────────────────────────
  function collectComponents(){
    const comps = JSON.parse(JSON.stringify((St.doc.playbook || {}).components || []));
    root().querySelectorAll('[data-st-f]').forEach(el => {
      const c = comps[Number(el.dataset.i)];
      if (!c) return;
      const k = el.dataset.stF;
      c[k] = el.type === 'number' ? Number(el.value || 0) : el.value;
    });
    root().querySelectorAll('[data-st-include]').forEach(el => { const c = comps[Number(el.dataset.stInclude)]; if (c) c.include = el.checked; });
    return comps;
  }
  // Live: the realtime voice agent (static/realtime_voice.js) in a chat
  // session of its own for this use case. What the person says flows into the
  // compose box; sending stays a click, so the model steps run on purpose.
  async function toggleLive(){
    const voice = window.synPulseVoice;
    if (!voice) return;
    if (St.live) { await stopLive(); return; }
    let sid = St.doc.voice_session;
    if (!sid) {
      const data = await post('/api/session/new', {});
      sid = data && data.session && data.session.session_id;
      if (!sid) { toast('Voice session could not start'); return; }
      try { await post('/api/session/rename', { session_id: sid, title: 'Studio · ' + (St.doc.title || 'use case') }); } catch (_e) {}
      await save({ voice_session: sid }, true);
    }
    const base = (root().querySelector('[data-st-send] textarea') || {}).value || '';
    // The voice client only runs for the conversation that is open in the chat
    // (d.current()), so open this use case's voice conversation in the
    // background and put the previous one back when live talking stops.
    const state = typeof S !== 'undefined' ? S : null;
    const previous = state && state.session && state.session.session_id;
    if (typeof loadSession === 'function' && previous !== sid) {
      try { await loadSession(sid); } catch (_e) {}
      if (typeof switchPanel === 'function') await switchPanel('studio');
    }
    const original = voice.d.transcript;
    const originalTasks = voice.d.tasks;
    St.live = { original, originalTasks, base, previous, tasks: [], seen: St.doc.updated_at };
    voice.d.tasks = (tasks, controller) => {
      try { if (originalTasks) originalTasks(tasks, controller); } catch (_e) {}
      if (St.live) { St.live.tasks = (tasks || []).slice(-6); render(); }
    };
    // The voice agent's Studio tools change the use case on the server; follow along.
    St.live.poll = setInterval(async () => {
      if (!St.live || !St.doc) return;
      try {
        const fresh = await call('/api/studio/usecase?id=' + encodeURIComponent(St.doc.id));
        if (fresh.updated_at !== St.live.seen) {
          St.live.seen = fresh.updated_at;
          if (fresh.title !== St.doc.title) loadList().then(renderSide).catch(() => {});
          const draft = St.draft;
          St.doc = fresh; St.draft = draft;
          if (fresh.ui_view) St.oppView = fresh.ui_view;
          render();
          const canvas = root() && root().querySelector('.st-canvas');
          if (canvas) { canvas.classList.remove('st-flash'); void canvas.offsetWidth; canvas.classList.add('st-flash'); }
        }
      } catch (_e) {}
    }, 2500);
    voice.d.transcript = entries => {
      try { if (original) original(entries); } catch (_e) {}
      const said = (entries || []).filter(e => e.role === 'user').map(e => e.text).join(' ').trim();
      St.draft = (base ? base + ' ' : '') + said;
      const ta = root() && root().querySelector('[data-st-send] textarea');
      if (ta) ta.value = St.draft;
    };
    render();
    try { await voice.start(sid); } catch (e) { toast(errMsg(e)); stopLive(); }
  }
  async function stopLive(){
    const voice = window.synPulseVoice;
    const previous = St.live && St.live.previous;
    if (St.live) clearInterval(St.live.poll);
    if (voice && St.live) { voice.d.transcript = St.live.original; voice.d.tasks = St.live.originalTasks; try { voice.stop(); } catch (_e) {} }
    St.live = null; render();
    if (previous && typeof loadSession === 'function') {
      try { await loadSession(previous); } catch (_e) {}
      if (typeof switchPanel === 'function') await switchPanel('studio');
    }
  }

  function dictate(){
    const R = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!R) return;
    if (St.listening && St.rec) { St.rec.stop(); return; }
    const rec = new R();
    rec.lang = lang() === 'en' ? 'en-GB' : 'nl-NL'; rec.interimResults = true; rec.continuous = true;
    const base = (root().querySelector('[data-st-send] textarea') || {}).value || '';
    rec.onresult = ev => { let text = ''; for (const r of ev.results) text += r[0].transcript; St.draft = (base ? base + ' ' : '') + text; const ta = root().querySelector('[data-st-send] textarea'); if (ta) ta.value = St.draft; };
    rec.onend = () => { St.listening = false; St.rec = null; render(); };
    rec.onerror = () => { St.listening = false; St.rec = null; render(); };
    St.rec = rec; St.listening = true; rec.start(); render();
  }
  function bind(){
    const r = root();
    if (!r || r.dataset.stBound) return;
    r.dataset.stBound = '1';
    r.addEventListener('input', ev => { if (ev.target.matches('[data-st-send] textarea')) St.draft = ev.target.value; });
    r.addEventListener('change', async ev => {
      const el = ev.target;
      if (el.hasAttribute('data-st-team')) await save({ team: el.value });
      if (el.hasAttribute('data-st-title')) await save({ title: el.value });
    });
    r.addEventListener('submit', async ev => {
      if (!ev.target.hasAttribute('data-st-send')) return;
      ev.preventDefault();
      const text = String(new FormData(ev.target).get('input') || '').trim();
      const phase = St.doc.phase || 'discover';
      if (!text && phase !== 'playbook') { toast(w('need_input')); return; }
      await step(phase === 'design' ? 'design' : phase === 'playbook' ? 'playbook' : 'discover', text);
    });
    r.addEventListener('click', async ev => {
      const b = ev.target.closest('button');
      if (!b) return;
      if (b.dataset.stHubGo) { St.tab = b.dataset.stHubGo; St.doc = null; render(); return; }
      if (b.hasAttribute('data-st-conv-toggle')) { St.convOpen = !St.convOpen; try { localStorage.setItem('sp-studio-conv', St.convOpen ? '1' : '0'); } catch (_e) {} render(); return; }
      if (b.dataset.stTab) { St.tab = b.dataset.stTab; St.doc = null; if (St.tab === 'usecases') await loadList(); render(); return; }
      if (b.dataset.stOppview) { St.oppView = b.dataset.stOppview; render(); if (St.doc) await save({ ui_view: St.oppView }, true); return; }
      if (b.dataset.stBacklog || b.hasAttribute('data-st-backlog-all')) {
        const sols = allSolutions(St.doc).filter(s => b.dataset.stBacklog ? s.id === b.dataset.stBacklog : !St.backlogged.has(St.doc.id + ':' + s.id));
        for (const s of sols) {
          try { await post('/api/studio/backlog', { title: s.title, pain: s.opp.title, why: s.how, goal: s.opp.goal, impact: s.impact, effort: s.effort, building_block: s.building_block, team: St.doc.team || '', source_use_case: St.doc.id }); St.backlogged.add(St.doc.id + ':' + s.id); }
          catch (e) { toast(errMsg(e)); }
        }
        toast(w('in_backlog')); render(); return;
      }
      if (b.hasAttribute('data-st-make-pb')) {
        b.disabled = true;
        try { const pb = await post('/api/studio/playbook/draft', { use_case: St.doc.id }); St.doc = null; if (window.SPLibrary) await window.SPLibrary.openPlaybook(pb.id); }
        catch (e) { toast(errMsg(e)); }
        return;
      }
      if (b.hasAttribute('data-st-new')) {
        try { St.doc = await post('/api/studio/usecase', { team: St.presetTeam || '' }); St.presetTeam = ''; } catch (e) { toast(errMsg(e)); }
        render(); return;
      }
      if (b.dataset.stOpen) { await open(b.dataset.stOpen); return; }
      if (b.hasAttribute('data-st-back')) { if (St.live) stopLive(); St.doc = null; await loadList(); render(); return; }
      if (b.hasAttribute('data-st-delete')) { if (confirm(w('confirm_delete'))) { try { await post('/api/studio/delete', { id: St.doc.id }); } catch (e) { toast(errMsg(e)); } St.doc = null; await loadList(); render(); } return; }
      if (b.dataset.stPhase) { await save({ phase: b.dataset.stPhase }, true); render(); return; }
      if (b.dataset.stGoto) {
        if (b.dataset.stGoto === 'build' && St.doc.phase === 'playbook') await save({ components: collectComponents() }, true);
        await save({ phase: b.dataset.stGoto }, true); render(); return;
      }
      if (b.dataset.stTopic) { const ta = r.querySelector('[data-st-send] textarea'); if (ta) { ta.value = (ta.value ? ta.value + '\n' : '') + b.dataset.stTopic + ': '; ta.focus(); St.draft = ta.value; } return; }
      if (b.dataset.stSelect) { await save({ selected: b.dataset.stSelect }, true); render(); return; }
      if (b.hasAttribute('data-st-make-playbook')) { if (St.doc.phase !== 'playbook') await save({ phase: 'playbook' }, true); await step('playbook', St.draft); return; }
      if (b.hasAttribute('data-st-save-playbook')) { await save({ components: collectComponents() }); render(); return; }
      if (b.hasAttribute('data-st-build')) { if (!St.building) await runBuild(); return; }
      if (b.hasAttribute('data-st-mic')) { dictate(); return; }
      if (b.hasAttribute('data-st-live')) { await toggleLive(); return; }
      if (b.dataset.stOpenSession) { if (typeof switchPanel === 'function') await switchPanel('chat'); if (typeof loadSession === 'function') await loadSession(b.dataset.stOpenSession); return; }
      if (b.hasAttribute('data-st-chat')) {
        const summary = (St.doc.notes || []).filter(n => n.role === 'user').map(n => n.text).join(' ').slice(0, 600);
        if (typeof switchPanel === 'function') await switchPanel('chat');
        if (typeof newSession === 'function') await newSession(false);
        const box = $id('msg'); if (box) { box.value = w('chat_prompt', { t: St.doc.title || '', s: summary }); box.focus(); if (typeof autoResize === 'function') autoResize(); }
        return;
      }
      if (b.dataset.stNav) { if (typeof switchPanel === 'function') await switchPanel(b.dataset.stNav); return; }
    });
    r.addEventListener('change', ev => { if (ev.target.hasAttribute('data-st-include')) ev.target.closest('.st-comp').classList.toggle('off', !ev.target.checked); });
  }

  window.SPStudio = {
    openUseCase: async (id) => { St.tab = 'usecases'; if (typeof switchPanel === 'function') await switchPanel('studio'); await open(id); },
    setTab: (tab) => { St.tab = tab; St.doc = null; render(); },
    load: async () => { bind(); await Promise.all([loadList(), loadCounts()]); render(); },
    renderSide: async () => { if (St.list === null) await Promise.all([loadList(), loadCounts()]); renderSide(); },
    refreshCounts: async () => { await loadCounts(); renderSide(); },
    newForTeam: async (team) => { St.presetTeam = team || ''; St.doc = null; if (typeof switchPanel === 'function') await switchPanel('studio'); bind(); try { St.doc = await post('/api/studio/usecase', { team: St.presetTeam }); St.presetTeam = ''; } catch (e) { toast(errMsg(e)); } render(); }
  };
})();
