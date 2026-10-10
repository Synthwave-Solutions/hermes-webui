"""Organisation routes under ``/api/org/`` (plan 3.6, read-only in Wave 1).

Five GET views for the people who administer the organisation on its own
installation:

    /api/org/overview      platform, org, billing, department
    /api/org/departments   platform, org, department (own departments only)
    /api/org/people        platform, org, department (own departments only)
    /api/org/approvals     platform, org, department (own departments only)
    /api/org/usage         platform, org, billing, department (own departments only)

They are self routes in the governance catalog, so the enforcement hook lets
every signed-in person through and each handler decides from
``delegated_scope()`` itself, in every governance mode: a member without a
designation gets 403 and nothing else. When the installation has no
organisation (HQ, or a policy without an ``organization`` block) the routes
answer 404, exactly like an unknown route. A policy that cannot be read
answers 503; scope is never widened on doubt.

Everything here reads; mutations arrive with W3b in Wave 2 and answer 405
until then.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from types import SimpleNamespace

from api.governance import delegation
from api.governance.delegation import (
    SCOPE_BILLING,
    SCOPE_DEPARTMENT,
    SCOPE_ORG,
    SCOPE_PLATFORM,
    DelegatedScope,
)
from api.governance.models import GovernanceSubject
from api.helpers import j

logger = logging.getLogger(__name__)

_ALL = frozenset({SCOPE_PLATFORM, SCOPE_ORG, SCOPE_BILLING, SCOPE_DEPARTMENT})
_ADMINISTRATION = frozenset({SCOPE_PLATFORM, SCOPE_ORG, SCOPE_DEPARTMENT})
# Organisation-wide views: every department, every person.
_WHOLE_ORG = frozenset({SCOPE_PLATFORM, SCOPE_ORG})


# ── Shared helpers ───────────────────────────────────────────────────────────

def _in_scope_departments(policy, scope: DelegatedScope) -> list[str]:
    return sorted(key for key in policy.departments if scope.covers_department(key))


def _in_scope_people(policy, scope: DelegatedScope) -> tuple[str, ...]:
    if scope.scope in _WHOLE_ORG or scope.scope == SCOPE_BILLING:
        return delegation.organization_people(policy)
    return delegation.people_in_departments(policy, scope.departments)


def _department_row(policy, key: str) -> dict:
    department = policy.departments[key]
    return {
        "key": key,
        "name": department.name,
        "group": department.group,
        "admins": list(department.admins),
        "assignable_roles": list(department.assignable_roles),
        "assignable_groups": list(department.assignable_groups),
        "member_count": len(delegation.department_members(policy, key)),
    }


# ── Views ────────────────────────────────────────────────────────────────────

def _overview(policy, scope: DelegatedScope, subject: GovernanceSubject) -> dict:
    organization = policy.organization
    departments = _in_scope_departments(policy, scope)
    payload = {
        "organization": {"id": organization.id, "name": organization.name},
        "installation": {"kind": policy.installation_kind or "client"},
        "viewer": {"email": subject.normalized_email, "delegated_scope": scope.to_dict()},
        "departments": [{"key": key, "name": policy.departments[key].name} for key in departments],
        "counts": {
            "people": len(_in_scope_people(policy, scope)),
            "departments": len(departments),
        },
    }
    if scope.scope != SCOPE_DEPARTMENT:
        # Who the organisation's admins are is organisation-level
        # information; a department admin sees their own department only.
        payload["admins"] = list(organization.admins)
        payload["billing_admins"] = list(organization.billing_admins)
    return payload


def _departments(policy, scope: DelegatedScope, subject: GovernanceSubject) -> dict:
    return {"departments": [_department_row(policy, key) for key in _in_scope_departments(policy, scope)]}


def _person_row(policy, email: str, scope: DelegatedScope) -> dict:
    user = policy.users.get(email)
    member_of = delegation.member_departments(policy, email)
    admin_of = delegation.admin_departments(policy, email)
    row = {
        "email": email,
        "roles": sorted(user.roles) if user is not None else [],
    }
    if scope.scope in _WHOLE_ORG:
        row.update({
            "groups": sorted(user.groups) if user is not None else [],
            "departments": list(member_of),
            "admin_of": list(admin_of),
            "org_roles": delegation.org_roles_for(policy, email),
            "platform_admin": delegation.is_platform_admin(policy, email),
        })
    else:
        # A department admin sees their own departments only, not where else
        # a colleague belongs or what else they administer.
        row.update({
            "departments": [key for key in member_of if key in scope.departments],
            "admin_of": [key for key in admin_of if key in scope.departments],
        })
    return row


def _people(policy, scope: DelegatedScope, subject: GovernanceSubject) -> dict:
    return {"people": [_person_row(policy, email, scope) for email in _in_scope_people(policy, scope)]}


def _approvals(policy, scope: DelegatedScope, subject: GovernanceSubject) -> dict:
    """Pending requests in scope.

    Platform admins see every kind. Organisation and department admins see
    access requests (kind ``grant``) only: MCP, integration, skill and CLI
    requests stay platform-only (plan 3.6). A department admin sees the
    requests of their departments' members. Read only: the spool that the
    engine writes is not ingested here (the governance queue does that).
    """
    from api import approvals
    from api.governance_api import _approval_row

    rows = approvals.list_pending()
    if scope.scope != SCOPE_PLATFORM:
        rows = [row for row in rows if str(row.get("kind") or "").strip().lower() == approvals.KIND_GRANT]
    if scope.scope == SCOPE_DEPARTMENT:
        members = set(delegation.people_in_departments(policy, scope.departments))
        rows = [row for row in rows if str(row.get("owner_email") or "").strip().lower() in members]
    return {"pending": [_approval_row(row) for row in rows]}


def _usage(policy, scope: DelegatedScope, subject: GovernanceSubject) -> dict:
    """Today's and this month's governed usage counters in scope.

    The counters are the governance usage state (tool calls, file writes,
    MCP calls, background processes), keyed per person exactly as the usage
    module keys them. Platform, organisation and department admins get one
    row per person they administer; a billing admin gets the organisation
    totals only, never a row per person. Model usage and department quotas
    come later (plan 3.6, Wave 3).
    """
    from api.governance import usage

    state = usage.read_usage_state()
    day, month = usage._today(), usage._month()
    days = state.get("days") if isinstance(state.get("days"), dict) else {}
    months = state.get("months") if isinstance(state.get("months"), dict) else {}
    today = days.get(day) if isinstance(days.get(day), dict) else {}
    this_month = months.get(month) if isinstance(months.get(month), dict) else {}

    def count(value) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    def counters(bucket, email):
        key = usage._subject_key(SimpleNamespace(subject=GovernanceSubject(email=email)))
        values = bucket.get(key) if isinstance(bucket.get(key), dict) else {}
        return {name: count(values.get(name)) for name in usage._empty_counters()}

    people = [
        {"email": email, "today": counters(today, email), "month": counters(this_month, email)}
        for email in _in_scope_people(policy, scope)
    ]
    totals = {
        period: {name: sum(row[period][name] for row in people) for name in usage._empty_counters()}
        for period in ("today", "month")
    }
    if scope.scope == SCOPE_BILLING:
        people = []
    return {"period": {"day": day, "month": month}, "totals": totals, "people": people}


_GET_VIEWS = {
    "/api/org/overview": (_overview, _ALL),
    "/api/org/departments": (_departments, _ADMINISTRATION),
    "/api/org/people": (_people, _ADMINISTRATION),
    "/api/org/approvals": (_approvals, _ADMINISTRATION),
    "/api/org/usage": (_usage, _ALL),
}


# ── Dispatch ─────────────────────────────────────────────────────────────────

def handle_get(handler, parsed) -> bool:
    """Read-only organisation views. False (404) for any other path and on
    an installation without an organisation."""
    path = str(getattr(parsed, "path", "") or "")
    entry = _GET_VIEWS.get(path)
    if entry is None:
        return False
    view, allowed = entry

    from api.governance import loader
    from api.governance.enforce import _request_identity, subject_from_identity

    try:
        policy = loader.get_policy()
    except Exception:
        j(handler, {"error": "policy_unavailable"}, status=503)
        return True
    if not delegation.organization_id(policy):
        return False
    subject = subject_from_identity(_request_identity(handler), policy)
    scope = delegation.delegated_scope(policy, subject)
    if scope.scope not in allowed:
        j(handler, {"error": "forbidden", "reason": "delegated_scope"}, status=403)
        return True
    try:
        payload = view(policy, scope, subject)
    except Exception:
        logger.exception("GET %s failed", path)
        j(handler, {"error": "internal_error"}, status=500)
        return True
    payload["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    j(handler, payload)
    return True


def handle_post(handler, parsed, body) -> bool:
    """Organisation mutations (W3b, Wave 2). Until then 405."""
    j(handler, {"error": "Method not allowed"}, status=405)
    return True
