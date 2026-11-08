/* Organisation, Management and value per task or bot (8 Nov 2026).

   Three surfaces share this file:
   - Organisation (#mainOrganisation): organisation chart of departments,
     teams, people and the bots and scheduled tasks that work for them, plus
     team management for organisation and department admins.
   - Management (#mainManagement): what automation saves and costs per team,
     and what needs a decision. Every number links to where it comes from.
   - Value: a card in the task detail (minutes by hand before against the
     minutes a person still spends now) and minutes on bot responsibilities.

   APIs: /api/org/structure(/me), /api/org/chart, /api/management/*,
   /api/value/*. Nothing here decides access; the server filters by scope. */
(function(){
  'use strict';

  const W = {
    nl: {
      per_label: 'Eenheid', per_run_opt: 'per keer', per_day_opt: 'per dag', per_week_opt: 'per week', per_hint: 'Draait de taak vaker dan dagelijks? Kies per dag: de besparing telt dan één keer per dag met een geslaagde run.',
      of_which_confirmed: 'waarvan {h} bevestigd', all_estimated: 'nog geheel op basis van AI-schattingen',
      d_check_high: 'Schatting lijkt hoog', d_check_high_sub: 'meer dan 4 uur per dag voor één taak; controleer eenheid en minuten',
      chip_logged: 'Gelogd als: {d} · bespaart ~{m} min', chip_no_duty: 'Niet gekoppeld aan een verantwoordelijkheid', chip_wrong: 'Klopt niet', chip_which: 'Welke verantwoordelijkheid deed dit gesprek?', chip_none: 'Geen',
      measuring_since: 'Meting loopt sinds {d}: eerdere runs waren al opgeschoond, dus deze periode is nog niet compleet.',
      person: 'Persoon',
      other: 'Overig', fails: 'faalt', no_value: 'zonder waarde', suggested: 'voorstel',
      suggest_intro: '{n} voorstellen op basis van de bestaande categorie.', apply_suggestions: 'Neem alle voorstellen over', applied_n: '{n} ingedeeld',
      org: 'Organisatie', mgmt: 'Management', chart: 'Organigram', manage: 'Teams beheren',
      people: 'Mensen', bots: 'Bots', both: 'Samen', tasks: 'Taken', team: 'Team', teams: 'Teams',
      department: 'Afdeling', departments: 'Afdelingen', lead: 'Lead', members: 'Leden', rate: 'Uurtarief',
      org_intro: 'Wie in welk team zit, welke bots en geplande taken voor dat team werken, en hoeveel tijd dat bespaart.',
      mgmt_intro: 'Wat automatisering per team oplevert en kost, en waar een beslissing nodig is. Elk getal is te herleiden: klik erop.',
      empty_title: 'Je organisatie is nog niet ingericht',
      empty_body: 'Leg afdelingen en teams vast. Daarna zie je per team welke bots en taken er draaien en wat dat oplevert.',
      empty_start: 'Zelf opbouwen', empty_template: 'Start met een voorbeeldindeling',
      empty_member: 'Je zit nog niet in een team. Vraag je lead of beheerder om je in te delen.',
      no_access: 'Dit scherm is voor organisatie- en afdelingsbeheerders.',
      unassigned: 'Niet ingedeeld', unassigned_hint: 'Bots en taken die nog geen team hebben.',
      assign: 'Indelen in team', choose_team: 'Kies team', none: 'Geen',
      running_now: 'Draait nu', playbooks: 'Playbooks', waiting: 'Wacht op actie', saving: 'Besparing',
      new_automation: 'Nieuwe automatisering voor dit team', open_mgmt: 'Open in Management',
      saved_hours: 'u bespaard', h: 'u', min: 'min', per_week: 'per week', per_run: 'per keer',
      nothing_yet: 'Nog niets', nothing_runs: 'Hier draait nog niets.',
      add_team: 'Team toevoegen', add_dept: 'Afdeling toevoegen', save: 'Opslaan', delete: 'Verwijderen',
      cancel: 'Annuleren', name: 'Naam', key: 'Sleutel', saved: 'Opgeslagen', removed: 'Verwijderd',
      confirm_delete: 'Team verwijderen? Mensen blijven bestaan, alleen de indeling verdwijnt.',
      period: 'Periode', d7: '7 dagen', d28: '4 weken', d90: '3 maanden', d365: '12 maanden',
      compare: 'Vergelijk met vorige periode', refresh: 'Vernieuwen', settings: 'Prijzen en tarieven', export: 'Exporteer CSV',
      k_saved: 'Tijd bespaard', k_saved_sub: 'uit geslaagde runs en gesprekken',
      k_estimate: 'geschat via bot-verantwoordelijkheden',
      k_net: 'Netto waarde', k_net_sub: 'indicatief, op basis van uurtarieven', k_net_missing: 'Stel uurtarieven in',
      k_cost: 'AI-kosten', k_cost_sub: 'API-equivalent', k_cost_missing: 'Prijzen instellen', tokens: 'tokens zonder prijs',
      k_return: 'Rendement', k_return_sub: 'waarde gedeeld door AI-kosten',
      k_active: 'Actief', k_active_sub: 'taken aan, bots',
      k_coverage: 'Dekking', k_coverage_sub: 'taken met een bevestigde nulmeting',
      decisions: 'Beslissing nodig', decisions_none: 'Niets dat nu je aandacht vraagt.',
      d_failing: 'Taken die herhaald falen', d_failing_sub: 'drie keer of vaker achter elkaar mislukt',
      d_missing_value: 'Taken zonder waarde', d_missing_value_sub: 'vul in hoeveel tijd dit met de hand kostte',
      d_unconfirmed: 'Schattingen niet bevestigd', d_unconfirmed_sub: 'de eigenaar bevestigt of stelt bij',
      d_negative: 'Kost meer dan het oplevert', d_negative_sub: 'AI-kosten hoger dan de bespaarde tijd',
      d_idle_teams: 'Teams zonder automatisering', d_idle_teams_sub: 'hier draait nog geen bot of taak',
      d_unassigned: 'Nog niet ingedeeld', d_unassigned_sub: 'taken en bots zonder team',
      d_old_approvals: 'Goedkeuringen wachten langer dan 3 dagen', d_old_approvals_sub: 'bekijk ze in Governance',
      open: 'Openen', fill: 'Invullen', yes: 'Klopt', less: 'Minder', more: 'Meer', find_use_case: 'Use case zoeken',
      per_team: 'Per team', per_bot: 'Bots', top: 'Meeste waarde',
      col_team: 'Team', col_lead: 'Lead', col_bots: 'Bots', col_tasks: 'Taken', col_runs: 'Runs', col_success: 'Gelukt',
      col_saved: 'Bespaard', col_estimate: 'Geschat', col_cost: 'AI-kosten', col_net: 'Netto',
      col_bot: 'Bot', col_chats: 'Gesprekken', col_people: 'Mensen', col_labeled: 'Bevestigd bespaard', col_week: 'Schatting per week',
      last_collect: 'Gegevens bijgewerkt', price_title: 'Prijzen voor AI-kosten (API-equivalent)',
      price_intro: 'Per model de prijs in euro per miljoen tokens. Gebruik * voor alle overige modellen. Zonder prijs blijft de AI-prijs onbekend en tonen we het aantal tokens.',
      model: 'Model', p_in: 'Invoer', p_out: 'Uitvoer', p_cache: 'Cache', add_row: 'Regel toevoegen',
      rates_title: 'Uurtarieven', rates_intro: 'Per afdeling of team, voor de netto waarde in euro. Zonder tarief tonen we alleen uren.',
      // Value card
      value: 'Waarde', value_intro: 'Wat dit werk eerst met de hand kostte, en wat een mens er nu nog aan kwijt is.',
      before: 'Eerst, met de hand', now: 'Nu, controle', saves: 'Bespaart', task_label: 'Welk werk vervangt dit?',
      task_ph: 'Bijv. debiteurenlijst samenstellen', minutes_before: 'Minuten eerst per keer', minutes_now: 'Minuten nu per keer',
      unknown: 'Weet ik nog niet', unknown_reason: 'Waarom nog onbekend?',
      measured: 'Gemeten', measured_runs: 'geslaagde runs', failed_runs: 'mislukt', in_period: 'in 4 weken',
      label_confirmed: 'Bevestigd door eigenaar', label_ai_estimate: 'AI-schatting', label_estimated: 'Schatting',
      label_missing: 'Waarde ontbreekt', label_unknown: 'Nog onbekend',
      confirm_q: 'Klopt deze schatting?', edit: 'Aanpassen', team_of_task: 'Team van deze taak',
      value_saved: 'Waarde opgeslagen', value_cleared: 'Waarde gewist', need_minutes: 'Vul de minuten eerst in, of kies Weet ik nog niet',
      // Bot duties
      duty_minutes_before: 'Minuten eerst', duty_minutes_now: 'Minuten nu', duty_times: 'Keer per week',
      duty_saves: 'bespaart ~{h} u per week', serves: 'Werkt voor team(s)', serves_hint: 'Bepaalt onder welk team deze bot in Organisatie en Management staat.',
      template_note: 'Voorbeeldindeling toegevoegd. Pas namen en leden aan.',
      chat_prompt_team: 'Help me een nieuwe automatisering te bedenken voor het team {team}. Vraag eerst welk terugkerend werk het team de meeste tijd kost en hoe lang dat nu met de hand duurt.',
      chat_prompt_value: 'Help me de waarde van mijn geplande taak "{task}" te bepalen: hoeveel minuten kostte dit werk met de hand, en hoeveel tijd kost controle nu?'
    },
    en: {
      per_label: 'Unit', per_run_opt: 'per run', per_day_opt: 'per day', per_week_opt: 'per week', per_hint: 'Runs more than daily? Choose per day: the saving then counts once per day with a completed run.',
      of_which_confirmed: 'of which {h} confirmed', all_estimated: 'still entirely based on AI estimates',
      d_check_high: 'Estimate looks high', d_check_high_sub: 'more than 4 hours a day for one task; check unit and minutes',
      chip_logged: 'Logged as: {d} · saves ~{m} min', chip_no_duty: 'Not linked to a responsibility', chip_wrong: 'Not right', chip_which: 'Which responsibility did this chat cover?', chip_none: 'None',
      measuring_since: 'Measuring since {d}: earlier runs had already been pruned, so this period is not complete yet.',
      person: 'Person',
      other: 'Other', fails: 'failing', no_value: 'without value', suggested: 'suggested',
      suggest_intro: '{n} suggestions based on the existing category.', apply_suggestions: 'Apply all suggestions', applied_n: '{n} placed',
      org: 'Organisation', mgmt: 'Management', chart: 'Org chart', manage: 'Manage teams',
      people: 'People', bots: 'Bots', both: 'Both', tasks: 'Tasks', team: 'Team', teams: 'Teams',
      department: 'Department', departments: 'Departments', lead: 'Lead', members: 'Members', rate: 'Hourly rate',
      org_intro: 'Who is in which team, which bots and scheduled tasks work for that team, and how much time that saves.',
      mgmt_intro: 'What automation delivers and costs per team, and where a decision is needed. Every number can be traced: click it.',
      empty_title: 'Your organisation is not set up yet',
      empty_body: 'Record departments and teams. Then you see per team which bots and tasks run and what they deliver.',
      empty_start: 'Build it yourself', empty_template: 'Start from an example structure',
      empty_member: 'You are not in a team yet. Ask your lead or administrator to place you.',
      no_access: 'This screen is for organisation and department administrators.',
      unassigned: 'Unassigned', unassigned_hint: 'Bots and tasks without a team yet.',
      assign: 'Place in team', choose_team: 'Choose team', none: 'None',
      running_now: 'Running now', playbooks: 'Playbooks', waiting: 'Needs action', saving: 'Savings',
      new_automation: 'New automation for this team', open_mgmt: 'Open in Management',
      saved_hours: 'h saved', h: 'h', min: 'min', per_week: 'per week', per_run: 'per run',
      nothing_yet: 'Nothing yet', nothing_runs: 'Nothing runs here yet.',
      add_team: 'Add team', add_dept: 'Add department', save: 'Save', delete: 'Delete',
      cancel: 'Cancel', name: 'Name', key: 'Key', saved: 'Saved', removed: 'Removed',
      confirm_delete: 'Delete this team? People stay, only the grouping goes.',
      period: 'Period', d7: '7 days', d28: '4 weeks', d90: '3 months', d365: '12 months',
      compare: 'Compare with previous period', refresh: 'Refresh', settings: 'Prices and rates', export: 'Export CSV',
      k_saved: 'Time saved', k_saved_sub: 'from completed runs and chats',
      k_estimate: 'estimated from bot responsibilities',
      k_net: 'Net value', k_net_sub: 'indicative, based on hourly rates', k_net_missing: 'Set hourly rates',
      k_cost: 'AI cost', k_cost_sub: 'API equivalent', k_cost_missing: 'Set prices', tokens: 'tokens without a price',
      k_return: 'Return', k_return_sub: 'value divided by AI cost',
      k_active: 'Active', k_active_sub: 'tasks on, bots',
      k_coverage: 'Coverage', k_coverage_sub: 'tasks with a confirmed baseline',
      decisions: 'Needs a decision', decisions_none: 'Nothing needs your attention right now.',
      d_failing: 'Tasks failing repeatedly', d_failing_sub: 'three or more failures in a row',
      d_missing_value: 'Tasks without a value', d_missing_value_sub: 'fill in how long this took by hand',
      d_unconfirmed: 'Estimates not confirmed', d_unconfirmed_sub: 'the owner confirms or adjusts',
      d_negative: 'Costs more than it saves', d_negative_sub: 'AI cost above the time saved',
      d_idle_teams: 'Teams without automation', d_idle_teams_sub: 'no bot or task runs here yet',
      d_unassigned: 'Not placed yet', d_unassigned_sub: 'tasks and bots without a team',
      d_old_approvals: 'Approvals waiting over 3 days', d_old_approvals_sub: 'review them in Governance',
      open: 'Open', fill: 'Fill in', yes: 'Correct', less: 'Less', more: 'More', find_use_case: 'Find a use case',
      per_team: 'Per team', per_bot: 'Bots', top: 'Most value',
      col_team: 'Team', col_lead: 'Lead', col_bots: 'Bots', col_tasks: 'Tasks', col_runs: 'Runs', col_success: 'Succeeded',
      col_saved: 'Saved', col_estimate: 'Estimated', col_cost: 'AI cost', col_net: 'Net',
      col_bot: 'Bot', col_chats: 'Chats', col_people: 'People', col_labeled: 'Confirmed saved', col_week: 'Estimate per week',
      last_collect: 'Data updated', price_title: 'Prices for AI cost (API equivalent)',
      price_intro: 'Per model the price in euro per million tokens. Use * for all other models. Without a price the AI cost stays unknown and we show the token count.',
      model: 'Model', p_in: 'Input', p_out: 'Output', p_cache: 'Cache', add_row: 'Add row',
      rates_title: 'Hourly rates', rates_intro: 'Per department or team, for the net value in euro. Without a rate we only show hours.',
      value: 'Value', value_intro: 'What this work took by hand before, and what a person still spends on it now.',
      before: 'Before, by hand', now: 'Now, review', saves: 'Saves', task_label: 'Which work does this replace?',
      task_ph: 'E.g. compile the receivables list', minutes_before: 'Minutes before per run', minutes_now: 'Minutes now per run',
      unknown: 'Not known yet', unknown_reason: 'Why not known yet?',
      measured: 'Measured', measured_runs: 'completed runs', failed_runs: 'failed', in_period: 'in 4 weeks',
      label_confirmed: 'Confirmed by owner', label_ai_estimate: 'AI estimate', label_estimated: 'Estimate',
      label_missing: 'Value missing', label_unknown: 'Not known yet',
      confirm_q: 'Is this estimate right?', edit: 'Edit', team_of_task: 'Team of this task',
      value_saved: 'Value saved', value_cleared: 'Value cleared', need_minutes: 'Fill in the minutes first, or choose Not known yet',
      duty_minutes_before: 'Minutes before', duty_minutes_now: 'Minutes now', duty_times: 'Times per week',
      duty_saves: 'saves ~{h} h per week', serves: 'Works for team(s)', serves_hint: 'Decides under which team this bot appears in Organisation and Management.',
      template_note: 'Example structure added. Adjust names and members.',
      chat_prompt_team: 'Help me come up with a new automation for the team {team}. First ask which recurring work costs the team the most time and how long it takes by hand now.',
      chat_prompt_value: 'Help me determine the value of my scheduled task "{task}": how many minutes did this work take by hand, and how much time does review take now?'
    }
  };
  const lang = () => ((document.documentElement.lang || 'nl').toLowerCase().startsWith('en') ? 'en' : 'nl');
  const w = (k, vars) => { let s = (W[lang()] || W.nl)[k] || W.nl[k] || k; if (vars) for (const [a, b] of Object.entries(vars)) s = s.replace('{' + a + '}', b); return s; };
  const H = v => (typeof esc === 'function' ? esc(String(v ?? '')) : String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
  const $id = id => document.getElementById(id);
  const toast = m => { if (typeof showToast === 'function') showToast(m); };
  const call = (path, opts) => api(path, Object.assign({ timeoutToast: false }, opts || {}));
  const post = (path, body) => call(path, { method: 'POST', body: JSON.stringify(body) });
  const nf = (d) => new Intl.NumberFormat(lang() === 'en' ? 'en-GB' : 'nl-NL', { maximumFractionDigits: d ?? 1 });
  const hrs = m => nf(1).format((m || 0) / 60) + ' ' + w('h');
  const eur = v => v == null ? '' : new Intl.NumberFormat(lang() === 'en' ? 'en-GB' : 'nl-NL', { style: 'currency', currency: 'EUR', maximumFractionDigits: Math.abs(v) < 10 ? 2 : 0 }).format(v);
  const initials = s => String(s || '?').replace(/@.*/, '').split(/[.\s_-]+/).filter(Boolean).slice(0, 2).map(x => x[0].toUpperCase()).join('') || '?';
  const errMsg = e => (e && e.message) || String(e);

  // ── Who may see what (nav) ────────────────────────────────────────────────
  let me = null;
  async function loadMe(force){
    if (me && !force) return me;
    try { me = await call('/api/org/structure/me'); } catch (_e) { me = { can_view: false, can_manage: false }; }
    return me;
  }
  async function refreshNav(){
    const info = await loadMe(true);
    document.querySelectorAll('[data-panel="organisation"]').forEach(b => { b.hidden = !info.can_view; });
    document.querySelectorAll('[data-panel="management"]').forEach(b => { b.hidden = !info.can_manage; });
  }

  async function startChat(text){
    try {
      if (typeof switchPanel === 'function') await switchPanel('chat');
      if (typeof newSession === 'function') await newSession(false);
    } catch (_e) {}
    const box = $id('msg');
    if (box) { box.value = text; box.focus(); if (typeof autoResize === 'function') autoResize(); }
  }
  async function openTask(jobId, store, bot){
    if (typeof openCronFromBot === 'function') return openCronFromBot(jobId, store || 'default', bot || store || 'default');
  }

  // ── Organisation screen ───────────────────────────────────────────────────
  const O = { view: 'chart', layer: 'both', chart: null, structure: null, selected: '', busy: false, error: '' };

  function shell(id, title, actions){
    const root = $id(id);
    if (!root) return null;
    if (!root.querySelector('.main-view-body')) {
      root.innerHTML = `<div class="main-view-header"><div><div class="main-view-title">${H(title)}</div></div><div class="om-head-actions" data-om-actions></div></div><div class="main-view-body"><div class="om-wrap" data-om-body></div></div>`;
    }
    root.querySelector('[data-om-actions]').innerHTML = actions || '';
    return root.querySelector('[data-om-body]');
  }

  async function loadOrg(){
    await loadMe(true);
    O.error = '';
    try {
      const [chart, structure] = await Promise.all([call('/api/org/chart'), call('/api/org/structure')]);
      O.chart = chart; O.structure = structure;
    } catch (e) {
      O.chart = null; O.structure = null;
      O.error = e && e.status === 403 ? (me && me.can_manage ? '' : w('empty_member')) : errMsg(e);
    }
    renderOrg();
  }

  function orgActions(){
    const tabs = `<div class="om-seg" role="group" aria-label="${H(w('org'))}">
      <button type="button" aria-pressed="${O.view === 'chart'}" data-om-view="chart">${H(w('chart'))}</button>
      ${me && me.can_manage ? `<button type="button" aria-pressed="${O.view === 'manage'}" data-om-view="manage">${H(w('manage'))}</button>` : ''}
    </div>`;
    const layer = O.view === 'chart' ? `<div class="om-seg" role="group" aria-label="${H(w('chart'))}">
      ${['people', 'bots', 'both'].map(l => `<button type="button" aria-pressed="${O.layer === l}" data-om-layer="${l}">${H(w(l))}</button>`).join('')}
    </div>` : '';
    return tabs + layer + `<button type="button" class="sm-btn" data-om-refresh>${H(w('refresh'))}</button>`;
  }

  function teamCardHtml(team){
    const s = team.stats || {};
    const flag = (s.failing || 0) > 0 || (s.missing_value || 0) > 0;
    const saving = (s.saved_minutes || 0) > 0 ? `<div class="om-team-saving">${H(hrs(s.saved_minutes))} ${H(w('saved_hours').replace(/^\S+\s*/, ''))}</div>`
      : `<div class="om-team-saving none">${H((s.jobs || 0) + (s.bots || 0) ? '' : w('nothing_yet'))}</div>`;
    const people = O.layer !== 'bots' ? `<div class="om-chips">${(team.people || []).slice(0, 6).map(p => `<span class="om-chip" title="${H(p.email)}">${H(p.email === team.lead ? '★ ' : '')}${H(p.email.replace(/@.*/, ''))}</span>`).join('')}${(team.people || []).length > 6 ? `<span class="om-chip">+${(team.people || []).length - 6}</span>` : ''}</div>` : '';
    const bots = O.layer !== 'people' ? `<div class="om-chips">${(team.bot_list || []).slice(0, 5).map(b => `<span class="om-chip">🤖 ${H(b.title)}</span>`).join('')}</div>` : '';
    return `<button type="button" class="om-team-card" data-om-team="${H(team.key)}" aria-pressed="${O.selected === team.key}">
      ${flag ? `<span class="om-flag" title="${H(w('waiting'))}"></span>` : ''}
      <span class="om-team-name">${H(team.name)}</span>
      <span class="om-stats"><span><b>${(team.people || []).length}</b> ${H(((team.people || []).length === 1 ? w('person') : w('people')).toLowerCase())}</span><span><b>${(team.bot_list || []).length}</b> ${H(w('bots').toLowerCase())}</span><span><b>${(team.job_list || []).filter(j => j.state !== 'paused').length}</b> ${H(w('tasks').toLowerCase())}</span></span>
      ${saving}${people}${bots}
    </button>`;
  }

  function teamOptions(selected){
    const teams = (O.structure && O.structure.teams) || {};
    const depts = (O.structure && O.structure.departments) || {};
    const groups = {};
    for (const t of Object.values(teams)) (groups[t.department] = groups[t.department] || []).push(t);
    return `<option value="">${H(w('choose_team'))}</option>` + Object.keys(groups).sort().map(d => `<optgroup label="${H((depts[d] || {}).name || d)}">${groups[d].sort((a, b) => a.name.localeCompare(b.name)).map(t => `<option value="${H(t.key)}" ${t.key === selected ? 'selected' : ''}>${H(t.name)}</option>`).join('')}</optgroup>`).join('');
  }

  function jobRowHtml(j, opts){
    opts = opts || {};
    const label = j.value_label || 'missing';
    return `<div class="om-row" data-job="${H(j.id)}" data-store="${H(j.store)}">
      <span class="om-dot ${H(j.state || 'new')}" aria-hidden="true"></span>
      <div class="om-row-main"><div class="om-row-title">${H(j.name)}</div>
        <div class="om-row-sub">${j.saved_minutes ? H(hrs(j.saved_minutes)) + ' · ' : ''}${H(j.runs || 0)} ${H(w('col_runs').toLowerCase())}${j.failed_runs ? ' · ' + H(j.failed_runs) + ' ' + H(w('failed_runs')) : ''}</div></div>
      <div class="om-row-actions"><span class="om-badge ${H(label)}">${H(w('label_' + label))}</span>
        ${opts.assign ? `<select class="om-select" data-om-assign-job aria-label="${H(w('assign'))}">${teamOptions('')}</select>` : ''}
        <button type="button" class="sm-btn" data-om-open-job>${H(w('open'))}</button></div>
    </div>`;
  }

  function botRowHtml(b, opts){
    opts = opts || {};
    const av = b.avatar_url ? `<img src="${H(b.avatar_url)}" alt="">` : H(initials(b.title));
    const est = b.estimate_minutes_per_week ? w('duty_saves', { h: nf(1).format(b.estimate_minutes_per_week / 60) }) : '';
    return `<div class="om-row" data-bot="${H(b.name)}">
      <span class="om-avatar" style="${b.color ? 'background:' + H(b.color) : ''}">${av}</span>
      <div class="om-row-main"><div class="om-row-title">${H(b.title)}</div><div class="om-row-sub">${H(b.role || '')}${b.role && est ? ' · ' : ''}${H(est)}</div></div>
      <div class="om-row-actions">${opts.assign ? `<select class="om-select" data-om-assign-bot aria-label="${H(w('assign'))}">${teamOptions('')}</select>` : ''}
      <button type="button" class="sm-btn" data-om-open-bot>${H(w('open'))}</button></div>
    </div>`;
  }

  function drawerHtml(team){
    if (!team) return '';
    const s = team.stats || {};
    const jobs = team.job_list || [];
    const bots = team.bot_list || [];
    const waiting = jobs.filter(j => j.state === 'error' || j.value_label === 'missing');
    const money = me && me.can_manage && s.net_eur != null ? ` · ${H(eur(s.net_eur))}` : '';
    return `<aside class="om-drawer" aria-label="${H(team.name)}">
      <div class="om-drawer-head"><div><h3>${H(team.name)}</h3><div class="om-muted om-small">${H(w('lead'))}: ${H(team.lead || '·')}</div></div>
      <button type="button" class="om-drawer-close" data-om-close aria-label="${H(w('cancel'))}">×</button></div>
      <h4>${H(w('saving'))}</h4>
      <div class="om-row" style="padding:4px 0"><div class="om-row-main"><div class="om-row-title">${H(hrs(s.saved_minutes || 0))}${money}</div>
        <div class="om-row-sub">${H(w('in_period'))} · ${H(s.runs || 0)} ${H(w('col_runs').toLowerCase())}${s.failed_runs ? ' · ' + H(s.failed_runs) + ' ' + H(w('failed_runs')) : ''}${s.estimate_minutes ? ' · ' + H(hrs(s.estimate_minutes)) + ' ' + H(w('k_estimate')) : ''}</div></div></div>
      ${waiting.length ? `<h4>${H(w('waiting'))} (${waiting.length})</h4><div class="om-list">${waiting.map(j => jobRowHtml(j)).join('')}</div>` : ''}
      <h4>${H(w('running_now'))}</h4>
      ${bots.length || jobs.length ? `<div class="om-list">${bots.map(b => botRowHtml(b)).join('')}${jobs.filter(j => !waiting.includes(j)).map(j => jobRowHtml(j)).join('')}</div>` : `<p class="om-muted om-small">${H(w('nothing_runs'))}</p>`}
      <h4>${H(w('people'))} (${(team.people || []).length})</h4>
      <div class="om-list">${(team.people || []).map(p => `<div class="om-row"><span class="om-person">${H(initials(p.email))}</span><div class="om-row-main"><div class="om-row-title">${H(p.email)}${p.email === team.lead ? ' · ' + H(w('lead')) : ''}</div><div class="om-row-sub">${H(p.title || '')}${p.reports_to ? ' → ' + H(p.reports_to) : ''}</div></div></div>`).join('')}</div>
      <div class="om-value-actions" style="margin-top:16px">
        <button type="button" class="sm-btn primary" data-om-new-automation="${H(team.key)}">${H(w('new_automation'))}</button>
        ${me && me.can_manage ? `<button type="button" class="sm-btn" data-om-goto-mgmt>${H(w('open_mgmt'))}</button>` : ''}
      </div>
    </aside>`;
  }

  function findTeam(key){
    for (const d of (O.chart && O.chart.departments) || []) for (const t of d.teams || []) if (t.key === key) return t;
    return null;
  }

  function sideEl(id){
    const panel = $id(id);
    if (!panel) return null;
    let box = panel.querySelector('.om-side');
    if (!box) { box = document.createElement('nav'); box.className = 'om-side'; panel.append(box); }
    return box;
  }
  function renderOrgSide(){
    const box = sideEl('panelOrganisation');
    if (!box) return;
    box.setAttribute('aria-label', w('teams'));
    const depts = (O.chart && O.chart.departments) || [];
    const u = O.chart && O.chart.unassigned;
    const uCount = u ? (u.job_list || []).filter(j => j.state !== 'paused').length + (u.bot_list || []).length : 0;
    box.innerHTML = depts.map(d => `<div class="om-side-label">${H(d.name)}</div>${(d.teams || []).map(t => {
        const s = t.stats || {};
        const flag = (s.failing || 0) + (s.missing_value || 0) > 0;
        return `<button type="button" data-om-side-team="${H(t.key)}" aria-current="${O.selected === t.key}">${flag ? '<span class="om-side-flag" aria-hidden="true"></span>' : ''}${H(t.name)}<span class="om-side-count">${(t.job_list || []).filter(j => j.state !== 'paused').length + (t.bot_list || []).length}</span></button>`;
      }).join('')}`).join('') + (uCount ? `<div class="om-side-label">${H(w('other'))}</div><button type="button" data-om-side-unassigned>${H(w('unassigned'))}<span class="om-side-count">${uCount}</span></button>` : '');
    if (!box.dataset.omBound) {
      box.dataset.omBound = '1';
      box.addEventListener('click', ev => {
        const b = ev.target.closest('button');
        if (!b) return;
        if (b.dataset.omSideTeam) { O.view = 'chart'; O.selected = b.dataset.omSideTeam; renderOrg(); return; }
        if (b.hasAttribute('data-om-side-unassigned')) { O.view = 'chart'; renderOrg(); const el = document.querySelector('#mainOrganisation .om-unassigned'); if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); }
      });
    }
  }

  function renderOrg(){
    const body = shell('mainOrganisation', w('org'), orgActions());
    if (!body) return;
    renderOrgSide();
    if (O.error) { body.innerHTML = `<p class="om-intro">${H(w('org_intro'))}</p><div class="om-empty"><h3>${H(w('org'))}</h3><p>${H(O.error)}</p></div>`; return; }
    if (!O.chart) { body.innerHTML = `<p class="om-muted">…</p>`; return; }
    if (O.view === 'manage' && me && me.can_manage) { body.innerHTML = manageHtml(); if (window.SpPicker) SpPicker.mountAll(body); return; }
    const depts = O.chart.departments || [];
    const hasTeams = depts.some(d => (d.teams || []).length);
    if (!hasTeams) {
      body.innerHTML = `<p class="om-intro">${H(w('org_intro'))}</p><div class="om-empty"><h3>${H(w('empty_title'))}</h3><p>${H(me && me.can_manage ? w('empty_body') : w('empty_member'))}</p>
        ${me && me.can_manage ? `<div class="om-actions"><button type="button" class="sm-btn primary" data-om-view="manage">${H(w('empty_start'))}</button><button type="button" class="sm-btn" data-om-template>${H(w('empty_template'))}</button></div>` : ''}</div>
        ${unassignedHtml()}`;
      return;
    }
    const selected = O.selected ? findTeam(O.selected) : null;
    const orgName = lang() === 'en' ? 'Organisation' : 'Organisatie';
    body.innerHTML = `<p class="om-intro">${H(w('org_intro'))}</p>
      <div class="om-layout ${selected ? 'has-drawer' : ''}">
        <div class="om-tree"><div class="om-tree-root"><div class="om-org-node">${H(orgName)}</div>
          <div class="om-depts">${depts.map(d => `<div class="om-dept"><div class="om-dept-node"><strong>${H(d.name)}</strong><span class="om-muted om-small">${(d.teams || []).length} ${H(((d.teams || []).length === 1 ? w('team') : w('teams')).toLowerCase())}</span></div>
            <div class="om-dept-teams">${(d.teams || []).map(teamCardHtml).join('')}</div></div>`).join('')}</div></div>
          ${unassignedHtml()}</div>
        ${drawerHtml(selected)}
      </div>`;
  }

  function unassignedHtml(){
    const u = O.chart && O.chart.unassigned;
    if (!u || (!(u.job_list || []).length && !(u.bot_list || []).length)) return '';
    const canAssign = me && me.can_manage && O.structure && Object.keys(O.structure.teams || {}).length;
    return `<section class="om-section om-unassigned"><div class="om-section-head"><h3>${H(w('unassigned'))}</h3><span class="om-muted">${H(w('unassigned_hint'))}</span></div>
      <div class="om-card" style="padding:4px 0">${(u.bot_list || []).map(b => botRowHtml(b, { assign: canAssign })).join('')}${(u.job_list || []).filter(j => j.state !== 'paused').map(j => jobRowHtml(j, { assign: canAssign })).join('')}</div></section>`;
  }

  function manageHtml(){
    const s = O.structure || { departments: {}, teams: {} };
    const depts = Object.values(s.departments || {}).sort((a, b) => a.name.localeCompare(b.name));
    const teamsBy = {};
    for (const t of Object.values(s.teams || {})) (teamsBy[t.department] = teamsBy[t.department] || []).push(t);
    const all = (me && me.scope) === 'all';
    const teamRow = (t, dept) => `<form class="om-team-edit" data-om-team-form data-key="${H(t ? t.key : '')}" data-dept="${H(dept)}">
        <label class="om-field">${H(w('name'))}<input name="name" required maxlength="80" value="${H(t ? t.name : '')}"></label>
        <label class="om-field">${H(w('lead'))}<input name="lead" data-sp-picker data-sp-source="people" data-sp-custom="1" value="${H(t ? t.lead : '')}"></label>
        <label class="om-field">${H(w('members'))}<input name="members" data-sp-picker data-sp-source="people" data-sp-multi="1" data-sp-custom="1" value="${H(t ? (t.members || []).join(',') : '')}"></label>
        <label class="om-field">${H(w('rate'))}<input name="hourly_rate" type="number" min="0" step="1" value="${H(t && t.hourly_rate != null ? t.hourly_rate : '')}" placeholder="€"></label>
        <div class="om-row-actions"><button type="submit" class="sm-btn primary">${H(w('save'))}</button>${t ? `<button type="button" class="sm-btn danger" data-om-delete-team="${H(t.key)}">${H(w('delete'))}</button>` : ''}</div>
      </form>`;
    return `<p class="om-intro">${H(w('org_intro'))}</p>
      ${depts.map(d => `<section class="om-dept-block"><header><h3>${H(d.name)}</h3>
          ${d.editable ? `<label class="om-inline-form om-small om-muted">${H(w('rate'))} <input type="number" min="0" step="1" data-om-dept-rate="${H(d.key)}" value="${H(d.hourly_rate ?? '')}" placeholder="€"></label>` : ''}
          <span class="om-muted om-small">${H(d.source === 'policy' ? 'policy' : '')}</span></header>
        ${(teamsBy[d.key] || []).sort((a, b) => a.name.localeCompare(b.name)).map(t => teamRow(t, d.key)).join('')}
        <details><summary class="om-link" style="margin:6px 0 0">+ ${H(w('add_team'))}</summary>${teamRow(null, d.key)}</details>
      </section>`).join('')}
      ${all ? `<section class="om-section"><form class="om-inline-form" data-om-dept-form><input name="name" required maxlength="80" placeholder="${H(w('department'))}"><button type="submit" class="sm-btn">${H(w('add_dept'))}</button></form></section>` : ''}`;
  }

  async function orgMutate(body, okMsg){
    try { O.structure = await post('/api/org/structure', body); toast(okMsg || w('saved')); }
    catch (e) { toast(errMsg(e)); return false; }
    try { O.chart = await call('/api/org/chart'); } catch (_e) {}
    renderOrg();
    return true;
  }

  async function applyTemplate(){
    const lang_nl = lang() === 'nl';
    const depts = lang_nl ? [['management', 'Management'], ['commercieel', 'Commercieel'], ['delivery', 'Delivery'], ['marketing', 'Marketing'], ['finance', 'Finance'], ['tech', 'Tech']]
      : [['management', 'Management'], ['commercial', 'Commercial'], ['delivery', 'Delivery'], ['marketing', 'Marketing'], ['finance', 'Finance'], ['tech', 'Tech']];
    for (const [key, name] of depts) {
      try { await post('/api/org/structure', { op: 'department.save', key, name }); } catch (_e) {}
      try { await post('/api/org/structure', { op: 'team.save', department: key, key: key + '/' + key, name, members: [] }); } catch (_e) {}
    }
    toast(w('template_note'));
    O.view = 'manage';
    await loadOrg();
  }

  function bindOrg(){
    const root = $id('mainOrganisation');
    if (!root || root.dataset.omBound) return;
    root.dataset.omBound = '1';
    root.addEventListener('click', async ev => {
      const t = ev.target.closest('button,[data-om-view]');
      if (!t) return;
      if (t.dataset.omView) { O.view = t.dataset.omView; renderOrg(); return; }
      if (t.dataset.omLayer) { O.layer = t.dataset.omLayer; renderOrg(); return; }
      if (t.hasAttribute('data-om-refresh')) { await loadOrg(); return; }
      if (t.dataset.omTeam) { O.selected = O.selected === t.dataset.omTeam ? '' : t.dataset.omTeam; renderOrg(); return; }
      if (t.hasAttribute('data-om-close')) { O.selected = ''; renderOrg(); return; }
      if (t.hasAttribute('data-om-template')) { await applyTemplate(); return; }
      if (t.dataset.omNewAutomation) { if (window.SPStudio) { await window.SPStudio.newForTeam(t.dataset.omNewAutomation); return; } const team = findTeam(t.dataset.omNewAutomation); await startChat(w('chat_prompt_team', { team: team ? team.name : t.dataset.omNewAutomation })); return; }
      if (t.hasAttribute('data-om-goto-mgmt')) { if (typeof switchPanel === 'function') await switchPanel('management'); return; }
      if (t.dataset.omDeleteTeam) { if (confirm(w('confirm_delete'))) await orgMutate({ op: 'team.delete', key: t.dataset.omDeleteTeam }, w('removed')); return; }
      const row = t.closest('[data-job],[data-bot]');
      if (t.hasAttribute('data-om-open-job') && row) { await openTask(row.dataset.job, row.dataset.store); return; }
      if (t.hasAttribute('data-om-open-bot') && row) { if (typeof switchPanel === 'function') await switchPanel('profiles'); if (typeof openProfileDetail === 'function') openProfileDetail(row.dataset.bot); return; }
    });
    root.addEventListener('change', async ev => {
      const el = ev.target;
      const row = el.closest('[data-job],[data-bot]');
      if (el.hasAttribute('data-om-assign-job') && row && el.value) {
        try { await post('/api/value/job', { action: 'team', job_id: row.dataset.job, store: row.dataset.store, team: el.value }); toast(w('saved')); await loadOrg(); }
        catch (e) { toast(errMsg(e)); }
      }
      if (el.hasAttribute('data-om-assign-bot') && row && el.value) {
        try { await assignBot(row.dataset.bot, el.value); toast(w('saved')); await loadOrg(); }
        catch (e) { toast(errMsg(e)); }
      }
      if (el.dataset.omDeptRate !== undefined && el.dataset.omDeptRate) {
        await orgMutate({ op: 'department.save', key: el.dataset.omDeptRate, hourly_rate: el.value === '' ? null : Number(el.value) });
      }
    });
    root.addEventListener('submit', async ev => {
      const form = ev.target;
      ev.preventDefault();
      if (form.hasAttribute('data-om-team-form')) {
        // Read through the element's value property: the shared picker keeps
        // its selection there (static/sp-picker.js), not in the form data.
        const val = n => String((form.querySelector(`[name="${n}"]`) || {}).value || '');
        const members = val('members').split(',').map(s => s.trim()).filter(Boolean);
        const rate = val('hourly_rate');
        const body = { op: 'team.save', department: form.dataset.dept, name: val('name'), lead: val('lead').trim(), members, hourly_rate: rate === '' ? null : Number(rate) };
        if (form.dataset.key) body.key = form.dataset.key;
        await orgMutate(body);
      } else if (form.hasAttribute('data-om-dept-form')) {
        const name = String(new FormData(form).get('name') || '');
        await orgMutate({ op: 'department.save', name });
      }
    });
  }

  async function assignBot(bot, team){
    const list = await call('/api/profiles?fast=1');
    const row = ((list && list.profiles) || []).find(p => p.name === bot) || {};
    return post('/api/profile/appearance', { name: bot, revision: row.bot_revision || 0, bot: { serves: team ? [team] : [] } });
  }

  // ── Management screen ─────────────────────────────────────────────────────
  const M = { period: '28', compare: true, data: null, error: '', sort: 'saved_minutes', dir: -1, settings: false, pricing: null };

  async function loadMgmt(){
    await loadMe(true);
    M.error = '';
    try { M.data = await call('/api/management/overview?period=' + M.period + (M.compare ? '&compare=previous' : '')); }
    catch (e) { M.data = null; M.error = e && e.status === 403 ? w('no_access') : errMsg(e); }
    renderMgmt();
  }

  function mgmtActions(){
    return `<select class="om-select" data-om-period aria-label="${H(w('period'))}">${['7', '28', '90', '365'].map(p => `<option value="${p}" ${M.period === p ? 'selected' : ''}>${H(w('d' + p))}</option>`).join('')}</select>
      <button type="button" class="sm-btn" data-om-settings aria-expanded="${M.settings}">${H(w('settings'))}</button>
      <button type="button" class="sm-btn" data-om-export>${H(w('export'))}</button>
      <button type="button" class="sm-btn" data-om-mrefresh>${H(w('refresh'))}</button>`;
  }

  function delta(now, prev, invert){
    if (prev == null || now == null || !prev) return '';
    const d = (now - prev) / Math.abs(prev);
    if (!isFinite(d) || Math.abs(d) < 0.005) return '';
    const up = d > 0;
    return `<span class="om-kpi-delta ${(up !== !!invert) ? 'up' : 'down'}">${up ? '▲' : '▼'} ${nf(0).format(Math.abs(d) * 100)}%</span>`;
  }

  function kpisHtml(d){
    const t = d.totals || {}, p = d.previous_totals || {};
    const cover = t.coverage == null ? null : Math.round(t.coverage * 100);
    return `<div class="om-kpis">
      <div class="om-kpi"><span class="om-kpi-label">${H(w('k_saved'))}</span><span class="om-kpi-value">${H(hrs(t.saved_minutes))}</span>${delta(t.saved_minutes, p.saved_minutes)}
        <span class="om-kpi-sub">${H(w('k_saved_sub'))}${t.saved_minutes ? `<br><strong>${H(t.saved_confirmed_minutes ? w('of_which_confirmed', { h: hrs(t.saved_confirmed_minutes) }) : w('all_estimated'))}</strong>` : ''}${t.estimate_minutes ? `<br>+ ${H(hrs(t.estimate_minutes))} ${H(w('k_estimate'))}` : ''}</span></div>
      <div class="om-kpi"><span class="om-kpi-label">${H(w('k_net'))}</span>${t.net_eur != null ? `<span class="om-kpi-value">${H(eur(t.net_eur))}</span>${delta(t.net_eur, p.net_eur)}<span class="om-kpi-sub">${H(w('k_net_sub'))}</span>` : `<span class="om-kpi-value om-muted">·</span><button type="button" class="om-link" data-om-goto-rates>${H(w('k_net_missing'))}</button>`}</div>
      <div class="om-kpi"><span class="om-kpi-label">${H(w('k_cost'))}</span>${t.pricing_set ? `<span class="om-kpi-value">${H(eur(t.ai_cost_eur || 0))}</span>${delta(t.ai_cost_eur, p.ai_cost_eur, true)}<span class="om-kpi-sub">${H(w('k_cost_sub'))}${t.unpriced_tokens ? ' · ' + H(nf(0).format(t.unpriced_tokens)) + ' ' + H(w('tokens')) : ''}</span>` : `<span class="om-kpi-value om-muted">·</span><span class="om-kpi-sub">${H(nf(0).format(t.unpriced_tokens || 0))} ${H(w('tokens'))}</span><button type="button" class="om-link" data-om-settings>${H(w('k_cost_missing'))}</button>`}</div>
      <div class="om-kpi"><span class="om-kpi-label">${H(w('k_return'))}</span><span class="om-kpi-value">${t.return_ratio != null ? H(nf(1).format(t.return_ratio)) + '×' : '<span class="om-muted">·</span>'}</span><span class="om-kpi-sub">${H(w('k_return_sub'))}</span></div>
      <div class="om-kpi"><span class="om-kpi-label">${H(w('k_active'))}</span><span class="om-kpi-value">${H(t.active_jobs || 0)} · ${H(t.bots || 0)}</span><span class="om-kpi-sub">${H(w('k_active_sub'))}</span></div>
      <div class="om-kpi"><span class="om-kpi-label">${H(w('k_coverage'))}</span><span class="om-kpi-value">${cover == null ? '·' : H(cover) + '%'}</span><div class="om-bar" aria-hidden="true"><span style="width:${cover || 0}%"></span></div><span class="om-kpi-sub">${H(w('k_coverage_sub'))}</span></div>
    </div>`;
  }

  const SEV = { failing: 'high', negative: 'high', check_high: 'mid', missing_value: 'mid', unconfirmed: 'mid', unassigned: 'mid', old_approvals: 'mid', idle_teams: 'low' };

  function decisionItemHtml(kind, item){
    if (kind === 'idle_teams') return `<div class="om-row"><div class="om-row-main"><div class="om-row-title">${H(item.name)}</div></div><div class="om-row-actions"><button type="button" class="sm-btn" data-om-usecase="${H(item.name)}" data-om-usecase-key="${H(item.key)}">${H(w('find_use_case'))}</button></div></div>`;
    const teamName = item.team && item.team !== '_unassigned' ? ((M.data.team_names || {})[item.team] || item.team) : w('unassigned');
    let extra = '';
    if (kind === 'missing_value') extra = `<form class="om-inline-form" data-om-quick-value><input type="number" min="1" max="6000" name="before" placeholder="${H(w('duty_minutes_before'))}" aria-label="${H(w('minutes_before'))}" required><input type="number" min="0" max="6000" name="now" placeholder="${H(w('duty_minutes_now'))}" aria-label="${H(w('minutes_now'))}"><select class="om-select" name="per" aria-label="${H(w('per_label'))}">${['run', 'day', 'week'].map(p => `<option value="${p}">${H(w('per_' + p + '_opt'))}</option>`).join('')}</select><button type="submit" class="sm-btn primary">${H(w('save'))}</button></form>`;
    else if (kind === 'unconfirmed') extra = `<span class="om-confirm">${['yes', 'less', 'more'].map(a => `<button type="button" class="sm-btn" data-om-confirm="${a}">${H(w(a))}</button>`).join('')}</span>`;
    else if (kind === 'unassigned') extra = `<select class="om-select" ${item.bot ? 'data-om-assign-bot' : 'data-om-assign-job'} aria-label="${H(w('assign'))}">${mgmtTeamOptions(item.suggested_team)}</select>`;
    if (kind === 'unassigned' && item.bot) return `<div class="om-row" data-bot="${H(item.bot)}"><span class="om-avatar">${H(initials(item.name))}</span><div class="om-row-main"><div class="om-row-title">${H(item.name)}</div><div class="om-row-sub">${H(w('bots'))}${item.suggested_team ? ' · ' + H(w('suggested')) : ''}</div></div><div class="om-row-actions">${extra}</div></div>`;
    const unit = item.per ? w('per_' + item.per + '_opt') : '';
    const sub = kind === 'failing' ? `${item.failure_streak}× · ${teamName}` : kind === 'negative' ? `${eur(item.net_eur)} · ${teamName}`
      : kind === 'check_high' ? `${hrs(item.saved_minutes)} · ${item.runs} runs · ${item.before_minutes}→${item.review_minutes || 0} ${w('min')} ${unit}`
      : kind === 'unconfirmed' && item.before_minutes ? `${item.before_minutes}→${item.review_minutes || 0} ${w('min')} ${unit} · ${teamName}` : teamName;
    return `<div class="om-row" data-job="${H(item.id)}" data-store="${H(item.store)}"><div class="om-row-main"><div class="om-row-title">${H(item.name)}</div><div class="om-row-sub">${H(sub)}</div></div>
      <div class="om-row-actions">${extra}<button type="button" class="sm-btn" data-om-open-job>${H(w('open'))}</button></div></div>`;
  }

  function mgmtTeamOptions(selected){
    const names = (M.data && M.data.team_names) || {};
    return `<option value="">${H(w('choose_team'))}</option>` + Object.entries(names).sort((a, b) => a[1].localeCompare(b[1])).map(([k, n]) => `<option value="${H(k)}" ${k === selected ? 'selected' : ''}>${H(n)}${k === selected ? ' · ' + H(w('suggested')) : ''}</option>`).join('');
  }

  function decisionsHtml(d){
    const list = d.decisions || [];
    if (!list.length) return `<div class="om-card om-muted">${H(w('decisions_none'))}</div>`;
    return `<div class="om-decisions">${list.map(x => `<details class="om-decision sev-${SEV[x.kind] || 'low'}" ${x.kind === 'failing' ? 'open' : ''}>
      <summary><span class="om-decision-count">${H(x.count)}</span><div><div class="om-decision-title">${H(w('d_' + x.kind))}</div><div class="om-decision-sub">${H(w('d_' + x.kind + '_sub'))}</div></div></summary>
      ${(x.items || []).length ? `<div class="om-decision-body">${x.kind === 'unassigned' && x.suggestions ? `<div class="om-row"><div class="om-row-main"><div class="om-row-sub">${H(w('suggest_intro', { n: x.suggestions }))}</div></div><div class="om-row-actions"><button type="button" class="sm-btn primary" data-om-apply-suggestions>${H(w('apply_suggestions'))}</button></div></div>` : ''}${x.items.map(i => decisionItemHtml(x.kind, i)).join('')}</div>` : (x.kind === 'old_approvals' ? `<div class="om-decision-body"><div class="om-row"><button type="button" class="sm-btn" data-om-goto-gov>${H(w('open'))}</button></div></div>` : '')}
    </details>`).join('')}</div>`;
  }

  function teamsTableHtml(d){
    const rows = (d.teams || []).slice();
    const key = M.sort;
    rows.sort((a, b) => M.dir * (((a[key] ?? -1e12) > (b[key] ?? -1e12)) ? 1 : ((a[key] ?? -1e12) < (b[key] ?? -1e12)) ? -1 : 0));
    const th = (k, label, num) => `<th class="${num ? 'num' : ''}" aria-sort="${M.sort === k ? (M.dir > 0 ? 'ascending' : 'descending') : 'none'}"><button type="button" data-om-sort="${k}">${H(label)}${M.sort === k ? (M.dir > 0 ? ' ↑' : ' ↓') : ''}</button></th>`;
    return `<div class="om-table-wrap"><table class="om-table"><thead><tr>${th('name', w('col_team'))}${th('lead', w('col_lead'))}${th('bots', w('col_bots'), 1)}${th('active_jobs', w('col_tasks'), 1)}${th('runs', w('col_runs'), 1)}<th>${H(w('col_success'))}</th>${th('saved_minutes', w('col_saved'), 1)}${th('estimate_minutes', w('col_estimate'), 1)}${th('ai_cost_eur', w('col_cost'), 1)}${th('net_eur', w('col_net'), 1)}</tr></thead><tbody>
      ${rows.map(r => {
        const pct = r.runs ? Math.round(r.ok_runs / r.runs * 100) : null;
        const dept = (d.departments || {})[r.department];
        const name = r.key === '_unassigned' ? w('unassigned') : r.name;
        return `<tr data-om-team-row="${H(r.key)}" tabindex="0"><td><span class="om-team-name">${H(name)}</span>${dept ? `<div class="om-muted om-small">${H(dept.name)}</div>` : ''}${r.failing ? ` <span class="om-badge error">${H(r.failing)} ${H(w('fails'))}</span>` : ''}${r.missing_value ? ` <span class="om-badge missing">${H(r.missing_value)} ${H(w('no_value'))}</span>` : ''}</td>
          <td class="om-small">${H((r.lead || '').replace(/@.*/, ''))}</td><td class="num">${H(r.bots)}</td><td class="num">${H(r.active_jobs)}</td><td class="num">${H(r.runs)}</td>
          <td>${pct == null ? '<span class="om-muted">·</span>' : `<span class="om-success"><span class="om-bar"><span style="width:${pct}%"></span></span>${pct}%</span>`}</td>
          <td class="num">${r.saved_minutes ? H(hrs(r.saved_minutes)) : '<span class="om-muted">·</span>'}</td><td class="num om-muted">${r.estimate_minutes ? H(hrs(r.estimate_minutes)) : '·'}</td>
          <td class="num">${r.ai_cost_eur ? H(eur(r.ai_cost_eur)) : (r.unpriced_tokens ? `<span class="om-muted" title="${H(nf(0).format(r.unpriced_tokens))} ${H(w('tokens'))}">?</span>` : '<span class="om-muted">·</span>')}</td>
          <td class="num">${r.net_eur != null ? H(eur(r.net_eur)) : '<span class="om-muted">·</span>'}</td></tr>`;
      }).join('')}</tbody></table></div>`;
  }

  function botsTableHtml(d){
    const rows = d.bots || [];
    if (!rows.length) return '';
    return `<section class="om-section" data-om-anchor="bots"><div class="om-section-head"><h3>${H(w('per_bot'))}</h3></div><div class="om-table-wrap"><table class="om-table"><thead><tr><th>${H(w('col_bot'))}</th><th>${H(w('col_team'))}</th><th class="num">${H(w('col_tasks'))}</th><th class="num">${H(w('col_chats'))}</th><th class="num">${H(w('col_people'))}</th><th class="num">${H(w('col_labeled'))}</th><th class="num">${H(w('col_week'))}</th><th class="num">${H(w('col_cost'))}</th></tr></thead><tbody>
      ${rows.map(b => `<tr data-om-bot-row="${H(b.name)}" tabindex="0"><td><span style="display:inline-flex;gap:8px;align-items:center"><span class="om-avatar" style="${b.color ? 'background:' + H(b.color) : ''}">${b.avatar_url ? `<img src="${H(b.avatar_url)}" alt="">` : H(initials(b.title))}</span>${H(b.title)}</span></td>
        <td class="om-small">${H(b.team === '_unassigned' ? w('unassigned') : ((d.team_names || {})[b.team] || b.team))}</td><td class="num">${H(b.jobs)}</td><td class="num">${H(b.chats)}</td><td class="num">${H(b.people)}</td>
        <td class="num">${b.labeled_minutes ? H(hrs(b.labeled_minutes)) : '<span class="om-muted">·</span>'}</td>
        <td class="num">${b.estimate_minutes_per_week ? H(hrs(b.estimate_minutes_per_week)) + (b.estimate_confirmed ? '' : ' <span class="om-badge estimated">~</span>') : `<span class="om-muted">${b.duties ? '·' : ''}</span>`}</td>
        <td class="num">${b.ai_cost_eur ? H(eur(b.ai_cost_eur)) : (b.unpriced_tokens ? '<span class="om-muted">?</span>' : '<span class="om-muted">·</span>')}</td></tr>`).join('')}
      </tbody></table></div></section>`;
  }

  function topHtml(d){
    if (!(d.top || []).length) return '';
    return `<section class="om-section" data-om-anchor="top"><div class="om-section-head"><h3>${H(w('top'))}</h3></div><div class="om-card" style="padding:4px 0">${d.top.map(j => jobRowHtml(Object.assign({}, j))).join('')}</div></section>`;
  }

  function settingsHtml(){
    if (!M.settings) return '';
    const models = Object.entries((M.pricing && M.pricing.models) || {});
    if (!models.length) models.push(['synthwave-auto', { in: '', out: '', cache: '' }]);
    const editable = M.pricing && M.pricing.editable;
    return `<section class="om-section om-card" id="omSettings"><div class="om-section-head"><h3>${H(w('price_title'))}</h3></div><p class="om-intro" style="margin-bottom:12px">${H(w('price_intro'))}</p>
      <form data-om-pricing><div class="om-table-wrap" style="box-shadow:none"><table class="om-table"><thead><tr><th>${H(w('model'))}</th><th class="num">${H(w('p_in'))}</th><th class="num">${H(w('p_out'))}</th><th class="num">${H(w('p_cache'))}</th></tr></thead><tbody>
        ${models.map(([m, p]) => `<tr data-om-price-row><td><input class="om-select" name="model" value="${H(m)}" ${editable ? '' : 'disabled'}></td>${['in', 'out', 'cache'].map(k => `<td class="num"><input class="om-select" style="width:90px;text-align:right" type="number" min="0" step="0.01" name="${k}" value="${H(p[k] ?? '')}" ${editable ? '' : 'disabled'}></td>`).join('')}</tr>`).join('')}
      </tbody></table></div>${editable ? `<div class="om-value-actions"><button type="button" class="sm-btn" data-om-add-price>${H(w('add_row'))}</button><button type="submit" class="sm-btn primary">${H(w('save'))}</button></div>` : ''}</form>
      <div class="om-section-head" style="margin-top:22px"><h3>${H(w('rates_title'))}</h3></div><p class="om-intro" style="margin-bottom:8px">${H(w('rates_intro'))}</p>
      <button type="button" class="sm-btn" data-om-goto-rates>${H(w('manage'))}</button></section>`;
  }

  function renderMgmtSide(){
    const box = sideEl('panelManagement');
    if (!box) return;
    box.setAttribute('aria-label', w('mgmt'));
    const d = M.data || {};
    const dec = (d.decisions || []).reduce((a, x) => a + (x.count || 0), 0);
    const items = [['kpis', w('k_saved')], ['decisions', w('decisions'), dec], ['teams', w('per_team'), (d.teams || []).length], ['bots', w('per_bot'), (d.bots || []).length], ['top', w('top')]];
    box.innerHTML = `<div class="om-side-label">${H(w('mgmt'))}</div>` + items.map(([k, label, n]) => `<button type="button" data-om-jump="${k}">${k === 'decisions' && n ? '<span class="om-side-flag" aria-hidden="true"></span>' : ''}${H(label)}${n != null ? `<span class="om-side-count">${H(n)}</span>` : ''}</button>`).join('')
      + `<div class="om-side-label">${H(w('period'))}</div>` + ['7', '28', '90', '365'].map(p => `<button type="button" data-om-side-period="${p}" aria-current="${M.period === p}">${H(w('d' + p))}</button>`).join('');
    if (!box.dataset.omBound) {
      box.dataset.omBound = '1';
      box.addEventListener('click', async ev => {
        const b = ev.target.closest('button');
        if (!b) return;
        if (b.dataset.omSidePeriod) { M.period = b.dataset.omSidePeriod; await loadMgmt(); return; }
        if (b.dataset.omJump) { const el = document.querySelector(`#mainManagement [data-om-anchor="${b.dataset.omJump}"]`); if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); }
      });
    }
  }

  function renderMgmt(){
    const body = shell('mainManagement', w('mgmt'), mgmtActions());
    if (!body) return;
    renderMgmtSide();
    if (M.error) { body.innerHTML = `<div class="om-empty"><h3>${H(w('mgmt'))}</h3><p>${H(M.error)}</p></div>`; return; }
    const d = M.data;
    if (!d) { body.innerHTML = '<p class="om-muted">…</p>'; return; }
    const updated = d.last_collect_at ? new Date(d.last_collect_at * 1000).toLocaleString(lang() === 'en' ? 'en-GB' : 'nl-NL', { dateStyle: 'medium', timeStyle: 'short' }) : '';
    const noTeams = !(d.teams || []).some(t => t.key !== '_unassigned');
    const since = d.ledger_since && d.ledger_since > d.start ? new Date(d.ledger_since * 1000).toLocaleString(lang() === 'en' ? 'en-GB' : 'nl-NL', { dateStyle: 'medium', timeStyle: 'short' }) : '';
    body.innerHTML = `<p class="om-intro">${H(w('mgmt_intro'))}${updated ? ` <span class="om-small">${H(w('last_collect'))}: ${H(updated)}</span>` : ''}</p>
      ${since ? `<p class="om-small om-muted" style="margin:-12px 0 18px">${H(w('measuring_since', { d: since }))}</p>` : ''}
      ${noTeams ? `<div class="om-empty" style="margin-bottom:18px"><h3>${H(w('empty_title'))}</h3><p>${H(w('empty_body'))}</p><div class="om-actions"><button type="button" class="sm-btn primary" data-om-goto-rates>${H(w('manage'))}</button></div></div>` : ''}
      ${settingsHtml()}
      <div data-om-anchor="kpis">${kpisHtml(d)}</div>
      <section class="om-section" data-om-anchor="decisions"><div class="om-section-head"><h3>${H(w('decisions'))}</h3></div>${decisionsHtml(d)}</section>
      <section class="om-section" data-om-anchor="teams"><div class="om-section-head"><h3>${H(w('per_team'))}</h3><span class="om-muted">${H(w('d' + d.period_days) || '')}</span></div>${teamsTableHtml(d)}</section>
      ${botsTableHtml(d)}${topHtml(d)}`;
  }

  function exportCsv(){
    const d = M.data;
    if (!d) return;
    const head = ['team', 'department', 'lead', 'bots', 'active_tasks', 'runs', 'ok_runs', 'saved_hours', 'estimate_hours', 'ai_cost_eur', 'net_eur'];
    const lines = [head.join(';')].concat((d.teams || []).map(t => [t.key === '_unassigned' ? w('unassigned') : t.name, t.department, t.lead, t.bots, t.active_jobs, t.runs, t.ok_runs,
      ((t.saved_minutes || 0) / 60).toFixed(2), ((t.estimate_minutes || 0) / 60).toFixed(2), t.ai_cost_eur ?? '', t.net_eur ?? ''].map(v => '"' + String(v ?? '').replace(/"/g, '""') + '"').join(';')));
    const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'management-' + new Date().toISOString().slice(0, 10) + '.csv';
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  function bindMgmt(){
    const root = $id('mainManagement');
    if (!root || root.dataset.omBound) return;
    root.dataset.omBound = '1';
    root.addEventListener('click', async ev => {
      const t = ev.target.closest('button,tr[data-om-team-row],tr[data-om-bot-row]');
      if (!t) return;
      if (t.hasAttribute('data-om-mrefresh')) { try { await post('/api/value/collect', {}); } catch (_e) {} await loadMgmt(); return; }
      if (t.hasAttribute('data-om-export')) { exportCsv(); return; }
      if (t.hasAttribute('data-om-settings')) { M.settings = !M.settings; if (M.settings && !M.pricing) { try { M.pricing = await call('/api/management/pricing'); } catch (e) { toast(errMsg(e)); } } renderMgmt(); return; }
      if (t.hasAttribute('data-om-add-price')) { const tb = root.querySelector('[data-om-pricing] tbody'); const tr = tb && tb.querySelector('tr'); if (tr) { const c = tr.cloneNode(true); c.querySelectorAll('input').forEach(i => { i.value = ''; }); tb.append(c); } return; }
      if (t.hasAttribute('data-om-goto-rates')) { O.view = 'manage'; if (typeof switchPanel === 'function') await switchPanel('organisation'); return; }
      if (t.hasAttribute('data-om-goto-gov')) { if (typeof switchPanel === 'function') await switchPanel('governance'); return; }
      if (t.dataset.omUsecase) { if (window.SPStudio && t.dataset.omUsecaseKey) { await window.SPStudio.newForTeam(t.dataset.omUsecaseKey); return; } await startChat(w('chat_prompt_team', { team: t.dataset.omUsecase })); return; }
      if (t.dataset.omSort) { const k = t.dataset.omSort; M.dir = M.sort === k ? -M.dir : -1; M.sort = k; renderMgmt(); return; }
      if (t.dataset.omTeamRow) { O.selected = t.dataset.omTeamRow === '_unassigned' ? '' : t.dataset.omTeamRow; O.view = 'chart'; if (typeof switchPanel === 'function') await switchPanel('organisation'); return; }
      if (t.dataset.omBotRow) { if (typeof switchPanel === 'function') await switchPanel('profiles'); if (typeof openProfileDetail === 'function') openProfileDetail(t.dataset.omBotRow); return; }
      const row = t.closest('[data-job]');
      if (row && t.hasAttribute('data-om-open-job')) { await openTask(row.dataset.job, row.dataset.store); return; }
      if (t.hasAttribute('data-om-apply-suggestions')) {
        const dec = ((M.data && M.data.decisions) || []).find(x => x.kind === 'unassigned');
        t.disabled = true;
        let n = 0;
        for (const it of (dec && dec.items) || []) {
          if (!it.suggested_team) continue;
          try {
            if (it.bot) await assignBot(it.bot, it.suggested_team);
            else await post('/api/value/job', { action: 'team', job_id: it.id, store: it.store, team: it.suggested_team });
            n++;
          } catch (_e) {}
        }
        toast(w('applied_n', { n }));
        await loadMgmt();
        return;
      }
      if (row && t.dataset.omConfirm) {
        try { await post('/api/value/job', { action: 'confirm', job_id: row.dataset.job, store: row.dataset.store, answer: t.dataset.omConfirm }); toast(w('value_saved')); await loadMgmt(); }
        catch (e) { toast(errMsg(e)); }
      }
    });
    root.addEventListener('change', async ev => {
      const el = ev.target;
      if (el.hasAttribute('data-om-period')) { M.period = el.value; await loadMgmt(); return; }
      const row = el.closest('[data-job]');
      if (row && el.hasAttribute('data-om-assign-job') && el.value) {
        try { await post('/api/value/job', { action: 'team', job_id: row.dataset.job, store: row.dataset.store, team: el.value }); toast(w('saved')); await loadMgmt(); }
        catch (e) { toast(errMsg(e)); }
      }
      const brow = el.closest('[data-bot]');
      if (brow && el.hasAttribute('data-om-assign-bot') && el.value) {
        try { await assignBot(brow.dataset.bot, el.value); toast(w('saved')); await loadMgmt(); }
        catch (e) { toast(errMsg(e)); }
      }
    });
    root.addEventListener('keydown', ev => {
      if ((ev.key === 'Enter' || ev.key === ' ') && ev.target.matches('tr[data-om-team-row],tr[data-om-bot-row]')) { ev.preventDefault(); ev.target.click(); }
    });
    root.addEventListener('submit', async ev => {
      const form = ev.target;
      ev.preventDefault();
      if (form.hasAttribute('data-om-quick-value')) {
        const row = form.closest('[data-job]');
        const fd = new FormData(form);
        try {
          await post('/api/value/job', { job_id: row.dataset.job, store: row.dataset.store, value: { before_minutes: Number(fd.get('before')), review_minutes: Number(fd.get('now') || 0), per: String(fd.get('per') || 'run'), source: 'owner', confidence: 'confirmed' } });
          toast(w('value_saved')); await loadMgmt();
        } catch (e) { toast(errMsg(e)); }
      } else if (form.hasAttribute('data-om-pricing')) {
        const models = {};
        form.querySelectorAll('[data-om-price-row]').forEach(tr => {
          const m = tr.querySelector('[name=model]').value.trim();
          if (!m) return;
          models[m] = { in: Number(tr.querySelector('[name=in]').value || 0), out: Number(tr.querySelector('[name=out]').value || 0), cache: Number(tr.querySelector('[name=cache]').value || 0) };
        });
        try { M.pricing = Object.assign(await post('/api/management/pricing', { models }), { editable: true }); toast(w('saved')); await loadMgmt(); }
        catch (e) { toast(errMsg(e)); }
      }
    });
  }

  // ── Value card in the task detail ─────────────────────────────────────────
  const V = { editing: false };
  function storeOf(job){
    try { if (typeof _cronOwnerProfileName === 'function') return _cronOwnerProfileName(job) || 'default'; } catch (_e) {}
    return job.owner_profile || 'default';
  }
  function jobCardHtml(job){
    if (!job || !job.id) return '';
    const store = storeOf(job);
    setTimeout(() => mountJob(job.id, store), 0);
    return `<div class="detail-card om-value-card" id="omValueCard" data-job="${H(job.id)}" data-store="${H(store)}"><div class="detail-card-title">${H(w('value'))}</div><div class="om-muted om-small">…</div></div>`;
  }
  async function mountJob(jobId, store){
    const card = $id('omValueCard');
    if (!card || card.dataset.job !== String(jobId)) return;
    let d;
    try { d = await call('/api/management/job?job_id=' + encodeURIComponent(jobId) + '&store=' + encodeURIComponent(store) + '&period=28'); }
    catch (e) { card.remove(); return; }
    if (!$id('omValueCard') || card.dataset.job !== String(jobId)) return;
    paintJob(card, d);
  }
  function paintJob(card, d){
    const v = d.value;
    const raw = d.raw_value || {};
    const label = !v ? 'missing' : v.unknown ? 'unknown' : v.confidence === 'confirmed' ? 'confirmed' : (v.source === 'ai_estimate' ? 'ai_estimate' : 'estimated');
    const runs = d.runs || [];
    const ok = runs.filter(r => r.status === 'ok');
    const saved = ok.reduce((a, r) => a + (r.saved_minutes || 0), 0);
    const cost = runs.reduce((a, r) => a + (r.ai_cost_eur || 0), 0);
    const unpriced = runs.some(r => r.cost_source === 'unknown');
    const teamSel = `<label class="om-field">${H(w('team_of_task'))}<select name="team" data-om-job-team>${'<option value="">' + H(w('none')) + '</option>' + (d.teams || []).map(t => `<option value="${H(t.key)}" ${((v && v.team) || raw.team || d.job.team) === t.key ? 'selected' : ''}>${H(t.name)}</option>`).join('')}</select></label>`;
    let inner;
    if (!v || V.editing) {
      const cur = v || {};
      inner = `<p class="detail-hint" style="margin:0 0 6px">${H(w('value_intro'))}</p>
        <form class="om-value-form" data-om-value-form>
          <label class="om-field wide">${H(w('task_label'))}<input name="task" maxlength="120" value="${H(cur.task || '')}" placeholder="${H(w('task_ph'))}"></label>
          <label class="om-field">${H(w('minutes_before'))}<input name="before" type="number" min="0" max="6000" value="${H(cur.before_minutes ?? '')}"></label>
          <label class="om-field">${H(w('minutes_now'))}<input name="now" type="number" min="0" max="6000" value="${H(cur.review_minutes ?? '')}"></label>
          <label class="om-field" title="${H(w('per_hint'))}">${H(w('per_label'))}<select name="per">${['run', 'day', 'week'].map(p => `<option value="${p}" ${(cur.per || 'run') === p ? 'selected' : ''}>${H(w('per_' + p + '_opt'))}</option>`).join('')}</select></label>
          ${teamSel}
          <label class="om-field wide" style="flex-direction:row;align-items:center;gap:8px;font-weight:500"><input type="checkbox" name="unknown" style="min-height:0;width:16px" ${cur.unknown ? 'checked' : ''}> ${H(w('unknown'))}</label>
          <label class="om-field wide" data-om-unknown-reason ${cur.unknown ? '' : 'hidden'}>${H(w('unknown_reason'))}<input name="reason" maxlength="200" value="${H(cur.unknown_reason || '')}"></label>
          <div class="om-value-actions" style="grid-column:1/-1"><button type="submit" class="sm-btn primary">${H(w('save'))}</button>${v ? `<button type="button" class="sm-btn" data-om-value-cancel>${H(w('cancel'))}</button>` : `<button type="button" class="sm-btn" data-om-value-ask>✨ ${H(lang() === 'en' ? 'Ask the Super Agent' : 'Vraag de Super Agent')}</button>`}</div>
        </form>`;
    } else if (v.unknown) {
      inner = `<p class="om-small om-muted" style="margin:4px 0">${H(v.unknown_reason || '')}</p>${teamSel}<div class="om-value-actions"><button type="button" class="sm-btn" data-om-value-edit>${H(w('edit'))}</button></div>`;
    } else {
      const per = Math.max(0, (v.before_minutes || 0) - (v.review_minutes || 0));
      inner = `${v.task ? `<p class="om-small" style="margin:2px 0 4px"><strong>${H(v.task)}</strong></p>` : ''}
        <div class="om-value-figures"><div><span>${H(w('before'))}</span><strong>${H(v.before_minutes)} ${H(w('min'))}</strong></div><div><span>${H(w('now'))}</span><strong>${H(v.review_minutes || 0)} ${H(w('min'))}</strong></div><div><span>${H(w('saves'))} ${H(w('per_' + (v.per || 'run') + '_opt'))}</span><strong>${H(per)} ${H(w('min'))}</strong></div></div>
        <div class="om-small"><strong>${H(w('measured'))}:</strong> ${H(ok.length)} ${H(w('measured_runs'))}${runs.length - ok.length ? ', ' + H(runs.length - ok.length) + ' ' + H(w('failed_runs')) : ''} ${H(w('in_period'))} · ${H(hrs(saved))}${cost ? ' · ' + H(eur(cost)) + ' AI' : (unpriced ? ' · AI ?' : '')}${d.rate != null && saved ? ' · ' + H(eur(saved / 60 * d.rate - cost)) : ''}</div>
        ${label !== 'confirmed' ? `<div class="om-confirm"><span>${H(w('confirm_q'))}</span>${['yes', 'less', 'more'].map(a => `<button type="button" class="sm-btn" data-om-confirm="${a}">${H(w(a))}</button>`).join('')}</div>` : ''}
        <div style="margin-top:10px">${teamSel}</div>
        <div class="om-value-actions"><button type="button" class="sm-btn" data-om-value-edit>${H(w('edit'))}</button></div>`;
    }
    card.innerHTML = `<div class="detail-card-title detail-card-title-row"><span>${H(w('value'))}</span><span class="om-badge ${H(label)}">${H(w('label_' + label))}</span></div>${inner}`;
    card._omData = d;
    if (!card.dataset.omBound) bindJobCard(card);
  }
  function bindJobCard(card){
    card.dataset.omBound = '1';
    const ids = () => ({ job_id: card.dataset.job, store: card.dataset.store });
    const reload = async () => { V.editing = false; await mountJob(card.dataset.job, card.dataset.store); };
    card.addEventListener('change', async ev => {
      const el = ev.target;
      if (el.name === 'unknown') { const r = card.querySelector('[data-om-unknown-reason]'); if (r) r.hidden = !el.checked; }
      if (el.hasAttribute('data-om-job-team') && !card.querySelector('[data-om-value-form]')) {
        try { await post('/api/value/job', Object.assign(ids(), { action: 'team', team: el.value })); toast(w('saved')); } catch (e) { toast(errMsg(e)); }
      }
    });
    card.addEventListener('click', async ev => {
      const b = ev.target.closest('button');
      if (!b) return;
      if (b.hasAttribute('data-om-value-edit')) { V.editing = true; paintJob(card, card._omData); return; }
      if (b.hasAttribute('data-om-value-cancel')) { V.editing = false; paintJob(card, card._omData); return; }
      if (b.hasAttribute('data-om-value-ask')) { const job = card._omData && card._omData.job; await startChat(w('chat_prompt_value', { task: (job && job.name) || '' })); return; }
      if (b.dataset.omConfirm) { try { await post('/api/value/job', Object.assign(ids(), { action: 'confirm', answer: b.dataset.omConfirm })); toast(w('value_saved')); await reload(); } catch (e) { toast(errMsg(e)); } }
    });
    card.addEventListener('submit', async ev => {
      ev.preventDefault();
      const form = ev.target;
      const fd = new FormData(form);
      const unknown = !!fd.get('unknown');
      const before = Number(fd.get('before') || 0);
      if (!unknown && !(before > 0)) { toast(w('need_minutes')); return; }
      const value = unknown ? { unknown: true, unknown_reason: String(fd.get('reason') || '').trim() || '·', task: String(fd.get('task') || '') }
        : { task: String(fd.get('task') || ''), before_minutes: before, review_minutes: Number(fd.get('now') || 0), per: String(fd.get('per') || 'run'), source: 'owner', confidence: 'confirmed' };
      if (fd.get('team')) value.team = String(fd.get('team'));
      try { await post('/api/value/job', Object.assign(ids(), { value })); toast(w('value_saved')); await reload(); }
      catch (e) { toast(errMsg(e)); }
    });
  }

  // ── Bot responsibilities: minutes before / now / times per week ──────────
  function dutyFieldsHtml(d){
    d = d || {};
    return `<div class="om-duty-value">
      <label for="botDutyMinBefore">${H(w('duty_minutes_before'))}<input id="botDutyMinBefore" type="number" min="0" max="6000" value="${H(d.minutes_before ?? '')}"></label>
      <label for="botDutyMinNow">${H(w('duty_minutes_now'))}<input id="botDutyMinNow" type="number" min="0" max="6000" value="${H(d.minutes_now ?? '')}"></label>
      <label for="botDutyTimes">${H(w('duty_times'))}<input id="botDutyTimes" type="number" min="0" max="500" step="0.5" value="${H(d.times_per_week ?? '')}"></label>
    </div>`;
  }
  function dutyFromForm(row){
    const num = id => { const el = $id(id); if (!el || el.value === '') return null; const n = Number(el.value); return isFinite(n) ? n : null; };
    const before = num('botDutyMinBefore'), now = num('botDutyMinNow'), times = num('botDutyTimes');
    if (before != null) { row.minutes_before = before; row.value_source = 'owner'; row.value_confidence = 'confirmed'; }
    if (now != null) row.minutes_now = now;
    if (times != null) row.times_per_week = times;
    return row;
  }
  function dutyChipHtml(d){
    if (!d || !d.minutes_before) return '';
    const per = Math.max(0, d.minutes_before - (d.minutes_now || 0));
    const week = per * (d.times_per_week || 0);
    const text = week ? w('duty_saves', { h: nf(1).format(week / 60) }) : `${d.minutes_before} → ${d.minutes_now || 0} ${w('min')}`;
    return `<span class="bot-duty-chip bot-duty-value">⏱ ${H(text)}</span>`;
  }
  function servesFieldHtml(p){
    const serves = ((p && p.bot && p.bot.serves) || []).join(',');
    return `<label class="bot-editor-wide" for="botServes">${H(w('serves'))}<select id="botServes" multiple size="1" data-om-serves style="display:none"></select><input type="hidden" id="botServesValue" value="${H(serves)}"><span id="botServesBox" class="om-inline-form"></span><span class="bot-field-hint">${H(w('serves_hint'))}</span></label>`;
  }
  async function mountServes(p){
    const box = $id('botServesBox');
    if (!box) return;
    let structure;
    try { structure = await call('/api/org/structure'); } catch (_e) { structure = null; }
    const current = (($id('botServesValue') || {}).value || '').split(',').filter(Boolean);
    const teams = structure ? Object.values(structure.teams || {}) : [];
    if (!teams.length) { box.innerHTML = `<span class="om-muted om-small">${H(current.join(', ') || w('nothing_yet'))}</span>`; return; }
    const depts = structure.departments || {};
    box.innerHTML = `<select class="om-select" id="botServesSelect" aria-label="${H(w('serves'))}"><option value="">${H(w('none'))}</option>${teams.sort((a, b) => a.name.localeCompare(b.name)).map(t => `<option value="${H(t.key)}" ${current[0] === t.key ? 'selected' : ''}>${H(((depts[t.department] || {}).name || t.department) + ' · ' + t.name)}</option>`).join('')}</select>`;
    $id('botServesSelect').addEventListener('change', async ev => {
      if (!p) return;
      try {
        const res = await post('/api/profile/appearance', { name: p.name, revision: p.bot_revision || 0, bot: { serves: ev.target.value ? [ev.target.value] : [] } });
        if (res && typeof res.bot_revision === 'number') p.bot_revision = res.bot_revision;
        toast(w('saved'));
      } catch (e) { toast(errMsg(e)); }
    });
  }

  // ── Value fields in the new-task form ─────────────────────────────────────
  function createFieldsHtml(){
    return `<div class="detail-form-row" id="cronFormValueRow">
      <label>${H(w('value'))}</label>
      <div class="om-value-form" style="margin-top:0">
        <label class="om-field">${H(w('minutes_before'))}<input id="cronFormValueBefore" type="number" min="1" max="6000" placeholder="45"></label>
        <label class="om-field">${H(w('minutes_now'))}<input id="cronFormValueNow" type="number" min="0" max="6000" placeholder="5"></label>
        <label class="om-field" title="${H(w('per_hint'))}">${H(w('per_label'))}<select id="cronFormValuePer">${['run', 'day', 'week'].map(p => `<option value="${p}">${H(w('per_' + p + '_opt'))}</option>`).join('')}</select></label>
        <label class="om-field wide">${H(w('task_label'))}<input id="cronFormValueTask" maxlength="120" placeholder="${H(w('task_ph'))}"></label>
        <label class="om-field wide" style="flex-direction:row;align-items:center;gap:8px;font-weight:500"><input type="checkbox" id="cronFormValueUnknown" style="min-height:0;width:16px" onchange="document.getElementById('cronFormValueBefore').disabled=this.checked;document.getElementById('cronFormValueNow').disabled=this.checked"> ${H(w('unknown'))}</label>
      </div>
      <div class="detail-form-hint">${H(w('value_intro'))}</div>
    </div>`;
  }
  function createValueFromForm(){
    const row = $id('cronFormValueRow');
    if (!row) return null;
    const unknown = !!($id('cronFormValueUnknown') || {}).checked;
    const task = String(($id('cronFormValueTask') || {}).value || '').trim();
    if (unknown) return { value: { unknown: true, unknown_reason: lang() === 'en' ? 'Not known when created' : 'Nog onbekend bij aanmaken', task } };
    const before = Number(($id('cronFormValueBefore') || {}).value || 0);
    if (!(before > 0)) return { error: w('need_minutes') };
    return { value: { before_minutes: before, review_minutes: Number(($id('cronFormValueNow') || {}).value || 0), per: String(($id('cronFormValuePer') || {}).value || 'run'), task, source: 'owner', confidence: 'confirmed' } };
  }

  // ── Chip under a bot chat: which responsibility it covered ───────────────
  // The collector labels finished chats (api/value_tracking.label_chats). The
  // person who had the chat confirms or corrects it here; nobody else can.
  const C = { sid: '', data: null, editing: false };
  function chipBox(){
    let box = $id('omChatValue');
    const wrap = $id('composerWrap');
    if (!box && wrap && wrap.parentNode) { box = document.createElement('div'); box.id = 'omChatValue'; box.className = 'om-chat-value'; box.hidden = true; wrap.parentNode.insertBefore(box, wrap); }
    return box;
  }
  function paintChip(){
    const box = chipBox();
    if (!box) return;
    const d = C.data;
    if (!d || !d.duties || !d.duties.length || d.label_state === 'none' || d.label_state === 'skipped') { box.hidden = true; box.innerHTML = ''; return; }
    box.hidden = false;
    const final = d.label_state === 'confirmed' || d.label_state === 'removed';
    if (C.editing) {
      box.innerHTML = `<span>${H(w('chip_which'))}</span><select class="om-select" data-om-chip-duty><option value="">${H(w('chip_none'))}</option>${d.duties.map(x => `<option value="${H(x.title)}" ${x.title === d.duty ? 'selected' : ''}>${H(x.title)} · ${x.saves} ${H(w('min'))}</option>`).join('')}</select><button type="button" class="sm-btn primary" data-om-chip-save>${H(w('save'))}</button>`;
      return;
    }
    const text = d.duty ? w('chip_logged', { d: d.duty, m: d.saved_minutes || 0 }) : w('chip_no_duty');
    box.innerHTML = `<span class="om-chip-text">⏱ ${H(text)}</span>${final ? `<span class="om-badge confirmed">${H(w('label_confirmed'))}</span>` : `<button type="button" class="sm-btn" data-om-chip-yes>${H(w('yes'))}</button>`}<button type="button" class="sm-btn" data-om-chip-edit>${H(w('chip_wrong'))}</button>`;
  }
  async function refreshChip(){
    const sid = (window.S && S.session && S.session.session_id) || '';
    if (sid === C.sid) return;
    C.sid = sid; C.data = null; C.editing = false; paintChip();
    if (!sid) return;
    try { const d = await call('/api/value/chat?session_id=' + encodeURIComponent(sid)); if (C.sid === sid) { C.data = d; paintChip(); } } catch (_e) {}
  }
  async function labelChip(duty){
    try { const r = await post('/api/value/chat', { session_id: C.sid, duty }); C.data = Object.assign({}, C.data, { duty: r.duty || '', saved_minutes: r.saved_minutes || 0, label_state: duty ? 'confirmed' : 'removed' }); C.editing = false; paintChip(); toast(w('saved')); }
    catch (e) { toast(errMsg(e)); }
  }
  document.addEventListener('click', ev => {
    const b = ev.target.closest('#omChatValue button');
    if (!b) return;
    if (b.hasAttribute('data-om-chip-yes')) labelChip(C.data && C.data.duty || '');
    else if (b.hasAttribute('data-om-chip-edit')) { C.editing = true; paintChip(); }
    else if (b.hasAttribute('data-om-chip-save')) labelChip(($id('omChatValue').querySelector('[data-om-chip-duty]') || {}).value || '');
  });
  setInterval(() => { refreshChip().catch(() => {}); }, 2500);

  // ── Panel hooks ───────────────────────────────────────────────────────────
  window.SPOrg = { load: async () => { bindOrg(); await loadOrg(); }, refreshNav };
  window.SPManagement = { load: async () => { bindMgmt(); await loadMgmt(); } };
  window.SPValue = { createFieldsHtml, createValueFromForm, jobCardHtml, dutyFieldsHtml, dutyFromForm, dutyChipHtml, servesFieldHtml, mountServes };

  function boot(){ setTimeout(() => { refreshNav().catch(() => {}); }, 1200); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
