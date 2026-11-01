"""Regression guards for localized profile-concept help copy (#2147)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
I18N_JS = (ROOT / "static" / "i18n.js").read_text(encoding="utf-8")
PANELS_JS = (ROOT / "static" / "panels.js").read_text(encoding="utf-8")

PROFILE_CONCEPT_KEYS = [
    "profile_concept_title",
    "profile_concept_subtitle",
    "profile_concept_desc_profiles",
    "profile_concept_desc_workspaces",
    "profile_concept_desc_together",
    "profile_concept_example",
    "profile_concept_label_together",
    "profile_concept_label_example",
]


def _locale_blocks():
    """Read the demand-loaded bundles used by the current locale loader."""
    return {
        path.stem: path.read_text(encoding="utf-8")
        for path in (ROOT / "static" / "i18n").glob("*.js")
    }


def _render_profiles_panel_body():
    start = PANELS_JS.index("function _renderProfilesList(")
    end = PANELS_JS.index("\nfunction ", start + 1)
    return PANELS_JS[start:end]


def _render_profile_concept_help_body():
    start = PANELS_JS.index("function _renderProfileConceptHelp(")
    end = PANELS_JS.index("\nfunction ", start + 1)
    return PANELS_JS[start:end]


def test_i18n_keys_keep_english_fallback_and_dutch_sidebar_copy():
    """Translations may override copy; English remains the fallback."""
    locale_blocks = _locale_blocks()
    en_block = locale_blocks["en"]
    for key in PROFILE_CONCEPT_KEYS:
        assert re.search(rf"\b{re.escape(key)}:\s*'", en_block), (
            f"missing key {key!r} in en locale block"
        )
    for key in ("profile_concept_title", "profile_concept_subtitle"):
        assert f'"{key}":' in locale_blocks['nl']
    assert re.search(r"_locale\[key\]\s*\?\?\s*LOCALES\.en\[key\]", I18N_JS)


def test_help_card_uses_i18n_keys():
    """The profiles panel explainer card must use t() instead of hardcoded English."""
    panel_body = _render_profiles_panel_body()
    assert "t('profile_concept_title')" in panel_body
    assert "t('profile_concept_subtitle')" in panel_body
    assert "Profiles vs workspaces" not in panel_body
    assert "Use profiles for how the agent works; use workspaces for what files it works on." not in panel_body


def test_concept_detail_uses_i18n_keys():
    """The concept detail view must use t() for the title and each description row."""
    detail_body = _render_profile_concept_help_body()
    assert "t('profile_concept_title')" in detail_body
    assert "t('profile_concept_desc_profiles')" in detail_body
    assert "t('profile_concept_desc_workspaces')" in detail_body
    assert "t('profile_concept_desc_together')" in detail_body
    assert "Profiles vs workspaces" not in detail_body


def test_example_row_present():
    """The concept detail view must render an example row."""
    detail_body = _render_profile_concept_help_body()
    assert "t('profile_concept_example')" in detail_body
