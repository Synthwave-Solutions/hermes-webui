"""Cron write authorisation (program plan 3.1, package W0).

Before this fix ``POST /api/crons/update`` and ``/api/crons/create`` ran
before the per-job scope guard and handed every body key to ``update_job``:
any ``cron:write`` user could edit someone else's scheduled task, rewrite its
``origin`` or ``shared_with``, point its delivery at any recipient, or blank
``owner_email`` (the identity the engine runs the job as).

The rules pinned here:

* Only the fields the Tasks panel sends are accepted, each in the shape the
  panel sends it (for cron admins too); identity fields, run state, anything
  unknown and a wrong shape give 400.
* The per-job scope guard runs first, then ownership: the owner or a cron
  admin may edit, a sharee may not. The same ownership rule covers pause,
  resume, delete and run, which are reached through the same scope guard.
* Values are checked: ``deliver`` must be one of the caller's own delivery
  options, ``model`` and ``provider`` must be within the caller's model
  grants, every new ``skills`` entry must be one a chat turn of the caller
  could load, ``script``, ``no_agent`` and ``managed_by`` are cron admin only,
  ``shared_with`` only names people in the policy.
* On create the owner and the origin are stamped from the signed-in identity.
  A task without an owner gets its creator as owner with their first update
  or resume where the engine takes the stamp; where it cannot and cannot
  govern the run either, that change is refused.
* The four job routes read ``job_id`` once, as a non-empty string.
* Run now runs governed: through the engine's ``run_job_governed`` when it
  has one, otherwise bound to the owner's governance like a chat turn, and
  never unbound for anyone but a cron admin.
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
from api.governance.agent_context import (  # noqa: E402
    bind_governed_agent_turn as _REAL_BIND,
    reset_governed_agent_turn as _REAL_RESET,
)
from api.profiles import cron_profile_context as _REAL_CRON_PROFILE_CONTEXT  # noqa: E402
from api.routes import _handle_cron_run as _REAL_HANDLE_CRON_RUN  # noqa: E402

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
    # A chat turn loads a skill through the skill_view tool: the skills
    # toolset plus a view grant for the skill.
    "tools": {"toolsets": ["skills"]},
    "skills": {"view": ["google-workspace"]},
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
        self.actions = []  # (action, job_id) for pause, resume, delete and run
        self.owner_kwarg = owner_kwarg

    def module(self):
        store = self
        mod = types.ModuleType("cron.jobs")

        def get_job(job_id):
            job = store.jobs.get(job_id)
            return copy.deepcopy(job) if job is not None else None

        def update_job(job_id, updates):
            # Like the engine: fields named in _IMMUTABLE_JOB_FIELDS (only
            # "id" on the live engine, the identity fields as well on E0)
            # are refused.
            immutable = set(getattr(mod, "_IMMUTABLE_JOB_FIELDS", ())).intersection(updates or {})
            if immutable:
                raise ValueError(f"Cron job field(s) cannot be updated: {', '.join(sorted(immutable))}")
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

        class AmbiguousJobReference(LookupError):
            pass

        # Like the engine's cron.jobs.resolve_job_ref: an exact id first, then
        # a case-insensitive name. pause_job, resume_job and remove_job accept
        # either, while get_job and update_job match ids only.
        def resolve_job_ref(ref):
            if not ref:
                return None
            if ref in store.jobs:
                return copy.deepcopy(store.jobs[ref])
            matches = [job for job in store.jobs.values()
                       if str(job.get("name") or "").lower() == str(ref).lower()]
            if len(matches) > 1:
                raise AmbiguousJobReference(ref)
            return copy.deepcopy(matches[0]) if matches else None

        def pause_job(job_id, reason=None):
            job = resolve_job_ref(job_id)
            if not job:
                return None
            store.actions.append(("pause", job["id"]))
            store.jobs[job["id"]]["enabled"] = False
            return copy.deepcopy(store.jobs[job["id"]])

        def resume_job(job_id):
            job = resolve_job_ref(job_id)
            if not job:
                return None
            store.actions.append(("resume", job["id"]))
            store.jobs[job["id"]]["enabled"] = True
            return copy.deepcopy(store.jobs[job["id"]])

        def remove_job(job_id):
            job = resolve_job_ref(job_id)
            if not job:
                return False
            store.actions.append(("delete", job["id"]))
            del store.jobs[job["id"]]
            return True

        mod.create_job = create_job
        mod.AmbiguousJobReference = AmbiguousJobReference
        mod.resolve_job_ref = resolve_job_ref
        mod.pause_job = pause_job
        mod.resume_job = resume_job
        mod.remove_job = remove_job
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

    # "Run now" starts a worker thread; the stand-in records the run instead.
    def _run_handler(handler, body):
        job_id = body.get("job_id", "")
        if job_id not in state.store.jobs:
            return routes.bad(handler, "Job not found", 404)
        state.store.actions.append(("run", job_id))
        return routes.j(handler, {"ok": True, "job_id": job_id, "status": "running"})

    monkeypatch.setattr(routes, "_handle_cron_run", _run_handler)

    def act(email, action, job_id):
        return _post(email, f"/api/crons/{action}", {"job_id": job_id})

    state.update = update
    state.create = create
    state.act = act
    state.install = _install
    return state


@pytest.fixture
def run_env(env, monkeypatch, tmp_path):
    """``env`` with the real Run now handler. The worker thread it starts is
    recorded (job, homes and the run plan) instead of running the job."""
    import threading

    import api.profiles as profiles
    import api.routes as routes

    monkeypatch.setattr(routes, "_handle_cron_run", _REAL_HANDLE_CRON_RUN)
    store_home = tmp_path / "store"
    store_home.mkdir()
    monkeypatch.setattr(profiles, "get_active_hermes_home", lambda: store_home)
    monkeypatch.setattr(routes, "_available_cron_profile_names", lambda: {"default", "alpha", "beta"})
    env.store_home = store_home
    env.runs = []
    started = threading.Event()

    def _tracked(job, profile_home=None, execution_profile_home=None, event_profile=None, run_plan=None,
                 actor=None):
        env.runs.append(SimpleNamespace(job=job, profile_home=profile_home,
                                        execution_profile_home=execution_profile_home,
                                        run_plan=run_plan))
        routes._mark_cron_done(job["id"])
        started.set()

    monkeypatch.setattr(routes, "_run_cron_tracked", _tracked)
    act = env.act

    def _act(email, action, job_id):
        started.clear()
        handler = act(email, action, job_id)
        if action == "run" and handler.status == 200:
            assert started.wait(5), "the Run now worker did not start"
        return handler

    env.act = _act
    return env


def _engine_has_run_job_governed(monkeypatch, present=True):
    """Give the fake engine the governed entry point E0 adds, or take it away."""
    scheduler = sys.modules["cron.scheduler"]
    if present:
        monkeypatch.setattr(scheduler, "run_job_governed",
                            lambda job, *, reason, **kwargs: None, raising=False)
    else:
        monkeypatch.delattr(scheduler, "run_job_governed", raising=False)


# cron.jobs._IMMUTABLE_JOB_FIELDS on an engine with the identity fix (E0); the
# live engine's is {"id"}.
E0_IMMUTABLE_JOB_FIELDS = frozenset({"id", "owner_email", "origin", "created_at"})


def _engine_identity_fields_immutable(monkeypatch):
    """Make the fake engine's update_job refuse owner_email, origin and
    created_at, as the engine with the identity fix (E0) does."""
    monkeypatch.setattr(sys.modules["cron.jobs"], "_IMMUTABLE_JOB_FIELDS",
                        E0_IMMUTABLE_JOB_FIELDS, raising=False)


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
    ("skill", "google-workspace"),
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


# ── Pause, resume, delete and run follow the same ownership rule ────────────
# Before this fix those four routes only ran the scope guard, which admits a
# job shared with the caller and every job in a profile they are granted: a
# sharee could pause or delete the owner's task, and so could anyone holding
# the profile grant. A run executes as the owner (owner_email) and delivers to
# the owner's targets, so it is not the sharee's to trigger either.

JOB_ACTIONS = ("pause", "resume", "delete", "run")


@pytest.mark.parametrize("action", JOB_ACTIONS)
def test_sharee_cannot_pause_resume_delete_or_run(env, action):
    handler = env.act(SHAREE, action, "own")
    assert handler.status == 403, handler.body
    assert handler.body["reason"] == "cron_owner"
    assert env.store.actions == []
    assert "own" in env.store.jobs


@pytest.mark.parametrize("action", JOB_ACTIONS)
def test_profile_grant_non_owner_cannot_pause_resume_delete_or_run(env, action):
    env.active = "alpha"  # OTHER is granted alpha, so the job is visible
    handler = env.act(OTHER, action, "own")
    assert handler.status == 403, handler.body
    assert handler.body["reason"] == "cron_owner"
    assert env.store.actions == []


@pytest.mark.parametrize("action", JOB_ACTIONS)
def test_out_of_scope_caller_still_gets_the_scope_refusal(env, action):
    handler = env.act(OTHER, action, "own")  # root store, neither own nor shared
    assert handler.status == 403
    assert handler.body["reason"] == "cron_scope"
    assert env.store.actions == []


@pytest.mark.parametrize("action", JOB_ACTIONS)
def test_owner_and_cron_admins_can_pause_resume_delete_and_run(env, action):
    for email in (OWNER, ADMIN, BOOTSTRAP):
        env.install(_Store())
        handler = env.act(email, action, "own")
        assert handler.status == 200, (email, handler.body)
        assert env.store.actions == [(action, "own")], email


def test_legacy_creator_and_stamped_owner_can_act(env):
    env.active = "alpha"
    assert env.act(OWNER, "pause", "legacy").status == 200
    assert env.act(OTHER, "pause", "reowned").status == 200
    # A stale origin stamp does not make OWNER the owner of OTHER's job.
    assert env.act(OWNER, "delete", "reowned").status == 403
    assert env.store.actions == [("pause", "legacy"), ("pause", "reowned")]


def test_missing_job_still_answers_404(env):
    for action in JOB_ACTIONS:
        assert env.act(OWNER, action, "ghost").status == 404, action


def test_report_only_lets_a_sharee_act_and_audits_it(env, inject_policy):
    inject_policy({**POLICY, "mode": "report_only"})
    handler = env.act(SHAREE, "pause", "own")
    assert handler.status == 200, handler.body
    assert env.store.actions == [("pause", "own")]
    events = read_audit_events(10)
    assert [e["event"] for e in events] == ["would_deny"]
    assert events[0]["reason"] == "cron_owner"
    assert events[0]["path"] == "/api/crons/pause"
    assert events[0]["extra"]["job_id"] == "own"


def test_governance_off_keeps_actions_unchanged(env, inject_policy):
    inject_policy({"version": 1, "mode": "off", "default_effect": "deny"})
    for action in JOB_ACTIONS:
        env.install(_Store())
        assert env.act(None, action, "own").status == 200, action
        assert env.store.actions == [(action, "own")]


def test_action_owner_check_does_not_deadlock_on_the_profile_lock(env, monkeypatch):
    import threading

    import api.profiles as profiles

    monkeypatch.setattr(profiles, "_cron_env_lock", threading.Lock())
    monkeypatch.setattr(profiles, "cron_profile_context", _REAL_CRON_PROFILE_CONTEXT)
    results = {}

    def _run(email, key):
        results[key] = env.act(email, "pause", "own").status

    for email, key in ((SHAREE, "sharee"), (OWNER, "owner")):
        worker = threading.Thread(target=_run, args=(email, key), daemon=True)
        worker.start()
        worker.join(10)
        assert not worker.is_alive(), f"{key}: cron action owner check deadlocked"
    assert results == {"sharee": 403, "owner": 200}


def test_owner_check_fails_closed_when_the_store_cannot_be_read(env, monkeypatch):
    def _broken(job_id):
        raise OSError("jobs.json unreadable")

    monkeypatch.setattr(sys.modules["cron.jobs"], "get_job", _broken)
    handler = env.act(SHAREE, "delete", "own")
    assert handler.status == 403
    assert env.store.actions == []


def test_owner_check_refuses_when_the_cron_package_cannot_be_imported(env, monkeypatch):
    monkeypatch.setitem(sys.modules, "cron.jobs", None)  # import fails
    handler = env.act(SHAREE, "pause", "own")
    assert handler.status == 403
    assert handler.body["reason"] == "cron_owner"
    assert env.store.actions == []


def test_the_agent_cron_package_is_pinned_before_the_guards_read_the_store(env, monkeypatch):
    """A plugin's top-level ``cron`` package can shadow the agent's until a
    cron route pins the agent dir first: the guards must not read the store
    before that pin (tests/test_cron_import_shadowing.py)."""
    import api.routes as routes

    order = []
    store_get_job = sys.modules["cron.jobs"].get_job

    def _get_job(job_id):
        order.append("lookup")
        return store_get_job(job_id)

    monkeypatch.setattr(sys.modules["cron.jobs"], "get_job", _get_job)
    monkeypatch.setattr(routes, "_ensure_agent_cron_import_path", lambda: order.append("pin"))
    assert env.act(OWNER, "pause", "own").status == 200
    assert "lookup" in order
    assert order.index("pin") < order.index("lookup"), order


# ── An ownerless task gets its owner with its creator's first change ────────
# A Tasks panel task from before the owner stamp has an empty owner_email; its
# creator owns it through the task's WebUI origin (identity_owns_cron_job).
# The live engine's scheduler fires a task without an owner with nothing bound
# (_governed_as_job_owner just yields), so the creator, a governed non-admin,
# could rewrite its prompt, skills, schedule, model or delivery, or resume it,
# and the next scheduled fire ran that with unrestricted tools; Run now
# already refuses to run unbound for a non-admin. The creator's change now
# stamps them as the owner in the same write (a resume: before the task is
# enabled). An engine whose update_job refuses owner_email (the identity fix,
# E0) refuses ownerless agent fires under enforce itself, which its
# run_job_governed marks, so nothing is stamped there; an engine that can do
# neither refuses the change. Cron admins' changes stamp nothing.

LEGACY_TASK_PAYLOADS = [
    pytest.param(_emoji_payload("legacy"), id="emoji"),
    pytest.param(_category_payload("legacy"), id="category"),
    pytest.param(_share_payload("legacy", [SHAREE]), id="share"),
    pytest.param(_form_update_payload("legacy", prompt="do anything", schedule="every 1m"), id="form"),
]


@pytest.mark.parametrize("payload", LEGACY_TASK_PAYLOADS)
def test_the_creators_update_stamps_an_ownerless_task(env, payload):
    handler = env.update(OWNER, payload)
    assert handler.status == 200, handler.body
    # One write: the change never lands without the owner.
    assert len(env.store.updates) == 1
    job_id, updates = env.store.updates[0]
    assert job_id == "legacy"
    assert updates["owner_email"] == OWNER
    assert env.store.jobs["legacy"]["owner_email"] == OWNER
    for key in set(payload) - {"job_id"}:
        assert key in updates, key


def test_the_creators_resume_stamps_an_ownerless_task_before_enabling_it(env, monkeypatch):
    env.store.jobs["legacy"]["enabled"] = False
    jobs_module = sys.modules["cron.jobs"]
    resume_job = jobs_module.resume_job
    owner_at_resume = []

    def _resume(job_id):
        owner_at_resume.append(env.store.jobs[job_id]["owner_email"])
        return resume_job(job_id)

    monkeypatch.setattr(jobs_module, "resume_job", _resume)
    handler = env.act(OWNER, "resume", "legacy")
    assert handler.status == 200, handler.body
    assert owner_at_resume == [OWNER]
    assert env.store.updates == [("legacy", {"owner_email": OWNER})]
    assert env.store.actions == [("resume", "legacy")]
    assert env.store.jobs["legacy"]["enabled"] is True


def test_pause_delete_and_a_stamped_task_stamp_nothing(env):
    assert env.act(OWNER, "pause", "legacy").status == 200
    assert env.update(OWNER, _form_update_payload("own")).status == 200
    assert env.act(OWNER, "resume", "own").status == 200
    assert env.act(OWNER, "delete", "legacy").status == 200
    assert all("owner_email" not in updates for _, updates in env.store.updates)
    assert env.store.jobs["own"]["owner_email"] == OWNER


def test_a_cron_admins_change_leaves_an_ownerless_task_ownerless(env, inject_policy):
    for email in (ADMIN, BOOTSTRAP):
        env.install(_Store())
        env.store.jobs["legacy"]["enabled"] = False
        assert env.update(email, _form_update_payload("legacy")).status == 200, email
        assert env.act(email, "resume", "legacy").status == 200, email
        assert env.store.jobs["legacy"]["owner_email"] == "", email
        assert all("owner_email" not in updates for _, updates in env.store.updates), email
    inject_policy({"version": 1, "mode": "off", "default_effect": "deny"})
    env.install(_Store())
    env.store.jobs["legacy"]["enabled"] = False
    assert env.update(None, _form_update_payload("legacy")).status == 200
    assert env.act(None, "resume", "legacy").status == 200
    assert env.store.jobs["legacy"]["owner_email"] == ""


def test_report_only_never_makes_a_non_owner_the_owner(env, inject_policy):
    inject_policy({**POLICY, "mode": "report_only"})
    env.active = "alpha"  # OTHER sees the task through the profile grant
    env.store.jobs["legacy"]["enabled"] = False
    assert env.update(OTHER, _emoji_payload("legacy")).status == 200
    assert env.act(OTHER, "resume", "legacy").status == 200
    assert env.store.jobs["legacy"]["owner_email"] == ""
    assert [e["reason"] for e in read_audit_events(10)] == ["cron_owner", "cron_owner"]
    # The creator's own change is stamped under report_only as well.
    assert env.update(OWNER, _emoji_payload("legacy")).status == 200
    assert env.store.jobs["legacy"]["owner_email"] == OWNER


def test_an_engine_that_governs_ownerless_fires_needs_no_stamp(env, monkeypatch):
    _engine_identity_fields_immutable(monkeypatch)
    _engine_has_run_job_governed(monkeypatch)
    env.store.jobs["legacy"]["enabled"] = False
    handler = env.update(OWNER, _form_update_payload("legacy"))
    assert handler.status == 200, handler.body
    handler = env.act(OWNER, "resume", "legacy")
    assert handler.status == 200, handler.body
    assert env.store.jobs["legacy"]["owner_email"] == ""
    assert env.store.jobs["legacy"]["enabled"] is True
    assert all("owner_email" not in updates for _, updates in env.store.updates)


def test_an_engine_that_can_neither_stamp_nor_govern_refuses_the_change(env, monkeypatch):
    _engine_identity_fields_immutable(monkeypatch)
    _engine_has_run_job_governed(monkeypatch, present=False)
    env.store.jobs["legacy"]["enabled"] = False
    before = copy.deepcopy(env.store.jobs)
    for handler in (env.update(OWNER, _form_update_payload("legacy")),
                    env.update(OWNER, _emoji_payload("legacy")),
                    env.act(OWNER, "resume", "legacy")):
        assert handler.status == 403, handler.body
        assert handler.body["reason"] == "cron_run_ungoverned"
    assert env.store.jobs == before
    assert env.store.updates == [] and env.store.actions == []
    # The creator's stamped tasks, a pause, and cron admins are unaffected.
    assert env.update(OWNER, _emoji_payload("own")).status == 200
    assert env.act(OWNER, "pause", "legacy").status == 200
    assert env.update(ADMIN, _emoji_payload("legacy")).status == 200
    assert env.act(ADMIN, "resume", "legacy").status == 200


def test_report_only_audits_an_ungoverned_change_instead(env, monkeypatch, inject_policy):
    inject_policy({**POLICY, "mode": "report_only"})
    _engine_identity_fields_immutable(monkeypatch)
    _engine_has_run_job_governed(monkeypatch, present=False)
    env.store.jobs["legacy"]["enabled"] = False
    assert env.update(OWNER, _emoji_payload("legacy")).status == 200
    assert env.act(OWNER, "resume", "legacy").status == 200
    events = read_audit_events(10)  # newest first
    assert [(e["event"], e["reason"], e["path"]) for e in events] == [
        ("would_deny", "cron_run_ungoverned", "/api/crons/resume"),
        ("would_deny", "cron_run_ungoverned", "/api/crons/update"),
    ]
    assert env.store.jobs["legacy"]["owner_email"] == ""
    assert env.store.jobs["legacy"]["enabled"] is True


@pytest.fixture
def real_store(tmp_path, monkeypatch, inject_policy):
    """The engine's own cron.jobs in a temporary store, driven through the
    real handle_post dispatcher on the default profile."""
    import api.governance.enforce as enforce
    import api.profiles as profiles
    import api.routes as routes

    jobs = pytest.importorskip("cron.jobs")
    if not routes._callable_accepts_kwarg(jobs.create_job, "owner_email"):
        pytest.skip("engine create_job predates owner_email")
    monkeypatch.setattr(jobs, "CRON_DIR", tmp_path / "cron")
    monkeypatch.setattr(jobs, "JOBS_FILE", tmp_path / "cron" / "jobs.json")
    monkeypatch.setattr(jobs, "OUTPUT_DIR", tmp_path / "cron" / "output")
    monkeypatch.setattr(jobs, "_compute_provider_model_snapshots", lambda **k: (None, None), raising=False)
    try:
        import cron.notepad as notepad
        monkeypatch.setattr(notepad, "NOTEPAD_FILE", tmp_path / "cron" / "notepad.db")
    except ImportError:
        pass
    monkeypatch.setattr(routes, "_get_active_profile_name", lambda: "default")
    monkeypatch.setattr(routes, "_check_csrf", lambda _handler: True)
    monkeypatch.setattr(
        routes, "_guard_request_session_visibility",
        lambda handler, parsed, body=None, method="POST": True,
    )
    monkeypatch.setattr(routes, "_ensure_agent_cron_import_path", lambda: None)
    monkeypatch.setattr(profiles, "cron_profile_context", nullcontext)
    inject_policy(POLICY)

    def post(email, path, body):
        identity = _identity(email)
        monkeypatch.setattr(enforce, "_request_identity", lambda handler: identity)
        monkeypatch.setattr(routes, "read_body", lambda _handler: copy.deepcopy(body))
        handler = _JSONHandler()
        assert routes.handle_post(handler, SimpleNamespace(path=path, query="")) is not False
        return handler

    return SimpleNamespace(jobs=jobs, post=post)


@pytest.mark.parametrize("identity_fixed,governed_runs,expected", [
    pytest.param(False, False, "stamped", id="live-engine"),
    pytest.param(True, True, "unstamped", id="identity-fixed-engine"),
    pytest.param(True, False, "refused", id="neither"),
])
def test_real_engine_store_and_an_ownerless_task(real_store, monkeypatch, identity_fixed,
                                                 governed_runs, expected):
    """Against the engine's own cron.jobs: the stamp goes in with the change
    in one update_job call, and before resume_job enables the task."""
    jobs, post = real_store.jobs, real_store.post
    scheduler = pytest.importorskip("cron.scheduler")
    monkeypatch.setattr(jobs, "_IMMUTABLE_JOB_FIELDS",
                        E0_IMMUTABLE_JOB_FIELDS if identity_fixed else frozenset({"id"}))
    if governed_runs:
        monkeypatch.setattr(scheduler, "run_job_governed", lambda job, **kwargs: None, raising=False)
    else:
        monkeypatch.delattr(scheduler, "run_job_governed", raising=False)
    legacy = {"platform": "webui", "chat_id": "sess-legacy", "user_id": OWNER}
    edited = jobs.create_job(prompt="ping", schedule="every 1h", name="Edited", origin=legacy)
    resumed = jobs.create_job(prompt="ping", schedule="every 1h", name="Resumed", origin=legacy)
    assert str(edited.get("owner_email") or "") == str(resumed.get("owner_email") or "") == ""
    assert post(OWNER, "/api/crons/pause", {"job_id": resumed["id"]}).status == 200
    assert jobs.get_job(resumed["id"])["enabled"] is False
    before = jobs.JOBS_FILE.read_bytes()

    update = post(OWNER, "/api/crons/update", {"job_id": edited["id"], "prompt": "do anything"})
    resume = post(OWNER, "/api/crons/resume", {"job_id": resumed["id"]})
    if expected == "refused":
        assert (update.status, resume.status) == (403, 403), (update.body, resume.body)
        assert jobs.JOBS_FILE.read_bytes() == before
        return
    assert (update.status, resume.status) == (200, 200), (update.body, resume.body)
    owner = OWNER if expected == "stamped" else ""
    stored = jobs.get_job(edited["id"])
    assert stored["prompt"] == "do anything"
    assert str(stored.get("owner_email") or "") == owner
    stored = jobs.get_job(resumed["id"])
    assert stored["enabled"] is True
    assert str(stored.get("owner_email") or "") == owner


# ── A job name must not slip past the owner guard ───────────────────────────
# The engine's pause_job, resume_job and remove_job resolve a job NAME as well
# as an id (resolve_job_ref), while both guards look the job up by id. Before
# this fix a cron:write user who sent the name of someone else's task passed
# both guards (no job has that id, so "the handler answers 404"), and the
# engine then paused, resumed or deleted it; the pause reply even carried the
# whole job record. The routes now act on ids only, like run and update.

NON_OWNERS = [
    pytest.param(SHAREE, "default", id="sharee"),
    pytest.param(OTHER, "alpha", id="profile-grant"),
    pytest.param(OTHER, "default", id="out-of-scope"),
]


@pytest.mark.parametrize("ref", ["Owner task", "owner task"])
@pytest.mark.parametrize("email,active", NON_OWNERS)
@pytest.mark.parametrize("action", JOB_ACTIONS)
def test_a_job_name_cannot_bypass_the_owner_guard(env, action, email, active, ref):
    env.active = active
    before = copy.deepcopy(env.store.jobs)
    handler = env.act(email, action, ref)
    assert handler.status in (403, 404), handler.body
    assert env.store.actions == []
    assert env.store.jobs == before
    assert "summarise the inbox" not in json.dumps(handler.body)


@pytest.mark.parametrize("action", JOB_ACTIONS)
def test_the_job_routes_act_on_ids_only(env, action):
    """The Tasks panel always sends the id; a name is not found, for anyone."""
    for email in (OWNER, ADMIN, BOOTSTRAP):
        handler = env.act(email, action, "Owner task")
        assert handler.status == 404, (email, handler.body)
    assert env.store.actions == []
    assert env.act(OWNER, action, "own").status == 200
    assert env.store.actions == [(action, "own")]


def test_real_engine_store_refuses_a_job_name_from_a_non_owner(tmp_path, monkeypatch, inject_policy):
    """Against the engine's own cron.jobs, whose pause_job, resume_job and
    remove_job also resolve names, through the real handle_post dispatcher:
    a sharee, a profile-grant holder and an out-of-scope colleague cannot
    reach the owner's task by its name, and the store does not change."""
    import api.governance.enforce as enforce
    import api.profiles as profiles
    import api.routes as routes

    jobs = pytest.importorskip("cron.jobs")
    if not routes._callable_accepts_kwarg(jobs.create_job, "owner_email"):
        pytest.skip("engine create_job predates owner_email")
    monkeypatch.setattr(jobs, "CRON_DIR", tmp_path / "cron")
    monkeypatch.setattr(jobs, "JOBS_FILE", tmp_path / "cron" / "jobs.json")
    monkeypatch.setattr(jobs, "OUTPUT_DIR", tmp_path / "cron" / "output")
    monkeypatch.setattr(jobs, "_compute_provider_model_snapshots", lambda **k: (None, None), raising=False)
    try:
        import cron.notepad as notepad
        monkeypatch.setattr(notepad, "NOTEPAD_FILE", tmp_path / "cron" / "notepad.db")
    except ImportError:
        pass
    active = {"name": "default"}
    monkeypatch.setattr(routes, "_get_active_profile_name", lambda: active["name"])
    monkeypatch.setattr(routes, "_check_csrf", lambda _handler: True)
    monkeypatch.setattr(
        routes, "_guard_request_session_visibility",
        lambda handler, parsed, body=None, method="POST": True,
    )
    monkeypatch.setattr(routes, "_ensure_agent_cron_import_path", lambda: None)
    monkeypatch.setattr(profiles, "cron_profile_context", nullcontext)
    inject_policy(POLICY)

    def _post(email, path, body):
        identity = _identity(email)
        monkeypatch.setattr(enforce, "_request_identity", lambda handler: identity)
        monkeypatch.setattr(routes, "read_body", lambda _handler: copy.deepcopy(body))
        handler = _JSONHandler()
        assert routes.handle_post(handler, SimpleNamespace(path=path, query="")) is not False
        return handler

    handler = _post(OWNER, "/api/crons/create", _form_create_payload(
        name="Owner private task", prompt="owner secret prompt",
        model=None, provider=None, skills=[]))
    assert handler.status == 200, handler.body
    job_id = handler.body["job"]["id"]
    assert _post(OWNER, "/api/crons/update", _share_payload(job_id, [SHAREE])).status == 200
    assert jobs.get_job(job_id)["shared_with"] == [SHAREE]

    before = jobs.JOBS_FILE.read_bytes()
    for email, profile in ((SHAREE, "default"), (OTHER, "alpha"), (OTHER, "default")):
        active["name"] = profile
        for action in ("pause", "resume", "delete"):
            for ref in ("Owner private task", "owner private task"):
                handler = _post(email, f"/api/crons/{action}", {"job_id": ref})
                assert handler.status in (403, 404), (email, profile, action, ref, handler.body)
                assert "owner secret prompt" not in json.dumps(handler.body)
                assert jobs.JOBS_FILE.read_bytes() == before, (email, profile, action, ref)
            # The id they could always send is refused as well.
            handler = _post(email, f"/api/crons/{action}", {"job_id": job_id})
            assert handler.status == 403, (email, profile, action, handler.body)
    assert jobs.JOBS_FILE.read_bytes() == before

    active["name"] = "default"
    handler = _post(OWNER, "/api/crons/pause", {"job_id": job_id})
    assert handler.status == 200, handler.body
    assert jobs.get_job(job_id)["enabled"] is False
    handler = _post(OWNER, "/api/crons/delete", {"job_id": job_id})
    assert handler.status == 200, handler.body
    assert jobs.get_job(job_id) is None


# ── One reading of job_id for the guards and the handlers ──────────────────
# The guards in handle_post read ``str(body.get("job_id") or "")``, so 0 and
# False reached them as "no job" and passed, while the delete handler looked
# up str(0) == "0" and removed that task. Only a non-empty string names a job
# now, read once for both.

# What str() made of each value: a task with that id would have been reached.
_NON_STRING_IDS = [0, False, True, 1, 1.5, ["own"], {"id": "own"}, None, ""]


def _plant_tasks_named_like(env, values):
    for value in values:
        key = str(value)
        env.store.jobs[key] = dict(_stored_jobs()["own"], id=key, name=f"task {key}")


@pytest.mark.parametrize("raw", _NON_STRING_IDS)
@pytest.mark.parametrize("action", JOB_ACTIONS)
def test_a_job_id_that_is_not_a_non_empty_string_is_refused(run_env, action, raw):
    env = run_env
    _plant_tasks_named_like(env, _NON_STRING_IDS)
    before = copy.deepcopy(env.store.jobs)
    for email in (OTHER, SHAREE, OWNER, ADMIN):
        handler = env.act(email, action, raw)
        assert handler.status == 400, (email, handler.body)
    assert env.store.actions == [] and env.runs == []
    assert env.store.jobs == before


@pytest.mark.parametrize("raw", _NON_STRING_IDS)
def test_update_job_id_must_be_a_non_empty_string(env, raw):
    _plant_tasks_named_like(env, _NON_STRING_IDS)
    for email in (OTHER, OWNER, ADMIN):
        handler = env.update(email, {"job_id": raw, "emoji": "x"})
        assert handler.status == 400, (email, handler.body)
    assert env.store.updates == []


@pytest.mark.parametrize("action", JOB_ACTIONS)
def test_guards_and_handler_look_up_the_same_id(run_env, monkeypatch, action):
    env = run_env
    looked_up = []
    store_get_job = sys.modules["cron.jobs"].get_job

    def _get_job(job_id):
        looked_up.append(job_id)
        return store_get_job(job_id)

    monkeypatch.setattr(sys.modules["cron.jobs"], "get_job", _get_job)
    assert env.act(OWNER, action, "own").status == 200
    assert looked_up and set(looked_up) == {"own"}, looked_up
    assert all(type(job_id) is str for job_id in looked_up)
    acted = env.store.actions or [("run", run.job["id"]) for run in env.runs]
    assert acted == [(action, "own")]


# ── Value checks ────────────────────────────────────────────────────────────

# Every allowlisted field has one shape, for cron admins too: the text fields
# (what saveCronForm and the popovers send) are strings, model, provider and
# profile a string or null (the form clears a pin with null), and
# toast_notifications a boolean. Before this check any JSON value reached
# update_job: an owner could store a list as their task's name, after which
# the engine's resolve_job_ref raised on every lookup by name in that store,
# so pausing, resuming or removing anyone's task by name there failed.
_BAD_VALUE_SHAPES = [
    ("name", ["x"]), ("name", {"a": 1}), ("name", 1), ("name", None),
    ("prompt", ["summarise"]), ("prompt", {"a": 1}),
    ("schedule", ["every 1h"]), ("schedule", {"kind": "interval", "minutes": 0}),
    ("deliver", ["telegram:1"]), ("deliver", {"telegram": "1"}), ("deliver", None),
    ("diagram", {"a": 1}), ("emoji", ["📬"]), ("category", {"a": 1}),
    ("model", ["gpt-allowed"]), ("model", 1), ("provider", {"a": 1}), ("profile", ["alpha"]),
    ("toast_notifications", "no"), ("toast_notifications", 0), ("toast_notifications", None),
]


@pytest.mark.parametrize("field,value", _BAD_VALUE_SHAPES)
def test_value_shapes_are_checked_for_everyone(env, field, value):
    for email in (OWNER, ADMIN, BOOTSTRAP):
        handler = env.update(email, {"job_id": "own", field: value})
        assert handler.status == 400, (email, handler.body)
        assert field in handler.body["error"], (email, handler.body)
        handler = env.create(email, _form_create_payload(**{field: value}))
        assert handler.status == 400, (email, handler.body)
        assert field in handler.body["error"], (email, handler.body)
    assert env.store.updates == [] and env.store.creates == []
    assert env.store.jobs == _stored_jobs()


def test_the_panels_value_shapes_pass(env):
    """What the Tasks panel sends, including a cleared model pin (null) and
    an unticked toast box."""
    handler = env.update(OWNER, _form_update_payload(
        "own", model=None, provider=None, toast_notifications=False, diagram="", emoji="", category=""))
    assert handler.status == 200, handler.body
    handler = env.create(OWNER, _form_create_payload(model=None, provider=None, profile=None,
                                                     toast_notifications=False))
    assert handler.status == 200, handler.body


def test_real_engine_name_lookups_survive_a_refused_name(real_store):
    jobs, post = real_store.jobs, real_store.post
    handler = post(OWNER, "/api/crons/create", _form_create_payload(
        name="Owner task", model=None, provider=None, skills=[]))
    assert handler.status == 200, handler.body
    job_id = handler.body["job"]["id"]
    before = jobs.JOBS_FILE.read_bytes()
    for body in ({"job_id": job_id, "name": ["x"]},
                 {"job_id": job_id, "schedule": {"kind": "interval", "minutes": 0}}):
        assert post(OWNER, "/api/crons/update", body).status == 400
    assert jobs.JOBS_FILE.read_bytes() == before
    assert jobs.resolve_job_ref("owner task")["id"] == job_id

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


def test_report_only_audits_a_model_outside_the_grants(env, inject_policy):
    inject_policy({**POLICY, "mode": "report_only"})
    handler = env.create(OWNER, _form_create_payload(model="gpt-forbidden", provider="openai"))
    assert handler.status == 200, handler.body
    events = read_audit_events(10)
    assert [e["event"] for e in events] == ["would_deny"]
    assert events[0]["reason"] == "cron_model"
    assert events[0]["path"] == "/api/crons/create"


def test_empty_deliver_on_update_is_local(env):
    """The engine reads an empty deliver as local (_normalize_deliver_value)."""
    handler = env.update(OWNER, _form_update_payload("own", deliver=""))
    assert handler.status == 200, handler.body
    handler = env.update(OWNER, _form_update_payload("own", deliver="  "))
    assert handler.status == 200, handler.body


# Skills: the scheduler injects every listed skill into the job's prompt
# (cron/scheduler.py _build_job_prompt calls skill_view directly, with no
# governance gate), so a skill its creator could not load in a chat would
# reach the agent, and its output the creator, through a scheduled task. The
# rule is the chat rule: the engine's own skill_view gates on the governance
# context a chat turn of the caller binds. That rule is stricter than the
# /api/skills listing guard, which treats "no skill grant" as "every skill".
SECRET_SKILL = "finance-secrets"
PLAIN = "plain@example.test"        # the skills toolset, no skill grant
TOOLLESS = "toolless@example.test"  # a skill grant, but no skill_view tool
SKILL_POLICY = {
    **POLICY,
    "roles": {
        **POLICY["roles"],
        "plain": {"grants": {k: v for k, v in WRITER_GRANTS.items() if k != "skills"}},
        "toolless": {"grants": {k: v for k, v in WRITER_GRANTS.items() if k != "tools"}},
    },
    "users": {
        **POLICY["users"],
        # Every skill but one: finance-secrets is denied outright.
        OWNER: {"roles": ["writer"],
                "grants": {"skills": {"view": ["*"]}},
                "deny": {"skills": {"view": [SECRET_SKILL], "load": [SECRET_SKILL]}}},
        # Only the role's google-workspace.
        OTHER: {"roles": ["writer"]},
        # May view every skill, but loading notion is denied.
        SHAREE: {"roles": ["writer"],
                 "grants": {"skills": {"view": ["*"]}},
                 "deny": {"skills": {"load": ["notion"]}}},
        PLAIN: {"roles": ["plain"]},
        TOOLLESS: {"roles": ["toolless"]},
    },
}


@pytest.fixture
def chat_rule():
    """The skill rule is the engine's own chat gate: skip without the engine."""
    pytest.importorskip("hermes_cli.dashboard_governance.tool_policy")
    pytest.importorskip("tools.registry")


@pytest.mark.parametrize("email,skills", [
    (OWNER, [SECRET_SKILL]),
    (OWNER, ["google-workspace", SECRET_SKILL]),
    (OWNER, ["Finance Secrets"]),            # the display form of the name
    (OWNER, [f"finance/{SECRET_SKILL}"]),     # a category path to the same skill
    (OTHER, ["notion"]),
    (SHAREE, ["notion"]),                    # viewable, but its load is denied
    (PLAIN, ["google-workspace"]),           # no skill grant: chat loads none
    (TOOLLESS, ["google-workspace"]),        # granted, but chat has no skill_view
])
def test_skill_outside_the_callers_grants_is_forbidden(env, inject_policy, chat_rule, email, skills):
    inject_policy(SKILL_POLICY)
    handler = env.create(email, _form_create_payload(skills=skills))
    assert handler.status == 403, handler.body
    assert handler.body["reason"] == "cron_skill"
    assert env.store.creates == []


def test_skill_within_the_callers_grants_is_allowed(env, inject_policy, chat_rule):
    inject_policy(SKILL_POLICY)
    for email in (OWNER, OTHER, SHAREE):
        handler = env.create(email, _form_create_payload(skills=["google-workspace"]))
        assert handler.status == 200, (email, handler.body)
    handler = env.create(OWNER, _form_create_payload(skills=["notion"]))
    assert handler.status == 200, handler.body
    for email in (OTHER, PLAIN, TOOLLESS):
        handler = env.create(email, _form_create_payload(skills=[]))
        assert handler.status == 200, (email, handler.body)
    handler = env.create(ADMIN, _form_create_payload(skills=[SECRET_SKILL]))
    assert handler.status == 200, handler.body
    assert env.store.creates[-1]["skills"] == [SECRET_SKILL]


def test_skill_rule_is_the_chat_gate(env, inject_policy, chat_rule, monkeypatch):
    """The decision comes from the engine's skill_view gates, on the context a
    chat turn of the caller binds, not from a copy of the rule."""
    import hermes_cli.dashboard_governance.tool_policy as tool_policy

    inject_policy(SKILL_POLICY)
    seen = []
    real = tool_policy.tool_arguments_allowed_for_context

    def _spy(ctx, tool_name, args):
        seen.append((ctx.subject.normalized_email, tool_name, args.get("name"), ctx.access.mode))
        return real(ctx, tool_name, args)

    monkeypatch.setattr(tool_policy, "tool_arguments_allowed_for_context", _spy)
    handler = env.create(OTHER, _form_create_payload(skills=["google-workspace"]))
    assert handler.status == 200, handler.body
    assert seen == [(OTHER, "skill_view", "google-workspace", "enforce")]


@pytest.mark.parametrize("skills", [SECRET_SKILL, [1], [["nested"]], {"name": SECRET_SKILL}, ""])
def test_skills_must_be_a_list_of_names(env, skills):
    for email in (OWNER, ADMIN):
        handler = env.create(email, _form_create_payload(skills=skills))
        assert handler.status == 400, (email, handler.body)
        handler = env.update(email, {"job_id": "own", "skills": skills})
        assert handler.status == 400, (email, handler.body)
    assert env.store.creates == [] and env.store.updates == []


def test_report_only_audits_a_skill_outside_the_grants(env, inject_policy, chat_rule):
    inject_policy({**SKILL_POLICY, "mode": "report_only"})
    handler = env.create(OWNER, _form_create_payload(skills=[SECRET_SKILL]))
    assert handler.status == 200, handler.body
    handler = env.update(OWNER, {"job_id": "own", "skills": [SECRET_SKILL]})
    assert handler.status == 200, handler.body
    events = read_audit_events(10)
    assert [e["event"] for e in events] == ["would_deny", "would_deny"]
    assert [e["reason"] for e in events] == ["cron_skill", "cron_skill"]
    assert sorted(e["path"] for e in events) == ["/api/crons/create", "/api/crons/update"]


def test_skill_check_fails_closed_without_the_engine_gate(env, inject_policy, monkeypatch):
    inject_policy(SKILL_POLICY)
    monkeypatch.setitem(sys.modules, "hermes_cli.dashboard_governance.tool_policy", None)
    handler = env.create(OTHER, _form_create_payload(skills=["google-workspace"]))
    assert handler.status == 403, handler.body
    assert handler.body["reason"] == "cron_skill"
    # No skills, nothing to check; admins are exempt.
    assert env.create(OTHER, _form_create_payload(skills=[])).status == 200
    assert env.create(ADMIN, _form_create_payload(skills=["google-workspace"])).status == 200


# Update takes skills too, under the same rule. Only a new name is checked:
# a skill already on the task stays when the owner saves it back.

def test_update_checks_new_skills_against_the_chat_rule(env, inject_policy, chat_rule):
    inject_policy(SKILL_POLICY)
    env.active = "alpha"  # a store OTHER and PLAIN may see
    handler = env.update(OTHER, {"job_id": "reowned", "skills": ["notion"]})
    assert handler.status == 403, handler.body
    assert handler.body["reason"] == "cron_skill"
    handler = env.update(PLAIN, {"job_id": "own", "skills": ["google-workspace"]})
    assert handler.status == 403  # ownership comes first
    assert handler.body["reason"] == "cron_owner"
    assert env.store.updates == []

    handler = env.update(OTHER, {"job_id": "reowned", "skills": ["google-workspace"]})
    assert handler.status == 200, handler.body
    assert env.store.jobs["reowned"]["skills"] == ["google-workspace"]
    handler = env.update(OTHER, {"job_id": "reowned", "skills": []})
    assert handler.status == 200, handler.body
    assert env.store.jobs["reowned"]["skills"] == []


def test_update_keeps_a_stored_skill_the_owner_may_not_load(env, inject_policy, chat_rule):
    inject_policy(SKILL_POLICY)
    env.active = "alpha"
    env.store.jobs["reowned"]["skills"] = ["notion"]  # set by a cron admin
    handler = env.update(OTHER, {"job_id": "reowned", "skills": ["notion", "google-workspace"]})
    assert handler.status == 200, handler.body
    handler = env.update(OTHER, {"job_id": "reowned", "skills": ["notion", SECRET_SKILL]})
    assert handler.status == 403
    assert "notion" not in handler.body["error"] and SECRET_SKILL in handler.body["error"]
    handler = env.update(ADMIN, {"job_id": "reowned", "skills": [SECRET_SKILL]})
    assert handler.status == 200, handler.body


def test_sharee_cannot_change_skills(env, inject_policy, chat_rule):
    inject_policy(SKILL_POLICY)
    handler = env.update(SHAREE, {"job_id": "own", "skills": ["google-workspace"]})
    assert handler.status == 403
    assert handler.body["reason"] == "cron_owner"
    assert env.store.updates == []


# ── Create stamps the owner ─────────────────────────────────────────────────

def test_create_stamps_owner_and_origin_from_the_identity(env):
    handler = env.create(OWNER, _form_create_payload())
    assert handler.status == 200, handler.body
    stamp = {"platform": "webui", "chat_id": None, "user_id": OWNER}
    # Both go in at creation: an engine with immutable identity fields refuses
    # them through update_job.
    assert env.store.creates[0]["owner_email"] == OWNER
    assert env.store.creates[0]["origin"] == stamp
    assert all("owner_email" not in u and "origin" not in u for _, u in env.store.updates)
    job = env.store.jobs["new1"]
    assert job["owner_email"] == OWNER
    assert job["origin"] == stamp


def test_create_stamps_the_owner_on_an_engine_without_the_owner_kwarg(env):
    env.install(_Store(owner_kwarg=False))
    handler = env.create(OWNER, _form_create_payload())
    assert handler.status == 200, handler.body
    assert "owner_email" not in env.store.creates[0]
    assert env.store.jobs["new1"]["owner_email"] == OWNER
    assert env.store.jobs["new1"]["origin"]["user_id"] == OWNER


def test_create_without_a_signed_in_email_stays_unstamped(env, inject_policy):
    inject_policy({"version": 1, "mode": "off", "default_effect": "deny"})
    handler = env.create(None, _form_create_payload())
    assert handler.status == 200, handler.body
    assert env.store.creates[0]["owner_email"] is None
    assert env.store.jobs["new1"]["origin"] is None


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


def test_real_engine_store_with_immutable_identity_fields(tmp_path, monkeypatch, inject_policy):
    """Against the engine's own cron.jobs, with owner_email, origin and
    created_at immutable in update_job (the E0 engine fix): a Tasks panel
    create still stamps both, the owner edits, a colleague cannot."""
    import api.governance.enforce as enforce
    import api.routes as routes

    jobs = pytest.importorskip("cron.jobs")
    if not routes._callable_accepts_kwarg(jobs.create_job, "owner_email"):
        pytest.skip("engine create_job predates owner_email")
    monkeypatch.setattr(jobs, "CRON_DIR", tmp_path / "cron")
    monkeypatch.setattr(jobs, "JOBS_FILE", tmp_path / "cron" / "jobs.json")
    monkeypatch.setattr(jobs, "OUTPUT_DIR", tmp_path / "cron" / "output")
    monkeypatch.setattr(jobs, "_compute_provider_model_snapshots", lambda **k: (None, None), raising=False)
    monkeypatch.setattr(jobs, "_IMMUTABLE_JOB_FIELDS",
                        frozenset({"id", "owner_email", "origin", "created_at"}))
    monkeypatch.setattr(routes, "_get_active_profile_name", lambda: "default")
    inject_policy(POLICY)

    def _as(email):
        identity = _identity(email)
        monkeypatch.setattr(enforce, "_request_identity", lambda handler: identity)
        return _JSONHandler()

    handler = _as(OWNER)
    routes._handle_cron_create(handler, _form_create_payload(model=None, provider=None, skills=[]))
    assert handler.status == 200, handler.body
    job_id = handler.body["job"]["id"]
    stored = jobs.get_job(job_id)
    assert stored["owner_email"] == OWNER
    assert stored["origin"] == {"platform": "webui", "chat_id": None, "user_id": OWNER}
    assert stored["emoji"] == "📬" and stored["category"] == "Finance"

    handler = _as(OWNER)
    routes._handle_cron_update(handler, _category_payload(job_id))
    assert handler.status == 200, handler.body

    before = jobs.JOBS_FILE.read_bytes()
    handler = _as(OTHER)
    routes._handle_cron_update(handler, _emoji_payload(job_id))
    assert handler.status == 403
    handler = _as(OWNER)
    routes._handle_cron_update(handler, {"job_id": job_id, "owner_email": ""})
    assert handler.status == 400
    assert jobs.JOBS_FILE.read_bytes() == before


# ── Run now runs governed ───────────────────────────────────────────────────
# POST /api/crons/run ran the job in a spawned child through
# cron.scheduler.run_job with no governance bound: the tool, skill, MCP and
# model gates were off for that run, so a job ran with more than its owner's
# rights, and an ownerless agent job ran unbound under enforce. The child now
# runs it through the engine's governed entry point (run_job_governed, from
# the engine identity fix) when the engine has one; the gate reads the policy
# of the store that holds the job. On an engine without it the child binds
# the owner's governance the way a chat turn binds its sender's, only a cron
# admin or the job's owner may start a run, and nobody but a cron admin runs a
# job with nothing bound.

RUN_REFUSAL = "Not run: this scheduled task has no owner."  # the fake engine's


def _ownerless_cli_task():
    return {
        "id": "cli",
        "name": "CLI task",
        "prompt": "ping",
        "schedule": {"kind": "interval", "minutes": 60},
        "deliver": "local",
        "owner_email": "",
        "origin": None,
    }


def _plan(run_as, *, unbound_allowed=False, store_home=None, profile="default"):
    return {
        "run_as": run_as,
        "unbound_allowed": unbound_allowed,
        "profile": profile,
        "store_home": str(store_home) if store_home is not None else None,
        "governance_policy": "",
    }


def _bound_email():
    """Who the engine's governance context names right now (None: unbound)."""
    try:
        from hermes_cli.dashboard_governance.context import current_governance_context
    except ImportError:
        return None
    ctx = current_governance_context()
    return None if ctx is None else ctx.subject.normalized_email


def _run_now_scheduler(monkeypatch, events, *, governed, outcome="ran"):
    """A cron.scheduler stand-in. With ``governed`` it has run_job_governed
    with the engine's result shape, and like the engine it looks run_job up on
    the module when a run starts."""
    import os

    scheduler = types.ModuleType("cron.scheduler")
    scheduler._KNOWN_DELIVERY_PLATFORMS = frozenset({"telegram", "slack"})

    def run_job(job, **kwargs):
        events.append(("run_job", job["id"], os.environ.get("HERMES_HOME"), _bound_email()))
        return True, "output", "final", None

    scheduler.run_job = run_job
    if governed:
        def run_job_governed(job, *, reason, record_refusal=True, **kwargs):
            events.append(("gate", job["id"], reason, record_refusal, os.environ.get("HERMES_HOME")))
            owner = str(job.get("owner_email") or "")
            if outcome == "refused":
                return SimpleNamespace(outcome="refused", success=False, output="", final_response="",
                                       error=RUN_REFUSAL, refusal=RUN_REFUSAL,
                                       refusal_recorded=record_refusal, owner_email=owner)
            if outcome == "failed":
                return SimpleNamespace(outcome="failed", success=False, output="", final_response="",
                                       error="ValueError: boom", refusal=None,
                                       refusal_recorded=False, owner_email=owner)
            success, output, final, error = scheduler.run_job(job, **kwargs)
            return SimpleNamespace(outcome="ran", success=success, output=output, final_response=final,
                                   error=error, refusal=None, refusal_recorded=False, owner_email=owner)

        scheduler.run_job_governed = run_job_governed
    monkeypatch.setitem(sys.modules, "cron.scheduler", scheduler)
    return scheduler


# Deciding on the request: who the run executes as, and who may start one.

def test_run_now_runs_as_the_owner(run_env):
    env = run_env
    assert env.act(OWNER, "run", "own").status == 200
    run = env.runs[0]
    assert run.profile_home == env.store_home
    assert run.run_plan["run_as"] == OWNER
    assert run.run_plan["unbound_allowed"] is False
    assert run.run_plan["store_home"] == str(env.store_home)
    assert run.run_plan["profile"] == "default"


def test_run_now_for_admins_and_legacy_creators(run_env):
    env = run_env
    env.store.jobs["cli"] = _ownerless_cli_task()
    assert env.act(ADMIN, "run", "own").status == 200     # owned: it runs as its owner
    assert env.act(ADMIN, "run", "cli").status == 200     # ownerless: an admin runs it unbound
    assert env.act(OWNER, "run", "legacy").status == 200  # before the owner stamp: its creator
    plans = [(run.run_plan["run_as"], run.run_plan["unbound_allowed"]) for run in env.runs]
    assert plans == [(OWNER, True), ("", True), (OWNER, False)]


@pytest.mark.parametrize("governed", [False, True], ids=["engine-without-entry", "governed-engine"])
def test_run_now_under_enforce_stays_with_the_owner_and_admins(run_env, monkeypatch, governed):
    env = run_env
    _engine_has_run_job_governed(monkeypatch, governed)
    handler = env.act(SHAREE, "run", "own")
    assert handler.status == 403 and handler.body["reason"] == "cron_owner"
    env.active = "alpha"
    handler = env.act(OTHER, "run", "own")
    assert handler.status == 403 and handler.body["reason"] == "cron_owner"
    assert env.runs == []
    assert env.act(OWNER, "run", "own").status == 200


def test_report_only_run_by_a_non_owner_is_refused_without_the_governed_entry(run_env, inject_policy, monkeypatch):
    """The WebUI cannot evaluate the engine's gate itself, so under report_only
    too only a cron admin or the owner may start a run on such an engine."""
    env = run_env
    inject_policy({**POLICY, "mode": "report_only"})
    _engine_has_run_job_governed(monkeypatch, present=False)
    env.store.jobs["cli"] = _ownerless_cli_task()
    for job_id in ("own", "cli"):
        handler = env.act(SHAREE, "run", job_id)
        assert handler.status == 403, (job_id, handler.body)
        assert handler.body["reason"] == "cron_run_ungoverned"
    assert env.runs == []
    assert env.act(OWNER, "run", "own").status == 200
    assert env.act(ADMIN, "run", "cli").status == 200


def test_report_only_run_by_a_non_owner_goes_to_the_governed_engine(run_env, inject_policy, monkeypatch):
    env = run_env
    inject_policy({**POLICY, "mode": "report_only"})
    _engine_has_run_job_governed(monkeypatch)
    handler = env.act(SHAREE, "run", "own")
    assert handler.status == 200, handler.body
    plan = env.runs[0].run_plan
    # The engine's gate runs it as the owner; were the child's engine to lack
    # the entry point after all, it binds the owner and never runs unbound.
    assert (plan["run_as"], plan["unbound_allowed"]) == (OWNER, False)
    assert [e["reason"] for e in read_audit_events(10)] == ["cron_owner"]


def test_governance_off_keeps_run_now(run_env, inject_policy):
    env = run_env
    inject_policy({"version": 1, "mode": "off", "default_effect": "deny"})
    assert env.act(None, "run", "own").status == 200
    assert env.runs[0].run_plan["unbound_allowed"] is True


# Running in the child: _cron_job_subprocess_main, driven in-process.

class _ResultQueue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


@pytest.fixture
def child(env, monkeypatch, tmp_path):
    import api.governance.agent_context as agent_context

    events = []
    homes = SimpleNamespace(store=tmp_path / "store", execution=tmp_path / "exec")
    homes.store.mkdir()
    homes.execution.mkdir()
    env.store.jobs["cli"] = _ownerless_cli_task()

    def _bind(identity, **kwargs):
        events.append(("bind", identity, kwargs.get("active_profile"), kwargs.get("session_id")))
        return ("token", identity)

    def _reset(token):
        events.append(("reset", token))

    monkeypatch.setattr(agent_context, "bind_governed_agent_turn", _bind)
    monkeypatch.setattr(agent_context, "reset_governed_agent_turn", _reset)

    def engine(governed, outcome="ran"):
        return _run_now_scheduler(monkeypatch, events, governed=governed, outcome=outcome)

    def run(job_id, plan, execution_home=homes.execution):
        import api.routes as routes

        queue = _ResultQueue()
        routes._cron_job_subprocess_main(copy.deepcopy(env.store.jobs[job_id]), execution_home, queue, plan)
        assert len(queue.items) == 1, queue.items
        return queue.items[0]

    return SimpleNamespace(events=events, homes=homes, engine=engine, run=run)


def test_child_runs_through_the_governed_entry_point(child):
    child.engine(governed=True)
    result = child.run("own", _plan(OWNER, store_home=child.homes.execution))
    assert result == ("ok", (True, "output", "final", None))
    assert [e[0] for e in child.events] == ["gate", "run_job"]
    _, job_id, reason, record_refusal, _home = child.events[0]
    assert (job_id, reason, record_refusal) == ("own", "manual", True)


def test_child_gate_reads_the_store_that_holds_the_job(child):
    child.engine(governed=True)
    assert child.run("own", _plan(OWNER, store_home=child.homes.store))[0] == "ok"
    gate, run = child.events
    assert gate[4] == str(child.homes.store)
    assert run[2] == str(child.homes.execution)
    assert sys.modules["cron.scheduler"].run_job.__name__ == "run_job"  # restored


def test_child_reports_a_governed_refusal_without_running(child):
    child.engine(governed=True, outcome="refused")
    result = child.run("cli", _plan("", unbound_allowed=True, store_home=child.homes.store))
    assert result == ("refused", RUN_REFUSAL, True)
    assert [e[0] for e in child.events] == ["gate"]


def test_child_reports_a_failed_governed_run_as_an_error(child):
    child.engine(governed=True, outcome="failed")
    status, message, _traceback = child.run("own", _plan(OWNER, store_home=child.homes.store))
    assert (status, message) == ("error", "ValueError: boom")


def test_child_without_a_plan_leaves_recording_to_the_parent(child):
    child.engine(governed=True, outcome="refused")
    assert child.run("cli", None) == ("refused", RUN_REFUSAL, False)
    gate = child.events[0]
    assert gate[3] is False and gate[4] == str(child.homes.execution)


def test_child_on_an_engine_without_the_entry_point_binds_the_owner(child):
    child.engine(governed=False)
    result = child.run("own", _plan(OWNER, store_home=child.homes.store))
    assert result == ("ok", (True, "output", "final", None))
    assert [e[0] for e in child.events] == ["bind", "run_job", "reset"]
    assert child.events[0][1:] == (OWNER, "default", "own")
    assert child.events[1][2] == str(child.homes.execution)


def test_child_never_runs_unbound_for_a_non_admin(child):
    child.engine(governed=False)
    status, refusal, recorded = child.run("cli", _plan("", store_home=child.homes.store))
    assert status == "refused" and recorded is False
    assert "owner" in refusal
    assert child.events == []


def test_child_runs_an_ownerless_job_unbound_for_a_cron_admin(child):
    child.engine(governed=False)
    result = child.run("cli", _plan("", unbound_allowed=True, store_home=child.homes.store))
    assert result[0] == "ok"
    assert [e[0] for e in child.events] == ["run_job"]


def test_child_refuses_when_the_owners_governance_cannot_be_bound(child, monkeypatch):
    import api.governance.agent_context as agent_context

    child.engine(governed=False)

    def _fail(identity, **kwargs):
        raise agent_context.GovernanceBindingError()

    monkeypatch.setattr(agent_context, "bind_governed_agent_turn", _fail)
    status, refusal, _recorded = child.run("own", _plan(OWNER, store_home=child.homes.store))
    assert status == "refused"
    assert "governance context unavailable" in refusal
    assert child.events == []


def test_child_refuses_when_the_policy_cannot_be_read(child):
    child.engine(governed=False)

    def _unreadable():
        raise OSError("policy unreadable")

    loader.set_policy_loader(_unreadable)
    status, _refusal, _recorded = child.run("own", _plan(OWNER, store_home=child.homes.store))
    assert status == "refused"
    assert child.events == []


def test_child_without_a_plan_binds_the_owner_like_the_scheduler(child):
    child.engine(governed=False)
    assert child.run("own", None)[0] == "ok"
    assert child.run("cli", None)[0] == "ok"
    assert [e[0] for e in child.events] == ["bind", "run_job", "reset", "run_job"]


def test_child_binds_the_owners_real_governance(child, monkeypatch):
    """With the engine's own context module the run sees the owner's grants."""
    pytest.importorskip("hermes_cli.dashboard_governance.context")
    import api.governance.agent_context as agent_context

    monkeypatch.setattr(agent_context, "bind_governed_agent_turn", _REAL_BIND)
    monkeypatch.setattr(agent_context, "reset_governed_agent_turn", _REAL_RESET)
    child.engine(governed=False)
    assert child.run("own", _plan(OWNER, store_home=child.homes.store))[0] == "ok"
    assert child.events == [("run_job", "own", str(child.homes.execution), OWNER)]
    assert _bound_email() is None  # reset after the run


def test_child_pins_the_policy_file_the_request_decided_with(child, monkeypatch, tmp_path):
    import os

    child.engine(governed=False)
    seen = []
    monkeypatch.delenv("HERMES_WEBUI_GOVERNANCE_POLICY", raising=False)
    policy_file = tmp_path / "decided.yaml"

    def _bind(identity, **kwargs):
        seen.append(os.environ.get("HERMES_WEBUI_GOVERNANCE_POLICY"))
        return None

    import api.governance.agent_context as agent_context

    monkeypatch.setattr(agent_context, "bind_governed_agent_turn", _bind)
    plan = dict(_plan(OWNER, store_home=child.homes.store), governance_policy=str(policy_file))
    assert child.run("own", plan)[0] == "ok"
    assert seen == [str(policy_file)]
    assert "HERMES_WEBUI_GOVERNANCE_POLICY" not in os.environ


# The parent records a refusal where the job lives, and delivers nothing.

@pytest.fixture
def tracked(env, monkeypatch):
    import api.routes as routes

    jobs = sys.modules["cron.jobs"]
    calls = []
    monkeypatch.setattr(jobs, "save_job_output",
                        lambda job_id, output: calls.append(("save", job_id)), raising=False)
    monkeypatch.setattr(jobs, "mark_job_run",
                        lambda job_id, success, error=None, **kw: calls.append(("mark_run", job_id, success, error)),
                        raising=False)
    monkeypatch.setattr(jobs, "mark_job_refused",
                        lambda job_id, reason, *, consume_occurrence=True, **kw:
                        calls.append(("mark_refused", job_id, reason, consume_occurrence)) or True,
                        raising=False)
    monkeypatch.setattr(sys.modules["cron.scheduler"], "_deliver_result",
                        lambda job, content: calls.append(("deliver", job["id"])), raising=False)

    def refuse(recorded):
        def _subprocess(job, execution_profile_home, run_plan=None):
            raise routes._CronRunRefused(RUN_REFUSAL, recorded=recorded)
        monkeypatch.setattr(routes, "_run_cron_job_in_profile_subprocess", _subprocess)

    def run(job_id="own"):
        routes._mark_cron_running(job_id)
        routes._run_cron_tracked(copy.deepcopy(env.store.jobs[job_id]), None, None, None,
                                 run_plan=_plan(OWNER))
        assert routes._is_cron_running(job_id) == (False, 0.0)

    return SimpleNamespace(calls=calls, refuse=refuse, run=run, jobs=jobs)


def test_a_refused_run_is_recorded_as_a_refusal(tracked):
    tracked.refuse(recorded=False)
    tracked.run()
    assert tracked.calls == [("mark_refused", "own", RUN_REFUSAL, False)]


def test_a_refusal_the_engine_recorded_is_not_recorded_twice(tracked):
    tracked.refuse(recorded=True)
    tracked.run()
    assert tracked.calls == []


def _oneshot_task():
    return {
        "id": "once",
        "name": "One-shot task",
        "prompt": "ping",
        "schedule": {"kind": "once", "run_at": "2026-10-01T09:00:00+00:00"},
        "repeat": {"times": 1, "completed": 0},
        "enabled": True,
        "state": "scheduled",
        "next_run_at": "2026-10-01T09:00:00+00:00",
        "deliver": "local",
        "owner_email": OWNER,
        "origin": None,
    }


def test_an_engine_without_mark_job_refused_records_only_the_outcome(env, tracked, monkeypatch):
    """The live engine has no mark_job_refused, and its mark_job_run counts a
    run: a refused Run now of a one-shot used up its only run without running
    it. The fallback records the outcome and leaves the schedule alone, as
    mark_job_refused(consume_occurrence=False) does."""
    monkeypatch.delattr(tracked.jobs, "mark_job_refused")

    def _engine_mark_job_run(job_id, success, error=None, **kwargs):
        # The live engine's accounting (cron/jobs.py _mark_job_run_locked).
        tracked.calls.append(("mark_run", job_id, success, error))
        job = env.store.jobs[job_id]
        job["repeat"]["completed"] += 1
        job["last_status"] = "ok" if success else "error"
        job["last_error"] = None if success else error
        if job["repeat"]["completed"] >= job["repeat"]["times"]:
            job.update(enabled=False, state="completed", next_run_at=None)
        return True

    monkeypatch.setattr(tracked.jobs, "mark_job_run", _engine_mark_job_run)
    env.store.jobs["once"] = _oneshot_task()
    before = copy.deepcopy(env.store.jobs["once"])
    tracked.refuse(recorded=False)
    tracked.run("once")
    after = env.store.jobs["once"]
    for field in ("schedule", "repeat", "enabled", "state", "next_run_at"):
        assert after[field] == before[field], field
    assert (after["last_status"], after["last_error"]) == ("blocked_config", RUN_REFUSAL)
    assert after["failure_streak"] == 1
    assert tracked.calls == []  # no run counted, no output, no delivery


def test_real_engine_fallback_keeps_a_refused_one_shot_scheduled(tmp_path, monkeypatch):
    """The same against the engine's own cron.jobs, with mark_job_refused
    taken away when the engine has it (the live engine does not)."""
    from datetime import datetime, timedelta, timezone

    import api.routes as routes

    jobs = pytest.importorskip("cron.jobs")
    if not routes._callable_accepts_kwarg(jobs.create_job, "owner_email"):
        pytest.skip("engine create_job predates owner_email")
    monkeypatch.setattr(jobs, "CRON_DIR", tmp_path / "cron")
    monkeypatch.setattr(jobs, "JOBS_FILE", tmp_path / "cron" / "jobs.json")
    monkeypatch.setattr(jobs, "OUTPUT_DIR", tmp_path / "cron" / "output")
    monkeypatch.setattr(jobs, "_compute_provider_model_snapshots", lambda **k: (None, None), raising=False)
    monkeypatch.delattr(jobs, "mark_job_refused", raising=False)
    run_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    job = jobs.create_job(prompt="ping", schedule=run_at, name="One-shot task", owner_email=OWNER)
    before = jobs.get_job(job["id"])
    assert before["enabled"] is True and before["next_run_at"]

    routes._record_cron_run_refusal(job["id"], RUN_REFUSAL)

    after = jobs.get_job(job["id"])
    for field in ("schedule", "repeat", "enabled", "state", "next_run_at", "last_run_at"):
        assert after.get(field) == before.get(field), field
    assert (after["last_status"], after["last_error"]) == ("blocked_config", RUN_REFUSAL)


# End to end: the handler, the worker thread, the child (run inline) and the
# bookkeeping, on both engine shapes.

class _InlineQueue(list):
    def put(self, item):
        self.append(item)

    def get(self, timeout=None):
        return self.pop(0)

    def close(self):
        pass

    def join_thread(self):
        pass


class _InlineContext:
    def Queue(self, maxsize=0):
        return _InlineQueue()

    def Process(self, target, args=()):
        return SimpleNamespace(start=lambda: target(*args), join=lambda timeout=None: None,
                               is_alive=lambda: False, terminate=lambda: None, exitcode=0)


@pytest.mark.parametrize("governed", [True, False], ids=["governed-engine", "engine-without-entry"])
@pytest.mark.parametrize("outcome", ["ran", "refused"])
def test_run_now_end_to_end(env, tracked, child, monkeypatch, governed, outcome):
    import multiprocessing
    import time

    import api.profiles as profiles
    import api.routes as routes

    monkeypatch.setattr(routes, "_handle_cron_run", _REAL_HANDLE_CRON_RUN)
    monkeypatch.setattr(profiles, "get_active_hermes_home", lambda: child.homes.store)
    monkeypatch.setattr(multiprocessing, "get_context", lambda method: _InlineContext())
    scheduler = child.engine(governed=governed, outcome=outcome)
    monkeypatch.setattr(scheduler, "_deliver_result",
                        lambda job, content: tracked.calls.append(("deliver", job["id"])), raising=False)
    if not governed and outcome == "refused":
        import api.governance.agent_context as agent_context

        def _unbindable(identity, **kwargs):
            child.events.append(("bind", identity, kwargs.get("active_profile"), kwargs.get("session_id")))
            raise agent_context.GovernanceBindingError()

        monkeypatch.setattr(agent_context, "bind_governed_agent_turn", _unbindable)

    handler = env.act(OWNER, "run", "own")
    assert handler.status == 200, handler.body
    deadline = time.monotonic() + 5
    while routes._is_cron_running("own")[0] and time.monotonic() < deadline:
        time.sleep(0.01)
    assert routes._is_cron_running("own") == (False, 0.0)

    kinds = [e[0] for e in child.events]
    if governed:
        assert kinds[0] == "gate" and child.events[0][4] == str(child.homes.store)
    else:
        assert kinds[0] == "bind" and child.events[0][1] == OWNER
    if outcome == "ran":
        assert "run_job" in kinds
        assert tracked.calls == [("save", "own"), ("deliver", "own"), ("mark_run", "own", True, None)]
    elif governed:
        assert "run_job" not in kinds
        assert tracked.calls == []  # recorded by the engine in the job's own store
    else:
        assert "run_job" not in kinds
        # Recorded by the WebUI in the job's store, as a refusal: no output,
        # no delivery.
        assert len(tracked.calls) == 1
        kind, job_id, refusal, consume_occurrence = tracked.calls[0]
        assert (kind, job_id, consume_occurrence) == ("mark_refused", "own", False)
        assert refusal.startswith("Not run: ")


# ── The policy the request decided with, inside the profile swap ────────────
# cron_profile_context points HERMES_HOME at the active profile's home, and
# without HERMES_WEBUI_GOVERNANCE_POLICY the loader reads the policy file under
# HERMES_HOME. For a named profile without its own file that read governance
# off, which made every caller a cron admin in the checks of create, update
# and Run now: a colleague could rewrite someone's task into a no_agent script,
# and a Run now was planned (and, on an engine without run_job_governed, run)
# unbound. The routes now keep the policy file the request was admitted with.

def _root_policy_file(monkeypatch):
    """The policy as a real file in the root HERMES_HOME, read by the real
    loader with HERMES_WEBUI_GOVERNANCE_POLICY unset (the upstream default),
    and a named profile ``alpha`` without a policy file of its own."""
    import os

    import yaml

    root = Path(os.environ["HERMES_HOME"])
    policy_file = root / "dashboard-governance.yaml"
    policy_file.write_text(yaml.safe_dump(POLICY), encoding="utf-8")
    alpha = root / "profiles" / "alpha"
    (alpha / "cron").mkdir(parents=True)
    monkeypatch.delenv("HERMES_WEBUI_GOVERNANCE_POLICY", raising=False)
    loader.set_policy_loader(None)
    assert loader.get_policy().mode == "enforce"
    return policy_file, alpha


def _swap_to(env, monkeypatch, home):
    import api.profiles as profiles

    env.active = "alpha"
    monkeypatch.setattr(profiles, "get_active_hermes_home", lambda: home)
    monkeypatch.setattr(profiles, "cron_profile_context", _REAL_CRON_PROFILE_CONTEXT)


def test_update_on_a_named_profile_keeps_the_request_policy(env, monkeypatch):
    import os

    _policy_file, alpha = _root_policy_file(monkeypatch)
    _swap_to(env, monkeypatch, alpha)
    before = copy.deepcopy(env.store.jobs["own"])
    handler = env.update(OTHER, {"job_id": "own", "prompt": "exfiltrate", "script": "x.py", "no_agent": True})
    assert handler.status == 403, handler.body
    assert handler.body["reason"] == "cron_owner"
    handler = env.update(OWNER, {"job_id": "own", "script": "x.py", "no_agent": True})
    assert handler.status == 403, handler.body
    assert handler.body["reason"] == "cron_admin_field"
    assert env.store.jobs["own"] == before and env.store.updates == []
    assert "HERMES_WEBUI_GOVERNANCE_POLICY" not in os.environ
    # The owner's own edit still goes through.
    assert env.update(OWNER, _category_payload("own")).status == 200


def test_resume_on_a_named_profile_keeps_the_request_policy(env, monkeypatch):
    """Resume decides whether the caller is a cron admin (the ownerless task
    stamp) inside the swap, so it keeps the request's policy too."""
    import os

    _policy_file, alpha = _root_policy_file(monkeypatch)
    _swap_to(env, monkeypatch, alpha)
    env.store.jobs["legacy"]["enabled"] = False
    handler = env.act(OWNER, "resume", "legacy")
    assert handler.status == 200, handler.body
    assert env.store.jobs["legacy"]["owner_email"] == OWNER
    assert "HERMES_WEBUI_GOVERNANCE_POLICY" not in os.environ


def test_create_on_a_named_profile_keeps_the_request_policy(env, monkeypatch):
    _policy_file, alpha = _root_policy_file(monkeypatch)
    _swap_to(env, monkeypatch, alpha)
    handler = env.create(OWNER, _form_create_payload(script="x.py", no_agent=True))
    assert handler.status == 403, handler.body
    assert handler.body["reason"] == "cron_admin_field"
    assert env.store.creates == []


def test_run_now_on_a_named_profile_is_planned_with_the_request_policy(run_env, monkeypatch):
    import os

    policy_file, alpha = _root_policy_file(monkeypatch)
    _swap_to(run_env, monkeypatch, alpha)
    handler = run_env.act(OWNER, "run", "own")
    assert handler.status == 200, handler.body
    plan = run_env.runs[-1].run_plan
    assert plan["unbound_allowed"] is False
    assert plan["run_as"] == OWNER
    assert plan["governance_policy"] == str(policy_file)
    assert "HERMES_WEBUI_GOVERNANCE_POLICY" not in os.environ


def test_a_deployment_pinned_policy_file_is_kept(env, monkeypatch, tmp_path):
    """HQ and the stack set HERMES_WEBUI_GOVERNANCE_POLICY: the routes use it
    and leave it as it was."""
    import os

    import yaml

    _root_policy_file(monkeypatch)
    pinned = tmp_path / "pinned" / "governance.yaml"
    pinned.parent.mkdir()
    pinned.write_text(yaml.safe_dump({**POLICY, "mode": "report_only"}), encoding="utf-8")
    monkeypatch.setenv("HERMES_WEBUI_GOVERNANCE_POLICY", str(pinned))
    _swap_to(env, monkeypatch, tmp_path / "profiles" / "alpha")
    handler = env.update(OTHER, _emoji_payload("own"))
    # The pinned file says report_only (allowed); the root file says enforce.
    assert handler.status == 200, handler.body
    assert os.environ["HERMES_WEBUI_GOVERNANCE_POLICY"] == str(pinned)
