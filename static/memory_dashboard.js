// Memory explorer and Who viewed my memories in the Memory panel (A13, plan addendum 6.6).
//
// Registers one provider in window.SynthPulseMemoryExtensions (the memory
// section registry in panels.js) with the sections memdash_explorer and
// memdash_access. Both stay hidden unless /api/memdash/banks says the
// explorer is enabled. Every element is built with createElement and
// textContent; no markup string is ever parsed.
//
// The explorer is the vendored dashboard app in an iframe with
// sandbox="allow-scripts": an opaque origin with no cookie and no network.
// Its shim turns each /api/ call into a message. This bridge accepts a
// message only from the current frame's window, with origin 'null', the exact
// shape and the per-load frame key; it forwards only allowlisted paths and
// parameters to /api/memdash/v1/* with the session cookie and CSRF token, and
// replies with targetOrigin '*' (the frame is opaque). A second load event of
// the frame (it navigated) closes the bridge and replaces the frame under a
// new key; picking another store also loads a new frame under a new key.
(function () {
  'use strict';
  if (typeof window === 'undefined' || typeof document === 'undefined') return;

  var VENDOR_DIR = 'static/vendor/mnemosyne-dashboard/0.14.0-a918e5e/';
  var REASON_TTL_MS = 10 * 60 * 1000;
  var MAX_BODY = 64 * 1024;
  var MAX_QUERY = 2048;
  var MAX_INFLIGHT = 32;
  var MAX_REPLACEMENTS = 5;
  var PATH_RE = /^[a-z0-9/_-]{1,64}$/;
  var REASONS = ['none', 'support', 'safety', 'quality', 'asked', 'other'];
  var COLOUR_RE = /^#[0-9a-f]{3,8}$/;

  // App path -> the query parameters forwarded for it (addendum 6.6.5).
  var VIEW_PARAMS = {
    'stats': [], 'digest/today': ['day', 'limit'],
    'review': ['queue', 'q', 'min_importance', 'limit', 'offset'], 'lifecycle': ['limit'],
    'profile/inferred': ['limit'], 'patterns': ['limit'], 'constellation': ['limit'],
    'search': ['q', 'limit'], 'recall-debug': ['q', 'limit'], 'timeline': ['q', 'group', 'limit'],
    'memories': ['kind', 'q', 'source', 'scope', 'session_id', 'sort', 'status', 'veracity',
      'degradation_tier', 'contaminated_only', 'degraded_only', 'due_for_degradation', 'limit', 'offset'],
    'memory': ['id'], 'session': ['id', 'limit'],
    'triples': ['q', 'subject', 'predicate', 'object', 'limit'], 'graph': ['q', 'limit'],
    'consolidations': ['q', 'limit'], 'memoria/stats': [],
    'memoria/facts': ['q', 'limit', 'offset'], 'memoria/timelines': ['q', 'limit', 'offset'],
    'memoria/instructions': ['q', 'limit', 'offset'], 'memoria/kg': ['q', 'limit', 'offset'],
    'memoria/preferences': ['q', 'limit', 'offset'],
    'auth/status': [], 'health': [], 'realtime/status': [], 'admin/audit': ['limit']
  };
  var ACTION_PATHS = {
    'admin/memory/invalidate': 'invalidate', 'admin/memory/supersede': 'supersede',
    'admin/memory/importance': 'importance', 'admin/memory/veracity': 'veracity',
    'admin/memory/expiry': 'expiry'
  };
  var ACTION_FIELDS = ['memory_id', 'content', 'importance', 'veracity', 'valid_until', 'updated_at'];
  var LOCAL_ANSWERS = { 'auth/logout': { ok: true } };

  var state = {
    banks: null,
    banksPromise: null,
    currentRef: null,
    pendingRef: null,
    reasons: new Map(),
    bridge: null,
    replacements: [],
    explorerRoot: null,
    accessRoot: null,
    themeObserver: null,
    themeTimer: null,
    panelObserver: null
  };

  function tr(key) {
    var args = Array.prototype.slice.call(arguments, 1);
    if (typeof window.t === 'function') return window.t.apply(null, [key].concat(args));
    return key;
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (name) {
      var value = attrs[name];
      if (value === undefined || value === null || value === false) return;
      if (name === 'text') node.textContent = String(value);
      else if (name === 'className') node.className = value;
      else if (name.indexOf('on') === 0 && typeof value === 'function') node.addEventListener(name.slice(2), value);
      else node.setAttribute(name, value === true ? '' : String(value));
    });
    (children || []).forEach(function (child) {
      if (child === null || child === undefined || child === false) return;
      node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
    });
    return node;
  }

  function icon(name) {
    // The shared icon helper returns markup; the icons here are simple
    // strokes, so they are drawn with DOM calls instead.
    var ns = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('width', '16'); svg.setAttribute('height', '16'); svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor'); svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round'); svg.setAttribute('aria-hidden', 'true');
    var shapes = {
      eye: [['path', { d: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z' }], ['circle', { cx: '12', cy: '12', r: '3' }]],
      expand: [['polyline', { points: '15 3 21 3 21 9' }], ['polyline', { points: '9 21 3 21 3 15' }],
        ['line', { x1: '21', y1: '3', x2: '14', y2: '10' }], ['line', { x1: '3', y1: '21', x2: '10', y2: '14' }]],
      back: [['polyline', { points: '15 18 9 12 15 6' }]]
    };
    (shapes[name] || []).forEach(function (shape) {
      var node = document.createElementNS(ns, shape[0]);
      Object.keys(shape[1]).forEach(function (k) { node.setAttribute(k, shape[1][k]); });
      svg.appendChild(node);
    });
    return svg;
  }

  function csrfToken() {
    var cfg = window.__HERMES_CONFIG__ || {};
    return typeof cfg.csrfToken === 'string' ? cfg.csrfToken : '';
  }

  function call(path, opts) {
    opts = opts || {};
    var url = new URL(path, document.baseURI || location.href);
    var headers = { 'Accept': 'application/json' };
    var token = csrfToken();
    if (token) headers['X-Hermes-CSRF-Token'] = token;
    var init = { method: opts.method || 'GET', credentials: 'same-origin', headers: headers, cache: 'no-store' };
    if (opts.body !== undefined) {
      headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(opts.body);
    }
    return fetch(url.href, init).then(function (res) {
      return res.json().catch(function () { return null; }).then(function (body) {
        return { status: res.status, body: body };
      });
    }, function () {
      return { status: 503, body: { error: 'unavailable' } };
    });
  }

  function loadBanks(force) {
    if (!force && state.banks) return Promise.resolve(state.banks);
    if (!force && state.banksPromise) return state.banksPromise;
    state.banksPromise = call('api/memdash/banks').then(function (res) {
      state.banksPromise = null;
      state.banks = res.status === 200 && res.body && res.body.enabled === true ? res.body : null;
      return state.banks;
    });
    return state.banksPromise;
  }

  function storeByRef(ref) {
    var banks = state.banks;
    if (!banks || !Array.isArray(banks.stores)) return null;
    for (var i = 0; i < banks.stores.length; i++) if (banks.stores[i].ref === ref) return banks.stores[i];
    return null;
  }

  function personName(store) {
    return (store && (store.owner || store.label)) || '';
  }

  function formatWhen(value) {
    if (!value) return '';
    var date = new Date(value);
    if (isNaN(date.getTime())) return String(value);
    try { return date.toLocaleString(); } catch (_) { return date.toISOString(); }
  }

  // ── Theme ──────────────────────────────────────────────────────────────────

  function isDark() {
    var root = document.documentElement;
    if (root.classList.contains('dark')) return true;
    if (root.dataset && root.dataset.theme) return root.dataset.theme !== 'light';
    return false;
  }

  function toHex(value) {
    var text = String(value || '').trim().toLowerCase();
    if (COLOUR_RE.test(text)) return text;
    var m = text.match(/^rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})/);
    if (!m) return '';
    return '#' + [m[1], m[2], m[3]].map(function (n) {
      var v = Math.max(0, Math.min(255, parseInt(n, 10)));
      return (v < 16 ? '0' : '') + v.toString(16);
    }).join('');
  }

  // The SynthPulse appearance the frame takes over (Settings, Appearance: theme,
  // skin and font size), as the computed values of the WebUI's own tokens. The
  // frame accepts only hex and plain rgb()/rgba() colours, a font stack of
  // plain characters and pixel lengths.
  var COLOUR_TOKENS = {
    'bg': '--bg', 'surface': '--surface', 'sidebar': '--sidebar', 'code-bg': '--code-bg',
    'text': '--text', 'muted': '--muted', 'border': '--border', 'border2': '--border2',
    'accent': '--accent', 'accent-hover': '--accent-hover', 'accent-text': '--accent-text',
    'accent-bg': '--accent-bg', 'accent-bg-strong': '--accent-bg-strong', 'focus-ring': '--focus-ring',
    'input-bg': '--input-bg', 'hover-bg': '--hover-bg', 'success': '--success', 'warning': '--warning',
    'error': '--error', 'info': '--info'
  };
  var LENGTH_TOKENS = { 'radius-sm': '--radius-sm', 'radius-md': '--radius-md', 'radius-lg': '--radius-lg' };
  var RGB_RE = /^rgba?\(\s*\d{1,3}(\s*,\s*|\s+)\d{1,3}(\s*,\s*|\s+)\d{1,3}(\s*[,/]\s*(0|1|0?\.\d+|\d{1,3}%))?\s*\)$/;
  var FONT_RE = /^[A-Za-z0-9 ,"'._-]{1,240}$/;
  var LENGTH_RE = /^\d{1,3}(\.\d{1,3})?px$/;

  function cleanColour(value) {
    var text = String(value || '').trim().toLowerCase();
    return COLOUR_RE.test(text) || RGB_RE.test(text) ? text : '';
  }

  function themeMessage() {
    var root = document.documentElement;
    var style = getComputedStyle(root);
    var tokens = {};
    Object.keys(COLOUR_TOKENS).forEach(function (name) {
      var value = cleanColour(style.getPropertyValue(COLOUR_TOKENS[name]));
      if (value) tokens[name] = value;
    });
    Object.keys(LENGTH_TOKENS).forEach(function (name) {
      var value = String(style.getPropertyValue(LENGTH_TOKENS[name]) || '').trim();
      if (LENGTH_RE.test(value)) tokens[name] = value;
    });
    var font = String(style.getPropertyValue('--font-ui') || '').trim() || String(style.fontFamily || '').trim();
    if (FONT_RE.test(font)) tokens['font-ui'] = font;
    var size = String(style.fontSize || '').trim();
    if (LENGTH_RE.test(size)) tokens['font-size'] = size;
    // The four colours of the first bridge version, for a frame still on the old shim.
    var colours = {};
    [['accent', '--accent'], ['bg', '--bg'], ['panel', '--surface'], ['text', '--text']].forEach(function (pair) {
      var hex = toHex(style.getPropertyValue(pair[1]));
      if (hex) colours[pair[0]] = hex;
    });
    var fontSize = root.dataset ? root.dataset.fontSize : '';
    return {
      theme: isDark() ? 'dark' : 'light',
      colours: colours,
      tokens: tokens,
      fontSize: fontSize === 'small' || fontSize === 'large' || fontSize === 'xlarge' ? fontSize : 'default'
    };
  }

  function sendTheme(bridge, force) {
    if (!bridge || bridge.closed || !bridge.iframe.contentWindow) return;
    var msg = themeMessage();
    var signature = JSON.stringify(msg);
    if (!force && bridge.themeSent === signature) return;
    bridge.themeSent = signature;
    bridge.iframe.contentWindow.postMessage({
      v: 1, type: 'memdash:theme', k: bridge.key, theme: msg.theme, colours: msg.colours,
      tokens: msg.tokens, fontSize: msg.fontSize
    }, '*');
  }

  function scheduleTheme() {
    // A theme or skin change sets several attributes at once: send once, after.
    if (state.themeTimer) return;
    state.themeTimer = setTimeout(function () {
      state.themeTimer = null;
      sendTheme(state.bridge, false);
    }, 30);
  }

  function watchTheme() {
    if (state.themeObserver || typeof MutationObserver !== 'function') return;
    state.themeObserver = new MutationObserver(scheduleTheme);
    state.themeObserver.observe(document.documentElement, {
      attributes: true, attributeFilter: ['class', 'data-theme', 'data-skin', 'data-font-size', 'style']
    });
    // A skin that an extension registers arrives as a style element in the head.
    if (document.head) state.themeObserver.observe(document.head, { childList: true });
  }

  // ── The bridge ─────────────────────────────────────────────────────────────

  function randomKey() {
    var bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    return Array.prototype.map.call(bytes, function (b) { return (b < 16 ? '0' : '') + b.toString(16); }).join('');
  }

  function isPlainObject(value) {
    return !!value && typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype;
  }

  function validMessage(msg) {
    if (!isPlainObject(msg) || msg.v !== 1 || typeof msg.k !== 'string') return false;
    if (msg.type === 'memdash:ready') return true;
    if (msg.type !== 'memdash:req') return false;
    if (!Number.isInteger(msg.id) || msg.id < 1 || msg.id > 2147483647) return false;
    if (msg.method !== 'GET' && msg.method !== 'POST') return false;
    if (typeof msg.path !== 'string' || !PATH_RE.test(msg.path)) return false;
    if (msg.query !== undefined && msg.query !== null && !isPlainObject(msg.query)) return false;
    if (msg.body !== undefined && msg.body !== null && !isPlainObject(msg.body)) return false;
    return true;
  }

  function closeBridge() {
    var bridge = state.bridge;
    if (bridge) bridge.closed = true;
    state.bridge = null;
  }

  function reply(bridge, id, status, body) {
    if (!bridge || bridge.closed || state.bridge !== bridge || !bridge.iframe.contentWindow) return;
    bridge.iframe.contentWindow.postMessage({ v: 1, type: 'memdash:res', k: bridge.key, id: id, status: status, body: body }, '*');
  }

  function freshReason(ref) {
    var reason = state.reasons.get(ref);
    if (!reason || Date.now() - reason.at > REASON_TTL_MS) return null;
    return reason;
  }

  function routeFor(bridge, msg) {
    var path = msg.path;
    if (msg.method === 'GET' && Object.prototype.hasOwnProperty.call(VIEW_PARAMS, path)) {
      var params = new URLSearchParams();
      params.set('bank', bridge.ref);
      params.set('view', path);
      var query = msg.query || {};
      VIEW_PARAMS[path].forEach(function (name) {
        var value = query[name];
        if (typeof value === 'string' || typeof value === 'number') params.set(name, String(value));
      });
      var store = storeByRef(bridge.ref);
      var reason = store && !store.own ? freshReason(bridge.ref) : null;
      if (reason) {
        params.set('reason_code', reason.code);
        if (reason.code === 'other' && reason.text) params.set('reason_text', reason.text);
      }
      return { kind: 'view', url: 'api/memdash/v1/view?' + params.toString() };
    }
    if (msg.method === 'POST' && Object.prototype.hasOwnProperty.call(LOCAL_ANSWERS, path)) {
      return { kind: 'local', body: LOCAL_ANSWERS[path] };
    }
    if (msg.method === 'POST' && Object.prototype.hasOwnProperty.call(ACTION_PATHS, path)) {
      var body = { bank: bridge.ref, action: ACTION_PATHS[path] };
      var source = msg.body || {};
      ACTION_FIELDS.forEach(function (name) {
        if (Object.prototype.hasOwnProperty.call(source, name)) body[name] = source[name];
      });
      return { kind: 'action', body: body };
    }
    return null;
  }

  function handleRequest(bridge, msg) {
    var querySize = JSON.stringify(msg.query || {}).length;
    var bodySize = JSON.stringify(msg.body || {}).length;
    if (querySize > MAX_QUERY || bodySize > MAX_BODY) { reply(bridge, msg.id, 413, { error: 'request too large' }); return; }
    if (bridge.inflight >= MAX_INFLIGHT) { reply(bridge, msg.id, 429, { error: 'too many requests' }); return; }
    var route = routeFor(bridge, msg);
    if (!route) { reply(bridge, msg.id, 404, { error: 'not found' }); return; }
    if (route.kind === 'local') { reply(bridge, msg.id, 200, route.body); return; }
    bridge.inflight += 1;
    var done = function (res) {
      bridge.inflight -= 1;
      reply(bridge, msg.id, res.status, res.body);
    };
    if (route.kind === 'view') { call(route.url).then(done); return; }
    var store = storeByRef(bridge.ref);
    var needReason = store && !store.own;
    var withReason = needReason ? askEditReason(store) : Promise.resolve({ code: 'none', text: '' });
    withReason.then(function (reason) {
      if (!reason) { done({ status: 400, body: { error: tr('memdash_readonly_note') } }); return; }
      route.body.reason_code = reason.code;
      if (reason.text) route.body.reason_text = reason.text;
      call('api/memdash/v1/action', { method: 'POST', body: route.body }).then(done);
    });
  }

  function onMessage(event) {
    var bridge = state.bridge;
    if (!bridge || bridge.closed) return;
    if (event.source !== bridge.iframe.contentWindow) return;
    if (event.origin !== 'null') return;
    var msg = event.data;
    if (!validMessage(msg) || msg.k !== bridge.key) return;
    if (msg.type === 'memdash:ready') { bridge.ready = true; sendTheme(bridge, true); return; }
    handleRequest(bridge, msg);
  }

  function onFrameLoad(bridge) {
    if (bridge.closed || state.bridge !== bridge) return;
    try {
      // The initial about:blank document is same-origin and readable.
      if (bridge.iframe.contentWindow.location.href === 'about:blank') return;
    } catch (_) { /* the vendored document is opaque */ }
    bridge.loads += 1;
    if (bridge.loads > 1) { replaceFrame(bridge); return; }
    sendTheme(bridge, true);
  }

  function replaceFrame(bridge) {
    closeBridge();
    var now = Date.now();
    state.replacements = state.replacements.filter(function (at) { return now - at < 60000; });
    state.replacements.push(now);
    var holder = bridge.iframe.parentNode;
    if (!holder) return;
    if (state.replacements.length > MAX_REPLACEMENTS) {
      holder.replaceChildren(el('div', { className: 'memdash-message', role: 'status', text: tr('memdash_unavailable') }));
      return;
    }
    mountFrame(holder, bridge.ref);
  }

  function mountFrame(holder, ref) {
    closeBridge();
    var key = randomKey();
    var iframe = document.createElement('iframe');
    iframe.setAttribute('sandbox', 'allow-scripts');
    iframe.setAttribute('referrerpolicy', 'no-referrer');
    iframe.setAttribute('title', tr('memdash_section_label'));
    iframe.className = 'memdash-frame';
    var bridge = { key: key, ref: ref, iframe: iframe, loads: 0, inflight: 0, closed: false, ready: false };
    iframe.addEventListener('load', function () { onFrameLoad(bridge); });
    iframe.src = VENDOR_DIR + 'index.html#theme=' + (isDark() ? 'dark' : 'light') + '&k=' + key;
    state.bridge = bridge;
    holder.replaceChildren(iframe);
    watchTheme();
    return bridge;
  }

  // ── Dialogs ────────────────────────────────────────────────────────────────

  function openDialog(content, onClose) {
    var dialog = el('dialog', { className: 'memdash-dialog' }, [content]);
    document.body.appendChild(dialog);
    var closed = false;
    var close = function (value) {
      if (closed) return;
      closed = true;
      try { if (dialog.open) dialog.close(); } catch (_) { /* ignore */ }
      dialog.remove();
      onClose(value);
    };
    dialog.addEventListener('cancel', function (event) { event.preventDefault(); close(null); });
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
    return close;
  }

  function reasonFields(name) {
    var select = el('select', { className: 'memdash-reason-select', id: 'memdashReasonSelect' });
    REASONS.forEach(function (code) {
      var label = code === 'asked' ? tr('memdash_reason_asked', name) : tr('memdash_reason_' + code);
      select.appendChild(el('option', { value: code, text: label }));
    });
    select.value = 'none';
    var other = el('input', { type: 'text', className: 'memdash-reason-text', maxlength: '200', 'aria-label': tr('memdash_reason_other') });
    other.hidden = true;
    select.addEventListener('change', function () { other.hidden = select.value !== 'other'; if (!other.hidden) other.focus(); });
    var label = el('label', { className: 'memdash-reason-label', for: 'memdashReasonSelect', text: tr('memdash_reason_label', name) });
    return { nodes: [label, select, other], read: function () { return { code: select.value, text: select.value === 'other' ? other.value.trim().slice(0, 200) : '' }; } };
  }

  function confirmOpen(store) {
    var name = personName(store);
    return new Promise(function (resolve) {
      var fields = reasonFields(name);
      var close;
      var openBtn = el('button', { type: 'button', className: 'memdash-btn memdash-btn-primary', text: tr('memdash_open'), onclick: function () { close(fields.read()); } });
      var backBtn = el('button', { type: 'button', className: 'memdash-btn', text: tr('memdash_back_to_mine'), onclick: function () { close(null); } });
      var content = el('div', { className: 'memdash-dialog-body', role: 'document' }, [
        el('h2', { className: 'memdash-dialog-title', text: tr('memdash_open_other_title', name) }),
        el('p', { className: 'memdash-dialog-text', text: tr('memdash_open_other_body', name) })
      ].concat(fields.nodes).concat([el('div', { className: 'memdash-dialog-actions' }, [backBtn, openBtn])]));
      close = openDialog(content, resolve);
      openBtn.focus();
    });
  }

  function askEditReason(store) {
    var reason = freshReason(store.ref);
    if (reason && reason.code !== 'none') return Promise.resolve(reason);
    var name = personName(store);
    return new Promise(function (resolve) {
      var fields = reasonFields(name);
      var close;
      var saveBtn = el('button', { type: 'button', className: 'memdash-btn memdash-btn-primary', text: tr('save'), onclick: function () {
        var value = fields.read();
        if (value.code === 'none' || (value.code === 'other' && !value.text)) return;
        value.at = Date.now();
        state.reasons.set(store.ref, value);
        close(value);
      } });
      var cancelBtn = el('button', { type: 'button', className: 'memdash-btn', text: tr('cancel'), onclick: function () { close(null); } });
      var content = el('div', { className: 'memdash-dialog-body', role: 'document' }, [
        el('h2', { className: 'memdash-dialog-title', text: tr('memdash_edit_reason_title') })
      ].concat(fields.nodes).concat([el('div', { className: 'memdash-dialog-actions' }, [cancelBtn, saveBtn])]));
      close = openDialog(content, resolve);
    });
  }

  // ── Notice card ────────────────────────────────────────────────────────────

  function noticeCard(onDone) {
    var banks = state.banks;
    var notice = banks && banks.notice;
    if (!notice || !notice.required || !notice.variant) return null;
    var card = el('section', { className: 'memdash-notice', role: 'region', 'aria-label': tr('memdash_notice_title') });
    var ack = function (manage) {
      call('api/memdash/notice', { method: 'POST', body: { version: notice.version } }).then(function (res) {
        if (res.status !== 200) return;
        notice.required = false;
        card.remove();
        if (manage) openSelfView();
        if (onDone) onDone();
      });
    };
    card.appendChild(el('h2', { className: 'memdash-notice-title', text: tr('memdash_notice_title') }));
    card.appendChild(el('p', { className: 'memdash-notice-body', text: tr('memdash_notice_body_' + notice.variant) }));
    card.appendChild(el('div', { className: 'memdash-notice-actions' }, [
      el('button', { type: 'button', className: 'memdash-btn memdash-btn-primary', text: tr('memdash_notice_ok'), onclick: function () { ack(false); } }),
      el('button', { type: 'button', className: 'memdash-btn', text: tr('memdash_notice_manage'), onclick: function () { ack(true); } })
    ]));
    return card;
  }

  function sideButton(labelKey) {
    var label = tr(labelKey);
    var buttons = document.querySelectorAll('#memoryPanel .side-menu-item');
    for (var i = 0; i < buttons.length; i++) {
      var span = buttons[i].querySelector('span');
      if (span && span.textContent === label) return buttons[i];
    }
    return null;
  }

  function openSelfView() {
    var button = sideButton('mnemo_section_label');
    if (button && typeof window.openMemorySection === 'function') window.openMemorySection('mnemo_me', button);
  }

  // ── Memory explorer ────────────────────────────────────────────────────────

  // The interim registry names a person's own stores in English; show them
  // in the WebUI language.
  function storeLabel(label) {
    var text = String(label || '');
    var legacy = / \(legacy\)$/.test(text);
    if (legacy) text = text.slice(0, -' (legacy)'.length);
    var conversation = text.match(/^Conversation memories ([0-9a-f]{8})$/);
    if (text === 'Personal memories') text = tr('memdash_store_personal');
    else if (conversation) text = tr('memdash_store_conversation', conversation[1]);
    return legacy ? tr('memdash_store_legacy', text) : text;
  }

  function pickerOptions(select, stores, filter) {
    select.replaceChildren();
    var groups = { mine: [], people: [], assistants: [], shared: [] };
    stores.forEach(function (store) {
      if (filter && !store.own && String(store.label + ' ' + (store.owner || '')).toLowerCase().indexOf(filter) === -1) return;
      (groups[store.group] || groups.shared).push(store);
    });
    var labelFor = function (store) {
      var text = store.own && store.primary ? tr('memdash_picker_me') : storeLabel(store.label);
      return store.last_write ? text + ' · ' + tr('memdash_store_last_write', formatWhen(store.last_write)) : text;
    };
    [['mine', null], ['people', 'memdash_picker_group_people'], ['assistants', 'memdash_picker_group_assistants'], ['shared', 'memdash_picker_group_shared']].forEach(function (pair) {
      var list = groups[pair[0]];
      if (!list.length) return;
      var parent = select;
      if (pair[1]) {
        var orgLabel = list[0].org_label || '';
        parent = el('optgroup', { label: pair[0] === 'people' ? tr(pair[1], orgLabel) : tr(pair[1]) });
        select.appendChild(parent);
      }
      list.forEach(function (store) {
        var option = el('option', { value: store.ref, text: labelFor(store) });
        if (store.ref === state.currentRef) option.selected = true;
        parent.appendChild(option);
      });
    });
  }

  function selectStore(ref) {
    var store = storeByRef(ref);
    if (!store) return;
    if (store.own) { showStore(ref); return; }
    confirmOpen(store).then(function (reason) {
      if (!reason) { renderExplorer(state.explorerRoot); return; }
      reason.at = Date.now();
      state.reasons.set(ref, reason);
      showStore(ref);
    });
  }

  function showStore(ref) {
    state.currentRef = ref;
    renderExplorer(state.explorerRoot);
  }

  function fullscreenButton(target) {
    var button = el('button', { type: 'button', className: 'memdash-btn memdash-btn-icon' }, [icon('expand'), el('span', { text: tr('memdash_fullscreen') })]);
    var sync = function () {
      var on = document.fullscreenElement === target;
      button.querySelector('span').textContent = on ? tr('memdash_exit_fullscreen') : tr('memdash_fullscreen');
      target.classList.toggle('memdash-is-fullscreen', on);
    };
    button.addEventListener('click', function () {
      if (document.fullscreenElement === target) { if (document.exitFullscreen) document.exitFullscreen(); }
      else if (target.requestFullscreen) target.requestFullscreen().catch(function () { /* not allowed */ });
    });
    document.addEventListener('fullscreenchange', sync);
    if (typeof document.exitFullscreen !== 'function') button.hidden = true;
    return button;
  }

  function renderExplorer(body) {
    if (!body) return;
    state.explorerRoot = body;
    var banks = state.banks;
    var root = el('div', { className: 'memdash', 'data-memdash': 'explorer' });
    body.replaceChildren(root);
    if (!banks || !banks.available || !Array.isArray(banks.stores) || !banks.stores.length) {
      closeBridge();
      root.appendChild(el('div', { className: 'memdash-message', role: 'status', text: tr('memdash_unavailable') }));
      return;
    }
    var notice = noticeCard(function () { renderExplorer(state.explorerRoot); });
    if (notice) root.appendChild(notice);
    if (state.pendingRef) {
      var pending = state.pendingRef;
      state.pendingRef = null;
      if (storeByRef(pending)) { selectStore(pending); return; }
    }
    if (!state.currentRef || !storeByRef(state.currentRef)) state.currentRef = banks.me || banks.stores[0].ref;
    var store = storeByRef(state.currentRef);

    var toolbar = el('div', { className: 'memdash-toolbar' });
    if (banks.stores.length > 1) {
      var select = el('select', { className: 'memdash-picker', id: 'memdashPicker' });
      pickerOptions(select, banks.stores, '');
      select.addEventListener('change', function () { selectStore(select.value); });
      toolbar.appendChild(el('label', { className: 'memdash-picker-label', for: 'memdashPicker', text: tr('memdash_picker_label') }));
      toolbar.appendChild(select);
      var othersListed = banks.stores.some(function (s) { return !s.own; });
      if (banks.viewer && banks.viewer.admin && othersListed) {
        var search = el('input', { type: 'search', className: 'memdash-picker-search', placeholder: tr('memdash_picker_search'), 'aria-label': tr('memdash_picker_search') });
        search.addEventListener('input', function () { pickerOptions(select, banks.stores, search.value.trim().toLowerCase()); });
        toolbar.appendChild(search);
      }
    }
    var frameBox = el('div', { className: 'memdash-frame-box' });
    toolbar.appendChild(el('span', { className: 'memdash-toolbar-spacer' }));
    toolbar.appendChild(fullscreenButton(frameBox));
    toolbar.appendChild(el('a', { className: 'memdash-licences', href: VENDOR_DIR + 'VENDOR.md', target: '_blank', rel: 'noopener noreferrer', text: tr('memdash_licences') }));
    root.appendChild(toolbar);

    if (store && !store.own) {
      var name = personName(store);
      var banner = el('div', { className: 'memdash-banner', role: 'status' }, [
        icon('eye'),
        el('span', { className: 'memdash-banner-text', text: tr('memdash_viewing_banner', name) }),
        el('button', { type: 'button', className: 'memdash-btn', onclick: function () { showStore(banks.me || banks.stores[0].ref); } }, [icon('back'), el('span', { text: tr('memdash_back_to_mine') })])
      ]);
      root.appendChild(banner);
      if (!(banks.changes_available && store.kind !== 'personal')) {
        root.appendChild(el('p', { className: 'memdash-note', text: tr('memdash_readonly_note') }));
      }
    }
    root.appendChild(frameBox);
    root.appendChild(el('p', { className: 'memdash-note memdash-coverage', text: tr('memdash_coverage_note') }));
    mountFrame(frameBox, state.currentRef);
  }

  // ── Who viewed my memories ─────────────────────────────────────────────────

  function roleLabel(role) {
    return role === 'org_admin' ? tr('memdash_access_role_org') : tr('memdash_access_role_platform');
  }

  function reasonLabel(session) {
    if (!session.reason_code || session.reason_code === 'none') return '';
    if (session.reason_code === 'other') return session.reason_text || tr('memdash_reason_other');
    if (session.reason_code === 'asked') {
      var me = state.banks && state.banks.viewer ? state.banks.viewer.display : '';
      return tr('memdash_reason_asked', me);
    }
    return tr('memdash_reason_' + session.reason_code);
  }

  function sessionCard(session) {
    var headline;
    if (session.forgot) headline = tr('memdash_access_row_forgot', session.viewer, session.forgot);
    else if (session.changed) headline = tr('memdash_access_row_changed', session.viewer, session.changed);
    else headline = tr('memdash_access_row', session.viewer);
    var reason = reasonLabel(session);
    return el('li', { className: 'memdash-session' + (session.new ? ' is-new' : '') }, [
      el('div', { className: 'memdash-session-head' }, [
        el('strong', { className: 'memdash-session-title', text: headline }),
        el('span', { className: 'memdash-role', text: roleLabel(session.role) })
      ]),
      el('div', { className: 'memdash-session-meta', text: tr('memdash_access_when', formatWhen(session.start), formatWhen(session.end)) }),
      el('div', { className: 'memdash-session-meta', text: tr('memdash_access_detail', session.views, session.items, session.searches) }),
      reason ? el('div', { className: 'memdash-session-meta', text: tr('memdash_access_reason', reason) }) : null
    ]);
  }

  function renderAccess(body) {
    if (!body) return;
    state.accessRoot = body;
    var root = el('div', { className: 'memdash', 'data-memdash': 'access' });
    body.replaceChildren(root);
    var notice = noticeCard(function () { renderAccess(state.accessRoot); });
    if (notice) root.appendChild(notice);
    var list = el('div', { className: 'memdash-access', 'aria-live': 'polite' });
    root.appendChild(list);
    call('api/memdash/access-log?scope=me').then(function (res) {
      if (state.accessRoot !== body) return;
      if (res.status !== 200 || !res.body || !Array.isArray(res.body.sessions)) {
        list.replaceChildren(el('div', { className: 'memdash-message', role: 'status', text: tr('memdash_unavailable') }));
        return;
      }
      var data = res.body;
      if (!data.sessions.length) {
        list.replaceChildren(el('div', { className: 'memdash-message memdash-empty', text: tr('memdash_access_empty') }));
      } else {
        var items = el('ul', { className: 'memdash-sessions' });
        data.sessions.forEach(function (session) { items.appendChild(sessionCard(session)); });
        list.replaceChildren(items);
      }
      if (data.unseen > 0 && data.last_id) {
        call('api/memdash/access-log/seen', { method: 'POST', body: { until_id: data.last_id } }).then(function (seen) {
          if (seen.status === 200 && state.banks) { state.banks.unseen = 0; decorateUnseen(); }
        });
      }
    });
  }

  function decorateUnseen() {
    var button = sideButton('memdash_access_section_label');
    if (!button) return;
    var badge = button.querySelector('.memdash-unseen');
    var count = state.banks && state.banks.unseen > 0 ? state.banks.unseen : 0;
    if (!count) { if (badge) badge.remove(); return; }
    if (!badge) { badge = el('span', { className: 'memdash-unseen' }); button.appendChild(badge); }
    badge.textContent = tr('memdash_access_new', count);
  }

  function watchPanel() {
    if (state.panelObserver || typeof MutationObserver !== 'function') return;
    var panel = document.getElementById('memoryPanel');
    if (!panel) return;
    state.panelObserver = new MutationObserver(function () { decorateUnseen(); });
    state.panelObserver.observe(panel, { childList: true });
  }

  // ── Registration ───────────────────────────────────────────────────────────

  var provider = {
    sections: function () {
      return loadBanks(true).then(function (banks) {
        if (!banks) { closeBridge(); return []; }
        watchPanel();
        setTimeout(decorateUnseen, 0);
        return [
          { key: 'memdash_explorer', labelKey: 'memdash_section_label', iconKey: 'map', titleKey: 'memdash_section_tooltip' },
          { key: 'memdash_access', labelKey: 'memdash_access_section_label', iconKey: 'eye', titleKey: 'memdash_access_section_tooltip' }
        ];
      }, function () { return []; });
    },
    render: function (key, slots) {
      var body = slots && slots.body;
      if (slots && slots.empty) slots.empty.style.display = 'none';
      if (body) body.style.display = '';
      if (key === 'memdash_access') { closeBridge(); renderAccess(body); return; }
      renderExplorer(body);
    }
  };

  window.addEventListener('message', onMessage);
  var registry = Array.isArray(window.SynthPulseMemoryExtensions)
    ? window.SynthPulseMemoryExtensions
    : (window.SynthPulseMemoryExtensions = []);
  registry.push(provider);

  window.SynthPulseMemoryDashboard = Object.freeze({
    open: function (ref) {
      if (typeof ref !== 'string' || !/^b_[0-9a-f]{32}$/.test(ref)) return false;
      state.pendingRef = ref;
      var go = function () {
        var button = sideButton('memdash_section_label');
        if (button && typeof window.openMemorySection === 'function') window.openMemorySection('memdash_explorer', button);
      };
      if (typeof window.switchPanel === 'function') Promise.resolve(window.switchPanel('memory')).then(function () { setTimeout(go, 0); });
      else go();
      return true;
    }
  });
})();
