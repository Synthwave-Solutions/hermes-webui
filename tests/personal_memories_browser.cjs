const {chromium}=require('playwright');
const fs=require('fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try { for (const width of [1440,768,390]) {
  const p=await browser.newPage({viewport:{width,height:900}});
  await p.setContent('<main id="mainMemory"><h1>Personal memory</h1><h2 id="memoryDetailTitle">My notes</h2><div id="memoryDetailBody"><p>No notes yet</p></div></main>');
  await p.addStyleTag({path:'static/style.css'});
  await p.addStyleTag({content:'body{overflow:auto;display:block}main{max-width:900px;margin:auto;padding:16px}h1,h2{margin:16px} .main-view-content{padding:16px}'});
  if(process.env.MEMORY_SCREENSHOTS) await p.screenshot({path:process.env.MEMORY_SCREENSHOTS+'/memory-before-'+width+'.png'});
  await p.addStyleTag({path:'static/personal-memories.css'});
  await p.addScriptTag({path:'static/personal-memories.js'});
  await p.evaluate(()=>{
   window.items=[{id:'a'.repeat(32),bank:'private',revision:'v1',scope:'private',timestamp:'2026-09-30T09:00:00',content:'I prefer short answers in Dutch.'},{id:'b'.repeat(32),bank:'c'.repeat(64),revision:'v2',scope:'shared chat',timestamp:'2026-09-30T08:00:00',content:'<img src=x onerror="window.xss=1"> Shared project prefers weekly updates.'}];
   window.requests=[];window.current='first';window.fail=false;
   window.options={context:()=>current,sessionId:'first',active:()=>true,confirm:async()=>true,api:async(url,opts)=>{
    if(opts){const data=JSON.parse(opts.body);requests.push(data);if(fail)throw Error('Memory changed. Refresh before editing again.');
     const row=items.find(x=>x.id===data.id);if(data.operation==='edit')row.content=data.content;else items=items.filter(x=>x!==row);
     return {ok:true};}
    const q=new URL(url,'http://fixture.test').searchParams.get('q');const found=items.filter(x=>!q||x.content.includes(q));
    return {items:found,total:found.length,limit:50};
   }};
   document.getElementById('memoryDetailTitle').textContent='Saved memories';
   PersonalMemories.render(document.getElementById('memoryDetailBody'),options);
  });
  await p.getByRole('status').filter({hasText:'2 saved memories'}).waitFor();
  assert.equal(await p.evaluate(()=>!!window.xss),false);
  assert.equal(await p.locator('article img').count(),0);
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  if(process.env.MEMORY_SCREENSHOTS)await p.screenshot({path:process.env.MEMORY_SCREENSHOTS+'/memory-after-'+width+'.png'});
  await p.getByRole('button',{name:'Edit',exact:true}).first().click();
  await p.getByRole('textbox',{name:'Memory content'}).fill('I prefer detailed answers.');
  await p.getByRole('button',{name:'Save',exact:true}).click();
  await p.getByText('I prefer detailed answers.',{exact:true}).waitFor();
  assert.equal(await p.evaluate(()=>requests[0].revision),'v1');
  await p.getByRole('searchbox').fill('weekly');await p.getByRole('button',{name:'Search',exact:true}).click();
  await p.getByRole('status').filter({hasText:'1 saved memories'}).waitFor();
  await p.getByRole('button',{name:'Delete',exact:true}).click();
  await p.getByRole('status').filter({hasText:'No saved memories yet'}).waitFor();
  await p.getByRole('searchbox').fill('');await p.getByRole('button',{name:'Search',exact:true}).click();
  await p.getByRole('button',{name:'Edit',exact:true}).click();
  await p.evaluate(()=>fail=true);await p.getByRole('button',{name:'Save',exact:true}).click();
  await p.getByRole('alert').filter({hasText:'Memory changed'}).waitFor();
  assert.equal(await p.getByRole('button',{name:'Save',exact:true}).isEnabled(),true);
  await p.getByRole('button',{name:'Cancel',exact:true}).click();
  // A late request from the previously selected chat cannot restore its data.
  await p.evaluate(()=>{options.api=()=>new Promise(resolve=>window.late=resolve);PersonalMemories.render(document.getElementById('memoryDetailBody'),options);current='second';document.getElementById('memoryDetailBody').replaceChildren();late({items,total:items.length,limit:50});});
  assert.equal(await p.locator('#memoryDetailBody').textContent(),'');
  console.log('PASS personal memories:',width);await p.close();
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
