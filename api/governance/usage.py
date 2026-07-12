"""Governance usage counters and caps (hashed subjects, atomic JSON state).

Vendored from the hermes-agent dashboard_governance usage module with the
hermes_constants and utils imports replaced by local helpers, a lock added
for the threaded http.server, and the DashboardGovernanceContext coupling
relaxed to duck typing (the webui does not vendor context.py in v1).

v1 consumers: the governance admin API usage endpoint (read only).
``check_usage_caps`` and ``record_tool_usage`` stay available for future
runtime wiring; ``ctx`` may be a context-like object exposing ``.access``
(and optionally ``.subject``) or an EffectiveAccess directly.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AccessDecision

_FILE_WRITE_TOOLS = {"write_file", "patch"}

# Serialize the read-modify-write of the usage state file across the
# webui's request-handler threads.
_USAGE_LOCK = threading.Lock()


def _hermes_home() -> Path:
    env_home = os.getenv("HERMES_HOME", "").strip()
    if env_home:
        return Path(env_home).expanduser()
    return Path.home() / ".hermes"


def _usage_file() -> Path:
    return _hermes_home() / "dashboard-governance-usage.json"


def _atomic_json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> str:
    return _now().strftime("%Y-%m-%d")


def _month() -> str:
    return _now().strftime("%Y-%m")


def _access_of(ctx: Any) -> Any:
    return getattr(ctx, "access", ctx)


def _subject_key(ctx: Any) -> str:
    access = _access_of(ctx)
    subject = getattr(access, "subject", None) or getattr(ctx, "subject", None)
    email = getattr(subject, "normalized_email", "") or ""
    user_id = getattr(subject, "user_id", "") or ""
    raw = (email or user_id or "anonymous").strip().lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _load_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def _empty_counters() -> dict[str, int]:
    return {
        "tool_calls": 0,
        "file_writes": 0,
        "mcp_calls": 0,
        "background_processes": 0,
    }


def _counter_bucket(state: dict[str, Any], ctx: Any, period: str) -> dict[str, int]:
    if period == "months":
        key = _month()
    else:
        period = "days"
        key = _today()
    subject = _subject_key(ctx)
    periods = state.setdefault(period, {})
    if not isinstance(periods, dict):
        state[period] = periods = {}
    period_bucket = periods.setdefault(key, {})
    if not isinstance(period_bucket, dict):
        periods[key] = period_bucket = {}
    counters = period_bucket.setdefault(subject, {})
    if not isinstance(counters, dict):
        period_bucket[subject] = counters = {}
    for name, value in _empty_counters().items():
        counters.setdefault(name, value)
    return counters


def _cap(caps: dict[str, Any], *names: str) -> int | None:
    for name in names:
        value = caps.get(name)
        if value is None or value == "":
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed >= 0:
            return parsed
    return None


def _usage_counters_for_tool(tool_name: str, args: dict[str, Any] | None = None) -> tuple[str, ...]:
    counters = ["tool_calls"]
    if tool_name in _FILE_WRITE_TOOLS:
        counters.append("file_writes")
    if tool_name.startswith("mcp_"):
        counters.append("mcp_calls")
    if tool_name == "terminal" and isinstance(args, dict) and bool(args.get("background")):
        counters.append("background_processes")
    return tuple(counters)


def read_usage_state() -> dict[str, Any]:
    return _load_state(_usage_file())


def _check_counter_cap(caps: dict[str, Any], counters: dict[str, int], counter: str, prefix: str) -> AccessDecision | None:
    cap = _cap(
        caps,
        f"{prefix}_{counter}",
        f"max_{prefix}_{counter}",
        f"{counter}_{prefix}",
    )
    if cap is not None and int(counters.get(counter, 0)) >= cap:
        return AccessDecision(False, f"{prefix}_{counter}_exceeded")
    return None


def check_usage_caps(ctx: Any | None, tool_name: str, args: dict[str, Any] | None = None) -> AccessDecision:
    if ctx is None or _access_of(ctx).mode != "enforce":
        return AccessDecision(True, "governance_inactive")
    caps = dict(_access_of(ctx).grants.usage_caps or {})
    if not caps:
        return AccessDecision(True, "usage_caps_inactive")

    state = _load_state(_usage_file())
    counter_names = _usage_counters_for_tool(tool_name, args)
    for period, prefix in (("days", "daily"), ("months", "monthly")):
        counters = _counter_bucket(state, ctx, period)
        for counter in counter_names:
            decision = _check_counter_cap(caps, counters, counter, prefix)
            if decision is not None:
                return decision
    return AccessDecision(True, "usage_allowed")


def record_tool_usage(ctx: Any | None, tool_name: str, args: dict[str, Any] | None = None) -> None:
    if ctx is None or _access_of(ctx).mode != "enforce":
        return
    if not dict(_access_of(ctx).grants.usage_caps or {}):
        return
    path = _usage_file()
    with _USAGE_LOCK:
        state = _load_state(path)
        for period in ("days", "months"):
            counters = _counter_bucket(state, ctx, period)
            for counter in _usage_counters_for_tool(tool_name, args):
                counters[counter] = int(counters.get(counter, 0)) + 1
        _atomic_json_write(path, state)
