// Behaviour of static/error-reporter.js (plan 3.3, W7).
//
// Runs the real file in a Node vm context with a fake window: listeners,
// timers and fetch are recorded, nothing leaves the process. Checks that the
// file installs nothing and sends nothing unless GET /api/settings says
// support_telemetry is true, and what a report looks like when it is.
// Run: node tests/error_reporter.cjs (tests/test_ops_reporter.py runs it).
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const ROOT=path.resolve(__dirname,'..');
const SOURCE=fs.readFileSync(path.join(ROOT,'static/error-reporter.js'),'utf8');
const ORIGIN='https://app.test';

function makeWorld(opts){
  opts=opts||{};
  const listeners={};
  const timers=[];
  const fetches=[];
  const window={
    addEventListener(type,fn){(listeners[type]=listeners[type]||[]).push(fn);},
    setTimeout(fn,ms){timers.push({fn,ms});return timers.length;},
    location:{origin:ORIGIN,href:ORIGIN+'/session/abc?x=1#y',pathname:'/session/abc'},
    document:{baseURI:ORIGIN+'/'},
    fetch(url,init){
      fetches.push({url:String(url),init:init||{}});
      if(String(url)===ORIGIN+'/api/settings'){
        if(opts.settingsFail)return Promise.reject(new TypeError('offline'));
        if(opts.settingsStatus&&opts.settingsStatus!==200){
          return Promise.resolve({ok:false,status:opts.settingsStatus,json:()=>Promise.resolve({})});
        }
        return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve(opts.settings||{})});
      }
      return Promise.resolve({ok:true,status:204});
    }
  };
  if(opts.noFetch)delete window.fetch;
  const context={window,URL,JSON,Object,String,Array,Promise,console};
  vm.createContext(context);
  const before=new Set(Object.getOwnPropertyNames(context));
  const windowBefore=new Set(Object.keys(window));
  vm.runInContext(SOURCE,context,{filename:'static/error-reporter.js'});
  const added=Object.getOwnPropertyNames(context).filter(n=>!before.has(n))
    .concat(Object.keys(window).filter(n=>!windowBefore.has(n)));
  return {
    window,listeners,timers,fetches,added,
    fire(type,event){(listeners[type]||[]).forEach(fn=>fn(event));},
    posts(){return fetches.filter(f=>f.url===ORIGIN+'/api/client-errors');},
    reports(){return this.posts().map(f=>JSON.parse(f.init.body));}
  };
}

const flush=()=>new Promise(resolve=>setImmediate(resolve));

function errorWithStack(name,message,stack){
  const error=new Error(message);
  error.name=name;
  error.stack=stack;
  return error;
}

const CHROME_STACK=[
  'TypeError: Cannot read properties of undefined (reading \'id\')',
  '    at renderMessage ('+ORIGIN+'/static/ui.js?v=1.2.3:120:15)',
  '    at https://cdn.other.example/static/lib.js:1:1',
  '    at Array.forEach (<anonymous>)',
  '    at renderMessages ('+ORIGIN+'/session/static/messages.js:40:3)',
  '    at '+ORIGIN+'/static/boot.js#frag:9:1'
].join('\n');

const GECKO_STACK=[
  'renderMessage@'+ORIGIN+'/static/ui.js?v=1:120:15',
  '@'+ORIGIN+'/static/boot.js:9:1'
].join('\n');

const checks=[];
function check(name,fn){checks.push({name,fn});}

check('defines no globals and needs a real window',async()=>{
  const world=makeWorld({settings:{support_telemetry:true}});
  assert.deepEqual(world.added,[]);
  const ctx={window:{}};
  vm.createContext(ctx);
  vm.runInContext(SOURCE,ctx);
  assert.deepEqual(Object.keys(ctx.window),[]);
  const noFetch=makeWorld({noFetch:true});
  assert.deepEqual(Object.keys(noFetch.listeners),[]);
  assert.equal(noFetch.timers.length,0);
});

check('before the flag is known nothing is installed and nothing is sent',async()=>{
  const world=makeWorld({settings:{support_telemetry:true}});
  assert.deepEqual(Object.keys(world.listeners),['synpulse:boot-ready']);
  assert.equal(world.fetches.length,0);
  assert.equal(world.timers.length,1);
  assert.equal(world.timers[0].ms,15000);
});

for(const [label,opts] of [
  ['support_telemetry false',{settings:{support_telemetry:false}}],
  ['support_telemetry missing',{settings:{}}],
  ['support_telemetry truthy but not true',{settings:{support_telemetry:'true'}}],
  ['settings answer 401',{settingsStatus:401}],
  ['settings request fails',{settingsFail:true}]
]){
  check('off when '+label,async()=>{
    const world=makeWorld(opts);
    world.fire('synpulse:boot-ready',{});
    await flush();await flush();
    assert.equal(world.fetches.length,1);
    assert.equal(world.fetches[0].url,ORIGIN+'/api/settings');
    assert.equal(world.fetches[0].init.method,undefined);
    assert.equal(world.fetches[0].init.credentials,'same-origin');
    assert.equal(world.listeners.error,undefined);
    assert.equal(world.listeners.unhandledrejection,undefined);
    world.fire('error',{error:errorWithStack('TypeError','x',CHROME_STACK),message:'x'});
    world.fire('unhandledrejection',{reason:new Error('y')});
    await flush();
    assert.equal(world.posts().length,0);
  });
}

check('the flag is read once, from boot-ready or the fallback timer',async()=>{
  const world=makeWorld({settings:{support_telemetry:true}});
  world.timers[0].fn();
  world.fire('synpulse:boot-ready',{});
  world.fire('synpulse:boot-ready',{});
  await flush();await flush();
  assert.equal(world.fetches.filter(f=>f.url===ORIGIN+'/api/settings').length,1);
  assert.equal(world.listeners.error.length,1);
  assert.equal(world.listeners.unhandledrejection.length,1);
});

async function onWorld(){
  const world=makeWorld({settings:{support_telemetry:true}});
  world.fire('synpulse:boot-ready',{});
  await flush();await flush();
  return world;
}

check('an uncaught error is reported with own static frames only',async()=>{
  const world=await onWorld();
  world.fire('error',{error:errorWithStack('TypeError','Cannot read id',CHROME_STACK),message:'Uncaught TypeError'});
  await flush();
  const posts=world.posts();
  assert.equal(posts.length,1);
  const init=posts[0].init;
  assert.equal(init.method,'POST');
  assert.equal(init.credentials,'same-origin');
  assert.equal(init.keepalive,true);
  assert.equal(init.headers['Content-Type'],'application/json');
  const report=JSON.parse(init.body);
  assert.deepEqual(Object.keys(report).sort(),['frames','kind','message','type','url_path']);
  assert.equal(report.kind,'error');
  assert.equal(report.type,'TypeError');
  assert.equal(report.message,'Cannot read id');
  assert.equal(report.url_path,'/session/abc');
  assert.deepEqual(report.frames,[
    {'function':'?','file':'static/boot.js'},
    {'function':'renderMessages','file':'static/messages.js'},
    {'function':'renderMessage','file':'static/ui.js'}
  ]);
  assert.ok(!init.body.includes('cdn.other.example'));
  assert.ok(!init.body.includes('v=1.2.3'));
  assert.ok(!init.body.includes('x=1'));
});

check('Firefox and Safari stacks are read too',async()=>{
  const world=await onWorld();
  world.fire('error',{error:errorWithStack('RangeError','bad',GECKO_STACK),message:'bad'});
  await flush();
  assert.deepEqual(world.reports()[0].frames,[
    {'function':'?','file':'static/boot.js'},
    {'function':'renderMessage','file':'static/ui.js'}
  ]);
});

check('unhandled rejections are reported',async()=>{
  const world=await onWorld();
  world.fire('unhandledrejection',{reason:'plain string reason'});
  world.fire('unhandledrejection',{reason:errorWithStack('SyntaxError','bad json','')});
  world.fire('unhandledrejection',{reason:undefined});
  await flush();
  const reports=world.reports();
  assert.equal(reports.length,3);
  assert.equal(reports[0].type,'UnhandledRejection');
  assert.equal(reports[0].message,'plain string reason');
  assert.equal(reports[0].kind,'unhandledrejection');
  assert.equal(reports[1].type,'SyntaxError');
  assert.equal(reports[2].message,'');
});

check('messages are shortened and odd error names are not trusted',async()=>{
  const world=await onWorld();
  world.fire('error',{error:errorWithStack('Bad Name<script>','m'.repeat(2000),''),message:'x'});
  await flush();
  const report=world.reports()[0];
  assert.equal(report.type,'Error');
  assert.equal(report.message.length,500);
});

check('cross-origin script errors and empty events are ignored',async()=>{
  const world=await onWorld();
  world.fire('error',{message:'Script error.'});
  world.fire('error',{});
  world.fire('error',null);
  world.fire('unhandledrejection',null);
  await flush();
  assert.equal(world.posts().length,0);
  world.fire('error',{message:'ReferenceError: foo is not defined'});
  await flush();
  assert.equal(world.reports()[0].message,'ReferenceError: foo is not defined');
});

check('duplicates are sent once and a page sends at most ten reports',async()=>{
  const world=await onWorld();
  for(let i=0;i<3;i++)world.fire('error',{error:errorWithStack('TypeError','same',CHROME_STACK)});
  assert.equal(world.posts().length,1);
  for(let i=0;i<30;i++)world.fire('error',{error:errorWithStack('TypeError','distinct '+i,CHROME_STACK)});
  await flush();
  assert.equal(world.posts().length,10);
});

check('a failing send or a throwing fetch never throws',async()=>{
  const world=await onWorld();
  world.window.fetch=()=>{throw new Error('blocked');};
  world.fire('error',{error:new Error('a')});
  world.window.fetch=()=>Promise.reject(new Error('offline'));
  world.fire('error',{error:new Error('b')});
  await flush();
});

(async()=>{
  let failed=0;
  for(const {name,fn} of checks){
    try{await fn();console.log('ok - '+name);}
    catch(error){failed+=1;console.log('not ok - '+name);console.log(error&&error.stack||error);}
  }
  if(failed){console.log(failed+' error-reporter check(s) failed');process.exit(1);}
  console.log('all error-reporter checks passed ('+checks.length+')');
})();
