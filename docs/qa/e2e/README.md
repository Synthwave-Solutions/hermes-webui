# Actual frontend E2E suite

This suite drives Chromium against the real WebUI server, real signed identities,
real file/session/policy persistence and the real Hermes agent. A loopback-only
OpenAI-compatible provider supplies deterministic synthetic responses. The suite
proves the application paths exercised by its assertions; it does not prove the
quality, uptime, OAuth credentials or behavior of an external provider.

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
all fixture process groups on success or failure. The operating-system home and credential config paths are private, the
environment excludes host secrets, and PATH excludes developer credential CLIs.
A Python audit guard rejects non-loopback DNS/connections and direct invocation
of listed credential CLIs in the server and its Python children; browser requests are limited to
loopback too. These test guards are not an OS sandbox for arbitrary native code.
The original run `20260908-202702-435893000` predates these guards: provider
discovery found a host GitHub CLI credential and attempted a Copilot token
exchange. Its blanket external-credential-isolation claim was incorrect. Keep
that run as historical evidence; use the subsequent isolated rerun for release
validation. Safe exports contain no credential values.
Scheduled test jobs deliver
locally; explicit Run now uses the deterministic provider, while duplicate jobs
are verified paused. Task-board fixtures are unassigned and never dispatched.
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

The configuration rejects non-loopback targets. Signed fixture sessions must
match the target base URL. The suite intentionally does not run against live
production data.

## Voice test boundary

`realtime-voice.spec.ts` replaces the physical microphone and browser peer with a
synthetic media transport. Native realtime events travel over an actual local
WebSocket, and the server sideband drives real authenticated HTTP routes, the
Hermes engine, actual delegated children, file effects, decisions and audit
records. It checks conversation continuity, dispatch deduplication, manual and
automatic review, task completion, revocation and teardown. This is not a test
of physical microphone capture, real WebRTC negotiation or OpenAI audio quality.
The official provider needs its own user-gesture microphone check before enablement.

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

External SSO/OAuth consent and physical-device authentication; actual
Nango/provider connections; email/Chat/Slack delivery; microphone capture and
real speech playback; real model quality; gateway scheduled ticks; real task
dispatch; package/plugin install
and removal; server restart/stop/update; larger virtualized history and races;
all keyboard and accessibility combinations; all conditional controls and
negative permission combinations remain distinct stories until their exact
scenario is exercised. The comprehensive user-story matrix should retain
NOT RUN or BLOCKED for these rows. Deterministic provider output must never be
reported as live external integration proof.
