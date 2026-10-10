import {test,expect,open,api} from './fixtures';
import fs from 'node:fs';
import path from 'node:path';

for(const width of [1440,390]) {
 test(`release SVG and help preserve composer at ${width}px`,async({page},info)=>{
  await page.setViewportSize({width,height:900});await open(page);
  await page.locator('#msg').fill('typing dismisses the optional tour');
  await expect(page.locator('#spHelpCard[data-kind="tour_offer"]')).toHaveCount(0);
  const svg=fs.readFileSync(path.resolve('tests/fixtures/svg/good/layer-stack.svg'),'utf8');
  const seeded=await api(page,'/api/session/import',{title:'Release visual validation',messages:[{role:'user',content:'Show the architecture'},{role:'assistant',content:'```svg\n'+svg+'\n```\nThe interface sits on automation, which sits on data.'}]});
  expect(seeded.status).toBe(200);
  await page.goto('/session/'+seeded.body.session.session_id);
  await expect(page.locator('figure.svg-visual')).toBeVisible();
  await expect.poll(()=>page.locator('img.svg-visual-img').evaluate((e:HTMLImageElement)=>e.complete&&e.naturalWidth>0)).toBe(true);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath('svg-'+width+'.png')});
  await page.locator('#btnPageHelp').click();
  await expect(page.locator('[role="dialog"]:visible').first()).toBeVisible();
  await page.screenshot({path:info.outputPath('help-'+width+'.png')});
 });
}

test('release group default survives reload and selects the permitted bot',async({page})=>{
 await open(page);
 const created=await api(page,'/api/session/new',{profile:'default',bot_participants:['default','qa-research']});expect(created.status).toBe(200);
 const sid=created.body.session.session_id;
 const updated=await api(page,'/api/session/participants',{session_id:sid,bot_participants:['default','qa-research'],participants:[],default_bot:'qa-research'});expect(updated.status).toBe(200);
 await page.goto('/session/'+sid);
 await expect(page.locator('#chatBotRoster [data-default-bot="qa-research"]')).toHaveAttribute('aria-pressed','true');
 await page.reload();
 expect((await api(page,'/api/session?session_id='+sid)).body.session.default_bot).toBe('qa-research');
 await page.locator('#msg').fill('QA_RELEASE_DEFAULT_BOT');await page.locator('#btnSend').click();
 await expect(page.locator('#messages')).toContainText('QA_REPLY: QA_RELEASE_DEFAULT_BOT',{timeout:30000});
 const read=(await api(page,'/api/session?session_id='+sid)).body.session;
 const reply=read.messages.find((m:any)=>m.role==='assistant'&&String(m.content).includes('QA_REPLY: QA_RELEASE_DEFAULT_BOT'));
 expect(reply.bot_profile).toBe('qa-research');expect(reply.route_reason).toBe('default');
});

test('release Memory explorer reads real private bank through sandbox bridge',async({page},info)=>{
 await open(page,'memory');
 await expect(page.locator('#memoryPanel')).toContainText('Memory explorer');
 await page.locator('#memoryPanel button').filter({hasText:'Memory explorer'}).click();
 const frame=page.frameLocator('iframe.memdash-frame');
 await expect(page.locator('iframe.memdash-frame')).toBeVisible();
 await expect.poll(()=>frame.locator('body').innerText()).toContain('QA personal memory for admin');
 await page.screenshot({path:info.outputPath('memory-desktop.png')});
 await page.setViewportSize({width:390,height:900});
 await page.screenshot({path:info.outputPath('memory-mobile.png')});
});
