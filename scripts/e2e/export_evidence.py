#!/usr/bin/env python3
"""Export safe scenario outcomes and selected screenshots, never auth state or traces."""
import argparse
import csv
import json
from pathlib import Path
import shutil

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('results',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    results=json.loads(args.results.read_text())
    rows=[]
    audits=[]
    browser_errors=[]
    def visit(suite):
        for spec in suite.get('specs',[]):
            for test in spec.get('tests',[]):
                attempts=test.get('results',[])
                last=attempts[-1] if attempts else {}
                title=spec['title']
                rows.append({'file':spec.get('file',suite.get('file','')),'line':spec.get('line',''),'scenario':title,'status':last.get('status','not-run'),'test_outcome':test.get('status','unknown'),'duration_ms':sum(r.get('duration',0) for r in attempts),'attempts':len(attempts),'evidence_scope':'navigation/tab reachability' if spec.get('file',suite.get('file','')).endswith('navigation.spec.ts') else 'exact assertions in test script'})
                for attachment in last.get('attachments',[]):
                    if attachment.get('name')=='uncaught-browser-errors':
                        import base64
                        raw=attachment.get('body')
                        errors=json.loads(base64.b64decode(raw)) if raw else json.loads(Path(attachment['path']).read_text())
                        browser_errors.append({'scenario':title,'errors':errors})
                    if attachment.get('name')=='persisted-governance-audit':
                        import base64
                        raw=attachment.get('body')
                        audits.append(json.loads(base64.b64decode(raw)) if raw else json.loads(Path(attachment['path']).read_text()))
        for child in suite.get('suites',[]):visit(child)
    for suite in results.get('suites',[]):visit(suite)
    out=args.out;out.mkdir(parents=True,exist_ok=True)
    with (out/'executed-scenarios.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=['file','line','scenario','status','test_outcome','duration_ms','attempts','evidence_scope']);writer.writeheader();writer.writerows(rows)
    manifest_path=args.results.parent.parent/'run.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    counts={status:sum(r['status']==status for r in rows) for status in sorted({r['status'] for r in rows})}
    summary={'scenario_count':len(rows),'outcomes':counts,'report_global_error_count':len(results.get('errors',[])),'all_features_certified':False,'story_certification_note':'These outcomes certify only explicit scenario assertions. Navigation, observed controls, and interaction counts do not certify all acceptance criteria.','source_unchanged_during_run':manifest.get('source_unchanged_during_run'),'test_exit_code':manifest.get('test_exit_code'),'webui_source_sha256':manifest.get('initial_source',{}).get('webui',{}).get('source_sha256'),'engine_source_sha256':manifest.get('initial_source',{}).get('engine',{}).get('source_sha256'),'run_directory':args.results.parent.parent.name,'boundary':'Real Chromium, backend persistence, Hermes engine, terminal and child agents; deterministic loopback model/reviewer. External credentials, provider quality, physical authenticators, audio and delivery are separate.','excluded_artifacts':['private test state','cookies and generated password','raw browser traces','raw network captures','session/auth databases']}
    summary['browser_error_collection']={'scenarios_with_error_collection':len(browser_errors),'uncaught_errors':sum(len(item['errors']) for item in browser_errors)}
    (out/'execution-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'browser-error-evidence.json').write_text(json.dumps(browser_errors,indent=2)+'\n')
    (out/'governance-runtime-audit-evidence.json').write_text(json.dumps(audits,indent=2)+'\n')
    screenshots=out/'screenshots';screenshots.mkdir(exist_ok=True)
    for name in ['governance-after-desktop.png','governance-after-laptop.png','governance-after-mobile.png']:
        candidates=list(args.results.parent.glob('artifacts/**/'+name))
        if len(candidates)!=1:raise RuntimeError(f'Expected one {name}, found {len(candidates)}')
        shutil.copy2(candidates[0],screenshots/name)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
