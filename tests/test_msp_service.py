from types import SimpleNamespace
from api import control_plane_client
from tests.test_org_api_read import home,write_policy,caller,_Handler,_raw,PLATFORM,NOBODY


def test_msp_proxy_binds_identity_not_browser_body(write_policy,caller,monkeypatch):
    from api import msp_service
    caller.email=PLATFORM[0]
    calls=[]
    monkeypatch.setattr(control_plane_client,'call',lambda *args,**kwargs:(calls.append((args,kwargs)) or (200,{'tickets':[]})))
    h=_Handler();msp_service.handle_get(h,SimpleNamespace(path='/api/msp/tickets',query='scope=mine'))
    assert h.status==200
    assert calls[0][1]['acting']['user']==PLATFORM[0]
    h=_Handler();msp_service.handle_post(h,'/api/msp/app-state',{'app_id':'opendesign','enabled':False,'org_id':'another'})
    assert h.status==422 and len(calls)==1


def test_unknown_and_anonymous_users_cannot_reach_msp(write_policy,caller,monkeypatch):
    from api import msp_service
    monkeypatch.setattr(control_plane_client,'call',lambda *a,**k:(_ for _ in ()).throw(AssertionError('network')))
    for who in [None,'stranger@elsewhere.example']:
        caller.email=who;h=_Handler();msp_service.handle_get(h,SimpleNamespace(path='/api/msp/overview',query=''))
        assert h.status==403


def test_job_cost_proxy_rejects_spoofed_profile_and_job(write_policy,caller,monkeypatch):
    from api import msp_service, profiles
    caller.email=PLATFORM[0]
    monkeypatch.setattr(profiles,'get_active_profile_name',lambda:'default')
    monkeypatch.setattr(control_plane_client,'call',lambda *a,**k:(_ for _ in ()).throw(AssertionError('network')))
    for body in ({'job_id':{},'profile':'default'}, {'job_id':'valid','profile':'other'}, {'job_id':'valid','org_id':'other'}):
        h=_Handler();msp_service.handle_post(h,'/api/msp/job-cost',body)
        assert h.status==422
