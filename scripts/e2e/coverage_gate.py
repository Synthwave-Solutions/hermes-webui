#!/usr/bin/env python3
"""Build a source + browser control inventory; fail full certification on gaps.

Observed or clicked is not semantic proof. Each passed test's recorded input
or click is classified 'interacted', never silently upgraded to 'all tested'.
Run with --require-complete only when every inventory item has explicit proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

REPO=Path(__file__).resolve().parents[2]
def key(c):
    if c.get('id'): return '#'+c['id']
    if c.get('selection'): return 'selection:'+c['selection']+':'+str(c.get('value',''))
    if c.get('panel'): return 'panel:'+c['panel']
    if c.get('onclick'): return 'onclick:'+c['onclick']
    return c.get('scope','app')+':'+c.get('tag','')+':'+c.get('text','')
def main():
    p=argparse.ArgumentParser();p.add_argument('results',type=Path,nargs='+');p.add_argument('--out',type=Path,required=True);p.add_argument('--require-complete',action='store_true');a=p.parse_args()
    controls={};actions=set();test_count=0;failures=0
    for src in [REPO/'static/index.html',*sorted((REPO/'static').glob('*.js'))]:
        text=src.read_text()
        for match in re.finditer(r'<(button|input|select|textarea|a)\b[^>]*>',text):
            tag=match.group();attrs=dict(re.findall(r'([\w-]+)="([^"\n]*)"',tag))
            if attrs.get('type')=='hidden':continue
            identifier=attrs.get('id','')
            if not identifier or any(x in identifier for x in ['+','${',"'",'\\']):continue
            c={'tag':match.group(1).upper(),'id':identifier,'onclick':attrs.get('onclick'),'panel':attrs.get('data-panel')}
            controls.setdefault(key(c),dict(c,source=str(src.relative_to(REPO)),line=text.count('\n',0,match.start())+1,observed=False,status='NOT_INTERACTED'))
    def visit(suite):
        nonlocal test_count,failures
        for spec in suite.get('specs',[]):
            for test in spec.get('tests',[]):
                test_count+=1
                passed=test.get('status')=='expected'
                if not passed:failures+=1
                for result in test.get('results',[]):
                    for attachment in result.get('attachments',[]):
                        if attachment.get('contentType')!='application/json' or 'controls' not in attachment.get('name',''):continue
                        import base64
                        raw=attachment.get('body')
                        try:
                            data=json.loads(base64.b64decode(raw)) if raw else json.loads(Path(attachment['path']).read_text())
                        except (KeyError,ValueError,OSError):continue
                        for c in data.get('controls',[]):
                            k=key(c);controls.setdefault(k,dict(c,source='browser',status='NOT_INTERACTED'));controls[k]['observed']=True
                        if passed:
                            for c in data.get('actions',[]): actions.add(key(c))
        for child in suite.get('suites',[]):visit(child)
    for result_file in a.results:
        data=json.loads(result_file.read_text())
        for suite in data.get('suites',[]):visit(suite)
    for k in actions:
        controls.setdefault(k,{'source':'browser action','observed':True});controls[k]['status']='INTERACTED_IN_PASSING_TEST'
    gap=[k for k,c in controls.items() if c['status']=='NOT_INTERACTED']
    report={'test_executions':test_count,'nonpassing_executions':failures,'inventoried_controls':len(controls),'interacted_controls':len(actions),'uncovered_controls':len(gap),'all_clicks_complete':not gap and not failures,'scope_note':'Source extraction includes static IDs in top-level JS templates. Browser observations add anonymous/dynamic controls. Dynamic states never opened, external services, OS dialogs and semantic correctness beyond assertions remain outside this count.','controls':dict(sorted(controls.items()))}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='controls'},indent=2))
    return 1 if a.require_complete and (gap or failures) else 0
if __name__=='__main__':raise SystemExit(main())
