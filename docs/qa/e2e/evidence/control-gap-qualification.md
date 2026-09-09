# Qualification of the remaining control inventory

**235 browser scenarios passed; all clicks are not certified.** Frozen run `20260909-184341-281192000` at WebUI `90cc10318788db857464663b1874d28eb1e50430` and engine `b0aaa74f9dcfe9e7caa4692656b4535ce04104e1` recorded **1,265 controls: 623 interacted with in passing scenarios and 642 without interaction evidence**. All 235 cases passed once, without skips, retries or flaky results; all 235 uncaught-browser-error collections are empty. Seventeen reporter bookkeeping warning entries are retained separately. These are different measures from the 365 acceptance stories: **23 PASS, 220 PARTIAL, 122 NOT RUN, 0 FAIL**.

The [per-control qualification](control-gap-qualification.json) preserves every raw key, its original `NOT_INTERACTED` status, source reference and a narrow shared-handler example where one exists. No row inherits PASS and no control was removed from the gate. The classification uses the current source and the selected run; it does not turn 642 entries into a claimed exact count of unique features.

| Planning category | Raw gaps | Meaning |
| --- | ---: | --- |
| Repeated data instances or shared component wrappers | 350 | Session labels, file/path rows, user/group values, message indices and wrapper controls share implementation. Their particular state and authorization combinations remain unverified. |
| Observed control gaps and distinct contracts requiring review | 208 | Visible raw entries without an interaction record. Includes 51 provider-card labels/configurations and 11 auxiliary Advanced slot buttons; neither group is declared equivalent merely because it shares a renderer. |
| Source-only, conditional or non-interactive backing controls | 50 | Unseen states, offscreen backing fields, readonly controls and deliberately forbidden approval choices. Unseen does not mean unreachable. |
| External/native integration or first-run onboarding | 34 | Thirteen onboarding/OAuth, fourteen audio/notification, three external Notes and four documentation-link entries. Many form and error paths remain locally testable; this is not a blanket external blocker. |
| **All retained raw gaps** | **642** | **Every entry remains un-interacted.** |

Across these planning categories, 576 gaps were observed at runtime and 66 came only from source inventory. This observed/unobserved split is independent of the four categories.

## Repeated instances and their limits

| Family | Raw gaps | Source and qualification |
| --- | ---: | --- |
| Session title/age rows | 152 | `static/sessions.js:8282`. Elapsed labels are data, while ownership, active/archive/source and streaming states still have different behavior. |
| File and directory rows | 49 | `static/ui.js:21026`. Shared tree rendering does not equate file types, symlinks, escape roots or read/write authority. |
| Governance entity edit/delete actions | 44 | `static/governance.js:989`, `static/governance.js:1302`. Exact named-handler examples may be recorded, but another identity's access after editing/deletion is not inherited. |
| Chip-focus wrappers | 41 | `static/governance.js:546`. Thirty-nine corresponding child inputs have interaction evidence. That establishes the child interaction, not the wrapper click or every permission dimension. |
| Allowed-user/group values | 31 | `static/bot-builder.js:42`, `static/bot-builder.js:52`. A shared checkbox collector does not establish all identity or group combinations. |
| Message-index actions | 12 | `static/ui.js:1979`, `static/commands.js:1953`, `static/outline.js:109`. The same navigation/fork handler can behave differently at boundaries, in a truncated transcript or during streaming. |
| Breadcrumb path segments | 7 | `static/workspace.js:1314`. A shared breadcrumb handler is not authority for every target path. |
| Indexed workspace assignment | 7 | `static/governance.js:1394`, `static/governance.js:1493`. One index's owner/member outcome does not cover another workspace's ACL. |
| Skill/category rows | 4 | `static/panels.js:4971`, `static/panels.js:5005`. Linked resources, formats and authorization remain distinct. |
| Global suggestions observed in another panel | 3 | `static/index.html:480`. Shared markup does not establish that each suggestion produces the expected dispatched result. |

These ten groups sum to 350, but they are not 350 passed operations. Remaining labels outside them may also share UI; that needs review before grouping. Provider cards (`static/panels.js:11506`) have distinct OAuth/API-key/self-hosted and vendor-specific paths. Auxiliary Advanced controls (`static/panels.js:12726`) have distinct worker routing and service-tier contracts. Their raw gaps remain explicit.

## How 559 became 539 and now 642

| Frozen run | Browser cases | Inventoried controls | Interacted | Raw remaining |
| --- | ---: | ---: | ---: | ---: |
| `20260908-222640-169443000` | 176 | 1,007 | 448 | 559 |
| Initial released scope: `20260909-080212-676633000` | 192 | 1,053 | 514 | 539 |
| Historical frozen pass: `20260909-124140-843191000` | 225 | 1,243 | 610 | 633 |
| Current selected run: `20260909-184341-281192000` | 235 | 1,265 | 623 | 642 |

Compared with the 192-case baseline, the current suite found **212 more inventory entries and recorded 109 more interactions**. The raw gap therefore increased by 103; it did not shrink to a fabricated “all tested” number. Long histories, new conversations/files and elapsed-time labels add dynamic observations. Repeated-instance gaps grew by 105, the observed/distinct-contract category grew by 14, source/conditional gaps fell by 16, and the external/onboarding category stayed unchanged.

An exact stable-ID comparison shows **25 previously un-interacted IDs now interacted**, 171 still un-interacted and zero absent. Examples now covered include Start/End and outline, virtualization, Render Markdown Anyway, clarification input/submit, real Kanban dispatch, Cron weekday/month-day/model fields, CLI/MCP policy fields and project chat/upload. These are interaction transitions, not automatic whole-story PASS. The JSON lists every ID; no disappearing dynamic label is counted as closure.

## Meaningful progress and remaining independent cases

The current full run includes real local CLI/MCP hard-deny and mandatory-review effects, populated MCP paging, retained project revocation, bot knowledge revision conflicts, long-history navigation and destructive Edit-index checks, quoted CSV/JSON/HTML/large Markdown previews with exact downloads, real clarification and Kanban worker dispatch, weekly/monthly/custom/one-shot Cron behavior, selected model/profile/skill execution, extension lifecycle/consent/storage, and draft/session activation races. These journeys are mapped to their exact assertions; they are not still listed as wholly missing work.

The following ten independent families remain useful local work. They are coverage proposals, not ten confirmed defects. The raw selectors are observed/source references, not permission to force-click hidden elements.

| Priority | Distinct next case | Evidence required |
| --- | --- | --- |
| 1 | First-run onboarding | Back/Next/Skip, required-field errors, local provider and allowed workspace, then persisted configuration and reload recovery. Genuine vendor OAuth stays separate. |
| 2 | Provider editor contracts | Exercise the actual API-key, OAuth and self-hosted editor branches, failed-save recovery and resulting routed request. A shared card header or connection probe alone is insufficient. |
| 3 | Mobile composer configuration | Use `composerMobileConfigBtn` and its model/reasoning/workspace/toolset actions; confirm the next turn's selection and a revoked/invalid choice's refusal. Existing mobile voice/governance tests cover different contracts. |
| 4 | Session-source visibility | Toggle CLI, Cron, webhook, Claude Code and previous messaging sources against real synthetic sessions; verify exact list changes and exclusion of other users' sessions. |
| 5 | Queue cancellation | Cancel one real queued item while another turn runs, preserve its neighbor, then prove no canceled dispatch after completion and reload. Existing queue/steer/interrupt tests do not assert this cancel control. |
| 6 | File drag/drop destinations | Drop into root/directory/breadcrumb destinations, compare exact bytes and hierarchy, and reject readonly/unauthorized paths. Chooser upload, preview and download are separate. |
| 7 | Authentication administration | Change current password and exercise disable/passwordless acknowledgements, retained and expired sessions in disposable state. Virtual passkey registration is a different flow. |
| 8 | Auxiliary worker execution by slot | Prove each remaining worker uses its selected provider/model and supported advanced settings. All-slot persistence and actual title generation do not execute every slot. |
| 9 | Composer/terminal clipboard and native media | Exact message and terminal clipboard bytes are locally testable. Dictation/TTS/notification settings and denial paths can also run locally; microphone, speaker and OS delivery need separate platform evidence. |
| 10 | Conditional maintenance and no-agent Cron | Trigger offline/stale-client/reload and isolated gateway/update failures; execute an existing readonly no-agent script schedule. Never mutate production services merely to improve a click count. |

`modelSelect` is an offscreen backing select; use the visible model chip. `cronFormScript` is readonly for existing no-agent jobs. Permanent/session/skip-all choices are intentionally absent from governed one-action approvals: correct absence is security evidence, not a click. These remain recorded raw entries.

## Failed attempts, host boundaries and production

The current verdict belongs only to the complete Mac235 run and its source fingerprints. Earlier Mac runs retain their failures, including documented sleep interruptions and corrected Start/focus/session/draft/Cron defects. The immutable Linux run at source `530710751934b36f0105313aae75e368b1817583` passed 203 of 224 and failed 21. CPU-cap changes do not establish individual failure causes. Subsequent targeted Linux attempts retain their original failures and source bindings.

At the current `90cc10318788db857464663b1874d28eb1e50430` / `b0aaa74f9dcfe9e7caa4692656b4535ce04104e1` pair, Linux v5 separately passed those exact 21 historical titles once, without browser/report errors. Its sampled process identities were gone, dedicated cgroup absent and listener closed. The selection excludes advanced Cron, the Cron-picker and task-edit focus regressions; their evidence comes from the Mac full run. Neither this replay nor the Mac pass relabels the old Linux224 result or certifies all Linux features. Review history keeps the full selection and cleanup scope.

All acceptance work used private fixture state, signed synthetic identities and deterministic loopback services. Real handlers, persistence, engine tools, child jobs and local sidecars were exercised where each scenario asserts them. This is not an OS sandbox or proof of real-provider decision quality, native microphone compatibility, external OAuth or delivery. Earlier production receipts apply only to their recorded deployed pair; this test run is not a deployment receipt.

The coverage gate and underlying run were not changed by this qualification. The source and raw observations are retained so further work can close a meaningful contract without hiding the remaining clicks.
