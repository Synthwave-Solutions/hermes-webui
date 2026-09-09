import type {Route} from '@playwright/test';
import {test,expect,open,session,api} from './fixtures';
declare const S:any,LIVE_STREAMS:any;
declare function attachLiveStream(sid:string,streamId:string,uploaded:any[],options:any):void;

test('SUPPLEMENT STREAM OWNERSHIP late old reconnect status cannot replace an interrupted successor',async({page},info)=>{
  await open(page);const sid=await session(page);
  const firstStart=page.waitForResponse(r=>r.url().endsWith('/api/chat/start')&&r.request().method()==='POST');
  await page.locator('#msg').fill('QA_SLOW_RESPONSE');await page.locator('#btnSend').click();
  const old=(await (await firstStart).json()).stream_id;
  await page.waitForFunction(({sid,old})=>LIVE_STREAMS[sid]?.streamId===old&&LIVE_STREAMS[sid]?.source.readyState===EventSource.OPEN,{sid,old});
  let releaseStatus!:()=>void,statusEntered!:()=>void,releaseNew!:()=>void,newEntered!:()=>void;
  const statusGate=new Promise<void>(r=>releaseStatus=r),statusWaiting=new Promise<void>(r=>statusEntered=r);
  const newGate=new Promise<void>(r=>releaseNew=r),newWaiting=new Promise<void>(r=>newEntered=r);
  let heldStatus=false,heldNew=false,newId='';const streams:string[]=[];
  page.on('request',request=>{const u=new URL(request.url());if(u.pathname==='/api/chat/stream')streams.push(u.searchParams.get('stream_id')||'');});
  const holdStatus=async(route:Route)=>{
    const u=new URL(route.request().url());
    if(!heldStatus&&u.searchParams.get('stream_id')===old){
      heldStatus=true;const response=await route.fetch();expect(response.status()).toBe(200);
      expect((await response.json()).active).toBe(true);statusEntered();await statusGate;await route.fulfill({response});return;
    }await route.continue();
  };
  const holdNew=async(route:Route)=>{
    const id=new URL(route.request().url()).searchParams.get('stream_id');
    if(id&&id!==old&&!heldNew){heldNew=true;newId=id;newEntered();await newGate;}
    await route.continue();
  };
  await page.route('**/api/chat/stream/status?**',holdStatus);
  await page.route('**/api/chat/stream?**',holdNew);
  try{
    // Controlled transport recovery overlap: all replies remain real backend
    // responses. Only the first old-stream status response is delayed.
    await page.evaluate(({sid,old})=>{LIVE_STREAMS[sid].source.close();attachLiveStream(sid,old,[],{reconnecting:true});},{sid,old});
    await statusWaiting;
    await page.evaluate(({sid,old})=>attachLiveStream(sid,old,[],{reconnecting:true}),{sid,old});
    await page.waitForFunction(({sid,old})=>LIVE_STREAMS[sid]?.streamId===old&&LIVE_STREAMS[sid]?.source.readyState===EventSource.OPEN,{sid,old});
    await page.locator('#msg').fill('/interrupt QA_RECONNECT_SUCCESSOR');await page.locator('#btnSend').click();
    await newWaiting;expect(newId).not.toBe(old);const before=streams.length;
    releaseStatus();releaseNew();
    await expect(page.locator('#messages')).toContainText('QA_REPLY: QA_RECONNECT_SUCCESSOR',{timeout:30000});
    const saved=(await api(page,'/api/session?session_id='+sid)).body.session;
    const answers=saved.messages.filter((m:any)=>m.role==='assistant').map((m:any)=>String(m.content||''));
    expect(answers.filter((s:string)=>s.includes('QA_REPLY: QA_RECONNECT_SUCCESSOR'))).toHaveLength(1);
    expect(answers.join('\n')).not.toContain('QA_REPLY: QA_SLOW_RESPONSE');
    expect(streams.slice(before)).not.toContain(old);
    await expect(page.locator('#btnSend')).not.toHaveAttribute('aria-label','Stop generation');
    await info.attach('held-real-reconnect-status',{body:JSON.stringify({sid,old,newId,streams,before,answers}),contentType:'application/json'});
    await page.reload();await expect(page.locator('#messages')).toContainText('QA_REPLY: QA_RECONNECT_SUCCESSOR');
  }finally{releaseStatus();releaseNew();await page.unroute('**/api/chat/stream/status?**',holdStatus);await page.unroute('**/api/chat/stream?**',holdNew);}
});
