import {test, expect, open, session, api, auth, capture} from './fixtures';

async function create(page:any, marker:string) {
  await open(page); const sid=await session(page);
  await page.locator('#msg').fill(marker); await page.locator('#btnSend').click();
  await expect(page.locator('#messages')).toContainText('QA_REPLY: '+marker.replace(/\d+$/,''),{timeout:30000});
  await expect.poll(async()=>(await api(page,'/health')).body.active_runs||0).toBe(0);
  return sid;
}
async function menu(page:any,sid:string) {
  const row=page.locator('.session-item[data-sid="'+sid+'"]');
  await row.hover(); await row.locator('.session-actions-trigger').click();
  await expect(page.locator('.session-action-menu')).toBeVisible();
}

test('US-SP-SESS-DISCOVERY rename Enter and Escape plus title content and URL search select persisted conversation',async({page},info)=>{
  const marker='QA_SEARCH_BODY_'+Date.now(); const sid=await create(page,marker);
  const name='QA renamed '+Date.now();
  await menu(page,sid); await page.getByRole('menuitem',{name:'Rename conversation',exact:true}).click();
  await page.locator('.session-title-input').fill(name); await page.locator('.session-title-input').press('Enter');
  await expect.poll(async()=>(await api(page,'/api/session?session_id='+sid)).body.session.title).toBe(name);
  await menu(page,sid); await page.getByRole('menuitem',{name:'Rename conversation',exact:true}).click();
  await page.locator('.session-title-input').fill('QA cancelled rename'); await page.locator('.session-title-input').press('Escape');
  expect((await api(page,'/api/session?session_id='+sid)).body.session.title).toBe(name);
  await page.reload(); await expect(page.locator('.session-item[data-sid="'+sid+'"]')).toContainText(name);
  for(const query of [name,marker,auth.base_url+'/session/'+sid]) {
    await page.locator('#sessionSearch').fill(query);
    const row=page.locator('.session-item[data-sid="'+sid+'"]'); await expect(row).toBeVisible();
    await row.click(); await expect(page.locator('#messages')).toContainText(marker);
    await page.locator('#sessionSearchClear').click(); await expect(page.locator('#sessionSearch')).toHaveValue('');
  }
  await page.locator('#sessionSearch').fill('QA_NO_MATCH_'+Date.now());
  await expect(page.locator('.session-item')).toHaveCount(0);
  await page.locator('#sessionSearchClear').click(); await expect(page.locator('.session-item[data-sid="'+sid+'"]')).toBeVisible();
  await capture(page,'conversation-discovery',info);
});

test('US-SP-SESS-ARCHIVE archive reload show archived and restore preserve authoritative transcript',async({page},info)=>{
  const marker='QA_ARCHIVE_'+Date.now(); const sid=await create(page,marker);
  await menu(page,sid); await page.getByRole('menuitem',{name:'Archive conversation',exact:true}).click();
  await expect.poll(async()=>(await api(page,'/api/session?session_id='+sid)).body.session.archived).toBe(true);
  await page.reload(); await expect(page.locator('.session-item[data-sid="'+sid+'"]')).toHaveCount(0);
  await page.getByText(/^Show \d+ archived$/).click();
  await expect(page.locator('.session-item[data-sid="'+sid+'"]')).toBeVisible();
  await menu(page,sid); await page.getByRole('menuitem',{name:'Restore conversation',exact:true}).click();
  await expect.poll(async()=>(await api(page,'/api/session?session_id='+sid)).body.session.archived).toBe(false);
  await page.reload(); await page.locator('.session-item[data-sid="'+sid+'"] .session-title').click();
  await expect(page.locator('#messages')).toContainText(marker);
  await capture(page,'conversation-restored',info);
});

test('US-SP-SESS-SHARE create public snapshot read anonymously cancel revoke then revoke invalidates public link',async({page,browser},info)=>{
  const marker='QA_SHARE_'+Date.now(); const sid=await create(page,marker);
  await page.locator('.rail-btn[data-panel="settings"]').click();
  const created=page.waitForResponse(r=>r.url().endsWith('/api/share/create')&&r.request().method()==='POST');
  await page.locator('#btnShareSession').click(); const response=await created;
  // Existing candidate defect: the rendered Share action currently returns404.
  // Keep this as a failing acceptance check until the endpoint is restored or
  // the product explicitly removes the unsupported feature; never skip it.
  expect(response.status(),'rendered Share must create a real snapshot').toBe(200);
  const payload=await response.json(); const href=new URL(payload.share.url,auth.base_url).href;
  expect(href).toContain('/share/');
  const anonymous=await browser.newContext();
  try {
    const publicPage=await anonymous.newPage(); await publicPage.goto(href);
    await expect(publicPage.locator('body')).toContainText('QA_REPLY: '+marker.replace(/\d+$/,''));
    await expect(publicPage.locator('#msg')).toHaveCount(0);
    await page.locator('#btnStopSharingSession').click(); await page.locator('#appDialogCancel').click();
    expect((await anonymous.request.get(href)).status()).toBe(200);
    await page.locator('#btnStopSharingSession').click(); await page.locator('#appDialogConfirm').click();
    await expect.poll(async()=>(await api(page,'/api/session?session_id='+sid)).body.session.share_token||null).toBe(null);
    expect((await anonymous.request.get(href)).status()).toBe(404);
    const response=await publicPage.reload(); expect(response!.status()).toBe(404);
    await expect(publicPage.locator('body')).not.toContainText(marker);
    expect((await api(page,'/api/session?session_id='+sid)).body.session.messages.length).toBeGreaterThan(0);
    await capture(page,'sharing-revoked',info);
  } finally {await anonymous.close();}
});
