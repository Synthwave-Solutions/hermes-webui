"""Answer a lazy extra install that policy forbids without starting the engine's worker.

Hermes Agent tools probe their optional SDKs through ``pm.ensure_import(extra)``.
When the extra is absent that call starts a package-manager worker process, and
only the worker reads ``security.allow_lazy_installs``. With the policy off the
worker spends 13 to 20 seconds (process start, install lock, plugin discovery,
stamp computation) before it refuses, and because nothing is installed the same
attempt repeats on the next probe. In this server that happened inside the tool
definition build of every agent construction (measured 12 Nov 2026: the
``fal`` extra behind ``check_image_generation_requirements``).

This guard takes the same decision in process: an extra that is not importable
while lazy installs are disabled is refused at once, with the error the worker
would have raised. Nothing else changes: explicit installs, repairs, plugin
syncs and every case where policy allows the install still reach the engine
untouched. It only ever refuses earlier, it never permits anything.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_MARK = "_webui_fast_lazy_refusal"
_reported: set[str] = set()


def _refusal(extras) -> Exception | None:
    """The InstallError the worker would end with, or None when it must run."""
    from pm import extras as pm_extras
    from pm.install import lazy_installs_allowed

    missing = [extra for extra in extras if not pm_extras.available(extra)]
    if not missing or lazy_installs_allowed():
        return None
    from pm.package import InstallError

    for extra in missing:
        if extra not in _reported:
            _reported.add(extra)
            logger.warning(
                "optional extra %r is not installed and lazy installs are disabled; "
                "refusing without the install worker (run `hermes pm install` to add it)",
                extra,
            )
    return InstallError(
        "venv",
        f"not installed and lazy installs are disabled: {missing}",
        "enable security.allow_lazy_installs or run `hermes pm install`",
    )


def install() -> bool:
    """Wrap ``pm.client.sync_venv`` once. Returns True when the guard is active."""
    try:
        import pm.client as client
    except Exception:
        return False
    with _LOCK:
        original = getattr(client, "sync_venv", None)
        if original is None:
            return False
        if getattr(original, _MARK, False):
            return True

        def sync_venv(extras=None, *args, **kwargs):
            # Only the implicit path: ensure_import calls sync_venv([extra]) and nothing else.
            if extras and not args and not any(kwargs.get(key) for key in ("explicit", "repair", "plugins", "project_root")):
                try:
                    refusal = _refusal(list(extras))
                except Exception:
                    refusal = None  # Unknown engine layout: let the engine decide.
                if refusal is not None:
                    raise refusal
            return original(extras, *args, **kwargs)

        setattr(sync_venv, _MARK, True)
        sync_venv.__wrapped__ = original
        client.sync_venv = sync_venv
        return True
