/* The personal intake as a conversation (15 Nov 2026).

   The same intake as "About you" in Studio, but asked the way a colleague
   would: one question at a time, answers as chips, every question can be
   skipped and every answer changed. It is offered once at first sign-in and
   stays available from Studio. Saving goes through the existing intake
   (POST /api/studio/profile, op "me"), so the agent keeps one short entry in
   the person's user profile exactly as before.

   Right after saving the agent proposes first tasks: one to finish now, two
   recurring ones and a few that many people start with. Choosing a card puts
   that request ready in the chat; nothing runs until the person sends it. The
   cards stay on the empty chat for two weeks.

   The shape of this flow follows the onboarding of Nod, n8n's open source
   personal agent (Apache 2.0, https://github.com/n8n-io/nod). */
(function(){
  'use strict';
  const NL = {
    name: 'Kennismaking met de Super Agent', close: 'Sluiten', later: 'Later', start: 'Begin', send: 'Verstuur', next: 'Verder', skip: 'Niet nu',
    skipped: 'Overgeslagen', edit: 'Antwoord wijzigen', other: 'Iets anders', other_ph: 'Typ het hier', step: 'Vraag {n} van {m}',
    hello: 'Hoi {name}. Ik ben de Super Agent.', hello_plain: 'Hoi. Ik ben de Super Agent.',
    hello2: 'Vertel me in twee minuten iets over jezelf, dan passen mijn antwoorden en voorstellen vanaf vandaag beter bij jou.',
    hello3: 'Elke vraag kun je overslaan. Ik onthoud een korte samenvatting in je gebruikersprofiel; die kun je altijd inzien en aanpassen.',
    q_title: 'Wat is je functie?', q_title_ph: 'Bijvoorbeeld: accountmanager',
    q_wishes: 'Wat wil je als eerste uit handen geven? Kies er zoveel als je wilt.',
    w_mail: 'Mail en chat bijhouden', w_calendar: 'Mijn agenda beheren', w_meetings: 'Overleggen en mijn dag voorbereiden',
    w_documents: 'Documenten en voorstellen maken', w_research: 'Dingen voor me uitzoeken', w_recurring: 'Terugkerende taken overnemen',
    q_week: 'Wat doe je elke week opnieuw? Beschrijf het in een paar zinnen, dan haal ik er de taken uit.',
    q_week_ph: 'Bijvoorbeeld: elke maandag haal ik de openstaande posten uit Exact en bel ik klanten na...',
    week_found: 'Ik haal hier deze taken uit: {tasks}. Je kunt ze later aanvullen in Studio.',
    week_none: 'Daar kon ik nu geen taken uit halen. Je kunt ze later toevoegen in Studio.',
    reading: 'De agent leest mee',
    q_tools: 'Met welke systemen werk je?',
    q_tone: 'Hoe spreek ik je aan?', t_informal: 'Informeel (je)', t_formal: 'Formeel (u)',
    q_length: 'En hoe wil je mijn antwoorden?', len_short: 'Kort en bondig', len_detailed: 'Uitgebreid',
    q_never: 'Wat mag ik nooit doen zonder het je eerst te vragen?',
    n_send: 'Mails of berichten versturen', n_calendar: 'Afspraken maken of wijzigen', n_delete: 'Bestanden verwijderen', n_pay: 'Iets kopen of betalen',
    q_ai: 'Tot slot: hoeveel ervaring heb je met AI?', ai_beginner: 'Beginner', ai_regular: 'Ik gebruik het regelmatig', ai_advanced: 'Ervaren',
    saving: 'Ik sla het op en kijk wat ik voor je kan doen',
    saved: 'Dank je. Dit onthoud ik over je:', saved_named: 'Dank je, {name}. Dit onthoud ik over je:',
    not_written: 'Je gebruikersprofiel is vol, dus de samenvatting staat alleen in Studio. Ruim je profiel op, dan onthoud ik hem ook in elk gesprek.',
    save_failed: 'Opslaan lukte niet. Probeer het opnieuw.', retry: 'Opnieuw proberen',
    pick: 'Kies een kaart: ik zet het verzoek klaar in de chat en begin pas als jij het verstuurt.',
    b_now: 'Nu', b_ongoing: 'Herhaalt', b_mail: 'Mail en agenda', more: 'Veel gekozen',
    to_chat: 'Naar de chat', later_toast: 'Je vindt de kennismaking terug in Studio onder Over jou.',
    for_you: 'Voorgesteld voor jou', hide_cards: 'Voorstellen verbergen', as_chat: 'Liever als gesprek'
  };
  const EN = {
    name: 'Getting to know the Super Agent', close: 'Close', later: 'Later', start: 'Start', send: 'Send', next: 'Continue', skip: 'Not now',
    skipped: 'Skipped', edit: 'Edit answer', other: 'Something else', other_ph: 'Type it here', step: 'Question {n} of {m}',
    hello: 'Hi {name}. I am the Super Agent.', hello_plain: 'Hi. I am the Super Agent.',
    hello2: 'Tell me a bit about yourself in two minutes, so my answers and proposals fit you better from today.',
    hello3: 'You can skip every question. I keep a short summary in your user profile; you can always read and change it.',
    q_title: 'What is your job title?', q_title_ph: 'For example: account manager',
    q_wishes: 'What would you like to take off your plate first? Pick as many as you like.',
    w_mail: 'Stay on top of mail and chat', w_calendar: 'Manage my calendar', w_meetings: 'Prepare my meetings and my day',
    w_documents: 'Make documents and proposals', w_research: 'Research things for me', w_recurring: 'Take over recurring tasks',
    q_week: 'What do you do again every week? Describe it in a few sentences and I will pull out the tasks.',
    q_week_ph: 'For example: every Monday I pull the open items from Exact and call customers...',
    week_found: 'I found these tasks: {tasks}. You can add to them later in Studio.',
    week_none: 'I could not find tasks in that right now. You can add them later in Studio.',
    reading: 'The agent is reading',
    q_tools: 'Which systems do you work with?',
    q_tone: 'How should I address you?', t_informal: 'Informal', t_formal: 'Formal',
    q_length: 'And how do you want my answers?', len_short: 'Short and to the point', len_detailed: 'Detailed',
    q_never: 'What may I never do without asking you first?',
    n_send: 'Send mails or messages', n_calendar: 'Make or change appointments', n_delete: 'Delete files', n_pay: 'Buy or pay for something',
    q_ai: 'Finally: how much experience do you have with AI?', ai_beginner: 'Beginner', ai_regular: 'I use it regularly', ai_advanced: 'Experienced',
    saving: 'I am saving this and looking at what I can do for you',
    saved: 'Thank you. This is what I remember about you:', saved_named: 'Thank you, {name}. This is what I remember about you:',
    not_written: 'Your user profile is full, so the summary is only kept in Studio. Clean up your profile and I will also remember it in every conversation.',
    save_failed: 'Saving did not work. Please try again.', retry: 'Try again',
    pick: 'Pick a card: I put the request ready in the chat and only start when you send it.',
    b_now: 'Now', b_ongoing: 'Repeats', b_mail: 'Mail and calendar', more: 'Popular',
    to_chat: 'Go to the chat', later_toast: 'You can find this introduction again in Studio under About you.',
    for_you: 'Suggested for you', hide_cards: 'Hide suggestions', as_chat: 'Rather as a conversation'
  };
  const lang = () => ((document.documentElement.lang || 'nl').toLowerCase().startsWith('en') ? 'en' : 'nl');
  const w = (k, v) => { let t = (lang() === 'en' ? EN : NL)[k] || NL[k] || k; if (v) for (const [a, b] of Object.entries(v)) t = t.replace('{' + a + '}', b); return t; };
  const H = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const toast = m => { if (typeof showToast === 'function') showToast(m); };
  const call = (p, o) => api(p, Object.assign({ timeoutToast: false, redirect401: false }, o || {}));
  const post = (p, b) => call(p, { method: 'POST', body: JSON.stringify(b) });
  const calm = () => { try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (_e) { return false; } };

  const WISHES = ['mail', 'calendar', 'meetings', 'documents', 'research', 'recurring'];
  const NEVER = ['n_send', 'n_calendar', 'n_delete', 'n_pay'];
  const COMMON_TOOLS = ['Outlook', 'Excel', 'Word', 'Teams', 'Google Workspace', 'SharePoint', 'Exact', 'AFAS', 'Salesforce', 'HubSpot', 'Notion', 'Slack'];
  const CARD_DAYS = 14;
  const DRAFT = 'sp-intake-chat';

  // One entry per question. `get` reads the current value from the intake, `set`
  // stores an answer, `say` is the text of the person's own bubble.
  const QUESTIONS = [
    { key: 'title', type: 'text', max: 100, get: d => d.role.title || '', set: (d, v) => { d.role.title = v; }, say: (d, v) => v },
    { key: 'wishes', type: 'multi', other: 120, options: () => WISHES.map(x => [x, w('w_' + x)]),
      get: d => ({ picked: d.wishes || [], other: d.wish_other || '' }),
      set: (d, v) => { d.wishes = v.picked; d.wish_other = v.other; },
      say: (d, v) => v.picked.map(x => w('w_' + x)).concat(v.other ? [v.other] : []).join(', ') },
    { key: 'week', type: 'long', max: 3000, get: d => d.week || '', set: (d, v) => { d.week = v; }, say: (d, v) => v },
    { key: 'tools', type: 'multi', other: 40, options: (d, ctx) => [...new Set([...(d.tools || []), ...((ctx && ctx.org_systems) || []), ...COMMON_TOOLS])].slice(0, 24).map(x => [x, x]),
      get: d => ({ picked: d.tools || [], other: '' }),
      set: (d, v) => { d.tools = [...new Set(v.picked.concat(v.other ? [v.other] : []))]; },
      say: (d, v) => v.picked.concat(v.other ? [v.other] : []).join(', ') },
    { key: 'tone', type: 'single', options: () => [['informal', w('t_informal')], ['formal', w('t_formal')]],
      get: d => d.prefs.tone || '', set: (d, v) => { d.prefs.tone = v; }, say: (d, v) => w('t_' + v) },
    { key: 'length', type: 'single', options: () => [['short', w('len_short')], ['detailed', w('len_detailed')]],
      get: d => d.prefs.length || '', set: (d, v) => { d.prefs.length = v; }, say: (d, v) => w('len_' + v) },
    { key: 'never', type: 'multi', other: 160, options: () => NEVER.map(x => [x, w(x)]),
      get: d => ({ picked: d._never || [], other: d._never_other || '' }),
      set: (d, v) => { d._never = v.picked; d._never_other = v.other; d.prefs.never = v.picked.map(x => w(x)).concat(v.other ? [v.other] : []).join('; ').slice(0, 300); },
      say: (d, v) => v.picked.map(x => w(x)).concat(v.other ? [v.other] : []).join(', ') },
    { key: 'ai', type: 'single', options: () => [['beginner', w('ai_beginner')], ['regular', w('ai_regular')], ['advanced', w('ai_advanced')]],
      get: d => d.literacy.self || '', set: (d, v) => { d.literacy.self = v; }, say: (d, v) => w('ai_' + v) }
  ];

  const C = { root: null, phase: 'welcome', at: 0, d: null, ctx: null, done: {}, typing: false, busy: false, pick: null, result: null, cards: null,
              failed: false, auto: false, timer: 0, opener: null };

  function firstName(){
    const me = window.__GOV_ME__ || {};
    const full = String(me.display_name || me.name || '').trim();
    return full && !full.includes('@') ? full.split(/\s+/)[0] : '';
  }
  function keep(){ try { localStorage.setItem(DRAFT, JSON.stringify({ d: C.d, done: C.done, at: C.at })); } catch (_e) {} }
  function drop(){ try { localStorage.removeItem(DRAFT); } catch (_e) {} }
  function empty(q, v){ return q.type === 'multi' ? !(v.picked.length || v.other) : !String(v || '').trim(); }

  function avatar(){ return '<span class="ic-avatar" aria-hidden="true"><img src="static/synthwave-symbol.png" alt="" width="28" height="28"></span>'; }
  function agent(html, extra){ return `<div class="ic-row ic-agent ${extra || ''}">${avatar()}<div class="ic-bubble">${html}</div></div>`; }
  function mine(text, i){
    return `<div class="ic-row ic-me"><div class="ic-bubble">${H(text)}</div><button type="button" class="ic-edit" data-ic-edit="${i}" aria-label="${H(w('edit'))}" title="${H(w('edit'))}">✎</button></div>`;
  }
  function dots(label){ return agent(`<span class="ic-dots" role="status" aria-label="${H(label || '')}"><i></i><i></i><i></i></span>`, 'ic-typing'); }

  function transcript(){
    const name = firstName();
    let html = agent(H(name ? w('hello', { name }) : w('hello_plain'))) + agent(H(w('hello2'))) + agent(H(w('hello3')));
    if (C.phase === 'welcome') return html;
    QUESTIONS.forEach((q, i) => {
      const done = C.done[q.key];
      if (i > C.at && (!done || C.phase === 'ask')) return;
      if (i === C.at && C.phase === 'ask' && C.typing) { html += dots(''); return; }
      if (!done && !(i === C.at && C.phase === 'ask')) return;
      html += agent(H(w('q_' + q.key)));
      if (done && !(i === C.at && C.phase === 'ask')) {
        html += mine(done.skipped ? w('skipped') : done.text, i);
        if (q.key === 'week' && done.note) html += agent(H(done.note));
      }
    });
    if (C.busy && C.phase === 'ask') html += dots(w('reading'));
    if (C.phase === 'saving') html += dots(w('saving'));
    if (C.phase === 'cards') html += cardsHtml();
    return html;
  }

  function badge(kind){ return `<span class="ic-badge ic-badge-${kind}">${H(w('b_' + kind))}</span>`; }
  function card(title, kind){ return `<button type="button" class="ic-card" data-ic-card="${H(title)}">${badge(kind)}<span>${H(title)}</span></button>`; }
  function cardsHtml(){
    const r = C.result || {}, t = C.cards || {}, name = firstName();
    let html = '';
    const note = String(r.note || '').replace(/^Intake \(Studio\):\s*/, '').trim();
    if (note) html += agent(`${H(name ? w('saved_named', { name }) : w('saved'))}<blockquote class="ic-note">${H(note)}</blockquote>`);
    if (r.note_written === false) html += agent(H(w('not_written')), 'ic-warn');
    const cards = (t.tasks || []).map(x => card(x.title, x.kind === 'now' ? 'now' : 'ongoing')).join('');
    const more = (t.common || []).map(x => card(x, 'ongoing')).join('') + (t.mail ? card(t.mail, 'mail') : '');
    html += agent(`${H(t.intro || '')}<div class="ic-cards">${cards}</div>${more ? `<p class="ic-more">${H(w('more'))}</p><div class="ic-cards">${more}</div>` : ''}<p class="ic-hint">${H(w('pick'))}</p>`, 'ic-wide');
    return html;
  }

  function chips(q, v){
    const multi = q.type === 'multi';
    const picked = multi ? v.picked : [v];
    return `<div class="ic-chips" role="group">${q.options(C.d, C.ctx).map(([val, label]) => `<button type="button" class="in-chip ic-chip" aria-pressed="${picked.includes(val)}" data-ic-chip="${H(val)}">${H(label)}</button>`).join('')}</div>`;
  }
  function footer(){
    if (C.phase === 'welcome') return `<div class="ic-actions"><button type="button" class="ic-btn" data-ic-later>${H(w('later'))}</button><button type="button" class="ic-btn primary" data-ic-start>${H(w('start'))}</button></div>`;
    if (C.phase === 'cards') return `<div class="ic-actions"><span></span><button type="button" class="ic-btn primary" data-ic-close>${H(w('to_chat'))}</button></div>`;
    if (C.phase === 'saving') return C.failed ? `<div class="ic-actions"><span class="ic-error" role="alert">${H(w('save_failed'))}</span><button type="button" class="ic-btn primary" data-ic-retry>${H(w('retry'))}</button></div>` : '';
    if (C.typing || C.busy) return '';
    const q = QUESTIONS[C.at], v = C.pick;
    const skip = `<button type="button" class="ic-btn quiet" data-ic-skip>${H(w('skip'))}</button>`;
    if (q.type === 'single') return `${chips(q, v)}<div class="ic-actions">${skip}<span></span></div>`;
    if (q.type === 'multi') return `${chips(q, v)}<form class="ic-form" data-ic-form><input data-ic-other maxlength="${q.other}" value="${H(v.other)}" placeholder="${H(w('other'))}" aria-label="${H(w('other'))}">
      <div class="ic-actions">${skip}<button type="submit" class="ic-btn primary">${H(w('next'))}</button></div></form>`;
    const field = q.type === 'long'
      ? `<textarea data-ic-input rows="3" maxlength="${q.max}" placeholder="${H(w('q_' + q.key + '_ph'))}" aria-label="${H(w('q_' + q.key))}">${H(v)}</textarea>`
      : `<input data-ic-input maxlength="${q.max}" value="${H(v)}" placeholder="${H(w('q_' + q.key + '_ph'))}" aria-label="${H(w('q_' + q.key))}">`;
    return `<form class="ic-form" data-ic-form>${field}<div class="ic-actions">${skip}<button type="submit" class="ic-btn primary">${H(w('send'))}</button></div></form>`;
  }
  function progress(){
    if (C.phase !== 'ask') return '';
    return `<span class="ic-progress" aria-label="${H(w('step', { n: C.at + 1, m: QUESTIONS.length }))}">${QUESTIONS.map((_q, i) => `<i class="${i < C.at ? 'done' : i === C.at ? 'now' : ''}"></i>`).join('')}</span>`;
  }

  function paint(focus){
    if (!C.root) return;
    C.root.querySelector('[data-ic-progress]').innerHTML = progress();
    const log = C.root.querySelector('[data-ic-log]');
    log.innerHTML = transcript();
    C.root.querySelector('[data-ic-foot]').innerHTML = footer();
    log.scrollTop = log.scrollHeight;
    if (focus !== false) {
      const el = C.root.querySelector('[data-ic-input]') || C.root.querySelector('[data-ic-start]') || (C.phase === 'cards' && C.root.querySelector('[data-ic-card]')) || C.root.querySelector('.ic-chip');
      if (el) try { el.focus({ preventScroll: true }); } catch (_e) {}
    }
  }

  function ask(i){
    clearTimeout(C.timer);
    C.phase = 'ask'; C.at = i; C.pick = QUESTIONS[i].get(C.d);
    if (QUESTIONS[i].type === 'multi') C.pick = { picked: [...C.pick.picked], other: C.pick.other };
    C.typing = !calm(); keep(); paint(false);
    if (C.typing) C.timer = setTimeout(() => { C.typing = false; paint(); }, 600);
    else paint();
  }
  function advance(){
    const next = QUESTIONS.findIndex((q, i) => i > C.at && !C.done[q.key]);
    const first = QUESTIONS.findIndex(q => !C.done[q.key]);
    const go = next >= 0 ? next : first;
    if (go >= 0) return ask(go);
    return save();
  }
  async function answer(value, skipped){
    const q = QUESTIONS[C.at];
    if (!skipped && empty(q, value)) skipped = true;
    if (!skipped) q.set(C.d, value);
    C.done[q.key] = skipped ? { skipped: true } : { text: q.say(C.d, value) };
    if (q.key === 'week' && !skipped) {
      C.busy = true; C.phase = 'ask'; C.at = QUESTIONS.length; paint(false); C.at = QUESTIONS.indexOf(q);
      try {
        const got = (await post('/api/studio/profile', { op: 'me_extract', text: value })).tasks || [];
        if (got.length) {
          const known = new Set((C.d.tasks || []).map(t => t.name.toLowerCase()));
          C.d.tasks = (C.d.tasks || []).concat(got.filter(t => !known.has(t.name.toLowerCase()))).slice(0, 20);
          C.done.week.note = w('week_found', { tasks: got.map(t => t.name).join(', ') });
        } else C.done.week.note = w('week_none');
      } catch (_e) { C.done.week.note = w('week_none'); }
      C.busy = false;
      if (!C.root) return;
    }
    keep(); advance();
  }

  async function save(){
    clearTimeout(C.timer);
    C.phase = 'saving'; C.failed = false; C.at = QUESTIONS.length; paint(false);
    const d = C.d;
    if (!d.prefs.language) d.prefs.language = lang();
    try {
      C.result = await post('/api/studio/profile', { op: 'me', role: d.role, tasks: d.tasks, tools: d.tools, prefs: d.prefs, literacy: d.literacy,
                                                     wishes: d.wishes || [], wish_other: d.wish_other || '' });
    } catch (_e) { if (C.root) { C.failed = true; paint(); } return; }
    drop();
    try { C.cards = await post('/api/studio/profile', { op: 'me_first_tasks', lang: lang() }); } catch (_e) { C.cards = null; }
    try {
      if (window.SPStudio && typeof _currentPanel === 'string' && _currentPanel === 'studio') window.SPStudio.load();
      else if (window.SPStudio && window.SPStudio.refreshCounts) window.SPStudio.refreshCounts();
    } catch (_e) {}
    if (!C.root) { showStarters(C.cards); return; }
    C.phase = 'cards'; paint();
    showStarters(C.cards);
  }

  function draftInChat(text){
    const box = document.getElementById('msg');
    if (!box || box.disabled || box.readOnly) return;
    if (!box.value.trimEnd().endsWith(text)) {
      box.value += (box.value.trim() ? '\n\n' : '') + text;
      box.dispatchEvent(new Event('input', { bubbles: true }));
    }
    box.focus();
    try { box.setSelectionRange(box.value.length, box.value.length); } catch (_e) {}
  }
  async function useCard(title){
    close(true);
    try {
      if (typeof switchPanel === 'function') await switchPanel('chat');
      const used = typeof S !== 'undefined' && S && Array.isArray(S.messages) && S.messages.length;
      if (used && typeof newSession === 'function') await newSession(false);
    } catch (_e) {}
    draftInChat(title);
  }

  function close(silent){
    clearTimeout(C.timer);
    if (!C.root) return;
    const saved = C.phase === 'cards' || !!C.result;
    C.root.remove(); C.root = null;
    document.removeEventListener('keydown', onKey, true);
    if (!saved && C.auto) post('/api/studio/profile', { op: 'me_onboarding', dismissed: true }).catch(() => {});
    if (!saved && !silent) toast(w('later_toast'));
    if (C.opener && document.contains(C.opener)) try { C.opener.focus(); } catch (_e) {}
    C.opener = null;
  }
  function onKey(ev){
    if (!C.root) return;
    if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); close(); return; }
    if (ev.key === 'Enter' && C.typing) { clearTimeout(C.timer); C.typing = false; paint(); ev.preventDefault(); return; }
    if (ev.key === 'Tab') {
      const items = [...C.root.querySelectorAll('button, input, textarea')].filter(el => !el.disabled && el.offsetParent !== null);
      if (!items.length) return;
      const first = items[0], last = items[items.length - 1];
      if (ev.shiftKey && document.activeElement === first) { ev.preventDefault(); last.focus(); }
      else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
    }
  }

  function bind(root){
    root.addEventListener('click', ev => {
      const b = ev.target.closest('button'); if (!b) return;
      if (b.hasAttribute('data-ic-close')) return close(C.phase === 'cards');
      if (b.hasAttribute('data-ic-later')) return close();
      if (b.hasAttribute('data-ic-start')) return advance();
      if (b.hasAttribute('data-ic-retry')) return save();
      if (b.hasAttribute('data-ic-skip')) return answer(null, true);
      if (b.dataset.icCard) return useCard(b.dataset.icCard);
      if (b.dataset.icEdit !== undefined && !C.busy && C.phase !== 'saving') { const i = Number(b.dataset.icEdit); delete C.done[QUESTIONS[i].key]; return ask(i); }
      if (b.dataset.icChip !== undefined) {
        const q = QUESTIONS[C.at], val = b.dataset.icChip;
        if (q.type === 'single') return answer(val);
        const other = C.root.querySelector('[data-ic-other]'); if (other) C.pick.other = other.value.trim();
        C.pick.picked = C.pick.picked.includes(val) ? C.pick.picked.filter(x => x !== val) : C.pick.picked.concat([val]);
        b.setAttribute('aria-pressed', String(C.pick.picked.includes(val)));
      }
    });
    root.addEventListener('submit', ev => {
      if (!ev.target.hasAttribute('data-ic-form')) return;
      ev.preventDefault();
      const q = QUESTIONS[C.at];
      if (q.type === 'multi') { C.pick.other = (ev.target.querySelector('[data-ic-other]').value || '').trim(); return answer(C.pick); }
      answer((ev.target.querySelector('[data-ic-input]').value || '').trim());
    });
    root.addEventListener('keydown', ev => {
      // Enter sends a long answer; Shift+Enter makes a new line.
      if (ev.key === 'Enter' && !ev.shiftKey && ev.target.matches && ev.target.matches('textarea[data-ic-input]')) { ev.preventDefault(); ev.target.form.requestSubmit(); }
    });
  }

  async function open(opts){
    if (C.root) return;
    let me = (opts && opts.me) || null;
    if (!me) { try { me = await call('/api/studio/profile?who=me'); } catch (_e) { toast(w('save_failed')); return; } }
    C.ctx = me; C.auto = !!(opts && opts.auto); C.result = null; C.cards = null; C.done = {}; C.typing = false; C.busy = false; C.failed = false;
    C.d = { role: Object.assign({ title: '', team: (me.my_teams || [])[0] || '', speciality: '', seniority: '', work_type: '', focus: [], responsibilities: [] }, me.role || {}),
            tasks: me.tasks || [], tools: me.tools || [], prefs: Object.assign({ language: '', tone: '', length: '', format: '', hours: '', never: '', notes: '' }, me.prefs || {}),
            literacy: Object.assign({ self: '', score: 0, answered: false }, me.literacy || {}), wishes: me.wishes || [], wish_other: me.wish_other || '', week: '' };
    C.phase = 'welcome'; C.at = -1;
    let draft = null; try { draft = JSON.parse(localStorage.getItem(DRAFT) || 'null'); } catch (_e) {}
    if (draft && draft.d && draft.d.role && draft.d.prefs && draft.d.literacy) { C.d = Object.assign(C.d, draft.d); C.done = draft.done || {}; }
    C.opener = document.activeElement;
    const root = document.createElement('div');
    root.className = 'ic-overlay';
    root.innerHTML = `<section class="ic-panel" role="dialog" aria-modal="true" aria-label="${H(w('name'))}">
      <header class="ic-head"><strong>${H(w('name'))}</strong><span data-ic-progress></span><button type="button" class="ic-x" data-ic-close aria-label="${H(w('close'))}" title="${H(w('close'))}">✕</button></header>
      <div class="ic-log" data-ic-log aria-live="polite"></div><footer class="ic-foot" data-ic-foot></footer></section>`;
    document.body.appendChild(root);
    C.root = root; bind(root);
    document.addEventListener('keydown', onKey, true);
    if (Object.keys(C.done).length) advance(); else paint();
  }

  // ── The cards on the empty chat, for two weeks after the intake ───────────
  function showStarters(t){
    const host = document.getElementById('emptyState');
    const old = host && host.querySelector('.ic-starters'); if (old) old.remove();
    if (!host || !t || !Array.isArray(t.tasks) || !t.tasks.length) return;
    const box = document.createElement('div');
    box.className = 'ic-starters';
    box.innerHTML = `<div class="ic-starters-head"><span>${H(w('for_you'))}</span><button type="button" class="ic-x" data-ic-hide aria-label="${H(w('hide_cards'))}" title="${H(w('hide_cards'))}">✕</button></div>
      <div class="ic-cards">${t.tasks.slice(0, 3).map(x => card(x.title, x.kind === 'now' ? 'now' : 'ongoing')).join('')}</div>`;
    box.addEventListener('click', ev => {
      const b = ev.target.closest('button'); if (!b) return;
      if (b.dataset.icCard) return draftInChat(b.dataset.icCard);
      if (b.hasAttribute('data-ic-hide')) { box.remove(); post('/api/studio/profile', { op: 'me_onboarding', cards_hidden: true }).catch(() => {}); }
    });
    const grid = host.querySelector('.suggestion-grid');
    if (grid) host.insertBefore(box, grid); else host.appendChild(box);
  }

  async function boot(){
    // A split view pane is a second copy of the app: the intake shows in the main one.
    if (document.documentElement.dataset.pane === '1' || typeof api !== 'function') return;
    const until = Date.now() + 3000;
    while (window.__GOV_ME__ === undefined && Date.now() < until) await new Promise(r => setTimeout(r, 150));
    let me; try { me = await call('/api/studio/profile?who=me'); } catch (_e) { return; }
    if (!me || !me.email) return;
    const state = me.onboarding || {}, cards = me.first_tasks;
    if (cards && !state.cards_hidden_at && Date.now() / 1000 - (cards.created_at || 0) < CARD_DAYS * 86400) showStarters(cards);
    const provider = document.getElementById('onboardingOverlay');
    if (me.offer_intake && !(provider && provider.style.display !== 'none' && provider.offsetParent !== null)) open({ me, auto: true });
  }

  document.addEventListener('click', ev => {
    const b = ev.target.closest && ev.target.closest('[data-intake-chat-open]');
    if (b) { ev.preventDefault(); open(); }
  });
  window.SPIntakeChat = { open, label: () => w('as_chat') };
  if (document.readyState === 'complete') setTimeout(boot, 400); else window.addEventListener('load', () => setTimeout(boot, 400));
})();
