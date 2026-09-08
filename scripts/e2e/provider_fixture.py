"""Loopback deterministic provider for real chat and governance action reviews."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import sys
import time

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def do_GET(self):
        self.send_json({'object':'list','data':[{'id':'qa-deterministic','object':'model','owned_by':'qa'}]})
    def send_json(self, data):
        body=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
        messages=data.get('messages',[])
        last_index=next((i for i in range(len(messages)-1,-1,-1) if messages[i].get('role')=='user'),-1)
        last=messages[last_index].get('content','') if last_index>=0 else ''
        if not isinstance(last,str): last='QA message'
        system_text=str([m.get('content','') for m in messages if m.get('role')=='system'])
        tool_calls=None
        is_review='You review one already-permitted tool action for an administrator.' in system_text
        review_decision=None
        if not is_review and 'QA_STEER_WINDOW' in last and data.get('tools'):
            with (Path(os.environ['QA_STATE'])/'provider-evidence.jsonl').open('a') as record:
                record.write(json.dumps({'phase':'request_started','marker':'QA_STEER_WINDOW'})+'\n')
        if not is_review and 'QA_SLOW_RESPONSE' in last and data.get('tools'):
            time.sleep(5)
        if is_review:
            review=json.loads(last)
            rules=str(review.get('administrator_rules',''))
            review_decision='approve' if 'QA_ALLOW_ONLY' in rules else 'deny' if 'QA_DENY_ONLY' in rules else 'manual'
            answer=json.dumps({'decision':review_decision,'reason':'Deterministic QA review for this synthetic action.','confidence':.99})
        elif 'QA_STEER_WINDOW' in last and data.get('tools') and not any(m.get('role')=='tool' for m in messages[last_index+1:]):
            time.sleep(5)
            target=str(Path(os.environ['QA_STATE'])/'workspace'/'qa-evidence.txt')
            tool_calls=[{'id':'qa-steer-'+str(time.time_ns()),'type':'function','function':{'name':'read_file','arguments':json.dumps({'path':target})}}]
            answer=None
        elif 'QA_DELEGATE_PARENT' in last and (data.get('tools') or any(m.get('role')=='tool' for m in messages[last_index+1:])):
            results=[m.get('content','') for m in messages[last_index+1:] if m.get('role')=='tool']
            if results:
                answer='QA_DELEGATE_RESULT: '+str(results[-1])
            else:
                tool_calls=[{'id':'qa-delegate-'+str(time.time_ns()),'type':'function','function':{'name':'delegate_task','arguments':json.dumps({'tasks':[{'goal':'Return exactly QA_CHILD_ONE_DONE. This is a synthetic QA task; no tools required.'},{'goal':'Return exactly QA_CHILD_TWO_DONE. This is a synthetic QA task; no tools required.'}]})}}]
                answer=None
        elif 'QA_TODO|' in last and (data.get('tools') or any(m.get('role')=='tool' for m in messages[last_index+1:])):
            results=[m.get('content','') for m in messages[last_index+1:] if m.get('role')=='tool']
            if results:
                answer='QA_TODO_RESULT: '+str(results[-1])
            else:
                action=last.split('QA_TODO|',1)[1].splitlines()[0].strip()
                todos=[] if action=='clear' else [{'id':'qa-first','content':'QA todo updated' if action=='update' else 'QA todo created','status':'completed' if action=='update' else 'in_progress'},{'id':'qa-second','content':'QA next task','status':'pending'}]
                tool_calls=[{'id':'qa-todo-'+str(time.time_ns()),'type':'function','function':{'name':'todo','arguments':json.dumps({'todos':todos})}}]
                answer=None
        elif ('QA_GOV_READ|' in last or 'QA_GOV_WRITE|' in last) and (data.get('tools') or any(m.get('role')=='tool' for m in messages[last_index+1:])):
            results=[m.get('content','') for m in messages[last_index+1:] if m.get('role')=='tool']
            if results:
                answer='QA_GOV_TOOL_RESULT: '+str(results[-1])
            else:
                write='QA_GOV_WRITE|' in last
                target=last.split('QA_GOV_WRITE|' if write else 'QA_GOV_READ|',1)[1].splitlines()[0].strip()
                arguments={'path':target}
                if write: arguments['content']='QA_GOVERNANCE_EXECUTED'
                tool_calls=[{'id':'qa-gov-action-'+str(time.time_ns()),'type':'function','function':{'name':'write_file' if write else 'read_file','arguments':json.dumps(arguments)}}]
                answer=None
        else:
            markers=re.findall(r'(?:ALICE_GROUP_QA|BOB_GROUP_QA|QA_[A-Z_]+)',last)
            if any('QA_ACTUAL_STEER' in str(m.get('content','')) for m in messages):
                markers=['QA_ACTUAL_STEER']
            answer=('RESEARCH ' if 'QA_BOT_RESEARCH' in system_text else 'DEFAULT ')+'QA_REPLY: '+(markers[-1] if markers else last.splitlines()[0][:80] if last else 'QA')
        evidence=Path(os.environ.get('QA_STATE',str(Path(__file__).parent)))/'provider-evidence.jsonl'
        with evidence.open('a') as record:
            record.write(json.dumps({'review':is_review,'review_decision':review_decision,'observed_steer':any('QA_ACTUAL_STEER' in str(m.get('content','')) for m in messages),'issued_tools':[c['function']['name'] for c in tool_calls or []],'tools_offered':[t.get('function',{}).get('name') for t in data.get('tools',[])]})+'\n')
        base={'id':'chatcmpl-qa','created':int(time.time()),'model':'qa-deterministic'}
        message={'role':'assistant','content':answer}
        if tool_calls: message['tool_calls']=tool_calls
        finish='tool_calls' if tool_calls else 'stop'
        usage={'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}
        if data.get('stream'):
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
            delta={'role':'assistant'}
            if tool_calls:delta['tool_calls']=[dict(c,index=i) for i,c in enumerate(tool_calls)]
            else:delta['content']=answer
            chunk={**base,'object':'chat.completion.chunk','choices':[{'index':0,'delta':delta,'finish_reason':None}]}
            self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode());self.wfile.flush()
            final={**base,'object':'chat.completion.chunk','choices':[{'index':0,'delta':{},'finish_reason':finish}],'usage':usage}
            self.wfile.write(('data: '+json.dumps(final)+'\n\ndata: [DONE]\n\n').encode())
        else:self.send_json({**base,'object':'chat.completion','choices':[{'index':0,'message':message,'finish_reason':finish}],'usage':usage})

ThreadingHTTPServer(('127.0.0.1',int(sys.argv[1]) if len(sys.argv)>1 else 19087),Handler).serve_forever()
