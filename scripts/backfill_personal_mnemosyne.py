#!/usr/bin/env python3
"""Explicit, resumable import of owned WebUI history. Dry run by default.

Run with the Hermes interpreter. Never infer a shared-message author from the
conversation owner, or treat assistant/tool text as the person's statements.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import personal_mnemosyne as memory


def email(value):
    value = str(value or '').strip().lower()
    return value if re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value) else ''


def text_content(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return '\n'.join(p.get('text', '') for p in content
                         if isinstance(p, dict) and p.get('type') == 'text'
                         and isinstance(p.get('text'), str)).strip()
    return ''


def records(data, sid, skipped):
    owner = email(data.get('owner_email'))
    messages = data.get('messages') or []
    authors = {email(m.get('author_email')) for m in messages if isinstance(m, dict)
               and m.get('role') == 'user' and m.get('author_email')}
    shared = bool(data.get('project_shared') or data.get('participants') or (authors - {'', owner}))
    session = SimpleNamespace(session_id=sid, owner_email=owner, participants=data.get('participants') or [],
                              project_shared=shared, profile=data.get('profile') or 'default',
                              project_id=data.get('project_id') or '')
    for index, message in enumerate(messages):
        if not isinstance(message, dict) or message.get('role') != 'user':
            continue
        if (message.get('_source') not in (None, '', 'webui') or any(message.get(k) for k in
                ('_empty_recovery_synthetic', '_length_continuation_nudge', '_wakeup_meta',
                 '_compaction_tail', 'bot_delegation'))):
            skipped['automatic_or_synthetic'] += 1
            continue
        author = email(message.get('author_email')) if message.get('author_email') else ('' if shared else owner)
        if not author:
            skipped['unknown_author'] += 1
            continue
        content = text_content(message.get('content'))
        if not content:
            skipped['empty_or_nontext'] += 1
            continue
        # No API-content sidecars, binaries, tool output or model summaries.
        # Chunk instead of silently dropping the end of a long user message.
        for part, start in enumerate(range(0, len(content), memory.MAX_CONTENT)):
            chunk = content[start:start + memory.MAX_CONTENT]
            if not chunk.strip():
                continue
            source = {'chat': sid, 'bot': session.profile, 'project': session.project_id,
                      'message_index': index, 'message_time': message.get('timestamp'),
                      'part': part, 'import_version': 1, 'kind': 'historical_user_statement'}
            # Content identity survives editing/deleting the imported memory.
            # The receipt is retained even if the owner later deletes it.
            receipt = hashlib.sha256(json.dumps([author, sid, index, part, chunk], ensure_ascii=False).encode()).hexdigest()
            yield author, session, chunk, source, receipt


def backup(path, directory):
    target = directory / (path.parent.parent.name + '-' + path.name)
    absent = target.with_suffix('.absent')
    if target.exists() or absent.exists():
        return
    if not path.exists():
        absent.write_text('Bank did not exist before this import.\n')
        absent.chmod(0o600)
        return
    with sqlite3.connect(path) as source, sqlite3.connect(target) as dest:
        source.backup(dest)
    target.chmod(0o600)


def import_batch(author, session, entries, backup_dir):
    result = Counter()
    identity = {'email': author}
    with memory._locked(identity, memory._bank(session)) as path:
        backup(path, backup_dir)
        with memory._beam(path) as mem:
            mem.conn.execute('''CREATE TABLE IF NOT EXISTS webui_history_imports
                (receipt TEXT PRIMARY KEY, memory_id TEXT NOT NULL, imported_at TEXT NOT NULL)''')
            mem.conn.commit()
            for content, source, receipt in entries:
                if mem.conn.execute('SELECT 1 FROM webui_history_imports WHERE receipt=?', (receipt,)).fetchone():
                    result['already_processed'] += 1
                    continue
                content = memory._content(content)
                mid = receipt[:32]
                existing = mem.conn.execute("SELECT id FROM working_memory WHERE session_id='personal' AND (id=? OR content=?) LIMIT 1", (mid, content)).fetchone()
                if existing:
                    mid = existing['id']
                    result['existing_memory'] += 1
                else:
                    mid = mem.remember(content, memory_id=mid, source='webui_history',
                                       veracity='stated', metadata=source)
                    ts = source.get('message_time')
                    try:
                        stamp = datetime.fromtimestamp(float(ts), timezone.utc).replace(tzinfo=None).isoformat()
                    except (ValueError, TypeError, OverflowError, OSError):
                        stamp = None
                    if stamp:
                        mem.conn.execute('UPDATE working_memory SET timestamp=? WHERE id=?', (stamp, mid))
                    result['created'] += 1
                mem.conn.execute('INSERT INTO webui_history_imports VALUES (?,?,?)',
                                 (receipt, mid, datetime.now(timezone.utc).isoformat()))
                mem.conn.commit()
    return result


def run(session_dir, report_dir, apply=False):
    # Only this offline importer opts out; serving process config is unchanged.
    os.environ['MNEMOSYNE_NO_EMBEDDINGS'] = '1'
    report_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    report_dir.chmod(0o700)
    backup_dir = report_dir / 'backups'
    backup_dir.mkdir(mode=0o700, exist_ok=True)
    counts = defaultdict(Counter)
    skipped = Counter()
    errors = []
    sessions = 0
    for path in sorted(session_dir.glob('*.json')):
        if path.name.startswith('_'):
            continue
        try:
            if path.is_symlink():
                raise ValueError('symlink_session')
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                raise ValueError('invalid_session')
            sessions += 1
            grouped = defaultdict(list)
            scopes = {}
            for author, session, content, source, receipt in records(data, path.stem, skipped):
                key = (author, memory._bank(session))
                grouped[key].append((content, source, receipt));scopes[key] = session
            for key, entries in grouped.items():
                author, bank = key
                counts[author]['chats'] += 1
                counts[author]['candidate_memories'] += len(entries)
                counts[author]['shared_chat_memories' if bank != 'private' else 'private_memories'] += len(entries)
                if apply:
                    # Short lock windows let live chat memory writes continue.
                    for start in range(0, len(entries), 20):
                        counts[author].update(import_batch(author, scopes[key], entries[start:start+20], backup_dir))
        except Exception as exc:
            errors.append({'chat': path.stem, 'error_type': type(exc).__name__})
        if sessions % 50 == 0:
            print(json.dumps({'scanned': sessions, 'created': sum(c['created'] for c in counts.values()), 'errors': len(errors)}), flush=True)
    report = {'applied': apply, 'scanned_chats': sessions, 'people': dict(counts), 'skipped_messages': dict(skipped), 'errors': errors}
    target = report_dir / ('applied.json' if apply else 'preview.json')
    target.write_text(json.dumps(report, indent=2));target.chmod(0o600)
    print(json.dumps(report), flush=True)
    return report


if __name__ == '__main__':
    from api.config import SESSION_DIR, STATE_DIR
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--report-dir', type=Path, required=True)
    args = parser.parse_args()
    outcome = run(SESSION_DIR, args.report_dir, args.apply)
    raise SystemExit(1 if outcome['errors'] else 0)
