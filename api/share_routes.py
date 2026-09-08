"""HTTP adapter for the existing sanitized, opt-in public snapshot store."""
from __future__ import annotations

import copy
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlencode

from api.helpers import bad, j, redact_session_data, _security_headers, _safe_write
from api import shares

# Serialize snapshot publication/revocation with the source metadata update.
_MUTATION_LOCK = threading.Lock()
_PUBLIC_PATH = re.compile(r"/(?:api/)?share/[A-Za-z0-9_-]{24}\Z")


def is_public_share_request(path, method):
    return method == "GET" and bool(_PUBLIC_PATH.fullmatch(path))


def handle_public(handler, parsed):
    if not is_public_share_request(parsed.path, "GET"):
        return False
    share = shares.load_share(parsed.path.rsplit("/", 1)[-1])
    headers = {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow",
               "Referrer-Policy": "no-referrer"}
    if share is None:
        return j(handler, {"error": "Shared conversation not found"}, status=404, extra_headers=headers)
    if parsed.path.startswith("/api/"):
        return j(handler, {"share": share}, extra_headers=headers)
    page = (Path(__file__).resolve().parent.parent / "static" / "share.html").read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(page)))
    _security_headers(handler, referrer_policy="no-referrer")
    for key, value in headers.items():
        if key != "Referrer-Policy":
            handler.send_header(key, value)
    _safe_write(handler, page)
    return True


def _session_pair(sid, handler):
    """Use the same visible external transcript as the session detail API."""
    from api import routes as r
    from api.auth import is_auth_enabled
    try:
        stored = r.get_session(sid)
    except KeyError:
        stored = None
    meta = (r._lookup_cli_session_metadata(sid) or {}) if stored is None or r._session_requires_cli_metadata_lookup(stored) else {}
    if stored is None:
        snapshot, reason = r._claim_or_synthesize_cli_session(sid, cli_meta=meta)
        if snapshot is None or reason == "was_webui":
            raise KeyError(sid)
    else:
        stored = r._ensure_full_session_before_mutation(sid, stored)
        snapshot = copy.copy(stored)
    if not r._session_visible_to_request(snapshot, handler):
        raise KeyError(sid)
    # Read/write participation is not permission to publish a conversation.
    if is_auth_enabled() and not r._group_participants_may_be_managed_by(snapshot, handler):
        raise KeyError(sid)
    messages = list(snapshot.messages or [])
    if r._is_messaging_session_record(snapshot) or r._is_messaging_session_record(meta) or not messages:
        external = r.get_cli_session_messages(sid, profile=getattr(snapshot, "profile", None))
        if external:
            messages = r._merged_session_messages_for_display(snapshot, external)
    snapshot.messages = copy.deepcopy(messages)
    if stored is None:
        # Sharing only creates a metadata sidecar; the original gateway/CLI
        # store continues to own its transcript.
        stored = r.Session(session_id=sid, title=snapshot.title, workspace=snapshot.workspace,
                           model=snapshot.model, model_provider=getattr(snapshot, "model_provider", None),
                           profile=getattr(snapshot, "profile", None), messages=[],
                           owner_email=getattr(snapshot, "owner_email", None),
                           created_at=snapshot.created_at, updated_at=snapshot.updated_at)
        for field in ("is_cli_session", "source_tag", "raw_source", "session_source", "source_label", "read_only"):
            setattr(stored, field, getattr(snapshot, field, None))
    return snapshot, stored


@contextmanager
def _source_scope(handler, snapshot, *, revoke=False):
    from api import profiles
    from api.governance.enforce import evaluate_request, _request_identity
    from api.workspace_access import ensure_session_workspace_access
    profile = str(getattr(snapshot, "profile", None) or "default")
    route = "/api/share/revoke" if revoke else "/api/share/create"
    decision = evaluate_request(_request_identity(handler), "POST", route + "?" + urlencode({"profile": profile}))
    if not decision.allow and decision.mode == "enforce":
        raise PermissionError("Source conversation profile is not allowed")
    previous = getattr(profiles._tls, "profile", None)
    profiles.set_request_profile(profile)
    try:
        ensure_session_workspace_access(handler, snapshot)
        yield
    finally:
        if previous is None:
            profiles.clear_request_profile()
        else:
            profiles.set_request_profile(previous)


def _check_media_access(handler, snapshot, candidate):
    from api.governance.enforce import _request_identity
    from api.governance.resource_access import ensure_file_access
    from api.personal_context import ensure_actor_path
    from api.upload import _attachment_root, _session_attachment_dir
    from api.workspace_access import ensure_workspace_access
    target = Path(candidate).resolve()
    if target.is_relative_to(_attachment_root().resolve()) and not target.is_relative_to(_session_attachment_dir(snapshot.session_id)):
        raise PermissionError("Attachments belong to another conversation")
    identity = _request_identity(handler)
    ensure_actor_path(identity, target, snapshot)
    ensure_file_access(identity, target)
    ensure_workspace_access(handler, target)
    return True


def handle_mutation(handler, body, *, revoke=False):
    from api import routes as r
    if not isinstance(body, dict):
        return bad(handler, "Request must be an object", 400)
    sid = body.get("session_id")
    if not isinstance(sid, str) or not r.is_safe_session_id(sid):
        return bad(handler, "A valid session_id is required", 400)
    try:
        with _MUTATION_LOCK, r._get_session_agent_lock(sid):
            snapshot, stored = _session_pair(sid, handler)
            with _source_scope(handler, snapshot, revoke=revoke):
                old_token, old_created = stored.share_token, stored.share_created_at
                if revoke:
                    shares.revoke_share(stored)
                    stored.share_token = stored.share_created_at = None
                    share_meta = None
                else:
                    def media_access_check(candidate):
                        return _check_media_access(handler, snapshot, candidate)

                    share_meta = shares.create_or_refresh_share(snapshot, media_access_check=media_access_check)
                    stored.share_token = share_meta["share_token"]
                    stored.share_created_at = share_meta["share_created_at"]
                try:
                    stored.save(touch_updated_at=False)
                except Exception:
                    # Never leave a newly published snapshot live without durable
                    # metadata through which its owner can revoke it.
                    if not revoke:
                        shares.revoke_share(stored)
                    stored.share_token, stored.share_created_at = old_token, old_created
                    raise
                r._publish_session_list_changed("session_share_revoke" if revoke else "session_share_create",
                                                profile=getattr(stored, "profile", None), session_id=sid)
                response = stored.compact() | {"messages": snapshot.messages}
                result = {"ok": True, "session": redact_session_data(response)}
                if share_meta:
                    result["share"] = {"token": share_meta["share_token"], "url": "/share/" + share_meta["share_token"],
                                       "title": share_meta["share_title"], "message_count": share_meta["share_message_count"],
                                       "created_at": share_meta["share_created_at"], "updated_at": share_meta["share_updated_at"]}
                return j(handler, result)
    except KeyError:
        return bad(handler, "Session not found", 404)
    except PermissionError:
        return bad(handler, "Sharing this conversation is not permitted", 403)
    except ValueError as exc:
        return bad(handler, str(exc), 400)
