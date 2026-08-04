"""Contract tests for the transcript redaction fast paths.

Two perf mechanisms sit in front of the combined redactor:

1. `_redact_message_list`: one joined marker scan per message; clean messages
   are returned by reference (no per-string scans, no dict/list copies).
2. `_redact_big_cached`: >16KB strings (which bypass the value-keyed LRU) are
   memoized by BLAKE2b content digest with a bounded byte budget.

Both must never weaken redaction: outputs stay identical to the plain
per-string `_redact_value` walk.
"""

from api import helpers


SECRET = "sk-ant-api03-" + "a" * 40


def _clean_message():
    return {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Hello, plain conversation text."},
            {"type": "text", "text": "No credentials anywhere here."},
        ],
    }


def _dirty_message():
    return {
        "role": "assistant",
        "content": [{"type": "text", "text": f"the key is {SECRET} ok"}],
    }


def test_clean_messages_returned_by_reference():
    msg = _clean_message()
    out = helpers._redact_message_list([msg], _enabled=True)
    assert out[0] is msg


def test_dirty_messages_still_redacted():
    out = helpers._redact_message_list([_clean_message(), _dirty_message()], _enabled=True)
    text = out[1]["content"][0]["text"]
    assert SECRET not in text
    assert "ok" in text


def test_fastpath_matches_per_string_walk():
    messages = [
        _clean_message(),
        _dirty_message(),
        {"role": "user", "content": "postgres://user:hunter2@db.internal/x"},
        {"role": "tool", "content": [{"type": "tool_result", "text": "plain"}]},
    ]
    fast = helpers._redact_message_list(messages, _enabled=True)
    slow = helpers._redact_value(messages, _enabled=True)
    assert fast == slow


def test_joined_scan_has_no_false_negatives_at_part_boundaries():
    # The phone marker uses alnum lookarounds; the joiner must keep a
    # non-alphanumeric separator so a phone number at the start of one part
    # still matches when the previous part ends in an alphanumeric.
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": "ends with alnum9"},
            {"type": "text", "text": "+31612345678 leading phone"},
        ],
    }]
    fast = helpers._redact_message_list(messages, _enabled=True)
    slow = helpers._redact_value(messages, _enabled=True)
    assert fast == slow


def test_redact_session_data_uses_message_fastpath():
    session = {
        "title": "t",
        "messages": [_clean_message(), _dirty_message()],
    }
    out = helpers.redact_session_data(session)
    assert out["messages"][0] is session["messages"][0]
    assert SECRET not in out["messages"][1]["content"][0]["text"]


def test_big_string_digest_cache_hits_and_matches_uncached():
    big = ("x" * (helpers._REDACT_CACHE_MAX_TEXT_LEN + 100)) + f" {SECRET}"
    first = helpers._redact_fn_cached(big)
    assert SECRET not in first
    assert first == helpers._redact_fn_uncached(big)
    # Second call must come from the digest cache (same object identity).
    assert helpers._redact_fn_cached(big) is first


def test_big_string_cache_respects_byte_budget():
    # Entries above the per-entry cap are never cached.
    huge = "y" * (helpers._REDACT_BIG_CACHE_MAX_ENTRY_CHARS + 1)
    before = len(helpers._REDACT_BIG_CACHE)
    helpers._redact_fn_cached(huge)
    assert len(helpers._REDACT_BIG_CACHE) == before
    # Total budget bookkeeping never goes negative and eviction keeps the
    # accounted bytes at or below the configured budget.
    assert 0 <= helpers._REDACT_BIG_CACHE_TOTAL_CHARS <= (
        helpers._REDACT_BIG_CACHE_MAX_TOTAL_CHARS
    )

