"""Upstream capacity: plain-language user copy plus administrator alerts.

Two Super Agent tickets of 27 Aug 2026:
* normal users saw raw HTTP statuses, provider diagnostics and terminal
  commands when an upstream account was spent;
* an alert that depended on an agent run could not fire when every upstream
  account was spent, leaving the user with silence.

The rule under test throughout: the user message claims an administrator was
notified ONLY when an alert was really recorded.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

CATALOG = (REPO / "api" / "governance" / "catalog.py").read_text(encoding="utf-8")
STREAMING = (REPO / "api" / "streaming.py").read_text(encoding="utf-8")


@pytest.fixture
def ca(tmp_path, monkeypatch):
    from api import config

    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    import api.capacity_alerts as module

    monkeypatch.setattr(module, "effective_config", lambda: dict(module.DEFAULT_CONFIG))
    return module


# ── User-facing copy ────────────────────────────────────────────────────────

def test_user_copy_is_plain_language_without_internals(ca):
    for kind in ("quota_exhausted", "rate_limit", "overloaded"):
        text = ca.user_facing_message(kind, notified=True)
        assert text and text[0].isupper()
        low = text.lower()
        for leak in ("http", "503", "429", "hermes model", "api key", "token",
                     "provider", "credits", "terminal"):
            assert leak not in low, f"{kind} copy leaks {leak!r}: {text}"
        assert "try again" in low


def test_notified_sentence_only_when_an_alert_exists(ca):
    assert "administrator has been notified" in ca.user_facing_message("quota_exhausted", notified=True)
    assert "administrator has been notified" not in ca.user_facing_message("quota_exhausted", notified=False)


def test_non_capacity_kind_has_no_copy(ca):
    assert ca.user_facing_message("model_not_found", notified=True) == ""
    assert ca.is_capacity_kind("auth_mismatch") is False


# ── Deduplication ───────────────────────────────────────────────────────────

def test_repeat_within_cooldown_is_one_alert_but_keeps_the_count(ca):
    first = ca.record_capacity_event("quota_exhausted", provider="anthropic", detail="529")
    second = ca.record_capacity_event("quota_exhausted", provider="anthropic", detail="529 again")
    third = ca.record_capacity_event("quota_exhausted", provider="anthropic")
    assert first["notified"] is True
    assert second["notified"] is False and second["deduplicated"] is True
    assert third["deduplicated"] is True
    events = ca.list_events()
    assert len(events) == 1
    assert events[0]["count"] == 3, "the real incident volume must stay visible"


def test_a_different_provider_or_kind_is_its_own_alert(ca):
    ca.record_capacity_event("quota_exhausted", provider="anthropic")
    assert ca.record_capacity_event("quota_exhausted", provider="openai")["notified"] is True
    assert ca.record_capacity_event("rate_limit", provider="anthropic")["notified"] is True
    assert len(ca.list_events()) == 3


def test_cooldown_expiry_alerts_again(ca, monkeypatch):
    monkeypatch.setattr(ca, "effective_config",
                        lambda: {**ca.DEFAULT_CONFIG, "capacity_alert_cooldown_seconds": 30})
    ca.record_capacity_event("quota_exhausted", provider="anthropic")
    store = json.loads((pathlib.Path(ca._store_path())).read_text(encoding="utf-8"))
    store["events"][0]["last_ts"] -= 3600
    pathlib.Path(ca._store_path()).write_text(json.dumps(store), encoding="utf-8")
    assert ca.record_capacity_event("quota_exhausted", provider="anthropic")["notified"] is True


# ── Admin surface ───────────────────────────────────────────────────────────

def test_diagnostics_are_stored_for_admins_not_for_users(ca):
    ca.record_capacity_event("quota_exhausted", provider="anthropic",
                             model="claude-x", detail="HTTP 529 upstream overloaded")
    event = ca.list_events()[0]
    assert event["detail"] == "HTTP 529 upstream overloaded"
    assert event["provider"] == "anthropic" and event["model"] == "claude-x"
    assert "529" not in ca.user_facing_message("quota_exhausted", notified=True)


def test_acknowledge_is_idempotent_and_filters(ca):
    ca.record_capacity_event("quota_exhausted", provider="anthropic")
    event_id = ca.list_events()[0]["id"]
    assert ca.acknowledge(event_id) is True
    assert ca.acknowledge(event_id) is False, "already acknowledged is not a change"
    assert ca.list_events(include_acknowledged=False) == []
    assert len(ca.list_events(include_acknowledged=True)) == 1


def test_alert_route_is_admin_gated():
    """Alert rows carry provider diagnostics, so read is config:write."""
    assert 'RouteRule("/api/capacity",            "config:write", "config:write")' in CATALOG


# ── Configuration ───────────────────────────────────────────────────────────

def test_invalid_config_values_are_dropped_never_stored(ca):
    clean = ca.sanitize_config({
        "capacity_alert_poll_seconds": 5,            # below the floor
        "capacity_alert_cooldown_seconds": "abc",    # not a number
        "capacity_alert_thresholds": {"Anthropic": 20, "bad": "x", "": 5, "openai": 300},
        "capacity_alert_destination": "telegram:123",
    })
    assert "capacity_alert_poll_seconds" not in clean
    assert "capacity_alert_cooldown_seconds" not in clean
    assert clean["capacity_alert_thresholds"] == {"anthropic": 20.0}
    assert clean["capacity_alert_destination"] == "telegram:123"


def test_valid_config_passes(ca):
    clean = ca.sanitize_config({"capacity_alert_poll_seconds": 600,
                                "capacity_alert_cooldown_seconds": 1800})
    assert clean == {"capacity_alert_poll_seconds": 600,
                     "capacity_alert_cooldown_seconds": 1800}


def test_thresholds_warn_before_depletion(ca, monkeypatch):
    monkeypatch.setattr(ca, "effective_config", lambda: {
        **ca.DEFAULT_CONFIG, "capacity_alert_thresholds": {"anthropic": 20, "openai": 10}})
    breaches = ca.threshold_breaches({"anthropic": 15, "openai": 50, "mistral": 1})
    assert [b["provider"] for b in breaches] == ["anthropic"]
    assert breaches[0]["threshold"] == 20.0
    assert ca.threshold_breaches({"anthropic": 20}), "at the threshold counts as a breach"


def test_store_never_grows_without_bound(ca):
    for i in range(ca._MAX_EVENTS + 25):
        ca.record_capacity_event("quota_exhausted", provider=f"p{i}")
    assert len(ca.list_events(limit=ca._MAX_EVENTS)) == ca._MAX_EVENTS


# ── Wiring ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("error", [
    "Error code: 429 - rate limit exceeded",
    "Your credit balance is too low, you need more credits",
    "401 unauthorized: invalid api key",
    "404 model not found: does not exist",
    "",  # silent failure: no content and no error
])
def test_no_user_facing_hint_carries_internals_or_a_cli_command(ca, error):
    """Every hint a WebUI user can see must be plain language: no status code,
    no terminal command, no instruction they cannot act on."""
    from api.streaming import _classify_provider_error

    hint = _classify_provider_error(error, None, silent_failure=not error).get("hint", "")
    low = hint.lower()
    assert "hermes model" not in low, hint
    assert "terminal" not in low, hint
    for code in ("401", "404", "429", "503", "529", "http"):
        assert code not in low, hint


def test_classifier_marks_capacity_kinds():
    assert "'category': 'capacity'" in STREAMING
    assert "_capacity_hint('quota_exhausted')" in STREAMING
    assert "_capacity_hint('rate_limit')" in STREAMING


def test_both_failure_paths_report_the_incident():
    assert STREAMING.count("_report_capacity_incident(") >= 3, (
        "definition plus the result path and the exception path"
    )


def test_scheduled_task_speaks_plain_language_on_a_capacity_failure(ca, monkeypatch):
    import api.cron_webui_delivery as bridge

    monkeypatch.setattr(bridge, "_classify_provider_error", None, raising=False)
    job = {"id": "j1", "name": "Peterson release monitor", "provider": "anthropic"}
    text = bridge.build_update_text(
        job, body=None, run_ok=False,
        run_error="Error code: 429 - rate limit exceeded for this account",
    )
    assert "429" not in text and "rate limit exceeded" not in text.lower()
    assert "could not run" in text
    assert "stays scheduled" in text
    assert ca.list_events(), "the failure must reach an administrator"


def test_non_capacity_failure_keeps_its_original_detail(ca):
    import api.cron_webui_delivery as bridge

    text = bridge.build_update_text(
        job := {"id": "j2", "name": "Nightly"}, body=None, run_ok=False,
        run_error="ValueError: bad config in step 3",
    )
    assert "bad config in step 3" in text
    assert job["id"] in text
    assert not ca.list_events(), "an ordinary bug is not a capacity incident"


# ── Administrator settings pane ─────────────────────────────────────────────

INDEX_HTML = (REPO / "static" / "index.html").read_text(encoding="utf-8")
PANELS_JS = (REPO / "static" / "panels.js").read_text(encoding="utf-8")
EN_JS = (REPO / "static" / "i18n" / "en.js").read_text(encoding="utf-8")


def test_settings_pane_exposes_every_configurable_value():
    for field in ("capacityPollSeconds", "capacityCooldownSeconds",
                  "capacityThresholds", "capacityDestination"):
        assert f'id="{field}"' in INDEX_HTML, field
    assert 'id="capacityAlertsList"' in INDEX_HTML


def test_pane_is_hidden_until_the_admin_route_answers():
    assert 'id="capacityAlertsField" style="display:none"' in INDEX_HTML
    block = PANELS_JS[PANELS_JS.index("async function loadCapacityAlerts"):][:1800]
    assert "field.style.display='none'" in block, (
        "a non-admin must not be shown an empty administrator panel"
    )
    assert "field.style.display=''" in block


def test_pane_loads_when_the_system_section_opens():
    assert "if(section==='system'&&typeof loadCapacityAlerts==='function')" in PANELS_JS


def test_saving_re_renders_from_the_server_validated_config():
    block = PANELS_JS[PANELS_JS.index("async function saveCapacityConfig"):][:1600]
    assert "await loadCapacityAlerts(false)" in block, (
        "a dropped invalid value must not linger in the field as if it were stored"
    )


def test_threshold_input_round_trips():
    parse = PANELS_JS[PANELS_JS.index("function _capacityParseThresholds"):][:600]
    assert "toLowerCase()" in parse and "pct>0&&pct<=100" in parse
    assert "function _capacityFormatThresholds" in PANELS_JS


def test_alert_rows_escape_provider_supplied_text():
    row = PANELS_JS[PANELS_JS.index("function _capacityAlertRow"):][:1400]
    for field in ("a.provider", "a.detail", "a.model", "a.dispatch_error"):
        assert f"esc(String({field}" in row or f"esc(String({field}))" in row, field


def test_every_pane_string_has_an_english_key():
    for key in ("settings_label_capacity", "capacity_poll", "capacity_cooldown",
                "capacity_thresholds", "capacity_destination", "capacity_save",
                "capacity_no_alerts", "capacity_ack", "capacity_dispatch_failed"):
        assert f"{key}:" in EN_JS, key
