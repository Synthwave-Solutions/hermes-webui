"""``GET /api/agui/runs/<stream_id>``: replay one finished run as AG-UI events.

Plan 5.1 and Appendix C: the route needs ``sessions:read`` and then admits only
the owner of the run's conversation or a current participant. It denies when
the owner cannot be resolved (``_stream_id_visible_to_request_profile`` allows
that case, so it is not reused). Every refusal before authorization is the
generic 404, so a stream's existence never leaks.
"""
from __future__ import annotations

import io
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
from jsonschema import Draft202012Validator

from api import agui
from api.governance import loader
from api.governance.catalog import route_permission
from api.governance.enforce import evaluate_request
from api.governance.loader import parse_governance_policy
from api.run_journal import append_run_event, read_run_events

OWNER = "owner@example.test"
PARTICIPANT = "colleague@example.test"
STRANGER = "stranger@example.test"
ADMIN = "boot@example.test"
SCHEMA = json.loads((Path(__file__).resolve().parent / "fixtures" / "agui" / "ag-ui-1.0.schema.json")
                    .read_text(encoding="utf-8"))

POLICY = {
    "version": 1,
    "mode": "enforce",
    "default_effect": "deny",
    "bootstrap_admins": [ADMIN],
    "roles": {
        "member": {"grants": {"permissions": ["chat:use", "sessions:read"], "profiles": ["*"], "routes": ["*"]}},
        "no_sessions": {"grants": {"permissions": ["chat:use"], "profiles": ["*"], "routes": ["*"]}},
    },
    "users": {
        OWNER: {"roles": ["member"]},
        PARTICIPANT: {"roles": ["member"]},
        STRANGER: {"roles": ["no_sessions"]},
    },
}


class _Handler:
    """Records one response the way BaseHTTPRequestHandler would send it."""

    def __init__(self):
        self.status = None
        self.headers = {}
        self.response_headers = []
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass

    def header(self, name):
        return next((v for k, v in self.response_headers if k.lower() == name.lower()), None)

    @property
    def raw(self):
        return self.wfile.getvalue()

    def events(self):
        body = self.raw.decode("utf-8")
        assert body.endswith("\n\n") and "\r" not in body
        frames = body.split("\n\n")[:-1]
        assert all(frame.startswith("data: ") and "\n" not in frame for frame in frames)
        return [json.loads(frame[len("data: "):]) for frame in frames]


def _identity(email):
    return {"email": email, "groups": [], "claims_subset": {}, "method": "oidc"}


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Journals under a temporary session dir; owner sessions from a table."""
    import api.config as config
    import api.governance.enforce as enforce
    import api.models as models
    import api.run_journal as run_journal

    monkeypatch.setattr(run_journal, "_default_session_dir", lambda: tmp_path)
    sessions = {}

    def fake_get_session(sid, metadata_only=False):
        if sid not in sessions:
            raise KeyError(sid)
        return sessions[sid]

    monkeypatch.setattr(models, "get_session", fake_get_session)
    who = SimpleNamespace(email=OWNER)
    monkeypatch.setattr(enforce, "_request_identity", lambda handler: _identity(who.email) if who.email else None)
    monkeypatch.delenv(agui.REPLAY_MAX_BYTES_ENV, raising=False)
    live = set()

    def add_run(session_id, stream_id, frames, *, owner=OWNER, participants=(), session=True):
        for seq, (event, payload) in enumerate(frames, start=1):
            append_run_event(session_id, stream_id, event, payload, session_dir=tmp_path, seq=seq,
                             created_at=1790000000.0 + seq)
        if session:
            sessions[session_id] = SimpleNamespace(session_id=session_id, owner_email=owner,
                                                   participants=list(participants), profile="default")
        return tmp_path / "_run_journal" / session_id / f"{stream_id}.jsonl"

    def get(stream_id, email=OWNER, path=None):
        who.email = email
        handler = _Handler()
        target = path if path is not None else f"/api/agui/runs/{stream_id}"
        result = agui.handle_replay(handler, urlparse("http://localhost" + target))
        return result, handler

    yield SimpleNamespace(add_run=add_run, get=get, sessions=sessions, root=tmp_path, live=live, who=who)
    with config.ACTIVE_RUNS_LOCK:
        for stream_id in live:
            config.ACTIVE_RUNS.pop(stream_id, None)


FINISHED = [
    ("token", {"text": "Hello"}),
    ("tool", {"name": "web", "args": {"q": "x"}, "tid": "c1"}),
    ("tool_complete", {"name": "web", "tid": "c1", "preview": "ok"}),
    ("done", {"session": {"messages": [{"role": "user", "content": "Hi"},
                                       {"role": "assistant", "content": "Hello"}]},
              "usage": {"input_tokens": 3, "output_tokens": 1}}),
    ("stream_end", {}),
]


def _refused(result, handler):
    """The generic refusal: the caller answers 404, nothing was written."""
    return result is False and handler.status is None and handler.raw == b""


# ── Access ───────────────────────────────────────────────────────────────────

def test_owner_gets_the_projection_of_the_finished_run(env):
    env.add_run("sess_a", "run_a", FINISHED)
    result, handler = env.get("run_a")
    assert result is True and handler.status == 200
    assert handler.header("Content-Type") == "text/event-stream; charset=utf-8"
    assert handler.header("Cache-Control") == "no-store"
    assert handler.header("X-Content-Type-Options") == "nosniff"
    assert int(handler.header("Content-Length")) == len(handler.raw)
    rows = read_run_events("sess_a", "run_a", session_dir=env.root)["events"]
    assert handler.events() == agui.project_journal(rows)
    assert handler.events()[0]["type"] == "RUN_STARTED" and handler.events()[-1]["type"] == "RUN_FINISHED"


def test_the_response_carries_a_pending_auth_cookie_like_every_other_response(env):
    env.add_run("sess_a", "run_a", FINISHED)
    handler = _Handler()
    handler._pending_set_cookies = ["hermes_session=refreshed; Path=/; HttpOnly"]
    assert agui.handle_replay(handler, urlparse("http://localhost/api/agui/runs/run_a")) is True
    assert handler.header("Set-Cookie") == "hermes_session=refreshed; Path=/; HttpOnly"
    assert handler.header("X-Accel-Buffering") == "no"


def test_replay_body_is_schema_valid_ag_ui_without_null(env):
    env.add_run("sess_a", "run_a", FINISHED)
    _result, handler = env.get("run_a")
    validator = Draft202012Validator(SCHEMA)
    for event in handler.events():
        assert not list(validator.iter_errors(event)), event
    assert b"null" not in handler.raw


def test_a_current_participant_may_replay(env):
    env.add_run("sess_a", "run_a", FINISHED, participants=[PARTICIPANT])
    result, handler = env.get("run_a", email=PARTICIPANT.upper())
    assert result is True and handler.status == 200


def test_a_foreign_stream_is_refused_with_the_generic_404(env):
    env.add_run("sess_a", "run_a", FINISHED, participants=[PARTICIPANT])
    assert _refused(*env.get("run_a", email=STRANGER))


def test_a_participant_removed_after_the_run_is_refused(env):
    env.add_run("sess_a", "run_a", FINISHED, participants=[PARTICIPANT])
    assert env.get("run_a", email=PARTICIPANT)[1].status == 200
    env.sessions["sess_a"].participants = []
    assert _refused(*env.get("run_a", email=PARTICIPANT))
    assert env.get("run_a", email=OWNER)[1].status == 200


def test_an_unresolvable_owner_session_is_refused(env):
    env.add_run("sess_gone", "run_gone", FINISHED, session=False)
    assert _refused(*env.get("run_gone", email=OWNER))


@pytest.mark.parametrize("owner", [None, "", "   "])
def test_a_conversation_without_an_owner_is_refused_even_for_its_participants(env, owner):
    env.add_run("sess_a", "run_a", FINISHED, owner=owner, participants=[PARTICIPANT])
    assert _refused(*env.get("run_a", email=PARTICIPANT))
    assert _refused(*env.get("run_a", email=ADMIN))


def test_a_session_that_resolves_to_another_id_is_refused(env):
    env.add_run("sess_a", "run_a", FINISHED)
    env.sessions["sess_a"] = SimpleNamespace(session_id="sess_other", owner_email=OWNER, participants=[])
    assert _refused(*env.get("run_a"))


def test_a_request_without_an_identity_is_refused(env):
    env.add_run("sess_a", "run_a", FINISHED)
    assert _refused(*env.get("run_a", email=None))


def test_an_administrator_gets_no_wider_access(env):
    env.add_run("sess_a", "run_a", FINISHED)
    assert _refused(*env.get("run_a", email=ADMIN))


def test_the_check_uses_the_real_session_fields(env):
    """A real Session normalizes participants; the owner is never a participant."""
    import api.models as models

    env.add_run("sess_real", "run_real", FINISHED, session=False)
    env.sessions["sess_real"] = models.Session(session_id="sess_real", owner_email=OWNER.upper(),
                                               participants=[PARTICIPANT.upper(), "not-an-address", OWNER])
    assert env.get("run_real", email=OWNER)[1].status == 200
    assert env.get("run_real", email=PARTICIPANT)[1].status == 200
    assert _refused(*env.get("run_real", email=STRANGER))


# ── Stream id and journal location ───────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "/api/agui/runs/",
    "/api/agui/runs/run_unknown",
    "/api/agui/runs/..",
    "/api/agui/runs/.",
    "/api/agui/runs/run_a/extra",
    "/api/agui/runs/run_a%2F..",
    "/api/agui/runs/run*",
    "/api/agui/runs/run a",
    "/api/agui/other/run_a",
])
def test_unknown_and_malformed_stream_ids_are_refused(env, path):
    env.add_run("sess_a", "run_a", FINISHED)
    assert _refused(*env.get(None, path=path))


def test_the_stub_contract_without_a_request_path_is_kept():
    assert agui.handle_replay(_Handler(), None) is False


def test_a_stream_id_journaled_in_two_conversations_is_refused(env):
    env.add_run("sess_a", "run_dup", FINISHED)
    env.add_run("sess_b", "run_dup", FINISHED)
    assert _refused(*env.get("run_dup"))


def test_a_symlinked_journal_file_is_refused(env):
    real = env.add_run("sess_a", "run_real", FINISHED)
    link_dir = env.root / "_run_journal" / "sess_b"
    link_dir.mkdir(parents=True)
    os.symlink(real, link_dir / "run_link.jsonl")
    env.sessions["sess_b"] = SimpleNamespace(session_id="sess_b", owner_email=OWNER, participants=[])
    assert _refused(*env.get("run_link"))
    assert env.get("run_real")[1].status == 200


def test_a_journal_reached_through_a_symlinked_session_directory_is_refused(env):
    outside = env.root / "outside"
    env.add_run("sess_c", "run_c", FINISHED)
    shutil.move(str(env.root / "_run_journal" / "sess_c"), str(outside))
    os.symlink(outside, env.root / "_run_journal" / "sess_c")
    assert (env.root / "_run_journal" / "sess_c" / "run_c.jsonl").is_file()
    assert _refused(*env.get("run_c"))


# ── Run state ────────────────────────────────────────────────────────────────

def test_a_live_run_answers_409_to_its_owner_and_404_to_anyone_else(env):
    import api.config as config

    env.add_run("sess_a", "run_live", [("token", {"text": "working"})])
    with config.ACTIVE_RUNS_LOCK:
        config.ACTIVE_RUNS["run_live"] = {"session_id": "sess_a"}
    env.live.add("run_live")
    result, handler = env.get("run_live")
    assert result is True and handler.status == 409
    assert json.loads(handler.raw)["error"] == "This run is still in progress. Try again when it has finished."
    assert _refused(*env.get("run_live", email=STRANGER))


def test_a_run_in_the_stream_registry_is_live_too(env, monkeypatch):
    import api.config as config

    env.add_run("sess_a", "run_stream", FINISHED)
    monkeypatch.setitem(config.STREAMS, "run_stream", object())
    assert env.get("run_stream")[1].status == 409


def test_a_run_whose_worker_is_gone_replays_as_an_interrupted_run(env):
    env.add_run("sess_a", "run_lost", [("token", {"text": "partial"}), ("tool", {"name": "x", "tid": "c"})])
    result, handler = env.get("run_lost")
    assert result is True and handler.status == 200
    events = handler.events()
    assert events[-1]["type"] == "RUN_ERROR" and events[-1]["code"] == "interrupted"
    assert events[-1]["message"] == "The live worker stopped before this run finished."
    rows = read_run_events("sess_a", "run_lost", session_dir=env.root)["events"]
    assert len(rows) == 2  # the replay never writes to the journal


def test_an_oversized_journal_answers_413_to_the_owner(env, monkeypatch):
    env.add_run("sess_a", "run_big", FINISHED)
    monkeypatch.setenv(agui.REPLAY_MAX_BYTES_ENV, "100")
    result, handler = env.get("run_big")
    assert result is True and handler.status == 413
    assert _refused(*env.get("run_big", email=STRANGER))
    monkeypatch.setenv(agui.REPLAY_MAX_BYTES_ENV, "not a number")
    assert agui.replay_max_bytes() == agui.DEFAULT_REPLAY_MAX_BYTES
    assert env.get("run_big")[1].status == 200


@pytest.mark.parametrize("damage", ["malformed_line", "foreign_row", "gap"])
def test_a_damaged_journal_answers_422_to_the_owner(env, damage):
    path = env.add_run("sess_a", "run_bad", FINISHED)
    lines = path.read_text(encoding="utf-8").splitlines()
    if damage == "malformed_line":
        lines.insert(2, "{not json")
    elif damage == "foreign_row":
        row = json.loads(lines[1])
        row["session_id"] = "sess_other"
        lines[1] = json.dumps(row)
    else:
        del lines[2]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result, handler = env.get("run_bad")
    assert result is True and handler.status == 422
    assert _refused(*env.get("run_bad", email=STRANGER))


def test_an_empty_journal_is_not_found(env):
    path = env.add_run("sess_a", "run_empty", FINISHED)
    path.write_text("", encoding="utf-8")
    assert _refused(*env.get("run_empty"))


# ── Wiring and governance ────────────────────────────────────────────────────

def test_the_get_dispatcher_serves_the_route(env, monkeypatch):
    import api.routes as routes

    env.add_run("sess_a", "run_a", FINISHED)
    monkeypatch.setattr(routes, "_guard_request_session_visibility",
                        lambda handler, parsed, body=None, method="GET": True)
    env.who.email = OWNER
    handler = _Handler()
    assert routes.handle_get(handler, urlparse("http://localhost/api/agui/runs/run_a")) is True
    assert handler.status == 200 and handler.events()[0]["type"] == "RUN_STARTED"
    env.who.email = STRANGER
    stranger = _Handler()
    assert routes.handle_get(stranger, urlparse("http://localhost/api/agui/runs/run_a")) is False
    assert stranger.status is None


def test_governance_requires_sessions_read_before_the_handler_runs():
    policy = parse_governance_policy(POLICY)
    loader.set_policy_loader(lambda: policy)
    try:
        assert route_permission("/api/agui/runs/run_a", "GET") == "sessions:read"
        assert evaluate_request(_identity(OWNER), "GET", "/api/agui/runs/run_a").allow
        decision = evaluate_request(_identity(STRANGER), "GET", "/api/agui/runs/run_a")
        assert (decision.allow, decision.reason) == (False, "permission_not_allowed")
    finally:
        loader.set_policy_loader(None)
