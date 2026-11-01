// Behaviour of the guided tours, Explain this page and What's new (plan 6.2, W4).
//
// Runs the real static/help-tour.js, static/help-content.js and the vendored
// Guida build in headless Chromium against a small copy of the app shell. The
// page is served from a fake origin by Playwright routes: nothing leaves the
// browser, and /api/settings and /api/help/events are answered here.
// Run: node tests/help_tour_behavior.cjs (PLAYWRIGHT_MODULE may point at a
// Playwright package; tests/test_guida_vendored_assets.py runs it in pytest).
'use strict';
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');

const ROOT=path.resolve(__dirname,'..');
const ORIGIN='http://help.test';
const MEMBER='ada@example.test';

// The English values of the W4 keys, straight from the locale bundle.
const EN={};
for(const match of fs.readFileSync(path.join(ROOT,'static/i18n/en.js'),'utf8')
  .matchAll(/^\s*((?:help|cmd)_[a-z_]+):\s*'((?:[^'\\]|\\.)*)'/gm)){
  EN[match[1]]=match[2].replace(/\\'/g,"'");
}
assert.equal(EN.help_tour_next,'Next');
assert.equal(EN.help_tour_step_of,'Step {0} of {1}');

function navButtons(){
  return ['chat','profiles','tasks','workspaces','kanban'].map(id=>`<button class="nav-tab" data-panel="${id}">${id}</button>`).join('')
    +'<button class="nav-tab" data-panel="governance" style="display:none">governance</button>'
    +'<button class="nav-tab" data-panel="modules" data-module-gated hidden>modules</button>'
    +'<button class="nav-tab" data-panel="settings">settings</button>';
}

function shell(opts){
  const scripts=[];
  if(opts.guida!==false)scripts.push('static/vendor/guida/0.2.0/guida.umd.js');
  scripts.push('static/help-content.js','static/help-tour.js');
  return `<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="static/help-tour.css">
<style>
 body{margin:0;font:14px sans-serif;--surface:#fff;--text:#111;--muted:#555;--border:#ddd;--border2:#ccc;--accent:#0a7;--accent-bg:#e6f7f1;--accent-text:#075;--input-bg:#fafafa;--hover-bg:#eee;}
 .app-titlebar{height:40px;display:flex;align-items:center;gap:8px;padding:0 8px;border-bottom:1px solid #ddd}
 .layout{display:flex;height:calc(100vh - 41px)}
 .rail{display:none;flex-direction:column;width:48px}
 .sidebar{width:260px;display:flex;flex-direction:column}
 .panel-view{display:none}.panel-view.active{display:block}
 main{flex:1;display:flex;flex-direction:column;justify-content:flex-end;padding:8px}
 #btnHamburger{display:none}
 @media(min-width:641px){.rail{display:flex}.sidebar>.sidebar-nav{display:none}}
 @media(max-width:640px){#btnHamburger{display:inline-block}.sidebar{position:fixed;left:0;top:0;bottom:0;width:100vw;background:#fff;transform:translateX(-100%)}.sidebar.mobile-open{transform:none}}
</style></head><body>
<header class="app-titlebar">
 <button id="btnHamburger" type="button" data-tour="menu-button">Menu</button>
 <span style="flex:1">SynthPulse</span>
 <button id="btnPageHelp" type="button" data-tour="help-button" aria-label="Explain this page">?</button>
</header>
<div class="layout">
 <nav class="rail">${navButtons()}</nav>
 <aside class="sidebar">
  <div class="sidebar-nav">${navButtons()}</div>
  <div class="panel-view active" id="panelChat"><button id="btnNewChat" data-tour="chat-new">New chat</button><div id="sessionList" data-tour="chat-list">Chats</div></div>
  <div class="panel-view" id="panelTasks"><button data-tour="tasks-new">New job</button><div data-tour="tasks-list">Jobs</div></div>
  <div class="panel-view" id="panelProfiles"></div>
  <div class="panel-view" id="panelGovernance"><div data-tour="governance-intro">Roles</div></div>
  <div class="panel-view" id="panelSettings"><div data-tour="settings-menu">Menu</div></div>
 </aside>
 <main>
  <button id="composerPeopleChip" data-tour="chat-people">People</button>
  <textarea id="msg" data-tour="chat-composer"></textarea>
  <div><button id="btnAttach" data-tour="chat-attach">Attach</button><button id="profileChip" data-tour="chat-bot">Bot</button></div>
 </main>
</div>
<button id="outside" type="button">Outside</button>
<script>
 let _currentPanel='chat';
 window.panelSwitches=[];
 async function switchPanel(name){
   window.panelSwitches.push(name);
   _currentPanel=name;
   document.querySelectorAll('.panel-view').forEach(p=>p.classList.remove('active'));
   const view=document.getElementById('panel'+name.charAt(0).toUpperCase()+name.slice(1));
   if(view)view.classList.add('active');
   return true;
 }
 function _isDesktopWidth(){return window.matchMedia('(min-width:641px)').matches;}
 const HELP_EN=${JSON.stringify(EN)};
 function t(key,...args){let v=HELP_EN[key];if(v===undefined)return key;args.forEach((a,i)=>{v=v.split('{'+i+'}').join(String(a));});return v;}
 window.toasts=[];
 function showToast(message){window.toasts.push(message);}
 window.__GOV_ME__=${JSON.stringify(opts.me===undefined?{email:MEMBER,permissions:[],delegated_scope:'none'}:opts.me)};
 window.__HERMES_WEBUI_BUNDLE_VERSION__=${JSON.stringify(opts.version||'v0.53.0')};
 window._govHiddenNav=${JSON.stringify(opts.govHidden||[])};
 window.settingsCalls=0;
 window.api=async function(url){window.settingsCalls++;if(url!=='/api/settings')throw new Error('unexpected '+url);${opts.settingsFail?"throw new Error('offline');":''}return ${JSON.stringify(opts.settings||{enabled_modules:['workspace','group_chat','design_studio','workflows'],onboarding_completed:true})};};
 ${opts.preScript||''}
</script>
${scripts.map(src=>`<script src="${src}"></script>`).join('\n')}
</body></html>`;
}

async function open(browser,opts={}){
  const context=await browser.newContext({
    viewport:{width:opts.width||1280,height:opts.height||800},
    locale:opts.locale||'en-US',
    reducedMotion:'reduce',
  });
  if(opts.storage){
    await context.addInitScript(storage=>{
      if(window.location.origin!=='http://help.test')return;
      for(const [key,value] of Object.entries(storage))window.localStorage.setItem(key,value);
    },opts.storage);
  }
  const page=await context.newPage();
  const events=[];
  const errors=[];
  page.on('pageerror',err=>errors.push(String(err)));
  await page.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.origin!==ORIGIN)return route.abort();
    if(url.pathname==='/')return route.fulfill({status:200,contentType:'text/html',body:shell(opts)});
    if(url.pathname==='/api/help/events'){
      events.push(JSON.parse(route.request().postData()||'null'));
      return route.fulfill({status:204,body:''});
    }
    if(url.pathname.startsWith('/static/')){
      const file=path.join(ROOT,url.pathname);
      if(!file.startsWith(path.join(ROOT,'static'))||!fs.existsSync(file))return route.fulfill({status:404,body:''});
      const type=file.endsWith('.css')?'text/css':'application/javascript';
      return route.fulfill({status:200,contentType:type,body:fs.readFileSync(file)});
    }
    return route.fulfill({status:404,body:''});
  });
  await page.goto(ORIGIN+'/');
  await page.waitForFunction(()=>!!window.SynthPulseHelp);
  return {page,context,events,errors};
}

async function tooltipState(page){
  return page.evaluate(()=>{
    const tip=document.querySelector('.guida-tooltip.sp-help-tooltip.guida-visible');
    if(!tip)return null;
    const lit=document.querySelector('.guida-highlight');
    return {
      title:tip.querySelector('h3')?.textContent||'',
      body:tip.querySelector('.guida-tooltip-content > p')?.textContent||'',
      progress:tip.querySelector('.guida-progress span')?.textContent||'',
      role:tip.getAttribute('role'),modal:tip.getAttribute('aria-modal'),
      labelled:tip.getAttribute('aria-labelledby')===tip.querySelector('h3')?.id,
      buttons:Array.from(tip.querySelectorAll('.guida-controls button')).map(b=>b.textContent),
      focused:document.activeElement&&tip.contains(document.activeElement)?document.activeElement.textContent:null,
      lit:lit?(lit.getAttribute('data-tour')||lit.dataset.panel||lit.id||lit.tagName):null,
      litIn:lit?(lit.closest('.rail')?'rail':lit.closest('.sidebar-nav')?'sidebar':'other'):null,
    };
  });
}
async function waitStep(page,progress){
  await page.waitForFunction(p=>{
    const tip=document.querySelector('.guida-tooltip.sp-help-tooltip.guida-visible');
    const span=tip&&tip.querySelector('.guida-progress span');
    return !!(span&&span.textContent===p&&tip.querySelector('.guida-controls button'));
  },progress);
  return tooltipState(page);
}
async function noTour(page){
  await page.waitForFunction(()=>!document.querySelector('.guida-overlay')&&!document.querySelector('.guida-tooltip'));
}

const tests=[];
function test(name,fn){tests.push({name,fn});}

test('nothing starts on its own, and the tour is offered once after onboarding',async browser=>{
  const {page,context,errors}=await open(browser);
  await page.evaluate(()=>window.dispatchEvent(new Event('synpulse:boot-ready')));
  await page.waitForSelector('#spHelpCard[data-kind="tour_offer"]');
  assert.equal(await page.locator('.guida-overlay').count(),0);
  assert.equal(await page.locator('.guida-tooltip').count(),0);
  const card=await page.locator('#spHelpCard').innerText();
  assert.match(card,/Want a short tour of the basics\?/);
  await page.getByRole('button',{name:'Not now'}).click();
  assert.equal(await page.locator('#spHelpCard').count(),0);
  // A reload with the same storage offers nothing again.
  await page.reload();
  await page.waitForFunction(()=>!!window.SynthPulseHelp);
  await page.evaluate(()=>window.dispatchEvent(new Event('synpulse:boot-ready')));
  await page.waitForTimeout(400);
  assert.equal(await page.locator('#spHelpCard').count(),0);
  assert.equal(await page.locator('.guida-overlay').count(),0);
  assert.deepEqual(errors,[]);
  await context.close();
});

test('Getting started finishes in 6 steps with the keyboard only',async browser=>{
  const {page,context,events,errors}=await open(browser);
  await page.locator('#btnPageHelp').focus();
  const started=await page.evaluate(()=>window.SynthPulseHelp.startTour('first_run',{trigger:document.getElementById('btnPageHelp')}));
  assert.equal(started,true);
  let state=await waitStep(page,'Step 1 of 6');
  assert.equal(state.role,'dialog');assert.equal(state.modal,'true');assert.equal(state.labelled,true);
  assert.equal(state.title,'Start a chat');assert.equal(state.lit,'chat-composer');
  assert.equal(state.focused,'Next');
  assert.deepEqual(state.buttons,['Next','Close']);
  const titles=[state.title];
  for(let i=2;i<=6;i++){
    await page.keyboard.press('ArrowRight');
    state=await waitStep(page,`Step ${i} of 6`);
    titles.push(state.title);
  }
  assert.deepEqual(titles,['Start a chat','Pick a bot','Add a file','Work in a space','Schedule a task','Get help']);
  assert.equal(state.focused,'Done');
  assert.deepEqual(state.buttons,['Back','Close','Done']);
  // Back and forward with the arrows.
  await page.keyboard.press('ArrowLeft');
  assert.equal((await waitStep(page,'Step 5 of 6')).title,'Schedule a task');
  await page.keyboard.press('ArrowRight');
  await waitStep(page,'Step 6 of 6');
  // Tab stays inside the step card.
  for(let i=0;i<4;i++){
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(()=>!!document.activeElement.closest('.sp-help-tooltip')),true);
  }
  await page.getByRole('button',{name:'Done'}).focus();
  await page.keyboard.press('Enter');
  await noTour(page);
  assert.deepEqual(await page.evaluate(()=>window.toasts),['Tour completed']);
  assert.equal(await page.evaluate(()=>window.SynthPulseHelp.hasSeen('first_run')),true);
  assert.equal(await page.evaluate(()=>document.activeElement&&document.activeElement.id),'btnPageHelp');
  assert.equal(await page.evaluate(()=>document.querySelectorAll('[data-sp-help-step],.guida-highlight').length),0);
  await page.waitForTimeout(100);
  assert.deepEqual(events,[{event:'tour_started',tour:'first_run'},{event:'tour_completed',tour:'first_run'}]);
  assert.deepEqual(errors,[]);
  await context.close();
});

test('Escape closes a tour, marks it seen and returns focus',async browser=>{
  const {page,context}=await open(browser);
  await page.locator('#btnNewChat').focus();
  await page.evaluate(()=>window.SynthPulseHelp.startTour('first_run',{trigger:document.getElementById('btnNewChat')}));
  await waitStep(page,'Step 1 of 6');
  await page.keyboard.press('Escape');
  await noTour(page);
  assert.equal(await page.evaluate(()=>document.activeElement.id),'btnNewChat');
  assert.equal(await page.evaluate(()=>window.SynthPulseHelp.hasSeen('first_run')),true);
  assert.deepEqual(await page.evaluate(()=>window.toasts),[]);
  await context.close();
});

test('hidden panels and disabled modules are skipped',async browser=>{
  const {page,context}=await open(browser,{govHidden:['tasks']});
  assert.deepEqual(await page.evaluate(()=>window.SynthPulseHelp.stepsFor('first_run')),['chat','bots','files','spaces','help']);
  await page.evaluate(()=>document.querySelectorAll('[data-panel="workspaces"]').forEach(n=>n.classList.add('nav-tab-hidden')));
  assert.deepEqual(await page.evaluate(()=>window.SynthPulseHelp.stepsFor('first_run')),['chat','bots','files','help']);
  // A step or section that needs modules (all of) only shows when every one is on.
  await page.evaluate(()=>{
    const en=window.SynthPulseHelpContent.locales.en;
    en.tour_steps.kb={title:'Knowledge',body:'Ask your documents.',target:"[data-tour='chat-attach']",modules:['knowledge_base','notebook']};
    en.tour_steps.one={title:'One',body:'One module.',target:"[data-tour='chat-attach']",module:'knowledge_base'};
    en.tours.first_run=en.tours.first_run.concat(['kb','one']);
  });
  assert.deepEqual(await page.evaluate(()=>window.SynthPulseHelp.stepsFor('first_run')),['chat','bots','files','help']);
  await context.close();
  const both=await open(browser,{settings:{enabled_modules:['workspace','knowledge_base','notebook']}});
  await both.page.evaluate(()=>{
    const en=window.SynthPulseHelpContent.locales.en;
    en.tour_steps.kb={title:'Knowledge',body:'Ask your documents.',target:"[data-tour='chat-attach']",modules:['knowledge_base','notebook']};
    en.tour_steps.two={title:'Two',body:'Two modules.',target:"[data-tour='chat-attach']",modules:['knowledge_base','e_signing']};
    en.tours.first_run=en.tours.first_run.concat(['kb','two']);
  });
  assert.deepEqual(await both.page.evaluate(()=>window.SynthPulseHelp.stepsFor('first_run')),['chat','bots','files','spaces','tasks','help','kb']);
  await both.context.close();
  // A failed settings fetch hides every module-gated item (fail safe).
  const failed=await open(browser,{settingsFail:true});
  await failed.page.evaluate(()=>{
    const en=window.SynthPulseHelpContent.locales.en;
    en.tour_steps.one={title:'One',body:'One module.',target:"[data-tour='chat-attach']",module:'workspace'};
    en.tours.first_run=en.tours.first_run.concat(['one']);
  });
  assert.equal((await failed.page.evaluate(()=>window.SynthPulseHelp.stepsFor('first_run'))).includes('one'),false);
  await failed.context.close();
});

test('group chat help follows its module, governance help only for admins',async browser=>{
  const {page,context,events}=await open(browser,{settings:{enabled_modules:['workspace']}});
  await page.evaluate(()=>window.SynthPulseHelp.explainPage('group_chat'));
  // The chat page instead: its summary plus the five chat controls in the shell.
  let state=await waitStep(page,'Step 1 of 6');
  assert.equal(state.title,'Chats');
  await page.keyboard.press('Escape');
  await noTour(page);
  // A member asking for Governance gets the page they are on instead.
  await page.evaluate(()=>window.SynthPulseHelp.explainPage('governance'));
  state=await waitStep(page,'Step 1 of 6');
  assert.equal(state.title,'Chats');
  await page.keyboard.press('Escape');
  await noTour(page);
  assert.deepEqual(await page.evaluate(()=>window.panelSwitches),[]);
  await context.close();
  const admin=await open(browser,{me:{email:'root@example.test',permissions:['*'],delegated_scope:'platform'}});
  await admin.page.evaluate(()=>document.querySelectorAll('[data-panel="governance"]').forEach(n=>{n.style.display='';}));
  await admin.page.evaluate(()=>window.SynthPulseHelp.explainPage('governance'));
  state=await waitStep(admin.page,'Step 1 of 2');
  assert.equal(state.title,'Governance');
  assert.deepEqual(await admin.page.evaluate(()=>window.panelSwitches),['governance']);
  await admin.page.keyboard.press('ArrowRight');
  state=await waitStep(admin.page,'Step 2 of 2');
  assert.equal(state.lit,'governance-intro');
  assert.deepEqual(state.buttons,['Back','Close','Done']);
  await admin.page.getByRole('button',{name:'This did not help'}).click();
  assert.match(await admin.page.locator('.sp-help-feedback-thanks').innerText(),/Thanks/);
  await admin.page.keyboard.press('Escape');
  await noTour(admin.page);
  await admin.page.waitForTimeout(100);
  assert.deepEqual(admin.events,[{event:'explain_clicked',page:'governance'},{event:'did_not_help',page:'governance'}]);
  await admin.context.close();
  assert.deepEqual(events,[{event:'explain_clicked',page:'chat'},{event:'explain_clicked',page:'chat'}]);
});

test('a member sees no Governance step or page in the tours',async browser=>{
  const {page,context}=await open(browser);
  await page.evaluate(()=>{
    const en=window.SynthPulseHelpContent.locales.en;
    en.tour_steps.gov={title:'Governance',body:'Admins only.',nav:'governance',audience:'admin'};
    en.tours.first_run=en.tours.first_run.concat(['gov']);
  });
  assert.equal((await page.evaluate(()=>window.SynthPulseHelp.stepsFor('first_run'))).includes('gov'),false);
  assert.deepEqual(await page.evaluate(()=>window.SynthPulseHelp.stepsFor('org_admin')),[]);
  await context.close();
});

test('the rail is used on desktop and the menu or sidebar on a phone',async browser=>{
  const desk=await open(browser,{width:1280});
  await desk.page.evaluate(()=>window.SynthPulseHelp.startTour('first_run'));
  await waitStep(desk.page,'Step 1 of 6');
  for(let i=2;i<=4;i++){await desk.page.keyboard.press('ArrowRight');await waitStep(desk.page,`Step ${i} of 6`);}
  let state=await waitStep(desk.page,'Step 4 of 6');
  assert.equal(state.lit,'workspaces');assert.equal(state.litIn,'rail');
  await desk.context.close();
  const phone=await open(browser,{width:390,height:844});
  await phone.page.evaluate(()=>window.SynthPulseHelp.startTour('first_run'));
  await waitStep(phone.page,'Step 1 of 6');
  for(let i=2;i<=4;i++){await phone.page.keyboard.press('ArrowRight');await waitStep(phone.page,`Step ${i} of 6`);}
  state=await waitStep(phone.page,'Step 4 of 6');
  assert.equal(state.lit,'menu-button');
  await phone.page.keyboard.press('Escape');
  await noTour(phone.page);
  // With the mobile menu open, the sidebar button itself is lit.
  await phone.page.evaluate(()=>document.querySelector('.sidebar').classList.add('mobile-open'));
  await phone.page.evaluate(()=>window.SynthPulseHelp.startTour('first_run'));
  await waitStep(phone.page,'Step 1 of 6');
  for(let i=2;i<=4;i++){await phone.page.keyboard.press('ArrowRight');await waitStep(phone.page,`Step ${i} of 6`);}
  state=await waitStep(phone.page,'Step 4 of 6');
  assert.equal(state.lit,'workspaces');assert.equal(state.litIn,'sidebar');
  assert.equal(await phone.page.evaluate(()=>document.documentElement.scrollWidth<=390),true);
  await phone.context.close();
});

test('the admin tour has no steps while its pages do not exist, also on a phone',async browser=>{
  for(const width of [1280,390]){
    const {page,context}=await open(browser,{width,me:{email:'org@example.test',permissions:[],delegated_scope:'org'}});
    assert.deepEqual(await page.evaluate(()=>window.SynthPulseHelp.stepsFor('org_admin')),[]);
    assert.equal(await page.evaluate(()=>window.SynthPulseHelp.startTour('org_admin')),false);
    // Once the organisation page is in the menu, its step appears (on a phone
    // through the menu button while the menu is closed).
    await page.evaluate(()=>document.querySelectorAll('.rail, .sidebar-nav').forEach(nav=>{
      const b=document.createElement('button');b.className='nav-tab';b.dataset.panel='organization';b.textContent='Organisation';nav.appendChild(b);
    }));
    assert.deepEqual(await page.evaluate(()=>window.SynthPulseHelp.stepsFor('org_admin')),['organization']);
    await context.close();
  }
});

test('a tour switches to its page first',async browser=>{
  const {page,context}=await open(browser);
  await page.evaluate(()=>switchPanel('tasks'));
  await page.evaluate(()=>window.SynthPulseHelp.startTour('first_run'));
  const state=await waitStep(page,'Step 1 of 6');
  assert.equal(state.lit,'chat-composer');
  assert.deepEqual(await page.evaluate(()=>window.panelSwitches),['tasks','chat']);
  await context.close();
});

test('Explain this page walks the visible sections and opens from the title bar',async browser=>{
  const {page,context,events}=await open(browser);
  await page.evaluate(()=>switchPanel('tasks'));
  await page.locator('#btnPageHelp').click();
  let state=await waitStep(page,'Step 1 of 3');
  assert.equal(state.title,'Scheduled tasks');
  assert.equal(state.lit,'help-button');
  await page.keyboard.press('ArrowRight');
  state=await waitStep(page,'Step 2 of 3');
  assert.equal(state.lit,'tasks-new');
  // The notifications section is dynamic: it is skipped while its form is closed.
  await page.keyboard.press('ArrowRight');
  state=await waitStep(page,'Step 3 of 3');
  assert.equal(state.lit,'tasks-list');
  assert.equal(await page.locator('.sp-help-support').count(),0);
  await page.getByRole('button',{name:'Done'}).click();
  await noTour(page);
  assert.equal(await page.evaluate(()=>document.activeElement.id),'btnPageHelp');
  // Explaining never marks a tour as seen and never shows the tour toast.
  assert.deepEqual(await page.evaluate(()=>window.toasts),[]);
  assert.equal(await page.evaluate(()=>window.SynthPulseHelp.hasSeen('first_run')),false);
  await page.waitForTimeout(100);
  assert.deepEqual(events,[{event:'explain_clicked',page:'tasks'}]);
  await context.close();
});

test('the popover is the fallback without Guida or without a visible target',async browser=>{
  const bare=await open(browser,{guida:false});
  await bare.page.locator('#btnPageHelp').click();
  const pop=bare.page.locator('.sp-help-popover');
  await pop.waitFor();
  assert.equal(await pop.getAttribute('role'),'dialog');
  assert.equal(await bare.page.locator('.sp-help-popover-title').innerText(),'Chats');
  assert.match(await pop.innerText(),/About this page/);
  assert.match(await pop.innerText(),/Start a new chat/);
  assert.equal(await bare.page.evaluate(()=>document.getElementById('btnPageHelp').getAttribute('aria-expanded')),'true');
  // Related pages open their own explanation.
  await bare.page.getByRole('button',{name:'Group chats'}).click();
  await bare.page.waitForFunction(()=>document.querySelector('.sp-help-popover-title')?.textContent==='Group chats');
  await bare.page.keyboard.press('Escape');
  assert.equal(await bare.page.locator('.sp-help-popover').count(),0);
  assert.equal(await bare.page.evaluate(()=>document.activeElement.id),'btnPageHelp');
  // A tour without Guida lists its steps.
  await bare.page.evaluate(()=>window.SynthPulseHelp.startTour('first_run'));
  await bare.page.locator('.sp-help-popover ol li').first().waitFor();
  assert.equal(await bare.page.locator('.sp-help-popover ol li').count(),6);
  await bare.page.locator('#outside').click();
  assert.equal(await bare.page.locator('.sp-help-popover').count(),0);
  await bare.context.close();

  const {page,context}=await open(browser);
  // The bot builder page has text only, so Explain uses the popover.
  await page.evaluate(()=>window.SynthPulseHelp.explainPage('bot_builder'));
  await page.locator('.sp-help-popover').waitFor();
  assert.equal(await page.locator('.sp-help-popover-title').innerText(),'Guided bot builder');
  assert.equal(await page.locator('.sp-help-popover-section').count(),4);
  assert.match(await page.locator('.sp-help-popover').innerText(),/proactive work/);
  assert.equal(await page.locator('.guida-overlay').count(),0);
  await context.close();
});

test('Still stuck appears only when support can open a ticket',async browser=>{
  const {page,context}=await open(browser,{guida:false,preScript:`window.tickets=[];window.SynthPulseSupport={openTicket(o){window.tickets.push(o);}};`});
  await page.locator('#btnPageHelp').click();
  await page.getByRole('button',{name:'Still stuck? Ask support'}).click();
  assert.equal(await page.locator('.sp-help-popover').count(),0);
  assert.deepEqual(await page.evaluate(()=>window.tickets),[{page:'chat',title:'Chats',source:'help'}]);
  await context.close();
});

test('content is escaped before it reaches Guida or the popover',async browser=>{
  for(const guida of [true,false]){
    const {page,context}=await open(browser,{guida});
    await page.evaluate(()=>{
      const chat=window.SynthPulseHelpContent.locales.en.pages.chat;
      chat.title='<img src=x onerror="window.pwned=1">Chats';
      chat.sections[0].body='<b>bold</b> & more';
    });
    await page.evaluate(()=>window.SynthPulseHelp.explainPage('chat'));
    const selector=guida?'.guida-tooltip.guida-visible h3':'.sp-help-popover-title';
    await page.waitForSelector(selector);
    assert.equal(await page.locator(selector).innerText(),'<img src=x onerror="window.pwned=1">Chats');
    assert.equal(await page.evaluate(()=>document.querySelectorAll('.guida-tooltip img,.sp-help-popover img,.guida-tooltip b,.sp-help-popover b').length),0);
    assert.equal(await page.evaluate(()=>window.pwned),undefined);
    await context.close();
  }
});

test("What's new shows once per version, never on a first visit",async browser=>{
  const key='synthpulse-help:'+MEMBER+':whats_new:v1';
  const first=await open(browser,{version:'v0.53.0'});
  assert.equal(await first.page.evaluate(()=>window.SynthPulseHelp.showWhatsNew()),false);
  assert.equal(await first.page.evaluate(k=>localStorage.getItem(k),key),'0.53.0');
  await first.context.close();
  const upgraded=await open(browser,{version:'exp-v0.53.0-12-gabc',storage:{[key]:'0.52.158'}});
  assert.equal(await upgraded.page.evaluate(()=>window.SynthPulseHelp.showWhatsNew()),true);
  const card=upgraded.page.locator('#spHelpCard[data-kind="whats_new"]');
  await card.waitFor();
  assert.match(await card.innerText(),/What's new/);
  assert.match(await card.innerText(),/Help on every page/);
  assert.equal(await card.getAttribute('role'),'region');
  await upgraded.page.getByRole('button',{name:'Got it'}).click();
  assert.equal(await upgraded.page.locator('#spHelpCard').count(),0);
  assert.equal(await upgraded.page.evaluate(()=>window.SynthPulseHelp.showWhatsNew()),false);
  // The link from the monthly report shows it again on purpose.
  assert.equal(await upgraded.page.evaluate(()=>window.SynthPulseHelp.showWhatsNew({force:true})),true);
  await upgraded.context.close();
  // No card for a version that has no entry, and none for a downgrade.
  const none=await open(browser,{version:'v0.52.160',storage:{[key]:'0.52.158'}});
  assert.equal(await none.page.evaluate(()=>window.SynthPulseHelp.showWhatsNew()),false);
  await none.context.close();
  // After boot, the card takes the place of the tour offer.
  const boot=await open(browser,{version:'v0.53.1',storage:{[key]:'0.52.0'}});
  await boot.page.evaluate(()=>window.dispatchEvent(new Event('synpulse:boot-ready')));
  await boot.page.waitForSelector('#spHelpCard[data-kind="whats_new"]');
  await boot.context.close();
});

test('Dutch help for a browser that prefers Dutch, English when English was chosen',async browser=>{
  const nl=await open(browser,{guida:false,locale:'nl-NL'});
  await nl.page.evaluate(()=>window.SynthPulseHelp.explainPage('tasks'));
  await nl.page.locator('.sp-help-popover').waitFor();
  assert.equal(await nl.page.locator('.sp-help-popover-title').innerText(),'Geplande taken');
  await nl.context.close();
  const chosen=await open(browser,{guida:false,locale:'nl-NL',storage:{'hermes-lang':'en'}});
  await chosen.page.evaluate(()=>window.SynthPulseHelp.explainPage('tasks'));
  await chosen.page.locator('.sp-help-popover').waitFor();
  assert.equal(await chosen.page.locator('.sp-help-popover-title').innerText(),'Scheduled tasks');
  await chosen.context.close();
});

test('blocked storage never breaks a tour',async browser=>{
  const {page,context,errors}=await open(browser,{preScript:`Storage.prototype.setItem=function(){throw new Error('blocked');};Storage.prototype.getItem=function(){throw new Error('blocked');};`});
  await page.evaluate(()=>window.SynthPulseHelp.startTour('first_run'));
  await waitStep(page,'Step 1 of 6');
  await page.keyboard.press('Escape');
  await noTour(page);
  assert.equal(await page.evaluate(()=>window.SynthPulseHelp.hasSeen('first_run')),false);
  assert.deepEqual(errors,[]);
  await context.close();
});

test('the settings cards start the tour and explain the page left for Settings',async browser=>{
  const {page,context}=await open(browser,{guida:false,preScript:''});
  await page.evaluate(()=>{
    const pane=document.createElement('div');
    pane.innerHTML='<button type="button" id="helpCardStartTour" data-help-action="tour" data-help-tour="first_run">Getting started</button>'
      +'<button type="button" id="helpCardStartOrgTour" data-help-action="tour" data-help-tour="org_admin" hidden>Admins</button>'
      +'<button type="button" id="helpCardExplain" data-help-action="explain">Explain this page</button>';
    document.getElementById('panelSettings').appendChild(pane);
  });
  await page.evaluate(()=>switchPanel('tasks'));
  // Leaving Tasks for Settings through the nav records Tasks.
  await page.evaluate(()=>{document.querySelector('.rail [data-panel="settings"]').addEventListener('click',()=>switchPanel('settings'));});
  await page.locator('.rail [data-panel="settings"]').click();
  await page.locator('#helpCardExplain').click();
  await page.locator('.sp-help-popover').waitFor();
  assert.equal(await page.locator('.sp-help-popover-title').innerText(),'Scheduled tasks');
  await page.keyboard.press('Escape');
  // Explaining took the person to Tasks; back in Settings, start the tour.
  assert.equal(await page.evaluate(()=>_currentPanel),'tasks');
  await page.evaluate(()=>switchPanel('settings'));
  await page.locator('#helpCardStartTour').click();
  await page.locator('.sp-help-popover ol').waitFor();
  assert.equal(await page.evaluate(()=>_currentPanel),'chat');
  assert.equal(await page.locator('#helpCardStartOrgTour').isHidden(),true);
  await context.close();
});

(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||undefined});
  let failed=0;
  try{
    for(const {name,fn} of tests){
      try{await fn(browser);console.log('ok   '+name);}
      catch(err){failed++;console.log('FAIL '+name+'\n'+(err&&err.stack||err));}
    }
  }finally{await browser.close();}
  console.log(`${tests.length-failed} passed, ${failed} failed`);
  process.exit(failed?1:0);
})();
