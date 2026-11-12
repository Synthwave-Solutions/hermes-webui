"""The empty-poll shortcut of /api/crons/recent may only say "empty" when the handler would."""
import json
import os
import time
from pathlib import Path

import pytest

import api.cron_bots as cron_bots
import api.cron_recent_precheck as precheck
import api.cron_scope as cron_scope
import api.profile_yaml_cache as profile_yaml_cache
import api.profiles as profiles

OLD = "2026-11-12T08:00:00+00:00"
NEW = "2026-11-12T12:00:00+00:00"
OLD_TS = 1794470400.0  # 2026-11-12T08:00:00Z
SINCE = OLD_TS + 3600.0
ME = "me@example.test"


def _write(home: Path, jobs, age: float = 10.0) -> Path:
    path = home / "cron" / "jobs.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"jobs": jobs}), encoding="utf-8")
    stamp = time.time() - age
    os.utime(path, (stamp, stamp))
    return path


def _job(job_id, last_run, owner=None, **extra):
    job = {"id": job_id, "name": job_id, "last_run_at": last_run}
    if owner:
        job["origin"] = {"platform": "webui", "user_id": owner}
    job.update(extra)
    return job


@pytest.fixture
def stores(tmp_path, monkeypatch):
    """An active store plus one other bot's store; the caller is a plain signed-in user."""
    profile_yaml_cache.clear()
    monkeypatch.delenv("HERMES_WEBUI_CRON_RECENT_PRECHECK", raising=False)
    active, other = tmp_path / "active", tmp_path / "other"
    state = {"admin": False, "identity": {"email": ME}}
    monkeypatch.setattr(precheck, "_active_jobs_file", lambda: active / "cron" / "jobs.json")
    monkeypatch.setattr(precheck, "_normalize", lambda job: dict(job))
    monkeypatch.setattr(profiles, "get_active_hermes_home", lambda: active)
    monkeypatch.setattr(cron_bots, "store_homes", lambda: [("default", active), ("otherbot", other)])
    monkeypatch.setattr(cron_scope, "_identity_for", lambda handler: state["identity"])
    monkeypatch.setattr(cron_scope, "_identity_is_cron_admin", lambda identity: state["admin"])
    yield type("Stores", (), {"active": active, "other": other, "state": state})
    profile_yaml_cache.clear()


def test_run_times_follow_the_handler_parsing(tmp_path):
    path = _write(tmp_path, [
        _job("iso", "2026-11-12T08:00:00Z"),
        _job("offset", OLD),
        _job("number", 1794470400),
        _job("never", None),
        _job("garbage", "not a date"),
    ])
    rows = precheck._run_times(path)
    assert [(ts, job["id"]) for ts, job in rows] == [(OLD_TS, "iso"), (OLD_TS, "offset"), (OLD_TS, "number")]


@pytest.mark.parametrize("text", [
    "{not json",
    json.dumps([{"id": "bare-list", "last_run_at": NEW}]),
    json.dumps({"jobs": {"keyed": {"last_run_at": NEW}}}),
    json.dumps({"jobs": [{"id": "ok"}, "junk"]}),
    json.dumps({"jobs": [{"id": "odd", "last_run_at": {"nested": 1}}]}),
    json.dumps({"other": []}),
])
def test_unusual_job_files_are_unknown(tmp_path, text):
    path = tmp_path / "jobs.json"
    path.write_text(text, encoding="utf-8")
    assert precheck._run_times(path) is None


def test_missing_job_file_has_no_runs(tmp_path):
    assert precheck._run_times(tmp_path / "absent.json") == ()


def test_nothing_new_is_empty(stores):
    _write(stores.active, [_job("a", OLD, ME)])
    _write(stores.other, [_job("b", OLD, ME)])
    assert precheck.nothing_new(object(), SINCE) is True


def test_no_job_files_at_all_is_empty(stores):
    assert precheck.nothing_new(object(), SINCE) is True


@pytest.mark.parametrize("where", ["active", "other"])
def test_a_new_run_of_the_callers_own_job_goes_to_the_handler(stores, where):
    _write(stores.active, [_job("a", NEW if where == "active" else OLD, ME)])
    _write(stores.other, [_job("b", NEW if where == "other" else OLD, ME)])
    assert precheck.nothing_new(object(), SINCE) is False


@pytest.mark.parametrize("where", ["active", "other"])
def test_a_shared_job_goes_to_the_handler(stores, where):
    shared = _job("s", NEW, "someone@example.test", shared_with=[ME])
    _write(stores.active, [shared] if where == "active" else [])
    _write(stores.other, [shared] if where == "other" else [])
    assert precheck.nothing_new(object(), SINCE) is False


def test_someone_elses_new_run_stays_empty_for_a_plain_user(stores):
    _write(stores.active, [_job("a", NEW, "someone@example.test"), _job("cli", NEW)])
    _write(stores.other, [_job("b", NEW, "someone@example.test")])
    assert precheck.nothing_new(object(), SINCE) is True


def test_admins_and_password_logins_get_every_new_run(stores):
    _write(stores.other, [_job("b", NEW, "someone@example.test")])
    stores.state["admin"] = True
    assert precheck.nothing_new(object(), SINCE) is False
    stores.state["admin"] = False
    stores.state["identity"] = {}  # no email: the handler serves everything
    assert precheck.nothing_new(object(), SINCE) is False


def test_the_active_store_is_not_read_twice_as_another_bot(stores, monkeypatch):
    _write(stores.active, [_job("a", NEW, "someone@example.test")])
    # Scoping the "other" rows would raise if the active home were listed among them.
    seen = []
    real = cron_scope.scope_cron_completions

    def spy(identity, jobs, session_owner=None):
        seen.append([job.get("owner_profile") for job in jobs])
        return real(identity, jobs, session_owner)

    monkeypatch.setattr(cron_scope, "scope_cron_completions", spy)
    assert precheck.nothing_new(object(), SINCE) is True
    assert seen == [[None]]


@pytest.mark.parametrize("since", [0.0, -5.0, float("nan")])
def test_a_poll_without_a_usable_since_goes_to_the_handler(stores, since):
    assert precheck.nothing_new(object(), since) is False


def test_unknown_store_goes_to_the_handler(stores):
    _write(stores.active, [_job("a", OLD, ME)])
    path = _write(stores.other, [])
    path.write_text("[]", encoding="utf-8")
    assert precheck.nothing_new(object(), SINCE) is False


def test_failures_go_to_the_handler(stores, monkeypatch):
    _write(stores.active, [_job("a", NEW, "someone@example.test")])

    def boom(*args, **kwargs):
        raise RuntimeError("no identity")

    monkeypatch.setattr(cron_scope, "_identity_for", boom)
    assert precheck.nothing_new(object(), SINCE) is False
    monkeypatch.setattr(precheck, "_active_jobs_file", boom)
    assert precheck.nothing_new(object(), SINCE) is False


def test_switch_off(stores, monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_CRON_RECENT_PRECHECK", "0")
    assert precheck.nothing_new(object(), SINCE) is False


def test_unchanged_files_are_parsed_once_and_a_write_is_seen(stores, monkeypatch):
    _write(stores.active, [_job("a", OLD, ME)])
    _write(stores.other, [_job("b", OLD, ME)])
    reads = []
    real = precheck._read

    def counting(path):
        reads.append(os.fspath(path))
        return real(path)

    monkeypatch.setattr(precheck, "_read", counting)
    # A file written a moment ago is never kept (its change time cannot be set back).
    monkeypatch.setattr(profile_yaml_cache, "_RACY_NS", -1)
    for _ in range(3):
        assert precheck.nothing_new(object(), SINCE) is True
    assert len(reads) == 2
    _write(stores.other, [_job("b", NEW, ME)], age=5.0)
    assert precheck.nothing_new(object(), SINCE) is False
    assert len(reads) == 3


def test_cached_jobs_are_not_changed_by_scoping(stores):
    _write(stores.other, [_job("b", NEW, "someone@example.test")])
    assert precheck.nothing_new(object(), SINCE) is True
    rows = precheck._load(stores.other / "cron" / "jobs.json")
    assert "owner_profile" not in rows[0][1]


def test_the_handler_answers_empty_without_building_the_job_list(stores, monkeypatch):
    import sys
    import types
    from urllib.parse import urlparse

    import api.routes as routes

    _write(stores.active, [_job("a", OLD, ME)])
    sent = []
    monkeypatch.setattr(routes, "j", lambda handler, payload, *a, **k: sent.append(payload) or payload)
    cron_jobs = types.ModuleType("cron.jobs")

    def list_jobs(include_disabled=False):
        raise AssertionError("the full job list must not be built for an empty poll")

    cron_jobs.list_jobs = list_jobs
    cron_pkg = types.ModuleType("cron")
    cron_pkg.jobs = cron_jobs
    monkeypatch.setitem(sys.modules, "cron", cron_pkg)
    monkeypatch.setitem(sys.modules, "cron.jobs", cron_jobs)
    routes._handle_cron_recent(object(), urlparse(f"/api/crons/recent?since={SINCE}"))
    assert sent == [{"completions": [], "since": SINCE}]
