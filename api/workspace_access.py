"""Live workspace membership ceiling, independent of resource grants.

All explicitly owned ancestor roots must authorize the actor. A shared parent
or a symlink cannot bypass a private child; an unowned child cannot erase a
parent's ACL. Legacy unowned roots and existing admin recovery stay compatible.
This is application authorization, not an OS sandbox for host execution.
"""
import json
from pathlib import Path


def entry_emails(entry):
    owner = str(entry.get('owner_email') or '').strip().lower()
    members = entry.get('members') or []
    return {value for value in [owner, *(str(m or '').strip().lower() for m in members)] if value}


def load_acl_entries():
    """Read fresh ACL state without load_workspaces' corrupt-file fallback."""
    from api.workspace import _workspaces_file, load_workspaces
    try:
        registry = _workspaces_file()
        rows = json.loads(registry.read_text(encoding='utf-8')) if registry.exists() else load_workspaces()
        if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get('path'), str)
            or not row['path'].strip() or (row.get('members') is not None and not isinstance(row['members'], list))
            for row in rows):
            raise ValueError('Invalid workspace ACL registry')
        return rows
    except (OSError, ValueError, TypeError):
        raise PermissionError('Workspace membership unavailable') from None


def ensure_scope_access(scope, path, *, entries=None):
    if scope == 'all' or not path:
        return
    try:
        target = Path(path).expanduser().resolve()
        for entry in load_acl_entries() if entries is None else entries:
            emails = entry_emails(entry)
            if not emails:
                continue
            root = Path(entry['path']).expanduser().resolve()
            if target.is_relative_to(root) and scope not in emails:
                raise PermissionError('Workspace membership required')
    except (OSError, ValueError, RuntimeError):
        raise PermissionError('Workspace membership unavailable') from None


def ensure_workspace_access(handler, path, *, entries=None):
    from api.ownership import request_owner_scope
    ensure_scope_access(request_owner_scope(handler), path, entries=entries)


def ensure_workspace_selection(handler, path, *, entries=None):
    """Require membership and the policy's workspace dimension for activation."""
    ensure_workspace_access(handler, path, entries=entries)
    from api.governance.enforce import _request_identity
    _ensure_governance_selection(_request_identity(handler), path, entries=entries)


def resolve_implicit_workspace(handler, preferred=None):
    """Choose a usable workspace without rewriting shared selection hints.

    A profile's remembered directory is a hint shared by its users, not a
    permission grant. Explicit caller selections must use the strict validator.
    """
    from api.config import DEFAULT_WORKSPACE
    from api.workspace import _profile_default_workspace, resolve_trusted_workspace

    entries = load_acl_entries()
    candidates = [preferred, _profile_default_workspace(), DEFAULT_WORKSPACE,
                  *(entry['path'] for entry in entries)]
    seen = set()
    for candidate in candidates:
        if not candidate or str(candidate) in seen:
            continue
        seen.add(str(candidate))
        try:
            resolved = resolve_trusted_workspace(candidate)
            ensure_workspace_selection(handler, resolved, entries=entries)
        except (OSError, ValueError, TypeError):
            continue
        return str(resolved)
    raise PermissionError('No authorized workspace is available')


def _ensure_governance_selection(identity, path, *, entries=None):
    if not path:
        return
    from api.governance.loader import get_policy
    from api.governance.resolver import resolve_effective_access
    from api.governance.enforce import subject_from_identity
    from api.governance.models import grant_matches
    try:
        policy = get_policy()
        if not policy.enabled or policy.mode == 'report_only':
            return
        access = resolve_effective_access(policy, subject_from_identity(identity))
        target = Path(path).expanduser().resolve()
        rows = load_acl_entries() if entries is None else entries
        names = [str(row.get('name') or '') for row in rows
                 if target.is_relative_to(Path(row['path']).expanduser().resolve())]
        if grant_matches(access.deny.workspaces, str(target), path=True) or any(
                grant_matches(access.deny.workspaces, name) for name in names):
            raise PermissionError('Workspace explicitly denied by governance')
        if not access.grants.workspaces and access.role_ceiling is None:
            return  # Legacy omitted dimension retains its coarse route rule.
        if not (access.allows('workspaces', str(target), path=True) or any(
                access.allows('workspaces', name) for name in names)):
            raise PermissionError('Workspace is outside the user\'s governed scope')
    except PermissionError:
        raise
    except Exception:
        raise PermissionError('Workspace governance unavailable') from None


def ensure_identity_workspace_access(identity, path):
    from api.ownership import user_isolation_enabled, identity_is_admin, admin_sees_all
    if not user_isolation_enabled() or not identity or (identity_is_admin(identity) and admin_sees_all()):
        return
    ensure_scope_access(str(identity.get('email') or '').strip().lower(), path)


def ensure_identity_workspace_selection(identity, path):
    ensure_identity_workspace_access(identity, path)
    _ensure_governance_selection(identity, path)


def ensure_session_workspace_access(handler, session):
    # Worktree paths may sit outside the registered repository. Membership in
    # its source repository remains required after creating the worktree.
    repository = getattr(session, 'worktree_repo_root', None)
    workspace = getattr(session, 'workspace', None)
    ensure_workspace_selection(handler, repository or workspace)
    for path in (repository, workspace):
        ensure_workspace_access(handler, path)


def runtime_workspace_scope(session, identity, *, workspace=None):
    """Return a trusted, non-serializable checker for this turn's live ACL.

    Capture the principal and roots, never request-local TLS. Each engine call
    reopens the captured profile's registry using TLS-only profile binding.
    """
    from copy import deepcopy
    captured_identity = deepcopy(identity)
    workspace_path = str(workspace if workspace is not None else getattr(session, 'workspace', '') or '')
    repository_path = str(getattr(session, 'worktree_repo_root', '') or '')
    profile = str(getattr(session, 'profile', '') or 'default')

    def check(path):
        from api import profiles
        from api.ownership import user_isolation_enabled
        if (user_isolation_enabled() and captured_identity
                and captured_identity.get('method') != 'auth_disabled'
                and not str(captured_identity.get('email') or '').strip()):
            raise PermissionError('Workspace actor identity required')
        previous_profile = getattr(profiles._tls, 'profile', None)
        profiles.set_request_profile(profile)
        try:
            ensure_identity_workspace_selection(captured_identity, repository_path or workspace_path)
            for target in (repository_path, workspace_path, path):
                if target:
                    ensure_identity_workspace_access(captured_identity, target)
        finally:
            if previous_profile is None:
                profiles.clear_request_profile()
            else:
                profiles.set_request_profile(previous_profile)
        return True

    return workspace_path, check


def guard_session_request(handler, parsed, body=None):
    """Guard workspace execution on an existing session; cancellation stays usable."""
    from urllib.parse import parse_qs
    path = parsed.path
    relevant = path.startswith('/api/git/') or path in {
        '/api/chat/start', '/api/chat', '/api/chat/steer', '/api/terminal/start',
        '/api/terminal/input', '/api/terminal/resize', '/api/terminal/output', '/api/session/worktree/remove'}
    if not relevant:
        return True
    values = body if isinstance(body, dict) else {k: v[0] for k, v in parse_qs(parsed.query).items()}
    sid = values.get('session_id')
    if not sid:
        return True  # Existing endpoint validation handles missing context.
    from api.routes import get_session_for_file_ops
    from api.helpers import j
    try:
        ensure_session_workspace_access(handler, get_session_for_file_ops(sid))
    except KeyError:
        return True
    except PermissionError as exc:
        j(handler, {'error': str(exc)}, status=403)
        return False
    return True
