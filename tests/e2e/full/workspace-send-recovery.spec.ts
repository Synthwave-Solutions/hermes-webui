import fs from 'node:fs';
import path from 'node:path';
import {test, expect, open, api, auth} from './fixtures';
import type {Page, Browser} from '@playwright/test';
declare const S: any;
declare const _sendInProgress:boolean;
test.use({user:'manualapprove'});
async function setup(page:Page,browser:Browser){
 const context=await browser.newContext({baseURL:auth.base_url});
 await context.route('**/*',r=>['127.0.0.1','localhost','[::1]'].includes(new URL(r.request().url()).hostname)?r.continue():r.abort());
 await context.addCookies([{name:auth.cookie_name,value:auth.cookies.admin,url:auth.base_url,httpOnly:true,sameSite:'Lax'}]);
 const admin=await context.newPage();await open(admin);
 const root=path.join(auth.workspace,'qa-retained-'+Date.now());fs.mkdirSync(root);
 const name=path.basename(root);
 expect((await api(admin,'/api/workspaces/add',{name,path:root})).status).toBe(200);
 expect((await api(admin,'/api/workspaces/assign',{path:root,owner_email:'admin@example.test',members:['manualapprove@example.test']})).status).toBe(200);
 await open(page);
 const created=await api(page,'/api/session/new',{workspace:root,worktree:false});expect(created.status).toBe(200);
 const sid=created.body.session.session_id;await page.goto('/session/'+sid);
 await expect(page.locator('#msg')).toBeVisible();
 await page.waitForFunction(sid=>S.session?.session_id===sid&&!S.busy,sid);
 return{root,name,sid,admin,context,async revoke(){expect((await api(admin,'/api/workspaces/assign',{path:root,owner_email:'admin@example.test',members:[]})).status).toBe(200);},async cleanup(){expect((await api(admin,'/api/workspaces/remove',{path:root})).status).toBe(200);await context.close();}};
}
async function send(page:Page,prompt:string){await page.locator('#msg').fill(prompt);await page.locator('#btnSend').click();await expect.poll(()=>page.locator('#messages').innerText(),{intervals:[100],timeout:10000}).toContain('QA_REPLY: '+prompt);await page.waitForFunction(()=>!S.busy);}

test('WORKSPACE RECOVERY retained chat keeps history draft and attachments until explicit authorized choice and manual resend',async({page,browser},info)=>{
 const f=await setup(page,browser);
 try{
  await send(page,'QA_RETAINED_HISTORY');
  const before=(await api(page,'/api/session?session_id='+f.sid)).body.session.messages;
  await f.revoke();
  const history=await api(page,'/api/session?session_id='+f.sid);expect(history.status).toBe(200);expect(history.body.session.messages).toEqual(before);
  const requests:any[]=[];page.on('request',r=>{if(new URL(r.url()).pathname==='/api/chat/start'&&r.method()==='POST')requests.push(r.postDataJSON());});
  await page.locator('#fileInput').setInputFiles({name:'qa-retained.txt',mimeType:'text/plain',buffer:Buffer.from('Synthetic recovery attachment')});
  await page.locator('#msg').fill('QA_RETAINED_RETRY');
  const refused=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/chat/start');await page.locator('#btnSend').click();expect((await refused).status()).toBe(403);
  const notice=page.locator('#workspaceRecoveryNotice');await expect(notice).toContainText('Choose an available workspace');
  await expect(page.locator('#msg')).toHaveValue('QA_RETAINED_RETRY');await expect(page.locator('#attachTray')).toContainText('qa-retained.txt');
  await expect(page.locator('#messages')).toContainText('QA_REPLY: QA_RETAINED_HISTORY');expect(requests).toHaveLength(1);
  // Recovery keeps this conversation even when ordinary switching prefers a new chat.
  await page.evaluate(()=>{(window as any)._newChatOnWorkspaceSwitch=true;(window as any)._composerControlVisibility={...(window as any)._composerControlVisibility,hide_composer_workspace:true};(window as any)._applyComposerFooterVisibilitySettings();});
  await expect(page.locator('#composerWorkspaceChip')).toBeHidden();
  const catalog=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/workspaces');
  await notice.getByRole('button',{name:'Choose workspace',exact:true}).click();const choices=(await (await catalog).json()).workspaces;
  const dropdown=page.locator('#composerWsDropdown');await expect(dropdown).toBeVisible();
  expect(await dropdown.locator('.ws-opt[data-path]').evaluateAll(nodes=>nodes.map(n=>(n as HTMLElement).dataset.path).sort())).toEqual(choices.map((w:any)=>w.path).sort());
  await expect(dropdown.locator('.ws-opt[data-path]').filter({hasText:f.name})).toHaveCount(0);await expect(dropdown.locator('.ws-opt-action')).toHaveCount(0);
  const changed=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/session/update'&&r.request().method()==='POST');
  await dropdown.locator('.ws-opt[data-path]').filter({has:page.getByText(auth.workspace,{exact:true})}).click();const response=await changed;expect(response.status()).toBe(200);expect(response.request().postDataJSON()).toMatchObject({session_id:f.sid,workspace:auth.workspace});
  await expect(notice).toBeHidden();await expect(page.locator('#msg')).toHaveValue('QA_RETAINED_RETRY');await expect(page.locator('#attachTray')).toContainText('qa-retained.txt');expect(requests).toHaveLength(1);
  const retained=await api(page,'/api/session?session_id='+f.sid);expect(retained.body.session.messages).toEqual(before);expect(retained.body.session.workspace).toBe(auth.workspace);
  await page.locator('#msg').fill('QA_RETAINED_RETRY_EDITED');await page.locator('#btnSend').click();await expect.poll(()=>page.locator('#messages').innerText(),{intervals:[100],timeout:10000}).toContain('QA_REPLY: QA_RETAINED_RETRY_EDITED');
  expect(requests).toHaveLength(2);expect(requests[1].attachments).toHaveLength(1);
  const saved=(await api(page,'/api/session?session_id='+f.sid)).body.session.messages;expect(saved.slice(0,before.length)).toEqual(before);expect(saved.filter((m:any)=>m.role==='user'&&m.content.includes('QA_RETAINED_RETRY_EDITED'))).toHaveLength(1);expect(saved.some((m:any)=>m.role==='user'&&m.content==='QA_RETAINED_RETRY')).toBe(false);
  expect((await api(page,'/api/session/update',{session_id:f.sid,workspace:f.root})).status).toBe(403);
  await info.attach('workspace-recovery-dispatches',{body:JSON.stringify({attempted:requests.length,auto_resends:0,history_rows:before.length,authorized_catalog_count:choices.length}),contentType:'application/json'});
 }finally{await f.cleanup();}
});

function barrier(){let resolve!:()=>void;const promise=new Promise<void>(r=>resolve=r);return{promise,resolve};}
test('WORKSPACE RECOVERY late refusal and catalog cannot replace another chat or its draft',async({page,browser},info)=>{
 const f=await setup(page,browser);const arrived=barrier(),release=barrier(),delivered=barrier();
 try{
  await send(page,'QA_OLD_CONTEXT');await f.revoke();
  await page.route('**/api/chat/start',async route=>{const response=await route.fetch();expect(response.status()).toBe(403);arrived.resolve();await release.promise;await route.fulfill({response});delivered.resolve();},{times:1});
  await page.locator('#msg').fill('QA_OLD_DENIED_DRAFT');await page.locator('#btnSend').click();await arrived.promise;
  await page.locator('#btnNewChat').click();await expect.poll(()=>page.url()).not.toContain('/session/'+f.sid);
  const nextSid=await page.evaluate(()=>S.session.session_id);await page.locator('#msg').fill('QA_NEW_CONTEXT_DRAFT');release.resolve();await delivered.promise;
  await page.waitForFunction(()=>!_sendInProgress);
  await expect(page.locator('#workspaceRecoveryNotice')).toBeHidden();await expect(page.locator('#msg')).toHaveValue('QA_NEW_CONTEXT_DRAFT');expect(await page.evaluate(()=>S.session.session_id)).toBe(nextSid);await expect(page.locator('#messages')).not.toContainText('Workspace membership');
  await send(page,'QA_SUCCESSOR_HISTORY');
  await page.locator('#msg').fill('QA_NEW_CONTEXT_DRAFT');
  // Return through the ordinary sidebar and trigger the real refusal again.
  await page.locator('.session-item[data-sid="'+f.sid+'"]').click();await page.waitForFunction(sid=>S.session?.session_id===sid,f.sid);
  await page.locator('#msg').fill('QA_OLD_SECOND_ATTEMPT');const failed=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/chat/start');await page.locator('#btnSend').click();expect((await failed).status()).toBe(403);
  const notice=page.locator('#workspaceRecoveryNotice');await expect(notice).toBeVisible();
  const catalogArrived=barrier(),catalogRelease=barrier(),catalogDone=barrier();
  await page.route('**/api/workspaces',async route=>{const response=await route.fetch();expect(response.status()).toBe(200);catalogArrived.resolve();await catalogRelease.promise;await route.fulfill({response});catalogDone.resolve();},{times:1});
  const updates:any[]=[];page.on('request',r=>{if(new URL(r.url()).pathname==='/api/session/update'&&r.method()==='POST')updates.push(r.postDataJSON());});
  await notice.getByRole('button',{name:'Choose workspace',exact:true}).click();await catalogArrived.promise;
  await page.locator('.session-item[data-sid="'+nextSid+'"]').click();await page.waitForFunction(sid=>S.session?.session_id===sid,nextSid);await page.locator('#msg').fill('QA_SUCCESSOR_STILL_EDITABLE');
  catalogRelease.resolve();await catalogDone.promise;await expect(page.locator('#composerWsDropdown')).toBeHidden();await expect(notice).toBeHidden();await expect(page.locator('#msg')).toHaveValue('QA_SUCCESSOR_STILL_EDITABLE');
  expect(updates.filter(r=>r.workspace)).toHaveLength(0);expect((await api(page,'/api/session?session_id='+f.sid)).body.session.workspace).toBe(f.root);
  await info.attach('workspace-recovery-stale-context',{body:JSON.stringify({held_actual_refusal:true,held_actual_catalog:true,workspace_updates:0,successor_draft_preserved:true}),contentType:'application/json'});
 }finally{release.resolve();await f.cleanup();}
});

test('WORKSPACE RECOVERY unrelated chat permission denial keeps ordinary error without workspace action',async({page,browser})=>{
 const f=await setup(page,browser);let original:any;
 const update=async(entry:any)=>{const state=(await api(f.admin,'/api/governance/users')).body;return f.admin.evaluate(async({entry,etag})=>{const r=await fetch('/api/governance/users/update',{method:'POST',headers:{'Content-Type':'application/json','If-Match':etag},body:JSON.stringify({email:'manualapprove@example.test',entry})});return r.status;},{entry,etag:state.etag});};
 try{
  const state=(await api(f.admin,'/api/governance/users')).body;original=state.users['manualapprove@example.test'];
  expect(await update({...original,deny:{...(original.deny||{}),permissions:['chat:use']}})).toBe(200);
  await page.locator('#msg').fill('QA_UNRELATED_PERMISSION');const denied=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/chat/start');await page.locator('#btnSend').click();const response=await denied;expect(response.status()).toBe(403);expect((await response.json()).error).toBe('forbidden');
  await expect(page.locator('#messages')).toContainText('Error: forbidden');await expect(page.locator('#workspaceRecoveryNotice')).toBeHidden();await expect(page.locator('#msg')).toHaveValue('QA_UNRELATED_PERMISSION');
 }finally{if(original)expect(await update(original)).toBe(200);await f.cleanup();}
});
