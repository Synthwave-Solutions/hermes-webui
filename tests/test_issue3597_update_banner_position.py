"""Verify #updateBanner lives outside #mainChat so it is visible from any panel.

SynthPulse removed the update banner on purpose (ae53fb3a, Aug 2026): no popup
appears for agent, frontend or backend updates, and test_update_banner_fixes.py
guards the removal. The upstream placement rule (inside <main>, before
#mainChat) only applies if the banner ever returns, so each check below first
guards that it is still gone and otherwise enforces upstream's placement.
"""
import pathlib

INDEX = pathlib.Path(__file__).resolve().parent.parent / "static" / "index.html"


def test_update_banner_outside_main_chat():
    src = INDEX.read_text(encoding="utf-8")
    banner_pos = src.find('id="updateBanner"')
    main_chat_pos = src.find('id="mainChat"')
    assert main_chat_pos != -1, "#mainChat not found in index.html"
    if banner_pos == -1:
        # Removed on purpose (ae53fb3a); nothing of it may linger either.
        assert 'id="updateMsg"' not in src and 'id="btnApplyUpdate"' not in src
        return
    assert banner_pos < main_chat_pos, (
        "#updateBanner must appear before #mainChat in the DOM "
        "so it is not hidden when non-Chat panels are active"
    )


def test_update_banner_inside_main_element():
    src = INDEX.read_text(encoding="utf-8")
    main_pos = src.find('<main class="main">')
    main_end = src.find('</main>')
    banner_pos = src.find('id="updateBanner"')
    assert main_pos != -1, "<main class='main'> not found"
    assert main_end != -1, "</main> not found"
    if banner_pos == -1:
        # Removed on purpose (ae53fb3a); see test_update_banner_fixes.py. The
        # stale-client banner reuses the .update-banner style and is unrelated.
        assert 'id="btnForceUpdate"' not in src and 'id="updateError"' not in src
        return
    assert main_pos < banner_pos < main_end, (
        "#updateBanner must be inside <main class='main'>, "
        "not before it or after the closing </main>"
    )
