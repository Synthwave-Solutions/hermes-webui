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
  // A project can disappear or leave the caller's visibility scope between
  // refreshes. Never let a stale local selection turn a successfully loaded
  // hub into the generic unavailable state via a follow-up detail 404.
  const visibleIds = new Set((_projHub.projects || []).map(p => String(p.project_id || '')));
  if (_projSelectedId && !visibleIds.has(_projSelectedId)) {
    _projSelectedId = '';
    _projDetail = null;
  }
  if (_projSelectedId) await _projOpen(_projSelectedId);
  return true;
}

function _projRenderList() {
  const list = $('projectsPanelList');
  if (!list) return;
  const rows = (_projHub && Array.isArray(_projHub.projects)) ? _projHub.projects : [];
  const create='<div class="proj-card proj-create"><label class="proj-field" for="projNewName">Project name<input id="projNewName" placeholder="e.g. Product launch" aria-label="Project name"></label><button class="app-dialog-btn" id="projCreateButton" onclick="_projCreateShared()">New project</button></div>';
  if (!rows.length) {
    list.innerHTML = create + '<div class="proj-empty">'
      + _projEsc(_projT('projects_none_yet', 'You do not have any projects on this workstation yet.'))
      + '</div>';
    return;
  }
  list.innerHTML = create + rows.map(p => {
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
    + '</div>' + body + '</div>';
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
      + _projEsc(String(p.name))
      + (p.system ? '<span class="proj-chip">' + _projEsc(_projT('projects_system_label', 'System')) + '</span>' : '')
      + '</div><div class="proj-state">'
      + _projEsc(p.collaboration ? 'Work together with people, bots and shared project files.' : 'Conversations and resources collected in this project.')
      + '</div></div>';
  }

  let html = (p.collaboration || p.can_manage) ? '<div id="projTeamControls"></div>' : '';
  html += _projSectionCard(
    'projects_section_conversations', 'Conversations', _projDetail.conversations,
    s => '<div class="proj-item" data-project-session="'+_projEsc(s.session_id)+'"><span class="proj-item-name">'
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
  if (sections) {
    sections.innerHTML = html;
    sections.querySelectorAll('[data-project-session]').forEach(row=>row.addEventListener('click',()=>{
      loadSession(row.dataset.projectSession);switchPanel('chat');
    }));
  }
  if(p.collaboration || p.can_manage) _projLoadTeamControls(p);
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

async function _projWithBusy(button, label, action) {
  if (button && button.disabled) return;
  const previous = button && button.textContent;
  if (button) { button.disabled=true;button.textContent=label;button.setAttribute('aria-busy','true'); }
  try { return await action(); }
  finally { if(button){button.disabled=false;button.textContent=previous;button.removeAttribute('aria-busy');} }
}

async function _projCreateShared() {
  return _projWithBusy($('projCreateButton'), 'Creating…', _projCreateSharedAction);
}

async function _projCreateSharedAction() {
  const name = ($('projNewName') || {}).value || '';
  try {
    const result = await api('/api/projects/team', {method:'POST', body:JSON.stringify({name, members:[], bot_participants:[], profile:'default'})});
    _projSelectedId = result.project.project_id;
    await loadProjectsHub();
  } catch (error) { showToast(String(error.message || error)); }
}

async function _projLoadTeamControls(project) {
  const host = $('projTeamControls');
  if (!host) return;
  try {
    const [people, bots, files] = await Promise.all([
      api('/api/people'), api('/api/profiles?fast=1').catch(()=>({profiles:[]})), api('/api/projects/files?project_id='+encodeURIComponent(project.project_id)).catch(()=>null)
    ]);
    if (!_projDetail || _projDetail.project.project_id !== project.project_id) return;
    const humans = (people.people || []).slice();
    if(people.me && !humans.some(p=>p.email===people.me)) humans.push({email:people.me,display_name:people.me});
    const profiles = bots.profiles || [];
    host.innerHTML = '<div class="proj-card"><div class="proj-card-title">Project team</div><div class="proj-team-grid"><section class="proj-team-section"><h3>People</h3>'
      + '<label class="proj-field" for="projPeopleSearch">Find people<input id="projPeopleSearch" placeholder="Search by name or email" aria-label="Find people"></label>'
      + '<div id="projHumanChoices" class="proj-choices"></div></section><section class="proj-team-section"><h3>Bots</h3><p class="proj-state">Choose assistants for this project.</p><div id="projBotChoices" class="proj-choices"></div></section></div><div class="proj-actions">'
      + (project.can_manage ? '<button class="app-dialog-btn" id="projSaveTeam">Save members and bots</button><button class="app-dialog-btn" id="projArchiveTeam">Archive project</button>' : '')
      + '</div><p class="proj-state">Project membership does not change your bot or tool permissions.</p>'
      + '<button class="app-dialog-btn" id="projStartChat">New group conversation</button></div>'
      + (files ? '<div class="proj-card"><div class="proj-card-title">Project files</div><label class="proj-field" for="projUpload"><span id="projUploadLabel">Upload a file</span><input type="file" id="projUpload"></label><div id="projFileList" class="proj-actions"></div></div>' : '');
    const humanHost=$('projHumanChoices');
    const ownerRow=document.createElement('div');ownerRow.className='proj-owner';ownerRow.textContent='Owner: '+project.owner_email;humanHost.appendChild(ownerRow);
    humans.filter(p=>p.email!==project.owner_email).forEach(person=>{
      const label=document.createElement('label');label.className='proj-choice';
      label.dataset.search=(person.display_name+' '+person.email).normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
      const box=document.createElement('input');box.type='checkbox';box.value=person.email;
      box.checked=(project.members||[]).includes(person.email);box.disabled=!project.can_manage;
      label.append(box,document.createTextNode(' '+(person.display_name||person.email)));humanHost.appendChild(label);
    });
    $('projPeopleSearch').oninput=event=>{
      const q=event.target.value.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
      humanHost.querySelectorAll('label').forEach(row=>row.style.display=row.dataset.search.includes(q)?'flex':'none');
    };
    const botHost=$('projBotChoices');
    const ids=[...new Set(profiles.map(p=>p.name).concat(project.bot_participants||[]))];
    ids.forEach(id=>{
      const p=profiles.find(p=>p.name===id);const label=document.createElement('label');label.className='proj-choice';
      const box=document.createElement('input');box.type='checkbox';box.value=id;box.checked=(project.bot_participants||[]).includes(id);
      box.disabled=!project.can_manage || !p;
      label.appendChild(box);
      if(p && typeof botAvatarHtml==='function'){const avatar=document.createElement('span');avatar.innerHTML=botAvatarHtml(p);label.appendChild(avatar);}
      label.appendChild(document.createTextNode(' '+(p && typeof botDisplayName==='function'?botDisplayName(p):id)+(!p?' — ask an administrator for bot access':'')));botHost.appendChild(label);
    });
    if ($('projSaveTeam')) $('projSaveTeam').onclick=async()=>{
      try {
        await api('/api/projects/team',{method:'POST',body:JSON.stringify({project_id:project.project_id,revision:project.revision||0,
          members:Array.from(humanHost.querySelectorAll('input:checked')).map(x=>x.value),
          bot_participants:Array.from(botHost.querySelectorAll('input:checked')).map(x=>x.value)})});
        await _projOpen(project.project_id);
      } catch(error){showToast(String(error.message||error));}
    };
    if($('projArchiveTeam')) $('projArchiveTeam').onclick=async()=>{
      try {await api('/api/projects/team',{method:'POST',body:JSON.stringify({project_id:project.project_id,revision:project.revision||0,deleted:true})});_projSelectedId='';_projDetail=null;await loadProjectsHub();_projRenderDetail();}
      catch(error){showToast(String(error.message||error));}
    };
    $('projStartChat').onclick=async()=>{
      try {
        const usable=(project.bot_participants||[]).filter(id=>!(project.unavailable_bots||[]).includes(id));
        if(!usable.length){showToast('No project bot is available to your account. Ask the project owner or administrator.');return;}
        const result=await api('/api/projects/chat',{method:'POST',body:JSON.stringify({project_id:project.project_id,bot_participants:usable})});
        await loadSession(result.session.session_id);switchPanel('chat');
      } catch(error){showToast(String(error.message||error));}
    };
    for(const [id,label] of [['projSaveTeam','Saving…'],['projStartChat','Opening…'],['projArchiveTeam','Archiving…']]){
      const button=$(id);if(button){const action=button.onclick;button.onclick=()=>_projWithBusy(button,label,action);}
    }
    if(files){
      const fileHost=$('projFileList');
      (files.files||[]).forEach(file=>{
        const button=document.createElement('button');button.className='app-dialog-btn';button.textContent=file.name;
        button.onclick=async()=>{
          try {
            const data=await api('/api/projects/files?project_id='+encodeURIComponent(project.project_id)+'&name='+encodeURIComponent(file.name));
            const blob=new Blob([Uint8Array.from(atob(data.content_base64),c=>c.charCodeAt(0))]);
            const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=file.name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
          } catch(error){showToast(String(error.message||error));}
        };fileHost.appendChild(button);
      });
      $('projUpload').onchange=async event=>{
        const file=event.target.files[0];if(!file)return;
        if(file.size>5000000){event.target.value='';showToast('File limit is 5 MB');return;}
        const input=event.target;input.disabled=true;
        const uploadLabel=$('projUploadLabel');if(uploadLabel)uploadLabel.textContent='Uploading…';
        const resetUpload=()=>{input.disabled=false;input.value='';if(uploadLabel)uploadLabel.textContent='Upload a file';};
        const reader=new FileReader();reader.onload=async()=>{
          try {await api('/api/projects/files',{method:'POST',body:JSON.stringify({project_id:project.project_id,name:file.name,content_base64:String(reader.result).split(',')[1]})});await _projOpen(project.project_id);}
          catch(error){showToast(String(error.message||error));}
          finally{resetUpload();}
        };reader.onerror=()=>{resetUpload();showToast('The file could not be read. Please try again.');};reader.readAsDataURL(file);
      };
    }
  } catch(error){host.textContent=String(error.message||error);}
}
