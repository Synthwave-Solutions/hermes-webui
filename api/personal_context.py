"""Authenticated personal context, independent of selected bot and admin role.

No legacy bot files are imported. Shared project instructions remain a separate,
explicitly authorized source. Actor paths are server-generated, never client input.
"""
import hashlib
import os
from pathlib import Path
import tempfile

_FILES = {"memory": "MEMORY.md", "user": "USER.md", "soul": "SOUL.md",
          "project_context": "PROJECT.md"}
_MAX_BYTES = 128 * 1024


def actor_email(identity):
    email = str((identity or {}).get("email") or "").strip().lower()
    if (identity or {}).get("method") == "auth_disabled" and not email:
        return "local@localhost"
    if not email or "@" not in email or any(c.isspace() for c in email):
        raise PermissionError("Sign in with a personal account to access personal context")
    return email


def _safe(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise PermissionError("Personal context cannot use symlinks")
    return path


def home(identity):
    from api.config import STATE_DIR
    key = hashlib.sha256(actor_email(identity).encode()).hexdigest()
    return _safe(Path(STATE_DIR) / "personal_context" / key)


def session_for(identity, sid):
    if not sid:
        return None
    from api.models import get_session
    from api.group_chat import require_turn_membership
    session = get_session(sid)
    # Unlike administrative transcript visibility, private context does not
    # acquire another person's identity when an admin selects their session.
    require_turn_membership(session, identity)
    return session


def paths(identity, session=None):
    root = home(identity)
    project_key = str(getattr(session, "project_id", "") or "")
    if not project_key and session is not None:
        project_key = "workspace:" + str(getattr(session, "workspace", "") or "")
    project_root = root
    if project_key:
        project_root = root / "projects" / hashlib.sha256(project_key.encode()).hexdigest()
    return {key: _safe((project_root if key == "project_context" else root / "memories"
                       if key in ("memory", "user") else root) / name)
            for key, name in _FILES.items()}


def read_file(path):
    _safe(path)
    if not path.exists():
        return ""
    if path.stat().st_size > _MAX_BYTES:
        raise ValueError("Personal context exceeds 128 KiB")
    return path.read_text(encoding="utf-8", errors="replace")


def read(identity, session=None):
    return {key: read_file(path) for key, path in paths(identity, session).items()}


def write(identity, section, content, session=None):
    if section not in _FILES or not isinstance(content, str):
        raise ValueError("Invalid personal context section or content")
    if len(content.encode()) > _MAX_BYTES:
        raise ValueError("Personal context exceeds 128 KiB")
    target = paths(identity, session)[section]
    root = ensure_home(identity)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    for directory in (target.parent, *target.parent.parents):
        if not directory.is_relative_to(root):
            break
        _safe(directory).chmod(0o700)
    _safe(target)
    fd, temp = tempfile.mkstemp(prefix=".context-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        _safe(target)
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return target


def prompt_overlay(identity, session):
    values = read(identity, session)
    return "\n\n".join(
        title + "\n" + values[key]
        for key, title in (("soul", "Personal preferences of the authenticated user"),
                           ("project_context", "Private notes for this selected project"))
        if values[key].strip()
    )


def shared_project_context(identity, session):
    empty = {"content": "", "path": "", "name": "", "scope": ""}
    if session is None or not getattr(session, "project_shared", False):
        return empty
    from api.project_collaboration import runtime_file_scope
    workspace, allowed = runtime_file_scope(session, identity, getattr(session, "profile", None))
    if not workspace or not allowed:
        return empty
    from api.routes import _project_context_candidates, _strip_project_context_frontmatter
    root = Path(workspace)
    for candidate in _project_context_candidates(root):
        if not candidate.resolve().is_relative_to(root.resolve()) or not allowed(str(candidate)):
            continue
        if candidate.is_file() and not candidate.is_symlink():
            return {"content": _strip_project_context_frontmatter(read_file(candidate)),
                    "path": str(candidate), "name": candidate.name, "scope": "shared_project"}
    return empty


def shared_conversation(session):
    if getattr(session, "project_shared", False):
        return True
    owner = str(getattr(session, "owner_email", "") or "").strip().lower()
    return any(str(person).strip().lower() != owner
               for person in (getattr(session, "participants", None) or []))


def ensure_home(identity):
    root = home(identity)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    _safe(root.parent).chmod(0o700)
    _safe(root).chmod(0o700)
    return root


def ensure_actor_path(identity, path, session=None):
    """Additional file-API privacy guard; this never grants filesystem access."""
    from api.config import STATE_DIR
    target = Path(path).resolve()
    private_root = (Path(STATE_DIR) / "personal_context").resolve()
    if target == private_root or private_root.is_relative_to(target):
        raise PermissionError("File access would include private personal context")
    if target.is_relative_to(private_root):
        if shared_conversation(session) or not target.is_relative_to(home(identity).resolve()):
            raise PermissionError("Personal context is private to its authenticated owner")
