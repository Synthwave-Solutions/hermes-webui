from collections import Counter
from scripts.backfill_personal_mnemosyne import records, text_content


def test_shared_authorship_and_synthetic_messages():
    skipped=Counter()
    data={'owner_email':'alice@example.test','participants':['bob@example.test'], 'messages':[
        {'role':'user','content':'unknown'},
        {'role':'user','author_email':'bob@example.test','content':'I prefer purple'},
        {'role':'user','author_email':'alice@example.test','content':'automatic','_source':'process_wakeup'},
        {'role':'assistant','content':'invented personal fact'}]}
    rows=list(records(data,'shared',skipped))
    assert len(rows)==1 and rows[0][0]=='bob@example.test'
    assert rows[0][1].project_shared
    assert skipped=={'unknown_author':1,'automatic_or_synthetic':1}


def test_private_owner_and_preserved_long_text():
    text='a'*20000
    rows=list(records({'owner_email':'alice@example.test','messages':[{'role':'user','content':text,'api_content':'injected'}]},'private',Counter()))
    assert len(rows)==2
    assert ''.join(r[2] for r in rows)==text
    assert rows[0][4]!=rows[1][4]
    assert not rows[0][1].project_shared


def test_past_different_author_keeps_history_shared():
    data={'owner_email':'alice@example.test','messages':[{'role':'user','content':'unknown'},
        {'role':'user','author_email':'bob@example.test','content':'mine'}]}
    skipped=Counter();rows=list(records(data,'removed-member',skipped))
    assert rows[0][0]=='bob@example.test' and rows[0][1].project_shared
    assert skipped['unknown_author']==1
    assert text_content([{'type':'image_url','image_url':'secret'},{'type':'text','text':'hello'}])=='hello'


def test_real_import_receipts_preserve_edits_and_deletions(tmp_path):
    import os, subprocess
    from pathlib import Path
    runtime=os.environ.get('HERMES_WEBUI_PYTHON',str(Path.home()/'.hermes/hermes-agent/venv/bin/python'))
    script=r'''
from pathlib import Path
import sys
from types import SimpleNamespace as NS
from api import config,personal_mnemosyne as m
from scripts.backfill_personal_mnemosyne import import_batch
config.STATE_DIR=Path(sys.argv[1])/'state'
backups=Path(sys.argv[1])/'backup';backups.mkdir()
a='alice@example.test';s=NS(session_id='one',owner_email=a,participants=[],project_shared=False,profile='bot',project_id='')
source={'message_time':1700000000}
entry=[('I prefer violet',source,'a'*64)]
with m._locked({'email':a},'private') as path, m._beam(path): pass
assert import_batch(a,s,entry,backups)['created']==1
row=m.listing({'email':a})['items'][0]
assert row['timestamp'].startswith('2023-')
m.mutate({'email':a},dict(row,operation='edit',content='I prefer red'))
assert import_batch(a,s,entry,backups)['already_processed']==1
assert m.listing({'email':a})['items'][0]['content']=='I prefer red'
row=m.listing({'email':a})['items'][0]
m.mutate({'email':a},dict(row,operation='delete'))
assert import_batch(a,s,entry,backups)['already_processed']==1
assert m.listing({'email':a})['total']==0
assert import_batch('bob@example.test',s,entry,backups)['created']==1
assert m.listing({'email':a})['total']==0
assert list(backups.glob('*.db'))
'''
    result=subprocess.run([runtime,'-c',script,str(tmp_path)],capture_output=True,text=True,timeout=45,
        env=dict(os.environ,HERMES_HOME=str(tmp_path/'hermes'),HERMES_WEBUI_STATE_DIR=str(tmp_path/'state'),MNEMOSYNE_NO_EMBEDDINGS='1'))
    assert result.returncode==0,result.stderr[-3000:]
