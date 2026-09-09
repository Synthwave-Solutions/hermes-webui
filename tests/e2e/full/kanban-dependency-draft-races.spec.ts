import type {Page, Route} from '@playwright/test';
import {test, expect, open, api} from './fixtures';

const preview=(page:Page)=>page.locator('#kanbanTaskPreview');
const card=(page:Page,id:string)=>page.locator('#kanbanBoard .kanban-card[data-kanban-task-id="'+id+'"]');
async function readTask(page:Page,board:string,id:string){
 const r=await api(page,'/api/kanban/tasks/'+id+'?board='+board);expect(r.status).toBe(200);return r.body;
}
async function seed(page:Page){
 await open(page);
 const board='qa-draft-'+Date.now();
 expect((await api(page,'/api/kanban/boards',{slug:board,name:board,switch:true})).status).toBe(200);
 const ids:string[]=[];
 for(const title of ['Prerequisite','Current child','Other child']){
  const r=await api(page,'/api/kanban/tasks?board='+board,{title,status:'todo'});expect(r.status).toBe(200);ids.push(r.body.task.id);
 }
 const [parent,child,other]=ids;
 expect((await api(page,'/api/kanban/links?board='+board,{parent_id:parent,child_id:child})).status).toBe(200);
 await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();
 await expect(page.locator('#kanbanBoardSwitcherName')).toHaveText(board);
 await card(page,child).click();await expect(preview(page).locator('.kanban-detail-links [data-i18n="kanban_remove_dependency"]')).toHaveCount(1);
 const removed=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/links/delete'&&r.request().method()==='POST');
 await preview(page).locator('.kanban-detail-links [data-i18n="kanban_remove_dependency"]').click();expect((await removed).status()).toBe(200);
 await expect.poll(async()=>(await readTask(page,board,child)).links.parents).toEqual([]);
 await expect(preview(page).locator('.kanban-detail-links [data-i18n="kanban_remove_dependency"]')).toHaveCount(0);
 return {board,parent,child,other};
}
async function holdLiveRefresh(page:Page,board:string,child:string,title:string){
 let release!:()=>void, held!:()=>void;
 const gate=new Promise<void>(r=>release=r), arrived=new Promise<void>(r=>held=r);
 const deliveries=new Set<Promise<void>>();
 const pattern='**/api/kanban/tasks/'+child+'/log?*';
 const handler=(route:Route)=>{
  const delivery=(async()=>{const response=await route.fetch();expect(response.status()).toBe(200);held();await gate;await route.fulfill({response});})();
  deliveries.add(delivery);return delivery.finally(()=>deliveries.delete(delivery));
 };
 await page.route(pattern,handler);
 // A real task update emits the ordinary SSE refresh. Only delivery of its
 // actual successful log response is delayed, never its contents.
 const changed=await page.request.patch('/api/kanban/tasks/'+child+'?board='+board,{data:{title}});expect(changed.status()).toBe(200);
 await arrived;
 return {release,unroute:async()=>{await Promise.all([...deliveries]);await page.unroute(pattern,handler);}};
}

test('SUPPLEMENT KANBAN DEPENDENCY DRAFT a late live refresh preserves re-add input and one exact persisted link',async({page},info)=>{
 const {board,parent,child}=await seed(page);let release=()=>{};
 try{
  const title='Refreshed child '+Date.now();const held=await holdLiveRefresh(page,board,child,title);release=held.release;
  await page.locator('#kanbanDependencyInput').fill(parent);await expect(page.locator('#kanbanDependencyInput')).toHaveValue(parent);
  held.release();await expect(preview(page).locator('.kanban-task-preview-title')).toHaveText(title);
  await expect(page.locator('#kanbanDependencyInput')).toHaveValue(parent);await held.unroute();
  const submissions:any[]=[];
  page.on('request',r=>{if(new URL(r.url()).pathname==='/api/kanban/links'&&r.method()==='POST')submissions.push(r.postDataJSON());});
  const saved=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/links'&&r.request().method()==='POST');
  await preview(page).getByRole('button',{name:'Add dependency',exact:true}).click();expect((await saved).status()).toBe(200);
  await expect(preview(page).locator('.kanban-detail-links [data-i18n="kanban_remove_dependency"]')).toHaveCount(1);
  await expect(page.locator('#kanbanDependencyInput')).toHaveValue('');
  expect(submissions).toEqual([{parent_id:parent,child_id:child}]);expect((await readTask(page,board,child)).links.parents).toEqual([parent]);
  await page.reload();await page.locator('.rail-btn[data-panel="kanban"]').click();await card(page,child).click();
  await expect(preview(page).locator('.kanban-detail-links')).toContainText(parent);await expect(page.locator('#kanbanDependencyInput')).toHaveValue('');
  await info.attach('dependency-draft-refresh-readback',{body:JSON.stringify({board,parent,child,submissions,parents:(await readTask(page,board,child)).links.parents}),contentType:'application/json'});
 }finally{release();expect((await api(page,'/api/kanban/boards/default/switch',{})).status).toBe(200);}
});

test('SUPPLEMENT KANBAN DEPENDENCY DRAFT newer clear and task navigation cannot restore or transfer an old draft',async({page},info)=>{
 const {board,parent,child,other}=await seed(page);let release=()=>{};
 try{
  await page.locator('#kanbanDependencyInput').fill(parent);
  const title='Cleared child '+Date.now();const held=await holdLiveRefresh(page,board,child,title);release=held.release;
  await page.locator('#kanbanDependencyInput').fill('');held.release();
  await expect(preview(page).locator('.kanban-task-preview-title')).toHaveText(title);await expect(page.locator('#kanbanDependencyInput')).toHaveValue('');await held.unroute();
  await page.locator('#kanbanDependencyInput').fill(parent);
  const stale=await holdLiveRefresh(page,board,child,'Late old child '+Date.now());release=stale.release;
  await preview(page).locator('.kanban-back-btn').click();await card(page,other).click();
  await expect(preview(page).locator('.kanban-task-preview-title')).toHaveText('Other child');await expect(page.locator('#kanbanDependencyInput')).toHaveValue('');
  stale.release();await stale.unroute();
  await expect(preview(page).locator('.kanban-task-preview-title')).toHaveText('Other child');await expect(page.locator('#kanbanDependencyInput')).toHaveValue('');
  expect((await readTask(page,board,child)).links.parents).toEqual([]);expect((await readTask(page,board,other)).links.parents).toEqual([]);
  await info.attach('dependency-draft-navigation-readback',{body:JSON.stringify({board,child,other,childParents:[],otherParents:[]}),contentType:'application/json'});
 }finally{release();expect((await api(page,'/api/kanban/boards/default/switch',{})).status).toBe(200);}
});

test('SUPPLEMENT KANBAN DEPENDENCY DRAFT a delayed successful Add keeps the next edited dependency for its own submission',async({page},info)=>{
 const {board,parent,child,other}=await seed(page);
 let release!:()=>void, held!:()=>void, delivered!:()=>void;
 const gate=new Promise<void>(r=>release=r), arrived=new Promise<void>(r=>held=r), finished=new Promise<void>(r=>delivered=r);
 try{
  await page.route('**/api/kanban/links?*',async route=>{
   const response=await route.fetch();expect(response.status()).toBe(200);held();await gate;await route.fulfill({response});delivered();
  },{times:1});
  await page.locator('#kanbanDependencyInput').fill(parent);
  const saved=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/links'&&r.request().method()==='POST');
  await preview(page).getByRole('button',{name:'Add dependency',exact:true}).click();await arrived;
  expect((await readTask(page,board,child)).links.parents).toEqual([parent]);
  await page.locator('#kanbanDependencyInput').fill(other);
  const refreshed=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/tasks/'+child+'/log');
  release();expect((await saved).status()).toBe(200);await finished;await refreshed;
  await expect(page.locator('#kanbanDependencyInput')).toHaveValue(other);
  const second=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/kanban/links'&&r.request().method()==='POST');
  await preview(page).getByRole('button',{name:'Add dependency',exact:true}).click();const response=await second;
  expect(response.status()).toBe(200);expect(response.request().postDataJSON()).toEqual({parent_id:other,child_id:child});
  await expect(preview(page).locator('.kanban-detail-links [data-i18n="kanban_remove_dependency"]')).toHaveCount(2);
  await expect(page.locator('#kanbanDependencyInput')).toHaveValue('');
  expect((await readTask(page,board,child)).links.parents.sort()).toEqual([parent,other].sort());
  await info.attach('dependency-next-draft-readback',{body:JSON.stringify({board,child,parents:[parent,other].sort()}),contentType:'application/json'});
 }finally{release();expect((await api(page,'/api/kanban/boards/default/switch',{})).status).toBe(200);}
});
