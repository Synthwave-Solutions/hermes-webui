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
  _govRefreshApprovalsBadge();
  await _govSwitchTab(_govTab || 'overview');
  return true;
}

async function _govSwitchTab(name) {
  const tab = ['overview', 'users', 'groups', 'approvals', 'preview', 'audit'].includes(name) ? name : 'overview';
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
      '<div class="gov-form-row"><label for="govUserSkillsView">' + _govT('governance_grants_skills_view', 'Skills view (comma separated)') + '</label>' +
        '<input id="govUserSkillsView" type="text" placeholder="my-skill, *"></div>' +
      '<div class="gov-form-row"><label for="govUserSkillsLoad">' + _govT('governance_grants_skills_load', 'Skills load (comma separated)') + '</label>' +
        '<input id="govUserSkillsLoad" type="text" placeholder="my-skill"></div>' +
      '<div class="gov-form-row"><label for="govUserSkillsManage">' + _govT('governance_grants_skills_manage', 'Skills manage (comma separated)') + '</label>' +
        '<input id="govUserSkillsManage" type="text" placeholder="my-skill"></div>' +
      '<div class="gov-form-row"><label for="govUserMcpServers">' + _govT('governance_grants_mcp_servers', 'MCP servers (comma separated)') + '</label>' +
        '<input id="govUserMcpServers" type="text" placeholder="notion, playwright"></div>' +
      '<div class="gov-form-row"><label for="govUserCliCommands">' + _govT('governance_grants_cli_commands', 'CLI commands (comma separated)') + '</label>' +
        '<input id="govUserCliCommands" type="text" placeholder="git, gh"></div>' +
      '<div class="gov-form-actions">' +
        '<button type="button" class="gov-btn primary" onclick="_govSaveUser()">' + _govT('governance_save', 'Save') + '</button>' +
        '<button type="button" class="gov-btn" onclick="_govResetUserForm()">' + _govT('governance_cancel', 'Cancel') + '</button>' +
      '</div>' +
    '</div>';
  _govResetUserForm();
}

const _GOV_USER_GRANT_FIELDS = ['govUserSkillsView', 'govUserSkillsLoad', 'govUserSkillsManage', 'govUserMcpServers', 'govUserCliCommands'];

function _govSetInput(id, value) {
  const el = $(id);
  if (el) el.value = value;
}

function _govResetUserForm() {
  _govEditingUser = null;
  const title = $('govUserFormTitle');
  if (title) title.textContent = _govT('governance_user_add', 'Add user');
  const email = $('govUserEmail');
  if (email) { email.value = ''; email.disabled = false; }
  const roles = $('govUserRoles');
  if (roles) roles.value = '';
  const groups = $('govUserGroups');
  if (groups) groups.value = '';
  _GOV_USER_GRANT_FIELDS.forEach(id => _govSetInput(id, ''));
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
  _govSetInput('govUserSkillsView', (skills.view || []).join(', '));
  _govSetInput('govUserSkillsLoad', (skills.load || []).join(', '));
  _govSetInput('govUserSkillsManage', (skills.manage || []).join(', '));
  _govSetInput('govUserMcpServers', (mcp.servers || []).join(', '));
  // cli.commands entries may be strings or {id/argv0} objects per the policy schema
  const commands = (cli.commands || []).map(c => (typeof c === 'string') ? c : ((c && (c.id || c.argv0)) || '')).filter(Boolean);
  _govSetInput('govUserCliCommands', commands.join(', '));
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
  const view = _govCsv(($('govUserSkillsView') || {}).value);
  const load = _govCsv(($('govUserSkillsLoad') || {}).value);
  const manage = _govCsv(($('govUserSkillsManage') || {}).value);
  if (view.length) skills.view = view;
  if (load.length) skills.load = load;
  if (manage.length) skills.manage = manage;
  if (Object.keys(skills).length) grants.skills = skills;
  const mcp = {};
  const priorMcp = (prior.mcp && typeof prior.mcp === 'object') ? prior.mcp : {};
  if (priorMcp.tools && Object.keys(priorMcp.tools).length) mcp.tools = priorMcp.tools;
  const servers = _govCsv(($('govUserMcpServers') || {}).value);
  if (servers.length) mcp.servers = servers;
  if (Object.keys(mcp).length) grants.mcp = mcp;
  const cli = {};
  const priorCli = (prior.cli && typeof prior.cli === 'object') ? prior.cli : {};
  if (Array.isArray(priorCli.workdir_roots) && priorCli.workdir_roots.length) cli.workdir_roots = priorCli.workdir_roots;
  const commands = _govCsv(($('govUserCliCommands') || {}).value);
  if (commands.length) cli.commands = commands;
  if (Object.keys(cli).length) grants.cli = cli;
  return Object.keys(grants).length ? grants : null;
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
