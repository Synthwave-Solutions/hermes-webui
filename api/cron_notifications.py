"""Per-job notification settings for scheduled tasks (plan 3.1, Appendix E.1).

A job carries one engine-owned field ``notify`` with two independent levels:
``in_app`` (toasts, badges, unread markers and desktop notifications in the
WebUI) and ``delivery`` (chat and email delivery of the run's result). The
decision itself lives in the engine's ``cron/notify_policy.py``;
``notify_policy()`` uses that module when the engine has it and the pinned
byte copy ``api/_notify_policy_fallback.py`` otherwise.

api/routes.py calls the functions below at fixed seams (Appendix E.1):

* ``decorate_job`` adds ``notify`` (resolved), ``notify_source``, the
  viewer's own ``my_notify``, ``managed_by`` and ``support_notified`` to each
  ``GET /api/crons`` job.
* ``decorate_completion`` adds the effective in-app flags ``toast``,
  ``badge``, ``desktop`` and ``silent`` to each ``GET /api/crons/recent``
  completion: the AND of the job level and the viewer's own level. Older
  clients keep reading ``toast_notifications``, which now carries the same
  effective toast decision.
* ``validate_notify_field`` checks a ``notify`` value on cron create and
  update. ``off`` (in-app or delivery) is set and lifted by cron admins only.
* ``manual_run_kwargs``, ``delivery_decision`` and ``record_manual_outcome``
  shape "Run now": the trigger and actor for engines whose ``run_job`` takes
  them, the delivery gate, and the recorded outcome. An engine whose
  ``mark_job_run`` takes ``delivery_outcome`` records a muted or silent run
  itself; until then the WebUI records it in its delivery bridge ledger
  (api/cron_webui_delivery.py).
* ``handle_notifications_get`` and ``handle_notifications_post`` serve
  ``/api/crons/notifications``: each person's own in-app mute per job, stored
  in the WebUI state directory. It only lowers what that person sees; the
  job's owner and everyone else are unaffected.

Muting never touches incident recording, admin capacity alerts or the
central error feed: those do not go through these seams.
"""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from api import _notify_policy_fallback as _fallback_policy

logger = logging.getLogger(__name__)

ENGINE_POLICY_MODULE = "cron.notify_policy"

# The Appendix A surface an engine module must have before it is used.
_POLICY_API = (
    "LEVELS_IN_APP",
    "LEVELS_DELIVERY",
    "ALERT_KINDS",
    "OUTCOME_MUTED",
    "normalize_notify",
    "resolve_notify",
    "default_notify_for_new_job",
    "should_deliver",
    "in_app_flags",
    "combine_flags",
    "legacy_toast_value",
    "normalize_managed_by",
)

NOTIFY_KEYS = ("in_app", "delivery")

# Delivery outcomes a manual run can record. Muted is the engine's own value
# (policy.OUTCOME_MUTED); a silent run is "suppressed" in the engine and
# "suppressed_silent" in the WebUI bridge ledger.
OUTCOME_MUTED = _fallback_policy.OUTCOME_MUTED
OUTCOME_SILENT = "suppressed_silent"
_ENGINE_OUTCOMES = {OUTCOME_MUTED: OUTCOME_MUTED, OUTCOME_SILENT: "suppressed"}

# Decision D8: job-level in-app "off" also silences cron admins. The setting
# (or the env var, which wins) turns that off for admins.
ADMIN_OVERRIDE_SETTING = "cron_notify_admin_override"
ADMIN_OVERRIDE_ENV = "HERMES_WEBUI_CRON_NOTIFY_ADMIN_OVERRIDE"

# "Synthwave support is notified when this fails" holds only when the
# installation reports operational telemetry (Appendix D).
OPERATIONAL_TELEMETRY_ENV = "SP_OPERATIONAL_TELEMETRY"

CRON_ADMIN_PERMISSION = "cron:admin"

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_SUCCESS_STATUSES = frozenset({"ok", "success", "completed"})


def _flag_env(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return None
    return str(raw).strip().lower() in _TRUE_VALUES


# -- Policy ------------------------------------------------------------------

def notify_policy(*, import_engine: bool = True):
    """The notify policy module: the engine's first, the WebUI copy second.

    The engine module counts only with the full Appendix A surface. With
    ``import_engine=False`` (the delivery bridge thread, which never imports
    the engine) only an engine module that is already loaded is used. Both
    are the same bytes (tests/test_cron_notify_policy_blob.py), so the
    fallback never decides differently from a current engine.
    """
    module = sys.modules.get(ENGINE_POLICY_MODULE)
    if module is None and import_engine:
        try:
            module = importlib.import_module(ENGINE_POLICY_MODULE)
        except Exception:
            module = None
    if module is not None and all(hasattr(module, name) for name in _POLICY_API):
        return module
    return _fallback_policy


def _resolve(policy, job) -> dict:
    return policy.resolve_notify(job if isinstance(job, dict) else {})


def _legacy_levels(policy, job) -> dict:
    """The levels ``job`` resolves to once its ``notify`` is cleared."""
    rest = {k: v for k, v in (job or {}).items() if k != "notify"} if isinstance(job, dict) else {}
    return policy.resolve_notify(rest)


def notify_for_new_job(category: str | None) -> dict:
    """The job fields a new task gets when its create request sends no
    ``notify``: the plan 3.1 defaults (Monitoring tasks only toast on
    failures) plus the ``toast_notifications`` mirror for older clients."""
    policy = notify_policy()
    notify = policy.default_notify_for_new_job(category=category)
    return {"notify": notify, "toast_notifications": policy.legacy_toast_value(notify)}


# -- Request context ---------------------------------------------------------

def _current_handler():
    """The request handler bound to this thread by the server, or None."""
    try:
        from api.ownership import _CURRENT_REQUEST

        return getattr(_CURRENT_REQUEST, "handler", None)
    except Exception:
        return None


def _request_identity(handler):
    if handler is None:
        return None
    try:
        from api.governance.enforce import _request_identity as identity_for

        return identity_for(handler)
    except Exception:
        return None


def _identity_email(identity) -> str:
    try:
        return str((identity or {}).get("email") or "").strip().lower()
    except Exception:
        return ""


def _normalize_viewer(viewer) -> str | None:
    email = str(viewer or "").strip().lower()
    return email or None


def _identity_is_cron_admin(identity) -> bool:
    """``cron:admin`` by the same helper the cron write routes use
    (routes._cron_admin_allowed). Governance off counts as admin there too."""
    if identity is None:
        return False
    try:
        from api.governance.enforce import identity_has_permission

        return bool(identity_has_permission(identity, CRON_ADMIN_PERMISSION))
    except Exception:
        logger.warning("cron notify: cron admin check failed", exc_info=True)
        return False


def _caller_is_cron_admin() -> bool:
    """Whether the caller of the request on this thread is a cron admin.
    No request bound to the thread means no (fail closed)."""
    return _identity_is_cron_admin(_request_identity(_current_handler()))


def _viewer_is_cron_admin(viewer: str | None) -> bool:
    """Cron admin check for the viewer of a listing. Uses the request on this
    thread when it is that viewer's (so group grants count), otherwise the
    viewer's email alone."""
    email = _normalize_viewer(viewer)
    if email is None:
        return False
    identity = _request_identity(_current_handler())
    if _identity_email(identity) != email:
        identity = {"email": email, "groups": [], "claims_subset": {}, "method": "cron_notify"}
    return _identity_is_cron_admin(identity)


def _report_only_lets_through(reason: str) -> bool:
    """Under governance report_only, audit a refused notify value as
    would_deny and let it through, as the other cron write checks do
    (cron_scope.audit_write_would_deny). Needs the request on this thread."""
    handler = _current_handler()
    if handler is None:
        return False
    try:
        import api.cron_scope as cron_scope

        path = urlparse(str(getattr(handler, "path", "") or "")).path or "/api/crons/update"
        return bool(cron_scope.audit_write_would_deny(
            _request_identity(handler), path=path, reason=reason))
    except Exception:
        logger.warning("cron notify: report_only audit failed", exc_info=True)
        return False


# -- Writes: validate_notify_field -------------------------------------------

_OFF_SET_REFUSAL = "Only a cron admin can turn notifications off."
_OFF_LIFT_REFUSAL = "Only a cron admin can change a notification setting a cron admin turned off."


def validate_notify_field(value, *, is_admin: bool | None = None, job: dict | None = None):
    """Validate the ``notify`` field of a cron create or update.

    Returns the value stored as the job's ``notify`` (a normalized dict with
    both levels, or None to clear it). A ValueError becomes a 400 with its
    message.

    ``off`` is not offered in the UI: only cron admins set it (plan 3.1), and
    only they lift it. ``is_admin`` is the caller's cron admin status as the
    write route decided it; when it is not passed, the request bound to this
    thread decides (no request: not an admin). ``job`` is the stored task on
    an update: a non-admin may then save an ``off`` level back unchanged and
    change the other level, but not set or lift ``off``. Without ``job`` a
    non-admin can not send ``off`` at all. Under governance report_only a
    refusal is audited as would_deny and the value goes through.
    """
    policy = notify_policy()
    notify = policy.normalize_notify(value)
    admin = _caller_is_cron_admin() if is_admin is None else bool(is_admin)
    if admin:
        return notify
    current = _resolve(policy, job) if isinstance(job, dict) else None
    after = notify if notify is not None else _legacy_levels(policy, job)
    refusal = None
    for key in NOTIFY_KEYS:
        new_level = after.get(key)
        old_level = current.get(key) if current is not None else None
        if new_level == "off" and old_level != "off":
            refusal = _OFF_SET_REFUSAL
            break
        if old_level == "off" and new_level != "off":
            refusal = _OFF_LIFT_REFUSAL
            break
    if refusal and not _report_only_lets_through("cron_notify_admin_level"):
        raise ValueError(refusal)
    return notify


# -- Reads: decorate_job and decorate_completion -----------------------------

def _managed_by(policy, job) -> str:
    raw = (job or {}).get("managed_by") if isinstance(job, dict) else None
    if isinstance(raw, str):
        raw = raw.strip().lower()
    try:
        return policy.normalize_managed_by(raw)
    except ValueError:
        return "client"


def operational_telemetry_enabled() -> bool:
    return bool(_flag_env(OPERATIONAL_TELEMETRY_ENV))


def support_notified(job: dict) -> bool:
    """True when Synthwave support hears about this task's failures: it is a
    task Synthwave runs for the client (``managed_by = synthwave``) and the
    installation's operational telemetry is on."""
    return _managed_by(notify_policy(), job) == "synthwave" and operational_telemetry_enabled()


def decorate_job(payload: dict, viewer: str | None = None) -> dict:
    """Add the notify fields to one ``GET /api/crons`` job payload.

    ``notify`` is the resolved pair of levels, ``notify_source`` says whether
    it was set (``explicit``) or derived from ``toast_notifications``
    (``legacy``), ``my_notify`` is the viewer's own in-app level for the job
    (None when they set none), ``managed_by`` is ``synthwave`` or ``client``
    and ``support_notified`` whether support hears about failures.
    """
    policy = notify_policy()
    out = dict(payload or {})
    resolved = _resolve(policy, out)
    out["notify"] = {key: resolved[key] for key in NOTIFY_KEYS}
    out["notify_source"] = resolved["source"]
    out["my_notify"] = viewer_notify_level(viewer, out.get("id"))
    out["managed_by"] = _managed_by(policy, out)
    out["support_notified"] = out["managed_by"] == "synthwave" and operational_telemetry_enabled()
    return out


def _admin_override_enabled() -> bool:
    env = _flag_env(ADMIN_OVERRIDE_ENV)
    if env is not None:
        return env
    try:
        from api.config import load_settings

        return bool(load_settings().get(ADMIN_OVERRIDE_SETTING, False) is True)
    except Exception:
        return False


def _job_in_app_level(policy, job, viewer) -> str:
    level = _resolve(policy, job)["in_app"]
    if level == "off" and _admin_override_enabled() and _viewer_is_cron_admin(viewer):
        # D8 with the override on: job-level off does not silence cron admins.
        return "all"
    return level


def _run_succeeded(completion: dict) -> bool:
    return str((completion or {}).get("status") or "").strip().lower() in _SUCCESS_STATUSES


_SILENT_OUTPUT_CACHE: dict = {}
_SILENT_OUTPUT_CACHE_LOCK = threading.Lock()
_SILENT_OUTPUT_CACHE_MAX = 512


def _cron_output_dir() -> Path | None:
    """The output directory of the cron store being served (the route holds
    cron_profile_context, which points cron.jobs.OUTPUT_DIR at it)."""
    jobs_module = sys.modules.get("cron.jobs")
    output_dir = getattr(jobs_module, "OUTPUT_DIR", None) if jobs_module is not None else None
    if output_dir:
        return Path(output_dir)
    home = os.environ.get("HERMES_HOME")
    return Path(home) / "cron" / "output" if home else None


def _latest_run_output_is_silent(job: dict) -> bool:
    """Whether the job's latest run wrote a silent output ([SILENT], or a
    monitor tick with no change). Cached per store, job and run once the
    run's output file exists."""
    job_id = str((job or {}).get("id") or "")
    run_at = (job or {}).get("last_run_at")
    output_dir = _cron_output_dir()
    if not job_id or not run_at or output_dir is None:
        return False
    key = (str(output_dir), job_id, str(run_at))
    with _SILENT_OUTPUT_CACHE_LOCK:
        if key in _SILENT_OUTPUT_CACHE:
            return _SILENT_OUTPUT_CACHE[key]
    try:
        from api import cron_webui_delivery as delivery

        text = delivery.latest_output_text(output_dir / job_id, delivery.parse_run_at(run_at))
        if text is None:
            return False
        silent = delivery.output_is_silent(text)
    except Exception:
        logger.debug("cron notify: silent check failed for job %s", job_id, exc_info=True)
        return False
    with _SILENT_OUTPUT_CACHE_LOCK:
        if len(_SILENT_OUTPUT_CACHE) >= _SILENT_OUTPUT_CACHE_MAX:
            _SILENT_OUTPUT_CACHE.clear()
        _SILENT_OUTPUT_CACHE[key] = silent
    return silent


def _completion_is_silent(completion: dict, job: dict, success: bool) -> bool:
    if not success:
        return False
    if str((completion or {}).get("delivery_status") or "") == "silent":
        return True
    return _latest_run_output_is_silent(job)


def in_app_flags_for(job: dict, *, success: bool, silent: bool, viewer: str | None = None) -> dict:
    """The effective in-app flags for one run as ``viewer`` sees it: the AND
    of the job level and the viewer's own level (plan 3.1)."""
    policy = notify_policy()
    flags = policy.in_app_flags(_job_in_app_level(policy, job, viewer), success=success, silent=silent)
    own = viewer_notify_level(viewer, (job or {}).get("id"))
    if own is not None:
        flags = policy.combine_flags(flags, policy.in_app_flags(own, success=success, silent=silent))
    return {key: bool(flags.get(key)) for key in ("toast", "badge", "desktop")}


def decorate_completion(completion: dict, job: dict, viewer: str | None = None) -> dict:
    """Add the in-app flags to one ``GET /api/crons/recent`` completion.

    ``toast``, ``badge`` and ``desktop`` follow the table in plan 3.1 for the
    job level and the viewer's own level; ``silent`` marks a run that
    produced nothing to report ([SILENT] or an unchanged monitor), which
    notifies nobody. A run counts as failed unless its status is ok, so a
    successful run whose delivery failed (status error) still notifies as a
    failure. ``toast_notifications`` carries the effective toast for older
    clients.
    """
    out = dict(completion or {})
    success = _run_succeeded(out)
    silent = _completion_is_silent(out, job, success)
    flags = in_app_flags_for(job, success=success, silent=silent, viewer=viewer)
    out.update(flags)
    out["silent"] = silent
    out["toast_notifications"] = flags["toast"]
    return out


# -- Run now -------------------------------------------------------------------

def _accepts_kwarg(func, name: str) -> bool | None:
    """True or False from the callable's signature; None when unreadable."""
    try:
        parameters = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return None
    if name in parameters:
        return True
    return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values())


def manual_run_kwargs(job: dict, actor: str | None = None) -> dict:
    """Extra keyword arguments for ``cron.scheduler.run_job`` on "Run now".

    ``trigger="manual"`` and ``trigger_actor`` (the signed-in email of the
    caller, never a request body value) for engines whose ``run_job`` takes
    them (E1), feature detected with ``inspect.signature`` on the engine the
    route already loaded. Only what the signature shows it takes is passed:
    an engine that does not take them, or cannot be inspected, gets none, so
    the runner keeps its old call. The child filters them again by the
    callee's signature (routes._cron_run_job_kwargs). The WebUI's "Run now"
    sends no per-run prompt, so ``run_prompt`` is never set.
    """
    kwargs = {"trigger": "manual"}
    email = _normalize_viewer(actor)
    if email:
        kwargs["trigger_actor"] = email
    scheduler = sys.modules.get("cron.scheduler")
    run_job = getattr(scheduler, "run_job", None) if scheduler is not None else None
    if not callable(run_job):
        return {}
    return {key: value for key, value in kwargs.items() if _accepts_kwarg(run_job, key) is True}


def delivery_decision(job: dict, *, success: bool, silent: bool, default: bool) -> tuple:
    """Decide whether a manual run delivers its result.

    ``default`` is the decision the WebUI made before notify existed (False
    for a silent run or an empty result). Returns ``(deliver, outcome)``:
    ``outcome`` is ``suppressed_muted`` when the job's delivery level mutes
    the run, ``suppressed_silent`` for a silent run, otherwise None.
    """
    if silent:
        return False, OUTCOME_SILENT
    if not default:
        return False, None
    deliver, outcome = notify_policy().should_deliver(job or {}, success=bool(success))
    if not deliver:
        return False, outcome or OUTCOME_MUTED
    return True, None


def _mark_job_run(mark_job_run, job_id, success, error, delivery_error, engine_outcome) -> bool:
    """Call mark_job_run; True when the engine recorded ``engine_outcome``."""
    if engine_outcome is not None and _accepts_kwarg(mark_job_run, "delivery_outcome") is True:
        try:
            mark_job_run(job_id, success, error, delivery_error=delivery_error,
                         delivery_outcome=engine_outcome)
            return True
        except TypeError:
            logger.warning("cron notify: mark_job_run refused delivery_outcome; recording without it",
                           exc_info=True)
    try:
        mark_job_run(job_id, success, error, delivery_error=delivery_error)
    except TypeError:
        # Older/fake cron.jobs modules may not expose the delivery_error
        # parameter (see the matching note in api/routes.py).
        mark_job_run(job_id, success, error)
    return False


def record_manual_outcome(job_id, success, error, *, delivery_error=None, outcome=None) -> None:
    """Record the result of a manual run on the job.

    Called inside the job's cron store context. ``mark_job_run`` records the
    run as before; an engine whose ``mark_job_run`` takes ``delivery_outcome``
    (E1) also gets a muted or silent outcome. On an engine without it the
    outcome goes into the WebUI delivery bridge ledger against the run's
    ``last_run_at``, so the Tasks panel shows "Muted" (or silent) instead of
    "Delivered", and the bridge does not post a muted run into the
    originating conversation.
    """
    from cron.jobs import mark_job_run

    engine_outcome = _ENGINE_OUTCOMES.get(outcome)
    recorded = _mark_job_run(mark_job_run, job_id, success, error, delivery_error, engine_outcome)
    if engine_outcome is None or recorded:
        return
    try:
        from cron.jobs import get_job

        job = get_job(job_id)
    except Exception:
        job = None
    if not isinstance(job, dict) or not job.get("last_run_at"):
        return
    try:
        from api import cron_webui_delivery as delivery

        delivery.record_run_outcome(job, outcome)
    except Exception:
        logger.warning("cron notify: could not record the %s outcome of job %s", outcome, job_id,
                       exc_info=True)


# -- Per-viewer store ------------------------------------------------------------

VIEWER_STORE_FILENAME = "cron_notify_viewers.json"
MAX_ENTRIES_PER_VIEWER = 1000
MAX_JOB_ID_LENGTH = 200

_STORE_LOCK = threading.RLock()
_STORE_CACHE: dict = {"path": None, "sig": None, "data": None}


class StaleRevisionError(Exception):
    """The viewer's settings changed since the revision the client sent."""

    def __init__(self, current: int):
        super().__init__(f"stale revision (current {current})")
        self.current = int(current)


def _store_path() -> Path:
    from api import config

    return Path(config.STATE_DIR) / VIEWER_STORE_FILENAME


def _empty_store() -> dict:
    return {"version": 1, "viewers": {}}


def _clean_store(raw) -> dict:
    """Keep only well-formed viewers and entries."""
    policy = notify_policy()
    store = _empty_store()
    viewers = raw.get("viewers") if isinstance(raw, dict) else None
    if not isinstance(viewers, dict):
        return store
    for email, record in viewers.items():
        key = _normalize_viewer(email)
        if key is None or not isinstance(record, dict):
            continue
        revision = record.get("revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            revision = 0
        raw_jobs = record.get("jobs") if isinstance(record.get("jobs"), dict) else {}
        jobs = {}
        for job_id, entry in raw_jobs.items():
            level = entry.get("in_app") if isinstance(entry, dict) else None
            if isinstance(job_id, str) and job_id and level in policy.LEVELS_IN_APP and level != "all":
                jobs[job_id] = {"in_app": level, "updated_at": entry.get("updated_at")}
        store["viewers"][key] = {"revision": revision, "jobs": jobs}
    return store


def _move_aside(path: Path) -> None:
    try:
        target = path.with_name(f"{path.name}.corrupt-{int(time.time())}")
        os.replace(path, target)
        logger.warning("cron notify: unreadable viewer store moved to %s; starting fresh", target)
    except OSError:
        logger.warning("cron notify: unreadable viewer store %s; starting fresh", path, exc_info=True)


def _load_store() -> dict:
    """The parsed store, cached while the file is unchanged. A missing file
    is an empty store; an unreadable one is moved aside and starts fresh."""
    path = _store_path()
    with _STORE_LOCK:
        try:
            stat = path.stat()
        except FileNotFoundError:
            _STORE_CACHE.update(path=str(path), sig=None, data=_empty_store())
            return _STORE_CACHE["data"]
        except OSError:
            logger.warning("cron notify: viewer store not readable", exc_info=True)
            return _empty_store()
        sig = (stat.st_mtime_ns, stat.st_size)
        if _STORE_CACHE["path"] == str(path) and _STORE_CACHE["sig"] == sig and _STORE_CACHE["data"] is not None:
            return _STORE_CACHE["data"]
        try:
            data = _clean_store(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            _move_aside(path)
            data = _empty_store()
            sig = None
        _STORE_CACHE.update(path=str(path), sig=sig, data=data)
        return data


def _save_store(data: dict) -> None:
    from api.paths import _atomic_write_text

    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, json.dumps(data, indent=1, sort_keys=True))
    try:
        stat = path.stat()
        sig = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        sig = None
    _STORE_CACHE.update(path=str(path), sig=sig, data=data)


def viewer_notify_settings(viewer: str | None) -> tuple[int, dict]:
    """``(revision, {job_id: in_app level})`` of the viewer's own settings."""
    email = _normalize_viewer(viewer)
    if email is None:
        return 0, {}
    record = _load_store()["viewers"].get(email) or {}
    jobs = {job_id: entry["in_app"] for job_id, entry in (record.get("jobs") or {}).items()}
    return int(record.get("revision") or 0), jobs


def viewer_notify_level(viewer: str | None, job_id) -> str | None:
    """The viewer's own in-app level for ``job_id``, or None."""
    email = _normalize_viewer(viewer)
    if email is None or not job_id:
        return None
    record = _load_store()["viewers"].get(email) or {}
    entry = (record.get("jobs") or {}).get(str(job_id))
    return entry.get("in_app") if isinstance(entry, dict) else None


def set_viewer_notify_level(viewer: str, job_id: str, level: str | None, *, revision: int) -> int:
    """Set (or with None, or ``all``, clear) the viewer's own in-app level
    for one job. ``revision`` must be the viewer's current revision
    (StaleRevisionError otherwise). Returns the new revision."""
    email = _normalize_viewer(viewer)
    if email is None:
        raise ValueError("viewer required")
    if level is not None and level not in notify_policy().LEVELS_IN_APP:
        raise ValueError("in_app must be one of " + ", ".join(notify_policy().LEVELS_IN_APP))
    with _STORE_LOCK:
        store = _load_store()
        data = {"version": 1, "viewers": {k: {"revision": v["revision"], "jobs": dict(v["jobs"])}
                                          for k, v in store["viewers"].items()}}
        record = data["viewers"].setdefault(email, {"revision": 0, "jobs": {}})
        if int(revision) != int(record["revision"]):
            raise StaleRevisionError(record["revision"])
        jobs = record["jobs"]
        if level is None or level == "all":
            jobs.pop(str(job_id), None)
        else:
            jobs.pop(str(job_id), None)
            jobs[str(job_id)] = {"in_app": level, "updated_at": datetime.now(timezone.utc).isoformat()}
            while len(jobs) > MAX_ENTRIES_PER_VIEWER:
                oldest = min(jobs, key=lambda jid: str(jobs[jid].get("updated_at") or ""))
                jobs.pop(oldest)
        # The record stays when its last entry is cleared: its revision keeps
        # counting, so a client holding an older revision still gets a 409.
        record["revision"] = int(record["revision"]) + 1
        _save_store(data)
        return record["revision"]


# -- Visibility of jobs to a viewer ----------------------------------------------

def _cron_store_homes() -> list[tuple[str, Path]]:
    """``(profile name, home)`` of every cron store the Tasks panel reads:
    the active profile first, then the visible profiles (as
    routes._cron_jobs_cross_profile lists them), each home once."""
    import api.profiles as profiles

    homes: list[tuple[str, Path]] = []
    seen: set[str] = set()

    def _add(name, home):
        try:
            key = str(Path(home).expanduser().resolve(strict=False))
        except Exception:
            key = str(home)
        if key in seen:
            return
        seen.add(key)
        homes.append((str(name or "default"), Path(home)))

    active = profiles.get_active_profile_name() or "default"
    _add(active, profiles.get_active_hermes_home())
    try:
        rows = profiles.list_profiles_api(fast=True, include_skill_counts=False)
    except TypeError:
        rows = profiles.list_profiles_api()
    except Exception:
        logger.warning("cron notify: profile listing failed", exc_info=True)
        rows = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name or (row.get("visible") is False and not profiles._profiles_match(name, active)):
            continue
        _add(name, profiles.get_hermes_home_for_profile(name))
    return homes


def visible_job_ids(handler, job_ids) -> set[str]:
    """The ids in ``job_ids`` of jobs the caller may see: their own or shared
    jobs in any store, other jobs by the profile rule (the root store only
    for cron admins), exactly as the Tasks listing scopes rows
    (api/cron_scope.py). Fails closed: an error hides the job."""
    wanted = {str(job_id) for job_id in job_ids or () if job_id}
    if not wanted:
        return set()
    try:
        import api.cron_scope as cron_scope
        from api.cron_webui_delivery import _load_jobs_from_home

        identity = _request_identity(handler)
        decisions: dict[str, bool] = {}
        found: set[str] = set()
        for profile_name, home in _cron_store_homes():
            for row in _load_jobs_from_home(home):
                job_id = str(row.get("id") or "")
                if job_id not in wanted or job_id in found:
                    continue
                if cron_scope.row_owned_by_identity(identity, row) or cron_scope.row_shared_with_identity(identity, row):
                    found.add(job_id)
                    continue
                store_profile = str(row.get("owner_profile") or profile_name or cron_scope.ROOT_PROFILE)
                if store_profile not in decisions:
                    decisions[store_profile] = bool(cron_scope.identity_sees_cron_profile(identity, store_profile))
                if decisions[store_profile]:
                    found.add(job_id)
        return found
    except Exception:
        logger.warning("cron notify: visibility check failed", exc_info=True)
        return set()


# -- /api/crons/notifications ----------------------------------------------------

_POST_FIELDS = frozenset({"job_id", "in_app", "revision"})
_SIGN_IN_REFUSAL = "Sign in to change your own notification settings."
_CONFLICT_MESSAGE = "This setting changed elsewhere. Reload and try again."


def _json(handler, payload, status=200):
    from api.helpers import j

    j(handler, payload, status=status)
    return True


def _viewer_of(handler) -> str | None:
    return _normalize_viewer(_identity_email(_request_identity(handler)))


def handle_notifications_get(handler, parsed) -> bool:
    """``GET /api/crons/notifications``: ``{revision, jobs}``, the caller's
    own in-app levels (``jobs`` maps a job id to ``{"in_app": level}``) for
    the jobs they can still see. A caller without an email has none."""
    viewer = _viewer_of(handler)
    revision, levels = viewer_notify_settings(viewer)
    visible = visible_job_ids(handler, levels) if levels else set()
    jobs = {job_id: {"in_app": level} for job_id, level in sorted(levels.items()) if job_id in visible}
    return _json(handler, {"revision": revision, "jobs": jobs})


def handle_notifications_post(handler, body) -> bool:
    """``POST /api/crons/notifications {job_id, in_app, revision}``: set the
    caller's own in-app level for one job, or clear it with ``in_app: null``
    (``all`` clears too, it lowers nothing). 400 on a malformed body, 403
    without a signed-in email, 404 when the job is not visible to the caller,
    409 when ``revision`` is not the caller's current revision."""
    if not isinstance(body, dict):
        return _json(handler, {"error": "Request body must be an object"}, 400)
    unknown = sorted(str(key) for key in body if key not in _POST_FIELDS)
    if unknown:
        return _json(handler, {"error": f"Field not allowed: {', '.join(unknown)}"}, 400)
    job_id = body.get("job_id")
    if not isinstance(job_id, str) or not job_id.strip() or len(job_id) > MAX_JOB_ID_LENGTH:
        return _json(handler, {"error": "job_id required"}, 400)
    if "in_app" not in body:
        return _json(handler, {"error": "in_app required (null clears it)"}, 400)
    level = body.get("in_app")
    levels = notify_policy().LEVELS_IN_APP
    if level is not None and (not isinstance(level, str) or level not in levels):
        return _json(handler, {"error": "in_app must be one of " + ", ".join(levels) + ", or null"}, 400)
    revision = body.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        return _json(handler, {"error": "revision required"}, 400)
    viewer = _viewer_of(handler)
    if viewer is None:
        return _json(handler, {"error": _SIGN_IN_REFUSAL}, 403)
    if job_id not in visible_job_ids(handler, [job_id]):
        return _json(handler, {"error": "Job not found"}, 404)
    try:
        new_revision = set_viewer_notify_level(viewer, job_id, level, revision=revision)
    except StaleRevisionError as stale:
        return _json(handler, {"error": _CONFLICT_MESSAGE, "reason": "stale_revision",
                               "revision": stale.current}, 409)
    except OSError:
        logger.warning("cron notify: viewer store not writable", exc_info=True)
        return _json(handler, {"error": "Notification settings are unavailable. Please try again."}, 503)
    stored = None if level in (None, "all") else level
    return _json(handler, {"ok": True, "revision": new_revision, "job_id": job_id, "in_app": stored})
