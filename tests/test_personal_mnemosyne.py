"""Exercise real Mnemosyne SQLite/FTS, not a mocked memory backend."""
import os
from pathlib import Path
import subprocess
import textwrap


def test_real_mnemosyne_isolation_crud_retention_and_async_sync(tmp_path):
    # Use the configured Hermes runtime, whose optional Mnemosyne plugin is
    # installed independently from the WebUI development environment.
    runtime = os.environ.get('HERMES_WEBUI_PYTHON', str(Path.home() / '.hermes/hermes-agent/venv/bin/python'))
    engine = os.environ.get('HERMES_WEBUI_AGENT_DIR', str(Path.home() / '.hermes/hermes-agent'))
    script = r'''
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, sys.argv[2])
from api import config, personal_mnemosyne as m
config.STATE_DIR = Path(sys.argv[1]) / 'state'
a={'email':'alice@example.test'}; b={'email':'bob@example.test'}
s=NS(session_id='private-one', profile='bot-one', project_id='p', owner_email=a['email'], participants=[], project_shared=False)
s2=NS(session_id='private-two', profile='bot-two', project_id='q', owner_email=a['email'], participants=[], project_shared=False)
g=NS(session_id='group-one', profile='bot-one', project_id='p', owner_email=a['email'], participants=[b['email']], project_shared=True)
g2=NS(session_id='group-two', profile='bot-one', project_id='p', owner_email=a['email'], participants=[b['email']], project_shared=True)
mid=m.remember(a,s,'My favourite colour is turquoise')
assert 'turquoise' in m.recall(a,s2,'favourite colour')
assert not m.recall(b,s,'colour')
assert not m.listing(b)['items']
assert not m.recall(a,g,'colour')
m.remember(a,g,'Group prefers orange colours')
assert 'orange' in m.recall(a,g,'colours')
assert not m.recall(a,g2,'colours')
assert 'orange' not in m.recall(a,s,'colours')
assert len(m.listing(a)['items'])==2
row=next(x for x in m.listing(a)['items'] if x['id']==mid)
try:
 m.mutate(b,dict(row,operation='edit',content='stolen'))
 raise AssertionError('Cross-user mutation accepted')
except ValueError: pass
m.mutate(a,dict(row,operation='edit',content='My favourite colour is magenta'))
assert 'magenta' in m.recall(a,s2,'colour')
assert 'turquoise' not in m.recall(a,s2,'colour')
try:
 m.mutate(a,dict(row,operation='edit',content='stale'))
 raise AssertionError('Stale edit accepted')
except m.Conflict: pass
row=next(x for x in m.listing(a)['items'] if x['id']==mid)
m.mutate(a,dict(row,operation='delete'))
assert not m.recall(a,s2,'colour')
# Old records remain until their owner deletes them, despite BEAM's TTL.
old=m.remember(a,s,'Ancient lighthouse preference')
with m._locked(a,'private') as path, m._beam(path) as mem:
 mem.conn.execute("UPDATE working_memory SET timestamp='2001-01-01' WHERE id=?",(old,));mem.conn.commit()
m.remember(a,s,'Another permanent memory')
assert 'lighthouse' in m.recall(a,s,'lighthouse')
# Real provider manager reads across bots and writes only the raw user's text.
agent=m.attach(NS(_memory_manager=None),a,s,'I prefer indigo notebooks')
manager=agent._memory_manager
assert 'lighthouse' in manager.prefetch_all('lighthouse')
manager.sync_all('INJECTED WORKSPACE SECRET', 'ASSISTANT INVENTION')
manager.raw_user_content='I prefer copper pens'
manager.sync_all('INJECTED SECOND', 'OTHER INVENTION')
assert manager.flush_pending(timeout=30)
manager.shutdown_all()
alltext=' '.join(x['content'] for x in m.listing(a)['items'])
assert 'indigo notebooks' in alltext and 'copper pens' in alltext
assert 'INJECTED' not in alltext and 'INVENTION' not in alltext
assert m.listing(a,query='indigo')['total']==1
# HTTP handlers always use authenticated identity, ignore claimed email/path,
# and check conversation membership before any bank access.
from unittest.mock import patch
from urllib.parse import urlparse
from api import routes
captured={}
def response(handler,data): captured.clear();captured.update(data);return data
with patch('api.governance.enforce._request_identity',return_value=a), patch.object(routes,'j',response):
 routes._handle_memory_read(object(),urlparse('/api/memory?section=mnemosyne&q=indigo&email=bob@example.test'))
 assert captured['total']==1
 row=captured['items'][0]
 routes._handle_memory_write(object(),dict(row,section='mnemosyne',operation='edit',content='I prefer navy notebooks',email=b['email'],path='/tmp/foreign'))
 assert captured['ok']
assert 'navy' in m.recall(a,s,'notebooks') and not m.listing(b)['items']
with patch('api.governance.enforce._request_identity',return_value=b), patch.object(routes,'j',response), patch.object(routes,'bad',lambda h,msg,status:(msg,status)):
 denied=routes._handle_memory_write(object(),dict(row,section='mnemosyne',operation='delete'))
 assert denied[1]==400
with patch('api.governance.enforce._request_identity',return_value=a), patch.object(m.pc,'session_for',side_effect=PermissionError('Not a member')), patch.object(routes,'bad',lambda h,msg,status:(msg,status)):
 assert routes._handle_memory_read(object(),urlparse('/api/memory?section=mnemosyne&session_id=foreign'))[1]==403
# Simultaneous users and same-user writes cannot cross banks or lose rows.
with ThreadPoolExecutor(max_workers=4) as pool:
 list(pool.map(lambda n:m.remember(a if n%2 else b,s,f'concurrent-{n} zebra'),range(8)))
assert m.listing(a,query='concurrent-')['total']==4
assert m.listing(b,query='concurrent-')['total']==4
for body in ({'id':mid,'bank':'../../other','operation':'delete'}, {'id':'../bad','bank':'private','operation':'delete'}):
 try: m.mutate(a,body);raise AssertionError('Traversal accepted')
 except ValueError:pass
# Symlink bank cannot disclose another actor's database.
link=m._path(b,'f'*64);link.symlink_to(m._path(a,'private'))
try: m.listing(b);raise AssertionError('Symlink accepted')
except PermissionError:pass
print('real-mnemosyne-regressions-ok')
'''
    env = dict(os.environ, HERMES_HOME=str(tmp_path/'hermes'), MNEMOSYNE_NO_EMBEDDINGS='1',
               HERMES_WEBUI_STATE_DIR=str(tmp_path/'state'))
    result = subprocess.run([runtime, '-c', textwrap.dedent(script), str(tmp_path), engine], env=env,
                            text=True, capture_output=True, timeout=90)
    assert result.returncode == 0, result.stderr[-6000:] + result.stdout[-2000:]
    assert 'real-mnemosyne-regressions-ok' in result.stdout
