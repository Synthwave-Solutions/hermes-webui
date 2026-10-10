"""``/api/tts`` through the engine's TTS tool (plan 3.12, package R3).

``api/tts_backend.py`` keeps no provider URL or key of its own: the ElevenLabs
and OpenAI engines run through the engine's ``text_to_speech_tool`` in process,
inside the active profile's env. Under model gateway enforcement every server
engine (Edge included) is the gateway's audio route with the profile's key,
and ``409 gateway_required`` when the gateway carries no audio route or the
engine cannot guarantee that route.
"""

import io
import json
import os
import sys
import types
from pathlib import Path

import pytest

import api.profiles as profiles
import api.routes as routes
from api import tts_backend


class _Handler:
    def __init__(self, body=None, command="POST", client="7.7.7.7"):
        data = json.dumps(body or {}).encode()
        self.command = command
        self.rfile = io.BytesIO(data)
        self.wfile = io.BytesIO()
        self.headers = {"Content-Length": str(len(data))}
        self.client_address = (client, 1234)
        self.status = None
        self.sent_headers = {}

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.sent_headers[key] = value

    def end_headers(self):
        pass

    def payload(self):
        return json.loads(self.wfile.getvalue().decode("utf-8"))


class _FakeEngine:
    """Stands in for tools.tts_tool.text_to_speech_tool; writes real files."""

    def __init__(self, *, parts=(b"ID3engine-audio",), suffix=".mp3", result=None):
        self.calls = []
        self.parts = parts
        self.suffix = suffix
        self.result = result
        self.env_seen = {}

    def __call__(self, text, output_path=None, speed=None, instructions=None, provider=None):
        self.calls.append({"text": text, "output_path": output_path, "provider": provider})
        self.env_seen = {k: os.environ.get(k) for k in ("OPENAI_API_KEY", "HERMES_HOME")}
        if self.result is not None:
            return json.dumps(self.result)
        base = Path(output_path)
        paths = []
        for index, data in enumerate(self.parts, start=1):
            path = base if len(self.parts) == 1 else base.with_name(f"{base.stem}.part{index:02d}{self.suffix}")
            path = path.with_suffix(self.suffix)
            path.write_bytes(data)
            paths.append(str(path))
        return json.dumps({"success": True, "file_path": paths[0], "file_paths": paths, "provider": provider})


class _FakeGatewayModule:
    def __init__(self, enforced=True, base_url="http://gateway.test:4000/v1"):
        self._enforced = enforced
        self._base = base_url

    def enforced(self, config=None):
        return self._enforced

    def gateway_base_url(self, config=None):
        return self._base


@pytest.fixture(autouse=True)
def isolation(monkeypatch, tmp_path):
    for name in ("SP_MODEL_GATEWAY_ENFORCE", "SP_MODEL_GATEWAY_URL", "SP_MODEL_GATEWAY_AUDIO",
                 "SP_MODEL_GATEWAY_KEY_FILE", "SP_MODEL_GATEWAY_REALTIME",
                 "ELEVENLABS_API_KEY", "OPENAI_API_KEY", "VOICE_TOOLS_OPENAI_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(profiles, "_INITIAL_GATEWAY_ENFORCE", "", raising=False)
    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", base)
    monkeypatch.setattr(profiles, "get_active_hermes_home", lambda: base)
    import api.auth as auth
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: False)
    if hasattr(routes._handle_tts, "_tts_limiter"):
        del routes._handle_tts._tts_limiter
    import api.config as config
    monkeypatch.setattr(config, "get_config", lambda: {"tts": {"elevenlabs": {"voice_id": "pNInz6obpgDQGcFmaJgB"}}})
    yield base
    if hasattr(routes._handle_tts, "_tts_limiter"):
        del routes._handle_tts._tts_limiter


_DEFAULT_GATEWAY = _FakeGatewayModule()


def _use_engine(monkeypatch, engine, gateway=_DEFAULT_GATEWAY):
    monkeypatch.setattr(tts_backend, "_engine_text_to_speech", lambda: engine)
    monkeypatch.setattr(tts_backend, "_engine_model_gateway", lambda: gateway)


def _enforce(monkeypatch, *, audio):
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")
    if audio:
        monkeypatch.setenv("SP_MODEL_GATEWAY_AUDIO", "1")
        monkeypatch.setenv("SP_MODEL_GATEWAY_URL", "http://gateway.test:4000/v1")


# ── Without enforcement: the engine's tool, the requested engine ────────────


@pytest.mark.parametrize("engine", ["elevenlabs", "openai"])
def test_provider_engines_run_through_the_engine_tool(monkeypatch, engine):
    _enforce(monkeypatch, audio=True)
    fake = _FakeEngine()
    _use_engine(monkeypatch, fake)
    handler = _Handler()
    assert tts_backend.synthesize(handler, "Hello world", engine, "en-US-AriaNeural") is True
    assert handler.status == 200
    assert handler.sent_headers["Content-Type"] == "audio/mpeg"
    assert handler.sent_headers["Content-Length"] == str(len(b"ID3engine-audio"))
    assert handler.sent_headers["Cache-Control"] == "no-store"
    assert handler.wfile.getvalue() == b"ID3engine-audio"
    assert fake.calls == [{"text": "Hello world", "output_path": fake.calls[0]["output_path"], "provider": "openai"}]
    # The scratch files are gone after the response.
    assert not Path(fake.calls[0]["output_path"]).parent.exists()


def test_edge_is_not_a_server_engine_without_enforcement(monkeypatch):
    fake = _FakeEngine()
    _use_engine(monkeypatch, fake)
    assert "edge" not in tts_backend.SERVER_ENGINES
    assert "elevenlabs" in tts_backend.SERVER_ENGINES
    assert "openai" in tts_backend.SERVER_ENGINES
    assert tuple(tts_backend.SERVER_ENGINES) == ("elevenlabs", "openai")
    handler = _Handler()
    assert tts_backend.synthesize(handler, "Hello", "edge", "en-US-AriaNeural") is False
    assert handler.status is None and not fake.calls


def test_the_engine_runs_inside_the_active_profile_env(monkeypatch):
    _enforce(monkeypatch, audio=True)
    entered = []

    class _Scope:
        def __init__(self, purpose, logger_override=None):
            entered.append(purpose)

        def __enter__(self):
            os.environ["R3_PROFILE_SCOPE_MARK"] = "1"

        def __exit__(self, *exc):
            os.environ.pop("R3_PROFILE_SCOPE_MARK", None)
            return False

    seen = {}

    def engine(text, output_path=None, provider=None, **kw):
        seen["mark"] = os.environ.get("R3_PROFILE_SCOPE_MARK")
        Path(output_path).write_bytes(b"ID3x")
        return json.dumps({"success": True, "file_path": output_path})

    monkeypatch.setattr(profiles, "profile_env_for_active_request", _Scope)
    _use_engine(monkeypatch, engine)
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "openai", "")
    assert entered == ["/api/tts"]
    assert seen["mark"] == "1"
    assert handler.status == 200


def test_gateway_credentials_failure_is_redacted(monkeypatch):
    _enforce(monkeypatch, audio=True)
    fake = _FakeEngine(result={"success": False, "error": "TTS chunk 1 failed (elevenlabs): TTS configuration error (elevenlabs): ELEVENLABS_API_KEY not set. Get one at https://elevenlabs.io/"})
    _use_engine(monkeypatch, fake)
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "elevenlabs", "")
    assert handler.status == 502
    assert handler.payload()["error"] == "Speech generation failed"

    fake = _FakeEngine(result={"success": False, "error": "TTS configuration error (openai): No OpenAI API key found"})
    _use_engine(monkeypatch, fake)
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "openai", "")
    assert handler.status == 502
    assert handler.payload()["error"] == "Speech generation failed"


def test_engine_failure_is_502_and_never_echoes_upstream_text(monkeypatch):
    _enforce(monkeypatch, audio=True)
    fake = _FakeEngine(result={"success": False, "error": "TTS generation failed (openai): upstream said sk-secret-123 at /home/x"})
    _use_engine(monkeypatch, fake)
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "openai", "")
    assert handler.status == 502
    body = handler.payload()
    assert body["error"] == "Speech generation failed"
    assert "sk-secret" not in json.dumps(body)


def test_engine_tool_unavailable_is_503(monkeypatch):
    _enforce(monkeypatch, audio=True)
    def _missing():
        raise ImportError("No module named 'tools.tts_tool'")

    monkeypatch.setattr(tts_backend, "_engine_text_to_speech", _missing)
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "elevenlabs", "")
    assert handler.status == 503


def test_unsafe_elevenlabs_voice_id_in_config_is_refused_before_the_engine(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "synthetic-key")
    import api.config as config
    monkeypatch.setattr(config, "get_config", lambda: {"tts": {"elevenlabs": {"voice_id": "../../etc/passwd"}}})
    fake = _FakeEngine()
    _use_engine(monkeypatch, fake)
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "elevenlabs", "")
    assert handler.status == 400
    assert "voice_id" in handler.payload()["error"]
    assert not fake.calls


def test_oversized_audio_is_refused(monkeypatch):
    _enforce(monkeypatch, audio=True)
    monkeypatch.setattr(routes, "_TTS_PROXY_MAX_BYTES", 4)
    _use_engine(monkeypatch, _FakeEngine(parts=(b"12345",)))
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "openai", "")
    assert handler.status == 502


def test_mp3_parts_are_joined_in_order(monkeypatch):
    _enforce(monkeypatch, audio=True)
    _use_engine(monkeypatch, _FakeEngine(parts=(b"ID3one", b"ID3two")))
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "openai", "")
    assert handler.status == 200
    assert handler.wfile.getvalue() == b"ID3oneID3two"


def test_non_mp3_audio_keeps_its_content_type(monkeypatch):
    _enforce(monkeypatch, audio=True)
    _use_engine(monkeypatch, _FakeEngine(parts=(b"RIFFwav",), suffix=".wav"))
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "openai", "")
    assert handler.status == 200
    assert handler.sent_headers["Content-Type"] == "audio/wav"


def test_a_file_outside_the_scratch_directory_is_never_read(monkeypatch, tmp_path):
    _enforce(monkeypatch, audio=True)
    outside = tmp_path / "secret.mp3"
    outside.write_bytes(b"not for the browser")
    _use_engine(monkeypatch, _FakeEngine(result={"success": True, "file_path": str(outside)}))
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "openai", "")
    assert handler.status == 502
    assert b"not for the browser" not in handler.wfile.getvalue()


# ── Under enforcement: only the gateway's audio route ───────────────────────


@pytest.mark.parametrize("engine", ["elevenlabs", "openai", "edge"])
def test_enforced_without_an_audio_route_is_409_and_never_runs_the_engine(monkeypatch, engine):
    _enforce(monkeypatch, audio=False)
    fake = _FakeEngine()
    _use_engine(monkeypatch, fake, _FakeGatewayModule())
    assert engine in tts_backend.SERVER_ENGINES
    handler = _Handler()
    assert tts_backend.synthesize(handler, "Hi", engine, "en-US-AriaNeural") is True
    assert handler.status == 409
    body = handler.payload()
    assert body["code"] == "gateway_required"
    assert body["error"] == tts_backend.GATEWAY_UNAVAILABLE_MESSAGE
    assert not fake.calls


@pytest.mark.parametrize("engine", ["elevenlabs", "openai", "edge"])
def test_enforced_with_an_audio_route_uses_the_gateway_for_every_engine(monkeypatch, engine):
    _enforce(monkeypatch, audio=True)
    fake = _FakeEngine()
    _use_engine(monkeypatch, fake, _FakeGatewayModule())
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", engine, "en-US-AriaNeural")
    assert handler.status == 200
    assert [c["provider"] for c in fake.calls] == ["openai"]


def test_enforced_config_in_the_active_profile_counts(monkeypatch, isolation):
    (isolation / "config.yaml").write_text("model_gateway:\n  enforce: true\n", encoding="utf-8")
    fake = _FakeEngine()
    _use_engine(monkeypatch, fake, _FakeGatewayModule())
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "openai", "")
    assert handler.status == 409
    assert not fake.calls


@pytest.mark.parametrize("gateway", [None, _FakeGatewayModule(enforced=False), _FakeGatewayModule(base_url="")])
def test_enforced_but_engine_cannot_guarantee_the_gateway_is_409(monkeypatch, gateway):
    _enforce(monkeypatch, audio=True)
    fake = _FakeEngine()
    _use_engine(monkeypatch, fake, gateway)
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "openai", "")
    assert handler.status == 409
    assert handler.payload()["code"] == "gateway_required"
    assert not fake.calls


@pytest.mark.parametrize("result", [
    {"success": False, "error": "refused", "error_code": "gateway_required"},
    {"success": False, "error": "TTS chunk 1 failed (openai): TTS configuration error (openai): gateway_required: tts backend 'openai' is not allowed; no gateway key is configured"},
])
def test_engine_refusal_under_enforcement_is_409(monkeypatch, result):
    _enforce(monkeypatch, audio=True)
    _use_engine(monkeypatch, _FakeEngine(result=result), _FakeGatewayModule())
    handler = _Handler()
    tts_backend.synthesize(handler, "Hi", "openai", "")
    assert handler.status == 409
    assert handler.payload()["code"] == "gateway_required"


def test_route_sends_edge_to_the_backend_under_enforcement(monkeypatch):
    """The route's own Edge branch (a direct call to a speech provider) is never reached."""
    _enforce(monkeypatch, audio=False)
    broken_edge = types.ModuleType("edge_tts")

    def _refuse(*a, **k):
        raise AssertionError("Edge TTS reached under enforcement")

    broken_edge.Communicate = _refuse
    monkeypatch.setitem(sys.modules, "edge_tts", broken_edge)
    fake = _FakeEngine()
    _use_engine(monkeypatch, fake, _FakeGatewayModule())
    handler = _Handler({"text": "Hello", "engine": "edge", "voice": "en-US-AriaNeural"})
    routes._handle_tts(handler, None)
    assert handler.status == 409
    assert handler.payload()["code"] == "gateway_required"


def test_route_keeps_edge_in_the_route_without_enforcement(monkeypatch):
    calls = []

    class _Communicate:
        def __init__(self, text, voice, **kw):
            calls.append(voice)

        def stream_sync(self):
            yield {"type": "audio", "data": b"ID3edge"}

    edge = types.ModuleType("edge_tts")
    edge.Communicate = _Communicate
    monkeypatch.setitem(sys.modules, "edge_tts", edge)
    fake = _FakeEngine()
    _use_engine(monkeypatch, fake)
    handler = _Handler({"text": "Hello", "engine": "edge", "voice": "en-US-AriaNeural"})
    routes._handle_tts(handler, None)
    assert handler.status == 200
    assert calls == ["en-US-AriaNeural"]
    assert not fake.calls


def test_the_backend_holds_no_provider_url_or_key():
    source = Path(tts_backend.__file__).read_text(encoding="utf-8")
    for needle in ("api.elevenlabs.io", "api.openai.com", "ELEVENLABS_API_KEY\")",
                   "getenv(\"OPENAI_API_KEY", "VOICE_TOOLS_OPENAI_KEY", "xi-api-key", "Bearer "):
        assert needle not in source, needle


def test_gateway_message_matches_the_copy_rules():
    message = tts_backend.GATEWAY_UNAVAILABLE_MESSAGE
    assert "\u2014" not in message and "\u2013" not in message
    for name in ("n8n", "OmniRoute", "LangGraph", "Hermes", "LiteLLM"):
        assert name.lower() not in message.lower()
