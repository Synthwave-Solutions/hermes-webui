from pathlib import Path
from html.parser import HTMLParser
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
PANELS_JS  = (ROOT / "static" / "panels.js").read_text(encoding="utf-8")
I18N_JS    = (ROOT / "static" / "i18n.js").read_text(encoding="utf-8")
STYLE_CSS  = (ROOT / "static" / "style.css").read_text(encoding="utf-8")

LOCALE_BUNDLES = sorted((ROOT / "static" / "i18n").glob("*.js"))


class HelpLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "help-card-link" in attrs.get("class", "").split():
            self.links.append(attrs)


def _help_links():
    parser = HelpLinks()
    parser.feed(INDEX_HTML)
    return parser.links


def test_help_nav_button_present():
    assert 'data-settings-section="help"' in INDEX_HTML
    assert "switchSettingsSection('help',{fromSidebarItem:true})" in INDEX_HTML
    assert 'data-i18n="settings_tab_help"' in INDEX_HTML


def test_help_pane_present():
    assert 'id="settingsPaneHelp"' in INDEX_HTML
    assert {link['href'] for link in _help_links()} == {
        'https://synthwave.solutions/', 'https://github.com/Synthwave-Solutions',
    }


def test_help_pane_links_are_outbound():
    links = _help_links()
    assert links
    for link in links:
        assert link.get('target') == '_blank'
        assert {'noopener', 'noreferrer'} <= set(link.get('rel', '').split())


def test_panels_js_allowlist_includes_help():
    assert "name==='help'" in PANELS_JS


def test_panels_js_map_includes_help():
    assert "help:'Help'" in PANELS_JS


def test_panels_js_foreach_includes_help():
    assert "'help'" in PANELS_JS
    assert "settingsPaneHelp" not in PANELS_JS or 'settingsPane'+'{map[key]}' not in PANELS_JS
    # Simpler: confirm the forEach array string contains help
    assert ",'help'," in PANELS_JS or ",'help']" in PANELS_JS


def test_i18n_help_keys_present_in_all_locales():
    # Locale catalogs moved out of the loader into on-demand bundles. Check
    # each actual catalog so adding or removing a supported locale stays safe.
    assert LOCALE_BUNDLES
    for bundle in LOCALE_BUNDLES:
        content = bundle.read_text(encoding="utf-8")
        assert "__registerHermesLocale(" in content
        for key in ("settings_tab_help", "settings_help_docs_label",
                    "settings_help_issue_label", "settings_help_docs_link",
                    "settings_help_issue_link"):
            assert re.search(rf"\b{key}:\s*'[^']", content), (bundle.name, key)


def test_help_card_link_hover_is_contrast_safe():
    """The hover fill is var(--accent); the text color must NOT be var(--accent-text).

    In most themes --accent-text equals (or nearly equals) --accent — it is an
    accent-on-background link color, not a contrasting color for text sitting ON
    an accent fill. Using it on the accent-filled hover state produced same-color
    text on the fill (invisible) across nearly every theme (slate/gold/ares/mono/
    sisyphus/catppuccin dark all had accent == accent-text). The fix uses
    var(--bg) — the page background — which --accent is designed to contrast
    against, so the text stays readable in every theme.
    """
    import re
    m = re.search(r"\.help-card-link:hover\s*\{([^}]*)\}", STYLE_CSS)
    assert m, "expected a .help-card-link:hover rule in style.css"
    rule = m.group(1)
    assert "background:var(--accent)" in rule.replace(" ", "")
    # The bug: accent-text on accent fill. Must not reappear.
    assert "--accent-text" not in rule, (
        "hover text uses var(--accent-text) on an accent fill — invisible in most "
        "themes; use var(--bg) for theme-agnostic contrast"
    )
    assert "color:var(--bg)" in rule.replace(" ", "")
