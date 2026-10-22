import subprocess
from pathlib import Path


def test_browser_warmup_is_debounced_private_and_nonblocking():
    source=Path('static/boot.js').read_text()
    start=source.index('(function installComposerRuntimeWarmup(){')
    end=source.index('// End composer runtime warmup.',start)
    code=source[start:end]
    harness=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const handlers={}, timers=[], calls=[];
const composer={value:'PRIVATE DRAFT',addEventListener:(event,fn)=>handlers[event]=fn};
const document={hidden:false,activeElement:composer};
let now=0;
const context={document,$:()=>composer,setTimeout:fn=>{timers.push(fn);return timers.length;},
 Date:{now:()=>now},Promise,api:(url,options)=>{calls.push({url,options});return Promise.resolve({state:'ready'});}};
vm.runInNewContext(CODE,context);
(async()=>{
 handlers.focus(); handlers.input(); handlers.input(); assert.equal(timers.length,1);
 timers.shift()(); await new Promise(setImmediate);
 assert.equal(calls.length,1); assert.equal(calls[0].options.body,'{}');
 assert.equal(calls[0].url,'/api/chat/prewarm');
 handlers.input(); assert.equal(timers.length,0);
 now=31000; handlers.input(); document.activeElement=null; timers.shift()();
 await new Promise(setImmediate); assert.equal(calls.length,1);
 document.activeElement=composer; document.hidden=true; handlers.focus(); assert.equal(timers.length,0);
})().catch(e=>{console.error(e);process.exit(1);});
'''
    import json
    subprocess.run(['node','-e','const CODE='+json.dumps(code)+';\n'+harness],check=True)
