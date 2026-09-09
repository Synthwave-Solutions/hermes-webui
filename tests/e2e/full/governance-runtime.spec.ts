import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {test,expect,open,session,auth,api,capture} from './fixtures';
async function requestWrite(page:any,label:string){await open(page);const sid=await session(page);const target=path.join(auth.workspace,'qa-governance-'+label+'-'+Date.now()+'.txt');expect(fs.existsSync(target)).toBe(false);await page.locator('#msg').fill('QA_GOV_WRITE|'+target);await page.locator('#btnSend').click();return {sid,target};}
async function settled(page:any){await expect(page.locator('#messages')).toContainText('QA_GOV_TOOL_RESULT:',{timeout:35000});}
async function audited(sid:string,user:string,decision:string,source:string,info:any){
 const file=path.join(path.dirname(path.resolve(process.env.QA_SESSIONS||'../e2e-state/browser-sessions.json')),'home','dashboard-governance-audit.jsonl');
 let row:any;
 await expect.poll(()=>{const rows=fs.readFileSync(file,'utf8').trim().split('\n').filter(Boolean).map(s=>JSON.parse(s));row=rows.find(r=>r.event==='action_approval'&&r.extra?.session_id===sid);return !!row;}).toBe(true);
 expect(row.extra).toMatchObject({decision,source,tool:'write_file',session_id:sid});expect(row.extra.policy_revision).toMatch(/^[a-f0-9]{64}$/);expect(row.extra.operation_id).toMatch(/^[a-f0-9]{32}$/);expect(row.reason.trim().length).toBeGreaterThan(0);expect(row.subject_email_hash).toBe(crypto.createHash('sha256').update(user+'@example.test').digest('hex').slice(0,24));
 await info.attach('persisted-governance-audit',{body:JSON.stringify(row,null,2),contentType:'application/json'});
}
for(const [user,allowed] of [['autoapprove',true],['autodeny',false]] as const)test.describe(user,()=>{
 test.use({user});test(`US-SP-POL-RUNTIME-${user} actual model decision ${allowed?'allows':'blocks'} actual tool effect`,async({page},info)=>{
  const {target,sid}=await requestWrite(page,user);await settled(page);expect(fs.existsSync(target)).toBe(allowed);if(allowed)expect(fs.readFileSync(target,'utf8')).toBe('QA_GOVERNANCE_EXECUTED');else await expect(page.locator('#messages')).toContainText(/denied|blocked|not approved|policy/i);await expect(page.locator('#approvalCard')).toBeHidden();await audited(sid,user,allowed?'approve':'deny','automatic',info);await capture(page,user,info);
 });
});
for(const [user,choice] of [['manualapprove','once'],['manualdeny','deny'],['automanual','once']] as const)test.describe(user,()=>{
 test.use({user});test(`US-SP-POL-RUNTIME-${user} parked action waits for real frontend ${choice} decision`,async({page},info)=>{
  const {target,sid}=await requestWrite(page,user);await expect(page.locator('#approvalCard')).toBeVisible({timeout:25000});expect(fs.existsSync(target)).toBe(false);await expect(page.locator('#approvalBtnSession')).toBeHidden();await expect(page.locator('#approvalBtnAlways')).toBeHidden();await expect(page.locator('#approvalSkipAll')).toBeHidden();await capture(page,'pending-action-'+user,info);
  await page.locator(choice==='once'?'#approvalBtnOnce':'#approvalBtnDeny').click();await settled(page);expect(fs.existsSync(target)).toBe(choice==='once');if(choice==='once')expect(fs.readFileSync(target,'utf8')).toBe('QA_GOVERNANCE_EXECUTED');await expect(page.locator('#approvalCard')).toBeHidden();
  await audited(sid,user,choice==='once'?'approve':'deny','manual',info);
 });
});
