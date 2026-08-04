// ── Governance panel ──────────────────────────────────────────────────────
// Admin UI for the dashboard governance policy (roles, groups, users, access
// preview, audit tail). All data comes from /api/governance/* (see
// api/governance_api.py). Visibility of the nav buttons is cosmetic only:
// the server enforces every permission independently of what this file shows.
//
// Mutations are optimistic-concurrency guarded: every POST carries the last
// fetched policy etag in an If-Match header; a 412 response means the policy
// changed elsewhere and triggers a reload toast + refetch.
// CSRF: the global fetch wrapper in index.html injects X-Hermes-CSRF-Token on
// every mutation automatically; this file never sets that header manually.

let _govEtag = null;
let _govTab = 'overview';
let _govEditingUser = null;   // email currently being edited, null = create mode
let _govEditingGroup = null;  // group name currently being edited, null = create mode

function _govEsc(s) {
  if (typeof _escHtml === 'function') return _escHtml(s);
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function _govT(key, fallback) {
  const val = (typeof t === 'function') ? t(key) : key;
  return (val && val !== key) ? val : fallback;
}

function _govIsAdmin(me) {
  if (!me) return false;
  if (me.is_bootstrap_admin) return true;
  const perms = Array.isArray(me.permissions) ? me.permissions : [];
  return perms.includes('*') || perms.includes('governance:read') || perms.includes('governance:write');
}

/** Show/hide every governance nav button. Cosmetic only; server enforces. */
function govApplyVisibility(me) {
  const show = _govIsAdmin(me);
  document.querySelectorAll('[data-panel="governance"]').forEach(btn => {
    btn.style.display = show ? '' : 'none';
  });
}

async function _govFetchMe() {
  try {
    window.__GOV_ME__ = await api('/api/governance/me', { redirect401: false, timeoutToast: false, timeoutMs: 15000 });
  } catch (e) {
    window.__GOV_ME__ = null;
  }
  return window.__GOV_ME__;
}

/**
 * Panel entry point, called by switchPanel. Returns false when the caller is
 * not a governance admin so panels.js can fall back to the chat panel.
 */
async function loadGovernance() {
  const me = await _govFetchMe();
  govApplyVisibility(me);
  if (!_govIsAdmin(me)) return false;
  _govEnsureWorkspacesTab();
  _govRefreshApprovalsBadge();
  await _govSwitchTab(_govTab || 'overview');
  return true;
}

async function _govSwitchTab(name) {
  _govEnsureWorkspacesTab();
  const tab = ['overview', 'users', 'groups', 'workspaces', 'approvals', 'preview', 'audit'].includes(name) ? name : 'overview';
  _govTab = tab;
  document.querySelectorAll('#mainGovernance .gov-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.govTab === tab);
  });
  document.querySelectorAll('#mainGovernance .gov-tab-pane').forEach(pane => {
    pane.classList.toggle('active', pane.id === 'govPane' + tab.charAt(0).toUpperCase() + tab.slice(1));
  });
  if (tab === 'overview') await _govLoadOverview();
  if (tab === 'users') await _govLoadUsers();
  if (tab === 'groups') await _govLoadGroups();
  if (tab === 'workspaces') await _govLoadWorkspaces();
  if (tab === 'approvals') await _govLoadApprovals();
  if (tab === 'audit') await _govLoadAudit();
  // preview tab is form-driven; nothing to preload
}

async function _govRefreshTab() {
  try { await _govSwitchTab(_govTab); } catch (e) { /* rendered by the tab loader */ }
}

// ── HTTP helpers ──────────────────────────────────────────────────────────

async function _govPost(path, body) {
  return api(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'If-Match': _govEtag || '' },
    body: JSON.stringify(body),
    redirect401: false,
  });
}

/** Shared 412 handler: policy changed elsewhere, reload and let the user retry. */
function _govHandleConflict(e) {
  if (e && Number(e.status) === 412) {
    if (typeof showToast === 'function') showToast(_govT('governance_conflict_reload', 'Policy changed elsewhere, reloading'), 4000, 'error');
    _govRefreshTab();
    return true;
  }
  return false;
}

function _govError(e, containerId) {
  const el = $(containerId);
  let msg = (e && e.message) ? e.message : 'request failed';
  // Governance 403s carry structured reason/resource (attached by api());
  // surface them instead of the bare "forbidden".
  if (e && Number(e.status) === 403 && (e.reason || e.resource)) {
    msg = 'Access restricted' + (e.resource ? ': ' + e.resource : '') + (e.reason ? ' (' + e.reason + ')' : '');
  }
  if (el) el.innerHTML = '<div class="gov-error">' + _govEsc(msg) + '</div>';
}

function _govCsv(value) {
  return String(value || '').split(',').map(s => s.trim()).filter(Boolean);
}

// ── Overview tab ──────────────────────────────────────────────────────────

async function _govLoadOverview() {
  const el = $('govPaneOverview');
  if (!el) return;
  el.innerHTML = '<div class="gov-muted" data-i18n="loading">' + _govT('loading', 'Loading...') + '</div>';
  let data;
  try {
    data = await api('/api/governance/policy', { redirect401: false });
  } catch (e) {
    _govError(e, 'govPaneOverview');
    return;
  }
  _govEtag = data.etag || null;
  const policy = data.policy || {};
  const mode = String(policy.mode || 'off');
  const counts = {
    roles: Object.keys(policy.roles || {}).length,
    groups: Object.keys(policy.groups || {}).length,
    users: Object.keys(policy.users || {}).length,
    admins: Array.isArray(policy.bootstrap_admins) ? policy.bootstrap_admins.length : 0,
  };
  let denials24h = null;
  try {
    const audit = await api('/api/governance/audit?limit=200', { redirect401: false, timeoutToast: false });
    const cutoff = Date.now() - 24 * 3600 * 1000;
    denials24h = (audit.events || []).filter(ev => {
      if (ev.event !== 'deny' && ev.event !== 'would_deny') return false;
      const ts = Date.parse(ev.ts || '');
      return Number.isFinite(ts) && ts >= cutoff;
    }).length;
  } catch (e) { /* audit permission may be missing; leave blank */ }
  const stat = (label, value) => (
    '<div class="gov-stat"><div class="gov-stat-value">' + _govEsc(value) + '</div>' +
    '<div class="gov-stat-label">' + _govEsc(label) + '</div></div>'
  );
  el.innerHTML =
    '<div class="gov-overview-head">' +
      '<span class="gov-mode-badge gov-mode-' + _govEsc(mode) + '">' + _govT('governance_mode', 'Mode') + ': ' + _govEsc(mode) + '</span>' +
    '</div>' +
    '<div class="gov-stat-grid">' +
      stat(_govT('governance_stat_roles', 'Roles'), counts.roles) +
      stat(_govT('governance_stat_groups', 'Groups'), counts.groups) +
      stat(_govT('governance_stat_users', 'Users'), counts.users) +
      stat(_govT('governance_stat_admins', 'Bootstrap admins'), counts.admins) +
      stat(_govT('governance_stat_denials', 'Denials (24h)'), denials24h === null ? '?' : denials24h) +
    '</div>' +
    '<div class="gov-muted gov-overview-note">' + _govT('governance_overview_note',
      'Policy file: dashboard-governance.yaml. Denials include report-only would-deny events.') + '</div>';
}

// ── Users tab ─────────────────────────────────────────────────────────────

async function _govLoadUsers() {
  const el = $('govPaneUsers');
  if (!el) return;
  el.innerHTML = '<div class="gov-muted">' + _govT('loading', 'Loading...') + '</div>';
  let data;
  try {
    data = await api('/api/governance/users', { redirect401: false });
  } catch (e) {
    _govError(e, 'govPaneUsers');
    return;
  }
  _govEtag = data.etag || _govEtag;
  const users = data.users || {};
  const rows = Object.keys(users).sort().map(email => {
    const entry = users[email] || {};
    return '<tr>' +
      '<td>' + _govEsc(email) + '</td>' +
      '<td>' + _govEsc((entry.roles || []).join(', ')) + '</td>' +
      '<td>' + _govEsc((entry.groups || []).join(', ')) + '</td>' +
      '<td class="gov-row-actions">' +
        '<button type="button" class="gov-btn" onclick="_govEditUser(' + _govEsc(JSON.stringify(email)) + ')">' + _govT('governance_edit', 'Edit') + '</button>' +
        '<button type="button" class="gov-btn danger" onclick="_govDeleteUser(' + _govEsc(JSON.stringify(email)) + ')">' + _govT('governance_delete', 'Delete') + '</button>' +
      '</td></tr>';
  }).join('');
  window.__GOV_USERS__ = users;
  el.innerHTML =
    '<table class="gov-table"><thead><tr>' +
      '<th>' + _govT('governance_col_email', 'Email') + '</th>' +
      '<th>' + _govT('governance_col_roles', 'Roles') + '</th>' +
      '<th>' + _govT('governance_col_groups', 'Groups') + '</th><th></th>' +
    '</tr></thead><tbody>' + (rows || '<tr><td colspan="4" class="gov-muted">' + _govT('governance_no_users', 'No user entries in the policy.') + '</td></tr>') + '</tbody></table>' +
    '<div class="gov-form" id="govUserForm">' +
      '<div class="gov-form-title" id="govUserFormTitle">' + _govT('governance_user_add', 'Add user') + '</div>' +
      '<div class="gov-form-row"><label for="govUserEmail">' + _govT('governance_col_email', 'Email') + '</label>' +
        '<input id="govUserEmail" type="text" placeholder="name@example.com"></div>' +
      '<div class="gov-form-row"><label for="govUserRoles">' + _govT('governance_roles_csv', 'Roles (comma separated)') + '</label>' +
        '<input id="govUserRoles" type="text" placeholder="viewer, operator"></div>' +
      '<div class="gov-form-row"><label for="govUserGroups">' + _govT('governance_groups_csv', 'Groups (comma separated)') + '</label>' +
        '<input id="govUserGroups" type="text" placeholder="sw-engineering"></div>' +
      '<div class="gov-form-title gov-grants-title">' + _govT('governance_grants_title', 'Per-user grants (optional)') + '</div>' +
      _govChipFieldHtml('govUserSkillsView', _govT('governance_grants_skills_view', 'Skills view'), 'govDlSkills', 'my-skill, *') +
      _govChipFieldHtml('govUserSkillsLoad', _govT('governance_grants_skills_load', 'Skills load'), 'govDlSkills', 'my-skill') +
      _govChipFieldHtml('govUserSkillsManage', _govT('governance_grants_skills_manage', 'Skills manage'), 'govDlSkills', 'my-skill') +
      _govChipFieldHtml('govUserMcpServers', _govT('governance_grants_mcp_servers', 'MCP servers'), 'govDlMcp', 'notion, playwright') +
      _govChipFieldHtml('govUserCliCommands', _govT('governance_grants_cli_commands', 'CLI commands'), 'govDlCli', 'git, gh') +
      _govChipFieldHtml('govUserCliApproval', _govT('governance_grants_cli_approval', 'CLI commands requiring approval'), 'govDlCli', 'rm, sudo') +
      '<div class="gov-form-title gov-grants-title">' + _govT('governance_deny_title', 'Off-toggles (deny)') + '</div>' +
      '<div class="gov-muted">' + _govT('governance_deny_note',
        'Switched-off items override every role and group grant for this user. A specific off-toggle cannot narrow a wildcard (*) grant.') + '</div>' +
      _govChipFieldHtml('govUserDenySkills', _govT('governance_deny_skills', 'Skills off'), 'govDlSkills', 'my-skill') +
      _govChipFieldHtml('govUserDenyCli', _govT('governance_deny_cli', 'CLI commands off'), 'govDlCli', 'rm') +
      _govChipFieldHtml('govUserDenyMcp', _govT('governance_deny_mcp', 'MCP servers off'), 'govDlMcp', 'playwright') +
      '<div id="govUserEffective"></div>' +
      '<datalist id="govDlSkills"></datalist>' +
      '<datalist id="govDlCli"></datalist>' +
      '<datalist id="govDlMcp"></datalist>' +
      '<div class="gov-form-actions">' +
        '<button type="button" class="gov-btn primary" onclick="_govSaveUser()">' + _govT('governance_save', 'Save') + '</button>' +
        '<button type="button" class="gov-btn" onclick="_govResetUserForm()">' + _govT('governance_cancel', 'Cancel') + '</button>' +
      '</div>' +
    '</div>';
  _govResetUserForm();
  _govEnsureCatalogs().then(_govFillCatalogDatalists).catch(() => {});
}

const _GOV_USER_GRANT_FIELDS = ['govUserSkillsView', 'govUserSkillsLoad', 'govUserSkillsManage', 'govUserMcpServers', 'govUserCliCommands', 'govUserCliApproval'];
const _GOV_USER_DENY_FIELDS = ['govUserDenySkills', 'govUserDenyCli', 'govUserDenyMcp'];

// ── Chip multi-select with datalist autocomplete ──────────────────────────
// Values live in _govChipState (fieldId -> ordered unique array); the DOM is
// re-rendered from that state. Datalists are filled from _govEnsureCatalogs.

let _govChipState = {};

function _govChipsGet(id) { return _govChipState[id] || []; }

function _govChipsSet(id, values) {
  const seen = new Set();
  _govChipState[id] = (values || []).map(v => String(v).trim()).filter(v => v && !seen.has(v) && seen.add(v));
  _govRenderChipField(id);
}

function _govChipFieldHtml(id, label, datalistId, placeholder) {
  return '<div class="gov-form-row"><label for="' + id + 'Input">' + _govEsc(label) + '</label>' +
    '<div class="gov-chipbox" id="' + id + 'Box" onclick="(function(i){if(i)i.focus();})($(\'' + id + 'Input\'))">' +
      '<input id="' + id + 'Input" type="text" list="' + _govEsc(datalistId) + '" placeholder="' + _govEsc(placeholder || '') + '" autocomplete="off"' +
      ' onkeydown="_govChipKey(event, \'' + id + '\')" onchange="_govChipCommit(\'' + id + '\')" onblur="_govChipCommit(\'' + id + '\')">' +
    '</div></div>';
}

function _govRenderChipField(id) {
  const box = $(id + 'Box');
  const input = $(id + 'Input');
  if (!box || !input) return;
  box.querySelectorAll('.gov-chip-item').forEach(n => n.remove());
  _govChipsGet(id).forEach(value => {
    const chip = document.createElement('span');
    chip.className = 'gov-chip gov-chip-item';
    chip.textContent = value;
    const x = document.createElement('button');
    x.type = 'button';
    x.className = 'gov-chip-x';
    x.textContent = '×';
    x.title = _govT('governance_remove', 'Remove');
    x.addEventListener('click', ev => { ev.stopPropagation(); _govChipRemove(id, value); });
    chip.appendChild(x);
    box.insertBefore(chip, input);
  });
  // deny fields drive the effective on/off view
  if (_GOV_USER_DENY_FIELDS.includes(id)) _govRenderUserEffective();
}

function _govChipAdd(id, value) {
  const v = String(value || '').trim().replace(/,+$/, '').trim();
  if (!v) return;
  const values = _govChipsGet(id);
  if (!values.includes(v)) _govChipsSet(id, values.concat([v]));
}

function _govChipRemove(id, value) {
  _govChipsSet(id, _govChipsGet(id).filter(v => v !== value));
}

function _govChipCommit(id) {
  const input = $(id + 'Input');
  if (!input) return;
  // a paste/typed value may itself be a comma list
  _govCsv(input.value).forEach(v => _govChipAdd(id, v));
  input.value = '';
}

function _govChipKey(event, id) {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault();
    _govChipCommit(id);
  } else if (event.key === 'Backspace' && !event.target.value) {
    const values = _govChipsGet(id);
    if (values.length) _govChipRemove(id, values[values.length - 1]);
  }
}

// ── Autocomplete catalogs (skills, MCP servers, CLI commands) ─────────────
// Skills and MCP servers come from their live catalogs; CLI command ids have
// no catalog endpoint, so the union of every cli.commands already in the
// policy is offered (free text still works for new commands).

async function _govEnsureCatalogs(force) {
  if (window.__GOV_CAT__ && !force) return window.__GOV_CAT__;
  const cat = { skills: [], mcp: [], cli: [] };
  const opts = { redirect401: false, timeoutToast: false, timeoutMs: 15000 };
  await Promise.all([
    api('/api/skills', opts).then(d => {
      cat.skills = (d.skills || []).map(s => s && s.name).filter(Boolean).sort();
    }).catch(() => {}),
    api('/api/mcp/servers', opts).then(d => {
      cat.mcp = (d.servers || []).map(s => s && s.name).filter(Boolean).sort();
    }).catch(() => {}),
    api('/api/governance/policy', opts).then(d => {
      const seen = new Set();
      const walk = grants => {
        const cli = (grants && grants.cli && typeof grants.cli === 'object') ? grants.cli : {};
        (Array.isArray(cli.commands) ? cli.commands : []).forEach(c => {
          const v = (typeof c === 'string') ? c : ((c && (c.id || c.argv0)) || '');
          if (v && v !== '*') seen.add(v);
        });
      };
      const policy = d.policy || {};
      Object.values(policy.roles || {}).forEach(r => walk((r || {}).grants));
      Object.values(policy.groups || {}).forEach(g => walk((g || {}).grants));
      Object.values(policy.users || {}).forEach(u => { walk((u || {}).grants); walk((u || {}).deny); });
      cat.cli = Array.from(seen).sort();
      if (d.etag) _govEtag = d.etag;
    }).catch(() => {}),
  ]);
  window.__GOV_CAT__ = cat;
  return cat;
}

function _govFillCatalogDatalists(cat) {
  const fill = (id, values) => {
    const dl = $(id);
    if (dl) dl.innerHTML = values.map(v => '<option value="' + _govEsc(v) + '"></option>').join('');
  };
  fill('govDlSkills', cat.skills);
  fill('govDlMcp', cat.mcp);
  fill('govDlCli', cat.cli);
}

function _govResetUserForm() {
  _govEditingUser = null;
  _govUserEffective = null;
  const title = $('govUserFormTitle');
  if (title) title.textContent = _govT('governance_user_add', 'Add user');
  const email = $('govUserEmail');
  if (email) { email.value = ''; email.disabled = false; }
  const roles = $('govUserRoles');
  if (roles) roles.value = '';
  const groups = $('govUserGroups');
  if (groups) groups.value = '';
  _GOV_USER_GRANT_FIELDS.concat(_GOV_USER_DENY_FIELDS).forEach(id => _govChipsSet(id, []));
  _govRenderUserEffective();
}

function _govEditUser(email) {
  const entry = (window.__GOV_USERS__ || {})[email] || {};
  _govEditingUser = email;
  const title = $('govUserFormTitle');
  if (title) title.textContent = _govT('governance_user_edit', 'Edit user');
  const emailEl = $('govUserEmail');
  if (emailEl) { emailEl.value = email; emailEl.disabled = true; }
  const roles = $('govUserRoles');
  if (roles) roles.value = (entry.roles || []).join(', ');
  const groups = $('govUserGroups');
  if (groups) groups.value = (entry.groups || []).join(', ');
  const grants = (entry.grants && typeof entry.grants === 'object') ? entry.grants : {};
  const skills = (grants.skills && typeof grants.skills === 'object') ? grants.skills : {};
  const mcp = (grants.mcp && typeof grants.mcp === 'object') ? grants.mcp : {};
  const cli = (grants.cli && typeof grants.cli === 'object') ? grants.cli : {};
  _govChipsSet('govUserSkillsView', skills.view || []);
  _govChipsSet('govUserSkillsLoad', skills.load || []);
  _govChipsSet('govUserSkillsManage', skills.manage || []);
  _govChipsSet('govUserMcpServers', mcp.servers || []);
  // cli.commands entries may be strings or {id/argv0} objects per the policy schema
  const commands = (cli.commands || []).map(c => (typeof c === 'string') ? c : ((c && (c.id || c.argv0)) || '')).filter(Boolean);
  _govChipsSet('govUserCliCommands', commands);
  _govChipsSet('govUserCliApproval', cli.approval_commands || []);
  const deny = (entry.deny && typeof entry.deny === 'object') ? entry.deny : {};
  const denySkills = (deny.skills && typeof deny.skills === 'object') ? deny.skills : {};
  const denyMcp = (deny.mcp && typeof deny.mcp === 'object') ? deny.mcp : {};
  const denyCli = (deny.cli && typeof deny.cli === 'object') ? deny.cli : {};
  // the single "skills off" toggle covers view+load; the union round-trips
  // hand-edited asymmetric deny entries into a symmetric one on save
  _govChipsSet('govUserDenySkills', Array.from(new Set([].concat(denySkills.view || [], denySkills.load || []))));
  const denyCommands = (denyCli.commands || []).map(c => (typeof c === 'string') ? c : ((c && (c.id || c.argv0)) || '')).filter(Boolean);
  _govChipsSet('govUserDenyCli', denyCommands);
  _govChipsSet('govUserDenyMcp', denyMcp.servers || []);
  _govLoadUserEffective(email);
}

// ── Effective access on/off view ──────────────────────────────────────────
// Edit mode only: the union of the user's effective grants (post-deny, from
// the preview endpoint) and the current deny chips, rendered as clickable
// on/off toggles that write into the deny chip fields.

let _govUserEffective = null;

async function _govLoadUserEffective(email) {
  const el = $('govUserEffective');
  if (el) el.innerHTML = '<div class="gov-muted">' + _govT('loading', 'Loading...') + '</div>';
  try {
    const data = await api('/api/governance/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email }),
      redirect401: false,
      timeoutToast: false,
    });
    _govUserEffective = ((data.effective_access || {}).grants) || null;
  } catch (e) {
    _govUserEffective = null;
  }
  _govRenderUserEffective();
}

function _govRenderUserEffective() {
  const el = $('govUserEffective');
  if (!el) return;
  if (!_govEditingUser || !_govUserEffective) { el.innerHTML = ''; return; }
  const g = _govUserEffective;
  const sections = [
    { label: _govT('governance_eff_skills', 'Skills'), denyField: 'govUserDenySkills', granted: ((g.skills || {}).load) || [] },
    { label: _govT('governance_eff_cli', 'CLI commands'), denyField: 'govUserDenyCli', granted: ((g.cli || {}).commands) || [] },
    { label: _govT('governance_eff_mcp', 'MCP servers'), denyField: 'govUserDenyMcp', granted: ((g.mcp || {}).servers) || [] },
  ];
  const body = sections.map(sec => {
    const deny = _govChipsGet(sec.denyField);
    const wildcard = sec.granted.includes('*');
    const items = Array.from(new Set(sec.granted.filter(v => v !== '*').concat(deny))).sort();
    const chips = items.map(v => {
      const off = deny.includes(v);
      return '<button type="button" class="gov-chip gov-toggle ' + (off ? 'off' : 'on') +
        '" onclick="_govEffToggle(\'' + sec.denyField + '\', ' + _govEsc(JSON.stringify(v)) + ')" title="' +
        _govT('governance_toggle_hint', 'Click to toggle on/off') + '">' + _govEsc(v) + '</button>';
    }).join(' ');
    const wildcardNote = (wildcard && deny.length)
      ? '<div class="gov-error">' + _govT('governance_deny_wildcard_warn',
          'This user has a wildcard (*) grant here: specific off-toggles have no effect until the wildcard is replaced by an explicit list.') + '</div>'
      : (wildcard ? '<div class="gov-muted">' + _govT('governance_eff_wildcard', 'Wildcard (*) grant: everything is allowed.') + '</div>' : '');
    return '<div class="gov-preview-section"><div class="gov-form-title">' + _govEsc(sec.label) + '</div>' +
      (chips || '<span class="gov-muted">' + _govT('governance_none', 'none') + '</span>') + wildcardNote + '</div>';
  }).join('');
  el.innerHTML =
    '<div class="gov-form-title gov-grants-title">' + _govT('governance_eff_title', 'Effective access (click to toggle)') + '</div>' +
    '<div class="gov-muted">' + _govT('governance_eff_note',
      'Union of role, group and user grants after off-toggles. Save to apply; unsaved grant edits above are not reflected yet.') + '</div>' +
    body;
}

function _govEffToggle(denyField, value) {
  if (_govChipsGet(denyField).includes(value)) _govChipRemove(denyField, value);
  else _govChipAdd(denyField, value);
}

/**
 * Build the grants object from the form fields, or null when every field is
 * empty. Grant keys the form does not edit (mcp.tools, cli.workdir_roots,
 * usage_caps, ...) are carried over from the entry being edited so a save
 * never silently drops them.
 */
function _govCollectUserGrants() {
  const existing = (_govEditingUser && (window.__GOV_USERS__ || {})[_govEditingUser]) || {};
  const prior = (existing.grants && typeof existing.grants === 'object') ? existing.grants : {};
  const grants = {};
  for (const k of Object.keys(prior)) {
    if (k !== 'skills' && k !== 'mcp' && k !== 'cli') grants[k] = prior[k];
  }
  const skills = {};
  const view = _govChipsGet('govUserSkillsView');
  const load = _govChipsGet('govUserSkillsLoad');
  const manage = _govChipsGet('govUserSkillsManage');
  if (view.length) skills.view = view;
  if (load.length) skills.load = load;
  if (manage.length) skills.manage = manage;
  if (Object.keys(skills).length) grants.skills = skills;
  const mcp = {};
  const priorMcp = (prior.mcp && typeof prior.mcp === 'object') ? prior.mcp : {};
  if (priorMcp.tools && Object.keys(priorMcp.tools).length) mcp.tools = priorMcp.tools;
  const servers = _govChipsGet('govUserMcpServers');
  if (servers.length) mcp.servers = servers;
  if (Object.keys(mcp).length) grants.mcp = mcp;
  const cli = {};
  const priorCli = (prior.cli && typeof prior.cli === 'object') ? prior.cli : {};
  if (Array.isArray(priorCli.workdir_roots) && priorCli.workdir_roots.length) cli.workdir_roots = priorCli.workdir_roots;
  const commands = _govChipsGet('govUserCliCommands');
  if (commands.length) cli.commands = commands;
  const approvalCommands = _govChipsGet('govUserCliApproval');
  if (approvalCommands.length) cli.approval_commands = approvalCommands;
  if (Object.keys(cli).length) grants.cli = cli;
  return Object.keys(grants).length ? grants : null;
}

/**
 * Build the deny object from the off-toggle chip fields, or null when empty.
 * The single "skills off" field writes both deny.skills.view and .load so an
 * off-toggle really switches the skill off; deny keys the form does not edit
 * (permissions, routes, skills.manage, mcp.tools, cli.workdir_roots, ...) are
 * carried over from the entry being edited so a save never drops them.
 */
function _govCollectUserDeny() {
  const existing = (_govEditingUser && (window.__GOV_USERS__ || {})[_govEditingUser]) || {};
  const prior = (existing.deny && typeof existing.deny === 'object') ? existing.deny : {};
  const deny = {};
  for (const k of Object.keys(prior)) {
    if (k !== 'skills' && k !== 'mcp' && k !== 'cli') deny[k] = prior[k];
  }
  const skills = {};
  const priorSkills = (prior.skills && typeof prior.skills === 'object') ? prior.skills : {};
  const skillsOff = _govChipsGet('govUserDenySkills');
  if (skillsOff.length) {
    skills.view = skillsOff.slice();
    skills.load = skillsOff.slice();
  }
  if (Array.isArray(priorSkills.manage) && priorSkills.manage.length) skills.manage = priorSkills.manage;
  if (Object.keys(skills).length) deny.skills = skills;
  const mcp = {};
  const priorMcp = (prior.mcp && typeof prior.mcp === 'object') ? prior.mcp : {};
  if (priorMcp.tools && Object.keys(priorMcp.tools).length) mcp.tools = priorMcp.tools;
  const servers = _govChipsGet('govUserDenyMcp');
  if (servers.length) mcp.servers = servers;
  if (Object.keys(mcp).length) deny.mcp = mcp;
  const cli = {};
  const priorCli = (prior.cli && typeof prior.cli === 'object') ? prior.cli : {};
  if (Array.isArray(priorCli.workdir_roots) && priorCli.workdir_roots.length) cli.workdir_roots = priorCli.workdir_roots;
  const commands = _govChipsGet('govUserDenyCli');
  if (commands.length) cli.commands = commands;
  if (Object.keys(cli).length) deny.cli = cli;
  return Object.keys(deny).length ? deny : null;
}

async function _govSaveUser() {
  const email = String(($('govUserEmail') || {}).value || '').trim().toLowerCase();
  if (!email || !email.includes('@')) {
    if (typeof showToast === 'function') showToast(_govT('governance_invalid_email', 'Enter a valid email address'), 3000, 'error');
    return;
  }
  const entry = {
    roles: _govCsv(($('govUserRoles') || {}).value),
    groups: _govCsv(($('govUserGroups') || {}).value),
  };
  const grants = _govCollectUserGrants();
  if (grants) entry.grants = grants;
  const deny = _govCollectUserDeny();
  if (deny) entry.deny = deny;
  const path = _govEditingUser ? '/api/governance/users/update' : '/api/governance/users';
  try {
    const res = await _govPost(path, { email: email, entry: entry });
    _govEtag = res.etag || _govEtag;
    if (typeof showToast === 'function') showToast(_govT('governance_saved', 'Saved'), 2500);
    await _govLoadUsers();
  } catch (e) {
    if (!_govHandleConflict(e) && typeof showToast === 'function') showToast(e.message || 'save failed', 4000, 'error');
  }
}

async function _govDeleteUser(email) {
  try {
    const res = await _govPost('/api/governance/users/delete', { email: email });
    _govEtag = res.etag || _govEtag;
    if (typeof showToast === 'function') showToast(_govT('governance_deleted', 'Deleted'), 2500);
    await _govLoadUsers();
  } catch (e) {
    if (!_govHandleConflict(e) && typeof showToast === 'function') showToast(e.message || 'delete failed', 4000, 'error');
  }
}

// ── Groups tab ────────────────────────────────────────────────────────────

async function _govLoadGroups() {
  const el = $('govPaneGroups');
  if (!el) return;
  el.innerHTML = '<div class="gov-muted">' + _govT('loading', 'Loading...') + '</div>';
  let data;
  try {
    data = await api('/api/governance/groups', { redirect401: false });
  } catch (e) {
    _govError(e, 'govPaneGroups');
    return;
  }
  _govEtag = data.etag || _govEtag;
  const groups = data.groups || {};
  const rows = Object.keys(groups).sort().map(name => {
    const entry = groups[name] || {};
    return '<tr>' +
      '<td>' + _govEsc(name) + '</td>' +
      '<td>' + _govEsc((entry.sso_groups || []).join(', ')) + '</td>' +
      '<td>' + _govEsc((entry.roles || []).join(', ')) + '</td>' +
      '<td class="gov-row-actions">' +
        '<button type="button" class="gov-btn" onclick="_govEditGroup(' + _govEsc(JSON.stringify(name)) + ')">' + _govT('governance_edit', 'Edit') + '</button>' +
        '<button type="button" class="gov-btn danger" onclick="_govDeleteGroup(' + _govEsc(JSON.stringify(name)) + ')">' + _govT('governance_delete', 'Delete') + '</button>' +
      '</td></tr>';
  }).join('');
  window.__GOV_GROUPS__ = groups;
  el.innerHTML =
    '<table class="gov-table"><thead><tr>' +
      '<th>' + _govT('governance_col_name', 'Name') + '</th>' +
      '<th>' + _govT('governance_col_sso_groups', 'SSO groups') + '</th>' +
      '<th>' + _govT('governance_col_roles', 'Roles') + '</th><th></th>' +
    '</tr></thead><tbody>' + (rows || '<tr><td colspan="4" class="gov-muted">' + _govT('governance_no_groups', 'No group entries in the policy.') + '</td></tr>') + '</tbody></table>' +
    '<div class="gov-form" id="govGroupForm">' +
      '<div class="gov-form-title" id="govGroupFormTitle">' + _govT('governance_group_add', 'Add group') + '</div>' +
      '<div class="gov-form-row"><label for="govGroupName">' + _govT('governance_col_name', 'Name') + '</label>' +
        '<input id="govGroupName" type="text" placeholder="sw-engineering"></div>' +
      '<div class="gov-form-row"><label for="govGroupSso">' + _govT('governance_sso_csv', 'SSO groups (comma separated)') + '</label>' +
        '<input id="govGroupSso" type="text" placeholder="engineering@example.com"></div>' +
      '<div class="gov-form-row"><label for="govGroupRoles">' + _govT('governance_roles_csv', 'Roles (comma separated)') + '</label>' +
        '<input id="govGroupRoles" type="text" placeholder="operator"></div>' +
      '<div class="gov-form-actions">' +
        '<button type="button" class="gov-btn primary" onclick="_govSaveGroup()">' + _govT('governance_save', 'Save') + '</button>' +
        '<button type="button" class="gov-btn" onclick="_govResetGroupForm()">' + _govT('governance_cancel', 'Cancel') + '</button>' +
      '</div>' +
    '</div>';
  _govResetGroupForm();
}

function _govResetGroupForm() {
  _govEditingGroup = null;
  const title = $('govGroupFormTitle');
  if (title) title.textContent = _govT('governance_group_add', 'Add group');
  const name = $('govGroupName');
  if (name) { name.value = ''; name.disabled = false; }
  const sso = $('govGroupSso');
  if (sso) sso.value = '';
  const roles = $('govGroupRoles');
  if (roles) roles.value = '';
}

function _govEditGroup(name) {
  const entry = (window.__GOV_GROUPS__ || {})[name] || {};
  _govEditingGroup = name;
  const title = $('govGroupFormTitle');
  if (title) title.textContent = _govT('governance_group_edit', 'Edit group');
  const nameEl = $('govGroupName');
  if (nameEl) { nameEl.value = name; nameEl.disabled = true; }
  const sso = $('govGroupSso');
  if (sso) sso.value = (entry.sso_groups || []).join(', ');
  const roles = $('govGroupRoles');
  if (roles) roles.value = (entry.roles || []).join(', ');
}

async function _govSaveGroup() {
  const name = String(($('govGroupName') || {}).value || '').trim();
  if (!name) {
    if (typeof showToast === 'function') showToast(_govT('governance_invalid_name', 'Enter a group name'), 3000, 'error');
    return;
  }
  const entry = {
    sso_groups: _govCsv(($('govGroupSso') || {}).value),
    roles: _govCsv(($('govGroupRoles') || {}).value),
  };
  const path = _govEditingGroup ? '/api/governance/groups/update' : '/api/governance/groups';
  try {
    const res = await _govPost(path, { name: name, entry: entry });
    _govEtag = res.etag || _govEtag;
    if (typeof showToast === 'function') showToast(_govT('governance_saved', 'Saved'), 2500);
    await _govLoadGroups();
  } catch (e) {
    if (!_govHandleConflict(e) && typeof showToast === 'function') showToast(e.message || 'save failed', 4000, 'error');
  }
}

async function _govDeleteGroup(name) {
  try {
    const res = await _govPost('/api/governance/groups/delete', { name: name });
    _govEtag = res.etag || _govEtag;
    if (typeof showToast === 'function') showToast(_govT('governance_deleted', 'Deleted'), 2500);
    await _govLoadGroups();
  } catch (e) {
    if (!_govHandleConflict(e) && typeof showToast === 'function') showToast(e.message || 'delete failed', 4000, 'error');
  }
}

// ── Workspaces tab ────────────────────────────────────────────────────────
// Admin management of workspace ownership: owner_email plus members on the
// entries in the per-profile workspaces.json. Data comes from GET
// /api/workspaces (an admin caller receives EVERY entry including
// owner_email, members and the legacy_unowned annotation) and every write
// goes through POST /api/workspaces/assign (admin-only, enforced server
// side). NOTE: unlike /api/governance/* these routes are NOT etag-guarded,
// so mutations are plain api() POSTs without If-Match (last write wins on
// the workspaces store). The tab button and pane are injected here because
// the static markup for the governance panel lives in index.html.

let _govWsUserFilter = '';   // lowercased email of the per-user lens, '' = off

function _govEnsureWorkspacesTab() {
  const bar = document.querySelector('#mainGovernance .gov-tab-bar');
  const content = document.querySelector('#mainGovernance .gov-content');
  if (!bar || !content) return;
  if (!bar.querySelector('[data-gov-tab="workspaces"]')) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'gov-tab';
    btn.dataset.govTab = 'workspaces';
    btn.textContent = 'Workspaces';
    btn.addEventListener('click', () => { _govSwitchTab('workspaces'); });
    bar.insertBefore(btn, bar.querySelector('[data-gov-tab="approvals"]') || null);
  }
  if (!document.getElementById('govPaneWorkspaces')) {
    const pane = document.createElement('div');
    pane.className = 'gov-tab-pane';
    pane.id = 'govPaneWorkspaces';
    content.appendChild(pane);
  }
}

async function _govLoadWorkspaces() {
  const el = $('govPaneWorkspaces');
  if (!el) return;
  el.innerHTML = '<div class="gov-muted">' + _govT('loading', 'Loading...') + '</div>';
  let data;
  try {
    data = await api('/api/workspaces', { redirect401: false });
  } catch (e) {
    _govError(e, 'govPaneWorkspaces');
    return;
  }
  window.__GOV_WS__ = Array.isArray(data.workspaces) ? data.workspaces : [];
  window.__GOV_WS_ADMIN__ = !!data.viewer_is_admin;
  _govRenderWorkspaces();
}

/** All known emails for the per-user datalist: workspace owners plus members
 *  plus policy users (when the users tab already cached them). */
function _govWsKnownEmails() {
  const out = new Set();
  (window.__GOV_WS__ || []).forEach(w => {
    const owner = String(w.owner_email || '').trim().toLowerCase();
    if (owner) out.add(owner);
    (Array.isArray(w.members) ? w.members : []).forEach(m => {
      const email = String(m || '').trim().toLowerCase();
      if (email) out.add(email);
    });
  });
  Object.keys(window.__GOV_USERS__ || {}).forEach(email => {
    const norm = String(email || '').trim().toLowerCase();
    if (norm) out.add(norm);
  });
  return Array.from(out).sort();
}

function _govWsMembersLower(w) {
  return (Array.isArray(w.members) ? w.members : []).map(m => String(m || '').trim().toLowerCase()).filter(Boolean);
}

function _govRenderWorkspaces() {
  const el = $('govPaneWorkspaces');
  if (!el) return;
  const list = window.__GOV_WS__ || [];
  const isAdmin = !!window.__GOV_WS_ADMIN__;
  const filter = _govWsUserFilter;
  const options = _govWsKnownEmails().map(email => '<option value="' + _govEsc(email) + '"></option>').join('');
  const lensHeader = filter ? '<th>' + _govEsc(filter) + '</th>' : '';
  const rows = list.map((w, idx) => {
    const owner = String(w.owner_email || '').trim().toLowerCase();
    const members = _govWsMembersLower(w);
    const legacyBadge = w.legacy_unowned ? ' <span class="gov-chip">Legacy shared</span>' : '';
    let lensCell = '';
    if (filter) {
      let state, action = '';
      if (owner === filter) {
        state = '<span class="gov-chip">Owner</span>';
      } else if (members.includes(filter)) {
        state = '<span class="gov-chip">Member</span>';
        if (isAdmin) action = ' <button type="button" class="gov-btn danger" onclick="_govWsToggleMember(' + idx + ', false)">Remove ' + _govEsc(filter) + '</button>';
      } else {
        state = w.legacy_unowned
          ? '<span class="gov-muted">Shared (legacy)</span>'
          : '<span class="gov-muted">No access</span>';
        if (isAdmin) action = ' <button type="button" class="gov-btn primary" onclick="_govWsToggleMember(' + idx + ', true)">Add ' + _govEsc(filter) + '</button>';
      }
      lensCell = '<td class="gov-nowrap">' + state + action + '</td>';
    }
    const ownerCell = isAdmin
      ? '<input id="govWsOwner_' + idx + '" type="text" placeholder="owner@example.com" value="' + _govEsc(owner) + '">'
      : (_govEsc(owner) || '<span class="gov-muted">Shared (unowned)</span>');
    const membersCell = isAdmin
      ? '<input id="govWsMembers_' + idx + '" type="text" placeholder="a@example.com, b@example.com" value="' + _govEsc(members.join(', ')) + '">'
      : (_govEsc(members.join(', ')) || '<span class="gov-muted">none</span>');
    const actionsCell = isAdmin
      ? '<td class="gov-row-actions"><button type="button" class="gov-btn primary" onclick="_govSaveWorkspaceAssign(' + idx + ')">Save</button></td>'
      : '<td></td>';
    return '<tr>' +
      '<td>' + _govEsc(w.name || '') + legacyBadge + '</td>' +
      '<td class="gov-path">' + _govEsc(w.path || '') + '</td>' +
      '<td>' + ownerCell + '</td>' +
      '<td>' + membersCell + '</td>' +
      lensCell +
      actionsCell +
    '</tr>';
  }).join('');
  const colCount = filter ? 6 : 5;
  el.innerHTML =
    '<div class="gov-form">' +
      '<div class="gov-form-title">Per-user view</div>' +
      '<div class="gov-form-row"><label for="govWsUserFilter">User email</label>' +
        '<input id="govWsUserFilter" type="text" list="govWsUserEmails" placeholder="name@example.com" value="' + _govEsc(filter) + '" onchange="_govApplyWsUserFilter()"></div>' +
      '<datalist id="govWsUserEmails">' + options + '</datalist>' +
      '<div class="gov-form-actions">' +
        '<button type="button" class="gov-btn primary" onclick="_govApplyWsUserFilter()">Apply</button>' +
        '<button type="button" class="gov-btn" onclick="_govClearWsUserFilter()">Clear</button>' +
      '</div>' +
    '</div>' +
    (isAdmin ? '' : '<div class="gov-muted">You are not a workspace admin: the list below only shows your own entries and editing is disabled.</div>') +
    '<table class="gov-table"><thead><tr>' +
      '<th>Name</th><th>Path</th><th>Owner</th><th>Members</th>' + lensHeader + '<th></th>' +
    '</tr></thead><tbody>' +
    (rows || '<tr><td colspan="' + colCount + '" class="gov-muted">No workspaces configured.</td></tr>') +
    '</tbody></table>' +
    '<div class="gov-muted">Owner and members control who sees a workspace. An entry without either is legacy shared: visible to every signed-in user. Clearing the owner field returns an entry to legacy shared.</div>';
}

function _govApplyWsUserFilter() {
  _govWsUserFilter = String(($('govWsUserFilter') || {}).value || '').trim().toLowerCase();
  _govRenderWorkspaces();
}

function _govClearWsUserFilter() {
  _govWsUserFilter = '';
  _govRenderWorkspaces();
}

/** POST /api/workspaces/assign and refresh the cached list from the reply. */
async function _govWsAssign(body, okMsg) {
  try {
    const res = await api('/api/workspaces/assign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      redirect401: false,
    });
    if (Array.isArray(res.workspaces)) window.__GOV_WS__ = res.workspaces;
    if (typeof showToast === 'function') showToast(okMsg, 2500);
    _govRenderWorkspaces();
  } catch (e) {
    // 403 forbidden (not a workspace admin) or 400 validation from the server
    let msg = (e && e.message) ? e.message : 'request failed';
    if (e && Number(e.status) === 403 && (e.reason || e.resource)) {
      msg = 'Access restricted' + (e.resource ? ': ' + e.resource : '') + (e.reason ? ' (' + e.reason + ')' : '');
    }
    if (typeof showToast === 'function') showToast('Ownership save failed: ' + msg, 4000, 'error');
  }
}

async function _govSaveWorkspaceAssign(idx) {
  const w = (window.__GOV_WS__ || [])[idx];
  if (!w) return;
  const owner = String(($('govWsOwner_' + idx) || {}).value || '').trim().toLowerCase();
  const seen = new Set();
  const members = _govCsv(($('govWsMembers_' + idx) || {}).value)
    .map(m => m.toLowerCase())
    .filter(m => (seen.has(m) ? false : (seen.add(m), true)));
  // owner_email '' clears the owner (back to legacy shared); [] clears members
  await _govWsAssign({ path: w.path, owner_email: owner, members: members }, 'Ownership saved');
}

/** Quick add/remove of the per-user lens email as a member. Owner untouched
 *  (the request only carries the members key, so owner_email is unchanged). */
async function _govWsToggleMember(idx, add) {
  const w = (window.__GOV_WS__ || [])[idx];
  const email = _govWsUserFilter;
  if (!w || !email) return;
  const members = _govWsMembersLower(w).filter(m => m !== email);
  if (add) members.push(email);
  await _govWsAssign({ path: w.path, members: members }, add ? 'Member added' : 'Member removed');
}

// ── Approvals tab ─────────────────────────────────────────────────────────
// Pending user-added skills (api/skill_ownership registry). Approve makes a
// skill global; reject deletes it from disk. Server-gated by governance:write.

function _govUpdateApprovalsBadge(count) {
  const badge = $('govApprovalsBadge');
  if (!badge) return;
  const n = Number(count) || 0;
  badge.textContent = n > 0 ? String(n) : '';
  badge.style.display = n > 0 ? '' : 'none';
}

/** Refresh the pending-count badge without switching to the tab. */
async function _govRefreshApprovalsBadge() {
  try {
    const data = await api('/api/governance/approvals', { redirect401: false, timeoutToast: false, timeoutMs: 15000 });
    _govUpdateApprovalsBadge((data.pending || []).length);
  } catch (e) { /* not an admin or endpoint unavailable; leave badge hidden */ }
}

async function _govLoadApprovals() {
  const el = $('govPaneApprovals');
  if (!el) return;
  el.innerHTML = '<div class="gov-muted">' + _govT('loading', 'Loading...') + '</div>';
  let data;
  try {
    data = await api('/api/governance/approvals', { redirect401: false });
  } catch (e) {
    _govError(e, 'govPaneApprovals');
    return;
  }
  const pending = data.pending || [];
  _govUpdateApprovalsBadge(pending.length);
  const rows = pending.map(item => {
    let when = '';
    const ts = Number(item.added_at);
    if (Number.isFinite(ts) && ts > 0) when = new Date(ts * 1000).toLocaleString();
    return '<tr>' +
      '<td>' + _govEsc(item.key || '') + '</td>' +
      '<td>' + _govEsc(item.owner_email || '') + '</td>' +
      '<td class="gov-nowrap">' + _govEsc(when) + '</td>' +
      '<td class="gov-row-actions">' +
        '<button type="button" class="gov-btn primary" onclick="_govDecideApproval(' + _govEsc(JSON.stringify(item.key)) + ', \'approve\')">' + _govT('governance_approve', 'Approve') + '</button>' +
        '<button type="button" class="gov-btn danger" onclick="_govDecideApproval(' + _govEsc(JSON.stringify(item.key)) + ', \'reject\')">' + _govT('governance_reject', 'Reject') + '</button>' +
      '</td></tr>';
  }).join('');
  el.innerHTML =
    '<table class="gov-table"><thead><tr>' +
      '<th>' + _govT('governance_col_skill', 'Skill') + '</th>' +
      '<th>' + _govT('governance_col_added_by', 'Added by') + '</th>' +
      '<th>' + _govT('governance_col_added_at', 'Added') + '</th><th></th>' +
    '</tr></thead><tbody>' +
    (rows || '<tr><td colspan="4" class="gov-muted">' + _govT('governance_no_pending', 'No pending skill approvals.') + '</td></tr>') +
    '</tbody></table>' +
    '<div class="gov-muted">' + _govT('governance_approvals_note',
      'Approve makes the skill available to every user. Reject deletes the skill from disk.') + '</div>';
}

async function _govDecideApproval(key, decision) {
  try {
    await _govPost('/api/governance/approvals/decide', { kind: 'skill', key: key, decision: decision });
    if (typeof showToast === 'function') {
      showToast(decision === 'approve' ? _govT('governance_approved', 'Approved') : _govT('governance_rejected', 'Rejected'), 2500);
    }
    await _govLoadApprovals();
  } catch (e) {
    if (!_govHandleConflict(e) && typeof showToast === 'function') showToast(e.message || 'decision failed', 4000, 'error');
  }
}

// ── Preview access tab ────────────────────────────────────────────────────

async function _govRunPreview() {
  const out = $('govPreviewResult');
  if (!out) return;
  const email = String(($('govPreviewEmail') || {}).value || '').trim();
  if (!email || !email.includes('@')) {
    out.innerHTML = '<div class="gov-error">' + _govT('governance_invalid_email', 'Enter a valid email address') + '</div>';
    return;
  }
  const groups = _govCsv(($('govPreviewGroups') || {}).value);
  out.innerHTML = '<div class="gov-muted">' + _govT('loading', 'Loading...') + '</div>';
  let data;
  try {
    data = await api('/api/governance/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(groups.length ? { email: email, groups: groups } : { email: email }),
      redirect401: false,
    });
  } catch (e) {
    _govError(e, 'govPreviewResult');
    return;
  }
  const access = data.effective_access || {};
  const chips = list => (list || []).map(v => '<span class="gov-chip">' + _govEsc(v) + '</span>').join(' ') ||
    '<span class="gov-muted">' + _govT('governance_none', 'none') + '</span>';
  const section = (label, body) => '<div class="gov-preview-section"><div class="gov-form-title">' + _govEsc(label) + '</div>' + body + '</div>';
  out.innerHTML =
    section(_govT('governance_col_roles', 'Roles'), chips(access.roles)) +
    section(_govT('governance_col_groups', 'Groups'), chips(access.groups)) +
    section(_govT('governance_permissions', 'Permissions'), chips(access.permissions)) +
    section(_govT('governance_profiles', 'Profiles'), chips(access.profiles)) +
    section(_govT('governance_routes', 'Routes'), chips(access.routes)) +
    section(_govT('governance_grant_sources', 'Grant sources'), chips(data.grant_sources));
}

// ── Audit tab ─────────────────────────────────────────────────────────────

async function _govLoadAudit() {
  const el = $('govPaneAudit');
  if (!el) return;
  el.innerHTML = '<div class="gov-muted">' + _govT('loading', 'Loading...') + '</div>';
  let data;
  try {
    data = await api('/api/governance/audit?limit=100', { redirect401: false });
  } catch (e) {
    _govError(e, 'govPaneAudit');
    return;
  }
  const rows = (data.events || []).map(ev => {
    let when = String(ev.ts || '');
    const parsed = Date.parse(when);
    if (Number.isFinite(parsed)) when = new Date(parsed).toLocaleString();
    const subject = String(ev.subject_email_hash || '').slice(0, 8);
    return '<tr>' +
      '<td class="gov-nowrap">' + _govEsc(when) + '</td>' +
      '<td>' + _govEsc(ev.event || '') + '</td>' +
      '<td>' + _govEsc(ev.reason || '') + '</td>' +
      '<td>' + _govEsc(ev.method || '') + '</td>' +
      '<td class="gov-path">' + _govEsc(ev.path || '') + '</td>' +
      '<td class="gov-nowrap">' + _govEsc(subject) + '</td>' +
    '</tr>';
  }).join('');
  el.innerHTML =
    '<div class="gov-form-actions gov-audit-actions">' +
      '<button type="button" class="gov-btn" onclick="_govLoadAudit()">' + _govT('governance_refresh', 'Refresh') + '</button>' +
    '</div>' +
    '<table class="gov-table"><thead><tr>' +
      '<th>' + _govT('governance_col_time', 'Time') + '</th>' +
      '<th>' + _govT('governance_col_event', 'Event') + '</th>' +
      '<th>' + _govT('governance_col_reason', 'Reason') + '</th>' +
      '<th>' + _govT('governance_col_method', 'Method') + '</th>' +
      '<th>' + _govT('governance_col_path', 'Path') + '</th>' +
      '<th>' + _govT('governance_col_subject', 'Subject') + '</th>' +
    '</tr></thead><tbody>' +
    (rows || '<tr><td colspan="6" class="gov-muted">' + _govT('governance_no_events', 'No audit events yet.') + '</td></tr>') +
    '</tbody></table>';
}

// ── Boot: hide/show the nav buttons based on the caller's access ──────────

document.addEventListener('DOMContentLoaded', () => {
  _govFetchMe().then(govApplyVisibility).catch(() => {});
});
