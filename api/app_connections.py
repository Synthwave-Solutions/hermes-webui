"""Per-turn resolver behind the agent's ``app_connections`` tool (Integrations / Nango).

Ownership rule, applied on every call and never taken from model input:

- a person uses only connections whose Nango ``end_user.id`` is their own ``u-<slug>``;
- admins additionally use organisation connections (rows without an end user);
- nobody uses another person's personal connection, admins included.

Credentials stay server-side: REST calls go through the Nango proxy (the secret key and
the provider key are added here), MCP calls fetch the access token from Nango and call the
provider's MCP endpoint directly. Neither the key nor the token is ever returned.
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from api import integrations as _intg

_TIMEOUT = 60
_MAX_BODY = 2 * 1024 * 1024
_MAX_TEXT = 60_000
_BLOCKED_HEADERS = {
    "authorization", "cookie", "host", "content-length", "connection-id", "provider-config-key",
    "base-url-override", "decompress", "retries", "x-api-key", "api-key", "api-token", "x-auth-token",
    "proxy-authorization", "transfer-encoding",
}
_MCP_PROTOCOL = "2025-06-18"

# Provider -> environment variables our CLIs read (each CLI prefers the environment over its
# host file). Sources: "apiKey", "username", "password", "config:<field>", and an optional
# "fmt" template. Only PERSONAL connections are exported, so a person's own key replaces the
# shared host key in their own terminal and nobody receives an organisation key this way.
CLI_ENV: dict[str, dict[str, str]] = {
    "productive": {"PRODUCTIVE_API_KEY": "apiKey", "PRODUCTIVE_ORG_ID": "config:organizationId"},
    "lemlist": {"LEMLIST_API_KEY": "password"},
    "fireflies": {"FIREFLIES_API_KEY": "apiKey"},
    "openai": {"OPENAI_API_KEY": "apiKey"},
    "anthropic": {"ANTHROPIC_API_KEY": "apiKey"},
    "elevenlabs": {"ELEVENLABS_API_KEY": "apiKey"},
    "github-pat": {"GH_TOKEN": "apiKey", "GITHUB_TOKEN": "apiKey"},
    "semrush": {"SEMRUSH_API_KEY": "apiKey"},
    "active-campaign": {"ACTIVECAMPAIGN_API_KEY": "apiKey", "ACTIVECAMPAIGN_URL": "config:hostname|https://{}"},
    "google-gemini": {"GEMINI_API_KEY": "apiKey"},
    "twenty-crm": {"TWENTY_API_KEY": "apiKey"},
    "n8n": {"N8N_API_KEY": "apiKey", "N8N_HOST": "config:baseUrl"},
    "buffer-api": {"BUFFER_API_KEY": "apiKey"},
    "mailchimp-api-key": {"MAILCHIMP_API_KEY": "password"},
}
_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


def cli_env_names(provider: str) -> list[str]:
    return sorted((CLI_ENV.get(provider) or {}).keys())


def _cli_value(source: str, creds: dict, config: dict) -> str:
    source, _, fmt = source.partition("|")
    if source.startswith("config:"):
        value = config.get(source[7:])
    else:
        value = creds.get(source)
    value = str(value or "").strip()
    if value and fmt:
        value = fmt.format(value.removeprefix("https://").removeprefix("http://"))
    return value if value and "\n" not in value and "\x00" not in value else ""


_TOOLS_CACHE: dict[tuple[str, str], tuple[float, list]] = {}
_TOOLS_LOCK = threading.Lock()


def _clip(text: str) -> tuple[str, bool]:
    return (text[:_MAX_TEXT], True) if len(text) > _MAX_TEXT else (text, False)


def _shape_body(raw: bytes, content_type: str) -> dict:
    text = raw.decode("utf-8", errors="replace")
    if "json" in (content_type or "").lower() or text[:1] in "{[":
        try:
            parsed = json.loads(text)
            dumped = json.dumps(parsed, ensure_ascii=False)
            if len(dumped) <= _MAX_TEXT:
                return {"body": parsed, "truncated": False}
            clipped, _ = _clip(dumped)
            return {"body": clipped, "truncated": True}
        except ValueError:
            pass
    clipped, truncated = _clip(text)
    return {"body": clipped, "truncated": truncated}


def _validate_path(path: str) -> str:
    path = str(path or "").strip()
    # The proxy concatenates base_url + path: anything but a plain absolute path could move
    # the request (and the injected credential) to another host.
    if not path.startswith("/") or path.startswith("//") or "\\" in path or "://" in path:
        raise ValueError("path must be an absolute API path starting with a single '/' (e.g. '/api/team').")
    if any(ch in path for ch in "\r\n\t "):
        raise ValueError("path must not contain whitespace.")
    return path


def _mcp_url(entry: dict) -> str:
    params = entry.get("authorization_params") if isinstance(entry.get("authorization_params"), dict) else {}
    proxy = entry.get("proxy") if isinstance(entry.get("proxy"), dict) else {}
    url = str(params.get("resource") or proxy.get("base_url") or "").strip()
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise LookupError("This MCP connector has no usable endpoint.")
    if parts.path in ("", "/"):
        url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, "/mcp", "", ""))
    return url


class Resolver:
    """Bound per turn by api.personal_credentials; one instance per identity."""

    def __init__(self, identity: dict | None):
        self._identity = dict(identity or {})
        self._email = str(self._identity.get("email") or "").strip().lower()
        self._admin: bool | None = None

    @property
    def email(self) -> str:
        """The signed-in person this turn runs for (read by per-person tool plugins such as
        SynthPulse Artifacts; never a credential)."""
        return self._email

    # ── ownership ──────────────────────────────────────────────────────────
    def _is_admin(self) -> bool:
        if self._admin is None:
            try:
                from api.ownership import identity_is_admin
                self._admin = bool(identity_is_admin(self._identity))
            except Exception:
                self._admin = False
        return self._admin

    def _rows(self) -> list[dict]:
        rows: list[dict] = []
        if self._email:
            for row in _intg.list_connections(self._email, is_admin=False):
                rows.append({**row, "scope": "personal"})
        if self._is_admin():
            for row in _intg.list_connections(None, is_admin=True):
                if row.get("end_user") is None:
                    rows.append({**row, "scope": "organization"})
        return rows

    def _integrations(self) -> dict[str, dict]:
        entries = _intg.load_provider_entries()
        out = {}
        for item in _intg._list_integrations():
            key = str(item.get("unique_key") or "")
            provider = str(item.get("provider") or key)
            out[key] = {"provider": provider, "entry": entries.get(provider) or {}}
        return out

    def _pick(self, integration: str, connection_id: str | None) -> tuple[dict, dict]:
        rows = [r for r in self._rows() if r["provider_config_key"] == integration]
        if connection_id:
            rows = [r for r in rows if r["connection_id"] == connection_id]
        if not rows:
            raise LookupError(
                f"No usable '{integration}' connection for you. Connect it under Integrations in the WebUI "
                "(your own connection), or ask an admin for an organisation connection.")
        if len(rows) > 1:
            personal = [r for r in rows if r["scope"] == "personal"]
            rows = personal or rows
        if len(rows) > 1:
            ids = ", ".join(r["connection_id"] for r in rows)
            raise LookupError(f"You have several '{integration}' connections; pass connection_id (one of: {ids}).")
        info = self._integrations().get(integration) or {"provider": integration, "entry": {}}
        return rows[0], info

    # ── tool surface ───────────────────────────────────────────────────────
    def list(self) -> list[dict]:
        infos = self._integrations()
        out = []
        for row in self._rows():
            info = infos.get(row["provider_config_key"]) or {"provider": row["provider_config_key"], "entry": {}}
            entry = info["entry"]
            proxy = entry.get("proxy") if isinstance(entry.get("proxy"), dict) else {}
            auth_mode = str(entry.get("auth_mode") or "")
            out.append({
                "integration": row["provider_config_key"],
                "connection_id": row["connection_id"],
                "scope": row["scope"],
                "app": entry.get("display_name") or info["provider"],
                "auth_mode": auth_mode,
                "use": "mcp" if auth_mode == "MCP_OAUTH2" else "request",
                "api_base_url": proxy.get("base_url") or None,
                "docs": entry.get("docs") or None,
                "healthy": not row.get("errors"),
            })
        return out

    def request(self, integration, connection_id, method, path, query, body, headers) -> dict:
        row, info = self._pick(integration, connection_id)
        if str(info["entry"].get("auth_mode") or "") == "MCP_OAUTH2":
            raise ValueError(f"'{integration}' is an MCP connector: use action='mcp'.")
        path = _validate_path(path)
        url = _intg._nango_api_url() + "/proxy" + path
        if query:
            url += ("&" if "?" in path else "?") + urllib.parse.urlencode(
                {str(k): str(v) for k, v in query.items()}, doseq=True)
        out_headers = {"Accept": "application/json, */*"}
        for key, value in (headers or {}).items():
            name = str(key).strip()
            if name.lower() in _BLOCKED_HEADERS or name.lower().startswith(("nango-", "x-nango", "proxy-")):
                continue
            out_headers[name] = str(value)
        data = None
        if body is not None and method not in ("GET", "HEAD"):
            if isinstance(body, (dict, list)):
                data = json.dumps(body).encode("utf-8")
                out_headers.setdefault("Content-Type", "application/json")
            else:
                data = str(body).encode("utf-8")
        out_headers.update({
            "Authorization": f"Bearer {_intg._nango_secret_key()}",
            "Provider-Config-Key": integration,
            "Connection-Id": row["connection_id"],
        })
        req = urllib.request.Request(url, data=data, headers=out_headers, method=method)
        try:
            with _intg._OPENER.open(req, timeout=_TIMEOUT) as resp:
                status, ctype, raw = resp.status, resp.headers.get("Content-Type", ""), resp.read(_MAX_BODY)
        except urllib.error.HTTPError as exc:
            status, ctype, raw = exc.code, exc.headers.get("Content-Type", "") if exc.headers else "", exc.read(_MAX_BODY)
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(f"Nango is unreachable: {getattr(exc, 'reason', exc)}") from None
        return {"integration": integration, "connection_id": row["connection_id"], "scope": row["scope"],
                "status": status, "ok": 200 <= status < 300, "content_type": ctype,
                **_shape_body(raw, ctype)}

    # ── CLI environment ─────────────────────────────────────────────────────
    def cli_env(self) -> dict[str, str]:
        """Environment variables for this person's terminal from their own API-key connections."""
        if getattr(self, "_cli_env_cache", None) is not None:
            return dict(self._cli_env_cache)
        env: dict[str, str] = {}
        if self._email:
            infos = self._integrations()
            for row in _intg.list_connections(self._email, is_admin=False):
                key = row["provider_config_key"]
                provider = (infos.get(key) or {}).get("provider") or key
                mapping = CLI_ENV.get(provider)
                if not mapping or row.get("errors"):
                    continue
                try:
                    data = _intg._nango_request(
                        "GET", f"/connection/{urllib.parse.quote(row['connection_id'], safe='')}",
                        query={"provider_config_key": key})
                except Exception:
                    continue
                creds = data.get("credentials") if isinstance(data.get("credentials"), dict) else {}
                config = data.get("connection_config") if isinstance(data.get("connection_config"), dict) else {}
                for name, source in mapping.items():
                    value = _cli_value(source, creds, config)
                    # First connection per provider wins; several connections are ambiguous for a CLI.
                    if value and _ENV_NAME.match(name) and name not in env:
                        env[name] = value
        self._cli_env_cache = env
        return dict(env)

    # ── MCP ────────────────────────────────────────────────────────────────
    def _mcp_target(self, integration, connection_id) -> tuple[dict, str, str]:
        row, info = self._pick(integration, connection_id)
        if str(info["entry"].get("auth_mode") or "") != "MCP_OAUTH2":
            raise ValueError(f"'{integration}' is not an MCP connector: use action='request'.")
        data = _intg._nango_request("GET", f"/connection/{urllib.parse.quote(row['connection_id'], safe='')}",
                                    query={"provider_config_key": integration})
        creds = data.get("credentials") if isinstance(data.get("credentials"), dict) else {}
        token = str(creds.get("access_token") or "")
        if not token:
            raise RuntimeError("Nango returned no access token for this connection; reconnect it under Integrations.")
        return row, _mcp_url(info["entry"]), token

    @staticmethod
    def _rpc(url: str, token: str, payload: dict, session: str | None) -> tuple[dict | None, str | None]:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": _MCP_PROTOCOL}
        if session:
            headers["Mcp-Session-Id"] = session
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with _intg._OPENER.open(req, timeout=_TIMEOUT) as resp:
                sid = resp.headers.get("Mcp-Session-Id") or session
                ctype = resp.headers.get("Content-Type", "")
                raw = resp.read(_MAX_BODY).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", errors="replace")[:300] if exc.fp else ""
            raise RuntimeError(f"MCP endpoint answered HTTP {exc.code}: {detail}") from None
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(f"MCP endpoint unreachable: {getattr(exc, 'reason', exc)}") from None
        if "id" not in payload:
            return None, sid
        messages = []
        if "text/event-stream" in ctype:
            for line in raw.splitlines():
                if line.startswith("data:"):
                    try:
                        messages.append(json.loads(line[5:].strip()))
                    except ValueError:
                        continue
        elif raw.strip():
            parsed = json.loads(raw)
            messages = parsed if isinstance(parsed, list) else [parsed]
        for msg in messages:
            if isinstance(msg, dict) and msg.get("id") == payload["id"]:
                return msg, sid
        raise RuntimeError("MCP endpoint returned no response for the request.")

    def _mcp_session(self, url: str, token: str) -> str | None:
        init, sid = self._rpc(url, token, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": _MCP_PROTOCOL, "capabilities": {},
            "clientInfo": {"name": "synthpulse-app-connections", "version": "1.0"}}}, None)
        if init and init.get("error"):
            raise RuntimeError(f"MCP initialize failed: {init['error']}")
        self._rpc(url, token, {"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
        return sid

    def _tools(self, integration, connection_id) -> tuple[dict, list]:
        row, url, token = self._mcp_target(integration, connection_id)
        key = (integration, row["connection_id"])
        with _TOOLS_LOCK:
            hit = _TOOLS_CACHE.get(key)
        if hit and hit[0] > time.monotonic():
            return row, hit[1]
        sid = self._mcp_session(url, token)
        msg, _ = self._rpc(url, token, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, sid)
        if msg.get("error"):
            raise RuntimeError(f"MCP tools/list failed: {msg['error']}")
        tools = (msg.get("result") or {}).get("tools") or []
        with _TOOLS_LOCK:
            _TOOLS_CACHE[key] = (time.monotonic() + 300, tools)
        return row, tools

    def mcp_tool_is_read_only(self, integration, connection_id, name) -> bool:
        _, tools = self._tools(integration, connection_id)
        for tool in tools:
            if tool.get("name") == name:
                return bool((tool.get("annotations") or {}).get("readOnlyHint"))
        return False

    def mcp(self, integration, connection_id, method, name, arguments) -> dict:
        if method == "tools/list":
            row, tools = self._tools(integration, connection_id)
            return {"integration": integration, "connection_id": row["connection_id"], "tools": [
                {"name": t.get("name"), "description": (t.get("description") or "")[:500],
                 "read_only": bool((t.get("annotations") or {}).get("readOnlyHint")),
                 "input_schema": t.get("inputSchema")} for t in tools]}
        row, url, token = self._mcp_target(integration, connection_id)
        sid = self._mcp_session(url, token)
        msg, _ = self._rpc(url, token, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                        "params": {"name": name, "arguments": arguments or {}}}, sid)
        if msg.get("error"):
            return {"integration": integration, "ok": False, "error": msg["error"]}
        text, truncated = _clip(json.dumps(msg.get("result"), ensure_ascii=False))
        result = msg.get("result") if not truncated else text
        return {"integration": integration, "connection_id": row["connection_id"], "ok": True,
                "result": result, "truncated": truncated}


def bind(identity):
    """Bind the resolver for this identity into the agent's tool context."""
    from tools.app_connections_tool import bind_app_connections
    return bind_app_connections(Resolver(identity))


def reset(token) -> None:
    from tools.app_connections_tool import reset_app_connections
    reset_app_connections(token)
