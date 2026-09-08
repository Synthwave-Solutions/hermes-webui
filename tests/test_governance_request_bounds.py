"""A human capability decision cannot override a managed resource denial."""
from copy import deepcopy
from urllib.parse import urlparse

import pytest

from api import governance_api, approvals
from api.governance.loader import parse_governance_policy
from api.governance.models import GovernanceSubject


@pytest.mark.parametrize("kind,value,deny", [
    ("tool", "terminal", {"tools": {"builtins": ["terminal"]}}),
    ("profile", "other-tenant", {}),
])
def test_rejected_capability_grant_neither_changes_cached_policy_nor_decides_queue(tmp_path, monkeypatch, kind, value, deny):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    raw = {"mode": "enforce", "roles": {"member": {"grants": {
        "tools": {"builtins": ["*"]}, "profiles": ["alice"]}}}, "users": {
        "alice@example.test": {"roles": ["member"], "access_level": "elevated", "access_mode": "whitelist",
                               "grants": {"tools": {"builtins": ["read_file"]}}, "deny": deny}}}
    policy = parse_governance_policy(raw)
    original = deepcopy(policy.raw)
    entry = {"status": "pending", "kind": "grant", "payload": {
        "email": "alice@example.test", "gkind": kind, "value": value}}
    monkeypatch.setattr(approvals, "get", lambda *a: entry)
    monkeypatch.setattr(approvals, "decide", lambda *a, **kw: pytest.fail("must not decide denied request"))
    monkeypatch.setattr(governance_api, "get_policy", lambda: policy)
    monkeypatch.setattr(governance_api, "save_governance_policy", lambda *a: pytest.fail("must not persist out-of-scope grant"))
    responses = []
    monkeypatch.setattr(governance_api, "j", lambda h, payload, status=200: responses.append((status, payload)))
    governance_api._handle_grant_request_decide(object(), urlparse("/api/governance/approvals/decide"), policy,
        GovernanceSubject(email="admin@example.test"), {"key": "pending-request", "decision": "approve"})
    assert responses[-1][0] == 403
    assert policy.raw == original
    assert entry["status"] == "pending"
