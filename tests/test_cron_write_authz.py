"""Cron create and update authorisation (program plan 3.1, package W0).

Before this fix ``POST /api/crons/update`` and ``/api/crons/create`` ran
before the per-job scope guard and handed every body key to ``update_job``:
any ``cron:write`` user could edit someone else's scheduled task, rewrite its
``origin`` or ``shared_with``, point its delivery at any recipient, or blank
``owner_email`` (the identity the engine runs the job as).

The rules pinned here:

* Only the fields the Tasks panel sends are accepted; identity fields, run
  state and anything unknown give 400.
* The per-job scope guard runs first, then ownership: the owner or a cron
  admin may edit, a sharee may not.
* Values are checked: ``deliver`` must be one of the caller's own delivery
  options, ``model`` and ``provider`` must be within the caller's model
  grants, ``script``, ``no_agent`` and ``managed_by`` are cron admin only,
  ``shared_with`` only names people in the policy.
* ``report_only`` never enforces (it audits ``would_deny``), and installs with
  governance off behave as before.

Harness: the real ``handle_post`` dispatcher with an injected policy and an
in-memory ``cron.jobs`` store (pattern of tests/test_scheduled_jobs_scope.py).
"""
from __future__ import annotations

import copy
import io
import json
import re
import sys
import types
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.governance import loader  # noqa: E402
from api.governance.audit import read_audit_events  # noqa: E402
from api.governance.loader import parse_governance_policy  # noqa: E402
from api.profiles import cron_profile_context as _REAL_CRON_PROFILE_CONTEXT  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
PANELS_JS = (REPO / "static" / "panels.js").read_text(encoding="utf-8")

BOOTSTRAP = "michael@example.test"
ADMIN = "cronadmin@example.test"
OWNER = "owner@example.test"
OTHER = "other@example.test"
SHAREE = "sharee@example.test"
FORMER = "former@example.test"      # was shared with, no longer in the policy
STRANGER = "stranger@example.test"  # never in the policy

WRITER_GRANTS = {
    "permissions": ["cron:read", "cron:write", "cron:run"],
    "profiles": ["alpha"],
    "routes": ["/api/crons", "/api/crons/*"],
    "models": {"providers": ["openai"], "models": ["gpt-allowed"]},
}

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
        "writer": {"grants": WRITER_GRANTS},
    },
    "users": {
        ADMIN: {"roles": ["cron_admin"]},
        OWNER: {"roles": ["writer"]},
        OTHER: {"roles": ["writer"]},
        SHAREE: {"roles": ["writer"]},
    },
}


def _identity(email):
    return {"email": email, "groups": [], "claims_subset": {}, "method": "oidc"}


def _stored_jobs():
    return {
        # Stamped by the engine and by the WebUI: owner_email is authoritative.
        "own": {
            "id": "own",
            "name": "Owner task",
            "prompt": "summarise the inbox",
            "schedule": {"kind": "interval", "minutes": 60},
            "deliver": "telegram:999",  # custom target the agent set at creation
            "model": "gpt-retired",  # pinned before the grants narrowed
            "provider": "openai",
            "owner_email": OWNER,
            "origin": {"platform": "webui", "chat_id": "sess-own", "user_id": OWNER},
            "shared_with": [SHAREE, FORMER],
            "created_at": "2026-09-01T09:00:00+00:00",
        },
        # Created from the Tasks panel before the owner stamp existed.
        "legacy": {
            "id": "legacy",
            "name": "Legacy task",
            "prompt": "ping",
            "schedule": {"kind": "interval", "minutes": 60},
            "deliver": "local",
            "owner_email": "",
            "origin": {"platform": "webui", "chat_id": "sess-legacy", "user_id": OWNER},
        },
        # owner_email says OTHER; a stale origin stamp must not override it.
        "reowned": {
            "id": "reowned",
            "name": "Reowned task",
            "prompt": "ping",
            "schedule": {"kind": "interval", "minutes": 60},
            "deliver": "local",
            "owner_email": OTHER,
            "origin": {"platform": "webui", "chat_id": "sess-x", "user_id": OWNER},
        },
    }


class _Store:
    """In-memory stand-in for cron.jobs with the engine's call shapes."""

    def __init__(self, owner_kwarg=True):
        self.jobs = _stored_jobs()
        self.creates = []
        self.updates = []
        self.owner_kwarg = owner_kwarg

    def module(self):
        store = self
        mod = types.ModuleType("cron.jobs")

        def get_job(job_id):
            job = store.jobs.get(job_id)
            return copy.deepcopy(job) if job is not None else None

        def update_job(job_id, updates):
            if job_id not in store.jobs:
                return None
            store.updates.append((job_id, copy.deepcopy(updates)))
            store.jobs[job_id].update(copy.deepcopy(updates))
            return copy.deepcopy(store.jobs[job_id])

        def _record(**kwargs):
            store.creates.append(kwargs)
            job = {
                "id": f"new{len(store.creates)}",
                "name": kwargs.get("name") or "new task",
                "prompt": kwargs.get("prompt"),
                "schedule": kwargs.get("schedule"),
                "deliver": kwargs.get("deliver"),
                "model": kwargs.get("model"),
                "provider": kwargs.get("provider"),
                "owner_email": str(kwargs.get("owner_email") or ""),
                "origin": kwargs.get("origin"),
            }
            store.jobs[job["id"]] = job
            return copy.deepcopy(job)

        if self.owner_kwarg:
            def create_job(prompt, schedule, name=None, deliver=None, origin=None, skills=None,
                           model=None, provider=None, script=None, no_agent=False,
                           owner_email=None, enabled=True):
                return _record(prompt=prompt, schedule=schedule, name=name, deliver=deliver,
                               origin=origin, skills=skills, model=model, provider=provider,
                               script=script, no_agent=no_agent, owner_email=owner_email,
                               enabled=enabled)
        else:
            # An engine from before create_job took owner_email.
            def create_job(prompt, schedule, name=None, deliver=None, origin=None, skills=None,
                           model=None, provider=None, enabled=True):
                return _record(prompt=prompt, schedule=schedule, name=name, deliver=deliver,
                               origin=origin, skills=skills, model=model, provider=provider,
                               enabled=enabled)

        mod.get_job = get_job
        mod.update_job = update_job
        mod.create_job = create_job
        return mod


class _JSONHandler:
    def __init__(self):
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
        return json.loads(self.wfile.getvalue().decode("utf-8"))


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


@pytest.fixture
def env(monkeypatch, inject_policy):
    """Drive handle_post at /api/crons/create and /api/crons/update."""
    import api.governance.enforce as enforce
    import api.profiles as profiles
    import api.routes as routes

    inject_policy(POLICY)
    state = SimpleNamespace(store=_Store(), active="default")

    def _install(store):
        cron_pkg = types.ModuleType("cron")
        cron_pkg.__path__ = []
        scheduler = types.ModuleType("cron.scheduler")
        scheduler._KNOWN_DELIVERY_PLATFORMS = frozenset({"telegram", "slack"})
        monkeypatch.setitem(sys.modules, "cron", cron_pkg)
        monkeypatch.setitem(sys.modules, "cron.jobs", store.module())
        monkeypatch.setitem(sys.modules, "cron.scheduler", scheduler)
        state.store = store

    _install(state.store)
    monkeypatch.setattr(routes, "_get_active_profile_name", lambda: state.active)
    monkeypatch.setattr(routes, "_check_csrf", lambda _handler: True)
    monkeypatch.setattr(
        routes, "_guard_request_session_visibility",
        lambda handler, parsed, body=None, method="POST": True,
    )
    monkeypatch.setattr(routes, "_ensure_agent_cron_import_path", lambda: None)
    monkeypatch.setattr(profiles, "cron_profile_context", nullcontext)
    monkeypatch.setattr(profiles, "list_profiles_api", lambda: [
        {"name": "alpha", "visible": True},
        {"name": "beta", "visible": True},
    ])

    def _post(email, path, body):
        identity = _identity(email) if email else None
        monkeypatch.setattr(enforce, "_request_identity", lambda handler: identity)
        monkeypatch.setattr(routes, "read_body", lambda _handler: copy.deepcopy(body))
        handler = _JSONHandler()
        assert routes.handle_post(handler, SimpleNamespace(path=path, query="")) is not False
        return handler

    def update(email, body):
        return _post(email, "/api/crons/update", body)

    def create(email, body):
        return _post(email, "/api/crons/create", body)

    state.update = update
    state.create = create
    state.install = _install
    return state


# The payloads static/panels.js sends today (emoji picker L1397, category
# popover L1503, share dialog L1567, saveCronForm L2402 and its create branch).
def _emoji_payload(job_id):
    return {"job_id": job_id, "emoji": "📬"}


def _category_payload(job_id):
    return {"job_id": job_id, "category": "Finance"}


def _share_payload(job_id, people):
    return {"job_id": job_id, "shared_with": list(people)}


def _form_update_payload(job_id, **overrides):
    payload = {
        "job_id": job_id,
        "schedule": "every 2h",
        "profile": "",
        "toast_notifications": True,
        "prompt": "summarise the inbox, briefly",
        "diagram": "flowchart LR\n  A --> B",
        "emoji": "📬",
        "category": "Finance",
        "name": "Owner task renamed",
        "deliver": "local",
        "model": "gpt-allowed",
        "provider": "openai",
    }
    payload.update(overrides)
    return payload


def _form_create_payload(**overrides):
    payload = {
        "schedule": "every 2h",
        "prompt": "summarise the inbox",
        "deliver": "local",
        "profile": "",
        "toast_notifications": True,
        "name": "New task",
        "diagram": "flowchart LR\n  A --> B",
        "emoji": "📬",
        "category": "Finance",
        "skills": ["google-workspace"],
        "model": "gpt-allowed",
        "provider": "openai",
    }
    payload.update(overrides)
    return payload


# ── Field allowlist ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("field,value", [
    ("owner_email", ""),
    ("owner_email", OTHER),
    ("origin", {"platform": "webui", "chat_id": None, "user_id": OTHER}),
    ("id", "../escape"),
    ("created_at", "2020-01-01T00:00:00+00:00"),
    ("last_run_at", "2020-01-01T00:00:00+00:00"),
    ("last_status", "ok"),
    ("next_run_at", None),
    ("state", "scheduled"),
    ("repeat", {"times": 1, "completed": 0}),
    ("workdir", "/"),
    ("enabled_toolsets", ["terminal"]),
    ("base_url", "http://127.0.0.1:1/v1"),
    ("context_from", "legacy"),
    ("enabled", True),
    ("skills", ["google-workspace"]),
    ("unknown_field", 1),
])
def test_update_refuses_fields_outside_the_allowlist(env, field, value):
    for email in (OWNER, ADMIN, BOOTSTRAP):
        handler = env.update(email, {"job_id": "own", field: value})
        assert handler.status == 400, (email, field)
        assert field in handler.body["error"], (email, field)
    assert env.store.updates == []
    assert env.store.jobs["own"]["owner_email"] == OWNER
    assert env.store.jobs["own"]["origin"]["user_id"] == OWNER


@pytest.mark.parametrize("field,value", [
    ("owner_email", OTHER),
    ("origin", {"platform": "telegram", "chat_id": "123"}),
    ("id", "chosen"),
    ("created_at", "2020-01-01T00:00:00+00:00"),
    ("job_id", "own"),
    ("unknown_field", 1),
])
def test_create_refuses_fields_outside_the_allowlist(env, field, value):
    for email in (OWNER, ADMIN):
        handler = env.create(email, _form_create_payload(**{field: value}))
        assert handler.status == 400, (email, field)
        assert field in handler.body["error"], (email, field)
    assert env.store.creates == []


def _object_keys(literal: str) -> set[str]:
    keys = set()
    for part in literal.split(","):
        key = part.split(":", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


def _function_body(name: str) -> str:
    start = PANELS_JS.index(f"function {name}(")
    brace = PANELS_JS.index("{", PANELS_JS.index(")", start))
    depth = 0
    for idx in range(brace, len(PANELS_JS)):
        if PANELS_JS[idx] == "{":
            depth += 1
        elif PANELS_JS[idx] == "}":
            depth -= 1
            if depth == 0:
                return PANELS_JS[brace + 1:idx]
    raise AssertionError(f"{name} body did not terminate")


def test_every_panels_payload_field_is_allowlisted():
    """The four static/panels.js callers keep working: every key they send is
    accepted. Asserted as a subset so a later field (for example notify) only
    needs its own allowlist entry."""
    import api.routes as routes

    single_field = [
        _object_keys(m.group(1))
        for m in re.finditer(
            r"api\('/api/crons/update',\s*\{\s*method:\s*'POST',\s*body:\s*JSON\.stringify\(\{([^{}]*)\}\)",
            PANELS_JS,
        )
    ]
    assert {"job_id", "emoji"} in single_field
    assert {"job_id", "category"} in single_field
    assert {"job_id", "shared_with"} in single_field

    form = _function_body("saveCronForm")
    updates = _object_keys(re.search(r"const updates\s*=\s*\{([^{}]*)\}", form).group(1))
    updates |= set(re.findall(r"\bupdates\.(\w+)\s*=", form))
    body = _object_keys(re.search(r"const body\s*=\s*\{([^{}]*)\}", form).group(1))
    body |= set(re.findall(r"\bbody\.(\w+)\s*=", form))
    assert {"schedule", "prompt", "deliver", "model", "provider"} <= updates
    assert {"schedule", "prompt", "deliver", "enabled", "skills"} <= body

    update_keys = set().union(*single_field, updates) - {"job_id"}
    assert update_keys <= routes._CRON_WRITE_FIELDS, update_keys - routes._CRON_WRITE_FIELDS
    create_fields = routes._CRON_WRITE_FIELDS | routes._CRON_CREATE_ONLY_FIELDS
    assert body <= create_fields, body - create_fields


# ── Ownership ───────────────────────────────────────────────────────────────

def test_owner_keeps_every_panels_payload_working(env):
    for payload in (
        _emoji_payload("own"),
        _category_payload("own"),
        _share_payload("own", [SHAREE, FORMER, OTHER]),
        _form_update_payload("own"),
    ):
        handler = env.update(OWNER, payload)
        assert handler.status == 200, (payload, handler.body)
        assert handler.body["ok"] is True
    assert [job_id for job_id, _ in env.store.updates] == ["own"] * 4
    job = env.store.jobs["own"]
    assert job["name"] == "Owner task renamed"
    assert job["shared_with"] == [SHAREE, FORMER, OTHER]
    assert job["owner_email"] == OWNER


def test_legacy_webui_job_is_edited_by_its_creator(env):
    handler = env.update(OWNER, _form_update_payload("legacy"))
    assert handler.status == 200, handler.body
    assert env.store.updates[0][0] == "legacy"


def test_foreign_job_outside_scope_is_forbidden(env):
    """OTHER holds cron:write but the root store job is neither theirs nor shared."""
    for payload in (_emoji_payload("own"), _form_update_payload("own"),
                    _share_payload("own", [OTHER])):
        handler = env.update(OTHER, payload)
        assert handler.status == 403, payload
        assert handler.body["reason"] == "cron_scope"
    assert env.store.updates == []


def test_foreign_job_in_a_visible_store_is_forbidden(env):
    """Seeing a job through a profile grant is not a licence to edit it."""
    env.active = "alpha"  # OTHER is granted alpha, so the job is visible
    for payload in (_emoji_payload("own"), _form_update_payload("own", deliver="telegram"),
                    _share_payload("own", [OTHER])):
        handler = env.update(OTHER, payload)
        assert handler.status == 403, payload
        assert handler.body["reason"] == "cron_owner"
    assert env.store.updates == []


def test_sharee_can_see_but_not_edit(env):
    for payload in (_emoji_payload("own"), _category_payload("own"),
                    _share_payload("own", [SHAREE, OTHER]), _form_update_payload("own")):
        handler = env.update(SHAREE, payload)
        assert handler.status == 403, payload
        assert handler.body["reason"] == "cron_owner"
    assert env.store.updates == []


def test_owner_email_outranks_a_stale_origin_stamp(env):
    env.active = "alpha"
    handler = env.update(OWNER, _emoji_payload("reowned"))
    assert handler.status == 403
    assert handler.body["reason"] == "cron_owner"
    assert env.store.updates == []


def test_cron_admin_and_bootstrap_admin_edit_any_job(env):
    for email in (ADMIN, BOOTSTRAP):
        handler = env.update(email, _form_update_payload("own", deliver="telegram:12345"))
        assert handler.status == 200, (email, handler.body)
    assert [job_id for job_id, _ in env.store.updates] == ["own", "own"]


def test_guard_runs_inside_the_real_profile_lock_without_deadlock(env, monkeypatch):
    """The update handler holds cron_profile_context, whose lock is not
    reentrant; the scope guard must reuse the loaded row, not lock again."""
    import threading

    import api.profiles as profiles

    monkeypatch.setattr(profiles, "_cron_env_lock", threading.Lock())
    monkeypatch.setattr(profiles, "cron_profile_context", _REAL_CRON_PROFILE_CONTEXT)
    results = {}

    def _run(email, key):
        results[key] = env.update(email, _emoji_payload("own")).status

    for email, key in ((OTHER, "other"), (SHAREE, "sharee"), (OWNER, "owner")):
        worker = threading.Thread(target=_run, args=(email, key), daemon=True)
        worker.start()
        worker.join(10)
        assert not worker.is_alive(), f"{key}: cron write guard deadlocked on the profile lock"
    assert results == {"other": 403, "sharee": 403, "owner": 200}


def test_missing_job_is_404_for_everyone(env):
    for email in (OWNER, ADMIN):
        handler = env.update(email, _emoji_payload("ghost"))
        assert handler.status == 404, email


def test_report_only_allows_a_foreign_edit_and_audits_it(env, inject_policy):
    inject_policy({**POLICY, "mode": "report_only"})
    env.active = "alpha"
    handler = env.update(OTHER, _emoji_payload("own"))
    assert handler.status == 200, handler.body
    assert env.store.updates == [("own", {"emoji": "📬"})]
    events = read_audit_events(10)
    assert [e["event"] for e in events] == ["would_deny"]
    assert events[0]["reason"] == "cron_owner"
    assert events[0]["path"] == "/api/crons/update"
    assert events[0]["method"] == "POST"
    assert events[0]["report_only"] is True
    assert OTHER not in json.dumps(events)  # identity is stored hashed


def test_report_only_still_refuses_identity_fields(env, inject_policy):
    inject_policy({**POLICY, "mode": "report_only"})
    handler = env.update(OTHER, {"job_id": "own", "owner_email": ""})
    assert handler.status == 400
    assert env.store.updates == []


def test_governance_off_keeps_single_user_installs_unchanged(env, inject_policy):
    inject_policy({"version": 1, "mode": "off", "default_effect": "deny"})
    handler = env.update(None, _form_update_payload("own", deliver="telegram:12345",
                                                    model="any-model", provider="any"))
    assert handler.status == 200, handler.body
    handler = env.update(None, {"job_id": "own", "script": "report.sh", "no_agent": True})
    assert handler.status == 200, handler.body
    handler = env.update(None, _share_payload("own", [STRANGER]))
    assert handler.status == 200, handler.body
    handler = env.update(None, {"job_id": "own", "owner_email": ""})
    assert handler.status == 400


# ── Value checks ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("deliver", ["telegram:12345", "slack:#general", "all", "origin,telegram:1", "discord"])
def test_deliver_outside_the_callers_options_is_forbidden(env, deliver):
    handler = env.update(OWNER, _form_update_payload("own", deliver=deliver))
    assert handler.status == 403
    assert handler.body["reason"] == "cron_deliver"
    handler = env.create(OWNER, _form_create_payload(deliver=deliver))
    assert handler.status == 403
    assert handler.body["reason"] == "cron_deliver"
    assert env.store.updates == [] and env.store.creates == []


@pytest.mark.parametrize("deliver", ["local", "origin", "telegram", "slack"])
def test_deliver_from_the_callers_options_is_allowed(env, deliver):
    handler = env.update(OWNER, _form_update_payload("own", deliver=deliver))
    assert handler.status == 200, handler.body
    assert env.store.jobs["own"]["deliver"] == deliver
    handler = env.create(OWNER, _form_create_payload(deliver=deliver))
    assert handler.status == 200, handler.body


def test_delivery_options_route_and_write_check_share_one_list(env):
    import api.routes as routes

    handler = _JSONHandler()
    routes._handle_cron_delivery_options(handler)
    offered = {p["value"] for p in handler.body["platforms"]}
    assert offered == {"local", "origin", "telegram", "slack"}
    assert offered == {p["value"] for p in routes._cron_delivery_platforms()}


def test_unchanged_custom_deliver_can_be_saved_back(env):
    """The form re-sends the stored target (shown as 'telegram:999 *')."""
    handler = env.update(OWNER, _form_update_payload("own", deliver="telegram:999"))
    assert handler.status == 200, handler.body


@pytest.mark.parametrize("payload", [
    {"script": "report.sh"},
    {"no_agent": True},
    {"managed_by": "synthwave"},
    {"script": "report.sh", "no_agent": True},
])
def test_script_no_agent_and_managed_by_are_cron_admin_only(env, payload):
    handler = env.update(OWNER, {"job_id": "own", **payload})
    assert handler.status == 403
    assert handler.body["reason"] == "cron_admin_field"
    handler = env.create(OWNER, _form_create_payload(**payload))
    assert handler.status == 403
    assert handler.body["reason"] == "cron_admin_field"
    assert env.store.updates == [] and env.store.creates == []

    handler = env.update(ADMIN, {"job_id": "own", **payload})
    assert handler.status == 200, handler.body
    handler = env.create(ADMIN, _form_create_payload(**payload))
    assert handler.status == 200, handler.body


def test_admin_field_values_are_validated(env):
    for payload in ({"managed_by": "someone"}, {"no_agent": "yes"}, {"script": ["a"]}):
        handler = env.update(ADMIN, {"job_id": "own", **payload})
        assert handler.status == 400, payload
    assert env.store.updates == []
    handler = env.update(ADMIN, {"job_id": "own", "managed_by": "Client"})
    assert handler.status == 200
    assert env.store.jobs["own"]["managed_by"] == "client"
    handler = env.update(ADMIN, {"job_id": "own", "managed_by": ""})
    assert handler.status == 200
    assert env.store.jobs["own"]["managed_by"] is None


def test_admin_script_fields_reach_create_job(env):
    handler = env.create(ADMIN, _form_create_payload(script="report.sh", no_agent=True,
                                                     managed_by="synthwave"))
    assert handler.status == 200, handler.body
    assert env.store.creates[0]["script"] == "report.sh"
    assert env.store.creates[0]["no_agent"] is True
    assert env.store.jobs["new1"]["managed_by"] == "synthwave"


def test_shared_with_only_names_people_in_the_policy(env):
    handler = env.update(OWNER, _share_payload("own", [SHAREE, STRANGER]))
    assert handler.status == 400
    assert STRANGER in handler.body["error"]
    handler = env.update(ADMIN, _share_payload("own", [STRANGER]))
    assert handler.status == 400
    handler = env.create(OWNER, _form_create_payload(shared_with=[STRANGER]))
    assert handler.status == 400
    assert env.store.updates == [] and env.store.creates == []

    # A sharee already on the task may stay after leaving the directory.
    handler = env.update(OWNER, _share_payload("own", [FORMER, OTHER, BOOTSTRAP]))
    assert handler.status == 200, handler.body
    assert env.store.jobs["own"]["shared_with"] == [FORMER, OTHER, BOOTSTRAP]
    handler = env.create(OWNER, _form_create_payload(shared_with=[OTHER]))
    assert handler.status == 200, handler.body


def test_model_outside_the_callers_grants_is_forbidden(env):
    handler = env.update(OWNER, _form_update_payload("own", model="gpt-forbidden", provider="openai"))
    assert handler.status == 403
    assert handler.body["reason"] == "cron_model"
    handler = env.update(OWNER, _form_update_payload("own", model="gpt-allowed", provider="anthropic"))
    assert handler.status == 403
    handler = env.create(OWNER, _form_create_payload(model="gpt-forbidden", provider="openai"))
    assert handler.status == 403
    assert handler.body["reason"] == "cron_model"
    assert env.store.updates == [] and env.store.creates == []

    handler = env.update(ADMIN, _form_update_payload("own", model="gpt-forbidden", provider="openai"))
    assert handler.status == 200, handler.body


def test_model_within_grants_unchanged_or_cleared_is_allowed(env):
    # The stored pin is saved back as is; a new pin must be granted; clearing
    # falls back to the profile default.
    for model, provider in (("gpt-retired", "openai"), ("gpt-allowed", "openai"), (None, None)):
        handler = env.update(OWNER, _form_update_payload("own", model=model, provider=provider))
        assert handler.status == 200, (model, provider, handler.body)
    handler = env.create(OWNER, _form_create_payload(model=None, provider=None))
    assert handler.status == 200, handler.body


# ── cron_scope ownership helper ─────────────────────────────────────────────

def test_identity_owns_cron_job_rules():
    from api.cron_scope import identity_owns_cron_job

    jobs = _stored_jobs()
    no_session = lambda sid: ""  # noqa: E731
    assert identity_owns_cron_job(_identity(OWNER), jobs["own"], no_session) is True
    assert identity_owns_cron_job(_identity(OWNER), jobs["legacy"], no_session) is True
    assert identity_owns_cron_job(_identity(OWNER), jobs["reowned"], no_session) is False
    assert identity_owns_cron_job(_identity(OTHER), jobs["reowned"], no_session) is True
    assert identity_owns_cron_job(_identity(SHAREE), jobs["own"], no_session) is False
    assert identity_owns_cron_job(None, jobs["own"], no_session) is False
    unstamped = dict(jobs["legacy"], origin={"platform": "webui", "chat_id": "sess-9"})
    assert identity_owns_cron_job(_identity(OWNER), unstamped, lambda sid: OWNER) is True
    telegram = dict(jobs["legacy"], origin={"platform": "telegram", "chat_id": "1", "user_id": OWNER})
    assert identity_owns_cron_job(_identity(OWNER), telegram, no_session) is False

