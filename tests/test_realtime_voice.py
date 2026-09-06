import io
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from api import realtime_voice as voice


class Handler:
    command = "POST"
    def __init__(self, body=None):
        data = json.dumps(body or {}).encode()
        self.rfile = io.BytesIO(data)
        self.wfile = io.BytesIO()
        self.headers = {"Content-Length": str(len(data)), "Content-Type": "application/json"}
        self.status = None
    def send_response(self, status): self.status = status
    def send_header(self, key, value): pass
    def end_headers(self): pass
    def payload(self): return json.loads(self.wfile.getvalue())


@pytest.fixture(autouse=True)
def isolation(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-key")
    monkeypatch.setenv("SYNPULSE_REALTIME_VOICE_ENABLED", "1")
    voice._ATTEMPTS.clear()


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SYNPULSE_REALTIME_VOICE_ENABLED")
    assert not voice.configured()


def test_sdp_exchange_keeps_key_server_only_and_tools_disabled():
    calls = []
    def post(url, **kw):
        calls.append((url, kw))
        return SimpleNamespace(status_code=201, text="v=0\nanswer")
    answer = voice.create_call("v=0\noffer", "alice", post=post)
    assert answer == "v=0\nanswer"
    assert "fixture-key" not in answer
    config = json.loads(calls[0][1]["files"]["session"][1])
    assert config["tools"] == []
    assert config["audio"]["input"]["turn_detection"]["create_response"] is False
    assert calls[0][1]["headers"]["OpenAI-Safety-Identifier"] != "alice"
    assert calls[0][1]["timeout"] == 25


def test_provider_error_does_not_echo_secret_or_response():
    def post(*a, **kw):
        return SimpleNamespace(status_code=401, text="fixture-key upstream secret")
    with pytest.raises(RuntimeError, match="unavailable") as exc:
        voice.create_call("v=0", "alice", post=post)
    assert "fixture-key" not in str(exc.value)


def test_invalid_sdp_never_calls_provider():
    def post(*a, **kw): pytest.fail("must not call")
    for value in ("https://attacker", "v=0" + "x"*65536, {}, None):
        with pytest.raises(ValueError):
            voice.create_call(value, "alice", post=post)


def test_rate_limit_is_actor_scoped():
    post = lambda *a, **kw: SimpleNamespace(status_code=201, text="v=0")
    for _ in range(4): voice.create_call("v=0", "alice", post=post)
    with pytest.raises(ValueError, match="one minute"):
        voice.create_call("v=0", "alice", post=post)
    assert voice.create_call("v=0", "bob", post=post) == "v=0"


@pytest.mark.parametrize("identity,visible,status", [(None, True, 401),
    ({"email":"outsider@example.test"}, False, 404),
    ({"email":"alice@example.test"}, True, 200)])
def test_handler_auth_and_session_boundary(monkeypatch, identity, visible, status):
    from api import routes
    from api.governance import enforce
    monkeypatch.setattr(enforce, "_request_identity", lambda h: identity)
    monkeypatch.setattr(routes, "get_session", lambda *a, **kw: SimpleNamespace())
    monkeypatch.setattr(routes, "_session_visible_to_request", lambda *a: visible)
    monkeypatch.setattr(voice, "create_call", lambda *a, **kw: "v=0\nanswer")
    handler = Handler({"session_id":"voicefixture1", "sdp":"v=0"})
    voice.handle(handler)
    assert handler.status == status
    if status == 200: assert handler.payload()["sdp"] == "v=0\nanswer"


def test_revocation_during_negotiation_denies_answer(monkeypatch):
    from api import routes
    from api.governance import enforce
    monkeypatch.setattr(enforce, "_request_identity", lambda h: {"email":"alice@example.test"})
    monkeypatch.setattr(routes, "get_session", lambda *a, **kw: SimpleNamespace())
    checks = iter([True, False])
    monkeypatch.setattr(routes, "_session_visible_to_request", lambda *a: next(checks))
    monkeypatch.setattr(voice, "create_call", lambda *a, **kw: "v=0\nanswer")
    handler = Handler({"session_id":"voicefixture1", "sdp":"v=0"})
    voice.handle(handler)
    assert handler.status == 404
    assert "sdp" not in handler.payload()


def test_frontend_transport_lifecycle():
    node = shutil.which("node")
    if not node: pytest.skip("Node required")
    path = Path(__file__).resolve().parents[1] / "static/realtime_voice.js"
    script = r"""
const assert=require('node:assert/strict');
const {SynPulseVoice}=require(process.argv[1]);
(async()=>{
let sid='one', submitted=[], spoken=[], tracks=[], peers=[], audioCount=0;
const deps={
 current:()=>sid,audio:()=>audioCount++,status:()=>{},error:e=>{throw Error(e)},silence:()=>{},
 media:async()=>{const t={enabled:true,stopped:false,stop(){this.stopped=true}};tracks.push(t);return {getTracks:()=>[t]};},
 peer:()=>{const dc={readyState:'open',send:x=>spoken.push(JSON.parse(x)),close(){}};
 const p={dc,addTrack(){},createDataChannel:()=>dc,createOffer:async()=>({sdp:'v=0'}),
 setLocalDescription:async()=>{},setRemoteDescription:async()=>{},close(){this.closed=true}};
 peers.push(p);return p;},
 connect:async()=>({sdp:'v=0'}),submit:(text,id)=>submitted.push([text,id])
};
const v=new SynPulseVoice(deps);
await v.start('one');assert.equal(tracks[0].enabled,false);
v.mic(true);assert.equal(tracks[0].enabled,true);
v.mic(false);assert.equal(tracks[0].enabled,false);
v.event({type:'conversation.item.input_audio_transcription.completed',item_id:'a',transcript:'Do work'});
v.event({type:'conversation.item.input_audio_transcription.completed',item_id:'a',transcript:'Do work'});
assert.deepEqual(submitted,[['Do work','one']]);
v.speak('Done','one');assert(spoken.some(e=>e.type==='response.create'));
v.interrupt();assert.equal(spoken.at(-1).type,'output_audio_buffer.clear');
sid='other';v.event({type:'response.done'});assert.equal(v.state,'off');assert(tracks[0].stopped);assert(peers[0].closed);
// Late callbacks from the old peer cannot cross into the replacement session.
sid='old';await v.start('old');
const oldPeer=peers.at(-1),oldMessage=oldPeer.dc.onmessage,oldTrack=oldPeer.ontrack,oldState=oldPeer.onconnectionstatechange;
sid='new';await v.start('new');
const before=submitted.length;
oldMessage({data:JSON.stringify({type:'conversation.item.input_audio_transcription.completed',item_id:'late',transcript:'old private text'})});
oldTrack({streams:[{}]});oldPeer.connectionState='failed';oldState();
assert.equal(submitted.length,before);assert.equal(audioCount,0);assert.equal(v.sid,'new');v.stop();
// Pending permission completion after teardown must stop the newly acquired track.
sid='one';let resolve;deps.media=()=>new Promise(r=>resolve=r);
const pending=v.start('one');v.stop();
const late={enabled:true,stopped:false,stop(){this.stopped=true}};
resolve({getTracks:()=>[late]});await pending;assert(late.stopped);assert.equal(v.state,'off');
})().catch(e=>{console.error(e);process.exit(1)});
"""
    subprocess.run([node, "-e", script, str(path)], check=True, capture_output=True, text=True)


def test_real_post_dispatch_requires_csrf(monkeypatch):
    from urllib.parse import urlparse
    from api import routes
    handler = Handler()
    monkeypatch.setattr(routes, "_check_csrf", lambda h: False)
    monkeypatch.setattr(routes, "_csrf_rejection_error", lambda h: "csrf")
    monkeypatch.setattr(voice, "create_call", lambda *a: pytest.fail("no provider call"))
    routes.handle_post(handler, urlparse("/api/voice/realtime/call"))
    assert handler.status == 403


def test_voice_routes_require_chat_permission():
    from api.governance.catalog import route_permission
    assert route_permission("/api/voice/realtime/call", "POST") == "chat:use"
    assert route_permission("/api/voice/realtime/capability", "GET") == "chat:use"

def test_revoke_negotiated_call_hangs_up_without_returning_sdp():
    calls = []
    def post(url, **kw):
        calls.append(url)
        return SimpleNamespace(status_code=201, text="v=0", headers={"Location": "/v1/realtime/calls/rtc_fixture"})
    with pytest.raises(PermissionError):
        voice.create_call("v=0", "alice", post=post, access_check=lambda: False)
    assert calls[-1] == "https://api.openai.com/v1/realtime/calls/rtc_fixture/hangup"


def test_user_voice_capability_and_disabled_errors_are_provider_neutral(monkeypatch):
    from api import routes
    from api.governance import enforce
    monkeypatch.setattr(enforce, "_request_identity", lambda h: {"email":"alice@example.test"})
    monkeypatch.setattr(routes, "get_session", lambda *a, **kw: SimpleNamespace())
    monkeypatch.setattr(routes, "_session_visible_to_request", lambda *a: True)
    monkeypatch.delenv("SYNPULSE_REALTIME_VOICE_ENABLED")
    for capability in (True, False):
        handler = Handler({"session_id":"voicefixture1", "sdp":"v=0"})
        voice.handle(handler, capability=capability)
        assert handler.status == (200 if capability else 503)
        visible = json.dumps(handler.payload()).lower()
        assert "openai" not in visible
        assert "api key" not in visible
        assert "billing" not in visible
