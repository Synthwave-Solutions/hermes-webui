"""Server-side map tiles for the kit frame (api/map_tiles.py)."""
from __future__ import annotations

import io
import urllib.parse

import pytest

from api import map_tiles

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class _Headers(dict):
    def get(self, key, default=None):
        for k, v in self.items():
            if k.lower() == key.lower():
                return v
        return default


class _Handler:
    def __init__(self, headers=None, peer="100.64.0.7"):
        self.headers = _Headers(headers or {})
        self.client_address = (peer, 5555)
        self.status = None
        self.sent = {}
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.sent[key] = value

    def end_headers(self):
        pass


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(map_tiles, "_cache_dir", lambda: tmp_path)
    map_tiles._rate.clear()
    return tmp_path


@pytest.mark.parametrize("path,expected", [
    ("/static/interactive-ui/tiles/nl/12/2103/1346.png", ("nl", 12, 2103, 1346)),
    ("/session/static/interactive-ui/tiles/world/0/0/0.png", ("world", 0, 0, 0)),
    ("/static/interactive-ui/tiles/nl/2/4/0.png", None),          # x outside the zoom level
    ("/static/interactive-ui/tiles/nl/20/1/1.png", None),         # above max zoom
    ("/static/interactive-ui/tiles/evil/1/0/0.png", None),        # unknown style
    ("/static/interactive-ui/tiles/nl/1/0/0.png?x=1", None),
    ("/static/interactive-ui/tiles/nl/1/0/../0.png", None),
    ("/static/interactive-ui/tiles/nl/1/0/0.jpg", None),
])
def test_paths_are_checked(path, expected):
    assert map_tiles.parse(path) == expected


def test_tile_is_fetched_once_then_served_from_disk(cache, monkeypatch):
    calls = []
    monkeypatch.setattr(map_tiles, "_fetch", lambda *a: calls.append(a) or PNG)
    parsed = urllib.parse.urlparse("/static/interactive-ui/tiles/nl/12/2103/1346.png")
    for _ in range(2):
        h = _Handler()
        assert map_tiles.serve(h, parsed) is True
        assert h.status == 200 and h.wfile.getvalue() == PNG
    assert calls == [("nl", 12, 2103, 1346)]
    assert h.sent["Content-Type"] == "image/png"
    assert h.sent["Cross-Origin-Resource-Policy"] == "cross-origin"
    assert (cache / "nl" / "12" / "2103" / "1346.png").read_bytes() == PNG


def test_upstream_failure_is_a_502_so_the_map_shows_its_note(cache, monkeypatch):
    monkeypatch.setattr(map_tiles, "_fetch", lambda *a: None)
    h = _Handler()
    map_tiles.serve(h, urllib.parse.urlparse("/static/interactive-ui/tiles/world/3/1/1.png"))
    assert h.status == 502


def test_bad_path_is_404_without_a_fetch(cache, monkeypatch):
    monkeypatch.setattr(map_tiles, "_fetch", lambda *a: pytest.fail("no fetch for a bad path"))
    h = _Handler()
    map_tiles.serve(h, urllib.parse.urlparse("/static/interactive-ui/tiles/nl/1/9/9.png"))
    assert h.status == 404


def test_rate_limit_per_client(cache, monkeypatch):
    monkeypatch.setattr(map_tiles, "_fetch", lambda *a: PNG)
    monkeypatch.setattr(map_tiles, "RATE_PER_MINUTE", 3)
    parsed = urllib.parse.urlparse("/static/interactive-ui/tiles/nl/1/0/0.png")
    statuses = []
    for _ in range(4):
        h = _Handler()
        map_tiles.serve(h, parsed)
        statuses.append(h.status)
    assert statuses == [200, 200, 200, 429]
    other = _Handler(peer="100.64.0.8")
    map_tiles.serve(other, parsed)
    assert other.status == 200


def test_forwarded_for_only_counts_from_a_local_proxy():
    assert map_tiles._client(_Handler({"X-Forwarded-For": "1.2.3.4"}, peer="100.64.0.7")) == "100.64.0.7"
    assert map_tiles._client(_Handler({"X-Forwarded-For": "1.2.3.4"}, peer="127.0.0.1")) == "1.2.3.4"


def test_fetch_refuses_redirects_and_non_png(monkeypatch):
    class _Resp:
        def __init__(self, ctype, body):
            self.status = 200
            self.headers = {"Content-Type": ctype}
            self._body = body

        def read(self, n):
            return self._body[:n]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    seen = {}

    class _Opener:
        def __init__(self, resp):
            self.resp = resp

        def open(self, request, timeout):
            seen["ua"] = request.get_header("User-agent")
            seen["url"] = request.full_url
            return self.resp

    import urllib.request
    monkeypatch.setattr(urllib.request, "build_opener", lambda *h: (seen.setdefault("handlers", h), _Opener(_Resp("text/html", b"<html>")))[1])
    assert map_tiles._fetch("nl", 1, 0, 0) is None
    from api import map_resolve
    assert map_resolve._NoRedirect in seen["handlers"]
    assert seen["url"].startswith("https://service.pdok.nl/") and seen["ua"] == map_resolve.user_agent()
    monkeypatch.setattr(urllib.request, "build_opener", lambda *h: _Opener(_Resp("image/png", PNG)))
    assert map_tiles._fetch("world", 1, 0, 0) == PNG
    assert seen["url"] == "https://tile.openstreetmap.org/1/0/0.png"
