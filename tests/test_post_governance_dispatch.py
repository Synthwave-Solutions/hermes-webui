"""POST dispatch must reach the module governance gate for every browser route."""
from types import SimpleNamespace
from urllib.parse import urlparse
import pytest
from api import routes

@pytest.mark.parametrize('path',['/api/session/new','/api/profile/appearance','/api/profile/avatar'])
def test_post_dispatch_reaches_governance_gate(monkeypatch,path):
    seen=[]
    monkeypatch.setattr(routes.RequestDiagnostics,'maybe_start',lambda *a,**k:None)
    monkeypatch.setattr(routes,'_check_csrf',lambda handler:True)
    monkeypatch.setattr(routes.governance_api,'handle_governance_api',lambda handler,parsed,method:seen.append((parsed.path,method)) or True)
    assert routes.handle_post(SimpleNamespace(),urlparse(path)) is True
    assert seen==[(path,'POST')]

@pytest.mark.parametrize('endpoint',['appearance','avatar'])
def test_default_bot_real_post_dispatch(monkeypatch,tmp_path,endpoint):
    import io,json,base64
    from PIL import Image
    from api import auth,profiles,bot_metadata
    from api.governance import loader
    home=tmp_path/'root';home.mkdir()
    (home/'config.yaml').write_text('platform_toolsets:\n  cli: [file]\nmcp_servers:\n  notion: {}\n')
    (home/'SOUL.md').write_text('Bot instructions')
    policy=loader.parse_governance_policy({'version':1,'mode':'enforce','bootstrap_admins':['admin@example.test']})
    loader.set_policy_loader(lambda:policy)
    monkeypatch.setattr(auth,'is_auth_enabled',lambda:True)
    monkeypatch.setattr(auth,'parse_cookie',lambda h:'test-session')
    monkeypatch.setattr(auth,'get_session_identity',lambda cookie:{'email':'admin@example.test','groups':[]})
    monkeypatch.setattr(profiles,'get_hermes_home_for_profile',lambda name:home if name=='default' else tmp_path/'missing')
    monkeypatch.setattr(routes,'_check_csrf',lambda h:True)
    image=io.BytesIO();Image.new('RGB',(2,2)).save(image,format='PNG')
    body={'name':'default','revision':0,'bot':{'title':'My own bot'},'avatar':'data:image/png;base64,'+base64.b64encode(image.getvalue()).decode()}
    raw=json.dumps(body).encode();handler=SimpleNamespace(headers={'Content-Length':str(len(raw))},rfile=io.BytesIO(raw),command='POST')
    responses=[]
    monkeypatch.setattr(routes,'j',lambda h,payload,**kw:responses.append((payload,kw.get('status',200))) or True)
    monkeypatch.setattr(routes,'bad',lambda h,error,status=400:responses.append(({'error':error},status)) or True)
    try:
        routes.handle_post(handler,urlparse('/api/profile/'+endpoint))
        assert responses and responses[-1][1]==200,responses
        assert responses[-1][0]['ok']
        result=bot_metadata.read_profile('default')
        assert result['bot_configuration']['prompt']=='SOUL.md'
        assert result['bot_configuration']['toolsets']==['file']
        if endpoint=='appearance':assert result['bot']['title']=='My own bot'
        else:assert bot_metadata.avatar_bytes('default').startswith(b'\x89PNG')
    finally:loader.set_policy_loader(None)
