// Isolated browser coverage using the real task detail and notification handlers.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const cp = require('node:child_process');
const source = fs.readFileSync(process.env.CRON_NOTIFICATION_SOURCE || 'static/panels.js', 'utf8');
const detail = text => text.slice(text.indexOf('function _renderCronDetail(job){'), text.indexOf('function _setCronHeaderButtons('));
const toggle = source.slice(source.indexOf('async function toggleCurrentCronNotifications('), source.indexOf('function _renderCronDetail(job){'));
(async () => {
 const browser = await chromium.launch({headless:true});
 try {
  for (const width of [1360, 390]) {
   const page = await browser.newPage({viewport:{width,height:900}});
   await page.setContent('<main style="max-width:900px;margin:auto;padding:16px"><h1 id="taskDetailTitle"></h1><div id="taskDetailEmpty"></div><div id="taskDetailBody"></div></main>');
   await page.addStyleTag({path:'static/style.css'});
   await page.evaluate(() => {
    window.$ = id => document.getElementById(id);
    window.esc = text => String(text ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
    window.t = key => ({cron_toast_notifications_label:'Notifications',cron_toast_notifications_hint:'Show a pop-up when this task finishes. Task execution and delivery stay unchanged.',cron_toast_notifications_enabled:'Enabled',cron_toast_notifications_disabled:'Disabled',cron_status_active:'Active',error_prefix:'Error: '}[key] || key);
    window.S = {activeProfile:'default'};
    window._cronNotificationSaves = new Set();
    window._cronNewJobIds = new Set();
    window._cronMode = 'read';
    window._currentCronDetail = null;
    window._currentCronDetailKey = '';
    window._disposeCronSkillPicker = () => {};
    window._cronJobKey = job => `${job.profile || 'default'}\0${job.id}`;
    window._cronStatusMeta = () => ({state:'active',detailClass:'active',label:'Active'});
    window._isCronScriptJob = job => !!job.no_agent;
    window._cronModeLabel = () => 'Agent';
    window._cronProfileLabel = value => value || 'Default';
    window._cronProfileTitle = window._cronProfileLabel;
    window._cronOwnerProfileName = job => job.profile || 'default';
    window._cronProfileName = value => value || 'default';
    window._cronOutputTitle = () => 'Latest runs';
    window._cronScriptCardHtml = window._cronAgentPromptCardHtml = window._cronDiagramCardHtml = window._cronMetaBarHtml = window._cronScriptJobBannerHtml = () => '';
    window._setCronHeaderButtons = window._loadCronDetailRuns = () => {};
    window.toasts = [];
    window.showToast = text => toasts.push(text);
    window.saved = [{id:'first',name:'Daily report',enabled:true,deliver:'email',schedule_display:'Every day at 09:00'}, {id:'second',name:'Weekly review',enabled:true,toast_notifications:false}];
    window._cronList = structuredClone(saved);
    window.requests = [];
    window.network = 'ok';
    window.api = async (url, options) => {
     const body = JSON.parse(options.body); requests.push(body);
     if (network === 'slow') await new Promise(resolve => window.release = resolve);
     if (network === 'error') throw new Error('Offline');
     const job = saved.find(row => row.id === body.job_id);
     job.toast_notifications = body.toast_notifications;
     return {ok:true,job:structuredClone(job)};
    };
   });
   if (process.env.CRON_NOTIFICATION_EVIDENCE) {
    const before = cp.execFileSync('git',['show','HEAD:static/panels.js'],{encoding:'utf8'});
    await page.addScriptTag({content:detail(before)});
    await page.evaluate(() => _renderCronDetail(structuredClone(saved[0])));
    await page.screenshot({path:`${process.env.CRON_NOTIFICATION_EVIDENCE}/before-${width}.png`,fullPage:true});
   }
   await page.addScriptTag({content:toggle + detail(source)});
   await page.evaluate(() => _renderCronDetail(structuredClone(saved[0])));
   const button = page.getByRole('switch',{name:'Notifications'});
   assert.equal(await button.count(),1, 'Task details must expose a notification switch');
   assert.equal(await button.getAttribute('aria-checked'),'true');
   await button.click();
   await page.waitForFunction(() => document.getElementById('cronDetailNotifications').getAttribute('aria-checked') === 'false');
   assert.deepEqual(await page.evaluate(() => requests[0]),{job_id:'first',toast_notifications:false});
   assert.equal(await page.evaluate(() => saved[0].enabled && saved[0].deliver === 'email'),true);
   assert.equal(await page.evaluate(() => saved[1].toast_notifications),false);
   await page.evaluate(() => _renderCronDetail(structuredClone(saved[0])));
   assert.equal(await button.getAttribute('aria-checked'),'false');
   await button.focus(); await page.keyboard.press('Space');
   await page.waitForFunction(() => document.getElementById('cronDetailNotifications').getAttribute('aria-checked') === 'true');
   await page.evaluate(() => network = 'error'); await button.click();
   await page.waitForFunction(() => toasts.length === 1);
   assert.equal(await button.getAttribute('aria-checked'),'true');
   assert.equal(await button.isEnabled(),true);
   // A double click while saving is ignored. Navigating to another task cannot
   // let the first task's late response overwrite the newly selected control.
   await page.evaluate(() => {network='slow'; toggleCurrentCronNotifications($('cronDetailNotifications')); toggleCurrentCronNotifications($('cronDetailNotifications'));});
   assert.equal(await button.isDisabled(),true);
   const count = await page.evaluate(() => requests.length);
   await page.evaluate(() => {_renderCronDetail(structuredClone(saved[1])); release();});
   await page.waitForFunction(() => _cronNotificationSaves.size === 0);
   assert.equal(await button.getAttribute('aria-checked'),'false');
   assert.equal(await page.evaluate(() => requests.length),count);
   // Read-only tasks expose the state but cannot write it.
   await page.evaluate(() => _renderCronDetail({...saved[1],read_only:true}));
   assert.equal(await button.isDisabled(),true);
   await page.evaluate(() => toggleCurrentCronNotifications($('cronDetailNotifications')));
   assert.equal(await page.evaluate(() => requests.length),count);
   await page.evaluate(() => _renderCronDetail(structuredClone(saved[0])));
   assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),true);
   if (process.env.CRON_NOTIFICATION_EVIDENCE) await page.screenshot({path:`${process.env.CRON_NOTIFICATION_EVIDENCE}/after-${width}.png`,fullPage:true});
   await page.evaluate(() => {
    window._cronPollTimer = null; window._cronPollGeneration = 0; window._cronPollSince = 0;
    window.setInterval = fn => {window.poll = fn; return 1;};
    window.updateCronBadge = () => {};
    window.api = async () => ({completions:[
      {job_id:'first',name:'Muted',completed_at:1,toast_notifications:false},
      {job_id:'second',name:'Loud',completed_at:2,toast_notifications:true},
    ]});
    toasts.length = 0;
   });
   await page.addScriptTag({content:source.slice(source.indexOf('function startCronPolling(){'), source.indexOf('function updateCronBadge(){'))});
   await page.evaluate(async () => {startCronPolling(); await poll();});
   assert.equal(await page.evaluate(() => toasts.length),1);
   assert.deepEqual(await page.evaluate(() => [..._cronNewJobIds]),['first','second']);
   console.log(`Notification toggle, isolation, keyboard, errors and late responses passed at ${width}px`);
   await page.close();
  }
 } finally { await browser.close(); }
})().catch(error => {console.error(error);process.exitCode=1;});
