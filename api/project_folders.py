"""Folders inside a project (step 2 of merging Projects and Spaces).

Behind a flag (HERMES_WEBUI_PROJECT_FOLDERS=1 or settings
``project_folders_enabled: true``); with the flag off every route answers 404
and nothing changes. No migration happens here: a project only gets a
``folders`` list when someone adds a folder through the API.

Rules (no one gains access through this feature):
* Seeing a project's folders requires seeing the project (same rule as the
  Projects hub) AND access to each folder under the existing space ACL; a
  folder the caller cannot open is left out, not shown as locked.
* Adding a folder requires managing the project (owner or admin), files:write,
  and that the caller can already open the folder: a registered space visible
  to them, or any existing directory for admins.
* "Mijn werk" is virtual: the caller's own chats without a project plus the
  spaces they can see. It is never written to projects.json.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

MAX_FOLDERS = 20
ROLES = {"project", "linked"}


def enabled(settings: dict | None = None, environ=None, state_dir=None) -> bool:
    env = os.environ if environ is None else environ
    if str(env.get("HERMES_WEBUI_PROJECT_FOLDERS", "")).strip().lower() in {"1", "true", "yes", "on"}:
        return True
    if (settings or {}).get("project_folders_enabled") is True:
        return True
    return merged(state_dir)


MARKER = "projects_merge_state.json"


def merged(state_dir=None) -> bool:
    """True once the Projects + Spaces migration has run on this state dir."""
    try:
        if state_dir is None:
            from api.config import STATE_DIR as state_dir  # noqa: N811
        return (Path(state_dir) / MARKER).is_file()
    except Exception:
        return False


def classic_spaces(settings: dict | None = None, environ=None) -> bool:
    """Keep the old Spaces menu item visible (one release after the merge)."""
    env = os.environ if environ is None else environ
    if str(env.get("HERMES_WEBUI_CLASSIC_SPACES", "")).strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return (settings or {}).get("classic_spaces") is True


def _norm(value) -> str:
    return str(value or "").strip().lower()


def can_manage(project: dict, email: str, is_admin: bool) -> bool:
    return bool(is_admin or (email and email == _norm(project.get("owner_email"))))


def _real(path: str) -> str:
    return os.path.realpath(os.path.expanduser(str(path)))


def folder_entries(project: dict) -> list[dict]:
    """The project's folders, its own team folder first (role "project")."""
    out, seen = [], set()
    own = project.get("workspace") if project.get("collaboration") else None
    if own:
        out.append({"path": str(own), "name": "", "role": "project"})
        seen.add(_real(own))
    for item in project.get("folders") or []:
        if not isinstance(item, dict) or not item.get("path"):
            continue
        real = _real(item["path"])
        if real in seen:
            continue
        seen.add(real)
        role = item.get("role") if item.get("role") in ROLES else "linked"
        out.append({"path": str(item["path"]), "name": str(item.get("name") or Path(item["path"]).name)[:80],
                    "role": role, "added_by": item.get("added_by"), "added_at": item.get("added_at")})
    return out


def visible_folders(project: dict, can_open) -> list[dict]:
    """Folders of a visible project that the caller may open (``can_open(path)``)."""
    return [f for f in folder_entries(project) if can_open(f["path"])]


def add_folder(projects: list, project_id: str, path: str, name: str, *, email: str, is_admin: bool,
               may_write_files: bool, visible_space_paths: set, now: float | None = None) -> dict:
    """Validate and add one folder in place. Raises ValueError / PermissionError."""
    project = next((p for p in projects if isinstance(p, dict) and p.get("project_id") == project_id
                    and not p.get("deleted")), None)
    if project is None:
        raise LookupError("Project not found")
    if not can_manage(project, email, is_admin):
        raise PermissionError("Only the project owner or an admin can add folders")
    if not may_write_files:
        raise PermissionError("files:write is required")
    raw = str(path or "").strip()
    if not raw or "\x00" in raw:
        raise ValueError("A folder is required")
    real = _real(raw)
    if not os.path.isdir(real):
        raise ValueError("Folder does not exist")
    registered = {_real(p) for p in visible_space_paths}
    if not is_admin and real not in registered:
        raise PermissionError("Pick one of your spaces; only admins can link other folders")
    folders = list(project.get("folders") or [])
    if any(_real(f.get("path", "")) == real for f in folders if isinstance(f, dict)):
        return project
    own = project.get("workspace") if project.get("collaboration") else None
    if own and _real(own) == real:
        return project
    if len(folders) >= MAX_FOLDERS:
        raise ValueError(f"A project can have at most {MAX_FOLDERS} folders")
    folders.append({"path": raw, "name": (str(name or "").strip() or Path(real).name)[:80], "role": "linked",
                    "added_by": email, "added_at": float(now if now is not None else time.time())})
    project["folders"] = folders
    return project


def remove_folder(projects: list, project_id: str, path: str, *, email: str, is_admin: bool) -> dict:
    project = next((p for p in projects if isinstance(p, dict) and p.get("project_id") == project_id
                    and not p.get("deleted")), None)
    if project is None:
        raise LookupError("Project not found")
    if not can_manage(project, email, is_admin):
        raise PermissionError("Only the project owner or an admin can remove folders")
    real = _real(path)
    project["folders"] = [f for f in project.get("folders") or []
                          if isinstance(f, dict) and _real(f.get("path", "")) != real]
    return project


def my_work(sessions: list, email: str, spaces: list, limit: int = 50) -> dict:
    """Virtual "Mijn werk" project: own chats without a project + visible spaces."""
    who = _norm(email)
    own = [s for s in sessions if isinstance(s, dict) and not s.get("archived")
           and not s.get("project_id") and not s.get("project_shared")
           and (not who or _norm(s.get("owner_email")) == who)]
    own.sort(key=lambda s: float(s.get("last_message_at") or s.get("updated_at") or 0), reverse=True)
    return {
        "project": {"project_id": "my-work", "name": "Mijn werk", "virtual": True, "private": True},
        "conversations": [{"session_id": s.get("session_id"), "title": s.get("title") or "",
                           "last_activity_at": s.get("last_message_at") or s.get("updated_at")}
                          for s in own[:limit]],
        "conversation_count": len(own),
        "folders": [{"path": w.get("path"), "name": w.get("name") or Path(str(w.get("path"))).name, "role": "space"}
                    for w in spaces if isinstance(w, dict) and w.get("path")],
    }
