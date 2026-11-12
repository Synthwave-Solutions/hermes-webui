"""Answer an empty cron completion poll without building every job list.

Every open tab asks ``GET /api/crons/recent?since=<t>`` twice a minute. The
answer is almost always "nothing", but the handler built it the long way: the
engine's full job list with execution lookups, the job file of every other
bot, the delivery ledger and the session lookup (measured 12 Nov 2026 inside
the busy server: median 187 ms, p90 1.4 s, all of it holding the interpreter).

``nothing_new(handler, since)`` reads the same job files the handler reads,
keeps the parsed run times per file for as long as the file is unchanged
(``api.profile_yaml_cache``), and looks only at jobs that ran after ``since``.
When there are none, or none the caller may see, the poll is empty.

It can only ever say "empty" when the handler would. Anything it does not
recognise (an unreadable or unusual job file, an engine layout it does not
know, a failing identity or scope check) returns False and the handler runs
exactly as before. Set ``HERMES_WEBUI_CRON_RECENT_PRECHECK=0`` to switch it off.
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path


def _enabled() -> bool:
    return os.environ.get("HERMES_WEBUI_CRON_RECENT_PRECHECK", "1").strip().lower() not in {"0", "false", "off", "no"}


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _run_times(path):
    """``((timestamp, job), ...)`` for the jobs that ran, or None when the file is not understood.

    The timestamp is parsed exactly like ``_handle_cron_recent`` does. The
    result is shared between callers: copy a job before handing it on.
    """
    try:
        data = _read(path)
    except FileNotFoundError:
        return ()
    except Exception:
        return None
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        return None  # bare list or id-keyed map: the engine repairs those itself
    rows = []
    for job in jobs:
        if not isinstance(job, dict):
            return None
        last_run = job.get("last_run_at")
        if not last_run:
            continue
        if isinstance(last_run, str):
            try:
                ts = datetime.datetime.fromisoformat(last_run.replace("Z", "+00:00")).timestamp()
            except (ValueError, TypeError):
                continue
        else:
            try:
                ts = float(last_run)
            except (ValueError, TypeError):
                return None
        rows.append((ts, job))
    return tuple(rows)


def _load(path):
    from api import profile_yaml_cache

    return profile_yaml_cache.load(os.fspath(path), _run_times)


def _active_jobs_file():
    """The job file the engine's ``list_jobs`` reads in this request context."""
    from cron.jobs import _current_cron_store

    return _current_cron_store().jobs_file


def _normalize(job):
    from cron.jobs import _normalize_job_record

    return _normalize_job_record(dict(job))


def nothing_new(handler, since) -> bool:
    """True only when ``_handle_cron_recent`` would answer with no completions."""
    try:
        if not _enabled() or not since > 0:
            return False
        from api import cron_bots
        from api.cron_scope import _identity_for, scope_cron_completions
        from api.profiles import get_active_hermes_home

        active = _load(_active_jobs_file())
        if active is None:
            return False
        own = [job for ts, job in active if ts > since]
        active_key = cron_bots._home_key(get_active_hermes_home())
        others = []
        for owner, home in cron_bots.store_homes():
            if cron_bots._home_key(home) == active_key:
                continue
            rows = _load(Path(home) / "cron" / "jobs.json")
            if rows is None:
                return False
            others.extend(dict(job, owner_profile=owner) for ts, job in rows if ts > since)
        if not own and not others:
            return True
        # Something ran: empty only when none of it is the caller's to see.
        identity = _identity_for(handler)
        if own and scope_cron_completions(identity, [_normalize(job) for job in own]):
            return False
        if others and scope_cron_completions(identity, others):
            return False
        return True
    except Exception:
        return False
