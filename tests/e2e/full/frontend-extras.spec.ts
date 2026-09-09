import {test,expect,open,session,api,capture} from './fixtures';
test('US-SP-FILE-001 file and folder dialogs write real isolated workspace and support cancel',async({page})=>{
 await open(page);const sid=await session(page);await page.locator('#btnWorkspacePanelToggle').click();await expect(page.locator('#btnNewFile')).toBeVisible();await page.locator('#btnNewFile').click();await page.locator('#appDialogInput').fill('qa-file-'+Date.now()+'.txt');const name=await page.locator('#appDialogInput').inputValue();await page.locator('#appDialogConfirm').click();await expect(page.locator('#previewPathText')).toContainText(name);
 const r=await api(page,'/api/list?session_id='+sid+'&path=.');expect(r.status).toBe(200);expect(JSON.stringify(r.body)).toContain(name);
 await page.locator('#btnNewFile').click();await page.locator('#appDialogInput').fill('qa-cancelled.txt');await page.locator('#appDialogCancel').click();expect(JSON.stringify((await api(page,'/api/list?session_id='+sid+'&path=.')).body)).not.toContain('qa-cancelled.txt');
 await page.locator('#btnNewFolder').click();const folder='qa-folder-'+Date.now();await page.locator('#appDialogInput').fill(folder);await page.locator('#appDialogConfirm').click();await expect(page.locator('#appDialogDesc')).toContainText(/space/i);await page.locator('#appDialogCancel').click();expect(JSON.stringify((await api(page,'/api/list?session_id='+sid+'&path=.')).body)).toContain(folder);
});
test('US-SP-PREF-THEMES all built-in theme and font-size buttons apply and reload',async({page})=>{
 await open(page,'settings');await page.locator('[data-settings-section="appearance"]').click();
 for(const theme of ['light','dark','system']){await page.locator(`[data-theme-val="${theme}"]`).click();await expect.poll(()=>page.evaluate(()=>localStorage.getItem('hermes-theme'))).toBe(theme);}
 for(const size of ['small','default','large','xlarge']){await page.locator(`[data-font-size-val="${size}"]`).click();await expect.poll(()=>page.evaluate(()=>localStorage.getItem('hermes-font-size'))).toBe(size);}
 await page.reload();await expect(page.locator('html')).toHaveAttribute('data-font-size','xlarge');
});
test('US-SP-PREF-SKINS every rendered skin button applies its own skin value',async({page},info)=>{
 await open(page,'settings');await page.locator('[data-settings-section="appearance"]').click();const skins=await page.locator('#skinPickerGrid [data-skin-val]').evaluateAll(es=>es.map(e=>e.getAttribute('data-skin-val')));expect(skins.length).toBeGreaterThan(5);
 for(const skin of skins){await page.locator(`#skinPickerGrid [data-skin-val="${skin}"]`).click();await expect.poll(()=>page.evaluate(()=>localStorage.getItem('hermes-skin'))).toBe(skin);await capture(page,'skin-'+skin,info);}
});
test('US-SP-LOG-001 logfile tail severity wrap and refresh controls remain usable',async({page})=>{
 await open(page,'logs');await page.locator('#logsFile').selectOption('errors');await page.locator('#logsTail').selectOption('100');await page.locator('#logsSeverityFilter').selectOption('errors');await page.locator('#logsAutoRefresh').check();await page.locator('#logsWrap').check();await page.locator('#logsRefreshBtn').click();await expect(page.locator('#logsFile')).toHaveValue('errors');await expect(page.locator('#logsTail')).toHaveValue('100');await expect(page.locator('#logsWrap')).toBeChecked();
});
test('US-SP-INS-001 all analytics periods request and render their selected window',async({page})=>{
 await open(page,'insights');for(const days of ['7','30','90','365']){await page.locator('#insightsPeriod').selectOption(days);await page.locator('#insightsRefreshBtn').click();await expect(page.locator('#mainInsights')).toContainText('last '+days+' days');}
});
test('US-SP-UX-ERROR-TOAST error toast retains clickable dismiss control',async({page})=>{
 await open(page,'governance');await page.locator('[data-gov-tab="users"]').click();await page.locator('#govUserEmail').fill('bad-email');await page.locator('[onclick="_govSaveUser()"]').click();await expect(page.locator('#toast.error.show')).toBeVisible();await page.locator('#toast .toast-dismiss').click();await expect(page.locator('#toast')).not.toHaveClass(/show/);
});
