# PERF_REPORT_DOM: message-list DOM thrash removal (branch perf/dom-recycle)

## What the render path actually does today

All findings below are from `static/ui.js` on this branch (the July 2026 line
numbers 13101-13112 / 12964-13224 are long stale; current landmarks are given
by function name).

### The three interesting events

1. **Session switch** goes through `renderMessages()` (~line 15710). A revisit
   to a recently viewed, settled session is served by the
   `_sessionHtmlCache` fast path near the top of `renderMessages` (guarded by
   `sid!==_sessionHtmlCacheSid`, message count, window key and
   `_messageRenderCacheSignature()`): one `innerHTML` assignment from cache,
   then rehydration (`_rehydrateTransparentStreamDom`,
   `_rehydrateDeferredWorklogsFromCache`). A first visit takes the full build.
   Either way a full build for a NEW session is unavoidable and fine.

2. **A new message / turn settle / tool completion** calls
   `renderMessages({preserveScroll:true})`. This is where the thrash lived:
   the function does `inner.innerHTML=''` (the wipe, currently just after the
   `_preWipeNearTail` capture) and then rebuilds EVERY row of the transcript
   as fresh elements, even though only the tail changed. Every user bubble,
   every settled assistant turn, every wakeup card: new nodes, new innerHTML
   parses, every render.

3. **Each streaming chunk** does NOT go through `renderMessages`. Live deltas
   are written by the smd parser in `static/messages.js` directly into the
   `#liveAssistantTurn` node, and live tool cards go into the live worklog.
   However, mid-stream events (tool completion, activity refresh, clarify
   echo, CLI-import refresh) do trigger full `renderMessages` rebuilds, so the
   wipe-and-rebuild cost is paid repeatedly during a busy turn as well.

### The virtualization angle (the old finding)

Transcript virtualization is opt-in and default OFF (`_virtualizeTranscript`,
boot apply around line 833; CHANGELOG confirms opt-in default retained, #6318,
#4325). The virtual-window boundary wipe the July research flagged was already
fixed upstream by #4346/#4793: `_scheduleMessageVirtualizedRender()` arms
`_msgNodeRecycleEnabled=true` (with a `finally` clear) around its
`renderMessages` call, and `renderMessages` stashes existing keyed nodes
(`_recycleStash`, keys `data-recycle-key` for assistant turns and
`data-msg-idx` for user/wakeup rows) BEFORE the wipe and reuses them in the
render loop.

So the real remaining win, exactly as the task brief suspected, was in the
DEFAULT non-virtualized path: the recycle machinery existed but was never
armed there. Every in-session re-render was still a full wipe plus fresh
rebuild of all rows.

## What changed (surgical, one file: static/ui.js)

A new module flag `_msgNodeRecycleSameSession` (declared next to
`_msgNodeRecycleEnabled`) arms the EXISTING #4346 recycle machinery for any
same-session re-render:

- In `renderMessages`, just before `_recycleStash.clear()`, the flag is
  computed as: `sid` is truthy AND `sid===_sessionHtmlCacheSid` (the session
  whose rows currently occupy the DOM; assigned at the end of every render)
  AND no native scrollbar drag is active (`_scrollbarDragActive`, typeof
  guarded for the node test harnesses).
- The stash-fill gate and the three recycle lookups (process-wakeup row, user
  row, assistant-turn shell) now read
  `_msgNodeRecycleEnabled||_msgNodeRecycleSameSession`.
- The flag is cleared right after the render loop consumes the stash, so the
  arm is render-local and can never leak into another render or another
  session. The virtual-scroll path still owns `_msgNodeRecycleEnabled` with
  its unchanged true/finally-false lifecycle.

Effect per event:

- **New message / settle / tool completion**: unchanged user rows and wakeup
  cards keep their existing DOM nodes untouched (the recycle branch skips the
  `innerHTML` write when `dataset.rawText` and the built HTML match), and
  settled assistant turns reuse their shell node. Only changed and new rows
  produce fresh DOM work.
- **Session switch**: `sid!==_sessionHtmlCacheSid` at that moment, so the
  fresh-build (or cache fast path) is taken exactly as before. Zero change.
- **Streaming chunks**: untouched (parser path). Mid-stream `renderMessages`
  calls now recycle the settled rows above the live turn instead of
  recreating them.

Keying: rows are keyed by `rawIdx` (index into `S.messages`), the same stable
identity the existing machinery, `data-msg-idx` consumers and
`static/assistant_turn_anchors.js` (`raw_idx` in the anchor key) already use.
When an in-session mutation shifts content under a key (edit, undo,
compression), the content-equality check inside the recycle branch forces a
rebuild of that row, so reuse can never show stale content.

## Why streaming, anchors and settled scenes stay intact

- **Live turn**: the stash-fill explicitly skips `#liveAssistantTurn` (and any
  container holding it), so the live parser target is never handed out as a
  recycled shell. The #3877 `_preservedLiveTurn` capture/reattach logic
  (segment-level swap, structural-count guard) is untouched and still runs
  after the rebuild.
- **Tool cards / worklogs / thinking cards**: recycled assistant turns get
  `blocks.innerHTML=''` plus `_recycleResetAttrs` cleanup before refill, and
  the settled worklog rebuild pass (the big `querySelectorAll(...).remove()`
  then rebuild, gated on `!S.busy || S.toolCalls.length`) runs identically.
  The turn content is byte-identical to a fresh build; only the outer node
  identity is preserved. This is the exact behavior the opt-in virtualized
  path has shipped with since #4346/#4793.
- **Settled scenes**: `_hydrateIdLinkedHistoricalToolScenes`,
  `_assistantTurnAnchorSettledFinalAnswer` and the anchor-owned scene
  rendering operate on `S.messages` data before and during the loop; nothing
  in that pipeline reads recycled-node state, and the anchor ownership tests
  (`tests/test_anchor_fallback_ownership.py`, which execute the real
  `renderMessages` end to end) pass unchanged.
- **Scroll logic**: the wipe still happens (recycled nodes are re-appended in
  order), so `_preWipeNearTail`, `_rememberRenderedUserRowIntrinsicHeights`,
  the `_programmaticScroll` latch, `_scrollAfterMessageRender` and the
  `queueMicrotask` re-anchor all behave exactly as before. Recycled user rows
  additionally keep their painted `content-visibility` state, which if
  anything reduces the #5744 collapse class.
- **Session HTML cache**: unchanged; it serializes whatever is in the DOM at
  render end, and recycled rows serialize identically.

## Residual risks

- The user-row skip relies on `row.innerHTML===nextRowHtml` after browser
  serialization. Where serialization normalizes (entities, Prism-highlighted
  code blocks mutated post-render), the compare fails and the row is rebuilt;
  that is today's behavior, so the failure mode is "no win for that row",
  never stale content.
- Recycling is now active during busy/streaming re-renders in the default
  path, a combination the virtualized opt-in path exercises but default users
  have not. The live turn exclusion plus the content-equality rebuilds bound
  the blast radius; still, this is the one genuinely new state combination.
- Assistant turn INNER content is still rebuilt every render (blocks wipe).
  Skipping unchanged settled turns entirely would be the next win but touches
  the worklog/settled-scene rebuild pass, so it was deliberately left out.
- If a future change makes `renderMessages` throw between arm and the
  post-loop clear, the flag stays true until the next render recomputes it
  unconditionally; because it is recomputed (not OR-ed) each render and only
  read inside the loop, a stale value cannot alter behavior.

## How to verify live

1. Open a session with a long transcript (30+ messages), virtualization OFF
   (default). Open devtools, Elements panel, expand `#msgInner`.
2. Right-click an old user bubble's `div.msg-row` and "Store as global
   variable" (`temp1`). Send a new message and let the reply settle.
3. Before this change: `temp1.isConnected` becomes `false` after every render
   (node replaced). After this change: `temp1.isConnected` stays `true` and
   the element does not flash in the Elements panel; only the new tail rows
   light up as inserted.
4. Performance panel: record while sending a message in a long session. The
   "Recalculate style / Layout" work attributed to `renderMessages` drops
   sharply, and the DOM node churn (nodes created per render) shrinks from
   "entire transcript" to "changed tail rows".
5. Regression sweep by hand: mid-stream tool completions keep the streamed
   text visible (no blank/reappear), collapsing and expanding a settled
   worklog survives a new message, scroll position holds when re-rendered
   while scrolled up, and switching sessions still lands instantly (cache) or
   fully fresh, with `temp1.isConnected===false` after a switch, proving no
   cross-session reuse.

## Verification performed here

- `node --check static/ui.js`: pass. `npm run lint:runtime` equivalent
  (eslint runtime guard on static/ui.js): clean.
- Targeted pytest (repo venv, this worktree): 361 passed across
  test_issue4346_vscroll_footer_jitter, test_issue4793_dom_recycle_hardening,
  test_anchor_fallback_ownership, test_process_wakeup_rendering,
  test_issue5744/5638 user-row height, test_pinned_tail_midstream_jitter,
  test_issue500_message_list_virtualization, test_ui_tool_call_cleanup,
  test_issue1690_scroll_completion, test_5552_viewport_anchor_surrogate,
  test_issue4970, test_issue2613, test_issue3870, test_wipe_rows0,
  test_sse_recovery_scroll_stranding, test_issue6220,
  test_stable_assistant_turn_anchor_registry, test_issue4295,
  test_issue4856, test_live_to_final_anchor_visible_order, test_issue5367,
  test_issue5224.
- 3 failures, all PRE-EXISTING on the pristine tree (verified via git stash):
  two i18n locale-catalog checks (tool_action_label / process_wakeup_label
  missing from static/i18n.js locales) and one collection ImportError in
  test_auto_compression_card.py (api/streaming.py lacks
  _POST_COMPRESSION_TOOL_RESULT_SUMMARY_FLAG). None touch this diff.
- Behavioral smoke test of the arm condition executed from the real source:
  same-session arms, cross-session and null sid do not, scrollbar drag
  disarms, missing `_scrollbarDragActive` stub does not throw.
