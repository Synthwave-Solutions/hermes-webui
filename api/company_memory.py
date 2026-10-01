"""Admin-managed, automatically consolidated Mnemosyne company knowledge.

Only reviewed-by-code structured business claims enter the shared bank. Raw
personal messages remain in their original banks; the worker stores references.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import threading

from api import personal_mnemosyne as personal

_LOCK = threading.RLock()
CATEGORIES = {'process', 'tools', 'services', 'communication', 'standards'}
_SENSITIVE = re.compile(r'(?i)(password|wachtwoord|api.?key|secret|geheim|bearer|iban|salary|salaris|medical|medisch|patient|privé|private|personal|persoonlijk|home address|geboortedatum|[\w.+-]+@[\w.-]+\.[a-z]{2,})')


def path():
    from api.config import STATE_DIR
    return personal.pc._safe(Path(STATE_DIR) / 'company_memory' / 'mnemosyne.db')


def is_admin(identity):
    from api.ownership import identity_is_admin
    return identity_is_admin(identity)


def require_admin(identity):
    if not is_admin(identity):
        raise PermissionError('Company memory management is available to admins only')


@contextmanager
def database():
    import fcntl
    target = path()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    target.parent.chmod(0o700)
    with _LOCK:
        fd = os.open(personal.pc._safe(target.with_suffix('.lock')), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            for suffix in ('', '-wal', '-shm'):
                personal.pc._safe(target.with_name(target.name + suffix))
            with personal._beam(target) as mem:
                mem.conn.executescript('''
                    CREATE TABLE IF NOT EXISTS company_facts (
                        topic TEXT PRIMARY KEY, memory_id TEXT UNIQUE NOT NULL,
                        category TEXT NOT NULL, manual INTEGER NOT NULL DEFAULT 0,
                        deleted INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS company_sources (
                        source_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, processed_at TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS company_evidence (
                        topic TEXT NOT NULL, source_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
                        PRIMARY KEY(topic,source_id));
                    CREATE TABLE IF NOT EXISTS company_audit (
                        id INTEGER PRIMARY KEY, at TEXT NOT NULL, actor TEXT NOT NULL,
                        action TEXT NOT NULL, topic TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS company_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                ''')
                yield mem
        finally:
            os.close(fd)


def now():
    return datetime.now(timezone.utc).isoformat()


def _audit(db, actor, action, topic):
    db.execute('INSERT INTO company_audit(at,actor,action,topic) VALUES (?,?,?,?)', (now(), actor, action, topic))


def listing(identity, query='', offset=0):
    require_admin(identity)
    offset = max(0, min(int(offset), 100000))
    with database() as mem:
        pattern = '%' + str(query or '')[:200].replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        where = "f.deleted=0 AND w.content LIKE ? ESCAPE '\\'"
        total = mem.conn.execute('SELECT count(*) FROM company_facts f JOIN working_memory w ON w.id=f.memory_id WHERE '+where, (pattern,)).fetchone()[0]
        rows = mem.conn.execute('''SELECT w.id,w.content,f.topic,f.category,f.manual,f.updated_at AS timestamp,
            (SELECT count(*) FROM company_evidence e WHERE e.topic=f.topic) AS sources
            FROM company_facts f JOIN working_memory w ON w.id=f.memory_id WHERE ''' + where +
            ' ORDER BY f.updated_at DESC,f.topic LIMIT 50 OFFSET ?', (pattern,offset)).fetchall()
        items = [dict(row, bank='company',scope='company', revision=personal._revision(row['content'])) for row in rows]
        state = {row[0]:row[1] for row in mem.conn.execute('SELECT key,value FROM company_state')}
        return {'items':items,'total':total,'offset':offset,'limit':50,'consolidation':state}


def mutate(identity, body):
    require_admin(identity)
    if body.get('operation') not in ('edit','delete'):
        raise ValueError('Invalid company memory operation')
    with database() as mem:
        row = mem.conn.execute('''SELECT f.*,w.content FROM company_facts f
            JOIN working_memory w ON w.id=f.memory_id WHERE f.memory_id=? AND f.deleted=0''', (str(body.get('id') or ''),)).fetchone()
        if not row:
            raise ValueError('Company memory not found')
        if body.get('revision') != personal._revision(row['content']):
            raise personal.Conflict('Company memory changed. Refresh before editing.')
        if body['operation'] == 'edit':
            # UI edits do not need embeddings; FTS triggers update immediately.
            content = personal._content(body.get('content'))
            mem.conn.execute('UPDATE working_memory SET content=? WHERE id=?', (content,row['memory_id']))
            mem.conn.execute('UPDATE company_facts SET manual=1,updated_at=? WHERE topic=?', (now(),row['topic']))
        else:
            mem.forget_working(row['memory_id'])
            # Permanent topic tombstone stops later consolidation resurrecting it.
            mem.conn.execute('UPDATE company_facts SET deleted=1,manual=1,updated_at=? WHERE topic=?', (now(),row['topic']))
        _audit(mem.conn, personal.pc.actor_email(identity), body['operation'], row['topic'])
        mem.conn.commit()
    return {'ok':True}


def recall(query):
    target = path()
    if not target.exists():
        return ''
    terms = re.findall(r'\w{2,}', str(query))[:32]
    if not terms:
        return ''
    conn = personal._read(target)
    try:
        rows = conn.execute('''SELECT w.content FROM fts_working f
            JOIN working_memory w ON w.id=f.id JOIN company_facts c ON c.memory_id=w.id
            WHERE fts_working MATCH ? AND c.deleted=0 ORDER BY rank,c.updated_at DESC LIMIT 5''',
            (' OR '.join('"'+t+'"' for t in terms),)).fetchall()
        return '\n'.join(r['content'] for r in rows)[:5000]
    finally:
        conn.close()


def validate_proposals(proposals, sources):
    if not isinstance(proposals, list) or len(proposals) > 30:
        raise ValueError('Invalid consolidation response')
    accepted = []
    for proposal in proposals:
        if not isinstance(proposal,dict):
            raise ValueError('Invalid company claim')
        topic = str(proposal.get('topic') or '')
        content = str(proposal.get('content') or '').strip()
        evidence = proposal.get('evidence') or []
        category = proposal.get('category')
        if not re.fullmatch(r'[a-z][a-z0-9_-]{2,95}', topic) or category not in CATEGORIES:
            raise ValueError('Invalid company topic')
        if not 15 <= len(content) <= 1600 or _SENSITIVE.search(content):
            continue
        if proposal.get('scope') != 'company' or proposal.get('confidence',0) < .9:
            continue
        if not isinstance(evidence,list) or not evidence:
            continue
        valid=[]
        for e in evidence:
            if not isinstance(e,dict):
                continue
            source=sources.get(e.get('source_id'));quote=str(e.get('quote') or '')
            if source and len(quote)>=15 and quote in source['content'] and not _SENSITIVE.search(quote):
                valid.append(source)
        if not valid:
            continue
        kind = proposal.get('kind', 'stated_fact')
        if kind not in ('stated_fact', 'observed_practice'):
            continue
        if kind == 'observed_practice':
            origins = {(s.get('origin_actor'),s.get('chat')) for s in valid if s.get('origin_actor')}
            if len(origins) < 2 or not content.startswith('Waargenomen werkwijze:'):
                continue
        clean = personal._content(content)
        if clean != content:
            continue
        accepted.append({'topic':topic,'content':content,'category':category,'sources':valid})
    return accepted


def apply_proposals(proposals, sources):
    accepted = validate_proposals(proposals, {s['source_id']:s for s in sources})
    updated=0
    with database() as mem:
        for fact in accepted:
            topic=fact['topic']
            row=mem.conn.execute('SELECT * FROM company_facts WHERE topic=?',(topic,)).fetchone()
            if not row:
                row=mem.conn.execute('SELECT f.* FROM company_facts f JOIN working_memory w ON w.id=f.memory_id WHERE w.content=?', (fact['content'],)).fetchone()
                if row: topic=row['topic']
            # Suppress renamed claims backed by sources of a removed or pinned topic.
            if any(mem.conn.execute('SELECT 1 FROM company_evidence e JOIN company_facts f ON f.topic=e.topic WHERE e.source_id=? AND (f.deleted=1 OR f.manual=1)', (source['source_id'],)).fetchone() for source in fact['sources']):
                continue
            if row and (row['manual'] or row['deleted']):
                continue
            mid=hashlib.sha256(('company:'+topic).encode()).hexdigest()[:32]
            if row:
                mem.conn.execute('UPDATE working_memory SET content=? WHERE id=?',(fact['content'],mid))
                mem.conn.execute('UPDATE company_facts SET updated_at=? WHERE topic=?',(now(),topic))
            else:
                mid=mem.remember(fact['content'],source='company_consolidation',veracity='inferred',memory_id=mid,
                                 metadata={'topic':topic,'category':fact['category']})
                mem.conn.execute('INSERT INTO company_facts(topic,memory_id,category,updated_at) VALUES (?,?,?,?)',
                                 (topic,mid,fact['category'],now()))
            for source in fact['sources']:
                mem.conn.execute('INSERT OR REPLACE INTO company_evidence VALUES (?,?,?)',
                                 (topic,source['source_id'],source['fingerprint']))
            _audit(mem.conn,'consolidator','consolidate',topic)
            updated+=1
        for source in sources:
            mem.conn.execute('INSERT OR REPLACE INTO company_sources VALUES (?,?,?)',
                             (source['source_id'],source['fingerprint'],now()))
        mem.conn.execute('INSERT OR REPLACE INTO company_state VALUES (?,?)',('last_success',now()))
        mem.conn.execute('INSERT OR REPLACE INTO company_state VALUES (?,?)',('last_error',''))
        mem.conn.commit()
    return updated
