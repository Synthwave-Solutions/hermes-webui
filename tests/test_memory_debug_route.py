import io
import json
from types import SimpleNamespace
from urllib.parse import urlparse


class _FakeHandler:
    def __init__(self):
        self.status = None
        self.headers = {}
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.headers[key] = value

    def end_headers(self):
        pass

    def json_body(self):
        return json.loads(self.wfile.getvalue().decode("utf-8"))


def test_memory_debug_route_reports_session_route_cache_and_rss(monkeypatch):
    from api import config, route_session_list_cache as slc, routes

    original_sessions = config.SESSIONS
    original_routes_sessions = routes.SESSIONS
    config.SESSIONS = routes.SESSIONS = type(original_sessions)()
    session = SimpleNamespace(session_id="large-session", _cache_estimated_bytes=12345)
    config.SESSIONS[session.session_id] = session
    slc._session_list_cache_clear()
    key = slc._session_list_cache_key("default", False, False, False, False)
    slc._session_list_cache_set(key, {"sessions": [{"session_id": "large-session"}]})
    monkeypatch.setattr(routes, "_process_rss_bytes", lambda: 987654, raising=False)

    try:
        handler = _FakeHandler()
        assert routes.handle_get(handler, urlparse("/api/debug/memory")) is True
        payload = handler.json_body()
        assert handler.status == 200
        assert payload["session_cache_items"] == 1
        assert payload["session_cache_total_bytes"] == 12345
        assert payload["session_cache_top_bytes"] == [
            {"session_id": "large-session", "estimated_bytes": 12345}
        ]
        assert payload["route_cache_items"] == 1
        assert payload["process_rss_bytes"] == 987654
    finally:
        slc._session_list_cache_clear()
        config.SESSIONS = original_sessions
        routes.SESSIONS = original_routes_sessions


def test_session_list_cache_uses_an_immutable_snapshot_without_deepcopy():
    from api import route_session_list_cache as slc

    slc._session_list_cache_clear()
    key = slc._session_list_cache_key("default", False, False, False, False)
    payload = {"sessions": [{"session_id": "one", "title": "Original"}]}
    slc._session_list_cache_set(key, payload)
    cached, _fresh = slc._session_list_cache_get(key, allow_stale=True)

    payload["sessions"][0]["title"] = "Mutated"
    assert cached["sessions"][0]["title"] == "Original"
    try:
        cached["sessions"][0]["title"] = "Forbidden"
    except TypeError:
        pass
    else:
        raise AssertionError("cached snapshots must be immutable")
    slc._session_list_cache_clear()
