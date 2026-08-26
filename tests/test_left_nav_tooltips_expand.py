"""
left-nav-tooltips ticket (Aug 2026): the icon-only left navigation must be
discoverable without trial and error.

Three fixes pinned here:

  1. Accessible names: every icon-only nav button (desktop rail AND the mobile
     sidebar-nav) carries aria-label plus data-i18n-aria-label, so keyboard and
     screen-reader users get the same label sighted users see in the tooltip.
  2. Mobile tooltips actually render: the legacy data-label hover rule fought
     the has-tooltip--bottom system (opposite vertical anchoring on the same
     ::after, over-constraining the box) and the base .nav-tab overflow:hidden
     clipped the pseudo-element outright. The legacy rule is gone and
     .sidebar-nav .nav-tab is overflow:visible.
  3. Pin-to-expand: the desktop rail can be expanded into a labels view
     (html[data-rail-expanded="1"]), toggled by #railExpandToggle, persisted in
     localStorage, restored pre-paint, and suppressed in split-view panes.

Run:
    ./scripts/test.sh tests/test_left_nav_tooltips_expand.py -v
"""
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).parent.parent
INDEX_HTML = (REPO_ROOT / "static" / "index.html").read_text(encoding="utf-8")
STYLE_CSS = (REPO_ROOT / "static" / "style.css").read_text(encoding="utf-8")
BOOT_JS = (REPO_ROOT / "static" / "boot.js").read_text(encoding="utf-8")
SPLIT_JS = (REPO_ROOT / "static" / "split.js").read_text(encoding="utf-8")
EN_JS = (REPO_ROOT / "static" / "i18n" / "en.js").read_text(encoding="utf-8")

RAIL_EXPANDED_KEY = "hermes-webui-rail-expanded"


def _buttons_in(section_html):
    return re.findall(r"<button\b[^>]*>", section_html)


def _rail_section():
    m = re.search(r'<nav class="rail"[^>]*>(.*?)</nav>', INDEX_HTML, re.DOTALL)
    assert m, "rail nav not found in index.html"
    return m.group(1)


def _sidebar_nav_section():
    m = re.search(r'<div\s+class="sidebar-nav"[^>]*>(.*?)</div>', INDEX_HTML, re.DOTALL)
    assert m, "sidebar-nav not found in index.html"
    return m.group(1)


# ── 1. Accessible names on every icon-only nav button ────────────────────────

def test_every_rail_button_has_accessible_name():
    for btn in _buttons_in(_rail_section()):
        assert 'aria-label="' in btn, f"rail button misses aria-label: {btn[:120]}"


def test_every_sidebar_nav_tab_has_accessible_name():
    """The mobile sidebar-nav tabs are icon-only too (SVGs are aria-hidden),
    so without aria-label their accessible name was empty."""
    tabs = _buttons_in(_sidebar_nav_section())
    assert tabs, "no buttons found inside sidebar-nav"
    for btn in tabs:
        assert 'aria-label="' in btn, f"sidebar-nav tab misses aria-label: {btn[:120]}"
        assert 'data-i18n-aria-label="' in btn, (
            f"sidebar-nav tab misses data-i18n-aria-label (label would stay "
            f"English on locale switch): {btn[:120]}"
        )


def test_nav_labels_match_their_tooltips():
    """The accessible name and the visual tooltip must not drift apart."""
    for section in (_rail_section(), _sidebar_nav_section()):
        for btn in _buttons_in(section):
            tooltip = re.search(r'data-tooltip="([^"]*)"', btn)
            aria = re.search(r'(?<![a-z-])aria-label="([^"]*)"', btn)
            if tooltip and aria:
                # Aria may be more descriptive but never empty or unrelated;
                # they start from the same word (e.g. "Spaces" / "Spaces").
                assert aria.group(1), f"empty aria-label: {btn[:120]}"


# ── 2. Mobile sidebar-nav tooltips actually render ───────────────────────────

def test_legacy_data_label_hover_tooltip_removed():
    """The legacy rule conflicted with has-tooltip--bottom (both anchored the
    same ::after in opposite directions, over-constraining the box)."""
    assert ".sidebar-nav .nav-tab:hover::after{content:attr(data-label)" not in STYLE_CSS, (
        "legacy data-label hover tooltip is back; it fights the has-tooltip "
        "system on the mobile sidebar-nav"
    )


def test_sidebar_nav_tabs_do_not_clip_tooltips():
    """.nav-tab base sets overflow:hidden which clips the tooltip pseudo
    element; the sidebar-nav scope must restore overflow:visible (the rail
    already does via .rail .nav-tab)."""
    assert re.search(r"\.sidebar-nav \.nav-tab\{[^}]*overflow:visible", STYLE_CSS), (
        "missing .sidebar-nav .nav-tab{overflow:visible}: mobile nav tooltips "
        "get clipped by the base .nav-tab overflow:hidden"
    )
    assert re.search(r"\.rail \.nav-tab\{[^}]*overflow:visible", STYLE_CSS), (
        "rail nav tabs must keep overflow:visible so rail tooltips render"
    )


# ── 3. Rail pin-to-expand ────────────────────────────────────────────────────

def test_rail_expand_toggle_button_present_and_tooltipped():
    rail = _rail_section()
    m = re.search(r'<button[^>]*id="railExpandToggle"[^>]*>', rail)
    assert m, "railExpandToggle button missing from the rail"
    btn = m.group(0)
    assert "has-tooltip" in btn
    assert 'data-tooltip="' in btn
    assert 'aria-label="' in btn
    assert 'aria-pressed="' in btn
    assert 'onclick="toggleRailExpanded()"' in btn


def test_rail_expanded_css_shows_labels_from_data_tooltip():
    """Expanded mode restyles the tooltip ::after into a static inline label,
    reusing the i18n-synced data-tooltip text so label and tooltip can never
    disagree."""
    assert 'html[data-rail-expanded="1"] .rail{' in STYLE_CSS
    rule = re.search(
        r'html\[data-rail-expanded="1"\] \.rail \.rail-btn::after\{([^}]*)\}',
        STYLE_CSS,
    )
    assert rule, "expanded-rail label rule missing"
    body = rule.group(1)
    assert "content:attr(data-tooltip)" in body
    assert "position:static" in body
    assert "opacity:1" in body


def test_rail_expanded_state_persisted_and_restored_prepaint():
    assert RAIL_EXPANDED_KEY in BOOT_JS, "boot.js misses the persistence key"
    assert "function toggleRailExpanded" in BOOT_JS
    assert "_restoreRailExpandedState" in BOOT_JS
    # Pre-paint restore: the inline script must run before the stylesheet link
    # so the expanded rail renders without a flash of the collapsed state.
    inline_idx = INDEX_HTML.find(RAIL_EXPANDED_KEY)
    assert inline_idx != -1, "index.html misses the pre-paint restore script"
    assert inline_idx < INDEX_HTML.find('href="static/style.css'), (
        "pre-paint rail restore script must run before the stylesheet loads"
    )


def test_rail_expanded_state_suppressed_in_split_panes():
    """Split-view panes embed the full app; an expanded rail in every pane
    would eat the width the panes exist to share."""
    assert RAIL_EXPANDED_KEY in SPLIT_JS, (
        "split.js pane-mode localStorage block must include the rail key"
    )
    assert "pane" in INDEX_HTML[
        INDEX_HTML.find(RAIL_EXPANDED_KEY) - 200:INDEX_HTML.find(RAIL_EXPANDED_KEY)
    ], "pre-paint restore script must skip pane mode"
    assert "__HERMES_PANE_MODE" in BOOT_JS


def test_rail_expand_toggle_i18n_keys_exist():
    assert "nav_expand_labels:" in EN_JS
    assert "nav_collapse_labels:" in EN_JS


def test_rail_expand_toggle_not_mirrored_into_mobile_nav():
    """ui.js mirrors rail .nav-tab buttons with ids into the mobile sidebar;
    the expand toggle is desktop-only so it must not carry the nav-tab class."""
    m = re.search(r'<button[^>]*id="railExpandToggle"[^>]*>', _rail_section())
    assert m
    cls = re.search(r'class="([^"]*)"', m.group(0))
    assert cls and "nav-tab" not in cls.group(1).split(), (
        "railExpandToggle must not be a .nav-tab or the mobile mirror sync "
        "clones it into the sidebar-nav"
    )
