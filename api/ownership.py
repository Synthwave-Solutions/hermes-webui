"""Per-user ownership helpers for chat sessions and projects.

Implements the visibility rule from docs/user-isolation-design.md:

- Admins see all rows.
- Non-admins see only rows whose ``owner_email`` matches their identity email.
- Rows without an ``owner_email`` (legacy data, cron/CLI-imported sessions
  with no interactive creator) are admin-only.
- Requests without an identity (auth disabled / internal callers) behave as
  admin so single-user installs keep working unchanged.

The ownership check is independent of the governance ``mode``: it applies in
``off`` and ``report_only`` just like in ``enforce``. The escape hatch is the
env var ``HERMES_WEBUI_USER_ISOLATION`` (default on; ``0``/``false`` disables).
"""
from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

_ADMIN_CACHE_LOCK = threading.Lock()
_ADMIN_CACHE: dict = {}
_ADMIN_CACHE_MAX_ENTRIES = 256


def user_isolation_enabled() -> bool:
    """Return whether per-user ownership filtering is enabled (default on)."""
    raw = str(os.getenv("HERMES_WEBUI_USER_ISOLATION", "") or "").strip().lower()
    return raw not in ("0", "false")


def admin_sees_all() -> bool:
    """Return whether admins may see rows owned by other users (default on).

    Set ``HERMES_WEBUI_ADMIN_SEES_ALL=0`` to give admins the same per-user
    view as everyone else: their own rows only. Admin-only routes (governance,
    approvals, workspace ownership) are unaffected; this flag changes list
    visibility of sessions and projects, nothing else.
    """
    raw = str(os.getenv("HERMES_WEBUI_ADMIN_SEES_ALL", "") or "").strip().lower()
    return raw not in ("0", "false")


def _request_identity(handler):
    """Resolve the authenticated identity dict for a request handler.

    Returns the dict from api.auth.get_session_identity ({email, groups,
    claims_subset, method}), the auth-disabled synthetic identity when auth is
    off, or None when the request carries no identity.
    """
    try:
        from api.governance.enforce import _request_identity as _enforce_request_identity

        return _enforce_request_identity(handler)
    except Exception:
        logger.debug("Failed to resolve request identity for ownership check", exc_info=True)
        return None


def request_owner_email(handler) -> str | None:
    """Return the lowercased identity email for the request, or None."""
    identity = _request_identity(handler)
    if not identity:
        return None
    email = str(identity.get("email") or "").strip().lower()
    return email or None


def identity_is_admin(identity) -> bool:
    """Return whether the identity resolves to an admin, independent of mode.

    True when the resolved EffectiveAccess carries the bootstrap-admin grant
    source, an owner/admin role, wildcard routes, or the governance:write
    permission. The auth-disabled synthetic identity always counts as admin
    (trusted local single-user mode). Fails closed (non-admin) when the
    policy cannot be read for a real identity.
    """
    if not identity:
        return False
    if str(identity.get("method") or "") == "auth_disabled":
        return True
    try:
        from api.governance import loader
        from api.governance.enforce import subject_from_identity
        from api.governance.resolver import resolve_effective_access

        policy = loader.get_policy()
        subject = subject_from_identity(identity)
        cache_key = (
            id(policy),
            subject.normalized_email,
            tuple(sorted(subject.groups)),
        )
        with _ADMIN_CACHE_LOCK:
            cached = _ADMIN_CACHE.get(cache_key)
        if cached is not None:
            return cached
        if subject.normalized_email and subject.normalized_email in {
            admin.lower() for admin in policy.bootstrap_admins
        }:
            result = True
        else:
            access = resolve_effective_access(policy, subject)
            result = (
                "bootstrap_admin" in access.grant_sources
                or "owner" in access.roles
                or "admin" in access.roles
                or "*" in access.routes
                or access.has_permission("governance:write")
            )
        with _ADMIN_CACHE_LOCK:
            if len(_ADMIN_CACHE) >= _ADMIN_CACHE_MAX_ENTRIES:
                _ADMIN_CACHE.clear()
            _ADMIN_CACHE[cache_key] = result
        return result
    except Exception:
        logger.debug("Admin resolution failed; treating identity as non-admin", exc_info=True)
        return False


def request_owner_scope(handler) -> str:
    """Return the ownership scope string for a request.

    'all' for admins, identity-less requests, or when isolation is disabled;
    otherwise the request identity email (lowercased). Used as a cache-key
    component and as a list filter value.
    """
    if not user_isolation_enabled():
        return "all"
    identity = _request_identity(handler)
    if not identity:
        return "all"
    if identity_is_admin(identity) and admin_sees_all():
        return "all"
    return str(identity.get("email") or "").strip().lower()


def request_is_admin(handler) -> bool:
    """Return whether the request identity resolves to an admin.

    Public wrapper over identity_is_admin so route handlers that need an
    admin-only gate (e.g. workspace ownership assignment) do not have to
    import the private _request_identity helper. Identity-less requests with
    auth enabled are non-admin; the auth-disabled synthetic identity counts
    as admin (trusted local single-user mode).
    """
    return identity_is_admin(_request_identity(handler))


_CURRENT_REQUEST = threading.local()


def set_request_context(handler) -> None:
    """Remember the handler of the request being served on this thread.

    Used so code paths far from the HTTP layer (session creation, CLI import,
    background saves) can still resolve who is creating a row. Cleared in a
    finally block by the server, so a pooled thread never carries a stale
    identity into the next request.
    """
    _CURRENT_REQUEST.handler = handler


def clear_request_context() -> None:
    """Forget the handler for this thread."""
    _CURRENT_REQUEST.handler = None


def default_owner_email() -> str | None:
    """Return the fallback owner for rows created without an identity.

    Set ``HERMES_WEBUI_DEFAULT_OWNER`` so API, CLI and cron-created chats get a
    real owner instead of staying ownerless. Without it those rows fall back to
    the old admin-only behaviour.
    """
    return str(os.getenv("HERMES_WEBUI_DEFAULT_OWNER", "") or "").strip().lower() or None


def resolve_new_owner(explicit=None) -> str | None:
    """Return the owner to stamp on a newly created row.

    Order: an explicitly passed owner, then the identity of the request being
    served on this thread, then the configured default owner. Never guesses
    from data already on disk, so loading a row can not re-own it.
    """
    owner = str(explicit or "").strip().lower()
    if owner:
        return owner
    handler = getattr(_CURRENT_REQUEST, "handler", None)
    if handler is not None:
        try:
            owner = request_owner_email(handler) or ""
        except Exception:
            logger.debug("Owner resolution from request context failed", exc_info=True)
            owner = ""
        if owner:
            return owner
    return default_owner_email()


def row_visible_to(owner_email_of_row, handler) -> bool:
    """Return whether a row owned by ``owner_email_of_row`` is request-visible.

    Admins and identity-less requests see all rows. Non-admins see only rows
    whose owner matches their email; rows with no owner are admin-only.
    """
    scope = request_owner_scope(handler)
    if scope == "all":
        return True
    row_owner = str(owner_email_of_row or "").strip().lower()
    if not row_owner:
        return False
    return bool(scope) and row_owner == scope
