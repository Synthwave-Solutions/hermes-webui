"""Execute the integration UI with a controlled clock and API responses."""
from pathlib import Path
import subprocess


def test_hosted_oauth_survives_hidden_document_and_ignores_stale_responses():
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ['node', str(root / 'tests/frontend/hosted-oauth-lifecycle.cjs')],
        cwd=root, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
