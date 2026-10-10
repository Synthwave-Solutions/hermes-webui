"""Delegated administration designations (plan 3.6, read-only in Wave 1).

``delegated_scope(policy, subject)`` answers one question: which part of
this installation may the caller administer on behalf of the organisation?

    platform            a bootstrap admin, or a policy user with
                        ``access_level: admin``
    org                 listed in ``organization.admins``
    billing             listed in ``organization.billing_admins``
    department(keys)    listed in ``departments.<key>.admins``
    none                everybody else

With several designations the widest wins, in that order. Membership is by
exact (normalised) e-mail only: this module never reads grants, roles,
groups or wildcards, so no permission, however broad, makes anybody an
organisation admin. Designations are not permissions and are never injected
into ``EffectiveAccess``; the ``/api/org/*`` handlers and later packages
check them explicitly.

On an installation whose policy says ``installation.kind: hq`` the answer is
``platform`` or ``none``: HQ has no organisation. A subject from the
auth-disabled local mode is ``none`` (it maps to the first bootstrap admin
without anybody having signed in). Any error resolves to ``none``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

from .models import GovernancePolicy, GovernanceSubject, _norm_email

logger = logging.getLogger(__name__)

SCOPE_PLATFORM = "platform"
SCOPE_ORG = "org"
SCOPE_BILLING = "billing"
SCOPE_DEPARTMENT = "department"
SCOPE_NONE = "none"
# Widest first.
SCOPES = (SCOPE_PLATFORM, SCOPE_ORG, SCOPE_BILLING, SCOPE_DEPARTMENT, SCOPE_NONE)

ORG_ROLE_ORG_ADMIN = "org_admin"
ORG_ROLE_BILLING_ADMIN = "billing_admin"


@dataclass(frozen=True)
class DelegatedScope:
    """The caller's designation. ``departments`` is set only for ``department``."""

    scope: str = SCOPE_NONE
    departments: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        """The shape of ``expected.delegated_scope`` in the org_acme fixture."""
        payload: dict[str, Any] = {"scope": self.scope}
        if self.scope == SCOPE_DEPARTMENT:
            payload["departments"] = list(self.departments)
        return payload

    @property
    def is_none(self) -> bool:
        return self.scope == SCOPE_NONE

    def covers_department(self, key: str) -> bool:
        """Whether this designation reaches department ``key``."""
        if self.scope in (SCOPE_PLATFORM, SCOPE_ORG):
            return True
        return self.scope == SCOPE_DEPARTMENT and key in self.departments


NO_SCOPE = DelegatedScope()


def _email_of(subject: Any) -> str:
    if isinstance(subject, GovernanceSubject):
        return subject.normalized_email
    return _norm_email(getattr(subject, "email", "") or "")


def installation_is_hq(policy: GovernancePolicy | None) -> bool:
    """Only a policy that says ``installation.kind: hq`` is HQ."""
    return bool(policy is not None and getattr(policy, "installation_kind", "") == "hq")


def organization_id(policy: GovernancePolicy | None) -> str:
    """``organization.id``, or "" at HQ and when the policy has no organisation."""
    if policy is None or installation_is_hq(policy):
        return ""
    organization = getattr(policy, "organization", None)
    return organization.id if organization is not None else ""


def is_platform_admin(policy: GovernancePolicy, email: str) -> bool:
    """Bootstrap admin, or a policy user with ``access_level: admin``.

    The same definition as the engine's A2A gate (plan 3.6): never a role
    name, a group, a ``*`` grant or any other permission.
    """
    email = _norm_email(email)
    if not email:
        return False
    if email in {_norm_email(a) for a in policy.bootstrap_admins}:
        return True
    user = policy.users.get(email)
    return bool(user is not None and user.access_level == "admin")


def _resolve(policy: GovernancePolicy, subject: Any) -> DelegatedScope:
    if str(getattr(subject, "provider", "") or "") == "auth_disabled":
        return NO_SCOPE
    email = _email_of(subject)
    if not email:
        return NO_SCOPE
    if is_platform_admin(policy, email):
        return DelegatedScope(SCOPE_PLATFORM)
    if installation_is_hq(policy):
        return NO_SCOPE
    organization = policy.organization
    if organization is None:
        return NO_SCOPE
    if email in organization.admins:
        return DelegatedScope(SCOPE_ORG)
    if email in organization.billing_admins:
        return DelegatedScope(SCOPE_BILLING)
    keys = tuple(sorted(key for key, dept in policy.departments.items() if email in dept.admins))
    if keys:
        return DelegatedScope(SCOPE_DEPARTMENT, keys)
    return NO_SCOPE


def delegated_scope(policy: GovernancePolicy | None, subject: Any) -> DelegatedScope:
    """The widest designation of ``subject`` in ``policy``; fails closed to none."""
    if policy is None or subject is None:
        return NO_SCOPE
    try:
        return _resolve(policy, subject)
    except Exception:
        logger.warning("delegated scope could not be resolved; treating the caller as none", exc_info=True)
        return NO_SCOPE


def org_roles_for(policy: GovernancePolicy | None, email: str) -> list[str]:
    """Central organisation roles of ``email`` (``org_admin``, ``billing_admin``).

    Mirrors the render's org_members artifact, which lists only the
    organization block's admins and billing admins; HQ has no organisation.
    """
    email = _norm_email(email)
    if not email or organization_id(policy) == "":
        return []
    organization = policy.organization
    roles = []
    if email in organization.billing_admins:
        roles.append(ORG_ROLE_BILLING_ADMIN)
    if email in organization.admins:
        roles.append(ORG_ROLE_ORG_ADMIN)
    return sorted(roles)


def department_members(policy: GovernancePolicy | None, key: str) -> tuple[str, ...]:
    """Policy users whose groups include department ``key``'s group, sorted.

    Membership is what the policy records (D9: edited in the app, preserved
    on re-render); identity-provider claims play no part, because a
    department group may not be synced from the identity provider.
    """
    if organization_id(policy) == "":
        return ()
    department = policy.departments.get(key)
    if department is None:
        return ()
    return tuple(sorted(email for email, user in policy.users.items() if department.group in user.groups))


def member_departments(policy: GovernancePolicy | None, email: str) -> tuple[str, ...]:
    """Department keys ``email`` is a member of, sorted."""
    email = _norm_email(email)
    if not email or organization_id(policy) == "":
        return ()
    user = policy.users.get(email)
    if user is None:
        return ()
    return tuple(sorted(key for key, dept in policy.departments.items() if dept.group in user.groups))


def admin_departments(policy: GovernancePolicy | None, email: str) -> tuple[str, ...]:
    """Department keys ``email`` administers, sorted."""
    email = _norm_email(email)
    if not email or organization_id(policy) == "":
        return ()
    return tuple(sorted(key for key, dept in policy.departments.items() if email in dept.admins))


def organization_people(policy: GovernancePolicy | None) -> tuple[str, ...]:
    """Every e-mail the policy knows on a client installation, sorted.

    Policy users, bootstrap admins, and every designated admin (who may sign
    in through the identity provider without a users entry).
    """
    if organization_id(policy) == "":
        return ()
    people: set[str] = set(policy.users)
    people.update(_norm_email(a) for a in policy.bootstrap_admins)
    people.update(policy.organization.admins)
    people.update(policy.organization.billing_admins)
    for department in policy.departments.values():
        people.update(department.admins)
    return tuple(sorted(e for e in people if e))


def people_in_departments(policy: GovernancePolicy | None, keys: Iterable[str]) -> tuple[str, ...]:
    """Members of any of the departments ``keys``, sorted and de-duplicated."""
    people: set[str] = set()
    for key in keys:
        people.update(department_members(policy, key))
    return tuple(sorted(people))
