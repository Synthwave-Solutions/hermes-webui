# SynthPulse remaining frontend QA priorities

The acceptance catalog now contains **365 stable stories**, including 16 precise realtime voice stories discovered during implementation. The authoritative full-suite run is `20260909-080212-676633000`; its final counts and source fingerprints are in [execution-summary.json](evidence/execution-summary.json). Use the [story matrix](coverage-plan.csv) for exact assertions and gaps; a passing browser scenario is not certification of an entire historical story or every click.

The current control inventory contains **1,053 source/runtime entries: 514 recorded interactions in passing tests and 539 without such interaction evidence**. Entries include wrappers and repeated states; this is not a count of distinct fully verified user operations. The selected run has 192 browser scenarios and 192 primary uncaught-browser-error collections with 0 errors. 13 recorded fixture bookkeeping log entries remain documented separately in [run-review-notes.json](evidence/run-review-notes.json).

The earlier `20260908-202702-435893000` run is historical behavior evidence only. It ran 139 cases with 137 passes and two failures, and found 937 inventory entries with 366 interactions. Its fixture isolation claim was rejected after provider discovery could access host Copilot authentication. Those counts must not be reused as the next candidate's QA verdict. Current runs use private OS HOME/config/PATH plus browser and Python loopback network guards.

Subsequent actual local browser coverage includes all 14 additional grant/deny fields, legacy metadata preservation, group/user/capability administration, whitelist/blacklist and level revocation, requester pending/approved/rejected status, model/settings/skill direct-denial probes, settings behavior, eight System/Plugins/provider workflows, and owner/member workspace assignment. The workspace cases verify retained file/session/terminal denial and a real write blocked after membership is removed while human approval is pending. The realtime cases exercise actual voice HTTP handlers, local sideband WebSockets, engine jobs, two real children, continuation authority and governance; browser media/WebRTC is synthetic. The actual terminal also loads four pinned assets from the app origin under loopback-only guards and executes exact local command/restart effects. Final result rows and source fingerprints remain authoritative.

The following batches can run safely with additional disposable local fixtures. None requires production state or messages to other people. Each needs rendered actions, authoritative readback, the stated negative case, and meaningful state variants.

| Priority | Concrete remaining operations | Required evidence | Stable stories |
|---|---|---|---|
| P0 | Remaining policy precedence and CLI/MCP resource variants | Exercise actual CLI approval-command and populated MCP grants/denials; compare preview with a user's real tool result; change policy during delegated child execution. Skill allow/deny removal, retained workspace revocation, role-level changes and requester status are already covered and should be retained as regression cases. | GOV-006/007/011, POL-008/025/031 |
| P0 | Cross-user conversations, projects and knowledge | Retain another member's browser after project removal; attempt copied session URLs, transcript export and mutations; isolate Bot A/B knowledge; submit stale knowledge revision. Confirm exact hidden/private markers never leak. | SESS ownership variants, PROJ-004/006/008/009, KNOW-002/004/005/008/010 |
| P1 | Remaining file formats, skill runtime and imports | Hostile/structured/large file previews; drag/drop with hierarchy; non-Markdown skill links and view-permitted/load-denied runtime; import by a globally chat-denied identity, forged existing session ID and unsupported JSON shapes. Exact workspace rejection and forged owner/profile/participant handling are covered by the import-authority case. Existing lifecycle, chooser, cancellation, linked-file and hidden-file cases remain scoped to their actual assertions. | FILE-003/004/005/009/012/013, SKILL-002/006/008, SESS-018 |
| P1 | Remaining board and transition depth | Multiple selected tasks with partial failures; custom blocker reason where exposed; worker-owned task fences in the frontend; live eligible dispatch in an isolated process fixture. Existing board CRUD, exact filters, dependency cycles, direct Done and default-reason Block/Unblock have separate scenarios. | KAN-005/008/009/011/015 |
| P1 | Auxiliary dispatch and populated system catalogs | Trigger each configured auxiliary worker and verify the actual saved provider/model used; deliberate completion failure after successful provider probe; initialize local MCP and inspect populated schema/paging; trigger/acknowledge a local capacity alert. All 12 slot saves/reset and basic local MCP toggles already pass focused tests. | PROV-004/009/010, SYS-007/008/011 |
| P1 | Remaining preference behavior | Long-transcript virtualization, actual source-type session filtering and sound/notification states. Search, German DOM translation, welcome/suggestions, workspace Todos and both default-pane choices are already assertion-scoped. | PREF-021/023/026/035, SESS-002, CHAT-016 |
| P2 | Recovery, clarification, focus and clipboard | Deterministic clarification submit/resume; failed-send draft retention; offline/reconnect and stale-client refresh; exact message/terminal clipboard bytes; keyboard focus and terminal resize. Filtered log-copy bytes already have a separate scenario. | CHAT-010/018, UX-004/006/008/009, TERM-003/004/006 |
| P2 | First-run, connector and extension lifecycle fixtures | Empty-home onboarding validation/back/skip with local provider; restricted connector request/callback/consent; disposable extension sidecar with known local storage and denied routes. The documented self-contained plugin IIFE renders securely; arbitrary full-SPA authenticated assets need their own explicit bundle/proxy contract and tests. | AUTH setup, CONN-001/002/003/005–010, EXT-001–012 |

<!-- additional-affordances:start -->
Selected-run additional affordances: US-SP-AFFORDANCE-FILE-CANCEL PASS; US-SP-AFFORDANCE-SKILL-LINKS PASS; US-SP-AFFORDANCE-HIDDEN-FILES PASS; US-SP-AFFORDANCE-MESSAGE-FORK PASS. Exact cancellation bytes, skill linked-file/root authorization, hidden-file visibility and message-prefix forking are mapped in the catalog; they do not certify all file formats, runtime skills or sidebar lineage.
<!-- additional-affordances:end -->

## Concrete controls for the next local batches

The runtime inventory contains wrapper elements and repeated dynamic labels as well as real controls. The following stable selectors identify meaningful next actions; they are not a request to force-click hidden or inapplicable elements. Confirm the selected persona and current state in [control-coverage.csv](evidence/control-coverage.csv) before execution.

| Bounded batch | Rendered controls | Required outcome beyond a click |
|---|---|---|
| CLI/MCP policy | `govUserCliCommandsInput`, `govUserCliApprovalInput`, `govUserDenyCliInput`, `govUserMcpServersInput`, `govUserDenyMcpInput` | Persist exact grants/denials, preview the chosen identity, then exercise the corresponding real allowed and denied tool action. |
| Remaining file/import variants | `fileTree`, `btnImportJSON`, `previewMd`, `btnDownloadFile` | Exercise supported drag/drop hierarchy, hostile/structured/large previews and globally chat-denied imports, forged existing session IDs and unsupported JSON shapes; prove exact permitted bytes and denied ownership/path effects. |
| Remaining board variants | `kanbanBulkStatus`, `kanbanDependencyInput`, dispatcher controls | Prove multiple selected items and partial failure reporting, concurrent worker fencing and isolated actual dispatch. Existing single-item bulk, dependency cycles and Preview are separate evidence. |
| Preferences and recovery | `settingsVirtualizeTranscript`, `settingsShowCliSessions`, `settingsShowCronSessions`, `settingsShowWebhookSessions`, `btnReload` | Assert real transcript/source-list behavior and recovery after a controlled disconnected request. Default-pane behavior and filtered log copying already have explicit scenarios. |
| Remaining navigation and refresh | `integrationsRefreshBtn`, session source filters and current conditional catalog controls | Seed a changed permitted result, use the rendered refresh/filter, and prove both correct visible content and denied-object exclusion. Attach chooser, workspace edge, rail labels and requester Refresh are already individually exercised. |

## Product decisions and dependent acceptance

<!-- current-browser-verdict:start -->
No browser scenario failed in this selected run. Public Share and manual Todo Done/Blocked now have supported workflows and explicit tests; their former404 results remain historical, while unasserted criteria stay in the matrix.
<!-- current-browser-verdict:end -->

- **Administrator rejection reason:** capability rejection and requester status persist, but the current form has no reason input. The historical reason-entry clause in GOV-014 requires a product decision; it must not be silently marked passed.

## Evidence requiring a real external service or physical device

| Capability | Missing real-world evidence | Independently testable local coverage |
|---|---|---|
| Provider OAuth | Authorized disposable account, consent, refresh and revocation against the actual provider | Catalog/search, callback fixture, duplicate requests and owned/shared permission cases |
| Real automatic decision model | Named configured model evaluating harmless allowed/denied requests with assessed output and policy revision; POL-033 | Deterministic classification, malformed/timeout/uncertain responses and actual engine effects |
| Physical voice/dictation | Real microphone, native WebRTC/audio quality and actual voice/transcription provider; VOICE-007 | Current real handlers/sideband/engine with synthetic browser media; separate dictation and raw-audio fixtures remain locally implementable |
| Physical passkey | Intended authenticator/device compatibility | Browser virtual authenticator and additional account/credential boundary cases |
| Live delivery and service operations | Actual third-party delivery, production gateway upgrade/restart and live update channel | Disposable sink, scheduler, process restart and extension health fixtures |

## Requirements before an “all clicks” claim

1. Regenerate the current control inventory after the final full run; preserve the historical inventory separately. Normalize containers, dynamic labels and repeated states into meaningful operations without silently removing untested controls.
2. Keep discovery, recorded interaction and verified effect separate. A found locator or a checkbox already in the desired state is not evidence of a successful click or its downstream behavior.
3. Enumerate missing roles and states explicitly: non-admin navigation, populated/empty catalogs, changed policy, stale dialogs, denied devices, failed requests and keyboard paths. An admin-only tour cannot establish the complete product inventory.
4. Explain intentional hidden controls. New governed one-shot approval deliberately omits session-wide/permanent/skip-all choices; absence is asserted. Never click these by force or count an inapplicable control as a skipped pass.
5. Preserve uncaught-error evidence and harness warnings. The secondary-context Playwright fixture-step warning is a reporter limitation, distinct from an application page error; do not suppress or relabel it.
6. Keep precise local acceptance passes separate from physical/external claims, and keep unexecuted stories visible. Application policy enforcement does not constitute an OS sandbox for elevated host commands or arbitrary plugins.
