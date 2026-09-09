"""Task-specific operator: run reviewed QA in its own systemd unit, never production."""
import argparse, datetime, hashlib, json, os, pathlib, pwd, re, shutil, signal, socket, subprocess, sys, time

p=argparse.ArgumentParser();p.add_argument('--webui',required=True);p.add_argument('--engine',required=True);p.add_argument('--source',required=True);p.add_argument('--engine-source',required=True);a=p.parse_args()
assert socket.gethostname()=='synthwave-vps' and os.getuid()==1000 and pwd.getpwuid(1000).pw_name=='synthwavehq'
assert all(re.fullmatch(r'[0-9a-f]{40}',v) for v in [a.webui,a.engine]) and all(re.fullmatch(r'[0-9a-f]{64}',v) for v in [a.source,a.engine_source])
os.umask(0o077);sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
r=pathlib.Path('/home/synthwavehq/work/synthpulse-qa-20260909-v1');web=r/'webui';engine=r/'engine'
assert r.resolve()==r and r.stat().st_uid==1000 and not pathlib.Path('/etc/hermes').exists()
assert not any((repo/name).exists() for repo in [web,engine] for name in ['.env','.env.local'])
assert shutil.disk_usage(r).free>2*1024**3
unit=pathlib.Path('/proc/self/cgroup').read_text().strip()
assert 'synthpulse-qa-full-20260909-' in unit and 'hermes-webui.service' not in unit
sys.path.insert(0,str(web/'scripts/e2e'));from run_full import provenance
before={'webui':provenance(web),'engine':provenance(engine)}
assert before['webui']['head']==a.webui and before['engine']['head']==a.engine and before['webui']['source_sha256']==a.source and before['engine']['source_sha256']==a.engine_source
assert all(s['tracked_diff_sha256']==hashlib.sha256(b'').hexdigest() for s in before.values())
report=r/'execution.json';public=pathlib.Path('/home/synthwavehq/work/synthpulse/qa-vps-execution-20260909.json')
d={'kind':'isolated_linux_full_qa','status':'starting','source':{k:{n:v[n] for n in ['head','source_sha256']} for k,v in before.items()},'platform':sys.platform,'python':sys.version.split()[0],'unit_cgroup':unit,'disk_floor_gib':1.5,'source_unchanged':False}
def save():
 d['at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 for dest in [report,public]:
  tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2)+'\n');os.replace(tmp,dest)
def processes():
 out={}
 for q in pathlib.Path('/proc').iterdir():
  if not q.name.isdigit() or int(q.name)==os.getpid():continue
  try:
   if q.stat().st_uid!=1000 or (q/'cgroup').read_text().strip()!=unit:continue
   stat=(q/'stat').read_text();fields=stat[stat.rfind(')')+2:].split()
   out[int(q.name)]={'pid':int(q.name),'start_ticks':int(fields[19]),'ppid':int(fields[1]),'state':fields[0]}
  except (FileNotFoundError,ProcessLookupError,PermissionError):continue
 return out
for name in ['operator-home','operator-tmp','runs']:(r/name).mkdir(mode=0o700,exist_ok=True)
env={'PYTHONDONTWRITEBYTECODE':'1','PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(r/'operator-home'),'TMPDIR':str(r/'operator-tmp'),'LANG':'C.UTF-8','QA_PLAYWRIGHT_CLI':str(r/'e2e-tooling/node_modules/@playwright/test/cli.js'),'PLAYWRIGHT_BROWSERS_PATH':str(r/'browser-cache')}
assert not list((r/'runs').iterdir()),'Use a fresh explicitly reviewed output root'
d['playwright']=subprocess.check_output(['node',env['QA_PLAYWRIGHT_CLI'],'--version'],env=env,text=True).strip();save()
known={};started=time.monotonic()
with (r/'runner.log').open('w') as log:
 proc=subprocess.Popen([str(web/'.venv/bin/python'),str(web/'scripts/e2e/run_full.py'),'--engine',str(engine),'--out',str(r/'runs')],cwd=web,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 d['status']='running';d['runner_pid']=proc.pid;save()
 while proc.poll() is None:
  for pid,row in processes().items():known[(pid,row['start_ticks'])]=row
  free=shutil.disk_usage(r).free;d['free_gib']=round(free/1024**3,2);d['elapsed_seconds']=round(time.monotonic()-started,1)
  runs=list((r/'runs').iterdir())
  if len(runs)==1:d['run']=runs[0].name
  raw=(r/'runner.log').read_text(errors='replace');d['reported_passes']=len(re.findall(r'^\s*\u2713\s+\d+ ',raw,re.M));d['reported_failures']=len(re.findall(r'^\s*[\u2718x]\s+\d+ ',raw,re.M))
  (r/'census-during.json').write_text(json.dumps({'cgroup':unit,'processes':list(known.values()),'scope':'Sampled own unit descendants by exact cgroup and PID/start ticks; not universal process history.'},indent=2))
  if free<1.5*1024**3:
   d['abort_reason']='disk_reserve';save();os.killpg(proc.pid,signal.SIGTERM);break
  save();time.sleep(5)
 try:code=proc.wait(timeout=45)
 except subprocess.TimeoutExpired:
  d['abort_reason']='own_runner_did_not_stop';save();raise
d['runner_exit_code']=code;d['elapsed_seconds']=round(time.monotonic()-started,1)
after={'webui':provenance(web),'engine':provenance(engine)};d['source_unchanged']=all(before[k]['source_sha256']==after[k]['source_sha256'] for k in before)
runs=list((r/'runs').iterdir())
if len(runs)==1 and (runs[0]/'run.json').exists():
 run=runs[0];manifest=json.loads((run/'run.json').read_text());results=json.loads((run/'results/results.json').read_text())
 assert manifest['initial_source']==before and manifest['final_source']==after and manifest['source_unchanged_during_run'] is True and manifest['test_exit_code']==code
 assert pathlib.Path(manifest['results']).resolve()==run/'results/results.json' and pathlib.Path(manifest['engine']).resolve()==engine
 d['run']=run.name;d['results_stats']=results.get('stats');d['run_manifest_sha256']=hashlib.sha256((run/'run.json').read_bytes()).hexdigest();d['results_sha256']=hashlib.sha256((run/'results/results.json').read_bytes()).hexdigest()
 probe=json.loads((run/'e2e-state/runtime-engine.json').read_text());assert pathlib.Path(probe['engine_module']).resolve()==engine/'hermes_cli/kanban_db.py' and probe['guard_installed'] is True
 d['selected_engine_child_verified']=True
else:d['no_completed_run_manifest']=True
time.sleep(2)
remaining=[]
for row in known.values():
 try:
  raw=pathlib.Path('/proc')/str(row['pid'])/'stat';s=raw.read_text();f=s[s.rfind(')')+2:].split()
  if int(f[19])==row['start_ticks'] and f[0]!='Z':remaining.append(row)
 except (FileNotFoundError,ProcessLookupError):pass
d['sampled_owned_survivors_before_unit_exit']=remaining
valid=code==0 and d['source_unchanged'] and d.get('selected_engine_child_verified') is True and not d.get('no_completed_run_manifest')
d['status']='completed_pending_evidence_review' if valid else 'failed'
save();raise SystemExit(0 if valid else code or 1)
