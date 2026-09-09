"""Execute the real history loader against delayed server snapshots."""
import subprocess


def test_full_history_load_does_not_replace_newer_turn_or_session_state():
    script = r'''
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const sessions = fs.readFileSync('static/sessions.js', 'utf8');
const outline = fs.readFileSync('static/outline.js', 'utf8');
const messages = fs.readFileSync('static/messages.js', 'utf8');
const extract = (source, start, end) => {
  const from = source.indexOf(start), to = source.indexOf(end, from);
  assert.ok(from >= 0 && to > from);
  return source.slice(from, to);
};
const code = extract(messages, 'function _messageIdentityKey(', 'async function _restoreSettledSession(')
  + extract(sessions, 'async function _ensureAllMessagesLoaded()', 'const SESSION_ARCHIVED_PAGE_SIZE')
  + extract(outline, 'function _ensureOutlineMessagesLoaded(', '// Extracts the first 60');
function setup() {
  let release;
  const oldTail = [{role:'user',content:'OLD_TAIL'}, {role:'assistant',content:'OLD_ANSWER',_turnUsage:{input:7}}];
  const server = [{role:'user',content:'OLDER'}, {role:'assistant',content:'OLDER_ANSWER'},
    {role:'user',content:'OLD_TAIL'}, {role:'assistant',content:'OLD_ANSWER'}];
  const ctx = {S:{session:{session_id:'qa',message_count:4},messages:oldTail,busy:false,activeStreamId:null},
    window:{},_messagesTruncated:true,_loadingOlder:false,_loadingSessionId:null,_oldestIdx:2,_messagesGeneration:0,
    renders:0,expands:0,synced:0,api:()=>new Promise(resolve=>{release=resolve;}),
    renderMessages:()=>{ctx.renders++;},_expandOutlineRenderWindow:()=>{ctx.expands++;},
    _bumpMessagesGeneration:()=>++ctx._messagesGeneration,_syncToolCallsForLoadedMessages:()=>{ctx.synced++;}};
  vm.createContext(ctx);vm.runInContext(code,ctx);
  return {ctx,release:()=>release({session:{messages:server,message_count:4,tool_calls:[]}}),server};
}
(async()=>{
 for(const viaOutline of [false,true]) {
  for(const change of ['active','completed','replaced','generation','switched']) {
   const f=setup(),c=f.ctx;
   const pending=viaOutline?c._ensureOutlineMessagesLoaded('qa'):c._ensureAllMessagesLoaded();
   if(change==='active'||change==='completed') {
    c.S.messages.push({role:'user',content:'NEW_PENDING',_pending:true});
    c.S.busy=change==='active';c.S.activeStreamId=change==='active'?'new-stream':null;
   } else if(change==='replaced') c.S.messages=c.S.messages.map(m=>({...m,content:m.content+'_NEW'}));
   else if(change==='generation') c._messagesGeneration++;
   else c.S.session={session_id:'different',message_count:2};
   const preserved=c.S.messages,expected=JSON.stringify(preserved),generation=c._messagesGeneration;
   f.release();const loaded=await pending;
   assert.equal(c.S.messages,preserved);assert.equal(JSON.stringify(c.S.messages),expected);
   assert.equal(c._messagesTruncated,true);assert.equal(c._oldestIdx,2);
   assert.equal(c._messagesGeneration,generation);assert.equal(c._loadingOlder,false);
   assert.equal(c.synced,0);assert.equal(c.renders,0);assert.equal(c.expands,0);
   assert.equal(loaded,false,change);
  }
  const f=setup(),c=f.ctx;
  const pending=viaOutline?c._ensureOutlineMessagesLoaded('qa'):c._ensureAllMessagesLoaded();
  f.release();assert.equal(await pending,true);
  assert.equal(c.S.messages.length,4);assert.equal(c.S.messages[3]._turnUsage.input,7);
  assert.equal(c._messagesTruncated,false);assert.equal(c._oldestIdx,0);
  assert.equal(c._loadingOlder,false);assert.equal(c.synced,1);
  assert.equal(c.renders,viaOutline?1:0);assert.equal(c.expands,viaOutline?1:0);
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_edit_and_regenerate_abort_stale_loads_without_truncating_new_turns():
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('static/ui.js','utf8');
const start=source.indexOf('async function submitEdit('),end=source.indexOf('// postProcessRenderedMessages()',start);
assert.ok(start>=0&&end>start);
const code=source.slice(start,end);
function setup() {
 let loaded,truncate,started;
 const input={value:'KEEP_DRAFT'},apiStarted=new Promise(resolve=>{started=resolve;});
 const ctx={S:{session:{session_id:'qa'},messages:[{role:'user',content:'ORIGINAL'},{role:'assistant',content:'OLD_ANSWER'}],busy:false,activeStreamId:null},
  _oldestIdx:0,_messagesTruncated:false,apiCalls:0,sends:0,renders:0,
  _ensureAllMessagesLoaded:()=>new Promise(resolve=>{loaded=resolve;}),
  api:()=>{ctx.apiCalls++;started();return ctx.holdTruncate?new Promise(resolve=>{truncate=resolve;}):Promise.resolve({});},
  _deliberateSessionModelPick:()=>null,_reArmRecoveryPick:()=>{},msgContent:m=>m.content,
  renderMessages:()=>{ctx.renders++;},$:()=>input,send:async()=>{ctx.sends++;},setStatus:()=>{},t:k=>k};
 vm.createContext(ctx);vm.runInContext(code,ctx);
 return {ctx,input,apiStarted,load:value=>loaded(value),truncate:()=>truncate({})};
}
function invoke(c,name) {
 return name==='submitEdit'?c.submitEdit(0,'EDITED'):c.regenerateResponse({closest:()=>({dataset:{msgIdx:'1'}})});
}
(async()=>{
 for(const name of ['submitEdit','regenerateResponse']) {
  for(const change of ['false','active','completed','switched','still-truncated']) {
   const f=setup(),c=f.ctx,pending=invoke(c,name);
   if(change==='active'||change==='completed') c.S.messages.push({role:'user',content:'NEW_TURN'});
   if(change==='active') {c.S.busy=true;c.S.activeStreamId='new';}
   if(change==='switched') c.S.session={session_id:'different'};
   if(change==='still-truncated') c._messagesTruncated=true;
   const expected=JSON.stringify(c.S.messages),identity=c.S.messages;
   f.load(!['false','completed'].includes(change));await pending;
   assert.equal(c.apiCalls,0,`${name} ${change} must not truncate`);
   assert.equal(c.S.messages,identity);assert.equal(JSON.stringify(c.S.messages),expected);
   assert.equal(c.sends,0);assert.equal(c.renders,0);assert.equal(f.input.value,'KEEP_DRAFT');
  }
  for(const change of ['new-turn','switched']) {
   const f=setup(),c=f.ctx;c.holdTruncate=true;const pending=invoke(c,name);f.load(true);await f.apiStarted;
   if(change==='new-turn') {c.S.messages.push({role:'user',content:'NEW_DURING_TRUNCATE'});c.S.busy=true;c.S.activeStreamId='new';}
   else {c.S.session={session_id:'different'};c.S.messages=[{role:'user',content:'OTHER_SESSION'}];}
   const expected=JSON.stringify(c.S.messages),identity=c.S.messages;f.truncate();await pending;
   assert.equal(c.apiCalls,1);assert.equal(c.S.messages,identity);assert.equal(JSON.stringify(c.S.messages),expected);
   assert.equal(c.sends,0);assert.equal(c.renders,0);assert.equal(f.input.value,'KEEP_DRAFT');
  }
  const f=setup(),c=f.ctx,pending=invoke(c,name);f.load(true);await pending;
  assert.equal(c.apiCalls,1);assert.equal(c.sends,1);assert.equal(c.renders,1);
  assert.equal(c.S.messages.length,name==='submitEdit'?0:1);
  assert.equal(f.input.value,name==='submitEdit'?'EDITED':'ORIGINAL');
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
