# SynPulse release QA, 6 September 2026

Runtime acceptance was executed against WebUI 045ba4b3 and the isolated upgraded engine.
The following test-only commits do not alter that runtime: 1994f374 and 8ecbab7a.
Group chat passed two users/two bots and outsider denial. Project QA passed upload/download,
actual relative read_file execution, membership revocation, persistence and 390px mobile layout.
Delegation passed two real workers, six queued/running/completed SSE events, exactly two
persisted completed Anchor rows, visible activity and reload. Cancellation preserved the last
observed running state instead of inventing worker completion. Focused UI contract tests passed
9/9; the optional engine capability suite passed 3/3 with the upgraded engine installed.

## Full CI limitation: pre-existing collection errors

The GitHub matrix for PR 2 at 1994f374 could not collect the whole suite. All ten errors below
were independently reproduced on a fresh detached baseline checkout at 4d39eeac, before this
feature branch. No tests or workflows were disabled to hide these failures.

| Test module | Missing implementation export |
| --- | --- |
| test_atomic_settings_writes.py | api.config._atomic_write_settings_text |
| test_auto_compression_card.py | api.streaming._POST_COMPRESSION_TOOL_RESULT_SUMMARY_FLAG |
| test_cli_sessions_cache_cap.py | api.models._CLI_SESSIONS_CACHE_MAX_ENTRIES |
| test_context_history_sanitization.py | api.streaming._compact_image_parts_for_persistence |
| test_context_message_stable_ids.py | api.streaming._assign_stable_message_ids |
| test_cors_preflight_allowlist.py | api.routes.apply_cors_preflight_headers |
| test_gateway_read_idle_timeout.py | api.gateway_chat._GATEWAY_READ_TIMEOUT_DEFAULT |
| test_issue3929_process_wakeup_pause.py | api.models.PROCESS_WAKEUP_PAUSE_ERROR |
| test_session_msg_limit_ceiling.py | api.routes._MAX_MSG_LIMIT |
| test_state_db_backstop_boundary_gate.py | api.routes._STATE_DB_DISPLAY_ROW_BACKSTOP |

CI evidence: https://github.com/Synthwave-Solutions/hermes-webui/actions/runs/34032627992
(job 101484939419). Baseline collection reproduced ten errors in 4.16 seconds.
VPS evidence: /tmp/webui-ci-baseline-collection.log; isolated checkout:
/home/synthwavehq/work/codex-20260906-webui-ci-baseline.

The missing-engine integration test explicitly skips when the optional upgraded engine is not
installed; standalone UI projection and missing-capability behavior remain tested. This is distinct
from the ten pre-existing collection errors above, which remain visible and unresolved.


## Informational terminal-error browser gate

The informational terminal-error scenario also timed out waiting for terminal settlement after
15 seconds. The exact same failure was reproduced with the unchanged browser gate on baseline
4d39eeac: live reasoning and completed tool rendered, then the terminal settlement wait timed out.
This is a pre-existing terminal-error lifecycle limitation, not a passing check and not established
as a new regression. The normal and historical-transcript CI browser scenarios passed.

CI evidence: https://github.com/Synthwave-Solutions/hermes-webui/actions/runs/34032627979
(job 101484896319). Baseline command: LIFECYCLE_SCENARIO=terminal-error python
tests/browser_conversation_lifecycle.py in the baseline checkout, using an isolated browser-test
venv. VPS artifacts: /home/synthwavehq/work/webui-ci-terminal-error-baseline;
log: /tmp/webui-ci-terminal-error-baseline.log.
