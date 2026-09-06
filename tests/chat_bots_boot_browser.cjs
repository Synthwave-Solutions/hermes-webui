const assert=require('node:assert/strict'),{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const b=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||undefined});
 try{
 const p=await b.newPage();
 await p.setContent('<div id="composerWrap"><textarea id="msg"></textarea></div>');
 await p.evaluate(()=>{
 window.__GOV_ME__={email:'alice@example.test'};
 window.S={session:null,activeProfile:'default',_bootReady:false};
 window.t=k=>k; window.botAvatarHtml=()=>''; window.botDisplayName=p=>p.name;
 window.calls=[]; window.api=url=>new Promise((resolve,reject)=>calls.push({url,resolve,reject}));
 window.switches=[]; window.switchToProfile=async name=>switches.push(name);
 });
 await p.addScriptTag({path:'static/chat-bots.js'});
 assert.equal(await p.locator('.chat-bot-roster-state').textContent(),'Loading bots…');
 const resolve=async(index,value)=>p.evaluate(({index,value})=>calls[index].resolve(value),{index,value});
 const profiles=names=>({profiles:names.map(name=>({name}))});
 assert.deepEqual(await p.evaluate(()=>calls.map(c=>c.url)),['/api/profiles?fast=1','/api/people']);
 // The unresolved people request must not delay the fast bot roster.
 await resolve(0,profiles(['default','research']));
 await p.locator('[data-bot="research"]').waitFor();
 assert.equal(await p.locator('[data-bot="research"]').isDisabled(),true);
 await p.evaluate(()=>document.querySelector('[data-bot="research"]').onclick());
 assert.deepEqual(await p.evaluate(()=>switches),[]);
 await p.evaluate(()=>{S._bootReady=true;dispatchEvent(new Event('synpulse:boot-ready'));});
 assert.equal(await p.locator('[data-bot="research"]').isDisabled(),false);
 await resolve(1,{people:[]});
 await p.evaluate(()=>{S.session={session_id:'group',bot_participants:['research']};refreshChatBots();});
 assert.equal(await p.locator('[data-bot]').count(),0);
 await resolve(3,{people:[{email:'bob@example.test',display_name:'Bob'}]});
 await p.evaluate(()=>calls[2].reject(new Error('unavailable')));
 await p.waitForFunction(()=>document.querySelector('.chat-bot-roster-state')?.textContent==='No available bots');
 await p.evaluate(()=>refreshChatBots());
 assert.equal(await p.evaluate(()=>calls.length),6);
 await resolve(4,profiles(['research']));
 await p.locator('[data-bot="research"]').waitFor();
 // A retry retains the successfully loaded people directory while its new request is pending.
 await p.locator('#msg').fill('@bob');
 await p.locator('[data-mention-id="bob@example.test"]').waitFor();
 await p.evaluate(()=>{S.session={session_id:'other',bot_participants:['default']};refreshChatBots();});
 await resolve(5,{people:[{email:'stale@example.test'}]});
 await resolve(6,profiles(['default','research']));
 await p.locator('[data-bot="default"]').waitFor();
 assert.equal(await p.locator('[data-bot="research"]').count(),0);
 await resolve(7,{people:[]});
 await p.evaluate(()=>{S._bootReady=false;S.session=null;S.activeProfile='';refreshChatBots();S.activeProfile='research';S._bootReady=true;dispatchEvent(new Event('synpulse:boot-ready'));});
 assert.equal(await p.evaluate(()=>calls.length),12);
 await resolve(8,profiles(['stale-profile'])); await resolve(9,{people:[]});
 assert.equal(await p.locator('[data-bot="stale-profile"]').count(),0);
 await resolve(10,profiles(['research']));
 await p.locator('[data-bot="research"]').waitFor();
 assert.equal(await p.locator('[data-bot="research"]').isDisabled(),false);
 await resolve(11,{people:[]});
 assert.equal(await p.locator('.chat-bot-roster-state').count(),0);
 await p.evaluate(()=>{window.__GOV_ME__={};refreshChatBots();});
 assert.equal(await p.evaluate(()=>calls.length),13);
 assert.equal(await p.evaluate(()=>calls[12].url),'/api/profiles?fast=1');
 await resolve(12,profiles(['research']));
 await p.locator('[data-bot="research"]').waitFor();
 // Exercise the actual identity-settle hook, not a manual roster refresh.
 const govSource=require('fs').readFileSync('static/governance.js','utf8');
 const govFetch=govSource.slice(govSource.indexOf('async function _govFetchMe()'),govSource.indexOf('/**',govSource.indexOf('async function _govFetchMe()')));
 await p.addScriptTag({content:govFetch});
 await p.evaluate(()=>{window.identityPromise=_govFetchMe();});
 assert.equal(await p.evaluate(()=>calls[13].url),'/api/governance/me');
 await resolve(13,{email:'bob@example.test'});
 await p.evaluate(()=>identityPromise);
 assert.deepEqual(await p.evaluate(()=>calls.slice(14).map(c=>c.url)),['/api/profiles?fast=1','/api/people']);
 await resolve(14,profiles(['research'])); await resolve(15,{people:[]});
 console.log('PASS early loading, slow people, no boot switch, retry retains people, stale context exclusion');
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exit(1)});
