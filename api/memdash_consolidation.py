"""Expose current personal consolidation results through the dashboard contract.

Reads the selected bank only, through its existing read-only connection. These
are current derived facts, not invented historical consolidation runs.
"""


def results(store, q="", day="", limit=500):
    with store.connect() as con:
        if not {"personal_facts", "personal_evidence", "working_memory"} <= store._tables(con):
            return []
        pattern = store._prefix_pattern(q) if q else ""
        rows = [dict(row) for row in con.execute(
            """SELECT 'personal:' || f.memory_id AS id, w.session_id,
                   (SELECT COUNT(*) FROM personal_evidence e WHERE e.topic=f.topic) AS items_consolidated,
                   w.content AS summary_preview, w.timestamp AS created_at,
                   f.memory_id, f.category, 'current_personal_fact' AS result_kind
               FROM personal_facts f JOIN working_memory w ON w.id=f.memory_id
               WHERE f.deleted=0
                 AND (?='' OR w.session_id REGEXP ? OR w.content REGEXP ? OR w.timestamp REGEXP ?)
                 AND (?='' OR substr(w.timestamp,1,10)=?)
               ORDER BY w.timestamp DESC LIMIT ?""",
            (q, pattern, pattern, pattern, day, day, limit),
        )]
        if 'personal_episodes' in store._tables(con):
            rows += [dict(row) for row in con.execute('''
                SELECT 'episode:' || e.id AS id, e.session_id,
                    json_array_length(p.evidence) AS items_consolidated,
                    e.content AS summary_preview, e.timestamp AS created_at,
                    e.id AS memory_id, 'episode' AS category, 'current_personal_episode' AS result_kind
                FROM personal_episodes p JOIN episodic_memory e ON e.id=p.memory_id
                WHERE p.deleted=0
                    AND (?='' OR e.session_id REGEXP ? OR e.content REGEXP ? OR e.timestamp REGEXP ?)
                    AND (?='' OR substr(e.timestamp,1,10)=?)
                ORDER BY e.timestamp DESC LIMIT ?''',
                (q, pattern, pattern, pattern, day, day, limit))]
        return sorted(rows, key=lambda r: r['created_at'] or '', reverse=True)[:limit]


def install(store):
    original_consolidations = store.consolidations
    original_stats = store.stats
    original_digest = store.today_digest

    def consolidations(self, q="", limit=100):
        limit = max(1, min(int(limit or 100), 500))
        rows = original_consolidations(self, q=q, limit=limit) + results(self, q=q, limit=limit)
        return sorted(rows, key=lambda row: row.get("created_at") or "", reverse=True)[:limit]

    def stats(self):
        data = original_stats(self)
        with self.connect() as con:
            if {"personal_facts", "working_memory"} <= self._tables(con):
                count = con.execute("SELECT count(*) FROM personal_facts f JOIN working_memory w ON w.id=f.memory_id WHERE f.deleted=0").fetchone()[0]
                data["counts"]["consolidation_log"] += count
                data["counts"]["personal_facts"] = count
            if 'personal_episodes' in self._tables(con):
                count = con.execute('SELECT count(*) FROM personal_episodes p JOIN episodic_memory e ON e.id=p.memory_id WHERE p.deleted=0').fetchone()[0]
                data['counts']['consolidation_log'] += count
                data['counts']['personal_episodes'] = count
        return data

    def today_digest(self, day="", limit=80):
        data = original_digest(self, day=day, limit=limit)
        rows = results(self, day=day or self._today_key())
        data["counts"]["consolidations"] += len(rows)
        data["consolidations"] = sorted(data["consolidations"] + rows, key=lambda row: row.get("created_at") or "", reverse=True)[:max(1, min(int(limit or 80), 500))]
        return data

    store.consolidations = consolidations
    store.stats = stats
    store.today_digest = today_digest
