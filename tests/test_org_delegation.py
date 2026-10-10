"""delegated_scope() and the organisation id stamp (plan 3.6, package W3a).

The expectations come from the shared fixture
tests/fixtures/managed_service/org_acme.yaml, which the STACK render (C5)
and the cockpit import (C1) read too: ``expected.delegated_scope``,
``expected.org_roles``, ``expected.acting_departments`` and
``expected.org_id``.
"""
import copy
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import governance_api  # noqa: E402
from api.governance import delegation, enforce, loader  # noqa: E402
from api.governance.delegation import DelegatedScope, delegated_scope  # noqa: E402
from api.governance.loader import parse_governance_policy  # noqa: E402
from api.governance.models import GovernanceSubject  # noqa: E402

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "managed_service" / "org_acme.yaml"
FIXTURE = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
EXPECTED = FIXTURE["expected"]


def _raw() -> dict:
    return copy.deepcopy(FIXTURE["policy"])


def _policy(raw=None):
    return parse_governance_policy(raw if raw is not None else _raw())


def _hq_raw() -> dict:
    raw = _raw()
    raw["installation"] = {"kind": "hq"}
    raw.pop("organization")
    raw.pop("departments")
    return raw


def _subject(email, provider="oidc"):
    return GovernanceSubject(email=email, provider=provider)


# ── The shared fixture ───────────────────────────────────────────────────────

@pytest.mark.parametrize("email", sorted(EXPECTED["delegated_scope"]))
def test_scope_matches_the_shared_fixture(email):
    assert delegated_scope(_policy(), _subject(email)).to_dict() == EXPECTED["delegated_scope"][email]


def test_every_fixture_person_is_covered():
    people = set(FIXTURE["policy"]["users"]) | set(FIXTURE["policy"]["bootstrap_admins"])
    assert people <= set(EXPECTED["delegated_scope"])


@pytest.mark.parametrize("email", sorted(EXPECTED["org_roles"]))
def test_org_roles_match_the_shared_fixture(email):
    assert delegation.org_roles_for(_policy(), email) == EXPECTED["org_roles"][email]


@pytest.mark.parametrize("email", sorted(EXPECTED["acting_departments"]))
def test_department_membership_matches_the_shared_fixture(email):
    policy = _policy()
    assert {
        "member_of": list(delegation.member_departments(policy, email)),
        "admin_of": list(delegation.admin_departments(policy, email)),
    } == EXPECTED["acting_departments"][email]


def test_organization_id_matches_the_shared_fixture():
    assert delegation.organization_id(_policy()) == EXPECTED["org_id"] == "org_acme"


def test_department_members_come_from_the_policy():
    policy = _policy()
    assert delegation.department_members(policy, "sales") == ("head.sales@acme.example", "rep.sales@acme.example")
    assert delegation.department_members(policy, "finance") == (
        "clerk.finance@acme.example", "finance@acme.example", "head.finance@acme.example")
    assert delegation.department_members(policy, "unknown") == ()


# ── Resolution rules ─────────────────────────────────────────────────────────

def test_widest_designation_wins():
    raw = _raw()
    raw["departments"]["sales"]["admins"].append("owner@acme.example")
    raw["departments"]["sales"]["admins"].append("finance@acme.example")
    policy = _policy(raw)
    assert delegated_scope(policy, _subject("owner@acme.example")).scope == "org"
    assert delegated_scope(policy, _subject("finance@acme.example")).scope == "billing"
    raw["organization"]["admins"].append("ops@synthwave.example")
    assert delegated_scope(_policy(raw), _subject("ops@synthwave.example")).scope == "platform"


def test_several_departments_are_all_listed_sorted():
    raw = _raw()
    raw["departments"]["finance"]["admins"].append("head.sales@acme.example")
    scope = delegated_scope(_policy(raw), _subject("head.sales@acme.example"))
    assert scope == DelegatedScope("department", ("finance", "sales"))
    assert scope.to_dict() == {"scope": "department", "departments": ["finance", "sales"]}


def test_membership_is_by_exact_normalised_email():
    policy = _policy()
    assert delegated_scope(policy, _subject("  Owner@ACME.example ")).scope == "org"
    assert delegated_scope(policy, _subject("owner@acme.example.evil")).scope == "none"
    assert delegated_scope(policy, _subject("wner@acme.example")).scope == "none"


def test_grants_roles_groups_and_wildcards_never_designate():
    raw = _raw()
    # A policy user holding the admin role (governance:write) through a group
    # and the operational wildcard as a blacklist account, but no access_level
    # admin and no designation.
    raw["users"]["role.admin@acme.example"] = {"roles": ["admin"], "groups": ["administrators"]}
    raw["users"]["star@acme.example"] = {"grants": {"permissions": ["*", "org:*"]}}
    policy = _policy(raw)
    for email in ("role.admin@acme.example", "star@acme.example", "power.user@acme.example"):
        assert delegated_scope(policy, _subject(email)).scope == "none", email


def test_access_level_admin_is_platform():
    policy = _policy()
    assert delegated_scope(policy, _subject("it.admin@acme.example")).scope == "platform"
    assert delegation.is_platform_admin(policy, "it.admin@acme.example")
    assert not delegation.is_platform_admin(policy, "power.user@acme.example")


def test_hq_gives_platform_or_none_only():
    policy = _policy(_hq_raw())
    assert policy.is_hq
    assert delegated_scope(policy, _subject("ops@synthwave.example")).scope == "platform"
    assert delegated_scope(policy, _subject("it.admin@acme.example")).scope == "platform"
    for email in ("owner@acme.example", "finance@acme.example", "head.sales@acme.example", "rep.sales@acme.example"):
        assert delegated_scope(policy, _subject(email)).scope == "none", email
    assert delegation.organization_id(policy) == ""


def test_no_organization_block_gives_platform_or_none_only():
    raw = _raw()
    raw.pop("organization")
    raw.pop("departments")
    raw.pop("installation")
    policy = _policy(raw)
    assert delegated_scope(policy, _subject("ops@synthwave.example")).scope == "platform"
    assert delegated_scope(policy, _subject("owner@acme.example")).scope == "none"
    assert delegation.organization_id(policy) == ""


def test_auth_disabled_and_anonymous_are_none():
    policy = _policy()
    assert delegated_scope(policy, _subject("ops@synthwave.example", provider="auth_disabled")).scope == "none"
    assert delegated_scope(policy, GovernanceSubject()).scope == "none"
    assert delegated_scope(policy, None).scope == "none"
    assert delegated_scope(None, _subject("ops@synthwave.example")).scope == "none"


def test_a_broken_policy_object_fails_closed_to_none():
    broken = SimpleNamespace(bootstrap_admins=None, users=None)
    assert delegated_scope(broken, _subject("ops@synthwave.example")) == DelegatedScope()


def test_scope_to_dict_shapes():
    assert DelegatedScope().to_dict() == {"scope": "none"}
    assert DelegatedScope("org").to_dict() == {"scope": "org"}
    assert DelegatedScope("department", ("sales",)).covers_department("sales")
    assert not DelegatedScope("department", ("sales",)).covers_department("finance")
    assert DelegatedScope("org").covers_department("finance")
    assert not DelegatedScope("billing").covers_department("finance")


# ── organization.id stamping (enforce.py) ────────────────────────────────────

def _identity(email, method="oidc"):
    return {"email": email, "groups": [], "claims_subset": {"sub": f"sub-{email}"}, "method": method}


def test_subject_carries_the_organisation_id_from_the_policy():
    subject = enforce.subject_from_identity(_identity("rep.sales@acme.example"), _policy())
    assert subject.org_id == "org_acme"
    assert enforce.subject_from_identity(_identity("rep.sales@acme.example"), _policy(_hq_raw())).org_id == ""
    assert enforce.subject_from_identity(None, _policy()).org_id == ""


def test_subject_stamp_uses_the_current_policy_when_none_is_passed():
    policy = _policy()
    loader.set_policy_loader(lambda: policy)
    try:
        assert enforce.subject_from_identity(_identity("owner@acme.example")).org_id == "org_acme"
    finally:
        loader.set_policy_loader(None)


def test_subject_stamp_is_empty_when_the_policy_cannot_be_loaded():
    def broken():
        raise loader.GovernancePolicyError("broken")

    loader.set_policy_loader(broken)
    try:
        assert enforce.subject_from_identity(_identity("owner@acme.example")).org_id == ""
    finally:
        loader.set_policy_loader(None)


# ── /api/governance/me exposes delegated_scope ───────────────────────────────

class _Handler:
    def __init__(self):
        self.headers = {}
        self.rfile = io.BytesIO(b"")
        self.wfile = io.BytesIO()
        self.status = None
        self.response_headers = {}

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers[key] = value

    def end_headers(self):
        pass

    @property
    def body(self):
        return json.loads(self.wfile.getvalue().decode("utf-8"))


@pytest.fixture
def fixture_policy_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_WEBUI_GOVERNANCE_POLICY", raising=False)
    loader.set_policy_loader(None)
    (tmp_path / "dashboard-governance.yaml").write_text(yaml.safe_dump(_raw()), encoding="utf-8")
    yield tmp_path
    loader.set_policy_loader(None)


def _me(monkeypatch, email):
    monkeypatch.setattr(governance_api, "_caller_identity", lambda handler: _identity(email))
    handler = _Handler()
    assert governance_api.handle_governance_api(handler, SimpleNamespace(path="/api/governance/me", query=""), "GET")
    assert handler.status == 200
    return handler.body


@pytest.mark.parametrize("email", [
    "ops@synthwave.example", "owner@acme.example", "finance@acme.example",
    "head.sales@acme.example", "rep.sales@acme.example", "stranger@elsewhere.example",
])
def test_me_exposes_the_delegated_scope(fixture_policy_file, monkeypatch, email):
    me = _me(monkeypatch, email)
    assert me["delegated_scope"] == EXPECTED["delegated_scope"][email]


def test_me_effective_access_subject_carries_the_org_id(fixture_policy_file, monkeypatch):
    me = _me(monkeypatch, "rep.sales@acme.example")
    assert me["effective_access"]["subject"]["org_id"] == "org_acme"
