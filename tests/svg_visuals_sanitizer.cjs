// Headless Chromium matrix for static/svg_visuals.js (plan addendum 3.5).
//
// Usage: node tests/svg_visuals_sanitizer.cjs <playwright module dir> <repo root> [extra JSON]
// The optional extra JSON is {sources:{name:svg}, shapes:{name:[entry,prefix,unit,count,suffix]}}.
// Prints one JSON object on stdout:
//   results  sanitizeSvgSource() output for every fixture, keyed "good/x.svg"
//   sources  the same for every extra source, keyed by name
//   render   the full hydration of every fixture as a chat placeholder:
//            window.__pwned, every request that left the page, figure and
//            fallback counts, decoded image sizes, stray script or handler
//            nodes
//   timing   sanitizeSvgSource() time and answer for every hostile shape
//            (prefix + unit repeated count times + suffix); a shape that
//            runs past SHAPE_LIMIT_MS is marked timedOut and ends the phase,
//            since the page is then stuck
// Driven by tests/test_svg_visuals_sanitizer_js.py; the page has no network:
// the test origin is served from memory and every other request is refused
// and recorded.
'use strict';
const fs=require('fs');
const path=require('path');

const ORIGIN='http://svg-visuals.test';
const SHAPE_LIMIT_MS=10000;

async function main(){
  const [playwrightDir,repo,extraJson]=process.argv.slice(2);
  const extra=extraJson?JSON.parse(extraJson):{};
  const {chromium}=require(playwrightDir);
  const fixtures={};
  for(const kind of ['good','bad']){
    const dir=path.join(repo,'tests','fixtures','svg',kind);
    for(const name of fs.readdirSync(dir).filter(n=>n.endsWith('.svg')).sort()){
      fixtures[kind+'/'+name]=fs.readFileSync(path.join(dir,name),'utf8');
    }
  }
  const script=fs.readFileSync(path.join(repo,'static','svg_visuals.js'),'utf8');
  const browser=await chromium.launch();
  try{
    const context=await browser.newContext();
    const leaked=[];
    await context.route('**/*',route=>{
      const url=route.request().url();
      if(url===ORIGIN+'/'){
        return route.fulfill({status:200,contentType:'text/html',
          body:'<!doctype html><html><head><meta charset="utf-8"></head><body><div id="chat"></div></body></html>'});
      }
      leaked.push(url);
      return route.abort();
    });
    const page=await context.newPage();
    page.on('request',req=>{
      const url=req.url();
      if(url!==ORIGIN+'/'&&!url.startsWith('data:')&&leaked.indexOf(url)===-1) leaked.push(url);
    });
    const errors=[];
    page.on('pageerror',err=>errors.push(String(err)));
    await page.goto(ORIGIN+'/');
    await page.addScriptTag({content:script});

    const sanitizeAll=fx=>{
      const out={};
      for(const [key,src] of Object.entries(fx)){
        const r=sanitizeSvgSource(src);
        out[key]={ok:r.ok,svg:r.svg,title:r.title,box:r.box,reasons:r.reasons,paper:r.paper};
      }
      return out;
    };
    const results=await page.evaluate(sanitizeAll,fixtures);
    const sources=await page.evaluate(sanitizeAll,extra.sources||{});

    const render=await page.evaluate(async fx=>{
      const chat=document.getElementById('chat');
      const keys=Object.keys(fx);
      for(const key of keys){
        const row=document.createElement('div');
        row.className='msg-row';
        row.dataset.fixture=key;
        const block=document.createElement('div');
        block.className='svg-visual-block';
        block.dataset.svgId='svg-test';
        block.textContent=fx[key];
        row.appendChild(block);
        chat.appendChild(row);
      }
      renderSvgVisualBlocks(chat);
      renderSvgVisualBlocks(chat); // idempotent
      const imgs=Array.from(chat.querySelectorAll('img.svg-visual-img'));
      // Visuals load lazily; off-screen ones would never decode here.
      const lazy=imgs.filter(img=>img.loading==='lazy').length;
      imgs.forEach(img=>{img.loading='eager';});
      await Promise.all(imgs.map(img=>Promise.race([img.decode().catch(()=>null),new Promise(r=>setTimeout(r,5000))])));
      await new Promise(r=>setTimeout(r,300));
      const rows={};
      for(const row of chat.querySelectorAll('.msg-row')){
        const img=row.querySelector('img.svg-visual-img');
        const fallback=row.querySelector('.svg-visual-blocked code');
        rows[row.dataset.fixture]={
          figure:!!row.querySelector('figure.svg-visual[data-rendered="1"]'),
          blocked:!!fallback,
          fallbackIsSource:!!fallback&&fallback.textContent===fx[row.dataset.fixture],
          naturalWidth:img?img.naturalWidth:0,
          srcPrefix:img?img.getAttribute('src').slice(0,26):'',
          alt:img?img.alt:'',
          caption:(row.querySelector('figcaption')||{}).textContent||'',
          placeholders:row.querySelectorAll('.svg-visual-block').length,
        };
      }
      const outsideToolbar=Array.from(chat.querySelectorAll('svg')).filter(s=>!s.closest('.svg-visual-toolbar'));
      const handlers=Array.from(chat.querySelectorAll('*')).filter(n=>Array.from(n.attributes).some(a=>/^on/i.test(a.name)));
      return {
        pwned:typeof window.__pwned!=='undefined',
        rows,
        liveSvgNodes:outsideToolbar.length,
        scriptNodes:chat.querySelectorAll('script').length,
        foreignObjects:chat.getElementsByTagNameNS('http://www.w3.org/2000/svg','foreignObject').length,
        handlerNodes:handlers.length,
        lazyImages:lazy,
        imageCount:imgs.length,
      };
    },fixtures);
    await page.waitForTimeout(200);
    render.requests=leaked.slice();
    render.errors=errors.slice();

    const timing={};
    for(const [name,[,prefix,unit,count,suffix]] of Object.entries(extra.shapes||{})){
      const text=prefix+unit.repeat(count)+suffix;
      const outcome=await Promise.race([
        page.evaluate(src=>{
          const began=performance.now();
          const r=sanitizeSvgSource(src);
          return {ms:performance.now()-began,value:{ok:r.ok,reasons:r.reasons}};
        },text),
        new Promise(resolve=>setTimeout(()=>resolve(null),SHAPE_LIMIT_MS)),
      ]);
      if(!outcome){timing[name]={timedOut:true};break;}
      timing[name]=outcome;
    }
    process.stdout.write(JSON.stringify({results,sources,render,timing}));
  } finally {
    await browser.close();
  }
}

main().catch(err=>{
  process.stderr.write(String(err&&err.stack||err));
  process.exit(3);
});
