const assert=require('node:assert/strict'),{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||undefined});try{
for(const width of [1440,390]){
const page=await browser.newPage({viewport:{width,height:800}});
await page.setContent('<div id="composerWrap"><textarea id="msg"></textarea></div>');
await page.evaluate(()=>{
window.__GOV_ME__={email:'test@example.test'};window.S={session:{session_id:'group',bot_participants:['alpha','beta']},activeProfile:'alpha',_bootReady:true};
window.t=k=>k;window.botAvatarHtml=()=>'';window.botDisplayName=p=>p.name;
window.api=async url=>url.includes('profiles')?{profiles:[{name:'alpha'},{name:'beta'}]}:{people:[]};
});
await page.addScriptTag({path:'static/chat-bots.js'});
await page.locator('[data-bot="alpha"]').waitFor();
await page.evaluate(()=>{window.firstButton=document.querySelector('[data-bot="alpha"]');window.mutations=0;new MutationObserver(rows=>window.mutations+=rows.length).observe(document.querySelector('#chatBotRoster'),{childList:true,subtree:true});});
await page.locator('#msg').fill('A normal message without mentions');
await page.waitForTimeout(50);
assert.equal(await page.evaluate(()=>firstButton===document.querySelector('[data-bot="alpha"]')),true,'typing must preserve recipient buttons');
assert.equal(await page.evaluate(()=>mutations),0,'ordinary typing must not rebuild the roster');
await page.locator('#msg').fill('@beta Please review');
assert.equal(await page.locator('[data-bot="beta"]').getAttribute('aria-pressed'),'true');
assert.equal(await page.locator('[data-bot="alpha"]').getAttribute('aria-pressed'),'false');
await page.locator('#msg').fill('No mention');
assert.equal(await page.locator('[data-bot="beta"]').getAttribute('aria-pressed'),'false');
console.log(JSON.stringify({width,rosterMutations:await page.evaluate(()=>mutations),passed:true}));await page.close();
}}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
