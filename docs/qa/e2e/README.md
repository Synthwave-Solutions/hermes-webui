# Actual frontend E2E suite

This suite drives Chromium against the real WebUI server, real signed identities,
real file/session/policy persistence and the real Hermes agent. A loopback-only
OpenAI-compatible provider supplies deterministic synthetic responses. The suite
proves the application paths exercised by its assertions; it does not prove the
quality, uptime, OAuth credentials or behavior of an external provider.

## Install and run

Use Python 3.11–3.13 and an isolated virtual environment with the WebUI runtime
requirements and the matching Hermes engine installed. This is dev-only tooling;
the application has no new runtime dependency or build step.
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
starts WebUI and the deterministic provider on distinct ephemeral loopback ports,
runs `playwright.full.config.ts`, and stops both process groups on success or
failure. The real Hermes home, production sessions, production profiles, external
credentials and scheduling daemon are not used. Scheduled test jobs deliver
locally; explicit Run now uses the deterministic provider, while duplicate jobs
are verified paused. Task-board fixtures are unassigned and never dispatched.
Nango paths point to intentionally absent files inside private test state, so
the mobile Connections test checks the visible unavailable-service response.
Private browser cookies and the generated login password stay in the test-state
directory. Do not publish that directory or raw trace archives without review.
The terminal fixture explicitly uses `/bin/sh` with a sanitized environment.
`run.json` records repository revisions and SHA256 hashes for tracked and
untracked source files before and after execution. A changed source fingerprint
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
