// ── Projects hub panel (ticket 12) ────────────────────────────────────────
// A read-only view of what THIS workstation holds about a project, fed by
// GET /api/projects/hub and /api/projects/hub/detail (see api/projects_hub.py).
//
// Three properties of the payload this file must not undo:
//
// * Every row is filtered server-side. Nothing here re-filters, and nothing
//   here ever adds a row the server did not send.
// * A section MISSING from the payload is missing because the caller does not
//   hold the permission that guards the same data on its own route. The client
//   never re-adds it, and never renders a placeholder that hints it exists.
// * An empty section carries the server's own `empty_reason`, and an
//   unconnected source carries its own `seam` sentence. Both are rendered
//   verbatim: an invented "0" would read as "there is nothing", when the truth
//   is usually "nothing is connected yet".
//
// A failed or refused request renders the neutral projects_unavailable state.
// No toast: a role whose route allowlist omits this endpoint would otherwise
// be nagged on every panel open about something it cannot change.

let _projHub = null;        // last /api/projects/hub payload
let _projDetail = null;     // last /api/projects/hub/detail payload
let _projSelectedId = '';   // project_id currently open in the main view

function _projEsc(s) {
  if (typeof _escHtml === 'function') return _escHtml(s);
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function _projT(key, fallback) {
  const val = (typeof t === 'function') ? t(key) : key;
  return (val && val !== key) ? val : fallback;
}

// Absolute timestamps only, formatted by the browser's own locale: the server
// deliberately sends no pre-rendered date strings.
function _projWhen(ts) {
  const seconds = Number(ts || 0);
  if (!Number.isFinite(seconds) || seconds <= 0) return '';
  try {
    return new Date(seconds * 1000).toLocaleDateString();
  } catch (e) {
    return '';
  }
}

function _projChip(source) {
  const label = _projT('projects_source_' + String(source || ''), String(source || ''));
  return '<span class="proj-chip">' + _projEsc(String(label)) + '</span>';
}

function _projUnavailable() {
  const text = _projT('projects_unavailable', 'This view is not available for your account.');
  const list = $('projectsPanelList');
  if (list) list.innerHTML = '<div class="proj-empty">' + _projEsc(String(text)) + '</div>';
  const body = $('projDetailBody');
  const empty = $('projDetailEmpty');
  if (body) body.style.display = 'none';
  if (empty) empty.style.display = '';
}

/**
 * Panel entry point, called by switchPanel and the two refresh buttons.
 * Returns false when the hub could not be read, without raising.
 */
async function loadProjectsHub() {
  const list = $('projectsPanelList');
  if (list) list.innerHTML = '<div class="proj-empty">' + _projEsc(_projT('loading', 'Loading...')) + '</div>';
  try {
    _projHub = await api('/api/projects/hub', { redirect401: false, timeoutToast: false });
  } catch (e) {
    _projHub = null;
    _projUnavailable();
    return false;
  }
  _projRenderList();
  _projRenderIntegrations();
  if (_projSelectedId) await _projOpen(_projSelectedId);
  return true;
}

function _projRenderList() {
  const list = $('projectsPanelList');
  if (!list) return;
  const rows = (_projHub && Array.isArray(_projHub.projects)) ? _projHub.projects : [];
  if (!rows.length) {
    list.innerHTML = '<div class="proj-empty">'
      + _projEsc(_projT('projects_none_yet', 'You do not have any projects on this workstation yet.'))
      + '</div>';
    return;
  }
  list.innerHTML = rows.map(p => {
    const meta = [];
    meta.push(String(p.conversation_count || 0) + ' '
      + _projT('projects_section_conversations', 'Conversations').toLowerCase());
    if (p.workspace_count) {
      meta.push(String(p.workspace_count) + ' '
        + _projT('projects_section_workspaces', 'Spaces').toLowerCase());
    }
    const when = _projWhen(p.last_activity_at);
    if (when) meta.push(when);
    const system = p.system
      ? '<span class="proj-chip">' + _projEsc(_projT('projects_system_label', 'System')) + '</span>'
      : '';
    const dot = p.color
      ? ' style="background:' + _projEsc(String(p.color)) + '"'
      : '';
    return '<div class="proj-row' + (p.project_id === _projSelectedId ? ' active' : '')
      + '" onclick="_projOpen(\'' + _projEsc(String(p.project_id)) + '\')">'
      + '<span class="proj-dot"' + dot + '></span>'
      + '<div class="proj-row-main">'
      + '<div class="proj-row-name">' + _projEsc(String(p.name)) + '</div>'
      + '<div class="proj-row-meta">' + _projEsc(meta.join(' · ')) + '</div>'
      + '</div>' + system + '</div>';
  }).join('');
}

async function _projOpen(projectId) {
  _projSelectedId = String(projectId || '');
  _projRenderList();
  try {
    _projDetail = await api(
      '/api/projects/hub/detail?project_id=' + encodeURIComponent(_projSelectedId),
      { redirect401: false, timeoutToast: false });
  } catch (e) {
    _projDetail = null;
    _projUnavailable();
    return false;
  }
  _projRenderDetail();
  return true;
}

function _projSectionCard(titleKey, titleFallback, section, rowRenderer) {
  // A section the server did not send is a section this caller is not entitled
  // to see. Render nothing at all: an "empty" card would still disclose that
  // the data exists.
  if (!section) return '';
  const items = Array.isArray(section.items) ? section.items : [];
  let body;
  if (!items.length) {
    body = '<div class="proj-empty">'
      + _projEsc(String(section.empty_reason || _projT('projects_none_yet', 'Nothing here yet.')))
      + '</div>';
  } else {
    body = items.map(rowRenderer).join('');
    if (section.truncated) {
      body += '<div class="proj-empty">'
        + _projEsc(_projT('projects_truncated', 'Only the first entries are shown.')) + '</div>';
    }
  }
  return '<div class="proj-card"><div class="proj-card-title">'
    + _projEsc(_projT(titleKey, titleFallback))
    + _projChip(section.source) + '</div>' + body + '</div>';
}

function _projRenderDetail() {
  const body = $('projDetailBody');
  const empty = $('projDetailEmpty');
  const summary = $('projSummary');
  const sections = $('projSections');
  if (!_projDetail) {
    if (body) body.style.display = 'none';
    if (empty) empty.style.display = '';
    return;
  }
  if (body) body.style.display = '';
  if (empty) empty.style.display = 'none';

  const p = _projDetail.project || {};
  if (summary) {
    summary.innerHTML = '<div class="proj-card"><div class="proj-card-title">'
      + _projEsc(String(p.name)) + _projChip(p.source)
      + (p.system ? '<span class="proj-chip">' + _projEsc(_projT('projects_system_label', 'System')) + '</span>' : '')
      + '</div><div class="proj-state">'
      + _projEsc(_projT('projects_subtitle', 'A read-only view of what this workstation knows about each project.'))
      + '</div></div>';
  }

  let html = '';
  html += _projSectionCard(
    'projects_section_conversations', 'Conversations', _projDetail.conversations,
    s => '<div class="proj-item"><span class="proj-item-name">'
      + _projEsc(String(s.title)) + '</span><span class="proj-state">'
      + _projEsc(_projWhen(s.last_activity_at)) + '</span></div>');
  html += _projSectionCard(
    'projects_section_workspaces', 'Spaces', _projDetail.workspaces,
    w => '<div class="proj-item"><span class="proj-item-name">'
      + _projEsc(String(w.name)) + '</span></div>');
  html += _projSectionCard(
    'projects_section_files', 'Files', _projDetail.files,
    f => '<div class="proj-item"><span class="proj-item-name">'
      + _projEsc(String(f.name)) + '</span><span class="proj-state">'
      + _projEsc(String(f.workspace)) + '</span></div>');
  html += _projSectionCard(
    'projects_section_jobs', 'Scheduled work', _projDetail.jobs,
    j => '<div class="proj-item"><span class="proj-item-name">'
      + _projEsc(String(j.name)) + '</span><span class="proj-state">'
      + _projEsc(String(j.schedule)) + '</span></div>');
  html += _projSectionCard(
    'projects_section_status', 'Status', _projDetail.status,
    i => '<div class="proj-item"><span class="proj-item-name">'
      + _projEsc(String(i.summary)) + '</span><span class="proj-state">'
      + _projEsc(String(i.workspace)) + '</span></div>');

  const delivery = _projDetail.delivery;
  if (delivery) {
    html += '<div class="proj-card"><div class="proj-card-title">'
      + _projEsc(_projT('projects_section_delivery', 'Task board'))
      + _projChip(delivery.source) + '</div>'
      + '<div class="proj-empty">' + _projEsc(String(delivery.empty_reason || '')) + '</div>'
      + '<div class="proj-item"><span class="proj-item-name">'
      + '<a href="#" onclick="switchPanel(\'kanban\');return false;">'
      + _projEsc(_projT('projects_open_board', 'Open the shared task board')) + '</a>'
      + '</span><span class="proj-chip">'
      + _projEsc(_projT('projects_shared_board_note', 'Shared')) + '</span></div></div>';
  }
  if (sections) sections.innerHTML = html;
}

function _projRenderIntegrations() {
  const host = $('projIntegrations');
  if (!host) return;
  // Absent means the caller may not see the local source inventory at all.
  const rows = (_projHub && Array.isArray(_projHub.integrations)) ? _projHub.integrations : null;
  if (!rows) { host.innerHTML = ''; return; }
  const states = {
    not_configured: _projT('projects_state_not_configured', 'Not connected'),
    configured_not_readable: _projT('projects_state_configured_not_readable', 'Set up, not readable here'),
    reader_missing: _projT('projects_state_reader_missing', 'Connected, not read here yet'),
  };
  host.innerHTML = '<div class="proj-card"><div class="proj-card-title">'
    + _projEsc(_projT('projects_integrations_title', 'Sources not connected yet'))
    + '</div>'
    + '<div class="proj-empty">'
    + _projEsc(_projT('projects_connect_hint', 'Ask your administrator to connect a source before expecting it here.'))
    + '</div>'
    + rows.map(r => '<div class="proj-integration"><div class="proj-integration-head">'
      + _projEsc(_projT('projects_' + String(r.key || ''), String(r.label)))
      + '<span class="proj-chip">'
      + _projEsc(String(states[r.state] || _projT('projects_not_connected', 'Not connected')))
      + '</span></div><div class="proj-integration-seam">'
      + _projEsc(String(r.seam)) + '</div></div>').join('')
    + '</div>';
}
