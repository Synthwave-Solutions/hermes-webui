# hermes-webui governance port: complete design

Branch: `feat/governance-rbac` | Worktree: `/home/synthwavehq/work/hermes-webui-governance-port`
Reference implementation: `/home/synthwavehq/work/hermes-agent-governance-build/hermes_cli/dashboard_governance/`
Canonical policy file (shared with hermes-agent, schema unchanged): `~/.hermes/dashboard-governance.yaml`
Runtime: `/home/synthwavehq/.hermes/hermes-agent/venv/bin/python` (threaded `http.server`, no FastAPI, no hermes_cli imports anywhere in the port).

Never touch `/home/synthwavehq/hermes-webui` (live service). All work happens in this worktree.

---

## 0. Goals and non-goals

Goals (v1):
- Whitelist-first, deny-by-default route governance for every authenticated HTTP request, driven by the shared `~/.hermes/dashboard-governance.yaml` (mode `report_only` today, `off | report_only | enforce` supported).
- Identity-aware sessions (email, groups, method) with full backward compatibility with existing anonymous float-expiry sessions.
- One enforcement hook in `server.py`, post-auth, pre-dispatch, covering all five write methods and GET.
- Governance admin API under `/api/governance/` mirroring the reference API shapes (etag optimistic concurrency, admin-only mutations, policy_change audit).
- Minimal admin UI panel (overview, users, groups, preview-access, audit tail), admin-only visibility.
- JSONL audit with hashed subjects and secret redaction at `~/.hermes/dashboard-governance-audit.jsonl`.

Non-goals (v1, explicitly deferred):
- Tool/model/skill runtime policy (`tool_policy.py`, `model_policy.py`, `context.py` child-env export). The webui does not route agent tool calls through this layer today; vendor later if needed.
- Body-based enforcement (the hook must not consume the request body; path + method + query only).
- Editing the policy file schema. The loader accepts the canonical file as-is.

---

## 1. Vendored engine: new package `api/governance/`

All files created under `/home/synthwavehq/work/hermes-webui-governance-port/api/governance/`. No `hermes_cli`, no `fastapi`, no `starlette` imports. Only stdlib + `yaml` (already a webui dependency) + `api.auth` (from `enforce.py` only, late import to avoid cycles).

### 1.1 `api/governance/__init__.py`
Re-exports the public surface: `GovernancePolicy`, `GovernanceSubject`, `EffectiveAccess`, `GovernancePolicyError`, `load_governance_policy`, `save_governance_policy`, `parse_governance_policy`, `policy_etag`, `policy_mutation_lock`, `resolve_effective_access`, `route_permission`, `evaluate_request`, `enforce_request`, `Decision`, `append_audit_event`, `read_audit_events`.

### 1.2 `api/governance/models.py`
Vendor the reference `models.py` verbatim (stdlib-only frozen dataclasses): `GrantSet`, `GovernanceRole`, `GovernanceGroup`, `GovernanceUser`, `GovernancePolicy` (with `.enabled` and `.enforce` properties), `GovernanceSubject` (email, display_name, provider, user_id, org_id, roles, groups, claims, token_scopes, `normalized_email`), `EffectiveAccess` (has_permission, is_profile_allowed, is_route_allowed, is_tool_allowed, explain_permission), `AccessDecision`. Zero changes.

### 1.3 `api/governance/loader.py`
Vendor the reference loader with exactly one function rewritten and two additions:

- `resolve_policy_path(path=None, hermes_home=None) -> Path`: rewritten to drop `hermes_cli.config`. Resolution order: explicit `path` arg, env `HERMES_WEBUI_GOVERNANCE_POLICY`, env `HERMES_HOME` joined with `dashboard-governance.yaml`, default `Path.home() / ".hermes" / "dashboard-governance.yaml"`. This keeps both apps reading the same file.
- `parse_governance_policy(data) -> GovernancePolicy`: unchanged. Mode must be in `{off, report_only, enforce}`; `default_effect` must be `deny`; anything else raises `GovernancePolicyError`.
- `load_governance_policy(*, path=None, hermes_home=None) -> GovernancePolicy`: unchanged semantics. Missing file returns `GovernancePolicy(mode="off", default_effect="deny")` (governance disabled by absence); YAML error or non-mapping raises `GovernancePolicyError` (callers of the hook treat parse errors as fail-closed under enforce).
- `save_governance_policy(data, *, path=None, hermes_home=None) -> Path`: unchanged. Validates via `parse_governance_policy` first, then `tempfile.mkstemp` in the target dir + `fsync` + `os.replace` (atomic, complete-snapshot last-write-wins).
- NEW `policy_etag(raw) -> str` (ported from reference `web_server.py:_governance_policy_etag`):

  ```python
  def policy_etag(raw: Any) -> str:
      payload = raw if isinstance(raw, dict) else {}
      canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
      return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
  ```

- NEW module-level `_POLICY_MUTATION_LOCK = threading.Lock()` exposed via `policy_mutation_lock() -> threading.Lock`. The reference used an `asyncio.Lock` in app lifespan; the webui is a threaded `BaseHTTPRequestHandler`, so a process-wide `threading.Lock` wraps every read-check-save in the admin API.
- NEW injectable policy accessor for tests and the hook:

  ```python
  _policy_loader: Callable[[], GovernancePolicy] | None = None
  def set_policy_loader(fn) -> None: ...      # tests inject; None resets
  def get_policy() -> GovernancePolicy:        # hook + admin API entry point
      return (_policy_loader or load_governance_policy)()
  ```

  Fresh file read per request, mirroring the reference (no mtime cache in v1; the file is small and the Pi handles it).

### 1.4 `api/governance/resolver.py`
Vendor verbatim. `resolve_effective_access(policy, subject) -> EffectiveAccess` with semantics preserved byte-for-byte: bootstrap admin gets wildcard grants + role `owner`; user roles/groups union with SSO claim groups (`sso_groups` matching); group roles expand; merge order = role grants (sorted) then group grants (sorted) then direct user grants; `grant_sources` (`bootstrap_admin`, `role:X`, `group:Y`, `user:email`) and `permission_sources` recorded.

### 1.5 `api/governance/audit.py`
Vendor with two changes:

1. Replace the `hermes_constants.get_hermes_home` import with a local `_hermes_home()` (env `HERMES_HOME` else `Path.home() / ".hermes"`).
2. Add a module-level `_WRITE_LOCK = threading.Lock()` around the append (the reference relied on the single asyncio loop; the webui is threaded).

Unchanged contract:

```python
def append_audit_event(event: str, *, subject_email: str = "", subject_user_id: str = "",
                       path: str = "", method: str = "", reason: str = "", mode: str = "",
                       report_only: bool = False, extra: dict[str, Any] | None = None) -> None
def read_audit_events(limit: int = 100) -> list[dict]   # newest first, skips malformed lines
```

File: `<hermes_home>/dashboard-governance-audit.jsonl` (same file the reference writes). Privacy invariants preserved exactly: identities stored ONLY as `sha256(value).hexdigest()[:24]` (`subject_email_hash`, `subject_user_id_hash`, never raw); `extra` recursively redacted with `_SECRET_KEY_RE` (`api[_-]?key|secret|password|passwd|token|authorization|credential|refresh`) and `Bearer <token>` replaced by `Bearer [REDACTED]`. Audit failures are swallowed: an audit write error never blocks or changes an authorization decision.

### 1.6 `api/governance/usage.py`
Vendor with the two hermes-agent imports replaced by local helpers: `_hermes_home()` (as above) and `_atomic_json_write(path, payload)` (mkstemp + fsync + `os.replace`, same pattern as the loader). Add `threading.Lock` around the read-modify-write of `dashboard-governance-usage.json`. Hashed-subject keys unchanged. v1 consumers: the admin API usage endpoint (read) only; `record_tool_usage` stays available for future runtime wiring.

### 1.7 `api/governance/catalog.py`
Vendor the reference mechanism (`RouteRule` dataclass, `_MUTATION_METHODS`, `route_permission(path, method) -> str | None`, `_SELF_ROUTES`) and replace the CONTENT with the hermes-webui catalog derived from the route recon. Contract preserved: unknown `/api/*` path returns `None`, which enforcement treats as `unknown_route` (fail closed under enforce). Ordered most-specific first, prefix rules require a segment boundary (`/api/git` must not match `/api/gitfoo`).

Permission vocabulary: reuse the names already granted in the canonical policy (`sessions:read`, `sessions:write`, `chat:use`, `files:read`, `files:write`, `git:read`, `git:write`, `config:read`, `config:write`, `model:read`, `model:write`, `profiles:read`, `profiles:admin`, `skills:read`, `skills:write`, `mcp:read`, `mcp:write`, `plugins:read`, `plugins:write`, `cron:read`, `cron:write`, `cron:run`, `gateway:read`, `gateway:restart`, `logs:read`, `analytics:read`, `dashboard:read`, `dashboard:write`, `memory:read`, `memory:write`, `status:read`, `system:read`, `system:ops`, `governance:*`). No new permission names are invented, so the existing owner/admin/operator/viewer roles work without any policy edit.

Self routes (authenticated but no permission required, session self-management):

```
_SELF_ROUTES = frozenset({
    "/api/auth/status", "/api/auth/logout",
    "/api/auth/passkeys", "/api/auth/passkey/register/options",
    "/api/auth/passkey/register", "/api/auth/passkey/delete",
    "/api/governance/me",
})
```

Full `ROUTE_CATALOG` (RouteRule(pattern, read_permission, write_permission, match)):

```python
ROUTE_CATALOG: tuple[RouteRule, ...] = (
    # governance admin (mirror reference)
    RouteRule("/api/governance/policy",   "governance:read",  "governance:write"),
    RouteRule("/api/governance/validate", "governance:read",  "governance:read"),
    RouteRule("/api/governance/preview",  "governance:preview", "governance:preview"),
    RouteRule("/api/governance/audit",    "governance:audit:read"),
    RouteRule("/api/governance/usage",    "governance:usage:read"),
    RouteRule("/api/governance/users",    "governance:read",  "governance:write"),
    RouteRule("/api/governance/groups",   "governance:read",  "governance:write"),
    RouteRule("/api/governance",          "governance:read",  "governance:write"),

    # profiles
    RouteRule("/api/profiles",            "profiles:read"),
    RouteRule("/api/profile/active",      "profiles:read", match="exact"),
    RouteRule("/api/profile",             "profiles:read", "profiles:admin"),

    # sessions, projects, background
    RouteRule("/api/session/yolo",        "sessions:read", "sessions:write", match="exact"),
    RouteRule("/api/session",             "sessions:read", "sessions:write"),
    RouteRule("/api/sessions",            "sessions:read", "sessions:write"),
    RouteRule("/api/projects",            "sessions:read", "sessions:write"),
    RouteRule("/api/background",          "sessions:read", "sessions:write"),
    RouteRule("/api/bg-task-complete-ack", "sessions:write", "sessions:write", match="exact"),
    RouteRule("/api/process-complete-ack", "sessions:write", "sessions:write", match="exact"),

    # chat execution (incl. SSE streams, approval/clarify, voice)
    RouteRule("/api/chat",                "chat:use", "chat:use"),
    RouteRule("/api/btw",                 "chat:use", "chat:use", match="exact"),
    RouteRule("/api/goal",                "chat:use", "chat:use", match="exact"),
    RouteRule("/api/approval",            "chat:use", "chat:use"),
    RouteRule("/api/clarify",             "chat:use", "chat:use"),
    RouteRule("/api/transcribe/capability", "model:read", match="exact"),
    RouteRule("/api/transcribe",          "chat:use", "chat:use", match="exact"),
    RouteRule("/api/tts",                 "chat:use", "chat:use", match="exact"),

    # terminal + commands (RCE-grade; follows the reference precedent that
    # maps the hermes-agent PTY to chat:use; see rollout note in section 9)
    RouteRule("/api/terminal",            "chat:use", "chat:use"),
    RouteRule("/api/commands/exec",       "chat:use", "chat:use", match="exact"),
    RouteRule("/api/commands",            "config:read", "config:read"),

    # files and workspace
    RouteRule("/api/escape",              "files:read", "files:write"),
    RouteRule("/api/list",                "files:read", match="exact"),
    RouteRule("/api/file",                "files:read", "files:write"),
    RouteRule("/api/media",               "files:read", match="exact"),
    RouteRule("/api/folder/download",     "files:read", match="exact"),
    RouteRule("/api/upload",              "files:write", "files:write"),
    RouteRule("/api/workspace/upload",    "files:write", "files:write", match="exact"),
    RouteRule("/api/workspaces",          "files:read", "files:write"),
    RouteRule("/api/rollback",            "files:read", "files:write"),
    RouteRule("/api/wiki",                "files:read"),
    RouteRule("/api/notes",               "files:read"),

    # git
    RouteRule("/api/git-info",            "git:read", match="exact"),
    RouteRule("/api/git",                 "git:read", "git:write"),

    # config, settings, models, providers
    RouteRule("/api/settings",            "config:read", "config:write", match="exact"),
    RouteRule("/api/reasoning",           "config:read", "config:write", match="exact"),
    RouteRule("/api/models",              "model:read", "model:read"),
    RouteRule("/api/model",               "model:read", "model:write"),
    RouteRule("/api/default-model",       "model:write", "model:write", match="exact"),
    RouteRule("/api/providers",           "config:read", "config:write"),
    RouteRule("/api/provider",            "analytics:read"),
    RouteRule("/api/personalities",       "config:read", match="exact"),
    RouteRule("/api/personality",         "config:write", "config:write"),
    RouteRule("/api/prompts",             "config:read", "config:write", match="exact"),
    RouteRule("/api/memory/write",        "memory:write", "memory:write", match="exact"),
    RouteRule("/api/memory",              "memory:read", match="exact"),
    RouteRule("/api/admin",               "config:write", "config:write"),
    RouteRule("/api/dashboard",           "dashboard:read", "dashboard:write"),
    RouteRule("/api/insights",            "analytics:read"),
    RouteRule("/api/project-os",          "analytics:read"),
    RouteRule("/api/logs",                "logs:read", match="exact"),
    RouteRule("/api/client-events/log",   "status:read", "status:read", match="exact"),

    # skills, mcp, plugins, extensions
    RouteRule("/api/skills",              "skills:read", "skills:write"),
    RouteRule("/api/mcp",                 "mcp:read", "mcp:write"),
    RouteRule("/api/plugins",             "plugins:read", match="exact"),
    RouteRule("/api/extensions",          "plugins:read", "plugins:write"),  # incl. sidecar proxy wildcard

    # cron (route_permission special-cases POST .../run -> cron:run, as reference)
    RouteRule("/api/crons",               "cron:read", "cron:write"),

    # gateway
    RouteRule("/api/gateway/status",      "gateway:read", match="exact"),
    RouteRule("/api/gateway",             "gateway:read", "gateway:restart"),

    # kanban bridge (agent dispatch is chat-run grade)
    RouteRule("/api/kanban/dispatch",     "chat:use", "chat:use", match="exact"),
    RouteRule("/api/kanban",              "sessions:read", "sessions:write"),

    # system, health, updates, onboarding
    RouteRule("/api/health/restart",      "system:ops", "system:ops", match="exact"),
    RouteRule("/api/health",              "status:read"),
    RouteRule("/api/system",              "system:read"),
    RouteRule("/api/shutdown",            "system:ops", "system:ops", match="exact"),
    RouteRule("/api/updates/check",       "system:read", "system:read", match="exact"),
    RouteRule("/api/updates/summary",     "system:read", "system:read", match="exact"),
    RouteRule("/api/updates",             "system:read", "system:ops"),
    RouteRule("/api/onboarding",          "config:read", "config:write"),
)
```

The cron `run` special case is kept verbatim from the reference: `POST` on a path starting `/api/crons` and ending `/run` returns `cron:run` (also true for the flat `POST /api/crons/run`).

`GET /api/crons/run` (run detail) resolves through the RouteRule to `cron:read` because the special case only applies to mutation methods.

The extension sidecar proxy (`/api/extensions/<id>/sidecar[/...]`, any method) is covered by the `/api/extensions` prefix rule: GET resolves `plugins:read`, mutations `plugins:write`.

`POST /api/csp-report` never reaches the hook (it bypasses `check_auth` in server.py and the hook sits after `check_auth`); it stays unauthenticated by design and needs no rule.

### 1.8 `api/governance/enforce.py`
The only rewritten module (the reference `enforcement.py` is FastAPI-coupled). Framework-free core + one thin `http.server` adapter.

```python
@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str          # governance_off | non_api | bootstrap_admin | auth_disabled | allowed |
                         # unauthenticated | route_not_allowed | unknown_route |
                         # permission_not_allowed | profile_not_allowed | policy_error
    resource: str        # permission name from the catalog, "" when not applicable
    mode: str            # off | report_only | enforce

def subject_from_identity(identity: dict | None) -> GovernanceSubject:
    """identity is the dict returned by api.auth.get_session_identity (or None)."""
    if not identity:
        return GovernanceSubject()
    claims = identity.get("claims_subset") or {}
    return GovernanceSubject(
        email=(identity.get("email") or "").lower(),
        display_name=str(claims.get("name") or ""),
        provider=str(identity.get("method") or ""),
        user_id=str(claims.get("sub") or ""),
        groups=tuple(identity.get("groups") or ()),
        claims=claims,
    )

def evaluate_request(identity: dict | None, method: str, path: str) -> Decision:
    """Single decision entry point. path MAY carry a querystring; it is split
    internally (query is used only for the ?profile= target check)."""
```

`evaluate_request` order of checks (preserving the reference `governance_decision` order exactly, with the two port-specific additions marked NEW):

1. `policy = loader.get_policy()`; on `GovernancePolicyError`: `Decision(False, "policy_error", "", "enforce")` (fail closed; the adapter still honors report_only ONLY if the mode could be read, which it cannot here, so policy errors always deny under a previously-enforcing deployment and are audited).
2. `if not policy.enabled: return Decision(True, "governance_off", "", policy.mode)`.
3. Split `path` on `"?"` into `route_path`, `query`.
4. NEW `if not route_path.startswith("/api/"): return Decision(True, "non_api", "", policy.mode)` (page loads and static assets are not route-governed; panels are gated by their APIs).
5. `subject = subject_from_identity(identity)`.
6. NEW bootstrap short-circuit: `if subject.normalized_email and subject.normalized_email in {a.lower() for a in policy.bootstrap_admins}: return Decision(True, "bootstrap_admin", route_permission(route_path, method) or "", policy.mode)`. The bootstrap admin can NEVER be denied, even by catalog gaps (`unknown_route`) or a route whitelist mistake. (The resolver also grants wildcard; this guard protects against everything else.)
7. `if not subject.user_id and not subject.email: return Decision(False, "unauthenticated", "", policy.mode)` (anonymous/legacy sessions).
8. `access = resolve_effective_access(policy, subject)`.
9. `if not access.is_route_allowed(route_path): return Decision(False, "route_not_allowed", "", policy.mode)`.
10. `perm = route_permission(route_path, method)`; if `perm is None` and `route_path not in _SELF_ROUTES`: `Decision(False, "unknown_route", "", policy.mode)` (unknown `/api/*` fails closed under enforce, audited under report_only).
11. `if perm and not access.has_permission(perm): return Decision(False, "permission_not_allowed", perm, policy.mode)`.
12. Profile target: parse `?profile=` from the query (`urllib.parse.parse_qs`), skip value `active`; if present and `not access.is_profile_allowed(target)`: `Decision(False, "profile_not_allowed", perm or "", policy.mode)`.
13. `return Decision(True, "allowed", perm or "", policy.mode)`.

The `http.server` adapter (called by the single hook in server.py, section 3):

```python
def enforce_request(handler, parsed, method: str) -> bool:
    """check_auth-shaped contract: True = proceed to dispatch; False = a
    response has already been sent. NEVER reads the request body."""
```

Behavior:
- Builds identity: `from api import auth` (late import); if `auth` reports auth disabled, identity = `{"email": <first bootstrap admin from policy>, "method": "auth_disabled", "groups": [], "claims_subset": {}}` (trusted local single-user mode; governance cannot brick an auth-off install). Otherwise `identity = auth.get_session_identity(auth.parse_cookie(handler))`.
- `decision = evaluate_request(identity, method, parsed.path + ("?" + parsed.query if parsed.query else ""))`.
- `decision.allow` and reason not in `{"governance_off", "non_api"}` or plain allow: return True (allowed requests are NOT audited; matches the reference).
- Deny + `mode == "report_only"`: `append_audit_event("would_deny", subject_email=..., path=parsed.path, method=method, reason=decision.reason, mode=decision.mode, report_only=True, extra={"resource": decision.resource})`; return True (passthrough).
- Deny + `mode == "enforce"`: `append_audit_event("deny", ...)` then send the response and return False:
  - API/XHR (default): status 403, `Content-Type: application/json`, body `{"error": "forbidden", "resource": decision.resource, "reason": decision.reason}`. Reason `unauthenticated` also returns 403 with that body (`check_auth` already handled real 401s; this case means a stale anonymous session, and the JSON reason tells the client to re-login).
  - Page load (GET whose `Accept` header prefers `text/html`, i.e. a top-level navigation): status 403, `Content-Type: text/html`, a small friendly page (inline template constant `_DENY_PAGE_HTML` in enforce.py): "Access restricted | Your account does not have access to this resource (<resource>). Ask your administrator or switch accounts." with a link back to `/`. No secrets, no emails, no stack traces.
  - Every response sets `Content-Length` and `Connection: keep-alive` framing correctly (protocol is HTTP/1.1).
- Audit write failures are swallowed and never change the decision.

SSE note: the hook decides BEFORE any headers are sent, so long-lived streams (`/api/chat/stream`, `/api/terminal/output`, etc.) are gated at connect time; mid-stream revocation is out of scope for v1.

---

## 2. Identity-aware sessions (`api/auth.py`, `api/auth_oidc.py`)

Backward compatible with the existing anonymous store: `_sessions` today maps `token -> float expiry`; after this change values are `float` (legacy, kept as-is forever) OR `dict` (`{"exp": float, "email": str, "groups": [str], "claims_subset": dict, "method": str}`). Cookie format `token.sig`, HMAC signing, CSRF derivation, profile cookies: all untouched (they operate on the raw token only).

### 2.1 `api/auth.py` changes

Normalization helper (near line 102):

```python
def _session_expiry(value) -> float:
    if isinstance(value, dict):
        exp = value.get("exp")
        return float(exp) if isinstance(exp, (int, float)) else 0.0
    return float(value) if isinstance(value, (int, float)) else 0.0
```

- `_load_sessions()` (line 143-144 filter): keep `float` entries with `v > now` AS floats (no in-place migration, rollback-safe) and additionally keep `dict` entries with `_session_expiry(v) > now`.
- `verify_session()` (lines 577-582): `entry = _sessions.get(token)`; `if entry is None or time.time() > _session_expiry(entry): pop + save + False`.
- `_prune_expired_sessions()` (line 555): `expired = [t for t, v in _sessions.items() if now > _session_expiry(v)]`.
- `create_session(identity: dict | None = None) -> str`: same token/sig logic; store `{"exp": exp, **identity}` when an identity is provided (explicitly or staged, below), else the plain float (anonymous behavior preserved for any caller passing nothing when no identity is staged AND auth flow is unknown; in practice all four login flows resolve an identity, see 2.2).
- Thread-local identity staging (so the four `create_session()` call sites in `routes.py` need ZERO edits; routes.py is owned by B4, see section 6):

  ```python
  _PENDING_IDENTITY = threading.local()

  def stage_session_identity(identity: dict) -> None:
      _PENDING_IDENTITY.value = dict(identity)

  def _pop_pending_identity() -> dict | None:
      v = getattr(_PENDING_IDENTITY, "value", None)
      _PENDING_IDENTITY.value = None
      return v
  ```

  Inside `create_session`: `identity = identity or _pop_pending_identity() or _local_login_identity()`. Safe because `http.server` handles each request start-to-finish on one thread, and the OIDC callback stages then creates within the same request.
- Local (password/passkey/bootstrap) identity mapping:

  ```python
  def _local_login_identity() -> dict:
      email = os.getenv("HERMES_WEBUI_PASSWORD_IDENTITY", "").strip() or "michael@synthwave.solutions"
      return {"email": email.lower(), "groups": [], "claims_subset": {}, "method": "local"}
  ```

  The default maps password/passkey logins to the policy bootstrap admin (single-owner installs today; override via env for multi-user local setups). NOTE: the default email string is configuration, not a secret.
- New accessor consumed by governance:

  ```python
  def get_session_identity(cookie_value: str) -> dict | None:
      """Identity dict for a valid session cookie ({email, groups, claims_subset, method}),
      or None for invalid, legacy float, or anonymous sessions."""
  ```

  Implementation: `verify_session` first, then read the entry under `_SESSIONS_LOCK`, return `{k: v for k, v in entry.items() if k != "exp"}` when the entry is a dict, else None.
- New tiny helper for the admin API and hook: `is_auth_enabled() -> bool` if an equivalent public accessor does not already exist (wraps the same check `check_auth` uses at auth.py:690).

`claims_subset` is bounded to `{sub, email, name, preferred_username}` plus the groups claim; never persist the full raw claims (file stays lean, 0600 perms unchanged).

### 2.2 `api/auth_oidc.py` change (one addition)

At the end of `complete_authorization_code_flow` (after allowlist enforcement, before returning `result`):

```python
from api import auth as _auth   # late import if needed to avoid a cycle
claims = result.get("claims") or {}
_auth.stage_session_identity({
    "email": (result.get("email") or "").lower(),
    "groups": [str(g) for g in (claims.get("groups") or claims.get("roles") or [])],
    "claims_subset": {k: claims[k] for k in ("sub", "email", "name", "preferred_username") if k in claims},
    "method": "oidc",
})
```

The existing `create_session()` at routes.py:11194 then picks the staged identity up unmodified. Password (routes.py:14993), bootstrap (14404) and passkey (15037) logins fall through to `_local_login_identity()`.

### 2.3 Compatibility guarantees
- Existing `.sessions.json` float entries keep loading, verifying, pruning, logging out; they yield `get_session_identity() == None` until natural expiry (under `report_only` that is audited as `would_deny reason=unauthenticated`; under `enforce` those users re-login once).
- Rollback safe: old code reading a new-format file drops dict entries only (its float filter), so identity sessions degrade to a re-login.
- No cookie change, no forced logout, legacy 32-char signature branch untouched.

---

## 3. Enforcement hook (`server.py`)

Exactly one implementation (`api.governance.enforce.enforce_request`, section 1.8), called from the two symmetrical post-auth pre-dispatch points recon identified:

```python
# server.py top-level imports
from api.governance.enforce import enforce_request
```

1. `do_GET` (between current lines 390 and 391):

```python
        if not check_auth(self, parsed):
            return
        if not enforce_request(self, parsed, "GET"):     # NEW
            return
        result = handle_get(self, parsed)
```

2. `_handle_write` (between current lines 418 and 419); the `POST /api/csp-report` early path at lines 415-418 returns before this point, so csp-report keeps bypassing governance exactly as it bypasses auth:

```python
        if not check_auth(self, parsed):
            return
        if not enforce_request(self, parsed, self.command):   # NEW covers POST/PUT/PATCH/DELETE
            return
        result = route_func(self, parsed)
```

Properties:
- Runs AFTER `check_auth` (authn) and BEFORE any dispatch, including the extension sidecar proxy, the kanban bridge, the CSRF gate, plugin tab routing, and every SSE stream (headers not yet sent).
- Never reads the body (`read_body` happens later inside routes.py handlers).
- `do_OPTIONS` and unauthenticated public paths never reach the hook; non-`/api/` paths pass through inside `evaluate_request` (reason `non_api`).
- Mode `off` (or missing policy file): `evaluate_request` returns `governance_off` and the hook is a cheap passthrough (one small YAML read per request; acceptable on the Pi, and the injectable loader allows adding an mtime cache later without touching server.py).
- `report_only`: audit-only, zero behavior change (rollout default).
- `enforce`: 403 JSON for API calls, friendly HTML for browser navigations, per section 1.8.

---

## 4. Governance admin API (`api/governance_api.py`, new file)

Dispatched from `api/routes.py` via one function with two one-line call sites (the module handles all its own sub-routing so routes.py stays a single-line touch per method handler):

```python
# api/governance_api.py
def handle_governance_api(handler, parsed, method: str) -> bool:
    """Returns True if parsed.path is under /api/governance/ and a response was
    sent; False otherwise (routes.py continues normal dispatch)."""
```

routes.py insertions (owned by B4, the ONLY routes.py edits in this project):
- `handle_get` (after the extension sidecar proxy call at ~11073): `if governance_api.handle_governance_api(handler, parsed, "GET"): return True`
- `handle_post` (immediately AFTER the CSRF gate at ~12853, so all governance mutations get CSRF verification for free): `if governance_api.handle_governance_api(handler, parsed, "POST"): return True`

Design choice: ALL mutations are POST (webui idiom, e.g. `/api/providers/delete`), so no `handle_put`/`handle_patch`/`handle_delete` touch is needed. Payload and error SHAPES mirror the reference API; only the verb mapping differs.

### 4.1 Endpoints

Every endpoint first resolves the caller: `identity = auth.get_session_identity(auth.parse_cookie(handler))` (or the auth-disabled bootstrap identity, same rule as the hook), `subject = subject_from_identity(identity)`, `access = resolve_effective_access(get_policy(), subject)`.

Authorization helpers inside governance_api.py:
- `_is_bootstrap(subject, policy) -> bool`
- `_require(access, subject, policy, permission) -> bool` : bootstrap admin always passes; otherwise `access.has_permission(permission)`. On failure sends 403 `{"error": "forbidden", "resource": permission, "reason": "permission_not_allowed"}`.
- `_require_governance_admin(...)` = `_require(..., "governance:write")`. Applied to EVERY mutation REGARDLESS of policy mode (ported from the reference: in report_only the middleware lets denied requests through, so without this mode-independent gate any authenticated session could grant itself access during the dry-run rollout). Also applied when the policy file is missing (mode off): mutations then require the bootstrap identity.

| Method + path | Authz | Behavior |
|---|---|---|
| GET `/api/governance/me` | any authenticated (self route) | `{"email", "display_name", "method", "mode", "is_bootstrap_admin", "roles": [...], "groups": [...], "permissions": sorted([...]), "profiles": sorted([...])}` from the resolved access. Never includes claims or tokens. The UI keys admin visibility off `permissions` containing `governance:read`/`governance:write` or `is_bootstrap_admin`. |
| GET `/api/governance/policy` | `governance:read` | `{"policy": <raw yaml as dict, secrets-free by schema>, "etag": policy_etag(raw), "effective_access": <serialized caller access>}` . Response header `ETag: "<etag>"`. |
| POST `/api/governance/policy` | admin + `If-Match` | Full-document replace. Body = the complete policy mapping. Under `policy_mutation_lock()`: reload current raw, compute etag, compare with `If-Match` (strip quotes/whitespace); mismatch or absent header = 412 `{"error": "policy_conflict", "message": "policy changed since it was loaded; reload and retry"}`; then `save_governance_policy(body)` (validation errors = 400 `{"error": "invalid_policy", "message": str(e)}`); audit `policy_change` with a before/after summary (counts of roles/groups/users, mode, etag pair; never full documents, `_governance_policy_summary` port). Returns `{"ok": true, "etag": <new etag>}`. |
| POST `/api/governance/validate` | `governance:read` | Body `{"policy": {...}}`; runs `parse_governance_policy` only, NO save. `{"valid": true}` or `{"valid": false, "errors": ["..."]}` (200 either way). |
| POST `/api/governance/preview` | `governance:preview` | Body `{"email": "x@y", "groups": ["..."]?}`; builds a synthetic `GovernanceSubject`, resolves against the live policy, returns `{"effective_access": {roles, groups, permissions, profiles, routes}, "grant_sources": [...], "permission_sources": {...}}`. The serializer never leaks claims or token scopes (port `serialize_effective_access`). |
| GET `/api/governance/groups` | `governance:read` | `{"groups": {name: raw entry}, "etag": <policy etag>}` |
| POST `/api/governance/groups` | admin + `If-Match` | Create. Body `{"name": str, "entry": {...}}`. Validate via `_validated_governance_entry` port (mapping, only known keys: description, sso_groups, roles, grants). 400 invalid payload, 409 `{"error": "conflict"}` if the name exists, 412 stale etag. Read-modify-write of the FULL raw document under the mutation lock, `save_governance_policy`, audit `policy_change` (`extra={"op": "group_create", "target": name}`). Returns `{"ok": true, "etag": <new>}`. |
| POST `/api/governance/groups/update` | admin + `If-Match` | Body `{"name", "entry"}`; 404 `{"error": "not_found"}` on unknown name; otherwise as create. |
| POST `/api/governance/groups/delete` | admin + `If-Match` | Body `{"name"}`; 404 on unknown; audit `policy_change` (`op: group_delete`). |
| GET `/api/governance/users` | `governance:read` | `{"users": {email: raw entry}, "etag": <policy etag>}` |
| POST `/api/governance/users` | admin + `If-Match` | Create. Body `{"email": str, "entry": {roles?, groups?, grants?}}`; email must contain `@`; 409 on existing. |
| POST `/api/governance/users/update` | admin + `If-Match` | 404 on unknown email. |
| POST `/api/governance/users/delete` | admin + `If-Match` | 404 on unknown; refuses to delete a bootstrap admin entry (400 `{"error": "bootstrap_admin_protected"}`). |
| GET `/api/governance/audit?limit=N` | `governance:audit:read` | `{"events": read_audit_events(limit=min(N or 100, 500))}` newest first. |
| GET `/api/governance/usage` | `governance:usage:read` | `{"usage": <current usage state>, "caps": <caller usage_caps>}` |

Shared plumbing: JSON body parsing via the routes.py-idiomatic `read_body(handler)` + `json.loads` with 400 on malformed JSON; every response sends explicit `Content-Length` (HTTP/1.1 keep-alive). All mutation handlers run inside `with policy_mutation_lock():` covering read + etag check + save. All mutations audit `policy_change` even on the happy path; audit failure never blocks the mutation.

Note: the enforcement hook ALSO evaluates `/api/governance/*` requests (catalog section 1.7), so under enforce a non-admin is stopped at the hook; the in-module `_require*` gates are the defense that also holds under `report_only` and `off`.

---

## 5. Admin UI (minimal panel, per frontend recon)

Single-shell SPA: NO standalone governance.html. A new main-view panel `governance` following the exact existing panel pattern (logs/insights templates), with one new JS file so `panels.js` stays a 2-line touch.

Files and edits (all owned by B5):

1. `static/governance.js` (NEW): everything lives here.
   - `async function loadGovernance()` : entry point called by `switchPanel`. First `api('/api/governance/me')`; caches the result on `window.__GOV_ME__`.
   - Admin gating: helper `govApplyVisibility(me)` hides every `[data-panel="governance"]` button (`style.display='none'`) unless `me.is_bootstrap_admin` or `me.permissions` includes `governance:read` or `governance:write`; called on first load. Cosmetic only, the server enforces.
   - Tabs (simple in-panel tab bar, `gov-` prefixed classes):
     - Overview: mode badge (`off`/`report_only`/`enforce`), bootstrap admin list length, counts of roles/groups/users (from GET `/api/governance/policy`), last-24h deny/would_deny count (from the audit tail).
     - Users: table of `users` (email, roles, groups) with add/edit/delete forms posting to `/api/governance/users[...]` with the `If-Match` header set from the last fetched etag; on 412 show a toast "Policy changed elsewhere, reloading" and refetch.
     - Groups: same pattern against `/api/governance/groups[...]` (name, sso_groups, roles).
     - Preview access: email input (+ optional comma-separated groups), POST `/api/governance/preview`, render permissions/profiles/routes plus grant_sources.
     - Audit tail: GET `/api/governance/audit?limit=100`, newest first table (ts, event, reason, path, method, hashed subject prefix), refresh button; styled after the logs panel.
   - All fetches use the global `api()` helper from `workspace.js` (credentials, base-URI resolution, 401 redirect); CSRF header is added automatically by the fetch monkey-patch in index.html; governance.js NEVER sets `X-Hermes-CSRF-Token` manually.
   - Mutations always send `If-Match` (plain etag string; server strips quotes).
2. `static/index.html`: rail button + mobile sidebar-nav button (`data-panel="governance"`, copy the settings buttons at lines 165/184, admin-gated by governance.js at boot), sidebar `<div class="panel-view" id="panelGovernance">`, main `<div id="mainGovernance" class="main-view">` containing the tab bar and empty containers governance.js fills, and the single static-route registration: `<script src="static/governance.js?v=__WEBUI_VERSION__" defer></script>` inserted before `boot.js` (static assets under `/static/` are served without extra server registration; the script tag IS the registration).
3. `static/panels.js`: add `'governance'` to `MAIN_VIEW_PANELS` (line 47) and one lazy-load line in `switchPanel` (~367): `if (nextPanel === 'governance') await loadGovernance();`. In the same block, non-admin fallback: if `window.__GOV_ME__` says not admin, `switchPanel('chat')` instead (mirrors the hidden-section fallback precedent at panels.js:7544).
4. `static/i18n.js`: new keys in `LOCALES.en` only (`tab_governance`, `governance_overview`, `governance_users`, `governance_groups`, `governance_preview`, `governance_audit`, `governance_mode`, plus button/label keys). Other locales fall back to English automatically.
5. `static/style.css` (optional): `gov-` prefixed rules; otherwise reuse `.panel-view/.panel-head/.main-view/.settings-field/.sm-btn` and inline CSS vars like the rest of the codebase.

No em or en dash characters in any UI string.

---

## 6. File ownership: 5 builders, zero shared files

Hard rule: no file appears in two builders' lists. routes.py belongs to B4 ONLY (this is why identity staging in section 2.2 avoids routes.py login-call-site edits). server.py belongs to B3 ONLY. auth files belong to B2 ONLY.

| Builder | Creates | Edits |
|---|---|---|
| B1 (engine) | `api/governance/__init__.py`, `api/governance/models.py`, `api/governance/loader.py`, `api/governance/resolver.py`, `api/governance/catalog.py`, `api/governance/audit.py`, `api/governance/usage.py`, `api/governance/enforce.py`, `tests/test_governance_loader.py`, `tests/test_governance_resolver.py`, `tests/test_governance_catalog.py`, `tests/test_governance_enforce.py`, `tests/test_governance_audit.py`, `tests/test_governance_usage.py` | (nothing) |
| B2 (identity sessions) | `tests/test_governance_sessions.py` | `api/auth.py` (`_session_expiry`, `_load_sessions` filter, `verify_session`, `_prune_expired_sessions`, `create_session(identity=None)` + staging, `stage_session_identity`, `_local_login_identity`, `get_session_identity`, `is_auth_enabled`), `api/auth_oidc.py` (stage identity in `complete_authorization_code_flow`) |
| B3 (hook wiring) | `tests/test_governance_hook.py`, `tests/test_governance_catalog_coverage.py` | `server.py` (import + the two `enforce_request` call lines in `do_GET` and `_handle_write`, section 3) |
| B4 (admin API) | `api/governance_api.py`, `tests/test_governance_api.py` | `api/routes.py` (exactly two one-line insertions: `handle_get` after the sidecar proxy, `handle_post` after the CSRF gate; NOTHING else in this 24k-line file) |
| B5 (admin UI) | `static/governance.js` | `static/index.html`, `static/panels.js`, `static/i18n.js`, `static/style.css` (optional) |

Docs: this file (`docs/governance-port-design.md`) is written by the architect; builders do not edit it.

### 6.1 Interface contracts (the ONLY cross-builder coupling)

B1 exposes (consumed by B3, B4):
```python
# api/governance/enforce.py
@dataclass(frozen=True)
class Decision: allow: bool; reason: str; resource: str; mode: str
def evaluate_request(identity: dict | None, method: str, path: str) -> Decision
def enforce_request(handler, parsed, method: str) -> bool          # B3's hook target
def subject_from_identity(identity: dict | None) -> GovernanceSubject

# api/governance/loader.py
def load_governance_policy(*, path=None, hermes_home=None) -> GovernancePolicy
def save_governance_policy(data, *, path=None, hermes_home=None) -> Path
def parse_governance_policy(data) -> GovernancePolicy               # raises GovernancePolicyError
def policy_etag(raw) -> str
def policy_mutation_lock() -> threading.Lock
def get_policy() -> GovernancePolicy
def set_policy_loader(fn) -> None                                   # test injection

# api/governance/resolver.py
def resolve_effective_access(policy, subject) -> EffectiveAccess

# api/governance/catalog.py
def route_permission(path: str, method: str) -> str | None
ROUTE_CATALOG: tuple[RouteRule, ...]; _SELF_ROUTES: frozenset[str]

# api/governance/audit.py
def append_audit_event(event, *, subject_email="", subject_user_id="", path="", method="",
                       reason="", mode="", report_only=False, extra=None) -> None
def read_audit_events(limit: int = 100) -> list[dict]
```

B2 exposes (consumed by B1's `enforce_request` via late import, and by B4):
```python
# api/auth.py
def create_session(identity: dict | None = None) -> str
def stage_session_identity(identity: dict) -> None
def get_session_identity(cookie_value: str) -> dict | None
    # dict shape: {"email": str, "groups": list[str], "claims_subset": dict, "method": str}
def is_auth_enabled() -> bool
# unchanged: parse_cookie(handler) -> str, verify_session(cookie_value) -> bool
```

B4 exposes (consumed by its own routes.py dispatch lines; UI-facing contract consumed by B5):
```python
# api/governance_api.py
def handle_governance_api(handler, parsed, method: str) -> bool
```
HTTP contract for B5: the endpoint table in section 4.1 (paths, verbs, JSON shapes, `If-Match`/412, error bodies) is frozen; B5 codes against it without importing anything.

B3 consumes only `enforce_request` (B1) and, transitively, B2's session accessors. B3 exposes nothing.

Build order: B1 and B2 in parallel (no dependency); B3 and B4 after B1+B2; B5 after B4's contract is frozen (can start immediately from section 4.1).

---

## 7. Test plan

Runner: `/home/synthwavehq/.hermes/hermes-agent/venv/bin/python -m pytest tests/test_governance_*.py -q` (existing `pytest.ini` in the worktree applies). Every test isolates state via `monkeypatch.setenv("HERMES_HOME", str(tmp_path))` and/or `set_policy_loader`; NO test reads or writes the real `~/.hermes/dashboard-governance.yaml`, `.sessions.json`, or audit file. Mirror the reference tests' structure and assertions.

| File (owner) | Cases |
|---|---|
| `tests/test_governance_loader.py` (B1) | missing file = mode off + default deny; the FULL canonical policy shape (copy of the real yaml structure with placeholder values) parses (roles/groups/users/grants); invalid mode raises `GovernancePolicyError`; path override via env; `save_governance_policy` writes atomically (no `.tmp` residue); invalid save rejected WITHOUT clobbering the existing file; `policy_etag` stable across key order, changes on content change. |
| `tests/test_governance_resolver.py` (B1) | unknown user denied by default (empty permissions); bootstrap admin gets wildcard + owner role; user+group+role grants union with correct merge order; SSO claim group maps via `sso_groups`; `grant_sources`/`permission_sources` explain grants (preview contract). |
| `tests/test_governance_catalog.py` (B1) | endpoint families map to expected permissions (`GET /api/session` = sessions:read, `POST /api/session/delete` = sessions:write, `POST /api/chat/start` = chat:use, `POST /api/terminal/start` = chat:use, `GET /api/file` = files:read, `POST /api/file/save` = files:write, `POST /api/crons/run` = cron:run, `GET /api/crons/run` = cron:read, `POST /api/extensions/x/sidecar/y` = plugins:write, `POST /api/kanban/dispatch` = chat:use, `POST /api/gateway/restart` = gateway:restart, `POST /api/settings` = config:write); self routes return None; prefix rules honor segment boundaries (`/api/gitfoo` is unknown); unknown `/api/*` returns None. |
| `tests/test_governance_enforce.py` (B1) | pure `evaluate_request` decision tuples with an injected policy loader: mode off = governance_off allow; non-API path = allow; bootstrap admin allowed even on unknown routes and non-whitelisted routes (never-deny guard); identity None = unauthenticated deny; route_not_allowed; permission_not_allowed (viewer POSTing /api/file/save); profile_not_allowed via `?profile=`; `profile=active` exempt; allowed happy path per role (owner/admin/operator/viewer matrix over a representative route set); unknown `/api/*` = unknown_route deny; policy parse error = policy_error deny. |
| `tests/test_governance_audit.py` (B1) | secret-like keys and `Bearer x` redacted; identities hashed (raw email absent from file); newest-first + limit; concurrent appends from threads produce valid JSONL (lock). |
| `tests/test_governance_usage.py` (B1) | mirror reference: monthly cap blocks after `record_tool_usage`; hashed keys; atomic file. |
| `tests/test_governance_sessions.py` (B2) | legacy float entries load/verify/prune unchanged; dict entries round-trip through save/load; `create_session()` with no identity and nothing staged attaches `_local_login_identity` (email lowercase); staged identity (simulating the OIDC callback) is consumed exactly once and lands in the store; `get_session_identity` returns None for invalid cookies, legacy floats, and expired entries; CSRF token derivation unchanged for both entry types; mixed-format `.sessions.json` survives `_load_sessions`. |
| `tests/test_governance_hook.py` (B3) | end-to-end through `Handler` (spin up the real server on an ephemeral port, or fabricate a handler; mirror the reference fake-request pattern): report_only = request passes AND a `would_deny` audit line is written; enforce = 403 with JSON body `{error, resource, reason}` for an XHR-style request and HTML body for `Accept: text/html`; mode off = passthrough with no audit; `POST /api/csp-report` untouched; SSE endpoint denied at connect (no partial stream); body-carrying POST still reaches its handler intact when allowed (hook did not consume the body); auth-disabled install maps to bootstrap identity (nothing 403s). |
| `tests/test_governance_catalog_coverage.py` (B3) | walks `api/routes.py` dispatch (scrape the literal `parsed.path ==` / `startswith` comparisons in `handle_get/post/patch/delete/put` plus the kanban bridge table) and asserts EVERY non-public `/api/*` route resolves a permission via `route_permission` or is a self route. This is the fail-closed regression net: a new endpoint added without a catalog entry fails this test instead of silently 403ing in production. |
| `tests/test_governance_api.py` (B4) | against a live handler with injected policy + sessions: `/api/governance/me` shape for admin and viewer; policy GET requires governance:read and returns etag; POST policy without If-Match = 412; stale etag = 412; valid mutation saves + returns new etag + writes `policy_change` audit; validate returns errors without saving; preview explains sources and never leaks claims; groups/users CRUD happy paths, 400 invalid payload, 404 unknown, 409 conflict; bootstrap admin user delete refused; mutations forbidden for non-admin in enforce AND report_only AND with no policy file; CSRF required on mutations (POST without the header is rejected by the routes.py gate). |

Definition of done per builder: own tests green, plus the full `pytest tests/test_governance_*.py` suite green, plus `grep -c` for em/en dash characters over every touched file returns 0.

---

## 8. Audit event vocabulary

| event | emitted by | when |
|---|---|---|
| `would_deny` | hook | report_only denial (reason + resource in extra) |
| `deny` | hook | enforce denial (before sending 403) |
| `policy_change` | admin API | every successful policy/group/user mutation (op + target + before/after summary + old/new etag in extra) |

All events carry `mode`, `path`, `method`, `reason`, hashed subject fields, ISO timestamp. Nothing else writes to the audit file.

---

## 9. Rollout notes (post-merge, not part of the build)

- Ship with the shared policy exactly as-is: `mode: report_only`. Zero behavior change; audit fills with `would_deny` lines that validate the catalog and the identity mapping.
- Known data gap before flipping to enforce (policy VALUES, not schema): the operator/viewer `routes` whitelists in the shared yaml are hermes-agent shaped (`/api/sessions`, `/api/chat`, `/api/pty`); hermes-webui uses `/api/session/...`, `/api/terminal/...`, `/api/crons/...`. Under enforce, operator/viewer would hit `route_not_allowed` on those until webui route prefixes (or `/api/session*` style wildcards) are added to the role/group entries. report_only audit surfaces every case first. Admin/owner are unaffected (`routes: ["*"]`).
- Terminal endpoints map to `chat:use` (reference PTY precedent). If Michael wants terminal locked tighter than chat for freelancers, add a dedicated permission to the policy values later; the catalog line is a one-word change.
- Legacy anonymous sessions show up as `reason=unauthenticated` would_deny lines; they age out within the session TTL.
- Flip to enforce only after an audit-quiet week and after the placeholder Workspace `sso_groups` values in the policy are verified.
