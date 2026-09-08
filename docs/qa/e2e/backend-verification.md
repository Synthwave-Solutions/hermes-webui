# Backend verification handoff

Recorded 8 September 2026. These are bounded local verification results for the paired SynthPulse WebUI and Hermes Agent candidate. They do not certify global CI, every frontend feature, production deployment, or external-provider quality. Counts overlap and must not be added together.

## Source state

The tested engine commit remains `77ce302a209a586096d0c52336f42f357722f3e0`. The joint backend verification snapshot is WebUI `f117dc1241e3ee8cd67e9254a841ebf6bf7a5e43`; the latest runtime candidate is WebUI `820b4a8eecb2a223a8c133358e1dad7a10830211`. That later candidate leaves the API/engine implementation unchanged and adds local terminal assets with exact integrity checks, documentation and two E2E specification fixes. Its five added asset tests passed separately, as recorded below. The continuation, realtime voice and workspace changes are committed. The final frozen-source browser run `20260908-222640-169443000` completed with **174 passed and two known failures across 176 scenarios**. All 176 application page-error collections were empty. Nine Playwright fixture-bookkeeping warnings are preserved in the QA review notes; the report contained no global error records. See the [execution summary](execution-summary.json) and [source manifest](evidence/source-provenance.json) for the tested runtime and delivered documentation commits.

Local repositories:

- Engine: `/Users/michaelramirez/Documents/Codex/2026-09-08/do-x20/work/hermes-agent`
- WebUI: `/Users/michaelramirez/Documents/Codex/2026-09-08/do-x20/work/hermes-webui`

Both repositories must be installed together. The engine has one unrelated case-colliding contributor-file change, `contributors/emails/agent@Agents-Mac-mini.local`; it is excluded from feature ownership and staging.

## Reproduce the engine checks

The prepared WebUI `.venv` uses Python 3.12 and has the engine installed from the adjacent checkout. From the engine repository:

```sh
cd /Users/michaelramirez/Documents/Codex/2026-09-08/do-x20/work/hermes-agent
HERMES_PYTHON=../hermes-webui/.venv/bin/python scripts/run_tests.sh \
  tests/hermes_cli/test_dashboard_governance_*.py \
  tests/hermes_cli/test_project_file_scope.py \
  tests/hermes_cli/test_grant_operation_provenance.py \
  tests/hermes_cli/test_bot_access_ceiling.py \
  tests/test_governance*.py \
  tests/run_agent/test_dashboard_governance_model_runtime.py \
  tests/tools/test_async_delegation*.py -q
```

Final root verification on engine `77ce302a2`, after the workspace lock and last bot-revocation fix: **286 passed, 0 failed across 20 files in 11.2 seconds**. The canonical runner isolates each test file and sets its documented clean environment. Its local log is `work/final-engine-checks.log`; raw logs are not included in this public handoff.

This final result supersedes the earlier 280-test checkpoint and the 27-test workspace-lock follow-up. To focus only on retained continuation and live revocation:

```sh
../hermes-webui/.venv/bin/python -m pytest \
  tests/test_governance_continuation_context.py -q
```

That file now contains **33 cases**, including six added bot-revocation cases. Its earlier 27-case checkpoint passed in 1.12 seconds; the final 286-test canonical result includes all 33. These cover original role/deny/model/file/bot ceilings, current denials, malformed or mismatched identity/profile snapshots, nested continuations, original usage caps and environment/DWD identity, actual tool dispatch rejection, workspace relocation/revocation, callback-free serialized contexts and inactive-governance compatibility. False, missing or failing managed-bot callbacks are rejected before an actual primary provider-request entry. `git diff --check` passed.

## Reproduce the final joint WebUI checks

On WebUI `f117dc12`, the following 21-file check produced **319 passed in 17.89 seconds**. Its local log is `work/final-webui-checks.log`.

```sh
cd /Users/michaelramirez/Documents/Codex/2026-09-08/do-x20/work/hermes-webui
HERMES_WEBUI_TEST_PYTHON=/Users/michaelramirez/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  ./scripts/test.sh \
  tests/test_session_delegation_status.py \
  tests/test_session_progress.py \
  tests/test_session_ops.py \
  tests/test_realtime_voice.py \
  tests/test_realtime_voice_runtime.py \
  tests/test_realtime_voice_tls.py \
  tests/test_realtime_voice_frontend.py \
  tests/test_requester_grant_ingestion.py \
  tests/test_dashboard_plugin_asset_auth.py \
  tests/test_plugin_page_runtime.py \
  tests/test_e2e_isolation.py \
  tests/test_continuation_authority.py \
  tests/test_governance_agent_context.py \
  tests/test_workspace_acl_ceiling.py \
  tests/test_workspace_ownership.py \
  tests/test_personal_file_guard.py \
  tests/test_governance_resource_scope.py \
  tests/test_workspace_upload.py \
  tests/test_upload_request_visibility.py \
  tests/test_tool_failure_reporting.py \
  tests/test_issue6220_id_linked_tool_anchor_hydration.py -q
```

A separate non-overlapping check produced **9 passed in 2.18 seconds**:

```sh
HERMES_WEBUI_TEST_PYTHON=/Users/michaelramirez/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  ./scripts/test.sh \
  tests/test_tool_call_persistence.py \
  tests/test_live_tool_callback_events.py -q
```

On the later WebUI candidate `820b4a8e`, the new terminal-asset check produced **5 passed in 1.27 seconds**:

```sh
HERMES_WEBUI_TEST_PYTHON=/Users/michaelramirez/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  ./scripts/test.sh tests/test_xterm_vendored_assets.py -q
node --check static/terminal.js
.venv/bin/python -m ruff check tests/test_xterm_vendored_assets.py
```

The JavaScript syntax and new-test Ruff checks also passed. The five tests compare checked-in asset bytes with the existing SHA384 pins and check licensing/provenance plus base-relative loader paths. They do not replace an actual browser terminal-initialization test, and are distinct from the earlier backend snapshot.

Across the named snapshots, these disjoint WebUI checks cover **333 unique Python test cases** across 24 paths: 319 + 9 + 5. This is not a claim that all 333 were rerun together on the latest commit. The 51 voice/TLS cases below are already part of the 319. Node cases run inside the frontend wrapper are not added to these totals. The backend set covers current policy and workspace ownership, parked-action revocation, safe continuation identity/storage, delegation completion status, plugin authorization, isolated fixtures, uploads, and accurate persistence/rendering of tool failures.

## Focus only on realtime voice and TLS

Use the supported Python selection described in WebUI `TESTING.md` and run:

```sh
cd /Users/michaelramirez/Documents/Codex/2026-09-08/do-x20/work/hermes-webui
HERMES_WEBUI_TEST_PYTHON=/Users/michaelramirez/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  ./scripts/test.sh \
  tests/test_realtime_voice.py \
  tests/test_realtime_voice_runtime.py \
  tests/test_realtime_voice_tls.py \
  tests/test_realtime_voice_frontend.py -q
```

This **51-case** subset previously passed independently and is included in the final joint WebUI check above. It contains 13 negotiation/route cases, 35 controller/bridge cases, two real TLS cases and one Python wrapper that runs the Node frontend lifecycle suite. Inner Node cases are not additional independent Python test executions.

Scope: native function-call dispatch and deduplication, concurrent work, continued conversation after ordinary tool denial, deferred audio notifications, current actor/child visibility, private transcript persistence, expiry/teardown, pending delegation status, CSRF and model checks. TLS tests use an actual local HTTPS listener and certificate verification: the configured leaf pin succeeds without a loopback-name SAN; a different pin fails before authentication or work content is sent. Synthetic protocol tests do not establish real microphone acoustics, WebRTC media quality, provider entitlement or production credentials. Actual browser/HTTP/engine evidence is reported separately by the E2E package.

## Committed files in this backend handoff

Engine modified files:

```text
agent/agent_init.py
agent/chat_completion_helpers.py
hermes_cli/dashboard_governance/action_approval.py
hermes_cli/dashboard_governance/context.py
hermes_cli/dashboard_governance/model_policy.py
hermes_cli/dashboard_governance/tool_policy.py
hermes_cli/dashboard_governance/usage.py
model_tools.py
tests/hermes_cli/test_grant_operation_provenance.py
tests/hermes_cli/test_project_file_scope.py
tools/async_delegation.py
tools/environments/local.py
tools/file_tools.py
```

Engine new files:

```text
tests/test_governance_continuation_context.py
tests/tools/test_async_delegation_continuation_ref.py
tests/tools/test_async_delegation_pending.py
```

WebUI voice backend owned in this handoff: modified `api/realtime_voice.py`, `tests/test_realtime_voice.py`, `docs/realtime-voice.md`, `requirements.txt`; new `api/realtime_voice_runtime.py`, `tests/test_realtime_voice_runtime.py`, `tests/test_realtime_voice_tls.py`.

Coordinated host integration also modifies `api/routes.py`, `api/streaming.py`, `api/background_process.py`, `api/session_ops.py`, `api/governance/agent_context.py`, and adds `api/governance/continuation.py`, `api/workspace_access.py`, `tests/test_continuation_authority.py`, `tests/test_session_delegation_status.py`, `tests/test_workspace_acl_ceiling.py`. These changes are in the paired WebUI candidate and covered by its named joint checks. The complete release manifest, rather than this backend scope list, inventories frontend, fixture and unrelated feature-QA changes.

## Baseline failures and compatibility limits

- Global repository CI is not green. The earlier complete WebUI governance/bot/file check produced 381 passes and the unchanged `tests/test_governance_catalog.py::test_route_catalog_maps_core_endpoint_families` failure: `/api/memory` maps to `chat:use`, while that old test expects `memory:read`. Clean-baseline comparisons also reproduced collection and gateway/locale failures. These historical failures are separate from the passing suites above; their current full-repository status is not recertified here.
- A separate earlier root approval/auth/settings comparison had eight failures and 228 passes on the candidate versus 18 failures and 215 passes on its clean baseline, with no candidate-only failure. Those overlapping historical counts are context, not a global-green claim or the final voice/workspace result.
- Explicit whitelist grants start empty; blacklist subtracts denials within the role ceiling. Untouched legacy controls keep previous behavior. Global `enforce` activates policy blocking; bootstrap recovery owners remain the documented exception.
- Continuations keep the initiating identity and original **hard permission ceiling**. The current administrator-authored manual/automatic mode and prompt govern eligible action review. Unknown, malformed or unavailable AI decisions fall back to manual review; approval cannot grant a missing capability or override a hard denial.
- Original external SSO group claims are retained without a fresh IdP lookup. Current local policy and membership are checked on resumed turns. Live workspace and managed-bot callbacks run before tools and primary model requests; primary model permissions use the bound turn envelope plus retained original ceilings, not a fresh external model-policy load before every token request. Tool action review does reload authoritative policy.
- Original actor/profile/workspace bindings cannot silently relocate a job. Private authority references survive delayed-job recovery; missing authority fails closed. Records are created lazily for actual jobs and retained with the durable job lifecycle, not given a blanket expiry that invalidates legitimate delayed work. Storage is capped at 10,000 authority records; a full store rejects new captures without invalidating existing delayed jobs.
- Normal in-process delegated agents inherit live callbacks. External-process contexts cannot serialize callback capabilities and remain blocked until a trusted host rebinds them.
- Explicit managed file/environment denials also block unrestricted terminal/code and repository-wide Git access that could evade them. Otherwise, explicitly granted elevated host execution remains host privilege. No OS sandbox is claimed.

No secrets, raw logs, authentication state, browser traces or private continuation records are included in this handoff. Production has not been changed by these local verification commands.
