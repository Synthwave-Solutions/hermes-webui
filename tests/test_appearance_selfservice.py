"""Appearance settings are self-service; no admin approval for dark mode.

Reported by Michael on 26 Aug 2026 in Hermes WebUI: flipping dark mode (a
purely cosmetic, personal preference) required an administrator because the
whole ``POST /api/settings`` route rode on ``config:write``. Now:

* the route catalog admits ``POST /api/settings`` with ``config:read``;
* the handler's body-sink guard (api/settings_scope.py) lets appearance-only
  payloads through for any caller the route admitted, where the whitelist is
  derived from the REAL appearance autosave payload
  (static/panels.js::_appearancePayloadFromUi, every key classified as
  cosmetic), and keeps every non-cosmetic settings write on ``config:write``
  exactly as before;
* a governed user's dark-mode flip writes no approval row anywhere;
* denied non-cosmetic writes append a ``deny`` governance audit event, and
  ``report_only`` policy mode audits ``would_deny`` and allows instead of
  enforcing.

House pattern: injected policy loader + pure decision tests (see
tests/test_governance_enforce.py) and source inspection of the route hook.
"""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import approvals, config  # noqa: E402
from api.governance import loader  # noqa: E402
from api.governance.audit import read_audit_events  # noqa: E402
from api.governance.catalog import route_permission  # noqa: E402
from api.governance.enforce import evaluate_request  # noqa: E402
from api.governance.loader import parse_governance_policy  # noqa: E402
from api.settings_scope import (  # noqa: E402
    APPEARANCE_SETTINGS_KEYS,
    COMPOSER_CONTROL_VISIBILITY_KEYS,
    is_appearance_only_payload,
    settings_write_denial,
)

REPO = Path(__file__).resolve().parent.parent
ROUTES = (REPO / "api" / "routes.py").read_text(encoding="utf-8")
PANELS_JS = (REPO / "static" / "panels.js").read_text(encoding="utf-8")
BOOT_JS = (REPO / "static" / "boot.js").read_text(encoding="utf-8")

BOOTSTRAP = "michael@example.test"

POLICY = {
    "version": 1,
    "mode": "enforce",
    "default_effect": "deny",
    "bootstrap_admins": [BOOTSTRAP],
    "roles": {
        "admin": {
            "grants": {
                "permissions": ["config:read", "config:write"],
                "profiles": ["*"],
                "routes": ["*"],
            },
        },
        "governed": {
            # A settings-panel user: can read settings, has NO config:write.
            "grants": {
                "permissions": ["config:read", "sessions:read", "chat:use"],
                "profiles": ["steve"],
                "routes": ["/api/settings", "/api/session*", "/api/chat*"],
            },
        },
    },
    "users": {
        "admin@example.test": {"roles": ["admin"]},
        "steve@example.test": {"roles": ["governed"]},
    },
}


def _identity(email):
    return {"email": email, "groups": [], "claims_subset": {}, "method": "oidc"}


@pytest.fixture(autouse=True)
def _isolated_audit_home(tmp_path, monkeypatch):
    """Denied writes now audit; keep the JSONL sink out of the real ~/.hermes."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))


@pytest.fixture
def inject_policy():
    def _set(data):
        policy = parse_governance_policy(data)
        loader.set_policy_loader(lambda: policy)
        return policy
    yield _set
    loader.set_policy_loader(None)


# ── D1: the whitelist is derived from the REAL appearance autosave payload ──
# Fixture-pinned copy of every key static/panels.js _appearancePayloadFromUi
# can emit. If the frontend payload or the backend whitelist drifts, one of
# the equality assertions below fails and forces a deliberate re-classification
# (cosmetic → whitelist; non-cosmetic → split the payload client-side).

EXPECTED_APPEARANCE_PAYLOAD_KEYS = frozenset({
    "theme",
    "skin",
    "font_size",
    "chat_activity_display_mode",
    "transparent_stream_event_timestamps",
    "session_jump_buttons",
    "session_endless_scroll",
    "auto_scroll_follow",
    "render_user_markdown",
    "large_text_paste_as_attachment",
    "project_quick_create_buttons",
    "structured_code_default_view",
    "structured_code_auto_tree_lines",
    "show_titlebar_profile",
    "worklog_details_expanded_default",
    "activity_feed_expanded_default",
    "composer_control_order",
    "hidden_tabs",
    "tab_order",
    "hide_composer_attach",
    "hide_composer_saved_prompts",
    "hide_composer_mic",
    "hide_composer_profile",
    "hide_composer_workspace",
    "hide_composer_model",
    "hide_composer_reasoning",
    "hide_composer_context",
    "hide_composer_voice_mode",
    "hide_composer_yolo",
    "hide_composer_bg_badge",
    "hide_composer_mobile_config",
    "hide_composer_quota_chip",
    "hide_composer_toolsets",
    "hide_composer_status",
})


def _js_function_source(src, name):
    start = src.index("function " + name + "(){")
    end = src.index("\n}", start)
    return src[start:end]


def _appearance_payload_keys_from_js():
    """Enumerate every key the real autosave payload can emit, from the JS."""
    body = _js_function_source(PANELS_JS, "_appearancePayloadFromUi")
    ret = body[body.index("return {"):]
    keys = set(re.findall(r"^\s+([a-z_][a-z0-9_]*):", ret, re.M))
    # The payload spreads two helpers; resolve their keys too.
    assert "..._structuredCodeViewFromUi()" in ret
    assert "..._composerControlVisibilityPayload()" in ret
    structured = _js_function_source(PANELS_JS, "_structuredCodeViewFromUi")
    structured_ret = structured[structured.index("return {"):]
    keys |= set(re.findall(r"([a-z_][a-z0-9_]*):", structured_ret))
    # _composerControlVisibilityPayload emits one key per composer control def
    # (base + situational arrays in static/boot.js).
    composer_keys = set(re.findall(r"\bkey:'(hide_composer_[a-z0-9_]*)'", BOOT_JS))
    assert composer_keys, "composer control defs must be discoverable in boot.js"
    keys |= composer_keys
    return frozenset(keys)


def test_whitelist_equals_the_real_appearance_payload_keys():
    js_keys = _appearance_payload_keys_from_js()
    assert js_keys == EXPECTED_APPEARANCE_PAYLOAD_KEYS, (
        "static/panels.js _appearancePayloadFromUi changed its payload keys; "
        "re-classify the new/removed keys (cosmetic → api/settings_scope.py "
        "whitelist, non-cosmetic → split the autosave payload client-side) and "
        "update EXPECTED_APPEARANCE_PAYLOAD_KEYS."
    )
    assert APPEARANCE_SETTINGS_KEYS == EXPECTED_APPEARANCE_PAYLOAD_KEYS, (
        "api/settings_scope.py APPEARANCE_SETTINGS_KEYS drifted from the real "
        "appearance autosave payload; a governed user's appearance autosave "
        "would 403 (or a non-cosmetic key would ride the cosmetic whitelist)."
    )


def test_composer_visibility_keys_match_boot_defs():
    composer_keys = frozenset(re.findall(r"\bkey:'(hide_composer_[a-z0-9_]*)'", BOOT_JS))
    assert COMPOSER_CONTROL_VISIBILITY_KEYS == composer_keys


# ── Route catalog: the enforce hook admits the POST with config:read ────────

def test_settings_post_rides_on_config_read():
    assert route_permission("/api/settings", "GET") == "config:read"
    assert route_permission("/api/settings", "POST") == "config:read"


def test_governed_user_passes_the_route_hook_for_settings_post(inject_policy):
    inject_policy(POLICY)
    decision = evaluate_request(_identity("steve@example.test"), "POST", "/api/settings")
    assert decision.allow is True
    assert decision.reason == "allowed"


# ── Body-sink guard: appearance-only is self-service, the rest stays gated ──

def test_appearance_payload_classification():
    assert is_appearance_only_payload({"theme": "dark"}) is True
    assert is_appearance_only_payload({"theme": "light", "skin": "slate", "font_size": "15"}) is True
    assert is_appearance_only_payload({}) is False
    assert is_appearance_only_payload(None) is False
    assert is_appearance_only_payload({"theme": "dark", "bot_name": "X"}) is False


def test_full_appearance_autosave_payload_is_selfservice(inject_policy):
    """The REAL autosave payload (all ~34 keys at once) must pass the guard.

    Regression for the 26 Aug 2026 whitelist gap: the guard only admitted
    theme/skin/font_size while _appearancePayloadFromUi always sends the full
    cosmetic key set, so every governed user's dark-mode flip 403'd.
    """
    inject_policy(POLICY)
    full_payload = {key: "x" for key in sorted(EXPECTED_APPEARANCE_PAYLOAD_KEYS)}
    assert is_appearance_only_payload(full_payload) is True
    assert settings_write_denial(_identity("steve@example.test"), full_payload) is None
    # Self-service means no audit row either: allowed requests are not audited.
    assert read_audit_events(10) == []


def test_governed_user_flips_dark_mode_without_approval_row(inject_policy, tmp_path, monkeypatch):
    inject_policy(POLICY)
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "webui")

    for payload in ({"theme": "dark"}, {"theme": "light", "skin": "default", "font_size": "14"}):
        assert settings_write_denial(_identity("steve@example.test"), payload) is None

    # No approval row was requested or persisted anywhere.
    assert approvals.list_pending() == []
    assert not (config.STATE_DIR / "approvals.json").exists()


def test_non_cosmetic_settings_stay_gated_on_config_write(inject_policy):
    inject_policy(POLICY)
    governed = _identity("steve@example.test")
    for payload in (
        {"bot_name": "Hermes"},
        {"theme": "dark", "bot_name": "Hermes"},  # mixed payloads stay gated too
        {"_set_password": "hunter2"},
        {"show_thinking": True},
        {},
    ):
        denial = settings_write_denial(governed, payload)
        assert denial is not None, f"payload {payload!r} must still require config:write"
        assert denial["resource"] == "config:write"
        assert denial["reason"] == "permission_not_allowed"


def test_config_write_holders_and_bootstrap_keep_full_settings_access(inject_policy):
    inject_policy(POLICY)
    for email in ("admin@example.test", BOOTSTRAP):
        assert settings_write_denial(_identity(email), {"bot_name": "Hermes"}) is None
        assert settings_write_denial(_identity(email), {"theme": "dark"}) is None


def test_governance_off_keeps_previous_behaviour(inject_policy):
    inject_policy({"version": 1, "mode": "off", "default_effect": "deny"})
    assert settings_write_denial(None, {"bot_name": "Hermes"}) is None
    assert settings_write_denial(None, {"theme": "dark"}) is None


# ── D6: denied settings writes land in the governance audit trail ───────────

def test_denied_non_cosmetic_write_records_deny_audit(inject_policy):
    inject_policy(POLICY)
    denial = settings_write_denial(_identity("steve@example.test"), {"bot_name": "X"})
    assert denial is not None

    events = read_audit_events(10)
    assert len(events) == 1
    event = events[0]
    assert event["event"] == "deny"
    assert event["path"] == "/api/settings"
    assert event["method"] == "POST"
    assert event["reason"] == "permission_not_allowed"
    assert event["mode"] == "enforce"
    assert event["report_only"] is False
    assert event["extra"]["resource"] == "config:write"
    # Identity is stored hashed, never raw (house audit invariant).
    assert "steve@example.test" not in json.dumps(event)


def test_allowed_writes_are_not_audited(inject_policy):
    inject_policy(POLICY)
    assert settings_write_denial(_identity("admin@example.test"), {"bot_name": "X"}) is None
    assert settings_write_denial(_identity("steve@example.test"), {"theme": "dark"}) is None
    assert read_audit_events(10) == []


# ── D5: report_only governance mode must not enforce ────────────────────────

def test_report_only_allows_non_cosmetic_write_and_audits_would_deny(inject_policy):
    inject_policy({**POLICY, "mode": "report_only"})
    # Zero behaviour change for the caller: the write proceeds.
    assert settings_write_denial(_identity("steve@example.test"), {"bot_name": "X"}) is None

    events = read_audit_events(10)
    assert len(events) == 1
    event = events[0]
    assert event["event"] == "would_deny"
    assert event["path"] == "/api/settings"
    assert event["method"] == "POST"
    assert event["reason"] == "permission_not_allowed"
    assert event["mode"] == "report_only"
    assert event["report_only"] is True
    assert event["extra"]["resource"] == "config:write"
    assert "steve@example.test" not in json.dumps(event)


def test_report_only_appearance_writes_stay_unaudited(inject_policy):
    inject_policy({**POLICY, "mode": "report_only"})
    assert settings_write_denial(_identity("steve@example.test"), {"theme": "dark"}) is None
    assert read_audit_events(10) == []


# ── Route wiring + UI persistence (source inspection) ───────────────────────

def test_settings_post_branch_calls_the_guard_first():
    marker = ROUTES.index('if parsed.path == "/api/settings":',
                          ROUTES.index("Settings (POST)"))
    branch_head = ROUTES[marker:marker + 900]
    assert "settings_write_denial_for" in branch_head, (
        "POST /api/settings must run the api.settings_scope body-sink guard "
        "before doing any settings work (appearance self-service, 26 Aug 2026)."
    )
    # The guard runs before the password/auth handling that follows.
    assert branch_head.index("settings_write_denial_for") < branch_head.index("from api.auth import")


def test_ui_appearance_autosave_persists_and_confirms():
    # The appearance autosave payload stays cosmetic-only and the UI confirms
    # the save inline (Issue #1003 machinery this fix rides on).
    assert "_appearancePayloadFromUi" in PANELS_JS
    assert "_scheduleAppearanceAutosave" in PANELS_JS
