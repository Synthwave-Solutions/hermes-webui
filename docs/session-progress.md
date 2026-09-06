# Conversation progress

The conversation status row reads `/api/session/status` and remains visible
after a turn ends. It refreshes every five seconds, so background completion
appears when that conversation is opened without replacing the active pane.

The status is a projection of existing state, not a second job registry:

- **Queued:** a pending server start newer than the journal's latest run.
- **Working:** a stream/worker registered in this process.
- **Waiting for input:** that live run has an approval or clarification pending,
  or its authoritative outcome is a tool limit requiring intervention.
- **Completed:** an authoritative `done` event in the durable run journal.
- **Failed:** an error/crash outcome or a journal whose worker disappeared.
- **Canceled:** an authoritative user interruption.

Transport closure alone does not establish completion. A late title/transport
write to an older run does not replace the latest started run. Unknown history
without journal evidence has no synthesized completion status. The browser's
unsent follow-up queue keeps its existing cards and local persistence; this
change does not move unsubmitted messages to the server.

The read-only projection uses existing session authorization. Journal summaries
retain authoritative terminal-event identity across reload and service restart.
No messages, timestamps, or terminal outcomes are rewritten by this projection.

Validation: `./scripts/test.sh -q tests/test_session_progress.py
tests/test_session_ops.py tests/test_run_journal.py
tests/test_queued_message_durability.py`. Browser QA should verify a live run,
an approval wait, completion, failure, cancellation, refresh, and switching away
while an earlier status response is still pending. A request failure displays
status unavailable rather than leaving a stale success message.
