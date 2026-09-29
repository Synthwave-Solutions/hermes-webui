"""Clear must survive context hydration, disk reload and startup recovery."""
from __future__ import annotations

import json
from types import SimpleNamespace

from tests.test_session_truncate_keep_count_validation import _JSONHandler, _make_session


def _clear(monkeypatch, sid):
    import api.routes as routes
    monkeypatch.setattr(routes, '_check_csrf', lambda handler: True)
    handler = _JSONHandler(json.dumps({'session_id': sid}).encode())
    routes.handle_post(handler, SimpleNamespace(path='/api/session/clear'))
    return handler


def test_clear_blocks_state_replay_and_pre_clear_backup_recovery(monkeypatch, tmp_path):
    import api.models as models
    from api.session_recovery import inspect_session_recovery_status
    Session = _make_session(monkeypatch, tmp_path, 'clear-replay')
    before = Session.load('clear-replay')
    old_messages = list(before.messages)
    response = _clear(monkeypatch, before.session_id)
    assert response.status == 200, response.payload()
    models.SESSIONS.clear()
    after = Session.load(before.session_id)
    assert after.messages == []
    assert after.context_messages == []
    assert after.clear_generation
    assert after.truncation_watermark == after.truncation_boundary == 0.0
    assert models.merge_session_messages_append_only(
        after.messages, old_messages, truncation_watermark=after.truncation_watermark,
        truncation_boundary=after.truncation_boundary) == []
    status = inspect_session_recovery_status(after.path)
    assert status['recommend'] == 'no_action'
    assert status['intentional_clear_truncate'] is True
    after.save()
    reloaded = Session.load(before.session_id)
    assert reloaded.clear_generation == after.clear_generation
    assert inspect_session_recovery_status(reloaded.path)['recommend'] == 'no_action'


def test_clear_resets_stale_pending_and_compressed_context(monkeypatch, tmp_path):
    Session = _make_session(monkeypatch, tmp_path, 'clear-compressed')
    s = Session.load('clear-compressed')
    s.context_engine_state = {'stale-context': 'old message'}
    s.compression_anchor_summary = 'old message'
    s.compression_anchor_details = {'old': True}
    s.active_stream_id = 'dead-stream'
    s.pending_user_message = 'old pending message'
    s.pending_attachments = ['old-file']
    s.pending_started_at = 1.0
    s.pending_user_source = 'old-source'
    s.save()
    response = _clear(monkeypatch, s.session_id)
    assert response.status == 200
    after = Session.load(s.session_id)
    assert after.messages == after.context_messages == after.pending_attachments == []
    assert after.context_engine_state == after.compression_anchor_details == {}
    assert after.compression_anchor_summary is None
    assert after.active_stream_id is after.pending_user_message is after.pending_started_at is after.pending_user_source is None


def test_clear_refuses_live_turn_without_destroying_history(monkeypatch, tmp_path):
    import api.session_ops as ops
    Session = _make_session(monkeypatch, tmp_path, 'clear-active')
    before = Session.load('clear-active')
    monkeypatch.setattr(ops, '_live_active_stream_id', lambda session: 'live-stream')
    response = _clear(monkeypatch, before.session_id)
    assert response.status == 409
    assert Session.load(before.session_id).messages == before.messages
