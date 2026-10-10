import {test,expect,open,api} from './fixtures';
test.use({user:'admin'});
async function ready(page:any,sid?:string){await page.waitForFunction((target:any)=>typeof S!=='undefined'&&S._bootReady&&_loadingSessionId===null&&(!target||S.session?.session_id===target),sid);}
async function normal(page:any){const r=await api(page,'/api/session/new',{profile:'default',chat_mode:'normal',bot_participants:['default'],enabled_toolsets:['none']});expect(r.status).toBe(200);return r.body.session.session_id;}
test('early Send preserves the draft and restored normal conversation',async({page})=>{
 await open(page);await ready(page);const sid=await normal(page);
 let release!:()=>void;const gate=new Promise<void>(r=>release=r);let held=false;const writes:any[]=[];
 page.on('request',r=>{if(r.method()==='POST')writes.push({path:new URL(r.url()).pathname,body:r.postDataJSON()});});
 await page.route('**/api/session?**',async r=>{if(new URL(r.request().url()).searchParams.get('session_id')===sid){held=true;await gate;}await r.continue();});
 try {
  await page.goto('/session/'+sid,{waitUntil:'domcontentloaded'});await expect.poll(()=>held).toBe(true);
  await page.locator('#msg').fill('QA preserved hydration draft');await page.locator('#btnSend').click();
  await expect(page.locator('#toast')).toContainText('Your conversation is still loading');
  expect(writes.filter(x=>['/api/session/new','/api/chat/start'].includes(x.path))).toEqual([]);
  release();await ready(page,sid);await expect(page.locator('#msg')).toHaveValue('QA preserved hydration draft');
  const sent=page.waitForRequest(r=>new URL(r.url()).pathname==='/api/chat/start');
  await page.locator('#btnSend').click();expect((await sent).postDataJSON().session_id).toBe(sid);
  const current=(await api(page,'/api/session?session_id='+sid)).body.session;
  expect(current.chat_mode).toBe('normal');expect(current.bot_participants).toEqual(['default']);
  expect(writes.filter(x=>x.path==='/api/session/new')).toEqual([]);
 }finally{release();}
});
test('Memory reloads the active context when chat hydration invalidates its pending read',async({page})=>{
 await open(page);await ready(page);const first=await normal(page),second=await normal(page);
 await page.goto('/session/'+first);await ready(page,first);
 let release!:()=>void;const gate=new Promise<void>(r=>release=r);let held=false;const contexts:string[]=[];
 await page.route('**/api/memory?**',async r=>{contexts.push(new URL(r.request().url()).searchParams.get('session_id')||'');if(!held){held=true;await gate;}await r.continue();});
 try {
  await page.locator('.rail-btn[data-panel="memory"]').click();await expect.poll(()=>held).toBe(true);
  await page.evaluate(sid=>loadSession(sid),second);release();
  await expect.poll(()=>contexts.includes(second)).toBe(true);
  await expect(page.locator('#memoryPanel .side-menu-item').first()).toBeVisible();
  await page.waitForFunction(()=>_memoryLoadedContext===_memoryContext());
 }finally{release();}
});
