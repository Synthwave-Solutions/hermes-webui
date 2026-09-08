#!/usr/bin/env python3
"""Run the real frontend/backend suite in newly created synthetic state.

Usage: .venv/bin/python scripts/e2e/run_full.py --engine ../hermes-agent
Install @playwright/test first; QA_PLAYWRIGHT_CLI can point to its cli.js.
The runner creates private test cookies, binds only loopback, and terminates
both children on every exit. It never reads or resets a real Hermes home.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request

REPO = Path(__file__).resolve().parents[2]
def provenance(directory):
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=directory,text=True).strip()
    diff=subprocess.check_output(['git','diff','HEAD'],cwd=directory)
    files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=directory).decode().split('\0')
    extensions={'.py','.js','.mjs','.cjs','.ts','.css','.html','.toml','.json','.yaml','.yml','.sh'}
    hashes={}
    for relative in sorted(set(files)):
        p=directory/relative
        if p.is_file() and p.suffix in extensions:
            hashes[relative]=hashlib.sha256(p.read_bytes()).hexdigest()
    digest=hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'head':head,'tracked_diff_sha256':hashlib.sha256(diff).hexdigest(),'source_sha256':digest,'source_file_sha256':hashes}
def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--engine',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=REPO.parent/'e2e-runs')
    parser.add_argument('--grep',default='')
    args=parser.parse_args()
    engine=args.engine.resolve()
    if not (engine/'run_agent.py').is_file(): parser.error('engine must contain run_agent.py')
    run=args.out.resolve()/(time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns()%1000000000))
    run.mkdir(parents=True,exist_ok=False)
    state=run/'e2e-state';state.mkdir(mode=0o700)
    port,provider_port=free_port(),free_port()
    while provider_port==port: provider_port=free_port()
    base=f'http://127.0.0.1:{port}'
    env=dict(os.environ,QA_STATE=str(state),QA_SESSIONS=str(state/'browser-sessions.json'),QA_BASE_URL=base,QA_OUT=str(run/'results'))
    cli=os.environ.get('QA_PLAYWRIGHT_CLI',str(REPO.parent/'e2e-tooling/node_modules/@playwright/test/cli.js'))
    if not Path(cli).is_file(): parser.error('set QA_PLAYWRIGHT_CLI to installed @playwright/test/cli.js')
    env.setdefault('NODE_PATH',str(Path(cli).resolve().parents[2]))
    processes=[]
    logs=[]
    initial_source={'webui':provenance(REPO),'engine':provenance(engine)}
    try:
        for name,command in [
            ('provider',[sys.executable,str(REPO/'scripts/e2e/provider_fixture.py'),str(provider_port)]),
            ('server',[sys.executable,str(REPO/'scripts/e2e/server_fixture.py'),str(REPO),str(state),str(engine),str(port),str(provider_port)])]:
            log=(run/(name+'.log')).open('w');logs.append(log)
            processes.append(subprocess.Popen(command,cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True))
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if any(p.poll() is not None for p in processes): raise RuntimeError('fixture process exited; see server/provider log')
            try:
                with urllib.request.urlopen(base+'/health',timeout=1) as response:
                    if response.status==200: break
            except OSError: time.sleep(.2)
        else: raise RuntimeError('fixture health timeout')
        command=['node',cli,'test','-c','playwright.full.config.ts']
        if args.grep: command.extend(['--grep',args.grep])
        result=subprocess.run(command,cwd=REPO,env=env)
        final_source={'webui':provenance(REPO),'engine':provenance(engine)}
        source_unchanged=all(initial_source[k]['source_sha256']==final_source[k]['source_sha256'] for k in initial_source)
        test_sources=[REPO/'playwright.full.config.ts',*(REPO/'tests/e2e/full').glob('*.ts'),*(REPO/'scripts/e2e').glob('*.py')]
        manifest={'base_url':base,'state':'synthetic','engine':str(engine),'test_exit_code':result.returncode,'results':str(run/'results/results.json'),'all_features_certified':False,'source_unchanged_during_run':source_unchanged,'initial_source':initial_source,'final_source':final_source,'test_source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in test_sources}}
        (run/'run.json').write_text(json.dumps(manifest,indent=2))
        print('Evidence:',run)
        return result.returncode if source_unchanged else 1
    finally:
        for proc in reversed(processes):
            try: os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError: pass
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try: os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                proc.wait()
        for log in logs: log.close()
if __name__=='__main__': raise SystemExit(main())
