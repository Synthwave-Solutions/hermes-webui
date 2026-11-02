#!/usr/bin/env python3
"""Incremental per-person/per-bank consolidation, never mixing identities."""

import argparse
from datetime import datetime, timezone
from contextlib import contextmanager
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import sys
import sqlite3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["MNEMOSYNE_NO_EMBEDDINGS"] = "1"
from api import personal_mnemosyne as personal, personal_consolidation as facts
from api.memory_extraction import extract
from api.config import STATE_DIR


@contextmanager
def database(path):
    personal.pc._safe(path)
    fd = os.open(
        personal.pc._safe(path.with_suffix(".lock")),
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
        0o600,
    )
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        with personal._beam(path) as mem:
            facts.schema(mem.conn)
            from api.memory_statements import tag_reference_chunks

            tag_reference_chunks(mem.conn)
            yield mem
    finally:
        os.close(fd)


def run(
    max_batches=10, extractor=extract, *, workers=1, batch_chars=48000, batch_size=60
):

    from api.memory_banks import active_paths
    paths = active_paths()
    # Oldest successful bank first so large accounts cannot starve others.
    queue = []
    for path in paths:
        with database(path) as mem:
            facts.prune(mem)
            state = dict(mem.conn.execute("SELECT * FROM personal_state"))
            seen = dict(mem.conn.execute("SELECT * FROM personal_sources"))
            pending = [
                s
                for s in facts.sources(mem.conn)
                if seen.get(s["source_id"]) != s["fingerprint"]
            ]
            mem.conn.execute(
                "INSERT OR REPLACE INTO personal_state VALUES ('pending',?)",
                (str(len(pending)),),
            )
            mem.conn.commit()
        if pending:
            queue.append(
                (
                    state.get("last_attempt", state.get("last_success", "")),
                    path,
                    pending,
                    min(
                        max(24000, min(batch_chars, 128000)),
                        int(state.get("batch_chars", batch_chars)),
                    ),
                )
            )
    queue.sort(key=lambda v: v[0])

    def process_bank(item):
        _, path, pending, bank_chars = item
        updated = 0
        batch = []
        size = 0
        for source in pending:
            if batch and (
                len(batch) >= max(1, min(batch_size, 120))
                or size + len(source["content"]) > bank_chars
            ):
                break
            batch.append(source)
            size += len(source["content"])
        with database(path) as mem:
            mem.conn.execute(
                "INSERT OR REPLACE INTO personal_state VALUES ('last_attempt',?)",
                (datetime.now(timezone.utc).isoformat(),),
            )
            mem.conn.commit()
            catalog = [
                dict(r)
                for r in mem.conn.execute("""SELECT f.topic,f.category,f.manual,f.deleted,f.updated_at,w.content
                     FROM personal_facts f LEFT JOIN working_memory w ON w.id=f.memory_id ORDER BY updated_at DESC LIMIT 250""")
            ]
        try:
            proposed = extractor(facts.SYSTEM, batch, catalog)
            with database(path) as mem:
                updated += facts.apply(mem, proposed, batch)
                mem.conn.execute(
                    "INSERT OR REPLACE INTO personal_state VALUES ('pending',?)",
                    (str(len(pending) - len(batch)),),
                )
                mem.conn.commit()
            return len(batch), updated, 0
        except Exception as exc:
            with database(path) as mem:
                mem.conn.execute(
                    "INSERT OR REPLACE INTO personal_state VALUES ('last_error',?)",
                    (type(exc).__name__,),
                )
                if (
                    isinstance(exc, json.JSONDecodeError)
                    or str(exc) == "Incomplete consolidation response"
                ):
                    mem.conn.execute(
                        "INSERT OR REPLACE INTO personal_state VALUES ('batch_chars',?)",
                        (str(max(24000, bank_chars // 2)),),
                    )
                mem.conn.commit()
            print(
                json.dumps(
                    {
                        "status": "retry",
                        "error_type": type(exc).__name__,
                        "database_error": str(exc)
                        if isinstance(exc, sqlite3.DatabaseError)
                        else None,
                    }
                ),
                flush=True,
            )
            return 0, 0, 1

    # One worker per bank, so corrections retain chronological ordering.
    # Copied contexts preserve any configured profile scope in worker threads.
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as pool:
        futures = [
            pool.submit(copy_context().run, process_bank, item)
            for item in queue[:max_batches]
        ]
        results = [future.result() for future in futures]
    processed = sum(r[0] for r in results)
    updated = sum(r[1] for r in results)
    failed = sum(r[2] for r in results)
    result = {
        "failed_banks": failed,
        "processed": processed,
        "updated_topics": updated,
        "pending_banks": len(queue),
    }
    print(json.dumps(result), flush=True)
    return result


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-batches", type=int, default=10)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--batch-chars", type=int, default=48000)
    parser.add_argument("--batch-size", type=int, default=60)
    parser.add_argument(
        "--drain",
        action="store_true",
        help="Process pending banks until caught up; stop if no progress",
    )
    args = parser.parse_args()
    target = Path(STATE_DIR) / "personal_context"
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(
        personal.pc._safe(target / "consolidation.lock"),
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
        0o600,
    )
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | (0 if args.drain else fcntl.LOCK_NB))
        while True:
            result = run(
                max(1, min(args.max_batches, 50)),
                workers=args.workers,
                batch_chars=args.batch_chars,
                batch_size=args.batch_size,
            )
            if not args.drain or result["pending_banks"] == 0:
                break
            if result["processed"] == 0:
                raise RuntimeError(
                    "Consolidation cannot progress; sources retained for retry"
                )
    except BlockingIOError:
        print("Personal consolidation already running")
    except Exception as exc:
        print(
            json.dumps({"status": "failed", "error_type": type(exc).__name__}),
            flush=True,
        )
        raise SystemExit(1) from None
    finally:
        os.close(fd)
