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


def test_shared_prompts_follow_team_department_and_organisation(env):
    tom, eve, boss = V(OWNER, env), V(OTHER, env), V(ADMIN, env)
    t = lib.save_prompt(tom, {"label": "Aanmaning", "text": "Schrijf een vriendelijke aanmaning", "category": "Debiteuren",
                              "scope": "team", "team": "finance/debiteuren"})
    d = lib.save_prompt(tom, {"text": "Vat de maandcijfers samen", "scope": "department", "department": "finance"})
    o = lib.save_prompt(eve, {"label": "Mail korter", "text": "Maak deze mail korter", "scope": "org"})
    seen = lambda v: {p["id"] for p in lib.prompts_for(v)["prompts"]}
    assert seen(tom) == {t["id"], d["id"], o["id"]}
    assert seen(eve) == {o["id"]}, "another team and department see only the organisation prompt"
    assert seen(boss) == {t["id"], d["id"], o["id"]}
    assert lib.prompts_for(tom)["categories"] == ["Debiteuren"]
    with pytest.raises(PermissionError):
        lib.save_prompt(eve, {"text": "x", "scope": "team", "team": "finance/debiteuren"})
    with pytest.raises(PermissionError):
        lib.save_prompt(eve, {"text": "x", "scope": "department", "department": "finance"})
    with pytest.raises(PermissionError):
        lib.save_prompt(eve, {"id": t["id"], "op": "delete"})
    with pytest.raises(ValueError):
        lib.save_prompt(tom, {"text": "", "scope": "org"})
    with pytest.raises(ValueError):
        lib.save_prompt(tom, {"text": "x", "scope": "private"})
    assert lib.save_prompt(eve, {"id": o["id"], "op": "use"})["uses"] == 1
    assert lib.prompts_for(tom)["prompts"][0]["id"] == o["id"], "most used first"
    edited = lib.save_prompt(tom, {"id": t["id"], "label": "Aanmaning niveau 1"})
    assert edited["text"] == "Schrijf een vriendelijke aanmaning" and edited["scope"] == "team"
    assert lib.save_prompt(boss, {"id": t["id"], "op": "delete"}) == {"ok": True}


def test_organisation_profile_is_admin_only_and_feeds_the_studio_prompts(env, monkeypatch):
    tom, boss = V(OWNER, env), V(ADMIN, env)
    assert lib.context_text() == ""
    with pytest.raises(PermissionError):
        lib.save_profile(tom, {"name": "X"})
    p = lib.save_profile(boss, {"name": "Acme Installatie", "sector": "Installatietechniek", "size": "40 medewerkers",
                                "website": "acme.example", "goals": "Sneller offreren\nMinder handwerk",
                                "systems": "Exact, Outlook, Excel", "policy": "Geen klantdata naar Amerikaanse modellen"})
    assert p["website"] == "https://acme.example" and p["goals"] == ["Sneller offreren", "Minder handwerk"]
    assert p["systems"] == ["Exact", "Outlook", "Excel"] and p["updated_by"] == ADMIN
    ctx = lib.context_text()
    assert ctx.startswith("Acme Installatie (Installatietechniek, 40 medewerkers)") and "Exact, Outlook" in ctx
    assert "Geen klantdata" in ctx
    seen = []
    monkeypatch.setattr(studio, "_ask_json", lambda system, user: seen.append(user) or {"goals": [], "opportunities": []})
    doc = studio.update(tom, {"title": "Offertes", "team": "finance/debiteuren"})
    studio.run_step(tom, {"id": doc["id"], "step": "discover", "input": "Ik maak offertes in Word"})
    assert "Over de organisatie" in seen[0] and "Acme Installatie" in seen[0]
    # Keeps what is not sent along.
    p2 = lib.save_profile(boss, {"sector": "Bouw"})
    assert p2["name"] == "Acme Installatie" and p2["sector"] == "Bouw"


def test_research_refuses_private_addresses(env):
    boss = V(ADMIN, env)
    for url in ("http://127.0.0.1/", "http://localhost:8787/", "http://10.0.0.5/", "file:///etc/passwd", "ftp://example.com"):
        with pytest.raises(ValueError):
            lib.fetch_public_page(url)
    with pytest.raises(PermissionError):
        lib.research_profile(V(OWNER, env), "https://example.com")
    with pytest.raises(ValueError):
        lib.research_profile(boss, "")


def test_research_proposes_fields_without_saving(env, monkeypatch):
    boss = V(ADMIN, env)
    pages = {"https://acme.example/": ("https://acme.example/", "Acme installeert warmtepompen voor bedrijven. Wij werken met Exact.\n\nLINKS: /over-ons /contact"),
             "https://acme.example/over-ons": ("https://acme.example/over-ons", "Opgericht in 1998, 40 medewerkers.\n\nLINKS: ")}
    monkeypatch.setattr(lib, "fetch_public_page", lambda url: pages[url])
    monkeypatch.setattr(studio, "_ask_json", lambda system, user: {"name": "Acme", "sector": "Installatie", "size": "40 medewerkers",
                                                                    "systems": ["Exact"], "summary": "Installateur van warmtepompen"})
    out = lib.research_profile(boss, "acme.example/")
    assert out["proposal"]["name"] == "Acme" and out["proposal"]["systems"] == ["Exact"]
    assert out["sources"] == ["https://acme.example/", "https://acme.example/over-ons"]
    assert lib.load_profile() == {}, "research proposes, it does not save"
