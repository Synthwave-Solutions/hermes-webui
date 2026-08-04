"""Auto profile-sync triggers: governance mutations and OIDC login kick the
background per-user Hermes profile provisioning (fire-and-forget subprocess).
"""
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import governance_api  # noqa: E402
from api.governance import loader, profile_sync  # noqa: E402


# ── trigger_profile_sync unit ───────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _enable_sync(monkeypatch):
    """conftest disables the sync globally for tests; re-enable it here so
    the trigger unit tests exercise the real code path (spawn is mocked)."""
    monkeypatch.delenv("HERMES_WEBUI_DISABLE_PROFILE_SYNC", raising=False)


class _ImmediateThread:
    """Thread stand-in that runs the target synchronously on start()."""

    def __init__(self, target=None, args=(), kwargs=None, **_ignored):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        self._target(*self._args, **self._kwargs)


def test_trigger_builds_user_scoped_command(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(profile_sync, "_spawn", lambda cmd, reason, email: calls.append((cmd, reason, email)))
    monkeypatch.setattr(profile_sync.threading, "Thread", _ImmediateThread)
    script = tmp_path / "sync.py"
    script.write_text("", encoding="utf-8")
    monkeypatch.setattr(profile_sync, "SYNC_SCRIPT", script)

    assert profile_sync.trigger_profile_sync("user@example.test", reason="user_update") is True
    (cmd, reason, email), = calls
    assert cmd[-3:] == ["--apply", "--user", "user@example.test"]
    assert str(script) in cmd
    assert reason == "user_update"
    assert email == "user@example.test"


def test_trigger_full_sync_has_no_user_flag(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(profile_sync, "_spawn", lambda cmd, reason, email: calls.append(cmd))
    monkeypatch.setattr(profile_sync.threading, "Thread", _ImmediateThread)
    script = tmp_path / "sync.py"
    script.write_text("", encoding="utf-8")
    monkeypatch.setattr(profile_sync, "SYNC_SCRIPT", script)

    assert profile_sync.trigger_profile_sync(None, reason="group_update") is True
    assert calls[0][-1] == "--apply"
    assert "--user" not in calls[0]


def test_trigger_noop_when_script_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(profile_sync, "SYNC_SCRIPT", tmp_path / "absent.py")
    assert profile_sync.trigger_profile_sync("user@example.test", reason="login") is False


# ── API hook wiring ─────────────────────────────────────────────────────────

BOOTSTRAP = "michael@example.test"

API_POLICY = {
    "version": 1,
    "mode": "report_only",
    "default_effect": "deny",
    "bootstrap_admins": [BOOTSTRAP],
    "roles": {
        "admin": {
            "grants": {
                "permissions": ["governance:read", "governance:write", "governance:preview"],
                "profiles": ["*"],
                "routes": ["*"],
            }
        },
        "viewer": {"grants": {"permissions": ["sessions:read"], "skills": {"load": ["a", "b"]}}},
    },
    "groups": {"crew": {"grants": {"skills": {"load": ["c"]}}}},
    "users": {
        "admin@example.test": {"roles": ["admin"]},
        "viewer@example.test": {"roles": ["viewer"]},
        BOOTSTRAP: {"roles": ["admin"]},
    },
}


class FakeHandler:
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


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_WEBUI_GOVERNANCE_POLICY", raising=False)
    loader.set_policy_loader(None)
    yield tmp_path
    loader.set_policy_loader(None)


@pytest.fixture
def policy_file(isolated_home):
    def _write(data=API_POLICY):
        path = isolated_home / "dashboard-governance.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return path
    return _write


@pytest.fixture
def as_admin(monkeypatch):
    identity = {"email": "admin@example.test", "groups": [], "claims_subset": {}, "method": "oidc"}
    monkeypatch.setattr(governance_api, "_caller_identity", lambda handler: identity)


@pytest.fixture
def sync_calls(monkeypatch):
    calls = []

    def _capture(email=None, *, reason=""):
        calls.append((email, reason))
        return True

    monkeypatch.setattr(governance_api, "trigger_profile_sync", _capture)
    return calls


def _call(path, body):
    handler = FakeHandler(
        body=body,
        headers={"If-Match": loader.policy_etag(dict(loader.get_policy().raw))},
    )
    governance_api.handle_governance_api(handler, SimpleNamespace(path=path, query=""), "POST")
    return handler


def test_user_update_triggers_scoped_sync(policy_file, as_admin, sync_calls):
    policy_file()
    handler = _call(
        "/api/governance/users/update",
        {"email": "viewer@example.test", "entry": {"roles": ["viewer"]}},
    )
    assert handler.status == 200
    assert sync_calls == [("viewer@example.test", "user_update")]


def test_user_create_triggers_scoped_sync(policy_file, as_admin, sync_calls):
    policy_file()
    handler = _call(
        "/api/governance/users",
        {"email": "new@example.test", "entry": {"roles": ["viewer"]}},
    )
    assert handler.status == 200
    assert sync_calls == [("new@example.test", "user_create")]


def test_group_update_triggers_full_sync(policy_file, as_admin, sync_calls):
    policy_file()
    handler = _call(
        "/api/governance/groups/update",
        {"name": "crew", "entry": {"grants": {"skills": {"load": ["c", "d"]}}}},
    )
    assert handler.status == 200
    assert sync_calls == [(None, "group_update")]


def test_user_delete_does_not_trigger_sync(policy_file, as_admin, sync_calls):
    policy_file()
    handler = _call(
        "/api/governance/users/delete",
        {"email": "viewer@example.test"},
    )
    assert handler.status == 200
    assert sync_calls == []


def test_failed_mutation_does_not_trigger_sync(policy_file, as_admin, sync_calls):
    policy_file()
    handler = _call(
        "/api/governance/users/update",
        {"email": "ghost@example.test", "entry": {"roles": ["viewer"]}},
    )
    assert handler.status == 404
    assert sync_calls == []


def test_policy_replace_triggers_full_sync(policy_file, as_admin, sync_calls):
    policy_file()
    new_policy = dict(API_POLICY)
    handler = _call("/api/governance/policy", new_policy)
    assert handler.status == 200
    assert sync_calls == [(None, "policy_replace")]
