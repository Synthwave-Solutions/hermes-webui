"""Sidebar source reclassification batches DB reads without caching authority."""
import sqlite3
from api import models, routes


def test_batch_coercion_handles_stale_sources_both_lists_and_readonly(tmp_path, monkeypatch):
    path = tmp_path / 'state.db'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT)')
        conn.executemany('INSERT INTO sessions VALUES (?,?)', [('child', ' SUBAGENT '), ('human', 'webui')])
    monkeypatch.setattr(models, '_active_state_db_path', lambda: path)
    real_connect = sqlite3.connect
    connects = []
    def connect(*args, **kwargs):
        connects.append(args)
        return real_connect(*args, **kwargs)
    monkeypatch.setattr(sqlite3, 'connect', connect)
    visible = [{'session_id': 'child', 'source_tag': 'webui', 'is_cli_session': True},
               {'session_id': 'human', 'source_tag': 'webui'},
               {'session_id': 'explicit', 'source_tag': 'subagent', 'is_cli_session': True},
               {'session_id': 'unchanged', 'read_only': True, 'is_cli_session': True},
               {'session_id': 'missing'}, None]
    references = [{'session_id': 'child', 'session_source': 'fork', 'is_cli_session': True}]
    routes._coerce_subagent_rows(visible, references)
    assert len(connects) == 1
    for row in [visible[0], visible[2], references[0]]:
        assert row['read_only'] is True and row['is_cli_session'] is False
    assert visible[1] == {'session_id': 'human', 'source_tag': 'webui'}
    assert visible[3] == {'session_id': 'unchanged', 'read_only': True, 'is_cli_session': True}
    assert visible[4] == {'session_id': 'missing'}
    # Source changes must be observed on the very next rebuild.
    with real_connect(path) as conn:
        conn.execute("UPDATE sessions SET source='subagent' WHERE id='human'")
    routes._coerce_subagent_rows([visible[1]])
    assert visible[1]['read_only'] is True


def test_large_batch_chunking_missing_database_and_unsafe_ids(tmp_path, monkeypatch):
    path = tmp_path / 'state.db'
    monkeypatch.setattr(models, '_active_state_db_path', lambda: path)
    assert routes._state_db_session_sources(['missing']) == {}
    assert not path.exists()
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT)')
        conn.executemany('INSERT INTO sessions VALUES (?,?)', [(f's{i}', 'subagent') for i in range(1200)])
    ids = [f's{i}' for i in range(1200)]
    result = routes._state_db_session_sources(ids + ids + ['../unsafe', "x' OR 1=1 --"])
    assert result == {sid: 'subagent' for sid in ids}


def test_database_error_keeps_explicit_child_protection(tmp_path, monkeypatch):
    path = tmp_path / 'broken.db'
    path.write_text('invalid SQLite')
    monkeypatch.setattr(models, '_active_state_db_path', lambda: path)
    rows = [{'session_id': 'child', 'source_tag': 'subagent'}, {'session_id': 'ordinary'}]
    routes._coerce_subagent_rows(rows)
    assert rows[0]['read_only'] is True and rows[0]['is_cli_session'] is False
    assert rows[1] == {'session_id': 'ordinary'}
