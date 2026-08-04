"""Fire-and-forget bridge to the per-user Hermes profile sync script.

The webui never imports the hermes-agent codebase (vendoring boundary);
instead it spawns ~/.hermes/scripts/governance_profile_sync.py in a
background thread whenever the governance policy changes or a governed
user logs in. The script is idempotent and holds an exclusive flock, so
overlapping triggers serialize instead of racing.

Provisioning per user: profile dir + granted skills + mcp_servers subset +
governance system prompt in SOUL.md + creds-by-absence .env. Bootstrap
admins get wildcard profiles; michael@ (the default profile owner) is
skipped by the script itself.
"""
from __future__ import annotations

import datetime
import logging
import os
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger("webui.governance")

SYNC_SCRIPT = Path.home() / ".hermes" / "scripts" / "governance_profile_sync.py"
SYNC_LOG = Path.home() / ".hermes" / "logs" / "governance-profile-sync.log"
# The script imports hermes_cli; the agent venv always has its deps.
_AGENT_PYTHON = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"
_TIMEOUT_S = 300


def _python() -> str:
    return str(_AGENT_PYTHON) if _AGENT_PYTHON.exists() else "python3"


def _spawn(cmd: list[str], reason: str, email: str | None) -> None:
    """Run the sync subprocess, appending output to the sync log."""
    try:
        SYNC_LOG.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with open(SYNC_LOG, "a", encoding="utf-8") as log:
            log.write(f"--- {stamp} trigger reason={reason} target={email or 'ALL'}\n")
            log.flush()
            subprocess.run(
                cmd, stdout=log, stderr=subprocess.STDOUT, timeout=_TIMEOUT_S,
            )
    except Exception:
        logger.exception("governance profile sync failed (reason=%s)", reason)


def trigger_profile_sync(email: str | None = None, *, reason: str = "") -> bool:
    """Kick a background profile sync; never blocks or raises.

    email=None syncs every governed user (role/group edits fan out);
    a specific email limits the run to that user's profile.
    """
    # Test guard: the pytest suite exercises the mutation handlers against
    # the REAL home policy; never let it spawn real provisioning runs.
    if os.environ.get("HERMES_WEBUI_DISABLE_PROFILE_SYNC"):
        return False
    if not SYNC_SCRIPT.exists():
        return False
    cmd = [_python(), str(SYNC_SCRIPT), "--apply"]
    if email:
        cmd += ["--user", email]
    threading.Thread(
        target=_spawn, args=(cmd, reason, email),
        daemon=True, name="gov-profile-sync",
    ).start()
    return True
