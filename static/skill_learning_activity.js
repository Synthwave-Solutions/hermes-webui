// Personal background-learning notices: separate from shared/model messages.
(function () {
  'use strict';
  let session = '', rows = [], failed = false, timer = null, controller = null;
  // `unavailable`: the server said this feature does not apply here (no
  // signed-in email identity, conversation not visible to this person, bad
  // request). Nothing to show and no reason to keep asking for this chat.
  // `failures`: consecutive transient failures (timeout, 5xx, network). One
  // slow reply under load is normal and stays silent; only a repeated
  // failure shows a small notice, and earlier notices are kept meanwhile.
  let unavailable = false, failures = 0;
  const openNotices = new Set();
  let generation = 0, lastFetch = 0, pending = false;
  let renderedSession = '';
  const interval = 10000;
  const tr = (key, fallback) => {
    const value = typeof t === 'function' ? t(key) : '';
    return value && value !== key ? value : fallback;
  };
  function current() {
    if (document.hidden || typeof S === 'undefined' || !S.session) return '';
    if (typeof _currentPanel !== 'undefined' && !['chat', 'sessions'].includes(_currentPanel)) return '';
    if (typeof _loadingSessionId !== 'undefined' && _loadingSessionId &&
        (_loadingSessionId !== S.session.session_id || !S.messages?.length)) return '';
    if (renderedSession !== S.session.session_id) return '';
    return String(S.session.session_id || '');
  }
  function clear() {
    document.querySelectorAll('[data-skill-learning-notice]').forEach(node => node.remove());
  }
  function insertByTime(host, card, timestamp) {
    for (const marker of host.querySelectorAll('[data-msg-idx]')) {
      const message = S.messages?.[Number(marker.dataset.msgIdx)];
      const value = message?.timestamp || message?.created_at;
      const seconds = typeof value === 'number' ? value : Date.parse(value || '') / 1000;
      if (!Number.isFinite(seconds) || seconds <= timestamp) continue;
      let row = marker;
      while (row.parentElement && row.parentElement !== host) row = row.parentElement;
      if (row.parentElement === host) { host.insertBefore(card, row); return; }
    }
    host.append(card);
  }
  function draw() {
    clear();
    const host = document.getElementById('msgInner');
    if (!host || current() !== session || !session) return;
    for (const row of rows.slice().reverse()) {
      const card = document.createElement('div');
      card.dataset.skillLearningNotice = row.id;
      card.className = 'skill-learning-notice';
      const copy = document.createElement('div');
      const inTurn = row.source === 'turn';
      const labels = [
        ['created', inTurn ? tr('skill_created', 'Skill created') : tr('skill_learning_created', 'Skill automatically created')],
        ['patched', inTurn ? tr('skill_updated', 'Skill updated') : tr('skill_learning_patched', 'Skill automatically patched')],
        ['updated', inTurn ? tr('skill_updated', 'Skill updated') : tr('skill_learning_updated', 'Skill automatically updated')],
      ];
      const named = {created: 0, patched: 0, updated: 0};
      for (const skill of row.skills || []) {
        const line = document.createElement('div');
        const label = labels.find(([key]) => key === skill.kind)[1];
        line.textContent = label + ': ' + skill.name + (skill.count > 1 ? ' × ' + skill.count : '');
        copy.append(line); named[skill.kind] += skill.count;
      }
      for (const [key, label] of labels) {
        const missing = row.counts[key] - named[key];
        if (missing <= 0) continue;
        const line = document.createElement('div');
        line.textContent = label + (missing > 1 ? ' × ' + missing : '') + ' · ' +
          tr('skill_learning_name_unknown', 'Skill name was not recorded');
        copy.append(line);
      }
      const memoryLabels = {
        memory: tr('skill_learning_memory_saved', 'Memory updated'),
        user: tr('skill_learning_user_saved', 'User profile updated'),
        soul: tr('skill_learning_soul_saved', 'Bot personality updated'),
        profile_memory: tr('skill_learning_profile_memory_saved', 'Shared bot memory updated'),
        profile_user: tr('skill_learning_profile_user_saved', 'Shared user profile updated'),
        profile_soul: tr('skill_learning_soul_saved', 'Bot personality updated'),
      };
      for (const key of row.memory || []) {
        const line = document.createElement('div');
        line.textContent = memoryLabels[key];
        copy.append(line);
      }
      const meta = document.createElement('small');
      const time = document.createElement('time');
      const date = new Date(row.created_at * 1000);
      time.dateTime = date.toISOString();
      time.textContent = date.toLocaleString();
      const origin = row.source === 'turn'
        ? tr('skill_learning_in_turn', 'This conversation · Visible only to you')
        : tr('skill_learning_private', 'Automatic · Visible only to you');
      meta.append(document.createTextNode(origin + ' · '), time);
      // Friendly card: icon + plain title up front, the itemised lines and
      // origin/time behind a Details toggle (open state survives redraws).
      card.className += ' sp-learning-card';
      const head = document.createElement('button');
      head.type = 'button'; head.className = 'sp-learning-head';
      const isOpen = openNotices.has(row.id);
      const setAria = (el, k, v) => { if (typeof el.setAttribute === 'function') el.setAttribute(k, v); };
      setAria(head, 'aria-expanded', isOpen ? 'true' : 'false');
      const icon = document.createElement('span');
      icon.className = 'sp-learning-icon'; setAria(icon, 'aria-hidden', 'true');
      const skillTotal = named.created + named.patched + named.updated +
        Math.max(0, row.counts.created - named.created) + Math.max(0, row.counts.patched - named.patched) +
        Math.max(0, row.counts.updated - named.updated);
      icon.textContent = skillTotal ? '🧩' : '🧠';
      const title = document.createElement('span');
      title.className = 'sp-learning-title';
      title.textContent = plainTitle(row, skillTotal);
      const chip = document.createElement('span');
      chip.className = 'sp-learning-chip';
      chip.textContent = '🔒 ' + copyText('private');
      const toggle = document.createElement('span');
      toggle.className = 'sp-learning-toggle';
      toggle.textContent = copyText('details');
      head.append(icon, title, chip, toggle);
      const body = document.createElement('div');
      body.className = 'sp-learning-body';
      body.hidden = !isOpen;
      body.append(copy, meta);
      head.addEventListener('click', () => {
        const open = body.hidden;
        body.hidden = !open;
        setAria(head, 'aria-expanded', open ? 'true' : 'false');
        if (open) openNotices.add(row.id); else openNotices.delete(row.id);
      });
      card.append(head, body);
      insertByTime(host, card, row.created_at);
    }
    if (failed && !unavailable && failures >= 2) {
      const card = document.createElement('div');
      card.dataset.skillLearningNotice = 'unavailable';
      card.className = 'skill-learning-notice skill-learning-notice-soft';
      card.append(document.createTextNode('🧩 ' + tr('skill_learning_unavailable_soft', 'Skill updates could not be checked just now.')));
      const retry = document.createElement('button');
      retry.type = 'button'; retry.className = 'btn-link skill-learning-retry';
      retry.textContent = '🔄 ' + tr('retry', 'Retry');
      retry.addEventListener('click', () => refresh(true));
      card.append(retry); host.append(card);
    }
  }
  function lang() {
    const ft = window.SynPulseFriendlyTools;
    return ft && typeof ft.lang === 'function' ? ft.lang() : 'en';
  }
  const COPY = {
    nl: {private: 'Alleen voor jou', details: 'Details', skill_one: 'Skill bijgewerkt: {name}', skill_new: 'Nieuwe skill: {name}',
      skills: '{n} skills bijgewerkt', memory: 'Geheugen bijgewerkt', and_memory: ' en geheugen bijgewerkt'},
    en: {private: 'Only you', details: 'Details', skill_one: 'Skill updated: {name}', skill_new: 'New skill: {name}',
      skills: '{n} skills updated', memory: 'Memory updated', and_memory: ' and memory updated'},
  };
  function copyText(key, vars) {
    let out = (COPY[lang()] || COPY.en)[key] || COPY.en[key] || key;
    for (const k of Object.keys(vars || {})) out = out.replace('{' + k + '}', String(vars[k]));
    return out;
  }
  function plainTitle(row, skillTotal) {
    const skills = row.skills || [];
    const memory = (row.memory || []).length > 0;
    let text = '';
    if (skillTotal === 1 && skills.length === 1) {
      text = copyText(skills[0].kind === 'created' ? 'skill_new' : 'skill_one', {name: skills[0].name});
    } else if (skillTotal) {
      text = copyText('skills', {n: skillTotal});
    }
    if (!text) return copyText('memory');
    return memory ? text + copyText('and_memory') : text;
  }
  const MEMORY_KEYS = ['memory', 'user', 'soul', 'profile_memory', 'profile_user', 'profile_soul'];
  function valid(row) {
    const memory = row && row.memory === undefined ? [] : row && row.memory;
    if (!(row && /^[a-f0-9]{64}$/.test(row.id) && Number.isSafeInteger(row.created_at)
      && row.created_at >= 0 && row.created_at < 8640000000000
      && row.counts && ['created', 'patched', 'updated'].every(key =>
        Number.isSafeInteger(row.counts[key]) && row.counts[key] >= 0 && row.counts[key] <= 10000)
      && Array.isArray(memory) && memory.length <= MEMORY_KEYS.length
      && memory.every(key => MEMORY_KEYS.includes(key)) && new Set(memory).size === memory.length
      && (row.source === undefined || row.source === 'review' || row.source === 'turn')
      && (Object.values(row.counts).some(value => value > 0) || memory.length > 0))) return false;
    const skills = row.skills === undefined ? [] : row.skills;
    if (!Array.isArray(skills) || skills.length > 50) return false;
    const totals = {created: 0, patched: 0, updated: 0}, seen = new Set();
    for (const skill of skills) {
      if (!skill || typeof skill.name !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(skill.name) ||
          !Object.hasOwn(totals, skill.kind) || !Number.isSafeInteger(skill.count) ||
          skill.count < 1 || skill.count > 10000) return false;
      const key = skill.kind + ':' + skill.name;
      if (seen.has(key)) return false;
      seen.add(key); totals[skill.kind] += skill.count;
    }
    return Object.keys(totals).every(key => totals[key] <= row.counts[key]);
  }
  function schedule() {
    clearTimeout(timer); timer = null;
    if (current()) timer = setTimeout(() => { timer = null; sync(); }, interval);
  }
  async function refresh(force = false) {
    const sid = current();
    if (!sid || sid !== session || pending || (!force && Date.now() - lastFetch < interval)) return;
    if (unavailable && !force) return;
    const stamp = generation;
    pending = true; lastFetch = Date.now(); controller = new AbortController();
    try {
      const data = await api('/api/session/skill-updates?session_id=' + encodeURIComponent(sid), {
        signal: controller.signal, cache: 'no-store', timeoutMs: 12000,
        timeoutToast: false, retries: 0, redirect401: false,
      });
      if (stamp !== generation || current() !== sid) return;
      if (data === undefined) { // 401 with redirect401:false: not signed in
        unavailable = true; failed = false; rows = []; return;
      }
      if (!data || !Array.isArray(data.events) || data.events.length > 100 || !data.events.every(valid)) {
        const err = new Error('Invalid activity'); err.invalid = true; throw err;
      }
      rows = data.events; failed = false; failures = 0; unavailable = false;
    } catch (err) {
      if (stamp !== generation || current() !== sid) return;
      const status = Number(err && err.status) || 0;
      if (status >= 400 && status < 500 && status !== 408 && status !== 429) {
        // 401 no email identity (auth off or local login without identity),
        // 403/404 conversation not visible to this person, 400 bad request:
        // not a failure the person can fix, so show nothing.
        unavailable = true; failed = false; rows = [];
      } else {
        // One slow reply under load is normal; an unreadable payload is not.
        failures += err && err.invalid ? 2 : 1; failed = true; // keep loaded notices
      }
    } finally {
      if (stamp === generation) {
        pending = false; controller = null; draw(); schedule();
      }
    }
  }
  function sync(rendered = false) {
    if (rendered === true) renderedSession = String(S.session?.session_id || '');
    const sid = current();
    if (sid !== session) {
      generation++; controller?.abort(); controller = null; pending = false;
      session = sid; rows = []; failed = false; lastFetch = 0; unavailable = false; failures = 0; clear();
    }
    // renderMessages can rebuild the DOM synchronously after this hook.
    queueMicrotask(draw);
    if (sid) void refresh();
    schedule();
  }
  function invalidate() { renderedSession = ''; sync(); }
  // A state_saved frame means the server just recorded a notice for this
  // turn: fetch now instead of waiting for the next 10 s poll.
  function poke(delay = 1500) { setTimeout(() => { lastFetch = 0; void refresh(true); }, delay); }
  window.SynthPulseSkillActivity = {sync, invalidate, poke};
  document.addEventListener('visibilitychange', sync);
  window.addEventListener('pagehide', () => {
    generation++; controller?.abort(); clearTimeout(timer); session = ''; rows = []; clear();
  });
  window.addEventListener('pageshow', sync);
})();
