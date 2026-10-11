import {test,expect,open,api} from './fixtures';
async function ready(page:any){await page.waitForFunction(()=>typeof S!=='undefined'&&S._bootReady&&_loadingSessionId===null);await expect(page.locator('#btnApps')).toBeVisible();}

test.describe('organisation admin modules',()=>{
 test.use({user:'alice'});
 test('read-only catalogue, bilingual copy, responsive layouts and draft preservation',async({page},info)=>{
  await open(page);await ready(page);await page.locator('#msg').fill('QA modules draft remains unchanged');
  await page.screenshot({path:info.outputPath('modules-before-chat.png'),fullPage:true});
  await page.locator('.rail-btn[data-panel="modules"]').click();await expect(page.locator('.module-card')).toHaveCount(10);
  await expect(page.locator('[data-module-id="office_apps"]')).toContainText('Office apps with AI');
  const post:string[]=[];page.on('request',r=>{if(r.method()==='POST')post.push(r.url());});
  await page.locator('[data-module-id="knowledge_base"] summary').first().click();await expect(page.locator('[data-module-id="knowledge_base"]')).toContainText('service contact');
  await page.locator('[data-module-id="meeting_notes"] summary').last().click();await expect(page.locator('[data-module-id="meeting_notes"]')).toContainText('Only with the consent');expect(post).toEqual([]);
  for(const locale of ['nl','en'])for(const width of [390,1440]){
   await page.setViewportSize({width,height:1000});await page.locator('#mainModules select').selectOption(locale);
   await expect(page.locator('[data-module-id="office_apps"]')).toContainText(locale==='nl'?"Kantoorprogramma's met AI":'Office apps with AI');
   for(const theme of ['dark','light']){
    await page.evaluate(t=>{_applySkin('default');_applyTheme(t);document.getElementById('mainModules')!.scrollTop=0;},theme);
    expect(await page.evaluate(()=>document.documentElement.classList.contains('dark'))).toBe(theme==='dark');
    const box=await page.locator('#mainModules').evaluate(e=>({scroll:e.scrollWidth,width:e.clientWidth,right:e.getBoundingClientRect().right}));expect(box.scroll).toBeLessThanOrEqual(box.width+1);expect(box.right).toBeLessThanOrEqual(width+1);
    await page.screenshot({path:info.outputPath(`modules-${locale}-${width}-${theme}.png`),fullPage:true});
   }
  }
  await page.evaluate(()=>switchPanel('chat'));await expect(page.locator('#msg')).toHaveValue('QA modules draft remains unchanged');
  const r=await api(page,'/api/org/modules/request',{module:'notebook'});expect(r.status).toBe(503);expect(r.body.error).toBe('requests_not_connected');
 });
 test('Apps is a keyboard accessible navigation destination with role scoped links',async({page})=>{
  await open(page);await ready(page);await page.locator('#btnApps').focus();await page.keyboard.press('Enter');await expect(page.locator('#mainApps')).toBeVisible();
  const links=page.locator('#mainApps a');expect(await links.count()).toBeGreaterThan(0);
  await expect(page.locator('[data-app-id="omniroute"]')).toHaveCount(0);await expect(page.locator('[data-app-id="n8n"]')).toHaveCount(0);
  for(const link of await links.all()){await expect(link).toHaveAttribute('rel','noopener noreferrer');await expect(link).toHaveAttribute('target','_blank');}
 });
 test('failed settings fetch keeps module surfaces hidden',async({page})=>{
  await page.route('**/api/settings',route=>route.abort());await open(page);await expect(page.locator('#btnApps')).toBeHidden();await expect(page.locator('.rail-btn[data-panel="modules"]')).toBeHidden();
  await page.evaluate(()=>switchPanel('modules'));expect(await page.evaluate(()=>_currentPanel)).toBe('chat');
 });
});
test.describe('member module boundary',()=>{
 test.use({user:'bob'});
 test('member cannot read or request modules and advanced routes stay blocked',async({page})=>{
  await open(page);await ready(page);await expect(page.locator('.rail-btn[data-panel="modules"]')).toBeHidden();
  expect((await api(page,'/api/org/modules')).status).toBe(403);expect((await api(page,'/api/org/modules/request',{module:'notebook'})).status).toBe(403);
  expect((await api(page,'/api/notebook/test')).status).toBe(403);
  await page.evaluate(()=>switchPanel('modules'));expect(await page.evaluate(()=>_currentPanel)).toBe('chat');
 });
});
test.describe('platform launcher',()=>{
 test.use({user:'admin'});
 test('platform scope sees workflow app while server settings cannot activate modules',async({page})=>{
  await open(page);await ready(page);const before=await api(page,'/api/settings');
  expect((await api(page,'/api/apps')).body.apps.map((x:any)=>x.id)).toContain('n8n');
  const write=await api(page,'/api/settings',{enabled_modules:['notebook'],module_nav:{modules_visible:true},enabled_connections:['minutes_to_chat']});expect(write.status).toBe(200);
  const after=await api(page,'/api/settings');expect(after.body.enabled_modules).toEqual(before.body.enabled_modules);expect(after.body.enabled_connections).toEqual(before.body.enabled_connections);
 });
});
