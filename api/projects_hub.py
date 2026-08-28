"""Read-only aggregation behind the Projects hub panel (ticket 12).

Ticket 12 asks for "a project's context in one place" and states plainly that
this is a strategic long-term goal and NOT an immediate replacement for the
places a team already keeps project material. So this module aggregates only
what this system actually holds today, it labels every item with where it came
from, and where a source is simply not connected it says so by name instead of
rendering a convincing zero.

Three rules hold everywhere in here:

* Read-only. Nothing in this module writes to disk, and it never calls a
  helper that does. ``ensure_cron_project`` / ``ensure_webhook_project`` look
  like read helpers but back-tag and persist legacy rows on the way out
  (api/models.py), so system projects are identified by their reserved NAMES
  instead (the same read-only rule ``_profile_has_user_projects`` uses).
* Deny by default, per section. The hub route itself rides on ``sessions:read``
  (the existing RouteRule("/api/projects", ...) prefix rule), which is WIDER
  than the permission protecting some of the data it aggregates. Every section
  therefore names the permission that guards the same data on its own route,
  and a section the caller may not have is OMITTED from the payload entirely:
  never sent-then-hidden, and never a count that betrays what is there.
* No network I/O. Integration status is derived from locally readable state
  only. api/integrations.py (Nango) would answer richer questions but every
  one of its calls goes over the wire, which would turn opening a panel into a
  timeout.

Failure semantics mirror api/cron_scope.py: the caller translates ValueError to
400 and PermissionError to 403, and one unreadable source degrades to an
``empty_reason`` rather than taking the whole hub down.
"""
from __future__ import annotations

import logging

from api.models import CRON_PROJECT_NAME, WEBHOOK_PROJECT_NAME
from api.profiles import _profiles_match

logger = logging.getLogger(__name__)

# Section -> the permission that already protects the same data on its own
# route. The authority is api/governance/catalog.py, not a new vocabulary:
# workspaces/files ride on /api/workspaces + /api/list (files:read), jobs on
# /api/crons (cron:read), status on /api/project-os (analytics:read),
# integrations on /api/mcp (mcp:read), the notes drawer on /api/notes
# (files:read), and the board link on /api/kanban (sessions:read).
#
# "delivery" is deliberately the same permission as the hub route, so it is
# always present for anyone who can reach the hub at all. It stays a LINK with
# a "shared board" label and never renders task rows: api/kanban_bridge.py has
# no per-user ownership whatsoever, so listing tasks here would hand every
# caller other people's work.
SECTION_PERMISSIONS = {
    "workspaces": "files:read",
    "files": "files:read",
    "jobs": "cron:read",
    "status": "analytics:read",
    "integrations": "mcp:read",
    "notes_drawer": "files:read",
    "delivery": "sessions:read",
}

# A monorepo root would otherwise make the panel slow and the payload huge.
MAX_FILE_ROOTS = 5
MAX_FILE_ENTRIES = 25
MAX_CONVERSATIONS = 25
MAX_JOBS = 25

# The two system projects api/models.py mints on demand. Both are created
# WITHOUT an owner_email, so a scoped (non-admin) caller never sees them at
# all; the label matters for admins, who do.
SYSTEM_PROJECT_NAMES = frozenset({CRON_PROJECT_NAME, WEBHOOK_PROJECT_NAME})


# ── Project visibility ──────────────────────────────────────────────────────

def visible_projects_by_owner(projects, owner_scope) -> list:
    """The per-user ownership filter, lifted from the /api/projects branch.

    Unowned legacy projects are admin-only. Kept separate from the profile
    filter on purpose: /api/projects applies ownership FIRST and then derives
    ``other_profile_count`` from the difference, so folding the two together
    would zero that counter and change the ?all_profiles=1 response.
    """
    if owner_scope == "all":
        return list(projects or [])
    return [
        p for p in (projects or [])
        if isinstance(p, dict)
        and str(p.get("owner_email") or "").strip().lower()
        and str(p.get("owner_email") or "").strip().lower() == owner_scope
    ]


def visible_projects(projects, owner_scope, active_profile) -> list:
    """Projects this caller may see in this profile: ownership, then profile."""
    return [
        p for p in visible_projects_by_owner(projects, owner_scope)
        if isinstance(p, dict) and _profiles_match(p.get("profile"), active_profile)
    ]


def is_system_project(project) -> bool:
    """Whether a row is one of the projects the system mints for itself."""
    return str((project or {}).get("name") or "") in SYSTEM_PROJECT_NAMES


def visible_sessions(session_rows, owner_scope, active_profile) -> list:
    """Session index rows this caller may see, same rule as /api/sessions."""
    out = []
    for row in session_rows or []:
        if not isinstance(row, dict):
            continue
        if owner_scope != "all":
            row_owner = str(row.get("owner_email") or "").strip().lower()
            if not row_owner or row_owner != owner_scope:
                continue
        if not _profiles_match(row.get("profile"), active_profile):
            continue
        out.append(row)
    return out


def _activity_at(row) -> float:
    for field in ("last_message_at", "updated_at", "created_at"):
        try:
            value = float(row.get(field) or 0)
        except (TypeError, ValueError):
            continue
        if value:
            return value
    return 0.0


def project_rollups(projects, session_rows, owner_scope, active_profile) -> list:
    """One summary row per visible project, counting only visible sessions.

    A project with nothing in it reports ``conversation_count`` 0 AND an
    ``empty_reason``: a bare zero reads as "this project is empty" when the
    truth may be "everything in it belongs to someone else".
    """
    rows = visible_projects(projects, owner_scope, active_profile)
    seen = visible_sessions(session_rows, owner_scope, active_profile)
    by_project: dict[str, list] = {}
    for row in seen:
        pid = str(row.get("project_id") or "").strip()
        if pid:
            by_project.setdefault(pid, []).append(row)

    out = []
    for project in rows:
        pid = str(project.get("project_id") or "")
        mine = by_project.get(pid, [])
        workspaces = {
            str(s.get("workspace") or "").strip()
            for s in mine if str(s.get("workspace") or "").strip()
        }
        summary = {
            "project_id": pid,
            "name": str(project.get("name") or ""),
            "color": str(project.get("color") or ""),
            "system": is_system_project(project),
            "source": "project_record",
            "conversation_count": len(mine),
            # Count only. The paths themselves are workspace data, protected by
            # files:read on /api/workspaces, and this list endpoint carries no
            # such gate; the detail endpoint emits workspace NAMES instead.
            "workspace_count": len(workspaces),
            "last_activity_at": max((_activity_at(s) for s in mine), default=0.0),
        }
        if not mine:
            summary["empty_reason"] = (
                "No conversation you can see is filed under this project yet."
            )
        out.append(summary)
    return out


# ── Per-caller section gating ───────────────────────────────────────────────

def caller_capabilities(identity, permission_check=None) -> dict:
    """Which aggregated sections this caller is entitled to.

    ``permission_check`` defaults to the governance body-sink check, which
    mirrors the route hook without one: it fails open when governance is off or
    the caller is the bootstrap admin, and closed otherwise.
    """
    if permission_check is None:
        from api.governance.enforce import identity_has_permission

        permission_check = identity_has_permission
    allowed = {}
    for section, permission in SECTION_PERMISSIONS.items():
        try:
            allowed[section] = bool(permission_check(identity, permission))
        except Exception:
            logger.debug("capability check failed for %s", section, exc_info=True)
            allowed[section] = False
    return allowed


# ── Detail sections ─────────────────────────────────────────────────────────

def _conversation_items(sessions) -> list:
    items = []
    for row in sessions[:MAX_CONVERSATIONS]:
        items.append({
            "session_id": str(row.get("session_id") or ""),
            "title": str(row.get("title") or ""),
            "last_activity_at": _activity_at(row),
            "source": "conversations",
        })
    return items


def _section(items, source, empty_reason, *, truncated=False) -> dict:
    out = {"items": items, "count": len(items), "source": source}
    if truncated:
        out["truncated"] = True
    if not items:
        out["empty_reason"] = empty_reason
    return out


def _workspaces_section(sessions, workspace_entries) -> dict:
    """Registry entries whose path backs one of this project's conversations.

    Matched on path, reported by NAME. The absolute path is deployment detail
    the panel has no business printing, and the caller's own workspace ACL has
    already been applied to ``workspace_entries`` by the route.
    """
    wanted = {
        str(s.get("workspace") or "").strip()
        for s in sessions if str(s.get("workspace") or "").strip()
    }
    items = []
    for entry in workspace_entries or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("path") or "").strip() not in wanted:
            continue
        items.append({
            "name": str(entry.get("name") or ""),
            "source": "workspaces",
        })
    return _section(
        items, "workspaces",
        "No space you can open is linked to this project's conversations.",
    )


def _files_section(sessions, workspace_entries, list_dir_reader) -> dict:
    """A shallow peek at each linked space, capped so a monorepo stays cheap."""
    if list_dir_reader is None:
        return _section(
            [], "workspace_files",
            "File listing is not available for this project right now.",
        )
    linked = _workspaces_section(sessions, workspace_entries)["items"]
    items = []
    truncated = len(linked) > MAX_FILE_ROOTS
    for entry in linked[:MAX_FILE_ROOTS]:
        name = entry.get("name") or ""
        try:
            listing = list_dir_reader(name) or []
        except Exception:
            logger.debug("hub file listing failed for a space", exc_info=True)
            continue
        if len(listing) > MAX_FILE_ENTRIES:
            truncated = True
        for row in listing[:MAX_FILE_ENTRIES]:
            if not isinstance(row, dict):
                continue
            items.append({
                "name": str(row.get("name") or ""),
                "workspace": str(name),
                "is_dir": bool(row.get("is_dir")),
                "source": "workspace_files",
            })
    return _section(
        items, "workspace_files",
        "No files were found in the spaces linked to this project.",
        truncated=truncated,
    )


def _jobs_section(sessions, cron_rows) -> dict:
    """Scheduled jobs attached through the WebUI origin of a visible session.

    A job is only ever attached to a project through
    ``origin={'platform':'webui','chat_id':<session_id>}``: that is the one
    link this system actually records. A job from another platform is left
    unattached rather than guessed at, and a job whose originating session the
    caller cannot see is dropped with it.
    """
    session_ids = {
        str(s.get("session_id") or "") for s in sessions if s.get("session_id")
    }
    items = []
    for job in cron_rows or []:
        if not isinstance(job, dict):
            continue
        origin = job.get("origin")
        if not isinstance(origin, dict):
            continue
        if str(origin.get("platform") or "").strip().lower() != "webui":
            continue
        chat_id = str(origin.get("chat_id") or "").strip()
        if not chat_id or chat_id not in session_ids:
            continue
        items.append({
            "name": str(job.get("name") or job.get("id") or ""),
            "schedule": str(job.get("schedule") or ""),
            "session_id": chat_id,
            "source": "scheduled_jobs",
        })
        if len(items) >= MAX_JOBS:
            break
    return _section(
        items, "scheduled_jobs",
        "No scheduled job of yours was started from a conversation in this project.",
    )


def _status_section(sessions, workspace_entries, project_os_reader) -> dict:
    """The only real project-status text this system holds: the Project OS docs."""
    if project_os_reader is None:
        return _section(
            [], "project_os",
            "No project status document was found for this project.",
        )
    items = []
    for entry in _workspaces_section(sessions, workspace_entries)["items"][:MAX_FILE_ROOTS]:
        name = entry.get("name") or ""
        try:
            status = project_os_reader(name)
        except Exception:
            logger.debug("hub project status read failed", exc_info=True)
            continue
        if not isinstance(status, dict) or not status.get("summary"):
            continue
        items.append({
            "workspace": str(name),
            "summary": str(status.get("summary") or ""),
            "updated_at": status.get("updated_at") or 0,
            "source": "project_os",
        })
    return _section(
        items, "project_os",
        "No project status document was found for this project.",
    )


def project_detail(
    project,
    session_rows,
    owner_scope,
    active_profile,
    capabilities,
    *,
    workspace_entries=None,
    cron_rows=None,
    list_dir_reader=None,
    project_os_reader=None,
) -> dict:
    """Everything the hub can honestly say about one project, section-gated.

    Readers are injected rather than imported so this stays pure: the route
    binds them to the workspace-confined helpers, tests bind them to nothing.
    A reader that raises costs its own section an ``empty_reason``, never the
    whole response.
    """
    if not isinstance(project, dict):
        raise ValueError("project must be a record")
    capabilities = capabilities or {}
    sessions = [
        row for row in visible_sessions(session_rows, owner_scope, active_profile)
        if str(row.get("project_id") or "") == str(project.get("project_id") or "")
    ]
    sessions.sort(key=_activity_at, reverse=True)

    detail = {
        "project": {
            "project_id": str(project.get("project_id") or ""),
            "name": str(project.get("name") or ""),
            "color": str(project.get("color") or ""),
            "system": is_system_project(project),
            "source": "project_record",
        },
        "conversations": _section(
            _conversation_items(sessions), "conversations",
            "No conversation you can see is filed under this project yet.",
            truncated=len(sessions) > MAX_CONVERSATIONS,
        ),
    }

    if capabilities.get("workspaces"):
        detail["workspaces"] = _workspaces_section(sessions, workspace_entries)
    if capabilities.get("files"):
        detail["files"] = _files_section(sessions, workspace_entries, list_dir_reader)
    if capabilities.get("jobs"):
        detail["jobs"] = _jobs_section(sessions, cron_rows)
    if capabilities.get("status"):
        detail["status"] = _status_section(sessions, workspace_entries, project_os_reader)
    if capabilities.get("delivery"):
        # Link only, and labelled as shared: the board has no per-user
        # ownership, so its rows are not this caller's rows.
        detail["delivery"] = {
            "shared_board": True,
            "source": "kanban_board",
            "empty_reason": (
                "The task board is shared with everyone on this workstation, "
                "so it is linked here rather than summarised per project."
            ),
        }
    return detail


# ── Integrations: what is honestly not connected yet ────────────────────────

# Locally knowable hints only: the lowercased name of a configured MCP server.
# Nothing here probes, spawns or dials anything.
_INTEGRATION_HINTS = (
    (
        "meetings",
        "Meetings",
        ("fireflies", "granola", "otter", "recall", "meeting", "meet", "zoom"),
        "This view cannot read meeting notes yet, so nothing a meeting "
        "recorder captures is filed under a project here.",
    ),
    (
        "notes",
        "Notes",
        ("notion", "obsidian", "joplin", "logseq", "readwise", "wiki", "note"),
        "This view cannot read pages from a shared notes tool yet, so nothing "
        "written there is shown here.",
    ),
    (
        "code_reviews",
        "Code reviews",
        ("github", "gitlab", "bitbucket", "devops"),
        "This view reads local repositories only, so pull requests and code "
        "reviews from a hosting service are not shown here.",
    ),
    (
        "client_materials",
        "Client materials",
        ("attio", "hubspot", "salesforce", "pipedrive", "crm", "productive"),
        "This view cannot read a customer record system yet, so client details "
        "are not shown here.",
    ),
)


def integration_status(mcp_servers, mcp_runtime=None, notes_drawer_enabled=None) -> list:
    """What each external project source is, and honestly is not, today.

    Modelled on the notes-sources drawer (api/routes.py): report only what is
    locally knowable and never invent a source. The three states are:

    * ``not_configured``  nothing of this kind is set up on this workstation;
    * ``configured_not_readable``  something of this kind is set up but is not
      running, so nothing could be read from it even with a reader;
    * ``reader_missing``  it is set up and running, and what is missing is our
      side: this hub has no reader for it yet.

    A row's ``seam`` describes what this hub cannot do yet and is therefore
    true in all three states; the CONFIGURATION claim lives only in the
    state, which is derived from evidence.

    ``notes_drawer_enabled`` is the deployment's own opt-in flag and is
    protected by files:read on its own route, so the caller passes None when
    the caller may not see it; the notes row then reports the server state
    alone.
    """
    servers = mcp_servers if isinstance(mcp_servers, dict) else {}
    runtime = mcp_runtime if isinstance(mcp_runtime, dict) else {}
    names = {str(name or "").strip().lower(): name for name in servers}

    rows = []
    for key, label, hints, seam in _INTEGRATION_HINTS:
        matched = [
            original for folded, original in names.items()
            if any(hint in folded for hint in hints)
        ]
        if not matched:
            state = "not_configured"
        elif any(bool((runtime.get(name) or {}).get("connected")) for name in matched):
            state = "reader_missing"
        else:
            state = "configured_not_readable"
        if key == "notes" and notes_drawer_enabled is False and state == "reader_missing":
            # The drawer this deployment can turn on is off, so even a running
            # server is not readable here. Do not claim otherwise.
            state = "configured_not_readable"
        rows.append({
            "key": key,
            "label": label,
            "state": state,
            "seam": seam,
            "source": "local_inventory",
        })
    return rows
