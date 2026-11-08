"""Extra data block kinds (static/interactive-ui/kinds/*.js): each has a Node check file
tests/kinds_<kind>.cjs, is loaded by the kit frame and by the chat page, and registers."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KINDS = sorted(p.stem for p in (ROOT / "static" / "interactive-ui" / "kinds").glob("*.js"))


@pytest.mark.parametrize("kind", KINDS)
def test_kind_checks_in_node(kind):
    test = ROOT / "tests" / f"kinds_{kind}.cjs"
    assert test.is_file(), f"{kind} needs tests/kinds_{kind}.cjs"
    out = subprocess.run(["node", str(test)], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
    assert "ok" in out.stdout


@pytest.mark.parametrize("kind", KINDS)
def test_kind_is_loaded_everywhere(kind):
    from api import interactive_ui
    assert f"interactive-ui/kinds/{kind}.js" in interactive_ui.KIT_SCRIPT_FILES
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    assert f'static/interactive-ui/kinds/{kind}.js?v=__WEBUI_VERSION__' in html, "the chat page checks blocks too"
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    assert f"./static/interactive-ui/kinds/{kind}.js" in sw


@pytest.mark.parametrize("kind", KINDS)
def test_kind_registers_after_kit_core(kind):
    js = (
        "const path=require('path');const K=require(path.join(process.argv[1],'static/interactive-ui/kit-core.js'));"
        "global.SWKit=K;require(path.join(process.argv[1],'static/interactive-ui/kinds',process.argv[2]+'.js'));"
        "if(!K.extra(process.argv[2]))process.exit(3);process.stdout.write('registered')"
    )
    out = subprocess.run(["node", "-e", js, str(ROOT), kind], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0 and out.stdout == "registered", out.stderr
