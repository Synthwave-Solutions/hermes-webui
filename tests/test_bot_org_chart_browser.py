"""Bot org chart in a real browser; all bot data is synthetic."""

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path


def test_bot_org_chart_renders_tree_and_narrow_list_in_real_browser():
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    explicit_module = env.get("PLAYWRIGHT_MODULE")
    if explicit_module is not None:
        assert explicit_module.strip(), "PLAYWRIGHT_MODULE must not be empty"
    node = shutil.which("node")
    if explicit_module is None or node is None:
        # The CI pytest job installs Python Playwright and Chromium, not the
        # npm package. Use its existing bundled driver without installing more
        # dependencies or replacing an explicit, potentially invalid override.
        spec = importlib.util.find_spec("playwright")
        assert spec and spec.origin, (
            "Python Playwright is required when PLAYWRIGHT_MODULE or Node is unavailable"
        )
        driver = Path(spec.origin).parent / "driver"
        if explicit_module is None:
            package = driver / "package"
            assert (package / "package.json").is_file(), (
                "Python Playwright's bundled Node package was not found"
            )
            env["PLAYWRIGHT_MODULE"] = str(package)
        if node is None:
            bundled_node = driver / ("node.exe" if os.name == "nt" else "node")
            assert bundled_node.is_file(), "Python Playwright's bundled Node executable was not found"
            node = str(bundled_node)
    assert node, "Node is required for the bot org chart browser regression"
    result = subprocess.run(
        [node, "tests/bot_org_chart_browser.cjs"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    print(result.stdout, end="")
    assert result.returncode == 0, result.stdout + result.stderr
