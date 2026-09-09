# SynthPulse frontend E2E user stories and acceptance catalog

> **Final candidate evidence:** run `20260908-222640-169443000` uses private fixture state and loopback-only transports. The earlier 139-case run is historical behavior evidence; its original isolation claim was rejected and is not reused. This catalog distinguishes local synthetic-media acceptance from physical/live-provider evidence and does not claim exhaustive all-click coverage.

Prepared 2026-09-08. **362 acceptance stories across 26 feature areas. Execution reconciliation: 21 PASS; 175 PARTIAL; 2 FAIL; 164 NOT RUN. Passing stories certify only their stated acceptance scope; no all-features pass is claimed.**

This acceptance catalog began from the September 2 source export, September 6 feature material and the requested governance behavior. Current isolated browser execution is now mapped conservatively to its actual assertions. PASS means every stated acceptance assertion has current-spec evidence on a frozen source run. PARTIAL means some relevant assertions passed, while the full story still has open requirements. FAIL means the latest mapped browser test failed and needs triage; it does not mean every aspect of that story was executed. NOT RUN means no matching actual frontend assertion is evidenced. Current production deployment and exhaustive persona/control inventory are not certified.

The companion [coverage-plan.csv](coverage-plan.csv) is the machine-readable click and acceptance matrix. Each row contains a stable story ID, persona, actual frontend steps, persisted/read-back outcome, permission-negative path, test requirements, status, provenance and assertion-scoped execution mapping. Preserve these IDs when linking executable tests and findings.

<!-- final-run-summary:start -->

The current frozen-source execution is **20260908-222640-169443000**: **176 browser scenarios, 174 passed and 2 failed**. The two known rendered failures are public Share creation (SESS-010) and Done from an existing Todo task (KAN-007); later sharing assertions do not execute past creation. Every mapped case in the matrix identifies its actual assertion scope. Browser-scenario counts and full-story acceptance counts have different denominators. The paired source fingerprints are WebUI `d42a8115938eb65f3239120d3c8d23f823ce1464656f4f3d65e4ccb34990f6a5` and engine `3783a0a86080480305aea5caee79cc9e25df1fc4b4bd9a509ea587cc0283a7cc`.

<!-- final-run-summary:end -->

The current control inventory contains **1,007 source/runtime entries: 448 recorded interactions in passing tests and 559 without such interaction evidence**. Entries include wrappers and repeated states; this is not a count of distinct fully verified user operations. All 176 scenarios attached uncaught-browser-error collections with zero errors. Nine recorded fixture bookkeeping log entries remain documented separately in [run-review-notes.json](evidence/run-review-notes.json).

The remaining interactive inventory is reviewed in [remaining-clicks-priority.md](remaining-clicks-priority.md), with exact current control rows in [control-coverage.csv](evidence/control-coverage.csv) and review limitations in [run-review-notes.json](evidence/run-review-notes.json).

## Scope and evidence rules

- **HISTORICAL_SOURCE_DERIVED:** a control, workflow or behavior was found in historical source/release material. Labels, selectors, route wiring and continued availability must be verified on the current candidate. Source functions alone do not prove a feature is currently exposed.
- **REQUESTED_NEW_BEHAVIOR:** acceptance criteria for the user's requested RBAC, whitelist/blacklist and per-user manual/automatic decisions. The current implementation schema, precedence and legacy defaults must be reconciled with these criteria.
- The old static index contained 288 identified input/button/select/textarea controls and 15 navigation panel IDs. These are historical discovery counts, not a current runtime inventory or 288 executed clicks. Dynamic menus, settings, bot editors, role-specific controls and error states add controls.
- The runtime inventory must enumerate visible and disabled interactive elements in each relevant persona, screen, dialog, empty/populated and busy/error state. Map every discovered element to a story and actual exercised locator. Any missing mapping remains an explicit gap.
- A browser case must execute the actual rendered interaction and real application endpoint. Direct API setup/read-back and negative bypass probes supplement the case; they do not substitute for the user's frontend action.
- A read-only story must verify the displayed result against its fixture and verify no unintended mutation. A mutation story requires a fresh read/reload and, where relevant, a second authorized browser context or exact downloaded bytes.
- Do not use conditionally absent controls/data as a passing test. Required fixture absence is a setup failure or explicit blocked coverage item. A skipped test is not a pass.
- When one test covers several IDs, record each actual assertion and evidence reference. Do not assign a whole area to a navigation smoke test.
- Injecting controlled failure responses is appropriate for an error-path case, but its evidence must be labeled. Successful mutation, identity, permission and persistence cases use the real application/backend.
- Expected permission refusals belong to their negative case. Unexpected page errors, failed requests, console errors and missing artifacts require a linked finding.

## Fixtures and execution boundaries

Use a fresh isolated application state directory, agent home, workspace, governance policy and signed synthetic identities. Keep credentials/session files private and outside deliverables. Use stable local file contents and sentinel markers, two bots, at least two member accounts, an outsider, and ordinary/elevated/admin plus whitelist/blacklist and manual/automatic variants. Use the actual engine with a deterministic loopback provider for repeatable dispatch tests. Authentication itself must also have real login/passkey cases; seeded sessions alone do not test login.

Run mutable stories on isolated state or a dedicated disposable test tenant. Scheduled work, delivery targets, terminal commands, extension installation, password changes, gateway actions and checkpoint restore must use their named isolated fixtures. A real external roundtrip has its own explicit requirement and evidence: a local callback, successful connection probe or deterministic inference cannot establish real OAuth, microphone/WebRTC or configured AI-model integration.

Whitelist/blacklist mode, role and approval flow are separate dimensions in the requested behavior. Explicit denial must win. Whitelist begins with no protected capabilities until allowed. Blacklist permits unlisted functional actions under the documented selected-role contract. Whether authentication/help/request-access shell endpoints remain available, the precise elevated/admin powers, final-admin recovery, pending-request migration and legacy defaults must be explicitly documented and tested against the actual implementation; do not silently infer permissive defaults.

## Execution workflow and status

1. Record current source commit, paired engine commit, active feature flags, runtime version and served asset hashes. Compare the historical inventory to current source.
2. Seed deterministic fixtures and build a current runtime control manifest by persona/state. Fail fixture setup if required data or permissions are absent.
3. Execute representative happy and negative flows, then complete all mapped clicks and state variants at desktop, laptop and mobile widths.
4. Record assertions, exact test references, screenshots/trace/video where suitable, sanitized request outcomes, persisted read-back and findings. Keep external tests and pure integration/API checks distinguishable.
5. Independently review authorization, privilege inheritance, AI decision parsing, revocation and immutable bot/delegation ceilings. Re-run affected cases after changes.
6. Reconcile this matrix with actual results. Only evidence-backed assertions may change status. Current reconciliation records PASS for complete stated acceptance, PARTIAL for passing subsets, FAIL for the latest failed mapped execution, and NOT RUN for uncovered stories. No passing navigation check establishes a feature-level pass.

Suggested evidence record per executed ID: candidate commit, engine commit, test path/name, command/run ID, fixture persona, viewport/browser, start/end time, assertions, actual result, screenshot/trace link, read-back evidence and finding ID. Coverage percentage uses the current reconciled inventory denominator; do not divide a smoke-suite pass count by this planning list and call it all-click coverage.

The reconciled candidate heads are WebUI `820b4a8eecb2a223a8c133358e1dad7a10830211` and engine `77ce302a209a586096d0c52336f42f357722f3e0`. Exact tested file fingerprints, original run heads and run ID remain in [source-provenance.json](evidence/source-provenance.json). The authoritative scenario report is [executed-scenarios.csv](evidence/executed-scenarios.csv), with aggregate results in [execution-summary.json](evidence/execution-summary.json). Executable sources are under [test-kit](README.md). Production deployment is not certified by this local run. Provisional executable test IDs are mapped by reviewed assertion semantics, not ID equality.

## Current governance contract and execution limits

The current implementation treats level, management mode and approval flow independently. An ordinary or elevated user's assigned roles/groups define the resource ceiling; explicit Admin supplies the administrator preset. Blacklist allows unlisted capabilities within that ceiling. Whitelist requires direct explicit grants intersected with that ceiling. Explicit denials remain effective against wildcard grants. Bootstrap recovery administrators remain outside per-user restrictions, and the editor explains this exception.

Manual **action review** pauses an action that is already permitted by RBAC and resource policy. The owning signed-in requester/session receives Allow once or Deny; another account cannot authorize it. Session-wide, permanent and skip-all acceptance are unavailable for those requests. Requests to **expand capabilities**, such as new grants, skills, commands or integration access, use the separate governance administrator approval workflow. The automatic classifier can decide an eligible action using that user's stored administrator prompt; it cannot widen the role ceiling or replace an explicit denial. Uncertain, unavailable or malformed decisions must remain pending for manual review. The loopback deterministic decision provider proves plumbing and side effects; it does not prove real-model judgment quality.

These are application and engine policy controls. This work does not establish an operating-system sandbox. Native commands, code execution, custom plugins and external services need their own runtime containment and endpoint coverage; no OS isolation claim follows from passing route tests.

## Current exposure and open execution categories

| Observation | Current evidence | Treatment in this catalog |
|---|---|---|
| Footer Chat/Super visibility setting `hide_composer_chat_mode` | Legacy key remains in `api/settings_scope.py`; current footer definitions in `static/boot.js` omit it; rendered mode buttons live in `static/index.html` under `#chatModeHeader`. Actual header switching passes. | Historical footer control retired from the current footer inventory; keep PREF-018 for still-rendered footer controls. Do not count a missing legacy control as a skipped pass. |
| Realtime voice | Sixteen precise local cases cover actual voice HTTP handlers, local sideband WebSockets, engine work, governance, task timing and delegated continuation; browser media/WebRTC is synthetic. | See VOICE-009 through 024. Physical microphone/native transport quality and live upstream-provider behavior remain separate in VOICE-007. |
| OAuth and external connectors | Local fixture has no real provider authorization/consent account. | Real-external acceptance is unprovisioned, distinct from local catalog/approval tests that remain implementable. |
| Physical passkey | Virtual CTAP2 device completes registration, identity login and removal against the actual app. | Browser WebAuthn protocol covered; physical authenticator/device compatibility is unprovisioned. |
| Real automatic decision model | Actual engine dispatches to a deterministic local classifier; it emits controlled approve/deny/manual decisions. | POL-033 remains NOT RUN until a named configured model is exercised and its decisions are assessed. |
| External delivery, gateway and extension/plugin lifecycle | Fixture delivery is local and does not include real chat/mail sinks, live gateway deployment, or an installed disposable extension sidecar. | External roundtrips are unprovisioned; local disposable sink/extension cases are locally missing tests, not an external-access blocker. |
| Other historical workflows without a matching executed assertion | Their story rows retain provenance and explicit NOT RUN status. | No claim that an untested historical feature is retired or absent. Verify current exposure and implement the local cases. |

Remaining locally implementable gaps include cross-user conversation/project/knowledge isolation variants, failed-send recovery, rich-content and clipboard behavior, populated MCP and auxiliary-worker dispatch, further policy precedence/delegation timing, scheduler permission/delivery variants, board dependencies/bulk filtering, local extension lifecycle, remaining preference behavior and keyboard/offline recovery. Current requester status, retained skill/workspace revocation, owner/member assignment, role levels, System/Plugins/provider configuration and 16 local realtime voice workflows have concrete scenario evidence; each historical story still lists its own unasserted criteria. Unprovisioned external/device evidence includes real provider OAuth, physical microphone/WebRTC, physical authenticator compatibility and named real-model judgment. See [remaining-clicks-priority.md](remaining-clicks-priority.md) for bounded next cases.

<!-- evidence-area-summary:start -->
## Acceptance coverage by feature area

Counts refer to complete story acceptance, passing subsets, actual failing assertions and stories without a matching execution. They are not click counts or a percentage of all live controls.

| Feature area | PASS | PARTIAL | FAIL | NOT RUN |
|---|---:|---:|---:|---:|
| Authentication and identity | 0 | 7 | 0 | 3 |
| Composer, responses and runtime | 4 | 10 | 0 | 8 |
| Conversation list and lifecycle | 0 | 8 | 1 | 8 |
| People, mentions and shared conversations | 0 | 3 | 0 | 9 |
| Bot creation and editing | 0 | 8 | 0 | 6 |
| Bot knowledge and shared memory | 0 | 3 | 0 | 7 |
| Personal memory and external notes | 0 | 2 | 0 | 6 |
| Projects and collaboration | 0 | 4 | 0 | 6 |
| File tree, previews and transfers | 0 | 4 | 0 | 9 |
| Workspaces and assignment | 0 | 4 | 0 | 4 |
| Scheduled tasks and run history | 0 | 9 | 0 | 5 |
| Kanban boards, tasks and orchestration | 0 | 4 | 1 | 12 |
| Session task list | 0 | 4 | 0 | 0 |
| Skills library and management | 0 | 6 | 0 | 2 |
| Connections catalog and account ownership | 0 | 1 | 0 | 9 |
| Governance administration and existing approval flows | 1 | 15 | 0 | 6 |
| Requested RBAC, whitelist/blacklist and automatic approval | 0 | 24 | 0 | 9 |
| Insights, usage and health reporting | 0 | 1 | 0 | 5 |
| Logs and diagnostics | 0 | 3 | 0 | 2 |
| Settings and personal preferences | 0 | 29 | 0 | 11 |
| Providers, models and budgets | 0 | 4 | 0 | 6 |
| Plugins and extensions | 0 | 3 | 0 | 9 |
| System, gateway, MCP and capacity controls | 0 | 4 | 0 | 9 |
| Dictation, speech and realtime voice | 16 | 3 | 0 | 5 |
| Interactive terminal | 0 | 5 | 0 | 4 |
| Whole-application control coverage and resilience | 0 | 7 | 0 | 4 |

<!-- evidence-area-summary:end -->

## Test requirement legend

| Requirement | Meaning |
|---|---|
| REAL_BROWSER | Drive rendered frontend controls against the real app/backend. |
| REAL_LOGIN / SIGNED_IDENTITIES | Test actual login separately; signed synthetic sessions may seed non-login flows. |
| RELOAD | Reopen or hard reload and verify the persisted authoritative result. |
| NEGATIVE_SERVER | Attempt relevant direct route/resource/runtime bypass and confirm server-side denial. |
| TWO_USERS / ADMIN_AND_MEMBER / ALL_PERSONAS | Separate browser contexts with distinct canonical fixture identities and roles. |
| TWO_BOTS | At least two distinct canonical bots to prove selection and isolation. |
| DETERMINISTIC_PROVIDER / PROVIDER_FIXTURE | Real app/engine dispatch to a controlled local completion service with inspectable requests. |
| POLICY_FIXTURES / AUDIT_READBACK | Explicit role/mode/prompt/revision fixtures and durable decision-event verification. |
| REAL_DECISION_MODEL | Exercise the actually configured AI decision model; deterministic classification fixtures alone are insufficient. |
| FILE_BYTES / DOWNLOAD_BYTES | Upload/download actual files and compare exact bytes or hashes. |
| PRIVACY_MARKERS / HOSTILE_CONTENT | Seed unique synthetic private sentinels or inert attack strings and assert isolation/escaping. |
| CONNECTOR_FIXTURE / DELIVERY_SINK | Disposable local integration callback/tool service or message sink; no colleague/customer communication. |
| ISOLATED_SCHEDULER / ISOLATED_RUNTIME / ISOLATED_TERMINAL | Execute lifecycle side effects only inside disposable test state/processes. |
| LOCAL_EXTENSION_FIXTURE | A disposable local extension/plugin with known permissions, storage and behavior. |
| SEEDED_USAGE / SEEDED_LOGS | Known expected metrics/log content; unknown is distinct from zero. |
| MEDIA_FIXTURE / VIRTUAL_AUTHENTICATOR | Browser-supported deterministic media/authenticator simulation, explicitly not real device proof. |
| REAL_DEVICE / REAL_EXTERNAL | Actual device/provider roundtrip in an authorized disposable environment; evidence remains separate. |
| KEYBOARD / CLIPBOARD | Exercise keyboard or real browser clipboard behavior, including permission/fallback where relevant. |
| DESKTOP_LAPTOP_MOBILE | Default acceptance widths: 1440x950, 1024x768, 390x844; add supported browser/device variants. |
| CONTROL_MANIFEST | Record current interactive controls by persona/state and map every one to execution or an explicit gap. |

## Feature index

| Code | Area | Stories | Inventory basis |
|---|---|---:|---|
| AUTH | Authentication and identity | 10 | HISTORICAL_SOURCE_DERIVED |
| CHAT | Composer, responses and runtime | 18 | HISTORICAL_SOURCE_DERIVED |
| SESS | Conversation list and lifecycle | 17 | HISTORICAL_SOURCE_DERIVED |
| GROUP | People, mentions and shared conversations | 12 | HISTORICAL_SOURCE_DERIVED |
| BOT | Bot creation and editing | 14 | HISTORICAL_SOURCE_DERIVED |
| KNOW | Bot knowledge and shared memory | 10 | HISTORICAL_SOURCE_DERIVED |
| MEM | Personal memory and external notes | 8 | HISTORICAL_SOURCE_DERIVED |
| PROJ | Projects and collaboration | 10 | HISTORICAL_SOURCE_DERIVED |
| FILE | File tree, previews and transfers | 13 | HISTORICAL_SOURCE_DERIVED |
| WS | Workspaces and assignment | 8 | HISTORICAL_SOURCE_DERIVED |
| CRON | Scheduled tasks and run history | 14 | HISTORICAL_SOURCE_DERIVED |
| KAN | Kanban boards, tasks and orchestration | 17 | HISTORICAL_SOURCE_DERIVED |
| TODO | Session task list | 4 | HISTORICAL_SOURCE_DERIVED |
| SKILL | Skills library and management | 8 | HISTORICAL_SOURCE_DERIVED |
| CONN | Connections catalog and account ownership | 10 | HISTORICAL_SOURCE_DERIVED |
| GOV | Governance administration and existing approval flows | 22 | HISTORICAL_SOURCE_DERIVED |
| POL | Requested RBAC, whitelist/blacklist and automatic approval | 33 | REQUESTED_NEW_BEHAVIOR |
| INS | Insights, usage and health reporting | 6 | HISTORICAL_SOURCE_DERIVED |
| LOG | Logs and diagnostics | 5 | HISTORICAL_SOURCE_DERIVED |
| PREF | Settings and personal preferences | 40 | HISTORICAL_SOURCE_DERIVED |
| PROV | Providers, models and budgets | 10 | HISTORICAL_SOURCE_DERIVED |
| EXT | Plugins and extensions | 12 | HISTORICAL_SOURCE_DERIVED |
| SYS | System, gateway, MCP and capacity controls | 13 | HISTORICAL_SOURCE_DERIVED |
| VOICE | Dictation, speech and realtime voice | 8 | HISTORICAL_SOURCE_DERIVED |
| TERM | Interactive terminal | 9 | HISTORICAL_SOURCE_DERIVED |
| UX | Whole-application control coverage and resilience | 11 | HISTORICAL_SOURCE_DERIVED |

## Source provenance

Historical source root: `/Users/michaelramirez/Documents/Codex/2026-09-06/cont/work`.

The September 2 export has no local Git metadata proving its exact commit. September 6 subdirectories contain later feature modules, fixtures and release scripts. The latest historical bot-editor report records production commit `461b34e55192f483d083d1b97db66b729e54bbbd`; this is dated evidence, not the current candidate version. Prior full-suite collection failures, degraded gateway observations and untested external microphone/WebRTC paths remain historical findings to recheck, not fresh outcomes.

The legacy `tests/e2e` folder contains two files and 13 cases, including API-only, renderer-injection and conditional/skip cases. They do not establish broad current frontend coverage. Newer real-browser fixtures under `chat-experience-v2`, `bot-editor` and the project/group scripts are reusable after path/port/source reconciliation.

## Detailed stories

### AUTH — Authentication and identity

Persona: registered user. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/login.js; static/onboarding.js; static/panels.js`.

#### US-SP-AUTH-001

As a registered user, I want to sign in with valid credentials.

- **Frontend steps:** Open login; enter fixture credentials; submit; open Chats; reload.
- **Persisted/read-back result:** The same authorized identity persists and only its permitted data is visible.
- **Permission negative:** An unsigned, expired or different-user session cannot access the protected action or disclose its result.
- **Required verification:** REAL_LOGIN; SIGNED_IDENTITIES; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-AUTH-002

As a registered user, I want to recover from invalid credentials.

- **Frontend steps:** Enter an incorrect fixture password; submit; then correct it.
- **Persisted/read-back result:** The rejected attempt creates no usable authenticated session; correction succeeds without a stuck state.
- **Permission negative:** An unsigned, expired or different-user session cannot access the protected action or disclose its result.
- **Required verification:** REAL_LOGIN; SIGNED_IDENTITIES; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-AUTH-003

As a registered user, I want to sign out cleanly.

- **Frontend steps:** Open Settings; activate Sign out; use Back; reload the previous chat URL.
- **Persisted/read-back result:** The session is invalidated and protected content is unavailable through history or direct requests.
- **Permission negative:** An unsigned, expired or different-user session cannot access the protected action or disclose its result.
- **Required verification:** REAL_LOGIN; SIGNED_IDENTITIES; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-AUTH-004

As a registered user, I want to handle session expiry.

- **Frontend steps:** Open a fixture-owned chat; expire that session through the fixture controller; click a protected action; reauthenticate.
- **Persisted/read-back result:** A recoverable authentication state appears and no failed action is reported as successful.
- **Permission negative:** An unsigned, expired or different-user session cannot access the protected action or disclose its result.
- **Required verification:** REAL_LOGIN; SIGNED_IDENTITIES; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-AUTH-005

As a registered user, I want to keep separate users isolated.

- **Frontend steps:** Use two browser contexts for Alice and Bob; open the same panels; switch profiles in one; reload both.
- **Persisted/read-back result:** Identity, private data and cached catalogs remain scoped to the respective user.
- **Permission negative:** An unsigned, expired or different-user session cannot access the protected action or disclose its result.
- **Required verification:** REAL_LOGIN; SIGNED_IDENTITIES; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-AUTH-006

As a registered user, I want to open an authorized deep link.

- **Frontend steps:** Copy a fixture chat link; open it in a fresh authenticated tab; reload.
- **Persisted/read-back result:** The correct permitted conversation/profile restores without changing another session.
- **Permission negative:** An unsigned, expired or different-user session cannot access the protected action or disclose its result.
- **Required verification:** REAL_LOGIN; SIGNED_IDENTITIES; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-AUTH-007

As a registered user, I want to refuse an unauthorized deep link.

- **Frontend steps:** Open an outsider-owned chat or file URL in Alice's tab.
- **Persisted/read-back result:** Protected data is absent; denied/not-found feedback is clear; no private payload is returned.
- **Permission negative:** An unsigned, expired or different-user session cannot access the protected action or disclose its result.
- **Required verification:** REAL_LOGIN; SIGNED_IDENTITIES; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-AUTH-008

As a registered user, I want to handle unavailable authentication service.

- **Frontend steps:** Make the fixture login service unavailable; submit; restore it; retry.
- **Persisted/read-back result:** Failure is visible, submit recovers and no authenticated state is invented.
- **Permission negative:** An unsigned, expired or different-user session cannot access the protected action or disclose its result.
- **Required verification:** REAL_LOGIN; SIGNED_IDENTITIES; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-AUTH-009

As a registered user, I want to register and use a passkey.

- **Frontend steps:** Open Settings > System; register a browser virtual-authenticator passkey; sign out; sign in with it.
- **Persisted/read-back result:** The credential belongs to the correct fixture account and survives reload.
- **Permission negative:** Another account cannot list, use or delete it.
- **Required verification:** VIRTUAL_AUTHENTICATOR; REAL_LOGIN; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-AUTH-010

As a registered user, I want to remove a passkey.

- **Frontend steps:** Register two fixture passkeys; remove one in Settings; reload; retry that credential.
- **Persisted/read-back result:** Only the chosen credential is removed; the remaining one works.
- **Permission negative:** A non-owner cannot remove the credential.
- **Required verification:** VIRTUAL_AUTHENTICATOR; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

### CHAT — Composer, responses and runtime

Persona: authorized chat user. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/messages.js; static/commands.js; static/index.html; chat-experience-v2/browser_qa.cjs`.

#### US-SP-CHAT-001

As an authorized chat user, I want to start a new conversation.

- **Frontend steps:** Click New chat; choose a permitted bot; type a unique prompt; click Send.
- **Persisted/read-back result:** One conversation and user turn persist; the selected bot produces the expected deterministic answer.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-002

As an authorized chat user, I want to switch Chat and Super agent modes.

- **Frontend steps:** Click each mode control; send a distinct prompt in each; reload.
- **Persisted/read-back result:** The chosen mode persists and the engine uses its appropriate tool surface.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-003

As an authorized chat user, I want to preserve model and provider together.

- **Frontend steps:** Choose a permitted model/provider pair; create a chat; send; reload.
- **Persisted/read-back result:** The exact pair remains in the UI and actual worker request.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-004

As an authorized chat user, I want to use the configured send shortcut.

- **Frontend steps:** Set each send-key preference; type multiline text; exercise send/newline keys.
- **Persisted/read-back result:** The action happens once and stored text preserves intended line breaks.
- **Permission negative:** A disabled composer cannot submit through keyboard.
- **Required verification:** REAL_BROWSER; KEYBOARD; RELOAD.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-005

As an authorized chat user, I want to prevent duplicate sending.

- **Frontend steps:** Double-click Send and press the send key during a delayed submit response.
- **Persisted/read-back result:** Only one logical message/turn is stored and busy state is truthful.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-006

As an authorized chat user, I want to queue a follow-up while busy.

- **Frontend steps:** Start a delayed response; choose Queue follow-up; submit another prompt; finish the first.
- **Persisted/read-back result:** The follow-up executes in order with no lost draft or duplicate user message.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-007

As an authorized chat user, I want to steer a running turn.

- **Frontend steps:** Start a delayed response; choose Steer; submit a correction; complete the run.
- **Persisted/read-back result:** The correction reaches the active run and the stored transcript matches the supported lifecycle.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-008

As an authorized chat user, I want to interrupt a running turn.

- **Frontend steps:** Start a delayed response; choose Interrupt; submit replacement instructions.
- **Persisted/read-back result:** The first run is interrupted and its late events cannot overwrite the replacement.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-009

As an authorized chat user, I want to stop an active response.

- **Frontend steps:** Start a streaming response; click Stop; wait; reload.
- **Persisted/read-back result:** The stopped outcome survives reload; no invented completion or stuck composer remains.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-010

As an authorized chat user, I want to retain a draft after send failure.

- **Frontend steps:** Type text and attach a fixture file; fail submit; retry after recovery.
- **Persisted/read-back result:** Draft and attachment remain recoverable; retry stores one turn.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-011

As an authorized chat user, I want to restore an unsent draft.

- **Frontend steps:** Type a unique draft; switch conversations; return; hard reload.
- **Persisted/read-back result:** The draft restores only for its user/session and is not automatically submitted.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-012

As an authorized chat user, I want to recover a stream after reload.

- **Frontend steps:** Start a multi-event response; reload while active; complete; reload again.
- **Persisted/read-back result:** Recovered text/activity/final state match storage without duplicate turns.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-013

As an authorized chat user, I want to show an early access failure.

- **Frontend steps:** Revoke selected-bot access before worker dispatch; click Send.
- **Persisted/read-back result:** A visible access error clears busy state and no provider request occurs.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-014

As an authorized chat user, I want to render rich responses safely.

- **Frontend steps:** Render fixture Markdown, code, table, math and hostile HTML; open viewers; copy output.
- **Persisted/read-back result:** Supported content renders and hostile text stays inert; copied content matches the fixture.
- **Permission negative:** Other-session content cannot enter the transcript.
- **Required verification:** REAL_BROWSER; HOSTILE_CONTENT; CLIPBOARD; RELOAD.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-015

As an authorized chat user, I want to switch structured code Tree and Raw views.

- **Frontend steps:** Open long JSON/YAML; click Tree/Raw; expand/collapse; copy raw text.
- **Persisted/read-back result:** Both views represent the same content and remain usable.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-016

As an authorized chat user, I want to navigate a long transcript.

- **Frontend steps:** Load a seeded long chat; scroll up; load older messages; use Start/End and outline links.
- **Persisted/read-back result:** Correct messages are reached without missing/duplicate turns and settings govern scroll behavior.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-017

As an authorized chat user, I want to inspect delegated workers.

- **Frontend steps:** Run two actual engine children; open their activity rows; complete; reload.
- **Persisted/read-back result:** Each child retains its task/status/tool counts with no private reasoning or false completion.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CHAT-018

As an authorized chat user, I want to retain terminal error outcomes.

- **Frontend steps:** Run a deterministic provider/worker failure; inspect activity/final state; reload.
- **Persisted/read-back result:** The error remains authoritative and a later valid prompt can run.
- **Permission negative:** Without chat, profile, model or tool access the server denies the action and no protected provider/tool dispatch occurs.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### SESS — Conversation list and lifecycle

Persona: conversation owner. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/sessions.js`.

#### US-SP-SESS-001

As a conversation owner, I want to search conversations by title and content.

- **Frontend steps:** Seed several chats; search by title and unique message text; clear search.
- **Persisted/read-back result:** Only matching authorized chats appear; clear restores the permitted list.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-002

As a conversation owner, I want to filter conversation sources.

- **Frontend steps:** Enable supported source categories; switch WebUI/CLI/messaging/cron filters; reload.
- **Persisted/read-back result:** The chosen filter restores where supported; unauthorized external sessions stay absent.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-003

As a conversation owner, I want to rename a conversation.

- **Frontend steps:** Open a fixture chat menu; Rename; save a unique name; reload.
- **Persisted/read-back result:** Only the intended conversation name changes.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-004

As a conversation owner, I want to pin and unpin within the limit.

- **Frontend steps:** Pin to the fixture limit; attempt one more; unpin; pin another.
- **Persisted/read-back result:** Pinned state persists and the limit is consistent without data loss.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-005

As a conversation owner, I want to archive and restore a conversation.

- **Frontend steps:** Archive a fixture chat; open archived list; restore it; reload.
- **Persisted/read-back result:** The chat moves between lists with history intact.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-006

As a conversation owner, I want to delete a conversation.

- **Frontend steps:** Delete a disposable fixture chat through confirmation; reload its old URL.
- **Persisted/read-back result:** The intended record disappears and cannot return from stale sidecar/cache state.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-007

As a conversation owner, I want to cancel destructive confirmation.

- **Frontend steps:** Open Delete; cancel; reload.
- **Persisted/read-back result:** The fixture chat and history remain unchanged.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-008

As a conversation owner, I want to duplicate a conversation.

- **Frontend steps:** Choose Duplicate on a seeded chat; open both; add a turn to the duplicate.
- **Persisted/read-back result:** The copy has its own identity and later messages do not alter the original.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-009

As a conversation owner, I want to copy an internal conversation link.

- **Frontend steps:** Choose Copy link; open the copied URL in a fresh same-user tab.
- **Persisted/read-back result:** The URL resolves to the intended permitted chat.
- **Permission negative:** An outsider using the same link is refused.
- **Required verification:** REAL_BROWSER; CLIPBOARD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-010

As a conversation owner, I want to create a public share.

- **Frontend steps:** Share a synthetic non-sensitive chat; open its link unsigned.
- **Persisted/read-back result:** Only the intended share snapshot is readable; private metadata/files are excluded.
- **Permission negative:** Unshared sessions and underlying private endpoints remain protected.
- **Required verification:** REAL_BROWSER; UNSIGNED_CONTEXT; PRIVACY_MARKERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **FAIL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-011

As a conversation owner, I want to revoke a public share.

- **Frontend steps:** Create a fixture share; revoke; reopen the old URL unsigned.
- **Persisted/read-back result:** The old share is unreadable after reload.
- **Permission negative:** A non-owner cannot create or revoke it.
- **Required verification:** REAL_BROWSER; RELOAD; UNSIGNED_CONTEXT; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-012

As a conversation owner, I want to export a chat as HTML.

- **Frontend steps:** Choose Export HTML; capture download; open the artifact.
- **Persisted/read-back result:** The file contains the selected authorized chat with safe rendering.
- **Permission negative:** Export cannot contain other-chat private markers.
- **Required verification:** REAL_BROWSER; DOWNLOAD_BYTES; HOSTILE_CONTENT; PRIVACY_MARKERS.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-013

As a conversation owner, I want to apply bulk session actions.

- **Frontend steps:** Select disposable chats; apply supported archive/project actions; reload.
- **Persisted/read-back result:** Exactly the selected permitted records change once.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-014

As a conversation owner, I want to assign a conversation to a project.

- **Frontend steps:** Open its project picker; choose a permitted project; reload list and project.
- **Persisted/read-back result:** The assignment persists under current participant/project access.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-015

As a conversation owner, I want to continue an imported external session.

- **Frontend steps:** Open a permitted external session; import/continue; send a fixture prompt.
- **Persisted/read-back result:** The import relationship and new WebUI activity have correct ownership.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-016

As a conversation owner, I want to inspect conversation lineage.

- **Frontend steps:** Expand seeded parent/child/fork groups; open children; return; reload.
- **Persisted/read-back result:** Links identify correct conversations without hiding active or exposing forbidden records.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SESS-017

As a conversation owner, I want to retain unread and completion state.

- **Frontend steps:** Complete a fixture run in a background chat; open it; reload.
- **Persisted/read-back result:** The intended indicator clears while other conversations retain correct state.
- **Permission negative:** An outsider cannot enumerate, mutate, export or share the conversation through UI, copied URLs or direct requests.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### GROUP — People, mentions and shared conversations

Persona: authorized team member. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `chat-experience-v2/browser_qa.cjs; September 6 chat-mentions release evidence`.

#### US-SP-GROUP-001

As an authorized team member, I want to open and close the people picker.

- **Frontend steps:** Click people; inspect private state; open/close with Cancel and Escape.
- **Persisted/read-back result:** The conversation stays private until an audience change is committed.
- **Permission negative:** Unknown users, non-members and revoked recipients cannot read/change the group, attachments or runtime context.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GROUP-002

As an authorized team member, I want to choose colleagues for a group.

- **Frontend steps:** Select two fixture colleagues in the people picker; save; send.
- **Persisted/read-back result:** Participants persist and permitted members can reopen the chat.
- **Permission negative:** Unknown users, non-members and revoked recipients cannot read/change the group, attachments or runtime context.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GROUP-003

As an authorized team member, I want to remove a group participant.

- **Frontend steps:** Remove Bob in audience controls; retain Bob's tab; attempt refresh/send.
- **Persisted/read-back result:** Bob loses chat, stream and file access despite retained cookies.
- **Permission negative:** Unknown users, non-members and revoked recipients cannot read/change the group, attachments or runtime context.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GROUP-004

As an authorized team member, I want to mention a person with keyboard.

- **Frontend steps:** Type @ and partial name; use arrows; confirm Enter.
- **Persisted/read-back result:** The canonical person is staged once with the supported mention representation.
- **Permission negative:** Unknown users, non-members and revoked recipients cannot read/change the group, attachments or runtime context.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GROUP-005

As an authorized team member, I want to mention a bot with touch.

- **Frontend steps:** At 390px type @; tap a bot; send.
- **Persisted/read-back result:** The literal selected bot receives the prompt and attribution survives reload.
- **Permission negative:** Unknown users, non-members and revoked recipients cannot read/change the group, attachments or runtime context.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GROUP-006

As an authorized team member, I want to distinguish identical friendly names.

- **Frontend steps:** Seed a person and bots with overlapping names; select each through labels; send.
- **Persisted/read-back result:** Canonical recipients match the selection; prefixes/punctuation do not misroute.
- **Permission negative:** Unknown users, non-members and revoked recipients cannot read/change the group, attachments or runtime context.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GROUP-007

As an authorized team member, I want to start a fresh group from private chat.

- **Frontend steps:** Seed private history/file/memory markers; mention a colleague from that chat; send.
- **Persisted/read-back result:** A fresh group excludes earlier private history, files, workspace and personal context.
- **Permission negative:** Unknown users, non-members and revoked recipients cannot read/change the group, attachments or runtime context.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GROUP-008

As an authorized team member, I want to select multiple mentioned bots.

- **Frontend steps:** Mention two permitted bots and a person; send; inspect roster/dispatch.
- **Persisted/read-back result:** Bots join the roster; only the documented initial recipient runs absent explicit parallel work.
- **Permission negative:** Unknown users, non-members and revoked recipients cannot read/change the group, attachments or runtime context.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GROUP-009

As an authorized team member, I want to preserve drafts during catalog failure.

- **Frontend steps:** Type mentions while people loading is delayed; fail it; retry.
- **Persisted/read-back result:** Bot discovery remains usable as designed; draft survives and unknown recipients cannot submit.
- **Permission negative:** Unknown users, non-members and revoked recipients cannot read/change the group, attachments or runtime context.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GROUP-010

As an authorized team member, I want to collapse and expand the roster.

- **Frontend steps:** Collapse; reload; expand; repeat in another account.
- **Persisted/read-back result:** The preference is scoped to the signed-in account.
- **Permission negative:** Unknown users, non-members and revoked recipients cannot read/change the group, attachments or runtime context.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GROUP-011

As an authorized team member, I want to download a group attachment.

- **Frontend steps:** Upload/send unique fixture bytes; download as another participant.
- **Persisted/read-back result:** Members receive the exact bytes.
- **Permission negative:** Outsider and a different private session cannot access its URL.
- **Required verification:** REAL_BROWSER; TWO_USERS; FILE_BYTES; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GROUP-012

As an authorized team member, I want to retain bot attribution after reload.

- **Frontend steps:** Send two group turns to a selected bot; reload; send another.
- **Persisted/read-back result:** Selected bot identity and message attribution remain correct.
- **Permission negative:** Unknown users, non-members and revoked recipients cannot read/change the group, attachments or runtime context.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### BOT — Bot creation and editing

Persona: authorized bot creator. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `bot-editor; chat-experience-v2/server_fixture.py; September 6 bot-editor release evidence`.

#### US-SP-BOT-001

As an authorized bot creator, I want to create a bot through the wizard.

- **Frontend steps:** Open Bots > Create; complete every step; inspect Review; final Save.
- **Persisted/read-back result:** One correctly configured bot persists; no create request occurs before final Save.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-002

As an authorized bot creator, I want to cancel bot creation.

- **Frontend steps:** Start Create; fill two steps; cancel; reopen list.
- **Persisted/read-back result:** No partial published bot/runtime profile remains.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-003

As an authorized bot creator, I want to move Back and Continue without draft loss.

- **Frontend steps:** Fill all steps; navigate Back/Continue; inspect Review.
- **Persisted/read-back result:** All edits remain on this draft and navigation does not double-submit.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-004

As an authorized bot creator, I want to open all existing-bot tabs.

- **Frontend steps:** Open Bot A > Edit bot; click all six tabs; exercise each section deep link.
- **Persisted/read-back result:** Each opens its requested section and Bot B is unchanged.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-005

As an authorized bot creator, I want to save from any editor tab.

- **Frontend steps:** Change a field; switch tabs; Save bot; reload.
- **Persisted/read-back result:** All intended edits persist once from the active tab.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-006

As an authorized bot creator, I want to edit bot instructions.

- **Frontend steps:** Replace instructions; save; start a bot conversation; send a probe.
- **Persisted/read-back result:** Saved instructions reach the real worker/provider request.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-007

As an authorized bot creator, I want to select skill CLI and MCP capabilities.

- **Frontend steps:** Select permitted fixtures; remove one; save/reload; run corresponding governed tools.
- **Persisted/read-back result:** Selection persists and runtime intersects bot ceiling with caller rights.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-008

As an authorized bot creator, I want to preserve large legacy selections.

- **Frontend steps:** Load 554 skills, 154 CLI tools and 13 MCP entries; edit description; save/reload.
- **Persisted/read-back result:** Valid unchanged selections survive without a 100-item rejection.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-009

As an authorized bot creator, I want to preserve unchanged model during discovery failure.

- **Frontend steps:** Make discovery unavailable; edit an unrelated field; save the bot.
- **Persisted/read-back result:** The unchanged permitted pair survives; an unavailable new pair is refused.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-010

As an authorized bot creator, I want to assign users and groups.

- **Frontend steps:** Add fixture user/group; save; run as member; remove membership; retry.
- **Persisted/read-back result:** Members can run; revoked members lose list/avatar/builder/chat access.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-011

As an authorized bot creator, I want to upload and reset a bot photo.

- **Frontend steps:** Upload known PNG; save/reload; inspect roster/chat; use supported reset.
- **Persisted/read-back result:** Correct image/dimensions persist; reset leaves other bots unchanged.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-012

As an authorized bot creator, I want to handle stale edits.

- **Frontend steps:** Edit one bot in two tabs; save A; submit stale B; reload.
- **Persisted/read-back result:** A visible conflict protects the newer revision.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-013

As an authorized bot creator, I want to ignore a late save after navigation.

- **Frontend steps:** Delay save; navigate to Bot B or another panel; complete response.
- **Persisted/read-back result:** The old response cannot reclaim the panel or contaminate Bot B.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-BOT-014

As an authorized bot creator, I want to delete a disposable owned bot.

- **Frontend steps:** Delete a synthetic owned bot through confirmation; reopen direct link.
- **Persisted/read-back result:** Only the intended bot becomes unavailable.
- **Permission negative:** A member without management rights cannot edit/clone/delete/widen the bot; a creator cannot select capabilities outside current grants.
- **Required verification:** REAL_BROWSER; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

### KNOW — Bot knowledge and shared memory

Persona: bot owner. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `bot-editor/knowledge_qa.cjs; bot-editor/knowledge_lifecycle.cjs; bot-knowledge`.

#### US-SP-KNOW-001

As a bot owner, I want to upload without implicit selection.

- **Frontend steps:** Open Memory & knowledge; choose two real fixture files; upload.
- **Persisted/read-back result:** Both enter this bot's catalog and remain unselected until explicitly saved.
- **Permission negative:** Other owners/members cannot manage this catalog; selected knowledge does not bypass caller file/tool permissions.
- **Required verification:** REAL_BROWSER; TWO_BOTS; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-KNOW-002

As a bot owner, I want to search the catalog.

- **Frontend steps:** Upload distinct names; search partial name; clear.
- **Persisted/read-back result:** Matching rows appear; hidden selections remain preserved.
- **Permission negative:** Other owners/members cannot manage this catalog; selected knowledge does not bypass caller file/tool permissions.
- **Required verification:** REAL_BROWSER; TWO_BOTS; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KNOW-003

As a bot owner, I want to select and explicitly save knowledge.

- **Frontend steps:** Check one uploaded file; Save knowledge; reload.
- **Persisted/read-back result:** Exactly the selected reference persists for this bot.
- **Permission negative:** Other owners/members cannot manage this catalog; selected knowledge does not bypass caller file/tool permissions.
- **Required verification:** REAL_BROWSER; TWO_BOTS; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-KNOW-004

As a bot owner, I want to deselect knowledge.

- **Frontend steps:** Uncheck; Save knowledge; reload; request fixture knowledge.
- **Persisted/read-back result:** The removed reference is absent from selected runtime knowledge.
- **Permission negative:** Other owners/members cannot manage this catalog; selected knowledge does not bypass caller file/tool permissions.
- **Required verification:** REAL_BROWSER; TWO_BOTS; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KNOW-005

As a bot owner, I want to separate bot catalogs.

- **Frontend steps:** Upload unique file to Bot A; open Bot B and search for it.
- **Persisted/read-back result:** Bot B cannot enumerate or inherit Bot A's private catalog.
- **Permission negative:** Other owners/members cannot manage this catalog; selected knowledge does not bypass caller file/tool permissions.
- **Required verification:** REAL_BROWSER; TWO_BOTS; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KNOW-006

As a bot owner, I want to reject forged paths and selections.

- **Frontend steps:** Select valid file in UI; run forged-ID, encoded traversal and symlink negative probes.
- **Persisted/read-back result:** Invalid references fail clearly and no cross-root file opens.
- **Permission negative:** Other owners/members cannot manage this catalog; selected knowledge does not bypass caller file/tool permissions.
- **Required verification:** REAL_BROWSER; TWO_BOTS; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KNOW-007

As a bot owner, I want to enforce runtime read roots.

- **Frontend steps:** Select document; request it with matching root then unrelated-root actor.
- **Persisted/read-back result:** Only the permitted actor obtains the fixture bytes.
- **Permission negative:** Other owners/members cannot manage this catalog; selected knowledge does not bypass caller file/tool permissions.
- **Required verification:** REAL_BROWSER; TWO_BOTS; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KNOW-008

As a bot owner, I want to handle stale knowledge revisions.

- **Frontend steps:** Open selection in two tabs; save A; submit stale B; reload.
- **Persisted/read-back result:** The newer selection survives with a visible conflict.
- **Permission negative:** Other owners/members cannot manage this catalog; selected knowledge does not bypass caller file/tool permissions.
- **Required verification:** REAL_BROWSER; TWO_BOTS; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KNOW-009

As a bot owner, I want to edit shared bot memory.

- **Frontend steps:** Save a shared marker; run as authorized member; reload.
- **Persisted/read-back result:** The marker persists only in bot shared scope and authorized contexts.
- **Permission negative:** Other owners/members cannot manage this catalog; selected knowledge does not bypass caller file/tool permissions.
- **Required verification:** REAL_BROWSER; TWO_BOTS; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-KNOW-010

As a bot owner, I want to preserve private legacy memory.

- **Frontend steps:** Seed personal USER.md/MEMORY.md sentinels; save bot knowledge/shared memory; inspect authorized evidence.
- **Persisted/read-back result:** Private sentinels stay unchanged and absent from shared prompts.
- **Permission negative:** Unauthorized/revoked actors receive no shared or private markers.
- **Required verification:** REAL_BROWSER; PRIVACY_MARKERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### MEM — Personal memory and external notes

Persona: signed-in user. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/panels.js; September 6 personal-memory release evidence`.

#### US-SP-MEM-001

As a signed-in user, I want to open all personal memory sections.

- **Frontend steps:** Open Memory; click all four sections on desktop/mobile.
- **Persisted/read-back result:** Each shows only this user's content with correct empty states.
- **Permission negative:** Another user cannot read/write this user's personal sections by spoofing body, query, path or session identity.
- **Required verification:** REAL_BROWSER; TWO_USERS; PRIVACY_MARKERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-MEM-002

As a signed-in user, I want to save a personal section.

- **Frontend steps:** Edit one section; enter a unique marker; Save; reload.
- **Persisted/read-back result:** The marker persists only in this user's chosen section.
- **Permission negative:** Another user cannot read/write this user's personal sections by spoofing body, query, path or session identity.
- **Required verification:** REAL_BROWSER; TWO_USERS; PRIVACY_MARKERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-MEM-003

As a signed-in user, I want to cancel a memory edit.

- **Frontend steps:** Change content; Cancel; reload.
- **Persisted/read-back result:** Previously saved content is unchanged.
- **Permission negative:** Another user cannot read/write this user's personal sections by spoofing body, query, path or session identity.
- **Required verification:** REAL_BROWSER; TWO_USERS; PRIVACY_MARKERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-MEM-004

As a signed-in user, I want to exclude personal context from shared chat.

- **Frontend steps:** Save Alice/Bob private markers; run personal and group prompts.
- **Persisted/read-back result:** Private turns get only allowed caller context; group prompts contain neither marker.
- **Permission negative:** Another user cannot read/write this user's personal sections by spoofing body, query, path or session identity.
- **Required verification:** REAL_BROWSER; TWO_USERS; PRIVACY_MARKERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-MEM-005

As a signed-in user, I want to browse connected notes sources.

- **Frontend steps:** Open notes sources; select fixture source; inspect disconnected/loading states.
- **Persisted/read-back result:** The selected source is correct; inaccessible content is labeled unavailable.
- **Permission negative:** Without the source grant no note metadata/content is returned.
- **Required verification:** REAL_BROWSER; CONNECTOR_FIXTURE; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-MEM-006

As a signed-in user, I want to search and preview notes.

- **Frontend steps:** Select permitted source; query a unique note; open preview.
- **Persisted/read-back result:** Results match the selected authorized source/query.
- **Permission negative:** Another user cannot read/write this user's personal sections by spoofing body, query, path or session identity.
- **Required verification:** REAL_BROWSER; TWO_USERS; PRIVACY_MARKERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-MEM-007

As a signed-in user, I want to ignore results from a previous source.

- **Frontend steps:** Delay source A search; switch to B; complete A.
- **Persisted/read-back result:** A's content cannot replace B's current view.
- **Permission negative:** Another user cannot read/write this user's personal sections by spoofing body, query, path or session identity.
- **Required verification:** REAL_BROWSER; TWO_USERS; PRIVACY_MARKERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-MEM-008

As a signed-in user, I want to recover a failed memory save.

- **Frontend steps:** Edit; fail save; inspect draft; retry after recovery.
- **Persisted/read-back result:** Failure is visible, the draft survives and successful revision persists once.
- **Permission negative:** Another user cannot read/write this user's personal sections by spoofing body, query, path or session identity.
- **Required verification:** REAL_BROWSER; TWO_USERS; PRIVACY_MARKERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### PROJ — Projects and collaboration

Persona: project owner or member. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/projects.js; projects-groups; September 6 project collaboration release evidence`.

#### US-SP-PROJ-001

As a project owner or member, I want to create a project.

- **Frontend steps:** Open Projects; Create; enter a unique name; save; reload.
- **Persisted/read-back result:** One owned project appears with the chosen name and supported default state.
- **Permission negative:** A non-member or revoked member cannot obtain project files, chats, metadata or existing streams; project membership does not grant extra bot/CLI rights.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PROJ-002

As a project owner or member, I want to rename a project.

- **Frontend steps:** Open a disposable project; Edit/Rename; save; reload.
- **Persisted/read-back result:** Only that project's name changes.
- **Permission negative:** A non-member or revoked member cannot obtain project files, chats, metadata or existing streams; project membership does not grant extra bot/CLI rights.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PROJ-003

As a project owner or member, I want to render hostile project names safely.

- **Frontend steps:** Create a fixture name containing HTML-like text; open list/detail and selectors.
- **Persisted/read-back result:** The exact text is readable without executing markup or scripts.
- **Permission negative:** A denied user cannot use search/preview to read the name.
- **Required verification:** REAL_BROWSER; HOSTILE_CONTENT; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PROJ-004

As a project owner or member, I want to assign project members.

- **Frontend steps:** Open project members; add Alice/Bob; save; open as each user.
- **Persisted/read-back result:** The permitted roster persists and members see this project.
- **Permission negative:** A non-member or revoked member cannot obtain project files, chats, metadata or existing streams; project membership does not grant extra bot/CLI rights.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PROJ-005

As a project owner or member, I want to assign project bots.

- **Frontend steps:** Select two allowed bots in project controls; save; open a project chat and choose each.
- **Persisted/read-back result:** The assigned bot roster persists and dispatch obeys both project and bot permissions.
- **Permission negative:** A non-member or revoked member cannot obtain project files, chats, metadata or existing streams; project membership does not grant extra bot/CLI rights.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PROJ-006

As a project owner or member, I want to upload and download project files.

- **Frontend steps:** Upload unique synthetic bytes in project files; reopen; download as another member.
- **Persisted/read-back result:** The same file name and exact bytes persist and are shared only with permitted members.
- **Permission negative:** A non-member or revoked member cannot obtain project files, chats, metadata or existing streams; project membership does not grant extra bot/CLI rights.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PROJ-007

As a project owner or member, I want to reject duplicate and oversized project uploads.

- **Frontend steps:** Upload the same name twice and a file beyond the advertised limit.
- **Persisted/read-back result:** The UI reports each conflict/limit and never silently overwrites existing bytes.
- **Permission negative:** A non-member or revoked member cannot obtain project files, chats, metadata or existing streams; project membership does not grant extra bot/CLI rights.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PROJ-008

As a project owner or member, I want to create a project conversation.

- **Frontend steps:** Use project New conversation; send a fixture prompt; reopen from project and Chats.
- **Persisted/read-back result:** Project/workspace association and conversation ownership persist.
- **Permission negative:** A non-member or revoked member cannot obtain project files, chats, metadata or existing streams; project membership does not grant extra bot/CLI rights.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PROJ-009

As a project owner or member, I want to revoke a project member.

- **Frontend steps:** Remove Bob; retain Bob's tabs and URLs; attempt file, chat, stream and list access.
- **Persisted/read-back result:** Access is immediately denied across all routes without requiring logout.
- **Permission negative:** A non-member or revoked member cannot obtain project files, chats, metadata or existing streams; project membership does not grant extra bot/CLI rights.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PROJ-010

As a project owner or member, I want to label unavailable project sources honestly.

- **Frontend steps:** Open project detail with some sources disconnected or forbidden; refresh.
- **Persisted/read-back result:** Each source is accurately available/unavailable; a missing response is not represented as zero activity.
- **Permission negative:** A non-member or revoked member cannot obtain project files, chats, metadata or existing streams; project membership does not grant extra bot/CLI rights.
- **Required verification:** REAL_BROWSER; TWO_USERS; TWO_BOTS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### FILE — File tree, previews and transfers

Persona: authorized workspace user. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/workspace.js; static/index.html`.

#### US-SP-FILE-001

As an authorized workspace user, I want to navigate the file tree.

- **Frontend steps:** Open Files; expand two directories; navigate breadcrumbs/up; refresh.
- **Persisted/read-back result:** Correct directory contents appear; supported expansion state restores without crossing roots.
- **Permission negative:** Unpermitted roots, encoded traversal, symlinks and cross-session URLs cannot expose or overwrite protected files.
- **Required verification:** REAL_BROWSER; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-002

As an authorized workspace user, I want to preview text and code.

- **Frontend steps:** Open fixture text/code files; inspect highlighting; copy relative path.
- **Persisted/read-back result:** Displayed content/path match the selected authorized file; no write occurs.
- **Permission negative:** Unpermitted roots, encoded traversal, symlinks and cross-session URLs cannot expose or overwrite protected files.
- **Required verification:** REAL_BROWSER; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-003

As an authorized workspace user, I want to preview Markdown safely.

- **Frontend steps:** Open Markdown with links, code and hostile HTML; use supported preview controls.
- **Persisted/read-back result:** Supported content renders while hostile content stays inert.
- **Permission negative:** Protected links and images cannot bypass file authorization.
- **Required verification:** REAL_BROWSER; HOSTILE_CONTENT; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-004

As an authorized workspace user, I want to preview CSV and structured data.

- **Frontend steps:** Open a CSV with quotes/newlines and a JSON file; inspect rows/content.
- **Persisted/read-back result:** The preview preserves the fixture structure without truncation disguised as completeness.
- **Permission negative:** Unpermitted roots, encoded traversal, symlinks and cross-session URLs cannot expose or overwrite protected files.
- **Required verification:** REAL_BROWSER; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-005

As an authorized workspace user, I want to handle large Markdown fallback.

- **Frontend steps:** Open a file over preview limits; inspect plain-text fallback; click explicit render control.
- **Persisted/read-back result:** The size warning is honest and explicit rendering does not freeze navigation.
- **Permission negative:** Unpermitted roots, encoded traversal, symlinks and cross-session URLs cannot expose or overwrite protected files.
- **Required verification:** REAL_BROWSER; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-006

As an authorized workspace user, I want to edit and save a file.

- **Frontend steps:** Open editable fixture file; Edit; change bytes; Save; reopen and download.
- **Persisted/read-back result:** The intended file bytes persist and the downloaded file matches.
- **Permission negative:** Unpermitted roots, encoded traversal, symlinks and cross-session URLs cannot expose or overwrite protected files.
- **Required verification:** REAL_BROWSER; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-007

As an authorized workspace user, I want to cancel a file edit.

- **Frontend steps:** Change an editable fixture; Cancel; reopen.
- **Persisted/read-back result:** Original bytes remain unchanged.
- **Permission negative:** Unpermitted roots, encoded traversal, symlinks and cross-session URLs cannot expose or overwrite protected files.
- **Required verification:** REAL_BROWSER; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-008

As an authorized workspace user, I want to upload with the file picker.

- **Frontend steps:** Open target directory; activate Upload; choose known bytes; reopen/download.
- **Persisted/read-back result:** The chosen directory receives exactly the intended file and bytes.
- **Permission negative:** Unpermitted roots, encoded traversal, symlinks and cross-session URLs cannot expose or overwrite protected files.
- **Required verification:** REAL_BROWSER; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-009

As an authorized workspace user, I want to upload by drag and drop.

- **Frontend steps:** Drop multiple fixture files and a supported directory tree on the file pane.
- **Persisted/read-back result:** The supported relative hierarchy and exact bytes persist; invalid entries report failure.
- **Permission negative:** Unpermitted roots, encoded traversal, symlinks and cross-session URLs cannot expose or overwrite protected files.
- **Required verification:** REAL_BROWSER; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-010

As an authorized workspace user, I want to download a file.

- **Frontend steps:** Click Download for a binary fixture; capture the browser download.
- **Persisted/read-back result:** Name and bytes match the authorized source without content from another path.
- **Permission negative:** Unpermitted roots, encoded traversal, symlinks and cross-session URLs cannot expose or overwrite protected files.
- **Required verification:** REAL_BROWSER; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-011

As an authorized workspace user, I want to open an HTML artifact in the browser.

- **Frontend steps:** Select a synthetic HTML artifact; use Open in browser; inspect its URL and rendering.
- **Persisted/read-back result:** Only the intended artifact opens under the supported origin/sandbox behavior.
- **Permission negative:** An unauthorized actor cannot read it via direct preview/media URL.
- **Required verification:** REAL_BROWSER; HOSTILE_CONTENT; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-012

As an authorized workspace user, I want to refresh a preview after an agent write.

- **Frontend steps:** Open a fixture file preview; run an authorized tool that modifies it; observe/reopen.
- **Persisted/read-back result:** The preview reflects final stored bytes and stale events from another session cannot replace it.
- **Permission negative:** Unpermitted roots, encoded traversal, symlinks and cross-session URLs cannot expose or overwrite protected files.
- **Required verification:** REAL_BROWSER; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-FILE-013

As an authorized workspace user, I want to recover from a denied or missing file.

- **Frontend steps:** Open a stale/deleted/denied path; then navigate to a valid file.
- **Persisted/read-back result:** Error is explicit; no stale protected preview remains and navigation recovers.
- **Permission negative:** Unpermitted roots, encoded traversal, symlinks and cross-session URLs cannot expose or overwrite protected files.
- **Required verification:** REAL_BROWSER; FILE_BYTES; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### WS — Workspaces and assignment

Persona: authorized workspace administrator. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/panels.js; static/workspace.js; static/governance.js`.

#### US-SP-WS-001

As an authorized workspace administrator, I want to create a workspace.

- **Frontend steps:** Open Spaces/Workspaces; Create; enter fixture name/path; save; reload.
- **Persisted/read-back result:** The definition persists and resolves only to the permitted fixture directory.
- **Permission negative:** Workspace assignment does not grant outside-root access; non-admins cannot change other users or protected workspace definitions.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-WS-002

As an authorized workspace administrator, I want to use workspace path suggestions.

- **Frontend steps:** Type a partial allowed path; choose a suggestion by keyboard/touch.
- **Persisted/read-back result:** The chosen path is exact and unauthorized paths are not disclosed.
- **Permission negative:** Workspace assignment does not grant outside-root access; non-admins cannot change other users or protected workspace definitions.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-WS-003

As an authorized workspace administrator, I want to edit a workspace.

- **Frontend steps:** Open workspace detail; Edit; change permitted metadata; save/reload.
- **Persisted/read-back result:** Only that definition changes and existing session bindings follow the documented contract.
- **Permission negative:** Workspace assignment does not grant outside-root access; non-admins cannot change other users or protected workspace definitions.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-WS-004

As an authorized workspace administrator, I want to activate a workspace.

- **Frontend steps:** Select a workspace in panel and composer; start a fixture chat.
- **Persisted/read-back result:** The active workspace cue and actual worker directory agree.
- **Permission negative:** Workspace assignment does not grant outside-root access; non-admins cannot change other users or protected workspace definitions.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-WS-005

As an authorized workspace administrator, I want to switch with fresh-chat preference enabled.

- **Frontend steps:** Enable new chat on workspace switch; switch from A to B.
- **Persisted/read-back result:** A fresh conversation binds to B while the old chat stays bound to A.
- **Permission negative:** Workspace assignment does not grant outside-root access; non-admins cannot change other users or protected workspace definitions.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-WS-006

As an authorized workspace administrator, I want to switch with in-place preference.

- **Frontend steps:** Disable fresh-chat preference; switch from A to B in a disposable chat; reload.
- **Persisted/read-back result:** The current conversation adopts B according to the documented setting without stale A file context.
- **Permission negative:** Workspace assignment does not grant outside-root access; non-admins cannot change other users or protected workspace definitions.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-WS-007

As an authorized workspace administrator, I want to assign and remove members.

- **Frontend steps:** Edit workspace assignments; add Bob; save; remove Bob with his tab retained.
- **Persisted/read-back result:** Membership persists and revocation immediately affects UI, file routes and runtime.
- **Permission negative:** Workspace assignment does not grant outside-root access; non-admins cannot change other users or protected workspace definitions.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-WS-008

As an authorized workspace administrator, I want to remove a workspace definition.

- **Frontend steps:** Delete a disposable workspace through confirmation; reload.
- **Persisted/read-back result:** Only the definition is removed unless the UI explicitly promises file deletion; fixture bytes are inspected separately.
- **Permission negative:** Workspace assignment does not grant outside-root access; non-admins cannot change other users or protected workspace definitions.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### CRON — Scheduled tasks and run history

Persona: authorized scheduling user. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/panels.js (cron controls)`.

#### US-SP-CRON-001

As an authorized scheduling user, I want to browse tasks and profile filters.

- **Frontend steps:** Open Scheduled tasks; select profile filters; open two job details; refresh.
- **Persisted/read-back result:** Only permitted jobs/details appear and the selected detail stays aligned with its profile.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-002

As an authorized scheduling user, I want to create a one-time task.

- **Frontend steps:** Create a fixture task; enter prompt and one-time schedule; review preview; save/reload.
- **Persisted/read-back result:** The exact intended execution time and prompt persist with correct ownership.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-003

As an authorized scheduling user, I want to create a recurring task from a preset.

- **Frontend steps:** Choose a recurrence preset; edit its visible fields; review schedule preview; save.
- **Persisted/read-back result:** Stored recurrence matches the displayed plan and no duplicate job is created.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-004

As an authorized scheduling user, I want to validate custom schedule and time zone.

- **Frontend steps:** Enter valid/invalid custom schedules and a daylight-saving edge fixture; inspect preview/errors.
- **Persisted/read-back result:** Invalid schedules are refused and valid next-run times match the documented time-zone semantics.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-005

As an authorized scheduling user, I want to select model bot and skills.

- **Frontend steps:** Create/edit a job; select allowed profile/model/skills; save; run synthetically.
- **Persisted/read-back result:** Stored selections reach actual worker dispatch with current permission checks.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-006

As an authorized scheduling user, I want to choose a delivery destination.

- **Frontend steps:** Open delivery options; choose a synthetic sink; save; execute a fixture run.
- **Persisted/read-back result:** Output reaches only the selected fixture sink with matching job identity.
- **Permission negative:** An unauthorized external target is refused even when submitted directly.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DELIVERY_SINK; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-007

As an authorized scheduling user, I want to cancel task creation or editing.

- **Frontend steps:** Change a disposable form; Cancel; reload details.
- **Persisted/read-back result:** No job is created or altered.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-008

As an authorized scheduling user, I want to edit an existing task.

- **Frontend steps:** Change a fixture prompt/schedule; save; reopen.
- **Persisted/read-back result:** The intended job revision persists without duplicating or changing another profile's job.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-009

As an authorized scheduling user, I want to duplicate a task.

- **Frontend steps:** Use Duplicate on a seeded task; alter name/prompt; save.
- **Persisted/read-back result:** A separate owned job is created; future edits do not alter the original.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-010

As an authorized scheduling user, I want to pause and resume a task.

- **Frontend steps:** Pause a due fixture job; verify no run; Resume; advance fixture scheduler.
- **Persisted/read-back result:** Paused state persists and resumption schedules only the expected run.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-011

As an authorized scheduling user, I want to run a task now.

- **Frontend steps:** Click Run on a synthetic local-only job; inspect running state, output and completion.
- **Persisted/read-back result:** One actual run is recorded and the output/usage belong to that run.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-012

As an authorized scheduling user, I want to inspect and expand run history.

- **Frontend steps:** Open a task with multiple runs; expand prompts/results; open old run content.
- **Persisted/read-back result:** Each history row renders the correct persisted run and not a neighboring profile's output.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-013

As an authorized scheduling user, I want to inspect failure diagnostics.

- **Frontend steps:** Run a fixture failure; open its attention state; Copy diagnostics.
- **Persisted/read-back result:** Failure remains visible and copied diagnostics omit secrets while naming the failed run.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CRON-014

As an authorized scheduling user, I want to delete a disposable scheduled task.

- **Frontend steps:** Delete through confirmation; reload; advance scheduler past its due time.
- **Persisted/read-back result:** The intended job is absent and cannot execute after deletion.
- **Permission negative:** Without cron permission users cannot inspect/mutate jobs or invoke their bot, tool, model or delivery targets; scheduled execution retains creator constraints.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

### KAN — Kanban boards, tasks and orchestration

Persona: authorized board user. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/panels.js (kanban controls)`.

#### US-SP-KAN-001

As an authorized board user, I want to switch board and list views.

- **Frontend steps:** Open Kanban; toggle supported views; reload.
- **Persisted/read-back result:** The same authorized tasks appear and view preference persists where documented.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-002

As an authorized board user, I want to filter and clear board tasks.

- **Frontend steps:** Select profile/status/tenant filters; search; clear filters.
- **Persisted/read-back result:** Only intended tasks appear; empty-by-filter differs from an empty board.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-003

As an authorized board user, I want to create a task.

- **Frontend steps:** Open Create task; enter title/body/assignee/workspace; save/reload.
- **Persisted/read-back result:** One task with the selected permitted values persists.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-004

As an authorized board user, I want to edit a task.

- **Frontend steps:** Open fixture task; edit supported fields; save/reopen.
- **Persisted/read-back result:** Only the intended task changes.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-005

As an authorized board user, I want to cancel task edits and trap focus.

- **Frontend steps:** Open task modal; Tab/Shift+Tab through it; change fields; Escape/Cancel.
- **Persisted/read-back result:** Focus stays in the modal while open, returns on close and edits are discarded.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-006

As an authorized board user, I want to move a task by drag and drop.

- **Frontend steps:** Drag a fixture card to a permitted column; reload.
- **Persisted/read-back result:** The backend status and rendered column agree.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-007

As an authorized board user, I want to use quick card actions.

- **Frontend steps:** Use a supported start/complete/attention quick action on a fixture card.
- **Persisted/read-back result:** The authorized transition persists once with its event history.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **FAIL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-008

As an authorized board user, I want to block and unblock a task.

- **Frontend steps:** Open task detail; Block with reason; inspect; Unblock.
- **Persisted/read-back result:** Block state/reason and subsequent transition are durable and truthful.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-009

As an authorized board user, I want to apply bulk updates.

- **Frontend steps:** Select multiple fixture tasks; apply a supported bulk change.
- **Persisted/read-back result:** Only selected permitted tasks change; per-item failures remain visible.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-010

As an authorized board user, I want to add comments.

- **Frontend steps:** Open a task; add a synthetic comment; reload.
- **Persisted/read-back result:** The comment persists with correct author and safe rendering.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-011

As an authorized board user, I want to add and remove dependencies.

- **Frontend steps:** Link task A to B; inspect both; attempt a cycle if supported; remove link.
- **Persisted/read-back result:** Valid relationships persist; invalid cycles are refused; removal affects only the chosen edge.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-012

As an authorized board user, I want to inspect task events and runs.

- **Frontend steps:** Open a seeded task; inspect metadata, events and run links.
- **Persisted/read-back result:** Events/results belong to that task and timestamps/status are coherent.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-013

As an authorized board user, I want to create and rename a board.

- **Frontend steps:** Open board menu; Create; save; Rename; reload.
- **Persisted/read-back result:** Board identity remains stable while the new name persists.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-014

As an authorized board user, I want to archive a board.

- **Frontend steps:** Archive a disposable board through its UI; reload board list.
- **Persisted/read-back result:** The board is archived under the documented behavior without exposing or deleting unrelated tasks.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-015

As an authorized board user, I want to run the dispatcher.

- **Frontend steps:** On a synthetic isolated board, activate Run dispatcher; inspect result and spawned runs.
- **Persisted/read-back result:** Eligible permitted work dispatches once and failures are accurately counted.
- **Permission negative:** A non-elevated user cannot dispatch restricted jobs; board membership alone is insufficient.
- **Required verification:** REAL_BROWSER; ISOLATED_SCHEDULER; DETERMINISTIC_PROVIDER; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-016

As an authorized board user, I want to nudge the dispatcher.

- **Frontend steps:** Activate Nudge for an isolated eligible fixture task; inspect events/runs.
- **Persisted/read-back result:** The nudge is acknowledged once and does not duplicate active work.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-KAN-017

As an authorized board user, I want to recover from unavailable or stale board services.

- **Frontend steps:** Make the fixture board endpoint fail/stale; open board; use displayed refresh/reload recovery.
- **Persisted/read-back result:** Failure is explicit and recovery restores current tasks without reporting stale data as fresh.
- **Permission negative:** Users without board/task permission cannot read or mutate the board, trigger dispatch or inherit another tenant/workspace authority.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### TODO — Session task list

Persona: authorized chat user. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/panels.js loadTodos; static/workspace.js workspace Todos`.

#### US-SP-TODO-001

As an authorized chat user, I want to inspect tasks generated by a run.

- **Frontend steps:** Run a deterministic task-list fixture; open the left Todos panel.
- **Persisted/read-back result:** The actual session task states render with correct titles/order.
- **Permission negative:** Another session or user cannot read this task list through copied session IDs or workspace routes.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-TODO-002

As an authorized chat user, I want to open the workspace Todos tab.

- **Frontend steps:** Enable the workspace Todos setting; open right pane; select Todos.
- **Persisted/read-back result:** The same authorized session list is shown without mixing another workspace.
- **Permission negative:** Another session or user cannot read this task list through copied session IDs or workspace routes.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-TODO-003

As an authorized chat user, I want to see task state update and survive reload.

- **Frontend steps:** Run a fixture that moves a task to complete; observe list; reload.
- **Persisted/read-back result:** Only the actual completed task changes and persisted state matches runtime output.
- **Permission negative:** Another session or user cannot read this task list through copied session IDs or workspace routes.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-TODO-004

As an authorized chat user, I want to handle empty or legacy task state.

- **Frontend steps:** Open empty and legacy seeded conversations; inspect Todos.
- **Persisted/read-back result:** Empty/fallback states are honest and do not invent actionable tasks.
- **Permission negative:** Another session or user cannot read this task list through copied session IDs or workspace routes.
- **Required verification:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

### SKILL — Skills library and management

Persona: authorized skill user or manager. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/panels.js (skills controls)`.

#### US-SP-SKILL-001

As an authorized skill user or manager, I want to browse search and expand skill categories.

- **Frontend steps:** Open Skills; expand/collapse categories; search fixture name; clear.
- **Persisted/read-back result:** Only permitted skills appear and filters restore the right catalog.
- **Permission negative:** Missing skill view/load/manage grants deny both UI operations and direct/runtime access; viewing a skill does not imply permission to load it.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SKILL-002

As an authorized skill user or manager, I want to open a skill and its files.

- **Frontend steps:** Select a fixture skill; open supported linked files.
- **Persisted/read-back result:** Correct content renders without exposing files outside the allowed skill root.
- **Permission negative:** Missing skill view/load/manage grants deny both UI operations and direct/runtime access; viewing a skill does not imply permission to load it.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SKILL-003

As an authorized skill user or manager, I want to create a synthetic skill.

- **Frontend steps:** As manager choose Create; enter supported name/description/body; Save; reopen.
- **Persisted/read-back result:** A valid skill persists in the fixture skill root.
- **Permission negative:** Missing skill view/load/manage grants deny both UI operations and direct/runtime access; viewing a skill does not imply permission to load it.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SKILL-004

As an authorized skill user or manager, I want to edit a skill.

- **Frontend steps:** Open a managed fixture skill; Edit; change body; Save; reload.
- **Persisted/read-back result:** The selected skill revision changes and other skills remain intact.
- **Permission negative:** Missing skill view/load/manage grants deny both UI operations and direct/runtime access; viewing a skill does not imply permission to load it.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SKILL-005

As an authorized skill user or manager, I want to cancel a skill edit.

- **Frontend steps:** Change content; Cancel; reopen.
- **Persisted/read-back result:** Original skill bytes are preserved.
- **Permission negative:** Missing skill view/load/manage grants deny both UI operations and direct/runtime access; viewing a skill does not imply permission to load it.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SKILL-006

As an authorized skill user or manager, I want to enable or load a skill for a bot/chat.

- **Frontend steps:** Toggle/select an allowed skill; run a fixture invocation.
- **Persisted/read-back result:** The intended skill reaches runtime only when both caller and bot allow it.
- **Permission negative:** Missing skill view/load/manage grants deny both UI operations and direct/runtime access; viewing a skill does not imply permission to load it.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SKILL-007

As an authorized skill user or manager, I want to delete a managed skill.

- **Frontend steps:** Delete only a disposable fixture skill through confirmation; refresh catalog.
- **Persisted/read-back result:** The chosen skill is removed and cannot load via a stale selector.
- **Permission negative:** Missing skill view/load/manage grants deny both UI operations and direct/runtime access; viewing a skill does not imply permission to load it.
- **Required verification:** REAL_BROWSER; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SKILL-008

As an authorized skill user or manager, I want to render hostile skill content.

- **Frontend steps:** Open a skill with Markdown links and HTML-like hostile text.
- **Persisted/read-back result:** Supported documentation is readable and active markup stays inert.
- **Permission negative:** Protected linked files cannot bypass root restrictions.
- **Required verification:** REAL_BROWSER; HOSTILE_CONTENT; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### CONN — Connections catalog and account ownership

Persona: authorized connections user. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/integrations.js`.

#### US-SP-CONN-001

As an authorized connections user, I want to browse and filter service catalog.

- **Frontend steps:** Open Connections; choose category; search name; clear filters.
- **Persisted/read-back result:** Only available/permitted entries appear with correct auth/connect status.
- **Permission negative:** Users cannot view/disconnect another account, self-enable restricted providers or bypass connection and runtime grants through an existing connection ID.
- **Required verification:** REAL_BROWSER; CONNECTOR_FIXTURE; TWO_USERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-CONN-002

As an authorized connections user, I want to request a restricted service.

- **Frontend steps:** Open an ungranted fixture provider; Request access; inspect My approvals.
- **Persisted/read-back result:** One pending request is stored with correct caller/provider and no implicit grant.
- **Permission negative:** Users cannot view/disconnect another account, self-enable restricted providers or bypass connection and runtime grants through an existing connection ID.
- **Required verification:** REAL_BROWSER; CONNECTOR_FIXTURE; TWO_USERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CONN-003

As an authorized connections user, I want to connect an allowed fixture service.

- **Frontend steps:** Choose Connect; complete a local test authorization callback; refresh connections.
- **Persisted/read-back result:** The saved connection belongs to the initiating user and intended provider.
- **Permission negative:** Users cannot view/disconnect another account, self-enable restricted providers or bypass connection and runtime grants through an existing connection ID.
- **Required verification:** REAL_BROWSER; CONNECTOR_FIXTURE; TWO_USERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CONN-004

As an authorized connections user, I want to complete a real provider authorization.

- **Frontend steps:** In an approved disposable test tenant, use Connect and the genuine provider authorization/callback.
- **Persisted/read-back result:** Provider-side test connection and application ownership agree after reload.
- **Permission negative:** Unapproved scopes/foreign accounts must not be silently attached.
- **Required verification:** REAL_BROWSER; REAL_EXTERNAL; TWO_USERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CONN-005

As an authorized connections user, I want to disconnect an owned service.

- **Frontend steps:** Open an owned fixture connection; Disconnect; confirm; refresh.
- **Persisted/read-back result:** Only the selected connection is removed and future calls fail clearly.
- **Permission negative:** Users cannot view/disconnect another account, self-enable restricted providers or bypass connection and runtime grants through an existing connection ID.
- **Required verification:** REAL_BROWSER; CONNECTOR_FIXTURE; TWO_USERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CONN-006

As an authorized connections user, I want to separate personal and shared connections.

- **Frontend steps:** Seed own, another-user and explicitly shared connections; inspect each allowed role view.
- **Persisted/read-back result:** Visibility/actions reflect actual ownership and grants without credential leakage.
- **Permission negative:** Users cannot view/disconnect another account, self-enable restricted providers or bypass connection and runtime grants through an existing connection ID.
- **Required verification:** REAL_BROWSER; CONNECTOR_FIXTURE; TWO_USERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CONN-007

As an authorized connections user, I want to prevent duplicate pending requests.

- **Frontend steps:** Click Request access repeatedly while delayed; reload.
- **Persisted/read-back result:** Only one logical pending request exists and controls show its status.
- **Permission negative:** Users cannot view/disconnect another account, self-enable restricted providers or bypass connection and runtime grants through an existing connection ID.
- **Required verification:** REAL_BROWSER; CONNECTOR_FIXTURE; TWO_USERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CONN-008

As an authorized connections user, I want to recover from failed connection catalog.

- **Frontend steps:** Fail catalog/connections endpoint; open panel; retry after recovery.
- **Persisted/read-back result:** Error is visible and retry renders current identity-scoped results.
- **Permission negative:** Users cannot view/disconnect another account, self-enable restricted providers or bypass connection and runtime grants through an existing connection ID.
- **Required verification:** REAL_BROWSER; CONNECTOR_FIXTURE; TWO_USERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CONN-009

As an authorized connections user, I want to ignore stale results after identity change.

- **Frontend steps:** Delay Alice's connection fetch; switch fixture identity/context; complete old response.
- **Persisted/read-back result:** Alice's rows cannot appear in Bob's view.
- **Permission negative:** Users cannot view/disconnect another account, self-enable restricted providers or bypass connection and runtime grants through an existing connection ID.
- **Required verification:** REAL_BROWSER; CONNECTOR_FIXTURE; TWO_USERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-CONN-010

As an authorized connections user, I want to use a granted connection through runtime.

- **Frontend steps:** Connect an allowed fixture provider; run a synthetic tool request; revoke its grant; repeat.
- **Persisted/read-back result:** Only the currently permitted actor/tool receives the connection; revocation stops later dispatch.
- **Permission negative:** Users cannot view/disconnect another account, self-enable restricted providers or bypass connection and runtime grants through an existing connection ID.
- **Required verification:** REAL_BROWSER; CONNECTOR_FIXTURE; TWO_USERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### GOV — Governance administration and existing approval flows

Persona: governance administrator. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/governance.js; api/governance_api.py; api/governance/{loader,resolver,enforce,agent_context,nav,usage,suggestions}.py`.

#### US-SP-GOV-001

As a governance administrator, I want to open every governance tab.

- **Frontend steps:** Open Governance; click Overview, Users, Groups, Workspaces, Approvals, Integrations, Preview and Audit.
- **Persisted/read-back result:** Each tab loads its current authorized state and no click leaves a silent dead end.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-002

As a governance administrator, I want to create a governed user.

- **Frontend steps:** Open Users; enter a fixture identity and explicit configuration; Save user; reload.
- **Persisted/read-back result:** One user entry persists under the canonical identity with the displayed policy revision.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-003

As a governance administrator, I want to edit and cancel user policy.

- **Frontend steps:** Open an existing user; change description/roles; Cancel; reopen; edit/save; reload.
- **Persisted/read-back result:** Cancel preserves old state; explicit Save persists only intended changes.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-004

As a governance administrator, I want to delete a governed user entry.

- **Frontend steps:** Delete a disposable non-bootstrap fixture user policy; reload effective-access preview.
- **Persisted/read-back result:** The direct entry is removed; remaining inherited/default access is recomputed and displayed honestly.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-005

As a governance administrator, I want to assign roles and groups.

- **Frontend steps:** Edit fixture user roles/groups; save; inspect effective preview and actual user navigation.
- **Persisted/read-back result:** Effective grants and visible features reflect the saved inheritance.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-006

As a governance administrator, I want to add and remove capability chips.

- **Frontend steps:** Use keyboard and catalog selection to add/remove skill, CLI and MCP grants; Save; reload.
- **Persisted/read-back result:** Canonical selected values persist without duplicates or uncommitted chip text loss.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-007

As a governance administrator, I want to exclude inherited capabilities.

- **Frontend steps:** Open effective user capabilities; apply supported deny toggles; Save; inspect preview and runtime.
- **Persisted/read-back result:** Explicit exclusions override inherited grants and remain effective after reload.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-008

As a governance administrator, I want to create a group from a template.

- **Frontend steps:** Open Groups > New group; choose each supported template in isolated fixtures; save.
- **Persisted/read-back result:** The template's visible capabilities persist exactly; no unexplained grants are added.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-009

As a governance administrator, I want to edit and delete a group.

- **Frontend steps:** Change a disposable group's grants; save; inspect member access; delete group.
- **Persisted/read-back result:** Members receive revised inheritance; deletion removes group-derived rights without corrupting direct grants.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-010

As a governance administrator, I want to assign workspace membership.

- **Frontend steps:** Open Governance > Workspaces; filter a fixture user; add/remove assignments; Save; clear filter.
- **Persisted/read-back result:** Assignments persist and effective file/workspace access changes immediately.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-011

As a governance administrator, I want to preview effective access.

- **Frontend steps:** Open Preview; enter fixture email/groups; run Preview; compare to that user's real browser/API behavior.
- **Persisted/read-back result:** Preview reflects the same decision inputs and saved revision used by enforcement.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-012

As a governance administrator, I want to inspect pending approval kinds.

- **Frontend steps:** Seed grant, skill, integration, MCP and CLI requests; open each filter and explanation.
- **Persisted/read-back result:** Every row identifies requester, capability, data, risk, policy target and current status.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-013

As a governance administrator, I want to approve a manual request.

- **Frontend steps:** Open a synthetic pending request as admin; inspect explanation; Approve; reopen requester view.
- **Persisted/read-back result:** The allowed scoped change is stored and the requester sees the final accepted state.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-014

As a governance administrator, I want to deny a manual request with reason.

- **Frontend steps:** Open a synthetic pending request; Deny; select/type a reason; confirm; reopen requester view.
- **Persisted/read-back result:** Denied state and reason persist; blocked work cannot execute.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-015

As a governance administrator, I want to avoid duplicate approval decisions.

- **Frontend steps:** Open one pending request in two admin tabs; decide in A; decide differently in stale B.
- **Persisted/read-back result:** One authoritative final decision wins; stale action fails visibly and cannot widen grants.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-016

As a governance administrator, I want to inspect advice without treating it as approval.

- **Frontend steps:** Open a pending request with model/rules advice; expand its source/reason; leave undecided.
- **Persisted/read-back result:** Advice is labeled by source and the request remains pending until its configured approval flow decides.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-017

As a governance administrator, I want to inspect related suggestions.

- **Frontend steps:** Expand related access suggestions; approve, deny and ignore separate fixture suggestions.
- **Persisted/read-back result:** Each scoped suggestion decision persists separately; route permission and resource permission remain distinct.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-018

As a governance administrator, I want to manage integration enablement.

- **Frontend steps:** Open Governance > Integrations; enable/disable a fixture provider under admin controls; reload user catalog.
- **Persisted/read-back result:** Global enablement and per-user connection/runtime grants remain distinct and effective.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-019

As a governance administrator, I want to filter and refresh audit events.

- **Frontend steps:** Open Audit; filter a known fixture identity/action/time window; refresh.
- **Persisted/read-back result:** Only matching authorized events appear with accurate actor, decision and timing.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-020

As a governance administrator, I want to handle policy conflicts and invalid fields.

- **Frontend steps:** Open user edit; modify policy elsewhere; submit stale or invalid form data; correct/reload.
- **Persisted/read-back result:** Conflict/validation is explicit and the last valid policy remains intact.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-GOV-021

As a capability requester, I want to inspect the status and next action for my approval requests.

- **Frontend steps:** As requester open My approvals/Access requests; inspect pending, accepted and denied fixtures; reload.
- **Persisted/read-back result:** Only that caller's requests and accurate next actions/status are visible.
- **Permission negative:** A requester cannot list others' requests or approve their own unprivileged request.
- **Required verification:** REAL_BROWSER; TWO_USERS; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-GOV-022

As a governance administrator, I want to enforce governed navigation.

- **Frontend steps:** As a narrow member open settings navigation customization; attempt to re-enable a forbidden tab; use its deep link.
- **Persisted/read-back result:** Client preference cannot resurrect a denied capability; APIs still enforce the same denial.
- **Permission negative:** A user without governance administration cannot read private policy/audit data or create, change, approve, deny or delete another user policy through direct endpoints.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### POL — Requested RBAC, whitelist/blacklist and automatic approval

Persona: governance administrator configuring a user. Inventory: **REQUESTED_NEW_BEHAVIOR**. Source reference: `User request dated 2026-09-08; current implementation contract must be reconciled before execution`.

#### US-SP-POL-001

As a governance administrator configuring a user, I want to configure role mode and approval independently.

- **Frontend steps:** Open user policy; choose role, whitelist/blacklist and manual/automatic flow; Save; reopen.
- **Persisted/read-back result:** All three independent selections persist and displayed effective access explains their interaction.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-002

As a governance administrator configuring a user, I want to start an empty whitelist with no capabilities.

- **Frontend steps:** Create a user in whitelist mode with no explicit allowed capabilities; sign in as that user; try representative features/tools.
- **Persisted/read-back result:** No protected action executes until explicitly allowed; sign-in/help/request-access shell behavior is separately documented.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-003

As a governance administrator configuring a user, I want to allow one whitelist capability.

- **Frontend steps:** Grant a precise fixture capability; Save; as user perform it and a neighboring unlisted action.
- **Persisted/read-back result:** Only the specified capability and documented prerequisites become usable.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-004

As a governance administrator configuring a user, I want to revoke a whitelist capability.

- **Frontend steps:** Remove the allowed entry while the user retains its tab/cookie; retry UI/API/runtime.
- **Persisted/read-back result:** The revoked capability stops working immediately and prior grants are not cached as authority.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-005

As a governance administrator configuring a user, I want to start blacklist mode broadly enabled.

- **Frontend steps:** Assign Blacklist to a fixture user with a documented ordinary, elevated or admin RBAC ceiling and no denies; reload; exercise permitted actions and forbidden administrator actions.
- **Persisted/read-back result:** Unlisted actions inside the assigned role and resource ceiling succeed; blacklist does not invent new role grants or bypass protected administrator powers.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-006

As a governance administrator configuring a user, I want to deny one blacklist capability.

- **Frontend steps:** Add a precise capability to a blacklist; Save; perform that action and an unrelated one as user.
- **Persisted/read-back result:** The blocked action is denied while the unrelated action remains usable.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-007

As a governance administrator configuring a user, I want to remove a blacklist restriction.

- **Frontend steps:** Remove one denied entry; Save; retry as the same retained user session.
- **Persisted/read-back result:** The formerly blocked action becomes available under the documented role/mode rules.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-008

As a governance administrator configuring a user, I want to enforce denial over conflicting grants.

- **Frontend steps:** Seed role/group/direct allow and explicit deny for the same capability; save; preview; execute.
- **Persisted/read-back result:** The explicit denial wins at UI, API and runtime enforcement points.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-009

As a governance administrator configuring a user, I want to switch whitelist to blacklist.

- **Frontend steps:** Save a user in whitelist mode; record effective rights; change to blacklist; review and save.
- **Persisted/read-back result:** The UI clearly previews the widening change and persisted effective access matches the selected mode without stale grants.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-010

As a governance administrator configuring a user, I want to switch blacklist to whitelist.

- **Frontend steps:** Save blacklist policy; switch to whitelist with explicit selected grants; inspect current tabs and workers.
- **Persisted/read-back result:** All unlisted capabilities become denied immediately and previous broad access cannot survive in cache.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-011

As a governance administrator configuring a user, I want to assign ordinary elevated and admin roles.

- **Frontend steps:** Create one fixture user per supported role; sign into each; exercise member, elevated and governance-admin actions.
- **Persisted/read-back result:** The documented role hierarchy is enforced consistently and elevated is not silently equivalent to policy administrator.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-012

As a governance administrator configuring a user, I want to prevent self-elevation.

- **Frontend steps:** As ordinary/elevated user open or forge own policy edits for role/mode/prompt/approval flow.
- **Persisted/read-back result:** No unauthorized policy change persists and the attempt is denied/audited.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-013

As a governance administrator configuring a user, I want to preserve the last recoverable administrator.

- **Frontend steps:** Attempt to remove or downgrade the final configured/bootstrap administrator in an isolated fixture.
- **Persisted/read-back result:** The product's explicit last-admin recovery rule is honored and clearly surfaced; no silent irreversible lockout occurs.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-014

As a governance administrator configuring a user, I want to save a per-user natural-language policy.

- **Frontend steps:** Enter a fixture prompt describing allowed and disallowed actions; Save; reopen user policy.
- **Persisted/read-back result:** The exact intended prompt/revision persists only for the selected user and is visible to authorized administrators.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-015

As a governance administrator configuring a user, I want to keep manual approval pending.

- **Frontend steps:** Choose Manual; as the owning signed-in user trigger one otherwise-permitted fixture tool action; inspect the pending card before responding.
- **Persisted/read-back result:** The action remains parked with no side effect and offers only Allow once or Deny; capability expansion still requires governance administration.
- **Permission negative:** Another signed-in user cannot accept the owner-bound pending action; session/permanent/skip-all choices are refused; no one-shot action decision can add a grant or override an explicit denial.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-016

As a governance administrator configuring a user, I want to resume a manually approved action.

- **Frontend steps:** As the requester/session owner trigger one otherwise-permitted gated fixture tool action; choose Allow once in that session; reload and inspect the result.
- **Persisted/read-back result:** Only that exact already-permitted action resumes once and its final status is durable; manual acceptance cannot add capabilities or override a denial.
- **Permission negative:** Another signed-in user cannot accept the owner-bound pending action; session/permanent/skip-all choices are refused; no one-shot action decision can add a grant or override an explicit denial.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-017

As a governance administrator configuring a user, I want to block a manually denied action.

- **Frontend steps:** As the requester/session owner trigger one otherwise-permitted gated fixture tool action; choose Deny; reload and retry the denied request.
- **Persisted/read-back result:** The tool side effect remains absent; the decision is durable and cannot be reused for another action.
- **Permission negative:** Another signed-in user cannot accept the owner-bound pending action; session/permanent/skip-all choices are refused; no one-shot action decision can add a grant or override an explicit denial.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-018

As a governance administrator configuring a user, I want to automatically accept an allowed action.

- **Frontend steps:** Choose Automatic and a prompt explicitly allowing one fixture action; trigger it through the user UI.
- **Persisted/read-back result:** The actual decision service records acceptance with policy revision/reason and the scoped action executes once.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-019

As a governance administrator configuring a user, I want to automatically deny a forbidden action.

- **Frontend steps:** Choose Automatic and a prompt explicitly forbidding one fixture action; trigger it through UI.
- **Persisted/read-back result:** Automatic denial is visible and audited; no provider/tool side effect executes.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-020

As a governance administrator configuring a user, I want to distinguish policies between users.

- **Frontend steps:** Give Alice and Bob contradictory prompts for the same action; trigger in separate contexts.
- **Persisted/read-back result:** Each outcome follows the correct user's current prompt and no decision cache crosses identities.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-021

As a governance administrator configuring a user, I want to handle ambiguous automatic decisions.

- **Frontend steps:** Choose Automatic; return an ambiguous/manual result from the decision fixture; as requester/session owner inspect and resolve the pending card.
- **Persisted/read-back result:** Uncertain decisions park with no tool side effect until one-shot review by the owning identity; they never silently accept or expand access.
- **Permission negative:** Another signed-in user cannot accept the owner-bound pending action; session/permanent/skip-all choices are refused; no one-shot action decision can add a grant or override an explicit denial.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-022

As a governance administrator configuring a user, I want to handle unavailable decision intelligence.

- **Frontend steps:** Make the automatic decision provider timeout/fail; trigger a gated action; restore service.
- **Persisted/read-back result:** The action remains unapproved until a valid supported decision path completes; retry cannot duplicate side effects.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-023

As a governance administrator configuring a user, I want to reject malformed automatic responses.

- **Frontend steps:** Return invalid JSON, unknown decision labels, missing scope/revision and hostile markup from the decision fixture.
- **Persisted/read-back result:** Invalid results do not authorize work; the UI shows recoverable failure and renders text safely.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-024

As a governance administrator configuring a user, I want to resist prompt injection in action content.

- **Frontend steps:** Set a restrictive administrator policy; submit a fixture action containing instructions to ignore policy or self-approve.
- **Persisted/read-back result:** Untrusted action content cannot replace administrator policy or override explicit denials.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-025

As a governance administrator configuring a user, I want to enforce policy during delegated execution.

- **Frontend steps:** Allow a parent task but deny a child tool/resource; request two real engine children.
- **Persisted/read-back result:** Each child retains caller policy and immutable bot ceiling; the forbidden child action never executes.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-026

As a governance administrator configuring a user, I want to recheck policy before approved execution.

- **Frontend steps:** Approve an action; change/revoke policy before its queued execution begins; release the fixture runner.
- **Persisted/read-back result:** Execution rechecks current authorization and stale approval cannot bypass the new restriction.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-027

As a governance administrator configuring a user, I want to switch approval mode with pending requests.

- **Frontend steps:** Create a pending manual request; change user to automatic and back; inspect/resolve pending work.
- **Persisted/read-back result:** The product's explicit migration rule is shown; existing requests cannot be silently double-decided or auto-executed.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-028

As a governance administrator configuring a user, I want to bind an approval to the exact request.

- **Frontend steps:** Approve one request; change target/arguments or replay its identifier for a different action.
- **Persisted/read-back result:** Scope/identity/revision binding prevents a decision from authorizing changed work.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-029

As a governance administrator configuring a user, I want to audit automated acceptance and denial.

- **Frontend steps:** Run accepted/denied/manual/uncertain fixtures; open requester status and admin audit.
- **Persisted/read-back result:** Events identify actual actor/decision source, policy revision, target, outcome and readable reason without secrets.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-030

As a governance administrator configuring a user, I want to keep policy prompts separate from user data.

- **Frontend steps:** Store distinct user prompts and private markers; inspect another user, shared bot and model request fixtures.
- **Persisted/read-back result:** Only the decision service receives authorized policy context; one user's prompt/private data does not leak to another.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-031

As a governance administrator configuring a user, I want to show an effective-policy explanation.

- **Frontend steps:** Configure inheritance, mode and deny conflicts; open user effective access and denied-action explanation.
- **Persisted/read-back result:** The UI explains decisive role/mode/allow/deny/approval conditions in user language and matches actual enforcement.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-032

As a governance administrator configuring a user, I want to migrate legacy users without silent widening.

- **Frontend steps:** Load a historical fixture policy without new fields; open each user; save an unrelated field; reload.
- **Persisted/read-back result:** Migration/default semantics are explicitly documented and tested; existing rights do not widen accidentally.
- **Permission negative:** An unprivileged user or model-generated request cannot alter its role/mode/prompt, override explicit denial, self-elevate or manufacture approval.
- **Required verification:** REAL_BROWSER; POLICY_FIXTURES; RELOAD; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-POL-033

As a governance administrator configuring a user, I want to verify the configured AI decision model end to end.

- **Frontend steps:** In an isolated authorized environment invoke the actual configured decision model for one clearly allowed and one clearly denied harmless fixture action; inspect frontend outcomes and audit.
- **Persisted/read-back result:** Both decisions traverse the real configured intelligence service with recorded model/source and prompt revision; no external business side effect is performed.
- **Permission negative:** The real model cannot override a hard deny, self-elevate or approve changed request scope.
- **Required verification:** REAL_BROWSER; REAL_DECISION_MODEL; ISOLATED_RUNTIME; AUDIT_READBACK; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### INS — Insights, usage and health reporting

Persona: authorized analytics viewer. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/panels.js loadInsights and capacity/health renderers`.

#### US-SP-INS-001

As an authorized analytics viewer, I want to inspect usage and cost totals.

- **Frontend steps:** Open Insights on seeded known usage; inspect aggregate and per-model charts.
- **Persisted/read-back result:** Visible totals equal fixture values with correct units/time window; no write occurs.
- **Permission negative:** Without analytics/health permission a caller cannot obtain underlying session, identity, cost or usage data through hidden endpoints.
- **Required verification:** REAL_BROWSER; SEEDED_USAGE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-INS-002

As an authorized analytics viewer, I want to change reporting filters and periods.

- **Frontend steps:** Exercise visible date/profile/model filters; compare two known fixtures.
- **Persisted/read-back result:** Each chart/table uses the selected authorized scope without stale mixed data.
- **Permission negative:** Without analytics/health permission a caller cannot obtain underlying session, identity, cost or usage data through hidden endpoints.
- **Required verification:** REAL_BROWSER; SEEDED_USAGE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-INS-003

As an authorized analytics viewer, I want to inspect model and provider health.

- **Frontend steps:** Open model health/cost table and provider statuses; refresh.
- **Persisted/read-back result:** Status freshness and unknown/unavailable states are explicit; configured does not imply working inference.
- **Permission negative:** Without analytics/health permission a caller cannot obtain underlying session, identity, cost or usage data through hidden endpoints.
- **Required verification:** REAL_BROWSER; SEEDED_USAGE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-INS-004

As an authorized analytics viewer, I want to inspect skill usage.

- **Frontend steps:** Open skill usage details for a known fixture run.
- **Persisted/read-back result:** Counts and labels represent actual recorded permitted activity.
- **Permission negative:** Without analytics/health permission a caller cannot obtain underlying session, identity, cost or usage data through hidden endpoints.
- **Required verification:** REAL_BROWSER; SEEDED_USAGE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-INS-005

As an authorized analytics viewer, I want to inspect system and notes/wiki health.

- **Frontend steps:** Open supported system/notes/wiki status cards and their browser links.
- **Persisted/read-back result:** Cards distinguish connected, unavailable and stale states; links preserve access control.
- **Permission negative:** Without analytics/health permission a caller cannot obtain underlying session, identity, cost or usage data through hidden endpoints.
- **Required verification:** REAL_BROWSER; SEEDED_USAGE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-INS-006

As an authorized analytics viewer, I want to handle empty and failed metrics.

- **Frontend steps:** Load empty fixture; then fail metrics retrieval; retry.
- **Persisted/read-back result:** Zero usage is shown only for known empty data; failed data stays unavailable.
- **Permission negative:** Without analytics/health permission a caller cannot obtain underlying session, identity, cost or usage data through hidden endpoints.
- **Required verification:** REAL_BROWSER; SEEDED_USAGE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### LOG — Logs and diagnostics

Persona: authorized log viewer. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/panels.js (log controls)`.

#### US-SP-LOG-001

As an authorized log viewer, I want to select log file and tail size.

- **Frontend steps:** Open Logs; choose two fixture files and tail lengths.
- **Persisted/read-back result:** Displayed lines come from the selected permitted file and bounded tail.
- **Permission negative:** Users without logs access cannot list/read/copy log files; selected logs must exclude secrets and unauthorized private data.
- **Required verification:** REAL_BROWSER; SEEDED_LOGS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-LOG-002

As an authorized log viewer, I want to filter severity and text wrapping.

- **Frontend steps:** Choose each visible severity filter; toggle wrap; inspect long lines.
- **Persisted/read-back result:** Only matching lines remain and wrapping does not lose underlying text.
- **Permission negative:** Users without logs access cannot list/read/copy log files; selected logs must exclude secrets and unauthorized private data.
- **Required verification:** REAL_BROWSER; SEEDED_LOGS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-LOG-003

As an authorized log viewer, I want to refresh and auto-refresh logs.

- **Frontend steps:** Refresh manually; enable auto-refresh; append fixture line; navigate away.
- **Persisted/read-back result:** New authorized lines appear; polling stops when appropriate and no stale panel update occurs.
- **Permission negative:** Users without logs access cannot list/read/copy log files; selected logs must exclude secrets and unauthorized private data.
- **Required verification:** REAL_BROWSER; SEEDED_LOGS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-LOG-004

As an authorized log viewer, I want to copy log output.

- **Frontend steps:** Use Copy all on a known fixture selection; inspect clipboard.
- **Persisted/read-back result:** Copied content matches the intended filtered/raw contract and contains no planted secret marker.
- **Permission negative:** Users without logs access cannot list/read/copy log files; selected logs must exclude secrets and unauthorized private data.
- **Required verification:** REAL_BROWSER; SEEDED_LOGS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-LOG-005

As an authorized log viewer, I want to recover a log read failure.

- **Frontend steps:** Make a selected file unavailable; refresh; choose a valid file.
- **Persisted/read-back result:** Error is explicit and the previous protected content is not mislabeled as current.
- **Permission negative:** Users without logs access cannot list/read/copy log files; selected logs must exclude secrets and unauthorized private data.
- **Required verification:** REAL_BROWSER; SEEDED_LOGS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### PREF — Settings and personal preferences

Persona: signed-in user. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/index.html; static/panels.js (settings controls)`.

#### US-SP-PREF-001

As a signed-in user, I want to open every settings section.

- **Frontend steps:** Open Settings; click Conversation, Appearance, Access requests, Preferences, Providers, Plugins, Extensions, System and Help as permitted.
- **Persisted/read-back result:** Every reachable section shows its proper content and governed sections remain protected.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-002

As a signed-in user, I want to search for settings.

- **Frontend steps:** Type label/description queries; select a result; clear search; repeat for a hidden/forbidden setting.
- **Persisted/read-back result:** Search focuses the intended visible control without revealing or enabling unauthorized settings.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-003

As a signed-in user, I want to choose theme skin and font size.

- **Frontend steps:** Select each available theme/skin/font size on a fixture account; inspect chat/panels; reload.
- **Persisted/read-back result:** Chosen appearance persists for its documented scope with readable controls and no cross-user changes.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-004

As a signed-in user, I want to control default workspace pane visibility.

- **Frontend steps:** Toggle Keep workspace panel open; create a new chat; reload.
- **Persisted/read-back result:** The pane opens/closes by the persisted preference and manual controls still work.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-005

As a signed-in user, I want to toggle workspace Todos.

- **Frontend steps:** Toggle Show Todos tab; open right pane; reload.
- **Persisted/read-back result:** Tab visibility follows preference while authorized left Todos remains usable.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-006

As a signed-in user, I want to toggle session jump controls.

- **Frontend steps:** Toggle Start/End controls; open a long transcript; click each.
- **Persisted/read-back result:** The controls follow preference and reach correct transcript boundaries.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-007

As a signed-in user, I want to choose older-message loading behavior.

- **Frontend steps:** Toggle automatic older-message loading; scroll to top; use manual load alternative.
- **Persisted/read-back result:** Only the configured mechanism loads older messages and history remains complete.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-008

As a signed-in user, I want to choose activity display mode.

- **Frontend steps:** Select Compact Worklog, Transparent Stream and Final answer only; run a fixture response in each.
- **Persisted/read-back result:** The selected presentation persists and never changes actual execution/approval behavior.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-009

As a signed-in user, I want to toggle activity event timestamps.

- **Frontend steps:** Toggle transparent-event timestamps; inspect a fixture turn and footer.
- **Persisted/read-back result:** Per-event chips follow preference while the required footer time remains visible.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-010

As a signed-in user, I want to control automatic scroll following.

- **Frontend steps:** Toggle Auto-follow; stream a fixture response while scrolled upward and at bottom.
- **Persisted/read-back result:** Scrolling follows only the documented preference/user-position rule.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-011

As a signed-in user, I want to toggle user-message Markdown.

- **Frontend steps:** Send Markdown text with setting off/on; reload the chat.
- **Persisted/read-back result:** User text rendering follows preference while fenced code/math retain their documented behavior.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-012

As a signed-in user, I want to attach large pasted text.

- **Frontend steps:** Enable large-paste-as-attachment; paste a bounded long fixture; inspect composer; send.
- **Persisted/read-back result:** A valid attachment replaces large composer text under the documented threshold and preserves exact content.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-013

As a signed-in user, I want to toggle per-project quick creation.

- **Frontend steps:** Toggle project New conversation buttons; use one on a fixture project.
- **Persisted/read-back result:** Visibility follows setting and the resulting chat binds to that project.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-014

As a signed-in user, I want to configure structured code defaults.

- **Frontend steps:** Choose Auto/Tree/Raw and line threshold; open short/long JSON/YAML.
- **Persisted/read-back result:** Default view follows saved threshold/mode; manual view switching remains available.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-015

As a signed-in user, I want to toggle titlebar profile switcher.

- **Frontend steps:** Enable/disable titlebar switcher; switch a permitted profile; reload.
- **Persisted/read-back result:** Visibility persists and profile changes preserve current identity and grants.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-016

As a signed-in user, I want to choose default Worklog expansion.

- **Frontend steps:** Toggle automatic details expansion; run a fixture turn; manually collapse; reload.
- **Persisted/read-back result:** New rows honor the default and manual per-turn choices follow the documented persistence.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-017

As a signed-in user, I want to reorder and hide sidebar tabs.

- **Frontend steps:** Drag permitted sidebar chips; hide/show a tab; reload; inspect rail/mobile navigation.
- **Persisted/read-back result:** Order/visibility persists without hiding required access shell or resurrecting forbidden panels.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-018

As a signed-in user, I want to reorder and hide composer controls.

- **Frontend steps:** Drag footer-control chips within supported groups; toggle situational controls; reload.
- **Persisted/read-back result:** Saved order/visibility obey valid grouping and controls remain reachable on supported widths.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-019

As a signed-in user, I want to choose a default model.

- **Frontend steps:** Open default-model picker; select allowed pair; save/reload; start a new chat.
- **Persisted/read-back result:** New chat uses the saved provider/model; unavailable/ungranted selection is rejected.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-020

As a signed-in user, I want to hide welcome panel and suggestions.

- **Frontend steps:** Toggle each empty-chat option; create a new chat; reload.
- **Persisted/read-back result:** The selected welcome/suggestion elements follow the saved settings without affecting existing chats.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-021

As a signed-in user, I want to configure transcript virtualization.

- **Frontend steps:** Toggle experimental virtualization; open long seeded history; scroll/search/render old turns.
- **Persisted/read-back result:** Supported content remains reachable without lost/duplicate messages; limitations are honestly described.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-022

As a signed-in user, I want to choose language and RTL layout.

- **Frontend steps:** Choose a supported language and RTL; inspect chat and other panels; reload.
- **Persisted/read-back result:** Labels and intended chat alignment persist; non-chat layout follows its documented behavior.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-023

As a signed-in user, I want to configure notification sound.

- **Frontend steps:** Toggle completion sound; finish a fixture run in foreground/background.
- **Persisted/read-back result:** Sound occurs only according to preference and supported browser permission.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-024

As a signed-in user, I want to configure TTS and auto-read preferences.

- **Frontend steps:** Toggle response TTS and auto-read; choose voice/rate/pitch; use a fixture response.
- **Persisted/read-back result:** Values persist under the documented personal scope and read controls match them.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-025

As a signed-in user, I want to configure dictation append and raw audio.

- **Frontend steps:** Toggle append/raw-audio; invoke the fixture speech controls over an existing draft.
- **Persisted/read-back result:** Input handling matches saved mode and never silently replaces/appends contrary to the setting.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-026

As a signed-in user, I want to configure browser notifications.

- **Frontend steps:** Toggle notifications; deny/grant browser permission; complete a background fixture run.
- **Persisted/read-back result:** Permission status is accurate and notifications follow both settings and browser permission.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-027

As a signed-in user, I want to show token counts speed and quota controls.

- **Frontend steps:** Toggle token usage/TPS/quota chip; run known usage at narrow/wide widths.
- **Persisted/read-back result:** Correct values appear where supported and unknown quota is not shown as zero.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-028

As a signed-in user, I want to set maximum output tokens.

- **Frontend steps:** Enter valid/invalid/blank values; save; run a fixture completion.
- **Persisted/read-back result:** Valid cap reaches actual provider request; blank uses documented fallback and invalid input is rejected.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-029

As a signed-in user, I want to toggle conversation outline and fade effect.

- **Frontend steps:** Toggle each control; open a long streaming fixture; use outline jumps.
- **Persisted/read-back result:** Presentation persists without hiding content or causing scroll jumps.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-030

As a signed-in user, I want to configure terminal auto-expand.

- **Frontend steps:** Toggle auto-expand; collapse terminal; emit fixture command output.
- **Persisted/read-back result:** Terminal expansion follows preference and data remains accessible.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-031

As a signed-in user, I want to configure API redaction.

- **Frontend steps:** As authorized administrator toggle redaction in isolated state; inspect permitted fixture API/UI values.
- **Persisted/read-back result:** Redaction state persists and protected secrets/private data remain governed by the explicit security contract.
- **Permission negative:** Ordinary users cannot change global redaction or retrieve raw privileged values.
- **Required verification:** REAL_BROWSER; ADMIN_AND_MEMBER; PRIVACY_MARKERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-032

As a signed-in user, I want to configure sidebar density and pin limit.

- **Frontend steps:** Choose Compact/Detailed; set valid/invalid pin limits; pin fixture chats.
- **Persisted/read-back result:** Density persists and allowed pin count matches the valid configured limit.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-033

As a signed-in user, I want to configure automatic title refresh.

- **Frontend steps:** Choose Off and one refresh interval; run the required synthetic exchanges.
- **Persisted/read-back result:** Only documented title refreshes occur and user titles follow ownership rules.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-034

As a signed-in user, I want to configure default busy-message action.

- **Frontend steps:** Choose queue/interrupt/steer defaults; start a run; inspect composer and submit follow-up.
- **Persisted/read-back result:** The default and busy hint persist; actual behavior matches the visible action.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-035

As a signed-in user, I want to filter external session types.

- **Frontend steps:** Toggle non-WebUI/cron/Claude Code/webhook/previous messaging sessions; reload sidebar.
- **Persisted/read-back result:** Only configured and authorized source types appear; subordinate toggles behave consistently.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-036

As a signed-in user, I want to configure usage synchronization.

- **Frontend steps:** Toggle usage sync to Insights; run a known fixture turn; inspect recorded totals.
- **Persisted/read-back result:** Usage is recorded under the documented setting without double counting or crossing user boundaries.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-037

As a signed-in user, I want to configure update preferences.

- **Frontend steps:** Toggle checks/ignored agent updates/summary preference; select stable/experimental; inspect update UI.
- **Persisted/read-back result:** Selections persist and follow the configured update channel; no installation is implied by a check.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-038

As a signed-in user, I want to set a default assistant display name.

- **Frontend steps:** Edit default bot name; save; inspect default and named-profile chats.
- **Persisted/read-back result:** Only the documented default display name changes; named bots retain their identities.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-039

As a signed-in user, I want to recover failed settings autosave.

- **Frontend steps:** Change an autosaved preference; fail the request; inspect unsaved/error indicator; retry.
- **Persisted/read-back result:** Failure remains visible and success is claimed only after persisted read-back.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PREF-040

As a signed-in user, I want to discard unsaved settings on navigation.

- **Frontend steps:** Change a non-autosaved field; navigate away using the displayed save/discard flow.
- **Persisted/read-back result:** The chosen discard/save behavior matches stored state and no late response reclaims the old panel.
- **Permission negative:** Personal preferences cannot change another account or enable governance-forbidden functionality; privileged global options require their own server permission.
- **Required verification:** REAL_BROWSER; RELOAD; TWO_USERS; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### PROV — Providers, models and budgets

Persona: authorized provider administrator. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/panels.js (provider, quota, budget and auxiliary-model controls)`.

#### US-SP-PROV-001

As an authorized provider administrator, I want to inspect provider cards and models.

- **Frontend steps:** Open Providers; expand configured entries; inspect model list/status.
- **Persisted/read-back result:** Configured, connected and failed states are distinguished without exposing secret values.
- **Permission negative:** Non-admins cannot read/write provider secrets, change budgets or select ungranted model routes; errors and evidence must redact credentials.
- **Required verification:** REAL_BROWSER; PROVIDER_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PROV-002

As an authorized provider administrator, I want to save and remove a fixture provider key.

- **Frontend steps:** Enter a disposable local-provider credential; Save; test; Remove; reload.
- **Persisted/read-back result:** Only that provider credential changes and secret input is not echoed in reports or URLs.
- **Permission negative:** Non-admins cannot read/write provider secrets, change budgets or select ungranted model routes; errors and evidence must redact credentials.
- **Required verification:** REAL_BROWSER; PROVIDER_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PROV-003

As an authorized provider administrator, I want to configure a self-hosted provider.

- **Frontend steps:** Enter local fixture endpoint/model; test connection; save; refresh model picker.
- **Persisted/read-back result:** Saved provider and exact endpoint/model are selectable only when permitted.
- **Permission negative:** An identity without provider configuration permission cannot change the saved endpoint/model. Secret-bearing fields stay redacted from provider reads and browser evidence.
- **Required verification:** REAL_BROWSER; PROVIDER_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PROV-004

As an authorized provider administrator, I want to distinguish connection test from inference.

- **Frontend steps:** Pass a fixture health/catalog probe; deliberately fail completion; send a chat.
- **Persisted/read-back result:** The UI does not equate connection-test success with successful generation.
- **Permission negative:** A denied provider/model cannot be selected or invoked through either the connection probe or completion path; failed completion must preserve the user draft and expose no credentials.
- **Required verification:** REAL_BROWSER; PROVIDER_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PROV-005

As an authorized provider administrator, I want to refresh provider models.

- **Frontend steps:** Refresh the catalog; change fixture model availability; reopen picker.
- **Persisted/read-back result:** Current permitted models appear; stale results cannot replace another provider's catalog.
- **Permission negative:** Non-admins cannot read/write provider secrets, change budgets or select ungranted model routes; errors and evidence must redact credentials.
- **Required verification:** REAL_BROWSER; PROVIDER_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PROV-006

As an authorized provider administrator, I want to inspect quota windows and pools.

- **Frontend steps:** Load known fixture quotas/pool states; expand breakdowns; refresh.
- **Persisted/read-back result:** Units, remaining/used values, reset times and source freshness match fixture data.
- **Permission negative:** Non-admins cannot read/write provider secrets, change budgets or select ungranted model routes; errors and evidence must redact credentials.
- **Required verification:** REAL_BROWSER; PROVIDER_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PROV-007

As an authorized provider administrator, I want to handle quota errors and exhausted balance.

- **Frontend steps:** Return rate limit, credit exhaustion, authentication and unknown-status fixtures.
- **Persisted/read-back result:** The UI distinguishes states accurately, offers supported recovery and does not fabricate a balance.
- **Permission negative:** Non-admins cannot read/write provider secrets, change budgets or select ungranted model routes; errors and evidence must redact credentials.
- **Required verification:** REAL_BROWSER; PROVIDER_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PROV-008

As an authorized provider administrator, I want to configure a provider budget.

- **Frontend steps:** Set a bounded fixture budget; save; cross the cap synthetically; inspect behavior.
- **Persisted/read-back result:** Budget persists and documented enforcement/reporting behavior matches actual requests.
- **Permission negative:** Non-admins cannot read/write provider secrets, change budgets or select ungranted model routes; errors and evidence must redact credentials.
- **Required verification:** REAL_BROWSER; PROVIDER_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-PROV-009

As an authorized provider administrator, I want to configure auxiliary task models.

- **Frontend steps:** Open auxiliary model controls; choose allowed provider/model for a supported task; save; run that fixture task.
- **Persisted/read-back result:** The actual auxiliary request uses its saved pair without replacing the main chat model.
- **Permission negative:** An identity without model configuration permission cannot change any auxiliary assignment; ungranted provider/model pairs cannot be saved or invoked.
- **Required verification:** REAL_BROWSER; PROVIDER_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-PROV-010

As an authorized provider administrator, I want to configure advanced model options.

- **Frontend steps:** Open main/auxiliary advanced options; set supported reasoning/service-tier values; save/reopen.
- **Persisted/read-back result:** Only supported permitted options persist and unsupported provider options do not silently take effect.
- **Permission negative:** An identity without model configuration permission cannot alter main or auxiliary advanced options; saved keys are redacted and clearing/cancel cannot modify unrelated options.
- **Required verification:** REAL_BROWSER; PROVIDER_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

### EXT — Plugins and extensions

Persona: authorized extension administrator. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/panels.js; static/extension_settings.js`.

#### US-SP-EXT-001

As an authorized extension administrator, I want to inspect installed plugins.

- **Frontend steps:** Open Plugins; inspect active/inactive status, hooks and available plugin pages.
- **Persisted/read-back result:** Status reflects actual runtime data and unavailable plugins are not described as working.
- **Permission negative:** An identity without plugin read permission cannot read the plugin catalog or privileged page/asset contents.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-EXT-002

As an authorized extension administrator, I want to toggle a supported plugin.

- **Frontend steps:** As authorized fixture administrator toggle a disposable plugin; reload status.
- **Persisted/read-back result:** The documented activation state persists and runtime behavior agrees; read-only deployments show no false mutation success.
- **Permission negative:** An identity without plugin configuration permission cannot enable or disable the plugin through the frontend or direct settings request; the previous state remains intact.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-EXT-003

As an authorized extension administrator, I want to open plugin pages.

- **Frontend steps:** Select two permitted plugin pages; navigate away during a delayed page load.
- **Persisted/read-back result:** Correct page loads and stale content cannot replace another active panel.
- **Permission negative:** An ungranted or unsigned identity cannot read protected plugin content. The opaque plugin page cannot access the parent document, cookies, storage or authenticated session APIs.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-EXT-004

As an authorized extension administrator, I want to browse the extension gallery.

- **Frontend steps:** Open Extensions > Gallery; inspect source links, permissions and install details.
- **Persisted/read-back result:** Only supported safe URLs open and requested permissions are visible before installation.
- **Permission negative:** Users without extension administration cannot install/enable code, change sidecar consent, clear shared storage or access privileged plugin pages.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-EXT-005

As an authorized extension administrator, I want to install a disposable local extension.

- **Frontend steps:** Choose an isolated test extension; review declared permissions; Install; inspect Installed.
- **Persisted/read-back result:** The exact extension/version persists with truthful post-install activation requirements.
- **Permission negative:** Users without extension administration cannot install/enable code, change sidecar consent, clear shared storage or access privileged plugin pages.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-EXT-006

As an authorized extension administrator, I want to enable and disable an extension.

- **Frontend steps:** Toggle a fixture installed extension; reload page and supported feature.
- **Persisted/read-back result:** Enabled state persists and disabled assets/hooks stop according to the documented lifecycle.
- **Permission negative:** Users without extension administration cannot install/enable code, change sidecar consent, clear shared storage or access privileged plugin pages.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-EXT-007

As an authorized extension administrator, I want to uninstall an extension.

- **Frontend steps:** Uninstall the disposable extension through confirmation; reload gallery/installed list.
- **Persisted/read-back result:** Only that extension is removed and its feature no longer runs.
- **Permission negative:** Users without extension administration cannot install/enable code, change sidecar consent, clear shared storage or access privileged plugin pages.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-EXT-008

As an authorized extension administrator, I want to save and reset extension settings.

- **Frontend steps:** Edit each field of a fixture extension schema; Save; reload; Reset.
- **Persisted/read-back result:** Validated values persist; reset returns documented defaults without affecting other extensions.
- **Permission negative:** Users without extension administration cannot install/enable code, change sidecar consent, clear shared storage or access privileged plugin pages.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-EXT-009

As an authorized extension administrator, I want to clear extension storage.

- **Frontend steps:** Seed disposable extension storage; use its Clear storage action; reload.
- **Persisted/read-back result:** Only the intended extension/user scope is cleared.
- **Permission negative:** Users without extension administration cannot install/enable code, change sidecar consent, clear shared storage or access privileged plugin pages.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-EXT-010

As an authorized extension administrator, I want to decide sidecar proxy consent.

- **Frontend steps:** Open extension sidecar controls; decline and grant consent in separate fixtures; retry calls.
- **Persisted/read-back result:** Proxy availability follows explicit stored consent and extension permission constraints.
- **Permission negative:** Users without extension administration cannot install/enable code, change sidecar consent, clear shared storage or access privileged plugin pages.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-EXT-011

As an authorized extension administrator, I want to inspect extension health and diagnostics.

- **Frontend steps:** Open Diagnostics; refresh sidecar health/runtime; Copy diagnostics.
- **Persisted/read-back result:** Health and origins are current or labeled unavailable and copied data excludes credentials.
- **Permission negative:** Users without extension administration cannot install/enable code, change sidecar consent, clear shared storage or access privileged plugin pages.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-EXT-012

As an authorized extension administrator, I want to handle extension install or health failures.

- **Frontend steps:** Fail registry/install/sidecar fixture calls; retry supported actions.
- **Persisted/read-back result:** Errors are visible, partial installation state is honest and no duplicate active extension remains.
- **Permission negative:** Users without extension administration cannot install/enable code, change sidecar consent, clear shared storage or access privileged plugin pages.
- **Required verification:** REAL_BROWSER; LOCAL_EXTENSION_FIXTURE; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### SYS — System, gateway, MCP and capacity controls

Persona: authorized system administrator. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/panels.js (System, gateway, MCP, checkpoints, capacity controls)`.

#### US-SP-SYS-001

As an authorized system administrator, I want to change the fixture password.

- **Frontend steps:** Open System authentication; enter current/new fixture password; save; sign in again.
- **Persisted/read-back result:** New credential works and old credential is refused under the documented session invalidation contract.
- **Permission negative:** Without system/governance permission users cannot modify auth, restart services, restore checkpoints, change MCP state or adjust global limits.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-002

As an authorized system administrator, I want to inspect environment-managed authentication.

- **Frontend steps:** Open auth settings with environment-owned password enabled.
- **Persisted/read-back result:** The UI honestly explains precedence and cannot claim a stored setting overrides active configuration.
- **Permission negative:** Without system/governance permission users cannot modify auth, restart services, restore checkpoints, change MCP state or adjust global limits.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-003

As an authorized system administrator, I want to exercise passwordless and disabled-auth controls.

- **Frontend steps:** In an isolated fixture only, use each explicitly supported auth-mode action and confirmation.
- **Persisted/read-back result:** The documented mode changes persist and warnings/available controls match actual authentication behavior.
- **Permission negative:** Without system/governance permission users cannot modify auth, restart services, restore checkpoints, change MCP state or adjust global limits.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-004

As an authorized system administrator, I want to configure the external dashboard link.

- **Frontend steps:** Choose dashboard visibility mode; enter a safe fixture URL; Save; click the resulting link.
- **Persisted/read-back result:** Visibility/target persist and unsafe schemes are refused.
- **Permission negative:** An ungranted identity cannot change the global dashboard target/visibility, and unsafe URL input cannot execute script or persist a dangerous target.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-005

As an authorized system administrator, I want to inspect gateway health.

- **Frontend steps:** Open Gateway status; refresh healthy/degraded/unavailable fixtures.
- **Persisted/read-back result:** Actual readiness is distinct from process-active status and stale health is not reported current.
- **Permission negative:** Without system/governance permission users cannot modify auth, restart services, restore checkpoints, change MCP state or adjust global limits.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-006

As an authorized system administrator, I want to execute allowed gateway actions.

- **Frontend steps:** On an isolated idle fixture click each exposed start/stop/restart action; inspect state/read-back.
- **Persisted/read-back result:** The requested lifecycle action completes or fails visibly without affecting production services.
- **Permission negative:** Without system/governance permission users cannot modify auth, restart services, restore checkpoints, change MCP state or adjust global limits.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-007

As an authorized system administrator, I want to inspect and toggle MCP servers.

- **Frontend steps:** Open configured servers; inspect details; toggle an editable fixture server; reload.
- **Persisted/read-back result:** Supported state persists and current tools reflect availability; read-only controls report no mutation.
- **Permission negative:** An ungranted identity cannot toggle an MCP server or obtain denied server/tool configuration; denied writes leave the configured state unchanged.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-008

As an authorized system administrator, I want to search and page MCP tools.

- **Frontend steps:** Search fixture tools; change page size; move pages; inspect schema.
- **Persisted/read-back result:** Filtering/pagination returns the correct permitted tools and complete selected schema.
- **Permission negative:** The tool search, pagination and schema views cannot reveal a tool outside the signed-in identity's permitted MCP scope.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-009

As an authorized system administrator, I want to inspect checkpoint differences.

- **Frontend steps:** Open checkpoint list; select two fixture checkpoints; inspect Diff.
- **Persisted/read-back result:** The correct revision differences render safely without restoring anything.
- **Permission negative:** Without system/governance permission users cannot modify auth, restart services, restore checkpoints, change MCP state or adjust global limits.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-010

As an authorized system administrator, I want to restore a disposable checkpoint.

- **Frontend steps:** Select a checkpoint in isolated state; inspect diff; confirm Restore; reopen affected artifact.
- **Persisted/read-back result:** Only the documented checkpoint scope is restored and stored state matches the selected revision.
- **Permission negative:** Without system/governance permission users cannot modify auth, restart services, restore checkpoints, change MCP state or adjust global limits.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-011

As an authorized system administrator, I want to configure and acknowledge capacity alerts.

- **Frontend steps:** Set fixture thresholds; save; trigger alert; open it; Acknowledge; reload.
- **Persisted/read-back result:** Thresholds and acknowledgement persist; actual usage/alert state remains accurate.
- **Permission negative:** An ungranted identity cannot change alert thresholds/destination or acknowledge an alert; denied changes preserve authoritative configuration and alert state.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-012

As an authorized system administrator, I want to check and inspect available updates.

- **Frontend steps:** Click Check updates; inspect unavailable/current/new-version states; open supported summary/diff.
- **Persisted/read-back result:** The UI accurately identifies source/version; a check or summary is not represented as an installed update.
- **Permission negative:** Without system/governance permission users cannot modify auth, restart services, restore checkpoints, change MCP state or adjust global limits.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-SYS-013

As an authorized system administrator, I want to open help and diagnostics links.

- **Frontend steps:** Open Help and each visible local/support link in the fixture UI.
- **Persisted/read-back result:** Links resolve to intended safe destinations and private runtime data is not leaked in their URLs.
- **Permission negative:** Without system/governance permission users cannot modify auth, restart services, restore checkpoints, change MCP state or adjust global limits.
- **Required verification:** REAL_BROWSER; ISOLATED_RUNTIME; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### VOICE — Dictation, speech and realtime voice

Persona: authorized voice user. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/index.html; static/panels.js; September 6 voice release evidence`.

#### US-SP-VOICE-001

As an authorized voice user, I want to distinguish voice from dictation controls.

- **Frontend steps:** Open chat on desktop/mobile; inspect the waveform and microphone controls; activate each in a fixture.
- **Persisted/read-back result:** Each action opens its documented mode and duplicate/confusing controls do not appear.
- **Permission negative:** A user without voice/model permission cannot start a speech/provider session; denial or device refusal must not leak audio or invent transcription.
- **Required verification:** REAL_BROWSER; MEDIA_FIXTURE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-VOICE-002

As an authorized voice user, I want to handle microphone permission denial.

- **Frontend steps:** Click dictation/voice; deny browser permission; retry after permitted reset.
- **Persisted/read-back result:** Clear recoverable feedback appears and no recording/transcript is claimed.
- **Permission negative:** A user without voice/model permission cannot start a speech/provider session; denial or device refusal must not leak audio or invent transcription.
- **Required verification:** REAL_BROWSER; MEDIA_FIXTURE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-VOICE-003

As an authorized voice user, I want to dictate into an empty composer.

- **Frontend steps:** Use deterministic speech-recognition fixture; start/stop dictation.
- **Persisted/read-back result:** Expected transcript appears once and remains unsent until the configured explicit action.
- **Permission negative:** A user without voice/model permission cannot start a speech/provider session; denial or device refusal must not leak audio or invent transcription.
- **Required verification:** REAL_BROWSER; MEDIA_FIXTURE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-VOICE-004

As an authorized voice user, I want to append or replace existing draft by preference.

- **Frontend steps:** Seed a draft; dictate with append on/off; inspect result.
- **Persisted/read-back result:** The stored draft matches the chosen behavior without cross-session text.
- **Permission negative:** A user without voice/model permission cannot start a speech/provider session; denial or device refusal must not leak audio or invent transcription.
- **Required verification:** REAL_BROWSER; MEDIA_FIXTURE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-VOICE-005

As an authorized voice user, I want to send raw audio where enabled.

- **Frontend steps:** Enable raw-audio mode; record a bounded fixture sample; stop; send to local-only fixture.
- **Persisted/read-back result:** The correct audio attachment reaches the authorized worker with its metadata/bytes.
- **Permission negative:** A user without voice/model permission cannot start a speech/provider session; denial or device refusal must not leak audio or invent transcription.
- **Required verification:** REAL_BROWSER; MEDIA_FIXTURE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-VOICE-006

As an authorized voice user, I want to read and stop a response aloud.

- **Frontend steps:** Click response speaker; pause/stop; start typing during auto-read.
- **Persisted/read-back result:** Speech follows controls/preferences and does not continue against the documented interruption behavior.
- **Permission negative:** A user without voice/model permission cannot start a speech/provider session; denial or device refusal must not leak audio or invent transcription.
- **Required verification:** REAL_BROWSER; MEDIA_FIXTURE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-VOICE-007

As an authorized voice user, I want to complete a real microphone realtime roundtrip.

- **Frontend steps:** In a disposable approved environment, start voice; speak a synthetic prompt; hear a response; end.
- **Persisted/read-back result:** Actual capture, WebRTC/transport, speech/model response and cleanup are evidenced separately.
- **Permission negative:** No unauthorized provider or conversation receives the sample.
- **Required verification:** REAL_BROWSER; REAL_DEVICE; REAL_EXTERNAL; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-VOICE-008

As an authorized voice user, I want to recover device or voice connection loss.

- **Frontend steps:** Start a fixture voice session; disconnect device/transport; reconnect/close.
- **Persisted/read-back result:** Status is truthful, resources are released and a later session can start without duplicate listeners.
- **Permission negative:** A user without voice/model permission cannot start a speech/provider session; denial or device refusal must not leak audio or invent transcription.
- **Required verification:** REAL_BROWSER; MEDIA_FIXTURE; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

### TERM — Interactive terminal

Persona: user with explicit terminal access. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `static/terminal.js`.

#### US-SP-TERM-001

As an user with explicit terminal access, I want to open terminal in the current workspace.

- **Frontend steps:** Select a permitted fixture workspace; click terminal; run a harmless identity/path command.
- **Persisted/read-back result:** The actual process belongs to the correct session/workspace and output agrees with the visible context.
- **Permission negative:** A user without terminal/command/workspace permission cannot start or reuse a shell or execute a denied command through alternative UI/API routes.
- **Required verification:** REAL_BROWSER; ISOLATED_TERMINAL; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-TERM-002

As an user with explicit terminal access, I want to submit a harmless command.

- **Frontend steps:** Type a fixture echo/file-read command; submit; inspect output and status.
- **Persisted/read-back result:** Command runs once under the user's current authority and produces expected bytes.
- **Permission negative:** A user without terminal/command/workspace permission cannot start or reuse a shell or execute a denied command through alternative UI/API routes.
- **Required verification:** REAL_BROWSER; ISOLATED_TERMINAL; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-TERM-003

As an user with explicit terminal access, I want to collapse expand and resize terminal.

- **Frontend steps:** Collapse/expand; drag resize handle; exercise keyboard resizing; change viewport.
- **Persisted/read-back result:** Geometry stays usable within bounds and the same terminal output remains intact.
- **Permission negative:** A user without terminal/command/workspace permission cannot start or reuse a shell or execute a denied command through alternative UI/API routes.
- **Required verification:** REAL_BROWSER; ISOLATED_TERMINAL; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-TERM-004

As an user with explicit terminal access, I want to copy and clear output.

- **Frontend steps:** Emit known fixture output; Copy; verify clipboard; Clear.
- **Persisted/read-back result:** Copied bytes match output and clearing affects the intended display/state contract only.
- **Permission negative:** A user without terminal/command/workspace permission cannot start or reuse a shell or execute a denied command through alternative UI/API routes.
- **Required verification:** REAL_BROWSER; ISOLATED_TERMINAL; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-TERM-005

As an user with explicit terminal access, I want to interrupt a running command.

- **Frontend steps:** Run a bounded fixture process; send its interrupt control; inspect exit.
- **Persisted/read-back result:** The process stops, outcome is truthful and a later command can run.
- **Permission negative:** A user without terminal/command/workspace permission cannot start or reuse a shell or execute a denied command through alternative UI/API routes.
- **Required verification:** REAL_BROWSER; ISOLATED_TERMINAL; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-TERM-006

As an user with explicit terminal access, I want to close and restart terminal.

- **Frontend steps:** Open terminal; close; reopen/restart using supported controls.
- **Persisted/read-back result:** Process/socket ownership follows the documented lifecycle without orphaned active shells.
- **Permission negative:** A user without terminal/command/workspace permission cannot start or reuse a shell or execute a denied command through alternative UI/API routes.
- **Required verification:** REAL_BROWSER; ISOLATED_TERMINAL; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-TERM-007

As an user with explicit terminal access, I want to handle unsupported backend or startup failure.

- **Frontend steps:** Choose an unsupported remote-backend fixture or fail terminal creation; click terminal.
- **Persisted/read-back result:** The UI shows the correct limitation/error and does not leave a fake connected terminal.
- **Permission negative:** A user without terminal/command/workspace permission cannot start or reuse a shell or execute a denied command through alternative UI/API routes.
- **Required verification:** REAL_BROWSER; ISOLATED_TERMINAL; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-TERM-008

As an user with explicit terminal access, I want to revoke terminal access while connected.

- **Frontend steps:** Open an allowed fixture shell; revoke terminal permission; submit another command.
- **Persisted/read-back result:** Further privileged execution is denied and connection lifecycle follows documented revocation policy.
- **Permission negative:** A user without terminal/command/workspace permission cannot start or reuse a shell or execute a denied command through alternative UI/API routes.
- **Required verification:** REAL_BROWSER; ISOLATED_TERMINAL; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-TERM-009

As an user with explicit terminal access, I want to retain authoritative command errors.

- **Frontend steps:** Run a fixture command with nonzero exit; inspect; reload the chat/runtime view.
- **Persisted/read-back result:** The actual error is preserved where promised and never rewritten as successful completion.
- **Permission negative:** A user without terminal/command/workspace permission cannot start or reuse a shell or execute a denied command through alternative UI/API routes.
- **Required verification:** REAL_BROWSER; ISOLATED_TERMINAL; RELOAD; NEGATIVE_SERVER.
- **Priority / current status:** P0 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

### UX — Whole-application control coverage and resilience

Persona: user of each supported role. Inventory: **HISTORICAL_SOURCE_DERIVED**. Source reference: `All historical UI modules plus current runtime inventory required`.

#### US-SP-UX-001

As an user of each supported role, I want to account for every discovered interactive control.

- **Frontend steps:** On the current candidate enumerate visible buttons, links, inputs, selects, menus and dialogs for every seeded persona/state; map each to a story and exercised locator.
- **Persisted/read-back result:** Every discovered control is explicitly covered or an explained gap; historical source counts are not reported as executed coverage.
- **Permission negative:** Hidden/disabled UI is never the only authority; every negative case includes direct server/resource/runtime verification for the relevant boundary.
- **Required verification:** REAL_BROWSER; ALL_PERSONAS; DESKTOP_LAPTOP_MOBILE; CONTROL_MANIFEST; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-UX-002

As an user of each supported role, I want to open every permitted navigation entry.

- **Frontend steps:** As each persona click every visible rail/sidebar/mobile item and return to chat.
- **Persisted/read-back result:** Each entry loads its real backend-supported view with no silent errors or unintended mutations.
- **Permission negative:** Hidden/disabled UI is never the only authority; every negative case includes direct server/resource/runtime verification for the relevant boundary.
- **Required verification:** REAL_BROWSER; ALL_PERSONAS; DESKTOP_LAPTOP_MOBILE; CONTROL_MANIFEST; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-UX-003

As an user of each supported role, I want to use responsive layouts.

- **Frontend steps:** Run core flows at 1440x950, 1024x768 and 390x844; open menus/dialogs; scroll.
- **Persisted/read-back result:** Content/control access remains usable without unintended horizontal overflow or clipped primary actions.
- **Permission negative:** Hidden/disabled UI is never the only authority; every negative case includes direct server/resource/runtime verification for the relevant boundary.
- **Required verification:** REAL_BROWSER; ALL_PERSONAS; DESKTOP_LAPTOP_MOBILE; CONTROL_MANIFEST; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-UX-004

As an user of each supported role, I want to navigate by keyboard.

- **Frontend steps:** Tab through navigation/composer/forms; use Enter/Space/arrows/Escape; inspect focus return.
- **Persisted/read-back result:** Controls are reachable, labels/focus are intelligible and modals preserve intended focus boundaries.
- **Permission negative:** Hidden/disabled UI is never the only authority; every negative case includes direct server/resource/runtime verification for the relevant boundary.
- **Required verification:** REAL_BROWSER; ALL_PERSONAS; DESKTOP_LAPTOP_MOBILE; CONTROL_MANIFEST; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-UX-005

As an user of each supported role, I want to handle empty one-item and many-item lists.

- **Frontend steps:** Seed each catalog/list with 0, 1 and many permitted records; filter/open/select them.
- **Persisted/read-back result:** Empty/loading/pagination/selection behaviors are accurate and selection never falls onto a neighboring item.
- **Permission negative:** Hidden/disabled UI is never the only authority; every negative case includes direct server/resource/runtime verification for the relevant boundary.
- **Required verification:** REAL_BROWSER; ALL_PERSONAS; DESKTOP_LAPTOP_MOBILE; CONTROL_MANIFEST; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-UX-006

As an user of each supported role, I want to recover from API failures.

- **Frontend steps:** Inject bounded 400/401/403/409/429/500/timeout fixtures at user-action endpoints; exercise displayed retry.
- **Persisted/read-back result:** Each state has accurate recoverable feedback, draft preservation where relevant and no false success.
- **Permission negative:** Hidden/disabled UI is never the only authority; every negative case includes direct server/resource/runtime verification for the relevant boundary.
- **Required verification:** REAL_BROWSER; ALL_PERSONAS; DESKTOP_LAPTOP_MOBILE; CONTROL_MANIFEST; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-UX-007

As an user of each supported role, I want to ignore stale responses during rapid navigation.

- **Frontend steps:** Delay catalog/detail/save requests; switch panels/profiles/conversations; deliver old responses.
- **Persisted/read-back result:** Stale results cannot reclaim focus or expose data from a previous identity/context.
- **Permission negative:** Hidden/disabled UI is never the only authority; every negative case includes direct server/resource/runtime verification for the relevant boundary.
- **Required verification:** REAL_BROWSER; ALL_PERSONAS; DESKTOP_LAPTOP_MOBILE; CONTROL_MANIFEST; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-UX-008

As an user of each supported role, I want to survive offline and reconnect.

- **Frontend steps:** Open fixture chat; lose network; attempt supported action; reconnect; reload.
- **Persisted/read-back result:** Offline/error state is explicit and retry cannot duplicate mutation or lose acknowledged data.
- **Permission negative:** Hidden/disabled UI is never the only authority; every negative case includes direct server/resource/runtime verification for the relevant boundary.
- **Required verification:** REAL_BROWSER; ALL_PERSONAS; DESKTOP_LAPTOP_MOBILE; CONTROL_MANIFEST; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-UX-009

As an user of each supported role, I want to reload and update the PWA safely.

- **Frontend steps:** Open installed/PWA-style fixture; exercise reload/version-skew recovery and cached assets.
- **Persisted/read-back result:** Served assets belong to the intended candidate version and stale service-worker code does not masquerade as current QA.
- **Permission negative:** Hidden/disabled UI is never the only authority; every negative case includes direct server/resource/runtime verification for the relevant boundary.
- **Required verification:** REAL_BROWSER; ALL_PERSONAS; DESKTOP_LAPTOP_MOBILE; CONTROL_MANIFEST; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **NOT RUN**. No matching actual frontend execution evidence yet. All unasserted acceptance and permission requirements remain open.

#### US-SP-UX-010

As an user of each supported role, I want to retain downloadable evidence.

- **Frontend steps:** Exercise every delivered file/link/download path; compare fixture file names and hashes.
- **Persisted/read-back result:** Artifacts are actually retrievable with correct bytes by authorized actors and denied to outsiders.
- **Permission negative:** Hidden/disabled UI is never the only authority; every negative case includes direct server/resource/runtime verification for the relevant boundary.
- **Required verification:** REAL_BROWSER; ALL_PERSONAS; DESKTOP_LAPTOP_MOBILE; CONTROL_MANIFEST; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.

#### US-SP-UX-011

As an user of each supported role, I want to record browser errors and failed requests.

- **Frontend steps:** Collect pageerror, console errors and relevant failed/status responses during all executed stories.
- **Persisted/read-back result:** Every unexpected event is linked to a case with a finding or documented expected denial; none are silently ignored.
- **Permission negative:** Hidden/disabled UI is never the only authority; every negative case includes direct server/resource/runtime verification for the relevant boundary.
- **Required verification:** REAL_BROWSER; ALL_PERSONAS; DESKTOP_LAPTOP_MOBILE; CONTROL_MANIFEST; NEGATIVE_SERVER.
- **Priority / current status:** P1 / **PARTIAL**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All unasserted acceptance and permission requirements remain open.


## Current runtime additions

These appended IDs describe workflows discovered and exercised on the current candidate. Their narrower acceptance criteria reflect the tested operation; general cross-user security and all-persona requirements remain in the existing dedicated stories. Existing IDs are unchanged.

#### US-SP-CHAT-019

As an authorized chat user, I want to attach and remove files before sending.

- **Persona:** authorized chat user
- **Frontend steps:** Choose two synthetic text files in the real attachment picker; remove one; send the remaining file with a prompt; hard reload.
- **Expected persisted result:** The retained file uploads with exact fixture bytes; the tray clears after send; the persisted transcript retains its filename after reload and omits the removed file.
- **Permission / negative path:** A file removed before Send must not appear in the reloaded transcript.
- **Test requirements:** REAL_BROWSER; FILE_BYTES; DETERMINISTIC_PROVIDER; RELOAD
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.
- **Inventory basis:** CURRENT_RUNTIME_DISCOVERED
- **Source reference:** static/messages.js; tests/e2e/full/composer-content.spec.ts

#### US-SP-CHAT-020

As an authorized chat user, I want to cancel editing then edit and regenerate a response.

- **Persona:** authorized chat user
- **Frontend steps:** Send a fixture prompt; Edit message and Cancel changed text; edit again and submit; Regenerate response; hard reload.
- **Expected persisted result:** Cancelled text never persists; the edited user turn replaces the old text; regeneration completes and the reloaded conversation contains exactly one edited user turn.
- **Permission / negative path:** Cancel preserves the original text; editing and regeneration must not retain the replaced old user text or duplicate its user turn.
- **Test requirements:** REAL_BROWSER; DETERMINISTIC_PROVIDER; RELOAD
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.
- **Inventory basis:** CURRENT_RUNTIME_DISCOVERED
- **Source reference:** static/messages.js; tests/e2e/full/composer-content.spec.ts

#### US-SP-CHAT-021

As an authorized chat user, I want to save insert and delete a reusable prompt.

- **Persona:** authorized chat user
- **Frontend steps:** Open Saved prompts with an empty composer and attempt Save; enter a multiline prompt and save; reload; insert it; delete it; reload again.
- **Expected persisted result:** The empty save produces a visible error; exact multiline content is inserted with the documented separator; deletion removes the row and persisted prompt.
- **Permission / negative path:** An empty save attempt must show a validation error; deleting the selected prompt removes it after reload without silently reinserting it.
- **Test requirements:** REAL_BROWSER; RELOAD; NEGATIVE_VALIDATION
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.
- **Inventory basis:** CURRENT_RUNTIME_DISCOVERED
- **Source reference:** static/commands.js; tests/e2e/full/composer-content.spec.ts

### Runtime-discovered realtime voice acceptance

These cases use synthetic browser media/WebRTC with real application HTTP handlers, local sideband WebSockets, the engine, governance and persisted voice/task records. Physical audio quality and upstream-provider interoperability remain separate in VOICE-007.

#### US-SP-VOICE-009

As an authorized voice user, I want to hold a realtime conversation while preserving my typed draft.

- **Frontend steps:** Start voice; unmute; receive two synthetic spoken user/reply pairs; inspect transcript; end.
- **Persisted/read-back result:** Four exact turns appear in DOM and private voice journal; call ends and tracks stop.
- **Permission negative:** Typed draft stays intact; no chat turn, fallback speech request or duplicate response.create is submitted.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-010

As an authorized voice user, I want to dispatch one background job while continuing to speak.

- **Frontend steps:** Start voice; emit a duplicated dispatch event for one delayed file write; continue a second spoken exchange; expand completed task and open its chat.
- **Persisted/read-back result:** Exactly one child task writes exact fixture bytes; function result returns once; task link opens the persisted engine result.
- **Permission negative:** Duplicate provider dispatch must not create duplicate work; opening child leaves the voice call and unmuted microphone intact.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-011

As an authorized voice user, I want to end voice capture without canceling already-started background work.

- **Frontend steps:** Start voice; dispatch a delayed chat job; end the call while task is running.
- **Persisted/read-back result:** Provider call ends, voice bar hides, microphone track stops and the existing child later stores its expected result.
- **Permission negative:** Closing capture must not create another task or cancel the already-authorized child.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-012

As an authorized voice user, I want to approve an eligible voice-dispatched action once from mobile.

- **Frontend steps:** Start voice on390px viewport; dispatch real write; inspect waiting approval; continue speaking; press Allow once.
- **Persisted/read-back result:** Exact child session/approval identifiers reach the real approval endpoint; write occurs and task becomes done while voice stays open.
- **Permission negative:** No bytes are written before approval; only Allow once and Deny exist and horizontal overflow is absent.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P0 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-013

As an authorized voice user, I want to deny a voice-dispatched action from mobile.

- **Frontend steps:** Start voice on390px viewport; dispatch real write; inspect waiting approval; continue speaking; press Deny.
- **Persisted/read-back result:** Exact child session/approval identifiers reach the real endpoint; task reports its denied tool result and voice stays open.
- **Permission negative:** Target file remains absent before and after denial; only the two eligible one-shot decision controls appear.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P0 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-014

As an authorized voice user, I want to apply my automatic approval rules to a voice task.

- **Frontend steps:** Start voice as the automatic-approval fixture; dispatch a real write; await task and inspect audit.
- **Persisted/read-back result:** Controlled classifier approval allows exact bytes; automatic source/tool/decision and policy revision persist in audit.
- **Permission negative:** No manual approval controls appear and call identity remains unchanged; this tests deterministic classification plumbing.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P0 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-015

As an authorized voice user, I want to apply my automatic denial rules to a voice task.

- **Frontend steps:** Start voice as the automatic-denial fixture; dispatch a real write; await task and inspect audit.
- **Persisted/read-back result:** Controlled classifier denial leaves file absent; automatic source/tool/decision and policy revision persist in audit.
- **Permission negative:** No manual approval controls appear and call identity remains unchanged; no real-model judgment-quality claim follows.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P0 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-016

As an authorized voice user, I want to control microphone capture and interruption throughout a voice call.

- **Frontend steps:** Start muted; toggle mic twice; hold/release Space and pointer push-to-talk; interrupt native playback; send a typed turn then create another conversation.
- **Persisted/read-back result:** Track enabled state follows each control; interruption emits cancel plus output clear; session switch ends provider call and stops capture.
- **Permission negative:** Released push-to-talk cannot leave microphone enabled; playback must stop after interruption and capture cannot follow a different conversation.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-017

As an authorized voice user, I want to receive truthful feedback when voice microphone access is refused.

- **Frontend steps:** Deny synthetic getUserMedia; click voice; inspect toast, call inventory and bar.
- **Persisted/read-back result:** Explicit microphone refusal appears and voice bar remains hidden.
- **Permission negative:** No provider call is created and no successful recording or transcript is fabricated.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-018

As an authorized voice user, I want to stop browser capture when the server-side voice call ends.

- **Frontend steps:** Start voice; unmute; end this call using the authenticated real endpoint; inspect browser and status.
- **Persisted/read-back result:** Voice bar hides, track stops, provider is ended and subsequent status returns404.
- **Permission negative:** A removed server call cannot leave microphone capture active.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-019

As an authorized voice user, I want to cancel a pending voice launch without reviving an older one.

- **Frontend steps:** Hold two actual capability responses; launch/cancel first and launch second; release first; cancel second; release second.
- **Persisted/read-back result:** Voice remains closed with two capability reads and zero created peers.
- **Permission negative:** A stale first response cannot release or start the newer canceled launch.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-020

As an authorized voice user, I want to dispatch governed engine work in voice chat mode and inspect status.

- **Frontend steps:** Start voice; dispatch chat-mode read of a known fixture file; request get_work_status; inspect task row.
- **Persisted/read-back result:** Real read returns exact marker; status output identifies same child session, chat mode and done state.
- **Permission negative:** Task lookup must report the actual child and mode rather than a fabricated completion or parent conversation.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-021

As an authorized voice user, I want to dispatch two engine subagents through voice and receive their completion.

- **Frontend steps:** Start voice; dispatch subagents mode; await both actual children and parent continuation; request status.
- **Persisted/read-back result:** Persisted batch completion names both distinct child markers with exactly two completed statuses; task/result/status are done.
- **Permission negative:** Requested child goals alone are insufficient; both real completion outputs must exist before completion is reported.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-022

As an authorized voice user, I want to hear completed background results after current native playback finishes.

- **Frontend steps:** Start a slow job; begin native speech/audio playback; let job finish; emit response.done then audio-buffer.stopped.
- **Persisted/read-back result:** Result response.create count remains unchanged through response.done and increments once only after playback stops.
- **Permission negative:** A completed task cannot interrupt still-playing native audio merely because the model response is finished.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-023

As an authorized voice user, I want to see delegated work as running while an idle parent awaits delayed children.

- **Frontend steps:** Start voice subagent task with delayed children; observe parent idle and delegation pending; continue speaking; await continuation.
- **Persisted/read-back result:** Status shows agent_running false and delegation_pending true while voice task remains running; two child results persist and final pending/running flags clear.
- **Permission negative:** An idle parent must not be shown as done before its delayed children and continuation finish.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

#### US-SP-VOICE-024

As an authorized voice user, I want to preserve my original signed access restrictions after delegated work resumes.

- **Frontend steps:** Start voice as a restricted SSO fixture; dispatch two children and a parent follow-up attempting a denied write; await completion and inspect private authority proof.
- **Persisted/read-back result:** Both real child completions persist; captured email/group/profile and original denied glob remain; continuation returns file_denied_glob.
- **Permission negative:** Protected file stays absent after wakeup; reconstruction must not discard the original signed group restriction.
- **Required verification:** REAL_BROWSER; SYNTHETIC_MEDIA; REAL_HTTP_WS; REAL_ENGINE; AUTHORITATIVE_READBACK; NEGATIVE_STATE.
- **Priority / current status:** P0 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.

### Runtime-discovered tool outcome acceptance

#### US-SP-CHAT-022

As an authorized chat user, I want tool cards to show successful and denied outcomes accurately.

- **Frontend steps:** Perform a real successful write; expand its Processed details; read a file containing error-looking JSON; inspect settled cards and reload. Separately revoke workspace membership while a real write waits for Allow once; respond, settle, expand the denied card and reload.
- **Persisted/read-back result:** Successful write has exact bytes and successful write/read labels. Denied tool has a durable structured error, no file effect and a Failed label both settled and reloaded.
- **Permission negative:** File contents resembling an error must not turn a successful read into a failure. A denied write must not be labeled Updated or Updating after rebuild/reload.
- **Required verification:** REAL_BROWSER; REAL_ENGINE; RELOAD; AUTHORITATIVE_READBACK; NEGATIVE_STATE
- **Priority / current status:** P1 / **PASS**. Actual assertion mapping and report references: see this story row in [coverage-plan.csv](coverage-plan.csv). All stated acceptance assertions passed on a frozen source run with the current executable spec.
