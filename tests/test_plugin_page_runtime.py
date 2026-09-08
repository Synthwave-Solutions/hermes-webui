"""Real plugin route/renderer boundaries for opaque dashboard frames."""
import base64
import io
import re
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from api import plugins, routes
from api.governance import enforce, loader


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    dashboard = tmp_path / 'qa' / 'dashboard'
    (dashboard / 'dist').mkdir(parents=True)
    script = b'document.body.append("QA_PLUGIN_PAGE </script> & \\u263a");'
    css = b'body {color: rgb(1, 2, 3)} /* </style> */'
    (dashboard / 'dist' / 'index.js').write_bytes(script)
    (dashboard / 'dist' / 'style.css').write_bytes(css)
    manifest = {'name': 'qa', 'label': '<script>unsafe</script>', 'tab': {'path': '/qa'}}
    monkeypatch.setattr(plugins, '_PLUGIN_STATIC_ROOTS', {'qa': dashboard.resolve()})
    monkeypatch.setattr(plugins, 'PLUGIN_MANIFESTS', {'qa': manifest})
    return SimpleNamespace(root=dashboard, manifest=manifest, script=script, css=css)


def test_iife_shell_preserves_exact_bytes_without_cookie_bearing_asset_fetches(plugin):
    document = plugins.build_plugin_iife_page('qa', plugin.manifest).decode()
    assert '<title>&lt;script&gt;unsafe&lt;/script&gt;</title>' in document
    assert '<script>unsafe</script>' not in document
    assert '/dashboard-plugins/' not in document
    urls = re.findall(r'(?:src|href)="data:([^;]+);base64,([^"]+)"', document)
    assert {mime: base64.b64decode(encoded) for mime, encoded in urls} == {
        'application/javascript': plugin.script, 'text/css': plugin.css,
    }


@pytest.mark.parametrize('css', ['../private.css', 'dist/.hidden.css', 'dist/source.py', 'https://outside.invalid/style.css'])
def test_manifest_cannot_embed_unapproved_files(plugin, css):
    (plugin.root.parent / 'private.css').write_text('PRIVATE_MARKER')
    (plugin.root / 'dist' / '.hidden.css').write_text('PRIVATE_MARKER')
    (plugin.root / 'dist' / 'source.py').write_text('PRIVATE_MARKER')
    document = plugins.build_plugin_iife_page('qa', {**plugin.manifest, 'css': css}).decode()
    assert 'data:text/css' not in document
    assert 'PRIVATE_MARKER' not in document


def test_bundle_and_stylesheet_symlinks_cannot_embed_outside_plugin(plugin):
    outside = plugin.root.parent / 'private.js'
    outside.write_bytes(b'PRIVATE_MARKER')
    script = plugin.root / 'dist' / 'index.js'
    script.unlink(); script.symlink_to(outside)
    assert plugins.build_plugin_iife_page('qa', plugin.manifest) is None


@pytest.fixture
def harness(plugin, monkeypatch):
    identity = {'email': 'qa-plugin@example.test', 'groups': [], 'method': 'qa'}
    monkeypatch.setattr(enforce, '_request_identity', lambda _: identity)
    monkeypatch.setattr(enforce, '_audit_decision', lambda *args, **kwargs: None)
    monkeypatch.setattr('api.bot_builder.guard_profile_request', lambda *_: True)
    monkeypatch.setattr(routes, '_handle_extension_sidecar_proxy', lambda *a, **k: False)
    monkeypatch.setattr(routes.governance_api, 'handle_governance_api', lambda *_: False)
    monkeypatch.setattr(routes, '_dashboard_plugin_enabled', lambda _: True)
    def policy(*, permissions=('plugins:read',), paths=('/api/plugins',), deny=None, mode='enforce'):
        parsed = loader.parse_governance_policy({'mode': mode, 'users': {identity['email']: {
            'grants': {'permissions': list(permissions), 'routes': list(paths)}, 'deny': deny or {},
        }}})
        monkeypatch.setattr(loader, 'get_policy', lambda: parsed)
    def request(path):
        handler = SimpleNamespace(path=path, command='GET', headers={}, wfile=io.BytesIO(), status=None, response_headers={})
        handler.send_response = lambda status: setattr(handler, 'status', status)
        handler.send_header = lambda name, value: handler.response_headers.__setitem__(name, value)
        handler.end_headers = lambda: None
        handled = routes.handle_get(handler, urlsplit(path))
        if not handled:
            handler.status = 404
        return handler
    policy()
    return SimpleNamespace(policy=policy, request=request)


@pytest.mark.parametrize('path', ['/qa', '/dashboard-plugins/qa/dist/index.js'])
def test_plugin_surface_uses_canonical_panel_route_and_permission(harness, path):
    response = harness.request(path)
    assert response.status == 200
    assert response.response_headers['Content-Security-Policy'] == 'sandbox allow-scripts allow-forms allow-popups'
    assert b'PRIVATE_MARKER' not in response.wfile.getvalue()


@pytest.mark.parametrize('path', ['/qa', '/dashboard-plugins/qa/dist/index.js'])
@pytest.mark.parametrize('boundary', ['permission', 'route', 'explicit_deny', 'policy_error'])
def test_denied_plugin_surface_never_reads_any_bundle(harness, monkeypatch, path, boundary):
    if boundary == 'permission':
        harness.policy(permissions=[])
    elif boundary == 'route':
        harness.policy(paths=[])
    elif boundary == 'explicit_deny':
        harness.policy(deny={'permissions': ['plugins:read']})
    else:
        monkeypatch.setattr(loader, 'get_policy', lambda: (_ for _ in ()).throw(ValueError('invalid policy')))
    monkeypatch.setattr(plugins, 'serve_plugin_static', lambda *_: pytest.fail('denied plugin asset read'))
    response = harness.request(path)
    assert response.status == 403
    assert b'QA_PLUGIN_PAGE' not in response.wfile.getvalue()


@pytest.mark.parametrize('path', ['/qa', '/dashboard-plugins/qa/dist/index.js'])
def test_disabled_plugin_returns_404_even_for_granted_user(harness, monkeypatch, path):
    monkeypatch.setattr(routes, '_dashboard_plugin_enabled', lambda _: False)
    assert harness.request(path).status == 404


@pytest.mark.parametrize('path', ['/qa', '/dashboard-plugins/qa/dist/index.js'])
def test_report_only_preserves_existing_plugin_access(harness, path):
    harness.policy(permissions=[], mode='report_only')
    assert harness.request(path).status == 200


def test_shared_plugin_stylesheet_requires_the_same_permission(harness, plugin, monkeypatch):
    base = plugin.root.parent.parent
    (base / 'plugin.css').write_bytes(b'QA_SHARED_STYLE')
    monkeypatch.setattr(plugins, '_get_plugin_base', lambda: base)
    assert harness.request('/plugins/plugin.css').wfile.getvalue() == b'QA_SHARED_STYLE'
    harness.policy(permissions=[])
    denied = harness.request('/plugins/plugin.css')
    assert denied.status == 403 and b'QA_SHARED_STYLE' not in denied.wfile.getvalue()
