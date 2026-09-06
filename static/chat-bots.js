/* Chat recipients use the existing profile ACL and group @bot dispatch contract. */
(function () {
  'use strict';
  let key = '', generation = 0, profiles = [], loading = false;
  function contextKey() {
    const s = S.session || {};
    return JSON.stringify([s.session_id || '', S.activeProfile || '', s.bot_participants || []]);
  }
  function available(rows, session) {
    const bots = session && Array.isArray(session.bot_participants) ? session.bot_participants : [];
    return (rows || []).filter(p => p && typeof p.name === 'string' && p.visible !== false &&
      (!bots.length || bots.includes(p.name)));
  }
  function address(draft, name) {
    // Change only a leading recipient; preserve every other byte of the draft.
    return '@' + name + ' ' + String(draft || '').replace(/^\s*@[A-Za-z0-9][A-Za-z0-9_-]{0,63}(?=\s|$)\s*/, '');
  }
  function paint() {
    const host = document.getElementById('composerWrap');
    if (!host) return;
    let bar = document.getElementById('chatBotRoster');
    if (!bar) {
      bar = document.createElement('div'); bar.id = 'chatBotRoster';
      bar.className = 'chat-bot-roster'; host.prepend(bar);
    }
    bar.replaceChildren();
    const session = S.session || {}, group = (session.bot_participants || []).length > 0;
    const label = document.createElement('span'); label.className = 'chat-bot-roster-label';
    label.textContent = t(group ? 'chat_bots_address' : 'chat_bots_choose');
    bar.appendChild(label);
    const rows = available(profiles, session);
    for (const p of rows) {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'chat-bot-recipient';
      button.dataset.bot = p.name;
      const input = document.getElementById('msg');
      const mention = /^\s*@([A-Za-z0-9][A-Za-z0-9_-]{0,63})(?=\s|$)/.exec(input ? input.value : '');
      const selected = group ? (mention ? mention[1] === p.name : rows.length === 1) : S.activeProfile === p.name;
      button.setAttribute('aria-pressed', String(selected));
      button.title = '@' + p.name;
      button.disabled = loading || (!group && !!S.busy);
      button.innerHTML = botAvatarHtml(p);
      const name = document.createElement('span'); name.textContent = botDisplayName(p);
      button.appendChild(name);
      button.onclick = async () => {
        // The roster can outlive an asynchronous navigation; never address its old chat.
        if (contextKey() !== key) { window.refreshChatBots(); return; }
        if (group) {
          if (!input) return;
          input.value = address(input.value, p.name);
          input.dispatchEvent(new Event('input', {bubbles: true}));
          input.focus(); paint();
        } else if (p.name !== S.activeProfile) {
          button.disabled = true;
          try { await switchToProfile(p.name); }
          catch (err) { showToast(err.message); }
          finally { window.refreshChatBots(); }
        }
      };
      bar.appendChild(button);
    }
    if (!rows.length) {
      const state = document.createElement('span'); state.className = 'chat-bot-roster-state';
      state.textContent = t(loading ? 'chat_bots_loading' : 'chat_bots_unavailable');
      bar.appendChild(state);
    }
  }
  window.refreshChatBots = function () {
    const next = contextKey();
    if (next === key) return;
    key = next; profiles = []; loading = true; const current = ++generation; paint();
    api('/api/profiles?fast=1', {timeoutToast:false}).then(data => {
      if (generation !== current || contextKey() !== next) return;
      profiles = Array.isArray(data.profiles) ? data.profiles : [];
    }).catch(() => {
      // No cached roster from a different context, and no privileged fallback.
      if (generation === current) profiles = [];
    }).finally(() => {
      if (generation !== current || contextKey() !== next) return;
      loading = false; paint();
    });
  };
  document.addEventListener('input', event => {
    if (event.target && event.target.id === 'msg') paint();
  });
  // Export the pure recipient rules for behavior tests without a browser framework.
  window.chatBotRecipientRules = {available, address};
})();
