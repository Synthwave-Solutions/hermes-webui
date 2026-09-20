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

function _intgSafeDocsUrl(value) {
  const raw = String(value || '').trim();
  try {
    const url = new URL(raw);
    if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password) return '';
    return raw;
  } catch (_) { return ''; }
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
  await Promise.all([_intgLoadCatalog(), _intgRefreshConnections(), _intgRefreshRequests(), chLoadChannels(), chLoadMine()]);
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
      + (p.configured && p.needs_setup ? '<span class="intg-badge intg-badge-warn">' + _intgEsc(_intgT('integrations_setup_needed', 'Setup needed')) + '</span>' : '')
      + (approval === 'pending' ? '<span class="intg-badge intg-badge-pending">' + _intgEsc(_intgT('integrations_awaiting_approval', 'Waiting for admin approval')) + '</span>' : '');
    let action;
    if (p.configured && p.unique_key && p.needs_setup) {
      // The Nango row exists but has no registered OAuth client: connecting
      // would end on Nango's "Connection failed" page. Admins finish the setup
      // here; everyone else sees that it is not ready yet.
      if (isAdminUser && p.setup_kind === 'dynamic') {
        action = '<button type="button" class="intg-btn primary" data-intg-action="repair" data-key="' + _intgEsc(p.unique_key) + '">'
          + _intgEsc(_intgT('integrations_register_client', 'Register with provider')) + '</button>';
      } else if (isAdminUser && (p.setup_kind === 'static' || p.setup_kind === 'oauth')) {
        action = '<button type="button" class="intg-btn primary" data-intg-action="repair" data-key="' + _intgEsc(p.unique_key) + '">'
          + _intgEsc(_intgT('integrations_add_app_credentials', 'Add app credentials')) + '</button>';
      } else {
        action = '<span class="intg-muted" title="' + _intgEsc(p.setup_message || '') + '">' + _intgEsc(_intgT('integrations_setup_pending', 'Not ready yet: an admin has to finish the setup.')) + '</span>';
      }
    } else if (p.configured && p.unique_key && approval === 'pending') {
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
    } else if (isAdminUser && p.setup_required) {
      action = '<span class="intg-muted">' + _intgEsc(_intgT('integrations_setup_needed', 'Setup needed')) + '</span>';
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
    const setupGuide = isAdminUser && p.auth_mode === 'MCP_OAUTH2' && _intgSafeDocsUrl(p.setup_guide_url);
    const docsUrl = setupGuide || (!p.configured && _intgSafeDocsUrl(p.docs));
    const docs = docsUrl
      ? '<a class="intg-docs-link" href="' + _intgEsc(docsUrl) + '" target="_blank" rel="noopener noreferrer">' + _intgEsc(setupGuide ? _intgT('integrations_setup_guide', 'Setup guide') : _intgT('integrations_docs', 'Docs')) + '</a>'
      : '';
    // Same-origin logo proxied by our backend; hide the img on a 404 so
    // providers without a logo fall back to the plain text card.
    const logo = p.logo
      ? '<img class="intg-card-logo" src="' + _intgEsc(p.logo) + '" alt="" loading="lazy" onerror="this.remove()">'
      : '';
    return '<div class="intg-card' + (p.configured ? ' configured' : '') + '">'
      + '<div class="intg-card-head">' + logo
      + '<div class="intg-card-name">' + _intgEsc(p.display_name || p.key)
      + (p.unique_key && p.unique_key !== p.key ? ' · ' + _intgEsc(p.unique_key) : '') + '</div></div>'
      + '<div class="intg-card-key">' + _intgEsc(p.key) + '</div>'
      + '<div class="intg-card-badges">' + badges + '</div>'
      + (isAdminUser && p.setup_required ? '<div class="intg-muted intg-setup-message">' + _intgEsc(p.setup_message || 'Finish OAuth setup in Nango, then refresh SynthPulse.') + '</div>' : '')
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
async function _intgEnablePayload(providerKey) {
  const catalog = await api('/api/integrations/catalog', { redirect401: false });
  const provider = (catalog.providers || []).find(p => p.key === providerKey);
  if (!provider) throw new Error('Provider is no longer available. Refresh the catalog.');
  // Shared by the Connections and Governance Enable actions. Keep the
  // provider-managed MCP setup explanation visible before any POST or dialog.
  if (provider.setup_required) throw new Error(provider.setup_message || 'Finish OAuth setup in Nango, then refresh SynthPulse.');
  const payload = { provider_config_key: providerKey };
  const fields = provider.configured && provider.unique_key === providerKey ? [] : (provider.credential_fields || []);
  if (!fields.length) return payload;
  const credentials = await _intgCredentialDialog(provider, fields, { scopes: provider.setup_kind === 'static' || provider.setup_kind === 'oauth' });
  if (credentials === null) return null;
  payload.credentials = credentials;
  return payload;
}

function _intgCredentialDialog(provider, fields, opts) {
  opts = opts || {};
  return new Promise(resolve => {
    const dialog = document.createElement('dialog');
    dialog.className = 'app-dialog';
    dialog.style.cssText = 'max-width:480px;width:calc(100% - 32px);max-height:90vh;overflow:auto;margin:auto';
    const form = document.createElement('form');
    const title = document.createElement('h3');
    title.className = 'app-dialog-title';
    title.textContent = provider.display_name;
    form.appendChild(title);
    const explanation = document.createElement('p');
    explanation.className = 'app-dialog-desc';
    explanation.textContent = _intgT('integrations_credentials_prompt', 'Enter the app credentials from this provider to enable sign-in.');
    form.appendChild(explanation);
    if (provider.callback_url) {
      // The one value the admin has to copy into the provider's app settings.
      const hint = document.createElement('p');
      hint.className = 'app-dialog-desc intg-callback-hint';
      hint.textContent = _intgT('integrations_callback_hint', 'Redirect URL to register at the provider:') + ' ';
      const code = document.createElement('code');
      code.textContent = provider.callback_url;
      hint.appendChild(code);
      form.appendChild(hint);
      if (provider.setup_guide_url || provider.docs) {
        const guide = document.createElement('a');
        guide.href = provider.setup_guide_url || provider.docs; guide.target = '_blank'; guide.rel = 'noopener noreferrer';
        guide.className = 'intg-docs-link';
        guide.textContent = _intgT('integrations_setup_guide', 'Setup guide');
        form.appendChild(guide);
      }
    }
    const inputs = {};
    for (const field of fields) {
      const label = document.createElement('label');
      label.textContent = field.replace(/_/g, ' ');
      label.style.cssText = 'display:block;margin:12px 0';
      const input = document.createElement(field === 'private_key' ? 'textarea' : 'input');
      if (field !== 'private_key') input.type = field.includes('secret') ? 'password' : 'text';
      else input.rows = 6;
      input.className = 'app-dialog-input';
      input.required = true;
      input.autocomplete = 'off';
      input.spellcheck = false;
      input.style.cssText = 'display:block;width:100%;box-sizing:border-box';
      label.appendChild(input);
      form.appendChild(label);
      inputs[field] = input;
    }
    let scopesInput = null;
    if (opts.scopes) {
      const label = document.createElement('label');
      label.textContent = _intgT('integrations_scopes_label', 'scopes (comma separated, optional)');
      label.style.cssText = 'display:block;margin:12px 0';
      scopesInput = document.createElement('input');
      scopesInput.type = 'text'; scopesInput.className = 'app-dialog-input'; scopesInput.autocomplete = 'off'; scopesInput.spellcheck = false;
      scopesInput.value = provider.default_scopes || '';
      scopesInput.style.cssText = 'display:block;width:100%;box-sizing:border-box';
      label.appendChild(scopesInput);
      form.appendChild(label);
    }
    const finish = result => {
      Object.values(inputs).forEach(input => { input.value = ''; });
      dialog.close();
      dialog.remove();
      resolve(result);
    };
    const cancel = document.createElement('button');
    cancel.type = 'button'; cancel.className = 'app-dialog-btn';
    cancel.textContent = _intgT('cancel', 'Cancel');
    cancel.onclick = () => finish(null);
    const submit = document.createElement('button');
    submit.type = 'submit'; submit.className = 'app-dialog-btn confirm';
    submit.textContent = opts.submitLabel || _intgT('integrations_enable', 'Enable');
    const actions = document.createElement('div');
    actions.className = 'app-dialog-actions';
    actions.append(cancel, submit);
    form.appendChild(actions);
    form.onsubmit = event => {
      event.preventDefault();
      const values = Object.fromEntries(fields.map(field => [field, inputs[field].value.trim()]));
      if (Object.values(values).some(value => !value)) return;
      if (scopesInput) values.scopes = scopesInput.value.trim();
      finish(values);
    };
    dialog.addEventListener('cancel', event => { event.preventDefault(); finish(null); });
    dialog.appendChild(form); document.body.appendChild(dialog); dialog.showModal();
    inputs[fields[0]].focus();
  });
}

async function _intgEnable(providerKey) {
  let data;
  try {
    const payload = await _intgEnablePayload(providerKey);
    if (payload === null) return;
    data = await api('/api/integrations/enable', {
      method: 'POST',
      body: JSON.stringify(payload),
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

// Finish the OAuth client setup of an integration that exists in Nango
// without one (admin-gated POST /api/integrations/repair). Dynamic MCP
// providers register in one click; static MCP and OAuth need the app
// credentials the admin registered at the provider.
async function _intgRepair(uniqueKey) {
  let data;
  try {
    const catalog = await api('/api/integrations/catalog', { redirect401: false });
    const provider = (catalog.providers || []).find(p => p.unique_key === uniqueKey) || (catalog.providers || []).find(p => p.key === uniqueKey);
    if (!provider) throw new Error('Provider is no longer available. Refresh the catalog.');
    const payload = { provider_config_key: uniqueKey };
    if (provider.setup_kind === 'static' || provider.setup_kind === 'oauth') {
      const credentials = await _intgCredentialDialog(provider, ['client_id', 'client_secret'], { scopes: true, submitLabel: _intgT('integrations_save_credentials', 'Save and enable') });
      if (credentials === null) return;
      payload.credentials = credentials;
    }
    data = await api('/api/integrations/repair', { method: 'POST', body: JSON.stringify(payload), redirect401: false });
  } catch (e) {
    if (typeof showToast === 'function') showToast((e && e.message) || 'setup failed', 7000, 'error');
    return;
  }
  if (typeof showToast === 'function') {
    showToast(data && data.needs_setup
      ? _intgT('integrations_repair_incomplete', 'Saved, but the setup is still incomplete.')
      : _intgT('integrations_repaired', 'Set up. It can be connected now.'), 5000);
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
      } else if (action === 'repair') {
        _intgRepair(btn.getAttribute('data-key') || '');
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


// ── Messaging channels: Telegram, WhatsApp, Slack, Teams, Discord, Google Chat ──
// Admin-only section at the top of Connections. Backed by api/gateway_channels.py.
// Tokens go to the profile .env and are never echoed; the gateway picks them up
// after a restart. Each platform user is mapped to a colleague so governance
// follows them (gateway hook) and they see their own messaging sessions here.
let _chState = null;
const _CH_PLATFORM_ICON = { telegram: 'zap', whatsapp_cloud: 'message-square', slack: 'hash', teams: 'globe', discord: 'bot', google_chat: 'message-square' };

async function chLoadChannels() {
  const root = $('intgChannels');
  if (!root) return;
  if (!_intgIsAdmin(_intgMe)) { root.style.display = 'none'; return; }
  root.style.display = '';
  try {
    _chState = await api('/api/gateway/channels', { redirect401: false, timeoutToast: false });
  } catch (e) {
    _chState = null;
    const grid = $('intgChannelGrid');
    if (grid) grid.innerHTML = '<div class="intg-error">' + _intgEsc((e && e.message) || _intgT('channels_failed', 'Channel action failed.')) + '</div>';
    return;
  }
  chRenderGrid(); chRenderPending(); chRenderPeople();
}

function _chLabel(key) {
  const p = (_chState && _chState.platforms || []).find(x => x.key === key);
  return p ? p.label : key;
}

function chRenderGrid() {
  const grid = $('intgChannelGrid');
  if (!grid || !_chState) return;
  grid.innerHTML = (_chState.platforms || []).map(p => {
    const badges = [];
    badges.push(p.configured
      ? '<span class="intg-badge intg-badge-ok">' + _intgT('channels_configured', 'Connected') + '</span>'
      : '<span class="intg-badge">' + _intgT('channels_not_configured', 'Not connected') + '</span>');
    if (p.configured && p.allow_all) badges.push('<span class="intg-badge intg-badge-warn">' + _intgT('channels_allow_all_short', 'open to all') + '</span>');
    if (p.pending_count) badges.push('<span class="intg-badge intg-badge-pending">' + p.pending_count + ' ' + _intgT('channels_pairing_short', 'pairing') + '</span>');
    let meta = p.configured ? '<div class="ch-card-meta">' + _intgT('channels_people_count', '{n} people mapped').replace('{n}', String(p.mapped_count || 0)) + (p.approved_count ? ' · ' + p.approved_count + ' approved' : '') + '</div>' : '';
    if (p.public) {
      if (p.public.state === 'published') {
        meta += '<div class="ch-card-meta ch-public"><span>' + _intgEsc(p.public.label) + ':</span> <code>' + _intgEsc(p.public.url) + '</code> <button type="button" class="sm-btn ch-copy" onclick="chCopy(this)" data-copy="' + _intgEsc(p.public.url) + '">' + _intgT('copy', 'Copy') + '</button></div>';
      } else if (p.public.state === 'unpublished') {
        meta += '<div class="ch-card-meta ch-public">' + _intgT('channels_hook_unpublished', 'Webhook not public yet.') + ' <button type="button" class="sm-btn" onclick="chPublish(\'' + _intgEsc(p.key) + '\')">' + _intgT('channels_publish', 'Publish via Funnel') + '</button></div>';
      } else {
        meta += '<div class="ch-card-meta ch-public">' + _intgT('channels_hook_unavailable', 'Public webhook URL is set by the deploy bootstrap on this host.') + '</div>';
      }
    }
    const icon = (typeof li === 'function') ? li(_CH_PLATFORM_ICON[p.key] || 'message-circle', 16) : '';
    return '<div class="intg-card' + (p.configured ? ' configured' : '') + '" data-channel="' + _intgEsc(p.key) + '">'
      + '<div class="intg-card-head">' + icon + '<div class="intg-card-name">' + _intgEsc(p.label) + '</div></div>'
      + '<div class="ch-card-status">' + badges.join('') + '</div>'
      + '<div class="ch-card-summary">' + _intgEsc(p.summary) + '</div>' + meta
      + '<div class="intg-card-actions">'
      + '<button type="button" class="sm-btn' + (p.configured ? '' : ' primary') + '" onclick="chOpenConfigure(\'' + _intgEsc(p.key) + '\')">' + (p.configured ? _intgT('channels_edit', 'Edit') : _intgT('channels_configure', 'Connect')) + '</button>'
      + (p.configured ? '<button type="button" class="sm-btn" onclick="chDisable(\'' + _intgEsc(p.key) + '\')">' + _intgT('channels_disable', 'Disconnect') + '</button>' : '')
      + '</div></div>';
  }).join('');
}

function chOpenConfigure(key) {
  const p = (_chState && _chState.platforms || []).find(x => x.key === key);
  if (!p) return;
  document.querySelectorAll('dialog.ch-dialog').forEach(d => d.remove());
  const dialog = document.createElement('dialog');
  dialog.className = 'app-dialog ch-dialog';
  dialog.style.cssText = 'max-width:520px;width:calc(100% - 32px);max-height:90vh;overflow:auto;margin:auto';
  const form = document.createElement('form'); form.method = 'dialog';
  const title = document.createElement('div'); title.className = 'app-dialog-title'; title.textContent = p.label; form.appendChild(title);
  const desc = document.createElement('div'); desc.className = 'app-dialog-desc'; desc.textContent = p.summary + ' ' + _intgT('channels_dialog_hint', ''); form.appendChild(desc);
  if (p.public) {
    const pub = document.createElement('div'); pub.className = 'app-dialog-desc ch-public';
    pub.textContent = p.public.state === 'published'
      ? p.public.label + ': ' + p.public.url
      : _intgT('channels_hook_on_save', 'On save the webhook is published through Tailscale Funnel and the public URL appears on the card. Enter that URL at the provider.');
    form.appendChild(pub);
  }
  const inputs = {};
  p.fields.forEach(f => {
    const wrap = document.createElement('div'); wrap.className = 'ch-field';
    const label = document.createElement('label'); label.textContent = f.label + (f.required ? ' *' : ''); wrap.appendChild(label);
    const input = document.createElement('input');
    input.type = f.secret ? 'password' : 'text'; input.autocomplete = 'off'; input.className = 'app-dialog-input';
    input.placeholder = f.set ? _intgT('channels_secret_stored', 'Stored. Leave blank to keep.') : '';
    wrap.appendChild(input);
    const hint = document.createElement('div'); hint.className = 'ch-hint'; hint.textContent = f.hint || ''; wrap.appendChild(hint);
    inputs[f.key] = input; form.appendChild(wrap);
  });
  const toggle = document.createElement('label'); toggle.className = 'ch-field-toggle';
  const box = document.createElement('input'); box.type = 'checkbox'; box.checked = !!p.allow_all;
  toggle.appendChild(box); toggle.appendChild(document.createTextNode(_intgT('channels_allow_all', 'Everyone on this platform may message the bot')));
  form.appendChild(toggle);
  const err = document.createElement('div'); err.className = 'intg-error'; err.style.display = 'none'; form.appendChild(err);
  const actions = document.createElement('div'); actions.className = 'app-dialog-actions';
  const cancel = document.createElement('button'); cancel.type = 'button'; cancel.className = 'app-dialog-btn'; cancel.textContent = t('cancel') || 'Cancel';
  cancel.addEventListener('click', () => { dialog.close(); dialog.remove(); });
  const submit = document.createElement('button'); submit.type = 'submit'; submit.className = 'app-dialog-btn confirm'; submit.textContent = t('save') || 'Save';
  actions.appendChild(cancel); actions.appendChild(submit); form.appendChild(actions);
  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const values = {};
    Object.keys(inputs).forEach(k => { if (inputs[k].value.trim()) values[k] = inputs[k].value.trim(); });
    const allowKey = p.fields.length ? null : null;
    values[_chAllowAllEnv(p.key)] = box.checked ? 'true' : 'false';
    submit.disabled = true; err.style.display = 'none';
    try {
      const r = await api('/api/gateway/channels/configure', { method: 'POST', body: JSON.stringify({ platform: p.key, values }), timeoutToast: false });
      if (!r || !r.ok) throw new Error((r && r.error) || _intgT('channels_failed', 'Channel action failed.'));
      showToast(_intgT('channels_saved', 'Channel saved. Restart the gateway to apply.'));
      dialog.close(); dialog.remove();
      Object.keys(inputs).forEach(k => { inputs[k].value = ''; });
      await chLoadChannels();
    } catch (e) {
      err.textContent = (e && e.message) || _intgT('channels_failed', 'Channel action failed.'); err.style.display = '';
      submit.disabled = false;
    }
  });
  dialog.appendChild(form); document.body.appendChild(dialog); dialog.showModal();
}

function _chAllowAllEnv(key) {
  return { telegram: 'TELEGRAM_ALLOW_ALL_USERS', whatsapp_cloud: 'WHATSAPP_CLOUD_ALLOW_ALL_USERS', slack: 'SLACK_ALLOW_ALL_USERS',
           teams: 'TEAMS_ALLOW_ALL_USERS', discord: 'DISCORD_ALLOW_ALL_USERS', google_chat: 'GOOGLE_CHAT_ALLOW_ALL_USERS' }[key] || '';
}

async function chDisable(key) {
  if (!confirm(_chLabel(key) + ': ' + _intgT('channels_disable', 'Disconnect') + '?')) return;
  try {
    const r = await api('/api/gateway/channels/disable', { method: 'POST', body: JSON.stringify({ platform: key }), timeoutToast: false });
    if (!r || !r.ok) throw new Error((r && r.error) || '');
    showToast(_intgT('channels_disabled', 'Channel disconnected. Restart the gateway to apply.'));
    await chLoadChannels();
  } catch (e) { showToast((e && e.message) || _intgT('channels_failed', 'Channel action failed.')); }
}

async function chRestartGateway() {
  try {
    showToast(_intgT('channels_restarting', 'Restarting the gateway. This takes about two minutes.'));
    const r = await api('/api/gateway/restart', { method: 'POST', body: '{}', timeoutToast: false, timeoutMs: 120000 });
    if (r && r.ok === false) throw new Error(r.error || '');
    if (typeof loadGatewayStatus === 'function') loadGatewayStatus();
  } catch (e) { showToast((e && e.message) || _intgT('channels_failed', 'Channel action failed.')); }
}

function _chPersonPickerHtml(id) {
  return '<input type="text" id="' + id + '" data-sp-picker data-sp-source="people" data-sp-custom="0" placeholder="' + _intgEsc(_intgT('channels_pick_person', 'Pick a person')) + '">';
}

function chRenderPending() {
  const host = $('intgChannelPending');
  if (!host || !_chState) return;
  const pending = (_chState.pairing && _chState.pairing.pending) || [];
  if (!_chState.pairing || !_chState.pairing.available) {
    host.innerHTML = '<div class="intg-muted">' + _intgT('channels_engine_missing', 'Pairing store not available on this server.') + '</div>';
    return;
  }
  if (!pending.length) { host.innerHTML = ''; return; }
  const engineToKey = { telegram: 'telegram', whatsapp_cloud: 'whatsapp_cloud', whatsapp: 'whatsapp_cloud', slack: 'slack', teams: 'teams', discord: 'discord', google_chat: 'google_chat' };
  host.innerHTML = '<div class="ch-pending"><div class="ch-pending-title">' + _intgT('channels_pending_title', 'Waiting for approval') + '</div>'
    + pending.map((r, i) => {
      const key = engineToKey[r.platform] || r.platform;
      const who = _intgT('channels_pending_row', '{name} on {platform} asked for access {age} min ago')
        .replace('{name}', r.user_name || r.user_id || '?').replace('{platform}', _chLabel(key)).replace('{age}', String(r.age_minutes || 0));
      return '<div class="ch-pending-row" data-platform="' + _intgEsc(key) + '" data-request="' + _intgEsc(r.request_id || '') + '">'
        + '<span class="ch-pending-who">' + _intgEsc(who) + ' <code>' + _intgEsc(String(r.user_id || '')) + '</code></span>'
        + _chPersonPickerHtml('chPendingPerson' + i)
        + '<button type="button" class="sm-btn primary" ' + (r.request_id ? '' : 'disabled ') + 'onclick="chApprove(this, \'chPendingPerson' + i + '\')">' + _intgT('channels_approve_btn', 'Approve') + '</button>'
        + '</div>';
    }).join('') + '</div>';
  if (window.SpPicker) SpPicker.mountAll(host);
}

async function chApprove(btn, pickerId) {
  const row = btn.closest('.ch-pending-row');
  const email = (document.getElementById(pickerId) || {}).value || '';
  if (!email) { showToast(_intgT('channels_pick_person', 'Pick a person')); return; }
  btn.disabled = true;
  try {
    const r = await api('/api/gateway/pairing/approve', { method: 'POST', timeoutToast: false,
      body: JSON.stringify({ platform: row.dataset.platform, request_id: row.dataset.request, email: String(email).split(',')[0].trim() }) });
    if (!r || !r.ok) throw new Error((r && r.error) || '');
    showToast(_intgT('channels_approved', 'Access approved.'));
    await chLoadChannels();
  } catch (e) { btn.disabled = false; showToast((e && e.message) || _intgT('channels_failed', 'Channel action failed.')); }
}

function chRenderPeople() {
  const host = $('intgChannelPeople');
  if (!host || !_chState) return;
  const people = _chState.people || [];
  const platforms = _chState.platforms || [];
  const rows = people.map(r => '<tr>'
    + '<td>' + _intgEsc(_chLabel(r.platform)) + '</td>'
    + '<td><code>' + _intgEsc(r.user_id) + '</code>' + (r.name ? ' <span class="intg-muted">' + _intgEsc(r.name) + '</span>' : '') + '</td>'
    + '<td class="ch-person">' + (typeof _personAvatarHtml === 'function' ? _personAvatarHtml(r.email, r.email, 22) : '') + '<span>' + _intgEsc(r.email) + '</span></td>'
    + '<td><code>' + _intgEsc(r.profile || 'gateway') + '</code></td>'
    + '<td><button type="button" class="sm-btn" onclick="chRemovePerson(\'' + _intgEsc(r.platform) + '\',\'' + _intgEsc(r.user_id) + '\')">' + _intgT('channels_remove', 'Remove') + '</button></td>'
    + '</tr>').join('');
  host.innerHTML = (people.length
    ? '<div class="intg-table-wrap"><table class="ch-people-table"><thead><tr><th>' + _intgT('channels_platform', 'Platform') + '</th><th>' + _intgT('channels_user_id', 'Platform user id') + '</th><th>' + _intgT('channels_person', 'Person') + '</th><th>' + _intgT('channels_profile', 'Runs as profile') + '</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div>'
    : '<div class="intg-muted">' + _intgT('channels_no_people', 'Nobody is mapped yet. Approve a pairing request or map a person by id.') + '</div>')
    + '<div class="ch-people-add">'
    + '<label>' + _intgT('channels_platform', 'Platform') + '<select id="chAddPlatform">' + platforms.map(p => '<option value="' + _intgEsc(p.key) + '">' + _intgEsc(p.label) + '</option>').join('') + '</select></label>'
    + '<label>' + _intgT('channels_user_id', 'Platform user id') + '<input type="text" id="chAddUserId" placeholder="' + _intgEsc((platforms[0] || {}).user_id_hint || '') + '"></label>'
    + '<label>' + _intgT('channels_person', 'Person') + _chPersonPickerHtml('chAddPerson') + '</label>'
    + '<button type="button" class="sm-btn primary" onclick="chAddPerson()">' + _intgT('channels_add_person', '+ Map a person') + '</button>'
    + '</div>';
  const sel = $('chAddPlatform');
  if (sel) sel.addEventListener('change', () => { const p = platforms.find(x => x.key === sel.value); const inp = $('chAddUserId'); if (inp && p) inp.placeholder = p.user_id_hint || ''; });
  if (window.SpPicker) SpPicker.mountAll(host);
}

function chCopy(btn) {
  try { navigator.clipboard.writeText(btn.dataset.copy || ''); showToast(_intgT('copied', 'Copied')); } catch (_) {}
}
async function chPublish(key) {
  try {
    const r = await api('/api/gateway/channels/publish', { method: 'POST', body: JSON.stringify({ platform: key }), timeoutToast: false, timeoutMs: 60000 });
    if (!r || !r.ok) throw new Error((r && r.error) || '');
    showToast(_intgT('channels_published', 'Webhook published.') + ' ' + r.url);
    await chLoadChannels();
  } catch (e) { showToast((e && e.message) || _intgT('channels_failed', 'Channel action failed.')); }
}
async function chAddPerson() {
  const platform = ($('chAddPlatform') || {}).value, userId = (($('chAddUserId') || {}).value || '').trim();
  const email = String(($('chAddPerson') || {}).value || '').split(',')[0].trim();
  if (!platform || !userId || !email) { showToast(_intgT('channels_pick_person', 'Pick a person')); return; }
  try {
    const r = await api('/api/gateway/identities/set', { method: 'POST', timeoutToast: false, body: JSON.stringify({ platform, user_id: userId, email }) });
    if (!r || !r.ok) throw new Error((r && r.error) || '');
    showToast(_intgT('channels_person_saved', 'Person mapped.'));
    await chLoadChannels();
  } catch (e) { showToast((e && e.message) || _intgT('channels_failed', 'Channel action failed.')); }
}

async function chRemovePerson(platform, userId) {
  try {
    const r = await api('/api/gateway/identities/remove', { method: 'POST', timeoutToast: false, body: JSON.stringify({ platform, user_id: userId }) });
    if (!r || !r.ok) throw new Error((r && r.error) || '');
    showToast(_intgT('channels_person_removed', 'Mapping removed.'));
    await chLoadChannels();
  } catch (e) { showToast((e && e.message) || _intgT('channels_failed', 'Channel action failed.')); }
}

if (typeof window !== 'undefined') {
  Object.assign(window, { chLoadChannels, chOpenConfigure, chDisable, chRestartGateway, chApprove, chAddPerson, chRemovePerson, chPublish, chCopy });
}


// ── Your bot: one bot per person, self-service ─────────────────────────────
let _chMine = null;
async function chLoadMine() {
  const root = $('intgMine'), body = $('intgMineBody');
  if (!root || !body) return;
  try {
    _chMine = await api('/api/me/channels', { redirect401: false, timeoutToast: false });
  } catch (e) {
    root.style.display = 'none'; _chMine = null; return;
  }
  root.style.display = '';
  chRenderMine();
}

function chRenderMine() {
  const body = $('intgMineBody');
  if (!body || !_chMine) return;
  const m = _chMine;
  const tg = (m.own_bot || {}).telegram || {};
  const gw = m.people_gateway || {};
  const links = m.links || [];
  const when = gw.last_apply_at ? new Date(gw.last_apply_at * 1000).toLocaleString() : '';
  let html = '<div class="ch-mine-grid">';
  html += '<div class="intg-card configured"><div class="intg-card-head">' + (typeof li === 'function' ? li('zap', 16) : '') + '<div class="intg-card-name">Telegram</div></div>';
  if (m.shared_bot) {
    html += '<div class="ch-card-summary">' + _intgEsc(_intgT('mychannels_shared', '')) + '</div>';
  } else {
    html += '<div class="ch-card-status">' + (tg.token_set ? '<span class="intg-badge intg-badge-ok">' + _intgT('mychannels_token_stored', 'Token stored') + '</span>' : '<span class="intg-badge">' + _intgT('mychannels_token_missing', 'No bot yet') + '</span>')
      + '<span class="intg-badge">' + _intgT('mychannels_profile', 'Profile') + ': ' + _intgEsc(m.profile) + '</span></div>';
    html += '<div class="ch-card-summary">' + _intgEsc(_intgT('mychannels_intro', '')) + '</div>';
    html += '<details class="ch-steps"><summary>' + _intgT('help', 'How') + '</summary><div class="ch-card-summary">' + _intgEsc(_intgT('mychannels_steps', '')) + '</div></details>';
    html += '<div class="ch-field"><label>' + _intgT('mychannels_token', 'Bot token from @BotFather') + '</label><div class="ch-inline"><input type="password" id="chMineToken" autocomplete="off" placeholder="' + (tg.token_set ? _intgEsc(_intgT('channels_secret_stored', 'Stored. Leave blank to keep.')) : '123456:ABC...') + '"><button type="button" class="sm-btn primary" onclick="chSaveMyToken()">' + _intgT('mychannels_save_token', 'Save token') + '</button>'
      + (tg.token_set ? '<button type="button" class="sm-btn" onclick="chRemoveMyBot()">' + _intgT('mychannels_remove_bot', 'Remove bot') + '</button>' : '') + '</div></div>';
  }
  html += '<div class="ch-field"><label>' + _intgT('mychannels_your_id', 'Your Telegram user id') + '</label><div class="ch-inline"><input type="text" id="chMineId" placeholder="' + _intgEsc(tg.user_id_hint || '') + '"><button type="button" class="sm-btn primary" onclick="chLinkMe(\'telegram\')">' + _intgT('mychannels_link', 'Link') + '</button></div><div class="ch-hint">' + _intgEsc(_intgT('mychannels_your_id_hint', '')) + '</div></div>';
  html += '</div>';
  html += '<div class="intg-card"><div class="intg-card-name">' + _intgT('mychannels_links', 'Your linked platform ids') + '</div>';
  html += links.length ? '<div class="intg-table-wrap"><table class="ch-people-table"><tbody>' + links.map(l => '<tr><td>' + _intgEsc(_chLabelFrom(m.platforms, l.platform)) + '</td><td><code>' + _intgEsc(l.user_id) + '</code></td><td><code>' + _intgEsc(l.profile || 'gateway') + '</code></td><td><button type="button" class="sm-btn" onclick="chUnlinkMe(\'' + _intgEsc(l.platform) + '\',\'' + _intgEsc(l.user_id) + '\')">' + _intgT('mychannels_unlink', 'Unlink') + '</button></td></tr>').join('') + '</tbody></table></div>'
    : '<div class="intg-muted">' + _intgT('mychannels_no_links', 'Nothing linked yet.') + '</div>';
  html += '<div class="ch-field"><label>' + _intgT('channels_platform', 'Platform') + '</label><div class="ch-inline"><select id="chMinePlatform">' + (m.platforms || []).filter(p => p.key !== 'telegram').map(p => '<option value="' + _intgEsc(p.key) + '">' + _intgEsc(p.label) + '</option>').join('') + '</select><input type="text" id="chMineOtherId" placeholder="' + _intgEsc(_intgT('channels_user_id', 'Platform user id')) + '"><button type="button" class="sm-btn" onclick="chLinkMe(null)">' + _intgT('mychannels_link', 'Link') + '</button></div></div>';
  html += '</div></div>';
  html += '<div class="ch-apply"><button type="button" class="sm-btn' + (gw.active === false ? ' primary' : '') + '" onclick="chApplyMine()" ' + (gw.available ? '' : 'disabled') + '>' + _intgT('mychannels_apply', 'Apply (restart bots)') + '</button><span class="ch-hint">' + _intgEsc(_intgT('mychannels_apply_hint', '')) + (when ? ' ' + _intgEsc(_intgT('mychannels_last_apply', 'Last applied {when} by {who}').replace('{when}', when).replace('{who}', gw.last_apply_by || '?')) : '') + '</span></div>';
  body.innerHTML = html;
}
function _chLabelFrom(platforms, key) { const p = (platforms || []).find(x => x.key === key); return p ? p.label : key; }

async function chSaveMyToken() {
  const token = (($('chMineToken') || {}).value || '').trim();
  if (!token) return;
  try {
    const r = await api('/api/me/channels/bot', { method: 'POST', timeoutToast: false, body: JSON.stringify({ platform: 'telegram', values: { TELEGRAM_BOT_TOKEN: token } }) });
    if (!r || !r.ok) throw new Error((r && r.error) || '');
    showToast(_intgT('mychannels_saved', 'Saved.')); await chLoadMine();
  } catch (e) { showToast((e && e.message) || _intgT('channels_failed', 'Channel action failed.')); }
}
async function chRemoveMyBot() {
  if (!confirm(_intgT('mychannels_remove_bot', 'Remove bot') + '?')) return;
  try {
    const r = await api('/api/me/channels/bot', { method: 'POST', timeoutToast: false, body: JSON.stringify({ platform: 'telegram', remove: true }) });
    if (!r || !r.ok) throw new Error((r && r.error) || '');
    showToast(_intgT('mychannels_saved', 'Saved.')); await chLoadMine();
  } catch (e) { showToast((e && e.message) || _intgT('channels_failed', 'Channel action failed.')); }
}
async function chLinkMe(platform) {
  const key = platform || (($('chMinePlatform') || {}).value || '');
  const uid = ((platform ? $('chMineId') : $('chMineOtherId')) || {}).value || '';
  if (!key || !uid.trim()) return;
  try {
    const r = await api('/api/me/channels/link', { method: 'POST', timeoutToast: false, body: JSON.stringify({ platform: key, user_id: uid.trim() }) });
    if (!r || !r.ok) throw new Error((r && r.error) || '');
    showToast(_intgT('mychannels_linked', 'Linked.')); await chLoadMine(); if (typeof chLoadChannels === 'function') chLoadChannels();
  } catch (e) { showToast((e && e.message) || _intgT('channels_failed', 'Channel action failed.')); }
}
async function chUnlinkMe(platform, uid) {
  try {
    const r = await api('/api/me/channels/unlink', { method: 'POST', timeoutToast: false, body: JSON.stringify({ platform, user_id: uid }) });
    if (!r || !r.ok) throw new Error((r && r.error) || '');
    showToast(_intgT('mychannels_unlinked', 'Unlinked.')); await chLoadMine(); if (typeof chLoadChannels === 'function') chLoadChannels();
  } catch (e) { showToast((e && e.message) || _intgT('channels_failed', 'Channel action failed.')); }
}
async function chApplyMine() {
  try {
    const r = await api('/api/me/channels/apply', { method: 'POST', body: '{}', timeoutToast: false, timeoutMs: 130000 });
    if (!r || !r.ok) throw new Error((r && r.error) || '');
    showToast(_intgT('mychannels_applied', 'Bots are restarting.')); await chLoadMine();
  } catch (e) { showToast((e && e.message) || _intgT('channels_failed', 'Channel action failed.')); }
}
if (typeof window !== 'undefined') Object.assign(window, { chLoadMine, chSaveMyToken, chRemoveMyBot, chLinkMe, chUnlinkMe, chApplyMine });
