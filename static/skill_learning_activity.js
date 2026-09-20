// Personal background-learning notices: separate from shared/model messages.
(function () {
  'use strict';
  let session = '', rows = [], failed = false, timer = null, controller = null;
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
      const labels = [
        ['created', tr('skill_learning_created', 'Skill automatically created')],
        ['patched', tr('skill_learning_patched', 'Skill automatically patched')],
        ['updated', tr('skill_learning_updated', 'Skill automatically updated')],
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
      card.append(copy, meta);
      insertByTime(host, card, row.created_at);
    }
    if (failed) {
      const card = document.createElement('div');
      card.dataset.skillLearningNotice = 'unavailable';
      card.className = 'skill-learning-notice';
      card.append(document.createTextNode(tr('skill_learning_unavailable', 'Skill update notices are unavailable.')));
      const retry = document.createElement('button');
      retry.type = 'button'; retry.className = 'btn secondary';
      retry.textContent = tr('retry', 'Retry');
      retry.addEventListener('click', () => refresh(true));
      card.append(retry); host.append(card);
    }
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
    const stamp = generation;
    pending = true; lastFetch = Date.now(); controller = new AbortController();
    try {
      const data = await api('/api/session/skill-updates?session_id=' + encodeURIComponent(sid), {
        signal: controller.signal, cache: 'no-store', timeoutMs: 5000,
        timeoutToast: false, retries: 0, redirect401: false,
      });
      if (stamp !== generation || current() !== sid) return;
      if (!data || !Array.isArray(data.events) || data.events.length > 100 || !data.events.every(valid)) throw new Error('Invalid activity');
      rows = data.events; failed = false;
    } catch (_) {
      if (stamp !== generation || current() !== sid) return;
      rows = []; failed = true;
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
      session = sid; rows = []; failed = false; lastFetch = 0; clear();
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
