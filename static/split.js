// Split view : run up to 8 chats side by side for multitasking.
//
// Two halves, one file:
//
// 1. PANE MODE (`?pane=1` in the URL). The app itself, embedded in an iframe
//    by the split overlay. Chrome is reduced (no reload/profile buttons, no
//    nested split button), the sidebar starts collapsed but stays reachable
//    through the hamburger, the global gateway SSE stays off (8 panes on an
//    HTTP/1.1 origin would exhaust the browser's 6-connection budget), and
//    localStorage writes that would fight with the parent window
//    (`hermes-webui-session`, sidebar-collapsed) are suppressed. The pane
//    reports its active session upward so the parent can restore the exact
//    layout next time.
//
// 2. SPLIT OVERLAY (normal window). A full-viewport grid of same-origin
//    iframes, each a pane-mode app. Layout picker for 2/3/4/6/8 panes,
//    per-slot close, state persisted in localStorage
//    (`hermes-webui-split-state`). Requires frame-ancestors 'self' /
//    X-Frame-Options SAMEORIGIN (api/helpers.py) : same-origin only, the
//    embed surface for the outside world stays closed.
'use strict';

const _SPLIT_STATE_KEY = 'hermes-webui-split-state';
const _SPLIT_MAX_PANES = 8;
const _SPLIT_ALLOWED_COUNTS = [2, 3, 4, 6, 8];
// count -> [columns, rows]
const _SPLIT_GRIDS = { 2: [2, 1], 3: [3, 1], 4: [2, 2], 6: [3, 2], 8: [4, 2] };

function _splitIsPaneMode() {
  try { return new URLSearchParams(window.location.search || '').get('pane') === '1'; }
  catch (_e) { return false; }
}

// Boot (sessions.js startGatewaySSE) reads this before the async boot flow runs;
// all deferred scripts execute before DOMContentLoaded, so top-level is early enough.
window.__HERMES_PANE_MODE = _splitIsPaneMode();

// ── Pane mode ──────────────────────────────────────────────────────────────

(function _splitPaneInit() {
  if (!window.__HERMES_PANE_MODE) return;
  document.documentElement.setAttribute('data-pane', '1');

  // Keep pane-local UI state out of the shared localStorage: the parent window
  // owns "last session" and the sidebar preference. Everything else persists
  // normally (theme, locale, drafts are server-side).
  try {
    const _blocked = new Set(['hermes-webui-session', 'hermes-webui-sidebar-collapsed', 'hermes-webui-rail-expanded']);
    const _origSet = window.localStorage.setItem.bind(window.localStorage);
    window.localStorage.setItem = function (k, v) {
      if (_blocked.has(String(k))) return;
      return _origSet(k, v);
    };
  } catch (_e) { /* storage may be unavailable; pane still works */ }

  document.addEventListener('DOMContentLoaded', () => {
    // Sidebar: collapsed by default, hamburger toggles it inline without
    // persisting (the layout class is the non-persistent channel).
    const layout = document.querySelector('.layout');
    if (layout) layout.classList.add('sidebar-collapsed');
    const burger = document.getElementById('btnHamburger');
    if (burger) {
      burger.onclick = function () {
        if (!layout) return;
        layout.classList.toggle('sidebar-collapsed');
      };
    }
    // Report the active session upward so the parent can persist the layout.
    let _lastReported = null;
    setInterval(() => {
      try {
        const sid = (window.S && S.session && S.session.session_id) || null;
        if (sid === _lastReported) return;
        _lastReported = sid;
        window.parent.postMessage({ type: 'hermes-pane-session', sid: sid }, window.location.origin);
      } catch (_e) { /* parent gone or cross-origin : ignore */ }
    }, 2000);
  });
})();

// ── Split overlay (parent window) ──────────────────────────────────────────

let _splitState = null;    // {count, sessions: (sid|null)[]}
let _splitOpen = false;

function _splitLoadState() {
  try {
    const raw = localStorage.getItem(_SPLIT_STATE_KEY);
    if (!raw) return null;
    const st = JSON.parse(raw);
    if (!st || !_SPLIT_ALLOWED_COUNTS.includes(st.count) || !Array.isArray(st.sessions)) return null;
    st.sessions = st.sessions.slice(0, _SPLIT_MAX_PANES).map(s => (typeof s === 'string' && s) ? s : null);
    return st;
  } catch (_e) { return null; }
}

function _splitSaveState() {
  if (!_splitState) return;
  try { localStorage.setItem(_SPLIT_STATE_KEY, JSON.stringify(_splitState)); } catch (_e) {}
}

function _splitPaneUrl(sid) {
  const qs = new URLSearchParams();
  qs.set('pane', '1');
  if (sid) qs.set('session', sid);
  return window.location.pathname.replace(/\/session\/.*$/, '/') + '?' + qs.toString();
}

function _splitEnsureOverlay() {
  let overlay = document.getElementById('splitOverlay');
  if (overlay) return overlay;
  overlay = document.createElement('div');
  overlay.id = 'splitOverlay';
  overlay.setAttribute('role', 'region');
  overlay.setAttribute('aria-label', t('split_view'));
  overlay.innerHTML =
    '<div class="split-toolbar">' +
      '<span class="split-toolbar-title">' + t('split_view') + '</span>' +
      '<div class="split-toolbar-counts" id="splitCounts"></div>' +
      '<div class="split-toolbar-spacer"></div>' +
      '<button type="button" class="split-exit" id="btnSplitExit">' + t('split_view_exit') + '</button>' +
    '</div>' +
    '<div class="split-grid" id="splitGrid"></div>';
  document.body.appendChild(overlay);
  overlay.querySelector('#btnSplitExit').onclick = () => toggleSplitView(false);
  const counts = overlay.querySelector('#splitCounts');
  for (const n of _SPLIT_ALLOWED_COUNTS) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'split-count-btn';
    b.dataset.count = String(n);
    b.textContent = String(n);
    b.title = t('split_view_panes', n);
    b.onclick = () => _splitSetCount(n);
    counts.appendChild(b);
  }
  window.addEventListener('message', _splitOnPaneMessage);
  return overlay;
}

function _splitOnPaneMessage(ev) {
  if (ev.origin !== window.location.origin) return;
  const d = ev.data;
  if (!d || d.type !== 'hermes-pane-session' || !_splitState) return;
  const frames = document.querySelectorAll('#splitGrid iframe');
  for (let i = 0; i < frames.length; i++) {
    if (frames[i].contentWindow === ev.source) {
      frames[i].dataset.splitSid = d.sid || '';
      if (_splitState.sessions[i] !== d.sid) {
        _splitState.sessions[i] = d.sid || null;
        _splitSaveState();
      }
      return;
    }
  }
}

// Most-recent-first non-archived session ids from the parent window's sidebar
// cache (sessions.js `_allSessions`, loaded before this script), minus the ones
// already claimed by a slot.
function _splitRecentSessionIds(exclude, limit) {
  try {
    const rows = (typeof _allSessions !== 'undefined' && Array.isArray(_allSessions)) ? _allSessions : [];
    const out = [];
    for (const s of rows) {
      if (!s || !s.session_id || s.archived) continue;
      if (exclude.has(s.session_id)) continue;
      out.push(s.session_id);
      if (out.length >= limit) break;
    }
    return out;
  } catch (_e) { return []; }
}

// Every pane should be a DIFFERENT chat: drop duplicate sids (first slot wins),
// then fill the empty slots with the most recent sessions not yet on screen.
function _splitFillDistinct() {
  if (!_splitState) return;
  const seen = new Set();
  for (let i = 0; i < _splitState.sessions.length; i++) {
    const sid = _splitState.sessions[i];
    if (!sid) continue;
    if (seen.has(sid)) _splitState.sessions[i] = null;
    else seen.add(sid);
  }
  const fresh = _splitRecentSessionIds(seen, _splitState.count);
  for (let i = 0; i < _splitState.count && fresh.length; i++) {
    if (!_splitState.sessions[i]) _splitState.sessions[i] = fresh.shift();
  }
}

function _splitSetCount(n) {
  if (!_SPLIT_ALLOWED_COUNTS.includes(n)) return;
  _splitState = _splitState || { count: n, sessions: [] };
  _splitState.count = n;
  while (_splitState.sessions.length < n) _splitState.sessions.push(null);
  _splitFillDistinct();
  _splitSaveState();
  _splitRender();
}

function _splitRender() {
  const overlay = _splitEnsureOverlay();
  const grid = overlay.querySelector('#splitGrid');
  const [cols, rows] = _SPLIT_GRIDS[_splitState.count];
  grid.style.gridTemplateColumns = `repeat(${cols}, minmax(0,1fr))`;
  grid.style.gridTemplateRows = `repeat(${rows}, minmax(0,1fr))`;
  overlay.querySelectorAll('.split-count-btn').forEach(b => {
    b.classList.toggle('active', Number(b.dataset.count) === _splitState.count);
  });

  // Reuse existing slots so switching 4 -> 8 doesn't reload the first four
  // panes; only build what is missing and drop what falls off the end.
  const existing = Array.from(grid.children);
  for (let i = existing.length - 1; i >= _splitState.count; i--) existing[i].remove();
  for (let i = 0; i < _splitState.count; i++) {
    if (grid.children[i]) {
      // Slot already on screen: retarget the frame only if the assigned
      // session changed underneath it (e.g. the distinct-fill claimed a chat
      // for a previously blank pane).
      const fr = grid.children[i].querySelector('iframe');
      const want = _splitState.sessions[i] || '';
      if (fr && (fr.dataset.splitSid || '') !== want) {
        fr.dataset.splitSid = want;
        fr.src = _splitPaneUrl(_splitState.sessions[i]);
      }
      continue;
    }
    const slot = document.createElement('div');
    slot.className = 'split-slot';
    const bar = document.createElement('div');
    bar.className = 'split-slot-bar';
    const label = document.createElement('span');
    label.className = 'split-slot-label';
    label.textContent = String(i + 1);
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'split-slot-close';
    close.title = t('split_view_close_pane');
    close.textContent = '×';
    close.onclick = () => {
      _splitState.sessions[i] = null;
      _splitSaveState();
      const fr = slot.querySelector('iframe');
      if (fr) { fr.dataset.splitSid = ''; fr.src = _splitPaneUrl(null); }
    };
    bar.appendChild(label);
    bar.appendChild(close);
    const frame = document.createElement('iframe');
    frame.className = 'split-frame';
    frame.setAttribute('title', t('split_view_panes', 1) + ' ' + (i + 1));
    frame.dataset.splitSid = _splitState.sessions[i] || '';
    frame.src = _splitPaneUrl(_splitState.sessions[i]);
    slot.appendChild(bar);
    slot.appendChild(frame);
    grid.appendChild(slot);
  }
}

function toggleSplitView(force) {
  const next = typeof force === 'boolean' ? force : !_splitOpen;
  if (next === _splitOpen) return;
  _splitOpen = next;
  if (_splitOpen) {
    _splitState = _splitLoadState();
    if (!_splitState) {
      const current = (window.S && S.session && S.session.session_id) || null;
      _splitState = { count: 2, sessions: [current, null] };
    } else if (window.S && S.session && S.session.session_id
               && !_splitState.sessions.includes(S.session.session_id)) {
      // Bring the chat the user was just looking at into the first free slot.
      const free = _splitState.sessions.findIndex(s => !s);
      if (free >= 0) _splitState.sessions[free] = S.session.session_id;
    }
    _splitFillDistinct();
    _splitSaveState();
    _splitEnsureOverlay().hidden = false;
    document.documentElement.setAttribute('data-split-open', '1');
    _splitRender();
  } else {
    const overlay = document.getElementById('splitOverlay');
    if (overlay) {
      overlay.hidden = true;
      // Drop the iframes so 8 background apps stop consuming memory and SSE.
      const grid = overlay.querySelector('#splitGrid');
      if (grid) grid.innerHTML = '';
    }
    document.documentElement.removeAttribute('data-split-open');
  }
}
window.toggleSplitView = toggleSplitView;
