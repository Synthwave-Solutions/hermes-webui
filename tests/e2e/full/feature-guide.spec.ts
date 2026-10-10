import {test,expect,open} from './fixtures';
test.use({user:'admin'});
async function ready(page:any){await page.waitForFunction(()=>typeof S!=='undefined'&&S._bootReady&&_loadingSessionId===null);}
async function guide(page:any,feature?:string){await page.evaluate((f:any)=>window.SynthPulseFeatureGuide.open({feature:f,locale:'en'}),feature);await expect(page.locator('#spFeatureGuide')).toBeVisible();}

test('complete catalogs search locally, translate with parity, filter and export',async({page})=>{
 await open(page);await ready(page);await page.locator('#msg').fill('QA draft must survive the feature guide');
 const requests:string[]=[];page.on('request',r=>requests.push(r.url()+' '+(r.postData()||'')));await guide(page);
 const count=await page.evaluate(()=>window.SynthPulseFeatureGuide.featureCount);expect(count).toBeGreaterThan(400);
 await page.locator('#spGuideSearch').fill('notifications mute');
 await expect(page.locator('[data-feature="webui.tasks.mute"]')).toBeVisible();
 await page.locator('[data-feature="webui.tasks.mute"]').click();await expect(page.locator('#spGuideFeatureTitle')).toHaveText('Mute task notifications for yourself');
 await page.locator('#spGuideLanguage').selectOption('nl');await expect(page.locator('#spGuideFeatureTitle')).toHaveText('Taakmeldingen voor jezelf dempen');
 await page.getByRole('button',{name:'Zoekopdracht en filters wissen',exact:true}).click();await page.locator('#spGuideProduct').selectOption('msp');
 await expect(page.locator('.sp-guide-result').first()).toContainText('MSP');
 await page.locator('#spGuideSearch').fill('wizard');expect(await page.locator('.sp-guide-result').count()).toBeGreaterThan(0);
 await page.getByRole('button',{name:'Zoekopdracht en filters wissen',exact:true}).click();await page.locator('#spGuideStatus').selectOption('planned');
 expect(await page.locator('.sp-guide-result').count()).toBeGreaterThan(0);await expect(page.locator('.sp-guide-result').first()).toContainText('Gepland');
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Tweetalige catalogi downloaden'}).click();expect((await download).suggestedFilename()).toBe('synthpulse-feature-catalog.json');
 await page.locator('#spGuideSearch').fill('PRIVATE_GUIDE_QUERY_9274');await expect(page.locator('.sp-guide-empty')).toBeVisible();
 expect(requests.some(url=>url.includes('PRIVATE_GUIDE_QUERY')||url.includes('notifications%20mute'))).toBe(false);
 await page.getByRole('button',{name:'Gids sluiten'}).click();await expect(page.locator('#msg')).toHaveValue('QA draft must survive the feature guide');
});

test('context link, escape and hidden-control action preserve permissions and focus',async({page})=>{
 await open(page);await ready(page);await page.locator('#btnPageHelp').click();
 const context=page.getByRole('button',{name:/Features on this page|Functies op deze pagina/});await expect(context).toBeVisible();await context.click();
 await expect(page.locator('#spGuideArea')).toHaveValue('chat');await page.keyboard.press('Escape');await expect(page.locator('#btnPageHelp')).toBeFocused();
 await guide(page,'webui.settings.shutdown');const posts:string[]=[];page.on('request',r=>{if(r.method()==='POST')posts.push(r.url());});
 await page.getByRole('button',{name:'Show control',exact:true}).click();await expect(page.locator('.sp-guide-notice')).toContainText('not visible');expect(posts).toEqual([]);
 const beforeUrl=page.url();await page.keyboard.press('Control+k');expect(page.url()).toBe(beforeUrl);
 await page.locator('#spGuideSearch').fill('<img src=x onerror=alert(1)>');await expect(page.locator('.sp-guide-empty')).toBeVisible();expect(await page.locator('#spFeatureGuide img').count()).toBe(0);
 await page.keyboard.press('Escape');await expect(page.locator('#spFeatureGuide')).not.toBeVisible();
});

test('desktop and narrow Dutch layouts, keyboard focus and deep links',async({page},info)=>{
 await page.goto('/?help_feature=webui.memory.explorer');await expect(page.locator('#spFeatureGuide')).toBeVisible();await page.locator('#spGuideLanguage').selectOption('nl');
 await expect(page.locator('#spGuideFeatureTitle')).toHaveText('Geheugenbanken verkennen');await expect(page.locator('.sp-guide-detail')).toContainText('alleen voor de eigenaar');
 await page.screenshot({path:info.outputPath('feature-guide-desktop-nl.png'),fullPage:true});
 for(const width of [390,1440]){
  await page.setViewportSize({width,height:900});const bounds=await page.locator('#spFeatureGuide').evaluate(el=>({scroll:el.scrollWidth,width:el.clientWidth,rect:el.getBoundingClientRect().toJSON()}));expect(bounds.scroll).toBeLessThanOrEqual(bounds.width+1);expect(bounds.rect.right).toBeLessThanOrEqual(width);expect(bounds.rect.left).toBeGreaterThan(0);
  await page.locator('#spGuideLanguage').focus();for(let i=0;i<12;i++)await page.keyboard.press('Tab');expect(await page.locator('#spFeatureGuide').evaluate(el=>el.contains(document.activeElement))).toBe(true);
  if(width===390)await page.screenshot({path:info.outputPath('feature-guide-mobile-nl.png'),fullPage:true});
 }
 await page.keyboard.press('Escape');await expect(page.locator('#spFeatureGuide')).not.toBeVisible();
 await page.goto('/?help_feature=webui.unknown');await expect(page.locator('.sp-guide-notice')).toContainText(/not found|niet gevonden/);
});
