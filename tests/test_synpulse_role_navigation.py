from types import SimpleNamespace

from api.governance.nav import hidden_panels, visible_panels


def access(*permissions):
    return SimpleNamespace(permissions=frozenset(permissions), grants=SimpleNamespace(permissions=frozenset(permissions)))


POLICY = SimpleNamespace(enabled=True, mode='enforce')


def test_member_with_broad_feature_reads_gets_daily_work_navigation():
    caller = access('sessions:read', 'profiles:read', 'cron:read', 'skills:read',
                    'integrations:read', 'memory:read', 'files:read', 'logs:read',
                    'analytics:read', 'governance:read', 'kanban:read')
    assert set(visible_panels(caller, POLICY)) == {
        'chat', 'profiles', 'projects', 'tasks', 'skills', 'integrations',
        'approvals', 'settings',
    }


def test_administrative_grant_opens_full_navigation_without_role_name_magic():
    assert hidden_panels(access('governance:write'), POLICY) == []
    caller = access('sessions:read')
    caller.roles = frozenset({'admin'})
    assert 'governance' in hidden_panels(caller, POLICY)


def test_member_missing_feature_grant_keeps_own_approvals_but_no_dead_ends():
    assert set(visible_panels(access(), POLICY)) == {'chat', 'settings', 'approvals'}


def test_effective_permissions_take_precedence_over_unresolved_grants():
    caller = access()
    caller.grants.permissions = frozenset({'*'})
    assert 'governance' in hidden_panels(caller, POLICY)
