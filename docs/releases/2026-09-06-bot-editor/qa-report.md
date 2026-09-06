# SynPulse bot editor and knowledge files

## Change

Existing bot section buttons previously discarded the selected section and opened Identity. Existing bots now have six directly selectable tabs, with an explicit Edit bot entry point and Save bot from any tab. Drafts survive tab switches. Knowledge files use native file selection, upload, filtering and explicit Save knowledge, with per-bot storage.

## Verification

- 326 focused and neighboring tests passed through the canonical repository runner.
- Actual signed-account Chromium QA: all tabs, section deep links, two distinct bot edits/save/reload, selected skills, shared bot memory, and permission denials.
- File input uploaded two real synthetic documents; neither was automatically selected. Selection and filter persisted correctly after explicit save and reload. Other-bot catalog stayed separate; forged selection denied (400), unauthorized manage requests denied (403), path traversal denied (400).
- Shared bot memory is in BOT_MEMORY.md. Legacy private USER.md/MEMORY.md sentinels remained unchanged and absent from shared prompt. Revoked/unauthorized actor received no shared memory.
- Actual engine tool policy permits a selected document when the sender has its read-root grant and denies an unrelated-root grant. Selecting bot knowledge does not grant file access or bypass approvals.
- Desktop, laptop and fresh 390px mobile browser evidence; no horizontal page overflow and no JavaScript errors.
- New tab behavior browser regression failed on unchanged baseline at missing tab selector and passed the candidate.
- Builder publication rollback, stale revision, symlink denial and concurrent appearance/config save tests passed.

## Scope and limitations

Knowledge is a file reference library, not vector RAG. File contents are read by governed tools; extraction support depends on the selected tool and format. No real colleague messages or personal data were used for QA. Uploading alone does not select a file. Existing workspace references remain unchanged. General-suite collection failures and broader reconciliation failures were already recorded on the prior release; this change does not claim to fix them. Gateway degraded probes remain a separate existing condition.

## Release

Candidate awaits dev → staging → master promotion and live source/health verification. Production evidence is recorded separately after deployment.

## Live-catalog follow-up

A read-only check using the actual authorized editor and default profile found 554 selected skills and 154 selected CLI tools. Existing GET worked, but unchanged save validation rejected CLI count above100. Three regression tests reproduce those counts and fail the previous code. The fix retains the 10,000-entry bound plus actual-catalog/current-grant checks and removes the contradictory100 limit. Tests cover save, narrowing/restoring, new bots, unavailable commands and10001-entry rejection. Production user data is not mutated by the read-only validation check.

The same real configuration also exposed a second stale validation: unchanged configured model/provider was rejected when live discovery did not advertise it. Editing existing bot settings now preserves the exact persisted model/provider without querying live availability, while model/provider grants remain required. New or changed model selections still validate against provider availability. Regression tests cover all three cases.
