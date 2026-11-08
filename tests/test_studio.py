"""Use Case Studio backend (api/studio.py): storage, scope, the three model steps."""
from __future__ import annotations

import pytest

import api.org_structure as org
import api.studio as studio
from api.governance.models import GovernancePolicy

OWNER = "tom@example.com"
OTHER = "eve@example.com"
ADMIN = "boss@example.com"


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
    answers = {
        "discover": {"title": "Debiteuren", "goals": [{"name": "Minder openstaand", "kpi": "DSO 41 naar 30"}],
                     "opportunities": [{"id": "o1", "title": "Wekelijkse aanmaningen", "impact": 5, "effort": 2,
                                        "building_block": "task", "pain": "Handwerk", "why": "Sneller betaald"},
                                       {"id": "o2", "title": "Maatwerk portaal", "impact": 3, "effort": 5,
                                        "building_block": "custom"}]},
        "design": {"as_is": [{"step": "Lijst uit SnelStart", "actor": "mens", "minutes": 30}],
                   "to_be": [{"step": "Agent maakt aanmaningen", "actor": "agent", "building_block": "task"},
                             {"step": "Medewerker verstuurt", "actor": "mens", "building_block": "human"}],
                   "metrics": [{"name": "DSO", "baseline": "41", "target": "30"}]},
        "playbook": {"components": [
            {"type": "task", "name": "Aanmaningen maandag", "schedule": "0 8 * * 1", "prompt": "Maak concepten",
             "before_minutes": 45, "review_minutes": 5, "per": "run"},
            {"type": "skill", "name": "Aanmaning opstellen", "description": "Huisstijl", "content": "1. Lees"},
            {"type": "human", "name": "Nakijken", "who": OWNER, "what": "Concepten versturen"},
            {"type": "weird", "name": "x"}]},
    }

    def fake(system, user):
        key = "discover" if system is studio.DISCOVER else "design" if system is studio.DESIGN else "playbook"
        return answers[key]

    monkeypatch.setattr(studio, "_ask_json", fake)
    monkeypatch.setattr(studio, "_reuse_candidates", lambda text, limit=3: ["Taak: bestaande debiteurenlijst"])
    return policy


def _view(email, policy):
    return org.scope_for(email, policy=policy)


def test_full_flow_and_scope(env):
    owner = _view(OWNER, env)
    doc = studio.update(owner, {"team": "finance/debiteuren"})
    assert doc["owner"] == OWNER and doc["phase"] == "discover"
    doc = studio.run_step(owner, {"id": doc["id"], "step": "discover", "input": "Ik bel elke week facturen na"})
    assert [o["id"] for o in doc["opportunities"]] == ["o1", "o2"] and doc["title"] == "Debiteuren"
    assert doc["notes"][0]["role"] == "user" and doc["notes"][-1]["role"] == "agent"
    with pytest.raises(ValueError):
        studio.run_step(owner, {"id": doc["id"], "step": "design", "input": "x"})  # nothing chosen yet
    studio.update(owner, {"id": doc["id"], "selected": "o1"})
    doc = studio.run_step(owner, {"id": doc["id"], "step": "design", "input": "Eerst lijst, dan mails"})
    assert doc["process"]["to_be"][0]["reuse"] == ["Taak: bestaande debiteurenlijst"]
    doc = studio.run_step(owner, {"id": doc["id"], "step": "playbook", "input": ""})
    comps = doc["playbook"]["components"]
    assert [c["type"] for c in comps] == ["task", "skill", "human"]  # unknown type dropped
    assert comps[0]["before_minutes"] == 45 and comps[0]["per"] == "run" and doc["playbook"]["version"] == 1
    doc = studio.update(owner, {"id": doc["id"], "build_log": [{"key": comps[0]["key"], "type": "task", "status": "ok", "ref": "x"}]})
    assert doc["build_log"][0]["status"] == "ok"
    # Others do not see it; organisation admins do.
    assert studio.list_for(_view(OTHER, env)) == []
    assert [r["id"] for r in studio.list_for(_view(ADMIN, env))] == [doc["id"]]
    with pytest.raises(PermissionError):
        studio.update(_view(OTHER, env), {"id": doc["id"], "title": "hack"})


def test_invalid_input_is_refused(env):
    owner = _view(OWNER, env)
    with pytest.raises(ValueError):
        studio.update(owner, {"team": "nope/nope"})
    with pytest.raises(KeyError):
        studio.update(owner, {"id": "../etc/passwd"})
    doc = studio.update(owner, {})
    with pytest.raises(ValueError):
        studio.run_step(owner, {"id": doc["id"], "step": "launch"})
