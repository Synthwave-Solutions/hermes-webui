"""Execute Start navigation against delayed history and obsolete tail anchors."""
import subprocess


_SCRIPT = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('static/ui.js','utf8');
function extract(start,end){const a=source.indexOf(start),b=source.indexOf(end,a);assert.ok(a>=0&&b>a);return source.slice(a,b);}
const code=extract('async function jumpToSessionStart(){','function _userMessageDomId(')
 +extract('function _messageScrollSnapshotForRender(', 'function _messageScrollSnapshotInputChanged(')
 +extract('function _restoreMessageScrollSnapshot(snapshot){','/**\n * Mobile scroll-jank guard:')
 +extract('function _scrollAfterMessageRender(', 'function _maybeRecoverVirtualizedBlankViewport(');
function setup(){
 let resolveHistory;
 const frames=[],writes=[];
 const el={_top:9000,scrollHeight:10000,clientHeight:700,
  get scrollTop(){return this._top;},set scrollTop(value){this._top=value;writes.push(value);}};
 const obsolete={anchor:{sessionIdx:210,rawIdx:0,topOffset:0},top:0,bottom:9300,pinned:false,userUnpinned:true,inputGeneration:0};
 const ctx={S:{session:{session_id:'first'},messages:[{role:'user',content:'TAIL'}],busy:false,activeStreamId:null},
  _messageScrollInputGeneration:0,_scrollPinned:true,_messageUserUnpinned:false,_programmaticScroll:false,
  _programmaticScrollSetAt:0,_messageRenderWindowSize:30,_messageVirtualWindowKey:'old-tail',
  _lastScrollTop:0,_lastMessageClientHeight:0,_nearBottomCount:0,renders:0,loads:0,
  $:()=>el,performance:{now:()=>1},console,
  _ensureAllMessagesLoaded:()=>{ctx.loads++;return new Promise(resolve=>{resolveHistory=resolve;});},
  _cancelBottomSettle:()=>{},_currentMessageRenderWindowSize:()=>30,_messageRenderableMessageCount:()=>240,
  _captureMessageScrollSnapshot:()=>obsolete,
  _messageScrollSnapshotInputChanged:()=>false,_restorePinnedMessageScrollSnapshot:()=>false,
  _restoreMessageViewportAnchor:anchor=>{el.scrollTop=anchor.sessionIdx*100;return true;},
  _followMessagesAfterDomReplace:()=>false,_maybeShowNewMessageScrollCue:()=>{},
  _deferClearProgrammaticScroll:()=>{ctx._programmaticScroll=false;},
  _updateSessionStartJumpButton:()=>{},requestAnimationFrame:fn=>{frames.push(fn);},
  renderMessages:options=>{ctx.renders++;ctx._scrollAfterMessageRender(options.preserveScroll,ctx._messageScrollSnapshotForRender(options.preserveScroll,options));}};
 vm.createContext(ctx);vm.runInContext(code,ctx);
 return {ctx,el,frames,writes,obsolete,release:value=>resolveHistory(value)};
}
'''


def _run(body):
    result = subprocess.run(['node', '-e', _SCRIPT + body], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_start_replaces_obsolete_tail_anchor_without_changing_ordinary_preservation():
    _run(r'''
(async()=>{
 const f=setup(),c=f.ctx;
 // Normal renders continue to hold the existing semantic reader position.
 c.renderMessages({preserveScroll:true});assert.equal(f.el.scrollTop,21000);
 const old=JSON.stringify(f.obsolete);f.writes.length=0;c.renders=0;
 const navigation=c.jumpToSessionStart();f.release(true);await navigation;
 assert.equal(c.renders,1);assert.equal(c.loads,1);
 assert.equal(f.el.scrollTop,0);assert.ok(f.writes.every(value=>value===0));
 assert.equal(JSON.stringify(f.obsolete),old,'do not mutate another render snapshot');
 f.frames.forEach(fn=>fn());assert.equal(f.el.scrollTop,0);
 assert.equal(c._messageUserUnpinned,true);assert.equal(c._scrollPinned,false);
})().catch(error=>{console.error(error);process.exitCode=1;});
''')


def test_start_aborts_stale_failed_or_newly_active_history_without_moving_viewport():
    _run(r'''
(async()=>{
 for(const change of ['load-false','session-switch','new-navigation','new-turn']){
  const f=setup(),c=f.ctx,original=c.S.messages;
  const navigation=c.jumpToSessionStart();
  if(change==='session-switch') c.S.session={session_id:'second'};
  if(change==='new-navigation') c._messageScrollInputGeneration++;
  if(change==='new-turn'){c.S.busy=true;c.S.activeStreamId='new';c.S.messages.push({role:'user',content:'NEW'});}
  f.release(change!=='load-false');await navigation;f.frames.forEach(fn=>fn());
  assert.equal(c.renders,0,change);assert.equal(f.writes.length,0,change);assert.equal(f.el.scrollTop,9000,change);
  assert.equal(c.S.messages,original);assert.equal(c._programmaticScroll,false);
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
''')


def test_start_queued_frame_respects_new_session_navigation_or_turn_and_keeps_streaming_rows():
    _run(r'''
(async()=>{
 for(const change of ['session-switch','new-navigation','new-turn','completed-turn','replaced-messages']){
  const f=setup(),c=f.ctx,navigation=c.jumpToSessionStart();f.release(true);await navigation;
  f.el._top=1234;f.writes.length=0;
  if(change==='session-switch') c.S.session={session_id:'second'};
  if(change==='new-navigation') c._messageScrollInputGeneration++;
  if(change==='new-turn'){c.S.busy=true;c.S.activeStreamId='new';}
  if(change==='completed-turn') c.S.messages.push({role:'user',content:'COMPLETED'});
  if(change==='replaced-messages') c.S.messages=[{role:'user',content:'NEW ARRAY'}];
  f.frames.forEach(fn=>fn());assert.equal(f.el.scrollTop,1234,change);assert.equal(f.writes.length,0,change);
 }
 const f=setup(),c=f.ctx;c.S.busy=true;c.S.activeStreamId='existing';const messages=c.S.messages;
 await c.jumpToSessionStart();f.frames.forEach(fn=>fn());
 assert.equal(c.loads,0);assert.equal(c.renders,0);assert.equal(c.S.messages,messages);assert.equal(c.S.activeStreamId,'existing');
 assert.equal(f.el.scrollTop,0);
})().catch(error=>{console.error(error);process.exitCode=1;});
''')


def test_superseded_start_reconciles_loaded_indices_without_stealing_newer_viewport():
    _run(r'''
(async()=>{
 const source=fs.readFileSync('static/sessions.js','utf8');
 const from=source.indexOf('async function _ensureAllMessagesLoaded()'),to=source.indexOf('const SESSION_ARCHIVED_PAGE_SIZE',from);
 assert.ok(from>=0&&to>from);
 const f=setup(),c=f.ctx;let release;
 const all=[{role:'user',content:'FIRST'},{role:'assistant',content:'FIRST ANSWER'},
  {role:'user',content:'MIDDLE'},{role:'assistant',content:'MIDDLE ANSWER'},
  {role:'user',content:'TAIL'},{role:'assistant',content:'TAIL ANSWER'}];
 c.S.messages=all.slice(4);c._oldestIdx=4;c._messagesTruncated=true;c._loadingOlder=false;c._loadingSessionId=null;c._messagesGeneration=0;
 c.window={};c._bumpMessagesGeneration=()=>++c._messagesGeneration;c._syncToolCallsForLoadedMessages=()=>{};
 c.api=()=>new Promise(resolve=>{release=resolve;});
 let domIndex=0;const renders=[];
 c.renderMessages=options=>{renders.push(options);domIndex=c.S.messages.findIndex(message=>message.content==='TAIL');};
 vm.runInContext(source.slice(from,to),c);
 const pending=c.jumpToSessionStart();
 // Actual newer same-session End/scroll intent arrives while the HTTP read is pending.
 c._messageScrollInputGeneration++;f.el._top=1234;
 release({session:{messages:all,message_count:all.length,tool_calls:[]}});await pending;
 assert.equal(c.S.messages.length,6);assert.equal(c._oldestIdx,0);assert.equal(c._messagesTruncated,false);
 assert.equal(renders.length,1,'full-array replacement requires one DOM reconciliation');
 assert.equal(renders[0].preserveScroll,true);assert.equal(renders[0].scrollToStart,undefined);
 assert.equal(domIndex+c._oldestIdx,4,'Edit must still target the displayed tail question');
 assert.equal(f.el.scrollTop,1234,'reconciliation must not apply Start navigation');
 assert.equal(f.writes.length,0);assert.equal(f.frames.length,0);
})().catch(error=>{console.error(error);process.exitCode=1;});
''')
