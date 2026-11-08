"""Backlog, the agent that works an idea out, and Playbooks (api/studio_library.py)."""
from __future__ import annotations

import base64
import time

import pytest

import api.org_structure as org
import api.studio as studio
import api.studio_library as lib
from api.governance.models import GovernancePolicy

OWNER = "tom@example.com"
OTHER = "eve@example.com"
ADMIN = "boss@example.com"
PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()


@pytest.fixture
def env(monkeypatch, tmp_path):
    import api.config as config

    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "state")
    (tmp_path / "state").mkdir()
    policy = GovernancePolicy(bootstrap_admins=(ADMIN,), installation_kind="hq")
    monkeypatch.setattr(org, "_policy", lambda: policy)
    admin = org.scope_for(ADMIN, policy=policy)
    org.apply(admin, {"op": "department.save", "key": "finance", "name": "Finance"})
    org.apply(admin, {"op": "team.save", "department": "finance", "name": "Debiteuren", "members": [OWNER]})
    org.apply(admin, {"op": "department.save", "key": "sales", "name": "Sales"})
    org.apply(admin, {"op": "team.save", "department": "sales", "name": "Inside", "members": [OTHER]})

    def fake(system, user):
        if system is studio.DESIGN:
            return {"as_is": [{"step": "Handwerk", "actor": "mens", "minutes": 30}],
                    "to_be": [{"step": "Agent doet het", "actor": "agent", "building_block": "task"}]}
        if system is studio.PLAYBOOK:
            return {"components": [{"type": "task", "name": "Taak", "schedule": "0 8 * * 1", "prompt": "p",
                                    "before_minutes": 20, "review_minutes": 2}]}
        return {"title": "Zo maak je aanmaningen", "summary": "Kort", "trigger": "Maandag",
                "steps": [{"title": "Open de chat", "actor": "jij", "text": "Typ: maak concepten"}]}

    monkeypatch.setattr(studio, "_ask_json", fake)
    monkeypatch.setattr(studio, "_reuse_candidates", lambda text, limit=3: [])
    return policy


def V(email, policy):
    return org.scope_for(email, policy=policy)


def test_backlog_scope_rank_and_status(env):
    tom, eve = V(OWNER, env), V(OTHER, env)
    a = lib.save_item(tom, {"title": "Aanmaningen", "team": "finance/debiteuren", "impact": 5, "effort": 2})
    b = lib.save_item(tom, {"title": "Rapport", "team": "finance/debiteuren"})
    lib.save_item(eve, {"title": "Leads", "team": "sales/inside"})
    assert [i["title"] for i in lib.backlog_for(tom)] == ["Aanmaningen", "Rapport"]
    assert [i["title"] for i in lib.backlog_for(eve)] == ["Leads"]
    assert len(lib.backlog_for(V(ADMIN, env))) == 3
    lib.reorder(tom, [b["id"], a["id"]])
    assert [i["title"] for i in lib.backlog_for(tom)] == ["Rapport", "Aanmaningen"]
    with pytest.raises(PermissionError):
        lib.save_item(eve, {"id": a["id"], "status": "parked"})
    with pytest.raises(ValueError):
        lib.save_item(tom, {"id": a["id"], "status": "nonsense"})
    lib.save_item(tom, {"id": a["id"], "delete": True})
    assert [i["title"] for i in lib.backlog_for(tom)] == ["Rapport"]


def test_agent_works_an_idea_out_to_the_dry_run(env):
    tom = V(OWNER, env)
    item = lib.save_item(tom, {"title": "Aanmaningen", "team": "finance/debiteuren", "pain": "Handwerk"})
    state = lib.autopilot(tom, item["id"])
    for _ in range(100):
        if lib._AUTOPILOT[item["id"]].get("done"):
            break
        time.sleep(0.05)
    assert lib._AUTOPILOT[item["id"]]["step"] == "done", lib._AUTOPILOT[item["id"]]
    doc = studio._load(state["use_case"])
    assert doc["phase"] == "build" and doc["playbook"]["components"][0]["before_minutes"] == 20
    assert next(i for i in lib.backlog_items() if i["id"] == item["id"])["status"] == "design"


def test_playbook_visibility_media_and_draft(env):
    tom, eve, admin = V(OWNER, env), V(OTHER, env), V(ADMIN, env)
    pb = lib.save_playbook(tom, {"title": "Werkwijze", "team": "finance/debiteuren", "steps": [{"title": "Stap 1", "text": "Doe x"}]})
    assert pb["status"] == "draft" and lib.playbooks_for(eve) == []
    media = lib.save_media(tom, {"playbook": pb["id"], "type": "image/png", "data": PNG})
    pb = lib.save_playbook(tom, {"id": pb["id"], "steps": [{"title": "Stap 1", "text": "Doe x", "media": [dict(media, caption="scherm")]}],
                                 "status": "published", "visibility": "team"})
    assert pb["steps"][0]["media"][0]["file"] == media["file"]
    assert lib.playbooks_for(eve) == []                        # team-only, other team
    assert [p["id"] for p in lib.playbooks_for(admin)] == [pb["id"]]
    pb = lib.save_playbook(tom, {"id": pb["id"], "visibility": "org"})
    assert lib.playbooks_for(eve)[0]["cover"] == media["file"]
    with pytest.raises(PermissionError):
        lib.save_playbook(eve, {"id": pb["id"], "title": "hack"})
    with pytest.raises(ValueError):
        lib.save_media(tom, {"playbook": pb["id"], "type": "text/html", "data": PNG})
    # Injected media names are dropped.
    pb = lib.save_playbook(tom, {"id": pb["id"], "steps": [{"title": "x", "media": [{"file": "../../etc/passwd", "kind": "image"}]}]})
    assert pb["steps"][0]["media"] == []
    # Draft from a use case.
    doc = studio.update(tom, {"title": "Debiteuren", "team": "finance/debiteuren"})
    draft = lib.draft_from_use_case(tom, doc["id"])
    assert draft["title"] == "Zo maak je aanmaningen" and draft["steps"][0]["actor"] == "jij" and draft["use_case"] == doc["id"]
