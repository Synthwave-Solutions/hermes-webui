"""Skill update notices with sign-in switched off (trusted single-user mode).

Root cause of the permanent "Skill update notices are unavailable" box: with
auth off and no governance bootstrap admin, requests and turns carried no
email, so nothing was recorded and every read answered 401/404.
"""
from types import SimpleNamespace

import pytest

from api import skill_learning_activity as activity


def test_auth_off_falls_back_to_local_identity(monkeypatch):
    import api.auth as auth
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: False)
    monkeypatch.setenv("HERMES_WEBUI_PASSWORD_IDENTITY", "owner@example.com")
    assert activity._resolve_actor("") == "owner@example.com"
    assert activity._resolve_actor("a@b.co") == "a@b.co"


def test_auth_on_without_email_stays_signed_out(monkeypatch):
    import api.auth as auth
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: True)
    with pytest.raises(ValueError):
        activity._resolve_actor("")
    # Even with auth off, an explicit "no local fallback" keeps 401 semantics.
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: False)
    with pytest.raises(ValueError):
        activity._resolve_actor("", local_ok=False)


def test_read_route_uses_local_actor_for_auth_disabled_identity(monkeypatch, tmp_path):
    import api.auth as auth
    import api.models as models
    from api import ownership
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: False)
    monkeypatch.setenv("HERMES_WEBUI_PASSWORD_IDENTITY", "owner@example.com")
    monkeypatch.setattr(ownership, "_request_identity", lambda h: {"email": "", "method": "auth_disabled"})
    monkeypatch.setattr(models, "get_session", lambda sid: SimpleNamespace())
    seen = {}
    monkeypatch.setattr(activity, "read_activity", lambda actor, sid, access=None: seen.setdefault("actor", actor) and {"events": []})
    monkeypatch.setattr(activity, "j", lambda h, data, **kw: (data, kw))
    import api.governance.resource_scope as rs
    monkeypatch.setattr(rs, "access_for", lambda h: None)
    data, opts = activity.handle_get(object(), "session_id=abc123")
    assert seen["actor"] == "owner@example.com"
    assert "status" not in opts
