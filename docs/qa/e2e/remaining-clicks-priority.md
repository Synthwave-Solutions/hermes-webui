# SynthPulse remaining frontend QA priorities

The acceptance catalog now contains **365 stable stories**, including 16 precise realtime voice stories discovered during implementation. The authoritative full-suite run is `20260909-184341-281192000`; its final counts and source fingerprints are in [execution-summary.json](evidence/execution-summary.json). Use the [story matrix](coverage-plan.csv) for exact assertions and gaps; a passing browser scenario is not certification of an entire historical story or every click.

The current control inventory contains **1,265 source/runtime entries: 623 recorded interactions in passing tests and 642 without such interaction evidence**. Entries include wrappers and repeated states; this is not a count of distinct fully verified user operations. The selected run has 235 browser scenarios and 235 primary uncaught-browser-error collections with 0 errors. 17 recorded fixture bookkeeping log entries remain documented separately in [run-review-notes.json](evidence/run-review-notes.json).

The earlier `20260908-202702-435893000` run is historical behavior evidence only. It ran 139 cases with 137 passes and two failures, and found 937 inventory entries with 366 interactions. Its fixture isolation claim was rejected after provider discovery could access host Copilot authentication. Those counts must not be reused as the next candidate's QA verdict. Current runs use private OS HOME/config/PATH plus browser and Python loopback network guards.

Subsequent actual local browser coverage includes all 14 additional grant/deny fields, legacy metadata preservation, group/user/capability administration, whitelist/blacklist and level revocation, requester pending/approved/rejected status, model/settings/skill direct-denial probes, settings behavior, eight System/Plugins/provider workflows, and owner/member workspace assignment. The workspace cases verify retained file/session/terminal denial and a real write blocked after membership is removed while human approval is pending. The realtime cases exercise actual voice HTTP handlers, local sideband WebSockets, engine jobs, two real children, continuation authority and governance; browser media/WebRTC is synthetic. The actual terminal also loads four pinned assets from the app origin under loopback-only guards and executes exact local command/restart effects. Final result rows and source fingerprints remain authoritative.

The following batches can run safely with additional disposable local fixtures. None requires production state or messages to other people. Each needs rendered actions, authoritative readback, the stated negative case, and meaningful state variants.

| Priority | Concrete remaining operations | Required evidence | Stable stories |
|---|---|---|---|
| P0 | Remaining policy precedence and delegated revocation | Change a grant/deny while an actual delegated child is pending or running; verify the selected resource and original-subject ceiling. CLI command grants/mandatory review and local/canonical MCP denial now have real execution evidence. | POL-008/025/031, GOV-007 |
| P0 | Remaining conversation/project/knowledge authority | Test copied conversation/export mutations and already-running project work after membership changes; exercise selected bot knowledge in actual ingestion/retrieval. Retained project pages and bot A/B selection/revision conflicts already pass. | SESS authority variants, PROJ-004/006/008/009, KNOW-006/008/010 |
| P1 | Remaining file formats, runtime skills and imports | Code/image/Office/PDF variants, drag/drop hierarchy, non-Markdown skill links, view-permitted/load-denied invocation and unsupported or globally chat-denied imports. Quoted CSV, JSON, opaque HTML, large Markdown and exact downloads are now asserted. | FILE-003/009/012/013, SKILL-002/006/008, SESS-018 |
| P1 | Remaining task editor and worker fences | Exercise advanced task workspace/skill/max-runtime fields, custom reason if exposed and concurrent worker-owned transitions through the UI. Real local worker dispatch and mixed multi-selection partial failure are covered. | KAN-005/008/009/011/015 |
| P1 | Remaining auxiliary slots and capacity effects | Execute each remaining worker with its selected provider/model; test supported service tiers and local capacity alert acknowledgement. All-slot save/reset, actual title generation, pending Apply/Save isolation and populated MCP paging already pass. | PROV-004/009/010, SYS-011 |
| P1 | Source filters and mobile configuration | Verify actual CLI/Cron/webhook/messaging list changes with ownership filtering; use mobile composer model/reasoning/workspace/toolsets on the next turn. Virtualized history, Start/outline/End and stale Edit-index protection already pass. | PREF-023/026/035, SESS-002, CHAT-016 |
| P2 | Remaining recovery, queue cancel and clipboard | Cancel the selected queued item with exact no-dispatch proof; test failed-send/offline recovery, message/terminal clipboard bytes and terminal resize. Real clarification and draft/activation races are already covered. | CHAT-010/011/018, UX-004/006/008/009, TERM-003/004/006 |
| P2 | First-run, provider and connector contracts | Empty-home onboarding Back/Skip/errors; distinct local provider editors and connector request/callback/consent. Local extension install/storage/consent/uninstall and plugin IIFE isolation already pass, with vendor transport explicitly synthetic. | AUTH setup, CONN-001/002/003/005–010, EXT unasserted clauses |

<!-- additional-affordances:start -->
Selected-run additional affordances: US-SP-AFFORDANCE-FILE-CANCEL PASS; US-SP-AFFORDANCE-SKILL-LINKS PASS; US-SP-AFFORDANCE-HIDDEN-FILES PASS; US-SP-AFFORDANCE-MESSAGE-FORK PASS. Exact cancellation bytes, skill linked-file/root authorization, hidden-file visibility and message-prefix forking are mapped in the catalog; they do not certify all file formats, runtime skills or sidebar lineage.
<!-- additional-affordances:end -->

## Concrete controls for the next local batches

The runtime inventory contains wrapper elements and repeated dynamic labels as well as real controls. The following stable selectors identify meaningful next actions; they are not a request to force-click hidden or inapplicable elements. Confirm the selected persona and current state in [control-coverage.csv](evidence/control-coverage.csv) before execution.

| Bounded batch | Rendered controls | Required outcome beyond a click |
|---|---|---|
| Mobile composer choices | `composerMobileConfigBtn`, mobile model/reasoning/workspace actions | Selected value reaches the next actual turn; an invalid or revoked selection remains denied. |
| Queue cancellation and clipboard | `Cancel queued message`, `copyMsg`, `btnTerminalCopy` | Cancel only the chosen item without dispatching it or losing its neighbor; compare exact clipboard content. |
| Remaining file/import variants | `fileTree`, `btnImportJSON`, supported destination rows | Real drag/drop hierarchy and readonly/path refusal; unsupported or globally chat-denied imports make no unauthorized record. |
| Task advanced fields | Task modal workspace, skills and max-runtime fields | Persist actual selected configuration and demonstrate the running worker uses it; preserve existing worker run fencing. |
| Source visibility and recovery | `settingsShowCliSessions`, `settingsShowCronSessions`, `settingsShowWebhookSessions`, `btnReload` | Exact synthetic source lists change without exposing another identity; controlled disconnect/reload retains valid work. |
| Conditional catalog refresh | `integrationsRefreshBtn`, `cronRefreshBtn`, `governanceRefreshBtn` | Seed an authorized changed result, refresh visibly, and prove stale or denied objects remain excluded. |

See [control-gap qualification](control-gap-qualification.md) for all 642 retained entries, repeated-instance limits, stable-ID progress and ten independent next families.

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

1. The current inventory has been regenerated from the final235 run. Preserve it and the historical inventory; further normalization must keep all untested raw controls visible.
2. Keep discovery, recorded interaction and verified effect separate. A found locator or a checkbox already in the desired state is not evidence of a successful click or its downstream behavior.
3. Enumerate missing roles and states explicitly: non-admin navigation, populated/empty catalogs, changed policy, stale dialogs, denied devices, failed requests and keyboard paths. An admin-only tour cannot establish the complete product inventory.
4. Explain intentional hidden controls. New governed one-shot approval deliberately omits session-wide/permanent/skip-all choices; absence is asserted. Never click these by force or count an inapplicable control as a skipped pass.
5. Preserve uncaught-error evidence and harness warnings. The secondary-context Playwright fixture-step warning is a reporter limitation, distinct from an application page error; do not suppress or relabel it.
6. Keep precise local acceptance passes separate from physical/external claims, and keep unexecuted stories visible. Application policy enforcement does not constitute an OS sandbox for elevated host commands or arbitrary plugins.
