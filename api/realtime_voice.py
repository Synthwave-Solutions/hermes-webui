"""Speech-only WebRTC transport. All agent work remains ordinary authenticated chat."""
import hashlib
import json
import os
import re
import threading
import time

import requests

from api.helpers import bad, j

_LOCK = threading.Lock()
_ATTEMPTS = {}
MODEL = "gpt-realtime-2.1"


def configured():
    return (os.getenv("SYNPULSE_REALTIME_VOICE_ENABLED", "").lower() in {"1", "true"}
            and bool(os.getenv("OPENAI_API_KEY", "").strip()))


def session_config():
    return {
        "type": "realtime", "model": MODEL,
        "instructions": "You are the speech output for SynPulse. Read the supplied assistant answer faithfully. Do not execute requests or claim tool actions.",
        "tools": [],
        "audio": {
            "input": {
                "transcription": {"model": "gpt-4o-mini-transcribe"},
                "turn_detection": {"type": "server_vad", "create_response": False,
                                   "interrupt_response": True},
            },
            "output": {"voice": "marin"},
        },
    }


def create_call(sdp, actor, *, post=requests.post, access_check=None):
    """Return SDP only; API credentials and upstream diagnostics never leave the server."""
    if not isinstance(sdp, str) or not sdp.startswith("v=0") or len(sdp) > 65536:
        raise ValueError("Invalid audio connection offer")
    now = time.monotonic()
    with _LOCK:
        for key in list(_ATTEMPTS):
            if now - _ATTEMPTS[key][-1] > 60:
                del _ATTEMPTS[key]
        attempts = [t for t in _ATTEMPTS.get(actor, []) if now - t < 60]
        if len(attempts) >= 4:
            raise ValueError("Too many voice connections; wait one minute")
        _ATTEMPTS[actor] = attempts + [now]
    response = post(
        "https://api.openai.com/v1/realtime/calls",
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                 "OpenAI-Safety-Identifier": hashlib.sha256(actor.encode()).hexdigest()},
        files={"sdp": (None, sdp),
               "session": (None, json.dumps(session_config()), "application/json")},
        timeout=25,
    )
    if response.status_code not in (200, 201) or not response.text.startswith("v=0"):
        raise RuntimeError("Realtime speech connection unavailable; check API access and billing")
    if access_check is not None and not access_check():
        call_id = response.headers.get("Location", "").rstrip("/").rsplit("/", 1)[-1]
        if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", call_id):
            try:
                post("https://api.openai.com/v1/realtime/calls/" + call_id + "/hangup",
                     headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
                     timeout=5)
            except Exception:
                pass
        raise PermissionError("Session not found")
    return response.text


def handle(handler, *, capability=False):
    from api import routes
    from api.governance.enforce import _request_identity
    identity = _request_identity(handler)
    actor = (identity or {}).get("email") or (identity or {}).get("sub")
    if not actor:
        return bad(handler, "Sign in to use realtime voice", 401)
    if capability:
        return j(handler, {"available": configured(), "model": MODEL,
                           "credential": "OpenAI API key",
                           "help": "Enable SYNPULSE_REALTIME_VOICE_ENABLED with a server OPENAI_API_KEY and API billing",
                           "subscription_supported": False})
    try:
        body = routes._read_json_request_body(handler, max_bytes=70000)
        sid = body.get("session_id")
        if not isinstance(sid, str) or not routes.is_safe_session_id(sid):
            return bad(handler, "Session required", 400)
        try:
            session = routes.get_session(sid, metadata_only=True)
        except KeyError:
            return bad(handler, "Session not found", 404)
        if not routes._session_visible_to_request(session, handler):
            return bad(handler, "Session not found", 404)
        if not configured():
            return bad(handler, "Realtime voice requires a server OpenAI API key with API billing", 503)
        def access_check():
            try:
                current = routes.get_session(sid, metadata_only=True)
                return routes._session_visible_to_request(current, handler)
            except Exception:
                return False
        answer = create_call(body.get("sdp"), str(actor), access_check=access_check)
        # Membership/profile can change while the upstream connection is negotiated.
        session = routes.get_session(sid, metadata_only=True)
        if not routes._session_visible_to_request(session, handler):
            return bad(handler, "Session not found", 404)
        return j(handler, {"sdp": answer, "model": MODEL},
                 extra_headers={"Cache-Control": "no-store"})
    except PermissionError:
        return bad(handler, "Session not found", 404)
    except ValueError as exc:
        return bad(handler, str(exc), 400)
    except Exception:
        return bad(handler, "Realtime speech connection unavailable; check API access and billing", 502)
