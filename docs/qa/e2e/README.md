# Actual frontend E2E suite

This suite drives Chromium against the real WebUI server, real signed identities,
real file/session/policy persistence and the real Hermes agent. A loopback-only
OpenAI-compatible provider supplies deterministic synthetic responses. The suite
proves the application paths exercised by its assertions; it does not prove the
quality, uptime, OAuth credentials or behavior of an external provider.

## Verified release evidence

Frozen run `20260909-184341-281192000` completed **235 browser scenarios: 235 passed, zero failed**. Collected application errors: 0. Report-level errors: 0. Reporter bookkeeping warnings: 17, preserved separately.

The original runner manifest has no structured execution-host field; a platform is not inferred from the artifact path. Separate host and cleanup receipts retain their own scope.

Raw inventory: **1265 entries, 623 interacted with and 642 without interaction evidence**. The strict all-click gate remains incomplete. The 365-story catalog has 23 fully demonstrated, 220 partial, 122 not run. A passing scenario establishes its explicit assertions only. [Supplemental acceptance stories](supplement-user-stories.md) describe the added 43 executable cases and their precise setup and provider boundaries.

Focused backend verification: **749 WebUI tests across 65 files** at `90cc10318788db857464663b1874d28eb1e50430` and **453 engine tests across 32 files** at `b0aaa74f9dcfe9e7caa4692656b4535ce04104e1`. Exact selectors, scope and baseline qualifications are in [backend verification](backend-verification.md). These results do not certify repository-wide CI.

Share create/read/refresh/revoke and Todo-to-Done regressions pass. Supplemental coverage verifies CLI manual floors despite automatic review, per-tool MCP denial, project revocation, knowledge selection conflicts, long-history races, exact file previews, real clarification and Kanban worker completion, distinct main/auxiliary model routing, Cron execution and extension lifecycle. Knowledge document retrieval and real vendor gallery/OAuth delivery are not implied by catalog or transport-fixture tests.

Deployment is evidenced separately by `outputs/synthpulse-e2e/production-release-status.json` in the delivered artifact bundle. Browser tests do not prove live deployment.

The separate voice handoff records initial-release production audio evidence. Its source pair and real-provider synthetic-audio scope are distinct from this isolated browser run. Physical Mac microphone/speaker capture remains unverified.

## Install and run

Use Python 3.11–3.13 and an isolated virtual environment with the WebUI runtime
requirements and the matching Hermes engine installed. The browser tooling is development-only. The separate realtime voice
implementation adds its documented server dependency; see `docs/realtime-voice.md`.
Run the commands from the WebUI repository root with the matching engine checkout
at `../hermes-agent`. A copied test kit must retain `tests/e2e/full`,
`scripts/e2e`, and `playwright.full.config.ts` at these paths inside that checkout;
the kit does not contain the application or engine. Node.js and the `uv` Python
environment manager must be installed. The tested local environment used Python
3.12 and Playwright 1.55.1 with Chromium.

```sh
uv venv --python python3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip install --python .venv/bin/python -e ../hermes-agent
npm install --prefix ../e2e-tooling --no-audit --no-fund @playwright/test@1.55.1
../e2e-tooling/node_modules/.bin/playwright install chromium
.venv/bin/python scripts/e2e/run_full.py --engine ../hermes-agent
```

The runner creates a new private `e2e-runs/<timestamp>/e2e-state` directory,
starts WebUI, the deterministic engine provider and a realtime protocol provider
on distinct ephemeral loopback ports, runs `playwright.full.config.ts`, and stops
the three fixture process groups on success or failure. Detached native/PTY descendants need a separate ownership-verified census; process-group shutdown alone is not universal cleanup proof. The operating-system home and credential config paths are private, the
environment excludes host secrets, and PATH excludes developer credential CLIs.
A Python audit guard rejects non-loopback DNS/connections and direct invocation
of listed credential CLIs in the server and Python children that retain the bootstrap environment. The primary browser context blocks non-loopback HTTP/WebSocket requests. Additional contexts and APIRequestContext calls do not inherit those hooks; their current test URLs are explicitly local. The embedded native PTY keeps the private HOME but does not retain the Python bootstrap guard. These test guards are not an OS sandbox for arbitrary native code.
The original run `20260908-202702-435893000` predates these guards: provider
discovery found a host GitHub CLI credential and attempted a Copilot token
exchange. Its blanket external-credential-isolation claim was incorrect. Keep
that run as historical evidence; use the subsequent isolated rerun for release
validation. Safe exports contain no credential values.
Scheduled test jobs deliver
locally; explicit Run now uses the deterministic provider, while duplicate jobs
are verified paused. Task-board fixtures also launch a real isolated Kanban worker, verify claim and completion, and use the deterministic local provider.
Nango paths point to intentionally absent files inside private test state, so
the mobile Connections test checks the visible unavailable-service response.
Private browser cookies and the generated login password stay in the test-state
directory. Do not publish that directory or raw trace archives without review.
The terminal fixture explicitly uses `/bin/sh` with a sanitized environment.
`run.json` records repository revisions and SHA256 hashes for tracked and
untracked source files before and after execution. Generated QA documentation
under `docs/qa/e2e/` is excluded to avoid hashing a run's own exported result. A changed source fingerprint
invalidates the run even if its individual assertions passed.

`--grep <pattern>` selects test titles; `--out <directory>` selects run storage.
`QA_PLAYWRIGHT_CLI` can point at another installed `@playwright/test/cli.js`.

For an already running instance created by `server_fixture.py`, use:

```sh
QA_BASE_URL=http://127.0.0.1:19086 \
QA_SESSIONS=../e2e-state/browser-sessions.json \
QA_OUT=../e2e-results \
NODE_PATH=../e2e-tooling/node_modules \
../e2e-tooling/node_modules/.bin/playwright test -c playwright.full.config.ts
```

Use clean application and engine checkouts without an engine-root `.env`, and a machine without an active `/etc/hermes` managed configuration. Private HOME does not disable those engine fallback sources. Both prerequisites were verified absent for this run. Dependency versions and native executables are not pinned by the source digest; review/install them separately.

The configuration rejects non-loopback targets. Signed fixture sessions must
match the target base URL. The suite intentionally does not run against live
production data.

Files named `scripts/e2e/production_*` are separately invoked operator tools for an explicitly authorized production operation. The isolated runner does not execute them; their presence in this kit is not evidence that they ran during the browser suite.

`scripts/e2e/operator_vps_full.py` is a separately invoked supervisor for a dedicated disposable Linux QA unit, and `scripts/e2e/remote_evidence.py` separately exports/imports hash-verified allowlisted evidence. The normal browser suite does not invoke these operator entry points. Their source fingerprints and actual execution/transport receipts are separate from frontend acceptance; inclusion in the test kit alone does not prove they ran. Python bytecode writes are suppressed for fixture processes; this is not an OS sandbox or an enforced read-only filesystem boundary.

## Voice test boundary

`realtime-voice.spec.ts` replaces the physical microphone and browser peer with a
synthetic media transport. Native realtime events travel over an actual local
WebSocket, and the server sideband drives real authenticated HTTP routes, the
Hermes engine, actual delegated children, file effects, decisions and audit
records. It checks conversation continuity, dispatch deduplication, manual and
automatic review, task completion, revocation and teardown. This is not a test
of physical microphone capture, real WebRTC negotiation or OpenAI audio quality.
Separate production receipts record actual WebRTC negotiation and two controlled audio turns. A physical Mac microphone check remains separate.

## Private continuation authority

An authenticated async delegation captures the initiating user's verified email
and SSO group claims, plus the original governance ceiling, in a private
`STATE_DIR/continuation-authority/<opaque-id>.json` record. The directory is
created with mode `0700` and records with `0600`. Ordinary chat turns create no
record: persistence occurs only when an actual async producer captures its
reference. Nested jobs and resumed turns reuse that original reference.

These records contain identity and policy data, not authentication cookies or
provider tokens. Exclude this directory, the private state database, signed
browser sessions, and raw traces from shareable evidence. Back up continuation
authority together with the async job ledger when preserving restart recovery.
Actual job records are retained for durable and delayed completion delivery;
there is no time-based expiry or automatic deletion that could invalidate an
unfinished job. Operators may delete a record only after its referenced jobs and
pending completion deliveries are finished or explicitly discarded. Missing,
foreign-session or malformed references fail closed for authenticated async
continuations.

Storage is capped at 10,000 records of at most 256,000 bytes. Once full, the
trusted producer rejects a new async dispatch before it starts; existing refs
and delayed jobs continue normally. The `created_at` timestamp supports operator
review, but age alone does not prove a record is safe to remove. Creation is
serialized across threads and, on the supported Linux/macOS deployment, across
processes with an advisory file lock. Archive completed/discarded jobs and their
unused authority records before admitting more work. Ownerless legacy sessions
with authentication globally disabled retain their existing no-ref behavior;
owned or shared sessions never use that exception.

Every continuation rechecks current local governance policy and local
conversation, project, workspace and bot access. It also keeps the original
job's ceiling, so later policy expansion cannot broaden that job. Captured SSO
group claims are retained; this is not a fresh IdP token validation or external
group-membership lookup. External IdP revocation therefore needs an
authoritative local policy revocation or a separately configured fresh identity
resolver to stop an already dispatched durable job.
The retained ceiling applies to hard permissions and resource restrictions.
Manual versus automatic review and the reviewer prompt use the current
administrator policy; continuations do not apply a second historical approval
flow on top of the current one.

## Evidence and failure rules

Each test keeps a screenshot and a JSON record of browser controls and actual
click, context-menu, double-click, keyboard, change and input events across page reloads and split frames (without recording typed values). Failed tests retain Playwright traces and video. The JSON
report records every status; tests have no conditional pass, skip, retry or
forced click. Setup omissions fail visibly. Assertions check rendered state and,
where relevant, persisted backend state after actual frontend actions.

Navigation and tab tests assert reachability only. They do not stand for testing
all controls inside a tab. Download tests inspect the actual downloaded content.
Knowledge upload tests distinguish upload from explicit selection. Group/project
tests use named synthetic participants. Policy tests verify the saved schema,
legacy omission preservation and negative authorization behavior separately from
AI action-decision execution.

The runtime governance tests send actual chat requests through the real engine,
park real file writes pending manual review, approve or deny through the visible
card, and assert exact on-disk effects. The automatic flow invokes a second real
HTTP model request against the deterministic reviewer and checks approval,
denial, and uncertain-to-manual outcomes. Delegation tests create two actual
child agents and verify their results. Session task-list tests exercise the real
agent tool because the current Todos panel is read-only.

## Control inventory and certification gate

```sh
.venv/bin/python scripts/e2e/coverage_gate.py \
  ../e2e-runs/<run>/results/results.json \
  --out ../e2e-runs/<run>/control-coverage.json --require-complete
```

The inventory combines IDs extracted from current HTML/JavaScript templates with
controls observed in real browser states. An action counts only when its test
passed. `INTERACTED_IN_PASSING_TEST` means the interaction occurred within a
passing scenario; it does not claim a separate semantic assertion for every
control. `NOT_INTERACTED` remains an explicit gap. Dynamic states that were never
opened are outside the observed count and remain a coverage limitation. The
`--require-complete` command exits nonzero while any known control is untested or
any test failed. Do not drop the flag, silently waive rows or equate navigation
coverage with full certification.

`executed-scenarios.csv` and `execution-summary.json` exported from the Playwright
report describe semantic test outcomes. Test title identifiers are retrieval
labels; they do not automatically certify every acceptance criterion in a
similarly numbered user story. Reconcile the story matrix against the exact
assertions and keep partial coverage explicit.

## Areas requiring additional environment or scenarios

External SSO/OAuth consent, physical-device authentication, actual vendor/Nango connections, delivery to people, physical microphone/speaker acoustics, production-model judgment, real gateway scheduled ticks, service restart/update controls, and the remaining keyboard/accessibility/conditional permission combinations require their own evidence. Current supplements do exercise a real isolated Kanban worker, long-history navigation/races, and synthetic local extension installation/removal. Those specific paths must not remain labeled wholly unrun, and their local provider/archive boundaries must not be presented as external integration proof. Consult the current story matrix for each remaining clause.

The terminal uses the committed xterm distribution files under `static/vendor`, with the existing versions and SRI hashes. The browser suite verifies that all four assets load from the application origin before checking actual shell command and restart effects. Activity-layout-specific scenarios select their required persisted layout explicitly through Settings; they cannot rely on the previous case leaving a particular preference.

Review the [acceptance stories](user-stories.md), [coverage matrix](coverage-plan.csv), [remaining clicks](remaining-clicks-priority.md) and [focused backend verification](backend-verification.md). The [review notes](run-review-notes.json) retain earlier failures and reporter warnings.
