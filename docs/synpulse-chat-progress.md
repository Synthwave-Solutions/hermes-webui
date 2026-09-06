# SynPulse chat progress

Structured worker lifecycle events are shown alongside existing tool activity in the
conversation worklog. Each worker has a stable identity and moves from queued to
working to completed, failed, or stopped. The visible text includes a short task
summary; provider reasoning and raw delegation arguments are not part of this event.

The existing assistant-turn Anchor owns rendering and persistence. A per-stream
projector rejects duplicate, stale, malformed, and excess worker events. A late event
from another conversation cannot modify the currently visible turn. Completed worker
rows remain supporting activity, separate from the final assistant answer.

Validation: `./scripts/test.sh tests/test_subagent_progress_ui.py` exercises actual
JavaScript lifecycle behavior. Browser QA must additionally exercise two concurrent
workers, completion/failure, conversation switching, and hard reload against the real
SSE endpoint. The deterministic provider fixture proves application transport and
authorization; it does not measure a production model's latency or competence.
