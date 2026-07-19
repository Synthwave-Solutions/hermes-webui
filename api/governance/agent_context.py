"""Per-turn agent-side governance binding for in-process AIAgent turns.

The hermes-agent repo ships dormant enforcement (hermes_cli.dashboard_governance
tool_policy / model_policy / usage): every gate reads
current_governance_context() and stays inactive while nothing binds it. This
module resolves the webui caller's EffectiveAccess from the shared policy file
(same ~/.hermes/dashboard-governance.yaml the route layer enforces) and binds
the equivalent agent-side DashboardGovernanceContext around the in-process
AIAgent turn, which activates tool/skill/MCP/model/file/CLI/usage-cap
enforcement for non-admin users.

Threading contract: the bind uses the agent-side ContextVar, so it MUST run on
the thread that executes the turn (the _run_agent_streaming worker), never on
the HTTP handler thread (routes.py spawns bare daemon threading.Thread targets,
which start with an EMPTY contextvars Context). Tool-executor threads inherit
the binding because model_tools submits work through
tools.thread_context.propagate_context_to_thread, which snapshots the
submitting thread's Context. The process-global GOVERNANCE_CONTEXT_ENV env-var
route (used by the agent's own web_server for PTY child processes) is
deliberately never used here: os.environ is process-wide, so one user's grants
would leak into every concurrent turn.

Failure semantics mirror the route layer's posture: admins and disabled/broken
policies keep today's unrestricted behavior; a non-admin whose context cannot
be built runs unrestricted under report_only (audited) and is refused under
enforce (fail closed, GovernanceBindingError).
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, Iterator

from . import loader
from .audit import append_audit_event
from .models import GovernanceSubject
from .resolver import resolve_effective_access

logger = logging.getLogger(__name__)


class GovernanceBindingError(RuntimeError):
    """A non-admin turn must not run because the governance context could not
    be built or bound under mode enforce (fail closed). The message is safe to
    surface to the user verbatim."""

    def __init__(self, message: str = "Access restricted: governance context unavailable, ask your admin"):
        super().__init__(message)


def _agent_governance_module():
    """Late import of the agent-side context module.

    api.config appends the hermes-agent checkout root to sys.path at import
    time (the same mechanism that makes ``from run_agent import AIAgent``
    work), so importing it first keeps hermes_cli resolvable in fresh
    processes (tests, tooling) too. Kept as a module-level hook so tests can
    monkeypatch the agent side without a real checkout.
    """
    import api.config  # noqa: F401  (side effect: hermes-agent root on sys.path)
    from hermes_cli.dashboard_governance import context as agent_governance_context
    return agent_governance_context


def _identity_email(identity: Any) -> str:
    """Accept the api.auth identity dict, a bare owner email string, or None."""
    if isinstance(identity, str):
        return identity.strip().lower()
    if isinstance(identity, dict):
        return str(identity.get("email") or "").strip().lower()
    return ""


def _identity_groups(identity: Any) -> tuple[str, ...]:
    """SSO groups when the caller has the full identity dict; sessions only
    persist owner_email, so this is usually empty (policy users are
    email-keyed today, so nothing is lost for them)."""
    if isinstance(identity, dict):
        return tuple(str(g) for g in (identity.get("groups") or ()) if str(g).strip())
    return ()


def _translate_context(agent_mod, policy, email: str, groups: tuple[str, ...],
                       active_profile: str, session_id: str, request_id: str):
    """Resolve access with the WEBUI resolver and bridge it to agent types.

    The webui and agent-side dataclasses are field-identical but distinct
    types, so webui objects must never be handed to the agent gates directly.
    Bridge through the agent's own audited (de)serializer instead: duck-type
    the webui EffectiveAccess into serialize_context_for_env (it only reads
    attributes present on both vendored copies), then rebuild properly typed
    agent-side dataclasses via context_from_env_payload. A new grant dimension
    added agent-side fails loudly here (AttributeError, caught by the caller
    per mode) instead of silently dropping grants.
    """
    subject = GovernanceSubject(email=email, groups=groups)
    access = resolve_effective_access(policy, subject)
    shim = SimpleNamespace(
        access=access,
        active_profile=str(active_profile or "default"),
        session_id=str(session_id or ""),
        request_id=str(request_id or ""),
    )
    payload = agent_mod.serialize_context_for_env(shim)
    ctx = agent_mod.context_from_env_payload(payload)
    if ctx is None:
        # context_from_env_payload returning None would bind nothing and run
        # the turn unrestricted (governance_inactive); refuse instead so the
        # caller applies the per-mode failure policy.
        raise GovernanceBindingError("agent governance payload did not round-trip")
    return ctx


def _audit_bind_failure(email: str, session_id: str, request_id: str,
                        exc: BaseException, *, mode: str, report_only: bool) -> None:
    try:
        append_audit_event(
            "agent_governance_bind_failed",
            subject_email=email,
            reason=f"{type(exc).__name__}: {exc}"[:200],
            mode=mode,
            report_only=report_only,
            extra={"session_id": str(session_id), "stream_id": str(request_id)},
        )
    except Exception:
        # Same posture as enforce._audit_decision: the turn outcome must not
        # depend on the audit sink being writable.
        logger.debug("agent governance bind-failure audit append failed", exc_info=True)


def bind_governed_agent_turn(identity: Any, *, active_profile: str = "default",
                             session_id: str = "", request_id: str = ""):
    """Bind the caller's governance principal to the CURRENT thread's context.

    Returns an opaque token for reset_governed_agent_turn, or None when the
    turn runs unbound (governance off/unreadable, bootstrap admin, ownerless
    session, or agent side unavailable under report_only). Raises
    GovernanceBindingError when a non-admin context cannot be built under
    mode enforce (fail closed; callers surface the message to the user).
    """
    try:
        policy = loader.get_policy()
    except Exception:
        # Policy unreadable: the route layer already fails closed on
        # policy_error for every /api request, so a turn that still reaches
        # this point (auth off, legacy path) keeps current unrestricted
        # behavior rather than double-bricking.
        logger.debug("governed agent turn: policy unreadable, running unbound", exc_info=True)
        return None
    if not getattr(policy, "enabled", False):
        return None

    email = _identity_email(identity)
    if email and email in {str(a).strip().lower() for a in policy.bootstrap_admins}:
        # Never-deny principals: run unbound. The resolver would grant
        # wildcard anyway; skipping the bind keeps admin turns byte-identical
        # to today's behavior (and immune to translation bugs).
        return None
    if not email:
        # Ownerless sessions (legacy rows, cron/CLI-claimed, gateway imports)
        # have no principal to scope; deny-by-default would brick them, so run
        # unbound: exactly the dormant status quo for non-webui-owned turns.
        return None

    try:
        agent_mod = _agent_governance_module()
        ctx = _translate_context(
            agent_mod, policy, email, _identity_groups(identity),
            active_profile, session_id, request_id,
        )
        token = agent_mod.bind_governance_context(ctx)
        return (agent_mod, token)
    except Exception as exc:
        if policy.mode == "enforce":
            _audit_bind_failure(email, session_id, request_id, exc,
                                mode=policy.mode, report_only=False)
            logger.warning("governed agent turn: bind failed under enforce, refusing turn (%s)",
                           type(exc).__name__)
            raise GovernanceBindingError() from exc
        _audit_bind_failure(email, session_id, request_id, exc,
                            mode=policy.mode, report_only=True)
        logger.debug("governed agent turn: bind failed under report_only, running unbound", exc_info=True)
        return None


def reset_governed_agent_turn(token) -> None:
    """Restore the context bound by bind_governed_agent_turn (reset-token
    semantics, safe to call with None). Mirrors _reset_turn_session_identity:
    never raises out of a teardown finally."""
    if not token:
        return
    try:
        agent_mod, ctx_token = token
        agent_mod.reset_governance_context(ctx_token)
    except Exception:
        logger.debug("governed agent turn: context reset failed", exc_info=True)


@contextmanager
def governed_agent_turn(identity: Any, *, active_profile: str = "default",
                        session_id: str = "", request_id: str = "") -> Iterator[None]:
    """Context-manager form of the per-turn governance binding.

    The _run_agent_streaming worker uses the explicit bind/reset pair directly
    (its single try/finally spans the whole turn, including both self-heal
    retries); this wrapper is the canonical single-call API for other callers
    and for tests, and shares the exact same code path.
    """
    token = bind_governed_agent_turn(
        identity,
        active_profile=active_profile,
        session_id=session_id,
        request_id=request_id,
    )
    try:
        yield
    finally:
        reset_governed_agent_turn(token)
