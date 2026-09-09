import fs from 'node:fs';
import {test,expect,open,session,api,auth,capture} from './fixtures';

test('US-SP-CHAT-ATTACH actual text attachments remove one upload exact bytes and persist transcript',async({page},info)=>{
  await open(page);const sid=await session(page);const name='qa-attached-'+Date.now()+'.txt';const bytes='Synthetic attachment bytes.\nSecond line.';
  await page.locator('#fileInput').setInputFiles([{name,mimeType:'text/plain',buffer:Buffer.from(bytes)},{name:'qa-removed.txt',mimeType:'text/plain',buffer:Buffer.from('must not upload')}]);
  await expect(page.locator('#attachTray .attach-chip')).toHaveCount(2);
  await page.locator('#attachTray .attach-chip').filter({hasText:'qa-removed.txt'}).getByRole('button').click();
  await expect(page.locator('#attachTray .attach-chip')).toHaveCount(1);
  const uploaded=page.waitForResponse(r=>r.url().endsWith('/api/upload')&&r.request().method()==='POST');
  await page.locator('#msg').fill('QA_ATTACHMENT');await page.locator('#btnSend').click();const response=await uploaded;expect(response.status()).toBe(200);
  const body=await response.json();expect(fs.readFileSync(body.path,'utf8')).toBe(bytes);
  await expect(page.locator('#messages')).toContainText('QA_REPLY: QA_ATTACHMENT',{timeout:30000});
  await expect(page.locator('#attachTray .attach-chip')).toHaveCount(0);
  expect(JSON.stringify((await api(page,'/api/session?session_id='+sid)).body.session.messages)).toContain(name);
  await page.reload();await expect(page.locator('#messages')).toContainText(name);await expect(page.locator('#messages')).not.toContainText('qa-removed.txt');
  await capture(page,'attachment-after-reload',info);
});

test('US-SP-CHAT-EDIT actual cancel edit resubmit and regenerate preserve one edited user turn after reload',async({page},info)=>{
  await open(page);const sid=await session(page);await page.locator('#msg').fill('QA_BEFORE_EDIT');await page.locator('#btnSend').click();
  await expect(page.locator('#messages')).toContainText('QA_REPLY: QA_BEFORE_EDIT',{timeout:30000});
  await expect.poll(async()=>(await api(page,'/health')).body.active_runs||0).toBe(0);
  await page.getByRole('button',{name:'Edit message',exact:true}).click();await page.locator('.msg-edit-area').fill('QA_CANCELLED_EDIT');await page.locator('.msg-edit-cancel').click();
  await expect(page.locator('#messages')).toContainText('QA_BEFORE_EDIT');expect(JSON.stringify((await api(page,'/api/session?session_id='+sid)).body.session.messages)).not.toContain('QA_CANCELLED_EDIT');
  await page.getByRole('button',{name:'Edit message',exact:true}).click();await page.locator('.msg-edit-area').fill('QA_AFTER_EDIT');await page.locator('.msg-edit-send').click();
  await expect(page.locator('#messages')).toContainText('QA_REPLY: QA_AFTER_EDIT',{timeout:30000});await expect(page.locator('#messages')).not.toContainText('QA_BEFORE_EDIT');
  await expect.poll(async()=>(await api(page,'/health')).body.active_runs||0).toBe(0);
  const regenerated=page.waitForResponse(r=>r.url().endsWith('/api/chat/start')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Regenerate response',exact:true}).click();expect((await regenerated).status()).toBe(200);
  await expect.poll(async()=>(await api(page,'/health')).body.active_runs||0).toBe(0);
  await page.reload();await expect(page.locator('#messages')).toContainText('QA_REPLY: QA_AFTER_EDIT');
  const messages=(await api(page,'/api/session?session_id='+sid)).body.session.messages;
  expect(messages.filter((m:any)=>m.role==='user')).toHaveLength(1);expect(JSON.stringify(messages)).not.toContain('QA_BEFORE_EDIT');
  await capture(page,'edit-regenerate-reload',info);
});

test('US-SP-CHAT-PROMPTS saved prompt validates empty input saves reloads inserts exact text and deletes',async({page},info)=>{
  await open(page);const sid=await session(page);await page.locator('#btnSavedPrompts').click();await page.locator('.saved-prompt-save-btn').click();
  await expect(page.locator('#toast.error.show')).toContainText(/prompt|input/i);await page.locator('#toast .toast-dismiss').click();await page.locator('#btnSavedPrompts').click();
  const prompt='QA saved prompt '+Date.now()+'\nSecond line';await page.locator('#msg').fill(prompt);await page.locator('#btnSavedPrompts').click();await page.locator('.saved-prompt-save-btn').click();
  await expect(page.locator('#savedPromptsPopup')).toBeHidden();await expect.poll(async()=>(await api(page,'/api/session?session_id='+sid)).body.session.composer_draft?.text).toBe(prompt);await page.reload();await expect(page.locator('#msg')).toHaveValue(prompt);await page.locator('#msg').fill('');await page.locator('#btnSavedPrompts').click();
  const row=page.locator('.saved-prompt-row').filter({hasText:'QA saved prompt'});await expect(row).toHaveCount(1);await row.click();await expect(page.locator('#msg')).toHaveValue(prompt+'\n\n');
  await page.locator('#btnSavedPrompts').click();await row.locator('.saved-prompt-delete').click();await expect(row).toHaveCount(0);
  expect(JSON.stringify((await api(page,'/api/prompts')).body)).not.toContain(prompt);await page.reload();await page.locator('#btnSavedPrompts').click();await expect(page.locator('.saved-prompt-row').filter({hasText:'QA saved prompt'})).toHaveCount(0);await capture(page,'saved-prompt-deleted',info);
});
