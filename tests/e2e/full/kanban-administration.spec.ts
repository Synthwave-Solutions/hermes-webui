import type {Browser, Page} from '@playwright/test';
import {test, expect, open, api, auth, capture} from './fixtures';

const uid=(prefix:string)=>prefix+'-'+Date.now();
const preview=(page:Page)=>page.locator('#kanbanTaskPreview');
const card=(page:Page,id:string)=>page.locator('#kanbanBoard .kanban-card[data-kanban-task-id="'+id+'"]');
async function task(page:Page,id:string,board:string){
 const r=await api(page,'/api/kanban/tasks/'+id+'?board='+board);expect(r.status).toBe(200);return r.body;
}
async function denied(browser:Browser,url:string,method:string,data?:any){
 const context=await browser.newContext({baseURL:auth.base_url});
 try{
  await context.addCookies([{name:auth.cookie_name,value:auth.cookies.denied,url:auth.base_url,httpOnly:true,sameSite:'Lax'}]);
  const response=await context.request.fetch(url,{method,data});expect(response.status()).toBe(403);
 }finally{await context.close();}
}
async function boardMenu(page:Page){
 if(await page.locator('#kanbanBoardSwitcherMenu').isHidden())await page.locator('#kanbanBoardSwitcherToggle').click();
 await expect(page.locator('#kanbanBoardSwitcherMenu')).toBeVisible();
}
async function createBoard(page:Page,name:string){
 await page.locator('#btnKanbanCreateBoard').click();
 await expect(page.locator('#kanbanBoardModalName')).toBeFocused();await page.locator('#kanbanBoardModalName').fill(name);
 const slug=uid('qa-board');await page.locator('#kanbanBoardModalSlugInput').fill(slug);
 const saved=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/boards'&&r.request().method()==='POST');
 await page.locator('#kanbanBoardModalSubmit').click();expect((await saved).status()).toBe(200);
 await expect(page.locator('#kanbanBoardSwitcherName')).toHaveText(name);return slug;
}
async function createTask(page:Page,board:string,name:string,status='todo',assignee='',tenant=''){
 await page.locator('#kanbanNewTaskBtn').click();await expect(page.locator('#kanbanTaskModalTitleInput')).toBeFocused();await page.locator('#kanbanTaskModalTitleInput').fill(name);
 await page.locator('#kanbanTaskModalBody').fill('Synthetic board acceptance; no live delivery.');
 await page.locator('#kanbanTaskModalStatus').selectOption(status);await page.locator('#kanbanTaskModalAssignee').selectOption(assignee);
 await page.locator('#kanbanTaskModalTenant').fill(tenant);
 const saved=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/tasks'&&r.request().method()==='POST');
 await page.locator('#kanbanTaskModalSubmit').click();const response=await saved;expect(response.status()).toBe(200);
 const id=(await response.json()).task.id;await expect(preview(page).locator('.kanban-task-preview-title')).toHaveText(name);
 expect((await task(page,id,board)).task.status).toBe(status);return id;
}
async function showTask(page:Page,id:string){
 const title=await card(page,id).locator('.kanban-card-title').innerText();
 await preview(page).locator('.kanban-back-btn').click();await card(page,id).click();await expect(preview(page).locator('.kanban-task-preview-title')).toHaveText(title);
}
async function addDependency(page:Page,parent:string){
 await page.locator('#kanbanDependencyInput').fill(parent);
 const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/links'&&r.request().method()==='POST');
 await preview(page).getByRole('button',{name:'Add dependency',exact:true}).click();return await response;
}
async function done(page:Page,id:string){
 const changed=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/tasks/'+id&&r.request().method()==='PATCH');
 await preview(page).locator('.kanban-status-actions').getByRole('button',{name:'Done',exact:true}).click();return await changed;
}
async function returnDefault(page:Page){
 // Cleanup only: restore the shared fixture pointer so later cases start at default.
 expect((await api(page,'/api/kanban/boards/default/switch',{})).status).toBe(200);
}

test('US-SP-KAN-ADMIN-BOARDS create validate cancel rename switch archive persist with denied administration',async({page,browser},info)=>{
 await open(page,'kanban');await page.locator('#btnKanbanCreateBoard').click();await page.locator('#kanbanBoardModalSubmit').click();
 await expect(page.locator('#kanbanBoardModalError')).toContainText('Name is required');
 await page.locator('#kanbanBoardModalName').fill('Cancelled board');await page.keyboard.press('Escape');
 expect((await api(page,'/api/kanban/boards')).body.boards.some((x:any)=>x.name==='Cancelled board')).toBe(false);
 const name=uid('QA Board');const board=await createBoard(page,name);const renamed=name+' renamed';
 try{
  await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();await expect(page.locator('#kanbanBoardSwitcherName')).toHaveText(name);
  await boardMenu(page);await page.locator('#kanbanBoardSwitcherMenu [onclick="openKanbanRenameBoard()"]').click();
  await expect(page.locator('#kanbanBoardModalSlugInput')).toBeDisabled();await page.locator('#kanbanBoardModalName').fill('Discarded rename');await page.keyboard.press('Escape');
  expect((await api(page,'/api/kanban/boards')).body.boards.find((x:any)=>x.slug===board).name).toBe(name);
  await boardMenu(page);await page.locator('#kanbanBoardSwitcherMenu [onclick="openKanbanRenameBoard()"]').click();
  await expect(page.locator('#kanbanBoardModalName')).toBeFocused();await page.locator('#kanbanBoardModalName').fill(renamed);await page.locator('#kanbanBoardModalDesc').fill('Saved board metadata');
  await page.locator('#kanbanBoardModalIcon').fill('🧪');await page.locator('#kanbanBoardModalColor').fill('#335577');await page.locator('#kanbanBoardModalSubmit').click();
  await expect(page.locator('#kanbanBoardSwitcherName')).toHaveText(renamed);
  await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();await expect(page.locator('#kanbanBoardSwitcherName')).toHaveText(renamed);
  expect((await api(page,'/api/kanban/boards')).body.boards.find((x:any)=>x.slug===board)).toMatchObject({name:renamed,description:'Saved board metadata',icon:'🧪',color:'#335577'});
  await denied(browser,'/api/kanban/boards/'+board,'PATCH',{name:'Unauthorized'});await denied(browser,'/api/kanban/boards/'+board,'DELETE');
  expect((await api(page,'/api/kanban/boards')).body.boards.find((x:any)=>x.slug===board).name).toBe(renamed);
  await boardMenu(page);await page.locator('#kanbanBoardSwitcherMenu [data-board-slug="default"]').click();
  await expect(page.locator('#kanbanBoardSwitcherName')).toHaveText('Default');
  await boardMenu(page);await expect(page.locator('#kanbanBoardSwitcherMenu [onclick="archiveKanbanBoard()"]').first()).toBeDisabled();
  await page.locator('#kanbanBoardSwitcherMenu [data-board-slug="'+board+'"]').click();await expect(page.locator('#kanbanBoardSwitcherName')).toHaveText(renamed);
  await boardMenu(page);await page.locator('#kanbanBoardSwitcherMenu [onclick="archiveKanbanBoard()"]').click();await page.locator('#appDialogCancel').click();
  expect((await api(page,'/api/kanban/boards')).body.boards.some((x:any)=>x.slug===board)).toBe(true);
  await boardMenu(page);await page.locator('#kanbanBoardSwitcherMenu [onclick="archiveKanbanBoard()"]').click();
  await page.locator('#appDialogConfirm').click();await expect.poll(async()=>(await api(page,'/api/kanban/boards')).body.boards.some((x:any)=>x.slug===board)).toBe(false);
  await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();expect((await api(page,'/api/kanban/boards')).body.current).toBe('default');
  await capture(page,'board-archived',info);
 }finally{await returnDefault(page);}
});

test('US-SP-KAN-ADMIN-DEPENDENCIES add remove reject cycles and guard direct completion until parent finishes',async({page,browser},info)=>{
 await open(page,'kanban');const board=await createBoard(page,uid('QA Dependency Board'));
 try{
  const parent=await createTask(page,board,'QA pending prerequisite','triage');
  const child=await createTask(page,board,'QA pending child','todo');
  expect((await addDependency(page,parent)).status()).toBe(200);expect((await task(page,child,board)).links.parents).toEqual([parent]);
  await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();await card(page,child).click();await expect(preview(page).locator('.kanban-detail-links')).toContainText(parent);
  expect((await done(page,child)).status()).toBe(400);await expect(page.locator('#toast')).toContainText('finish its dependencies');
  expect((await task(page,child,board)).task.status).toBe('todo');expect((await task(page,child,board)).task.completed_at).toBeNull();
  await page.locator('#kanbanDependencyInput').fill(child);await preview(page).getByRole('button',{name:'Add dependency',exact:true}).click();await expect(page.locator('#toast')).toContainText('cannot depend on itself');
  await showTask(page,parent);expect((await addDependency(page,child)).status()).toBe(400);expect((await task(page,parent,board)).links.parents).toEqual([]);
  await showTask(page,child);await preview(page).locator('.kanban-detail-links [data-i18n="kanban_remove_dependency"]').click();
  await expect.poll(async()=>(await task(page,child,board)).links.parents).toEqual([]);await expect(preview(page).locator('.kanban-detail-links [data-i18n="kanban_remove_dependency"]')).toHaveCount(0);
  expect((await addDependency(page,parent)).status()).toBe(200);
  await denied(browser,'/api/kanban/tasks/'+child+'?board='+board,'PATCH',{status:'done'});
  await denied(browser,'/api/kanban/links/delete?board='+board,'POST',{parent_id:parent,child_id:child});
  expect((await task(page,child,board)).links.parents).toEqual([parent]);expect((await task(page,child,board)).task.status).toBe('todo');
  await showTask(page,parent);expect((await done(page,parent)).status()).toBe(200);expect((await task(page,parent,board)).task.status).toBe('done');
  await showTask(page,child);expect((await done(page,child)).status()).toBe(200);
  await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();
  for(const id of [parent,child]){await expect(page.locator('.kanban-column[data-status="done"] .kanban-card[data-kanban-task-id="'+id+'"]')).toBeVisible();expect((await task(page,id,board)).task.status).toBe('done');}
  await info.attach('dependency-completion-readback',{body:JSON.stringify({parent:await task(page,parent,board),child:await task(page,child,board)}),contentType:'application/json'});
 }finally{await returnDefault(page);}
});

test('US-SP-KAN-ADMIN-FILTERS exact assignee tenant mine lanes selected bulk completion and dispatcher preview',async({page,browser},info)=>{
 await open(page,'kanban');const board=await createBoard(page,uid('QA Filter Board'));
 const initial=(await api(page,'/api/kanban/config')).body.lane_by_profile===true;
 try{
  const a=await createTask(page,board,'QA Filter A','todo','default','qa-alpha');
  const b=await createTask(page,board,'QA Filter B','todo','qa-research','qa-beta');
  await preview(page).locator('.kanban-status-actions').getByRole('button',{name:'Ready',exact:true}).click();await expect.poll(async()=>(await task(page,b,board)).task.status).toBe('ready');
  await preview(page).locator('.kanban-status-actions').getByRole('button',{name:'Blocked',exact:true}).click();await expect.poll(async()=>(await task(page,b,board)).task.status).toBe('blocked');
  const c=await createTask(page,board,'QA Filter C','todo','','qa-alpha');
  await preview(page).locator('.kanban-status-actions').getByRole('button',{name:'Ready',exact:true}).click();await expect.poll(async()=>(await task(page,c,board)).task.status).toBe('ready');
  await preview(page).locator('.kanban-status-actions').getByRole('button',{name:'Blocked',exact:true}).click();await expect.poll(async()=>(await task(page,c,board)).task.status).toBe('blocked');
  await preview(page).locator('.kanban-back-btn').click();
  const visible=()=>page.locator('#kanbanBoard .kanban-card').evaluateAll(es=>es.map(e=>e.getAttribute('data-kanban-task-id')).sort());
  await expect.poll(visible).toEqual([a,b,c].sort());
  await page.locator('#kanbanAssigneeFilter').selectOption('qa-research');await expect.poll(visible).toEqual([b]);
  await page.locator('#kanbanAssigneeFilter').selectOption('');await page.locator('#kanbanTenantFilter').selectOption('qa-alpha');await expect.poll(visible).toEqual([a,c].sort());
  await page.locator('#kanbanTenantFilter').selectOption('');await page.locator('#kanbanOnlyMine').check();await expect.poll(visible).toEqual([a]);
  await page.locator('#kanbanOnlyMine').uncheck();await expect.poll(visible).toEqual([a,b,c].sort());
  await page.locator('#kanbanSearch').fill('QA Filter B');await expect.poll(visible).toEqual([b]);await page.locator('#kanbanSearch').fill('no-matching-task');await expect.poll(visible).toEqual([]);await page.locator('#kanbanSearch').fill('');
  await page.locator('#btnKanbanViewToggle').click();await expect.poll(async()=>(await api(page,'/api/kanban/config')).body.lane_by_profile).toBe(!initial);
  await expect.poll(visible).toEqual([a,b,c].sort());await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();
  expect((await api(page,'/api/kanban/config')).body.lane_by_profile).toBe(!initial);await expect.poll(visible).toEqual([a,b,c].sort());
  await page.locator('#btnKanbanViewToggle').click();await expect.poll(async()=>(await api(page,'/api/kanban/config')).body.lane_by_profile).toBe(initial);
  await card(page,a).click();await page.locator('#kanbanBulkStatus').selectOption('done');
  const bulk=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/tasks/bulk');await page.locator('#kanbanBulkBar [onclick="bulkUpdateKanban()"]').click();
  const bulkResponse=await bulk;expect(bulkResponse.status()).toBe(200);expect((await bulkResponse.json()).results).toEqual([{id:a,ok:true}]);
  expect((await task(page,a,board)).task.status).toBe('done');for(const id of [b,c])expect((await task(page,id,board)).task.status).toBe('blocked');
  await denied(browser,'/api/kanban/tasks/bulk?board='+board,'POST',{ids:[b,c],status:'done'});for(const id of [b,c])expect((await task(page,id,board)).task.status).toBe('blocked');
  const dispatch=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/dispatch');await page.locator('#btnKanbanPreviewDispatcher').click();
  const response=await dispatch;expect(response.status()).toBe(200);expect(new URL(response.url()).searchParams.get('dry_run')).toBe('1');const result=await response.json();expect(result.spawned).toEqual([]);
  for(const id of [a,b,c]){const persisted=(await task(page,id,board)).task;expect(persisted.worker_pid).toBeNull();expect(persisted.current_run_id).toBeNull();}
  await page.locator('#kanbanRefreshBtn').click();await expect.poll(visible).toEqual([a,b,c].sort());
  await info.attach('kanban-filter-preview-result',{body:JSON.stringify({result,tasks:await Promise.all([a,b,c].map(id=>task(page,id,board)))}),contentType:'application/json'});
 }finally{await returnDefault(page);}
});

test('US-SP-KAN-ADMIN-BLOCK Todo block unblock preserve reason dependency denial and repeated-block escalation',async({page,browser},info)=>{
 await open(page,'kanban');const board=await createBoard(page,uid('QA Manual Block Board'));
 try{
  const parent=await createTask(page,board,'QA unresolved prerequisite','triage');
  const child=await createTask(page,board,'QA manually blocked Todo','todo');
  expect((await addDependency(page,parent)).status()).toBe(200);await expect(preview(page).locator('.kanban-detail-links')).toContainText(parent);
  const block=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/tasks/'+child&&r.request().method()==='PATCH');
  await preview(page).locator('.kanban-status-actions').getByRole('button',{name:'Blocked',exact:true}).click();expect((await block).status()).toBe(200);
  await expect.poll(async()=>(await task(page,child,board)).task.status).toBe('blocked');
  const blocked=await task(page,child,board);expect(blocked.events.some((e:any)=>e.kind==='blocked'&&e.payload?.reason==='blocked from WebUI')).toBe(true);
  expect(blocked.task.worker_pid).toBeNull();expect(blocked.task.claim_lock).toBeNull();
  await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();await card(page,child).click();
  await expect(preview(page).locator('.kanban-detail-events')).toContainText('blocked from WebUI');
  await denied(browser,'/api/kanban/tasks/'+child+'/unblock?board='+board,'POST',{});expect((await task(page,child,board)).task.status).toBe('blocked');
  await preview(page).locator('.kanban-status-actions').getByRole('button',{name:'Unblock',exact:true}).click();await expect.poll(async()=>(await task(page,child,board)).task.status).toBe('todo');
  expect((await task(page,child,board)).links.parents).toEqual([parent]);
  await denied(browser,'/api/kanban/tasks/'+child+'?board='+board,'PATCH',{status:'blocked'});expect((await task(page,child,board)).task.status).toBe('todo');
  await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();await expect(page.locator('.kanban-column[data-status="todo"] .kanban-card[data-kanban-task-id="'+child+'"]')).toBeVisible();
  const unblocked=await task(page,child,board);expect(unblocked.links.parents).toEqual([parent]);expect(unblocked.events.filter((e:any)=>e.kind==='unblocked')).toHaveLength(1);
  await card(page,child).click();
  // The existing second-same-cause limit must still escalate to human triage.
  const namedBlock=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/tasks/'+child+'/block');
  await preview(page).locator('.kanban-status-actions').getByRole('button',{name:'Block',exact:true}).click();expect((await namedBlock).status()).toBe(200);await expect.poll(async()=>(await task(page,child,board)).task.status).toBe('triage');
  await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();await expect(page.locator('.kanban-column[data-status="triage"] .kanban-card[data-kanban-task-id="'+child+'"]')).toBeVisible();
  const final=await task(page,child,board);expect(final.links.parents).toEqual([parent]);expect(final.task.block_recurrences).toBe(2);expect(final.events.some((e:any)=>e.kind==='block_loop_detected'&&e.payload?.reason==='blocked from WebUI')).toBe(true);
  await info.attach('manual-block-persistence',{body:JSON.stringify(final),contentType:'application/json'});
 }finally{await returnDefault(page);}
});
