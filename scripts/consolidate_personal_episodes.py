#!/usr/bin/env python3
"""Incremental episodic consolidation; originals and personal bank boundaries survive."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['MNEMOSYNE_NO_EMBEDDINGS'] = '1'
from api import personal_episodes as episodes
from api.config import STATE_DIR
from api.memory_extraction import extract
from scripts.consolidate_personal_memory import database


def extract_episode(system, batch, catalog):
    from openai import APIConnectionError, APIStatusError
    # Short request-local references avoid model transcription errors in long
    # database identifiers. Restore only explicit source_id fields afterwards.
    aliases = {f's{i}': row['source_id'] for i, row in enumerate(batch)}
    payload = [dict(row, source_id=f's{i}') for i, row in enumerate(batch)]
    def restore(value):
        if isinstance(value, list):
            return [restore(item) for item in value]
        if isinstance(value, dict):
            return {key: aliases.get(item, item) if key == 'source_id' and isinstance(item, str)
                    else restore(item) for key, item in value.items()}
        return value
    try:
        return restore(extract(system, payload, catalog))
    except (APIConnectionError, APIStatusError) as exc:
        if isinstance(exc, APIStatusError) and exc.status_code not in (408, 429, 500, 502, 503, 504):
            raise
        print(json.dumps({'status':'provider_fallback', 'model':'synthpulse-luna'}), flush=True)
        return restore(extract(system, payload, catalog, model='synthpulse-luna'))


def run(max_batches=10, extractor=extract_episode, workers=2):
    queue = []
    from api.memory_banks import active_paths
    for path in active_paths():
        with database(path) as mem:
            episodes.schema(mem.conn)
            episodes.prune(mem)
            seen = {r['episode_key']: r for r in mem.conn.execute('SELECT * FROM personal_episodes')}
            pending = [(key, batch) for key, batch in episodes.batches(mem.conn).items()
                       if key not in seen or (not seen[key]['manual'] and seen[key]['fingerprint'] != episodes.signature(batch))]
            attempts = dict(mem.conn.execute('SELECT * FROM episode_attempts'))
            pending.sort(key=lambda item: attempts.get(item[0], ''))
            state = dict(mem.conn.execute('SELECT * FROM episode_state'))
            mem.conn.execute("INSERT OR REPLACE INTO episode_state VALUES ('pending',?)", (str(len(pending)),))
            mem.conn.commit()
            # Independent segments can be extracted concurrently. Database writes
            # still hold the bank lock and revalidate the source fingerprints.
            remaining = iter(pending)
            selected = []
            size = 0
            groups = []
            for key, batch in remaining:
                chars = sum(len(s['content']) for s in batch)
                if selected and (len(selected) >= int(state.get('batch_size', '6')) or size + chars > 36000):
                    groups.append(selected)
                    selected, size = [], 0
                    if len(groups) >= max(1, min(workers, 8)):
                        break
                selected.append((key, batch))
                size += chars
            if selected:
                groups.append(selected)
            for index, group in enumerate(groups):
                queue.append((index, state.get('last_attempt', ''), path, group))
    queue.sort(key=lambda item: item[:2])

    def process(item):
        _, _, path, selected = item
        with database(path) as mem:
            attempted = datetime.now(timezone.utc).isoformat()
            mem.conn.execute("INSERT OR REPLACE INTO episode_state VALUES ('last_attempt',?)", (attempted,))
            mem.conn.executemany('INSERT OR REPLACE INTO episode_attempts VALUES (?,?)', [(key, attempted) for key, _ in selected])
            mem.conn.commit()
        processed_count = count = 0
        try:
            if len(selected) == 1:
                key, batch = selected[0]
                by_key = {key: extractor(episodes.SYSTEM, batch, [])}
            else:
                prompt = episodes.SYSTEM + '''\nBatch mode: the input contains independent segments identified by episode_key.
Never combine segments. Return {"facts":[...]} with exactly ONE item for EVERY
episode_key. Each item includes episode_key, content and evidence as above, or
episode_key and skip:true when nothing useful qualifies. Evidence must come from
that same segment. No segment may be omitted.'''
                aliases = {f'episode_{i}': key for i, (key, _) in enumerate(selected)}
                flat = [dict(s, episode_key=f'episode_{i}') for i, (_, batch) in enumerate(selected) for s in batch]
                proposals = extractor(prompt, flat, [])
                by_key = {}
                for proposal in proposals:
                    key = aliases.get(proposal.get('episode_key'))
                    if key in by_key:
                        raise ValueError('Duplicate episode response')
                    by_key[key] = [] if proposal.get('skip') is True else [proposal]
                if set(by_key) != {key for key, _ in selected}:
                    raise ValueError('Incomplete episode batch')
            with database(path) as mem:
                errors = []
                for key, batch in selected:
                    try:
                        count += episodes.apply(mem, key, batch, by_key[key])
                        processed_count += 1
                    except ValueError as exc:
                        errors.append(exc)
                if errors:
                    raise errors[0]
                mem.conn.execute("INSERT OR REPLACE INTO episode_state VALUES ('last_error','')")
                mem.conn.execute("INSERT OR REPLACE INTO episode_state VALUES ('batch_size','6')")
                mem.conn.execute("INSERT OR REPLACE INTO episode_state VALUES ('last_success',?)", (datetime.now(timezone.utc).isoformat(),))
                mem.conn.execute("UPDATE episode_state SET value=CAST(value AS INTEGER)-? WHERE key='pending'", (len(selected),))
                mem.conn.commit()
            print(json.dumps({'status':'processed', 'segments':len(selected), 'episodes':count}), flush=True)
            return len(selected), count
        except Exception as exc:
            with database(path) as mem:
                mem.conn.execute("INSERT OR REPLACE INTO episode_state VALUES ('last_error',?)", (type(exc).__name__,))
                mem.conn.execute("INSERT OR REPLACE INTO episode_state VALUES ('batch_size','1')")
                mem.conn.execute("UPDATE episode_state SET value=CAST(value AS INTEGER)-? WHERE key='pending'", (processed_count,))
                mem.conn.commit()
            reason = str(exc) if type(exc) is ValueError and str(exc).startswith(('Invalid episode', 'Missing episode', 'Unsafe episode', 'Episode ', 'Incomplete ', 'Duplicate episode')) else type(exc).__name__
            print(json.dumps({'status':'retry', 'error_type':type(exc).__name__, 'reason':reason}), flush=True)
            return processed_count, count

    with ThreadPoolExecutor(max_workers=max(1, min(workers, 8))) as pool:
        results = list(pool.map(process, queue[:max_batches]))
    result = dict(processed=sum(r[0] for r in results), episodes=sum(r[1] for r in results), pending_banks=len({item[2] for item in queue}))
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--drain', action='store_true')
    parser.add_argument('--max-batches', type=int, default=10)
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    root = Path(STATE_DIR) / 'personal_context'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(root / 'episodes.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | (0 if args.drain else fcntl.LOCK_NB))
        while True:
            result = run(max(1, min(args.max_batches, 64)), workers=args.workers)
            if not args.drain or not result['pending_banks']:
                break
            if not result['processed']:
                raise RuntimeError('Episode processing cannot progress; originals retained')
    except BlockingIOError:
        print('Episode consolidation already running')
    finally:
        os.close(fd)
