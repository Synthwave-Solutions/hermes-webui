"""Handoffs retain chat identity, permission ceilings and at-most-once dispatch."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest
from api import bot_delegation as handoff, config, models, routes
from api.governance import continuation, loader, agent_context
from tests.test_continuation_authority import world, POLICY, EMAIL, IDENTITY  # noqa: F401


@pytest.fixture
def chat(world, monkeypatch):
    policy = deepcopy(POLICY)
    policy['roles']['member']['grants']['profiles'] = ['default', 'reviewer', 'research']
    world.current['policy'] = loader.parse_governance_policy(policy)
    world.session.bot_participants = ['default', 'reviewer', 'research']
    world.session.active_stream_id = 'origin'
    monkeypatch.setattr(config, 'STATE_DIR', world.root)
    monkeypatch.setattr(models, 'get_session', lambda _: world.session)
    monkeypatch.setattr(routes, 'get_session', lambda _: world.session)
    monkeypatch.setattr(routes, '_active_run_stream_for_session', lambda _: None)
    world.begin(capture=False)
    token = handoff.bind_turn(world.session, 'default', 'origin')
    yield world
    handoff.reset_turn(token)


def request(bot='reviewer', task='Review the plan'):
    return json.loads(handoff.handle({'action': 'delegate', 'bot': bot, 'task': task}))


def job():
    with handoff._db() as db:
        row = db.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 1').fetchone()
    return dict(row) if row else None


def ready(chat):
    result = request()
    assert result['status'] == 'queued'
    handoff.finish_turn('origin', True)
    chat.session.active_stream_id = None
    return result


def test_no_authority_files_for_an_unused_group_turn(chat):
    assert not (chat.root / 'authority').exists()


def test_catalog_and_idempotent_one_task_per_turn(chat):
    assert json.loads(handoff.handle({'action': 'list'}))['bots'] == ['reviewer', 'research']
    first = request()
    assert request()['delegation_id'] == first['delegation_id']
    assert 'error' in request('research')
    assert job()['state'] == 'pending'
    assert 'error' in request('default')
    assert 'error' in request('unknown')
    assert 'error' in request(task='')
    assert 'error' in request(task='x'*12001)


def test_awareness_is_fresh_scoped_and_uses_public_capabilities(chat, monkeypatch):
    from api import profiles, bot_metadata, bot_builder
    monkeypatch.setattr(profiles, 'list_profiles_api', lambda **kw: [
        {'name': 'default'}, {'name': 'reviewer'}, {'name': 'research'}, {'name': 'secret'}])
    descriptions = {'reviewer': 'Checks contracts', 'research': 'Finds and checks sources'}
    reads = []
    def metadata(name):
        reads.append(name)
        return {'bot': {'title': name.title(), 'description': descriptions.get(name, '')},
                'bot_configuration': {'toolsets': ['file'], 'prompt': 'PRIVATE-SOUL'},
                'bot_knowledge_sources': ['PRIVATE-FILE']}
    monkeypatch.setattr(bot_metadata, 'read_profile', metadata)
    monkeypatch.setattr(bot_builder, 'managed', lambda name: None)
    chat.session.bot_participants = ['default', 'reviewer']
    prompt = handoff.awareness_prompt(chat.session, IDENTITY, 'default')
    cards = json.loads(prompt.splitlines()[-1])
    by_id = {card['id']: card for card in cards}
    assert by_id['reviewer']['specialism'] == 'Checks contracts'
    assert by_id['reviewer']['handoff_participant'] is True
    assert by_id['research']['in_this_chat'] is False
    assert by_id['research']['handoff_participant'] is False
    assert 'secret' not in reads and 'secret' not in by_id
    assert 'PRIVATE' not in prompt
    listing = json.loads(handoff.handle({'action': 'list'}))
    assert listing['bot_details'][0]['specialism'] == 'Checks contracts'
    descriptions['reviewer'] = 'Checks technical plans'
    assert 'Checks technical plans' in handoff.awareness_prompt(chat.session, IDENTITY, 'default')
    assert handoff.awareness_prompt(chat.session, {}, 'default') == ''


def test_no_context_and_subagent_cannot_delegate(chat):
    assert 'error' in json.loads(handoff.handle({'action':'list'}, parent_agent=SimpleNamespace(_delegate_depth=1)))
    token = handoff._TURN.set(None)
    try:
        assert 'error' in request()
    finally:
        handoff._TURN.reset(token)


def test_cancelled_turn_never_dispatches(chat, monkeypatch):
    request(); handoff.finish_turn('origin', False)
    chat.session.active_stream_id = None
    monkeypatch.setattr(routes, 'start_session_turn', lambda *a, **kw: pytest.fail('Cancelled task dispatched'))
    handoff.dispatch_ready()
    assert job()['state'] == 'cancelled'


def test_pending_origin_and_busy_session_do_not_dispatch(chat, monkeypatch):
    request()
    calls=[]
    monkeypatch.setattr(routes, 'start_session_turn', lambda *a, **kw: calls.append(a))
    handoff.dispatch_ready();assert calls == []
    handoff.finish_turn('origin', True)
    handoff.dispatch_ready();assert calls == []
    assert job()['state'] == 'ready'


def test_dispatch_once_keeps_original_actor_and_target_profile(chat, monkeypatch):
    ready(chat)
    seen=[]
    def start(sid, message, **kw):
        record=continuation.resolve(kw['continuation_ref'],chat.session)
        seen.append((sid,message,record))
        return {'stream_id':'target','_status':200}
    monkeypatch.setattr(routes,'start_session_turn',start)
    handoff.dispatch_ready();handoff.dispatch_ready()
    assert len(seen)==1
    sid,message,record=seen[0]
    assert sid==chat.session.session_id
    assert message.startswith('@reviewer\n[Bot delegation: default → reviewer]')
    assert record['identity']['email']==EMAIL
    assert record['identity']['groups']==IDENTITY['groups']
    assert record['execution_profile']==record['active_profile']=='reviewer'
    assert record['bot_delegation']['depth']==1
    ceiling=chat.module.context_from_env_payload(record['context'])
    assert ceiling.active_profile=='reviewer'
    fresh=chat.module.current_governance_context()
    contexts=chat.module.policy_contexts(replace(fresh,active_profile='reviewer',continuation_contexts=(record['context'],)))
    assert len(contexts)==2
    assert contexts[1].access.grants==fresh.access.grants
    assert contexts[1].access.deny==fresh.access.deny
    assert job()['state']=='started'
    handoff.finish_turn('target',True)
    assert job()['state']=='completed'


def test_busy_dispatch_race_retries_but_never_double_starts(chat,monkeypatch):
    ready(chat);calls=[]
    def start(*args,**kw):
        calls.append(args)
        return {'_status':409} if len(calls)==1 else {'stream_id':'target'}
    monkeypatch.setattr(routes,'start_session_turn',start)
    handoff.dispatch_ready();assert job()['state']=='ready'
    handoff.dispatch_ready();handoff.dispatch_ready()
    assert len(calls)==2 and job()['state']=='started'


@pytest.mark.parametrize('revoke',['bot','membership','policy'])
def test_revocation_before_dispatch_fails_closed(chat,monkeypatch,revoke):
    ready(chat)
    if revoke=='bot':chat.session.bot_participants.remove('reviewer')
    elif revoke=='membership':chat.session.owner_email='someone@example.test'
    else:
        policy=deepcopy(POLICY);policy['roles']['member']['grants']['profiles']=['default']
        chat.current['policy']=loader.parse_governance_policy(policy)
    monkeypatch.setattr(routes,'start_session_turn',lambda *a,**kw:pytest.fail('Revoked handoff started'))
    handoff.dispatch_ready();assert job()['state']=='failed'


def test_chain_limit_and_context_cleanup(chat):
    token=handoff._TURN.set(replace(handoff._TURN.get(),depth=handoff.MAX_DEPTH))
    try:assert 'four handoffs' in request()['error']
    finally:handoff._TURN.reset(token)
    assert request()['status']=='queued'


def test_four_real_handoffs_preserve_all_prior_permission_ceilings(chat, monkeypatch):
    from contextlib import ExitStack
    starts = []
    def start(_sid, _message, **kwargs):
        starts.append(kwargs['continuation_ref'])
        return {'stream_id': f'hop-{len(starts)}'}
    monkeypatch.setattr(routes, 'start_session_turn', start)
    original = chat.module.current_governance_context()
    with ExitStack() as stack:
        for depth, target in enumerate(['reviewer', 'research', 'reviewer', 'research'], 1):
            assert request(target)['status'] == 'queued'
            handoff.finish_turn(chat.session.active_stream_id, True)
            chat.session.active_stream_id = None
            handoff.dispatch_ready()
            reference = starts[-1]
            record = continuation.resolve(reference, chat.session)
            assert record['identity']['groups'] == IDENTITY['groups']
            chat.session.active_stream_id = f'hop-{depth}'
            fresh_token = agent_context.bind_governed_agent_turn(
                IDENTITY, active_profile=target, session_id=chat.session.session_id)
            stack.callback(agent_context.reset_governed_agent_turn, fresh_token)
            authority_tokens = continuation.begin_turn(chat.session, IDENTITY,
                active_profile=target, execution_profile=target, reference=reference)
            stack.callback(continuation.end_turn, authority_tokens)
            token = handoff.bind_turn(chat.session, target, chat.session.active_stream_id, reference)
            stack.callback(handoff.reset_turn, token)
            contexts = chat.module.policy_contexts(chat.module.current_governance_context())
            assert len(contexts) == depth + 1
            assert all(c.access.grants == original.access.grants and c.access.deny == original.access.deny
                       for c in contexts)
        assert 'four handoffs' in request('reviewer')['error']


def test_receiver_request_is_not_attributed_to_human_and_survives_merge(chat,monkeypatch):
    ready(chat);record=job()
    token=handoff._TURN.set(replace(handoff._TURN.get(),incoming_id=record['id']))
    try:
        from api.streaming import _stamp_group_message_author
        prompt='@reviewer task';chat.session.messages=[{'role':'user','content':prompt,'author_email':EMAIL}]
        _stamp_group_message_author(chat.session,prompt,EMAIL)
        row=chat.session.messages[0]
        assert 'author_email' not in row
        assert row['bot_delegation']['from']=='default'
        merged=models.merge_session_messages_append_only([{'role':'user','content':prompt}],chat.session.messages)
        assert merged[0]['bot_delegation']==row['bot_delegation']
    finally:handoff._TURN.reset(token)


def test_tool_registration_integrates_with_engine_toolset(chat):
    handoff.register_tool()
    from tools.registry import registry
    from toolsets import resolve_toolset
    assert 'delegate_to_bot' in resolve_toolset('delegation')
    entry=registry.get_entry('delegate_to_bot')
    assert json.loads(entry.handler({'action':'list'}))['bots']==['reviewer','research']


def test_real_server_turn_dispatch_uses_receiver_model_and_original_sender(chat,monkeypatch):
    # Use the real start_session_turn -> _start_run -> local stream dispatcher;
    # replace only the final worker thread and infrastructure writes.
    ready(chat)
    from api import turn_journal
    chat.session.model='old';chat.session.model_provider='old';chat.session.title='Team';chat.session.pending_started_at=1
    monkeypatch.setattr(routes,'_resolve_chat_workspace_with_recovery',lambda *_:'/qa')
    monkeypatch.setattr(routes,'_read_profile_model_config',lambda s,p:('qa',s.profile+'-model',{}))
    monkeypatch.setattr(routes,'_resolve_compatible_session_model_state',lambda *_a,**_kw:('old','qa',False))
    monkeypatch.setattr(routes,'_is_hidden_empty_session',lambda s:False)
    monkeypatch.setattr(routes,'_prepare_chat_start_session_for_stream',lambda *a,**kw:None)
    monkeypatch.setattr(turn_journal,'append_turn_journal_event',lambda *a,**kw:{})
    monkeypatch.setattr(routes,'set_last_workspace',lambda *a:None)
    monkeypatch.setattr(routes,'register_stream_owner',lambda *a:None)
    launched=[]
    class Thread:
        def __init__(self,**kw):launched.append(kw)
        def start(self):pass
    monkeypatch.setattr(routes.threading,'Thread',Thread)
    handoff.dispatch_ready()
    assert job()['state']=='started'
    assert len(launched)==1
    worker=launched[0]
    assert worker['kwargs']['execution_profile']=='reviewer'
    assert worker['kwargs'].get('sender_email',chat.session.owner_email)==EMAIL
    assert worker['kwargs']['sender_identity']['groups']==IDENTITY['groups']
    assert 'reviewer-model' in worker['args']
    routes.STREAMS.pop(job()['target_stream'],None)


def test_parallel_identical_calls_share_one_durable_job(chat):
    from contextvars import copy_context
    from concurrent.futures import ThreadPoolExecutor
    contexts=[copy_context() for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda c:c.run(request),contexts))
    assert len({r['delegation_id'] for r in results})==1
    with handoff._db() as db:assert db.execute('SELECT count(*) FROM jobs').fetchone()[0]==1


def test_restart_interrupts_uncertain_work_instead_of_replaying(chat,monkeypatch):
    request()
    class Thread:
        def __init__(self,**kw):pass
        def start(self):pass
    monkeypatch.setattr(handoff,'_THREAD',None)
    monkeypatch.setattr(handoff.threading,'Thread',Thread)
    handoff.start_dispatcher()
    assert job()['state']=='interrupted'
    monkeypatch.setattr(routes,'start_session_turn',lambda *a,**kw:pytest.fail('Uncertain task replayed'))
    handoff.dispatch_ready()


def test_dispatch_failure_is_visible_once_in_same_chat(chat,monkeypatch):
    from api import background_process
    ready(chat)
    chat.session.messages=[];saves=[];events=[]
    chat.session.save=lambda:saves.append(True)
    monkeypatch.setattr(background_process,'get_session_channel',lambda _:SimpleNamespace(emit=lambda *args:events.append(args)))
    monkeypatch.setattr(routes,'start_session_turn',lambda *a,**kw:{'_status':403,'error':'Access revoked'})
    handoff.dispatch_ready()
    record=job()
    handoff._notify_failure(record,'retry notice')
    assert record['state']=='failed'
    assert len(chat.session.messages)==1 and len(saves)==1
    assert 'default → reviewer' in chat.session.messages[0]['content']
    assert events[0][0]=='session-updated'
    assert events[0][1]['session_id']==chat.session.session_id
