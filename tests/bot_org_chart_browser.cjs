// Bot org chart: tree from reports_to, cycle-safe, opens bots, indented on narrow screens.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('fs'),assert=require('node:assert/strict');
const panels=fs.readFileSync('static/panels.js','utf8');
const slice=(from,to)=>{const a=panels.indexOf(from),b=panels.indexOf(to,a);assert(a>=0&&b>a,from);return panels.slice(a,b);};
const code=slice('function botDisplayName(p)','async function saveBotAppearance(){');
const bots=[
 {name:'ceo',bot:{title:'Chief Bot',category:'Board'}},
 {name:'coo',bot:{title:'Operations',reports_to:'ceo',role:'Operations'}},
 {name:'cfo',bot:{title:'Finance',reports_to:'ceo',category:'Finance'}},
 {name:'books',bot:{title:'Bookkeeper',reports_to:'cfo',category:'Finance'}},
 {name:'orphan',bot:{title:'Orphan',reports_to:'invisible'}},
 {name:'loopa',bot:{title:'Loop A',reports_to:'loopb'}},
 {name:'loopb',bot:{title:'Loop B',reports_to:'loopa'}},
];
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||undefined});
 try{for(const width of [1280,390]){
  const p=await browser.newPage({viewport:{width,height:900}});
  await p.route('**/*',r=>r.fulfill({contentType:'text/html',body:'<html></html>'}));await p.goto('http://ui.test/');
  const html=fs.readFileSync('static/index.html','utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<link\b[^>]*>/gi,'');
  await p.setContent(html);await p.addStyleTag({path:'static/style.css'});
  await p.evaluate(([code,bots])=>{
   document.getElementById('mainProfiles').style.display='flex';
   window.$=id=>document.getElementById(id);
   window.esc=s=>String(s).replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
   window.t=k=>k;window.showToast=m=>{window.lastToast=m;};
   window._profilesCache={profiles:bots,active:'ceo'};window._currentProfileDetail=null;
   window.opened=[];window.openProfileDetail=name=>opened.push(name);
   window._setProfileHeaderButtons=()=>{};window._closeMobileSidebarAfterPanelSelection=()=>{};
   (0,eval)(code);
  },[code,bots]);
  await p.evaluate(()=>openBotOrgChart());
  const shape=await p.evaluate(()=>{
   const node=li=>({name:li.querySelector(':scope>.bot-org-card').dataset.name,kids:[...li.querySelectorAll(':scope>.bot-org-children>.bot-org-node')].map(node)});
   return [...document.querySelectorAll('.bot-org-tree>.bot-org-node')].map(node);
  });
  // Roots with people below them form the tree (a stored cycle surfaced once);
  // a bot with no place (here: its manager is hidden) is listed apart.
  assert.deepEqual(shape.map(n=>n.name),['ceo','loopa','orphan']);
  assert.deepEqual(shape[0].kids.map(n=>n.name),['cfo','coo']);
  assert.deepEqual(shape[0].kids[0].kids.map(n=>n.name),['books']);
  assert.deepEqual(shape[1].kids.map(n=>n.name),['loopb']);
  assert.deepEqual(await p.evaluate(()=>[...document.querySelectorAll('.bot-org-loose>.bot-org-node>.bot-org-card')].map(c=>c.dataset.name)),['orphan']);
  assert.equal(await p.locator('.bot-org-loose-title').count(),1);
  assert.equal(await p.locator('.bot-org-card').count(),bots.length);
  assert.equal(await p.textContent('#profileDetailTitle'),'bot_org_chart');
  await p.click('.bot-org-card[data-name="books"]');
  assert.deepEqual(await p.evaluate(()=>opened),['books']);
  const overflow=await p.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  assert.ok(overflow<=0,'page must not scroll horizontally at '+width);
  const geo=await p.evaluate(()=>{const r=n=>document.querySelector(`.bot-org-card[data-name="${n}"]`).getBoundingClientRect();return {ceo:r('ceo'),cfo:r('cfo'),coo:r('coo')};});
  if(width>640){assert.ok(geo.cfo.top>geo.ceo.bottom&&Math.abs(geo.cfo.top-geo.coo.top)<1,'children side by side under the manager');}
  else{assert.ok(geo.coo.top>geo.cfo.bottom&&geo.cfo.left>geo.ceo.left,'narrow screens use an indented list');}
  // Editor select: no self, nothing below the bot; a hidden manager is preserved.
  const opts=await p.evaluate(()=>{const d=document.createElement('div');d.innerHTML=_botReportsToSelectHtml(_profilesCache.profiles.find(x=>x.name==='cfo'));return [...d.querySelectorAll('option')].map(o=>[o.value,o.selected]);});
  const values=opts.map(o=>o[0]);
  assert.ok(values.includes('')&&values.includes('ceo')&&!values.includes('cfo')&&!values.includes('books'));
  assert.deepEqual(opts.find(o=>o[1]),['ceo',true]);
  const hidden=await p.evaluate(()=>{const d=document.createElement('div');d.innerHTML=_botReportsToSelectHtml(_profilesCache.profiles.find(x=>x.name==='orphan'));const o=d.querySelector('option:checked');return [o.value,o.textContent];});
  assert.deepEqual(hidden,['invisible','bot_reports_to_hidden']);
  if(process.env.ORG_CHART_SHOT)await p.screenshot({path:process.env.ORG_CHART_SHOT.replace('.png','-'+width+'.png'),fullPage:true});
  await p.close();
 }}finally{await browser.close();}
 console.log('bot org chart browser checks passed');
})().catch(e=>{console.error(e);process.exit(1);});
