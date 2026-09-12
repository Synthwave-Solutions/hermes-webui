"""Provider copy must not change error identity, access decisions, or diagnostics."""

import pytest

from api import streaming


@pytest.mark.parametrize("failure,expected_type", [
    ({"error": {"status_code": 401, "message": "Insufficient Balance"}}, "quota_exhausted"),
    ({"error": {"status_code": 401, "message": "Invalid account"}}, "auth_mismatch"),
    ({"error": {"status_code": 401}}, "auth_mismatch"),
    ({"error": {"status_code": 402, "message": "insufficient credits"}}, "quota_exhausted"),
])
def test_balance_semantics_take_precedence_over_auth_status(failure, expected_type):
    classified = streaming._classify_provider_error(failure)
    assert classified["type"] == expected_type
    payload = streaming._provider_error_payload(str(failure), expected_type, classified["hint"])
    assert payload["type"] == expected_type
    assert payload["details"] == str(failure)
    assert "status_code" not in payload["message"]


@pytest.mark.parametrize("failure,expected_type", [
    ({"error": {"status_code": 503}}, "service_unavailable"),
    ("Error code: 503 - Service Unavailable", "service_unavailable"),
    ("503 Service Unavailable", "service_unavailable"),
    ("ServiceUnavailableError: upstream request failed", "service_unavailable"),
    ({"error": {"type": "overloaded_error"}}, "overloaded"),
    ("The upstream is overloaded", "overloaded"),
    ({"error": {"status_code": 500}}, "error"),
    ("HTTP 500 Internal Server Error", "error"),
    ("Connection reset", "error"),
    ("Unexpected value 503 in field", "error"),
    ("Invalid overloaded operator in request", "error"),
    ("", "error"),
])
def test_recognized_unavailability_does_not_guess_capacity(failure, expected_type):
    classified = streaming._classify_provider_error(failure)
    assert classified["type"] == expected_type
    assert (classified.get("category") == "capacity") is (expected_type == "overloaded")
    if expected_type == "service_unavailable":
        assert "capacity" not in classified["hint"].lower()
        assert "administrator has been notified" not in classified["hint"]


@pytest.mark.parametrize("err_type,message", [
    ("governance_denied", "This workspace is not assigned to your account."),
    ("cancelled", "Cancelled by user"),
    ("interrupted", "The operation was interrupted."),
    ("tool_limit_reached", "The maximum number of tool calls was reached."),
    ("error", "HTTP 400: invalid request field"),
    ("error", "Connection reset before any response"),
    ("no_response", "The run ended without a final answer."),
])
def test_other_failures_keep_their_original_meaning(err_type, message):
    payload = streaming._provider_error_payload(message, err_type)
    assert payload == {"message": message, "type": err_type, "details": message}


@pytest.mark.parametrize("notified", [False, True])
def test_plain_copy_retains_actual_notification_outcome(monkeypatch, notified):
    from api import capacity_alerts

    monkeypatch.setattr(capacity_alerts, "record_capacity_event", lambda *a, **kw: {"notified": notified})
    classified = streaming._classify_provider_error("HTTP 402: insufficient credits")
    streaming._report_capacity_incident(classified, provider="synthetic", model="synthetic", detail="HTTP 402", source="chat")
    payload = streaming._provider_error_payload("HTTP 402", classified["type"], classified["hint"])
    normal_copy = payload["message"] + " " + payload.get("hint", "")
    assert ("administrator has been notified" in normal_copy) is notified
    assert "HTTP 402" not in normal_copy
    assert payload["details"] == "HTTP 402"


@pytest.mark.parametrize("provider_details", [False, True])
def test_diagnostic_redaction_and_existing_size_limit_are_preserved(monkeypatch, provider_details):
    monkeypatch.setattr(streaming, "_redact_text", lambda text: text.replace("SYNTHETIC_SECRET", "[REDACTED]"))
    payload = streaming._provider_error_payload(
        "HTTP 401 SYNTHETIC_SECRET " + "x" * 2000, "auth_mismatch", provider_details=provider_details,
    )
    assert "SYNTHETIC_SECRET" not in str(payload)
    assert "HTTP" not in payload["message"]
    if provider_details:
        assert "[REDACTED]" in payload["details"]
        assert len(payload["details"]) <= 1200
        assert payload["details"].endswith("…")
    else:
        assert "details" not in payload


def test_fully_redacted_error_does_not_fall_back_to_raw_input(monkeypatch):
    monkeypatch.setattr(streaming, "_redact_text", lambda text: "")
    payload = streaming._provider_error_payload("SYNTHETIC_SECRET", "error")
    assert payload["message"]
    assert "SYNTHETIC_SECRET" not in str(payload)
    assert "details" not in payload
