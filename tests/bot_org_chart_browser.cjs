// Bot org chart: compact columns from reports_to, cycle-safe, opens bots,
// people apart, search, no sideways scroll on a desktop or a phone.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('fs'),assert=require('node:assert/strict');
const panels=fs.readFileSync('static/panels.js','utf8');
const slice=(from,to)=>{const a=panels.indexOf(from),b=panels.indexOf(to,a);assert(a>=0&&b>a,from);return panels.slice(a,b);};
const code=slice('function _botKind(p)','async function saveBotAppearance(){');
const bots=[
 {name:'ceo',bot:{title:'Chief Bot',category:'Board'}},
 {name:'coo',bot:{title:'Operations',reports_to:'ceo',role:'Operations'}},
 {name:'cfo',bot:{title:'Finance',reports_to:'ceo',category:'Finance'}},
 {name:'books',bot:{title:'Bookkeeper',reports_to:'cfo',category:'Finance'}},
 {name:'audit',bot:{title:'Auditor',reports_to:'books',category:'Finance'}},
 {name:'orphan',bot:{title:'Orphan',reports_to:'invisible'}},
 {name:'loopa',bot:{title:'Loop A',reports_to:'loopb'}},
 {name:'loopb',bot:{title:'Loop B',reports_to:'loopa'}},
 {name:'odis',bot_kind:'person',bot:{title:'Odis',category:'Team'}},
 {name:'iflair',bot_kind:'person',bot:{title:'iFlair',category:'Partners'}},
 // A person with a bot below them stays in the tree.
 {name:'marcel',bot_kind:'person',bot:{title:'Marcel',category:'Team'}},
 {name:'sdr',bot:{title:'Sales Development',reports_to:'marcel',category:'Sales'}},
];
// The real shape that scrolled: one lead, eight departments, fifteen loose bots, ten people.
const big=[{name:'lead',bot:{title:'Chief Operating Bot',category:'Board'}}];
for(let d=0;d<8;d++){
  big.push({name:'head'+d,bot:{title:'Department head '+d,reports_to:'lead',category:'Department '+d}});
  for(let k=0;k<4;k++)big.push({name:`spec${d}_${k}`,bot:{title:`Specialist ${d}.${k}`,reports_to:'head'+d,category:'Department '+d}});
}
for(let i=0;i<15;i++)big.push({name:'loose'+i,bot:{title:'Unplaced bot '+i,category:'Other'}});
for(let i=0;i<10;i++)big.push({name:'person'+i,bot_kind:'person',bot:{title:'Person '+i,category:'Team'}});
async function render(p,list){
  await p.evaluate(list=>{window._profilesCache={profiles:list,active:list[0].name};window.opened=[];},list);
  await p.evaluate(()=>openBotOrgChart());
}
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||undefined});
 try{for(const width of [1440,1280,390]){
  const p=await browser.newPage({viewport:{width,height:900}});
  await p.route('**/*',r=>r.fulfill({contentType:'text/html',body:'<html></html>'}));await p.goto('http://ui.test/');
  const html=fs.readFileSync('static/index.html','utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<link\b[^>]*>/gi,'');
  await p.setContent(html);await p.addStyleTag({path:'static/style.css'});
  await p.evaluate(code=>{
   document.getElementById('mainProfiles').style.display='flex';
   window.$=id=>document.getElementById(id);
   window.esc=s=>String(s).replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
   window.t=k=>k;window.showToast=m=>{window.lastToast=m;};
   window._currentProfileDetail=null;
   window.openProfileDetail=name=>opened.push(name);
   window._setProfileHeaderButtons=()=>{};window._closeMobileSidebarAfterPanelSelection=()=>{};
   (0,eval)(code);
  },code);
  await render(p,bots);
  const shape=await p.evaluate(()=>[...document.querySelectorAll('.bot-org-block')].map(b=>({
   root:b.dataset.root,top:b.querySelector('.bot-org-top .bot-org-chip').dataset.name,
   cols:[...b.querySelectorAll('.bot-org-col')].map(c=>[...c.querySelectorAll('.bot-org-chip')].map(x=>x.dataset.name+':'+x.dataset.depth))})));
  // Leading bots with people below them form the tree (a stored cycle surfaced
  // once); a bot with no place (its manager is hidden) is listed apart.
  assert.deepEqual(shape.map(b=>b.root),['ceo','marcel','loopa']);
  assert.deepEqual(shape[0].cols,[['cfo:0','books:1','audit:2'],['coo:0']]);
  assert.deepEqual(shape[1].cols,[['sdr:0']]);
  assert.deepEqual(shape[2].cols,[['loopb:0']]);
  assert.deepEqual(await p.evaluate(()=>[...document.querySelectorAll('.bot-org-loose>.bot-org-chip')].map(c=>c.dataset.name)),['orphan']);
  assert.equal(await p.locator('.bot-org-loose-title').count(),1);
  // People without bots below them: a collapsed strip of their own.
  assert.equal(await p.locator('.bot-org-people').evaluate(d=>d.open),false);
  assert.deepEqual(await p.evaluate(()=>[...document.querySelectorAll('.bot-org-people .bot-org-chip')].map(c=>c.dataset.name)),['iflair','odis']);
  assert.equal(await p.locator('.bot-org-chip').count(),bots.length);
  assert.equal(await p.textContent('#profileDetailTitle'),'bot_org_chart');
  await p.click('.bot-org-chip[data-name="books"]');
  assert.deepEqual(await p.evaluate(()=>opened),['books']);
  const geo=await p.evaluate(()=>{const r=n=>document.querySelector(`.bot-org-chip[data-name="${n}"]`).getBoundingClientRect();return {ceo:r('ceo'),cfo:r('cfo'),coo:r('coo'),books:r('books')};});
  assert.ok(geo.cfo.top>geo.ceo.bottom&&geo.books.top>=geo.cfo.bottom&&geo.books.height<=40,'compact one-line chips stacked under the column head');
  if(width>640)assert.ok(Math.abs(geo.cfo.top-geo.coo.top)<1&&geo.coo.left>geo.cfo.right,'columns side by side');
  else assert.ok(geo.coo.top>geo.books.bottom,'columns stack on a phone');
  // Search narrows the chart and opens the people strip on a match there.
  await p.fill('#botOrgSearch','odis');
  assert.equal(await p.locator('.bot-org-chip:visible').count(),1);
  assert.equal(await p.locator('.bot-org-people').evaluate(d=>d.open),true);
  await p.fill('#botOrgSearch','book');
  assert.deepEqual(await p.evaluate(()=>[...document.querySelectorAll('.bot-org-chip')].filter(c=>c.offsetParent).map(c=>c.dataset.name)),['books']);
  await p.fill('#botOrgSearch','nothing like this');
  assert.equal(await p.locator('.bot-org-no-match').isVisible(),true);
  await p.fill('#botOrgSearch','');
  assert.equal(await p.locator('.bot-org-chip[data-name="coo"]').isVisible(),true);
  // The real shape fits: no sideways scroll, the whole tree in one screen on a desktop.
  await render(p,big);
  const fit=await p.evaluate(()=>{const tree=document.querySelector('.bot-org-tree').getBoundingClientRect();return {
   overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
   inner:[...document.querySelectorAll('.bot-org-scroll,.bot-org-col')].some(e=>e.scrollWidth>e.clientWidth+1),
   tree:tree.height,people:document.querySelectorAll('.bot-org-people .bot-org-chip').length,open:document.querySelector('.bot-org-people').open};});
  assert.ok(fit.overflow<=0&&!fit.inner,'no horizontal scroll at '+width);
  assert.equal(fit.people,10);assert.equal(fit.open,false);
  if(width>=1440)assert.ok(fit.tree<=600,'the whole tree fits a 1440x900 screen, was '+fit.tree);
  // Editor select: no self, nothing below the bot; a hidden manager is preserved.
  await render(p,bots);
  const opts=await p.evaluate(()=>{const d=document.createElement('div');d.innerHTML=_botReportsToSelectHtml(_profilesCache.profiles.find(x=>x.name==='cfo'));return [...d.querySelectorAll('option')].map(o=>[o.value,o.selected]);});
  const values=opts.map(o=>o[0]);
  assert.ok(values.includes('')&&values.includes('ceo')&&!values.includes('cfo')&&!values.includes('books'));
  assert.deepEqual(opts.find(o=>o[1]),['ceo',true]);
  const hidden=await p.evaluate(()=>{const d=document.createElement('div');d.innerHTML=_botReportsToSelectHtml(_profilesCache.profiles.find(x=>x.name==='orphan'));const o=d.querySelector('option:checked');return [o.value,o.textContent];});
  assert.deepEqual(hidden,['invisible','bot_reports_to_hidden']);
  // Kind select: Automatic (empty, the default rule) first and chosen while no
  // kind is stored; an explicit kind stays selected.
  const kinds=await p.evaluate(()=>[{name:'a',bot_kind:'person',bot:{}},{name:'b',bot_kind:'bot',bot:{kind:'bot'}},{name:'c',bot_kind:'person',bot:{kind:'person'}}].map(x=>{const d=document.createElement('div');d.innerHTML=_botKindSelectHtml(x);return [...d.querySelectorAll('option')].map(o=>[o.value,o.selected,o.textContent]);}));
  assert.deepEqual(kinds[0],[['',true,'bot_kind_auto (bot_kind_person)'],['bot',false,'bot_kind_bot'],['person',false,'bot_kind_person']]);
  assert.deepEqual(kinds[1].map(o=>o[1]),[false,true,false]);
  assert.deepEqual(kinds[2].map(o=>o[1]),[false,false,true]);
  assert.equal(kinds[2][0][2],'bot_kind_auto');
  if(process.env.ORG_CHART_SHOT){await render(p,big);await p.screenshot({path:process.env.ORG_CHART_SHOT.replace('.png','-'+width+'.png'),fullPage:true});}
  await p.close();
 }}finally{await browser.close();}
 console.log('bot org chart browser checks passed');
})().catch(e=>{console.error(e);process.exit(1);});
