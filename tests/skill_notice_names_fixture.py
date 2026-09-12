"""Loopback-only named chat notices with real private store and HTTP handler.

Synthetic identities, conversations and confirmed tool-result data; no providers,
production homes, credentials, or real skills. Run from this checkout's .venv.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SynthPulse skill updates fixture</title>
<link rel="stylesheet" href="/static/skill_learning_activity.css"><style>body{background:#0b1322;color:#e7edf7;font:15px system-ui;margin:0}main{max-width:820px;margin:auto;padding:24px}nav{display:flex;flex-wrap:wrap;gap:8px}button{background:#233956;color:inherit;border:1px solid #56718d;padding:9px;border-radius:7px}.message{background:#15243b;padding:18px;margin:14px 0;border-radius:10px}small{color:#a4b2c6}</style>
<main><h1>SynthPulse</h1><p>Synthetic private chat · real notice renderer, HTTP handler and bounded store.</p><nav>
<button onclick="choose('alice','chat-a')">Alice · Chat A</button><button onclick="choose('bob','chat-a')">Bob · Same shared chat</button><button onclick="choose('alice','chat-b')">Alice · Chat B</button>
<button onclick="change('create')">Confirm skill creation</button><button onclick="change('patch')">Confirm skill patch</button><button onclick="change('failed')">Failed patch</button><button onclick="temporaryError()">Temporary notice error</button><button onclick="lateSwitch()">Hold A then switch to B</button><button onclick="release()">Release held response</button><button onclick="rerender()">Rebuild chat</button>
</nav><p id="identity"></p><p id="status" role="status"></p><div id="msgInner"></div></main>
<script>
let actor='alice';const S={session:{session_id:'chat-a'},messages:[]};let _currentPanel='chat',_loadingSessionId=null;
async function api(url,opts={}){const res=await fetch(url,{...opts,headers:{'X-Fixture-Actor':actor}});if(!res.ok)throw new Error('Synthetic HTTP '+res.status);return res.json();}
async function control(action){await fetch('/fixture/'+action,{method:'POST'});}
function rerender(){S.messages=[{timestamp:Math.floor(Date.now()/1000)-300,content:'Improve the deployment workflow.'},{timestamp:Math.floor(Date.now()/1000)-290,content:'The requested task is complete.'}];document.getElementById('msgInner').innerHTML=S.messages.map((m,i)=>'<div class="message" data-msg-idx="'+i+'">'+m.content+'</div>').join('');document.getElementById('identity').textContent=actor+' · '+S.session.session_id;window.SynthPulseSkillActivity?.sync(true);}
function choose(who,sid){window.SynthPulseSkillActivity.invalidate();actor=who;S.session={session_id:sid};rerender();}
async function change(kind){await control(kind);document.getElementById('status').textContent='Confirmed fixture outcome recorded; polling will update this chat within ten seconds.';}
async function temporaryError(){choose('alice','chat-b');await control('fail');choose('alice','chat-a');}
async function lateSwitch(){choose('alice','chat-b');await control('hold');choose('alice','chat-a');await new Promise(r=>setTimeout(r,150));choose('alice','chat-b');document.getElementById('status').textContent='Chat A response is held; current chat is B.';}
async function release(){await control('release');document.getElementById('status').textContent='Held response released.';}
</script><script src="/static/skill_learning_activity.js"></script><script>rerender();</script></html>'''


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=0);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='synthpulse-skill-notices-') as temporary:
        temp=Path(temporary).resolve()
        os.environ.update(HERMES_HOME=str(temp/'engine'),HERMES_WEBUI_STATE_DIR=str(temp/'state'))
        import sys
        sys.path.insert(0,str(ROOT))
        from api import config,skill_learning_activity as activity,ownership,models
        config.STATE_DIR=temp/'state'
        ownership._request_identity=lambda handler:{'email':handler.headers.get('X-Fixture-Actor','alice')+'@example.test'}
        def session(sid):
            if sid not in {'chat-a','chat-b'}:raise KeyError(sid)
            return SimpleNamespace(owner_email='alice@example.test',participants=['bob@example.test'],project_shared=False)
        models.get_session=session
        state={'counter':0,'fail':False,'hold':False}; gate=threading.Event();gate.set()
        scope=lambda run:activity.ReviewScope('alice@example.test',run,'synthetic','chat-a')
        activity.record(scope('legacy'),{'created':0,'patched':1,'updated':0},now=int(time.time())-60)
        def confirm(kind):
            state['counter']+=1
            action='patch' if kind=='failed' else kind
            name='fixture/release-check' if action=='patch' else 'deployment-workflow'
            messages=[{'role':'assistant','tool_calls':[{'id':str(state['counter']),'function':{'name':'skill_manage','arguments':json.dumps({'action':action,'name':name,'old_string':'a','new_string':'b'})}}]},
                      {'role':'tool','tool_call_id':str(state['counter']),'content':json.dumps({'success':kind!='failed'})}]
            counts,skills=activity.successful_skill_changes(messages,[])
            return activity.record(scope(str(state['counter'])),counts,skills=skills)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def send(self,data,status=200,mime='application/json'):
                data=data if isinstance(data,bytes) else json.dumps(data).encode()
                self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
            def do_GET(self):
                parsed=urlparse(self.path)
                if parsed.path=='/':return self.send(HTML.encode(),mime='text/html; charset=utf-8')
                if parsed.path in {'/static/skill_learning_activity.js','/static/skill_learning_activity.css'}:
                    return self.send((ROOT/parsed.path.lstrip('/')).read_bytes(),mime='text/javascript' if parsed.path.endswith('.js') else 'text/css')
                if parsed.path in {'/api/session/skill-updates','/api/skills/learning-activity'}:
                    if state['hold']:state['hold']=False;gate.wait(30)
                    if state['fail']:state['fail']=False;return self.send({'error':'Synthetic temporary failure'},503)
                    return activity.handle_get(self,parsed.query)
                return self.send({'error':'Not found'},404)
            def do_POST(self):
                action=urlparse(self.path).path.removeprefix('/fixture/')
                if action in {'create','patch','failed'}:return self.send({'recorded':confirm(action)})
                if action=='fail':state['fail']=True
                elif action=='hold':state['hold']=True;gate.clear()
                elif action=='release':gate.set()
                else:return self.send({'error':'Not found'},404)
                return self.send({'ok':True})
        server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
        print(json.dumps({'url':f'http://127.0.0.1:{server.server_port}','scope':'synthetic identities/results; real store/handler/renderer'}),flush=True)
        try:server.serve_forever()
        finally:server.server_close()

if __name__=='__main__':main()
