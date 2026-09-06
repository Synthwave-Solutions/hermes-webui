from types import SimpleNamespace
import pytest
from api import group_chat


def test_selection_is_one_explicit_member_and_actor_authorized(monkeypatch):
    session=SimpleNamespace(bot_participants=['writer','reviewer'])
    calls=[]
    def allowed(actor,bot): calls.append((actor,bot));return actor=='alice@example.test'
    monkeypatch.setattr(group_chat,'bot_allowed',allowed)
    assert group_chat.selected_bot(session,'@reviewer Review this','alice@example.test')=='reviewer'
    with pytest.raises(ValueError):group_chat.selected_bot(session,'Please work','alice@example.test')
    with pytest.raises(ValueError):group_chat.selected_bot(session,'@admin Work','alice@example.test')
    with pytest.raises(ValueError):group_chat.selected_bot(session,'@writer Work','other@example.test')
    assert calls==[('alice@example.test','reviewer'),('other@example.test','writer')]


def test_one_bot_has_unambiguous_default(monkeypatch):
    monkeypatch.setattr(group_chat,'bot_allowed',lambda actor,bot:True)
    assert group_chat.selected_bot(SimpleNamespace(bot_participants=['writer']),'Hello','a@example.test')=='writer'
    assert group_chat.selected_bot(SimpleNamespace(bot_participants=[]),'Hello','a@example.test') is None


def test_bot_validation_existing_profile_and_grant(tmp_path,monkeypatch):
    from api import profiles
    (tmp_path/'config.yaml').write_text('model: {}')
    monkeypatch.setattr(profiles,'get_hermes_home_for_profile',lambda name:tmp_path)
    monkeypatch.setattr(group_chat,'bot_allowed',lambda actor,bot:bot=='writer')
    assert group_chat.validate_bots(['writer'],'a@example.test')==['writer']
    with pytest.raises(ValueError):group_chat.validate_bots(['reviewer'],'a@example.test')
    with pytest.raises(ValueError):group_chat.validate_bots(['../writer'],'a@example.test')
    with pytest.raises(ValueError):group_chat.validate_bots(['writer']*7,'a@example.test')


def test_group_bypasses_adapter_and_keeps_sender(monkeypatch):
    from api import routes, runtime_adapter
    monkeypatch.setattr(runtime_adapter, 'runtime_adapter_enabled', lambda: True)
    monkeypatch.setattr(runtime_adapter, 'runtime_adapter_runner_enabled', lambda: True)
    calls=[]
    monkeypatch.setattr(routes, '_start_chat_stream_for_session', lambda s,**kw: calls.append((s,kw)) or {'ok':True})
    session=SimpleNamespace(bot_participants=['writer','reviewer'], profile='conversation')
    for bot in ['writer','reviewer']:
        assert routes._start_run(session,msg='@'+bot+' Hello',attachments=[],workspace='/tmp',model=None,
            model_provider=None,normalized_model=None,source='webui',route='/api/chat/start',sender_email='alice@example.test')=={'ok':True}
    assert len(calls)==2
    assert all(call[1]['sender_email']=='alice@example.test' for call in calls)
    assert session.profile=='conversation'


def test_bot_attribution_two_turns_preserves_prior_author():
    from api.streaming import _stamp_group_bot_author
    session=SimpleNamespace(profile='conversation',messages=[{'role':'user','content':'@writer First'}, {'role':'assistant','content':'A'}])
    _stamp_group_bot_author(session,'@writer First','writer')
    session.messages += [{'role':'user','content':'@reviewer Second'}, {'role':'assistant','content':'B'}]
    _stamp_group_bot_author(session,'@reviewer Second','reviewer')
    assert [m['bot_profile'] for m in session.messages if m['role']=='assistant']==['writer','reviewer']
    assert session.profile=='conversation'


def test_bot_participants_roundtrip(tmp_path, monkeypatch):
    from api import models
    monkeypatch.setattr(models, 'SESSION_DIR', tmp_path)
    session=models.Session(session_id='group-bots',bot_participants=['writer','reviewer'])
    session.save(skip_index=True)
    assert models.Session.load('group-bots').bot_participants==['writer','reviewer']
    assert session.compact()['bot_participants']==['writer','reviewer']


def test_dispatch_two_bots_keeps_conversation_and_actor(monkeypatch):
    from api import routes, turn_journal
    session=SimpleNamespace(session_id='bot-dispatch', profile='conversation', bot_participants=['writer','reviewer'],
        participants=['alice@example.test'], owner_email='owner@example.test', pending_started_at=1, title='Group')
    monkeypatch.setattr(group_chat,'bot_allowed',lambda actor,bot:actor=='alice@example.test')
    monkeypatch.setattr(routes,'_read_profile_model_config',lambda s,p:('custom:router',s.profile+'-model',{}))
    monkeypatch.setattr(routes,'_active_run_stream_for_session',lambda sid:None)
    monkeypatch.setattr(routes,'_is_hidden_empty_session',lambda s:False)
    monkeypatch.setattr(routes,'_prepare_chat_start_session_for_stream',lambda *a,**kw:None)
    monkeypatch.setattr(turn_journal,'append_turn_journal_event',lambda *a,**kw:{})
    monkeypatch.setattr(routes,'set_last_workspace',lambda *a:None)
    monkeypatch.setattr(routes,'register_stream_owner',lambda *a:None)
    monkeypatch.setattr(routes,'webui_gateway_chat_enabled',lambda cfg:True)
    monkeypatch.setattr(routes,'get_config',lambda:{})
    launched=[]
    class Thread:
        def __init__(self,**kw):launched.append(kw)
        def start(self):pass
    monkeypatch.setattr(routes.threading,'Thread',Thread)
    for bot in ['writer','reviewer']:
        result=routes._start_chat_stream_for_session(session,msg='@'+bot+' Hello',attachments=[],workspace='/tmp',model='old',
            model_provider='old',normalized_model='old',sender_email='alice@example.test')
        assert result['effective_model']==bot+'-model'
        routes.STREAMS.pop(result['stream_id'],None)
    assert len(launched)==2
    assert [x['kwargs']['execution_profile'] for x in launched]==['writer','reviewer']
    assert all(x['kwargs']['sender_email']=='alice@example.test' and x['target']==routes._run_agent_streaming for x in launched)
    assert session.profile=='conversation'


def test_worker_membership_recheck_refuses_removed_sender():
    session=SimpleNamespace(owner_email='owner@example.test',participants=['alice@example.test'])
    group_chat.require_turn_membership(session,'alice@example.test')
    session.participants=[]
    with pytest.raises(PermissionError):group_chat.require_turn_membership(session,'alice@example.test')
    group_chat.require_turn_membership(session,'owner@example.test')
    with pytest.raises(PermissionError):group_chat.require_turn_membership(session,None)
