"""Approval gate in front of self-service installs (integrations + MCP).

Covers api/integrations.py (connect is gated on an admin-approved provider,
admins bypass and implicitly approve, catalog carries the approval field) and
api/mcp_requests.py + its routes (a user requests a remote MCP server, an
approved request is installed into the profile config.yaml with an audit
line, secrets never enter the registry).
"""
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import approvals, config, integrations, mcp_requests, routes  # noqa: E402
from api.governance.audit import read_audit_events  # noqa: E402
from api.governance.catalog import _SELF_ROUTES, route_permission  # noqa: E402

PROVIDER = "google-drive"
USER = "user@example.test"
ADMIN = "admin@example.test"


class FakeHandler:
    def __init__(self, body=None):
        raw = json.dumps(body).encode("utf-8") if body is not None else b""
        self.headers = {}
        if raw:
            self.headers["Content-Length"] = str(len(raw))
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
    """STATE_DIR (approvals.json), HERMES_HOME (audit log) and config.yaml."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "webui")
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump({"mcp_servers": {}}), encoding="utf-8")
    monkeypatch.setenv("HERMES_CONFIG_PATH", str(cfg_path))
    config.reload_config()
    yield tmp_path
    monkeypatch.delenv("HERMES_CONFIG_PATH", raising=False)
    config.reload_config()


@pytest.fixture
def nango(monkeypatch):
    """A Nango with one configured integration and a recording request client."""
    calls = []

    def _list_integrations():
        return [{
            "provider": PROVIDER,
            "unique_key": PROVIDER,
            "display_name": "Google Drive",
        }]

    def _request(method, path, *, payload=None, query=None):
        calls.append((method, path, payload))
        if path == "/connect/sessions":
            return {"data": {"token": "session-token", "expires_at": "2026-01-01T00:00:00Z"}}
        return {}

    monkeypatch.setattr(integrations, "_list_integrations", _list_integrations)
    monkeypatch.setattr(integrations, "_nango_request", _request)
    monkeypatch.setattr(
        integrations,
        "load_provider_entries",
        lambda: {PROVIDER: {"display_name": "Google Drive", "categories": ["storage"]}},
    )
    return calls


def _sessions(calls):
    return [c for c in calls if c[1] == "/connect/sessions"]


# ── Integrations: the gate ──────────────────────────────────────────────────

def test_unapproved_provider_yields_a_pending_request_not_a_session(nango):
    result = integrations.create_connect_session(USER, PROVIDER)

    assert result["status"] == integrations.CONNECT_STATUS_PENDING
    assert "token" not in result
    assert _sessions(nango) == []
    entry = approvals.get("integration", PROVIDER)
    assert entry["status"] == "pending"
    assert entry["owner_email"] == USER
    assert entry["label"] == "Google Drive"


def test_second_request_is_idempotent(nango):
    first = integrations.create_connect_session(USER, PROVIDER)
    second = integrations.create_connect_session("other@example.test", PROVIDER)

    assert second["status"] == integrations.CONNECT_STATUS_PENDING
    assert second["requested_at"] == first["requested_at"]
    assert approvals.get("integration", PROVIDER)["owner_email"] == USER
    # The requester's email is only exposed to the owner and to admins.
    assert second["approval_owner"] is None
    assert first["approval_owner"] == USER


def test_approved_provider_connects_exactly_as_before(nango):
    integrations.create_connect_session(USER, PROVIDER)
    approvals.decide("integration", PROVIDER, "approve", ADMIN)

    result = integrations.create_connect_session(USER, PROVIDER)

    assert result["status"] == integrations.CONNECT_STATUS_READY
    assert result["token"] == "session-token"
    assert result["connect_url"]
    assert result["expires_at"] == "2026-01-01T00:00:00Z"
    assert len(_sessions(nango)) == 1
    # Approval is global: a different user connects without a new request.
    other = integrations.create_connect_session("other@example.test", PROVIDER)
    assert other["status"] == integrations.CONNECT_STATUS_READY


def test_admin_connect_bypasses_and_implicitly_approves_globally(nango):
    result = integrations.create_connect_session(ADMIN, PROVIDER, is_admin=True)

    assert result["status"] == integrations.CONNECT_STATUS_READY
    assert result["token"] == "session-token"
    entry = approvals.get("integration", PROVIDER)
    assert entry["status"] == "approved"
    assert entry["decided_by"] == ADMIN
    # Next (non-admin) user is one-click.
    assert integrations.create_connect_session(USER, PROVIDER)["status"] == "ready"


def test_admin_connect_without_identity_still_records_the_approval(nango):
    integrations.create_connect_session(None, PROVIDER, is_admin=True)

    entry = approvals.get("integration", PROVIDER)
    assert entry["status"] == "approved"
    assert entry["owner_email"] == "admin"


def test_rejected_provider_is_403_with_the_reason(nango):
    integrations.create_connect_session(USER, PROVIDER)
    approvals.decide("integration", PROVIDER, "reject", ADMIN, reason="no budget")

    with pytest.raises(PermissionError) as exc:
        integrations.create_connect_session(USER, PROVIDER)
    assert "no budget" in str(exc.value)
    assert _sessions(nango) == []


def test_unknown_provider_still_400s_before_any_approval_bookkeeping(nango):
    with pytest.raises(ValueError):
        integrations.create_connect_session(USER, "not-in-nango")
    assert approvals.get("integration", "not-in-nango") is None


def test_catalog_carries_the_approval_field(nango):
    catalog = integrations.get_catalog(USER)
    item = next(p for p in catalog["providers"] if p["key"] == PROVIDER)
    assert item["configured"] is True
    assert item["approval"] == "none"
    assert item["approval_status"] is None

    integrations.request_provider_approval(USER, PROVIDER)
    item = next(p for p in integrations.get_catalog(USER)["providers"] if p["key"] == PROVIDER)
    assert item["approval"] == "pending"
    assert item["requested_by_me"] is True

    approvals.decide("integration", PROVIDER, "approve", ADMIN)
    item = next(p for p in integrations.get_catalog(USER)["providers"] if p["key"] == PROVIDER)
    assert item["approval"] == "approved"
    assert item["approval_status"] == "approved"


def test_catalog_without_arguments_keeps_working(nango):
    catalog = integrations.get_catalog()
    assert catalog["nango"]["available"] is True
    assert all("approval" in p for p in catalog["providers"])


def test_rejected_provider_reads_as_none_with_the_raw_status(nango):
    integrations.request_provider_approval(USER, PROVIDER)
    approvals.decide("integration", PROVIDER, "reject", ADMIN, reason="not allowed")

    item = next(p for p in integrations.get_catalog(USER)["providers"] if p["key"] == PROVIDER)
    assert item["approval"] == "none"
    assert item["approval_status"] == "rejected"
    assert item["approval_reason"] == "not allowed"


def test_request_endpoint_reports_the_real_state(nango):
    pending = integrations.request_provider_approval(USER, PROVIDER)
    assert pending["status"] == integrations.CONNECT_STATUS_PENDING

    approvals.decide("integration", PROVIDER, "approve", ADMIN)
    approved = integrations.request_provider_approval(USER, PROVIDER)
    assert approved["status"] == "approved"


def test_listing_and_deleting_connections_is_untouched(nango, monkeypatch):
    monkeypatch.setattr(
        integrations,
        "_nango_request",
        lambda method, path, *, payload=None, query=None: {
            "connections": [{
                "connection_id": "c1",
                "provider_config_key": PROVIDER,
                "end_user": {"id": integrations.end_user_id(USER)},
            }]
        },
    )
    rows = integrations.list_connections(USER)
    assert rows[0]["connection_id"] == "c1"


# ── MCP: requesting ─────────────────────────────────────────────────────────

def test_mcp_request_stores_no_secret(isolated_home):
    entry = mcp_requests.request_server(
        USER, "context7", "https://mcp.example.test/sse", auth_header="Authorization"
    )
    assert entry["status"] == "pending"
    assert entry["payload"]["url"] == "https://mcp.example.test/sse"
    assert entry["payload"]["auth_header"] == "Authorization"
    raw = (config.STATE_DIR / "approvals.json").read_text(encoding="utf-8")
    assert "secret" not in raw.lower()


@pytest.mark.parametrize("body", [
    {"headers": {"Authorization": "Bearer x"}},
    {"command": "npx"},
    {"env": {"TOKEN": "x"}},
    {"auth_value": "Bearer x"},
])
def test_mcp_request_rejects_secrets_and_stdio(body):
    with pytest.raises(ValueError):
        mcp_requests.reject_secret_fields(body)


@pytest.mark.parametrize("url", ["", "ftp://x/y", "notaurl", "http://"])
def test_mcp_request_rejects_bad_urls(url):
    with pytest.raises(ValueError):
        mcp_requests.request_server(USER, "srv", url)


@pytest.mark.parametrize("name", ["", "../etc/passwd", "a:b", "x" * 80])
def test_mcp_request_rejects_bad_names(name):
    with pytest.raises(ValueError):
        mcp_requests.request_server(USER, name, "https://ok.example.test")


def test_mcp_request_without_identity_is_403():
    with pytest.raises(PermissionError):
        mcp_requests.request_server("", "srv", "https://ok.example.test")


# ── MCP: installing approved requests ───────────────────────────────────────

def _servers():
    config.reload_config()
    return config.get_config().get("mcp_servers") or {}


def test_pending_request_installs_nothing(isolated_home):
    mcp_requests.request_server(USER, "context7", "https://mcp.example.test/sse")
    result = mcp_requests.sync_approved(ADMIN)
    assert result == {"installed": [], "skipped": [], "changed": False}
    assert _servers() == {}


def test_approved_request_is_written_into_the_config_with_an_audit_line(isolated_home):
    mcp_requests.request_server(USER, "context7", "https://mcp.example.test/sse")
    approvals.decide("mcp", "context7", "approve", ADMIN)

    result = mcp_requests.sync_approved(ADMIN)

    assert result["changed"] is True
    assert result["installed"][0]["name"] == "context7"
    servers = _servers()
    assert servers["context7"]["url"] == "https://mcp.example.test/sse"
    # No auth header requested: usable straight away.
    assert "enabled" not in servers["context7"]
    events = [e for e in read_audit_events(50) if e["event"] == "mcp_server_install"]
    assert events and events[0]["extra"]["target"] == "context7"


def test_request_with_an_auth_header_installs_disabled_and_empty(isolated_home):
    mcp_requests.request_server(
        USER, "context7", "https://mcp.example.test/sse", auth_header="Authorization"
    )
    approvals.decide("mcp", "context7", "approve", ADMIN)

    result = mcp_requests.sync_approved(ADMIN)

    assert result["installed"][0]["needs_secret"] is True
    servers = _servers()
    assert servers["context7"]["headers"] == {"Authorization": ""}
    assert servers["context7"]["enabled"] is False


def test_sync_is_idempotent_and_never_overwrites_an_admin_entry(isolated_home):
    mcp_requests.request_server(USER, "context7", "https://mcp.example.test/sse")
    approvals.decide("mcp", "context7", "approve", ADMIN)
    mcp_requests.sync_approved(ADMIN)

    # An admin edits the installed server; a second sync must not undo it.
    cfg = config.get_config()
    cfg["mcp_servers"]["context7"]["url"] = "https://edited.example.test/sse"
    config._save_yaml_config_file(config._get_config_path(), cfg)
    config.reload_config()

    again = mcp_requests.sync_approved(ADMIN)
    assert again["changed"] is False
    assert again["skipped"][0]["reason"] == "already_configured"
    assert _servers()["context7"]["url"] == "https://edited.example.test/sse"


def test_deleting_an_installed_server_revokes_its_approval(isolated_home):
    mcp_requests.request_server(USER, "context7", "https://mcp.example.test/sse")
    approvals.decide("mcp", "context7", "approve", ADMIN)
    mcp_requests.sync_approved(ADMIN)

    handler = FakeHandler()
    routes._handle_mcp_server_delete(handler, "context7")
    assert handler.status == 200
    assert approvals.get("mcp", "context7") is None
    # ... and the next sync does not resurrect it.
    assert mcp_requests.sync_approved(ADMIN)["installed"] == []
    assert _servers() == {}


def test_rejected_request_is_never_installed(isolated_home):
    mcp_requests.request_server(USER, "context7", "https://mcp.example.test/sse")
    approvals.decide("mcp", "context7", "reject", ADMIN, reason="unknown vendor")
    assert mcp_requests.sync_approved(ADMIN)["installed"] == []
    assert _servers() == {}


# ── MCP: routes ─────────────────────────────────────────────────────────────

@pytest.fixture
def as_caller(monkeypatch):
    from api import ownership

    def _set(email, is_admin=False):
        monkeypatch.setattr(ownership, "request_owner_email", lambda handler: email)
        monkeypatch.setattr(ownership, "request_is_admin", lambda handler: is_admin)
        monkeypatch.setattr(
            ownership, "request_owner_scope", lambda handler: "all" if is_admin else (email or "")
        )
    return _set


def test_route_request_is_202_for_a_non_admin(as_caller):
    as_caller(USER)
    handler = FakeHandler()
    routes._handle_mcp_server_request(
        handler, {"name": "context7", "url": "https://mcp.example.test/sse"}
    )
    assert handler.status == 202
    assert handler.body["status"] == "pending_approval"
    assert handler.body["request"]["installed"] is False
    assert _servers() == {}


def test_route_request_from_an_admin_installs_immediately(as_caller):
    as_caller(ADMIN, is_admin=True)
    handler = FakeHandler()
    routes._handle_mcp_server_request(
        handler, {"name": "context7", "url": "https://mcp.example.test/sse"}
    )
    assert handler.status == 200
    assert handler.body["status"] == "active"
    assert _servers()["context7"]["url"] == "https://mcp.example.test/sse"
    assert approvals.get("mcp", "context7")["status"] == "approved"


def test_route_request_rejects_a_secret(as_caller):
    as_caller(USER)
    handler = FakeHandler()
    routes._handle_mcp_server_request(
        handler,
        {
            "name": "context7",
            "url": "https://mcp.example.test/sse",
            "headers": {"Authorization": "Bearer nope"},
        },
    )
    assert handler.status == 400
    assert approvals.get("mcp", "context7") is None


def test_route_request_after_approval_activates(as_caller):
    as_caller(USER)
    routes._handle_mcp_server_request(
        FakeHandler(), {"name": "context7", "url": "https://mcp.example.test/sse"}
    )
    approvals.decide("mcp", "context7", "approve", ADMIN)

    handler = FakeHandler()
    routes._handle_mcp_server_request(
        handler, {"name": "context7", "url": "https://mcp.example.test/sse"}
    )
    assert handler.status == 200
    assert handler.body["status"] == "active"
    assert "context7" in _servers()


def test_route_request_on_a_rejected_server_is_403(as_caller):
    as_caller(USER)
    routes._handle_mcp_server_request(
        FakeHandler(), {"name": "context7", "url": "https://mcp.example.test/sse"}
    )
    approvals.decide("mcp", "context7", "reject", ADMIN, reason="unknown vendor")

    handler = FakeHandler()
    routes._handle_mcp_server_request(
        handler, {"name": "context7", "url": "https://mcp.example.test/sse"}
    )
    assert handler.status == 403
    assert "unknown vendor" in handler.body["error"]


def test_put_by_a_non_admin_creates_a_request_instead_of_a_server(as_caller):
    as_caller(USER)
    handler = FakeHandler()
    routes._handle_mcp_server_update(
        handler, "context7", {"url": "https://mcp.example.test/sse"}
    )
    assert handler.status == 202
    assert handler.body["status"] == "pending_approval"
    assert _servers() == {}
    assert approvals.get("mcp", "context7")["owner_email"] == USER


def test_put_by_a_non_admin_cannot_add_a_stdio_server(as_caller):
    # Existing server: the create branch does not apply, but a stdio edit
    # from a non-admin is still refused.
    mcp_requests.request_server(USER, "context7", "https://mcp.example.test/sse")
    approvals.decide("mcp", "context7", "approve", ADMIN)
    mcp_requests.sync_approved(ADMIN)

    as_caller(USER)
    handler = FakeHandler()
    routes._handle_mcp_server_update(
        handler, "context7", {"command": "npx", "args": ["-y", "evil"]}
    )
    assert handler.status == 403
    assert "url" in _servers()["context7"]


def test_put_by_an_admin_is_unchanged(as_caller, monkeypatch):
    monkeypatch.setattr(routes, "_mcp_runtime_status_by_name", lambda: {})
    as_caller(ADMIN, is_admin=True)
    handler = FakeHandler()
    routes._handle_mcp_server_update(
        handler, "context7", {"command": "npx", "args": ["-y", "ctx"]}
    )
    assert handler.status == 200
    assert handler.body["ok"] is True
    assert _servers()["context7"]["command"] == "npx"


def test_route_requests_list_is_scoped_to_the_caller(as_caller):
    mcp_requests.request_server(USER, "mine", "https://mine.example.test/sse")
    mcp_requests.request_server("other@example.test", "theirs", "https://x.example.test/sse")

    as_caller(USER)
    handler = FakeHandler()
    routes._handle_mcp_requests_list(handler)
    assert [r["name"] for r in handler.body["requests"]] == ["mine"]

    as_caller(ADMIN, is_admin=True)
    handler = FakeHandler()
    routes._handle_mcp_requests_list(handler)
    assert sorted(r["name"] for r in handler.body["requests"]) == ["mine", "theirs"]


def test_route_requests_list_hides_everything_from_an_emailless_identity(as_caller):
    mcp_requests.request_server(USER, "mine", "https://mine.example.test/sse")

    as_caller("")
    handler = FakeHandler()
    routes._handle_mcp_requests_list(handler)
    assert handler.body["requests"] == []


def test_sync_route_is_admin_only(as_caller):
    mcp_requests.request_server(USER, "context7", "https://mcp.example.test/sse")
    approvals.decide("mcp", "context7", "approve", ADMIN)

    as_caller(USER)
    handler = FakeHandler()
    routes._handle_mcp_sync_approved(handler)
    assert handler.status == 403
    assert _servers() == {}

    as_caller(ADMIN, is_admin=True)
    handler = FakeHandler()
    routes._handle_mcp_sync_approved(handler)
    assert handler.status == 200
    assert handler.body["installed"][0]["name"] == "context7"


def test_server_list_materializes_approved_requests(as_caller, monkeypatch):
    monkeypatch.setattr(routes, "_mcp_runtime_status_by_name", lambda: {})
    mcp_requests.request_server(USER, "context7", "https://mcp.example.test/sse")
    approvals.decide("mcp", "context7", "approve", ADMIN)

    handler = FakeHandler()
    routes._handle_mcp_servers_list(handler)
    assert [s["name"] for s in handler.body["servers"]] == ["context7"]


# ── Governance classification ───────────────────────────────────────────────

def test_request_routes_are_self_routes():
    for path in (
        "/api/mcp/servers/request",
        "/api/mcp/requests",
        "/api/integrations/request",
    ):
        assert path in _SELF_ROUTES
        assert route_permission(path, "POST") is None


def test_install_and_connect_routes_keep_their_permission():
    assert route_permission("/api/mcp/servers/sync-approved", "POST") == "mcp:write"
    assert route_permission("/api/mcp/servers/context7", "PUT") == "mcp:write"
    assert route_permission("/api/integrations/connect", "POST") == "config:write"


# ── Non-admin writes on an already configured server (adversarial) ──────────

def _install_context7(auth_header=None):
    mcp_requests.request_server(
        USER, "context7", "https://mcp.example.test/sse", auth_header=auth_header
    )
    approvals.decide("mcp", "context7", "approve", ADMIN)
    mcp_requests.sync_approved(ADMIN)


def test_put_by_a_non_admin_cannot_repoint_an_existing_server(as_caller):
    """Editing a configured server is an admin action: rewriting its url is a
    full bypass of the approval gate (an approved server silently becomes an
    attacker-controlled one)."""
    _install_context7()

    as_caller(USER)
    handler = FakeHandler()
    routes._handle_mcp_server_update(
        handler, "context7", {"url": "https://attacker.example.test/sse"}
    )
    assert handler.status == 403
    assert _servers()["context7"]["url"] == "https://mcp.example.test/sse"


def test_put_by_a_non_admin_cannot_inject_headers_into_an_existing_server(as_caller):
    _install_context7()

    as_caller(USER)
    handler = FakeHandler()
    routes._handle_mcp_server_update(
        handler,
        "context7",
        {"url": "https://mcp.example.test/sse", "headers": {"Authorization": "Bearer x"}},
    )
    assert handler.status == 403
    assert "headers" not in _servers()["context7"]


def test_toggle_by_a_non_admin_cannot_enable_a_secret_pending_server(as_caller):
    """A request that named an auth header installs disabled on purpose, so a
    non-admin must not be able to flip it on."""
    _install_context7(auth_header="Authorization")
    assert _servers()["context7"]["enabled"] is False

    as_caller(USER)
    handler = FakeHandler()
    routes._handle_mcp_server_toggle(handler, "context7", {"enabled": True})
    assert handler.status == 403
    assert _servers()["context7"]["enabled"] is False


def test_delete_by_a_non_admin_is_refused(as_caller):
    """Delete also revokes the approval entry, so a non-admin delete would
    erase the record that the server was ever approved."""
    _install_context7()

    as_caller(USER)
    handler = FakeHandler()
    routes._handle_mcp_server_delete(handler, "context7")
    assert handler.status == 403
    assert "context7" in _servers()
    assert approvals.get("mcp", "context7")["status"] == "approved"


def test_admin_put_patch_delete_still_work(as_caller, monkeypatch):
    monkeypatch.setattr(routes, "_mcp_runtime_status_by_name", lambda: {})
    _install_context7()

    as_caller(ADMIN, is_admin=True)
    handler = FakeHandler()
    routes._handle_mcp_server_update(handler, "context7", {"url": "https://new.example.test/sse"})
    assert handler.status is None or handler.status == 200
    assert _servers()["context7"]["url"] == "https://new.example.test/sse"

    handler = FakeHandler()
    routes._handle_mcp_server_toggle(handler, "context7", {"enabled": False})
    assert _servers()["context7"]["enabled"] is False

    handler = FakeHandler()
    routes._handle_mcp_server_delete(handler, "context7")
    assert "context7" not in _servers()


# ── Revocation: approved then rejected must become unusable ─────────────────

def test_rejecting_an_installed_server_uninstalls_it(isolated_home):
    _install_context7()
    assert "context7" in _servers()

    approvals.decide("mcp", "context7", "reject", ADMIN, reason="unknown vendor")
    assert mcp_requests.uninstall("context7", ADMIN) is True

    assert "context7" not in _servers()
    assert mcp_requests.sync_approved(ADMIN)["installed"] == []
    events = [e for e in read_audit_events(50) if e["event"] == "mcp_server_uninstall"]
    assert events and events[0]["extra"]["target"] == "context7"


def test_uninstall_never_removes_a_server_an_admin_re_pointed(isolated_home):
    _install_context7()
    cfg = config.get_config()
    cfg["mcp_servers"]["context7"]["url"] = "https://admins-own.example.test/sse"
    config._save_yaml_config_file(config._get_config_path(), cfg)
    config.reload_config()

    approvals.decide("mcp", "context7", "reject", ADMIN)
    assert mcp_requests.uninstall("context7", ADMIN) is False
    assert _servers()["context7"]["url"] == "https://admins-own.example.test/sse"


def test_uninstall_ignores_servers_that_were_never_requested(isolated_home):
    cfg = config.get_config()
    cfg["mcp_servers"] = {"adminonly": {"url": "https://admin.example.test/sse"}}
    config._save_yaml_config_file(config._get_config_path(), cfg)
    config.reload_config()

    assert mcp_requests.uninstall("adminonly", ADMIN) is False
    assert mcp_requests.uninstall_quietly("adminonly", ADMIN) is False
    assert "adminonly" in _servers()
