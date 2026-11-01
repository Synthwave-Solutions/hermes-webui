import pytest
from api import bot_metadata, bot_scout, cron_bots
from tests.test_bot_scout import scout_env, ALICE, BOB, _revision, _jobs

@pytest.mark.parametrize('frequency,expected', [('hourly','15 * * * *'),('3h','15 1,4,7,10,13,16,19,22 * * *'),('6h','15 1,7,13,19 * * *'),('12h','15 7,19 * * *'),('daily','15 7 * * *'),('weekdays','15 7 * * 1-5')])
def test_schedule(frequency, expected):
    assert bot_scout.schedule_for('07:15', frequency) == expected

def test_inheritance_and_person_isolation(scout_env):
    def save(caller, **body):
        return bot_scout.apply('radar', dict(revision=_revision('radar'), **body), caller, editor=caller==ALICE)
    save(ALICE, enabled=True, default_frequency='3h')
    save(BOB, enabled=True, frequency='hourly')
    save(ALICE, default_frequency='6h')
    scout=bot_metadata.read_profile('radar')['bot']['scout']
    assert bot_metadata.scout_person_view(scout, ALICE)['frequency']=='6h'
    assert bot_metadata.scout_person_view(scout, BOB)['frequency']=='hourly'
    save(BOB, frequency='')
    assert bot_metadata.read_profile('radar')['bot']['scout']['people'][BOB]=={'enabled':True}
    with pytest.raises(bot_scout.ScoutError): save(BOB, default_frequency='hourly')
    with pytest.raises(ValueError): save(BOB, frequency='* * * * *')

def test_scout_link_survives_roundtrip():
    link={'job_id':'abc','profile':'radar','kind':'scout'}
    assert cron_bots.normalize_job_link(link)==link
    assert cron_bots.job_chat_title({'managed_by':'scout','name':'Scout · Alice'})=='Scout · Alice'
    assert cron_bots.job_chat_title({'name':'Other'}).startswith('🗓')

@pytest.fixture
def collector(monkeypatch):
    import importlib.util, sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/'scripts'/'scout'
    monkeypatch.syspath_prepend(str(root))
    spec=importlib.util.spec_from_file_location('scout_collector_cadence',root/'scout_collect.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def test_calendar_is_scoped_bounded_and_read_only(collector, monkeypatch):
    import json,time
    from types import SimpleNamespace
    calls=[]
    monkeypatch.setattr(collector.shutil,'which',lambda _: '/bin/gws-hermes')
    def run(args,**kwargs):
        calls.append((args,kwargs))
        return SimpleNamespace(returncode=0,stdout=json.dumps({'items':[
            {'summary':'Prep meeting','start':{'dateTime':'2026-10-23T09:00:00+02:00'},'htmlLink':'https://calendar.google.com/event'},
            {'summary':'Cancelled','status':'cancelled'},
            {'summary':'Declined','attendees':[{'self':True,'responseStatus':'declined'}]}]}))
    monkeypatch.setattr(collector.subprocess,'run',run)
    context={'person':'alice@synthwave.solutions','person_explicit':True}
    text,notes=collector.collect_calendar(context,10000,time.monotonic()+50)
    args,kwargs=calls[0]
    assert args[1:6]==['--as',context['person'],'calendar','events','list']
    params=json.loads(args[-1]); assert params['calendarId']=='primary' and params['maxResults']==40
    assert kwargs['timeout']<=18 and not kwargs.get('shell')
    assert 'Prep meeting' in text and 'Cancelled' not in text and 'Declined' not in text
    assert not notes
    text,notes=collector.collect_calendar({'person':context['person']},10000,time.monotonic()+50)
    assert not text and notes and len(calls)==1

def test_calendar_failure_is_not_empty_calendar(collector,monkeypatch):
    import time
    from types import SimpleNamespace
    monkeypatch.setattr(collector.shutil,'which',lambda _: '/bin/gws-hermes')
    monkeypatch.setattr(collector.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=1,stdout='',stderr='sensitive token'))
    text,notes=collector.collect_calendar({'person':'alice@synthwave.solutions','person_explicit':True},1,time.monotonic()+30)
    assert not text and notes and 'sensitive' not in str(notes)

def test_proactive_sweep_without_fresh_events_and_retry_debounce(collector):
    from types import SimpleNamespace
    assert collector.proactive_due(SimpleNamespace(get_meta=lambda _:None),10000)
    assert not collector.proactive_due(SimpleNamespace(get_meta=lambda _:'9900'),10000)
    assert collector.proactive_due(SimpleNamespace(get_meta=lambda _:'6400'),10000)

def test_scout_form_renders_inheritance_and_personal_override():
    import subprocess
    from pathlib import Path
    js=(Path(__file__).resolve().parents[1]/'static/panels.js').read_text()
    helpers=js[js.index('function _scoutFrequencyOptions'):js.index('function _paintBotScoutTopics')]
    code="""
const esc=x=>String(x),t=x=>x,_botKind=p=>'bot';
const _BOT_SCOUT_PROMPT_MAX=2000,_BOT_SCOUT_TOPIC_MAX=80;
let _botScoutSelected={bot:'',person:''};
"""+helpers+"""
const html=_botScoutCardHtml({bot_kind:'bot',bot_editable:true,bot:{scout:{frequency:'6h'}},scout_me:{enabled:true,own_frequency:true,frequency:'hourly'}});
if(html.includes('botScoutSpace') || html.includes('Google Chat'))throw Error('provider-specific UI');
if(!html.includes('id="botScoutFrequency"') || !html.includes('id="botScoutDefaultFrequency"'))throw Error('missing selectors');
if(!html.includes('value="hourly" selected') || !html.includes('value="6h" selected'))throw Error('wrong values');
const personal=_botScoutCardHtml({bot_kind:'bot',bot_editable:false,scout_me:{enabled:false}});
if(personal.includes('id="botScoutDefaultFrequency"') || !personal.includes('value="" selected'))throw Error('inheritance/editor');
_botScoutSelected={bot:'radar',person:'bob@example.com'};
const admin=_botScoutCardHtml({name:'radar',bot_kind:'bot',scout_manageable:true,bot_editable:false,scout_me:{enabled:false},scout_people_options:[{email:'bob@example.com',enabled:true,prompt:'Prepare quotes'}]});
if(!admin.includes('value="bob@example.com" selected') || !admin.includes('Prepare quotes') || !admin.includes('loadBotScoutPeople()'))throw Error('admin selected person');

"""
    subprocess.run(['node','-e',code],check=True,capture_output=True,text=True)

def test_email_reads_owned_mail_without_writes(collector,monkeypatch):
    import time,json
    from types import SimpleNamespace
    calls=[]
    monkeypatch.setattr(collector.shutil,'which',lambda _: '/bin/gmail')
    def run(args,**kwargs):
        calls.append(args)
        data={'messages':[{'id':'a123','subject':'Meeting','unread':True}]} if args[3]=='list' else {'body':'Prepare proposal'}
        return SimpleNamespace(returncode=0,stdout=json.dumps(data))
    monkeypatch.setattr(collector.subprocess,'run',run)
    text,notes=collector.collect_email({'person':'alice@synthwave.solutions','person_explicit':True},time.monotonic()+20)
    assert 'Prepare proposal' in text and notes
    assert [a[3] for a in calls]==['list','read']
    assert all(a[1:3]==['--as','alice@synthwave.solutions'] for a in calls)
    collector.collect_email({'person':'bob@synthwave.solutions'},time.monotonic()+20)
    assert len(calls)==2

def test_scout_remains_an_agent_with_skills(scout_env):
    from api.config import get_config_for_profile_home
    from cron.scheduler import _resolve_cron_enabled_toolsets
    result=bot_scout.apply('radar',{'enabled':True,'revision':_revision('radar')},ALICE)
    job=_jobs(scout_env.homes['radar'])[0]
    assert job['no_agent'] is False
    assert 'skills' in _resolve_cron_enabled_toolsets(job, get_config_for_profile_home(scout_env.homes['radar']))
    assert 'skills_list' in job['prompt'] and 'skill_view' in job['prompt']

def test_rolling_chats_include_answers_without_advancing_event_cursor(collector,monkeypatch,tmp_path):
    import json
    from types import SimpleNamespace
    state=tmp_path/'webui';sessions=state/'sessions';sessions.mkdir(parents=True)
    now=1000000;person='alice@example.com'
    row={'session_id':'own','profile':'radar','owner_email':person,'updated_at':now-100,'title':'Client prep'}
    data={**row,'messages':[{'role':'user','content':'Prepare the meeting','timestamp':now-200},
                           {'role':'assistant','content':'Draft ready; budget still unresolved','timestamp':now-100},
                           {'role':'tool','content':'SECRET TOOL OUTPUT'}]}
    (sessions/'_index.json').write_text(json.dumps([row]))
    (sessions/'own.json').write_text(json.dumps(data))
    monkeypatch.setattr(collector,'webui_state_dir',lambda ctx:state)
    writes=[];led=SimpleNamespace(get_meta=lambda _:str(now),set_meta=lambda *args:writes.append(args))
    ctx={'person':person,'person_explicit':True,'profile':'radar'}
    assert collector.collect_chats(ctx,led,now)==[]
    result=collector.collect_chats(ctx,led,now,context=True)
    assert len(result)==1 and 'budget still unresolved' in result[0]['summary']
    assert 'Prepare the meeting' in result[0]['summary'] and 'SECRET TOOL' not in str(result)
    assert writes==[]
    # Stale index must never override changed ownership or sharing.
    for changed in ({'owner_email':'bob@example.com'},{'share_token':'shared'}, {'profile':'other'}, {'project_shared':True}):
        (sessions/'own.json').write_text(json.dumps({**data,**changed}))
        assert collector.collect_chats(ctx,led,now,context=True)==[]

def test_cross_bot_context_requires_opt_in_and_source_access(collector,tmp_path):
    import yaml
    root=tmp_path/'hermes';home=root/'profiles'/'radar';home.mkdir(parents=True)
    person='alice@example.com';ctx={'home':home,'root':root,'profile':'radar','person':person}
    rows=[{'profile':n,'owner_email':person} for n in ('other','denied','managed','default')]
    (root/'dashboard-governance.yaml').write_text(yaml.safe_dump({'mode':'enforce','default_effect':'deny',
        'users':{person:{'grants':{'profiles':['other']}}}}))
    def consent(value):
        (home/'profile.yaml').write_text(yaml.safe_dump({'ui_meta':{'hermes-bots':{'scout':{
            'people':{person:{'enabled':True,'cross_bot_context':value}}}}}}))
    consent(False)
    assert collector.cross_bot_profiles(ctx,rows)==set()
    consent(True)
    assert collector.cross_bot_profiles(ctx,rows)=={'other','default'}
    managed=root/'profiles'/'managed';managed.mkdir()
    (managed/'profile.yaml').write_text(yaml.safe_dump({'synpulse_builder':{'owner_email':person}}))
    assert 'managed' in collector.cross_bot_profiles(ctx,rows)
    (managed/'profile.yaml').write_text(yaml.safe_dump({'synpulse_builder':{'owner_email':'bob@example.com'}}))
    assert 'managed' not in collector.cross_bot_profiles(ctx,rows)
    (root/'dashboard-governance.yaml').write_text('broken: [')
    assert collector.cross_bot_profiles(ctx,rows)==set()

def test_other_bot_context_stays_owned_and_attributed(collector,monkeypatch,tmp_path):
    import json
    from types import SimpleNamespace
    state=tmp_path/'webui';sessions=state/'sessions';sessions.mkdir(parents=True)
    now=1000000;person='alice@example.com'
    rows=[]
    for sid,profile,owner in [('mine','other',person),('someone','other','bob@example.com'),('blocked','denied',person)]:
        row={'session_id':sid,'profile':profile,'owner_email':owner,'updated_at':now-10,'title':sid}
        rows.append(row)
        (sessions/(sid+'.json')).write_text(json.dumps({**row,'messages':[{'role':'user','content':sid,'timestamp':now-10}]}))
    (sessions/'_index.json').write_text(json.dumps(rows))
    monkeypatch.setattr(collector,'webui_state_dir',lambda ctx:state)
    monkeypatch.setattr(collector,'cross_bot_profiles',lambda ctx,rows:{'other'})
    ctx={'person':person,'person_explicit':True,'profile':'radar'}
    led=SimpleNamespace(get_meta=lambda _:None,set_meta=lambda *args:None)
    result=collector.collect_chats(ctx,led,now,context=True)
    assert len(result)==1 and result[0]['profile']=='other' and 'Chat met other' in result[0]['title']
    assert collector.collect_chats(ctx,led,now)==[]
