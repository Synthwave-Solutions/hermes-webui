#!/usr/bin/env python3
"""Run with service Python -B."""
import datetime, importlib.metadata, json, os, pwd, re, socket, sqlite3, subprocess, sys, tempfile
from pathlib import Path
BASE_ROOT = Path('/home/synthwavehq')
ENGINE = BASE_ROOT / 'work/codex-20260906-pantheon-engine'
OUT = BASE_ROOT / 'work/synthpulse/qa-release-drain-inspection-20260908.json'
EVENTS = ('kanban_task_completed', 'kanban_task_blocked')
ERRORS = []
def read(path):
  with Path(path).open('rb') as f:
    data = f.read((1 << 22) + 1)
  if len(data) > 1 << 22: raise ValueError('oversize')
  return data
def attempt(section, fn):
  try:
    return fn()
  except Exception as exc:
    ERRORS.append({'section': section, 'error': type(exc).__name__})
    return None
def safe(value):
  return re.sub(r'[^A-Za-z0-9_./:@+-]', '_', str(value))[:300]
def process(pid):
  p = Path('/proc') / str(pid)
  if not p.exists(): return {'pid': pid, 'alive': False}
  if p.stat().st_uid != 1000: return {'pid': pid, 'alive': True, 'expected_uid': False}
  args = read(p / 'cmdline').decode(errors='replace').split('\0')
  names = [Path(a).name for a in args if a]
  kind = 'other'
  if 'server.py' in names:
    kind = 'webui'
  elif any('gateway' in a for a in args):
    kind = 'gateway'
  elif any(a in names for a in ('run_agent.py', 'kanban.py', 'cron.py')):
    kind = 'agent_or_scheduler'
  elif any('multiprocessing' in a for a in args):
    kind = 'python_worker'
  stat = read(p / 'stat').decode().rsplit(')', 1)[1].split()
  return {'pid': pid, 'alive': True, 'expected_uid': True, 'kind': kind,
      'start_ticks': stat[19], 'parent_pid': int(stat[1]),
      'exe': safe(os.readlink(p / 'exe')), 'cwd': safe(os.readlink(p / 'cwd'))}
def command(args):
  cp = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=8, check=True, env={**os.environ, 'LC_ALL': 'C'})
  if len(cp.stdout) > 1 << 20: raise ValueError('oversize')
  return cp.stdout.decode()
def services(user):
  prefix = ['systemctl'] + (['--user'] if user else [])
  rows = command(prefix + ['list-units', '--type=service', '--state=running', '--no-legend', '--plain']).splitlines()
  units = [r.split()[0] for r in rows if r.split() and re.search(r'hermes|synthpulse|gateway', r.split()[0], re.I)]
  return {'running_units': [safe(u) for u in units[:30]], 'truncated': len(units) > 30}
def yaml_data(path):
  import yaml
  obj = yaml.safe_load(read(path)) or {}
  if not isinstance(obj, dict): raise ValueError('not mapping')
  return obj
def ledger(home):
  db = home / 'state.db'
  if not db.exists(): return {'home': safe(home), 'exists': False}
  if Path(str(db) + '-wal').exists() and not Path(str(db) + '-shm').exists(): return {'home': safe(home), 'status': 'unknown: WAL has no existing SHM'}
  con = sqlite3.connect(db.as_uri() + '?mode=ro', uri=True, timeout=2)
  try:
    con.execute('PRAGMA query_only=ON')
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name='async_delegations'").fetchone(): return {'home': safe(home), 'table_exists': False}
    rows = con.execute('SELECT state,delivery_state,owner_pid,owner_started_at,COUNT(*) FROM async_delegations GROUP BY state,delivery_state,owner_pid,owner_started_at').fetchall()
    groups = []
    for state, delivery, pid, started, count in rows[:300]:
      live = attempt('owner_process', lambda pid=pid: process(int(pid))) if pid else None
      match = None
      if live and not live.get('alive'):
        match = False
      elif live and live.get('start_ticks') and started is not None:
        match = str(started) == live['start_ticks']
      groups.append({'state': safe(state), 'delivery': safe(delivery), 'count': count,
             'owner': live, 'owner_instance_matches': match})
    return {'home': safe(home), 'groups': groups, 'truncated': len(rows) > 300}
  finally:
    con.close()
def hooks(home):
  cfg = yaml_data(home / 'config.yaml') if (home / 'config.yaml').exists() else {}
  plugins = cfg.get('plugins') if isinstance(cfg.get('plugins'), dict) else {}
  result = {'home': safe(home), 'enabled': [safe(x) for x in plugins.get('enabled', [])][:100] if isinstance(plugins.get('enabled'), list) else None,
       'disabled': [safe(x) for x in plugins.get('disabled', [])][:100] if isinstance(plugins.get('disabled'), list) else None,
       'manifests': []}
  roots = [ENGINE / 'plugins', ENGINE / 'plugins/platforms', home / 'plugins']
  for base in roots:
    for path in sorted(base.glob('*/plugin.yaml'))[:150]:
      obj = attempt('manifest', lambda path=path: yaml_data(path))
      if obj is None: continue
      declarations = json.dumps({k: obj.get(k) for k in ('provides_hooks', 'hooks', 'emits', 'listens')})
      events = [e for e in EVENTS if e in declarations]
      if events or path.parent.name in (result['enabled'] or []):
        result['manifests'].append({'path': safe(path), 'name': safe(obj.get('name', path.parent.name)), 'target_events_declared': events})
  return result
def origin():
  d = importlib.metadata.distribution('hermes-agent')
  direct = json.loads(d.read_text('direct_url.json') or '{}')
  url = direct.get('url', '')
  return {'metadata_root': safe(d.locate_file('')), 'editable': direct.get('dir_info', {}).get('editable'),
      'local_source_only': safe(url[7:]) if url.startswith('file:///') else None}
def main():
  if socket.gethostname().split('.')[0] != 'synthwave-vps' or os.getuid() != os.geteuid() or os.getuid() != 1000 or pwd.getpwuid(os.getuid()).pw_name != 'synthwavehq': raise SystemExit('Refused: unexpected host/account')
  if OUT.parent.stat().st_uid != 1000 or OUT.is_symlink() or OUT.parent.is_symlink() or OUT.parent.resolve() != OUT.parent or not OUT.parent.is_dir(): raise SystemExit('Refused: unexpected output parent')
  r = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'services': {}, 'processes': []}
  for user in (True, False):
    r['services'][str(user)] = attempt('services', lambda user=user: services(user))
  homes = {BASE_ROOT / '.hermes'}
  homes.update(p for p in (BASE_ROOT / '.hermes/profiles').glob('*') if p.is_dir())
  for p in Path('/proc').iterdir():
    if not p.name.isdigit(): continue
    try:
      if p.stat().st_uid != 1000: continue
      proc = process(int(p.name))
      if proc.get('kind') not in ('webui', 'gateway', 'agent_or_scheduler', 'python_worker'): continue
      r['processes'].append(proc)
      env = dict(x.decode(errors='replace').split('=', 1) for x in read(p / 'environ').split(b'\0') if b'=' in x)
      for k in ('HERMES_HOME', 'HERMES_BASE_HOME'):
        if env.get(k) and Path(env[k]).is_absolute():
          homes.add(Path(env[k]))
      proc['project_plugins_launch_enabled'] = env.get('HERMES_ENABLE_PROJECT_PLUGINS', '').lower() in ('1', 'true', 'yes', 'on')
      proc['native_relay_configured_at_launch'] = bool(env.get('HERMES_NEMO_RELAY_PLUGINS_TOML'))
      proc['webui_password_launch_present'] = bool(env.get('HERMES_WEBUI_PASSWORD'))
    except (FileNotFoundError, ProcessLookupError): pass
    except Exception as exc:
      ERRORS.append({'section': 'process_scan', 'error': type(exc).__name__})
  selected = sorted(homes)[:100]
  r['homes_truncated'] = len(homes) > 100
  r['ledgers'] = [attempt('ledger', lambda h=h: ledger(h)) for h in selected]
  r['hooks'] = [attempt('hooks', lambda h=h: hooks(h)) for h in selected]
  r['entrypoints_metadata_only'] = attempt('entrypoints', lambda: [safe(e.name) for e in importlib.metadata.entry_points(group='hermes_agent.plugins')][:100])
  r['installed_engine_origin'] = attempt('origin', origin)
  r['interpreter'] = safe(sys.executable)
  r['limits'] = ['Snapshot only, not drain/loaded-module proof. No app imports.',
    'Dynamic/project/native Relay hooks unverified; gateway hooks are separate.',
    'Dead/reused/dropped owners do not prove active work. Preserve ledgers.']
  r['errors'] = ERRORS
  fd, temp = tempfile.mkstemp(prefix='.qa-drain-', dir=OUT.parent)
  try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as f:
      json.dump(r, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temp, OUT)
  finally:
    if os.path.exists(temp):
      os.unlink(temp)
if __name__ == '__main__':
  main()
