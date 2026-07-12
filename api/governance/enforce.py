"""Request enforcement: pure decision core + one http.server adapter.

The reference enforcement module is FastAPI-coupled; this port keeps its
decision order byte-for-byte and adds two webui-specific checks (non-API
passthrough and the bootstrap-admin never-deny short circuit). The adapter
``enforce_request`` follows the check_auth contract used by server.py:
True = proceed to dispatch, False = a response has already been sent.
It never reads the request body.
"""
from __future__ import annotations

import html as _html
import json
from dataclasses import dataclass
from urllib.parse import parse_qs

from . import loader
from .audit import append_audit_event
from .catalog import _ANON_ROUTES, _SELF_ROUTES, route_permission
from .models import GovernanceSubject
from .resolver import resolve_effective_access


@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str          # governance_off | non_api | anon_route | bootstrap_admin |
                         # allowed | unauthenticated | route_not_allowed |
                         # unknown_route | permission_not_allowed |
                         # profile_not_allowed | policy_error
    resource: str        # permission name from the catalog, "" when not applicable
    mode: str            # off | report_only | enforce


_DENY_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Access restricted</title>
<style>
body { font-family: system-ui, sans-serif; background: #10131a; color: #e6e9f0;
       display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
.card { max-width: 30rem; padding: 2rem 2.5rem; background: #1a1f2b; border-radius: 12px;
        border: 1px solid #2a3245; text-align: center; }
h1 { font-size: 1.25rem; margin: 0 0 0.75rem; }
p { margin: 0 0 1.25rem; color: #aab2c5; line-height: 1.5; }
a { color: #7aa2ff; text-decoration: none; }
</style>
</head>
<body>
<div class="card">
<h1>Access restricted</h1>
<p>Your account does not have access to this resource (%(resource)s).
Ask your administrator or switch accounts.</p>
<a href="/">Back to home</a>
</div>
</body>
</html>
"""


def subject_from_identity(identity: dict | None) -> GovernanceSubject:
    """Build a governance subject from the api.auth session identity dict.

    ``identity`` is the dict returned by api.auth.get_session_identity
    ({email, groups, claims_subset, method}) or None for anonymous/legacy
    sessions. The auth layer owns verification; this only translates the
    safe identity fields into the resolver's principal model.
    """
    if not identity:
        return GovernanceSubject()
    claims = identity.get("claims_subset") or {}
    if not isinstance(claims, dict):
        claims = {}
    return GovernanceSubject(
        email=str(identity.get("email") or "").lower(),
        display_name=str(claims.get("name") or ""),
        provider=str(identity.get("method") or ""),
        user_id=str(claims.get("sub") or ""),
        groups=tuple(str(g) for g in (identity.get("groups") or ()) if str(g).strip()),
        claims=claims,
    )


def evaluate_request(identity: dict | None, method: str, path: str) -> Decision:
    """Single decision entry point.

    ``path`` may carry a querystring; it is split internally (the query is
    used only for the ?profile= target check).
    """
    route_path, _, query = path.partition("?")

    # Pre-auth public login surface: exempt BEFORE the policy is even read, so
    # these endpoints stay reachable under enforce AND under a broken policy.
    # They carry no identity by construction; denying them would 403 every
    # login attempt (including the bootstrap admin's). Returning allow=True
    # also keeps them out of the report_only audit trail.
    if route_path in _ANON_ROUTES:
        return Decision(True, "anon_route", "", "enforce")

    try:
        policy = loader.get_policy()
    except Exception:
        # Policy load/parse errors fail closed: the mode cannot be read, so
        # the decision reports enforce and the adapter denies + audits.
        return Decision(False, "policy_error", "", "enforce")

    if not policy.enabled:
        return Decision(True, "governance_off", "", policy.mode)

    if not route_path.startswith("/api/"):
        # Page loads and static assets are not route-governed; panels are
        # gated by their APIs.
        return Decision(True, "non_api", "", policy.mode)

    subject = subject_from_identity(identity)

    # Bootstrap short circuit: the bootstrap admin can NEVER be denied, even
    # by catalog gaps (unknown_route) or a route whitelist mistake. The
    # resolver also grants wildcard; this guard protects against everything else.
    if subject.normalized_email and subject.normalized_email in {a.lower() for a in policy.bootstrap_admins}:
        return Decision(True, "bootstrap_admin", route_permission(route_path, method) or "", policy.mode)

    if not subject.user_id and not subject.email:
        return Decision(False, "unauthenticated", "", policy.mode)

    access = resolve_effective_access(policy, subject)

    if not access.is_route_allowed(route_path):
        return Decision(False, "route_not_allowed", "", policy.mode)

    perm = route_permission(route_path, method)
    if perm is None and route_path not in _SELF_ROUTES:
        # Unknown /api/* fails closed under enforce, audited under report_only.
        return Decision(False, "unknown_route", "", policy.mode)
    if perm and not access.has_permission(perm):
        return Decision(False, "permission_not_allowed", perm, policy.mode)

    if query:
        for target in parse_qs(query).get("profile", []):
            target = str(target).strip()
            if not target or target == "active":
                continue
            if not access.is_profile_allowed(target):
                return Decision(False, "profile_not_allowed", perm or "", policy.mode)

    return Decision(True, "allowed", perm or "", policy.mode)


def is_profile_allowed_for(identity: dict | None, profile: str) -> bool:
    """Body-sink profile scoping check.

    The enforce hook only inspects the ?profile= query target; endpoints that
    take the profile from the JSON body (POST /api/profile/switch, which then
    mints a signed profile cookie, plus /api/chat, /api/goal,
    /api/projects/create) bypass it. Consumers of a body profile call this to
    reuse the resolver's EffectiveAccess scoping.

    Fails OPEN when governance is off / not loaded / the bootstrap admin is the
    caller, matching evaluate_request; fails CLOSED (False) only when a loaded,
    enabled policy scopes the caller's profiles and the target is not in scope.
    The "active"/empty sentinels and "default" resolve via is_profile_allowed.
    """
    target = str(profile or "").strip()
    if not target or target == "active":
        return True
    try:
        policy = loader.get_policy()
    except Exception:
        # Policy unreadable: do not brick profile switching here. The enforce
        # hook already fails closed on the request itself under policy_error.
        return True
    if not policy.enabled:
        return True
    subject = subject_from_identity(identity)
    if subject.normalized_email and subject.normalized_email in {a.lower() for a in policy.bootstrap_admins}:
        return True
    access = resolve_effective_access(policy, subject)
    return access.is_profile_allowed(target)


def _auth_disabled_identity() -> dict:
    """Trusted local single-user mode: map the request to the bootstrap admin
    so governance cannot brick an auth-off install."""
    email = ""
    try:
        policy = loader.get_policy()
        if policy.bootstrap_admins:
            email = policy.bootstrap_admins[0]
    except Exception:
        email = ""
    return {"email": email, "groups": [], "claims_subset": {}, "method": "auth_disabled"}


def _request_identity(handler) -> dict | None:
    from api import auth  # late import to avoid cycles

    try:
        if not auth.is_auth_enabled():
            return _auth_disabled_identity()
        get_identity = getattr(auth, "get_session_identity", None)
        if not callable(get_identity):
            return None
        cookie = auth.parse_cookie(handler)
        if not cookie:
            return None
        return get_identity(cookie)
    except Exception:
        return None


def _audit_decision(identity: dict | None, parsed, method: str, decision: Decision, *, report_only: bool) -> None:
    try:
        subject = subject_from_identity(identity)
        append_audit_event(
            "would_deny" if report_only else "deny",
            subject_email=subject.email,
            subject_user_id=subject.user_id,
            path=parsed.path,
            method=method,
            reason=decision.reason,
            mode=decision.mode,
            report_only=report_only,
            extra={"resource": decision.resource},
        )
    except Exception:
        # Authorization must not become unavailable because the audit sink
        # is temporarily unwritable. The denial still happens in enforce mode.
        return


def _send_denied(handler, method: str, decision: Decision) -> None:
    accept = str(handler.headers.get("Accept", "") or "")
    if method.upper() == "GET" and "text/html" in accept:
        # Top-level browser navigation: friendly page, no secrets, no traces.
        body = (_DENY_PAGE_HTML % {"resource": _html.escape(decision.resource or decision.reason)}).encode("utf-8")
        ctype = "text/html; charset=utf-8"
    else:
        body = json.dumps({
            "error": "forbidden",
            "resource": decision.resource,
            "reason": decision.reason,
        }).encode("utf-8")
        ctype = "application/json"
    handler.send_response(403)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def enforce_request(handler, parsed, method: str) -> bool:
    """check_auth-shaped contract: True = proceed to dispatch; False = a
    response has already been sent. NEVER reads the request body."""
    identity = _request_identity(handler)
    path = parsed.path + (("?" + parsed.query) if getattr(parsed, "query", "") else "")
    decision = evaluate_request(identity, method, path)
    if decision.allow:
        # Allowed requests are not audited (matches the reference).
        return True
    if decision.mode == "report_only":
        _audit_decision(identity, parsed, method, decision, report_only=True)
        return True
    _audit_decision(identity, parsed, method, decision, report_only=False)
    _send_denied(handler, method, decision)
    return False
