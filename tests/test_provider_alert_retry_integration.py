"""Real provider-error and capacity-store integration; external delivery is fake."""

from collections import OrderedDict

import pytest


@pytest.fixture
def incident_store(tmp_path, monkeypatch):
    from api import capacity_alerts, config, streaming

    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(capacity_alerts, "effective_config", lambda: {
        **capacity_alerts.DEFAULT_CONFIG,
        "capacity_alert_cooldown_seconds": 30,
    })
    monkeypatch.setattr(capacity_alerts, "_DISPATCH_STATES", OrderedDict())
    clock = [10000.0]
    monkeypatch.setattr(capacity_alerts.time, "time", lambda: clock[0])
    return streaming, capacity_alerts, clock


def report_error(streaming, diagnostic):
    """Use the same classification/report/payload chain as the chat exits."""
    classified = streaming._classify_provider_error(diagnostic)
    streaming._report_capacity_incident(
        classified, provider="synthetic-provider", model="synthetic-model",
        detail=diagnostic, source="chat",
    )
    payload = streaming._provider_error_payload(
        diagnostic, classified["type"], classified["hint"],
    )
    return classified, payload


def test_rate_limit_retry_preserves_truthful_copy_and_one_stored_incident(
    incident_store, monkeypatch,
):
    streaming, capacity_alerts, clock = incident_store
    diagnostic = "HTTP 429 rate limit exceeded; request_id=fixture-429"
    deliveries = []

    def deliver(event):
        deliveries.append((clock[0], dict(event)))
        return (False, "synthetic transport timeout") if len(deliveries) == 1 else (True, "")

    monkeypatch.setattr(capacity_alerts, "_dispatch_external", deliver)
    first, first_payload = report_error(streaming, diagnostic)
    first_event = capacity_alerts.list_events()[0]
    event_id = first_event["id"]
    assert first["type"] == "rate_limit" and first["category"] == "capacity"
    assert first["admin_notified"] is True, "the initial in-app notice was persisted"
    assert first_event["dispatched"] is False, "an in-app notice is not external delivery"
    assert first_event["dispatch_error"] == "synthetic transport timeout"
    assert first_event["dispatch_attempt_ts"] == 10000

    repeats = []
    for elapsed in (10, 20, 29):
        clock[0] = 10000 + elapsed
        classified, payload = report_error(streaming, diagnostic)
        repeats.append(payload)
        assert classified["admin_notified"] is False, "a count update is not a new notice"
        assert "administrator has been notified" not in payload["hint"]
    assert len(deliveries) == 1
    before_retry = capacity_alerts.list_events()
    assert len(before_retry) == 1 and before_retry[0]["id"] == event_id
    assert before_retry[0]["count"] == 4 and before_retry[0]["last_ts"] == 10029

    # Ongoing reports keep the incident active; they must not postpone transport retry.
    clock[0] = 10030
    retried, retry_payload = report_error(streaming, diagnostic)
    assert retried["admin_notified"] is True
    assert "administrator has been notified" in retry_payload["hint"]
    after_retry = capacity_alerts.list_events()
    assert len(after_retry) == 1
    assert after_retry[0]["id"] == event_id and after_retry[0]["count"] == 5
    assert after_retry[0]["dispatched"] is True and after_retry[0]["dispatch_error"] == ""
    assert after_retry[0]["dispatch_attempt_ts"] == 10030
    assert [(when, event["id"]) for when, event in deliveries] == [
        (10000, event_id), (10030, event_id),
    ]
    assert all(event["detail"] == diagnostic for _, event in deliveries)
    assert after_retry[0]["provider"] == "synthetic-provider"
    assert after_retry[0]["model"] == "synthetic-model"
    assert after_retry[0]["source"] == "chat"

    for elapsed in (40, 50, 60):
        clock[0] = 10000 + elapsed
        classified, payload = report_error(streaming, diagnostic)
        repeats.append(payload)
        assert classified["admin_notified"] is False
    assert len(deliveries) == 2, "confirmed delivery stays deduplicated beyond another retry interval"
    assert capacity_alerts.list_events()[0]["count"] == 8

    # The reporting outcome must survive the real formatter without promoting raw diagnostics.
    for payload in [first_payload, *repeats, retry_payload]:
        assert payload["type"] == "rate_limit"
        assert payload["message"] == "The service is receiving too many requests right now."
        assert payload["details"] == diagnostic
        assert "429" not in payload["message"] + payload["hint"]
    assert "administrator has been notified" in first_payload["hint"]


def test_neutral_unavailability_does_not_alert_but_explicit_overload_does(
    incident_store, monkeypatch,
):
    streaming, capacity_alerts, _clock = incident_store
    deliveries = []
    monkeypatch.setattr(
        capacity_alerts, "_dispatch_external",
        lambda event: (deliveries.append(dict(event)) or True, ""),
    )
    neutral_diagnostic = "HTTP 503 Service Unavailable; request_id=fixture-neutral"
    neutral, neutral_payload = report_error(streaming, neutral_diagnostic)
    assert capacity_alerts.list_events() == []
    assert not capacity_alerts._store_path().exists(), "a neutral 503 must not create a capacity record"
    assert deliveries == []
    assert not neutral.get("admin_notified", False)
    assert "administrator has been notified" not in neutral_payload.get("hint", "")

    overload_diagnostic = "HTTP 503 overloaded_error: upstream is overloaded; request_id=fixture-overload"
    overload, overload_payload = report_error(streaming, overload_diagnostic)
    events = capacity_alerts.list_events()
    assert len(events) == 1 and len(deliveries) == 1
    assert events[0]["id"] == deliveries[0]["id"]
    assert events[0]["kind"] == "overloaded" and events[0]["count"] == 1
    assert events[0]["detail"] == overload_diagnostic
    assert events[0]["dispatched"] is True
    assert overload["admin_notified"] is True
    assert overload["category"] == "capacity"
    assert "administrator has been notified" in overload_payload["hint"]

    assert neutral["type"] == neutral_payload["type"] == "service_unavailable"
    assert neutral.get("category") != "capacity"
    assert neutral_payload["message"] == "The service is temporarily unavailable."
    assert neutral_payload["details"] == neutral_diagnostic
    assert "capacity" not in neutral_payload["message"] + neutral_payload["hint"]
    assert overload["type"] == overload_payload["type"] == "overloaded"
    assert overload_payload["message"] == "The service is very busy right now."
    assert overload_payload["details"] == overload_diagnostic
    assert "503" not in overload_payload["message"] + overload_payload["hint"]
