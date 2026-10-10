"""Guida 0.2.0 is vendored, pinned and loaded only from this app (plan 6.1, 6.2).

The help tours use Guida's UMD build behind ``static/help-tour.js``. The file
is the unmodified ``dist/index.js`` of the npm archive, pinned by sha256, and
the page loads it from ``static/vendor`` (never from a CDN), deferred and
before the help scripts and ``boot.js``. The service worker precaches it so a
cached shell still has it offline.
"""

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
VENDOR = STATIC / "vendor" / "guida" / "0.2.0"
GUIDA = VENDOR / "guida.umd.js"
GUIDA_SHA256 = "f59fc2684a1b8d9c2e85d065d2462a3dcb971a9e177fbf71236adae8fcc20e69"
GUIDA_TAG_PATH = "static/vendor/guida/0.2.0/guida.umd.js"
HELP_SCRIPTS = (GUIDA_TAG_PATH, "static/help-content.js", "static/help-tour.js")
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node not on PATH")


def _tag(path: str) -> str:
    return f'<script src="{path}?v=__WEBUI_VERSION__" defer></script>'


def test_vendored_guida_matches_the_pinned_upstream_build():
    body = GUIDA.read_bytes()
    assert hashlib.sha256(body).hexdigest() == GUIDA_SHA256
    # The UMD build exposes one global and never fetches anything itself.
    text = body.decode("utf-8")
    assert "SpotlightOnboarding" in text
    assert "fetch(" not in text and "XMLHttpRequest" not in text


def test_vendored_guida_ships_its_licence_and_package_metadata():
    licence = (VENDOR / "LICENSE").read_text(encoding="utf-8")
    assert licence.startswith("MIT License")
    assert "Permission is hereby granted" in licence
    package = json.loads((VENDOR / "package.json").read_text(encoding="utf-8"))
    assert package["name"] == "guida.js"
    assert package["version"] == "0.2.0"
    assert package["license"] == "MIT"
    assert package["main"] == "dist/index.js"
    vendor_note = (VENDOR / "VENDOR.md").read_text(encoding="utf-8")
    assert "https://registry.npmjs.org/guida.js/-/guida.js-0.2.0.tgz" in vendor_note
    assert GUIDA_SHA256 in vendor_note


def test_vendor_directory_holds_only_the_documented_files():
    assert sorted(p.name for p in VENDOR.iterdir()) == [
        "LICENSE", "VENDOR.md", "guida.umd.js", "package.json",
    ]


def test_index_loads_guida_locally_and_never_from_a_cdn():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    mentions = [m.start() for m in re.finditer(r"guida", html, re.I)]
    tag = _tag(GUIDA_TAG_PATH)
    assert html.count(tag) == 1
    start = html.index(tag)
    # Every mention of the library is the one local, relative script tag, so
    # no CDN copy (unpkg, jsdelivr and the like) can be loaded next to it.
    assert mentions and all(start <= pos < start + len(tag) for pos in mentions)


def test_help_scripts_load_nothing_remote():
    for rel in ("static/help-tour.js", "static/help-content.js", "static/help-tour.css"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "http://" not in text and "https://" not in text, rel
        assert "import(" not in text, rel
        assert "createElement('script')" not in text and 'createElement("script")' not in text, rel


def test_script_order_guida_then_content_then_wrapper_then_boot():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    positions = []
    for path in HELP_SCRIPTS + ("static/boot.js",):
        tag = _tag(path)
        assert html.count(tag) == 1, path
        positions.append(html.index(tag))
    assert positions == sorted(positions)
    # The help stylesheet sits in the head like the other feature styles.
    css = '<link rel="stylesheet" href="static/help-tour.css?v=__WEBUI_VERSION__">'
    assert html.count(css) == 1 and html.index(css) < html.index("</head>")


def test_service_worker_precaches_the_help_assets():
    sw = (STATIC / "sw.js").read_text(encoding="utf-8")
    start = sw.index("const SHELL_ASSETS")
    shell = sw[start:sw.index("];", start)]
    for rel in HELP_SCRIPTS + ("static/help-tour.css",):
        assert shell.count("'./" + rel + "' + VQ,") == 1, rel
        assert (ROOT / rel).is_file(), rel


@needs_node
def test_umd_build_defines_the_guida_class_on_its_global():
    script = r"""
const fs=require('fs'),vm=require('vm');
const ctx={};ctx.globalThis=ctx;ctx.self=ctx;vm.createContext(ctx);
vm.runInContext(fs.readFileSync('static/vendor/guida/0.2.0/guida.umd.js','utf8'),ctx);
const lib=ctx.SpotlightOnboarding;
process.stdout.write(JSON.stringify({
  guida: typeof (lib&&lib.Guida),
  create: typeof (lib&&lib.createOnboarding),
  quick: typeof (lib&&lib.quickStart),
}));
"""
    done = subprocess.run([NODE, "-e", script], capture_output=True, text=True,
                          timeout=60, cwd=str(ROOT))
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {"guida": "function", "create": "function", "quick": "function"}


def test_help_tour_behaviour_in_a_real_browser():
    """Run tests/help_tour_behavior.cjs: the wrapper around this vendored build.

    Uses the Playwright package bundled with Python Playwright (as the CI job
    installs it) unless PLAYWRIGHT_MODULE points at another one. The page is
    served from a fake origin by Playwright routes, so nothing leaves the box.
    """
    import importlib.util
    import os

    env = os.environ.copy()
    node = NODE
    if not env.get("PLAYWRIGHT_MODULE") or node is None:
        spec = importlib.util.find_spec("playwright")
        if not (spec and spec.origin):
            pytest.skip("Playwright is not installed")
        driver = Path(spec.origin).parent / "driver"
        if not env.get("PLAYWRIGHT_MODULE"):
            package = driver / "package"
            if not (package / "package.json").is_file():
                pytest.skip("Python Playwright's bundled package was not found")
            env["PLAYWRIGHT_MODULE"] = str(package)
        if node is None:
            bundled = driver / ("node.exe" if os.name == "nt" else "node")
            if not bundled.is_file():
                pytest.skip("no Node to run the browser test")
            node = str(bundled)
    done = subprocess.run([node, "tests/help_tour_behavior.cjs"], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, timeout=420)
    print(done.stdout, end="")
    if done.returncode != 0 and "Executable doesn't exist" in (done.stdout + done.stderr):
        pytest.skip("Chromium for Playwright is not installed")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "0 failed" in done.stdout
