// Bot page: the Responsibilities card (read for everyone, add, edit and remove
// for an editor, saved under the bot revision) and, on My approvals, the
// "Waiting for you" section.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('fs'),assert=require('node:assert/strict');
const panels=fs.readFileSync('static/panels.js','utf8');
const slice=(from,to)=>{const a=panels.indexOf(from),b=panels.indexOf(to,a);assert(a>=0&&b>a,from);return panels.slice(a,b);};
// Module state as globals so the page can seed and read it between evaluations.
const duties=slice('// Responsibilities card (ui_meta.hermes-bots.responsibilities)','async function uploadBotAvatar(input){').replace(/^(let|const) /gm,'var ');
async function page(browser,width){
  const p=await browser.newPage({viewport:{width,height:900}});
  await p.route('**/*',r=>r.fulfill({contentType:'text/html',body:'<html></html>'}));await p.goto('http://ui.test/');
  const html=fs.readFileSync('static/index.html','utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<link\b[^>]*>/gi,'');
  await p.setContent(html);await p.addStyleTag({path:'static/style.css'});
  await p.evaluate(()=>{
   window.$=id=>document.getElementById(id);
   window.esc=s=>String(s).replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
   window.t=k=>k;window.showToast=m=>{window.lastToast=m;};
   window._botKind=p=>(p&&p.bot_kind)==='person'?'person':'bot';
   window._profileDropdownClearStoredCache=()=>{};window.loadProfilesPanel=async()=>{window.reloaded=(window.reloaded||0)+1;};
   window.calls=[];window.failNext=false;
   window.api=async(url,opts)=>{const body=opts&&opts.body?JSON.parse(opts.body):null;calls.push([url,body]);if(window.failNext){window.failNext=false;throw new Error('Bot changed elsewhere. Reload before saving.');}return {ok:true};};
  });
  return p;
}
async function mountDuties(p,code,profile){
  await p.evaluate(([code,profile])=>{
   (0,eval)(code);
   document.getElementById('mainProfiles').style.display='flex';
   const body=document.getElementById('profileDetailBody');body.style.display='';
   body.innerHTML='<div class="main-view-content bot-detail-content">'+_botDutiesCardHtml(profile)+'</div>';
   window._currentProfileDetail=profile;
   _botDuties=((profile.bot||{}).responsibilities||[]).map(d=>({...d}));_botDutyEditing=-1;_paintBotDuties();
  },[code,profile]);
}
const waiting=slice('// "Wacht op jou" on My approvals','window.loadWaitingForYou=loadWaitingForYou;').replace(/^(let|const) /gm,'var ');
const DUTY={title:'Inbox triage',objective:'Sort new mail',trigger:'bij nieuwe mail',autonomy:'report_only',reporting:'digest in de botchat'};
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||undefined});
 try{for(const width of [1280,390]){
  const p=await page(browser,width);
  // Read-only viewer: the list, no buttons; a person's profile has no card.
  await mountDuties(p,duties,{name:'cfo',bot_revision:4,bot_editable:false,bot:{responsibilities:[DUTY]}});
  assert.equal(await p.locator('.bot-duty').count(),1);
  assert.equal(await p.textContent('.bot-duty-title'),'Inbox triage');
  assert.deepEqual(await p.$$eval('.bot-duty-chip',n=>n.map(x=>x.textContent)),['bot_duty_trigger: bij nieuwe mail','bot_duty_autonomy_report_only','bot_duty_reports: digest in de botchat']);
  assert.equal(await p.locator('#botDutiesCard button').count(),0);
  assert.equal(await p.evaluate(()=>_botDutiesCardHtml({name:'odis',bot_kind:'person',bot:{}})),'');
  // Editor: add a row, saved with the revision and only the list.
  await mountDuties(p,duties,{name:'cfo',bot_revision:4,bot_editable:true,bot:{responsibilities:[DUTY]}});
  await p.click('#botDutyAdd');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'botDutyTitle');
  await p.click('#botDutyForm .primary');
  assert.equal(await p.evaluate(()=>lastToast),'bot_duty_title_required');
  assert.equal(await p.evaluate(()=>calls.length),0);
  await p.fill('#botDutyTitle','  Weekly   report ');await p.fill('#botDutyTrigger','vrijdag 16:00');
  await p.selectOption('#botDutyAutonomy','auto');
  await p.click('#botDutyForm .primary');
  let call=await p.evaluate(()=>calls.at(-1));
  assert.equal(call[0],'/api/profile/appearance');
  assert.deepEqual(call[1],{name:'cfo',revision:4,bot:{responsibilities:[DUTY,{title:'Weekly report',objective:'',trigger:'vrijdag 16:00',autonomy:'auto',reporting:''}]}});
  assert.equal(await p.locator('.bot-duty').count(),2);
  assert.equal(await p.evaluate(()=>lastToast),'bot_duties_saved');
  // Edit the first row in place.
  await p.click('.bot-duty[data-index="0"] button:first-child');
  assert.equal(await p.inputValue('#botDutyTitle'),'Inbox triage');
  assert.equal(await p.inputValue('#botDutyAutonomy'),'report_only');
  await p.fill('#botDutyTitle','Inbox');await p.click('#botDutyForm .primary');
  call=await p.evaluate(()=>calls.at(-1));
  assert.deepEqual(call[1].bot.responsibilities.map(d=>d.title),['Inbox','Weekly report']);
  // A failed save keeps the list and the form as they were.
  await p.evaluate(()=>{failNext=true;});
  await p.click('.bot-duty[data-index="1"] button:last-child');
  assert.equal(await p.locator('.bot-duty').count(),2);
  assert.match(await p.evaluate(()=>lastToast),/changed elsewhere/);
  // Remove.
  await p.click('.bot-duty[data-index="1"] button:last-child');
  call=await p.evaluate(()=>calls.at(-1));
  assert.deepEqual(call[1].bot.responsibilities.map(d=>d.title),['Inbox']);
  // Cancel leaves everything untouched.
  await p.click('#botDutyAdd');await p.click('#botDutyForm .sm-btn:not(.primary)');
  assert.equal(await p.locator('#botDutyForm').count(),0);
  // Twelve is the limit: the add button is disabled.
  await mountDuties(p,duties,{name:'cfo',bot_revision:1,bot_editable:true,bot:{responsibilities:Array.from({length:12},(_,i)=>({title:'D'+i,autonomy:'ask'}))}});
  assert.equal(await p.locator('#botDutyAdd').isDisabled(),true);
  // Work of this bot: open tasks by status, what needs a person on top and
  // highlighted, the made files as downloads, a task opens on the board.
  await p.evaluate(()=>{
   window._canUseFeature=()=>true;window.opened=[];
   window.switchPanel=async name=>opened.push('panel:'+name);window.loadKanbanTask=async id=>opened.push('task:'+id);
   window.screenRow={bot:'cfo',state:'waiting',reason:'please log in to Exact',rights:{view:true,control:true}};
   window.api=async url=>{calls.push([url,null]);
    if(url.startsWith('/api/bot-screen/status')){if(!screenRow)throw new Error('screen_forbidden');return {screens:[screenRow]};}
    if(window.noBoard)throw new Error('403');
    return {tasks:[
     {id:'t1',title:'Draft',status:'todo'},{id:'t2',title:'Login needed',status:'blocked',block_kind:'needs_input'},
     {id:'t3',title:'Check me',status:'review'},{id:'t4',title:'Waiting on parent',status:'blocked',block_kind:'dependency'}],
    attachments:[{id:7,task_id:'t9',filename:'report <1>.md',size:2048,created_at:1760000000,task_title:'Weekly'}]};};
   const body=document.querySelector('.bot-detail-content');body.insertAdjacentHTML('beforeend',_botWorkSectionHtml(_currentProfileDetail));
  });
  await p.evaluate(()=>_loadBotWork(_currentProfileDetail));
  assert.deepEqual(await p.evaluate(()=>calls.slice(-2).map(c=>c[0])),['/api/kanban/bot-work?profile=cfo','/api/bot-screen/status?bot=cfo']);
  assert.equal(await p.textContent('.bot-screen-text'),'bot_screen: bot_screen_waiting');
  assert.equal(await p.getAttribute('.bot-screen-line','data-state'),'waiting');
  assert.equal(await p.getAttribute('.bot-screen-open','href'),'/static/bot-screens.html?bot=cfo');
  // Human in control by a named person; no desktop has no link.
  await p.evaluate(()=>{window.t=k=>({bot_screen_human:'{who} since {since}',bot_screen_waiting:'waiting: {reason}'}[k]||k);});
  assert.equal(await p.evaluate(()=>_botScreenStatusText({state:'waiting',reason:'log in'})),'waiting: log in');
  assert.match(await p.evaluate(()=>_botScreenStatusText({state:'human',by:'ada@example.test',since:1760000000})),/^ada@example\.test since \S/);
  assert.equal(await p.evaluate(()=>_botScreenLineHtml({bot:'cfo',state:'none'}).includes('bot-screen-open')),false);
  await p.evaluate(()=>{window.t=k=>k;});
  assert.deepEqual(await p.$$eval('.bot-work-group',n=>n.map(g=>g.dataset.status)),['blocked','review','todo']);
  assert.deepEqual(await p.$$eval('.bot-work-task.is-attention',n=>n.map(b=>b.dataset.taskId)),['t2','t3']);
  assert.deepEqual(await p.$$eval('.bot-work-flag',n=>n.map(b=>b.textContent)),['bot_work_flag_needs_input','bot_work_flag_review']);
  assert.deepEqual(await p.$eval('.bot-work-file a',a=>[a.getAttribute('href'),a.textContent,a.getAttribute('download')]),['/api/kanban/attachment?id=7','report <1>.md','report <1>.md']);
  await p.click('.bot-work-task[data-task-id="t3"]');
  assert.deepEqual(await p.evaluate(()=>opened),['panel:kanban','task:t3']);
  // Without board rights only the screen line shows; without screen rights
  // too the section stays hidden.
  const remount=()=>p.evaluate(()=>{document.getElementById('botWork').remove();document.querySelector('.bot-detail-content').insertAdjacentHTML('beforeend',_botWorkSectionHtml(_currentProfileDetail));calls.length=0;});
  await p.evaluate(()=>{window._canUseFeature=()=>false;});await remount();
  await p.evaluate(()=>_loadBotWork(_currentProfileDetail));
  assert.deepEqual(await p.evaluate(()=>calls.map(c=>c[0])),['/api/bot-screen/status?bot=cfo']);
  assert.equal(await p.locator('#botWork .bot-screen-line').isVisible(),true);
  assert.equal(await p.locator('#botWork .bot-work-group').count(),0);
  await p.evaluate(()=>{window.screenRow=null;});await remount();
  await p.evaluate(()=>_loadBotWork(_currentProfileDetail));
  assert.equal(await p.locator('#botWork').isVisible(),false);
  const overflow=await p.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  assert.ok(overflow<=0,'no sideways scroll at '+width);
  // My approvals, Waiting for you: chats with a pending approval first, then
  // tasks; reply, unblock and open use the existing routes.
  await p.evaluate(code=>{
   (0,eval)(code);
   document.getElementById('mainApprovals').style.display='flex';
   window.opened=[];window.calls=[];window.deny=new Set();
   window.openCronJobChat=(sid,profile)=>opened.push('chat:'+sid+':'+profile);
   window.openKanbanTaskFromBot=id=>opened.push('task:'+id);
   window.api=async(url,opts)=>{calls.push([url,opts&&opts.body?JSON.parse(opts.body):null]);
    if(deny.has(url))throw new Error('403');
    if(url==='/api/kanban/waiting')return {tasks:[{id:'t2',title:'Login needed',status:'blocked',block_kind:'needs_input',assignee:'cfo'},{id:'t3',title:'Check me',status:'review',assignee:'coo'}]};
    if(url==='/api/approval/waiting')return {approvals:[{session_id:'s1',title:'Deploy chat',profile:'cfo',description:'rm -rf build',count:2}]};
    if(url==='/api/bot-screen/status')return {screens:[{bot:'cfo',state:'waiting',reason:'please log in to Exact',rights:{view:true,control:true}},
      {bot:'coo',state:'waiting',reason:'watch only',rights:{view:true,control:false}},{bot:'ceo',state:'agent',rights:{view:true,control:true}}]};
    return {ok:true};};
  },waiting);
  await p.evaluate(()=>loadWaitingForYou());
  assert.equal(await p.locator('#myWaitingSection').isVisible(),true);
  assert.deepEqual(await p.$$eval('.waiting-item',n=>n.map(x=>x.dataset.kind+':'+(x.dataset.taskId||x.dataset.sessionId||x.dataset.bot))),['screen:cfo','approval:s1','task:t2','task:t3']);
  assert.deepEqual(await p.$eval('.waiting-item[data-kind="screen"]',li=>[li.querySelector('.waiting-item-detail').textContent,li.querySelector('a').getAttribute('href'),li.querySelector('a').target]),['please log in to Exact','/static/bot-screens.html?bot=cfo','_blank']);
  assert.equal(await p.locator('.waiting-item[data-task-id="t3"] button',{hasText:'kanban_unblock'}).count(),0);
  // The blocked task of cfo (screen waiting, may control) carries the takeover link; the review task does not.
  assert.equal(await p.getAttribute('.waiting-item[data-task-id="t2"] .waiting-screen-link','href'),'/static/bot-screens.html?bot=cfo');
  assert.equal(await p.locator('.waiting-item[data-task-id="t3"] .waiting-screen-link').count(),0);
  await p.click('.waiting-item[data-session-id="s1"] button');
  await p.click('.waiting-item[data-task-id="t3"] button:first-child');
  assert.deepEqual(await p.evaluate(()=>opened),['chat:s1:cfo','task:t3']);
  await p.click('.waiting-item[data-task-id="t2"] button:nth-child(2)');
  assert.equal(await p.evaluate(()=>document.activeElement.id),'waitingComment');
  await p.fill('#waitingComment','Logged in, go ahead');
  await p.click('.waiting-comment .primary');
  assert.deepEqual(await p.evaluate(()=>calls.find(c=>c[0].endsWith('/comments'))),['/api/kanban/tasks/t2/comments',{body:'Logged in, go ahead'}]);
  await p.click('.waiting-item[data-task-id="t2"] button:nth-child(3)');
  assert.ok(await p.evaluate(()=>calls.some(c=>c[0]==='/api/kanban/tasks/t2/unblock')));
  // No rights on either source: the section stays hidden; one source still shows.
  await p.evaluate(()=>{deny.add('/api/kanban/waiting');deny.add('/api/approval/waiting');deny.add('/api/bot-screen/status');});
  await p.evaluate(()=>loadWaitingForYou());
  assert.equal(await p.locator('#myWaitingSection').isVisible(),false);
  await p.evaluate(()=>{deny.delete('/api/approval/waiting');});
  await p.evaluate(()=>loadWaitingForYou());
  assert.deepEqual(await p.$$eval('.waiting-item',n=>n.map(x=>x.dataset.kind)),['approval']);
  const overflow2=await p.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  assert.ok(overflow2<=0,'no sideways scroll on approvals at '+width);
  await p.close();
 }}finally{await browser.close();}
 console.log('bot responsibilities, work and waiting browser checks passed');
})().catch(e=>{console.error(e);process.exit(1);});
