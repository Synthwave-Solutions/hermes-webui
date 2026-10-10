"""Server-side text-to-speech behind ``/api/tts`` (plan Appendix E.7.1, 3.12).

``/api/tts`` keeps its request checks (method, body, text length,
authentication, rate limit) and then hands a server engine to
``synthesize()``. With enforcement enabled, the
ElevenLabs and OpenAI-compatible engines run through the engine's TTS tool
(``tools.tts_tool.text_to_speech_tool``) in process, inside the active
profile's env, so the engine's own configuration, keys and model gateway hook
(package R2) decide where the audio comes from.

Under model gateway enforcement (``SP_MODEL_GATEWAY_ENFORCE=1`` or the
engine's ``model_gateway.enforce``) every server engine, Edge included, is the
gateway's audio route with the profile's gateway key. When the gateway carries
no audio route (``SP_MODEL_GATEWAY_AUDIO`` is not 1), or the engine cannot
guarantee that route, the answer is ``409`` with ``code: gateway_required``.
Without enforcement the hardened legacy provider adapters and Edge branch stay unchanged.
"""

from __future__ import annotations

import importlib
import json
import logging
import re
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

GATEWAY_REQUIRED = "gateway_required"
GATEWAY_UNAVAILABLE_MESSAGE = (
    "Server voices are not available on this platform. Choose the browser voice in Settings."
)

#: The engines that always run here (never in the route).
PROVIDER_ENGINES = ("elevenlabs", "openai")

_ENGINE_LABELS = {"elevenlabs": "ElevenLabs TTS", "openai": "OpenAI TTS"}
_MISSING_KEY_MESSAGES = {
    "elevenlabs": "ELEVENLABS_API_KEY not configured",
    "openai": "OpenAI API key not configured",
}
_MISSING_KEY_PATTERN = re.compile(
    r"not set|not configured|no [a-z ]*api key|api[_ ]key|missing key|unauthori[sz]ed", re.I)
_MISSING_DEPENDENCY_PATTERN = re.compile(
    r"no module named|not installed|pip install|dependency missing", re.I)
_AUDIO_CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".m4a": "audio/mp4",
}
_DEFAULT_MAX_AUDIO_BYTES = 16 * 1024 * 1024


class _ServerEngines:
    """The engines ``/api/tts`` hands to ``synthesize()``.

    ElevenLabs and OpenAI always. Under model gateway enforcement every engine,
    so the route's own Edge branch (a direct call to a speech provider) is never
    reached; ``synthesize()`` then answers with the gateway's audio route or
    409. Iteration yields the provider engines only.
    """

    def __contains__(self, engine) -> bool:
        name = str(engine or "").strip().lower()
        if name in PROVIDER_ENGINES:
            return True
        return bool(name) and _gateway_enforced()

    def __iter__(self):
        return iter(PROVIDER_ENGINES)

    def __len__(self) -> int:
        return len(PROVIDER_ENGINES)

    def __repr__(self) -> str:
        return f"SERVER_ENGINES{PROVIDER_ENGINES!r} (every engine under model gateway enforcement)"


SERVER_ENGINES = _ServerEngines()


def _gateway_enforced() -> bool:
    try:
        from api.profiles import model_gateway_enforced

        return model_gateway_enforced()
    except Exception:
        logger.warning("Model gateway enforcement could not be read; treating it as on", exc_info=True)
        return True


def _audio_route_enabled() -> bool:
    try:
        from api.profiles import model_gateway_route_enabled

        return model_gateway_route_enabled("audio")
    except Exception:
        logger.warning("Model gateway audio route could not be read; treating it as absent", exc_info=True)
        return False


def _engine_text_to_speech():
    """The engine's TTS tool (imported lazily; the engine is on ``sys.path``)."""
    return importlib.import_module("tools.tts_tool").text_to_speech_tool


def _engine_model_gateway():
    """The engine's model gateway module (package R2), or None on an older engine."""
    try:
        return importlib.import_module("agent.model_gateway")
    except Exception:
        return None


def _engine_guarantees_gateway(module) -> bool:
    """True when the engine itself enforces the gateway for this profile."""
    if module is None:
        return False
    try:
        return bool(module.enforced()) and bool(module.gateway_base_url())
    except Exception:
        logger.warning("Engine model gateway state could not be read", exc_info=True)
        return False


def _send_json(handler, payload, status):
    from api.helpers import j

    j(handler, payload, status=status)
    return True


def _gateway_required(handler):
    return _send_json(handler, {
        "error": GATEWAY_UNAVAILABLE_MESSAGE,
        "code": GATEWAY_REQUIRED,
    }, 409)


def _bad(handler, message, status):
    from api.helpers import bad

    bad(handler, message, status)
    return True


def _max_audio_bytes() -> int:
    try:
        from api import routes

        return int(getattr(routes, "_TTS_PROXY_MAX_BYTES", _DEFAULT_MAX_AUDIO_BYTES))
    except Exception:
        return _DEFAULT_MAX_AUDIO_BYTES


def _unsafe_elevenlabs_voice_id() -> bool:
    """A config voice_id that is not a safe path segment (defence in depth, #3510)."""
    try:
        from api.config import get_config

        tts_cfg = (get_config() or {}).get("tts", {})
        el_cfg = tts_cfg.get("elevenlabs", {}) if isinstance(tts_cfg, dict) else {}
        voice_id = el_cfg.get("voice_id") if isinstance(el_cfg, dict) else None
    except Exception:
        return False
    if voice_id in (None, ""):
        return False
    return not re.fullmatch(r"[A-Za-z0-9_-]+", str(voice_id))


def _is_gateway_refusal(result: dict) -> bool:
    if str(result.get("error_code") or result.get("error_type") or "") == GATEWAY_REQUIRED:
        return True
    return GATEWAY_REQUIRED in str(result.get("error") or "")


def _read_audio(result: dict, workdir: Path) -> tuple[bytes, str]:
    """The synthesized audio and its content type; only files in ``workdir``."""
    raw_paths = result.get("file_paths") or [result.get("file_path")]
    paths = []
    root = workdir.resolve()
    for raw in raw_paths:
        if not raw:
            continue
        path = Path(str(raw)).resolve()
        if root not in path.parents:
            raise ValueError("the speech engine wrote outside its scratch directory")
        paths.append(path)
    if not paths:
        raise ValueError("the speech engine returned no audio")
    suffixes = {path.suffix.lower() for path in paths}
    if len(paths) > 1 and suffixes != {".mp3"}:
        raise ValueError("the speech engine returned audio parts that cannot be joined")
    limit = _max_audio_bytes()
    audio = bytearray()
    for path in paths:
        with path.open("rb") as stream:
            audio.extend(stream.read(limit - len(audio) + 1))
        if len(audio) > limit:
            raise ValueError("the synthesized audio exceeded the byte limit")
    if not audio:
        raise ValueError("the speech engine produced no audio")
    content_type = _AUDIO_CONTENT_TYPES.get(paths[0].suffix.lower(), "audio/mpeg")
    return bytes(audio), content_type


def _engine_failure(handler, result: dict, provider: str, enforced: bool, label: str):
    if _is_gateway_refusal(result):
        return _gateway_required(handler)
    error = str(result.get("error") or "")
    if enforced:
        logger.warning("Speech through the model gateway failed")
        return _bad(handler, "Speech generation failed", 502)
    if _MISSING_DEPENDENCY_PATTERN.search(error):
        logger.warning("%s is not installed in the engine", label)
        return _bad(handler, f"{label} is not installed on the server", 503)
    if _MISSING_KEY_PATTERN.search(error):
        return _bad(handler, _MISSING_KEY_MESSAGES.get(provider, f"{label} is not configured"), 503)
    logger.warning("%s generation failed in the engine", label)
    return _bad(handler, f"{label} generation failed", 502)


def synthesize(handler, text, engine, voice):
    """Answer one TTS request with the engine's TTS tool.

    ``/api/tts`` calls this after its own checks for an engine in
    ``SERVER_ENGINES`` and returns what it returns: True once a response
    (audio or an error) is sent. For an engine that is not handled here nothing
    is sent and the result is False. ``voice`` is the voice the request asked for; the server
    engines take their voice from the profile configuration, as before.
    """
    if not _gateway_enforced():
        from api.tts_legacy import synthesize as legacy_synthesize
        return legacy_synthesize(handler, text, engine, voice)
    del voice  # the server engines use the configured voice
    name = str(engine or "").strip().lower()
    enforced = _gateway_enforced()
    if enforced:
        if not _audio_route_enabled():
            return _gateway_required(handler)
        provider = "openai"  # the gateway's OpenAI-compatible audio route
        label = "Speech"
    elif name in PROVIDER_ENGINES:
        provider = name
        label = _ENGINE_LABELS[name]
        if provider == "elevenlabs" and _unsafe_elevenlabs_voice_id():
            return _bad(handler, "invalid voice_id in config", 400)
    else:
        return False

    try:
        text_to_speech = _engine_text_to_speech()
    except Exception:
        logger.warning("The engine's TTS tool is not available", exc_info=True)
        return _bad(handler, "Server voices are not available on this server.", 503)

    from api import profiles

    workdir = Path(tempfile.mkdtemp(prefix="webui-tts-"))
    try:
        with profiles.profile_env_for_active_request("/api/tts", logger_override=logger):
            if enforced and not _engine_guarantees_gateway(_engine_model_gateway()):
                return _gateway_required(handler)
            raw = text_to_speech(text=text, output_path=str(workdir / "speech.mp3"), provider=provider)
        try:
            result = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
        except (TypeError, ValueError):
            result = {"success": False, "error": "invalid engine result"}
        if not result.get("success"):
            return _engine_failure(handler, result, provider, enforced, label)
        try:
            audio, content_type = _read_audio(result, workdir)
        except (OSError, ValueError):
            logger.warning("%s returned unusable audio", label, exc_info=True)
            return _bad(handler, f"{label} generation failed", 502)
    except Exception:
        logger.exception("%s generation failed", label)
        return _bad(handler, f"{label} generation failed", 500)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(audio)))
    handler.end_headers()
    try:
        handler.wfile.write(audio)
    except (BrokenPipeError, ConnectionResetError):
        pass
    return True
