"""Snapshot must overlap preparation while remaining a barrier before the agent."""
import threading

import pytest

from tests.test_issue1897_profile_switch_agent_cache import (
    test_same_session_profile_switch_rebuilds_agent_under_new_soul_home as run_three_turns,
)


def test_worker_overlaps_snapshot_with_roster_and_joins_before_model(tmp_path, monkeypatch):
    from api import streaming, bot_delegation

    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    calls = []
    original_sanitize = streaming._sanitize_messages_for_api
    original_worker = streaming._run_agent_streaming

    def run_turn(**kwargs):
        started.clear()
        release.clear()
        finished.clear()
        return original_worker(**kwargs)

    def snapshot(profile_home, memory_home=None):
        # The post-run snapshot is synchronous and needs no preparation barrier.
        if threading.current_thread().name.startswith('persistent-snapshot-'):
            calls.append((profile_home, memory_home))
            started.set()
            assert release.wait(2), 'roster preparation did not overlap scan'
            finished.set()
        return {'memory': {}, 'skills': {}}

    def roster(*args, **kwargs):
        assert started.wait(1), 'snapshot did not start before roster preparation'
        release.set()
        return ''

    def sanitize(*args, **kwargs):
        assert finished.is_set(), 'model history prepared before snapshot joined'
        return original_sanitize(*args, **kwargs)

    monkeypatch.setattr(streaming, '_persistent_state_snapshot', snapshot)
    monkeypatch.setattr(streaming, '_run_agent_streaming', run_turn)
    monkeypatch.setattr(bot_delegation, 'awareness_prompt', roster)
    monkeypatch.setattr(streaming, '_sanitize_messages_for_api', sanitize)
    try:
        run_three_turns(tmp_path, monkeypatch)
        assert len(calls) == 3
        assert calls[0][0] == calls[1][0] != calls[2][0]
        assert not any(t.name.startswith('persistent-snapshot-') for t in threading.enumerate())
    finally:
        release.set()


@pytest.mark.parametrize("ephemeral", [False, True])
@pytest.mark.parametrize("cancelled", [False, True])
def test_preparation_failure_and_cancellation_join_snapshot(tmp_path, monkeypatch, ephemeral, cancelled):
    from api import streaming, bot_delegation

    original_worker = streaming._run_agent_streaming
    original_task = streaming._PersistentStateSnapshotTask
    started = threading.Event()
    release = threading.Event()
    joined = threading.Event()
    finished = threading.Event()

    class StopHarness(Exception):
        pass

    class TrackedTask(original_task):
        def join(self):
            joined.set()
            release.set()
            super().join()

    def snapshot(*args):
        started.set()
        assert release.wait(2), 'worker exit did not join its scan'
        finished.set()
        return {'memory': {}, 'skills': {}}

    def roster(*args, **kwargs):
        assert started.wait(1)
        if cancelled:
            for event in streaming.CANCEL_FLAGS.values():
                event.set()
        raise ValueError('preparation failed after cancellation')

    def one_turn(**kwargs):
        original_worker(**kwargs, ephemeral=ephemeral)
        assert joined.is_set() and finished.is_set()
        assert not any(t.name.startswith('persistent-snapshot-') for t in threading.enumerate())
        raise StopHarness

    monkeypatch.setattr(streaming, '_PersistentStateSnapshotTask', TrackedTask)
    monkeypatch.setattr(streaming, '_persistent_state_snapshot', snapshot)
    monkeypatch.setattr(streaming, '_run_agent_streaming', one_turn)
    monkeypatch.setattr(bot_delegation, 'awareness_prompt', roster)
    try:
        with pytest.raises(StopHarness):
            run_three_turns(tmp_path, monkeypatch)
    finally:
        release.set()


def test_snapshot_falls_back_when_thread_cannot_start(monkeypatch):
    from api import streaming

    def cannot_start(thread):
        raise RuntimeError('thread limit')

    monkeypatch.setattr(threading.Thread, 'start', cannot_start)
    monkeypatch.setattr(streaming, '_persistent_state_snapshot', lambda profile, memory: {'profile': profile, 'memory': memory})
    task = streaming._PersistentStateSnapshotTask('/profile', '/memory', 'synthetic')
    assert task.result() == {'profile': '/profile', 'memory': '/memory'}
    assert task.thread is None
    assert task.finished >= task.started
