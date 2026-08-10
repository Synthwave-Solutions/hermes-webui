# Governance, isolation and auth: the SynthPulse additions

Code-level reference for what our fork adds on top of upstream
[nesquena/hermes-webui](https://github.com/nesquena/hermes-webui). Upstream owns
authentication (who you are): password, passkeys and the OIDC login flow. Our
layer owns authorization (what that person may do), per-user data isolation, the
admin surface for both, and a small number of deployment behaviours.

Two design notes written during the build carry the full reasoning and the
decision log: [governance-port-design.md](governance-port-design.md) and
[user-isolation-design.md](user-isolation-design.md). This file is the map.

## One policy file, two applications

The policy lives at `~/.hermes/dashboard-governance.yaml` (override with
`HERMES_WEBUI_GOVERNANCE_POLICY`, or resolve under `HERMES_HOME`). The engine
side reads and writes the same file, so the schema and the validation results
must stay identical to the engine's reference implementation. `api/governance/`
is a port of the engine's `dashboard_governance` package with the engine imports
removed: standard library plus `yaml` only, no FastAPI, no `hermes_cli`.

Three modes, from `policy.mode`:

| Mode | Behaviour |
|---|---|
| `off` (also: no policy file) | Every request passes. Ownership isolation still applies, and the admin API still refuses mutations to non-admins |
| `report_only` | Denials are audited as `would_deny` and the request is still dispatched |
| `enforce` | Denials return 403 and are audited as `deny` |

`default_effect` must be `deny`: the policy is a whitelist. Only `bootstrap_admins`
are never-deny principals, in three independent places (a short circuit in the
enforcement hook, a wildcard grant in the resolver, and an exemption from
per-user `deny` subtraction).

## Module map: `api/governance/`

| Module | Responsibility |
|---|---|
| `loader.py` | Parse, validate, cache and atomically persist the policy. Path resolution order: explicit argument, `HERMES_WEBUI_GOVERNANCE_POLICY`, `HERMES_HOME`, then `~/.hermes/dashboard-governance.yaml`. The cache key is path plus inode plus nanosecond mtime plus size, so an atomic replace is observed on the next request. Writes use a per-writer `mkstemp` temp file so two concurrent writers cannot publish interleaved content. `policy_etag()` gives the optimistic-concurrency hash |
| `models.py` | `GrantSet` (permissions, profiles, routes, settings, toolsets, tools, skills view/load/manage, MCP servers and tools, model providers and models, file read/write roots and denied globs, CLI commands and workdir roots, workspaces, usage caps), plus the merge and subtract algebra and the policy/role/group/user/subject dataclasses |
| `resolver.py` | Resolve a subject to `EffectiveAccess`: bootstrap wildcard, then user roles and groups, then SSO-group matching, then role grants, group grants, user grants, and finally per-user `deny` subtraction. Every merge records a grant source (`role:x`, `group:y`, `user:z`, `deny:user:z`) so the admin UI can explain a decision |
| `catalog.py` | The route-to-permission table for THIS application's API surface. `RouteRule` is vendored, the content is ours. Unknown `/api/*` routes deliberately map to nothing so a new endpoint fails closed until classified. `_ANON_ROUTES` is the pre-auth login surface, kept aligned with `api.auth.PUBLIC_PATHS` by a coverage test; `_SELF_ROUTES` needs a valid identity but no permission |
| `enforce.py` | The decision core plus one `http.server` adapter. Never reads the request body |
| `audit.py` | Append-only JSONL at `$HERMES_HOME/dashboard-governance-audit.jsonl`, subjects hashed, secret-shaped keys and bearer tokens redacted, appends serialized under a lock |
| `usage.py` | Usage counters and caps with atomic state writes. Read-only consumer today: the admin API usage endpoint |
| `agent_context.py` | Binds the caller's `EffectiveAccess` around an in-process agent turn, which activates the engine's tool, skill, MCP, model, file, CLI and usage-cap gates for non-admins |
| `profile_sync.py` | Fire-and-forget bridge to the engine-side per-user profile provisioner |

## Request enforcement

`server.py` calls `enforce_request(self, parsed, method)` after `check_auth` and
before dispatch, on GET and on all four write verbs. It follows the `check_auth`
contract: `True` means proceed, `False` means a response has already been sent.

Decision order in `evaluate_request`, which is the part to keep intact:

1. `_ANON_ROUTES` pass **before the policy is read**, so a broken policy file can
   never lock out the login endpoints (including the bootstrap admin's).
2. Anything not under `/api/` passes, also before the policy is read: pages and
   static assets are not route-governed, panels are gated by their APIs. So an
   unparseable policy cannot brick the login page; only `/api/*` fails closed.
3. A policy load or parse error denies with reason `policy_error`.
4. Governance disabled (`mode: off`) passes.
5. A bootstrap admin passes, even through a catalog gap.
6. No identity denies with `unauthenticated`.
7. The route whitelist, then the catalog permission (`unknown_route` when the
   path is not classified and is not a self route), then the `?profile=` target
   against the caller's allowed profiles.

Denials render as JSON, or as a small self-contained HTML page for a top-level
browser navigation (`GET` with `Accept: text/html`). Allowed requests are not
audited, matching the engine reference.

Two body-sink gaps are closed outside the hook, because the hook must not consume
the request body: `is_profile_allowed_for()` re-checks a profile taken from a
JSON body (notably `POST /api/profile/switch`, which mints a signed profile
cookie), and `POST /api/workspaces/assign` carries its own admin gate.

## `/api/governance/*` admin API

Dispatched from `api/routes.py` into `handle_governance_api` in
`api/governance_api.py`. All mutations are POST, following this application's
idiom rather than the engine's verb mapping. Mutations require
`governance:write` **regardless of mode**, so nobody can grant themselves access
during a `report_only` rollout, and every mutation is audited as a
`policy_change` with a bounded before/after summary (counts and entry names, never
full grant documents).

| Method and path | Gate |
|---|---|
| `GET /api/governance/me` | Any authenticated caller. Returns email, method, mode, bootstrap flag, roles, groups, permissions, profiles. Never claims or tokens |
| `GET /api/governance/policy` | `governance:read`. Returns the policy, an `ETag` header and the caller's effective access |
| `GET /api/governance/users`, `GET /api/governance/groups` | `governance:read` |
| `GET /api/governance/audit?limit=` | `governance:audit:read`. Default 100, maximum 500 |
| `GET /api/governance/usage` | `governance:usage:read` |
| `GET /api/governance/approvals` | `governance:write` |
| `POST /api/governance/policy` | `governance:write`. Full-document replace under `If-Match`; refuses a document that drops `bootstrap_admins` |
| `POST /api/governance/validate` | `governance:read`. Parse-only, no write |
| `POST /api/governance/preview` | `governance:preview`. Effective access for another email plus hypothetical groups |
| `POST /api/governance/groups`, `/groups/update`, `/groups/delete` | `governance:write` |
| `POST /api/governance/users`, `/users/update`, `/users/delete` | `governance:write` |
| `POST /api/governance/approvals/decide` | `governance:write` |

Policy mutations serialize through a process-wide lock and follow
read-check-save under `If-Match`, so a stale editor gets a conflict instead of
overwriting a concurrent change. After a successful mutation the per-user profile
sync is triggered in the background.

## Per-user data isolation

Implemented in `api/ownership.py` and applied in the data layer, independent of
the governance `mode`: it holds in `off` and `report_only` exactly as in
`enforce`. `HERMES_WEBUI_USER_ISOLATION=0` disables it.

- **Ownership stamping.** `server.py` binds the request handler to the serving
  thread (`set_request_context` / `clear_request_context` in a `finally`), so code
  far from the HTTP layer (session creation, CLI import, background saves) can
  resolve the creator. `resolve_new_owner()` takes an explicit owner, then the
  thread's request identity, then `HERMES_WEBUI_DEFAULT_OWNER`. It never guesses
  from data on disk, so loading a row cannot re-own it.
- **Visibility.** `request_owner_scope()` returns `all` for admins (when
  `HERMES_WEBUI_ADMIN_SEES_ALL` is on), for identity-less requests and when
  isolation is off; otherwise the caller's lowercased email. Rows with no
  `owner_email` (legacy data, cron and CLI imports) are admin-only. The scope is
  part of the session list cache key, so users can never be served each other's
  cached list.
- **Admin resolution.** `identity_is_admin()` is true for the bootstrap-admin
  grant source, an `owner` or `admin` role, wildcard routes, or the
  `governance:write` permission. It fails closed for a real identity when the
  policy cannot be read. The synthetic `auth_disabled` identity always counts as
  admin, so a trusted single-user install keeps working.

## Workspaces as a grant category

`GrantSet.workspaces` makes the workspace list a governed grant rather than a
file-side convention, and `_wildcard_grants()` includes it so a bootstrap admin
sees everything.

`_workspaces_response_list()` in `api/routes.py` filters and annotates the list
per identity: admins get every entry, and for anyone else the governance grant
decides. When the policy cannot be read, or the person is not in it, the code
falls back to the per-entry `members` list in `workspaces.json`, and only when
that is empty too does it fall back to showing the entry (marked
`legacy_unowned` so the admin UI can offer an assign affordance). An empty grant
list means "show nothing", never "show everything".

`POST /api/workspaces/assign` sets `owner_email` and `members` on an entry. It
carries an explicit `request_is_admin()` gate in the handler because the catalog
maps `/api/workspaces` to `files:write`, and `files:write` is not admin-scoped.
`api/workspace.py` preserves unknown per-entry keys during its cleanup pass,
which runs on every load and persists its result: dropping them would silently
destroy ownership metadata.

## Skill approvals

`api/skill_ownership.py` keeps a sidecar registry at
`STATE_DIR/skill_ownership.json`, mapping a stable skill key (`category/name`, or
a bare `name` for a flat skill, both the on-disk directory names) to
`{owner_email, added_at, status}` with status `pending` or `approved`. Writes are
atomic and serialized under a module lock.

- A skill saved through `/api/skills/save` by a non-admin lands on disk as usual
  and is registered `pending`, owned by the creator. Registration is idempotent,
  so re-saving never resets the status or reassigns the owner.
- A non-admin may create new skills and edit their own. Editing a global skill or
  someone else's skill returns 403.
- Skills with no registry entry are global (pre-existing or admin-managed).
  Pending skills are visible only to their owner and to admins; approving flips
  the status to `approved` and makes the skill global while keeping the
  `added_by` annotation; rejecting deletes the skill directory and the registry
  entry. Both decisions are audited.

## Governed agent turns

Route-level enforcement stops at the HTTP boundary. `api/governance/agent_context.py`
extends it into the turn: it resolves the caller's `EffectiveAccess` from the same
policy file and binds the equivalent engine-side governance context around the
in-process agent turn, which activates the engine's dormant tool, skill, MCP,
model, file, CLI and usage-cap gates for non-admin users.

Two constraints in that module are easy to break and expensive to debug:

- The bind uses the engine's `ContextVar`, so it MUST run on the thread that
  executes the turn, never on the HTTP handler thread. The process-global env-var
  route is deliberately unused: `os.environ` is process-wide, so one person's
  grants would leak into every concurrent turn.
- The two vendored dataclass families are field-identical but distinct types, so
  objects are bridged through the engine's own serializer instead of being passed
  across directly. A new grant dimension added engine-side then fails loudly here
  instead of silently dropping grants.

Failure posture mirrors the route layer: admins, ownerless sessions and a
disabled or unreadable policy run unbound (today's behaviour); a non-admin whose
context cannot be built runs unbound and audited under `report_only`, and is
refused with `GovernanceBindingError` under `enforce`.

## Identity and login

Upstream owns the login mechanics. Our additions:

- **Identity-bearing sessions.** `create_session()` records who logged in: an
  explicit identity, then the identity staged by the OIDC callback, then the
  local password/passkey identity. `get_session_identity()` returns
  `{email, groups, claims_subset, method}`. Legacy anonymous sessions (a bare
  expiry float) still verify, they simply carry no identity.
- **Local login identity.** Password and passkey logins map to
  `HERMES_WEBUI_PASSWORD_IDENTITY`, falling back to a hardcoded operator address
  in `api/auth.py`. Set it explicitly in any deployment.
- **OIDC hardening.** A login is rejected when the IdP says `email_verified` is
  false (an IdP that omits the claim is left as-is). Otherwise an allowlisted
  account could set its email to a bootstrap admin's and inherit never-deny
  access.
- **Group mapping.** Groups come from the `groups` or `roles` claim, plus a
  pseudo-group `hd:<hosted_domain>` synthesized ONLY for the Google issuer, so a
  policy can map a whole Workspace domain to a baseline role via
  `sso_groups: ["hd:<domain>"]` without per-person entries. The `hd` claim is
  ignored for every other issuer to prevent cross-issuer group forgery.
- **Just-in-time provisioning.** When the allowlist refuses a cryptographically
  validated identity, the verified address gets exactly one second chance through
  an engine-side provisioner script under `$HOME/.hermes/scripts/`, which is
  idempotent, takes its own lock and refuses any address outside a hardcoded
  company-domain constant (`_JIT_PROVISION_DOMAIN` in `api/auth_oidc.py`). The
  reason this exists: the allowlist comes from the process environment, a
  snapshot taken at start, so a colleague provisioned after the last restart
  would otherwise be refused even though the system of record knows them. Every
  failure re-raises the original refusal, and each attempt is audited. Disable
  with `HERMES_WEBUI_DISABLE_JIT_PROVISION`.
- **Two-step login (optional).** With `HERMES_WEBUI_REQUIRE_SSO_FIRST` truthy, a
  successful OIDC callback does not create a session: it stashes the validated
  identity in an in-memory store for about ten minutes and hands the browser a
  signed HttpOnly cookie. `POST /api/auth/login` then rejects a password-only
  attempt with `sso_required` **before** checking the password, so a leaked
  password alone cannot mint a session, and consumes the pending entry
  destructively (a failed consume is a hard failure, so two racing requests
  cannot both mint a session from one token). The resulting session is recorded
  with method `sso+password`. Default off, so the flow is unchanged until a
  deployment turns it on.

### Auth posture in a SynthPulse deployment

- The service is never exposed directly. No host port is published; the ingress
  Caddy terminates TLS and is the only route in. `HERMES_WEBUI_TRUST_FORWARDED_PROTO`
  and `_HOST` must be on behind it, otherwise the OIDC redirect is rebuilt as
  `http://` and the secure cookie is dropped, which looks like an endless login
  loop.
- OIDC is the intended per-person login. The password
  (`HERMES_WEBUI_PASSWORD`) is the **break-glass**: it stays reachable
  (`REQUIRE_SSO_FIRST=0`) so an operator is not locked out of a client
  deployment when the IdP misbehaves. It is a real credential with real reach:
  it logs in as `HERMES_WEBUI_PASSWORD_IDENTITY`, which in a single-owner setup
  is a bootstrap admin, so treat it as an admin credential, keep it out of the
  image and out of git, and prefer turning `REQUIRE_SSO_FIRST` on once SSO is
  proven.
- `/health` is unauthenticated by contract, which is what makes the container
  health probe work with either login mode.
- Governance is inactive until the policy exists on the volume. The container
  entrypoint warns about a missing policy by default and can be made to refuse
  to start (`SP_WEBUI_REQUIRE_GOVERNANCE=1`), which is the recommended setting
  once the policy is in `enforce`.

## Frontend surface

`static/governance.js` is the admin panel, a separate file rather than part of
`ui.js`. Tabs: overview, users, groups, workspaces (injected at runtime),
approvals (with a pending badge), preview access, and audit. It fetches
`/api/governance/me` and hides every `[data-panel="governance"]` nav button for
non-admins. That hiding is cosmetic only: every action it offers is gated server
side as well.

Two related deployment behaviours:

- `HERMES_WEBUI_DEFAULT_HIDDEN_TABS` is the fresh-install baseline for hidden
  sidebar panels (comma separated; `chat` and `settings` are always dropped from
  the list). It is a baseline, not a lock: a value the user saved in Settings
  wins, because `load_settings()` merges defaults under the persisted file.
- At boot, `static/boot.js` reconciles `hidden_tabs` and `tab_order` from
  `/api/settings`, making the server value authoritative. Without this, the
  pre-paint inline script and the restore path can only read `localStorage`, so a
  server-side change stayed invisible until the user opened Settings, and a tab
  hidden in an old browser session could keep the Governance panel out of the
  rail even for a bootstrap admin (`.nav-tab-hidden` uses
  `display:none !important` and beats the admin reveal).

## Tests

Ours, all runnable with `./scripts/test.sh <path>`:

`test_governance_loader.py`, `_resolver.py`, `_catalog.py`,
`_catalog_coverage.py`, `_enforce.py`, `_deny.py`, `_hook.py`, `_api.py`,
`_audit.py`, `_usage.py`, `_sessions.py`, `_agent_context.py`,
`_approval_approver.py`, `_profile_sync_trigger.py`, `_reference_gaps.py`,
plus `test_two_step_login.py`, `test_workspace_ownership.py` and
`test_chat_sync_governance.py`.

`test_governance_catalog_coverage.py` is the safety net that keeps the catalog
aligned with the real route surface and with `api.auth.PUBLIC_PATHS`. When you
add an `/api/*` endpoint, classify it in `catalog.py` in the same change.
