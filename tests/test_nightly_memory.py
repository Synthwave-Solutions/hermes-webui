import subprocess
from types import SimpleNamespace
from scripts.nightly_memory import run, STAGES


def test_nightly_processes_all_stages_even_after_failure_or_timeout():
    calls=[]
    def runner(command,**kwargs):
        calls.append(command)
        assert '--drain' in command and kwargs['timeout']>0
        if len(calls)==1:
            return SimpleNamespace(returncode=1)
        if len(calls)==2:
            raise subprocess.TimeoutExpired(command,kwargs['timeout'])
        return SimpleNamespace(returncode=0)
    assert run(runner)==1
    assert len(calls)==len(STAGES)==4


def test_nightly_reports_success_only_when_every_stage_succeeds():
    assert run(lambda *a,**k:SimpleNamespace(returncode=0))==0
