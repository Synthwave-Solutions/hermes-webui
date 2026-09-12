// Isolated rendered-module QA. No provider credentials, external requests or real accounts.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const root = path.resolve(__dirname, '../..');
const output = path.resolve(process.env.SYNTHPULSE_QA_OUTPUT || 'test-results/mcp-setup');
const source = fs.readFileSync(process.env.SYNTHPULSE_JS_OVERRIDE || path.join(root, 'static/integrations.js'), 'utf8');
const fixture = {
  nango: {available: true},
  providers: [
    {key:'unsafe-docs-fixture', display_name:'Unsafe docs fixture', auth_mode:'MCP_OAUTH2', configured:false,
     credential_fields:[], setup_required:true, approval:'none', docs:'javascript:alert(1)', setup_guide_url:''},
    {key:'unsafe-guide-fixture', display_name:'Unsafe guide fixture', auth_mode:'MCP_OAUTH2', configured:true,
     unique_key:'unsafe-guide-fixture', credential_fields:[], approval:'approved',
     docs:'https://user:password@example.test/docs', setup_guide_url:'https://user:password@example.test/docs'},
    {key:'attio-mcp', display_name:'Attio (MCP)', auth_mode:'MCP_OAUTH2', configured:false,
     credential_fields:[], setup_required:true, approval:'approved',
     setup_message:"Finish Attio (MCP)'s OAuth setup in Nango, then refresh SynthPulse. Nango must complete the provider's client registration before a new integration can connect.",
     setup_guide_url:'https://nango.dev/docs/api-integrations/attio-mcp'},
    {key:'granola-mcp', unique_key:'granola-work', display_name:'Granola (MCP)', auth_mode:'MCP_OAUTH2', configured:true,
     credential_fields:[], setup_required:false, approval:'approved',
     setup_guide_url:'https://nango.dev/docs/api-integrations/granola-mcp'},
    {key:'granola-mcp', unique_key:'granola-personal', display_name:'Granola (MCP)', auth_mode:'MCP_OAUTH2', configured:true,
     credential_fields:[], setup_required:false, approval:'approved',
     setup_guide_url:'https://nango.dev/docs/api-integrations/granola-mcp'},
  ]
};
(async()=>{
  fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({headless:true});
  try {
    for (const width of [1440,390]) {
      const context=await browser.newContext({viewport:{width,height:1000}});
      await context.route('**/*',route=>route.abort());
      const page=await context.newPage();
      await page.setContent('<!doctype html><html class="dark"><body style="padding:16px"><main id="mainIntegrations"><h1>SynthPulse Connections</h1><div id="intgGrid" class="intg-grid"></div><div id="toast" role="status"></div></main></body></html>');
      await page.addStyleTag({path:path.join(root,'static/style.css')});
      await page.addScriptTag({content:'window.$=id=>document.getElementById(id); window.showToast=message=>{document.getElementById("toast").textContent=message;};'});
      await page.addScriptTag({content:source});
      await page.addScriptTag({path:path.join(root,'static/governance.js')});
      await page.evaluate(()=>document.dispatchEvent(new Event('DOMContentLoaded')));
      await page.evaluate(fixture=>{
        window.fixture=fixture; window.posts=[];
        _intgCatalog=fixture; _intgConnections=[]; _intgRequests=[];
        _intgMe={email:'admin@example.test',roles:['admin']};
        api=async(url,options={})=>{
          if(url.endsWith('/catalog'))return window.fixture;
          if(options.method==='POST')window.posts.push({url,body:JSON.parse(options.body)});
          if(url.endsWith('/connect'))return {status:'pending_approval'};
          return {};
        };
        _intgRefreshRequests=async()=>{};
        _intgRenderGrid();
      },fixture);
      await page.screenshot({path:path.join(output,`admin-${width}.png`),fullPage:true});
      const attio=page.locator('.intg-card').filter({hasText:'Attio (MCP)'});
      assert.equal(await attio.getByRole('button',{name:'Enable',exact:true}).count(),0,'no creation of an unregistered MCP row');
      assert.equal(await attio.locator('.intg-setup-message').count(),1);
      assert.equal(await attio.getByRole('link',{name:'Setup guide'}).getAttribute('href'),fixture.providers.find(p=>p.key==='attio-mcp').setup_guide_url);
      for (const label of ['Unsafe docs fixture','Unsafe guide fixture']) {
        assert.equal(await page.locator('.intg-card').filter({hasText:label}).getByRole('link').count(),0);
      }
      const work=page.locator('.intg-card').filter({hasText:'granola-work'});
      assert.equal(await work.getByRole('button',{name:'Connect',exact:true}).isEnabled(),true);
      assert.equal(await work.getByRole('link',{name:'Setup guide'}).getAttribute('href'),fixture.providers.find(p=>p.unique_key==='granola-work').setup_guide_url);
      // A normal link click opens the provider's exact guide; network is aborted.
      const popupPromise=page.waitForEvent('popup');
      await work.getByRole('link',{name:'Setup guide'}).click();
      const guidePopup=await popupPromise;
      await guidePopup.waitForLoadState().catch(()=>{});
      await guidePopup.close();
      // Real click keeps the selected unique configuration, closes pending popup.
      const connectPopupPromise=page.waitForEvent('popup');
      await work.getByRole('button',{name:'Connect',exact:true}).click();
      const connectPopup=await connectPopupPromise;
      if (!connectPopup.isClosed()) await connectPopup.waitForEvent('close');
      assert.deepEqual(await page.evaluate(()=>posts),[{url:'/api/integrations/connect',body:{provider_config_key:'granola-work'}}]);
      // Both Enable entry points refresh catalog and stop before POST/dialog.
      await page.evaluate(async()=>{
        posts=[]; _govPost=async(url,body)=>posts.push({url,body});
        await _intgEnable('attio-mcp');
        await _govIntgAction('enable','attio-mcp');
      });
      assert.deepEqual(await page.evaluate(()=>posts),[]);
      assert.match(await page.locator('#toast').innerText(),/Nango.*SynthPulse/);
      assert.equal(await page.locator('dialog').count(),0);
      await page.evaluate(()=>{
        _intgMe={email:'member@example.test',roles:['member']};
        _intgCatalog.providers.find(p=>p.key==='attio-mcp').approval='none';
        _intgCatalog.providers.find(p=>p.unique_key==='granola-work').approval='pending';
        _intgRenderGrid();
      });
      assert.equal(await attio.getByRole('button',{name:'Request access',exact:true}).isEnabled(),true);
      assert.equal(await work.getByRole('button',{name:'Waiting for approval',exact:true}).isDisabled(),true);
      assert.equal(await page.locator('.intg-setup-message').count(),0);
      await page.screenshot({path:path.join(output,`member-${width}.png`),fullPage:true});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'no horizontal overflow');
      await context.close();
    }
    fs.writeFileSync(path.join(output,'result.json'),JSON.stringify({status:'passed',viewports:[1440,390],coverage:'Rendered integration module with stubbed API and blocked external network; no live OAuth proof'},null,2));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
