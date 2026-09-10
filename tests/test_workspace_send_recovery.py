"""Exercise actual recovery selection code across delayed dialog/API boundaries."""
import subprocess

SCRIPT = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const messages=fs.readFileSync('static/messages.js','utf8'),panels=fs.readFileSync('static/panels.js','utf8');
const helper=messages.slice(messages.indexOf('function _isWorkspaceStartForbidden('),messages.indexOf('function _renderWorkspaceSendRecovery('));
const change=panels.slice(panels.indexOf('async function switchToWorkspace('),panels.indexOf('// ── Profile panel'));
function setup({dirty=false,fileError=false}={}){
 let release;const requests=[],events=[],recovery={sid:'old',profile:'default',workspace:'/old'};
 const c={S:{session:{session_id:'old',workspace:'/old',model:'test'},activeProfile:'default',messages:[{role:'user',content:'history'}],pendingFiles:['attachment']},window:{_newChatOnWorkspaceSwitch:true},
  _previewDirty:dirty,console,api:(url,opts)=>{requests.push([url,JSON.parse(opts.body)]);return new Promise(r=>release=r);},
  showConfirmDialog:()=>new Promise(r=>release=r),cancelEditMode:()=>events.push('cancel-edit'),clearPreview:()=>{},
  $:()=>null,t:(text)=>text,showToast:text=>events.push(text),setStatus:text=>events.push(text),
  closeWsDropdown:()=>{},bumpWorkspaceTreeGen:()=>{},syncTopbar:()=>events.push('topbar'),
  _renderWorkspaceSendRecovery:()=>events.push('notice'),_workspaceSendRecovery:recovery,
  loadDir:async()=>{events.push('files');if(fileError)throw Error('file pane unavailable');},_currentPanel:'chat',
  newSession:()=>{throw Error('recovery must retain history');}
 };vm.createContext(c);vm.runInContext(helper+change,c);
 return{c,recovery,requests,events,release:value=>release(value)};
}
'''

def run(body):
    result = subprocess.run(['node', '-e', SCRIPT + body], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_only_explicit_workspace_start_denials_offer_recovery():
    run(r'''
const {c}=setup();
for(const message of ['Workspace membership required','Workspace membership unavailable',"Workspace is outside the user's governed scope",'Workspace explicitly denied by governance']){
 assert.equal(c._isWorkspaceStartForbidden({status:403,message}),true);
 assert.equal(c._isWorkspaceStartForbidden({status:500,message}),false);
}
for(const message of ['forbidden','Workspace actor identity required','Workspace governance unavailable','Other workspace error'])assert.equal(c._isWorkspaceStartForbidden({status:403,message}),false);
''')


def test_stale_session_profile_or_workspace_selection_response_cannot_mutate_visible_chat():
    run(r'''
(async()=>{for(const field of ['sid','profile','workspace']){
 const f=setup(),c=f.c;const pending=c.switchToWorkspace('/allowed','Allowed',{recovery:f.recovery});
 assert.equal(f.requests.length,1);assert.equal(f.requests[0][1].session_id,'old');
 if(field==='sid')c.S.session={session_id:'new',workspace:'/new'};
 if(field==='profile')c.S.activeProfile='different';
 if(field==='workspace')c.S.session.workspace='/newer-choice';
 const before=JSON.stringify(c.S);f.release({});await pending;
 assert.equal(JSON.stringify(c.S),before);assert.deepEqual(f.events,[]);
}})().catch(e=>{console.error(e);process.exitCode=1;});
''')


def test_dirty_confirmation_cannot_apply_to_successor_and_never_dispatches():
    run(r'''
(async()=>{const f=setup({dirty:true});const pending=f.c.switchToWorkspace('/allowed','Allowed',{recovery:f.recovery});
f.c.S.session={session_id:'new',workspace:'/new'};f.release(true);await pending;
assert.deepEqual(f.requests,[]);assert.deepEqual(f.events,[]);
})().catch(e=>{console.error(e);process.exitCode=1;});
''')


def test_current_recovery_retains_history_and_reports_file_failure_after_workspace_saved():
    run(r'''
(async()=>{const f=setup({fileError:true});const pending=f.c.switchToWorkspace('/allowed','Allowed',{recovery:f.recovery});
f.release({});await pending;assert.equal(f.c.S.session.session_id,'old');assert.equal(f.c.S.session.workspace,'/allowed');
assert.equal(f.c.S.messages[0].content,'history');assert.equal(f.c.S.pendingFiles[0],'attachment');
assert.ok(f.events.some(e=>e.includes('file pane unavailable')));assert.equal(f.requests.length,1);
assert.equal(f.requests[0][0],'/api/session/update');
})().catch(e=>{console.error(e);process.exitCode=1;});
''')


def test_late_file_pane_completion_cannot_load_memory_or_toast_in_successor():
    run(r'''
(async()=>{const f=setup();let filesDone;f.c.loadDir=()=>new Promise(r=>filesDone=r);
f.c.loadMemory=async()=>{throw Error('old recovery reached successor memory');};
const pending=f.c.switchToWorkspace('/allowed','Allowed',{recovery:f.recovery});f.release({});
await new Promise(r=>setImmediate(r));assert.equal(f.c.S.session.workspace,'/allowed');
f.c.S.session={session_id:'new',workspace:'/new'};f.c._currentPanel='memory';
const before=f.events.slice();filesDone();await pending;assert.deepEqual(f.events,before);
})().catch(e=>{console.error(e);process.exitCode=1;});
''')
