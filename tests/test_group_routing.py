"""Group chat routing and live bot identity (plan 5.2, Wave 1, package W6).

An unaddressed message in a group chat goes to the bot that answered last
(sticky), else to the chat's default bot. A bot the sender may not use is
skipped, never silently used. The worker announces the bot of a group turn
(``turn_bot``), the other tabs learn it from ``peer_turn_started``, and the
Working state is kept per session. Handles are title slugs without internal
component names (plan E.4.3).
"""

from __future__ import annotations

import copy
import io
import json
import os
import queue
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from api import group_chat

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
ALICE = "alice@example.test"
BOB = "bob@example.test"
OWNER = "owner@example.test"


@pytest.fixture(autouse=True)
def _clean_routes():
    if not hasattr(group_chat, "_ROUTES"):
        yield
        return
    with group_chat._ROUTES_LOCK:
        saved = copy.deepcopy(group_chat._ROUTES)
        group_chat._ROUTES.clear()
    yield
    with group_chat._ROUTES_LOCK:
        group_chat._ROUTES.clear()
        group_chat._ROUTES.update(saved)


@pytest.fixture
def titles(monkeypatch):
    """Bot titles by profile id, as the bot owner set them."""
    table = {}
    monkeypatch.setattr(group_chat, "bot_title", lambda profile: table.get(profile))
    return table


def _group(bots=("writer", "reviewer"), messages=(), default=None, **extra):
    session = SimpleNamespace(session_id="group-1", owner_email=OWNER, participants=[ALICE, BOB],
                              bot_participants=list(bots), messages=list(messages), project_id=None, **extra)
    if default is not None:
        session.default_bot = default
    return session


def _reply(bot, text="Done"):
    return {"role": "assistant", "content": text, "bot_profile": bot, "bot_name": bot.title()}


def _allow(monkeypatch, allowed):
    calls = []

    def check(actor, bot):
        who = actor.get("email") if isinstance(actor, dict) else actor
        calls.append((who, bot))
        return (who, bot) in allowed or bot in allowed

    monkeypatch.setattr(group_chat, "bot_allowed", check)
    return calls


# ── Selection ────────────────────────────────────────────────────────────────

def test_mention_only_bot_sticky_and_default_in_order(monkeypatch, titles):
    _allow(monkeypatch, {"writer", "reviewer"})
    history = [{"role": "user", "content": "@reviewer check"}, _reply("reviewer")]
    assert group_chat.select_bot_with_reason(_group(messages=history), "@writer draft", ALICE) == ("writer", "mention")
    assert group_chat.select_bot_with_reason(_group(bots=["writer"]), "Hello", ALICE) == ("writer", "only_bot")
    assert group_chat.select_bot_with_reason(_group(messages=history), "And the rest?", ALICE) == ("reviewer", "sticky")
    assert group_chat.select_bot_with_reason(_group(messages=history, default="writer"), "More", ALICE) == ("reviewer", "sticky")
    assert group_chat.select_bot_with_reason(_group(default="writer"), "Start here", ALICE) == ("writer", "default")
    assert group_chat.select_bot_with_reason(_group(bots=[]), "Hello", ALICE) == (None, None)
    assert group_chat.selected_bot(_group(messages=history), "Go on", ALICE) == "reviewer"


def test_sticky_bot_is_the_latest_bot_reply(monkeypatch, titles):
    _allow(monkeypatch, {"writer", "reviewer"})
    history = [_reply("writer"), {"role": "user", "content": "@reviewer look"}, _reply("reviewer"),
               {"role": "assistant", "content": "status line without a bot"}, {"role": "tool", "content": "x"}]
    assert group_chat.last_bot(_group(messages=history)) == "reviewer"
    assert group_chat.select_bot_with_reason(_group(messages=history), "next", ALICE) == ("reviewer", "sticky")
    assert group_chat.last_bot(_group(messages=[{"role": "assistant", "content": "private chat era"}])) is None


def test_sender_without_rights_on_the_last_bot_is_asked_to_choose(monkeypatch, titles):
    calls = _allow(monkeypatch, {(ALICE, "reviewer"), (BOB, "writer")})
    session = _group(messages=[_reply("reviewer")])
    with pytest.raises(ValueError) as refused:
        group_chat.select_bot_with_reason(session, "Continue please", BOB)
    assert str(refused.value) == group_chat.LAST_BOT_UNAVAILABLE_ERROR
    assert str(refused.value) == "The last bot is not available to you. Choose a bot to continue."
    assert (BOB, "reviewer") in calls
    # The same message from someone who may use the last bot continues with it.
    assert group_chat.select_bot_with_reason(session, "Continue please", ALICE) == ("reviewer", "sticky")


def test_skipped_last_bot_falls_back_to_an_allowed_default(monkeypatch, titles):
    _allow(monkeypatch, {(BOB, "writer")})
    session = _group(messages=[_reply("reviewer")], default="writer")
    assert group_chat.select_bot_with_reason(session, "Continue", BOB) == ("writer", "default")


def test_default_bot_is_governed_at_use_time(monkeypatch, titles):
    calls = _allow(monkeypatch, {(ALICE, "writer")})
    session = _group(default="reviewer")
    with pytest.raises(ValueError) as refused:
        group_chat.select_bot_with_reason(session, "Hello", ALICE)
    assert str(refused.value) == group_chat.CHOOSE_BOT_ERROR
    assert calls == [(ALICE, "reviewer")]


def test_removed_bots_never_route(monkeypatch, titles):
    _allow(monkeypatch, {"writer", "reviewer", "retired"})
    session = _group(messages=[_reply("retired")], default="retired")
    with pytest.raises(ValueError) as refused:
        group_chat.select_bot_with_reason(session, "Hello", ALICE)
    assert str(refused.value) == group_chat.CHOOSE_BOT_ERROR
    session.default_bot = "../writer"
    assert group_chat.default_bot_of(session) is None
    session.default_bot = "writer"
    assert group_chat.select_bot_with_reason(session, "Hello", ALICE) == ("writer", "default")


def test_project_bots_filter_the_sticky_bot(monkeypatch, titles):
    from api import project_collaboration
    _allow(monkeypatch, {"writer", "reviewer"})
    monkeypatch.setattr(project_collaboration, "session_access", lambda s, actor: True)
    monkeypatch.setattr(project_collaboration, "project_for", lambda pid: {"bot_participants": ["writer"]})
    session = _group(messages=[_reply("reviewer")])
    assert group_chat.select_bot_with_reason(session, "Next", ALICE) == ("writer", "only_bot")
    monkeypatch.setattr(project_collaboration, "session_access", lambda s, actor: False)
    with pytest.raises(ValueError):
        group_chat.select_bot_with_reason(session, "Next", ALICE)


def test_mentions_resolve_by_id_case_or_title_handle(monkeypatch, titles):
    _allow(monkeypatch, {"sales-bot-7", "research"})
    titles.update({"sales-bot-7": "Sales", "research": "Research desk"})
    session = _group(bots=["sales-bot-7", "research"])
    assert group_chat.select_bot_with_reason(session, "@sales quote this", ALICE) == ("sales-bot-7", "mention")
    assert group_chat.select_bot_with_reason(session, "@Research-Desk dig", ALICE) == ("research", "mention")
    assert group_chat.select_bot_with_reason(session, "@RESEARCH dig", ALICE) == ("research", "mention")
    for message in ("@admin go", "@sal go", "@sales@example.test go"):
        with pytest.raises(ValueError):
            group_chat.select_bot_with_reason(session, message, ALICE)


def test_a_shared_title_resolves_only_to_the_one_usable_bot(monkeypatch, titles):
    titles.update({"sales-a": "Sales", "sales-b": "Sales"})
    _allow(monkeypatch, {(ALICE, "sales-b")})
    session = _group(bots=["sales-a", "sales-b"])
    assert group_chat.select_bot_with_reason(session, "@sales hi", ALICE) == ("sales-b", "mention")
    _allow(monkeypatch, {"sales-a", "sales-b"})
    with pytest.raises(ValueError):
        group_chat.select_bot_with_reason(session, "@sales hi", ALICE)


def test_a_mentioned_bot_the_sender_may_not_use_is_refused(monkeypatch, titles):
    _allow(monkeypatch, {(ALICE, "writer")})
    with pytest.raises(ValueError) as refused:
        group_chat.select_bot_with_reason(_group(), "@reviewer go", ALICE)
    assert "not allowed" in str(refused.value)


# ── Handles ──────────────────────────────────────────────────────────────────

def test_handles_are_title_slugs_without_internal_names(titles):
    from api.modules import DISPLAY_DENYLIST
    assert group_chat.handle_from_text("Sales") == "sales"
    assert group_chat.handle_from_text("Crème Brûlée desk!") == "creme-brulee-desk"
    assert group_chat.handle_from_text("Hermes Ops") == "ops"
    assert group_chat.handle_from_text("OmniRoute") == ""
    assert group_chat.handle_from_text("Mnemo-hub helper") == "helper"
    assert group_chat.handle_from_text("mnemo-OmniRoute-hub") == ""
    assert len(group_chat.handle_from_text("x" * 200)) == 64
    titles.update({"ops-omniroute": None, "legal": "Legal"})
    assert group_chat.bot_handle("legal") == "legal"
    assert group_chat.bot_handle("ops-omniroute") == "ops"
    assert group_chat.bot_handle("hermes") == "bot"
    for name in DISPLAY_DENYLIST:
        for text in (name, f"My {name} bot", f"{name}{name}x", name.upper()):
            handle = group_chat.handle_from_text(text)
            assert re.fullmatch(r"([a-z0-9][a-z0-9-]*)?", handle), handle
            assert not any(denied.lower() in handle for denied in DISPLAY_DENYLIST), (text, handle)


@pytest.mark.skipif(NODE is None, reason="node not on PATH")
def test_browser_handles_match_the_server_and_the_denylist():
    from api.modules import DISPLAY_DENYLIST
    samples = ["Sales", "Crème Brûlée desk!", "Hermes Ops", "OmniRoute", "Mnemo-hub helper",
               "mnemo-OmniRoute-hub", "x" * 200, "  Research   Desk  ", "N8N flows", "İstanbul office", "ß-team"]
    script = (
        "const fs=require('fs'),vm=require('vm');"
        "const ctx={window:{addEventListener(){}},document:{readyState:'loading',getElementById(){return null;},addEventListener(){}},S:{}};"
        "vm.runInNewContext(fs.readFileSync('static/chat-bots.js','utf8'),ctx);"
        "const r=ctx.window.chatBotRecipientRules;"
        "process.stdout.write(JSON.stringify({denylist:r.HANDLE_DENYLIST,handles:JSON.parse(process.argv[1]).map(r.handleFromText)}));"
    )
    result = subprocess.run([NODE, "-e", script, json.dumps(samples)], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert tuple(data["denylist"]) == tuple(DISPLAY_DENYLIST)
    assert data["handles"] == [group_chat.handle_from_text(text) for text in samples]


# ── Default bot ──────────────────────────────────────────────────────────────

def test_default_bot_is_validated_before_the_session_changes(monkeypatch):
    _allow(monkeypatch, {(OWNER, "writer"), (OWNER, "reviewer")})
    session = _group()
    before = dict(vars(session))
    for body in ({"default_bot": "stranger"}, {"default_bot": 7}, {"default_bot": "reviewer", "bot_participants": ["writer"]}):
        with pytest.raises(ValueError):
            group_chat.apply_participants_extra(session, body, OWNER)
        assert vars(session) == before
    _allow(monkeypatch, {(OWNER, "writer")})
    with pytest.raises(ValueError) as refused:
        group_chat.apply_participants_extra(session, {"default_bot": "reviewer"}, OWNER)
    assert "not available to you" in str(refused.value)
    assert vars(session) == before


def test_default_bot_set_kept_moved_and_cleared(monkeypatch):
    _allow(monkeypatch, {"writer", "reviewer", "editor"})
    session = _group()
    group_chat.apply_participants_extra(session, {"participants": [BOB]}, OWNER)
    assert not hasattr(session, "default_bot")
    group_chat.apply_participants_extra(session, {"default_bot": " reviewer "}, OWNER)
    assert session.default_bot == "reviewer"
    # A plain participants save keeps the default while its bot stays in the chat.
    group_chat.apply_participants_extra(session, {"participants": [BOB], "bot_participants": ["writer", "reviewer", "editor"]}, OWNER)
    assert session.default_bot == "reviewer"
    # Validated against the lists being saved, not the old ones.
    group_chat.apply_participants_extra(session, {"bot_participants": ["writer", "editor"], "default_bot": "editor"}, OWNER)
    assert session.default_bot == "editor"
    group_chat.apply_participants_extra(session, {"bot_participants": ["writer"]}, OWNER)
    assert session.default_bot is None
    session.default_bot = "writer"
    group_chat.apply_participants_extra(session, {"default_bot": ""}, OWNER)
    assert session.default_bot is None
    session.default_bot = "writer"
    group_chat.apply_participants_extra(session, {"default_bot": None}, OWNER)
    assert session.default_bot is None
    group_chat.apply_participants_extra(session, None, OWNER)
    assert session.default_bot is None


POLICY = {
    "version": 1,
    "mode": "enforce",
    "default_effect": "deny",
    "bootstrap_admins": ["boot@example.test"],
    "roles": {"member": {"grants": {"permissions": ["chat:use", "sessions:read", "sessions:write"],
                                    "profiles": ["*"], "routes": ["*"]}}},
    "users": {OWNER: {"roles": ["member"]}, BOB: {"roles": ["member"]}},
}


class _Handler:
    def __init__(self):
        self.status = None
        self.response_headers = []
        self.headers = {}
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass

    @property
    def body(self):
        return json.loads(self.wfile.getvalue().decode("utf-8"))


def test_participants_route_saves_a_valid_default_bot_and_refuses_others(monkeypatch):
    import api.governance.enforce as enforce
    import api.routes as routes
    from api.governance import loader

    policy = loader.parse_governance_policy(POLICY)
    loader.set_policy_loader(lambda: policy)
    saved = []

    class _Session:
        session_id = "g1"
        owner_email = OWNER
        participants = [BOB]
        bot_participants = ["writer", "reviewer"]
        profile = None
        project_id = None

        def save(self):
            saved.append((list(self.participants), list(self.bot_participants), getattr(self, "default_bot", None)))

    session = _Session()
    try:
        monkeypatch.setattr(enforce, "_request_identity", lambda handler: {"email": OWNER, "groups": [], "claims_subset": {}, "method": "oidc"})
        monkeypatch.setattr(routes, "_check_csrf", lambda _handler: True)
        monkeypatch.setattr(routes, "_guard_request_session_visibility", lambda handler, parsed, body=None, method="GET": True)
        monkeypatch.setattr(routes, "get_session", lambda sid, **kw: session)
        monkeypatch.setattr(routes, "_session_is_subagent_view_only", lambda sid: False)
        monkeypatch.setattr(routes, "_session_visible_to_request", lambda s, handler=None: True)
        monkeypatch.setattr(routes, "_group_participants_may_be_managed_by", lambda s, handler: True)
        monkeypatch.setattr(routes, "_audit_group_participants", lambda *a, **k: None)
        monkeypatch.setattr(routes, "_on_session_list_changed", lambda *a, **k: None)
        monkeypatch.setattr(routes, "publish_session_list_changed", lambda *a, **k: None)
        monkeypatch.setattr(group_chat, "validate", lambda values, owner_email=None: ([BOB], None))
        monkeypatch.setattr(group_chat, "validate_bots", lambda values, actor: list(values))
        calls = _allow(monkeypatch, {(OWNER, "writer"), (OWNER, "reviewer")})

        def post(body):
            monkeypatch.setattr(routes, "read_body", lambda _handler: copy.deepcopy(body))
            handler = _Handler()
            routes.handle_post(handler, SimpleNamespace(path="/api/session/participants", query=""))
            return handler

        base = {"session_id": "g1", "participants": [BOB], "bot_participants": ["writer", "reviewer"]}
        assert post({**base, "default_bot": "reviewer"}).status == 200
        assert saved[-1] == ([BOB], ["writer", "reviewer"], "reviewer")
        assert (OWNER, "reviewer") in calls
        refused = post({**base, "default_bot": "stranger"})
        assert refused.status == 400 and "bots in this chat" in refused.body["error"]
        assert len(saved) == 1 and session.default_bot == "reviewer"
        # Removing the default bot from the chat clears the default in the same save.
        assert post({**base, "bot_participants": ["writer"]}).status == 200
        assert saved[-1] == ([BOB], ["writer"], None)
    finally:
        loader.set_policy_loader(None)


# ── Route memory, turn_bot, peer fields and the Working state ────────────────

def test_remembered_route_feeds_turn_bot_and_peer_fields(monkeypatch, titles):
    from api import config
    titles.update({"sales-bot-7": "Sales"})
    config.register_stream_owner("st-1", "group-1")
    try:
        group_chat.remember_route_reason("st-1", "sales-bot-7", "sticky")
        assert group_chat.route_for_stream("st-1")["session_id"] == "group-1"
        event = group_chat.turn_bot_event("group-1", "st-1", "sales-bot-7")
        assert event == {"session_id": "group-1", "stream_id": "st-1", "bot": "sales-bot-7",
                         "reason": "sticky", "handle": "sales", "name": "Sales"}
        session = _group(active_stream_id="st-1")
        assert group_chat.turn_started_extra(session, "sales-bot-7") == {
            "bot_profile": "sales-bot-7", "bot_handle": "sales", "bot_name": "Sales", "route_reason": "sticky"}
        # routes passes the bot as an attribute that may be missing; the active stream answers.
        assert group_chat.turn_started_extra(session, None)["bot_profile"] == "sales-bot-7"
        assert group_chat.turn_started_extra(_group(active_stream_id="other"), None) == {}
        assert group_chat.turn_started_extra(_group(active_stream_id="st-1"), "writer") == {
            "bot_profile": "writer", "bot_handle": "writer"}
    finally:
        config.unregister_stream_owner("st-1")


def test_turn_bot_event_without_a_reason_or_metadata_never_raises(monkeypatch):
    def broken(profile):
        raise RuntimeError("metadata unreadable")

    from api import bot_metadata
    monkeypatch.setattr(bot_metadata, "read_profile", broken)
    event = group_chat.turn_bot_event("group-1", "st-2", "writer")
    assert event == {"session_id": "group-1", "stream_id": "st-2", "bot": "writer", "handle": "writer"}
    assert group_chat.route_for_stream("st-2")["session_id"] == "group-1"
    group_chat.remember_route_reason("st-3", "writer", "invented")
    assert group_chat.route_for_stream("st-3")["reason"] is None
    group_chat.remember_route_reason("st-4", "../writer", "sticky")
    group_chat.remember_route_reason("", "writer", "sticky")
    assert group_chat.route_for_stream("st-4") is None and len(group_chat._ROUTES) == 2
    assert group_chat.turn_started_extra(object(), None) == {}


def test_working_state_follows_the_running_stream(monkeypatch):
    from api import config
    monkeypatch.setattr(config, "ACTIVE_RUNS", {})
    monkeypatch.setattr(config, "STREAMS", {})
    for stream_id in ("old", "new"):
        config.register_stream_owner(stream_id, "group-1")
    try:
        group_chat.remember_route_reason("old", "writer", "mention")
        group_chat.remember_route_reason("new", "reviewer", "sticky")
        assert group_chat.working_state("group-1") is None
        config.STREAMS["new"] = object()
        state = group_chat.working_state("group-1")
        assert state["bot"] == "reviewer" and state["stream_id"] == "new" and state["reason"] == "sticky"
        config.ACTIVE_RUNS["old"] = {}
        assert group_chat.working_state("group-1")["bot"] == "reviewer"
        del config.STREAMS["new"]
        assert group_chat.working_state("group-1")["bot"] == "writer"
        assert group_chat.working_state("group-2") is None and group_chat.working_state("") is None
        config.ACTIVE_RUNS.clear()
        assert group_chat.working_state("group-1") is None
    finally:
        for stream_id in ("old", "new"):
            config.unregister_stream_owner(stream_id)


def test_latest_route_reason_is_the_newest_turn_of_the_session(monkeypatch):
    from api import config
    monkeypatch.setattr(config, "ACTIVE_RUNS", {})
    monkeypatch.setattr(config, "STREAMS", {})
    for stream_id, sid in (("t1", "group-1"), ("t2", "group-1"), ("t3", "group-2")):
        config.register_stream_owner(stream_id, sid)
    try:
        assert group_chat.latest_route_reason("group-1", "writer") is None
        group_chat.remember_route_reason("t1", "writer", "mention")
        # The stream has ended by the time a reply is stamped; the reason is still known.
        assert group_chat.latest_route_reason("group-1", "writer") == "mention"
        group_chat.remember_route_reason("t2", "reviewer", "default")
        group_chat.remember_route_reason("t3", "writer", "sticky")
        # Only the newest turn of the session counts, and only for its own bot.
        assert group_chat.latest_route_reason("group-1", "reviewer") == "default"
        assert group_chat.latest_route_reason("group-1", "writer") is None
        assert group_chat.latest_route_reason("group-2", "writer") == "sticky"
        for sid, bot in (("", "writer"), (None, "writer"), ("group-1", None), ("group-9", "reviewer")):
            assert group_chat.latest_route_reason(sid, bot) is None
    finally:
        for stream_id in ("t1", "t2", "t3"):
            config.unregister_stream_owner(stream_id)


def test_route_memory_is_bounded(monkeypatch):
    from api import config
    monkeypatch.setattr(config, "ACTIVE_RUNS", {"keep": {}})
    monkeypatch.setattr(config, "STREAMS", {})
    monkeypatch.setattr(group_chat, "_ROUTES_MAX", 5)
    group_chat.remember_route_reason("keep", "writer", "mention")
    for index in range(10):
        group_chat.remember_route_reason(f"s{index}", "writer", "mention")
    assert len(group_chat._ROUTES) == 5
    # Idle, finished streams are dropped; a running one is kept.
    monkeypatch.setattr(group_chat, "_ROUTES_MAX", 50)
    with group_chat._ROUTES_LOCK:
        group_chat._ROUTES.clear()
    group_chat.remember_route_reason("keep", "writer", "mention")
    group_chat.remember_route_reason("done", "writer", "mention")
    with group_chat._ROUTES_LOCK:
        for entry in group_chat._ROUTES.values():
            entry["since"] -= 10_000
    group_chat.remember_route_reason("fresh", "writer", "mention")
    assert list(group_chat._ROUTES) == ["keep", "fresh"]


# ── The worker's turn_bot event ──────────────────────────────────────────────

def _run_worker(monkeypatch, tmp_path, *, execution_profile, allowed=True, sender="alice@example.test"):
    from api import personal_context, streaming
    stream_id = "w6-worker-" + str(execution_profile)
    events = queue.Queue()
    monkeypatch.setattr(streaming, "STREAMS", {stream_id: events})
    monkeypatch.setattr(streaming, "RunJournalWriter", lambda *a: None)
    monkeypatch.setattr(streaming, "append_turn_journal_event_for_stream", lambda *a, **kw: None)
    monkeypatch.setattr(streaming, "_report_capacity_incident", lambda *a, **kw: None)
    session = _group(bots=["writer", "reviewer"], profile="conversation", active_stream_id=stream_id,
                     pending_user_message="Continue", pending_attachments=[], pending_started_at=None,
                     pending_user_source=None, save=lambda **kw: None)
    session.session_id = "w6-group"
    monkeypatch.setattr(streaming, "get_session", lambda sid, **kw: session)
    monkeypatch.setattr(group_chat, "bot_allowed", lambda actor, bot: allowed)
    monkeypatch.setattr(group_chat, "require_turn_membership", lambda s, actor: None)
    monkeypatch.setattr(group_chat, "bot_title", lambda profile: "Review desk" if profile == "reviewer" else None)

    def stop(*args, **kwargs):
        raise PermissionError("stopped after the announcement")

    monkeypatch.setattr(personal_context, "ensure_home", stop)
    if execution_profile:
        group_chat.remember_route_reason(stream_id, execution_profile, "sticky")
    streaming._run_agent_streaming(
        "w6-group", "Continue", "qa-model", str(tmp_path), stream_id,
        sender_email=sender, sender_identity={"email": sender} if sender else None,
        execution_profile=execution_profile,
    )
    rows = []
    while not events.empty():
        rows.append(events.get_nowait())
    return [row for row in rows if row[0] != "metering"]


def test_worker_announces_the_group_bot_first(monkeypatch, tmp_path):
    rows = _run_worker(monkeypatch, tmp_path, execution_profile="reviewer")
    assert rows[0][0] == "turn_bot"
    assert rows[0][1] == {"session_id": "w6-group", "stream_id": "w6-worker-reviewer", "bot": "reviewer",
                          "reason": "sticky", "handle": "review-desk", "name": "Review desk"}
    assert [row[0] for row in rows].count("turn_bot") == 1


def test_worker_announces_nothing_for_a_revoked_bot_or_a_private_turn(monkeypatch, tmp_path):
    rows = _run_worker(monkeypatch, tmp_path, execution_profile="reviewer", allowed=False)
    assert rows and not any(row[0] == "turn_bot" for row in rows)
    assert any("no longer allowed" in str(row) for row in rows)
    rows = _run_worker(monkeypatch, tmp_path, execution_profile=None, sender=None)
    assert rows and not any(row[0] == "turn_bot" for row in rows)


def test_streaming_has_one_turn_bot_put_after_the_bot_recheck_and_keeps_the_visuals_seam():
    src = (ROOT / "api" / "streaming.py").read_text(encoding="utf-8")
    assert src.count("put('turn_bot'") == 1 and src.count('"turn_bot"') == 0
    recheck = src.index("raise PermissionError('Selected group bot is no longer allowed')")
    announce = src.index("put('turn_bot', turn_bot_event(session_id, stream_id, execution_profile))")
    overlay = src.index("_personal_root = personal_context.ensure_home(_turn_identity)")
    assert recheck < announce < overlay
    # The addendum's AE-5 visuals prompt seam stays in place.
    assert "webui_visuals.prompt_block(config_data)" in src


# ── Chat start through the routing seams ─────────────────────────────────────

def _chat_start_fakes(monkeypatch):
    from api import routes, turn_journal
    monkeypatch.setattr(routes, "_read_profile_model_config", lambda s, p: ("custom:router", s.profile + "-model", {}))
    monkeypatch.setattr(routes, "_active_run_stream_for_session", lambda sid: None)
    monkeypatch.setattr(routes, "_is_hidden_empty_session", lambda s: False)
    monkeypatch.setattr(routes, "_prepare_chat_start_session_for_stream",
                        lambda s, **kw: setattr(s, "active_stream_id", kw["stream_id"]))
    monkeypatch.setattr(turn_journal, "append_turn_journal_event", lambda *a, **kw: {})
    monkeypatch.setattr(routes, "set_last_workspace", lambda *a: None)
    monkeypatch.setattr(routes, "webui_gateway_chat_enabled", lambda cfg: True)
    monkeypatch.setattr(routes, "get_config", lambda: {})
    launched = []

    class Thread:
        def __init__(self, **kw):
            launched.append(kw)

        def start(self):
            pass

    monkeypatch.setattr(routes.threading, "Thread", Thread)
    return routes, launched


def test_unaddressed_group_message_continues_with_the_last_bot(monkeypatch, titles):
    routes, launched = _chat_start_fakes(monkeypatch)
    titles.update({"sales": "Sales"})
    _allow(monkeypatch, {(ALICE, "sales"), (ALICE, "research")})
    session = _group(bots=["research", "sales"], messages=[{"role": "user", "content": "@sales price?"}, _reply("sales")],
                     profile="conversation", pending_started_at=1, title="Group")
    session.session_id = "w6-chat-start"
    result = routes._start_chat_stream_for_session(session, msg="And for ten seats?", attachments=[], workspace="/tmp",
                                                   model="old", model_provider="old", normalized_model="old",
                                                   sender_email=ALICE)
    try:
        assert result.get("_status", 200) == 200, result
        assert launched[-1]["kwargs"]["execution_profile"] == "sales"
        assert result.execution_profile == "sales"
        assert group_chat.route_for_stream(result["stream_id"])["reason"] == "sticky"

        class Channel:
            frames = []

            def emit(self, name, payload):
                self.frames.append((name, payload))

        channel = Channel()
        from api import background_process
        monkeypatch.setattr(background_process, "get_session_channel", lambda sid: channel)
        assert routes._fan_out_peer_turn(session, result, ALICE, "And for ten seats?", []) is True
        name, payload = channel.frames[-1]
        assert name == "peer_turn_started"
        assert payload["bot_profile"] == "sales" and payload["bot_handle"] == "sales"
        assert payload["route_reason"] == "sticky" and payload["sender_email"] == ALICE
    finally:
        routes.STREAMS.pop(result.get("stream_id"), None)
        routes.unregister_stream_owner(result.get("stream_id"))


def test_sender_who_may_not_use_the_last_bot_gets_the_choose_prompt(monkeypatch, titles):
    routes, launched = _chat_start_fakes(monkeypatch)
    _allow(monkeypatch, {(BOB, "research")})
    session = _group(bots=["research", "sales"], messages=[_reply("sales")], profile="conversation",
                     pending_started_at=1, title="Group")
    session.session_id = "w6-chat-refused"
    result = routes._start_chat_stream_for_session(session, msg="Continue", attachments=[], workspace="/tmp",
                                                   model="old", model_provider="old", normalized_model="old",
                                                   sender_email=BOB)
    assert result == {"error": "The last bot is not available to you. Choose a bot to continue.", "_status": 403}
    assert launched == []


# ── Browser behaviour (tests/group_routing_ui.cjs) ───────────────────────────

@pytest.mark.skipif(NODE is None, reason="node not on PATH")
def test_group_routing_ui_behaviour():
    result = subprocess.run([NODE, str(ROOT / "tests" / "group_routing_ui.cjs")], cwd=ROOT,
                            capture_output=True, text=True, timeout=180, env=dict(os.environ))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "group routing vm checks passed" in result.stdout
