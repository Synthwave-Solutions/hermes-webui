"""Interactive answers: the sandbox frame, the prompt block and the wiring.

The frame must always run in an opaque origin with network limited to the
public CDNs; the prompt block reaches browser and Gateway turns exactly once;
the renderer seams stay guarded so the chat renders as before without the
module. The parser is exercised in Node through ``interactive_ui_parse.cjs``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from api import interactive_ui, streaming

REPO = Path(__file__).resolve().parents[1]
STATIC = REPO / "static"
UI = (STATIC / "ui.js").read_text(encoding="utf-8")
MESSAGES = (STATIC / "messages.js").read_text(encoding="utf-8")
MODULE = (STATIC / "interactive_ui.js").read_text(encoding="utf-8")
CSS = (STATIC / "interactive_ui.css").read_text(encoding="utf-8")
INDEX = (STATIC / "index.html").read_text(encoding="utf-8")
SW = (STATIC / "sw.js").read_text(encoding="utf-8")
NODE = shutil.which("node")
LONG_DASHES = "[" + chr(0x2013) + chr(0x2014) + "]"
HEADER = "WebUI interactive answers:"


class _Handler:
    def __init__(self, command="GET"):
        self.command = command
        self.status = None
        self.headers = []
        self.body = b""
        self.wfile = self

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.headers.append((name, value))

    def end_headers(self):
        pass

    def write(self, data):
        self.body += data

    def header(self, name):
        values = [v for k, v in self.headers if k.lower() == name.lower()]
        assert len(values) == 1, (name, values)
        return values[0]


def _get(path, command="GET"):
    handler = _Handler(command)
    ok = interactive_ui.serve(handler, SimpleNamespace(path=path, params=""))
    return ok, handler


def _directives(csp):
    out = {}
    for part in csp.split(";"):
        words = part.strip().split(None, 1)
        if words:
            out[words[0]] = words[1] if len(words) > 1 else ""
    return out


# ── Frame document ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [interactive_ui.FRAME_PATH, "/session" + interactive_ui.FRAME_PATH])
def test_frame_is_served_with_its_own_headers(path):
    ok, handler = _get(path)
    assert ok is True and handler.status == 200
    assert handler.body == interactive_ui.FRAME_BYTES
    assert handler.header("Content-Type") == "text/html; charset=utf-8"
    assert handler.header("Cache-Control") == "no-store"
    assert handler.header("Referrer-Policy") == "no-referrer"
    assert handler.header("X-Frame-Options") == "SAMEORIGIN"
    assert int(handler.header("Content-Length")) == len(interactive_ui.FRAME_BYTES)
    assert not any(k.lower() == "set-cookie" for k, _ in handler.headers)


def test_head_sends_headers_without_a_body():
    ok, handler = _get(interactive_ui.FRAME_PATH, "HEAD")
    assert ok and handler.status == 200 and handler.body == b""


@pytest.mark.parametrize("path", ["/static/interactive-ui/", "/static/interactive-ui/frame.htm",
                                  "/static/interactive-ui/frame.html/", "/static/interactive-ui/../ui.js",
                                  "/static/interactive-ui/%66rame.html", "/api/interactive-ui/frame.html"])
def test_only_the_exact_frame_path_is_served(path):
    ok, handler = _get(path)
    assert ok is False and handler.status is None


def test_frame_csp_keeps_the_widget_in_an_opaque_origin():
    csp = _directives(interactive_ui.FRAME_CSP)
    sandbox = csp["sandbox"].split()
    assert set(sandbox) == {"allow-scripts", "allow-forms", "allow-popups"}
    assert "allow-same-origin" not in interactive_ui.FRAME_CSP
    assert "allow-top-navigation" not in interactive_ui.FRAME_CSP
    assert "allow-popups-to-escape-sandbox" not in interactive_ui.FRAME_CSP
    assert csp["default-src"] == "'none'"
    assert csp["form-action"] == "'none'"
    assert csp["base-uri"] == "'none'"
    assert csp["frame-src"] == "'none'"
    assert csp["object-src"] == "'none'"
    assert csp["frame-ancestors"] == "'self'"
    # Network only to the public CDNs: generated code cannot post data elsewhere.
    assert set(csp["connect-src"].split()) == set(interactive_ui.CDN_HOSTS)
    script_hosts = {w for w in csp["script-src"].split() if w.startswith("https://")}
    assert script_hosts == set(interactive_ui.CDN_HOSTS)
    for host in interactive_ui.CDN_HOSTS:
        assert host.startswith("https://") and "*" not in host


def test_frame_document_contains_shell_theme_and_import_map():
    html = interactive_ui.FRAME_HTML
    assert '<div id="iui-root"></div>' in html
    assert '<style id="iui-user-style"></style>' in html
    assert html.index('type="importmap"') < html.index("<script>")
    imports = json.loads(interactive_ui.IMPORT_MAP)["imports"]
    assert {"three", "d3", "chart.js", "gsap"} <= set(imports)
    for url in imports.values():
        assert any(url.startswith(h + "/") for h in interactive_ui.CDN_HOSTS)
    # The shell only listens to its host window and exposes the bridge.
    shell = interactive_ui.SHELL_JS
    assert "if(e.source !== host || (HOST_OK && e.origin !== HOST_ORIGIN)) return;" in shell
    assert "host.postMessage(Object.assign({iui:1}, msg), HOST_OK ? HOST_ORIGIN : '*')" in shell
    # Opened on its own (no parent), the frame renders nothing and exposes no bridge.
    assert shell.index("if(!host || host === window){") < shell.index("window.synthwave = api;")
    # Common model habits are made harmless.
    for token in ("document.write = document.writeln", "memoryStorage()", "new Event('DOMContentLoaded'"):
        assert token in shell
    assert "window.synthwave = api;" in shell
    assert "window.Websandbox" in shell
    for token in ("--sw-bg", "--sw-accent", "--sw-c1", ".card", ".stat", "button.primary"):
        assert token in interactive_ui.BASE_CSS
    # The body stays transparent so the card follows the chat surface.
    assert "background:transparent" in interactive_ui.BASE_CSS


def test_routes_dispatch_the_frame_before_the_generic_static_handler():
    routes = (REPO / "api" / "routes.py").read_text(encoding="utf-8")
    call = 'if parsed.path in ("/static/interactive-ui/frame.html", "/session/static/interactive-ui/frame.html"):'
    assert routes.count(call) == 1
    assert routes.index('"/static/vendor/mnemosyne-dashboard/"') < routes.index(call)


# ── Prompt block ────────────────────────────────────────────────────────────

@pytest.fixture
def isolated_prompt(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv(interactive_ui.ENV_VAR, raising=False)
    monkeypatch.setattr(streaming, "get_config", lambda: {})
    from api import bot_builder, bot_knowledge, bot_metadata
    monkeypatch.setattr(bot_metadata, "knowledge_prompt", lambda *a: "")
    monkeypatch.setattr(bot_knowledge, "prompt", lambda *a: "")
    monkeypatch.setattr(bot_builder, "memory_prompt", lambda *a: "")


def _prompt(config=None):
    return streaming._webui_ephemeral_system_prompt("Keep the selected tone.", config_data=config)


def test_prompt_block_is_on_by_default_and_appears_once(isolated_prompt):
    for _ in range(2):
        text = _prompt({})
        assert text.count(HEADER) == 1
        assert interactive_ui.PROMPT in text
    assert text.index("WebUI artifact delivery:") < text.index(HEADER) < text.index("SynthPulse interaction guidance:")


@pytest.mark.parametrize("env,config,expected", [
    (None, None, True), (None, {"webui_interactive_ui": False}, False), (None, {"webui_interactive_ui": "off"}, False),
    (None, {"webui_interactive_ui": "banana"}, True), ("0", {}, False), ("1", {"webui_interactive_ui": False}, True),
    ("maybe", {"webui_interactive_ui": False}, False),
])
def test_switch_and_environment_override(isolated_prompt, monkeypatch, env, config, expected):
    if env is not None:
        monkeypatch.setenv(interactive_ui.ENV_VAR, env)
    assert interactive_ui.enabled(config) is expected
    assert (HEADER in _prompt(config)) is expected


def test_prompt_text_names_the_contract_and_has_no_long_dashes():
    text = interactive_ui.PROMPT
    assert "interactive-ui" in text
    assert "<style>" in text and "<script>" in text
    for host in ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com", "esm.sh"):
        assert host in text
    assert "synthwave.sendPrompt" in text
    assert "the user confirms it" in text
    assert not re.search(LONG_DASHES, text)
    assert not re.search(LONG_DASHES, MODULE)
    assert not re.search(LONG_DASHES, CSS)


# ── Wiring ──────────────────────────────────────────────────────────────────

def test_fence_seam_is_guarded_and_runs_before_svg_and_mermaid():
    call = "if(_iuiFenceOk(lang,code)) return lead+_iuiPlaceholder(code,lang);"
    assert UI.count(call) == 1
    assert UI.index(call) < UI.index("if(_svgVisualFenceAccepts(lang,code))") < UI.index("if(lang==='mermaid'")
    assert "if(typeof interactiveUiFenceAccepts!=='function') return false;" in UI
    assert "try{return interactiveUiFenceAccepts(lang,code)===true;}catch(_){return false;}" in UI
    assert '<div class="iui-block" data-iui-id="${id}" data-iui-kind="${kind}">${esc(code.trim())}</div>' in UI
    assert "const kind=/^[a-z-]+$/.test(lang||'')?lang:'interactive-ui';" in UI


def test_placeholder_is_protected_from_the_paragraph_splitter_and_cannot_be_forged():
    assert '|<div class="iui-block"[\\s\\S]*?<\\/div>|<div class="svg-visual-block"' in UI
    # _tag only keeps whitelisted div classes, so raw model HTML cannot claim iui-block.
    assert "_cls(a.class,['pre-header','mermaid-block','katex-block'])" in UI


def test_post_process_and_stream_hooks_are_guarded():
    assert "if(typeof renderInteractiveUiBlocks==='function'){try{renderInteractiveUiBlocks(container);}" in UI
    assert "if(assistantBody&&typeof interactiveUiStreamTick==='function'){try{interactiveUiStreamTick(assistantBody);}catch(_){}}" in MESSAGES


def test_assets_are_loaded_and_cached():
    assert '<script src="static/interactive_ui.js?v=__WEBUI_VERSION__" defer></script>' in INDEX
    assert '<link rel="stylesheet" href="static/interactive_ui.css?v=__WEBUI_VERSION__">' in INDEX
    assert INDEX.index("static/interactive_ui.js") < INDEX.index('src="static/ui.js')
    assert "'./static/interactive_ui.js' + VQ" in SW and "'./static/interactive_ui.css' + VQ" in SW


def test_host_never_puts_widget_source_into_its_own_dom_as_html():
    # The source is only ever set with textContent or sent to the frame.
    code = "\n".join(line for line in MODULE.splitlines() if not line.lstrip().startswith("//"))
    assert "innerHTML=ctrl.source" not in code.replace(" ", "")
    assert "iframe.setAttribute('sandbox','allow-scripts allow-forms allow-popups');" in MODULE
    assert "allow-same-origin" not in code
    assert "byWindow.get(e.source)" in code
    assert "if(e.origin!=='null') return;" in code
    # Widget prompts are only offered; the host's own trusted click sends them.
    assert "if(!ev||!ev.isTrusted) return;" in code
    assert "window.open(FRAME_URL" not in code
    assert "srcdoc" not in code


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_parser_in_node():
    import os
    env = dict(os.environ)
    templates = Path.home() / ".hermes" / "skills" / "synthwave" / "interactive-ui" / "templates"
    if templates.is_dir():
        env["IUI_TEMPLATES"] = str(templates)
    result = subprocess.run([NODE, str(REPO / "tests" / "interactive_ui_parse.cjs")], env=env,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all parser checks passed" in result.stdout


# ── Data blocks: the kit frame ──────────────────────────────────────────────

class _Request(_Handler):
    """A handler with request headers kept apart from the response headers."""

    def __init__(self, command="GET", request_headers=None):
        super().__init__(command)
        self.request_headers = dict(request_headers or {})


def _get_kit(path=interactive_ui.KIT_FRAME_PATH, request_headers=None, config=None, monkeypatch=None):
    if monkeypatch is not None:
        monkeypatch.setattr(interactive_ui, "_config", lambda: dict(config or {}))
    handler = _Request("GET", request_headers)
    # serve() reads If-None-Match from handler.headers (the request headers in the real server).
    real_headers = handler.headers
    handler.headers = _HeaderView(handler.request_headers, real_headers)
    ok = interactive_ui.serve(handler, SimpleNamespace(path=path, params=""))
    return ok, handler


class _HeaderView(list):
    def __init__(self, request, sent):
        super().__init__(sent)
        self._request = request

    def get(self, name, default=None):
        return self._request.get(name, default)


def _sent(handler, name):
    values = [v for k, v in list(handler.headers) if k.lower() == name.lower()]
    assert len(values) == 1, (name, values)
    return values[0]


@pytest.mark.parametrize("path", [interactive_ui.KIT_FRAME_PATH, "/session" + interactive_ui.KIT_FRAME_PATH])
def test_kit_frame_is_served_with_its_own_policy(path, monkeypatch):
    ok, handler = _get_kit(path, config={}, monkeypatch=monkeypatch)
    assert ok is True and handler.status == 200
    assert handler.body == interactive_ui.KIT_FRAME_BYTES
    assert _sent(handler, "Content-Security-Policy") == interactive_ui.kit_frame_csp({})
    assert _sent(handler, "Cache-Control") == "private, no-cache"
    assert _sent(handler, "Referrer-Policy") == "no-referrer"
    assert _sent(handler, "X-Frame-Options") == "SAMEORIGIN"
    etag = _sent(handler, "ETag")
    ok, again = _get_kit(path, request_headers={"If-None-Match": etag}, config={}, monkeypatch=monkeypatch)
    assert ok and again.status == 304 and again.body == b""


def test_kit_frame_csp_runs_only_its_own_hashed_scripts():
    csp = _directives(interactive_ui.KIT_FRAME_CSP)
    assert csp["sandbox"].split() == ["allow-scripts"], "no popups, forms or same origin"
    assert csp["default-src"] == "'none'"
    assert csp["connect-src"] == "'none'"
    assert csp["form-action"] == "'none'" and csp["base-uri"] == "'none'" and csp["frame-ancestors"] == "'self'"
    scripts = csp["script-src"].split()
    assert scripts and all(re.fullmatch(r"'sha256-[A-Za-z0-9+/]{43}='", s) for s in scripts), scripts
    assert "unsafe-eval" not in interactive_ui.KIT_FRAME_CSP
    assert "'unsafe-inline'" not in csp["script-src"]
    for host in interactive_ui.CDN_HOSTS:
        assert host not in interactive_ui.KIT_FRAME_CSP
    assert csp["img-src"].split() == ["data:", "https://tile.openstreetmap.org", "https://upload.wikimedia.org"]
    # The widget frame keeps its own policy.
    assert "allow-popups" in interactive_ui.FRAME_CSP and "allow-popups" not in interactive_ui.KIT_FRAME_CSP


def test_kit_frame_hashes_match_the_served_scripts():
    import base64
    import hashlib
    bodies = re.findall(r"<script>([\s\S]*?)</script>", interactive_ui.KIT_FRAME_HTML)
    assert len(bodies) == len(interactive_ui.KIT_SCRIPT_FILES) == len(interactive_ui.KIT_SCRIPT_HASHES)
    served = ["'sha256-" + base64.b64encode(hashlib.sha256(b.encode("utf-8")).digest()).decode() + "'" for b in bodies]
    assert served == list(interactive_ui.KIT_SCRIPT_HASHES)
    assert "<script " not in interactive_ui.KIT_FRAME_HTML, "no external or typed scripts"
    assert '<div id="kit-root"></div>' in interactive_ui.KIT_FRAME_HTML
    assert interactive_ui.BASE_CSS in interactive_ui.KIT_FRAME_HTML


@pytest.mark.parametrize("tiles,origin", [
    ("https://tiles.example.nl/osm/{z}/{x}/{y}.png", "https://tiles.example.nl"),
    ({"url": "https://maps.example.com:8443/t/{z}/{x}/{y}.png", "attribution": "Eigen kaart"}, "https://maps.example.com:8443"),
    ("http://insecure.example/{z}/{x}/{y}.png", "https://tile.openstreetmap.org"),
    ("https://evil.example/{z}/{x}.png", "https://tile.openstreetmap.org"),
    ("https://a.example/{z}/{x}/{y}.png; script-src *", "https://tile.openstreetmap.org"),
])
def test_kit_frame_image_source_follows_the_tile_setting(tiles, origin, monkeypatch):
    monkeypatch.delenv("HERMES_WEBUI_MAP_TILES", raising=False)
    csp = _directives(interactive_ui.kit_frame_csp({"webui_map_tiles": tiles}))
    assert csp["img-src"].split() == ["data:", origin, "https://upload.wikimedia.org"]


def test_vendored_libraries_match_their_recorded_hashes():
    import hashlib
    for rel in ("chartjs/4.4.7", "leaflet/1.9.4"):
        folder = STATIC / "vendor" / rel
        recorded = dict(re.findall(r"\| `([^`]+)`[^|]*\| `([0-9a-f]{64})` \|", (folder / "VENDOR.md").read_text(encoding="utf-8")))
        assert recorded, rel
        for name, digest in recorded.items():
            assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest, name
    assert (STATIC / "vendor/chartjs/4.4.7/chart.umd.js").read_text(encoding="utf-8").startswith("/*!\n * Chart.js v4.4.7")
    assert "Leaflet 1.9.4" in (STATIC / "vendor/leaflet/1.9.4/leaflet.js").read_text(encoding="utf-8")[:200]


def test_routes_serve_the_kit_frame_and_the_map_endpoint():
    routes = (REPO / "api" / "routes.py").read_text(encoding="utf-8")
    kit = 'if parsed.path in ("/static/interactive-ui/kit.html", "/session/static/interactive-ui/kit.html"):'
    assert routes.count(kit) == 1
    assert routes.index(kit) < routes.index('if parsed.path.startswith("/session/static/"):')
    post = 'if parsed.path == "/api/map/resolve":'
    assert routes.count(post) == 1
    # After the CSRF gate, before the generic body reader.
    assert routes.index("if not _csrf_exempt_path(parsed.path) and not _check_csrf(handler):") < routes.index(post)
    assert routes.index(post) < routes.index("body = read_body(handler)", routes.index(post) - 5000)


def test_kit_assets_load_in_order():
    core = '<script src="static/interactive-ui/kit-core.js?v=__WEBUI_VERSION__" defer></script>'
    host_map = '<script src="static/interactive_ui_map.js?v=__WEBUI_VERSION__" defer></script>'
    assert INDEX.index(core) < INDEX.index("static/interactive_ui.js") < INDEX.index(host_map) < INDEX.index('src="static/ui.js')
    assert "'./static/interactive-ui/kit-core.js' + VQ" in SW and "'./static/interactive_ui_map.js' + VQ" in SW
    assert "iframe.setAttribute('sandbox','allow-scripts');" in MODULE
    assert "if(e.origin!=='null') return;" in MODULE


def test_data_prompt_appears_once_before_the_interactive_block(isolated_prompt):
    text = _prompt({})
    assert text.count("WebUI data blocks:") == 1
    assert interactive_ui.PROMPT_DATA in text
    assert text.index("WebUI data blocks:") < text.index(HEADER)
    assert "WebUI data blocks:" not in _prompt({"webui_interactive_ui": False})


def test_data_prompt_names_the_rules_within_its_budget():
    text = interactive_ui.PROMPT_DATA
    assert not re.search(LONG_DASHES, text)
    assert len(text.split()) <= 360
    for phrase in ("```table", "```chart", "```map", "```csv", "```kpi", "```timeline", "JSON numbers", "lat and lng only when a tool or the user supplied them",
                   "Never put travel times, distances or opening hours", "photos:true only for landmarks",
                   "At most one data block per reply", "takeaway"):
        assert phrase in text, phrase
    # The interactive-ui line now points data to these blocks.
    assert "a chart of real data" not in interactive_ui.PROMPT
    assert "calculator, what-if model or simulation" in interactive_ui.PROMPT
