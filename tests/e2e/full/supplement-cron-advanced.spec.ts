import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import type {Page} from '@playwright/test';
import {test, expect, open, api, auth, capture} from './fixtures';

const state = path.dirname(auth.workspace);
const home = path.join(state, 'home');
async function job(page:Page,id:string){
 const r=await api(page,'/api/crons');expect(r.status).toBe(200);
 return r.body.jobs.find((j:any)=>j.id===id);
}
async function createForm(page:Page,name:string,prompt='QA_CRON_ADVANCED'){
 await open(page,'tasks');await page.getByRole('button',{name:'New job',exact:true}).click();
 await page.locator('#cronFormName').fill(name);await page.locator('#cronFormPrompt').fill(prompt);
 await expect(page.locator('#cronFormDeliver')).toBeEnabled();await page.locator('#cronFormDeliver').selectOption('local');
}
async function save(page:Page,endpoint='create'){
 const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/crons/'+endpoint&&r.request().method()==='POST');
 await page.locator('#btnSaveTaskDetail').click();const response=await pending;
 expect(response.status()).toBe(200);const body=await response.json();return body.job;
}
async function reopen(page:Page,name:string){
 await open(page,'tasks');await page.locator('.cron-item').filter({hasText:name}).click();
 await page.locator('#btnEditTaskDetail').click();
}
async function remove(page:Page,id:string){
 await page.locator('#btnDeleteTaskDetail').click();await page.locator('#appDialogConfirm').click();
 await expect.poll(()=>job(page,id)).toBeUndefined();
}
function receipts(){
 const file=path.join(state,'provider-evidence.jsonl');
 return fs.existsSync(file)?fs.readFileSync(file,'utf8').split('\n').filter(Boolean).map(line=>JSON.parse(line)):[];
}
// Read the genuine persisted record into a disposable store. Only this copy's
// scheduler clock is advanced; the browser server and its jobs are untouched.
function eligibility(id:string,at:string){
 expect(path.basename(state)).toBe('e2e-state');
 const source=path.join(home,'cron','jobs.json');const before=fs.readFileSync(source);
 const store=JSON.parse(before.toString());const original=store.jobs.find((j:any)=>j.id===id);
 const copy=fs.mkdtempSync(path.join(state,'cron-due-copy-'));
 fs.mkdirSync(path.join(copy,'cron'));fs.writeFileSync(path.join(copy,'cron','jobs.json'),JSON.stringify({...store,jobs:original?[original]:[]}));
 const code=`import json,sys\nfrom datetime import datetime\nimport cron.jobs as jobs\nimport isolation\nassert isolation._INSTALLED\njobs._hermes_now=lambda:datetime.fromisoformat(sys.argv[1])\nprint(json.dumps({'due':[j['id'] for j in jobs.get_due_jobs()], 'engine':jobs.__file__}))`;
 const result=spawnSync(path.resolve('.venv/bin/python'),['-c',code,at],{encoding:'utf8',env:{...process.env,HERMES_HOME:copy,HERMES_BASE_HOME:copy,HERMES_CONFIG_PATH:path.join(copy,'config.yaml'),PYTHONPATH:[path.resolve('scripts/e2e'),auth.engine,path.resolve('.')].join(path.delimiter)}});
 expect(result.status,result.stderr).toBe(0);const evaluated=JSON.parse(result.stdout.trim());
 expect(path.resolve(evaluated.engine)).toBe(path.join(auth.engine,'cron','jobs.py'));
 expect(fs.readFileSync(source).equals(before),'eligibility probe must not mutate live fixture store').toBe(true);
 return evaluated.due as string[];
}

test('SUPPLEMENT CRON ADVANCED weekly Sunday editor and pause resume delete govern future scheduler eligibility',async({page,browser},info)=>{
 const name='QA weekly '+Date.now();await createForm(page,name);
 await page.locator('#cronFormSchedulePreset').selectOption('weekly');
 await page.locator('#cronFormScheduleWeekday').selectOption('0');await page.locator('#cronFormScheduleTime').fill('13:27');
 await expect(page.locator('#cronFormSchedulePreview')).toContainText('27 13 * * 0');
 const created=await save(page);const id=created.id;
 expect(created.schedule).toMatchObject({kind:'cron',expr:'27 13 * * 0'});
 expect(created.next_run_at.slice(11,16)).toBe('13:27');expect(new Date(created.next_run_at.slice(0,10)+'T00:00:00Z').getUTCDay()).toBe(0);
 expect(Date.parse(created.next_run_at)).toBeGreaterThan(Date.now());
 await reopen(page,name);await expect(page.locator('#cronFormSchedulePreset')).toHaveValue('weekly');
 await expect(page.locator('#cronFormScheduleWeekday')).toHaveValue('0');await expect(page.locator('#cronFormScheduleTime')).toHaveValue('13:27');
 await page.locator('#btnCancelTaskDetail').click();
 const future=created.next_run_at;
 expect(eligibility(id,future)).toEqual([id]);
 const denied=await browser.newContext({baseURL:auth.base_url});
 try{await denied.addCookies([{name:auth.cookie_name,value:auth.cookies.denied,url:auth.base_url,httpOnly:true,sameSite:'Lax'}]);
  const before=await job(page,id);
  for(const endpoint of ['update','run','pause','resume','delete'])expect((await denied.request.post('/api/crons/'+endpoint,{data:{job_id:id,schedule:'every 1m'}})).status()).toBe(403);
  expect(await job(page,id)).toEqual(before);
 }finally{await denied.close();}
 await page.locator('#btnPauseTaskDetail').click();await expect(page.locator('#btnResumeTaskDetail')).toBeVisible();
 expect(await job(page,id)).toMatchObject({enabled:false,state:'paused'});expect(eligibility(id,future)).toEqual([]);
 await open(page,'tasks');await page.locator('.cron-paused-summary').click();await page.locator('.cron-item').filter({hasText:name}).click();await expect(page.locator('#btnResumeTaskDetail')).toBeVisible();
 await page.locator('#btnResumeTaskDetail').click();await expect(page.locator('#btnPauseTaskDetail')).toBeVisible();
 const resumed=await job(page,id);expect(resumed.enabled).toBe(true);expect(Date.parse(resumed.next_run_at)).toBeGreaterThan(Date.now());
 expect(eligibility(id,resumed.next_run_at)).toEqual([id]);
 await remove(page,id);expect(eligibility(id,future)).toEqual([]);
 await info.attach('future-eligibility-boundary',{body:JSON.stringify({created,resumed,at:future,states:['enabled:due','paused:not due','resumed:due','deleted:not due'],method:'real engine get_due_jobs against copied persisted records with controlled future clock; no wall-clock ticker certification'}),contentType:'application/json'});
});

test('SUPPLEMENT CRON ADVANCED monthly day31 and custom expression preserve saved state across invalid edit and reload',async({page},info)=>{
 const name='QA monthly '+Date.now();await createForm(page,name);
 await page.locator('#cronFormSchedulePreset').selectOption('monthly');await page.locator('#cronFormScheduleMonthDay').selectOption('31');
 await page.locator('#cronFormScheduleTime').fill('22:41');const created=await save(page);const id=created.id;
 expect(created.schedule).toMatchObject({kind:'cron',expr:'41 22 31 * *'});expect(created.next_run_at.slice(8,10)).toBe('31');expect(created.next_run_at.slice(11,16)).toBe('22:41');
 await reopen(page,name);await expect(page.locator('#cronFormSchedulePreset')).toHaveValue('monthly');
 await expect(page.locator('#cronFormScheduleMonthDay')).toHaveValue('31');await expect(page.locator('#cronFormScheduleTime')).toHaveValue('22:41');
 await page.locator('#cronFormSchedulePreset').selectOption('custom');await page.locator('#cronFormSchedule').fill('not-a-cron');
 const rejected=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/crons/update'&&r.request().method()==='POST');
 await page.locator('#btnSaveTaskDetail').click();expect((await rejected).status()).toBe(400);await expect(page.locator('#cronFormError')).toBeVisible();
 expect((await job(page,id)).schedule).toEqual(created.schedule);
 await page.locator('#cronFormSchedule').fill('*/17 8-18 * * 1-5');const updated=await save(page,'update');
 expect(updated.schedule).toMatchObject({kind:'cron',expr:'*/17 8-18 * * 1-5'});
 await reopen(page,name);await expect(page.locator('#cronFormSchedulePreset')).toHaveValue('custom');await expect(page.locator('#cronFormSchedule')).toHaveValue('*/17 8-18 * * 1-5');
 await page.locator('#cronFormSchedule').fill('@hourly');await page.locator('#btnCancelTaskDetail').click();
 expect((await job(page,id)).schedule).toEqual(updated.schedule);await capture(page,'monthly-custom-persisted',info);await remove(page,id);
});

test('SUPPLEMENT CRON ADVANCED one-shot custom warning and Run now retain completed history without future eligibility',async({page},info)=>{
 test.setTimeout(90_000);const marker='QA_CRON_ONESHOT_RUNTIME';const name='QA once '+Date.now();await createForm(page,name,marker);
 await page.locator('#cronFormSchedulePreset').selectOption('custom');await page.locator('#cronFormSchedule').fill('2h');
 await expect(page.locator('#cronFormScheduleOnceWarning')).toBeHidden();const recurring=await save(page);
 expect(recurring.schedule).toMatchObject({kind:'interval',minutes:120});await remove(page,recurring.id);
 await createForm(page,name,marker);await page.locator('#cronFormSchedulePreset').selectOption('custom');await page.locator('#cronFormSchedule').fill('in 2h');
 await expect(page.locator('#cronFormScheduleOnceWarning')).toBeVisible();const created=await save(page);const id=created.id;
 expect(created.schedule.kind).toBe('once');expect(Date.parse(created.next_run_at)-Date.now()).toBeGreaterThan(110*60*1000);
 await reopen(page,name);await expect(page.locator('#cronFormSchedulePreset')).toHaveValue('custom');await expect(page.locator('#cronFormScheduleOnceWarning')).toBeVisible();
 await expect(page.locator('#cronFormSchedule')).toHaveValue(created.schedule.run_at);
 await page.locator('#cronFormName').fill(name+' renamed');const renamed=await save(page,'update');
 expect(renamed.schedule.run_at).toBe(created.schedule.run_at);expect(renamed.next_run_at).toBe(created.next_run_at);
 await page.locator('#btnRunTaskDetail').click();
 await expect.poll(async()=> (await api(page,'/api/crons/history?job_id='+id)).body.total,{timeout:60_000}).toBe(1);
 await expect.poll(async()=> (await job(page,id)).state,{timeout:15_000}).toBe('completed');
 const completed=await job(page,id);expect(completed).toMatchObject({enabled:false,next_run_at:null,last_status:'ok',repeat:{times:1,completed:1}});
 expect(eligibility(id,created.schedule.run_at)).toEqual([]);
 const history=(await api(page,'/api/crons/history?job_id='+id)).body;
 const output=await api(page,'/api/crons/run?job_id='+id+'&filename='+encodeURIComponent(history.runs[0].filename));
 expect(output.status).toBe(200);expect(output.body.content).toContain('QA_REPLY: '+marker);
 await open(page,'tasks');await page.locator('.cron-item').filter({hasText:name+' renamed'}).click();
 await expect(page.locator('#taskDetailBody .detail-row').filter({has:page.locator('.detail-row-label',{hasText:/^Status$/})}).locator('.detail-badge')).toHaveText('off');
 await expect(page.locator('#cronDetailRuns .detail-run-item')).toHaveCount(1);await page.locator('#cronDetailRuns .detail-run-head').click();
 await expect(page.locator('#cronDetailRuns .cron-run-pre')).toContainText('QA_REPLY: '+marker);
 expect((await api(page,'/api/crons/history?job_id='+id)).body.total).toBe(1);await remove(page,id);
 expect((await api(page,'/api/crons/run',{job_id:id})).status).toBe(404);
 await info.attach('one-shot-consumption',{body:JSON.stringify({created,completed,history,output:output.body}),contentType:'application/json'});
});

test('SUPPLEMENT CRON ADVANCED selected profile model and skill reach actual isolated cron execution',async({page},info)=>{
 test.setTimeout(90_000);const suffix=Date.now();const skill='qa-cron-'+suffix;const marker='QA_CRON_SELECTED_RUNTIME';
 const skillPaths=[path.join(home,'skills',skill),path.join(home,'profiles','qa-research','skills',skill)];
 for(const [i,directory] of skillPaths.entries()){
  fs.mkdirSync(directory,{recursive:true});fs.writeFileSync(path.join(directory,'SKILL.md'),'---\nname: '+skill+'\ndescription: Synthetic isolated Cron skill\n---\n'+(i?'QA_CRON_TARGET_SKILL':'QA_CRON_WRONG_PROFILE_SKILL')+'\nSummarize only the supplied synthetic evidence.\n');
 }
 let id='';const name='QA selected '+suffix;
 try{
  await createForm(page,name,marker);await page.locator('#cronFormProfile').selectOption('qa-research');
  await expect(page.locator('#cronFormModel')).toBeEnabled();
  const model=page.locator('#cronFormModel');const value=await model.locator('option').evaluateAll(options=>options.map(o=>(o as HTMLOptionElement).value).find(v=>v.endsWith('qa-deterministic')));
  expect(value).toBeTruthy();await model.selectOption(value!);
  await page.locator('#cronFormSkillSearch').fill(skill);await page.locator('#cronFormSkillDropdown .skill-opt').filter({hasText:skill}).click();
  await expect(page.locator('#cronFormSkillTags .skill-tag')).toHaveCount(1);
  await page.locator('#cronFormSkillTags .remove-tag').click();await expect(page.locator('#cronFormSkillTags .skill-tag')).toHaveCount(0);
  await page.locator('#cronFormSkillSearch').fill(skill);await page.locator('#cronFormSkillDropdown .skill-opt').filter({hasText:skill}).click();
  const created=await save(page);id=created.id;expect(created).toMatchObject({profile:'qa-research',model:'qa-deterministic',provider:'custom:qa',skills:[skill]});
  await reopen(page,name);await expect(page.locator('#cronFormProfile')).toHaveValue('qa-research');await expect(model).toHaveValue(value!);
  await expect(page.locator('#cronFormSkillSearch')).toBeDisabled();await expect(page.locator('#cronFormSkillTags')).toContainText(skill);
  await page.locator('#btnCancelTaskDetail').click();await page.locator('#btnRunTaskDetail').click();
  await expect.poll(async()=> (await api(page,'/api/crons/history?job_id='+id)).body.total,{timeout:60_000}).toBe(1);
  await expect.poll(async()=> (await job(page,id)).last_status).toBe('ok');
  const rows=receipts().filter(row=>!row.review&&String(row.last_user_text).includes('QA_CRON_TARGET_SKILL'));
  expect(rows).toHaveLength(1);expect(rows[0].request_model).toBe('qa-deterministic');expect(rows[0].last_user_text).not.toContain('QA_CRON_WRONG_PROFILE_SKILL');
  const history=(await api(page,'/api/crons/history?job_id='+id)).body;
  const output=await api(page,'/api/crons/run?job_id='+id+'&filename='+encodeURIComponent(history.runs[0].filename));
  expect(output.body.content).toContain('RESEARCH QA_REPLY: '+marker);
  await expect(page.locator('#cronDetailRuns .detail-run-item')).toHaveCount(1,{timeout:15000});await page.locator('#cronDetailRuns .detail-run-head').click();
  await expect(page.locator('#cronDetailRuns .cron-run-pre')).toContainText('RESEARCH QA_REPLY: '+marker);
  await info.attach('cron-selected-runtime-receipt',{body:JSON.stringify({job:await job(page,id),provider:rows,output:output.body}),contentType:'application/json'});
  await remove(page,id);id='';
 }finally{
  if(id)expect((await api(page,'/api/crons/delete',{job_id:id})).status).toBe(200);
  for(const directory of skillPaths)fs.rmSync(directory,{recursive:true});
 }
});
