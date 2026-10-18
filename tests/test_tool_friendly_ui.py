"""Execute the real dependency-free friendly tool row presenter."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_friendly_tool_rows_presentation():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for frontend behavior checks")
    result = subprocess.run(
        [node, str(Path(__file__).with_suffix(".cjs"))],
        text=True, capture_output=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_friendly_modules_are_loaded_and_cached():
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    for name in ("tool-friendly.js", "subagent-threads.js"):
        assert f'static/{name}?v=__WEBUI_VERSION__' in html
        assert f"./static/{name}" in sw
    # Loaded before ui.js renders rows and before messages.js streams events.
    assert html.index("static/tool-friendly.js") < html.index("static/messages.js")
    assert 'id="spSubagentDock"' in html


def test_ui_copy_has_no_en_or_em_dashes():
    for name in ("tool-friendly.js", "subagent-threads.js"):
        text = (ROOT / "static" / name).read_text(encoding="utf-8")
        assert "–" not in text and "—" not in text, name
