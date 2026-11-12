"""One shared model catalogue for the own gateway, instead of one per profile.

Hermes Agent resolves context lengths and prices from the ``/models`` listing of
the configured endpoint (``agent.model_metadata.fetch_endpoint_model_metadata``).
For the gateway on this host that listing is expensive: one request rebuilds
the whole catalogue and the gateway answers nothing else for about twelve
seconds. The engine keeps its snapshot per profile, per credential and per
process, keeps no disk copy for a local endpoint, reads with a ten second
timeout (shorter than the build) and retries a failed refresh every five
minutes. In this server, which hosts every profile, that added up to dozens of
catalogue builds per hour, most of them thrown away (measured 12 Nov 2026: 172
builds in 3.4 hours, the gateway unresponsive for 18% of the busy time).

This guard keeps one snapshot per gateway port for all profiles and
credentials:

- a snapshot younger than ``_FRESH_SECONDS`` is returned as is;
- an older snapshot is still returned at once, while a single background
  refresh rebuilds it, at most once per ``_ATTEMPT_GAP_SECONDS``;
- without any snapshot one caller fetches and the others wait for that result;
  after a failure nothing is tried again for ``_COLD_RETRY_SECONDS``;
- the refresh reads with a timeout longer than the catalogue build;
- the snapshot is written to the WebUI state directory and loaded again after a
  restart. It holds model metadata only, never a credential;
- an empty or failed refresh never replaces a good snapshot.

Only loopback endpoints on the configured gateway ports are handled. Every
other endpoint, and any unexpected engine layout, reaches the engine untouched.
The returned mapping is shared between callers, exactly like the engine's own
snapshot: treat it as read only.

Set ``HERMES_WEBUI_CATALOG_GUARD=0`` to switch the guard off.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import threading
import time
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

_MARK = "_webui_shared_catalog"
_HTTP_MARK = "_webui_catalog_timeout"
_LOCK = threading.Lock()  # install
_STATE_LOCK = threading.Lock()  # snapshots
_LOCAL = threading.local()

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_FRESH_SECONDS = 1800.0
_ATTEMPT_GAP_SECONDS = 1800.0
_COLD_RETRY_SECONDS = 300.0
_FORCE_GAP_SECONDS = 60.0
_FOLLOWER_WAIT_SECONDS = 40.0
_MERGE_BASE_SECONDS = 86400.0
_CONNECT_TIMEOUT_SECONDS = 5.0
_READ_TIMEOUT_SECONDS = 30.0
_SNAPSHOT_FILE = "engine_catalog_snapshot.json"

_slots: dict = {}
_disk_loaded = False
_snapshot_path_override = None  # tests


class _Slot:
    __slots__ = ("models", "fetched_at", "base_at", "attempt_at", "flight")

    def __init__(self):
        self.models = None
        self.fetched_at = 0.0
        self.base_at = 0.0
        self.attempt_at = 0.0
        self.flight = None


def _enabled() -> bool:
    return os.environ.get("HERMES_WEBUI_CATALOG_GUARD", "1").strip().lower() not in {"0", "false", "off", "no"}


def _float_env(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, ""))
    except (TypeError, ValueError):
        return default
    return value if value >= 0 else default


def _gateway_ports() -> set:
    ports = set()
    for part in os.environ.get("HERMES_WEBUI_CATALOG_GUARD_PORTS", "20128").split(","):
        part = part.strip()
        if part.isdigit():
            ports.add(int(part))
    return ports


def _gateway_port(base_url):
    """The gateway port when ``base_url`` is the own gateway, else None."""
    if not isinstance(base_url, str):
        return None
    try:
        parts = urlsplit(base_url.strip())
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or host not in _LOOPBACK_HOSTS:
        return None
    return port if port in _gateway_ports() else None


def _snapshot_path():
    if _snapshot_path_override is not None:
        return _snapshot_path_override
    from api.config import STATE_DIR

    return os.path.join(os.fspath(STATE_DIR), _SNAPSHOT_FILE)


def _load_disk_locked() -> None:
    """Read the stored snapshots once (caller holds ``_STATE_LOCK``)."""
    global _disk_loaded
    if _disk_loaded:
        return
    _disk_loaded = True
    try:
        with open(_snapshot_path(), encoding="utf-8") as handle:
            stored = json.load(handle)
        endpoints = stored.get("endpoints") if isinstance(stored, dict) else None
        for key, entry in (endpoints or {}).items():
            models = entry.get("models") if isinstance(entry, dict) else None
            if not (isinstance(models, dict) and models and all(isinstance(v, dict) for v in models.values())):
                continue
            slot = _slots.setdefault(int(key), _Slot())
            if slot.models is None:
                slot.models = models
                slot.fetched_at = float(entry.get("fetched_at") or 0.0)
                slot.base_at = float(entry.get("base_at") or 0.0)
    except FileNotFoundError:
        pass
    except Exception:
        logger.debug("stored engine catalogue snapshot is unreadable; starting empty", exc_info=True)


def _write_disk() -> None:
    try:
        with _STATE_LOCK:
            endpoints = {
                str(port): {"fetched_at": slot.fetched_at, "base_at": slot.base_at, "models": slot.models}
                for port, slot in _slots.items() if slot.models
            }
        text = json.dumps({"version": 1, "endpoints": endpoints})
        path = _snapshot_path()
        temp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
    except Exception:
        logger.debug("engine catalogue snapshot could not be stored", exc_info=True)


def _refresh(port, slot, flight, fetch, normalized, api_key, background):
    """Leader: fetch once with the long read timeout, keep the result, release followers."""
    started = time.monotonic()
    fetched = {}
    try:
        _LOCAL.read_timeout = _float_env("HERMES_WEBUI_CATALOG_GUARD_READ_TIMEOUT", _READ_TIMEOUT_SECONDS)
        try:
            fetched = fetch(normalized, api_key, native_protocol_probes=False)
        finally:
            _LOCAL.read_timeout = None
    except Exception:
        logger.debug("engine catalogue refresh failed", exc_info=True)
        fetched = {}
    usable = isinstance(fetched, dict) and bool(fetched) and all(isinstance(v, dict) for v in fetched.values())
    try:
        with _STATE_LOCK:
            if usable:
                now = time.time()
                if slot.models and 0 <= now - slot.base_at < _MERGE_BASE_SECONDS:
                    # Credentials may see different subsets: keep the union for a day.
                    merged = dict(slot.models)
                    merged.update(fetched)
                else:
                    merged = dict(fetched)
                    slot.base_at = now
                slot.models = merged
                slot.fetched_at = now
            result = slot.models or {}
    finally:
        with _STATE_LOCK:
            slot.flight = None
        flight.set()
    logger.info(
        "engine catalogue refresh port=%s ok=%s models=%s seconds=%.1f background=%s",
        port, usable, len(fetched) if isinstance(fetched, dict) else 0, time.monotonic() - started, background,
    )
    if usable:
        _write_disk()
    return result


def _serve(port, fetch, normalized, api_key, force_refresh, cached_only):
    fresh_for = _float_env("HERMES_WEBUI_CATALOG_GUARD_FRESH_SECONDS", _FRESH_SECONDS)
    with _STATE_LOCK:
        _load_disk_locked()
        slot = _slots.setdefault(port, _Slot())
        now = time.time()
        have = bool(slot.models)
        since_attempt = now - slot.attempt_at
        if since_attempt < 0:  # clock went backwards
            since_attempt = float("inf")
        if have and not force_refresh:
            age = now - slot.fetched_at
            if 0 <= age < fresh_for or cached_only:
                return slot.models
            if slot.flight is not None or since_attempt < _ATTEMPT_GAP_SECONDS:
                return slot.models
            mode = "background"
        elif cached_only:
            return slot.models if have else {}
        elif have and since_attempt < _FORCE_GAP_SECONDS:
            return slot.models
        elif not have and slot.flight is None and since_attempt < _COLD_RETRY_SECONDS:
            return {}
        else:
            mode = "foreground"
        flight = slot.flight
        leader = flight is None
        if leader:
            flight = threading.Event()
            slot.flight = flight
            slot.attempt_at = now
        stale = slot.models
    if mode == "background":
        # Copy the context so the refresh resolves the caller's profile (TLS settings).
        context = contextvars.copy_context()
        threading.Thread(
            target=context.run, args=(_refresh, port, slot, flight, fetch, normalized, api_key, True),
            name="engine-catalogue-refresh", daemon=True,
        ).start()
        return stale
    if leader:
        return _refresh(port, slot, flight, fetch, normalized, api_key, False)
    flight.wait(_FOLLOWER_WAIT_SECONDS)
    with _STATE_LOCK:
        return slot.models or {}


def _wrap_stream(http) -> bool:
    """Let the guard's own refresh read ``/models`` with a longer timeout."""
    original = getattr(http, "stream", None)
    if original is None:
        return False
    if getattr(original, _HTTP_MARK, False):
        return True

    def stream(url, *args, **kwargs):
        read = getattr(_LOCAL, "read_timeout", None)
        if read and isinstance(url, str) and url.split("?", 1)[0].rstrip("/").endswith("/models"):
            kwargs["timeout"] = (_CONNECT_TIMEOUT_SECONDS, read)
        return original(url, *args, **kwargs)

    setattr(stream, _HTTP_MARK, True)
    stream.__wrapped__ = original
    http.stream = stream
    return True


def install() -> bool:
    """Wrap the engine's endpoint metadata fetch once. Returns True when the guard is active."""
    if not _enabled():
        return False
    try:
        import sys

        import agent.model_metadata as metadata
        import agent.model_metadata_endpoint as endpoint
        import agent.model_metadata_http as http
    except Exception:
        return False
    with _LOCK:
        original = getattr(metadata, "fetch_endpoint_model_metadata", None)
        if original is None or not callable(getattr(endpoint, "_fetch_endpoint_model_metadata_uncached", None)):
            return False
        if getattr(original, _MARK, False):
            return True
        if not _wrap_stream(http):
            return False

        def fetch_endpoint_model_metadata(base_url, api_key="", force_refresh=False, *args, **kwargs):
            port = None
            if _enabled() and not args:
                try:
                    port = _gateway_port(base_url)
                except Exception:
                    port = None
            if port is None:
                return original(base_url, api_key, force_refresh, *args, **kwargs)
            normalized = base_url.strip().rstrip("/")
            return _serve(
                port, endpoint._fetch_endpoint_model_metadata_uncached, normalized, api_key,
                bool(force_refresh), bool(kwargs.get("cached_only")),
            )

        setattr(fetch_endpoint_model_metadata, _MARK, True)
        fetch_endpoint_model_metadata.__wrapped__ = original
        metadata.fetch_endpoint_model_metadata = fetch_endpoint_model_metadata
        # ``agent.usage_pricing`` imports the function by name: rebind it when already loaded.
        pricing = sys.modules.get("agent.usage_pricing")
        if pricing is not None and getattr(pricing, "fetch_endpoint_model_metadata", None) is original:
            pricing.fetch_endpoint_model_metadata = fetch_endpoint_model_metadata
        return True


def reset_for_tests() -> None:
    global _disk_loaded
    with _STATE_LOCK:
        _slots.clear()
        _disk_loaded = False
