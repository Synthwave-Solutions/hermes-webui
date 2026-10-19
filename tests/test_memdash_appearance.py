"""The Memory explorer follows the SynthPulse appearance settings.

The panel sends the WebUI's own tokens (theme, skin colours, font, font size,
radii) into the sandboxed frame; the frame shim validates them and sets them
as --sp-* custom properties, and memdash-overrides.css maps those onto the
dashboard. A theme, skin or font size change while the explorer is open is
sent again.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATIC = REPO / "static"
SERVED = STATIC / "vendor" / "mnemosyne-dashboard" / "0.14.0-a918e5e"
PANEL_JS = (STATIC / "memory_dashboard.js").read_text(encoding="utf-8")
SHIM_JS = (SERVED / "memdash-shim.js").read_text(encoding="utf-8")
OVERRIDES = (SERVED / "memdash-overrides.css").read_text(encoding="utf-8")
DASHES = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")

TOKENS = ("bg", "surface", "text", "muted", "border", "accent", "accent-text", "accent-bg",
          "success", "warning", "error", "radius-md", "radius-lg", "font-ui", "font-size")


def _appearance_css() -> str:
    return OVERRIDES.split("SynthPulse appearance", 1)[1]


def test_panel_sends_the_appearance_tokens_and_watches_every_appearance_attribute():
    for name in TOKENS:
        assert f"'{name}'" in PANEL_JS, name
    assert "'--font-ui'" in PANEL_JS
    assert "tokens: msg.tokens, fontSize: msg.fontSize" in PANEL_JS
    for attr in ("class", "data-theme", "data-skin", "data-font-size"):
        assert f"'{attr}'" in PANEL_JS, attr


def test_shim_accepts_only_safe_token_values_and_marks_the_root():
    for name in TOKENS:
        assert f"'{name}'" in SHIM_JS, name
    assert "root.style.setProperty('--sp-' + name, value)" in SHIM_JS
    assert "data-sp-appearance" in SHIM_JS and "data-sp-font-size" in SHIM_JS
    # No CSS text is ever built from a message: only setProperty with a value
    # that passed a strict pattern.
    assert "cssText" not in SHIM_JS and "insertRule" not in SHIM_JS and "innerHTML" not in SHIM_JS
    assert "FONT_RE = /^[A-Za-z0-9 ,\"'._-]{1,240}$/" in SHIM_JS
    assert "LENGTH_RE = /^\\d{1,3}(\\.\\d{1,3})?px$/" in SHIM_JS


def test_overrides_map_the_tokens_without_fixed_colours():
    css = _appearance_css()
    assert css.count("{") == css.count("}")
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", css)
    for var in ("--bg", "--panel", "--text", "--muted", "--line", "--accent", "--accent2"):
        assert re.search(r"\n  " + re.escape(var) + r": var\(--sp-", css), var
    for token in ("--sp-font-ui", "--sp-font-size", "--sp-radius-lg", "--sp-radius-md", "--sp-radius-sm"):
        assert token in css, token
    assert ':root[data-sp-appearance][data-theme="light"]' in css
    assert "@font-face" not in css and "@import" not in css and "url(" not in css


def test_store_labels_are_translated_and_copy_has_no_dashes():
    for key in ("memdash_store_personal", "memdash_store_conversation", "memdash_store_legacy"):
        assert key in PANEL_JS
        for locale in ("en", "nl"):
            assert key + ":" in (STATIC / "i18n" / f"{locale}.js").read_text(encoding="utf-8"), (key, locale)
    nl = (STATIC / "i18n" / "nl.js").read_text(encoding="utf-8")
    assert "memdash_store_personal: 'Persoonlijke herinneringen'" in nl
    for text in (PANEL_JS, SHIM_JS, OVERRIDES):
        assert not DASHES.search(text)
