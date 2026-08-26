"""Scheduled job visibility must respect the caller's governance scope.

Reported by Michael on 26 Aug 2026 in Hermes WebUI: a governed user could see
scheduled cron jobs outside their authorised scope (names, schedules, prompts,
status). The fix lives in api/cron_scope.py and is hooked into the
``/api/crons*`` GET branches in api/routes.py:

* the listing filters rows by the identity's profile grants (``cron:admin``,
  the bootstrap admin and governance-off installs keep seeing everything);
* the per-job detail routes 403 when the active profile is out of scope, so
  unauthorised jobs cannot be retrieved by direct URL either.

House pattern: pure decision tests with an injected policy loader (see
tests/test_governance_enforce.py) plus source-inspection of the route hooks
(see tests/test_issue4768_cron_module_missing.py).
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.cron_scope import (  # noqa: E402
    identity_sees_cron_profile,
    scope_cron_rows,
)
from api.governance import loader  # noqa: E402
from api.governance.audit import read_audit_events  # noqa: E402
from api.governance.loader import parse_governance_policy  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ROUTES = (REPO / "api" / "routes.py").read_text(encoding="utf-8")

BOOTSTRAP = "michael@example.test"

POLICY = {
    "version": 1,
    "mode": "enforce",
    "default_effect": "deny",
    "bootstrap_admins": [BOOTSTRAP],
    "roles": {
        "cron_admin": {
            "grants": {
                "permissions": ["cron:read", "cron:write", "cron:run", "cron:admin"],
                "profiles": ["*"],
                "routes": ["*"],
            },
        },
        "alpha_operator": {
            "grants": {
                "permissions": ["cron:read", "cron:write", "cron:run"],
                "profiles": ["alpha"],
                "routes": ["/api/crons", "/api/crons/*"],
            },
        },
        "beta_operator": {
            "grants": {
                "permissions": ["cron:read"],
                "profiles": ["beta"],
                "routes": ["/api/crons", "/api/crons/*"],
            },
        },
    },
    "users": {
        "cronadmin@example.test": {"roles": ["cron_admin"]},
        "alpha@example.test": {"roles": ["alpha_operator"]},
        "beta@example.test": {"roles": ["beta_operator"]},
    },
}


def _identity(email):
    return {"email": email, "groups": [], "claims_subset": {}, "method": "oidc"}


def _job(job_id, owner_profile):
    return {
        "id": job_id,
        "name": f"job {job_id}",
        "schedule": "0 9 * * *",
        "prompt": f"secret prompt for {owner_profile}",
        "owner_profile": owner_profile,
        "read_only": False,
    }


ACTIVE_ROWS = [_job("a1", "default"), _job("a2", "default")]
OTHER_ROWS = [_job("b1", "alpha"), _job("b2", "beta"), _job("b3", "alpha")]


@pytest.fixture(autouse=True)
def _isolated_audit_home(tmp_path, monkeypatch):
    """report_only decisions audit; keep the JSONL sink out of the real ~/.hermes."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))


@pytest.fixture
def inject_policy():
    def _set(data):
        policy = parse_governance_policy(data)
        loader.set_policy_loader(lambda: policy)
        return policy
    yield _set
    loader.set_policy_loader(None)


# ── Pure decision core ──────────────────────────────────────────────────────

def test_governed_user_cannot_see_other_profiles(inject_policy):
    inject_policy(POLICY)
    identity = _identity("alpha@example.test")
    assert identity_sees_cron_profile(identity, "alpha") is True
    assert identity_sees_cron_profile(identity, "beta") is False
    assert identity_sees_cron_profile(identity, "default") is False


def test_isolation_across_two_governed_users(inject_policy):
    """Regression: two governed users see disjoint, own-profile-only rows."""
    inject_policy(POLICY)

    alpha_active, alpha_other = scope_cron_rows(
        _identity("alpha@example.test"), ACTIVE_ROWS, OTHER_ROWS)
    beta_active, beta_other = scope_cron_rows(
        _identity("beta@example.test"), ACTIVE_ROWS, OTHER_ROWS)

    # Neither sees the default-profile rows the store happened to serve.
    assert alpha_active == [] and beta_active == []
    assert [row["id"] for row in alpha_other] == ["b1", "b3"]
    assert [row["id"] for row in beta_other] == ["b2"]

    # No foreign metadata survives in either payload.
    alpha_ids = {row["id"] for row in alpha_active + alpha_other}
    beta_ids = {row["id"] for row in beta_active + beta_other}
    assert not alpha_ids & beta_ids
    for row in alpha_other:
        assert "beta" not in row["prompt"]
    for row in beta_other:
        assert "alpha" not in row["prompt"]


def test_governed_user_keeps_rows_of_allowed_active_profile(inject_policy):
    inject_policy(POLICY)
    active = [_job("a1", "alpha")]
    kept_active, kept_other = scope_cron_rows(
        _identity("alpha@example.test"), active, OTHER_ROWS)
    assert [row["id"] for row in kept_active] == ["a1"]
    assert [row["id"] for row in kept_other] == ["b1", "b3"]


def test_cron_admin_and_bootstrap_see_everything(inject_policy):
    inject_policy(POLICY)
    for email in ("cronadmin@example.test", BOOTSTRAP):
        active, other = scope_cron_rows(_identity(email), ACTIVE_ROWS, OTHER_ROWS)
        assert active == ACTIVE_ROWS
        assert other == OTHER_ROWS


def test_governance_off_keeps_previous_behaviour(inject_policy):
    inject_policy({"version": 1, "mode": "off", "default_effect": "deny"})
    active, other = scope_cron_rows(None, ACTIVE_ROWS, OTHER_ROWS)
    assert active == ACTIVE_ROWS
    assert other == OTHER_ROWS


def test_anonymous_identity_sees_nothing_under_enforce(inject_policy):
    inject_policy(POLICY)
    active, other = scope_cron_rows(None, ACTIVE_ROWS, OTHER_ROWS)
    assert active == [] and other == []


def test_report_only_mode_keeps_rows_visible_and_audits_would_deny(inject_policy):
    """D5: report_only governance must never enforce; it audits instead."""
    inject_policy({**POLICY, "mode": "report_only"})
    identity = _identity("alpha@example.test")

    # Zero behaviour change for the caller: every row stays visible.
    active, other = scope_cron_rows(identity, ACTIVE_ROWS, OTHER_ROWS)
    assert active == ACTIVE_ROWS
    assert other == OTHER_ROWS

    # Every profile that WOULD be hidden under enforce is audited once.
    events = read_audit_events(20)
    assert {event["event"] for event in events} == {"would_deny"}
    assert {event["extra"]["profile"] for event in events} == {"default", "beta"}
    for event in events:
        assert event["path"] == "/api/crons"
        assert event["method"] == "GET"
        assert event["reason"] == "profile_not_allowed"
        assert event["mode"] == "report_only"
        assert event["report_only"] is True
        assert event["extra"]["resource"] == "cron:admin"
    # Identity is stored hashed, never raw (house audit invariant).
    assert "alpha@example.test" not in json.dumps(events)


def test_report_only_identity_check_allows_and_audits(inject_policy):
    inject_policy({**POLICY, "mode": "report_only"})
    assert identity_sees_cron_profile(_identity("beta@example.test"), "alpha") is True
    events = read_audit_events(5)
    assert len(events) == 1
    assert events[0]["event"] == "would_deny"
    assert events[0]["extra"]["profile"] == "alpha"


def test_report_only_in_scope_rows_stay_unaudited(inject_policy):
    inject_policy({**POLICY, "mode": "report_only"})
    assert identity_sees_cron_profile(_identity("alpha@example.test"), "alpha") is True
    assert read_audit_events(5) == []


def test_enforce_mode_still_hides_without_would_deny_audit(inject_policy):
    inject_policy(POLICY)
    active, other = scope_cron_rows(_identity("alpha@example.test"), ACTIVE_ROWS, OTHER_ROWS)
    assert active == []
    assert [row["id"] for row in other] == ["b1", "b3"]
    assert read_audit_events(5) == []


def test_rows_without_owner_profile_default_to_root_profile(inject_policy):
    inject_policy(POLICY)
    rows = [{"id": "x1", "name": "legacy"}]
    active, _ = scope_cron_rows(_identity("alpha@example.test"), rows, [])
    assert active == []  # "default" is not in alpha's scope
    active, _ = scope_cron_rows(_identity("cronadmin@example.test"), rows, [])
    assert active == rows


# ── Route-level integration (harness mirrors #3947's cron route tests) ─────

def _install_cron_jobs(monkeypatch, jobs_by_home, current_home):
    import types

    cron_pkg = types.ModuleType("cron")
    cron_pkg.__path__ = []
    cron_jobs = types.ModuleType("cron.jobs")

    def _list_jobs(include_disabled=True):
        return [dict(job) for job in jobs_by_home[current_home["value"]]]

    cron_jobs.list_jobs = _list_jobs
    monkeypatch.setitem(sys.modules, "cron", cron_pkg)
    monkeypatch.setitem(sys.modules, "cron.jobs", cron_jobs)


class _JSONHandler:
    def __init__(self):
        import io

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

    @property
    def body(self):
        import json

        return json.loads(self.wfile.getvalue().decode("utf-8"))


@pytest.fixture
def crons_route_env(monkeypatch, inject_policy):
    import api.profiles as profiles
    import api.routes as routes
    import api.governance.enforce as enforce

    inject_policy(POLICY)

    current_home = {"value": None}
    jobs_by_home = {
        "alpha-home": [{"id": "job-alpha", "name": "Alpha secret", "profile": None}],
        "beta-home": [{"id": "job-beta", "name": "Beta secret", "profile": None}],
        "default-home": [],
    }
    _install_cron_jobs(monkeypatch, jobs_by_home, current_home)

    class _Ctx:
        def __init__(self, home):
            self.home = str(home)
            self.prev = None

        def __enter__(self):
            self.prev = current_home["value"]
            current_home["value"] = self.home
            return self

        def __exit__(self, exc_type, exc, tb):
            current_home["value"] = self.prev
            return False

    monkeypatch.setattr(routes, "_get_active_profile_name", lambda: "alpha")
    monkeypatch.setattr(profiles, "list_profiles_api", lambda: [
        {"name": "alpha", "visible": True},
        {"name": "beta", "visible": True},
    ])
    monkeypatch.setattr(
        profiles,
        "get_hermes_home_for_profile",
        lambda name: Path({"alpha": "alpha-home", "beta": "beta-home",
                           "default": "default-home"}[name]),
    )
    monkeypatch.setattr(profiles, "cron_profile_context_for_home", _Ctx)

    def _as_user(email):
        identity = _identity(email) if email else None
        monkeypatch.setattr(enforce, "_request_identity", lambda handler: identity)

    return SimpleNamespace(as_user=_as_user, routes=routes)


def test_route_hides_foreign_jobs_from_governed_user(crons_route_env):
    """Acceptance: unauthorised jobs are absent from the API listing."""
    crons_route_env.as_user("beta@example.test")  # scoped to beta, active is alpha
    handler = _JSONHandler()
    assert crons_route_env.routes.handle_get(
        handler, SimpleNamespace(path="/api/crons", query="")) is not False

    assert handler.status == 200
    body = handler.body
    assert body["jobs"] == []  # the active (alpha) store is out of beta's scope
    assert body["other_profile_count"] == 1  # only beta's own foreign row counts
    assert "Alpha secret" not in handler.wfile.getvalue().decode("utf-8")


def test_route_keeps_own_profile_jobs_for_governed_user(crons_route_env):
    crons_route_env.as_user("alpha@example.test")
    handler = _JSONHandler()
    assert crons_route_env.routes.handle_get(
        handler, SimpleNamespace(path="/api/crons", query="")) is not False

    body = handler.body
    assert [row["id"] for row in body["jobs"]] == ["job-alpha"]
    assert body["other_profile_count"] == 0  # beta's row neither listed nor counted
    assert "Beta secret" not in handler.wfile.getvalue().decode("utf-8")


def test_route_keeps_admin_view_unchanged(crons_route_env):
    crons_route_env.as_user("cronadmin@example.test")
    handler = _JSONHandler()
    assert crons_route_env.routes.handle_get(
        handler, SimpleNamespace(path="/api/crons", query="all_profiles=1")) is not False

    body = handler.body
    assert body["all_profiles"] is True
    assert {row["id"] for row in body["jobs"]} == {"job-alpha", "job-beta"}


def test_detail_route_403s_out_of_scope_direct_url(crons_route_env):
    """Acceptance: unauthorised jobs cannot be retrieved by direct API request."""
    crons_route_env.as_user("beta@example.test")
    handler = _JSONHandler()
    assert crons_route_env.routes.handle_get(
        handler,
        SimpleNamespace(path="/api/crons/output", query="job_id=abcdef123456"),
    ) is not False
    assert handler.status == 403
    assert handler.body["error"] == "forbidden"


# ── POST mutation routes share the scope guard (D2, 26 Aug 2026) ────────────

CRON_MUTATION_PATHS = (
    "/api/crons/pause",
    "/api/crons/resume",
    "/api/crons/run",
    "/api/crons/delete",
)


@pytest.fixture
def cron_post_env(monkeypatch, inject_policy):
    """Drive handle_post at the cron mutation branches with spied handlers.

    The spies stand in for the real mutation handlers so the tests observe
    exactly what the guard lets through: a 403 must arrive BEFORE any
    handler runs, and an allowed call must reach the handler unchanged.
    """
    from contextlib import nullcontext

    import api.governance.enforce as enforce
    import api.profiles as profiles
    import api.routes as routes

    inject_policy(POLICY)

    monkeypatch.setattr(routes, "_get_active_profile_name", lambda: "alpha")
    monkeypatch.setattr(routes, "_check_csrf", lambda _handler: True)
    monkeypatch.setattr(
        routes, "_guard_request_session_visibility",
        lambda handler, parsed, body=None, method="POST": True,
    )
    monkeypatch.setattr(routes, "_ensure_agent_cron_import_path", lambda: None)
    monkeypatch.setattr(profiles, "cron_profile_context", nullcontext)

    calls = []

    def _spy(name):
        def _handler(handler, body):
            calls.append((name, dict(body)))
            return routes.j(handler, {"ok": True, "handler": name})
        return _handler

    for name in ("_handle_cron_pause", "_handle_cron_resume",
                 "_handle_cron_run", "_handle_cron_delete"):
        monkeypatch.setattr(routes, name, _spy(name))

    def _post(email, path, body=None):
        identity = _identity(email) if email else None
        monkeypatch.setattr(enforce, "_request_identity", lambda handler: identity)
        monkeypatch.setattr(
            routes, "read_body", lambda _handler: dict(body or {"job_id": "job-alpha"})
        )
        handler = _JSONHandler()
        assert routes.handle_post(
            handler, SimpleNamespace(path=path, query="")
        ) is not False
        return handler

    return SimpleNamespace(post=_post, calls=calls)


def test_governed_user_cannot_mutate_out_of_scope_jobs(cron_post_env):
    """Acceptance: pause/resume/run/delete 403 for an out-of-scope caller."""
    for path in CRON_MUTATION_PATHS:
        handler = cron_post_env.post("beta@example.test", path)  # active is alpha
        assert handler.status == 403, path
        assert handler.body == {"error": "forbidden", "reason": "cron_scope"}, path
    # No mutation handler ever ran: nothing executed, deleted, or leaked.
    assert cron_post_env.calls == []


def test_scoped_user_and_admin_can_still_mutate(cron_post_env):
    for email in ("alpha@example.test", "cronadmin@example.test", BOOTSTRAP):
        cron_post_env.calls.clear()
        for path in CRON_MUTATION_PATHS:
            handler = cron_post_env.post(email, path)
            assert handler.status == 200, (email, path)
            assert handler.body["ok"] is True, (email, path)
        assert [name for name, _ in cron_post_env.calls] == [
            "_handle_cron_pause", "_handle_cron_resume",
            "_handle_cron_run", "_handle_cron_delete",
        ]


def test_report_only_mode_allows_mutation_and_audits_would_deny(
    cron_post_env, inject_policy
):
    inject_policy({**POLICY, "mode": "report_only"})
    handler = cron_post_env.post("beta@example.test", "/api/crons/pause")
    assert handler.status == 200
    assert [name for name, _ in cron_post_env.calls] == ["_handle_cron_pause"]
    events = read_audit_events(5)
    assert len(events) == 1
    assert events[0]["event"] == "would_deny"
    assert events[0]["extra"]["profile"] == "alpha"


# ── Route wiring (source inspection, house pattern of #4768's test) ─────────

def _api_crons_branch() -> str:
    marker = ROUTES.index('if parsed.path == "/api/crons":')
    nxt = ROUTES.index('if parsed.path == "/api/crons/output":', marker)
    return ROUTES[marker:nxt]


def test_listing_route_applies_scope_filter_before_payload():
    branch = _api_crons_branch()
    assert "scope_cron_rows_for_caller" in branch, (
        "GET /api/crons must filter rows through api.cron_scope before "
        "building the payload (scheduled-jobs scope report, 26 Aug 2026)."
    )
    # Filter runs before the payload assembly and the hidden-count derivation,
    # so out-of-scope rows can neither be listed nor counted.
    assert branch.index("scope_cron_rows_for_caller") < branch.index(
        "jobs = active_jobs + other_jobs if all_profiles else active_jobs")


def test_detail_routes_share_the_scope_guard():
    guard = ROUTES.index("from api.cron_scope import caller_sees_cron_profile")
    # The guard's path gate covers every /api/crons/* GET detail branch.
    gate_start = ROUTES.rindex("if parsed.path in (", 0, guard)
    gate = ROUTES[gate_start:guard]
    for path in ("/api/crons/output", "/api/crons/history", "/api/crons/run",
                 "/api/crons/recent", "/api/crons/status", "/api/crons/delivery-options"):
        assert f'"{path}"' in gate, (
            f"the cron scope guard must cover the {path} GET branch so "
            "unauthorised jobs cannot be fetched by direct URL"
        )
    # The guard sits before the first detail dispatch and denies with a 403.
    assert guard < ROUTES.index("return _handle_cron_output(handler, parsed)")
    guard_block = ROUTES[guard:guard + 400]
    assert "status=403" in guard_block


def test_post_mutation_routes_share_the_scope_guard():
    """D2: the POST guard covers pause/resume/run/delete before dispatch."""
    guard = ROUTES.rindex("from api.cron_scope import caller_sees_cron_profile")
    gate_start = ROUTES.rindex("if parsed.path in (", 0, guard)
    gate = ROUTES[gate_start:guard]
    for path in ("/api/crons/delete", "/api/crons/run",
                 "/api/crons/pause", "/api/crons/resume"):
        assert f'"{path}"' in gate, (
            f"the cron scope guard must cover the {path} POST branch so "
            "out-of-scope jobs cannot be mutated by a known job_id"
        )
    # The guard sits before every mutation dispatch and denies with a 403.
    for dispatch in ("return _handle_cron_delete(handler, body)",
                     "return _handle_cron_run(handler, body)",
                     "return _handle_cron_pause(handler, body)",
                     "return _handle_cron_resume(handler, body)"):
        assert guard < ROUTES.index(dispatch)
    guard_block = ROUTES[guard:guard + 400]
    assert "status=403" in guard_block
