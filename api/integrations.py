"""Integrations screen bridge to a self-hosted Nango instance.

Owns the provider catalog (parsed from Nango's providers.yaml), per-user
connection listing, connect-session minting, and connection deletion. Pure
logic module in the house style: no HTTP-handler code here; functions raise
ValueError (-> 400), PermissionError (-> 403), KeyError (-> 404) and
RuntimeError (-> 5xx) and api/routes.py translates them into responses.

Ownership model: connect sessions are minted with ``end_user.id =
u-<slug(owner_email)>`` and Nango links every connection created through the
Connect UI to that end user (the connection_id itself is a Nango-generated
uuid; connect sessions refuse caller-chosen connection ids). Non-admin
callers only ever see or delete connections whose ``end_user.id`` equals
their own. Admins (api.ownership.identity_is_admin) see all connections.
This holds in ALL governance modes (off / report_only / enforce), mirroring
the ownership rules elsewhere in the webui.

Config (env, read at call time so profile .env switches are honoured):

- ``HERMES_WEBUI_NANGO_API_URL``        Nango server base URL
- ``HERMES_WEBUI_NANGO_SECRET_KEY_FILE`` file containing the environment
  secret key (read + stripped per request-ish, cached by mtime)
- ``HERMES_WEBUI_NANGO_CONNECT_URL``    public Connect UI base URL returned
  to the frontend alongside minted session tokens
- ``HERMES_WEBUI_NANGO_PROVIDERS_YAML`` path to Nango's providers.yaml
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_API_URL = "http://127.0.0.1:3003"
_DEFAULT_SECRET_KEY_FILE = "/home/synthwavehq/.config/synthwave/nango/secret-key-dev"
_DEFAULT_CONNECT_URL = "https://synthwavehq.tailbdab77.ts.net:3009"
_DEFAULT_PROVIDERS_YAML = "/home/synthwavehq/.hermes/external/nango/providers.yaml"

_NANGO_TIMEOUT_SECONDS = 15
# GET /connection caps limit at 2000 server-side; stay inside the contract.
_NANGO_CONNECTIONS_LIMIT = 2000
# Bound on any Nango response body we are willing to buffer (providers.yaml
# derived catalogs and 2000-connection listings fit comfortably).
_MAX_RESPONSE_BYTES = 8 * 1024 * 1024

# Fields the catalog surfaces from each providers.yaml entry. ``alias`` is
# consumed during resolution and never surfaced.
_SCALAR_FIELDS = ("display_name", "auth_mode", "docs", "alias")


# ── Config (env read at call time; profile .env loads into os.environ) ───────

def _nango_api_url() -> str:
    raw = str(os.getenv("HERMES_WEBUI_NANGO_API_URL", "") or "").strip() or _DEFAULT_API_URL
    base = raw.rstrip("/")
    scheme = urllib.parse.urlsplit(base).scheme.lower()
    # Hardening: the URL is operator-configured, but reject non-HTTP(S)
    # schemes so a bad env value can never be handed to urlopen.
    if scheme not in ("http", "https"):
        raise RuntimeError("HERMES_WEBUI_NANGO_API_URL must be http(s)")
    return base


def _nango_connect_url() -> str:
    raw = str(os.getenv("HERMES_WEBUI_NANGO_CONNECT_URL", "") or "").strip()
    return (raw or _DEFAULT_CONNECT_URL).rstrip("/")


def _providers_yaml_path() -> Path:
    raw = str(os.getenv("HERMES_WEBUI_NANGO_PROVIDERS_YAML", "") or "").strip()
    return Path(raw or _DEFAULT_PROVIDERS_YAML).expanduser()


_SECRET_CACHE_LOCK = threading.Lock()
_SECRET_CACHE: dict[str, tuple[tuple[int, int], str]] = {}


def _nango_secret_key() -> str:
    """Read the Nango environment secret key from its key file (mtime-cached)."""
    raw = str(os.getenv("HERMES_WEBUI_NANGO_SECRET_KEY_FILE", "") or "").strip()
    path = Path(raw or _DEFAULT_SECRET_KEY_FILE).expanduser()
    try:
        st = path.stat()
        sig = (st.st_size, st.st_mtime_ns)
        cache_key = str(path)
        with _SECRET_CACHE_LOCK:
            cached = _SECRET_CACHE.get(cache_key)
        if cached and cached[0] == sig:
            return cached[1]
        secret = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Nango secret key file is not readable: {exc.strerror or exc}")
    if not secret:
        raise RuntimeError("Nango secret key file is empty")
    with _SECRET_CACHE_LOCK:
        if len(_SECRET_CACHE) > 8:
            _SECRET_CACHE.clear()
        _SECRET_CACHE[cache_key] = (sig, secret)
    return secret


# ── Identity helpers ─────────────────────────────────────────────────────────

def slug_email(email: str | None) -> str:
    """Slug an email for use in ids: lowercase, non [a-z0-9] -> '-', collapsed."""
    return re.sub(r"[^a-z0-9]+", "-", str(email or "").lower()).strip("-")


def end_user_id(owner_email: str | None) -> str:
    """The Nango end_user.id for a webui identity (``u-<slug>``)."""
    return "u-" + (slug_email(owner_email) or "admin")


def _row_end_user(row: dict) -> dict | None:
    end_user = row.get("end_user")
    if not isinstance(end_user, dict):
        return None
    return {
        "id": str(end_user.get("id") or ""),
        "email": end_user.get("email"),
        "display_name": end_user.get("display_name"),
    }


# ── Nango HTTP client (stdlib urllib only, no-redirect, bounded reads) ───────

class NangoError(RuntimeError):
    """Raised when the Nango API rejects or fails a request."""

    def __init__(self, message: str, *, status: int = 0, code: str = ""):
        super().__init__(message)
        self.status = int(status)
        self.code = str(code or "")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # The request carries the environment secret key as a Bearer token; refuse
    # redirects so it can never be replayed against a 3xx Location.
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _nango_request(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform a JSON request against the Nango API; raise NangoError on failure."""
    url = _nango_api_url() + path
    if query:
        url += "?" + urllib.parse.urlencode({k: str(v) for k, v in query.items()})
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {_nango_secret_key()}",
        "User-Agent": "Hermes-WebUI-Integrations",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=_NANGO_TIMEOUT_SECONDS) as resp:
            raw = resp.read(_MAX_RESPONSE_BYTES)
    except urllib.error.HTTPError as exc:
        status, code, detail = exc.code, "", ""
        try:
            parsed = json.loads(exc.read(65536) or b"{}")
            err = parsed.get("error")
            if isinstance(err, dict):
                code = str(err.get("code") or "")
                detail = str(err.get("message") or code)
            elif err:
                detail = str(err)
        except Exception:
            detail = ""
        raise NangoError(
            f"Nango API error ({status}): {detail or 'request rejected'}",
            status=status,
            code=code,
        )
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", None) or exc
        raise NangoError(f"Nango is unreachable: {reason}")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        raise NangoError("Nango returned a non-JSON response")
    return parsed if isinstance(parsed, dict) else {}


# ── providers.yaml catalog (mtime-cached, alias-resolving) ───────────────────

_CATALOG_CACHE_LOCK = threading.Lock()
_CATALOG_CACHE: dict[str, tuple[tuple[int, int], dict[str, dict]]] = {}


def _parse_providers_minimal(text: str) -> dict[str, dict]:
    """Tolerant fallback parser for providers.yaml when PyYAML is unavailable.

    Only extracts what the catalog needs: top-level provider keys, the
    ``display_name``/``auth_mode``/``docs``/``alias`` scalars at the first
    indent level, and the ``categories`` string list. Everything else
    (proxy, credentials, connection_config, ...) is deliberately ignored.
    """
    entries: dict[str, dict] = {}
    current: dict | None = None
    in_categories = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0:
            current = None
            in_categories = False
            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.-]*):\s*$", stripped)
            if m:
                current = {}
                entries[m.group(1)] = current
            continue
        if current is None:
            continue
        if in_categories:
            if indent > 4 and stripped.startswith("- "):
                current.setdefault("categories", []).append(
                    stripped[2:].strip().strip("'\"")
                )
                continue
            in_categories = False
        if indent == 4:
            if stripped == "categories:":
                in_categories = True
                current.setdefault("categories", [])
                continue
            m = re.match(r"^([A-Za-z0-9_]+):\s*(\S.*)$", stripped)
            if m and m.group(1) in _SCALAR_FIELDS:
                current[m.group(1)] = m.group(2).strip().strip("'\"")
    return entries


def _parse_providers(text: str) -> dict[str, dict]:
    """Parse providers.yaml with PyYAML when present, else the minimal parser."""
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return _parse_providers_minimal(text)
    try:
        data = yaml.safe_load(text)
    except Exception:
        logger.warning("PyYAML failed to parse providers.yaml; using minimal parser", exc_info=True)
        return _parse_providers_minimal(text)
    if not isinstance(data, dict):
        raise RuntimeError("providers.yaml did not parse to a mapping")
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def _resolve_aliases(entries: dict[str, dict]) -> dict[str, dict]:
    """Resolve ``alias:`` entries: inherit from the target, keep own overrides."""
    resolved: dict[str, dict] = {}
    for key, entry in entries.items():
        own = {k: v for k, v in entry.items() if k != "alias"}
        base: dict = {}
        target = entry.get("alias")
        seen = {key}
        while isinstance(target, str) and target in entries and target not in seen:
            seen.add(target)
            target_entry = entries[target]
            # Nearer targets in the chain win over farther ones.
            base = {
                **{k: v for k, v in target_entry.items() if k != "alias"},
                **base,
            }
            target = target_entry.get("alias")
        resolved[key] = {**base, **own}
    return resolved


def load_provider_entries() -> dict[str, dict]:
    """providers.yaml as {key: entry} with aliases resolved (mtime-cached)."""
    path = _providers_yaml_path()
    try:
        st = path.stat()
    except OSError as exc:
        raise RuntimeError(f"Nango providers.yaml is not readable: {exc.strerror or exc}")
    sig = (st.st_size, st.st_mtime_ns)
    cache_key = str(path)
    with _CATALOG_CACHE_LOCK:
        cached = _CATALOG_CACHE.get(cache_key)
    if cached and cached[0] == sig:
        return cached[1]
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise RuntimeError(f"Nango providers.yaml is not readable: {exc.strerror or exc}")
    resolved = _resolve_aliases(_parse_providers(text))
    with _CATALOG_CACHE_LOCK:
        if len(_CATALOG_CACHE) > 4:
            _CATALOG_CACHE.clear()
        _CATALOG_CACHE[cache_key] = (sig, resolved)
    return resolved


def _catalog_item(key: str, entry: dict) -> dict:
    categories = entry.get("categories")
    return {
        "key": key,
        "display_name": str(entry.get("display_name") or key),
        "auth_mode": str(entry.get("auth_mode") or ""),
        "categories": [str(c) for c in categories] if isinstance(categories, list) else [],
        "docs": str(entry.get("docs") or ""),
        "configured": False,
        "unique_key": None,
    }


def get_catalog() -> dict:
    """Provider catalog merged with which providers have a Nango integration.

    Degrades gracefully: when the Nango API is down the yaml-derived catalog
    is still returned with every ``configured`` flag false and the failure
    surfaced under ``nango`` so the screen can render a banner instead of a
    hard error.
    """
    items = {
        key: _catalog_item(key, entry)
        for key, entry in load_provider_entries().items()
    }
    nango: dict[str, Any] = {"available": True, "error": None}
    try:
        for row in _list_integrations():
            provider = str(row.get("provider") or "")
            unique_key = str(row.get("unique_key") or "")
            if not provider or not unique_key:
                continue
            item = items.get(provider)
            if item is None:
                # Integration for a provider missing from providers.yaml
                # (custom/renamed provider): still surface it as connectable.
                item = _catalog_item(provider, {"display_name": row.get("display_name")})
                items[provider] = item
            item["configured"] = True
            if not item["unique_key"]:
                item["unique_key"] = unique_key
    except NangoError as exc:
        logger.warning("Nango integrations fetch failed: %s", exc)
        nango = {"available": False, "error": str(exc)}
    providers = sorted(items.values(), key=lambda p: str(p["display_name"]).lower())
    return {"providers": providers, "nango": nango}


# ── Connections ──────────────────────────────────────────────────────────────

def _list_integrations() -> list[dict]:
    data = _nango_request("GET", "/integrations")
    rows = data.get("data")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def list_connections(owner_email: str | None, *, is_admin: bool = False) -> list[dict]:
    """The caller's Nango connections; admins see every connection.

    Non-admin callers are filtered to connections whose ``end_user.id``
    equals their own ``u-<slug(email)>`` (Nango generates the connection_id
    itself, so the end user link is the ownership key). The filter is asked
    of Nango via ``endUserId`` AND re-checked here, regardless of the
    governance mode.
    """
    query: dict[str, Any] = {"limit": _NANGO_CONNECTIONS_LIMIT}
    own_id = None
    if not is_admin:
        if not owner_email:
            return []
        own_id = end_user_id(owner_email)
        query["endUserId"] = own_id
    data = _nango_request("GET", "/connection", query=query)
    rows = data.get("connections")
    if not isinstance(rows, list):
        rows = data.get("data") if isinstance(data.get("data"), list) else []
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        end_user = _row_end_user(row)
        if own_id is not None and (end_user is None or end_user["id"] != own_id):
            continue
        errors = row.get("errors")
        out.append({
            "connection_id": str(row.get("connection_id") or ""),
            "provider_config_key": str(row.get("provider_config_key") or ""),
            "created": row.get("created"),
            "errors": errors if isinstance(errors, list) else [],
            "end_user": end_user,
        })
    return out


def create_connect_session(owner_email: str | None, provider_config_key: str) -> dict:
    """Mint a Nango connect session for the caller and one integration.

    Only integrations actually configured in Nango are allowed (the Nango
    server would also reject unknown keys, but validating here yields a clean
    400 instead of a passthrough error). Returns ``{token, connect_url,
    expires_at}``; the frontend opens ``connect_url`` with the token (session
    tokens expire after 30 minutes, so a fresh session is minted per attempt).
    """
    key = str(provider_config_key or "").strip()
    if not key:
        raise ValueError("provider_config_key is required")
    configured = {str(row.get("unique_key") or "") for row in _list_integrations()}
    if key not in configured:
        raise ValueError(f"integration '{key}' is not configured in Nango")
    end_user: dict[str, Any] = {"id": end_user_id(owner_email)}
    email = str(owner_email or "").strip().lower()
    # Nango requires a syntactically valid email of length >= 5 when present;
    # omit it (and display_name) for identity-less local-admin installs.
    if "@" in email and len(email) >= 5:
        end_user["email"] = email
        end_user["display_name"] = email.split("@", 1)[0]
    response = _nango_request(
        "POST",
        "/connect/sessions",
        payload={"end_user": end_user, "allowed_integrations": [key]},
    )
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    token = str(data.get("token") or "")
    if not token:
        raise RuntimeError("Nango did not return a connect session token")
    return {
        "token": token,
        "connect_url": _nango_connect_url(),
        "expires_at": data.get("expires_at"),
    }


def delete_connection(
    owner_email: str | None,
    connection_id: str,
    provider_config_key: str,
    *,
    is_admin: bool = False,
) -> dict:
    """Delete a Nango connection; non-admins may only delete their own.

    Raises PermissionError (-> 403) when a non-admin targets a connection
    whose ``end_user.id`` is not their own ``u-<slug(email)>``, KeyError
    (-> 404) when Nango does not know the (connection_id,
    provider_config_key) pair.
    """
    cid = str(connection_id or "").strip()
    key = str(provider_config_key or "").strip()
    if not cid:
        raise ValueError("connection id is required")
    if not key:
        raise ValueError("provider_config_key is required")
    if not is_admin:
        if not owner_email:
            raise PermissionError("you can only delete your own connections")
        # Ownership check: the connection must be linked to the caller's end
        # user. Look it up scoped to the caller; absence means it is either
        # unknown or someone else's, and both must read as "not yours".
        data = _nango_request(
            "GET",
            "/connection",
            query={"endUserId": end_user_id(owner_email), "connectionId": cid},
        )
        rows = data.get("connections")
        if not isinstance(rows, list):
            rows = []
        owned = any(
            isinstance(row, dict)
            and str(row.get("connection_id") or "") == cid
            and str(row.get("provider_config_key") or "") == key
            for row in rows
        )
        if not owned:
            raise PermissionError("you can only delete your own connections")
    try:
        response = _nango_request(
            "DELETE",
            "/connection/" + urllib.parse.quote(cid, safe=""),
            query={"provider_config_key": key},
        )
    except NangoError as exc:
        if exc.code == "unknown_connection" or exc.status == 404:
            raise KeyError("connection not found")
        raise
    return {"success": bool(response.get("success", True))}
