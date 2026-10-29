"""Exercise current WebUI routes and real read-only SQLite reader with synthetic banks."""
import hashlib,sys,sqlite3
from pathlib import Path
import pytest
BASE=Path(__file__).resolve().parents[1]
PATCH=BASE/'tests/fixtures/memdash'
sys.path[:0]=[str(BASE),str(BASE/'tests'),str(BASE/'tests/fixtures/memdash')]
import memdash_harness as H
from api import memdash_backend as backend

@pytest.fixture
def env(monkeypatch,tmp_path):
 from api import config,personal_context
 e=H.Env(monkeypatch,tmp_path,backend='local_personal')
 monkeypatch.setattr(config,'STATE_DIR',e.state)
 policy=H.hq_policy(installation={'kind':'client','name':'Iuvenis'})
 e.set_policy(policy)
 owner=personal_context.home({'email':H.ADA})/'mnemosyne/private.db'
 foreign=personal_context.home({'email':H.BOB})/'mnemosyne/private.db'
 H.make_bank(owner,owner='Ada',extra=['A completed task with an episodic summary'])
 H.make_bank(foreign,owner='Bob')
 e.owner=owner;e.foreign=foreign
 yield e
 if backend.LocalPersonalBackend._shared:
  backend.LocalPersonalBackend._shared.reader.close()
 backend.LocalPersonalBackend._shared=None
 e.close()

def test_customer_explorer_returns_owner_consolidations_graph_and_episodic_data(env):
 banks=env.banks()
 assert banks['available'] is True
 assert len(banks['stores'])==1
 assert banks['changes_available'] is False
 response=env.view('me','consolidations')
 assert response.status==200,response.body
 assert any('Ada planning summary' in str(item) for item in response.body['items'])
 graph=env.view('me','graph')
 assert graph.status==200 and graph.body['nodes'] and graph.body['edges']
 stats=env.view('me','stats')
 assert stats.status==200 and stats.body['counts']
 # Data written after the first read must be visible; no stale immutable-reader caching.
 with sqlite3.connect(env.owner) as db:
  db.execute('INSERT INTO consolidation_log(session_id,items_consolidated,summary_preview) VALUES (?,?,?)',('new-session',3,'New consolidation visible'))
 fresh=env.view('me','consolidations')
 assert fresh.status==200 and any('New consolidation visible' in str(item) for item in fresh.body['items'])

def test_foreign_bank_hidden_even_for_admin_and_reader_is_readonly(env):
 from api.memdash_scope import email_hash
 foreign_ref=env.registry.ref_for('person:'+email_hash(H.BOB)+':private')
 assert env.view(foreign_ref,'stats').status==404
 before=hashlib.sha256(env.owner.read_bytes()).hexdigest()
 response=env.view('me','consolidations')
 assert response.status==200
 assert hashlib.sha256(env.owner.read_bytes()).hexdigest()==before

def test_mode_refuses_conflicting_remote_hub(monkeypatch):
 monkeypatch.setenv('HERMES_WEBUI_MEMDASH_BACKEND','local_personal')
 monkeypatch.setenv('HERMES_WEBUI_MNEMO_URL','https://example.test')
 with pytest.raises(backend.BackendUnavailable):backend.select_backend(is_hq=False)

def test_real_fallback_consolidation_reaches_explorer(env,tmp_path):
 import subprocess,os,json
 from importlib.metadata import version,PackageNotFoundError
 try:
  installed=version('mnemosyne-memory')
 except PackageNotFoundError:
  pytest.skip('Optional real consolidation proof needs mnemosyne-memory 3.15.1')
 if installed!='3.15.1':pytest.skip('Pinned real consolidation proof targets mnemosyne-memory 3.15.1')
 # Fresh disposable bank, not the fixture's prewritten consolidation rows.
 env.owner.unlink()
 for suffix in ('-wal','-shm'):
  Path(str(env.owner)+suffix).unlink(missing_ok=True)
 isolated=tmp_path/'isolated';isolated.mkdir()
 clean_env={'PATH':os.environ['PATH'],'HOME':str(isolated),'HERMES_HOME':str(isolated/'hermes'),
  'MNEMOSYNE_DATA_DIR':str(isolated/'data'),'MNEMOSYNE_LLM_ENABLED':'false',
  'MNEMOSYNE_HOST_LLM_ENABLED':'false','MNEMOSYNE_NO_EMBEDDINGS':'1',
  'MNEMOSYNE_SKIP_EMBEDDINGS':'1','HF_HUB_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1'}
 result=subprocess.run([sys.executable,str(PATCH/'consolidate_test_bank.py'),str(env.owner)],env=clean_env,text=True,capture_output=True,timeout=60)
 assert result.returncode==0,result.stderr
 proof=json.loads(result.stdout.splitlines()[-1]);assert proof['items_consolidated']>=3
 response=env.view('me','consolidations')
 assert response.status==200,response.body
 assert any(item.get('items_consolidated',0)>=3 for item in response.body['items']),response.body
 memories=env.view('me','memories',kind='episodic')
 assert memories.status==200,memories.body
 assert 'green sample folder' in str(memories.body)
