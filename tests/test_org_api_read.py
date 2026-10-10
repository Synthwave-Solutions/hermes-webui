"""Read-only organisation routes /api/org/* (plan 3.6, package W3a).

Each handler decides from delegated_scope() itself, in every governance
mode: a member without a designation gets nothing, a department admin sees
only their own departments, an organisation admin sees the whole
organisation. The installation's policy is the shared org_acme fixture,
written to an isolated HERMES_HOME; the caller identity is injected.
"""
import copy
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import org_api  # noqa: E402
from api.governance import enforce, loader  # noqa: E402

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "managed_service" / "org_acme.yaml"
FIXTURE = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))

ROUTES = ("/api/org/overview", "/api/org/departments", "/api/org/people", "/api/org/approvals", "/api/org/usage")
PLATFORM = ("ops@synthwave.example", "it.admin@acme.example")
ORG = ("owner@acme.example", "it.lead@acme.example")
BILLING = ("finance@acme.example",)
DEPARTMENT = ("head.sales@acme.example", "head.finance@acme.example")
NOBODY = ("rep.sales@acme.example", "clerk.finance@acme.example", "power.user@acme.example",
          "stranger@elsewhere.example")

# Which designations each route admits (plan 3.6; the docstring of api/org_api.py).
ADMITS = {
    "/api/org/overview": {"platform", "org", "billing", "department"},
    "/api/org/departments": {"platform", "org", "department"},
    "/api/org/people": {"platform", "org", "department"},
    "/api/org/approvals": {"platform", "org", "department"},
    "/api/org/usage": {"platform", "org", "billing", "department"},
}
SCOPE_OF = {**{e: "platform" for e in PLATFORM}, **{e: "org" for e in ORG}, **{e: "billing" for e in BILLING},
            **{e: "department" for e in DEPARTMENT}, **{e: "none" for e in NOBODY}}


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


def _raw() -> dict:
    return copy.deepcopy(FIXTURE["policy"])


@pytest.fixture
def home(tmp_path, monkeypatch):
    from api import config

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_WEBUI_GOVERNANCE_POLICY", raising=False)
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "webui")
    loader.set_policy_loader(None)
    yield tmp_path
    loader.set_policy_loader(None)


@pytest.fixture
def write_policy(home):
    def _write(raw=None):
        (home / "dashboard-governance.yaml").write_text(yaml.safe_dump(raw if raw is not None else _raw()),
                                                        encoding="utf-8")
    _write()
    return _write


@pytest.fixture
def caller(monkeypatch):
    state = SimpleNamespace(email=None, method="oidc")

    def identity(handler):
        if state.email is None:
            return None
        return {"email": state.email, "groups": [], "claims_subset": {}, "method": state.method}

    monkeypatch.setattr(enforce, "_request_identity", identity)
    return state


def _get(caller, path, email):
    caller.email = email
    handler = _Handler()
    handled = org_api.handle_get(handler, SimpleNamespace(path=path, query=""))
    return handled, handler


# ── Scope matrix ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", ROUTES)
@pytest.mark.parametrize("email", PLATFORM + ORG + BILLING + DEPARTMENT + NOBODY)
def test_scope_matrix(write_policy, caller, path, email):
    handled, handler = _get(caller, path, email)
    assert handled is True
    if SCOPE_OF[email] in ADMITS[path]:
        assert handler.status == 200, (path, email, handler.body)
    else:
        assert handler.status == 403, (path, email)
        assert handler.body == {"error": "forbidden", "reason": "delegated_scope"}


@pytest.mark.parametrize("path", ROUTES)
def test_unauthenticated_and_auth_disabled_get_nothing(write_policy, caller, path):
    handled, handler = _get(caller, path, None)
    assert (handled, handler.status) == (True, 403)
    caller.method = "auth_disabled"
    handled, handler = _get(caller, path, "ops@synthwave.example")
    assert (handled, handler.status) == (True, 403)


@pytest.mark.parametrize("mode", ["off", "report_only", "enforce"])
def test_the_handler_decides_in_every_mode(write_policy, caller, mode):
    raw = _raw()
    raw["mode"] = mode
    write_policy(raw)
    assert _get(caller, "/api/org/people", "rep.sales@acme.example")[1].status == 403
    assert _get(caller, "/api/org/people", "owner@acme.example")[1].status == 200


# ── No organisation here: 404 like an unknown route ──────────────────────────

@pytest.mark.parametrize("path", ROUTES)
def test_hq_answers_404_even_for_platform_admins(write_policy, caller, path):
    raw = _raw()
    raw.pop("organization")
    raw.pop("departments")
    raw["installation"] = {"kind": "hq"}
    write_policy(raw)
    handled, handler = _get(caller, path, "ops@synthwave.example")
    assert handled is False and handler.status is None


@pytest.mark.parametrize("path", ROUTES)
def test_no_organization_block_answers_404(write_policy, caller, path):
    raw = _raw()
    for key in ("installation", "organization", "departments"):
        raw.pop(key)
    write_policy(raw)
    handled, handler = _get(caller, path, "owner@acme.example")
    assert handled is False and handler.status is None


def test_unknown_org_path_is_not_claimed(write_policy, caller):
    handled, handler = _get(caller, "/api/org/secrets", "owner@acme.example")
    assert handled is False and handler.status is None
    assert org_api.handle_get(_Handler(), None) is False


def test_policy_error_answers_503(home, caller):
    (home / "dashboard-governance.yaml").write_text("mode: [broken", encoding="utf-8")
    handled, handler = _get(caller, "/api/org/overview", "owner@acme.example")
    assert (handled, handler.status) == (True, 503)
    assert handler.body == {"error": "policy_unavailable"}


def test_invalid_org_block_answers_503(write_policy, caller):
    raw = _raw()
    raw["departments"]["sales"]["assignable_roles"].append("admin")
    write_policy(raw)
    assert _get(caller, "/api/org/overview", "owner@acme.example")[1].status == 503


def test_writes_answer_405(write_policy, caller):
    for path in ROUTES:
        handler = _Handler()
        assert org_api.handle_post(handler, SimpleNamespace(path=path, query=""), {"x": 1}) is True
        assert handler.status == 405


# ── What an organisation admin sees ──────────────────────────────────────────

def test_org_admin_sees_the_overview_and_every_department(write_policy, caller):
    body = _get(caller, "/api/org/overview", "owner@acme.example")[1].body
    assert body["organization"] == {"id": "org_acme", "name": "Acme"}
    assert body["installation"] == {"kind": "client"}
    assert body["viewer"] == {"email": "owner@acme.example", "delegated_scope": {"scope": "org"}}
    assert [d["key"] for d in body["departments"]] == ["finance", "sales"]
    assert body["admins"] == ["it.lead@acme.example", "owner@acme.example"]
    assert body["billing_admins"] == ["finance@acme.example", "owner@acme.example"]
    assert body["counts"]["departments"] == 2
    assert body["counts"]["people"] == 10  # nine policy users plus the bootstrap admin

    departments = _get(caller, "/api/org/departments", "owner@acme.example")[1].body["departments"]
    assert departments == [
        {"key": "finance", "name": "Finance", "group": "dept-finance", "admins": ["head.finance@acme.example"],
         "assignable_roles": ["viewer"], "assignable_groups": ["dept-finance"], "member_count": 3},
        {"key": "sales", "name": "Sales", "group": "dept-sales", "admins": ["head.sales@acme.example"],
         "assignable_roles": ["viewer", "operator"], "assignable_groups": ["dept-sales", "all-staff"],
         "member_count": 2},
    ]


def test_org_admin_sees_every_person_with_designations(write_policy, caller):
    people = {p["email"]: p for p in _get(caller, "/api/org/people", "it.lead@acme.example")[1].body["people"]}
    expected_people = set(FIXTURE["policy"]["users"]) | set(FIXTURE["policy"]["bootstrap_admins"])
    assert set(people) == expected_people
    assert people["owner@acme.example"]["org_roles"] == ["billing_admin", "org_admin"]
    assert people["head.sales@acme.example"]["departments"] == ["sales"]
    assert people["head.sales@acme.example"]["admin_of"] == ["sales"]
    assert people["it.admin@acme.example"]["platform_admin"] is True
    assert people["ops@synthwave.example"]["platform_admin"] is True
    assert people["rep.sales@acme.example"]["platform_admin"] is False
    assert people["finance@acme.example"]["groups"] == ["all-staff", "dept-finance"]


# ── A Sales department admin sees only Sales ─────────────────────────────────

def test_sales_admin_sees_only_sales(write_policy, caller):
    overview = _get(caller, "/api/org/overview", "head.sales@acme.example")[1].body
    assert overview["viewer"]["delegated_scope"] == {"scope": "department", "departments": ["sales"]}
    assert overview["departments"] == [{"key": "sales", "name": "Sales"}]
    assert overview["counts"] == {"people": 2, "departments": 1}
    assert "admins" not in overview and "billing_admins" not in overview

    departments = _get(caller, "/api/org/departments", "head.sales@acme.example")[1].body["departments"]
    assert [d["key"] for d in departments] == ["sales"]

    people = _get(caller, "/api/org/people", "head.sales@acme.example")[1].body["people"]
    assert [p["email"] for p in people] == ["head.sales@acme.example", "rep.sales@acme.example"]
    dumped = json.dumps(people)
    assert "finance" not in dumped and "groups" not in dumped and "org_roles" not in dumped


def test_a_sales_member_in_finance_too_shows_only_sales_to_the_sales_admin(write_policy, caller):
    raw = _raw()
    raw["users"]["rep.sales@acme.example"]["groups"].append("dept-finance")
    write_policy(raw)
    people = _get(caller, "/api/org/people", "head.sales@acme.example")[1].body["people"]
    rep = next(p for p in people if p["email"] == "rep.sales@acme.example")
    assert rep["departments"] == ["sales"]
    finance_view = _get(caller, "/api/org/people", "head.finance@acme.example")[1].body["people"]
    assert "rep.sales@acme.example" in {p["email"] for p in finance_view}
    assert "head.sales@acme.example" not in {p["email"] for p in finance_view}


# ── Approvals ────────────────────────────────────────────────────────────────

@pytest.fixture
def pending(write_policy):
    from api import approvals

    approvals.request(approvals.KIND_GRANT, "route:rep", "rep.sales@acme.example", label="Route access",
                      payload={"email": "rep.sales@acme.example", "gkind": "route", "value": "/api/files"})
    approvals.request(approvals.KIND_GRANT, "route:clerk", "clerk.finance@acme.example", label="Route access",
                      payload={"email": "clerk.finance@acme.example", "gkind": "route", "value": "/api/files"})
    approvals.request(approvals.KIND_MCP, "notion", "rep.sales@acme.example", label="Notion",
                      payload={"name": "notion"})
    decided = approvals.request(approvals.KIND_GRANT, "route:old", "rep.sales@acme.example",
                                payload={"email": "rep.sales@acme.example", "gkind": "route", "value": "/api/x"})
    approvals.decide(approvals.KIND_GRANT, decided["key"], "reject", "ops@synthwave.example")


def _pending_keys(caller, email):
    rows = _get(caller, "/api/org/approvals", email)[1].body["pending"]
    return sorted(f"{row['kind']}:{row['key']}" for row in rows)


def test_approvals_are_scoped(pending, caller):
    assert _pending_keys(caller, "ops@synthwave.example") == ["grant:route:clerk", "grant:route:rep", "mcp:notion"]
    assert _pending_keys(caller, "owner@acme.example") == ["grant:route:clerk", "grant:route:rep"]
    assert _pending_keys(caller, "head.sales@acme.example") == ["grant:route:rep"]
    assert _pending_keys(caller, "head.finance@acme.example") == ["grant:route:clerk"]
    assert _get(caller, "/api/org/approvals", "finance@acme.example")[1].status == 403
    assert _get(caller, "/api/org/approvals", "rep.sales@acme.example")[1].status == 403


def test_approval_rows_carry_no_reviewer_advice(pending, caller):
    rows = _get(caller, "/api/org/approvals", "owner@acme.example")[1].body["pending"]
    assert rows and all("advice" not in row and "explanation" not in row for row in rows)


# ── Usage ────────────────────────────────────────────────────────────────────

@pytest.fixture
def usage_state(write_policy, home):
    from api.governance import usage
    from api.governance.models import GovernanceSubject

    def key(email):
        return usage._subject_key(SimpleNamespace(subject=GovernanceSubject(email=email)))

    state = {
        "days": {usage._today(): {
            key("rep.sales@acme.example"): {"tool_calls": 4, "file_writes": 1, "mcp_calls": 0, "background_processes": 0},
            key("clerk.finance@acme.example"): {"tool_calls": 2, "file_writes": 0, "mcp_calls": 1,
                                                "background_processes": "bad"},
        }},
        "months": {usage._month(): {
            key("rep.sales@acme.example"): {"tool_calls": 40, "file_writes": 3, "mcp_calls": 2, "background_processes": 1},
        }},
    }
    (home / "dashboard-governance-usage.json").write_text(json.dumps(state), encoding="utf-8")


def test_usage_rows_per_person_in_scope(usage_state, caller):
    body = _get(caller, "/api/org/usage", "head.sales@acme.example")[1].body
    assert [row["email"] for row in body["people"]] == ["head.sales@acme.example", "rep.sales@acme.example"]
    rep = body["people"][1]
    assert rep["today"] == {"tool_calls": 4, "file_writes": 1, "mcp_calls": 0, "background_processes": 0}
    assert rep["month"] == {"tool_calls": 40, "file_writes": 3, "mcp_calls": 2, "background_processes": 1}
    assert body["totals"]["today"]["tool_calls"] == 4

    whole = _get(caller, "/api/org/usage", "owner@acme.example")[1].body
    clerk = next(row for row in whole["people"] if row["email"] == "clerk.finance@acme.example")
    assert clerk["today"] == {"tool_calls": 2, "file_writes": 0, "mcp_calls": 1, "background_processes": 0}
    assert whole["totals"]["today"]["tool_calls"] == 6


def test_billing_admin_gets_totals_only(usage_state, caller):
    body = _get(caller, "/api/org/usage", "finance@acme.example")[1].body
    assert body["people"] == []
    assert body["totals"]["today"] == {"tool_calls": 6, "file_writes": 1, "mcp_calls": 1, "background_processes": 0}
    assert body["totals"]["month"]["tool_calls"] == 40


# ── Wiring through the real dispatcher ───────────────────────────────────────

def test_routes_dispatch_reaches_the_handler(write_policy, caller, monkeypatch):
    import api.routes as routes

    monkeypatch.setattr(routes, "_guard_request_session_visibility",
                        lambda handler, parsed, body=None, method="GET": True)
    caller.email = "owner@acme.example"
    handler = _Handler()
    assert routes.handle_get(handler, urlparse("http://localhost/api/org/overview")) is not False
    assert handler.status == 200 and handler.body["organization"]["id"] == "org_acme"
    caller.email = "rep.sales@acme.example"
    handler = _Handler()
    routes.handle_get(handler, urlparse("http://localhost/api/org/people"))
    assert handler.status == 403


def test_enforcement_hook_lets_a_member_reach_the_self_route(write_policy):
    """Under enforce the hook admits the self routes (the handler decides),
    subject to the role's route allowlist like every other route: the
    fixture roles list no routes, so a role needs /api/org/* first."""
    from api.governance.enforce import evaluate_request

    identity = {"email": "rep.sales@acme.example", "groups": [], "claims_subset": {}, "method": "oidc"}
    assert evaluate_request(identity, "GET", "/api/org/overview").reason == "route_not_allowed"
    raw = _raw()
    raw["roles"]["operator"]["grants"]["routes"] = ["/api/org/*"]
    write_policy(raw)
    for path in ROUTES:
        decision = evaluate_request(identity, "GET", path)
        assert decision.allow, (path, decision)
