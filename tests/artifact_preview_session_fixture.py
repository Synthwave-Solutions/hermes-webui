"""Loopback CUA fixture: actual preview/download JS, synthetic PDF/HTML only.

The HTTP authorization boundary is deliberately a fixture: only the known
artifact-a session may fetch the known synthetic files. The Python regression
suite separately exercises the actual media handler. PDF.js uses the production
CDN loader; no bundled PDF.js asset exists in this checkout.
"""
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parents[1]
REQUESTS = []


def tiny_pdf():
    stream = b"BT /F1 18 Tf 32 100 Td (SynthPulse synthetic artifact) Tj ET"
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 350 160] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"]
    data = b"%PDF-1.4\n"; offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data)); data += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n" + b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    return data + f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()


PDF = tiny_pdf()
HTML = b"<!doctype html><meta charset=utf-8><title>SynthPulse synthetic artifact</title><h1>SynthPulse synthetic artifact</h1><p>Only this synthetic document is being tested.</p>"
FILES = {"/synthetic/report.pdf": (PDF, "application/pdf"),
         "/synthetic/report.html": (HTML, "text/html; charset=utf-8"),
         "/synthetic/large.pdf": (PDF + b" " * (4 * 1024 * 1024), "application/pdf"),
         "/synthetic/large.html": (HTML + b"<!--" + b"x" * (2 * 1024 * 1024) + b"-->", "text/html; charset=utf-8")}


def page():
    ui = (REPO / "static/ui.js").read_text()
    previews = ui[ui.index("let _pdfjsReady=false"):ui.index("function renderMermaidBlocks(")]
    workspace = (REPO / "static/workspace.js").read_text()
    downloads = workspace[workspace.index("async function downloadArtifact("):workspace.index("// ── Render breadcrumb for file preview mode")]
    return '''<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>SynthPulse artifact session QA</title><link rel=stylesheet href=/static/style.css>
<style>body{display:block;overflow:auto;padding:20px;max-width:850px;margin:auto}button,select{padding:9px;margin:4px}#preview{margin:20px 0}.pdf-preview-body{max-height:none}pre{white-space:pre-wrap;overflow-wrap:anywhere}#toast{min-height:35px}</style>
<h1>Artifact session QA</h1><p>Real production PDF/HTML preview and download helpers. Synthetic files and synthetic session authorization only. PDF rendering uses the production PDF.js CDN loader.</p>
<label>Format <select id=kind><option value=pdf>PDF</option><option value=html>HTML</option></select></label>
<label>Case <select id=mode><option value=normal>Normal</option><option value=large>Too large for preview</option><option value=fetch_error>Preview request fails</option></select></label>
<label><input type=checkbox id=delay>Hold preview response</label>
<div><button id=render>Render from original chat</button><button id=switch>Switch to another chat</button><button id=release>Release held preview</button></div>
<p id=current>Current chat: artifact-a</p><div id=preview></div><div id=toast role=status></div>
<div><button id=missing>Download without session (expect denied)</button><button id=wrong>Download with wrong session (expect denied)</button></div>
<pre id=evidence></pre><script>
const $=id=>document.getElementById(id);const S={session:{session_id:'artifact-a'}};
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const translations={pdf_download:'Download PDF',pdf_too_large:'Too large for inline preview',pdf_error:'Preview unavailable; use download',html_open_full:'Open full HTML',html_error:'Preview unavailable; use download',html_too_large:'Too large for inline preview',html_sandbox_label:'HTML preview',artifact_download_denied:'Download denied: session authorization missing',artifact_download_failed:'Download failed',artifact_download_invalid:'Invalid download response',artifact_download_missing:'Artifact missing',downloading:'Handed bytes to browser'};
const t=(key,value)=>translations[key]||key;const showToast=text=>$('toast').textContent=text;
const nativeFetch=window.fetch.bind(window);let releasePreview=null;let fixturePath='/synthetic/report.pdf';
async function refreshEvidence(){const r=await nativeFetch('/fixture/evidence');$('evidence').textContent=JSON.stringify(await r.json(),null,2)}
window.fetch=async(url,options={})=>{
 const u=new URL(url,location.href);const preview=u.pathname==='/api/media'&&!u.searchParams.has('download')&&!u.searchParams.has('inline');
 const mode=$('mode').value;
 if(preview&&$('delay').checked)await new Promise(resolve=>releasePreview=resolve);
 const headers=new Headers(options.headers||{});if(preview&&mode==='fetch_error')headers.set('X-Fixture-Preview-Fail','1');
 const response=await nativeFetch(url,{...options,headers});await refreshEvidence();return response;
};
</script><script>''' + previews + downloads + '''
$('render').onclick=()=>{
 S.session={session_id:'artifact-a'};$('current').textContent='Current chat: artifact-a';$('toast').textContent='';
 const kind=$('kind').value;fixturePath='/synthetic/'+($('mode').value==='large'?'large':'report')+'.'+kind;
 $('preview').innerHTML='<div class="'+kind+'-preview-load" data-path="'+fixturePath+'">Loading synthetic preview…</div>';
 if(kind==='pdf')loadPdfInline($('preview'));else loadHtmlInline($('preview'));
};
$('switch').onclick=()=>{S.session={session_id:'another-chat'};$('current').textContent='Current chat: another-chat (original preview retained for this test)'};
$('release').onclick=()=>{if(releasePreview){const fn=releasePreview;releasePreview=null;fn()}};
$('missing').onclick=()=>downloadArtifact('/api/media?path='+encodeURIComponent(fixturePath),'report');
$('wrong').onclick=()=>downloadArtifact('/api/media?path='+encodeURIComponent(fixturePath)+'&session_id=another-chat','report');
refreshEvidence();
</script></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_bytes(self, status, raw, mime="application/json", *, filename=None, download=False):
        if isinstance(raw, str):
            raw = raw.encode()
        self.send_response(status); self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(raw))); self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", ("attachment" if download else "inline") + '; filename="' + filename + '"')
        self.end_headers(); self.wfile.write(raw)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/":
            return self.send_bytes(200, page(), "text/html; charset=utf-8")
        if u.path == "/static/style.css":
            return self.send_bytes(200, (REPO / "static/style.css").read_bytes(), "text/css")
        if u.path == "/fixture/evidence":
            return self.send_bytes(200, json.dumps({"requests": REQUESTS[-50:], "file_sha256": {p: sha256(v[0]).hexdigest() for p, v in FILES.items()}}))
        if u.path != "/api/media":
            return self.send_bytes(404, '{"error":"Unknown fixture route"}')
        path = q.get("path", [""])[0]; sid = q.get("session_id", [""])[0]
        status = 200 if path in FILES and sid == "artifact-a" else 403
        if self.headers.get("X-Fixture-Preview-Fail") == "1":
            status = 503
        REQUESTS.append({"path": path, "session_id": sid, "download": q.get("download") == ["1"], "inline": q.get("inline") == ["1"], "status": status})
        if status != 200:
            return self.send_bytes(status, '{"error":"Synthetic fixture request denied or failed"}')
        raw, mime = FILES[path]
        return self.send_bytes(200, raw, mime, filename=Path(path).name, download=q.get("download") == ["1"])


if __name__ == "__main__":
    port = int(sys.argv[1])
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Synthetic artifact QA: http://127.0.0.1:{server.server_address[1]}", flush=True)
    server.serve_forever()
