"""Server-owned authority for an async job's later continuation.

Only authenticated worker entry creates these records. Async producers carry
an opaque reference; neither a model request nor an HTTP body supplies identity
or grants. Records stay outside session DTOs and chat/model context.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field, replace
import json
import os
import re
import threading
import time
import uuid


@dataclass
class _Authority:
    reference: str
    # Pending payload is private to the worker context. Ordinary chat turns
    # never persist it; only the trusted async producer calls current_ref().
    pending: dict | None = None
    lock: object = field(default_factory=threading.Lock)


_CURRENT_REF: ContextVar[_Authority | None] = ContextVar("webui_continuation_ref", default=None)
_CREATION_LOCK = threading.Lock()
MAX_AUTHORITY_RECORDS = 10000


def current_ref() -> str:
    """Capture authority durably when an actual async job is being created."""
    authority = _CURRENT_REF.get()
    if authority is None:
        return ""
    with authority.lock:
        if authority.pending is not None:
            directory = _directory()
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            from api.turn_journal import _journal_file_lock
            with _CREATION_LOCK:
                lock_fd = os.open(directory / ".creation.lock", os.O_WRONLY | os.O_CREAT, 0o600)
                with os.fdopen(lock_fd, "w") as lock_file, _journal_file_lock(lock_file):
                    if sum(1 for _ in directory.glob("*.json")) >= MAX_AUTHORITY_RECORDS:
                        raise PermissionError("Async authority storage is full; archive completed job authority before delegating")
                    authority.pending["created_at"] = time.time()
                    payload = json.dumps(authority.pending, ensure_ascii=False).encode("utf-8")
                    if len(payload) > 256000:
                        raise PermissionError("Async continuation authority is too large")
                    path = directory / (authority.reference + ".json")
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    try:
                        with os.fdopen(fd, "wb") as output:
                            output.write(payload)
                            output.flush()
                            os.fsync(output.fileno())
                    except BaseException:
                        path.unlink(missing_ok=True)
                        raise
            authority.pending = None
    return authority.reference


def _directory():
    from api.config import STATE_DIR
    return STATE_DIR / "continuation-authority"


def _identity(value):
    if not isinstance(value, dict):
        raise PermissionError("Authenticated continuation identity is unavailable")
    email = str(value.get("email") or "").strip().lower()
    method = str(value.get("method") or "")
    if not email and method != "auth_disabled":
        raise PermissionError("Authenticated continuation identity is unavailable")
    groups = value.get("groups") or []
    if not isinstance(groups, (list, tuple)) or any(not isinstance(g, str) for g in groups):
        raise PermissionError("Invalid continuation group identity")
    claims = value.get("claims_subset") or {}
    return {"email": email, "groups": sorted(set(groups)), "method": method,
            "claims_subset": {key: str(claims[key]) for key in ("sub", "name")
                              if isinstance(claims, dict) and claims.get(key)}}


def _same_session(record, session):
    return (record.get("session_id") == session.session_id
            and record.get("session_profile") == str(getattr(session, "profile", None) or "default")
            and record.get("owner_email") == str(getattr(session, "owner_email", None) or "").lower())


def resolve(reference, session):
    """Recheck local policy/membership using the original authenticated claims.

    This does not refresh the IdP token or query current external SSO groups.
    """
    if not isinstance(reference, str) or not re.fullmatch(r"[a-f0-9]{32}", reference):
        raise PermissionError("Async continuation authority is unavailable")
    try:
        path = _directory() / (reference + ".json")
        if path.stat().st_size > 256000:
            raise ValueError("Oversize continuation authority")
        record = json.loads(path.read_text())
    except (OSError, ValueError, TypeError):
        raise PermissionError("Async continuation authority is unavailable") from None
    if not isinstance(record, dict) or record.get("version") != 1 or not _same_session(record, session):
        raise PermissionError("Async continuation authority does not match this conversation")
    identity = _identity(record.get("identity"))
    from api import auth
    if auth.is_auth_enabled() and (not identity["email"] or identity["method"] == "auth_disabled"):
        raise PermissionError("Async continuation requires authentication")
    if identity["email"]:
        from api.group_chat import require_turn_membership, bot_allowed, normalize_bots
        require_turn_membership(session, identity)
        bot = record.get("execution_profile")
        if bot and (bot not in normalize_bots(getattr(session, "bot_participants", None))
                    or not bot_allowed(identity, bot)):
            raise PermissionError("Async continuation bot membership was revoked")
    from .enforce import evaluate_request, is_profile_allowed_for
    decision = evaluate_request(identity, "POST", "/api/chat/start")
    if not decision.allow and decision.mode != "report_only":
        raise PermissionError("Async continuation access was revoked")
    if not is_profile_allowed_for(identity, record["active_profile"]):
        raise PermissionError("Async continuation profile access was revoked")
    record["identity"] = identity
    from api.workspace_access import runtime_workspace_scope
    workspace, workspace_check = runtime_workspace_scope(session, identity)
    if workspace and workspace_check(workspace) is not True:
        raise PermissionError("Async continuation workspace membership was revoked")
    return record


def begin_turn(session, identity, *, active_profile, execution_profile=None,
               request_id="", reference=None):
    """Bind the trusted ref and retain the initiating job's original ceiling.

    Called after ordinary fresh governance binding and before agent creation.
    Reusing the original reference across continuations preserves its ceiling
    without growing an unbounded chain of equivalent snapshots.
    """
    from .agent_context import _agent_governance_module, _translate_context
    from . import loader
    agent_mod = _agent_governance_module()
    identity = _identity(identity)
    fresh = agent_mod.current_governance_context()
    token = None
    if reference:
        record = resolve(reference, session)
        if record["identity"] != identity or record["active_profile"] != active_profile:
            raise PermissionError("Async continuation actor or execution profile changed")
        if fresh is None:
            fresh = _translate_context(agent_mod, loader.get_policy(), identity["email"],
                                       tuple(identity["groups"]), active_profile, session.session_id, request_id)
        if "continuation_contexts" not in getattr(fresh, "__dataclass_fields__", {}):
            raise PermissionError("Engine does not support governed continuations")
        token = agent_mod.bind_governance_context(replace(fresh, continuation_contexts=(record["context"],)))
    else:
        original = fresh or _translate_context(agent_mod, loader.get_policy(), identity["email"],
                                              tuple(identity["groups"]), active_profile, session.session_id, request_id)
        reference = uuid.uuid4().hex
        record = {"version": 1, "session_id": session.session_id,
                  "session_profile": str(getattr(session, "profile", None) or "default"),
                  "owner_email": str(getattr(session, "owner_email", None) or "").lower(),
                  "active_profile": active_profile, "execution_profile": execution_profile,
                  "identity": identity, "context": agent_mod.serialize_context_for_env(original)}
    authority = _Authority(reference, pending=None if token is not None else record)
    return _CURRENT_REF.set(authority), agent_mod, token


def end_turn(tokens):
    if tokens is None:
        return
    context_token, agent_mod, governance_token = tokens
    _CURRENT_REF.reset(context_token)
    if governance_token is not None:
        agent_mod.reset_governance_context(governance_token)
