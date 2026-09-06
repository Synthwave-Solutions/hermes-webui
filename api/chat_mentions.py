"""Prepare recipients without publishing a private conversation's history."""
import hashlib
import json
import threading
import uuid
from pathlib import Path

_LOCK = threading.RLock()
_RECENT = {}


def prepare(handler, body):
    from api import routes
    from api.config import STATE_DIR
    from api.group_chat import validate, validate_bots, require_turn_membership
    from api.ownership import request_owner_email
    from api.profiles import _is_isolated_profile_mode, _isolated_profile_name
    from api.helpers import get_profile_cookie
    from api.project_collaboration import project_for

    from api.governance.enforce import evaluate_request, _request_identity
    identity = _request_identity(handler)
    for path in ("/api/chat/mentions/prepare", "/api/session/new"):
        if not evaluate_request(identity, "POST", path).allow:
            raise PermissionError("Chat and conversation write permissions required")
    actor = request_owner_email(handler)
    if not actor:
        raise PermissionError("Authenticated identity required")
    if not isinstance(body, dict) or set(body) - {"session_id", "participants", "bot_participants", "request_id", "model", "model_provider", "chat_mode"}:
        raise ValueError("Invalid mention request")
    try:
        request_id = str(uuid.UUID(str(body.get("request_id", ""))))
    except ValueError:
        raise ValueError("request_id must be a UUID") from None
    fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    cache_key = (actor, request_id)
    with _LOCK:
        prior = _RECENT.get(cache_key)
        if prior:
            if prior[0] != fingerprint:
                raise RuntimeError("This request_id was already used for different recipients")
            session = routes.get_session(prior[1])
            require_turn_membership(session, actor)
            validate_bots(body.get("bot_participants", []), actor)
            return {"session": session.compact() | {"messages": session.messages}, "created": prior[2]}
        sid = body.get("session_id")
        if sid is not None and (not isinstance(sid, str) or not routes.is_safe_session_id(sid)):
            raise ValueError("Invalid session_id")
        session = routes.get_session(sid) if sid else None
        lock = routes._get_session_agent_lock(sid) if sid else _LOCK
        with lock:
            if sid:
                session = routes.get_session(sid)
                require_turn_membership(session, actor)
                if not routes._session_visible_to_request(session, handler):
                    raise PermissionError("Conversation unavailable")
                if getattr(session, "read_only", False) or getattr(session, "is_read_only", False):
                    raise PermissionError("Read-only conversations cannot change recipients")
                if routes._session_is_subagent_view_only(sid):
                    raise PermissionError("Subagent conversations are read-only")
                if getattr(session, "active_stream_id", None):
                    raise RuntimeError("Wait for the active response before changing recipients")
            people, error = validate(body.get("participants", []), owner_email=actor)
            if error:
                raise ValueError(error)
            bots = validate_bots(body.get("bot_participants", []), actor)
            if not people and not bots:
                raise ValueError("Select at least one recipient")
            current_people = list(getattr(session, "participants", []) or []) if session else []
            current_bots = list(getattr(session, "bot_participants", []) or []) if session else []
            shared = bool(current_people or (getattr(session, "project_id", None) and
                          (project_for(session.project_id) or {}).get("collaboration")))
            created = session is None or (bool(people) and not shared)
            if created:
                model, provider = ((getattr(session, "model", None), getattr(session, "model_provider", None))
                    if session else routes._session_model_state_from_request(body.get("model"), body.get("model_provider")))
                mode = getattr(session, "chat_mode", None) if session else (
                    routes._validate_chat_mode(body["chat_mode"]) if body.get("chat_mode") is not None else None)
                profile = bots[0] if bots else (getattr(session, "profile", None) or
                    (_isolated_profile_name() if _is_isolated_profile_mode() else get_profile_cookie(handler) or "default"))
                validate_bots([profile], actor)
                workspace = Path(STATE_DIR) / "group_workspaces" / uuid.uuid4().hex
                workspace.mkdir(parents=True, mode=0o700)
                session = routes.new_session(workspace=str(workspace), profile=profile,
                    model=model, model_provider=provider, chat_mode=mode)
                session.owner_email = actor
                session.participants = people
                session.bot_participants = bots or [profile]
                session.save()
                routes._audit_group_participants(handler, session, [], people, "mention_group_new")
                routes._audit_group_participants(handler, session, [], ["bot:"+b for b in session.bot_participants], "mention_bots")
            else:
                owner = str(getattr(session, "owner_email", "") or "").lower()
                additions = [p for p in people if p != owner and p not in current_people]
                bot_additions = [b for b in bots if b not in current_bots]
                if additions or bot_additions:
                    if getattr(session, "project_id", None):
                        raise PermissionError("Change project recipients in the project controls")
                    if not routes._group_participants_may_be_managed_by(session, handler):
                        raise PermissionError("Only the conversation owner can add recipients")
                    merged, error = validate(current_people + additions, owner_email=owner)
                    if error:
                        raise ValueError(error)
                    merged_bots = validate_bots(current_bots + bot_additions, actor)
                    session.participants = merged
                    session.bot_participants = merged_bots
                    session.save()
                    routes._audit_group_participants(handler, session, current_people, merged, "mention_recipients")
                    routes._audit_group_participants(handler, session, ["bot:"+b for b in current_bots],
                                                    ["bot:"+b for b in merged_bots], "mention_bots")
            routes._on_session_list_changed(getattr(session, "profile", None))
            routes.publish_session_list_changed("mention_recipients", profile=getattr(session, "profile", None),
                                                session_id=session.session_id)
            _RECENT[cache_key] = (fingerprint, session.session_id, created)
            if len(_RECENT) > 256:
                _RECENT.pop(next(iter(_RECENT)))
            return {"session": session.compact() | {"messages": session.messages}, "created": created}
