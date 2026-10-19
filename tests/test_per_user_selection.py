"""One person's folder / thinking-level choice must not change a colleague's.

Reported 18 Oct 2026: picking a workspace (now "📁 Project") on the home
screen made it the selection for everyone on the same bot.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

import api.workspace as ws
from api import ownership, user_prefs


@pytest.fixture
def as_user(monkeypatch, tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setattr(ws, "_profile_state_dir", lambda: state)
    monkeypatch.setattr(ws, "_remote_terminal_cwd", lambda: None)
    default = tmp_path / "admin-default"
    default.mkdir()
    monkeypatch.setattr(ws, "_profile_default_workspace", lambda: str(default))
    monkeypatch.setattr(ws, "_GLOBAL_LW_FILE", state / "global_last_workspace.txt")
    current = {"email": None}

    def use(email):
        current["email"] = email
        ownership._CURRENT_REQUEST.handler = SimpleNamespace() if email is not False else None
    monkeypatch.setattr(ws, "_current_request_email", lambda: current["email"] or None)
    yield use, state, default, tmp_path
    ownership._CURRENT_REQUEST.handler = None


def test_folder_choice_is_per_person(as_user):
    use, state, default, tmp = as_user
    a_dir = tmp / "a-folder"; a_dir.mkdir()
    b_dir = tmp / "b-folder"; b_dir.mkdir()
    use("anna@x.nl"); ws.set_last_workspace(str(a_dir))
    use("bram@x.nl")
    assert ws.get_last_workspace() == str(default)  # Bram never picked: admin default, not Anna's
    assert ws.get_profile_default_workspace() == str(default)
    ws.set_last_workspace(str(b_dir))
    use("anna@x.nl")
    assert ws.get_last_workspace() == str(a_dir)
    use("bram@x.nl")
    assert ws.get_last_workspace() == str(b_dir)


def test_profile_wide_file_never_leaks_to_signed_in_people(as_user):
    use, state, default, tmp = as_user
    shared = tmp / "someone-elses"; shared.mkdir()
    (state / "last_workspace.txt").write_text(str(shared), encoding="utf-8")
    use("carla@x.nl")
    assert ws.get_last_workspace() == str(default)
    use(None)  # identity-less (auth off / password without email): legacy single-user behaviour
    assert ws.get_last_workspace() == str(shared)


def test_background_work_moves_nobodys_folder(as_user):
    use, state, default, tmp = as_user
    job = tmp / "cron-folder"; job.mkdir()
    use(False)  # no request on this thread: scheduled job / async delegation
    ws.set_last_workspace(str(job))
    assert not (state / "last_workspace.txt").exists()
    assert not (state / "last_workspace_by_user").exists()


def test_pytest_temp_workspace_is_never_adopted(as_user, monkeypatch):
    use, state, default, tmp = as_user
    import api.config as cfg
    monkeypatch.setattr(cfg, "STATE_DIR", Path("/srv/live/webui"))
    use("anna@x.nl")
    ws.set_last_workspace("/tmp/hermes-webui-tests/webui-test-x/test-workspace")
    assert not (state / "last_workspace_by_user").exists()
    assert cfg.is_foreign_test_workspace("/tmp/hermes-webui-tests/webui-test-x/test-workspace")
    monkeypatch.setattr(cfg, "STATE_DIR", Path("/tmp/hermes-webui-tests/webui-test-x"))
    assert not cfg.is_foreign_test_workspace("/tmp/hermes-webui-tests/webui-test-x/test-workspace")


def test_thinking_level_is_per_person_per_bot(monkeypatch, tmp_path):
    import api.config as cfg
    monkeypatch.setattr(cfg, "STATE_DIR", tmp_path)
    user_prefs.set_reasoning_effort("anna@x.nl", "sales", "high")
    assert user_prefs.get_reasoning_effort("anna@x.nl", "sales") == "high"
    assert user_prefs.get_reasoning_effort("bram@x.nl", "sales") is None
    assert user_prefs.get_reasoning_effort("anna@x.nl", "default") is None
    user_prefs.set_reasoning_effort("anna@x.nl", "sales", "")
    assert user_prefs.get_reasoning_effort("anna@x.nl", "sales") is None
    with pytest.raises(ValueError):
        user_prefs.set_reasoning_effort("", "sales", "high")


def test_routes_keep_bot_default_for_admin_scope_only():
    src = (Path(__file__).resolve().parents[1] / "api" / "routes.py").read_text(encoding="utf-8")
    block = src[src.index('if parsed.path == "/api/reasoning":\n        # CLI-parity /reasoning handler'):][:3000]
    assert 'str(body.get("scope") or "") == "profile" and request_is_admin(handler)' in block
    assert "user_prefs.set_reasoning_effort(_who" in block
    stream = (Path(__file__).resolve().parents[1] / "api" / "streaming.py").read_text(encoding="utf-8")
    assert "_user_prefs.get_reasoning_effort(" in stream
