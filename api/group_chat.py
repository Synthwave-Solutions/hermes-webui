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

import logging
import re

logger = logging.getLogger(__name__)

# A conversation people actually work in, not a mailing list. The cap keeps the
# blast radius of one mistaken pick small and keeps the participant chips
# readable in the composer.
MAX_PARTICIPANTS = 25

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean(value) -> str:
    return str(value or "").strip().lower()


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


def known_emails() -> set:
    """Every address the governance policy knows, for validating a pick.

    Returns an empty set when the policy cannot be read, and callers treat that
    as "cannot validate" rather than "nobody exists": failing open on a typo is
    better than blocking every group chat because a policy file is briefly
    unreadable, and a typo grants nothing on its own.
    """
    try:
        from api.governance.loader import load_governance_policy

        policy = load_governance_policy()
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
    known = known_emails()
    if known:
        unknown = [p for p in participants if p not in known]
        if unknown:
            return [], (
                "not a known account on this workstation: " + ", ".join(unknown[:5])
            )
    return participants, None
