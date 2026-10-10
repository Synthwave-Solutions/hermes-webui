"""Authenticated app links from the rendered installation environment only."""
from __future__ import annotations
import json
import os
import re
from urllib.parse import urlsplit
from api import modules
from api.org_modules import CATALOG, context
from api.helpers import j

_HOST = re.compile(r'(?=.{1,253}$)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z')


def safe_link(value, environ):
    """Public subdomains or this node's exact private hostname. No request-derived trust."""
    if not isinstance(value, str) or any(ord(c) <= 32 for c in value) or '\\' in value:
        return None
    try:
        u = urlsplit(value)
        host = (u.hostname or '').lower()
        domain = environ.get('SP_DOMAIN', '').strip().lower()
        mesh = environ.get('SP_MESH_FQDN', '').strip().lower()
        if (u.scheme != 'https' or not _HOST.fullmatch(host) or '..' in host
                or u.username is not None or u.password is not None or u.query or u.fragment
                or any(name.lower() in host for name in modules.DISPLAY_DENYLIST)):
            return None
        port = u.port
        public = bool(domain and _HOST.fullmatch(domain) and '.' in domain
                      and (host == domain or host.endswith('.' + domain)))
        private = bool(mesh and _HOST.fullmatch(mesh) and host == mesh)
        if not (public or private) or (public and not private and port not in (None, 443)):
            return None
        return value
    except (ValueError, TypeError):
        return None


def handle_get(handler, parsed):
    try:
        policy, subject, scope = context(handler)
    except Exception:
        j(handler, {'error': 'policy_unavailable'}, status=503)
        return True
    if not subject.normalized_email or subject.provider == 'auth_disabled':
        j(handler, {'error': 'forbidden'}, status=403)
        return True
    try:
        links = json.loads(os.environ.get('SP_MODULE_LINKS', '{}'))
        if not isinstance(links, dict):
            links = {}
    except (ValueError, TypeError):
        links = {}
    state = modules.current_state()
    apps = []
    for mid in state.active:
        spec = modules.REGISTRY[mid]
        if not spec.app_tile:
            continue
        if mid == 'workflows' and os.getenv('SP_WORKFLOWS_CLIENT_EDITOR') != '1' and scope.scope != 'platform':
            continue
        url = safe_link(links.get(mid), os.environ)
        if url:
            apps.append({'module': mid, 'name': CATALOG[mid]['name'], 'url': url})
    j(handler, {'apps': apps})
    return True
