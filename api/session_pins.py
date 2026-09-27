"""Pins belong to the person who pinned (Michael Ramirez, 27 Sep 2026).

A conversation carried one ``pinned`` flag. In a group chat that meant one
person's pin showed up in everybody's sidebar (Yaser pinned "Gate Terminal
slides" and Michael, a participant, saw it pinned too), and the pin quota
counted everyone's pins together.

``pinned`` keeps its old meaning, the owner's own pin, so every row written
before this change reads exactly as it did. Anyone else who pins the
conversation (a participant, or an admin looking at someone else's chat) is
listed in ``pinned_by``. A row without an owner (legacy, cron and CLI rows)
keeps one shared flag, as before, and so does a request without an identity
(auth off, local single-user mode).

``pinned_by`` never leaves the server: list rows are projected per viewer with
:func:`project_row`, and the sidebar allowlist does not carry the field.
"""

from __future__ import annotations

_MAX_PINNED_BY = 50


def _clean(value) -> str:
    return str(value or "").strip().lower()


def _field(row, name, default=None):
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def normalize(values) -> list:
    """Lower-cased, de-duplicated e-mail addresses, order kept, capped."""
    if not isinstance(values, (list, tuple, set)):
        return []
    out = []
    for value in values:
        email = _clean(value)
        if not email or "@" not in email or email in out:
            continue
        out.append(email)
        if len(out) >= _MAX_PINNED_BY:
            break
    return out


def _uses_shared_flag(row, who: str) -> bool:
    owner = _clean(_field(row, "owner_email"))
    return not who or not owner or owner == who


def is_pinned_for(row, email) -> bool:
    """Whether *row* (a Session or an index row) is pinned for *email*."""
    who = _clean(email)
    if _uses_shared_flag(row, who):
        return bool(_field(row, "pinned", False))
    return who in normalize(_field(row, "pinned_by"))


def set_pinned(session, email, pinned: bool) -> None:
    """Pin or unpin *session* for *email* only."""
    who = _clean(email)
    if _uses_shared_flag(session, who):
        session.pinned = bool(pinned)
        return
    people = normalize(getattr(session, "pinned_by", None))
    if pinned and who not in people:
        people.append(who)
    elif not pinned and who in people:
        people.remove(who)
    session.pinned_by = people


def project_row(row: dict, email) -> dict:
    """A copy of a list row as *email* sees it: ``pinned`` is theirs, and the
    list of other people's pins is dropped. Never mutates *row*, which may be
    a shared cache entry."""
    if not isinstance(row, dict):
        return row
    out = dict(row)
    out["pinned"] = is_pinned_for(row, email)
    out.pop("pinned_by", None)
    return out
