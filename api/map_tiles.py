"""Map tiles for the chat's map blocks, fetched by the server and cached.

The kit frame is sandboxed with an opaque origin, so browsers differ in the
Referer they send for its images, and OpenStreetMap answers some of them with a
"blocked" tile. The frame therefore loads tiles from this server:

    /static/interactive-ui/tiles/<style>/<z>/<x>/<y>.png

``nl`` is the grey BRT Achtergrondkaart of Kadaster (PDOK, open data, also for
commercial use) and ``world`` is OpenStreetMap for places outside the
Netherlands. The path is under /static/ because the opaque frame sends no
cookies; the route is guarded instead: a fixed style list, tile numbers checked
against the zoom level, a per-client rate limit, at most four upstream requests
at a time, an identifying User-Agent, no redirects, image/png only and a size
cap. Tiles are kept on disk for 30 days (OpenStreetMap asks proxies to cache).
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

TILE_PREFIX = "/static/interactive-ui/tiles/"
STYLES = {
    "nl": {"url": "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/grijs/EPSG:3857/{z}/{x}/{y}.png", "max_zoom": 19},
    "world": {"url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png", "max_zoom": 19},
}
_PATH_RE = re.compile(r"^/(?:session)?/?static/interactive-ui/tiles/([a-z]+)/(\d{1,2})/(\d{1,7})/(\d{1,7})\.png$")
CACHE_SECONDS = 30 * 24 * 3600
MAX_BYTES = 400_000
RATE_PER_MINUTE = 900
_upstream = threading.BoundedSemaphore(4)
_rate_lock = threading.Lock()
_rate: dict[str, list] = {}


def _cache_dir() -> Path:
    from api.config import STATE_DIR
    return Path(STATE_DIR) / "map_tiles"


def _client(handler) -> str:
    headers = getattr(handler, "headers", None)
    forwarded = ""
    try:
        forwarded = str(headers.get("X-Forwarded-For") or "").split(",")[0].strip() if headers is not None else ""
    except Exception:
        forwarded = ""
    addr = getattr(handler, "client_address", None) or ("", 0)
    peer = str(addr[0] if isinstance(addr, (tuple, list)) and addr else addr)
    # Only a local proxy (Tailscale serve) may name the real client.
    return forwarded if forwarded and peer in ("127.0.0.1", "::1") else peer


def _allowed(client: str, now: float) -> bool:
    with _rate_lock:
        window = _rate.setdefault(client, [now, 0])
        if now - window[0] >= 60:
            window[0], window[1] = now, 0
        window[1] += 1
        if len(_rate) > 2000:
            for key in [k for k, v in _rate.items() if now - v[0] >= 60][:1000]:
                _rate.pop(key, None)
        return window[1] <= RATE_PER_MINUTE


def parse(path: str):
    """(style, z, x, y) for a valid tile path, else None."""
    match = _PATH_RE.match(str(path or ""))
    if not match:
        return None
    style, z, x, y = match.group(1), int(match.group(2)), int(match.group(3)), int(match.group(4))
    conf = STYLES.get(style)
    if not conf or z > conf["max_zoom"]:
        return None
    if x >= 2 ** z or y >= 2 ** z:
        return None
    return style, z, x, y


def _fetch(style: str, z: int, x: int, y: int) -> bytes | None:
    from api import map_resolve
    url = STYLES[style]["url"].format(z=z, x=x, y=y)
    request = urllib.request.Request(url, headers={"User-Agent": map_resolve.user_agent(), "Accept": "image/png"})
    if not _upstream.acquire(timeout=8):
        return None
    try:
        opener = urllib.request.build_opener(map_resolve._NoRedirect)
        with opener.open(request, timeout=8) as response:
            if response.status != 200 or "image/png" not in str(response.headers.get("Content-Type") or ""):
                return None
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES or not body.startswith(b"\x89PNG"):
                return None
            return body
    except (urllib.error.URLError, OSError, ValueError) as exc:
        logger.info("map tile fetch failed for style %s: %s", style, type(exc).__name__)
        return None
    finally:
        _upstream.release()


def tile(style: str, z: int, x: int, y: int) -> bytes | None:
    path = _cache_dir() / style / str(z) / str(x) / f"{y}.png"
    try:
        if path.is_file() and time.time() - path.stat().st_mtime < CACHE_SECONDS:
            return path.read_bytes()
    except OSError:
        pass
    body = _fetch(style, z, x, y)
    if body is None:
        try:
            return path.read_bytes() if path.is_file() else None  # an old tile beats none
        except OSError:
            return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_bytes(body)
        os.replace(tmp, path)
    except OSError:
        pass
    return body


def serve(handler, parsed) -> bool:
    """Answer a tile path; False when the path is not a tile path."""
    raw = str(getattr(parsed, "path", "") or "")
    if TILE_PREFIX not in raw:
        return False
    parts = parse(raw)
    if parts is None or getattr(parsed, "params", ""):
        _plain(handler, 404)
        return True
    if not _allowed(_client(handler), time.time()):
        _plain(handler, 429)
        return True
    body = tile(*parts)
    if body is None:
        _plain(handler, 502)
        return True
    etag = '"' + hashlib.sha256(body).hexdigest()[:24] + '"'
    try:
        sent = str(handler.headers.get("If-None-Match") or "")
    except Exception:
        sent = ""
    if etag in [t.strip() for t in sent.split(",")]:
        handler.send_response(304)
        handler.send_header("ETag", etag)
        handler.end_headers()
        return True
    handler.send_response(200)
    handler.send_header("Content-Type", "image/png")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "public, max-age=604800")
    handler.send_header("ETag", etag)
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Cross-Origin-Resource-Policy", "cross-origin")
    handler.end_headers()
    handler.wfile.write(body)
    return True


def _plain(handler, status: int) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Content-Length", "0")
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
