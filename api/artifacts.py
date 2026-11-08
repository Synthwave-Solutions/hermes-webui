"""SynthPulse Artifacts in the chat: preview, download and explicit sharing.

The agent publishes with the ``artifacts`` plugin (``artifact_publish``); the reply
carries an ```artifact block with the artifact id, which static/artifacts.js turns
into a card. This module is the card's server side:

  GET  /api/artifacts/<id>            metadata for the card (title, kind, shares)
  GET  /api/artifacts/<id>/frame      the rendered document for a sandboxed iframe
  GET  /api/artifacts/<id>/download   the original bytes as an attachment
  POST /api/artifacts/<id>/share      one guest link, only on the person's click

The artifact service (Synthwave HQ, loopback) holds the library; its machine
credential stays here and never reaches the browser. Ownership follows the plugin's
rule: the owner key is derived from the signed-in email, and only the emails in the
admins file see other people's artifacts. Someone else's artifact answers 404, the
same as an unknown id.

The frame response carries the service's own frame policy plus ``sandbox
allow-scripts`` (opaque origin, so artifact code can never reach WebUI cookies or
APIs) and ``frame-ancestors 'self'``.
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

SERVICE_URL = os.environ.get("SYNTHPULSE_ARTIFACTS_URL", "http://127.0.0.1:18152").rstrip("/")
TOKEN_FILE = Path(os.environ.get(
    "SYNTHPULSE_ARTIFACTS_TOKEN_FILE", "~/.config/synthwave/synthpulse-artifacts/api-token")).expanduser()
ADMINS_FILE = Path(os.environ.get(
    "SYNTHPULSE_ARTIFACTS_ADMINS_FILE", "~/.config/synthwave/synthpulse-artifacts/admins")).expanduser()
TIMEOUT = 20
MAX_BYTES = 12 * 1024 * 1024
MAX_SHARE_HOURS = 8760

_ROUTE = re.compile(r"^/api/artifacts/([0-9a-fA-F-]{36})(?:/(frame|download|share))?$")
_EXT = {"html": "html", "markdown": "md", "svg": "svg", "png": "png", "webp": "webp"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


class ArtifactError(Exception):
    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status, self.code = status, code


def owner_key(email: str) -> str:
    """Same derivation as the plugin (plugin/tools.py ``_owner``)."""
    user = str(email or "").strip().lower()
    safe = re.sub(r"[^a-z0-9_.-]", "-", user.replace("@", "_at_"))
    return (safe if "@" in user else f"user_{safe}")[:64].strip(".-_") or "unknown"


def _admins() -> set[str]:
    try:
        raw = ADMINS_FILE.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {ln.strip().lower() for ln in raw.splitlines() if ln.strip() and not ln.startswith("#")}


def _token() -> str:
    try:
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def configured() -> bool:
    return bool(_token())


def _request(method: str, path: str, *, params: dict | None = None, body: dict | None = None):
    token = _token()
    if not token:
        raise ArtifactError(503, "not_configured")
    url = f"{SERVICE_URL}/internal/v1{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with _opener.open(req, timeout=TIMEOUT) as resp:
            raw = resp.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ArtifactError(502, "too_large")
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, raw
    except urllib.error.HTTPError as exc:
        raise ArtifactError(404 if exc.code == 404 else 502, "not_found" if exc.code == 404 else "service_error") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ArtifactError(503, "service_unreachable") from None


def _identity_email(handler) -> str | None:
    """The signed-in email; '' in auth-disabled single-user mode; None when signed out."""
    try:
        from api import auth
        if not auth.is_auth_enabled():
            return ""
    except Exception:
        pass
    try:
        from api.ownership import request_owner_email
        email = request_owner_email(handler)
    except Exception:
        logger.debug("artifact identity lookup failed", exc_info=True)
        return None
    return str(email).strip().lower() if email else None


def _owned_detail(handler, artifact_id: str) -> dict:
    email = _identity_email(handler)
    if email is None:
        raise ArtifactError(401, "sign_in_required")
    _status, _headers, raw = _request("GET", f"/artifacts/{artifact_id}")
    detail = json.loads(raw.decode("utf-8"))
    artifact = detail.get("artifact") or {}
    if email == "" or email in _admins():
        return detail
    if artifact.get("source_profile") != owner_key(email):
        raise ArtifactError(404, "not_found")
    return detail


def _public(detail: dict) -> dict:
    a = detail.get("artifact") or {}
    shares = detail.get("shares") or []
    return {
        "id": a.get("id"), "slug": a.get("slug"), "title": a.get("title"), "kind": a.get("kind"),
        "created_at": a.get("created_at"), "byte_length": a.get("byte_length"),
        "active_shares": sum(1 for s in shares if s.get("status") == "active"),
    }


def _send_json(handler, payload: dict, status: int = 200) -> bool:
    from api.helpers import j
    j(handler, payload, status=status, extra_headers={"Cache-Control": "no-store"})
    return True


def _send_bytes(handler, body: bytes, content_type: str, headers: dict) -> bool:
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Referrer-Policy", "no-referrer")
    for k, v in headers.items():
        handler.send_header(k, v)
    handler.end_headers()
    if getattr(handler, "command", "GET") != "HEAD":
        handler.wfile.write(body)
    return True


def match(path: str) -> bool:
    return bool(_ROUTE.match(path or ""))


def handle_get(handler, parsed) -> bool:
    m = _ROUTE.match(parsed.path)
    if not m or m.group(2) == "share":
        return _send_json(handler, {"error": "not_found"}, 404)
    artifact_id, action = m.group(1).lower(), m.group(2)
    try:
        detail = _owned_detail(handler, artifact_id)
        if action is None:
            return _send_json(handler, {"artifact": _public(detail)})
        if action == "frame":
            query = urllib.parse.parse_qs(parsed.query or "")
            theme = "dark" if (query.get("theme") or [""])[0] == "dark" else "light"
            _s, headers, raw = _request("GET", f"/artifacts/{artifact_id}/render", params={"theme": theme})
            policy = headers.get("x-artifact-frame-policy", "")
            if not policy:
                raise ArtifactError(502, "service_error")
            return _send_bytes(handler, raw, "text/html; charset=utf-8", {
                "Content-Security-Policy": f"{policy}; sandbox allow-scripts; frame-ancestors 'self'",
                "Cache-Control": "private, max-age=300",
                "Cross-Origin-Resource-Policy": "same-origin",
            })
        a = detail.get("artifact") or {}
        _s, headers, raw = _request("GET", f"/artifacts/{artifact_id}/download")
        slug = re.sub(r"[^a-z0-9-]", "", str(a.get("slug") or "artifact"))[:80] or "artifact"
        filename = f"{slug}.{_EXT.get(a.get('kind'), 'bin')}"
        return _send_bytes(handler, raw, "application/octet-stream", {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Cache-Control": "private, no-store",
        })
    except ArtifactError as exc:
        return _send_json(handler, {"error": exc.code}, exc.status)
    except (ValueError, KeyError, TypeError):
        return _send_json(handler, {"error": "service_error"}, 502)


def handle_post(handler, parsed, body: dict | None) -> bool:
    m = _ROUTE.match(parsed.path)
    if not m or m.group(2) != "share":
        return _send_json(handler, {"error": "not_found"}, 404)
    artifact_id = m.group(1).lower()
    try:
        _owned_detail(handler, artifact_id)
        hours = (body or {}).get("expires_in_hours", 168)
        try:
            hours = float(hours)
        except (TypeError, ValueError):
            return _send_json(handler, {"error": "invalid_expiry"}, 400)
        if not (0 < hours <= MAX_SHARE_HOURS):
            return _send_json(handler, {"error": "invalid_expiry"}, 400)
        _s, _h, raw = _request("POST", f"/artifacts/{artifact_id}/shares",
                               body={"expires_in_seconds": int(hours * 3600)})
        grant = json.loads(raw.decode("utf-8"))
        share = grant.get("share") or {}
        return _send_json(handler, {"url": grant.get("url"), "share": {
            "id": share.get("id"), "expires_at": share.get("expires_at")}})
    except ArtifactError as exc:
        return _send_json(handler, {"error": exc.code}, exc.status)
    except (ValueError, KeyError, TypeError):
        return _send_json(handler, {"error": "service_error"}, 502)


PROMPT = """
SynthPulse Artifacts (the Super Agent's artifacts, like Claude artifacts):
- When the answer is a finished deliverable the person will open, reuse or pass on (an interactive HTML page, dashboard, prototype, calculator page, one-pager, report with charts, a Markdown document of roughly 40 lines or more, an SVG diagram), publish it with the artifact_publish tool instead of pasting it into the reply (find the tool with tool_search when it is not loaded). Then put the chat_block it returns in your reply exactly once, verbatim, plus one or two sentences on what it is. Never repeat the artifact's source in the reply.
- HTML artifacts are one self-contained file: inline <style> and <script>, no external URLs, CDNs, web fonts or fetch (the preview has no network). Responsive, readable in light and dark, real content, no em or en dashes in visible text.
- Not an artifact: short answers (plain text), answer widgets inside the reply (interactive-ui and data blocks), Word, Excel, PowerPoint or PDF deliverables (SynthPulse Office).
- To change an artifact, read it with artifact_get, then publish a new version with the same title plus v2, v3. Only call artifact_share when the person explicitly asks for a link for someone else; the card has its own Share button. Details: skill synthpulse-artifacts.
""".strip()


def prompt_block() -> str:
    return PROMPT if configured() else ""
