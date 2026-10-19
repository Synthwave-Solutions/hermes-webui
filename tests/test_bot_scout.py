"""Scout per bot (api/bot_scout.py, POST /api/bots/scout).

One Scout job per bot in the bot's own cron store, recognised by
managed_by "scout"; on creates or resumes it, off pauses it, the runner files
are the bot's own copies, and the settings in profile.yaml stay the truth.
All state lives in a temporary Hermes root.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from api import bot_metadata, bot_scout

ALICE = "alice@example.com"


@pytest.fixture
def scout_env(monkeypatch, tmp_path):
    import api.profiles as profiles

    root = tmp_path / "hermes"
    homes = {"default": root, "radar": root / "profiles" / "radar", "odis": root / "profiles" / "odis"}
    for home in homes.values():
        (home / "cron").mkdir(parents=True, exist_ok=True)
    (homes["odis"] / "profile.yaml").write_text(yaml.safe_dump({"ui_meta": {"hermes-bots": {"category": "Team"}}}))
    src = root / "scripts" / "scout"
    src.mkdir(parents=True)
    (src / "scout_collect.py").write_text("print('{\"wakeAgent\": false}')\n")
    (src / "scout_ledger.py").write_text("print('ledger')\n")
    (src / "prompt.md").write_text("Eigen Scout prompt.\n")
    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", root)
    monkeypatch.setattr(profiles, "_is_isolated_profile_mode", lambda: False)
    monkeypatch.setattr(profiles, "_is_root_profile", lambda name: name == "default")
    monkeypatch.setattr(profiles, "get_hermes_home_for_profile",
                        lambda name: homes.get(str(name or "default") or "default", root / "profiles" / str(name)))
    return SimpleNamespace(root=root, homes=homes, src=src)


def _jobs(home: Path) -> list:
    path = home / "cron" / "jobs.json"
    return json.loads(path.read_text())["jobs"] if path.exists() else []


def _revision(name):
    return bot_metadata.read_profile(name)["bot_revision"]


def _set(name, **body):
    body.setdefault("revision", _revision(name))
    return bot_scout.apply(name, body, ALICE)


# -- Runner copies -------------------------------------------------------------

def test_runner_files_are_copied_as_real_files_and_only_when_changed(scout_env):
    dest = bot_scout.install_runner(scout_env.homes["radar"])
    assert dest == scout_env.homes["radar"] / "scripts" / "scout"
    for name in bot_scout.RUNNER_FILES:
        assert (dest / name).is_file() and not (dest / name).is_symlink()
        assert (dest / name).read_bytes() == (scout_env.src / name).read_bytes()
    stamp = (dest / "scout_collect.py").stat().st_mtime_ns
    bot_scout.install_runner(scout_env.homes["radar"])
    assert (dest / "scout_collect.py").stat().st_mtime_ns == stamp
    (scout_env.src / "scout_collect.py").write_text("print('v2')\n")
    bot_scout.install_runner(scout_env.homes["radar"])
    assert (dest / "scout_collect.py").read_text() == "print('v2')\n"


def test_root_profile_uses_the_source_folder_itself(scout_env):
    assert bot_scout.install_runner(scout_env.root) == scout_env.src


def test_missing_source_refuses_and_changes_nothing(scout_env):
    (scout_env.src / "scout_ledger.py").unlink()
    with pytest.raises(bot_scout.ScoutError) as err:
        _set("radar", enabled=True)
    assert err.value.status == 503 and "scout_ledger.py" in err.value.message
    assert _jobs(scout_env.homes["radar"]) == []
    assert "scout" not in bot_metadata.read_profile("radar")["bot"]
    assert not (scout_env.homes["radar"] / "scripts").exists()


def test_symlinked_runner_target_is_refused(scout_env, tmp_path):
    dest = scout_env.homes["radar"] / "scripts" / "scout"
    dest.mkdir(parents=True)
    outside = tmp_path / "outside.py"
    outside.write_text("keep")
    (dest / "scout_collect.py").symlink_to(outside)
    with pytest.raises(bot_scout.ScoutError):
        bot_scout.install_runner(scout_env.homes["radar"])
    assert outside.read_text() == "keep"


# -- The job -------------------------------------------------------------------

def test_turning_scout_on_creates_one_job_in_the_bots_own_store(scout_env):
    result = _set("radar", enabled=True, topics=["AI act", " MKB  automatisering ", "ai ACT"], digest_time="06:45")
    assert result["bot"]["scout"] == {"enabled": True, "topics": ["AI act", "MKB automatisering"], "digest_time": "06:45"}
    assert _jobs(scout_env.root) == []
    [job] = _jobs(scout_env.homes["radar"])
    assert job["managed_by"] == "scout" and job["name"] == "Scout"
    assert job["script"] == "scout/scout_collect.py" and job["no_agent"] is False
    assert job["schedule"]["kind"] == "cron" and job["schedule"]["expr"] == "45 6 * * *"
    assert job["enabled_toolsets"] == ["kanban", "web"]
    assert job["prompt"].startswith("Eigen Scout prompt.") and "AI act; MKB automatisering" in job["prompt"]
    assert job["deliver"] == "local" and job["notify"] == {"in_app": "off", "delivery": "all"}
    assert job["owner_email"] == ALICE and job["origin"] == {"platform": "webui", "chat_id": None, "user_id": ALICE}
    assert job["enabled"] is True and job["state"] == "scheduled"
    assert result["scout_job"]["id"] == job["id"] and result["scout_job"]["enabled"] is True
    saved = yaml.safe_load((scout_env.homes["radar"] / "profile.yaml").read_text())
    assert saved["ui_meta"]["hermes-bots"]["scout"]["digest_time"] == "06:45"


def test_on_again_is_idempotent_and_off_pauses_without_deleting(scout_env):
    first = _set("radar", enabled=True)["scout_job"]["id"]
    _set("radar", enabled=True, digest_time="08:00")
    [job] = _jobs(scout_env.homes["radar"])
    assert job["id"] == first and job["schedule"]["expr"] == "0 8 * * *"
    assert job["enabled_toolsets"] == ["kanban"]
    assert "geen onderwerpen" in job["prompt"]
    off = _set("radar", enabled=False)
    assert off["bot"]["scout"]["enabled"] is False and off["bot"]["scout"]["digest_time"] == "08:00"
    [job] = _jobs(scout_env.homes["radar"])
    assert job["id"] == first and job["enabled"] is False and job["state"] == "paused"
    _set("radar", enabled=False)
    assert len(_jobs(scout_env.homes["radar"])) == 1
    _set("radar", enabled=True)
    [job] = _jobs(scout_env.homes["radar"])
    assert job["id"] == first and job["enabled"] is True and job["state"] != "paused"


def test_off_without_a_job_writes_no_job(scout_env):
    result = _set("radar", enabled=False, topics=["Later"])
    assert result["scout_job"] is None and _jobs(scout_env.homes["radar"]) == []
    assert result["bot"]["scout"]["topics"] == ["Later"]


def test_built_in_prompt_when_the_bot_has_none(scout_env):
    (scout_env.src / "prompt.md").unlink()
    _set("radar", enabled=True)
    [job] = _jobs(scout_env.homes["radar"])
    assert job["prompt"].startswith(bot_scout.DEFAULT_PROMPT)
    for word in ("negeren", "stil bewaren", "aan project koppelen", "melden", "triage", "[SILENT]",
                 "SCOUT-LEDGER: <hash8>=<status>,<hash8>=<status>", *bot_scout.LEDGER_STATUSES):
        assert word in job["prompt"]
    for word in ("python", "scout_ledger.py", "terminal", "$HERMES_HOME"):
        assert word not in job["prompt"]
    assert chr(0x2014) not in bot_scout.DEFAULT_PROMPT and chr(0x2013) not in bot_scout.DEFAULT_PROMPT


def test_a_person_gets_no_scout(scout_env):
    with pytest.raises(bot_scout.ScoutError) as err:
        _set("odis", enabled=True)
    assert err.value.status == 400
    assert _jobs(scout_env.homes["odis"]) == []


@pytest.mark.parametrize("body", [
    {"enabled": "yes"}, {"enabled": True, "digest_time": "7:30"}, {"enabled": True, "digest_time": "24:00"},
    {"enabled": True, "topics": ["x" * 81]}, {"enabled": True, "topics": ["t%d" % i for i in range(13)]},
    {"enabled": True, "topics": "AI"}, {"enabled": True, "topics": ["bad\ntopic"]},
])
def test_invalid_settings_are_refused_before_anything_changes(scout_env, body):
    with pytest.raises(ValueError):
        _set("radar", **body)
    assert _jobs(scout_env.homes["radar"]) == [] and _revision("radar") == 0


def test_stale_revision_is_a_conflict(scout_env):
    _set("radar", enabled=False)
    with pytest.raises(RuntimeError):
        bot_scout.apply("radar", {"enabled": True, "revision": 0}, ALICE)
    assert _jobs(scout_env.homes["radar"]) == []


def test_failed_job_write_restores_the_previous_settings(scout_env, monkeypatch):
    def broken(*_a, **_kw):
        raise OSError("disk full")
    monkeypatch.setattr(bot_scout, "sync_job", broken)
    with pytest.raises(OSError):
        _set("radar", enabled=True, topics=["AI act"])
    scout = bot_metadata.read_profile("radar")["bot"]["scout"]
    assert scout["enabled"] is False and scout["topics"] == []


def test_scout_route_needs_the_bot_edit_permission():
    from api.governance.catalog import route_permission

    assert route_permission("/api/bots/scout", "POST") == "profiles:admin"
    src = (Path(__file__).resolve().parents[1] / "api" / "routes.py").read_text(encoding="utf-8")
    route = src[src.index('if parsed.path == "/api/bots/scout":'):]
    assert route[:route.index("if parsed.path ==", 10)].strip().endswith("return _handle_bot_scout(handler, body)")
    block = src[src.index("def _handle_bot_scout(handler, body):"):]
    block = block[:block.index("\ndef ", 10)]
    assert "_cron_admin_allowed(handler)" in block
    assert '"profiles:admin"' in block and "_chat_profile_target_allowed(handler, name)" in block
    assert "bot_builder.require_edit(_request_identity(handler), name)" in block


class _RouteHandler:
    def __init__(self):
        self.status = None
        self.body = b""
        self.headers = {}

    def send_response(self, code, *a):
        self.status = code

    def send_header(self, *a):
        pass

    def end_headers(self):
        pass

    @property
    def wfile(self):
        handler = self

        class _W:
            def write(self, data):
                handler.body += data
        return _W()


def _route_env(monkeypatch, cron_admin):
    from api import routes, governance_api
    monkeypatch.setattr(governance_api, "get_policy", lambda: SimpleNamespace(bootstrap_admins=[]))
    monkeypatch.setattr(governance_api, "_caller_identity", lambda handler: {"email": ALICE})
    monkeypatch.setattr(governance_api, "resolve_effective_access", lambda policy, subject: None)
    monkeypatch.setattr(governance_api, "_require", lambda *a: True)
    monkeypatch.setattr(routes, "_chat_profile_target_allowed", lambda handler, name: True)
    monkeypatch.setattr(routes, "_cron_admin_allowed", lambda handler: cron_admin)
    return routes


def test_scout_route_refuses_a_non_cron_admin_and_changes_nothing(scout_env, monkeypatch):
    routes = _route_env(monkeypatch, cron_admin=False)
    for enabled in (True, False):
        h = _RouteHandler()
        routes._handle_bot_scout(h, {"name": "radar", "enabled": enabled, "revision": 0})
        assert h.status == 403 and b"cron admin" in h.body
    assert _jobs(scout_env.homes["radar"]) == [] and _revision("radar") == 0
    assert not (scout_env.homes["radar"] / "scripts").exists()


def test_scout_route_lets_a_cron_admin_turn_it_on(scout_env, monkeypatch):
    routes = _route_env(monkeypatch, cron_admin=True)
    h = _RouteHandler()
    routes._handle_bot_scout(h, {"name": "radar", "enabled": True, "revision": 0})
    assert h.status == 200 and len(_jobs(scout_env.homes["radar"])) == 1


def test_an_older_scout_job_loses_terminal_on_the_next_sync(scout_env):
    from api.profiles import cron_profile_context_for_home
    first = _set("radar", enabled=True)["scout_job"]["id"]
    with cron_profile_context_for_home(scout_env.homes["radar"]):
        import cron.jobs as cj
        cj.update_job(first, {"enabled_toolsets": ["terminal", "kanban"]})
    _set("radar", enabled=False)
    [job] = _jobs(scout_env.homes["radar"])
    assert job["enabled_toolsets"] == ["kanban"] and job["state"] == "paused"
    with cron_profile_context_for_home(scout_env.homes["radar"]):
        import cron.jobs as cj
        cj.update_job(first, {"enabled_toolsets": ["terminal", "kanban", "web"]})
    _set("radar", enabled=True)
    [job] = _jobs(scout_env.homes["radar"])
    assert job["enabled_toolsets"] == ["kanban"]
