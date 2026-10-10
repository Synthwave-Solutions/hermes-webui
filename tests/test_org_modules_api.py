"""Local catalogue authorization in all governance modes, without entitlement mutation."""
import copy
import json
from types import SimpleNamespace
import pytest
from api import org_modules, modules
from api.governance import loader, enforce
from tests.test_org_api_read import home, write_policy, caller, _raw, _Handler, PLATFORM, ORG, BILLING, DEPARTMENT, NOBODY


def call(caller, email, is_request=False):
    caller.email=email
    h=_Handler()
    (org_modules.handle_request(h, {'enabled_modules':['*'], 'status':'active'}) if is_request else
     org_modules.handle_get(h, SimpleNamespace(path='/api/org/modules')))
    return h


@pytest.mark.parametrize('email', PLATFORM+ORG+BILLING+DEPARTMENT+NOBODY+(None,))
@pytest.mark.parametrize('is_request', [False, True])
@pytest.mark.parametrize('mode', ['off','report_only','enforce'])
def test_scope_matrix(write_policy, caller, email, is_request, mode):
    raw=_raw();raw['mode']=mode;write_policy(raw)
    response=call(caller,email,is_request)
    allowed=email in PLATFORM+ORG+BILLING
    assert response.status==(503 if is_request else 200) if allowed else response.status==403
    if allowed and is_request:assert response.body=={'error':'requests_not_connected'}


@pytest.mark.parametrize('is_request',[False,True])
def test_hq_and_auth_disabled(write_policy,caller,is_request):
    caller.method='auth_disabled'
    assert call(caller,PLATFORM[0],is_request).status==403
    raw=_raw();raw['installation']={'kind':'hq'};raw.pop('organization');raw.pop('departments');write_policy(raw)
    assert call(caller,PLATFORM[0],is_request).status==404


@pytest.mark.parametrize('env,active',[(None,False),('',False),('???',False),('*',False),('knowledge_base',True)])
def test_local_status_not_policy_or_body(write_policy,caller,monkeypatch,env,active):
    if env is None:monkeypatch.delenv('SP_ENABLED_MODULES',raising=False)
    else:monkeypatch.setenv('SP_ENABLED_MODULES',env)
    modules.clear_cache()
    response=call(caller,ORG[0]);rows={r['id']:r for r in response.body['modules']}
    assert len(rows)==10
    assert sum(r['status']=='included' for r in rows.values())==4
    assert rows['knowledge_base']['status']==('active' if active else 'available')
    assert response.body['requests_connected'] is False
    text=json.dumps(response.body).lower()
    assert all(word.lower() not in text for word in modules.DISPLAY_DENYLIST)


def test_settings_and_policy_failure(write_policy,caller,monkeypatch):
    caller.email=ORG[0]
    assert org_modules.settings_view(_Handler())['module_nav']['modules_visible'] is True
    caller.email=NOBODY[0]
    assert org_modules.settings_view(_Handler())['module_nav']['modules_visible'] is False
    monkeypatch.setattr(loader,'get_policy',lambda:(_ for _ in ()).throw(RuntimeError('bad policy')))
    assert call(caller,ORG[0]).status==503
    assert org_modules.settings_view(_Handler())['module_nav']['apps_visible'] is False
