"""The integrations connect address has no built-in HQ default (PLAN 3.10, N3).

Before N3, ``api/integrations.py`` fell back to HQ's own integration host
whenever ``HERMES_WEBUI_NANGO_CONNECT_URL`` was unset, so every installation
without the variable built connect links to HQ. Now an unset (or unusable)
variable means "connecting apps is not set up here": the connect flow answers
a not-configured state, mints no session, records no approval and never
builds a URL. With the variable set the flow is unchanged.
"""
import io
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import config, integrations  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROVIDER = "google-drive"
USER = "user@example.test"
ADMIN = "admin@example.test"
CONNECT_URL = "https://connect.example.test:3009"
NOT_CONFIGURED_EN = "Connecting apps is not set up on this platform yet. Ask your administrator."
# Word-bounded on purpose: a plain substring grep also hits ``parts.netloc``.
HQ_HOST_RE = re.compile(r"\btailbdab77\b|\bts\.net\b")
NETWORK_PRODUCTS = ("Tailscale", "Funnel", "tailnet", "NetBird", "WireGuard", "Headscale")
DASHES = ("\u2013", "\u2014")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "webui")
    monkeypatch.delenv("HERMES_WEBUI_NANGO_CONNECT_URL", raising=False)
    yield tmp_path


@pytest.fixture
def nango(monkeypatch):
    """A Nango with one configured integration; every call is recorded."""
    calls = []

    def _list_integrations():
        calls.append(("GET", "/integrations", None))
        return [{"provider": PROVIDER, "unique_key": PROVIDER, "display_name": "Google Drive"}]

    def _request(method, path, *, payload=None, query=None):
        calls.append((method, path, payload))
        if path == "/connect/sessions":
            return {"data": {"token": "session-token", "expires_at": "2026-01-01T00:00:00Z"}}
        return {}

    def _no_dashboard(*_a, **_k):
        raise integrations.NangoError("no dashboard in this fixture")

    monkeypatch.setattr(integrations, "_list_integrations", _list_integrations)
    monkeypatch.setattr(integrations, "_nango_request", _request)
    monkeypatch.setattr(integrations, "_v1_integrations_by_key", _no_dashboard)
    monkeypatch.setattr(
        integrations,
        "load_provider_entries",
        lambda: {PROVIDER: {"display_name": "Google Drive", "categories": ["storage"]}},
    )
    return calls


def _approval_entry():
    from api import approvals
    return approvals.get("integration", PROVIDER)


# ── Without the variable: not configured, nothing built, nothing minted ─────

def test_no_builtin_connect_address():
    assert integrations._nango_connect_url() == ""
    assert not hasattr(integrations, "_DEFAULT_CONNECT_URL")


@pytest.mark.parametrize("is_admin", [False, True])
def test_connect_without_the_variable_answers_not_configured(nango, is_admin):
    result = integrations.create_connect_session(ADMIN if is_admin else USER, PROVIDER, is_admin=is_admin)

    assert result["status"] == integrations.CONNECT_STATUS_NOT_CONFIGURED == "not_configured"
    assert result["message_key"] == "integrations_connect_not_configured"
    assert result["message"] == NOT_CONFIGURED_EN
    assert "token" not in result
    assert not result.get("connect_url")
    assert not HQ_HOST_RE.search(json.dumps(result))
    # No Nango call at all (no session minted), and no approval bookkeeping:
    # neither an admin's implicit approval nor a user's pending request.
    assert nango == []
    assert _approval_entry() is None


@pytest.mark.parametrize("value", ["", "   ", "javascript:alert(1)", "ftp://connect.example.test", "https://", "not a url"])
def test_unusable_values_count_as_not_configured(nango, monkeypatch, value):
    monkeypatch.setenv("HERMES_WEBUI_NANGO_CONNECT_URL", value)
    assert integrations._nango_connect_url() == ""
    assert integrations.connect_configured() is False
    result = integrations.create_connect_session(ADMIN, PROVIDER, is_admin=True)
    assert result["status"] == "not_configured"
    assert nango == []


def test_missing_provider_key_is_still_a_400_first():
    with pytest.raises(ValueError):
        integrations.create_connect_session(USER, "  ")


# ── With the variable: exactly as before ─────────────────────────────────────

def test_connect_with_the_variable_uses_it_unchanged(nango, monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_NANGO_CONNECT_URL", CONNECT_URL + "/")
    assert integrations.connect_configured() is True
    assert integrations._nango_connect_url() == CONNECT_URL

    result = integrations.create_connect_session(ADMIN, PROVIDER, is_admin=True)

    assert result == {
        "status": integrations.CONNECT_STATUS_READY,
        "approval": integrations.APPROVAL_APPROVED,
        "token": "session-token",
        "connect_url": CONNECT_URL,
        "expires_at": "2026-01-01T00:00:00Z",
    }
    assert [c[1] for c in nango if c[1] == "/connect/sessions"] == ["/connect/sessions"]
    assert _approval_entry()["status"] == "approved"


def test_unapproved_user_with_the_variable_still_gets_a_pending_request(nango, monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_NANGO_CONNECT_URL", CONNECT_URL)
    result = integrations.create_connect_session(USER, PROVIDER)
    assert result["status"] == integrations.CONNECT_STATUS_PENDING
    assert "token" not in result
    assert _approval_entry()["status"] == "pending"


# ── The route answers the state (200, no URL) ────────────────────────────────

class _Handler:
    def __init__(self, body):
        raw = json.dumps(body).encode("utf-8")
        self.headers = {"Content-Length": str(len(raw)), "Content-Type": "application/json"}
        self.rfile = io.BytesIO(raw)
        self.wfile = io.BytesIO()
        self.status = None
        self.client_address = ("127.0.0.1", 0)
        self.request = None

    def send_response(self, status):
        self.status = status

    def send_header(self, *_a):
        pass

    def end_headers(self):
        pass

    def json_body(self):
        return json.loads(self.wfile.getvalue().decode("utf-8"))


def test_connect_route_answers_not_configured_without_a_url(nango, monkeypatch):
    from api import bot_builder, ownership, routes

    monkeypatch.setattr(bot_builder, "guard_profile_request", lambda *a, **k: True)
    monkeypatch.setattr(routes, "_check_csrf", lambda handler: True)
    monkeypatch.setattr(routes, "_guard_request_session_visibility", lambda *a, **k: True)
    monkeypatch.setattr(ownership, "request_owner_email", lambda handler: USER)
    monkeypatch.setattr(ownership, "request_is_admin", lambda handler: False)

    handler = _Handler({"provider_config_key": PROVIDER})
    routes.handle_post(handler, urlparse("/api/integrations/connect"))

    assert handler.status == 200
    body = handler.json_body()
    assert body["status"] == "not_configured"
    assert body["message_key"] == "integrations_connect_not_configured"
    assert not body.get("connect_url") and "token" not in body
    assert nango == []


# ── Copy and source checks ───────────────────────────────────────────────────

def test_not_configured_copy_matches_the_e5_key():
    en = (ROOT / "static" / "i18n" / "en.js").read_text(encoding="utf-8")
    assert "integrations_connect_not_configured: '" + NOT_CONFIGURED_EN + "'" in en
    assert not any(d in NOT_CONFIGURED_EN for d in DASHES)
    assert not any(p.lower() in NOT_CONFIGURED_EN.lower() for p in NETWORK_PRODUCTS)


def test_frontend_shows_the_not_configured_state():
    js = (ROOT / "static" / "integrations.js").read_text(encoding="utf-8")
    assert "=== 'not_configured'" in js
    assert "_intgT('integrations_connect_not_configured', '" + NOT_CONFIGURED_EN + "')" in js


def test_no_hq_address_in_api_or_static():
    hits = []
    for top in ("api", "static"):
        for path in sorted((ROOT / top).rglob("*")):
            if not path.is_file() or path.suffix not in {".py", ".js", ".html", ".css", ".json", ".md", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), 1):
                if HQ_HOST_RE.search(line):
                    hits.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()[:120]}")
    assert hits == []
