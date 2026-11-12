"""A chat list poll does not wait for a rebuild when only another process wrote to state.db."""
import threading

import pytest

import api.routes as routes
from api import route_session_list_cache as slc

BASE = ((10, 100), (11, 110), (12, 120), (13, 130), (14, 140), "fp-1", 3)


def _stamp(**changes):
    parts = list(BASE)
    for position, value in changes.items():
        parts[int(position[1:])] = value
    return tuple(parts)


def _payload(marker):
    return {"sessions": [{"session_id": marker}], "cli_count": 0, "all_profiles": False,
            "active_profile": None, "other_profile_count": 0}


class _Stages:
    def __init__(self):
        self.stages = []

    def stage(self, name):
        self.stages.append(str(name))


@pytest.fixture
def cache(monkeypatch):
    routes._session_list_cache_clear()
    with routes._SESSIONS_CACHE_LOCK:
        routes._SESSIONS_CACHE_INFLIGHT.clear()
    state = {"stamp": BASE}
    monkeypatch.setattr(routes, "_session_list_cache_source_stamp", lambda _key: state["stamp"])
    monkeypatch.delenv("HERMES_WEBUI_SESSION_LIST_EXTERNAL_STALE_MAX_SECONDS", raising=False)
    key = routes._session_list_cache_key(
        active_profile="default", all_profiles=False, show_cli_sessions=False,
        show_previous_messaging_sessions=False, show_cron_sessions=False,
    )
    routes._session_list_cache_set(key, _payload("old"))
    state["key"] = key
    yield state
    routes._session_list_cache_clear()
    with routes._SESSIONS_CACHE_LOCK:
        routes._SESSIONS_CACHE_INFLIGHT.clear()


def _poll(state, marker="new"):
    started, release, diag = threading.Event(), threading.Event(), _Stages()

    def builder():
        started.set()
        release.wait(5)
        return _payload(marker)

    result = {}
    worker = threading.Thread(target=lambda: result.setdefault(
        "payload", routes._get_cached_session_list_payload(key=state["key"], builder=builder, diag=diag)))
    worker.start()
    worker.join(1.0)
    returned_before_build_finished = not worker.is_alive()
    release.set()
    worker.join(5)
    return result["payload"], returned_before_build_finished, started, diag


@pytest.mark.parametrize("changes", [
    {"p0": (10, 999)}, {"p1": (99, 110)}, {"p2": (12, 121)}, {"p5": "fp-2"},
    {"p0": (20, 100), "p1": (21, 110), "p5": "fp-9"},
])
def test_external_write_serves_the_previous_list_and_rebuilds_in_the_background(cache, changes):
    cache["stamp"] = _stamp(**changes)
    assert slc._session_list_cache_stale_reason(cache["key"]) == "source"
    payload, immediate, started, diag = _poll(cache)
    assert payload == _payload("old")
    assert immediate, "the poll must not wait for the rebuild"
    assert started.wait(1.0), "a background rebuild must start"
    assert "session_list_cache_stale_background_rebuild" in diag.stages
    for _ in range(100):
        cached, fresh = routes._session_list_cache_get(cache["key"], allow_stale=True)
        if cached == _payload("new"):
            break
        threading.Event().wait(0.02)
    assert cached == _payload("new") and fresh is True


@pytest.mark.parametrize("changes", [
    {"p3": (13, 131)},                      # session index: this server's own write
    {"p4": (15, 140)},                      # settings file
    {"p6": 4},                              # settings write version
    {"p0": (10, 999), "p4": (15, 140)},     # external and settings together
    {"p0": ("streaming", ("s1",)), "p1": ("streaming", ("s1",)), "p2": ("streaming", ("s1",)),
     "p3": ("streaming", ("s1",)), "p5": ("streaming", ("s1",))},  # a stream started
])
def test_own_changes_and_stream_transitions_still_wait_for_the_rebuild(cache, changes):
    cache["stamp"] = _stamp(**changes)
    payload, immediate, _started, diag = _poll(cache)
    assert payload == _payload("new")
    assert not immediate
    assert "session_list_cache_rebuild_owner" in diag.stages


def test_entry_built_during_a_stream_is_strict_when_the_stream_ends(cache):
    marker = ("streaming", ("s1",))
    cache["stamp"] = (marker, marker, marker, marker, (14, 140), marker, 3)
    routes._session_list_cache_set(cache["key"], _payload("old"))
    cache["stamp"] = BASE
    payload, immediate, _started, _diag = _poll(cache)
    assert payload == _payload("new") and not immediate


def test_an_old_entry_is_not_served(cache):
    with routes._SESSIONS_CACHE_LOCK:
        ts, stamp, frozen = routes._SESSIONS_CACHE[cache["key"]]
        routes._SESSIONS_CACHE[cache["key"]] = (ts - 61.0, stamp, frozen)
    cache["stamp"] = _stamp(p0=(10, 999))
    payload, immediate, _started, _diag = _poll(cache)
    assert payload == _payload("new") and not immediate


def test_zero_switches_the_behaviour_off(cache, monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_SESSION_LIST_EXTERNAL_STALE_MAX_SECONDS", "0")
    cache["stamp"] = _stamp(p0=(10, 999))
    payload, immediate, _started, _diag = _poll(cache)
    assert payload == _payload("new") and not immediate


def test_unknown_stamp_shape_is_strict(cache):
    cache["stamp"] = ("stable",)
    routes._session_list_cache_set(cache["key"], _payload("old"))
    cache["stamp"] = ("changed",)
    assert slc._session_list_cache_stale_is_external(cache["key"]) is False
    payload, immediate, _started, _diag = _poll(cache)
    assert payload == _payload("new") and not immediate


def test_real_stamp_has_the_expected_shape(tmp_path, monkeypatch):
    """The positions used above must match the stamp the server really builds."""
    state_db = tmp_path / "state.db"
    state_db.write_text("db", encoding="utf-8")
    wal = tmp_path / "state.db-wal"
    wal.write_text("wal-1", encoding="utf-8")
    gateway = tmp_path / "gateway-sessions.json"
    gateway.write_text("{}", encoding="utf-8")
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    index = session_dir / "_index.json"
    index.write_text("{}", encoding="utf-8")
    settings = tmp_path / "settings.json"
    settings.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(routes, "_active_state_db_path", lambda: str(state_db))
    monkeypatch.setattr(routes, "_gateway_session_metadata_path", lambda: gateway)
    monkeypatch.setattr(routes, "SESSION_DIR", session_dir)
    monkeypatch.setattr(routes, "SETTINGS_FILE", settings)
    monkeypatch.setattr(routes, "_active_stream_ids", lambda: set())
    key = routes._session_list_cache_key(
        active_profile="default", all_profiles=False, show_cli_sessions=True,
        show_previous_messaging_sessions=False, show_cron_sessions=False,
    )

    def moved(write):
        before = routes._session_list_cache_source_stamp(key)
        write()
        after = routes._session_list_cache_source_stamp(key)
        assert len(before) == len(after) == 7
        return {position for position in range(7) if before[position] != after[position]}

    assert moved(lambda: wal.write_text("wal-2-longer", encoding="utf-8")) <= {1, 5}
    assert moved(lambda: state_db.write_text("db-longer", encoding="utf-8")) <= {0, 5}
    assert moved(lambda: gateway.write_text('{"a": 1}', encoding="utf-8")) == {2}
    assert moved(lambda: index.write_text('{"a": 1}', encoding="utf-8")) == {3}
    assert moved(lambda: settings.write_text('{"a": 1}', encoding="utf-8")) == {4}
    routes._session_list_cache_clear()
    routes._session_list_cache_set(key, _payload("old"))
    wal.write_text("wal-3-even-longer", encoding="utf-8")
    assert slc._session_list_cache_stale_is_external(key) is True
    routes._session_list_cache_set(key, _payload("old"))
    index.write_text('{"a": 2, "b": 3}', encoding="utf-8")
    assert slc._session_list_cache_stale_is_external(key) is False
    monkeypatch.setattr(routes, "_active_stream_ids", lambda: {"s1"})
    assert slc._session_list_cache_stale_is_external(key) is False
