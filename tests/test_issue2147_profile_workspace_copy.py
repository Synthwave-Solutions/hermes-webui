"""Regression tests for issue #2147 profile/workspace mental-model copy."""
from pathlib import Path
from tests._i18n_source import monolithic_i18n_source

REPO = Path(__file__).resolve().parent.parent


def read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_profiles_panel_surfaces_profiles_vs_workspaces_help_card():
    src = read("static/panels.js")
    assert "t('profile_concept_title')" in src
    assert "t('profile_concept_subtitle')" in src
    assert "_renderProfileConceptHelp" in src
    assert "explainer.onclick = () => _renderProfileConceptHelp" in src


def test_profile_concept_help_distinguishes_how_from_where():
    i18n = monolithic_i18n_source()
    # SynthPulse rewrote the explainer as "Bots and workspaces"; the split
    # it teaches is unchanged: a bot is who works, a workspace is where.
    assert "profile_concept_title: 'Bots and workspaces'" in i18n
    assert "Who the assistant is: its tools, access, memory and skills." in i18n
    assert "Where it works: the folder its commands and file edits run in." in i18n
    assert "A bot can work in any workspace. Switching one never switches the other." in i18n
    src = read("static/panels.js")
    assert "t('profile_concept_desc_profiles')" in src
    assert "t('profile_concept_desc_workspaces')" in src
    assert "t('profile_concept_desc_together')" in src


def test_empty_profiles_state_keeps_help_card_visible():
    src = read("static/panels.js")
    assert "panel.innerHTML = ''" in src
    assert "panel.appendChild(explainer)" in src
    assert "emptyMsg.textContent = t('profiles_no_profiles')" in src
    assert "panel.appendChild(emptyMsg)" in src
