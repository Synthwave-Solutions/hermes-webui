"""Local, synthetic DOM fixture using the actual tool renderer/reconciliation.

No provider, production session, browser automation or authenticated endpoint.
Run with Python, open the printed loopback URL, and use the visible controls.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = (
    "_rehydrateTransparentLiveRow", "_refreshTransparentLiveRow",
    "_transparentLiveRowAttributePairs", "_transparentLiveRowInteractiveState",
    "_materializeTransparentToolDetail", "_setTransparentCardOpen",
    "_setTransparentDetailMode", "_transparentToolRowHasDetail", "buildToolCard",
)


def page():
    source = (ROOT / "static/ui.js").read_text()
    chunks = []
    for name in FUNCTIONS:
        start = source.index("function " + name + "(")
        end = source.index("\nfunction ", start + 1)
        chunks.append(source[start:end])
    return ("""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>SynthPulse terminal output fixture</title><link rel="stylesheet" href="/style.css">
<style>body{margin:24px;background:#111827;color:#eee}button{margin:4px;padding:8px}#rows{max-width:800px;margin-top:20px}.tool-card{display:block}.tool-card-detail{display:none}.tool-card.open .tool-card-detail{display:block}#status{margin:12px}</style>
<h1>SynthPulse terminal output fixture</h1>
<p>Synthetic deferred-row lifecycle; actual renderer, refresh and materialization functions.</p>
<button onclick="reset()">Reset pending</button><button onclick="openCard()">Open card</button>
<button onclick="complete('success')">Complete successfully</button>
<button onclick="complete('failed')">Complete with escaped error</button>
<button onclick="complete('empty')">Replace with no details</button>
<div id="status" role="status"></div><div id="rows"></div>
<script>
const esc=s=>String(s??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
const li=()=>'',toolIcon=()=>'',_toolActionKind=()=> 'shell',_toolCardAllowsDetail=()=>true;
const _toolDisplayName=()=> 'Terminal',_toolActionLabelText=()=> 'Terminal';
const _toolCardPreviewText=()=>'',_formatToolArgPreview=()=>'',_toolDetailLeadLabel=()=> 'Shell';
const _toolDetailLeadText=(kind,tc)=>tc.args&&tc.args.command?'$ '+tc.args.command:'';
const _isMemorySave=()=>false,_isSkillUpdate=()=>false,_snippetLooksLikeDiff=()=>false;
const _wireTransparentHeaderToggle=()=>{},_attachCopyButton=()=>{};
const _refreshTransparentThinkingLiveRow=()=>false;
let latest=null,row=null;
const _transparentToolCallFromRowDataset=()=>latest;
const _transparentToolStatus=()=> 'Completed';
""" + "\n".join(chunks) + """
function make(tc){
 const node=buildToolCard(tc);node.classList.add('transparent-event-row');
 // Establish the same deferred row contract as the settled decorator.
 if(_transparentToolRowHasDetail(tc)){
  const detail=node.querySelector('.tool-card-detail');if(detail)detail.remove();
  node._deferredToolCall=tc;node.setAttribute('data-transparent-detail-deferred','1');
 }
 return node;
}
function reset(){
 latest={name:'terminal',args:{command:'printf fixture'},snippet:'',done:false};
 row=make(latest);document.getElementById('rows').replaceChildren(row);
 document.getElementById('status').textContent='Pending synthetic tool';
}
function openCard(){_setTransparentCardOpen(row.querySelector('.tool-card'),true);}
function complete(kind){
 latest={name:'terminal',args:kind==='empty'?{}:{command:'printf fixture'},done:true,
  snippet:kind==='empty'?'':kind==='failed'?'<img src=x onerror="alert(1)"> fixture error':'fixture stdout',is_error:kind==='failed'};
 row=_refreshTransparentLiveRow(row,make(latest),{});
 document.getElementById('status').textContent='Completed synthetic tool: '+kind;
}
reset();
</script>""").encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body, kind = page(), "text/html; charset=utf-8"
        elif self.path == "/style.css":
            body, kind = (ROOT / "static/style.css").read_bytes(), "text/css"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    print(f"http://127.0.0.1:{server.server_port}", flush=True)
    server.serve_forever()
