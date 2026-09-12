// CI/browser runner for the loopback fixture; never point at the application.
// The fixture uses the production form/JS and real temporary preference store.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const origin=new URL(process.env.INTERACTION_QA_ORIGIN||'http://127.0.0.1:8936');
assert.ok(['127.0.0.1','localhost','[::1]'].includes(origin.hostname),'Loopback fixture only');
assert.equal(origin.protocol,'http:');
assert.equal(origin.pathname,'/');
assert.equal(origin.username+origin.password+origin.search+origin.hash,'');
const field=(page,name)=>page.locator('#interaction'+name);
const loaded=async page=>{
 await field(page,'Status').filter({hasText:/^Saved style:/}).waitFor();
 assert.equal(await field(page,'Save').isEnabled(),true);
};
async function open(page){
 await page.goto(origin.href);
 await page.getByRole('heading',{name:'Clarification preferences QA',exact:true}).waitFor();
 assert.deepEqual(await page.locator('#actor option').allTextContents(),['alice','bob']);
 await loaded(page);
}
async function reload(page){await field(page,'Reload').click();await loaded(page)}
async function chat(page,sid){await page.locator('#chat').selectOption(sid);await reload(page)}
async function actor(page,name){await page.locator('#actor').selectOption(name);await loaded(page)}
async function save(page,userMode,taskMode){
 await field(page,'UserMode').selectOption(userMode);
 if(taskMode!==undefined)await field(page,'TaskMode').selectOption(taskMode);
 await field(page,'Save').click();
 await field(page,'Status').filter({hasText:/^Saved\. Changes apply/}).waitFor();
 assert.equal(await field(page,'Save').isEnabled(),true);
}
async function values(page){
 return {user:await field(page,'UserMode').inputValue(),task:await field(page,'TaskMode').inputValue()};
}
async function resetActor(page,name){
 await actor(page,name);
 for(const sid of ['first-chat','second-chat']){await chat(page,sid);await save(page,'balanced','')}
}
async function journey(browser,width){
 const context=await browser.newContext({viewport:{width,height:844}});
 try{
  const page=await context.newPage();await open(page);
  // Make both viewport runs independently repeatable without resetting files.
  await resetActor(page,'bob');await resetActor(page,'alice');await chat(page,'first-chat');
  await save(page,'minimal','balanced');await page.reload();await loaded(page);
  assert.deepEqual(await values(page),{user:'minimal',task:'balanced'});
  await actor(page,'bob');assert.deepEqual(await values(page),{user:'balanced',task:''});
  await actor(page,'alice');await chat(page,'second-chat');
  assert.deepEqual(await values(page),{user:'minimal',task:''});

  // Explicit reset removes only this conversation's override.
  await chat(page,'first-chat');await save(page,'minimal','');await reload(page);
  assert.deepEqual(await values(page),{user:'minimal',task:''});
  await chat(page,'');assert.equal(await field(page,'TaskMode').isEnabled(),false);
  await save(page,'balanced');await reload(page);
  assert.deepEqual(await values(page),{user:'balanced',task:''});
  const requests=JSON.parse(await page.locator('#evidence').textContent());
  assert.equal(requests.filter(r=>r.method==='POST').at(-1).body.session_id,null);
  await chat(page,'first-chat');

  // Changing the selected conversation before save must not write the old one.
  await page.locator('#chat').selectOption('second-chat');
  const postsBefore=JSON.parse(await page.locator('#evidence').textContent()).filter(r=>r.method==='POST').length;
  await field(page,'Save').click();
  await field(page,'Status').filter({hasText:'The conversation changed. Reload preferences before saving.'}).waitFor();
  assert.equal(JSON.parse(await page.locator('#evidence').textContent()).filter(r=>r.method==='POST').length,postsBefore);
  assert.equal(await field(page,'Save').isEnabled(),false);await reload(page);

  // Late GET cannot enable controls for a different conversation.
  await page.locator('#network').selectOption('slow');await field(page,'Reload').click();
  await field(page,'Status').filter({hasText:'Loading clarification preferences…'}).waitFor();
  await page.locator('#chat').selectOption('first-chat');await page.locator('#release').click();
  await field(page,'Status').filter({hasText:'The conversation changed. Reload preferences before editing.'}).waitFor();
  assert.equal(await field(page,'Save').isEnabled(),false);
  await page.locator('#network').selectOption('normal');await reload(page);

  // Late POST persists the originally chosen scope and does not enable the new one.
  await field(page,'UserMode').selectOption('minimal');await field(page,'TaskMode').selectOption('balanced');
  await page.locator('#network').selectOption('slow');await field(page,'Save').click();
  await field(page,'Status').filter({hasText:'Saving clarification preferences…'}).waitFor();
  await page.locator('#chat').selectOption('second-chat');await page.locator('#release').click();
  await field(page,'Status').filter({hasText:'Saved for the previously selected conversation.'}).waitFor();
  assert.equal(await field(page,'Save').isEnabled(),false);
  await page.locator('#network').selectOption('normal');await reload(page);
  assert.deepEqual(await values(page),{user:'minimal',task:''});
  await chat(page,'first-chat');assert.deepEqual(await values(page),{user:'minimal',task:'balanced'});

  // Offline errors require a fresh read before another write.
  await page.locator('#network').selectOption('offline');await field(page,'Save').click();
  await field(page,'Status').filter({hasText:'Reload saved preferences before trying again.'}).waitFor();
  assert.equal(await field(page,'Save').isEnabled(),false);
  await page.locator('#network').selectOption('normal');await reload(page);

  // Commit on the real fixture server, then lose its response as on a timeout.
  let lostResponse=false;
  const responseLoss=async route=>{
   if(route.request().method()!=='POST')return route.continue();
   const response=await route.fetch();assert.equal(response.status(),200);
   lostResponse=true;await route.abort('timedout');
  };
  await page.route('**/api/interaction/preferences',responseLoss);
  await field(page,'UserMode').selectOption('balanced');await field(page,'TaskMode').selectOption('');
  await field(page,'Save').click();
  await field(page,'Status').filter({hasText:'Reload saved preferences before trying again.'}).waitFor();
  assert.equal(lostResponse,true);assert.equal(await field(page,'Save').isEnabled(),false);
  await page.unroute('**/api/interaction/preferences',responseLoss);await reload(page);
  assert.deepEqual(await values(page),{user:'balanced',task:''});

  // A second tab wins a real CAS write; the stale tab must not overwrite it.
  const other=await context.newPage();await open(other);
  await save(other,'minimal','');
  await field(page,'UserMode').selectOption('balanced');await field(page,'Save').click();
  await field(page,'Status').filter({hasText:'Preferences changed in another tab.'}).waitFor();
  assert.equal(await field(page,'Save').isEnabled(),false);
  await reload(page);assert.deepEqual(await values(page),{user:'minimal',task:''});
  await actor(page,'bob');assert.deepEqual(await values(page),{user:'balanced',task:''});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  console.log('Preference persistence, isolation, reset, stale responses, response loss and CAS passed at '+width+'px');
 }finally{await context.close()}
}
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{for(const width of [1360,390])await journey(browser,width)}finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
