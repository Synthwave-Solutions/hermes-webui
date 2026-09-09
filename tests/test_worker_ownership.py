"""Only actual worker/cancellation completion permits a cached successor."""
from concurrent.futures import ThreadPoolExecutor
import queue
import threading
import time
from unittest.mock import Mock

import pytest

from api import config, routes, streaming, worker_ownership as ownership


@pytest.fixture
def token():
    value = ownership.claim('owned-test-session', 'old-stream')
    yield value
    ownership.release(value)


def test_claim_fences_the_session_until_exact_token_retires(token):
    assert ownership.live_stream(token.session_id) == 'old-stream'
    with pytest.raises(RuntimeError, match='still finishing'):
        ownership.claim(token.session_id, 'new-stream')
    ownership.release(ownership.WorkerToken(token.session_id, token.stream_id))
    assert ownership.live_stream(token.session_id) == 'old-stream'
    ownership.release(token)
    new = ownership.claim(token.session_id, 'new-stream')
    try:
        ownership.release(token)
        assert ownership.live_stream(token.session_id) == 'new-stream'
    finally:
        ownership.release(new)


@pytest.mark.parametrize('sid,stream', [('foreign', 'old-stream'), ('owned-test-session', 'new-stream')])
def test_wrong_session_or_stream_cannot_lease_cancel(token, sid, stream):
    callback = Mock()
    assert ownership.run_if_live(sid, stream, callback) is False
    callback.assert_not_called()


def test_interrupt_callback_can_outlive_worker_without_deadlock_or_new_admission(token):
    entered = threading.Event()
    resume = threading.Event()
    def callback():
        entered.set()
        assert resume.wait(3)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(ownership.run_if_live, token.session_id, token.stream_id, callback)
        try:
            assert entered.wait(3)
            ownership.release(token)  # Must return while callback remains held.
            assert ownership.live_stream(token.session_id) == token.stream_id
            with pytest.raises(RuntimeError):
                ownership.claim(token.session_id, 'next')
            assert ownership.run_if_live(token.session_id, token.stream_id, Mock()) is False
        finally:
            resume.set()
        assert future.result(timeout=3) is True
    assert ownership.live_stream(token.session_id) is None


def test_callback_exception_does_not_leak_its_lease(token):
    with pytest.raises(ValueError, match='test callback'):
        ownership.run_if_live(token.session_id, token.stream_id,
                              Mock(side_effect=ValueError('test callback')))
    assert ownership.live_stream(token.session_id) == token.stream_id
    ownership.release(token)
    assert ownership.live_stream(token.session_id) is None


def test_deferred_wakeup_runs_once_after_last_cancel_lease_and_can_claim_successor():
    entered, resume = threading.Event(), threading.Event()
    drained = []
    sid = 'deferred-retirement-session'
    def drain():
        assert ownership.live_stream(sid) is None
        new = ownership.claim(sid, 'deferred-next')
        drained.append(new.stream_id)
        ownership.release(new)
    token = ownership.claim(sid, 'old', on_retired=drain)
    def callback():
        entered.set()
        assert resume.wait(3)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(ownership.run_if_live,sid,'old',callback)
        try:
            assert entered.wait(3)
            ownership.release(token)
            assert drained == []
            assert routes._active_run_stream_for_session(sid) == 'old'
        finally:
            resume.set()
        assert future.result(timeout=3)
    ownership.release(token)
    assert drained == ['deferred-next']


def test_actual_owner_outweighs_missing_or_aged_advisory_registry(token, monkeypatch):
    monkeypatch.setattr(config, 'ACTIVE_RUNS', {})
    monkeypatch.setattr(config, 'STREAMS', {})
    assert routes._active_run_stream_for_session(token.session_id) == token.stream_id
    config.ACTIVE_RUNS[token.stream_id] = {'session_id': token.session_id, 'started_at': time.time()-999}
    assert routes._active_run_stream_for_session(token.session_id) == token.stream_id
    assert token.stream_id in config.ACTIVE_RUNS
    ownership.release(token)
    assert routes._active_run_stream_for_session(token.session_id) is None
    assert token.stream_id not in config.ACTIVE_RUNS


def test_other_thread_cannot_refresh_reset_or_close_owned_agent(token, monkeypatch):
    agent = Mock(session_id=token.session_id)
    commit = Mock()
    monkeypatch.setattr(streaming, '_lifecycle_commit_session_memory', commit)
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(streaming._refresh_cached_agent_runtime, agent, {'api_key':'new'}).result() is False
        assert pool.submit(streaming._clear_cached_agent_interrupt, agent).result() is False
        assert pool.submit(streaming._close_evicted_agent_at_session_boundary, token.session_id, agent).result() is False
    agent.clear_interrupt.assert_not_called()
    agent.switch_model.assert_not_called()
    agent.shutdown_memory_provider.assert_not_called()
    commit.assert_not_called()


def test_late_tracked_cancel_never_borrows_successor_cached_agent(monkeypatch):
    sid = 'late-cancel-session'
    token = ownership.claim(sid, 'successor-stream')
    agent = Mock(session_id=sid)
    session = Mock(session_id=sid, active_stream_id='successor-stream', messages=[])
    active = {'old-stream': {'session_id':sid, 'worker_lifetime_tracked':True}}
    maps = {'ACTIVE_RUNS':active, 'STREAMS':{}, 'CANCEL_FLAGS':{}, 'AGENT_INSTANCES':{},
            'SESSION_AGENT_CACHE':{sid:(agent,'sig')}}
    for key, value in maps.items():
        monkeypatch.setattr(config, key, value)
        if hasattr(streaming,key):
            monkeypatch.setattr(streaming,key,value)
    monkeypatch.setattr(streaming, 'get_session', lambda *_:session)
    from api import clarify
    cleared = Mock()
    monkeypatch.setattr(clarify, 'clear_pending', cleared)
    try:
        assert streaming.cancel_stream('old-stream') is True
        agent.interrupt.assert_not_called()
        cleared.assert_not_called()
        session.save.assert_not_called()
        assert session.active_stream_id == 'successor-stream'
    finally:
        ownership.release(token)


def test_tracked_cancel_interrupts_matching_worker_and_clears_its_prompt(token, monkeypatch):
    sid, stream = token.session_id, token.stream_id
    agent = Mock(session_id=sid)
    session = Mock(session_id=sid, active_stream_id=stream, messages=[],
                   pending_user_message='', pending_attachments=[], pending_started_at=None)
    maps = {'ACTIVE_RUNS':{stream:{'session_id':sid,'worker_lifetime_tracked':True}},
            'STREAMS':{stream:queue.Queue()}, 'CANCEL_FLAGS':{stream:threading.Event()},
            'AGENT_INSTANCES':{stream:agent}}
    for key,value in maps.items():
        monkeypatch.setattr(config,key,value)
        if hasattr(streaming,key):
            monkeypatch.setattr(streaming,key,value)
    monkeypatch.setattr(streaming,'get_session',lambda *_:session)
    from api import clarify
    cleared = Mock()
    monkeypatch.setattr(clarify,'clear_pending',cleared)
    assert streaming.cancel_stream(stream) is True
    agent.interrupt.assert_called_once_with('Cancelled by user')
    cleared.assert_called_once_with(sid)
    assert ownership.live_stream(sid) == stream  # Callback alone never retires worker.


def test_queue_snapshot_remains_strict_when_advisory_record_has_disappeared(monkeypatch):
    sid = 'queue-owner-session'
    token = ownership.claim(sid, 'new-stream')
    old_queue = queue.Queue()
    old_queue._worker_lifetime_tracked = True
    agent = Mock(session_id=sid)
    session = Mock(session_id=sid, active_stream_id='new-stream', messages=[])
    maps = {'ACTIVE_RUNS':{}, 'STREAMS':{'old-stream':old_queue},
            'CANCEL_FLAGS':{}, 'AGENT_INSTANCES':{'old-stream':agent}}
    for key,value in maps.items():
        monkeypatch.setattr(config,key,value)
        if hasattr(streaming,key):
            monkeypatch.setattr(streaming,key,value)
    monkeypatch.setattr(streaming,'get_session',lambda *_:session)
    from api import clarify
    cleared = Mock()
    monkeypatch.setattr(clarify,'clear_pending',cleared)
    try:
        assert streaming.cancel_stream('old-stream') is True
        agent.interrupt.assert_not_called()
        cleared.assert_not_called()
    finally:
        ownership.release(token)


def test_captured_cancel_provenance_survives_retirement_before_interrupt(monkeypatch):
    sid = 'retiring-owner-session'
    old = ownership.claim(sid, 'old-stream')
    new = []
    agent = Mock(session_id=sid)
    session = Mock(session_id=sid, active_stream_id='old-stream', messages=[])
    maps = {'ACTIVE_RUNS':{'old-stream':{'session_id':sid,'worker_lifetime_tracked':True}},
            'STREAMS':{'old-stream':queue.Queue()}, 'CANCEL_FLAGS':{},
            'AGENT_INSTANCES':{'old-stream':agent}}
    for key,value in maps.items():
        monkeypatch.setattr(config,key,value)
        if hasattr(streaming,key):
            monkeypatch.setattr(streaming,key,value)
    def retire_after_snapshot(*args,**kwargs):
        config.ACTIVE_RUNS.clear()
        ownership.release(old)
        new.append(ownership.claim(sid,'new-stream'))
        session.active_stream_id = 'new-stream'
    monkeypatch.setattr(streaming,'update_active_run',retire_after_snapshot)
    monkeypatch.setattr(streaming,'get_session',lambda *_:session)
    from api import clarify
    cleared = Mock()
    monkeypatch.setattr(clarify,'clear_pending',cleared)
    try:
        assert streaming.cancel_stream('old-stream') is True
        agent.interrupt.assert_not_called()
        cleared.assert_not_called()
    finally:
        ownership.release(old)
        for token in new:
            ownership.release(token)


def test_explicit_cache_eviction_does_not_close_a_retired_worker_with_leased_callback(token, monkeypatch):
    entered, resume = threading.Event(), threading.Event()
    agent = Mock(session_id=token.session_id)
    monkeypatch.setattr(config,'SESSION_AGENT_CACHE',{token.session_id:(agent,'sig')})
    monkeypatch.setattr(config,'ACTIVE_RUNS',{})
    from api import session_lifecycle
    commit = Mock()
    monkeypatch.setattr(session_lifecycle,'commit_session_memory',commit)
    def callback():
        entered.set()
        assert resume.wait(3)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(ownership.run_if_live,token.session_id,token.stream_id,callback)
        try:
            assert entered.wait(3)
            ownership.release(token)
            config._evict_session_agent(token.session_id)
            assert token.session_id not in config.SESSION_AGENT_CACHE
            commit.assert_not_called()
            agent._session_db.close.assert_not_called()
        finally:
            resume.set()
        assert future.result(timeout=3)


@pytest.mark.parametrize('cleanup_raises', [False, True])
def test_real_worker_releases_ownership_on_denial_and_cleanup_exception(monkeypatch, tmp_path, cleanup_raises):
    sid, stream = 'worker-refusal-session', 'worker-refusal-stream'
    monkeypatch.setattr(streaming,'STREAMS',{stream:queue.Queue()})
    monkeypatch.setattr(streaming,'RunJournalWriter',lambda *_:None)
    monkeypatch.setattr(streaming,'append_turn_journal_event_for_stream',lambda *a,**k:None)
    monkeypatch.setattr(streaming,'_report_capacity_incident',lambda *a,**k:None)
    monkeypatch.setattr(streaming,'_set_turn_session_identity',lambda *_:None)
    monkeypatch.setattr(streaming,'_reset_turn_session_identity',lambda *_:None)
    def refused(*_):
        assert ownership.live_stream(sid) == stream
        raise PermissionError('QA revoked before provider')
    monkeypatch.setattr(streaming,'get_session',refused)
    monkeypatch.setattr(streaming,'_clear_thread_env',
                        Mock(side_effect=RuntimeError('cleanup failed') if cleanup_raises else None))
    try:
        if cleanup_raises:
            with pytest.raises(RuntimeError,match='cleanup failed'):
                streaming._run_agent_streaming(sid,'QA denied','qa',str(tmp_path),stream)
        else:
            streaming._run_agent_streaming(sid,'QA denied','qa',str(tmp_path),stream)
        assert ownership.live_stream(sid) is None
    finally:
        config.unregister_active_run(stream)
