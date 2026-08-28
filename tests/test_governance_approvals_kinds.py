"""Kind-aware approvals: api/approvals.py + the governance approvals API.

Covers the four request kinds (skill, integration, mcp, cli), the global vs
owner-scoped approval rule, the admin queue, the decide endpoint and the
non-admin /api/governance/approvals/mine view. Skills must keep behaving
exactly as before: they stay in skill_ownership.json and never leak into
approvals.json.
"""
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import approvals, config, governance_api, skill_ownership  # noqa: E402
from api.governance import loader  # noqa: E402
from api.governance.audit import read_audit_events  # noqa: E402
from api.governance.catalog import _SELF_ROUTES, route_permission  # noqa: E402

BOOTSTRAP = "michael@example.test"

POLICY = {
    "version": 1,
    "mode": "report_only",
    "default_effect": "deny",
    "bootstrap_admins": [BOOTSTRAP],
    "roles": {
        "admin": {
            "grants": {
                "permissions": ["governance:read", "governance:write"],
                "profiles": ["*"],
                "routes": ["*"],
            },
        },
        "viewer": {
            "grants": {"permissions": ["sessions:read"], "profiles": ["default"]},
        },
    },
    "groups": {},
    "users": {
        "admin@example.test": {"roles": ["admin"]},
        "viewer@example.test": {"roles": ["viewer"]},
        BOOTSTRAP: {"roles": ["admin"]},
    },
}


class FakeHandler:
    def __init__(self, body=None, headers=None):
        raw = json.dumps(body).encode("utf-8") if body is not None else b""
        self.headers = dict(headers or {})
        if raw:
            self.headers.setdefault("Content-Length", str(len(raw)))
        self.rfile = io.BytesIO(raw)
        self.wfile = io.BytesIO()
        self.status = None
        self.response_headers = {}
        self.close_connection = False

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers[key] = value

    def end_headers(self):
        pass

    @property
    def body(self):
        return json.loads(self.wfile.getvalue().decode("utf-8"))


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_WEBUI_GOVERNANCE_POLICY", raising=False)
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "webui")
    loader.set_policy_loader(None)
    (tmp_path / "dashboard-governance.yaml").write_text(yaml.safe_dump(POLICY), encoding="utf-8")
    yield tmp_path
    loader.set_policy_loader(None)


@pytest.fixture
def as_user(monkeypatch):
    def _set(email, groups=None, method="oidc"):
        identity = (
            {"email": email, "groups": list(groups or []), "claims_subset": {}, "method": method}
            if email is not None
            else None
        )
        monkeypatch.setattr(governance_api, "_caller_identity", lambda handler: identity)
    return _set


def _call(path, method="GET", body=None, query=""):
    handler = FakeHandler(body=body)
    handled = governance_api.handle_governance_api(
        handler, SimpleNamespace(path=path, query=query), method
    )
    return handled, handler


# ── Registry module ─────────────────────────────────────────────────────────

def test_skill_requests_stay_in_skill_ownership(isolated_home):
    entry = approvals.request("skill", "ops/deploy", "u@example.test")
    assert entry["kind"] == "skill" and entry["status"] == "pending"
    assert skill_ownership.get("ops/deploy")["owner_email"] == "u@example.test"
    assert not (config.STATE_DIR / "approvals.json").exists()


def test_request_is_idempotent_and_never_reassigns(isolated_home):
    first = approvals.request("mcp", "context7", "u@example.test", label="Context7")
    again = approvals.request("mcp", "context7", "other@example.test", label="Hijack")
    assert again["owner_email"] == "u@example.test"
    assert again["label"] == "Context7"
    assert again["requested_at"] == first["requested_at"]

    approvals.decide("mcp", "context7", "approve", "admin@example.test")
    after = approvals.request("mcp", "context7", "u@example.test")
    assert after["status"] == "approved"


def test_approved_scope_global_vs_owner(isolated_home):
    approvals.request("cli", "gh", "u@example.test")
    approvals.request("mcp", "private", "u@example.test", payload={"scope": "owner"})
    approvals.decide("cli", "gh", "approve", "admin@example.test")
    approvals.decide("mcp", "private", "approve", "admin@example.test")

    assert approvals.is_approved("cli", "gh", "anyone@example.test") is True
    assert approvals.is_approved("mcp", "private", "u@example.test") is True
    assert approvals.is_approved("mcp", "private", "anyone@example.test") is False
    assert approvals.is_approved("mcp", "private", "all") is True
    assert approvals.is_approved("mcp", "never-asked") is False


def test_reject_keeps_the_row_with_a_reason(isolated_home):
    approvals.request("integration", "gdrive", "u@example.test")
    entry = approvals.decide(
        "integration", "gdrive", "reject", "admin@example.test", reason="use the shared account"
    )
    assert entry["status"] == "rejected"
    assert entry["reason"] == "use the shared account"
    assert entry["decided_by"] == "admin@example.test"
    assert approvals.is_approved("integration", "gdrive") is False
    assert approvals.list_pending(kinds="integration") == []
    assert approvals.status_of("integration", "gdrive") == "rejected"


def test_list_pending_merges_skills_oldest_first(isolated_home):
    approvals.request("skill", "ops/deploy", "u@example.test")
    approvals.request("mcp", "context7", "u@example.test")
    approvals.request("cli", "gh", "b@example.test")
    assert [(r["kind"], r["key"]) for r in approvals.list_pending()] == [
        ("skill", "ops/deploy"),
        ("mcp", "context7"),
        ("cli", "gh"),
    ]
    assert [r["key"] for r in approvals.list_pending(kinds=["cli"])] == ["gh"]


def test_bad_kind_and_missing_entry_raise(isolated_home):
    with pytest.raises(ValueError):
        approvals.request("bogus", "x", "u@example.test")
    with pytest.raises(ValueError):
        approvals.request("mcp", "  ", "u@example.test")
    with pytest.raises(ValueError):
        approvals.decide("mcp", "x", "maybe", "admin@example.test")
    with pytest.raises(KeyError):
        approvals.decide("mcp", "never", "approve", "admin@example.test")


def test_corrupt_registry_degrades_to_empty(isolated_home):
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    (config.STATE_DIR / "approvals.json").write_text("{not json", encoding="utf-8")
    assert approvals.load() == {}
    assert approvals.list_pending() == []


# ── API ─────────────────────────────────────────────────────────────────────

def test_queue_lists_every_kind_with_legacy_skill_fields(as_user):
    approvals.request("skill", "ops/deploy", "u@example.test")
    approvals.request("mcp", "context7", "u@example.test", label="Context7", payload={"command": "npx"})
    as_user("admin@example.test")
    _, handler = _call("/api/governance/approvals")
    rows = handler.body["pending"]
    assert handler.status == 200
    skill = rows[0]
    assert skill["key"] == "ops/deploy"
    assert skill["name"] == "deploy" and skill["category"] == "ops"
    assert skill["owner_email"] == "u@example.test" and skill["added_at"]
    assert skill["kind"] == "skill"
    mcp = rows[1]
    assert mcp["kind"] == "mcp" and mcp["name"] == "Context7"
    assert mcp["payload"] == {"command": "npx"}
    assert mcp["status"] == "pending"


def test_queue_requires_governance_write(as_user):
    as_user("viewer@example.test")
    _, handler = _call("/api/governance/approvals")
    assert handler.status == 403
    assert handler.body["resource"] == "governance:write"


def test_decide_rejects_unknown_kind(as_user):
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/approvals/decide", "POST",
        body={"kind": "plugin", "key": "x", "decision": "approve"},
    )
    assert handler.status == 400
    assert handler.body["error"] == "invalid_payload"
    assert "skill" in handler.body["message"] and "mcp" in handler.body["message"]


def test_decide_skill_still_flips_ownership_status(as_user):
    approvals.request("skill", "ops/deploy", "u@example.test")
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/approvals/decide", "POST",
        body={"kind": "skill", "key": "ops/deploy", "decision": "approve"},
    )
    assert handler.status == 200
    assert handler.body == {"ok": True, "key": "ops/deploy", "status": "approved"}
    assert skill_ownership.get("ops/deploy")["status"] == "approved"


def test_decide_generic_approves_and_audits(as_user):
    approvals.request("mcp", "context7", "u@example.test", label="Context7")
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/approvals/decide", "POST",
        body={"kind": "mcp", "key": "context7", "decision": "approve"},
    )
    assert handler.status == 200
    assert handler.body["ok"] is True
    assert handler.body["status"] == "approved"
    assert handler.body["entry"]["decided_by"] == "admin@example.test"
    assert approvals.is_approved("mcp", "context7", "anyone@example.test") is True

    events = [e for e in read_audit_events(20) if e.get("event") == "approval_decision"]
    assert events and events[-1]["reason"] == "approvals.approve"
    assert events[-1]["extra"]["key"] == "mcp:context7"


def test_decide_generic_404_for_unrequested_item(as_user):
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/approvals/decide", "POST",
        body={"kind": "cli", "key": "gh", "decision": "approve"},
    )
    assert handler.status == 404
    assert handler.body["error"] == "not_found"


def test_mine_is_scoped_and_needs_no_admin(as_user):
    approvals.request("mcp", "context7", "u@example.test")
    approvals.request("cli", "gh", "viewer@example.test")
    approvals.decide("cli", "gh", "reject", "admin@example.test", reason="no")

    as_user("viewer@example.test")
    _, handler = _call("/api/governance/approvals/mine")
    assert handler.status == 200
    assert handler.body["owner_email"] == "viewer@example.test"
    rows = handler.body["requests"]
    assert [r["key"] for r in rows] == ["gh"]
    assert rows[0]["status"] == "rejected" and rows[0]["reason"] == "no"


def test_mine_kind_filter(as_user):
    approvals.request("mcp", "context7", "viewer@example.test")
    approvals.request("cli", "gh", "viewer@example.test")
    as_user("viewer@example.test")
    _, handler = _call("/api/governance/approvals/mine", query="kind=cli")
    assert [r["key"] for r in handler.body["requests"]] == ["gh"]


def test_mine_route_needs_no_permission():
    assert "/api/governance/approvals/mine" in _SELF_ROUTES
    assert route_permission("/api/governance/approvals/mine", "GET") is None
    assert route_permission("/api/governance/approvals", "GET") == "governance:read"


def test_mcp_decide_installs_on_approve_and_uninstalls_on_reject(isolated_home, as_user, monkeypatch):
    """Approve/reject must take effect on the MCP surface, not only in the
    registry: a rejected server that is already installed has to be removed,
    otherwise 'approved then rejected' stays live forever."""
    from api import mcp_requests

    calls = []
    monkeypatch.setattr(
        mcp_requests, "sync_approved_quietly",
        lambda decided_by=None, **kw: calls.append(("install", decided_by)),
    )
    monkeypatch.setattr(
        mcp_requests, "uninstall_quietly",
        lambda name, decided_by=None, **kw: calls.append(("uninstall", name, decided_by)),
    )

    approvals.request("mcp", "context7", "u@example.test", payload={"url": "https://x/sse"})
    as_user("admin@example.test")

    status, handler = _call(
        "/api/governance/approvals/decide", "POST",
        {"kind": "mcp", "key": "context7", "decision": "approve"},
    )
    assert handler.body["status"] == "approved"
    assert calls == [("install", "admin@example.test")]

    _call(
        "/api/governance/approvals/decide", "POST",
        {"kind": "mcp", "key": "context7", "decision": "reject", "reason": "no"},
    )
    assert calls[-1] == ("uninstall", "context7", "admin@example.test")


def test_non_mcp_decide_does_not_touch_the_mcp_config(isolated_home, as_user, monkeypatch):
    from api import mcp_requests

    monkeypatch.setattr(
        mcp_requests, "sync_approved_quietly",
        lambda *a, **k: pytest.fail("integration decide must not sync MCP servers"),
    )
    monkeypatch.setattr(
        mcp_requests, "uninstall_quietly",
        lambda *a, **k: pytest.fail("integration decide must not uninstall MCP servers"),
    )
    approvals.request("integration", "gdrive", "u@example.test")
    as_user("admin@example.test")
    _call(
        "/api/governance/approvals/decide", "POST",
        {"kind": "integration", "key": "gdrive", "decision": "approve"},
    )
    assert approvals.status_of("integration", "gdrive") == "approved"


def test_request_flood_is_capped_per_owner(isolated_home):
    """Requesting needs no permission, so an unbounded registry would let any
    user flood the admin queue (and bury a malicious row in it)."""
    for i in range(approvals._MAX_PENDING_PER_OWNER):
        approvals.request("integration", f"p{i}", "spammer@example.test")
    with pytest.raises(ValueError):
        approvals.request("integration", "one-too-many", "spammer@example.test")
    # Another user is unaffected, and a re-request of an existing item works.
    assert approvals.request("integration", "p0", "spammer@example.test")["key"] == "p0"
    assert approvals.request("integration", "mine", "other@example.test")["status"] == "pending"
    # Deciding frees the budget.
    approvals.decide("integration", "p0", "reject", "admin@example.test")
    assert approvals.request("integration", "one-more", "spammer@example.test")["key"] == "one-more"


# ── Row shape after the capability/risk detail was added (28 Aug 2026) ───────

def test_legacy_skill_fields_survive_the_added_explanation(as_user):
    """The five fields the skills UI binds to keep their meaning and value; the
    reviewer detail is added alongside them, never in place of one."""
    approvals.request("skill", "ops/deploy", "u@example.test")
    as_user("admin@example.test")
    _, handler = _call("/api/governance/approvals")
    skill = handler.body["pending"][0]
    assert skill["key"] == "ops/deploy"
    assert skill["name"] == "deploy"
    assert skill["category"] == "ops"
    assert skill["owner_email"] == "u@example.test"
    assert skill["added_at"] == skill["requested_at"]
    assert isinstance(skill["explanation"], dict) and skill["explanation"]["capability"]


def test_mine_row_shape_is_unchanged(as_user):
    """static/panels.js loadMyAccessRequests and static/integrations.js read
    this row; it must keep exactly the keys it had before the admin queue grew
    an explanation."""
    approvals.request("mcp", "context7", "u@example.test", label="Context7")
    as_user("u@example.test")
    _, handler = _call("/api/governance/approvals/mine")
    assert set(handler.body["requests"][0]) == {
        "kind", "key", "name", "category", "label", "owner_email", "added_at",
        "requested_at", "status", "decided_by", "decided_at", "reason", "payload",
    }


# ── The permission grant kind (ticket 10, 28 Aug 2026) ──────────────────────

def test_permission_grants_are_held_to_an_allowlist(isolated_home):
    """A route grant was safe to offer one-click BECAUSE the permission wall
    stayed up behind it. Handing out the permission removes that wall, so the
    guard here is an allowlist and not the route guard's denylist: a denylist
    of governance:*/*:admin lets terminal:use and config:write straight
    through, and config:write is a body-sink permission the route layer admits
    at config:read."""
    from api import grant_requests

    raw = {"users": {"u@example.test": {"grants": {}}}}
    assert grant_requests.apply_grant_to_policy(
        raw, {"email": "u@example.test", "gkind": "permission", "value": "sessions:read"}
    ) is not None
    assert raw["users"]["u@example.test"]["grants"]["permissions"] == ["sessions:read"]

    for refused in ("terminal:use", "config:write", "governance:write", "profiles:admin"):
        raw = {"users": {"u@example.test": {"grants": {}}}}
        assert grant_requests.apply_grant_to_policy(
            raw, {"email": "u@example.test", "gkind": "permission", "value": refused}
        ) is None, refused
        assert raw["users"]["u@example.test"]["grants"] == {}
