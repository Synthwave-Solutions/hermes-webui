// Actual production WebRTC/provider audio conversation; synthetic prerecorded input, no physical microphone.
const fs = require('fs');
const os = require('os');
const cp = require('child_process');
const crypto = require('crypto');
const { chromium } = require('/home/synthwavehq/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const root = '/home/synthwavehq/work/synthpulse';
const base = 'http://127.0.0.1:8787';
const title = 'QA native voice audio ' + crypto.randomUUID();
const wav = root + '/qa-native-audio-' + crypto.randomUUID() + '.wav';
const report = {kind:'actual_provider_browser_audio_conversation', physical_microphone:'NOT_USED_SYNTHETIC_PRERECORDED_INPUT', started_at_utc:new Date().toISOString(), title, requests:[], page_errors:[], cleanup:{}};
let browser, context, page, sid, authHeaders, voiceId;
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
    cp.execFileSync('/usr/bin/ffmpeg',['-hide_banner','-loglevel','error','-f','lavfi','-i',"flite=text='Please answer only cobalt river seven. Do not start a chat or use tools.':voice=slt",'-af','adelay=1000,apad=pad_dur=10','-ar','48000','-ac','1','-c:a','pcm_s16le',wav],{timeout:20000,stdio:'pipe'});
    fs.chmodSync(wav,0o600);
    browser=await chromium.launch({headless:true,executablePath:'/home/synthwavehq/.cloakbrowser/chromium-146.0.7680.177.3/chrome',args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--use-file-for-fake-audio-capture='+wav]});
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
    page.on('response',async r=>{const u=new URL(r.url());if(u.pathname.startsWith('/api/voice/realtime/'))report.requests.push({path:u.pathname,status:r.status()});if(u.pathname==='/api/voice/realtime/call'&&r.status()===200){try{const body=await r.json();if(/^[A-Za-z0-9_-]{1,128}$/.test(body.voice_id||''))voiceId=body.voice_id;}catch{}}});
    await page.goto(base+'/session/'+sid,{waitUntil:'domcontentloaded'});
    await page.locator('#messages').getByText('Synthetic connection check only. Do not use tools or start tasks.',{exact:true}).waitFor({state:'visible',timeout:30000});
    report.synthetic_conversation_loaded=true;
    await page.locator('#msg').fill('Unsent synthetic voice draft');
    await page.locator('#btnRealtimeVoice').click();
    try { await page.locator('#realtimeVoiceStatus').filter({hasText:'Microphone muted'}).waitFor({state:'visible',timeout:45000}); report.provider_connected=true; }
    catch { report.provider_connected=false; }
    report.status_text=await page.locator('#realtimeVoiceStatus').innerText();
    report.warning_present=Boolean(await page.locator('#realtimeVoiceWarning').innerText());
    report.unmute_enabled=await page.locator('#realtimeVoiceMic').isEnabled();
    report.draft_preserved=await page.locator('#msg').inputValue()==='Unsent synthetic voice draft';
    report.transcript_characters=(await page.locator('#realtimeVoiceTranscript').innerText()).length;
    need(report.provider_connected && report.unmute_enabled && report.draft_preserved,'native_provider_connection_not_established');
    need(report.page_errors.length===0,'browser_page_error');
    const userRows=page.locator('#realtimeVoiceTranscript [data-role=user]');
    const assistantRows=page.locator('#realtimeVoiceTranscript [data-role=assistant]');
    const rtpTotals=()=>page.evaluate(async()=>{const stats=await window.synPulseVoice.pc.getStats();const out={received:0,sent:0};for(const r of stats.values())if(r.kind==='audio'){if(r.type==='inbound-rtp')out.received+=r.bytesReceived||0;if(r.type==='outbound-rtp')out.sent+=r.bytesSent||0;}return out;});
    report.audio_turns=[];
    for(let turn=0;turn<2;turn++){
      const before={user:await userRows.count(),assistant:await assistantRows.count(),rtp:await rtpTotals()};
      await page.locator('#realtimeVoiceMic').click();
      await page.waitForFunction(n=>document.querySelectorAll('#realtimeVoiceTranscript [data-role=user]').length>n,before.user,{timeout:55000});
      await page.locator('#realtimeVoiceMic').click();
      await page.waitForFunction(n=>document.querySelectorAll('#realtimeVoiceTranscript [data-role=assistant]').length>n,before.assistant,{timeout:30000});
      await page.locator('#realtimeVoiceStatus').filter({hasText:'Microphone muted'}).waitFor({state:'visible',timeout:30000});
      const after=await rtpTotals();
      const delta={turn:turn+1,received:after.received-before.rtp.received,sent:after.sent-before.rtp.sent,playback_settled:true};
      need(delta.received>0&&delta.sent>0,'turn_audio_transport_not_proven');
      report.audio_turns.push(delta);
    }
    report.first_direct_audio_reply=true;
    report.second_direct_audio_reply=true;
    report.user_caption_count=await userRows.count();
    report.assistant_caption_count=await assistantRows.count();
    report.expected_phrase_reply_count=await assistantRows.filter({hasText:/cobalt river seven/i}).count();
    report.native_task_count=await page.locator('#realtimeVoiceTasks .realtime-voice-task').count();
    report.audio_rtp=await page.evaluate(async()=>{const stats=await window.synPulseVoice.pc.getStats();const rows=[];for(const r of stats.values())if(['inbound-rtp','outbound-rtp'].includes(r.type)&&r.kind==='audio')rows.push({type:r.type,bytesReceived:r.bytesReceived||0,bytesSent:r.bytesSent||0,packetsReceived:r.packetsReceived||0,packetsSent:r.packetsSent||0});return rows;});
    report.draft_preserved=await page.locator('#msg').inputValue()==='Unsent synthetic voice draft';
    need(report.expected_phrase_reply_count>=2 && report.native_task_count===0 && report.draft_preserved,'direct_continuous_audio_reply_not_proven');
    need(report.audio_rtp.some(r=>r.type==='inbound-rtp'&&r.bytesReceived>0)&&report.audio_rtp.some(r=>r.type==='outbound-rtp'&&r.bytesSent>0),'bidirectional_audio_transport_not_proven');
    need(report.page_errors.length===0,'browser_page_error');
    report.result='PASS_PROVIDER_SYNTHETIC_AUDIO_TWO_TURNS';
  } catch(e) { report.result='FAIL'; report.failure=e.message; }
  finally {
    if(page)try{if(await page.locator('#realtimeVoiceEnd').isVisible()){const ended=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/voice/realtime/end',{timeout:8000});await page.locator('#realtimeVoiceEnd').click();need((await ended).status()===200,'voice_end_failed');report.cleanup.voice_ended=true;} }catch{report.cleanup.voice_end_error=true;}
    if(context&&voiceId&&!report.cleanup.voice_ended)try{const end=await context.request.post('/api/voice/realtime/end',{headers:authHeaders,data:{voice_id:voiceId}});need([200,404].includes(end.status()),'voice_fallback_end_failed');report.cleanup.voice_ended=true;delete report.cleanup.voice_end_error;}catch{report.cleanup.voice_end_error=true;}
    if(context&&sid)try{
      const read=await context.request.get('/api/session?session_id='+encodeURIComponent(sid));
      const body=await read.json();
      const session=body.session||body;
      need(session.title===title,'synthetic_session_ownership_changed');
      need(Array.isArray(session.messages)&&session.messages.length===1&&session.messages[0].content==='Synthetic connection check only. Do not use tools or start tasks.','synthetic_session_changed');
      const deleted=await context.request.post('/api/session/delete',{headers:authHeaders,data:{session_id:sid}});
      need(deleted.status()===200,'synthetic_delete_failed');report.cleanup.synthetic_session_deleted=true;
    }catch{report.cleanup.session_cleanup_error=true;}
    if(context)try{need((await context.request.post('/api/auth/logout',{headers:authHeaders,data:{}})).status()===200,'logout_failed');report.cleanup.auth_logged_out=true;}catch{report.cleanup.logout_error=true;}
    if(browser)await browser.close();
    if(hostVerified&&fs.existsSync(wav)){fs.unlinkSync(wav);report.cleanup.synthetic_audio_deleted=true;}
    report.completed_at_utc=new Date().toISOString();
    if(hostVerified)fs.writeFileSync(root+'/qa-release-native-audio-20260909.json',JSON.stringify(report,null,2),{flag:'wx',mode:0o600});
    process.exitCode=report.result==='PASS_PROVIDER_SYNTHETIC_AUDIO_TWO_TURNS'&&!Object.keys(report.cleanup).some(k=>k.endsWith('_error'))?0:1;
  }
})();
