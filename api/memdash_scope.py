"""Who may see which memory stores in the Memory explorer (server side).

Plan addendum 6.6.6 and 2.1 (decision 10). Wave 1 body (A13); A9 takes this
file over in Wave 2 and derives the viewer kind from W3a's
``delegated_scope()`` alone.

Viewer kinds:

* ``platform_admin``: exactly PLAN 3.6 ``platform`` in Wave 1, that is a
  bootstrap admin or a policy user with ``access_level: admin``. Never
  ``auth_disabled``, never a ``*`` or any other permission, never a role name.
  Only while ``memory_admin_view_platform_admins`` is on (default true,
  decision D74). On a client installation also only in a staff guest session
  under a live ``staff_guest_access`` grant (PLAN X10, X11); until X11 wires
  its checker (``set_staff_guest_checker``) that path is refused there.
* ``org_admin``: always false in Wave 1 (A9 fills it from ``delegated_scope``).
* ``member``: everyone else, and every platform candidate who fails a check.

Only a policy that says ``installation.kind: hq`` is HQ; any other value, or no
``installation`` block, is a client installation. A policy error raises
``ScopeUnavailable`` (the routes answer 503 and never show more).

This module also reads the explorer's WebUI config (``settings.json`` keys and
their environment overrides, addendum Appendix AD).
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

MEMBER = "member"
ORG_ADMIN = "org_admin"
PLATFORM_ADMIN = "platform_admin"
ADMIN_KINDS = frozenset({ORG_ADMIN, PLATFORM_ADMIN})
_EMAIL_RE = re.compile(r"^[^@\s\x00-\x1f\x7f]{1,128}@[^@\s\x00-\x1f\x7f]{1,125}$")
_ORG_RE = re.compile(r"^org_[a-z0-9-]{1,40}$")


class ScopeUnavailable(RuntimeError):
    """The policy cannot be read; callers answer 503 and never widen scope."""


@dataclass(frozen=True)
class Config:
    enabled: bool = False
    admin_view: bool = False
    view_org_admins: bool = True
    view_platform_admins: bool = True
    edit_personal: bool = False
    mask_secrets: bool = True
    retention_days: int = 730


@dataclass(frozen=True)
class Viewer:
    email: str
    email_hash: str
    display_name: str
    kind: str
    org_id: str
    org_name: str
    is_hq: bool
    guest: bool = False

    @property
    def is_admin(self) -> bool:
        return self.kind in ADMIN_KINDS

    @property
    def mem_admin_claim(self) -> str | None:
        """The ``mem_admin`` claim for the hub assertion (addendum 2.3)."""
        if self.kind == PLATFORM_ADMIN:
            return "platform"
        if self.kind == ORG_ADMIN:
            return "org"
        return None


def email_hash(email: str) -> str:
    raw = str(email or "").strip().lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24] if raw else ""


def _flag(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def load_config() -> Config:
    """The explorer's switches; defaults per addendum Appendix AD.

    ``memdash_enabled`` has the environment override ``HERMES_WEBUI_MEMDASH``;
    the admin view is switched on only by ``HERMES_WEBUI_MNEMO_ADMIN_VIEW=1``
    (8.7). A settings file that cannot be read gives the defaults, which keep
    the explorer off.
    """
    try:
        from api.config import load_settings

        settings = load_settings() or {}
    except Exception:
        logger.warning("memdash settings unreadable; using defaults")
        settings = {}
    env_enabled = os.environ.get("HERMES_WEBUI_MEMDASH", "").strip()
    enabled = _flag(env_enabled, False) if env_enabled else _flag(settings.get("memdash_enabled"), False)
    try:
        retention = int(settings.get("memory_access_log_retention_days", 730))
    except (TypeError, ValueError):
        retention = 730
    return Config(
        enabled=enabled,
        admin_view=os.environ.get("HERMES_WEBUI_MNEMO_ADMIN_VIEW", "").strip() == "1",
        view_org_admins=_flag(settings.get("memory_admin_view_org_admins"), True),
        view_platform_admins=_flag(settings.get("memory_admin_view_platform_admins"), True),
        edit_personal=_flag(settings.get("memory_admin_edit_personal"), False),
        mask_secrets=_flag(settings.get("memory_admin_mask_secrets"), True),
        retention_days=max(30, min(retention, 3650)),
    )


# ── Staff guest grants (PLAN X10, X11) ───────────────────────────────────────

_staff_guest_checker: Callable[[dict], bool] | None = None


def set_staff_guest_checker(fn: Callable[[dict], bool] | None) -> None:
    """X11 registers the live grant check here; until then there is none."""
    global _staff_guest_checker
    _staff_guest_checker = fn


def staff_guest_grant_live(identity: dict) -> bool:
    checker = _staff_guest_checker
    if checker is None:
        return False
    try:
        return checker(identity) is True
    except Exception:
        logger.warning("staff guest grant check failed; refusing")
        return False


# ── Policy facts ─────────────────────────────────────────────────────────────

def _policy():
    from api.governance import loader

    try:
        return loader.get_policy()
    except Exception as exc:
        raise ScopeUnavailable("the governance policy cannot be read") from exc


def installation_is_hq(policy) -> bool:
    raw = getattr(policy, "raw", None) or {}
    block = raw.get("installation") if isinstance(raw, dict) else None
    if not isinstance(block, dict):
        return False
    kind = block.get("kind")
    return isinstance(kind, str) and kind.strip() == "hq"


def organization(policy) -> tuple[str, str]:
    """``(organization.id, organization.name)`` of a client policy, or ``('', '')``."""
    raw = getattr(policy, "raw", None) or {}
    block = raw.get("organization") if isinstance(raw, dict) else None
    if not isinstance(block, dict):
        return "", ""
    org_id = str(block.get("id") or "").strip()
    if not _ORG_RE.match(org_id):
        org_id = ""
    return org_id, str(block.get("name") or "").strip()[:80]


def installation_name(policy) -> str:
    raw = getattr(policy, "raw", None) or {}
    block = raw.get("installation") if isinstance(raw, dict) else None
    if isinstance(block, dict):
        name = str(block.get("name") or "").strip()
        if name:
            return name[:80]
    return ""


def is_platform_candidate(policy, email: str) -> bool:
    """PLAN 3.6 ``platform``: a bootstrap admin or ``access_level: admin``."""
    email = str(email or "").strip().lower()
    if not email:
        return False
    if email in {str(a).strip().lower() for a in (getattr(policy, "bootstrap_admins", ()) or ())}:
        return True
    users = getattr(policy, "users", None) or {}
    user = users.get(email)
    return bool(user is not None and getattr(user, "access_level", "") == "admin")


def display_name(identity: dict) -> str:
    claims = identity.get("claims_subset") if isinstance(identity, dict) else None
    name = ""
    if isinstance(claims, dict):
        name = str(claims.get("name") or "").strip()
    email = str((identity or {}).get("email") or "").strip().lower()
    return (name or email.split("@")[0] or "Administrator")[:120]


def resolve_viewer(identity: dict, config: Config | None = None) -> Viewer:
    """The viewer kind for an authenticated, interactive identity.

    Raises ``ScopeUnavailable`` on a policy error. An identity without a valid
    email, or an ``auth_disabled`` identity, is never an admin.
    """
    config = config or load_config()
    policy = _policy()
    email = str((identity or {}).get("email") or "").strip().lower()
    method = str((identity or {}).get("method") or "")
    is_hq = installation_is_hq(policy)
    org_id, org_name = ("", "") if is_hq else organization(policy)
    if is_hq:
        org_name = installation_name(policy) or "Synthwave"
    kind = MEMBER
    guest = False
    if _EMAIL_RE.match(email) and method != "auth_disabled" and is_platform_candidate(policy, email):
        if config.view_platform_admins:
            if is_hq:
                kind = PLATFORM_ADMIN
            elif staff_guest_grant_live(identity):
                kind = PLATFORM_ADMIN
                guest = True
    return Viewer(
        email=email,
        email_hash=email_hash(email),
        display_name=display_name(identity),
        kind=kind,
        org_id=org_id,
        org_name=org_name,
        is_hq=is_hq,
        guest=guest,
    )
