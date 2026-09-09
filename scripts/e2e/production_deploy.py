#!/usr/bin/env python3
"""Paired, host-bound SynPulse deployment. Launch in its own user systemd unit.

Requires exact reviewed commits and idle runtime. Never rewrites governance,
credentials, task ledgers or session history. Reports contain no secret values.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time

BASE = Path('/home/synthwavehq')
WEB = BASE / 'hermes-webui'
ENGINE = BASE / 'work/codex-20260906-pantheon-engine'
WORK = BASE / 'work/synthpulse'
OUTPUT = WORK / 'qa-release-deployment-20260909.json'
OLD = {'webui': '571c11f9cc184657b49abf93ad9bedf633a437fe',
       'engine': '2960f6c918d8b8141619d5c132c592e1885b073b'}
UNIT = 'hermes-webui.service'
DEPLOY_UNIT = 'synthpulse-release-20260909.service'
REPORT = {'status': 'preparing', 'events': [], 'old_commits': OLD}
HOST_VERIFIED = False

def require(value, reason):
    if not value: raise RuntimeError(reason)

def record(phase, **data):
    REPORT.update(phase=phase, updated_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **data)
    REPORT['events'].append({'phase': phase, 'at': REPORT['updated_at_utc']})
    fd, name = tempfile.mkstemp(prefix='.qa-release-', dir=OUTPUT.parent)
    with os.fdopen(fd, 'w') as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(REPORT, stream, indent=2)
        stream.flush(); os.fsync(stream.fileno())
    os.replace(name, OUTPUT)

def run(args, cwd=None, timeout=60):
    result = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=timeout, check=False)
    require(result.returncode == 0, 'command_failed_' + Path(args[0]).name)
    return result.stdout.decode().strip()

def git(path, *args): return run(['git', '-C', str(path), *args])

def clean(path, allowed):
    status = git(path, 'status', '--porcelain=v1', '--untracked-files=normal').splitlines()
    require(all(line in allowed for line in status), 'unexpected_repository_changes_' + path.name)
    return status

def health():
    connection = http.client.HTTPConnection('127.0.0.1', 8787, timeout=5)
    try:
        connection.request('GET', '/health', headers={'Host':'localhost','Connection':'close'})
        response = connection.getresponse()
        require(response.status == 200, 'health_http_error')
        value = json.loads(response.read(1024 * 1024))
        return {key:value.get(key) for key in ('status','active_runs','active_streams','server_started_at')}
    finally: connection.close()

def wait_healthy(helper, excluded_pid=None):
    until = time.monotonic()+90
    while True:
        try:
            value = health()
            pid = int(run(['systemctl','--user','show',UNIT,'--property=MainPID','--value']))
            if (value['status']=='ok' and pid > 1 and pid != excluded_pid
                    and pid in helper.listener_pids()['pids_owned_by_expected_user']):
                return value,pid
        except Exception: pass
        require(time.monotonic()<until,'service_health_timeout')
        time.sleep(2)

def best_effort_record(*args,**kwargs):
    try: record(*args,**kwargs)
    except Exception: pass

def require_idle_ledgers(helper):
    homes = [BASE/'.hermes', *((BASE/'.hermes/profiles').glob('*'))]
    for home in homes:
        if not home.is_dir(): continue
        info = helper.ledger(home)
        require(info.get('status') != 'unknown', 'unreadable_ledger')
        if not info.get('exists'): continue
        require(info.get('table_present') and isinstance(info.get('unfinished_owner_pids_existing'),int)
                and info['unfinished_owner_pids_existing'] >= 0, 'unknown_ledger_schema')
        connection = sqlite3.connect((home/'state.db').resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
        try:
            connection.execute('PRAGMA query_only=ON')
            # A finished child with undelivered output still belongs to its live owner.
            owners = connection.execute("SELECT DISTINCT owner_pid,owner_started_at FROM async_delegations WHERE "
                "state IN ('running','stalling','finalizing') OR delivery_state='pending'").fetchall()
            for owner_pid,started in owners:
                require(isinstance(owner_pid,int) and owner_pid > 0, 'unknown_delegated_owner')
                proc = Path('/proc')/str(owner_pid)
                if not proc.exists(): continue
                try: current = (proc/'stat').read_text().rsplit(')',1)[1].split()[19]
                except FileNotFoundError: continue
                require(started is not None, 'unknown_delegated_owner_instance')
                require(str(started) != current, 'live_delegated_work_or_delivery_must_finish')
        finally: connection.close()

def main():
    global HOST_VERIFIED
    import socket
    require(socket.gethostname() == 'synthwave-vps' and pwd.getpwuid(os.geteuid()).pw_name == 'synthwavehq'
            and os.getuid() == os.geteuid() == 1000, 'unexpected_host_or_user')
    require(WORK.resolve() == WORK and WORK.stat().st_uid == os.getuid(), 'unexpected_output_owner')
    require(not OUTPUT.is_symlink(), 'unexpected_output_symlink')
    HOST_VERIFIED = True
    os.environ['GIT_TERMINAL_PROMPT'] = '0'
    p = argparse.ArgumentParser()
    p.add_argument('--webui', required=True); p.add_argument('--engine', required=True)
    p.add_argument('--execute', action='store_true')
    args = p.parse_args()
    require(args.execute and all(re.fullmatch('[0-9a-f]{40}', x) for x in (args.webui,args.engine)), 'explicit_exact_commits_required')
    new = {'webui':args.webui,'engine':args.engine}
    REPORT['new_commits'] = new
    require(git(WEB,'rev-parse','HEAD') == OLD['webui'] and git(ENGINE,'rev-parse','HEAD') == OLD['engine'], 'production_base_changed')
    before = {'webui':clean(WEB,set()),'engine':clean(ENGINE,{'?? .playwright-mcp/'})}
    REPORT['preexisting_untracked'] = before
    require(shutil.disk_usage(WORK).free > 1024**3, 'insufficient_disk')
    record('fetching_reviewed_commits')
    for key,path,branch in [('webui',WEB,'master'),('engine',ENGINE,'main')]:
        run(['git','-C',str(path),'fetch','origin',branch],timeout=120)
        require(git(path,'rev-parse','refs/remotes/origin/'+branch) == new[key], 'remote_head_changed_'+key)
        run(['git','-C',str(path),'merge-base','--is-ancestor',OLD[key],new[key]])
    python = ENGINE / '.venv/bin/python'
    # Metadata-only check; deployed environment already contains these exact compatible releases.
    versions = json.loads(run([str(python),'-B','-I','-c',
        'import importlib.metadata as m,json;print(json.dumps({n:m.version(n) for n in ["Pillow","requests","websockets","PyYAML","cryptography","openai"]}))']))
    require(versions['Pillow'].startswith('12.') and versions['requests'].startswith('2.')
            and versions['websockets'].startswith('15.'), 'runtime_dependency_family_changed')
    REPORT['dependency_versions'] = versions
    helper_path = WORK / 'qa-release-preflight-20260908.py'
    spec = importlib.util.spec_from_file_location('release_readonly',helper_path)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    pids = helper.listener_pids()['pids_owned_by_expected_user']
    require(len(pids) == 1, 'ambiguous_listener')
    pid = pids[0]
    env = helper.launch_environment(pid)
    require(env.get('HERMES_WEBUI_AGENT_DIR') == str(ENGINE) and env.get('HERMES_WEBUI_STATE_DIR') == str(BASE/'.hermes/webui'), 'runtime_paths_changed')
    require(run(['systemctl','--user','show',UNIT,'--property=MainPID','--value']) == str(pid), 'service_listener_mismatch')
    REPORT['old_pid'] = pid
    require_idle_ledgers(helper)
    for _ in range(2):
        h = health()
        require(h['status'] == 'ok' and h['active_runs'] == 0 and h['active_streams'] == 0, 'active_webui_work_must_finish')
        time.sleep(1)
    # This per-user rollout must remain in the existing enforcement mode and preserve recovery owners.
    policy = BASE/'.hermes/dashboard-governance.yaml'
    policy_hash = hashlib.sha256(policy.read_bytes()).hexdigest()
    backup = BASE/'.local/state/synthpulse-releases'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup.mkdir(mode=0o700,parents=True,exist_ok=False)
    shutil.copy2(policy,backup/'dashboard-governance.yaml'); (backup/'dashboard-governance.yaml').chmod(0o600)
    (backup/'release.json').write_text(json.dumps({'old':OLD,'new':new,'policy_sha256':policy_hash,'dependencies':versions}))
    (backup/'release.json').chmod(0o600)
    REPORT['backup_directory'] = str(backup)
    record('ready_to_switch', health_before=h)
    # Final idle check immediately precedes stop. Run this script in a separate systemd unit
    # so stopping the WebUI cgroup cannot interrupt the paired swap or rollback.
    require_idle_ledgers(helper)
    cgroup = Path('/proc/self/cgroup').read_text()
    require(DEPLOY_UNIT in cgroup and UNIT not in cgroup
            and run(['systemctl','--user','show',DEPLOY_UNIT,'--property=MainPID','--value'])==str(os.getpid()),
            'deployment_must_have_verified_independent_unit')
    REPORT['deployment_unit'] = DEPLOY_UNIT
    stop_attempted = False
    try:
        h = health(); require(h['active_runs'] == 0 and h['active_streams'] == 0,'work_started_before_stop')
        stop_attempted = True
        run(['systemctl','--user','stop',UNIT],timeout=90)
        require(not helper.listener_pids()['pids_owned_by_expected_user'], 'listener_survived_stop')
        record('service_stopped')
        for key,path in [('engine',ENGINE),('webui',WEB)]:
            require(git(path,'rev-parse','HEAD') == OLD[key], 'source_changed_during_stop_'+key)
            clean(path,{'?? .playwright-mcp/'} if key=='engine' else set())
            git(path,'merge','--ff-only',new[key])
            require(git(path,'rev-parse','HEAD') == new[key], 'checkout_revision_mismatch_'+key)
        record('paired_sources_updated')
        run(['systemctl','--user','start',UNIT],timeout=90)
        h,newpid = wait_healthy(helper,excluded_pid=pid)
        require(hashlib.sha256(policy.read_bytes()).hexdigest()==policy_hash,'policy_changed_during_deploy')
        record('service_healthy', status='deployed_pending_live_smoke', new_pid=newpid, health_after=h,
               governance_policy_preserved=True)
    except Exception as exc:
        best_effort_record('deployment_failed',status='failed',failure_type=type(exc).__name__,failure_code=str(exc)[:120])
        if stop_attempted:
            run(['systemctl','--user','stop',UNIT],timeout=90)
            require(hashlib.sha256(policy.read_bytes()).hexdigest()==policy_hash,'rollback_requires_policy_review')
            for key,path in [('engine',ENGINE),('webui',WEB)]:
                clean(path,{'?? .playwright-mcp/'} if key=='engine' else set())
                require(git(path,'rev-parse','HEAD') in {OLD[key],new[key]}, 'rollback_source_changed_'+key)
                git(path,'checkout','--detach',OLD[key])
            run(['systemctl','--user','start',UNIT],timeout=90)
            restored,restored_pid = wait_healthy(helper,excluded_pid=pid)
            require(all(git(path,'rev-parse','HEAD')==OLD[key] for key,path in [('webui',WEB),('engine',ENGINE)]),'rollback_revision_not_restored')
            record('paired_sources_rolled_back',status='rolled_back',rollback_health=restored,
                   rollback_pid=restored_pid,rollback_checkout_state='detached at recorded old commits')
        raise

if __name__=='__main__':
    try: main()
    except Exception as error:
        if HOST_VERIFIED:
            best_effort_record('stopped_with_error',status=REPORT.get('status','failed'),error_type=type(error).__name__,error_code=str(error)[:120])
        raise SystemExit(1) from None
