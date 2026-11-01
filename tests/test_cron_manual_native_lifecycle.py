"""Exercise manual completion against native receipts, ledger and delivery queue."""

import os
from pathlib import Path
import subprocess

import pytest

from tests.conftest import HERMES_AGENT, REPO_ROOT, VENV_PYTHON


@pytest.mark.skipif(HERMES_AGENT is None, reason="requires the native cron engine")
@pytest.mark.parametrize("mode", ["complete", "lost_reply", "crash", "caller_dies"])
def test_manual_and_native_receipt_recovery_share_one_completion(tmp_path, mode):
    probe = Path(__file__).parent / "fixtures" / "cron_manual_native_probe.py"
    env = {
        key: value for key, value in os.environ.items()
        if key in {"PATH", "LANG", "LC_ALL", "SYSTEMROOT"}
    }
    env.update({
        "HOME": str(tmp_path / "user"),
        "HERMES_HOME": str(tmp_path / "profile"),
        "HERMES_RUNTIME_DIR": str(tmp_path / "runtime"),
        "HERMES_WEBUI_STATE_DIR": str(tmp_path / "webui"),
        "HERMES_WEBUI_AGENT_DIR": str(HERMES_AGENT),
        "PYTHONPATH": os.pathsep.join((str(REPO_ROOT), str(HERMES_AGENT))),
    })
    result = subprocess.run(
        [VENV_PYTHON, str(probe), mode], env=env, cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode == 77:
        pytest.skip(result.stdout.strip())
    assert result.returncode == 0, result.stdout + result.stderr
