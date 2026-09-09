"""Deny generic file API access across private actor boundaries.

This adds no workspace permission. Existing route authorization and anchored IO
still apply after this check. Host administrators and terminal access are a
separate trust boundary.
"""
from pathlib import Path


def guard_request(handler, route, values):
    if not (route.startswith('/api/file') or route.startswith('/api/escape/')
            or route in ('/api/media', '/api/list', '/api/folder/download')):
        return
    from api import personal_context
    from api.governance.enforce import _request_identity
    identity = _request_identity(handler)
    from api.governance.resource_access import ensure_file_access
    write = route in {"/api/file/delete", "/api/file/save", "/api/file/office-save",
                      "/api/file/create", "/api/file/rename", "/api/file/move", "/api/file/create-dir"}
    sid = values.get('session_id')
    from api.routes import get_session_for_file_ops
    try:
        session = get_session_for_file_ops(sid) if sid else None
    except KeyError:
        session = None  # Existing route returns its normal missing-session error.
    workspace = getattr(session, 'workspace', None)
    if session:
        from api.workspace_access import ensure_session_workspace_access
        ensure_session_workspace_access(handler, session)
    candidates = []
    if route.startswith('/api/escape/') and workspace and values.get('token'):
        from api.workspace import resolve_authorized_escape_request
        try:
            resolved = resolve_authorized_escape_request(Path(workspace), sid, values['token'], values.get('path') or '.')
        except (ValueError, FileNotFoundError):
            raise PermissionError('Invalid private file authorization') from None
        personal_context.ensure_actor_path(identity, resolved['target'], session)
        ensure_file_access(identity, resolved['target'], write=write)
    if route == '/api/file/raw' and session:
        from api.routes import _file_raw_target
        resolved = _file_raw_target(session, sid, values.get('path') or '')
        if resolved:
            personal_context.ensure_actor_path(identity, resolved[1], session)
            ensure_file_access(identity, resolved[1], write=write)
    for key in ('path', 'dest_dir', 'new_path'):
        raw = values.get(key)
        if raw is None:
            continue
        path = Path(str(raw))
        if not path.is_absolute():
            if not workspace:
                continue  # Existing endpoint validation rejects missing context.
            path = Path(workspace) / path
        candidates.append(path.resolve())
    if not candidates and workspace and route in ('/api/list', '/api/folder/download'):
        candidates.append(Path(workspace).resolve())
    if values.get('new_name') and candidates:
        candidates.append(candidates[0].parent / str(values['new_name']))
    for path in candidates:
        personal_context.ensure_actor_path(identity, path, session)
        ensure_file_access(identity, path, write=write)
