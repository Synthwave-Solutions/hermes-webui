import io
from types import SimpleNamespace
from urllib.parse import urlparse, urlencode
from unittest.mock import patch

import pytest
from api import routes


@pytest.mark.parametrize("extension", [".html", ".png"])
def test_media_explicit_download_overrides_inline(tmp_path, monkeypatch, extension):
    monkeypatch.setenv("MEDIA_ALLOWED_ROOTS", str(tmp_path))
    target = tmp_path / ("index" + extension)
    target.write_bytes(b"artifact bytes")
    handler = SimpleNamespace(wfile=io.BytesIO())
    with patch("api.auth.is_auth_enabled", return_value=False), patch.object(routes, "_serve_file_bytes") as serve:
        routes._handle_media(handler, urlparse("/api/media?" + urlencode({
            "path": str(target), "inline": "1", "download": "1"})))
    assert serve.call_args.args[3] == "attachment"
    assert serve.call_args.kwargs.get("csp") is None


def test_browser_download_waits_for_bytes_and_reports_errors():
    import shutil
    import subprocess
    from pathlib import Path
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required")
    source = (Path(__file__).parents[1] / "static/workspace.js").read_text()
    helper = source[source.index("async function downloadArtifact("):source.index("\nfunction downloadFile(")]
    script = r"""
const assert=require('node:assert/strict');
const window={location:{href:'https://example.test/',origin:'https://example.test'}};
let clicked=0,removed=0,toasts=[],timers=[];
const setTimeout=(fn)=>{timers.push(fn);return timers.length};
const clearTimeout=()=>{};
const document={body:{appendChild(){}},createElement(){return {click(){clicked++},remove(){removed++}}}};
const showToast=(...args)=>toasts.push(args);
const t=(key)=>key;
let fetch;
""" + helper + r"""
(async()=>{
 for(const status of [401,403,404,500]){
  fetch=async()=>({ok:false,status});
  assert.equal(await downloadArtifact('/api/media?path=/tmp/index.htm','index.htm'),false);
  assert.equal(clicked,0);
  assert.equal(toasts.at(-1)[2],'error');
 }
 let resolveBytes;
 fetch=async()=>({ok:true,headers:new Headers({'Content-Disposition':'attachment; filename="index.htm"'}),blob:()=>new Promise(resolve=>resolveBytes=resolve)});
 const pending=downloadArtifact('/api/media?path=/tmp/index.htm','index.htm');
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(clicked,0);
 resolveBytes(new Blob(['<html>snapshot</html>'],{type:'text/html'}));
 assert.equal(await pending,true);
 assert.equal(clicked,1);
 assert.equal(removed,1);
 fetch=async()=>{throw new Error('network')};
 assert.equal(await downloadArtifact('/api/media?path=/tmp/index.htm','index.htm'),false);
 assert.equal(clicked,1);
 timers.forEach(fn=>fn());
})().catch(error=>{console.error(error);process.exit(1)});
"""
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)


def test_raw_html_download_does_not_use_inline_preview(tmp_path):
    target = tmp_path / "index.htm"
    target.write_text("<html>download original</html>")
    session = SimpleNamespace(workspace=str(tmp_path))
    with patch.object(routes, "get_session_for_file_ops", return_value=session), patch.object(routes, "_serve_file_bytes") as serve, patch.object(routes, "_serve_inline_html_preview") as preview:
        routes._handle_file_raw(object(), urlparse("/api/file/raw?session_id=fixture&path=index.htm&inline=1&download=1"))
    preview.assert_not_called()
    assert serve.call_args.args[3] == "attachment"


@pytest.mark.parametrize("extension,mime", [
    (".html", "text/html"), (".pdf", "application/pdf"),
    (".png", "image/png"), (".zip", "application/octet-stream"),
])
@pytest.mark.parametrize("endpoint", ["media", "file/raw", "escape/file/raw"])
def test_download_endpoints_return_attachment_filename_and_exact_bytes(tmp_path, monkeypatch, extension, mime, endpoint):
    target = tmp_path / ("Report é ✓" + extension)
    payload = b"isolated artifact bytes\x00\x01"
    target.write_bytes(payload)
    monkeypatch.setenv("MEDIA_ALLOWED_ROOTS", str(tmp_path))
    headers = {}
    statuses = []
    handler = SimpleNamespace(
        wfile=io.BytesIO(), headers={},
        send_response=statuses.append,
        send_header=lambda key, value: headers.__setitem__(key, value),
        end_headers=lambda: None,
    )
    session = SimpleNamespace(workspace=str(tmp_path))
    with patch("api.auth.is_auth_enabled", return_value=False), patch.object(routes, "get_session_for_file_ops", return_value=session), patch.object(routes, "raw_authorized_escape_target", return_value=(tmp_path, target)):
        parsed = urlparse("/api/" + endpoint + "?" + urlencode({
            "session_id": "fixture", "token": "fixture-only", "path": str(target) if endpoint == "media" else target.name,
            "inline": "1", "download": "1",
        }))
        {"media": routes._handle_media, "file/raw": routes._handle_file_raw, "escape/file/raw": routes._handle_escape_file_raw}[endpoint](handler, parsed)
    assert statuses == [200]
    assert headers["Content-Type"] == mime
    assert headers["Content-Disposition"].startswith("attachment;")
    assert "filename*=UTF-8''Report%20%C3%A9%20%E2%9C%93" in headers["Content-Disposition"]
    assert handler.wfile.getvalue() == payload


def test_download_response_contract_and_authoritative_filename():
    import shutil
    import subprocess
    from pathlib import Path
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required")
    source = (Path(__file__).parents[1] / "static/workspace.js").read_text()
    helper = source[source.index("async function downloadArtifact("):source.index("\nfunction downloadFile(")]
    script = r"""
const assert=require('node:assert/strict');
const window={location:{href:'https://example.test/',origin:'https://example.test'}};
let saves=[],toasts=[],timers=[],readBytes=0;
const setTimeout=fn=>{timers.push(fn);return timers.length};
const clearTimeout=()=>{};
const document={body:{appendChild(){}},createElement(){return {click(){saves.push(this.download)},remove(){}}}};
const showToast=(...args)=>toasts.push(args);
const t=key=>key;
let fetch;
function response(disposition){return {ok:true,headers:new Headers(disposition?{'Content-Disposition':disposition}:{}),blob:async()=>{readBytes++;return new Blob(['fixture bytes'])}}}
""" + helper + r"""
(async()=>{
 for(const disposition of [null,'inline; filename="login.html"']){
  fetch=async()=>response(disposition);
  assert.equal(await downloadArtifact('/api/media?path=/tmp/image.png','Friendly image caption'),false,'A 200 error/login response must not be downloaded');
  assert.equal(readBytes,0);assert.deepEqual(saves,[]);
  assert.equal(toasts.at(-1)[0],'artifact_download_invalid');
 }
 for(const [header,expected] of [
  ['attachment; filename="fallback.png"; filename*=UTF-8\'\'Rapport%20%C3%A9%20%E2%9C%93.png','Rapport é ✓.png'],
  ['attachment; filename="real image.png"','real image.png'],
  ['attachment; filename="safe.png"; filename*=UTF-8\'\'%XX','safe.png'],
  ['attachment; filename="../safe.png"','safe.png'],
 ]){
  fetch=async()=>response(header);
  assert.equal(await downloadArtifact('/api/media?path=/tmp/image.png','Friendly image caption'),true);
  assert.equal(saves.at(-1),expected);
 }
 fetch=async()=>({ok:false,status:404});
 assert.equal(await downloadArtifact('/api/media?path=/tmp/missing.htm','missing.htm'),false);
 assert.equal(toasts.at(-1)[0],'artifact_download_missing');
 assert.equal(saves.length,4);
 timers.forEach(fn=>fn());
})().catch(error=>{console.error(error);process.exit(1)});
"""
    subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)
