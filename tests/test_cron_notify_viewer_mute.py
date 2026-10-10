"""Per-viewer mute for scheduled tasks (plan 3.1, package W1).

``GET /api/crons/notifications`` returns ``{revision, jobs}``: the caller's
own in-app level per job (``jobs`` maps a job id to ``{"in_app": level}``),
only for jobs they can still see. ``POST /api/crons/notifications
{job_id, in_app|null, revision}`` sets or clears it: 404 when the job is not
visible to the caller, 409 on a stale revision, 400 on a malformed body, 403
without a signed-in email.

A person's own level only lowers what that person sees (the effective flags
are the AND of the job level and theirs), so a sharee can mute a task for
themselves without edit rights and the owner is unaffected. Visibility is the
Tasks listing's rule (api/cron_scope.py): own or shared tasks in any store,
other tasks by the profile rule, the root store for cron admins only.
"""

from __future__ import annotations

import copy
import io
import json
import sys
import threading
import types
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

from api.governance import loader
from api.governance.loader import parse_governance_policy

ADMIN = "cronadmin@example.test"
OWNER = "owner@example.test"
SHAREE = "sharee@example.test"
OTHER = "other@example.test"

POLICY = {
    "version": 1,
    "mode": "enforce",
    "default_effect": "deny",
    "bootstrap_admins": ["boot@example.test"],
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
    def __init__(self, email=None, path="/api/crons/notifications"):
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


def _webui_job(job_id, owner, **extra):
    job = {"id": job_id, "name": job_id, "deliver": "local", "owner_email": owner,
           "origin": {"platform": "webui", "chat_id": None, "user_id": owner}}
    job.update(extra)
    return job


def _write_jobs(home: Path, jobs):
    (home / "cron").mkdir(parents=True, exist_ok=True)
    (home / "cron" / "jobs.json").write_text(json.dumps({"jobs": jobs}), encoding="utf-8")


@pytest.fixture
def mute_env(monkeypatch, tmp_path):
    """Three cron stores: the root store (active), profile ``alpha`` and a
    hidden profile; an injected policy and the real routes dispatcher."""
    import api.config as config
    import api.governance.enforce as enforce
    import api.profiles as profiles
    import api.routes as routes

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setattr(config, "STATE_DIR", state_dir)
    root, alpha, secret = tmp_path / "root", tmp_path / "alpha", tmp_path / "secret"
    _write_jobs(root, [
        _webui_job("own-root", OWNER, shared_with=[SHAREE]),
        _webui_job("foreign-root", OTHER),
    ])
    _write_jobs(alpha, [_webui_job("alpha-job", OTHER)])
    _write_jobs(secret, [_webui_job("secret-job", OTHER)])
    homes = {"default": root, "alpha": alpha, "secret": secret}
    monkeypatch.setattr(profiles, "get_active_profile_name", lambda: "default")
    monkeypatch.setattr(profiles, "get_active_hermes_home", lambda: root)
    monkeypatch.setattr(profiles, "get_hermes_home_for_profile", lambda name: homes.get(name or "default", root))
    monkeypatch.setattr(profiles, "list_profiles_api", lambda **kw: [
        {"name": "default", "path": str(root)},
        {"name": "alpha", "path": str(alpha)},
        {"name": "secret", "path": str(secret), "visible": False},
    ])

    cron_pkg = types.ModuleType("cron")
    cron_pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "cron", cron_pkg)
    monkeypatch.delitem(sys.modules, "cron.notify_policy", raising=False)

    loader.set_policy_loader(lambda: parse_governance_policy(POLICY))
    monkeypatch.setattr(enforce, "_request_identity",
                        lambda handler: _identity(handler.email) if getattr(handler, "email", None) else None)
    monkeypatch.setattr(routes, "_check_csrf", lambda _handler: True)
    monkeypatch.setattr(routes, "_guard_request_session_visibility",
                        lambda handler, parsed, body=None, method="GET": True)

    def get(email):
        handler = _Handler(email)
        routes.handle_get(handler, urlparse("http://localhost/api/crons/notifications"))
        return handler

    def post(body, email):
        monkeypatch.setattr(routes, "read_body", lambda _handler: copy.deepcopy(body))
        handler = _Handler(email)
        routes.handle_post(handler, SimpleNamespace(path="/api/crons/notifications", query=""))
        return handler

    yield SimpleNamespace(get=get, post=post, state_dir=state_dir, homes=homes)
    loader.set_policy_loader(None)


def _store_file(env):
    return env.state_dir / "cron_notify_viewers.json"


def test_nothing_set_reads_as_revision_zero(mute_env):
    handler = mute_env.get(SHAREE)
    assert handler.status == 200
    assert handler.body == {"revision": 0, "jobs": {}}


def test_sharee_mutes_a_shared_task_for_themselves_only(mute_env):
    from api import cron_notifications as cn

    handler = mute_env.post({"job_id": "own-root", "in_app": "quiet", "revision": 0}, SHAREE)
    assert handler.status == 200, handler.body
    assert handler.body == {"ok": True, "revision": 1, "job_id": "own-root", "in_app": "quiet"}
    assert mute_env.get(SHAREE).body == {"revision": 1, "jobs": {"own-root": {"in_app": "quiet"}}}
    assert mute_env.get(OWNER).body == {"revision": 0, "jobs": {}}

    job = _webui_job("own-root", OWNER, shared_with=[SHAREE])
    failed = {"job_id": "own-root", "status": "error"}
    sharee = cn.decorate_completion(failed, job, viewer=SHAREE)
    owner = cn.decorate_completion(failed, job, viewer=OWNER)
    assert (sharee["toast"], sharee["badge"], sharee["desktop"]) == (False, True, False)
    assert (owner["toast"], owner["badge"], owner["desktop"]) == (True, True, True)
    assert cn.decorate_job(job, viewer=SHAREE)["my_notify"] == "quiet"
    assert cn.decorate_job(job, viewer=OWNER)["my_notify"] is None


def test_a_viewer_may_turn_their_own_notifications_off(mute_env):
    from api import cron_notifications as cn

    assert mute_env.post({"job_id": "alpha-job", "in_app": "off", "revision": 0}, OWNER).status == 200
    out = cn.decorate_completion({"status": "error"}, _webui_job("alpha-job", OTHER), viewer=OWNER)
    assert (out["toast"], out["badge"], out["desktop"]) == (False, False, False)


def test_stale_revision_is_a_409_and_changes_nothing(mute_env):
    assert mute_env.post({"job_id": "own-root", "in_app": "failures", "revision": 0}, OWNER).status == 200
    handler = mute_env.post({"job_id": "own-root", "in_app": "quiet", "revision": 0}, OWNER)
    assert handler.status == 409
    assert handler.body["revision"] == 1
    assert handler.body["reason"] == "stale_revision"
    assert mute_env.get(OWNER).body == {"revision": 1, "jobs": {"own-root": {"in_app": "failures"}}}


def test_revisions_are_per_viewer(mute_env):
    assert mute_env.post({"job_id": "own-root", "in_app": "quiet", "revision": 0}, OWNER).status == 200
    assert mute_env.post({"job_id": "own-root", "in_app": "quiet", "revision": 0}, SHAREE).status == 200


@pytest.mark.parametrize("email, job_id", [
    (OWNER, "foreign-root"),   # root store, neither own nor shared: cron admins only
    (SHAREE, "foreign-root"),
    (OWNER, "secret-job"),     # hidden profile store
    (OWNER, "no-such-job"),
])
def test_a_task_the_caller_can_not_see_is_a_404(mute_env, email, job_id):
    handler = mute_env.post({"job_id": job_id, "in_app": "quiet", "revision": 0}, email)
    assert handler.status == 404
    assert handler.body == {"error": "Job not found"}
    assert not _store_file(mute_env).exists()


def test_cron_admin_sees_the_root_store(mute_env):
    assert mute_env.post({"job_id": "foreign-root", "in_app": "quiet", "revision": 0}, ADMIN).status == 200


def test_profile_grant_makes_another_store_visible(mute_env):
    assert mute_env.post({"job_id": "alpha-job", "in_app": "failures", "revision": 0}, SHAREE).status == 200


def test_null_and_all_clear_the_viewers_level(mute_env):
    assert mute_env.post({"job_id": "own-root", "in_app": "quiet", "revision": 0}, OWNER).status == 200
    handler = mute_env.post({"job_id": "own-root", "in_app": None, "revision": 1}, OWNER)
    assert handler.status == 200
    assert handler.body == {"ok": True, "revision": 2, "job_id": "own-root", "in_app": None}
    assert mute_env.get(OWNER).body == {"revision": 2, "jobs": {}}
    assert mute_env.post({"job_id": "own-root", "in_app": "failures", "revision": 2}, OWNER).status == 200
    handler = mute_env.post({"job_id": "own-root", "in_app": "all", "revision": 3}, OWNER)
    assert handler.body["in_app"] is None
    assert mute_env.get(OWNER).body == {"revision": 4, "jobs": {}}


@pytest.mark.parametrize("body, message", [
    ([], "Request body must be an object"),
    ({"job_id": "own-root", "in_app": "quiet", "revision": 0, "owner_email": "x"}, "Field not allowed: owner_email"),
    ({"in_app": "quiet", "revision": 0}, "job_id required"),
    ({"job_id": "", "in_app": "quiet", "revision": 0}, "job_id required"),
    ({"job_id": 7, "in_app": "quiet", "revision": 0}, "job_id required"),
    ({"job_id": "x" * 201, "in_app": "quiet", "revision": 0}, "job_id required"),
    ({"job_id": "own-root", "revision": 0}, "in_app required (null clears it)"),
    ({"job_id": "own-root", "in_app": "loud", "revision": 0}, None),
    ({"job_id": "own-root", "in_app": 1, "revision": 0}, None),
    ({"job_id": "own-root", "in_app": "quiet"}, "revision required"),
    ({"job_id": "own-root", "in_app": "quiet", "revision": True}, "revision required"),
    ({"job_id": "own-root", "in_app": "quiet", "revision": -1}, "revision required"),
    ({"job_id": "own-root", "in_app": "quiet", "revision": "0"}, "revision required"),
])
def test_malformed_bodies_are_a_400(mute_env, monkeypatch, body, message):
    from api import cron_notifications as cn

    handler = _Handler(OWNER)
    assert cn.handle_notifications_post(handler, copy.deepcopy(body)) is True
    assert handler.status == 400
    if message is None:
        assert handler.body["error"].startswith("in_app must be one of")
    else:
        assert handler.body == {"error": message}
    assert not _store_file(mute_env).exists()


def test_a_caller_without_an_email_can_not_mute(mute_env):
    handler = mute_env.post({"job_id": "own-root", "in_app": "quiet", "revision": 0}, None)
    assert handler.status == 403
    assert mute_env.get(None).body == {"revision": 0, "jobs": {}}


def test_get_lists_only_tasks_the_caller_can_still_see(mute_env):
    from api import cron_notifications as cn

    # Set while it was shared with the sharee, then the owner unshared it.
    cn.set_viewer_notify_level(SHAREE, "foreign-root", "quiet", revision=0)
    cn.set_viewer_notify_level(SHAREE, "gone", "quiet", revision=1)
    cn.set_viewer_notify_level(SHAREE, "alpha-job", "failures", revision=2)
    assert mute_env.get(SHAREE).body == {"revision": 3, "jobs": {"alpha-job": {"in_app": "failures"}}}


def test_the_store_survives_a_restart_and_follows_outside_edits(mute_env):
    from api import cron_notifications as cn

    assert mute_env.post({"job_id": "own-root", "in_app": "quiet", "revision": 0}, OWNER).status == 200
    data = json.loads(_store_file(mute_env).read_text(encoding="utf-8"))
    assert data["viewers"][OWNER]["revision"] == 1
    assert data["viewers"][OWNER]["jobs"]["own-root"]["in_app"] == "quiet"
    cn._STORE_CACHE.update(path=None, sig=None, data=None)  # a new process
    assert cn.viewer_notify_level(OWNER, "own-root") == "quiet"
    data["viewers"][OWNER]["jobs"]["own-root"]["in_app"] = "failures"
    data["viewers"][OWNER]["revision"] = 5
    _store_file(mute_env).write_text(json.dumps(data, indent=4), encoding="utf-8")
    assert cn.viewer_notify_level(OWNER, "own-root") == "failures"
    assert mute_env.get(OWNER).body["revision"] == 5


def test_a_corrupt_store_is_moved_aside_and_starts_fresh(mute_env):
    _store_file(mute_env).write_text("{not json", encoding="utf-8")
    assert mute_env.get(OWNER).body == {"revision": 0, "jobs": {}}
    assert [p.name.startswith("cron_notify_viewers.json.corrupt-") for p in mute_env.state_dir.iterdir()].count(True) == 1
    assert mute_env.post({"job_id": "own-root", "in_app": "quiet", "revision": 0}, OWNER).status == 200


def test_bad_entries_in_the_store_are_ignored(mute_env):
    from api import cron_notifications as cn

    _store_file(mute_env).write_text(json.dumps({"viewers": {
        OWNER: {"revision": 2, "jobs": {"own-root": {"in_app": "loud"}, "alpha-job": {"in_app": "quiet"},
                                        "x": "quiet", "": {"in_app": "quiet"}}},
        "": {"revision": 1, "jobs": {}},
        SHAREE: {"revision": True, "jobs": []},
    }}), encoding="utf-8")
    assert cn.viewer_notify_settings(OWNER) == (2, {"alpha-job": "quiet"})
    assert cn.viewer_notify_settings(SHAREE) == (0, {})


def test_each_viewer_keeps_a_bounded_number_of_entries(mute_env, monkeypatch):
    from api import cron_notifications as cn

    monkeypatch.setattr(cn, "MAX_ENTRIES_PER_VIEWER", 2)
    for revision, job_id in enumerate(("a", "b", "c")):
        cn.set_viewer_notify_level(OWNER, job_id, "quiet", revision=revision)
    assert cn.viewer_notify_settings(OWNER) == (3, {"b": "quiet", "c": "quiet"})


def test_concurrent_writes_with_one_revision_let_exactly_one_through(mute_env):
    from api import cron_notifications as cn

    results, barrier = [], threading.Barrier(4)

    def write(job_id):
        barrier.wait()
        try:
            results.append(cn.set_viewer_notify_level(OWNER, job_id, "quiet", revision=0))
        except cn.StaleRevisionError as stale:
            results.append(("stale", stale.current))

    threads = [threading.Thread(target=write, args=(f"job{i}",)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count(1) == 1
    assert sorted(r for r in results if r != 1) == [("stale", 1)] * 3
    assert cn.viewer_notify_settings(OWNER)[0] == 1


def test_an_unwritable_store_is_a_503(mute_env, monkeypatch):
    from api import cron_notifications as cn

    def _fail(data):
        raise OSError("read-only state dir")

    monkeypatch.setattr(cn, "_save_store", _fail)
    handler = mute_env.post({"job_id": "own-root", "in_app": "quiet", "revision": 0}, OWNER)
    assert handler.status == 503
    assert mute_env.get(OWNER).body == {"revision": 0, "jobs": {}}
