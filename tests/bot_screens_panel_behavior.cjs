// Real workspace tab/entry code against an isolated browser shell. No credentials.
// PLAYWRIGHT_MODULE and PLAYWRIGHT_CHROMIUM_EXECUTABLE may select a local runtime.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=process.env.TEST_SOURCE_ROOT||path.resolve(__dirname,'..');
const index=fs.readFileSync(path.join(root,'static/index.html'),'utf8');
const panel=index.slice(index.indexOf('<aside class="rightpanel">'),index.indexOf('</aside>',index.indexOf('<aside class="rightpanel">'))+8);

(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{})});
  try{
    for(const granted of [false,true]){
      const page=await browser.newPage({viewport:{width:1100,height:800}});
      page.setDefaultTimeout(5000);
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      let frames=0;
      await page.route('http://screen.test/**',async route=>{
        const url=new URL(route.request().url());
        if(url.pathname==='/api/bot-screen')return route.fulfill({json:granted?{bots:[{id:'test-bot'}]}:{bots:[]}});
        if(url.pathname==='/static/bot-screens.html'){frames++;return route.fulfill({contentType:'text/html',body:'<p>Isolated screen frame</p>'});}
        if(url.pathname.startsWith('/static/'))return route.fulfill({contentType:url.pathname.endsWith('.css')?'text/css':'text/javascript',body:fs.readFileSync(path.join(root,url.pathname))});
        return route.fulfill({contentType:'text/html',body:`<!doctype html><html class="dark"><head><link rel="stylesheet" href="/static/style.css"></head><body>
          <a id="btnBotScreens" hidden style="display:none">Bot Screens</a>${panel}
          <script>const $=id=>document.getElementById(id);const t=key=>key;const S={activeProfile:'test-bot',session:null,messages:[],todos:[]};function syncWorkspacePanelUI(){}</script>
          <script src="/static/workspace.js"></script><script src="/static/bot-screens-link.js"></script></body></html>`});
      });
      await page.goto('http://screen.test/');
      if(!granted){
        await page.evaluate(()=>switchWorkspacePanelTab('screens'));
        assert.equal(await page.locator('#workspaceScreensTab').isVisible(),false);
        assert.equal(await page.locator('#workspaceScreensFrame').count(),0);
      }else{
        await page.locator('#workspaceScreensTab').waitFor();
        assert.equal(frames,0,'viewer must load lazily');
        await page.locator('#workspaceScreensTab').click();
        await page.frameLocator('#workspaceScreensFrame').locator('p').waitFor();
        assert.equal(await page.locator('#workspaceScreensTab').getAttribute('aria-selected'),'true');
        const src=await page.locator('#workspaceScreensFrame').getAttribute('src');
        assert.equal(new URL(src,'http://screen.test').searchParams.get('bot'),'test-bot');
        assert.equal(await page.locator('#fileTree').isVisible(),false);
        await page.evaluate(()=>{document.getElementById('previewArea').classList.add('visible');document.getElementById('previewEditArea').value='Unsaved draft';window.originalScreen=document.getElementById('workspaceScreensFrame');});
        assert.equal(await page.locator('#previewArea').isVisible(),false);
        for(const tab of ['files','artifacts','screens'])await page.evaluate(tab=>switchWorkspacePanelTab(tab),tab);
        assert.equal(await page.evaluate(()=>window.originalScreen===document.getElementById('workspaceScreensFrame')),true);
        assert.equal(await page.locator('#previewEditArea').inputValue(),'Unsaved draft');
        assert.equal(frames,1,'switching tabs must preserve the same viewer/lease');
        await page.evaluate(()=>showPreview('image'));
        assert.equal(await page.locator('#previewArea').isVisible(),true,'opening a document must reveal its preview');
        await page.locator('#workspaceScreensTab').click();
        assert.equal(await page.evaluate(()=>window.originalScreen===document.getElementById('workspaceScreensFrame')),true);
        await page.setViewportSize({width:390,height:800});
        await page.evaluate(()=>document.querySelector('.rightpanel').classList.add('mobile-open'));
        assert.equal(await page.locator('#workspaceScreensTab').isVisible(),true);
        assert.equal(await page.locator('#workspaceScreensFrame').isVisible(),true);
      }
      assert.deepEqual(errors,[]);
      await page.close();
    }
    console.log('Bot Screens panel: grants, lazy mount, active bot, tab lifetime, unsaved preview and mobile passed');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
