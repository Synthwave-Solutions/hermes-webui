// Render the real Support UI against synthetic customer-portal responses.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true, ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{})});
 try{for(const lang of ['nl','en'])for(const width of [1440,768,390]){
  const p=await browser.newPage({viewport:{width,height:1000}}),errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  await p.setContent('<html lang="'+lang+'"><body><main id="mainMsp"></main><div id="mspSidebar"></div></body></html>');
  await p.addStyleTag({content:':root{--text:#e3eaf2;--muted:#91a6bc;--surface:#142032;--border:#29445e;--accent:#35adff}body{background:#0b1220;color:var(--text);font:15px system-ui;margin:0}'});
  await p.addStyleTag({path:'static/apps.css'});
  await p.addStyleTag({path:'static/msp.css'});
  await p.evaluate(()=>{
   window.fixture={org:{name:'Example customer'},permissions:{billing:true},support_access:{available_minutes:0,can_submit:false},billing_requests:[
    {id:'paid',service_order_id:'hours-order',product_name:'Two support hours',invoice_ref:'INV-PAID',created_at:'2026-10-10T10:00:00Z',status:'paid',amount_incl_vat_cents:12100,payment:{mode:'live',status:'paid'}},
    {id:'open',product_name:'Infrastructure',invoice_ref:'INV-OPEN',created_at:'2026-10-11T10:00:00Z',status:'invoiced',amount_incl_vat_cents:24200,payment:{mode:'live',status:'open',checkout_url:'https://www.mollie.com/checkout/test'}},
    {id:'failed',product_name:'<img src=x onerror="window.xss=1">',invoice_ref:'INV-FAILED',created_at:'2026-10-12T10:00:00Z',status:'invoiced',amount_incl_vat_cents:5000,payment:{mode:'live',status:'failed',checkout_url:'javascript:alert(1)'}}
   ],service_orders:[],annual_support:[],apps:[]};
   window.api=async path=>path==='/api/msp/overview'?fixture:{tickets:[]};
  });
  await p.addScriptTag({path:'static/msp.js'});
  await p.evaluate(async()=>{SynthPulseMSP.applyVisible(true);await SynthPulseMSP.load();});
  await p.locator('#mspBillingTab').click();
  if(process.env.SUPPORT_BEFORE)await p.screenshot({path:process.env.SUPPORT_BEFORE+'/before-'+lang+'-'+width+'.png',fullPage:true});
  assert.equal(await p.locator('#mspInvoices').getByText('INV-PAID',{exact:true}).isVisible(),true,'Paid service-order invoices must be visible without expanding history');
  assert.equal(await p.locator('#mspInvoices [data-invoice-id]').count(),3);
  assert.match(await p.locator('[data-invoice-id="paid"]').innerText(),lang==='nl'?/Betaald/:/Paid/);
  assert.match(await p.locator('[data-invoice-id="failed"]').innerText(),lang==='nl'?/Mislukt/:/Failed/);
  assert.equal(await p.locator('#mspInvoices a').count(),1);
  assert.equal(await p.locator('#mspInvoices img').count(),0);
  assert.equal(await p.evaluate(()=>!!window.xss),false);
  const filter=p.getByLabel(lang==='nl'?'Betaalstatus':'Payment status',{exact:true});
  await filter.selectOption('paid');assert.equal(await p.locator('#mspInvoices [data-invoice-id]').count(),1);
  await filter.selectOption('open');assert.equal(await p.locator('#mspInvoices [data-invoice-id]').count(),2);
  await filter.selectOption('all');
  assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  if(process.env.SUPPORT_SCREENSHOTS)await p.screenshot({path:process.env.SUPPORT_SCREENSHOTS+'/payments-'+lang+'-'+width+'.png',fullPage:true});
  await p.evaluate(async()=>{fixture.billing_requests=[];await SynthPulseMSP.load();});
  assert.equal(await p.locator('#mspInvoices [data-invoice-id]').count(),0);
  assert.ok(await p.locator('#mspInvoices').getByText(lang==='nl'?'Nog geen betaalverzoeken of facturen.':'No payment requests or invoices yet.',{exact:true}).isVisible());
  await p.evaluate(async()=>{fixture.permissions.billing=false;await SynthPulseMSP.load();});
  assert.equal(await p.locator('#mspInvoices').count(),0);
  assert.deepEqual(errors,[]);await p.close();
 }}finally{await browser.close();}
 console.log('Support payments: NL/EN, desktop/tablet/mobile, paid/open/failed, safe links, empty and restricted views passed');
})().catch(e=>{console.error(e);process.exit(1)});
