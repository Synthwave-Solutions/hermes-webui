"""The vendored Memory explorer under ``/static/vendor/mnemosyne-dashboard/``.

Plan addendum 6.6.4 and Appendix E.7.5.1. ``api/routes.py`` sends every path
under that prefix here (also through the ``/session/static/`` alias) and never
to the generic static handler, so the frame document is never served without
its own Content-Security-Policy.

* Only the pinned directory ``0.14.0-a918e5e/`` and only the files listed in
  ``FILES`` are served; ``..``, ``//``, backslashes, ``;`` parameters and any
  percent-encoding (encoded traversal included) answer 404.
* The document runs in an opaque origin: ``sandbox allow-scripts`` (never
  ``allow-same-origin``) with ``connect-src 'none'`` and no fonts, frames,
  workers, forms or plugins.
* Scripts and styles carry ``Access-Control-Allow-Origin: *`` (three.js is a
  CORS module fetch from the opaque origin; public MIT code, never with
  credentials) and an immutable cache; the document is ``no-cache``.
* No response sets a cookie.
"""

from __future__ import annotations

import os
import stat
import threading
from pathlib import Path

PREFIX = "/static/vendor/mnemosyne-dashboard/"
VERSION_DIR = "0.14.0-a918e5e"


def root() -> Path:
    """The pinned directory under the WebUI's static root."""
    try:
        from api.config import get_static_root

        static_root = Path(get_static_root())
    except Exception:
        static_root = Path(__file__).resolve().parents[1] / "static"
    return (static_root / "vendor" / "mnemosyne-dashboard" / VERSION_DIR).resolve()

DOCUMENT_CSP = (
    "sandbox allow-scripts; default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'none'; connect-src 'none'; media-src 'none'; object-src 'none'; "
    "frame-src 'none'; worker-src 'none'; manifest-src 'none'; base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'self'"
)
ASSET_CSP = "default-src 'none'; sandbox"
PERMISSIONS_POLICY = ", ".join(
    f"{feature}=()" for feature in (
        "accelerometer", "ambient-light-sensor", "autoplay", "battery", "bluetooth", "camera",
        "clipboard-read", "clipboard-write", "display-capture", "encrypted-media", "fullscreen",
        "gamepad", "geolocation", "gyroscope", "hid", "idle-detection", "magnetometer",
        "microphone", "midi", "payment", "picture-in-picture", "publickey-credentials-get",
        "screen-wake-lock", "serial", "usb", "web-share", "xr-spatial-tracking",
    )
)

# Served file -> (content type, kind). Kind: document | script | style | other.
FILES = {
    "index.html": ("text/html; charset=utf-8", "document"),
    "app.js": ("text/javascript; charset=utf-8", "script"),
    "memdash-shim.js": ("text/javascript; charset=utf-8", "script"),
    "vendor/three.module.min.js": ("text/javascript; charset=utf-8", "script"),
    "style.css": ("text/css; charset=utf-8", "style"),
    "memdash-overrides.css": ("text/css; charset=utf-8", "style"),
    "favicon.svg": ("image/svg+xml", "other"),
    "LICENSE": ("text/plain; charset=utf-8", "other"),
    "VENDOR.md": ("text/plain; charset=utf-8", "other"),
}

_CACHE: dict[str, tuple[int, int, bytes]] = {}
_LOCK = threading.Lock()


def _relative(path: str) -> str | None:
    """The file name inside the pinned directory, or None when refused."""
    if path.startswith("/session" + PREFIX):
        path = path[len("/session"):]
    if not path.startswith(PREFIX):
        return None
    rest = path[len(PREFIX):]
    if not rest.startswith(VERSION_DIR + "/"):
        return None
    name = rest[len(VERSION_DIR) + 1:]
    if not name or any(c in name for c in ("%", "\\", ";", "\x00")) or "//" in name:
        return None
    if any(part in ("", ".", "..") for part in name.split("/")):
        return None
    return name if name in FILES else None


def _read(name: str) -> bytes | None:
    base = root()
    candidate = base / name
    try:
        info = os.lstat(candidate)
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode):
        return None
    real = Path(os.path.realpath(candidate))
    try:
        real.relative_to(base)
    except ValueError:
        return None
    key = str(real)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and cached[0] == info.st_mtime_ns and cached[1] == info.st_size:
            return cached[2]
    try:
        data = real.read_bytes()
    except OSError:
        return None
    with _LOCK:
        _CACHE[key] = (info.st_mtime_ns, info.st_size, data)
    return data


def headers_for(name: str) -> list[tuple[str, str]]:
    content_type, kind = FILES[name]
    headers = [
        ("Content-Type", content_type),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
    ]
    if kind == "document":
        headers += [
            ("Content-Security-Policy", DOCUMENT_CSP),
            ("X-Frame-Options", "SAMEORIGIN"),
            ("Cache-Control", "no-cache"),
            ("Permissions-Policy", PERMISSIONS_POLICY),
            ("Cross-Origin-Resource-Policy", "same-origin"),
        ]
    elif kind in ("script", "style"):
        headers += [
            ("Access-Control-Allow-Origin", "*"),
            ("Cross-Origin-Resource-Policy", "cross-origin"),
            ("Cache-Control", "public, max-age=31536000, immutable"),
        ]
    else:
        headers += [
            ("Content-Security-Policy", ASSET_CSP),
            ("Cross-Origin-Resource-Policy", "same-origin"),
            ("Cache-Control", "no-cache"),
        ]
    return headers


def serve(handler, parsed) -> bool:
    """Serve one vendored file; False (404) for anything else."""
    if parsed is None or getattr(parsed, "params", ""):
        return False
    name = _relative(str(getattr(parsed, "path", "") or ""))
    if name is None:
        return False
    data = _read(name)
    if data is None:
        return False
    handler.send_response(200)
    for header, value in headers_for(name):
        handler.send_header(header, value)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    try:
        handler.wfile.write(data)
    except (BrokenPipeError, ConnectionResetError):
        pass
    return True
