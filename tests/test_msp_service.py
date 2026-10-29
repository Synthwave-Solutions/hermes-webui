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


def test_paid_order_proxy_binds_identity_and_rejects_price_or_status(write_policy,caller,monkeypatch):
    from api import msp_service
    caller.email=PLATFORM[0];calls=[]
    monkeypatch.setattr(control_plane_client,'call',lambda *a,**k:(calls.append((a,k)) or (200,{'status':'offered'})))
    h=_Handler();assert msp_service.handle_post(h,'/api/msp/order',{'order_id':'so_example','action':'submit'})
    assert h.status==200
    assert calls[0][0]==('POST','/v1/customer/orders/so_example/submit')
    assert calls[0][1]['body']=={}
    assert calls[0][1]['acting']['user']==PLATFORM[0]
    for extra in [{'paid':True},{'amount':1},{'org_id':'other'},{'user':'other'}]:
        h=_Handler();msp_service.handle_post(h,'/api/msp/order',{'order_id':'so_example','action':'submit',**extra});assert h.status==422
    assert len(calls)==1


def test_invoice_proxy_keeps_customer_scope_and_hides_provider_choices(write_policy,caller,monkeypatch):
    from api import msp_service
    caller.email=PLATFORM[0];calls=[]
    monkeypatch.setattr(control_plane_client,'call',lambda *a,**k:(calls.append((a,k)) or (200,{'content_type':'application/pdf','pdf_base64':'JVBERi0='})))
    h=_Handler();assert msp_service.handle_post(h,'/api/msp/invoice',{'request_id':'br_example'})
    assert h.status==200 and calls[0][0]==('POST','/v1/customer/invoices/br_example/download')
    assert calls[0][1]['body']=={} and calls[0][1]['acting']['user']==PLATFORM[0]
    assert calls[0][1]['timeout']==60
    for extra in [{'org_id':'other'},{'invoice_id':'invoice_other'},{'url':'https://other.test'},{'paid':True}]:
        h=_Handler();msp_service.handle_post(h,'/api/msp/invoice',{'request_id':'br_example',**extra});assert h.status==422
    assert len(calls)==1


def test_request_only_apps_reject_direct_toggle_but_keep_explicit_requests(write_policy,caller,monkeypatch):
    from api import msp_service
    caller.email=PLATFORM[0]; calls=[]
    monkeypatch.setenv('SP_MSP_REQUEST_ONLY_APPS','1')
    monkeypatch.setattr(control_plane_client,'call',lambda *a,**k:(calls.append((a,k)) or (200,{'status':'requested'})))
    h=_Handler();msp_service.handle_post(h,'/api/msp/app-state',{'app_id':'opendesign','enabled':True})
    assert h.status==403 and h.body['error']=='msp_approval_required'
    assert calls==[]
    h=_Handler();msp_service.handle_post(h,'/api/msp/app-request',{'app_id':'opendesign','note':'Please review this app.'})
    assert h.status==200
    assert calls[0][0]==('POST','/v1/customer/apps/opendesign/request')
    assert calls[0][1]['acting']['user']==PLATFORM[0]


def test_unmanaged_app_toggle_behavior_is_unchanged(write_policy,caller,monkeypatch):
    from api import msp_service
    caller.email=PLATFORM[0]; calls=[]
    monkeypatch.delenv('SP_MSP_REQUEST_ONLY_APPS',raising=False)
    monkeypatch.setattr(control_plane_client,'call',lambda *a,**k:(calls.append((a,k)) or (200,{'enabled':True})))
    h=_Handler();msp_service.handle_post(h,'/api/msp/app-state',{'app_id':'opendesign','enabled':True})
    assert h.status==200
    assert calls[0][0]==('POST','/v1/customer/apps/opendesign/state')
