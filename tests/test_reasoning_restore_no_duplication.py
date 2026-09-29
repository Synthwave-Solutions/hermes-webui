import copy

from api.streaming import (
    _merge_display_messages_after_agent_result,
    _restore_display_reasoning_metadata,
)


def _fragment(i):
    return {
        "role": "assistant",
        "content": "",
        "reasoning": f"thinking {i}",
        "reasoning_content": f"thinking {i}",
        "finish_reason": "length",
        "_length_continuation_fragment": True,
        "timestamp": 1000 + i,
        "_row_id": 500 + i,
    }


def _display_with_fragments(turns=4):
    display = []
    for i in range(turns):
        display += [
            {"role": "user", "content": f"q{i}", "timestamp": i + 1},
            _fragment(i),
            {"role": "assistant", "content": f"a{i}", "timestamp": i + 1.5},
        ]
    return display


def _fragment_count(messages):
    return sum(1 for m in messages if m.get("_length_continuation_fragment"))


def test_thinking_rows_do_not_multiply_after_context_compaction():
    display = _display_with_fragments()
    context = [
        {"role": "user", "content": "q3", "timestamp": 4},
        {"role": "assistant", "content": "a3", "timestamp": 4.5},
    ]
    counts = []
    for turn in range(6):
        prompt = f"new{turn}"
        result = copy.deepcopy(context) + [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": f"r{turn}"},
        ]
        restored = _restore_display_reasoning_metadata(display, result)
        display = _merge_display_messages_after_agent_result(display, context, restored, prompt)
        context = result
        counts.append(_fragment_count(display))

    assert counts == [4] * 6


def test_restore_skips_thinking_row_already_returned_by_agent():
    previous = [
        {"role": "user", "content": "q", "timestamp": 1},
        _fragment(0),
        {"role": "assistant", "content": "a", "timestamp": 2},
    ]
    updated = [
        {"role": "user", "content": "q"},
        copy.deepcopy(previous[1]),
        {"role": "assistant", "content": "a"},
    ]

    restored = _restore_display_reasoning_metadata(previous, updated)

    assert _fragment_count(restored) == 1


def test_restore_still_reinserts_thinking_row_when_history_lines_up():
    previous = [
        {"role": "user", "content": "q", "timestamp": 1},
        _fragment(0),
        {"role": "assistant", "content": "a", "timestamp": 2},
        {"role": "user", "content": "q2", "timestamp": 3},
    ]
    updated = [
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "a"},
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "a2"},
    ]

    restored = _restore_display_reasoning_metadata(previous, updated)

    assert [m["role"] for m in restored] == ["user", "assistant", "assistant", "user", "assistant"]
    assert restored[1]["_length_continuation_fragment"] is True
