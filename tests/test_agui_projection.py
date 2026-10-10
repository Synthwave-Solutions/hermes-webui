"""AG-UI 1.0 projection of WebUI run journals (program plan 5.1, package W5).

The shared fixtures in tests/fixtures/agui are journals written by the real
run journal writer (api/run_journal.py) with the payload shapes of
api/streaming.py, each with the AG-UI events it must project to. The vendored
AG-UI 1.0 JSON Schema checks every event; an independent verifier below checks
the ordering rules the schema cannot express (AG-UI 1.0 lifecycle, streaming,
step and subagent rules). The same fixtures serve the browser port in W10.

Set ``AGUI_UPDATE_GOLDEN=1`` to rewrite the expected files after a deliberate
mapping change, then review the diff.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from api import agui
from api.agui import ProjectionContext, Projector, encode_sse, project_journal

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "agui"
SCHEMA_PATH = FIXTURES / "ag-ui-1.0.schema.json"
# The vendored copy: upstream ag-ui-protocol@1.0.0 (sha256 4b5c9322...e71a)
# with U+2014 in description annotations replaced by "-" (see the README).
SCHEMA_SHA256 = "d6972043f6f2d7adaf59242ea89561825b2690bd06ede48064aac80a803cf168"
UPSTREAM_SHA256 = "4b5c93226838a0e72d88e6c5df20633c686c49fcb75d9be2815c6cbf9e48e71a"
INDEX = json.loads((FIXTURES / "index.json").read_text(encoding="utf-8"))
CASES = [case["name"] for case in INDEX["cases"]]
UPDATE_GOLDEN = os.environ.get("AGUI_UPDATE_GOLDEN") == "1"


def _no_redaction(messages):
    return messages


def _ctx(**kwargs):
    kwargs.setdefault("thread_id", "sess_1")
    kwargs.setdefault("run_id", "run_1")
    kwargs.setdefault("redact_messages", _no_redaction)
    return ProjectionContext(**kwargs)


def _rows(name):
    path = FIXTURES / f"{name}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _case(name):
    return next(case for case in INDEX["cases"] if case["name"] == name)


def _project(name):
    return project_journal(_rows(name))


@pytest.fixture(scope="module")
def validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _feed_all(projector, frames):
    out = []
    for index, (name, data) in enumerate(frames, start=1):
        out.extend(projector.feed(name, data, seq=index))
    return out


def _types(events):
    return [event["type"] for event in events]


def _walk(value, path="$"):
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def _apply_patch(state, ops):
    """Minimal RFC 6902 add, replace and remove on dict paths."""
    state = copy.deepcopy(state)
    for op in ops:
        parts = [p.replace("~1", "/").replace("~0", "~") for p in op["path"].split("/")[1:]]
        target = state
        for part in parts[:-1]:
            target = target[part]
        if op["op"] == "add":
            target[parts[-1]] = op["value"]
        elif op["op"] == "replace":
            assert parts[-1] in target, op
            target[parts[-1]] = op["value"]
        elif op["op"] == "remove":
            del target[parts[-1]]
        else:  # pragma: no cover - the projector emits only these three
            raise AssertionError(op)
    return state


def verify_ag_ui_sequence(events, *, allow_truncated=False):
    """Check AG-UI 1.0 ordering rules; return the final state for inspection.

    Rules (spec 1.0: lifecycle, text messages, reasoning, tool calls, steps,
    subagents): a stream opens with RUN_STARTED or RUN_ERROR; nothing but a
    late RUN_ERROR or a new RUN_STARTED follows RUN_FINISHED; nothing but
    RUN_STARTED follows RUN_ERROR; streamed entities open before they continue
    and close before RUN_FINISHED; a tool result answers a started call; steps
    and subagents open once and close before RUN_FINISHED; a subagent names
    only an announced parent and is never reused; deltas follow a snapshot and
    apply to it.
    """
    phase = "none"
    late_error_used = False
    text, spans, reasoning, tools, steps, active = set(), set(), set(), set(), set(), set()
    started_tools, finished_subagents, announced, result_ids = set(), set(), set(), set()
    state = None
    for index, event in enumerate(events):
        kind = event["type"]
        where = f"event {index} {kind}"
        if phase == "none":
            assert kind in ("RUN_STARTED", "RUN_ERROR"), where
        elif phase == "finished":
            assert kind in ("RUN_ERROR", "RUN_STARTED"), where
            assert not (kind == "RUN_ERROR" and late_error_used), where
        elif phase == "errored":
            assert kind == "RUN_STARTED", where
        if kind == "RUN_STARTED":
            assert phase != "active", where
            phase = "active"
            text, spans, reasoning, tools, steps, active = set(), set(), set(), set(), set(), set()
            started_tools, finished_subagents, announced, result_ids = set(), set(), set(), set()
            continue
        if kind == "RUN_FINISHED":
            assert phase == "active", where
            assert not (text or spans or reasoning or tools or steps or active), (where, text, spans,
                                                                                   reasoning, tools, steps, active)
            phase = "finished"
            continue
        if kind == "RUN_ERROR":
            late_error_used = phase == "finished"
            phase = "errored"
            continue
        assert phase == "active", where
        if kind == "TEXT_MESSAGE_START":
            assert event["messageId"] not in text, where
            text.add(event["messageId"])
        elif kind in ("TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END"):
            assert event["messageId"] in text, where
            if kind == "TEXT_MESSAGE_END":
                text.discard(event["messageId"])
        elif kind == "REASONING_START":
            assert event["messageId"] not in spans, where
            spans.add(event["messageId"])
        elif kind == "REASONING_END":
            assert event["messageId"] in spans, where
            spans.discard(event["messageId"])
        elif kind == "REASONING_MESSAGE_START":
            assert event["messageId"] not in reasoning, where
            reasoning.add(event["messageId"])
        elif kind in ("REASONING_MESSAGE_CONTENT", "REASONING_MESSAGE_END"):
            assert event["messageId"] in reasoning, where
            if kind == "REASONING_MESSAGE_END":
                reasoning.discard(event["messageId"])
        elif kind == "TOOL_CALL_START":
            assert event["toolCallId"] not in tools, where
            tools.add(event["toolCallId"])
            started_tools.add(event["toolCallId"])
        elif kind in ("TOOL_CALL_ARGS", "TOOL_CALL_END"):
            assert event["toolCallId"] in tools, where
            if kind == "TOOL_CALL_END":
                tools.discard(event["toolCallId"])
        elif kind == "TOOL_CALL_RESULT":
            assert event["toolCallId"] in started_tools, where
            assert event["messageId"] not in result_ids, where
            result_ids.add(event["messageId"])
        elif kind == "STEP_STARTED":
            assert event["stepName"] not in steps, where
            steps.add(event["stepName"])
        elif kind == "STEP_FINISHED":
            assert event["stepName"] in steps, where
            steps.discard(event["stepName"])
        elif kind == "SUBAGENT_STARTED":
            sid = event["subagentRunId"]
            assert sid not in active and sid not in finished_subagents, where
            parent = event.get("parentSubagentRunId")
            assert parent is None or parent in announced, where
            active.add(sid)
            announced.add(sid)
        elif kind in ("SUBAGENT_FINISHED", "SUBAGENT_ERROR"):
            sid = event["subagentRunId"]
            assert sid in active, where
            active.discard(sid)
            finished_subagents.add(sid)
        elif kind == "STATE_SNAPSHOT":
            state = copy.deepcopy(event["snapshot"])
        elif kind == "STATE_DELTA":
            assert state is not None, where
            state = _apply_patch(state, event["delta"])
    if not allow_truncated:
        assert phase in ("finished", "errored"), "the run never ended"
    return state


def _run(*middle, end=None):
    start = {"type": "RUN_STARTED", "threadId": "t", "runId": "r"}
    end = end or {"type": "RUN_FINISHED", "threadId": "t", "runId": "r"}
    return [start, *middle, end]


@pytest.mark.parametrize("events", [
    [{"type": "TEXT_MESSAGE_START", "messageId": "m"}],
    _run({"type": "TEXT_MESSAGE_START", "messageId": "m"}),
    _run({"type": "TEXT_MESSAGE_CONTENT", "messageId": "m", "delta": "x"}),
    _run({"type": "REASONING_START", "messageId": "s"}),
    _run({"type": "REASONING_MESSAGE_START", "messageId": "m", "role": "reasoning"}),
    _run({"type": "TOOL_CALL_RESULT", "messageId": "m", "toolCallId": "c", "content": ""}),
    _run({"type": "TOOL_CALL_START", "toolCallId": "c", "toolCallName": "n"}),
    _run({"type": "STEP_FINISHED", "stepName": "s"}),
    _run({"type": "STEP_STARTED", "stepName": "s"}),
    _run({"type": "SUBAGENT_STARTED", "subagentRunId": "a", "name": "n"}),
    _run({"type": "SUBAGENT_STARTED", "subagentRunId": "a", "name": "n", "parentSubagentRunId": "p"},
         {"type": "SUBAGENT_FINISHED", "subagentRunId": "a"}),
    _run({"type": "SUBAGENT_STARTED", "subagentRunId": "a", "name": "n"},
         {"type": "SUBAGENT_FINISHED", "subagentRunId": "a"},
         {"type": "SUBAGENT_STARTED", "subagentRunId": "a", "name": "n"},
         {"type": "SUBAGENT_FINISHED", "subagentRunId": "a"}),
    _run({"type": "STATE_DELTA", "delta": []}),
    _run() + [{"type": "CUSTOM", "name": "x", "value": 1}],
    _run(end={"type": "RUN_ERROR", "message": "m"}) + [{"type": "RUN_ERROR", "message": "again"}],
    _run() + [{"type": "RUN_ERROR", "message": "a"}, {"type": "RUN_ERROR", "message": "b"}],
    [{"type": "RUN_STARTED", "threadId": "t", "runId": "r"}],
])
def test_the_ordering_verifier_rejects_violations(events):
    with pytest.raises(AssertionError):
        verify_ag_ui_sequence(events)


# ── Vendored schema and fixture set ─────────────────────────────────────────

def test_vendored_schema_is_the_pinned_ag_ui_1_0_schema():
    raw = SCHEMA_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SCHEMA_SHA256
    schema = json.loads(raw)
    assert schema["$id"] == "https://ag-ui.com/spec/1.0/schema.json"
    assert schema["$ref"] == "#/$defs/Event"
    Draft202012Validator.check_schema(schema)
    # Only ASCII: the one change against upstream is the dash replacement.
    raw.decode("ascii")
    readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
    assert UPSTREAM_SHA256 in readme and SCHEMA_SHA256 in readme
    assert "Permission is hereby granted" in (FIXTURES / "ag-ui-1.0.schema.LICENSE").read_text(encoding="utf-8")
    assert INDEX["schema"] == SCHEMA_PATH.name and INDEX["schemaSha256"] == SCHEMA_SHA256


def test_fixture_index_lists_every_journal_with_its_expected_events():
    journals = sorted(path.stem for path in FIXTURES.glob("*.jsonl"))
    assert sorted(CASES) == journals
    for case in INDEX["cases"]:
        assert case["journal"] == f"{case['name']}.jsonl"
        assert case["expected"] == f"{case['name']}.agui.json"
        assert (FIXTURES / case["expected"]).is_file() or UPDATE_GOLDEN
        assert case["covers"]


def test_fixtures_cover_every_recorded_journal_kind_the_plan_names():
    """Plan 5.1 tests: tool, sub-agent, todo, approval, cancel, error, group turn."""
    projected = {name: _project(name) for name in CASES}
    everything = [event for events in projected.values() for event in events]

    def has(predicate):
        return any(predicate(event) for event in everything)

    assert has(lambda e: e["type"] == "TOOL_CALL_RESULT")
    assert has(lambda e: e["type"] == "SUBAGENT_STARTED") and has(lambda e: e["type"] == "SUBAGENT_ERROR")
    assert has(lambda e: e["type"] == "ACTIVITY_SNAPSHOT" and e["activityType"] == "plan")
    assert has(lambda e: e["type"] == "CUSTOM" and e["name"] == "synthpulse.approval")
    assert has(lambda e: e["type"] == "RUN_FINISHED" and e["outcome"]["type"] == "cancelled")
    assert has(lambda e: e["type"] == "RUN_ERROR")
    assert has(lambda e: e["type"] == "CUSTOM" and e["name"] == "synthpulse.turn_bot")
    assert has(lambda e: e["type"] == "STEP_STARTED" and e["stepName"] == "preparation")


@pytest.mark.parametrize("name", CASES)
def test_every_recorded_journal_projects_to_its_expected_events(name):
    events = _project(name)
    expected_path = FIXTURES / _case(name)["expected"]
    if UPDATE_GOLDEN:
        expected_path.write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert events == json.loads(expected_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", CASES)
def test_every_projected_event_is_schema_valid(name, validator):
    for index, event in enumerate(_project(name)):
        errors = sorted(validator.iter_errors(event), key=lambda e: list(e.path))
        assert not errors, (index, event, [e.message for e in errors[:3]])


@pytest.mark.parametrize("name", CASES)
def test_no_projected_event_carries_null_or_a_non_finite_number(name):
    for event in _project(name):
        for path, value in _walk(event):
            assert value is not None, path
            if isinstance(value, float):
                assert math.isfinite(value), path


@pytest.mark.parametrize("name", CASES)
def test_projection_obeys_the_ag_ui_ordering_rules(name):
    verify_ag_ui_sequence(_project(name), allow_truncated=name == "truncated_run")


@pytest.mark.parametrize("name", CASES)
def test_live_feed_equals_the_journal_projection(name):
    """The live tail (W10) feeds frame by frame; the replay projects the file."""
    rows = _rows(name)
    projector = Projector(ProjectionContext(thread_id=rows[0]["session_id"], run_id=rows[0]["run_id"]))
    live = []
    for row in rows:
        live.extend(projector.feed(row["event"], row["payload"], seq=row["seq"], timestamp=row["created_at"]))
    live.extend(projector.finish(timestamp=rows[-1]["created_at"]))
    assert live == project_journal(rows)
    assert project_journal(rows) == project_journal(copy.deepcopy(rows))


def test_the_truncated_journal_is_not_given_an_ending():
    events = _project("truncated_run")
    assert events[-1]["type"] == "STEP_STARTED"
    assert not {"RUN_FINISHED", "RUN_ERROR"} & set(_types(events))


# ── Text, reasoning and tool calls ───────────────────────────────────────────

def test_tokens_stream_one_message_that_a_tool_boundary_closes():
    events = _feed_all(Projector(_ctx()), [
        ("token", {"text": "Hel"}),
        ("token", {"text": "lo"}),
        ("tool", {"name": "search", "args": {"q": "x"}, "tid": "c1"}),
        ("token", {"text": "Done"}),
        ("done", {}),
        ("stream_end", {}),
    ])
    assert _types(events) == [
        "RUN_STARTED", "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_CONTENT",
        "TEXT_MESSAGE_END", "TOOL_CALL_START", "TOOL_CALL_ARGS", "TOOL_CALL_END",
        "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END", "RUN_FINISHED",
    ]
    assert events[1] == {"type": "TEXT_MESSAGE_START", "messageId": "run_1:text:1", "role": "assistant"}
    assert [e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT"] == ["Hel", "lo", "Done"]
    assert events[5]["parentMessageId"] == "run_1:text:1"
    assert events[6]["delta"] == '{"q":"x"}'
    assert events[-1] == {"type": "RUN_FINISHED", "threadId": "sess_1", "runId": "run_1",
                          "outcome": {"type": "success"}}
    assert events[0] =={"type": "RUN_STARTED", "threadId": "sess_1", "runId": "run_1", "protocolVersion": "1.0"}
    verify_ag_ui_sequence(events)


def test_interim_message_that_already_streamed_only_closes_the_open_message():
    events = _feed_all(Projector(_ctx()), [
        ("token", {"text": "Checking."}),
        ("interim_assistant", {"text": "Checking.", "already_streamed": True}),
        ("interim_assistant", {"text": "  ", "already_streamed": False}),
    ])
    assert _types(events) == ["RUN_STARTED", "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END"]


def test_interim_message_that_did_not_stream_is_one_whole_message():
    events = _feed_all(Projector(_ctx()), [
        ("reasoning", {"text": "think"}),
        ("interim_assistant", {"text": " I will look first. ", "already_streamed": False}),
    ])
    assert _types(events)[-5:] == ["REASONING_MESSAGE_END", "REASONING_END", "TEXT_MESSAGE_START",
                                   "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END"]
    assert events[-2]["delta"] == "I will look first."


def test_reasoning_frames_are_passed_on_as_deltas():
    """The native reasoning frame is new text since the last frame, not cumulative."""
    events = _feed_all(Projector(_ctx()), [
        ("reasoning", {"text": "ab"}),
        ("reasoning", {"text": "abcd"}),
        ("reasoning", {"text": ""}),
        ("token", {"text": "x"}),
    ])
    assert _types(events)[:3] == ["RUN_STARTED", "REASONING_START", "REASONING_MESSAGE_START"]
    assert events[2] == {"type": "REASONING_MESSAGE_START", "messageId": "run_1:reasoning:1:message",
                         "role": "reasoning"}
    assert [e["delta"] for e in events if e["type"] == "REASONING_MESSAGE_CONTENT"] == ["ab", "abcd"]
    assert _types(events)[5:7] == ["REASONING_MESSAGE_END", "REASONING_END"]


def test_legacy_tool_calls_get_sequence_ids_and_results_match_by_name():
    projector = Projector(_ctx())
    events = []
    events += projector.feed("tool", {"name": "grep", "args": {"p": "a"}}, seq=7)
    events += projector.feed("tool", {"name": "grep", "args": {"p": "b"}}, seq=8)
    events += projector.feed("tool", {"name": "read", "args": {}}, seq=9)
    events += projector.feed("tool_complete", {"name": "grep", "preview": "b hits", "duration": 0.25}, seq=10)
    events += projector.feed("tool_complete", {"name": "grep", "preview": "a hits", "is_error": True}, seq=11)
    events += projector.feed("tool_complete", {"name": "grep", "preview": "extra"}, seq=12)
    results = [e for e in events if e["type"] == "TOOL_CALL_RESULT"]
    assert [(r["toolCallId"], r["content"]) for r in results][:2] == [("t8", "b hits"), ("t7", "a hits")]
    timings = [e["value"] for e in events if e["type"] == "CUSTOM"]
    assert timings[0] == {"toolCallId": "t8", "durationMs": 250, "isError": False}
    assert timings[1] == {"toolCallId": "t7", "isError": True}
    # The third grep result has no open grep call: it opens its own call first.
    assert results[2]["toolCallId"] == "t12"
    assert "durationMs" not in timings[2]


def test_structured_tool_ids_are_kept_and_duplicates_are_ignored():
    projector = Projector(_ctx())
    events = []
    events += projector.feed("tool", {"name": "web", "args": {"q": 1}, "tid": "call_1"}, timestamp=10.0)
    events += projector.feed("tool", {"name": "web", "args": {"q": 1}, "tid": "call_1"}, timestamp=10.1)
    events += projector.feed("tool_complete", {"name": "web", "tid": "call_1", "preview": "ok"}, timestamp=11.5)
    events += projector.feed("tool_complete", {"name": "web", "tid": "call_1", "preview": "again"}, timestamp=12.0)
    assert _types(events).count("TOOL_CALL_START") == 1
    assert _types(events).count("TOOL_CALL_RESULT") == 1
    result = next(e for e in events if e["type"] == "TOOL_CALL_RESULT")
    assert result == {"type": "TOOL_CALL_RESULT", "messageId": "run_1:tool-result:call_1", "toolCallId": "call_1",
                      "content": "ok", "role": "tool", "timestamp": 11500}
    timing = next(e for e in events if e["type"] == "CUSTOM")["value"]
    assert timing == {"toolCallId": "call_1", "durationMs": 1500, "isError": False}


def test_a_result_for_a_call_that_never_started_opens_the_call_without_a_duration():
    projector = Projector(_ctx())
    events = projector.feed("tool_complete", {"name": "fetch", "tid": "call_9", "preview": {"a": None, "b": 1}},
                            timestamp=5.0)
    assert _types(events) == ["RUN_STARTED", "TOOL_CALL_START", "TOOL_CALL_ARGS", "TOOL_CALL_END",
                              "TOOL_CALL_RESULT", "CUSTOM"]
    assert events[4]["content"] == '{"b":1}'
    assert events[5]["value"] == {"toolCallId": "call_9", "isError": False}


# ── Run lifecycle ────────────────────────────────────────────────────────────

def test_run_finished_waits_for_stream_end_so_later_frames_stay_inside_the_run():
    events = _feed_all(Projector(_ctx()), [
        ("token", {"text": "a"}),
        ("done", {"usage": {"input_tokens": 5}}),
        ("metering", {"ttft_ms": 120, "active": 9, "high": 80.0, "tps": 33.0}),
        ("title_status", {"state": "pending"}),
        ("stream_end", {}),
        ("title", {"title": "After the end"}),
        ("token", {"text": "late"}),
    ])
    assert _types(events) == ["RUN_STARTED", "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END",
                              "STATE_SNAPSHOT", "STATE_DELTA", "CUSTOM", "RUN_FINISHED"]
    assert events[-1]["outcome"] == {"type": "success"}
    verify_ag_ui_sequence(events)


def test_finish_sends_the_waiting_run_finished_when_stream_end_is_missing():
    projector = Projector(_ctx())
    events = _feed_all(projector, [("token", {"text": "a"}), ("done", {})])
    assert "RUN_FINISHED" not in _types(events)
    tail = projector.finish(timestamp=2.0)
    assert tail == [{"type": "RUN_FINISHED", "threadId": "sess_1", "runId": "run_1",
                     "outcome": {"type": "success"}, "timestamp": 2000}]
    assert projector.closed and projector.finish() == []


def test_stream_end_without_done_finishes_the_run_as_a_success():
    events = _feed_all(Projector(_ctx()), [("step", {"name": "prep", "status": "started"}), ("stream_end", {})])
    assert _types(events) == ["RUN_STARTED", "STEP_STARTED", "STEP_FINISHED", "RUN_FINISHED"]
    verify_ag_ui_sequence(events)


def test_cancel_closes_everything_before_the_cancelled_run_finished():
    projector = Projector(_ctx())
    events = _feed_all(projector, [
        ("token", {"text": "a"}),
        ("reasoning", {"text": "b"}),
        ("compressing", {}),
        ("subagent", {"id": "s1", "status": "running", "summary": "Look"}),
        ("cancel", {"message": "Cancelled by user", "type": "cancelled"}),
        ("token", {"text": "dropped"}),
        ("done", {}),
        ("apperror", {"type": "cancelled", "message": "Cancelled"}),
    ])
    tail = _types(events)[_types(events).index("SUBAGENT_STARTED") + 2:]
    assert tail == ["REASONING_MESSAGE_END", "REASONING_END", "TEXT_MESSAGE_END", "STEP_FINISHED",
                    "SUBAGENT_ERROR", "RUN_FINISHED"]
    assert events[-2]["code"] == "cancelled"
    assert events[-1]["outcome"] == {"type": "cancelled"}
    verify_ag_ui_sequence(events)


def test_a_failure_after_a_finished_run_is_reported_once_as_run_error():
    projector = Projector(_ctx())
    events = _feed_all(projector, [
        ("done", {}), ("stream_end", {}),
        ("apperror", {"type": "save_failed", "message": "Saving failed"}),
        ("apperror", {"type": "other", "message": "Second"}),
        ("stream_end", {}),
    ])
    assert _types(events) == ["RUN_STARTED", "RUN_FINISHED", "RUN_ERROR"]
    assert events[-1] == {"type": "RUN_ERROR", "message": "Saving failed", "code": "save_failed"}
    verify_ag_ui_sequence(events)


def test_apperror_ends_the_run_with_run_error_and_nothing_follows():
    events = _feed_all(Projector(_ctx()), [
        ("token", {"text": "a"}),
        ("apperror", {"message": "x" * 5000, "type": "Rate_Limit", "hint": "wait"}),
        ("token", {"text": "b"}),
        ("done", {}),
        ("stream_end", {}),
    ])
    assert _types(events) == ["RUN_STARTED", "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "RUN_ERROR"]
    assert events[-1]["code"] == "rate_limit" and len(events[-1]["message"]) == 2000
    error = _feed_all(Projector(_ctx()), [("error", {})])[-1]
    assert error == {"type": "RUN_ERROR", "message": "The run failed."}
    verify_ag_ui_sequence(events)


def test_a_cancelled_apperror_is_a_cancelled_run():
    events = _feed_all(Projector(_ctx()), [("token", {"text": "a"}), ("apperror", {"type": "Cancelled"})])
    assert _types(events)[-2:] == ["TEXT_MESSAGE_END", "RUN_FINISHED"]
    assert events[-1]["outcome"] == {"type": "cancelled"}


@pytest.mark.parametrize("frame", [
    ("done", {"terminal_state": "tool_limit_reached", "terminal_reason": "max_iterations"}),
    ("apperror", {"type": "tool_limit_reached", "terminal_state": "tool_limit_reached",
                  "terminal_reason": "max_iterations", "message": "Stopped"}),
])
def test_a_tool_limit_stop_is_a_cancelled_run_with_its_reason(frame):
    events = _feed_all(Projector(_ctx()), [("token", {"text": "a"}), frame, ("stream_end", {})])
    custom = next(e for e in events if e["type"] == "CUSTOM")
    assert custom["name"] == "synthpulse.terminal_state"
    assert custom["value"] == {"state": "tool_limit_reached", "reason": "max_iterations"}
    assert events[-1]["type"] == "RUN_FINISHED" and events[-1]["outcome"] == {"type": "cancelled"}
    verify_ag_ui_sequence(events)


def test_unknown_and_journal_only_frames_are_dropped():
    events = _feed_all(Projector(_ctx()), [
        ("preparation", {"phase": "x"}),
        ("run_timing", {"stage": "agent_run"}),
        ("bg_task_complete", {"x": 1}),
        ("peer_turn_started", {"x": 1}),
        (None, {"x": 1}),
    ])
    assert _types(events) == ["RUN_STARTED"]


def test_feed_tolerates_malformed_frames():
    projector = Projector(_ctx())
    events = []
    events += projector.feed("token", None)
    events += projector.feed("token", ["not", "a", "dict"])
    events += projector.feed("token", {"text": 12}, seq=True, timestamp=float("nan"))
    events += projector.feed("tool", {"name": None, "args": "raw text", "tid": ""}, seq=-3, timestamp=-1)
    events += projector.feed("subagent", {"id": 5, "status": "running"})
    events += projector.feed("subagent", {"id": "ok", "status": "exploded"})
    events += projector.feed("todo_state", {"todos": "nope"})
    events += projector.feed("step", {"name": "x" * 200, "status": "started"})
    events += projector.feed("turn_bot", {"bot": ""})
    events += projector.feed("context_status", {"prefill": "nope"})
    assert _types(events) == ["RUN_STARTED", "TEXT_MESSAGE_START", "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_END",
                              "TOOL_CALL_START", "TOOL_CALL_ARGS", "TOOL_CALL_END"]
    assert events[2]["delta"] == "12" and "timestamp" not in events[2]
    assert events[4]["toolCallName"] == "tool" and events[4]["toolCallId"] == "t4"
    assert events[5]["delta"] == '"raw text"'


def test_projection_context_is_required():
    with pytest.raises(TypeError):
        Projector({"thread_id": "a", "run_id": "b"})
    with pytest.raises(ValueError):
        Projector(ProjectionContext(thread_id="", run_id="b"))
    assert project_journal([]) == []


# ── Subagents, activity and state ────────────────────────────────────────────

def test_subagent_lifecycle_follows_the_ag_ui_rules():
    events = _feed_all(Projector(_ctx()), [
        ("subagent", {"id": "a", "status": "queued", "summary": "First", "task_count": 2}),
        ("subagent", {"id": "a", "status": "running", "tool_count": 2}),
        ("subagent", {"id": "b", "status": "running", "parent_id": "a"}),
        ("subagent", {"id": "c", "status": "running", "parent_id": "nobody"}),
        ("subagent", {"id": "a", "status": "completed", "duration_seconds": 1.5}),
        ("subagent", {"id": "a", "status": "running"}),
        ("subagent", {"id": "b", "status": "failed"}),
        ("done", {}),
        ("stream_end", {}),
    ])
    started = [e for e in events if e["type"] == "SUBAGENT_STARTED"]
    assert started[0] == {"type": "SUBAGENT_STARTED", "subagentRunId": "a", "name": "subagent",
                          "description": "First"}
    assert started[1]["parentSubagentRunId"] == "a" and "parentSubagentRunId" not in started[2]
    assert [e["type"] for e in events if e.get("subagentRunId") == "a"] == [
        "SUBAGENT_STARTED", "SUBAGENT_FINISHED"]
    closing = [e for e in events if e["type"] == "SUBAGENT_ERROR"]
    assert [(e["subagentRunId"], e["code"]) for e in closing] == [("b", "failed"), ("c", "unfinished")]
    snapshot = next(e for e in events if e["type"] == "ACTIVITY_SNAPSHOT")
    assert snapshot == {"type": "ACTIVITY_SNAPSHOT", "messageId": "run_1:subagent:a", "activityType": "subagent",
                        "content": {"id": "a", "status": "queued", "summary": "First", "taskCount": 2}}
    verify_ag_ui_sequence(events)


def test_todo_state_is_a_plan_activity_that_replaces_itself():
    events = _feed_all(Projector(_ctx()), [
        ("todo_state", {"todos": [{"id": "1", "content": "A", "status": "pending", "note": None}],
                        "summary": {"total": 1}, "session_id": "s", "ts": 1.0, "version": 1}),
        ("todo_state", {"todos": [], "summary": "bad"}),
    ])
    plans = [e for e in events if e["type"] == "ACTIVITY_SNAPSHOT"]
    assert [p["messageId"] for p in plans] == ["run_1:plan", "run_1:plan"]
    assert plans[0]["content"] == {"todos": [{"id": "1", "content": "A", "status": "pending"}],
                                   "summary": {"total": 1}}
    assert plans[1]["content"] == {"todos": []}


def test_goal_frames_are_one_goal_activity_without_the_judge_decision():
    events = _feed_all(Projector(_ctx()), [
        ("goal", {"state": "idle", "message": "Goal met.", "message_key": "goal_met", "message_args": ["x"],
                  "decision": {"secret_reasoning": "internal"}}),
        ("goal_continue", {"continuation_prompt": "Next", "decision": {"should_continue": True}}),
    ])
    goals = [e for e in events if e["type"] == "ACTIVITY_SNAPSHOT"]
    assert goals[0]["content"] == {"state": "idle", "message": "Goal met.", "messageKey": "goal_met",
                                   "messageArgs": ["x"]}
    assert goals[1]["content"] == {"state": "continuing", "continuationPrompt": "Next"}
    assert {g["messageId"] for g in goals} == {"run_1:goal"}


def test_state_is_one_snapshot_then_rfc_6902_deltas():
    events = _feed_all(Projector(_ctx()), [
        ("context_status", {"prefill": {"status": "loaded", "source": "file", "label": "Team notes",
                                        "message_count": 3, "compacted": True}}),
        ("metering", {"usage": {"input_tokens": 10, "output_tokens": 1, "cost_status": "unknown",
                                "estimated_cost": None}}),
        ("metering", {"usage": {"input_tokens": 10, "output_tokens": 1}}),
        ("metering", {"usage": {"input_tokens": 20, "output_tokens": 1}, "ttft_ms": 90}),
        ("compressed", {"usage": {"context_length": 1000}}),
    ])
    states = [e for e in events if e["type"].startswith("STATE_")]
    assert _types(states) == ["STATE_SNAPSHOT", "STATE_DELTA", "STATE_DELTA", "STATE_DELTA"]
    assert states[0]["snapshot"] == {"context": {"prefillStatus": "loaded", "prefillSource": "file",
                                                 "prefillMessageCount": 3, "prefillCompacted": True}}
    assert states[1]["delta"] == [{"op": "add", "path": "/usage",
                                   "value": {"inputTokens": 10, "outputTokens": 1, "costStatus": "unknown"}}]
    assert states[2]["delta"] == [{"op": "replace", "path": "/usage/inputTokens", "value": 20},
                                  {"op": "add", "path": "/usage/ttftMs", "value": 90}]
    final = verify_ag_ui_sequence(events, allow_truncated=True)
    assert final == {"context": {"prefillStatus": "loaded", "prefillSource": "file", "prefillMessageCount": 3,
                                 "prefillCompacted": True},
                     "usage": {"inputTokens": 20, "outputTokens": 1, "costStatus": "unknown", "ttftMs": 90,
                               "contextLength": 1000}}


def test_metering_never_exposes_server_wide_numbers_or_routing():
    events = _feed_all(Projector(_ctx()), [
        ("metering", {"tps": 41.0, "high": 90.0, "low": 1.0, "active": 7, "estimated": False,
                      "usage": {"input_tokens": 1, "gateway_routing": {"route": "x"}, "used_model": "m",
                                "cost_source": "table", "tps": float("inf")}}),
    ])
    assert events[-1]["snapshot"] == {"usage": {"inputTokens": 1}}


def test_approval_exposes_only_the_documented_fields():
    events = _feed_all(Projector(_ctx()), [
        ("approval", {"approval_id": "gw:1", "command": "rm x", "description": "Delete", "pattern_key": "del",
                      "pattern_keys": ["del"], "pending_count": 2, "_gateway_mirror_token": "secret-token",
                      "_webui_mirror_token": "t", "run_id": "internal-run", "session_key": "internal"}),
        ("approval", {}),
    ])
    custom, activity, second_custom, second_activity = events[1:]
    assert custom["value"] == {"approvalId": "gw:1", "command": "rm x", "description": "Delete",
                               "patternKey": "del", "patternKeys": ["del"], "pendingCount": 2}
    assert activity == {"type": "ACTIVITY_SNAPSHOT", "messageId": "run_1:approval:gw:1", "activityType": "approval",
                        "content": {"kind": "approval", "status": "pending", "approvalId": "gw:1",
                                    "description": "Delete"}}
    assert second_custom["value"] == {} and second_activity["messageId"] == "run_1:approval:2"
    assert "secret-token" not in json.dumps(events)


def test_clarify_is_a_custom_event_and_an_approval_activity():
    events = _feed_all(Projector(_ctx()), [
        ("clarify", {"question": "Which?", "choices": ["a", None, 3], "clarify_id": "c1", "timeout_seconds": 60,
                     "_session_id": "s"}),
    ])
    assert events[1]["value"] == {"clarifyId": "c1", "question": "Which?", "timeoutSeconds": 60,
                                  "choices": ["a", "3"]}
    assert events[2]["content"] == {"kind": "clarify", "status": "pending", "clarifyId": "c1", "question": "Which?"}
    assert events[2]["activityType"] == "approval"


def test_turn_bot_is_a_custom_event_and_names_the_bot_on_later_messages():
    events = _feed_all(Projector(_ctx()), [
        ("turn_bot", {"bot": "sales", "reason": "default", "session_id": "s", "extra": "x"}),
        ("token", {"text": "hi"}),
    ])
    assert events[1] == {"type": "CUSTOM", "name": "synthpulse.turn_bot", "value": {"bot": "sales",
                                                                                   "reason": "default"}}
    assert events[2]["name"] == "sales"
    assert _feed_all(Projector(_ctx()), [("turn_bot", {"bot_profile": "ops"})])[1]["value"] == {"bot": "ops"}


def test_step_frames_follow_the_documented_contract():
    events = _feed_all(Projector(_ctx()), [
        ("step", {"name": "prep", "status": "started"}),
        ("step", {"name": "prep", "status": "started"}),
        ("step", {"name": "prep", "status": "finished"}),
        ("step", {"name": "prep", "status": "finished"}),
        ("step", {"name": "run", "status": "started"}),
        ("step", {"name": "other", "status": "paused"}),
        ("compressing", {}),
        ("compressed", {}),
        ("done", {}),
        ("stream_end", {}),
    ])
    assert [(e["type"], e.get("stepName")) for e in events[1:]] == [
        ("STEP_STARTED", "prep"), ("STEP_FINISHED", "prep"), ("STEP_STARTED", "prep"), ("STEP_FINISHED", "prep"),
        ("STEP_STARTED", "run"), ("STEP_STARTED", "compress"), ("STEP_FINISHED", "compress"),
        ("STEP_FINISHED", "run"), ("RUN_FINISHED", None)]
    verify_ag_ui_sequence(events)


def test_passthrough_frames_become_custom_events_without_private_keys_or_nulls():
    events = _feed_all(Projector(_ctx()), [
        ("warning", {"type": "fallback", "message": "Busy", "detail": None, "_internal": 1}),
        ("state_saved", {"kind": "skill", "action": "updated", "name": "report"}),
        ("pending_steer_leftover", {"text": "later"}),
        ("title", {"title": "T"}),
        ("title_status", {"state": "done"}),
    ])
    assert [(e["name"], e["value"]) for e in events[1:]] == [
        ("synthpulse.warning", {"type": "fallback", "message": "Busy"}),
        ("synthpulse.state_saved", {"kind": "skill", "action": "updated", "name": "report"}),
        ("synthpulse.pending_steer_leftover", {"text": "later"}),
        ("synthpulse.title", {"title": "T"}),
        ("synthpulse.title_status", {"state": "done"}),
    ]


# ── Messages snapshot ────────────────────────────────────────────────────────

SECRET = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


def test_messages_snapshot_redacts_credentials_by_default():
    projector = Projector(ProjectionContext(thread_id="sess_1", run_id="run_1"))
    events = _feed_all(projector, [
        ("done", {"session": {"messages": [
            {"role": "user", "content": f"my token is {SECRET}"},
            {"role": "assistant", "content": "Noted.", "bot_profile": "ops"},
        ]}}),
    ])
    snapshot = next(e for e in events if e["type"] == "MESSAGES_SNAPSHOT")
    assert SECRET not in json.dumps(snapshot)
    assert snapshot["messages"][1] == {"id": "sess_1:message:1", "role": "assistant", "name": "ops",
                                       "content": "Noted."}


def test_messages_snapshot_is_left_out_when_redaction_fails():
    def broken(_messages):
        raise RuntimeError("redactor unavailable")

    projector = Projector(ProjectionContext(thread_id="s", run_id="r", redact_messages=broken))
    events = _feed_all(projector, [("done", {"session": {"messages": [{"role": "user", "content": SECRET}]}}),
                                   ("stream_end", {})])
    assert _types(events) == ["RUN_STARTED", "RUN_FINISHED"]
    assert SECRET not in json.dumps(events)


def test_messages_snapshot_converts_roles_and_skips_what_ag_ui_cannot_express():
    events = _feed_all(Projector(_ctx()), [("done", {"session": {"messages": [
        {"role": "user", "content": [{"type": "text", "text": "a"}, {"type": "image_url", "image_url": "x"},
                                     "b"]},
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": "c1", "function": {"name": "f", "arguments": {"k": None, "v": 1}}},
            {"id": "", "function": {"name": "g"}},
            {"id": "c2", "function": {}},
            "junk"]},
        {"role": "tool", "tool_call_id": "c1", "content": {"ok": True}},
        {"role": "tool", "content": "no call id"},
        {"role": "system", "content": "sys"},
        {"role": "developer", "content": "dev"},
        {"role": "narrator", "content": "unknown role"},
        "not a message",
    ]}})])
    messages = next(e for e in events if e["type"] == "MESSAGES_SNAPSHOT")["messages"]
    assert messages == [
        {"id": "sess_1:message:0", "role": "user", "content": "a\nb"},
        {"id": "sess_1:message:1", "role": "assistant", "toolCalls": [
            {"id": "c1", "type": "function", "function": {"name": "f", "arguments": '{"v":1}'}}]},
        {"id": "sess_1:message:2", "role": "tool", "content": '{"ok":true}', "toolCallId": "c1"},
        {"id": "sess_1:message:4", "role": "system", "content": "sys"},
        {"id": "sess_1:message:5", "role": "developer", "content": "dev"},
    ]


# ── Wire format ──────────────────────────────────────────────────────────────

def test_encode_sse_frames_one_json_object_per_data_line_with_lf():
    events = project_journal(_rows("group_turn"))
    body = encode_sse(events)
    assert b"\r" not in body
    frames = body.decode("utf-8").split("\n\n")
    assert frames[-1] == ""
    frames = frames[:-1]
    assert len(frames) == len(events)
    for frame, event in zip(frames, events, strict=True):
        assert frame.startswith("data: ") and "\n" not in frame
        assert json.loads(frame[len("data: "):]) == event
    assert b"null" not in body


def test_non_finite_numbers_never_reach_the_wire():
    events = _feed_all(Projector(_ctx()), [
        ("metering", {"usage": {"input_tokens": float("nan"), "output_tokens": 2}}),
        ("warning", {"message": "x", "ratio": float("inf")}),
        ("tool_complete", {"name": "x", "duration": float("nan")}),
    ])
    encode_sse(events)  # allow_nan=False would raise on a non-finite number
    assert events[1]["snapshot"] == {"usage": {"outputTokens": 2}}
    assert events[2]["value"] == {"message": "x"}


def test_module_constants_describe_the_protocol_version_and_route():
    assert agui.PROTOCOL_VERSION == "1.0"
    assert agui.ROUTE_PREFIX == "/api/agui/runs/"
    assert agui.CUSTOM_PREFIX == "synthpulse."
