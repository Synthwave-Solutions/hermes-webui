"""Per-job notification settings for scheduled tasks (scaffold stub).

The managed-service program (plan 3.1, Appendix E.1) routes every cron
notification decision in api/routes.py through the functions below. This
module is the Wave 0 stub: each function returns exactly what the code did
before the seam existed, so the scaffold changes no behaviour. Package W1
fills the bodies (notify resolution against ``cron/notify_policy.py`` with
``api/_notify_policy_fallback.py`` as the fallback, the per-viewer mute
store and the ``/api/crons/notifications`` routes).

The signatures are the contract with api/routes.py; W1 keeps them.
"""

from __future__ import annotations


def decorate_job(payload: dict, viewer: str | None = None) -> dict:
    """Add the notify fields to one ``GET /api/crons`` job payload.

    Called after the delivery state is set. ``viewer`` is the signed-in
    email of the request (None for callers without one). Returns the payload
    to send; the stub returns it unchanged.
    """
    return payload


def decorate_completion(completion: dict, job: dict, viewer: str | None = None) -> dict:
    """Add the in-app flags to one ``GET /api/crons/recent`` completion.

    Returns the completion to send; the stub returns it unchanged.
    """
    return completion


def validate_notify_field(value):
    """Validate the ``notify`` field of a cron create or update.

    Returns the value stored as the job's ``notify`` (a normalized dict, or
    None to clear it). A ValueError becomes a 400 with its message. The stub
    refuses every value, so ``notify`` keeps answering 400 as before.
    """
    raise ValueError("notify is not supported yet")


def manual_run_kwargs(job: dict, actor: str | None = None) -> dict:
    """Extra keyword arguments for ``cron.scheduler.run_job`` on "Run now".

    ``actor`` is the signed-in email of the caller. The runner passes only
    the keys ``run_job`` accepts. The stub adds none.
    """
    return {}


def delivery_decision(job: dict, *, success: bool, silent: bool, default: bool) -> tuple:
    """Decide whether a manual run delivers its result.

    ``default`` is the decision the WebUI made before notify existed.
    Returns ``(deliver, outcome)``; ``outcome`` is the delivery outcome to
    record (for example ``suppressed_muted``) or None. The stub keeps the
    default and records nothing.
    """
    return default, None


def record_manual_outcome(job_id, success, error, *, delivery_error=None, outcome=None) -> None:
    """Record the result of a manual run on the job.

    Called inside the job's cron store context. The stub calls
    ``cron.jobs.mark_job_run`` exactly as the WebUI did before, including the
    fallback for engines whose ``mark_job_run`` takes no ``delivery_error``.
    """
    from cron.jobs import mark_job_run

    try:
        mark_job_run(job_id, success, error, delivery_error=delivery_error)
    except TypeError:
        # Older/fake cron.jobs modules may not expose the delivery_error
        # parameter (see the matching note in api/routes.py).
        mark_job_run(job_id, success, error)


def handle_notifications_get(handler, parsed) -> bool:
    """``GET /api/crons/notifications``. The stub answers 404 (False)."""
    return False


def handle_notifications_post(handler, body) -> bool:
    """``POST /api/crons/notifications``. The stub answers 404 (False)."""
    return False
