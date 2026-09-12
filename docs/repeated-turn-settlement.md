# Repeated conversation turns

SynthPulse must preserve two separately submitted user turns even when their
prompts and assistant answers are identical. A successful second answer must
settle normally and survive reload in both the visible transcript and model
context.

The result's known previous-context prefix establishes the historical boundary.
Within the remaining suffix, the last exact current-user match anchors the
current exchange. Replay cleanup still removes overlapping historical material
before that exchange. Content deduplication inside model context is scoped to
each user turn; adjacent duplicate user checkpoints and repeated tool-call rows
within a turn remain deduplicated. Compression references remain globally
deduplicated.

This corrects the older context tests that treated identical exchanges, or the
same answer to different questions, as one global content identity. The state
layers changed are transcript settlement and next-turn model context, following
the current-turn ownership and replay invariants in the
[run-state contract](rfcs/webui-run-state-consistency-contract.md).

An old-only result with no new exchange still cannot satisfy a pending turn.
Explicit failed/partial results keep their terminal error path even if text was
streamed. The change does not retry provider calls, execute tools again, or
change permissions. It does not diagnose delays between the last text token and
the provider's terminal response.

Verification uses the real streaming worker with an isolated synthetic agent:
stream a repeated answer, return a healthy append-only result, assert `done`
without `apperror`, and reload both U/A/U/A sequences. Its explicit-failure
counterpart must emit `apperror` without `done`, with exactly one agent run.
Helper cases cover repeated turns, leading historical replay, workspace-tagged
prompts, checkpoint duplicates, and distinct tool-call IDs. Provider behavior
and rendered browser acceptance are separate release checks.
