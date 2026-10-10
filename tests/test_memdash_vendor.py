"""The vendored Memory explorer app is pinned, rebuilt reproducibly and clean.

Plan addendum 6.6.4 and 6.6.10: hash pins for every upstream file; the
served ``index.html`` and ``app.js`` are byte-identical to a rebuild from the
pristine copies; ``LICENSE`` and ``VENDOR.md`` are present; the served HTML,
JS and CSS reference no absolute ``/api/`` or ``/static/`` URL and no other
host; no fonts; the vendored Python has no listener and no configuration
route; upstream ``server.py``, ``config.py`` and the plugin tools are absent.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SERVED = REPO / "static" / "vendor" / "mnemosyne-dashboard" / "0.14.0-a918e5e"
PRISTINE = REPO / "tests" / "fixtures" / "memdash_upstream" / "a918e5e"
CORE = REPO / "api" / "third_party" / "mnemosyne_dashboard"

PINS = {
    PRISTINE / "index.html": "e0960c649d97db0e78c0aec1f8300086a650d2e653baaaa6e94d3a4e004820b5",
    PRISTINE / "app.js": "6be2877b01619d8f10f086a791e54a4d1897ae6ea2544291191eaa681e969dbb",
    SERVED / "style.css": "db7f345589a048b6a11e6a92db3b0e6861cd95725887b5bce5ab5642c58f5db8",
    SERVED / "vendor" / "three.module.min.js": "3e690ac7d180b0aadf0891bea39eec643e29e2d3e75c99b18689518665f69ba6",
    SERVED / "favicon.svg": "2dbcbd5abf1b70bcfcaec92f641f40c7fad0da3112515ca6d8397fb1c248e4eb",
    SERVED / "LICENSE": "d89209ee7aa7ceae54947726a9ab95d0e2fb679e975c52490394c2bf3e8c1f87",
    CORE / "LICENSE": "d89209ee7aa7ceae54947726a9ab95d0e2fb679e975c52490394c2bf3e8c1f87",
    CORE / "dashboard_core.py": "836cd334bf7f26b45e886c92c60362092163ba0211cb0df553ba8d43c7e871b7",
}
SERVED_TEXT = ("index.html", "app.js", "memdash-shim.js", "style.css", "memdash-overrides.css", "vendor/three.module.min.js")
DASHES = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")
DENYLIST = re.compile(r"mnemosyne|mnemo-hub|hermes|memoria|omniroute|langgraph|litellm|n8n", re.IGNORECASE)


def _load_vendor_script():
    spec = importlib.util.spec_from_file_location("memdash_vendor", REPO / "scripts" / "memdash_vendor.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("path, digest", PINS.items(), ids=lambda v: str(v)[-40:])
def test_upstream_files_match_their_sha256_pins(path, digest):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_served_files_are_a_byte_identical_rebuild_of_the_pristine_copies():
    vendor = _load_vendor_script()
    built = vendor.build()
    assert built["index.html"] == (SERVED / "index.html").read_bytes()
    assert built["app.js"] == (SERVED / "app.js").read_bytes()
    assert vendor.check() == []
    # The check mode of the script is the same gate, as a command.
    completed = subprocess.run([sys.executable, str(REPO / "scripts" / "memdash_vendor.py"), "--check"],
                               capture_output=True, text=True, timeout=60)
    assert completed.returncode == 0, completed.stderr


def test_a_rewrite_rule_with_a_drifted_count_fails_loudly():
    vendor = _load_vendor_script()
    with pytest.raises(vendor.VendorError, match="matched 0 times, pinned 1"):
        vendor.apply_rules("nothing here", (("needle", "x", 1),), "probe")


def test_licence_and_vendor_notes_are_present():
    assert "Permission is hereby granted" in (SERVED / "LICENSE").read_text()
    notes = (SERVED / "VENDOR.md").read_text()
    assert "a918e5e0841fdc85baad7ab582432b2b7499b2f2" in notes
    assert "https://github.com/wysie/mnemosyne-dashboard" in notes
    assert "Copyright 2010-2023 Three.js Authors" in notes
    for name in ("server.py", "config.py", "brand-fonts.css"):
        assert name in notes  # listed under the files not taken


def test_only_the_expected_files_are_vendored():
    files = sorted(str(p.relative_to(SERVED)) for p in SERVED.rglob("*") if p.is_file())
    assert files == sorted([
        "LICENSE", "VENDOR.md", "app.js", "favicon.svg", "index.html", "memdash-overrides.css",
        "memdash-shim.js", "style.css", "vendor/three.module.min.js",
    ])
    assert sorted(p.name for p in CORE.iterdir() if p.is_file()) == ["LICENSE", "__init__.py", "dashboard_core.py", "patches.py"]
    for forbidden in ("server.py", "config.py", "plugin.yaml", "brand-fonts.css"):
        assert not (CORE / forbidden).exists() and not (SERVED / forbidden).exists(), forbidden
    assert not any(p.suffix in {".woff", ".woff2", ".ttf", ".otf"} for p in SERVED.rglob("*"))


def test_served_markup_scripts_and_styles_reference_no_absolute_path_and_no_other_host():
    for name in SERVED_TEXT:
        text = (SERVED / name).read_text(encoding="utf-8")
        assert "/static/" not in text, name
        urls = set(re.findall(r"https?://[^\s\"'`)<>]+", text))
        allowed = {u for u in urls if u.startswith("http://www.w3.org/")}
        if name == "vendor/three.module.min.js":
            # A documentation link inside a warning string of the unmodified,
            # pinned three.js build; it is never requested.
            allowed |= {u for u in urls if u.startswith("https://discourse.threejs.org/")}
        assert urls <= allowed, (name, urls - allowed)
        if name in ("index.html", "style.css", "memdash-overrides.css"):
            assert "/api/" not in text, name
    # In app.js the /api/ paths are only the app's own calls, which the shim
    # answers through the WebUI panel; never a URL the browser resolves.
    for lineno, line in enumerate((SERVED / "app.js").read_text(encoding="utf-8").splitlines(), 1):
        if "/api/" in line:
            assert re.search(r"\b(api|fetch|postJson|EventSource|loadMemoriaTable)\(", line), (lineno, line[:120])


def test_no_fonts_and_no_font_links():
    index = (SERVED / "index.html").read_text(encoding="utf-8")
    assert "brand-fonts" not in index and "favicon" not in index
    for name in ("style.css", "memdash-overrides.css"):
        css = (SERVED / name).read_text(encoding="utf-8")
        assert "@font-face" not in css and "@import" not in css, name


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text: list[str] = []
        self.attrs: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        for name, value in attrs:
            if name in ("title", "placeholder", "aria-label", "alt") and value:
                self.attrs.append(value)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.text.append(data.strip())


def test_served_document_text_holds_no_denylisted_name_and_no_dash():
    parser = _Text()
    parser.feed((SERVED / "index.html").read_text(encoding="utf-8"))
    visible = parser.text + parser.attrs
    assert not [t for t in visible if DENYLIST.search(t)]
    for name in ("index.html", "app.js", "memdash-shim.js", "memdash-overrides.css", "VENDOR.md"):
        assert not DASHES.search((SERVED / name).read_text(encoding="utf-8")), name


def test_app_rewrites_are_applied():
    app = (SERVED / "app.js").read_text(encoding="utf-8")
    assert "localStorage" not in app and app.count("__mdStore") == 4
    assert "import('./vendor/three.module.min.js')" in app
    assert "mnemosyne_triple_add" not in app and "Mnemosyne" not in app
    assert "Backups and audit entries will be created." not in app
    assert "'Expire" not in app and "Forget selected" in app
    index = (SERVED / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<script src="memdash-shim\.js\?v=[0-9a-f]{12}"></script><script src="app\.js\?v=[0-9a-f]{12}"></script>', index)
    assert index.index('href="style.css') < index.index('href="memdash-overrides.css')
    assert "<a " not in index.split('<footer class="app-footer">', 1)[1].split("</footer>", 1)[0]


def _python_sources():
    paths = [CORE / "dashboard_core.py", CORE / "patches.py", CORE / "__init__.py",
             REPO / "api" / "memdash_reader.py", REPO / "api" / "memdash_backend.py"]
    return [p for p in paths if p.exists() or p.parent == CORE]


def test_vendored_python_has_no_listener_and_no_config_route():
    for path in _python_sources():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imported |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert "socket" not in imported and "socketserver" not in imported, path
        assert "http" not in imported or path.name == "memdash_backend.py", path
        for token in ("serve_forever", "ThreadingHTTPServer", "0.0.0.0", "/api/config"):
            assert token not in source, (path, token)


def test_patched_store_refuses_writes_defaults_and_unlisted_paths(tmp_path):
    from api.third_party import mnemosyne_dashboard as md

    with pytest.raises(PermissionError):
        md.DashboardStore()
    with pytest.raises(PermissionError):
        md.dashboard_core.default_db_path()
    with pytest.raises(PermissionError):
        md.dashboard_core.plugin_data_dir()
    db = tmp_path / "store.db"
    import sqlite3
    sqlite3.connect(db).close()
    md.allow_paths([])
    store = md.DashboardStore(db)
    with pytest.raises(PermissionError):
        store.connect()
    for name in ("connect_rw", "backup_database", "audit_log", "diagnostics", "realtime_status"):
        with pytest.raises(PermissionError):
            getattr(store, name)()
    for name in ("invalidate_memory", "set_memory_importance", "set_memory_veracity", "set_memory_expiry", "supersede_memory"):
        with pytest.raises(PermissionError):
            getattr(store, name)("id", "x")
    # The search pattern is anchored (linear) and still matches whole words.
    pattern = md.DashboardStore._prefix_pattern("alpha beta")
    assert pattern.startswith(r"(?s)\A")
    assert re.search(pattern, "x beta\nand alpha y", flags=re.IGNORECASE)
    assert not re.search(pattern, "alphabet only", flags=re.IGNORECASE)
    assert md.DashboardStore._pattern_origin_label("hermes_chat") == "Assistant"
