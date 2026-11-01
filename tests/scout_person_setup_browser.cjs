// Browser behavior against the real Scout renderer and bot editor, with synthetic API data.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=process.env.SCOUT_SOURCE || '.';
const source=fs.readFileSync(path.join(root,'static/panels.js'),'utf8');
const scout=source.slice(source.indexOf('// Scout card (api/bot_scout.py)'),source.indexOf('// Responsibilities card ('));

(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH || undefined});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    page.setDefaultTimeout(10000);
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.setContent('<html class="dark"><body><main style="width:100%;height:100%;overflow:auto"><h1 id="profileDetailTitle"></h1><div id="profileDetailEmpty"></div><div id="profileDetailBody"></div><button id="btnSaveProfileDetail"></button></main></body></html>');
    await page.evaluate(()=>{
      window.__GOV_ME__={email:'alex@example.test'};
      window.catalogs={};window.__registerHermesLocale=(code,entries)=>catalogs[code]=entries;
      window.t=key=>catalogs.nl?.[key]||catalogs.en?.[key]||key;
      window.$=id=>document.getElementById(id);
      window.esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');
      window._botKind=p=>p.bot_kind;
      window._currentProfileDetail=null;window._profileMode='';
      window._setProfileHeaderButtons=()=>{};window.switchPanel=()=>{};
      window._profileDropdownClearStoredCache=()=>{};window.showToast=()=>{};
      window.loadProfilesPanel=async()=>{throw Error('Scout save must stay in its editor');};
      window.fixture={name:'assistant',bot_kind:'bot',bot_revision:3,bot_editable:true,scout_manageable:true,scout_people_count:1,
        bot:{title:'Executive Assistant',scout:{digest_time:'07:30',frequency:'daily',topics:['Planning'],people:{'alex@example.test':{enabled:true,prompt:'Prepare my day.'}}}},
        scout_me:{known:true,enabled:true,digest_time:'07:30',frequency:'daily',prompt:'Prepare my day.'}};
      window.people=['alex@example.test','sam@example.test','lee@example.test'].map(email=>({email,enabled:email.startsWith('alex'),digest_time:'07:30',frequency:'daily'}));
      window.calls=[];window.failSave=false;window.holdSave=false;
      window.api=async(url,options)=>{
        const body=options?.body?JSON.parse(options.body):null;calls.push({url,body});
        if(url.startsWith('/api/bots/builder'))return {can_edit:true,catalog:{},config:{name:'assistant',title:'Executive Assistant',system_prompt:'Help prepare useful work.'}};
        if(url.startsWith('/api/profiles'))return {profiles:[structuredClone(fixture)]};
        if(body?.action==='people')return {people:structuredClone(people)};
        if(failSave)throw Error('Access changed. Please retry.');
        if(holdSave)await new Promise(resolve=>window.finishSave=resolve);
        const result=structuredClone(fixture),email=body.person||'alex@example.test';
        result.bot_revision++;
        if('topics' in body){result.bot.scout.topics=body.topics;result.bot.scout.frequency=body.default_frequency;result.bot.scout.digest_time=body.default_time;}
        else result.bot.scout.people[email]={enabled:body.enabled,prompt:body.prompt,digest_time:body.digest_time,frequency:body.frequency,cross_bot_context:body.cross_bot_context};
        result.scout_people_count=Object.values(result.bot.scout.people).filter(e=>e.enabled).length;
        if(email==='alex@example.test' && !('topics' in body))result.scout_me={...result.bot.scout.people[email],known:true,own_time:!!body.digest_time,own_frequency:!!body.frequency};
        window.fixture=result;
        return {...result,ok:true,scout_person:email,scout_job:{id:'job-'+email,enabled:body.enabled}};
      };
    });
    const helpers=fs.readFileSync(path.join(root,'static/i18n.js'),'utf8');
    await page.addScriptTag({content:helpers.slice(helpers.indexOf('function _i18nProcessedElapsed('),helpers.indexOf('window.__registerHermesLocale='))});
    for(const file of ['style.css','bot-builder.css','workspace-clarity.css'])await page.addStyleTag({path:path.join(root,'static/'+file)});
    for(const file of ['i18n/en.js','i18n/nl.js'])await page.addScriptTag({path:path.join(root,'static/'+file)});
    await page.addScriptTag({content:scout});await page.addScriptTag({path:path.join(root,'static/bot-builder.js')});
    await page.evaluate(()=>BotBuilder.open('assistant','scout'));
    await page.locator('#botScoutPrompt').waitFor();
    assert.deepEqual(errors,[],'fixture loads the real locale helpers');
    if(process.env.SCOUT_SCREENSHOTS){
      fs.mkdirSync(process.env.SCOUT_SCREENSHOTS,{recursive:true});
      for(const width of [1440,900,390]){
        await page.setViewportSize({width,height:1000});
        await page.locator('.bot-builder').screenshot({path:path.join(process.env.SCOUT_SCREENSHOTS,`scout-${process.env.SCOUT_PHASE||'after'}-${width}.png`)});
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'no horizontal overflow');
      }
    }
    await page.evaluate(()=>selectBotScoutPerson('sam@example.test'));
    await page.locator('#botScoutPrompt').fill('Keep this personal draft');
    await page.evaluate(()=>selectBotScoutPerson('lee@example.test'));
    assert.equal(await page.locator('#botScoutPrompt').inputValue(),'');
    await page.evaluate(()=>selectBotScoutPerson('sam@example.test'));
    assert.equal(await page.locator('#botScoutPrompt').inputValue(),'Keep this personal draft','switching people retains their separate drafts');
    assert.equal(await page.evaluate(()=>calls.filter(c=>c.body&&c.body.action!=='people').length),0,'editing never starts a Scout');
    await page.locator('#builderTab1').click();await page.locator('#builderPrompt').fill('Bot configuration draft');
    await page.locator('#builderTab6').click();
    assert.equal(await page.locator('#botScoutPrompt').inputValue(),'Keep this personal draft','Scout draft survives editor tab switch');
    await page.locator('[data-scout-template="agenda"]').click();
    assert.match(await page.locator('#botScoutPrompt').inputValue(),/^Keep this personal draft/);
    assert.equal(await page.locator('#botScoutCrossBot').isChecked(),false,'templates do not grant extra conversation context');
    await page.locator('#botScoutFrequency').selectOption('weekdays');
    await page.locator('#botScoutInheritTime').uncheck();await page.locator('#botScoutTime').fill('08:45');
    await page.locator('#botScoutTime').fill('');
    const assertEmptyCustomTime=async context=>{
      assert.equal(await page.locator('#botScoutInheritTime').isChecked(),false,context+': inheritance stays unchecked');
      assert.equal(await page.locator('#botScoutTime').isDisabled(),false,context+': custom time stays editable');
      assert.equal(await page.locator('#botScoutTime').inputValue(),'',context+': empty custom time stays empty');
      assert.equal(await page.locator('#botScoutTime').evaluate(input=>input.validity.valid),false,context+': empty custom time stays invalid');
      const writes=await page.evaluate(()=>calls.length);
      await page.locator('#botScoutSave').click();await page.locator('#botScoutPause').click();
      assert.equal(await page.evaluate(()=>calls.length),writes,context+': invalid custom time blocks both save actions');
    };
    await page.evaluate(()=>selectBotScoutPerson('lee@example.test'));
    await page.evaluate(()=>selectBotScoutPerson('sam@example.test'));
    await assertEmptyCustomTime('person switch');
    await page.locator('#builderTab1').click();await page.locator('#builderTab6').click();
    await assertEmptyCustomTime('editor tab switch');
    await page.locator('#botScoutTime').fill('08:45');
    await page.evaluate(()=>{failSave=true;});await page.locator('#botScoutSave').click();
    assert.match(await page.locator('#botScoutError').textContent(),/Access changed/);
    assert.match(await page.locator('#botScoutPrompt').inputValue(),/^Keep this personal draft/);
    await page.evaluate(()=>{failSave=false;holdSave=true;});
    await page.locator('#botScoutSave').click();
    await page.waitForFunction(()=>typeof finishSave==='function');
    assert.ok(await page.locator('#botScoutSave').isDisabled());
    const count=await page.evaluate(()=>calls.length);
    await page.evaluate(()=>saveBotScout(true));assert.equal(await page.evaluate(()=>calls.length),count,'double submit is ignored');
    await page.evaluate(()=>{holdSave=false;finishSave();});
    await page.waitForFunction(()=>document.getElementById('botScoutStatus')?.textContent.includes('opgeslagen'));
    const sent=await page.evaluate(()=>calls.filter(c=>c.body&&c.body.action!=='people').at(-1).body);
    assert.equal(sent.person,'sam@example.test');assert.equal(sent.frequency,'weekdays');assert.equal(sent.digest_time,'08:45');assert.equal(sent.revision,3);
    assert.equal(sent.enabled,true);assert.equal('topics' in sent,false);assert.equal('inherit_time' in sent,false,'draft inheritance state stays out of the API payload');
    await page.locator('#builderTab1').click();assert.equal(await page.locator('#builderPrompt').inputValue(),'Bot configuration draft');
    await page.locator('#builderTab6').click();
    await page.locator('#botScoutPeople summary').click();
    const beforeSearch=await page.evaluate(()=>calls.length);
    await page.locator('#botScoutSearch').fill('no-match');assert.ok(await page.locator('#botScoutNoPeople').isVisible());
    await page.locator('#botScoutSearch').fill('lee@');
    assert.equal(await page.locator('.bot-scout-person:visible').count(),1);
    assert.equal(await page.evaluate(()=>calls.length),beforeSearch,'people search is local');
    await page.locator('.bot-scout-person[value="lee@example.test"]').click();
    assert.equal(await page.locator('#botScoutPrompt').inputValue(),'');
    await page.evaluate(()=>selectBotScoutPerson('denied@example.test'));
    assert.match(await page.locator('#botScoutTitle').textContent(),/lee@example.test/,'unknown people cannot become the target');
    await page.locator('#botScoutDefaults summary').click();
    await page.locator('#botScoutDefaultTime').fill('06:30');
    await page.locator('#botScoutPrompt').fill('Lee only');
    await page.locator('#botScoutPause').click();
    await page.waitForFunction(()=>document.getElementById('botScoutStatus')?.textContent.includes('opgeslagen'));
    assert.equal(await page.locator('#botScoutDefaultTime').inputValue(),'06:30','personal save preserves shared default draft');
    let last=await page.evaluate(()=>calls.filter(c=>c.body&&c.body.action!=='people').at(-1).body);
    assert.equal(last.person,'lee@example.test');assert.equal(last.enabled,false);assert.equal(last.digest_time,'');assert.equal(last.frequency,'');
    assert.equal('inherit_time' in last,false,'inherited API time uses only the existing empty-string contract');
    await page.locator('#botScoutInheritTime').uncheck();await page.locator('#botScoutTime').fill('');
    await page.locator('#botScoutDefaults button').last().click();
    await page.waitForFunction(()=>document.getElementById('botScoutStatus')?.textContent.includes('instellingen'));
    last=await page.evaluate(()=>calls.filter(c=>c.body&&c.body.action!=='people').at(-1).body);
    assert.equal(last.default_time,'06:30');assert.equal('person' in last,false);assert.equal('enabled' in last,false);
    await assertEmptyCustomTime('shared defaults save');
    // No extra privileges or people controls for a normal bot user.
    await page.evaluate(()=>{
      BotBuilder.invalidate();const p=structuredClone(fixture);p.scout_manageable=false;p.bot_editable=false;
      delete p.bot.scout.people;delete p.scout_people_count;_currentProfileDetail=p;
      document.getElementById('profileDetailBody').innerHTML=_botScoutCardHtml(p);
    });
    assert.equal(await page.locator('#botScoutPeople').count(),0);assert.equal(await page.locator('#botScoutDefaults').count(),0);
    await page.evaluate(()=>selectBotScoutPerson('sam@example.test'));
    await page.locator('#botScoutPrompt').fill('Only my private setup');
    await page.locator('#botScoutInheritTime').uncheck();await page.locator('#botScoutTime').fill('');
    let writes=await page.evaluate(()=>calls.length);await page.locator('#botScoutSave').click();
    assert.equal(await page.evaluate(()=>calls.length),writes,'an empty custom time cannot accidentally become inherited');
    await page.locator('#botScoutTime').fill('09:15');
    await page.evaluate(()=>{holdSave=true;});await page.locator('#botScoutSave').click();
    await page.waitForFunction(()=>document.getElementById('botScoutControls').disabled);
    last=await page.evaluate(()=>calls.filter(c=>c.body&&c.body.action!=='people').at(-1).body);
    assert.equal('person' in last,false,'normal user saves only themselves');
    // Late completion must not steal navigation or paint another bot's card.
    await page.evaluate(()=>{_currentProfileDetail={name:'different'};document.getElementById('profileDetailBody').textContent='Another bot';holdSave=false;finishSave();});
    await page.waitForTimeout(50);assert.equal(await page.locator('#profileDetailBody').textContent(),'Another bot');
    assert.deepEqual(errors,[]);
    console.log('PASS Scout setup: person drafts, templates, explicit activation, errors, single submit, revisions, editor preservation');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
