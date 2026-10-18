"""Bot-owned scheduled jobs (Michael Ramirez, 18 Oct 2026).

"Ik wil scheduled jobs aan een bot kunnen koppelen ... Scheduled jobs die een
bot aanmaakt horen automatisch aan hem gekoppeld. En bij terugkoppeling van de
job hoort er een chat te openen met context van die scheduled job."

Covers api/cron_bots.py, the bridge changes in api/cron_webui_delivery.py, the
owner route in api/routes.py and scripts/cron_bot_owner_migration.py:
ownership is the store a job lives in, a job made in a bot's store is that
bot's, changing the owner moves the record, a run's result lands in a chat of
the owning bot with the job's context, and two people never see each other's
job chats or job context.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import api.cron_bots as cron_bots
import api.cron_webui_delivery as cwd

ROOT = Path(__file__).resolve().parents[1]
ALICE = "alice@example.com"
BOB = "bob@example.com"


class _JSONHandler:
    def __init__(self):
        self.status = None
        self.response_headers = []
        self.wfile = io.BytesIO()
        self.headers = {}

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass


def _payload(handler):
    return json.loads(handler.wfile.getvalue().decode("utf-8"))


def _now_iso(offset_secs=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_secs)).isoformat()


def _write_jobs(home: Path, jobs: list) -> None:
    (home / "cron").mkdir(parents=True, exist_ok=True)
    (home / "cron" / "jobs.json").write_text(json.dumps({"jobs": jobs}), encoding="utf-8")


def _read_jobs(home: Path) -> list:
    path = home / "cron" / "jobs.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["jobs"]


@pytest.fixture
def bots_env(monkeypatch, tmp_path):
    """A Hermes root with two bots (scout, writer), isolated WebUI state."""
    import api.config as config
    import api.models as models
    import api.profiles as profiles

    root = tmp_path / "hermes"
    homes = {"default": root, "scout": root / "profiles" / "scout", "writer": root / "profiles" / "writer"}
    for home in homes.values():
        (home / "cron" / "output").mkdir(parents=True, exist_ok=True)
    state_dir = tmp_path / "state"
    session_dir = state_dir / "sessions"
    session_dir.mkdir(parents=True)

    monkeypatch.setattr(config, "STATE_DIR", state_dir)
    monkeypatch.setattr(models, "SESSION_DIR", session_dir)
    monkeypatch.setattr(models, "SESSION_INDEX_FILE", session_dir / "_index.json")
    monkeypatch.setattr(models, "_sync_sidecar_from_state_db_if_newer", lambda s: False)
    monkeypatch.setattr(models, "_repair_stale_pending", lambda s: False)
    monkeypatch.setattr(cwd, "_MEMORY_WATERMARKS", {})
    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", root)
    monkeypatch.setattr(profiles, "_is_isolated_profile_mode", lambda: False)
    monkeypatch.setattr(profiles, "_is_root_profile", lambda name: name == "default")
    monkeypatch.setattr(profiles, "get_hermes_home_for_profile",
                        lambda name: homes.get(str(name or "default") or "default", root / "profiles" / str(name)))
    monkeypatch.setattr(profiles, "list_profiles_api", lambda **_kw: [
        {"name": "default", "is_default": True}, {"name": "scout"}, {"name": "writer", "visible": False}])
    return SimpleNamespace(root=root, homes=homes, state_dir=state_dir, session_dir=session_dir, models=models)


def _write_session(env, sid, *, profile=None, owner=ALICE, bots=None):
    payload = {
        "session_id": sid, "title": "Origin conversation", "workspace": str(env.session_dir),
        "model": "test-model", "created_at": 1.0, "updated_at": 1.0, "profile": profile,
        "owner_email": owner, "bot_participants": bots or [],
        "messages": [{"role": "user", "content": "plan this please", "timestamp": 1.0}],
    }
    (env.session_dir / f"{sid}.json").write_text(json.dumps(payload), encoding="utf-8")


def _read_session(env, sid):
    return json.loads((env.session_dir / f"{sid}.json").read_text(encoding="utf-8"))


def _write_output(home, job_id, body, name="run.md"):
    out = home / "cron" / "output" / job_id
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_text(f"# Cron Job\n\n## Prompt\n\np\n\n## Response\n\n{body}\n", encoding="utf-8")


def _job(job_id, *, chat_id=None, user=ALICE, run_at=None, status="ok", deliver="local", **extra):
    job = {
        "id": job_id, "name": "Weekly pipeline digest", "prompt": "Summarise the pipeline",
        "deliver": deliver, "owner_email": user,
        "origin": {"platform": "webui", "chat_id": chat_id, "user_id": user},
        "last_run_at": run_at or _now_iso(), "last_status": status, "last_error": None,
        "last_delivery_error": None, "schedule": {"kind": "cron", "expr": "0 9 * * 1", "display": "0 9 * * 1"},
        "schedule_display": "Mondays 09:00", "enabled": True,
    }
    job.update(extra)
    return job


def _chat_ids(env):
    return sorted(p.stem for p in env.session_dir.glob("*.json") if not p.name.startswith("_"))


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


# -- Ownership: the store a job lives in ---------------------------------------

def test_every_bot_store_is_listed_root_first_hidden_bots_included(bots_env):
    homes = cron_bots.store_homes()
    assert [name for name, _ in homes] == ["default", "scout", "writer"]
    assert homes[0][1] == bots_env.root


def test_owner_is_the_profile_whose_store_holds_the_job(bots_env):
    _write_jobs(bots_env.homes["scout"], [{"id": "s1", "name": "Scout job"}])
    _write_jobs(bots_env.root, [{"id": "d1", "name": "Root job"}])
    assert cron_bots.find_job("s1") == ({"id": "s1", "name": "Scout job"}, "scout")
    assert cron_bots.find_job("d1")[1] == "default"
    assert cron_bots.find_job("s1", "writer") == (None, "")
    assert cron_bots.profile_for_home(bots_env.homes["writer"]) == "writer"
    assert cron_bots.profile_for_home(bots_env.root) == "default"


def test_session_serves_its_own_bot_and_bots_taking_part():
    chat = SimpleNamespace(profile="scout", bot_participants=[])
    group = SimpleNamespace(profile=None, bot_participants=["writer"])
    assert cron_bots.session_serves_bot(chat, "scout")
    assert not cron_bots.session_serves_bot(chat, "writer")
    assert cron_bots.session_serves_bot(group, "writer")
    assert cron_bots.session_serves_bot(group, "default")


def test_job_person_is_the_run_identity_then_the_webui_creator():
    assert cron_bots.job_person_email({"owner_email": "A@x.io", "origin": {"platform": "webui", "user_id": BOB}}) == "a@x.io"
    assert cron_bots.job_person_email({"origin": {"platform": "webui", "user_id": BOB}}) == BOB
    assert cron_bots.job_person_email(
        {"origin": {"platform": "webui", "chat_id": "c1"}}, session_owner=lambda sid: ALICE) == ALICE
    assert cron_bots.job_person_email({"origin": {"platform": "telegram", "user_id": "123"}}) == ""


# -- Auto-link: a job a bot creates lives in that bot's store -------------------

def test_job_created_while_bound_to_a_bot_lands_in_its_store(bots_env, engine_store):
    cj = engine_store
    from api.profiles import cron_profile_context_for_home

    with cron_profile_context_for_home(bots_env.homes["scout"]):
        jobs = cj.load_jobs()
        jobs.append({"id": "auto1", "name": "Made by scout", "prompt": "x",
                     "schedule": {"kind": "interval", "minutes": 60}})
        cj.save_jobs(jobs)
    assert [j["id"] for j in _read_jobs(bots_env.homes["scout"])] == ["auto1"]
    assert _read_jobs(bots_env.root) == []
    assert cron_bots.find_job("auto1")[1] == "scout"


def test_streaming_turn_binds_the_cronjob_tool_to_the_session_bot():
    src = (ROOT / "api" / "streaming.py").read_text(encoding="utf-8")
    # The bot of the turn (execution_profile for a delegated bot, else the
    # session's) decides the store the cronjob tool writes to.
    assert "get_hermes_home_for_profile(execution_profile or getattr(s, 'profile', None))" in src
    assert "_STREAMING_CRON_PROFILE_HOME.set(_profile_home)" in src
    assert "with cron_profile_context_for_home(Path(profile_home)):" in src


# -- Changing the owner moves the record ---------------------------------------

def test_move_job_changes_owner_moves_output_and_clears_legacy_profile(bots_env, engine_store):
    _write_jobs(bots_env.root, [_job("m1", profile="writer"), _job("keep")])
    _write_output(bots_env.root, "m1", "old run")
    moved = cron_bots.move_job("m1", "default", "scout")
    assert moved["profile"] is None
    assert [j["id"] for j in _read_jobs(bots_env.root)] == ["keep"]
    assert [j["id"] for j in _read_jobs(bots_env.homes["scout"])] == ["m1"]
    assert (bots_env.homes["scout"] / "cron" / "output" / "m1" / "run.md").is_file()
    assert not (bots_env.root / "cron" / "output" / "m1").exists()
    assert cron_bots.find_job("m1")[1] == "scout"


def test_move_job_refuses_running_jobs_and_taken_ids_and_rolls_back(bots_env, engine_store, monkeypatch):
    _write_jobs(bots_env.root, [_job("busy", run_claim={"pid": 1}), _job("dup"), _job("fail")])
    _write_jobs(bots_env.homes["scout"], [_job("dup")])
    with pytest.raises(cron_bots.OwnerChangeError) as running:
        cron_bots.move_job("busy", "default", "scout")
    assert running.value.status == 409 and running.value.reason == "job_running"
    with pytest.raises(cron_bots.OwnerChangeError) as taken:
        cron_bots.move_job("dup", "default", "scout")
    assert taken.value.reason == "job_id_taken"
    with pytest.raises(cron_bots.OwnerChangeError) as missing:
        cron_bots.move_job("nope", "default", "scout")
    assert missing.value.status == 404

    real_put = cron_bots._put_in_store

    def _flaky_put(home, job):
        if Path(home) == bots_env.homes["scout"]:
            raise RuntimeError("disk full")
        return real_put(home, job)

    monkeypatch.setattr(cron_bots, "_put_in_store", _flaky_put)
    with pytest.raises(RuntimeError):
        cron_bots.move_job("fail", "default", "scout")
    assert sorted(j["id"] for j in _read_jobs(bots_env.root)) == ["busy", "dup", "fail"]


# -- Backfill: report, apply, restore ------------------------------------------

def _run_migration(*args):
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "cron_bot_owner_migration.py"), *args],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_migration_plan_reports_per_bot_counts_and_findings(tmp_path):
    root = tmp_path / "h"
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "c-scout.json").write_text(json.dumps({"profile": "scout", "owner_email": ALICE}))
    _write_jobs(root, [
        _job("a"),
        _job("legacy", profile="scout"),
        _job("gone", profile="ghost"),
        _job("other", chat_id="c-scout"),
        _job("lost", chat_id="c-missing"),
        {"id": "nobody", "name": "CLI job", "origin": {"platform": "cli"}},
    ])
    _write_jobs(root / "profiles" / "scout", [_job("s1", enabled=False), _job("a")])
    (root / "profiles" / "writer").mkdir(parents=True)
    report = json.loads(_run_migration("plan", "--hermes", str(root), "--sessions", str(sessions), "--json"))
    assert report["jobs_per_bot"] == {"default": 6, "scout": 2}
    assert report["enabled_per_bot"] == {"default": 6, "scout": 1}
    ids = {k: [r["job_id"] for r in v] for k, v in report["findings"].items()}
    assert ids["legacy_profile"] == ["legacy"]
    assert ids["missing_profile"] == ["gone"]
    assert ids["origin_other_bot"] == ["other"]
    assert ids["origin_chat_missing"] == ["lost"]
    assert ids["no_person"] == ["nobody"]
    assert ids["duplicate_id"] == ["a"]
    assert [m["job_id"] for m in report["moves"]] == ["legacy"]


def test_migration_apply_moves_legacy_rows_and_restore_puts_them_back(tmp_path):
    root = tmp_path / "h"
    _write_jobs(root, [_job("legacy", profile="scout"), _job("gone", profile="ghost"), _job("stay")])
    _write_output(root, "legacy", "saved run")
    (root / "profiles" / "scout").mkdir(parents=True)
    before = (root / "cron" / "jobs.json").read_text()
    backup = tmp_path / "backup"
    _run_migration("apply", "--hermes", str(root), "--sessions", str(tmp_path / "none"), "--backup-dir", str(backup))
    assert sorted(j["id"] for j in _read_jobs(root)) == ["gone", "stay"]
    assert next(j for j in _read_jobs(root) if j["id"] == "gone")["profile"] is None
    (moved,) = _read_jobs(root / "profiles" / "scout")
    assert moved["id"] == "legacy" and moved["profile"] is None
    assert (root / "profiles" / "scout" / "cron" / "output" / "legacy" / "run.md").is_file()
    assert (backup / "manifest.json").is_file()
    # A second apply has nothing left to do.
    again = json.loads(_run_migration("apply", "--hermes", str(root), "--sessions", str(tmp_path / "none"),
                                      "--backup-dir", str(tmp_path / "backup2")))
    assert again["moves"] == [] and again["clears"] == []
    _run_migration("restore", "--backup-dir", str(backup))
    assert (root / "cron" / "jobs.json").read_text() == before
    assert not (root / "profiles" / "scout" / "cron" / "jobs.json").exists()
    assert (root / "cron" / "output" / "legacy" / "run.md").is_file()
    assert not (root / "profiles" / "scout" / "cron" / "output" / "legacy").exists()


# -- Results land in a chat of the owning bot ----------------------------------

def test_origin_chat_of_the_owning_bot_keeps_getting_results(bots_env):
    _write_session(bots_env, "orig1", profile="scout")
    _write_output(bots_env.homes["scout"], "j1", "Pipeline is healthy.")
    job = _job("j1", chat_id="orig1")
    (action,) = cwd.process_jobs_once([job], home=bots_env.homes["scout"])
    assert action["outcome"] == cwd.OUTCOME_DELIVERED
    assert action["target"] == cwd.TARGET_ORIGIN and action["profile"] == "scout"
    last = _read_session(bots_env, "orig1")["messages"][-1]
    assert "Pipeline is healthy." in last["content"]
    assert last["cron_delivery"]["profile"] == "scout"
    assert _chat_ids(bots_env) == ["orig1"]


def test_result_opens_a_job_chat_in_the_owning_bot_and_reuses_it(bots_env):
    # Made in a SynthPulse chat, then handed to scout: the old chat is not scout's.
    _write_session(bots_env, "orig2", profile="default")
    _write_output(bots_env.homes["scout"], "j2", "Three deals moved to proposal.")
    job = _job("j2", chat_id="orig2", run_at=_now_iso(-30))
    (action,) = cwd.process_jobs_once([job], home=bots_env.homes["scout"])
    assert action["outcome"] == cwd.OUTCOME_DELIVERED and action["target"] == cwd.TARGET_JOB_CHAT
    sid = action["session_id"]
    assert sid and sid != "orig2"
    chat = _read_session(bots_env, sid)
    assert chat["profile"] == "scout"
    assert chat["owner_email"] == ALICE
    assert chat["cron_job"] == {"job_id": "j2", "profile": "scout"}
    assert chat["title"].startswith("\U0001f5d3") and "Weekly pipeline digest" in chat["title"]
    intro, update = chat["messages"]
    assert intro["cron_context"] == {"job_id": "j2", "profile": "scout"}
    assert "Mondays 09:00" in intro["content"] and "Summarise the pipeline" in intro["content"]
    assert "Three deals moved to proposal." in update["content"]
    assert len(_read_session(bots_env, "orig2")["messages"]) == 1
    # The ledger names the chat, so a completion notice can open it.
    assert cwd.delivered_session_for_job(job) == sid

    _write_output(bots_env.homes["scout"], "j2", "Second run.", name="run2.md")
    job2 = dict(job, last_run_at=_now_iso(), last_status="error", last_error="Provider timed out")
    (again,) = cwd.process_jobs_once([job2], home=bots_env.homes["scout"])
    assert again["session_id"] == sid
    messages = _read_session(bots_env, sid)["messages"]
    assert len(messages) == 3 and "Provider timed out" in messages[-1]["content"]
    assert messages[-1]["cron_delivery"]["status"] == "error"
    assert len(_chat_ids(bots_env)) == 2


def test_tasks_panel_job_without_a_chat_gets_its_job_chat(bots_env):
    _write_output(bots_env.root, "j3", "Done.")
    (action,) = cwd.process_jobs_once([_job("j3")], home=bots_env.root)
    assert action["target"] == cwd.TARGET_JOB_CHAT
    assert _read_session(bots_env, action["session_id"])["profile"] == "default"


def test_silent_and_muted_runs_open_no_chat(bots_env):
    _write_output(bots_env.homes["scout"], "j4", "[SILENT]")
    _write_output(bots_env.homes["scout"], "j5", "Report")
    silent = _job("j4")
    failures_only = _job("j5", notify={"in_app": "all", "delivery": "failures"})
    actions = cwd.process_jobs_once([silent, failures_only], home=bots_env.homes["scout"])
    assert [a["outcome"] for a in actions] == [cwd.OUTCOME_SILENT, cwd.OUTCOME_MUTED]
    assert _chat_ids(bots_env) == []
    # A failure of the failures-only job does reach its chat.
    failed = dict(failures_only, last_run_at=_now_iso(5), last_status="error", last_error="boom")
    (action,) = cwd.process_jobs_once([failed], home=bots_env.homes["scout"])
    assert action["outcome"] == cwd.OUTCOME_DELIVERED and action["target"] == cwd.TARGET_JOB_CHAT


def test_jobs_from_other_platforms_join_only_after_opting_in(bots_env):
    telegram = {"id": "t1", "name": "TG", "deliver": "local", "owner_email": ALICE,
                "origin": {"platform": "telegram", "chat_id": "123"},
                "last_run_at": _now_iso(), "last_status": "ok"}
    _write_output(bots_env.homes["scout"], "t1", "hello")
    assert cwd.process_jobs_once([telegram], home=bots_env.homes["scout"]) == []
    opted = dict(telegram, notify={"in_app": "all", "delivery": "all"})
    (action,) = cwd.process_jobs_once([opted], home=bots_env.homes["scout"])
    assert action["outcome"] == cwd.OUTCOME_DELIVERED and action["target"] == cwd.TARGET_JOB_CHAT
    # A Telegram job that answers in Telegram stays there.
    external = dict(opted, id="t2", deliver="origin", last_run_at=_now_iso(1))
    (skip,) = cwd.process_jobs_once([external], home=bots_env.homes["scout"])
    assert skip["outcome"] == cwd.OUTCOME_SKIPPED_EXTERNAL


def test_bridge_reads_every_bot_store(bots_env):
    _write_jobs(bots_env.homes["writer"], [_job("w1")])
    _write_output(bots_env.homes["writer"], "w1", "Draft ready.")
    actions = cwd.process_jobs_once()
    assert [(a["job_id"], a["profile"]) for a in actions] == [("w1", "writer")]


# -- Access: two people ---------------------------------------------------------

def test_job_chat_belongs_to_the_job_person_only(bots_env):
    _write_output(bots_env.root, "a1", "Alice's numbers")
    _write_output(bots_env.root, "b1", "Bob's numbers")
    actions = cwd.process_jobs_once([_job("a1"), _job("b1", user=BOB)], home=bots_env.root)
    by_job = {a["job_id"]: a["session_id"] for a in actions}
    assert _read_session(bots_env, by_job["a1"])["owner_email"] == ALICE
    assert _read_session(bots_env, by_job["b1"])["owner_email"] == BOB

    rows = [{"id": "a1", "owner_profile": "default"}, {"id": "b1", "owner_profile": "default"}]
    cron_bots.annotate_job_chats(rows, ALICE)
    assert rows[0]["job_chat_session_id"] == by_job["a1"]
    assert "job_chat_session_id" not in rows[1]
    # A chat that changed hands is not reused for the job's person.
    assert cron_bots.find_job_chat("a1", "default", BOB) is None


def test_job_context_reaches_the_agent_only_for_people_who_see_the_job(bots_env, monkeypatch):
    import api.cron_scope as cron_scope

    _write_jobs(bots_env.homes["scout"], [_job("ctx1", last_error="Quota exceeded", last_status="error")])
    _write_output(bots_env.homes["scout"], "ctx1", "Earlier run output")
    session = SimpleNamespace(cron_job={"job_id": "ctx1", "profile": "scout"}, messages=[], profile="scout")
    monkeypatch.setattr(cron_scope, "identity_sees_cron_profile", lambda identity, profile: False)

    text = cron_bots.context_prompt(session, {"email": ALICE})
    assert "job_id ctx1" in text and "Quota exceeded" in text
    assert "Summarise the pipeline" in text and "Earlier run output" in text
    assert "cronjob tool" in text
    assert cron_bots.context_prompt(session, {"email": BOB}) == ""


def test_origin_chat_context_follows_the_posted_results(bots_env):
    _write_jobs(bots_env.root, [_job("o1")])
    session = SimpleNamespace(cron_job=None, profile="default", messages=[
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "update", "cron_delivery": {"job_id": "o1", "profile": "default"}},
    ])
    assert cron_bots.job_refs_for_session(session) == [("o1", "default")]
    assert "job_id o1" in cron_bots.context_prompt(session)


def test_recent_completions_of_other_bots_are_scoped_to_their_person(bots_env, monkeypatch):
    import api.cron_scope as cron_scope
    import api.routes as routes
    import api.profiles as profiles

    _write_jobs(bots_env.homes["scout"], [_job("sa"), _job("sb", user=BOB)])
    monkeypatch.setattr(profiles, "get_active_hermes_home", lambda: bots_env.root)
    monkeypatch.setattr(cron_scope, "_identity_is_cron_admin", lambda identity: False)
    for who, expected in ((ALICE, ["sa"]), (BOB, ["sb"])):
        monkeypatch.setattr(cron_scope, "_identity_for", lambda handler, who=who: {"email": who})
        rows = routes._cron_recent_other_store_jobs(object())
        assert [r["id"] for r in rows] == expected
        assert {r["owner_profile"] for r in rows} == {"scout"}


def _owner_route(monkeypatch, *, caller, admin=False, allowed=("scout", "writer", "default")):
    import api.routes as routes
    import api.governance.enforce as enforce

    calls = []
    monkeypatch.setattr(enforce, "_request_identity", lambda handler: {"email": caller})
    monkeypatch.setattr(routes, "_cron_admin_allowed", lambda handler: admin)
    monkeypatch.setattr(routes, "_chat_profile_target_allowed", lambda handler, p: p in allowed)
    monkeypatch.setattr(routes, "_available_cron_profile_names", lambda: {"default", "scout", "writer"})
    monkeypatch.setattr(routes, "_is_cron_running", lambda job_id: (False, 0.0))
    monkeypatch.setattr(routes, "_get_active_profile_name", lambda: "default")
    monkeypatch.setattr("api.cron_scope._policy_mode", lambda: "enforce")
    monkeypatch.setattr("api.cron_scope.identity_sees_cron_profile", lambda identity, profile: admin)
    monkeypatch.setattr(cron_bots, "move_job", lambda job_id, src, dst: calls.append((job_id, src, dst)) or {"id": job_id})
    return routes, calls


def test_owner_route_lets_the_owner_choose_a_bot_they_may_use(bots_env, monkeypatch):
    _write_jobs(bots_env.root, [_job("own1")])
    routes, calls = _owner_route(monkeypatch, caller=ALICE)
    handler = _JSONHandler()
    routes._handle_cron_owner(handler, {"job_id": "own1", "from_profile": "default", "to_profile": "scout"})
    assert handler.status == 200, _payload(handler)
    body = _payload(handler)
    assert body["job"]["owner_profile"] == "scout" and body["to_profile"] == "scout"
    assert calls == [("own1", "default", "scout")]


def test_owner_route_refuses_other_people_and_bots_they_may_not_use(bots_env, monkeypatch):
    _write_jobs(bots_env.root, [_job("own2")])
    # Bob cannot even see Alice's root-store job.
    routes, calls = _owner_route(monkeypatch, caller=BOB)
    handler = _JSONHandler()
    routes._handle_cron_owner(handler, {"job_id": "own2", "from_profile": "default", "to_profile": "scout"})
    assert handler.status == 404
    # Bob sees it when it is shared with him, but sharing does not grant this.
    _write_jobs(bots_env.root, [_job("own2", shared_with=[BOB])])
    handler = _JSONHandler()
    routes._handle_cron_owner(handler, {"job_id": "own2", "from_profile": "default", "to_profile": "scout"})
    assert handler.status == 403 and _payload(handler)["reason"] == "cron_owner"
    # Alice owns it but may not use writer.
    routes, calls = _owner_route(monkeypatch, caller=ALICE, allowed=("scout",))
    handler = _JSONHandler()
    routes._handle_cron_owner(handler, {"job_id": "own2", "from_profile": "default", "to_profile": "writer"})
    assert handler.status == 403 and _payload(handler)["reason"] == "profile_not_allowed"
    # A cron admin may choose any bot for anyone's job.
    routes, calls = _owner_route(monkeypatch, caller=BOB, admin=True, allowed=())
    handler = _JSONHandler()
    routes._handle_cron_owner(handler, {"job_id": "own2", "from_profile": "default", "to_profile": "writer"})
    assert handler.status == 200 and calls == [("own2", "default", "writer")]
    # Unknown bots are a 404, a missing target a 400.
    handler = _JSONHandler()
    routes._handle_cron_owner(handler, {"job_id": "own2", "from_profile": "default", "to_profile": "ghost"})
    assert handler.status == 404
    handler = _JSONHandler()
    routes._handle_cron_owner(handler, {"job_id": "own2", "from_profile": "default"})
    assert handler.status == 400


# -- Session field, UI wiring and copy ------------------------------------------

def test_session_keeps_its_job_link(bots_env):
    from api.models import Session

    s = Session(session_id="lnk1", cron_job={"job_id": "j9", "profile": "scout", "junk": 1})
    s.messages.append({"role": "assistant", "content": "x"})
    s.save()
    data = _read_session(bots_env, "lnk1")
    assert data["cron_job"] == {"job_id": "j9", "profile": "scout"}
    assert Session.load("lnk1").compact()["cron_job"] == {"job_id": "j9", "profile": "scout"}
    assert "cron_job" not in Session(session_id="plain1").compact()
    assert Session(session_id="bad1", cron_job={"job_id": ""}).cron_job is None


def test_tasks_panel_shows_filters_and_changes_the_bot():
    panels = (ROOT / "static" / "panels.js").read_text(encoding="utf-8")
    for needle in ("function _renderCronBotFilter(", "function openCronBotPicker(", "'/api/crons/owner'",
                   "cron-bot-badge", "_cronMatchesBotFilter", "function _loadProfileBotJobs(",
                   "c.chat_session_id", "function _cronToastWithChat("):
        assert needle in panels, needle
    assert 'id="cronBotFilter"' in (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    assert "cron_job" in (ROOT / "static" / "ui.js").read_text(encoding="utf-8")


def test_new_copy_is_dutch_first_and_dash_free():
    nl = (ROOT / "static" / "i18n" / "nl.js").read_text(encoding="utf-8")
    for key in ("cron_bot_picker_title", "cron_bot_filter_all", "cron_job_chat_open", "profile_bot_jobs_title"):
        assert f"  {key}: " in nl, key
    for path in ("api/cron_bots.py", "scripts/cron_bot_owner_migration.py", "static/i18n/nl.js"):
        text = (ROOT / path).read_text(encoding="utf-8")
        assert chr(0x2013) not in text and chr(0x2014) not in text, path


def test_schedule_in_plain_dutch_words():
    words = cron_bots.schedule_in_words
    assert words("0 9 * * 1") == "elke maandag om 09:00"
    assert words("30 7 * * 1-5") == "elke werkdag om 07:30"
    assert words("0 9 * * *") == "elke dag om 09:00"
    assert words("*/15 * * * *") == "elke 15 minuten"
    assert words("every 2h") == "elke 2 uur"
    assert words("0 10 1 * *") == "elke 1e van de maand om 10:00"
    assert words("*/30 8-18 * * 1-5") == "*/30 8-18 * * 1-5"
    intro = cron_bots.job_chat_intro({"name": "Digest", "schedule_display": "0 9 * * 1"}, "default")
    assert "Wanneer: elke maandag om 09:00" in intro


def test_run_post_is_dutch_and_names_the_moment():
    job = {"id": "d1", "name": "Digest", "last_run_at": "2026-10-19T07:00:00+00:00"}
    text = cwd.build_update_text(job, body="Alles groen.", run_ok=True, run_error=None)
    assert text.startswith("\U0001f5d3️ Uitkomst van Digest, 19-10-2026 ")
    assert "Scheduled task" not in text
    failed = cwd.build_update_text(job, body=None, run_ok=False, run_error="ValueError: stap 3")
    assert "mislukt" in failed and "stap 3" in failed and "d1" in failed


def test_job_detail_labels_and_output_card_are_translated():
    panels = (ROOT / "static" / "panels.js").read_text(encoding="utf-8")
    assert "Live output is available only when this profile is active here.' : (t('loading')" not in panels
    assert "t('cron_output_in_chat', ownerBotTitle)" in panels
    assert "function _cronScheduleInWords(" in panels
    assert '<div class="detail-row-label">Schedule</div>' not in panels
    assert '<div class="detail-row-label">Deliver</div>' not in panels
    nl = (ROOT / "static" / "i18n" / "nl.js").read_text(encoding="utf-8")
    for key in ("cron_words_weekly", "cron_output_in_chat", "cron_output_other_bot"):
        assert f"  {key}: " in nl, key
