import { test, expect, open, api, auth } from './fixtures';

test('US-SP-POL-RESOURCE resource denials saved in frontend block real named skill settings and model API bypasses', async ({page,browser,errors},info) => {
  expect(errors).toEqual([]);
  await open(page,'governance');
  // This seeded member is exclusively owned by this test. Every restriction,
  // including skill-management denial, is set through the rendered editor.
  await page.locator('[data-gov-tab="users"]').click();
  await page.locator('#govPaneUsers tr').filter({hasText:'resource@example.test'}).getByRole('button',{name:'Edit',exact:true}).click();
  await page.locator('#govUserDenySkillsInput').fill('qa-review');await page.locator('#govUserDenySkillsInput').press('Enter');
  await page.locator('#govUserDenySkillsManageInput').fill('qa-review');await page.locator('#govUserDenySkillsManageInput').press('Enter');
  await page.locator('details.gov-access-details').nth(1).locator('summary').click();
  for(const [field,value] of [['SettingsRead','theme'],['SettingsWrite','appearance'],['Models','qa-deterministic'],['Providers','custom:qa']]){
    const input=page.locator('#govUserDeny'+field+'Input');await input.fill(value);await input.press('Enter');
  }
  const save=page.waitForResponse(r=>/\/api\/governance\/users(?:\/update)?$/.test(r.url())&&r.request().method()==='POST');
  await page.locator('#govUserSave').click();expect((await save).status()).toBe(200);
  await expect(page.locator('#govUserEmail')).toHaveValue('');
  const saved=(await api(page,'/api/governance/users')).body.users['resource@example.test'];
  expect(saved.deny.skills.manage).toEqual(['qa-review']);expect(saved.deny.models.providers).toEqual(['custom:qa']);
  const originalSkill=await api(page,'/api/skills/content?name=qa-review');expect(originalSkill.status).toBe(200);
  const originalSettings=await api(page,'/api/settings');expect(originalSettings.status).toBe(200);
  const originalModels=await api(page,'/api/models');expect(originalModels.status).toBe(200);
  const member=await browser.newContext({baseURL:auth.base_url});
  try {
    await member.addCookies([{name:auth.cookie_name,value:auth.cookies.resource,url:auth.base_url}]);
    const p=await member.newPage();const memberErrors:string[]=[];p.on('pageerror',e=>memberErrors.push(e.message));
    await p.goto('/');await expect(p.locator('#msg')).toBeVisible();
    await p.locator('.rail-btn[data-panel="skills"]').click();
    await expect(p.locator('#skillsList')).not.toContainText('qa-review');
    const results:any[]=[];
    for(const [url,body] of [
      ['/api/skills/content?name=qa-review',undefined],
      ['/api/skills/content?name=qa-review&file=SKILL.md',undefined],
      ['/api/skills/save',{name:'QA Review',content:'QA_FORBIDDEN_WRITE'}],
      ['/api/skills/delete',{name:'qa-review'}],
      ['/api/skills/toggle',{name:'qa-review',enabled:false}],
      ['/api/settings',{theme:'light'}],
      ['/api/default-model',{model:'qa-deterministic',provider:'custom:qa'}],
      ['/api/model/set',{scope:'auxiliary',task:'title_generation',model:'qa-deterministic',provider:'custom:qa'}],
      ['/api/models/live?provider=custom%3Aqa',undefined],
      ['/api/models/refresh',{provider:'custom:qa'}],
    ] as [string,any][]){const r=await api(p,url,body);results.push({url,status:r.status,reason:r.body.reason});expect(r.status,url).toBe(403);}
    const skills=await api(p,'/api/skills');expect(skills.status).toBe(200);expect(skills.body.skills.some((s:any)=>s.name==='qa-review')).toBe(false);
    const settings=await api(p,'/api/settings');expect(settings.status).toBe(200);expect(settings.body).not.toHaveProperty('theme');
    const models=await api(p,'/api/models');expect(models.status).toBe(200);expect(JSON.stringify(models.body)).not.toContain('qa-deterministic');
    expect((await api(page,'/api/skills/content?name=qa-review')).body).toEqual(originalSkill.body);
    expect((await api(page,'/api/settings')).body.theme).toEqual(originalSettings.body.theme);
    expect((await api(page,'/api/models')).body.default_model).toEqual(originalModels.body.default_model);
    expect(memberErrors,'restricted browser uncaught errors').toEqual([]);
    await info.attach('resource-denial-http-outcomes',{body:JSON.stringify(results,null,2),contentType:'application/json'});
  } finally {await member.close();}
});
