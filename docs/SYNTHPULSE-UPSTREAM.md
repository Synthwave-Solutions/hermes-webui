# Fork relationship and upstream refresh

## What this is a fork of

Upstream project: [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui),
the web interface for the Hermes agent, licensed **MIT** ("Copyright (c) 2025
Hermes Web UI Contributors", see [LICENSE](../LICENSE)). Upstream wrote this
application. The three-panel UI, sessions, workspace browser, profiles, voice,
themes, the password/passkey/OIDC login mechanics, the launchers, the Docker
variants, the CI workflows and the large majority of the test suite are their
work, and our changes ship under the same MIT terms. Do not replace or reword
`LICENSE`, `CONTRIBUTORS.md` or the upstream sections of `README.md`.

Remotes in this checkout:

| Remote | URL | Use |
|---|---|---|
| `origin` | `https://github.com/Synthwave-Solutions/hermes-webui.git` | Our fork. All pushes go here |
| `upstream` | `https://github.com/nesquena/hermes-webui.git` | Read-only. Fetch, never push |

Fork position, as of the last `git fetch upstream` in this checkout:

```
git merge-base HEAD upstream/master
  -> 320789ae  (upstream, 2026-07-31)
git rev-list --left-right --count upstream/master...HEAD
  -> 118   31        # upstream commits since the base | our commits on top
```

So every carried change is the 31 commits in `320789ae..HEAD`, and upstream has
moved 118 commits since that base. Re-run both commands before planning a
refresh; the numbers above are a snapshot, not a constant.

## What is ours

Read from `git log --oneline 320789ae..HEAD` and the corresponding diff. Grouped
by area:

| Area | Commits | What changed |
|---|---|---|
| Brand overlay | `844071da`, `80f13c9e` | User-visible "Hermes" strings to "SynthPulse" across `static/*.js` and the locale catalogs, favicons/manifest/PWA icons, a SynthPulse skin in the palette list (upstream's "Nous" skin kept as "Steel" with its original value), `server_version` header, gateway timeout tuning |
| Governance policy engine | `7dfb332f`, `893d3366`, `fa134373`, `819226f3`, `343cba4b` and the review fixes `3152b7bb`, `94ed063f`, `3ae55ad1`, `8e065ad0` | New `api/governance/` package (a port of the engine's `dashboard_governance`), `api/governance_api.py`, the enforcement hook in `server.py`, identity-bearing sessions in `api/auth.py`, `static/governance.js`, and `docs/governance-port-design.md` |
| Two-step SSO login | `76b38ba3`, `e9a757be`, `f43e1c5c` | `HERMES_WEBUI_REQUIRE_SSO_FIRST`, the pending-SSO store and its signed cookie, the `hd:` pseudo-group, passkey path covered |
| Per-user isolation and skill approvals | `e316961f`, `9e18d1d6`, `9bef2e49`, `5d43641f` | `api/ownership.py`, `api/skill_ownership.py`, ownership filtering in the session/project/skill routes, the approvals admin API and UI, `docs/user-isolation-design.md` |
| Runtime enforcement and hardening | `a0f22509`, `cc7b1191`, `4b53d3ba` | Per-turn agent binding (`api/governance/agent_context.py`), the `terminal:use` split off `chat:use`, workspace ownership, frontend 403 handling, the anonymous `csp-report` route |
| Governance panel and workspaces | `e01706bd`, `bf86df42`, `610327df`, `385cbecf` | Group grants editor, capability pills, templates, the Workspaces admin tab, ownership stamping, the admin scope flag and OIDC just-in-time provisioning |
| Update banner removal | `ae53fb3a` | The background update check and its banner are gone: image tags are the update mechanism for a client deployment |
| Tab visibility | `bfe2f12a`, `46ae5572` | `HERMES_WEBUI_DEFAULT_HIDDEN_TABS` as a fresh-install baseline, and the server value made authoritative at boot |
| i18n demand loading | `3e82a7e0` | `static/i18n.js` reduced to a loader plus metadata (99 lines); the catalogs moved to `static/i18n/<locale>.js` and are fetched on demand, with `window.i18nReady` awaited in `boot.js`. Upstream still ships one large `static/i18n.js` |

The functional additions are described in
[SYNTHPULSE-GOVERNANCE.md](SYNTHPULSE-GOVERNANCE.md); how the result is shipped is
in [SYNTHPULSE.md](SYNTHPULSE.md).

## Refresh procedure

The goal of a refresh is: newest upstream architecture, with our behaviour and
branding re-applied on top, verified before anything is re-pinned.

**Never refresh in a live checkout, and never push to `upstream`.**

1. **Inventory and freeze.** Record `git status --short`, `git remote -v`,
   `git log -1`, and:
   ```bash
   git fetch upstream --prune
   git merge-base HEAD upstream/master
   git rev-list --left-right --count upstream/master...HEAD
   ```
2. **Back up the fork tip before rewriting anything.** Push a dated branch to
   `origin`, for example `backup/master-YYYYMMDD-pre-refresh`.
3. **Work in a disposable clone or worktree**, not in the tree a service is
   running from.
4. **Forecast the conflicts read-only** before starting. This writes nothing to
   the working tree or to any ref:
   ```bash
   git merge-tree --write-tree --name-only HEAD upstream/master
   git diff --stat $(git merge-base HEAD upstream/master)..upstream/master -- static/ api/ server.py
   ```
   Run against `upstream/master` at the time of writing, that forecast returned
   six conflicting files: `api/gateway_chat.py`, `api/models.py`,
   `api/route_session_list_cache.py`, `api/routes.py`, `api/streaming.py` and
   `static/i18n.js`. Treat it as the current shape of the work, not a fixed list.
5. **Rebase (or merge) our 31 commits onto the chosen upstream commit.** Prefer a
   reviewed upstream release commit over a random tip.
6. **Resolve with one rule: take the newer upstream code, then re-apply our
   behaviour on top.** Concretely: keep new upstream i18n keys and rebrand only
   the visible strings; take upstream refactors and rebrand only user-facing
   messages; drop an old block of ours that upstream superseded, then re-apply the
   branding to the replacement; for a file upstream deleted, check for remaining
   references (`grep -rn '<name>' static api`) before deciding.
7. **Verify in the disposable clone** (all of these are what CI runs):
   ```bash
   python3 -m compileall -q api server.py bootstrap.py mcp_server.py tests scripts
   python3 scripts/ruff_lint.py --diff origin/master
   python3 scripts/scope_undef_gate.py
   npx eslint --no-config-lookup -c eslint.runtime-guard.config.mjs "static/**/*.js"
   ./scripts/test.sh
   ```
   Then boot the server and load the pages: the browser smoke gate exists because
   a whole class of JS bricks only appears when a browser executes the code.
   Governance-specific smoke: log in, confirm the Governance panel appears for an
   admin and not for a non-admin, `GET /api/governance/me`, and a policy mutation
   with the `If-Match` etag.
8. **Re-pin and rebuild in the hub.** Edit `ARG SP_WEBUI_REF` in the hub's
   `Dockerfile.webui` (the only place the pin lives; CI reads the default out of
   that file), tag a hub release so `build-webui` publishes `:X.Y.Z` and
   `:latest`, then `docker compose pull webui && docker compose up -d webui`.
   Bumping the ref matters twice: it is also what busts the clone layer cache, so
   a forgotten bump ships old code in a "refreshed" image.

Two pitfalls seen on earlier refreshes: a broad
`git diff --check upstream/master...HEAD` reports thousands of whitespace findings
from upstream-only files, so scope hygiene checks to the files you changed; and a
PR opened from a rebased refresh branch can show an unusable diff against the old
fork history, in which case the tested branch SHA plus local verification is the
source of truth.

### Files that carry the conflict risk

The measured forecast above changes with every upstream release. These are the
files whose divergence is structural, so they keep coming back:

| File | Why |
|---|---|
| `server.py` | Our enforcement hook and ownership context sit inside `do_GET` and `_handle_write`, which upstream also edits |
| `api/routes.py` | The single large dispatcher. Our ownership filters and route branches are spread through it |
| `api/auth.py`, `api/auth_oidc.py` | Identity-bearing sessions, the pending-SSO store and the JIT path interleave with upstream's login work |
| `api/config.py` | Settings defaults, including the hidden-tabs baseline |
| `static/index.html`, `boot.js`, `panels.js`, `ui.js`, `sessions.js`, `style.css` | Governance panel wiring, branding and boot reconciliation live in files upstream changes constantly |
| `static/i18n.js` and `static/i18n/*.js` | Structural divergence: upstream edits one large catalog file, we ship a loader plus per-locale files. Every upstream i18n change has to be re-applied into the split |
| favicons, `manifest.json`, `sw.js` | Brand assets |

### Known drift to repair on the next refresh

Verified against the merge base `320789ae` in this checkout. The last refresh
resolved several hunks in favour of our side and, in doing so, dropped upstream
work that was already in the base:

| Missing from our tree | Evidence |
|---|---|
| `api.auth.reset_trusted_auth_request_state` | Present at the base and on `upstream/master`; absent from `api/auth.py` at HEAD, while `tests/test_trusted_header_auth.py` still calls it and asserts two call sites in `server.py` |
| `api.routes.apply_cors_preflight_headers` | Present at the base; absent at HEAD. `do_OPTIONS` sends a static `Access-Control-Allow-Origin: *` again, and `tests/test_cors_preflight_allowlist.py` still imports the function. The `Content-Length: 0` framing of the preflight response was lost with it |
| `HERMES_WEBUI_TRUSTED_PROXY_CIDRS` support | The base and `upstream/master` read it in `api/routes.py` (the trusted-proxy allowlist for the local-origin gate); no application code at HEAD reads it. The hub compose service sets the variable, so it is currently inert |
| The SIGTERM orderly-shutdown handler in `main()` | Present at the base so a managed stop unwinds the `finally` and drains in-flight work; absent at HEAD |
| Line counts | `api/routes.py` 25163 lines at HEAD versus 26987 at the base, `api/auth.py` 1042 versus 1219, despite our additions. That delta is upstream content, not cleanup |

Recommended handling: for these specific files take upstream's version wholesale
on the next refresh and re-apply our hooks on top, rather than carrying the
current versions forward. The tests above are the fastest signal that it worked.
(The test outcomes are stated from reading the sources; the suite was not executed
while writing this document.)
