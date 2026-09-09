# Supplemental frontend stories and evidence boundaries

Review snapshot: 9 September 2026. Source: `work/coverage-webui/tests/e2e/full/supplement-*.spec.ts`, `workspace-default-recovery.spec.ts`, `session-activation-races.spec.ts` `session-draft-restoration.spec.ts`, `kanban-dependency-draft-races.spec.ts`, `stream-reconnect-ownership.spec.ts`, `chat-interrupt-startup.spec.ts`, `kanban-edit-focus-race.spec.ts`, and `cron-skill-picker-race.spec.ts`, paired with the selected `work/coverage-engine` checkout. This is a working acceptance inventory, not a replacement for the 365-story coverage ledger or a certification that every control has been exercised.

The `SUP-*` identifiers below are local review references, not additions to the historical story IDs. Suggested mappings identify only the specific acceptance clauses supported by the assertions. They do **not** upgrade an existing story to PASS. A broad historical story remains partial until its remaining steps, permission negatives, and frozen-run evidence are reconciled.

## Executable source index

Paths below are relative to `work/coverage-webui/tests/e2e/full/`. Narrative numbers locate the acceptance detail; test counts are executable Playwright cases, not action counts.

| Spec | Cases | Local acceptance references |
| --- | ---: | --- |
| `supplement-cli-mcp.spec.ts` | 4 | SUP-01–04 |
| `supplement-mcp-tool-governance.spec.ts` | 2 | SUP-05–06 |
| `supplement-project-knowledge.spec.ts` | 3 | SUP-07–09 |
| `supplement-transcript-files.spec.ts` | 7 | SUP-10–14; SUP-29; SUP-42 |
| `supplement-appearance-rejection.spec.ts` | 1 | SUP-15 |
| `workspace-default-recovery.spec.ts` | 1 | SUP-16 |
| `supplement-clarify-dispatch.spec.ts` | 3 | SUP-17–19; two parameterized clarification branches plus one worker case |
| `supplement-model-routing.spec.ts` | 2 | SUP-20–21 in first test; SUP-28 in second |
| `supplement-cron-advanced.spec.ts` | 4 | SUP-22–25 |
| `supplement-extension-lifecycle.spec.ts` | 2 | SUP-26–27 |
| `session-activation-races.spec.ts` | 4 | SUP-30–33; available/404 restore and current/other sidebar selection |
| `session-draft-restoration.spec.ts` | 1 | SUP-34; intentional empty draft beats late restoration |
| `kanban-dependency-draft-races.spec.ts` | 3 | SUP-35–37; dependency editor ownership |
| `stream-reconnect-ownership.spec.ts` | 1 | SUP-38; stale stream transport recovery |
| `chat-interrupt-startup.spec.ts` | 3 | SUP-39–41; cache initialization, Stop and live-worker lifetime |
| `kanban-edit-focus-race.spec.ts` | 1 | SUP-43; task edit focus and exact field persistence |
| `cron-skill-picker-race.spec.ts` | 1 | SUP-44; old blur ownership and skill selection persistence |

## Common execution boundary

- The normal application frontend, authenticated HTTP handlers, persistence, governance resolver, and engine are used. Browser authentication is seeded with separate signed synthetic identities, not a production SSO login.
- Inference uses a deterministic loopback provider. This proves actual dispatch, request routing, decision plumbing, and side effects. It does not measure a commercial model's intelligence or upstream compatibility.
- MCP tests start an actual local stdio JSON-RPC server with eight synthetic tools. Approved `qa_mark` invocations write a private fixture ledger; terminal tests execute a real harmless `touch` command.
- Tests use a private Hermes/OS home and loopback networking guard. This is not an OS sandbox. No production state, credentials, or external messaging is needed.
- Selected-engine child `PYTHONPATH` starts with the isolation `sitecustomize` directory, then the requested engine and WebUI checkout. The fixture independently spawns a fresh child in the private workspace and checks its imported `kanban_db.py` path and installed guard. This is a child-import regression, distinct from the dispatcher worker's run/claim evidence.
- File creation, role ceilings, existing signed identities, and some session toolset selections are fixture/API setup where explicitly described below. Those operations must not be counted as clicks on the corresponding configuration controls.

## CLI and MCP execution

Source: `supplement-cli-mcp.spec.ts`.

### SUP-01 — Configure command grants and decide real command effects

As a governance administrator, I want an explicitly granted harmless command to wait for a one-action decision, and an explicit deny to block it under a wildcard grant.

Acceptance: enter `touch` in command and approval-command chips; Save and reload; read back exact values. As the governed user, send the tool request through the composer. Before Once/Deny there is no target file and session/permanent buttons are hidden. Once creates the exact empty file; Deny leaves it absent. Change command allowance to `*`, deny `touch`, inspect the preview, and execute again: the engine returns `cli_command_denied` and no file exists.

Scope: initial direct policy/role envelope and session toolsets are API setup; command edits, preview, composer, and decisions are real UI. Real process execution and persisted policy are checked. Because this case also configures manual mode, its approval-command chip alone does not independently demonstrate the automatic-mode review floor; SUP-04 does.

Suggested mappings: parts of `US-SP-GOV-006`, `GOV-011`, `POL-008`, `POL-015`, `POL-016`, `POL-017`. This is an agent tool action, not the embedded terminal-panel journey in `TERM-002`.

### SUP-02 — Search and page an initialized MCP catalog

As an authorized administrator, I want the catalog to show the actual local MCP tools and preserve correct results while searching and paging.

Acceptance: enable the disposable server in System and issue the real `/reload-mcp` chat command. API inventory has exactly eight tools from that server. The UI shows the sorted first five, then remaining three, with correct disabled pager boundaries. Search finds `qa_mark` and its required string marker field; a nonexistent term produces zero rows; page size 10 displays all eight.

Scope: actual MCP initialization, inventory, visible search/page-size/pager controls. This asserts the selected marker field's rendered schema, not byte equality of every complete tool schema. Server is disabled during cleanup.

Suggested mapping: positive clauses of `US-SP-SYS-007` and `SYS-008`. Per-tool denied inventory requires the separate governance/catalog regressions; the positive paging case alone cannot satisfy that negative.

### SUP-03 — Grant a server, then deny execution and catalog disclosure

As a governed user, I want permitted MCP work to require my configured approval, while an explicit server deny blocks both execution and metadata disclosure.

Acceptance: administrator enters the server grant in Users. A composer request parks; Once produces one exact ledger marker and actual tool output. Replace allowance with `*` and deny `qa-stdio`; another request has no ledger effect and returns a refusal. The restricted user's System navigation is hidden, and the separately permitted direct catalog endpoint returns no tools from the denied server.

Scope: broad role and per-server tool map initially seeded by API; server grant/deny are UI edits; actual stdio invocation and user-filtered catalog are real. Hiding navigation is tested separately from server authorization.

Suggested mappings: parts of `US-SP-POL-003`, `POL-008`, `POL-016`, `SYS-007`, `SYS-008`, `GOV-022`.

### SUP-04 — Keep a mandatory CLI review floor under automatic approval

As an administrator, I want selected commands to require a human even when the same user's normal approval flow is automatic.

Acceptance: use Users to set automatic mode with `QA_ALLOW_ONLY` and `approval_commands: [touch]`. An allowed read through the real engine obtains one actual automatic classifier approval and returns the fixture bytes without a manual card. Each subsequent matching `touch` request instead parks with the manual-review explanation, has no file effect, and makes no additional classifier call. Once permits its file; Deny prevents its file. Restore the original user policy.

Scope: initial envelope and read fixture bytes are setup; automatic flow, prompt, command chips, composer, and one-action decisions are real UI. Provider receipts distinguish a working automatic control from the mandatory manual command path. The focused unchanged-source replay passed; exact evidence is recorded at the end. Actual approval POST bodies contain the correct session and nonempty approval ID. This spec waits for New chat to change the URL before binding toolsets, so a prior session cannot be mistaken for the new request.

Suggested mappings: distinct supplement to `US-SP-POL-001`, `POL-015`–`POL-018`, `POL-028`. It is not evidence of real-provider decision quality (`POL-033`).

## MCP tool-rule onboarding

Source: `supplement-mcp-tool-governance.spec.ts`.

### SUP-05 — Create a complete user tool map and enforce local/canonical denial

As a governance administrator, I want to onboard a user entirely through the Users form and restrict individual MCP tools without removing the whole server.

Acceptance: delete the disposable direct user policy; recreate roles, Elevated, Whitelist, Manual, explicit resource grants, server, and `qa_mark` tool rule through visible controls. Save/reload preserves the map. The real user request waits, Once invokes `qa_mark` exactly once. Then replace the allowed tool with `*`, first deny `qa_mark`, then deny `mcp__qa_stdio__qa_mark`; each actual request is refused with no queued approval and no ledger effect.

Scope: authenticated identity and assigned role ceiling are fixture setup; all recreated user grants/denies are UI. Deleting a governance user entry removes a policy override; it does not delete or disable the authenticated account. The test immediately recreates it and does not prove inherited/default access preview after deletion.

Suggested mappings: parts of `US-SP-GOV-002`, `GOV-004`, `GOV-006`, `POL-003`, `POL-008`, `POL-016`. No empty-whitelist or blacklist-mode transition coverage is implied by this configured whitelist case.

### SUP-06 — Edit group tool maps and retain untouched legacy user maps

As an administrator, I want duplicate server rows rejected and untouched legacy maps preserved while editing individual rules.

Acceptance: create a group rule using the UI; a duplicate server row produces validation feedback and no group write. Remove the duplicate, save/reload, inspect the exact map, remove the rule, save, and delete the group. Separately seed a legacy user map containing scalar and array values; open/Save unchanged and compare the entire entry. Edit one visible tool chip; only that map changes and denied tools remain intact.

Scope: group editor is UI; the legacy-shaped user is intentionally seeded through the API. No group runtime invocation is asserted. Group rules support allow maps; this does not invent a group-deny editor/schema.

Suggested mappings: parts of `US-SP-GOV-009`, `GOV-020`, `POL-032`. No template selection (`GOV-008`) or full user-deletion semantics are demonstrated.

## Project and bot knowledge boundaries

Source: `supplement-project-knowledge.spec.ts`.

### SUP-07 — Revoke a project member with retained tabs

As a project owner, I want removing a member to stop file and chat access immediately, including controls already rendered in that member's browser.

Acceptance: create a project, assign Bob and a bot, upload a file, explicitly grant/register/assign the project workspace using administrator controls. Bob downloads exact bytes, starts a project chat, and receives the real engine's synthetic reply. Remove Bob. Existing buttons now reject download, upload, and new-chat requests; retained composer mention preparation and direct start/read reject access. Bob cannot re-add himself. Owner readback contains only the original file and no revoked prompt; project/list/deep-link views hide protected content.

Scope: project/workspace/governance controls and retained-page negatives are UI; direct negative requests independently test backend boundaries. Workspace RBAC and ACL are granted separately from project membership. The test does not inspect an already-open stream after revocation or prove every arbitrary file route. Cleanup restores the remembered workspace and original user policy.

Suggested mappings: concrete clauses of `US-SP-PROJ-004`, `PROJ-005`, `PROJ-006`, `PROJ-008`, `PROJ-009`. `PROJ-009` remains partial for its existing-stream clause unless combined with separate evidence.

### SUP-08 — Search, deselect, and isolate bot document catalogs

As a bot owner, I want document choices to persist only for their bot and foreign IDs to be rejected.

Acceptance: create two bots through the wizard; upload synthetic documents without auto-selecting them; search and clear; select/save/reopen/deselect/save/reopen the first bot. The second bot cannot show the first catalog. A forged foreign selection returns 400 and changes neither catalog nor revision. Bob cannot list the private bots or obtain their document catalogs.

Scope: real upload/catalog/selection persistence and UI. The test does not execute retrieval, ingest/index content, or ask the model to read selected knowledge. The search is performed before selection, so hidden-selection retention during filtering is not independently asserted.

Suggested mappings: parts of `US-SP-KNOW-001`–`KNOW-006`. No runtime read-root (`KNOW-007`) claim, and `KNOW-004` still needs its requested runtime-knowledge check.

### SUP-09 — Reject stale knowledge edits and recover visibly

As a bot owner editing in two tabs, I want a stale save to preserve the newer selection and let me reopen before retrying.

Acceptance: tab A selects the first file and saves. Stale tab B selects the second and receives 409 with explicit reopen instructions; its local choice remains visible while authoritative selection/revision stay at A's result. Cancel/reopen B, change the selection, save once, and verify the final exact selection and incremented revision from A.

Scope: two actual authenticated browser contexts and real optimistic concurrency. This is catalog selection integrity, not a runtime knowledge-permission test.

Suggested mapping: positive/conflict clauses of `US-SP-KNOW-008`; its wider runtime/other-owner negative needs separate evidence.

## Transcript and file views

Source: `supplement-transcript-files.spec.ts`.

### SUP-10 — Navigate complete history with virtualization on and off

As a conversation reader, I want Start, outline, and End to reach the correct persisted turns without duplication.

Acceptance: enable relevant preferences through Settings; import 120 question/answer pairs through the file chooser. Reach first/middle/last exact question with Start/outline/End. Verify virtual spacers and fewer than 120 rendered questions; compare all 240 persisted messages exactly. Reload, disable virtualization through Settings, use outline again, and verify all 120 distinct question IDs without spacers. Another signed user receives 404 without history content.

Scope: imported synthetic conversation, real hydration/history APIs and preference controls; no provider call for imported text.

Suggested mappings: parts of `US-SP-CHAT-016`, `SESS-018`, `PREF-006`, `PREF-021`, `PREF-029`. Import limits/malformed-import and every chat-dispatch permission are outside this case.

### SUP-11 — Preserve CSV and valid/malformed JSON literally

As a file reader, I want quoted delimiters, embedded newlines, Unicode and malformed input handled without data corruption or executing markup.

Acceptance: choose real files in the tree; verify CSV headers/rows, quoted comma/quote/newline content, semicolon and tab forms, BOM/blank-prefix behavior, and literal hostile text without an image node. Valid and malformed JSON render as exact code without executing script content. An unterminated CSV produces a visible parse error and no misleading table. Downloaded bytes remain exact; selected cross-user raw reads return 404.

Scope: file bytes are written by the fixture, not uploaded via UI. Visible selection, preview, clear, and download use the real frontend/backend. Cross-user negatives are tested for comma CSV and both JSON files; the spec does not assert a separate denied read for every delimiter variant.

Suggested mappings: positive/data-integrity clauses of `US-SP-FILE-004` and download clauses of `FILE-010`. Encoded traversal and symlink negatives are separate requirements.

### SUP-12 — Run an HTML artifact in an opaque preview

As a file reader, I want an interactive artifact to run its own script while being unable to read the parent page, cookies, or local storage.

Acceptance: select an HTML fixture; verify exact sandbox flags. Its own script runs, and each attempted parent/cookie/storage read reports BLOCKED. Parent URL/composer remain intact, exact download bytes match, and another user cannot read the artifact via its raw URL.

Scope: inline HTML preview iframe. It does **not** click the separate Open in browser affordance, so `US-SP-FILE-011` is only related sandbox/negative evidence, not a completed positive journey. Also supports a narrow safety clause of `FILE-003`/`CHAT-014` only when their actual rendering surface matches; do not substitute it for Markdown/chat rendering tests.

### SUP-13 — Explicitly render large Markdown without carrying permission to the next file

As a file reader, I want a large file to default to literal text and explicit rendering to apply only to that selected file.

Acceptance: choose a 5,005-line fixture; exact literal fallback and Render anyway appear. Click it, verify first and final content, switch to a small Markdown file, then reopen the large file. Large-file rendering again requires the explicit action. Exact downloads and denied other-user read are checked; disk bytes remain unchanged.

Scope: real preview path; fixture-created files. This tests one configured size threshold and continued navigation, not every resource-exhaustion limit.

Suggested mappings: positive clauses of `US-SP-FILE-005` and exact download clauses of `FILE-010`; broader root/traversal negatives remain separate.

### SUP-14 — Ignore stale full-history responses during a new turn

As a chat user, I want delayed outline/history loading to preserve a newer active turn.

Acceptance: import 40 pairs and capture a genuine full-history HTTP response. Hold only its delivery, send a new slow synthetic-provider request, then release the older response. Truncation/cursor state and the active user turn remain intact; stale outline entries are not applied. The real new reply persists exactly once, the original 80 messages remain exact, and reopening the outline shows 41 questions and reaches the first.

Scope: browser transport timing control around a real backend response; no fabricated history/body. This is one same-conversation stale-response interleaving, not every panel/profile race.

Suggested mappings: parts of `US-SP-CHAT-016` and related resilience in `US-SP-UX-007`; this same-conversation interleaving does not satisfy that story’s cross-panel/profile/conversation navigation steps.

## Preferences and implicit workspace recovery

### SUP-15 — Reject appearance sync without breaking the browser

Source: `supplement-appearance-rejection.spec.ts`.

As a user whose appearance writes are denied, I want my local rendering and draft input to remain usable without claiming that the server accepted a forbidden update.

Acceptance: administrator adds the appearance write-deny through Users. Seed local theme/skin/font values, boot as that user, and observe actual 403 automatic sync requests. HTML attributes retain local rendering; server readback keeps its original skin/font. Typing still works; reload repeats the same denial without uncaught browser errors. Restore policy.

Scope: localStorage is setup, not clicks on every appearance option. This proves error handling and policy refusal, not successful persistence or an exhaustive theme/font sweep.

Suggested mapping: negative/error clauses of `US-SP-PREF-003`, plus resource-denial behavior. No positive full-story upgrade.

### SUP-16 — Recover an implicit remembered workspace without authorizing it explicitly

Source: `workspace-default-recovery.spec.ts`.

As a signed-in user, I want New chat to choose an authorized fallback when a shared profile hint references a revoked or unregistered directory.

Acceptance: setup a private workspace and shared remembered hint through real admin APIs. After membership removal, boot and profile-switch responses omit the forbidden path and choose the allowed workspace. Actual New chat sends that allowed path and persists the correct owner; omitted-workspace API creation also recovers. Explicit forbidden selection remains 403, and admin still sees the original shared hint. A directory removed from the registry but still on disk produces the safe fallback; explicit selection is 400. Restore shared hint/registrations and delete test sessions.

Scope: workspace registration, membership changes, and remembered-state preparation are API setup. Actual boot/New chat and response projection are frontend behavior. The browser switch check targets default; named-target TLS restoration is separately covered by backend tests.

Suggested mappings: narrow recovery/negative evidence related to `US-SP-WS-004`, `WS-007`, `WS-008` and `CHAT-001`. It does not prove the full workspace-picker or actual worker-directory story.

## Clarification and actual board workers

Source: `supplement-clarify-dispatch.spec.ts`.

### SUP-17 — Submit an Other clarification exactly once

As an agent user, I want to collapse a question, supply Other text, and resume only the matching question once.

Acceptance: real engine `clarify` parks on a choice question. Collapse/Expand preserves the input. Choose Other, enter custom text, double-click Submit: one actual response request consumes the first ID. A stale replay returns 409 and cannot consume the second question; another identity returns 403. Enter a free-text follow-up with Enter. Provider phases are exactly 0/1/2 with the exact two answers; persisted final reply survives reload and no question remains pending.

Scope: session toolset activation is API setup; clarification cards and replies are UI; stale/cross-user probes are direct real API negatives. Deterministic provider initiates actual engine tools.

Suggested mapping: a distinct new clarification story. Existing generic duplicate-send and approval stories are not equivalent to the clarification queue.

### SUP-18 — Choose the recommended clarification option then answer free text

As an agent user, I want a choice button to submit its actual answer and the next free-text response to resume the same run correctly.

Acceptance: same real two-question flow and collapse/expand controls as SUP-17; click Alpha (Recommended), verify the recorded answer is `Alpha`, reject stale/foreign replies, submit the second answer with Enter, and compare exact provider phases and persisted answers.

Scope: separate actual choice-click branch; no double-click assertion on this branch. Suggested mapping: distinct clarification acceptance, not another count of every shared collapse/input control.

### SUP-19 — Complete a real worker while mixed bulk edits remain fenced

As a board operator, I want the dispatcher to claim eligible work once and multiple selected manual tasks to report individual outcomes honestly.

Acceptance: create an isolated board and tasks through UI, including an unfinished dependency and one assigned Ready worker. Cancel dispatcher confirmation and verify no run/PID; confirm and verify one spawned worker with positive PID/current run/claim. Running-state mutation is rejected and an unauthorized dispatcher request is 403. Use real Control-or-Command clicks and Control+Enter to toggle two cards; refresh retains selection. Bulk Done updates only the eligible selected card, returns a dependency failure for the other, and shows `1 updated; 1 failed` with its ID. The unselected worker retains its original run and completes through real `kanban_show`/`kanban_complete`; persisted outcome, summary, worker session, events and reload agree.

Scope: genuine spawned engine worker and its own completion token. Completion clears transient worker PID/claim fields; the test matches the original run ID and durable worker session rather than incorrectly requiring the PID to remain after completion. Synthetic provider deliberately delays completion. This is not production cron/gateway drain testing or a multi-tenant stress test.

Suggested mappings: concrete positive/negative clauses of `US-SP-KAN-009`, `KAN-012`, `KAN-015`. Historical board read/tenant-privacy requirements still need their separate evidence.

## Actual main and auxiliary model routing

Source: `supplement-model-routing.spec.ts`. Its first executable test covers SUP-20 and SUP-21; the second covers SUP-28. These acceptance subdivisions are not extra test cases.

### SUP-20 — Route a visible custom conversation model

As a chat user, I want the model selected in the composer to reach the provider and remain specific to that conversation.

Acceptance: create two sessions; use the actual custom-model input for `qa-alternate`; Save, send a unique marker, and verify the provider receives that model. Reload preserves the chip/model/workspace/user turn; the global main assignment and untouched second conversation remain unchanged.

Scope: actual engine/provider HTTP receipt. Only one configured loopback provider is used; this does not test cross-provider failover or a denied model selection. Suggested mapping: positive clauses of `US-SP-CHAT-003`; its permission negatives remain open in this case.

### SUP-21 — Apply and execute a distinct auxiliary title model

As a settings user, I want a saved auxiliary assignment to reach its real task without changing the main chat model.

Acceptance: choose `custom:qa` and a distinct custom `qa-title-alternate` through the auxiliary picker and Apply. Navigate away without a false unsaved warning. Use the actual conversation menu to Regenerate title; provider receipts use the distinct title ID with no offered tools. Read back the title and auxiliary pair while main assignment and conversation model remain unchanged; reload; restore the original auxiliary assignment.

Scope: real UI and auxiliary-provider request. A distinct model differentiates auxiliary routing from fallback to the main default. This is one title task on one synthetic provider, not every auxiliary option/provider or denied assignment. Suggested mapping: positive routing/save clauses of `US-SP-PROV-009`; its non-admin and denied-pair requirements need separate evidence.

### SUP-28 — Save pending auxiliary edits and retain failed or unrelated edits

As a settings user, I want navigation Save to apply pending auxiliary choices, and auxiliary Apply to preserve independent general edits and recoverable failures.

Acceptance: set a pending title model; navigate to Chat; use the unsaved bar’s Save and verify the actual saved auxiliary pair and unchanged main assignment. Edit general max tokens and an auxiliary model; Apply only the auxiliary value. Navigation still requires a decision for the general edit, whose server value is unchanged. Discard it and reopen without the draft value. Choose a new auxiliary value, force a controlled save failure, and verify the error, pending choice, unsaved guard, and previously stored auxiliary assignment remain intact.

Scope: successful saves and persisted readback use real backend APIs. The final failure is deliberately synthesized as HTTP500 with Playwright `route.fulfill`; it proves frontend failure handling, not an actual backend governance denial. Restore the original auxiliary route and remove the transport interception. Suggested mapping: saving/error clauses related to `US-SP-PROV-009`; no positive or negative full-story promotion from this scenario alone.

## Advanced schedules

Source: `supplement-cron-advanced.spec.ts`. Four executable cases have an unchanged-source focused replay. Future-eligibility probes copy persisted jobs and call actual engine logic under a controlled clock; actual Run now cases additionally execute real workers.

### SUP-22 — Preserve a weekly schedule and future eligibility through pause/resume/delete

As a scheduling user, I want Sunday at 13:27 to persist and paused/deleted jobs to be excluded from scheduling.

Acceptance: use the weekly/day/time controls; read back the exact cron expression and future Sunday time; reopen the editor; cancel; pause/reopen/resume/delete through UI. A denied signed identity receives403 for update, run, pause, resume, and delete, with the exact saved job unchanged. Verify genuine engine `get_due_jobs` against a **copy** of each persisted record under a controlled future clock, with the live fixture store byte-identical before/after.

Scope: this copied-record scheduling probe is real engine logic but not a wall-clock ticker firing the live job. Suggested mappings: parts of `US-SP-CRON-003`, `CRON-010`, `CRON-014`, including direct mutation denials. The denied identity does not click a hidden scheduling control, and broader list/history visibility is not asserted here.

### SUP-23 — Validate monthly/custom edits without overwriting the saved schedule

As a scheduling user, I want day 31 and a custom expression to round-trip, while an invalid or canceled edit preserves the prior schedule.

Acceptance: choose monthly day31 at22:41, save/reopen exact values. Submit invalid custom syntax and receive400/visible error with unchanged stored schedule. Save `*/17 8-18 * * 1-5`, reopen, then cancel an `@hourly` edit and verify no change.

Scope: real UI/validation/storage; no live execution or full timezone/DST matrix. Suggested mappings: parts of `US-SP-CRON-003`, `CRON-004`, `CRON-007`, `CRON-008`.

### SUP-24 — Preserve a one-shot deadline and completed history

As a scheduling user, I want the one-shot warning to reflect actual schedule semantics and a name-only edit to leave its deadline unchanged.

Acceptance: custom `2h` has no one-shot warning and persists as a 120-minute interval. Remove it, create `in 2h`, and verify the warning and one-shot future time. Reopen using the exact stored `run_at`, rename and Save: both deadline and next-run time are unchanged. Run now produces one actual history/output record with the synthetic provider result. The job remains stored as completed, disabled, next-run null, repeat count1; copied-store eligibility is empty. Reopen shows existing status label `off`, expand the real output, and verify history count1. Delete the job, then verify a direct Run now is404.

Scope: actual immediate worker execution; no two-hour wall-clock wait. The 404 is after explicit deletion, not a claim that an existing completed job has vanished or is impossible to run manually again. Suggested mappings: concrete clauses of `US-SP-CRON-002`, `CRON-011`, `CRON-012`.

### SUP-25 — Execute the selected Cron bot/model/skill

As a scheduling user, I want the selected profile, model, and skill to affect the real worker, not only the saved form.

Acceptance: fixture-seed same-named skills with different default/target-profile markers. Use profile/model/skill selectors and remove/re-add the skill chip; save/reopen exact values. Run now; verify target skill marker and requested model at the provider, absence of wrong-profile marker, target bot prefix in actual saved output, and the expanded history view. Remove the job and synthetic skill directories.

Scope: skill file creation is fixture setup; selector/Run/history interactions are UI. This is one local profile/model/skill combination, not external delivery or a complete provider matrix. Suggested mapping: positive runtime clauses of `US-SP-CRON-005`, `CRON-011`, `CRON-012`.

## Extension lifecycle and consent

Source: `supplement-extension-lifecycle.spec.ts` and its opt-in `scripts/e2e/extension_fixture.py` transport fixture.

### SUP-26 — Install a checksum-verified extension and deny unauthorized lifecycle calls

As an extension administrator, I want an invalid package checksum to fail cleanly and a valid disposable extension to install through the real gallery path.

Acceptance: activate only the synthetic registry/archive fixture. A bad checksum returns400 and visible SHA256 feedback, leaves no installed directory, and permits retry. Install the valid local package and read its actual manifest/files. For a signed non-admin, Extensions navigation is hidden and seven direct endpoints—status, registry, toggle, consent, uninstall, install, and sidecar—return403. The manifest remains byte-equivalent, installed assets remain, a forbidden install is absent, and the sidecar receives no calls. Cleanup uses the real administrator Uninstall controls.

Scope: gallery entry and ZIP bytes are synthetic local transport data. The ordinary loader, checksum validation, extraction, state, authorization and asset paths are real. This is not vendor TLS/DNS or external download proof; no local-upload control exists or is claimed. Suggested mappings: selected clauses of `US-SP-EXT-004`, `EXT-005`, `EXT-012` plus shared lifecycle negatives. Source-link opening and every declared-permission affordance are not independently asserted.

### SUP-27 — Persist extension settings, isolate storage, and gate a real sidecar by consent

As an extension administrator, I want typed settings, extension-owned storage, explicit sidecar consent and enablement to match the actual loaded runtime.

Acceptance: install two local packages, then reload through the actual Installed control before their runtime appears. Save all five schema types (boolean/string/number/integer/enum), read exact values from the loaded extension and reload. Invalid integer input fails without changing stored settings. Reset returns documented defaults while retaining that extension’s stored data. Clear storage removes only its namespace; peer data survives reload, and these browser values are not written into server settings.

Without consent, a real sidecar call returns403 and produces no sidecar receipt. Open Diagnostics, grant consent, call again and verify200 plus a real receipt showing a valid server token and no forwarded Cookie/Authorization. A forged browser token is replaced by the trusted server credential; only token-file mode0600 is inspected, never its value. Reload, revoke consent and verify another403/no new sidecar call. Disable/reload removes the runtime while the peer remains; enable/reload restores it. Uninstall both, reload and verify runtime removal, absent package directories, asset404 and an empty install manifest.

Scope: real loaded extension API/storage/proxy and loopback HTTP sidecar; synthetic fixture packages and gallery transport. Browser storage isolation is between these two extension namespaces in one browser; it does not assert separate-user storage behavior. The test does not click a distinct Decline-consent action or Copy diagnostics, and uninstall confirmation is not independently asserted. Suggested mappings: concrete clauses of `US-SP-EXT-006`–`EXT-011`, not a blanket PASS. Engine plugins and opaque plugin-page journeys (`EXT-001`–`EXT-003`) remain distinct.

## Navigation ownership and transcript integrity

### SUP-29 — Keep Edit attached to its message after a superseded Start

Source: `supplement-transcript-files.spec.ts`, case `newer manual scroll during history loading keeps correct message Edit indices and earlier persisted turns`.

As a conversation owner, I want a later manual scroll to supersede Start without leaving message actions attached to obsolete transcript indices.

Acceptance: enable virtualization and jump buttons, then import 40 question/answer pairs through the visible JSON chooser. Confirm the initial 30-message tail represents absolute positions 50–79. Hold delivery of the real full-history response started by Start. Use normal wheel gestures to scroll up and return to the bottom; confirm a newer navigation generation and the native viewport position. Release history and edit the visible final question. The actual truncate POST keeps exactly 78 messages; the edited request and deterministic reply produce exactly 80 final messages. The first 78 messages remain exact after the edit and reload.

Scope: transport timing controls delivery of a genuine response; no history is fabricated and no control is force-clicked. The regression checks the destructive server request and persisted bytes, not only the displayed text. It uses manual scrolling, not a click on the End button. The separate real-loader unit requires one ordinary preserving redraw after successful history expansion, with no obsolete Start scroll or queued frame. Different-session, failed-load and active-turn guards remain separate unit/browser assertions.

Suggested mappings: additional clauses of `US-SP-CHAT-016`, `CHAT-020`, and `UX-007`. This case alone does not establish Cancel, Regenerate, cross-user access or every active-stream navigation variant.

### SUP-30 — Prefer New Chat over a delayed available saved-session restore

Source: `session-activation-races.spec.ts`, `available` restore case.

As a signed-in user, I want my explicit New Chat action to win over an older automatic restore.

Acceptance: create a real conversation with a persisted exchange, reload the root page, and hold its actual successful saved-session lookup. Click New Chat, verify one successful creation with a different ID, and type a draft. Release the older response and wait for boot completion. URL, saved session ID, typed draft and accessible current record still identify the newly created administrator-owned conversation; no stale unavailable message appears. Exactly one New Chat record was created by this action.

Scope: the delayed available response is the root restore's saved-session lookup, not a fabricated body. The draft is preserved in the live composer; this case does not submit it or prove its recovery after another reload.

Suggested mappings: parts of `US-SP-CHAT-001`, `CHAT-011`, and `UX-007`; no new complete-story verdict is implied.

### SUP-31 — Prefer New Chat over a delayed forbidden saved-session restore

Source: `session-activation-races.spec.ts`, `inaccessible` restore case.

As a user on a browser with an inaccessible saved conversation ID, I want a new authorized chat to remain usable when the old restore finally returns 404.

Acceptance: first create an administrator-owned conversation with a persisted exchange; then use the separate signed Bob identity and hold the actual 404 session restore. Click New Chat and type a draft. Releasing the old 404 must not clear the new URL or saved ID, replace its view with an unavailable error, or erase the draft. The new record is readable as Bob, owned by Bob, and created exactly once.

Scope: signed synthetic identities are fixture setup; the different-owner 404 comes from the real backend. This checks navigation/error ownership, not an external SSO login or a full cross-user transcript/export permission matrix.

Suggested mappings: parts of `US-SP-CHAT-001`, `CHAT-011`, and `UX-007`.

### SUP-32 — Let reselecting the current chat supersede pending creation

Source: `session-activation-races.spec.ts`, `current` sidebar case.

As a conversation owner, I want reselecting my current conversation to cancel a pending New Chat activation without deleting the record already created on the server.

Acceptance: start from an existing conversation with a real persisted exchange. Hold delivery of a successful New Chat POST after its distinct empty record has been created. The New Chat button is pending/disabled. Click the current conversation's actual sidebar row and type a draft. After release, the same conversation still owns the URL, saved ID, displayed history and draft; New Chat reenables. A direct authorized read confirms the separate created record remains empty and administrator-owned.

Scope: even the normal same-session no-op is a newer activation choice in this race. The case verifies retained server identity and visible state; it does not assert reload recovery, automatic deletion of unused drafts or non-owner access to the created record.

Suggested mappings: parts of `US-SP-CHAT-001`, `CHAT-011`, and `UX-007`.

### SUP-33 — Let another sidebar conversation supersede pending creation

Source: `session-activation-races.spec.ts`, `other` sidebar case.

As a conversation owner, I want opening another existing conversation to retain priority over a delayed New Chat reply.

Acceptance: create two conversations with distinct real persisted exchanges and return to the first. Hold a third successful New Chat creation response. Click the second conversation's sidebar row and type a draft there. Releasing the create response must preserve the second conversation's URL, saved ID, expected transcript marker and draft, and reenable New Chat. The third record remains retrievable, empty and owned by the administrator.

Scope: this covers a real different-session load during pending creation, complementing the same-session path in SUP-32. It does not imply cross-user authority, complete transcript byte comparison or browser-reload draft restoration.

Suggested mappings: parts of `US-SP-CHAT-001`, `CHAT-011`, and `UX-007`.

### SUP-34 — Preserve an intentionally empty draft over late restoration

Source: `session-draft-restoration.spec.ts`, `actual typing and clearing beat late metadata and deliberate prompt reinsertion stays exact`.

As a conversation owner, I want clearing the composer during startup to remain my current draft, even if an older saved draft arrives afterward.

Acceptance: save an exact multiline reusable prompt and verify the real session draft has autosaved. Reload and hold delivery of the actual successful session metadata response containing that old draft. Type replacement text and explicitly clear it; record the two trusted input events. Release metadata and wait for boot completion. The composer remains empty and the same session's persisted draft becomes empty before any saved-prompt insertion. Insert the saved prompt once and verify its exact text and separator. Intentionally insert it again: both copies remain exact, autosave and survive reload.

Scope: this is a real held-response ordering, not an empty fill into an already empty textarea, and it does not deduplicate deliberate user insertion. The companion original saved-prompt lifecycle now verifies autosave and the exact restored draft before clearing it. Separate behavioral units cover untouched restoration, normal cross-session restoration, and avoiding a write into a superseding session. This browser case does not independently prove cross-user draft authority, conversation switching or all send/attachment variants.

Suggested mappings: specific clauses of `US-SP-CHAT-011`, `CHAT-021`, and `UX-007`; broad stories keep their remaining requirements.

### SUP-35 — Preserve dependency re-add input during a live refresh

Source: `kanban-dependency-draft-races.spec.ts`, `a late live refresh preserves re-add input and one exact persisted link`.

As a task editor, I want a background detail refresh to preserve the dependency I am typing.

Acceptance: remove an existing dependency through its visible control. Hold the actual successful detail-log response caused by a real task update/SSE refresh. Type the removed parent's ID before releasing that response. The same editor retains the exact parent text. Add sends one exact parent-child request; authoritative state and reload contain one link and the submitted input is empty.

Scope: board/task creation is private API setup. The transport delay changes delivery order without replacing backend content. This case does not independently assert denied roles, dependency cycles or running-task mutation; those are separate administration cases. Suggested mappings: `US-SP-KAN-011`, `UX-007`.

### SUP-36 — Respect clear and task navigation over older dependency details

Source: `kanban-dependency-draft-races.spec.ts`, `newer clear and task navigation cannot restore or transfer an old draft`.

As a task editor, I want clearing a draft or moving to another task to supersede an older detail response.

Acceptance: hold a genuine refresh, type then explicitly clear the dependency field, and release the response. The field remains empty. During a later held response, use Back and select a different task normally. The older response cannot navigate back or transfer a draft into the new task; both stored dependency sets remain empty.

Scope: this checks current-user task and draft ownership. Cross-user access and alternate board refresh ordering are not implied by these clicks. Suggested mappings: `US-SP-KAN-011`, `UX-007`.

### SUP-37 — Preserve the next dependency while the prior Add finishes

Source: `kanban-dependency-draft-races.spec.ts`, `a delayed successful Add keeps the next edited dependency for its own submission`.

As a task editor, I want to enter a second dependency while the first successful request is finishing without losing the new draft.

Acceptance: hold delivery of a real Add200 after its first link has already persisted. Replace the field with a different parent and then release the old response. The next draft remains; its own normal Add sends that exact parent. Both distinct links persist, and the completed input clears.

Scope: actual backend mutation is retained; the test delays its response only. It does not certify every simultaneous board writer or retry/duplicate-add variant. Suggested mappings: `US-SP-KAN-011`, `UX-007`.

### SUP-38 — Retain a successor stream when an old reconnect completes late

Source: `stream-reconnect-ownership.spec.ts`, `late old reconnect status cannot replace an interrupted successor`.

As a conversation owner, I want an interrupted replacement response to remain visible when older network recovery completes late.

Acceptance: open a real slow turn and deliberately invoke two actual renderer recovery attempts while holding the first real active-status response. Use the normal composer Interrupt command to cancel the old turn and submit a replacement. Hold the replacement transport until the old status is released. No new old-stream request appears; the replacement response appears, is stored exactly once, and survives reload. The original cancelled response has no fabricated completion.

Scope: explicit renderer recovery calls are controlled fault injection, not additional user clicks or simulated provider replies. All HTTP results, cancellation, inference and persisted replies are real inside the private fixture. This is one ordering and does not certify physical network reconnects on every device. Suggested mappings: parts of `US-SP-CHAT-008`, `CHAT-012`, `UX-007`.

### SUP-39 — Recover a cached agent after cancellation during initialization

Source: `chat-interrupt-startup.spec.ts`, `startup interrupt leaves the cached successor able to answer`.

As a conversation owner, I want Interrupt during startup to cancel that request and allow my replacement to execute once.

Acceptance: a private barrier pauses the real agent after cache publication and before stream registration. The normal Interrupt command cancels the original, which never enters the provider. The cached successor enters the engine with no pending interrupt, makes exactly one provider request, and displays and persists its exact reply.

Scope: only scheduling is controlled; engine and provider results are not replaced. This does not assert every startup interleaving or reload recovery. Suggested mapping: `US-SP-CHAT-008`.

### SUP-40 — Honor Stop even after cancellation metadata is removed

Source: `chat-interrupt-startup.spec.ts`, `Stop during cached initialization prevents provider admission and permits a later turn`.

As a conversation owner, I want Stop during cached-agent initialization to remain effective throughout startup.

Acceptance: warm the real cache, hold its runtime refresh, click Stop and await the genuine successful cancellation response. Release the refresh after the cancel-map entry is absent. The stopped request makes no provider call or engine conversation entry. A later normal send enters un-interrupted once and persists its exact reply.

Scope: this proves retained request cancellation through a controlled initialization boundary. The private barrier is not an alternate cancellation implementation. Suggested mapping: `US-SP-CHAT-009`.

### SUP-41 — Keep a cancelled worker's interrupt until its actual lifetime ends

Source: `chat-interrupt-startup.spec.ts`, `an aged cancelled worker retains its interrupt until its held reply settles`.

As a conversation owner, I want an old cancelled worker to remain stopped while a replacement waits for the session.

Acceptance: hold an actual provider response that would request a file write. Interrupt through the normal composer, and age only the advisory registry timestamp in the private fixture. The successor start returns409 while the old worker remains alive; its interrupt is not reset and no file exists. Release the old reply: it still observes its interrupt and leaves the file absent. The queued successor then appears once with one persisted user and assistant turn.

Scope: this tests worker lifetime independently of an advisory timestamp, without waiting180 seconds or replacing provider output. It does not prove process-crash recovery or OS confinement. Suggested mappings: `US-SP-CHAT-008`, `CHAT-009`.

### SUP-42 — Keep Start ahead of a delayed terminal dock follow

Source: `supplement-transcript-files.spec.ts`, `delayed terminal dock follow cannot override newer Start navigation`.

As a conversation reader, I want Start to remain at the beginning when an earlier terminal close finishes adjusting the layout.

Acceptance: import 120 question/answer pairs through the visible JSON chooser with virtualization and navigation controls enabled. Open the actual disposable terminal, wait for its real xterm surface, and close it normally while at the transcript tail. Hold only the actual dock-layout animation callback, identified by its scheduling stack. Click Start normally and reach the first message, then release the older callback. The first message remains in the viewport and the scroll-write observations contain no stale return to the tail. Continue through the middle outline entry and End; all 240 persisted messages remain exact. After reload, disable virtualization and reach the first message again with 120 unique question IDs and no spacers. Another signed user receives 404 without transcript content.

Scope: callback timing is controlled; terminal rendering, close controls, import, transcript rendering and backend responses are real. This is a separate case from the unchanged normal Start/outline/End journey in SUP-10. The controlled browser race covers the terminal dock only. Eight executable backend cases cover the shared guard across terminal, handoff, approval and clarification callback families; they are not four browser race journeys. No shell command execution, live service or exhaustive layout ordering is inferred.

The delayed-outline test also uses function predicates for polling under the existing CSP. That preserves the exact loading-state assertion without enabling `unsafe-eval`, changing an application permission or creating a new browser scenario.

Suggested mappings: concrete clauses of `US-SP-CHAT-016`, `PREF-006`, `PREF-021`, `PREF-029`, `TERM-002`, `UX-007`. These do not promote an entire terminal story based on opening and closing the surface.

### SUP-43 — Keep priority typing in the selected task field

Source: `kanban-edit-focus-race.spec.ts`, `delayed initial focus cannot redirect priority typing into the saved title`.

As a board user editing a task, I want a delayed initial focus callback to respect the field I selected and preserve my title.

Acceptance: seed a disposable board and unassigned Todo through the real API. Open its actual Edit modal, change title and body, clear priority and confirm that priority has focus. Release only any actual 50ms callback scheduled by `openKanbanEdit`, then type `2` through the browser keyboard and Save. The real PATCH succeeds with the exact edited title/body and priority2; authoritative readback also retains Todo and no assignee. The preview shows the edited title. Reload, reopen Edit and verify the exact title and priority2 again.

Scope: the timing adapter changes delivery of the existing callback only; it does not fabricate DOM values or server responses. Fixed source schedules no delayed initial-focus timer. Board/task creation is API setup, not tested creation clicks. This case does not cover every editable field, Cancel, focus trapping or denied-role edits. The unchanged full lifecycle case separately exercises comment/completion/archive/restore. Neither it nor this controlled focus case belongs to the unchanged historical Linux21 selection.

Suggested mapping: concrete edit/save/reopen clauses of `US-SP-KAN-004`; no complete-story status promotion from this case alone.

### SUP-44 — Keep a reopened skill query ahead of an old blur callback

Source: `cron-skill-picker-race.spec.ts`, `an old blur cannot close a reopened query and a current outside click still closes it`.

As a scheduling user, I want to remove and re-add a skill without an earlier blur hiding my current search results.

Acceptance: create a private synthetic skill file as fixture setup, open the actual New job form and select its visible option. Remove the selected chip, reopen the same query, then release the held actual 150ms `search.onblur` callback. The matching option remains available for a normal click. Remove/search again, click another field, and release the pending callbacks; the current outside blur closes the dropdown. Refocus the unchanged query, select the option, and Save through the UI. The real create response and authoritative job readback retain exactly one skill. Reload, reopen Edit and verify that the saved chip remains and the skill control is disabled.

Scope: timing interception holds only the real blur callback, identified by its scheduling stack, and explicitly runs already-queued callbacks even if canceled. It does not replace DOM state, HTTP responses or actionability checks. Four behavior tests additionally cover input/refocus, successive blur identities, selection removal, rebinding, disposal and replaced nodes. This new browser case does not run a worker, choose a model/profile or assert a denied identity. Those claims remain with the separate unchanged advanced Cron execution case. Suggested mapping: selection/save/reopen clauses of `US-SP-CRON-005` only; no whole-story promotion.

Evidence: controlled old-source replay `cron-picker-before/20260909-175013-91756000` failed on the hidden second option. Final focused replay `cron-picker-final/20260909-175517-145534000` passed this case and all four unchanged advanced Cron cases with five empty browser-error collections and unchanged source. These focused results do not relabel the earlier full234 result of233 passes/1 failure or qualify a new full235 release. The separate work receipt is `cron-skill-picker-regression-evidence.json`.

## Governance contract and changes relevant to these supplements

The global policy must be `enforce`. Explicit managed **whitelist** means no work capability until directly granted within the assigned role/resource ceiling; own identity/recovery/request status remain available. **Blacklist** exposes the assigned ceiling except retained explicit denies; it does not mean every host/admin capability. User, Elevated, and Admin levels constrain that ceiling; bootstrap recovery owners are a separate exception. The configured whitelist cases above do not re-test every mode transition or the empty-whitelist condition.

Hard deny is evaluated before either human or AI action review and again after waiting. AI does not add grants, remove deny entries, or grant new capability requests. The normal manual flow and automatic decision flow remain independent of access mode. Existing policy/role tests and the earlier full-suite action cases cover those broader combinations; they must remain linked separately.

The supplemental engine change makes `cli.approval_commands` a mandatory **current-policy manual requirement**, not a command grant. A matching otherwise-permitted terminal invocation cannot be automatically approved, satisfied by session/permanent/YOLO allowances, or relieved by placing the same selector under deny.approval_commands. Explicit execution deny still wins. Command matching preserves comment/newline and heredoc boundaries; unsupported compound/control-flow syntax requires manual review when only a review floor is present, and is denied under finite command allowances or retained hard command denies. This is not a complete shell parser or a sandbox for arbitrary interpreters. Backend tests in `coverage-engine/tests/test_governance_cli_approval_commands.py` cover the policy/continuation/parser boundaries; SUP-04 separately covers the actual browser floor.

MCP execution now normalizes local, native canonical (`mcp__<sanitized-server>__<tool>`), and legacy names against the **trusted registered server toolset**. A local `qa_mark` deny must therefore block canonical `mcp__qa_stdio__qa_mark` under wildcard grants, matching catalog filtering. User-filtered inventories are not cached as a shared identity result. Notes operations also map to concrete search/read tool permission; those API negatives are separate backend tests and not implied by clicking the generic MCP catalog.

## Evidence status and final reconciliation

**Final frozen run `20260909-184341-281192000` passed all 235 browser scenarios once, with zero skips, retries, flaky outcomes, report-level errors or uncaught browser errors in 235 collections.** The unchanged source pair is WebUI `90cc10318788db857464663b1874d28eb1e50430` and engine `b0aaa74f9dcfe9e7caa4692656b4535ce04104e1`. Seventeen reporter bookkeeping warning entries remain recorded separately. The final source/provenance and executed-scenario files bind every title to this single run.

The current source inventory contains **43 supplemental executable cases across seventeen files**, described by 44 acceptance narratives because one model-routing case checks both conversation routing and auxiliary execution. These are included within the 235-case full run, not additional runs to sum. The separate 365-story ledger contains **23 PASS, 220 PARTIAL and 122 NOT RUN**. Raw inventory records **1,265 controls, 623 interacted with and 642 without interaction evidence**; no all-click claim follows.

The same source pair separately passed the unchanged historical 21-case Linux selection in replay v5, run `20260909-184734-991570225`, with one attempt per case, no report/browser errors, and verified owned-process/cgroup/listener cleanup. This selection includes the original long-history and fork journeys but excludes advanced Cron, the new Cron picker and the task-edit focus regression. It is not a full 235-case Linux pass. Earlier Mac and Linux failures, including the rejected 232/233/234 attempts and the old 224-case Linux attempt, remain intact in [review history](review-history.json).

The prior Mac225 pass at 7b2620b3 remains a separate historical result. Later dependency, reconnect, cached-worker, dock, task-focus and Cron-picker regressions are now part of the new single frozen full run. The CSP function-predicate and finer fork text polling changes are harness corrections; they do not relabel failed attempts. In the old Linux fork failure, the first correct recorded DOM snapshot was 55 ms after timeout, with an approximately one-second unsampled interval after the last failed poll. First actual DOM appearance is unknown. The corrected case correlates accepted requests and samples every 100 ms with the same ten-second text assertion budget; exact prefix, child continuation and parent privacy assertions remain.

The following scoped manifests and Playwright results were read directly. Every listed case is `expected`, `test_exit_code:0`, `source_unchanged_during_run:true`, and its `uncaught-browser-errors` attachment decodes to an empty array:

| Reviewed scope | Cases | Run directory under `work/supplement-runs/` |
| --- | ---: | --- |
| Clarification and real Kanban worker (SUP-17/18/19) | 3 | `clarify-dispatch/20260909-095047-148379000` |
| New mandatory CLI floor with automatic control (SUP-04) | 1 | `cli-floor/20260909-100932-319673000` |
| Main/auxiliary routing and independent save state (SUP-20/21/28) | 2 | `20260909-100027-873897000` |
| Advanced Cron (SUP-22/23/24/25) | 4 | `cron-advanced/20260909-100739-489646000` |
| Extension lifecycle (SUP-26/27) | 2 | `20260909-100700-236084000` |
| Draft ordering (SUP-34), saved-prompt lifecycle, and four activation neighbors | 6 | `draft-restore/20260909-123200-306176000` |

These are scoped verification snapshots, **not one combined final fingerprint**. For example, the CLI-floor run used WebUI HEAD `7e749c70b8b44293a3073809ae1db470cfbc69a8` plus source digest `3f45e2530138cabaf7be216a5f5cae31e6829302c5a2d07d2088cabe26717361`, paired with engine `b0aaa74f9dcfe9e7caa4692656b4535ce04104e1`. Subsequent source edits, including warning translations, are covered by the later integrated run named above; this historical scoped receipt keeps its original source. The clarification snapshot’s WebUI source digest is `61c6612c7cc344d5db370a4656150510f1f34e2bb260f4c6a6c8b5704cbf95d0` with the same engine head.

Historical manifests also show expected outcomes for earlier CLI/MCP, project/knowledge, transcript/file, appearance and tool-map supplements, but several record source drift. Test exit0 alone does not qualify those as a frozen release replay; the runner intentionally fails overall on drift. Workspace recovery has an unchanged scoped run at `20260909-094706-99781000`. The separate immutable 224-case Linux attempt at WebUI `530710751934b36f0105313aae75e368b1817583` had 203 passes and 21 failures. Its failures remain separately qualified; a targeted Linux replay is distinct from this passing full Mac run. No integrated verdict is derived by summing focused snapshots. Exact outcomes and tested source fingerprints must be read from the authoritative execution summary and provenance.

Final reconciliation uses the selected source fingerprint, exact executable titles, passed assertions and recorded click targets. Repeated dynamic user/group rows remain separate raw observations; they neither create additional semantic journeys nor turn an unclicked affordance into a pass. Historical counts and statuses remain unchanged.

The late-Start browser regression first reproduced an actual truncate request of 28 instead of 78, leaving 30 persisted messages instead of 80; the corrected focused replay preserved the exact 78-message prefix and all 80 final messages. Its ten passing transcript/preference cases included an unrelated new-spec addition during the run, so that replay is behavioral evidence rather than the final frozen release. The four session-activation cases have a separate unchanged-source replay. Neither snapshot is summed into an integrated result. The later six-case draft-restoration snapshot likewise does not relabel the immutable 530 source attempt. The historical full225 and the new full235 each separately pass the exact navigation, Edit-index, activation and draft-restoration assertions at their own recorded source.
