"""Gateway terminal failures retain authoritative ownership in live/replay SSE."""
import io
import queue
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest


@pytest.mark.parametrize('failure', [RuntimeError('Synthetic terminal failure'),
    HTTPError('http://fixture.invalid', 403, 'Forbidden', {}, io.BytesIO(b'Fixture denied'))])
def test_gateway_failure_stamps_session_before_journal_and_delivery(monkeypatch, tmp_path, failure):
    from api import gateway_chat as gateway

    events = queue.Queue()
    journal = []
    sid, stream = 'synthetic-session', 'synthetic-stream'
    monkeypatch.setattr(gateway, 'STREAMS', {stream: events})
    monkeypatch.setattr(gateway, 'RunJournalWriter', lambda *args: SimpleNamespace(
        append_sse_event=lambda event, data: journal.append((event, dict(data)))))
    monkeypatch.setattr(gateway, 'register_active_run', lambda *a, **k: None)
    monkeypatch.setattr(gateway, 'unregister_active_run', lambda *a, **k: None)
    monkeypatch.setattr(gateway, 'unregister_stream_owner', lambda *a, **k: None)

    def fail(*args):
        raise failure

    monkeypatch.setattr(gateway, 'get_session', fail)
    gateway._run_gateway_chat_streaming(sid, 'Synthetic request', 'fixture-model',
                                       str(tmp_path), stream)
    event, data = events.get_nowait()
    assert event == 'apperror'
    assert data['session_id'] == sid
    assert journal == [('apperror', data)]
    assert stream not in gateway.STREAMS


@pytest.mark.parametrize("stale", [False, True])
@pytest.mark.parametrize("raw_secret", [False, True])
def test_gateway_failure_is_saved_before_delivery(monkeypatch, tmp_path, stale, raw_secret):
    from api import gateway_chat as gateway, streaming

    sid, stream = 'synthetic-persist-session', 'synthetic-persist-stream'
    events, saved, journal = queue.Queue(), [], []
    session = SimpleNamespace(session_id=sid, active_stream_id='newer-stream' if stale else stream, messages=[],
        context_messages=[], pending_user_message='Synthetic request',
        pending_started_at=1.0, pending_user_source='webui', pending_attachments=[])
    session.save = lambda: saved.append([dict(row) for row in session.messages])
    monkeypatch.setattr(gateway, 'STREAMS', {stream: events})
    monkeypatch.setattr(gateway, 'RunJournalWriter', lambda *a: SimpleNamespace(
        append_sse_event=lambda event, data: journal.append((event, dict(data)))))
    monkeypatch.setattr(gateway, 'get_session', lambda *a: session)
    monkeypatch.setattr(gateway, 'register_active_run', lambda *a, **k: None)
    monkeypatch.setattr(gateway, 'unregister_active_run', lambda *a, **k: None)
    monkeypatch.setattr(gateway, 'unregister_stream_owner', lambda *a, **k: None)
    monkeypatch.setattr(streaming, '_session_payload_with_full_messages',
        lambda s, **k: {'session_id': s.session_id, 'messages': s.messages})

    secret = 'sk-SYNTHETIC_REDACTION_SENTINEL_1234567890'
    if raw_secret:
        monkeypatch.setattr(gateway, '_gateway_http_error_event', lambda *a, **k: {
            'message': 'Synthetic terminal failure ' + secret, 'hint': secret})

    def fail(*a, **k):
        if raw_secret:
            raise HTTPError('http://fixture.invalid', 403, 'Forbidden', {}, io.BytesIO(b''))
        raise RuntimeError('Synthetic terminal failure')

    monkeypatch.setattr(gateway, '_gateway_reasoning_effort_for_request', fail)
    gateway._run_gateway_chat_streaming(sid, 'Synthetic request', 'fixture-model',
                                       str(tmp_path), stream)
    if stale:
        assert events.empty()
        assert not saved
        assert session.active_stream_id == 'newer-stream'
        return
    event, data = events.get_nowait()
    assert event == 'apperror'
    assert saved
    assert [row['role'] for row in saved[0]] == ['user', 'assistant']
    assert saved[0][-1]['_error'] is True
    assert saved[0][-1]['_turnDuration'] > 0
    assert 'Synthetic terminal failure' in saved[0][-1]['content']
    assert data['session']['messages'] == saved[0]
    if raw_secret:
        assert secret not in str(saved)
        assert secret not in str(data)
        assert secret not in str(journal)
    assert session.active_stream_id is None
    assert session.pending_user_message is None
