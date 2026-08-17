# Scene cache: instant warm session switching (perf/scene-cache)

Goal: switching back to a recently viewed chat renders instantly (previously ~270ms
for the metadata + messages round-trips), with stale-while-revalidate correctness.

## What changed (files and functions)

### static/sessions.js
- Scene cache helpers (top of file, previously committed as unused scaffolding, now
  completed and wired):
  - `_captureActiveSessionScene()`: snapshots the outgoing conversation
    (metadata clone, `S.messages`, `S.toolCalls`, truncation cursor `_oldestIdx` /
    `_messagesTruncated`, scroll position and pin state, revision signal). Refuses
    to capture live/pending sessions (`S.busy`, `S.activeStreamId`, `INFLIGHT[sid]`,
    `active_stream_id`, `pending_user_message`) and half-loaded transcripts
    (`message_count > 0` while `S.messages` is empty).
  - `_restoreSessionScene(scene)`: repopulates `S.messages` / `S.toolCalls` /
    cursors / scroll-pin state and returns a metadata-only stand-in for the
    metadata payload (no duplicate transcript array on `S.session`). Returns null
    for scenes whose metadata carries a live/pending turn.
  - `_putSessionSceneCache` / `_getSessionSceneCache` / `_invalidateSessionSceneCache`:
    bounded LRU. 15 entries, 32MB byte budget (both bounds enforced on every put;
    reads reinsert at the LRU tail). `_clearSessionSceneCache()` empties it.
  - `_validateCachedSessionScene(sid, scene)`: the background revalidation. One
    `messages=0` metadata request; compares revision (`revision` ||
    `updated_at` || `last_message_at`), `message_count`, remote live/pending
    state, and a normalized composer-draft signature. On mismatch it invalidates
    the entry and forces `loadSession(sid, {force:true, keepStaleUntilLoaded:true})`
    (single-frame swap, no blank gap). If the warm load still owns
    `_loadingSessionId` when the response lands, the reload retries briefly
    (150ms x 20) instead of silently dropping the refresh.
- `loadSession(sid)`:
  - Force reloads (`opts.force`) invalidate the sid's scene up front.
  - On switch-away (after the awaited draft flush and its stale guard, so the
    scene carries the just-persisted `composer_draft`): `_captureActiveSessionScene()`.
  - Warm path: before the Phase 1 metadata fetch, an eligible cached scene
    (`!forceReload`, no `INFLIGHT[sid]`, metadata idle) is restored synchronously,
    `data` is synthesized from the scene metadata, the normal render flow
    continues with zero blocking network, and `_validateCachedSessionScene` is
    fired in the background. Cache miss: behavior unchanged (metadata fetch, then
    `_ensureMessagesLoaded`'s messages fetch).
  - After render: unpinned scenes get their scroll offset restored.
  - All scene calls inside `loadSession` are typeof-guarded so the
    extracted-function Node test harnesses keep running the cold path.
- `_saveComposerDraftNow`: unchanged payloads now return `Promise.resolve(false)`
  so the pre-switch `await` costs one microtask instead of a POST (this was the
  remaining blocking await on the warm path when the draft did not change).
- `_switchProfileForSessionLoad`: clears the whole scene cache after a
  successful profile switch.
- `ensureSessionEventsSSE` `sessions_changed` handler: invalidates the changed
  `payload.session_id` before profile filtering.
- `startGatewaySSE` `sessions_changed` handler: invalidates every changed sid in
  `data.sessions`.
- `deleteSession` and the bulk-delete path: invalidate the deleted sids.

### static/messages.js
- `attachLiveStream`: invalidates the sid's scene (covers every user-initiated
  send, reconnect, and server-initiated turn attach).
- `_handleBgTaskCompleteEvent`: invalidates after the dedupe check.
- Per-session SSE `session-updated` handler: invalidates the target sid.
- Per-session SSE `server_turn_started` handler: invalidates the target sid.

### static/panels.js
- `switchToProfile`: clears the scene cache right after the switch POST succeeds.

### static/ui.js
- `queueSessionMessage`: invalidates the target sid (queued messages become the
  session's next turn).

### tests/test_issue_new_chat_draft_restore.py
- One stale assertion updated: it pinned the old
  `!_composerDraftKnownPayloadSessions.has(sid)` check that the committed
  signature-based `_saveComposerDraftNow` (already on this branch) had replaced.
  It was red at HEAD; it now asserts the signature-compare skip.

## Cache design

- In-memory per tab (`Map` in sessions.js module scope), never persisted.
- Key: session_id. Entries are deep clones (structuredClone with JSON fallback),
  so later mutation of `S.session` / `S.messages` cannot corrupt a scene.
- LRU: Map insertion order; reads reinsert at the tail; eviction pops the head.
  Bounds: 15 entries AND 32MB estimated bytes.
- Version signal per scene: `revision` (server field when present, else
  `updated_at` / `last_message_at`) plus `message_count`, checked by the
  background validator on every warm hit, together with remote live/pending
  state and the composer-draft signature.
- Capture point: switch-away only (the freshest possible snapshot, including
  any SSE-applied updates while viewing).

## Warm switch flow

1. Click session B while B has a cached scene: `loadSession` restores the scene
   synchronously; there is no macrotask between the transcript clear and
   `renderMessages`, so the "Loading conversation..." placeholder never paints
   and the swap is effectively instant.
2. `_validateCachedSessionScene` runs in the background (one ~1KB metadata
   request). Match: nothing happens. Mismatch: entry dropped +
   `loadSession(force, keepStaleUntilLoaded)` swaps in the fresh transcript in
   one frame.
3. The deferred model resolver (`_resolveSessionModelForDisplaySoon`) still runs
   as before; it never blocked first paint.

## Invalidation paths (complete list)

| Trigger | Where |
|---|---|
| Local send / any live stream attach | `attachLiveStream` (messages.js) |
| Queued message for any session | `queueSessionMessage` (ui.js) |
| Server-initiated turn starts | `server_turn_started` SSE handler (messages.js) |
| Turn finished during SSE gap | `session-updated` SSE handler (messages.js) |
| Background task completion | `_handleBgTaskCompleteEvent` (messages.js) |
| Any sidebar-visible session change | `sessions_changed` on `/api/sessions/events` and on the gateway stream (sessions.js) |
| Any force reload of a session | top of `loadSession` (covers edits, self-heal, compression, external refresh) |
| Session delete (single + bulk) | `deleteSession` / bulk path (sessions.js) |
| Profile switch | `switchToProfile` (panels.js) + `_switchProfileForSessionLoad` (sessions.js): full cache clear |
| Validator mismatch | `_validateCachedSessionScene` |

Streaming/pending sessions are additionally never captured in the first place.

## Known-red tests (intentional, pre-existing)

`tests/test_session_scene_cache.py` (committed earlier on this branch, all 6 red
at HEAD) encodes a larger phase-2 design. Four of six now pass. The two still red
directly contradict currently green tests, so they were left out of scope:

- `test_cold_switch_uses_one_metadata_plus_messages_request` wants the cold
  switch collapsed into a single `messages=1` request and `messages=0` removed
  from `loadSession`. That conflicts with
  `test_bg_task_complete_loadsession_stream_restart` (anchors on the
  `messages=0` fetch inside `loadSession`) and the executable harness in
  `test_cross_session_message_load_isolation` (asserts the exact two-request
  sequence). The task brief also specifies "cache miss keeps current behavior".
- `test_draft_switch_waits_only_when_payload_changed` wants a
  `const draftSave = ... / if (draftSave) await draftSave;` shape; that
  conflicts with `test_issue2543_named_context_session_switch` and
  `test_issue_new_chat_draft_restore`, which pin
  `await _saveComposerDraftNow(currentSid`. The actual perf goal (no POST on an
  unchanged draft) is delivered via the `Promise.resolve(false)` fast path.

Also pre-existing red at HEAD and untouched:
`test_session_switch_performance.py::test_compression_continuation_fallback_reads_only_file_head`
and `test_api_timeout.py::test_api_has_default_timeout_and_per_call_override_contract`.

## Residual risks

- Split-view panes (`window.__HERMES_PANE_MODE`) do not hold the sidebar SSE, so
  their invalidation relies on the per-session SSE handlers plus the background
  validator. Worst case a pane paints a stale scene for one validator round-trip
  (~100-300ms) before the keepStale swap corrects it.
- The revision signal depends on server `updated_at` / `last_message_at`
  moving on every transcript change. Metadata-only changes that do not bump
  those fields (for example a rename) can leave a scene's title stale until the
  next cold load; the transcript itself is covered by `message_count`.
- The validator adds one background `messages=0` request per warm switch. Net
  traffic still drops (the blocking messages fetch disappears from the hot
  path) but it is not zero.
- Scroll restore for unpinned scenes is a single assignment after render; late
  layout shifts (image loads) can still nudge the position slightly.
- Byte accounting uses a JSON size estimate; scenes with non-JSON-serializable
  fields fall back to a length heuristic. Bounds still hold.

## How to verify live

1. Open the WebUI, click chat A, then chat B, then A again. The second visit to
   A must paint instantly (no "Loading conversation..." flash). In DevTools
   Network you should see no blocking `/api/session?...messages=1` for the warm
   switch, only a background `messages=0` validation request.
2. Correctness: in chat A ask something, wait for the reply, switch to B, use
   another client (CLI/phone) to add a message to A, switch back to A. The old
   scene may paint for a moment, then the transcript updates in place within a
   validator round-trip (no blank gap).
3. Streaming: start a long turn in A, switch to B and back mid-stream. The live
   turn must reattach exactly as before (scenes are never captured or served
   while a stream or pending message exists).
4. Draft: type in A without sending, switch to B and back. The draft must
   reappear; switching must feel instant when the draft was already saved.
5. Profile switch: switch profiles and open a chat with the same position in the
   list; it must cold-load (cache cleared).

## Verification performed

- `node --check` on static/sessions.js, static/messages.js, static/ui.js,
  static/panels.js: all pass.
- Targeted pytest (13 session/loadSession-related files, 118 tests): all pass
  except the pre-existing/intentional reds listed above.
- Node smoke harness (extracted functions, outside the repo): cold load A ->
  switch to B (capture) -> warm switch to A with zero blocking calls ->
  matching validation keeps the scene -> simulated server-side append ->
  warm paint + validator invalidates + keepStale reload swaps in the new
  transcript. Also exercised LRU bound (15) and full clear.
