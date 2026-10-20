const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync('static/messages.js','utf8');
const code=src.slice(src.indexOf('let _bgPollTimers='),src.indexOf('// ── Panel navigation',src.indexOf('let _bgPollTimers=')));
function setup(){
 let resolve,reject,requests=0,renders=0,next=0;
 const timers=new Map(),badge={style:{},setAttribute(){}};
 const c={S:{session:{session_id:'a'},messages:[]},$:()=>badge,t:(k,...v)=>k+v.join(','),showToast(){},renderMessages(){renders++;},
 api:()=>{requests++;return new Promise((r,j)=>{resolve=r;reject=j});},setTimeout:fn=>{timers.set(++next,fn);return next;},clearTimeout:id=>timers.delete(id)};
 vm.createContext(c);vm.runInContext(code,c);
 return {c,badge,timers,get requests(){return requests},get renders(){return renders},complete:r=>resolve(r),fail:e=>reject(e),tick:async()=>{const f=[...timers.values()][0];timers.clear();if(f)await f();}};
}
(async()=>{
 const h=setup();h.c.startBackgroundPolling('a','one','First task');h.c.startBackgroundPolling('a','two','Second task');
 assert.equal(h.requests,1,'one request per parent session, including during the first fetch');
 h.complete({results:[{task_id:'one',answer:'First result'},{task_id:'two',answer:'Second result'}]});
 await new Promise(setImmediate);
 assert.equal(h.c.S.messages.length,2,'deliver every result from the destructive status response');
 assert.equal(h.renders,1,'batch completed results into one render');
 assert.equal(h.timers.size,0,'release completed polling state');
 const switched=setup();switched.c.startBackgroundPolling('a','one','First task');switched.c.S.session={session_id:'b'};
 switched.complete({results:[{task_id:'one',answer:'Private result for a'}]});await new Promise(setImmediate);
 assert.equal(switched.c.S.messages.length,0,'never append a completion to another chat');
 await switched.tick();assert.equal(switched.requests,1,'do not poll or consume another chat while inactive');
 switched.c.S.session={session_id:'a'};await switched.tick();
 assert.equal(switched.c.S.messages.length,1,'deliver the retained result when its chat is active again');
 assert.equal(switched.timers.size,0);
 const retry=setup();retry.c.startBackgroundPolling('a','one','Task');retry.fail(new Error('offline'));await new Promise(setImmediate);
 assert.equal(retry.timers.size,1);const retryDone=retry.tick();retry.complete({results:[{task_id:'one',answer:'Recovered'}]});await retryDone;
 assert.equal(retry.c.S.messages.length,1);assert.equal(retry.timers.size,0);
 const denied=setup();denied.c.startBackgroundPolling('a','one','Task');denied.fail({status:403});await new Promise(setImmediate);assert.equal(denied.timers.size,0);
 const deleted=setup();deleted.c.startBackgroundPolling('a','one','Task');deleted.c.stopBackgroundPolling('a');
 deleted.complete({results:[{task_id:'one',answer:'Late result'}]});await new Promise(setImmediate);
 assert.equal(deleted.c.S.messages.length,0);assert.equal(deleted.timers.size,0);
 const loading=setup();loading.c._loadingSessionId='a';loading.c.startBackgroundPolling('a','one','Task');
 assert.equal(loading.requests,0);loading.c.stopBackgroundPolling('a');assert.equal(loading.timers.size,0);
 console.log('background polling: coalescing, delivery, session ownership and cleanup passed');
})().catch(e=>{console.error(e);process.exitCode=1});
