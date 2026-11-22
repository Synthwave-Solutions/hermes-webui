"""The quickscan roadmap in Studio (api/studio_roadmap.py).

Neutral fixture data only: a made up three month roadmap with a start group and
two blocks. Covered: strict import validation, links that must exist and be
visible to the person saving, evidence and the derived status with fake task
runs in the value ledger, the roll-up, who may read and who may change, the
block in the central summary, and the JavaScript of the page.
"""
from __future__ import annotations

import copy
import json
import sqlite3
import subprocess
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import api.org_structure as org  # noqa: E402
import api.studio as studio  # noqa: E402
import api.studio_library as lib  # noqa: E402
import api.studio_report as report  # noqa: E402
import api.studio_roadmap as rm  # noqa: E402
import api.value_tracking as vt  # noqa: E402
from api.governance.models import GovernancePolicy  # noqa: E402

ADMIN = "boss@example.com"
MEMBER = "tom@example.com"
OUTSIDER = "eve@example.com"
CONSULTANT = "carla@partner.example"
DEVELOPER = "dev@partner.example"
QA = "quinn@partner.example"


def roadmap_doc() -> dict:
    return {
        "report_version": "1.2", "title": "Roadmap voorbeeld", "start_date": "2026-12-09", "weeks": 12,
        "steering_weeks": [1, 5, 9],
        "planning_note": "Deze planning is indicatief: een voorstel, geen offerte en geen toezegging.",
        "notes": {"proposal": "Een menukaart.", "estimate": "", "start": "Start na de verkenning."},
        "prerequisites": ["Toegang tot het boekhoudsysteem"], "open_points": ["Privacytoets"], "pilot_criteria": ["Nulmeting per domein"],
        "groups": [
            {"id": "start", "name": "Start", "rows": [
                {"id": "kickoff", "name": "Kick-off en verkenning", "kind": "werksessie", "start_week": 1, "weeks": 2}]},
            {"id": "blok1", "name": "Blok 1: debiteuren", "short": "Debiteuren", "phase": "p1", "rows": [
                {"id": "b1-fundament", "name": "Koppeling en toegang", "kind": "fundament", "start_week": 2, "weeks": 2},
                {"id": "b1-agent", "name": "Aanmaningen voorbereiden", "start_week": 4, "weeks": 3},
                {"id": "b1-sessie", "name": "Werksessie team", "kind": "werksessie", "start_week": 6, "weeks": 1}]},
            {"id": "blok2", "name": "Blok 2: offertes", "phase": "p2", "rows": [
                {"id": "b2-fundament", "name": "Sjablonen verzamelen", "kind": "fundament", "start_week": 6, "weeks": 2},
                {"id": "b2-agent", "name": "Offertes opstellen", "kind": "agent", "start_week": 8, "weeks": 4, "status": "in_progress"}]}],
        "safeguarding": {"name": "Borging en overdracht", "start_week": 11, "weeks": 2},
        "phases": [
            {"id": "p1", "name": "Debiteuren", "summary": "Aanmaningen als concept.", "prerequisites": ["Export van openstaande posten"],
             "human_role": "De medewerker beslist en verstuurt.", "steps": ["Lijst ophalen", "Concepten maken", "Nakijken"],
             "pilot_criteria": ["Doorlooptijd per aanmaning"], "ready_when": "Elke maandag liggen de concepten klaar."},
            {"id": "p2", "name": "Offertes", "ready_when": "Een offerte staat binnen een dag klaar."}],
        "systems": [{"name": "Boekhouding", "status": "te_valideren", "note": "Export bevestigen"}, {"name": "CRM", "status": "voorgesteld"}],
        "diagrams": [{"id": "d1", "title": "Aanmaning", "phase": "p1",
                      "source": "flowchart TD\n  A[Lijst ophalen] --> B{Openstaand?}\n  B -->|Ja| C[Concept maken]\n  B -->|Nee| D[Klaar]\n  C --> E[Medewerker beslist]:::human\n  classDef human fill:#eee"}],
    }


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


@pytest.fixture
def env(monkeypatch, tmp_path):
    import api.config as config
    import api.profiles as profiles

    root = tmp_path / "hermes"
    homes = {"default": root, "finbot": root / "profiles" / "finbot"}
    for home in homes.values():
        (home / "cron").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "finance" / "aanmaning-opstellen").mkdir(parents=True)
    (root / "skills" / "finance" / "aanmaning-opstellen" / "SKILL.md").write_text("# skill", encoding="utf-8")
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setattr(config, "STATE_DIR", state)
    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", root)
    monkeypatch.setattr(profiles, "_is_isolated_profile_mode", lambda: False)
    monkeypatch.setattr(profiles, "_is_root_profile", lambda name: name == "default")
    monkeypatch.setattr(profiles, "get_hermes_home_for_profile",
                        lambda name: homes.get(str(name or "default") or "default", root / "profiles" / str(name)))
    monkeypatch.setattr(profiles, "list_profiles_api", lambda **_kw: [{"name": "default"}, {"name": "finbot"}])
    policy = GovernancePolicy(bootstrap_admins=(ADMIN,), installation_kind="hq")
    monkeypatch.setattr(org, "_policy", lambda: policy)
    monkeypatch.setattr(vt, "_last_collect", 0.0)
    report._reset_for_tests()
    admin = org.scope_for(ADMIN, policy=policy)
    org.apply(admin, {"op": "department.save", "key": "finance", "name": "Finance"})
    org.apply(admin, {"op": "team.save", "department": "finance", "name": "Debiteuren", "members": [MEMBER]})
    for email, role in ((CONSULTANT, "consultant"), (DEVELOPER, "developer"), (QA, "qa")):
        org.apply(admin, {"op": "partner.save", "email": email, "name": role.title(), "role": role})
    return SimpleNamespace(policy=policy, homes=homes, state=state, now=time.time())


def V(email, env):
    return org.scope_for(email, policy=env.policy)


def _jobs(env, jobs):
    (env.homes["finbot"] / "cron" / "jobs.json").write_text(json.dumps({"jobs": jobs}), encoding="utf-8")


def _job(job_id, **extra):
    job = {"id": job_id, "name": f"Taak {job_id}", "prompt": "p", "owner_email": MEMBER, "enabled": True,
           "schedule_display": "Maandag 08:00", "origin": {"user_id": MEMBER}}
    job.update(extra)
    return job


def _runs(env, rows):
    """Finished executions of the engine: (execution id, job id, completed or failed, seconds ago)."""
    conn = sqlite3.connect(env.homes["finbot"] / "cron" / "executions.db")
    conn.execute("CREATE TABLE IF NOT EXISTS executions (id TEXT PRIMARY KEY, job_id TEXT, source TEXT, process_id TEXT, pid INT, "
                 "status TEXT, claimed_at TEXT, started_at TEXT, finished_at TEXT, error TEXT)")
    conn.executemany("INSERT INTO executions VALUES (?,?,?,?,?,?,?,?,?,?)",
                     [(eid, jid, "s", "p", 1, status, _iso(env.now - ago), _iso(env.now - ago), _iso(env.now - ago + 60), None)
                      for eid, jid, status, ago in rows])
    conn.commit()
    conn.close()
    vt.collect(force=True)


def _world(env, email=ADMIN, sees_job=None):
    return rm.World(view=V(email, env), sees_job=sees_job, now=env.now + 120)


# ── Import validation ────────────────────────────────────────────────────────

def test_import_stores_a_normalised_roadmap_and_audits_it(env):
    doc = rm.import_roadmap(V(ADMIN, env), roadmap_doc(), _world(env))
    assert doc["start_date"] == "2026-12-07"                    # week 1 starts on the Monday
    assert [g["id"] for g in doc["groups"]] == ["start", "blok1", "blok2", "safeguarding"]
    assert doc["groups"][1]["rows"][1]["kind"] == "agent"         # no kind is an agent row
    assert doc["groups"][3]["rows"][0] == dict(doc["groups"][3]["rows"][0], kind="borging", start_week=11, weeks=2, status="planned", links=[])
    assert doc["groups"][2]["rows"][1]["status"] == "in_progress" and doc["steering_weeks"] == [1, 5, 9]
    stored = rm.load()
    assert stored["report_version"] == "1.2" and stored["updated_by"] == ADMIN
    audit = [json.loads(line) for line in (env.state / "studio" / "roadmap_audit.jsonl").read_text().splitlines()]
    assert audit[-1]["action"] == "import" and audit[-1]["detail"] == {"report_version": "1.2", "previous_version": None,
                                                                       "groups": 4, "rows": 7, "phases": 2}
    # A newer report replaces it and the audit names the previous version.
    newer = dict(roadmap_doc(), report_version="1.3")
    rm.import_roadmap(V(CONSULTANT, env), newer, _world(env, CONSULTANT))
    audit = [json.loads(line) for line in (env.state / "studio" / "roadmap_audit.jsonl").read_text().splitlines()]
    assert audit[-1]["actor"] == CONSULTANT and audit[-1]["detail"]["previous_version"] == "1.2"


def _broken(change):
    doc = copy.deepcopy(roadmap_doc())
    change(doc)
    return doc


LONG_DASH = chr(0x2014)


@pytest.mark.parametrize("change", [
    lambda d: d.pop("report_version"),
    lambda d: d.pop("start_date"),
    lambda d: d.update(start_date="next week"),
    lambda d: d.update(weeks=2),
    lambda d: d.update(weeks=500),
    lambda d: d.update(weeks="12"),
    lambda d: d.update(steering_weeks=[1, 40]),
    lambda d: d.update(groups=[]),
    lambda d: d.update(groups=[{"name": "x", "rows": []}] * 17),
    lambda d: d.update(surprise=True),
    lambda d: d["groups"][1].update(html="x"),
    lambda d: d["groups"][1]["rows"][0].update(kind="mijlpaal"),
    lambda d: d["groups"][1]["rows"][0].update(start_week=12, weeks=3),
    lambda d: d["groups"][1]["rows"][0].update(status="done"),
    lambda d: d["groups"][1]["rows"][0].update(name="<b>vet</b>"),
    lambda d: d["groups"][1]["rows"][0].update(name="x" * 121),
    lambda d: d["groups"][1]["rows"][0].update(name="Eerst " + LONG_DASH + " dan"),
    lambda d: d["groups"][1]["rows"][0].update(id="kickoff"),
    lambda d: d["groups"][1]["rows"].extend([{"name": "r", "start_week": 1}] * 30),
    lambda d: d["groups"][1].update(phase="p9"),
    lambda d: d["groups"][1]["rows"][0].update(links=[{"type": "website", "ref": "x"}]),
    lambda d: d["groups"][1]["rows"][0].update(links=[{"type": "job", "ref": "../../etc"}]),
    lambda d: d["groups"][1]["rows"][0].update(delivered_at="gisteren"),
    lambda d: d["phases"][0].update(steps=["a"] * 21),
    lambda d: d["phases"][0].update(ready_when="<script>alert(1)</script>"),
    lambda d: d["systems"][0].update(status="klaar"),
    lambda d: d["diagrams"][0].update(source="sequenceDiagram\n A->>B: hoi"),
    lambda d: d["diagrams"][0].update(source="flowchart TD\n A[<img src=x onerror=alert(1)>]"),
    lambda d: d["diagrams"][0].update(source='flowchart TD\n A --> B\n click A href "https://example.com"'),
    lambda d: d["diagrams"][0].update(source="flowchart TD\n" + "A --> B\n" * 2000),
    lambda d: d.update(notes={"proposal": "x", "extra": "y"}),
    lambda d: d.update(title="t" * 400000),
])
def test_import_is_validated_strictly(env, change):
    with pytest.raises(ValueError):
        rm.import_roadmap(V(ADMIN, env), _broken(change), _world(env))
    assert rm.load() is None


# ── Links ────────────────────────────────────────────────────────────────────

def test_links_must_exist_and_be_visible_to_who_saves(env):
    _jobs(env, [_job("j1"), _job("j2", owner_email=OUTSIDER)])
    uc = studio.update(V(MEMBER, env), {"team": "finance/debiteuren", "title": "Aanmaningen"})
    private = studio.update(V(OUTSIDER, env), {"title": "Alleen van Eve"})
    pb = lib.save_playbook(V(MEMBER, env), {"title": "Zo maak je aanmaningen", "team": "finance/debiteuren", "status": "published"})
    rm.import_roadmap(V(ADMIN, env), roadmap_doc(), _world(env))
    carla = V(CONSULTANT, env)
    own_only = lambda profile, job: job.get("owner_email") == MEMBER            # the consultant may see j1, not j2
    world = _world(env, CONSULTANT, own_only)

    doc = rm.update_item(carla, {"target": "row", "id": "b1-agent", "status": "built", "delivered_at": "2026-12-20", "note": "Staat klaar",
                                 "links": [{"type": "job", "ref": "finbot:j1"}, {"type": "bot", "ref": "finbot"},
                                           {"type": "skill", "ref": "aanmaning-opstellen"}, {"type": "use_case", "ref": uc["id"]},
                                           {"type": "playbook", "ref": pb["id"]}, {"type": "job", "ref": "finbot:j1"}]}, world)
    row = doc["groups"][1]["rows"][1]
    assert [link["type"] for link in row["links"]] == ["job", "bot", "skill", "use_case", "playbook"]      # the double one is dropped
    assert row["status"] == "built" and row["delivered_at"] == "2026-12-20" and row["note"] == "Staat klaar"
    assert rm.update_item(carla, {"target": "row", "id": "b1-sessie", "links": [{"type": "job", "ref": "j1"}]}, world)   # a bare id that is unique

    for link in ({"type": "job", "ref": "finbot:nope"}, {"type": "job", "ref": "finbot:j2"},          # missing, and not hers to see
                 {"type": "bot", "ref": "ghostbot"}, {"type": "skill", "ref": "bestaat-niet"},
                 {"type": "use_case", "ref": "uc_000000000000"}, {"type": "use_case", "ref": private["id"]},
                 {"type": "playbook", "ref": "pb_000000000000"}):
        with pytest.raises(ValueError, match="not found"):
            rm.update_item(carla, {"target": "row", "id": "b2-agent", "links": [link]}, world)
    with pytest.raises(ValueError):
        rm.update_item(carla, {"target": "row", "id": "b2-agent", "name": "Andere naam"}, world)            # only execution fields
    with pytest.raises(KeyError):
        rm.update_item(carla, {"target": "row", "id": "nope", "status": "live"}, world)
    # An import with a link that does not exist is refused as a whole.
    bad = roadmap_doc()
    bad["phases"][0]["links"] = [{"type": "bot", "ref": "ghostbot"}]
    with pytest.raises(ValueError, match="not found"):
        rm.import_roadmap(V(ADMIN, env), bad, _world(env))
    # A phase takes links too, and something linked earlier may stay after it has gone.
    rm.update_item(carla, {"target": "phase", "id": "p1", "links": [{"type": "job", "ref": "finbot:j1"}]}, world)
    _jobs(env, [])
    gone = _world(env, CONSULTANT, own_only)
    doc = rm.update_item(carla, {"target": "phase", "id": "p1", "note": "Taak is opgeruimd"}, gone)
    assert doc["phases"][0]["links"] == [{"type": "job", "ref": "finbot:j1"}]
    options = rm.link_options(carla, _world(env, CONSULTANT, own_only))
    assert options["bot"] == [{"value": "default", "label": "default"}, {"value": "finbot", "label": "finbot"}]
    assert options["skill"] == [{"value": "aanmaning-opstellen", "label": "aanmaning-opstellen"}]
    assert [o["value"] for o in options["use_case"]] == [uc["id"]] and [o["value"] for o in options["playbook"]] == [pb["id"]]


# ── Evidence and the derived status ──────────────────────────────────────────

def test_status_is_derived_from_what_really_ran(env):
    value = {"before_minutes": 60, "review_minutes": 15, "source": "playbook", "confidence": "estimated"}
    _jobs(env, [_job("ran", value=value), _job("idle", enabled=False), _job("failed"), _job("old")])
    uc = studio.update(V(MEMBER, env), {"team": "finance/debiteuren", "title": "Aanmaningen", "process": {
        "frequency": {"count": 10, "per": "week"}, "as_is": [{"step": "Handwerk", "minutes": 60}],
        "to_be": [{"step": "Nakijken", "minutes": 12, "building_block": "human"}]}})
    doc = roadmap_doc()
    doc["groups"][1]["rows"][0].update(status="live")                                            # claimed by hand, nothing linked
    doc["groups"][1]["rows"][1].update(links=[{"type": "job", "ref": "finbot:ran"}, {"type": "use_case", "ref": uc["id"]}])
    doc["groups"][1]["rows"][2].update(status="live", links=[{"type": "job", "ref": "finbot:idle"}])
    doc["groups"][2]["rows"][0].update(links=[{"type": "job", "ref": "finbot:failed"}, {"type": "skill", "ref": "aanmaning-opstellen"}])
    doc["groups"][2]["rows"][1].update(links=[{"type": "job", "ref": "finbot:old"}])               # in_progress by hand
    rm.import_roadmap(V(ADMIN, env), doc, _world(env))
    _runs(env, [("e1", "ran", "completed", 3 * 86400), ("e2", "ran", "completed", 10 * 86400), ("e3", "ran", "failed", 86400),
                ("e4", "failed", "failed", 2 * 86400), ("e5", "old", "completed", 45 * 86400)])

    result = rm.read(V(ADMIN, env), _world(env))
    rows = result["rows"]
    # live: a linked task completed a run in the last 30 days.
    assert rows["b1-agent"] == dict(rows["b1-agent"], status="live", manual="planned", derived=True, differs=True)
    job = rows["b1-agent"]["evidence"][0]
    assert job == dict(job, found=True, live=True, name="Taak ran", enabled=True, schedule="Maandag 08:00", runs_30d=3, ok_runs_30d=2,
                       hours_saved_30d=1.5, last_result="failed", bot="finbot")
    assert job["last_run_at"] == pytest.approx(env.now - 86400 + 60, abs=5)
    case = rows["b1-agent"]["evidence"][1]
    assert case == dict(case, found=True, phase="discover", hours_week_before=10.0, hours_week_after=2.0, hours_week_saved=8.0, name="Aanmaningen")
    # built: linked, but switched off and never run. The hand-typed "live" does not count.
    assert rows["b1-sessie"] == dict(rows["b1-sessie"], status="built", manual="live", differs=True)
    assert rows["b1-sessie"]["evidence"][0]["enabled"] is False and rows["b1-sessie"]["evidence"][0]["runs_30d"] == 0
    # built: the only run failed; a skill never makes a row live.
    assert rows["b2-fundament"]["status"] == "built"
    assert rows["b2-fundament"]["evidence"][1] == dict(rows["b2-fundament"]["evidence"][1], installed=True, enabled=True, last_used_at=None)
    # built: the last completed run is older than 30 days.
    assert rows["b2-agent"] == dict(rows["b2-agent"], status="built", manual="in_progress", differs=True)
    # Nothing linked: what was set by hand stands, and is marked as not derived.
    assert rows["b1-fundament"] == dict(rows["b1-fundament"], status="live", manual="live", derived=False, differs=False, evidence=[])
    assert rows["kickoff"]["status"] == "planned" and rows["kickoff"]["derived"] is False

    blocks = {b["id"]: b for b in result["rollup"]["blocks"]}
    assert blocks["blok1"] == dict(blocks["blok1"], rows_total=3, rows_planned=0, rows_built=1, rows_live=2,
                                   baseline_hours_week_saved=8.0, measured_hours_week_saved=round(1.5 / (30 / 7), 1))
    assert blocks["blok2"] == dict(blocks["blok2"], rows_total=2, rows_built=2, rows_live=0, measured_hours_week_saved=0.0)
    assert result["rollup"] == dict(result["rollup"], rows_total=7, rows_planned=2, rows_built=3, rows_live=2, baseline_hours_week_saved=8.0)

    # A linked bot that is active makes a row live as well (its task completed a run).
    rm.update_item(V(ADMIN, env), {"target": "row", "id": "kickoff", "links": [{"type": "bot", "ref": "finbot"}]}, _world(env))
    rm.update_item(V(ADMIN, env), {"target": "row", "id": "safeguarding", "links": [{"type": "bot", "ref": "default"}]}, _world(env))
    rows = rm.read(V(ADMIN, env), _world(env))["rows"]
    assert rows["kickoff"]["status"] == "live" and rows["kickoff"]["evidence"][0] == dict(rows["kickoff"]["evidence"][0], active=True, tasks_total=4)
    assert rows["safeguarding"]["status"] == "built" and rows["safeguarding"]["evidence"][0]["active"] is False

    # Somebody who may not see the task gets the same status, without its details.
    hidden = rm.read(V(MEMBER, env), _world(env, MEMBER, lambda profile, job: False))
    assert hidden["rows"]["b1-agent"]["status"] == "live" and hidden["editable"] is False
    assert hidden["rows"]["b1-agent"]["evidence"][0] == {"type": "job", "ref": "finbot:ran", "found": True, "visible": False, "live": True}

    # The task disappears: the link is shown as missing and the row falls back.
    _jobs(env, [])
    after = rm.read(V(ADMIN, env), _world(env))["rows"]["b2-agent"]
    assert after["evidence"][0]["found"] is False and after["status"] == "in_progress" and after["derived"] is False


# ── Rights ───────────────────────────────────────────────────────────────────

def test_who_reads_and_who_changes(env):
    with pytest.raises(PermissionError):
        rm.import_roadmap(V(MEMBER, env), roadmap_doc(), _world(env, MEMBER))
    for email in (ADMIN, CONSULTANT, DEVELOPER):
        rm.import_roadmap(V(email, env), roadmap_doc(), _world(env, email))
        assert rm.read(V(email, env), _world(env, email))["editable"] is True
        rm.update_item(V(email, env), {"target": "row", "id": "kickoff", "status": "in_progress"}, _world(env, email))
    for email in (MEMBER, QA):                                   # a team member and qa read only
        got = rm.read(V(email, env), _world(env, email))
        assert got["editable"] is False and got["roadmap"]["report_version"] == "1.2"
        for change in (lambda v, w: rm.import_roadmap(v, roadmap_doc(), w),
                       lambda v, w: rm.update_item(v, {"target": "row", "id": "kickoff", "status": "live"}, w),
                       lambda v, w: rm.link_options(v, w), lambda v, w: rm.remove(v)):
            with pytest.raises(PermissionError):
                change(V(email, env), _world(env, email))
    with pytest.raises(PermissionError):                         # no place in the structure: not even reading
        rm.read(V(OUTSIDER, env), _world(env, OUTSIDER))
    with pytest.raises(PermissionError):                         # removing stays with the organisation admin
        rm.remove(V(CONSULTANT, env))

    sent = []
    old_j, old_scope, old_world = rm.j, org.request_scope, rm._world
    rm.j = lambda handler, payload, status=200, **_kw: sent.append((status, payload))
    rm._world = lambda handler, view: _world(env, view.email)
    try:
        for email, method, body, status in ((QA, "POST", {"op": "update", "target": "row", "id": "kickoff", "status": "live"}, 403),
                                            (QA, "GET", None, 200), (OUTSIDER, "GET", None, 403),
                                            (CONSULTANT, "POST", {"op": "update", "target": "row", "id": "kickoff", "status": "live"}, 200),
                                            (CONSULTANT, "POST", {"op": "nonsense"}, 400), (CONSULTANT, "POST", {"op": "remove"}, 403),
                                            (ADMIN, "POST", {"op": "import", "roadmap": {"weeks": 1}}, 400)):
            org.request_scope = lambda handler, email=email: V(email, env)
            parsed = SimpleNamespace(path="/api/studio/roadmap", query="")
            assert (studio.handle_get(None, parsed) if method == "GET" else studio.handle_post(None, parsed, body)) is True
            assert sent[-1][0] == status, (email, method, body)
        org.request_scope = lambda handler: V(ADMIN, env)
        studio.handle_post(None, SimpleNamespace(path="/api/studio/roadmap", query=""), {"op": "remove"})
        assert sent[-1][0] == 200 and sent[-1][1]["roadmap"] is None and rm.load() is None
    finally:
        rm.j, org.request_scope, rm._world = old_j, old_scope, old_world


# ── The block in the central summary ─────────────────────────────────────────

def test_summary_carries_roadmap_counts_and_no_free_text(env):
    assert "roadmap" not in report.build_summary()                # no roadmap, no field
    _jobs(env, [_job("ran", value={"before_minutes": 70, "review_minutes": 10, "source": "playbook", "confidence": "estimated"})])
    doc = roadmap_doc()
    doc["groups"][1]["rows"][1].update(links=[{"type": "job", "ref": "finbot:ran"}], note="GEHEIM notitie")
    doc["groups"][2]["rows"][0].update(links=[{"type": "skill", "ref": "aanmaning-opstellen"}])
    rm.import_roadmap(V(ADMIN, env), doc, _world(env))
    assert report.stats()["dirty"] is True                        # a roadmap change is pushed like a Studio save
    _runs(env, [("e1", "ran", "completed", 86400), ("e2", "ran", "completed", 2 * 86400)])
    block = report.build_summary()["roadmap"]
    assert set(block) == {"report_version", "updated_at", "blocks", "rows_total", "rows_built", "rows_live", "measured_hours_week_saved"}
    assert block == dict(block, report_version="1.2", rows_total=7, rows_built=1, rows_live=1,
                         measured_hours_week_saved=round(2.0 / (30 / 7), 1))
    assert block["updated_at"].endswith("Z")
    assert block["blocks"] == [{"name": "Start", "rows_total": 1, "rows_built": 0, "rows_live": 0},
                               {"name": "Blok 1: debiteuren", "rows_total": 3, "rows_built": 0, "rows_live": 1},
                               {"name": "Blok 2: offertes", "rows_total": 2, "rows_built": 1, "rows_live": 0},
                               {"name": "Borging en overdracht", "rows_total": 1, "rows_built": 0, "rows_live": 0}]
    text = json.dumps(block, ensure_ascii=False)
    for leak in ("GEHEIM", "Aanmaningen voorbereiden", "Taak ran", "finbot", "example.com", "indicatief", "flowchart", "Boekhouding"):
        assert leak not in text, leak


# ── The page ─────────────────────────────────────────────────────────────────

def test_roadmap_page_script_is_wired_and_clean():
    source = (REPO / "static" / "studio_plan.js").read_text(encoding="utf-8")
    index = (REPO / "static" / "index.html").read_text(encoding="utf-8")
    assert "static/studio_plan.js" in index and "window.SPPlan" in source
    assert "/api/studio/roadmap" in source and "renderMermaidBlocks" in source and "data-sp-picker" in source
    for text in (source, (REPO / "static" / "studio.css").read_text(encoding="utf-8")):
        assert chr(0x2013) not in text and chr(0x2014) not in text
    if shutil.which("node"):
        proc = subprocess.run(["node", "--check", str(REPO / "static" / "studio_plan.js")], capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, proc.stderr
