import {test,expect,capture} from './fixtures';

for(const [panel,control,endpoint,status] of [
 ['approvals','#btnMyApprovalsRefresh','/api/governance/approvals/mine',200],
 ['integrations','#mainIntegrations [onclick="loadIntegrations()"]','/api/integrations/catalog',502],
] as const){
 test('US-SP-UX-MOBILE '+panel+' hamburger navigation allows actual main refresh control',async({page},info)=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/');await expect(page.locator('#msg')).toBeVisible();
  await page.locator('#btnHamburger').click();await page.locator('.sidebar [data-panel="'+panel+'"]').click();
  const response=page.waitForResponse(r=>r.url().includes(endpoint)&&r.request().method()==='GET');
  await page.locator(control).click();expect((await response).status()).toBe(status);
  if(panel==='integrations') await expect(page.locator('#intgGrid .intg-error')).toContainText('Nango providers.yaml is not readable');
  await expect(page.locator('.sidebar')).not.toHaveClass(/mobile-open/);await capture(page,'mobile-'+panel+'-refreshed',info);
 });
}
