"""Read legacy triples and current BEAM entity facts through one bank connection.

No migration, extraction, cross-bank joins or memory-to-memory graph_edges.
Unknown timestamps stay unknown. Source-qualified IDs prevent collisions.
"""

SOURCES = ('triples', 'facts', 'memoria_kg')


def _union(store, con):
    selects = []
    for table in SOURCES:
        if table not in store._tables(con):
            continue
        cols = store._columns(con, table)
        key = 'fact_id' if table == 'facts' else 'id'
        if not {'subject', 'predicate', 'object', key} <= cols:
            continue

        def pick(*names, default='NULL', cols=cols):
            available = [name for name in names if name in cols]
            return ('COALESCE(' + ','.join(available) + ')') if len(available) > 1 else (available[0] if available else default)

        identifier = key if table == 'triples' else f"'{table}:' || {key}"
        source = pick('source', default=f"'{table}'")
        selects.append(f'''SELECT {identifier} AS id, subject, predicate, object,
            {pick('valid_from','timestamp')} AS valid_from,
            {pick('valid_until')} AS valid_until, {source} AS source,
            {pick('confidence')} AS confidence,
            {pick('created_at','timestamp','valid_from')} AS created_at,
            {pick('session_id')} AS session_id, '{table}' AS source_table
            FROM {table} WHERE trim(COALESCE(subject,''))<>''
              AND trim(COALESCE(predicate,''))<>'' AND trim(COALESCE(object,''))<>'' ''')
    return ' UNION ALL '.join(selects)


def _rows(store, *, q='', subject='', predicate='', object_='', limit=200, session=None, day=None):
    limit = max(1, min(int(limit or 200), 1000))
    with store.connect() as con:
        union = _union(store, con)
        if not union:
            return []
        where, params = [], []
        if q:
            where.append("(COALESCE(subject,'') || ' ' || COALESCE(predicate,'') || ' ' || COALESCE(object,'') || ' ' || COALESCE(source,'')) REGEXP ?")
            params.append(store._prefix_pattern(q))
        for column, value in (('subject',subject), ('predicate',predicate), ('object',object_)):
            if value:
                where.append(f'{column} REGEXP ?')
                params.append(store._prefix_pattern(value))
        if session is not None:
            where.append('(session_id=? OR source=?)')
            params.extend([session,session])
        if day is not None:
            where.append('substr(COALESCE(created_at,valid_from,\'\'),1,10)=?')
            params.append(day)
        clause = ' WHERE ' + ' AND '.join(where) if where else ''
        # Each stored assertion is evidence with its own provenance; equal labels
        # from distinct sessions are not silently collapsed into a new fact.
        return [dict(r) for r in con.execute(
            f'SELECT * FROM ({union}){clause} ORDER BY created_at DESC,id LIMIT ?',
            [*params,limit])]


def install(store):
    if getattr(store, '_modern_graph_sources', False):
        return
    original_stats, original_session, original_digest = store.stats, store.session_detail, store.today_digest

    def triples(self, q='', subject='', predicate='', object_='', limit=200):
        return _rows(self, q=q, subject=subject, predicate=predicate, object_=object_, limit=limit)

    def stats(self):
        data = original_stats(self)
        with self.connect() as con:
            union = _union(self, con)
            counts = {table:0 for table in SOURCES if table in self._tables(con)}
            if union:
                counts.update(dict(con.execute(f'SELECT source_table, count(*) FROM ({union}) GROUP BY source_table')))
        data['graph_sources'] = counts
        data['counts']['triples'] = sum(counts.values())
        return data

    def session_detail(self, session_id, limit=200):
        data = original_session(self, session_id, limit=limit)
        triples = _rows(self, session=str(session_id).strip(), limit=max(1,min(int(limit or 200),500)))
        data['triples'], data['counts']['triples'] = triples, len(triples)
        events = [e for e in data['events'] if e['type'] != 'triple']
        events += [{'type':'triple', 'timestamp':t['created_at'] or t['valid_from'] or '',
                    'title':t['predicate'], 'preview':f"{t['subject']} → {t['object']}", 'item':t} for t in triples]
        data['counts']['events'] = sum(data['counts'][k] for k in ('memories','triples','consolidations'))
        data['events'] = sorted(events,key=lambda e:e.get('timestamp') or '',reverse=True)[:max(1,min(int(limit or 200),500))]
        return data

    def today_digest(self, day='', limit=80):
        data = original_digest(self,day=day,limit=limit)
        triples = _rows(self, day=data['day'], limit=max(1,min(int(limit or 80),500)))
        data['counts']['triples_added'] = len(triples)
        data['triples_added'] = triples
        return data

    store.triples, store.stats = triples, stats
    store.session_detail, store.today_digest = session_detail, today_digest
    store._modern_graph_sources = True
