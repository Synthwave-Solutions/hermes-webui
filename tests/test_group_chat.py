"""Group conversations: who is in a chat, who can see it, and whose rights apply.

The security question these tests exist for: being named in somebody else's
conversation must let you read and write there and grant you nothing else.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import group_chat  # noqa: E402


OWNER = "michael@synthwave.solutions"
STEVE = "stephen@synthwave.solutions"
DEV = "hrishikesh@synthwave.solutions"
STRANGER = "someone@example.com"


@pytest.fixture
def known(monkeypatch):
    monkeypatch.setattr(group_chat, "known_emails", lambda: {OWNER, STEVE, DEV})


class TestNormalize:
    def test_lowercases_and_strips(self):
        assert group_chat.normalize([" Stephen@Synthwave.Solutions "]) == [STEVE]

    def test_drops_duplicates_keeping_order(self):
        assert group_chat.normalize([STEVE, DEV, STEVE]) == [STEVE, DEV]

    def test_drops_the_owner_because_they_are_in_it_by_owning_it(self):
        assert group_chat.normalize([OWNER, STEVE], owner_email=OWNER) == [STEVE]

    def test_drops_values_that_are_not_addresses(self):
        assert group_chat.normalize(["", None, "steve", 7, STEVE]) == [STEVE]

    def test_caps_the_list(self):
        many = [f"p{i}@synthwave.solutions" for i in range(60)]
        assert len(group_chat.normalize(many)) == group_chat.MAX_PARTICIPANTS

    def test_a_non_list_is_no_participants(self):
        assert group_chat.normalize("stephen@synthwave.solutions") == []
        assert group_chat.normalize(None) == []


class TestMembership:
    def test_the_owner_is_a_member(self):
        assert group_chat.is_member(OWNER, [], OWNER)

    def test_a_named_person_is_a_member(self):
        assert group_chat.is_member(OWNER, [STEVE], STEVE)

    def test_everybody_else_is_not(self):
        assert not group_chat.is_member(OWNER, [STEVE], DEV)

    def test_membership_is_case_insensitive(self):
        assert group_chat.is_member(OWNER, ["Stephen@Synthwave.Solutions"], STEVE)

    def test_no_identity_is_never_a_member(self):
        assert not group_chat.is_member(OWNER, [STEVE], "")


class TestVisibility:
    def test_an_admin_sees_everything(self):
        assert group_chat.visible_to_scope(OWNER, [], "all")

    def test_the_owner_sees_their_own_chat(self):
        assert group_chat.visible_to_scope(OWNER, [], OWNER)

    def test_a_participant_sees_the_group_chat(self):
        assert group_chat.visible_to_scope(OWNER, [STEVE], STEVE)

    def test_a_non_participant_does_not(self):
        assert not group_chat.visible_to_scope(OWNER, [STEVE], DEV)

    def test_a_private_chat_stays_private(self):
        assert not group_chat.visible_to_scope(OWNER, [], STEVE)

    def test_an_unowned_row_stays_admin_only(self):
        # Nobody could have named a participant on a row with no owner, so
        # widening must not accidentally expose legacy and cron rows.
        assert not group_chat.visible_to_scope(None, [STEVE], STEVE)
        assert not group_chat.visible_to_scope("", [], STEVE)

    def test_an_identity_less_scope_sees_nothing_of_a_group(self):
        assert not group_chat.visible_to_scope(OWNER, [STEVE], "")


class TestValidate:
    def test_a_known_colleague_is_accepted(self, known):
        participants, error = group_chat.validate([STEVE], owner_email=OWNER)
        assert error is None and participants == [STEVE]

    def test_an_unknown_address_is_refused(self, known):
        participants, error = group_chat.validate([STRANGER], owner_email=OWNER)
        assert participants == []
        assert "not a known account" in error

    def test_a_malformed_address_is_refused(self, known):
        _, error = group_chat.validate(["not-an-address"], owner_email=OWNER)
        assert "not an e-mail address" in error

    def test_too_many_people_is_refused(self, known):
        many = [f"p{i}@synthwave.solutions" for i in range(group_chat.MAX_PARTICIPANTS + 1)]
        _, error = group_chat.validate(many, owner_email=OWNER)
        assert "at most" in error

    def test_a_non_list_is_refused(self, known):
        _, error = group_chat.validate("stephen@synthwave.solutions", owner_email=OWNER)
        assert "must be a list" in error

    def test_none_clears_without_error(self, known):
        participants, error = group_chat.validate(None, owner_email=OWNER)
        assert participants == [] and error is None

    def test_an_empty_list_clears_without_error(self, known):
        participants, error = group_chat.validate([], owner_email=OWNER)
        assert participants == [] and error is None

    def test_an_unreadable_policy_does_not_block_the_pick(self, monkeypatch):
        # Failing open on validation is safe: naming somebody grants nothing on
        # its own, and each turn still runs under that person's own access.
        monkeypatch.setattr(group_chat, "known_emails", lambda: set())
        participants, error = group_chat.validate([STRANGER], owner_email=OWNER)
        assert error is None and participants == [STRANGER]


class TestParticipantsOf:
    def test_reads_an_index_row(self):
        row = {"owner_email": OWNER, "participants": [STEVE, OWNER]}
        assert group_chat.participants_of(row) == [STEVE]

    def test_reads_a_session_object(self):
        class Fake:
            owner_email = OWNER
            participants = [STEVE]

        assert group_chat.participants_of(Fake()) == [STEVE]

    def test_a_row_without_the_field_has_no_participants(self):
        assert group_chat.participants_of({"owner_email": OWNER}) == []

    def test_none_is_no_participants(self):
        assert group_chat.participants_of(None) == []
