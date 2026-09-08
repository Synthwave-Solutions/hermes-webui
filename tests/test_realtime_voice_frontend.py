"""Node lifecycle tests for the native realtime frontend state machine."""
from pathlib import Path
import shutil
import subprocess


def test_native_realtime_frontend_lifecycle_contract():
    node = shutil.which("node")
    assert node, "Node is required to verify the realtime frontend"
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [node, "--test", str(root / "tests/realtime_voice_frontend.test.cjs")],
        cwd=root, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
