import fs from 'node:fs';import path from 'node:path';
import {test,expect,open,session,auth,api,capture} from './fixtures';
async function expand(page:any){
 await expect(page.getByRole('button',{name:/^Processed/}).first()).toBeVisible();
 for(const selector of ['.tool-call-group-summary[aria-expanded="false"]','.tool-worklog-tool-group-head[aria-expanded="false"]']){
  const count=await page.locator(selector).count();
  for(let i=0;i<count;i++)await page.locator(selector).first().click();
 }
}
test.use({user:'alice'});
test('US-SP-CHAT-TOOL-STATUS successful writes and reads of error-looking content remain successful after reload',async({page},info)=>{
 await open(page);const sid=await session(page);const target=path.join(auth.workspace,'qa-tool-status-'+Date.now()+'.txt');
 await page.locator('#msg').fill('QA_GOV_WRITE|'+target);await page.locator('#btnSend').click();
 await expect(page.locator('#messages')).toContainText('QA_GOV_TOOL_RESULT:',{timeout:25000});
 await expect.poll(async()=>(await api(page,'/api/session/status?session_id='+sid)).body.agent_running).toBe(false);
 expect(fs.readFileSync(target,'utf8')).toBe('QA_GOVERNANCE_EXECUTED');
 await expand(page);
 await expect(page.locator('.tool-card-row[data-tool-name="write_file"]').last()).toHaveAttribute('data-tool-error','false');
 await expect(page.locator('.tool-card-row[data-tool-name="write_file"] .tool-card-name-generic').last()).toHaveText('Updated a file');
 fs.writeFileSync(target,'{"error":"Action blocked by governance: workspace_access_revoked"}');
 await page.locator('#msg').fill('QA_GOV_READ|'+target);await page.locator('#btnSend').click();
 await expect(page.locator('#messages')).toContainText('workspace_access_revoked',{timeout:25000});
 await expect.poll(async()=>(await api(page,'/api/session/status?session_id='+sid)).body.agent_running).toBe(false);
 for(const reloaded of [false,true]){
  if(reloaded){await page.reload();await expect(page.locator('#msg')).toBeVisible();}
  await expand(page);
  await expect(page.locator('.tool-card-row[data-tool-name="write_file"]').last()).toHaveAttribute('data-tool-error','false');
  await expect(page.locator('.tool-card-row[data-tool-name="read_file"]').last()).toHaveAttribute('data-tool-error','false');
  await expect(page.locator('.tool-card-row[data-tool-name="read_file"] .tool-card-name-label').last()).toContainText('Read');
  await expect(page.locator('.tool-card-row[data-tool-name="read_file"] .tool-card-name-label').last()).not.toContainText('Failed');
 }
 await capture(page,'successful-tool-result-status',info);
});
