# SynPulse chat and bot setup: QA report

Date: 6 September 2026. This report uses synthetic QA identities and data. Production promotion and live verification are recorded in the linked release note.

## Acceptance coverage

| Area | Verification |
|---|---|
| Chat / Super agent | Real mode request, persisted selection after reload, pending-state lock and correct worker dispatch. Top switch inspected on desktop, laptop and mobile. |
| Voice and navigation icons | One visible realtime waveform action, separate dictation microphone, distinct Connections and My approvals icons. User-facing capability and error messages contain no OpenAI/key/billing language. |
| Bot recipient selection | Personal bot selection opens that bot; group selection targets its literal bot ID. Two signed users and two bots completed messages in one group; outsider access was refused. |
| Bot photo | Real PNG upload accepted; independently decoded as 512 × 341 pixels. Image survives full reload and appears in the chat avatar row. |
| Guided bot setup | Bounded creator completed all four steps. No POST before final save. Prompt, selected skill/MCP/CLI, users and group persisted; editing and photo reload passed. An unavailable CLI selection was refused. |
| Managed bot execution | Both owner and group member completed real composer → worker → deterministic provider turns. Stored bot instructions reached the model request; the caller's remaining permissions still limited the actual tool surface. |
| Personal memory | Alice, Bob and an administrator each used their own four synthetic private markers. Spoofed body identities did not alter ownership. Foreign-user and foreign-session reads were refused. Shared group requests contained no private markers. |
| Personal navigation | Signed member clicked Memory and all four personal sections at 1440-pixel desktop and 390-pixel mobile widths. No data writes, page errors or horizontal overflow. |
| File boundaries | Generic file/list/media routes checked direct, escaped and symlink paths. Engine file tools check the same private scope. |
| Approval and delegation | Engine regressions verify that refreshed human permissions are intersected with the immutable bot ceiling, including project-file exceptions and delegated context. |
| Revocation and legacy routes | Fresh active-cookie ACLs, explicit targets, owner-only configuration writes, private clone/delete and transaction rollback have independent review and regression coverage. Final real-browser revocation results are listed below. |
| Compatibility and ownership | Bootstrap-only administrators can edit their own bots. The explicitly auth-disabled legacy Gateway route is retained; 18 dispatch cases cover the route contract. |
| Terminal outcomes | Actual normal and terminal lifecycle checks passed. Terminal errors persist as authoritative outcomes; stale-run events cannot overwrite a newer run. |
| Loading feedback | Reproduced the persistent “Loading conversation…” placeholder on an empty chat; it now disappears after successful hydration. |
| Browser lifecycle | Delayed catalog/save responses cannot reclaim a different panel; Back/Continue cannot double-submit a pending save. |

## Automated results

Final focused WebUI result: **282 passed in 18.45 seconds**, on code commit `f93bac36`, with the paired engine selected explicitly through `HERMES_WEBUI_AGENT_DIR`. The isolated browser suite passed all **13 checks**, with no page errors, at 1440 × 950, 1024 × 768 and 390 × 844.

The focused GitHub workflow runs these 282 tests, recipient rules, full-page browser smoke, the guided-builder browser regression and both normal and terminal-error Gateway lifecycle checks. Both actual lifecycle checks passed locally on the final patch, including preserved activity and hard-reload parity. Six Gateway regressions cover session identity, stale-run refusal, durable error state and redaction before storage, journal and live delivery.

The neighboring session/profile authorization tests are included in this total. Two older session doubles were corrected to implement the existing `save()` lifecycle method, without changing runtime behavior.

The real revocation rerun passed: a retained selected-bot cookie no longer exposes the bot in the list, and avatar, builder, direct chat and group chat return HTTP 403. Misleading query parameters do not bypass the refusal. No provider request is dispatched. The worker's early-access-error path also has a regression test so an asynchronous revocation emits a visible access error and clears runtime state.

Engine: **101 passed, 2 skipped** in the combined memory, file-tool, bot-ceiling and approval-provenance run. The two skips are explicitly native Windows-only tests on Linux. The focused GitHub workflow passed on engine commit `ec698c918c04d69e88df4516a2ff998074269098`.

Independent review additionally reran the builder/personal-context regressions and the actual approval-ceiling tests. These overlap the combined suites and must not be added to the totals.

The initial focused GitHub run exposed a test dependency on the VPS's installed skill library. It now uses a real synthetic skill in a temporary directory, so normal-mode exclusion is checked identically on a clean CI host and the VPS.

## Known baseline and evidence boundaries

- Full WebUI CI had 11 collection errors at production base `27861048`; the current comparison has 10, still caused by missing upstream symbols. The broad suite never reached test execution and is not green. The existing workflow is retained; focused release results do not replace or imply a passing broad suite.
- Existing full engine Python, Windows and Nix jobs use custom runner labels unavailable in this fork. Focused actor/bot checks run on standard Ubuntu runners. Queued jobs are not reported as passed.
- Browser QA uses the real local WebUI and engine, signed synthetic identities, and a deterministic loopback completion provider. No real colleagues were impersonated and no customer tools were executed.
- An external microphone/WebRTC/speech-provider conversation was not exercised by these automated tests. Capability UI and error handling were tested separately.
- Personal storage is isolated at the application and governed file-tool level. Separately privileged host administrators or terminal tools remain an operating-system trust boundary.
- Existing shared bot memory is preserved, not automatically copied to users. Historic bot instructions should be reviewed for personal data before sharing.

## Evidence files

Sanitized reports: `privacy-browser-report.json`, `builder-alice-qa.json`, `builder-access-qa.json`, `builder-runtime-provider-qa.json`, `builder-revocation-qa.json`, `memory-nav-qa.json`. Screenshots: desktop chat, mobile chat, uploaded avatar editor, mobile bot review, and personal navigation at desktop/mobile widths. Private fixture session cookies are excluded from deliverables.

Unchanged legacy skill selections were also verified above the former 100-item limit. The live default profile has 554 catalogued skills; editing its other fields preserves the existing installed skill tree and previous wildcard skill behavior.

## Promotion and live verification

The engine production branch is `main`; the WebUI production branch is `master`. Promotion proceeds through `dev` and `staging` in both repositories. Exact promotion commits and the deployment/live-check outcome are maintained in the [project release note](https://www.notion.so/3d3937f18d888101811dfbaf63083725), alongside this QA evidence. The release-note status distinguishes prepared code from verified live deployment.
