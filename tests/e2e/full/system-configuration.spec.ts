import {test,expect,open,api,auth,capture,session} from './fixtures';

async function settings(page:any,section='system') {
 await open(page,'settings');
 await page.locator(`[data-settings-section="${section}"]`).click();
}
async function refused(browser:any,url:string,data:any,method='POST') {
 const context=await browser.newContext({baseURL:auth.base_url});
 try {
  await context.addCookies([{name:auth.cookie_name,value:auth.cookies.denied,url:auth.base_url}]);
  const response=await context.request.fetch(url,{method,data,headers:{Origin:auth.base_url}});
  expect(response.status(),url+' remains denied to an ungranted identity').toBe(403);
 } finally {await context.close();}
}
async function auxiliary(page:any) {
 const result=await api(page,'/api/model/auxiliary');expect(result.status).toBe(200);return result.body;
}
async function auxGear(page:any,slot:string) {
 await page.locator('#aux-model-'+slot).locator('..').locator('.aux-advanced-btn').click();
 await expect(page.locator('#auxAdvancedOverlay')).toBeVisible();
}
async function advancedSave(page:any) {
 const pending=page.waitForResponse((r:any)=>new URL(r.url()).pathname==='/api/model/set'&&r.request().method()==='POST');
 await page.locator('#auxAdvancedSave').click();expect((await pending).status()).toBe(200);
 await expect(page.locator('#auxAdvancedOverlay')).toBeHidden();
 await expect(page.locator('#aux-model-vision')).toBeVisible();
}

test('US-SP-SYSTEM-CAPACITY four capacity controls save reload sanitize and refuse an ungranted identity',async({page,browser},info)=>{
 await settings(page);await expect(page.locator('#capacityAlertsField')).toBeVisible();
 const original=(await api(page,'/api/capacity/alerts')).body.config;
 await page.locator('#capacityPollSeconds').fill('120');await page.locator('#capacityCooldownSeconds').fill('240');
 await page.locator('#capacityThresholds').fill('qa=17, invalid=140');await page.locator('#capacityDestination').fill('');
 await page.locator('#btnCapacitySave').click();await expect(page.locator('#capacityConfigStatus')).toContainText(/saved/i);
 const current=(await api(page,'/api/capacity/alerts')).body.config;
 expect(current).toMatchObject({capacity_alert_poll_seconds:120,capacity_alert_cooldown_seconds:240,capacity_alert_thresholds:{qa:17},capacity_alert_destination:''});
 expect(current.capacity_alert_thresholds).not.toHaveProperty('invalid');
 await page.reload();await settings(page);await expect(page.locator('#capacityPollSeconds')).toHaveValue('120');await expect(page.locator('#capacityCooldownSeconds')).toHaveValue('240');await expect(page.locator('#capacityThresholds')).toHaveValue('qa=17');
 await page.locator('[onclick="loadCapacityAlerts(true)"]').click();await expect(page.locator('#capacityAlertsList')).not.toBeEmpty();
 await refused(browser,'/api/capacity/config',{capacity_alert_poll_seconds:600});expect((await api(page,'/api/capacity/alerts')).body.config).toEqual(current);
 await capture(page,'capacity-saved',info);
 expect((await api(page,'/api/capacity/config',original)).status).toBe(200);
});

test('US-SP-SYSTEM-DASHBOARD all legacy dashboard modes save loopback URL reload and reject ungranted write',async({page,browser},info)=>{
 await settings(page);const before=await api(page,'/api/dashboard/config');expect(before.status).toBe(200);
 const target=auth.base_url;
 await page.locator('#settingsDashboardUrl').fill(target+'/unsupported-path');
 const invalid=page.waitForResponse((r:any)=>new URL(r.url()).pathname==='/api/dashboard/config'&&r.request().method()==='POST');
 await page.locator('[onclick="saveDashboardSettings()"]').click();expect((await invalid).status()).toBe(400);
 await expect(page.locator('#settingsDashboardStatus')).toContainText('failed to save');expect((await api(page,'/api/dashboard/config')).body).toEqual(before.body);
 for(const mode of ['always','never','auto']) {
  await page.locator('#settingsDashboardMode').selectOption(mode);await page.locator('#settingsDashboardUrl').fill(target);
  const saved=page.waitForResponse((r:any)=>new URL(r.url()).pathname==='/api/dashboard/config'&&r.request().method()==='POST');
  await page.locator('[onclick="saveDashboardSettings()"]').click();expect((await saved).status()).toBe(200);
  expect((await api(page,'/api/dashboard/config')).body).toMatchObject({enabled:mode,url:target});
  await page.reload();await settings(page);await expect(page.locator('#settingsDashboardMode')).toHaveValue(mode);await expect(page.locator('#settingsDashboardUrl')).toHaveValue(target);
 }
 await refused(browser,'/api/dashboard/config',{enabled:'never',url:''});expect((await api(page,'/api/dashboard/config')).body).toMatchObject({enabled:'auto',url:target});
 await capture(page,'dashboard-modes',info);expect((await api(page,'/api/dashboard/config',before.body)).status).toBe(200);
});

test('US-SP-SYSTEM-MCP configured local server toggles persist and empty tool search and every page size remain honest',async({page,browser},info)=>{
 await settings(page);const before=await api(page,'/api/mcp/servers');expect(before.status).toBe(200);expect(before.body.toggle_supported).toBe(true);
 const server=before.body.servers.find((s:any)=>s.name==='qa-local');expect(server).toMatchObject({enabled:false,command:'/usr/bin/false'});
 const row=page.locator('.mcp-server-row').filter({has:page.locator('.mcp-server-name',{hasText:'qa-local'})});
 for(const enabled of [true,false]) {
  const changed=page.waitForResponse((r:any)=>new URL(r.url()).pathname==='/api/mcp/servers/qa-local'&&r.request().method()==='PATCH');
  await row.locator('.mcp-toggle-btn').click();expect((await changed).status()).toBe(200);
  expect((await api(page,'/api/mcp/servers')).body.servers.find((s:any)=>s.name==='qa-local').enabled).toBe(enabled);
  await page.reload();await settings(page);await expect(row.locator('.mcp-toggle-btn')).toHaveClass(enabled?/mcp-toggle-enabled/:/mcp-toggle-disabled/);
 }
 await refused(browser,'/api/mcp/servers/qa-local',{enabled:true},'PATCH');expect((await api(page,'/api/mcp/servers')).body.servers.find((s:any)=>s.name==='qa-local').enabled).toBe(false);
 const tools=await api(page,'/api/mcp/tools');expect(tools.status).toBe(200);expect(tools.body.tools).toEqual([]);
 await page.locator('#mcpToolSearch').fill('QA_NO_TOOL_MATCH');await expect(page.locator('#mcpToolList')).toContainText(/no.*match/i);
 for(const size of ['5','10','20','40']) {await page.locator('#mcpToolToolbar select').selectOption(size);await expect(page.locator('#mcpToolToolbar select')).toHaveValue(size);await expect(page.locator('.mcp-tool-row')).toHaveCount(0);}
 await page.locator('#mcpToolSearch').fill('');await expect(page.locator('#mcpToolList')).toContainText(/no.*tools/i);await capture(page,'mcp-empty-and-disabled',info);
});

test('US-SP-SYSTEM-AUX-SLOTS every actual auxiliary slot saves chosen local provider model and reset cancellation preserves assignments',async({page,browser},info)=>{
 test.setTimeout(60000);await settings(page,'preferences');const initial=await auxiliary(page);const slots=initial.tasks.map((s:any)=>s.task);
 expect(slots).toHaveLength(12);
 for(const slot of slots){await page.locator('#aux-prov-'+slot).selectOption('custom:qa');await page.locator('#aux-model-'+slot).selectOption('qa-deterministic');}
 await page.locator('#btnApplyAuxModels').click();await expect(page.locator('#btnApplyAuxModels')).toBeHidden();
 const saved=await auxiliary(page);for(const task of saved.tasks)expect(task).toMatchObject({provider:'custom:qa',model:'qa-deterministic'});
 await page.reload();await settings(page,'preferences');for(const slot of slots){await expect(page.locator('#aux-prov-'+slot)).toHaveValue('custom:qa');await expect(page.locator('#aux-model-'+slot)).toHaveValue('qa-deterministic');}
 await page.locator('#btnResetAuxModels').click();await page.locator('#appDialogCancel').click();expect((await auxiliary(page)).tasks).toEqual(saved.tasks);
 await refused(browser,'/api/model/set',{scope:'auxiliary',task:'vision',provider:'auto',model:''});expect((await auxiliary(page)).tasks).toEqual(saved.tasks);
 await page.locator('#btnResetAuxModels').click();await page.locator('#appDialogConfirm').click();await expect.poll(async()=> (await auxiliary(page)).tasks.every((t:any)=>t.provider==='auto'&&t.model==='')).toBe(true);
 await page.reload();await settings(page,'preferences');for(const slot of slots){await expect(page.locator('#aux-prov-'+slot)).toHaveValue('auto');await expect(page.locator('#aux-model-'+slot)).toHaveValue('');}
 await capture(page,'all-auxiliary-reset',info);
});

test('US-SP-SYSTEM-AUX-ADVANCED real modal validates JSON saves all fields hides synthetic key and clears or cancels precisely',async({page},info)=>{
 await settings(page,'preferences');const initial=await auxiliary(page);const baseUrl=initial.main.base_url;expect(new URL(baseUrl).hostname).toBe('127.0.0.1');
 await auxGear(page,'vision');await page.locator('#auxAdvancedExtraBody').fill('[');await page.locator('#auxAdvancedSave').click();await expect(page.locator('#toast')).toContainText(/valid JSON/i);await expect(page.locator('#auxAdvancedOverlay')).toBeVisible();
 await page.locator('#auxAdvancedExtraBody').fill('[]');await page.locator('#auxAdvancedSave').click();await expect(page.locator('#toast')).toContainText(/JSON object/i);
 await page.locator('#auxAdvancedBaseUrl').fill(baseUrl);await page.locator('#auxAdvancedTimeout').fill('19');await page.locator('#auxAdvancedDownloadTimeout').fill('23');await page.locator('#auxAdvancedMaxConcurrency').fill('2');await page.locator('#auxAdvancedExtraBody').fill('{"qa_marker":"synthetic"}');await page.locator('#auxAdvancedApiKey').click();await page.locator('#auxAdvancedApiKey').fill('qa-synthetic-advanced-key');await advancedSave(page);
 const current=(await auxiliary(page)).tasks.find((t:any)=>t.task==='vision');expect(current).toMatchObject({base_url:baseUrl,timeout:19,download_timeout:23,max_concurrency:2,extra_body:{qa_marker:'synthetic'},api_key_set:true});expect(JSON.stringify(await auxiliary(page))).not.toContain('qa-synthetic-advanced-key');
 await page.reload();await settings(page,'preferences');await auxGear(page,'vision');await expect(page.locator('#auxAdvancedTimeout')).toHaveValue('19');await expect(page.locator('#auxAdvancedApiKey')).toHaveValue('');await expect(page.locator('#auxAdvancedApiKeyClear')).toBeVisible();
 await page.locator('#auxAdvancedTimeout').fill('999');await page.locator('#auxAdvancedCancel').click();expect((await auxiliary(page)).tasks.find((t:any)=>t.task==='vision')).toEqual(current);
 await auxGear(page,'vision');await page.locator('#auxAdvancedApiKeyClear').check();for(const id of ['auxAdvancedBaseUrl','auxAdvancedTimeout','auxAdvancedDownloadTimeout','auxAdvancedMaxConcurrency','auxAdvancedExtraBody'])await page.locator('#'+id).fill('');await advancedSave(page);
 const cleared=(await auxiliary(page)).tasks.find((t:any)=>t.task==='vision');expect(cleared).toMatchObject({base_url:'',timeout:'',download_timeout:'',max_concurrency:'',extra_body:{},api_key_set:false});
 await auxGear(page,'vision');await page.locator('#auxAdvancedClose').click();await expect(page.locator('#auxAdvancedOverlay')).toBeHidden();await capture(page,'advanced-cleared',info);
});

test('US-SP-SYSTEM-MAIN-ADVANCED main model options cancel and save persist without changing loopback provider pair',async({page},info)=>{
 await settings(page,'preferences');const initial=(await auxiliary(page)).main;expect(initial.provider).toBe('custom:qa');expect(new URL(initial.base_url).hostname).toBe('127.0.0.1');
 await page.locator('#mainAdvancedBtn').click();await page.locator('#auxAdvancedExtraBody').fill('{"discarded":true}');await page.locator('#auxAdvancedCancel').click();expect((await auxiliary(page)).main).toEqual(initial);
 await page.locator('#mainAdvancedBtn').click();await page.locator('#auxAdvancedExtraBody').fill('{"qa_main":true}');await advancedSave(page);
 expect((await auxiliary(page)).main).toMatchObject({provider:'custom:qa',model:'qa-deterministic',base_url:initial.base_url,extra_body:{qa_main:true}});
 await page.reload();await settings(page,'preferences');await page.locator('#mainAdvancedBtn').click();await expect(page.locator('#auxAdvancedExtraBody')).toHaveValue(/qa_main/);await expect(page.locator('#auxAdvancedBaseUrl')).toHaveValue(initial.base_url);await page.locator('#auxAdvancedExtraBody').fill('');await advancedSave(page);
 expect((await auxiliary(page)).main).toMatchObject({provider:'custom:qa',model:'qa-deterministic',base_url:initial.base_url,extra_body:{}});await capture(page,'main-options-restored',info);
});

test('US-SP-SYSTEM-PLUGIN local dashboard plugin toggle page sandbox and disabled routes persist with negative checks',async({page,browser},info)=>{
 await settings(page,'plugins');const plugin=page.locator('.plugin-card[data-plugin="qa-dashboard"]');await expect(plugin).toBeVisible();
 const found=(await api(page,'/api/plugins')).body.plugins.find((p:any)=>p.key==='qa-dashboard');expect(found).toMatchObject({enabled:false,tab:{path:'/qa-dashboard'}});
 expect((await page.request.get('/qa-dashboard')).status()).toBe(404);expect((await page.request.get('/dashboard-plugins/qa-dashboard/dist/index.js')).status()).toBe(404);
 await plugin.locator('.plugin-toggle-slider').click();await expect(plugin.locator('.plugin-enable-toggle')).toBeChecked();await expect(plugin.locator('.plugin-open-btn')).toBeVisible();expect((await api(page,'/api/settings')).body.dashboard_plugins['qa-dashboard']).toBe(true);
 await page.reload();await settings(page,'plugins');await expect(plugin.locator('.plugin-enable-toggle')).toBeChecked();
 await refused(browser,'/qa-dashboard',undefined,'GET');await refused(browser,'/dashboard-plugins/qa-dashboard/dist/index.js',undefined,'GET');
 const guest=await browser.newContext({baseURL:auth.base_url});
 try {
  const asset=await guest.request.get('/dashboard-plugins/qa-dashboard/dist/index.js',{maxRedirects:0});expect(asset.status()).toBe(401);expect(await asset.text()).not.toContain('QA_PLUGIN_PAGE');
  const destination=await guest.request.get('/qa-dashboard',{maxRedirects:0});expect(destination.status()).toBe(302);
  expect((await guest.request.get('/api/sessions')).status()).toBe(401);
  await guest.addCookies([{name:auth.cookie_name,value:'qa-invalid-session.signature',url:auth.base_url}]);
  expect((await guest.request.get('/dashboard-plugins/qa-dashboard/dist/index.js',{maxRedirects:0})).status()).toBe(401);
 } finally {await guest.close();}
 await plugin.locator('.plugin-open-btn').click();
 const frame=page.frameLocator('#pluginPageContainer iframe');await expect(frame.locator('body')).toContainText('QA_PLUGIN_PAGE');await expect(page.locator('#pluginPageContainer iframe')).toHaveAttribute('sandbox','allow-scripts allow-forms allow-popups');
 const isolated=await frame.locator('body').evaluate(()=>{
  const blocked=(read:()=>unknown)=>{try{read();return false;}catch(error){return error instanceof DOMException&&error.name==='SecurityError';}};
  return {parent:blocked(()=>window.parent.document),cookie:blocked(()=>document.cookie),storage:blocked(()=>localStorage.getItem('hermes-lang'))};
 });expect(isolated).toEqual({parent:true,cookie:true,storage:true});
 const sessionAttempt=page.waitForRequest((r:any)=>new URL(r.url()).pathname==='/api/sessions');
 const sessionReadable=await frame.locator('body').evaluate(async()=>{try{const response=await fetch('/api/sessions',{credentials:'include'});return response.ok;}catch{return false;}});
 expect(sessionReadable).toBe(false);expect(Object.hasOwn(await (await sessionAttempt).allHeaders(),'cookie'),'opaque frame request carries no session cookie').toBe(false);
 await info.attach('plugin-opaque-frame-rendered',{body:await page.locator('#pluginPageContainer iframe').screenshot(),contentType:'image/png'});
 const result=await page.request.get('/qa-dashboard');expect(result.status()).toBe(200);expect(result.headers()['content-security-policy']).toContain('sandbox');
 await refused(browser,'/api/settings',{dashboard_plugins:{'qa-dashboard':false}});expect((await api(page,'/api/settings')).body.dashboard_plugins['qa-dashboard']).toBe(true);
 await settings(page,'plugins');await plugin.locator('.plugin-toggle-slider').click();await expect(plugin.locator('.plugin-enable-toggle')).not.toBeChecked();await expect(plugin.locator('.plugin-open-btn')).toHaveCount(0);await page.reload();await settings(page,'plugins');await expect(plugin.locator('.plugin-enable-toggle')).not.toBeChecked();
 expect((await page.request.get('/qa-dashboard')).status()).toBe(404);expect((await page.request.get('/dashboard-plugins/qa-dashboard/dist/index.js')).status()).toBe(404);await capture(page,'plugin-disabled',info);
});

test('US-SP-SYSTEM-PROVIDER actual self-hosted connection test save and inference use only the loopback provider',async({page,browser},info)=>{
 test.setTimeout(60000);await settings(page,'providers');const initial=(await auxiliary(page)).main;expect(new URL(initial.base_url).hostname).toBe('127.0.0.1');
 const card=page.locator('.provider-card[data-provider="lmstudio"]');await expect(card).toBeVisible();await card.locator('button.provider-card-header').click();
 const inputs=card.locator('input.provider-card-input');await expect(inputs).toHaveCount(3);await inputs.nth(0).fill(initial.base_url);await inputs.nth(2).fill('');await expect(card.getByRole('button',{name:'Save',exact:true})).toBeDisabled();
 const probed=page.waitForResponse((r:any)=>new URL(r.url()).pathname==='/api/onboarding/probe'&&r.request().method()==='POST');await card.getByRole('button',{name:'Test connection',exact:true}).click();expect((await probed).status()).toBe(200);await expect(card).toContainText('Connected. 1 model(s) available.');await expect(inputs.nth(2)).toHaveValue('qa-deterministic');
 try {
  const saved=page.waitForResponse((r:any)=>new URL(r.url()).pathname==='/api/providers/self-hosted'&&r.request().method()==='POST');await card.getByRole('button',{name:'Save',exact:true}).click();expect((await saved).status()).toBe(200);
  expect((await auxiliary(page)).main).toMatchObject({provider:'lmstudio',model:'qa-deterministic',base_url:initial.base_url});
  await page.reload();await settings(page,'providers');await card.locator('button.provider-card-header').click();await expect(card.locator('input.provider-card-input').nth(0)).toHaveValue(initial.base_url);
  await refused(browser,'/api/providers/self-hosted',{provider:'lmstudio',base_url:initial.base_url,model:'forbidden-model'});expect((await auxiliary(page)).main.model).toBe('qa-deterministic');
  await open(page);const sid=await session(page);await page.locator('#msg').fill('QA_SELF_HOSTED_INFERENCE');await page.locator('#btnSend').click();await expect(page.locator('#messages')).toContainText('QA_REPLY: QA_SELF_HOSTED_INFERENCE',{timeout:35000});
  const current=(await api(page,'/api/session?session_id='+sid)).body.session;expect(JSON.stringify(current.messages)).toContain('QA_SELF_HOSTED_INFERENCE');await capture(page,'real-self-hosted-reply',info);
 } finally {
  expect((await api(page,'/api/model/set',{scope:'main',provider:initial.provider,model:initial.model,advanced:{base_url:initial.base_url,extra_body:initial.extra_body||{}}})).status).toBe(200);
 }
});
