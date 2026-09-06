"""Upload mutation follows request-scoped session authorization."""
from types import SimpleNamespace

import pytest

from api import upload


@pytest.mark.parametrize("shared", [False, True])
@pytest.mark.parametrize("visible", [False, True])
def test_upload_uses_request_visibility(monkeypatch, shared, visible):
    from api import routes, group_chat
    from api.governance import enforce
    actor = object()
    handler = object()
    session = SimpleNamespace(participants=["member"] if shared else [], project_id=None)
    checks = []
    monkeypatch.setattr(routes, "_session_visible_to_request",
                        lambda s, h: visible if s is session and h is handler else False)
    monkeypatch.setattr(enforce, "_request_identity", lambda h: actor)
    monkeypatch.setattr(group_chat, "require_turn_membership", lambda s, a: checks.append((s, a)))
    replies = []
    monkeypatch.setattr(upload, "j", lambda h, body, status: replies.append(status))
    assert upload._reject_invisible_session(handler, session) is (not visible)
    assert checks == ([(session, actor)] if shared and visible else [])
    assert replies == ([] if visible else [404])


@pytest.mark.parametrize("project", [False, True])
def test_upload_rechecks_revoked_membership(monkeypatch, project):
    from api import routes, group_chat
    from api.governance import enforce
    session = SimpleNamespace(participants=[] if project else ["member"],
                              project_id="project" if project else None)
    monkeypatch.setattr(routes, "_session_visible_to_request", lambda *args: True)
    monkeypatch.setattr(enforce, "_request_identity", lambda h: object())

    def revoked(*args):
        raise PermissionError("revoked")

    monkeypatch.setattr(group_chat, "require_turn_membership", revoked)
    replies = []
    monkeypatch.setattr(upload, "j", lambda h, body, status: replies.append(status))
    assert upload._reject_invisible_session(object(), session) is True
    assert replies == [404]

@pytest.mark.parametrize("visible,revoked", [(True, False), (False, False), (True, True)])
def test_file_resolver_request_membership(monkeypatch, visible, revoked):
    from api import models, routes, group_chat
    from api.governance import enforce
    session = SimpleNamespace(profile="other", participants=["member"], project_id=None)
    handler = object()
    monkeypatch.setattr(models, "get_session", lambda *args, **kwargs: session)
    monkeypatch.setattr(routes, "_session_visible_to_request", lambda s, h: visible and h is handler)
    monkeypatch.setattr(enforce, "_request_identity", lambda h: object())

    def membership(*args):
        if revoked:
            raise PermissionError("revoked")

    monkeypatch.setattr(group_chat, "require_turn_membership", membership)
    if visible and not revoked:
        assert models.get_session_for_file_ops("group", handler=handler) is session
    else:
        with pytest.raises(KeyError):
            models.get_session_for_file_ops("group", handler=handler)
