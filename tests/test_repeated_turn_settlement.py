"""An identical new exchange is a new turn, not a replay of its predecessor."""
from copy import deepcopy

import pytest

from api import streaming


PROMPT = "Reply with exactly: SynthPulse chatcontrole geslaagd."
ANSWER = "SynthPulse chatcontrole geslaagd."


def exchange():
    return [
        {"role": "user", "content": PROMPT},
        {"role": "assistant", "content": ANSWER},
    ]


@pytest.mark.parametrize("prior_turns", [1, 2])
def test_identical_new_exchange_survives_display_and_context(prior_turns):
    previous = exchange() * prior_turns
    result = deepcopy(previous) + exchange()
    original = deepcopy(result)
    assert streaming._merge_display_messages_after_agent_result(
        previous, previous, result, PROMPT
    ) == original
    assert streaming._dedupe_replayed_context_messages(
        previous, result, PROMPT
    ) == original
    assert streaming._deduplicate_context_messages(original) == original
    assert not streaming._merged_transcript_lacks_final_assistant_answer(
        previous, previous, result, PROMPT
    )
    assert result == original


def test_replayed_prefix_before_identical_current_turn_is_still_removed():
    previous = exchange()
    # One replayed previous exchange precedes the newly submitted exchange.
    result = deepcopy(previous) + exchange() + exchange()
    assert streaming._merge_display_messages_after_agent_result(
        previous, previous, result, PROMPT
    ) == previous + exchange()
    assert streaming._dedupe_replayed_context_messages(
        previous, result, PROMPT
    ) == previous + exchange()


def test_old_history_without_a_new_exchange_cannot_satisfy_current_turn():
    previous = exchange()
    assert streaming._merged_transcript_lacks_final_assistant_answer(
        previous, previous, deepcopy(previous), PROMPT
    )
    assert not streaming._assistant_reply_added_after_current_turn(
        previous, previous, PROMPT
    )


def test_repeated_tool_exchange_is_kept_in_current_model_context():
    previous = [exchange()[0],
                {"role": "assistant", "content": "Checking"},
                {"role": "tool", "content": "Same result"}, exchange()[1]]
    result = deepcopy(previous) + deepcopy(previous)
    assert streaming._dedupe_replayed_context_messages(
        previous, result, PROMPT
    ) == result


def test_adjacent_user_checkpoint_and_tool_replay_still_deduplicate():
    user = exchange()[0]
    call = {"role": "assistant", "content": "", "tool_calls": [
        {"id": "call-a", "function": {"name": "fixture"}, "type": "function"}
    ]}
    output = {"role": "tool", "content": "same", "tool_call_id": "call-a"}
    rows = [user, deepcopy(user), call, output, deepcopy(call), deepcopy(output), exchange()[1]]
    assert streaming._deduplicate_context_messages(rows) == [user, call, output, exchange()[1]]


def test_distinct_tool_calls_with_same_text_are_kept():
    rows = [exchange()[0]]
    for call_id in ("call-a", "call-b"):
        rows.extend([
            {"role": "assistant", "content": "", "tool_calls": [
                {"id": call_id, "function": {"name": "fixture"}, "type": "function"}
            ]},
            {"role": "tool", "content": "same", "tool_call_id": call_id},
        ])
    rows.append(exchange()[1])
    assert streaming._deduplicate_context_messages(rows) == rows


def test_workspace_wrapped_current_turn_survives_identical_prior_answer():
    previous = exchange()
    current = exchange()
    current[0]["content"] = "[Workspace::v1: /synthetic]\n" + PROMPT
    merged = streaming._merge_display_messages_after_agent_result(
        previous, previous, deepcopy(previous) + current, PROMPT
    )
    assert merged == previous + exchange()


@pytest.mark.parametrize("prompt", [None, ""])
def test_missing_prompt_does_not_protect_historical_replay(prompt):
    previous = exchange()
    assert streaming._dedupe_replayed_context_messages(
        previous, deepcopy(previous) + exchange(), prompt
    ) == previous


def test_references_stay_global_across_new_turn_boundaries():
    marker = {"role": "assistant", "content": "[CONTEXT COMPACTION — REFERENCE ONLY] summary",
              "_compressed_summary": True}
    rows = [marker] + exchange() + [deepcopy(marker)] + exchange()
    assert streaming._deduplicate_context_messages(rows) == [marker] + exchange() + exchange()
