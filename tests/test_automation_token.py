"""Automation service token: narrow bearer auth for the inbound-offer helper.

Offline: fake handlers only, state in tmp_path, no live server.
"""
import hmac
import io
import json
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

import api.auth as auth
import api.automation_token as at
import api.config as api_config
import api.routes as routes
from api.governance import enforce

OWNER = "yaser@example.test"
OTHER = "other@example.test"


class _H:
    def __init__(self, method="POST", path="/api/session/import", headers=None,
                 ip="127.0.0.1", body=b"{}"):
        self.command = method
        self.path = path
        self.headers = headers or {}
        self.client_address = (ip, 4000)
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.status = None
        self.sent_headers = {}

    def send_response(self, status):
        self.status = status

    def send_header(self, k, v):
        self.sent_headers[k] = v

    def end_headers(self):
        pass


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(api_config, "STATE_DIR", tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(auth, "_signing_key", lambda: b"k" * 32)
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth, "_login_attempts", {})
    monkeypatch.setattr(auth, "_save_login_attempts", lambda a: None)
    import api.group_chat as gc
    monkeypatch.setattr(gc, "known_emails", lambda: {OWNER, OTHER})
    return tmp_path


def _call(token, method="POST", path="/api/session/import", ip="127.0.0.1", extra=None):
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    headers.update(extra or {})
    h = _H(method, path, headers, ip)
    ok = auth.check_auth(h, urlparse(path))
    return h, ok


def _audit_rows(env):
    f = env / "home" / "dashboard-governance-audit.jsonl"
    if not f.exists():
        return []
    return [json.loads(x) for x in f.read_text().splitlines() if x.strip()]


def test_create_stores_only_hash_with_0600(env):
    token = at.create(OWNER, "inbound", 30)
    p = env / "automation_token.json"
    assert oct(p.stat().st_mode & 0o777) == "0o600"
    raw = p.read_text()
    assert token not in raw
    data = json.loads(raw)
    assert data["owner_email"] == OWNER and data["label"] == "inbound"
    assert data["expires_at"] and data["session_ids"] == []
    assert at.status()["active"] is True
    assert token not in json.dumps(at.status())


def test_create_rejects_unknown_owner_and_second_active(env):
    with pytest.raises(ValueError):
        at.create("nobody@example.test", "x")
    at.create(OWNER, "x")
    with pytest.raises(ValueError):
        at.create(OWNER, "y")
    assert at.create(OWNER, "y", rotate=True)


def test_valid_token_on_allowlisted_routes(env):
    token = at.create(OWNER, "inbound")
    for method, path in [("POST", "/api/session/import"),
                         ("POST", "/api/session/participants"),
                         ("POST", "/api/session/delete")]:
        h, ok = _call(token, method, path)
        assert ok, path
        assert at.get_ctx(h)["owner_email"] == OWNER
        assert enforce._request_identity(h)["email"] == OWNER
    at.record_session("sess1")
    for path in ("/api/session?session_id=sess1", "/api/file/raw?session_id=sess1&path=a"):
        h, ok = _call(token, "GET", path)
        assert ok, path


def test_wrong_token_is_401_and_counts_against_rate_limit(env):
    at.create(OWNER, "inbound")
    h, ok = _call("hat_wrong")
    assert not ok and h.status == 401
    for _ in range(6):
        _call("hat_wrong")
    h, ok = _call("hat_wrong")
    assert not ok and h.status == 429


def test_no_stored_token_fails_closed(env):
    h, ok = _call("anything")
    assert not ok and h.status == 401


def test_expired_token_rejected(env):
    token = at.create(OWNER, "inbound", 1)
    p = env / "automation_token.json"
    d = json.loads(p.read_text())
    d["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    p.write_text(json.dumps(d))
    h, ok = _call(token)
    assert not ok and h.status == 401


def test_revoked_token_rejected_on_next_request(env):
    token = at.create(OWNER, "inbound")
    assert _call(token)[1]
    at.revoke()
    h, ok = _call(token)
    assert not ok and h.status == 401
    assert at.status()["active"] is False


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/sessions"),
    ("POST", "/api/session/import_cli"),
    ("GET", "/api/governance/policy"),
    ("POST", "/api/settings"),
    ("POST", "/api/chat/start"),
    ("GET", "/health"),
    ("GET", "/api/auth/status"),
    ("POST", "/api/auth/login"),
    ("GET", "/static/app.js"),
    ("GET", "/api/session/delete"),
])
def test_non_allowlisted_route_is_403(env, method, path):
    token = at.create(OWNER, "inbound")
    h, ok = _call(token, method, path)
    assert not ok and h.status == 403


@pytest.mark.parametrize("ip", ["10.0.0.5", "192.168.1.9", "100.64.0.3", "not-an-ip"])
def test_non_loopback_is_403(env, ip):
    token = at.create(OWNER, "inbound")
    h, ok = _call(token, ip=ip)
    assert not ok and h.status == 403


def test_forwarded_request_is_403(env):
    token = at.create(OWNER, "inbound")
    h, ok = _call(token, extra={"X-Forwarded-For": "203.0.113.1"})
    assert not ok and h.status == 403


def test_query_routes_limited_to_own_sessions(env):
    token = at.create(OWNER, "inbound")
    for path in ("/api/session?session_id=foreign", "/api/file/raw?session_id=foreign&path=a",
                 "/api/session", "/api/session?session_id="):
        h, ok = _call(token, "GET", path)
        assert not ok and h.status == 403, path


def test_delete_limited_to_own_sessions(env):
    token = at.create(OWNER, "inbound")
    h, ok = _call(token, "POST", "/api/session/delete")
    assert ok
    assert not at.session_gate(h, "foreign")
    at.record_session("mine")
    assert at.session_gate(h, "mine")
    # a non-bearer request is never limited by the gate
    assert at.session_gate(_H(), "foreign")
    at.revoke()
    assert not at.session_gate(h, "mine")


def test_bearer_skips_csrf_but_cookie_still_requires_it(env):
    token = at.create(OWNER, "inbound")
    h, ok = _call(token)
    assert ok
    h.headers.update({"Origin": "http://evil.example", "Host": "127.0.0.1:8787"})
    assert routes._check_csrf(h) is True  # bearer on allowlisted route

    raw = "d" * 64
    sig = hmac.new(auth._signing_key(), raw.encode(), "sha256").hexdigest()
    auth._sessions[raw] = time.time() + 60
    try:
        cookie = f"{raw}.{sig}"
        hc = _H(headers={"Origin": "http://127.0.0.1:8787", "Host": "127.0.0.1:8787",
                         "Cookie": f"{auth.COOKIE_NAME}={cookie}"})
        assert not routes._check_csrf(hc)  # no token: still rejected
        hc.headers[auth.CSRF_HEADER_NAME] = auth.csrf_token_for_session(cookie)
        assert routes._check_csrf(hc)
    finally:
        auth._sessions.pop(raw, None)


def test_ctx_not_inherited_by_cookie_request(env):
    token = at.create(OWNER, "inbound")
    h, ok = _call(token)
    assert ok and at.get_ctx(h)
    # same handler object reused for a cookie request (keep-alive): ctx resets
    h.headers = {}
    auth.check_auth(h, urlparse("/api/sessions"))
    assert at.get_ctx(h) is None


def test_owner_override_in_body_is_ignored(env, monkeypatch):
    token = at.create(OWNER, "inbound")
    h, ok = _call(token)
    assert ok
    seen = {}

    class _S:
        def __init__(self, **kw):
            seen.update(kw)
            self.session_id = "newsess"
            self.messages = kw.get("messages")
            self.pinned = False

        def save(self):
            pass

        def compact(self):
            return {"session_id": self.session_id}

    monkeypatch.setattr(routes, "Session", _S)
    monkeypatch.setattr(routes, "resolve_trusted_workspace", lambda w: w)
    monkeypatch.setattr(routes, "publish_session_list_changed", lambda *a, **k: None)
    monkeypatch.setattr(routes, "_evict_sessions_over_cap", lambda: None)
    monkeypatch.setattr("api.workspace_access.ensure_workspace_selection", lambda *a, **k: None)
    monkeypatch.setattr(routes, "j", lambda handler, payload, **k: payload)
    body = {"messages": [], "owner_email": OTHER, "owner": OTHER, "title": "t"}
    routes._handle_session_import(h, body)
    assert seen["owner_email"] == OWNER
    assert json.loads((env / "automation_token.json").read_text())["session_ids"] == ["newsess"]


def test_admin_only_route_unreachable(env):
    token = at.create(OWNER, "inbound")
    for path in ("/api/governance/policy", "/api/updates/apply", "/api/shutdown"):
        h, ok = _call(token, "POST", path)
        assert not ok and h.status == 403


def test_audit_has_route_session_outcome_label_and_no_token(env, caplog):
    token = at.create(OWNER, "inbound-label")
    with caplog.at_level("DEBUG"):
        _call(token)
        _call(token + "x")
        _call(token, "GET", "/api/sessions")
        at.record_session("s1")
        h, _ = _call(token, "GET", "/api/session?session_id=s1")
    rows = [r for r in _audit_rows(env) if r["event"] == "automation_token_request"]
    outcomes = [r["extra"]["outcome"] for r in rows]
    assert "accepted" in outcomes and "denied_invalid_token" in outcomes
    assert "denied_route_not_allowed" in outcomes
    ok_rows = [r for r in rows if r["extra"]["outcome"] == "accepted"]
    assert ok_rows[0]["extra"]["label"] == "inbound-label"
    assert any(r["extra"]["session_id"] == "s1" for r in ok_rows)
    blob = json.dumps(rows) + caplog.text
    assert token not in blob
    assert token not in (env / "automation_token.json").read_text()
    for h in (h,):
        assert token not in json.dumps(h.sent_headers)


def test_script_create_prints_token_once_status_never(env, capsys, monkeypatch):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "automation_token_cli", Path(api_config.__file__).parent.parent / "scripts" / "automation_token.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    assert cli.main(["create", "--owner", OWNER, "--label", "inbound", "--days", "30"]) == 0
    token = capsys.readouterr().out.strip()
    assert token.startswith("hat_")
    assert cli.main(["status"]) == 0
    assert token not in capsys.readouterr().out
    assert cli.main(["revoke"]) == 0
    assert at.status()["active"] is False
    assert cli.main(["create", "--owner", "nobody@example.test", "--label", "x"]) == 2
