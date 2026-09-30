const fs=require('node:fs'),assert=require('node:assert/strict'),{chromium}=require('playwright');
const panels=fs.readFileSync(process.env.BOT_SCOPE_PANELS || 'static/panels.js','utf8');
const sessions=fs.readFileSync('static/sessions.js','utf8');
const switchCode=panels.slice(panels.indexOf('async function switchToProfile(name) {'),panels.indexOf('function openProfileCreate(){'));
// The next top-level function bounds the actual project/source partitioner.
const partStart=sessions.indexOf('function _partitionSidebarSessionRows(');
const partEnd=sessions.indexOf('\nfunction ',partStart+10);
(async()=>{const browser=await chromium.launch({headless:true});try{
 for(const width of [1360,390]){
  const page=await browser.newPage({viewport:{width,height:844}});
  await page.setContent('<main style="max-width:800px;margin:auto;padding:16px"><h1>Chats</h1><div id="composerWrap"><textarea id="msg"></textarea></div><div id="sessionList"></div></main>');
  await page.addStyleTag({path:'static/style.css'});await page.addStyleTag({path:'static/chat-bots.css'});
  await page.evaluate(()=>{
   window.$=id=>document.getElementById(id);window.t=k=>k;window.botAvatarHtml=()=>'';window.botDisplayName=p=>p.name;
   window.__GOV_ME__={email:'tester@example.test'};window.S={activeProfile:'writer',activeProfileIsDefault:false,_bootReady:true,session:null,messages:[]};
   window._showAllProfiles=true;window._profileSwitchGeneration=0;window._profileSwitchOpeningExistingSession=false;
   window._activeProject='team';window.NO_PROJECT_FILTER='__none__';window._showArchived=false;window._sessionSourceFilter='webui';window._archivedCliCount=0;window._archivedWebuiCount=0;
   window._allProjects=[{project_id:'team',collaboration:true,bot_participants:['writer','reviewer']}];
   window.rows=[{session_id:'a',title:'Writer · Project A',profile:'writer',project_id:'team',message_count:2},{session_id:'b',title:'Reviewer · Project A',profile:'reviewer',project_id:'team',message_count:2},{session_id:'c',title:'Reviewer · Project B',profile:'reviewer',project_id:'other',message_count:2}];
   window._sidebarRowHasVisibleMessages=()=>true;window._isCliSession=()=>false;
   window._setShowAllProfiles=value=>{window._showAllProfiles=value};window._setActiveProjectFilter=value=>{window._activeProject=value};
   window._profileMatchesActiveProfile=(a,b)=>(a||'default')===b;
   window.errors=[];window.showToast=value=>errors.push(value);
   window._resetWorkspaceListState=window._clearPersistedModelState=window.syncTopbar=window._refreshProfileSwitchBackground=()=>{};
   window._profileSwitchPanelLoad=async()=>{};
   window.api=async(url,opts)=>{
    if(url.includes('/api/profiles'))return {profiles:[{name:'writer'},{name:'reviewer'}]};
    if(url.includes('/api/people'))return {people:[]};
    if(url==='/api/profile/switch'){if(window.failSwitch)throw Error('Offline');return {active:JSON.parse(opts.body).name};}
    throw Error(url);
   };
   window.renderSessionList=async()=>{
    const scoped=rows.filter(row=>_showAllProfiles||row.profile===S.activeProfile);
    const filtered=_partitionSidebarSessionRows(scoped,null).sessionsRaw;
    window.visible=filtered.map(row=>row.session_id);
    $('sessionList').innerHTML=filtered.map(row=>'<p>'+row.title+'</p>').join('');
   };
  });
  await page.addScriptTag({content:sessions.slice(partStart,partEnd)});
  await page.addScriptTag({content:switchCode});await page.addScriptTag({path:'static/chat-bots.js'});
  await page.evaluate(()=>{refreshChatBots();return renderSessionList()});
  await page.locator('[data-bot="reviewer"]').waitFor();
  if(process.env.BOT_SCOPE_EVIDENCE)await page.screenshot({path:`${process.env.BOT_SCOPE_EVIDENCE}/before-${width}.png`});
  await page.locator('[data-bot="reviewer"]').click();
  await page.waitForFunction(()=>S.activeProfile==='reviewer');
  assert.deepEqual(await page.evaluate(()=>visible),['b']);
  assert.equal(await page.evaluate(()=>_showAllProfiles),false);
  assert.equal(await page.evaluate(()=>_activeProject),'team');
  // Selecting the already active bot also exits the aggregate view.
  await page.evaluate(()=>{_showAllProfiles=true;return renderSessionList()});
  await page.locator('[data-bot="reviewer"]').click();
  assert.deepEqual(await page.evaluate(()=>visible),['b']);
  // A failed switch must leave the current filter intact.
  await page.evaluate(()=>{window.failSwitch=true});
  await page.locator('[data-bot="writer"]').click();
  assert.deepEqual(await page.evaluate(()=>visible),['b']);
  await page.evaluate(()=>{window.failSwitch=false;_allProjects=[{project_id:'team',profile:'reviewer'}]});
  await page.locator('[data-bot="writer"]').click();
  assert.equal(await page.evaluate(()=>_activeProject),null);
  assert.deepEqual(await page.evaluate(()=>visible),['a']);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  if(process.env.BOT_SCOPE_EVIDENCE)await page.screenshot({path:`${process.env.BOT_SCOPE_EVIDENCE}/after-${width}.png`});
  await page.close();console.log(`Bot and project scope passed at ${width}px`);
 }
}finally{await browser.close()}})().catch(error=>{console.error(error);process.exitCode=1});
