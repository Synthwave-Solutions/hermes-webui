"""Personal sidebar organization; never changes sessions, projects or bot ACLs."""
import hashlib
import json
import os
import re
import threading
import uuid
from pathlib import Path

_LOCK = threading.RLock()
_ID = re.compile(r'^[A-Za-z0-9_-]{1,128}$')


def _path(email):
    from api.config import STATE_DIR
    return Path(STATE_DIR) / 'sidebar-organization' / (hashlib.sha256(email.encode()).hexdigest() + '.json')


def read(email):
    path = _path(email)
    if not path.exists():
        return dict(revision=0, sections=[], assignments={}, task_categories={}, task_grouping='category_bot')
    return json.loads(path.read_text())


def _name(value):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100 or any(ord(c) < 32 for c in value):
        raise ValueError('Use a name of 1–100 characters')
    return value.strip()


def update(email, body):
    with _LOCK:
        data = read(email)
        if type(body.get('revision')) is not int or body['revision'] != data['revision']:
            raise RuntimeError('Organization changed in another tab. Reload and try again.')
        sections = {s['id']: s for s in data['sections']}
        op = body.get('action')
        sid = body.get('id')
        if op in ('create', 'edit'):
            parent = body.get('parent') or None
            if parent is not None and parent not in sections:
                raise ValueError('Parent section not found')
            if op == 'edit' and sid not in sections:
                raise ValueError('Section not found')
            name = _name(body.get('name'))
            if op == 'create':
                if len(sections) >= 2000: raise ValueError('Section storage limit reached')
                sid = uuid.uuid4().hex
            # Iterative walk: unlimited nesting, but cycles are never valid.
            ancestor, seen = parent, {sid}
            while ancestor:
                if ancestor in seen: raise ValueError('A section cannot contain itself')
                seen.add(ancestor)
                ancestor = sections[ancestor].get('parent')
            sections[sid] = dict(id=sid, name=name, parent=parent)
            data['sections'] = list(sections.values())
        elif op == 'delete':
            if sid not in sections: raise ValueError('Section not found')
            parent = sections.pop(sid).get('parent')
            for section in sections.values():
                if section.get('parent') == sid: section['parent'] = parent
            data['sections'] = list(sections.values())
            data['assignments'] = {k: (parent if v == sid else v) for k, v in data['assignments'].items() if v != sid or parent}
        elif op in ('assign', 'category'):
            chat = body.get('session_id')
            if not isinstance(chat, str) or not _ID.fullmatch(chat): raise ValueError('Invalid conversation')
            if op == 'assign':
                target = body.get('section')
                if target and target not in sections: raise ValueError('Section not found')
                field = 'assignments'
            else:
                target = _name(body['category']) if body.get('category') else None
                field = 'task_categories'
            if target:
                if chat not in data[field] and len(data[field]) >= 20000: raise ValueError('Organization storage limit reached')
                data[field][chat] = target
            else: data[field].pop(chat, None)
        elif op == 'grouping':
            value = body.get('value')
            if value not in ('category', 'bot', 'category_bot'): raise ValueError('Invalid task grouping')
            data['task_grouping'] = value
        else: raise ValueError('Unknown organization action')
        data['revision'] += 1
        path = _path(email)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        try:
            with open(temp, 'w') as f:
                os.chmod(temp, 0o600)
                json.dump(data, f, ensure_ascii=False)
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
        return data


def handle(handler, body=None):
    from api.ownership import request_owner_email
    from api.routes import j, bad, get_session, _session_visible_to_request, _subagent_parent_visible_to_request
    email = str(request_owner_email(handler) or '').strip().lower()
    if not email: return bad(handler, 'Sign in to organize conversations', 401)
    try:
        if body is not None:
            if not isinstance(body, dict): raise ValueError('Expected an object')
            if body.get('action') in ('assign', 'category'):
                sid = body.get('session_id')
                if not isinstance(sid, str) or not _ID.fullmatch(sid): raise ValueError('Invalid conversation')
                try: allowed = _session_visible_to_request(get_session(sid), handler)
                except KeyError: allowed = _subagent_parent_visible_to_request(sid, handler)
                if not allowed: return bad(handler, 'Conversation not found', 404)
            return j(handler, update(email, body))
        return j(handler, read(email))
    except RuntimeError as exc: return bad(handler, str(exc), 409)
    except ValueError as exc: return bad(handler, str(exc), 400)
    except OSError: return bad(handler, 'Organization could not be saved or loaded', 503)
