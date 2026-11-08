"""The "flow" data block: the checks and layout in Node, and the drawing in a
real browser (keyboard, restore, a single tab stop, the phone layout)."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")

BUILD = r"""
const path=require('path'),fs=require('fs');
const K=require(path.join(process.argv[1],'static/interactive-ui/kit-core.js'));
global.SWKit=K;
require(path.join(process.argv[1],'static/interactive-ui/kinds/flow.js'));
const r=K.build('flow',process.argv[2],{lang:'nl'});
process.stdout.write(JSON.stringify({spec:r.spec,errors:r.errors}));
"""

ONBOARDING = {
    "title": "Onboarding",
    "nodes": [
        {"id": "c", "label": "Contract getekend", "type": "start", "owner": "HR"},
        {"id": "acc", "label": "Accounts aanmaken", "owner": "IT"},
        {"id": "lap", "label": "Laptop nodig?", "type": "decision", "owner": "Operations"},
        {"id": "best", "label": "Laptop bestellen", "owner": "Inkoop", "note": "Binnen een dag"},
        {"id": "eigen", "label": "Eigen laptop inrichten", "owner": "IT"},
        {"id": "vog", "label": "VOG binnen?", "type": "decision", "owner": "HR"},
        {"id": "herinn", "label": "Herinnering sturen", "owner": "HR"},
        {"id": "dag1", "label": "Eerste werkdag", "type": "end"},
    ],
    "edges": [["c", "acc"], ["acc", "lap"], ["lap", "best", "Ja"], ["lap", "eigen", "Nee"], ["best", "vog"],
              ["eigen", "vog"], ["vog", "dag1", "Ja"], ["vog", "herinn", "Nee"], ["herinn", "vog", "Na 3 dagen"]],
}

THREE_WAY = {
    "title": "Escalatie",
    "steps": [
        {"id": "m", "label": "Melding", "type": "start"}, {"id": "p", "label": "Prioriteit?", "type": "decision"},
        {"id": "h", "label": "Hoog: direct bellen"}, {"id": "mid", "label": "Midden: binnen 4 uur"},
        {"id": "l", "label": "Laag: in de wachtrij"}, {"id": "x", "label": "Opgelost", "type": "end"},
    ],
    "links": ["m -> p", {"from": "p", "to": "h", "label": "Hoog"}, {"from": "p", "to": "mid", "label": "Midden"},
              {"from": "p", "to": "l", "label": "Laag"}, "h -> x", "mid -> x", "l -> x",
              {"from": "x", "to": "m", "label": "Heropend"}],
}

# Records what the renderer saves, before kits.js hands it to the host.
SPY = """
(() => {
  let real;
  Object.defineProperty(window, 'SWKitRender', {configurable: true,
    get(){ return real; },
    set(v){ const save = v.save; v.save = function(x){ (window.__saved = window.__saved || []).push(x); return save.call(this, x); }; real = v; }});
})();
"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_flow_kind_in_node():
    result = subprocess.run([NODE, str(ROOT / "tests" / "kinds_flow.cjs")], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().endswith("ok")


def _spec(value):
    out = subprocess.run([NODE, "-e", BUILD, str(ROOT), json.dumps(value)], capture_output=True, text=True, check=True, timeout=60)
    res = json.loads(out.stdout)
    assert res["errors"] == []
    return res["spec"]


def _page(browser, spec, width, restore):
    from api import interactive_ui
    payload = {"kit": "flow", "spec": spec, "data": None, "final": True, "restore": restore, "lang": "nl", "theme": "light"}
    doc = interactive_ui.KIT_FRAME_HTML
    at = doc.index("<script>")
    doc = doc[:at] + "<script>" + SPY + "window.__SWKIT_DOC=" + json.dumps(payload).replace("<", "\\u003c") + ";</script>" + doc[at:]
    page = browser.new_page(viewport={"width": width, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.set_content(doc)
    page.wait_for_selector(".k-flow-node")
    page.wait_for_timeout(300)
    return page, errors


STATE = """() => ({
  pressed: [...document.querySelectorAll('.k-flow-node')].filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.querySelector('.k-flow-label').textContent),
  stops: [...document.querySelectorAll('.k-flow-node')].filter(b => b.tabIndex === 0).length,
  focus: document.activeElement && document.activeElement.classList.contains('k-flow-node') ? document.activeElement.querySelector('.k-flow-label').textContent : '',
  detail: document.querySelector('.k-flow-detail').textContent,
  saved: window.__saved || []
})"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_flow_keyboard_restore_and_phone_width():
    api = pytest.importorskip("playwright.sync_api")
    onboarding, three = _spec(ONBOARDING), _spec(THREE_WAY)
    with api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # pragma: no cover - no browser on this machine
            pytest.skip(f"chromium is not available: {exc}")
        try:
            page, errors = _page(browser, onboarding, 760, {"a": 2})
            s = page.evaluate(STATE)
            assert s["pressed"] == ["Laptop nodig?"], "restore {a:2} selects the third step"
            assert s["stops"] == 1, "one tab stop"
            assert s["detail"].startswith("Laptop nodig? · Keuze · Operations · Daarna: Laptop bestellen (Ja)")
            assert s["saved"] == [], "a restore is not saved again"

            page.keyboard.press("Tab")
            assert page.evaluate(STATE)["focus"] == "Laptop nodig?", "tab lands on the selected step"
            page.keyboard.press("ArrowDown")
            s = page.evaluate(STATE)
            assert s["focus"] == "Laptop bestellen"
            assert s["pressed"] == ["Laptop nodig?"], "arrows move focus, they do not select"
            assert s["stops"] == 1
            # The steps sit in the DOM in reading order, so Tab follows the drawing.
            order = page.evaluate("[...document.querySelectorAll('.k-flow-node .k-flow-label')].map(e => e.textContent)")
            assert order[0] == "Contract getekend" and sorted(order) == sorted(n["label"] for n in onboarding["nodes"])
            page.keyboard.press("End")
            last = order[-1]
            assert page.evaluate(STATE)["focus"] == last
            page.keyboard.press("Enter")
            page.wait_for_timeout(400)
            s = page.evaluate(STATE)
            k = [n["label"] for n in onboarding["nodes"]].index(last)
            assert s["pressed"] == [last]
            assert s["detail"].startswith(last)
            assert s["saved"][-1] == {"a": k}
            page.keyboard.press("Home")
            assert page.evaluate(STATE)["focus"] == "Contract getekend"
            page.keyboard.press(" ")
            page.wait_for_timeout(400)
            s = page.evaluate(STATE)
            assert s["pressed"] == ["Contract getekend"] and s["stops"] == 1
            assert s["detail"] == "Contract getekend · Start · HR · Daarna: Accounts aanmaken"
            assert s["saved"][-1] == {"a": 0}
            # Selected and focused look different: a fill for one, a dashed ring for the other.
            looks = page.evaluate("""() => {
              const a = document.querySelector('.k-flow-node.is-active'), cs = getComputedStyle(a);
              return {selectedOutline: cs.outlineStyle, focusOutline: getComputedStyle(document.activeElement).outlineStyle, ring: cs.boxShadow};
            }""")
            assert looks["focusOutline"] == "dashed"
            assert "inset" in looks["ring"]
            assert errors == []
            page.close()

            # A spec that asks for "right" runs down on a phone and fits without scrolling.
            page, errors = _page(browser, dict(onboarding, direction="right"), 390, {})
            assert page.evaluate("document.querySelector('.k-flow-canvas').classList.contains('is-right')") is False
            page.close()

            # A three-way decision with a loop fits a phone: no sideways scroll, nothing past the edge.
            page, errors = _page(browser, three, 390, {})
            fit = page.evaluate("""() => {
              const s = document.querySelector('.k-flow-scroll');
              const out = [...document.querySelectorAll('.k-flow-node, .k-flow-elabel')].filter(e => e.getBoundingClientRect().right > innerWidth + 0.5);
              return {wide: s.classList.contains('is-wide'), over: s.scrollWidth - s.clientWidth, out: out.map(e => e.textContent),
                upright: [...document.querySelectorAll('.k-flow-elabel.is-up')].map(e => e.textContent)};
            }""")
            assert fit == {"wide": False, "over": 0, "out": [], "upright": ["Heropend"]}
            assert errors == []
            page.close()
        finally:
            browser.close()
