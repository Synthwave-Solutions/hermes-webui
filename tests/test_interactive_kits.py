"""Data blocks: the shared kit helpers in Node and the renderer's DOM rules.

``tests/interactive_kits.cjs`` runs ``static/interactive-ui/kit-core.js``
over valid, fixable and fatal fixtures for ```table, ```csv, ```chart,
```map, ```kpi and ```timeline, Dutch numbers, CSV quoting, exports, the NL
lat/lng swap, the timeline axis and periods, and the fence seam in
``static/interactive_ui.js``. The browser behaviour is covered
by ``tests/browser_interactive_ui.py`` (step 10).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
KITS = (REPO / "static" / "interactive-ui" / "kits.js").read_text(encoding="utf-8")
CORE = (REPO / "static" / "interactive-ui" / "kit-core.js").read_text(encoding="utf-8")
MAP_HOST = (REPO / "static" / "interactive_ui_map.js").read_text(encoding="utf-8")
NODE = shutil.which("node")
LONG_DASHES = "[" + chr(0x2013) + chr(0x2014) + "]"


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_kit_helpers_in_node():
    result = subprocess.run([NODE, str(REPO / "tests" / "interactive_kits.cjs")], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all kit checks passed" in result.stdout


def _code(text):
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))


def test_renderers_never_write_markup_or_run_strings():
    code = _code(KITS)
    for token in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function", "srcdoc"):
        assert token not in code, token
    # Only the chat may talk to the frame, and links leave through it.
    assert "if(e.source !== host || (HOST_OK && e.origin !== HOST_ORIGIN)) return;" in KITS
    assert "if(!/^https:\\/\\//i.test(url)) return;" in KITS
    assert "window.open(" in KITS and "if(standalone)" in KITS  # only in a downloaded copy
    # Map values are checked again before they reach the network.
    assert "var PHOTO_PREFIX = 'https://upload.wikimedia.org/wikipedia/commons/';" in KITS
    assert "K.tileUrlOk(data.tiles.url)" in KITS
    assert "Number.isFinite(lat) && Number.isFinite(lng)" in KITS
    assert "scrollIntoView" not in code, "the list scrolls itself, never the chat"
    assert "scrollWheelZoom:false" in KITS and "referrerPolicy:'origin'" in KITS


def test_frame_accepts_only_kit_theme_measure_and_scroll_messages():
    handled = set(re.findall(r"msg\.type === '([a-z-]+)'", KITS))
    # scroll: the chat asks the frame to scroll itself (bounded) so tapped details come into view.
    assert handled == {"theme", "kit", "measure", "scroll"}, handled


def test_kpi_and_timeline_carry_meaning_beyond_colour():
    # A delta pill has an arrow and a sign plus a spoken "gunstig"/"ongunstig".
    assert "h('span', 'k-sr', ', ' + T(tone === 'good' ? 'good' : tone === 'bad' ? 'bad' : 'flat'))" in KITS
    assert "good:'gunstig', bad:'ongunstig'" in KITS
    # Bars are real buttons with a spoken period; the detail line is a live status.
    assert "detail.setAttribute('role', 'status');" in KITS
    assert "b.setAttribute('aria-label', [it.label, period" in KITS
    assert "e.key === 'ArrowDown'" in KITS
    css = (REPO / "static" / "interactive-ui" / "kits.css").read_text(encoding="utf-8")
    assert "@media (max-width:479px)" in css and ".k-tl-chart{display:flex;flex-direction:column}" in css
    assert "text-transform" not in css and "letter-spacing" not in css, "calm labels: no uppercase tracking"


def test_map_host_calls_the_endpoint_once_per_block():
    assert "const PREFIX='iui-map:', RETRY_MS=3000" in MAP_HOST
    assert "inflight.has(key)" in MAP_HOST
    assert "'api/map/resolve'" in MAP_HOST and "method:'POST'" in MAP_HOST


def test_copy_has_no_long_dashes():
    for text in (KITS, CORE, MAP_HOST, (REPO / "static" / "interactive-ui" / "kits.css").read_text(encoding="utf-8")):
        assert not re.search(LONG_DASHES, text)
