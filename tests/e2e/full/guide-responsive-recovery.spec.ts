import type {Page} from '@playwright/test';
import {test, expect, open} from './fixtures';

async function openGuide(page:Page) {
  await open(page);
  await page.waitForFunction(()=>typeof S!=='undefined'&&S._bootReady&&_loadingSessionId===null);
  await page.evaluate(async()=>{
    await window.loadSynthPulseFeatureGuide();
    window.SynthPulseFeatureGuide.open({locale:'en'});
  });
  await expect(page.locator('#spFeatureGuide')).toBeVisible();
}

async function scrollToFooter(page:Page) {
  // Scroll from the dialog chrome, as a user would, rather than forcing the
  // footer into view through a clipped overflow:hidden container.
  await page.locator('.sp-guide-header').hover();
  await page.mouse.wheel(0,1500);
  await expect(page.getByRole('button',{name:'Download bilingual catalogs',exact:true})).toBeInViewport({ratio:0.99});
}

test('short portrait guide keeps expanded filters, results and reading controls reachable',async({page})=>{
  await page.setViewportSize({width:390,height:568});
  await openGuide(page);
  await page.locator('.sp-guide-filters summary').click();
  await page.locator('#spGuideSearch').fill('notifications mute');

  const result=page.locator('[data-feature="webui.tasks.mute"]');
  await result.scrollIntoViewIfNeeded();
  await expect(result).toBeInViewport({ratio:0.99});
  await result.click();
  await expect(page.locator('#spGuideFeatureTitle')).toHaveText('Mute task notifications for yourself');
  await expect(page.locator('#spGuideFeatureTitle')).toBeInViewport({ratio:0.99});

  const access=page.locator('.sp-guide-access summary');
  await access.click();
  const copy=page.getByRole('button',{name:'Copy feature link',exact:true});
  await copy.scrollIntoViewIfNeeded();
  await expect(copy).toBeInViewport({ratio:0.99});
  await page.locator('[data-guide-back]').click();
  await expect(page.locator('#spGuideSearch')).toHaveValue('notifications mute');
  await expect(result).toBeFocused();
  await scrollToFooter(page);
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download bilingual catalogs',exact:true}).click();
  expect((await download).suggestedFilename()).toBe('synthpulse-feature-catalog.json');
});

test('short landscape guide lets users scroll to the footer and read a result',async({page})=>{
  await page.setViewportSize({width:844,height:390});
  await openGuide(page);
  await scrollToFooter(page);
  await page.locator('.sp-guide-footer summary').click();
  const privacy=page.locator('.sp-guide-footer p').filter({hasText:'Search uses this static catalog only.'});
  await privacy.scrollIntoViewIfNeeded();
  await expect(privacy).toBeInViewport({ratio:0.99});

  const result=page.locator('.sp-guide-result').first();
  const title=await result.locator('span').innerText();
  await result.scrollIntoViewIfNeeded();
  await expect(result).toBeInViewport({ratio:0.99});
  await result.click();
  await page.locator('#spGuideFeatureTitle').scrollIntoViewIfNeeded();
  await expect(page.locator('#spGuideFeatureTitle')).toHaveText(title);
  await expect(page.locator('#spGuideFeatureTitle')).toBeInViewport({ratio:0.99});
});

test('desktop guide keeps results and reading panes independently scrollable',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await openGuide(page);
  const results=page.locator('.sp-guide-results');
  const detail=page.locator('.sp-guide-detail');
  await results.hover();
  await page.mouse.wheel(0,500);
  await expect.poll(()=>results.evaluate(el=>el.scrollTop)).toBeGreaterThan(0);
  const resultsScroll=await results.evaluate(el=>el.scrollTop);
  expect(await detail.evaluate(el=>el.scrollTop)).toBe(0);

  await detail.hover();
  await page.mouse.wheel(0,500);
  await expect.poll(()=>detail.evaluate(el=>el.scrollTop)).toBeGreaterThan(0);
  expect(await results.evaluate(el=>el.scrollTop)).toBe(resultsScroll);
  expect(await page.locator('#spFeatureGuide').evaluate(el=>el.scrollTop)).toBe(0);
  await expect(page.locator('.sp-guide-header')).toBeInViewport({ratio:0.99});
  await expect(page.locator('.sp-guide-footer')).toBeInViewport({ratio:0.99});
});

test('empty desktop search remains recoverable after resizing to mobile',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/?help_feature=webui.tasks.mute');
  await expect(page.locator('#spGuideFeatureTitle')).toHaveText('Mute task notifications for yourself');
  await page.locator('#spGuideSearch').fill('no-feature-matches-this-qa-query');
  await page.setViewportSize({width:390,height:844});

  await expect(page.locator('#spGuideSearch')).toBeVisible();
  await expect(page.locator('.sp-guide-empty')).toContainText('No matching features');
  await expect(page.locator('.sp-guide-empty')).toBeVisible();
  await page.getByRole('button',{name:'Clear search and filters',exact:true}).click();
  await expect(page.locator('#spGuideSearch')).toHaveValue('');
  await page.locator('#spGuideSearch').fill('notifications mute');
  await page.locator('[data-feature="webui.tasks.mute"]').click();
  await expect(page.locator('#spGuideFeatureTitle')).toHaveText('Mute task notifications for yourself');
  await expect(page.locator('#spGuideFeatureTitle')).toBeVisible();
});
