/* Studio roadmap (15 Nov 2026): the use-case backlog on a time axis.

   The same picture a QuickScan ends with: months and weeks across the top, one
   bar per idea, coloured by how far it is. Shown for yourself, your team, your
   department or the organisation (the shared lens), and grouped per person,
   per team or per department.

   A start that someone set is a solid bar. Everything else is a proposal from
   the server (one idea at a time per person, started work first, then the
   backlog order, duration from the effort) and is drawn dashed. Nothing is
   stored here except the chosen grouping (localStorage). */
(function(){
  'use strict';
  const NL = {
    intro: 'De backlog op een tijdas. Een vaste balk is ingepland; een gestreepte balk is een voorstel op basis van volgorde, moeite en wie het doet.',
    g_person: 'Per persoon', g_team: 'Per team', g_dept: 'Per afdeling', g_none: 'Eén lijst', group: 'Groeperen',
    t_ideas: 'Ideeën in beeld', t_running: 'In uitvoering', t_live: 'Live', t_span: 'Doorlooptijd', t_saves: 'Verwachte besparing', t_quick: 'Quick wins',
    weeks: 'weken', week: 'week', wk: 'wk', hours_week: 'uur per week', today: 'Vandaag', proposal: 'Voorstel, nog niet ingepland', planned: 'Ingepland',
    s_idea: 'Idee', s_chosen: 'Gekozen', s_design: 'In ontwerp', s_built: 'Gebouwd', s_live: 'Live',
    p_discover: 'QuickScan', p_design: 'Deep Dive', p_playbook: 'Bouwplan', p_build: 'Bouwen', p_measure: 'Meten',
    no_team: 'Zonder team', no_dept: 'Zonder afdeling', nobody: 'Niemand', all: 'Alle ideeën',
    empty: 'Nog niets om in te plannen. Voeg ideeën toe in de lijst, of zet kansen uit een use case in de backlog.',
    empty_lens: 'Niets in deze weergave. Kies een bredere weergave om meer te zien.',
    start: 'Startweek', duration: 'Aantal weken', who: 'Wie doet het', status: 'Status', save: 'Opslaan', close: 'Sluiten',
    propose: 'Laat voorstellen', propose_hint: 'Haalt de vaste start weg; de planning schuift dan mee met de volgorde.',
    open_uc: 'Open use case', saved: 'Planning opgeslagen', from: 'vanaf', until: 't/m', saves: 'bespaart', owner_does: 'eigenaar',
    earlier: 'begon eerder', later: 'loopt door', legend: 'Legenda', plan_of: 'Planning van'
  };
  const EN = {
    intro: 'The backlog on a time axis. A solid bar is scheduled; a dashed bar is a proposal based on order, effort and who does it.',
    g_person: 'By person', g_team: 'By team', g_dept: 'By department', g_none: 'One list', group: 'Group by',
    t_ideas: 'Ideas in view', t_running: 'Under way', t_live: 'Live', t_span: 'Lead time', t_saves: 'Expected saving', t_quick: 'Quick wins',
    weeks: 'weeks', week: 'week', wk: 'wk', hours_week: 'hours per week', today: 'Today', proposal: 'Proposal, not scheduled yet', planned: 'Scheduled',
    s_idea: 'Idea', s_chosen: 'Chosen', s_design: 'In design', s_built: 'Built', s_live: 'Live',
    p_discover: 'QuickScan', p_design: 'Deep Dive', p_playbook: 'Build plan', p_build: 'Building', p_measure: 'Measuring',
    no_team: 'No team', no_dept: 'No department', nobody: 'Nobody', all: 'All ideas',
    empty: 'Nothing to schedule yet. Add ideas in the list, or put opportunities from a use case on the backlog.',
    empty_lens: 'Nothing in this view. Choose a wider view to see more.',
    start: 'Start week', duration: 'Number of weeks', who: 'Who does it', status: 'Status', save: 'Save', close: 'Close',
    propose: 'Let it be proposed', propose_hint: 'Removes the fixed start; the schedule then follows the order again.',
    open_uc: 'Open use case', saved: 'Schedule saved', from: 'from', until: 'until', saves: 'saves', owner_does: 'owner',
    earlier: 'started earlier', later: 'continues', legend: 'Legend', plan_of: 'Schedule of'
  };
  const lang = () => ((document.documentElement.lang || 'nl').toLowerCase().startsWith('en') ? 'en' : 'nl');
  const w = k => (lang() === 'en' ? EN : NL)[k] || NL[k] || k;
  const H = v => (typeof esc === 'function' ? esc(String(v ?? '')) : String(v ?? ''));
  const toast = m => { if (typeof showToast === 'function') showToast(m); };
  const post = (p, b) => api(p, { timeoutToast: false, method: 'POST', body: JSON.stringify(b) });
  const store = { get: (k, d) => { try { return localStorage.getItem(k) || d; } catch (_e) { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (_e) {} } };
  const STATUSES = ['idea', 'chosen', 'design', 'built', 'live'];
  const GROUPS = ['person', 'team', 'dept', 'none'];
  const DAY = 86400000, MIN_WEEKS = 12, MAX_WEEKS = 40, BACK_WEEKS = 2;

  const R = { host: null, opts: null, items: [], teams: [], sc: null, group: store.get('sp-rm-group', 'person'), edit: '' };

  // ── Dates: everything is counted in whole weeks from a Monday ──────────────
  const day = iso => { const [y, m, d] = String(iso).slice(0, 10).split('-').map(Number); return new Date(Date.UTC(y, m - 1, d)); };
  const iso = d => d.toISOString().slice(0, 10);
  const monday = d => new Date(d.getTime() - ((d.getUTCDay() + 6) % 7) * DAY);
  const today = () => { const n = new Date(); return new Date(Date.UTC(n.getFullYear(), n.getMonth(), n.getDate())); };
  const weeksBetween = (a, b) => Math.round((b - a) / (7 * DAY));
  const addWeeks = (d, n) => new Date(d.getTime() + n * 7 * DAY);
  function isoWeek(d){
    const t = new Date(d.getTime() + (3 - (d.getUTCDay() + 6) % 7) * DAY);          // the Thursday of this week
    const first = new Date(Date.UTC(t.getUTCFullYear(), 0, 4));
    return 1 + Math.round(((t - first) / DAY - 3 + (first.getUTCDay() + 6) % 7) / 7);
  }
  const fmt = (d, o) => d.toLocaleDateString(lang() === 'en' ? 'en-GB' : 'nl-NL', Object.assign({ timeZone: 'UTC' }, o));
  const short = d => fmt(d, { day: 'numeric', month: 'short' });

  // ── Names ──────────────────────────────────────────────────────────────────
  const S = () => window.SPScope;
  const personName = e => !e ? w('nobody') : (S() ? S().personName(e) : String(e).replace(/@.*/, ''));
  const teamName = k => !k ? w('no_team') : (R.sc && S() ? S().teamName(R.sc, k) : ((R.teams.find(t => t.key === k) || {}).name || k));
  const deptKey = k => !k ? '' : (R.sc && S() ? S().deptKey(R.sc, k) : String(k).split('/')[0]);
  const deptName = k => !k ? w('no_dept') : (R.sc && S() ? S().deptName(R.sc, k) : k);
  const face = e => (R.sc && S() && e ? S().face(R.sc, e, 'rm-face') : '');

  function rows(){
    // The lens "mine" means: the ideas I do. So the person who does it stands in for the owner.
    return R.items.filter(it => it.plan && it.status !== 'parked').map(it => Object.assign({}, it, { made_by: it.owner, owner: it.assignee || it.owner }));
  }
  function grouped(list){
    if (R.group === 'none') return [{ key: 'all', name: w('all'), sub: '', items: list }];
    const keyOf = it => R.group === 'person' ? (it.owner || '') : R.group === 'team' ? (it.team || '') : deptKey(it.team);
    const by = new Map();
    for (const it of list) { const k = keyOf(it); if (!by.has(k)) by.set(k, []); by.get(k).push(it); }
    const me = R.sc ? R.sc.email : '';
    const label = k => R.group === 'person' ? personName(k) : R.group === 'team' ? teamName(k) : deptName(k);
    const mine = k => R.group === 'person' ? k === me : R.group === 'team' ? !!(R.sc && R.sc.myTeams.has(k)) : !!(R.sc && R.sc.myDepts.has(k));
    return [...by.keys()].sort((a, b) => (!a) - (!b) || (mine(b) - mine(a)) || label(a).localeCompare(label(b)))
      .map(k => ({ key: k || '-', name: label(k), sub: R.group === 'team' && k ? deptName(deptKey(k)) : '', person: R.group === 'person' ? k : '', items: by.get(k) }));
  }

  // ── Painting ───────────────────────────────────────────────────────────────
  function axis(list){
    const now = monday(today());
    let first = now, last = addWeeks(now, MIN_WEEKS);
    for (const it of list) {
      const a = day(it.plan.start), b = day(it.plan.end);
      if (a < first) first = a;
      if (b > last) last = b;
    }
    if (first < addWeeks(now, -BACK_WEEKS)) first = addWeeks(now, -BACK_WEEKS);
    const n = Math.max(MIN_WEEKS, Math.min(MAX_WEEKS, weeksBetween(first, last)));
    return { first, n, now, weeks: Array.from({ length: n }, (_, i) => addWeeks(first, i)) };
  }
  function headHtml(ax){
    const months = [];
    for (const d of ax.weeks) {
      const key = d.getUTCFullYear() + '-' + d.getUTCMonth(), lastM = months[months.length - 1];
      if (lastM && lastM.key === key) lastM.span++; else months.push({ key, span: 1, d });
    }
    return `<div class="rm-row rm-head" aria-hidden="true"><div class="rm-left"></div><div class="rm-track rm-months">${months.map(m =>
        `<span style="grid-column:span ${m.span}">${m.span > 1 ? H(fmt(m.d, { month: 'long' }) + (m.d.getUTCMonth() === 0 || m === months[0] ? ' ' + m.d.getUTCFullYear() : '')) : ''}</span>`).join('')}</div></div>
      <div class="rm-row rm-head rm-weeks" aria-hidden="true"><div class="rm-left">${H(w('wk'))}</div><div class="rm-track">${ax.weeks.map(d =>
        `<span class="${d.getTime() === ax.now.getTime() ? 'now' : ''}" title="${H(short(d))}">${isoWeek(d)}</span>`).join('')}</div></div>`;
  }
  function barHtml(it, ax){
    const a = weeksBetween(ax.first, day(it.plan.start)), b = a + it.plan.weeks;
    const from = Math.max(0, a), to = Math.min(ax.n, b);
    if (to <= 0 || from >= ax.n) return `<span class="rm-off ${from >= ax.n ? 'right' : ''}" title="${H(short(day(it.plan.start)))}">${from >= ax.n ? '→' : '←'}</span>`;
    const end = addWeeks(day(it.plan.start), it.plan.weeks);
    const label = `${it.title}: ${w('s_' + it.status)}, ${w('from')} ${short(day(it.plan.start))} ${w('until')} ${short(new Date(end - DAY))} (${it.plan.weeks} ${w(it.plan.weeks === 1 ? 'week' : 'weeks')})${it.plan.auto ? ', ' + w('proposal').toLowerCase() : ''}`;
    const text = to - from >= 3 ? (it.uc_phase && it.status !== 'live' ? w('p_' + it.uc_phase) : w('s_' + it.status)) : '';
    return `<button type="button" class="rm-bar s-${H(it.status)}${it.plan.auto ? ' auto' : ''}${a < 0 ? ' clip-l' : ''}${b > ax.n ? ' clip-r' : ''}" style="grid-column:${from + 1} / span ${to - from}"
      data-rm-edit="${H(it.id)}" aria-expanded="${R.edit === it.id}" aria-label="${H(label)}" title="${H(label)}"><span>${H(text)}</span></button>`;
  }
  function editHtml(it){
    const people = new Set([it.made_by, it.owner].filter(Boolean));
    if (R.sc) { for (const e of R.sc.people.keys()) people.add(e); if (R.sc.email) people.add(R.sc.email); }
    const end = addWeeks(day(it.plan.start), it.plan.weeks);
    const facts = `<p class="rm-edit-facts">${H(w('s_' + it.status))} · ${H(personName(it.owner))} · ${H(short(day(it.plan.start)))} ${H(w('until'))} ${H(short(new Date(end - DAY)))}${it.plan.auto ? ' · ' + H(w('proposal')) : ''}${it.saves_hours_week ? ' · ' + H(w('saves')) + ' ' + it.saves_hours_week + ' ' + H(w('hours_week')) : ''}</p>`;
    const uc = it.use_case ? `<button type="button" class="sm-btn" data-rm-open="${H(it.use_case)}">${H(w('open_uc'))}</button>` : '';
    if (!it.editable) return `<div class="rm-edit" data-rm-panel="${H(it.id)}">${facts}<div class="rm-edit-actions">${uc}<button type="button" class="sm-btn" data-rm-close>${H(w('close'))}</button></div></div>`;
    return `<form class="rm-edit" data-rm-panel="${H(it.id)}" data-rm-form="${H(it.id)}">${facts}
      <div class="rm-edit-fields">
        <label>${H(w('start'))}<input type="date" name="start" value="${H(it.plan.start)}"></label>
        <label>${H(w('duration'))}<input type="number" name="weeks" min="1" max="52" step="1" value="${it.plan.weeks}"></label>
        <label>${H(w('who'))}<select name="assignee" class="om-select">${[...people].sort((a, b) => personName(a).localeCompare(personName(b))).map(e => `<option value="${H(e)}" ${e === it.owner ? 'selected' : ''}>${H(personName(e))}${e === it.made_by ? ' (' + H(w('owner_does')) + ')' : ''}</option>`).join('')}</select></label>
        <label>${H(w('status'))}<select name="status" class="om-select">${STATUSES.concat(['parked']).map(s => `<option value="${s}" ${it.status === s ? 'selected' : ''}>${H(s === 'parked' ? (lang() === 'en' ? 'Parked' : 'Geparkeerd') : w('s_' + s))}</option>`).join('')}</select></label>
      </div>
      <div class="rm-edit-actions"><button type="submit" class="sm-btn primary">${H(w('save'))}</button>
        ${it.plan.auto ? '' : `<button type="button" class="sm-btn" data-rm-propose="${H(it.id)}" title="${H(w('propose_hint'))}">${H(w('propose'))}</button>`}${uc}
        <button type="button" class="sm-btn" data-rm-close>${H(w('close'))}</button></div></form>`;
  }
  function rowHtml(it, ax){
    const chips = [it.saves_hours_week ? `<span class="om-chip rm-saves">${it.saves_hours_week} ${H(w('hours_week'))}</span>` : '',
      (it.impact || 3) - (it.effort || 3) >= 2 ? '<span class="om-chip bl-quick">Quick win</span>' : ''].join('');
    const who = R.group === 'person' ? (it.team ? `<span class="rm-who">${H(teamName(it.team))}</span>` : '') : `<span class="rm-who">${face(it.owner)}${H(personName(it.owner))}</span>`;
    return `<div class="rm-row rm-item${R.edit === it.id ? ' open' : ''}" data-rm-row="${H(it.id)}"><div class="rm-left">
        <button type="button" class="rm-title" data-rm-edit="${H(it.id)}" aria-expanded="${R.edit === it.id}">${H(it.title)}</button>
        <span class="rm-sub">${who}${chips}</span></div>
      <div class="rm-track" style="--rm-today:${((today() - ax.first) / DAY / (ax.n * 7) * 100).toFixed(3)}%">${barHtml(it, ax)}</div></div>${R.edit === it.id ? editHtml(it) : ''}`;
  }
  function tiles(list){
    const n = s => list.filter(it => s.includes(it.status)).length;
    const now = monday(today());
    const open = list.filter(it => it.status !== 'live');
    const span = open.length ? Math.max(0, ...open.map(it => weeksBetween(now, day(it.plan.end)))) : 0;
    const saves = Math.round(list.reduce((sum, it) => sum + (it.saves_hours_week || 0), 0) * 10) / 10;
    const t = (label, value, unit) => `<div class="rm-tile"><span class="rm-tile-label">${H(label)}</span><span class="rm-tile-value">${H(value)}${unit ? `<small>${H(unit)}</small>` : ''}</span></div>`;
    return `<div class="rm-tiles">${t(w('t_ideas'), list.length)}${t(w('t_running'), n(['design', 'built']))}${t(w('t_live'), n(['live']))}${t(w('t_span'), span, w(span === 1 ? 'week' : 'weeks'))}${t(w('t_saves'), saves || '0', w('hours_week'))}${t(w('t_quick'), list.filter(it => (it.impact || 3) - (it.effort || 3) >= 2).length)}</div>`;
  }
  function legend(){
    return `<div class="rm-legend" aria-label="${H(w('legend'))}">${STATUSES.map(s => `<span><i class="rm-bar s-${s}"></i>${H(w('s_' + s))}</span>`).join('')}
      <span><i class="rm-bar s-chosen auto"></i>${H(w('proposal'))}</span><span><i class="rm-now"></i>${H(w('today'))}</span></div>`;
  }
  function paint(){
    const host = R.host;
    if (!host || !host.isConnected) return;
    const all = rows();
    const sc = R.sc, lens = sc && S() ? S().getLens(sc, 'roadmap', 'org') : 'org';
    const list = sc && S() ? all.filter(it => S().match(sc, it, lens)) : all;
    const bar = `<div class="rm-bar-row">${sc && S() ? S().barHtml(sc, 'roadmap', all, lens) : ''}
      <div class="om-seg" role="group" aria-label="${H(w('group'))}">${GROUPS.map(g => `<button type="button" aria-pressed="${g === R.group}" data-rm-group="${g}">${H(w('g_' + g))}</button>`).join('')}</div></div>`;
    if (!all.length) { host.innerHTML = `<div class="rm"><p class="om-intro">${H(w('intro'))}</p><div class="om-empty"><p>${H(w('empty'))}</p></div></div>`; return; }
    const ax = axis(list);
    const groups = grouped(list.slice().sort((a, b) => a.plan.start.localeCompare(b.plan.start) || (a.rank || 0) - (b.rank || 0)));
    host.innerHTML = `<div class="rm" data-tour="studio-roadmap"><p class="om-intro">${H(w('intro'))}</p>${bar}${tiles(list)}
      ${list.length ? `<div class="rm-scroll"><div class="rm-chart" style="--rm-n:${ax.n}" role="group" aria-label="${H(w('plan_of'))} ${list.length}">${headHtml(ax)}
        ${groups.map(g => `<section class="rm-group" data-rm-group-key="${H(g.key)}">${R.group === 'none' ? '' : `<div class="rm-row rm-group-head"><div class="rm-left">${g.person ? face(g.person) : ''}<strong>${H(g.name)}</strong>${g.sub ? `<span class="rm-who">${H(g.sub)}</span>` : ''}<span class="om-side-count">${g.items.length}</span></div><div class="rm-track"></div></div>`}
          ${g.items.map(it => rowHtml(it, ax)).join('')}</section>`).join('')}</div></div>${legend()}`
        : `<div class="om-empty"><p>${H(w('empty_lens'))}</p></div>`}</div>`;
  }

  // ── Saving ─────────────────────────────────────────────────────────────────
  async function save(body){
    try { await post('/api/studio/backlog', body); toast(w('saved')); }
    catch (e) { toast((e && e.message) || String(e)); return; }
    R.edit = '';
    if (R.opts && R.opts.reload) await R.opts.reload();
  }
  function bind(host){
    if (host.dataset.rmBound) return;
    host.dataset.rmBound = '1';
    host.addEventListener('click', ev => {
      const el = ev.target.closest('[data-rm-group],[data-rm-edit],[data-rm-close],[data-rm-propose],[data-rm-open]');
      if (!el || !host.contains(el)) return;
      if (el.dataset.rmGroup) { R.group = el.dataset.rmGroup; store.set('sp-rm-group', R.group); paint(); return; }
      if (el.dataset.rmEdit) {
        R.edit = R.edit === el.dataset.rmEdit ? '' : el.dataset.rmEdit; paint();
        const focus = R.edit ? host.querySelector('[data-rm-panel] input, [data-rm-panel] button') : host.querySelector(`[data-rm-row="${CSS.escape(el.dataset.rmEdit)}"] .rm-title`);
        if (focus) focus.focus();
        return;
      }
      if (el.hasAttribute('data-rm-close')) { const id = R.edit; R.edit = ''; paint(); const back = host.querySelector(`[data-rm-row="${CSS.escape(id)}"] .rm-title`); if (back) back.focus(); return; }
      if (el.dataset.rmPropose) { void save({ id: el.dataset.rmPropose, start: '', weeks: '' }); return; }
      if (el.dataset.rmOpen && R.opts && R.opts.openUseCase) R.opts.openUseCase(el.dataset.rmOpen);
    });
    host.addEventListener('submit', ev => {
      const form = ev.target.closest('[data-rm-form]');
      if (!form) return;
      ev.preventDefault();
      const fd = new FormData(form), it = R.items.find(i => i.id === form.dataset.rmForm) || {};
      const body = { id: form.dataset.rmForm, weeks: Number(fd.get('weeks')) || '', assignee: String(fd.get('assignee') || ''), status: String(fd.get('status') || 'idea') };
      // Only a start that was changed becomes a fixed one; saving the other fields keeps a proposal a proposal.
      if (String(fd.get('start') || '') !== (it.plan || {}).start || !(it.plan || {}).auto) body.start = String(fd.get('start') || '');
      if (it.plan && it.plan.auto && body.weeks === it.plan.weeks && !it.weeks) delete body.weeks;
      void save(body);
    });
    host.addEventListener('keydown', ev => { if (ev.key === 'Escape' && R.edit && ev.target.closest('[data-rm-panel]')) { ev.stopPropagation(); host.querySelector('[data-rm-close]').click(); } });
  }
  document.addEventListener('sp-lens-change', ev => { if (ev.detail && ev.detail.surface === 'roadmap') paint(); });

  async function render(host, opts){
    R.host = host; R.opts = opts || {}; R.items = R.opts.items || []; R.teams = R.opts.teams || [];
    bind(host);
    paint();                                     // at once, with what is known
    if (!S()) return;
    try { const sc = await S().load(); if (R.host === host) { R.sc = sc; paint(); } } catch (_e) {}
  }
  window.SPRoadmap = { render };
})();
