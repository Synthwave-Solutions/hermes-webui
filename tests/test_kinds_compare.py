"""Data block "compare": the checks in Node and the cards in a real browser.

``tests/kinds_compare.cjs`` runs the checks (scales, currencies, units, the
recommended option, the export). The browser part draws the standalone kit
page the way "Downloaden" gives it and checks that values reach the page as
text, that there is one recommended badge, that the cards are one tab stop
moved by the arrow keys, that a restored position sets the dot, and that four
cards swipe instead of overflowing on a narrow frame.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_compare_checks_in_node():
    result = subprocess.run([NODE, str(REPO / "tests" / "kinds_compare.cjs")], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith("ok")


_BUILD = r"""
const path=require('path'),fs=require('fs');
const K=require(path.join(process.argv[1],'static/interactive-ui/kit-core.js'));
global.SWKit=K;
require(path.join(process.argv[1],'static/interactive-ui/kinds/compare.js'));
const r=K.build('compare',process.argv[2],{lang:'nl',fence:'compare'});
process.stdout.write(JSON.stringify(r.spec));
"""

EVIL = '<img src=x onerror="window.__hit=1">'
SPEC = {
    "title": "Laptops",
    "recommended": "Bechtle",
    "options": [
        {"name": EVIL, "price": 124999.95, "priceUnit": "eenmalig", "score": "8,5", "facts": {"Levertijd": "1 week"}, "pros": ["<b>vet</b>"]},
        {"name": "Bechtle", "price": "€ 1.249.000", "score": "72%", "tag": "Snelste levering met een lang label dat moet afbreken", "facts": {"Levertijd": "2 dagen"}},
        {"name": "Centralpoint Technologies", "price": "$ 54,000", "score": 7, "cons": ["Duur"]},
        {"name": "Coolblue", "price": 45, "priceUnit": "maand", "score": "7/10"},
    ],
}


def _page_html(spec, theme="light", restore=None):
    from api import interactive_ui

    payload = {"kit": "compare", "spec": spec, "data": None, "final": True, "restore": restore or {}, "lang": "nl", "theme": theme}
    doc = interactive_ui.KIT_FRAME_HTML
    at = doc.index("<script>")
    return doc[:at] + "<script>window.__SWKIT_DOC=" + json.dumps(payload).replace("<", "\\u003c") + ";</script>" + doc[at:]


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_compare_cards_in_the_browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    spec = json.loads(subprocess.run([NODE, "-e", _BUILD, str(REPO), json.dumps(SPEC)], capture_output=True, text=True, check=True).stdout)
    assert spec["options"][1]["score"] == 72 and spec["options"][0]["score"] == 85
    errors: list[str] = []
    with sync_api.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        except Exception as exc:  # pragma: no cover - no browser on this machine
            pytest.skip(f"chromium is not available: {exc}")
        try:
            # Wide: side by side, text only, one badge, one tab stop.
            page = browser.new_page(viewport={"width": 900, "height": 900})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.set_content(_page_html(spec))
            page.wait_for_selector(".k-cmp-card")
            info = page.evaluate(
                """() => {
                  const cards = [...document.querySelectorAll('.k-cmp-card')];
                  const label = c => c.getAttribute('aria-labelledby').split(' ').map(id => document.getElementById(id).textContent).join(' ');
                  const desc = c => (c.getAttribute('aria-describedby') || '').split(' ').filter(Boolean).map(id => document.getElementById(id).textContent).join(' ');
                  return {
                    imgs: document.querySelectorAll('.k-cmp img, .k-cmp b').length, hit: !!window.__hit,
                    name0: cards[0].querySelector('.k-cmp-name').firstChild.textContent,
                    badges: document.querySelectorAll('.k-cmp-badge.is-rec').length,
                    recCard: cards.findIndex(c => c.classList.contains('is-rec')),
                    tabStops: cards.filter(c => c.tabIndex === 0).length,
                    swipe: document.querySelector('.k-cmp').classList.contains('is-swipe'),
                    dotsHidden: document.querySelector('.k-cmp-dots').hidden,
                    label1: label(cards[1]), desc1: desc(cards[1]),
                    prices: cards.map(c => c.querySelector('.k-cmp-price').textContent),
                    over: cards.some(c => [...c.querySelectorAll('*')].some(e => { const r = e.getBoundingClientRect(), b = c.getBoundingClientRect(); return r.width && !e.classList.contains('k-sr') && (r.right > b.right + 0.5 || r.left < b.left - 0.5); })),
                  };
                }"""
            )
            assert info["imgs"] == 0 and not info["hit"]
            assert info["name0"] == EVIL
            assert info["badges"] == 1 and info["recCard"] == 1
            assert info["tabStops"] == 1
            assert not info["swipe"] and info["dotsHidden"]
            assert "Bechtle" in info["label1"] and "Optie 2 van 4" in info["label1"]
            assert "Aanrader" in info["desc1"] and "72 van 100" in info["desc1"] and "2 dagen" in info["desc1"]
            assert "$ 54,000" in info["prices"][2] and "€" not in info["prices"][2]
            assert "per maand" in info["prices"][3]
            assert not info["over"], "a value spills out of its card"

            page.focus(".k-cmp-card:nth-child(1)")
            page.keyboard.press("ArrowRight")
            focus = page.evaluate("() => [...document.querySelectorAll('.k-cmp-card')].indexOf(document.activeElement)")
            assert focus == 1
            assert page.evaluate("() => [...document.querySelectorAll('.k-cmp-card')].map(c => c.tabIndex)") == [-1, 0, -1, -1]
            page.keyboard.press("End")
            assert page.evaluate("() => [...document.querySelectorAll('.k-cmp-card')].indexOf(document.activeElement)") == 3
            page.close()

            # Narrow: four cards swipe, nothing spills, and a restored position sets the dot.
            for width in (640, 390):
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.set_content(_page_html(spec, "dark", {"i": 2}))
                page.wait_for_selector(".k-cmp-card")
                page.wait_for_timeout(300)
                info = page.evaluate(
                    """() => ({
                      swipe: document.querySelector('.k-cmp').classList.contains('is-swipe'),
                      dotsHidden: document.querySelector('.k-cmp-dots').hidden,
                      current: [...document.querySelectorAll('.k-cmp-dot')].map(d => d.getAttribute('aria-current')),
                      docW: document.documentElement.scrollWidth,
                      scrolled: document.querySelector('.k-cmp').scrollLeft,
                    })"""
                )
                assert info["swipe"] and not info["dotsHidden"], width
                assert info["current"] == ["false", "false", "true", "false"], width
                assert info["scrolled"] > 0, width
                assert info["docW"] <= width, width
                page.close()
        finally:
            browser.close()
    assert not errors, errors
