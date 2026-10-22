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
"""+helpers+"""
const html=_botScoutCardHtml({bot_kind:'bot',bot_editable:true,bot:{scout:{frequency:'6h'}},scout_me:{enabled:true,own_frequency:true,frequency:'hourly'}});
if(!html.includes('id="botScoutFrequency"') || !html.includes('id="botScoutDefaultFrequency"'))throw Error('missing selectors');
if(!html.includes('value="hourly" selected') || !html.includes('value="6h" selected'))throw Error('wrong values');
const personal=_botScoutCardHtml({bot_kind:'bot',bot_editable:false,scout_me:{enabled:false}});
if(personal.includes('id="botScoutDefaultFrequency"') || !personal.includes('value="" selected'))throw Error('inheritance/editor');
"""
    subprocess.run(['node','-e',code],check=True,capture_output=True,text=True)
