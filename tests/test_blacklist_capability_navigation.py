"""Capability visibility never confers administrator identity or bypasses denies."""
import subprocess
from dataclasses import replace
from api.governance.models import EffectiveAccess, GovernanceSubject, GrantSet
from api.governance.nav import administrative_access, feature_permissions, hidden_panels


def caller(mode='blacklist', level='elevated', denied=()):
    grants=GrantSet(permissions=frozenset({'*'}))
    return EffectiveAccess(subject=GovernanceSubject(email='technical@example.test'), mode='enforce',
        permissions=grants.permissions, grants=grants, deny=GrantSet(permissions=frozenset(denied)),
        access_mode=mode, access_level=level)


def test_blacklist_panel_visibility_uses_effective_reads_without_admin_identity():
    access=caller(denied=('governance:*','logs:*','files:*'))
    assert not administrative_access(access)
    hidden=hidden_panels(access)
    assert {'logs','governance','files','workspaces'} <= set(hidden)
    assert not {'kanban','todos','profiles','insights','tasks'} & set(hidden)
    assert 'kanban' in hidden_panels(caller(denied=('sessions:read',)))


def test_mode_only_blacklist_wildcard_does_not_grant_administrative_identity():
    access=caller(level='')
    assert not administrative_access(access)
    assert administrative_access(replace(access,access_level='admin'))


def test_legacy_and_whitelist_keep_daily_navigation_contract():
    for mode in ('','whitelist'):
        access=caller(mode=mode)
        assert {'kanban','workspaces','files','todos','insights','logs'} <= set(hidden_panels(access))


def test_permission_projection_resolves_wildcard_denies_and_implicit_host_restriction():
    access=caller(denied=('plugins:*','profiles:admin'))
    permissions=feature_permissions(access)
    assert permissions['plugins:read'] is False
    assert permissions['profiles:admin'] is False
    assert permissions['config:read'] is True
    restricted=replace(access,deny=GrantSet(file_read_roots=frozenset({'/private'})))
    # Keep the existing model's hard restriction visible; later model fixes can
    # retain their own enforcement semantics without a JS wildcard bypass.
    assert feature_permissions(restricted)['terminal:use'] == restricted.has_permission('terminal:use')


def test_real_frontend_feature_gate_prefers_server_boolean_over_raw_wildcard():
    script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('static/panels.js','utf8');
const fn=source.slice(source.indexOf('function _canUseFeature('),source.indexOf('function _advancedChatPreferenceKey('));
const ctx={window:{__GOV_ME__:{permissions:['*'],feature_permissions:{'plugins:read':false,'config:read':true}}}};
vm.createContext(ctx);vm.runInContext(fn,ctx);
assert.equal(ctx._canUseFeature('plugins:read'),false);assert.equal(ctx._canUseFeature('config:read'),true);
ctx.window.__GOV_ME__={permissions:['plugins:read']};assert.equal(ctx._canUseFeature('plugins:read'),true);
'''
    result=subprocess.run(['node','-e',script],capture_output=True,text=True)
    assert result.returncode == 0,result.stdout+result.stderr
