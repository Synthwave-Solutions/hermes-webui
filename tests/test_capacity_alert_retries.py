"""Capacity transport retries use their own clock; no real delivery is performed."""
from concurrent.futures import ThreadPoolExecutor
import json
import threading

import pytest


@pytest.fixture
def incident(tmp_path, monkeypatch):
    from api import config, capacity_alerts as ca

    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(ca, "effective_config", lambda: {
        **ca.DEFAULT_CONFIG, "capacity_alert_cooldown_seconds": 30,
    })
    clock = [10000.0]
    monkeypatch.setattr(ca.time, "time", lambda: clock[0])
    if hasattr(ca, "_DISPATCH_STATES"):
        monkeypatch.setattr(ca, "_DISPATCH_STATES", ca._DISPATCH_STATES.copy())
        ca._DISPATCH_STATES.clear()
    return ca, clock


def emit(ca, provider="fixture"):
    return ca.record_capacity_event("quota_exhausted", provider=provider)


def test_repeated_incidents_retry_from_attempt_time_not_last_incident(incident, monkeypatch):
    ca, clock = incident
    calls = []

    def deliver(event):
        calls.append((clock[0], event["id"]))
        return (len(calls) > 1, "" if len(calls) > 1 else "429 retry later")

    monkeypatch.setattr(ca, "_dispatch_external", deliver)
    first = emit(ca)
    for elapsed in (10, 20, 29):
        clock[0] = 10000 + elapsed
        repeat = emit(ca)
        assert repeat["deduplicated"] and not repeat["notified"]
    clock[0] = 10030
    retry = emit(ca)
    assert len(calls) == 2
    assert retry == {"notified": True, "deduplicated": True,
                     "event_id": first["event_id"], "recorded": True,
                     "dispatched": True}
    event = ca.list_events()[0]
    assert event["count"] == 5 and event["last_ts"] == 10030
    assert event["dispatch_attempt_ts"] == 10030
    assert event["dispatched"] is True and event["dispatch_error"] == ""
    for elapsed in range(40, 181, 10):
        clock[0] = 10000 + elapsed
        assert emit(ca)["dispatched"] is False
    assert len(calls) == 2, "confirmed deliveries remain deduplicated"


@pytest.mark.parametrize("error", ["429 retry later", "delivery timeout", "unconfirmed"])
def test_failed_retries_are_bounded_and_are_not_new_notifications(incident, monkeypatch, error):
    ca, clock = incident
    calls = []
    monkeypatch.setattr(ca, "_dispatch_external", lambda event: (calls.append(clock[0]) or False, error))
    emit(ca)
    for elapsed in range(1, 91):
        clock[0] = 10000 + elapsed
        result = emit(ca)
        assert result["recorded"] is True
        assert result["notified"] is False and result["dispatched"] is False
    assert calls == [10000, 10030, 10060, 10090]
    assert ca.list_events()[0]["count"] == 91


def test_failed_storage_does_not_create_a_transport_storm(incident, monkeypatch):
    ca, clock = incident
    calls = []
    monkeypatch.setattr(ca, "_save", lambda *args, **kwargs: False)
    monkeypatch.setattr(ca, "_dispatch_external", lambda event: (calls.append(clock[0]) or False, "429"))
    for elapsed in range(91):
        clock[0] = 10000 + elapsed
        outcome = emit(ca)
        assert outcome["recorded"] is False and outcome["notified"] is False
    assert calls == [10000, 10030, 10060, 10090]


def test_success_survives_failed_dispatch_status_save(incident, monkeypatch):
    ca, clock = incident
    original_save = ca._save
    writes = 0
    calls = []

    def save(*args, **kwargs):
        nonlocal writes
        writes += 1
        return False if writes == 2 else original_save(*args, **kwargs)

    monkeypatch.setattr(ca, "_save", save)
    monkeypatch.setattr(ca, "_dispatch_external", lambda event: (calls.append(clock[0]) or True, ""))
    assert emit(ca)["dispatched"] is True
    for elapsed in range(10, 181, 10):
        clock[0] = 10000 + elapsed
        assert emit(ca)["dispatched"] is False
    assert calls == [10000]
    assert ca.list_events()[0]["dispatched"] is True


@pytest.mark.parametrize("storage_failure", [False, True])
def test_retry_claim_is_single_flight_and_transport_does_not_hold_store_lock(incident, monkeypatch, storage_failure):
    ca, clock = incident
    calls = []
    started, release = threading.Event(), threading.Event()

    def deliver(event):
        calls.append(clock[0])
        if len(calls) == 1:
            return False, "temporary failure"
        assert not ca._LOCK.locked()
        started.set()
        assert release.wait(5)
        return False, "still unavailable"

    monkeypatch.setattr(ca, "_dispatch_external", deliver)
    if storage_failure:
        monkeypatch.setattr(ca, "_save", lambda *args, **kwargs: False)
    first = emit(ca)
    clock[0] = 10020
    emit(ca)
    clock[0] = 10030
    with ThreadPoolExecutor(max_workers=8) as pool:
        leader = pool.submit(emit, ca)
        try:
            assert started.wait(2), "failed delivery must become eligible for retry"
            # Even another retry interval cannot overlap an unfinished send.
            clock[0] = 10060
            followers = [pool.submit(emit, ca) for _ in range(20)]
            results = [future.result(timeout=2) for future in followers]
            assert all(not row["dispatched"] for row in results)
            assert len(calls) == 2
        finally:
            release.set()
        assert leader.result(timeout=2)["dispatched"] is False
    events = ca.list_events()
    if storage_failure:
        assert events == []
    else:
        assert any(event["id"] == first["event_id"] for event in events)


def test_persisted_attempt_survives_process_state_reset(incident, monkeypatch):
    ca, clock = incident
    calls = []
    monkeypatch.setattr(ca, "_dispatch_external", lambda event: (calls.append(clock[0]) or False, "timeout"))
    emit(ca)
    assert ca.list_events()[0]["dispatch_attempt_ts"] == 10000
    if hasattr(ca, "_DISPATCH_STATES"):
        ca._DISPATCH_STATES.clear()
    for elapsed in (10, 20, 29, 30):
        clock[0] = 10000 + elapsed
        emit(ca)
    assert calls == [10000, 10030]


def test_unexpected_store_exception_does_not_leave_an_inflight_claim(incident, monkeypatch):
    ca, clock = incident
    save = ca._save
    calls = []

    def broken_store(*args, **kwargs):
        raise UnicodeEncodeError("utf-8", "\ud800", 0, 1, "synthetic diagnostic")

    monkeypatch.setattr(ca, "_save", broken_store)
    monkeypatch.setattr(ca, "_dispatch_external", lambda event: (calls.append(clock[0]) or False, "timeout"))
    assert emit(ca)["notified"] is False
    assert calls == []
    assert all(not state["in_flight"] for state in ca._DISPATCH_STATES.values())
    monkeypatch.setattr(ca, "_save", save)
    clock[0] = 10030
    emit(ca)
    assert calls == [10030]


def test_recent_attempts_are_not_evicted_under_failed_storage_pressure(incident, monkeypatch):
    ca, clock = incident
    monkeypatch.setattr(ca, "_MAX_EVENTS", 2)
    monkeypatch.setattr(ca, "_save", lambda *args, **kwargs: False)
    calls = []
    monkeypatch.setattr(ca, "_dispatch_external", lambda event: (calls.append(event["provider"]) or False, "429"))
    for provider in ["a", "b", "c", "a", "d", "b"]:
        emit(ca, provider)
        assert len(ca._DISPATCH_STATES) <= 2
    assert calls == ["a", "b"]
    clock[0] = 10030
    emit(ca, "c")
    assert calls == ["a", "b", "c"]
    assert len(ca._DISPATCH_STATES) == 2


def test_other_profiles_shorter_cooldown_cannot_evict_a_protected_attempt(incident, monkeypatch, tmp_path):
    from api import config
    ca, clock = incident
    current_cooldown = [900]
    monkeypatch.setattr(ca, "_MAX_EVENTS", 1)
    monkeypatch.setattr(ca, "_save", lambda *args, **kwargs: False)
    monkeypatch.setattr(ca, "effective_config", lambda: {
        **ca.DEFAULT_CONFIG, "capacity_alert_cooldown_seconds": current_cooldown[0],
    })
    calls = []
    monkeypatch.setattr(ca, "_dispatch_external", lambda event: (calls.append(event["provider"]) or False, "429"))
    emit(ca, "long-cooldown")
    current_cooldown[0] = 30
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "another-profile")
    clock[0] = 10031
    emit(ca, "short-cooldown")
    assert calls == ["long-cooldown"]
    assert next(iter(ca._DISPATCH_STATES.values()))["cooldown"] == 900
    clock[0] = 10900
    emit(ca, "short-cooldown")
    assert calls == ["long-cooldown", "short-cooldown"]


def test_same_scope_configuration_change_updates_its_retention_interval(incident, monkeypatch):
    ca, clock = incident
    monkeypatch.setattr(ca, "_dispatch_external", lambda event: (False, "429"))
    emit(ca)
    monkeypatch.setattr(ca, "effective_config", lambda: {
        **ca.DEFAULT_CONFIG, "capacity_alert_cooldown_seconds": 900,
    })
    clock[0] = 10001
    emit(ca)
    assert next(iter(ca._DISPATCH_STATES.values()))["cooldown"] == 900


@pytest.mark.parametrize("success", [False, True])
def test_storage_failure_retry_state_is_scoped_to_current_profile_store(incident, monkeypatch, tmp_path, success):
    from api import config
    ca, clock = incident
    monkeypatch.setattr(ca, "_save", lambda *args, **kwargs: False)
    calls = []
    monkeypatch.setattr(ca, "_dispatch_external", lambda event: (calls.append(event["provider"]) or success, "" if success else "429"))
    emit(ca)
    emit(ca)
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "another-profile")
    emit(ca)
    emit(ca)
    assert calls == ["fixture", "fixture"]
    assert len(ca._DISPATCH_STATES) == 2


def test_completion_updates_captured_store_even_if_current_scope_changes(incident, monkeypatch, tmp_path):
    from api import config
    ca, clock = incident
    captured_path = ca._store_path()

    def deliver(event):
        monkeypatch.setattr(config, "STATE_DIR", tmp_path / "another-profile")
        return True, ""

    monkeypatch.setattr(ca, "_dispatch_external", deliver)
    assert emit(ca)["dispatched"] is True
    assert ca.list_events() == []
    assert json.loads(captured_path.read_text())["events"][0]["dispatched"] is True


def test_transport_exception_releases_claim_and_remains_retryable(incident, monkeypatch):
    ca, clock = incident
    calls = []

    def deliver(event):
        calls.append(clock[0])
        raise RuntimeError("synthetic transport exception")

    monkeypatch.setattr(ca, "_dispatch_external", deliver)
    emit(ca)
    clock[0] = 10020
    assert emit(ca)["notified"] is False
    clock[0] = 10030
    result = emit(ca)
    assert result["recorded"] is True and result["notified"] is False
    assert calls == [10000, 10030]
    assert all(not state["in_flight"] for state in ca._DISPATCH_STATES.values())


def test_legacy_failed_event_retries_from_first_attempt_not_recent_incident(incident, monkeypatch):
    ca, clock = incident
    ca._store_path().write_text(json.dumps({"events": [{
        "id": "legacy", "key": "quota_exhausted|fixture", "kind": "quota_exhausted",
        "provider": "fixture", "first_ts": 9900, "last_ts": 9999,
        "count": 8, "dispatched": False, "dispatch_error": "timeout",
    }]}))
    calls = []
    monkeypatch.setattr(ca, "_dispatch_external", lambda event: (calls.append(event["id"]) or True, ""))
    result = emit(ca)
    assert calls == ["legacy"]
    assert result["deduplicated"] and result["dispatched"] and result["notified"]


def test_quiet_interval_starts_a_new_incident_after_confirmed_delivery(incident, monkeypatch):
    ca, clock = incident
    calls = []
    monkeypatch.setattr(ca, "_dispatch_external", lambda event: (calls.append(event["id"]) or True, ""))
    first = emit(ca)
    clock[0] = 10029
    emit(ca)
    clock[0] = 10059
    second = emit(ca)
    assert second["dispatched"] and not second["deduplicated"]
    assert calls == [first["event_id"], second["event_id"]]
    assert first["event_id"] != second["event_id"]
