# SynthPulse WebUI: the fork, and how it ships

This repository is Synthwave Solutions' fork of [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui),
the vanilla-JS web interface for the Hermes agent. Upstream wrote the application:
the three-panel chat UI, sessions, workspace browser, profiles, voice, themes,
the passkey/password/OIDC login surface, the launchers (`bootstrap.py`,
`start.sh`, `ctl.sh`), the Docker variants and the test suite. Everything in this
file describes what our fork ADDS on top of that, and how the result reaches a
client.

Inside the SynthPulse product the fork is called the **SynthPulse WebUI**: the
governed, multi-user team dashboard of the Agentic Workstation. One deployment,
one account per person, one access policy.

- What is ours versus upstream, plus the refresh procedure: [SYNTHPULSE-UPSTREAM.md](SYNTHPULSE-UPSTREAM.md)
- Code-level reference for the governance, isolation and auth additions: [SYNTHPULSE-GOVERNANCE.md](SYNTHPULSE-GOVERNANCE.md)
- Original design notes written during the build: [governance-port-design.md](governance-port-design.md), [user-isolation-design.md](user-isolation-design.md)

## Where this sits in the SynthPulse product

The hub repository `synthpulse-agentic-workstation` is the deliverable: it owns
the docker compose stack, the terraform roots, the client lifecycle CLI
(`bin/synthpulse client new|render|doctor|deploy|status|teardown|verify` driven by
`clients/<name>/client.yaml`), the modules and the customer documentation set.
This repository is one of the components that hub builds into an image.

Two web surfaces exist in a deployment and they are not alternatives. The engine
dashboard (inside the `core` container) is an operator console for one person
behind a single shared password. This WebUI is the product for a team: identity
per person, authorization enforced server side on every request, and per-user
isolation of sessions, projects, workspaces and skills.

Family of repositories: `synthpulse-agentic-workstation` (hub and deliverable),
`hermes-agent` (our engine fork), **`hermes-webui` (this repo, the team
dashboard fork)**, `synthpulse-swarm`, `hermes-desktop`, `synthpulse-ios`,
`synthwave-omniroute`, `opendesign-app`, `synthwave-skills`, `workspace-cli`,
`synthwave-templates`.

## How this repo reaches a client

Nothing here is deployed from a checkout. The hub bakes a pinned commit of this
fork into a container image, and the client runs the image.

| Step | Where it happens | Detail |
|---|---|---|
| Pin | hub `Dockerfile.webui` | `ARG SP_WEBUI_REF=<40-char commit sha>` plus `ARG SP_WEBUI_REPO`. The clone is a FULL clone followed by `git checkout`, never `--depth 1`: a shallow clone cannot check out an arbitrary commit, and having the ref in the `RUN` line is what busts the layer cache on a bump |
| Base image | hub `Dockerfile.webui` | `FROM ${SP_CORE_IMAGE}` (default `ghcr.io/synthwave-solutions/synthpulse-agentic-workstation:latest`). NOT a slim Python image, because this app imports the engine in-process, see below |
| Build and publish | hub `.github/workflows/docker-image.yml`, job `build-webui` | Runs after `check-pins` and `build` (it consumes the core tag that run just pushed), reads the `SP_WEBUI_REF` default straight out of `Dockerfile.webui` so a local build and CI cannot disagree, and pushes `ghcr.io/synthwave-solutions/synthpulse-webui` for `linux/amd64` and `linux/arm64`. Tags: `edge` on the hub's `main`, `{{version}}` on a semver tag, and `latest` on a `v*` tag |
| Run | hub `docker-compose.yml`, service `webui` | Compose profile `webui`, container `synthpulse-webui`, `depends_on: [core]`, one named volume mounted at the engine home, and the client secrets directory mounted read-only |
| Reach | hub `modules/ingress/Caddyfile` | `webui.{$SP_DOMAIN}` reverse-proxies to `webui:8787`. The service publishes NO host port, on purpose: TLS terminates at the ingress and the `X-Forwarded-*` headers the OIDC redirect and the secure cookie depend on are set there. A cloudflared hostname pointing at `http://webui:8787` is the alternative |
| Start | hub `modules/webui/webui-entrypoint.sh` | Installed as `/usr/local/bin/synthpulse-webui`, run under `tini`. It maps the product-facing `SP_WEBUI_*` names onto the `HERMES_WEBUI_*` names this server reads, creates the state tree, checks two preconditions that otherwise fail silently (engine importable, governance policy present) and then execs `server.py` with the ENGINE interpreter |

Client-facing turn-on, key map (`webui.enabled`, `webui.sso.*`,
`webui.hidden_tabs_default`), backup, the policy apply chain and the
troubleshooting table live in the hub repo: see the hub repo `docs/WEBUI.md`,
with `docs/CLIENT-CONFIG.md` for the `client.yaml` keys. The hub has no
`docs/GOVERNANCE.md`: the policy file's own shape is documented in the engine
fork's `docs/dashboard-governance.md`, and the operator-facing procedure in the
hub's `skills/synthpulse-governance/SKILL.md`.

### Why the image is not slim

The WebUI imports the engine **in-process**: its agent runtime does
`from run_agent import AIAgent` inside the long-lived server process, and the
supported launch runs `server.py` with the engine interpreter. So the engine
checkout and the engine venv must sit on the same filesystem as this source
tree. That is why `Dockerfile.webui` is `FROM` the core image (which already
carries the engine checkout at a pinned `SP_ENGINE_REF` plus its venv) and adds
only this source plus the two hard dependencies from `requirements.txt`
(`pyyaml`, `cryptography`) into that venv. A standalone slim image serves pages
and then fails every chat turn.

Upstream does ship an HTTP escape hatch (`HERMES_WEBUI_CHAT_BACKEND=gateway`,
which talks to the engine gateway over the network), which would allow a
genuinely slim image. It is not the default code path and the non-chat surfaces
still resolve an engine directory, so it stays a scoped decision with its own QA
rather than a free swap.

### What the image build strips

The build removes `.git` (roughly 270 MB of history no client needs), `tests/`,
`CHANGELOG.md`, editor/ops `*.bak*` files and `__pycache__`, and stamps the
resolved commit into `.sp-webui-ref`. In-app self-update and rollback are off by
design: image tags are the update mechanism. Optional Office parsers
(`python-docx`, `openpyxl`, `python-pptx`) are installed only when the image is
built with `SP_WEBUI_WITH_OFFICE=1`; without them the workspace preview routes
answer 503 with an install hint, which is upstream behaviour and not a failure.

## Running and building locally

Upstream's launchers are unchanged and remain the supported way to run a
checkout. They discover an engine install, create a local venv and start the
server on port 8787:

```bash
python3 bootstrap.py     # repo bootstrap (venv, discovery, launch)
./start.sh               # shell launcher
./ctl.sh start           # background daemon; also status | logs | restart | stop
```

Tests go through the repo script, which pins execution to Python 3.11 to 3.13,
creates or reuses `.venv` and installs the dev test dependencies:

```bash
./scripts/test.sh                                  # whole suite
./scripts/test.sh tests/test_governance_enforce.py # one file
```

The lint gates CI runs can all be run locally:

```bash
python3 -m compileall -q api server.py bootstrap.py mcp_server.py tests scripts
python3 scripts/ruff_lint.py --diff origin/master   # new/changed lines only
python3 scripts/scope_undef_gate.py                 # cross-file JS scope gate
npm install --no-save eslint@^10
npx eslint --no-config-lookup -c eslint.runtime-guard.config.mjs "static/**/*.js"
```

There is no frontend build step: `static/*.js` is served as written, so a page
reload picks up an edit.

To exercise the code the way a deployment runs it (engine imported in-process,
governance policy from an explicit path), point the server at an engine checkout
and an isolated state tree instead of your real `~/.hermes`:

```bash
HERMES_HOME=/tmp/sp-engine-home \
HERMES_WEBUI_STATE_DIR=/tmp/sp-webui-state \
HERMES_WEBUI_GOVERNANCE_POLICY=/tmp/sp-engine-home/dashboard-governance.yaml \
HERMES_WEBUI_AGENT_DIR=/path/to/hermes-agent \
/path/to/hermes-agent/venv/bin/python server.py
```

To build and run the container image, do it from the hub checkout, not here:

```bash
# in synthpulse-agentic-workstation
docker compose build webui        # builds core first, hands it over as the `base` context
SP_WEBUI_REF=<sha> docker compose build webui   # test a fork bump before baking it in
docker compose --profile webui up -d webui
```

## CI in this repository

The workflows under `.github/workflows/` are upstream's and we have not changed
them. What they do:

| Workflow | Trigger | What it does |
|---|---|---|
| `tests.yml` | PR and push to `master` | `changes` detects a docs-only change set (fails safe), `lint` runs the compileall/ruff/ESLint/scope gates, and `test` runs pytest across Python 3.11, 3.12 and 3.13 with the suite split into 5 `pytest-shard` shards per version |
| `browser-smoke.yml` | PR and push to `master` | Boots the real `server.py` agent-free and loads the key pages in Chromium, failing on any console error |
| `conversation-lifecycle.yml` | path-filtered PR and push | Informational browser gate for the chat render/streaming surface |
| `docker-smoke.yml` | path-filtered PR and push (`Dockerfile`, `docker_init.bash`, `docker-compose*.yml`, and so on) | `docker compose up`s the three upstream compose variants against a real daemon |
| `docs-ci.yml` | docs paths | A minimal rendering-break check plus a non-blocking link check. Not a style linter |
| `native-windows-startup.yml` | `start.ps1` changes | Validates the Windows launcher's path discovery |
| `release.yml` | `v*` and `exp-v*` tags | Creates a GitHub release and pushes a multi-arch image to `ghcr.io/<owner>/<repo>` |

Two honest notes about publishing. `release.yml` is upstream's release train: it
uses `ghcr.io/${{ github.repository }}`, so a `v*` tag pushed on this fork would
publish under our organisation rather than upstream's. That is not our delivery
path. **The SynthPulse image is built by the hub** (`build-webui`, above) from a
pinned commit, so nothing here needs to be tagged or published for a client to
get an update.

## Configuration that matters

Upstream's discovery table (state dir, default workspace, port) is in the
[README](../README.md) under "Configuration & access". The variables below are
the ones a SynthPulse deployment sets, and the ones our own code reads. Secrets
are marked; never commit a value for those.

| Variable | Default | Purpose |
|---|---|---|
| `HERMES_HOME` | `~/.hermes` | Engine home. Profiles, the governance policy and the audit trail are resolved from it |
| `HERMES_WEBUI_STATE_DIR` | `$HERMES_HOME/webui` | Sessions, `workspaces.json`, settings, shares, `skill_ownership.json`. The only tree that must be persisted |
| `HERMES_WEBUI_GOVERNANCE_POLICY` | `$HERMES_HOME/dashboard-governance.yaml` | Explicit path to the shared policy file |
| `HERMES_WEBUI_DEFAULT_HIDDEN_TABS` | empty | Comma separated sidebar panels hidden on a fresh install. Deployment baseline only: a stored user value wins. `chat` and `settings` are always visible. SynthPulse sets `logs` |
| `HERMES_WEBUI_USER_ISOLATION` | on (`0`/`false` disables) | Per-user ownership filtering of sessions, projects, workspaces and skills |
| `HERMES_WEBUI_ADMIN_SEES_ALL` | on (`0`/`false` disables) | Whether admins see other people's rows in list views. The SynthPulse compose service sets `0` |
| `HERMES_WEBUI_DEFAULT_OWNER` | unset | Owner stamped on rows created without a request identity (CLI, cron, imports) |
| `HERMES_WEBUI_PASSWORD` | unset | **Secret.** The break-glass password login |
| `HERMES_WEBUI_PASSWORD_IDENTITY` | a hardcoded operator address in `api/auth.py` | Identity attached to local password/passkey logins. Always set this explicitly in a deployment; the built-in fallback is a single-owner convenience, not a deployment default |
| `HERMES_WEBUI_REQUIRE_SSO_FIRST` | off | Turns the login into mandatory two-step: SSO first, then the password |
| `HERMES_WEBUI_OIDC_ISSUER` / `_CLIENT_ID` / `_REDIRECT_URI` / `_SCOPES` | unset / `openid profile email` | OIDC login |
| `HERMES_WEBUI_OIDC_CLIENT_SECRET` | unset | **Secret.** OIDC client secret |
| `HERMES_WEBUI_OIDC_ALLOW_CLAIM` / `_ALLOW_VALUES` | unset | Login allowlist: which claim is checked and which values pass |
| `HERMES_WEBUI_DISABLE_JIT_PROVISION` | unset | Set to disable just-in-time provisioning of a verified SSO identity |
| `HERMES_WEBUI_TRUST_FORWARDED_PROTO` / `_HOST` | off, off (both opt-in) | Required behind the ingress: without them the OIDC redirect is rebuilt as `http://` and the secure cookie is dropped, so login loops |
| `HERMES_WEBUI_TRUST_FORWARDED_FOR` | off | Trust forwarded client-IP headers in the unauthenticated onboarding local-origin gate and the TTS rate-limit key |
| `HERMES_WEBUI_TRUSTED_PROXY_CIDRS` | unset | Set by the hub compose service, but **currently inert in this fork**: the trusted-proxy allowlist upstream added is not present in our tree. See [SYNTHPULSE-UPSTREAM.md](SYNTHPULSE-UPSTREAM.md), "Known drift" |
| `HERMES_WEBUI_ALLOWED_ORIGINS` | unset | Origin allowlist for browser requests |
| `HERMES_WEBUI_DISABLE_PROFILE_SYNC` | unset | Test guard: suppresses the per-user profile sync subprocess |
| `HERMES_WEBUI_SOCKET_TIMEOUT` | `120` (floor 30) | Per-connection socket timeout, raised from upstream's 30s for slow mobile links |

Config files that matter: `~/.hermes/dashboard-governance.yaml` (the shared
policy, also read and written by the engine side), `STATE_DIR/settings.json`
(user settings, including saved tab visibility), `STATE_DIR/workspaces.json`
(workspace entries with our `owner_email` and `members` keys),
`STATE_DIR/skill_ownership.json` (the skill approval registry), and
`~/.hermes/dashboard-governance-audit.jsonl` (the audit trail).

## Repository layout

| Path | What lives there |
|---|---|
| `server.py` | Threaded `http.server` entry point. Our additions: the governance enforcement hook and the per-request ownership context |
| `api/` | The HTTP backend. `routes.py` is the dispatcher, `auth.py` / `auth_oidc.py` the login surface, `config.py` settings and discovery, `streaming.py` the chat stream |
| `api/governance/` | Our policy engine: loader, models, resolver, catalog, enforce, audit, usage, agent_context, profile_sync. See its [README](../api/governance/README.md) |
| `api/governance_api.py` | Our `/api/governance/*` admin API |
| `api/ownership.py`, `api/skill_ownership.py` | Our per-user isolation helpers and the skill approval registry |
| `static/` | The frontend, served as-is. `governance.js` is our admin panel; `i18n.js` plus `i18n/<locale>.js` is our demand-loaded locale split |
| `tests/` | pytest suite. Ours are `test_governance_*.py`, `test_two_step_login.py`, `test_workspace_ownership.py`, `test_chat_sync_governance.py` |
| `docs/` | Upstream documentation plus our `SYNTHPULSE*.md`, `governance-port-design.md` and `user-isolation-design.md` |
| `scripts/` | `test.sh`, the ruff and JS scope gates |
| `.github/workflows/` | Upstream CI, unchanged |

## Where to go next

- The hub repo `docs/QUICKSTART.md` for a first deployment, and `docs/WEBUI.md`
  for everything client-facing about this service (turn-on, key map, backup,
  `SP_WEBUI_REF` bump, troubleshooting).
- For the policy this application enforces: the engine fork's
  `docs/dashboard-governance.md` for the file's shape and the hub repo's
  `skills/synthpulse-governance/SKILL.md` for the operator procedure. The hub's
  `docs/OPERATIONS.md` is the day-two runbook. (There is no hub
  `docs/GOVERNANCE.md` yet: it is listed as a port in the hub's
  `docs/plans/PRODUCTIZATION-PLAN.md`.)
- [SYNTHPULSE-GOVERNANCE.md](SYNTHPULSE-GOVERNANCE.md) for the code-level detail
  of our additions.
- [SYNTHPULSE-UPSTREAM.md](SYNTHPULSE-UPSTREAM.md) before touching anything
  upstream also touches, and before an upstream refresh.
