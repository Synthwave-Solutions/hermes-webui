import json
import threading
from types import SimpleNamespace

import pytest


def messages(action="create", *, call_id="new", success=True, **result):
    return [{"role": "assistant", "tool_calls": [{"id": call_id, "function": {
        "name": "skill_manage", "arguments": json.dumps({"action": action,
        "name": "PRIVATE-SKILL", "content": "PRIVATE-CONTENT", "old_string": "old", "new_string": "new"})}}]},
        {"role": "tool", "tool_call_id": call_id,
         "content": json.dumps({"success": success, **result})}]


@pytest.fixture
def activity(monkeypatch, tmp_path):
    from api import skill_learning_activity as mod, config
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    return mod


def test_counts_only_confirmed_new_skill_changes(activity):
    prior = messages(call_id="old")
    rows = (prior + messages() + messages("patch", call_id="patch")
            + messages("edit", call_id="edit")
            + messages(call_id="denied", success=False)
            + messages(call_id="staged", staged=True)
            + messages(call_id="pending", pending_id="unapproved")
            + messages("delete", call_id="delete"))
    rows += [{"role": "tool", "tool_call_id": "unknown", "content": '{"success":true}'}]
    assert activity.successful_skill_counts(rows, prior) == {"created": 1, "patched": 1, "updated": 1}


@pytest.mark.parametrize("kind", ["string-success", "memory", "duplicate-call", "malformed", "batch-rollback"])
def test_uncertain_or_non_skill_evidence_is_not_counted(activity, kind):
    rows = messages()
    if kind == "string-success":
        rows[-1]["content"] = '{"success":"true"}'
    elif kind == "memory":
        rows[0]["tool_calls"][0]["function"]["name"] = "memory"
    elif kind == "duplicate-call":
        rows.insert(0, rows[0])
    elif kind == "malformed":
        rows[-1]["content"] = '[]'
    elif kind == "batch-rollback":
        rows[0]["tool_calls"][0]["function"]["arguments"] = json.dumps({"operations":[{"action":"create"}]})
        rows[-1]["content"] = '{"success":false,"completed_before_failure":1}'
    assert activity.successful_skill_counts(rows, []) == {"created":0,"patched":0,"updated":0}


def test_recording_failure_preserves_native_summary_and_context_reset(activity, monkeypatch):
    from agent import background_review as native
    activity.install_adapter()
    def fail(*args, **kwargs):
        raise OSError("synthetic disk error")
    monkeypatch.setattr(activity, "record", fail)
    def run_review(*args, **kwargs):
        assert native.summarize_background_review_actions(messages(), [], notification_mode="off") == []
    monkeypatch.setattr(native, "_run_review_in_thread", run_review)
    with activity.turn_scope("a@example.test", "r", "p", "chat-a"):
        target, _ = native.spawn_background_review_thread(SimpleNamespace(), [], task_cfg={})
        target()
        assert activity._REVIEW.get() is None


def test_private_restart_safe_minimal_store(activity, tmp_path):
    scope = activity.ReviewScope("a@example.test", "run-a", "profile-a", "chat-a")
    activity.record(scope, {"created": 1, "patched": 2, "updated": 0}, now=1000)
    activity.record(scope, {"created": 1, "patched": 2, "updated": 0}, now=1000)
    data = activity.read_activity("a@example.test", "chat-a", now=1001)
    assert len(data["events"]) == 1
    assert data["events"][0]["counts"] == {"created": 1, "patched": 2, "updated": 0}
    assert activity.read_activity("b@example.test", "chat-a", now=1001)["events"] == []
    text = "".join(p.read_text() for p in tmp_path.rglob("*.json"))
    assert not any(s in text for s in ("example.test", "profile-a", "run-a", "PRIVATE"))
    assert all(p.stat().st_mode & 0o077 == 0 for p in tmp_path.rglob("*.json"))
    # Read through a fresh Python interpreter, not in-memory state.
    import subprocess
    code = ("from api import config,skill_learning_activity as a; "
            f"config.STATE_DIR={str(tmp_path)!r}; "
            "print(len(a.read_activity('a@example.test','chat-a',now=1001)['events']))")
    import sys
    assert subprocess.check_output([sys.executable, "-c", code], text=True).strip() == "1"


def test_native_late_review_keeps_actor_and_counts_structured_success(activity, monkeypatch):
    from agent import background_review as native
    from run_agent import AIAgent
    from tools import thread_context
    started, release, done = threading.Event(), threading.Event(), threading.Event()
    monkeypatch.setattr(thread_context, "_callback_api", lambda: (
        lambda: None, lambda: None, lambda value: None, lambda value: None))
    monkeypatch.setattr(native, "load_background_review_settings", lambda: (True, {}))
    def run_review(*args, **kwargs):
        started.set()
        try:
            assert release.wait(5)
            native.summarize_background_review_actions(messages("patch"), [], notification_mode="off")
        finally:
            done.set()
    monkeypatch.setattr(native, "_run_review_in_thread", run_review)
    with activity.turn_scope("a@example.test", "run-a", "profile-a", "chat-a"):
        AIAgent._spawn_background_review(SimpleNamespace(), [], review_skills=True)
        assert started.wait(5)
    with activity.turn_scope("b@example.test", "run-b", "profile-b", "chat-b"):
        release.set()
        assert done.wait(5)
    assert activity.read_activity("a@example.test", "chat-a")["events"][0]["counts"]["patched"] == 1
    assert activity.read_activity("b@example.test", "chat-a")["events"] == []


def test_api_own_identity_only_and_no_cache(activity, monkeypatch):
    from api import ownership, personal_context
    monkeypatch.setattr(ownership, "_request_identity", lambda h: {"email": h.email})
    monkeypatch.setattr(personal_context, "session_for", lambda identity, sid: SimpleNamespace())
    monkeypatch.setattr(activity, "j", lambda h, data, **kw: (data, kw))
    actor = SimpleNamespace(email="a@example.test")
    data, opts = activity.handle_get(actor, "session_id=chat-a")
    assert data["events"] == []
    assert opts["extra_headers"]["Cache-Control"] == "no-store"
    data, opts = activity.handle_get(actor, "session_id=chat-a&actor=b@example.test")
    assert opts["status"] == 400
    data, opts = activity.handle_get(SimpleNamespace(email=None), "session_id=chat-a")
    assert opts["status"] == 401


@pytest.mark.parametrize("fault", ["json", "oversize", "symlink", "fifo", "public", "hardlink"])
def test_unsafe_or_malformed_store_fails_bounded_without_overwrite(activity, tmp_path, fault):
    import os
    path, lock = activity._paths("a@example.test")
    foreign = tmp_path / "foreign"
    foreign.write_text("unchanged")
    if fault == "symlink":
        path.symlink_to(foreign)
    elif fault == "fifo":
        os.mkfifo(path, 0o600)
    elif fault == "hardlink":
        os.link(foreign, path)
    else:
        path.write_text("[" if fault == "json" else "x" * (activity._MAX_BYTES + 1) if fault == "oversize" else "[]")
        path.chmod(0o644 if fault == "public" else 0o600)
    with pytest.raises((OSError, ValueError)):
        activity.read_activity("a@example.test", "chat-a")
    assert not activity.record(activity.ReviewScope("a@example.test", "r", "p", "chat-a"),
                               {"created": 1, "patched": 0, "updated": 0})
    assert foreign.read_text() == "unchanged"


def test_actor_and_session_filters_retention_and_revoked_membership(activity, monkeypatch):
    from api import ownership, personal_context
    for i in range(105):
        assert activity.record(activity.ReviewScope("a@example.test", str(i), "p", "chat-a"),
                               {"created": 1, "patched": 0, "updated": 0}, now=1000+i)
    assert len(activity.read_activity("a@example.test", "chat-a", now=1200)["events"]) == 100
    assert activity.read_activity("a@example.test", "chat-b", now=1200)["events"] == []
    assert activity.read_activity("a@example.test", "chat-a", now=activity._RETENTION+1200)["events"] == []
    monkeypatch.setattr(ownership, "_request_identity", lambda h: {"email": "a@example.test"})
    monkeypatch.setattr(activity, "j", lambda h, data, **kw: (data, kw))
    def denied(*args):
        raise PermissionError("removed")
    monkeypatch.setattr(personal_context, "session_for", denied)
    assert activity.handle_get(None, "session_id=chat-a")[1]["status"] == 404


def test_manual_or_foreground_summary_does_not_create_automatic_notice(activity, monkeypatch):
    from agent import background_review as native
    activity.install_adapter()
    original = native.spawn_background_review_thread
    assert activity.install_adapter()
    assert native.spawn_background_review_thread is original
    def run_review(*args, **kwargs):
        native.summarize_background_review_actions(messages(), [], notification_mode="off")
    monkeypatch.setattr(native, "_run_review_in_thread", run_review)
    with activity.turn_scope("a@example.test", "r", "p", "chat-a"):
        native.summarize_background_review_actions(messages(), [], notification_mode="off")
        target, _ = native.spawn_background_review_thread(SimpleNamespace(), [], focus="explicit", task_cfg={})
        target()
    assert activity.read_activity("a@example.test", "chat-a")["events"] == []


def test_actual_native_create_patch_batch_and_failure_observed_without_provider(activity, monkeypatch, tmp_path):
    import hermes_constants
    from api import profiles
    from agent import background_review as native
    from tools import skill_manager_tool as manager, skill_provenance, skills_tool
    home = tmp_path / "engine"
    home.mkdir()
    (home / "config.yaml").write_text("{}\n")
    monkeypatch.setenv("HERMES_HOME", str(home))
    # Disable outbound sync transport; tool storage and successful result
    # generation, autonomous preflight and file guards remain native.
    monkeypatch.setattr(manager, "_maybe_debounced_sync_push", lambda *args: None)
    monkeypatch.setattr(manager, "SKILLS_DIR", manager._SKILLS_DIR_AT_IMPORT)
    token = hermes_constants.set_hermes_home_override(home)
    origin = skill_provenance.set_current_write_origin("background_review")
    results = []
    try:
        profiles.patch_skill_home_modules(home)
        content = "---\nname: fixture-learning\ndescription: Local synthetic test\n---\n# Workflow\nOriginal step.\n"
        calls = [
            {"action": "create", "name": "fixture-learning", "content": content},
            {"action": "patch", "name": "fixture-learning", "old_string": "Original step.", "new_string": "Improved step."},
            {"action": "patch", "name": "fixture-learning", "old_string": "missing text", "new_string": "never applied"},
            {"action": "patch", "name": "fixture-learning", "old_string": "Improved step.", "new_string": "Improved step."},
            {"action": "batch", "name": "fixture-learning", "operations": [
                {"action": "patch", "name": "fixture-learning", "old_string": "Improved step.", "new_string": "Final step."}]},
        ]
        for i, call in enumerate(calls):
            if call["action"] in ("patch", "batch"):
                skills_tool.skill_view("fixture-learning")
            result = manager.skill_manage(**call)
            results.extend([{"role": "assistant", "tool_calls": [{"id": str(i), "function": {
                "name": "skill_manage", "arguments": json.dumps(call)}}]},
                {"role": "tool", "tool_call_id": str(i), "content": result}])
        assert json.loads(results[1]["content"])["success"] is True
        assert json.loads(results[3]["content"])["success"] is True, results[3]["content"]
        assert json.loads(results[5]["content"])["success"] is False
        assert json.loads(results[9]["content"])["success"] is True, results[9]["content"]
        assert "Final step." in (home / "skills/fixture-learning/SKILL.md").read_text()
        def run_review(*args, **kwargs):
            native.summarize_background_review_actions(results, [], notification_mode="off")
        monkeypatch.setattr(native, "_run_review_in_thread", run_review)
        with activity.turn_scope("a@example.test", "real-tools", str(home), "chat-a"):
            target, _ = native.spawn_background_review_thread(SimpleNamespace(), [], task_cfg={})
            target()
        assert activity.read_activity("a@example.test", "chat-a")["events"][0]["counts"] == {
            "created": 1, "patched": 2, "updated": 0}
    finally:
        skill_provenance.reset_current_write_origin(origin)
        hermes_constants.reset_hermes_home_override(token)


def test_unsupported_platform_keeps_turn_running_and_reports_unavailable(activity, monkeypatch):
    from api import ownership, personal_context
    monkeypatch.setattr(activity, "fcntl", None)
    with activity.turn_scope("a@example.test", "r", "p", "chat-a"):
        assert activity._TURN.get().actor == "a@example.test"
        assert not activity.record(activity._TURN.get(), {"created": 1, "patched": 0, "updated": 0})
    assert activity._TURN.get() is None
    monkeypatch.setattr(ownership, "_request_identity", lambda h: {"email": "a@example.test"})
    monkeypatch.setattr(personal_context, "session_for", lambda *args: SimpleNamespace())
    monkeypatch.setattr(activity, "j", lambda h, data, **kw: (data, kw))
    assert activity.handle_get(None, "session_id=chat-a")[1]["status"] == 503


def test_same_actor_concurrent_appends_preserve_all_confirmed_events(activity):
    from concurrent.futures import ThreadPoolExecutor
    def append(i):
        return activity.record(activity.ReviewScope("a@example.test", str(i), "p", "chat-a"),
                               {"created": 1, "patched": 0, "updated": 0}, now=1000+i)
    with ThreadPoolExecutor(max_workers=8) as executor:
        assert all(executor.map(append, range(24)))
    rows = activity.read_activity("a@example.test", "chat-a", now=1100)["events"]
    assert len(rows) == len({row["id"] for row in rows}) == 24


def test_contended_lock_fails_with_bounded_wait(activity):
    import os
    import time
    _, lock = activity._paths("a@example.test")
    fd = activity._open_regular(lock, os.O_RDWR | os.O_CREAT)
    activity.fcntl.flock(fd, activity.fcntl.LOCK_EX)
    started = time.monotonic()
    try:
        assert not activity.record(activity.ReviewScope("a@example.test", "r", "p", "chat-a"),
                                   {"created": 1, "patched": 0, "updated": 0})
        assert time.monotonic() - started < 3
    finally:
        os.close(fd)


@pytest.mark.parametrize("kind", ["symlink", "fifo"])
def test_unsafe_lock_rejected_without_waiting(activity, tmp_path, kind):
    import os
    _, lock = activity._paths("a@example.test")
    if kind == "symlink":
        foreign = tmp_path / "foreign-lock"
        foreign.write_text("unchanged")
        lock.symlink_to(foreign)
    else:
        os.mkfifo(lock, 0o600)
    with pytest.raises(OSError):
        activity.read_activity("a@example.test", "chat-a")
