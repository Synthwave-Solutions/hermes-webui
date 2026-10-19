"""Screen authority and durable lease tests with two users and two profiles."""
from contextlib import contextmanager
from types import SimpleNamespace
from urllib.parse import urlsplit
import pytest
from tests.test_org_api_read import _Handler
from api import bot_screens as screens


@pytest.fixture
def setup(tmp_path, monkeypatch):
    # The checkout source is discovered using the existing WebUI configuration.
    from api.routes import _ensure_agent_cron_import_path
    _ensure_agent_cron_import_path()
    from tools.bot_desktop import lease
    homes = {n: tmp_path/n for n in ('one', 'two')}
    for h in homes.values(): h.mkdir()
    config = {'enabled': True, 'profiles': {
        'one': {'admins': ['admin@example.test'], 'controllers': ['driver@example.test'], 'viewers': ['watch@example.test']},
        'two': {'controllers': ['second@example.test']}}}
    state = SimpleNamespace(email='admin@example.test', cookie='cookie-admin', running=True)
    monkeypatch.setattr(screens.loader, 'get_policy', lambda: SimpleNamespace(raw={'bot_screens': config}))
    monkeypatch.setattr(screens.auth, 'parse_cookie', lambda h: state.cookie)
    monkeypatch.setattr(screens.auth, 'get_session_identity', lambda c: {'email': state.email} if state.email else None)
    monkeypatch.setattr(screens.auth, 'csrf_token_for_session', lambda c: 'csrf')
    monkeypatch.setattr(screens, '_home', lambda bot: homes[bot])
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    runtime = SimpleNamespace(status=lambda: SimpleNamespace(running=state.running, as_dict=lambda: {'running': state.running,'installed':True,'supported':True,'missing':[]}), start=lambda:None, stop=lambda:None)
    @contextmanager
    def context(home): yield runtime, lease
    monkeypatch.setattr(screens, '_runtime', context)
    screens._CHALLENGES.clear()
    return state, config, homes, lease


def post(action, bot='one', **extra):
    h=_Handler();screens.handle_post(h, {'bot':bot,'tab':'tab-1234567890123456','action':action,**extra});return h


def get(bot='one'):
    h=_Handler();screens.handle_get(h,urlsplit('/api/bot-screen?bot='+bot+'&tab=tab-1234567890123456'));return h


def challenge(operation="takeover"):
    h=post('confirm',operation=operation);assert h.status==200;return h.body['challenge']


def test_disabled_and_unknown_users_never_inherit_admin(setup):
    state, cfg, _, _ = setup
    cfg['enabled']=False
    assert get().status==403
    cfg['enabled']=True;state.email='other@example.test'
    assert get().status==403
    state.email=None
    assert get().status==401


def test_profile_scope_and_view_only(setup):
    state, _, _, _=setup
    assert get('two').status==403
    state.email='watch@example.test'
    assert get().status==200
    for action in ('start','stop','confirm','takeover','release','recover'):
        assert post(action).status==403


def test_takeover_requires_single_use_session_bound_confirmation(setup):
    state, _, homes, lease=setup
    assert post('takeover').status==409
    token=challenge();state.cookie='different-cookie'
    assert post('takeover',challenge=token).status==409
    state.cookie='cookie-admin'
    assert post('takeover',challenge=token).status==200
    assert lease.human_holds(str(homes['one']))
    assert not lease.human_holds(str(homes['two']))
    assert post('takeover',challenge=token).status==409
    with pytest.raises(lease.HumanHasControl):lease.assert_agent_may_act(str(homes['one']))


def test_private_handoff_and_admin_recovery(setup):
    state, _, homes, lease=setup
    assert post('takeover',challenge=challenge()).body['mine']
    state.email='driver@example.test';state.cookie='driver-cookie'
    assert get().body['private'] and not get().body['mine']
    assert post('release').status==409
    assert post('takeover',challenge=challenge()).status==409
    assert post('recover').status==403
    state.email='admin@example.test';state.cookie='new-admin-session'
    assert post('recover',challenge=challenge('recover')).status==200
    assert not lease.human_holds(str(homes['one']))


def test_holder_can_hand_back_but_stop_cannot_kill_human(setup):
    _, _, homes, lease=setup
    post('takeover',challenge=challenge())
    assert post('stop',challenge=challenge('stop')).status==409
    assert post('release').status==200
    assert not lease.human_holds(str(homes['one']))
    assert post('stop',challenge=challenge('stop')).status==200


def test_revocation_is_immediate_even_for_holder(setup):
    _, cfg, homes, lease=setup
    post('takeover',challenge=challenge())
    cfg['profiles']['one']['admins']=[]
    assert get().status==403
    assert post('release').status==403
    assert lease.human_holds(str(homes['one']))


def test_hostile_fields_and_tab_scope(setup):
    h=_Handler();screens.handle_post(h, {'bot':'one','tab':'tab-1234567890123456','action':'takeover','viewer_id':'someone'})
    assert h.status==422
    assert screens._viewer('cookie','one','tab-1234567890123456') != screens._viewer('cookie','two','tab-1234567890123456')
    with pytest.raises(screens.ScreenError):screens._viewer('cookie','one','../')


@pytest.mark.parametrize('origin', ['', 'https://evil.example', 'https://local.example/extra', 'null'])
def test_cross_origin_socket_refused(setup, origin):
    h=_Handler();h.headers={'Origin':origin,'Host':'local.example'}
    screens.handle_get(h,urlsplit('/api/bot-screen/ws?bot=one&tab=tab-1234567890123456'))
    assert h.status==403


def test_privacy_unknown_human_owner_fails_closed(setup):
    _,_,_,lease=setup
    assert not screens._may_watch(lease.Lease(holder='human',viewer_id='unreadable-lease'),'me')
    assert screens._may_watch(lease.Lease(),'me')


def test_confirmation_cannot_be_swapped_between_actions(setup):
    token=challenge('takeover')
    assert post('stop',challenge=token).status==409


def test_expired_confirmation_does_not_acquire_lease(setup, monkeypatch):
    _,_,homes,lease=setup
    token=challenge()
    monkeypatch.setattr(screens.time,'monotonic',lambda:10**20)
    assert post('takeover',challenge=token).status==409
    assert not lease.human_holds(str(homes['one']))


def status(query=''):
    h=_Handler();screens.handle_get(h,urlsplit('/api/bot-screen/status'+query));return h


def _ask(lease, home, reason):
    def ask(row):
        row.reason=reason;return True
    lease._transition(str(home), ask)


def test_status_states_and_scope(setup):
    state, _, homes, lease=setup
    screens._HOLDERS.clear()
    assert status().body=={'screens':[{'bot':'one','rights':{'view':True,'control':True,'admin':True},'state':'none'}]}
    _ask(lease, homes['one'], '  please   log in to Exact ')
    row=status('?bot=one').body['screens'][0]
    assert row['state']=='waiting' and row['reason']=='please log in to Exact'
    post('takeover',challenge=challenge())
    row=status('?bot=one').body['screens'][0]
    assert row['state']=='human' and row['by']=='admin@example.test' and row['mine'] is True
    # A watcher sees who holds it, not as their own; a bot without a grant is absent.
    state.email='watch@example.test';state.cookie='watch-cookie'
    rows=status().body['screens']
    assert [r['bot'] for r in rows]==['one'] and rows[0]['mine'] is False and rows[0]['rights']['control'] is False
    assert status('?bot=two').status==403
    state.email='second@example.test'
    assert [r['bot'] for r in status().body['screens']]==['two']
    state.email=None
    assert status().status==401


def test_status_after_hand_back_and_unreadable_lease(setup):
    _, _, homes, lease=setup
    post('takeover',challenge=challenge());post('release')
    assert status('?bot=one').body['screens'][0]['state']=='agent'
    (homes['one']/'bot-desktop'/'lease.json').write_text('{broken')
    row=status('?bot=one').body['screens'][0]
    assert row['state']=='human' and row['by']=='' and row['mine'] is False
