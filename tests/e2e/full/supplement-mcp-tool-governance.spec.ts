import fs from 'node:fs';
import path from 'node:path';
import type {Page, BrowserContext} from '@playwright/test';
import {test, expect, open, api, auth, session, capture} from './fixtures';

const email='climcp@example.test';
const unique=(name:string)=>`qa-mcp-${name}-${Date.now()}-${Math.random().toString(16).slice(2,7)}`;
async function chip(page:Page,id:string,value:string){
 const input=page.locator('#'+id+'Input');await input.fill(value);await input.press('Enter');await input.press('Escape');
}
async function users(page:Page){await open(page,'governance');await page.locator('[data-gov-tab="users"]').click();}
async function edit(page:Page,target=email){await users(page);await page.locator('#govPaneUsers tr').filter({hasText:target}).getByRole('button',{name:'Edit',exact:true}).click();}
async function save(page:Page){
 const pending=page.waitForResponse(r=>/\/api\/governance\/users(?:\/update)?$/.test(new URL(r.url()).pathname)&&r.request().method()==='POST');
 await page.locator('#govUserSave').click();const r=await pending;expect(r.status(),await r.text()).toBe(200);await expect(page.locator('#govUserEmail')).toHaveValue('');
}
async function stored(page:Page,target=email){const r=await api(page,'/api/governance/users');expect(r.status).toBe(200);return r.body.users[target];}
async function as(page:Page,context:BrowserContext,user:string){await context.addCookies([{name:auth.cookie_name,value:auth.cookies[user],url:auth.base_url,httpOnly:true,sameSite:'Lax'}]);await open(page);}
async function rule(page:Page,id:string,server:string,names:string[]){
 await page.locator('#'+id+'Add').click();const row=page.locator('#'+id+' [data-mcp-tool-rule]').last();
 await row.locator('[data-mcp-tool-server]').fill(server);
 const input=row.locator('input[id$="Input"]');
 for(const name of names){await input.fill(name);await input.press('Enter');await input.press('Escape');}
 return row;
}
async function enabled(page:Page,value:boolean){
 await open(page,'settings');await page.locator('[data-settings-section="system"]').click();
 const row=page.locator('.mcp-server-row').filter({has:page.locator('.mcp-server-name',{hasText:'qa-stdio'})});await expect(row).toBeVisible();
 const current=(await api(page,'/api/mcp/servers')).body.servers.find((x:any)=>x.name==='qa-stdio');
 if(current.enabled!==value){const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/mcp/servers/qa-stdio'&&r.request().method()==='PATCH');await row.locator('.mcp-toggle-btn').click();expect((await response).status()).toBe(200);}
 await page.locator('.rail-btn[data-panel="chat"]').click();await session(page);await page.locator('#msg').fill('/reload-mcp');await page.locator('#btnSend').click();await expect(page.locator('#messages')).toContainText('Reloaded MCP servers from configuration.',{timeout:30000});
}
function effects(marker:string){const file=path.join(auth.workspace,'qa-mcp-effects.jsonl');return fs.existsSync(file)?fs.readFileSync(file,'utf8').split('\n').filter(Boolean).map(x=>JSON.parse(x)).filter(x=>x.marker===marker):[];}
async function invoke(page:Page,marker:string){
 await page.setViewportSize({width:1920,height:1080});
 const sid=await session(page);await page.locator('#chatModeSuper').click();
 // Session toolset activation is environment setup; all user governance
 // grants and denies above are entered through the real Users form.
 expect((await api(page,'/api/session/toolsets',{session_id:sid,toolsets:['mcp-qa-stdio']})).status).toBe(200);
 await page.locator('#msg').fill('QA_SUPPLEMENT_MCP|'+marker);await page.locator('#btnSend').click();return sid;
}
async function done(page:Page,sid:string){await expect(page.locator('#messages')).toContainText('QA_SUPPLEMENT_TOOL_RESULT:',{timeout:45000});await expect.poll(async()=>(await api(page,'/api/session/status?session_id='+sid)).body.agent_running).toBe(false);}
async function restore(page:Page,entry:any){
 const current=await api(page,'/api/governance/users');
 const status=await page.evaluate(async({etag,entry,email,endpoint})=>{const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json','If-Match':etag},body:JSON.stringify({email,entry})});return r.status;},{etag:current.body.etag,entry,email,endpoint:current.body.users[email]?'/api/governance/users/update':'/api/governance/users'});expect(status).toBe(200);
}

test('SUPPLEMENT MCP TOOL GOVERNANCE complete Users onboarding allows one real tool then local and canonical explicit denies block wildcard dispatch',async({page,context},info)=>{
 test.setTimeout(180000);await users(page);const original=await stored(page);
 try{
  await enabled(page,true);await users(page);
  const deleted=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/governance/users/delete');
  await page.locator('#govPaneUsers tr').filter({hasText:email}).getByRole('button',{name:'Delete',exact:true}).click();expect((await deleted).status()).toBe(200);await expect(page.locator('#govPaneUsers tr').filter({hasText:email})).toHaveCount(0);
  // The signed identity already exists, but its entire user policy is entered
  // from the visible form. Only the surrounding role ceiling is fixture setup.
  await page.locator('#govUserEmail').fill(email);
  await chip(page,'govUserRolesSel','member');await chip(page,'govUserRolesSel','qa_cli_mcp');
  await page.locator('#govUserAccessLevel').selectOption('elevated');
  await page.locator('#govUserAccessMode').selectOption('whitelist');await page.locator('#govUserApprovalMode').selectOption('manual');
  await chip(page,'govUserMcpServers','qa-stdio');await rule(page,'govUserMcpTools','qa-stdio',['qa_mark']);
  await page.locator('details.gov-access-details').first().locator('summary').click();
  for(const [field,value] of [['Permissions','*'],['Profiles','*'],['Routes','*'],['Workspaces',auth.workspace],['Models','*'],['Providers','*'],['FilesRead',auth.workspace],['FilesWrite',auth.workspace],['Workdirs',auth.workspace]])await chip(page,'govUserGrant'+field,value);
  await save(page);await page.reload();await edit(page);
  expect((await stored(page)).grants.mcp).toEqual({servers:['qa-stdio'],tools:{'qa-stdio':['qa_mark']}});
  await expect(page.locator('#govUserMcpTools [data-mcp-tool-server]')).toHaveValue('qa-stdio');await expect(page.locator('#govUserMcpTools .gov-chip-item')).toContainText('qa_mark');
  await capture(page,'mcp-user-onboarding-visible-rule',info);
  await as(page,context,'climcp');const allowed=unique('allowed').toUpperCase().replace(/-/g,'_');const sid=await invoke(page,allowed);
  await expect(page.locator('#approvalCard')).toBeVisible({timeout:30000});expect(effects(allowed)).toEqual([]);
  await page.locator('#approvalBtnOnce').click();await done(page,sid);expect(effects(allowed)).toHaveLength(1);
  await expect(page.locator('#messages')).toContainText('QA_MCP_EXECUTED:'+allowed);
  for(const name of ['qa_mark','mcp__qa_stdio__qa_mark']){
   await as(page,context,'admin');await edit(page);
   await page.locator('#govUserMcpTools .gov-chip-x').click();const allowInput=page.locator('#govUserMcpTools input[id$="Input"]');await allowInput.fill('*');await allowInput.press('Enter');await allowInput.press('Escape');
   const rows=page.locator('#govUserDenyMcpTools [data-mcp-tool-rule]');if(await rows.count())await rows.locator('[data-mcp-tool-remove]').click();
   await rule(page,'govUserDenyMcpTools','qa-stdio',[name]);await save(page);await page.reload();
   const entry=await stored(page);expect(entry.grants.mcp.tools['qa-stdio']).toEqual(['*']);expect(entry.deny.mcp.tools['qa-stdio']).toEqual([name]);
   await as(page,context,'climcp');const marker=unique('denied').toUpperCase().replace(/-/g,'_');const deniedSid=await invoke(page,marker);await done(page,deniedSid);
   await expect(page.locator('#approvalCard')).toBeHidden();expect(effects(marker)).toEqual([]);
   await expect(page.locator('#messages')).toContainText(/mcp_tool_denied|not.available|not.allowed|blocked|denied/i);
   expect((await api(page,'/api/approval/pending?session_id='+deniedSid)).body.pending).toBeNull();
  }
 }finally{await as(page,context,'admin');await restore(page,original);await enabled(page,false);}
});

test('SUPPLEMENT MCP TOOL GOVERNANCE Groups rule creation validation removal and untouched user legacy maps round trip',async({page})=>{
 test.setTimeout(90000);const name=unique('group');await open(page,'governance');await page.locator('[data-gov-tab="groups"]').click();
 await page.getByRole('button',{name:'+ Add group',exact:true}).click();await page.locator('#govGroupName').fill(name);await page.locator('#govGroupRoles').fill('member');
 await chip(page,'govGroupMcpServers','qa-stdio');await rule(page,'govGroupMcpTools','qa-stdio',['qa_mark']);
 const duplicate=await rule(page,'govGroupMcpTools','qa-stdio',['qa_read']);await page.locator('[onclick="_govSaveGroup()"]').click();await expect(page.locator('#toast')).toContainText('Use one tool rule per server');
 expect((await api(page,'/api/governance/groups')).body.groups[name]).toBeUndefined();await duplicate.locator('[data-mcp-tool-remove]').click();
 const saved=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/governance/groups'&&r.request().method()==='POST');await page.locator('[onclick="_govSaveGroup()"]').click();expect((await saved).status()).toBe(200);await page.reload();await open(page,'governance');await page.locator('[data-gov-tab="groups"]').click();
 const card=page.locator('.gov-group-card').filter({hasText:name});await card.getByRole('button',{name:'Edit',exact:true}).click();
 expect((await api(page,'/api/governance/groups')).body.groups[name].grants.mcp.tools).toEqual({'qa-stdio':['qa_mark']});
 await expect(page.locator('#govGroupMcpTools [data-mcp-tool-server]')).toHaveValue('qa-stdio');
 await page.locator('#govGroupMcpTools [data-mcp-tool-remove]').click();const changed=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/governance/groups/update');await page.locator('[onclick="_govSaveGroup()"]').click();expect((await changed).status()).toBe(200);
 expect((await api(page,'/api/governance/groups')).body.groups[name].grants.mcp).toEqual({servers:['qa-stdio']});
 const removed=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/governance/groups/delete');await card.getByRole('button',{name:'Delete',exact:true}).click();expect((await removed).status()).toBe(200);
 const legacyEmail=unique('legacy')+'@example.test';await users(page);const snapshot=await api(page,'/api/governance/users');
 const entry={roles:['member'],groups:[],grants:{mcp:{servers:['qa-stdio'],tools:{'qa-stdio':'qa_mark','other':['read','write']}}},deny:{mcp:{tools:{'blocked':'destroy'}}}};
 const status=await page.evaluate(async({etag,email,entry})=>{const r=await fetch('/api/governance/users',{method:'POST',headers:{'Content-Type':'application/json','If-Match':etag},body:JSON.stringify({email,entry})});return r.status;},{etag:snapshot.body.etag,email:legacyEmail,entry});expect(status).toBe(200);
 await edit(page,legacyEmail);await save(page);expect(await stored(page,legacyEmail)).toEqual(entry);
 await edit(page,legacyEmail);
 // The controls use DOM values, not persisted HTML attributes.
 const first=page.locator('#govUserMcpTools [data-mcp-tool-rule]').first();await first.locator('.gov-chip-x').click();await first.locator('input[id$="Input"]').fill('qa_other');await first.locator('input[id$="Input"]').press('Enter');await first.locator('input[id$="Input"]').press('Escape');await save(page);
 const edited=await stored(page,legacyEmail);expect(edited.grants.mcp.tools).toEqual({'qa-stdio':['qa_other'],other:['read','write']});expect(edited.deny.mcp.tools).toEqual(entry.deny.mcp.tools);
});
