import type {Route} from '@playwright/test';
import {test,expect,open,session,api} from './fixtures';
declare const S:any;
test('SUPPLEMENT DRAFT RESTORE actual typing and clearing beat late metadata and deliberate prompt reinsertion stays exact',async({page},info)=>{
  test.setTimeout(60000);await open(page);const sid=await session(page);
  const prompt='QA controlled saved prompt typed-clear\nSecond line';
  await page.locator('#msg').fill(prompt);await page.locator('#btnSavedPrompts').click();
  await page.locator('.saved-prompt-save-btn').click();await expect(page.locator('#savedPromptsPopup')).toBeHidden();
  await expect.poll(async()=>(await api(page,'/api/session?session_id='+sid)).body.session.composer_draft?.text).toBe(prompt);
  let release!:()=>void,entered!:()=>void,held=false;
  const released=new Promise<void>(r=>release=r),waiting=new Promise<void>(r=>entered=r);
  const hold=async(route:Route)=>{
   const u=new URL(route.request().url());
   if(!held&&u.searchParams.get('session_id')===sid&&u.searchParams.get('include')==='journal_snapshot'){
    held=true;const response=await route.fetch();expect(response.status()).toBe(200);
    expect((await response.json()).session.composer_draft.text).toBe(prompt);
    entered();await released;await route.fulfill({response});return;
   }await route.continue();
  };
  await page.addInitScript(()=>{
   (window as any).__draftInputEvents=[];
   document.addEventListener('input',e=>{if((e.target as Element).id==='msg') (window as any).__draftInputEvents.push({value:(e.target as HTMLTextAreaElement).value,trusted:e.isTrusted});},true);
  });
  await page.route('**/api/session?**',hold);
  try{
   await page.reload();await waiting;await expect(page.locator('#msg')).toBeVisible();
   const before=await page.locator('#msg').inputValue();
   await page.locator('#msg').fill('Temporary replacement explicitly cleared by user');
   await page.locator('#msg').fill('');await expect(page.locator('#msg')).toHaveValue('');
   const events=await page.evaluate(()=>(window as any).__draftInputEvents);
   expect(events.map((e:any)=>e.value)).toEqual(['Temporary replacement explicitly cleared by user','']);
   expect(events.every((e:any)=>e.trusted===true)).toBe(true);
   release();await page.waitForFunction(()=>S._bootReady===true);
   const after=await page.locator('#msg').inputValue();
   await expect(page.locator('#msg')).toHaveValue('');
   await expect.poll(async()=>(await api(page,'/api/session?session_id='+sid)).body.session.composer_draft?.text).toBe('');
   await page.locator('#btnSavedPrompts').click();
   const row=page.locator('.saved-prompt-row').filter({hasText:'QA controlled saved prompt typed-clear'});
   await expect(row).toHaveCount(1);await row.click();
   const final=await page.locator('#msg').inputValue();
   await info.attach('controlled-draft-restore-order',{body:JSON.stringify({sid,before,events,after,final}),contentType:'application/json'});
   await expect(page.locator('#msg')).toHaveValue(prompt+'\n\n');
   // A second intentional insertion is still valid; do not deduplicate text.
   await page.locator('#btnSavedPrompts').click();await row.click();
   const repeated=prompt+'\n\n'+prompt+'\n\n';
   await expect(page.locator('#msg')).toHaveValue(repeated);
   await expect.poll(async()=>(await api(page,'/api/session?session_id='+sid)).body.session.composer_draft?.text).toBe(repeated);
   await page.reload();await expect(page.locator('#msg')).toHaveValue(repeated);
  }finally{release();await page.unroute('**/api/session?**',hold);}
 });
