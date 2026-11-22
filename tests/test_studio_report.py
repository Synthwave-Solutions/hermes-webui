"""Assignments from, and the Studio summary to, the central Cloud (api/studio_report.py).

A fake control plane (a real HTTP server on localhost that checks the signed
request arrives without any acting or organisation header) answers the two
calls. Covered: the pull replaces only the cloud partners and survives a bad
answer, the push carries no personal data of the customer, an unreachable
control plane leaves one pending file that is delivered later, nothing
happens without a configured control plane, the local progress route, and the
partner's sign-in role in the governance resolver.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api.org_structure as org  # noqa: E402
import api.studio as studio  # noqa: E402
import api.studio_library as lib  # noqa: E402
import api.studio_hours as hours  # noqa: E402
import api.studio_report as report  # noqa: E402
from api import control_plane_client as cpc  # noqa: E402
from api.governance import resolver  # noqa: E402
from api.governance.models import GovernancePolicy, GovernanceRole, GovernanceSubject, GovernanceUser, GrantSet  # noqa: E402

ADMIN = "boss@example.com"
OWNER = "tom.de.vries@example.com"
DEPT_ADMIN = "dana@example.com"
OTHER = "eve@example.com"
CONSULTANT = "carla@partner.example"
DEVELOPER = "dev@partner.example"
KEY_ID = "0a1b2c3d4e5f6071"
SECRET_HEX = "5f" * 16 + "a0" * 16


class FakeControlPlane:
    """Answers the two customer routes and records every request."""

    def __init__(self):
        self.assignments = {"assignments": []}
        self.hours = None
        self.status = 200
        self.requests = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _handle(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                fake.requests.append({"method": self.command, "path": self.path,
                                      "headers": {k.lower(): v for k, v in self.headers.items()},
                                      "body": json.loads(raw) if raw else None})
                if fake.status != 200:
                    payload = {"error": {"code": "down", "message": "down"}}
                elif self.command == "GET" and self.path == report.ASSIGNMENTS_PATH:
                    payload = fake.assignments
                elif self.command == "POST" and self.path == report.SUMMARY_PATH:
                    payload = {"ok": True}
                elif self.command == "GET" and fake.hours is not None and re.fullmatch(r"/v1/customer/hours\?period=\d{4}-\d{2}", self.path):
                    payload = dict(fake.hours, period=self.path.rsplit("=", 1)[1])
                else:
                    payload = {"error": {"code": "not_found", "message": "unknown"}}
                data = json.dumps(payload).encode()
                self.send_response(fake.status if fake.status != 200 else (200 if "error" not in payload else 404))
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = _handle

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self):
        return "http://127.0.0.1:%d" % self.server.server_address[1]

    def sent(self, method, path):
        return [r for r in self.requests if r["method"] == method and r["path"] == path]

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def env(monkeypatch, tmp_path):
    import api.config as config

    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setattr(config, "STATE_DIR", state)
    for name in ("SP_CONTROL_SOCKET", "SP_CONTROL_URL", "SP_CONTROL_KEY_FILE", "SP_STUDIO_REPORT", "SP_CLOUD_PERSONAL_MSP",
                 "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    cpc.clear_cache()
    report._reset_for_tests()
    hours.clear_cache()
    policy = GovernancePolicy(bootstrap_admins=(ADMIN,), installation_kind="hq")
    monkeypatch.setattr(org, "_policy", lambda: policy)
    monkeypatch.setattr(report, "_measured_hours", lambda: {})
    admin = org.scope_for(ADMIN, policy=policy)
    org.apply(admin, {"op": "department.save", "key": "finance", "name": "Finance", "admins": [DEPT_ADMIN], "hourly_rate": 83.25})
    org.apply(admin, {"op": "team.save", "department": "finance", "name": "Debiteuren", "members": [OWNER]})
    org.apply(admin, {"op": "department.save", "key": "sales", "name": "Sales"})
    org.apply(admin, {"op": "team.save", "department": "sales", "name": "Inside", "members": [OTHER]})
    plane = FakeControlPlane()

    def configure():
        key = tmp_path / "control.key"
        key.write_text(json.dumps({"kind": "control", "key_id": KEY_ID, "secret": SECRET_HEX}), encoding="utf-8")
        key.chmod(0o600)
        monkeypatch.setenv("SP_CONTROL_URL", plane.url)
        monkeypatch.setenv("SP_CONTROL_KEY_FILE", str(key))
        cpc.clear_cache()

    yield SimpleNamespace(policy=policy, plane=plane, configure=configure, state=state, admin=admin)
    plane.close()
    report._reset_for_tests()
    cpc.clear_cache()


def V(email, env):
    return org.scope_for(email, policy=env.policy)


def _use_case(env):
    """A use case with everything a summary must leave behind."""
    owner = V(OWNER, env)
    doc = studio.update(owner, {"team": "finance/debiteuren", "title": "Aanmaningen versturen"})
    process = {"description": "GEHEIM procesverhaal van Tom", "data_sensitivity": "personal",
               "data_note": "GEHEIM bsn en rekeningnummers", "frequency": {"count": 10, "per": "week"},
               "as_is": [{"step": "Lijst maken", "actor": "Tom de Vries", "minutes": 60, "pain": "GEHEIM knelpunt"}],
               "to_be": [{"step": "Agent maakt lijst", "actor": "agent", "minutes": 12, "building_block": "task", "note": "GEHEIM notitie"}]}
    studio.update(owner, {"id": doc["id"], "phase": "design", "process": process,
                          "notes": [{"role": "user", "text": "GEHEIM gesprek over collega Eve"}],
                          "goals": [{"name": "GEHEIM doel", "kpi": "x"}]})
    lib.save_item(owner, {"title": "Aanmaningen", "team": "finance/debiteuren", "use_case": doc["id"], "status": "design",
                          "pain": "GEHEIM pijn", "assignee": OWNER})
    return doc["id"]


# ── Pull ─────────────────────────────────────────────────────────────────────

def test_everything_is_a_no_op_without_a_control_plane(env):
    _use_case(env)
    assert report.enabled() is False
    assert report.pull_assignments() == {"ok": False, "reason": "not_configured"}
    assert report.push_summary() == "off"
    assert report.run_due(time.time(), {}) == []
    assert report.start_thread() is False
    assert env.plane.requests == [] and not (env.state / "studio-report").exists()
    assert org.load()["partners"] == []


def test_pull_replaces_only_cloud_partners(env):
    env.configure()
    org.apply(env.admin, {"op": "partner.save", "email": "local.qa@partner.example", "name": "Lokaal", "role": "qa"})
    env.plane.assignments = {"assignments": [
        {"email": "Carla@Partner.Example", "name": "Carla Jansen", "role": "consultant", "starts_at": "2026-11-01", "ends_at": "2099-01-01"},
        {"email": DEVELOPER, "name": "Dev", "role": "developer", "starts_at": "", "ends_at": None},
        {"email": "broken", "role": "consultant"}, {"email": "x@partner.example", "role": "owner"}]}
    assert report.pull_assignments() == {"ok": True, "changed": True, "count": 2, "skipped": 2}
    request = env.plane.sent("GET", report.ASSIGNMENTS_PATH)[0]
    assert request["headers"]["authorization"].startswith("SP-HMAC-SHA256 ")
    assert not any(h.startswith("x-sp-acting") or "organi" in h for h in request["headers"])
    partners = {p["email"]: p for p in org.load()["partners"]}
    assert set(partners) == {CONSULTANT, DEVELOPER, "local.qa@partner.example"}
    assert partners[CONSULTANT]["source"] == "cloud" and partners[CONSULTANT]["org"] == "synthwave"
    assert partners["local.qa@partner.example"]["source"] == "local"
    assert V(CONSULTANT, env).partner_role == "consultant"
    # The same answer again changes nothing and writes no audit line.
    audit = env.state / "org_structure" / "audit.jsonl"
    lines = len(audit.read_text().splitlines())
    assert report.pull_assignments()["changed"] is False and len(audit.read_text().splitlines()) == lines
    assert json.loads(audit.read_text().splitlines()[-1])["action"] == "partners.sync"
    # The Cloud withdraws the consultant: gone here on the next pull, the local one stays.
    env.plane.assignments = {"assignments": [{"email": DEVELOPER, "name": "Dev", "role": "developer"}]}
    assert report.pull_assignments()["changed"] is True
    assert {p["email"] for p in org.load()["partners"]} == {DEVELOPER, "local.qa@partner.example"}
    assert V(CONSULTANT, env).partner_role is None
    # A local edit cannot touch a central assignment.
    with pytest.raises(ValueError):
        org.apply(env.admin, {"op": "partner.save", "email": DEVELOPER, "role": "consultant"})
    with pytest.raises(ValueError):
        org.apply(env.admin, {"op": "partner.remove", "email": DEVELOPER})


@pytest.mark.parametrize("answer", [{"assignments": "none"}, {"rows": []}, ["x"], {"assignments": [{}] * 101}])
def test_a_confused_or_unreachable_control_plane_removes_nobody(env, answer):
    env.configure()
    env.plane.assignments = {"assignments": [{"email": CONSULTANT, "name": "Carla", "role": "consultant"}]}
    assert report.pull_assignments()["ok"] is True
    env.plane.assignments = answer
    assert report.pull_assignments()["ok"] is False
    env.plane.status = 503
    assert report.pull_assignments() == {"ok": False, "reason": "unavailable", "status": 503}
    assert [p["email"] for p in org.load()["partners"]] == [CONSULTANT]


# ── Push ─────────────────────────────────────────────────────────────────────

def test_summary_shape_and_no_customer_personal_data(env, monkeypatch):
    env.configure()
    uc = _use_case(env)
    env.plane.assignments = {"assignments": [{"email": CONSULTANT, "name": "Carla Jansen", "role": "consultant"}]}
    report.pull_assignments()
    studio.update(V(CONSULTANT, env), {"id": uc, "consultant": CONSULTANT})
    monkeypatch.setattr(report, "_measured_hours", lambda: {uc: 6.5})
    assert report.push_summary() == "sent"
    request = env.plane.sent("POST", report.SUMMARY_PATH)[0]
    assert not any(h.startswith("x-sp-acting") or "organi" in h for h in request["headers"])
    body = request["body"]
    assert set(body) == {"generated_at", "use_cases", "partners"}
    assert body["partners"] == [{"email": CONSULTANT, "role": "consultant"}]
    assert body["generated_at"].endswith("Z")
    row = body["use_cases"][0]
    assert set(row) == {"id", "title", "phase", "backlog_status", "team", "consultant", "updated_at", "hours_week_before",
                        "hours_week_after", "hours_week_saved", "measured_hours_saved_30d"}
    assert row == dict(row, id=uc, title="Aanmaningen versturen", phase="design", backlog_status="design",
                       team="finance/debiteuren", consultant=CONSULTANT, hours_week_before=10.0, hours_week_after=2.0,
                       hours_week_saved=8.0, measured_hours_saved_30d=6.5)
    text = json.dumps(body, ensure_ascii=False).lower()
    # No address or name of anybody at the customer, no notes, descriptions, data notes, goals or pains.
    for leak in ("example.com", "tom", "vries", "eve", "boss", "dana", "geheim", "owner", "notes", "description", "data_note",
                 "organization", "organisation", "org_id"):
        assert leak not in text, leak
    # A consultant whose assignment ended is no longer named.
    env.plane.assignments = {"assignments": []}
    report.pull_assignments()
    summary = report.build_summary()
    assert summary["partners"] == [] and summary["use_cases"][0]["consultant"] == ""


def test_push_spools_when_the_control_plane_is_down_and_delivers_later(env, monkeypatch):
    env.configure()
    _use_case(env)
    pending = env.state / "studio-report" / "spool" / "pending.json"
    env.plane.status = 503
    assert report.push_summary() == "spooled"
    assert pending.is_file() and oct(pending.stat().st_mode & 0o777) == "0o600"
    kept = json.loads(pending.read_text())
    assert kept["reason"] == "status_503" and kept["body"]["use_cases"][0]["title"] == "Aanmaningen versturen"
    assert "example.com" not in pending.read_text()
    # Bounded: a second failure replaces the file, it does not add one.
    assert report.push_summary() == "spooled"
    assert [p.name for p in pending.parent.iterdir()] == ["pending.json"]
    assert report.stats()["pending"] is True and report.stats()["failures"] == 2
    # Unreachable (nothing listening) spools as well.
    env.plane.close()
    assert report.push_summary() == "spooled"

    # Back up: the timer sees the pending file and delivers the state of that moment.
    plane = FakeControlPlane()
    try:
        monkeypatch.setenv("SP_CONTROL_URL", plane.url)
        state = {"next_pull": time.time() + 999, "next_push": time.time() + 999}
        assert report.run_due(time.time(), state) == ["push:sent"]
        assert not pending.exists() and report.stats()["failures"] == 0
        assert len(plane.sent("POST", report.SUMMARY_PATH)) == 1
        assert report.run_due(time.time(), state) == []          # nothing owed any more
    finally:
        env.plane = plane


def test_a_studio_save_is_pushed_after_the_debounce_and_a_refusal_is_not_retried(env, monkeypatch):
    env.configure()
    monkeypatch.setattr(report, "DEBOUNCE_S", 20.0)
    state = {"next_pull": time.time() + 999, "next_push": time.time() + 999}
    _use_case(env)                                               # saves through studio and the backlog
    assert report.stats()["dirty"] is True
    now = time.time()
    assert report.run_due(now, state) == []                      # still inside the debounce
    assert report.run_due(now + 21, state) == ["push:sent"]
    assert report.stats()["dirty"] is False
    # The timer also pulls and pushes when their moment comes.
    assert report.run_due(now + 30, {}) == ["pull", "push:sent"]
    # A 4xx is a refusal: nothing is kept for a retry.
    env.plane.status = 422
    assert report.push_summary() == "rejected"
    assert not (env.state / "studio-report" / "spool" / "pending.json").exists()


# ── The local progress route ─────────────────────────────────────────────────

def test_local_summary_for_admins_department_admins_and_partners(env):
    uc = _use_case(env)
    other = studio.update(V(OTHER, env), {"team": "sales/inside", "title": "Leads opvolgen"})
    private = studio.update(V(OTHER, env), {"title": "Zonder team"})
    org.apply(env.admin, {"op": "partner.save", "email": CONSULTANT, "name": "Carla Jansen", "role": "consultant"})
    org.apply(env.admin, {"op": "partner.save", "email": "quinn@partner.example", "name": "Quinn", "role": "qa"})
    studio.update(V(OWNER, env), {"id": uc, "consultant": CONSULTANT})

    full = report.summary_for(V(ADMIN, env))
    assert {r["id"] for r in full["use_cases"]} == {uc, other["id"], private["id"]}
    row = next(r for r in full["use_cases"] if r["id"] == uc)
    assert row["owner_name"] == "Tom De Vries" and row["team_name"] == "Debiteuren" and row["consultant_name"] == "Carla Jansen"
    assert row["hours_week_saved"] == 8.0 and full["totals"] == {"use_cases": 3, "hours_week_saved": 8.0, "measured_hours_saved_30d": 0.0}
    assert [p["role"] for p in full["partners"]] == ["consultant", "qa"]
    # No money anywhere, for anybody.
    assert "83.25" not in json.dumps(full) and "hourly_rate" not in json.dumps(full) and "net_eur" not in json.dumps(full)

    assert [r["id"] for r in report.summary_for(V(DEPT_ADMIN, env))["use_cases"]] == [uc]       # only their department
    for partner in (CONSULTANT, "quinn@partner.example"):                                       # qa reads it too
        assert {r["id"] for r in report.summary_for(V(partner, env))["use_cases"]} == {uc, other["id"]}
    for nobody in (OWNER, OTHER, "stranger@example.com"):
        with pytest.raises(PermissionError):
            report.summary_for(V(nobody, env))

    sent = []
    import api.studio_report as module
    module_j, module.j = module.j, lambda handler, payload, status=200, **_kw: sent.append((status, payload))
    scope, org.request_scope = org.request_scope, lambda handler: V(OWNER, env)
    try:
        assert studio.handle_get(None, SimpleNamespace(path="/api/studio/summary", query="")) is True
        assert sent[-1][0] == 403
        org.request_scope = lambda handler: V(CONSULTANT, env)
        studio.handle_get(None, SimpleNamespace(path="/api/studio/summary", query=""))
        assert sent[-1][0] == 200 and sent[-1][1]["viewer"]["partner"] == {"role": "consultant", "org": "synthwave"}
    finally:
        module.j, org.request_scope = module_j, scope


# ── Sign-in: the partner role in the governance resolver ─────────────────────

def _policy_with_partner_role(**extra):
    role = GovernanceRole(name=resolver.PARTNER_ROLE, grants=GrantSet(
        permissions=frozenset({"chat:use", "sessions:read", "sessions:write", "profiles:read", "governance:write",
                               "profiles:admin", "terminal:use", "org:admin"}),
        routes=frozenset({"/api/studio/*", "/api/org/structure*", "/api/chat*", "/api/session*", "/api/auth/*",
                          "/api/governance/*", "/api/management/*", "/api/msp/*"}),
        profiles=frozenset({"default"})))
    return GovernancePolicy(mode="enforce", bootstrap_admins=(ADMIN,), roles={resolver.PARTNER_ROLE: role}, **extra)


def _access(policy, email):
    return resolver.resolve_effective_access(policy, GovernanceSubject(email=email, provider="synthpulse_cloud"))


def test_partner_role_only_for_a_current_central_assignment(env, monkeypatch):
    policy = _policy_with_partner_role()
    env.configure()
    env.plane.assignments = {"assignments": [{"email": CONSULTANT, "name": "Carla", "role": "consultant"}]}
    report.pull_assignments()
    org.apply(env.admin, {"op": "partner.save", "email": "local@partner.example", "role": "developer"})

    # Switch off (the default): an assigned partner is still nobody.
    assert _access(policy, CONSULTANT).routes == frozenset() and not _access(policy, CONSULTANT).is_route_allowed("/api/studio/usecases")

    monkeypatch.setenv("SP_CLOUD_PERSONAL_MSP", "1")
    access = _access(policy, CONSULTANT)
    assert resolver.PARTNER_ROLE in access.roles and f"partner:{resolver.PARTNER_ROLE}" in access.grant_sources
    for route in ("/api/studio/usecases", "/api/studio/step", "/api/org/structure", "/api/org/structure/me", "/api/chat/start"):
        assert access.is_route_allowed(route), route
    assert access.has_permission("chat:use") and access.is_profile_allowed("default")
    # Whatever the role lists: no admin permission and no admin or money route.
    for permission in ("governance:write", "governance:read", "profiles:admin", "terminal:use", "org:admin", "billing:read"):
        assert not access.has_permission(permission), permission
    for route in ("/api/governance/policy", "/api/governance/users", "/api/governance/approvals", "/api/management/overview",
                  "/api/management/pricing", "/api/msp/overview", "/api/msp/invoice", "/api/value/job", "/api/org/people"):
        assert not access.is_route_allowed(route), route
    assert access.is_route_allowed("/api/governance/me")

    # Not for a partner an organisation admin added locally, a stranger, or without the role in the policy.
    assert _access(policy, "local@partner.example").routes == frozenset()
    assert _access(policy, "stranger@partner.example").routes == frozenset()
    bare = GovernancePolicy(mode="enforce", bootstrap_admins=(ADMIN,))
    assert _access(bare, CONSULTANT).routes == frozenset() and resolver.PARTNER_ROLE not in _access(bare, CONSULTANT).roles
    # A person with their own entry in the policy keeps exactly that entry.
    own = _policy_with_partner_role(users={CONSULTANT: GovernanceUser(email=CONSULTANT)})
    assert resolver.PARTNER_ROLE not in _access(own, CONSULTANT).roles and _access(own, CONSULTANT).routes == frozenset()

    # The assignment ends centrally: the next request resolves to nothing.
    env.plane.assignments = {"assignments": [{"email": CONSULTANT, "name": "Carla", "role": "consultant", "ends_at": "2020-01-01"}]}
    report.pull_assignments()
    gone = _access(policy, CONSULTANT)
    assert gone.routes == frozenset() and resolver.PARTNER_ROLE not in gone.roles and not gone.has_permission("chat:use")


def test_request_enforcement_and_the_login_label_for_a_partner(env, monkeypatch):
    from api import cloud_login, msp_service
    from api.governance import enforce, loader

    policy = _policy_with_partner_role()
    monkeypatch.setattr(loader, "get_policy", lambda: policy)
    monkeypatch.setenv("SP_CLOUD_PERSONAL_MSP", "1")
    env.configure()
    env.plane.assignments = {"assignments": [{"email": CONSULTANT, "name": "Carla", "role": "consultant"}]}
    identity = {"email": CONSULTANT, "method": "synthpulse_cloud", "groups": [], "claims_subset": {}}

    # Before the installation has pulled: denied, and the login itself fetches the assignment.
    assert enforce.evaluate_request(identity, "GET", "/api/studio/usecases").allow is False
    assert cloud_login._partner(CONSULTANT) == {"role": "consultant", "org": "synthwave"}
    assert len(env.plane.sent("GET", report.ASSIGNMENTS_PATH)) == 1
    assert cloud_login._partner("stranger@partner.example") is None
    assert cloud_login._partner(ADMIN) is None

    assert enforce.evaluate_request(identity, "GET", "/api/studio/usecases").allow is True
    assert enforce.evaluate_request(identity, "POST", "/api/studio/usecase").allow is True
    assert enforce.evaluate_request(identity, "GET", "/api/org/structure").allow is True
    for method, path in (("GET", "/api/governance/policy"), ("POST", "/api/governance/users"),
                         ("GET", "/api/management/overview"), ("GET", "/api/msp/overview")):
        assert enforce.evaluate_request(identity, method, path).allow is False, path

    # What a partner is denied never becomes an access request in the customer's queue: approving one
    # would give the address its own policy entry, and then it no longer resolves through the partner role.
    from api import grant_requests

    assert grant_requests.record_route_denial(CONSULTANT, "/api/management/overview") is False
    assert grant_requests.record_route_denial(CONSULTANT, "/api/crons") is False
    assert not grant_requests._spool_path().exists()
    assert grant_requests.record_route_denial(OWNER, "/api/crons") is True          # a person of the customer still can ask
    assert list(grant_requests._load_spool()) == [f"{OWNER}|route|/api/crons"]
    spool = grant_requests._load_spool()
    spool[f"{CONSULTANT}|skill|pdf"] = {"email": CONSULTANT, "gkind": "skill", "value": "pdf", "reason": "skill_not_allowed", "count": 1}
    grant_requests._spool_path().write_text(json.dumps(spool), encoding="utf-8")       # as the engine would spool it
    assert grant_requests.ingest_spool() == 1

    # The customer's own account (invoices, orders) is closed to a partner, also behind the route layer.
    subject = GovernanceSubject(email=CONSULTANT, provider="synthpulse_cloud")
    monkeypatch.setattr(msp_service, "context", lambda handler: (policy, subject, None))
    with pytest.raises(PermissionError):
        msp_service.identity(None)
    assert msp_service.visible(None) is False


# ── Hours of the month ───────────────────────────────────────────────────────

HOURS = {"usage_as_of": 1795000000, "departments": [{
    "department_id": "dep_1", "name": "Finance", "tier": "t2", "tier_name": "Pakket twee", "term_ends_at": "2027-03-31",
    "planned_tier_change": False, "price_cents": 500000, "internal": "x",
    "roles": [{"role": "consultant", "label": "Consultant", "allocated_minutes": 960, "used_minutes": 420, "remaining_minutes": 540,
               "people": [{"name": "Carla Jansen", "used_minutes": 420, "email": "carla@partner.example"}], "rate": 150},
              {"role": "developer", "label": "Developer", "allocated_minutes": 1920, "used_minutes": None, "remaining_minutes": None, "people": []},
              {"role": "owner", "label": "x", "allocated_minutes": 1}],
    "team": [{"role": "consultant", "label": "Consultant", "name": "Carla Jansen", "hours_per_week": 4}]}],
    "maintenance": [], "support": None, "productive": {"status": "ok", "token": "secret"}}


def test_hours_are_proxied_cached_and_bounded(env):
    # Not configured: a friendly empty state, nothing is sent.
    assert hours.hours("2026-11") == {"configured": False, "available": False, "period": "2026-11", "departments": []}
    assert env.plane.requests == []
    env.configure()
    env.plane.hours = HOURS
    got = hours.hours("2026-11")
    request = env.plane.requests[-1]
    assert request["method"] == "GET" and request["path"] == "/v1/customer/hours?period=2026-11"
    assert request["headers"]["authorization"].startswith("SP-HMAC-SHA256 ")
    assert not any(h.startswith("x-sp-acting") or "organi" in h for h in request["headers"])
    assert got["configured"] and got["available"] and got["period"] == "2026-11" and got["usage_as_of"] == 1795000000
    dept = got["departments"][0]
    assert set(dept) == {"department_id", "name", "tier", "tier_name", "term_ends_at", "planned_tier_change", "roles", "team"}
    assert [r["role"] for r in dept["roles"]] == ["consultant", "developer"]                    # an unknown role is dropped
    assert dept["roles"][0] == {"role": "consultant", "label": "Consultant", "allocated_minutes": 960, "used_minutes": 420,
                                "remaining_minutes": 540, "people": [{"name": "Carla Jansen", "used_minutes": 420}]}
    assert dept["roles"][1]["used_minutes"] is None and dept["roles"][1]["remaining_minutes"] is None    # not known yet stays null
    assert dept["team"] == [{"role": "consultant", "label": "Consultant", "name": "Carla Jansen", "hours_per_week": 4}]
    text = json.dumps(got)
    for leak in ("price_cents", "rate", "secret", "internal", "partner.example", "maintenance", "support"):
        assert leak not in text, leak
    # Five minutes from the cache, then asked again; another month is its own entry.
    sent = len(env.plane.requests)
    assert hours.hours("2026-11") == got and len(env.plane.requests) == sent
    assert hours.hours("2026-11", now=time.time() + 301)["available"] and len(env.plane.requests) == sent + 1
    assert hours.hours("2026-10")["period"] == "2026-10" and len(env.plane.requests) == sent + 2
    assert hours.hours()["period"] == time.strftime("%Y-%m")
    for bad in ("2026-13", "2026-1", "november", "2026-11&x=1", "../x"):
        with pytest.raises(ValueError):
            hours.hours(bad)
    # Down: an empty state that is not kept, so the next look asks again.
    hours.clear_cache()
    env.plane.status = 503
    down = hours.hours("2026-11")
    assert down == {"configured": True, "available": False, "period": "2026-11", "departments": [], "status": 503}
    env.plane.status = 200
    assert hours.hours("2026-11")["available"] is True


def test_hours_route_for_admins_department_admins_and_partners(env):
    env.configure()
    env.plane.hours = HOURS
    org.apply(env.admin, {"op": "partner.save", "email": CONSULTANT, "name": "Carla", "role": "consultant"})
    org.apply(env.admin, {"op": "partner.save", "email": "quinn@partner.example", "name": "Quinn", "role": "qa"})
    sent = []
    old_j, old_scope = hours.j, org.request_scope
    hours.j = lambda handler, payload, status=200, **_kw: sent.append((status, payload))
    try:
        for email, query, status in ((ADMIN, "period=2026-11", 200), (DEPT_ADMIN, "", 200), (CONSULTANT, "", 200),
                                     ("quinn@partner.example", "", 200), (OWNER, "", 403), ("stranger@example.com", "", 403),
                                     (ADMIN, "period=nonsense", 400)):
            org.request_scope = lambda handler, email=email: V(email, env)
            assert studio.handle_get(None, SimpleNamespace(path="/api/studio/hours", query=query)) is True
            assert sent[-1][0] == status, (email, query)
        assert sent[0][1]["departments"][0]["tier_name"] == "Pakket twee"
    finally:
        hours.j, org.request_scope = old_j, old_scope
