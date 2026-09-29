from api.interaction_context import actor_identity_prompt
from api.streaming import _webui_ephemeral_system_prompt

OWNER = "yaser@synthwave.solutions"
GUEST = "hrishikesh@synthwave.solutions"


def test_guest_in_owned_conversation_gets_shared_clause():
    prompt = actor_identity_prompt(GUEST, OWNER)
    assert f"Active user: {GUEST}" in prompt
    assert "Shared conversation" in prompt
    assert f"Address {GUEST}, not {OWNER}" in prompt


def test_owner_own_turn_has_no_shared_clause():
    assert "Shared conversation" not in actor_identity_prompt(OWNER, OWNER)
    assert "Shared conversation" not in actor_identity_prompt(OWNER.upper(), OWNER)


def test_missing_or_invalid_owner_adds_nothing():
    base = actor_identity_prompt(GUEST)
    assert actor_identity_prompt(GUEST, None) == base
    assert actor_identity_prompt(GUEST, "not-an-email") == base


def test_invalid_actor_still_returns_empty():
    assert actor_identity_prompt("", OWNER) == ""


def test_ephemeral_prompt_passes_owner_through():
    prompt = _webui_ephemeral_system_prompt(
        None, {"source": "webui"}, {}, actor_email=GUEST, conversation_owner_email=OWNER,
    )
    assert "Shared conversation" in prompt
    solo = _webui_ephemeral_system_prompt(None, {"source": "webui"}, {}, actor_email=OWNER)
    assert "Shared conversation" not in solo
