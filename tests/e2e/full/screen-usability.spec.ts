import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {test,expect,api,auth} from './fixtures';

for (const [user,kind] of [['qafindadmin','admin'],['qafindmember','member'],['qaengineer','engineer'],['qaoperator','operator']] as const) {
  test.describe('Workspace start for '+kind,()=>{
    test.use({user});
    test('SCREEN USABILITY personal updates can load before the workspace lists',async({page})=>{
      execFileSync(process.env.QA_RUNTIME_PYTHON!, ['scripts/e2e/seed_findings.py',user], {
        env:{...process.env,HERMES_WEBUI_AGENT_DIR:auth.engine,PYTHONPATH:[process.env.PYTHONPATH,process.cwd(),auth.engine].join(path.delimiter)}
      });
      let release;
      const wait = new Promise<void>(resolve=>{release=resolve;});
      await page.route('**/api/studio/playbooks',async route=>{await wait;await route.continue();});
      try {
        await page.goto('/',{waitUntil:'domcontentloaded'});
        await expect(page.locator('html')).toHaveAttribute('data-workspace-kind',kind);
        await expect(page.locator('[data-wp-findings] article:visible')).toHaveCount(1);
        await expect(page.locator('[data-wp-findings] article')).toContainText('A new supplier comparison for '+user);
      } finally {release();}
      await expect(page.locator('.wp-hero')).toBeVisible();
    });
  });
}

test('SCREEN USABILITY browse, filter and reopen a skill on desktop and mobile',async({page},info)=>{
  await page.goto('/');
  await expect(page.locator('.wp-hero')).toBeVisible();
  const tour=page.locator('#spHelpCard[data-kind="tour_offer"] .sp-help-btn').first();
  await page.addLocatorHandler(tour,()=>tour.click());
  for (const [name,category,description] of [
    ['prepare-interview','research','Prepare questions for the next customer interview.'],
    ['compare-suppliers','research','Compare supplier evidence in a short table.'],
    ['weekly-brief','writing','Turn a week of decisions into a short brief.']
  ]) {
    const saved=await api(page,'/api/skills/save',{name,category,content:'---\nname: '+name+'\ndescription: '+description+'\n---\n# '+name+'\n'+description});
    expect(saved.status).toBe(200);
  }
  await page.locator('.rail [data-panel="skills"]').click();
  const lib=page.locator('#skillDetailEmpty');
  await expect(lib.locator('h1')).toHaveText('Skills library');
  const query=lib.locator('#librarySkillQuery'),category=lib.locator('select').first();
  await query.fill('customer interview');
  await expect(lib.locator('.library-skill')).toHaveCount(1);
  await query.fill('');
  await category.selectOption('writing');
  const item=lib.locator('[data-library-skill="weekly-brief"]');
  await item.click();
  await expect(page.locator('#skillDetailTitle')).toHaveText('weekly-brief');
  await page.locator('#skillLibraryBack').click();
  await expect(category).toHaveValue('writing');
  await query.fill('nothing-matches');
  await lib.getByRole('button',{name:'Clear filters'}).click();
  await expect(item).toBeVisible();
  await expect(category).toHaveValue('');
  for(const width of [1440,900,390]){
    await page.setViewportSize({width,height:900});
    await expect(item).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
    await page.screenshot({path:info.outputPath('library-'+width+'.png')});
  }
  await page.locator('#btnHamburger').click();
  await page.locator('.sidebar-nav [data-panel="skills"]').click();
  await expect(page.locator('.sidebar')).not.toHaveClass(/mobile-open/);
  await item.click();
  await expect(page.locator('#skillDetailTitle')).toHaveText('weekly-brief');
});

test('SCREEN USABILITY catalogues reclaim space and retain mobile navigation',async({page})=>{
  await page.goto('/');
  await expect(page.locator('.wp-hero')).toBeVisible();
  const tour=page.locator('#spHelpCard[data-kind="tour_offer"] .sp-help-btn').first();
  await page.addLocatorHandler(tour,()=>tour.click());
  for(const panel of ['modules','apps','msp']){
    await page.locator('.rail [data-panel="'+panel+'"]').click();
    await expect(page.locator('main')).toHaveClass(new RegExp('showing-'+panel));
    await expect(page.locator('.sidebar')).toBeHidden();
  }
  await page.locator('.rail [data-panel="studio"]').click();
  await expect(page.locator('.sidebar')).toBeVisible();
});

test('SCREEN USABILITY more skills, status filtering and keyboard disclosure',async({page})=>{
  const skills=Array.from({length:27},(_,i)=>({name:'library-'+String(i).padStart(2,'0'),category:'research',disabled:i===26}));
  await page.route('**/api/skills',route=>route.fulfill({json:{skills}}));
  await page.goto('/');
  await expect(page.locator('.wp-hero')).toBeVisible();
  const tour=page.locator('#spHelpCard[data-kind="tour_offer"] .sp-help-btn').first();
  await page.addLocatorHandler(tour,()=>tour.click());
  await page.locator('.rail [data-panel="skills"]').click();
  const grid=page.locator('#librarySkillGrid');
  await expect(page.locator('#librarySkillCount')).toHaveText('24 of 27 skills');
  await page.locator('#libraryMoreSkills').click();
  await expect(grid.locator('button')).toHaveCount(27);
  await expect(grid.locator('button').nth(24)).toBeFocused();
  await page.locator('#librarySkillStatus').selectOption('off');
  await expect(grid.locator('button')).toHaveCount(1);
  await expect(grid.locator('strong')).toHaveText('library-26');
  const group=page.locator('.skills-cat-header').first();
  await group.focus();await page.keyboard.press('Enter');
  await expect(group).toHaveAttribute('aria-expanded','false');
  await group.press('Space');
  await expect(group).toHaveAttribute('aria-expanded','true');
});
