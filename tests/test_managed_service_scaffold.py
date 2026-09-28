"""The managed-service scaffold is behaviour-neutral (program plan Appendix E.1,
addendum Appendix AE).

Wave 0 pre-writes every seam, stub module, catalog rule, script tag and i18n
key that the Wave 1 packages fill, so no two packages edit the same shared
file. Until a package fills its stub the WebUI must behave exactly as before.
These tests pin that:

* each stub returns what the code did before its seam existed (404, 405, 204
  with nothing stored, the payload unchanged, ``mark_job_run`` as before);
* the dispatcher and the route catalog classify every new route, and the
  personal memory routes resolve ``chat:use`` while unknown children fail
  closed;
* the chat renderer, the post-processing chain, the Memory panel and the
  runtime prompt produce the same output as the code without the seams;
* the seams are wired: a filled stub is actually called with the documented
  arguments and its answer is used;
* the placeholder files exist, define nothing, and are listed in the page and
  the service worker; every scaffold i18n key is in all 15 locales.

"Pre-scaffold" renderers and prompts are rebuilt from the current source with
the seam blocks cut out, so these checks stay valid across unrelated changes;
the seam text itself is pinned here because the packages read it.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import io
import json
import re
import shutil
import subprocess
import sys
import textwrap
import threading
import types
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.governance import loader  # noqa: E402
from api.governance.catalog import _SELF_ROUTES, route_permission  # noqa: E402
from api.governance.enforce import evaluate_request  # noqa: E402
from api.governance.loader import parse_governance_policy  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures" / "managed_service"
STATIC = REPO / "static"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node not on PATH")

MEMBER = "member@example.test"
OUTSIDER = "outsider@example.test"
OWNER = "owner@example.test"
OTHER = "other@example.test"

POLICY = {
    "version": 1,
    "mode": "enforce",
    "default_effect": "deny",
    "bootstrap_admins": ["boot@example.test"],
    "roles": {
        "member": {
            "grants": {
                "permissions": ["chat:use", "sessions:read", "sessions:write",
                                "cron:read", "cron:write", "cron:run"],
                "profiles": ["*"],
                "routes": ["*"],
            },
        },
        "outsider": {
            "grants": {"permissions": ["sessions:read"], "profiles": ["*"], "routes": ["*"]},
        },
    },
    "users": {
        MEMBER: {"roles": ["member"]},
        OUTSIDER: {"roles": ["outsider"]},
        OWNER: {"roles": ["member"]},
        OTHER: {"roles": ["member"]},
    },
}

WAVE1_SELF_ROUTES = (
    "/api/crons/notifications",
    "/api/client-errors",
    "/api/help/events",
    "/api/org/overview",
    "/api/org/departments",
    "/api/org/people",
    "/api/org/approvals",
    "/api/org/usage",
)
ORG_ROUTES = WAVE1_SELF_ROUTES[3:]
# Modules page and Apps launcher (plan Appendix E.4.2), filled by W12.
MODULE_ROUTES = (
    ("GET", "/api/org/modules"),
    ("POST", "/api/org/modules/request"),
    ("GET", "/api/apps"),
)
MODULE_PLACEHOLDERS = ("static/modules.js", "static/modules.css", "static/module-content.js")
MNEMO_GET_ROUTES = (
    "/api/mnemo/scopes",
    "/api/mnemo/me/summary",
    "/api/mnemo/me/memories",
    "/api/mnemo/me/export",
    "/api/mnemo/me/settings",
)
MNEMO_POST_ROUTES = (
    "/api/mnemo/me/memory/update",
    "/api/mnemo/me/memory/forget",
    "/api/mnemo/me/erase",
    "/api/mnemo/me/settings",
)
MNEMO_ROUTES = tuple(dict.fromkeys(MNEMO_GET_ROUTES + MNEMO_POST_ROUTES))

JS_PLACEHOLDERS = (
    "static/svg_visuals.js",
    "static/memory_inventory.js",
    "static/help-content.js",
    "static/help-tour.js",
    "static/error-reporter.js",
    "static/vendor/guida/0.2.0/guida.umd.js",
)
CSS_PLACEHOLDERS = (
    "static/svg_visuals.css",
    "static/memory_inventory.css",
    "static/cron-notify.css",
    "static/help-tour.css",
    "static/group-routing.css",
)
SEAM_GLOBALS = (
    "svgVisualFenceAccepts",
    "svgVisualRawSpans",
    "renderSvgVisualBlocks",
    "enhanceSvgMediaCards",
    "SynthPulseMemoryExtensions",
)

# Plan Appendix G (W2, W4, W6) and addendum Appendix AG (A1, A6).
I18N_KEYS = (
    "cron_notify_legend", "cron_notify_me_label", "cron_notify_me_all",
    "cron_notify_me_failures", "cron_notify_me_never", "cron_notify_me_off_admin",
    "cron_notify_delivery_failures_only", "cron_notify_delivery_off_notice",
    "cron_notify_hint", "cron_notify_hint_managed", "cron_notify_delivery_off_warning",
    "cron_notify_chip_change", "cron_notify_mute_for_me", "cron_notify_unmute_for_me",
    "cron_notify_muted", "cron_notify_saved", "cron_notify_conflict",
    "help_page_button", "help_page_button_title", "help_tour_first_run",
    "help_tour_org_admin", "help_tour_next", "help_tour_back", "help_tour_close",
    "help_tour_done", "help_tour_step_of", "help_tour_completed", "help_tour_offer",
    "help_tour_offer_yes", "help_tour_offer_no", "help_explain_fallback_title",
    "help_still_stuck", "help_did_not_help", "help_whats_new_title",
    "help_whats_new_dismiss", "help_card_tour_title", "help_card_tour_body",
    "help_card_explain_title", "help_card_explain_body", "cmd_tour_desc",
    "cmd_explain_desc", "group_route_reason_mention", "group_route_reason_only_bot",
    "group_route_reason_sticky", "group_route_reason_default", "group_route_working",
    "group_route_set_default", "group_route_clear_default", "group_route_default_badge",
    "group_route_last_bot_unavailable",
    "svg_visual_label", "svg_toolbar_label", "svg_view_full", "svg_copy", "svg_copied",
    "svg_download", "svg_show_source", "svg_hide_source", "svg_blocked", "svg_drawing",
    "mnemo_section_label", "mnemo_section_tooltip", "mnemo_intro", "mnemo_summary",
    "mnemo_summary_one", "mnemo_auto_store", "mnemo_auto_recall", "mnemo_settings_saved",
    "mnemo_search_placeholder", "mnemo_filter_all", "mnemo_filter_preference",
    "mnemo_filter_decision", "mnemo_filter_person", "mnemo_filter_project",
    "mnemo_filter_fact", "mnemo_filter_snippet", "mnemo_filter_summary",
    "mnemo_filter_shared_by_me", "mnemo_filter_shared_with_me", "mnemo_kind_preference",
    "mnemo_kind_decision", "mnemo_kind_person", "mnemo_kind_project",
    "mnemo_kind_correction", "mnemo_kind_fact", "mnemo_kind_snippet",
    "mnemo_kind_summary", "mnemo_kind_note", "mnemo_source_label", "mnemo_source_all",
    "mnemo_source_webui", "mnemo_source_gchat", "mnemo_source_assistant",
    "mnemo_source_manual", "mnemo_source_other", "mnemo_badge_only_you",
    "mnemo_badge_shared_with", "mnemo_badge_shared_by", "mnemo_forget",
    "mnemo_forget_confirm", "mnemo_forgotten", "mnemo_edit_saved", "mnemo_edit_conflict",
    "mnemo_export_json", "mnemo_export_md", "mnemo_forget_all", "mnemo_forget_all_title",
    "mnemo_forget_all_body", "mnemo_forget_all_type", "mnemo_forget_all_done",
    "mnemo_empty", "mnemo_no_results", "mnemo_load_more", "mnemo_hub_down",
    "mnemo_rate_limited",
)
LOCALES = ("cs", "de", "en", "es", "fr", "it", "ja", "ko", "pl", "pt", "ru", "tr", "vi", "zh", "zh-Hant")

# Keys the orchestrator adds before Wave 1 (plan Appendix E.4.2 and later
# seams), with their exact English values in every locale.
SEAM_I18N = {
    # E.4.2: the Modules page and the Apps launcher (W12).
    "modules_nav": "Modules",
    "modules_title": "Modules",
    "modules_intro": "What your organisation has and what you can add.",
    "modules_included_heading": "Included in your service",
    "modules_advanced_heading": "Available modules",
    "modules_status_included": "Included",
    "modules_status_active": "Active",
    "modules_status_requested": "Requested",
    "modules_status_setting_up": "Being set up",
    "modules_status_available": "Available",
    "modules_status_not_available": "Not available here",
    "modules_price_on_request": "Price on request",
    "modules_uses_model_budget": "Uses your model budget",
    "modules_no_model_budget": "Does not use your model budget",
    "modules_request_button": "Request this module",
    "modules_request_contact": "Ask your Synthwave contact to add this module.",
    "modules_request_preview_title": "What we send",
    "modules_request_note_label": "Note (optional)",
    "modules_request_sent": "Request sent. We will send you a proposal.",
    "modules_request_partner": "Ask your partner to add this module.",
    "apps_button": "Apps",
    "apps_button_title": "Open your apps",
    "apps_empty": "No apps available yet.",
    "apps_open": "Open {0}",
    "modules_reason_arch": "Not available on this server type.",
    "modules_reason_hosting_model": "Not available where your platform runs.",
    "modules_reason_requires": "Needs another module first.",
    "modules_reason_not_confirmed": "Not offered yet.",
    "modules_reason_placement": "Needs extra server capacity first.",
    # E.5.2: module connections (W12) and the neutral channel copy (N3).
    "modules_works_with": "Works with",
    "modules_connection_active": "Connected",
    "modules_connection_off": "Not switched on",
    "modules_connection_needs_module": "Available with {0}",
    "modules_connection_consent_note": "Only with the consent of the people involved",
    "channels_hook_on_save_neutral": "On save the webhook is published on your platform's public address and the URL appears on the card. Enter that URL at the provider.",
    "integrations_connect_not_configured": "Connecting apps is not set up on this platform yet. Ask your administrator.",
    # E.7.1: the A6 amendment keys and R3's live voice notice.
    "mnemo_filter_review": "Needs your review",
    "mnemo_trust_inferred": "Inferred by your assistant",
    "mnemo_trust_imported": "Imported",
    "mnemo_status_outdated": "Outdated",
    "voice_live_unavailable": "Live voice is not available on this platform.",
}
# E.5.3 and E.6.1: network and identity product names never appear in copy.
NETWORK_IDENTITY_NAMES = ("Tailscale", "NetBird", "Headscale", "Keycloak", "oauth2-proxy", "WireGuard",
                          "Nubus", "Univention", "noVNC", "TigerVNC", "Xvnc", "Xfce", "Funnel")


# ── Harness ────────────────────────────────────────────────────────────────

def _identity(email):
    return {"email": email, "groups": [], "claims_subset": {}, "method": "oidc"}


class _Handler:
    """Records one response the way BaseHTTPRequestHandler would send it."""

    def __init__(self):
        self.status = None
        self.headers = {}
        self.response_headers = []
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass

    def header(self, name):
        return next((v for k, v in self.response_headers if k.lower() == name.lower()), None)

    @property
    def raw(self):
        return self.wfile.getvalue()

    @property
    def body(self):
        return json.loads(self.raw.decode("utf-8"))


@pytest.fixture
def inject_policy():
    def _set(data):
        policy = parse_governance_policy(data)
        loader.set_policy_loader(lambda: policy)
        return policy
    yield _set
    loader.set_policy_loader(None)


@pytest.fixture
def dispatch(monkeypatch, inject_policy):
    """Drive the real handle_get / handle_post as a signed-in user."""
    import api.governance.enforce as enforce
    import api.routes as routes

    inject_policy(POLICY)
    state = SimpleNamespace(email=MEMBER)
    monkeypatch.setattr(enforce, "_request_identity", lambda handler: _identity(state.email) if state.email else None)
    monkeypatch.setattr(routes, "_check_csrf", lambda _handler: True)
    monkeypatch.setattr(routes, "_guard_request_session_visibility",
                        lambda handler, parsed, body=None, method="GET": True)

    def get(path, email=MEMBER):
        state.email = email
        handler = _Handler()
        result = routes.handle_get(handler, urlparse("http://localhost" + path))
        return result, handler

    def post(path, body=None, email=MEMBER):
        state.email = email
        monkeypatch.setattr(routes, "read_body", lambda _handler: copy.deepcopy(body or {}))
        handler = _Handler()
        result = routes.handle_post(handler, SimpleNamespace(path=path, query=""))
        return result, handler

    return SimpleNamespace(get=get, post=post, state=state)


def _node(script: str, stdin: str = "") -> str:
    completed = subprocess.run(
        [NODE, "-e", script], input=stdin, capture_output=True, text=True,
        encoding="utf-8", timeout=60, cwd=str(REPO),
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return completed.stdout


def _cut(src: str, start: str, end: str) -> str:
    """Remove the one block that starts with ``start`` and ends with ``end``."""
    assert src.count(start) == 1, f"seam start not found exactly once: {start!r}"
    i = src.index(start)
    j = src.index(end, i)
    return src[:i] + src[j + len(end):]


def _js_function(src: str, name: str) -> str:
    """Brace-matched source of a top-level JS function (as the node drivers do)."""
    match = re.search(r"(?:async\s+)?function\s+" + re.escape(name) + r"\s*\(", src)
    assert match, name
    i = src.index("{", match.start()) + 1
    depth = 1
    while depth:
        depth += {"{": 1, "}": -1}.get(src[i], 0)
        i += 1
    return src[match.start():i]


# ── Fixtures and the notify policy fallback ─────────────────────────────────

def _pin(name):
    return (FIXTURES / name).read_text(encoding="utf-8").split()[0]


def test_notify_policy_fallback_is_the_pinned_engine_blob():
    blob = (REPO / "api" / "_notify_policy_fallback.py").read_bytes()
    assert hashlib.sha256(blob).hexdigest() == _pin("notify_policy.sha256")
    # Appendix A: standard library only, and the full public surface.
    tree = ast.parse(blob.decode("utf-8"))
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert imported <= set(sys.stdlib_module_names) | {"__future__"}, imported
    from api import _notify_policy_fallback as policy
    for name in ("normalize_notify", "resolve_notify", "default_notify_for_new_job", "should_deliver",
                 "in_app_flags", "combine_flags", "legacy_toast_value", "normalize_managed_by"):
        assert callable(getattr(policy, name)), name
    assert policy.OUTCOME_MUTED == "suppressed_muted"


def test_org_acme_fixture_matches_its_pin():
    data = (FIXTURES / "org_acme.yaml").read_bytes()
    assert hashlib.sha256(data).hexdigest() == _pin("org_acme.sha256")


# ── Stub modules answer exactly what the code did before ─────────────────────

def test_cron_notification_stubs_change_nothing(monkeypatch):
    from api import cron_notifications as cn

    payload, completion, job = {"id": "j"}, {"job_id": "j"}, {"id": "j"}
    assert cn.decorate_job(payload, viewer="a@example.test") is payload
    assert cn.decorate_completion(completion, job, viewer="a@example.test") is completion
    with pytest.raises(ValueError, match="^notify is not supported yet$"):
        cn.validate_notify_field({"in_app": "all"})
    assert cn.manual_run_kwargs(job, actor="a@example.test") == {}
    assert cn.delivery_decision(job, success=True, silent=False, default=True) == (True, None)
    assert cn.delivery_decision(job, success=False, silent=True, default=False) == (False, None)
    assert cn.handle_notifications_get(_Handler(), None) is False
    assert cn.handle_notifications_post(_Handler(), {}) is False

    calls = []
    jobs_mod = types.ModuleType("cron.jobs")
    jobs_mod.mark_job_run = lambda job_id, success, error=None, delivery_error=None: calls.append(
        (job_id, success, error, delivery_error))
    monkeypatch.setitem(sys.modules, "cron.jobs", jobs_mod)
    cn.record_manual_outcome("j", False, "boom", delivery_error="gone", outcome="ignored")
    assert calls == [("j", False, "boom", "gone")]
    # Engines whose mark_job_run takes no delivery_error keep working.
    jobs_mod.mark_job_run = lambda job_id, success, error=None: calls.append((job_id, success, error))
    cn.record_manual_outcome("j", True, None, delivery_error=None, outcome=None)
    assert calls[-1] == ("j", True, None)


def test_route_stubs_answer_404_405_or_204_and_store_nothing():
    from api import agui, help_events, mnemo_proxy, ops_reporter, org_api, webui_visuals

    assert org_api.handle_get(_Handler(), None) is False
    handler = _Handler()
    assert org_api.handle_post(handler, None, {"x": 1}) is True
    assert handler.status == 405 and handler.body == {"error": "Method not allowed"}
    assert agui.handle_replay(_Handler(), None) is False
    assert mnemo_proxy.handle_get(_Handler(), None) is False
    assert mnemo_proxy.handle_post(_Handler(), None, {}) is False
    for send in (lambda h: ops_reporter.handle_client_error(h, {"message": "x"}),
                 lambda h: help_events.handle_post(h, {"event": "tour_started"})):
        handler = _Handler()
        assert send(handler) is True
        assert handler.status == 204 and handler.raw == b""
        assert handler.header("Content-Length") == "0"
    assert ops_reporter.browser_reporting_enabled() is False
    assert webui_visuals.prompt_block() == ""
    assert webui_visuals.prompt_block({"webui_inline_svg": True}) == ""
    assert webui_visuals.visuals_enabled() is False


def test_group_routing_stubs_report_selected_bot_and_keep_nothing(monkeypatch):
    from api import group_chat

    monkeypatch.setattr(group_chat, "bot_allowed", lambda actor, bot: True)
    two = SimpleNamespace(bot_participants=["writer", "reviewer"])
    one = SimpleNamespace(bot_participants=["writer"])
    none = SimpleNamespace(bot_participants=[])
    assert group_chat.select_bot_with_reason(two, "@reviewer go", "a@example.test") == ("reviewer", "mention")
    assert group_chat.select_bot_with_reason(one, "@writer go", "a@example.test") == ("writer", "mention")
    assert group_chat.select_bot_with_reason(one, "Hello", "a@example.test") == ("writer", "only_bot")
    assert group_chat.select_bot_with_reason(none, "Hello", "a@example.test") == (None, None)
    for session, message in ((two, "Please work"), (two, "@admin go"), (one, "@other go")):
        with pytest.raises(ValueError) as expected:
            group_chat.selected_bot(session, message, "a@example.test")
        with pytest.raises(ValueError) as seam:
            group_chat.select_bot_with_reason(session, message, "a@example.test")
        assert str(seam.value) == str(expected.value)

    session = SimpleNamespace(bot_participants=["writer"], participants=["b@example.test"])
    before = dict(vars(session))
    assert group_chat.remember_route_reason("stream", "writer", "only_bot") is None
    assert group_chat.turn_started_extra(session, "writer") == {}
    assert group_chat.apply_participants_extra(session, {"default_bot": "writer"}, "a@example.test") is None
    assert vars(session) == before


# ── Route catalog and dispatch ───────────────────────────────────────────────

def test_catalog_classifies_every_wave1_route():
    for path in WAVE1_SELF_ROUTES:
        assert path in _SELF_ROUTES, path
        for method in ("GET", "POST"):
            assert route_permission(path, method) is None, path
    for method in ("GET", "POST"):
        assert route_permission("/api/agui/runs/abc123", method) == "sessions:read"
    # The notifications route is a self route even though /api/crons is cron:read.
    assert route_permission("/api/crons/other", "GET") == "cron:read"


def test_mnemo_routes_resolve_chat_use_and_unknown_children_fail_closed():
    for path in MNEMO_ROUTES:
        for method in ("GET", "POST"):
            assert route_permission(path, method) == "chat:use", (path, method)
    for path in ("/api/mnemo/unknown", "/api/mnemo", "/api/mnemo/me", "/api/mnemo/me/summary/x",
                 "/api/mnemo/me/memory"):
        for method in ("GET", "POST", "PUT", "DELETE"):
            assert route_permission(path, method) is None, (path, method)


def test_governance_decisions_for_the_new_routes(inject_policy):
    inject_policy(POLICY)
    member, outsider = _identity(MEMBER), _identity(OUTSIDER)
    for path in MNEMO_GET_ROUTES:
        assert evaluate_request(member, "GET", path).allow, path
        decision = evaluate_request(outsider, "GET", path)
        assert (decision.allow, decision.reason) == (False, "permission_not_allowed"), path
    for path in MNEMO_POST_ROUTES:
        assert evaluate_request(member, "POST", path).allow, path
    decision = evaluate_request(member, "GET", "/api/mnemo/unknown")
    assert (decision.allow, decision.reason) == (False, "unknown_route")
    for path in WAVE1_SELF_ROUTES:
        assert evaluate_request(outsider, "POST", path).allow, path
    assert evaluate_request(outsider, "GET", "/api/agui/runs/abc").allow
    assert not evaluate_request(None, "GET", "/api/org/overview").allow


def test_mnemo_routes_answer_404_for_a_chat_user(dispatch):
    for path in MNEMO_GET_ROUTES:
        result, handler = dispatch.get(path)
        assert result is False and handler.status is None, path
    for path in MNEMO_POST_ROUTES:
        result, handler = dispatch.post(path, {"id": "m1"})
        assert result is False and handler.status is None, path


def test_scaffold_routes_answer_their_stub_status(dispatch):
    for path in ("/api/crons/notifications", "/api/agui/runs/abc123") + ORG_ROUTES:
        result, handler = dispatch.get(path)
        assert result is False and handler.status is None, path
    result, handler = dispatch.post("/api/crons/notifications", {"job_id": "j", "in_app": None, "revision": 1})
    assert result is False and handler.status is None
    for path in ORG_ROUTES:
        result, handler = dispatch.post(path, {"x": 1})
        assert handler.status == 405, path
    for path in ("/api/client-errors", "/api/help/events"):
        result, handler = dispatch.post(path, {"message": "x"})
        assert result is not False and handler.status == 204 and handler.raw == b"", path


def test_stub_dispatch_calls_each_seam_with_the_request(dispatch, monkeypatch):
    from api import agui, cron_notifications, help_events, mnemo_proxy, ops_reporter, org_api

    seen = []

    def record(name, answer=False):
        def _fn(*args):
            seen.append((name, args[1:]))
            return answer
        return _fn

    monkeypatch.setattr(mnemo_proxy, "handle_get", record("mnemo_get"))
    monkeypatch.setattr(mnemo_proxy, "handle_post", record("mnemo_post"))
    monkeypatch.setattr(org_api, "handle_get", record("org_get"))
    monkeypatch.setattr(org_api, "handle_post", record("org_post"))
    monkeypatch.setattr(agui, "handle_replay", record("agui"))
    monkeypatch.setattr(cron_notifications, "handle_notifications_get", record("notify_get"))
    monkeypatch.setattr(cron_notifications, "handle_notifications_post", record("notify_post"))
    monkeypatch.setattr(ops_reporter, "handle_client_error", record("client_error"))
    monkeypatch.setattr(help_events, "handle_post", record("help"))

    dispatch.get("/api/mnemo/me/summary")
    dispatch.post("/api/mnemo/me/erase", {"confirm": "FORGET"})
    dispatch.get("/api/org/people")
    dispatch.post("/api/org/people", {"a": 1})
    dispatch.get("/api/agui/runs/st1")
    dispatch.get("/api/crons/notifications")
    dispatch.post("/api/crons/notifications", {"job_id": "j"})
    dispatch.post("/api/client-errors", {"m": 1})
    dispatch.post("/api/help/events", {"e": 1})
    names = [name for name, _ in seen]
    assert names == ["mnemo_get", "mnemo_post", "org_get", "org_post", "agui", "notify_get",
                     "notify_post", "client_error", "help"]
    assert seen[1][1][0].path == "/api/mnemo/me/erase" and seen[1][1][1] == {"confirm": "FORGET"}
    assert seen[4][1][0].path == "/api/agui/runs/st1"
    assert seen[6][1] == ({"job_id": "j"},)


def test_module_routes_are_self_routes_and_answer_404(dispatch):
    for method, path in MODULE_ROUTES:
        assert path in _SELF_ROUTES, path
        assert route_permission(path, method) is None, path
        result, handler = (dispatch.get(path) if method == "GET" else dispatch.post(path, {"module": "notebook"}))
        assert result is False and handler.status is None, path
    from api import apps_launcher, org_modules

    assert org_modules.handle_get(_Handler(), None) is False
    assert org_modules.handle_request(_Handler(), {"module": "notebook"}) is False
    assert apps_launcher.handle_get(_Handler(), None) is False


def test_module_route_dispatch_calls_each_stub_with_the_request(dispatch, monkeypatch):
    from api import apps_launcher, org_modules

    seen = []
    monkeypatch.setattr(org_modules, "handle_get", lambda h, parsed: seen.append(("org_get", parsed.path)) or False)
    monkeypatch.setattr(org_modules, "handle_request", lambda h, body: seen.append(("request", body)) or False)
    monkeypatch.setattr(apps_launcher, "handle_get", lambda h, parsed: seen.append(("apps", parsed.path)) or False)
    dispatch.get("/api/org/modules")
    dispatch.post("/api/org/modules/request", {"module": "notebook", "note": "x"})
    dispatch.get("/api/apps")
    assert seen == [("org_get", "/api/org/modules"), ("request", {"module": "notebook", "note": "x"}),
                    ("apps", "/api/apps")]


def test_modules_is_a_member_panel_without_a_permission_of_its_own():
    from api.governance.nav import MEMBER_PANELS, PANEL_PERMISSIONS

    assert "modules" in MEMBER_PANELS and "modules" not in PANEL_PERMISSIONS


# ── /api/settings ───────────────────────────────────────────────────────────

STANDARD_MODULES = ["workspace", "group_chat", "design_studio", "workflows"]
# Installation facts GET /api/settings adds after the settings filter (E.1,
# E.4.2 and E.5.2); nothing else in the response may change.
SETTINGS_FACTS = ("support_telemetry", "enabled_modules", "modules_source", "module_nav", "enabled_connections")


@pytest.fixture
def fresh_modules(monkeypatch):
    from api import modules

    monkeypatch.delenv("SP_ENABLED_MODULES", raising=False)
    monkeypatch.delenv("SP_ENABLED_CONNECTIONS", raising=False)
    modules.clear_cache()
    yield modules
    modules.clear_cache()


def test_settings_adds_only_the_managed_service_facts(dispatch, monkeypatch, fresh_modules):
    import api.routes as routes
    from api import ops_reporter

    _, handler = dispatch.get("/api/settings")
    assert handler.status == 200
    payload = handler.body
    assert payload["support_telemetry"] is False
    # E.4.2: always a list, the Standard set when SP_ENABLED_MODULES is unset.
    assert payload["enabled_modules"] == STANDARD_MODULES
    assert payload["modules_source"] == "default"
    assert payload["module_nav"] == {
        "hidden_panels": ["knowledge", "meetings"],
        "hidden_settings_sections": [],
        "hidden_composer_controls": [],
        "apps": [{"module": "design_studio", "app": "design"}, {"module": "workflows", "app": "workflows"}],
    }
    # E.5.2: always a list, empty unless SP_ENABLED_CONNECTIONS is set.
    assert payload["enabled_connections"] == []

    monkeypatch.setenv("SP_ENABLED_MODULES", "knowledge_base")
    monkeypatch.setenv("SP_ENABLED_CONNECTIONS", "assistant_knowledge,minutes_to_knowledge")
    monkeypatch.setattr(ops_reporter, "browser_reporting_enabled", lambda: True)
    _, handler = dispatch.get("/api/settings")
    changed = handler.body
    assert changed["support_telemetry"] is True
    assert changed["enabled_modules"] == STANDARD_MODULES + ["knowledge_base"]
    assert changed["modules_source"] == "env"
    assert changed["module_nav"]["hidden_panels"] == ["meetings"]
    assert changed["enabled_connections"] == ["assistant_knowledge"]
    # Everything else is what the handler returned before the seams.
    assert {k: v for k, v in changed.items() if k not in SETTINGS_FACTS} == \
        {k: v for k, v in payload.items() if k not in SETTINGS_FACTS}

    for garbage in ("", "Bad Id", "*"):
        monkeypatch.setenv("SP_ENABLED_MODULES", garbage)
        _, handler = dispatch.get("/api/settings")
        assert handler.body["enabled_modules"] == STANDARD_MODULES, garbage

    def broken():
        raise RuntimeError("reporter unavailable")

    monkeypatch.setattr(ops_reporter, "browser_reporting_enabled", broken)
    assert routes._support_telemetry_enabled() is False


def test_settings_save_drops_the_installation_facts(dispatch, monkeypatch, fresh_modules):
    import api.routes as routes

    seen = []
    monkeypatch.setattr(routes, "save_settings", lambda body: seen.append(dict(body)) or dict(body))
    import api.settings_scope as settings_scope

    monkeypatch.setattr(settings_scope, "settings_write_denial_for", lambda handler, body: seen.append(("check", dict(body))) and None)
    facts = {"enabled_modules": ["knowledge_base"], "modules_source": "hq", "module_nav": {"apps": []},
             "enabled_connections": ["module_map"]}
    dispatch.post("/api/settings", dict(facts, send_key="enter"))
    assert seen[0] == ("check", {"send_key": "enter"})
    assert seen[1] == {"send_key": "enter"}
    assert set(routes._SETTINGS_READ_ONLY_FACTS) >= set(facts)


# ── Cron notify seams ─────────────────────────────────────────────────────────

class _CronStore:
    def __init__(self):
        self.jobs = {
            "own": {"id": "own", "name": "Own", "prompt": "p", "schedule": {"kind": "interval", "minutes": 60},
                    "deliver": "local", "owner_email": OWNER,
                    "origin": {"platform": "webui", "chat_id": "s", "user_id": OWNER}},
        }
        self.creates, self.updates = [], []

    def module(self):
        store = self
        mod = types.ModuleType("cron.jobs")

        def get_job(job_id):
            job = store.jobs.get(job_id)
            return copy.deepcopy(job) if job else None

        def update_job(job_id, updates):
            store.updates.append((job_id, copy.deepcopy(updates)))
            store.jobs[job_id].update(copy.deepcopy(updates))
            return copy.deepcopy(store.jobs[job_id])

        def create_job(**kwargs):
            store.creates.append(kwargs)
            job = {"id": "new", "name": kwargs.get("name") or "new", "prompt": kwargs["prompt"],
                   "schedule": kwargs["schedule"], "owner_email": kwargs.get("owner_email") or ""}
            store.jobs["new"] = job
            return copy.deepcopy(job)

        mod.get_job, mod.update_job, mod.create_job = get_job, update_job, create_job
        return mod


@pytest.fixture
def cron_env(dispatch, monkeypatch):
    import api.profiles as profiles
    import api.routes as routes

    store = _CronStore()
    cron_pkg = types.ModuleType("cron")
    cron_pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "cron", cron_pkg)
    monkeypatch.setitem(sys.modules, "cron.jobs", store.module())
    monkeypatch.setitem(sys.modules, "cron.scheduler", types.ModuleType("cron.scheduler"))
    monkeypatch.setattr(routes, "_get_active_profile_name", lambda: "default")
    monkeypatch.setattr(routes, "_ensure_agent_cron_import_path", lambda: None)
    monkeypatch.setattr(profiles, "cron_profile_context", nullcontext)
    return SimpleNamespace(store=store, post=dispatch.post)


def test_notify_field_answers_400_until_w1_and_writes_nothing(cron_env):
    _, handler = cron_env.post("/api/crons/update", {"job_id": "own", "notify": {"in_app": "failures"}}, email=OWNER)
    assert handler.status == 400 and handler.body == {"error": "notify is not supported yet"}
    _, handler = cron_env.post("/api/crons/create", {"prompt": "p", "schedule": "every 1h", "notify": {}}, email=OWNER)
    assert handler.status == 400 and handler.body == {"error": "notify is not supported yet"}
    # Ownership is still decided first: a foreign task is refused as before.
    _, handler = cron_env.post("/api/crons/update", {"job_id": "own", "notify": {"in_app": "off"}}, email=OTHER)
    assert handler.status == 403
    assert cron_env.store.updates == [] and cron_env.store.creates == []


def test_notify_seam_writes_the_validated_value_and_its_toast_mirror(cron_env, monkeypatch):
    from api import cron_notifications

    monkeypatch.setattr(cron_notifications, "validate_notify_field",
                        lambda value: {"in_app": value["in_app"], "delivery": "all"})
    _, handler = cron_env.post("/api/crons/update", {
        "job_id": "own", "notify": {"in_app": "quiet"}, "toast_notifications": True, "name": "Renamed",
    }, email=OWNER)
    assert handler.status == 200, handler.body
    assert cron_env.store.updates == [("own", {
        "toast_notifications": False, "name": "Renamed", "notify": {"in_app": "quiet", "delivery": "all"},
    })]
    _, handler = cron_env.post("/api/crons/create", {
        "prompt": "p", "schedule": "every 1h", "notify": {"in_app": "failures"},
    }, email=OWNER)
    assert handler.status == 200, handler.body
    job_id, updates = cron_env.store.updates[-1]
    assert job_id == "new"
    assert updates["notify"] == {"in_app": "failures", "delivery": "all"}
    assert updates["toast_notifications"] is True


def test_job_payloads_pass_the_viewer_to_the_notify_seam(monkeypatch):
    import api.governance.enforce as enforce
    import api.routes as routes
    from api import cron_notifications

    job = {"id": "j", "name": "J"}
    plain = routes._cron_job_for_api(job)
    assert plain == routes._cron_jobs_for_api([job], viewer="v@example.test")[0]
    seen = []

    def decorate(payload, viewer=None):
        seen.append(viewer)
        return {**payload, "my_notify": None}

    monkeypatch.setattr(cron_notifications, "decorate_job", decorate)
    assert routes._cron_jobs_for_api([job], viewer="v@example.test")[0] == {**plain, "my_notify": None}
    assert seen == ["v@example.test"]

    def broken(payload, viewer=None):
        raise RuntimeError("seam failed")

    monkeypatch.setattr(cron_notifications, "decorate_job", broken)
    assert routes._cron_job_for_api(job, viewer="v@example.test") == plain

    monkeypatch.setattr(enforce, "_request_identity", lambda handler: _identity("V@Example.test"))
    assert routes._cron_request_email(_Handler()) == "v@example.test"
    branch = inspect.getsource(routes.handle_get)
    branch = branch[branch.index('if parsed.path == "/api/crons":'):branch.index('if parsed.path == "/api/crons/output":')]
    assert "viewer=_cron_request_email(handler)" in branch


def test_recent_completions_pass_through_the_notify_seam(monkeypatch):
    import api.cron_scope as cron_scope
    import api.governance.enforce as enforce
    import api.routes as routes
    from api import cron_notifications

    jobs_mod = types.ModuleType("cron.jobs")
    jobs_mod.list_jobs = lambda include_disabled=True: [
        {"id": "a", "name": "A", "last_run_at": 200.0, "last_status": "ok"},
        {"id": "b", "name": "B", "last_run_at": 50.0, "last_status": "ok"},
    ]
    monkeypatch.setitem(sys.modules, "cron.jobs", jobs_mod)
    monkeypatch.setattr(cron_scope, "scope_cron_completions_for_caller", lambda handler, jobs: jobs)
    monkeypatch.setattr(routes, "_latest_cron_session_info_for_jobs", lambda ids, done: {})
    monkeypatch.setattr(enforce, "_request_identity", lambda handler: _identity(MEMBER))

    def recent():
        handler = _Handler()
        routes._handle_cron_recent(handler, SimpleNamespace(query="since=100"))
        return handler.body

    before = recent()
    assert [c["job_id"] for c in before["completions"]] == ["a"]
    seen = []

    def decorate(completion, job, viewer=None):
        seen.append((job["id"], viewer))
        return {**completion, "toast": True}

    monkeypatch.setattr(cron_notifications, "decorate_completion", decorate)
    after = recent()
    assert seen == [("a", MEMBER)]
    assert after["completions"] == [{**before["completions"][0], "toast": True}]


def _install_run_fakes(monkeypatch, calls):
    jobs_mod = types.ModuleType("cron.jobs")
    jobs_mod.save_job_output = lambda job_id, output: calls.append(("save", job_id, output))
    jobs_mod.mark_job_run = lambda job_id, success, error=None, delivery_error=None: calls.append(
        ("mark", job_id, success, error, delivery_error))
    scheduler = types.ModuleType("cron.scheduler")
    scheduler.SILENT_MARKER = "[SILENT]"
    scheduler._deliver_result = lambda job, content: calls.append(("deliver", job["id"], content)) or None
    monkeypatch.setitem(sys.modules, "cron.jobs", jobs_mod)
    monkeypatch.setitem(sys.modules, "cron.scheduler", scheduler)


def test_manual_run_seams_are_neutral_until_filled(monkeypatch):
    import api.routes as routes
    from api import cron_notifications

    calls, decisions = [], []
    _install_run_fakes(monkeypatch, calls)
    monkeypatch.setattr(routes, "_run_cron_job_in_profile_subprocess",
                        lambda job, execution_profile_home: (True, "out", "[SILENT] nothing new", None))
    real_decision = cron_notifications.delivery_decision
    monkeypatch.setattr(cron_notifications, "delivery_decision",
                        lambda job, **kw: decisions.append(kw) or real_decision(job, **kw))
    routes._mark_cron_running("quiet-job")
    routes._run_cron_tracked({"id": "quiet-job"}, actor=MEMBER)
    assert calls == [("save", "quiet-job", "out"), ("mark", "quiet-job", True, None, None)]
    assert decisions == [{"success": True, "silent": True, "default": False}]
    assert routes._is_cron_running("quiet-job") == (False, 0.0)


def test_manual_run_seams_are_wired_when_filled(monkeypatch):
    import api.routes as routes
    from api import cron_notifications

    calls, received, outcomes = [], [], []
    _install_run_fakes(monkeypatch, calls)

    def run(job, execution_profile_home, run_kwargs=None):
        received.append(run_kwargs)
        return True, "out", "done", None

    monkeypatch.setattr(routes, "_run_cron_job_in_profile_subprocess", run)
    monkeypatch.setattr(cron_notifications, "manual_run_kwargs",
                        lambda job, actor=None: {"trigger": "manual", "trigger_actor": actor})
    monkeypatch.setattr(cron_notifications, "delivery_decision",
                        lambda job, *, success, silent, default: (False, "suppressed_muted"))
    monkeypatch.setattr(cron_notifications, "record_manual_outcome",
                        lambda job_id, success, error, *, delivery_error=None, outcome=None:
                        outcomes.append((job_id, success, error, delivery_error, outcome)))
    routes._mark_cron_running("muted-job")
    routes._run_cron_tracked({"id": "muted-job"}, actor=MEMBER)
    assert received == [{"trigger": "manual", "trigger_actor": MEMBER}]
    assert calls == [("save", "muted-job", "out")]  # nothing delivered
    assert outcomes == [("muted-job", True, None, None, "suppressed_muted")]


def test_subprocess_passes_only_the_run_job_kwargs_the_engine_takes(monkeypatch):
    import api.routes as routes

    seen = []
    scheduler = types.ModuleType("cron.scheduler")

    def run_job(job, trigger=None):
        seen.append((job["id"], trigger))
        return True, "o", "f", None

    scheduler.run_job = run_job
    monkeypatch.setitem(sys.modules, "cron.scheduler", scheduler)
    queue = SimpleNamespace(items=[], put=lambda item: queue.items.append(item))
    routes._cron_job_subprocess_main({"id": "j"}, None, queue, run_kwargs={"trigger": "manual", "run_prompt": "x"})
    routes._cron_job_subprocess_main({"id": "k"}, None, queue)
    assert seen == [("j", "manual"), ("k", None)]
    assert [item[0] for item in queue.items] == ["ok", "ok"]
    assert routes._cron_run_job_kwargs(lambda job, **kw: None, {"a": 1}) == {"a": 1}
    assert routes._cron_run_job_kwargs(run_job, None) == {}


def test_run_now_passes_the_session_email_as_actor(cron_env, monkeypatch):
    import api.routes as routes
    import api.cron_scope as cron_scope

    started = threading.Event()
    seen = []

    def tracked(job, profile_home=None, execution_profile_home=None, event_profile=None, run_plan=None,
                actor=None):
        seen.append((job["id"], actor))
        routes._mark_cron_done(job["id"])
        started.set()

    monkeypatch.setattr(routes, "_run_cron_tracked", tracked)
    monkeypatch.setattr(cron_scope, "caller_may_act_on_cron_job", lambda *a, **k: True)
    _, handler = cron_env.post("/api/crons/run", {"job_id": "own", "actor": "forged@example.test"}, email=OWNER)
    assert handler.status == 200, handler.body
    assert started.wait(5)
    assert seen == [("own", OWNER)]


# ── Group chat seams in the chat path ────────────────────────────────────────

def test_peer_turn_frame_is_unchanged_and_carries_the_bot_to_the_seam(monkeypatch):
    from api import background_process, group_chat, routes

    events = []
    channel = SimpleNamespace(emit=lambda event, data: events.append((event, data)) or 1)
    monkeypatch.setattr(background_process, "get_session_channel", lambda sid: channel)
    session = SimpleNamespace(session_id="s1", participants=["bob@example.test"], bot_participants=["writer"],
                              pending_started_at=1.5)
    response = routes._ChatStartResponse({"stream_id": "st", "pending_started_at": 2.5})
    response.execution_profile = "writer"
    assert json.loads(json.dumps(response)) == {"stream_id": "st", "pending_started_at": 2.5}
    assert routes._fan_out_peer_turn(session, response, "Alice@Example.test", "hi", [])
    assert events[-1] == ("peer_turn_started", {
        "session_id": "s1", "stream_id": "st", "sender_email": "alice@example.test",
        "message": "hi", "attachments": [], "pending_started_at": 2.5,
    })
    seen = []
    monkeypatch.setattr(group_chat, "turn_started_extra",
                        lambda s, bot: seen.append(bot) or {"bot": bot, "route_reason": "only_bot"})
    routes._fan_out_peer_turn(session, response, "a@example.test", "hi", [])
    assert seen == ["writer"] and events[-1][1]["bot"] == "writer"
    monkeypatch.setattr(group_chat, "turn_started_extra", lambda s, bot: 1 / 0)
    assert routes._fan_out_peer_turn(session, {"stream_id": "st"}, "a@example.test", "hi", [])
    assert "bot" not in events[-1][1]


def test_chat_start_uses_the_routing_seams_in_order():
    from api import routes

    src = inspect.getsource(routes._start_chat_stream_for_session)
    assert "selected_bot(" not in src
    assert "_group_chat.select_bot_with_reason(" in src
    registered = src.index("STREAMS[stream_id] = stream")
    remembered = src.index("_group_chat.remember_route_reason(stream_id, execution_profile, route_reason)")
    assert registered < remembered < src.index("thr.start()")
    assert "response.execution_profile = execution_profile" in src


def test_participants_seam_runs_after_validation_and_before_save(monkeypatch, dispatch):
    import api.routes as routes
    from api import group_chat

    saved = []

    class _Session:
        session_id = "g1"
        owner_email = MEMBER
        participants = []
        bot_participants = []
        profile = None
        project_id = None

        def save(self):
            saved.append((list(self.participants), getattr(self, "default_bot", None)))

    session = _Session()
    monkeypatch.setattr(routes, "get_session", lambda sid, **kw: session)
    monkeypatch.setattr(routes, "_session_is_subagent_view_only", lambda sid: False)
    monkeypatch.setattr(routes, "_session_visible_to_request", lambda s, handler=None: True)
    monkeypatch.setattr(routes, "_group_participants_may_be_managed_by", lambda s, handler: True)
    monkeypatch.setattr(routes, "_audit_group_participants", lambda *a, **k: None)
    monkeypatch.setattr(routes, "_on_session_list_changed", lambda *a, **k: None)
    monkeypatch.setattr(routes, "publish_session_list_changed", lambda *a, **k: None)
    monkeypatch.setattr(group_chat, "validate", lambda values, owner_email=None: (["bob@example.test"], None))
    monkeypatch.setattr(group_chat, "validate_bots", lambda values, actor: ["writer"])

    body = {"session_id": "g1", "participants": ["bob@example.test"], "bot_participants": ["writer"]}
    _, handler = dispatch.post("/api/session/participants", body)
    assert handler.status == 200, handler.body
    assert saved == [(["bob@example.test"], None)]

    seen = []

    def extra(s, request_body, actor):
        seen.append((request_body.get("default_bot"), actor))
        s.default_bot = request_body["default_bot"]

    monkeypatch.setattr(group_chat, "apply_participants_extra", extra)
    _, handler = dispatch.post("/api/session/participants", {**body, "default_bot": "writer"})
    assert handler.status == 200 and seen == [("writer", MEMBER)]
    assert saved[-1] == (["bob@example.test"], "writer")

    def refuse(s, request_body, actor):
        raise ValueError("default_bot must be one of the bots")

    monkeypatch.setattr(group_chat, "apply_participants_extra", refuse)
    _, handler = dispatch.post("/api/session/participants", {**body, "default_bot": "nobody"})
    assert handler.status == 400 and handler.body["error"] == "default_bot must be one of the bots"
    assert len(saved) == 2


# ── Runtime prompt (addendum AE-5) ───────────────────────────────────────────

_PROMPT_SEAM_START = "    # Visual answers (plan addendum AE-5)"
_PROMPT_SEAM_END = "        parts.append(visuals_prompt)\n"


def _pre_scaffold_prompt_builder():
    from api import streaming

    src = textwrap.dedent(inspect.getsource(streaming._webui_ephemeral_system_prompt))
    pre = _cut(src, _PROMPT_SEAM_START, _PROMPT_SEAM_END)
    assert "webui_visuals" not in pre
    namespace = dict(vars(streaming))
    exec(compile(pre, "pre_scaffold_prompt", "exec"), namespace)
    return namespace["_webui_ephemeral_system_prompt"]


@pytest.mark.parametrize("args", [
    ("Keep the selected tone.", None, {}, None),
    (None, {"session_id": "s1"}, {"webui_inline_svg": True}, None),
])
def test_ephemeral_prompt_equals_the_pre_scaffold_output(args):
    from api import streaming

    pre = _pre_scaffold_prompt_builder()
    assert streaming._webui_ephemeral_system_prompt(*args) == pre(*args)


def test_visuals_prompt_seam_is_wired(monkeypatch):
    from api import streaming, webui_visuals

    baseline = streaming._webui_ephemeral_system_prompt("Tone.", None, {}, None)
    monkeypatch.setattr(webui_visuals, "prompt_block", lambda config_data=None: "VISUALS BLOCK")
    prompt = streaming._webui_ephemeral_system_prompt("Tone.", None, {}, None)
    assert streaming._WEBUI_ARTIFACT_DELIVERY_PROMPT + "\n\nVISUALS BLOCK" in prompt

    def broken(config_data=None):
        raise RuntimeError("visuals unavailable")

    monkeypatch.setattr(webui_visuals, "prompt_block", broken)
    assert streaming._webui_ephemeral_system_prompt("Tone.", None, {}, None) == baseline


# ── Static assets ────────────────────────────────────────────────────────────

def test_placeholders_exist_as_one_comment_line():
    for path in JS_PLACEHOLDERS:
        lines = (REPO / path).read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1 and lines[0].startswith("// "), path
    for path in CSS_PLACEHOLDERS:
        lines = (REPO / path).read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1 and lines[0].startswith("/* ") and lines[0].endswith(" */"), path


@needs_node
def test_js_placeholders_define_no_globals():
    script = r"""
const fs=require('fs'),vm=require('vm');
const out={};
let data='';process.stdin.on('data',c=>data+=c);process.stdin.on('end',()=>{
  for(const path of JSON.parse(data)){
    const ctx={window:{}};ctx.self=ctx.window;vm.createContext(ctx);
    const before=new Set(Object.getOwnPropertyNames(ctx));
    vm.runInContext(fs.readFileSync(path,'utf8'),ctx);
    out[path]=Object.getOwnPropertyNames(ctx).filter(n=>!before.has(n)).concat(Object.keys(ctx.window));
  }
  process.stdout.write(JSON.stringify(out));
});
"""
    added = json.loads(_node(script, json.dumps(list(JS_PLACEHOLDERS))))
    assert added == {path: [] for path in JS_PLACEHOLDERS}
    for path in JS_PLACEHOLDERS:
        text = (REPO / path).read_text(encoding="utf-8")
        for name in SEAM_GLOBALS:
            assert name not in text, (path, name)


def test_index_html_loads_the_scaffold_assets_in_place():
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    def tag(path):
        if path.endswith(".css"):
            return f'<link rel="stylesheet" href="static/{path}?v=__WEBUI_VERSION__">'
        return f'<script src="static/{path}?v=__WEBUI_VERSION__" defer></script>'

    def at(path):
        assert html.count(tag(path)) == 1, path
        return html.index(tag(path))

    head_end = html.index("</head>")
    for css in ("cron-notify.css", "help-tour.css", "group-routing.css"):
        assert at("bot-builder.css") < at(css) < head_end, css
    # Addendum AE-6: immediately before ui.js, immediately after panels.js.
    assert tag("svg_visuals.css") + "\n" + tag("svg_visuals.js") + "\n" + tag("ui.js") in html
    assert tag("panels.js") + "\n" + tag("memory_inventory.css") + "\n" + tag("memory_inventory.js") in html
    boot = at("boot.js")
    for script in ("vendor/guida/0.2.0/guida.umd.js", "help-content.js", "help-tour.js", "error-reporter.js"):
        assert at(script) < boot, script


def test_module_placeholders_define_only_their_documented_no_ops():
    css = (REPO / "static/modules.css").read_text(encoding="utf-8").splitlines()
    assert len(css) == 1 and css[0].startswith("/* ") and css[0].endswith(" */")
    for path in ("static/modules.js", "static/module-content.js"):
        lines = (REPO / path).read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2 and lines[0].startswith("// "), path


@needs_node
def test_module_placeholders_reveal_nothing():
    script = r"""
const fs=require('fs'),vm=require('vm');
const ctx={window:{}};ctx.self=ctx.window;vm.createContext(ctx);
for(const path of ['static/module-content.js','static/modules.js'])vm.runInContext(fs.readFileSync(path,'utf8'),ctx);
const w=ctx.window;
const applied=w.SynthPulseModules.apply({enabled_modules:['knowledge_base']});
process.stdout.write(JSON.stringify({keys:Object.keys(w).sort(),apps:Object.keys(w.SynthPulseModules),
  applied:applied===undefined,content:w.SynthPulseModuleContent}));
"""
    out = json.loads(_node(script))
    assert out == {"keys": ["SynthPulseModuleContent", "SynthPulseModules"], "apps": ["apply"], "applied": True,
                   "content": {"version": 1, "locales": {"en": {}, "nl": {}}}}


def test_module_surfaces_start_hidden_in_the_markup():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    gated = re.findall(r"<[a-z]+\b[^>]*\bdata-module-gated\b[^>]*>", html)
    assert len(gated) == 3, gated
    for tag in gated:
        assert re.search(r"\shidden(\s|>)", tag), tag
    nav = [tag for tag in gated if 'data-panel="modules"' in tag]
    assert len(nav) == 2 and any("rail-btn" in tag for tag in nav)
    assert sum('id="btnApps"' in tag for tag in gated) == 1
    assert html.count('<div class="panel-view" id="panelModules"></div>') == 1
    style = (STATIC / "style.css").read_text(encoding="utf-8")
    assert "[data-module-gated][hidden]{display:none!important;}" in style

    def tag(path):
        if path.endswith(".css"):
            return f'<link rel="stylesheet" href="static/{path}?v=__WEBUI_VERSION__">'
        return f'<script src="static/{path}?v=__WEBUI_VERSION__" defer></script>'

    for path in ("modules.css", "module-content.js", "modules.js"):
        assert html.count(tag(path)) == 1, path
    assert html.index(tag("modules.css")) < html.index("</head>")
    panels, boot = html.index(tag("panels.js")), html.index(tag("boot.js"))
    assert panels < html.index(tag("module-content.js")) < html.index(tag("modules.js")) < boot


def test_panels_js_carries_the_module_seams():
    src = (STATIC / "panels.js").read_text(encoding="utf-8")
    assert "window._moduleHiddenNav = window._moduleHiddenNav || [];" in src
    order = re.search(r"const _MEMBER_NAV_ORDER = \[([^\]]*)\]", src).group(1)
    assert "'modules'" in order
    start = src.index("async function switchPanel(name, opts = {}) {")
    assert "const nextPanel = _panelGatedByModule(name || 'chat') ? 'chat' : (name || 'chat');" in src[start:start + 200]
    assert "window._moduleHiddenNav" in _js_function(src, "_applyTabVisibility")
    assert "[data-module-gated][data-panel=" in _js_function(src, "_renderTabVisibilityChips")


@needs_node
def test_switch_panel_falls_back_to_chat_for_a_module_panel():
    src = (STATIC / "panels.js").read_text(encoding="utf-8")
    script = _js_function(src, "_panelGatedByModule") + r"""
const gated=new Set(['modules']);
globalThis.window={_moduleHiddenNav:['knowledge']};
globalThis.document={querySelector:(sel)=>{const m=/data-panel="([^"]+)"/.exec(sel);return m&&gated.has(m[1])?{}:null;}};
const out={};
for(const p of ['chat','settings','tasks','modules','knowledge','meetings',''])out[p]=_panelGatedByModule(p);
window._moduleHiddenNav='junk';out.junk=_panelGatedByModule('knowledge');
process.stdout.write(JSON.stringify(out));
"""
    out = json.loads(_node(script))
    assert out == {"chat": False, "settings": False, "tasks": False, "modules": True, "knowledge": True,
                   "meetings": False, "": False, "junk": False}


def test_service_worker_precaches_every_scaffold_asset():
    sw = (STATIC / "sw.js").read_text(encoding="utf-8")
    shell = sw[sw.index("const SHELL_ASSETS"):sw.index("];", sw.index("const SHELL_ASSETS"))]
    for path in JS_PLACEHOLDERS + CSS_PLACEHOLDERS + MODULE_PLACEHOLDERS:
        entry = "'./" + path + "' + VQ,"
        assert shell.count(entry) == 1, path
        assert (REPO / path).is_file(), path


def test_every_shell_asset_exists():
    """cache.addAll fails on one missing file, so every entry must exist."""
    sw = (STATIC / "sw.js").read_text(encoding="utf-8")
    shell = sw[sw.index("const SHELL_ASSETS"):sw.index("];", sw.index("const SHELL_ASSETS"))]
    for rel in re.findall(r"'\./(static/[^']+)'", shell):
        assert (REPO / rel).is_file(), rel


# ── i18n ─────────────────────────────────────────────────────────────────────

def _locale_values(code, keys=I18N_KEYS):
    """The scaffold keys of one locale bundle, read from its source.

    The scaffold writes each key once as a plain single-quoted string, so the
    literal is parsed directly (the bundles need the i18n.js helpers to run).
    """
    text = (STATIC / "i18n" / f"{code}.js").read_text(encoding="utf-8")
    values = {}
    for key in keys:
        found = re.findall(r"^[ \t]*" + key + r"[ \t]*:[ \t]*('(?:[^'\\\n]|\\.)*'),?[ \t]*$", text, re.M)
        assert len(found) == 1, (code, key, found)
        values[key] = ast.literal_eval(found[0])
    return values


def test_scaffold_i18n_keys_are_in_every_locale_with_the_english_value():
    assert len(I18N_KEYS) == 115 and len(set(I18N_KEYS)) == 115
    english = _locale_values("en")
    assert all(isinstance(value, str) and value for value in english.values())
    assert english["svg_drawing"] == "Drawing visual\u2026"
    assert english["help_tour_step_of"] == "Step {0} of {1}"
    assert english["help_whats_new_title"] == "What's new"
    assert english["mnemo_forget_all_type"] == "Type FORGET to confirm"
    assert english["cron_notify_me_off_admin"] == "Off (admin setting)"
    for code in LOCALES:
        assert _locale_values(code) == english, code
    for value in english.values():
        assert "\u2013" not in value and "\u2014" not in value


def test_seam_i18n_keys_are_in_every_locale_with_the_english_value():
    assert len(SEAM_I18N) == len(set(SEAM_I18N)) and not set(SEAM_I18N) & set(I18N_KEYS)
    for code in LOCALES:
        assert _locale_values(code, tuple(SEAM_I18N)) == SEAM_I18N, code
    for value in SEAM_I18N.values():
        assert "\u2013" not in value and "\u2014" not in value
    from api.modules import DISPLAY_DENYLIST
    for key, value in SEAM_I18N.items():
        for denied in DISPLAY_DENYLIST + NETWORK_IDENTITY_NAMES:
            assert denied.lower() not in value.lower(), (key, denied)


@needs_node
def test_locale_bundles_still_register_in_the_browser_loader():
    """The appended keys keep every bundle loadable by static/i18n.js."""
    from tests._i18n_source import monolithic_i18n_source

    script = r"""
const vm=require('vm');
let data='';process.stdin.on('data',c=>data+=c);process.stdin.on('end',()=>{
  const store={};
  const ctx={console,navigator:{language:'en',languages:['en']},
    localStorage:{getItem:k=>store[k]??null,setItem:(k,v)=>{store[k]=String(v);},removeItem:k=>{delete store[k];}},
    document:{documentElement:{lang:''},querySelectorAll:()=>[],querySelector:()=>null,addEventListener:()=>{}}};
  ctx.window=ctx;vm.createContext(ctx);vm.runInContext(data+';globalThis.__L=LOCALES;',ctx);
  const out={};for(const [code,bundle] of Object.entries(ctx.__L))out[code]=[bundle.svg_drawing,bundle.mnemo_hub_down];
  process.stdout.write(JSON.stringify(out));
});
"""
    out = json.loads(_node(script, monolithic_i18n_source()))
    assert sorted(out) == sorted(LOCALES)
    assert set(map(tuple, out.values())) == {("Drawing visual\u2026",
                                              "The memory service is not reachable right now. Try again later.")}


# ── Chat renderer (addendum AE-1 to AE-4) ────────────────────────────────────

_RENDER_CORPUS = [
    "```svg\n<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 10 10\"><rect width=\"10\" height=\"10\"/></svg>\n```",
    "Intro\n\n```xml\n<svg viewBox=\"0 0 4 4\"><circle r=\"2\"/></svg>\n```\n\nAfter",
    "```SVG\n<svg></svg>\n```",
    "```\n<svg></svg>\n```\n\n$$x^2$$ and `<svg>` inline",
    "Here is a picture: <svg viewBox=\"0 0 4 4\"><circle cx=\"2\" cy=\"2\" r=\"2\"/></svg> and text",
    "<svg width=\"20\" height=\"20\">\n  <g><path d=\"M0 0L10 10\"/></g>\n</svg>\n\nNext paragraph with `code` and **bold**",
    "Two <svg><rect/></svg> runs <svg><circle/></svg> in one line",
    "<div class=\"svg-visual-block\" data-svg-id=\"svg-evil\">&lt;svg onload=alert(1)&gt;</div>",
    "<div class=\"svg-visual-block\">x</div>\n\n```mermaid\ngraph TD\nA-->B\n```",
    "> quoted\n> ```svg\n> <svg></svg>\n> ```\n\nplain",
    "MEDIA:/tmp/pic.svg then <svg><text>MEDIA:x</text></svg>",
    "| a | b |\n|---|---|\n| <svg></svg> | 2 |",
    "```diff\n+ <svg>\n- </svg>\n```",
    "```json\n{\"svg\": \"<svg/>\"}\n```",
    "<SVG viewBox=\"0 0 1 1\"></SVG> upper case",
    "",
]

_RENDER_DRIVER = r"""
const vm=require('vm');
let data='';process.stdin.on('data',c=>data+=c);process.stdin.on('end',()=>{
  const {sources,corpus,hooks}=JSON.parse(data);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function build(src){
    const ctx={esc,console,
      _inlineMediaHtmlForRef:r=>`<img class="msg-media-img" src="api/media?path=${encodeURIComponent(String(r||''))}" alt="image" loading="lazy">`,
      _sessionUrlForSid:sid=>'/app/session/'+encodeURIComponent(String(sid||'')),
      window:{},document:{createElement:()=>({innerHTML:'',textContent:''}),baseURI:'http://localhost/app/'}};
    vm.createContext(ctx);
    // Deterministic placeholder ids: the seams draw them from Math.random.
    vm.runInContext('var __seed=0;Math.random=()=>((++__seed)*0.1234567)%1;\n'+src+'\n;'+(hooks||''),ctx);
    return c=>{vm.runInContext('__seed=0',ctx);return ctx.renderMd(c);};
  }
  const out={};
  for(const [name,src] of Object.entries(sources)){const r=build(src);out[name]=corpus.map(c=>r(c));}
  process.stdout.write(JSON.stringify(out));
});
"""

_AE1_CALL = "    if(_svgVisualFenceAccepts(lang,code)) return lead+_svgVisualPlaceholder(code);\n"
_AE2_CALL = "  s=_svgVisualRawRuns(s);\n"
_AE12_HELPERS = ("\n  // ── Inline SVG visuals seams (plan addendum AE-1, AE-2)", "    return s;\n  }\n")
_AE3_COMMENT = ("  // The svg-visual-block alternation (plan addendum AE-3) only ever matches\n"
                "  // placeholders built above: _tag strips that class from raw HTML.\n")
_AE3_ALTERNATION = '|<div class="svg-visual-block"[\\s\\S]*?<\\/div>/g'


def _renderer_sources():
    ui = (STATIC / "ui.js").read_text(encoding="utf-8")
    helpers = _js_function(ui, "_matchBacktickFenceLine") + "\n" + _js_function(ui, "_isBacktickFenceClose")
    render = _js_function(ui, "renderMd")
    assert "(mermaid-block|katex-block)" in render
    for call in (_AE1_CALL, _AE2_CALL):
        assert render.count(call) == 1, call
    pre = render.replace(_AE1_CALL, "").replace(_AE2_CALL, "")
    pre = _cut(pre, *_AE12_HELPERS)
    assert pre.count(_AE3_COMMENT) == 1 and pre.count(_AE3_ALTERNATION) == 1
    pre = pre.replace(_AE3_COMMENT, "").replace(_AE3_ALTERNATION, "/g")
    assert "svg-visual" not in pre and "svgVisual" not in pre
    return {"scaffold": helpers + "\n" + render, "pre_scaffold": helpers + "\n" + pre}


def _render(corpus, hooks=""):
    payload = {"sources": _renderer_sources(), "corpus": corpus, "hooks": hooks}
    return json.loads(_node(_RENDER_DRIVER, json.dumps(payload)))


_INERT_HOOKS = {
    "absent": "",
    "not_exactly_true": (
        "var svgVisualFenceAccepts=(lang,code)=>lang==='svg'?'yes':1;"
        "var svgVisualRawSpans=s=>[[-1,5],[3,2],[0.5,4],'x',[0,s.length+1],[0,3],null,[2,2]];"
    ),
    "throwing": (
        "var svgVisualFenceAccepts=()=>{throw new Error('fence');};"
        "var svgVisualRawSpans=()=>{throw new Error('spans');};"
    ),
    "not_an_array": "var svgVisualRawSpans=s=>({0:[0,s.length]});",
}


@needs_node
@pytest.mark.parametrize("mode", sorted(_INERT_HOOKS))
def test_render_md_is_byte_identical_to_the_pre_scaffold_renderer(mode):
    out = _render(_RENDER_CORPUS, _INERT_HOOKS[mode])
    for case, new, old in zip(_RENDER_CORPUS, out["scaffold"], out["pre_scaffold"], strict=True):
        assert new == old, case
    # The raw class never survives from model output.
    assert 'class="svg-visual-block"' not in "".join(out["scaffold"])


@needs_node
def test_fence_seam_builds_an_escaped_placeholder_only_for_exact_true():
    corpus = [
        "```svg\n<svg onload=\"x()\"><rect/></svg>\n```",
        "```xml\n<svg></svg>\n```",
    ]
    out = _render(corpus, "var svgVisualFenceAccepts=(lang,code)=>lang==='svg'&&code.includes('<svg');")
    svg, xml = out["scaffold"]
    assert re.fullmatch(
        r'<div class="svg-visual-block" data-svg-id="svg-[a-z0-9]{1,8}">'
        r'&lt;svg onload=&quot;x\(\)&quot;&gt;&lt;rect/&gt;&lt;/svg&gt;</div>', svg), svg
    assert xml == out["pre_scaffold"][1]


@needs_node
def test_raw_span_seam_takes_only_valid_non_overlapping_runs():
    text = "Before <svg><rect/></svg> middle <svg><circle/></svg> end"
    hooks = (
        "var svgVisualRawSpans=s=>{const out=[];let i=0;"
        "while((i=s.indexOf('<svg',i))!==-1){const e=s.indexOf('</svg>',i)+6;out.push([i,e]);i=e;}"
        "if(out.length)out.push([out[0][0]+1,out[0][1]]);"  # overlapping, dropped
        "return out;};"
    )
    rendered = _render([text, "A <svg>MEDIA:/x.png</svg> B"], hooks)["scaffold"]
    html = rendered[0]
    blocks = re.findall(r'<div class="svg-visual-block" data-svg-id="svg-[a-z0-9]{1,8}">(.*?)</div>', html)
    assert blocks == ["&lt;svg&gt;&lt;rect/&gt;&lt;/svg&gt;", "&lt;svg&gt;&lt;circle/&gt;&lt;/svg&gt;"]
    assert "<p>Before</p>" in html and "<p>middle</p>" in html and "<p>end</p>" in html
    assert "<p><div" not in html
    # A run that would swallow another stash token is not taken.
    assert "svg-visual-block" not in rendered[1]


@needs_node
def test_post_processing_runs_the_visual_hooks_last_and_guarded():
    ui = (STATIC / "ui.js").read_text(encoding="utf-8")
    fn = _js_function(ui, "postProcessRenderedMessages")
    script = r"""
const vm=require('vm');
let data='';process.stdin.on('data',c=>data+=c);process.stdin.on('end',()=>{
  const {fn}=JSON.parse(data);const calls=[];const warnings=[];
  const names=['highlightCode','addCopyButtons','loadDiffInline','loadCsvInline','loadExcalidrawInline',
    'loadPdfInline','loadHtmlInline','renderMermaidBlocks','renderKatexBlocks','initTreeViews'];
  function run(extra){
    const ctx={console:{warn:(...a)=>warnings.push(a[0])}};
    for(const n of names)ctx[n]=()=>calls.push(n);
    Object.assign(ctx,extra);vm.createContext(ctx);vm.runInContext(fn,ctx);calls.length=0;
    ctx.postProcessRenderedMessages({});return calls.slice();
  }
  const plain=run({});
  const hooked=run({renderSvgVisualBlocks:()=>calls.push('renderSvgVisualBlocks'),
                    enhanceSvgMediaCards:()=>{throw new Error('boom');}});
  process.stdout.write(JSON.stringify({plain,hooked,warnings,names}));
});
"""
    out = json.loads(_node(script, json.dumps({"fn": fn})))
    assert out["plain"] == out["names"]
    assert out["hooked"] == out["names"] + ["renderSvgVisualBlocks"]
    assert out["warnings"] == ["[svg] render failed"]


# ── Memory panel registry (addendum AE-9) ────────────────────────────────────

_MEMORY_HARNESS = r"""
const vm=require('vm'),assert=require('assert/strict');
let data='';process.stdin.on('data',c=>data+=c);process.stdin.on('end',()=>{
  const {source,scenario}=JSON.parse(data);
  class Panel{constructor(){this.children=[];this._html='';}
    set innerHTML(v){this._html=v;if(v==='')this.children=[];} get innerHTML(){return this._html;}
    appendChild(el){this.children.push(el);}}
  const nodes={memoryPanel:new Panel(),memoryDetailBody:{innerHTML:'',style:{}},
    memoryDetailTitle:{textContent:'',style:{}},memoryDetailEmpty:{style:{}}};
  const resolvers=[];
  const ctx={console,window:{},S:{session:{session_id:'s1'},activeProfile:'default'},
    $:id=>nodes[id]||null,esc:x=>String(x),t:k=>'T('+k+')',li:(n,s)=>'<i:'+n+'>',renderMd:x=>'md:'+x,
    loadNotesSources:async()=>({}),_closeMobileSidebarAfterPanelSelection:()=>{},
    api:async()=>ctx.memoryData,
    document:{querySelectorAll:()=>[],createElement:()=>{const el={type:'',className:'',innerHTML:'',title:'',
      classes:[],classList:{add:c=>el.classes.push(c)}};return el;}}};
  ctx.memoryData={memory:'m',user:'u',external_notes_enabled:false};
  vm.createContext(ctx);vm.runInContext(source,ctx);
  const list=()=>nodes.memoryPanel.children.map(b=>({label:b.innerHTML,title:b.title,active:b.classes.includes('active')}));
  const run=code=>vm.runInContext(code,ctx);
  (async()=>{
    const result={};
    if(scenario==='none'){
      await ctx.loadMemory(); result.none=list();
      ctx.window.SynthPulseMemoryExtensions=[]; await ctx.loadMemory(); result.empty=list();
      let called=0;
      ctx.window.SynthPulseMemoryExtensions=[{sections:()=>{called++;return [];}},{render:()=>{}},null,'x'];
      await ctx.loadMemory(); result.invalid=list(); result.called=called;
      result.mode=run('_memoryMode');
    } else {
      const rendered=[];
      ctx.window.SynthPulseMemoryExtensions=[
        {sections:async d=>{rendered.push('sections:'+d.memory);return [
            {key:'mnemo_me',labelKey:'mnemo_section_label',iconKey:'brain',titleKey:'mnemo_section_tooltip'},
            {key:'memory',labelKey:'x',iconKey:'x',titleKey:'x'},
            {key:'Bad-Key',labelKey:'x',iconKey:'x',titleKey:'x'},
            {key:'ab',labelKey:'x',iconKey:'x',titleKey:'x'},
            {key:'no_label',iconKey:'x',titleKey:'x'},
            null];},
         render:(key,els)=>{rendered.push('render:'+key+':'+Object.keys(els).join(','));els.body.innerHTML='mine';}},
        {sections:()=>[{key:'mnemo_me',labelKey:'other',iconKey:'x',titleKey:'y'},
                       {key:'org_memory',labelKey:'org_label',iconKey:'users',titleKey:'org_title'}],
         render:()=>{rendered.push('second');}},
        {sections:()=>{throw new Error('boom');},render:()=>{}}];
      await ctx.loadMemory(); result.list=list();
      result.meta=run("JSON.stringify(_memorySectionMeta('mnemo_me'),(k,v)=>k==='provider'?undefined:v)");
      result.metaFallback=run("_memorySectionMeta('nope').key");
      const btn=nodes.memoryPanel.children[4];
      await ctx.openMemorySection('mnemo_me',btn);
      result.afterOpen={title:nodes.memoryDetailTitle.textContent,body:nodes.memoryDetailBody.innerHTML,
        mode:run('_memoryMode'),current:run('_currentMemorySection')};
      await ctx.loadMemory(); result.reloadActive=list().filter(b=>b.active).map(b=>b.label);
      ctx.window.SynthPulseMemoryExtensions=[]; await ctx.loadMemory();
      result.afterRemoval={list:list(),current:run('_currentMemorySection')};
      // Epoch and context checks are repeated after the provider await.
      let release;ctx.window.SynthPulseMemoryExtensions=[{sections:()=>new Promise(r=>release=r),render:()=>{}}];
      const first=ctx.loadMemory(); await new Promise(r=>setImmediate(r));
      ctx.S.session={session_id:'s2'}; ctx.window.SynthPulseMemoryExtensions=[];
      ctx.memoryData={memory:'second',external_notes_enabled:false};
      await ctx.loadMemory(); release([{key:'late_key',labelKey:'l',iconKey:'i',titleKey:'t'}]); await first;
      result.stale={memory:run('_memoryData.memory'),labels:list().map(b=>b.label)};
      result.rendered=rendered;
    }
    process.stdout.write(JSON.stringify(result));
  })().catch(e=>{console.error(e);process.exitCode=1;});
});
"""


def _memory_source():
    panels = (STATIC / "panels.js").read_text(encoding="utf-8")

    def between(start, end):
        i = panels.index(start)
        return panels[i:panels.index(end, i)]

    return "\n".join((
        between("// ── Memory (main view) ──", "function _renderMemoryEdit("),
        between("async function openMemorySection(", "function editCurrentMemory("),
        between("// ── Memory panel ──", "// Drag and drop"),
    ))


def _memory(scenario):
    return json.loads(_node(_MEMORY_HARNESS, json.dumps({"source": _memory_source(), "scenario": scenario})))


_BUILT_IN_BUTTONS = [
    {"label": "<i:brain><span>T(my_notes)</span>", "title": "Only you", "active": False},
    {"label": "<i:user><span>T(user_profile)</span>", "title": "Only you", "active": False},
    {"label": "<i:sparkles><span>Personal agent preferences</span>", "title": "Only you", "active": False},
    {"label": "<i:file-text><span>My project notes</span>", "title": "Only you", "active": False},
]


@needs_node
def test_memory_panel_section_list_is_unchanged_without_a_provider():
    out = _memory("none")
    assert out["none"] == _BUILT_IN_BUTTONS
    assert out["empty"] == _BUILT_IN_BUTTONS
    assert out["invalid"] == _BUILT_IN_BUTTONS
    assert out["called"] == 0  # a provider without render is not a provider
    assert out["mode"] == "empty"


@needs_node
def test_memory_panel_registry_lists_and_renders_registered_sections():
    out = _memory("providers")
    assert out["list"] == _BUILT_IN_BUTTONS + [
        {"label": "<i:brain><span>T(mnemo_section_label)</span>", "title": "T(mnemo_section_tooltip)", "active": False},
        {"label": "<i:users><span>T(org_label)</span>", "title": "T(org_title)", "active": False},
    ]
    assert json.loads(out["meta"]) == {"key": "mnemo_me", "labelKey": "mnemo_section_label", "iconKey": "brain",
                                       "titleKey": "mnemo_section_tooltip", "readOnly": True}
    assert out["metaFallback"] == "memory"
    assert out["afterOpen"] == {"title": "T(mnemo_section_label)", "body": "mine", "mode": "read",
                                "current": "mnemo_me"}
    assert out["reloadActive"] == ["<i:brain><span>T(mnemo_section_label)</span>"]
    assert out["afterRemoval"] == {"list": _BUILT_IN_BUTTONS, "current": None}
    assert out["stale"] == {"memory": "second", "labels": [b["label"] for b in _BUILT_IN_BUTTONS]}
    assert out["rendered"][:2] == ["sections:m", "render:mnemo_me:title,body,empty"]
    assert "second" not in out["rendered"]
