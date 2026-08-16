// ── Integrations panel ────────────────────────────────────────────────────
// Per-user third-party connections backed by self-hosted Nango. Data comes
// from /api/integrations/* (see api/integrations.py): a provider catalog
// (providers.yaml merged with configured Nango integrations), the caller's
// own connections (admins see everyone's), connect-session minting, and
// connection deletion. Ownership is enforced server-side via the Nango
// end_user link (end_user.id === 'u-' + slug(email); connection ids are
// Nango-generated uuids); everything this file shows or hides is cosmetic
// on top of that.
//
// Connect flow: POST /api/integrations/connect mints a short-lived (30 min)
// Nango connect session; we open the prebuilt Connect UI in a popup as
// <connect_url>/?session_token=<token>&apiURL=<public Nango server URL>.
// The apiURL param is REQUIRED for self-hosted Nango (the prebuilt UI
// defaults to https://api.nango.dev otherwise). By deployment convention the
// Nango server is served on port 3003 of the same host as the Connect UI
// (port 3009); override with window.HERMES_NANGO_API_URL when that differs.
// While the popup is open we poll the connections list every 3s and stop
// when it closes.
//
// Approvals: each catalog provider carries an "approval" field from the
// approvals registry (api/approvals.py) - "approved" (or absent, for the
// admin-managed globals that predate the registry) means connect straight
// away, "none" means the caller must request access first, and "pending"
// means an admin has not decided yet. Requesting access is the same POST
// /api/integrations/connect call; the server answers 202 with
// {"status":"pending_approval"} instead of minting a connect session.
// CSRF: the global fetch wrapper in index.html injects X-Hermes-CSRF-Token
// on every mutation automatically; this file never sets that header.

let _intgCatalog = null;      // last /api/integrations/catalog payload
let _intgConnections = null;  // last connections array
let _intgRequests = null;     // caller's own approval requests (any status)
let _intgMe = null;           // /api/governance/me payload (for email/admin)
let _intgSearch = '';
let _intgCategory = '';
let _intgSearchTimer = null;
let _intgPollTimer = null;
let _intgPopup = null;

function _intgEsc(s) {
  if (typeof _escHtml === 'function') return _escHtml(s);
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function _intgT(key, fallback) {
  const val = (typeof t === 'function') ? t(key) : key;
  return (val && val !== key) ? val : fallback;
}

// Mirror of api/integrations.py slug_email(): lowercase, non [a-z0-9] -> '-',
// collapsed and trimmed. Used to compute the caller's own end_user id.
function _intgSlugEmail(email) {
  return String(email || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

// Mirror of api/integrations.py end_user_id(): the caller's Nango end_user id.
function _intgMyEndUserId() {
  const slug = _intgSlugEmail(_intgMe && _intgMe.email);
  return 'u-' + (slug || 'admin');
}

// A connection row is the caller's own when its end_user matches; non-admin
// listings are already server-filtered to own connections, so treat rows
// without end_user info as own for non-admins.
function _intgIsOwnConnection(c) {
  const endUserId = String((c && c.end_user && c.end_user.id) || '');
  if (endUserId) return endUserId === _intgMyEndUserId();
  return !_intgIsAdmin(_intgMe);
}

// Cosmetic admin check mirroring api/ownership.py identity_is_admin (server
// enforces regardless): bootstrap admin, auth-disabled single-user mode,
// wildcard/governance:write permission, or an owner/admin role.
function _intgIsAdmin(me) {
  if (!me) return false;
  if (me.is_bootstrap_admin) return true;
  if (String(me.method || '') === 'auth_disabled') return true;
  const perms = Array.isArray(me.permissions) ? me.permissions : [];
  if (perms.includes('*') || perms.includes('governance:write')) return true;
  const roles = Array.isArray(me.roles) ? me.roles : [];
  return roles.includes('owner') || roles.includes('admin');
}

async function _intgFetchMe() {
  if (window.__GOV_ME__) { _intgMe = window.__GOV_ME__; return _intgMe; }
  try {
    _intgMe = await api('/api/governance/me', { redirect401: false, timeoutToast: false, timeoutMs: 15000 });
  } catch (e) {
    _intgMe = null;
  }
  return _intgMe;
}

/**
 * Panel entry point, called by switchPanel (and the header refresh button).
 * Visible to every authenticated user; there is no admin gate here.
 */
async function loadIntegrations() {
  await _intgFetchMe();
  const titleEl = $('intgConnectionsTitle');
  if (titleEl) {
    titleEl.textContent = _intgIsAdmin(_intgMe)
      ? _intgT('integrations_all_connections', 'All connections')
      : _intgT('integrations_my_connections', 'My connections');
  }
  await Promise.all([_intgLoadCatalog(), _intgRefreshConnections(), _intgRefreshRequests()]);
  return true;
}

async function _intgLoadCatalog() {
  const grid = $('intgGrid');
  try {
    _intgCatalog = await api('/api/integrations/catalog', { redirect401: false });
  } catch (e) {
    _intgCatalog = null;
    if (grid) grid.innerHTML = '<div class="intg-error">' + _intgEsc((e && e.message) || 'request failed') + '</div>';
    return;
  }
  _intgRenderNotice();
  _intgRenderCategoryChips();
  _intgRenderGrid();
}

async function _intgRefreshConnections() {
  const el = $('intgConnections');
  let data;
  try {
    data = await api('/api/integrations/connections', { redirect401: false, timeoutToast: false });
  } catch (e) {
    if (el && _intgConnections === null) {
      el.innerHTML = '<div class="intg-error">' + _intgEsc((e && e.message) || 'request failed') + '</div>';
    }
    return;
  }
  _intgConnections = (data && Array.isArray(data.connections)) ? data.connections : [];
  _intgRenderConnections();
  _intgRenderGrid(); // "Connected" chips depend on the connection list
}

// The caller's own approval requests, scoped server-side to their identity.
// Not admin-gated; a missing endpoint (older backend) just leaves the line
// hidden, so the panel keeps working exactly as before.
async function _intgRefreshRequests() {
  let data;
  try {
    data = await api('/api/governance/approvals/mine?kind=integration', {
      redirect401: false, timeoutToast: false, timeoutMs: 15000,
    });
  } catch (e) {
    if (_intgRequests === null) _intgRequests = [];
    _intgRenderRequests();
    return;
  }
  _intgRequests = (data && Array.isArray(data.requests)) ? data.requests : [];
  _intgRenderRequests();
  _intgRenderGrid(); // pending chips also come from the request list
}

// ── Rendering ─────────────────────────────────────────────────────────────

function _intgRenderNotice() {
  const el = $('intgNotice');
  if (!el) return;
  const nango = (_intgCatalog && _intgCatalog.nango) || { available: true };
  if (nango.available === false) {
    el.style.display = '';
    el.innerHTML = '<div class="intg-banner">'
      + _intgEsc(_intgT('integrations_nango_down', 'Nango is unreachable; showing the catalog without connect state.'))
      + (nango.error ? ' <span class="intg-muted">(' + _intgEsc(nango.error) + ')</span>' : '')
      + '</div>';
  } else {
    el.style.display = 'none';
    el.innerHTML = '';
  }
}

// Approval state of a catalog provider. A provider without the field is an
// admin-managed global that predates the registry: connect straight away.
function _intgApprovalOf(p) {
  const value = String((p && p.approval) || '').trim().toLowerCase();
  if (value === 'pending' || value === 'none' || value === 'rejected') return value;
  return 'approved';
}

// Provider keys with a pending request of the caller's own, from
// /api/governance/approvals/mine (authoritative even when the catalog is
// cached or does not carry the approval field yet).
function _intgPendingRequestKeys() {
  const keys = new Set();
  (_intgRequests || []).forEach(r => {
    if (String((r && r.status) || '') !== 'pending') return;
    const key = String((r && r.key) || '');
    if (key) keys.add(key);
  });
  return keys;
}

function _intgRenderRequests() {
  const el = $('intgRequests');
  if (!el) return;
  const pending = (_intgRequests || []).filter(r => String((r && r.status) || '') === 'pending');
  if (!pending.length) {
    el.style.display = 'none';
    el.innerHTML = '';
    return;
  }
  const chips = pending.map(r => {
    const key = String(r.key || '');
    // _intgProviderName echoes the key back when the catalog has no match.
    const known = _intgProviderName(key);
    const label = (known && known !== key) ? known : (String(r.label || '') || key);
    return '<span class="intg-badge intg-badge-pending">' + _intgEsc(label) + '</span>';
  }).join(' ');
  el.style.display = '';
  el.innerHTML = '<div class="intg-requests">'
    + '<span class="intg-muted">' + _intgEsc(_intgT('integrations_my_requests', 'My requests')) + ':</span> '
    + chips
    + '</div>';
}

function _intgOwnConnectionKeys() {
  const keys = new Set();
  (_intgConnections || []).forEach(c => {
    if (_intgIsOwnConnection(c)) keys.add(String(c.provider_config_key || ''));
  });
  return keys;
}

// Keys with ANY visible connection, for the "Connected" badge. The server
// already scopes the list to the caller's own connections for non-admins;
// for admins this also covers org-level rows without an end_user link
// (seeded synthwave-* connections), which _intgIsOwnConnection excludes.
function _intgConnectedKeys() {
  const keys = new Set();
  (_intgConnections || []).forEach(c => {
    const k = String((c && c.provider_config_key) || '');
    if (k) keys.add(k);
  });
  return keys;
}

function _intgFmtDate(value) {
  if (!value) return '';
  const d = new Date(value);
  if (isNaN(d.getTime())) return String(value);
  try {
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  } catch (e) {
    return d.toLocaleString();
  }
}

// Owner label for the admin view, from the row's end_user link (email when
// Nango has it, else the u-<slug> id without its "u-" prefix).
function _intgOwnerOf(c) {
  const endUser = (c && c.end_user) || null;
  if (!endUser) return '';
  const email = String(endUser.email || '');
  if (email) return email;
  const id = String(endUser.id || '');
  return id.indexOf('u-') === 0 ? id.slice(2) : id;
}

function _intgProviderName(key) {
  const providers = (_intgCatalog && _intgCatalog.providers) || [];
  for (const p of providers) {
    if (p.unique_key === key || p.key === key) return p.display_name || key;
  }
  return key;
}

function _intgRenderConnections() {
  const el = $('intgConnections');
  if (!el) return;
  const rows = _intgConnections || [];
  const isAdmin = _intgIsAdmin(_intgMe);
  if (!rows.length) {
    el.innerHTML = '<div class="intg-muted">' + _intgEsc(_intgT('integrations_no_connections', 'No connections yet. Connect a service from the catalog below.')) + '</div>';
    return;
  }
  const ownerTh = isAdmin ? '<th>' + _intgEsc(_intgT('integrations_col_owner', 'Owner')) + '</th>' : '';
  const body = rows.map(c => {
    const cid = String(c.connection_id || '');
    const key = String(c.provider_config_key || '');
    const errors = Array.isArray(c.errors) ? c.errors : [];
    const status = errors.length
      ? '<span class="intg-badge intg-badge-error">' + errors.length + ' ' + _intgEsc(_intgT('integrations_errors', 'error(s)')) + '</span>'
      : '<span class="intg-badge intg-badge-ok">' + _intgEsc(_intgT('integrations_healthy', 'Healthy')) + '</span>';
    let ownerTd = '';
    if (isAdmin) {
      const owner = _intgOwnerOf(c);
      const label = _intgIsOwnConnection(c) ? _intgT('integrations_owner_you', 'you') : (owner || '?');
      ownerTd = '<td class="intg-nowrap">' + _intgEsc(label) + '</td>';
    }
    const canDelete = isAdmin || _intgIsOwnConnection(c);
    const action = canDelete
      ? '<button type="button" class="intg-btn danger" data-intg-action="disconnect" data-cid="' + _intgEsc(cid) + '" data-key="' + _intgEsc(key) + '">' + _intgEsc(_intgT('integrations_disconnect', 'Disconnect')) + '</button>'
      : '';
    return '<tr>'
      + '<td class="intg-nowrap">' + _intgEsc(_intgProviderName(key)) + '</td>'
      + '<td class="intg-path">' + _intgEsc(cid) + '</td>'
      + ownerTd
      + '<td class="intg-nowrap">' + _intgEsc(_intgFmtDate(c.created)) + '</td>'
      + '<td>' + status + '</td>'
      + '<td class="intg-row-actions">' + action + '</td>'
      + '</tr>';
  }).join('');
  el.innerHTML = '<div class="intg-table-wrap"><table class="intg-table"><thead><tr>'
    + '<th>' + _intgEsc(_intgT('integrations_col_provider', 'Provider')) + '</th>'
    + '<th>' + _intgEsc(_intgT('integrations_col_connection', 'Connection')) + '</th>'
    + ownerTh
    + '<th>' + _intgEsc(_intgT('integrations_col_created', 'Created')) + '</th>'
    + '<th>' + _intgEsc(_intgT('integrations_col_status', 'Status')) + '</th>'
    + '<th></th>'
    + '</tr></thead><tbody>' + body + '</tbody></table></div>';
}

function _intgCategories() {
  const providers = (_intgCatalog && _intgCatalog.providers) || [];
  const set = new Set();
  providers.forEach(p => (p.categories || []).forEach(c => set.add(String(c))));
  return Array.from(set).sort((a, b) => a.localeCompare(b));
}

function _intgRenderCategoryChips() {
  const el = $('intgCategoryChips');
  if (!el) return;
  const cats = _intgCategories();
  if (_intgCategory && cats.indexOf(_intgCategory) === -1) _intgCategory = '';
  const chip = (value, label) => '<button type="button" class="intg-chip' + (_intgCategory === value ? ' active' : '')
    + '" data-intg-action="category" data-cat="' + _intgEsc(value) + '">' + _intgEsc(label) + '</button>';
  el.innerHTML = chip('', _intgT('integrations_all_categories', 'All'))
    + cats.map(c => chip(c, c)).join('');
}

function _intgAuthModeLabel(mode) {
  const m = String(mode || '').toUpperCase();
  if (!m || m === 'NONE') return '';
  if (m.indexOf('OAUTH') === 0) return 'OAuth';
  if (m === 'API_KEY') return _intgT('integrations_auth_api_key', 'API key');
  if (m === 'BASIC') return 'Basic';
  return m.charAt(0) + m.slice(1).toLowerCase().replace(/_/g, ' ');
}

function _intgFilteredProviders() {
  const providers = (_intgCatalog && _intgCatalog.providers) || [];
  const q = _intgSearch.trim().toLowerCase();
  const cat = _intgCategory;
  const out = providers.filter(p => {
    if (cat && (p.categories || []).indexOf(cat) === -1) return false;
    if (!q) return true;
    if (String(p.display_name || '').toLowerCase().includes(q)) return true;
    if (String(p.key || '').toLowerCase().includes(q)) return true;
    return (p.categories || []).some(c => String(c).toLowerCase().includes(q));
  });
  // Configured providers first; within each group keep the backend's
  // alphabetical display_name order (Array.prototype.sort is stable).
  return out.slice().sort((a, b) => (b.configured ? 1 : 0) - (a.configured ? 1 : 0));
}

function _intgRenderGrid() {
  const grid = $('intgGrid');
  if (!grid || !_intgCatalog) return;
  const providers = _intgFilteredProviders();
  const connectedKeys = _intgConnectedKeys();
  const pendingKeys = _intgPendingRequestKeys();
  const isAdminUser = _intgIsAdmin(_intgMe);
  const nangoUp = !((_intgCatalog.nango || {}).available === false);
  if (!providers.length) {
    grid.innerHTML = '<div class="intg-muted">' + _intgEsc(_intgT('integrations_no_results', 'No providers match your search.')) + '</div>';
    return;
  }
  grid.innerHTML = providers.map(p => {
    const authLabel = _intgAuthModeLabel(p.auth_mode);
    const cats = (p.categories || []).slice(0, 3);
    const connected = p.configured && p.unique_key && connectedKeys.has(p.unique_key);
    let approval = _intgApprovalOf(p);
    if ((p.unique_key && pendingKeys.has(p.unique_key)) || pendingKeys.has(p.key)) approval = 'pending';
    const badges = (authLabel ? '<span class="intg-badge">' + _intgEsc(authLabel) + '</span>' : '')
      + cats.map(c => '<span class="intg-badge intg-badge-cat">' + _intgEsc(c) + '</span>').join('')
      + (connected ? '<span class="intg-badge intg-badge-ok">' + _intgEsc(_intgT('integrations_connected', 'Connected')) + '</span>' : '')
      + (approval === 'pending' ? '<span class="intg-badge intg-badge-pending">' + _intgEsc(_intgT('integrations_awaiting_approval', 'Waiting for admin approval')) + '</span>' : '');
    let action;
    if (p.configured && p.unique_key && approval === 'pending') {
      // Requested, no admin decision yet: nothing to do from here.
      action = '<button type="button" class="intg-btn" disabled>'
        + _intgEsc(_intgT('integrations_waiting_approval', 'Waiting for approval')) + '</button>';
    } else if (p.configured && p.unique_key) {
      // "none" means the caller has to ask first; same endpoint either way.
      const label = approval === 'none'
        ? _intgT('integrations_request_access', 'Request access')
        : _intgT('integrations_connect', 'Connect');
      action = '<button type="button" class="intg-btn primary" data-intg-action="connect" data-key="' + _intgEsc(p.unique_key) + '"'
        + (nangoUp ? '' : ' disabled')
        + '>' + _intgEsc(label) + '</button>';
    } else if (isAdminUser) {
      // An admin does not request: enabling creates the Nango integration
      // directly (and implicitly approves it for everyone).
      action = '<button type="button" class="intg-btn primary" data-intg-action="enable" data-key="' + _intgEsc(p.key) + '">'
        + _intgEsc(_intgT('integrations_enable', 'Enable')) + '</button>';
    } else if (approval === 'pending') {
      // Requested but no Nango integration yet: the admin still has to decide.
      action = '<button type="button" class="intg-btn" disabled>'
        + _intgEsc(_intgT('integrations_waiting_approval', 'Waiting for approval')) + '</button>';
    } else if (approval === 'approved') {
      // Approved, but the admin has not created the Nango integration yet.
      action = '<span class="intg-muted">' + _intgEsc(_intgT('integrations_approved_setup', 'Approved. An admin is setting it up.')) + '</span>';
    } else {
      // Any provider can be requested: /api/integrations/request queues an
      // admin approval, after which the admin configures it in Nango.
      action = '<button type="button" class="intg-btn" data-intg-action="request" data-key="' + _intgEsc(p.key) + '">'
        + _intgEsc(_intgT('integrations_request_access', 'Request access')) + '</button>';
    }
    const docs = (!p.configured && p.docs)
      ? '<a class="intg-docs-link" href="' + _intgEsc(p.docs) + '" target="_blank" rel="noopener noreferrer">' + _intgEsc(_intgT('integrations_docs', 'Docs')) + '</a>'
      : '';
    // Same-origin logo proxied by our backend; hide the img on a 404 so
    // providers without a logo fall back to the plain text card.
    const logo = p.logo
      ? '<img class="intg-card-logo" src="' + _intgEsc(p.logo) + '" alt="" loading="lazy" onerror="this.remove()">'
      : '';
    return '<div class="intg-card' + (p.configured ? ' configured' : '') + '">'
      + '<div class="intg-card-head">' + logo
      + '<div class="intg-card-name">' + _intgEsc(p.display_name || p.key) + '</div></div>'
      + '<div class="intg-card-key">' + _intgEsc(p.key) + '</div>'
      + '<div class="intg-card-badges">' + badges + '</div>'
      + '<div class="intg-card-actions">' + action + docs + '</div>'
      + '</div>';
  }).join('');
}

// ── Search / filter handlers ──────────────────────────────────────────────

function _intgOnSearchInput(value) {
  _intgSearch = String(value || '');
  if (_intgSearchTimer) clearTimeout(_intgSearchTimer);
  _intgSearchTimer = setTimeout(() => { _intgSearchTimer = null; _intgRenderGrid(); }, 120);
}

// ── Connect flow ──────────────────────────────────────────────────────────

// Public Nango server URL for the Connect UI's apiURL parameter. Defaults to
// the connect_url host with the server port (3003, per the deployment's
// nango.env); override with window.HERMES_NANGO_API_URL when they differ.
function _intgApiUrlFor(connectUrl) {
  if (window.HERMES_NANGO_API_URL) return String(window.HERMES_NANGO_API_URL);
  try {
    const u = new URL(connectUrl);
    u.port = '3003';
    u.pathname = '';
    u.search = '';
    u.hash = '';
    return u.origin;
  } catch (e) {
    return '';
  }
}

// Flip a provider to "pending" locally so the card updates immediately,
// before the requests refresh (and even if that call fails).
function _intgMarkPending(providerConfigKey) {
  const key = String(providerConfigKey || '');
  const providers = (_intgCatalog && _intgCatalog.providers) || [];
  providers.forEach(p => {
    if (p && (p.unique_key === key || p.key === key)) p.approval = 'pending';
  });
  _intgRenderGrid();
}

// Admin path: create the Nango integration for a provider so it becomes
// connectable for everyone (POST /api/integrations/enable, admin-gated).
async function _intgEnable(providerKey) {
  let data;
  try {
    data = await api('/api/integrations/enable', {
      method: 'POST',
      body: JSON.stringify({ provider_config_key: providerKey }),
      redirect401: false,
    });
  } catch (e) {
    if (typeof showToast === 'function') showToast((e && e.message) || 'enable failed', 5000, 'error');
    return;
  }
  if (typeof showToast === 'function') {
    if (data && data.needs_credentials) {
      showToast(_intgT('integrations_enabled_needs_credentials',
        'Enabled. Add the OAuth client credentials in the Nango dashboard before connecting.'), 8000);
    } else {
      showToast(_intgT('integrations_enabled', 'Enabled. It can be connected now.'), 4000);
    }
  }
  loadIntegrations();
}

// Ask for a provider that has no Nango integration yet. No popup involved:
// this only queues an admin approval (POST /api/integrations/request).
async function _intgRequestAccess(providerKey) {
  let data;
  try {
    data = await api('/api/integrations/request', {
      method: 'POST',
      body: JSON.stringify({ provider_config_key: providerKey }),
      redirect401: false,
    });
  } catch (e) {
    if (typeof showToast === 'function') showToast((e && e.message) || 'request failed', 5000, 'error');
    return;
  }
  const status = String((data && data.status) || '');
  if (status === 'approved') {
    // Race: an admin already approved it. The message explains what to do.
    if (typeof showToast === 'function') showToast(String(data.message || 'Approved.'), 5000);
    loadIntegrations();
    return;
  }
  if (typeof showToast === 'function') {
    showToast(_intgT('integrations_access_requested', 'Access requested. An admin has to approve it.'), 5000);
  }
  _intgMarkPending(providerKey);
  _intgRefreshRequests();
}

async function _intgConnect(providerConfigKey) {
  // Open the popup SYNCHRONOUSLY, inside the click's user-gesture stack, and
  // navigate it once the session token arrives. Opening it after the await
  // instead is what browsers block by default: the window.open no longer
  // counts as user-initiated, and the click silently did nothing.
  let popup = null;
  try {
    popup = window.open('about:blank', 'hermesNangoConnect', 'popup=yes,width=480,height=720');
  } catch (_) { popup = null; }
  if (popup) {
    try {
      popup.document.write(
        '<!doctype html><meta charset="utf-8"><title>Connecting…</title>' +
        '<body style="font:14px system-ui;padding:24px;color:#333">Preparing the secure connect window…</body>'
      );
    } catch (_) { /* cross-origin write can fail harmlessly */ }
  }
  const closePopup = () => { try { if (popup && !popup.closed) popup.close(); } catch (_) {} };

  let data;
  try {
    // Session tokens expire after 30 minutes (Nango hardcoded); mint a fresh
    // session per connect attempt.
    data = await api('/api/integrations/connect', {
      method: 'POST',
      body: JSON.stringify({ provider_config_key: providerConfigKey }),
      redirect401: false,
    });
  } catch (e) {
    closePopup();
    if (typeof showToast === 'function') showToast((e && e.message) || 'connect failed', 5000, 'error');
    return;
  }
  // 202: the request was queued for an admin instead of minting a session.
  if (data && String(data.status || '') === 'pending_approval') {
    closePopup();
    if (typeof showToast === 'function') {
      showToast(_intgT('integrations_access_requested', 'Access requested. An admin has to approve it.'), 5000);
    }
    _intgMarkPending(providerConfigKey);
    await _intgRefreshRequests();
    return;
  }
  const base = String((data && data.connect_url) || '').replace(/\/+$/, '');
  const token = String((data && data.token) || '');
  if (!base || !token) {
    closePopup();
    if (typeof showToast === 'function') showToast(_intgT('integrations_connect_failed', 'Connect session could not be created.'), 5000, 'error');
    return;
  }
  const apiUrl = _intgApiUrlFor(base);
  let url = base + '/?session_token=' + encodeURIComponent(token);
  if (apiUrl) url += '&apiURL=' + encodeURIComponent(apiUrl);
  if (!popup || popup.closed) {
    // Blocked, or the user closed the placeholder. Try once more now that we
    // have the URL, and fall back to telling them rather than failing silently.
    try { popup = window.open(url, 'hermesNangoConnect', 'popup=yes,width=480,height=720'); } catch (_) { popup = null; }
    if (!popup) {
      if (typeof showToast === 'function') showToast(_intgT('integrations_popup_blocked', 'Popup blocked: allow popups for this site and try again.'), 6000, 'error');
      return;
    }
  } else {
    try {
      popup.location.replace(url);
    } catch (_) {
      try { popup.location.href = url; } catch (_) { closePopup(); return; }
    }
    try { popup.focus(); } catch (_) {}
  }
  _intgPopup = popup;
  _intgStartPolling();
}

function _intgStartPolling() {
  _intgStopPolling();
  _intgPollTimer = setInterval(async () => {
    const popup = _intgPopup;
    if (!popup || popup.closed) {
      _intgStopPolling();
      _intgPopup = null;
      await _intgRefreshConnections();
      return;
    }
    await _intgRefreshConnections();
  }, 3000);
}

function _intgStopPolling() {
  if (_intgPollTimer) {
    clearInterval(_intgPollTimer);
    _intgPollTimer = null;
  }
}

// ── Disconnect flow ───────────────────────────────────────────────────────

async function _intgDisconnect(connectionId, providerConfigKey) {
  let ok = true;
  if (typeof showConfirmDialog === 'function') {
    ok = await showConfirmDialog({
      title: _intgT('integrations_disconnect_title', 'Disconnect service'),
      message: _intgT('integrations_disconnect_message', 'Remove this connection? Anything using it stops working until you reconnect.')
        + '\n\n' + connectionId,
      confirmLabel: _intgT('integrations_disconnect', 'Disconnect'),
      danger: true,
      focusCancel: true,
    });
  } else {
    ok = window.confirm(_intgT('integrations_disconnect_message', 'Remove this connection?'));
  }
  if (!ok) return;
  try {
    await api('/api/integrations/connections/' + encodeURIComponent(connectionId)
      + '?provider_config_key=' + encodeURIComponent(providerConfigKey), {
      method: 'DELETE',
      redirect401: false,
    });
  } catch (e) {
    if (typeof showToast === 'function') showToast((e && e.message) || 'disconnect failed', 5000, 'error');
    return;
  }
  if (typeof showToast === 'function') showToast(_intgT('integrations_disconnected', 'Connection removed.'), 3000);
  await _intgRefreshConnections();
}

// ── Boot wiring ───────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  // Event delegation for JS-rendered buttons (connect / disconnect / chips):
  // connection ids and provider keys live in data attributes, never inline JS.
  const main = document.getElementById('mainIntegrations');
  if (main) {
    main.addEventListener('click', (ev) => {
      const btn = ev.target && ev.target.closest ? ev.target.closest('[data-intg-action]') : null;
      if (!btn || btn.disabled) return;
      const action = btn.getAttribute('data-intg-action');
      if (action === 'connect') {
        _intgConnect(btn.getAttribute('data-key') || '');
      } else if (action === 'request') {
        _intgRequestAccess(btn.getAttribute('data-key') || '');
      } else if (action === 'enable') {
        _intgEnable(btn.getAttribute('data-key') || '');
      } else if (action === 'disconnect') {
        _intgDisconnect(btn.getAttribute('data-cid') || '', btn.getAttribute('data-key') || '');
      } else if (action === 'category') {
        _intgCategory = btn.getAttribute('data-cat') || '';
        _intgRenderCategoryChips();
        _intgRenderGrid();
      }
    });
  }
  const search = document.getElementById('intgSearch');
  if (search) search.addEventListener('input', () => _intgOnSearchInput(search.value));
});

// Deep link: https://<host>/#integrations opens this panel (used by the
// OpenWebUI banner). Runs after boot; harmless when the hash is absent.
window.addEventListener('load', () => {
  if ((location.hash || '').replace('#', '') === 'integrations' &&
      typeof switchPanel === 'function') {
    switchPanel('integrations');
  }
});
