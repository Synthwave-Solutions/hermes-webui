"""SynthPulse: the first LLM title no longer holds a finished turn open.

The turn ends (stream_end) as soon as the answer is written; the title thread
publishes on the per-session channel, and /api/session/stream replays a
generated title to every new subscriber.
"""
from pathlib import Path
import queue
import uuid

from api import streaming
from api.background_process import subscribe_to_session_channel

ROOT = Path(__file__).parent.parent
STREAMING_SRC = (ROOT / "api" / "streaming.py").read_text(encoding="utf-8")
ROUTES_SRC = (ROOT / "api" / "routes.py").read_text(encoding="utf-8")
MESSAGES_SRC = (ROOT / "static" / "messages.js").read_text(encoding="utf-8")


def test_stream_end_is_sent_before_the_first_title_thread_starts():
    branch = STREAMING_SRC.index("if _should_bg_title and _u0 and _a0:")
    end = STREAMING_SRC.index("put('stream_end', {'session_id': session_id})", branch)
    thread = STREAMING_SRC.index("target=_run_background_title_update", branch)
    assert end < thread
    window = STREAMING_SRC[thread:thread + 400]
    assert "_session_channel_put(s.session_id)" in window
    assert "'emit_stream_end': False" in window


def test_title_thread_without_stream_end_never_emits_it():
    events = []
    missing = f"missing-{uuid.uuid4().hex}"
    streaming._run_background_title_update(
        missing, "hello", "hi", "hello", lambda e, d: events.append(e), emit_stream_end=False,
    )
    assert "stream_end" not in events
    events.clear()
    streaming._run_background_title_update(missing, "hello", "hi", "hello", lambda e, d: events.append(e))
    assert events[-1] == "stream_end"


def test_session_channel_put_reaches_a_subscribed_tab():
    sid = f"title-{uuid.uuid4().hex}"
    channel, q = subscribe_to_session_channel(sid)
    try:
        streaming._session_channel_put(sid)("title", {"session_id": sid, "title": "Quarterly plan"})
        received = q.get(timeout=2)
        assert "title" in str(received) and "Quarterly plan" in str(received)
    finally:
        channel.unsubscribe(q)


def test_session_channel_put_without_subscribers_is_silent():
    streaming._session_channel_put(f"nobody-{uuid.uuid4().hex}")("title", {"title": "x"})


def test_session_stream_replays_a_generated_title_on_subscribe():
    handler = ROUTES_SRC.index("def _handle_session_sse_stream")
    replay = ROUTES_SRC.index("session-stream title replay failed", handler)
    window = ROUTES_SRC[replay - 900:replay]
    assert "llm_title_generated" in window
    assert "_sse(handler, 'title'" in window


def test_frontend_applies_titles_from_the_session_channel():
    assert "es.addEventListener('title'" in MESSAGES_SRC
    block = MESSAGES_SRC[MESSAGES_SRC.index("es.addEventListener('title'"):][:400]
    assert "applySessionTitleUpdate(" in block
