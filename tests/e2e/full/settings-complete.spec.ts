import {test,expect,open,api,auth} from './fixtures';

const toggles: [string,string,string][] = [
 ['appearance','settingsSessionJumpButtons','session_jump_buttons'],
 ['appearance','settingsSessionEndlessScroll','session_endless_scroll'],
 ['appearance','settingsAutoScrollFollow','auto_scroll_follow'],
 ['appearance','settingsRenderUserMarkdown','render_user_markdown'],
 ['appearance','settingsLargeTextPasteAsAttachment','large_text_paste_as_attachment'],
 ['appearance','settingsProjectQuickCreate','project_quick_create_buttons'],
 ['appearance','settingsShowTitlebarProfile','show_titlebar_profile'],
 ['appearance','settingsWorklogDetailsExpandedDefault','worklog_details_expanded_default'],
 ['preferences','settingsShowTokenUsage','show_token_usage'],
 ['preferences','settingsShowQuotaChip','show_quota_chip'],
 ['preferences','settingsShowConversationOutline','show_conversation_outline'],
 ['preferences','settingsShowTps','show_tps'],
 ['preferences','settingsFadeTextEffect','fade_text_effect'],
 ['preferences','settingsTerminalAutoExpand','terminal_auto_expand_on_output'],
 ['preferences','settingsShowBusyPlaceholderHint','show_busy_placeholder_hint'],
 ['preferences','settingsRtl','rtl'],
 ['preferences','settingsSoundEnabled','sound_enabled'],
 ['preferences','settingsWhatsNewSummary','whats_new_summary_enabled'],
];
for (const [section,id,key] of toggles) test(`US-SP-PREF-CONTROL-${key} both switch states save and reload`,async({page})=>{
 await open(page,'settings');await page.locator(`[data-settings-section="${section}"]`).click();
 const field=page.locator('#'+id);await expect(field).toBeVisible();const start=await field.isChecked();
 for(const wanted of [!start,start]){
  await field.setChecked(wanted);
  await expect.poll(async()=>{const r=await api(page,'/api/settings');expect(r.status).toBe(200);return r.body[key];}).toBe(wanted);
  await page.reload();await page.locator('.rail-btn[data-panel="settings"]').click();await page.locator(`[data-settings-section="${section}"]`).click();
  await expect(field).toBeChecked({checked:wanted});
 }
});

test('US-SP-PREF-ACTIVITY all activity display modes persist and timestamps toggle independently',async({page})=>{
 await open(page,'settings');await page.locator('[data-settings-section="appearance"]').click();
 for(const mode of ['transparent_stream','hide_all_activity','compact_worklog']){
  await page.locator(`[data-chat-activity-mode="${mode}"]`).click();
  await expect.poll(async()=>(await api(page,'/api/settings')).body.chat_activity_display_mode).toBe(mode);
  await expect(page.locator(`[data-chat-activity-mode="${mode}"]`)).toHaveAttribute('aria-pressed','true');
 }
 await page.locator('[data-chat-activity-mode="transparent_stream"]').click();
 for(const wanted of [false,true]){await page.locator('#settingsTransparentEventTimestamps').setChecked(wanted);await expect.poll(async()=>(await api(page,'/api/settings')).body.transparent_stream_event_timestamps).toBe(wanted);}
 await page.reload();await page.locator('.rail-btn[data-panel="settings"]').click();await page.locator('[data-settings-section="appearance"]').click();await expect(page.locator('[data-chat-activity-mode="transparent_stream"]')).toHaveAttribute('aria-pressed','true');
});

test('US-SP-PREF-STRUCTURED JSON and YAML view choices and threshold persist',async({page})=>{
 await open(page,'settings');await page.locator('[data-settings-section="appearance"]').click();
 for(const mode of ['on','off','auto']){
  await page.locator('#settingsStructuredCodeMode').selectOption(mode);
  await expect.poll(async()=>(await api(page,'/api/settings')).body.structured_code_default_view).toBe(mode);
  if(mode==='auto') await expect(page.locator('#settingsStructuredCodeAutoLines')).toBeEnabled();
  else await expect(page.locator('#settingsStructuredCodeAutoLines')).toBeDisabled();
 }
 await page.locator('#settingsStructuredCodeAutoLines').fill('32');await page.locator('#settingsStructuredCodeAutoLines').press('Tab');await expect.poll(async()=>(await api(page,'/api/settings')).body.structured_code_auto_tree_lines).toBe(32);
 await page.reload();await page.locator('.rail-btn[data-panel="settings"]').click();await page.locator('[data-settings-section="appearance"]').click();await expect(page.locator('#settingsStructuredCodeAutoLines')).toHaveValue('32');
});

test('US-SP-AUTH-009 virtual authenticator registers signs in and removes an actual passkey',async({page,context})=>{
 const cdp=await context.newCDPSession(page);await cdp.send('WebAuthn.enable');
 const {authenticatorId}=await cdp.send('WebAuthn.addVirtualAuthenticator',{options:{protocol:'ctap2',transport:'usb',hasResidentKey:true,hasUserVerification:true,isUserVerified:true,automaticPresenceSimulation:true}});
 try{
  // WebAuthn RP IDs are domain names. Use localhost with the same isolated
  // server, authenticating normally instead of transferring signed cookies.
  const base=auth.base_url.replace('127.0.0.1','localhost');await page.goto(base+'/login');
  await page.locator('#pw').fill(auth.login_password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.locator('#msg')).toBeVisible();
  await page.locator('.rail-btn[data-panel="settings"]').click();await page.locator('[data-settings-section="system"]').click();
  await expect(page.locator('#btnRegisterPasskey')).toBeEnabled();await page.locator('#btnRegisterPasskey').click();
  await expect(page.locator('#passkeyList')).toContainText('This device');
  await page.reload();await page.locator('.rail-btn[data-panel="settings"]').click();await page.locator('[data-settings-section="system"]').click();await expect(page.locator('#passkeyList')).toContainText('This device');
  await page.locator('#btnSignOut').click();await expect(page).toHaveURL(/\/login/);await expect(page.locator('#passkey-login')).toBeVisible();
  const credentials=await cdp.send('WebAuthn.getCredentials',{authenticatorId});
  expect(credentials.credentials).toHaveLength(1);expect(credentials.credentials[0].rpId).toBe('localhost');
  await page.locator('#passkey-login').click();await expect(page.locator('#msg')).toBeVisible();
  const me=await api(page,'/api/governance/me');expect(me.status).toBe(200);expect(JSON.stringify(me.body)).toContain('admin@example.test');
  await page.locator('.rail-btn[data-panel="settings"]').click();await page.locator('[data-settings-section="system"]').click();await page.locator('#passkeyList').getByRole('button',{name:'Remove',exact:true}).click();await page.locator('#appDialogCancel').click();await expect(page.locator('#passkeyList')).toContainText('This device');
  await page.locator('#passkeyList').getByRole('button',{name:'Remove',exact:true}).click();await page.locator('#appDialogConfirm').click();await expect(page.locator('#passkeyList')).toContainText('No passkeys registered.');
 }finally{await cdp.send('WebAuthn.removeVirtualAuthenticator',{authenticatorId});await cdp.detach();}
});

for(const [id,key] of [['settingsSendKey','send_key'],['settingsSidebarDensity','sidebar_density'],['settingsDefaultMessageMode','default_message_mode'],['settingsAutoTitleRefresh','auto_title_refresh_every']])
 test(`US-SP-PREF-SELECT-${key} every offered option saves and restores`,async({page})=>{
  await open(page,'settings');await page.locator('[data-settings-section="preferences"]').click();const field=page.locator('#'+id);await expect(field).toBeVisible();
  const original=await field.inputValue();const values=await field.locator('option').evaluateAll(es=>es.map(e=>(e as HTMLOptionElement).value));expect(values.length).toBeGreaterThan(1);
  for(const value of [...values,original]){await field.selectOption(value);await expect.poll(async()=>String((await api(page,'/api/settings')).body[key])).toBe(value);}
  await page.reload();await page.locator('.rail-btn[data-panel="settings"]').click();await page.locator('[data-settings-section="preferences"]').click();await expect(field).toHaveValue(original);
 });

test('US-SP-PREF-NUMBERS pinned limit and assistant display name save and reload',async({page})=>{
 await open(page,'settings');await page.locator('[data-settings-section="preferences"]').click();
 await page.locator('#settingsPinnedSessionsLimit').fill('9');await page.locator('#settingsPinnedSessionsLimit').press('Tab');await expect.poll(async()=>(await api(page,'/api/settings')).body.pinned_sessions_limit).toBe(9);
 await page.locator('#settingsBotName').fill('QA Assistant');await page.locator('#settingsBotName').press('Tab');await expect.poll(async()=>(await api(page,'/api/settings')).body.bot_name).toBe('QA Assistant');
 await page.reload();await page.locator('.rail-btn[data-panel="settings"]').click();await page.locator('[data-settings-section="preferences"]').click();await expect(page.locator('#settingsPinnedSessionsLimit')).toHaveValue('9');await expect(page.locator('#settingsBotName')).toHaveValue('QA Assistant');
 await page.locator('#settingsBotName').fill('SynPulse');await page.locator('#settingsBotName').press('Tab');await expect.poll(async()=>(await api(page,'/api/settings')).body.bot_name).toBe('SynPulse');
});

test('US-SP-PREF-TAB-CHIPS each configurable navigation chip hides and restores its panel',async({page})=>{
 test.setTimeout(120000);await open(page,'settings');await page.locator('[data-settings-section="appearance"]').click();
 const chips=page.locator('#tabVisibilityChips [data-tab-panel]');
 const panels=await chips.evaluateAll(es=>es.filter(e=>!e.hasAttribute('disabled')).map(e=>e.getAttribute('data-tab-panel')).filter(p=>p&&p!=='__hermes_dashboard__'&&p!=='chat'&&p!=='settings'));
 expect(panels.length).toBeGreaterThan(5);
 for(const panel of panels){
  await test.step('Toggle '+panel+' visibility',async()=>{
   const initial=(await api(page,'/api/settings')).body.hidden_tabs||[];const wasHidden=initial.includes(panel);
   await page.locator(`#tabVisibilityChips [data-tab-panel="${panel}"]`).click();
   await expect.poll(async()=>((await api(page,'/api/settings')).body.hidden_tabs||[]).includes(panel)).toBe(!wasHidden);
   await page.locator(`#tabVisibilityChips [data-tab-panel="${panel}"]`).click();
   await expect.poll(async()=>((await api(page,'/api/settings')).body.hidden_tabs||[]).includes(panel)).toBe(wasHidden);
  });
 }
});

test('US-SP-PREF-COMPOSER-CHIPS every footer visibility chip saves both states',async({page})=>{
 test.setTimeout(120000);await open(page,'settings');await page.locator('[data-settings-section="appearance"]').click();
 const keys=await page.locator('#composerControlsChips [data-composer-control-key]').evaluateAll(es=>es.map(e=>e.getAttribute('data-composer-control-key')));expect(keys.length).toBeGreaterThan(3);
 for(const key of keys){await test.step('Toggle '+key,async()=>{
  const chip=page.locator(`#composerControlsChips [data-composer-control-key="${key}"]`);const original=Boolean((await api(page,'/api/settings')).body[key!]);
  await chip.click();await expect.poll(async()=>(await api(page,'/api/settings')).body[key!]).toBe(!original);
  await chip.click();await expect.poll(async()=>(await api(page,'/api/settings')).body[key!]).toBe(original);
 });}
});
