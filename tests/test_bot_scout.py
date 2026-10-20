"""Scout per person per bot (api/bot_scout.py, POST /api/bots/scout).

One Scout job per (bot, person) in the bot's own cron store, recognised by
managed_by "scout" plus scout_person; on creates or resumes it, off pauses it,
the runner files are the bot's own copies, and the settings in profile.yaml
stay the truth. All state lives in a temporary Hermes root.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from api import bot_metadata, bot_scout

ALICE = "alice@example.com"
BOB = "bob.de.vries@example.com"


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
    if "digest_time" in body:
        body["default_time"] = body.pop("digest_time")
    return bot_scout.apply(name, body, ALICE, editor=True)


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
    assert result["bot"]["scout"] == {"enabled": True, "topics": ["AI act", "MKB automatisering"], "digest_time": "06:45",
                                      "people": {ALICE: {"enabled": True}}}
    assert _jobs(scout_env.root) == []
    [job] = _jobs(scout_env.homes["radar"])
    assert job["managed_by"] == "scout" and job["name"] == "Scout \u00b7 Alice" and job["scout_person"] == ALICE
    assert job["script"] == "scout/scout_collect.py" and job["no_agent"] is False
    assert job["schedule"]["kind"] == "cron" and job["schedule"]["expr"] == "45 6 * * *"
    assert job["enabled_toolsets"] == ["kanban", "web", "no_mcp"]
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
    assert job["enabled_toolsets"] == ["kanban", "no_mcp"]
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
                 "SCOUT-LEDGER: <hash8>=<status>,<hash8>=<status>", "hooguit 3 kanbantaken per run",
                 *bot_scout.LEDGER_STATUSES):
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


def test_scout_route_is_chat_use_with_the_bot_edit_gate_inside():
    from api.governance.catalog import route_permission

    assert route_permission("/api/bots/scout", "POST") == "chat:use"
    src = (Path(__file__).resolve().parents[1] / "api" / "routes.py").read_text(encoding="utf-8")
    route = src[src.index('if parsed.path == "/api/bots/scout":'):]
    assert route[:route.index("if parsed.path ==", 10)].strip().endswith("return _handle_bot_scout(handler, body)")
    block = src[src.index("def _handle_bot_scout(handler, body):"):]
    block = block[:block.index("\ndef ", 10)]
    assert "_chat_profile_target_allowed(handler, name)" in block
    assert "_bot_editable_check(handler)" in block


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


def _route_env(monkeypatch, editor, caller=ALICE, chat=True):
    from api import routes
    import api.ownership as ownership
    monkeypatch.setattr(ownership, "request_owner_email", lambda handler: caller)
    monkeypatch.setattr(routes, "_chat_profile_target_allowed", lambda handler, name: chat)
    monkeypatch.setattr(routes, "_bot_editable_check", lambda handler: (lambda name, managed: editor))
    monkeypatch.setattr(routes, "_cron_admin_allowed", lambda handler: False)
    return routes


def _post(routes, body):
    h = _RouteHandler()
    routes._handle_bot_scout(h, body)
    return h.status, (json.loads(h.body.decode()) if h.body else {})


def test_scout_route_lets_a_chat_user_switch_their_own_scout_without_cron_admin(scout_env, monkeypatch):
    routes = _route_env(monkeypatch, editor=False, caller=BOB)
    status, body = _post(routes, {"name": "radar", "enabled": True, "revision": 0})
    assert status == 200 and body["scout_me"]["enabled"] is True and body["scout_me"]["job"]["enabled"] is True
    [job] = _jobs(scout_env.homes["radar"])
    assert job["owner_email"] == BOB and job["scout_person"] == BOB and job["origin"]["user_id"] == BOB
    # A non editor never sees who else has Scout on.
    assert "people" not in body["bot"]["scout"] and "scout_people_count" not in body


@pytest.mark.parametrize("extra", [{"person": ALICE}, {"topics": ["x"]}, {"default_time": "06:00"},
                                   {"spaces": ["spaces/AAQASUfEemQ"]}])
def test_scout_route_needs_the_bot_edit_gate_for_others_and_bot_fields(scout_env, monkeypatch, extra):
    routes = _route_env(monkeypatch, editor=False, caller=BOB)
    status, _ = _post(routes, {"name": "radar", "enabled": True, "revision": 0, **extra})
    assert status == 403
    assert _jobs(scout_env.homes["radar"]) == [] and _revision("radar") == 0


def test_scout_route_refuses_a_bot_without_chat_access(scout_env, monkeypatch):
    routes = _route_env(monkeypatch, editor=True, chat=False)
    status, _ = _post(routes, {"name": "radar", "enabled": True, "revision": 0})
    assert status == 404 and _jobs(scout_env.homes["radar"]) == []


def test_scout_route_refuses_a_caller_without_email(scout_env, monkeypatch):
    routes = _route_env(monkeypatch, editor=False, caller=None)
    status, _ = _post(routes, {"name": "radar", "enabled": True, "revision": 0})
    assert status == 403 and _jobs(scout_env.homes["radar"]) == []


def test_scout_route_lets_an_editor_set_someone_else(scout_env, monkeypatch):
    routes = _route_env(monkeypatch, editor=True)
    status, body = _post(routes, {"name": "radar", "person": BOB, "enabled": True, "digest_time": "09:15",
                                  "prompt": "Let op klantvragen", "revision": 0})
    assert status == 200 and body["scout_person"] == BOB
    assert body["scout_people_count"] == 1 and BOB in body["bot"]["scout"]["people"]
    assert body["scout_me"]["enabled"] is False
    [job] = _jobs(scout_env.homes["radar"])
    assert job["owner_email"] == BOB and job["schedule"]["expr"] == "15 9 * * *"
    assert "Wensen van Bob" in job["prompt"] and "Let op klantvragen" in job["prompt"]


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
    assert job["enabled_toolsets"] == ["kanban", "no_mcp"]


def test_unreadable_bot_metadata_is_unknown_and_gets_no_scout(scout_env):
    (scout_env.homes["radar"] / "profile.yaml").write_text("ui_meta: [unclosed\n")
    assert bot_metadata.read_profile("radar")["bot_kind"] == "unknown"
    assert bot_metadata.read_profile("missing-bot")["bot_kind"] == "unknown"
    for enabled in (True, False):
        with pytest.raises(bot_scout.ScoutError) as err:
            bot_scout.apply("radar", {"enabled": enabled, "revision": 0}, ALICE)
        assert err.value.status == 409
    assert _jobs(scout_env.homes["radar"]) == [] and not (scout_env.homes["radar"] / "scripts").exists()
    assert (scout_env.homes["radar"] / "profile.yaml").read_text() == "ui_meta: [unclosed\n"


def test_corrupt_metadata_is_a_clear_value_error_on_save(scout_env):
    path = scout_env.homes["radar"] / "profile.yaml"
    path.write_text("ui_meta: [unclosed\n")
    for call in (lambda: bot_metadata.save_profile("radar", {"title": "x"}, 0),
                 lambda: bot_metadata.save_scout("radar", {"enabled": False}, 0)):
        with pytest.raises(ValueError, match="not valid YAML"):
            call()
    assert path.read_text() == "ui_meta: [unclosed\n"


def test_nothing_is_copied_when_the_settings_are_not_saved(scout_env):
    _set("radar", enabled=False)
    with pytest.raises(RuntimeError):
        bot_scout.apply("radar", {"enabled": True, "revision": 0}, ALICE)
    assert not (scout_env.homes["radar"] / "scripts").exists()


def test_failed_copy_restores_the_previous_settings(scout_env, monkeypatch):
    def broken(home):
        raise OSError("disk full")
    monkeypatch.setattr(bot_scout, "install_runner", broken)
    with pytest.raises(OSError):
        _set("radar", enabled=True, topics=["AI act"])
    assert bot_metadata.read_profile("radar")["bot"]["scout"]["enabled"] is False
    assert _jobs(scout_env.homes["radar"]) == []


def test_the_bots_own_prompt_is_copied_once_and_then_kept(scout_env):
    dest = bot_scout.install_runner(scout_env.homes["radar"])
    assert (dest / "prompt.md").read_text() == "Eigen Scout prompt.\n"
    (dest / "prompt.md").write_text("Prompt van deze bot.\n")
    (scout_env.src / "prompt.md").write_text("Nieuwe gedeelde prompt.\n")
    (scout_env.src / "scout_ledger.py").write_text("print('ledger v2')\n")
    bot_scout.install_runner(scout_env.homes["radar"])
    assert (dest / "prompt.md").read_text() == "Prompt van deze bot.\n"
    assert (dest / "scout_ledger.py").read_text() == "print('ledger v2')\n"
    _set("radar", enabled=True)
    [job] = _jobs(scout_env.homes["radar"])
    assert job["prompt"].startswith("Prompt van deze bot.")
