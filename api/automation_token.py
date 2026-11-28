"""Narrow, fail-closed service token for the inbound-offer automation.

One token, stored as an HMAC hash in STATE_DIR/automation_token.json (0600).
It is accepted as ``Authorization: Bearer <token>`` only for a small route
allowlist, only from loopback, and acts as the configured owner e-mail with no
elevation. The token itself is never stored, logged, audited or put in an
error message.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import tempfile
import threading
import time
from datetime import datetime, timezone
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)

TOKEN_PREFIX = "hat_"
MAX_TOKEN_LEN = 200
MAX_SESSION_IDS = 5000
CTX_ATTR = "_automation_ctx"

# (method, path) pairs a bearer token may call.
ALLOWLIST = frozenset({
    ("POST", "/api/session/import"),
    ("POST", "/api/session/participants"),
    ("POST", "/api/session/delete"),
    ("GET", "/api/session"),
    ("GET", "/api/file/raw"),
})
# Routes whose session_id (query string) must belong to this token.
QUERY_SCOPED = frozenset({("GET", "/api/session"), ("GET", "/api/file/raw")})

_LOCK = threading.Lock()


def _state_dir():
    from api.config import STATE_DIR

    return STATE_DIR


def token_path():
    return _state_dir() / "automation_token.json"


def _hash_token(token: str) -> str:
    from api.auth import _signing_key

    return hmac.new(
        _signing_key(), b"automation-token:" + token.encode("utf-8"), hashlib.sha256
    ).hexdigest()


class _FileLock:
    def __init__(self):
        self._fh = None

    def __enter__(self):
        _LOCK.acquire()
        try:
            import fcntl

            p = token_path().with_suffix(".json.lock")
            p.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(p), os.O_CREAT | os.O_RDWR, 0o600)
            self._fh = os.fdopen(fd, "r+")
            fcntl.flock(self._fh, fcntl.LOCK_EX)
        except ImportError:
            self._fh = None
        return self

    def __exit__(self, *exc):
        try:
            if self._fh:
                self._fh.close()
        finally:
            _LOCK.release()


def _load() -> dict | None:
    try:
        data = json.loads(token_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _save(data: dict) -> None:
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".automation_token.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _active(data: dict | None) -> bool:
    if not data or not data.get("token_hash") or data.get("revoked_at"):
        return False
    exp = data.get("expires_at")
    if exp:
        try:
            if datetime.fromisoformat(exp).timestamp() <= time.time():
                return False
        except ValueError:
            return False
    return True


def _known_owner(email: str) -> bool:
    try:
        from api.group_chat import known_emails

        return email in known_emails()
    except Exception:
        return False


# ── management (used by scripts/automation_token.py) ───────────────────────

def create(owner_email: str, label: str, days: int | None = None, *, rotate: bool = False) -> str:
    owner = (owner_email or "").strip().lower()
    label = (label or "").strip()
    if not owner or not label:
        raise ValueError("owner and label are required")
    if not _known_owner(owner):
        raise ValueError("owner is not a user known to governance")
    if days is not None and days <= 0:
        raise ValueError("days must be positive")
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    with _FileLock():
        old = _load()
        if _active(old) and not rotate:
            raise ValueError("an active token exists; use --rotate or revoke it first")
        created = datetime.now(timezone.utc)
        data = {
            "token_hash": _hash_token(token),
            "owner_email": owner,
            "label": label[:80],
            "created_at": created.isoformat(),
            "expires_at": (
                datetime.fromtimestamp(created.timestamp() + days * 86400, timezone.utc).isoformat()
                if days else None
            ),
            "session_ids": list((old or {}).get("session_ids") or [])[-MAX_SESSION_IDS:],
        }
        _save(data)
    return token


def revoke() -> bool:
    with _FileLock():
        data = _load()
        if not data:
            return False
        data["token_hash"] = ""
        data["revoked_at"] = _now_iso()
        _save(data)
    return True


def status() -> dict:
    data = _load()
    if not data:
        return {"exists": False, "active": False}
    return {
        "exists": True,
        "active": _active(data),
        "label": data.get("label"),
        "owner_email": data.get("owner_email"),
        "created_at": data.get("created_at"),
        "expires_at": data.get("expires_at"),
        "revoked_at": data.get("revoked_at"),
        "session_count": len(data.get("session_ids") or []),
    }


# ── per-request use ────────────────────────────────────────────────────────

def record_session(sid: str) -> None:
    with _FileLock():
        data = _load()
        if not data:
            return
        ids = list(data.get("session_ids") or [])
        if sid not in ids:
            ids.append(sid)
        data["session_ids"] = ids[-MAX_SESSION_IDS:]
        _save(data)


def owns_session(sid: str) -> bool:
    data = _load()
    return bool(sid and _active(data) and sid in (data.get("session_ids") or []))


def get_ctx(handler) -> dict | None:
    return getattr(handler, CTX_ATTR, None)


def _bearer_value(handler) -> str | None:
    raw = handler.headers.get("Authorization") if getattr(handler, "headers", None) else None
    if not raw:
        return None
    raw = str(raw)
    if raw[:7].lower() != "bearer ":
        return None
    return raw[7:].strip()


def has_bearer(handler) -> bool:
    return _bearer_value(handler) is not None


def audit(handler_or_ctx, method: str, path: str, outcome: str, session_id: str = "") -> None:
    """Write one audit row. Carries route, session id, outcome and label only."""
    try:
        from api.governance.audit import append_audit_event

        ctx = handler_or_ctx if isinstance(handler_or_ctx, dict) else (get_ctx(handler_or_ctx) or {})
        append_audit_event(
            "automation_token_request",
            subject_email=str(ctx.get("owner_email") or ""),
            path=path,
            method=method,
            reason=outcome,
            extra={
                "session_id": str(session_id or "")[:80],
                "outcome": outcome,
                "label": str(ctx.get("label") or ""),
            },
        )
    except Exception:
        logger.debug("automation token audit failed", exc_info=True)


def _reply(handler, status: int, error: str) -> None:
    body = json.dumps({"error": error}).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _client_ip(handler) -> str:
    try:
        return str(handler.client_address[0])
    except Exception:
        return ""


def authenticate(handler, parsed) -> bool:
    """Handle a request that carries a bearer header. True = proceed.

    On False a response has already been sent. Sets ``handler._automation_ctx``
    only when every check passed.
    """
    from api import auth

    method = str(getattr(handler, "command", "GET") or "GET").upper()
    path = parsed.path
    deny = {"owner_email": "", "label": ""}
    ip = _client_ip(handler)

    # Loopback only, and never through a forwarding proxy.
    if not auth._is_loopback(ip) or any(
        handler.headers.get(h) for h in ("X-Forwarded-For", "X-Real-IP", "Forwarded")
    ):
        audit(deny, method, path, "denied_not_loopback")
        _reply(handler, 403, "forbidden")
        return False
    if not auth._check_login_rate(ip):
        audit(deny, method, path, "denied_rate_limited")
        _reply(handler, 429, "Too many attempts")
        return False
    if (method, path) not in ALLOWLIST:
        audit(deny, method, path, "denied_route_not_allowed")
        _reply(handler, 403, "forbidden")
        return False

    presented = _bearer_value(handler) or ""
    data = _load()
    stored = (data or {}).get("token_hash") or ""
    ok = False
    if presented and len(presented) <= MAX_TOKEN_LEN:
        try:
            candidate = _hash_token(presented)
            ok = hmac.compare_digest(candidate, stored or ("0" * len(candidate)))
        except Exception:
            ok = False
    ok = bool(ok and stored and _active(data))
    owner = str((data or {}).get("owner_email") or "").strip().lower()
    if ok and not _known_owner(owner):
        ok = False
    if not ok:
        auth._record_login_attempt(ip)
        audit(deny, method, path, "denied_invalid_token")
        _reply(handler, 401, "Authentication required")
        return False

    ctx = {"owner_email": owner, "label": str(data.get("label") or "")}
    sid = ""
    if (method, path) in QUERY_SCOPED:
        sid = (parse_qs(parsed.query).get("session_id") or [""])[0]
        if not sid or sid not in (data.get("session_ids") or []):
            audit(ctx, method, path, "denied_session_not_owned", sid)
            _reply(handler, 403, "forbidden")
            return False
    audit(ctx, method, path, "accepted", sid)
    setattr(handler, CTX_ATTR, ctx)
    return True


def reset_ctx(handler) -> None:
    try:
        setattr(handler, CTX_ATTR, None)
    except Exception:
        pass


def session_gate(handler, sid: str) -> bool:
    """For bearer requests: True only when the session was created by this token.

    Always True for non-bearer requests.
    """
    ctx = get_ctx(handler)
    if not ctx:
        return True
    if owns_session(str(sid or "")):
        audit(ctx, str(getattr(handler, "command", "") or "POST"),
              "session_gate", "session_authorized", str(sid or ""))
        return True
    audit(ctx, str(getattr(handler, "command", "") or "POST"),
          "session_gate", "denied_session_not_owned", str(sid or ""))
    return False


def identity(handler) -> dict | None:
    ctx = get_ctx(handler)
    if not ctx or not ctx.get("owner_email"):
        return None
    return {
        "email": ctx["owner_email"],
        "groups": [],
        "claims_subset": {},
        "method": "automation_token",
    }
