"""Status follows real worker and profile-ledger truth through final writeback."""
import sqlite3
import time

import pytest

from api import config, profiles, routes, run_journal, session_ops
from api.models import Session
from tools import async_delegation


@pytest.fixture
def status_session(tmp_path, monkeypatch):
    session = Session(session_id='owned-session', profile='owner-profile',
                      bot_participants=['bot-profile'], workspace=tmp_path)
    monkeypatch.setattr(session_ops, 'get_session', lambda sid: session)
    monkeypatch.setattr(routes, '_session_attention_summary', lambda sid: None)
    monkeypatch.setattr(run_journal, '_default_session_dir', lambda: tmp_path / 'journals')
    monkeypatch.setattr(config, 'STREAMS', {})
    monkeypatch.setattr(config, 'ACTIVE_RUNS', {})
    monkeypatch.setattr(async_delegation, '_records', {})
    monkeypatch.setattr(profiles, 'get_hermes_home_for_profile', lambda name: tmp_path / name)
    return session


def seed_ledger(home, sid, delegation_id):
    home.mkdir()
    with sqlite3.connect(home / 'state.db') as conn:
        async_delegation._initialize_schema(conn)
        conn.execute('''INSERT INTO async_delegations
            (delegation_id, origin_session, origin_ui_session_id, parent_session_id,
             state, dispatched_at, updated_at, delivery_state)
            VALUES (?, ?, ?, ?, 'completed', 1, 2, 'pending')''',
            (delegation_id, sid, sid, sid))


def test_idle_parent_keeps_bot_result_pending_in_its_own_profile(status_session, tmp_path, monkeypatch):
    seed_ledger(tmp_path / 'bot-profile', status_session.session_id, 'queued-child')
    seed_ledger(tmp_path / 'unrelated-profile', 'sibling', 'other-child')
    # Simulate a request currently bound to an unrelated profile. Status must
    # inspect the stored conversation and its bots, without changing this home.
    monkeypatch.setattr(async_delegation, '_db_path', lambda: tmp_path / 'unrelated-profile' / 'state.db')
    run_journal.append_run_event(status_session.session_id, 'parent-run', 'done', {})
    status = session_ops.session_status(status_session.session_id)
    assert status['agent_running'] is False
    assert status['progress']['status'] == 'completed'
    assert status['delegation_pending'] is True
    assert status['delegation_pending_count'] == 1
    assert async_delegation._db_path() == tmp_path / 'unrelated-profile' / 'state.db'
    with sqlite3.connect(tmp_path / 'bot-profile' / 'state.db') as conn:
        conn.execute("UPDATE async_delegations SET delivery_state='delivered'")
    assert session_ops.session_status(status_session.session_id)['delegation_pending'] is False


def test_unreadable_bot_ledger_is_unknown_not_completed(status_session, tmp_path):
    home = tmp_path / 'bot-profile'
    home.mkdir()
    (home / 'state.db').write_bytes(b'corrupt')
    status = session_ops.session_status(status_session.session_id)
    assert status['delegation_pending'] is None
    assert status['delegation_pending_count'] is None


def test_final_writeback_gap_uses_owned_live_worker_then_durable_done(status_session):
    sid = status_session.session_id
    run_journal.append_run_event(sid, 'finalizing-run', 'token', {'text': 'answer'})
    # The real worker clears active_stream_id before saving final model/session
    # data and publishing done. This must still project running, not lost-worker.
    assert status_session.active_stream_id is None
    config.STREAMS['finalizing-run'] = object()
    config.ACTIVE_RUNS['finalizing-run'] = {
        'stream_id': 'finalizing-run', 'session_id': sid, 'started_at': time.time(),
    }
    status = session_ops.session_status(sid)
    assert status['agent_running'] is True
    assert status['active_stream_id'] == 'finalizing-run'
    assert status['progress']['status'] == 'running'
    run_journal.append_run_event(sid, 'finalizing-run', 'done', {'terminal_state': 'completed'})
    run_journal.append_run_event(sid, 'finalizing-run', 'stream_end', {'terminal_state': 'completed'})
    config.STREAMS.clear()
    config.ACTIVE_RUNS.clear()
    status = session_ops.session_status(sid)
    assert status['agent_running'] is False
    assert status['active_stream_id'] is None
    assert status['progress']['status'] == 'completed'


def test_other_session_or_stale_worker_cannot_resurrect_stream(status_session):
    config.STREAMS['other-run'] = object()
    config.ACTIVE_RUNS.update({
        'other-run': {'session_id': 'sibling', 'stream_id': 'other-run'},
        'stale-run': {'session_id': status_session.session_id, 'stream_id': 'stale-run'},
    })
    status = session_ops.session_status(status_session.session_id)
    assert status['agent_running'] is False
    assert status['active_stream_id'] is None
