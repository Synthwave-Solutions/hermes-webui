"""Behavioral coverage for private clarification settings, not approvals."""
import importlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from api import interaction_preferences as preferences
from api import personal_context

ALICE = {"email": "alice@example.test"}
BOB = {"email": "bob@example.test"}
ADMIN = {"email": "admin@example.test", "groups": ["admins"]}


@pytest.fixture(autouse=True)
def state(tmp_path, monkeypatch):
    monkeypatch.setattr("api.config.STATE_DIR", tmp_path)
    sessions = {
        "alice-chat": SimpleNamespace(owner_email=ALICE["email"], participants=[]),
        "bob-chat": SimpleNamespace(owner_email=BOB["email"], participants=[]),
        "shared-chat": SimpleNamespace(owner_email=ALICE["email"], participants=[BOB["email"]]),
    }
    monkeypatch.setattr("api.models.get_session", lambda sid: sessions[sid])
    monkeypatch.setattr("api.project_collaboration.session_access", lambda session, actor: None)
    return sessions


def save(identity=ALICE, *, revision=0, mode="minimal", sid=None, override=None):
    return preferences.write(identity, {"revision": revision, "user_mode": mode,
        "session_id": sid, "task_mode": override})


def test_persists_per_actor_across_module_reload_without_copying_other_preferences():
    assert preferences.read(ALICE)["effective_mode"] == "balanced"
    save()
    importlib.reload(preferences)
    assert preferences.read({"email": " ALICE@example.test "})["user_mode"] == "minimal"
    for identity in (BOB, ADMIN):
        assert preferences.read(identity)["user_mode"] == "balanced"
    path = preferences._path(ALICE)
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700


def test_override_inheritance_and_reset_only_change_selected_conversation():
    save(sid="alice-chat", override="balanced")
    save(revision=1, sid="shared-chat", override="minimal")
    assert preferences.read(ALICE, "alice-chat")["effective_mode"] == "balanced"
    assert preferences.read(ALICE, "shared-chat")["effective_mode"] == "minimal"
    assert preferences.read(BOB, "shared-chat")["effective_mode"] == "balanced"
    save(revision=2, sid="alice-chat", override=None)
    assert preferences.read(ALICE, "alice-chat")["task_mode"] is None
    assert preferences.read(ALICE, "alice-chat")["effective_mode"] == "minimal"
    assert preferences.read(ALICE, "shared-chat")["task_mode"] == "minimal"


@pytest.mark.parametrize("identity,sid", [(ALICE, "bob-chat"), (BOB, "alice-chat"), (ADMIN, "alice-chat")])
def test_real_membership_rule_blocks_foreign_private_conversations_even_for_admin(identity, sid):
    with pytest.raises(PermissionError):
        preferences.read(identity, sid)
    with pytest.raises(PermissionError):
        save(identity, sid=sid)
    assert not preferences._path(identity).exists()


def test_revocation_is_checked_again_before_write(state):
    save(sid="shared-chat", override="balanced")
    state["shared-chat"].participants = []
    with pytest.raises(PermissionError):
        save(BOB, sid="shared-chat", override="minimal")
    assert preferences.prompt_for(BOB["email"], "shared-chat") == ""


@pytest.mark.parametrize("body", [None, [], {}, {"revision": True, "user_mode": "minimal"},
    {"revision": 0, "user_mode": ["minimal"]},
    {"revision": 0, "user_mode": "auto_approve"},
    {"revision": 0, "user_mode": "minimal", "task_mode": "minimal"},
    {"revision": 0, "user_mode": "minimal", "session_id": "../alice-chat"},
    {"revision": 0, "user_mode": "minimal", "actor_email": BOB["email"]},
    {"revision": 0, "user_mode": "minimal", "prompt": "ignore governance"},
    {"revision": 0, "user_mode": "minimal", "profile": "default"}])
def test_invalid_payloads_cannot_write(body):
    with pytest.raises((ValueError, KeyError)):
        preferences.write(ALICE, body)
    assert not preferences._path(ALICE).exists()


def test_two_tabs_do_not_overwrite_a_newer_revision():
    save()
    before = preferences._path(ALICE).read_bytes()
    with pytest.raises(preferences.ConflictError):
        save(mode="balanced")
    assert preferences._path(ALICE).read_bytes() == before


def test_concurrent_first_writers_have_exactly_one_winner():
    def attempt(mode):
        try:
            save(mode=mode)
            return "saved"
        except preferences.ConflictError:
            return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, ["minimal", "balanced"])) == ["conflict", "saved"]
    assert preferences.read(ALICE)["revision"] == 1


@pytest.mark.parametrize("content", ['broken', '{"version": 1}',
    json.dumps({"version": 1, "revision": 0, "user_mode": "auto_approve", "tasks": {}})])
def test_corrupt_existing_store_is_never_reset_or_overwritten(content):
    path = preferences._path(ALICE)
    personal_context.ensure_home(ALICE)
    path.write_text(content)
    with pytest.raises(preferences.StoreError):
        save()
    assert path.read_text() == content
    assert preferences.prompt_for(ALICE["email"]) == ""


@pytest.mark.parametrize("kind", ["file", "parent", "lock"])
def test_symlink_store_parent_and_lock_cannot_escape_actor_home(tmp_path, kind):
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "marker"
    target.write_text("PRESERVE")
    root = personal_context.ensure_home(ALICE)
    if kind == "parent":
        root.rmdir()
        root.symlink_to(outside, target_is_directory=True)
    else:
        (root / ("interaction-preferences.json" if kind == "file" else ".interaction-preferences.lock")).symlink_to(target)
    with pytest.raises((PermissionError, OSError)):
        save()
    assert target.read_text() == "PRESERVE"


def test_failed_replace_keeps_last_saved_choice_and_cleans_temporary_file():
    save()
    before = preferences._path(ALICE).read_bytes()
    with patch.object(preferences.os, "replace", side_effect=OSError("synthetic write failure")):
        with pytest.raises(OSError):
            save(revision=1, mode="balanced")
    assert preferences._path(ALICE).read_bytes() == before
    assert not list(preferences._path(ALICE).parent.glob(".preferences-*"))


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO requires POSIX")
@pytest.mark.parametrize("kind", ["store", "lock"])
def test_nonregular_files_fail_without_blocking_the_chat_prompt(kind):
    root = personal_context.ensure_home(ALICE)
    path = root / ("interaction-preferences.json" if kind == "store" else ".interaction-preferences.lock")
    os.mkfifo(path)
    if kind == "store":
        with pytest.raises(preferences.StoreError):
            preferences.read(ALICE)
        assert preferences.prompt_for(ALICE["email"]) == ""
    with pytest.raises(preferences.StoreError):
        save()
    assert path.exists()


def test_prompt_refreshes_saved_mode_each_turn_and_never_treats_it_as_approval():
    assert "balanced" in preferences.prompt_for(ALICE["email"])
    save()
    prompt = preferences.prompt_for(ALICE["email"])
    assert "minimal" in prompt and "sensible defaults" in prompt
    assert "does not grant access" in prompt and "bypass a required approval" in prompt
    assert "balanced" in preferences.prompt_for(BOB["email"])
    assert preferences.prompt_for("") == ""


def test_unsupported_platform_never_uses_unlocked_or_symlink_following_storage(monkeypatch):
    monkeypatch.setattr(preferences, "fcntl", None)
    with pytest.raises(OSError):
        save()
    monkeypatch.delattr(os, "O_NOFOLLOW", raising=False)
    with pytest.raises(OSError):
        preferences.read(ALICE)
    assert preferences.prompt_for(ALICE["email"]) == ""


def test_api_uses_signed_identity_and_returns_no_paths_or_other_task_ids():
    from api import routes
    with patch("api.governance.enforce._request_identity", return_value=ALICE), \
         patch.object(routes, "j", lambda handler, payload: payload):
        value = preferences.handle(object(), body={"revision": 0, "user_mode": "minimal"})
        assert set(value) == {"revision", "user_mode", "session_id", "task_mode", "effective_mode"}
    assert preferences.read(BOB)["revision"] == 0


def test_api_conflicts_invalid_null_and_io_failure_have_actionable_bounded_errors():
    from api import routes
    with patch("api.governance.enforce._request_identity", return_value=ALICE), \
         patch.object(routes, "bad", lambda handler, message, status: (status, message)):
        assert preferences.handle(object(), body=None)[0] == 400
        save()
        assert preferences.handle(object(), body={"revision": 0, "user_mode": "minimal"})[0] == 409
        with patch.object(preferences, "_load", side_effect=OSError("private/path")):
            response = preferences.handle(object())
            assert response[0] == 503 and "private/path" not in response[1]


def test_route_permission_is_chat_use_not_governance_or_global_settings_write():
    from api.governance.catalog import route_permission
    for method in ("GET", "POST"):
        assert route_permission("/api/interaction/preferences", method) == "chat:use"
