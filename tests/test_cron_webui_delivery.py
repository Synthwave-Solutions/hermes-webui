"""Regression coverage for the cron WebUI delivery bridge.

Scheduler-delivery / polling-completion-update tickets (reported 2026-08-26):
a cron job created in a WebUI conversation carries ``origin.platform ==
"webui"``, which the engine cannot deliver to ("unknown platform 'webui'"),
so runs finished with ``last_status: ok`` while the update never reached the
originating conversation and the failure stayed invisible. The bridge in
``api/cron_webui_delivery.py`` posts the update into the originating WebUI
session and tracks the delivery outcome separately from run status.

Covers the ticket's required regressions: delivery into the conversation,
successful run with failed delivery, duplicate-run refusal, and a recurring
schedule delivering once per run.
"""

from __future__ import annotations

import io
import json
import sys
import types
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import api.cron_webui_delivery as cwd


class _JSONHandler:
    def __init__(self):
        self.status = None
        self.response_headers = []
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass


def _payload(handler):
    return json.loads(handler.wfile.getvalue().decode("utf-8"))


@pytest.fixture
def bridge_env(monkeypatch, tmp_path):
    """Isolated STATE_DIR / SESSION_DIR / hermes home for the bridge."""
    import api.config as config
    import api.models as models

    state_dir = tmp_path / "state"
    session_dir = state_dir / "sessions"
    session_dir.mkdir(parents=True)
    home = tmp_path / "hermes_home"
    (home / "cron" / "output").mkdir(parents=True)

    monkeypatch.setattr(config, "STATE_DIR", state_dir)
    monkeypatch.setattr(models, "SESSION_DIR", session_dir)
    monkeypatch.setattr(models, "SESSION_INDEX_FILE", session_dir / "_index.json")
    # Keep the test hermetic: no state.db mirroring or stale-pending repair.
    monkeypatch.setattr(models, "_sync_sidecar_from_state_db_if_newer", lambda s: False)
    monkeypatch.setattr(models, "_repair_stale_pending", lambda s: False)
    # The process-lifetime watermark must not leak between tests.
    monkeypatch.setattr(cwd, "_MEMORY_WATERMARKS", {})

    return SimpleNamespace(
        state_dir=state_dir, session_dir=session_dir, home=home, models=models
    )


def _write_session(env, sid):
    payload = {
        "session_id": sid,
        "title": "Origin conversation",
        "workspace": str(env.session_dir),
        "model": "test-model",
        "created_at": 1.0,
        "updated_at": 1.0,
        "messages": [{"role": "user", "content": "monitor this please", "timestamp": 1.0}],
    }
    (env.session_dir / f"{sid}.json").write_text(json.dumps(payload), encoding="utf-8")


def _read_session(env, sid):
    return json.loads((env.session_dir / f"{sid}.json").read_text(encoding="utf-8"))


def _job(job_id, sid, run_at, *, status="ok", deliver="origin", **extra):
    job = {
        "id": job_id,
        "name": "Peterson release monitor",
        "deliver": deliver,
        "origin": {"platform": "webui", "chat_id": sid, "thread_id": None},
        "last_run_at": run_at,
        "last_status": status,
        "last_error": None,
        "last_delivery_error": None,
        "schedule": {"kind": "interval", "minutes": 5, "display": "every 5m"},
    }
    job.update(extra)
    return job


def _write_output(env, job_id, body, name="run.md"):
    out_dir = env.home / "cron" / "output" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / name).write_text(
        f"# Cron Job: test\n\n## Prompt\n\nprompt text\n\n## Response\n\n{body}\n",
        encoding="utf-8",
    )


def _now_iso(offset_secs=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_secs)).isoformat()


# -- Delivery into the originating conversation ------------------------------

def test_completed_run_delivers_update_into_originating_conversation(bridge_env):
    sid = "cwddeliv001"
    _write_session(bridge_env, sid)
    _write_output(bridge_env, "job1", "PR checks are green, promotion continued.")
    job = _job("job1", sid, _now_iso())

    from api.background_process import get_or_create_session_channel

    ch = get_or_create_session_channel(sid)
    q = ch.subscribe()
    try:
        actions = cwd.process_jobs_once([job], home=bridge_env.home)
    finally:
        ch.unsubscribe(q)

    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_DELIVERED]
    data = _read_session(bridge_env, sid)
    assert len(data["messages"]) == 2
    update = data["messages"][-1]
    assert update["role"] == "assistant"
    assert "Peterson release monitor" in update["content"]
    assert "PR checks are green" in update["content"]
    assert update["cron_delivery"]["job_id"] == "job1"

    # An open tab is notified via the existing session-updated frame.
    event_name, event_data = q.get_nowait()
    assert event_name == "session-updated"
    assert event_data["session_id"] == sid
    assert event_data["message_count"] == 2
    assert event_data["source"] == "cron_delivery"

    # Delivery outcome is recorded separately from run status.
    ledger = cwd.load_ledger()
    entry = ledger["jobs"]["job1"]
    assert entry["outcome"] == cwd.OUTCOME_DELIVERED
    assert entry["run_at"] == job["last_run_at"]
    assert cwd.delivery_state_for_job(job) == ("delivered", None)


# -- Successful run whose delivery failed ------------------------------------

def test_successful_run_with_failed_delivery_is_visible_not_ok(bridge_env, monkeypatch):
    sid = "cwdmissing1"  # session sidecar intentionally absent
    _write_output(bridge_env, "job2", "output that has nowhere to go")
    job = _job("job2", sid, _now_iso())

    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_FAILED]
    assert "not found" in actions[0]["error"]

    status, error = cwd.delivery_state_for_job(job)
    assert status == "failed"
    assert "not found" in error

    # /api/crons/recent must surface the delivery failure instead of ok.
    import api.routes as routes

    cron_pkg = types.ModuleType("cron")
    cron_pkg.__path__ = []
    cron_jobs = types.ModuleType("cron.jobs")
    cron_jobs.list_jobs = lambda include_disabled=True: [job]
    monkeypatch.setitem(sys.modules, "cron", cron_pkg)
    monkeypatch.setitem(sys.modules, "cron.jobs", cron_jobs)
    monkeypatch.setattr(
        routes,
        "_latest_cron_session_info_for_jobs",
        lambda job_ids, completed_job_ids=None: {},
    )

    handler = _JSONHandler()
    routes._handle_cron_recent(handler, SimpleNamespace(query="since=0"))
    body = _payload(handler)
    assert handler.status == 200
    (completion,) = body["completions"]
    assert completion["status"] == "error"
    assert completion["status_detail"] == "delivery_failed"
    assert completion["delivery_status"] == "failed"
    assert "not found" in completion["delivery_error"]


# -- Duplicate-run refusal and recurring schedule ----------------------------

def test_duplicate_run_refusal_does_not_swallow_next_recurring_update(bridge_env):
    sid = "cwdrecur001"
    _write_session(bridge_env, sid)
    _write_output(bridge_env, "job3", "first run report", name="run1.md")
    first_run_at = _now_iso(-60)
    job = _job("job3", sid, first_run_at)

    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_DELIVERED]
    assert len(_read_session(bridge_env, sid)["messages"]) == 2

    # A duplicate-run refusal leaves last_run_at untouched: the tick is a
    # no-op, no duplicate post, and the watermark stays on the first run.
    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert actions == []
    assert len(_read_session(bridge_env, sid)["messages"]) == 2

    # The NEXT completed run of the recurring schedule still delivers.
    _write_output(bridge_env, "job3", "second run report", name="run2.md")
    job_next = dict(job, last_run_at=_now_iso())
    actions = cwd.process_jobs_once([job_next], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_DELIVERED]
    messages = _read_session(bridge_env, sid)["messages"]
    assert len(messages) == 3
    assert "second run report" in messages[-1]["content"]

    # And a repeat tick after that stays quiet again.
    assert cwd.process_jobs_once([job_next], home=bridge_env.home) == []
    assert len(_read_session(bridge_env, sid)["messages"]) == 3


# -- Failed run posts an actionable failure update ---------------------------

def test_failed_run_posts_concise_failure_update(bridge_env):
    sid = "cwdfail0001"
    _write_session(bridge_env, sid)
    job = _job(
        "job4", sid, _now_iso(), status="error",
        last_error="agent crashed: boom",
    )

    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_DELIVERED]
    update = _read_session(bridge_env, sid)["messages"][-1]
    assert "failed" in update["content"]
    assert "agent crashed: boom" in update["content"]


# -- SILENT suppression ------------------------------------------------------

def test_silent_response_is_suppressed_but_outcome_recorded(bridge_env):
    sid = "cwdsilent01"
    _write_session(bridge_env, sid)
    _write_output(bridge_env, "job5", "[SILENT]")
    job = _job("job5", sid, _now_iso())

    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_SILENT]
    assert len(_read_session(bridge_env, sid)["messages"]) == 1
    assert cwd.delivery_state_for_job(job) == ("silent", None)


# -- External target failure notice ------------------------------------------

def test_external_delivery_failure_posts_actionable_notice(bridge_env):
    sid = "cwdext00001"
    _write_session(bridge_env, sid)
    job = _job(
        "job6", sid, _now_iso(),
        deliver="google_chat:users/12345",
        last_delivery_error="delivery error: chat_id must match 'users/<id>'",
    )

    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_EXTERNAL_FAILED]
    update = _read_session(bridge_env, sid)["messages"][-1]
    assert "google_chat:users/12345" in update["content"]
    assert "chat_id must match" in update["content"]

    status, error = cwd.delivery_state_for_job(job)
    assert status == "failed"
    assert "chat_id must match" in error


def test_external_delivery_success_is_not_duplicated_into_chat(bridge_env):
    sid = "cwdext00002"
    _write_session(bridge_env, sid)
    job = _job("job7", sid, _now_iso(), deliver="telegram:12345")

    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_SKIPPED_EXTERNAL]
    assert len(_read_session(bridge_env, sid)["messages"]) == 1
    assert cwd.delivery_state_for_job(job) == ("delivered", None)


# -- Historical runs never flood on first sighting ---------------------------

def test_first_sighting_of_stale_run_initializes_watermark_silently(bridge_env):
    sid = "cwdstale001"
    _write_session(bridge_env, sid)
    _write_output(bridge_env, "job8", "old report")
    stale_run_at = _now_iso(-(cwd.FRESH_RUN_WINDOW_SECS + 600))
    job = _job("job8", sid, stale_run_at)

    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_SKIPPED_STALE]
    assert len(_read_session(bridge_env, sid)["messages"]) == 1

    # A later fresh run on the same job delivers normally.
    _write_output(bridge_env, "job8", "fresh report", name="run2.md")
    job_next = dict(job, last_run_at=_now_iso())
    actions = cwd.process_jobs_once([job_next], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_DELIVERED]
    assert "fresh report" in _read_session(bridge_env, sid)["messages"][-1]["content"]


# -- Busy session defers, never drops ----------------------------------------

def test_busy_session_defers_delivery_to_next_tick(bridge_env, monkeypatch):
    sid = "cwdbusy0001"
    _write_session(bridge_env, sid)
    _write_output(bridge_env, "job9", "deferred report")
    job = _job("job9", sid, _now_iso())

    monkeypatch.setattr(cwd, "_session_busy", lambda _sid: True)
    assert cwd.process_jobs_once([job], home=bridge_env.home) == []
    assert len(_read_session(bridge_env, sid)["messages"]) == 1
    # Watermark was NOT advanced; the update is pending, not lost.
    assert cwd.delivery_state_for_job(job) == ("pending", None)

    monkeypatch.setattr(cwd, "_session_busy", lambda _sid: False)
    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_DELIVERED]
    assert "deferred report" in _read_session(bridge_env, sid)["messages"][-1]["content"]


# -- Ledger durability: D4 (26 Aug 2026 adversarial review) ------------------

def test_unwritable_ledger_posts_each_update_at_most_once_per_process(
    bridge_env, monkeypatch
):
    """A persistent ledger write failure must not re-post every tick."""
    sid = "cwdnodisk01"
    _write_session(bridge_env, sid)
    _write_output(bridge_env, "job11", "one-shot report")
    job = _job("job11", sid, _now_iso())

    def _broken_save(_ledger):
        raise OSError("state dir is read-only")

    monkeypatch.setattr(cwd, "_save_ledger", _broken_save)

    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_DELIVERED]
    assert len(_read_session(bridge_env, sid)["messages"]) == 2

    # The in-memory watermark survives the failed write: later ticks are
    # no-ops instead of re-posting the same run every POLL_INTERVAL.
    for _ in range(3):
        assert cwd.process_jobs_once([job], home=bridge_env.home) == []
    assert len(_read_session(bridge_env, sid)["messages"]) == 2

    # And the surfaced state reflects the delivery, not a bogus "pending".
    assert cwd.delivery_state_for_job(job) == ("delivered", None)


def test_corrupt_ledger_does_not_replay_fresh_window_runs(bridge_env):
    """A garbled ledger initializes watermarks WITHOUT delivering."""
    sid = "cwdcorrupt1"
    _write_session(bridge_env, sid)
    _write_output(bridge_env, "job12", "already delivered once")
    job = _job("job12", sid, _now_iso())

    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_DELIVERED]
    assert len(_read_session(bridge_env, sid)["messages"]) == 2

    # Simulate a restart with a damaged ledger: process memory is empty and
    # the on-disk ledger is garbage, while the run is inside the fresh window.
    cwd._MEMORY_WATERMARKS.clear()
    (bridge_env.state_dir / cwd.LEDGER_FILENAME).write_text(
        "{not json", encoding="utf-8"
    )

    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_SKIPPED_STALE]
    assert len(_read_session(bridge_env, sid)["messages"]) == 2  # no replay

    # The rebuilt ledger is valid again and the NEXT run still delivers.
    _write_output(bridge_env, "job12", "next run report", name="run2.md")
    job_next = dict(job, last_run_at=_now_iso())
    actions = cwd.process_jobs_once([job_next], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_DELIVERED]
    assert "next run report" in _read_session(bridge_env, sid)["messages"][-1]["content"]


def test_missing_ledger_is_not_treated_as_corruption(bridge_env):
    """First boot (no ledger file) still delivers fresh runs normally."""
    sid = "cwdfirstrun"
    _write_session(bridge_env, sid)
    _write_output(bridge_env, "job14", "fresh first boot report")
    job = _job("job14", sid, _now_iso())

    assert not (bridge_env.state_dir / cwd.LEDGER_FILENAME).exists()
    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_DELIVERED]


def test_watermark_is_persisted_before_delivery(bridge_env, monkeypatch):
    """Persist-then-deliver: a crash mid-post loses at most one update."""
    sid = "cwdorder001"
    _write_session(bridge_env, sid)
    _write_output(bridge_env, "job13", "ordering probe")
    job = _job("job13", sid, _now_iso())

    seen = {}
    real_deliver = cwd.deliver_update_to_session

    def _spy(session_id, text, job_arg):
        on_disk = json.loads(
            (bridge_env.state_dir / cwd.LEDGER_FILENAME).read_text(encoding="utf-8")
        )
        seen["entry"] = on_disk["jobs"].get("job13")
        return real_deliver(session_id, text, job_arg)

    monkeypatch.setattr(cwd, "deliver_update_to_session", _spy)
    actions = cwd.process_jobs_once([job], home=bridge_env.home)
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_DELIVERED]
    # At post time the watermark for this exact run was already on disk.
    assert seen["entry"] is not None
    assert seen["entry"]["run_at"] == job["last_run_at"]


# -- Non-WebUI jobs are untouched --------------------------------------------

def test_non_webui_origin_jobs_are_ignored(bridge_env):
    job = _job("job10", "1125980349", _now_iso())
    job["origin"]["platform"] = "telegram"
    assert cwd.process_jobs_once([job], home=bridge_env.home) == []
    ledger = cwd.load_ledger()
    assert "job10" not in ledger["jobs"]
