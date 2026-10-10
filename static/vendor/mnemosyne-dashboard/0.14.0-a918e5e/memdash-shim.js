/*
 * Memory explorer frame shim (plan addendum 6.6.4). Loaded before app.js.
 *
 * The frame runs in an opaque origin (CSP sandbox allow-scripts) with no
 * network (connect-src 'none'), no cookie and no storage. This shim:
 *   - reads the per-load frame key and the theme from the URL fragment, then
 *     removes the fragment from the address;
 *   - gives app.js an in-memory __mdStore in place of localStorage;
 *   - removes EventSource, so live updates are off;
 *   - replaces fetch: a URL that starts with /api/ becomes a message to the
 *     parent WebUI panel, which answers it; anything else is refused;
 *   - applies theme messages from the parent (dark or light, four colours).
 * It never builds HTML from strings.
 */
(function () {
  'use strict';

  var fragment = String(location.hash || '').replace(/^#/, '');
  var params = new URLSearchParams(fragment);
  var key = String(params.get('k') || '');
  var theme = params.get('theme') === 'light' ? 'light' : 'dark';
  if (!/^[0-9a-f]{32}$/.test(key)) key = '';
  try { history.replaceState(null, '', location.pathname + location.search); } catch (_) { /* opaque origin */ }

  // app.js pushes a history entry per tab; in a frame that would fill the
  // WebUI's back button, so every push replaces the current entry instead.
  try {
    var replace = history.replaceState.bind(history);
    history.pushState = function (state, title, url) {
      try { replace(state, title, url); } catch (_) { /* opaque origin */ }
    };
    history.replaceState = function (state, title, url) {
      try { replace(state, title, url); } catch (_) { /* opaque origin */ }
    };
  } catch (_) { /* keep the browser's own */ }

  var store = Object.create(null);
  store['mnemosyne-dashboard-theme'] = theme;
  var mdStore = Object.freeze({
    getItem: function (k) { k = String(k); return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
    setItem: function (k, v) { store[String(k)] = String(v); },
    removeItem: function (k) { delete store[String(k)]; },
    clear: function () { Object.keys(store).forEach(function (k) { delete store[k]; }); }
  });
  Object.defineProperty(window, '__mdStore', { value: mdStore, writable: false, configurable: false });
  document.documentElement.dataset.theme = theme;

  try { delete window.EventSource; } catch (_) { /* ignore */ }
  if ('EventSource' in window) {
    try { Object.defineProperty(window, 'EventSource', { value: undefined, configurable: true }); } catch (_) { /* ignore */ }
  }

  var parentWindow = window.parent && window.parent !== window ? window.parent : null;
  var targetOrigin = (typeof location.origin === 'string' && location.origin && location.origin !== 'null') ? location.origin : '*';
  var pending = new Map();
  var nextId = 1;
  var TIMEOUT_MS = 30000;
  var COLOUR_RE = /^#[0-9a-f]{3,8}$/;
  var COLOUR_VARS = { accent: '--accent', bg: '--bg', panel: '--panel', text: '--text' };

  function refuse() {
    return Promise.reject(new TypeError('Network access is not available here.'));
  }

  function showStandalone() {
    // Opened outside SynthPulse (no parent or no key): no call is ever made.
    window.fetch = refuse;
    document.addEventListener('DOMContentLoaded', function () {
      var note = document.createElement('div');
      note.className = 'memdash-standalone';
      note.setAttribute('role', 'status');
      note.textContent = 'Open this from Memory in SynthPulse';
      document.body.appendChild(note);
    });
  }

  if (!parentWindow || !key) {
    showStandalone();
    return;
  }

  function applyTheme(msg) {
    var mode = msg.theme === 'light' ? 'light' : 'dark';
    var root = document.documentElement;
    if (typeof window.setTheme === 'function') {
      try { window.setTheme(mode); } catch (_) { root.dataset.theme = mode; }
    } else {
      root.dataset.theme = mode;
    }
    var colours = msg.colours && typeof msg.colours === 'object' ? msg.colours : {};
    Object.keys(COLOUR_VARS).forEach(function (name) {
      var value = colours[name];
      if (typeof value === 'string' && COLOUR_RE.test(value)) root.style.setProperty(COLOUR_VARS[name], value);
    });
  }

  function toQuery(searchParams) {
    var out = {};
    searchParams.forEach(function (value, name) { out[name] = value; });
    return out;
  }

  window.addEventListener('message', function (event) {
    if (event.source !== parentWindow) return;
    var msg = event.data;
    if (!msg || typeof msg !== 'object' || msg.v !== 1 || msg.k !== key) return;
    if (msg.type === 'memdash:theme') { applyTheme(msg); return; }
    if (msg.type !== 'memdash:res' || typeof msg.id !== 'number') return;
    var entry = pending.get(msg.id);
    if (!entry) return;
    pending.delete(msg.id);
    clearTimeout(entry.timer);
    var status = Number(msg.status) || 502;
    if (status < 200 || status > 599) status = 502;
    var body = JSON.stringify(msg.body === undefined ? null : msg.body);
    entry.resolve(new Response(body, { status: status, headers: { 'Content-Type': 'application/json' } }));
  });

  window.fetch = function (input, init) {
    var raw = typeof input === 'string' ? input : (input && typeof input.url === 'string' ? input.url : '');
    if (typeof raw !== 'string' || raw.indexOf('/api/') !== 0) return refuse();
    var url;
    try { url = new URL(raw, location.href); } catch (_) { return refuse(); }
    if (url.pathname.indexOf('/api/') !== 0) return refuse();
    var method = String((init && init.method) || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'POST') return refuse();
    var body = null;
    if (init && typeof init.body === 'string' && init.body) {
      try { body = JSON.parse(init.body); } catch (_) { return refuse(); }
    }
    var id = nextId++;
    return new Promise(function (resolve, reject) {
      var timer = setTimeout(function () {
        pending.delete(id);
        reject(new TypeError('The request timed out.'));
      }, TIMEOUT_MS);
      pending.set(id, { resolve: resolve, reject: reject, timer: timer });
      parentWindow.postMessage({
        v: 1, type: 'memdash:req', k: key, id: id, method: method,
        path: url.pathname.slice('/api/'.length), query: toQuery(url.searchParams), body: body
      }, targetOrigin);
    });
  };

  parentWindow.postMessage({ v: 1, type: 'memdash:ready', k: key }, targetOrigin);
})();
