import io
import json
from types import SimpleNamespace

import pytest

from api import realtime_voice as voice


class Handler:
    command = "POST"
    def __init__(self, body=None):
        data = json.dumps(body or {}).encode()
        self.rfile = io.BytesIO(data)
        self.wfile = io.BytesIO()
        self.headers = {"Content-Length": str(len(data)), "Content-Type": "application/json"}
        self.status = None
    def send_response(self, status): self.status = status
    def send_header(self, key, value): pass
    def end_headers(self): pass
    def payload(self): return json.loads(self.wfile.getvalue())


@pytest.fixture(autouse=True)
def isolation(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-key")
    monkeypatch.setenv("SYNPULSE_REALTIME_VOICE_ENABLED", "1")
    voice._ATTEMPTS.clear()
    from api import realtime_voice_runtime as runtime, routes
    monkeypatch.setattr(runtime, "voice_access", lambda h: voice.configured())
    class Bridge:
        def __init__(self, handler, actor, sid): self.handler = handler
        def check(self):
            if not routes._session_visible_to_request(SimpleNamespace(), self.handler):
                raise PermissionError("revoked")
    class Controller:
        voice_id = "opaque-voice"
        def __init__(self, bridge, call_id): self.bridge = bridge
        def check(self): return self.bridge.check()
        def start(self): pass
        def close(self): pass
    monkeypatch.setattr(runtime, "LoopbackBridge", Bridge)
    monkeypatch.setattr(runtime, "VoiceController", Controller)
    monkeypatch.setattr(runtime, "register", lambda c: None)


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SYNPULSE_REALTIME_VOICE_ENABLED")
    assert not voice.configured()


def test_sdp_exchange_keeps_key_server_only_and_native_tools_enabled():
    calls = []
    def post(url, **kw):
        calls.append((url, kw))
        return SimpleNamespace(status_code=201, text="v=0\nanswer", headers={"Location":"/v1/realtime/calls/rtc_fixture"})
    answer = voice.create_call("v=0\noffer", "alice", post=post)
    assert answer == ("v=0\nanswer", "rtc_fixture")
    assert "fixture-key" not in answer
    config = json.loads(calls[0][1]["files"]["session"][1])
    assert {tool["name"] for tool in config["tools"]} == {"dispatch_work", "get_work_status"}
    assert config["audio"]["input"]["turn_detection"]["create_response"] is True
    assert calls[0][1]["headers"]["OpenAI-Safety-Identifier"] != "alice"
    assert calls[0][1]["timeout"] == 25


def test_provider_error_does_not_echo_secret_or_response():
    def post(*a, **kw):
        return SimpleNamespace(status_code=401, text="fixture-key upstream secret")
    with pytest.raises(RuntimeError, match="unavailable") as exc:
        voice.create_call("v=0", "alice", post=post)
    assert "fixture-key" not in str(exc.value)


def test_invalid_sdp_never_calls_provider():
    def post(*a, **kw): pytest.fail("must not call")
    for value in ("https://attacker", "v=0" + "x"*65536, {}, None):
        with pytest.raises(ValueError):
            voice.create_call(value, "alice", post=post)


def test_rate_limit_is_actor_scoped():
    post = lambda *a, **kw: SimpleNamespace(status_code=201, text="v=0", headers={"Location":"/v1/realtime/calls/rtc_fixture"})
    for _ in range(4): voice.create_call("v=0", "alice", post=post)
    with pytest.raises(ValueError, match="one minute"):
        voice.create_call("v=0", "alice", post=post)
    assert voice.create_call("v=0", "bob", post=post) == ("v=0", "rtc_fixture")


@pytest.mark.parametrize("identity,visible,status", [(None, True, 401),
    ({"email":"outsider@example.test"}, False, 404),
    ({"email":"alice@example.test"}, True, 200)])
def test_handler_auth_and_session_boundary(monkeypatch, identity, visible, status):
    from api import routes
    from api.governance import enforce
    monkeypatch.setattr(enforce, "_request_identity", lambda h: identity)
    monkeypatch.setattr(routes, "get_session", lambda *a, **kw: SimpleNamespace())
    monkeypatch.setattr(routes, "_session_visible_to_request", lambda *a: visible)
    monkeypatch.setattr(voice, "create_call", lambda *a, **kw: ("v=0\nanswer", "rtc_fixture"))
    handler = Handler({"session_id":"voicefixture1", "sdp":"v=0"})
    voice.handle(handler)
    assert handler.status == status
    if status == 200: assert handler.payload()["sdp"] == "v=0\nanswer"


def test_revocation_during_negotiation_denies_answer(monkeypatch):
    from api import routes
    from api.governance import enforce
    monkeypatch.setattr(enforce, "_request_identity", lambda h: {"email":"alice@example.test"})
    monkeypatch.setattr(routes, "get_session", lambda *a, **kw: SimpleNamespace())
    checks = iter([True, False])
    monkeypatch.setattr(routes, "_session_visible_to_request", lambda *a: next(checks))
    monkeypatch.setattr(voice, "create_call", lambda *a, **kw: ("v=0\nanswer", "rtc_fixture"))
    handler = Handler({"session_id":"voicefixture1", "sdp":"v=0"})
    voice.handle(handler)
    assert handler.status == 404
    assert "sdp" not in handler.payload()


def test_real_post_dispatch_requires_csrf(monkeypatch):
    from urllib.parse import urlparse
    from api import routes
    handler = Handler()
    monkeypatch.setattr(routes, "_check_csrf", lambda h: False)
    monkeypatch.setattr(routes, "_csrf_rejection_error", lambda h: "csrf")
    monkeypatch.setattr(voice, "create_call", lambda *a: pytest.fail("no provider call"))
    routes.handle_post(handler, urlparse("/api/voice/realtime/call"))
    assert handler.status == 403


def test_voice_routes_require_chat_permission():
    from api.governance.catalog import route_permission
    assert route_permission("/api/voice/realtime/call", "POST") == "chat:use"
    assert route_permission("/api/voice/realtime/capability", "GET") == "chat:use"

def test_revoke_negotiated_call_hangs_up_without_returning_sdp():
    calls = []
    def post(url, **kw):
        calls.append(url)
        return SimpleNamespace(status_code=201, text="v=0", headers={"Location": "/v1/realtime/calls/rtc_fixture"})
    with pytest.raises(PermissionError):
        voice.create_call("v=0", "alice", post=post, access_check=lambda: False)
    assert calls[-1] == "https://api.openai.com/v1/realtime/calls/rtc_fixture/hangup"


def test_user_voice_capability_and_disabled_errors_are_provider_neutral(monkeypatch):
    from api import routes
    from api.governance import enforce
    monkeypatch.setattr(enforce, "_request_identity", lambda h: {"email":"alice@example.test"})
    monkeypatch.setattr(routes, "get_session", lambda *a, **kw: SimpleNamespace())
    monkeypatch.setattr(routes, "_session_visible_to_request", lambda *a: True)
    monkeypatch.delenv("SYNPULSE_REALTIME_VOICE_ENABLED")
    for capability in (True, False):
        handler = Handler({"session_id":"voicefixture1", "sdp":"v=0"})
        voice.handle(handler, capability=capability)
        assert handler.status == (200 if capability else 503)
        visible = json.dumps(handler.payload()).lower()
        assert "openai" not in visible
        assert "api key" not in visible
        assert "billing" not in visible
