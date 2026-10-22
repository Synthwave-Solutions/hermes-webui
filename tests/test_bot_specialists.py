"""Background specialists keep identity/ceilings and do not join group chats."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from api import bot_delegation as bots, bot_specialists as specialists, models, profiles, routes
from api.governance import continuation, loader
from tests.test_bot_delegation import chat  # noqa: F401
from tests.test_continuation_authority import world, POLICY, EMAIL, IDENTITY  # noqa: F401


@pytest.fixture
def team(chat, monkeypatch):
    chat.session.bot_participants = []  # Ordinary single-bot conversation.
    chat.session.workspace = '/qa/work'
    chat.session.messages = []
    chat.session.save = lambda: None
    sessions = {chat.session.session_id: chat.session}
    monkeypatch.setattr(profiles, 'list_profiles_api', lambda **kw: [
        {'name': n} for n in ('default', 'reviewer', 'research', 'forbidden')])
    def get(sid):
        if sid not in sessions:
            raise KeyError(sid)
        return sessions[sid]
    def new(**kw):
        child = SimpleNamespace(**kw, messages=[], active_stream_id=None, save=lambda: None)
        sessions[child.session_id] = child
        return child
    monkeypatch.setattr(models, 'get_session', get)
    monkeypatch.setattr(routes, 'get_session', get)
    monkeypatch.setattr(models, 'new_session', new)
    chat.sessions = sessions
    return chat


def enqueue(bot='reviewer', task='Review only the provided plan'):
    return json.loads(bots.handle({'action': 'delegate', 'bot': bot, 'task': task}))


def job():
    with specialists._db() as db:
        row = db.execute('SELECT * FROM specialists ORDER BY created DESC LIMIT 1').fetchone()
    return dict(row) if row else None


def release(team):
    result = enqueue()
    assert result['status'] == 'queued'
    bots.finish_turn('origin', True)
    team.session.active_stream_id = None
    return result


def test_single_bot_discovery_default_background_and_no_membership_change(team):
    catalog = json.loads(bots.handle({'action': 'list'}))
    assert catalog['bots'] == ['reviewer', 'research']
    assert 'error' in enqueue('forbidden')
    first = enqueue()
    assert first['mode'] == 'background'
    assert first['delegation_id'] == enqueue()['delegation_id']
    assert 'error' in enqueue('research')
    assert team.session.bot_participants == []
    assert job()['state'] == 'pending'


def test_join_request_is_human_only_and_requires_reason(team):
    assert 'error' in json.loads(bots.handle({'action': 'request_join', 'bot': 'reviewer'}))
    request = json.loads(bots.handle({'action': 'request_join', 'bot': 'reviewer',
                                     'task': 'We need an ongoing shared review discussion'}))
    assert request['status'] == 'human_action_required'
    assert team.session.bot_participants == []
    assert job() is None


def test_child_has_own_profile_private_owner_and_original_ceiling(team, monkeypatch):
    result = release(team)
    calls = []
    def start(sid, prompt, **kw):
        child = team.sessions[sid]
        record = continuation.resolve(kw['continuation_ref'], child)
        calls.append((child, prompt, record))
        return {'stream_id': 'child-turn'}
    monkeypatch.setattr(routes, 'start_session_turn', start)
    specialists.dispatch(); specialists.dispatch()
    assert len(calls) == 1
    child, prompt, record = calls[0]
    assert child.session_id == result['session_id'] != team.session.session_id
    assert child.profile == 'reviewer' and child.bot_participants == ['reviewer']
    assert child.owner_email == EMAIL and child.participants == []
    assert child.parent_session_id == team.session.session_id and child.read_only is True
    assert child.source_tag == 'subagent'
    assert record['identity']['groups'] == IDENTITY['groups']
    ceiling = team.module.context_from_env_payload(record['context'])
    original = team.module.current_governance_context()
    assert ceiling.active_profile == 'reviewer'
    assert ceiling.access.grants == original.access.grants
    assert ceiling.access.deny == original.access.deny
    assert 'full chat' not in prompt
    assert team.session.bot_participants == []


def test_completion_returns_once_to_original_bot_without_human_attribution(team, monkeypatch):
    release(team)
    calls = []
    def start(sid, prompt, **kw):
        session = team.sessions[sid]
        record = continuation.resolve(kw['continuation_ref'], session)
        calls.append((sid, prompt, record))
        # Finish immediately, before dispatch can record stream IDs.
        if sid != team.session.session_id:
            session.messages.append({'role': 'assistant', 'content': 'The plan needs a rollback step.'})
            bots.finish_turn('child-turn', True, kw['continuation_ref'], session)
        else:
            token = bots.bind_turn(session, 'default', 'report-turn', kw['continuation_ref'])
            # bind_turn normally runs inside begin_turn; use explicit incoming context here.
            old = bots._TURN.set(bots.Turn(sid, 'report-turn', 'default', kw['continuation_ref'], 1, job()['id']))
            try:
                message = {'role': 'user', 'content': prompt, 'author_email': EMAIL}
                assert bots.stamp_request(session, message)
                assert 'author_email' not in message
                assert message['bot_delegation']['result'] is True
                assert message['_source'] == 'process_wakeup'
                assert prompt.startswith('[ASYNC DELEGATION COMPLETE — ')
            finally:
                bots._TURN.reset(old)
                bots.reset_turn(token)
            bots.finish_turn('report-turn', True, kw['continuation_ref'], session)
        return {'stream_id': 'test-stream'}
    monkeypatch.setattr(routes, 'start_session_turn', start)
    specialists.dispatch()
    assert job()['state'] == 'completed'
    specialists.dispatch(); specialists.dispatch()
    assert len(calls) == 2 and job()['state'] == 'delivered'
    assert calls[1][0] == team.session.session_id
    assert 'rollback step' in calls[1][1]
    assert calls[1][2]['active_profile'] == 'default'
    assert calls[1][2]['identity']['email'] == EMAIL
    assert team.session.bot_participants == []


@pytest.mark.parametrize('stage', ['before_start', 'before_return'])
def test_access_revoked_at_either_boundary_fails_closed(team, monkeypatch, stage):
    release(team)
    calls = []
    def start(sid, prompt, **kw):
        calls.append(sid)
        return {'stream_id': 'child-turn'}
    monkeypatch.setattr(routes, 'start_session_turn', start)
    if stage == 'before_return':
        specialists.dispatch()
        child = team.sessions[job()['child_id']]
        child.messages.append({'role': 'assistant', 'content': 'Private specialist result'})
        bots.finish_turn('child-turn', True)
    policy = deepcopy(POLICY)
    policy['roles']['member']['grants']['profiles'] = ['default']
    team.current['policy'] = loader.parse_governance_policy(policy)
    specialists.dispatch()
    assert len(calls) == (1 if stage == 'before_return' else 0)
    assert job()['state'] == 'failed'
    assert not any('Private specialist result' in m.get('content', '') for m in team.session.messages)


def test_cancelled_origin_and_restart_do_not_replay(team, monkeypatch):
    enqueue(); bots.finish_turn('origin', False)
    monkeypatch.setattr(routes, 'start_session_turn', lambda *a, **kw: pytest.fail('Unexpected replay'))
    specialists.dispatch()
    assert job()['state'] == 'cancelled'
    with specialists._db() as db:
        db.execute("UPDATE specialists SET state='started'")
    specialists.recover(); specialists.dispatch()
    assert job()['state'] == 'notified'
    assert len(team.session.messages) == 1


def test_explicit_busy_retries_same_child_without_duplicate_start(team, monkeypatch):
    release(team)
    calls = []
    def start(sid, *args, **kw):
        calls.append(sid)
        return {'_status': 409} if len(calls) == 1 else {'stream_id': 'child-turn'}
    monkeypatch.setattr(routes, 'start_session_turn', start)
    specialists.dispatch()
    assert job()['state'] == 'ready'
    specialists.dispatch(); specialists.dispatch()
    assert calls[0] == calls[1] and len(calls) == 2
    assert job()['state'] == 'started'


def test_ambiguous_start_does_not_retry(team, monkeypatch):
    release(team)
    calls = []
    def start(*args, **kw):
        calls.append(args)
        raise TimeoutError('Unknown whether task started')
    monkeypatch.setattr(routes, 'start_session_turn', start)
    specialists.dispatch(); specialists.dispatch(); specialists.dispatch()
    assert len(calls) == 1 and job()['state'] == 'notified'


def test_no_mixing_handoff_and_background_in_one_turn(team):
    team.session.bot_participants = ['default', 'reviewer']
    assert enqueue()['status'] == 'queued'
    assert 'error' in json.loads(bots.handle({'action': 'delegate', 'mode': 'handoff',
                                            'bot': 'reviewer', 'task': 'Another task'}))


def test_nested_work_finishes_before_outer_result_is_returned(team, monkeypatch):
    release(team)
    calls = []
    def start(sid, prompt, **kw):
        calls.append(sid)
        return {'stream_id': 'child-turn'}
    monkeypatch.setattr(routes, 'start_session_turn', start)
    specialists.dispatch()
    outer = job()
    child = team.sessions[outer['child_id']]
    child.messages.append({'role': 'assistant', 'content': 'I queued more research.'})
    bots.finish_turn('child-turn', True)
    specialist_turn = bots.Turn(child.session_id, 'nested-origin', 'reviewer',
                               outer['target_authority'], 1, outer['id'])
    nested = specialists.enqueue(specialist_turn, 'research', 'Check sources', outer['ceiling'])
    specialists.dispatch()
    assert calls == [child.session_id], 'Do not return the queued-work acknowledgement'
    with specialists._db() as db:
        db.execute("UPDATE specialists SET state='delivered' WHERE id=?", (nested['delegation_id'],))
    child.messages.append({'role': 'assistant', 'content': 'Research complete, sources checked.'})
    specialists.dispatch()
    assert calls == [child.session_id, team.session.session_id]


def test_real_target_governance_turn_accepts_child_bound_authority(team, monkeypatch):
    from api.governance import agent_context
    release(team)
    def start(sid, prompt, **kw):
        child = team.sessions[sid]
        identity = continuation.resolve(kw['continuation_ref'], child)['identity']
        token = agent_context.bind_governed_agent_turn(identity, active_profile='reviewer', session_id=sid)
        try:
            bound = continuation.begin_turn(child, identity, active_profile='reviewer',
                                             execution_profile='reviewer', reference=kw['continuation_ref'])
            try:
                current = team.module.current_governance_context()
                assert current.active_profile == 'reviewer'
                assert len(current.continuation_contexts) == 1
            finally:
                continuation.end_turn(bound)
        finally:
            agent_context.reset_governed_agent_turn(token)
        return {'stream_id': 'child-turn'}
    monkeypatch.setattr(routes, 'start_session_turn', start)
    specialists.dispatch()
    assert job()['state'] == 'started'


def test_group_guest_keeps_own_identity_and_private_child(team, monkeypatch):
    team.end()
    team.session.owner_email = 'other-owner@example.test'
    team.session.participants = [EMAIL]
    team.begin(capture=False)
    token = bots.bind_turn(team.session, 'default', 'origin')
    try:
        release(team)
        seen = []
        def start(sid, prompt, **kw):
            child = team.sessions[sid]
            record = continuation.resolve(kw['continuation_ref'], child)
            seen.append((child.owner_email, record['identity']['email']))
            return {'stream_id': 'child-turn'}
        monkeypatch.setattr(routes, 'start_session_turn', start)
        specialists.dispatch()
        assert seen == [(EMAIL, EMAIL)]
        assert team.session.owner_email == 'other-owner@example.test'
    finally:
        bots.reset_turn(token)
