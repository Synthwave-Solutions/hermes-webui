"""Team structure, value per task and bot, Management (8 Nov 2026).

Michaël: "elke scheduled job moet dat hebben en elke bot ook obv wat een taak
eerst kostte en wat het nu kostte en er moet een soort van management scherm
komen en er moet team structuur inkomen".

Covers api/org_structure.py (scope, mutations, audit), api/value_tracking.py
(validation, writing a job's value, the run ledger, pricing) and
api/management.py (per-team numbers, decisions, scope filtering).
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import api.org_structure as org
import api.value_tracking as vt
import api.management as mgmt
from api.governance.models import GovernancePolicy

ADMIN = "boss@example.com"
LEAD = "lisa@example.com"
MEMBER = "tom@example.com"
OTHER = "eve@example.com"


@pytest.fixture
def env(monkeypatch, tmp_path):
    import api.config as config
    import api.profiles as profiles

    root = tmp_path / "hermes"
    homes = {"default": root, "finbot": root / "profiles" / "finbot"}
    for home in homes.values():
        (home / "cron").mkdir(parents=True, exist_ok=True)
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setattr(config, "STATE_DIR", state_dir)
    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", root)
    monkeypatch.setattr(profiles, "_is_isolated_profile_mode", lambda: False)
    monkeypatch.setattr(profiles, "_is_root_profile", lambda name: name == "default")
    monkeypatch.setattr(profiles, "get_hermes_home_for_profile",
                        lambda name: homes.get(str(name or "default") or "default", root / "profiles" / str(name)))
    monkeypatch.setattr(profiles, "list_profiles_api", lambda **_kw: [{"name": "default"}, {"name": "finbot"}])
    policy = GovernancePolicy(bootstrap_admins=(ADMIN,), installation_kind="hq")
    monkeypatch.setattr(org, "_policy", lambda: policy)
    monkeypatch.setattr(vt, "_last_collect", 0.0)
    return SimpleNamespace(root=root, homes=homes, state_dir=state_dir, policy=policy)


@pytest.fixture
def engine_store(monkeypatch):
    """The real engine's cron.jobs when it imports, else a minimal stand-in
    with the same store contract: the store is wherever JOBS_FILE points
    (api/profiles.cron_profile_context_for_home re-points it per bot)."""
    try:
        import importlib

        return importlib.import_module("cron.jobs")
    except Exception:
        pass
    import contextlib
    import types

    cron_pkg = types.ModuleType("cron")
    cron_pkg.__path__ = []
    jobs_mod = types.ModuleType("cron.jobs")
    jobs_mod.HERMES_DIR = jobs_mod.CRON_DIR = jobs_mod.JOBS_FILE = jobs_mod.OUTPUT_DIR = None

    def load_jobs():
        path = Path(jobs_mod.JOBS_FILE)
        return json.loads(path.read_text())["jobs"] if path.exists() else []

    def save_jobs(jobs, removed_ids=None, replace=False):
        path = Path(jobs_mod.JOBS_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"jobs": jobs}))

    jobs_mod.load_jobs = load_jobs
    jobs_mod.save_jobs = save_jobs
    jobs_mod._save_jobs_unlocked = save_jobs
    jobs_mod._jobs_lock = contextlib.nullcontext
    monkeypatch.setitem(sys.modules, "cron", cron_pkg)
    monkeypatch.setitem(sys.modules, "cron.jobs", jobs_mod)
    return jobs_mod



def _view(email):
    return org.scope_for(email, policy=org._policy())


def _jobs(home: Path, jobs: list) -> None:
    (home / "cron" / "jobs.json").write_text(json.dumps({"jobs": jobs}), encoding="utf-8")


def _read(home: Path) -> list:
    return json.loads((home / "cron" / "jobs.json").read_text(encoding="utf-8"))["jobs"]


def _job(job_id, **extra):
    job = {"id": job_id, "name": f"Job {job_id}", "prompt": "p", "owner_email": MEMBER, "enabled": True,
           "schedule": {"kind": "cron", "expr": "0 8 * * 1"}, "schedule_display": "Mondays 08:00",
           "last_status": "ok", "origin": {"user_id": MEMBER}}
    job.update(extra)
    return job


def _structure(env):
    admin = _view(ADMIN)
    org.apply(admin, {"op": "department.save", "key": "finance", "name": "Finance", "hourly_rate": 60})
    org.apply(admin, {"op": "team.save", "department": "finance", "name": "Debiteuren",
                      "lead": LEAD, "members": [MEMBER]})
    org.apply(admin, {"op": "department.save", "key": "sales", "name": "Sales", "admins": [OTHER]})
    org.apply(admin, {"op": "team.save", "department": "sales", "name": "Inside sales", "members": [OTHER]})
    return org.load()


# ── Structure and scope ──────────────────────────────────────────────────────

def test_platform_admin_sees_all_and_others_none(env):
    assert _view(ADMIN).scope == org.SCOPE_ALL
    assert _view(OTHER).scope == org.SCOPE_NONE
    assert _view("").scope == org.SCOPE_NONE


def test_team_crud_and_scope_derivation(env):
    data = _structure(env)
    assert data["teams"]["finance/debiteuren"]["members"] == [LEAD, MEMBER]  # lead is also a member
    lead = _view(LEAD)
    assert lead.scope == org.SCOPE_TEAMS and "finance/debiteuren" in lead.lead_teams
    member = _view(MEMBER)
    assert member.member_teams == {"finance/debiteuren"}
    dept_admin = _view(OTHER)
    assert dept_admin.scope == org.SCOPE_DEPARTMENTS and dept_admin.departments == {"sales"}


def test_department_admin_edits_only_own_department(env):
    _structure(env)
    sales_admin = _view(OTHER)
    org.apply(sales_admin, {"op": "team.save", "department": "sales", "name": "Field sales", "members": []})
    with pytest.raises(PermissionError):
        org.apply(sales_admin, {"op": "team.save", "department": "finance", "name": "Hack"})
    with pytest.raises(PermissionError):
        org.apply(_view(LEAD), {"op": "team.save", "department": "finance", "name": "Nope"})


def test_snapshot_filters_teams_by_scope_and_hides_rates(env):
    _structure(env)
    member_snap = org.snapshot(_view(MEMBER))
    assert set(member_snap["teams"]) == {"finance/debiteuren"}
    assert "hourly_rate" not in member_snap["teams"]["finance/debiteuren"]
    admin_snap = org.snapshot(_view(ADMIN))
    assert set(admin_snap["teams"]) == {"finance/debiteuren", "sales/inside-sales"}
    assert admin_snap["departments"]["finance"]["hourly_rate"] == 60


def test_member_move_and_reporting_lines(env):
    _structure(env)
    admin = _view(ADMIN)
    org.apply(admin, {"op": "member.move", "email": MEMBER, "from": "finance/debiteuren", "to": "sales/inside-sales"})
    data = org.load()
    assert MEMBER not in data["teams"]["finance/debiteuren"]["members"]
    assert MEMBER in data["teams"]["sales/inside-sales"]["members"]
    org.apply(admin, {"op": "person.save", "email": MEMBER, "reports_to": LEAD, "title": "Medewerker"})
    with pytest.raises(ValueError):
        org.apply(admin, {"op": "person.save", "email": LEAD, "reports_to": MEMBER})  # circle
    audit = (env.state_dir / "org_structure" / "audit.jsonl").read_text().strip().splitlines()
    assert len(audit) >= 6 and json.loads(audit[-1])["actor"] == ADMIN


def test_invalid_input_is_refused(env):
    admin = _view(ADMIN)
    with pytest.raises(ValueError):
        org.apply(admin, {"op": "department.save", "key": "Bad Key", "name": "x"})
    org.apply(admin, {"op": "department.save", "key": "ops", "name": "Ops"})
    with pytest.raises(ValueError):
        org.apply(admin, {"op": "team.save", "department": "ops", "name": "T", "members": ["not-an-email"]})
    with pytest.raises(KeyError):
        org.apply(admin, {"op": "team.save", "department": "nope", "name": "T"})


# ── Value validation and writing ─────────────────────────────────────────────

def test_value_requires_minutes_or_a_reason(env):
    with pytest.raises(ValueError):
        vt.validate_value({"task": "x"})
    with pytest.raises(ValueError):
        vt.validate_value({"unknown": True})
    assert vt.validate_value({"unknown": True, "unknown_reason": "new process"})["unknown"] is True
    clean = vt.validate_value({"before_minutes": 45, "review_minutes": 5, "task": " Debiteuren  lijst "})
    assert clean == {"before_minutes": 45, "review_minutes": 5, "task": "Debiteuren lijst", "rationale": "",
                     "source": "owner", "confidence": "confirmed"}
    with pytest.raises(ValueError):
        vt.validate_value({"before_minutes": 10, "secret": "x"})


def test_set_and_confirm_job_value_in_its_store(env, engine_store):
    _structure(env)
    _jobs(env.homes["finbot"], [_job("j1")])
    saved = vt.set_job_value("j1", "finbot", {"before_minutes": 40, "review_minutes": 5, "source": "ai_estimate",
                                             "team": "finance/debiteuren"}, ADMIN)
    assert saved["value"]["confidence"] == "estimated" and saved["value"]["set_by"] == ADMIN
    vt.confirm_job_value("j1", "finbot", "less", MEMBER)
    value = _read(env.homes["finbot"])[0]["value"]
    assert value["confidence"] == "confirmed" and value["before_minutes"] == 28 and value["team"] == "finance/debiteuren"
    assert value["confirmed_by"] == MEMBER


# ── Ledger, pricing and Management ───────────────────────────────────────────

def _executions(home: Path, rows):
    conn = sqlite3.connect(home / "cron" / "executions.db")
    conn.execute("CREATE TABLE executions (id TEXT PRIMARY KEY, job_id TEXT, source TEXT, process_id TEXT, pid INT, "
                 "status TEXT, claimed_at TEXT, started_at TEXT, finished_at TEXT, error TEXT)")
    conn.executemany("INSERT INTO executions VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()


def _state(home: Path, rows):
    conn = sqlite3.connect(home / "state.db")
    conn.execute("CREATE TABLE sessions (id TEXT, source TEXT, user_id TEXT, model TEXT, started_at REAL, ended_at REAL, "
                 "last_activity_at REAL, message_count INT, input_tokens INT, output_tokens INT, cache_read_tokens INT, "
                 "cache_write_tokens INT, estimated_cost_usd REAL, actual_cost_usd REAL, cost_status TEXT, title TEXT)")
    conn.executemany("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()


def _iso(ts):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def test_collect_management_and_scope(env, engine_store, monkeypatch):
    _structure(env)
    now = time.time()
    home = env.homes["finbot"]
    _jobs(home, [_job("j1", value={"before_minutes": 45, "review_minutes": 5, "source": "owner",
                                   "confidence": "confirmed", "team": "finance/debiteuren"}),
                 _job("j2", name="Broken", failure_streak=4, last_status="error", owner_email=OTHER),
                 _job("j3", name="No value", owner_email="nobody@example.com")])
    _executions(home, [
        ("e1", "j1", "s", "p", 1, "completed", _iso(now - 3600), _iso(now - 3600), _iso(now - 3500), None),
        ("e2", "j1", "s", "p", 1, "completed", _iso(now - 7200), _iso(now - 7200), _iso(now - 7100), None),
        ("e3", "j1", "s", "p", 1, "failed", _iso(now - 9000), _iso(now - 9000), _iso(now - 8990), "x"),
        ("e4", "j2", "s", "p", 1, "failed", _iso(now - 9000), _iso(now - 9000), _iso(now - 8990), "x"),
    ])
    _state(home, [("c1", "cron", "", "synthwave-auto", now - 3600, now - 3500, now - 3500, 3, 100000, 20000, 0, 0,
                   0, None, "unknown", "Job j1 · Nov 08 09:00"),
                  ("w1", "webui", MEMBER, "synthwave-auto", now - 600, None, now - 500, 6, 50000, 5000, 0, 0, 0, None,
                   "unknown", "Offerte voor klant")])
    monkeypatch.setattr(mgmt, "_bots", lambda: {"finbot": {"name": "finbot", "title": "Finance Bot", "kind": "bot",
                                                           "role": "", "reports_to": "", "serves": ["finance/debiteuren"],
                                                           "duties": [], "avatar_url": "", "color": ""}})
    stats = vt.collect(force=True)
    assert stats["runs"] == 4 and stats["chats"] == 1
    assert vt.collect(force=True)["runs"] == 0  # idempotent

    admin = _view(ADMIN)
    model = mgmt.build(admin, 28, now - 28 * 86400, now + 60)
    team = next(t for t in model["teams"] if t["key"] == "finance/debiteuren")
    assert team["runs"] == 3 and team["ok_runs"] == 2 and team["failed_runs"] == 1
    assert team["saved_minutes"] == 80  # 2 ok runs x (45 - 5); failed run saves nothing
    assert team["net_eur"] == 80.0  # 80 min at EUR 60/h, AI cost unknown counts as 0 in net but is flagged
    assert team["unpriced_tokens"] > 0
    assert model["totals"]["pricing_set"] is False
    kinds = {d["kind"] for d in model["decisions"]}
    assert {"failing", "missing_value", "unassigned"} <= kinds

    vt.save_pricing({"synthwave-auto": {"in": 10, "out": 50, "cache": 1}}, ADMIN)
    model = mgmt.build(admin, 28, now - 28 * 86400, now + 60)
    team = next(t for t in model["teams"] if t["key"] == "finance/debiteuren")
    assert team["ai_cost_eur"] > 0 and team["net_eur"] < 80.0

    # A department admin of sales sees only sales and no unassigned bucket.
    sales = mgmt.build(_view(OTHER), 28, now - 28 * 86400, now + 60)
    assert {t["key"] for t in sales["teams"]} == {"sales/inside-sales"}
    assert all(j["team"] == "sales/inside-sales" for j in sales["jobs"])

    # The chart for a team member: own team only, no money.
    chart = mgmt.chart(_view(MEMBER))
    teams = [t for d in chart["departments"] for t in d["teams"]]
    assert [t["key"] for t in teams] == ["finance/debiteuren"]
    assert "net_eur" not in teams[0]["stats"] and chart["unassigned"] is None


def test_chat_label_only_by_the_person_who_chatted(env):
    now = time.time()
    _state(env.homes["finbot"], [("w1", "webui", MEMBER, "m", now - 60, None, now - 30, 4, 10, 10, 0, 0, 0, None,
                                  "unknown", "t")])
    vt.collect(force=True)
    key = "finbot:w1"
    with pytest.raises(PermissionError):
        vt.label_chat(key, "Offerte", OTHER, 30)
    row = vt.label_chat(key, "Offerte", MEMBER, 30)
    assert row["label_state"] == "confirmed" and row["saved_minutes"] == 30


def test_ai_cost_sources():
    pricing = {"models": {"m": {"in": 1, "out": 2, "cache": 0}}}
    assert vt.ai_cost_eur("m", 1_000_000, 1_000_000, 0, None, pricing) == (3.0, "price_table")
    assert vt.ai_cost_eur("x", 10, 0, 0, None, pricing) == (None, "unknown")
    assert vt.ai_cost_eur("x", 0, 0, 0, None, pricing) == (0.0, "none")
    assert vt.ai_cost_eur("x", 10, 0, 0, 1.0, pricing)[1] == "provider"


def test_bot_responsibility_value_fields_validate():
    from api.bot_metadata import validate_responsibilities

    rows = validate_responsibilities([{"title": "Offerte", "minutes_before": 120, "minutes_now": 25,
                                       "times_per_week": 3, "value_source": "owner", "value_confidence": "confirmed"}])
    assert rows[0]["minutes_before"] == 120 and rows[0]["times_per_week"] == 3.0
    with pytest.raises(ValueError):
        validate_responsibilities([{"title": "x", "minutes_before": 10, "minutes_now": 20}])
    with pytest.raises(ValueError):
        validate_responsibilities([{"title": "x", "minutes_before": -1}])


def test_value_line_in_a_prompt_is_parsed(env):
    from api.routes import _cron_value_from_prompt

    _structure(env)
    prompt = 'Stel de lijst op.\nVALUE: before=45 now=5 task="Debiteurenlijst samenstellen" team=finance/debiteuren\n'
    value = _cron_value_from_prompt(prompt)
    assert value["before_minutes"] == 45 and value["review_minutes"] == 5
    assert value["task"] == "Debiteurenlijst samenstellen" and value["team"] == "finance/debiteuren"
    assert value["confidence"] == "confirmed"
    estimate = _cron_value_from_prompt("x\nVALUE: before=30 now=0 source=ai_estimate")
    assert estimate["source"] == "ai_estimate" and estimate["confidence"] == "estimated"
    assert _cron_value_from_prompt("VALUE: before=unknown reason=nieuw")["unknown"] is True
    assert _cron_value_from_prompt("no value here") is None
    assert _cron_value_from_prompt("VALUE: before=abc") is None


def test_finished_bot_chats_get_a_duty_label(env, monkeypatch):
    now = time.time()
    _state(env.homes["finbot"], [("w1", "webui", MEMBER, "m", now - 7200, None, now - 4000, 4, 10, 10, 0, 0, 0, None,
                                  "unknown", "Aanmaning voor klant X"),
                                 ("w2", "webui", MEMBER, "m", now - 7200, None, now - 4000, 4, 10, 10, 0, 0, 0, None,
                                  "unknown", "Vraag over vakantie")])
    monkeypatch.setattr(vt, "bot_duties", lambda bot: [{"title": "Aanmaning opstellen", "minutes_before": 30, "minutes_now": 5}])
    monkeypatch.setattr(vt, "_ask_label", lambda duties, title, first: "Aanmaning opstellen" if "Aanmaning" in title else "")
    vt.collect(force=True)
    assert vt.label_chats() == 2
    rows = {r["session_id"]: r for r in vt.chats_between(0, now + 1)}
    assert rows["w1"]["label_state"] == "auto" and rows["w1"]["saved_minutes"] == 25
    assert rows["w2"]["label_state"] == "auto_none" and rows["w2"]["saved_minutes"] == 0
    # The person's own correction wins and is final.
    vt.label_chat("finbot:w1", "", MEMBER)
    assert {r["session_id"]: r for r in vt.chats_between(0, now + 1)}["w1"]["label_state"] == "removed"
