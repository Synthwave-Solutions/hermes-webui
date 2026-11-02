"""Exercise real banks and dashboard reads across age transitions and graph edits."""
import os
from pathlib import Path
import subprocess


def test_lifecycle_graph_and_recall(tmp_path):
    root=Path(__file__).resolve().parents[1]
    script=r'''
import sys
sys.path[:0]=sys.argv[1:]
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace as NS
from api import personal_mnemosyne as p,personal_episodes as e,personal_lifecycle as l
from scripts.consolidate_personal_memory import database
from scripts.maintain_personal_memory import run
from api.third_party import mnemosyne_dashboard as md
a={'email':'alice@example.test'};b={'email':'bob@example.test'}
s=NS(session_id='graph-chat',profile='default',project_id='')
text='Project Kobalt gebruikt PostgreSQL voor de database. De release is nog niet afgerond.'
source=p.remember(a,s,text)
path=p._path(a,p._bank(s))
with database(path) as mem:
 e.schema(mem.conn)
 key,batch=next(iter(e.batches(mem.conn).items()))
 assert e.apply(mem,key,batch,[dict(content=text,evidence=[dict(source_id=source,quote=text)])])==1
 mid=mem.conn.execute('SELECT memory_id FROM personal_episodes').fetchone()[0]
 # Migrate the previously hard-coded cold tier exactly once.
 mem.conn.execute('UPDATE episodic_memory SET tier=3');mem.conn.commit()
 l.schema(mem.conn)
 assert mem.conn.execute('SELECT tier FROM episodic_memory').fetchone()[0]==1
 now=datetime.now(timezone.utc)
 assert not l.due(mem.conn,now)
 mem.conn.execute('UPDATE episodic_memory SET created_at=?',((now-timedelta(days=31)).isoformat(),));mem.conn.commit()
 row=l.due(mem.conn,now)[0];assert row['target_tier']==2
 l.apply_degradation(mem.conn,row,[dict(source_id=mid,content=text)],now)
 assert mem.conn.execute('SELECT tier FROM episodic_memory').fetchone()[0]==2
 l.schema(mem.conn) # must not reset an actual aged row
 assert mem.conn.execute('SELECT tier FROM episodic_memory').fetchone()[0]==2
 assert not l.due(mem.conn,now)
 row=l.due(mem.conn,now+timedelta(days=150))[0];assert row['target_tier']==3
 l.apply_degradation(mem.conn,row,[dict(source_id=mid,content='Project Kobalt gebruikt PostgreSQL. De release is nog niet afgerond.')],now)
 assert mem.conn.execute('SELECT original_content FROM personal_lifecycle WHERE memory_id=?',(mid,)).fetchone()[0]==text
 assert mem.conn.execute('SELECT count(*) FROM working_memory').fetchone()[0]==1
 assert 'PostgreSQL' in e.recall(mem.conn,'Kobalt')
def extractor(prompt,batch,catalog):
 return [dict(source_id=x['source_id'],relations=[dict(subject='Project Kobalt',predicate='gebruikt',object='PostgreSQL',quote=x['content'])]) for x in batch]
result=run(extractor=extractor)
assert result['graph_edges']==1 and result['graph_processed']==1
assert run(extractor=lambda *a: (_ for _ in ()).throw(AssertionError('reprocessed')))['graph_processed']==0
with database(path) as mem:
 assert 'PostgreSQL' in l.recall(mem.conn,'Kobalt')
 assert mem.conn.execute('SELECT quote FROM personal_graph_edges').fetchone()[0]
 snapshot=list(l.parents(mem.conn).values())
 try:l.apply_graph(mem.conn,snapshot,[dict(source_id=mid,relations=[dict(subject='Kobalt',predicate='uses',object='wrong',quote='invented supporting quotation')])]);raise AssertionError('invalid graph accepted')
 except ValueError:pass
 assert mem.conn.execute('SELECT count(*) FROM triples').fetchone()[0]==1
assert not p.recall(b,s,'Kobalt')
assert 'Knowledge relations' in p.recall(a,s,'Kobalt')
md.allow_paths([path]);dash=md.DashboardStore(path)
assert len(dash.graph()['nodes'])==2 and len(dash.graph()['edges'])==1
assert dash.lifecycle_dashboard()['counts']['cold']==1
assert dash.lifecycle_dashboard()['counts']['recently_degraded']==1
md.allow_paths([])
# Editing a source retracts both episode and graph immediately.
row=next(x for x in p.listing(a)['items'] if x['id']==source)
p.mutate(a,dict(row,operation='edit',content='Project Kobalt gebruikt nu SQLite; de eerdere databasekeuze is vervallen.'))
with database(path) as mem:
 assert mem.conn.execute('SELECT count(*) FROM triples').fetchone()[0]==0
 assert not l.recall(mem.conn,'Kobalt')
 try:l.apply_graph(mem.conn,snapshot,extractor('',snapshot,[]));raise AssertionError('stale graph accepted')
 except ValueError:pass
print('lifecycle-graph-ok')
# Equal relevance must rank hot above a newer cold episode.
for sid,label in [('hot-chat','Warmebron'),('cold-chat','Koudebron')]:
 st=NS(session_id=sid,profile='default',project_id='')
 body=f'Project Amber gebruikt een database voor de planning volgens {label}.'
 original=p.remember(b,st,body)
 with database(p._path(b,p._bank(s))) as mem:
  e.schema(mem.conn)
  key,batch=next((k,v) for k,v in e.batches(mem.conn).items() if any(x['source_id']==original for x in v))
  e.apply(mem,key,batch,[dict(content=body,evidence=[dict(source_id=original,quote=body)])])
with database(p._path(b,p._bank(s))) as mem:
 l.schema(mem.conn)
 mem.conn.execute("UPDATE episodic_memory SET tier=3,timestamp='2099-01-01T00:00:00' WHERE content LIKE '%Koudebron%'")
 mem.conn.commit()
 recalled=e.recall(mem.conn,'Project Amber')
 assert recalled.index('Warmebron')<recalled.index('Koudebron')
 mem.conn.execute('UPDATE personal_episodes SET manual=1')
 mem.conn.execute("UPDATE episodic_memory SET created_at='2020-01-01 00:00:00'")
 mem.conn.commit()
 assert not l.due(mem.conn)
# Multiple graph chunks in one bank commit independently without missing parents.
c={'email':'charlie@example.test'}
for i in range(12):
 body=f'Project Kobalt gebruikt PostgreSQL voor onderdeel {i} van de database.'
 original=p.remember(c,NS(session_id='chunk'+str(i),profile='default',project_id=''),body)
 with database(p._path(c,p._bank(s))) as mem:
  e.schema(mem.conn)
  key,batch=next((k,v) for k,v in e.batches(mem.conn).items() if any(x['source_id']==original for x in v))
  e.apply(mem,key,batch,[dict(content=body,evidence=[dict(source_id=original,quote=body)])])
def partial_extractor(prompt,batch,catalog):
 result=extractor(prompt,batch,catalog)
 for source,proposal in zip(batch,result):
  if 'onderdeel 0 ' in source['content']:
   proposal['relations'][0]['quote']='Fabricated quote with no source support'
 return result
result=run(extractor=partial_extractor)
assert result['graph_processed']==13 and result['failed_banks']==1,result
with database(p._path(c,p._bank(s))) as mem:
 assert mem.conn.execute('SELECT count(*) FROM personal_graph_sources').fetchone()[0]==11
result=run(extractor=extractor)
assert result['graph_processed']==1,result
with database(p._path(c,p._bank(s))) as mem:
 assert mem.conn.execute('SELECT count(*) FROM personal_graph_sources').fetchone()[0]==12
 assert mem.conn.execute('SELECT count(*) FROM personal_graph_edges').fetchone()[0]==12
assert run(extractor=extractor)['graph_processed']==0
'''
    result=subprocess.run([os.environ['HERMES_WEBUI_PYTHON'],'-c',script,str(root),
        os.environ.get('HERMES_WEBUI_AGENT_DIR',str(Path.home()/'.hermes/hermes-agent'))],
        env=dict(os.environ,HERMES_HOME=str(tmp_path/'home'),HERMES_WEBUI_STATE_DIR=str(tmp_path/'state'),MNEMOSYNE_NO_EMBEDDINGS='1'),
        capture_output=True,text=True,timeout=90,cwd=root)
    assert result.returncode==0,result.stderr[-4000:]+result.stdout[-1500:]
