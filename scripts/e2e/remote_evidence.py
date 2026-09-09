#!/usr/bin/env python3
"""Hash-bound, allowlisted transfer of a successful synthetic QA run.

Export is standalone. Import runs locally with the work/package_sources module
on Python's import path and an explicit workspace --root.

The raw Playwright report is hashed on its original host, never transferred:
steps/stdout can contain login data. A separately hashed projection retains
outcomes and approved evidence. This helper does not launch tests or use auth.
"""
from __future__ import annotations
import argparse
import ast
import base64
import copy
import hashlib
import json
import os
import platform
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
import zipfile

VERSION = 1
SCREENSHOTS = {
    'governance-after-desktop.png', 'governance-after-laptop.png',
    'governance-after-mobile.png', 'native-voice-conversation.png',
    'voice-mobile-pending-once.png', 'voice-mobile-pending-deny.png',
}
MAX_MEMBER = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
SHA = re.compile(r'^[0-9a-f]{64}$')
HEAD = re.compile(r'^[0-9a-f]{40}$')
WARNING = re.compile(r'^Internal error: step id not found: fixture@[0-9]+$')
CONTROL_FIELDS = {'event','tag','id','text','onclick','panel','scope','selection','value'}
AUDIT_FIELDS = {'event','extra','method','mode','path','reason','report_only',
                'subject_email_hash','subject_user_id_hash','ts'}
AUDIT_EXTRA = {'decision','operation_id','policy_revision','request_id','session_id','source','tool'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(data):
    return (json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode()


def decode(raw):
    def unique(pairs):
        out={}
        for key,value in pairs:
            if key in out: raise ValueError('Duplicate JSON key')
            out[key]=value
        return out
    return json.loads(raw, object_pairs_hook=unique)


def relative(name):
    path=PurePosixPath(name)
    if not name or path.is_absolute() or '\\' in name or any(p in {'.','..',''} for p in name.split('/')):
        raise ValueError('Unsafe archive/source relative path')
    return path


def safe_read(path, root, limit=MAX_MEMBER):
    path=Path(path);root=Path(root).resolve()
    if not path.is_absolute(): path=root/path
    if '..' in path.parts or not path.is_relative_to(root) or not path.resolve().is_relative_to(root):
        raise ValueError('Evidence path escapes its root')
    cur=path
    while cur != root:
        if cur.is_symlink(): raise ValueError('Evidence symlink refused')
        cur=cur.parent
    info=path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size>limit: raise ValueError('Invalid evidence file type/size')
    return path.read_bytes()


def current_provenance(web, directory):
    tree=ast.parse((web/'scripts/e2e/run_full.py').read_text())
    fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='provenance')
    ns={'hashlib':hashlib,'json':json,'subprocess':subprocess}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'reviewed-runner-provenance','exec'),ns)
    return ns['provenance'](directory)


def validate_manifest(manifest, web_head, engine_head):
    if (manifest.get('state')!='synthetic' or manifest.get('test_exit_code')!=0
            or manifest.get('source_unchanged_during_run') is not True):
        raise ValueError('Only completed successful unchanged synthetic runs may be transported')
    permitted={'base_url','state','engine','test_exit_code','results','all_features_certified',
               'source_unchanged_during_run','isolation','initial_source','final_source','test_source_sha256'}
    if set(manifest)-permitted: raise ValueError('Unreviewed original manifest fields')
    if manifest.get('all_features_certified') is not False: raise ValueError('Unsupported all-features claim')
    if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]+',manifest.get('base_url','')): raise ValueError('Not a loopback fixture')
    for key,head in [('webui',web_head),('engine',engine_head)]:
        if not HEAD.fullmatch(head): raise ValueError('Exact40-character heads required')
        before=manifest['initial_source'][key];after=manifest['final_source'][key]
        if before!=after or before['head']!=head: raise ValueError('Run source changed or wrong expected head')
        if set(before)!={'head','tracked_diff_sha256','source_sha256','source_file_sha256'}: raise ValueError('Unreviewed source fields')
        files=before['source_file_sha256']
        for name,sha in files.items():
            relative(name)
            if not SHA.fullmatch(sha): raise ValueError('Invalid source file digest')
        calculated=digest(json.dumps(files,sort_keys=True,separators=(',',':')).encode())
        if before['source_sha256']!=calculated or before['tracked_diff_sha256']!=digest(b''):
            raise ValueError('Unclean or inconsistent source manifest')
    for name,sha in manifest['test_source_sha256'].items():
        relative(name)
        if manifest['initial_source']['webui']['source_file_sha256'].get(name)!=sha:
            raise ValueError('Test source digest disagrees with source manifest')
    isolation=manifest.get('isolation',{})
    if set(isolation)-{'private_os_home','credential_cli_discovery_excluded','python_network','browser_network','os_sandbox'}:
        raise ValueError('Unreviewed isolation metadata')


def project_attachment(attachment, artifacts):
    name=attachment.get('name','');ctype=attachment.get('contentType')
    if ctype!='application/json': return None
    kind=('controls' if name.endswith('-controls') else 'errors' if name.endswith('browser-errors')
          else 'audit' if name in {'persisted-governance-audit','voice-persisted-governance-audit'} else None)
    if not kind: return None
    if 'body' in attachment:
        raw=base64.b64decode(attachment['body'],validate=True)
    else: raw=safe_read(attachment['path'],artifacts)
    if len(raw)>MAX_MEMBER: raise ValueError('Structured evidence too large')
    data=decode(raw)
    if kind=='errors':
        if data!=[]: raise ValueError('Nonempty page errors require independent private review')
    elif kind=='controls':
        if not isinstance(data,dict) or set(data)-{'controls','actions'}: raise ValueError('Unreviewed control envelope')
        for rows in data.values():
            if not isinstance(rows,list): raise ValueError('Invalid control rows')
            for row in rows:
                if not isinstance(row,dict) or set(row)-CONTROL_FIELDS: raise ValueError('Unreviewed control fields')
                for value in row.values():
                    if value is not None and not isinstance(value,(str,bool)): raise ValueError('Unreviewed control value')
                if row.get('event') not in {None,'click','dblclick','contextmenu','change','input','keydown'}: raise ValueError('Unknown control event')
    else:
        if not isinstance(data,dict) or set(data)-AUDIT_FIELDS or set(data.get('extra',{}))-AUDIT_EXTRA:
            raise ValueError('Unreviewed governance audit fields')
        if data.get('event')!='action_approval': raise ValueError('Unreviewed audit event')
    return {'name':name,'contentType':ctype,'body':base64.b64encode(raw).decode()}


def project_report(report, artifacts):
    if report.get('errors'): raise ValueError('Report errors require independent private review')
    omitted=[];retained=[]
    def suite(src):
        out={k:copy.deepcopy(src[k]) for k in ('title','file','line','column') if k in src}
        out['specs']=[]
        for sp in src.get('specs',[]):
            spec={k:copy.deepcopy(sp[k]) for k in ('title','ok','tags','id','file','line','column') if k in sp}
            spec['tests']=[]
            for t in sp.get('tests',[]):
                attempts=t.get('results',[])
                if (t.get('status')!='expected' or t.get('expectedStatus')!='passed' or len(attempts)!=1
                        or attempts[0].get('status')!='passed' or attempts[0].get('retry')!=0
                        or attempts[0].get('errors') or attempts[0].get('error')):
                    raise ValueError('Non-passing, skipped, retried or errored result refused')
                test={k:copy.deepcopy(t[k]) for k in ('timeout','expectedStatus','projectId','projectName','status') if k in t}
                a=attempts[0]
                result={k:copy.deepcopy(a[k]) for k in ('workerIndex','parallelIndex','status','duration','retry','startTime') if k in a}
                result.update(errors=[],attachments=[])
                for att in a.get('attachments',[]):
                    projected=project_attachment(att,artifacts)
                    identifier={'spec_id':sp.get('id'),'name':att.get('name'),'content_type':att.get('contentType')}
                    if projected:
                        result['attachments'].append(projected)
                        retained.append(dict(identifier,body_sha256=digest(base64.b64decode(projected['body']))))
                    else:
                        omitted.append(identifier)
                if sum(x['name']=='uncaught-browser-errors' for x in result['attachments'])!=1:
                    raise ValueError('Missing unique primary browser-error collection')
                test['results']=[result];spec['tests'].append(test)
            out['specs'].append(spec)
        out['suites']=[suite(s) for s in src.get('suites',[])]
        return out
    config=report.get('config',{})
    clean={'config':{k:copy.deepcopy(config[k]) for k in ('configFile','rootDir','workers','fullyParallel','version') if k in config},
           'suites':[suite(s) for s in report.get('suites',[])],'errors':[],
           'stats':{k:copy.deepcopy(report.get('stats',{}).get(k)) for k in ('startTime','duration','expected','unexpected','flaky','skipped')}}
    return clean,{'retained_structured_attachments':retained,'omitted_attachments':omitted,
                  'omitted_fields':['test annotations','result annotations','result steps','result stdout','result stderr','unreviewed config fields'],
                  'scope':'Projection retains original scenario IDs, locations, project IDs, statuses, timing and empty error outcomes. Omitted data is never silently certified.'}


def isolated_facts(run, runner_log, qa_root):
    qa_root=Path(qa_root).resolve()
    if not run.is_relative_to(qa_root): raise ValueError('Run outside explicit QA root')
    raw=safe_read(runner_log,qa_root,64*1024*1024)
    text=raw.decode(errors='replace')
    if not any(line.strip()=='Evidence: '+str(run) for line in text.splitlines()):
        raise ValueError('Runner log is not tied to the completed selected run')
    warnings=[]
    for line in text.splitlines():
        if line.startswith('Internal error: step id not found:'):
            if not WARNING.fullmatch(line): raise ValueError('Unreviewed reporter warning format')
            warnings.append(line)
    counts={}
    events=run/'e2e-state/isolation-events.jsonl'
    if events.exists():
        for line in safe_read(events,run).splitlines():
            name=decode(line).get('event')
            if name not in {'external_dns','external_connection','credential_cli'}: raise ValueError('Unknown isolation event')
            counts[name]=counts.get(name,0)+1
    server=safe_read(run/'server.log',run,256*1024*1024)
    return {'execution_host':{'system':platform.system(),'machine':platform.machine(),'python':platform.python_version()},'runner_log_sha256':digest(raw),'completed_evidence_line':str(run),
            'runner_reporter_warnings':warnings,'isolation':{'blocked_attempt_counts':counts,
            'raw_copilot_token_fallback_observed':b'RAW token' in server},
            'private_data_exported':False,'scope':'Only event-category counts and one exact known-token-fallback indicator were extracted; raw logs/state remain remote.'}


def export(args):
    qa=args.qa_root.resolve();run=args.run.resolve();web=qa/'webui';engine=qa/'engine'
    if not run.is_relative_to(qa) or run in {qa,web,engine}: raise ValueError('Run must be a dedicated child of QA root')
    original=safe_read(run/'run.json',run);manifest=decode(original)
    validate_manifest(manifest,args.webui_head,args.engine_head)
    if Path(manifest['results'])!=run/'results/results.json' or Path(manifest['engine'])!=engine:
        raise ValueError('Manifest does not match selected remote directories')
    for name,directory in [('webui',web),('engine',engine)]:
        if current_provenance(web,directory)!=manifest['final_source'][name]: raise ValueError('Remote source no longer matches run')
    raw_report=safe_read(run/'results/results.json',run)
    report,projection=project_report(decode(raw_report),run/'results/artifacts')
    facts=isolated_facts(run,args.runner_log.resolve(),qa)
    members={'origin/run.json':original,'projection/results.json':encoded(report),
             'projection/selection.json':encoded(projection),'projection/runtime-facts.json':encoded(facts)}
    screen_sources={}
    for name in sorted(SCREENSHOTS):
        matches=list((run/'results/artifacts').glob('**/'+name))
        if len(matches)!=1: raise ValueError('Expected exactly one approved screenshot '+name)
        raw=safe_read(matches[0],run/'results/artifacts')
        if not raw.startswith(b'\x89PNG\r\n\x1a\n'): raise ValueError('Approved screenshot is not PNG')
        key='screenshots/'+name;members[key]=raw
        screen_sources[key]=str(matches[0].relative_to(run))
    receipt={'version':VERSION,'kind':'synthetic-qa-safe-projection','original_run':str(run),
             'original_webui':str(web),'original_engine':str(engine),
             'original_results_sha256':digest(raw_report),'original_manifest_sha256':digest(original),
             'webui_head':args.webui_head,'engine_head':args.engine_head,
             'screenshots_original_paths':screen_sources,
             'members':{k:{'sha256':digest(v),'bytes':len(v)} for k,v in sorted(members.items())},
             'exclusions':['raw results steps/stdout','all private test state','auth/cookies/passwords','raw trace/video','provider/server/runner logs','nonallowlisted attachments']}
    members['transport.json']=encoded(receipt)
    if sum(map(len,members.values()))>MAX_TOTAL: raise ValueError('Archive exceeds bounded size')
    target=args.out.resolve()
    if target.exists(): raise ValueError('Refuse overwriting existing transfer')
    target.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:
        with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:
            for name,raw in sorted(members.items()):
                info=zipfile.ZipInfo(name);info.external_attr=(stat.S_IFREG|0o600)<<16;info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,raw)
    print(json.dumps({'archive':str(target),'archive_sha256':digest(target.read_bytes()),
                      'original_results_sha256':receipt['original_results_sha256'],
                      'original_manifest_sha256':receipt['original_manifest_sha256'],'members':len(members)}))


def read_archive(path,expected_sha):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_TOTAL:
        raise ValueError('Invalid archive file type/size')
    if not SHA.fullmatch(expected_sha) or digest(path.read_bytes())!=expected_sha: raise ValueError('Independent archive hash mismatch')
    data={}
    with zipfile.ZipFile(path) as z:
        if len(z.infolist())>32: raise ValueError('Unexpected archive member count')
        total=0
        for info in z.infolist():
            relative(info.filename)
            if info.filename in data or info.is_dir() or stat.S_IFMT(info.external_attr>>16)!=stat.S_IFREG: raise ValueError('Duplicate/nonregular archive entry')
            total+=info.file_size
            if info.file_size>MAX_MEMBER or total>MAX_TOTAL: raise ValueError('Archive size bound exceeded')
            data[info.filename]=z.read(info)
    receipt=decode(data['transport.json'])
    if receipt.get('version')!=VERSION or receipt.get('kind')!='synthetic-qa-safe-projection': raise ValueError('Unsupported transport')
    expected={'origin/run.json','projection/results.json','projection/selection.json','projection/runtime-facts.json'}|{'screenshots/'+n for n in SCREENSHOTS}
    if set(receipt['members'])!=expected or set(data)!=expected|{'transport.json'}: raise ValueError('Unexpected/missing transport member')
    for name,row in receipt['members'].items():
        if row!={'sha256':digest(data[name]),'bytes':len(data[name])}: raise ValueError('Member digest/size mismatch')
    if digest(data['origin/run.json'])!=receipt['original_manifest_sha256']: raise ValueError('Original manifest digest mismatch')
    if not SHA.fullmatch(receipt['original_results_sha256']): raise ValueError('Missing raw report digest')
    return data,receipt


def import_archive(args):
    archive=args.archive.resolve();data,receipt=read_archive(archive,args.archive_sha256)
    root=args.root.resolve();out=args.out_run.resolve()
    if out.parent!=root/'work/e2e-runs' or out.name!=Path(receipt['original_run']).name or out.exists():
        raise ValueError('Import needs a new work/e2e-runs/<original-run-name> directory')
    original=decode(data['origin/run.json']);validate_manifest(original,args.webui_head,args.engine_head)
    if receipt['webui_head']!=args.webui_head or receipt['engine_head']!=args.engine_head: raise ValueError('Unexpected transport source heads')
    # Import reviewed local packaging validators only; they do not run tests.
    from package_sources import current_sources,current_scenario_catalog,require_complete_report
    current_sources(root,original)
    report=decode(data['projection/results.json'])
    checked,_=project_report(report,out/'results/artifacts')
    if checked!=report: raise ValueError('Report is not the declared safe projection')
    before_report=digest(data['projection/results.json'])
    changes=[]
    for field,new in [('configFile',str(root/'work/coverage-webui/playwright.full.config.ts')),('rootDir',str(root/'work/coverage-webui/tests/e2e/full'))]:
        old=report['config'].get(field)
        if old is not None:
            expected=str(Path(receipt['original_webui'])/('playwright.full.config.ts' if field=='configFile' else 'tests/e2e/full'))
            if old!=expected: raise ValueError('Unexpected remote config path')
            report['config'][field]=new;changes.append({'json_path':'report.config.'+field,'from':old,'to':new})
    manifest=copy.deepcopy(original)
    for field,new in [('results',str(out/'results/results.json')),('engine',str(root/'work/coverage-engine'))]:
        changes.append({'json_path':'manifest.'+field,'from':manifest[field],'to':new});manifest[field]=new
    facts=decode(data['projection/runtime-facts.json'])
    if facts['completed_evidence_line']!=receipt['original_run'] or any(not WARNING.fullmatch(s) for s in facts['runner_reporter_warnings']): raise ValueError('Runtime facts not bound to original run')
    report_bytes=encoded(report)
    rebasing={'version':1,'archive_sha256':args.archive_sha256,
             'transport_receipt_sha256':digest(data['transport.json']),
             'original_manifest_sha256':receipt['original_manifest_sha256'],
             'original_results_sha256':receipt['original_results_sha256'],
             'projected_remote_report_sha256':before_report,'rebased_report_sha256':digest(report_bytes),
             'original_run':receipt['original_run'],'local_run':str(out),'changes':changes,
             'scope':'Only explicit config/results/engine filesystem references were rebased. Inline controls and audit evidence retain original bytes; raw report was not transported.'}
    manifest['remote_transport']=rebasing
    # All retained structured evidence is inline, so validation needs no copied auth/state.
    require_complete_report(report,out/'results/results.json',manifest,current_scenario_catalog(root))
    out.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix='.remote-import-',dir=out.parent))
    try:
        files={'run.json':encoded(manifest),'results/results.json':report_bytes,
               'remote-evidence/transport.json':data['transport.json'],
               'remote-evidence/original-run.json':data['origin/run.json'],
               'remote-evidence/projected-remote-results.json':data['projection/results.json'],
               'remote-evidence/selection.json':data['projection/selection.json'],
               'remote-evidence/runtime-facts.json':data['projection/runtime-facts.json'],
               'remote-evidence/rebasing.json':encoded(rebasing)}
        for name in SCREENSHOTS:files['results/artifacts/remote-approved/'+name]=data['screenshots/'+name]
        for name,raw in files.items():
            dest=temp/name;dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as f:f.write(raw)
            dest.chmod(0o600)
        temp.rename(out)
    finally:
        if temp.exists():
            import shutil
            shutil.rmtree(temp)
    print(json.dumps({'imported_run':str(out),'archive_sha256':args.archive_sha256,
                      'original_results_sha256':receipt['original_results_sha256'],
                      'rebased_results_sha256':digest(report_bytes),'source_and_full_catalog_verified':True}))


def imported_facts(run):
    """Revalidate selected imported files before local packaging; no raw logs."""
    run=Path(run).resolve()
    manifest=decode(safe_read(run/'run.json',run))
    rebasing=manifest['remote_transport']
    receipt_raw=safe_read(run/'remote-evidence/transport.json',run)
    if digest(receipt_raw)!=rebasing['transport_receipt_sha256']:
        raise ValueError('Imported transport receipt changed')
    receipt=decode(receipt_raw)
    for key,local in [('origin/run.json','remote-evidence/original-run.json'),
                      ('projection/results.json','remote-evidence/projected-remote-results.json'),
                      ('projection/selection.json','remote-evidence/selection.json'),
                      ('projection/runtime-facts.json','remote-evidence/runtime-facts.json')]:
        raw=safe_read(run/local,run)
        if receipt['members'][key]!={'sha256':digest(raw),'bytes':len(raw)}:
            raise ValueError('Imported original/projection member changed')
    for name in SCREENSHOTS:
        raw=safe_read(run/'results/artifacts/remote-approved'/name,run)
        if receipt['members']['screenshots/'+name]!={'sha256':digest(raw),'bytes':len(raw)}:
            raise ValueError('Imported screenshot changed')
    raw=safe_read(run/'results/results.json',run)
    if digest(raw)!=rebasing['rebased_report_sha256']:
        raise ValueError('Rebased report changed')
    if (rebasing['local_run']!=str(run) or rebasing['original_run']!=receipt['original_run']
            or rebasing['original_results_sha256']!=receipt['original_results_sha256']
            or rebasing['original_manifest_sha256']!=receipt['original_manifest_sha256']):
        raise ValueError('Imported identity changed')
    original=decode(safe_read(run/'remote-evidence/original-run.json',run))
    restored=copy.deepcopy(manifest);restored.pop('remote_transport')
    report=decode(raw)
    for change in rebasing['changes']:
        namespace,field=change['json_path'].split('.',1)
        if namespace=='manifest' and field in {'results','engine'}:
            if restored[field]!=change['to']: raise ValueError('Manifest rebase mismatch')
            restored[field]=change['from']
        elif namespace=='report' and field in {'config.configFile','config.rootDir'}:
            field=field.split('.')[1]
            if report['config'][field]!=change['to']: raise ValueError('Report rebase mismatch')
            report['config'][field]=change['from']
        else: raise ValueError('Unreviewed import transformation')
    if restored!=original or encoded(report)!=safe_read(run/'remote-evidence/projected-remote-results.json',run):
        raise ValueError('Import changed fields beyond explicit path transformation')
    return decode(safe_read(run/'remote-evidence/runtime-facts.json',run))


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    ex=sub.add_parser('export');ex.add_argument('--qa-root',type=Path,required=True);ex.add_argument('--run',type=Path,required=True);ex.add_argument('--runner-log',type=Path,required=True);ex.add_argument('--out',type=Path,required=True)
    im=sub.add_parser('import');im.add_argument('--archive',type=Path,required=True);im.add_argument('--archive-sha256',required=True);im.add_argument('--root',type=Path,required=True,help='Local Codex workspace containing work/package_sources.py; import needs that module on Python import path');im.add_argument('--out-run',type=Path,required=True)
    for cmd in (ex,im):cmd.add_argument('--webui-head',required=True);cmd.add_argument('--engine-head',required=True)
    args=p.parse_args();(export if args.command=='export' else import_archive)(args)

if __name__=='__main__':main()
