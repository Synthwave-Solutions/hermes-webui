"""Preview actions retain the same session context as their successful fetch.

Runs real frontend helpers and the server media decision with synthetic files.
No provider, production account, or browser download is exercised here.
"""
import io
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

from api import routes


def render_action(path, kind, outcome, session_id):
    source = (Path(__file__).parents[1] / "static/ui.js").read_text()
    helper = source[source.index("let _pdfjsReady=false"):source.index("function renderMermaidBlocks(")]
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the actual frontend helpers")
    driver = r"""
const fs=require('fs'); const spec=JSON.parse(fs.readFileSync(0,'utf8'));
let capturedHtml='',requests=[],timers=[];
const S={session:{session_id:spec.sid}};
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('"','&quot;');
const t=k=>k;
const setTimeout=fn=>{timers.push(fn);return timers.length};
const element={dataset:{path:spec.path},parentNode:{},setAttribute(){},replaceWith(wrap){capturedHtml=wrap.innerHTML},
 set outerHTML(value){capturedHtml=value}};
const container={querySelectorAll(){return [element]}};
const document={head:{appendChild(){}},createElement(){return {innerHTML:'',querySelector(){return {appendChild(){}}}}}};
const window={addEventListener(){},_pdfjsLib:{getDocument(){return {promise:Promise.resolve({numPages:0})}}}};
const fetch=async url=>{
 requests.push(url);
 if(spec.outcome==='fetch_error') throw new Error('synthetic fetch failure');
 return {ok:true,arrayBuffer:async()=>new ArrayBuffer(spec.outcome==='large'?4*1024*1024+1:8),
         text:async()=>spec.outcome==='large'?'x'.repeat(2*1024*1024+1):'<html>synthetic</html>'};
};
""" + helper + r"""
_pdfjsReady=spec.outcome!=='cdn_timeout';
if(spec.kind==='pdf') loadPdfInline(container); else loadHtmlInline(container);
// The original callback may settle after the foreground chat changed.
S.session={session_id:'another-chat'};
timers.forEach(fn=>fn());
setImmediate(()=>{
 const match=capturedHtml.match(/href="([^"]+)"/);
 if(!match) throw new Error('actual helper did not render an action');
 process.stdout.write(JSON.stringify({preview:requests[0]||null,action:match[1].replaceAll('&amp;','&')}));
});
"""
    result = subprocess.run([node, "-e", driver], input=json.dumps({"path": str(path), "sid": session_id, "kind": kind, "outcome": outcome}),
                            text=True, capture_output=True, timeout=10, check=True)
    return json.loads(result.stdout)


@pytest.mark.parametrize("kind,outcome", [
    ("pdf", "normal"), ("pdf", "large"), ("pdf", "fetch_error"), ("pdf", "cdn_timeout"),
    ("html", "normal"), ("html", "large"), ("html", "fetch_error"),
])
def test_preview_action_keeps_origin_session_across_success_fallback_and_chat_switch(tmp_path, monkeypatch, kind, outcome):
    artifact = tmp_path / ("synthetic-π&报告." + kind)
    artifact.write_bytes(b"%PDF-1.4 synthetic" if kind == "pdf" else b"<html>synthetic</html>")
    workspace = tmp_path / "separate-workspace"
    workspace.mkdir()
    session_id = "synthetic-artifact-session"
    urls = render_action(artifact, kind, outcome, session_id)
    action_query = parse_qs(urlparse(urls["action"]).query)
    assert action_query.get("session_id") == [session_id]
    assert action_query["path"] == [str(artifact)]
    if urls["preview"]:
        assert parse_qs(urlparse(urls["preview"]).query)["session_id"] == [session_id]

    monkeypatch.setenv("MEDIA_ALLOWED_ROOTS", "")
    monkeypatch.setattr("api.auth.is_auth_enabled", lambda: False)
    monkeypatch.setattr("api.workspace.get_last_workspace", lambda: str(workspace))
    def get_session(sid):
        if sid != session_id:
            raise ValueError("synthetic unavailable session")
        return SimpleNamespace(messages=[{"role": "assistant", "content": "MEDIA:" + str(artifact)}])
    monkeypatch.setattr(routes, "get_session", get_session)
    monkeypatch.setattr(routes, "_serve_file_bytes", lambda *args, **kwargs: 200)
    monkeypatch.setattr(routes, "bad", lambda handler, message, status=400: status)
    handler = SimpleNamespace(wfile=io.BytesIO())
    assert routes._handle_media(handler, urlparse(urls["action"])) == 200
    # Carrying a session ID is not permission: absent, unknown and unmentioned
    # artifacts still go through the unchanged server-side allow-list decision.
    without_session = urls["action"].replace("&session_id=" + session_id, "")
    assert routes._handle_media(handler, urlparse(without_session)) == 403
    unknown_session = urls["action"].replace(session_id, "another-chat")
    assert routes._handle_media(handler, urlparse(unknown_session)) == 403
    monkeypatch.setattr(routes, "get_session", lambda sid: SimpleNamespace(messages=[]))
    assert routes._handle_media(handler, urlparse(urls["action"])) == 403


@pytest.mark.parametrize("kind", ["pdf", "html"])
def test_sessionless_preview_does_not_invent_an_origin_session(tmp_path, kind):
    urls = render_action(tmp_path / ("synthetic." + kind), kind, "normal", "")
    assert "session_id" not in parse_qs(urlparse(urls["action"]).query)
