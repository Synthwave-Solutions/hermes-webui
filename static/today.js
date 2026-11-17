/* Start of the day on the Studio overview, plus counters in the navigation.

   Adds to the overview (static/workplace.js) what a first visit needs:
   - one place to ask, with three starters that fill the field;
   - "Wacht op jou": what is waiting for this person right now.
   The same counts show as a small badge on My approvals and Governance in the
   rail, so waiting work is visible from every screen.

   Nothing is stored. Every list comes from routes the viewer may already read;
   a source the viewer may not read is left out. */
(function(){
  'use strict';
  const NL = {
    ask_title: 'Waar kan ik je mee helpen?', ask_placeholder: 'Bijvoorbeeld: maak een offerte voor…', ask_send: 'Stel je vraag',
    ask_hint: 'Voorbeelden om mee te beginnen',
    s1: 'Vat mijn mail van vandaag samen', s2: 'Wat staat er vandaag in mijn agenda?', s3: 'Plan mijn week',
    wait_title: 'Wacht op jou', wait_none: 'Niets wacht op jou.', wait_all: 'Alles bekijken', view: 'Bekijk',
    wait_review: 'Klaar voor jouw controle', wait_input: 'Heeft jouw antwoord nodig', wait_screen: 'Vraagt je om mee te kijken',
    wait_access_one: '1 toegangsverzoek wacht op een besluit', wait_access_many: '{n} toegangsverzoeken wachten op een besluit',
    wait_mine_one: 'Je eigen verzoek wacht op goedkeuring', wait_mine_many: 'Je {n} eigen verzoeken wachten op goedkeuring',
    sub_none: 'Niets wacht op jou.', sub_one: 'Eén ding wacht op jou.', sub_many: '{n} dingen wachten op jou.',
    badge_one: '1 wacht op jou', badge_many: '{n} wachten op jou'
  };
  const EN = {
    ask_title: 'What can I help you with?', ask_placeholder: 'For example: draft a quote for…', ask_send: 'Ask your question',
    ask_hint: 'Examples to start with',
    s1: 'Summarise my email today', s2: 'What is on my calendar today?', s3: 'Plan my week',
    wait_title: 'Waiting on you', wait_none: 'Nothing is waiting on you.', wait_all: 'View all', view: 'View',
    wait_review: 'Ready for your review', wait_input: 'Needs your answer', wait_screen: 'Asks you to take a look',
    wait_access_one: '1 access request is waiting for a decision', wait_access_many: '{n} access requests are waiting for a decision',
    wait_mine_one: 'Your own request is waiting for approval', wait_mine_many: 'Your {n} own requests are waiting for approval',
    sub_none: 'Nothing is waiting on you.', sub_one: 'One thing is waiting on you.', sub_many: '{n} things are waiting on you.',
    badge_one: '1 waiting on you', badge_many: '{n} waiting on you'
  };
  function lang(){ try { return String(localStorage.getItem('hermes-lang') || document.documentElement.lang || 'nl').slice(0, 2); } catch (_e) { return 'nl'; } }
  function w(key, vars){
    let s = (lang() === 'en' ? EN : NL)[key] || NL[key] || key;
    Object.entries(vars || {}).forEach(([k, v]) => { s = s.replace('{' + k + '}', String(v)); });
    return s;
  }
  const H = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const allowed = panel => !!(window.SynthPulseWorkspace && window.SynthPulseWorkspace.allowed(panel));
  const get = url => (typeof api === 'function' ? api(url, { timeoutToast: false, redirect401: false }) : Promise.reject()).catch(() => null);

  const state = { items: null, mine: 0, decide: 0, at: 0, loading: null };
  let root = null;

  function botLabel(name){
    try { if (name && typeof _cronBotTitle === 'function') return _cronBotTitle(name); } catch (_e) { /* fall through */ }
    return name || '';
  }
  async function load(force){
    if (state.loading) return state.loading;
    if (!force && state.items && Date.now() - state.at < 20000) return state;
    state.loading = (async () => {
      const board = typeof _botWorkQuery === 'function' ? _botWorkQuery() : '';
      const [tasks, screens, mine, queue] = await Promise.all([
        get('/api/kanban/waiting' + board), get('/api/bot-screen/status'),
        get('/api/governance/approvals/mine'), get('/api/governance/approvals')]);
      const items = [];
      ((screens && screens.screens) || []).filter(r => r && r.state === 'waiting' && r.rights && r.rights.control).forEach(r =>
        items.push({ title: botLabel(r.bot), sub: r.reason || w('wait_screen'), go: 'approvals' }));
      ((tasks && tasks.tasks) || []).forEach(task =>
        items.push({ title: task.title || task.id, go: 'approvals',
          sub: [botLabel(task.assignee), w(task.status === 'blocked' ? 'wait_input' : 'wait_review')].filter(Boolean).join(' · ') }));
      state.mine = ((mine && mine.requests) || []).filter(r => String((r && r.status) || '').toLowerCase() === 'pending').length;
      state.decide = Array.isArray(queue && queue.pending) ? queue.pending.length : 0;
      if (state.decide) items.unshift({ title: w(state.decide === 1 ? 'wait_access_one' : 'wait_access_many', { n: state.decide }), sub: '', go: 'governance' });
      if (state.mine) items.push({ title: w(state.mine === 1 ? 'wait_mine_one' : 'wait_mine_many', { n: state.mine }), sub: '', go: 'approvals' });
      state.items = items; state.at = Date.now();
      return state;
    })();
    try { return await state.loading; } finally { state.loading = null; }
  }
  // What needs this person: their own pending requests are shown, but only work
  // that asks for an action from them counts.
  function count(){ return state.items ? state.items.length - (state.mine ? 1 : 0) : 0; }

  function badge(panel, n){
    document.querySelectorAll('.nav-tab[data-panel="' + panel + '"]').forEach(tab => {
      let el = tab.querySelector('.sp-nav-count');
      if (!n) { if (el) el.remove(); return; }
      if (!el) { el = document.createElement('span'); el.className = 'sp-nav-count'; tab.appendChild(el); }
      el.textContent = n > 99 ? '99+' : String(n);
      el.title = w(n === 1 ? 'badge_one' : 'badge_many', { n });
    });
  }
  function paintBadges(){
    if (!state.items) return;
    badge('approvals', count() - state.decide);
    badge('governance', state.decide);
  }

  function waitingHtml(){
    if (!state.items) return '<p class="sp-today-note" aria-busy="true">…</p>';
    if (!state.items.length) return '<p class="sp-today-note">' + H(w('wait_none')) + '</p>';
    return '<ul class="sp-today-list">' + state.items.slice(0, 4).map(it =>
      '<li><span class="sp-today-item"><span class="sp-today-item-title">' + H(it.title) + '</span>' +
      (it.sub ? '<span class="sp-today-item-sub">' + H(it.sub) + '</span>' : '') + '</span>' +
      '<button type="button" class="sm-btn" data-today-go="' + H(it.go) + '">' + H(w('view')) + '</button></li>').join('') + '</ul>' +
      (state.items.length > 4 ? '<button type="button" class="om-link sp-today-more" data-today-go="approvals">' + H(w('wait_all')) + '</button>' : '');
  }
  function paintWaiting(){
    if (!root) return;
    const box = root.querySelector('[data-today-waiting]');
    if (box) box.innerHTML = waitingHtml();
    const n = root.querySelector('[data-today-count]');
    if (n) { n.textContent = state.items && state.items.length ? String(state.items.length) : ''; n.hidden = !(state.items && state.items.length); }
    const sub = document.querySelector('[data-today-sub]');
    if (sub && state.items) { const c = count(); sub.textContent = w(c === 0 ? 'sub_none' : c === 1 ? 'sub_one' : 'sub_many', { n: c }); sub.hidden = false; }
  }
  async function refresh(force){
    await load(force);
    paintWaiting(); paintBadges();
  }

  async function ask(text){
    text = String(text || '').trim();
    if (!text || typeof switchPanel !== 'function') return;
    await switchPanel('chat');
    // A question from the overview starts its own conversation, never a reply in an open one.
    if (typeof S !== 'undefined' && S.session && Array.isArray(S.messages) && S.messages.length && typeof newSession === 'function') await newSession(false);
    const composer = document.getElementById('msg');
    if (!composer || composer.disabled || composer.readOnly) return;
    composer.value = text;
    composer.dispatchEvent(new Event('input', { bubbles: true }));
    composer.focus();
    if (typeof send === 'function') await send();
  }

  function build(){
    const el = document.createElement('div');
    el.className = 'sp-today';
    const askHtml = allowed('chat') ? '<section class="wp-card sp-today-ask" aria-labelledby="spTodayAskTitle">' +
      '<h3 id="spTodayAskTitle">' + H(w('ask_title')) + '</h3>' +
      '<form class="sp-today-form" data-today-form><label class="sr-only" for="spTodayInput">' + H(w('ask_title')) + '</label>' +
      '<input id="spTodayInput" type="text" autocomplete="off" maxlength="4000" placeholder="' + H(w('ask_placeholder')) + '">' +
      '<button type="submit" class="sm-btn primary" aria-label="' + H(w('ask_send')) + '" title="' + H(w('ask_send')) + '">' +
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/></svg></button></form>' +
      '<div class="sp-today-starters" role="group" aria-label="' + H(w('ask_hint')) + '">' + ['s1', 's2', 's3'].map(k =>
        '<button type="button" class="sp-today-starter" data-today-starter>' + H(w(k)) + '</button>').join('') + '</div></section>' : '';
    el.innerHTML = askHtml + '<section class="wp-card sp-today-waiting" aria-labelledby="spTodayWaitTitle">' +
      '<header class="wp-card-head"><h3 id="spTodayWaitTitle">' + H(w('wait_title')) + '</h3><span class="sp-nav-count sp-today-count" data-today-count hidden></span></header>' +
      '<div data-today-waiting>' + waitingHtml() + '</div></section>';
    el.classList.toggle('sp-today-single', !askHtml);
    el.addEventListener('submit', ev => {
      if (!ev.target.matches('[data-today-form]')) return;
      ev.preventDefault();
      const input = el.querySelector('#spTodayInput'), text = input.value;
      input.value = '';
      void ask(text);
    });
    el.addEventListener('click', ev => {
      const b = ev.target.closest('button');
      if (!b) return;
      if (b.hasAttribute('data-today-starter')) {
        const input = el.querySelector('#spTodayInput');
        input.value = b.textContent; input.focus(); input.setSelectionRange(input.value.length, input.value.length);
        return;
      }
      if (b.dataset.todayGo && typeof switchPanel === 'function') {
        const panel = b.dataset.todayGo;
        void switchPanel(allowed(panel) ? panel : 'approvals');
      }
    });
    return el;
  }
  // The overview repaints while its lists arrive. The same node moves into every
  // repaint, so a half-typed question and the caret survive.
  function mount(slot){
    if (!slot) return;
    if (!root || root.dataset.lang !== lang()) { root = build(); root.dataset.lang = lang(); }
    const input = root.querySelector('#spTodayInput');
    const focused = input && document.activeElement === input ? [input.selectionStart, input.selectionEnd] : null;
    slot.replaceChildren(root);
    if (focused) { input.focus({ preventScroll: true }); input.setSelectionRange(focused[0], focused[1]); }
    paintWaiting();
    void refresh(false);
  }

  window.SPToday = { mount, refresh, count };
  // Badges stay current without opening the overview: on load, when the tab
  // becomes visible again and after every panel switch that may have changed them.
  function tick(){ if (!document.hidden) void refresh(false); }
  if (document.readyState === 'complete') setTimeout(tick, 2500); else window.addEventListener('load', () => setTimeout(tick, 2500));
  document.addEventListener('visibilitychange', tick);
  setInterval(tick, 120000);
})();
