"""
Hermes Web UI -- Governance admin API (/api/governance/*).

Dispatched from api/routes.py handle_get/handle_post via
handle_governance_api(handler, parsed, method). Mirrors the reference
hermes-agent dashboard governance admin API shapes (etag optimistic
concurrency via If-Match, admin-only mutations regardless of policy mode,
policy_change audit trail); only the verb mapping differs: all mutations
are POST, following the webui idiom (e.g. /api/providers/delete).

The enforcement hook (api/governance/enforce.py) also evaluates these
routes through the catalog, so under enforce a non-admin is stopped before
dispatch; the in-module _require* gates are the defense that also holds
under report_only and off.
"""

import logging
from urllib.parse import parse_qs

from api.governance.audit import append_audit_event, read_audit_events
from api.governance.enforce import subject_from_identity
from api.governance.loader import (
    GovernancePolicyError,
    get_policy,
    parse_governance_policy,
    policy_etag,
    policy_mutation_lock,
    save_governance_policy,
)
from api.governance.models import GovernanceSubject, _norm_email
from api.governance.profile_sync import trigger_profile_sync
from api.governance.resolver import resolve_effective_access
from api.governance.usage import read_usage_state
from api.helpers import j, read_body

logger = logging.getLogger(__name__)

_GOVERNANCE_PREFIX = "/api/governance/"
_AUDIT_LIMIT_DEFAULT = 100
_AUDIT_LIMIT_MAX = 500

# Whitelist of keys accepted in group/user policy entries (the rest of the
# schema is owned by the full-document POST /api/governance/policy replace).
_GROUP_ENTRY_KEYS = frozenset({"description", "sso_groups", "roles", "grants"})
_USER_ENTRY_KEYS = frozenset({"description", "roles", "groups", "grants", "deny"})


# ── Caller resolution ────────────────────────────────────────────────────────

def _caller_identity(handler) -> dict | None:
    """Identity dict for the request, mirroring the enforcement hook rule.

    Auth-disabled installs map to the first bootstrap admin (trusted local
    single-user mode); otherwise the session cookie must carry an identity.
    """
    from api import auth  # late import to avoid cycles (matches enforce.py)

    try:
        if not auth.is_auth_enabled():
            email = ""
            try:
                policy = get_policy()
                if policy.bootstrap_admins:
                    email = policy.bootstrap_admins[0]
            except Exception:
                email = ""
            return {"email": email, "groups": [], "claims_subset": {}, "method": "auth_disabled"}
        cookie = auth.parse_cookie(handler)
        if not cookie:
            return None
        return auth.get_session_identity(cookie)
    except Exception:
        return None


def _is_bootstrap(subject: GovernanceSubject, policy) -> bool:
    email = subject.normalized_email
    return bool(email) and email in {str(a).lower() for a in policy.bootstrap_admins}


def _require(handler, access, subject, policy, permission: str) -> bool:
    """Bootstrap admin always passes; otherwise the permission must be granted.

    On failure a 403 has been sent and the caller must return True (handled).
    """
    if _is_bootstrap(subject, policy) or access.has_permission(permission):
        return True
    j(
        handler,
        {"error": "forbidden", "resource": permission, "reason": "permission_not_allowed"},
        status=403,
    )
    return False


def _require_governance_admin(handler, access, subject, policy) -> bool:
    """Defense-in-depth gate for every policy mutation, REGARDLESS of mode.

    The enforcement hook only hard-denies in enforce mode: in report_only
    denied requests are audited and still dispatched, and with mode off (or
    no policy file) every request passes. Policy mutations must never execute
    for subjects without governance:write in any mode, otherwise any
    authenticated session could grant itself access during the dry-run
    rollout (or bootstrap a policy that flips mode to enforce).
    """
    return _require(handler, access, subject, policy, "governance:write")


# ── Serialization helpers ────────────────────────────────────────────────────

def _policy_raw(policy) -> dict:
    """Raw policy payload for reads/etags (safe_policy_payload port).

    The policy schema is whitelist-only and should not carry secrets, but
    keep this as a single choke point so future secret-bearing fields can be
    redacted here before they reach the admin UI.
    """
    if policy.raw:
        return dict(policy.raw)
    return {
        "version": policy.version,
        "mode": policy.mode,
        "default_effect": policy.default_effect,
        "bootstrap_admins": list(policy.bootstrap_admins),
    }


def _serialize_access(access) -> dict:
    """Serialize an EffectiveAccess for API responses.

    Never includes claims or token scopes (port of the reference
    serialize_effective_access).
    """
    subject = access.subject
    return {
        "mode": access.mode,
        "subject": {
            "email": subject.email,
            "display_name": subject.display_name,
            "provider": subject.provider,
            "user_id": subject.user_id,
            "org_id": subject.org_id,
        },
        "roles": sorted(access.roles),
        "groups": sorted(access.groups),
        "permissions": sorted(access.permissions),
        "profiles": sorted(access.profiles),
        "routes": sorted(access.routes),
        "grant_sources": list(access.grant_sources),
        "is_admin": access.has_permission("governance:read") or access.has_permission("governance:write"),
    }


def _policy_summary(raw) -> dict:
    """Bounded before/after summary for policy_change audit entries.

    Counts and entry names only; never full documents (grants stay out of
    the audit trail).
    """
    data = raw if isinstance(raw, dict) else {}
    users = data.get("users") if isinstance(data.get("users"), dict) else {}
    groups = data.get("groups") if isinstance(data.get("groups"), dict) else {}
    roles = data.get("roles") if isinstance(data.get("roles"), dict) else {}
    return {
        "version": data.get("version"),
        "mode": str(data.get("mode") or ""),
        "counts": {"roles": len(roles), "groups": len(groups), "users": len(users)},
        "roles": sorted(str(key) for key in roles),
        "groups": sorted(str(key) for key in groups),
        "users": sorted(str(key) for key in users),
    }


# ── Request plumbing ─────────────────────────────────────────────────────────

def _read_json(handler) -> dict | None:
    """JSON object body, or None after sending a 400."""
    try:
        body = read_body(handler)
    except ValueError as exc:
        j(handler, {"error": "invalid_payload", "message": str(exc)}, status=400)
        return None
    if not isinstance(body, dict):
        j(handler, {"error": "invalid_payload", "message": "body must be a JSON object"}, status=400)
        return None
    return body


def _check_if_match(handler, current_raw: dict) -> bool:
    """Optimistic concurrency: the client must echo the etag it loaded.

    A missing or stale If-Match header cannot silently revert edits that
    landed between the client's GET and this mutation. On failure a 412 has
    been sent and the caller must return True (handled).
    """
    expected = str(handler.headers.get("If-Match", "") or "").strip().strip('"').strip()
    if not expected or expected != policy_etag(current_raw):
        j(
            handler,
            {
                "error": "policy_conflict",
                "message": "policy changed since it was loaded; reload and retry",
            },
            status=412,
        )
        return False
    return True


def _validated_entry(handler, raw_entry, *, kind: str) -> dict | None:
    """Validated group/user policy entry, or None after sending a 400."""
    allowed = _GROUP_ENTRY_KEYS if kind == "group" else _USER_ENTRY_KEYS
    if raw_entry is None:
        return {}
    if not isinstance(raw_entry, dict):
        j(
            handler,
            {"error": "invalid_payload", "message": f"{kind} entry must be an object"},
            status=400,
        )
        return None
    unknown = sorted(str(key) for key in raw_entry if key not in allowed)
    if unknown:
        j(
            handler,
            {
                "error": "invalid_payload",
                "message": f"unknown {kind} entry keys: {', '.join(unknown)}",
            },
            status=400,
        )
        return None
    for field_name in ("roles", "groups", "sso_groups"):
        value = raw_entry.get(field_name)
        if value is not None and not isinstance(value, list):
            j(
                handler,
                {"error": "invalid_payload", "message": f"{kind} {field_name} must be a list"},
                status=400,
            )
            return None
    for grants_key in ("grants", "deny"):
        value = raw_entry.get(grants_key)
        if value is not None and not isinstance(value, dict):
            j(
                handler,
                {"error": "invalid_payload", "message": f"{kind} {grants_key} must be an object"},
                status=400,
            )
            return None
    return dict(raw_entry)


def _reject_bootstrap_admin_deny(handler, policy, email: str, entry: dict) -> bool:
    """True (after a 400) when the entry puts a deny on a bootstrap admin.

    The resolver already ignores such denies (never-deny principals); reject
    them at the API too so the policy file never records a lockout attempt.
    """
    deny = entry.get("deny")
    if not deny:
        return False
    admins = {str(a).strip().lower() for a in getattr(policy, "bootstrap_admins", ())}
    if email in admins:
        j(
            handler,
            {"error": "invalid_payload", "message": "deny is not allowed on a bootstrap admin"},
            status=400,
        )
        return True
    return False


def _audit_policy_change(
    subject: GovernanceSubject,
    mode: str,
    parsed,
    *,
    op: str,
    target: str = "",
    before=None,
    after=None,
    old_etag: str = "",
    new_etag: str = "",
) -> None:
    """Audit a successful mutation; a broken audit sink never undoes the
    mutation (it is already persisted)."""
    try:
        append_audit_event(
            "policy_change",
            subject_email=subject.email,
            subject_user_id=subject.user_id,
            path=parsed.path,
            method="POST",
            reason=op,
            mode=mode,
            extra={
                "op": op,
                "target": target,
                "before": before,
                "after": after,
                "old_etag": old_etag,
                "new_etag": new_etag,
            },
        )
    except Exception:
        return


def _mutate_policy(handler, parsed, subject: GovernanceSubject, *, op: str, target: str, mutate) -> bool:
    """Shared read + If-Match check + mutate + atomic save + audit cycle.

    ``mutate(raw)`` edits the full raw policy document in place and returns
    ``(before, after)`` audit values, or None when it already sent an error
    response (404/409/400). The whole cycle runs under the process-wide
    policy mutation lock so two concurrent admin edits can never interleave.
    """
    with policy_mutation_lock():
        try:
            current_policy = get_policy()
        except GovernancePolicyError as exc:
            j(handler, {"error": "policy_error", "message": str(exc)}, status=500)
            return True
        raw = _policy_raw(current_policy)
        old_etag = policy_etag(raw)
        if not _check_if_match(handler, raw):
            return True
        result = mutate(raw)
        if result is None:
            return True
        before, after = result
        try:
            save_governance_policy(raw)
        except GovernancePolicyError as exc:
            j(handler, {"error": "invalid_policy", "message": str(exc)}, status=400)
            return True
        except Exception:
            logger.exception("POST %s failed", parsed.path)
            j(handler, {"error": "internal_error"}, status=500)
            return True
        new_etag = policy_etag(raw)
    _audit_policy_change(
        subject,
        current_policy.mode,
        parsed,
        op=op,
        target=target,
        before=before,
        after=after,
        old_etag=old_etag,
        new_etag=new_etag,
    )
    # Re-provision Hermes profiles from the new policy in the background.
    # User edits sync just that user; role/group edits fan out to everyone.
    # Deletes keep the profile dir (data is never destroyed automatically).
    if op != "user_delete":
        trigger_profile_sync(
            target if op in ("user_create", "user_update") else None,
            reason=op,
        )
    j(handler, {"ok": True, "etag": new_etag})
    return True


# ── GET endpoints ────────────────────────────────────────────────────────────

def _handle_me(handler, parsed, policy, subject, access) -> bool:
    """Self route: any authenticated caller. Never includes claims or tokens."""
    j(
        handler,
        {
            "email": subject.email,
            "display_name": subject.display_name,
            "method": subject.provider,
            "mode": policy.mode,
            "is_bootstrap_admin": _is_bootstrap(subject, policy),
            "roles": sorted(access.roles),
            "groups": sorted(access.groups),
            "permissions": sorted(access.permissions),
            "profiles": sorted(access.profiles),
            # Left-navigation items this caller must not see, derived from the
            # same permissions that gate the panels' APIs (27 Aug 2026 ticket).
            # The client hides these on top of the user's own hidden_tabs; the
            # APIs stay the real enforcement.
            "hidden_nav": _hidden_nav(access, policy),
        },
    )
    return True


def _hidden_nav(access, policy) -> list:
    try:
        from api.governance.nav import hidden_panels

        return hidden_panels(access, policy)
    except Exception:
        return []


def _handle_policy_get(handler, parsed, policy, subject, access) -> bool:
    if not _require(handler, access, subject, policy, "governance:read"):
        return True
    payload = _policy_raw(policy)
    etag = policy_etag(payload)
    j(
        handler,
        {"policy": payload, "etag": etag, "effective_access": _serialize_access(access)},
        extra_headers={"ETag": f'"{etag}"'},
    )
    return True


def _handle_collection_get(handler, parsed, policy, subject, access, *, key: str) -> bool:
    if not _require(handler, access, subject, policy, "governance:read"):
        return True
    raw = _policy_raw(policy)
    entries = raw.get(key) if isinstance(raw.get(key), dict) else {}
    j(handler, {key: entries or {}, "etag": policy_etag(raw)})
    return True


def _handle_audit_get(handler, parsed, policy, subject, access) -> bool:
    if not _require(handler, access, subject, policy, "governance:audit:read"):
        return True
    query = parse_qs(getattr(parsed, "query", "") or "")
    try:
        limit = int((query.get("limit") or [_AUDIT_LIMIT_DEFAULT])[0])
    except (TypeError, ValueError):
        limit = _AUDIT_LIMIT_DEFAULT
    limit = max(1, min(limit or _AUDIT_LIMIT_DEFAULT, _AUDIT_LIMIT_MAX))
    j(handler, {"events": read_audit_events(limit)})
    return True


def _handle_usage_get(handler, parsed, policy, subject, access) -> bool:
    if not _require(handler, access, subject, policy, "governance:usage:read"):
        return True
    j(handler, {"usage": read_usage_state(), "caps": dict(access.grants.usage_caps)})
    return True


# ── POST endpoints ───────────────────────────────────────────────────────────

def _handle_policy_replace(handler, parsed, policy, subject, access) -> bool:
    if not _require_governance_admin(handler, access, subject, policy):
        return True
    body = _read_json(handler)
    if body is None:
        return True

    with policy_mutation_lock():
        try:
            current_policy = get_policy()
        except GovernancePolicyError as exc:
            j(handler, {"error": "policy_error", "message": str(exc)}, status=500)
            return True
        current = _policy_raw(current_policy)
        old_etag = policy_etag(current)
        if not _check_if_match(handler, current):
            return True

        # Lock-out guard: a governance:write caller could POST a policy that
        # drops (or empties) bootstrap_admins and flips mode to enforce,
        # permanently locking out the never-deny owner(s). Refuse unless every
        # CURRENT bootstrap admin survives the replace, or the caller is
        # themselves a bootstrap admin (they own the never-deny set and may
        # rotate it deliberately). Mirrors the users/delete protection shape.
        current_bootstrap = {_norm_email(str(a)) for a in current_policy.bootstrap_admins}
        new_bootstrap = {
            _norm_email(str(a))
            for a in (body.get("bootstrap_admins") or [])
            if str(a).strip()
        }
        if current_bootstrap and not _is_bootstrap(subject, current_policy):
            if not current_bootstrap.issubset(new_bootstrap):
                j(
                    handler,
                    {
                        "error": "bootstrap_admin_protected",
                        "message": "policy replace must retain all current bootstrap admins",
                    },
                    status=400,
                )
                return True

        before = _policy_summary(current)
        try:
            save_governance_policy(body)
        except GovernancePolicyError as exc:
            j(handler, {"error": "invalid_policy", "message": str(exc)}, status=400)
            return True
        except Exception:
            logger.exception("POST /api/governance/policy failed")
            j(handler, {"error": "internal_error"}, status=500)
            return True
        new_etag = policy_etag(dict(body))
    _audit_policy_change(
        subject,
        current_policy.mode,
        parsed,
        op="policy_replace",
        target="policy",
        before=before,
        after=_policy_summary(body),
        old_etag=old_etag,
        new_etag=new_etag,
    )
    trigger_profile_sync(None, reason="policy_replace")
    j(handler, {"ok": True, "etag": new_etag})
    return True


def _handle_validate(handler, parsed, policy, subject, access) -> bool:
    if not _require(handler, access, subject, policy, "governance:read"):
        return True
    body = _read_json(handler)
    if body is None:
        return True
    raw_policy = body.get("policy")
    if not isinstance(raw_policy, dict):
        j(handler, {"error": "invalid_payload", "message": "policy must be an object"}, status=400)
        return True
    try:
        parse_governance_policy(raw_policy)
    except GovernancePolicyError as exc:
        j(handler, {"valid": False, "errors": [str(exc)]})
        return True
    j(handler, {"valid": True})
    return True


def _handle_preview(handler, parsed, policy, subject, access) -> bool:
    if not _require(handler, access, subject, policy, "governance:preview"):
        return True
    body = _read_json(handler)
    if body is None:
        return True
    email = str(body.get("email") or "").strip()
    if not email or "@" not in email:
        j(handler, {"error": "invalid_payload", "message": "email must be a valid address"}, status=400)
        return True
    groups = body.get("groups")
    if groups is not None and not isinstance(groups, list):
        j(handler, {"error": "invalid_payload", "message": "groups must be a list"}, status=400)
        return True
    synthetic = GovernanceSubject(
        email=email,
        groups=tuple(str(g) for g in (groups or []) if str(g).strip()),
    )
    preview = resolve_effective_access(policy, synthetic)
    j(
        handler,
        {
            "effective_access": {
                "roles": sorted(preview.roles),
                "groups": sorted(preview.groups),
                "permissions": sorted(preview.permissions),
                "profiles": sorted(preview.profiles),
                "routes": sorted(preview.routes),
                # Grant detail for the admin UI's per-user on/off toggles.
                # Post-deny (the resolver already subtracted users[email].deny).
                "grants": {
                    "skills": {
                        "view": sorted(preview.grants.skills_view),
                        "load": sorted(preview.grants.skills_load),
                        "manage": sorted(preview.grants.skills_manage),
                    },
                    "mcp": {"servers": sorted(preview.grants.mcp_servers)},
                    "cli": {
                        "commands": sorted(preview.grants.cli_commands),
                        "approval_commands": sorted(preview.grants.cli_approval_commands),
                    },
                },
            },
            "grant_sources": list(preview.grant_sources),
            "permission_sources": {
                perm: list(sources) for perm, sources in sorted(preview.permission_sources.items())
            },
        },
    )
    return True


def _handle_group_create(handler, parsed, policy, subject, access) -> bool:
    if not _require_governance_admin(handler, access, subject, policy):
        return True
    body = _read_json(handler)
    if body is None:
        return True
    name = str(body.get("name") or "").strip()
    if not name:
        j(handler, {"error": "invalid_payload", "message": "name must be a non-empty string"}, status=400)
        return True
    entry = _validated_entry(handler, body.get("entry"), kind="group")
    if entry is None:
        return True

    def mutate(raw: dict):
        groups = dict(raw.get("groups")) if isinstance(raw.get("groups"), dict) else {}
        if name in groups:
            j(handler, {"error": "conflict", "message": f"group already exists: {name}"}, status=409)
            return None
        groups[name] = entry
        raw["groups"] = groups
        return None, entry

    return _mutate_policy(handler, parsed, subject, op="group_create", target=name, mutate=mutate)


def _handle_group_update(handler, parsed, policy, subject, access) -> bool:
    if not _require_governance_admin(handler, access, subject, policy):
        return True
    body = _read_json(handler)
    if body is None:
        return True
    name = str(body.get("name") or "").strip()
    if not name:
        j(handler, {"error": "invalid_payload", "message": "name must be a non-empty string"}, status=400)
        return True
    entry = _validated_entry(handler, body.get("entry"), kind="group")
    if entry is None:
        return True

    def mutate(raw: dict):
        groups = dict(raw.get("groups")) if isinstance(raw.get("groups"), dict) else {}
        if name not in groups:
            j(handler, {"error": "not_found", "message": f"unknown group: {name}"}, status=404)
            return None
        before = groups.get(name)
        groups[name] = entry
        raw["groups"] = groups
        return before, entry

    return _mutate_policy(handler, parsed, subject, op="group_update", target=name, mutate=mutate)


def _handle_group_delete(handler, parsed, policy, subject, access) -> bool:
    if not _require_governance_admin(handler, access, subject, policy):
        return True
    body = _read_json(handler)
    if body is None:
        return True
    name = str(body.get("name") or "").strip()
    if not name:
        j(handler, {"error": "invalid_payload", "message": "name must be a non-empty string"}, status=400)
        return True

    def mutate(raw: dict):
        groups = dict(raw.get("groups")) if isinstance(raw.get("groups"), dict) else {}
        if name not in groups:
            j(handler, {"error": "not_found", "message": f"unknown group: {name}"}, status=404)
            return None
        before = groups.pop(name)
        raw["groups"] = groups
        return before, None

    return _mutate_policy(handler, parsed, subject, op="group_delete", target=name, mutate=mutate)


def _handle_user_create(handler, parsed, policy, subject, access) -> bool:
    if not _require_governance_admin(handler, access, subject, policy):
        return True
    body = _read_json(handler)
    if body is None:
        return True
    email = _norm_email(str(body.get("email") or ""))
    if not email or "@" not in email:
        j(handler, {"error": "invalid_payload", "message": "email must be a valid address"}, status=400)
        return True
    entry = _validated_entry(handler, body.get("entry"), kind="user")
    if entry is None:
        return True
    if _reject_bootstrap_admin_deny(handler, policy, email, entry):
        return True

    def mutate(raw: dict):
        users = dict(raw.get("users")) if isinstance(raw.get("users"), dict) else {}
        if any(_norm_email(str(key)) == email for key in users):
            j(handler, {"error": "conflict", "message": f"user already exists: {email}"}, status=409)
            return None
        users[email] = entry
        raw["users"] = users
        return None, entry

    return _mutate_policy(handler, parsed, subject, op="user_create", target=email, mutate=mutate)


def _handle_user_update(handler, parsed, policy, subject, access) -> bool:
    if not _require_governance_admin(handler, access, subject, policy):
        return True
    body = _read_json(handler)
    if body is None:
        return True
    email = _norm_email(str(body.get("email") or ""))
    if not email or "@" not in email:
        j(handler, {"error": "invalid_payload", "message": "email must be a valid address"}, status=400)
        return True
    entry = _validated_entry(handler, body.get("entry"), kind="user")
    if entry is None:
        return True
    if _reject_bootstrap_admin_deny(handler, policy, email, entry):
        return True

    def mutate(raw: dict):
        users = dict(raw.get("users")) if isinstance(raw.get("users"), dict) else {}
        before = None
        found = False
        for existing_key in list(users):
            if _norm_email(str(existing_key)) == email:
                before = users.pop(existing_key)
                found = True
        if not found:
            j(handler, {"error": "not_found", "message": f"unknown user: {email}"}, status=404)
            return None
        users[email] = entry
        raw["users"] = users
        return before, entry

    return _mutate_policy(handler, parsed, subject, op="user_update", target=email, mutate=mutate)


def _handle_user_delete(handler, parsed, policy, subject, access) -> bool:
    if not _require_governance_admin(handler, access, subject, policy):
        return True
    body = _read_json(handler)
    if body is None:
        return True
    email = _norm_email(str(body.get("email") or ""))
    if not email or "@" not in email:
        j(handler, {"error": "invalid_payload", "message": "email must be a valid address"}, status=400)
        return True

    def mutate(raw: dict):
        bootstrap = {_norm_email(str(a)) for a in (raw.get("bootstrap_admins") or [])}
        if email in bootstrap:
            j(
                handler,
                {
                    "error": "bootstrap_admin_protected",
                    "message": "bootstrap admin entries cannot be deleted",
                },
                status=400,
            )
            return None
        users = dict(raw.get("users")) if isinstance(raw.get("users"), dict) else {}
        before = None
        found = False
        for existing_key in list(users):
            if _norm_email(str(existing_key)) == email:
                before = users.pop(existing_key)
                found = True
        if not found:
            j(handler, {"error": "not_found", "message": f"unknown user: {email}"}, status=404)
            return None
        raw["users"] = users
        return before, None

    return _mutate_policy(handler, parsed, subject, op="user_delete", target=email, mutate=mutate)


# ── Approvals (skills + self-service installs) ───────────────────────────────

def _skill_key_parts(key) -> tuple | None:
    """Split a registry skill key into (category, name), or None when malformed.

    Keys are on-disk directory names: ``name`` or ``category/name`` (see
    api.skill_ownership.skill_key). Anything with empty segments, extra
    segments, traversal tokens, or path separators is rejected so a corrupted
    or crafted key can never resolve outside the skills root.
    """
    raw = str(key or "").strip()
    if not raw:
        return None
    parts = raw.split("/")
    if len(parts) == 1:
        category, name = None, parts[0]
    elif len(parts) == 2:
        category, name = parts[0], parts[1]
    else:
        return None
    for part in parts:
        if not part.strip() or part in (".", "..") or "\\" in part or "\x00" in part:
            return None
    return category, name


def _audit_approval(subject: GovernanceSubject, mode: str, parsed, *, op: str, key: str, owner: str) -> None:
    """Audit an approval decision; a broken audit sink never undoes it."""
    try:
        append_audit_event(
            "approval_decision",
            subject_email=subject.email,
            subject_user_id=subject.user_id,
            path=parsed.path,
            method="POST",
            reason=op,
            mode=mode,
            extra={"op": op, "target": key, "key": key, "owner": owner},
        )
    except Exception:
        return


def _approval_row(entry: dict) -> dict:
    """Serialize a registry entry for the approvals API.

    The four fields the skills UI already binds to (key, name, category,
    owner_email, added_at) keep their exact meaning and position; kind,
    label, status, requested_at and payload are added on top so a client can
    render the other install kinds without a second endpoint.
    """
    from api import approvals

    kind = str(entry.get("kind") or approvals.KIND_SKILL).strip().lower()
    key = str(entry.get("key") or "")
    if kind == approvals.KIND_SKILL:
        parts = _skill_key_parts(key)
        category, name = parts if parts else (None, key)
    else:
        category, name = None, str(entry.get("label") or "").strip() or key
    payload = entry.get("payload")
    return {
        "kind": kind,
        "key": key,
        "name": name,
        "category": category,
        "label": str(entry.get("label") or "").strip() or name,
        "owner_email": entry.get("owner_email"),
        "added_at": entry.get("requested_at"),
        "requested_at": entry.get("requested_at"),
        "status": entry.get("status"),
        "decided_by": entry.get("decided_by"),
        "decided_at": entry.get("decided_at"),
        "reason": entry.get("reason"),
        "payload": payload if isinstance(payload, dict) else {},
    }


def _approval_kinds_param(parsed) -> tuple | None:
    """Optional ?kind= filter (repeatable and/or comma separated)."""
    from api import approvals

    raw = []
    for value in parse_qs(parsed.query or "").get("kind", []):
        raw.extend(part for part in str(value).split(","))
    wanted = [k.strip().lower() for k in raw if k.strip()]
    if not wanted:
        return None
    return tuple(k for k in wanted if k in approvals.KINDS) or ()


def _handle_approvals_get(handler, parsed, policy, subject, access) -> bool:
    """Pending self-service requests (skills, integrations, MCP, CLI).

    Skill rows come from api/skill_ownership through the approvals adapter,
    so the existing skills queue is unchanged; the other kinds come from the
    STATE_DIR approvals registry. Optional ?kind= narrows the queue.
    """
    if not _require_governance_admin(handler, access, subject, policy):
        return True
    from api import approvals, grant_requests

    grant_requests.ingest_spool()
    kinds = _approval_kinds_param(parsed)
    pending = [_approval_row(entry) for entry in approvals.list_pending(kinds=kinds)]
    j(handler, {"pending": pending})
    return True


def _handle_approvals_mine(handler, parsed, policy, subject, access) -> bool:
    """The caller's OWN requests and their current status.

    Deliberately not admin-gated: a non-admin must be able to see whether
    what they asked for is still pending, approved or rejected. The response
    is scoped to the caller's identity, so it never leaks another user's
    requests, and the route is listed in catalog._SELF_ROUTES so a plain
    authenticated session reaches it under enforce.
    """
    from api import approvals

    email = subject.normalized_email or str(subject.email or "").strip().lower()
    if not email:
        # No identity email (auth disabled without bootstrap admins): nothing
        # can be attributed to the caller, so the list is empty by definition.
        j(handler, {"requests": [], "owner_email": None})
        return True
    kinds = _approval_kinds_param(parsed)
    rows = [
        _approval_row(entry)
        for entry in approvals.list_all(kinds=kinds, owner_scope=email)
    ]
    j(handler, {"requests": rows, "owner_email": email})
    return True


def _handle_approvals_decide_generic(handler, parsed, policy, subject, body, kind) -> bool:
    """Approve or reject a non-skill request through api/approvals.

    Approve marks the entry approved (global, or owner-only when the request
    payload carries {"scope": "owner"}); reject keeps the row as rejected so
    the requester sees the outcome and the reason. Nothing is installed or
    removed here: the surface that owns the kind (MCP, integrations, CLI)
    reads api.approvals.is_approved before acting.
    """
    from api import approvals

    key = str(body.get("key") or "").strip()
    if not key:
        j(handler, {"error": "invalid_payload", "message": "key is required"}, status=400)
        return True
    decision = str(body.get("decision") or "").strip().lower()
    if decision not in ("approve", "reject"):
        j(
            handler,
            {"error": "invalid_payload", "message": "decision must be 'approve' or 'reject'"},
            status=400,
        )
        return True
    reason = str(body.get("reason") or "").strip() or None

    entry = approvals.get(kind, key)
    if entry is None:
        j(
            handler,
            {"error": "not_found", "message": f"unknown {kind} approval: {key}"},
            status=404,
        )
        return True
    owner = str(entry.get("owner_email") or "").strip().lower()
    decided_by = subject.normalized_email or str(subject.email or "").strip().lower()
    try:
        updated = approvals.decide(kind, key, decision, decided_by, reason=reason)
    except ValueError as exc:
        j(handler, {"error": "invalid_payload", "message": str(exc)}, status=400)
        return True
    except KeyError:
        j(
            handler,
            {"error": "not_found", "message": f"unknown {kind} approval: {key}"},
            status=404,
        )
        return True
    except OSError:
        logger.exception("Failed to persist approval decision for %s:%s", kind, key)
        j(
            handler,
            {"error": "internal_error", "message": "failed to persist the decision"},
            status=500,
        )
        return True

    if kind == approvals.KIND_MCP:
        # Make the decision take effect on the MCP surface immediately.
        # Approve installs the entry (idempotent, never overwrites an admin's
        # own server) instead of waiting for someone to open the MCP panel;
        # reject UNINSTALLS an already installed server, otherwise a rejected
        # item stays live and "approved then rejected" is not revocable.
        # Neither call can raise into this handler.
        from api import mcp_requests

        if decision == "approve":
            mcp_requests.sync_approved_quietly(decided_by, path=parsed.path)
        else:
            mcp_requests.uninstall_quietly(key, decided_by, path=parsed.path)

    if kind == approvals.KIND_INTEGRATION and decision == "approve":
        # Same immediacy as MCP: approving a provider also creates the Nango
        # integration, so the requester's card flips straight to Connect
        # instead of parking on "an admin is setting it up". Best-effort:
        # a Nango outage must not fail the (already persisted) decision.
        try:
            from api.integrations import enable_integration

            enable_integration(decided_by, key)
        except Exception:
            logger.warning("Approved integration %s but enabling it in Nango failed", key, exc_info=True)

    op = "approvals.approve" if decision == "approve" else "approvals.reject"
    _audit_approval(subject, policy.mode, parsed, op=op, key=f"{kind}:{key}", owner=owner)
    j(
        handler,
        {
            "ok": True,
            "kind": kind,
            "key": key,
            "status": updated.get("status"),
            "entry": _approval_row(updated),
        },
    )
    return True


def _handle_approvals_revoke(handler, parsed, policy, subject, access) -> bool:
    """Remove a decided (or pending) non-skill approval entry entirely.

    The provider/server/command drops back to the never-requested state, so
    the next user goes through the normal request flow again. Skills are
    excluded: their lifecycle (delete-from-disk on reject) lives in the
    decide handler and a silent registry removal would leave the skill
    installed but unaccounted for.
    """
    if not _require_governance_admin(handler, access, subject, policy):
        return True
    body = _read_json(handler)
    if body is None:
        return True
    from api import approvals

    kind = str(body.get("kind") or "").strip().lower()
    if kind not in approvals.KINDS or kind == approvals.KIND_SKILL:
        j(
            handler,
            {"error": "invalid_payload", "message": "kind must be one of: "
             + ", ".join(k for k in approvals.KINDS if k != approvals.KIND_SKILL)},
            status=400,
        )
        return True
    key = str(body.get("key") or "").strip()
    if not key:
        j(handler, {"error": "invalid_payload", "message": "key is required"}, status=400)
        return True
    entry = approvals.get(kind, key)
    owner = str((entry or {}).get("owner_email") or "").strip().lower()
    removed = approvals.remove(kind, key)
    if not removed:
        j(handler, {"error": "not_found", "message": f"unknown {kind} approval: {key}"}, status=404)
        return True
    _audit_approval(subject, policy.mode, parsed, op="approvals.revoke", key=f"{kind}:{key}", owner=owner)
    j(handler, {"ok": True, "kind": kind, "key": key})
    return True


def _handle_grant_request_decide(handler, parsed, policy, subject, body) -> bool:
    """Decide a governance access request (kind "grant").

    Approve applies the grant to the USER entry in the policy document (under
    the policy mutation lock, audited as a policy_change) and then marks the
    registry row approved; reject only marks the row, which keeps future
    denials of the same item from re-nagging the queue. No If-Match here:
    the approvals tab holds no policy etag and the mutation is additive.
    """
    from api import approvals, grant_requests

    key = str(body.get("key") or "").strip()
    decision = str(body.get("decision") or "").strip().lower()
    if not key or decision not in ("approve", "reject"):
        j(handler, {"error": "invalid_payload", "message": "key and decision (approve|reject) required"}, status=400)
        return True
    entry = approvals.get(approvals.KIND_GRANT, key)
    if entry is None:
        j(handler, {"error": "not_found", "message": f"unknown grant request: {key}"}, status=404)
        return True
    if str(entry.get("status") or "pending") != "pending":
        j(handler, {"error": "invalid_payload", "message": "request already decided"}, status=409)
        return True
    decided_by = subject.normalized_email or str(subject.email or "").strip().lower()
    payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}

    if decision == "approve":
        with policy_mutation_lock():
            try:
                current_policy = get_policy()
            except GovernancePolicyError as exc:
                j(handler, {"error": "policy_error", "message": str(exc)}, status=500)
                return True
            raw = _policy_raw(current_policy)
            old_etag = policy_etag(raw)
            result = grant_requests.apply_grant_to_policy(raw, payload)
            if result is None:
                j(handler, {"error": "invalid_payload", "message": "request does not describe an applicable grant"}, status=400)
                return True
            before, after = result
            try:
                save_governance_policy(raw)
            except GovernancePolicyError as exc:
                j(handler, {"error": "invalid_policy", "message": str(exc)}, status=400)
                return True
            new_etag = policy_etag(raw)
        _audit_policy_change(
            subject,
            current_policy.mode,
            parsed,
            op="grant_request_approve",
            target=str(payload.get("email") or ""),
            before=before,
            after=after,
            old_etag=old_etag,
            new_etag=new_etag,
        )
        trigger_profile_sync(str(payload.get("email") or "") or None, reason="grant_request_approve")
        grant_requests.drop_from_spool(key)

    try:
        updated = approvals.decide(approvals.KIND_GRANT, key, decision, decided_by, reason=str(body.get("reason") or "").strip() or None)
    except (ValueError, KeyError) as exc:
        j(handler, {"error": "invalid_payload", "message": str(exc)}, status=400)
        return True
    j(handler, {"ok": True, "kind": approvals.KIND_GRANT, "key": key, "status": str(updated.get("status") or decision)})
    return True


def _handle_approvals_decide(handler, parsed, policy, subject, access) -> bool:
    """Approve or reject a pending self-service request.

    Skills keep their original semantics unchanged: approve flips the
    skill_ownership status to approved (the skill becomes global, visible to
    everyone), reject deletes the skill directory from disk and removes the
    registry entry. The other kinds (integration, mcp, cli) are decided in
    the approvals registry and installed by their own surface. All paths are
    audited with the same approval_decision event.
    """
    if not _require_governance_admin(handler, access, subject, policy):
        return True
    body = _read_json(handler)
    if body is None:
        return True
    from api import approvals

    kind = str(body.get("kind") or "").strip().lower()
    if kind not in approvals.KINDS:
        j(
            handler,
            {
                "error": "invalid_payload",
                "message": "kind must be one of: " + ", ".join(approvals.KINDS),
            },
            status=400,
        )
        return True
    if kind == approvals.KIND_GRANT:
        return _handle_grant_request_decide(handler, parsed, policy, subject, body)
    if kind != approvals.KIND_SKILL:
        return _handle_approvals_decide_generic(handler, parsed, policy, subject, body, kind)

    key = str(body.get("key") or "").strip()
    if not key or _skill_key_parts(key) is None:
        j(handler, {"error": "invalid_payload", "message": "key must be a valid skill key"}, status=400)
        return True
    decision = str(body.get("decision") or "").strip().lower()
    if decision not in ("approve", "reject"):
        j(
            handler,
            {"error": "invalid_payload", "message": "decision must be 'approve' or 'reject'"},
            status=400,
        )
        return True

    from api import skill_ownership

    entry = skill_ownership.get(key)
    if entry is None:
        j(handler, {"error": "not_found", "message": f"unknown skill approval: {key}"}, status=404)
        return True
    owner = str(entry.get("owner_email") or "").strip().lower()

    if decision == "approve":
        skill_ownership.set_status(key, skill_ownership.STATUS_APPROVED)
        _audit_approval(subject, policy.mode, parsed, op="approvals.approve", key=key, owner=owner)
        j(handler, {"ok": True, "key": key, "status": skill_ownership.STATUS_APPROVED})
        return True

    # Reject: delete the skill directory, then drop the registry entry. The
    # key is validated above (no traversal tokens) and the resolved path is
    # re-checked against the skills root, mirroring _handle_skill_save.
    import shutil

    from api import routes as api_routes  # late import (routes imports this module)

    skills_dir = api_routes._active_skills_dir()
    skill_dir = skills_dir / key
    try:
        skill_dir.resolve().relative_to(skills_dir.resolve())
    except (OSError, ValueError):
        j(
            handler,
            {"error": "invalid_payload", "message": "key resolves outside the skills directory"},
            status=400,
        )
        return True
    removed = False
    try:
        if skill_dir.is_symlink():
            skill_dir.unlink()
            removed = True
        elif skill_dir.is_dir():
            shutil.rmtree(str(skill_dir))
            removed = True
    except OSError:
        logger.exception("Failed to remove rejected skill directory %s", skill_dir)
        j(handler, {"error": "internal_error", "message": "failed to remove skill directory"}, status=500)
        return True
    skill_ownership.remove(key)
    try:
        api_routes._SKILLS_STATS_CACHE.clear()
    except Exception:
        pass
    _audit_approval(subject, policy.mode, parsed, op="approvals.reject", key=key, owner=owner)
    j(handler, {"ok": True, "key": key, "removed": removed})
    return True


# ── Dispatch ─────────────────────────────────────────────────────────────────

_GET_ROUTES = {
    "/api/governance/me": _handle_me,
    "/api/governance/policy": _handle_policy_get,
    "/api/governance/users": lambda h, p, pol, s, a: _handle_collection_get(h, p, pol, s, a, key="users"),
    "/api/governance/groups": lambda h, p, pol, s, a: _handle_collection_get(h, p, pol, s, a, key="groups"),
    "/api/governance/audit": _handle_audit_get,
    "/api/governance/usage": _handle_usage_get,
    "/api/governance/approvals": _handle_approvals_get,
    "/api/governance/approvals/mine": _handle_approvals_mine,
}

_POST_ROUTES = {
    "/api/governance/policy": _handle_policy_replace,
    "/api/governance/validate": _handle_validate,
    "/api/governance/preview": _handle_preview,
    "/api/governance/groups": _handle_group_create,
    "/api/governance/groups/update": _handle_group_update,
    "/api/governance/groups/delete": _handle_group_delete,
    "/api/governance/users": _handle_user_create,
    "/api/governance/users/update": _handle_user_update,
    "/api/governance/users/delete": _handle_user_delete,
    "/api/governance/approvals/decide": _handle_approvals_decide,
    "/api/governance/approvals/revoke": _handle_approvals_revoke,
}


def handle_governance_api(handler, parsed, method: str) -> bool:
    """Handle /api/governance/* routes.

    Returns True when parsed.path is under /api/governance/ and a response
    was sent; False otherwise (routes.py continues normal dispatch).
    """
    path = parsed.path.rstrip("/") or parsed.path
    if path != "/api/governance" and not path.startswith(_GOVERNANCE_PREFIX):
        return False

    routes = _GET_ROUTES if (method or "").upper() == "GET" else _POST_ROUTES
    route_func = routes.get(path)
    if route_func is None:
        j(handler, {"error": "not_found", "message": f"unknown governance endpoint: {path}"}, status=404)
        return True

    try:
        policy = get_policy()
    except GovernancePolicyError as exc:
        j(handler, {"error": "policy_error", "message": str(exc)}, status=500)
        return True
    subject = subject_from_identity(_caller_identity(handler))
    access = resolve_effective_access(policy, subject)
    return route_func(handler, parsed, policy, subject, access)
