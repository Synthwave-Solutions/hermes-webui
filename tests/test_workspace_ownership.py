"""Tests for per-user workspace ownership plus admin assignment.

Covers: owner stamping on add, non-admin list filtering (owner or member
match), admin sees all, legacy ownerless passthrough (visible and mutable for
everyone), forbidden mutations on foreign owned entries, the admin-only
/api/workspaces/assign handler, and _clean_workspace_list preserving the
ownership keys it used to strip.
"""
import pytest
from unittest.mock import patch, MagicMock

from api.routes import (
    _handle_workspace_add,
    _handle_workspace_remove,
    _handle_workspace_rename,
    _handle_workspace_assign,
    _workspaces_response_list,
    _workspace_visible_to,
)
from api.workspace import _clean_workspace_list

STEVE = "steve@synthwave.solutions"
MICHAEL = "michael@synthwave.solutions"


def _make_handler():
    """Create a mock HTTP handler."""
    h = MagicMock()
    h.wfile = MagicMock()
    return h


class TestWorkspaceAddOwnerStamping:
    """POST /api/workspaces/add stamps owner_email from the caller identity."""

    @patch("api.ownership.request_owner_scope", return_value="all")
    @patch("api.ownership.request_owner_email", return_value=STEVE)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_add_stamps_owner_email(self, mock_load, mock_save, _owner, _scope, tmp_path):
        mock_load.return_value = []
        handler = _make_handler()
        _handle_workspace_add(handler, {"path": str(tmp_path)})
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert len(saved) == 1
        assert saved[0]["owner_email"] == STEVE

    @patch("api.ownership.request_owner_scope", return_value="all")
    @patch("api.ownership.request_owner_email", return_value=None)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_add_without_identity_stays_legacy(self, mock_load, mock_save, _owner, _scope, tmp_path):
        """Auth off / identity-less: no owner_email key, entry stays shared."""
        mock_load.return_value = []
        handler = _make_handler()
        _handle_workspace_add(handler, {"path": str(tmp_path)})
        saved = mock_save.call_args[0][0]
        assert "owner_email" not in saved[0]


class TestWorkspaceListFiltering:
    """Ownership filtering + legacy annotation of the workspace list."""

    WSS = [
        {"path": "/home/user/own", "name": "Own", "owner_email": STEVE},
        {"path": "/home/user/assigned", "name": "Assigned",
         "owner_email": MICHAEL, "members": [STEVE]},
        {"path": "/home/user/foreign", "name": "Foreign", "owner_email": MICHAEL},
        {"path": "/home/user/legacy", "name": "Legacy"},
    ]

    @patch("api.ownership.request_owner_scope", return_value=STEVE)
    def test_non_admin_sees_own_member_and_legacy(self, _scope):
        out = _workspaces_response_list(self.WSS, _make_handler())
        paths = [w["path"] for w in out]
        assert "/home/user/own" in paths
        assert "/home/user/assigned" in paths
        assert "/home/user/legacy" in paths
        assert "/home/user/foreign" not in paths

    @patch("api.ownership.request_owner_scope", return_value="all")
    def test_admin_sees_all(self, _scope):
        out = _workspaces_response_list(self.WSS, _make_handler())
        assert len(out) == len(self.WSS)

    @patch("api.ownership.request_owner_scope", return_value=STEVE)
    def test_legacy_entries_are_marked(self, _scope):
        out = _workspaces_response_list(self.WSS, _make_handler())
        by_path = {w["path"]: w for w in out}
        assert by_path["/home/user/legacy"].get("legacy_unowned") is True
        assert "legacy_unowned" not in by_path["/home/user/own"]

    @patch("api.ownership.request_owner_scope", return_value=STEVE)
    def test_annotation_copies_entries(self, _scope):
        """legacy_unowned must never leak into the persisted list objects."""
        _workspaces_response_list(self.WSS, _make_handler())
        assert "legacy_unowned" not in self.WSS[3]

    @patch("api.ownership.request_owner_scope", return_value=STEVE)
    def test_member_email_matching_is_case_insensitive(self, _scope):
        wss = [{"path": "/p", "name": "P", "owner_email": "Steve@Synthwave.Solutions"}]
        assert _workspace_visible_to(wss[0], _make_handler()) is True


class TestWorkspaceMutationGuards:
    """Rename/remove of owned entries require owner/member/admin."""

    @patch("api.ownership.request_owner_scope", return_value=STEVE)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_remove_foreign_forbidden(self, mock_load, mock_save, _scope):
        mock_load.return_value = [
            {"path": "/home/user/foreign", "name": "F", "owner_email": MICHAEL},
        ]
        handler = _make_handler()
        _handle_workspace_remove(handler, {"path": "/home/user/foreign"})
        handler.send_response.assert_called_with(403)
        mock_save.assert_not_called()

    @patch("api.ownership.request_owner_scope", return_value=STEVE)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_remove_own_allowed(self, mock_load, mock_save, _scope):
        mock_load.return_value = [
            {"path": "/home/user/own", "name": "O", "owner_email": STEVE},
        ]
        handler = _make_handler()
        _handle_workspace_remove(handler, {"path": "/home/user/own"})
        mock_save.assert_called_once()
        assert mock_save.call_args[0][0] == []

    @patch("api.ownership.request_owner_scope", return_value=STEVE)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_remove_legacy_allowed_for_non_admin(self, mock_load, mock_save, _scope):
        """Legacy ownerless entries stay mutable by everyone (shared picker)."""
        mock_load.return_value = [{"path": "/home/user/legacy", "name": "L"}]
        handler = _make_handler()
        _handle_workspace_remove(handler, {"path": "/home/user/legacy"})
        mock_save.assert_called_once()

    @patch("api.ownership.request_owner_scope", return_value=STEVE)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_rename_foreign_forbidden(self, mock_load, mock_save, _scope):
        mock_load.return_value = [
            {"path": "/home/user/foreign", "name": "F", "owner_email": MICHAEL},
        ]
        handler = _make_handler()
        _handle_workspace_rename(handler, {"path": "/home/user/foreign", "name": "X"})
        handler.send_response.assert_called_with(403)
        mock_save.assert_not_called()

    @patch("api.ownership.request_owner_scope", return_value=STEVE)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_rename_as_member_allowed(self, mock_load, mock_save, _scope):
        mock_load.return_value = [
            {"path": "/home/user/assigned", "name": "A",
             "owner_email": MICHAEL, "members": [STEVE]},
        ]
        handler = _make_handler()
        _handle_workspace_rename(handler, {"path": "/home/user/assigned", "name": "New"})
        mock_save.assert_called_once()
        assert mock_save.call_args[0][0][0]["name"] == "New"


class TestWorkspaceAssignEndpoint:
    """POST /api/workspaces/assign is admin-only and manages owner + members."""

    @patch("api.ownership.request_is_admin", return_value=False)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_assign_requires_admin(self, mock_load, mock_save, _admin):
        mock_load.return_value = [{"path": "/home/user/a", "name": "A"}]
        handler = _make_handler()
        _handle_workspace_assign(handler, {"path": "/home/user/a", "owner_email": STEVE})
        handler.send_response.assert_called_with(403)
        mock_save.assert_not_called()

    @patch("api.ownership.request_owner_scope", return_value="all")
    @patch("api.ownership.request_is_admin", return_value=True)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_assign_sets_owner_and_members(self, mock_load, mock_save, _admin, _scope):
        mock_load.return_value = [{"path": "/home/user/a", "name": "A"}]
        handler = _make_handler()
        _handle_workspace_assign(handler, {
            "path": "/home/user/a",
            "owner_email": "  Steve@Synthwave.Solutions ",
            "members": [MICHAEL, " Michael@Synthwave.Solutions ", ""],
        })
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0][0]
        assert saved["owner_email"] == STEVE
        # Members are lowercased, stripped, and deduped
        assert saved["members"] == [MICHAEL]

    @patch("api.ownership.request_owner_scope", return_value="all")
    @patch("api.ownership.request_is_admin", return_value=True)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_assign_empty_owner_clears_to_legacy(self, mock_load, mock_save, _admin, _scope):
        mock_load.return_value = [
            {"path": "/home/user/a", "name": "A", "owner_email": STEVE, "members": [MICHAEL]},
        ]
        handler = _make_handler()
        _handle_workspace_assign(handler, {"path": "/home/user/a", "owner_email": "", "members": []})
        saved = mock_save.call_args[0][0][0]
        assert "owner_email" not in saved
        assert "members" not in saved

    @patch("api.ownership.request_is_admin", return_value=True)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_assign_unknown_path_404(self, mock_load, mock_save, _admin):
        mock_load.return_value = [{"path": "/home/user/a", "name": "A"}]
        handler = _make_handler()
        _handle_workspace_assign(handler, {"path": "/home/user/missing", "owner_email": STEVE})
        handler.send_response.assert_called_with(404)
        mock_save.assert_not_called()

    @patch("api.ownership.request_is_admin", return_value=True)
    @patch("api.routes.save_workspaces")
    @patch("api.routes.load_workspaces")
    def test_assign_rejects_non_list_members(self, mock_load, mock_save, _admin):
        mock_load.return_value = [{"path": "/home/user/a", "name": "A"}]
        handler = _make_handler()
        _handle_workspace_assign(handler, {"path": "/home/user/a", "members": "not-a-list"})
        handler.send_response.assert_called_with(400)
        mock_save.assert_not_called()


class TestCleanWorkspaceListPreservesOwnership:
    """_clean_workspace_list must carry owner_email/members through (it runs
    on every load and persists its result, so stripping would destroy them)."""

    def test_extra_keys_preserved(self):
        cleaned = _clean_workspace_list([
            {"path": "/home/user/a", "name": "A",
             "owner_email": STEVE, "members": [MICHAEL]},
        ])
        assert len(cleaned) == 1
        assert cleaned[0]["owner_email"] == STEVE
        assert cleaned[0]["members"] == [MICHAEL]

    def test_default_rename_still_applies(self):
        cleaned = _clean_workspace_list([
            {"path": "/home/user/a", "name": "default", "owner_email": STEVE},
        ])
        assert cleaned[0]["name"] == "Home"
        assert cleaned[0]["owner_email"] == STEVE
