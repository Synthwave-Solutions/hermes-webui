"""Native episodic writes, recall, provenance and owner lifecycle."""
import os
from pathlib import Path
import subprocess


def test_provider_failure_falls_back_but_auth_errors_do_not(monkeypatch):
    import sys
    from types import SimpleNamespace
    import pytest
    from scripts import consolidate_personal_episodes as worker

    class StatusError(Exception):
        def __init__(self, code):
            self.status_code = code

    monkeypatch.setitem(sys.modules, 'openai', SimpleNamespace(APIConnectionError=ConnectionError, APIStatusError=StatusError))
    calls = []
    def extract(*args, **kwargs):
        calls.append(kwargs.get('model'))
        if not kwargs:
            raise StatusError(503)
        return []
    monkeypatch.setattr(worker, 'extract', extract)
    assert worker.extract_episode('prompt', [], []) == []
    assert calls == [None, 'synthpulse-luna']
    monkeypatch.setattr(worker, 'extract', lambda *a, **k: (_ for _ in ()).throw(StatusError(403)))
    with pytest.raises(StatusError):
        worker.extract_episode('prompt', [], [])


def test_extraction_source_references_are_request_local(monkeypatch):
    import sys
    from types import SimpleNamespace
    from scripts import consolidate_personal_episodes as worker
    monkeypatch.setitem(sys.modules,'openai',SimpleNamespace(APIConnectionError=ConnectionError,APIStatusError=RuntimeError))
    def extract(system,batch,catalog):
        assert [r['source_id'] for r in batch]==['s0','s1']
        return [dict(source_id='s0',content='literal s1',evidence=[dict(source_id='s1',quote='literal s0')])]
    monkeypatch.setattr(worker,'extract',extract)
    for prefix in ('alice','bob'):
        result=worker.extract_episode('',[dict(source_id=prefix+'-1'),dict(source_id=prefix+'-2')],[])[0]
        assert result['source_id']==prefix+'-1' and result['evidence'][0]['source_id']==prefix+'-2'
        assert result['content']=='literal s1' and result['evidence'][0]['quote']=='literal s0'


def test_episode_pipeline(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = r'''
import sys
sys.path[:0]=sys.argv[1:]
from types import SimpleNamespace as NS
from api import personal_mnemosyne as p, personal_episodes as e
from scripts.consolidate_personal_memory import database
from scripts.consolidate_personal_episodes import run
a={'email':'alice@example.test'}; b={'email':'bob@example.test'}
s=NS(session_id='chat1',profile='default',project_id='')
text='Voor project Kobalt besluiten we eerst de import te testen; de release is nog niet klaar.'
mid=p.remember(a,s,text)
def extract(system,batch,catalog):
 return [{'content':'Voor project Kobalt is besloten de import eerst te testen. De release is volgens de gebruiker nog niet klaar.',
          'evidence':[{'source_id':batch[0]['source_id'],'quote':batch[0]['content']},
                      {'source_id':batch[0]['source_id'],'quote':'Kobalt'}]}]
r=run(extractor=extract);assert r['episodes']==1,r
assert run(extractor=lambda *args: (_ for _ in ()).throw(AssertionError('duplicate')))['processed']==0
assert 'release' in e.recall(p._read(p._path(a,p._bank(s))),'Kobalt')
assert not p.recall(b,s,'Kobalt')
agent=p.attach(NS(_memory_manager=None),a,s)
assert 'Conversation episodes' in agent._memory_manager.prefetch_all('Kobalt')
agent._memory_manager.shutdown_all()
episode=next(r for r in p.listing(a)['items'] if r['metadata'].get('kind')=='episode')
with database(p._path(a,p._bank(s))) as mem:
 assert mem.conn.execute('SELECT count(*) FROM working_memory').fetchone()[0]==1
 assert mem.conn.execute('SELECT count(*) FROM episodic_memory').fetchone()[0]==1
 key,batch=next(iter(e.batches(mem.conn).items()))
 for quote in ('Kobalt','Invented evidence that is not in any source'):
  bad=extract('',batch,[])
  bad[0]['evidence']=[dict(source_id=batch[0]['source_id'],quote=quote)]
  try:e.apply(mem,key,batch,bad);raise AssertionError('unsupported evidence accepted')
  except ValueError:pass
 assert e.apply(mem,key,batch,extract('',batch,[])*2)==1
 assert mem.conn.execute('SELECT count(*) FROM episodic_memory').fetchone()[0]==1
# Editing evidence immediately retracts the automatic summary, then regenerates.
source=next(r for r in p.listing(a)['items'] if r['id']==mid)
p.mutate(a,dict(source,operation='edit',content=text+' De import is inmiddels getest.'))
assert not any(r['metadata'].get('kind')=='episode' for r in p.listing(a)['items'])
assert run(extractor=extract)['episodes']==1
episode=next(r for r in p.listing(a)['items'] if r['metadata'].get('kind')=='episode')
p.mutate(a,dict(episode,operation='edit',content='Project Kobalt: de gebruiker heeft de import getest; de release staat nog open.'))
assert run(extractor=extract)['processed']==0
episode=next(r for r in p.listing(a)['items'] if r['metadata'].get('kind')=='episode')
p.mutate(a,dict(episode,operation='delete'))
assert run(extractor=extract)['processed']==0
assert not any(r['metadata'].get('kind')=='episode' for r in p.listing(a)['items'])
# Failed extraction never checkpoints; original working memories stay searchable.
p.remember(b,s,text)
assert run(extractor=lambda *a: (_ for _ in ()).throw(ValueError('failed')))['processed']==0
assert 'Kobalt' in p.recall(b,s,'Kobalt')
assert run(extractor=extract)['episodes']==1
# Multiple independent conversations in one provider call must remain separate.
c={'email':'charlie@example.test'}
p.remember(c,s,text)
s2=NS(session_id='chat2',profile='default',project_id='')
p.remember(c,s2,'Voor project Amber staat de presentatie gepland; de klant heeft nog niet gereageerd.')
def multi(system,batch,catalog):
 return [dict(episode_key=x['episode_key'],content=x['content'],evidence=[dict(source_id=x['source_id'],quote=x['content'])]) for x in batch]
assert run(extractor=multi)['episodes']==2
assert len([r for r in p.listing(c)['items'] if r['metadata'].get('kind')=='episode'])==2
# Parallel chunks of the same owner's bank must retain every segment.
d={'email':'delta@example.test'}
for i in range(8):
 p.remember(d,NS(session_id='parallel'+str(i),profile='default',project_id=''),text+' Segment '+str(i))
def partial_multi(system,batch,catalog):
 result=multi(system,batch,catalog)
 for source,proposal in zip(batch,result):
  if source['content'].endswith('Segment 0'):
   proposal['evidence'][0]['quote']='Invented evidence with no supporting source'
 return result
result=run(extractor=partial_multi,workers=4)
assert result['processed']==7 and result['episodes']==7,result
assert run(extractor=extract)['episodes']==1
assert len([r for r in p.listing(d)['items'] if r['metadata'].get('kind')=='episode'])==8
from api.third_party import mnemosyne_dashboard as md
md.allow_paths([p._path(c,p._bank(s))])
dashboard=md.DashboardStore(p._path(c,p._bank(s)))
assert dashboard.stats()['counts']['episodic_memory']==2
assert dashboard.stats()['counts']['personal_episodes']==2
assert dashboard.stats()['counts']['consolidation_log']==2
assert len(dashboard.consolidations())==2
assert len(dashboard.global_search('Kobalt')['consolidations'])==1
md.allow_paths([])
assert not any('Amber' in r['content'] for r in p.listing(a)['items'])
# A pinned/deleted fact cannot be resurrected through the older episode.
from api import personal_consolidation as f
with database(p._path(c,p._bank(s))) as mem:
 source=next(x for x in f.sources(mem.conn) if 'Kobalt' in x['content'])
 proposal=dict(topic='kobalt_status',category='project',content='Project Kobalt: de release is volgens de gebruiker nog niet klaar.',confidence=.99,
               evidence=[dict(source_id=source['source_id'],quote=source['content'])])
 assert f.apply(mem,[proposal],[source])==1
fact=next(r for r in p.listing(c)['items'] if r['metadata'].get('kind')=='consolidated')
p.mutate(c,dict(fact,operation='delete'))
assert not any('Kobalt' in r['content'] for r in p.listing(c)['items'] if r['metadata'].get('kind')=='episode')
with database(p._path(c,p._bank(s))) as mem:
 assert not e.recall(mem.conn,'Kobalt')
 key,batch=next(iter(e.batches(mem.conn).items()))
source=next(r for r in p.listing(c)['items'] if r['id']==batch[0]['source_id'])
p.mutate(c,dict(source,operation='edit',content='Project Amber: de klant heeft nu wel gereageerd; de presentatie gaat door.'))
with database(p._path(c,p._bank(s))) as mem:
 try:e.apply(mem,key,batch,[]);raise AssertionError('stale episode accepted')
 except ValueError:pass
'''
    result = subprocess.run([os.environ['HERMES_WEBUI_PYTHON'], '-c', script, str(root),
        os.environ.get('HERMES_WEBUI_AGENT_DIR', str(Path.home()/'.hermes/hermes-agent'))],
        env=dict(os.environ, HERMES_HOME=str(tmp_path/'home'), HERMES_WEBUI_STATE_DIR=str(tmp_path/'state'), MNEMOSYNE_NO_EMBEDDINGS='1'),
        capture_output=True, text=True, timeout=90, cwd=root)
    assert result.returncode == 0, result.stderr[-5000:] + result.stdout[-1500:]
