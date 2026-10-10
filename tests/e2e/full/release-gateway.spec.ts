import fs from 'node:fs';
import path from 'node:path';
import {test,expect,open,api,session} from './fixtures';
test.use({user:'admin'});
test('gateway enforcement refuses unavailable speech routes and restores normal capability',async({page},info)=>{
 const qa=path.dirname(process.env.QA_SESSIONS!);
 expect(qa).toContain('e2e-state');
 const config=path.join(qa,'home','config.yaml');
 const original=fs.readFileSync(config,'utf8');
 await open(page);await session(page);
 expect((await api(page,'/api/voice/realtime/capability')).body.available).toBe(true);
 try {
  fs.writeFileSync(config,original+'\nmodel_gateway:\n  enforce: true\n');
  await expect.poll(async()=>(await api(page,'/api/voice/realtime/capability')).status).toBe(409);
  for(const engine of ['edge','openai','elevenlabs']){
   // TTS is rate-limited; each test call uses a different signed test user only
   // in backend tests. Browser waits for the normal per-user limit here.
   await page.waitForTimeout(2100);
   const response=await api(page,'/api/tts',{text:'Synthetic local policy check',engine});
   expect(response.status).toBe(409);expect(response.body.code).toBe('gateway_required');
  }
  await page.reload();await expect(page.locator('#msg')).toBeVisible();
  await page.waitForFunction(()=>typeof S!=='undefined' && S.session?.session_id && typeof _loadingSessionId!=='undefined' && _loadingSessionId===null);
  await page.locator('#btnRealtimeVoice').click();
  await expect(page.locator('#toast')).toContainText('Live voice is not available on this platform.');
  await page.screenshot({path:info.outputPath('gateway-speech-unavailable-desktop.png')});
  await page.setViewportSize({width:390,height:844});
  await page.locator('#btnRealtimeVoice').click();
  await expect(page.locator('#toast')).toContainText('Live voice is not available on this platform.');
  await page.screenshot({path:info.outputPath('gateway-speech-unavailable-mobile.png')});
 }finally{fs.writeFileSync(config,original);}
 await expect.poll(async()=>(await api(page,'/api/voice/realtime/capability')).body.available).toBe(true);
});
