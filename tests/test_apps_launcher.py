"""No request-controlled links, dormant apps, workflow editor leakage or unsafe origins."""
import json
from types import SimpleNamespace
import pytest
from api import apps_launcher, modules
from tests.test_org_api_read import home, write_policy, caller, _Handler, PLATFORM, NOBODY


@pytest.mark.parametrize('url',[
'http://design.example.test','javascript:alert(1)','https://example.test.evil.test',
'https://evilexample.test','https://n8n.example.test','https://opendesign.example.test',
'https://user:pass@design.example.test','https://design.example.test:444',
'https://design.example.test?token=secret','https://design.example.test/#fragment',
'https://design.example.test\\@evil.test','https://design.example.test\n',
'https://node.tail.test.evil.test:9443','https://evil.node.tail.test:9443',None,{},
])
def test_unsafe_links(url):
    assert apps_launcher.safe_link(url,{'SP_DOMAIN':'example.test','SP_MESH_FQDN':'node.tail.test'}) is None


def test_domain_requires_trusted_config():
    assert apps_launcher.safe_link('https://design.example.test',{}) is None
    assert apps_launcher.safe_link('https://design.example.test',{'SP_DOMAIN':'example.test'})
    assert apps_launcher.safe_link('https://node.tail.test:9443/app',{'SP_MESH_FQDN':'node.tail.test'})


def get(caller,email):
    caller.email=email;h=_Handler();apps_launcher.handle_get(h,SimpleNamespace(path='/api/apps',query='url=https://evil.test'));return h


@pytest.mark.parametrize('editor',[False,True])
@pytest.mark.parametrize('admin',[False,True])
def test_tiles_scope_and_active_only(write_policy,caller,monkeypatch,editor,admin):
    monkeypatch.setenv('SP_DOMAIN','example.test');monkeypatch.setenv('SP_ENABLED_MODULES','')
    monkeypatch.setenv('SP_WORKFLOWS_CLIENT_EDITOR','1' if editor else '0')
    monkeypatch.setenv('SP_MODULE_LINKS',json.dumps({'design_studio':'https://design.example.test','workflows':'https://workflows.example.test','notebook':'https://notebook.example.test','office_apps':'https://office.example.test'}))
    modules.clear_cache();h=get(caller,PLATFORM[0] if admin else NOBODY[0]);assert h.status==200
    assert [a['module'] for a in h.body['apps']]==(['design_studio','workflows'] if admin or editor else ['design_studio'])
    monkeypatch.setenv('SP_ENABLED_MODULES','notebook');modules.clear_cache()
    assert 'notebook' in [a['module'] for a in get(caller,NOBODY[0]).body['apps']]


@pytest.mark.parametrize('links',['bad','[]','null','{}'])
def test_empty_and_malformed_links(write_policy,caller,monkeypatch,links):
    monkeypatch.setenv('SP_MODULE_LINKS',links)
    assert get(caller,NOBODY[0]).body=={'apps':[]}


def test_anonymous_auth_disabled(write_policy,caller):
    assert get(caller,None).status==403
    caller.method='auth_disabled'
    assert get(caller,PLATFORM[0]).status==403
