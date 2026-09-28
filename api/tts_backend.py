"""Server-side text-to-speech engines behind ``/api/tts`` (plan Appendix E.7.1).

The ElevenLabs and OpenAI-compatible branches of ``api.routes._handle_tts``
moved here unchanged: ``/api/tts`` keeps its request checks (method, body,
text length, authentication, rate limit) and then calls ``synthesize()``;
the Edge engine stays in the route. The HTTP helpers (``_tts_open``, the
no-redirect and pinned-address openers, the buffered reader and the base URL
check) stay in ``api.routes`` and are looked up there at call time, so the
existing TTS tests and their patches keep working. Package R3 owns this file
in Wave 1 (the model gateway route for speech, plan 3.12).
"""

from __future__ import annotations

import json
import logging
import os
import re

# The moved branches keep logging under the route's logger, as before the move.
logger = logging.getLogger("api.routes")

SERVER_ENGINES = ("elevenlabs", "openai")


def synthesize(handler, text, engine, voice):
    """Answer one TTS request with a server-side provider engine.

    ``/api/tts`` calls this after its own checks for an engine in
    ``SERVER_ENGINES`` and returns what it returns (the response is always
    sent). For any other engine nothing is sent and the result is False.
    ``voice`` is the voice the request asked for; the provider engines take
    their voice from the configuration, as before.
    """
    from api import routes as _routes

    # ── ElevenLabs TTS ──────────────────────────────────────────────────
    if engine == "elevenlabs":
        api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
        if not api_key:
            # Fall back to reading from Hermes .env file
            try:
                from api.onboarding import _load_env_file
                from api.profiles import get_active_hermes_home
                api_key = _load_env_file(get_active_hermes_home() / ".env").get("ELEVENLABS_API_KEY", "")
            except Exception:
                pass
        if not api_key:
            from api.helpers import bad as _bad
            return _bad(handler, "ELEVENLABS_API_KEY not configured", 503)

        # Resolve voice_id from Hermes config.yaml → env fallback
        voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam (same default as hermes-agent config.yaml)
        model_id = "eleven_multilingual_v2"
        try:
            from api.config import get_config
            tts_cfg = (get_config() or {}).get("tts", {})
            if isinstance(tts_cfg, dict):
                el_cfg = tts_cfg.get("elevenlabs", {})
                if isinstance(el_cfg, dict):
                    voice_id = el_cfg.get("voice_id", voice_id)
                    model_id = el_cfg.get("model", model_id) or el_cfg.get("model_id", model_id)
                    # ^ treat empty string as "not set": fall through to default
        except Exception:
            pass  # fall back to defaults

        # Validate voice_id is a safe path segment (no traversal)
        # fullmatch (not match) so a trailing newline can't slip past the `$`
        # anchor, defense-in-depth on the config-derived voice_id before it
        # goes into the request URL (#3510 review).
        if not re.fullmatch(r'[A-Za-z0-9_-]+', voice_id):
            from api.helpers import bad as _bad
            return _bad(handler, "invalid voice_id in config", 400)

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream?output_format=mp3_44100_128"
        req_body = json.dumps({
            "text": text,
            "model_id": model_id,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }).encode("utf-8")

        req = _routes.Request(url, data=req_body, headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        })

        # Buffer the full response before sending first byte.
        # The streaming endpoint is designed for chunked delivery, but urllib's
        # chunked-read path adds per-chunk overhead that dominates short TTS
        # payloads. A hard cap keeps the buffered path bounded even if the
        # upstream misbehaves.
        try:
            with _routes._tts_open(req, timeout=30, opener_factory=lambda: _routes.build_opener(_routes.ProxyHandler({}), _routes._NoRedirectTtsHandler())) as resp:
                audio_data = _routes._buffer_tts_audio_response(resp)
        except ValueError:
            logger.warning("ElevenLabs TTS rejected an invalid upstream response", exc_info=True)
            from api.helpers import bad as _bad
            return _bad(handler, "ElevenLabs TTS generation failed", 502)
        except Exception:
            logger.exception("ElevenLabs TTS generation failed")
            from api.helpers import bad as _bad
            return _bad(handler, "ElevenLabs TTS generation failed", 500)

        handler.send_response(200)
        handler.send_header("Content-Type", "audio/mpeg")
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("Content-Length", str(len(audio_data)))
        handler.end_headers()
        try:
            handler.wfile.write(audio_data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        return True

    # ── OpenAI-compatible TTS ──────────────────────────────────────────
    if engine == "openai":
        api_key = os.getenv("VOICE_TOOLS_OPENAI_KEY", "").strip()
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            try:
                from api.onboarding import _load_env_file
                from api.profiles import get_active_hermes_home
                env_cfg = _load_env_file(get_active_hermes_home() / ".env")
                api_key = env_cfg.get("VOICE_TOOLS_OPENAI_KEY", "") or env_cfg.get("OPENAI_API_KEY", "")
            except Exception:
                pass
        if not api_key:
            from api.helpers import bad as _bad
            return _bad(handler, "OpenAI API key not configured", 503)

        from urllib.parse import urlunsplit as _urlunsplit

        base_url = _urlunsplit(("https", "api.openai.com", "/v1", "", ""))
        model = "gpt-4o-mini-tts"
        oai_voice = "alloy"
        try:
            from api.config import get_config
            tts_cfg = (get_config() or {}).get("tts", {})
            if isinstance(tts_cfg, dict):
                oai_cfg = tts_cfg.get("openai", {})
                if isinstance(oai_cfg, dict):
                    base_url = _routes._normalized_openai_tts_base_url(oai_cfg.get("base_url") or base_url)
                    model = oai_cfg.get("model") or model
                    oai_voice = oai_cfg.get("voice") or oai_voice
                else:
                    base_url = _routes._normalized_openai_tts_base_url(base_url)
            else:
                base_url = _routes._normalized_openai_tts_base_url(base_url)
        except ValueError:
            from api.helpers import bad as _bad
            return _bad(handler, "invalid OpenAI base_url in config", 400)
        except Exception:
            pass

        url = f"{base_url}/audio/speech"
        req_body = json.dumps({
            "model": model,
            "input": text,
            "voice": oai_voice,
        }).encode("utf-8")

        req = _routes.Request(url, data=req_body, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        })

        # Use a pinned HTTPS opener so the resolved address is the one that gets
        # dialed. Keep the no-redirect handler in the same chain to block
        # bearer leaks and SSRF bounce redirects after hostname validation.
        try:
            with _routes._tts_open(req, timeout=30, opener_factory=lambda: _routes.build_opener(_routes.ProxyHandler({}), _routes._NoRedirectTtsHandler(), _routes._PinnedHTTPSHandler())) as resp:
                audio_data = _routes._buffer_tts_audio_response(resp)
        except ValueError:
            logger.warning("OpenAI TTS rejected an invalid upstream response", exc_info=True)
            from api.helpers import bad as _bad
            return _bad(handler, "OpenAI TTS generation failed", 502)
        except Exception:
            logger.exception("OpenAI TTS generation failed")
            from api.helpers import bad as _bad
            return _bad(handler, "OpenAI TTS generation failed", 500)

        handler.send_response(200)
        handler.send_header("Content-Type", "audio/mpeg")
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("Content-Length", str(len(audio_data)))
        handler.end_headers()
        try:
            handler.wfile.write(audio_data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        return True

    return False
