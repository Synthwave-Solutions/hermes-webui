"""Real HTTP handler coverage for non-admin bot selection and denied bodies."""
import http.client
import json
import socket
import threading
from http.server import ThreadingHTTPServer
import pytest
import server
from api import routes
from api.governance import enforce, loader
from api.governance.loader import parse_governance_policy

@pytest.fixture
def endpoint(monkeypatch):
    identity = {'email': 'member@example.test'}
    policy = parse_governance_policy({'version':1,'mode':'enforce','default_effect':'deny',
        'roles':{'member':{'grants':{'permissions':['chat:use','profiles:read'],
                                  'profiles':['default','research'],'routes':['*']}}},
        'users':{'member@example.test':{'roles':['member']}}})
    monkeypatch.setattr(loader,'get_policy',lambda:policy)
    monkeypatch.setattr(enforce,'_request_identity',lambda h:identity)
    monkeypatch.setattr(enforce,'_audit_decision',lambda *a,**k:None)
    monkeypatch.setattr(server,'check_auth',lambda *a:True)
    monkeypatch.setattr(server,'_set_owner_context',lambda *a:None)
    monkeypatch.setattr(server,'_clear_owner_context',lambda:None)
    monkeypatch.setattr(server,'get_profile_cookie',lambda h:None)
    monkeypatch.setattr(routes,'_check_csrf',lambda h:True)
    monkeypatch.setattr('api.profiles.switch_profile',lambda name,process_wide: {
        'ok':True,'active':name,'process_wide':process_wide})
    monkeypatch.setattr('api.config.invalidate_models_cache',lambda:None)
    monkeypatch.setattr('api.gateway_watcher.restart_watcher_for_profile',lambda name:None)
    monkeypatch.setattr('api.helpers.build_profile_cookie',lambda name,h:'profile='+name)
    httpd=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    yield httpd.server_address
    httpd.shutdown();httpd.server_close();thread.join()

def test_member_can_select_allowed_bot_without_admin(endpoint):
    conn=http.client.HTTPConnection(*endpoint,timeout=3)
    conn.request('POST','/api/profile/switch',json.dumps({'name':'research'}),
                 {'Content-Type':'application/json'})
    response=conn.getresponse();body=json.loads(response.read())
    assert response.status==200,body
    assert body['active']=='research'
    assert body['process_wide'] is False
    conn.request('POST','/api/profile/switch',json.dumps({'name':'private'}),
                 {'Content-Type':'application/json'})
    response=conn.getresponse();assert response.status==403
    assert json.loads(response.read())['error']=='profile_not_allowed'
    conn.close()

def test_rejected_unread_post_does_not_parse_body_as_http(endpoint):
    sock=socket.create_connection(endpoint,timeout=3)
    body=b'{"name":"private"}'
    sock.sendall(b'POST /api/profile/create HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body+
                 b'GET /api/profiles HTTP/1.1\r\nHost: localhost\r\n\r\n')
    chunks=[]
    while True:
        part=sock.recv(65536)
        if not part:break
        chunks.append(part)
    sock.close()
    result=b''.join(chunks)
    assert b'403' in result
    assert b'501' not in result
    assert result.count(b'HTTP/1.1')==1
