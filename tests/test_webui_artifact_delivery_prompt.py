"""The per-turn artifact instructions must describe the actual chat renderer.

This verifies prompt assembly and renders its literal examples with production
JavaScript. It does not claim that a provider followed the instructions or that
a browser saved a file.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from api.streaming import _webui_ephemeral_system_prompt
from tests.test_data_uri_images import _DRIVER_SRC


def delivery_prompt():
    return _webui_ephemeral_system_prompt("Keep the selected tone.")


def test_delivery_guidance_is_present_on_each_prompt_assembly():
    for _ in range(2):
        prompt = delivery_prompt()
        assert "Keep the selected tone." in prompt
        assert prompt.count("WebUI artifact delivery:") == 1
        assert "Verify the file exists" in prompt
        assert "not just a raw server path" in prompt
        assert "authorization and path checks still apply" in prompt
        assert "Do not invent sandbox:" in prompt


@pytest.fixture(scope="module")
def render_example(tmp_path_factory):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to execute the actual renderer")
    driver = tmp_path_factory.mktemp("artifact_protocol") / "driver.js"
    # Supply the current chat so the production media helper builds its normal
    # session-scoped URL; renderer and media policy remain production functions.
    driver.write_text(_DRIVER_SRC.replace(
        "const S = {};", "const S = {session: {session_id: 'artifact-session'}};"
    ))
    ui = Path(__file__).parents[1] / "static/ui.js"

    def render(markdown):
        result = subprocess.run([node, str(driver), str(ui)], input=markdown,
                                text=True, capture_output=True, check=True, timeout=15)
        return result.stdout

    return render


@pytest.mark.parametrize("ref,expected", [
    ("MEDIA:/absolute/path/to/chart.png", 'class="msg-artifact-image"'),
    ("MEDIA:/absolute/path/to/deliverables.zip", 'download="deliverables.zip"'),
    ("MEDIA:file:///absolute/path/to/Quarterly%20Report.pdf", 'data-path="/absolute/path/to/Quarterly Report.pdf"'),
])
def test_prompt_media_examples_render_as_artifacts(render_example, ref, expected):
    prompt = delivery_prompt()
    examples = re.findall(r"MEDIA:[^\s`]+", prompt)
    assert ref in examples
    html = render_example(ref)
    assert expected in html
    assert "MEDIA:" not in html
    if ref.endswith(".zip"):
        assert "api/media?path=%2Fabsolute%2Fpath%2Fto%2Fdeliverables.zip" in html
        assert "session_id=artifact-session" in html
        assert "download=1" in html


def test_prompt_workspace_example_uses_friendly_label_and_relative_preview(render_example):
    prompt = delivery_prompt()
    link = "[Open report](workspace://outputs/Quarterly%20Report.pdf)"
    assert link in prompt
    html = render_example(link)
    assert 'href="#workspace=outputs%2FQuarterly%20Report.pdf"' in html
    assert ">Open report</a>" in html
    assert "workspace://" not in html
    assert "/absolute/" not in html
