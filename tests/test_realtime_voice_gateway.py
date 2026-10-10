"""Realtime voice and the model gateway (plan 3.12, D58 (b), package R3).

Under model gateway enforcement (``SP_MODEL_GATEWAY_ENFORCE=1`` or the
engine's ``model_gateway.enforce``) the realtime voice routes answer ``409``
with ``code: gateway_required`` and never reach the provider, unless the
gateway carries a realtime route (``SP_MODEL_GATEWAY_REALTIME=1``), in which
case the call, its sideband socket and its hangup go to the gateway with the
profile's own gateway key. Without enforcement the direct route is unchanged.
"""

import io
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import api.profiles as profiles
from api import realtime_voice as voice
from api import realtime_voice_runtime as runtime

_GATEWAY = "http://gateway.test:4000/v1"


class Handler:
    command = "POST"

    def __init__(self, body=None):
        data = json.dumps(body or {}).encode()
        self.rfile = io.BytesIO(data)
        self.wfile = io.BytesIO()
        self.headers = {"Content-Length": str(len(data)), "Content-Type": "application/json"}
        self.status = None

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        pass

    def end_headers(self):
        pass

    def payload(self):
        return json.loads(self.wfile.getvalue())


def _answer(url, **kw):
    return SimpleNamespace(status_code=201, text="v=0\nanswer",
                           headers={"Location": "/v1/realtime/calls/rtc_fixture"})


@pytest.fixture(autouse=True)
def isolation(monkeypatch, tmp_path):
    for name in ("SP_MODEL_GATEWAY_ENFORCE", "SP_MODEL_GATEWAY_URL", "SP_MODEL_GATEWAY_REALTIME",
                 "SP_MODEL_GATEWAY_AUDIO", "SP_MODEL_GATEWAY_KEY_FILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(profiles, "_INITIAL_GATEWAY_ENFORCE", "", raising=False)
    monkeypatch.setattr(profiles, "_INITIAL_GATEWAY_KEY_FILE", "", raising=False)
    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", base)
    monkeypatch.setattr(profiles, "get_active_hermes_home", lambda: base)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-direct-provider-key")
    monkeypatch.setenv("SYNPULSE_REALTIME_VOICE_ENABLED", "1")
    voice._ATTEMPTS.clear()
    yield base


def _enforce(monkeypatch):
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")


def _gateway_realtime(monkeypatch, tmp_path, key="gw-profile-key"):
    key_file = tmp_path / "gateway.key"
    key_file.write_text(key + "\n", encoding="utf-8")
    monkeypatch.setattr(profiles, "_INITIAL_GATEWAY_KEY_FILE", str(key_file))
    monkeypatch.setenv("SP_MODEL_GATEWAY_URL", _GATEWAY)
    monkeypatch.setenv("SP_MODEL_GATEWAY_REALTIME", "1")


def _signed_in(monkeypatch, *, visible=True):
    from api import routes
    from api.governance import enforce
    monkeypatch.setattr(enforce, "_request_identity", lambda h: {"email": "alice@example.test"})
    monkeypatch.setattr(routes, "get_session", lambda *a, **kw: SimpleNamespace())
    monkeypatch.setattr(routes, "_session_visible_to_request", lambda *a: visible)
    monkeypatch.setattr(runtime, "voice_access", lambda h: voice.configured())


# ── Without enforcement the direct route is unchanged ───────────────────────


def test_direct_route_without_enforcement():
    route = voice.realtime_route()
    assert route.kind == "direct"
    assert voice.configured() is True
    calls = []

    def post(url, **kw):
        calls.append((url, kw))
        return _answer(url, **kw)

    assert voice.create_call("v=0\noffer", "alice", post=post) == ("v=0\nanswer", "rtc_fixture")
    assert calls[0][0] == "https://api.openai.com/v1/realtime/calls"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer sk-direct-provider-key"
    assert voice.sideband_url(route, "rtc_fixture") == "wss://api.openai.com/v1/realtime?call_id=rtc_fixture"


# ── Under enforcement without a realtime route: refused, never reached ─────


def test_enforced_without_realtime_route_is_not_configured(monkeypatch):
    _enforce(monkeypatch)
    assert voice.realtime_route().kind == "refused"
    # The provider key is present, yet voice is off: it is never used.
    assert voice.configured() is False


def test_enforced_config_of_the_active_profile_refuses(monkeypatch, isolation):
    (isolation / "config.yaml").write_text(yaml.safe_dump({"model_gateway": {"enforce": True}}), encoding="utf-8")
    assert voice.realtime_route().kind == "refused"
    assert voice.configured() is False


def test_create_call_refuses_and_never_posts(monkeypatch):
    _enforce(monkeypatch)

    def post(*a, **k):
        pytest.fail("the provider must not be called under enforcement")

    with pytest.raises(voice.RealtimeGatewayRequired):
        voice.create_call("v=0\noffer", "alice", post=post)


def test_call_route_answers_409_gateway_required(monkeypatch):
    _enforce(monkeypatch)
    _signed_in(monkeypatch)
    monkeypatch.setattr(voice, "create_call", lambda *a, **k: pytest.fail("no call under enforcement"))
    handler = Handler({"session_id": "voicefixture1", "sdp": "v=0"})
    voice.handle(handler)
    assert handler.status == 409
    body = handler.payload()
    assert body["code"] == "gateway_required"
    assert body["message_key"] == "voice_live_unavailable"
    assert body["error"] == "Live voice is not available on this platform."


def test_capability_answers_409_with_available_false(monkeypatch):
    _enforce(monkeypatch)
    _signed_in(monkeypatch)
    handler = Handler()
    voice.handle(handler, capability=True)
    assert handler.status == 409
    body = handler.payload()
    assert body["available"] is False
    assert body["code"] == "gateway_required"


def test_status_answers_409_under_enforcement(monkeypatch):
    _enforce(monkeypatch)
    _signed_in(monkeypatch)
    handler = Handler()
    handler.command = "GET"
    voice.handle_status(handler, SimpleNamespace(query="voice_id=anything"))
    assert handler.status == 409
    assert handler.payload()["code"] == "gateway_required"


def test_unauthenticated_request_is_still_401_first(monkeypatch):
    _enforce(monkeypatch)
    from api.governance import enforce
    monkeypatch.setattr(enforce, "_request_identity", lambda h: None)
    handler = Handler({"session_id": "voicefixture1", "sdp": "v=0"})
    voice.handle(handler)
    assert handler.status == 401


def test_controller_never_opens_a_refused_route(monkeypatch, tmp_path):
    _enforce(monkeypatch)

    class Bridge:
        actor, session_id = "alice@example.test", "parent"

        def check(self):
            return {}

    def connector(*a, **k):
        pytest.fail("no sideband socket under enforcement")

    controller = runtime.VoiceController(Bridge(), "rtc_x", connector=connector, journal_dir=tmp_path)
    monkeypatch.setattr(voice, "hangup_call", lambda *a, **k: None)
    with pytest.raises(PermissionError):
        controller.start()
    controller.close()


def test_a_direct_call_ends_when_enforcement_turns_on(monkeypatch, tmp_path):
    class Bridge:
        actor, session_id = "alice@example.test", "parent"

        def check(self):
            return {}

    hangups = []
    monkeypatch.setattr(voice, "hangup_call", lambda *a, **k: hangups.append(a))
    controller = runtime.VoiceController(Bridge(), "rtc_x", journal_dir=tmp_path)
    controller.route = voice.realtime_route()
    assert controller.route.kind == "direct"
    controller.check()
    _enforce(monkeypatch)
    with pytest.raises(PermissionError):
        controller.check()
    controller.close()
    assert hangups and hangups[0][0] == "rtc_x"


# ── Under enforcement with a realtime route: only the gateway ───────────────


def test_gateway_route_posts_to_the_gateway_with_the_profile_key(monkeypatch, tmp_path):
    _enforce(monkeypatch)
    _gateway_realtime(monkeypatch, tmp_path)
    route = voice.realtime_route()
    assert route.kind == "gateway"
    assert voice.configured() is True
    calls = []

    def post(url, **kw):
        calls.append((url, kw))
        return _answer(url, **kw)

    voice.create_call("v=0\noffer", "alice", post=post, route=route)
    assert calls[0][0] == _GATEWAY + "/realtime/calls"
    headers = calls[0][1]["headers"]
    assert headers["Authorization"] == "Bearer gw-profile-key"
    assert "sk-direct-provider-key" not in json.dumps(calls[0][1], default=str)
    voice.hangup_call("rtc_fixture", route, post=post)
    assert calls[1][0] == _GATEWAY + "/realtime/calls/rtc_fixture/hangup"
    assert calls[1][1]["headers"]["Authorization"] == "Bearer gw-profile-key"
    assert voice.sideband_url(route, "rtc_fixture") == "ws://gateway.test:4000/v1/realtime?call_id=rtc_fixture"


def test_gateway_route_socket_goes_to_the_gateway(monkeypatch, tmp_path):
    _enforce(monkeypatch)
    _gateway_realtime(monkeypatch, tmp_path)

    class Bridge:
        actor, session_id = "alice@example.test", "parent"

        def check(self):
            return {}

    opened = []

    class _Socket:
        def recv(self, timeout=1):
            raise TimeoutError

        def send(self, value):
            pass

        def close(self):
            pass

    def connector(url, **kw):
        opened.append((url, kw))
        return _Socket()

    monkeypatch.setattr(voice, "hangup_call", lambda *a, **k: None)
    controller = runtime.VoiceController(Bridge(), "rtc_x", connector=connector, journal_dir=tmp_path)
    controller.route = voice.realtime_route()
    controller.start()
    try:
        assert opened[0][0] == "ws://gateway.test:4000/v1/realtime?call_id=rtc_x"
        assert opened[0][1]["additional_headers"]["Authorization"] == "Bearer gw-profile-key"
        assert opened[0][1]["proxy"] is None
    finally:
        controller.close()


def test_gateway_route_through_the_handler(monkeypatch, tmp_path):
    _enforce(monkeypatch)
    _gateway_realtime(monkeypatch, tmp_path)
    _signed_in(monkeypatch)
    routes_seen = []

    def create_call(*args, **kwargs):
        routes_seen.append(kwargs.get("route"))
        return ("v=0\nanswer", "rtc_fixture")

    class Controller:
        voice_id = "opaque"

        def __init__(self, bridge, call_id):
            self.route = None

        def start(self):
            routes_seen.append(self.route)

        def check(self):
            pass

        def close(self):
            pass

    class Bridge:
        def __init__(self, *a):
            pass

        def check(self):
            return {}

    monkeypatch.setattr(voice, "create_call", create_call)
    monkeypatch.setattr(runtime, "VoiceController", Controller)
    monkeypatch.setattr(runtime, "LoopbackBridge", Bridge)
    monkeypatch.setattr(runtime, "register", lambda c: None)
    handler = Handler({"session_id": "voicefixture1", "sdp": "v=0"})
    voice.handle(handler)
    assert handler.status == 200
    assert [r.kind for r in routes_seen] == ["gateway", "gateway"]


def test_gateway_realtime_without_a_key_is_not_configured(monkeypatch):
    _enforce(monkeypatch)
    monkeypatch.setenv("SP_MODEL_GATEWAY_URL", _GATEWAY)
    monkeypatch.setenv("SP_MODEL_GATEWAY_REALTIME", "1")
    assert voice.realtime_route().kind == "gateway"
    assert voice.configured() is False


def test_realtime_flag_without_a_gateway_address_is_refused_under_enforcement(monkeypatch):
    _enforce(monkeypatch)
    monkeypatch.setenv("SP_MODEL_GATEWAY_REALTIME", "1")
    assert voice.realtime_route().kind == "refused"


def test_engine_realtime_setting_counts_as_the_gateway_route(monkeypatch, tmp_path, isolation):
    key_file = tmp_path / "k"
    key_file.write_text("gw-config-key", encoding="utf-8")
    (isolation / "config.yaml").write_text(yaml.safe_dump({"model_gateway": {
        "enforce": True, "realtime": True, "base_url": _GATEWAY, "key_file": str(key_file)}}), encoding="utf-8")
    route = voice.realtime_route()
    assert route.kind == "gateway" and route.base_url == _GATEWAY
    assert voice.configured() is True


def test_gateway_realtime_is_used_even_without_enforcement(monkeypatch, tmp_path):
    _gateway_realtime(monkeypatch, tmp_path)
    assert voice.realtime_route().kind == "gateway"


# ── Copy ────────────────────────────────────────────────────────────────────


def test_message_matches_the_e71_i18n_key():
    en = Path("static/i18n/en.js").read_text(encoding="utf-8")
    match = re.search(r"voice_live_unavailable:\s*'([^']*)'", en)
    assert match and match.group(1) == voice.LIVE_VOICE_UNAVAILABLE
    assert voice.LIVE_VOICE_UNAVAILABLE_KEY == "voice_live_unavailable"
