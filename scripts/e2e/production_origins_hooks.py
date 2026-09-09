#!/usr/bin/env python3
import ast, datetime, hashlib, importlib.metadata as md, json, os, pwd, re, socket, tempfile
from pathlib import Path
H = Path('/home/synthwavehq')
W = H / 'work/synthpulse'
OUT = W / 'qa-release-origins-hooks-20260909.json'
PIDS = (1053107, 3968984, 3082, 3555943)
EVENTS = {'kanban_task_completed', 'kanban_task_blocked', 'on_kanban_task_updated'}
ERRORS = []
def read(p):
  with Path(p).open('rb') as f: b = f.read(1048577)
  if len(b) > 1048576: raise ValueError('oversize')
  return b
def attempt(label, fn):
  try: return fn()
  except Exception as e:
    ERRORS.append({'section':label,'error':type(e).__name__})
def safe(s): return re.sub(r'[^A-Za-z0-9_./@:+-]', '_', str(s))[:300]
def proc(pid):
  p = Path('/proc') / str(pid)
  if not p.exists(): return {'pid':pid,'gone':True}
  if p.stat().st_uid != 1000: raise ValueError('uid changed')
  argv = [x.decode(errors='replace') for x in read(p/'cmdline').split(b'\0') if x]
  env = dict(x.decode(errors='replace').split('=',1) for x in read(p/'environ').split(b'\0') if b'=' in x)
  cwd = Path(os.readlink(p/'cwd'))
  arg0 = Path(argv[0])
  if not arg0.is_absolute(): arg0 = cwd / arg0
  prefix = arg0.parent.parent
  version = re.search(r'python(\d+\.\d+)',os.readlink(p/'exe')).group(1)
  sites = [prefix/f'lib/python{version}/site-packages',prefix/f'lib/python{version}/dist-packages']
  if prefix == Path('/usr'): sites += [Path(f'/usr/local/lib/python{version}/site-packages'),Path('/usr/lib/python3/dist-packages')]
  sites += [H/f'.local/lib/python{version}/site-packages']
  origins = []
  for d in md.distributions(path=[str(s) for s in sites]):
    if (d.metadata.get('Name') or '').lower().replace('_','-') != 'hermes-agent': continue
    data = json.loads(d.read_text('direct_url.json') or '{}')
    url = data.get('url','')
    source = url[7:] if url.startswith('file:///') else None
    origins.append({'metadata_root':safe(d.locate_file('')),'editable':data.get('dir_info',{}).get('editable'),'local_source':safe(source) if source else None})
  return {'pid':pid,'argv0':safe(argv[0]),'exe':safe(os.readlink(p/'exe')),'cwd':safe(cwd),
    'script':safe(argv[1]) if len(argv)>1 and argv[1].endswith('.py') else None,
    'units':re.findall(r'([^/\n]+\.service)',read(p/'cgroup').decode()),
    'site_directories':[safe(s) for s in sites if s.is_dir()], 'engine_metadata':origins,
    'agent_dir_launch':safe(env['HERMES_WEBUI_AGENT_DIR']) if env.get('HERMES_WEBUI_AGENT_DIR') else None,
    'start_ticks':read(p/'stat').decode().rsplit(')',1)[1].split()[19]}
def source(path):
  files = sorted(path.rglob('*.py'))
  out = {'path':safe(path),'python_files':len(files),'truncated':len(files)>80,'registrations':[],'target_literals':[]}
  for p in files[:80]:
    tree = ast.parse(read(p))
    rel = safe(p.relative_to(path))
    for n in ast.walk(tree):
      if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value in EVENTS:
        out['target_literals'].append({'file':rel,'line':n.lineno,'event':n.value})
      if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr == 'register_hook':
        value = n.args[0].value if n.args and isinstance(n.args[0],ast.Constant) else None
        literal = value if isinstance(value,str) and re.fullmatch('[a-z_]{1,70}',value) else None
        out['registrations'].append({'file':rel,'line':n.lineno,'literal_event':literal,'dynamic':literal is None})
  return out
def main():
  if socket.gethostname() != 'synthwave-vps' or os.getuid()!=os.geteuid() or os.getuid()!=1000 or pwd.getpwuid(os.getuid()).pw_name!='synthwavehq': raise SystemExit('wrong host/account')
  if W.resolve()!=W or W.stat().st_uid!=1000: raise SystemExit('wrong output parent')
  r = {'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'processes':[attempt('process',lambda pid=pid:proc(pid)) for pid in PIDS]}
  roots = {H/'work/codex-20260906-pantheon-engine'}
  for p in r['processes']:
    if not p: continue
    for d in p.get('engine_metadata',[]):
      if d.get('local_source'): roots.add(Path(d['local_source']))
    if p.get('agent_dir_launch'): roots.add(Path(p['agent_dir_launch']))
  prior = json.loads(read(W/'qa-release-drain-inspection-20260908.json'))
  paths = set()
  for cfg in prior.get('hooks',[]):
    if not cfg: continue
    for key in cfg.get('enabled') or []:
      if '..' in Path(key).parts or Path(key).is_absolute(): continue
      for base in [Path(cfg['home'])/'plugins', *[e/'plugins' for e in roots]]:
        path = base / key
        if path.is_dir(): paths.add(path)
  r['enabled_plugin_sources']=[attempt('plugin_source',lambda p=p:source(p)) for p in sorted(paths)]
  r['limits']=['Metadata only; no loaded-module proof.',
    'Only literal register_hook calls/target events. Dynamic hooks/initialization unverified. No hooks invoked.',
    'Prior plugin selection; config changes unverified.']
  r['errors']=ERRORS
  fd,tmp=tempfile.mkstemp(prefix='.qa-origins-',dir=W)
  with os.fdopen(fd,'w') as f:
    os.fchmod(f.fileno(),0o600);json.dump(r,f,indent=2);f.flush();os.fsync(f.fileno())
  os.replace(tmp,OUT)
if __name__=='__main__': main()
