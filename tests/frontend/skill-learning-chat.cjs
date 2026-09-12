// Durable CI/manual browser script; no production or real skill writes.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const server = spawn(process.env.PYTHON || path.join(root,'.venv/bin/python'), ['tests/skill_notice_names_fixture.py'], {cwd:root,stdio:['ignore','pipe','inherit']});
const ready = new Promise((resolve,reject)=>{server.stdout.once('data',data=>{try{resolve(JSON.parse(data.toString()).url)}catch(e){reject(e)}});server.once('error',reject)});
(async()=>{
  const url=await ready;
  const browser=await chromium.launch({headless:true});
  try{
    for(const width of [1440,390]){
      const page=await browser.newPage({viewport:{width,height:900}});
      await page.goto(url);
      await page.getByText(/Skill name was not recorded/).first().waitFor();
      const initialCount=await page.locator('[data-skill-learning-notice]').count();
      await page.getByRole('button',{name:'Confirm skill creation',exact:true}).click();
      await page.waitForFunction(count=>document.querySelectorAll('[data-skill-learning-notice]').length===count,initialCount+1,{timeout:15000});
      await page.getByText('Skill automatically created: deployment-workflow',{exact:true}).first().waitFor({timeout:15000});
      await page.getByRole('button',{name:'Confirm skill patch',exact:true}).click();
      await page.waitForFunction(count=>document.querySelectorAll('[data-skill-learning-notice]').length===count,initialCount+2,{timeout:15000});
      await page.getByText('Skill automatically patched: release-check',{exact:true}).first().waitFor({timeout:15000});
      const count=await page.locator('[data-skill-learning-notice]').count();
      await page.getByRole('button',{name:'Failed patch',exact:true}).click();
      await page.waitForTimeout(11000);
      assert.equal(await page.locator('[data-skill-learning-notice]').count(),count);
      assert.equal(await page.evaluate(()=>S.messages.length),2);
      await page.getByRole('button',{name:'Rebuild chat',exact:true}).click();
      assert.equal(await page.locator('[data-skill-learning-notice]').count(),count);
      await page.reload();
      await page.getByText('Skill automatically patched: release-check',{exact:true}).first().waitFor();
      await page.getByRole('button',{name:'Bob · Same shared chat',exact:true}).click();
      await page.waitForTimeout(300);
      assert.equal(await page.locator('[data-skill-learning-notice]').count(),0);
      await page.getByRole('button',{name:'Hold A then switch to B',exact:true}).click();
      await page.getByText('Chat A response is held; current chat is B.',{exact:true}).waitFor();
      await page.getByRole('button',{name:'Release held response',exact:true}).click();
      await page.waitForTimeout(300);
      assert.equal(await page.locator('[data-skill-learning-notice]').count(),0);
      await page.getByRole('button',{name:'Temporary notice error',exact:true}).click();
      await page.getByRole('button',{name:'Retry',exact:true}).waitFor();
      await page.getByRole('button',{name:'Retry',exact:true}).click();
      await page.getByText('Skill automatically patched: release-check',{exact:true}).first().waitFor();
      await page.close();
    }
  } finally { await browser.close();server.kill(); }
})().catch(error=>{server.kill();console.error(error);process.exitCode=1;});
