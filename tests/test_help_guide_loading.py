"""Exercise the shipped script list and lazy loader in a real browser."""
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUIDE_FILES = {'help-features.js', 'help-msp-features.js', 'help-feature-targets.js', 'help-guide.js', 'help-guide-loader.js'}


@pytest.mark.parametrize('retry,deep_link', [(False, False), (True, False), (False, True)])
def test_guide_downloads_only_on_request_and_retries_failed_catalog(retry, deep_link):
    api = pytest.importorskip('playwright.sync_api')
    index = (ROOT / 'static/index.html').read_text()
    scripts = [src for src in re.findall(r'<script[^>]+src="([^"]+)"', index)
               if src.split('?')[0].split('/')[-1] in GUIDE_FILES]
    with api.sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page()
        requested = []
        fail = [retry]
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))

        def route(request):
            path = urlparse(request.request.url).path
            if path == '/':
                html = '<html><body><button id="helpCardGuide" data-help-guide="">Browse all features</button>'
                html += '<script>function t(k){return k;}function showToast(){};</script>'
                html += ''.join(f'<script src="/{src.replace("__WEBUI_VERSION__", "fixture")}"></script>' for src in scripts)
                return request.fulfill(content_type='text/html', body=html + '</body></html>')
            name = path.rsplit('/', 1)[-1]
            requested.append(name)
            if name == 'help-features.js' and fail[0]:
                fail[0] = False
                return request.abort()
            file = ROOT / path.lstrip('/')
            assert file.parent == ROOT / 'static'
            request.fulfill(content_type='application/javascript', body=file.read_bytes())

        page.route('http://guide.test/**', route)
        try:
            page.goto('http://guide.test/' + ('?help_feature=webui.chat.background' if deep_link else ''))
            if not deep_link:
                assert requested == ['help-guide-loader.js'], 'optional catalogs must not load with the chat'
                page.locator('#helpCardGuide').click()
            if retry:
                page.wait_for_function("!document.getElementById('helpCardGuide').hasAttribute('aria-busy')")
                page.locator('#helpCardGuide').click()
            page.locator('#spFeatureGuide').wait_for(state='visible')
            assert page.evaluate('window.SynthPulseFeatureGuide.featureCount') > 100
            count = len(requested)
            page.keyboard.press('Escape')
            page.locator('#helpCardGuide').click()
            page.locator('#spFeatureGuide').wait_for(state='visible')
            assert len(requested) == count, 'reopening reuses loaded catalogs'
            assert not errors
            saved = sum((ROOT / 'static' / f).stat().st_size for f in GUIDE_FILES if f != 'help-guide-loader.js')
            if not deep_link: print(f'Initial optional JS avoided: {saved} bytes; loader: {(ROOT / "static/help-guide-loader.js").stat().st_size} bytes')
        finally:
            browser.close()


def test_service_worker_caches_optional_catalogs_after_use_not_install():
    import subprocess
    script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const handlers={},added=[],stored=[];
const cache={addAll:async urls=>added.push(...urls),put:async req=>stored.push(req.url)};
const ctx={URL,Request,Response,console,
 self:{location:{origin:'https://app.test'},registration:{scope:'https://app.test/'},addEventListener:(name,fn)=>handlers[name]=fn,skipWaiting(){}},
 caches:{keys:async()=>[],open:async()=>cache,match:async()=>undefined},fetch:async()=>new Response('catalog')};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/sw.js','utf8'),ctx);
(async()=>{
 let installed;handlers.install({waitUntil:p=>installed=p});await installed;
 assert(added.some(url=>url.includes('help-guide-loader.js')));
 for(const name of ['help-features.js','help-msp-features.js','help-feature-targets.js','help-guide.js']){
   assert(!added.some(url=>url.includes('/'+name+'?')));
   const request=new Request('https://app.test/static/'+name+'?v=__WEBUI_VERSION__');
   let response;handlers.fetch({request,respondWith:p=>response=p});assert(response);await response;
 }
 await new Promise(setImmediate);assert.equal(stored.length,4);
 console.log('Optional catalogs are excluded from install and cached after use');
})().catch(error=>{console.error(error);process.exitCode=1});
"""
    subprocess.run(['node', '-e', script], cwd=ROOT, check=True, timeout=20)
