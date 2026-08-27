"""A profile named in a POST body is authorised before it binds anything.

Reported 27 Aug 2026 ("Allow a different governed user profile for each
conversation"), acceptance criterion: elevated profiles require governance
approval and cannot be selected by an unauthorised user.

The governance route hook only inspects the ``?profile=`` QUERY target, and
/api/profile/switch carried a standing TODO saying the other body sinks skipped
the check. Those sinks bind a turn, a session or a project to a profile, so an
unchecked one let a caller run under a profile they are not scoped for.
"""
import pathlib
import sys
from types import SimpleNamespace

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

ROUTES = (REPO / "api" / "routes.py").read_text(encoding="utf-8")


def _guard(monkeypatch, allowed):
    import api.governance.enforce as enforce
    import api.routes as routes

    monkeypatch.setattr(enforce, "_request_identity", lambda handler: {"email": "u@example.test"})
    monkeypatch.setattr(enforce, "is_profile_allowed_for", lambda identity, profile: profile in allowed)
    return routes._body_profile_allowed


def test_allowed_profile_passes(monkeypatch):
    assert _guard(monkeypatch, {"steve"})(SimpleNamespace(), "steve") is True


def test_unauthorised_profile_is_refused(monkeypatch):
    assert _guard(monkeypatch, {"steve"})(SimpleNamespace(), "admin-elevated") is False


def test_no_profile_named_means_the_sessions_own_profile_applies(monkeypatch):
    guard = _guard(monkeypatch, set())
    for empty in ("", None, "   "):
        assert guard(SimpleNamespace(), empty) is True


def test_governance_failure_denies(monkeypatch):
    import api.governance.enforce as enforce
    import api.routes as routes

    def _boom(identity, profile):
        raise RuntimeError("policy unreadable")

    monkeypatch.setattr(enforce, "_request_identity", lambda handler: {"email": "u@example.test"})
    monkeypatch.setattr(enforce, "is_profile_allowed_for", _boom)
    assert routes._body_profile_allowed(SimpleNamespace(), "anything") is False


def test_every_body_profile_sink_is_guarded():
    """One definition plus the three sinks the TODO named."""
    assert ROUTES.count("_body_profile_allowed(") >= 4
    assert ROUTES.count('return bad(handler, "profile_not_allowed", 403)') >= 4


def test_the_guard_runs_before_the_profile_binds_anything():
    for anchor in ('session_profile = getattr(s, "profile", None)',
                   'if requested_profile and not _profiles_match('):
        sink = ROUTES.index(anchor)
        window = ROUTES[max(0, sink - 400):sink]
        assert "_body_profile_allowed(handler, requested_profile)" in window, anchor
