from __future__ import annotations

from unittest.mock import patch

from api import routes
from api import route_approvals


MICHAEL = "michael@synthwave.solutions"
MARCEL = "marcel@synthwave.solutions"


def _queue_governance_approval(sid: str) -> str:
    route_approvals.submit_pending(sid, {
        "command": "python3 -V",
        "pattern_key": "governance-cli:test",
        "pattern_keys": ["governance-cli:test"],
        "description": "governance approval",
        "approval_kind": "governance_cli",
        "subject_email": MARCEL,
        "required_approver": MICHAEL,
        "allow_permanent": False,
    })
    with route_approvals._lock:
        return route_approvals._pending[sid][0]["approval_id"]


def _fake_j(_handler, payload, status=200):
    return {"status": status, "payload": payload}


def test_required_approver_round_trips_from_pending_queue():
    sid = "governance-approver-roundtrip"
    with route_approvals._lock:
        route_approvals._pending.pop(sid, None)
    try:
        approval_id = _queue_governance_approval(sid)
        assert route_approvals.approval_required_approver(sid, approval_id) == MICHAEL
        assert route_approvals.approval_required_approver(sid, "stale-id") == ""
    finally:
        with route_approvals._lock:
            route_approvals._pending.pop(sid, None)


def test_marcel_cannot_approve_his_own_governance_command():
    sid = "governance-marcel-self-approve"
    with route_approvals._lock:
        route_approvals._pending.pop(sid, None)
    try:
        approval_id = _queue_governance_approval(sid)
        with patch("api.routes.j", new=_fake_j), \
             patch("api.ownership.request_owner_email", return_value=MARCEL):
            response = routes._handle_approval_respond(
                object(),
                {"session_id": sid, "approval_id": approval_id, "choice": "once"},
            )
        assert response["status"] == 403
        assert response["payload"]["code"] == "governance_approver_required"
        with route_approvals._lock:
            assert route_approvals._pending[sid][0]["approval_id"] == approval_id
    finally:
        with route_approvals._lock:
            route_approvals._pending.pop(sid, None)


def test_michael_can_approve_marcel_governance_command_once_without_session_grant():
    sid = "governance-michael-approve"
    with route_approvals._lock:
        route_approvals._pending.pop(sid, None)
    try:
        approval_id = _queue_governance_approval(sid)
        with patch("api.routes.j", new=_fake_j), \
             patch("api.ownership.request_owner_email", return_value=MICHAEL), \
             patch("api.gateway_chat.webui_gateway_chat_enabled", return_value=False), \
             patch("api.runtime_adapter.runtime_adapter_enabled", return_value=False), \
             patch("api.routes.approve_session") as approve_session:
            response = routes._handle_approval_respond(
                object(),
                {"session_id": sid, "approval_id": approval_id, "choice": "once"},
            )
        assert response["status"] == 200
        assert response["payload"]["ok"] is True
        approve_session.assert_not_called()
    finally:
        with route_approvals._lock:
            route_approvals._pending.pop(sid, None)


def test_governance_command_rejects_session_and_always_scopes():
    for choice in ("session", "always"):
        sid = f"governance-scope-{choice}"
        with route_approvals._lock:
            route_approvals._pending.pop(sid, None)
        try:
            approval_id = _queue_governance_approval(sid)
            with patch("api.routes.j", new=_fake_j), \
                 patch("api.ownership.request_owner_email", return_value=MICHAEL):
                response = routes._handle_approval_respond(
                    object(),
                    {"session_id": sid, "approval_id": approval_id, "choice": choice},
                )
            assert response["status"] == 400
            assert response["payload"]["code"] == "governance_one_shot_only"
            with route_approvals._lock:
                assert route_approvals._pending[sid][0]["approval_id"] == approval_id
        finally:
            with route_approvals._lock:
                route_approvals._pending.pop(sid, None)
