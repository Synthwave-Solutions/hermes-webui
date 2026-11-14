import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {test, expect, auth} from './fixtures';

test('PERSONAL FINDINGS read a delivered result and discuss that exact update', async ({page, request}, info) => {
  const repo = process.cwd();
  execFileSync(process.env.QA_RUNTIME_PYTHON!, [path.join(repo, 'scripts/e2e/seed_findings.py')], {
    env:{...process.env, HERMES_WEBUI_AGENT_DIR:auth.engine, PYTHONPATH:[process.env.PYTHONPATH, repo, auth.engine].join(path.delimiter)},
  });
  await page.goto('/');
  const tour = page.locator('#spHelpCard[data-kind="tour_offer"] .sp-help-btn').first();
  await page.addLocatorHandler(tour, async()=>{await tour.click();});
  await expect(page.locator('.wp-hero')).toBeVisible();
  const feed = page.locator('[data-wp-findings]');
  await expect(feed.getByRole('heading', {name:'Findings for you'})).toBeVisible();
  const cards = feed.locator('article:visible');
  await expect(cards).toHaveCount(3);
  await expect(cards.first()).toContainText('revised proposal');
  await expect(feed).not.toContainText('Private report for Alice');
  const other = await request.get(auth.base_url + '/api/me/findings', {
    headers:{Cookie:auth.cookie_name + '=' + auth.cookies.alice},
  });
  expect(other.status()).toBe(200);
  expect((await other.json()).findings.map(row=>row.body)).toEqual([
    'Private report for Alice.\n\nThe original report includes a dated comparison.'
  ]);
  const sent = [];
  page.on('request', req=>{if (req.url().includes('/api/chat/start')) sent.push(req.url());});
  for (const width of [1440,900,390]) {
    await page.setViewportSize({width,height:900});
    await page.evaluate(()=>closeMobileSidebar());
    expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({path:info.outputPath('findings-'+width+'.png')});
  }
  await feed.getByRole('button',{name:'Earlier updates (1)'}).click();
  await expect(cards).toHaveCount(4);
  await cards.last().getByRole('button',{name:'Read update'}).click();
  await expect(cards.last().locator('.wp-finding-body')).toContainText('dated comparison');
  await cards.last().getByRole('button',{name:'Discuss in chat'}).click();
  await expect(page.locator('#msg')).toBeVisible();
  await expect(page.locator('#composerSelectionChips blockquote')).toContainText('new supplier');
  await expect(page.locator('#composerSelectionChips')).not.toContainText('revised proposal');
  expect(await page.evaluate(()=>S.activeProfile)).toBe('qa-research');
  await expect(page.locator('#msg')).toBeEmpty();
  await page.locator('.selection-chip-remove').click();
  await expect(page.locator('#composerSelectionChips')).toBeHidden();
  expect(sent).toHaveLength(0);
});

test('PERSONAL FINDINGS empty feed and retry stay inside Studio', async ({page}) => {
  let attempts = 0;
  await page.route('**/api/me/findings', route => {
    const failed = ++attempts === 1;
    return route.fulfill({status:failed ? 503 : 200,json: failed ? {error:'unavailable'} : {findings:[]}});
  });
  await page.goto('/');
  const tour = page.locator('#spHelpCard[data-kind="tour_offer"] .sp-help-btn').first();
  await page.addLocatorHandler(tour, async()=>{await tour.click();});
  const feed = page.locator('[data-wp-findings]');
  await feed.getByRole('button',{name:'Retry'}).click();
  await expect(feed).toContainText('When a bot finds something for you');
  await expect(page.locator('.wp-hero')).toBeVisible();
});
