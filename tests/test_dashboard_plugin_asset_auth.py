"""Unauthenticated plugin assets must not enter a relative login redirect loop."""
import io
from urllib.parse import urlparse

import pytest

from api import auth


class Handler:
    def __init__(self):
        self.headers = {}
        self.response_headers = {}
        self.wfile = io.BytesIO()
        self.status = None

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers[key] = value

    def end_headers(self):
        pass


@pytest.mark.parametrize('path', ['/dashboard-plugins/qa-dashboard/dist/index.js', '/plugins/plugin.css'])
def test_unauthenticated_plugin_bundle_returns_401_without_redirect(monkeypatch, path):
    monkeypatch.setattr(auth, 'is_auth_enabled', lambda: True)
    handler = Handler()
    assert not auth.check_auth(handler, urlparse(path))
    assert handler.status == 401
    assert 'Location' not in handler.response_headers
    assert handler.response_headers['Content-Type'] == 'application/json'
    assert b'Authentication required' in handler.wfile.getvalue()


def test_top_level_plugin_page_keeps_login_flow(monkeypatch):
    monkeypatch.setattr(auth, 'is_auth_enabled', lambda: True)
    handler = Handler()
    assert not auth.check_auth(handler, urlparse('/qa-dashboard'))
    assert handler.status == 302
    assert handler.response_headers['Location'] == 'login?next=/qa-dashboard'
