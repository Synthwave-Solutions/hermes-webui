#!/usr/bin/env python3
"""Maintain age-based tiers and the owner-scoped knowledge graph."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['MNEMOSYNE_NO_EMBEDDINGS'] = '1'
from api.config import STATE_DIR
from api import personal_lifecycle as life, personal_episodes as episodes
from scripts.consolidate_personal_memory import database
from scripts.consolidate_personal_episodes import extract_episode


def run(extractor=extract_episode, max_banks=10):
    queue = []
    from api.memory_banks import active_paths
    for path in active_paths():
        with database(path) as mem:
            episodes.schema(mem.conn)
            episodes.prune(mem)
            life.schema(mem.conn)
            life.prune(mem.conn)
            live = life.parents(mem.conn)
            seen = dict(mem.conn.execute('SELECT * FROM personal_graph_sources'))
            pending = [p for mid,p in live.items() if seen.get(mid) != life.facts.fingerprint(p['content'])]
            aged = life.due(mem.conn)
            state = dict(mem.conn.execute('SELECT * FROM lifecycle_state'))
            attempts = dict(mem.conn.execute('SELECT * FROM personal_graph_attempts'))
            pending.sort(key=lambda p:attempts.get(p['source_id'],''))
            mem.conn.execute("INSERT OR REPLACE INTO lifecycle_state VALUES ('graph_pending',?)", (str(len(pending)),))
            mem.conn.execute("INSERT OR REPLACE INTO lifecycle_state VALUES ('degradation_pending',?)", (str(len(aged)),))
            mem.conn.commit()
            if pending or aged:
                size = int(state.get('batch_size','8'))
                chunks = [pending[i:i+size] for i in range(0, min(len(pending), size*4), size)] or [[]]
                for index, chunk in enumerate(chunks):
                    queue.append((index,state.get('last_attempt',''),path,chunk,aged[:4] if index == 0 else []))
    queue.sort(key=lambda x:x[:2])
    total = dict(graph_edges=0, graph_processed=0, degraded=0, failed_banks=0, pending_banks=len({x[2] for x in queue}))
    def process(item):
        _,_,path,batch,aged = item
        total = dict(graph_edges=0, graph_processed=0, degraded=0, failed_banks=0)
        with database(path) as mem:
            mem.conn.execute("INSERT OR REPLACE INTO lifecycle_state VALUES ('last_attempt',?)", (datetime.now(timezone.utc).isoformat(),))
            mem.conn.executemany('INSERT OR REPLACE INTO personal_graph_attempts VALUES (?,?)',[(p['source_id'],datetime.now(timezone.utc).isoformat()) for p in batch])
            mem.conn.commit()
        try:
            degradation_errors = []
            for row in aged:
                try:
                    if len(row['content']) <= row['target_chars']:
                        proposals=[dict(source_id=row['id'],content=row['content'])]
                    else:
                        proposals=extractor(life.COMPRESS_PROMPT,[dict(source_id=row['id'],content=row['content'],target_chars=row['target_chars'])],[])
                    with database(path) as mem:
                        life.apply_degradation(mem.conn,row,proposals)
                        total['degraded']+=1
                except Exception as exc:
                    degradation_errors.append(type(exc).__name__)
            if batch:
                with database(path) as mem:
                    current = life.parents(mem.conn)
                    batch = [current[s['source_id']] for s in batch if s['source_id'] in current]
                aliases = {f'm{i}':s['source_id'] for i,s in enumerate(batch)}
                proposed=extractor(life.GRAPH_PROMPT,[dict(s,source_id=f'm{i}') for i,s in enumerate(batch)],[])
                for p in proposed:
                    p['source_id']=aliases.get(p.get('source_id'))
                by_id = {p.get('source_id'): p for p in proposed}
                if len(by_id) != len(proposed) or set(by_id) != {s['source_id'] for s in batch}:
                    raise ValueError('Invalid graph response')
                graph_errors = []
                with database(path) as mem:
                    for source in batch:
                        try:
                            total['graph_edges']+=life.apply_graph(mem.conn,[source],[by_id[source['source_id']]])
                            total['graph_processed']+=1
                        except ValueError as exc:
                            graph_errors.append(exc)
                if graph_errors:
                    raise graph_errors[0]
            with database(path) as mem:
                mem.conn.execute("INSERT OR REPLACE INTO lifecycle_state VALUES ('last_error',?)", (degradation_errors[0] if degradation_errors else '',))
                total['failed_banks'] += bool(degradation_errors)
                mem.conn.execute("INSERT OR REPLACE INTO lifecycle_state VALUES ('batch_size','8')")
                mem.conn.execute("INSERT OR REPLACE INTO lifecycle_state VALUES ('last_success',?)", (datetime.now(timezone.utc).isoformat(),))
                seen = dict(mem.conn.execute('SELECT * FROM personal_graph_sources'))
                remaining = sum(seen.get(mid) != life.facts.fingerprint(p['content']) for mid,p in life.parents(mem.conn).items())
                mem.conn.execute("INSERT OR REPLACE INTO lifecycle_state VALUES ('graph_pending',?)", (str(remaining),))
                mem.conn.execute("INSERT OR REPLACE INTO lifecycle_state VALUES ('degradation_pending',?)", (str(len(life.due(mem.conn))),))
                mem.conn.commit()
        except Exception as exc:
            reason = str(exc) if isinstance(exc, ValueError) and str(exc).startswith(('Invalid graph', 'Incomplete graph', 'Too many graph', 'Graph source')) else type(exc).__name__
            print(json.dumps({'status':'graph_retry','reason':reason}),flush=True)
            total['failed_banks']+=1
            with database(path) as mem:
                mem.conn.execute("INSERT OR REPLACE INTO lifecycle_state VALUES ('last_error',?)", (type(exc).__name__,))
                mem.conn.execute("INSERT OR REPLACE INTO lifecycle_state VALUES ('batch_size','1')")
                mem.conn.commit()
        return total
    failed_paths = set()
    with ThreadPoolExecutor(max_workers=4) as pool:
        for item, result in zip(queue[:max_banks], pool.map(process, queue[:max_banks])):
            if result['failed_banks']:
                failed_paths.add(item[2])
            for key, value in result.items():
                if key != 'failed_banks':
                    total[key] += value
    total['failed_banks'] = len(failed_paths)
    print(json.dumps(total),flush=True)
    return total


if __name__=='__main__':
    import argparse
    import fcntl
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--drain',action='store_true',help='Process historical backlog without timer pauses')
    parser.add_argument('--max-banks',type=int,default=10)
    args=parser.parse_args()
    root=Path(STATE_DIR)/'personal_context'
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(root/'lifecycle.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        if args.drain:
            print('Graph backfill waiting for the current lifecycle pass, then draining',flush=True)
        fcntl.flock(fd,fcntl.LOCK_EX | (0 if args.drain else fcntl.LOCK_NB))
        while True:
            result=run(max_banks=max(1,min(args.max_banks,64)))
            if not args.drain or not result['pending_banks']:
                break
            if not result['graph_processed'] and not result['degraded']:
                raise RuntimeError('Lifecycle cannot progress; pending sources retained for retry')
    except BlockingIOError:
        print('Memory lifecycle already running')
    finally:
        os.close(fd)
