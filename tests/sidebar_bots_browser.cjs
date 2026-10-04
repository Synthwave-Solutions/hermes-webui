const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||undefined});
 try{for(const width of [1440,1024,390]){
  const p=await browser.newPage({viewport:{width,height:900}});
  await p.route('**/*',r=>r.fulfill({contentType:'text/html',body:'<html></html>'}));await p.goto('http://ui.test/');
  const html=fs.readFileSync('static/index.html','utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<link\b[^>]*>/gi,'');
  await p.setContent(html);await p.addStyleTag({path:'static/style.css'});
  await p.evaluate(()=>{
   document.documentElement.classList.add('dark');document.documentElement.dataset.navAudience='admin';
   document.querySelector('.sidebar').classList.add('mobile-open');
   window.__GOV_ME__={email:'alice@example.test'};
   window.S={session:{session_id:'group',bot_participants:['writer']},activeProfile:'writer',_bootReady:true};
   window.t=k=>({tab_profiles:'Bots',tab_projects:'Projecten'}[k]||k);
   window.botAvatarHtml=()=>'<svg aria-hidden="true" viewBox="0 0 32 32"><circle cx="16" cy="16" r="12" fill="currentColor"/></svg>';
   window.botDisplayName=p=>p.name;window.showToast=m=>window.lastError=m;
   window.api=async url=>url.includes('profiles')?{profiles:[{name:'writer'},{name:'reviewer'},{name:'research'},{name:'hidden',visible:false}]}:{people:[]};
   window.switches=[];window.switchPanel=()=>{throw Error('Must remain in chat');};
   window.switchToProfile=name=>{switches.push(name);return new Promise((resolve,reject)=>{window.completeSwitch=()=>{S.activeProfile=name;resolve(true)};window.failSwitch=()=>reject(Error('Switch failed'));});};
  });
  await p.addScriptTag({path:'static/chat-bots.js'});
  const source=fs.readFileSync('static/sessions.js','utf8');
  const start=source.indexOf('  // Project filter bar',source.indexOf('function renderSessionListFromCache'));
  const end=source.indexOf('  // Profile filter toggle',start);
  await p.evaluate(code=>{
   const list=document.getElementById('sessionList');
   const profileFiltered=[],_allProjects=[{project_id:'demo',name:'Project A'}],_activeProject=null,NO_PROJECT_FILTER='none';
   window.renderFixture=()=>{list.replaceChildren();eval(code);};renderFixture();
  },source.slice(start,end));
  assert.equal(await p.locator('#sidebarBots').getAttribute('open'),null);
  await p.locator('#sidebarBots summary').click();
  await p.waitForFunction(()=>localStorage.getItem('synpulse:sidebar-bots-collapsed:alice@example.test')==='0');
  assert.deepEqual(await p.locator('[data-sidebar-bot]').evaluateAll(rows=>rows.map(r=>r.dataset.sidebarBot)),['writer','reviewer','research']);
  assert.equal(await p.locator('[data-sidebar-bot="hidden"]').count(),0);
  assert.equal(await p.locator('[data-sidebar-bot="writer"]').getAttribute('aria-pressed'),'true');
  const rect=await p.locator('#sidebarBots').boundingBox();assert.ok(rect.x>=0&&rect.x+rect.width<=width);
  await p.locator('[data-sidebar-bot="reviewer"]').click();
  assert.equal(await p.locator('[data-sidebar-bot="research"]').isDisabled(),true);
  await p.evaluate(()=>completeSwitch());
  await p.waitForFunction(()=>document.querySelector('[data-sidebar-bot="reviewer"]')?.getAttribute('aria-pressed')==='true');
  assert.deepEqual(await p.evaluate(()=>switches),['reviewer']);
  await p.evaluate(()=>renderFixture());
  assert.equal(await p.locator('[data-sidebar-bot="research"]').isVisible(),true);
  await p.locator('[data-sidebar-bot="research"]').click();await p.evaluate(()=>failSwitch());
  await p.waitForFunction(()=>lastError==='Switch failed');
  assert.equal(await p.locator('[data-sidebar-bot="reviewer"]').getAttribute('aria-pressed'),'true');
  assert.equal(await p.locator('[data-sidebar-bot="research"]').isDisabled(),false);
  if(process.env.SIDEBAR_BOTS_SCREENSHOTS)await p.screenshot({path:process.env.SIDEBAR_BOTS_SCREENSHOTS+'/bots-'+width+'.png'});
  await p.locator('#sidebarBots summary').click();
  await p.waitForFunction(()=>localStorage.getItem('synpulse:sidebar-bots-collapsed:alice@example.test')==='1');
  await p.evaluate(()=>renderFixture());assert.equal(await p.locator('[data-sidebar-bot="writer"]').isVisible(),false);
  assert.equal(await p.locator('.session-source-tabs').count(),0);
  // Identity changes discard the old catalog before the new response arrives.
  await p.evaluate(()=>{window.__GOV_ME__={email:'bob@example.test'};window.api=()=>new Promise(()=>{});refreshChatBots();});
  assert.equal(await p.locator('[data-sidebar-bot]').count(),0);
  console.log('PASS sidebar bots:',width);await p.close();
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
