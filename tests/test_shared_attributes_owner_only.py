"""Shared attributes (name, category, colour, members) are owner/admin only;
personal presentation (order) is per person."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def caller(monkeypatch):
    import api.ownership as own
    state = {"scope": "member@x.nl", "admin": False}
    monkeypatch.setattr(own, "request_owner_scope", lambda h: state["scope"])
    monkeypatch.setattr(own, "request_is_admin", lambda h: state["admin"])
    return state


def test_member_cannot_rename_or_recategorise_a_space(caller):
    from api.routes import _workspace_manage_allowed
    space = {"path": "/w/acme", "owner_email": "owner@x.nl", "members": ["member@x.nl"]}
    assert _workspace_manage_allowed(space, object()) is False
    caller["scope"] = "owner@x.nl"
    assert _workspace_manage_allowed(space, object()) is True
    caller.update(scope="boss@x.nl", admin=True)
    assert _workspace_manage_allowed(space, object()) is True


def test_legacy_space_without_owner_is_admin_managed(caller):
    from api.routes import _workspace_manage_allowed
    legacy = {"path": "/w/shared"}
    assert _workspace_manage_allowed(legacy, object()) is False
    caller["admin"] = True
    assert _workspace_manage_allowed(legacy, object()) is True


def test_rename_handler_checks_owner_after_visibility():
    src = (ROOT / "api" / "routes.py").read_text(encoding="utf-8")
    fn = src[src.index("def _handle_workspace_rename"):src.index("def _handle_workspace_reorder")]
    assert fn.index("_workspace_visible_to(w, handler)") < fn.index("_workspace_manage_allowed(w, handler)")
    assert "it changes it for everyone" in fn


def test_personal_order_does_not_touch_the_shared_registry(monkeypatch, tmp_path):
    import api.config as cfg
    from api import user_prefs
    monkeypatch.setattr(cfg, "STATE_DIR", tmp_path)
    rows = [{"path": "/a"}, {"path": "/b"}, {"path": "/c"}]
    user_prefs.set_workspace_order("anna@x.nl", "default", ["/c", "/a"])
    assert [r["path"] for r in user_prefs.apply_order(rows, user_prefs.get_workspace_order("anna@x.nl", "default"))] == ["/c", "/a", "/b"]
    assert user_prefs.get_workspace_order("bram@x.nl", "default") == []
    assert [r["path"] for r in user_prefs.apply_order(rows, [])] == ["/a", "/b", "/c"]
    src = (ROOT / "api" / "routes.py").read_text(encoding="utf-8")
    fn = src[src.index("def _handle_workspace_reorder"):][:8000]
    assert 'str(body.get("scope") or "") == "default" and request_is_admin(handler)' in fn
    assert fn.index("user_prefs.set_workspace_order") < fn.index("save_workspaces(")


def test_member_cannot_rename_or_recolour_someone_elses_project(monkeypatch):
    """/api/projects/rename (name, colour, category) is owner/admin only; a
    project member gets the same 404 as a stranger."""
    import api.ownership as own
    monkeypatch.setattr(own, "request_owner_scope", lambda h: "member@x.nl")
    assert own.row_visible_to("owner@x.nl", object()) is False
    src = (ROOT / "api" / "routes.py").read_text(encoding="utf-8")
    block = src[src.index('if parsed.path == "/api/projects/rename":'):][:2500]
    assert "_row_visible_to(proj.get(\"owner_email\"), handler)" in block
    assert "Manage shared projects in the Projects hub" in block


def test_bot_appearance_requires_profiles_admin():
    src = (ROOT / "api" / "routes.py").read_text(encoding="utf-8")
    block = src[src.index('if parsed.path in ("/api/profile/appearance", "/api/profile/avatar"):'):][:800]
    assert '"profiles:admin"' in block


def test_ui_tells_editors_the_change_is_for_everyone():
    panels = (ROOT / "static" / "panels.js").read_text(encoding="utf-8")
    projects = (ROOT / "static" / "projects.js").read_text(encoding="utf-8")
    assert "shared_change_hint_space" in panels and "shared_change_hint_project" in projects
    nl = (ROOT / "static" / "i18n" / "nl.js").read_text(encoding="utf-8")
    assert "Dit verandert het voor iedereen in dit project." in nl
