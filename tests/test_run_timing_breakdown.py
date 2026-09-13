"""Exercise content-free timing on the real streaming worker and journal."""

import threading
import time
import types
import asyncio
import json
import sys
from collections import OrderedDict

import httpx
import pytest
from api import config
from tests.test_issue5121_provider_auth_terminal_error import (
    _isolate_session_dir as _isolate_session_dir,
    _isolate_stream_state as _isolate_stream_state,
    _isolate_agent_locks as _isolate_agent_locks,
    _neutralize_credential_self_heal as _neutralize_credential_self_heal,
    _mock_hermes_modules as _mock_hermes_modules,
    _prepare_session,
    _run_stream,
    _queue_events,
    MockAgent,
    streaming,
)


@pytest.fixture
def timings(monkeypatch):
    records = []
    original = streaming.RunJournalWriter.append_sse_event

    def append(writer, event, payload=None):
        if event == "run_timing":
            records.append(payload)
        return original(writer, event, payload)

    monkeypatch.setattr(streaming.RunJournalWriter, "append_sse_event", append)
    monkeypatch.setattr(
        streaming, "_prewarm_skill_tool_modules", lambda: time.sleep(0.02)
    )
    monkeypatch.setattr(
        streaming,
        "_install_streaming_cronjob_profile_wrapper",
        lambda: time.sleep(0.02),
    )
    monkeypatch.setitem(
        sys.modules,
        "tools.mcp_tool",
        types.SimpleNamespace(discover_mcp_tools=lambda: time.sleep(0.02)),
    )
    monkeypatch.setattr(config, "SESSION_AGENT_CACHE", OrderedDict())
    return records


@pytest.fixture(autouse=True)
def no_http_requests(monkeypatch):
    attempts = []

    def refused(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Unexpected HTTP request in isolated timing test")

    async def refused_async(*args, **kwargs):
        return refused(*args, **kwargs)

    monkeypatch.setattr(httpx.Client, "send", refused)
    monkeypatch.setattr(httpx.AsyncClient, "send", refused_async)
    yield
    assert not attempts


class Answer(MockAgent):
    def run_conversation(self, **kwargs):
        self.stream_delta_callback("Synthetic answer")
        time.sleep(0.02)
        return {
            "completed": True,
            "final_response": "Synthetic answer",
            "messages": list(kwargs.get("conversation_history") or [])
            + [
                {"role": "user", "content": kwargs["persist_user_message"]},
                {"role": "assistant", "content": "Synthetic answer"},
            ],
        }


@pytest.mark.parametrize("mode", ["normal", "super"])
def test_real_turn_reports_separate_setup_and_posttoken_intervals(
    tmp_path, monkeypatch, timings, mode
):
    s = _prepare_session(
        "timing_own", "timing_stream", pending_user_message="DO_NOT_COPY_INPUT"
    )
    s.chat_mode = mode
    queue = _run_stream(
        monkeypatch, s, "timing_stream", Answer, workspace=str(tmp_path)
    )
    by_stage = {r["stage"]: r for r in timings}
    assert set(by_stage) == {
        "skill_modules",
        "cron_wrapper",
        "env_lock_wait",
        "env_lock_hold",
        "mcp_discovery",
        "agent_constructor",
        "agent_run",
        "checkpoint_join",
    }
    assert all(
        set(r) == {"stage", "elapsed_ms", "duration_ms", "outcome"} for r in timings
    )
    assert all(r["duration_ms"] >= 0 for r in timings)
    for stage in ["skill_modules", "cron_wrapper", "agent_run"]:
        assert by_stage[stage]["duration_ms"] >= 15
    assert by_stage["mcp_discovery"]["outcome"] == (
        "skipped" if mode == "normal" else "completed"
    )
    assert "DO_NOT_COPY_INPUT" not in str(timings) and str(tmp_path) not in str(timings)
    events = _queue_events(queue)
    assert any(e == "done" for e, _ in events)
    assert not any(e == "run_timing" for e, _ in events)
    rows = [
        json.loads(line)
        for line in (tmp_path / "sessions/_run_journal/timing_own/timing_stream.jsonl")
        .read_text()
        .splitlines()
    ]
    assert [r["payload"] for r in rows if r.get("event") == "run_timing"] == timings


def test_journal_timing_failure_cannot_break_real_answer(
    tmp_path, monkeypatch, timings
):
    original = streaming.RunJournalWriter.append_sse_event

    def unavailable(writer, event, payload=None):
        if event == "run_timing":
            raise OSError("private journal unavailable")
        return original(writer, event, payload)

    monkeypatch.setattr(streaming.RunJournalWriter, "append_sse_event", unavailable)
    s = _prepare_session(
        "timing_failure",
        "timing_failure_stream",
        pending_user_message="Synthetic prompt",
    )
    queue = _run_stream(
        monkeypatch, s, "timing_failure_stream", Answer, workspace=str(tmp_path)
    )
    assert any(e == "done" for e, _ in _queue_events(queue))


def test_discovery_failure_remains_nonfatal_and_is_distinguishable(
    tmp_path, monkeypatch, timings
):
    def unavailable():
        raise RuntimeError("DO_NOT_COPY_CONNECTOR_DETAILS")

    monkeypatch.setattr(
        sys.modules["tools.mcp_tool"], "discover_mcp_tools", unavailable
    )
    session = _prepare_session(
        "timing_mcp_failure",
        "timing_mcp_failure_stream",
        pending_user_message="Synthetic prompt",
    )
    session.chat_mode = "super"
    result = _run_stream(
        monkeypatch,
        session,
        "timing_mcp_failure_stream",
        Answer,
        workspace=str(tmp_path),
    )
    assert (
        next(r for r in timings if r["stage"] == "mcp_discovery")["outcome"]
        == "unavailable"
    )
    assert "DO_NOT_COPY_CONNECTOR_DETAILS" not in str(timings)
    assert any(e == "done" for e, _ in _queue_events(result))


def test_raised_agent_preserves_error_and_records_return_boundary(
    tmp_path, monkeypatch, timings
):
    class Failed(MockAgent):
        def run_conversation(self, **kwargs):
            raise PermissionError("Access restricted: synthetic refusal")

    s = _prepare_session(
        "timing_raised", "timing_raised_stream", pending_user_message="Synthetic prompt"
    )
    queue = _run_stream(
        monkeypatch, s, "timing_raised_stream", Failed, workspace=str(tmp_path)
    )
    assert next(r for r in timings if r["stage"] == "agent_run")["outcome"] == "raised"
    assert any(
        e == "apperror" and d["type"] == "governance_denied"
        for e, d in _queue_events(queue)
    )


def test_contended_lock_is_timed_without_journal_io_under_owned_lock(
    tmp_path, monkeypatch, timings
):
    class ObservedLock:
        def __init__(self):
            self.lock = threading.Lock()
            self.attempt = threading.Event()
            self.owner = None

        def __enter__(self):
            self.attempt.set()
            self.lock.acquire()
            self.owner = threading.get_ident()

        def __exit__(self, *args):
            self.owner = None
            self.lock.release()

    lock = ObservedLock()
    lock.lock.acquire()

    def release():
        assert lock.attempt.wait(3)
        time.sleep(0.04)
        lock.lock.release()

    holder = threading.Thread(target=release)
    holder.start()
    monkeypatch.setattr(streaming, "_ENV_LOCK", lock)
    original = streaming.RunJournalWriter.append_sse_event
    owned_writes = []

    def append(writer, event, payload=None):
        if event == "run_timing" and lock.owner == threading.get_ident():
            owned_writes.append(True)
        return original(writer, event, payload)

    monkeypatch.setattr(streaming.RunJournalWriter, "append_sse_event", append)
    session = _prepare_session(
        "timing_lock", "timing_lock_stream", pending_user_message="Synthetic prompt"
    )
    try:
        _run_stream(
            monkeypatch, session, "timing_lock_stream", Answer, workspace=str(tmp_path)
        )
    finally:
        holder.join(4)
    assert not holder.is_alive() and not owned_writes
    assert (
        next(r for r in timings if r["stage"] == "env_lock_wait")["duration_ms"] >= 30
    )


def test_cancelled_error_propagates_after_recording_agent_boundary(
    tmp_path, monkeypatch, timings
):
    class Cancelled(MockAgent):
        def run_conversation(self, **kwargs):
            raise asyncio.CancelledError()

    session = _prepare_session(
        "timing_cancel", "timing_cancel_stream", pending_user_message="Synthetic prompt"
    )
    with pytest.raises(asyncio.CancelledError):
        _run_stream(
            monkeypatch,
            session,
            "timing_cancel_stream",
            Cancelled,
            workspace=str(tmp_path),
        )
    assert next(r for r in timings if r["stage"] == "agent_run")["outcome"] == "raised"


def test_constructor_and_lru_close_costs_are_separate(tmp_path, monkeypatch, timings):
    class SlowConstructor(Answer):
        def __init__(self, **kwargs):
            time.sleep(0.02)
            super().__init__(**kwargs)

    config.SESSION_AGENT_CACHE["inactive-other"] = (
        MockAgent(session_id="inactive-other"),
        "old-signature",
    )
    monkeypatch.setattr(config, "SESSION_AGENT_CACHE_MAX", 1)
    closed = []

    def close(sid, agent):
        closed.append(sid)
        time.sleep(0.03)
        return True

    monkeypatch.setattr(streaming, "_close_evicted_agent_at_session_boundary", close)
    session = _prepare_session(
        "timing_close", "timing_close_stream", pending_user_message="Synthetic prompt"
    )
    result = _run_stream(
        monkeypatch,
        session,
        "timing_close_stream",
        SlowConstructor,
        workspace=str(tmp_path),
    )
    assert closed == ["inactive-other"]
    by_stage = {r["stage"]: r for r in timings}
    assert by_stage["agent_constructor"]["duration_ms"] >= 15
    assert by_stage["cache_eviction_close"]["duration_ms"] >= 25
    assert "inactive-other" not in str(timings)
    assert any(e == "done" for e, _ in _queue_events(result))
