const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{})});try{
for(const lang of ['nl','en'])for(const width of [1440,390]){
 const p=await browser.newPage({viewport:{width,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));await p.route('http://support.test/**',r=>r.fulfill({contentType:'text/html',body:'<html></html>'}));
 await p.goto('http://support.test/');await p.setContent('<html lang="'+lang+'"><body><div id="job"><div class="main-view-content"></div></div></body></html>');
 await p.addStyleTag({path:'static/style.css'});await p.addStyleTag({path:'static/apps.css'});await p.addStyleTag({path:'static/msp.css'});await p.addStyleTag({content:'body{display:block;overflow:auto}#job{max-width:800px;margin:auto;padding:16px}label{display:block;margin:12px 0}input[type=number]{display:block;width:100%;box-sizing:border-box}p{overflow-wrap:anywhere}'});
 await p.evaluate(()=>{window._currentCronDetail={id:'daily',name:'Daily report'};window._cronOwnerProfileName=()=> 'default';window.rows=[];window.calls=[];window.api=async(path,opts)=>{if(path==='/api/msp/overview')return {permissions:{billing:true},scheduled_jobs:{jobs:rows}};const body=JSON.parse(opts.body);calls.push(body);const row={...body,revision:1,annual_support_minutes:body.support_minutes};rows=[row];return row;};});
 await p.addScriptTag({path:'static/job-costs.js'});await p.evaluate(()=>SynthPulseJobCosts.mount(_currentCronDetail,document.getElementById('job')));
 const hours=p.getByLabel(lang==='nl'?'Supporturen per jaar':'Support hours per year',{exact:true}),toggle=p.getByRole('switch');
 await hours.fill('4');await toggle.check();await p.getByRole('button',{name:lang==='nl'?'Opslaan':'Save',exact:true}).click();
 await p.getByRole('status').filter({hasText:lang==='nl'?'meegenomen':'included'}).waitFor();
 assert.equal(await hours.isDisabled(),true);assert.equal(await toggle.isDisabled(),true);assert.equal(await toggle.isChecked(),true);
 const sent=await p.evaluate(()=>calls[0]);assert.equal(sent.support_minutes,240);assert.equal(sent.support_enabled,true);
 assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 if(process.env.SUPPORT_SCREENSHOTS)await p.screenshot({path:process.env.SUPPORT_SCREENSHOTS+'/job-'+lang+'-'+width+'.png',fullPage:true});
 await p.evaluate(async()=>{const parent=document.getElementById('job');parent.querySelector('.main-view-content').replaceChildren();await SynthPulseJobCosts.mount(_currentCronDetail,parent);});
 assert.equal(await hours.inputValue(),'4');assert.equal(await toggle.isDisabled(),true);
 assert.deepEqual(errors,[]);await p.close();
}}finally{await browser.close();}console.log('Annual job support enabled, persisted and locked in NL/EN desktop/mobile');})().catch(e=>{console.error(e);process.exit(1)});
