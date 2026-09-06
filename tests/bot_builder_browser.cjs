const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH || undefined}),p=await b.newPage({viewport:{width:390,height:844}});
await p.setContent('<div id="profileDetailTitle"></div><div id="profileDetailEmpty"></div><div id="profileDetailBody"></div><button id="btnSaveProfileDetail"></button>');
await p.evaluate(()=>{window.esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');window._profileMode='';window._setProfileHeaderButtons=()=>{};window.switchPanel=()=>{};window._profileDropdownClearStoredCache=()=>{};window.loadProfilesPanel=async()=>{};window.openProfileDetail=()=>{};window.showToast=()=>{};window.sent=[];window.api=async(url,opt)=>{if(opt?.method==='POST'){sent.push(JSON.parse(opt.body));return {ok:true}}return {can_edit:true,catalog:{skills:[{name:'review',description:'Review evidence'}],mcp_servers:[{name:'drive'}],cli_tools:[{name:'terminal'}],users:[{email:'colleague@example.test'}],groups:[{name:'finance'}]},config:{default_model:'codex/gpt-6-astra',model_provider:'custom:omniroute'}}};});
await p.addStyleTag({path:'static/bot-builder.css'});await p.addScriptTag({path:'static/bot-builder.js'});await p.evaluate(()=>BotBuilder.open());
await p.locator('#builderName').fill('review-bot');await p.locator('#builderTitle').fill('Reviewer');
const data=await p.evaluate(()=>{const c=document.createElement('canvas');c.width=1024;c.height=1024;c.getContext('2d').fillRect(0,0,1024,1024);return c.toDataURL('image/png').split(',')[1]});
await p.locator('#builderPhoto').setInputFiles({name:'photo.png',mimeType:'image/png',buffer:Buffer.from(data,'base64')});
await p.locator('.bot-builder-photo').waitFor();
assert.equal(await p.evaluate(()=>sent.length),0);
await p.locator('#builderNext').click();await p.locator('#builderPrompt').fill('Review supplied evidence. Never invent payments.');await p.locator('[data-selection="skills"]').check();
await p.locator('#builderNext').click();await p.locator('[data-selection="mcp_servers"]').check();await p.locator('[data-selection="cli_tools"]').check();
await p.locator('#builderNext').click();await p.locator('[data-selection="allowed_users"]').check();await p.locator('[data-selection="allowed_groups"]').check();
assert.equal(await p.evaluate(()=>sent.length),0);
assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth),390);
if(process.env.BOT_BUILDER_SCREENSHOT) await p.screenshot({path:process.env.BOT_BUILDER_SCREENSHOT,fullPage:true});
await p.locator('#builderNext').click();const sent=await p.evaluate(()=>sent);
assert.equal(sent.length,1);assert.equal(sent[0].system_prompt,'Review supplied evidence. Never invent payments.');assert.deepEqual(sent[0].skills,['review']);assert.deepEqual(sent[0].mcp_servers,['drive']);assert.deepEqual(sent[0].cli_tools,['terminal']);assert.deepEqual(sent[0].allowed_users,['colleague@example.test']);assert.deepEqual(sent[0].allowed_groups,['finance']);assert.ok(sent[0].avatar.startsWith('data:image/png;base64,'));assert.equal('revision' in sent[0],false);
// Reopen the saved bot using the server revision and verify an edit roundtrip.
await p.evaluate(saved=>{
  window.api=async(url,opt)=>{
    if(opt?.method==='POST'){sent.push(JSON.parse(opt.body));return {ok:true};}
    return {can_edit:true,catalog:{skills:[{name:'review'}],mcp_servers:[{name:'drive'}],cli_tools:[{name:'terminal'}],users:[{email:'colleague@example.test'}],groups:[{name:'finance'}]},config:{...saved,revision:7,avatar_url:saved.avatar}};
  };
},sent[0]);
await p.evaluate(()=>BotBuilder.open('review-bot'));
assert.equal(await p.locator('#builderName').getAttribute('readonly'),'');
assert.equal(await p.locator('.bot-builder-photo').count(),1);
await p.locator('[data-builder-tab="1"]').click();
assert.equal(await p.locator('#builderPrompt').inputValue(),'Review supplied evidence. Never invent payments.');
await p.locator('#builderPrompt').fill('Updated bot instructions.');
await p.locator('[data-builder-tab="5"]').click();
await p.locator('[data-builder-tab="2"]').click();
await p.locator('[data-builder-tab="1"]').click();
assert.equal(await p.locator('#builderPrompt').inputValue(),'Updated bot instructions.');
await p.locator('#builderNext').click();
const edited=await p.evaluate(()=>sent.at(-1));
assert.equal(edited.revision,7);assert.equal(edited.system_prompt,'Updated bot instructions.');
assert.equal('avatar_url' in edited,false);

// A slow catalog response cannot reclaim the view after accepted navigation.
await p.evaluate(()=>{
 window.previousApi=api;
 window.api=()=>new Promise(resolve=>window.resolveCatalog=resolve);
 BotBuilder.open();
});
await p.waitForFunction(()=>typeof resolveCatalog==='function');
await p.evaluate(()=>{BotBuilder.invalidate();document.getElementById('profileDetailBody').textContent='Other view';resolveCatalog({can_edit:true,catalog:{},config:{}});});
await p.waitForTimeout(30);
assert.equal(await p.locator('#profileDetailBody').textContent(),'Other view');
await p.evaluate(()=>{window.api=previousApi;});
await p.evaluate(()=>BotBuilder.open('review-bot'));
await p.locator('#builderPhoto').setInputFiles([]);
assert.equal(await p.locator('#builderError').isVisible(),false);
await p.locator('[data-builder-tab="3"]').click();
await p.evaluate(()=>{window.postCount=0;window.api=()=>{postCount++;return new Promise(resolve=>window.resolveSave=resolve);};});
await p.locator('#builderNext').click();
assert.equal(await p.locator('#builderBack').isDisabled(),true);
assert.equal(await p.locator('#builderNext').isDisabled(),true);
await p.evaluate(()=>{document.getElementById('builderBack').onclick();BotBuilder.save();});
assert.equal(await p.evaluate(()=>postCount),1);
await p.evaluate(()=>{BotBuilder.invalidate();document.getElementById('profileDetailBody').textContent='Other view';resolveSave({ok:true});});
await p.waitForTimeout(30);
assert.equal(await p.locator('#profileDetailBody').textContent(),'Other view');
// Deep links select the requested existing bot section without profile switching.
await p.evaluate(()=>{window.api=previousApi;});
for(const [section,selector] of [['soul','#builderPrompt'],['skills','[data-selection="skills"]'],['settings','[data-selection="mcp_servers"]'],['memory','#builderMemory']]){
  await p.evaluate(section=>BotBuilder.open('review-bot',section),section);
  assert.equal(await p.locator(selector).isVisible(),true);
}
await p.locator('#builderMemory').fill('Shared bot working notes.');
await p.locator('[data-builder-tab="1"]').click();
await p.locator('[data-builder-tab="4"]').click();
assert.equal(await p.locator('#builderMemory').inputValue(),'Shared bot working notes.');
await p.locator('#builderNext').click();
assert.equal(await p.evaluate(()=>sent.at(-1).bot_memory),'Shared bot working notes.');
// Knowledge drafts cannot be discarded by Save bot or an in-flight tab switch.
await p.evaluate(()=>{window.BotKnowledge={mount:()=>{},hasUnsaved:()=>true,isBusy:()=>false,forget:()=>{}};});
await p.evaluate(()=>BotBuilder.open('review-bot','memory'));
const beforeKnowledgeSave=await p.evaluate(()=>sent.length);
await p.locator('#builderNext').click();
assert.equal(await p.evaluate(()=>sent.length),beforeKnowledgeSave);
assert.match(await p.locator('#builderError').textContent(),/knowledge file selection/);
await p.evaluate(()=>{BotKnowledge.isBusy=()=>true;});
await p.locator('[data-builder-tab="1"]').click();
assert.equal(await p.locator('#builderMemory').isVisible(),true);
await b.close();console.log('PASS: four-step payload, no early create, selected tools/access, resized photo, 390px no overflow');})().catch(e=>{console.error(e);process.exit(1)});
