"""Repeated status reads must not repeatedly parse an unchanged transcript."""
import json
from types import SimpleNamespace

import pytest
import api.models as models


@pytest.fixture
def disk(tmp_path, monkeypatch):
    monkeypatch.setattr(models, 'SESSION_DIR', tmp_path)
    monkeypatch.setattr(models, '_lookup_index_message_count', lambda sid: 2)
    path = tmp_path / 'freshness.json'
    def write(stamp=1):
        data = dict(session_id='freshness', title='T', created_at=1, updated_at=stamp,
                    workspace=str(tmp_path), model='test', compression_anchor_summary='x' * 1100000,
                    message_count=2, anchor_activity_scenes={'one': {'updated_at': stamp}},
                    messages=[{'role':'user','content':'hi'}, {'role':'assistant','content':'hello'}])
        path.write_text(json.dumps(data))
    write()
    return path, write


def cached(stamp=1):
    return SimpleNamespace(session_id='freshness', messages=[{}, {}], active_stream_id=None,
                           pending_user_message=None, anchor_activity_scenes={'one': {'updated_at':stamp}})


def test_unchanged_large_sidecar_is_parsed_once(disk, monkeypatch):
    calls = []
    original = models.Session.load_metadata_only
    def load(sid):
        calls.append(sid)
        return original(sid)
    monkeypatch.setattr(models.Session, 'load_metadata_only', load)
    value = cached()
    assert not models._cached_session_lags_disk(value)
    assert not models._cached_session_lags_disk(value)
    assert not models._cached_session_lags_disk(value)
    assert len(calls) == 1


def test_disk_change_invalidates_facts(disk):
    _, write = disk
    value = cached()
    assert not models._cached_session_lags_disk(value)
    write(stamp=2)
    assert models._cached_session_lags_disk(value)


def test_local_scene_mutation_is_still_compared(disk):
    value = cached()
    assert not models._cached_session_lags_disk(value)
    value.anchor_activity_scenes = {}
    assert models._cached_session_lags_disk(value)


def test_deleted_file_does_not_reuse_facts(disk):
    path, _ = disk
    value = cached()
    assert not models._cached_session_lags_disk(value)
    path.unlink()
    value.anchor_activity_scenes = {}
    assert not models._cached_session_lags_disk(value)


def test_same_session_id_in_another_store_is_not_a_cache_hit(disk, tmp_path, monkeypatch):
    path, _ = disk
    assert not models._cached_session_lags_disk(cached())
    other = tmp_path / 'other-profile'
    other.mkdir()
    data = json.loads(path.read_text())
    data['anchor_activity_scenes']['one']['updated_at'] = 9
    (other / path.name).write_text(json.dumps(data))
    monkeypatch.setattr(models, 'SESSION_DIR', other)
    assert models._cached_session_lags_disk(cached())


def test_replacement_during_read_is_not_cached(disk, monkeypatch):
    _, write = disk
    original = models.Session.load_metadata_only
    calls = []
    def load(sid):
        value = original(sid)
        calls.append(sid)
        if len(calls) == 1:
            write(stamp=2)
        return value
    monkeypatch.setattr(models.Session, 'load_metadata_only', load)
    assert not models._cached_session_lags_disk(cached())
    assert models._cached_session_lags_disk(cached())
    assert len(calls) == 2


def test_facts_cache_is_bounded(disk, monkeypatch):
    path, _ = disk
    monkeypatch.setattr(models, '_SESSION_FRESHNESS_FACTS_MAX', 2)
    models._SESSION_FRESHNESS_FACTS.clear()
    for sid in ('one', 'two', 'three'):
        data = json.loads(path.read_text())
        data['session_id'] = sid
        (path.parent / (sid + '.json')).write_text(json.dumps(data))
        assert models._session_disk_freshness_facts(sid) is not None
    assert len(models._SESSION_FRESHNESS_FACTS) == 2
    assert str((path.parent / 'one.json').absolute()) not in models._SESSION_FRESHNESS_FACTS
