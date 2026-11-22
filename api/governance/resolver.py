from __future__ import annotations

import logging
import os
from collections import defaultdict
from dataclasses import replace
from typing import Iterable

from .models import (
    EffectiveAccess,
    GrantSet,
    GovernancePolicy,
    GovernanceSubject,
    _norm_email,
    intersect_grants,
    grant_matches,
    permission_matches,
)


logger = logging.getLogger(__name__)

# The supplier's staff that the central Cloud assigned to this installation
# (consultant, developer, qa) sign in through their personal Cloud link without
# being a user of the customer's policy. They get exactly one role, and only
# when the policy defines it: the grants are the policy's, rendered centrally
# like every other role; the assignment (pulled over the signed control-plane
# channel into the team structure) only decides who holds it, and for how long.
# Without the role in the policy, or without SP_CLOUD_PERSONAL_MSP=1, nothing
# changes: an unknown address keeps resolving to no access at all.
PARTNER_ROLE = "synthwave_partner"
PARTNER_LOGIN_ENV = "SP_CLOUD_PERSONAL_MSP"
# Whatever the role says, a partner never administers the installation and
# never reaches the customer's money: these are subtracted after the role.
PARTNER_DENY = GrantSet(
    permissions=frozenset({"governance:*", "org:*", "billing:*", "departments:*", "support:*", "*:admin"}),
    routes=frozenset({
        "/api/governance/policy*", "/api/governance/users*", "/api/governance/groups*", "/api/governance/audit*",
        "/api/governance/usage*", "/api/governance/validate*", "/api/governance/preview*", "/api/governance/approvals",
        "/api/management/*", "/api/value/*", "/api/msp/*", "/api/admin/*",
        "/api/org/overview", "/api/org/departments", "/api/org/people", "/api/org/approvals", "/api/org/usage",
        "/api/org/modules*",
    }),
)


def partner_role_for(policy: GovernancePolicy, email: str):
    """The policy's partner role when ``email`` is a current, centrally assigned partner, else None.

    Fails closed: any doubt (no role, switch off, a policy user or bootstrap
    admin with their own entry, an unreadable structure) gives None.
    """
    if not email or os.environ.get(PARTNER_LOGIN_ENV) != "1":
        return None
    role = policy.roles.get(PARTNER_ROLE)
    if role is None or email in policy.users or email in policy.bootstrap_admins:
        return None
    try:
        from api import org_structure

        if org_structure.cloud_partner_for(email) is None:
            return None
    except Exception:
        logger.warning("partner lookup failed in the governance resolver", exc_info=True)
        return None
    return role


def _add_permission_sources(target: dict[str, set[str]], grants: GrantSet, source: str) -> None:
    for permission in grants.permissions:
        target[permission].add(source)


def _merge_grant(current: GrantSet, incoming: GrantSet, source: str, sources: list[str], permission_sources: dict[str, set[str]]) -> GrantSet:
    sources.append(source)
    _add_permission_sources(permission_sources, incoming, source)
    return current.merge(incoming)


def _matching_sso_groups(policy: GovernancePolicy, subject_groups: Iterable[str]) -> set[str]:
    claimed = {str(group).strip() for group in subject_groups if str(group).strip()}
    if not claimed:
        return set()
    matches: set[str] = set()
    for name, group in policy.groups.items():
        if claimed & set(group.sso_groups):
            matches.add(name)
    return matches


def _role_names_for(policy: GovernancePolicy, direct_roles: Iterable[str], group_names: Iterable[str]) -> set[str]:
    names = {str(role).strip() for role in direct_roles if str(role).strip()}
    for group_name in group_names:
        group = policy.groups.get(group_name)
        if group:
            names.update(str(role).strip() for role in group.roles if str(role).strip())
    return names


def _wildcard_grants() -> GrantSet:
    star = frozenset({"*"})
    return GrantSet(
        permissions=star,
        profiles=star,
        routes=star,
        settings_read=star,
        settings_write=star,
        toolsets=star,
        tools=star,
        skills_view=star,
        skills_load=star,
        skills_manage=star,
        mcp_servers=star,
        mcp_tools={"*": star},
        model_providers=star,
        models=star,
        file_read_roots=star,
        file_write_roots=star,
        cli_commands=star,
        cli_workdir_roots=star,
        workspaces=star,
    )


def _level_ceiling(grants: GrantSet, level: str) -> GrantSet:
    """Levels constrain configured role scopes; they do not invent resources."""
    if level == "admin":
        return grants
    from .catalog import ROUTE_CATALOG
    known = {p for rule in ROUTE_CATALOG for p in (rule.read_permission, rule.write_permission) if p}
    known.update({"self:read", "config:write", "terminal:use"})
    def permitted(p):
        if p.startswith("governance:"):
            return False
        if level == "user" and (p.endswith(":admin") or p in {
            "terminal:use", "config:write", "system:write", "system:ops", "gateway:restart",
            "model:write", "mcp:write", "plugins:write",
        }):
            return False
        return True
    # permission_matches: a wildcard in the grants never admits a reserved
    # catalog permission (org:, billing:, departments:, support:, a2a:,
    # screen:) into the ceiling; only an entry naming its namespace does
    # (plan 3.6, defence in depth next to EffectiveAccess.allows).
    return replace(grants, permissions=frozenset(
        p for p in known | set(grants.permissions)
        if not any(char in p for char in "*?[") and permitted(p) and permission_matches(grants.permissions, p)))


def resolve_effective_access(policy: GovernancePolicy, subject: GovernanceSubject) -> EffectiveAccess:
    email = _norm_email(subject.email)
    sources: list[str] = []
    permission_sources: dict[str, set[str]] = defaultdict(set)
    grants = GrantSet()
    roles: set[str] = set(str(role).strip() for role in subject.roles if str(role).strip())
    groups: set[str] = set(str(group).strip() for group in subject.groups if str(group).strip())

    if email and email in policy.bootstrap_admins:
        grants = _merge_grant(grants, _wildcard_grants(), "bootstrap_admin", sources, permission_sources)
        roles.add("owner")

    user = policy.users.get(email) if email else None
    if user:
        roles.update(user.roles)
        groups.update(user.groups)

    groups.update(_matching_sso_groups(policy, subject.groups))
    roles.update(_role_names_for(policy, roles, groups))

    # Apply role grants before group/user grants so direct grants can be shown last in previews.
    for role_name in sorted(roles):
        role = policy.roles.get(role_name)
        if role:
            grants = _merge_grant(grants, role.grants, f"role:{role_name}", sources, permission_sources)
    for group_name in sorted(groups):
        group = policy.groups.get(group_name)
        if group:
            grants = _merge_grant(grants, group.grants, f"group:{group_name}", sources, permission_sources)
    role_ceiling = None
    direct_grants_applied = False
    partner_role = partner_role_for(policy, email) if user is None else None
    if partner_role is not None:
        grants = _merge_grant(grants, partner_role.grants, f"partner:{PARTNER_ROLE}", sources, permission_sources)
        grants = grants.subtract(PARTNER_DENY)
        roles.add(PARTNER_ROLE)
        # Never above an ordinary user, whatever the role lists.
        role_ceiling = _level_ceiling(grants, "user")
    if user and (user.access_mode or user.access_level) and email not in policy.bootstrap_admins:
        level = user.access_level or "user"
        if user.access_mode == "blacklist":
            # Blacklist is default-allow, not a role's implicit allowlist.
            # Keep configured denies, exceptions, caps and explicit secret
            # forwarding; the operational wildcard does not grant env vars.
            grants = _merge_grant(grants, user.grants, f"user:{email}", sources, permission_sources)
            direct_grants_applied = True
            grants = _merge_grant(grants, _wildcard_grants(), "access_mode:blacklist", sources, permission_sources)
            # 14-09-2026 (Michael): a blacklist account carries exactly ONE
            # file blacklist, its own. Role and group denied_globs are the
            # generic secret rules written for whitelist colleagues; merged
            # into a default-allow account they closed ~/.hermes, every .env
            # and every key file the person was otherwise allowed to reach.
            grants = replace(grants, file_denied_globs=frozenset(user.grants.file_denied_globs))
        else:
            # Whitelist and level-only legacy entries retain their configured
            # resource ceiling. Bootstrap ownership is handled separately.
            if level == "admin":
                grants = grants.merge(_wildcard_grants())
            if not user.access_mode:
                grants = grants.merge(user.grants)
            role_ceiling = _level_ceiling(grants, level)
            grants = intersect_grants(user.grants, role_ceiling) if user.access_mode == "whitelist" else role_ceiling
            sources.append(f"access_mode:{user.access_mode or 'legacy'}")
        roles.difference_update({"owner", "admin"})
    if user:
        if role_ceiling is None and not direct_grants_applied:
            grants = _merge_grant(grants, user.grants, f"user:{email}", sources, permission_sources)
        elif not direct_grants_applied:
            sources.append(f"user:{email}")
        # Approval selectors restrict existing command access; unlike grants,
        # they must survive every access mode.
        grants = replace(grants, cli_approval_commands=grants.cli_approval_commands | user.grants.cli_approval_commands)
    if user and not user.deny.is_empty() and email not in policy.bootstrap_admins:
        # Per-user off-toggles subtract AFTER the full union so they win from
        # any role/group grant. Bootstrap admins are exempt (never-deny
        # principals: a stray deny: "*" must not brick the owner).
        grants = grants.subtract(user.deny)
        sources.append(f"deny:user:{email}")
        for permission in user.deny.permissions:
            permission_sources.pop(permission, None)

    if user and (role_ceiling is not None or user.access_mode == "blacklist") and user.access_level == "admin" and grant_matches(grants.permissions, "governance:write") and not grant_matches(user.deny.permissions, "governance:write"):
        roles.add("admin")
    return EffectiveAccess(
        subject=subject,
        mode=policy.mode,
        roles=frozenset(roles),
        groups=frozenset(groups),
        permissions=grants.permissions,
        profiles=grants.profiles,
        routes=grants.routes,
        grants=grants,
        grant_sources=tuple(sources),
        permission_sources={key: tuple(sorted(value)) for key, value in permission_sources.items()},
        deny=PARTNER_DENY if partner_role is not None else (
            user.deny if user and email not in policy.bootstrap_admins else GrantSet()),
        role_ceiling=role_ceiling,
        access_level=user.access_level if user else "",
        access_mode=user.access_mode if user else "",
        approval_mode=user.approval_mode if user else "manual",
        approval_prompt=user.approval_prompt if user else "",
        approval_configured=user.approval_configured if user else False,
    )
