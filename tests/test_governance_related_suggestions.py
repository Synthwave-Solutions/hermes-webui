"""Related access for one governance request (ticket 10, 28 Aug 2026).

An administrator deciding an access request should see the rest of the chain in
the same review, decide each item on its own, and never hand out a capability
by clicking something that was only meant to inform them.

The two security properties this file exists to pin:

* a suggestion is never a one-click widening of access. The permissions that
  may be granted here are an ALLOWLIST of read-shaped names, enforced in
  api/grant_requests.apply_grant_to_policy and not only in the surface that
  offers them, so a hand-crafted POST naming terminal:use or config:write
  changes nothing;
* nothing is granted automatically or bundled. Reading the list writes no
  policy, approving one row leaves its siblings open, and denying one never
  pre-empts a real request the person has not filed yet.
"""
import io
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import approvals, config, governance_api, grant_requests  # noqa: E402
from api.governance import loader, suggestions  # noqa: E402
from api.governance.audit import _hash_identity, append_audit_event, read_audit_events  # noqa: E402
from api.governance.catalog import route_permission  # noqa: E402

BOOTSTRAP = "michael@example.test"
USER = "u@example.test"

# The requester holds chat access and the chat address, and their model access
# is written in the aliased form: both August incidents are reproducible from
# this one fixture.
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
        "viewer": {"grants": {"permissions": ["sessions:read"], "profiles": ["default"]}},
    },
    "groups": {},
    "users": {
        "admin@example.test": {"roles": ["admin"]},
        "viewer@example.test": {"roles": ["viewer"]},
        BOOTSTRAP: {"roles": ["admin"]},
        USER: {
            "grants": {
                "permissions": ["chat:use"],
                "routes": ["/api/chat*"],
                "models": {"providers": ["custom:omniroute"]},
            },
        },
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


def _policy():
    return loader.get_policy()


def _policy_file(home):
    return home / "dashboard-governance.yaml"


def _request(email, gkind, value, *, reason="route_not_allowed"):
    """A pending access request exactly as ingest_spool would have written it."""
    key = f"{email}|{gkind}|{value}"
    registry = approvals.load()
    registry[f"{approvals.KIND_GRANT}:{key}"] = {
        "kind": approvals.KIND_GRANT,
        "key": key,
        "label": grant_requests._request_label({"gkind": gkind, "value": value}),
        "owner_email": email,
        "status": "pending",
        "requested_at": time.time(),
        "payload": {
            "email": email, "gkind": gkind, "value": value, "reason": reason,
            "tool": "", "detail": value, "trigger": "", "count": 1,
        },
    }
    approvals.save(registry)
    return key


def _suggest(email, gkind, value, **kw):
    key = _request(email, gkind, value, **kw)
    return key, suggestions.suggestions_for(approvals.get(approvals.KIND_GRANT, key), _policy())


def _by(rows, gkind, value):
    for row in rows:
        if row["gkind"] == gkind and row["value"] == value:
            return row
    return None


# ── Confirmed dependencies ──────────────────────────────────────────────────

def test_route_request_surfaces_the_permission_wall_behind_it(isolated_home):
    """The second wall: enforce checks the address first and the permission
    second, so approving the address alone leaves the person stopped."""
    _key, rows = _suggest(USER, "route", "/api/crons")
    row = _by(rows, "permission", "cron:read")
    assert row is not None and row["confidence"] == "confirmed"
    assert row["signal"] == "route_needs_permission"
    assert _by(rows, "permission", "cron:write") is not None


def test_the_chat_session_dependency_is_confirmed(isolated_home):
    """11 Aug 2026: chat access was granted on its own and the assistant opened
    and then stopped, because opening a workspace needs sessions:write."""
    _key, rows = _suggest(USER, "route", "/api/crons")
    row = _by(rows, "permission", "sessions:write")
    assert row is not None and row["confidence"] == "confirmed"
    assert row["signal"] == "known_dependency"
    # The address the workspace is opened at comes with it, in the wildcard
    # form that actually unblocks the paths underneath it.
    route = _by(rows, "route", "/api/session*")
    assert route is not None and route["confidence"] == "confirmed"


def test_the_provider_alias_shape_is_confirmed_and_clears_when_fixed(isolated_home):
    """12 Aug 2026: a model entry written as custom:<name> is rewritten to
    plain custom before the check, so the check never matches."""
    _key, rows = _suggest(USER, "route", "/api/crons")
    row = _by(rows, "model_provider", "custom")
    assert row is not None and row["confidence"] == "confirmed"

    policy = json.loads(json.dumps(POLICY))
    policy["users"][USER]["grants"]["models"]["providers"].append("custom")
    _policy_file(isolated_home).write_text(yaml.safe_dump(policy), encoding="utf-8")
    loader.set_policy_loader(None)
    key = _request(USER, "route", "/api/crons")
    rows = suggestions.suggestions_for(approvals.get(approvals.KIND_GRANT, key), _policy())
    assert _by(rows, "model_provider", "custom") is None


def test_an_uppercase_provider_entry_is_confirmed(isolated_home):
    """The check lowercases the incoming provider but not the recorded one."""
    policy = json.loads(json.dumps(POLICY))
    policy["users"][USER]["grants"]["models"]["providers"] = ["FreeLLMAPI"]
    _policy_file(isolated_home).write_text(yaml.safe_dump(policy), encoding="utf-8")
    loader.set_policy_loader(None)
    _key, rows = _suggest(USER, "route", "/api/crons")
    row = _by(rows, "model_provider", "freellmapi")
    assert row is not None and row["confidence"] == "confirmed"


def test_the_dependency_chain_is_walked_to_the_end(isolated_home):
    """sessions:write is itself built on sessions:read, so leaving the smaller
    one out would send the person into a third wall after this review."""
    _key, rows = _suggest(USER, "route", "/api/crons")
    row = _by(rows, "permission", "sessions:read")
    assert row is not None and row["confidence"] == "confirmed"
    assert row["signal"] == "permission_depends_on"
    assert row["actionable"] is True


def test_a_dependency_the_person_already_has_stays_silent(isolated_home):
    policy = json.loads(json.dumps(POLICY))
    policy["users"][USER]["grants"]["permissions"] = ["chat:use", "sessions:write", "sessions:read"]
    policy["users"][USER]["grants"]["routes"] = ["/api/chat*", "/api/session*"]
    _policy_file(isolated_home).write_text(yaml.safe_dump(policy), encoding="utf-8")
    loader.set_policy_loader(None)
    _key, rows = _suggest(USER, "route", "/api/crons")
    assert _by(rows, "permission", "sessions:write") is None
    assert _by(rows, "route", "/api/session*") is None


def test_a_wildcard_route_holder_is_not_told_to_grant_the_prefix(isolated_home):
    """is_route_allowed matches an exact path or a trailing wildcard, so a
    plain membership test would report /api/chat* as lacking /api/chat."""
    _key, rows = _suggest(USER, "route", "/api/crons")
    assert _by(rows, "route", "/api/chat*") is None


def test_a_granted_route_value_actually_unblocks_the_paths_under_it(isolated_home):
    """The suggested value is the wildcard form, so approving it opens the
    child addresses and not only the bare prefix."""
    from api.governance.models import GovernanceSubject
    from api.governance.resolver import resolve_effective_access

    _key, rows = _suggest(USER, "route", "/api/crons")
    value = _by(rows, "route", "/api/session*")["value"]
    raw = yaml.safe_load(_policy_file(isolated_home).read_text(encoding="utf-8"))
    grant_requests.apply_grant_to_policy(raw, {"email": USER, "gkind": "route", "value": value})
    _policy_file(isolated_home).write_text(yaml.safe_dump(raw), encoding="utf-8")
    loader.set_policy_loader(None)
    access = resolve_effective_access(_policy(), GovernanceSubject(email=USER))
    assert access.is_route_allowed("/api/session/new")


def test_approve_already_applies_skill_and_mcp_extras_so_they_are_not_suggested(isolated_home):
    """apply_grant_to_policy writes skills.view AND skills.load for a skill, and
    opens every tool on an MCP server; re-suggesting either would be noise."""
    _key, rows = _suggest(USER, "skill", "ops/deploy")
    assert not [r for r in rows if "skills" in r["value"] or r["gkind"] == "skill"]
    _key, rows = _suggest(USER, "mcp", "context7")
    assert not [r for r in rows if r["gkind"] in ("tool", "mcp")]


def test_terminal_use_is_never_suggested_next_to_chat(isolated_home):
    """The catalog split terminal:use off chat:use on purpose."""
    _key, rows = _suggest(USER, "route", "/api/chat/stream")
    assert _by(rows, "permission", "terminal:use") is None


# ── Confidence, risk and the blocked set ────────────────────────────────────

def test_confirmed_and_heuristic_never_blur(isolated_home):
    append_audit_event(
        "deny", subject_email=USER, path="/api/reasoning", method="POST",
        reason="permission_not_allowed", extra={"resource": "config:write"},
    )
    _key, rows = _suggest(USER, "route", "/api/crons")
    assert rows
    assert {r["confidence"] for r in rows} <= {"confirmed", "heuristic"}
    confirmed = {(r["gkind"], r["value"]) for r in rows if r["confidence"] == "confirmed"}
    heuristic = {(r["gkind"], r["value"]) for r in rows if r["confidence"] == "heuristic"}
    assert not (confirmed & heuristic)


def test_governance_and_admin_capabilities_are_never_offered(isolated_home):
    for gkind, value in (("route", "/api/governance/users"), ("route", "/api/profile")):
        _key, rows = _suggest(USER, gkind, value)
        for row in rows:
            if row["gkind"] == "permission":
                assert not row["value"].startswith("governance:")
                assert not row["value"].endswith(":admin")
            if row["gkind"] == "route":
                bare = row["value"].rstrip("*")
                for method in ("GET", "POST"):
                    name = route_permission(bare, method) or ""
                    assert not name.startswith("governance:") and not name.endswith(":admin")


def test_write_shaped_permissions_are_information_and_never_a_button(isolated_home):
    """The security line: a suggestion must not become one click to a shell or
    to every settings write."""
    for path, permission in (("/api/terminal", "terminal:use"),
                             ("/api/reasoning", "config:write"),
                             ("/api/shutdown", "system:ops")):
        _key, rows = _suggest(USER, "route", path)
        row = _by(rows, "permission", permission)
        assert row is not None, f"{permission} should still be reported as information"
        assert row["actionable"] is False
        assert row["risk"] == "high"


def test_read_shaped_permissions_are_the_only_actionable_ones(isolated_home):
    _key, rows = _suggest(USER, "route", "/api/crons")
    assert _by(rows, "permission", "cron:read")["actionable"] is True
    assert _by(rows, "permission", "cron:write")["actionable"] is False
    for row in rows:
        if row["gkind"] == "permission" and row["actionable"]:
            assert row["value"] in grant_requests.GRANTABLE_PERMISSIONS


def test_the_allowlist_is_read_shaped_only(isolated_home):
    for name in grant_requests.GRANTABLE_PERMISSIONS:
        assert name.endswith(":read"), name
        assert not name.startswith("governance:"), name


def test_admins_and_a_disabled_policy_get_nothing(isolated_home):
    _key, rows = _suggest("admin@example.test", "route", "/api/crons")
    assert rows == []
    _key, rows = _suggest(BOOTSTRAP, "route", "/api/crons")
    assert rows == []

    policy = json.loads(json.dumps(POLICY))
    policy["mode"] = "off"
    _policy_file(isolated_home).write_text(yaml.safe_dump(policy), encoding="utf-8")
    loader.set_policy_loader(None)
    key = _request(USER, "route", "/api/crons")
    assert suggestions.suggestions_for(approvals.get(approvals.KIND_GRANT, key), _policy()) == []


# ── Heuristics ──────────────────────────────────────────────────────────────

def test_other_denials_by_the_same_person_surface_as_heuristics(isolated_home):
    for _ in range(3):
        append_audit_event(
            "deny", subject_email=USER, path="/api/insights", method="GET",
            reason="permission_not_allowed", extra={"resource": "analytics:read"},
        )
    append_audit_event(
        "deny", subject_email="someone.else@example.test", path="/api/logs", method="GET",
        reason="permission_not_allowed", extra={"resource": "logs:read"},
    )
    _key, rows = _suggest(USER, "route", "/api/crons")
    row = _by(rows, "permission", "analytics:read")
    assert row is not None and row["confidence"] == "heuristic"
    assert row["signal"] == "audit_co_denial"
    assert "3" in " ".join(row["evidence"])
    assert _by(rows, "permission", "logs:read") is None, "another person's denial must not leak"


def test_the_subject_match_goes_through_the_hashed_identity(isolated_home):
    append_audit_event(
        "deny", subject_email=USER.upper(), path="/api/insights", method="GET",
        reason="permission_not_allowed", extra={"resource": "analytics:read"},
    )
    rows = read_audit_events(10)
    assert rows[0]["subject_email_hash"] == _hash_identity(USER)
    _key, rows = _suggest(USER, "route", "/api/crons")
    assert _by(rows, "permission", "analytics:read") is not None


def test_a_denial_outside_the_window_is_ignored(isolated_home):
    """The audit trail stores an ISO timestamp and the request an epoch float;
    comparing them needs a parse, and a stale row must not be pulled in."""
    append_audit_event(
        "deny", subject_email=USER, path="/api/insights", method="GET",
        reason="permission_not_allowed", extra={"resource": "analytics:read"},
    )
    key = _request(USER, "route", "/api/crons")
    entry = approvals.get(approvals.KIND_GRANT, key)
    entry["requested_at"] = 1000.0  # 1970, far outside the seven day window
    registry = approvals.load()
    registry[f"{approvals.KIND_GRANT}:{key}"] = entry
    approvals.save(registry)
    rows = suggestions.suggestions_for(entry, _policy())
    assert _by(rows, "permission", "analytics:read") is None


def test_other_pending_asks_by_the_same_person_are_offered(isolated_home):
    _request(USER, "route", "/api/insights")
    key = _request(USER, "route", "/api/crons")
    rows = suggestions.suggestions_for(approvals.get(approvals.KIND_GRANT, key), _policy())
    row = _by(rows, "route", "/api/insights")
    assert row is not None and row["confidence"] == "heuristic" and row["signal"] == "open_ask"


# ── Copy ────────────────────────────────────────────────────────────────────

def test_reviewer_copy_carries_no_internals(isolated_home):
    """Plain language for a business reader: no paths, no module names, no
    status codes. Permission slugs are allowed only in the label, which renders
    inside the governance admin panel and nowhere else."""
    seen = 0
    for path in ("/api/crons", "/api/terminal", "/api/insights"):
        _key, rows = _suggest(USER, "route", path)
        for row in rows:
            seen += 1
            for field in ("why", "risk_note", "capability"):
                text = str(row[field] or "").lower()
                for token in ("/", "http", ".py", "yaml", "403", "none"):
                    assert token not in text, f"{field} leaked {token!r}: {text}"
            for line in row["evidence"]:
                assert "/" not in line and "http" not in line.lower()
    assert seen


# ── The endpoints ───────────────────────────────────────────────────────────

def test_both_endpoints_require_governance_write(isolated_home, as_user):
    key = _request(USER, "route", "/api/crons")
    as_user("viewer@example.test")
    _, handler = _call("/api/governance/approvals/suggestions", query=f"key={key}")
    assert handler.status == 403
    _, handler = _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": key, "gkind": "permission", "value": "cron:read", "decision": "approve"},
    )
    assert handler.status == 403


def test_the_route_is_classified_by_the_existing_prefix_rule(isolated_home):
    assert route_permission("/api/governance/approvals/suggestions", "GET") == "governance:read"
    assert route_permission("/api/governance/approvals/suggestions/decide", "POST") == "governance:write"


def test_reading_the_detail_grants_nothing(isolated_home, as_user):
    key = _request(USER, "route", "/api/crons")
    before = _policy_file(isolated_home).read_bytes()
    as_user("admin@example.test")
    _, handler = _call("/api/governance/approvals/suggestions", query=f"key={key}")
    assert handler.status == 200
    assert handler.body["confirmed"] >= 1
    assert _policy_file(isolated_home).read_bytes() == before


def test_an_unknown_request_is_not_found(isolated_home, as_user):
    as_user("admin@example.test")
    _, handler = _call("/api/governance/approvals/suggestions", query="key=nope|route|/api/x")
    assert handler.status == 404


def test_approving_one_leaves_every_sibling_open_and_writes_only_that_value(isolated_home, as_user):
    key = _request(USER, "route", "/api/crons")
    raw_before = yaml.safe_load(_policy_file(isolated_home).read_text(encoding="utf-8"))
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": key, "gkind": "permission", "value": "cron:read", "decision": "approve"},
    )
    assert handler.status == 200 and handler.body["ok"] is True

    raw_after = yaml.safe_load(_policy_file(isolated_home).read_text(encoding="utf-8"))
    before_perms = raw_before["users"][USER]["grants"]["permissions"]
    after_perms = raw_after["users"][USER]["grants"]["permissions"]
    assert set(after_perms) - set(before_perms) == {"cron:read"}
    raw_after["users"][USER]["grants"]["permissions"] = before_perms
    assert raw_after == raw_before, "nothing else in the policy moved"

    _, handler = _call("/api/governance/approvals/suggestions", query=f"key={key}")
    open_rows = [r for r in handler.body["suggestions"] if r["status"] == "open"]
    assert len(open_rows) == len(handler.body["suggestions"])
    assert _by(handler.body["suggestions"], "permission", "cron:write") is not None


def test_policy_save_failure_leaves_related_suggestion_retryable(isolated_home, as_user, monkeypatch):
    key = _request(USER, "route", "/api/crons")
    as_user("admin@example.test")

    def _fail_save(_raw):
        raise governance_api.GovernancePolicyError("disk unavailable")

    monkeypatch.setattr(governance_api, "save_governance_policy", _fail_save)
    _, handler = _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": key, "gkind": "permission", "value": "cron:read", "decision": "approve"},
    )
    assert handler.status == 400
    decision = suggestions.load_decisions().get(
        suggestions.decision_key(key, "permission", "cron:read")
    )
    assert decision is None or decision.get("status") != suggestions.STATUS_APPROVED

    _, detail = _call("/api/governance/approvals/suggestions", query=f"key={key}")
    row = _by(detail.body["suggestions"], "permission", "cron:read")
    assert row is not None and row["status"] == suggestions.STATUS_OPEN


def test_approve_lands_in_the_audit_trail_with_the_chain(isolated_home, as_user):
    key = _request(USER, "route", "/api/crons")
    as_user("admin@example.test")
    _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": key, "gkind": "permission", "value": "cron:read", "decision": "approve"},
    )
    rows = read_audit_events(200)
    assert any(r["event"] == "policy_change" and r["reason"] == "grant_request_approve" for r in rows)
    decision = [r for r in rows if r["reason"] == "suggestion.approve"]
    assert decision, "the suggestion decision itself must be recorded"
    extra = decision[0]["extra"]
    assert extra["origin"] == key
    assert extra["confidence"] == "confirmed"
    assert extra["signal"] == "route_needs_permission"


def test_deny_writes_no_policy_no_registry_row_and_is_audited(isolated_home, as_user):
    key = _request(USER, "route", "/api/crons")
    before = _policy_file(isolated_home).read_bytes()
    rows_before = len(approvals.load())
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": key, "gkind": "permission", "value": "cron:read", "decision": "deny"},
    )
    assert handler.body["status"] == "denied"
    assert _policy_file(isolated_home).read_bytes() == before
    assert len(approvals.load()) == rows_before
    assert any(r["reason"] == "suggestion.deny" for r in read_audit_events(200))


def test_deny_does_not_pre_empt_a_real_request_for_the_same_thing(isolated_home, as_user):
    """ingest_spool never re-creates a decided row, so a denied guess written
    into the approvals registry would silence a wall the person has not hit."""
    key = _request(USER, "route", "/api/crons")
    as_user("admin@example.test")
    _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": key, "gkind": "permission", "value": "cron:read", "decision": "deny"},
    )
    spool = config.STATE_DIR / "governance-grant-requests.json"
    spool.parent.mkdir(parents=True, exist_ok=True)
    spool.write_text(json.dumps({
        f"{USER}|route|/api/crons/list": {
            "email": USER, "gkind": "route", "value": "/api/crons/list",
            "reason": "route_not_allowed", "count": 1, "first_seen": 1.0, "last_seen": 1.0,
        }
    }), encoding="utf-8")
    grant_requests.ingest_spool()
    entry = approvals.get(approvals.KIND_GRANT, f"{USER}|route|/api/crons/list")
    assert entry is not None and entry["status"] == "pending"


def test_ignore_stays_visible_with_its_status(isolated_home, as_user):
    key = _request(USER, "route", "/api/crons")
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": key, "gkind": "permission", "value": "cron:read", "decision": "ignore"},
    )
    assert handler.body["status"] == "ignored"
    _, handler = _call("/api/governance/approvals/suggestions", query=f"key={key}")
    row = _by(handler.body["suggestions"], "permission", "cron:read")
    assert row["status"] == "ignored" and row["decided_by"] == "admin@example.test"
    assert any(r["reason"] == "suggestion.ignore" for r in read_audit_events(200))


def test_a_decision_in_one_review_does_not_silence_another(isolated_home, as_user):
    """Decisions are keyed per originating request, so setting something aside
    here never hides it in the next review where it may be a dependency."""
    first = _request(USER, "route", "/api/crons")
    as_user("admin@example.test")
    _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": first, "gkind": "permission", "value": "cron:read", "decision": "deny"},
    )
    second = _request(USER, "route", "/api/crons/list")
    _, handler = _call("/api/governance/approvals/suggestions", query=f"key={second}")
    row = _by(handler.body["suggestions"], "permission", "cron:read")
    assert row is not None and row["status"] == "open"


def test_approving_twice_changes_nothing_the_second_time(isolated_home, as_user):
    key = _request(USER, "route", "/api/crons")
    as_user("admin@example.test")
    body = {"origin_key": key, "gkind": "permission", "value": "cron:read", "decision": "approve"}
    _call("/api/governance/approvals/suggestions/decide", method="POST", body=body)
    after_first = _policy_file(isolated_home).read_bytes()
    _, handler = _call("/api/governance/approvals/suggestions/decide", method="POST", body=body)
    # The person now holds it, so the engine no longer derives it and the
    # re-derivation guard refuses the pair outright.
    assert handler.status == 404
    assert _policy_file(isolated_home).read_bytes() == after_first


def test_a_pair_the_engine_did_not_derive_is_refused(isolated_home, as_user):
    """Authorisation comes from the re-derived suggestion, never from the body,
    even when the pair would otherwise be a perfectly valid grant."""
    key = _request(USER, "route", "/api/crons")
    before = _policy_file(isolated_home).read_bytes()
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": key, "gkind": "permission", "value": "files:read", "decision": "approve"},
    )
    assert handler.status == 404
    assert _policy_file(isolated_home).read_bytes() == before


def test_a_non_actionable_suggestion_cannot_be_approved(isolated_home, as_user):
    key = _request(USER, "route", "/api/terminal")
    before = _policy_file(isolated_home).read_bytes()
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": key, "gkind": "permission", "value": "terminal:use", "decision": "approve"},
    )
    assert handler.status == 403
    assert _policy_file(isolated_home).read_bytes() == before


def test_dependencies_of_a_refused_request_cannot_be_applied(isolated_home, as_user):
    key = _request(USER, "route", "/api/crons")
    approvals.decide(approvals.KIND_GRANT, key, "reject", "admin@example.test")
    before = _policy_file(isolated_home).read_bytes()
    as_user("admin@example.test")
    _, handler = _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": key, "gkind": "permission", "value": "cron:read", "decision": "approve"},
    )
    assert handler.status == 409
    assert _policy_file(isolated_home).read_bytes() == before


def test_an_approved_suggestion_reaches_the_requester_own_view(isolated_home, as_user):
    """No notifier is built: approving materialises a grant row owned by that
    person, so it appears in Settings > Access requests through the surface
    that is already there."""
    key = _request(USER, "route", "/api/crons")
    as_user("admin@example.test")
    _call(
        "/api/governance/approvals/suggestions/decide", method="POST",
        body={"origin_key": key, "gkind": "permission", "value": "cron:read", "decision": "approve"},
    )
    as_user(USER)
    _, handler = _call("/api/governance/approvals/mine")
    mine = [r for r in handler.body["requests"] if r["key"] == f"{USER}|permission|cron:read"]
    assert mine and mine[0]["status"] == "approved"
    # And the label a non-admin reads is a sentence, not a permission slug.
    assert "cron:read" not in mine[0]["label"]


# ── Defense in depth on the policy writer itself ────────────────────────────

def test_apply_grant_refuses_a_permission_outside_the_allowlist(isolated_home):
    for value in ("terminal:use", "config:write", "governance:write", "profiles:admin"):
        raw = {"users": {USER: {"grants": {}}}}
        assert grant_requests.apply_grant_to_policy(
            raw, {"email": USER, "gkind": "permission", "value": value}
        ) is None
        assert raw["users"][USER]["grants"] == {}


def test_apply_grant_writes_an_allowlisted_permission(isolated_home):
    raw = {"users": {USER: {"grants": {}}}}
    result = grant_requests.apply_grant_to_policy(
        raw, {"email": USER, "gkind": "permission", "value": "cron:read"}
    )
    assert result is not None
    assert raw["users"][USER]["grants"]["permissions"] == ["cron:read"]


def test_materialise_refuses_a_permission_outside_the_allowlist(isolated_home):
    assert grant_requests.materialise_suggested_grant(USER, "permission", "terminal:use") is None
    assert approvals.load() == {}


# ── Source inspection, house style ──────────────────────────────────────────

REPO = Path(__file__).resolve().parent.parent
GOV_JS = (REPO / "static" / "governance.js").read_text(encoding="utf-8")
GOV_API = (REPO / "api" / "governance_api.py").read_text(encoding="utf-8")


def test_the_two_confidence_levels_are_rendered_apart():
    assert "governance_sug_confirmed" in GOV_JS and "governance_sug_heuristic" in GOV_JS
    assert "block('confirmed'" in GOV_JS and "block('heuristic'" in GOV_JS


def test_the_decision_buttons_use_data_attributes_not_inline_handlers():
    assert "data-gov-suggestion=" in GOV_JS
    assert 'onclick="_govDecideSuggestion' not in GOV_JS
    assert "onclick=" not in GOV_JS[GOV_JS.index("function _govSuggestionHtml"):][:2600]


def test_approve_reuses_the_existing_grant_decision_path():
    """One policy writer, not two: the lock, the policy_change audit and the
    profile sync are the existing ones."""
    block = GOV_API[GOV_API.index("def _handle_suggestion_decide"):][:6000]
    assert "_handle_grant_request_decide(" in block
    assert "save_governance_policy" not in block
    assert "policy_mutation_lock" not in block
