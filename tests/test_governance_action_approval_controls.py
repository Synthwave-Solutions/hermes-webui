"""Hostile approval scopes never mutate pending work or broad allowlists."""
from copy import deepcopy
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

from api import route_approvals, routes
from api.governance import loader
from api.governance.loader import parse_governance_policy


@pytest.fixture
def pending():
    sid = "managed-action-review-test"
    route_approvals.submit_pending(sid, {
        "command": "one requested write", "pattern_key": "governance_action:operation",
        "governance_action": True, "allow_session": False, "allow_permanent": False,
    })
    with route_approvals._lock:
        entry = deepcopy(route_approvals._pending[sid][0])
    yield sid, entry
    with route_approvals._lock:
        route_approvals._pending.pop(sid, None)


@pytest.mark.parametrize("choice", ["session", "always"])
def test_action_cannot_expand_scope_or_mutate_queue(pending, monkeypatch, choice):
    sid, entry = pending
    monkeypatch.setattr(routes, "j", lambda h, data, status=200: (status, data))
    monkeypatch.setattr(routes, "_resolve_approval_legacy", lambda *args: pytest.fail("must not resolve"))
    monkeypatch.setattr(routes, "approve_session", lambda *args: pytest.fail("must not save session grant"))
    monkeypatch.setattr(routes, "approve_permanent", lambda *args: pytest.fail("must not save permanent grant"))
    status, data = routes._handle_approval_respond(object(), {
        "session_id": sid, "approval_id": entry["approval_id"], "choice": choice,
    })
    assert status == 400
    assert data["code"] == "governance_one_shot_only"
    with route_approvals._lock:
        assert route_approvals._pending[sid] == [entry]
    assert route_approvals.approval_choice_allowed(sid, entry["approval_id"], "once")
    assert route_approvals.approval_choice_allowed(sid, entry["approval_id"], "deny")


@pytest.mark.parametrize("config", [
    {"access_level": "elevated"}, {"access_mode": "blacklist"},
    {"approval": {"mode": "manual", "prompt": ""}},
])
def test_managed_user_cannot_enable_yolo_even_without_pending_work(monkeypatch, config):
    policy = parse_governance_policy({"mode": "enforce", "users": {"alice@example.test": config}})
    monkeypatch.setattr(loader, "get_policy", lambda: policy)
    monkeypatch.setattr(routes, "_check_csrf", lambda h: True)
    monkeypatch.setattr(routes, "_guard_request_session_visibility", lambda *a, **kw: True)
    monkeypatch.setattr(routes, "read_body", lambda h: {"session_id": "managed-yolo", "enabled": True})
    monkeypatch.setattr(routes, "j", lambda h, data, status=200: (status, data))
    monkeypatch.setattr("api.bot_builder.guard_profile_request", lambda *a: True)
    monkeypatch.setattr("api.governance.resource_scope.guard_request", lambda *a: True)
    monkeypatch.setattr("api.governance.enforce._request_identity", lambda h: {"email": "alice@example.test"})
    monkeypatch.setattr(routes, "enable_session_yolo", lambda *a: pytest.fail("must not enable YOLO"))
    monkeypatch.setattr(routes, "resolve_gateway_approval", lambda *a, **kw: pytest.fail("must not resolve pending"))
    status, data = routes.handle_post(SimpleNamespace(headers={}), urlparse("/api/session/yolo"))
    assert status == 403
    assert data["code"] == "governance_approval_required"


def test_legacy_user_cannot_skip_a_governed_pending_action(pending, monkeypatch):
    sid, _ = pending
    monkeypatch.setattr(loader, "get_policy", lambda: parse_governance_policy({"mode": "off"}))
    with pytest.raises(PermissionError):
        route_approvals.require_yolo_eligible({"email": "legacy@example.test"}, sid)


def test_gateway_preserves_one_action_contract():
    from api.gateway_chat import _gateway_runs_approval_event
    event = _gateway_runs_approval_event({"tool": "write_file", "command": "write",
        "governance_action": True, "allow_session": False, "allow_permanent": False,
        "required_approver": "admin@example.test"})
    assert event["governance_action"] is True
    assert event["allow_session"] is False
    assert event["allow_permanent"] is False
    assert event["required_approver"] == "admin@example.test"


def test_resolver_rechecks_scope_under_lock_and_once_does_not_save_allowlist(pending, monkeypatch):
    sid, entry = pending
    monkeypatch.setattr(routes, "approve_session", lambda *a: pytest.fail("governed once must not save a session grant"))
    monkeypatch.setattr(routes, "approve_permanent", lambda *a: pytest.fail("must not save permanent grant"))
    for choice in ("session", "always"):
        assert routes._resolve_approval_legacy(sid, entry["approval_id"], choice) is False
    # An id-less stale click cannot consume a newly queued governed request.
    assert routes._resolve_approval_legacy(sid, "", "once") is False
    with route_approvals._lock:
        assert route_approvals._pending[sid] == [entry]
    assert routes._resolve_approval_legacy(sid, entry["approval_id"], "once") is True
