"""Fail-closed guard for in-process Hermes Agent source revisions.

Hermes WebUI currently imports ``run_agent.AIAgent`` into its long-lived server
process. If the Agent checkout changes while that process is alive, Python may
combine already-cached modules with newly-read source. Refuse to reuse that
mixed runtime and require a clean WebUI restart instead.
"""

from __future__ import annotations

from pathlib import Path
import sys
import subprocess
import threading
import re

# Retain the discovered path as a diagnostic/test-visible compatibility value;
# runtime identity is deliberately captured from the loaded module below.
from api.config import _AGENT_DIR  # noqa: F401

_RESTART_MESSAGE = (
    "Hermes Agent was updated while Hermes WebUI was running. "
    "Restart Hermes WebUI before retrying this action."
)

# Cache only the verified source identity, never the revision. Every admission
# reads HEAD again, without spawning git on the latency-sensitive chat path.
_TRACKED_ROOTS: dict[tuple[Path, Path], Path] = {}


def _head_revision(root: Path) -> str | None:
    try:
        git_dir = root / ".git"
        if git_dir.is_file():
            pointer = git_dir.read_text().strip()
            if not pointer.startswith("gitdir: "):
                return None
            git_dir = (root / pointer[8:]).resolve()
        common = git_dir
        if (git_dir / "commondir").exists():
            common = (git_dir / (git_dir / "commondir").read_text().strip()).resolve()
        head = (git_dir / "HEAD").read_text().strip()
        if head.startswith("ref: "):
            ref = head[5:]
            if not ref.startswith("refs/") or ".." in Path(ref).parts:
                return None
            for directory in (git_dir, common):
                if (directory / ref).is_file():
                    head = (directory / ref).read_text().strip()
                    break
            else:
                head = next((line.split()[0] for line in (common / "packed-refs").read_text().splitlines()
                             if len(line.split()) == 2 and line.split()[1] == ref), "")
        return head if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", head) else None
    except (OSError, ValueError):
        return None


def _read_agent_revision(
    agent_dir: Path | None,
    *,
    module_path: Path | None = None,
) -> str | None:
    """Return the loaded Agent checkout HEAD, or ``None`` if it is not tracked."""
    if agent_dir is None:
        return None

    if module_path is None:
        module = sys.modules.get("run_agent")
        module_file = getattr(module, "__file__", None)
        if not module_file:
            return None
        try:
            module_path = Path(module_file).resolve()
        except (OSError, RuntimeError, TypeError):
            return None

    identity = (agent_dir, module_path)
    root = _TRACKED_ROOTS.get(identity)
    if root is not None:
        return _head_revision(root) if module_path.is_file() else None

    try:
        worktree_result = subprocess.run(
            ["git", "-C", str(agent_dir), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if worktree_result.returncode != 0:
            return None
        worktree = Path(worktree_result.stdout.strip()).resolve()
        relative_module = module_path.relative_to(worktree).as_posix()
        tracked_result = subprocess.run(
            [
                "git",
                "--literal-pathspecs",
                "-C",
                str(worktree),
                "ls-files",
                "--error-unmatch",
                "--",
                relative_module,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if tracked_result.returncode != 0:
            return None
        revision_result = subprocess.run(
            ["git", "-C", str(worktree), "rev-parse", "--verify", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError):
        return None

    revision = revision_result.stdout.strip()
    if revision_result.returncode == 0 and revision:
        _TRACKED_ROOTS[identity] = worktree
        return revision
    return None


_AGENT_SOURCE_DIR: Path | None = None
_AGENT_MODULE_PATH: Path | None = None
_AGENT_REVISION: str | None = None
_AIAgent = None
_RUNTIME_LOCK = threading.Lock()


class AgentRuntimeChangedError(RuntimeError):
    """Raised when the loaded Agent runtime no longer matches its source tree."""


def _loaded_agent_source_identity() -> tuple[Path, Path] | None:
    """Return the source directory and file that supplied ``run_agent``."""
    module = sys.modules.get("run_agent")
    module_file = getattr(module, "__file__", None)
    if not module_file:
        return None
    try:
        module_path = Path(module_file).resolve()
        return module_path.parent, module_path
    except (OSError, RuntimeError, TypeError):
        return None


def _capture_loaded_agent_revision() -> None:
    """Bind the guard to the checkout that supplied the loaded Agent module."""
    global _AGENT_SOURCE_DIR, _AGENT_MODULE_PATH, _AGENT_REVISION

    if _AGENT_REVISION is not None:
        ensure_agent_runtime_current()
        return

    identity = _loaded_agent_source_identity()
    if identity is None:
        return
    source_dir, module_path = identity
    current_revision = _read_agent_revision(source_dir, module_path=module_path)
    _AGENT_SOURCE_DIR = source_dir
    _AGENT_MODULE_PATH = module_path
    _AGENT_REVISION = current_revision


def ensure_agent_runtime_current() -> None:
    """Reject a known Git checkout change instead of mixing Python modules."""
    if _AGENT_REVISION is None:
        return
    if (
        _read_agent_revision(_AGENT_SOURCE_DIR, module_path=_AGENT_MODULE_PATH)
        != _AGENT_REVISION
    ):
        raise AgentRuntimeChangedError(_RESTART_MESSAGE)


def require_ai_agent_class():
    """Import ``AIAgent`` after proving the loaded source revision is current."""
    ensure_agent_runtime_current()
    from run_agent import AIAgent  # noqa: PLC0415

    _capture_loaded_agent_revision()
    return AIAgent


def get_ai_agent_class():
    """Return ``AIAgent`` while preserving the existing lazy-import retry."""
    global _AIAgent, _AGENT_REVISION

    with _RUNTIME_LOCK:
        ensure_agent_runtime_current()
        if _AIAgent is None:
            try:
                agent_class = require_ai_agent_class()
            except ImportError:
                return None
            _AIAgent = agent_class
        return _AIAgent
