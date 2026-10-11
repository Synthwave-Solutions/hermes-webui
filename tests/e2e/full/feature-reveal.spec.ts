import {test,expect,open} from './fixtures';
async function ready(page:any){await open(page);await page.waitForFunction(()=>typeof S!=='undefined'&&S._bootReady&&_loadingSessionId===null);}

test('feature selection reveals the correct settings pane and returns to chat with draft intact',async({page},info)=>{
 await ready(page);await page.locator('#msg').fill('Unsent tour regression draft');
 await page.evaluate(()=>window.SynthPulseHelp.startFeatureTour(['webui.settings.theme','webui.chat.model'],{locale:'nl'}));
 const tip=page.locator('.sp-feature-tour');await expect(tip).toBeVisible();
 await expect.poll(()=>page.evaluate(()=>_currentPanel)).toBe('settings');
 await expect(page.locator('#themePickerGrid')).toHaveClass(/guida-highlight/);
 await expect(tip.locator('.sp-feature-tour-note')).toHaveCount(0);
 await page.screenshot({path:info.outputPath('settings-revealed.png')});
 await tip.locator('.sp-feature-tour-picker').selectOption('1');
 await expect.poll(()=>page.evaluate(()=>_currentPanel)).toBe('chat');
 await expect(page.locator('#composerModelChip')).toHaveClass(/guida-highlight/);
 await page.keyboard.press('Escape');await expect(page.locator('#msg')).toHaveValue('Unsent tour regression draft');
});

test('task form feature points to its real entry and explains the required action',async({page},info)=>{
 await ready(page);await page.evaluate(()=>window.SynthPulseHelp.startFeatureTour(['webui.tasks.notify'],{locale:'nl'}));
 const tip=page.locator('.sp-feature-tour');
 await expect.poll(()=>page.evaluate(()=>_currentPanel)).toBe('tasks');
 await expect(page.locator('.guida-highlight')).toHaveCount(1);
 await expect(tip.locator('.sp-feature-tour-note')).not.toContainText('Deze bediening is hier niet zichtbaar');
 await expect(tip.locator('.sp-feature-tour-note')).toContainText(/taak/i);
 await page.screenshot({path:info.outputPath('task-entry.png')});
 await page.keyboard.press('Escape');await expect(page.locator('.guida-highlight')).toHaveCount(0);
});

test('immediate close cancels deferred guide navigation',async({page})=>{
 await ready(page);await page.evaluate(()=>{window.SynthPulseHelp.startFeatureTour(['webui.settings.theme'],{locale:'en'});window.SynthPulseHelp.closeAll();});
 await page.waitForTimeout(450);expect(await page.evaluate(()=>_currentPanel)).toBe('chat');await expect(page.locator('.sp-feature-tour,#spFeatureTourAnchor')).toHaveCount(0);
});

test('mobile guide opens and restores a collapsed drawer without creating a task',async({page},info)=>{
 await page.setViewportSize({width:390,height:900});await ready(page);
 const writes:string[]=[];page.on('request',r=>{if(['POST','PUT','PATCH','DELETE'].includes(r.method())&&!r.url().endsWith('/api/help/events'))writes.push(r.url());});
 const before=await page.locator('.sidebar').getAttribute('class');
 await page.evaluate(()=>window.SynthPulseHelp.startFeatureTour(['webui.tasks.notify','webui.chat.send'],{locale:'en'}));
 const tip=page.locator('.sp-feature-tour');
 await expect(page.locator('[data-tour="tasks-new"]')).toHaveClass(/guida-highlight/);
 const box=await tip.boundingBox();expect(box!.x).toBeGreaterThanOrEqual(0);expect(box!.x+box!.width).toBeLessThanOrEqual(390);expect(box!.y+box!.height).toBeLessThanOrEqual(900);
 await page.screenshot({path:info.outputPath('mobile-task-entry.png')});
 await tip.locator('.sp-feature-tour-picker').selectOption('1');await expect(page.locator('#msg')).toHaveClass(/guida-highlight/);
 await page.keyboard.press('Escape');await expect(page.locator('.sidebar')).toHaveAttribute('class',before!);expect(writes).toEqual([]);
});

test('unsaved settings prevent automatic navigation and remain untouched',async({page})=>{
 await ready(page);await page.evaluate(async()=>{await switchPanel('settings');switchSettingsSection('preferences');});
 await expect(page.locator('#mainSettings .settings-main')).not.toHaveAttribute('inert','');
 await page.locator('#settingsMaxTokens').fill('12345');
 await page.evaluate(()=>window.SynthPulseHelp.startFeatureTour(['webui.chat.model'],{locale:'nl'}));
 await expect(page.locator('.sp-feature-tour-note')).toContainText('Bewaar of sluit');
 expect(await page.evaluate(()=>_currentPanel)).toBe('settings');
 await page.keyboard.press('Escape');await expect(page.locator('#settingsMaxTokens')).toHaveValue('12345');
});

test('new bot wizard draft survives a topic on another panel',async({page})=>{
 await ready(page);await page.evaluate(()=>switchPanel('profiles'));await page.locator('[data-tour="bots-new"]').click();await page.locator('#builderName').fill('draft-bot');
 await page.evaluate(()=>window.SynthPulseHelp.startFeatureTour(['webui.chat.model'],{locale:'en'}));
 await expect(page.locator('.sp-feature-tour-note')).toContainText('Save or close');expect(await page.evaluate(()=>_currentPanel)).toBe('profiles');
 await page.keyboard.press('Escape');await expect(page.locator('#builderName')).toHaveValue('draft-bot');
});

test('project creation draft survives a topic on another panel',async({page})=>{
 await ready(page);await page.evaluate(()=>switchPanel('projects'));await page.locator('#projNewName').fill('Draft project');
 await page.evaluate(()=>window.SynthPulseHelp.startFeatureTour(['webui.chat.model'],{locale:'en'}));
 await expect(page.locator('.sp-feature-tour-note')).toContainText('Save or close');expect(await page.evaluate(()=>_currentPanel)).toBe('projects');
 await page.keyboard.press('Escape');await expect(page.locator('#projNewName')).toHaveValue('Draft project');
});

test('unsaved clarification preference prevents guide section reload',async({page})=>{
 await ready(page);await page.evaluate(async()=>{await switchPanel('settings');switchSettingsSection('preferences');});
 await expect(page.locator('#interactionUserMode')).toBeEnabled();
 const original=await page.locator('#interactionUserMode').inputValue(),next=original==='minimal'?'balanced':'minimal';await page.locator('#interactionUserMode').selectOption(next);
 await page.evaluate(()=>window.SynthPulseHelp.startFeatureTour(['webui.settings.theme'],{locale:'en'}));
 await expect(page.locator('.sp-feature-tour-note')).toContainText('Save or close');expect(await page.evaluate(()=>_currentSettingsSection)).toBe('preferences');
 await page.keyboard.press('Escape');await expect(page.locator('#interactionUserMode')).toHaveValue(next);
});
