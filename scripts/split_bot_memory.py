#!/usr/bin/env python3
"""Offline, resumable split of owner banks by recorded bot provenance.

Stop WebUI and memory workers for --apply. Original databases remain archived;
only complete, same-bot provenance is copied for derived records.
"""
import argparse
from contextlib import closing
from collections import defaultdict
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['MNEMOSYNE_NO_EMBEDDINGS'] = '1'
from api import memory_banks as banks, personal_mnemosyne as personal
from api import personal_episodes as episodes, personal_lifecycle as lifecycle
from scripts.consolidate_personal_memory import database


def rows(db, table):
    if not lifecycle.exists(db, table):
        return []
    return [dict(r) for r in db.execute('SELECT * FROM '+table)]


def insert(db, table, values):
    columns = {r[1] for r in db.execute('PRAGMA table_info('+table+')')}
    for row in values:
        names = [name for name in row if name in columns]
        db.execute('INSERT OR IGNORE INTO '+table+' ('+','.join(names)+') VALUES ('+
                   ','.join('?' for _ in names)+')', [row[name] for name in names])


def split(path, apply=False):
    with closing(personal._read(path)) as source:
        if banks.archived(source) or banks.BOT_BANK.fullmatch(path.stem):
            return dict(originals=0, banks=0, skipped=True)
        working = rows(source, 'working_memory')
        groups = defaultdict(list)
        for row in working:
            meta = json.loads(row['metadata_json'] or '{}')
            if meta.get('kind') == 'consolidated':
                continue
            bot = banks.bot_name(meta.get('bot'))
            meta['bot'] = bot
            meta['company_source_id'] = banks.source_reference(path,row['id'],meta)
            row['metadata_json'] = json.dumps(meta)
            groups[bot].append(row)
        # Empty historical banks can still contain durable deletion receipts.
        if not groups:
            groups['default'] = []
        tables = {name: rows(source,name) for name in (
            'personal_facts','personal_evidence','personal_sources','personal_episodes',
            'episodic_memory','personal_lifecycle','personal_graph_sources',
            'personal_graph_edges','triples','webui_history_imports')}
    result = dict(originals=sum(map(len,groups.values())),banks=len(groups),skipped=False)
    if not apply:
        return result
    with database(path) as source_mem:
        if banks.archived(source_mem.conn):
            return dict(originals=0,banks=0,skipped=True)
        # Keep the source lock for the entire split. No deletion or overwrite of
        # original banks; a failed split is safely retryable before activation.
        for bot, originals in groups.items():
            target = path.with_name(banks.key(bot,path.stem)+'.db')
            ids = {r['id'] for r in originals}
            evidence = defaultdict(list)
            for row in tables['personal_evidence']:
                evidence[row['topic']].append(row)
            topics = {r['topic'] for r in tables['personal_facts']
                      if evidence[r['topic']] and all(e['source_id'] in ids for e in evidence[r['topic']])}
            facts = [dict(r) for r in tables['personal_facts'] if r['topic'] in topics]
            # Retain owner correction/deletion blocks even when their old
            # evidence spans bots. Do not publish that mixed content to a bot.
            for row in tables['personal_facts']:
                if row['topic'] not in topics and (row['manual'] or row['deleted']) and any(e['source_id'] in ids for e in evidence[row['topic']]):
                    facts.append(dict(row,manual=1,deleted=1))
            retained_topics = {r['topic'] for r in facts}
            reprocess = {r['source_id'] for r in tables['personal_evidence']
                         if r['topic'] not in retained_topics and r['source_id'] in ids}
            fact_ids = {r['memory_id'] for r in facts if not r['deleted']}
            ep_rows = [r for r in tables['personal_episodes']
                       if all(mid in ids for mid,_ in json.loads(r['evidence']))]
            ep_ids = {r['memory_id'] for r in ep_rows if r['memory_id'] and not r['deleted']}
            parent_ids = fact_ids | ep_ids
            graph_edges = [r for r in tables['personal_graph_edges'] if r['memory_id'] in parent_ids]
            triple_ids = {r['triple_id'] for r in graph_edges}
            with database(target) as mem:
                episodes.schema(mem.conn)
                lifecycle.schema(mem.conn)
                mem.conn.execute('CREATE TABLE IF NOT EXISTS webui_history_imports (receipt TEXT PRIMARY KEY,memory_id TEXT NOT NULL,imported_at TEXT NOT NULL)')
                insert(mem.conn,'working_memory',originals+[r for r in working if r['id'] in fact_ids])
                insert(mem.conn,'personal_facts',facts)
                insert(mem.conn,'personal_evidence',[r for r in tables['personal_evidence'] if r['topic'] in retained_topics and r['source_id'] in ids])
                insert(mem.conn,'personal_sources',[r for r in tables['personal_sources'] if r['source_id'] in ids and r['source_id'] not in reprocess])
                insert(mem.conn,'episodic_memory',[r for r in tables['episodic_memory'] if r['id'] in ep_ids])
                insert(mem.conn,'personal_episodes',ep_rows)
                insert(mem.conn,'personal_lifecycle',[r for r in tables['personal_lifecycle'] if r['memory_id'] in ep_ids])
                insert(mem.conn,'triples',[r for r in tables['triples'] if r['id'] in triple_ids])
                insert(mem.conn,'personal_graph_edges',graph_edges)
                insert(mem.conn,'personal_graph_sources',[r for r in tables['personal_graph_sources'] if r['memory_id'] in parent_ids])
                # All receipts are safe opaque tombstones. Copying them to each
                # bot prevents deleted imports resurfacing after this split.
                insert(mem.conn,'webui_history_imports',tables['webui_history_imports'])
                mem.conn.commit()
                copied = {r[0] for r in mem.conn.execute('SELECT id FROM working_memory')}
                if not ids <= copied:
                    raise RuntimeError('Incomplete bot memory split')
                episodes.prune(mem)
                lifecycle.prune(mem.conn)
        source_mem.conn.execute('CREATE TABLE IF NOT EXISTS bot_bank_migration (complete INTEGER NOT NULL)')
        source_mem.conn.execute('INSERT INTO bot_bank_migration VALUES (1)')
        source_mem.conn.commit()
    return result


def run(apply=False):
    total = dict(originals=0,banks=0,archived=0)
    for path in banks.active_paths():
        result = split(path,apply)
        if not result['skipped']:
            total['originals'] += result['originals']
            total['banks'] += result['banks']
            total['archived'] += 1
    print(json.dumps(dict(total,applied=apply)),flush=True)
    return total


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    run(args.apply)
