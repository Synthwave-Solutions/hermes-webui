"""Projects hub (ticket 12): an honest, permission-filtered project view.

The ticket calls the Projects hub a strategic long-term goal and explicitly
NOT an immediate replacement for the tools a team already keeps project
material in. Two properties follow from that and are pinned here:

* nothing is claimed without evidence: an unconnected source says so by name,
  and an empty section carries a reason rather than a bare zero;
* the hub route rides on sessions:read, which is WIDER than the permission
  guarding some of the data it aggregates, so every section is re-gated with
  the permission its own route requires and an ungranted section is absent
  from the payload rather than present-and-empty.

Pre-release review of the plan found two defects that these tests are the net
for: the integration inventory shipping mcp:read data on a sessions:read
route, and a "read-only" helper (ensure_cron_project) that writes.
"""
import ast
import pathlib
import sys

from unittest.mock import patch

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

CATALOG = (REPO / "api" / "governance" / "catalog.py").read_text(encoding="utf-8")
NAV = (REPO / "api" / "governance" / "nav.py").read_text(encoding="utf-8")
ROUTES = (REPO / "api" / "routes.py").read_text(encoding="utf-8")
HUB = (REPO / "api" / "projects_hub.py").read_text(encoding="utf-8")
INDEX_HTML = (REPO / "static" / "index.html").read_text(encoding="utf-8")
PANELS_JS = (REPO / "static" / "panels.js").read_text(encoding="utf-8")
PROJECTS_JS = (REPO / "static" / "projects.js").read_text(encoding="utf-8")
STYLE_CSS = (REPO / "static" / "style.css").read_text(encoding="utf-8")
EN_JS = (REPO / "static" / "i18n" / "en.js").read_text(encoding="utf-8")

STEVE = "steve@synthwave.solutions"
MICHAEL = "michael@synthwave.solutions"

ALL_SECTIONS = {
    "workspaces": True, "files": True, "jobs": True, "status": True,
    "integrations": True, "notes_drawer": True, "delivery": True,
}


def _handler_stub():
    from unittest.mock import MagicMock

    handler = MagicMock()
    handler.wfile = MagicMock()
    return handler


def _parsed(path):
    from urllib.parse import urlparse

    return urlparse(path)


def _session(sid, project_id, owner, *, profile="default", title="Chat",
             workspace="", updated=100.0):
    return {
        "session_id": sid, "project_id": project_id, "owner_email": owner,
        "profile": profile, "title": title, "workspace": workspace,
        "last_message_at": updated, "updated_at": updated,
    }


# ── Route classification and navigation ─────────────────────────────────────

def test_hub_rides_the_existing_projects_rule_without_a_catalog_edit():
    from api.governance.catalog import route_permission

    assert route_permission("/api/projects/hub", "GET") == "sessions:read"
    assert route_permission("/api/projects/hub/detail", "GET") == "sessions:read"
    assert CATALOG.count('RouteRule("/api/projects",') == 1, (
        "the prefix rule already classifies the hub; a second rule would be "
        "a silent widening"
    )


def test_the_panel_is_navigable_only_with_the_permission_its_route_needs():
    from api.governance.nav import hidden_panels

    assert '"projects": "sessions:read",' in NAV

    class _Grants:
        def __init__(self, permissions):
            self.permissions = permissions

    class _Access:
        def __init__(self, permissions):
            self.grants = _Grants(permissions)

    class _Policy:
        enabled = True
        mode = "enforce"

    assert "projects" in hidden_panels(_Access({"chat:use"}), _Policy())
    assert "projects" not in hidden_panels(_Access({"sessions:read"}), _Policy())


def test_the_panel_id_exists_in_the_markup():
    # tests/test_governance_nav_visibility.py asserts every PANEL_PERMISSIONS
    # id is a real data-panel; keep that true.
    assert 'data-panel="projects"' in INDEX_HTML


# ── Project and session visibility ──────────────────────────────────────────

def test_visible_projects_reuses_the_projects_ownership_rule():
    from api import projects_hub

    rows = [
        {"project_id": "a", "name": "Mine", "owner_email": STEVE, "profile": "default"},
        {"project_id": "b", "name": "Theirs", "owner_email": MICHAEL, "profile": "default"},
        {"project_id": "c", "name": "Legacy", "profile": "default"},
    ]
    mine = projects_hub.visible_projects(rows, STEVE, "default")
    assert [p["project_id"] for p in mine] == ["a"], "unowned rows are admin-only"
    everything = projects_hub.visible_projects(rows, "all", "default")
    assert [p["project_id"] for p in everything] == ["a", "b", "c"]


def test_a_project_tagged_to_another_profile_is_dropped():
    from api import projects_hub

    rows = [
        {"project_id": "a", "name": "Here", "owner_email": STEVE, "profile": "default"},
        {"project_id": "b", "name": "Elsewhere", "owner_email": STEVE, "profile": "research"},
    ]
    assert [p["project_id"] for p in projects_hub.visible_projects(rows, STEVE, "default")] == ["a"]


def test_the_owner_filter_is_shared_with_the_projects_list_route():
    assert "projects_hub.visible_projects_by_owner(" in ROUTES, (
        "one ownership rule, or the list and the hub drift apart"
    )


def test_the_projects_list_still_counts_other_profiles_after_the_refactor():
    # visible_projects_by_owner must NOT apply the profile filter: the list
    # route derives other_profile_count from the difference.
    from api import projects_hub

    rows = [
        {"project_id": "a", "owner_email": STEVE, "profile": "default"},
        {"project_id": "b", "owner_email": STEVE, "profile": "research"},
    ]
    owned = projects_hub.visible_projects_by_owner(rows, STEVE)
    assert len(owned) == 2, "the profile split happens after this filter, not inside it"


def test_rollups_count_only_sessions_the_caller_may_see():
    from api import projects_hub

    projects = [{"project_id": "p1", "name": "Alpha", "owner_email": STEVE, "profile": "default"}]
    sessions = [
        _session("s1", "p1", STEVE, updated=300.0),
        _session("s2", "p1", MICHAEL, updated=900.0),
        _session("s3", "p1", None, updated=800.0),
    ]
    row = projects_hub.project_rollups(projects, sessions, STEVE, "default")[0]
    assert row["conversation_count"] == 1
    assert row["last_activity_at"] == 300.0, (
        "last activity must come from visible rows only"
    )


def test_an_empty_project_says_why_instead_of_showing_a_bare_zero():
    from api import projects_hub

    projects = [{"project_id": "p1", "name": "Alpha", "owner_email": STEVE, "profile": "default"}]
    row = projects_hub.project_rollups(projects, [], STEVE, "default")[0]
    assert row["conversation_count"] == 0
    assert isinstance(row.get("empty_reason"), str) and row["empty_reason"].strip()
    assert row["source"] == "project_record"


def test_the_list_endpoint_never_ships_workspace_paths():
    from api import projects_hub

    projects = [{"project_id": "p1", "name": "Alpha", "owner_email": STEVE, "profile": "default"}]
    sessions = [_session("s1", "p1", STEVE, workspace="/home/steve/secret-client")]
    row = projects_hub.project_rollups(projects, sessions, STEVE, "default")[0]
    assert "workspace_paths" not in row
    assert row["workspace_count"] == 1
    assert "secret-client" not in repr(row)


def test_both_system_projects_are_labelled_and_neither_is_minted():
    from api import projects_hub

    for name in ("Cron Jobs", "Webhooks"):
        assert projects_hub.is_system_project({"name": name}), name
    assert not projects_hub.is_system_project({"name": "Alpha"})
    assert "CRON_PROJECT_NAME" in HUB and "WEBHOOK_PROJECT_NAME" in HUB


def _hub_identifiers():
    """Every name the hub module actually references, comments excluded."""
    tree = ast.parse(HUB)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            for alias in node.names:
                names.add(alias.name)
    return names


def test_the_hub_module_never_writes_and_never_dials_out():
    names = _hub_identifiers()
    for forbidden in ("ensure_cron_project", "ensure_webhook_project", "save_projects"):
        assert forbidden not in names, (
            f"{forbidden} back-tags and persists legacy rows; a GET must not write"
        )
    for forbidden in ("urllib", "requests", "http.client", "api.integrations",
                      "socket", "httpx"):
        assert forbidden not in names, forbidden


# ── Section gating ──────────────────────────────────────────────────────────

def test_every_section_names_the_permission_its_own_route_requires():
    from api.governance.catalog import route_permission
    from api.projects_hub import SECTION_PERMISSIONS

    assert SECTION_PERMISSIONS["workspaces"] == route_permission("/api/workspaces", "GET")
    assert SECTION_PERMISSIONS["jobs"] == route_permission("/api/crons", "GET")
    assert SECTION_PERMISSIONS["status"] == route_permission("/api/project-os", "GET")
    assert SECTION_PERMISSIONS["integrations"] == route_permission("/api/mcp/servers", "GET")
    assert SECTION_PERMISSIONS["notes_drawer"] == route_permission("/api/notes/sources", "GET")
    assert SECTION_PERMISSIONS["delivery"] == route_permission("/api/kanban", "GET")
    assert "kanban:read" not in SECTION_PERMISSIONS.values(), (
        "kanban:read is granted by no role in the policy; the board routes are "
        "sessions:read"
    )


def test_a_section_the_caller_lacks_is_absent_rather_than_empty():
    from api import projects_hub

    project = {"project_id": "p1", "name": "Alpha", "owner_email": STEVE, "profile": "default"}
    sessions = [_session("s1", "p1", STEVE, workspace="/srv/alpha")]
    caps = dict(ALL_SECTIONS, files=False, workspaces=False)
    detail = projects_hub.project_detail(
        project, sessions, STEVE, "default", caps,
        workspace_entries=[{"name": "Alpha", "path": "/srv/alpha"}],
        list_dir_reader=lambda name: [{"name": "secret.txt"}],
    )
    assert "files" not in detail and "workspaces" not in detail
    assert not any(k.startswith("files") for k in detail), "not even a count may leak"
    assert "secret.txt" not in repr(detail)


def test_caller_capabilities_close_when_a_permission_is_refused():
    from api import projects_hub

    caps = projects_hub.caller_capabilities(
        {"email": STEVE}, permission_check=lambda _i, perm: perm != "mcp:read")
    assert caps["integrations"] is False
    assert caps["jobs"] is True


def test_caller_capabilities_default_to_the_governance_body_sink_check():
    from api import projects_hub

    with patch("api.governance.enforce.identity_has_permission",
               return_value=False) as check:
        caps = projects_hub.caller_capabilities({"email": STEVE})
    assert check.called, "the section gate must reuse the governance resolver"
    assert not any(caps.values())


def test_a_capability_check_that_raises_closes_the_section():
    from api import projects_hub

    def _boom(_identity, _permission):
        raise RuntimeError("policy unreadable")

    caps = projects_hub.caller_capabilities({"email": STEVE}, permission_check=_boom)
    assert not any(caps.values()), "governance is deny by default"


def test_the_hub_omits_the_integration_inventory_without_mcp_read():
    # The blocking defect the plan review found: the inventory is mcp:read
    # data on a sessions:read route.
    assert "capabilities.get(\"integrations\")" in ROUTES
    block = ROUTES[ROUTES.index("def _handle_projects_hub(handler)"):][:1400]
    assert 'payload["integrations"] = _projects_hub_integrations(capabilities)' in block
    assert 'if capabilities.get("integrations"):' in block


def test_the_route_withholds_the_inventory_from_a_caller_without_mcp_read():
    """The blocking defect, exercised on the real handler rather than its source."""
    import api.routes as routes

    captured = {}

    def _capture(_handler, payload, **kw):
        captured["payload"] = payload
        return True

    project = {"project_id": "p1", "name": "Alpha", "owner_email": STEVE,
               "profile": "default"}
    with patch.object(routes, "j", _capture), \
            patch("api.ownership.request_owner_scope", return_value="all"), \
            patch("api.governance.enforce.identity_has_permission",
                  side_effect=lambda _i, perm: perm != "mcp:read"), \
            patch.object(routes, "load_projects", return_value=[project]), \
            patch.object(routes, "all_sessions", return_value=[]):
        routes.handle_get(_handler_stub(), _parsed("/api/projects/hub"))
    assert "integrations" not in captured["payload"]
    assert "integrations" not in captured["payload"]["sections"]


def test_the_detail_route_withholds_files_from_a_caller_without_files_read():
    import api.routes as routes

    captured = {}

    def _capture(_handler, payload, **kw):
        captured["payload"] = payload
        return True

    project = {"project_id": "p1", "name": "Alpha", "owner_email": STEVE,
               "profile": "default"}
    sessions = [_session("s1", "p1", STEVE, workspace="/srv/alpha")]
    with patch.object(routes, "j", _capture), \
            patch("api.ownership.request_owner_scope", return_value="all"), \
            patch("api.governance.enforce.identity_has_permission",
                  side_effect=lambda _i, perm: perm != "files:read"), \
            patch.object(routes, "load_projects", return_value=[project]), \
            patch.object(routes, "all_sessions", return_value=sessions):
        routes.handle_get(
            _handler_stub(), _parsed("/api/projects/hub/detail?project_id=p1"))
    payload = captured["payload"]
    assert "files" not in payload and "workspaces" not in payload
    assert payload["conversations"]["count"] == 1, (
        "the sections the caller IS entitled to must still arrive"
    )


def test_the_route_ships_the_inventory_to_a_caller_with_mcp_read():
    import api.routes as routes

    captured = {}

    def _capture(_handler, payload, **kw):
        captured["payload"] = payload
        return True

    project = {"project_id": "p1", "name": "Alpha", "owner_email": STEVE,
               "profile": "default"}
    with patch.object(routes, "j", _capture), \
            patch("api.ownership.request_owner_scope", return_value="all"), \
            patch("api.governance.enforce.identity_has_permission", return_value=True), \
            patch.object(routes, "load_projects", return_value=[project]), \
            patch.object(routes, "all_sessions", return_value=[]):
        routes.handle_get(_handler_stub(), _parsed("/api/projects/hub"))
    assert isinstance(captured["payload"].get("integrations"), list)


def test_the_notes_drawer_flag_is_gated_separately_on_files_read():
    block = ROUTES[ROUTES.index("def _projects_hub_integrations("):][:1400]
    assert 'capabilities.get("notes_drawer")' in block
    assert "_external_notes_sources_enabled()" in block


# ── Aggregation behaviour ───────────────────────────────────────────────────

def test_workspaces_are_reported_by_name_never_by_path():
    from api import projects_hub

    project = {"project_id": "p1", "name": "Alpha", "owner_email": STEVE, "profile": "default"}
    sessions = [_session("s1", "p1", STEVE, workspace="/srv/alpha")]
    detail = projects_hub.project_detail(
        project, sessions, STEVE, "default", ALL_SECTIONS,
        workspace_entries=[
            {"name": "Alpha", "path": "/srv/alpha"},
            {"name": "Beta", "path": "/srv/beta"},
        ],
    )
    names = [w["name"] for w in detail["workspaces"]["items"]]
    assert names == ["Alpha"], "only spaces backing this project's chats"
    assert "/srv/alpha" not in repr(detail["workspaces"])


def test_no_emitted_string_is_an_absolute_path():
    from api import projects_hub

    project = {"project_id": "p1", "name": "Alpha", "owner_email": STEVE, "profile": "default"}
    sessions = [_session("s1", "p1", STEVE, workspace="/srv/alpha")]
    detail = projects_hub.project_detail(
        project, sessions, STEVE, "default", ALL_SECTIONS,
        workspace_entries=[{"name": "Alpha", "path": "/srv/alpha"}],
        list_dir_reader=lambda name: [{"name": "README.md", "is_dir": False}],
        project_os_reader=lambda name: {"summary": "Ship the hub", "updated_at": 1},
    )
    for text in _strings(detail):
        assert not text.startswith("/"), text
        assert ":\\" not in text, text


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def test_a_job_is_attached_only_through_a_visible_webui_session():
    from api import projects_hub

    project = {"project_id": "p1", "name": "Alpha", "owner_email": STEVE, "profile": "default"}
    sessions = [
        _session("s1", "p1", STEVE),
        _session("s2", "p1", MICHAEL),
    ]
    jobs = [
        {"name": "Mine", "origin": {"platform": "webui", "chat_id": "s1"}},
        {"name": "Theirs", "origin": {"platform": "webui", "chat_id": "s2"}},
        {"name": "Telegram", "origin": {"platform": "telegram", "chat_id": "s1"}},
        {"name": "Nowhere", "origin": {"platform": "webui", "chat_id": "s9"}},
    ]
    detail = projects_hub.project_detail(
        project, sessions, STEVE, "default", ALL_SECTIONS, cron_rows=jobs)
    assert [j["name"] for j in detail["jobs"]["items"]] == ["Mine"]


def test_one_broken_source_cannot_take_down_the_hub():
    from api import projects_hub

    def _boom(_name):
        raise RuntimeError("status file unreadable")

    project = {"project_id": "p1", "name": "Alpha", "owner_email": STEVE, "profile": "default"}
    sessions = [_session("s1", "p1", STEVE, workspace="/srv/alpha")]
    detail = projects_hub.project_detail(
        project, sessions, STEVE, "default", ALL_SECTIONS,
        workspace_entries=[{"name": "Alpha", "path": "/srv/alpha"}],
        project_os_reader=_boom,
        list_dir_reader=_boom,
    )
    assert detail["status"]["items"] == []
    assert detail["status"]["empty_reason"]
    assert detail["files"]["empty_reason"]
    assert detail["conversations"]["count"] == 1, "the healthy sections survive"


def test_every_emitted_item_carries_provenance():
    from api import projects_hub

    project = {"project_id": "p1", "name": "Alpha", "owner_email": STEVE, "profile": "default"}
    sessions = [_session("s1", "p1", STEVE, workspace="/srv/alpha")]
    detail = projects_hub.project_detail(
        project, sessions, STEVE, "default", ALL_SECTIONS,
        workspace_entries=[{"name": "Alpha", "path": "/srv/alpha"}],
        cron_rows=[{"name": "Nightly", "origin": {"platform": "webui", "chat_id": "s1"}}],
        list_dir_reader=lambda name: [{"name": "README.md"}],
        project_os_reader=lambda name: {"summary": "Ship the hub"},
    )
    for key in ("conversations", "workspaces", "files", "jobs", "status"):
        section = detail[key]
        assert section["source"], key
        for item in section["items"]:
            assert item.get("source"), (key, item)


def test_the_board_is_a_labelled_link_and_never_task_rows():
    from api import projects_hub

    project = {"project_id": "p1", "name": "Alpha", "owner_email": STEVE, "profile": "default"}
    detail = projects_hub.project_detail(
        project, [], STEVE, "default", ALL_SECTIONS)
    assert detail["delivery"]["shared_board"] is True
    assert "items" not in detail["delivery"], (
        "the board has no per-user ownership, so its rows are not this "
        "caller's rows"
    )


# ── Integration honesty ─────────────────────────────────────────────────────

def test_nothing_configured_means_every_source_says_not_connected():
    from api import projects_hub

    rows = projects_hub.integration_status({}, {}, None)
    assert rows
    for row in rows:
        assert row["state"] == "not_configured", row
        assert row["seam"].strip()
        assert "connected" not in row["state"]


def test_a_configured_source_is_never_called_readable():
    from api import projects_hub

    rows = {
        r["key"]: r for r in projects_hub.integration_status(
            {"notion": {}, "fireflies": {}},
            {"fireflies": {"connected": True}},
            True,
        )
    }
    assert rows["notes"]["state"] == "configured_not_readable"
    assert rows["meetings"]["state"] == "reader_missing"
    assert rows["code_reviews"]["state"] == "not_configured"


def test_a_seam_never_contradicts_its_own_state():
    from api import projects_hub

    rows = projects_hub.integration_status({"attio": {}}, {}, None)
    row = next(r for r in rows if r["key"] == "client_materials")
    assert row["state"] == "configured_not_readable"
    for candidate in rows:
        assert "connected" not in candidate["seam"].lower(), (
            "the seam must stay true in every state; the configuration claim "
            "belongs to the state, which is derived from evidence"
        )


def test_integration_copy_is_plain_language_without_internals():
    from api import projects_hub

    rows = projects_hub.integration_status({"notion": {}}, {}, True)
    for row in rows:
        for text in (row["label"], row["seam"]):
            lowered = text.lower()
            for forbidden in ("/", "http", "token", "key", "secret", "nango", "_"):
                assert forbidden not in lowered, (forbidden, text)


# ── Route wiring ────────────────────────────────────────────────────────────

def test_both_branches_are_exact_match_and_read_only():
    assert 'if parsed.path == "/api/projects/hub":' in ROUTES
    assert 'if parsed.path == "/api/projects/hub/detail":' in ROUTES
    hub_idx = ROUTES.index('if parsed.path == "/api/projects/hub":')
    projects_idx = ROUTES.index('if parsed.path == "/api/projects":')
    assert hub_idx < projects_idx, (
        "the exact-match hub branches must be reached before the /api/projects "
        "branch that follows them"
    )


def test_a_foreign_project_is_indistinguishable_from_a_missing_one():
    block = ROUTES[ROUTES.index("def _handle_projects_hub_detail("):][:2600]
    assert 'return bad(handler, "Project not found", 404)' in block


def test_the_sessions_branch_ordering_test_is_not_disturbed():
    # tests/test_issue1611_session_profile_filtering.py slices routes.py
    # between the /api/sessions and /api/projects markers and asserts the
    # profile filter runs before the messaging dedupe. The hub branches land
    # inside that slice, so they must not carry either marker.
    block = ROUTES[
        ROUTES.index('parsed.path == "/api/sessions":'):
        ROUTES.index('parsed.path == "/api/projects":')
    ]
    hub = block[block.index('if parsed.path == "/api/projects/hub":'):]
    assert '_profiles_match(s.get("profile"), active_profile)' not in hub
    assert "_keep_latest_messaging_session_per_source(" not in hub


def test_the_detail_route_binds_the_readers_only_when_entitled():
    block = ROUTES[ROUTES.index("def _handle_projects_hub_detail("):][:2600]
    assert 'if capabilities.get("files") else None' in block
    assert 'if capabilities.get("status") else None' in block
    assert "scope_cron_rows_for_caller(" in block, (
        "cron rows must pass the existing cron scope filter first"
    )


# ── Frontend wiring ─────────────────────────────────────────────────────────

def test_the_panel_is_wired_into_the_shell():
    assert 'id="panelProjects"' in INDEX_HTML
    assert 'id="mainProjects"' in INDEX_HTML
    assert '<script src="static/projects.js' in INDEX_HTML
    assert "projects: 'tab_projects'" in PANELS_JS
    assert "if (nextPanel === 'projects') await loadProjectsHub();" in PANELS_JS
    assert "'integrations','projects','plugin'" in PANELS_JS


def test_the_main_view_switching_rules_are_complete():
    assert "main.main > #mainProjects," in STYLE_CSS
    assert "main.main.showing-projects > #mainProjects{display:flex" in STYLE_CSS
    chat_rule = [
        line for line in STYLE_CSS.splitlines()
        if "> #mainChat{display:flex;}" in line and line.startswith("main.main:not(")
    ]
    assert chat_rule, "the chat default-view rule must exist"
    assert ":not(.showing-projects)" in chat_rule[0], (
        "without this the chat view renders behind the Projects panel"
    )


def test_every_server_supplied_field_is_escaped():
    for field in ("p.name", "w.name", "s.title", "j.name", "f.name",
                  "i.summary", "r.seam"):
        assert f"_projEsc(String({field}" in PROJECTS_JS, field


def test_a_refused_request_renders_a_neutral_state_without_a_toast():
    block = PROJECTS_JS[PROJECTS_JS.index("async function loadProjectsHub"):][:900]
    assert "_projUnavailable()" in block
    assert "showToast" not in PROJECTS_JS and "alert(" not in PROJECTS_JS
    assert "projects_unavailable" in PROJECTS_JS


def test_the_client_never_re_adds_a_section_the_server_withheld():
    block = PROJECTS_JS[PROJECTS_JS.index("function _projSectionCard"):][:900]
    assert "if (!section) return '';" in block


def test_every_string_the_panel_can_show_has_an_english_key():
    keys = set()
    for match in PROJECTS_JS.split("_projT('")[1:]:
        keys.add(match.split("'")[0])
    for match in PROJECTS_JS.split('data-i18n="')[1:]:
        keys.add(match.split('"')[0])
    # Two lookups are built from a server-supplied suffix; assert the whole
    # family instead of the prefix.
    keys.discard("projects_source_")
    keys.discard("projects_")
    for source in ("project_record", "conversations", "workspaces",
                   "workspace_files", "scheduled_jobs", "project_os",
                   "kanban_board"):
        keys.add("projects_source_" + source)
    for key in ("meetings", "notes", "code_reviews", "client_materials"):
        keys.add("projects_" + key)
    for key in sorted(keys):
        assert f"{key}:" in EN_JS, key


def test_the_markup_strings_have_english_keys():
    for key in ("tab_projects", "projects_title", "projects_subtitle",
                "projects_desc", "projects_refresh", "projects_empty_title",
                "projects_empty_sub"):
        assert f"{key}:" in EN_JS, key


def test_user_copy_carries_no_internals():
    start = EN_JS.index("tab_projects: 'Projects',")
    block = EN_JS[start:EN_JS.index("tab_integrations:", start)]
    for forbidden in ("http", "Nango", "/home/", "HERMES_", "403", "404",
                      "sessions:read", "mcp:read"):
        assert forbidden not in block, forbidden
