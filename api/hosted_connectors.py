"""Hosted connector catalog and personal accounts beside the Nango catalog."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

from api import personal_context

_CATALOG_LOCK = threading.Lock()
_CATALOG_CACHE = None
_TOKEN_LOCK = threading.Lock()
_TOKEN_CACHE = {}
_PERSONAL_CATALOGS = {}


def catalog():
    """Public metadata only: no guest identity or credentials on page reads."""
    global _CATALOG_CACHE
    with _CATALOG_LOCK:
        if _CATALOG_CACHE and time.monotonic() - _CATALOG_CACHE[0] < 900:
            return _CATALOG_CACHE[1]
        from tools.connectors.portal.client import PortalConnectorClient
        rows = PortalConnectorClient().public_catalog().model_dump()['connectors']
        _CATALOG_CACHE = (time.monotonic(), rows)
        return rows


def _account_home(identity):
    return personal_context._safe(personal_context.home(identity) / 'connectors')


def catalog_for(identity):
    """Signed-in users see their actual catalog; private metadata is never shared."""
    path = personal_context._safe(_account_home(identity) / 'auth.json')
    if not path.is_file():
        return catalog()
    key = (str(path), path.stat().st_mtime_ns)
    now = time.monotonic()
    with _CATALOG_LOCK:
        cached = _PERSONAL_CATALOGS.get(key)
        if cached and cached[0] > now:
            return cached[1]
    rows = _worker(identity, 'catalog')['connectors']
    with _CATALOG_LOCK:
        for old in [k for k, value in _PERSONAL_CATALOGS.items() if value[0] <= now]:
            _PERSONAL_CATALOGS.pop(old, None)
        _PERSONAL_CATALOGS[key] = (now + 300, rows)
    return rows


def _worker(identity, action, **values):
    from api.config import _AGENT_DIR
    root = _account_home(identity)
    if action in {'accounts', 'token'} and not (root / 'auth.json').is_file():
        return {'accounts': []} if action == 'accounts' else {'token': None}
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    # An allowlist, not a copy of os.environ: a bot's Nous/TOOL_GATEWAY token
    # must never override this person's store. No shell and no arbitrary action.
    env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL', 'SSL_CERT_FILE', 'SSL_CERT_DIR') if key in os.environ}
    # Native auth also falls back through get_default_hermes_root(). Pin HOME
    # so a personal store below the host's Hermes directory stays its own root.
    env.update(HOME=str(root), HERMES_HOME=str(root), HERMES_SHARED_AUTH_DIR=str(root / 'shared'),
               PYTHONPATH=str(_AGENT_DIR), PYTHONDONTWRITEBYTECODE='1')
    process = subprocess.run([sys.executable, str(Path(__file__).with_name('hosted_connector_worker.py'))],
                             input=json.dumps({'action': action, **values}), text=True,
                             capture_output=True, timeout=55, env=env, cwd=str(_AGENT_DIR))
    try:
        data = json.loads(process.stdout)
    except ValueError:
        raise RuntimeError('The connector service is unavailable. Please retry.') from None
    if process.returncode or not data.get('ok'):
        raise RuntimeError('The connector service could not complete this request. Please retry.')
    return data['result']


def personal_token(identity):
    root = _account_home(identity)
    path = personal_context._safe(root / 'auth.json')
    if not path.is_file():
        return None
    signature = (path.stat().st_mtime_ns, path.stat().st_size)
    key = str(root)
    with _TOKEN_LOCK:
        cached = _TOKEN_CACHE.get(key)
        if cached and cached[0] == signature and time.monotonic() < cached[1]:
            return cached[2]
    value = _worker(identity, 'token').get('token')
    with _TOKEN_LOCK:
        # Bound memory growth; the cache contains only short-lived private credentials.
        now = time.monotonic()
        for expired in [k for k, v in _TOKEN_CACHE.items() if v[1] <= now]:
            _TOKEN_CACHE.pop(expired, None)
        _TOKEN_CACHE[key] = (signature, now + 60, value)
    return value


def account_rows(identity):
    rows = _worker(identity, 'accounts')['accounts']
    fields = ('connector', 'connectionId', 'alias', 'label', 'status', 'disabled')
    return [{k: row.get(k) for k in fields} for row in rows]


class _ApprovalRequired(PermissionError):
    def __init__(self, requests):
        self.requests = requests
        super().__init__(' '.join(row['message'] for row in requests))


def authorize_connection(identity, slugs):
    """Server-owned policy callback for browser and native connect/reconnect.

    Record unapproved providers in the existing queue before refusing the whole
    mutation; no partial batch can mint links. Identity is supplied by the host.
    """
    from api.integrations import provider_approval, request_provider_approval, _record_admin_approval
    from api.ownership import identity_is_admin

    owner = personal_context.actor_email(identity)
    if not isinstance(slugs, (list, tuple)) or not slugs or any(
            not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,99}', slug)
            for slug in slugs):
        raise ValueError('Invalid connector')
    is_admin = identity_is_admin(identity)
    pending = []
    for slug in dict.fromkeys(slugs):
        key = 'hosted-' + slug
        if is_admin:
            _record_admin_approval(key, owner, None)
        elif provider_approval(key, owner)['approval'] != 'approved':
            request = request_provider_approval(owner, key)
            if request['approval'] != 'approved':
                pending.append(request)
    if pending:
        raise _ApprovalRequired(pending)


def connect(identity, slug):
    if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,99}', slug):
        raise ValueError('Invalid connector')
    if not any(row['slug'] == slug for row in catalog_for(identity)):
        raise ValueError('Unknown connector')
    try:
        authorize_connection(identity, [slug])
    except _ApprovalRequired as exc:
        return exc.requests[0]
    result = _worker(identity, 'connect', slug=slug)
    rows = result.get('results') or []
    row = next((r for r in rows if r.get('connector') == slug), None)
    if not row or row.get('status') == 'failed':
        raise RuntimeError('This connector could not be connected. Please retry.')
    url = str(row.get('connect_url') or '')
    parsed = urlsplit(url)
    if url and (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password):
        raise RuntimeError('The connector returned an invalid authorization link.')
    return {'status': row['status'], 'connect_url': url}


def disconnect(identity, connection_id):
    if not isinstance(connection_id, str) or not connection_id or len(connection_id) > 256:
        raise ValueError('Invalid connection')
    if not any(r['connectionId'] == connection_id for r in account_rows(identity)):
        raise PermissionError('This connection does not belong to your account')
    return _worker(identity, 'disconnect', connection_id=connection_id)


def handle(handler, action, body=None):
    from api.ownership import _request_identity
    from api.routes import j
    identity = _request_identity(handler)
    try:
        personal_context.actor_email(identity)
        if action == 'catalog':
            return j(handler, {'connectors': catalog_for(identity)})
        if action == 'accounts':
            return j(handler, {'accounts': account_rows(identity)})
        if action == 'connect':
            value = connect(identity, (body or {}).get('slug'))
            return j(handler, value, status=202 if value.get('status') == 'pending_approval' else 200)
        if action == 'disconnect':
            return j(handler, disconnect(identity, (body or {}).get('connection_id')))
        return j(handler, {'error': 'Unknown connector action'}, status=404)
    except PermissionError as exc:
        return j(handler, {'error': str(exc)}, status=403)
    except ValueError as exc:
        return j(handler, {'error': str(exc)}, status=400)
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return j(handler, {'error': 'The connector service is unavailable. Please retry.'}, status=502)
