"""Group conversations: one chat, several people from the organisation.

A conversation has exactly one ``owner_email`` (its creator) and, from here on,
an optional ``participants`` list: other people in the organisation who can open
the conversation and write in it. Ownership is unchanged, so every existing
conversation keeps behaving exactly as it did; a chat becomes a group chat only
when somebody is named in it.

Two rules make this safe to add on top of per-user isolation:

* Being named lets a person SEE and WRITE. It never lends them the owner's
  rights: each turn runs under the governance of whoever sent that message
  (api/routes.py passes the sender to the streaming worker), so a participant
  can do in a group chat exactly what they could do in their own chat, and
  nothing more.
* Only people the governance policy already knows can be named. A stranger's
  address cannot be typed into a conversation, and a colleague who is removed
  from the policy stops being reachable here too.
"""

from __future__ import annotations

import collections
import logging
import re
import threading
import time
import unicodedata

logger = logging.getLogger(__name__)

# A conversation people actually work in, not a mailing list. The cap keeps the
# blast radius of one mistaken pick small and keeps the participant chips
# readable in the composer.
MAX_PARTICIPANTS = 25

_MENTION_RE = re.compile(r'^\s*@([A-Za-z0-9][A-Za-z0-9_-]{0,63})(?=\s|$)')
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean(value) -> str:
    return str((value.get("email") if isinstance(value, dict) else value) or "").strip().lower()


def normalize(values, *, owner_email=None) -> list:
    """Return the participant list as stored: lowercased, deduped, ordered.

    The owner is dropped if named: they are already in the conversation by
    owning it, and storing them twice would make "remove me" ambiguous.
    """
    owner = _clean(owner_email)
    out: list[str] = []
    if not isinstance(values, (list, tuple, set, frozenset)):
        return out
    for raw in values:
        email = _clean(raw)
        if not email or email == owner or email in out:
            continue
        if not _EMAIL_RE.match(email):
            continue
        out.append(email)
        if len(out) >= MAX_PARTICIPANTS:
            break
    return out


def participants_of(session_or_row) -> list:
    """The participant list of a Session object or an index row, never None."""
    if session_or_row is None:
        return []
    if isinstance(session_or_row, dict):
        raw = session_or_row.get("participants")
        owner = session_or_row.get("owner_email")
    else:
        raw = getattr(session_or_row, "participants", None)
        owner = getattr(session_or_row, "owner_email", None)
    return normalize(raw, owner_email=owner)


def is_member(owner_email, participants, email) -> bool:
    """Whether ``email`` owns this conversation or was named in it."""
    who = _clean(email)
    if not who:
        return False
    if who == _clean(owner_email):
        return True
    return who in normalize(participants, owner_email=owner_email)


def visible_to_scope(owner_email, participants, owner_scope) -> bool:
    """Ownership visibility, widened by participation.

    ``owner_scope`` follows api.ownership.request_owner_scope: "all" for admins
    and identity-less requests, otherwise the caller's email. Unowned rows stay
    admin-only exactly as before, because an unowned row has no one who could
    have named a participant.
    """
    scope = _clean(owner_scope)
    if scope == "all":
        return True
    if not scope:
        return False
    owner = _clean(owner_email)
    if not owner:
        # Legacy, cron and CLI rows have no owner, so nobody could have named a
        # participant on them. Reading a participant list off such a row would
        # widen exactly the rows that are deliberately admin-only.
        return False
    if owner == scope:
        return True
    return scope in normalize(participants, owner_email=owner)


def shared_profile_visible(session_or_row, email) -> bool:
    """Explicit group membership intersects existing bot/profile permission."""
    who = _clean(email)
    row = session_or_row if isinstance(session_or_row, dict) else vars(session_or_row)
    participants = participants_of(row)
    if not (participants or row.get('bot_participants')) or not is_member(row.get('owner_email'), participants, who):
        return False
    bots = normalize_bots(row.get('bot_participants'))
    return any(bot_allowed(who, bot) for bot in bots) if bots else bot_allowed(who, str(row.get('profile') or 'default'))


def bot_allowed(email, profile) -> bool:
    from api.bot_builder import allowed as _managed_allowed
    try:
        result = _managed_allowed(email if isinstance(email, dict) else {"email": email}, profile)
        if result is not None:
            return result
    except Exception:
        return False
    who = _clean(email)
    if not who:
        return False
    try:
        from api.governance.loader import get_policy
        from api.governance.enforce import subject_from_identity
        from api.governance.resolver import resolve_effective_access
        policy = get_policy()
        if not policy.enabled:
            return who in known_emails()
        access = resolve_effective_access(policy, subject_from_identity(email if isinstance(email, dict) else {'email': who}))
        return access.is_profile_allowed(profile or 'default')
    except Exception:
        return False


def normalize_bots(values) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return list(dict.fromkeys(str(v).strip() for v in values if isinstance(v, str)
                             and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', v.strip())))[:6]


def validate_bots(values, actor) -> list[str]:
    if values is None:
        return []
    bots = normalize_bots(values)
    if not isinstance(values, list) or any(not isinstance(v, str) for v in values) or len(values) > 6 or len(bots) != len(set(values)):
        raise ValueError('Select up to six valid bots')
    from api.profiles import get_hermes_home_for_profile
    for bot in bots:
        if not bot_allowed(actor, bot) or not (get_hermes_home_for_profile(bot) / 'config.yaml').is_file():
            raise ValueError('Bot is unavailable or not allowed: ' + bot)
    return bots


def selected_bot(session, message, actor) -> str | None:
    """The bot a group turn runs as, or None when the chat has no bots.

    Same decision as :func:`select_bot_with_reason`, without the reason.
    """
    return select_bot_with_reason(session, message, actor)[0]


# ── Group routing (plan 5.2, Wave 1) ──
# A group turn goes to the bot the message names, else the chat's only bot,
# else the bot that answered last (sticky), else the chat's default bot. A bot
# the sender may not use is skipped, never silently used; when nothing is left
# the sender is asked to choose a bot. The reason is shown on the reply, and
# the bot is announced to every open tab while it works (``turn_bot``).

ROUTE_REASONS = ("mention", "only_bot", "sticky", "default")
CHOOSE_BOT_ERROR = 'Choose one group bot by starting the message with @bot-id'
LAST_BOT_UNAVAILABLE_ERROR = 'The last bot is not available to you. Choose a bot to continue.'
_BOT_ID_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}')
_HANDLE_MAX = 64
# Remembered routes of recent turns, keyed by stream id (see remember_route_reason).
_ROUTES: "collections.OrderedDict[str, dict]" = collections.OrderedDict()
_ROUTES_LOCK = threading.Lock()
_ROUTES_MAX = 512
_ROUTES_IDLE_SECONDS = 900


def _slug(text) -> str:
    folded = unicodedata.normalize('NFKD', str(text or ''))
    folded = re.sub('[\u0300-\u036f]', '', folded).lower()
    return re.sub(r'[^a-z0-9]+', '-', folded).strip('-')


def _denied_handle_parts() -> tuple:
    try:
        from api.modules import DISPLAY_DENYLIST
    except Exception:
        return ()
    return tuple(part for part in (_slug(name) for name in DISPLAY_DENYLIST) if part)


def handle_from_text(text) -> str:
    """A mention handle made from display text: its slug without internal names.

    Every name on the internal-name denylist (plan E.4.3) is cut out, so a
    handle never shows a component name. static/chat-bots.js computes the same
    handle in the browser; tests keep both in step.
    """
    handle = _slug(text)
    denied = _denied_handle_parts()
    changed = True
    while changed:
        changed = False
        for part in denied:
            if part in handle:
                handle = handle.replace(part, '-')
                changed = True
        handle = re.sub('-+', '-', handle).strip('-')
    return handle[:_HANDLE_MAX].strip('-')


def bot_title(profile) -> str | None:
    """The title the bot's owner gave it, or None."""
    if not profile:
        return None
    try:
        from api.bot_metadata import read_profile
        title = (read_profile(profile).get('bot') or {}).get('title')
    except Exception:
        return None
    return title.strip() if isinstance(title, str) and title.strip() else None


def bot_handle(profile, title=None) -> str:
    """The handle a bot is shown and addressed by: ``@<handle>``.

    It is the slug of the bot's title, falling back to the slug of its id, and
    never carries an internal component name.
    """
    if title is None:
        title = bot_title(profile)
    return handle_from_text(title) or handle_from_text(profile) or 'bot'


def default_bot_of(session) -> str | None:
    """The chat's default bot as stored on the session, or None."""
    value = getattr(session, 'default_bot', None)
    return value if isinstance(value, str) and _BOT_ID_RE.fullmatch(value) else None


def last_bot(session) -> str | None:
    """The bot that answered last: the ``bot_profile`` of the latest bot reply."""
    for message in reversed(getattr(session, 'messages', None) or []):
        if isinstance(message, dict) and message.get('role') == 'assistant':
            bot = message.get('bot_profile')
            if isinstance(bot, str) and bot.strip():
                return bot.strip()
    return None


def _group_bots(session, actor) -> list:
    bots = normalize_bots(getattr(session, 'bot_participants', None))
    from api.project_collaboration import project_for, session_access
    project_access = session_access(session, actor)
    if project_access is False:
        raise ValueError('You are no longer a member of this project')
    if project_access is True:
        project = project_for(getattr(session, 'project_id', None))
        bots = [b for b in bots if b in project.get('bot_participants', [])]
        if not bots:
            raise ValueError('No assigned bot is available for this project conversation')
    return bots


def _resolve_mention(token, bots, actor) -> str | None:
    """The bot ``@token`` names: its id, or its handle when that is unique."""
    if token in bots:
        return token
    low = token.lower()
    by_id = [b for b in bots if b.lower() == low]
    if len(by_id) == 1:
        return by_id[0]
    by_handle = [b for b in bots if bot_handle(b) == low]
    if len(by_handle) > 1:
        # Two bots with the same title: only one of them may be usable.
        by_handle = [b for b in by_handle if bot_allowed(actor, b)]
    return by_handle[0] if len(by_handle) == 1 else None


def select_bot_with_reason(session, message, actor) -> tuple:
    """Return ``(bot, reason)`` for a group turn, or ``(None, None)``.

    Order (plan 5.2): ``mention`` (the message starts with ``@bot``), then
    ``only_bot``, then ``sticky`` (the bot that answered last), then
    ``default`` (the chat's default bot). A bot the sender may not use is
    skipped, never silently used. Raises ValueError with a sentence for the
    sender when no bot applies.
    """
    bots = _group_bots(session, actor)
    if not bots:
        return None, None
    match = _MENTION_RE.match(str(message or ''))
    if match:
        selected = _resolve_mention(match.group(1), bots, actor)
        if selected is None:
            raise ValueError(CHOOSE_BOT_ERROR)
        if not bot_allowed(actor, selected):
            raise ValueError('The selected bot is not allowed for your account')
        return selected, 'mention'
    if len(bots) == 1:
        if not bot_allowed(actor, bots[0]):
            raise ValueError('The selected bot is not allowed for your account')
        return bots[0], 'only_bot'
    skipped = False
    last = last_bot(session)
    if last in bots:
        if bot_allowed(actor, last):
            return last, 'sticky'
        skipped = True
    default = default_bot_of(session)
    if default in bots and default != last and bot_allowed(actor, default):
        return default, 'default'
    raise ValueError(LAST_BOT_UNAVAILABLE_ERROR if skipped else CHOOSE_BOT_ERROR)


def _stream_active(stream_id) -> bool:
    try:
        from api.config import ACTIVE_RUNS, ACTIVE_RUNS_LOCK, STREAMS, STREAMS_LOCK
    except Exception:
        return False
    with ACTIVE_RUNS_LOCK:
        if stream_id in ACTIVE_RUNS:
            return True
    with STREAMS_LOCK:
        return stream_id in STREAMS


def _prune_routes_locked(now) -> None:
    for stream_id, entry in list(_ROUTES.items()):
        if len(_ROUTES) <= _ROUTES_MAX and now - entry.get('since', now) < _ROUTES_IDLE_SECONDS:
            break
        if len(_ROUTES) > _ROUTES_MAX or not _stream_active(stream_id):
            _ROUTES.pop(stream_id, None)


def remember_route_reason(stream_id, bot, reason) -> None:
    """Remember why the turn on ``stream_id`` went to ``bot``.

    Called by api/routes.py once the stream id exists. The entry feeds the
    ``turn_bot`` event, the ``peer_turn_started`` fields and the Working state.
    """
    stream_id = str(stream_id or '').strip()
    if not stream_id or not isinstance(bot, str) or not _BOT_ID_RE.fullmatch(bot):
        return None
    try:
        from api.config import stream_owner_session_id
        session_id = stream_owner_session_id(stream_id)
    except Exception:
        session_id = None
    now = time.time()
    entry = {
        'stream_id': stream_id,
        'session_id': session_id,
        'bot': bot,
        'reason': reason if reason in ROUTE_REASONS else None,
        'since': now,
    }
    with _ROUTES_LOCK:
        _ROUTES[stream_id] = entry
        _ROUTES.move_to_end(stream_id)
        _prune_routes_locked(now)
    return None


def route_for_stream(stream_id) -> dict | None:
    """The remembered route of a stream: ``{stream_id, session_id, bot, reason, since}``."""
    stream_id = str(stream_id or '').strip()
    if not stream_id:
        return None
    with _ROUTES_LOCK:
        entry = _ROUTES.get(stream_id)
        return dict(entry) if entry else None


def working_state(session_id) -> dict | None:
    """The bot working in a conversation right now, or None.

    ``{bot, stream_id, reason, since}`` of the newest group turn of the session
    whose stream is still running. This is the per-session Working state the
    roster shows, and what an "Active now" view builds on.
    """
    session_id = str(session_id or '').strip()
    if not session_id:
        return None
    with _ROUTES_LOCK:
        entries = [dict(e) for e in _ROUTES.values() if e.get('session_id') == session_id]
    for entry in reversed(entries):
        if _stream_active(entry['stream_id']):
            return {key: entry.get(key) for key in ('bot', 'stream_id', 'reason', 'since')}
    return None


def latest_route_reason(session_id, bot) -> str | None:
    """Why the newest group turn of a conversation went to ``bot``, or None.

    For stamping the reason on the turn's reply (``route_reason`` next to
    ``bot_profile``), so the chip survives a reload. Only the newest
    remembered turn of the session counts, and only when it ran as ``bot``;
    the stream may already have ended. Never raises.
    """
    session_id = str(session_id or '').strip()
    if not session_id or not isinstance(bot, str) or not bot:
        return None
    with _ROUTES_LOCK:
        newest = next((e for e in reversed(_ROUTES.values()) if e.get('session_id') == session_id), None)
        if newest is None or newest.get('bot') != bot:
            return None
        return newest.get('reason') if newest.get('reason') in ROUTE_REASONS else None


def turn_bot_event(session_id, stream_id, bot) -> dict:
    """The ``turn_bot`` event a group turn's worker emits when it starts.

    ``{session_id, stream_id, bot, handle, name?, reason?}``: which bot works on
    this turn, how it is shown, and why it was chosen. Never raises.
    """
    payload = {'session_id': str(session_id or ''), 'stream_id': str(stream_id or ''), 'bot': str(bot or '')}
    try:
        entry = route_for_stream(stream_id)
        if entry is None and payload['stream_id'] and _BOT_ID_RE.fullmatch(payload['bot']):
            remember_route_reason(payload['stream_id'], payload['bot'], None)
            entry = route_for_stream(stream_id)
        if entry is not None and not entry.get('session_id') and payload['session_id']:
            with _ROUTES_LOCK:
                if payload['stream_id'] in _ROUTES:
                    _ROUTES[payload['stream_id']]['session_id'] = payload['session_id']
        if entry and entry.get('bot') == payload['bot'] and entry.get('reason'):
            payload['reason'] = entry['reason']
        title = bot_title(payload['bot'])
        payload['handle'] = bot_handle(payload['bot'], title)
        if title:
            payload['name'] = title
    except Exception:
        logger.debug("group chat: turn_bot details unavailable for stream %s", stream_id, exc_info=True)
    return payload


def turn_started_extra(session, bot) -> dict:
    """Extra fields for the ``peer_turn_started`` frame of a group turn.

    ``{bot_profile, bot_handle, bot_name?, route_reason?}`` so the other open
    tabs know which bot works on the turn. ``bot`` is the bot the turn runs
    as; when it is not given, the session's active stream is looked up.
    """
    try:
        bot = bot if isinstance(bot, str) and _BOT_ID_RE.fullmatch(bot) else None
        entry = route_for_stream(getattr(session, 'active_stream_id', None))
        if bot is None and entry:
            bot = entry.get('bot')
        if not bot:
            return {}
        title = bot_title(bot)
        extra = {'bot_profile': bot, 'bot_handle': bot_handle(bot, title)}
        if title:
            extra['bot_name'] = title
        if entry and entry.get('bot') == bot and entry.get('reason'):
            extra['route_reason'] = entry['reason']
        return extra
    except Exception:
        logger.debug("group chat: peer turn fields unavailable", exc_info=True)
        return {}


def apply_participants_extra(session, body, actor) -> None:
    """Apply ``default_bot`` from ``POST /api/session/participants``.

    The default bot answers an unaddressed message when no bot answered
    before (plan 5.2). It must be one of the chat's bots and usable by the
    person setting it; ``null`` or ``""`` clears it. Without ``default_bot`` in
    the body the current default is kept while its bot stays in the chat.

    Everything is validated before the session is touched, so a ValueError
    (answered with 400) leaves the session exactly as it was.
    """
    if not isinstance(body, dict):
        return None
    raw_bots = body.get('bot_participants', getattr(session, 'bot_participants', None))
    bots = normalize_bots(raw_bots) if raw_bots is not None else []
    current = default_bot_of(session)
    if 'default_bot' in body:
        requested = body.get('default_bot')
        if requested is None or (isinstance(requested, str) and not requested.strip()):
            new = None
        else:
            requested = requested.strip() if isinstance(requested, str) else None
            if requested not in bots:
                raise ValueError('Choose the default bot from the bots in this chat.')
            if not bot_allowed(actor, requested):
                raise ValueError('That bot is not available to you, so it cannot be the default.')
            new = requested
    else:
        new = current if current in bots else None
    if new != current or (new is None and getattr(session, 'default_bot', None) is not None):
        session.default_bot = new
    return None


def known_emails() -> set:
    """Every address the governance policy knows, for validating a pick.

    Returns an empty set when the policy cannot be read. Adding a participant
    grants transcript visibility, so an unavailable directory must fail closed.
    """
    try:
        from api.governance.loader import get_policy

        policy = get_policy()
    except Exception:
        logger.debug("group chat: governance policy unavailable for validation", exc_info=True)
        return set()
    found: set[str] = set()
    for email in (getattr(policy, "users", None) or {}):
        cleaned = _clean(email)
        if cleaned:
            found.add(cleaned)
    for email in (getattr(policy, "bootstrap_admins", None) or ()):
        cleaned = _clean(email)
        if cleaned:
            found.add(cleaned)
    return found


def validate(values, *, owner_email=None) -> tuple:
    """Return ``(participants, error)`` for a requested participant list.

    ``error`` is a sentence for the caller, or None when the list is usable.
    """
    if values is None:
        return [], None
    if not isinstance(values, (list, tuple)):
        return [], "participants must be a list of e-mail addresses"
    if len(values) > MAX_PARTICIPANTS:
        return [], f"a conversation can hold at most {MAX_PARTICIPANTS} other people"
    for raw in values:
        if not isinstance(raw, str) or not _EMAIL_RE.match(_clean(raw)):
            return [], f"not an e-mail address: {str(raw)[:80]}"
    participants = normalize(values, owner_email=owner_email)
    if not participants:
        return [], None
    known = known_emails()
    if not known:
        return [], "People directory is unavailable. Please try again."
    if known:
        unknown = [p for p in participants if p not in known]
        if unknown:
            return [], (
                "not a known account on this workstation: " + ", ".join(unknown[:5])
            )
    return participants, None


def require_turn_membership(session, actor) -> None:
    """Recheck the original human at worker entry after queue/dispatch races."""
    from api.project_collaboration import session_access
    project_access = session_access(session, actor)
    if project_access is not None:
        if not project_access:
            raise PermissionError('You are no longer a member of this project')
        return
    if not is_member(getattr(session, 'owner_email', None), getattr(session, 'participants', None), actor):
        raise PermissionError('You are no longer a member of this conversation')
