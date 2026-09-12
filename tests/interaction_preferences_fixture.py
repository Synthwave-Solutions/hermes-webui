"""Loopback form + real preference store. Synthetic identities; no provider calls.

Run with the repo's test Python: tests/interaction_preferences_fixture.py PORT.
The UI is extracted from the actual index and uses the production JS unchanged.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parents[1]
STATE = Path(tempfile.mkdtemp(prefix="synthpulse-preferences-e2e-state-")).resolve()
os.environ["HERMES_WEBUI_STATE_DIR"] = str(STATE)
sys.path.insert(0, str(REPO))
from api import config, interaction_preferences as preferences, personal_context
config.STATE_DIR = STATE


def fixture_session(identity, sid):
    if sid not in {"first-chat", "second-chat"}:
        raise PermissionError("Unknown fixture conversation")
    return SimpleNamespace(session_id=sid, owner_email=identity["email"])


personal_context.session_for = fixture_session


def page():
    source = (REPO / "static/index.html").read_text()
    start = source.index('            <div class="settings-field" id="interactionPreferences"')
    end = source.index('            <div class="settings-field">', start + 1)
    return '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SynthPulse clarification preferences QA</title><link rel="stylesheet" href="/static/style.css">
<style>body{display:block;overflow:auto;margin:24px auto;padding:16px;max-width:720px}select{max-width:100%;padding:8px}button{padding:8px}</style>
<h1>Clarification preferences QA</h1><p>Synthetic actors, real preference storage and production form code. No model or external connection.</p>
<label>Actor <select id="actor"><option>alice</option><option>bob</option></select></label>
<label>Conversation <select id="chat"><option value="first-chat">First conversation</option><option value="second-chat">Second conversation</option><option value="">No conversation</option></select></label>
<label>Network <select id="network"><option>normal</option><option>offline</option><option>slow</option></select></label>
<button id="release">Complete waiting request</button>
''' + source[start:end] + '''
<pre id="evidence"></pre>
<script>
window.$=id=>document.getElementById(id);window.S={session:{session_id:'first-chat'}};window.requests=[];
$('chat').onchange=()=>{S.session=$('chat').value?{session_id:$('chat').value}:null;};
$('actor').onchange=()=>loadInteractionPreferences();
window.api=async(url,options={})=>{
 const actor=$('actor').value;const network=$('network').value;
 requests.push({url,method:options.method||'GET',body:options.body?JSON.parse(options.body):null,actor});
 $('evidence').textContent=JSON.stringify(requests,null,2);
 if(network==='offline')throw new Error('Synthetic network failure');
 if(network==='slow')await new Promise(resolve=>$('release').onclick=resolve);
 const response=await fetch(url,{...options,headers:{'Content-Type':'application/json','X-QA-Actor':actor}});
 const data=await response.json();if(!response.ok)throw new Error(data.error);return data;
};
</script><script src="/static/interaction_preferences.js"></script><script>loadInteractionPreferences();</script>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, data, content_type="application/json"):
        raw = data.encode() if isinstance(data, str) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self.reply(200, page(), "text/html; charset=utf-8")
        if parsed.path in {"/static/interaction_preferences.js", "/static/style.css"}:
            return self.reply(200, (REPO / parsed.path[1:]).read_text(),
                              "text/javascript" if parsed.path.endswith(".js") else "text/css")
        if parsed.path == "/api/interaction/preferences":
            return self.preferences(parsed)
        return self.reply(404, {"error": "Not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/interaction/preferences":
            return self.reply(404, {"error": "Not found"})
        return self.preferences(parsed, write=True)

    def preferences(self, parsed, write=False):
        actor = self.headers.get("X-QA-Actor", "")
        if actor not in {"alice", "bob"}:
            return self.reply(403, {"error": "Fixture actor required"})
        identity = {"email": actor + "@example.test"}
        try:
            if write:
                size = int(self.headers.get("Content-Length", "0"))
                if size > 1024:
                    return self.reply(400, {"error": "Fixture payload too large"})
                value = preferences.write(identity, json.loads(self.rfile.read(size)))
            else:
                value = preferences.read(identity, parse_qs(parsed.query).get("session_id", [None])[0])
            return self.reply(200, value)
        except preferences.ConflictError as exc:
            return self.reply(409, {"error": str(exc)})
        except (ValueError, PermissionError):
            return self.reply(400, {"error": "Invalid fixture preferences"})


if __name__ == "__main__":
    port = int(sys.argv[1])
    print(f"Preference QA on http://127.0.0.1:{port}; temporary synthetic storage only", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
