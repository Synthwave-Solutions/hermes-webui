"""Tests for the mandatory two-step login (SSO first, then password).

Feature: when HERMES_WEBUI_REQUIRE_SSO_FIRST is on, a user must complete Google
OIDC AND then enter the dashboard password before a full session is created.
Password-only login (no prior SSO in this browser) is refused.

The toggle is DEFAULT OFF; with it off the login flow is unchanged (no
regressions), which the "toggle OFF" tests below pin.

Style mirrors tests/test_issue3825_oidc_auth.py (RouteFakeHandler) and
tests/test_auth_sessions.py (direct api.auth calls under an isolated STATE_DIR).
"""
import io
import json
import os
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

# Isolate the state dir so we never touch real sessions/keys.
_TEST_STATE = Path(tempfile.mkdtemp())
os.environ.setdefault("HERMES_WEBUI_STATE_DIR", str(_TEST_STATE))

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api.auth as auth  # noqa: E402
import api.auth_oidc as auth_oidc  # noqa: E402
import api.routes as routes  # noqa: E402


class FakeHeaders(dict):
    def get(self, key, default=None):
        # Case-insensitive lookup like http.server headers.
        for k, v in self.items():
            if k.lower() == str(key).lower():
                return v
        return default


class RouteFakeHandler:
    """Minimal handler compatible with handle_get / handle_post / auth helpers."""

    def __init__(self, *, cookie=None, body=None, client_address=("127.0.0.1", 12345)):
        headers = {"Host": "localhost:8787"}
        if cookie:
            headers["Cookie"] = cookie
        raw = json.dumps(body or {}).encode("utf-8")
        headers["Content-Length"] = str(len(raw))
        self.headers = FakeHeaders(headers)
        self.request = SimpleNamespace()
        self.rfile = io.BytesIO(raw)
        self.wfile = io.BytesIO()
        self.client_address = client_address
        self.status = None
        self.sent_headers = []
        self.close_connection = False

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.sent_headers.append((key, value))

    def end_headers(self):
        pass

    def json_body(self):
        return json.loads(self.wfile.getvalue().decode("utf-8"))

    def header_values(self, name):
        needle = name.lower()
        return [value for key, value in self.sent_headers if key.lower() == needle]

    def set_cookie_for(self, name):
        """Return the first Set-Cookie header value that sets *name*."""
        for value in self.header_values("Set-Cookie"):
            if value.startswith(name + "="):
                return value
        return None


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Reset in-memory stores + password + toggle before each test."""
    auth._sessions.clear()
    auth._sso_pending.clear()
    monkeypatch.delenv("HERMES_WEBUI_REQUIRE_SSO_FIRST", raising=False)
    # A known password for the login handler.
    monkeypatch.setenv("HERMES_WEBUI_PASSWORD", "correct horse battery staple")
    auth._invalidate_password_hash_cache()
    # Rate limiter should never interfere.
    monkeypatch.setattr(auth, "_check_login_rate", lambda ip: True)
    monkeypatch.setattr(auth, "_record_login_attempt", lambda ip: None)
    monkeypatch.setattr(auth, "_clear_login_attempts", lambda ip: None)
    yield
    auth._sessions.clear()
    auth._sso_pending.clear()


def _identity(email="user@synthwave.solutions", groups=None):
    return {
        "email": email,
        "groups": list(groups or ["hd:synthwave.solutions"]),
        "claims_subset": {"sub": "abc123", "email": email},
    }


# ── Toggle helper ────────────────────────────────────────────────────────────


def test_require_sso_first_default_off_and_truthy_parsing(monkeypatch):
    monkeypatch.delenv("HERMES_WEBUI_REQUIRE_SSO_FIRST", raising=False)
    assert auth.require_sso_first() is False
    for truthy in ("1", "true", "yes", "on", "TRUE", "On"):
        monkeypatch.setenv("HERMES_WEBUI_REQUIRE_SSO_FIRST", truthy)
        assert auth.require_sso_first() is True
    for falsy in ("0", "false", "no", "off", ""):
        monkeypatch.setenv("HERMES_WEBUI_REQUIRE_SSO_FIRST", falsy)
        assert auth.require_sso_first() is False


# ── Toggle OFF: unchanged behavior ───────────────────────────────────────────


def test_toggle_off_oidc_callback_creates_full_session(monkeypatch):
    monkeypatch.setattr(
        "api.auth_oidc.complete_authorization_code_flow",
        lambda *_a: {"next_path": "/chat/1"},
    )
    monkeypatch.setattr(auth, "create_session", lambda: "sess-token.sig")

    handler = RouteFakeHandler()
    routes.handle_get(
        handler,
        SimpleNamespace(path="/api/auth/oidc/callback", query="state=s&code=c"),
    )

    assert handler.status == 302
    # A full auth session cookie is set, no pending cookie.
    assert handler.set_cookie_for(auth.COOKIE_NAME) is not None
    assert handler.set_cookie_for(auth.SSO_PENDING_COOKIE_NAME) is None
    assert handler.header_values("Location") == ["/chat/1"]


def test_toggle_off_password_login_works_standalone():
    handler = RouteFakeHandler(body={"password": "correct horse battery staple"})
    routes.handle_post(handler, SimpleNamespace(path="/api/auth/login", query=""))
    assert handler.status == 200
    assert handler.json_body() == {"ok": True}
    cookie = handler.set_cookie_for(auth.COOKIE_NAME)
    assert cookie is not None
    # The cookie value is a real, verifiable session.
    value = cookie.split("=", 1)[1].split(";", 1)[0]
    assert auth.verify_session(value)


# ── Toggle ON: two-step behavior ─────────────────────────────────────────────


def test_toggle_on_oidc_callback_sets_pending_and_no_session(monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_REQUIRE_SSO_FIRST", "1")

    ident = _identity()

    def fake_flow(*_a):
        # Real flow stages identity on the thread for create_session().
        auth.stage_session_identity({**ident, "method": "oidc"})
        return {"next_path": "/projects", **ident}

    monkeypatch.setattr("api.auth_oidc.complete_authorization_code_flow", fake_flow)

    handler = RouteFakeHandler()
    routes.handle_get(
        handler,
        SimpleNamespace(path="/api/auth/oidc/callback", query="state=s&code=c"),
    )

    assert handler.status == 302
    # NO full session cookie.
    assert handler.set_cookie_for(auth.COOKIE_NAME) is None
    # A pending cookie is set, and it redirects to /login preserving next.
    pending = handler.set_cookie_for(auth.SSO_PENDING_COOKIE_NAME)
    assert pending is not None
    assert "HttpOnly" in pending
    [location] = handler.header_values("Location")
    assert location.startswith("/login")
    assert "next=/projects" in location
    # The pending entry carries the SSO identity.
    pending_value = pending.split("=", 1)[1].split(";", 1)[0]
    stored = auth.verify_sso_pending(pending_value)
    assert stored is not None
    assert stored["email"] == ident["email"]
    assert "hd:synthwave.solutions" in stored["groups"]


def test_toggle_on_login_page_no_pending_hides_password(monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_REQUIRE_SSO_FIRST", "1")
    monkeypatch.setattr("api.auth_oidc.is_oidc_enabled", lambda: True)
    captured = {}
    monkeypatch.setattr(
        routes,
        "t",
        lambda _h, body, *, content_type=None, **_k: captured.update({"body": body})
        or True,
    )

    handler = RouteFakeHandler()
    routes.handle_get(handler, SimpleNamespace(path="/login", query=""))

    html = captured["body"]
    # SSO button present, password input absent.
    assert 'id="oidc-login"' in html
    assert 'id="pw"' not in html
    assert "Sign in with Google to continue" in html


def test_toggle_on_login_page_with_pending_shows_password_and_email(monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_REQUIRE_SSO_FIRST", "1")
    monkeypatch.setattr("api.auth_oidc.is_oidc_enabled", lambda: True)
    pending_cookie = auth.create_sso_pending(_identity(email="alice@synthwave.solutions"))

    captured = {}
    monkeypatch.setattr(
        routes,
        "t",
        lambda _h, body, *, content_type=None, **_k: captured.update({"body": body})
        or True,
    )

    handler = RouteFakeHandler(
        cookie=f"{auth.SSO_PENDING_COOKIE_NAME}={pending_cookie}"
    )
    routes.handle_get(handler, SimpleNamespace(path="/login", query=""))

    html = captured["body"]
    assert 'id="pw"' in html  # password step shown
    assert "alice@synthwave.solutions" in html
    assert "via Google" in html


def test_toggle_on_login_page_escapes_pending_email(monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_REQUIRE_SSO_FIRST", "1")
    monkeypatch.setattr("api.auth_oidc.is_oidc_enabled", lambda: True)
    pending_cookie = auth.create_sso_pending(
        _identity(email='<script>x</script>@evil.test')
    )
    captured = {}
    monkeypatch.setattr(
        routes,
        "t",
        lambda _h, body, *, content_type=None, **_k: captured.update({"body": body})
        or True,
    )
    handler = RouteFakeHandler(
        cookie=f"{auth.SSO_PENDING_COOKIE_NAME}={pending_cookie}"
    )
    routes.handle_get(handler, SimpleNamespace(path="/login", query=""))
    assert "<script>x</script>" not in captured["body"]
    assert "&lt;script&gt;" in captured["body"]


def test_toggle_on_password_without_pending_rejected(monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_REQUIRE_SSO_FIRST", "1")

    handler = RouteFakeHandler(body={"password": "correct horse battery staple"})
    routes.handle_post(handler, SimpleNamespace(path="/api/auth/login", query=""))

    assert handler.status == 401
    assert handler.json_body()["error"] == "sso_required"
    # No session cookie handed out.
    assert handler.set_cookie_for(auth.COOKIE_NAME) is None


def test_toggle_on_password_without_pending_does_not_check_password(monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_REQUIRE_SSO_FIRST", "1")
    called = {"verify": False}

    def _spy(_pw):
        called["verify"] = True
        return True

    monkeypatch.setattr(auth, "verify_password", _spy)
    handler = RouteFakeHandler(body={"password": "whatever"})
    routes.handle_post(handler, SimpleNamespace(path="/api/auth/login", query=""))
    assert handler.status == 401
    assert called["verify"] is False  # rejected before password check


def test_toggle_on_full_flow_creates_session_with_sso_identity(monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_REQUIRE_SSO_FIRST", "1")
    ident = _identity(email="bob@synthwave.solutions", groups=["hd:synthwave.solutions", "ops"])
    pending_cookie = auth.create_sso_pending(ident)
    pending_token = auth._sso_pending_token(pending_cookie)
    assert pending_token in auth._sso_pending

    handler = RouteFakeHandler(
        cookie=f"{auth.SSO_PENDING_COOKIE_NAME}={pending_cookie}",
        body={"password": "correct horse battery staple"},
    )
    routes.handle_post(handler, SimpleNamespace(path="/api/auth/login", query=""))

    assert handler.status == 200
    assert handler.json_body() == {"ok": True}
    # Full session cookie set + verifiable.
    session_cookie = handler.set_cookie_for(auth.COOKIE_NAME)
    assert session_cookie is not None
    session_value = session_cookie.split("=", 1)[1].split(";", 1)[0]
    assert auth.verify_session(session_value)
    session_identity = auth.get_session_identity(session_value)
    assert session_identity["email"] == "bob@synthwave.solutions"
    assert "hd:synthwave.solutions" in session_identity["groups"]
    assert "ops" in session_identity["groups"]
    assert session_identity["method"] == "sso+password"
    # The pending token has been consumed (deleted).
    assert pending_token not in auth._sso_pending
    # The pending cookie is cleared.
    cleared = handler.set_cookie_for(auth.SSO_PENDING_COOKIE_NAME)
    assert cleared is not None
    assert "Max-Age=0" in cleared


# ── Pending cookie tamper resistance ─────────────────────────────────────────


def test_pending_cookie_bad_signature_rejected():
    good = auth.create_sso_pending(_identity())
    token, _sig = good.rsplit(".", 1)
    tampered = f"{token}.deadbeef"
    assert auth.verify_sso_pending(tampered) is None
    assert auth.consume_sso_pending(tampered) is None


def test_pending_cookie_unknown_token_rejected():
    # Correctly signed but never stored token.
    import hashlib
    import hmac

    fake_token = "0" * 64
    sig = hmac.new(auth._signing_key(), fake_token.encode(), hashlib.sha256).hexdigest()
    assert auth.verify_sso_pending(f"{fake_token}.{sig}") is None


def test_pending_cookie_expired_rejected(monkeypatch):
    good = auth.create_sso_pending(_identity())
    token = auth._sso_pending_token(good)
    # Force the stored entry to be expired.
    auth._sso_pending[token]["exp"] = time.time() - 1
    assert auth.verify_sso_pending(good) is None


def test_consume_deletes_entry():
    good = auth.create_sso_pending(_identity())
    token = auth._sso_pending_token(good)
    assert token in auth._sso_pending
    ident = auth.consume_sso_pending(good)
    assert ident is not None
    assert token not in auth._sso_pending
    # Second consume returns None.
    assert auth.consume_sso_pending(good) is None


# ── hd pseudo-group ──────────────────────────────────────────────────────────


def test_hd_claim_yields_pseudo_group():
    claims = {
        "sub": "s1",
        "email": "carol@synthwave.solutions",
        "hd": "synthwave.solutions",
        "groups": ["ops"],
    }
    identity = auth_oidc._identity_from_claims(claims)
    assert "hd:synthwave.solutions" in identity["groups"]
    assert "ops" in identity["groups"]
    assert identity["email"] == "carol@synthwave.solutions"


def test_hd_claim_absent_no_pseudo_group():
    claims = {"sub": "s1", "email": "dan@example.test", "groups": ["ops"]}
    identity = auth_oidc._identity_from_claims(claims)
    assert not any(g.startswith("hd:") for g in identity["groups"])


def test_hd_pseudo_group_not_duplicated():
    claims = {
        "sub": "s1",
        "email": "e@synthwave.solutions",
        "hd": "synthwave.solutions",
        "groups": ["hd:synthwave.solutions"],
    }
    identity = auth_oidc._identity_from_claims(claims)
    assert identity["groups"].count("hd:synthwave.solutions") == 1
