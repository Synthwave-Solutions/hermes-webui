"""Pins belong to the person who pinned (27 Sep 2026).

Reported by Michael: Yaser pinned the group chat "Gate Terminal slides" and it
showed up pinned in Michael's sidebar too, because a conversation carried one
shared ``pinned`` flag. The pin quota also counted everyone's pins together.
"""

import contextlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import routes, session_pins  # noqa: E402
from api.models import Session  # noqa: E402


YASER = "yaser@synthwave.solutions"
MICHAEL = "michael@synthwave.solutions"
STEPHEN = "stephen@synthwave.solutions"


def _group_chat(sid="gate-terminal", owner=YASER, participants=(MICHAEL,), **extra):
    s = Session(session_id=sid, title="Gate Terminal slides", owner_email=owner,
                participants=list(participants), **extra)
    s.save = lambda *a, **k: None
    return s


@pytest.fixture
def pin_env(monkeypatch):
    """Run _apply_session_pin against an in-memory set of rows."""
    rows = []
    monkeypatch.setattr(routes, "all_sessions", lambda *a, **k: [r.compact() for r in rows])
    monkeypatch.setattr(routes, "SESSIONS", {})
    monkeypatch.setattr(routes, "load_settings", lambda: {"pinned_sessions_limit": 2})
    monkeypatch.setattr(routes, "_get_session_agent_lock", lambda sid: contextlib.nullcontext())
    return rows


def test_owner_pin_stays_out_of_a_participants_sidebar(pin_env):
    chat = _group_chat()
    pin_env.append(chat)

    assert routes._apply_session_pin(chat, YASER, True, chat.session_id) is None

    assert session_pins.is_pinned_for(chat, YASER)
    assert not session_pins.is_pinned_for(chat, MICHAEL)
    assert not session_pins.project_row(chat.compact(), MICHAEL)["pinned"]


def test_participant_pin_is_their_own_and_leaves_the_owner_alone(pin_env):
    chat = _group_chat()
    pin_env.append(chat)

    assert routes._apply_session_pin(chat, MICHAEL, True, chat.session_id) is None
    assert session_pins.is_pinned_for(chat, MICHAEL)
    assert not session_pins.is_pinned_for(chat, YASER)
    assert not session_pins.is_pinned_for(chat, STEPHEN)
    assert chat.pinned is False
    assert chat.pinned_by == [MICHAEL]

    # The owner pins too, then the participant unpins: the owner keeps theirs.
    routes._apply_session_pin(chat, YASER, True, chat.session_id)
    routes._apply_session_pin(chat, MICHAEL, False, chat.session_id)
    assert session_pins.is_pinned_for(chat, YASER)
    assert not session_pins.is_pinned_for(chat, MICHAEL)
    assert chat.pinned_by == []


def test_quota_counts_only_your_own_pins(pin_env):
    theirs = [_group_chat(sid=f"yaser-{i}") for i in range(2)]
    pin_env.extend(theirs)
    for chat in theirs:
        assert routes._apply_session_pin(chat, YASER, True, chat.session_id) is None

    # Yaser is at the limit of 2; Michael has pinned nothing yet.
    extra = _group_chat(sid="yaser-extra")
    pin_env.append(extra)
    assert "Up to 2 sessions" in routes._apply_session_pin(extra, YASER, True, extra.session_id)

    mine = [_group_chat(sid=f"michael-{i}", owner=MICHAEL, participants=()) for i in range(2)]
    pin_env.extend(mine)
    for chat in mine:
        assert routes._apply_session_pin(chat, MICHAEL, True, chat.session_id) is None
    # Now Michael is at his own limit, whatever Yaser pinned.
    assert "Up to 2 sessions" in routes._apply_session_pin(theirs[0], MICHAEL, True, theirs[0].session_id)
    assert not session_pins.is_pinned_for(theirs[0], MICHAEL)


def test_rows_written_before_this_change_keep_the_pin_with_the_owner():
    legacy_row = {"session_id": "old", "owner_email": YASER, "participants": [MICHAEL], "pinned": True}
    assert session_pins.is_pinned_for(legacy_row, YASER)
    assert not session_pins.is_pinned_for(legacy_row, MICHAEL)


def test_rows_without_owner_or_requests_without_identity_keep_one_shared_flag():
    ownerless = {"session_id": "cron", "pinned": True}
    assert session_pins.is_pinned_for(ownerless, MICHAEL)
    assert session_pins.is_pinned_for(ownerless, None)

    owned = {"session_id": "s", "owner_email": YASER, "pinned": True, "pinned_by": [MICHAEL]}
    assert session_pins.is_pinned_for(owned, None) is True

    local = Session(session_id="local")
    session_pins.set_pinned(local, None, True)
    assert local.pinned is True and local.pinned_by == []


def test_projection_copies_the_row_and_keeps_other_peoples_pins_private():
    row = {"session_id": "s", "owner_email": YASER, "pinned": True, "pinned_by": [MICHAEL, STEPHEN]}
    seen = session_pins.project_row(row, STEPHEN)
    assert seen["pinned"] is True
    assert "pinned_by" not in seen
    # The source row (possibly a shared cache entry) is untouched.
    assert row["pinned_by"] == [MICHAEL, STEPHEN] and row["pinned"] is True
    assert session_pins.project_row(row, "someone@else.test")["pinned"] is False
    # The sidebar allowlist never carries the field either.
    assert "pinned_by" not in routes._SIDEBAR_SESSION_RESPONSE_FIELDS


def test_session_model_normalizes_and_round_trips_pinned_by():
    s = Session(session_id="rt", owner_email=YASER,
                pinned_by=["Michael@Synthwave.Solutions", "michael@synthwave.solutions", "", "not-an-email"])
    assert s.pinned_by == [MICHAEL]
    compact = s.compact()
    assert compact["pinned_by"] == [MICHAEL]
    again = Session(**{k: v for k, v in compact.items() if k in {"session_id", "owner_email", "pinned", "pinned_by"}})
    assert again.pinned_by == [MICHAEL]
