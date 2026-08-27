"""Left navigation follows effective permissions.

Reported 27 Aug 2026 ("Let administrators configure visible left-navigation
items by user group"): customers saw menu items for features their permissions
do not include, so each was a dead end.

Navigation is derived, never configured twice: a panel is hidden exactly when
the caller lacks the permission that already gates the panel's own API. An
administrator therefore changes navigation by changing the group's grants.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from api.governance.nav import (  # noqa: E402
    ESSENTIAL_PANELS,
    PANEL_PERMISSIONS,
    hidden_panels,
    visible_panels,
)

PANELS_JS = (REPO / "static" / "panels.js").read_text(encoding="utf-8")
BOOT_JS = (REPO / "static" / "boot.js").read_text(encoding="utf-8")
GOV_API = (REPO / "api" / "governance_api.py").read_text(encoding="utf-8")
INDEX_HTML = (REPO / "static" / "index.html").read_text(encoding="utf-8")


class _Grants:
    def __init__(self, permissions):
        self.permissions = frozenset(permissions)


class _Access:
    def __init__(self, permissions):
        self.grants = _Grants(permissions)


class _Policy:
    def __init__(self, enabled=True, mode="enforce"):
        self.enabled = enabled
        self.mode = mode


def test_a_panel_is_hidden_exactly_when_its_permission_is_missing():
    access = _Access({"cron:read", "files:read"})
    hidden = hidden_panels(access, _Policy())
    assert "tasks" not in hidden and "workspaces" not in hidden and "files" not in hidden
    assert "insights" in hidden and "governance" in hidden and "logs" in hidden


def test_essential_panels_are_never_hidden():
    hidden = hidden_panels(_Access(set()), _Policy())
    for panel in ESSENTIAL_PANELS:
        assert panel not in hidden
    # Everything else a narrow user cannot reach is hidden rather than shown.
    assert set(hidden) == set(PANEL_PERMISSIONS) - ESSENTIAL_PANELS


def test_wildcard_and_area_admin_grants_open_the_panel():
    assert hidden_panels(_Access({"*"}), _Policy()) == []
    assert "governance" not in hidden_panels(_Access({"governance:admin"}), _Policy())
    assert "tasks" not in hidden_panels(_Access({"cron:admin"}), _Policy())


@pytest.mark.parametrize("policy", [_Policy(enabled=False), _Policy(mode="report_only")])
def test_governance_off_or_report_only_never_hides(policy):
    assert hidden_panels(_Access(set()), policy) == []


def test_visible_is_the_complement_and_always_includes_the_essentials():
    access = _Access({"analytics:read"})
    visible = visible_panels(access, _Policy())
    assert "insights" in visible
    assert set(ESSENTIAL_PANELS) <= set(visible)
    assert not set(visible) & set(hidden_panels(access, _Policy()))


def test_every_panel_id_exists_in_the_markup():
    """A permission mapped to a panel that does not exist would hide nothing."""
    for panel in PANEL_PERMISSIONS:
        assert f'data-panel="{panel}"' in INDEX_HTML, panel


def test_me_endpoint_publishes_hidden_nav():
    assert '"hidden_nav": _hidden_nav(access, policy)' in GOV_API


def test_client_merges_governance_hidden_nav_into_every_visibility_pass():
    assert "window._govHiddenNav" in PANELS_JS
    assert "hidden=hidden.concat(govHidden" in PANELS_JS
    assert "loadGovernanceNavVisibility()" in BOOT_JS


def test_client_can_only_hide_never_reveal():
    """The merge concatenates onto the hidden list; nothing removes entries."""
    block = PANELS_JS[PANELS_JS.index("function _applyTabVisibility"):][:600]
    assert "hidden=hidden.concat(" in block, "the merge must only add entries"
    assert "hidden=hidden.filter(" not in block
    assert "hidden.splice(" not in block


def test_resolution_failure_shows_everything_rather_than_locking_a_user_out():
    class _Broken:
        @property
        def grants(self):
            raise RuntimeError("policy unreadable")

    assert hidden_panels(_Broken(), _Policy()) == []
