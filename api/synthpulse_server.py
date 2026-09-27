"""SynthPulse additions to the HTTP entry point, kept out of server.py.

server.py stays the thin upstream dispatcher (tests/test_sprint10.py keeps it
under 750 lines, and upstream alone sits at 749). What SynthPulse adds around
each request and at start-up lives here: the ownership context for the
request thread, the socket timeout override, and the background threads only
this fork runs. server.py imports these under its old private names, so the
call sites and the tests that patch ``server._set_owner_context`` or
``server.enforce_request`` behave exactly as before.
"""

from __future__ import annotations

import logging
import os

from api.governance.enforce import enforce_request  # noqa: F401  (used by server.py)

logger = logging.getLogger(__name__)


def env_int(name: str, default: int, minimum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def set_owner_context(handler) -> None:
    """Bind the current request to this thread for ownership stamping."""
    try:
        from api.ownership import set_request_context
        set_request_context(handler)
    except Exception:
        pass


def clear_owner_context() -> None:
    try:
        from api.ownership import clear_request_context
        clear_request_context()
    except Exception:
        pass


def start_background_threads() -> None:
    """Start the SynthPulse-only threads: cache pre-warm and cron delivery."""
    try:
        from api.prewarm import start_prewarm_thread
        if start_prewarm_thread():
            print('[ok] cache pre-warm thread started (claude-code transcripts + model catalog)', flush=True)
    except Exception as e:
        print(f'[!!] WARNING: cache pre-warm failed to start: {e}', flush=True)

    try:
        from api.cron_webui_delivery import start_cron_delivery_thread
        if start_cron_delivery_thread():
            print('[ok] cron WebUI delivery bridge started', flush=True)
    except Exception as e:
        print(f'[!!] WARNING: cron WebUI delivery bridge failed to start: {e}', flush=True)


def stop_background_threads() -> None:
    try:
        from api.cron_webui_delivery import stop_cron_delivery_thread
        stop_cron_delivery_thread()
    except Exception:
        logger.debug("Failed to stop cron WebUI delivery bridge during shutdown", exc_info=True)
