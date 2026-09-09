// Actual production WebRTC/provider negotiation; synthetic muted capture, no physical microphone.
const fs = require('fs');
const os = require('os');
const cp = require('child_process');
const crypto = require('crypto');
const { chromium } = require('/home/synthwavehq/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const root = '/home/synthwavehq/work/synthpulse';
const base = 'http://127.0.0.1:8787';
const title = 'QA native voice connection ' + crypto.randomUUID();
const report = {kind:'actual_provider_browser_negotiation', physical_microphone:'NOT_USED_SYNTHETIC_MUTED_CAPTURE', started_at_utc:new Date().toISOString(), title, requests:[], page_errors:[], cleanup:{}};
let browser, context, page, sid, authHeaders;
let hostVerified = false;
const need = (value, reason) => { if (!value) throw new Error(reason); };
(async()=>{
  try {
    need(os.hostname()==='synthwave-vps' && process.getuid()===1000, 'unexpected_host_or_user');
    hostVerified = true;
    process.umask(0o077);
    const deployment=JSON.parse(fs.readFileSync(root+'/qa-release-deployment-v3-20260909.json','utf8'));
    need(deployment.gateway_drains_released && deployment.governance_policy_preserved, 'deployment_not_verified');
    const pid=Number(cp.execFileSync('systemctl',['--user','show','hermes-webui.service','--property=MainPID','--value'],{encoding:'utf8'}).trim());
    need(pid===deployment.services_after_release['hermes-webui.service'].pid, 'webui_instance_changed');
    const env=Object.fromEntries(fs.readFileSync('/proc/'+pid+'/environ').toString().split('\0').filter(x=>x.includes('=')).map(x=>[x.slice(0,x.indexOf('=')),x.slice(x.indexOf('=')+1)]));
    need(Boolean(env.HERMES_WEBUI_PASSWORD),'runtime_password_missing');
    browser=await chromium.launch({headless:true,executablePath:'/home/synthwavehq/.cloakbrowser/chromium-146.0.7680.177.3/chrome',args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
    context=await browser.newContext({baseURL:base,permissions:['microphone'],viewport:{width:1440,height:1000}});
    const login=await context.request.post('/api/auth/login',{data:{password:env.HERMES_WEBUI_PASSWORD}});
    delete env.HERMES_WEBUI_PASSWORD;
    need(login.status()===200,'normal_login_failed');
    const shell=await context.request.get('/');
    const csrf=(await shell.text()).match(/csrfToken:("(?:\\.|[^"\\])*")/);
    need(csrf,'normal_csrf_missing');
    authHeaders={'Origin':base,'X-Hermes-CSRF-Token':JSON.parse(csrf[1])};
    const created=await context.request.post('/api/session/import',{headers:authHeaders,data:{title,workspace:root,messages:[{role:'user',content:'Synthetic connection check only. Do not use tools or start tasks.'}]}});
    need(created.status()===200,'synthetic_session_create_failed');
    sid=(await created.json()).session.session_id;
    need(/^[a-zA-Z0-9_-]{1,128}$/.test(sid),'invalid_synthetic_session');
    page=await context.newPage();
    page.on('pageerror',e=>report.page_errors.push(e.name));
    page.on('response',r=>{const u=new URL(r.url());if(u.pathname.startsWith('/api/voice/realtime/'))report.requests.push({path:u.pathname,status:r.status()});});
    await page.goto(base+'/session/'+sid,{waitUntil:'domcontentloaded'});
    await page.locator('#msg').fill('Unsent synthetic voice draft');
    await page.locator('#btnRealtimeVoice').click();
    try { await page.locator('#realtimeVoiceStatus').filter({hasText:'Microphone muted'}).waitFor({state:'visible',timeout:45000}); report.provider_connected=true; }
    catch { report.provider_connected=false; }
    report.status_text=await page.locator('#realtimeVoiceStatus').innerText();
    report.warning_text=await page.locator('#realtimeVoiceWarning').innerText();
    report.unmute_enabled=await page.locator('#realtimeVoiceMic').isEnabled();
    report.draft_preserved=await page.locator('#msg').inputValue()==='Unsent synthetic voice draft';
    report.transcript_text=await page.locator('#realtimeVoiceTranscript').innerText();
    need(report.provider_connected && report.unmute_enabled && report.draft_preserved,'native_provider_connection_not_established');
    need(report.page_errors.length===0,'browser_page_error');
    report.result='PASS_PROVIDER_NEGOTIATION_ONLY';
  } catch(e) { report.result='FAIL'; report.failure=e.message; }
  finally {
    if(page)try{if(await page.locator('#realtimeVoiceEnd').isVisible()){const ended=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/voice/realtime/end',{timeout:8000});await page.locator('#realtimeVoiceEnd').click();need((await ended).status()===200,'voice_end_failed');report.cleanup.voice_ended=true;} }catch{report.cleanup.voice_end_error=true;}
    if(context&&sid)try{
      const read=await context.request.get('/api/session?session_id='+encodeURIComponent(sid));
      const body=await read.json();
      const session=body.session||body;
      need(session.title===title,'synthetic_session_ownership_changed');
      need(Array.isArray(session.messages)&&session.messages.length===1&&session.messages[0].content==='Synthetic connection check only. Do not use tools or start tasks.','synthetic_session_changed');
      const deleted=await context.request.post('/api/session/delete',{headers:authHeaders,data:{session_id:sid}});
      need(deleted.status()===200,'synthetic_delete_failed');report.cleanup.synthetic_session_deleted=true;
    }catch{report.cleanup.session_cleanup_error=true;}
    if(context)try{await context.request.post('/api/auth/logout',{headers:authHeaders,data:{}});report.cleanup.auth_logged_out=true;}catch{report.cleanup.logout_error=true;}
    if(browser)await browser.close();
    report.completed_at_utc=new Date().toISOString();
    if(hostVerified)fs.writeFileSync(root+'/qa-release-native-voice-20260909.json',JSON.stringify(report,null,2),{flag:'wx',mode:0o600});
    process.exitCode=report.result==='PASS_PROVIDER_NEGOTIATION_ONLY'&&!Object.keys(report.cleanup).some(k=>k.endsWith('_error'))?0:1;
  }
})();
