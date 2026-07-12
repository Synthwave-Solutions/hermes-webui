"""Dashboard governance for hermes-webui (vendored engine).

Ported from the hermes-agent dashboard_governance package: policy loading,
access resolution, route catalog, request enforcement, audit and usage.
Stdlib + yaml only; no hermes_cli, no FastAPI. The package is intentionally
independent from authentication: api.auth verifies who the caller is; this
package decides what that caller may do.
"""

from .audit import append_audit_event, read_audit_events
from .catalog import ROUTE_CATALOG, RouteRule, route_permission
from .enforce import Decision, enforce_request, evaluate_request, subject_from_identity
from .loader import (
    GovernancePolicyError,
    get_policy,
    load_governance_policy,
    parse_governance_policy,
    policy_etag,
    policy_mutation_lock,
    resolve_policy_path,
    save_governance_policy,
    set_policy_loader,
)
from .models import AccessDecision, EffectiveAccess, GovernancePolicy, GovernanceSubject
from .resolver import resolve_effective_access

__all__ = [
    "AccessDecision",
    "Decision",
    "EffectiveAccess",
    "GovernancePolicy",
    "GovernancePolicyError",
    "GovernanceSubject",
    "ROUTE_CATALOG",
    "RouteRule",
    "append_audit_event",
    "enforce_request",
    "evaluate_request",
    "get_policy",
    "load_governance_policy",
    "parse_governance_policy",
    "policy_etag",
    "policy_mutation_lock",
    "read_audit_events",
    "resolve_effective_access",
    "resolve_policy_path",
    "route_permission",
    "save_governance_policy",
    "set_policy_loader",
    "subject_from_identity",
]
