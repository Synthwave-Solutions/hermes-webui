"""Loader validation of the managed-service policy sections (plan 2.5, 3.6).

installation, organization and departments, plus the delegable and external
flags, are rendered from client.yaml. The loader refuses a policy that would
let a delegated admin hand out more than a platform admin allowed, and the
policy write paths refuse any change to the render-stamped organization.id
and installation.kind (package W3a).
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
from api.governance import loader  # noqa: E402
from api.governance.enforce import evaluate_request  # noqa: E402
from api.governance.loader import (  # noqa: E402
    GovernancePolicyError,
    PolicyImmutableFieldError,
    immutable_field_changes,
    parse_governance_policy,
    policy_etag,
    save_governance_policy,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "managed_service" / "org_acme.yaml"
FIXTURE = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))


def _raw() -> dict:
    return copy.deepcopy(FIXTURE["policy"])


def _refused(raw, match):
    with pytest.raises(GovernancePolicyError, match=match):
        parse_governance_policy(raw)


# ── The shared fixture parses into typed sections ────────────────────────────

def test_fixture_policy_parses_with_typed_sections():
    policy = parse_governance_policy(_raw())
    assert policy.installation_kind == "client" and not policy.is_hq
    assert policy.organization.id == "org_acme"
    assert policy.organization.name == "Acme"
    assert policy.organization.admins == ("it.lead@acme.example", "owner@acme.example")
    assert policy.organization.billing_admins == ("finance@acme.example", "owner@acme.example")
    sales = policy.departments["sales"]
    assert (sales.name, sales.group, sales.admins) == ("Sales", "dept-sales", ("head.sales@acme.example",))
    assert sales.assignable_roles == ("viewer", "operator")
    assert sales.assignable_groups == ("dept-sales", "all-staff")
    assert policy.roles["operator"].delegable and not policy.roles["admin"].delegable
    assert policy.groups["dept-sales"].delegable and not policy.groups["administrators"].delegable
    assert not any(group.external for group in policy.groups.values())


def test_fixture_sections_equal_the_expected_policy_sections():
    raw = _raw()
    expected = FIXTURE["expected"]["policy_sections"]
    for key in ("installation", "organization", "departments"):
        assert raw[key] == expected[key]


def test_policies_without_the_new_sections_are_unchanged():
    raw = _raw()
    for key in ("installation", "organization", "departments"):
        raw.pop(key)
    policy = parse_governance_policy(raw)
    assert (policy.installation_kind, policy.organization, policy.departments) == ("", None, {})


def test_hq_policy_with_external_groups_and_no_organization_parses():
    raw = _raw()
    raw.pop("organization")
    raw.pop("departments")
    raw["installation"] = {"kind": "hq"}
    raw["groups"]["clients"] = {"external": True, "roles": [], "sso_groups": []}
    policy = parse_governance_policy(raw)
    assert policy.is_hq and policy.groups["clients"].external


def test_email_lists_are_normalised_and_deduplicated():
    raw = _raw()
    raw["organization"]["admins"] = [" Owner@ACME.example", "owner@acme.example"]
    assert parse_governance_policy(raw).organization.admins == ("owner@acme.example",)


# ── organization and installation refusals ───────────────────────────────────

def test_refuses_an_organization_block_at_hq():
    raw = _raw()
    raw["installation"] = {"kind": "hq"}
    raw.pop("departments")
    _refused(raw, "hq installation has no organization")


def test_refuses_an_organization_block_next_to_external_groups():
    raw = _raw()
    raw["groups"]["freelancers"] = {"external": True, "roles": [], "sso_groups": []}
    _refused(raw, "external groups")


@pytest.mark.parametrize("installation", [{"kind": "cloud"}, {"kind": ""}, {}, "client", ["hq"]])
def test_refuses_an_invalid_installation_block(installation):
    raw = _raw()
    raw["installation"] = installation
    _refused(raw, "installation")


@pytest.mark.parametrize("org_id", [None, "", "Org Acme", "../acme", "org/acme", 7, "a" * 65])
def test_refuses_an_invalid_organization_id(org_id):
    raw = _raw()
    raw["organization"]["id"] = org_id
    _refused(raw, "organization id")


@pytest.mark.parametrize("admins", ["owner@acme.example", ["not-an-email"], [7], ["a@b"], ["x y@acme.example"]])
def test_refuses_invalid_admin_lists(admins):
    raw = _raw()
    raw["organization"]["admins"] = admins
    _refused(raw, "organization admins")


def test_refuses_departments_without_an_organization():
    raw = _raw()
    raw.pop("organization")
    _refused(raw, "departments need an organization")


# ── department refusals ──────────────────────────────────────────────────────

@pytest.mark.parametrize("key", ["Sales", "sales team", "-sales", "sales.eu", "s" * 41])
def test_refuses_an_invalid_department_key(key):
    raw = _raw()
    raw["departments"][key] = raw["departments"].pop("sales")
    _refused(raw, "department keys")


def test_refuses_a_non_delegable_assignable_role():
    raw = _raw()
    raw["departments"]["sales"]["assignable_roles"].append("admin")
    _refused(raw, "roles marked delegable")


def test_refuses_an_unknown_assignable_role():
    raw = _raw()
    raw["departments"]["sales"]["assignable_roles"].append("ghost")
    _refused(raw, "roles marked delegable")


def test_refuses_a_non_delegable_assignable_group():
    raw = _raw()
    raw["departments"]["finance"]["assignable_groups"].append("administrators")
    _refused(raw, "groups marked delegable")


def test_refuses_an_unknown_department_group():
    raw = _raw()
    raw["departments"]["sales"]["group"] = "dept-ghost"
    _refused(raw, "unknown group")


def test_refuses_a_missing_department_group():
    raw = _raw()
    raw["departments"]["sales"].pop("group")
    _refused(raw, "needs a group")


@pytest.mark.parametrize("change", [
    {"roles": ["admin"]},
    {"roles": ["tech_lead"]},
    {"roles": ["ghost"]},
    {"grants": {"permissions": ["terminal:use"]}},
    {"grants": {"permissions": ["governance:read"]}},
    {"grants": {"permissions": ["files:*"]}},
    {"grants": {"permissions": ["support:admin"]}},
    {"grants": {"permissions": ["screen:watch"]}},
    {"grants": {"cli": {"commands": ["git"]}}},
    {"grants": {"mcp": {"servers": ["notion"]}}},
    {"grants": {"skills": {"manage": ["notes"]}}},
    {"grants": {"env": {"vars": ["API_KEY"]}}},
    {"grants": {"files": {"read_roots": ["/**"]}}},
    {"grants": {"routes": ["*"]}},
])
def test_refuses_a_privileged_department_group(change):
    raw = _raw()
    raw["groups"]["dept-sales"].update(copy.deepcopy(change))
    _refused(raw, "must not be privileged")


def test_a_delegable_role_with_a_privileged_grant_makes_the_group_privileged():
    raw = _raw()
    raw["roles"]["operator"]["grants"]["permissions"].append("terminal:use")
    raw["groups"]["dept-sales"]["roles"] = ["operator"]
    _refused(raw, "must not be privileged")


def test_a_plain_delegable_role_on_the_department_group_is_allowed():
    raw = _raw()
    raw["groups"]["dept-sales"]["roles"] = ["operator"]
    raw["groups"]["dept-sales"]["grants"] = {"profiles": ["sales-bot"], "workspaces": ["/srv/sales"]}
    assert parse_governance_policy(raw).departments["sales"].group == "dept-sales"


@pytest.mark.parametrize("sso", [["Sales"], ["hd:acme.example"]])
def test_refuses_an_sso_synced_department_group(sso):
    raw = _raw()
    raw["groups"]["dept-sales"]["sso_groups"] = sso
    _refused(raw, "identity provider")


def test_refuses_an_hd_department_group():
    raw = _raw()
    raw["groups"]["hd:acme.example"] = {"delegable": True, "roles": [], "sso_groups": []}
    raw["departments"]["sales"]["group"] = "hd:acme.example"
    _refused(raw, "identity provider")


def test_refuses_two_departments_on_one_group():
    raw = _raw()
    raw["departments"]["finance"]["group"] = "dept-sales"
    _refused(raw, "shares its group")


@pytest.mark.parametrize("flag,owner", [("delegable", "roles"), ("delegable", "groups"), ("external", "groups")])
def test_refuses_a_flag_that_is_not_a_boolean(flag, owner):
    raw = _raw()
    target = raw[owner]["operator" if owner == "roles" else "all-staff"]
    target[flag] = "yes"
    _refused(raw, f"{flag} must be true or false")


# ── An invalid block fails closed through the enforcement hook ───────────────

def test_an_invalid_block_fails_closed_for_every_api_request():
    raw = _raw()
    raw["departments"]["sales"]["assignable_roles"].append("admin")

    def load():
        return parse_governance_policy(raw)

    loader.set_policy_loader(load)
    try:
        decision = evaluate_request({"email": "owner@acme.example", "groups": [], "claims_subset": {},
                                     "method": "oidc"}, "GET", "/api/sessions")
        assert (decision.allow, decision.reason) == (False, "policy_error")
    finally:
        loader.set_policy_loader(None)


# ── organization.id and installation.kind are immutable ──────────────────────

def test_immutable_field_changes_detects_add_change_and_remove():
    base = _raw()
    assert immutable_field_changes(base, copy.deepcopy(base)) == []
    changed = copy.deepcopy(base)
    changed["organization"]["id"] = "org_other"
    assert immutable_field_changes(base, changed) == ["organization.id"]
    removed = copy.deepcopy(base)
    removed.pop("organization")
    assert immutable_field_changes(base, removed) == ["organization.id"]
    assert immutable_field_changes(removed, base) == ["organization.id"]
    kind = copy.deepcopy(base)
    kind["installation"] = {"kind": "hq"}
    assert immutable_field_changes(base, kind) == ["installation.kind"]
    no_block = copy.deepcopy(base)
    no_block.pop("installation")
    assert immutable_field_changes(base, no_block) == ["installation.kind"]
    renamed = copy.deepcopy(base)
    renamed["organization"]["name"] = "Acme Holding"
    renamed["organization"]["admins"] = ["owner@acme.example"]
    assert immutable_field_changes(base, renamed) == []


@pytest.fixture
def policy_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_WEBUI_GOVERNANCE_POLICY", raising=False)
    loader.set_policy_loader(None)
    path = tmp_path / "dashboard-governance.yaml"
    path.write_text(yaml.safe_dump(_raw()), encoding="utf-8")
    yield path
    loader.set_policy_loader(None)


def test_save_refuses_a_changed_organization_id(policy_home):
    changed = _raw()
    changed["organization"]["id"] = "org_other"
    before = policy_home.read_bytes()
    with pytest.raises(PolicyImmutableFieldError) as info:
        save_governance_policy(changed)
    assert info.value.field == "organization.id"
    assert policy_home.read_bytes() == before


def test_save_refuses_a_changed_installation_kind(policy_home):
    changed = _raw()
    changed.pop("organization")
    changed.pop("departments")
    changed["installation"] = {"kind": "hq"}
    with pytest.raises(PolicyImmutableFieldError) as info:
        save_governance_policy(changed)
    assert info.value.field in {"organization.id", "installation.kind"}


def test_save_allows_ordinary_edits_on_an_organisation_policy(policy_home):
    edited = _raw()
    edited["users"]["new.person@acme.example"] = {"roles": ["viewer"], "groups": ["all-staff"]}
    save_governance_policy(edited)
    assert "new.person@acme.example" in loader.get_policy().users


def test_save_refuses_a_first_organization_block_on_an_existing_policy(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    plain = _raw()
    for key in ("installation", "organization", "departments"):
        plain.pop(key)
    save_governance_policy(plain)
    with pytest.raises(PolicyImmutableFieldError):
        save_governance_policy(_raw())


class _Handler:
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


def _as(monkeypatch, email):
    identity = {"email": email, "groups": [], "claims_subset": {}, "method": "oidc"}
    monkeypatch.setattr(governance_api, "_caller_identity", lambda handler: identity)


def _post(path, body):
    handler = _Handler(body=body, headers={"If-Match": policy_etag(dict(loader.get_policy().raw))})
    assert governance_api.handle_governance_api(handler, SimpleNamespace(path=path, query=""), "POST")
    return handler


@pytest.mark.parametrize("mutation", ["change_id", "drop_organization", "flip_kind", "drop_installation"])
def test_policy_replace_refuses_render_stamped_changes_even_for_bootstrap_admins(policy_home, monkeypatch, mutation):
    _as(monkeypatch, "ops@synthwave.example")
    body = _raw()
    if mutation == "change_id":
        body["organization"]["id"] = "org_other"
    elif mutation == "drop_organization":
        body.pop("organization")
        body.pop("departments")
    elif mutation == "flip_kind":
        body["installation"] = {"kind": "hq"}
        body.pop("organization")
        body.pop("departments")
    else:
        body.pop("installation")
    before = policy_home.read_bytes()
    handler = _post("/api/governance/policy", body)
    assert handler.status == 400
    assert handler.body["error"] == "immutable_field"
    assert handler.body["field"] in {"organization.id", "installation.kind"}
    assert policy_home.read_bytes() == before


def test_policy_replace_with_unchanged_stamps_still_works(policy_home, monkeypatch):
    _as(monkeypatch, "ops@synthwave.example")
    body = _raw()
    body["users"]["new.person@acme.example"] = {"roles": ["viewer"], "groups": ["all-staff"]}
    handler = _post("/api/governance/policy", body)
    assert handler.status == 200, handler.body
    assert "new.person@acme.example" in loader.get_policy().users


def test_mutate_policy_refuses_an_organization_id_change(policy_home, monkeypatch):
    before = policy_home.read_bytes()
    handler = _Handler(headers={"If-Match": policy_etag(dict(loader.get_policy().raw))})

    def mutate(raw):
        raw["organization"] = dict(raw["organization"], id="org_other")
        return None, None

    governance_api._mutate_policy(handler, SimpleNamespace(path="/api/governance/test"),
                                  governance_api.GovernanceSubject(email="ops@synthwave.example"),
                                  op="test", target="organization", mutate=mutate)
    assert handler.status == 400
    assert handler.body == {
        "error": "immutable_field",
        "field": "organization.id",
        "message": "organization.id is set by the installation setup and cannot be changed here",
    }
    assert policy_home.read_bytes() == before


def test_mutate_policy_refuses_an_in_place_installation_kind_change(policy_home, monkeypatch):
    handler = _Handler(headers={"If-Match": policy_etag(dict(loader.get_policy().raw))})

    def mutate(raw):
        raw["installation"]["kind"] = "hq"
        return None, None

    governance_api._mutate_policy(handler, SimpleNamespace(path="/api/governance/test"),
                                  governance_api.GovernanceSubject(email="ops@synthwave.example"),
                                  op="test", target="installation", mutate=mutate)
    assert handler.status == 400 and handler.body["field"] == "installation.kind"
    # The refused in-place edit did not leak into the cached policy.
    assert loader.get_policy().raw["installation"] == {"kind": "client"}


def test_user_edits_through_mutate_policy_still_work_on_an_organisation_policy(policy_home, monkeypatch):
    _as(monkeypatch, "ops@synthwave.example")
    handler = _post("/api/governance/users", {"email": "new.person@acme.example",
                                              "entry": {"roles": ["viewer"], "groups": ["all-staff"]}})
    assert handler.status == 200, handler.body
    policy = loader.get_policy()
    assert "new.person@acme.example" in policy.users
    assert policy.organization.id == "org_acme"


# ── The group editor keeps the new flags ─────────────────────────────────────

def test_group_update_without_the_flags_keeps_them(policy_home, monkeypatch):
    """The governance group editor sends description, sso_groups, roles and
    grants only; an edit of a department's group must not drop delegable
    (the department would then be refused as assigning a non-delegable group)."""
    _as(monkeypatch, "ops@synthwave.example")
    handler = _post("/api/governance/groups/update", {
        "name": "dept-sales",
        "entry": {"description": "Sales, renamed", "sso_groups": [], "roles": []},
    })
    assert handler.status == 200, handler.body
    group = loader.get_policy().groups["dept-sales"]
    assert group.delegable is True and group.description == "Sales, renamed"


def test_group_update_can_set_and_clear_the_flags(policy_home, monkeypatch):
    _as(monkeypatch, "ops@synthwave.example")
    handler = _post("/api/governance/groups/update", {
        "name": "administrators", "entry": {"roles": ["admin"], "delegable": False},
    })
    assert handler.status == 200, handler.body
    assert loader.get_policy().groups["administrators"].delegable is False
    # all-staff is assignable by the Sales department: clearing its flag is
    # refused by the loader rule, and nothing is written.
    before = policy_home.read_bytes()
    handler = _post("/api/governance/groups/update", {
        "name": "all-staff", "entry": {"roles": [], "delegable": False},
    })
    assert handler.status == 400 and "delegable" in handler.body["message"]
    assert policy_home.read_bytes() == before


def test_group_flags_must_be_booleans_and_external_is_refused_next_to_an_organization(policy_home, monkeypatch):
    _as(monkeypatch, "ops@synthwave.example")
    handler = _post("/api/governance/groups", {"name": "guests", "entry": {"roles": [], "delegable": "yes"}})
    assert handler.status == 400 and "true or false" in handler.body["message"]
    handler = _post("/api/governance/groups", {"name": "freelancers", "entry": {"roles": [], "external": True}})
    assert handler.status == 400 and "external groups" in handler.body["message"]
    assert "freelancers" not in loader.get_policy().groups
