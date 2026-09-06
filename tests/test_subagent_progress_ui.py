"""Execute the real dependency-free lifecycle presenter."""
from pathlib import Path
import shutil
import subprocess
import pytest


def test_structured_worker_lifecycle_presentation():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for frontend behavior checks")
    result = subprocess.run(
        [node, str(Path(__file__).with_suffix(".cjs"))],
        text=True, capture_output=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
