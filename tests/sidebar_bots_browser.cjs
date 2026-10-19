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
   window.esc=v=>String(v).replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
   window.scoutCalls=[];window.confirms=[];window.confirmAnswer=false;window.showConfirmDialog=async o=>{confirms.push(o);return confirmAnswer;};window._botScreenSinceText=ts=>ts?'waiting since '+ts:'';
   window.api=async(url,opts)=>{if(url==='/api/bots/scout'){scoutCalls.push(JSON.parse(opts.body));return {ok:true};}
    if(url==='/api/bot-screen/status')return {screens:[{bot:'reviewer',state:'waiting',reason:'please log in',help_since:1760000000},{bot:'writer',state:'agent'}]};
    return url.includes('profiles')?{profiles:[{name:'default',is_default:true,bot_kind:'bot'},{name:'writer',bot_kind:'bot',bot_editable:true,bot_revision:3,bot:{category:'Content'}},{name:'reviewer',bot_kind:'bot',bot:{category:'Content',scout:{enabled:true,topics:[],digest_time:'07:30'}}},{name:'research',bot_kind:'person',bot_editable:true},{name:'hidden',visible:false}]}:{people:[]};};
   window.switches=[];window.switchPanel=()=>{throw Error('Must remain in chat');};
   window.switchToProfile=name=>{switches.push(name);return new Promise((resolve,reject)=>{window.completeSwitch=()=>{S.activeProfile=name;resolve(true)};window.failSwitch=()=>reject(Error('Switch failed'));});};
  });
  // The grouped renderer the Bots panel uses, taken from panels.js as is.
  const panels=fs.readFileSync('static/panels.js','utf8');
  const groupStart=panels.indexOf('function spRenderGrouped(');
  await p.addScriptTag({content:panels.slice(groupStart,panels.indexOf('window.spRenderGrouped',groupStart))+';window.spRenderGrouped=spRenderGrouped;'});
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
  await p.locator('#sidebarBots > summary').click();
  await p.waitForFunction(()=>localStorage.getItem('synpulse:sidebar-bots-collapsed:alice@example.test')==='0');
  assert.deepEqual(await p.locator('[data-sidebar-bot]').evaluateAll(rows=>rows.map(r=>r.dataset.sidebarBot)),['default','writer','reviewer','research']);
  assert.equal(await p.locator('[data-sidebar-bot="hidden"]').count(),0);
  // SynthPulse on top outside the groups, then categories, "no category" last.
  assert.equal(await p.locator('#sidebarBotItems > .sidebar-bot-row > [data-sidebar-bot="default"]').count(),1);
  // Scout: a toggle where this person may edit the bot, a mark where it is on
  // but not theirs, nothing on a person's own profile.
  assert.deepEqual(await p.locator('button[data-scout-bot]').evaluateAll(b=>b.map(x=>[x.dataset.scoutBot,x.getAttribute('aria-pressed')])),[['writer','false']]);
  assert.equal(await p.locator('[data-sidebar-bot="reviewer"] + span.sidebar-bot-scout.is-on').count(),1);
  assert.equal(await p.locator('[data-sidebar-bot="research"] + .sidebar-bot-scout').count(),0);
  // A bot whose screen waits for a person carries a small dot, nothing else does.
  assert.deepEqual(await p.locator('.sidebar-bot-screen-wait').evaluateAll(d=>d.map(x=>[x.parentElement.querySelector('[data-sidebar-bot]').dataset.sidebarBot,x.title])),[['reviewer','Bot screen waits for you: please log in · waiting since 1760000000']]);
  assert.equal(await p.locator('button[data-scout-bot="writer"]').getAttribute('title'),'Scout on/off');
  // Hit area of at least 24px.
  const box=await p.locator('button[data-scout-bot="writer"]').boundingBox();
  assert.ok(box.width>=24&&box.height>=24,'scout toggle hit area '+box.width+'x'+box.height);
  // First time on for a bot: a confirm with the time; cancel changes nothing.
  await p.locator('button[data-scout-bot="writer"]').click();
  await p.waitForFunction(()=>confirms.length===1);
  assert.deepEqual(await p.evaluate(()=>[confirms[0].title,confirms[0].message,confirms[0].confirmLabel]),['Turn Scout on?','This bot gets a daily Scout task at 07:30. Read only, notifications off.','Turn Scout on']);
  assert.equal(await p.evaluate(()=>scoutCalls.length),0);
  await p.evaluate(()=>{confirmAnswer=true;});
  await p.locator('button[data-scout-bot="writer"]').click();
  await p.waitForFunction(()=>scoutCalls.length===1);
  assert.deepEqual(await p.evaluate(()=>scoutCalls[0]),{name:'writer',enabled:true,revision:3});
  assert.deepEqual(await p.evaluate(()=>switches),[]);
  await p.waitForFunction(()=>!document.querySelector('button[data-scout-bot="writer"]').disabled);
  assert.deepEqual(await p.locator('#sidebarBotItems .sp-group .cron-group-name').allTextContents(),['Content','cron_category_none']);
  assert.deepEqual(await p.locator('#sidebarBotItems .sp-group .cron-group-count').allTextContents(),['2','1']);
  await p.locator('#sidebarBotItems .sp-group summary').first().click();
  await p.waitForFunction(()=>localStorage.getItem('synpulse:sidebar-bots-group:alice@example.test:Content')==='1');
  assert.equal(await p.locator('[data-sidebar-bot="writer"]').isVisible(),false);
  await p.evaluate(()=>{document.getElementById('sidebarBotItems').dataset.state='';refreshChatBots();});
  await p.waitForFunction(()=>document.querySelector('#sidebarBotItems .sp-group')&&!document.querySelector('#sidebarBotItems .sp-group').open);
  await p.locator('#sidebarBotItems .sp-group summary').first().click();
  assert.equal(await p.locator('[data-sidebar-bot="writer"]').isVisible(),true);
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
  await p.locator('#sidebarBots > summary').click();
  await p.waitForFunction(()=>localStorage.getItem('synpulse:sidebar-bots-collapsed:alice@example.test')==='1');
  await p.evaluate(()=>renderFixture());assert.equal(await p.locator('[data-sidebar-bot="writer"]').isVisible(),false);
  assert.equal(await p.locator('.session-source-tabs').count(),0);
  // Identity changes discard the old catalog before the new response arrives.
  await p.evaluate(()=>{window.__GOV_ME__={email:'bob@example.test'};window.api=()=>new Promise(()=>{});refreshChatBots();});
  assert.equal(await p.locator('[data-sidebar-bot]').count(),0);
  console.log('PASS sidebar bots:',width);await p.close();
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
