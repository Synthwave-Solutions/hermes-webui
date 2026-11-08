/* Studio: the personal intake ("About you") and the organisation intake (8 Nov 2026).

   Personal intake, six steps: role, work (describe your week and let the agent
   pull out the tasks), systems, which tasks AI may do or help with, how the
   agent should work with you plus a short AI check, and a summary. Saving
   writes one short entry into your user notes (the user profile the agent
   reads in every conversation) and keeps the full intake for Studio.

   Organisation intake, seven steps: welcome with the website (optional
   research), check what was found, structure, goals with a KPI, systems,
   rules for AI and data, and finish. It fills the organisation profile that
   every QuickScan reads. A draft is kept in this browser until saved. */
(function(){
  'use strict';
  const NL = {
    back: 'Terug', next: 'Volgende', skip: 'Overslaan', save_me: 'Opslaan in mijn profiel', save_org: 'Organisatieprofiel opslaan',
    me_title: 'Vertel de Super Agent wie je bent', me_intro: 'Zes korte stappen. De agent onthoudt een korte samenvatting in je gebruikersprofiel en stemt zijn antwoorden en voorstellen erop af. Je eigen notities blijven staan.',
    s_role: 'Je rol', s_work: 'Je werk', s_tools: 'Systemen', s_sort: 'Indelen', s_prefs: 'Voorkeuren', s_done: 'Samenvatting',
    title: 'Functie', team: 'Team', no_team: 'Geen team', seniority: 'Niveau', speciality: 'Specialisme', work_type: 'Waar je werkt',
    focus: 'Waar je je op richt (één per regel)', responsibilities: 'Verantwoordelijkheden (één per regel)',
    sen_junior: 'Junior', sen_medior: 'Medior', sen_senior: 'Senior', sen_lead: 'Teamlead', sen_management: 'Management',
    wt_office: 'Op kantoor', wt_hybrid: 'Hybride', wt_remote: 'Op afstand', wt_field: 'Op locatie',
    week: 'Beschrijf een gewone werkweek: wat doe je terugkerend, hoe vaak, hoe lang en in welke systemen?',
    week_ph: 'Bijvoorbeeld: elke maandag haal ik de openstaande posten uit Exact en bel ik klanten na, dat kost twee uur...',
    extract: 'Haal taken eruit', extracting: 'De agent leest mee…', add_task: 'Taak toevoegen', task: 'Taak', cadence: 'Hoe vaak', minutes: 'Minuten per keer', remove: 'Verwijderen',
    c_daily: 'Dagelijks', c_weekly: 'Wekelijks', c_monthly: 'Maandelijks', c_adhoc: 'Af en toe',
    tools_intro: 'Welke systemen gebruik je? Kies of voeg toe.', add_tool: 'Systeem toevoegen',
    sort_intro: 'Wat mag de Super Agent doen? Kies per taak.', k_automate: 'AI doet het', k_assist: 'AI helpt mij', k_human: 'Blijft bij mij', no_tasks: 'Nog geen taken; ga terug naar Je werk.',
    p_language: 'Taal', p_tone: 'Toon', p_length: 'Lengte', p_format: 'Vorm', l_nl: 'Nederlands', l_en: 'Engels',
    t_informal: 'Informeel (je)', t_formal: 'Formeel (u)', len_short: 'Kort', len_detailed: 'Uitgebreid', f_bullets: 'Opsommingen', f_prose: 'Lopende tekst',
    hours: 'Werktijden (optioneel)', hours_ph: 'Bijvoorbeeld: ma tot do 8 tot 17 uur', never: 'Wat moet de agent nooit doen?', never_ph: 'Bijvoorbeeld: nooit zelf mails versturen',
    notes: 'Verder nog iets? (optioneel)', ai_self: 'Je ervaring met AI', ai_beginner: 'Beginner', ai_regular: 'Gebruik het regelmatig', ai_advanced: 'Ervaren',
    quiz: 'Korte check (optioneel)',
    q1: 'Wat is een taalmodel?', q1a: 'Een grote database met antwoorden', q1b: 'AI die tekst begrijpt en maakt op basis van patronen', q1c: 'Een programma dat alleen zoekt op internet',
    q2: 'Een AI-antwoord klinkt zeker. Wat doe je?', q2a: 'Overnemen, het klinkt goed', q2b: 'Feiten en cijfers controleren voor ik het gebruik', q2c: 'Het nog een keer vragen tot het hetzelfde zegt',
    q3: 'Wat geef je liever niet zomaar aan een AI-dienst buiten jullie eigen omgeving?', q3a: 'Een openbare nieuwsbrief', q3b: 'Klantgegevens en persoonsgegevens', q3c: 'Een vraag over spelling',
    score: 'Score', saved_me: 'Opgeslagen. Dit onthoudt de agent over jou:', notes_room: 'Ruimte in je gebruikersprofiel', to_backlog: 'Zet taken die AI mag doen in de backlog', in_backlog: 'In de backlog gezet', start_uc: 'Start een use case',
    org_title: 'Organisatie-intake', org_intro: 'Zeven stappen om de Super Agent jullie organisatie te leren kennen. Alles wat je invult gaat mee als context in elke QuickScan, elk ontwerp en elk bouwplan.',
    o_welcome: 'Welkom', o_check: 'Controleren', o_structure: 'Structuur', o_goals: 'Doelen', o_systems: 'Systemen', o_rules: 'Beleid', o_done: 'Afronden',
    name: 'Naam van de organisatie', website: 'Website', research: 'Onderzoek de website', researching: 'De agent leest de website…', research_done: 'Gevonden op de website; controleer het in de volgende stap.',
    sector: 'Sector', size: 'Omvang', description: 'Wat jullie doen', products: 'Producten en diensten (één per regel)', customers: 'Klanten',
    structure_intro: 'Zo is de organisatie nu ingedeeld. Pas afdelingen en teams aan bij Teams beheren.', manage_teams: 'Teams beheren', no_structure: 'Nog geen afdelingen of teams.',
    goals_intro: 'Wat willen jullie de komende tijd bereiken? Hooguit drie doelen, elk met een meetbare KPI.', goal: 'Doel', kpi: 'Hoe meet je het', goal_ph: 'Bijvoorbeeld: offertes sneller de deur uit', kpi_ph: 'Bijvoorbeeld: doorlooptijd van 3 naar 1 dag',
    systems_intro: 'Met welke systemen werkt de organisatie?',
    rules_intro: 'Welke regels gelden voor AI en data? Vink aan wat past en vul aan.', custom_rules: 'Eigen regels en beleid',
    r1: 'Een mens controleert alles wat naar klanten of externen gaat.', r2: 'Geen persoonsgegevens naar AI-diensten buiten de EU.', r3: 'Vertrouwelijke stukken blijven in onze eigen omgeving.',
    r4: 'Betalen, boeken en andere financiële handelingen doet altijd een mens.', r5: 'Bij twijfel vraagt de agent het eerst na.', r6: 'Wachtwoorden en inloggegevens nooit in prompts of notities.',
    done_intro: 'Zo leest de agent jullie organisatie. Kies Opslaan om het profiel te bewaren.', saved_org: 'Organisatieprofiel opgeslagen',
    redo_org: 'Intake opnieuw doen', view_profile: 'Profiel bekijken', draft_kept: 'Je concept blijft in deze browser bewaard tot je opslaat.',
    hint_me: 'Vertel de Super Agent in drie minuten wie je bent en wat je doet: dan passen antwoorden en voorstellen beter bij jou.', open_me: 'Start de intake',
    r_private: 'Alleen openbare websites kunnen worden onderzocht.', r_unreachable: 'De website was niet bereikbaar.', r_no_site: 'Vul eerst de website in.'
  };
  const EN = {
    back: 'Back', next: 'Next', skip: 'Skip', save_me: 'Save to my profile', save_org: 'Save organisation profile',
    me_title: 'Tell the Super Agent who you are', me_intro: 'Six short steps. The agent keeps a short summary in your user profile and tunes its answers and proposals to it. Your own notes stay.',
    s_role: 'Your role', s_work: 'Your work', s_tools: 'Systems', s_sort: 'Sort', s_prefs: 'Preferences', s_done: 'Summary',
    title: 'Job title', team: 'Team', no_team: 'No team', seniority: 'Level', speciality: 'Speciality', work_type: 'Where you work',
    focus: 'What you focus on (one per line)', responsibilities: 'Responsibilities (one per line)',
    sen_junior: 'Junior', sen_medior: 'Medior', sen_senior: 'Senior', sen_lead: 'Team lead', sen_management: 'Management',
    wt_office: 'At the office', wt_hybrid: 'Hybrid', wt_remote: 'Remote', wt_field: 'On site',
    week: 'Describe an ordinary working week: what do you do repeatedly, how often, how long and in which systems?',
    week_ph: 'For example: every Monday I pull the open items from Exact and call customers, which takes two hours...',
    extract: 'Find the tasks', extracting: 'The agent is reading…', add_task: 'Add task', task: 'Task', cadence: 'How often', minutes: 'Minutes per run', remove: 'Remove',
    c_daily: 'Daily', c_weekly: 'Weekly', c_monthly: 'Monthly', c_adhoc: 'Now and then',
    tools_intro: 'Which systems do you use? Choose or add.', add_tool: 'Add system',
    sort_intro: 'What may the Super Agent do? Choose per task.', k_automate: 'AI does it', k_assist: 'AI helps me', k_human: 'Stays with me', no_tasks: 'No tasks yet; go back to Your work.',
    p_language: 'Language', p_tone: 'Tone', p_length: 'Length', p_format: 'Form', l_nl: 'Dutch', l_en: 'English',
    t_informal: 'Informal', t_formal: 'Formal', len_short: 'Short', len_detailed: 'Detailed', f_bullets: 'Bullets', f_prose: 'Prose',
    hours: 'Working hours (optional)', hours_ph: 'For example: Mon to Thu 8 to 17', never: 'What must the agent never do?', never_ph: 'For example: never send mails itself',
    notes: 'Anything else? (optional)', ai_self: 'Your experience with AI', ai_beginner: 'Beginner', ai_regular: 'Use it regularly', ai_advanced: 'Experienced',
    quiz: 'Short check (optional)',
    q1: 'What is a language model?', q1a: 'A big database of answers', q1b: 'AI that understands and writes text from patterns', q1c: 'A program that only searches the internet',
    q2: 'An AI answer sounds certain. What do you do?', q2a: 'Use it, it sounds right', q2b: 'Check facts and figures before using it', q2c: 'Ask again until it says the same',
    q3: 'What do you rather not give to an AI service outside your own environment?', q3a: 'A public newsletter', q3b: 'Customer and personal data', q3c: 'A spelling question',
    score: 'Score', saved_me: 'Saved. This is what the agent remembers about you:', notes_room: 'Room in your user profile', to_backlog: 'Put tasks AI may do on the backlog', in_backlog: 'Put on the backlog', start_uc: 'Start a use case',
    org_title: 'Organisation intake', org_intro: 'Seven steps for the Super Agent to get to know your organisation. Everything you fill in goes along as context in every QuickScan, design and build plan.',
    o_welcome: 'Welcome', o_check: 'Check', o_structure: 'Structure', o_goals: 'Goals', o_systems: 'Systems', o_rules: 'Policy', o_done: 'Finish',
    name: 'Organisation name', website: 'Website', research: 'Research the website', researching: 'The agent is reading the website…', research_done: 'Found on the website; check it in the next step.',
    sector: 'Sector', size: 'Size', description: 'What you do', products: 'Products and services (one per line)', customers: 'Customers',
    structure_intro: 'This is how the organisation is set up now. Change departments and teams under Manage teams.', manage_teams: 'Manage teams', no_structure: 'No departments or teams yet.',
    goals_intro: 'What do you want to achieve in the coming period? At most three goals, each with a measurable KPI.', goal: 'Goal', kpi: 'How you measure it', goal_ph: 'For example: quotes out faster', kpi_ph: 'For example: lead time from 3 to 1 day',
    systems_intro: 'Which systems does the organisation use?',
    rules_intro: 'Which rules apply to AI and data? Tick what fits and add your own.', custom_rules: 'Own rules and policy',
    r1: 'A person checks everything that goes to customers or outsiders.', r2: 'No personal data to AI services outside the EU.', r3: 'Confidential documents stay in our own environment.',
    r4: 'Payments, bookings and other financial actions are always done by a person.', r5: 'When in doubt, the agent asks first.', r6: 'Never passwords or credentials in prompts or notes.',
    done_intro: 'This is how the agent reads your organisation. Choose Save to keep the profile.', saved_org: 'Organisation profile saved',
    redo_org: 'Do the intake again', view_profile: 'View profile', draft_kept: 'Your draft is kept in this browser until you save.',
    hint_me: 'Tell the Super Agent in three minutes who you are and what you do, so answers and proposals fit you better.', open_me: 'Start the intake',
    r_private: 'Only public websites can be researched.', r_unreachable: 'The website could not be reached.', r_no_site: 'Fill in the website first.'
  };
  const lang = () => ((document.documentElement.lang || 'nl').toLowerCase().startsWith('en') ? 'en' : 'nl');
  const w = k => (lang() === 'en' ? EN : NL)[k] || NL[k] || k;
  const H = v => (typeof esc === 'function' ? esc(String(v ?? '')) : String(v ?? ''));
  const toast = m => { if (typeof showToast === 'function') showToast(m); };
  const call = (p, o) => api(p, Object.assign({ timeoutToast: false }, o || {}));
  const post = (p, b) => call(p, { method: 'POST', body: JSON.stringify(b) });
  const errMsg = e => (e && e.message) || String(e);
  const lines = v => String(v || '').split('\n').map(x => x.trim()).filter(Boolean);
  const csv = v => String(v || '').split(',').map(x => x.trim()).filter(Boolean);

  const ME_STEPS = ['s_role', 's_work', 's_tools', 's_sort', 's_prefs', 's_done'];
  const ORG_STEPS = ['o_welcome', 'o_check', 'o_structure', 'o_goals', 'o_systems', 'o_rules', 'o_done'];
  const COMMON_TOOLS = ['Outlook', 'Excel', 'Word', 'Teams', 'Google Workspace', 'SharePoint', 'Exact', 'AFAS', 'Twinfield', 'Salesforce', 'HubSpot', 'Notion', 'Slack', 'Jira', 'Productive'];
  const RULES = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6'];
  const QUIZ = [['q1', 'b'], ['q2', 'b'], ['q3', 'b']];

  const I = { body: null, kind: '', step: 0, d: null, ctx: null, busy: false, saved: null, wizard: false };
  const draftKey = () => 'sp-intake-' + I.kind;
  function keepDraft(){ try { localStorage.setItem(draftKey(), JSON.stringify({ step: I.step, d: I.d })); } catch (_e) {} }
  function dropDraft(){ try { localStorage.removeItem(draftKey()); } catch (_e) {} }

  function seg(name, options, value, prefix){
    return `<div class="om-seg in-seg" role="radiogroup">${options.map(o => `<button type="button" role="radio" aria-pressed="${value === o}" aria-checked="${value === o}" data-in-set="${H(name)}" data-in-val="${H(o)}">${H(w((prefix || '') + o))}</button>`).join('')}</div>`;
  }
  function field(label, html){ return `<label class="om-field in-field">${H(label)}${html}</label>`; }
  function stepper(steps){
    return `<ol class="st-stepper in-stepper" data-tour="studio-intake-steps">${steps.map((s, i) => `<li><button type="button" data-in-go="${i}" aria-current="${i === I.step ? 'step' : 'false'}" class="${i < I.step ? 'done' : ''}"><span>${i + 1}</span>${H(w(s))}</button></li>`).join('')}</ol>`;
  }
  function nav(steps, saveLabel){
    const last = I.step === steps.length - 1;
    return `<div class="in-nav">${I.step ? `<button type="button" class="sm-btn" data-in-back>${H(w('back'))}</button>` : '<span></span>'}
      <span class="om-small om-muted">${H(w('draft_kept'))}</span>
      ${last ? `<button type="button" class="sm-btn primary" data-in-save ${I.busy ? 'disabled' : ''}>${H(saveLabel)}</button>` : `<button type="button" class="sm-btn primary" data-in-next>${H(w('next'))}</button>`}</div>`;
  }

  // ── Personal ──────────────────────────────────────────────────────────────
  function meStep(){
    const d = I.d, r = d.role, p = d.prefs;
    if (I.step === 0) return `<div class="in-grid">
        ${field(w('title'), `<input data-in-f="role.title" value="${H(r.title)}" maxlength="100">`)}
        ${field(w('team'), `<select data-in-f="role.team"><option value="">${H(w('no_team'))}</option>${(I.ctx.teams || []).map(t => `<option value="${H(t.key)}" ${r.team === t.key ? 'selected' : ''}>${H(t.name)}</option>`).join('')}</select>`)}
        ${field(w('speciality'), `<input data-in-f="role.speciality" value="${H(r.speciality)}" maxlength="100">`)}
        <div class="om-field in-field">${H(w('seniority'))}${seg('role.seniority', ['junior', 'medior', 'senior', 'lead', 'management'], r.seniority, 'sen_')}</div>
        <div class="om-field in-field wide">${H(w('work_type'))}${seg('role.work_type', ['office', 'hybrid', 'remote', 'field'], r.work_type, 'wt_')}</div>
        ${field(w('focus'), `<textarea data-in-f="role.focus" data-in-lines rows="3">${H((r.focus || []).join('\n'))}</textarea>`)}
        ${field(w('responsibilities'), `<textarea data-in-f="role.responsibilities" data-in-lines rows="3">${H((r.responsibilities || []).join('\n'))}</textarea>`)}
      </div>`;
    if (I.step === 1) return `<div class="in-work">
        ${field(w('week'), `<textarea data-in-f="week" rows="5" placeholder="${H(w('week_ph'))}">${H(d.week || '')}</textarea>`)}
        <div class="om-value-actions"><button type="button" class="sm-btn" data-in-extract ${I.busy ? 'disabled' : ''}>${H(I.busy ? w('extracting') : w('extract'))}</button></div>
        <div class="in-tasks" data-tour="studio-intake-tasks">${(d.tasks || []).map((t, i) => `<div class="in-task">
            <input data-in-task="${i}:name" value="${H(t.name)}" aria-label="${H(w('task'))}" placeholder="${H(w('task'))}">
            <select data-in-task="${i}:cadence" aria-label="${H(w('cadence'))}">${['daily', 'weekly', 'monthly', 'adhoc'].map(c => `<option value="${c}" ${t.cadence === c ? 'selected' : ''}>${H(w('c_' + c))}</option>`).join('')}</select>
            <input type="number" min="0" max="2400" data-in-task="${i}:minutes" value="${H(t.minutes || '')}" aria-label="${H(w('minutes'))}" placeholder="${H(w('minutes'))}">
            <button type="button" class="sm-btn pr-quiet" data-in-task-remove="${i}" aria-label="${H(w('remove'))}">✕</button></div>`).join('')}
          <button type="button" class="sm-btn" data-in-task-add>＋ ${H(w('add_task'))}</button></div></div>`;
    if (I.step === 2) {
      const pool = [...new Set([...(I.ctx.org_systems || []), ...COMMON_TOOLS, ...(d.tools || []), ...(d.tasks || []).flatMap(t => t.tools || [])])];
      return `<p class="om-intro">${H(w('tools_intro'))}</p><div class="in-chips">${pool.map(x => `<button type="button" class="in-chip" aria-pressed="${(d.tools || []).includes(x)}" data-in-tool="${H(x)}">${H(x)}</button>`).join('')}</div>
        <form class="om-inline-form in-add" data-in-add-tool><input name="tool" maxlength="40" placeholder="${H(w('add_tool'))}"><button type="submit" class="sm-btn">＋</button></form>`;
    }
    if (I.step === 3) return (d.tasks || []).length ? `<p class="om-intro">${H(w('sort_intro'))}</p><div class="in-sort" data-tour="studio-intake-sort">${d.tasks.map((t, i) => `<div class="in-sort-row"><span><strong>${H(t.name)}</strong><span class="om-small om-muted"> · ${H(w('c_' + t.cadence))}${t.minutes ? ' · ' + t.minutes + ' min' : ''}</span></span>${seg('tasks.' + i + '.kind', ['automate', 'assist', 'human'], t.kind, 'k_')}</div>`).join('')}</div>` : `<p class="om-muted">${H(w('no_tasks'))}</p>`;
    if (I.step === 4) return `<div class="in-grid">
        <div class="om-field in-field">${H(w('p_language'))}${seg('prefs.language', ['nl', 'en'], p.language, 'l_')}</div>
        <div class="om-field in-field">${H(w('p_tone'))}${seg('prefs.tone', ['informal', 'formal'], p.tone, 't_')}</div>
        <div class="om-field in-field">${H(w('p_length'))}${seg('prefs.length', ['short', 'detailed'], p.length, 'len_')}</div>
        <div class="om-field in-field">${H(w('p_format'))}${seg('prefs.format', ['bullets', 'prose'], p.format, 'f_')}</div>
        ${field(w('hours'), `<input data-in-f="prefs.hours" value="${H(p.hours)}" maxlength="80" placeholder="${H(w('hours_ph'))}">`)}
        ${field(w('never'), `<input data-in-f="prefs.never" value="${H(p.never)}" maxlength="300" placeholder="${H(w('never_ph'))}">`)}
        ${field(w('notes'), `<textarea data-in-f="prefs.notes" rows="2" maxlength="300">${H(p.notes)}</textarea>`)}
        <div class="om-field in-field wide">${H(w('ai_self'))}${seg('literacy.self', ['beginner', 'regular', 'advanced'], d.literacy.self, 'ai_')}</div>
        <details class="in-quiz wide" ${d.quiz && Object.keys(d.quiz).length ? 'open' : ''}><summary>${H(w('quiz'))}</summary>${QUIZ.map(([q]) => `<fieldset><legend>${H(w(q))}</legend>${['a', 'b', 'c'].map(o => `<label><input type="radio" name="${q}" value="${o}" data-in-quiz="${q}" ${(d.quiz || {})[q] === o ? 'checked' : ''}> ${H(w(q + o))}</label>`).join('')}</fieldset>`).join('')}</details>
      </div>`;
    const teamName = ((I.ctx.teams || []).find(t => t.key === d.role.team) || {}).name || '';
    const rows = [[w('title'), [d.role.title, teamName, d.role.seniority && w('sen_' + d.role.seniority)].filter(Boolean).join(' · ')],
                  [w('focus'), (d.role.focus || []).join('; ')], [w('s_work'), (d.tasks || []).map(t => `${t.name} (${w('c_' + t.cadence)}${t.kind ? ', ' + w('k_' + t.kind) : ''})`).join('; ')],
                  [w('s_tools'), (d.tools || []).join(', ')], [w('s_prefs'), [p.language && w('l_' + p.language), p.tone && w('t_' + p.tone), p.length && w('len_' + p.length), p.format && w('f_' + p.format)].filter(Boolean).join(', ')],
                  [w('never'), p.never], [w('ai_self'), [d.literacy.self && w('ai_' + d.literacy.self), d.literacy.answered ? w('score') + ' ' + d.literacy.score + '/3' : ''].filter(Boolean).join(' · ')]].filter(r => r[1]);
    return `<div class="pf-read in-summary">${rows.map(([k, v]) => `<div class="pf-row"><span class="om-small om-muted">${H(k)}</span><span>${H(v)}</span></div>`).join('')}</div>
      ${I.saved ? `<div class="om-card in-saved" data-tour="studio-intake-note"><strong>${H(w('saved_me'))}</strong><p>${H(I.saved.note)}</p>
        <div class="om-bar" title="${H(w('notes_room'))}"><span style="width:${Math.min(100, Math.round(100 * I.saved.notes_used / I.saved.notes_limit))}%"></span></div><span class="om-small om-muted">${H(w('notes_room'))}: ${I.saved.notes_used} / ${I.saved.notes_limit}</span>
        ${(d.tasks || []).some(t => t.kind === 'automate' || t.kind === 'assist') ? `<div class="om-value-actions"><button type="button" class="sm-btn" data-in-backlog>${H(w('to_backlog'))}</button></div>` : ''}</div>` : ''}`;
  }

  // ── Organisation ──────────────────────────────────────────────────────────
  function orgStep(){
    const d = I.d;
    if (I.step === 0) return `<div class="in-grid">${field(w('name'), `<input data-in-f="name" value="${H(d.name)}" maxlength="120">`)}
        ${field(w('website'), `<input data-in-f="website" value="${H(d.website)}" maxlength="200" inputmode="url" placeholder="https://">`)}</div>
      <div class="om-value-actions"><button type="button" class="sm-btn" data-in-research ${I.busy ? 'disabled' : ''}>${H(I.busy ? w('researching') : w('research'))}</button>${d._researched ? `<span class="om-small om-muted">${H(w('research_done'))}</span>` : ''}</div>`;
    if (I.step === 1) return `<div class="in-grid">${field(w('sector'), `<input data-in-f="sector" value="${H(d.sector)}" maxlength="120">`)}${field(w('size'), `<input data-in-f="size" value="${H(d.size)}" maxlength="80">`)}
        ${field(w('description'), `<textarea data-in-f="description" rows="3" maxlength="900">${H(d.description)}</textarea>`)}
        ${field(w('products'), `<textarea data-in-f="products" data-in-lines rows="3">${H((d.products || []).join('\n'))}</textarea>`)}
        ${field(w('customers'), `<input data-in-f="customers" value="${H(d.customers)}" maxlength="400">`)}</div>`;
    if (I.step === 2) {
      const depts = (I.ctx.structure && I.ctx.structure.departments) || [];
      return `<p class="om-intro">${H(w('structure_intro'))}</p>${depts.length ? `<div class="in-structure">${depts.map(x => `<div class="om-card"><strong>${H(x.name)}</strong><div class="om-chips">${(x.teams || []).map(t => `<span class="om-chip">${H(t)}</span>`).join('')}</div></div>`).join('')}</div>` : `<p class="om-muted">${H(w('no_structure'))}</p>`}
        ${I.ctx.can_manage ? `<div class="om-value-actions"><button type="button" class="sm-btn" data-in-teams>${H(w('manage_teams'))}</button></div>` : ''}`;
    }
    if (I.step === 3) {
      const goals = (d._goals || []).concat([{}, {}, {}]).slice(0, 3);
      return `<p class="om-intro">${H(w('goals_intro'))}</p><div class="in-goals">${goals.map((g, i) => `<div class="in-goal"><span class="st-num">${i + 1}</span>
          ${field(w('goal'), `<input data-in-goal="${i}:goal" value="${H(g.goal || '')}" maxlength="140" placeholder="${H(w('goal_ph'))}">`)}
          ${field(w('kpi'), `<input data-in-goal="${i}:kpi" value="${H(g.kpi || '')}" maxlength="100" placeholder="${H(w('kpi_ph'))}">`)}</div>`).join('')}</div>`;
    }
    if (I.step === 4) {
      const pool = [...new Set([...COMMON_TOOLS, ...(d.systems || [])])];
      return `<p class="om-intro">${H(w('systems_intro'))}</p><div class="in-chips">${pool.map(x => `<button type="button" class="in-chip" aria-pressed="${(d.systems || []).includes(x)}" data-in-system="${H(x)}">${H(x)}</button>`).join('')}</div>
        <form class="om-inline-form in-add" data-in-add-system><input name="tool" maxlength="60" placeholder="${H(w('add_tool'))}"><button type="submit" class="sm-btn">＋</button></form>`;
    }
    if (I.step === 5) return `<p class="om-intro">${H(w('rules_intro'))}</p><div class="in-rules" data-tour="studio-intake-rules">${RULES.map(r => `<label class="in-rule"><input type="checkbox" data-in-rule="${r}" ${(d.rules || []).includes(w(r)) ? 'checked' : ''}> ${H(w(r))}</label>`).join('')}</div>
      ${field(w('custom_rules'), `<textarea data-in-f="policy" rows="3" maxlength="900">${H(d.policy)}</textarea>`)}`;
    return `<p class="om-intro">${H(w('done_intro'))}</p><pre class="in-context">${H(orgPreview(d))}</pre>`;
  }
  function orgGoalsToList(d){ return (d._goals || []).filter(g => g.goal).map(g => g.kpi ? `${g.goal} (KPI: ${g.kpi})` : g.goal); }
  function orgPreview(d){
    const head = [d.sector, d.size].filter(Boolean).join(', ');
    return [d.name ? d.name + (head ? ` (${head})` : '') : head, d.description, (d.products || []).length ? 'Producten en diensten: ' + d.products.join('; ') : '',
            d.customers ? 'Klanten: ' + d.customers : '', orgGoalsToList(d).length ? 'Doelen: ' + orgGoalsToList(d).join('; ') : '',
            (d.systems || []).length ? 'Systemen in gebruik: ' + d.systems.join(', ') : '', (d.rules || []).length ? 'Regels voor AI: ' + d.rules.join('; ') : '',
            d.policy ? 'Beleid voor AI en data: ' + d.policy : ''].filter(Boolean).join('\n');
  }

  // ── Render and wiring ─────────────────────────────────────────────────────
  function paint(){
    const steps = I.kind === 'me' ? ME_STEPS : ORG_STEPS;
    I.body.innerHTML = `<div class="in-wrap" data-tour="studio-intake"><div class="in-head"><h3>${H(w(I.kind === 'me' ? 'me_title' : 'org_title'))}</h3><p class="om-intro">${H(w(I.kind === 'me' ? 'me_intro' : 'org_intro'))}</p></div>
      ${stepper(steps)}<section class="om-card in-step">${I.kind === 'me' ? meStep() : orgStep()}</section>${nav(steps, w(I.kind === 'me' ? 'save_me' : 'save_org'))}</div>`;
  }
  function setPath(obj, path, val){ const k = path.split('.'); let o = obj; while (k.length > 1) { const x = k.shift(); o = o[x] = o[x] || {}; } o[k[0]] = val; }
  function collect(){
    if (!I.body) return;
    I.body.querySelectorAll('[data-in-f]').forEach(el => setPath(I.d, el.dataset.inF, el.hasAttribute('data-in-lines') ? lines(el.value) : el.value));
    I.body.querySelectorAll('[data-in-task]').forEach(el => { const [i, k] = el.dataset.inTask.split(':'); if (I.d.tasks[i]) I.d.tasks[i][k] = k === 'minutes' ? Number(el.value || 0) : el.value; });
    const goals = I.d._goals || [];
    I.body.querySelectorAll('[data-in-goal]').forEach(el => { const [i, k] = el.dataset.inGoal.split(':'); goals[i] = goals[i] || {}; goals[i][k] = el.value.trim(); });
    if (I.body.querySelector('[data-in-goal]')) I.d._goals = goals.filter(g => g && (g.goal || g.kpi));
    if (I.kind === 'org' && I.body.querySelector('[data-in-rule]')) I.d.rules = [...I.body.querySelectorAll('[data-in-rule]:checked')].map(el => w(el.dataset.inRule));
    keepDraft();
  }
  async function saveMe(){
    const d = I.d;
    const score = QUIZ.filter(([q, a]) => (d.quiz || {})[q] === a).length;
    d.literacy = Object.assign({}, d.literacy, { score, answered: !!(d.quiz && Object.keys(d.quiz).length) });
    I.busy = true; paint();
    try {
      I.saved = await post('/api/studio/profile', Object.assign({ op: 'me' }, { role: d.role, tasks: d.tasks, tools: d.tools, prefs: d.prefs, literacy: d.literacy }));
      dropDraft(); toast(w('saved_me').split('.')[0] + '.');
      if (window.SPStudio && window.SPStudio.refreshCounts) window.SPStudio.refreshCounts();
    } catch (e) { toast(errMsg(e)); }
    I.busy = false; paint();
  }
  async function saveOrg(){
    const d = I.d;
    const body = { name: d.name, website: d.website, sector: d.sector, size: d.size, description: d.description, products: d.products, customers: d.customers,
                   goals: orgGoalsToList(d), systems: d.systems, rules: d.rules, policy: d.policy };
    I.busy = true; paint();
    try { await post('/api/studio/profile', body); dropDraft(); toast(w('saved_org')); I.wizard = false;
      if (window.SPStudio && window.SPStudio.refreshCounts) await window.SPStudio.refreshCounts();
      I.busy = false; return render(I.body, 'org'); }
    catch (e) { toast(errMsg(e)); }
    I.busy = false; paint();
  }
  function bind(root){
    if (!root || root.dataset.inBound) return;
    root.dataset.inBound = '1';
    root.addEventListener('change', ev => {
      if (!I.body || !I.body.contains(ev.target)) return;
      if (ev.target.dataset.inQuiz) { I.d.quiz = I.d.quiz || {}; I.d.quiz[ev.target.dataset.inQuiz] = ev.target.value; keepDraft(); }
    });
    root.addEventListener('submit', ev => {
      const f = ev.target; if (!I.body || !I.body.contains(f)) return;
      if (f.hasAttribute('data-in-add-tool') || f.hasAttribute('data-in-add-system')) {
        ev.preventDefault(); collect();
        const v = String(new FormData(f).get('tool') || '').trim(); if (!v) return;
        const key = f.hasAttribute('data-in-add-tool') ? 'tools' : 'systems';
        I.d[key] = [...new Set([...(I.d[key] || []), v])]; keepDraft(); paint();
      }
    });
    root.addEventListener('click', async ev => {
      const b = ev.target.closest('button'); if (!b || !I.body || !I.body.contains(b)) return;
      const steps = I.kind === 'me' ? ME_STEPS : ORG_STEPS;
      if (b.dataset.inGo !== undefined) { collect(); I.step = Number(b.dataset.inGo); keepDraft(); paint(); return; }
      if (b.hasAttribute('data-in-next')) { collect(); I.step = Math.min(steps.length - 1, I.step + 1); keepDraft(); paint(); I.body.scrollIntoView({ block: 'start' }); return; }
      if (b.hasAttribute('data-in-back')) { collect(); I.step = Math.max(0, I.step - 1); keepDraft(); paint(); return; }
      if (b.dataset.inSet) { collect(); const cur = b.dataset.inSet.split('.').reduce((o, k) => (o || {})[k], I.d); setPath(I.d, b.dataset.inSet, cur === b.dataset.inVal ? '' : b.dataset.inVal); keepDraft(); paint(); return; }
      if (b.dataset.inTool) { collect(); const t = new Set(I.d.tools || []); t.has(b.dataset.inTool) ? t.delete(b.dataset.inTool) : t.add(b.dataset.inTool); I.d.tools = [...t]; keepDraft(); paint(); return; }
      if (b.dataset.inSystem) { collect(); const t = new Set(I.d.systems || []); t.has(b.dataset.inSystem) ? t.delete(b.dataset.inSystem) : t.add(b.dataset.inSystem); I.d.systems = [...t]; keepDraft(); paint(); return; }
      if (b.hasAttribute('data-in-task-add')) { collect(); I.d.tasks.push({ name: '', cadence: 'weekly', minutes: 0, tools: [], kind: '' }); paint(); const el = I.body.querySelector(`[data-in-task="${I.d.tasks.length - 1}:name"]`); if (el) el.focus(); return; }
      if (b.dataset.inTaskRemove !== undefined) { collect(); I.d.tasks.splice(Number(b.dataset.inTaskRemove), 1); keepDraft(); paint(); return; }
      if (b.hasAttribute('data-in-extract')) {
        collect(); I.busy = true; paint();
        try { const got = (await post('/api/studio/profile', { op: 'me_extract', text: I.d.week || '' })).tasks || [];
          const have = new Set((I.d.tasks || []).map(t => t.name.toLowerCase())); I.d.tasks = (I.d.tasks || []).concat(got.filter(t => !have.has(t.name.toLowerCase()))); }
        catch (e) { toast(errMsg(e)); }
        I.busy = false; keepDraft(); paint(); return;
      }
      if (b.hasAttribute('data-in-research')) {
        collect(); I.busy = true; paint();
        try { const r = await post('/api/studio/profile', { op: 'research', url: I.d.website || '' }); const pr = r.proposal || {};
          for (const k of ['name', 'website', 'sector', 'size', 'description', 'customers']) if (!I.d[k] && pr[k]) I.d[k] = pr[k];
          for (const k of ['products', 'systems']) if (!(I.d[k] || []).length && (pr[k] || []).length) I.d[k] = pr[k];
          if (!(I.d._goals || []).length && (pr.goals || []).length) I.d._goals = pr.goals.slice(0, 3).map(g => ({ goal: g, kpi: '' }));
          I.d._researched = true; }
        catch (e) { const m = errMsg(e); toast(/public/i.test(m) ? w('r_private') : /reached|answered/i.test(m) ? w('r_unreachable') : /website first/i.test(m) ? w('r_no_site') : m); }
        I.busy = false; keepDraft(); paint(); return;
      }
      if (b.hasAttribute('data-in-teams')) { collect(); if (window.SPOrg && window.SPOrg.show) await window.SPOrg.show('manage'); return; }
      if (b.hasAttribute('data-in-save')) { collect(); return I.kind === 'me' ? saveMe() : saveOrg(); }
      if (b.hasAttribute('data-in-backlog')) {
        const team = I.d.role.team || '';
        let n = 0;
        for (const t of I.d.tasks || []) {
          if (t.kind !== 'automate' && t.kind !== 'assist') continue;
          try { await post('/api/studio/backlog', { title: t.name, pain: `${w('c_' + t.cadence)}${t.minutes ? ', ' + t.minutes + ' min' : ''}`, team, building_block: t.kind === 'automate' ? 'task' : 'skill', impact: 3, effort: 2 }); n++; }
          catch (e) { toast(errMsg(e)); }
        }
        b.disabled = true; b.textContent = w('in_backlog') + ` (${n})`;
        if (window.SPStudio && window.SPStudio.refreshCounts) window.SPStudio.refreshCounts();
      }
    });
  }
  async function render(body, kind){
    I.body = body; I.kind = kind; I.saved = null; bind(body.closest('#mainStudio'));
    body.innerHTML = '<div class="om-skeleton"></div><div class="om-skeleton"></div>';
    let draft = null; try { draft = JSON.parse(localStorage.getItem('sp-intake-' + kind) || 'null'); } catch (_e) {}
    if (kind === 'me') {
      let me = {}; try { me = await call('/api/studio/profile?who=me'); } catch (e) { toast(errMsg(e)); }
      I.ctx = me;
      const base = { role: Object.assign({ title: '', team: (me.my_teams || [])[0] || '', speciality: '', seniority: '', work_type: '', focus: [], responsibilities: [] }, me.role || {}),
                     tasks: me.tasks || [], tools: me.tools || [], prefs: Object.assign({ language: '', tone: '', length: '', format: '', hours: '', never: '', notes: '' }, me.prefs || {}),
                     literacy: Object.assign({ self: '', score: 0, answered: false }, me.literacy || {}), quiz: {}, week: '' };
      I.d = draft && draft.d ? Object.assign(base, draft.d) : base; I.step = draft ? draft.step || 0 : (me.updated_at ? ME_STEPS.length - 1 : 0);
      if (me.updated_at && !draft) I.saved = { note: me.note, notes_used: me.notes_used, notes_limit: me.notes_limit };
      paint(); return;
    }
    let prof = {}; try { prof = await call('/api/studio/profile'); } catch (e) { toast(errMsg(e)); }
    const empty = !prof.context;
    if (!prof.editable || (!empty && !I.wizard && !draft)) {
      if (window.SPPrompts) { await window.SPPrompts.render(body, 'profile'); if (prof.editable) body.insertAdjacentHTML('afterbegin', `<div class="om-value-actions in-redo"><button type="button" class="sm-btn" data-in-redo>${H(w('redo_org'))}</button></div>`); }
      const redo = body.querySelector('[data-in-redo]'); if (redo) redo.onclick = () => { I.wizard = true; render(body, 'org'); };
      return;
    }
    let structure = null; try { const s = await call('/api/org/chart'); structure = { departments: (s.departments || []).map(d => ({ name: d.name, teams: (d.teams || []).map(t => t.name) })) }; } catch (_e) {}
    let me = {}; try { me = await call('/api/org/structure/me'); } catch (_e) {}
    I.ctx = { structure, can_manage: !!me.can_manage };
    const goals = (prof.goals || []).map(g => { const m = /^(.*) \(KPI: (.*)\)$/.exec(g); return m ? { goal: m[1], kpi: m[2] } : { goal: g, kpi: '' }; });
    const base = { name: prof.name || '', website: prof.website || '', sector: prof.sector || '', size: prof.size || '', description: prof.description || '', products: prof.products || [],
                   customers: prof.customers || '', _goals: goals, systems: prof.systems || [], rules: prof.rules || [], policy: prof.policy || '' };
    I.d = draft && draft.d ? Object.assign(base, draft.d) : base; I.step = draft ? draft.step || 0 : 0;
    paint();
  }
  window.SPIntake = { render, hintMe: () => w('hint_me'), openMe: () => w('open_me') };
})();
