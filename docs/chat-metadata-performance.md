# Chat metadata scan performance

Opening and polling a session checks its persisted metadata for newer messages
and activity scenes. Long compression summaries can make this prefix hundreds
of kilobytes. The shared scanner now uses the standard library JSON string
scanner instead of collecting each character in a Python list. Nested keys,
escaped quotes, Unicode escapes, and incomplete chunks remain handled.

This changes only the read path for sidebar/session metadata. Files remain the
authority; freshness comparisons, transcript loading, access checks, cache
ownership, and persistence are unchanged. No new cache or dependency is added.

A synthetic 600,078-character prefix containing a nested messages key and a
large escaped Unicode summary took a median 59.5 ms before and 1.8 ms after
(10 scans on the same host). These are scanner timings, not browser load times.

Validation uses `./scripts/test.sh` with `test_metadata_prefix_scanner.py`,
`test_session_cache_ownership.py`, `test_issue4842_cron_projection_perf.py`, and
`test_webui_state_db_reconciliation.py`. The escaped-key regression fails
before the change. Large metadata fixtures verify that nested messages and
escaped structural characters do not truncate metadata or include transcripts.

The neighboring `test_issue5854_anchor_scene_split.py` currently has ten failures
on both the unchanged baseline and this change: this branch lacks the scene
fingerprint/legacy-facts implementation those tests expect. Those pre-existing
failures are not fixed by this scanner optimization.

Activation requires restarting the WebUI process. Check `/health` and observed
session endpoint durations afterwards; measure under representative concurrent
agent activity before drawing conclusions about sustained browser performance.

The selected five-file suite reports 64 passing tests and six pre-existing
failures in `test_webui_state_db_reconciliation.py`; running that file against
the unchanged baseline reproduces the same six failures. They concern missing
state.db prefix-summary optimizations, not JSON string scanning. The fifth file,
`test_shared_conversation_identity.py`, covers the previously committed shared
conversation identity change included in this deployment.
