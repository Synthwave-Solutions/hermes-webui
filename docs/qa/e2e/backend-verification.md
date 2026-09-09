# Backend verification handoff

Recorded 9 September 2026. These are canonical focused local checks for the paired SynthPulse release. The WebUI and engine totals describe different repositories; earlier overlapping checkpoints are superseded and are not added to these counts. This is not a certification of global CI, all frontend features, production deployment or external-provider quality.

## Source state

The verified WebUI code commit is `704d5737da750931eba0b2ef5aa5d3e9a6e75677` and the verified engine code commit is `49bf59875c41e84baf5ac53bd1194859d54be94d`. The frozen-source browser run `20260908-234115-847878000` used that same pair and passed **187 of 187 scenarios**, with **0 failed**. All 187 application page-error collections were empty; the report recorded zero global errors. The 11 Playwright fixture-bookkeeping warning entries remain in [review notes](../synthpulse-e2e/run-review-notes.json), separately from application errors and scenario results.

The [execution summary](../synthpulse-e2e/execution-summary.json) and [source manifest](../synthpulse-source/manifest.json) bind these results to the tested code and any later documentation-only delivered commits. The control inventory remains incomplete: 508 of 1052 entries were interacted with in passing tests, leaving 544 without that evidence.

Both repositories must be installed together. The engine's unrelated case-colliding contributor-file change is excluded from the committed release patches. Production deployment is user-authorized and pending a separately verified live result.

## Reproduce the WebUI checks

The canonical `./scripts/test.sh` bundle passed **439 tests, 0 failed across 32 files** at `704d5737da750931eba0b2ef5aa5d3e9a6e75677`. The exact file list below is taken from `work/release-backend-verification.json`; its local log is `work/release-webui-checks.log`. Raw logs are not included in this handoff.

Use the prepared Python 3.12 environment with the matching engine installed from the adjacent checkout. Run from the WebUI repository; the runner keeps its documented test isolation. The Python paths below are relative to those paired checkouts.

```sh
HERMES_WEBUI_TEST_PYTHON=.venv/bin/python ./scripts/test.sh \
  tests/test_continuation_authority.py \
  tests/test_dashboard_plugin_asset_auth.py \
  tests/test_e2e_isolation.py \
  tests/test_governance_agent_context.py \
  tests/test_governance_catalog_coverage.py \
  tests/test_governance_resource_scope.py \
  tests/test_issue1823_kanban_not_found.py \
  tests/test_issue6174_public_share_media_embed.py \
  tests/test_issue6220_id_linked_tool_anchor_hydration.py \
  tests/test_kanban_bridge.py \
  tests/test_kanban_manual_completion.py \
  tests/test_live_tool_callback_events.py \
  tests/test_personal_file_guard.py \
  tests/test_plugin_page_runtime.py \
  tests/test_public_share_security.py \
  tests/test_realtime_voice.py \
  tests/test_realtime_voice_frontend.py \
  tests/test_realtime_voice_runtime.py \
  tests/test_realtime_voice_tls.py \
  tests/test_requester_grant_ingestion.py \
  tests/test_session_delegation_status.py \
  tests/test_session_ops.py \
  tests/test_session_progress.py \
  tests/test_session_public_share.py \
  tests/test_session_public_share_static.py \
  tests/test_tool_call_persistence.py \
  tests/test_tool_failure_reporting.py \
  tests/test_upload_request_visibility.py \
  tests/test_workspace_acl_ceiling.py \
  tests/test_workspace_ownership.py \
  tests/test_workspace_upload.py \
  tests/test_xterm_vendored_assets.py -q
```

## Reproduce the engine checks

The canonical `scripts/run_tests.sh` bundle passed **357 tests, 0 failed across 29 files** at `49bf59875c41e84baf5ac53bd1194859d54be94d`. The exact file list below is taken from `work/release-backend-verification.json`; its local log is `work/release-engine-checks.log`. Raw logs are not included in this handoff.

Use the prepared Python 3.12 environment with the matching engine installed from the adjacent checkout. Run from the engine repository; the runner keeps its documented test isolation. The Python paths below are relative to those paired checkouts.

```sh
HERMES_PYTHON=../hermes-webui/.venv/bin/python scripts/run_tests.sh \
  tests/hermes_cli/test_bot_access_ceiling.py \
  tests/hermes_cli/test_dashboard_governance_audit.py \
  tests/hermes_cli/test_dashboard_governance_cli.py \
  tests/hermes_cli/test_dashboard_governance_deny.py \
  tests/hermes_cli/test_dashboard_governance_enforcement.py \
  tests/hermes_cli/test_dashboard_governance_loader.py \
  tests/hermes_cli/test_dashboard_governance_resolver.py \
  tests/hermes_cli/test_dashboard_governance_route_catalog.py \
  tests/hermes_cli/test_dashboard_governance_usage.py \
  tests/hermes_cli/test_dashboard_governance_web.py \
  tests/hermes_cli/test_grant_operation_provenance.py \
  tests/hermes_cli/test_kanban_block_kinds.py \
  tests/hermes_cli/test_kanban_blocked_sticky.py \
  tests/hermes_cli/test_kanban_lifecycle_hooks.py \
  tests/hermes_cli/test_kanban_manual_pending_completion.py \
  tests/hermes_cli/test_kanban_manual_todo_block.py \
  tests/hermes_cli/test_kanban_parent_reopen_invalidation.py \
  tests/hermes_cli/test_kanban_review_lifecycle.py \
  tests/hermes_cli/test_kanban_review_lifecycle_complete.py \
  tests/hermes_cli/test_kanban_task_updated_hook.py \
  tests/hermes_cli/test_project_file_scope.py \
  tests/run_agent/test_dashboard_governance_model_runtime.py \
  tests/test_governance_continuation_context.py \
  tests/test_governance_per_user_actions.py \
  tests/test_governance_tool_runtime.py \
  tests/tools/test_async_delegation.py \
  tests/tools/test_async_delegation_continuation_ref.py \
  tests/tools/test_async_delegation_fd_leak.py \
  tests/tools/test_async_delegation_pending.py -q
```

## What the focused bundles verify

The WebUI bundle covers session and delegation lifecycle, exact durable continuation authority, current workspace ownership and permission ceilings, parked-action revocation, file and upload authorization, plugin rendering/authentication, isolated fixtures, realtime voice protocol/TLS behavior, accurate tool-failure persistence, terminal asset integrity, and public Share lifecycle/privacy. Share checks include owner and CSRF boundaries, stale/foreign token rejection, snapshot refresh/revocation, and fail-closed publication when source metadata cannot be saved.

The engine bundle covers per-user whitelist/blacklist resolution, explicit denials, model/tool/file/environment/usage boundaries, trusted delegation and continuation ceilings, authoritative runtime rechecks, audit provenance and manual/automatic action review. Its Kanban regression files additionally exercise explicitly opted-in manual Todo/Triage completion and Todo blocking, dependency validation, audit/reason retention, recurrence escalation, parent lifecycle effects and unchanged worker run fencing.

These backend checks complement the actual Chromium scenarios; source assertions alone do not prove frontend behavior. The 187-scenario browser run exercises public Share create/refresh/revoke, direct manual completion, Todo→Blocked→Unblock persistence, denied task mutation, parent dependencies, repeated-block escalation, named board administration and dry-run dispatcher preview. It does not launch a production Kanban worker.

Realtime voice tests use actual local HTTP/WebSocket/HTTPS and engine routes with synthetic media and a deterministic local provider. Certificate pinning is checked against an actual local TLS listener. They do not establish physical microphone acoustics, real WebRTC negotiation, external-provider quality or production credentials. Virtual WebAuthn tests likewise do not certify a physical authenticator.

## Baseline failures and compatibility limits

- Global repository CI is not certified green. The earlier complete WebUI governance/bot/file check produced 381 passes and the unchanged `tests/test_governance_catalog.py::test_route_catalog_maps_core_endpoint_families` failure: `/api/memory` maps to `chat:use`, while that old test expects `memory:read`. Clean-baseline comparisons also reproduced collection and gateway/locale failures. These historical failures are separate from the passing suites above; their current full-repository status is not recertified here.
- A separate earlier root approval/auth/settings comparison had eight failures and 228 passes on the candidate versus 18 failures and 215 passes on its clean baseline, with no candidate-only failure. Those overlapping historical counts are context, not a global-green claim or the final voice/workspace result.
- Explicit whitelist grants start empty; blacklist subtracts denials within the role ceiling. Untouched legacy controls keep previous behavior. Global `enforce` activates policy blocking; bootstrap recovery owners remain the documented exception.
- Continuations keep the initiating identity and original **hard permission ceiling**. The current administrator-authored manual/automatic mode and prompt govern eligible action review. Unknown, malformed or unavailable AI decisions fall back to manual review; approval cannot grant a missing capability or override a hard denial.
- Original external SSO group claims are retained without a fresh IdP lookup. Current local policy and membership are checked on resumed turns. Live workspace and managed-bot callbacks run before tools and primary model requests; primary model permissions use the bound turn envelope plus retained original ceilings, not a fresh external model-policy load before every token request. Tool action review does reload authoritative policy.
- Original actor/profile/workspace bindings cannot silently relocate a job. Private authority references survive delayed-job recovery; missing authority fails closed. Records are created lazily for actual jobs and retained with the durable job lifecycle, not given a blanket expiry that invalidates legitimate delayed work. Storage is capped at 10,000 authority records; a full store rejects new captures without invalidating existing delayed jobs.
- Normal in-process delegated agents inherit live callbacks. External-process contexts cannot serialize callback capabilities and remain blocked until a trusted host rebinds them.
- Explicit managed file/environment denials also block unrestricted terminal/code and repository-wide Git access that could evade them. Otherwise, explicitly granted elevated host execution remains host privilege. No OS sandbox is claimed.

No secrets, raw logs, authentication state, browser traces or private continuation records are included in this handoff. These local verification commands are separate from the user-authorized production deployment, whose live verification result is pending.
