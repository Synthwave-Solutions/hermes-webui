// Rendered control journeys against tests/fixtures/project-conversation.html.
// Serve the repository on a loopback-only port before running this script.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const base=process.env.PROJECT_QA_ORIGIN||'http://127.0.0.1:8934';
assert.ok(['127.0.0.1','localhost','[::1]'].includes(new URL(base).hostname),'Only isolated loopback fixtures are allowed');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const width of [1360,390]){
   const page=await browser.newPage({viewport:{width,height:844}});
   await page.goto(base+'/tests/fixtures/project-conversation.html');
   await page.locator('#evidence').getByText('private-before-project',{exact:false}).waitFor();
   const evidence=async()=>JSON.parse(await page.locator('#evidence').textContent());
   await page.locator('#mode').selectOption('slow');await page.locator('#new').click();
   await page.getByRole('button',{name:'Creating…',exact:true}).waitFor();
   assert.equal(await page.locator('#new').isDisabled(),true);
   assert.equal((await evidence()).calls.filter(x=>x.url==='/api/projects/chat').length,1);
   await page.locator('#release').click();await page.locator('#feedback').getByText('Opened project conversation',{exact:false}).waitFor();
   await page.locator('#mode').selectOption('offline');await page.locator('#new').click();
   await page.locator('#feedback').getByText('Reference:',{exact:false}).waitFor();
   const id=(await evidence()).calls.filter(x=>x.url==='/api/projects/chat').at(-1).body.request_id;
   await page.reload();await page.locator('#new').click();
   await page.locator('#feedback').getByText('Opened project conversation',{exact:false}).waitFor();
   assert.equal((await evidence()).calls.find(x=>x.url==='/api/projects/chat').body.request_id,id);
   await page.locator('#existing').click();await page.getByText('Test project',{exact:true}).click();
   assert.match(await page.locator('#confirmText').textContent(),/Nothing will be copied/);
   const original=(await evidence()).original;await page.locator('#cancel').click();
   await page.locator('#existing').click();await page.getByText('Test project',{exact:true}).click();await page.locator('#accept').click();
   await page.locator('#feedback').getByText('Opened project conversation',{exact:false}).waitFor();
   assert.deepEqual((await evidence()).original,original);
   assert.equal((await evidence()).calls.some(x=>x.url==='/api/session/move'),false);
   await page.locator('#mode').selectOption('no bots');await page.locator('#new').click();
   await page.locator('#feedback').getByText('No project bot',{exact:false}).waitFor();
   await page.locator('#mode').selectOption('revoked');await page.locator('#new').click();
   await page.locator('#feedback').getByText('Project not found',{exact:true}).waitFor();
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await page.close();
  }
  console.log('Project creation rendered journeys passed at desktop and mobile widths');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
