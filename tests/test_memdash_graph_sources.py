"""Modern BEAM facts must reach the graph without migrating or merging banks."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / 'fixtures' / 'memdash'))
import memdash_harness as H
from api.third_party import mnemosyne_dashboard as md


@pytest.fixture
def bank(tmp_path):
    path = H.make_bank(tmp_path / 'one.db', owner='one')
    other = H.make_bank(tmp_path / 'other.db', owner='PRIVATE-CANARY')
    with sqlite3.connect(path) as con:
        con.executescript('''
          DELETE FROM triples;
          CREATE TABLE facts(fact_id TEXT PRIMARY KEY, session_id TEXT,
            subject TEXT, predicate TEXT, object TEXT, timestamp TEXT,
            source_msg_id TEXT, confidence REAL, created_at TEXT);
          CREATE TABLE memoria_kg(id INTEGER PRIMARY KEY, session_id TEXT,
            subject TEXT, predicate TEXT, object TEXT, message_idx INTEGER,
            confidence REAL, source_memory_id TEXT);
          CREATE TABLE graph_edges(id INTEGER PRIMARY KEY, source TEXT, target TEXT, edge_type TEXT);
          INSERT INTO facts VALUES('f1','s1','MAX','reports_to','CFO','2026-11-01T10:00:00',
            'm1',0.9,'2026-11-01T10:00:00');
          INSERT INTO facts VALUES('f2','s2','ABC','listed_on','NYSE','2026-10-31T10:00:00',
            'm2',0.8,'2026-10-31T10:00:00');
          INSERT INTO memoria_kg VALUES(1,'s1','MAX','uses','Trading212',0,0.7,'memory1');
          INSERT INTO graph_edges VALUES(1,'memory1','memory2','related');
        ''')
    md.allow_paths([path])
    try:
        yield md.DashboardStore(path), path, other
    finally:
        md.allow_paths([])


def test_modern_facts_without_legacy_triples(bank):
    store, path, other = bank
    graph = store.graph()
    assert len(graph['edges']) == 3
    assert {n['label'] for n in graph['nodes']} == {'MAX','CFO','ABC','NYSE','Trading212'}
    assert {e['triple_id'] for e in graph['edges']} == {'facts:f1','facts:f2','memoria_kg:1'}
    assert len(store.triples(subject='MAX')) == 2
    assert len(store.triples(predicate='listed_on', object_='NYSE')) == 1
    assert store.triples(q="' OR 1=1 --") == []
    assert len(store.graph(q='MAX')['edges']) == 2
    assert len(store.graph(limit=1)['edges']) == 1
    assert len(store.global_search('MAX')['triples']) == 2
    assert store.stats()['counts']['triples'] == 3
    assert store.stats()['graph_sources'] == {'triples':0,'facts':2,'memoria_kg':1}
    assert len(store.session_detail('s1')['triples']) == 2
    assert store.today_digest(day='2026-11-01')['counts']['triples_added'] == 1
    with pytest.raises(PermissionError):
        md.DashboardStore(other).graph()
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT count(*) FROM triples').fetchone()[0] == 0
        assert con.execute('SELECT count(*) FROM facts').fetchone()[0] == 2


def test_legacy_and_modern_coexist_with_stable_ids(bank):
    store, path, _ = bank
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO triples(subject,predicate,object,valid_from,source) VALUES('MAX','owns','research','2026-11-01','manual')")
    assert len(store.graph()['edges']) == 4
    assert any(isinstance(t['id'], int) for t in store.triples())
    assert len({e['id'] for e in store.graph()['edges']}) == 4


def test_missing_optional_columns_are_not_a_fake_timestamp(tmp_path):
    path = H.make_bank(tmp_path / 'minimal.db', owner='minimal')
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE facts(fact_id TEXT,subject TEXT,predicate TEXT,object TEXT)')
        con.execute("INSERT INTO facts VALUES('minimal','A','relates_to','B')")
    md.allow_paths([path])
    try:
        store = md.DashboardStore(path)
        fact = next(t for t in store.triples() if t['id']=='facts:minimal')
        assert fact['created_at'] is None and fact['confidence'] is None
        assert fact['source'] == 'facts'
    finally:
        md.allow_paths([])
