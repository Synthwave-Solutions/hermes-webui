"""Opt-in completion of a live, pre-execution governance pause.

No prompts or tool arguments are replayed. A lost live waiter needs input.
SQLite owns consent, immutable operation bindings, and transition audit.
"""
from __future__ import annotations
import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

_WAITERS: dict[str, threading.Event] = {}
_LOCK = threading.RLock()
_RUNNING: set[str] = set()
MAX_WAIT_SECONDS = 300

@contextmanager
def _db():
    from api import config
    path = Path(config.STATE_DIR) / 'approval-resume.sqlite'
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    path.chmod(0o600)
    db.row_factory = sqlite3.Row
    try:
        db.executescript('''CREATE TABLE IF NOT EXISTS consent(owner TEXT, session TEXT, expires REAL, PRIMARY KEY(owner,session));
        CREATE TABLE IF NOT EXISTS intents(id TEXT PRIMARY KEY, owner TEXT, session TEXT, grant_key TEXT, binding TEXT, status TEXT, expires REAL, reason TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, operation TEXT, status TEXT, at REAL, reason TEXT);''')
        with db:
            yield db
    finally:
        db.close()

def _transition(db, op, status, reason=''):
    db.execute('UPDATE intents SET status=?,reason=? WHERE id=?', (status, reason, op))
    db.execute('INSERT INTO events(operation,status,at,reason) VALUES(?,?,?,?)', (op,status,time.time(),reason))

def set_consent(owner: str, session: str, enabled: bool):
    if not owner or not session:
        raise ValueError('Authenticated conversation required')
    with _db() as db:
        db.execute('INSERT OR REPLACE INTO consent VALUES(?,?,?)', (owner,session,time.time()+3600 if enabled else 0))
    if not enabled:
        for row in records(owner):
            if row['session']==session and row['status'] in ('waiting','queued'):
                cancel(owner,row['id'])

def consent_enabled(owner: str, session: str):
    with _db() as db:
        row=db.execute('SELECT expires FROM consent WHERE owner=? AND session=?',(owner,session)).fetchone()
        return bool(row and row['expires']>time.time())

def records(owner: str):
    with _LOCK, _db() as db:
        rows=db.execute('SELECT * FROM intents WHERE owner=? ORDER BY rowid DESC LIMIT 100',(owner,)).fetchall()
        for row in rows:
            if row['status']=='resumed' and row['id'] not in _RUNNING:
                _transition(db,row['id'],'input-needed','Execution outcome unknown after restart; nothing replayed')
            if row['status'] in ('waiting','queued'):
                if row['expires']<=time.time():
                    _transition(db,row['id'],'expired','Approval wait expired')
                elif row['id'] not in _WAITERS:
                    _transition(db,row['id'],'input-needed','The original paused operation is no longer running')
        return [dict(r) for r in db.execute('SELECT id,session,status,expires,reason FROM intents WHERE owner=? ORDER BY rowid DESC LIMIT 100',(owner,))]

def cancel(owner: str, operation_id: str):
    with _LOCK, _db() as db:
        row=db.execute('SELECT * FROM intents WHERE id=? AND owner=?',(operation_id,owner)).fetchone()
        if row is None: raise KeyError('Unknown continuation')
        if row['status'] in ('waiting','queued'):
            _transition(db,operation_id,'cancelled','Cancelled by requester')
            if operation_id in _WAITERS: _WAITERS[operation_id].set()

def decide(entry: dict, decision: str):
    """Signal only an exact matching, immutable, still-live operation."""
    payload=entry.get('payload') or {}
    owner=str(entry.get('owner_email') or '').strip().lower()
    operations=payload.get('operations') or {}
    with _LOCK, _db() as db:
        rows=db.execute("SELECT * FROM intents WHERE owner=? AND grant_key=? AND status='waiting'",(owner,entry.get('key'))).fetchall()
        for row in rows:
            saved=json.loads(row['binding']); current=operations.get(row['id'])
            if not isinstance(current,dict) or any(current.get(k)!=saved.get(k) for k in ('operation_id','actor_email','session_id','request_id','tool_call_id','prompt_sha256','gkind','value')):
                _transition(db,row['id'],'input-needed','Approval no longer matches the paused operation')
            elif row['expires']<=time.time(): _transition(db,row['id'],'expired','Approval wait expired')
            elif row['id'] not in _WAITERS: _transition(db,row['id'],'input-needed','Original operation is no longer running')
            elif decision!='approve': _transition(db,row['id'],'failed','Access request declined')
            else: _transition(db,row['id'],'queued','Approved; current policy must still be revalidated')
            event=_WAITERS.get(row['id'])
            if event: event.set()

def make_waiter(owner, session, request, prompt_sha256, cancel_event, *, fresh=lambda: True, max_wait=MAX_WAIT_SECONDS):
    """Bound by the authenticated run, never from a browser-supplied identity."""
    if not consent_enabled(owner,session): return None
    def wait(operation):
        expected={'actor_email':owner,'session_id':session,'request_id':request,'prompt_sha256':prompt_sha256}
        if not prompt_sha256 or operation.get('binding_status')!='bound' or operation.get('freshness_status')!='bound' or any(operation.get(k)!=v for k,v in expected.items()): return False
        op=operation.get('operation_id'); call=operation.get('tool_call_id')
        if not op or not call or not operation.get('gkind') or not operation.get('value'): return False
        key=f"{owner}|{operation['gkind']}|{operation['value']}"
        event=threading.Event()
        deadline=time.time()+min(MAX_WAIT_SECONDS,max(0,max_wait))
        with _LOCK, _db() as db:
            if db.execute('SELECT 1 FROM intents WHERE id=?',(op,)).fetchone(): return False
            _WAITERS[op]=event
            db.execute('INSERT INTO intents VALUES(?,?,?,?,?,?,?,?)',(op,owner,session,key,json.dumps(operation,sort_keys=True),'waiting',deadline,''))
            db.execute('INSERT INTO events(operation,status,at,reason) VALUES(?,?,?,?)',(op,'waiting',time.time(),'Requester opted in before this run'))
        try:
            from api import approvals
            existing = approvals.get(approvals.KIND_GRANT, key)
            if existing and existing.get("status") in ("approved", "rejected"):
                decide(existing, "approve" if existing["status"] == "approved" else "reject")
            while True:
                event.wait(min(.25,max(0,deadline-time.time())))
                with _LOCK, _db() as db:
                    row=db.execute('SELECT * FROM intents WHERE id=?',(op,)).fetchone()
                    if cancel_event.is_set(): _transition(db,op,'cancelled','Run cancelled'); return False
                    if time.time()>=deadline: _transition(db,op,'expired','Approval wait expired'); return False
                    if not fresh(): _transition(db,op,'input-needed','Conversation or workspace changed'); return False
                    if row['status']=='queued':
                        _RUNNING.add(op)
                        _transition(db,op,'resumed','Original invocation released for policy revalidation')
                        return True
                    if row['status']!='waiting': return False
        finally:
            with _LOCK: _WAITERS.pop(op,None)
    wait.finish = finish
    return wait

def finish(operation_id: str, success: bool):
    """Called by the original gate after revalidation/execution, never a replay."""
    with _db() as db:
        row=db.execute('SELECT status FROM intents WHERE id=?',(operation_id,)).fetchone()
        if row and row['status']=='resumed':
            _transition(db,operation_id,'completed' if success else 'failed','Original invocation finished' if success else 'Revalidation or invocation failed')
            _RUNNING.discard(operation_id)


def finish_call(request_id, tool_call_id, result):
    # The normal tool-complete callback is authoritative for invocation return.
    try:
        value = json.loads(result) if isinstance(result, str) else result
    except (TypeError, ValueError):
        value = None
    success = not (isinstance(value, dict) and (value.get('error') or value.get('is_error') or value.get('success') is False))
    with _db() as db:
        for row in db.execute("SELECT id,binding FROM intents WHERE status='resumed'").fetchall():
            binding = json.loads(row['binding'])
            if binding.get('request_id') == request_id and binding.get('tool_call_id') == tool_call_id:
                _transition(db,row['id'],'completed' if success else 'failed','Original tool invocation returned')
                _RUNNING.discard(row['id'])


def close_run(request_id):
    with _LOCK, _db() as db:
        for row in db.execute("SELECT id,binding FROM intents WHERE status IN ('waiting','queued','resumed')").fetchall():
            if json.loads(row['binding']).get('request_id') == request_id:
                _transition(db,row['id'],'input-needed','Run ended without a verified invocation outcome; nothing replayed')
                _RUNNING.discard(row['id'])
                event=_WAITERS.get(row['id'])
                if event: event.set()
