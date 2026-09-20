"""Profile photos for the people on this workstation.

Michael asked on 20 Sep 2026 for a photo per person, mainly so a group
conversation shows who wrote what at a glance. One PNG per identity email,
stored under STATE_DIR/user-avatars/<sha1>.png (same addressing as the
per-user appearance store, api/settings_scope.py), never in the governance
policy and never in a session file.

* ``POST /api/me/avatar`` {avatar: data URL} sets the caller's own photo;
  {avatar: null} removes it. Self-service: the route is gated on
  ``sessions:read`` like the people directory, and the target is always the
  request identity, so nobody can set a photo for somebody else.
* ``GET /api/me/avatar`` returns the caller's current URL (settings pane).
* ``GET /api/people/avatar?email=`` serves the PNG. The URL carries the file
  mtime as ``v`` so browsers may cache it for a year and a new upload still
  shows at once.
"""
from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s/\\]+@[^@\s/\\]+\.[^@\s/\\]+$")
MAX_SIDE = 256


def _dir() -> Path:
    from api import config

    return Path(config.STATE_DIR) / "user-avatars"


def normalize_email(value) -> str:
    email = str(value or "").strip().lower()
    return email if _EMAIL_RE.match(email) else ""


def avatar_path(email: str) -> Path:
    digest = hashlib.sha1(email.encode("utf-8")).hexdigest()
    return _dir() / f"{digest}.png"


def avatar_url(email) -> str:
    """Cache-busting URL for ``email``'s photo, or '' when there is none."""
    email = normalize_email(email)
    if not email:
        return ""
    try:
        path = avatar_path(email)
        if not path.is_file() or path.is_symlink():
            return ""
        return f"/api/people/avatar?email={quote(email)}&v={path.stat().st_mtime_ns}"
    except OSError:
        return ""


def _decode(value) -> bytes:
    """Data URL -> square-ish PNG thumbnail (<= MAX_SIDE px)."""
    import base64
    import io

    from PIL import Image, ImageOps

    if not isinstance(value, str) or len(value) > 2800000:
        raise ValueError("Photo is too large (max 2 MB)")
    match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=\s]+)", value)
    if not match:
        raise ValueError("Use a PNG, JPEG or WebP photo")
    raw = base64.b64decode(match.group(2), validate=False)
    with Image.open(io.BytesIO(raw)) as image:
        if image.width * image.height > 16000000:
            raise ValueError("Photo dimensions too large")
        image.load()
        image = ImageOps.exif_transpose(image)
        image = ImageOps.fit(image.convert("RGBA"), (MAX_SIDE, MAX_SIDE), method=Image.LANCZOS)
        out = io.BytesIO()
        image.save(out, format="PNG", optimize=True)
        return out.getvalue()


def save_avatar(email: str, data_url) -> str:
    email = normalize_email(email)
    if not email:
        raise PermissionError("Sign in to set a profile photo")
    blob = _decode(data_url)
    path = avatar_path(email)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(blob)
    tmp.replace(path)
    return avatar_url(email)


def delete_avatar(email: str) -> None:
    email = normalize_email(email)
    if not email:
        raise PermissionError("Sign in to remove a profile photo")
    try:
        avatar_path(email).unlink()
    except FileNotFoundError:
        pass


def read_avatar(email) -> bytes | None:
    email = normalize_email(email)
    if not email:
        return None
    path = avatar_path(email)
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return path.read_bytes()
    except OSError:
        return None


# ── HTTP glue (called from api/routes.py) ───────────────────────────────────

def handle_me_avatar(handler, method: str, body):
    from api.helpers import bad, j
    from api.ownership import request_owner_email

    email = normalize_email(request_owner_email(handler))
    if not email:
        return bad(handler, "Sign in to manage your profile photo", 401)
    if method == "GET":
        return j(handler, {"email": email, "avatar_url": avatar_url(email)})
    value = (body or {}).get("avatar") if isinstance(body, dict) else None
    try:
        if value in (None, "", False):
            delete_avatar(email)
            return j(handler, {"ok": True, "email": email, "avatar_url": ""})
        url = save_avatar(email, value)
    except PermissionError as exc:
        return bad(handler, str(exc), 401)
    except (ValueError, OSError) as exc:
        return bad(handler, str(exc) or "Could not save the photo", 400)
    except Exception:
        logger.warning("profile photo decode failed for %s", email, exc_info=True)
        return bad(handler, "Could not read this image", 400)
    return j(handler, {"ok": True, "email": email, "avatar_url": url})


def handle_people_avatar(handler, query: dict):
    from api.helpers import bad

    email = normalize_email((query.get("email") or [""])[0])
    blob = read_avatar(email)
    if blob is None:
        return bad(handler, "No photo", 404)
    handler.send_response(200)
    handler.send_header("Content-Type", "image/png")
    handler.send_header("Content-Length", str(len(blob)))
    # The URL carries the mtime, so a long private cache is safe.
    handler.send_header("Cache-Control", "private, max-age=31536000, immutable")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    if getattr(handler, "command", "GET") != "HEAD":
        handler.wfile.write(blob)
    return True
