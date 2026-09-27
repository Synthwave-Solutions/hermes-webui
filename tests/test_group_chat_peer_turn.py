"""Group conversations: typing while someone else's turn runs (27 Sep 2026).

Michael asked whether people can chat at the same time in a group chat. They
can type and send at any moment, but one answer runs at a time. Before this
change a message sent during someone else's turn was steered into that turn,
which runs under the other person's access. Now the server refuses that steer
(fallback ``peer_turn``) and the client queues the message, so it goes out as
the writer's own turn when the current one is done.
"""

import json
import os
import queue
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROOT = Path(__file__).resolve().parents[1]
MESSAGES_JS = (ROOT / "static" / "messages.js").read_text(encoding="utf-8")

YASER = "yaser@synthwave.solutions"
MICHAEL = "michael@synthwave.solutions"


@pytest.fixture
def steer_env():
    from api.config import (
        ACTIVE_RUNS, ACTIVE_RUNS_LOCK, SESSION_AGENT_CACHE, SESSION_AGENT_CACHE_LOCK,
        STREAMS, STREAMS_LOCK,
    )
    with SESSION_AGENT_CACHE_LOCK:
        cache_snap = dict(SESSION_AGENT_CACHE)
        SESSION_AGENT_CACHE.clear()
    with STREAMS_LOCK:
        streams_snap = dict(STREAMS)
        STREAMS.clear()
    with ACTIVE_RUNS_LOCK:
        runs_snap = dict(ACTIVE_RUNS)
        ACTIVE_RUNS.clear()
    yield
    with SESSION_AGENT_CACHE_LOCK:
        SESSION_AGENT_CACHE.clear()
        SESSION_AGENT_CACHE.update(cache_snap)
    with STREAMS_LOCK:
        STREAMS.clear()
        STREAMS.update(streams_snap)
    with ACTIVE_RUNS_LOCK:
        ACTIVE_RUNS.clear()
        ACTIVE_RUNS.update(runs_snap)


def _steer(caller, *, participants, run_sender="__owner__", register_run=True):
    """Steer a running turn as *caller*; return (response body, agent)."""
    from api.config import (
        SESSION_AGENT_CACHE, SESSION_AGENT_CACHE_LOCK, STREAMS, STREAMS_LOCK,
        register_active_run,
    )
    from api.models import Session
    from api.streaming import _handle_chat_steer

    sid, stream_id = "group-sid", "group-stream"
    agent = MagicMock()
    agent.steer = MagicMock(return_value=True)
    with SESSION_AGENT_CACHE_LOCK:
        SESSION_AGENT_CACHE[sid] = (agent, "sig")
    with STREAMS_LOCK:
        STREAMS[stream_id] = queue.Queue()
    if register_run:
        # The worker records None for the owner's own turn.
        register_active_run(stream_id, session_id=sid,
                            sender_email=None if run_sender == "__owner__" else run_sender)
    session = Session(session_id=sid, owner_email=YASER, participants=participants)
    session.active_stream_id = stream_id

    handler = MagicMock()
    handler.wfile = MagicMock()
    handler.headers = MagicMock()
    handler.headers.get = MagicMock(return_value="")
    with patch("api.streaming.get_session", return_value=session), \
            patch("api.streaming._cached_agent_matches_session", return_value=True), \
            patch("api.ownership.request_owner_email", return_value=caller):
        _handle_chat_steer(handler, {"session_id": sid, "text": "also check the footer"})
    body = json.loads(handler.wfile.write.call_args_list[-1][0][0].decode("utf-8"))
    return body, agent


def test_participant_cannot_steer_the_owners_turn(steer_env):
    body, agent = _steer(MICHAEL, participants=[MICHAEL])
    assert body["accepted"] is False
    assert body["fallback"] == "peer_turn"
    agent.steer.assert_not_called()


def test_owner_cannot_steer_a_participants_turn(steer_env):
    body, agent = _steer(YASER, participants=[MICHAEL], run_sender=MICHAEL)
    assert body["fallback"] == "peer_turn"
    agent.steer.assert_not_called()


def test_whoever_started_the_turn_can_still_steer_it(steer_env):
    body, agent = _steer(MICHAEL, participants=[MICHAEL], run_sender=MICHAEL)
    assert body["accepted"] is True
    agent.steer.assert_called_once_with("also check the footer")


def test_owner_steers_own_turn_in_a_group_chat(steer_env):
    body, agent = _steer(YASER, participants=[MICHAEL])
    assert body["accepted"] is True


def test_unknown_turn_owner_is_refused_in_a_group_chat(steer_env):
    body, agent = _steer(YASER, participants=[MICHAEL], register_run=False)
    assert body["fallback"] == "peer_turn"
    agent.steer.assert_not_called()


def test_one_person_chat_is_unchanged(steer_env):
    body, agent = _steer(YASER, participants=[], register_run=False)
    assert body["accepted"] is True


def _extract(src, name):
    start = src.index("function " + name + "(")
    brace = src.index("{", src.index(")", start))
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
    raise AssertionError(name)


def test_client_knows_when_the_running_turn_is_someone_elses():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not on PATH")
    driver = "\n".join([
        "const _peerTurnStreamIds = new Set();",
        _extract(MESSAGES_JS, "_rememberPeerTurn"),
        _extract(MESSAGES_JS, "_peerTurnIsRunning"),
        "globalThis.S = {activeStreamId: 'mine'};",
        "const out = [];",
        "out.push(_peerTurnIsRunning());",
        "_rememberPeerTurn('theirs');",
        "out.push(_peerTurnIsRunning());",
        "S.activeStreamId = 'theirs';",
        "out.push(_peerTurnIsRunning());",
        "for (let i = 0; i < 100; i++) _rememberPeerTurn('x' + i);",
        "out.push(_peerTurnStreamIds.size <= 64);",
        "process.stdout.write(JSON.stringify(out));",
    ])
    proc = subprocess.run([node, "-e", driver], text=True, capture_output=True, timeout=30, check=False)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == [False, False, True, True]


def test_send_never_steers_or_interrupts_a_peer_turn():
    start = MESSAGES_JS.index("async function send(")
    body = MESSAGES_JS[start:MESSAGES_JS.index("\nasync function ", start + 1)]
    assert "const _peerTurn=typeof _peerTurnIsRunning==='function'&&_peerTurnIsRunning();" in body
    assert "defaultMessageMode==='steer'&&S.activeStreamId&&!_peerTurn&&" in body
    assert "defaultMessageMode==='interrupt'&&!_peerTurn" in body
    assert "if(_peerTurn) showToast(t('group_turn_queued'),3000);" in body
    # The peer frame feeds the set.
    handler = MESSAGES_JS[MESSAGES_JS.index("es.addEventListener('peer_turn_started'"):]
    assert "_rememberPeerTurn(streamId);" in handler[:1500]
