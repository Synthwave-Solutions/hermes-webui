"""Task overview uses production rendering, locales and styles; no live tasks."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('width', [390, 820, 1440])
def test_task_overview_is_readable_keyboard_accessible_and_session_scoped(width):
    api = pytest.importorskip('playwright.sync_api')
    src = (ROOT / 'static/messages.js').read_text()
    chunk = src[src.index('let _bgPollTimers='):src.index('// ── Panel navigation', src.index('let _bgPollTimers='))]
    badge = re.search(r'<button[^>]+id="bgBadge".*?</button>', (ROOT / 'static/index.html').read_text()).group()
    with api.sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': width, 'height': 800})
        try:
            page.set_content('<html><body><main style="padding:20px"><h1>SynthPulse</h1><textarea id="msg"></textarea>' + badge + '</main></body></html>')
            page.add_style_tag(content=(ROOT / 'static/style.css').read_text())
            i18n = (ROOT / 'static/i18n.js').read_text().split('window.i18nReady=')[0]
            i18n = i18n.replace("(document.currentScript&&new URL(document.currentScript.src).searchParams.get('v'))", 'null')
            page.add_script_tag(content=i18n)
            for locale in ['en', 'nl']:
                page.add_script_tag(content=(ROOT / f'static/i18n/{locale}.js').read_text())
            page.evaluate("() => {_locale=LOCALES.nl;}")
            page.add_script_tag(content="""
              const S={session:{session_id:'a'},messages:[]};const $=id=>document.getElementById(id);
              const resolvers=[];function api(){return new Promise(resolve=>resolvers.push(resolve));}
              function renderMessages(){}function showToast(){}function loadSession(id){window.openedSession=id;}
            """ + chunk)
            page.evaluate("""() => {
              showBackgroundBadge('one');startBackgroundPolling('a','one','Controleer de offerte <script>geen HTML</script>');
              showBackgroundBadge('two');startBackgroundPolling('a','two','Maak een overzicht van de openstaande acties');
            }""")
            badge_node = page.locator('#bgBadge')
            assert badge_node.get_attribute('aria-label') == '2 achtergrondtaken'
            badge_node.focus()
            page.keyboard.press('Enter')
            dialog = page.locator('#bgTaskDialog')
            dialog.wait_for(state='visible')
            import os
            evidence=os.environ.get('SYNTHPULSE_UX_EVIDENCE_DIR')
            if evidence:
                Path(evidence).mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(Path(evidence)/f'tasks-after-{width}.png'))
            assert page.locator('#bgTaskList li').count() == 2
            assert page.locator('#bgTaskList script').count() == 0
            assert 'Controleer de offerte <script>' in dialog.inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('#bgTaskList button').first.bounding_box()['height'] >= 44
            page.keyboard.press('Escape')
            assert badge_node.evaluate('(el)=>el===document.activeElement')
            badge_node.click()
            page.evaluate("() => {S.session={session_id:'b'};resolvers[0]({results:[{task_id:'one',answer:'Resultaat voor a'}]});}")
            page.get_by_text('Resultaat klaar', exact=True).wait_for()
            assert page.locator('#bgTaskList button').first.evaluate('(el)=>el===document.activeElement')
            assert page.evaluate('S.messages.length') == 0
            page.locator('#bgTaskList button').first.click()
            assert page.evaluate('window.openedSession') == 'a'
            assert not dialog.is_visible()
        finally:
            browser.close()


def test_polling_coalesces_results_and_cleans_up_deleted_sessions():
    import subprocess
    subprocess.run(['node', 'tests/background_polling_behavior.cjs'], cwd=ROOT, check=True, timeout=20)
