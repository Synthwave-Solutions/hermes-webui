// Run manually/CI with PLAYWRIGHT_MODULE_PATH set; serves this checkout only.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const server = spawn(process.env.PYTHON || 'python3', ['-m','http.server','8899','--bind','127.0.0.1'], {cwd:root,stdio:'ignore'});
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    for(const width of [1440,390]){
      const page=await browser.newPage({viewport:{width,height:900}});
      await page.goto('http://127.0.0.1:8899/tests/frontend/skill-learning-chat-fixture.html');
      await page.getByText('Skill automatically created · Skill automatically patched × 2',{exact:true}).waitFor();
      const order=await page.locator('#msgInner > *').allTextContents();
      assert.match(order[2],/Skill automatically created/);
      assert.equal(order[3],'Continue with the next task.');
      assert.equal(await page.evaluate(()=>S.messages.length),3);
      await page.getByRole('button',{name:'Rebuild chat',exact:true}).click();
      assert.equal(await page.locator('[data-skill-learning-notice]').count(),1);
      await page.getByRole('button',{name:'Simulate temporary error',exact:true}).click();
      await page.getByRole('button',{name:'Retry',exact:true}).waitFor();
      await page.getByRole('button',{name:'Retry',exact:true}).click();
      await page.getByText('Skill automatically created · Skill automatically patched × 2',{exact:true}).waitFor();
      await page.getByRole('button',{name:'Delayed A response → B',exact:true}).click();
      await page.waitForTimeout(1800);
      assert.equal(await page.locator('[data-skill-learning-notice]').count(),0);
      await page.getByRole('button',{name:'Delayed A → loading B',exact:true}).click();
      await page.waitForTimeout(2300);
      assert.equal(await page.locator('[data-skill-learning-notice]').count(),0);
      assert.equal(await page.locator('#msgInner').textContent(),'Conversation B could not load.');
      await page.getByRole('button',{name:'Conversation A',exact:true}).click();
      await page.getByText('Skill automatically created · Skill automatically patched × 2',{exact:true}).waitFor();
      await page.reload();
      await page.getByText('Skill automatically created · Skill automatically patched × 2',{exact:true}).waitFor();
      assert.equal(await page.locator('[data-skill-learning-notice]').count(),1);
      await page.close();
    }
  } finally { await browser.close();server.kill(); }
})().catch(error=>{server.kill();console.error(error);process.exitCode=1;});
