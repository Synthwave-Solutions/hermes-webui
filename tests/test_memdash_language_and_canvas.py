"""The Memory explorer follows the WebUI language and draws its canvases in the WebUI tokens.

The panel sends the WebUI language with the appearance message (and in the
frame URL); the frame shim translates the dashboard's own strings from a
Dutch table keyed on the exact English source, English for anything else.
The 3D visualiser's palette functions are wrapped by the shim so nodes,
links and the background follow the --sp-* tokens; the SVG knowledge graph
follows them through memdash-overrides.css.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATIC = REPO / "static"
SERVED = STATIC / "vendor" / "mnemosyne-dashboard" / "0.14.0-a918e5e"
PANEL_JS = (STATIC / "memory_dashboard.js").read_text(encoding="utf-8")
SHIM_JS = (SERVED / "memdash-shim.js").read_text(encoding="utf-8")
OVERRIDES = (SERVED / "memdash-overrides.css").read_text(encoding="utf-8")
INDEX = (SERVED / "index.html").read_text(encoding="utf-8")
DASHES = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")


def _nl_table() -> dict[str, str]:
    block = SHIM_JS.split("// <nl-table>", 1)[1].split("// </nl-table>", 1)[0]
    body = block.split("var NL = ", 1)[1].rsplit(";", 1)[0]
    return json.loads(body)


def _nav_labels() -> list[str]:
    nav = INDEX.split("<nav>", 1)[1].split("</nav>", 1)[0]
    labels = []
    for attrs, label in re.findall(r"<button ([^>]*)><span>[^<]*</span>([^<]+)</button>", nav):
        if "nav-hidden" in attrs:
            continue  # the hidden labyrinth and legacy views
        labels.append(label.strip())
    return labels


def test_dutch_table_covers_every_nav_label():
    table = _nl_table()
    labels = _nav_labels()
    assert {"Overview", "Today", "Visualiser", "Review", "Memories", "Context Bank", "Lifecycle",
            "Knowledge Graph", "Structured memory", "History"} <= set(labels)
    for label in labels:
        assert label in table, label
        assert table[label] and table[label] != label, label


def test_dutch_table_is_clean_and_covers_the_reported_screens():
    table = _nl_table()
    assert len(table) > 300
    for source, dutch in table.items():
        assert isinstance(dutch, str) and dutch.strip(), source
        assert not DASHES.search(source + dutch), source
    for source in ("Working", "Episodic", "Needs review", "Degraded", "Triples", "Consolidations",
                   "Search memory…", "Constellation", "Neural Map", "Relationship graph", "Nothing selected",
                   "No memories added today.", "Pick a star, memory, or link to inspect the underlying read-only source."):
        assert source in table, source
    # The two-letter menu badges and the brand have their own Dutch.
    assert "['nav button span', 'KG', 'KN']" in SHIM_JS
    assert "['.brand-name', 'Memory', 'Geheugen']" in SHIM_JS


def test_panel_sends_the_webui_language():
    assert "function frameLang()" in PANEL_JS
    assert "/^nl\\b/i.test(code) ? 'nl' : 'en'" in PANEL_JS
    assert "lang: frameLang()" in PANEL_JS and "lang: msg.lang" in PANEL_JS
    assert "'&lang=' + frameLang()" in PANEL_JS
    assert "'data-font-size', 'style', 'lang']" in PANEL_JS


def test_shim_translates_with_an_observer_and_falls_back_to_english():
    assert "params.get('lang') === 'nl' ? 'nl' : 'en'" in SHIM_JS
    assert "if (msg.lang === 'nl' || msg.lang === 'en') setLang(msg.lang);" in SHIM_JS
    assert "new MutationObserver(" in SHIM_JS
    assert "attributeFilter: I18N_ATTRS" in SHIM_JS
    assert "var I18N_ATTRS = ['placeholder', 'title', 'aria-label'];" in SHIM_JS
    # Memory text and node labels are the user's own data.
    assert "pre:not(.html-detail), code, textarea, .content, .three-labels" in SHIM_JS
    # Unknown strings stay as they are; switching back restores the source.
    assert "return null;" in SHIM_JS and "node.nodeValue = known.src;" in SHIM_JS
    assert "innerHTML" not in SHIM_JS and "cssText" not in SHIM_JS and "eval(" not in SHIM_JS


def test_shim_draws_the_3d_visualiser_in_the_tokens_and_redraws_on_a_theme_change():
    for name in ("constellationColors", "neuralColors", "colorForTheme"):
        assert f"window.{name} = function ()" in SHIM_JS, name
    assert "getComputedStyle(document.documentElement).getPropertyValue('--sp-' + name)" in SHIM_JS
    assert "window.renderThreeVisualiser(threeVis.data)" in SHIM_JS
    assert "repaintCanvases();" in SHIM_JS
    assert "document.addEventListener('DOMContentLoaded', wrapPalettes);" in SHIM_JS


def test_overrides_colour_the_graph_and_the_3d_view_with_tokens_only():
    css = OVERRIDES.split("The 3D visualiser and the knowledge graph", 1)[1]
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", css.replace("#edgeGradient", ""))
    for selector in (".three-viewport", ".three-label", ".legend-dot", ".legend-line", "#edgeGradient stop",
                     ".edge", ".node", ".nodeText", ".edgeLabel"):
        assert f":root[data-sp-appearance] {selector}" in css, selector
    assert "stop-color: var(--sp-accent)" in css


def test_app_is_a_cors_script_so_three_js_loads():
    assert re.search(r'<script src="app\.js\?v=[0-9a-f]{12}" crossorigin="anonymous"></script>', INDEX)
    vendor = (REPO / "scripts" / "memdash_vendor.py").read_text(encoding="utf-8")
    assert '<script src="app.js?v={app.js}" crossorigin="anonymous"></script>' in vendor
