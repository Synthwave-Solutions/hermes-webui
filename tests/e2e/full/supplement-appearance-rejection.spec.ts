import {test, expect, open, api, auth} from './fixtures';

test('SUPPLEMENT APPEARANCE rejected automatic preference sync preserves local rendering without uncaught promises', async ({page, context}) => {
  await open(page,'governance');await page.locator('[data-gov-tab="users"]').click();
  const email='climcp@example.test', original=(await api(page,'/api/governance/users')).body.users[email];
  await page.locator('#govPaneUsers tr').filter({hasText:email}).getByRole('button',{name:'Edit',exact:true}).click();
  await page.locator('details.gov-access-details').nth(1).locator('summary').click();
  await page.locator('#govUserDenySettingsWriteInput').fill('appearance');await page.locator('#govUserDenySettingsWriteInput').press('Enter');await page.locator('#govUserDenySettingsWriteInput').press('Escape');
  const saved=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/governance/users/update'&&r.request().method()==='POST');await page.locator('#govUserSave').click();expect((await saved).status()).toBe(200);
  try {
    await context.addCookies([{name:auth.cookie_name,value:auth.cookies.climcp,url:auth.base_url,httpOnly:true,sameSite:'Lax'}]);
    const baseline=(await api(page,'/api/settings')).body;
    const skin=baseline.skin==='verdigris'?'ares':'verdigris',font=baseline.font_size==='xlarge'?'small':'xlarge';
    await page.evaluate(({skin,font})=>{localStorage.setItem('hermes-theme','dark');localStorage.setItem('hermes-skin',skin);localStorage.setItem('hermes-font-size',font);},{skin,font});
    const writes: {status:number;keys:string[]}[]=[];
    page.on('response', r => {
      if(new URL(r.url()).pathname==='/api/settings' && r.request().method()==='POST')writes.push({status:r.status(),keys:Object.keys(r.request().postDataJSON()).sort()});
    });
    await open(page);
    await expect.poll(() => writes).toEqual(expect.arrayContaining([{status:403,keys:['skin','theme']},{status:403,keys:['font_size']}]));
    await expect(page.locator('html')).toHaveAttribute('data-skin',skin);await expect(page.locator('html')).toHaveAttribute('data-font-size',font);
    const settings=await api(page,'/api/settings');expect(settings.status).toBe(200);
    expect(settings.body.skin).toBe(baseline.skin);expect(settings.body.font_size).toBe(baseline.font_size);
    await page.locator('#msg').fill('An unsent draft still works after a denied preference update.');await expect(page.locator('#msg')).toHaveValue('An unsent draft still works after a denied preference update.');
    await page.reload();await expect.poll(()=>writes.length).toBe(4);
    await expect(page.locator('html')).toHaveAttribute('data-skin',skin);await expect(page.locator('html')).toHaveAttribute('data-font-size',font);
  } finally {
    await context.addCookies([{name:auth.cookie_name,value:auth.cookies.admin,url:auth.base_url,httpOnly:true,sameSite:'Lax'}]);
    await open(page);
    const current=await api(page,'/api/governance/users');
    const status=await page.evaluate(async({etag,email,entry})=>{const r=await fetch('/api/governance/users/update',{method:'POST',headers:{'Content-Type':'application/json','If-Match':etag},body:JSON.stringify({email,entry})});return r.status;},{etag:current.body.etag,email,entry:original});expect(status).toBe(200);
  }
});
