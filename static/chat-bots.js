/* Chat recipients use the existing actor-scoped catalog and group dispatch. */
(function () {
  'use strict';
  let key = '', generation = 0, profiles = [], people = [], loading = true, peopleLoading = true, catalogRetry = false;
  let menuRows = [], menuIndex = 0, menuRange = null, preparing = false, retry = null;
  function tx(key, fallback) { const value = typeof t === 'function' ? t(key) : key; return value && value !== key ? value : fallback; }
  function actor() { return String((window.__GOV_ME__ || {}).email || '').toLowerCase(); }
  function contextKey() {
    const s = S.session || {};
    return JSON.stringify([actor(), s.session_id || '', S.activeProfile || '', s.bot_participants || [], s.participants || []]);
  }
  function preferenceKey() { return actor() ? 'synpulse:bot-roster-collapsed:' + actor() : null; }
  function collapsed() {
    try { return preferenceKey() && localStorage.getItem(preferenceKey()) === '1'; } catch (_) { return false; }
  }
  function available(rows, session) {
    const bots = session && Array.isArray(session.bot_participants) ? session.bot_participants : [];
    return (rows || []).filter(p => p && typeof p.name === 'string' && p.visible !== false &&
      (!bots.length || bots.includes(p.name)));
  }
  function address(draft, name) {
    return '@' + name + ' ' + String(draft || '').replace(/^\s*@[A-Za-z0-9][A-Za-z0-9_-]{0,63}(?=\s|$)\s*/, '');
  }
  function fold(value) { return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
  function catalog() {
    return profiles.filter(p => p && p.visible !== false).map(p => ({kind:'bot', id:p.name, label:botDisplayName(p)}))
      .concat(people.filter(p => p && p.email && p.email.toLowerCase() !== actor())
        .map(p => ({kind:'user', id:p.email, label:p.display_name || p.name || p.email})));
  }
  function mentionMatches(text, rows) {
    const result = [];
    // Whole tokens only: an email address in prose is not an invitation.
    for (const match of String(text || '').matchAll(/(?:^|\s)@([^\s,;!?()[\]{}<>]+)/g)) {
      const token = match[1].replace(/[.:]$/, '');
      const item = rows.find(row => row.id.toLowerCase() === token.toLowerCase());
      if (item) { const start = match.index + match[0].indexOf('@'); result.push({item, start, end:start + token.length + 1}); }
    }
    return result;
  }
  function mentions(text, rows) {
    const result = [];
    for (const match of mentionMatches(text, rows)) {
      if (!result.some(row => row.kind === match.item.kind && row.id === match.item.id)) result.push(match.item);
    }
    return result;
  }
  function normalizeBotAddress(text, rows) {
    const match = mentionMatches(text, rows).find(row => row.item.kind === 'bot');
    if (!match) return text;
    if (match.start === 0) {
      const remainder = text.slice(match.end);
      return '@' + match.item.id + (remainder && !/^\s/.test(remainder) ? ' ' : '') + remainder;
    }
    return '@' + match.item.id + ' ' + text.slice(0, match.start) + text.slice(match.end);
  }
  function closeMenu() {
    menuRange = null; menuRows = [];
    const popup = document.getElementById('chatMentionDropdown');
    if (popup) popup.hidden = true;
    const input = document.getElementById('msg');
    if (input && input.getAttribute('aria-controls') === 'chatMentionDropdown') {
      input.removeAttribute('aria-controls'); input.removeAttribute('aria-activedescendant'); input.removeAttribute('aria-expanded');
    }
  }
  function choose(item) {
    const input = document.getElementById('msg');
    if (!input || !menuRange || contextKey() !== key) return closeMenu();
    const {start, end} = menuRange;
    input.setRangeText('@' + item.id + ' ', start, end, 'end');
    closeMenu(); input.dispatchEvent(new Event('input', {bubbles:true})); input.focus();
  }
  function paintMenu() {
    const input = document.getElementById('msg'), host = document.getElementById('composerWrap');
    if (!input || !host || document.activeElement !== input || preparing || loading) return closeMenu();
    const before = input.value.slice(0, input.selectionStart);
    const match = /(?:^|\s)@([^\s@]*)$/.exec(before);
    if (!match) return closeMenu();
    const query = fold(match[1]);
    menuRows = catalog().filter(row => fold(row.label + ' ' + row.id).includes(query)).slice(0, 12);
    menuRange = {start:before.length - match[1].length - 1, end:input.selectionStart};
    menuIndex = Math.min(menuIndex, Math.max(0, menuRows.length - 1));
    let popup = document.getElementById('chatMentionDropdown');
    if (!popup) { popup = document.createElement('div'); popup.id = 'chatMentionDropdown'; popup.className = 'chat-mention-dropdown'; popup.setAttribute('role','listbox'); popup.setAttribute('aria-label',tx('chat_mentions_picker', 'Mention a person or bot')); host.appendChild(popup); }
    popup.hidden = false; popup.replaceChildren();
    input.setAttribute('aria-controls', popup.id); input.setAttribute('aria-expanded','true');
    menuRows.forEach((row, index) => {
      const button = document.createElement('button'); button.type = 'button'; button.id = 'chatMentionOption-' + index;
      button.dataset.mentionKind = row.kind; button.dataset.mentionId = row.id;
      button.setAttribute('role','option'); button.setAttribute('aria-selected',String(index === menuIndex)); button.tabIndex = -1;
      const label = document.createElement('span'); label.textContent = row.label;
      const detail = document.createElement('small'); detail.textContent = (row.kind === 'bot' ? tx('chat_mentions_bot', 'Bot') : tx('chat_mentions_person', 'Person')) + ' · @' + row.id;
      button.append(label, detail); button.onpointerdown = event => event.preventDefault(); button.onclick = () => choose(row); popup.appendChild(button);
    });
    if (menuRows.length) input.setAttribute('aria-activedescendant','chatMentionOption-' + menuIndex);
    else { input.removeAttribute('aria-activedescendant'); const empty = document.createElement('span'); empty.textContent = tx('chat_mentions_empty', 'No matching people or bots'); popup.appendChild(empty); }
  }
  function paint() {
    const host = document.getElementById('composerWrap');
    if (!host) return;
    let bar = document.getElementById('chatBotRoster');
    if (!bar) { bar = document.createElement('div'); bar.id = 'chatBotRoster'; bar.className = 'chat-bot-roster'; host.prepend(bar); }
    bar.replaceChildren();
    const toggle = document.createElement('button'); toggle.type = 'button'; toggle.id = 'chatBotRosterToggle'; toggle.className = 'chat-bot-recipient chat-bot-toggle';
    toggle.textContent = collapsed() ? tx('chat_roster_show', 'Show bots') : tx('chat_roster_hide', 'Hide bots'); toggle.setAttribute('aria-expanded',String(!collapsed())); toggle.setAttribute('aria-controls','chatBotRosterItems');
    toggle.onclick = () => { try { if (preferenceKey()) localStorage.setItem(preferenceKey(), collapsed() ? '0' : '1'); } catch (_) {} paint(); document.getElementById('chatBotRosterToggle').focus(); };
    bar.appendChild(toggle);
    const items = document.createElement('div'); items.id = 'chatBotRosterItems'; items.className = 'chat-bot-roster-items'; items.hidden = !!collapsed(); bar.appendChild(items);
    const session = S.session || {}, group = (session.bot_participants || []).length > 0;
    const rows = available(profiles, session);
    for (const p of rows) {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'chat-bot-recipient'; button.dataset.bot = p.name;
      const input = document.getElementById('msg');
      const mention = /^\s*@([A-Za-z0-9][A-Za-z0-9_-]{0,63})(?=\s|$)/.exec(input ? input.value : '');
      button.setAttribute('aria-pressed',String(group ? (mention ? mention[1] === p.name : rows.length === 1) : S.activeProfile === p.name));
      button.title = '@' + p.name; button.disabled = loading || !S._bootReady || preparing || (!group && !!S.busy);
      button.innerHTML = botAvatarHtml(p); const name = document.createElement('span'); name.textContent = botDisplayName(p); button.appendChild(name);
      button.onclick = async () => {
        if (!S._bootReady || preparing) return;
        if (contextKey() !== key) { window.refreshChatBots(); return; }
        if (group) { if (!input) return; input.value = address(input.value, p.name); input.dispatchEvent(new Event('input', {bubbles:true})); input.focus(); paint(); }
        else if (p.name !== S.activeProfile) { button.disabled = true; try { await switchToProfile(p.name); } catch (err) { showToast(err.message); } finally { window.refreshChatBots(); } }
      };
      items.appendChild(button);
    }
    if (!rows.length) { const state = document.createElement('span'); state.className = 'chat-bot-roster-state'; state.setAttribute('role','status'); state.textContent = loading ? tx('chat_bots_loading', 'Loading bots…') : tx('chat_bots_unavailable', 'No available bots'); items.appendChild(state); }
    let hint = document.getElementById('chatMentionHint');
    if (!hint) { hint = document.createElement('div'); hint.id = 'chatMentionHint'; hint.className = 'chat-mention-hint'; host.appendChild(hint); }
    const draft = (document.getElementById('msg') || {}).value || '';
    hint.hidden = !preparing && !!collapsed() && !/(?:^|\s)@/.test(draft);
    hint.textContent = preparing ? tx('chat_mentions_preparing', 'Preparing recipients…') : tx('chat_mentions_hint', '@ people: new group from private chat. First @ bot responds.');
  }
  window.refreshChatBots = function () {
    const next = contextKey(); if (next === key && !catalogRetry) return;
    const changed = next !== key;
    key = next; catalogRetry = false;
    if (changed) { profiles = []; people = []; }
    loading = true; peopleLoading = true; closeMenu(); const current = ++generation; paint();
    const fresh = () => generation === current && contextKey() === next;
    Promise.resolve(api('/api/profiles?fast=1', {timeoutToast:false})).then(result => {
      if (!fresh()) return;
      if (!Array.isArray(result.profiles)) throw new Error('Invalid bot catalog');
      profiles = result.profiles;
    }).catch(() => { if (fresh()) catalogRetry = true; }).finally(() => {
      if (!fresh()) return;
      loading = false; paint(); paintMenu();
    });
    Promise.resolve(api('/api/people', {timeoutToast:false})).then(result => {
      if (!fresh()) return;
      if (!Array.isArray(result.people)) throw new Error('Invalid people catalog');
      people = result.people;
    }).catch(() => { if (fresh()) catalogRetry = true; }).finally(() => {
      if (!fresh()) return;
      peopleLoading = false; paintMenu();
    });
  };
  window.chatMentionsBlockBusySend = function () {
    const input = document.getElementById('msg');
    if (preparing || ((S.busy || (typeof _sendInProgress !== 'undefined' && _sendInProgress)) && /(?:^|\s)@/.test(input ? input.value : ''))) {
      showToast(tx('chat_mentions_busy', 'Wait for this turn to finish before sending mentions. Your draft is kept.')); return true;
    }
    return false;
  };
  window.prepareChatMentions = async function () {
    const input = document.getElementById('msg'); if (!input || !/(?:^|\s)@/.test(input.value)) return true;
    const origin = contextKey(), original = input.value;
    if (loading || peopleLoading) { showToast(tx('chat_mentions_loading', 'People and bots are still loading. Please try again.')); return false; }
    const selected = mentions(original, catalog()); if (!selected.length) return true;
    const users = selected.filter(row => row.kind === 'user').map(row => row.id), bots = selected.filter(row => row.kind === 'bot').map(row => row.id);
    if (users.length && ((S.pendingFiles || []).length || (typeof _pendingSelections !== 'undefined' && _pendingSelections.length))) {
      showToast(tx('chat_mentions_attachments', 'Remove private attachments or selections first. You can attach files explicitly in the group.')); return false;
    }
    const body = {session_id:(S.session || {}).session_id || null, participants:users, bot_participants:bots};
    if (!body.session_id) {
      const model = typeof _chatPayloadModelState === 'function' ? _chatPayloadModelState() : {};
      body.model = model.model || null; body.model_provider = model.model_provider || null;
      body.chat_mode = S._pendingChatMode || 'super';
    }
    const signature = JSON.stringify([actor(), body, original]);
    if (!retry || retry.signature !== signature) retry = {signature, id:crypto.randomUUID()};
    const oldReadOnly = input.readOnly, pendingFiles = [...(S.pendingFiles || [])];
    preparing = true; input.readOnly = true; closeMenu(); paint();
    try {
      const result = await api('/api/chat/mentions/prepare', {method:'POST', body:JSON.stringify({...body, request_id:retry.id})});
      if (contextKey() !== origin || input.value !== original) throw new Error(tx('chat_mentions_changed', 'The chat or draft changed. Nothing was sent.'));
      const target = result.session && result.session.session_id;
      if (!target) throw new Error(tx('chat_mentions_failed', 'Recipients could not be prepared. Your draft is kept.'));
      if (target !== (S.session || {}).session_id) {
        await loadSession(target);
        if ((S.session || {}).session_id !== target) throw new Error(tx('chat_mentions_navigation', 'The chat changed. Nothing was sent.'));
      } else { S.session = {...S.session, ...result.session}; }
      // Bot dispatch remains one explicitly addressed bot, never automatic fanout.
      const draft = normalizeBotAddress(original, selected);
      if (!users.length) S.pendingFiles = pendingFiles;
      input.value = draft; input.dispatchEvent(new Event('input', {bubbles:true}));
      retry = null; key = ''; window.refreshChatBots(); return true;
    } catch (error) { showToast(error.message || tx('chat_mentions_error', 'Could not prepare recipients. Your draft is kept.')); return false; }
    finally { preparing = false; input.readOnly = oldReadOnly; paint(); }
  };
  document.addEventListener('input', event => { if (event.target && event.target.id === 'msg') { menuIndex = 0; paint(); paintMenu(); } });
  document.addEventListener('focusin', event => { if (event.target && event.target.id === 'msg') paintMenu(); });
  document.addEventListener('keydown', event => {
    if (!event.target || event.target.id !== 'msg' || !menuRange || event.isComposing || event.keyCode === 229) return;
    if (!['ArrowUp','ArrowDown','Enter','Tab','Escape'].includes(event.key)) return;
    event.preventDefault(); event.stopImmediatePropagation();
    if (event.key === 'Escape') return closeMenu();
    if (!menuRows.length) return;
    if (event.key === 'ArrowUp' || event.key === 'ArrowDown') { menuIndex = (menuIndex + (event.key === 'ArrowUp' ? -1 : 1) + menuRows.length) % menuRows.length; paintMenu(); document.getElementById('chatMentionOption-' + menuIndex).scrollIntoView({block:'nearest'}); }
    else choose(menuRows[menuIndex]);
  }, true);
  document.addEventListener('pointerdown', event => { const popup = document.getElementById('chatMentionDropdown'); if (popup && !popup.contains(event.target) && event.target.id !== 'msg') closeMenu(); });
  window.addEventListener('synpulse:bot-updated', () => { key = ''; window.refreshChatBots(); });
  window.addEventListener('synpulse:boot-ready', () => { if (contextKey() !== key) window.refreshChatBots(); else paint(); });
  paint();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => window.refreshChatBots(), {once:true});
  else window.refreshChatBots();
  window.chatBotRecipientRules = {available, address, mentions, fold, normalizeBotAddress};
})();
