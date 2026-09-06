"""Explicit project membership, isolated files, and project conversation creation.

Project membership grants transcript and scoped file access only. Bot execution
continues to resolve each original human's existing profile/tool permissions.
"""
import base64
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

from api.models import PROJECTS_LOCK as _LOCK


def _value(row, key, default=None):
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


def project_for(pid):
    from api.models import load_projects
    return next((p for p in load_projects(_migrate=False) if p.get('project_id') == pid), None)


def administrative(email):
    from api.ownership import identity_is_admin
    return identity_is_admin(email if isinstance(email, dict) else {'email':email})


def transaction(function):
    from functools import wraps
    @wraps(function)
    def wrapped(handler, parsed, *args, **kwargs):
        if str(getattr(parsed, 'path', '')).startswith('/api/projects/'):
            with _LOCK:
                return function(handler, parsed, *args, **kwargs)
        return function(handler, parsed, *args, **kwargs)
    return wrapped


def member(project, email):
    who = str((email.get('email') if isinstance(email, dict) else email) or '').strip().lower()
    return bool(who and project and not project.get('deleted') and
                (who == str(project.get('owner_email') or '').lower() or who in project.get('members', []) or administrative(email)))


def session_access(session, email):
    """None for legacy personal chats; bool for authoritative project scope."""
    pid = _value(session, 'project_id')
    project = project_for(pid) if pid else None
    if _value(session, 'project_shared', False):
        return member(project, email)
    return None


def session_visible(session, scope):
    access = session_access(session, scope)
    if access is not None:
        # Shared project membership is explicit, including administrators.
        return access
    from api.group_chat import visible_to_scope
    return visible_to_scope(_value(session, 'owner_email'), _value(session, 'participants'), scope)


def _identity(handler):
    from api.governance.enforce import _request_identity, subject_from_identity
    from api.governance.loader import get_policy
    from api.governance.resolver import resolve_effective_access
    identity = _request_identity(handler)
    subject = subject_from_identity(identity)
    if not subject.normalized_email:
        raise PermissionError('Sign in to use shared projects')
    access = resolve_effective_access(get_policy(), subject)
    return subject.normalized_email, access


def _require(access, permission):
    # EffectiveAccess exposes the same permission predicate as route governance.
    if not access.has_permission(permission):
        raise PermissionError('Your account does not have ' + permission)


def _save(rows):
    from api.models import PROJECTS_FILE
    PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=PROJECTS_FILE.parent, prefix='.projects-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(rows, stream, ensure_ascii=False, indent=2)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, PROJECTS_FILE)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def public_project(project, actor, access):
    from api.group_chat import bot_allowed
    actor_email = str(actor.get('email') if isinstance(actor, dict) else actor).lower()
    public = dict(project)
    if not access.has_permission('files:read'): public.pop('workspace', None)
    return {**public, 'can_manage': actor_email == project.get('owner_email') or administrative(actor),
            'unavailable_bots': [b for b in project.get('bot_participants', []) if not bot_allowed(actor, b)]}


def _directory_fd(project):
    # Fixed server-owned directory identity; do not trust a caller-supplied path.
    from api.models import PROJECTS_FILE
    root = PROJECTS_FILE.parent / 'project_workspaces'
    rootfd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        return os.open(project['project_id'], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=rootfd)
    finally: os.close(rootfd)


def _filename(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.()-]{0,180}', name):
        raise ValueError('Use a plain file name without folders or hidden files')
    return name


def handle(handler, path, body=None, query=None):
    """Real dispatcher entry. Returns a payload; exceptions become HTTP errors."""
    from api import models, group_chat
    actor, access = _identity(handler)
    from api.governance.enforce import _request_identity
    actor_identity = _request_identity(handler)
    body = body or {}; query = query or {}
    pid = str(body.get('project_id') or (query.get('project_id') or [''])[0])
    if pid and not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', pid): raise ValueError('Invalid project ID')
    with _LOCK:
        project = project_for(pid) if pid else None
        if path == '/api/projects/team':
            _require(access, 'sessions:write')
            rows = models.load_projects(_migrate=False)
            if pid:
                if not project or project.get('deleted'): raise FileNotFoundError('Project not found')
                if actor != project.get('owner_email') and not administrative(actor_identity):
                    raise PermissionError('Only the project owner or administrator can change its members')
                if body.get('revision') != project.get('revision', 0): raise RuntimeError('Project changed; reload before saving')
            else:
                pid = uuid.uuid4().hex[:12]
                profile = str(body.get('profile') or 'default')
                # Presentation profile does not grant bot access.
                if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', profile): raise ValueError('Invalid bot profile')
                project = {'project_id': pid, 'owner_email': actor, 'profile': profile,
                           'created_at': time.time(), 'collaboration': True, 'revision': 0}
            name = body.get('name', project.get('name', ''))
            if not isinstance(name, str) or not name.strip() or len(name) > 128: raise ValueError('Project name required (at most 128 characters)')
            members, error = group_chat.validate(body.get('members', project.get('members', [])), owner_email=project['owner_email'])
            if error: raise ValueError(error)
            bots = group_chat.validate_bots(body.get('bot_participants', project.get('bot_participants', [])), actor_identity)
            project = {**project, 'collaboration': True, 'name': name.strip(), 'members': members, 'bot_participants': bots,
                       'revision': project.get('revision', 0) + 1, 'deleted': bool(body.get('deleted', False))}
            root = models.PROJECTS_FILE.parent / 'project_workspaces'
            root.mkdir(parents=True, exist_ok=True)
            if root.is_symlink(): raise ValueError('Invalid project workspace')
            folder = root / pid
            folder.mkdir(exist_ok=True)
            if folder.is_symlink(): raise ValueError('Invalid project workspace')
            project['workspace'] = str(folder)
            _save([p for p in rows if p.get('project_id') != pid] + [project])
            from api.governance.audit import append_audit_event
            append_audit_event('project_membership_changed', subject_email=actor,
                path=path, method='POST', reason='Explicit project update',
                extra={'project_id':pid,'revision':project['revision'],'members':members,
                       'bots':bots,'deleted':project['deleted']})
            from api.routes import _on_session_list_changed
            _on_session_list_changed(None)
            return {'ok': True, 'project': public_project(project, actor_identity, access)}
        if not project or not project.get('collaboration') or not member(project, actor_identity):
            raise FileNotFoundError('Project not found')
        if path == '/api/projects/files':
            _require(access, 'files:write' if body else 'files:read')
            fd = _directory_fd(project)
            try:
                if body:
                    name = _filename(body.get('name'))
                    encoded = body.get('content_base64')
                    if not isinstance(encoded, str) or len(encoded) > 7_000_000: raise ValueError('File limit is 5 MB')
                    blob = base64.b64decode(encoded, validate=True)
                    if len(blob) > 5_000_000: raise ValueError('File limit is 5 MB')
                    # O_EXCL refuses overwrites and symlinks. Retrying cannot silently replace data.
                    target = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
                    with os.fdopen(target, 'wb') as stream: stream.write(blob)
                    return {'ok': True, 'name': name}
                if query.get('name'):
                    name = _filename(query['name'][0])
                    target = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                    import stat
                    with os.fdopen(target, 'rb') as stream:
                        info = os.fstat(stream.fileno())
                        if not stat.S_ISREG(info.st_mode) or info.st_size > 5_000_000: raise ValueError('Not a downloadable project file')
                        blob = stream.read(5_000_001)
                        if len(blob) > 5_000_000: raise ValueError('File grew beyond the 5 MB download limit')
                    return {'name': name, 'content_base64': base64.b64encode(blob).decode()}
                import stat
                entries = []
                for name in sorted(os.listdir(fd)):
                    info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                    if stat.S_ISREG(info.st_mode): entries.append({'name': name, 'size': info.st_size})
                return {'files': entries}
            finally: os.close(fd)
        if path == '/api/projects/chat':
            _require(access, 'sessions:write')
            bots = body.get('bot_participants', project.get('bot_participants', []))
            if not isinstance(bots, list) or not bots or any(b not in project.get('bot_participants', []) for b in bots):
                raise ValueError('Select at least one bot assigned to this project')
            bots = group_chat.validate_bots(bots, actor_identity)
            session = models.new_session(workspace=project['workspace'], profile=project.get('profile'), project_id=pid)
            session.owner_email = actor; session.project_shared = True
            session.bot_participants = bots
            session.title = str(body.get('title') or project['name'])[:128]
            session.save()
            from api.routes import _on_session_list_changed
            _on_session_list_changed(None)
            return {'ok': True, 'session': session.compact() | {'messages': []}}
        raise ValueError('Unknown project operation')


def runtime_file_scope(session, actor, bot):
    """In-memory capability; read project and user policy on EVERY invocation."""
    if not _value(session, 'project_shared', False):
        return '', None
    pid = _value(session, 'project_id')
    project = project_for(pid)
    if not member(project, actor):
        raise PermissionError('Project membership was revoked')
    workspace = str(project['workspace'])
    def allowed(path, write=False):
        try:
            from api.governance.loader import get_policy
            from api.governance.enforce import subject_from_identity
            from api.governance.resolver import resolve_effective_access
            from api.group_chat import bot_allowed
            current = project_for(pid)
            if not member(current, actor) or current.get('workspace') != workspace:
                return False
            if bot not in current.get('bot_participants', []) or not bot_allowed(actor, bot):
                return False
            access = resolve_effective_access(get_policy(), subject_from_identity(actor if isinstance(actor, dict) else {'email':actor}))
            if not access.has_permission('files:write' if write else 'files:read'):
                return False
            target = Path(path)
            return target.is_absolute() and target.resolve().is_relative_to(Path(workspace).resolve())
        except Exception:
            return False
    return workspace, allowed
