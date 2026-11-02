"""Provenance-preserving migration from one user's mixed bank to bot banks."""
import os
from pathlib import Path
import subprocess


def test_split_preserves_supported_memories_and_isolates_bots(tmp_path):
    root=Path(__file__).resolve().parents[1]
    script=r'''
import sys,json
from types import SimpleNamespace as NS
sys.path[:0]=sys.argv[1:]
from api import personal_mnemosyne as p,personal_consolidation as f,personal_episodes as e,personal_lifecycle as l,memory_banks as banks
from scripts.consolidate_personal_memory import database
from scripts.consolidate_company_memory import discover
from scripts.split_bot_memory import split
a={'email':'alice@example.test'};b={'email':'bob@example.test'}
path=p._path(a,'private')
path.parent.mkdir(parents=True)
with database(path) as mem:
 e.schema(mem.conn);l.schema(mem.conn)
 mids=[]
 for bot,word in [('alpha','Kobalt'),('beta','Amber')]:
  content=f'Project {word} gebruikt PostgreSQL voor de database; de release is nog niet klaar.'
  mid=mem.remember(content,memory_id=('a' if bot=='alpha' else 'b')*32,source='webui',metadata={'bot':bot,'chat':bot})
  mids.append(mid)
  key,batch=next((k,v) for k,v in e.batches(mem.conn).items() if any(s['source_id']==mid for s in v))
  assert e.apply(mem,key,batch,[dict(content=content,evidence=[dict(source_id=mid,quote=content)])])==1
 source=next(s for s in f.sources(mem.conn) if s['source_id']==mids[0])
 assert f.apply(mem,[dict(topic='database',category='project',content=source['content'],confidence=.99,evidence=[dict(source_id=source['source_id'],quote=source['content'])])],[source])==1
 # A mixed-bot derived fact must never be copied into either bot's memory.
 src=f.sources(mem.conn)
 assert f.apply(mem,[dict(topic='mixed',category='project',content='Project Kobalt en project Amber gebruiken PostgreSQL voor hun database.',confidence=.99,evidence=[dict(source_id=s['source_id'],quote=s['content']) for s in src])],src)==1
 l.schema(mem.conn)
 parents=list(l.parents(mem.conn).values())
 l.apply_graph(mem.conn,parents,[dict(source_id=s['source_id'],relations=[dict(subject='Project',predicate='uses',object='PostgreSQL',quote=s['content'])]) for s in parents])
 mem.conn.execute('CREATE TABLE webui_history_imports (receipt TEXT PRIMARY KEY,memory_id TEXT,imported_at TEXT)')
 mem.conn.execute('INSERT INTO webui_history_imports VALUES (?,?,?)',('deleted-receipt','f'*32,'2026-01-01'))
 mem.conn.commit()
 before=dict(mem.conn.execute('SELECT id,content FROM working_memory'))
company_before={r['source_id']:r['fingerprint'] for r in discover()}
assert split(path)['originals']==2
assert split(path,True)['banks']==2
assert split(path,True)['skipped']
assert company_before=={r['source_id']:r['fingerprint'] for r in discover()}
with p._read(path) as db:
 assert banks.archived(db)
 assert dict(db.execute('SELECT id,content FROM working_memory'))==before
for bot,own,foreign in [('alpha','Kobalt','Amber'),('beta','Amber','Kobalt')]:
 session=NS(session_id='new-chat',profile=bot)
 assert own in p.recall(a,session,own)
 assert foreign not in p.recall(a,session,foreign)
 assert not p.recall(b,session,own)
 target=p._path(a,p._bank(session))
 with database(target) as mem:
  assert mem.conn.execute('SELECT count(*) FROM episodic_memory').fetchone()[0]==1
  assert mem.conn.execute("SELECT count(*) FROM personal_facts WHERE topic='mixed'").fetchone()[0]==0
  assert mem.conn.execute("SELECT count(*) FROM webui_history_imports WHERE receipt='deleted-receipt'").fetchone()[0]==1
  assert l.recall(mem.conn,'PostgreSQL')
 assert 'private.db' not in {x.name for x in banks.active_paths(target.parent)}
row=next(x for x in p.listing(a)['items'] if x['id']==mids[0])
assert row['bot']=='alpha'
p.mutate(a,dict(row,operation='edit',content='Project Kobalt gebruikt nu SQLite voor de database.'))
assert split(path,True)['skipped']
assert 'SQLite' in p.recall(a,NS(profile='alpha'),'Kobalt')
try:p.mutate(a,dict(row,bank='private',operation='delete'));raise AssertionError('archived mutation accepted')
except p.Conflict:pass
# A historical deleted message cannot reappear even under a newly created bot.
from scripts.backfill_personal_mnemosyne import import_batch
backup=path.parent/'backups';backup.mkdir()
result=import_batch(a['email'],NS(profile='gamma',session_id='old',project_shared=False),
 [('Deleted text must not return',{},'deleted-receipt')],backup)
assert result['already_processed']==1 and result['created']==0
assert not p.recall(a,NS(profile='gamma'),'Deleted')
# A deleted fact spanning bots keeps its source blocks without copying its text.
c={'email':'charlie@example.test'};legacy=p._path(c,'private');legacy.parent.mkdir(parents=True)
with database(legacy) as mem:
 for bot in ('alpha','beta'):
  mem.remember('Project '+bot+' gebruikt een database voor rapportages.',metadata={'bot':bot,'chat':bot})
 src=f.sources(mem.conn)
 f.apply(mem,[dict(topic='removed',category='project',content='Een oude gecombineerde conclusie over de projecten.',confidence=.99,evidence=[dict(source_id=x['source_id'],quote=x['content']) for x in src])],src)
 mid=mem.conn.execute('SELECT memory_id FROM personal_facts').fetchone()[0]
 mem.forget_working(mid)
 mem.conn.execute('UPDATE personal_facts SET manual=1,deleted=1');mem.conn.commit()
split(legacy,True)
for bot in ('alpha','beta'):
 with database(p._path(c,banks.key(bot))) as mem:
  assert mem.conn.execute('SELECT count(*) FROM personal_facts WHERE manual=1 AND deleted=1').fetchone()[0]==1
  assert not e.eligible_sources(mem.conn)
  assert not mem.conn.execute("SELECT 1 FROM working_memory WHERE content LIKE '%gecombineerde%'").fetchone()
'''
    result=subprocess.run([os.environ['HERMES_WEBUI_PYTHON'],'-c',script,str(root),
        os.environ.get('HERMES_WEBUI_AGENT_DIR',str(Path.home()/'.hermes/hermes-agent'))],
        env=dict(os.environ,HERMES_HOME=str(tmp_path/'home'),HERMES_WEBUI_STATE_DIR=str(tmp_path/'state'),MNEMOSYNE_NO_EMBEDDINGS='1'),
        capture_output=True,text=True,timeout=120,cwd=root)
    assert result.returncode==0,result.stderr[-5000:]+result.stdout[-1000:]
