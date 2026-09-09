"""Execute real reconnect continuations against delayed status and changing owners."""
import subprocess

import pytest


SCRIPT = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('static/messages.js','utf8');
function extract(a,b){const start=source.indexOf(a),end=source.indexOf(b,start);assert.ok(start>=0&&end>start);return source.slice(start,end);}
const ownership=extract('function _liveStreamAttachmentIsCurrent(', 'const _STREAM_NOTIFICATION_BACKGROUND=');
const teardown=extract('function closeLiveStream(', 'function closeOtherLiveStreams(');
const preflight=extract('  (async()=>{\n    // Reattach path', '\n}\n\nfunction transcript()');
const deferred=extract('  function _reattachOrRestoreAfterDeferredStreamError(', '  function _deferStreamErrorIfPageHidden(');
const probe=extract('        const _probeReconnect=async(', '        setTimeout(()=>{void _probeReconnect(0);}')+'globalThis.probe=_probeReconnect;';
function setup(kind='preflight'){
 let resolve,reject;const attachment={streamId:'old'},opened=[],wired=[],mutations=[];
 const ctx={S:{session:{session_id:'sid'},activeStreamId:'old'},activeSid:'sid',streamId:'old',
  _LIVE_STREAM_ATTACHMENTS:{sid:attachment},LIVE_STREAMS:{},INFLIGHT:{},
  _terminalStateReached:false,_streamFinalized:false,reconnecting:true,_retryDelays:[1],source:{},
  _isSessionCurrentPane:sid=>ctx.S.session?.session_id===sid,
  api:()=>new Promise((yes,no)=>{resolve=yes;reject=no;}),
  _wireSSE:stream=>wired.push(stream.url),
  EventSource:class{constructor(url){this.url=url;opened.push(url);}close(){}},
  URL,document:{baseURI:'http://127.0.0.1/'},location:{href:'http://127.0.0.1/'},console,
  _runJournalReplayParams:()=>'',
  _clearOwnerInflightState:()=>mutations.push('inflight'),_clearApprovalForOwner:()=>mutations.push('approval'),
  _clearClarifyForOwner:()=>mutations.push('clarify'),clearLiveToolCards:()=>mutations.push('tools'),
  removeThinking:()=>mutations.push('thinking'),_setActivePaneIdleIfOwner:()=>mutations.push('idle'),
  renderMessages:()=>mutations.push('render'),renderSessionList:()=>mutations.push('list'),
  _scheduleAnchorRegistryCleanup:()=>{},_isActiveSession:()=>ctx.S.session?.session_id==='sid',
  _isMessagePaneNearBottom:()=>false,_isMessageReaderUnpinned:()=>false,
  _deferStreamErrorIfOffline:()=>{mutations.push('offline');return false;},_pageHiddenForStreamError:()=>false,
  _deferStreamErrorIfPageHidden:()=>{mutations.push('hidden');return false;},
  _flushReasoningToAnchor:()=>{},_handleStreamError:()=>mutations.push('error'),
  _restoreSettledSession:async()=>{mutations.push('restore');return true;},
  setComposerStatus:()=>mutations.push('status'),setTimeout:()=>mutations.push('timer'),clearTimeout:()=>{},
  _resumeSessionStreamAfterLiveChat:()=>{},
 };
 vm.createContext(ctx);vm.runInContext(ownership+teardown,ctx);
 ctx._isAttachmentCurrent=()=>ctx._liveStreamAttachmentIsCurrent('sid','old',attachment);
 if(kind==='deferred'){vm.runInContext(deferred,ctx);ctx._reattachOrRestoreAfterDeferredStreamError({});}
 else if(kind==='probe'){vm.runInContext(probe,ctx);ctx.probe();}
 else vm.runInContext(preflight,ctx);
 return {ctx,attachment,opened,wired,mutations,release:x=>resolve(x),reject:()=>reject(new Error('transport')),settle:()=>new Promise(r=>setImmediate(r))};
}
'''


def run(body):
    result = subprocess.run(['node', '-e', SCRIPT + body], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('kind', ['preflight', 'deferred', 'probe'])
def test_delayed_status_cannot_reopen_or_clear_newer_stream(kind):
    run(r'''
(async()=>{
 for(const outcome of [{active:true},{active:false,replay_available:true},{active:false},null]){
  for(const change of ['new-stream','pending-send','same-id-new-attachment','other-session','navigation-teardown']){
   const f=setup(KIND),c=f.ctx;
   if(change==='new-stream') c.S.activeStreamId='new';
   if(change==='pending-send') c.S.activeStreamId=null;
   if(change==='same-id-new-attachment') c._LIVE_STREAM_ATTACHMENTS.sid={streamId:'old'};
   if(change==='other-session') c.S.session={session_id:'other'};
   if(change==='navigation-teardown') c.closeLiveStream('sid');
   const before=JSON.stringify(c.S);if(outcome===null) f.reject();else f.release(outcome);await f.settle();
   assert.deepEqual(f.opened,[],change);assert.deepEqual(f.wired,[],change);assert.deepEqual(f.mutations,[],change);
   assert.equal(JSON.stringify(c.S),before,change);
  }
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
'''.replace('KIND', repr(kind)))


@pytest.mark.parametrize('kind', ['preflight', 'deferred', 'probe'])
def test_current_owner_still_recovers_real_active_stream(kind):
    run(r'''
(async()=>{
 const f=setup(KIND);f.release({active:true});await f.settle();
 assert.equal(f.opened.length,1);assert.equal(f.wired.length,1);
 assert.match(f.wired[0],/stream_id=old/);assert.equal(f.ctx.S.activeStreamId,'old');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''.replace('KIND', repr(kind)))


def test_current_preflight_replays_finished_journal_and_clears_truly_dead_stream():
    run(r'''
(async()=>{
 const replay=setup();replay.release({active:false,replay_available:true});await replay.settle();
 assert.equal(replay.wired.length,1);assert.equal(replay.ctx.S.activeStreamId,'old');
 const dead=setup();dead.release({active:false,replay_available:false});await dead.settle();
 assert.equal(dead.wired.length,0);assert.equal(dead.ctx.S.activeStreamId,null);
 assert.ok(dead.mutations.includes('idle'));assert.ok(dead.mutations.includes('render'));
})().catch(error=>{console.error(error);process.exitCode=1;});
''')


def test_late_settled_snapshot_cannot_replace_successor_or_other_session():
    run(r'''
(async()=>{
 const restore=extract('  async function _restoreSettledSession(', '  function _handleStreamError(');
 for(const change of ['new-stream','same-id-new-attachment','other-session']){
  const f=setup(),c=f.ctx;f.release({active:true});await f.settle();f.opened.length=0;f.wired.length=0;
  c.S.messages=[{role:'user',content:'NEWER TURN'}];c._closeSource=()=>{};
  vm.runInContext(restore,c);const response=c._restoreSettledSession({}, {status:true});
  if(change==='new-stream')c.S.activeStreamId='new';
  if(change==='same-id-new-attachment')c._LIVE_STREAM_ATTACHMENTS.sid={streamId:'old'};
  if(change==='other-session')c.S.session={session_id:'other'};
  const before=JSON.stringify(c.S);f.release({session:{session_id:'sid',messages:[{role:'user',content:'OLD'}]}});
  assert.equal(await response,'stale',change);assert.equal(JSON.stringify(c.S),before,change);assert.deepEqual(f.mutations,[],change);
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
''')


def test_stale_attach_caller_cannot_touch_successor_before_status_probe():
    run(r'''
const entry=extract('function attachLiveStream(', '  _bindStreamHiddenTracker();')+'return true;\n}';
const c={S:{session:{session_id:'sid'},activeStreamId:'new'},effects:[],
 _isSessionCurrentPane:sid=>c.S.session.session_id===sid,
 _invalidateSessionSceneCache:sid=>c.effects.push(sid)};
vm.createContext(c);vm.runInContext(entry,c);
assert.equal(c.attachLiveStream('sid','old'),undefined);assert.deepEqual(c.effects,[]);
assert.equal(c.attachLiveStream('other','new'),undefined);assert.deepEqual(c.effects,[]);
assert.equal(c.attachLiveStream('sid','new'),true);assert.deepEqual(c.effects,['sid']);
''')


def test_final_recovery_timer_and_late_false_result_cannot_mutate_replaced_attachment():
    run(r'''
(async()=>{
 for(const fireTimer of [false,true]){
  const f=setup('probe'),c=f.ctx;let releaseRestore,calls=0;const timers=[],cleared=[];
  c.setTimeout=fn=>{timers.push(fn);return timers.length;};c.clearTimeout=id=>cleared.push(id);
  c._restoreSettledSession=async()=>{if(++calls===1)return false;return new Promise(r=>releaseRestore=r);};
  c._deferStreamErrorIfOffline=()=>{f.mutations.push('offline');return false;};
  c._deferStreamErrorIfPageHidden=()=>{f.mutations.push('hidden');return false;};
  f.release({active:false,replay_available:false});await f.settle();
  assert.equal(calls,2);assert.equal(timers.length,1);f.mutations.length=0;
  c._LIVE_STREAM_ATTACHMENTS.sid={streamId:'old'};
  if(fireTimer)timers[0]();releaseRestore(false);await f.settle();
  assert.deepEqual(f.mutations,[],fireTimer?'expired timer':'late false result');
  assert.equal(c.S.activeStreamId,'old');assert.equal(f.wired.length,0);
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
''')
