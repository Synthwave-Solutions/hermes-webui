"""Cron notify backend (plan 3.1, package W1).

``api/cron_notifications.py`` fills the Wave 0 seams in api/routes.py:

* ``GET /api/crons`` jobs carry ``notify`` (resolved), ``notify_source``,
  ``my_notify``, ``managed_by`` and ``support_notified``.
* ``GET /api/crons/recent`` completions carry ``toast``, ``badge``,
  ``desktop`` and ``silent`` per the plan 3.1 table, the AND of the job level
  and the viewer's own level; ``delivery_status`` may be ``muted``. Silent
  runs no longer notify anyone, legacy jobs otherwise behave as before.
* ``notify`` on create and update is validated; ``off`` is cron admin only
  (set and lifted), and the toast mirror is written for older clients.
* "Run now" passes the trigger and actor to engines that take them, mutes
  delivery per the job's level, and records a muted or silent run: through
  ``mark_job_run(delivery_outcome=)`` when the engine has it, otherwise in the
  WebUI delivery bridge ledger.

The policy module is the engine's ``cron/notify_policy.py`` when the
configured agent directory has it (an integration run against the engine
branch), otherwise the pinned fallback copy; both are byte identical.
"""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import sys
import types
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from api import _notify_policy_fallback as fallback_policy
from api.governance import loader
from api.governance.loader import parse_governance_policy

ADMIN = "cronadmin@example.test"
OWNER = "owner@example.test"
SHAREE = "sharee@example.test"
OTHER = "other@example.test"
BOOTSTRAP = "boot@example.test"

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
        "writer": {
            "grants": {
                "permissions": ["cron:read", "cron:write", "cron:run"],
                "profiles": ["alpha"],
                "routes": ["/api/crons", "/api/crons/*"],
            },
        },
    },
    "users": {
        ADMIN: {"roles": ["cron_admin"]},
        OWNER: {"roles": ["writer"]},
        SHAREE: {"roles": ["writer"]},
        OTHER: {"roles": ["writer"]},
    },
}


def _identity(email):
    return {"email": email, "groups": [], "claims_subset": {}, "method": "oidc"}


class _Handler:
    """Records one JSON response the way BaseHTTPRequestHandler sends it."""

    def __init__(self, email=None, path="/api/crons/update"):
        self.email = email
        self.path = path
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
        raw = self.wfile.getvalue()
        return json.loads(raw.decode("utf-8")) if raw else None


def _now_iso(offset_secs=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_secs)).isoformat()


def _engine_policy_module():
    """The engine's notify policy when the agent dir has it, else None."""
    from api import config

    agent_dir = getattr(config, "_AGENT_DIR", None)
    path = Path(agent_dir) / "cron" / "notify_policy.py" if agent_dir else None
    if path is None or not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("cron.notify_policy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ENGINE_POLICY = _engine_policy_module()


@pytest.fixture
def notify_env(monkeypatch, tmp_path):
    """Isolated WebUI state, a fake cron package and an injected policy."""
    import api.config as config
    import api.cron_webui_delivery as cwd
    import api.governance.enforce as enforce
    from api import ownership

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    home = tmp_path / "home"
    (home / "cron" / "output").mkdir(parents=True)
    monkeypatch.setattr(config, "STATE_DIR", state_dir)
    monkeypatch.setattr(cwd, "_MEMORY_WATERMARKS", {})
    for name in ("SP_OPERATIONAL_TELEMETRY", "HERMES_WEBUI_CRON_NOTIFY_ADMIN_OVERRIDE"):
        monkeypatch.delenv(name, raising=False)

    cron_pkg = types.ModuleType("cron")
    cron_pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "cron", cron_pkg)
    jobs_mod = types.ModuleType("cron.jobs")
    jobs_mod.OUTPUT_DIR = home / "cron" / "output"
    monkeypatch.setitem(sys.modules, "cron.jobs", jobs_mod)
    monkeypatch.setitem(sys.modules, "cron.scheduler", types.ModuleType("cron.scheduler"))
    if _ENGINE_POLICY is not None:
        monkeypatch.setitem(sys.modules, "cron.notify_policy", _ENGINE_POLICY)
    else:
        monkeypatch.delitem(sys.modules, "cron.notify_policy", raising=False)

    loader.set_policy_loader(lambda: parse_governance_policy(POLICY))
    monkeypatch.setattr(enforce, "_request_identity",
                        lambda handler: _identity(handler.email) if getattr(handler, "email", None) else None)
    ownership.clear_request_context()
    yield SimpleNamespace(state_dir=state_dir, home=home, jobs=jobs_mod)
    ownership.clear_request_context()
    loader.set_policy_loader(None)


def _as_request(email, path="/api/crons/update"):
    """Bind a request of ``email`` to this thread, as server.py does."""
    from api import ownership

    handler = _Handler(email, path)
    ownership.set_request_context(handler)
    return handler


def _job(job_id="j1", **extra):
    job = {"id": job_id, "name": "Report", "deliver": "telegram:1", "owner_email": OWNER,
           "origin": {"platform": "webui", "chat_id": None, "user_id": OWNER}}
    job.update(extra)
    return job


def _flags(completion):
    return {key: completion[key] for key in ("toast", "badge", "desktop", "silent")}


# -- The policy in use ---------------------------------------------------------

def test_the_policy_in_use_is_the_engine_module_or_the_pinned_copy(notify_env):
    from api import cron_notifications as cn

    expected = _ENGINE_POLICY if _ENGINE_POLICY is not None else fallback_policy
    assert cn.notify_policy() is expected


# -- GET /api/crons: decorate_job ----------------------------------------------

def test_legacy_job_resolves_to_every_run_and_always_deliver(notify_env):
    from api import cron_notifications as cn

    out = cn.decorate_job({"id": "legacy", "toast_notifications": True}, viewer=OWNER)
    assert out["notify"] == {"in_app": "all", "delivery": "all"}
    assert out["notify_source"] == "legacy"
    assert out["my_notify"] is None
    assert out["managed_by"] == "client"
    assert out["support_notified"] is False


def test_legacy_job_with_toasts_off_resolves_to_never(notify_env):
    from api import cron_notifications as cn

    out = cn.decorate_job({"id": "quiet", "toast_notifications": False})
    assert out["notify"] == {"in_app": "quiet", "delivery": "all"}
    assert out["notify_source"] == "legacy"


def test_explicit_notify_is_returned_resolved(notify_env):
    from api import cron_notifications as cn

    out = cn.decorate_job({"id": "x", "notify": {"in_app": "failures", "delivery": "failures"}})
    assert out["notify"] == {"in_app": "failures", "delivery": "failures"}
    assert out["notify_source"] == "explicit"


def test_damaged_notify_reads_as_legacy_and_keeps_delivering(notify_env):
    from api import cron_notifications as cn

    out = cn.decorate_job({"id": "x", "notify": {"in_app": "loud"}, "toast_notifications": True})
    assert out["notify"] == {"in_app": "all", "delivery": "all"}
    assert out["notify_source"] == "legacy"


@pytest.mark.parametrize("managed_by, telemetry, expected", [
    ("synthwave", "1", True),
    ("Synthwave", "true", True),
    ("synthwave", None, False),
    ("synthwave", "0", False),
    ("client", "1", False),
    (None, "1", False),
    ("somebody", "1", False),
])
def test_support_notified_needs_a_synthwave_task_and_operational_telemetry(
        notify_env, monkeypatch, managed_by, telemetry, expected):
    from api import cron_notifications as cn

    if telemetry is not None:
        monkeypatch.setenv("SP_OPERATIONAL_TELEMETRY", telemetry)
    out = cn.decorate_job({"id": "m", "managed_by": managed_by})
    assert out["support_notified"] is expected
    assert out["managed_by"] == ("synthwave" if str(managed_by).lower() == "synthwave" else "client")
    assert cn.support_notified({"managed_by": managed_by}) is expected


def test_my_notify_is_the_viewers_own_level_only(notify_env):
    from api import cron_notifications as cn

    cn.set_viewer_notify_level(SHAREE, "j1", "quiet", revision=0)
    assert cn.decorate_job(_job(), viewer=SHAREE)["my_notify"] == "quiet"
    assert cn.decorate_job(_job(), viewer=SHAREE.upper())["my_notify"] == "quiet"
    assert cn.decorate_job(_job(), viewer=OWNER)["my_notify"] is None
    assert cn.decorate_job(_job(), viewer=None)["my_notify"] is None


def test_job_listing_route_carries_the_notify_fields(notify_env):
    import api.routes as routes
    from api import cron_notifications as cn

    cn.set_viewer_notify_level(SHAREE, "j1", "failures", revision=0)
    job = _job(notify={"in_app": "all", "delivery": "failures"}, managed_by="synthwave",
               shared_with=[SHAREE], last_run_at=_now_iso(), last_status="ok")
    (payload,) = routes._cron_jobs_for_api([job], viewer=SHAREE)
    assert payload["notify"] == {"in_app": "all", "delivery": "failures"}
    assert payload["notify_source"] == "explicit"
    assert payload["my_notify"] == "failures"
    assert payload["managed_by"] == "synthwave"
    assert payload["support_notified"] is False
    assert payload["delivery_status"] == "delivered"


# -- GET /api/crons/recent: decorate_completion ----------------------------------

# The plan 3.1 table, as (level, success) -> (toast, badge, desktop).
IN_APP_TABLE = {
    ("all", True): (True, True, False),
    ("all", False): (True, True, True),
    ("failures", True): (False, False, False),
    ("failures", False): (True, True, True),
    ("quiet", True): (False, True, False),
    ("quiet", False): (False, True, False),
    ("off", True): (False, False, False),
    ("off", False): (False, False, False),
}


@pytest.mark.parametrize("level, success", sorted(IN_APP_TABLE))
def test_completion_flags_follow_the_in_app_table(notify_env, level, success):
    from api import cron_notifications as cn

    job = _job(notify={"in_app": level, "delivery": "all"})
    completion = {"job_id": "j1", "status": "ok" if success else "error", "toast_notifications": True}
    out = cn.decorate_completion(completion, job, viewer=OWNER)
    toast, badge, desktop = IN_APP_TABLE[(level, success)]
    assert _flags(out) == {"toast": toast, "badge": badge, "desktop": desktop, "silent": False}
    # Older clients read toast_notifications: it carries the same decision.
    assert out["toast_notifications"] is toast


def test_legacy_jobs_notify_exactly_as_before(notify_env):
    from api import cron_notifications as cn

    loud, muted = _job("loud"), _job("muted", toast_notifications=False)
    for status in ("ok", "error"):
        out = cn.decorate_completion({"job_id": "loud", "status": status}, loud)
        assert out["toast"] is True and out["badge"] is True
        assert out["toast_notifications"] is True
        out = cn.decorate_completion({"job_id": "muted", "status": status}, muted)
        assert out["toast"] is False and out["badge"] is True
        assert out["toast_notifications"] is False


def test_silent_run_from_the_delivery_record_notifies_nobody(notify_env):
    from api import cron_notifications as cn

    out = cn.decorate_completion({"job_id": "j1", "status": "ok", "delivery_status": "silent"}, _job())
    assert _flags(out) == {"toast": False, "badge": False, "desktop": False, "silent": True}
    assert out["toast_notifications"] is False


@pytest.mark.parametrize("output", [
    "# Cron Job: r\n\n## Prompt\n\np\n\n## Response\n\n[SILENT]\n",
    "# Cron Job: m\n\n**Job ID:** j1\n**Mode:** monitor\n**Status:** no_change (agent run suppressed)\n",
])
def test_silent_run_from_its_output_notifies_nobody(notify_env, output):
    from api import cron_notifications as cn

    run_at = _now_iso()
    out_dir = notify_env.home / "cron" / "output" / "j1"
    out_dir.mkdir(parents=True)
    (out_dir / "run.md").write_text(output, encoding="utf-8")
    job = _job(last_run_at=run_at)
    out = cn.decorate_completion({"job_id": "j1", "status": "ok"}, job)
    assert out["silent"] is True
    assert out["toast"] is False and out["badge"] is False


def test_an_output_written_after_the_first_poll_is_still_read(notify_env):
    from api import cron_notifications as cn

    job = _job(last_run_at=_now_iso())
    assert cn.decorate_completion({"job_id": "j1", "status": "ok"}, job)["silent"] is False
    out_dir = notify_env.home / "cron" / "output" / "j1"
    out_dir.mkdir(parents=True)
    (out_dir / "run.md").write_text("## Response\n\n[SILENT]\n", encoding="utf-8")
    assert cn.decorate_completion({"job_id": "j1", "status": "ok"}, job)["silent"] is True


def test_a_normal_output_and_a_failed_run_are_never_silent(notify_env):
    from api import cron_notifications as cn

    run_at = _now_iso()
    out_dir = notify_env.home / "cron" / "output" / "j1"
    out_dir.mkdir(parents=True)
    (out_dir / "run.md").write_text(
        "## Response\n\nThe monitor said **Status:** no_change earlier, now it changed.\n", encoding="utf-8")
    out = cn.decorate_completion({"job_id": "j1", "status": "ok"}, _job(last_run_at=run_at))
    assert out["silent"] is False and out["toast"] is True
    (out_dir / "run.md").write_text("## Response\n\n[SILENT]\n", encoding="utf-8")
    out = cn.decorate_completion({"job_id": "j1", "status": "error"}, _job("j1", last_run_at=_now_iso(1)))
    assert out["silent"] is False and out["toast"] is True and out["desktop"] is True


def test_viewer_level_only_lowers_the_job_level(notify_env):
    from api import cron_notifications as cn

    loud = _job("loud", notify={"in_app": "all", "delivery": "all"})
    quiet = _job("quiet", notify={"in_app": "quiet", "delivery": "all"})
    cn.set_viewer_notify_level(SHAREE, "loud", "quiet", revision=0)
    cn.set_viewer_notify_level(SHAREE, "quiet", "failures", revision=1)
    failed = {"status": "error"}
    assert _flags(cn.decorate_completion(failed, loud, viewer=SHAREE)) == {
        "toast": False, "badge": True, "desktop": False, "silent": False}
    # The owner is unaffected by the sharee's mute.
    assert _flags(cn.decorate_completion(failed, loud, viewer=OWNER)) == {
        "toast": True, "badge": True, "desktop": True, "silent": False}
    # A viewer level can not raise a job level.
    assert _flags(cn.decorate_completion(failed, quiet, viewer=SHAREE)) == {
        "toast": False, "badge": True, "desktop": False, "silent": False}


def test_job_level_off_silences_cron_admins_by_default(notify_env):
    from api import cron_notifications as cn

    job = _job(notify={"in_app": "off", "delivery": "all"})
    for viewer in (ADMIN, OWNER):
        _as_request(viewer, "/api/crons/recent")
        out = cn.decorate_completion({"status": "error"}, job, viewer=viewer)
        assert out["toast"] is False and out["badge"] is False and out["desktop"] is False


def test_admin_override_lets_cron_admins_keep_notifications(notify_env, monkeypatch):
    from api import cron_notifications as cn

    monkeypatch.setenv("HERMES_WEBUI_CRON_NOTIFY_ADMIN_OVERRIDE", "1")
    job = _job(notify={"in_app": "off", "delivery": "all"})
    _as_request(ADMIN, "/api/crons/recent")
    out = cn.decorate_completion({"status": "error"}, job, viewer=ADMIN)
    assert out["toast"] is True and out["badge"] is True and out["desktop"] is True
    # Without a request on the thread the admin is found by email.
    from api import ownership

    ownership.clear_request_context()
    assert cn.decorate_completion({"status": "error"}, job, viewer=ADMIN)["toast"] is True
    # Everyone else stays silenced.
    _as_request(OWNER, "/api/crons/recent")
    assert cn.decorate_completion({"status": "error"}, job, viewer=OWNER)["toast"] is False


def test_admin_override_setting_is_read_from_the_webui_settings(notify_env, monkeypatch):
    import api.config as config
    from api import cron_notifications as cn

    job = _job(notify={"in_app": "off", "delivery": "all"})
    monkeypatch.setattr(config, "load_settings", lambda: {"cron_notify_admin_override": True})
    assert cn.decorate_completion({"status": "ok"}, job, viewer=ADMIN)["toast"] is True
    monkeypatch.setattr(config, "load_settings", lambda: {"cron_notify_admin_override": "yes"})
    assert cn.decorate_completion({"status": "ok"}, job, viewer=ADMIN)["toast"] is False
    # The env var wins over the setting.
    monkeypatch.setattr(config, "load_settings", lambda: {"cron_notify_admin_override": True})
    monkeypatch.setenv("HERMES_WEBUI_CRON_NOTIFY_ADMIN_OVERRIDE", "0")
    assert cn.decorate_completion({"status": "ok"}, job, viewer=ADMIN)["toast"] is False


def test_recent_route_adds_flags_and_reports_muted_runs(notify_env, monkeypatch):
    import api.cron_scope as cron_scope
    import api.cron_webui_delivery as cwd
    import api.routes as routes

    run_at = _now_iso()
    jobs = [
        _job("muted", deliver="telegram:1", notify={"in_app": "failures", "delivery": "failures"},
             last_run_at=run_at, last_status="ok"),
        _job("failed", deliver="telegram:1", notify={"in_app": "failures", "delivery": "failures"},
             last_run_at=run_at, last_status="error"),
        _job("legacy", deliver="telegram:1", last_run_at=run_at, last_status="ok"),
    ]
    notify_env.jobs.list_jobs = lambda include_disabled=True: copy.deepcopy(jobs)
    cwd.record_run_outcome(jobs[0], cwd.OUTCOME_MUTED)
    monkeypatch.setattr(cron_scope, "scope_cron_completions_for_caller", lambda handler, rows: rows)
    monkeypatch.setattr(routes, "_latest_cron_session_info_for_jobs", lambda ids, done=None: {})

    handler = _as_request(OWNER, "/api/crons/recent")
    routes._handle_cron_recent(handler, SimpleNamespace(query="since=0"))
    assert handler.status == 200
    by_id = {c["job_id"]: c for c in handler.body["completions"]}
    assert by_id["muted"]["delivery_status"] == "muted"
    assert by_id["muted"]["status"] == "ok"
    assert _flags(by_id["muted"]) == {"toast": False, "badge": False, "desktop": False, "silent": False}
    assert _flags(by_id["failed"]) == {"toast": True, "badge": True, "desktop": True, "silent": False}
    assert _flags(by_id["legacy"]) == {"toast": True, "badge": True, "desktop": False, "silent": False}
    assert by_id["legacy"]["toast_notifications"] is True


# -- POST /api/crons/create and /update: validate_notify_field -------------------

def test_notify_values_are_normalized(notify_env):
    from api import cron_notifications as cn

    assert cn.validate_notify_field(None, is_admin=False) is None
    assert cn.validate_notify_field({"in_app": "failures"}, is_admin=False) == {
        "in_app": "failures", "delivery": "all"}
    assert cn.validate_notify_field({"delivery": "failures"}, is_admin=False) == {
        "in_app": "all", "delivery": "failures"}
    assert cn.validate_notify_field({}, is_admin=False) == {"in_app": "all", "delivery": "all"}


@pytest.mark.parametrize("value", [
    "all", ["all"], 1, True, {"in_app": "loud"}, {"delivery": "quiet"}, {"in_app": None},
    {"in_app": "all", "extra": "x"}, {"owner_email": "x@example.test"},
])
def test_malformed_notify_values_are_refused(notify_env, value):
    from api import cron_notifications as cn

    with pytest.raises(ValueError):
        cn.validate_notify_field(value, is_admin=True)


@pytest.mark.parametrize("value", [
    {"in_app": "off"}, {"delivery": "off"}, {"in_app": "off", "delivery": "off"},
])
def test_off_is_for_cron_admins_only(notify_env, value):
    from api import cron_notifications as cn

    with pytest.raises(ValueError, match="cron admin"):
        cn.validate_notify_field(value, is_admin=False)
    assert cn.validate_notify_field(value, is_admin=True)["in_app"] == value.get("in_app", "all")


def test_caller_context_decides_admin_when_the_route_does_not_say(notify_env):
    from api import cron_notifications as cn

    # No request bound to the thread: not an admin (fail closed).
    with pytest.raises(ValueError, match="cron admin"):
        cn.validate_notify_field({"in_app": "off"})
    _as_request(OWNER)
    with pytest.raises(ValueError, match="cron admin"):
        cn.validate_notify_field({"delivery": "off"})
    _as_request(ADMIN)
    assert cn.validate_notify_field({"delivery": "off"}) == {"in_app": "all", "delivery": "off"}
    _as_request(BOOTSTRAP)
    assert cn.validate_notify_field({"in_app": "off"})["in_app"] == "off"


def test_governance_off_treats_every_caller_as_cron_admin(notify_env):
    from api import cron_notifications as cn

    loader.set_policy_loader(lambda: parse_governance_policy({"version": 1, "mode": "off"}))
    _as_request(OWNER)
    assert cn.validate_notify_field({"in_app": "off"})["in_app"] == "off"


def test_admin_set_off_is_read_only_for_everyone_else(notify_env):
    from api import cron_notifications as cn

    stored = _job(notify={"in_app": "off", "delivery": "failures"})
    # Saving it back unchanged, or changing the other level, is fine.
    assert cn.validate_notify_field({"in_app": "off", "delivery": "failures"}, is_admin=False, job=stored)
    assert cn.validate_notify_field({"in_app": "off", "delivery": "all"}, is_admin=False, job=stored) == {
        "in_app": "off", "delivery": "all"}
    # Lifting it, or clearing notify (which would lift it), is not.
    with pytest.raises(ValueError, match="cron admin"):
        cn.validate_notify_field({"in_app": "all", "delivery": "failures"}, is_admin=False, job=stored)
    with pytest.raises(ValueError, match="cron admin"):
        cn.validate_notify_field(None, is_admin=False, job=stored)
    # A cron admin may.
    assert cn.validate_notify_field(None, is_admin=True, job=stored) is None
    # Setting off on a task that has none is refused as before.
    with pytest.raises(ValueError, match="cron admin"):
        cn.validate_notify_field({"delivery": "off"}, is_admin=False, job=_job())


def test_report_only_audits_a_refused_off_and_lets_it_through(notify_env, monkeypatch, tmp_path):
    from api import cron_notifications as cn
    from api.governance.audit import read_audit_events

    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "audit_home"))
    loader.set_policy_loader(lambda: parse_governance_policy({**POLICY, "mode": "report_only"}))
    _as_request(OWNER)
    assert cn.validate_notify_field({"in_app": "off"})["in_app"] == "off"
    events = [e for e in read_audit_events(limit=50) if e.get("reason") == "cron_notify_admin_level"]
    assert events and all(e["event"] == "would_deny" and e["report_only"] for e in events)
    assert events[0]["path"] == "/api/crons/update"


def test_new_task_defaults_follow_the_plan(notify_env):
    from api import cron_notifications as cn

    assert cn.notify_for_new_job(None) == {
        "notify": {"in_app": "all", "delivery": "all"}, "toast_notifications": True}
    assert cn.notify_for_new_job("Monitoring") == {
        "notify": {"in_app": "failures", "delivery": "all"}, "toast_notifications": True}


class _CronStore:
    def __init__(self):
        self.jobs = {"own": _job("own", deliver="local")}
        self.creates, self.updates = [], []

    def install(self, jobs_mod):
        store = self

        def get_job(job_id):
            job = store.jobs.get(job_id)
            return copy.deepcopy(job) if job else None

        def update_job(job_id, updates):
            store.updates.append((job_id, copy.deepcopy(updates)))
            store.jobs[job_id].update(copy.deepcopy(updates))
            return copy.deepcopy(store.jobs[job_id])

        def create_job(**kwargs):
            store.creates.append(kwargs)
            job = {"id": "new", "name": kwargs.get("name") or "new", "prompt": kwargs["prompt"],
                   "schedule": kwargs["schedule"], "owner_email": kwargs.get("owner_email") or ""}
            store.jobs["new"] = job
            return copy.deepcopy(job)

        jobs_mod.get_job, jobs_mod.update_job, jobs_mod.create_job = get_job, update_job, create_job


@pytest.fixture
def cron_routes(notify_env, monkeypatch):
    """The real handle_post with an in-memory cron store; each request is
    bound to the thread the way server.py binds it."""
    import api.profiles as profiles
    import api.routes as routes

    store = _CronStore()
    store.install(notify_env.jobs)
    monkeypatch.setattr(routes, "_get_active_profile_name", lambda: "default")
    monkeypatch.setattr(routes, "_ensure_agent_cron_import_path", lambda: None)
    monkeypatch.setattr(routes, "_check_csrf", lambda _handler: True)
    monkeypatch.setattr(routes, "_guard_request_session_visibility",
                        lambda handler, parsed, body=None, method="GET": True)
    monkeypatch.setattr(profiles, "cron_profile_context", nullcontext)

    def post(path, body, email):
        monkeypatch.setattr(routes, "read_body", lambda _handler: copy.deepcopy(body))
        handler = _as_request(email, path)
        routes.handle_post(handler, SimpleNamespace(path=path, query=""))
        return handler

    return SimpleNamespace(store=store, post=post)


def test_owner_sets_notify_on_update_with_the_toast_mirror(cron_routes):
    handler = cron_routes.post("/api/crons/update", {
        "job_id": "own", "notify": {"in_app": "quiet", "delivery": "failures"}, "toast_notifications": True,
    }, OWNER)
    assert handler.status == 200, handler.body
    assert cron_routes.store.updates == [("own", {
        "toast_notifications": False, "notify": {"in_app": "quiet", "delivery": "failures"}})]
    job = handler.body["job"]
    assert job["notify"] == {"in_app": "quiet", "delivery": "failures"}
    assert job["notify_source"] == "explicit"


def test_owner_can_not_turn_notifications_off(cron_routes):
    for notify in ({"in_app": "off"}, {"delivery": "off"}):
        handler = cron_routes.post("/api/crons/update", {"job_id": "own", "notify": notify}, OWNER)
        assert handler.status == 400
        assert "cron admin" in handler.body["error"]
    handler = cron_routes.post("/api/crons/create", {
        "prompt": "p", "schedule": "every 1h", "notify": {"delivery": "off"}}, OWNER)
    assert handler.status == 400
    assert cron_routes.store.updates == [] and cron_routes.store.creates == []


def test_cron_admin_turns_delivery_off_and_foreign_jobs_stay_refused(cron_routes):
    handler = cron_routes.post("/api/crons/update", {
        "job_id": "own", "notify": {"in_app": "off", "delivery": "off"}}, ADMIN)
    assert handler.status == 200, handler.body
    assert cron_routes.store.jobs["own"]["notify"] == {"in_app": "off", "delivery": "off"}
    assert cron_routes.store.jobs["own"]["toast_notifications"] is False
    handler = cron_routes.post("/api/crons/update", {"job_id": "own", "notify": {"in_app": "all"}}, OTHER)
    assert handler.status == 403


def test_create_stores_the_validated_notify(cron_routes):
    handler = cron_routes.post("/api/crons/create", {
        "prompt": "p", "schedule": "every 1h", "category": "Monitoring",
        "notify": {"in_app": "failures"}}, OWNER)
    assert handler.status == 200, handler.body
    job_id, updates = cron_routes.store.updates[-1]
    assert job_id == "new"
    assert updates["notify"] == {"in_app": "failures", "delivery": "all"}
    assert updates["toast_notifications"] is True


def _routes_pass_the_notify_caller_context() -> bool:
    import inspect

    import api.routes as routes

    return "job" in inspect.signature(routes._cron_notify_updates).parameters


@pytest.mark.skipif(not _routes_pass_the_notify_caller_context(),
                    reason="api/routes.py does not pass is_admin and the stored job to the notify seam yet")
def test_owner_saves_an_admin_off_back_unchanged_but_can_not_lift_it(cron_routes):
    cron_routes.store.jobs["own"]["notify"] = {"in_app": "off", "delivery": "all"}
    handler = cron_routes.post("/api/crons/update", {
        "job_id": "own", "name": "Renamed", "notify": {"in_app": "off", "delivery": "failures"}}, OWNER)
    assert handler.status == 200, handler.body
    assert cron_routes.store.jobs["own"]["notify"] == {"in_app": "off", "delivery": "failures"}
    for notify in ({"in_app": "all", "delivery": "failures"}, None):
        handler = cron_routes.post("/api/crons/update", {"job_id": "own", "notify": notify}, OWNER)
        assert handler.status == 400 and "cron admin" in handler.body["error"]
    assert cron_routes.store.jobs["own"]["notify"] == {"in_app": "off", "delivery": "failures"}


def test_malformed_notify_on_update_is_a_400_and_writes_nothing(cron_routes):
    handler = cron_routes.post("/api/crons/update", {"job_id": "own", "notify": {"in_app": "loud"}}, OWNER)
    assert handler.status == 400
    assert "notify.in_app" in handler.body["error"]
    assert cron_routes.store.updates == []


# -- Run now -----------------------------------------------------------------------

def test_manual_run_kwargs_follow_the_engine_signature(notify_env):
    from api import cron_notifications as cn

    scheduler = sys.modules["cron.scheduler"]
    scheduler.run_job = lambda job: None
    assert cn.manual_run_kwargs({"id": "j"}, actor=OWNER) == {}

    def run_job(job, *, trigger=None, trigger_actor=None, run_prompt=None):
        return None

    scheduler.run_job = run_job
    assert cn.manual_run_kwargs({"id": "j"}, actor=" Owner@Example.test ") == {
        "trigger": "manual", "trigger_actor": OWNER}
    assert cn.manual_run_kwargs({"id": "j"}, actor=None) == {"trigger": "manual"}
    scheduler.run_job = lambda job, **kwargs: None
    assert cn.manual_run_kwargs({"id": "j"}, actor=OWNER) == {"trigger": "manual", "trigger_actor": OWNER}
    scheduler.run_job = lambda job, *, trigger=None: None
    assert cn.manual_run_kwargs({"id": "j"}, actor=OWNER) == {"trigger": "manual"}
    # Nothing to inspect (or an uninspectable callable): the runner keeps its
    # old call, without run_kwargs.
    scheduler.run_job = len
    assert cn.manual_run_kwargs({"id": "j"}, actor=OWNER) == {}
    del scheduler.run_job
    assert cn.manual_run_kwargs({"id": "j"}, actor=OWNER) == {}


@pytest.mark.parametrize("delivery, success, silent, default, expected", [
    (None, True, False, True, (True, None)),
    (None, False, False, True, (True, None)),
    ("all", True, False, True, (True, None)),
    ("failures", True, False, True, (False, "suppressed_muted")),
    ("failures", False, False, True, (True, None)),
    ("off", True, False, True, (False, "suppressed_muted")),
    ("off", False, False, True, (False, "suppressed_muted")),
    ("all", True, True, False, (False, "suppressed_silent")),
    ("failures", True, True, False, (False, "suppressed_silent")),
    ("all", True, False, False, (False, None)),
])
def test_delivery_decision_follows_the_delivery_level(notify_env, delivery, success, silent, default, expected):
    from api import cron_notifications as cn

    job = _job() if delivery is None else _job(notify={"in_app": "all", "delivery": delivery})
    assert cn.delivery_decision(job, success=success, silent=silent, default=default) == expected


def test_engine_with_delivery_outcome_records_muted_and_silent_itself(notify_env):
    import api.cron_webui_delivery as cwd
    from api import cron_notifications as cn

    calls = []

    def mark_job_run(job_id, success, error=None, delivery_error=None, status=None, *, delivery_outcome=None):
        calls.append((job_id, success, error, delivery_error, delivery_outcome))

    notify_env.jobs.mark_job_run = mark_job_run
    notify_env.jobs.get_job = lambda job_id: _job(job_id, last_run_at=_now_iso())
    cn.record_manual_outcome("j1", True, None, delivery_error=None, outcome="suppressed_muted")
    cn.record_manual_outcome("j2", True, None, delivery_error=None, outcome="suppressed_silent")
    cn.record_manual_outcome("j3", False, "boom", delivery_error="gone", outcome=None)
    assert calls == [
        ("j1", True, None, None, "suppressed_muted"),
        ("j2", True, None, None, "suppressed"),
        ("j3", False, "boom", "gone", None),
    ]
    assert cwd.load_ledger()["jobs"] == {}


def test_engine_without_delivery_outcome_gets_the_bridge_ledger(notify_env):
    import api.cron_webui_delivery as cwd
    from api import cron_notifications as cn

    calls, stored = [], {}

    def mark_job_run(job_id, success, error=None, delivery_error=None):
        calls.append((job_id, success, error, delivery_error))
        stored[job_id] = _job(job_id, deliver="telegram:1", last_run_at=_now_iso(len(stored)),
                              last_status="ok" if success else "error")

    notify_env.jobs.mark_job_run = mark_job_run
    notify_env.jobs.get_job = lambda job_id: copy.deepcopy(stored.get(job_id))
    cn.record_manual_outcome("muted", True, None, delivery_error=None, outcome="suppressed_muted")
    cn.record_manual_outcome("silent", True, None, delivery_error=None, outcome="suppressed_silent")
    cn.record_manual_outcome("plain", True, None, delivery_error=None, outcome=None)
    assert calls == [("muted", True, None, None), ("silent", True, None, None), ("plain", True, None, None)]
    ledger = cwd.load_ledger()["jobs"]
    assert ledger["muted"]["outcome"] == "suppressed_muted"
    assert ledger["muted"]["run_at"] == stored["muted"]["last_run_at"]
    assert ledger["silent"]["outcome"] == "suppressed_silent"
    assert "plain" not in ledger
    assert cwd.delivery_state_for_job(stored["muted"]) == ("muted", None)
    assert cwd.delivery_state_for_job(stored["silent"]) == ("silent", None)
    assert cwd.delivery_state_for_job(stored["plain"]) == ("delivered", None)
    # The next run is not reported as muted.
    later = dict(stored["muted"], last_run_at=_now_iso(60))
    assert cwd.delivery_state_for_job(later) == ("delivered", None)


def test_engines_without_delivery_error_still_record_the_run(notify_env):
    from api import cron_notifications as cn

    calls = []
    notify_env.jobs.mark_job_run = lambda job_id, success, error=None: calls.append((job_id, success, error))
    notify_env.jobs.get_job = lambda job_id: None
    cn.record_manual_outcome("j", True, None, delivery_error=None, outcome="suppressed_muted")
    assert calls == [("j", True, None)]


def _install_run_fakes(notify_env, calls, stored):
    scheduler = sys.modules["cron.scheduler"]
    scheduler.run_job = lambda job, *, trigger=None, trigger_actor=None, run_prompt=None: None
    scheduler.SILENT_MARKER = "[SILENT]"
    scheduler._deliver_result = lambda job, content: calls.append(("deliver", job["id"], content)) or None
    notify_env.jobs.save_job_output = lambda job_id, output: calls.append(("save", job_id))

    def mark_job_run(job_id, success, error=None, delivery_error=None):
        calls.append(("mark", job_id, success))
        stored[job_id] = dict(stored[job_id], last_run_at=_now_iso(), last_status="ok" if success else "error")

    notify_env.jobs.mark_job_run = mark_job_run
    notify_env.jobs.get_job = lambda job_id: copy.deepcopy(stored.get(job_id))


@pytest.mark.parametrize("success, final, delivered, state", [
    (True, "All green.", False, "muted"),
    (False, None, True, "delivered"),
    (True, "[SILENT]", False, "silent"),
])
def test_run_now_with_only_send_when_it_fails(notify_env, monkeypatch, success, final, delivered, state):
    import api.cron_webui_delivery as cwd
    import api.routes as routes

    calls = []
    stored = {"r": _job("r", deliver="telegram:1", notify={"in_app": "all", "delivery": "failures"})}
    _install_run_fakes(notify_env, calls, stored)
    received = []

    def run(job, execution_profile_home, run_kwargs=None):
        received.append(run_kwargs)
        return success, "out", final, None if success else "boom"

    monkeypatch.setattr(routes, "_run_cron_job_in_profile_subprocess", run)
    routes._mark_cron_running("r")
    routes._run_cron_tracked(copy.deepcopy(stored["r"]), actor=OWNER)
    assert received == [{"trigger": "manual", "trigger_actor": OWNER}]
    assert any(c[0] == "deliver" for c in calls) is delivered
    assert ("mark", "r", success) in calls
    assert cwd.delivery_state_for_job(stored["r"]) == (state, None)
    assert routes._is_cron_running("r") == (False, 0.0)


def test_profile_isolation_preserves_engine_notification_capabilities(monkeypatch):
    from api import cron_notifications, profiles
    scheduler = types.ModuleType("cron.scheduler")
    def run_job(job, *, extra_prompt=None):
        return job
    scheduler.run_job = run_job
    cron = types.ModuleType("cron")
    cron.__path__ = []
    cron.scheduler = scheduler
    monkeypatch.setitem(sys.modules, "cron", cron)
    monkeypatch.setitem(sys.modules, "cron.scheduler", scheduler)
    profiles.install_cron_scheduler_profile_isolation()
    assert scheduler.run_job is not run_job
    assert cron_notifications.manual_run_kwargs({}, actor=OWNER) == {}


def test_notification_delivery_policy_exists_at_initial_job_creation(cron_routes, monkeypatch):
    jobs = sys.modules["cron.jobs"]
    original = jobs.create_job
    initial = []
    def create_job(*, notify=None, category=None, managed_by=None, **kwargs):
        initial.append({"notify": notify, "category": category, "managed_by": managed_by})
        return original(**kwargs)
    monkeypatch.setattr(jobs, "create_job", create_job)
    reply = cron_routes.post("/api/crons/create", {
        "prompt": "Synthetic monitoring", "schedule": "every 1h", "category": "Monitoring",
        "notify": {"in_app": "quiet", "delivery": "off"}}, ADMIN)
    assert reply.status == 200, reply.body
    assert initial == [{"notify": {"in_app": "quiet", "delivery": "off"}, "category": "Monitoring", "managed_by": None}]
