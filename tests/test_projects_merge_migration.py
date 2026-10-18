"""Projects + Spaces merge migration: zero gain/loss, idempotent, reversible."""
import importlib.util
import itertools
import json
from pathlib import Path

import pytest

from api import projects_hub

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pmm", ROOT / "scripts" / "projects_merge_migrate.py")
pmm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pmm)


def _state(tmp_path):
    hermes = tmp_path / "hermes"; state = hermes / "webui"; state.mkdir(parents=True)
    folders = {}
    for name in ("acme", "beta", "shared", "team"):
        d = tmp_path / "f" / name; d.mkdir(parents=True); folders[name] = str(d)
    (state / "projects.json").write_text(json.dumps([
        {"project_id": "t1", "name": "Acme", "owner_email": "o@x.nl", "collaboration": True,
         "members": ["m@x.nl"], "workspace": folders["team"], "profile": "default"},
        {"project_id": "p1", "name": "Beta", "owner_email": "o@x.nl", "profile": "default"},
    ], indent=2), encoding="utf-8")
    (state / "workspaces.json").write_text(json.dumps([
        {"path": folders["acme"], "name": "Acme", "owner_email": "o@x.nl", "members": ["m@x.nl"]},
        {"path": folders["beta"], "name": "Beta", "members": ["only-member@x.nl"]},
        {"path": folders["shared"], "name": "Gedeeld"},
        {"path": folders["team"], "name": "Team"},
        {"path": str(tmp_path / "gone"), "name": "Weg", "owner_email": "o@x.nl"},
    ]), encoding="utf-8")
    prof = hermes / "profiles" / "sales" / "webui_state"; prof.mkdir(parents=True)
    (prof / "workspaces.json").write_text(json.dumps([
        {"path": folders["acme"], "name": "Acme", "owner_email": "s@x.nl"},
    ]), encoding="utf-8")
    (hermes / "dashboard-governance.yaml").write_text(
        "version: 1\nbootstrap_admins:\n  - boss@x.nl\nusers:\n  viewer@x.nl:\n    roles: [creative_studio]\n", encoding="utf-8")
    return state, hermes, folders


def test_mirrored_rules_match_the_app():
    emails = ["", "a@x.nl", "b@x.nl"]
    for owner, members, shared, scope in itertools.product(emails, [[], ["a@x.nl"], ["B@X.NL"]], [False, True],
                                                           ["all", "a@x.nl", "b@x.nl", "c@x.nl"]):
        row = {"kind": "space", "owner_email": owner, "members": members, "shared_with_all": shared}
        assert pmm.space_project_visible(row, scope) == projects_hub.space_project_visible(row, scope)
        assert (row in projects_hub.visible_projects_by_owner([row], scope)) == pmm.space_project_visible(row, scope)


def test_plan_decisions_are_conservative(tmp_path):
    state, hermes, folders = _state(tmp_path)
    rows, decisions = pmm.plan(json.loads((state / "projects.json").read_text()), pmm.load_spaces(state, hermes))
    by_name = {r["name"]: r for r in rows}
    assert "Team" not in by_name  # the team project's own folder is skipped
    assert any(d["decision"] == "skip" and d["space"] == "Team" for d in decisions)
    assert by_name["Gedeeld"]["shared_with_all"] is True and by_name["Gedeeld"]["owner_email"] is None
    assert by_name["Beta (map)"]["members"] == ["only-member@x.nl"]  # name clash with project "Beta"
    assert "Acme (sales)" in by_name  # same name in another profile gets a profile suffix
    assert by_name["Acme (map)"]["owner_email"] == "o@x.nl"  # clash with team project "Acme"
    assert any("does not exist" in r for d in decisions for r in d.get("reasons", []))


def test_apply_verify_idempotent_and_rollback(tmp_path):
    state, hermes, _ = _state(tmp_path)
    original = (state / "projects.json").read_bytes()
    ok, before = pmm.verify(state, hermes)
    assert not ok  # nothing migrated yet: spaces have no project counterpart
    first = pmm.apply(state, hermes)
    assert first["created"] == 5 and first["skipped"] == 1
    ok, after = pmm.verify(state, hermes, Path(first["backup"]))
    assert ok, after
    assert all(not v["gain"] and not v["loss"] for v in after["people"].values())
    second = pmm.apply(state, hermes)
    assert second["created"] == 0
    assert (state / pmm.MARKER).is_file()
    rb = pmm.rollback(state, hermes, None, False)
    assert rb["removed_projects"] == 5
    assert json.loads((state / "projects.json").read_bytes()) == json.loads(original)
    assert not (state / pmm.MARKER).exists()
    pmm.apply(state, hermes)
    pmm.rollback(state, hermes, Path(first["backup"]), True)
    assert json.loads((state / "projects.json").read_bytes()) == json.loads(original)


def test_verify_catches_a_gain(tmp_path):
    state, hermes, _ = _state(tmp_path)
    res = pmm.apply(state, hermes)
    rows = json.loads((state / "projects.json").read_text())
    for r in rows:
        if r.get("kind") == "space" and r["name"] == "Beta (map)":
            r["members"].append("viewer@x.nl")
    (state / "projects.json").write_text(json.dumps(rows), encoding="utf-8")
    ok, result = pmm.verify(state, hermes, Path(res["backup"]))
    assert not ok and result["people"]["viewer@x.nl"]["gain"]


def test_space_projects_follow_the_space_folder_for_conversations():
    project = {"project_id": "sp1", "kind": "space", "folders": [{"path": "/w/acme"}]}
    rows = [{"session_id": "a", "workspace": "/w/acme/sub"}, {"session_id": "b", "workspace": "/w/other"},
            {"session_id": "c", "workspace": "/w/acme", "project_id": "x"}]
    assert [r["session_id"] for r in projects_hub.project_sessions(project, rows)] == ["a"]


def test_sidebar_list_hides_space_projects_and_ui_hides_spaces_menu_when_merged():
    routes = (ROOT / "api" / "routes.py").read_text(encoding="utf-8")
    assert 'if (parse_qs(parsed.query).get("include_spaces") or ["0"])[0] != "1":' in routes
    css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
    assert 'html[data-sp-merged="1"] [data-panel="workspaces"]{display:none!important;}' in css
    js = (ROOT / "static" / "projects-folders.js").read_text(encoding="utf-8")
    assert "config.merged && !config.classic_spaces" in js
