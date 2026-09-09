import type {Route} from '@playwright/test';
import {test,expect,open,session,api,auth} from './fixtures';
declare const S:any;

for (const outcome of ['available','inaccessible'] as const) {
 test('SUPPLEMENT SESSION ACTIVATION newer New Chat survives a delayed '+outcome+' saved-session restore',async({page,context},info)=>{
  test.setTimeout(60000);await open(page);const oldSid=await session(page);
  await page.locator('#msg').fill('QA_ACTIVATION_OLD_HISTORY');await page.locator('#btnSend').click();
  await expect.poll(async()=>(await api(page,'/api/session/status?session_id='+oldSid)).body.agent_running).toBe(false);
  await expect(page.locator('#messages')).toContainText('QA_ACTIVATION_OLD_HISTORY');
  await expect.poll(async()=>(await api(page,'/api/session?session_id='+oldSid)).body.session.messages.length).toBeGreaterThanOrEqual(2);
  if(outcome==='inaccessible') await context.addCookies([{name:auth.cookie_name,value:auth.cookies.bob,url:auth.base_url,httpOnly:true,sameSite:'Lax'}]);
  let release!:()=>void,entered!:()=>void,held=false,heldStatus=0;
  const released=new Promise<void>(resolve=>{release=resolve;});const waiting=new Promise<void>(resolve=>{entered=resolve;});
  const creations:string[]=[];
  page.on('response',async response=>{
   if(new URL(response.url()).pathname==='/api/session/new'&&response.request().method()==='POST'&&response.status()===200){
    try{creations.push((await response.json()).session.session_id);}catch{}
   }
  });
  const holdRestore=async(route:Route)=>{
   const url=new URL(route.request().url());
   const phaseMatches=outcome==='inaccessible'?url.searchParams.get('include')==='journal_snapshot':!url.searchParams.has('include');
   if(!held&&phaseMatches&&url.pathname==='/api/session'&&url.searchParams.get('session_id')===oldSid&&url.searchParams.get('messages')==='0'){
    held=true;const response=await route.fetch();heldStatus=response.status();entered();
    await released;await route.fulfill({response});return;
   }
   await route.continue();
  };
  await page.route('**/api/session?**',holdRestore);
  try{
   await page.goto('/');await waiting;await expect(page.locator('#msg')).toBeVisible();
   const created=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/session/new'&&r.request().method()==='POST');
   await page.locator('#btnNewChat').click();const response=await created;expect(response.status()).toBe(200);
   const next=(await response.json()).session;expect(next.session_id).not.toBe(oldSid);
   await expect(page).toHaveURL(new RegExp('/session/'+next.session_id+'$'));
   await page.locator('#msg').fill('KEEP_NEW_CHAT_DRAFT');release();
   await page.waitForFunction(()=>S._bootReady===true);
   await expect(page).toHaveURL(new RegExp('/session/'+next.session_id+'$'));
   await expect(page.locator('#msg')).toHaveValue('KEEP_NEW_CHAT_DRAFT');
   await expect(page.locator('#msgInner')).not.toContainText('Session not available in web UI.');
   expect(await page.evaluate(()=>localStorage.getItem('hermes-webui-session'))).toBe(next.session_id);
   const current=await api(page,'/api/session?session_id='+next.session_id);
   expect(current.status).toBe(200);expect(current.body.session.session_id).toBe(next.session_id);
   expect(current.body.session.owner_email).toBe(outcome==='inaccessible'?'bob@example.test':'admin@example.test');
   await expect.poll(()=>creations).toEqual([next.session_id]);
   expect(heldStatus).toBe(outcome==='inaccessible'?404:200);
   await info.attach('actual-saved-restore-versus-new-chat',{body:JSON.stringify({old_session_id:oldSid,new_session_id:next.session_id,delayed_status:heldStatus,created:creations}),contentType:'application/json'});
  }finally{release();await page.unroute('**/api/session?**',holdRestore);}
 });
}

for (const destination of ['current','other'] as const) {
 test('SUPPLEMENT SESSION ACTIVATION a later '+destination+' sidebar choice survives a delayed New Chat response',async({page},info)=>{
  test.setTimeout(60000);await open(page);const oldSid=await session(page);
  const sendHistory=async(marker:string)=>{
   await page.locator('#msg').fill(marker);await page.locator('#btnSend').click();
   await expect(page.locator('#messages')).toContainText(marker);
   const sid=new URL(page.url()).pathname.split('/').pop()!;
   await expect.poll(async()=>(await api(page,'/api/session?session_id='+sid)).body.session.messages.length).toBeGreaterThanOrEqual(2);
   await expect.poll(async()=>(await api(page,'/api/session/status?session_id='+sid)).body.agent_running).toBe(false);
  };
  await sendHistory('QA_ACTIVATION_CURRENT_HISTORY');
  let targetSid=oldSid;
  if(destination==='other'){
   const created=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/session/new'&&r.request().method()==='POST');
   await page.locator('#btnNewChat').click();const createdResponse=await created;expect(createdResponse.status()).toBe(200);
   targetSid=(await createdResponse.json()).session.session_id;expect(targetSid).not.toBe(oldSid);
   await expect(page).toHaveURL(new RegExp('/session/'+targetSid+'$'));
   await sendHistory('QA_ACTIVATION_OTHER_HISTORY');
   await page.locator('.session-item[data-sid="'+oldSid+'"]').click();
   await expect(page).toHaveURL(new RegExp('/session/'+oldSid+'$'));
  }
  const targetMarker=destination==='current'?'QA_ACTIVATION_CURRENT_HISTORY':'QA_ACTIVATION_OTHER_HISTORY';
  let release!:()=>void,entered!:()=>void,createdSid='',held=false;
  const released=new Promise<void>(resolve=>{release=resolve;});const waiting=new Promise<void>(resolve=>{entered=resolve;});
  const holdCreation=async(route:Route)=>{
   if(!held&&route.request().method()==='POST'){
    held=true;const response=await route.fetch();expect(response.status()).toBe(200);
    createdSid=(await response.json()).session.session_id;entered();await released;await route.fulfill({response});return;
   }
   await route.continue();
  };
  await page.route('**/api/session/new',holdCreation);
  try{
   await page.locator('#btnNewChat').click();await waiting;
   expect(createdSid).not.toBe(oldSid);expect(createdSid).not.toBe(targetSid);
   await expect(page.locator('#btnNewChat')).toBeDisabled();
   await page.locator('.session-item[data-sid="'+targetSid+'"]').click();
   await expect(page).toHaveURL(new RegExp('/session/'+targetSid+'$'));
   await expect(page.locator('#messages')).toContainText(targetMarker);
   await page.locator('#msg').fill('KEEP_SELECTED_CHAT_DRAFT');release();
   await expect(page.locator('#btnNewChat')).toBeEnabled();
   await expect(page).toHaveURL(new RegExp('/session/'+targetSid+'$'));
   await expect(page.locator('#messages')).toContainText(targetMarker);
   await expect(page.locator('#msg')).toHaveValue('KEEP_SELECTED_CHAT_DRAFT');
   expect(await page.evaluate(()=>localStorage.getItem('hermes-webui-session'))).toBe(targetSid);
   const created=await api(page,'/api/session?session_id='+createdSid);
   expect(created.status).toBe(200);expect(created.body.session.owner_email).toBe('admin@example.test');
   expect(created.body.session.messages).toEqual([]);
   await info.attach('actual-create-versus-later-sidebar-choice',{body:JSON.stringify({old_session_id:oldSid,selected_session_id:targetSid,created_session_id:createdSid,created_record_retained:true}),contentType:'application/json'});
  }finally{release();await page.unroute('**/api/session/new',holdCreation);}
 });
}
