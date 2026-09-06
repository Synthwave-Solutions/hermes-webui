"""Background cache pre-warm at server start.

Sidebar metadata has a disposable persistent index; its first build still
parses source transcripts. Model discovery is independent and may use network
providers. Warming either must not delay starting the other.

Separate workers start both immediately at startup so the first real
``/api/sessions`` and ``/api/models`` hit warm caches. It is best-effort and
gated the same way as the request paths: transcript warming is skipped when
the "show Claude Code sessions" setting is off. Disable entirely with
``HERMES_WEBUI_PREWARM=0`` (e.g. memory-constrained boxes where the sidebar
sources are disabled anyway).
"""
from __future__ import annotations

import os
import threading
import time

def _prewarm_enabled() -> bool:
    return (os.environ.get("HERMES_WEBUI_PREWARM", "1") or "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


def _run() -> None:
    started = time.time()
    # 1. Claude Code transcript parse cache (dominates cold /api/sessions).
    try:
        from api.config import load_settings

        settings = load_settings() or {}
        if bool(settings.get("show_claude_code_sessions")):
            from api import models

            t = time.time()
            sessions = models.get_claude_code_sessions()
            print(f"[prewarm] claude-code transcript cache warm ({len(sessions or [])} sessions, {time.time()-t:.1f}s)", flush=True)
        else:
            print("[prewarm] claude-code sessions disabled in settings; skipped", flush=True)
    except Exception as e:
        print(f"[prewarm] claude-code warm failed: {e!r}", flush=True)


    print(f"[prewarm] done in {time.time()-started:.1f}s", flush=True)


def _warm_model_catalog() -> None:
    # 2. Provider/model catalog (cold rebuild is 5-17s, warm ~60ms).
    try:
        from api.config import get_available_models

        # Default (prefer_cache=False) on purpose: this IS the live rebuild,
        # off the request path. prefer_cache=True would never build anything
        # on a cold start and the first human request would still pay it.
        t = time.time()
        payload = get_available_models()
        groups = (payload or {}).get("groups") if isinstance(payload, dict) else None
        n = sum(len(g.get("models") or []) for g in groups) if isinstance(groups, list) else 0
        print(f"[prewarm] model catalog warm ({n} models, {time.time()-t:.1f}s)", flush=True)
    except Exception as e:
        print(f"[prewarm] model catalog warm failed: {e!r}", flush=True)


def start_prewarm_thread() -> bool:
    """Start the pre-warm thread; returns True when started."""
    if not _prewarm_enabled():
        return False
    # Network discovery and local transcript projection are independent.
    threading.Thread(target=_warm_model_catalog, name="webui-prewarm-models", daemon=True).start()
    t = threading.Thread(target=_run, name="webui-prewarm", daemon=True)
    t.start()
    return True
