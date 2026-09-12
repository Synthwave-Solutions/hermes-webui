// Durable rendered picker/switch journeys. See fixture disclaimer for adapter scope.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const base=process.env.PROFILE_QA_ORIGIN||'http://127.0.0.1:8935';
assert.ok(['127.0.0.1','localhost','[::1]'].includes(new URL(base).hostname),'Only isolated loopback fixtures');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const width of [1360,390]){
   const page=await browser.newPage({viewport:{width,height:844}});
   await page.goto(base+'/tests/fixtures/default-profile-recovery.html');
   await page.getByRole('button',{name:'Own bot conversation',exact:true}).waitFor();
   const evidence=async()=>JSON.parse(await page.locator('#evidence').textContent());
   const originals=(await evidence()).originals;
   await page.getByRole('button',{name:'Own bot conversation',exact:true}).click();
   await page.locator('#mode').selectOption('slow');
   await page.locator('#profileChip').click();await page.locator('.profile-opt-name').filter({hasText:'SynthPulse'}).click();
   assert.equal(await page.locator('#profileChip').isDisabled(),true);
   await page.getByText('Loading conversations…',{exact:true}).waitFor();
   await page.locator('#release').click();
   await page.getByRole('button',{name:'Morning conversation',exact:true}).click();
   assert.equal(await page.locator('#transcript').textContent(),'My morning notes');
   await page.locator('#mode').selectOption('denied');
   await page.locator('#profileChip').click();await page.locator('.profile-opt-name').filter({hasText:'Own bot'}).click();
   await page.getByText('Switch failed: profile_not_allowed',{exact:true}).waitFor();
   assert.equal((await evidence()).active,'default');
   assert.equal(await page.locator('#profileChip').isDisabled(),false);
   await page.getByRole('button',{name:'Morning conversation',exact:true}).waitFor();
   await page.locator('#mode').selectOption('success');
   await page.locator('#profileChip').click();await page.locator('.profile-opt-name').filter({hasText:'Own bot'}).click();
   await page.getByRole('button',{name:'Own bot conversation',exact:true}).waitFor();
   assert.deepEqual((await evidence()).originals,originals);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await page.close();
  }
  console.log('Default profile rendered recovery journeys passed at desktop and mobile widths');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
