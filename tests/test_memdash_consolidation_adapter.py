"""Current derived facts must reach every existing consolidation view."""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "fixtures" / "memdash"))
import memdash_harness as H
from api.third_party import mnemosyne_dashboard as md


def test_current_facts_reach_dashboard_without_changing_bank(tmp_path):
    path = H.make_bank(tmp_path / "bank.db", owner="owner")
    with sqlite3.connect(path) as con:
        con.executescript("""
          CREATE TABLE personal_facts(topic TEXT, memory_id TEXT, category TEXT, deleted INTEGER);
          CREATE TABLE personal_evidence(topic TEXT, source_id TEXT);
          INSERT INTO personal_facts VALUES ('planning','owner-w1','preference',0),
              ('deleted','owner-w2','preference',1), ('missing','missing','profile',0);
          INSERT INTO personal_evidence VALUES ('planning','s1'),('planning','s2');
        """)
    md.allow_paths([path])
    try:
        store = md.DashboardStore(path)
        assert store.stats()["counts"]["consolidation_log"] == 2
        assert store.stats()["counts"]["personal_facts"] == 1
        rows = store.consolidations()
        assert len(rows) == 2  # legacy run plus current fact
        fact = next(row for row in rows if row["id"] == "personal:owner-w1")
        assert fact["items_consolidated"] == 2
        assert fact["summary_preview"] == "owner prefers option 1 for project planning"
        assert store.consolidations(q="option 1") == [fact]
        assert store.consolidations(q="absent") == []
        assert len(store.consolidations(limit=1)) == 1
        digest = store.today_digest(day="2026-09-11")
        assert digest["counts"]["consolidations"] == 1
        assert digest["consolidations"] == [fact]
        assert store.session_detail("s1")["consolidations"] == [fact]
        assert store.global_search("option 1")["consolidations"] == [fact]
        with sqlite3.connect(path) as con:
            assert con.execute("SELECT count(*) FROM consolidation_log").fetchone()[0] == 1
            con.execute("DELETE FROM working_memory WHERE id='owner-w1'")
        assert store.stats()["counts"]["personal_facts"] == 0
        assert len(store.consolidations()) == 1
    finally:
        md.allow_paths([])
