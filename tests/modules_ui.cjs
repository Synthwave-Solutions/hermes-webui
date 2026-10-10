'use strict';
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH});
 const page=await browser.newPage({viewport:{width:390,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://modules.test/**',route=>{
  if(new URL(route.request().url()).pathname==='/')return route.fulfill({contentType:'text/html',body:`<!doctype html><html lang="en"><head><style>body{--surface:white;--text:black;--border:gray;--muted:#555;--hover-bg:#eee;--accent:blue;font-family:sans-serif}.main{width:100%}</style><link rel="stylesheet" href="/static/modules.css"></head><body><button id="btnApps" data-module-gated hidden>Apps</button><button data-module-gated data-panel="modules" hidden>Modules</button><main class="main showing-modules"><div id="mainModules"></div></main><script>window.api=async()=>{throw Error('offline')};</script><script src="/static/module-content.js"></script><script src="/static/modules.js"></script></body></html>`});
  const p=path.resolve(__dirname,'..','.'+new URL(route.request().url()).pathname);return route.fulfill({path:p});
 });
 await page.goto('http://modules.test/');assert(await page.locator('#btnApps').isHidden());
 await page.evaluate(()=>{
  window.testRows=[{id:'design_studio',tier:'standard',status:'unavailable',reason:'unknown_reason',model_usage:'medium',works_with:[
   {name:{en:'Consent only',nl:'Alleen toestemming'},status:'off',other_modules:[],consent:['admin_approve']},
   {name:{en:'Owner only',nl:'Alleen eigenaar'},status:'off',other_modules:[],consent:['owner_confirm']},
   {name:{en:'No consent class',nl:'Geen toestemmingsklasse'},status:'off',other_modules:[],consent:['none']},
   {name:{en:'<img src=x onerror=alert(1)>',nl:'Veilige tekst'},status:'off',other_modules:[],consent:['none']},
  ]}];
  window.api=async()=>({modules:window.testRows,apps:[]});
  window.SynthPulseModules.apply({enabled_modules:['design_studio'],module_nav:{hidden_panels:[],modules_visible:true,apps_visible:true}});
  return window.SynthPulseModules.load();
 });
 await page.locator('summary').click();assert.equal(await page.locator('.module-meta').filter({hasText:'Only with the consent'}).count(),2);assert.equal(await page.locator('#mainModules img').count(),0);assert(await page.locator('#mainModules').innerText().then(t=>t.includes('Not available here')));
 await page.locator('#mainModules select').selectOption('nl');await page.locator('summary').click();assert.equal(await page.locator('.module-meta').filter({hasText:'Alleen met toestemming'}).count(),2);
 await page.evaluate(async()=>{window.testRows[0].works_with=[];await window.SynthPulseModules.load();});assert.equal(await page.locator('summary').count(),0);
 await page.locator('#btnApps').click();assert(await page.locator('#appsPopover').innerText().then(t=>t.includes('geen app-links')));await page.keyboard.press('Escape');assert(await page.locator('#btnApps').evaluate(e=>e===document.activeElement));
 await page.evaluate(async()=>{window.api=async()=>{throw Error('offline')};await window.SynthPulseModules.refresh();});assert(await page.locator('#btnApps').isHidden());assert(await page.locator('[data-panel="modules"]').isHidden());assert.equal(await page.locator('.module-card').count(),0);
 assert.deepEqual(errors,[]);await browser.close();console.log('Modules UI: 11 assertions passed (consent, unknown reason, NL/EN, no registry, XSS, empty links, keyboard, failure).');
})().catch(e=>{console.error(e);process.exitCode=1;});
