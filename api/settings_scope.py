"""Self-service classification for appearance settings writes.

Reported by Michael on 26 Aug 2026: flipping dark mode (and other purely
cosmetic appearance preferences) required an administrator, because the whole
``POST /api/settings`` route was gated on ``config:write``. Appearance is now
self-service:

* The route catalog admits ``POST /api/settings`` with ``config:read`` (any
  identity that can open the settings panel), see api/governance/catalog.py.
* This module is the body-sink guard the route handler calls FIRST: payloads
  that touch anything beyond the appearance keys still require
  ``config:write``, exactly as before. Appearance-only payloads pass without
  any approval step or admin involvement.

The guard mirrors the house body-sink pattern (api/routes.py::
_cron_profile_target_allowed) with two governance-parity additions:

* ``report_only`` policy mode never enforces: a write that WOULD be denied is
  recorded as a ``would_deny`` audit event and allowed, mirroring
  api/governance/enforce.py::enforce_request.
* Denied writes under ``enforce`` append the same ``deny`` audit event the
  route-level hook would have produced, so moving the config:write gate into
  this body sink did not remove denials from the governance audit trail.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Appearance whitelist ────────────────────────────────────────────────────
# Derived from the REAL appearance autosave payload in static/panels.js
# (_appearancePayloadFromUi). Every key that function can emit is listed here
# and was individually classified as cosmetic: a per-user presentation / UI
# chrome preference that cannot grant capability, change auth, models,
# providers, or any server-side behaviour. Panels stay gated by their APIs
# (see api/governance/enforce.py), so tab/control visibility keys are
# presentation only. If the frontend payload ever grows a NON-cosmetic key,
# split the payload client-side instead of adding that key here.
# tests/test_appearance_selfservice.py re-derives this set from the JS
# sources, so drift in either direction fails the suite.

# static/boot.js: _COMPOSER_CONTROL_TOGGLE_DEFS +
# _COMPOSER_SITUATIONAL_CONTROL_TOGGLE_DEFS, emitted via
# _composerControlVisibilityPayload(). Pure composer-chrome visibility.
COMPOSER_CONTROL_VISIBILITY_KEYS = frozenset({
    "hide_composer_attach",
    "hide_composer_saved_prompts",
    "hide_composer_mic",
    "hide_composer_profile",
    "hide_composer_workspace",
    "hide_composer_model",
    "hide_composer_reasoning",
    "hide_composer_context",
    "hide_composer_voice_mode",
    "hide_composer_yolo",
    "hide_composer_bg_badge",
    "hide_composer_mobile_config",
    "hide_composer_quota_chip",
    "hide_composer_toolsets",
    "hide_composer_status",
})

APPEARANCE_SETTINGS_KEYS = frozenset({
    # Core look and feel.
    "theme",
    "skin",
    "font_size",
    # Chat activity presentation (compact worklog / transparent stream).
    "chat_activity_display_mode",
    "transparent_stream_event_timestamps",
    "worklog_details_expanded_default",
    "activity_feed_expanded_default",
    # Transcript / session view behaviour (client-side rendering only).
    "session_jump_buttons",
    "session_endless_scroll",
    "auto_scroll_follow",
    "render_user_markdown",
    "structured_code_default_view",
    "structured_code_auto_tree_lines",
    # Composer / chrome conveniences (own-input handling and visibility).
    "large_text_paste_as_attachment",
    "project_quick_create_buttons",
    "show_titlebar_profile",
    "composer_control_order",
    # Sidebar tab chrome (panels stay gated by their APIs).
    "hidden_tabs",
    "tab_order",
}) | COMPOSER_CONTROL_VISIBILITY_KEYS

_WRITE_PERMISSION = "config:write"


def is_appearance_only_payload(body) -> bool:
    """True when the settings payload only touches cosmetic appearance keys."""
    if not isinstance(body, dict) or not body:
        return False
    return all(key in APPEARANCE_SETTINGS_KEYS for key in body)


def _policy_mode() -> str:
    """Effective governance mode: off | report_only | enforce.

    Mirrors evaluate_request: an unreadable policy reports ``enforce`` (the
    mode cannot be read, so report_only leniency must not apply).
    """
    from api.governance import loader

    try:
        policy = loader.get_policy()
    except Exception:
        return "enforce"
    if not policy.enabled:
        return "off"
    return policy.mode


def _audit_settings_denial(identity, reason: str, *, report_only: bool, mode: str) -> None:
    """Append the deny/would_deny audit row enforce_request would have written.

    Field-for-field consistent with api/governance/enforce.py::_audit_decision;
    an unwritable audit sink never blocks the authorization decision itself.
    """
    try:
        from api.governance.audit import append_audit_event
        from api.governance.enforce import subject_from_identity

        subject = subject_from_identity(identity)
        append_audit_event(
            "would_deny" if report_only else "deny",
            subject_email=subject.email,
            subject_user_id=subject.user_id,
            path="/api/settings",
            method="POST",
            reason=reason,
            mode=mode,
            report_only=report_only,
            extra={"resource": _WRITE_PERMISSION},
        )
    except Exception:
        logger.warning("settings denial audit append failed", exc_info=True)


def settings_write_denial(identity, body):
    """Pure decision core: None = proceed, dict = 403 payload for the route.

    Appearance-only payloads are self-service for any authenticated caller the
    route catalog already let through (config:read). Everything else keeps the
    pre-existing ``config:write`` requirement. Under ``report_only`` mode a
    would-be denial is audited and allowed instead of enforced.
    """
    if is_appearance_only_payload(body):
        return None
    from api.governance.enforce import identity_has_permission

    if identity_has_permission(identity, _WRITE_PERMISSION):
        return None
    mode = _policy_mode()
    if mode == "report_only":
        _audit_settings_denial(identity, "permission_not_allowed", report_only=True, mode=mode)
        return None
    _audit_settings_denial(identity, "permission_not_allowed", report_only=False, mode=mode)
    return {
        "error": "forbidden",
        "resource": _WRITE_PERMISSION,
        "reason": "permission_not_allowed",
    }


def settings_write_denial_for(handler, body):
    """Route hook for ``POST /api/settings``: resolve identity, then decide.

    Unexpected governance failures deny the write (fail closed, audited as a
    ``deny`` with reason ``policy_error``) rather than letting a non-admin
    payload through; appearance-only payloads never reach the permission check
    and therefore stay available even then.
    """
    if is_appearance_only_payload(body):
        return None
    try:
        from api.governance.enforce import _request_identity

        return settings_write_denial(_request_identity(handler), body)
    except Exception:
        logger.warning("settings write governance check failed", exc_info=True)
        _audit_settings_denial(None, "policy_error", report_only=False, mode="enforce")
        return {
            "error": "forbidden",
            "resource": _WRITE_PERMISSION,
            "reason": "policy_error",
        }
