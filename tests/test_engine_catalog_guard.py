"""The WebUI keeps one shared model catalogue for the own gateway."""
import json
import sys
import threading
import types
from contextlib import contextmanager

import pytest

GATEWAY = "http://127.0.0.1:20128/v1"


@pytest.fixture
def engine(monkeypatch, tmp_path):
    """Stand-ins for the engine's metadata modules, recording every real fetch."""
    state = types.SimpleNamespace(original_calls=[], uncached_calls=[], stream_calls=[], result={"m-a": {"context_length": 1000}},
                                  uncached_error=None, gate=None)

    def original_fetch(base_url, api_key="", force_refresh=False, *, cached_only=False, native_protocol_probes=True):
        state.original_calls.append((base_url, api_key, force_refresh, cached_only))
        return {"from-original": {"context_length": 1}}

    @contextmanager
    def original_stream(url, *, headers=None, params=None, timeout=10.0, verify=None):
        state.stream_calls.append((url, timeout))
        yield None

    def uncached(normalized, api_key, *, native_protocol_probes=True):
        state.uncached_calls.append((normalized, api_key, native_protocol_probes))
        with http.stream(normalized + "/models", headers={}, timeout=(5, 10), verify=None):
            pass
        with http.stream(normalized + "/props", headers={}, timeout=5, verify=None):
            pass
        if state.gate is not None:
            state.gate.wait(5)
        if state.uncached_error is not None:
            raise state.uncached_error
        return state.result

    agent = types.ModuleType("agent")
    agent.__path__ = []
    metadata = types.ModuleType("agent.model_metadata")
    metadata.fetch_endpoint_model_metadata = original_fetch
    endpoint = types.ModuleType("agent.model_metadata_endpoint")
    endpoint._fetch_endpoint_model_metadata_uncached = uncached
    http = types.ModuleType("agent.model_metadata_http")
    http.stream = original_stream
    pricing = types.ModuleType("agent.usage_pricing")
    pricing.fetch_endpoint_model_metadata = original_fetch
    agent.model_metadata, agent.model_metadata_endpoint, agent.model_metadata_http, agent.usage_pricing = metadata, endpoint, http, pricing
    for name, module in (("agent", agent), ("agent.model_metadata", metadata), ("agent.model_metadata_endpoint", endpoint),
                         ("agent.model_metadata_http", http), ("agent.usage_pricing", pricing)):
        monkeypatch.setitem(sys.modules, name, module)
    from api import engine_catalog_guard as guard

    monkeypatch.delenv("HERMES_WEBUI_CATALOG_GUARD", raising=False)
    monkeypatch.delenv("HERMES_WEBUI_CATALOG_GUARD_PORTS", raising=False)
    monkeypatch.setattr(guard, "_snapshot_path_override", str(tmp_path / "snapshot.json"))
    guard.reset_for_tests()
    assert guard.install() is True
    state.guard, state.metadata, state.pricing, state.http, state.original = guard, metadata, pricing, http, original_fetch
    state.snapshot = tmp_path / "snapshot.json"
    yield state
    guard.reset_for_tests()


def _wait_for(predicate, seconds=5.0):
    import time

    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def test_install_replaces_the_engine_function_and_the_by_name_import(engine):
    wrapped = engine.metadata.fetch_endpoint_model_metadata
    assert wrapped is not engine.original
    assert wrapped.__wrapped__ is engine.original
    assert engine.pricing.fetch_endpoint_model_metadata is wrapped
    assert engine.guard.install() is True  # idempotent
    assert engine.metadata.fetch_endpoint_model_metadata is wrapped


def test_one_fetch_serves_every_profile_and_credential(engine):
    fetch = engine.metadata.fetch_endpoint_model_metadata
    first = fetch(GATEWAY, api_key="key-one")
    assert first == {"m-a": {"context_length": 1000}}
    for key in ("key-one", "key-two", ""):
        for url in (GATEWAY, GATEWAY + "/", "http://localhost:20128/v1", "http://127.0.0.1:20128"):
            assert fetch(url, api_key=key, native_protocol_probes=False) is first
    assert len(engine.uncached_calls) == 1
    assert engine.uncached_calls[0] == (GATEWAY, "key-one", False)
    assert engine.original_calls == []


def test_other_endpoints_reach_the_engine_untouched(engine):
    fetch = engine.metadata.fetch_endpoint_model_metadata
    for url in ("https://api.example.com/v1", "http://127.0.0.1:11434/v1", "http://10.0.0.5:20128/v1", "", None):
        assert fetch(url, "k", cached_only=True) == {"from-original": {"context_length": 1}}
    assert len(engine.original_calls) == 5
    assert engine.original_calls[0] == ("https://api.example.com/v1", "k", False, True)
    assert engine.uncached_calls == []


def test_refresh_reads_models_with_the_long_timeout_only(engine):
    engine.metadata.fetch_endpoint_model_metadata(GATEWAY, "k")
    assert engine.stream_calls == [(GATEWAY + "/models", (5.0, 30.0)), (GATEWAY + "/props", 5)]
    # Outside the guard's refresh the engine's own timeout is left alone.
    with engine.http.stream(GATEWAY + "/models", timeout=(5, 10)):
        pass
    assert engine.stream_calls[-1] == (GATEWAY + "/models", (5, 10))


def test_cached_only_never_fetches(engine):
    fetch = engine.metadata.fetch_endpoint_model_metadata
    assert fetch(GATEWAY, "k", cached_only=True) == {}
    assert engine.uncached_calls == []
    fetch(GATEWAY, "k")
    assert fetch(GATEWAY, "k", cached_only=True) == {"m-a": {"context_length": 1000}}
    assert len(engine.uncached_calls) == 1


def test_stale_snapshot_is_served_while_one_background_refresh_runs(engine, monkeypatch):
    fetch = engine.metadata.fetch_endpoint_model_metadata
    first = fetch(GATEWAY, "k")
    slot = engine.guard._slots[20128]
    slot.fetched_at -= 4000
    slot.attempt_at -= 4000
    engine.result = {"m-b": {"context_length": 2000}}
    engine.gate = threading.Event()
    for _ in range(5):
        assert fetch(GATEWAY, "k") is first  # served at once, refresh still running
    assert _wait_for(lambda: len(engine.uncached_calls) == 2)
    engine.gate.set()
    assert _wait_for(lambda: slot.flight is None)
    assert len(engine.uncached_calls) == 2
    # Union for a day: another credential may see another subset.
    assert fetch(GATEWAY, "k") == {"m-a": {"context_length": 1000}, "m-b": {"context_length": 2000}}


def test_failed_refresh_keeps_the_snapshot_and_waits_for_the_next_window(engine):
    fetch = engine.metadata.fetch_endpoint_model_metadata
    first = fetch(GATEWAY, "k")
    slot = engine.guard._slots[20128]
    slot.fetched_at -= 4000
    slot.attempt_at -= 4000
    engine.result = {}
    assert fetch(GATEWAY, "k") is first
    assert _wait_for(lambda: len(engine.uncached_calls) == 2 and slot.flight is None)
    engine.uncached_error = RuntimeError("down")
    for _ in range(5):
        assert fetch(GATEWAY, "k") is first
    assert len(engine.uncached_calls) == 2  # no retry inside the attempt window


def test_cold_failure_is_not_retried_at_once(engine):
    fetch = engine.metadata.fetch_endpoint_model_metadata
    engine.uncached_error = RuntimeError("down")
    assert fetch(GATEWAY, "k") == {}
    assert fetch(GATEWAY, "k") == {}
    assert len(engine.uncached_calls) == 1
    engine.guard._slots[20128].attempt_at -= 400
    engine.uncached_error = None
    assert fetch(GATEWAY, "k") == {"m-a": {"context_length": 1000}}
    assert len(engine.uncached_calls) == 2


def test_cold_callers_share_one_fetch(engine):
    fetch = engine.metadata.fetch_endpoint_model_metadata
    engine.gate = threading.Event()
    results = []
    threads = [threading.Thread(target=lambda: results.append(fetch(GATEWAY, "k"))) for _ in range(6)]
    for thread in threads:
        thread.start()
    assert _wait_for(lambda: len(engine.uncached_calls) == 1)
    engine.gate.set()
    for thread in threads:
        thread.join(5)
    assert len(engine.uncached_calls) == 1
    assert results == [{"m-a": {"context_length": 1000}}] * 6


def test_force_refresh_is_rate_limited(engine):
    fetch = engine.metadata.fetch_endpoint_model_metadata
    first = fetch(GATEWAY, "k")
    assert fetch(GATEWAY, "k", True) is first
    assert len(engine.uncached_calls) == 1
    engine.guard._slots[20128].attempt_at -= 100
    engine.result = {"m-a": {"context_length": 5}}
    assert fetch(GATEWAY, "k", force_refresh=True) == {"m-a": {"context_length": 5}}
    assert len(engine.uncached_calls) == 2


def test_snapshot_survives_a_restart_without_credentials(engine):
    fetch = engine.metadata.fetch_endpoint_model_metadata
    fetch(GATEWAY, "very-private-key")
    stored = engine.snapshot.read_text(encoding="utf-8")
    assert "very-private-key" not in stored
    assert json.loads(stored)["endpoints"]["20128"]["models"] == {"m-a": {"context_length": 1000}}
    engine.guard.reset_for_tests()  # a new process
    engine.uncached_error = RuntimeError("must not be called")
    assert fetch(GATEWAY, "another") == {"m-a": {"context_length": 1000}}
    assert len(engine.uncached_calls) == 1


def test_unreadable_snapshot_file_starts_empty(engine):
    engine.snapshot.write_text("{not json", encoding="utf-8")
    engine.guard.reset_for_tests()
    assert engine.metadata.fetch_endpoint_model_metadata(GATEWAY, "k") == {"m-a": {"context_length": 1000}}


def test_kill_switch_reaches_the_engine(engine, monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_CATALOG_GUARD", "0")
    assert engine.metadata.fetch_endpoint_model_metadata(GATEWAY, "k") == {"from-original": {"context_length": 1}}
    assert engine.uncached_calls == []


def test_unknown_engine_layout_fails_open(monkeypatch):
    agent = types.ModuleType("agent")
    agent.__path__ = []
    metadata = types.ModuleType("agent.model_metadata")
    endpoint = types.ModuleType("agent.model_metadata_endpoint")
    http = types.ModuleType("agent.model_metadata_http")
    for name, module in (("agent", agent), ("agent.model_metadata", metadata), ("agent.model_metadata_endpoint", endpoint),
                         ("agent.model_metadata_http", http)):
        monkeypatch.setitem(sys.modules, name, module)
    from api import engine_catalog_guard as guard

    assert guard.install() is False
    metadata.fetch_endpoint_model_metadata = lambda *a, **k: {}
    assert guard.install() is False  # no uncached fetch to call
    assert not getattr(metadata.fetch_endpoint_model_metadata, guard._MARK, False)
