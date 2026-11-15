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
  const report = page.getByRole('dialog');
  await expect(report.locator('.wp-finding-body')).toContainText('dated comparison');
  await report.getByRole('button',{name:'Discuss in chat'}).click();
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

test('PERSONAL FINDINGS prioritises concrete advice and opens a readable report', async ({page}, info) => {
  const report = [
    'Update: er zijn geen nieuwe scout-items. Ik heb de agenda gelezen.',
    'De status is gebaseerd op de laatst opgeslagen planning.',
    'Mijn advies: Bereid de technische overdracht van maandag voor.',
    'Dit kan ik voor je oppakken:\n1. *Controleer de planning.* Bekijk de laatste run.\n2. Gebruik **taakstatus** en `jobs.json`.',
    'Bron: [Planning](https://example.test/planning).',
  ].join('\n\n');
  const other = '## Update\nNo new scout findings.\n\n## Next step\nReview the schedule before Friday.\n\n![Diagram](https://example.test/tracker.png) <img src=x> [invalid](javascript:void)';
  const bodies = [report, other, 'A proposal is ready for review.'];
  const findings = bodies.map((body,i)=>({body,bot:['Operations Bot','Research Bot','Planning Bot'][i],at:1800000000-i,
    run_at:new Date((1800000000-i)*1000).toISOString(),session_id:'qa-finding-'+i,profile:'qa-research'}));
  await page.route('**/api/me/findings', r=>r.fulfill({json:{findings}}));
  await page.goto('/');
  const tour = page.locator('#spHelpCard[data-kind="tour_offer"] .sp-help-btn').first();
  await page.addLocatorHandler(tour, async()=>{await tour.click();});
  await expect(page.locator('.wp-hero')).toBeVisible();
  const card = page.locator('.wp-finding').first();
  const read = card.getByRole('button',{name:'Read update'});
  for (const width of [1440,900,390]) {
    await page.setViewportSize({width,height:900});
    await page.evaluate(()=>closeMobileSidebar());
    await read.click();
    await page.screenshot({path:info.outputPath('finding-reader-'+width+'.png')});
    const reader = page.getByRole('dialog',{name:'Operations Bot'});
    await expect(reader).toBeVisible();
    await expect(reader.getByRole('heading',{name:'Mijn advies'})).toBeVisible();
    await expect(reader.locator('ol li')).toHaveCount(2);
    await expect(reader.locator('em')).toHaveText('Controleer de planning.');
    await expect(reader.locator('strong')).toContainText('taakstatus');
    await expect(reader.locator('code')).toHaveText('jobs.json');
    await expect(reader.getByRole('link')).toHaveCount(1);
    await expect(reader.getByRole('link',{name:'Planning'})).toHaveAttribute('href','https://example.test/planning');
    expect(await reader.evaluate(el=>el.scrollWidth<=el.clientWidth)).toBe(true);
    await page.keyboard.press('Escape');
    await expect(read).toBeFocused();
    await expect(card.locator('.wp-finding-preview')).toHaveText('Bereid de technische overdracht van maandag voor.');
  }
  const second = page.locator('.wp-finding').nth(1);
  await expect(second.locator('.wp-finding-preview')).toHaveText('Review the schedule before Friday.');
  await second.getByRole('button',{name:'Read update'}).click();
  await expect(page.getByRole('dialog')).toContainText('Review the schedule');
  await expect(page.getByRole('dialog').locator('a,img,iframe')).toHaveCount(0);
});
