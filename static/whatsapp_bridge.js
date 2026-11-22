/* WhatsApp in the Super Agent (Connections, tab Messaging channels).

   The WhatsApp bridge is a module of the installation with its own guard. The
   guard serves an API next to the WebUI, at /_synthpulse/whatsapp, and checks
   every call against the caller's WebUI session. This file only draws:

   * "WhatsApp koppelen" for everybody: the business number, asking for a code,
     the code shown large with the instruction to send it from your own
     WhatsApp, the time left, and your linked number (masked) with unlink;
   * "WhatsApp van de afdeling" for administrators: status, linked people with
     revoke, the two settings, the pairing window and recent refused messages.

   Linking a number is proven by the phone that sends the code. Nothing here
   can link a number to a person, and no key or number is typed here.

   When the module is not installed the API does not answer; both blocks then
   stay hidden. */
(function(){
  'use strict';
  const BASE = '/_synthpulse/whatsapp';
  const NL = {
    me_title: 'WhatsApp koppelen', me_intro: 'App met je AI-assistent via het zakelijke nummer van je afdeling. Je werkt daar met je eigen rechten.',
    active: 'Actief', inactive: 'Nog niet actief', inactive_note: 'Het zakelijke nummer is nog niet gekoppeld of staat uit. Je beheerder zet dit aan.',
    business: 'Zakelijk nummer', department: 'Afdeling', your_number: 'Jouw gekoppelde nummer', since: 'gekoppeld op', none: 'Je hebt nog geen nummer gekoppeld.',
    request: 'Code aanvragen', request_new: 'Nieuwe code aanvragen', unlink: 'Ontkoppelen', unlink_confirm: 'Je nummer ontkoppelen? Berichten vanaf dat nummer krijgen daarna geen toegang meer.',
    unlinked: 'Je nummer is ontkoppeld.', code_title: 'Jouw code', code_default: 'Stuur deze code vanaf je eigen WhatsApp naar het zakelijke nummer.',
    send_to: 'Stuur naar', valid: 'Nog {t} geldig', expired: 'De code is verlopen. Vraag een nieuwe aan.', open_wa: 'Open WhatsApp',
    pending: 'Er staat nog een code open tot {t}. Ben je hem kwijt, vraag dan een nieuwe aan.', linked_now: 'Je nummer is gekoppeld.',
    failed: 'Dit is nu niet gelukt. Probeer het later opnieuw.',
    admin_title: 'WhatsApp van de afdeling', admin_intro: 'Het zakelijke nummer, wie gekoppeld is en wat er is geweigerd. Een nummer koppelen kan alleen de persoon zelf, met een code vanaf de eigen telefoon.',
    connection: 'Verbinding', enabled: 'Ingeschakeld', key: 'Sleutel', policy: 'Beleid', last_message: 'Laatste bericht', last_refused: 'Laatste weigering', webhook: 'Webhook geregistreerd',
    yes: 'ja', no: 'nee', key_set: 'ingesteld', key_missing: 'ontbreekt', never: 'nog niet', linked_people: 'Gekoppelde mensen',
    c_ready: 'Verbonden', c_authenticated: 'Aangemeld', c_qr: 'Wacht op scannen', c_booting: 'Start op', c_disconnected: 'Niet verbonden', c_unconfigured: 'Niet ingericht', c_error: 'Fout',
    g_enforce: 'handhaven', g_report_only: 'alleen melden', g_off: 'uit', g_unknown: 'onbekend',
    policy_warn: 'Zonder actief beleid weigert de koppeling elk bericht.', dry_run: 'Proefstand: er wordt niets teruggestuurd.',
    settings: 'Instellingen', unknown_reply: 'Antwoord aan onbekende nummers', unknown_hint: 'Leeg laten betekent: onbekende nummers krijgen geen antwoord.', save: 'Opslaan', saved: 'Opgeslagen',
    pairing: 'Zakelijk nummer koppelen', pairing_hint: 'Open een venster van vijftien minuten en scan de code met WhatsApp op de telefoon van het zakelijke nummer, onder Gekoppelde apparaten.',
    pairing_open: 'Koppelvenster openen', pairing_page: 'Open de koppelpagina', pairing_until: 'Open tot {t}',
    people: 'Gekoppelde mensen', person: 'Persoon', number: 'Nummer', verified: 'Gekoppeld op', revoke: 'Intrekken', revoke_confirm: 'De koppeling van {n} intrekken?', revoked: 'De koppeling is ingetrokken.', no_people: 'Nog niemand heeft een nummer gekoppeld.',
    refused: 'Recent geweigerd', no_refused: 'Er is niets geweigerd.', when: 'Wanneer', what: 'Wat',
    e_refused_unknown: 'Onbekend nummer', e_refused_group: 'Groep of kanaal', e_refused_replay: 'Herhaald of te oud bericht', e_refused_instance: 'Ander WhatsApp-account', e_refused_no_policy: 'Geen actief beleid',
    e_refused_media: 'Bijlage of spraakbericht', e_refused_suppressed: 'Onbekend nummer, zonder antwoord', e_refused: 'Geweigerd'
  };
  const EN = {
    me_title: 'Link WhatsApp', me_intro: 'Message your AI assistant through the business number of your department. You work there with your own rights.',
    active: 'Active', inactive: 'Not active yet', inactive_note: 'The business number is not linked yet or is switched off. Your administrator switches this on.',
    business: 'Business number', department: 'Department', your_number: 'Your linked number', since: 'linked on', none: 'You have not linked a number yet.',
    request: 'Request a code', request_new: 'Request a new code', unlink: 'Unlink', unlink_confirm: 'Unlink your number? Messages from that number get no access afterwards.',
    unlinked: 'Your number is unlinked.', code_title: 'Your code', code_default: 'Send this code from your own WhatsApp to the business number.',
    send_to: 'Send to', valid: 'Valid for another {t}', expired: 'The code has expired. Request a new one.', open_wa: 'Open WhatsApp',
    pending: 'A code is still open until {t}. If you lost it, request a new one.', linked_now: 'Your number is linked.',
    failed: 'This did not work right now. Try again later.',
    admin_title: 'WhatsApp of the department', admin_intro: 'The business number, who is linked and what was refused. Only the person can link a number, with a code from their own phone.',
    connection: 'Connection', enabled: 'Switched on', key: 'Key', policy: 'Policy', last_message: 'Last message', last_refused: 'Last refusal', webhook: 'Webhook registered',
    yes: 'yes', no: 'no', key_set: 'set', key_missing: 'missing', never: 'not yet', linked_people: 'Linked people',
    c_ready: 'Connected', c_authenticated: 'Signed in', c_qr: 'Waiting for the scan', c_booting: 'Starting', c_disconnected: 'Not connected', c_unconfigured: 'Not set up', c_error: 'Error',
    g_enforce: 'enforce', g_report_only: 'report only', g_off: 'off', g_unknown: 'unknown',
    policy_warn: 'Without an active policy the bridge refuses every message.', dry_run: 'Trial mode: nothing is sent back.',
    settings: 'Settings', unknown_reply: 'Reply to unknown numbers', unknown_hint: 'Leaving this empty means: unknown numbers get no reply.', save: 'Save', saved: 'Saved',
    pairing: 'Link the business number', pairing_hint: 'Open a window of fifteen minutes and scan the code with WhatsApp on the phone of the business number, under Linked devices.',
    pairing_open: 'Open the pairing window', pairing_page: 'Open the pairing page', pairing_until: 'Open until {t}',
    people: 'Linked people', person: 'Person', number: 'Number', verified: 'Linked on', revoke: 'Revoke', revoke_confirm: 'Revoke the link of {n}?', revoked: 'The link is revoked.', no_people: 'Nobody has linked a number yet.',
    refused: 'Recently refused', no_refused: 'Nothing was refused.', when: 'When', what: 'What',
    e_refused_unknown: 'Unknown number', e_refused_group: 'Group or channel', e_refused_replay: 'Repeated or too old message', e_refused_instance: 'Another WhatsApp account', e_refused_no_policy: 'No active policy',
    e_refused_media: 'Attachment or voice message', e_refused_suppressed: 'Unknown number, without a reply', e_refused: 'Refused'
  };
  const lang = () => ((document.documentElement.lang || 'nl').toLowerCase().startsWith('en') ? 'en' : 'nl');
  const w = (k, v) => { let s = (lang() === 'en' ? EN : NL)[k] || NL[k] || k; if (v) for (const [a, b] of Object.entries(v)) s = s.replace('{' + a + '}', b); return s; };
  const H = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const toast = m => { if (typeof showToast === 'function') showToast(m); };
  const loc = () => (lang() === 'en' ? 'en-GB' : 'nl-NL');
  // A moment as the guard sends it: epoch seconds or an ISO text.
  const moment = v => { if (v == null || v === '') return null; const d = typeof v === 'number' ? new Date(v * 1000) : new Date(v); return isNaN(d) ? null : d; };
  const day = v => { const d = moment(v); return d ? d.toLocaleDateString(loc(), { day: 'numeric', month: 'short', year: 'numeric' }) : ''; };
  const clock = v => { const d = moment(v); return d ? d.toLocaleTimeString(loc(), { hour: '2-digit', minute: '2-digit' }) : ''; };
  const stamp = v => { const d = moment(v); return d ? d.toLocaleString(loc(), { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''; };

  const S = { me: null, status: null, audit: null, code: null, timer: null, poll: null, busy: false, note: '', pairing: null, token: 0 };

  async function call(path, body){
    const options = { credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (body !== undefined) Object.assign(options, { method: 'POST', body: JSON.stringify(body), headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-SynthPulse-WhatsApp': '1' } });
    const res = await fetch(BASE + path, options);
    let data = null;
    try { data = await res.json(); } catch (_e) { data = null; }
    if (!res.ok || !data || typeof data !== 'object') { const err = new Error((data && typeof data.detail === 'string' && data.detail) || w('failed')); err.status = res.status; throw err; }
    return data;
  }
  const hosts = () => ({ me: document.getElementById('intgWhatsApp'), admin: document.getElementById('intgWhatsAppAdmin') });
  function hide(){ const h = hosts(); for (const el of [h.me, h.admin]) if (el) { el.hidden = true; el.replaceChildren(); } stop(); }
  function stop(){ if (S.timer) clearInterval(S.timer); if (S.poll) clearInterval(S.poll); S.timer = S.poll = null; }

  // ── Personal block ─────────────────────────────────────────────────────────
  function left(){ const end = S.code && moment(S.code.expires_at); return end ? Math.max(0, Math.round((end - Date.now()) / 1000)) : 0; }
  function leftText(){ const s = left(); return w('valid', { t: Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0') }); }
  function codeHtml(){
    if (!S.code) return '';
    const digits = String(S.code.send_to || S.me.business_number || '').replace(/\D/g, '');
    const text = String(S.code.code || '');
    const over = left() <= 0;
    return `<div class="wa-code" data-wa-code role="status" aria-live="polite">
      <div class="wa-code-label">${H(w('code_title'))}</div>
      <div class="wa-code-value ${over ? 'expired' : ''}" data-wa-code-value>${H(text)}</div>
      <p class="wa-code-how">${H(S.code.instruction || w('code_default'))}</p>
      <p class="wa-code-to">${H(w('send_to'))} <strong>${H(S.code.send_to || S.me.business_number || '')}</strong></p>
      <p class="wa-code-left ${over ? 'expired' : ''}" data-wa-left>${H(over ? w('expired') : leftText())}</p>
      ${digits && !over ? `<a class="sm-btn wa-open" href="https://wa.me/${H(digits)}?text=${encodeURIComponent(text.replace(/\s+/g, ''))}" target="_blank" rel="noopener noreferrer">${H(w('open_wa'))}</a>` : ''}</div>`;
  }
  function paintMe(){
    const host = hosts().me, m = S.me;
    if (!host || !m) return;
    host.hidden = false;
    const links = Array.isArray(m.links) ? m.links : [];
    const pendingEnd = !S.code && m.pending && moment(m.pending.expires_at) > Date.now() ? clock(m.pending.expires_at) : '';
    host.innerHTML = `<div class="intg-section-title">${H(w('me_title'))} <span class="intg-badge ${m.active ? 'intg-badge-ok' : ''}" data-wa-state>${H(w(m.active ? 'active' : 'inactive'))}</span></div>
      <p class="intg-muted intg-channels-intro">${H(w('me_intro'))}</p>
      <div class="intg-card wa-card">
        <dl class="wa-facts"><div><dt>${H(w('business'))}</dt><dd data-wa-business>${H(m.business_number || '')}</dd></div>${m.department_name ? `<div><dt>${H(w('department'))}</dt><dd>${H(m.department_name)}</dd></div>` : ''}</dl>
        ${m.active ? '' : `<p class="intg-muted">${H(w('inactive_note'))}</p>`}
        <div class="wa-links"><div class="wa-sub">${H(w('your_number'))}</div>
          ${links.length ? links.map(l => `<div class="wa-link" data-wa-link="${H(l.link_id || '')}"><code>${H(l.number || '')}</code><span class="intg-muted">${H(w('since'))} ${H(day(l.verified_at))}</span><button type="button" class="sm-btn" data-wa-unlink ${S.busy ? 'disabled' : ''}>${H(w('unlink'))}</button></div>`).join('') : `<p class="intg-muted" data-wa-none>${H(w('none'))}</p>`}</div>
        ${S.note ? `<p class="wa-note" role="status">${H(S.note)}</p>` : ''}
        ${codeHtml()}
        ${pendingEnd ? `<p class="intg-muted" data-wa-pending>${H(w('pending', { t: pendingEnd }))}</p>` : ''}
        <div class="ch-inline"><button type="button" class="sm-btn primary" data-wa-request ${m.active && !S.busy ? '' : 'disabled'}>${H(w(S.code || pendingEnd ? 'request_new' : 'request'))}</button></div>
      </div>`;
  }
  function watchCode(){
    stop();
    // The seconds tick in place; the block is only redrawn when something changes.
    S.timer = setInterval(() => {
      const el = document.querySelector('#intgWhatsApp [data-wa-left]');
      if (!S.code || !el) return;
      if (left() <= 0) { stop(); paintMe(); return; }
      el.textContent = leftText();
    }, 1000);
    // The link appears when the guard received the code from the phone.
    S.poll = setInterval(async () => {
      if (!S.code) return;
      const before = (S.me.links || []).map(l => l.link_id + ':' + l.verified_at).join();
      try {
        const next = await call('/api/me');
        const after = (next.links || []).map(l => l.link_id + ':' + l.verified_at).join();
        if (after && after !== before) { S.me = next; S.code = null; S.note = w('linked_now'); stop(); paintMe(); if (S.me.is_admin) void loadAdmin(); }
      } catch (_e) { /* keep waiting; the next tick asks again */ }
    }, 5000);
  }
  async function act(fn){
    if (S.busy) return;
    S.busy = true; S.note = ''; paintMe();
    try { await fn(); } catch (e) { S.note = (e && e.message) || w('failed'); }
    S.busy = false; paintMe();
  }

  // ── Administrators ─────────────────────────────────────────────────────────
  function refusedRows(){
    const events = (S.audit && Array.isArray(S.audit.events) ? S.audit.events : []).filter(e => e && String(e.event || '').startsWith('refused'));
    return events.slice(-12).reverse();
  }
  function paintAdmin(){
    const host = hosts().admin, st = S.status;
    if (!host) return;
    if (!st || st.installed === false) { host.hidden = true; host.replaceChildren(); return; }
    host.hidden = false;
    const links = Array.isArray(st.links) ? st.links : [];
    const fact = (label, value, cls) => `<div><dt>${H(label)}</dt><dd class="${cls || ''}">${H(value)}</dd></div>`;
    const warn = st.governance === 'off' || st.governance === 'unknown';
    const pairingOpen = moment(st.pairing_open_until) > Date.now() ? st.pairing_open_until : (S.pairing && moment(S.pairing.expires_at) > Date.now() ? S.pairing.expires_at : null);
    const page = S.pairing && typeof S.pairing.page === 'string' && S.pairing.page.startsWith(BASE + '/') ? S.pairing.page : BASE + '/pairing';
    const refused = refusedRows();
    host.innerHTML = `<div class="intg-section-title">${H(w('admin_title'))} <span class="intg-badge ${st.connection === 'ready' && st.enabled ? 'intg-badge-ok' : ''}" data-wa-connection>${H(w('c_' + (st.connection || 'unconfigured')))}</span></div>
      <p class="intg-muted intg-channels-intro">${H(w('admin_intro'))}</p>
      <div class="intg-card wa-card">
        <dl class="wa-facts wa-facts-wide">
          ${fact(w('business'), st.business_number || '')}${fact(w('department'), st.department_name || st.department || '')}
          ${fact(w('enabled'), w(st.enabled ? 'yes' : 'no'))}${fact(w('key'), w(st.key_set ? 'key_set' : 'key_missing'), st.key_set ? '' : 'wa-warn')}
          ${fact(w('policy'), w('g_' + (st.governance || 'unknown')), warn ? 'wa-warn' : '')}${fact(w('linked_people'), String(st.linked_people ?? links.length))}
          ${fact(w('last_message'), stamp(st.last_message_at) || w('never'))}${fact(w('last_refused'), stamp(st.last_refused_at) || w('never'))}
          ${fact(w('webhook'), stamp(st.webhook_registered_at) || w('never'))}</dl>
        ${warn ? `<p class="wa-note wa-warn" data-wa-policy-warn>${H(w('policy_warn'))}</p>` : ''}${st.dry_run ? `<p class="wa-note">${H(w('dry_run'))}</p>` : ''}
      </div>
      <div class="intg-card wa-card"><div class="wa-sub">${H(w('settings'))}</div>
        <form class="wa-settings" data-wa-settings>
          <label class="wa-check"><input type="checkbox" name="enabled" ${st.enabled ? 'checked' : ''}> ${H(w('enabled'))}</label>
          <label class="wa-field">${H(w('unknown_reply'))}<textarea name="unknown_reply" rows="2" maxlength="500">${H(st.unknown_reply || '')}</textarea><span class="intg-muted">${H(w('unknown_hint'))}</span></label>
          <div class="ch-inline"><button type="submit" class="sm-btn primary" ${S.busy ? 'disabled' : ''}>${H(w('save'))}</button></div></form></div>
      <div class="intg-card wa-card"><div class="wa-sub">${H(w('pairing'))}</div><p class="intg-muted">${H(w('pairing_hint'))}</p>
        <div class="ch-inline"><button type="button" class="sm-btn" data-wa-pairing ${S.busy ? 'disabled' : ''}>${H(w('pairing_open'))}</button>
          ${pairingOpen ? `<a class="sm-btn primary" data-wa-pairing-page href="${H(page)}" target="_blank" rel="noopener noreferrer">${H(w('pairing_page'))}</a><span class="intg-muted">${H(w('pairing_until', { t: clock(pairingOpen) }))}</span>` : ''}</div></div>
      <div class="intg-card wa-card"><div class="wa-sub">${H(w('people'))}</div>
        ${links.length ? `<div class="intg-table-wrap"><table class="ch-people-table wa-table wa-people"><thead><tr><th>${H(w('person'))}</th><th>${H(w('number'))}</th><th>${H(w('verified'))}</th><th></th></tr></thead><tbody>
          ${links.map(l => `<tr data-wa-row="${H(l.link_id || '')}"><td><strong>${H(l.name || l.email || '')}</strong>${l.name && l.email ? `<div class="intg-muted">${H(l.email)}</div>` : ''}</td><td><code>${H(l.number || '')}</code></td><td>${H(day(l.verified_at))}</td>
            <td><button type="button" class="sm-btn" data-wa-revoke="${H(l.link_id || '')}" data-wa-name="${H(l.name || l.email || '')}" ${S.busy ? 'disabled' : ''}>${H(w('revoke'))}</button></td></tr>`).join('')}</tbody></table></div>` : `<p class="intg-muted">${H(w('no_people'))}</p>`}</div>
      <div class="intg-card wa-card"><div class="wa-sub">${H(w('refused'))}</div>
        ${refused.length ? `<div class="intg-table-wrap"><table class="ch-people-table wa-table" data-wa-refused><thead><tr><th>${H(w('when'))}</th><th>${H(w('what'))}</th><th>${H(w('number'))}</th></tr></thead><tbody>
          ${refused.map(e => `<tr><td>${H(stamp(e.ts))}</td><td>${H((lang() === 'en' ? EN : NL)['e_' + e.event] || w('e_refused'))}</td><td><code>${H(e.number || '')}</code></td></tr>`).join('')}</tbody></table></div>` : `<p class="intg-muted">${H(w('no_refused'))}</p>`}</div>`;
  }
  async function loadAdmin(){
    const token = S.token;
    try {
      const [status, audit] = await Promise.all([call('/api/status'), call('/api/audit').catch(() => null)]);
      if (token !== S.token) return;
      S.status = status; S.audit = audit;
    } catch (_e) { if (token !== S.token) return; S.status = null; }
    paintAdmin();
  }
  async function adminAct(fn, okMsg){
    if (S.busy) return;
    S.busy = true; paintAdmin();
    try { await fn(); if (okMsg) toast(okMsg); } catch (e) { toast((e && e.message) || w('failed')); }
    S.busy = false;
    paintMe();               // its buttons were drawn while the change ran
    await loadAdmin();
  }

  function bind(){
    const h = hosts();
    if (h.me && !h.me.dataset.waBound) {
      h.me.dataset.waBound = '1';
      h.me.addEventListener('click', ev => {
        const b = ev.target.closest('button');
        if (!b) return;
        if (b.hasAttribute('data-wa-request')) void act(async () => { S.code = await call('/api/me/link', {}); S.me = Object.assign({}, S.me, { pending: { expires_at: S.code.expires_at } }); watchCode(); });
        if (b.hasAttribute('data-wa-unlink') && confirm(w('unlink_confirm'))) void act(async () => { await call('/api/me/unlink', {}); S.me = await call('/api/me'); S.code = null; stop(); S.note = w('unlinked'); if (S.me.is_admin) void loadAdmin(); });
      });
    }
    if (h.admin && !h.admin.dataset.waBound) {
      h.admin.dataset.waBound = '1';
      h.admin.addEventListener('click', ev => {
        const b = ev.target.closest('button');
        if (!b) return;
        if (b.hasAttribute('data-wa-pairing')) void adminAct(async () => { S.pairing = await call('/api/pairing', {}); });
        if (b.dataset.waRevoke && confirm(w('revoke_confirm', { n: b.dataset.waName || '' }))) void adminAct(async () => { await call('/api/links/' + encodeURIComponent(b.dataset.waRevoke) + '/revoke', {}); if (S.me) S.me = await call('/api/me'); paintMe(); }, w('revoked'));
      });
      h.admin.addEventListener('submit', ev => {
        const form = ev.target.closest('[data-wa-settings]');
        if (!form) return;
        ev.preventDefault();
        const fd = new FormData(form);
        void adminAct(async () => { await call('/api/settings', { enabled: fd.get('enabled') === 'on', unknown_reply: String(fd.get('unknown_reply') || '') }); S.me = await call('/api/me'); paintMe(); }, w('saved'));
      });
    }
  }

  async function load(){
    const h = hosts();
    if (!h.me && !h.admin) return;
    const token = ++S.token;
    bind();
    let me;
    try { me = await call('/api/me'); } catch (_e) { me = null; }
    if (token !== S.token) return;
    // Not installed, or not reachable for this person: nothing of WhatsApp is shown.
    if (!me || typeof me.active !== 'boolean') { S.me = S.status = null; hide(); return; }
    S.me = me;
    if (S.code && left() <= 0) S.code = null;
    paintMe();
    if (me.is_admin) await loadAdmin(); else { S.status = null; paintAdmin(); }
  }
  window.SPWhatsApp = { load };
})();
