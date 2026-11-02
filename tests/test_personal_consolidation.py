"""Evidence, identity, correction, deletion and actual provider recall contracts."""

import os
from pathlib import Path
import subprocess


def test_consolidation_lifecycle_and_isolation(tmp_path):
    runtime = os.environ["HERMES_WEBUI_PYTHON"]
    root = Path(__file__).resolve().parents[1]
    script = r"""
import sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2])
from api import personal_mnemosyne as p,personal_consolidation as f
from scripts.consolidate_personal_memory import run,database
alice={'email':'alice@example.test'};bob={'email':'bob@example.test'}
s=NS(session_id='private-chat',profile='default',project_id='')
mid=p.remember(alice,s,'Ik ontvang mijn rapporten bij voorkeur in het Nederlands.')
path=p._path(alice,p._bank(s))
with database(path) as mem:source=f.sources(mem.conn)[0]
def proposal(content='Deze persoon ontvangt rapporten bij voorkeur in het Nederlands.'):
 return {'topic':'report_language','category':'preference','content':content,'confidence':.99,
         'evidence':[{'source_id':source['source_id'],'quote':source['content']}]}
assert run(extractor=lambda *args:[proposal()])['updated_topics']==1
assert 'Nederlands' in p.recall(alice,s,'Wat zijn mijn voorkeuren?')
assert not p.recall(bob,s,'rapporten Nederlands')
# Agent's actual provider prefetch must use the consolidated memory.
a=p.attach(NS(_memory_manager=None),alice,s)
assert 'Nederlands' in a._memory_manager.prefetch_all('voorkeuren')
a._memory_manager.shutdown_all()
assert run(extractor=lambda *args: (_ for _ in ()).throw(AssertionError('reprocessed')))['processed']==0
# User editing a derived fact pins it; subsequent auto updates cannot overwrite it.
row=next(x for x in p.listing(alice)['items'] if x['metadata'].get('kind')=='consolidated')
p.mutate(alice,dict(row,operation='edit',content='Deze persoon ontvangt rapporten bij voorkeur in het Engels.'))
with database(path) as mem:assert f.apply(mem,[proposal()],[source])==0
assert 'Engels' in p.recall(alice,s,'voorkeuren')
row=next(x for x in p.listing(alice)['items'] if x['metadata'].get('kind')=='consolidated')
p.mutate(alice,dict(row,operation='delete'))
with database(path) as mem:
 q=proposal();q['topic']='renamed_language';assert f.apply(mem,[q],[source])==0
assert not p.recall(alice,s,'voorkeuren')
# Invalid evidence is rejected; deletion of original evidence retracts a fact immediately.
mid2=p.remember(bob,s,'Ik ontvang iedere rapportage graag als bewerkbaar document.')
bpath=p._path(bob,p._bank(s))
with database(bpath) as mem:
 source=f.sources(mem.conn)[0];bad=proposal();bad['evidence'][0]['quote']='fabricated quotation';assert f.apply(mem,[bad],[source])==0
 assert f.apply(mem,[proposal('Deze persoon ontvangt rapporten graag als bewerkbaar document.')],[source])==1
assert 'bewerkbaar' in p.recall(bob,s,'voorkeuren')
row=next(x for x in p.listing(bob)['items'] if x['id']==mid2)
p.mutate(bob,dict(row,operation='delete'))
assert 'bewerkbaar' not in p.recall(bob,s,'voorkeuren')
# Network extraction raced with a source edit: do not publish/checkpoint stale text.
mid3=p.remember(bob,s,'Ik ontvang mijn presentaties graag in het Nederlands.')
with database(bpath) as mem:source=next(x for x in f.sources(mem.conn) if x['source_id']==mid3)
row=next(x for x in p.listing(bob)['items'] if x['id']==mid3)
p.mutate(bob,dict(row,operation='edit',content='Ik ontvang mijn presentaties graag in het Engels.'))
with database(bpath) as mem:
 try:f.apply(mem,[proposal()],[source]);raise AssertionError('Stale source accepted')
 except ValueError:pass
# Shared-chat bank cannot leak into the same person's private context.
shared=NS(session_id='shared-chat',profile='default',project_id='',project_shared=True,participants=['bob@example.test'])
p.remember(alice,shared,'Voor project Kobalt leveren wij iedere vrijdag een bewerkbare planning.')
assert 'Kobalt' not in p.recall(alice,s,'Kobalt')
# Repeated quotes from a single source must not violate evidence uniqueness.
charlie={'email':'charlie@example.test'}
text='Ik ontvang mijn rapporten bij voorkeur in het Nederlands.'
p.remember(charlie,s,text)
with database(p._path(charlie,p._bank(s))) as mem:
 source=f.sources(mem.conn)[0]
 q=proposal(text);q['evidence'].append(dict(q['evidence'][0]))
 assert f.apply(mem,[q],[source])==1
 derived=mem.conn.execute('SELECT memory_id FROM personal_facts').fetchone()[0]
 assert derived!=source['source_id']
 assert len(f.sources(mem.conn))==1  # Derived rows never replace original evidence.
 assert mem.conn.execute('SELECT count(*) FROM personal_evidence').fetchone()[0]==1
# A failed bank cannot starve another bank; worker threads keep ownership separate.
p.remember(alice,s,'Voortaan wil ik iedere presentatie als bewerkbaar bestand ontvangen.')
p.remember(bob,s,'Mijn vaste voorkeur is om presentaties in het Engels te ontvangen.')
def mixed_extractor(system,batch,catalog):
 if any('Voortaan wil' in x['content'] for x in batch):raise ValueError('simulated provider failure')
 return []
result=run(max_batches=50,extractor=mixed_extractor,workers=3)
assert result['failed_banks']==1 and result['processed']>0
# Incomplete model output preserves the checkpoint and reduces the next payload.
with database(p._path(alice,p._bank(s))) as mem:
 checkpoint=mem.conn.execute('SELECT count(*) FROM personal_sources').fetchone()[0]
result=run(max_batches=50,extractor=lambda *args: (_ for _ in ()).throw(ValueError('Incomplete consolidation response')),batch_chars=96000)
assert result['processed']==0 and result['failed_banks']==1
with database(p._path(alice,p._bank(s))) as mem:
 assert mem.conn.execute('SELECT count(*) FROM personal_sources').fetchone()[0]==checkpoint
 assert dict(mem.conn.execute('SELECT * FROM personal_state'))['batch_chars']=='48000'
print('personal-consolidation-ok')
"""
    env = dict(
        os.environ,
        HERMES_HOME=str(tmp_path / "home"),
        HERMES_WEBUI_STATE_DIR=str(tmp_path / "state"),
        MNEMOSYNE_NO_EMBEDDINGS="1",
    )
    result = subprocess.run(
        [
            runtime,
            "-c",
            script,
            str(root),
            os.environ.get(
                "HERMES_WEBUI_AGENT_DIR", str(Path.home() / ".hermes/hermes-agent")
            ),
        ],
        capture_output=True,
        text=True,
        timeout=90,
        env=env,
        cwd=root,
    )
    assert result.returncode == 0, result.stderr[-4000:] + result.stdout[-1000:]
