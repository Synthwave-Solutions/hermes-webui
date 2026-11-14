"""Personal results for Studio, projected from delivered messages in job chats."""
from heapq import nlargest

from api import cron_bots, cron_webui_delivery as delivery
from api.config import load_settings
from api.helpers import _redact_text, bad, j
from api.models import get_session, get_session_for_scan, is_safe_session_id
from api.ownership import request_owner_email
from api.project_collaboration import session_access_checker

HOME_LIMIT = 12


def _results(session, link):
    seen = set()
    for message in reversed(session.messages):
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        run = message.get("cron_delivery")
        if not isinstance(run, dict) or run.get("job_id") != link["job_id"] or run.get("status") != "ok":
            continue
        if run.get("profile") and cron_bots.normalize_profile(run["profile"]) != link["profile"]:
            continue
        at = delivery.parse_run_at(run.get("run_at"))
        if not at or at in seen:
            continue
        # The delivery bridge also posts failure/empty-result notices into this
        # chat. Only the successful result envelope contains a personal report.
        text = message.get("content")
        if not isinstance(text, str):
            continue
        header, separator, body = text.replace("\r\n", "\n").partition("\n\n")
        if not separator or not header.startswith(delivery.RESULT_HEADING):
            continue
        body = delivery.scout_report_body(body)
        if not body or delivery._is_silent_response(body):
            continue
        seen.add(at)
        yield {"session_id": session.session_id, "profile": link["profile"],
               "run_at": run["run_at"], "at": at.timestamp(), "body": body}


def _personal_results(email, allowed_profile):
    project_access = session_access_checker(email)

    def eligible(session, key, sid):
        if session is None or session.session_id != sid or str(session.owner_email or "").strip().lower() != email or session.archived:
            return None
        link = cron_bots.normalize_job_link(session.cron_job)
        if not link or link.get("kind") != "scout" or link["profile"] != cron_bots.normalize_profile(session.profile):
            return None
        if cron_bots._chat_key(link["job_id"], link["profile"]) != key or project_access(session) is False:
            return None
        return link

    for key, entry in cron_bots._load_chats(strict=True)["chats"].items():
        if not isinstance(entry, dict) or str(entry.get("owner_email") or "").strip().lower() != email:
            continue
        sid = entry.get("session_id")
        profile, separator, _ = key.partition("/")
        if not separator or not is_safe_session_id(sid) or not allowed_profile(profile):
            continue
        try:
            metadata = get_session(sid, metadata_only=True)
        except KeyError:
            continue
        if eligible(metadata, key, sid):
            session = get_session_for_scan(sid)
            link = eligible(session, key, sid)
            if link:
                yield from _results(session, link)


def handle(handler):
    from api.routes import _chat_profile_target_allowed, _is_isolated_profile_mode, _session_visible_to_active_profile

    email = str(request_owner_email(handler) or "").strip().lower()
    if not email:
        return j(handler, {"findings": []}, extra_headers={"Cache-Control": "private, no-store"})
    allowed = {}
    isolated = _is_isolated_profile_mode()

    def allowed_profile(profile):
        if profile not in allowed:
            allowed[profile] = ((not isolated or _session_visible_to_active_profile(profile, handler))
                                and _chat_profile_target_allowed(handler, profile))
        return allowed[profile]

    try:
        rows = nlargest(HOME_LIMIT, _personal_results(email, allowed_profile),
                        key=lambda row: (row["at"], row["session_id"]))
        redact = bool(load_settings().get("api_redact_enabled", True))
        labels = {}
        for row in rows:
            profile = row["profile"]
            if profile not in labels:
                labels[profile] = _redact_text(cron_bots.bot_label(profile), _enabled=redact)
            row["bot"] = labels[profile]
            row["body"] = delivery._truncate_body(_redact_text(row["body"], _enabled=redact))
        return j(handler, {"findings": rows}, extra_headers={"Cache-Control": "private, no-store"})
    except (OSError, ValueError):
        return bad(handler, "Personal findings could not be loaded", 503)
