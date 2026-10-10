# RFC: AG-UI Projection v1

- **Status:** Implemented (Wave 1: projector, fixtures, replay route)
- **Author:** Synthwave managed-service program, package W5
- **Created:** 2026-09-28
- **Code:** `api/agui.py`
- **Tests:** `tests/test_agui_projection.py`, `tests/test_agui_replay_route.py`
- **Fixtures:** `tests/fixtures/agui/` (shared with the browser port)

## Problem

The WebUI streams its own SSE vocabulary (`token`, `tool`, `done` and about
twenty more) and journals every frame in
`<SESSION_DIR>/_run_journal/<session_id>/<stream_id>.jsonl`
(`api/run_journal.py`). Clients that speak AG-UI, and the planned run
visualisations, need the same runs as AG-UI 1.0 events, without the WebUI
taking a runtime dependency on an AG-UI SDK and without changing the native
stream.

## Goals

- A pure projector from native frames to AG-UI 1.0 events that one live
  consumer (the tail, Wave 2) and one replay consumer (this RFC) share.
- Every emitted event valid against the AG-UI 1.0 JSON Schema, and every
  sequence valid under the AG-UI 1.0 ordering rules (lifecycle, streaming,
  steps, subagents).
- No `null` on the wire: an optional field without a value is omitted.
- A replay route for finished runs that only the conversation's owner or a
  current participant can use.

## Non-goals

- The live tail of a running stream (Wave 2, W10: the drain loop extraction
  from `_handle_sse_stream` comes first, with regression tests on the native
  stream).
- The inbound `POST /api/agui/run` for external clients (Wave 3; its
  authentication design is reviewed before any code).
- Run visualisations in the browser (W10).
- Adopting `@ag-ui/client` or `ag-ui-protocol` at runtime.

## Protocol version and schema

- Protocol: AG-UI 1.0. `RUN_STARTED` carries `protocolVersion: "1.0"`, which
  the 1.0 versioning rules require of a producer.
- Schema: `docs/spec/1.0/schema.json` of the AG-UI repository at the tag
  `ag-ui-protocol@1.0.0` (commit `f08ccf85`), identical to the file at its
  `$id`, `https://ag-ui.com/spec/1.0/schema.json`. It is vendored as a test
  asset in `tests/fixtures/agui/ag-ui-1.0.schema.json` with its MIT license;
  the fixture README records the upstream and vendored sha256 and the single
  change (the em dash inside description annotations replaced by a hyphen).
  Validation uses `jsonschema` (Draft 2020-12), already a dev dependency.

## Interfaces

```python
ctx = ProjectionContext(thread_id=session_id, run_id=stream_id)
projector = Projector(ctx)
events = projector.feed(event_name, data, seq=journal_seq, timestamp=created_at)
events += projector.finish(timestamp=last_created_at)

events = project_journal(rows)        # one run's journal rows, in order
body = encode_sse(events)             # b"data: {json}\n\n" per event
```

- `seq` is the journal sequence number. It makes the synthetic tool call ids
  (`t<seq>`) identical between a live projection and a replay. Without it the
  projector counts the frames it was fed.
- `timestamp` is the journal `created_at` in seconds; events carry it as
  integer milliseconds. Without it events carry no `timestamp`, so the output
  stays deterministic.
- `ProjectionContext.redact_messages` redacts the conversation before
  `MESSAGES_SNAPSHOT`; the default is the WebUI's credential redaction
  (`api.helpers.redact_session_data`).
- The projector never raises on malformed frames: a frame it cannot use
  projects to nothing.

## Mapping

Identifiers: `threadId` is the session id and `runId` the stream id. Message
ids are derived from the run: `<run>:text:<n>`, `<run>:reasoning:<n>` (span)
and `<run>:reasoning:<n>:message`, `<run>:tool-result:<toolCallId>`,
`<run>:plan`, `<run>:goal`, `<run>:subagent:<id>`, `<run>:approval:<id>`,
`<run>:clarify:<id>`. Snapshot messages are `<thread>:message:<index>`, the
index being the message's position in the native transcript.

| Native frame | AG-UI 1.0 events |
|--------------|------------------|
| first frame of a run | `RUN_STARTED {threadId, runId, protocolVersion}` |
| `turn_bot` | `CUSTOM synthpulse.turn_bot {bot, reason?}`; later text messages carry `name: <bot>` |
| `token` | `TEXT_MESSAGE_START {messageId, role: "assistant", name?}` for the first token of a message, then `TEXT_MESSAGE_CONTENT {delta}` |
| `interim_assistant` | not streamed: `TEXT_MESSAGE_START`, `CONTENT`, `END` with the visible text; `already_streamed`: only closes the open message |
| `reasoning` | `REASONING_START`, `REASONING_MESSAGE_START {role: "reasoning"}`, then `REASONING_MESSAGE_CONTENT {delta}`; closed by `REASONING_MESSAGE_END`, `REASONING_END` at the next token, interim message, tool frame or run end |
| `tool` | closes the open text and reasoning, then `TOOL_CALL_START {toolCallId, toolCallName, parentMessageId?}`, `TOOL_CALL_ARGS {delta: compact sorted JSON of the args}`, `TOOL_CALL_END`; id = `tid` or `t<seq>` |
| `tool_complete` | `TOOL_CALL_RESULT {messageId, toolCallId, content, role: "tool"}` plus `CUSTOM synthpulse.tool_timing {toolCallId, durationMs?, isError}` |
| `subagent` | `SUBAGENT_STARTED` at the first sighting, `ACTIVITY_SNAPSHOT` (activityType `subagent`), then `SUBAGENT_FINISHED` (completed) or `SUBAGENT_ERROR` (failed, cancelled) |
| `todo_state` | `ACTIVITY_SNAPSHOT` (activityType `plan`, content `{todos, summary}`) |
| `goal`, `goal_continue` | `ACTIVITY_SNAPSHOT` (activityType `goal`) |
| `context_status` | state under `/context` |
| `metering` | state under `/usage` |
| `compressing`, `compressed` | `STEP_STARTED`, `STEP_FINISHED` with `stepName: "compress"`; `compressed` also updates `/usage` |
| `step` | `STEP_STARTED` or `STEP_FINISHED` (contract below) |
| `approval` | `CUSTOM synthpulse.approval` plus `ACTIVITY_SNAPSHOT` (activityType `approval`, `kind: "approval"`) |
| `clarify` | `CUSTOM synthpulse.clarify` plus `ACTIVITY_SNAPSHOT` (activityType `approval`, `kind: "clarify"`) |
| `warning`, `title`, `title_status`, `state_saved`, `pending_steer_leftover` | `CUSTOM synthpulse.<name>` with the native payload |
| `apperror`, `error` | `RUN_ERROR {message, code?}` (`code` is the native `type`); cancel and tool limit types as below |
| `cancel` | everything open is closed, then `RUN_FINISHED {outcome: {type: "cancelled"}}` |
| `done` | `MESSAGES_SNAPSHOT` (redacted), usage into state; `RUN_FINISHED {outcome: {type: "success"}}` follows at `stream_end` |
| `stream_end` | the waiting `RUN_FINISHED`; transport only otherwise |
| `preparation`, `run_timing` (journal only), `bg_task_complete`, anything else | nothing |

### State

State is one object, sent as `STATE_SNAPSHOT` at the first state-bearing frame
and as `STATE_DELTA` (RFC 6902 `add` and `replace`) afterwards. Frames merge
into it; a key never disappears within a run.

```json
{
  "context": {"prefillStatus": "loaded", "prefillSource": "file", "prefillMessageCount": 3, "prefillCompacted": true},
  "usage": {"inputTokens": 2400, "outputTokens": 90, "cacheReadTokens": 800, "cacheWriteTokens": 0,
            "contextLength": 200000, "thresholdTokens": 160000, "lastPromptTokens": 2400,
            "postCompressionContextTokensEstimate": 5000, "estimatedCost": 0.0042, "costStatus": "estimated",
            "cacheHitPercent": 33.3, "turnCacheHitPercent": 33.3, "durationSeconds": 4.2, "tps": 38.5,
            "ttftMs": 350}
}
```

Only these fields are copied. The metering frame's top level (`tps`, `high`,
`low`, `active`) describes every stream on the server, not this run, and the
usage block's routing details (`gateway_routing`, `used_model`, `cost_source`)
are not run state; both stay out.

### Activities

| activityType | messageId | content |
|--------------|-----------|---------|
| `plan` | `<run>:plan` | `{todos: [...], summary?: {...}}` (the native snapshot, nulls removed) |
| `goal` | `<run>:goal` | `{state?, message?, messageKey?, messageArgs?, continuationPrompt?}` (the judge's `decision` stays out) |
| `subagent` | `<run>:subagent:<id>` | `{id, status, summary?, taskIndex?, taskCount?, toolCount?, durationSeconds?, parentId?}` |
| `approval` | `<run>:approval:<approvalId or n>` | `{kind: "approval", status: "pending", approvalId?, description?}` |
| `approval` | `<run>:clarify:<clarifyId or n>` | `{kind: "clarify", status: "pending", clarifyId?, question?}` |

Each snapshot replaces the activity (the AG-UI default).

### Custom events

All names carry the `synthpulse.` prefix. Values:

| name | value |
|------|-------|
| `turn_bot` | `{bot, reason?}` |
| `tool_timing` | `{toolCallId, durationMs?, isError}` |
| `approval` | `{approvalId?, command?, description?, patternKey?, patternKeys?, pendingCount?}` |
| `clarify` | `{clarifyId?, question?, description?, timeoutSeconds?, choices?}` |
| `terminal_state` | `{state: "tool_limit_reached", reason?}` |
| `warning`, `title`, `title_status`, `state_saved`, `pending_steer_leftover` | the native payload, without `null` values and without keys that start with an underscore |

## Contracts for frames that later packages emit

These frames do not exist in the native stream yet. Their payload is fixed
here so the emitting package and the projector agree.

- `turn_bot` (W6, journaled at worker start for group turns):
  `{"bot": "<bot profile>", "reason": "<route reason>"}`. `bot_profile` is
  accepted in place of `bot`. Without a bot the frame projects to nothing.
- `step` (W10, preparation and run timing phases):
  `{"name": "<step name>", "status": "started" | "finished"}`, name at most 128
  characters. A repeated start is ignored; a finish without a start becomes a
  started and finished pair, because AG-UI forbids finishing a step that was
  never opened; any other status is ignored. Open steps close before
  `RUN_FINISHED`.

## Replay route

`GET /api/agui/runs/<stream_id>` (dispatched through the Appendix E.1 seam,
catalog class `sessions:read`).

1. The stream id must be a safe id (the run journal's id rules, `.` and `..`
   refused, no further path segments).
2. The request needs an identity with an email.
3. Exactly one journal file may carry the stream id; a missing, ambiguous or
   symlinked one (file or session directory) is refused.
4. The owner session (the journal's directory name) must resolve through
   `get_session`, to a session with that id and a non-empty `owner_email`.
5. The caller must be that owner or a current participant (`participants_of`
   at request time). Administrators get no wider access, and neither does
   project membership.

Every refusal in steps 1 to 5 returns `False`, so the dispatcher answers the
same generic 404 whether or not the stream exists. Only after step 5:

- `409` while the run is live (in `ACTIVE_RUNS` or `STREAMS`);
- `413` when the journal is larger than `HERMES_WEBUI_AGUI_REPLAY_MAX_BYTES`
  (default 32 MiB);
- `422` when a row is malformed, belongs to another session or run, or the
  sequence has a gap;
- `404` for an empty journal;
- otherwise `200`, `Content-Type: text/event-stream; charset=utf-8`,
  `Cache-Control: no-store`, the security headers, any pending auth cookie,
  and the whole projection as `data: {json}` frames with LF line endings and
  a `Content-Length` (sent through the shared plain-body helper `t()`).

A journal without a terminal frame whose worker is gone gets the run
journal's own interruption frame (`stale_interrupted_event`, as the native
replay does), so it ends with `RUN_ERROR {code: "interrupted"}`. The route
never writes to the journal.

## Deviations from the plan table (5.1)

1. **Reasoning is a delta.** The plan describes the native `reasoning` frame
   as cumulative with "delta = new suffix since the last buffer length". Since
   the coalescing change in `api/streaming.py` (#4729) each frame carries only
   the new text and the browser appends it, so the projector passes it on as
   the delta unchanged. Taking suffixes would drop text.
2. **The full reasoning sequence.** AG-UI 1.0 requires a reasoning message
   inside the span, so `REASONING_MESSAGE_START` and `REASONING_MESSAGE_END`
   are emitted besides the `REASONING_START`, `CONTENT` and `END` the table
   names.
3. **`RUN_FINISHED` waits for `stream_end`.** The native stream sends
   `metering` (and possibly title frames) after `done`, and AG-UI allows
   nothing after `RUN_FINISHED` except a late `RUN_ERROR`. So `done` emits the
   snapshot and `RUN_FINISHED` follows at `stream_end`, or at `finish()` when
   the journal has no `stream_end`. A live consumer sees `RUN_FINISHED` when
   the native stream closes, which is when the drain loop ends anyway.
4. **No `usage` on `RUN_FINISHED`.** The table puts usage there. AG-UI defines
   it as the run's own model calls, but the native `done.usage` counts are the
   cached agent's cumulative session counters, not this run's. Reporting them
   as run usage would be wrong, so they go to the state under `/usage` and
   `RUN_FINISHED.usage` stays absent (absent means "not reported"). A native
   per-run usage block would let the projector fill it (request below).
5. **Cancellation and limits.** An `apperror` whose type is `cancelled` is a
   cancelled run. A tool limit stop (`terminal_state: tool_limit_reached`, on
   `done` or on `apperror`) is a stop by a limit the producer enforces, which
   AG-UI 1.0 requires to end with the cancelled outcome; it is preceded by
   `CUSTOM synthpulse.terminal_state` with the reason. Everything open closes
   first, as AG-UI requires before any `RUN_FINISHED`.
6. **`stream_end` without a terminal frame** finishes the run as a success,
   matching the run journal, which records it as completed.
7. **A late failure.** An `apperror` after the run finished becomes one
   `RUN_ERROR` (AG-UI's late failure); after `RUN_ERROR` nothing follows.
8. **`interim_assistant` with `already_streamed`** closes the open text
   message (it marks the end of an assistant segment in the native client)
   instead of being a pure no-op.
9. **`context_status` goes to `/context`**, not `/usage`: it carries the
   prefill context status, not usage.
10. **Tool calls close immediately.** The native `tool` frame carries the
    complete argument snapshot, so `START`, `ARGS` and `END` are emitted
    together; `TEXT_MESSAGE_END` happens at that boundary. A result whose call
    never started in the run opens the call first (without a duration, since
    no start time is known). A result without `tid` is matched to the latest
    unanswered call with the same name, like the native legacy rule.
11. **Subagents.** Announced at the first sighting, including `queued`.
    `name` is the fixed `subagent` (the native frame has no reusable name) and
    `description` the task summary. `parentSubagentRunId` is sent only for a
    parent already announced in the run. A cancelled subagent ends with
    `SUBAGENT_ERROR {code: "cancelled"}` (AG-UI has no cancelled subagent
    outcome); a subagent still active at the run's end is closed with code
    `cancelled` on a cancelled run and `unfinished` otherwise; a frame for an
    id that already finished is ignored (AG-UI forbids reusing it).
12. **Approval and clarify values are allowlisted.** The native approval
    frame carries private mirror tokens and run bookkeeping; only the fields
    in the table above leave. Clarify uses activityType `approval` with
    `kind: "clarify"`, as the table says.
13. **Journal-only frames.** `preparation` and `run_timing` rows (written to
    the journal directly, never to the queue) and frames that are not in the
    table project to nothing. W10 either emits `step` frames for those phases
    or extends this mapping.
14. **Messages snapshot.** Ids follow the transcript position because native
    messages have no stable ids. Reasoning and activity messages are left out
    of the snapshot, so AG-UI consumers keep the ones streamed in the run.
    Tool messages without a `tool_call_id` are skipped (AG-UI requires it),
    as are unknown roles. An assistant message's `bot_profile` becomes its
    `name`. If redaction fails, the snapshot is left out rather than sent
    unredacted.
15. **Access.** "Owner" is the session's `owner_email`, matched against the
    request identity's email; in auth-disabled mode that identity is the
    bootstrap administrator, so a single-user install replays its own runs
    only when sessions carry that owner. Unowned sessions (legacy, cron, CLI)
    are refused, as are administrators who are neither owner nor participant.
16. **Additions not in the table.** `protocolVersion` on `RUN_STARTED`; the
    native `error` frame handled like `apperror`; the text message `name` after
    `turn_bot`.

## Notes for the browser port (W10)

- Feed each fixture row as `feed(row.event, row.payload, seq=row.seq,
  timestamp=row.created_at)` and call `finish(timestamp=<last created_at>)`;
  the result must equal `<case>.agui.json`.
- Tool argument text is compact JSON with sorted keys (`JSON.stringify` with
  a key-sorting replacer), no whitespace.
- `timestamp` is `Math.round(created_at * 1000)`.
- The browser does not redact; the fixtures hold no credential-shaped text,
  so the snapshot is identical.

## Open items

- A per-run usage block in the native `done` payload would let
  `RUN_FINISHED.usage` be filled (deviation 4).
- W6 emits `turn_bot` and W10 emits `step` with the payloads above.
- The live tail (W10) must pass the journal `seq` of each queued frame, so
  its synthetic tool ids equal the replay's.
