"""Hermetic native-engine probe; no provider or messaging service is contacted."""

from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import sys
from unittest.mock import patch


def main():
    try:
        from cron import delivery_queue, executions, jobs, scheduler, scheduler_authority
        from hermes_cli import gateway_client
    except ImportError as exc:
        print(f"Native receipt APIs unavailable: {exc}")
        return 77
    if not hasattr(executions, "adopt_claimed_execution"):
        print("Native execution handoff API unavailable")
        return 77
    from api import routes

    mode = sys.argv[1]
    home = Path(os.environ["HERMES_HOME"])
    home.mkdir(parents=True, exist_ok=True)
    job = (json.loads(Path(sys.argv[2]).read_text()) if mode in {"worker", "dispatch"} else
           jobs.create_job(prompt="Synthetic Scout", schedule="every 1h", deliver="telegram:1"))
    delivered = []
    receipts = []
    result = (True, "# Synthetic Scout\n\nOne useful result.", "One useful result.", None)

    class Peer:
        async def rpc(self, method, **params):
            if method == "cron.submit":
                receipts.append(dict(params))
                return {"session_id": "synthetic-session", "admission_id": "synthetic-admission"}
            if method in {"cron.status", "cron.recover"}:
                return {"status": "terminal", "job": job, "result": list(result)}
            raise AssertionError(method)

    @asynccontextmanager
    async def connect():
        yield Peer()

    if mode == "worker":
        original_save = scheduler._save_compose_deliver

        def crash_after_queue(*args, **kwargs):
            original_save(*args, **kwargs)
            # A real child dies after persisting the delivery request, before
            # bookkeeping or its response to the WebUI parent can complete.
            os._exit(23)

        with patch.object(gateway_client, "connect_gateway", connect), \
                patch.object(scheduler, "_save_compose_deliver", crash_after_queue):
            routes._cron_job_subprocess_main(
                job, home, Queue(), run_kwargs={"trigger": "manual", "execution_id": job["execution_id"]},
                native_execution=job["execution_id"],
            )
        raise AssertionError("worker did not reach the crash boundary")

    class ResultQueue(Queue):
        def get(self, timeout=None):
            if mode == "lost_reply":
                raise Empty
            return super().get(timeout=0.1)

        def close(self):
            pass

        def join_thread(self):
            pass

    class InlineProcess:
        exitcode = 0

        def __init__(self, target, args):
            self.target, self.args = target, args

        def start(self):
            if mode in {"crash", "dispatch"}:
                payload = home / "worker.json"
                payload.write_text(json.dumps(self.args[0]))
                child = subprocess.run([sys.executable, __file__, "worker", str(payload)], timeout=30)
                self.exitcode = child.returncode
                assert self.exitcode == 23, self.exitcode
                if mode == "dispatch":
                    os._exit(24)  # the caller dies too, without running its error handler
            else:
                self.target(*self.args)

        def join(self, timeout=None):
            pass

        def is_alive(self):
            return False

    class Context:
        Queue = ResultQueue
        Process = InlineProcess

    original_run = scheduler.run_job

    def run_with_competing_recovery(*args, **kwargs):
        returned = original_run(*args, **kwargs)
        # The observed failure: the native receipt is terminal before the WebUI
        # child returns, while two scheduler ticks try to settle the same fire.
        for _ in range(2):
            scheduler_authority.reconcile_pending()
        return returned

    with patch.object(gateway_client, "connect_gateway", connect), \
            patch.object(scheduler, "run_job", run_with_competing_recovery), \
            patch.object(scheduler, "_deliver_result", lambda job, content, **kw: delivered.append(content)), \
            patch("multiprocessing.get_context", return_value=Context()):
        if mode == "caller_dies":
            payload = home / "caller.json"
            payload.write_text(json.dumps(job))
            caller = subprocess.run([sys.executable, __file__, "dispatch", str(payload)], timeout=45)
            assert caller.returncode == 24, caller.returncode
        else:
            routes._mark_cron_running(job["id"])
            routes._run_cron_tracked(job, home, home)
        if mode in {"crash", "caller_dies"}:
            journals = list((home / "cron" / "admissions").glob("*.json"))
            assert len(journals) == 1, journals
            receipts.append(json.loads(journals[0].read_text())["params"])
            assert executions.get_execution(receipts[0]["request_id"])["status"] == (
                "unknown" if mode == "crash" else "running")
            assert jobs.get_job(job["id"])["repeat"]["completed"] == 0
            # A fresh scheduler can recover the crashed child; no WebUI
            # callback or result payload from that process is needed.
            scheduler_authority.reconcile_pending()
            scheduler_authority.reconcile_pending()
        delivery_queue.drain(lambda job, content, failure: delivered.append(content))
        scheduler_authority.reconcile_pending()
        delivery_queue.drain(lambda job, content, failure: delivered.append(content))

    saved = jobs.get_job(job["id"])
    assert saved["repeat"]["completed"] == 1, saved
    assert delivered == [result[2]], delivered
    assert len(receipts) == 1, receipts
    execution_id = receipts[0]["request_id"]
    row = executions.get_execution(execution_id)
    assert row and row["status"] == "completed", row
    assert saved["canonical_completions"] == [execution_id], saved
    assert not scheduler_authority.journal_path(job["id"], execution_id).exists()
    assert routes._is_cron_running(job["id"]) == (False, 0.0)
    print(json.dumps({"completions": 1, "deliveries": len(delivered), "execution_id": execution_id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
