"""Deleting a conversation while its answer is still being written (27 Sep 2026).

Found in the live smoke test after the upstream restoration: a chat deleted
mid-turn came back in the sidebar, because the worker saved the session at the
end of the turn, and Session.save() both rewrote the sidecar and cleared the
deleted-session tombstone. A deleted conversation now stays deleted, and the
delete route stops the turn that is still running for it.
"""

import json
import re
from collections import OrderedDict
from pathlib import Path

import pytest

ROUTES_PY = (Path(__file__).resolve().parents[1] / "api" / "routes.py").read_text(encoding="utf-8")


@pytest.fixture
def temp_session_dir(tmp_path, monkeypatch):
    import api.models as models

    sd = tmp_path / "sessions"
    sd.mkdir()
    monkeypatch.setattr(models, "SESSION_DIR", sd)
    monkeypatch.setattr(models, "SESSIONS", OrderedDict())
    return sd


def _session(sid="deleted_mid_turn"):
    from api.models import Session

    return Session(
        session_id=sid,
        title="Rooktest",
        workspace="",
        messages=[
            {"role": "user", "content": "Answer with OK"},
            {"role": "assistant", "content": "OK"},
        ],
    )


def test_a_late_save_does_not_bring_a_deleted_session_back(temp_session_dir):
    import api.models as models

    s = _session()
    models._record_webui_deleted_session_tombstone(s.session_id)
    s.save()

    assert not (temp_session_dir / f"{s.session_id}.json").exists()
    assert s.session_id in models._load_webui_deleted_session_tombstone()
    index = temp_session_dir / "_index.json"
    if index.exists():
        rows = json.loads(index.read_text(encoding="utf-8"))
        assert all(r.get("session_id") != s.session_id for r in rows if isinstance(r, dict))


def test_an_ordinary_session_still_saves(temp_session_dir):
    s = _session("still_alive")
    s.save()
    assert (temp_session_dir / "still_alive.json").exists()


def test_new_session_with_a_tombstoned_id_is_not_blocked(temp_session_dir):
    """Creating or importing clears the tombstone first, so a deliberate new
    session with a previously deleted id is written as before."""
    import api.models as models

    s = _session("reused_id")
    models._record_webui_deleted_session_tombstone(s.session_id)
    models._clear_webui_deleted_session_tombstone(s.session_id)
    s.save()
    assert (temp_session_dir / "reused_id.json").exists()


def test_delete_route_stops_the_running_turn_after_the_tombstone():
    start = ROUTES_PY.index('if parsed.path == "/api/session/delete":')
    block = ROUTES_PY[start:ROUTES_PY.index("_evict_session_agent(sid)", start)]
    assert 'running_stream_id = getattr(_deleted_meta, "active_stream_id", None) or None' in block
    tombstone_at = block.index("_record_webui_deleted_session_tombstone(sid)")
    cancel_at = block.index("cancel_stream(running_stream_id)")
    # The tombstone is recorded first, so the cancelled worker's own final
    # save is already a no-op when it runs.
    assert tombstone_at < cancel_at
    assert re.search(r"with STREAMS_LOCK:\s*\n\s*_still_running = running_stream_id in STREAMS", block)
