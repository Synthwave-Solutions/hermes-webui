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


def test_roadmap_keeps_a_set_start_and_proposes_the_rest(env):
    from datetime import date

    tom = V(OWNER, env)
    today = date(2026, 11, 18)                                     # a Wednesday; its week starts on the 16th
    a = lib.save_item(tom, {"title": "Aanmaningen", "team": "finance/debiteuren", "effort": 2})
    b = lib.save_item(tom, {"title": "Rapport", "team": "finance/debiteuren", "effort": 1})
    c = lib.save_item(tom, {"title": "Vast", "team": "finance/debiteuren", "start": "2026-11-26", "weeks": 2})
    d = lib.save_item(tom, {"title": "Later", "team": "finance/debiteuren", "status": "parked"})
    lib.save_item(tom, {"id": b["id"], "status": "design"})
    p = lib.plan(lib.backlog_items(), today)
    assert c["start"] == "2026-11-23" and p[c["id"]] == {"start": "2026-11-23", "weeks": 2, "end": "2026-12-07", "auto": False}
    assert p[b["id"]] == {"start": "2026-11-16", "weeks": 1, "end": "2026-11-23", "auto": True}   # started work goes first
    assert p[a["id"]]["start"] == "2026-12-07" and p[a["id"]]["weeks"] == 2                        # two weeks do not fit before the fixed one
    assert d["id"] not in p
    lib.save_item(tom, {"id": c["id"], "start": "", "weeks": ""})
    again = lib.plan(lib.backlog_items(), today)
    assert again[c["id"]]["auto"] and again[c["id"]]["weeks"] == 3 and again[a["id"]]["start"] == "2026-11-23"
    with pytest.raises(ValueError):
        lib.save_item(tom, {"id": a["id"], "start": "next week"})


def test_an_idea_can_be_given_to_a_colleague_who_then_sees_and_plans_it(env):
    from datetime import date

    tom, eve = V(OWNER, env), V(OTHER, env)
    a = lib.save_item(tom, {"title": "Aanmaningen", "team": "finance/debiteuren"})
    assert not lib.backlog_for(eve)
    with pytest.raises(ValueError):
        lib.save_item(tom, {"id": a["id"], "assignee": "stranger@example.com"})
    lib.save_item(tom, {"id": a["id"], "assignee": OTHER})
    row = lib.backlog_for(eve)[0]
    assert row["assignee"] == OTHER and row["editable"] and row["plan"]["auto"]
    lib.save_item(eve, {"id": a["id"], "start": "2026-12-01"})
    lib.save_item(eve, {"title": "Leads", "team": "sales/inside", "effort": 1})
    p = lib.plan(lib.backlog_items(), date(2026, 11, 30))
    leads = next(i for i in lib.backlog_items() if i["title"] == "Leads")
    assert p[a["id"]]["start"] == "2026-11-30" and p[leads["id"]]["start"] == "2026-12-21"      # one idea at a time per person
    lib.save_item(tom, {"id": a["id"], "assignee": ""})
    assert not [r for r in lib.backlog_for(eve) if r["id"] == a["id"]]
    assert lib.backlog_for(tom)[0]["assignee"] == OWNER


def test_the_roadmap_shows_what_the_deep_dive_expects_to_save(env):
    tom = V(OWNER, env)
    a = lib.save_item(tom, {"title": "Aanmaningen", "team": "finance/debiteuren"})
    uc = studio.update(tom, {"title": "Aanmaningen", "team": "finance/debiteuren"})
    studio.update(tom, {"id": uc["id"], "phase": "design", "process": {
        "frequency": {"count": 10, "per": "week"},
        "as_is": [{"step": "Handwerk", "minutes": 30}], "to_be": [{"step": "Controle", "minutes": 6}]}})
    lib.save_item(tom, {"id": a["id"], "use_case": uc["id"]})
    row = lib.backlog_for(tom)[0]
    assert row["uc_phase"] == "design" and row["saves_hours_week"] == 4.0
    lib.save_item(tom, {"id": a["id"], "use_case": "uc_000000000000"})
    assert "uc_phase" not in lib.backlog_for(tom)[0]


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


def test_page_text_keeps_title_meta_and_structured_data(monkeypatch):
    html = (b'<html><head><title>Acme | Warmtepompen</title><meta name="description" content="Acme installeert warmtepompen voor bedrijven.">'
            b'<meta property="og:site_name" content="Acme"><script type="application/ld+json">{"@type":"Organization","numberOfEmployees":40}</script>'
            b'<script>var x=1</script></head><body><div id="root"></div></body></html>')

    class Resp:
        headers = type("H", (), {"get_content_charset": lambda self: "utf-8"})()
        def read(self, n): return html
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(lib, "_public_host", lambda host: True)
    import urllib.request
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", lambda self, req, timeout=None: Resp())
    url, text = lib.fetch_public_page("https://acme.example/")
    assert "Titel: Acme | Warmtepompen" in text and "description: Acme installeert warmtepompen" in text
    assert "numberOfEmployees" in text and "var x" not in text


def test_personal_intake_writes_one_entry_into_the_user_notes(env, monkeypatch):
    from api import personal_context
    tom = V(OWNER, env)
    ident = {"email": OWNER}
    personal_context.write(ident, "user", "Houdt van korte mails\n§\nZit op dinsdag op kantoor")
    body = {"role": {"title": "Debiteurenbeheerder", "team": "finance/debiteuren", "seniority": "senior", "work_type": "hybrid",
                     "focus": "Betaaltermijn omlaag\nMinder nabellen"},
            "tasks": [{"name": "Openstaande posten nabellen", "cadence": "weekly", "minutes": 120, "tools": ["Exact"], "kind": "assist"},
                      {"name": "Aanmaningen opstellen", "cadence": "weekly", "minutes": 45, "kind": "automate"},
                      {"name": "", "cadence": "daily"}],
            "tools": "Exact, Outlook", "prefs": {"language": "nl", "tone": "informal", "length": "short", "format": "bullets",
                                                 "never": "Nooit zelf mails versturen"},
            "literacy": {"self": "regular", "score": 2, "answered": True}}
    out = lib.save_person(tom, ident, body)
    notes = personal_context.read_file(personal_context.paths(ident)["user"])
    entries = notes.split("\n§\n")
    assert entries[:2] == ["Houdt van korte mails", "Zit op dinsdag op kantoor"], "the person's own notes stay"
    assert entries[2].startswith(lib.INTAKE_MARK) and "Debiteurenbeheerder, Debiteuren, senior" in entries[2]
    assert "Openstaande posten nabellen (wekelijks)" in entries[2] and "Nooit: Nooit zelf mails versturen" in entries[2]
    assert len(entries[2]) <= lib.INTAKE_NOTE_MAX and out["notes_used"] <= lib.USER_NOTE_LIMIT
    assert len(out["tasks"]) == 2 and out["tasks"][1]["kind"] == "automate"
    # A new intake replaces its entry and nothing else.
    lib.save_person(tom, ident, dict(body, role=dict(body["role"], title="Teamlead debiteuren")))
    entries = personal_context.read_file(personal_context.paths(ident)["user"]).split("\n§\n")
    assert len(entries) == 3 and "Teamlead debiteuren" in entries[2]
    assert lib.load_person(OWNER)["role"]["title"] == "Teamlead debiteuren"
    # The intake also goes along as context in the person's own QuickScan.
    seen = []
    monkeypatch.setattr(studio, "_ask_json", lambda system, user: seen.append(user) or {"goals": [], "opportunities": []})
    doc = studio.update(tom, {"title": "Nabellen"})
    studio.run_step(tom, {"id": doc["id"], "step": "discover", "input": "Ik bel elke week na"})
    assert "Over de persoon" in seen[0] and "Teamlead debiteuren" in seen[0]


def test_user_notes_stay_within_the_agent_limit(env):
    from api import personal_context
    ident = {"email": OTHER}
    personal_context.write(ident, "user", "x" * 1200)
    out = lib.save_person(V(OTHER, env), ident, {"role": {"title": "Accountmanager " * 20}, "tasks": [{"name": "Offertes maken " * 5}]})
    assert out["notes_used"] <= lib.USER_NOTE_LIMIT
    assert personal_context.read_file(personal_context.paths(ident)["user"]).startswith("x" * 1200)


def test_tasks_are_extracted_from_a_description_of_the_week(env, monkeypatch):
    monkeypatch.setattr(studio, "_ask_json", lambda system, user: {"tasks": [
        {"name": "Weekrapport maken", "cadence": "weekly", "minutes": 60, "tools": ["Excel"]},
        {"name": "Mail lezen", "cadence": "nooit", "minutes": "veel"}]})
    tasks = lib.extract_tasks("Elke maandag maak ik het weekrapport in Excel, dat kost een uur.")
    assert tasks[0] == {"name": "Weekrapport maken", "cadence": "weekly", "minutes": 60, "tools": ["Excel"], "kind": ""}
    assert tasks[1]["cadence"] == "weekly" and tasks[1]["minutes"] == 0
    with pytest.raises(ValueError):
        lib.extract_tasks("kort")


def test_full_user_notes_are_left_alone_and_the_intake_is_kept(env):
    from api import personal_context
    ident = {"email": ADMIN}
    personal_context.write(ident, "user", "y" * 1370)
    out = lib.save_person(V(ADMIN, env), ident, {"role": {"title": "Directeur"}})
    assert out["note_written"] is False and out["notes_room"] < 160
    assert personal_context.read_file(personal_context.paths(ident)["user"]) == "y" * 1370
    assert lib.load_person(ADMIN)["role"]["title"] == "Directeur", "the intake itself is still kept for Studio"


def test_wishes_go_into_the_note_and_survive_a_save_from_the_studio_form(env):
    tom, ident = V(OWNER, env), {"email": OWNER}
    out = lib.save_person(tom, ident, {"role": {"title": "Debiteurenbeheerder"}, "wishes": ["mail", "meetings", "onzin", "mail"],
                                        "wish_other": "Declaraties indienen"})
    assert out["wishes"] == ["mail", "meetings"]
    assert "Wil als eerste uit handen geven: mail en chat bijhouden; vergaderingen en de dag voorbereiden; Declaraties indienen." in out["note"]
    # The Studio form does not send wishes; they stay.
    again = lib.save_person(tom, ident, {"role": {"title": "Teamlead debiteuren"}})
    assert again["wishes"] == ["mail", "meetings"] and again["wish_other"] == "Declaraties indienen"


def test_first_tasks_follow_the_intake_and_fall_back_when_the_model_is_off(env, monkeypatch):
    tom, ident = V(OWNER, env), {"email": OWNER}
    lib.save_person(tom, ident, {"role": {"title": "Debiteurenbeheerder"}, "wishes": ["mail", "calendar"],
                                 "tasks": [{"name": "Aanmaningen opstellen", "cadence": "weekly"}], "tools": ["Exact"]})
    seen = {}

    def good(system, user):
        seen["system"], seen["user"] = system, user
        return {"intro": "Gebaseerd op je aanmaningen en je mail.",
                "tasks": [{"kind": "ongoing", "title": "Maak concepten voor de aanmaningen van deze week."},
                          {"kind": "ongoing", "title": "Zet elke maandag de openstaande posten uit Exact klaar"},
                          {"kind": "now", "title": "Vat elke ochtend mijn nieuwe mail samen"}]}

    monkeypatch.setattr(studio, "_ask_json", good)
    out = lib.first_tasks(tom, {"lang": "nl"})
    assert "Aanmaningen opstellen" in seen["user"] and "Nederlands" in seen["system"]
    assert out["personal"] is True and out["intro"] == "Gebaseerd op je aanmaningen en je mail."
    # The first card is always the one to finish now; a closing full stop is dropped.
    assert [t["kind"] for t in out["tasks"]] == ["now", "ongoing", "ongoing"]
    assert out["tasks"][0]["title"] == "Maak concepten voor de aanmaningen van deze week"
    assert len(out["common"]) == 2 and "mail" in out["mail"]
    assert lib.load_person(OWNER)["first_tasks"]["tasks"] == out["tasks"], "kept for the chat's empty state"

    # Too many cards, a title that is too long or a model error: the fixed cards for the person's wishes.
    for bad in ({"tasks": [{"kind": "now", "title": "Een"}]},
                {"intro": "x", "tasks": [{"title": "woord " * 20}, {"title": "Twee"}, {"title": "Drie"}]}):
        monkeypatch.setattr(studio, "_ask_json", lambda system, user, bad=bad: bad)
        out = lib.first_tasks(tom, {"lang": "nl"})
        assert out["personal"] is False
        assert out["tasks"][0] == {"kind": "now", "title": "Maak concepten voor de mails die op mijn antwoord wachten"}
        assert out["tasks"][2]["title"] == "Loop elke maandag mijn agenda van de week met me door"

    def boom(system, user):
        raise RuntimeError("no model")

    monkeypatch.setattr(studio, "_ask_json", boom)
    out = lib.first_tasks(tom, {"lang": "en"})
    assert out["personal"] is False and out["tasks"][0]["title"] == "Draft replies to the mails waiting for my answer"
    # A later save of the intake keeps the cards.
    lib.save_person(tom, ident, {"role": {"title": "Teamlead debiteuren"}})
    assert lib.load_person(OWNER)["first_tasks"]["lang"] == "en"


def test_first_tasks_without_an_intake_do_not_call_the_model(env, monkeypatch):
    def never(system, user):
        raise AssertionError("no model call without answers")

    monkeypatch.setattr(studio, "_ask_json", never)
    out = lib.first_tasks(V(OTHER, env), {})
    assert out["personal"] is False and [t["kind"] for t in out["tasks"]] == ["now", "ongoing", "ongoing"]
    assert len({t["title"] for t in out["tasks"]} | set(out["common"])) == 5, "no card twice"


def test_the_chat_intake_is_offered_once(env, monkeypatch):
    eve = V(OTHER, env)
    assert lib.intake_offer(lib.load_person(OTHER)) is False, "an install switches the offer on itself"
    monkeypatch.setenv("SP_INTAKE_OFFER", "1")
    assert lib.intake_offer(lib.load_person(OTHER)) is True
    lib.onboarding_state(eve, {"dismissed": True})
    assert lib.intake_offer(lib.load_person(OTHER)) is False
    # Someone who saved the intake is not asked again, and "later" survives that save.
    lib.save_person(V(OWNER, env), {"email": OWNER}, {"role": {"title": "Debiteurenbeheerder"}})
    assert lib.intake_offer(lib.load_person(OWNER)) is False
    lib.save_person(eve, {"email": OTHER}, {"role": {"title": "Accountmanager"}})
    assert lib.load_person(OTHER)["onboarding"]["dismissed_at"]


# ── Partners in the backlog and the playbooks (22 Nov 2026) ─────────────────

CONSULTANT = "carla@partner.example"
QA = "quinn@partner.example"


def _partners(policy, *rows):
    admin = org.scope_for(ADMIN, policy=policy)
    for email, role in rows:
        org.apply(admin, {"op": "partner.save", "email": email, "name": "P", "role": role})


def test_partner_works_on_team_backlog_and_can_be_assignee(env):
    _partners(env, (CONSULTANT, "consultant"), (QA, "qa"))
    tom, carla, quinn = V(OWNER, env), V(CONSULTANT, env), V(QA, env)
    a = lib.save_item(tom, {"title": "Aanmaningen", "team": "finance/debiteuren"})
    lib.save_item(V(OTHER, env), {"title": "Leads", "team": "sales/inside"})
    loose = lib.save_item(tom, {"title": "Los idee"})                       # no team: not for the partner
    assert {i["title"] for i in lib.backlog_for(carla)} == {"Aanmaningen", "Leads"}
    assert all(i["editable"] for i in lib.backlog_for(carla))
    assert not any(i["removable"] for i in lib.backlog_for(carla))          # the screen offers no delete that would be refused
    assert all(i["removable"] for i in lib.backlog_for(tom))
    assert lib.save_item(carla, {"id": a["id"], "status": "chosen", "assignee": CONSULTANT})["assignee"] == CONSULTANT
    with pytest.raises(PermissionError):
        lib.save_item(carla, {"id": loose["id"], "status": "chosen"})
    with pytest.raises(PermissionError):
        lib.save_item(carla, {"id": lib.save_item(V(OTHER, env), {"title": "Weg", "team": "sales/inside"})["id"], "delete": True})
    # A teamless idea the partner made is theirs.
    own = lib.save_item(carla, {"title": "Eigen notitie"})
    assert own["id"] in {i["id"] for i in lib.backlog_for(carla)}
    # qa reads the same ideas and changes none.
    assert {i["title"] for i in lib.backlog_for(quinn)} == {"Aanmaningen", "Leads", "Weg"}
    assert not any(i["editable"] for i in lib.backlog_for(quinn))
    with pytest.raises(PermissionError):
        lib.save_item(quinn, {"id": a["id"], "status": "parked"})
    with pytest.raises(PermissionError):
        lib.autopilot(quinn, a["id"])
    # Once the assignment is gone, so is the partner access. What is left is what any
    # address has: the idea they are assignee of and the one they made themselves.
    org.apply(org.scope_for(ADMIN, policy=env), {"op": "partner.remove", "email": CONSULTANT})
    gone = V(CONSULTANT, env)
    assert {i["title"] for i in lib.backlog_for(gone)} == {"Aanmaningen", "Eigen notitie"}
    with pytest.raises(PermissionError):
        lib.save_item(gone, {"id": lib.backlog_for(V(OTHER, env))[0]["id"], "status": "parked"})


def test_partner_edits_team_playbooks_and_qa_only_reads(env):
    _partners(env, (CONSULTANT, "consultant"), (QA, "qa"))
    tom, carla, quinn = V(OWNER, env), V(CONSULTANT, env), V(QA, env)
    draft = lib.save_playbook(tom, {"title": "Aanmaningen", "team": "finance/debiteuren"})      # still a draft
    private = lib.save_playbook(tom, {"title": "Kladje"})
    assert [p["id"] for p in lib.playbooks_for(carla)] == [draft["id"]]
    assert lib.save_playbook(carla, {"id": draft["id"], "summary": "Aangevuld"})["summary"] == "Aangevuld"
    with pytest.raises(PermissionError):
        lib.save_playbook(carla, {"id": private["id"], "summary": "x"})
    assert lib._pb_removable(carla, draft) is False
    assert [p["id"] for p in lib.playbooks_for(quinn)] == [draft["id"]]
    with pytest.raises(PermissionError):
        lib.save_playbook(quinn, {"id": draft["id"], "summary": "x"})
