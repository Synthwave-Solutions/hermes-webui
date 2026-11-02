#!/usr/bin/env python3
"""Full nightly memory pipeline for all dynamically discovered owner banks."""
import json
from pathlib import Path
import subprocess
import sys

STAGES = (
    ('facts','consolidate_personal_memory.py','--drain','--max-batches','50','--workers','2'),
    ('episodes','consolidate_personal_episodes.py','--drain','--max-batches','64','--workers','8'),
    ('company','consolidate_company_memory.py','--drain','--max-batches','50'),
    ('graph_and_lifecycle','maintain_personal_memory.py','--drain','--max-banks','64'),
)


def run(runner=subprocess.run):
    results = {}
    for name, script, *args in STAGES:
        print(json.dumps({'stage':name,'status':'started'}),flush=True)
        try:
            completed=runner([sys.executable,str(Path(__file__).with_name(script)),*args],timeout=6*3600,check=False)
            results[name]=completed.returncode
        except subprocess.TimeoutExpired:
            results[name]=124
        print(json.dumps({'stage':name,'exit_code':results[name]}),flush=True)
    print(json.dumps({'nightly_results':results}),flush=True)
    return 1 if any(results.values()) else 0


if __name__=='__main__':
    sys.exit(run())
