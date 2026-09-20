"""Governance scope filtering for scheduled cron job visibility.

Reported by Michael on 26 Aug 2026: governed WebUI users could see scheduled
jobs outside their authorised scope (names, schedules, prompts, status). The
fix keeps job visibility inside the caller's governance profile scope:

* ``cron:admin`` callers (and the bootstrap admin, and installs where
  governance is off, both of which fail open inside the governance helpers)
  keep the previous behaviour and see every profile's rows.
* Everyone else only sees rows whose owning profile home is granted to their
  identity by the effective governance access (``profiles`` grants).

This lives in its own module on purpose: the ``/api/crons*`` route branches in
api/routes.py sit next to the scheduler delivery backend surface owned by a
concurrent workstream, so routes.py only carries minimal hooks into here.

Failure semantics mirror api/routes.py::_cron_admin_allowed: an unexpected
governance error denies foreign visibility (fails closed) and logs a warning;
the helpers below only fail open when governance itself fails open (policy off
or bootstrap admin).

``report_only`` policy mode never enforces: rows that WOULD be hidden are
recorded as ``would_deny`` audit events and kept visible, mirroring
api/governance/enforce.py::enforce_request.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

CRON_ADMIN_PERMISSION = "cron:admin"


def _policy_mode() -> str:
    """Effective governance mode: off | report_only | enforce.

    Mirrors evaluate_request: an unreadable policy reports ``enforce`` (the
    mode cannot be read, so report_only leniency must not apply).
    """
    from api.governance import loader

    try:
        policy = loader.get_policy()
    except Exception:
        return "enforce"
    if not policy.enabled:
        return "off"
    return policy.mode


def _audit_would_deny(identity, profile) -> None:
    """Append the ``would_deny`` audit row for a report_only scope decision.

    Field-for-field consistent with api/governance/enforce.py::_audit_decision;
    an unwritable audit sink never blocks the visibility decision itself.
    """
    try:
        from api.governance.audit import append_audit_event
        from api.governance.enforce import subject_from_identity

        subject = subject_from_identity(identity)
        append_audit_event(
            "would_deny",
            subject_email=subject.email,
            subject_user_id=subject.user_id,
            path="/api/crons",
            method="GET",
            reason="profile_not_allowed",
            mode="report_only",
            report_only=True,
            extra={"resource": CRON_ADMIN_PERMISSION, "profile": str(profile or "default")},
        )
    except Exception:
        logger.warning("cron scope would_deny audit append failed", exc_info=True)


def identity_sees_cron_profile(identity, profile) -> bool:
    """Pure decision core: may ``identity`` see jobs owned by ``profile``?

    Testable without a handler; the route-facing wrappers below resolve the
    request identity and delegate here. Under ``report_only`` policy mode a
    row that would be hidden is audited as ``would_deny`` and kept visible.
    """
    from api.governance.enforce import identity_has_permission, is_profile_allowed_for

    if identity_has_permission(identity, CRON_ADMIN_PERMISSION):
        return True
    if is_profile_allowed_for(identity, str(profile or "default")):
        return True
    if _policy_mode() == "report_only":
        _audit_would_deny(identity, profile)
        return True
    return False


def _identity_for(handler):
    from api.governance.enforce import _request_identity

    return _request_identity(handler)


def _identity_email(identity) -> str:
    try:
        return str((identity or {}).get("email") or "").strip().lower()
    except Exception:
        return ""


# Owner lookups for legacy WebUI-origin jobs (no ``origin.user_id`` stamp)
# read the originating conversation's sidecar on EVERY /api/crons and Projects
# hub request; five such jobs on the VPS cost 0.7 to 1.2 s per request because
# their sidecars are large. Cache the answer per session keyed by the sidecar's
# (size, mtime_ns): a rewritten sidecar misses, an unchanged one is one stat.
_OWNER_EMAIL_CACHE: dict = {}
_OWNER_EMAIL_CACHE_LOCK = threading.Lock()
_OWNER_EMAIL_CACHE_MAX = 512


def _session_sidecar_signature(session_id: str):
    try:
        from api.config import SESSION_DIR

        st = (Path(SESSION_DIR) / f"{session_id}.json").stat()
        return (st.st_size, st.st_mtime_ns)
    except Exception:
        return None


def _session_owner_email(session_id: str) -> str:
    """Owner email of a WebUI conversation, empty when unknown. Best effort."""
    if not session_id:
        return ""
    sid = str(session_id)
    sig = _session_sidecar_signature(sid)
    if sig is not None:
        with _OWNER_EMAIL_CACHE_LOCK:
            hit = _OWNER_EMAIL_CACHE.get(sid)
            if hit is not None and hit[0] == sig:
                return hit[1]
    try:
        from api.models import get_session

        session = get_session(sid, metadata_only=True)
        email = str(getattr(session, "owner_email", "") or "").strip().lower()
    except Exception:
        return ""
    if sig is not None:
        with _OWNER_EMAIL_CACHE_LOCK:
            if len(_OWNER_EMAIL_CACHE) >= _OWNER_EMAIL_CACHE_MAX:
                _OWNER_EMAIL_CACHE.clear()
            _OWNER_EMAIL_CACHE[sid] = (sig, email)
    return email


def row_owned_by_identity(identity, row, session_owner=None) -> bool:
    """A job created from someone's WebUI conversation belongs to that person.

    Reported by Michael on 27 Aug 2026: a governed user's own scheduled job was
    absent from the list. Jobs the agent creates from a WebUI chat land in
    whichever profile store was active at the time (usually ``default``), and
    the creator's profile grants need not cover that store, so the profile
    check alone hid their own work. Ownership is read from the job's origin:
    ``origin.platform == webui`` and either ``origin.user_id`` (the identity
    email the WebUI stamps at creation) matches the caller, or, for jobs made
    before that stamp existed, the originating conversation is owned by them.
    Non-WebUI origins (telegram, cli, ...) carry no comparable identity and
    stay on the profile rule.
    """
    email = _identity_email(identity)
    if not email or not isinstance(row, dict):
        return False
    origin = row.get("origin")
    if not isinstance(origin, dict):
        return False
    if str(origin.get("platform") or "").strip().lower() != "webui":
        return False
    stamped = str(origin.get("user_id") or "").strip().lower()
    if stamped:
        return stamped == email
    lookup = session_owner or _session_owner_email
    return lookup(str(origin.get("chat_id") or "")) == email


def row_shared_with_identity(identity, row) -> bool:
    """A job explicitly shared with this person (``shared_with`` emails, set from
    the Tasks tab). Sharing grants visibility, output and completion notices,
    not editing: that stays with governance and the owner."""
    email = _identity_email(identity)
    if not email or not isinstance(row, dict):
        return False
    shared = row.get("shared_with")
    if not isinstance(shared, list):
        return False
    return email in {str(x or "").strip().lower() for x in shared}


def _active_store_job(job_id: str):
    """Load one job from the ACTIVE profile's store (the store the detail
    routes serve). None when absent or the cron package is unavailable."""
    if not job_id:
        return None
    try:
        from api.profiles import cron_profile_context

        with cron_profile_context():
            from cron.jobs import get_job

            return get_job(str(job_id))
    except Exception:
        logger.debug("cron scope job lookup failed for %s", job_id, exc_info=True)
        return None


def caller_sees_cron_profile(handler, profile, job_id: str | None = None) -> bool:
    """Route hook for the per-job detail endpoints (output/history/run/recent).

    Those endpoints serve the ACTIVE profile's cron store, so a single check on
    the active profile is enough to stop direct-URL retrieval of jobs outside
    the caller's scope. A ``job_id`` lets a caller reach their OWN job in a
    store their profile grants do not cover (see row_owned_by_identity).
    """
    try:
        identity = _identity_for(handler)
        if identity_sees_cron_profile(identity, profile):
            return True
        if job_id:
            job = _active_store_job(job_id)
            return row_owned_by_identity(identity, job) or row_shared_with_identity(identity, job)
        return False
    except Exception:
        logger.warning("cron scope governance check failed", exc_info=True)
        return False


def scope_cron_rows(identity, active_jobs, other_jobs, session_owner=None):
    """Filter listing rows by the identity's governance scope.

    Returns the ``(active_jobs, other_jobs)`` pair with out-of-scope rows
    removed entirely, so neither their metadata nor their count leaks into the
    ``/api/crons`` payload (``other_profile_count`` is derived from the
    filtered ``other_jobs`` by the route). A row the caller created from their
    own WebUI conversation is always kept, whichever store it lives in.
    """
    decisions: dict[str, bool] = {}

    def _keep(row) -> bool:
        if row_owned_by_identity(identity, row, session_owner) or row_shared_with_identity(identity, row):
            return True
        profile = str((row.get("owner_profile") if isinstance(row, dict) else None) or "default")
        if profile not in decisions:
            decisions[profile] = identity_sees_cron_profile(identity, profile)
        return decisions[profile]

    return (
        [row for row in (active_jobs or []) if _keep(row)],
        [row for row in (other_jobs or []) if _keep(row)],
    )


def _identity_is_cron_admin(identity) -> bool:
    """Admins receive every completion: bootstrap admins, ``cron:admin``
    holders, and any caller while governance is off or unreadable (the
    permission check fails open there, so a single-user install is unchanged)."""
    from api.governance.enforce import identity_has_permission

    try:
        if identity_has_permission(identity, CRON_ADMIN_PERMISSION):
            return True
    except Exception:
        return True
    try:
        from api.ownership import identity_is_admin

        return bool(identity_is_admin(identity))
    except Exception:
        return False


def scope_cron_completions(identity, jobs, session_owner=None):
    """Completion notifications go to the job's creator; admins get them all.

    Requested 20 Sep 2026: every signed-in user was toasted for every cron in
    the store. A job is "yours" by the same rule the listing uses for
    ownership, or when it was shared with you from the Tasks tab, (``origin.platform == webui`` and your identity stamp, or the
    originating conversation is yours). Jobs without a WebUI creator (CLI,
    messaging platforms, imported) only reach admins. An identity without an
    email (password login) keeps the old behaviour so nothing goes dark.
    """
    if not _identity_email(identity) or _identity_is_cron_admin(identity):
        return list(jobs or [])
    return [job for job in (jobs or [])
            if row_owned_by_identity(identity, job, session_owner) or row_shared_with_identity(identity, job)]


def scope_cron_completions_for_caller(handler, jobs):
    """Route hook for ``/api/crons/recent``."""
    try:
        identity = _identity_for(handler)
    except Exception:
        logger.warning("cron completion identity resolution failed", exc_info=True)
        return list(jobs or [])
    try:
        return scope_cron_completions(identity, jobs)
    except Exception:
        logger.warning("cron completion scope filter failed", exc_info=True)
        return list(jobs or [])


def scope_cron_rows_for_caller(handler, active_jobs, other_jobs):
    """Route hook for the ``/api/crons`` listing branch."""
    try:
        identity = _identity_for(handler)
    except Exception:
        logger.warning("cron scope identity resolution failed", exc_info=True)
        identity = None  # anonymous: only passes when governance fails open
    try:
        return scope_cron_rows(identity, active_jobs, other_jobs)
    except Exception:
        logger.warning("cron scope row filter failed", exc_info=True)
        return [], []
