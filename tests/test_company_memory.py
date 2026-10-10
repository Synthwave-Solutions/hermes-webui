"""Real BEAM/FTS consolidation with real governance decisions and isolated state."""
import os
from pathlib import Path
import subprocess


def test_company_consolidation_governance_crud_and_sources(tmp_path):
    runtime=os.environ.get('HERMES_WEBUI_PYTHON',str(Path.home()/'.hermes/hermes-agent/venv/bin/python'))
    engine=os.environ.get('HERMES_WEBUI_AGENT_DIR',str(Path.home()/'.hermes/hermes-agent'))
    script=r'''
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from urllib.parse import urlparse
# The WebUI root goes on sys.path by absolute path (as the service script does):
# newer engines drop the cwd entry ('') from sys.path when run_agent is imported.
sys.path.insert(0,sys.argv[3])
sys.path.insert(0,sys.argv[2])
from api import config,company_memory as c,personal_mnemosyne as p,personal_context as pc,routes
from api.governance import loader
from scripts.consolidate_company_memory import discover,run
config.STATE_DIR=Path(sys.argv[1])/'state'
policy=loader.parse_governance_policy({'version':1,'mode':'enforce','bootstrap_admins':['admin@example.test'],'users':{'member@example.test':{'roles':['member']}}})
admin={'email':'admin@example.test'};member={'email':'member@example.test'}
s=NS(session_id='chat',owner_email=member['email'],participants=[],project_shared=False,profile='bot',project_id='')
with patch.object(loader,'get_policy',return_value=policy):
 assert c.is_admin(admin) and not c.is_admin(member)
 for action in (lambda:c.listing(member),lambda:c.mutate(member,{}),lambda:pc.ensure_actor_path(member,c.path())):
  try:action();raise AssertionError('Member gained admin access')
  except PermissionError:pass
 assert c.recall('company')==''
 p.remember(member,s,'At Synthwave our company uses Notion to document standard operating processes.')
 sources=discover();source=sources[0]
 def proposal(content='Synthwave documenteert standaardwerkprocessen in Notion.',topic='process_documentation',quote=None):
  return {'topic':topic,'category':'process','scope':'company','confidence':.97,'content':content,
          'evidence':[{'source_id':source['source_id'],'quote':quote or source['content']}]}
 # Unsupported or sensitive claims never reach the shared bank.
 assert c.validate_proposals([proposal(quote='Invented unsupported source')],{source['source_id']:source})==[]
 assert c.validate_proposals([proposal(content='My private medical salary information')],{source['source_id']:source})==[]
 observation=proposal(content='Waargenomen werkwijze: processen worden in Notion vastgelegd.')
 observation['kind']='observed_practice'
 assert c.validate_proposals([observation],{source['source_id']:source})==[]
 second=dict(source,source_id='other-source',origin_actor='another-person',chat='different-chat')
 observation['evidence'].append({'source_id':'other-source','quote':second['content']})
 assert len(c.validate_proposals([observation],{source['source_id']:source,'other-source':second}))==1
 assert run(1,extractor=lambda batch,catalog:[proposal()])['updated_topics']==1
 assert 'Notion' in c.recall('Notion')
 # Another person's agent can recall only the shared fact, not the author's
 # complete personal statement, even inside a shared conversation.
 other={'email':'other@example.test'}
 group=NS(session_id='other-group',owner_email=other['email'],participants=['third@example.test'],project_shared=True)
 agent=p.attach(NS(_memory_manager=None),other,group)
 recalled=agent._memory_manager.prefetch_all('Notion')
 assert 'Company knowledge' in recalled and 'documenteert' in recalled
 assert source['content'] not in recalled
 agent._memory_manager.shutdown_all()
 assert run(1,extractor=lambda b,c: (_ for _ in ()).throw(AssertionError('Already processed')))['processed']==0
 row=c.listing(admin)['items'][0]
 assert row['sources']==1 and not row['manual']
 c.mutate(admin,dict(row,operation='edit',content='Synthwave documenteert processen in de centrale Notion-kennisbank.'))
 c.apply_proposals([proposal()],sources)
 assert 'centrale' in c.recall('Notion')
 try:c.mutate(admin,dict(row,operation='delete'));raise AssertionError('Stale revision accepted')
 except p.Conflict:pass
 row=c.listing(admin)['items'][0];c.mutate(admin,dict(row,operation='delete'))
 assert not c.recall('Notion')
 c.apply_proposals([proposal(topic='renamed_documentation')],sources)
 assert c.listing(admin)['total']==0
 # A different fact with a new source can be published, then auto-retracted
 # when its original personal source is deleted.
 mid=p.remember(member,s,'At Synthwave our company uses Git for version control of software.')
 new=next(x for x in discover() if 'version control' in x['content'])
 fact={'topic':'version_control','category':'tools','scope':'company','confidence':.99,'content':'Synthwave gebruikt Git voor versiebeheer.',
       'evidence':[{'source_id':new['source_id'],'quote':new['content']}]}
 c.apply_proposals([fact],[new]);assert 'Git' in c.recall('Git')
 row=next(x for x in p.listing(member)['items'] if x['id']==mid)
 p.mutate(member,dict(row,operation='delete'))
 run(1,extractor=lambda batch,catalog:[])
 assert not c.recall('Git')
 # HTTP section dispatch still denies a member even with spoofed identity fields.
 with patch('api.governance.enforce._request_identity',return_value=member),patch.object(routes,'bad',lambda h,msg,status:status):
  assert routes._handle_memory_read(object(),urlparse('/api/memory?section=company'))==403
  assert routes._handle_memory_write(object(),{'section':'company','email':admin['email'],'operation':'delete'})==403
 # Invalid model responses are not checkpointed as successful.
 before=len(c.listing(admin)['items'])
 try:c.apply_proposals({'invalid':1},sources);raise AssertionError('Invalid response accepted')
 except ValueError:pass
 assert len(c.listing(admin)['items'])==before
print('company-memory-ok')
'''
    result=subprocess.run([runtime,'-c',script,str(tmp_path),engine,str(Path(__file__).resolve().parents[1])],text=True,capture_output=True,timeout=80,
        env=dict(os.environ,HERMES_HOME=str(tmp_path/'hermes'),HERMES_WEBUI_STATE_DIR=str(tmp_path/'state'),MNEMOSYNE_NO_EMBEDDINGS='1'))
    assert result.returncode==0,result.stderr[-4000:]+result.stdout[-1000:]
