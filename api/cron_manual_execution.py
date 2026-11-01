"""Use the native receipt lifecycle for same-profile manual agent runs.

The native execution ledger owns the attempt; its delivery queue and completion
identity are also used by receipt recovery. No WebUI delivery ledger is added.
"""

from dataclasses import dataclass
import importlib
import os


@dataclass(frozen=True)
class NativeCompletion:
    execution_id: str


def prepare(job, scheduler):
    """Claim a native attempt in the active home, or keep an older engine's path."""
    if job.get("no_agent") or not all(callable(getattr(scheduler, name, None)) for name in (
        "run_job_governed", "_RunDelivery", "_FireOwnership", "_save_compose_deliver",
        "_apply_agent_failure_marker", "_fire_secret_scope",
    )):
        return None
    try:
        authority = importlib.import_module("cron.scheduler_authority")
        executions = importlib.import_module("cron.executions")
        bookkeeping = importlib.import_module("cron.scheduler_bookkeeping")
    except ModuleNotFoundError as exc:
        if exc.name in {"cron.scheduler_authority", "cron.executions", "cron.scheduler_bookkeeping"}:
            return None
        raise
    if not all(callable(getattr(module, name, None)) for module, name in (
        (authority, "run_canonical_job"), (authority, "pause_for_unknown"),
        (executions, "create_execution"), (executions, "mark_execution_handoff_pending"),
        (executions, "adopt_claimed_execution"), (executions, "execution_owner_live"),
        (executions, "give_up_execution"), (executions, "terminalize_dead_owner"),
        (bookkeeping, "finish_completed_run"), (bookkeeping, "fail_empty_response"),
    )):
        return None
    execution_id = executions.create_execution(job["id"], source="webui-manual")["id"]
    try:
        if executions.mark_execution_handoff_pending(execution_id) is None:
            raise RuntimeError("Manual cron execution could not be handed to its worker")
    except BaseException as exc:
        executions.finish_execution(execution_id, success=False, error=str(exc))
        raise
    return execution_id


def complete_in_child(job, execution_id, run, *, refusal_type, profile_home=None):
    """Adopt, run and finish while this child owns the native execution row."""
    from cron import executions, scheduler
    from cron.execution_identity import enter_cron_execution, exit_cron_execution
    from cron.scheduler_bookkeeping import fail_empty_response, finish_completed_run
    from contextlib import nullcontext
    from api.profiles import cron_profile_context_for_home

    def home():
        return cron_profile_context_for_home(profile_home) if profile_home is not None else nullcontext()

    if job.get("execution_id") != execution_id:
        raise RuntimeError("Manual cron execution identity mismatch")
    with home():
        record = executions.adopt_claimed_execution(execution_id)
        if record is None or record["job_id"] != job["id"]:
            raise RuntimeError("Manual cron execution ownership was not acquired")
        token = enter_cron_execution(job, execution_id, record)
    try:
        result = run()
        success, output, answer, error = result
        success, error, declared = scheduler._apply_agent_failure_marker(job, success, error, answer)
        delivery = scheduler._RunDelivery(job, success, error, agent_declared=declared)
        with home(), scheduler._fire_secret_scope():
            scheduler._save_compose_deliver(
                delivery, scheduler._FireOwnership(dict(job, fire_claim=None)), answer, output,
                adapters=None, loop=None, verbose=False, execution_token=None,
            )
            fail_empty_response(delivery, answer)
            finish_completed_run(delivery, None, execution_id)
            require_completed(job["id"], execution_id)
        return NativeCompletion(execution_id)
    except refusal_type as exc:
        with home():
            executions.finish_execution(execution_id, success=False, error=str(exc))
        raise
    except BaseException as exc:
        with home():
            settle_error(job, execution_id, str(exc))
        raise
    finally:
        exit_cron_execution(token)


def require_completed(job_id, execution_id):
    """A child envelope alone cannot authorize skipping the parent's legacy tail."""
    from cron.executions import get_execution

    row = get_execution(execution_id)
    if not row or row["job_id"] != job_id or row["status"] not in {"completed", "failed"}:
        raise RuntimeError("Manual cron completion was not recorded by its native owner")


def settle_error(job, execution_id, error):
    """Leave admitted work to native recovery; record only a proven unadmitted failure.

    This also handles a failed spawn or dead child. A live adopted worker keeps
    ownership. An existing terminal result must never be overwritten by a lost
    queue response or a parent-side wait error.
    """
    from cron import executions, jobs
    from cron.scheduler_authority import journal_path, pause_for_unknown

    row = executions.get_execution(execution_id)
    if not row or row["job_id"] != job["id"]:
        raise RuntimeError("Manual cron execution record is missing or mismatched")
    if row["status"] in {"completed", "failed"}:
        return
    owns = row["pid"] == os.getpid()
    if not owns and executions.execution_owner_live(execution_id, job["id"]):
        return
    if journal_path(job["id"], execution_id).exists():
        pause_for_unknown(job["id"], execution_id, error)
        if owns:
            executions.give_up_execution(execution_id, reason=error)
        else:
            executions.terminalize_dead_owner(execution_id, reason=error)
        return
    # Native agent work writes its admission journal before submission. No
    # journal and no live foreign owner means there is no result to replay.
    jobs.mark_job_run(job["id"], False, error, execution_id=execution_id,
                      delivery_outcome="suppressed")
    if owns:
        executions.finish_execution(execution_id, success=False, error=error,
                                    delivery_outcome="suppressed")
    else:
        executions.terminalize_dead_owner(execution_id, reason=error)
