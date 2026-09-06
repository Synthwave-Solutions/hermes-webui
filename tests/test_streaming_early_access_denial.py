import queue


def test_worker_emits_access_error_when_refused_before_provider_resolution(monkeypatch, tmp_path):
    from api import streaming

    stream_id = 'qa-early-denial'
    events = queue.Queue()
    monkeypatch.setattr(streaming, 'STREAMS', {stream_id: events})
    monkeypatch.setattr(streaming, 'RunJournalWriter', lambda *a: None)
    monkeypatch.setattr(streaming, 'append_turn_journal_event_for_stream', lambda *a, **kw: None)
    monkeypatch.setattr(streaming, '_report_capacity_incident', lambda *a, **kw: None)

    def revoked(*args, **kwargs):
        raise PermissionError('Bot access was revoked')

    monkeypatch.setattr(streaming, 'get_session', revoked)
    streaming._run_agent_streaming(
        'qa-private-session', 'Synthetic denied request', 'qa-model', str(tmp_path),
        stream_id, sender_email='qa@example.test',
        sender_identity={'email': 'qa@example.test'},
    )
    rows = []
    while not events.empty():
        rows.append(events.get_nowait())
    assert any('governance_denied' in str(row) and 'Bot access was revoked' in str(row) for row in rows)
    assert stream_id not in streaming.STREAMS
    assert stream_id not in streaming.CANCEL_FLAGS
