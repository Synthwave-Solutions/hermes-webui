/* Workplace (10 Nov 2026): what is yours, your team's and the organisation's.

   Two parts, both views over data the other screens own:
     SPScope      who you are in the structure (teams, department, role) and
                  the lens "mine | my team | my department | organisation"
                  that any list can reuse.
     SPWorkplace  the Studio landing "Overzicht": use cases, scheduled tasks,
                  bots, playbooks, prompts and backlog in one place, grouped
                  per kind, per team (under its department) or per person.
   Nothing is stored here except the chosen lens and grouping (localStorage).
   Rights stay on the server: every list is what the routes already return. */
(function(){
  'use strict';
  const NL = {
    findings:'Voor je uitgezocht', findings_empty:'Zodra een bot iets voor je vindt, verschijnt de update hier.',
    findings_read:'Lees update', findings_close:'Sluit update', findings_chat:'Bespreek in chat', findings_older:'Eerdere updates ({n})',
    recent_chats:'Recente gesprekken', recent_runs:'Laatst uitgevoerde taken', no_chats:'Nog geen recente gesprekken.', no_runs:'Nog geen uitgevoerde taken in deze weergave.',
    projects:'Projecten', chart:'Botorganogram', agenda:'Taakagenda', navigate:'Alle onderdelen',
    title: 'Overzicht', morning: 'Goedemorgen', afternoon: 'Goedemiddag', evening: 'Goedenavond',
    intro: 'Alles wat van jou is, van je team en van de organisatie op één plek.',
    l_mine: 'Van mij', l_team: 'Mijn team', l_teams: 'Mijn teams', l_dept: 'Mijn afdeling', l_depts: 'Mijn afdelingen', l_org: 'Organisatie', l_all: 'Alles',
    lens: 'Toon', group: 'Groepeer', g_kind: 'Per soort', g_team: 'Per team', g_person: 'Per persoon',
    k_usecase: 'Use cases', k_task: 'Geplande taken', ks_task: 'Taken', k_bot: 'Bots', k_playbook: 'Playbooks', k_prompt: 'Prompts', k_backlog: 'Backlog',
    r_admin: 'Beheerder', r_dept: 'Afdelingsbeheerder', r_lead: 'Teamlead', r_member: 'Lid',
    no_team: 'Geen team', no_owner: 'Zonder eigenaar', no_dept: 'Overig', not_placed: 'Nog niet ingedeeld in een team',
    all: 'Alles bekijken', more: 'Toon nog {n}', less: 'Minder tonen', untitled: 'Naamloos',
    s_on: 'Actief', s_paused: 'Gepauzeerd', s_error: 'Fout', s_done: 'Afgerond', assistant: 'Persoonlijke assistent',
    lead: 'Teamlead', members: '{n} leden', member_one: '1 lid', you: 'jij', by: 'van {p}',
    empty_h: 'Hier staat nog niets', empty_mine: 'Begin met een use case: vertel over je werk en de Super Agent zoekt uit wat hij kan overnemen.',
    empty_scope: 'In deze weergave staat nog niets. Kies een andere weergave of maak een use case.',
    empty_peek: 'Bekijk {l}', kpi_hint: '{k} openen',
    loading: 'Laden…', failed: 'Laden is niet gelukt. Probeer het opnieuw.', retry: 'Opnieuw', people: 'Mensen', nothing: 'Nog niets',
    p_discover: 'Ontdekken', p_design: 'Inrichten', p_playbook: 'Bouwplan', p_build: 'Bouwen', p_measure: 'Meten',
    role_consultant: 'Agentic Consultant', role_developer: 'Agentic Developer', role_reader: 'leest mee',
    role_consultant_does: 'brengt de processen in kaart, kiest en prioriteert de use cases, traint en draagt over.', role_developer_does: 'bouwt en onderhoudt de automations in dit platform.',
    partner_team: 'Team van Synthwave', partner_team_sub: 'Zij werken met jullie aan de use cases in deze omgeving.',
    hrs_title: 'Uren deze maand', hrs_package: 'Pakket', hrs_allocated: 'Maanduren', hrs_used: 'Verbruikt', hrs_left: 'Resterend', hrs_unknown: 'Nog niet bekend',
    hrs_basis: 'Basis {a} uur, extra blokken {b} uur', hrs_from_card: 'Uit strippenkaart gebruikt: {h} uur', hrs_uncovered: '{h} uur valt buiten de maanduren en de strippenkaarten.',
    hrs_closed: 'Maand afgesloten', hrs_cards: 'Strippenkaarten', hrs_card: '{l}: {r} van {p} uur over', hrs_card_until: 'geldig tot {d}', hrs_card_expired: 'verlopen op {d}', hrs_card_used: 'opgebruikt', hrs_card_voided: 'vervallen',
    hrs_as_of: 'Bijgewerkt tot', hrs_team: 'Team van Synthwave', hrs_week: 'uur per week', hrs_role: 'Rol', hrs_h: 'uur',
    hrs_off: 'De uren zijn in deze omgeving nog niet gekoppeld aan de Cloud.', hrs_down: 'De uren zijn nu niet op te halen. Probeer het later opnieuw.',
    hrs_none: 'Voor deze maand zijn nog geen uren toegewezen.', hrs_until: 'loopt tot', hrs_change: 'Wijziging van pakket gepland'
  };
  const EN = {
    findings:'Findings for you', findings_empty:'When a bot finds something for you, its update appears here.',
    findings_read:'Read update', findings_close:'Close update', findings_chat:'Discuss in chat', findings_older:'Earlier updates ({n})',
    recent_chats:'Recent conversations', recent_runs:'Recently run tasks', no_chats:'No recent conversations yet.', no_runs:'No task runs in this view yet.',
    projects:'Projects', chart:'Bot org chart', agenda:'Task calendar', navigate:'All destinations',
    title: 'Overview', morning: 'Good morning', afternoon: 'Good afternoon', evening: 'Good evening',
    intro: 'Everything that is yours, your team\'s and the organisation\'s in one place.',
    l_mine: 'Mine', l_team: 'My team', l_teams: 'My teams', l_dept: 'My department', l_depts: 'My departments', l_org: 'Organisation', l_all: 'Everything',
    lens: 'Show', group: 'Group', g_kind: 'By kind', g_team: 'By team', g_person: 'By person',
    k_usecase: 'Use cases', k_task: 'Scheduled tasks', ks_task: 'Tasks', k_bot: 'Bots', k_playbook: 'Playbooks', k_prompt: 'Prompts', k_backlog: 'Backlog',
    r_admin: 'Admin', r_dept: 'Department admin', r_lead: 'Team lead', r_member: 'Member',
    no_team: 'No team', no_owner: 'No owner', no_dept: 'Other', not_placed: 'Not placed in a team yet',
    all: 'View all', more: 'Show {n} more', less: 'Show fewer', untitled: 'Untitled',
    s_on: 'Active', s_paused: 'Paused', s_error: 'Failing', s_done: 'Completed', assistant: 'Personal assistant',
    lead: 'Team lead', members: '{n} members', member_one: '1 member', you: 'you', by: 'by {p}',
    empty_h: 'Nothing here yet', empty_mine: 'Start with a use case: tell about your work and the Super Agent works out what it can take over.',
    empty_scope: 'Nothing in this view yet. Choose another view or create a use case.',
    empty_peek: 'View {l}', kpi_hint: 'Open {k}',
    loading: 'Loading…', failed: 'Loading failed. Try again.', retry: 'Retry', people: 'People', nothing: 'Nothing yet',
    p_discover: 'Discover', p_design: 'Design', p_playbook: 'Build plan', p_build: 'Build', p_measure: 'Measure',
    role_consultant: 'Agentic Consultant', role_developer: 'Agentic Developer', role_reader: 'read only',
    role_consultant_does: 'maps the processes, chooses and prioritises the use cases, trains and hands over.', role_developer_does: 'builds and maintains the automations in this platform.',
    partner_team: 'Synthwave team', partner_team_sub: 'They work with you on the use cases in this environment.',
    hrs_title: 'Hours this month', hrs_package: 'Package', hrs_allocated: 'Monthly hours', hrs_used: 'Used', hrs_left: 'Remaining', hrs_unknown: 'Not known yet',
    hrs_basis: 'Base {a} hours, extra blocks {b} hours', hrs_from_card: 'Used from hour card: {h} hours', hrs_uncovered: '{h} hours fall outside the monthly hours and the hour cards.',
    hrs_closed: 'Month closed', hrs_cards: 'Hour cards', hrs_card: '{l}: {r} of {p} hours left', hrs_card_until: 'valid until {d}', hrs_card_expired: 'expired on {d}', hrs_card_used: 'used up', hrs_card_voided: 'withdrawn',
    hrs_as_of: 'Updated until', hrs_team: 'Synthwave team', hrs_week: 'hours per week', hrs_role: 'Role', hrs_h: 'hours',
    hrs_off: 'The hours are not linked to the Cloud in this environment yet.', hrs_down: 'The hours cannot be fetched right now. Try again later.',
    hrs_none: 'No hours have been allocated for this month yet.', hrs_until: 'runs until', hrs_change: 'Package change planned'
  };
  const lang = () => ((document.documentElement.lang || 'nl').toLowerCase().startsWith('en') ? 'en' : 'nl');
  const w = (k, v) => { let s = (lang() === 'en' ? EN : NL)[k] || NL[k] || k; if (v) for (const [a, b] of Object.entries(v)) s = s.replace('{' + a + '}', b); return s; };
  const H = v => (typeof esc === 'function' ? esc(String(v ?? '')) : String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])));
  const call = p => api(p, { timeoutToast: false });
  const norm = e => String(e || '').trim().toLowerCase();
  const initials = s => String(s || '?').replace(/@.*/, '').split(/[.\s_-]+/).filter(Boolean).slice(0, 2).map(x => x[0].toUpperCase()).join('') || '?';
  const hue = v => { let h = 0; for (const c of String(v || '')) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
  const store = { get: (k, d) => { try { return localStorage.getItem(k) || d; } catch (_e) { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (_e) {} } };
  const KINDS = ['usecase', 'task', 'bot', 'playbook', 'prompt', 'backlog'];

  // ── Scope: who am I in the structure ───────────────────────────────────────
  let ctxCache = null, ctxAt = 0, ctxLoading = null, ctxEarly = null;
  // The structure arrives in two steps. Who you are and the team names are quick. The chart
  // (members, faces, the team of each scheduled task) is slow, so the first paint does not wait for it.
  function buildCtx(me, pr, chart){
      const c = { email: norm(me.email), scope: me.scope || 'none', canView: !!me.can_view, canManage: !!me.can_manage,
                  leadTeams: new Set(me.lead_teams || []), memberTeams: new Set(me.member_teams || []), adminDepts: new Set(me.departments || []),
                  teams: new Map(), depts: new Map(), people: new Map(), jobTeam: new Map(), promptRows: pr ? (pr.prompts || []) : [], chart,
                  partner: me.partner && me.partner.role ? me.partner : null };
      c.myTeams = new Set([...c.leadTeams, ...c.memberTeams]);
      for (const d of (pr && pr.departments) || []) c.depts.set(d.key, { key: d.key, name: d.name || d.key });
      for (const t of (pr && pr.teams) || []) c.teams.set(t.key, { key: t.key, name: t.name || t.key, department: t.department || t.key.split('/')[0], lead: '', members: [] });
      for (const d of (chart && chart.departments) || []) {
        if (!c.depts.has(d.key)) c.depts.set(d.key, { key: d.key, name: d.name || d.key });
        for (const t of d.teams || []) {
          const row = c.teams.get(t.key) || { key: t.key, name: t.name || t.key, department: t.department || d.key };
          row.lead = norm(t.lead); row.members = (t.members || []).map(norm).filter(Boolean);
          c.teams.set(t.key, row);
          for (const j of t.job_list || []) { c.jobTeam.set((j.store || 'default') + ':' + j.id, t.key); }
        }
      }
      for (const [email, p] of Object.entries((chart && chart.people) || {})) c.people.set(norm(email), { email: norm(email), title: p.title || '', avatar_url: p.avatar_url || '' });
      c.myDepts = new Set([...c.adminDepts, ...[...c.myTeams].map(k => deptKey(c, k))].filter(Boolean));
      return c;
  }
  async function loadCtx(force){
    if (!force && ctxCache && Date.now() - ctxAt < 60000) return ctxCache;
    if (ctxLoading) return ctxLoading;
    const base = Promise.all([call('/api/org/structure/me').catch(() => ({})), call('/api/studio/prompts').catch(() => null)]);
    ctxEarly = base.then(([me, pr]) => buildCtx(me, pr, null));
    ctxLoading = base.then(async ([me, pr]) => {
      const chart = me && me.can_view ? await call('/api/org/chart').catch(() => null) : null;
      ctxCache = buildCtx(me, pr, chart); ctxAt = Date.now();
      return ctxCache;
    });
    try { return await ctxLoading; } finally { ctxLoading = null; }
  }
  function deptKey(c, teamKey){ const t = c.teams.get(teamKey); return t ? t.department : String(teamKey || '').split('/')[0]; }
  function teamName(c, key){ return (c.teams.get(key) || {}).name || (key ? String(key).split('/').pop() : w('no_team')); }
  function deptName(c, key){ return (c.depts.get(key) || {}).name || key || w('no_dept'); }
  function personName(email){
    const partner = Partners.get(email);
    if (partner && partner.name) return partner.name;
    const local = String(email || '').replace(/@.*/, '');
    return local.split(/[._-]+/).filter(Boolean).map(p => p[0].toUpperCase() + p.slice(1)).join(' ') || w('no_owner');
  }
  // The team a person is shown under: where they lead first, else their first team.
  function primaryTeam(c, email){
    email = norm(email);
    if (!email) return '';
    let member = '';
    for (const t of c.teams.values()) {
      if (t.lead === email) return t.key;
      if (!member && t.members.includes(email)) member = t.key;
    }
    return member;
  }
  function roles(c){
    const out = [];
    if (c.partner) out.push({ label: Partners.label(c.partner.role), cls: 'partner' });
    if (c.scope === 'all') out.push({ label: w('r_admin'), cls: 'admin' });
    else if (c.scope === 'departments') out.push({ label: w('r_dept') + ' ' + [...c.adminDepts].map(k => deptName(c, k)).join(', '), cls: 'admin' });
    if (c.leadTeams.size) out.push({ label: w('r_lead') + ' ' + [...c.leadTeams].map(k => teamName(c, k)).join(', '), cls: 'lead' });
    const only = [...c.memberTeams].filter(k => !c.leadTeams.has(k));
    if (only.length) out.push({ label: w('r_member') + ' ' + only.map(k => teamName(c, k)).join(', '), cls: '' });
    return out;
  }
  function lenses(c){
    const out = ['mine'];
    if (c.myTeams.size) out.push('team');
    // The department lens only earns its place when it shows more than the team lens.
    const deptTeams = [...c.teams.values()].filter(t => c.myDepts.has(t.department)).map(t => t.key);
    if (c.myDepts.size && deptTeams.some(k => !c.myTeams.has(k))) out.push('dept');
    out.push('org');
    return out;
  }
  function lensLabel(c, lens){
    if (lens === 'mine') return w('l_mine');
    if (lens === 'team') return w(c.myTeams.size > 1 ? 'l_teams' : 'l_team');
    if (lens === 'dept') return w(c.myDepts.size > 1 ? 'l_depts' : 'l_dept');
    return w(c.scope === 'all' ? 'l_org' : 'l_all');
  }
  function match(c, it, lens){
    if (lens === 'mine') return !!it.owner && norm(it.owner) === c.email;
    if (lens === 'team') return !!it.team && c.myTeams.has(it.team);
    if (lens === 'dept') return !!it.team && c.myDepts.has(deptKey(c, it.team));
    return true;
  }
  function getLens(c, surface, fallback){
    const saved = store.get('sp-lens-' + surface, fallback || 'org');
    return lenses(c).includes(saved) ? saved : (fallback && lenses(c).includes(fallback) ? fallback : 'org');
  }
  function barHtml(c, surface, items, current){
    const ls = lenses(c);
    const counts = Object.fromEntries(ls.map(l => [l, items.filter(it => match(c, it, l)).length]));
    return `<div class="om-seg sp-lens" role="group" aria-label="${H(w('lens'))}">${ls.map(l => `<button type="button" aria-pressed="${l === current}" data-sp-lens="${l}" data-sp-lens-surface="${H(surface)}">${H(lensLabel(c, l))}<span class="sp-lens-n">${counts[l]}</span></button>`).join('')}</div>`;
  }
  // Department > team, the viewer's own teams first, "no team" last.
  function groupByTeam(c, items){
    const by = new Map();
    for (const it of items) { const k = it.team || ''; if (!by.has(k)) by.set(k, []); by.get(k).push(it); }
    const keys = [...by.keys()].sort((a, b) => (!a) - (!b) || (c.myTeams.has(b) - c.myTeams.has(a)) || deptName(c, deptKey(c, a)).localeCompare(deptName(c, deptKey(c, b))) || teamName(c, a).localeCompare(teamName(c, b)));
    return keys.map(k => ({ key: k, name: k ? teamName(c, k) : w('no_team'), department: k ? deptName(c, deptKey(c, k)) : '', items: by.get(k) }));
  }
  document.addEventListener('click', ev => {
    const b = ev.target.closest && ev.target.closest('[data-sp-lens]');
    if (!b) return;
    const surface = b.dataset.spLensSurface || '';
    store.set('sp-lens-' + surface, b.dataset.spLens);
    document.dispatchEvent(new CustomEvent('sp-lens-change', { detail: { surface, lens: b.dataset.spLens } }));
  });
  // ── Partners: the supplier's staff assigned to this installation ───────────
  // One small shared store. Studio, the backlog and the organisation screens fill it from
  // what the server already sends them and read the badge and the team block from here.
  const Partners = {
    rows: [],
    set(list){ if (Array.isArray(list)) Partners.rows = list.filter(p => p && p.email).map(p => ({ email: norm(p.email), name: p.name || '', role: p.role || '', org: p.org || 'synthwave' })); },
    list(){ return Partners.rows.slice(); },
    get(email){ const e = norm(email); return e ? Partners.rows.find(p => p.email === e) || null : null; },
    // The Cloud assigns consultants and developers. An older stored assignment with another role only reads.
    // The one place where a role id becomes a name: `consultant` is the Agentic Consultant, `developer` the
    // Agentic Developer (role_* above, Dutch and English). Ids and API fields keep their own names.
    short(role){ return ['consultant', 'developer'].includes(role) ? w('role_' + role) : role === 'qa' ? w('role_reader') : ''; },
    label(role){ const name = Partners.short(role); return name ? 'Synthwave ' + name : ''; },
    // Who can be named on a use case or take an idea: the people who work along.
    workers(){ return Partners.rows.filter(p => ['consultant', 'developer'].includes(p.role)); },
    name(p){ return p.name || String(p.email).replace(/@.*/, '').split(/[._-]+/).filter(Boolean).map(x => x[0].toUpperCase() + x.slice(1)).join(' '); },
    // Badge for a person (by address) or for a role name. Empty when it is not a partner.
    badge(who){
      const role = ['consultant', 'developer', 'qa'].includes(who) ? who : (Partners.get(who) || {}).role;
      return role ? `<span class="om-badge sp-partner">${H(Partners.label(role))}</span>` : '';
    },
    // "Team van Synthwave": who is assigned. `compact` is the sidebar form.
    teamHtml(compact){
      if (!Partners.rows.length) return '';
      const rows = Partners.rows.map(p => `<div class="sp-partner-row"><span class="om-face ${compact ? 'st-face-xs' : ''}" style="--h:${hue(p.email)}" aria-hidden="true">${H(initials(Partners.name(p)))}</span><span class="sp-partner-name">${H(Partners.name(p))}</span>${compact ? `<span class="sp-partner-role">${H(Partners.short(p.role))}</span>` : Partners.badge(p.role)}</div>`).join('');
      return compact ? `<div class="om-side-label">${H(w('partner_team'))}</div><div class="sp-partner-list compact">${rows}</div>`
        : `<section class="wp-card sp-partners" aria-label="${H(w('partner_team'))}"><div class="wp-card-head"><h3>${H(w('partner_team'))}</h3><span class="om-muted om-small">${H(w('partner_team_sub'))}</span></div><div class="sp-partner-list">${rows}</div><ul class="sp-partner-roles">${['consultant', 'developer'].filter(r => Partners.rows.some(p => p.role === r)).map(r => `<li><strong>${H(Partners.short(r))}:</strong> ${H(w('role_' + r + '_does'))}</li>`).join('')}</ul></section>`;
    }
  };
  window.SPPartners = Partners;

  window.SPScope = { load: loadCtx, lenses, lensLabel, match, getLens, barHtml, groupByTeam, teamName, deptName, deptKey, personName, primaryTeam, roles,
    face: (c, email, cls) => faceHtml(c, email, cls) };

  function faceHtml(c, email, cls){
    const p = (c && c.people.get(norm(email))) || {};
    return `<span class="om-face ${cls || ''}" style="--h:${hue(email)}" title="${H(personName(email))}">${p.avatar_url ? `<img src="${H(p.avatar_url)}" alt="" loading="lazy">` : H(initials(email))}</span>`;
  }

  // ── Hours of the month (organisation admins, department admins, partners) ──
  function hoursHtml(d){
    if (!d) return '';
    const loc = lang() === 'en' ? 'en-GB' : 'nl-NL';
    // Tenths of an hour, rounded the same way above and below zero so used and remaining add up.
    const hm = m => (m == null ? null : (Math.sign(m) * Math.round(Math.abs(m) / 6) / 10).toLocaleString(loc, { maximumFractionDigits: 1 }));
    const cell = m => (m == null ? `<span class="om-muted">${H(w('hrs_unknown'))}</span>` : `<span class="${m < 0 ? 'sp-hours-over' : ''}">${H(hm(m))} ${H(w('hrs_h'))}</span>`);
    const date = v => { const d = typeof v === 'number' ? new Date(v * 1000) : new Date(String(v).slice(0, 10) + 'T00:00:00Z'); return isNaN(d) ? String(v).slice(0, 10) : d.toLocaleDateString(loc, { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }); };
    const roleName = r => Partners.short(r.role || r.resource) || r.label || '';
    const shell = body => `<section class="wp-card sp-hours" data-tour="studio-hours" aria-label="${H(w('hrs_title'))}"><div class="wp-card-head"><h3>${H(w('hrs_title'))}</h3>${d.usage_as_of ? `<span class="om-muted om-small">${H(w('hrs_as_of'))} ${H(new Date(d.usage_as_of * 1000).toLocaleDateString(loc, { day: 'numeric', month: 'long' }))}</span>` : ''}</div>${body}</section>`;
    if (!d.configured) return shell(`<p class="sp-hours-empty">${H(w('hrs_off'))}</p>`);
    if (!d.available) return shell(`<p class="sp-hours-empty">${H(w('hrs_down'))}</p>`);
    const depts = (d.departments || []).filter(x => (x.roles || []).length || (x.team || []).length || (x.cards || []).length);
    if (!depts.length) return shell(`<p class="sp-hours-empty">${H(w('hrs_none'))}</p>`);
    // Under a role: how the month is built up, what came from an hour card, and what nothing covers.
    const notes = r => {
      const out = [];
      if (r.increment_minutes > 0) out.push(H(w('hrs_basis', { a: hm(r.base_minutes), b: hm(r.increment_minutes) })));
      if (r.card_minutes_used > 0) out.push(H(w('hrs_from_card', { h: hm(r.card_minutes_used) })));
      if (r.uncovered_minutes > 0) out.push(`<span data-sp-hours-uncovered>${H(w('hrs_uncovered', { h: hm(r.uncovered_minutes) }))}</span>`);
      return out.length ? `<tr class="sp-hours-note"><td colspan="4">${out.join(' · ')}</td></tr>` : '';
    };
    const cardLine = k => {
      const state = k.status === 'voided' ? w('hrs_card_voided') : k.status === 'used' ? w('hrs_card_used') : k.expires_at ? w(k.status === 'expired' ? 'hrs_card_expired' : 'hrs_card_until', { d: date(k.expires_at) }) : '';
      return `<span class="om-chip sp-hours-card ${k.status && k.status !== 'active' ? 'done' : ''}">${H(w('hrs_card', { l: roleName(k), r: hm(k.remaining_minutes), p: hm(k.purchased_minutes) }))}${state ? ' · ' + H(state) : ''}</span>`;
    };
    return shell(depts.map(x => `<div class="sp-hours-dept">
        <div class="sp-hours-head"><strong>${H(x.name || '')}</strong>${x.tier_name || x.tier ? `<span class="om-badge">${H(w('hrs_package'))}: ${H(x.tier_name || x.tier)}</span>` : ''}${x.term_ends_at ? `<span class="om-muted om-small">${H(w('hrs_until'))} ${H(date(x.term_ends_at))}</span>` : ''}${x.planned_tier_change ? `<span class="om-badge warn">${H(w('hrs_change'))}</span>` : ''}</div>
        ${(x.roles || []).length ? `<div class="om-table-wrap sp-hours-table"><table class="om-table"><thead><tr><th>${H(w('hrs_role'))}</th><th class="num">${H(w('hrs_allocated'))}</th><th class="num">${H(w('hrs_used'))}</th><th class="num">${H(w('hrs_left'))}</th></tr></thead><tbody>${x.roles.map(r => `<tr><td><strong>${H(roleName(r))}</strong>${r.closed ? ` <span class="om-badge sp-hours-closed">${H(w('hrs_closed'))}</span>` : ''}</td><td class="num">${cell(r.allocated_minutes)}</td><td class="num">${cell(r.used_minutes)}</td><td class="num">${cell(r.remaining_minutes)}</td></tr>${notes(r)}${(r.people || []).map(p => `<tr class="sp-hours-person"><td>${H(p.name)}</td><td></td><td class="num">${cell(p.used_minutes)}</td><td></td></tr>`).join('')}`).join('')}</tbody></table></div>` : ''}
        ${(x.cards || []).length ? `<div class="sp-hours-team sp-hours-cards"><span class="om-muted om-small">${H(w('hrs_cards'))}</span>${x.cards.map(cardLine).join('')}</div>` : ''}
        ${(x.team || []).length ? `<div class="sp-hours-team"><span class="om-muted om-small">${H(w('hrs_team'))}</span>${x.team.map(t => `<span class="om-chip">${H(t.name)}${t.label || t.role ? ' · ' + H(Partners.short(t.role) || t.label) : ''}${t.hours_per_week != null ? ' · ' + H(Number(t.hours_per_week).toLocaleString(loc, { maximumFractionDigits: 1 })) + ' ' + H(w('hrs_week')) : ''}</span>`).join('')}</div>` : ''}</div>`).join(''));
  }

  // ── Workplace: the items ───────────────────────────────────────────────────
  const Wp = { data: null, at: 0, group: store.get('sp-wp-group', 'kind'), open: new Set(), more: new Set(), token: 0, body: null, intake: null, setup: '',
               raw: {}, early: null, sig: '' };
  // The structure the page paints with: the full one, or the quick one until the chart is in.
  const cur = () => ctxCache || Wp.early;
  // Kinds whose list has never arrived yet. They show as loading, not as zero.
  function pendingKinds(){
    const p = new Set();
    if (Wp.raw.cr === undefined) p.add('task');
    if (Wp.raw.pf === undefined) p.add('bot');
    return p;
  }
  function buildItems(c){
    const { uc, bl, pb, cr, pf } = Wp.raw;
    const items = [];
    const withTeam = (team, owner) => team || primaryTeam(c, owner);
    for (const r of (uc && uc.usecases) || []) items.push({ kind: 'usecase', id: r.id, title: r.title || '', owner: norm(r.owner), team: withTeam(r.team, r.owner), sub: w('p_' + (r.phase || 'discover')), at: r.updated_at || 0 });
    for (const r of (bl && bl.items) || []) { if (['live', 'parked'].includes(r.status)) continue; items.push({ kind: 'backlog', id: r.id, title: r.title || '', owner: norm(r.owner), team: withTeam(r.team, r.owner), sub: r.pain || '', at: r.updated_at || 0 }); }
    for (const r of (pb && pb.playbooks) || []) items.push({ kind: 'playbook', id: r.id, title: r.title || '', owner: norm(r.owner), team: withTeam(r.team, r.owner), sub: r.summary || r.category || '', at: r.updated_at || 0 });
    for (const r of c.promptRows) items.push({ kind: 'prompt', id: r.id, title: r.label || r.title || '', owner: norm(r.owner), team: withTeam(r.scope === 'team' ? r.team : '', r.scope === 'org' ? '' : r.owner), sub: r.category || '', at: r.updated_at || 0 });
    const bots = new Map();
    for (const p of (pf && pf.profiles) || []) {
      if (p.visible === false) continue;
      const b = p.bot || {};
      const person = (p.bot_kind || b.kind) === 'person';
      const owner = person ? ([...c.people.keys()].find(e => e.split('@')[0].split('.')[0] === String(p.name).toLowerCase()) || '') : '';
      const team = (Array.isArray(b.serves) && b.serves[0]) || primaryTeam(c, owner);
      const title = b.title || (p.is_default ? 'Super Agent' : p.name);
      bots.set(p.name, { title, team });
      items.push({ kind: 'bot', id: p.name, title, owner, team, sub: person ? w('assistant') : (b.category || b.description || ''), avatar: p.bot_avatar_url || '', color: b.color || '', at: 0 });
    }
    for (const j of (cr && cr.jobs) || []) {
      const st = String(j.owner_profile ?? j.profile ?? '') || 'default';
      const bot = String(j.assigned_bot || '') || st;
      const failing = j.enabled && (j.last_status === 'error' || (j.failure_streak || 0) > 0);
      const status = j.state === 'completed' ? 'done' : !j.enabled ? 'paused' : failing ? 'error' : 'on';
      const sched = typeof _cronScheduleInWords === 'function' ? _cronScheduleInWords(j.schedule_display || (j.schedule && j.schedule.display) || '') : (j.schedule_display || '');
      const botTitle = (bots.get(bot) || {}).title || '';
      items.push({ kind: 'task', id: j.id, store: st, bot, title: j.name || '', owner: norm(j.owner_email),
                   team: c.jobTeam.get(st + ':' + j.id) || (bots.get(bot) || {}).team || primaryTeam(c, j.owner_email),
                   sub: [sched, botTitle].filter(Boolean).join(' · '), status, runStatus:j.last_status === 'error' ? w('s_error') : j.last_status === 'ok' || j.last_status === 'success' ? w('s_done') : '', at: Date.parse(j.last_run_at || '') / 1000 || 0 });
    }
    return items;
  }

  const STATUS_RANK = { error: 0, on: 1, paused: 2, done: 3 };
  function sortItems(rows){
    return rows.slice().sort((a, b) => ((STATUS_RANK[a.status] ?? 1) - (STATUS_RANK[b.status] ?? 1)) || (b.at - a.at) || String(a.title).localeCompare(String(b.title)));
  }
  function statusBadge(it){
    if (it.kind !== 'task') return '';
    const cls = { on: 'ok', error: 'error', paused: 'paused', done: 'paused' }[it.status] || '';
    return `<span class="om-badge ${cls}">${H(w('s_' + it.status))}</span>`;
  }
  function rowHtml(c, it, opts){
    opts = opts || {};
    const bits = [];
    if (opts.kind) bits.push(w('k_' + it.kind));
    if (it.sub) bits.push(it.sub);
    if (opts.team && it.team) bits.push(teamName(c, it.team));
    if (opts.owner && it.owner && it.owner !== c.email) bits.push(personName(it.owner));
    const lead = it.kind === 'bot'
      ? `<span class="om-face bot wp-face-sm" style="${it.color ? '--bot:' + H(it.color) : ''}">${it.avatar ? `<img src="${H(it.avatar)}" alt="" loading="lazy">` : H(initials(it.title))}</span>`
      : `<span class="wp-kind-dot k-${it.kind}" aria-hidden="true"></span>`;
    return `<button type="button" class="wp-row" data-wp-open="${H(it.kind)}" data-wp-id="${H(it.id)}" data-wp-store="${H(it.store || '')}" data-wp-bot="${H(it.bot || '')}">${lead}
      <span class="wp-row-main"><span class="wp-row-title ${it.title ? '' : 'wp-untitled'}">${H(it.title || w('untitled'))}</span>${bits.length ? `<span class="wp-row-sub">${H(bits.join(' · '))}</span>` : ''}</span>${statusBadge(it)}</button>`;
  }
  function listHtml(c, rows, key, opts, limit){
    limit = limit || 6;
    const sorted = sortItems(rows);
    const openAll = Wp.more.has(key);
    const shown = openAll ? sorted : sorted.slice(0, limit);
    return shown.map(it => rowHtml(c, it, opts)).join('') + (sorted.length > limit ? `<button type="button" class="wp-more" data-wp-more="${H(key)}">${H(openAll ? w('less') : w('more', { n: sorted.length - limit }))}</button>` : '');
  }
  function kindCard(c, kind, rows, key, opts){
    return `<section class="wp-card"><header class="wp-card-head"><h3>${H(w('k_' + kind))}</h3><span class="wp-count">${rows.length}</span><button type="button" class="om-link wp-all" data-wp-go="${kind}">${H(w('all'))}</button></header>
      <div class="wp-rows">${listHtml(c, rows, key, opts)}</div></section>`;
  }
  function short(k){ return k === 'task' ? w('ks_task') : w('k_' + k); }
  function chipsHtml(rows, key){
    const n = Object.fromEntries(KINDS.map(k => [k, rows.filter(it => it.kind === k).length]));
    const have = KINDS.filter(k => n[k]);
    if (!have.length) return `<span class="wp-none">${H(w('nothing'))}</span>`;
    return have.map(k => `<button type="button" class="wp-chip" aria-pressed="${Wp.open.has(key + '|' + k)}" data-wp-toggle="${H(key + '|' + k)}"><span class="wp-kind-dot k-${k}" aria-hidden="true"></span>${H(short(k))}<strong>${n[k]}</strong></button>`).join('');
  }
  function openLists(c, rows, key, opts){
    return KINDS.filter(k => Wp.open.has(key + '|' + k)).map(k => {
      const sub = rows.filter(it => it.kind === k);
      return sub.length ? `<div class="wp-sub"><div class="wp-sub-label">${H(w('k_' + k))}</div><div class="wp-rows">${listHtml(c, sub, key + '|' + k, opts, 8)}</div></div>` : '';
    }).join('');
  }
  function teamView(c, rows){
    const groups = groupByTeam(c, rows);
    let lastDept = null, out = '';
    const showDept = groups.some(g => g.department && g.department !== g.name);
    for (const g of groups) {
      const t = c.teams.get(g.key) || {};
      if (showDept && g.department !== lastDept) { out += `<div class="wp-dept">${H(g.department || w('no_dept'))}</div>`; lastDept = g.department; }
      const key = 't:' + g.key;
      const members = (t.members || []).filter(e => e !== t.lead);
      out += `<section class="wp-card wp-team"><header class="wp-team-head">
          <div class="wp-team-name"><h3>${H(g.name)}</h3>${c.myTeams.has(g.key) ? `<span class="om-badge wp-mine">${H(w(c.leadTeams.has(g.key) ? 'r_lead' : 'r_member'))}</span>` : ''}</div>
          ${t.lead || members.length ? `<div class="wp-team-people">${t.lead ? faceHtml(c, t.lead, 'lead') + `<span class="wp-lead-name">${H(personName(t.lead))}</span>` : ''}${members.length ? `<span class="om-faces wp-faces">${members.slice(0, 6).map(e => faceHtml(c, e)).join('')}${members.length > 6 ? `<span class="wp-face-more">+${members.length - 6}</span>` : ''}</span>` : ''}</div>` : ''}
        </header><div class="wp-chips">${chipsHtml(g.items, key)}</div>${openLists(c, g.items, key, { owner: true })}</section>`;
    }
    return out;
  }
  function personView(c, rows, lens){
    const byOwner = new Map();
    for (const it of rows) { const k = it.owner || ''; if (!byOwner.has(k)) byOwner.set(k, []); byOwner.get(k).push(it); }
    // Everyone in the teams in view, also when they have nothing yet.
    const inView = t => lens === 'org' || (lens === 'team' ? c.myTeams.has(t.key) : c.myDepts.has(t.department));
    const placed = new Map();
    for (const t of c.teams.values()) {
      if (!inView(t)) continue;
      for (const e of [t.lead, ...t.members].filter(Boolean)) if (!placed.has(e) && primaryTeam(c, e) === t.key) placed.set(e, t.key);
    }
    for (const e of byOwner.keys()) if (e && !placed.has(e)) placed.set(e, primaryTeam(c, e));
    const teams = new Map();
    for (const [e, k] of placed) { if (!teams.has(k)) teams.set(k, []); teams.get(k).push(e); }
    const keys = [...teams.keys()].sort((a, b) => (!a) - (!b) || (c.myTeams.has(b) - c.myTeams.has(a)) || teamName(c, a).localeCompare(teamName(c, b)));
    const person = (e, teamKey) => {
      const mine = byOwner.get(e) || [];
      const p = c.people.get(e) || {};
      const lead = !!teamKey && (c.teams.get(teamKey) || {}).lead === e;
      const key = 'p:' + e;
      return `<div class="wp-person"><div class="wp-person-head">${faceHtml(c, e, lead ? 'lead' : '')}
          <div class="wp-person-main"><div class="wp-person-name">${H(personName(e))}${e === c.email ? ` <span class="wp-you">${H(w('you'))}</span>` : ''}</div>
          <div class="wp-row-sub">${H([p.title, teamKey ? w(lead ? 'r_lead' : 'r_member') : ''].filter(Boolean).join(' · '))}</div></div>
          <div class="wp-chips">${chipsHtml(mine, key)}</div></div>${openLists(c, mine, key, {})}</div>`;
    };
    let out = keys.map(k => `<section class="wp-card wp-team"><header class="wp-team-head"><div class="wp-team-name"><h3>${H(k ? teamName(c, k) : w('not_placed'))}</h3>${k && deptName(c, deptKey(c, k)) !== teamName(c, k) ? `<span class="wp-team-dept">${H(deptName(c, deptKey(c, k)))}</span>` : ''}</div></header>
        ${teams.get(k).sort((a, b) => ((c.teams.get(k) || {}).lead === b) - ((c.teams.get(k) || {}).lead === a) || a.localeCompare(b)).map(e => person(e, k)).join('')}</section>`).join('');
    const orphans = byOwner.get('') || [];
    if (orphans.length) out += `<section class="wp-card wp-team"><header class="wp-team-head"><div class="wp-team-name"><h3>${H(w('no_owner'))}</h3></div></header><div class="wp-chips">${chipsHtml(orphans, 'p:')}</div>${openLists(c, orphans, 'p:', { team: true })}</section>`;
    return out;
  }
  function greeting(){ const h = new Date().getHours(); return w(h < 12 ? 'morning' : h < 18 ? 'afternoon' : 'evening'); }
  function heroHtml(c){
    const first = personName(c.email).split(' ')[0];
    const job = ((Wp.intake || {}).role || {}).title || (c.people.get(c.email) || {}).title || '';
    const rs = roles(c);
    return `<section class="wp-hero">${faceHtml(c, c.email, 'wp-avatar')}
      <div class="wp-hero-main"><h2>${H(greeting())}, <span class="wp-hero-name">${H(first)}</span></h2>
        <p>${H(job || w('intro'))}</p>
        <p data-today-sub hidden></p>
        ${rs.length ? `<div class="wp-badges">${rs.map(r => `<span class="om-badge wp-role ${r.cls}">${H(r.label)}</span>`).join('')}</div>` : ''}</div></section>`;
  }
  function allowed(panel) { return !!window.SynthPulseWorkspace?.allowed(panel); }
  let findings = null, findingsFailed = false, showEarlier = false;
  // Older reports use plain section labels. Give them the same hierarchy as new Markdown reports.
  const findingLabel = /^(?:\*\*)?(update|mijn advies|advies|dit kan ik voor je oppakken|volgende stap|waarom nu|bron(?:nen)?|my advice|my recommendation|what i can do for you|next steps?|why now|sources?)(?:\*\*)?\s*(?::(?:\*\*)?\s*|$)/i;
  const quietFinding = /^(?:(?:er zijn|ik heb)\s+geen nieuwe (?:scout[ -]?)?(?:items|signalen|bevindingen)|(?:there are |i found )?no new (?:scout[ -]?)?(?:items|signals|findings|updates))\b/i;

  function findingPreview(body) {
    let first = '', fallback = '', section = '', plain = '';
    for (const line of body.split(/\r?\n/)) {
      const text = line.trim().replace(/^#{1,6}\s+/, '');
      const label = text.match(findingLabel);
      if (label) section = label[1].toLowerCase();
      const snippet = text.slice(label ? label[0].length : 0)
        .replace(/!?\[([^\]]*)\]\([^)]+\)/g, '$1')
        .replace(/^(?:[-*>]|\d+[.)])\s+/, '')
        .replace(/(\*\*|__|\*|`)(.+?)\1/g, '$2').trim();
      if (!snippet) continue;
      if (!first) first = snippet;
      if (quietFinding.test(snippet)) continue;
      if (!fallback) fallback = snippet;
      if (!quietFinding.test(first) || /advies|oppakken|volgende|advice|recommendation|next step|can do/.test(section)) {
        plain = snippet;
        break;
      }
    }
    plain = plain || fallback || first;
    if (plain.length <= 170) return plain;
    const cut = plain.slice(0, 169);
    return (cut.replace(/\s+\S*$/, '') || cut) + '…';
  }

  function findingDocument(source) {
    let fenced = false;
    const normalized = source.split(/\r?\n/).map(line => {
      if (/^\s*`{3}/.test(line)) { fenced = !fenced; return line; }
      if (fenced) return line;
      return line.trim().replace(findingLabel, (_,label) => '### ' + label + '\n')
        .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1');
    }).join('\n');
    const template = document.createElement('template');
    template.innerHTML = _kanbanRenderMarkdown(normalized);
    // Keep only reading elements from the inert Markdown document. No embeds, controls or remote media.
    const tags = new Set('p h1 h2 h3 h4 h5 h6 strong em del code pre ol ul li a blockquote table tbody tr td hr br'.split(' '));
    for (const node of [...template.content.querySelectorAll('*')].reverse()) {
      if (node.matches('input[type=checkbox]')) {
        node.replaceWith(node.checked ? '☑ ' : '☐ ');
        continue;
      }
      if (!tags.has(node.localName)) { node.replaceWith(...node.childNodes); continue; }
      const href = node.getAttribute('href');
      for (const attr of [...node.attributes]) node.removeAttribute(attr.name);
      if (node.localName === 'a') {
        let url;
        try { url = new URL(href); } catch (_) {}
        if (!url || !['https:', 'http:'].includes(url.protocol) || url.username || url.password) {
          node.replaceWith(...node.childNodes); continue;
        }
        node.href = url.href; node.target = '_blank'; node.rel = 'noopener noreferrer';
      }
      if (/^h[1-6]$/.test(node.localName) && node.localName !== 'h3') {
        const heading = document.createElement('h3');
        heading.append(...node.childNodes); node.replaceWith(heading);
      }
    }
    return template.content;
  }

  function findingDate(row) {
    return new Intl.DateTimeFormat(lang(), {day:'numeric', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit'}).format(row.at * 1000);
  }

  function findingAuthor(row, reader = false) {
    const avatar = window.SynPulseFriendlyTools.bots.avatarHtml(row.profile, row.bot, 'wp-finding-avatar');
    const name = reader ? `<h2 id="wpFindingReaderTitle" tabindex="-1">${H(row.bot)}</h2>` : `<strong>${H(row.bot)}</strong>`;
    return `<div class="wp-finding-author">${avatar}<div>${name}<time datetime="${H(row.run_at)}">${H(findingDate(row))}</time></div></div>`;
  }

  function findingCard(row, index) {
    return `<article class="wp-finding" data-finding-index="${index}"${index >= 3 && !showEarlier ? ' hidden' : ''}>
      <header>${findingAuthor(row)}</header>
      <p class="wp-finding-preview">${H(findingPreview(row.body))}</p>
      <div class="wp-finding-actions"><button type="button" class="om-link" data-finding-read aria-haspopup="dialog">${H(w('findings_read'))}</button>
      <button type="button" class="sm-btn" data-finding-chat>${H(w('findings_chat'))}</button></div></article>`;
  }

  function readFinding(row, button) {
    const dialog = document.createElement('dialog');
    dialog.className = 'wp-finding-reader';
    dialog.setAttribute('aria-labelledby', 'wpFindingReaderTitle');
    dialog.innerHTML = `<header>${findingAuthor(row, true)}
      <button type="button" class="sm-btn" data-reader-close>${H(w('findings_close'))}</button></header>
      <div class="wp-finding-body"></div><footer><button type="button" class="sm-btn" data-reader-chat>${H(w('findings_chat'))}</button></footer>`;
    dialog.querySelector('.wp-finding-body').append(findingDocument(row.body));
    document.body.append(dialog);
    const dismiss = () => dialog.close();
    dialog.querySelector('[data-reader-close]').onclick = dismiss;
    dialog.querySelector('[data-reader-chat]').onclick = () => { dismiss(); void discussFinding(row, button); };
    dialog.addEventListener('click', ev => {
      if (ev.target !== dialog) return;
      const box = dialog.getBoundingClientRect();
      if (ev.clientX < box.left || ev.clientX > box.right || ev.clientY < box.top || ev.clientY > box.bottom) dismiss();
    });
    window.addEventListener('popstate', dismiss);
    dialog.addEventListener('close', () => {
      window.removeEventListener('popstate', dismiss);
      dialog.remove();
    }, {once:true});
    dialog.showModal();
    dialog.querySelector('h2').focus({preventScroll:true});
  }

  function findingsSection() {
    return allowed('chat') ? '<section class="wp-card wp-findings" aria-labelledby="wpFindingsTitle" data-wp-findings>'+findingsHtml()+'</section>' : '';
  }

  function findingsHtml() {
    let content;
    if (findingsFailed) content = `<div class="wp-findings-note" role="status">${H(w('failed'))} <button class="om-link" type="button" data-finding-retry>${H(w('retry'))}</button></div>`;
    else if (findings === null) content = `<p class="wp-findings-note" role="status">${H(w('loading'))}</p>`;
    else if (!findings.length) content = `<p class="wp-findings-note">${H(w('findings_empty'))}</p>`;
    else content = `<div class="wp-findings-list" id="wpFindingsList">${findings.map(findingCard).join('')}</div>`;
    const more = findings?.length > 3 ? `<button class="om-link" type="button" data-finding-more aria-controls="wpFindingsList" aria-expanded="${showEarlier}">${H(showEarlier ? w('less') : w('findings_older',{n:findings.length-3}))}</button>` : '';
    return `<header class="wp-card-head"><h3 id="wpFindingsTitle">${H(w('findings'))}</h3>${more}</header>${content}`;
  }

  async function loadFindings(token) {
    try {
      const result = await call('/api/me/findings');
      if (token !== Wp.token) return;
      if (!Array.isArray(result?.findings)) throw new Error();
      findings = result.findings;
      findingsFailed = false;
    } catch (_e) {
      if (token !== Wp.token) return;
      findingsFailed = true;
    }
    const section = Wp.body?.querySelector('[data-wp-findings]');
    if (section) section.innerHTML = findingsHtml();
  }

  async function discussFinding(row, button) {
    button.disabled = true;
    try {
      await _openSidebarSession(row, {explicitProfile:true});
      if (_currentPanel === 'chat' && S.session?.session_id === row.session_id && _profileMatchesActiveProfile(row.profile,S.activeProfile||'default')) {
        _addNamedContextBlock(row.body, row.bot + ' · ' + findingDate(row));
        document.getElementById('msg')?.focus();
      }
    } catch (_e) { showToast(w('failed')); }
    finally { button.disabled = false; }
  }

  function recentHtml(title, target, items, empty) {
    return `<section class="wp-card"><header class="wp-card-head"><h3>${H(w(title))}</h3><button type="button" class="om-link wp-all" data-wp-go="${target}">${H(w('all'))}</button></header>${items || '<p class="wp-no-recent">'+H(w(empty))+'</p>'}</section>`;
  }
  function recentChats() {
    const chats = window.ConversationWorkbench?.recent() || [];
    return recentHtml('recent_chats', 'conversations', chats.map(s => rowHtml(cur(), {kind:'conversation', id:s.id,
      title:s.title, sub:[s.bot, s.at ? _formatRelativeSessionTime(s.at) : ''].filter(Boolean).join(' · ')})).join(''), 'no_chats');
  }
  function refreshRecent() {
    const node = Wp.body?.querySelector('[data-wp-recent-chats]');
    if (node && allowed('chat')) {
      const focused = node.contains(document.activeElement) ? document.activeElement.dataset : null;
      node.innerHTML = recentChats();
      if (focused) [...node.querySelectorAll('button')].find(b=>b.dataset.wpGo === focused.wpGo && b.dataset.wpId === focused.wpId)?.focus({preventScroll:true});
    }
  }
  function activity(rows) {
    const jobs = rows.filter(r=>r.kind === 'task' && r.at > 0).sort((a,b)=>b.at-a.at).slice(0,4);
    const runs = jobs.map(r=>rowHtml(cur(), {...r, status:undefined, kind:'run',
      sub:[_formatRelativeSessionTime(r.at*1000), r.runStatus].filter(Boolean).join(' · ')})).join('');
    return `<div class="wp-grid wp-activity">${allowed('chat') ? '<div data-wp-recent-chats>'+recentChats()+'</div>' : ''}
      ${allowed('tasks') ? recentHtml('recent_runs','task',runs,pendingKinds().has('task') ? 'loading' : Wp.runsReadable ? 'no_runs' : 'failed') : ''}</div>`;
  }
  function shortcuts() {
    const actions = [['projects','projects','projects'],['profiles','chart','chart'],['tasks','agenda','agenda']];
    return '<div class="wp-shortcuts">'+actions.filter(([panel])=>allowed(panel)).map(([,target,label])=>
      `<button type="button" class="sm-btn" data-wp-go="${target}">${H(w(label))}</button>`).join('')+
      `<button type="button" class="sm-btn" data-wp-go="navigate">${H(t('workspace_navigation_search'))}</button></div>`;
  }
  function paint(force){
    const body = Wp.body, c = cur(), pending = pendingKinds();
    if (!body || !body.isConnected || !c || !Wp.data) return;
    // The Studio body is shared by every hub: never paint over another hub that opened meanwhile.
    if (!force && !(body.firstElementChild && body.firstElementChild.classList.contains('wp'))) return;
    const lens = homeLens(c);
    const rows = Wp.data.filter(it => match(c, it, lens) && (it.kind !== 'task' || allowed('tasks')) && (it.kind !== 'bot' || allowed('profiles')));
    const group = lens === 'mine' ? 'kind' : Wp.group;
    const n = Object.fromEntries(KINDS.map(k => [k, rows.filter(it => it.kind === k).length]));
    const groupSeg = lens === 'mine' ? '' : `<div class="om-seg" role="group" aria-label="${H(w('group'))}">${['kind', 'team', 'person'].map(g => `<button type="button" aria-pressed="${g === group}" data-wp-group="${g}">${H(w('g_' + g))}</button>`).join('')}</div>`;
    let main;
    if (!rows.length && pending.size) main = `<div class="wp-skeleton" aria-busy="true" aria-label="${H(w('loading'))}"><span></span><span></span></div>`;
    else if (!rows.length) {
      const wider = lenses(c).find(l => l !== lens && Wp.data.some(it => match(c, it, l)));
      main = `<div class="wp-empty"><span class="wp-empty-art" aria-hidden="true"><svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l2.2 5.3L20 9.5l-4.3 3.9L17 19l-5-2.9L7 19l1.3-5.6L4 9.5l5.8-1.2z"/></svg></span>
        <h3>${H(w('empty_h'))}</h3><p>${H(w(lens === 'mine' ? 'empty_mine' : 'empty_scope'))}</p>
        ${wider ? `<button type="button" class="sm-btn" data-sp-lens="${wider}" data-sp-lens-surface="home">${H(w('empty_peek', { l: lensLabel(c, wider).toLowerCase() }))}</button>` : ''}</div>`;
    }
    else if (group === 'team') main = `<div class="wp-stack">${teamView(c, rows)}</div>`;
    else if (group === 'person') main = `<div class="wp-stack">${personView(c, rows, lens)}</div>`;
    else main = `<div class="wp-grid">${KINDS.filter(k => n[k]).map(k => kindCard(c, k, rows.filter(it => it.kind === k), 'k:' + lens + ':' + k, { team: lens !== 'mine' && k !== 'bot', owner: lens !== 'mine' })).join('')}</div>`;
    body.innerHTML = `<div class="wp" data-tour="studio-home">${heroHtml(c)}
      <div data-sp-today></div>
      ${findingsSection()}
      <div data-wp-setup>${Wp.setup}</div>
      ${Partners.teamHtml(false)}${hoursHtml(Wp.hours)}
      <div class="wp-bar">${barHtml(c, 'home', Wp.data, lens)}${groupSeg}</div>
      <div class="wp-kpis">${KINDS.filter(k => k === 'task' ? allowed('tasks') : k !== 'bot' || allowed('profiles')).map(k => `<button type="button" class="wp-kpi ${n[k] || pending.has(k) ? '' : 'zero'}" title="${H(w('kpi_hint', { k: w('k_' + k) }))}" data-wp-go="${k}"${k === 'usecase' ? ' data-tour="studio-usecases"' : ''}><span class="wp-kpi-label"><span class="wp-kind-dot k-${k}" aria-hidden="true"></span>${H(short(k))}</span><span class="wp-kpi-value"${pending.has(k) ? ` aria-busy="true" aria-label="${H(w('loading'))}">…` : `>${n[k]}`}</span></button>`).join('')}</div>
      ${shortcuts()}
      <details class="wp-card wp-destinations"><summary>${H(w('navigate'))}</summary><div class="wp-shortcuts">${(window.WorkspaceDestinations?.destinations() || []).map(d=>
        `<button type="button" class="sm-btn" data-wp-destination="${H(d.panel)}">${H(d.label)}</button>`).join('')}${[...document.querySelectorAll('#studioHubNav [data-st-hub]')].filter(b=>['me','profile','teams','chart','mgmt'].includes(b.dataset.stHub)).map(b=>
        `<button type="button" class="sm-btn" data-wp-studio="${H(b.dataset.stHub)}">${H(b.textContent)}</button>`).join('')}</div></details>
      ${activity(rows)}${main}</div>`;
    window.SPToday?.mount(body.querySelector('[data-sp-today]'));
  }
  async function render(body, opts){
    Wp.body = body; Wp.setup = (opts && opts.setup) || '';
    const token = ++Wp.token;
    findings = null; findingsFailed = false; showEarlier = false;
    const fetchOnEntry = allowed('chat');
    if (fetchOnEntry) void loadFindings(token);
    if (!body.dataset.wpBound) {
      body.dataset.wpBound = '1';
      body.addEventListener('click', onClick);
    }
    if (ctxCache && Wp.data) paint(true); else body.innerHTML = `<div class="wp">${findingsSection()}<div class="wp-skeleton" aria-busy="true" aria-label="${H(w('loading'))}"><span></span><span></span><span></span></div></div>`;
    // Paint as soon as the quick lists are in. Tasks, bots and the chart join when they arrive;
    // a repaint that would show the same thing is skipped.
    const step = () => {
      const c = cur();
      if (token !== Wp.token || !c || !Wp.raw.quick) return;
      const items = buildItems(c);
      const sig = JSON.stringify(items) + '|' + [...pendingKinds()].join() + '|' + c.people.size + '|' + [...c.teams.values()].map(t => t.members.length).join() + '|' + Partners.rows.map(p => p.email + p.role).join() + '|' + JSON.stringify(Wp.hours || null);
      if (Wp.data && sig === Wp.sig && body.querySelector('.wp-kpis')) return;
      Wp.data = items; Wp.sig = sig;
      paint();
    };
    try {
      const full = loadCtx(Date.now() - Wp.at > 30000);
      if (!ctxCache && ctxEarly) void ctxEarly.then(c => { Wp.early = c; step(); });
      // Hours of the month: only asked for the people the server shows them to.
      void (ctxEarly || full).then(c => (c && (c.canManage || c.partner) ? call('/api/studio/hours').catch(() => null) : null)).then(h => { if (token === Wp.token) { Wp.hours = h; step(); } }).catch(() => {});
      await Promise.all([
        full.then(step),
        Promise.all([call('/api/studio/usecases').catch(() => null), call('/api/studio/backlog').catch(() => null), call('/api/studio/playbooks').catch(() => null),
                     call('/api/studio/profile?who=me').catch(() => null)])
          .then(([uc, bl, pb, me]) => { Object.assign(Wp.raw, { uc, bl, pb, quick: true }); Wp.intake = me; if (uc) Partners.set(uc.partners); step(); }),
        call('/api/crons?all_profiles=1').catch(() => null).then(cr => { Wp.raw.cr = cr; Wp.runsReadable = Array.isArray(cr?.jobs); step(); }),
        // The fast list skips the alias scan and the skill counts, which this page never shows.
        call('/api/profiles?fast=1&counts=0').catch(() => null).then(pf => { Wp.raw.pf = pf; step(); })]);
      Wp.at = Date.now();
    }
    catch (_e) { if (token === Wp.token && body.isConnected && body.firstElementChild && body.firstElementChild.classList.contains('wp')) body.innerHTML = `<div class="wp">${findingsSection()}<div class="om-empty wp-failed"><h3>${H(w('failed'))}</h3><div class="om-actions"><button type="button" class="sm-btn" data-wp-retry>${H(w('retry'))}</button></div></div></div>`; return; }
    if (token === Wp.token) {
      step();
      if (!fetchOnEntry && allowed('chat')) void loadFindings(token);
    }
  }
  // Opens on "mine". Someone who owns nothing yet and never chose a lens starts on
  // the first lens that has something to show, so the first visit is never an empty page.
  function homeLens(c){
    const lens = getLens(c, 'home', 'mine');
    if (lens !== 'mine' || store.get('sp-lens-home', '') || !Wp.data || pendingKinds().size) return lens;
    if (Wp.data.some(it => match(c, it, 'mine'))) return lens;
    return lenses(c).find(l => l !== 'mine' && Wp.data.some(it => match(c, it, l))) || lens;
  }
  async function go(kind){
    const c = cur();
    const lens = c ? homeLens(c) : 'org';
    if (kind === 'conversations' && allowed('chat')) return window.ConversationWorkbench.show();
    if (kind === 'projects' && allowed('projects')) return switchPanel('projects');
    if (kind === 'chart' && allowed('profiles')) {
      await switchPanel('profiles'); if (_currentPanel === 'profiles') openBotOrgChart(); return;
    }
    if (kind === 'agenda' && allowed('tasks')) {
      await switchPanel('tasks'); if (_currentPanel === 'tasks' && ['empty','read'].includes(_cronMode)) window.CronAgenda.open(); return;
    }
    if (kind === 'navigate') return document.getElementById('btnWorkspaceNavigator')?.click();
    if (kind === 'task' && allowed('tasks')) { if (typeof switchPanel === 'function') await switchPanel('tasks'); return; }
    if (kind === 'bot' && allowed('profiles')) { if (typeof switchPanel === 'function') await switchPanel('profiles'); return; }
    const tab = { usecase: 'usecases', playbook: 'playbooks', prompt: 'prompts', backlog: 'backlog' }[kind];
    if (tab === 'usecases') store.set('sp-lens-usecases', lens);
    if (tab && window.SPStudio) window.SPStudio.setTab(tab);
  }
  async function openItem(b){
    const kind = b.dataset.wpOpen, id = b.dataset.wpId;
    if (kind === 'usecase' && window.SPStudio) return window.SPStudio.openUseCase(id);
    if (kind === 'playbook' && window.SPLibrary) return window.SPLibrary.openPlaybook(id);
    if ((kind === 'backlog' || kind === 'prompt') && window.SPStudio) return window.SPStudio.setTab(kind === 'backlog' ? 'backlog' : 'prompts');
    if (kind === 'conversation' && allowed('chat')) return window.ConversationWorkbench.openRecent(id);
    if ((kind === 'task' || kind === 'run') && allowed('tasks') && typeof openCronFromBot === 'function') return openCronFromBot(id, b.dataset.wpStore === 'default' ? '' : b.dataset.wpStore, b.dataset.wpBot);
    if (kind === 'bot' && allowed('profiles') && typeof switchPanel === 'function') {
      await switchPanel('profiles');
      if (typeof openProfileDetail === 'function') openProfileDetail(id);
    }
  }
  function onClick(ev){
    const b = ev.target.closest('button');
    if (!b || !Wp.body || !Wp.body.contains(b)) return;
    if (b.hasAttribute('data-finding-retry')) { b.disabled = true; void loadFindings(Wp.token); return; }
    if (b.hasAttribute('data-finding-more')) {
      showEarlier = !showEarlier;
      Wp.body.querySelectorAll('[data-finding-index]').forEach((el, i) => { el.hidden = !showEarlier && i >= 3; });
      b.setAttribute('aria-expanded', String(showEarlier));
      b.textContent = showEarlier ? w('less') : w('findings_older', {n:findings.length-3});
      return;
    }
    const card = b.closest('[data-finding-index]');
    if (card && allowed('chat')) {
      const row = findings?.[Number(card.dataset.findingIndex)];
      if (!row) return;
      if (b.hasAttribute('data-finding-chat')) { void discussFinding(row, b); return; }
      if (b.hasAttribute('data-finding-read')) {
        readFinding(row, b);
        return;
      }
    }
    if (b.dataset.wpGroup) { Wp.group = b.dataset.wpGroup; store.set('sp-wp-group', Wp.group); paint(); return; }
    if (b.dataset.wpToggle) { const k = b.dataset.wpToggle; if (Wp.open.has(k)) Wp.open.delete(k); else Wp.open.add(k); paint(); return; }
    if (b.dataset.wpMore) { const k = b.dataset.wpMore; if (Wp.more.has(k)) Wp.more.delete(k); else Wp.more.add(k); paint(); return; }
    if (b.dataset.wpStudio) { document.querySelector('#studioHubNav [data-st-hub="'+CSS.escape(b.dataset.wpStudio)+'"]')?.click(); return; }
    if (b.dataset.wpDestination) { window.WorkspaceDestinations.open(b.dataset.wpDestination); return; }
    if (b.dataset.wpGo) { go(b.dataset.wpGo); return; }
    if (b.dataset.wpOpen) { openItem(b); return; }
    if (b.hasAttribute('data-wp-retry')) { render(Wp.body); }
  }
  document.addEventListener('sp-lens-change', ev => { if (ev.detail && ev.detail.surface === 'home') paint(); });

  function updateSetup(html) {
    Wp.setup = html;
    const setup = Wp.body?.querySelector('[data-wp-setup]');
    if (setup) setup.innerHTML = html;
  }
  window.SPWorkplace = { render, updateSetup, refreshRecent, title: () => w('title'), invalidate: () => { Wp.at = 0; ctxAt = 0; } };
})();
