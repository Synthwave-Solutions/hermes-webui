"""21-09-2026: a workspace registered at /home swallowed every session's
attachment inbox, so the live membership check refused uploads for everyone
but that entry's owner (Yaser: "mn superagent workspace ligt eruit"). A root
that contains the home directory or the WebUI state directory is refused at
registration; ordinary project folders, including ones under the home
directory, still register."""
from pathlib import Path

import pytest

from api.workspace import overbroad_workspace_error


@pytest.fixture
def layout(tmp_path):
    home = tmp_path / "home" / "synthwavehq"
    state = home / ".hermes" / "webui"
    state.mkdir(parents=True)
    (home / "clients" / "_synthwave").mkdir(parents=True)
    (home / "work").mkdir()
    return home, state


@pytest.mark.parametrize("relative", ["", "..", "../..", ".hermes", ".hermes/webui"])
def test_roots_that_contain_home_or_the_state_dir_are_refused(layout, relative):
    home, state = layout
    root = (home / relative).resolve() if relative else home
    error = overbroad_workspace_error(root, home=home, state_dir=state)
    assert error and "too broad" in error


@pytest.mark.parametrize("relative", ["clients/_synthwave", "work", "clients"])
def test_project_folders_under_home_still_register(layout, relative):
    home, state = layout
    assert overbroad_workspace_error(home / relative, home=home, state_dir=state) is None


def test_the_add_route_applies_the_check_after_validation():
    src = (Path(__file__).resolve().parent.parent / "api" / "routes.py").read_text(encoding="utf-8")
    body = src.split("def _handle_workspace_add(", 1)[1].split("\ndef ", 1)[0]
    assert "overbroad_workspace_error(p)" in body
    assert body.index("validate_workspace_to_add(path_str)") < body.index("overbroad_workspace_error(p)")
