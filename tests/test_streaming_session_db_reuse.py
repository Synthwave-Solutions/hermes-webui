"""Cached agents own their database handle until eviction or credential self-heal."""
from pathlib import Path
from types import SimpleNamespace
import sqlite3

import pytest


class Database:
    def __init__(self, path):
        self.db_path = path
        self._conn = sqlite3.connect(path)
        self._read_conns_closed = False
        self.generation_checks = 0
        self._identity = path.stat().st_ino

    def _halt_if_db_generation_changed(self):
        self.generation_checks += 1
        if self.db_path.stat().st_ino != self._identity:
            raise RuntimeError('database replaced')

    def close(self):
        self._read_conns_closed = True
        self._conn.close()
        self._conn = None


def test_same_profile_turn_reuses_open_database(tmp_path, monkeypatch):
    from api import streaming
    import sys
    db = Database(tmp_path / 'state.db')
    agent = SimpleNamespace(_session_db=db)
    monkeypatch.setitem(sys.modules, 'hermes_state', SimpleNamespace(
        SessionDB=lambda **kwargs: pytest.fail('cached turn reopened database')))
    try:
        assert streaming._build_session_db_for_stream(db.db_path, cached_agent=agent) is db
        assert db.generation_checks == 1
        assert db._conn.execute('SELECT 1').fetchone() == (1,)
    finally:
        db.close()


@pytest.mark.parametrize('case', ['profile_change', 'closed', 'missing', 'legacy', 'readonly'])
def test_only_healthy_same_profile_handles_are_reused(tmp_path, monkeypatch, case):
    from api import streaming
    import sys
    old = Database(tmp_path / 'first.db')
    requested = tmp_path / 'second.db' if case == 'profile_change' else old.db_path
    if case == 'closed':
        old.close()
    if case == 'readonly':
        old.read_only = True
    if case == 'legacy':
        old._halt_if_db_generation_changed = None
    agent = SimpleNamespace(_session_db=None if case == 'missing' else old)
    created = []
    def create(db_path):
        db = Database(Path(db_path))
        created.append(db)
        return db
    monkeypatch.setitem(sys.modules, 'hermes_state', SimpleNamespace(SessionDB=create))
    try:
        result = streaming._build_session_db_for_stream(requested, cached_agent=agent)
        assert result is created[0]
        assert result.db_path == requested
        assert old.generation_checks == 0
    finally:
        if old._conn is not None:
            old.close()
        for db in created:
            db.close()


def test_replaced_generation_fails_closed(tmp_path, monkeypatch):
    from api import streaming
    import sys
    db = Database(tmp_path / 'state.db')
    replacement = tmp_path / 'replacement.db'
    replacement.touch()
    replacement.replace(db.db_path)
    monkeypatch.setitem(sys.modules, 'hermes_state', SimpleNamespace(
        SessionDB=lambda **kwargs: pytest.fail('must not bypass generation guard')))
    try:
        with pytest.raises(RuntimeError, match='database replaced'):
            streaming._build_session_db_for_stream(db.db_path, cached_agent=SimpleNamespace(_session_db=db))
    finally:
        db.close()
