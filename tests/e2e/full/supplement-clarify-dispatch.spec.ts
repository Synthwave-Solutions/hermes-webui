import fs from 'node:fs';
import path from 'node:path';
import type {Page} from '@playwright/test';
import {test, expect, open, api, auth, session, capture} from './fixtures';

function providerRows(){
 const file=path.join(path.dirname(auth.workspace),'provider-evidence.jsonl');
 return fs.existsSync(file)?fs.readFileSync(file,'utf8').trim().split('\n').filter(Boolean).map(line=>JSON.parse(line)):[];
}
async function pending(page:Page,sid:string){
 const r=await api(page,'/api/clarify/pending?session_id='+sid);expect(r.status).toBe(200);return r.body.pending;
}
async function send(page:Page,text:string){await page.locator('#msg').fill(text);await page.locator('#btnSend').click();}
async function request(page:Page,url:string,method:string,data:any){
 return page.evaluate(async({url,method,data})=>{const r=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});return{status:r.status,body:await r.json()};},{url,method,data});
}

for(const first of ['other','choice'])test('SUPPLEMENT CLARIFY DISPATCH '+first+' clarification collapses answers and resumes once while stale replies cannot consume next question',async({page,browser},info)=>{
 test.setTimeout(90_000);await open(page);const sid=await session(page);
 expect((await api(page,'/api/session/toolsets',{session_id:sid,toolsets:['clarify']})).status).toBe(200);
 const marker=first+'-'+Date.now();const posts:any[]=[];
 page.on('request',r=>{if(new URL(r.url()).pathname==='/api/clarify/respond')posts.push(r.postDataJSON());});
 await send(page,'QA_CLARIFY_FLOW|'+marker);
 await expect(page.locator('#clarifyCard')).toBeVisible({timeout:30_000});
 await expect(page.locator('#clarifyQuestion')).toHaveText('QA clarification choice '+marker);
 const initial=await pending(page,sid);expect(initial.clarify_id).toBeTruthy();
 await page.locator('#clarifyCollapse').click();await expect(page.locator('#clarifyCollapse')).toHaveAttribute('aria-expanded','false');
 await expect(page.locator('#clarifyInput')).toBeHidden();await page.locator('#clarifyCollapse').click();await expect(page.locator('#clarifyInput')).toBeVisible();
 const firstAnswer=first==='other'?'Synthetic alternative '+marker:'Alpha';
 const accepted=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/clarify/respond'&&r.request().postDataJSON().clarify_id===initial.clarify_id);
 if(first==='other'){
  await page.locator('#clarifyChoices [data-choice="other"]').click();await expect(page.locator('#clarifyInput')).toBeFocused();
  await page.locator('#clarifyInput').fill(firstAnswer);await page.locator('#clarifySubmit').dblclick({delay:20});
 }else await page.locator('#clarifyChoices .clarify-choice').filter({hasText:'Alpha'}).click();
 expect((await accepted).status()).toBe(200);
 await expect(page.locator('#clarifyQuestion')).toHaveText('QA clarification follow-up '+marker,{timeout:30_000});
 const second=await pending(page,sid);expect(second.clarify_id).toBeTruthy();expect(second.clarify_id).not.toBe(initial.clarify_id);
 expect(posts.filter(p=>p.clarify_id===initial.clarify_id)).toHaveLength(1);
 const stale=await api(page,'/api/clarify/respond',{session_id:sid,clarify_id:initial.clarify_id,response:'STALE_MUST_NOT_RESUME'});
 expect(stale.status).toBe(409);expect(stale.body).toMatchObject({ok:false,stale:true});
 expect((await pending(page,sid)).clarify_id).toBe(second.clarify_id);
 const deny=await browser.newContext({baseURL:auth.base_url});
 try{await deny.addCookies([{name:auth.cookie_name,value:auth.cookies.denied,url:auth.base_url,httpOnly:true,sameSite:'Lax'}]);
  expect((await deny.request.post('/api/clarify/respond',{data:{session_id:sid,clarify_id:second.clarify_id,response:'FORBIDDEN'}})).status()).toBe(403);
 }finally{await deny.close();}
 const followup='Synthetic follow-up '+marker;
 await page.locator('#clarifyInput').fill(followup);await page.locator('#clarifyInput').press('Enter');
 await expect(page.locator('#messages')).toContainText('QA_CLARIFY_COMPLETED:'+marker,{timeout:30_000});
 await expect.poll(async()=>Boolean((await api(page,'/api/session/status?session_id='+sid)).body.agent_running)).toBe(false);
 expect(await pending(page,sid)).toBeNull();
 const records=providerRows().filter(row=>row.clarify_marker===marker);
 expect(records.map(row=>row.clarify_phase)).toEqual([0,1,2]);
 expect(records[2].clarify_answers.map((result:any)=>result.responses[0].user_response)).toEqual([firstAnswer,followup]);
 expect(JSON.stringify(records)).not.toContain('STALE_MUST_NOT_RESUME');expect(JSON.stringify(records)).not.toContain('FORBIDDEN');
 const saved=await api(page,'/api/session?session_id='+sid);expect(saved.status).toBe(200);
 expect(JSON.stringify(saved.body)).toContain('QA_CLARIFY_COMPLETED:'+marker);
 await page.reload();await expect(page.locator('#clarifyCard')).toBeHidden();await expect(page.locator('#messages')).toContainText(followup);
 await info.attach('clarification-real-provider-resumptions',{body:JSON.stringify({marker,records,initial_id:initial.clarify_id,second_id:second.clarify_id}),contentType:'application/json'});
});

const preview=(page:Page)=>page.locator('#kanbanTaskPreview');
const card=(page:Page,id:string)=>page.locator('#kanbanBoard .kanban-card[data-kanban-task-id="'+id+'"]');
async function detail(page:Page,id:string,board:string){const r=await api(page,'/api/kanban/tasks/'+id+'?board='+board);expect(r.status).toBe(200);return r.body;}
async function createBoard(page:Page,name:string){
 await page.locator('#btnKanbanCreateBoard').click();await page.locator('#kanbanBoardModalName').fill(name);
 const slug='qa-dispatch-'+Date.now();await page.locator('#kanbanBoardModalSlugInput').fill(slug);
 const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/boards'&&r.request().method()==='POST');
 await page.locator('#kanbanBoardModalSubmit').click();expect((await response).status()).toBe(200);await expect(page.locator('#kanbanBoardSwitcherName')).toHaveText(name);return slug;
}
async function createTask(page:Page,title:string,status:string,assignee='',body='Synthetic local QA task.'){
 await page.locator('#kanbanNewTaskBtn').click();await expect(page.locator('#kanbanTaskModalTitleInput')).toBeFocused();await page.locator('#kanbanTaskModalTitleInput').fill(title);await page.locator('#kanbanTaskModalBody').fill(body);
 await page.locator('#kanbanTaskModalStatus').selectOption(status);await page.locator('#kanbanTaskModalAssignee').selectOption(assignee);
 const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/tasks'&&r.request().method()==='POST');
 await page.locator('#kanbanTaskModalSubmit').click();const saved=await response;expect(saved.status()).toBe(200);
 const id=(await saved.json()).task.id;await expect(preview(page).locator('.kanban-task-preview-title')).toHaveText(title);return id;
}

test('SUPPLEMENT CLARIFY DISPATCH real Kanban worker claims completes and remains isolated from mixed bulk failures',async({page,browser},info)=>{
 test.setTimeout(120_000);await open(page,'kanban');const board=await createBoard(page,'QA actual dispatcher '+Date.now());
 try{
  const parent=await createTask(page,'QA unmet prerequisite','triage');
  const blocked=await createTask(page,'QA dependency blocked selection','todo');
  await page.locator('#kanbanDependencyInput').fill(parent);const link=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/links');
  await preview(page).getByRole('button',{name:'Add dependency',exact:true}).click();expect((await link).status()).toBe(200);
  const good=await createTask(page,'QA manual eligible selection','todo');
  const worker=await createTask(page,'QA local worker','ready','qa-research','QA_KANBAN_WORKER_FLOW. Complete this synthetic task locally. No external actions.');
  await preview(page).locator('.kanban-back-btn').click();
  await page.locator('#btnKanbanRunDispatcher').click();await page.locator('#appDialogCancel').click();
  expect((await detail(page,worker,board)).task.worker_pid).toBeNull();expect((await detail(page,worker,board)).runs).toEqual([]);
  const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/dispatch'&&!new URL(r.url()).searchParams.has('dry_run'));
  await page.locator('#btnKanbanRunDispatcher').click();await page.locator('#appDialogConfirm').click();const dispatched=await response;
  expect(dispatched.status()).toBe(200);const dispatchResult=await dispatched.json();expect(dispatchResult.spawned).toHaveLength(1);
  await expect.poll(async()=>(await detail(page,worker,board)).task.status,{timeout:20_000}).toBe('running');
  const running=await detail(page,worker,board);expect(running.task.worker_pid).toBeGreaterThan(0);expect(running.task.current_run_id).toBeTruthy();expect(running.task.claim_lock).toBeTruthy();
  const forced=await request(page,'/api/kanban/tasks/'+worker+'?board='+board,'PATCH',{status:'running'});expect(forced.status).toBe(400);
  const deny=await browser.newContext({baseURL:auth.base_url});
  try{await deny.addCookies([{name:auth.cookie_name,value:auth.cookies.denied,url:auth.base_url,httpOnly:true,sameSite:'Lax'}]);
   expect((await deny.request.post('/api/kanban/dispatch?board='+board,{data:{}})).status()).toBe(403);
  }finally{await deny.close();}
  await card(page,good).click();await card(page,blocked).click({modifiers:['ControlOrMeta']});
  await expect(page.locator('#kanbanBoard .kanban-card.selected')).toHaveCount(2);
  await card(page,blocked).click({modifiers:['ControlOrMeta']});await expect(page.locator('#kanbanBoard .kanban-card.selected')).toHaveCount(1);
  await card(page,blocked).focus();await card(page,blocked).press('Control+Enter');await expect(page.locator('#kanbanBoard .kanban-card.selected')).toHaveCount(2);
  await page.locator('#kanbanRefreshBtn').click();await expect(page.locator('#kanbanBoard .kanban-card.selected')).toHaveCount(2);
  await page.locator('#kanbanBulkStatus').selectOption('done');const bulk=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/tasks/bulk');
  await page.locator('#kanbanBulkBar [onclick="bulkUpdateKanban()"]').click();const bulkResponse=await bulk;expect(bulkResponse.status()).toBe(200);
  const bulkResult=await bulkResponse.json();expect(bulkResult.results).toHaveLength(2);expect(bulkResult.results.find((r:any)=>r.id===good)).toEqual({id:good,ok:true});
  expect(bulkResult.results.find((r:any)=>r.id===blocked)).toMatchObject({id:blocked,ok:false});
  await expect(page.locator('#toast')).toContainText('1 updated; 1 failed');await expect(page.locator('#toast')).toContainText(blocked);
  expect((await detail(page,good,board)).task.status).toBe('done');expect((await detail(page,blocked,board)).task.status).toBe('todo');
  const stillRunning=await detail(page,worker,board);expect(stillRunning.task.status).toBe('running');expect(stillRunning.task.current_run_id).toBe(running.task.current_run_id);
  await expect.poll(async()=>(await detail(page,worker,board)).task.status,{timeout:60_000}).toBe('done');
  const completed=await detail(page,worker,board);expect(completed.runs).toHaveLength(1);
  const childImport=JSON.parse(fs.readFileSync(path.join(path.dirname(auth.workspace),'runtime-engine.json'),'utf8'));
  expect(childImport.engine_module).toBe(path.join(auth.engine,'hermes_cli','kanban_db.py'));
  expect(childImport.guard_installed).toBe(true);
  expect(completed.runs[0]).toMatchObject({id:running.task.current_run_id,profile:'qa-research',status:'done',outcome:'completed',summary:'QA_KANBAN_WORKER_DONE'});
  expect(completed.runs[0].metadata.worker_session_id).toBeTruthy();
  expect(completed.events.some((event:any)=>event.kind==='claimed')).toBe(true);expect(completed.events.some((event:any)=>event.kind==='completed')).toBe(true);
  await page.locator('#kanbanRefreshBtn').click();await card(page,worker).click();await expect(preview(page)).toContainText('QA_KANBAN_WORKER_DONE');
  await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();expect((await detail(page,worker,board)).task.status).toBe('done');
  await info.attach('real-dispatch-mixed-bulk-readback',{body:JSON.stringify({dispatchResult,bulkResult,running,completed,blocked:await detail(page,blocked,board),good:await detail(page,good,board)}),contentType:'application/json'});
  await capture(page,'worker-completed-and-bulk-refusal',info);
 }finally{expect((await api(page,'/api/kanban/boards/default/switch',{})).status).toBe(200);}
});
