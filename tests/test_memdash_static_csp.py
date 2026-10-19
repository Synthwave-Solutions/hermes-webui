"""The vendored Memory explorer is served with its own headers (addendum 6.6.4).

The document runs in an opaque origin (``sandbox allow-scripts`` without
``allow-same-origin``) with no network; scripts and styles are public MIT code
with ``Access-Control-Allow-Origin: *`` and never with credentials; no response
sets a cookie; only the pinned directory is served and every traversal
spelling, encoded included, answers 404.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures" / "memdash"))

import memdash_harness as H  # noqa: E402
from api import memdash_static  # noqa: E402

BASE = memdash_static.PREFIX + memdash_static.VERSION_DIR + "/"
ASSETS = ("app.js", "memdash-shim.js", "vendor/three.module.min.js", "style.css", "memdash-overrides.css")


def _get(path: str) -> H.Handler:
    handler = H.Handler()
    if memdash_static.serve(handler, H.parsed(path)) is False:
        handler.status = 404
    return handler


def _directives(csp: str) -> dict[str, str]:
    out = {}
    for part in csp.split(";"):
        words = part.strip().split(None, 1)
        if words:
            out[words[0]] = words[1] if len(words) > 1 else ""
    return out


def test_the_document_is_sandboxed_without_same_origin_and_without_network():
    response = _get(BASE + "index.html")
    assert response.status == 200
    assert response.header("Content-Type") == "text/html; charset=utf-8"
    csps = response.headers_named("Content-Security-Policy")
    assert len(csps) == 1
    csp = _directives(csps[0])
    assert csp["sandbox"] == "allow-scripts"
    assert "allow-same-origin" not in csps[0]
    assert csp["connect-src"] == "'none'"
    assert csp["frame-ancestors"] == "'self'"
    assert csp["base-uri"] == "'none'"
    assert csp["form-action"] == "'none'"
    assert csp["object-src"] == "'none'"
    assert csp["default-src"] == "'none'"
    assert csp["script-src"] == "'self'"
    assert csp["font-src"] == "'none'"
    for name in ("frame-src", "worker-src", "media-src", "manifest-src"):
        assert csp[name] == "'none'", name
    assert response.header("X-Content-Type-Options") == "nosniff"
    assert response.header("Referrer-Policy") == "no-referrer"
    assert response.header("X-Frame-Options") == "SAMEORIGIN"
    assert response.header("Cache-Control") == "no-cache"
    policy = response.header("Permissions-Policy")
    assert policy and all(item.strip().endswith("=()") for item in policy.split(","))
    for feature in ("camera", "microphone", "geolocation", "clipboard-read", "payment", "usb"):
        assert f"{feature}=()" in policy
    assert response.header("Access-Control-Allow-Origin") is None
    assert response.header("Set-Cookie") is None
    assert int(response.header("Content-Length")) == len(response.raw)


@pytest.mark.parametrize("name", ASSETS)
def test_scripts_and_styles_are_public_cors_assets_without_credentials_or_cookies(name):
    response = _get(BASE + name)
    assert response.status == 200, name
    expected = "text/javascript; charset=utf-8" if name.endswith(".js") else "text/css; charset=utf-8"
    assert response.header("Content-Type") == expected
    assert response.header("Access-Control-Allow-Origin") == "*"
    assert response.header("Access-Control-Allow-Credentials") is None
    assert response.header("Cross-Origin-Resource-Policy") == "cross-origin"
    assert "immutable" in response.header("Cache-Control")
    assert response.header("X-Content-Type-Options") == "nosniff"
    assert response.header("Set-Cookie") is None
    assert response.raw == (memdash_static.root() / name).read_bytes()


@pytest.mark.parametrize("name", ("LICENSE", "VENDOR.md", "favicon.svg"))
def test_other_files_are_sandboxed_and_not_shared_across_origins(name):
    response = _get(BASE + name)
    assert response.status == 200
    assert "sandbox" in response.header("Content-Security-Policy")
    assert response.header("Access-Control-Allow-Origin") is None
    assert response.header("Set-Cookie") is None


@pytest.mark.parametrize("path", [
    BASE + "../0.14.0-a918e5e/index.html",
    BASE + "vendor/../index.html",
    BASE + "./index.html",
    BASE + ".//index.html",
    BASE + "%2e%2e/%2e%2e/%2e%2e/api/memdash.py",
    BASE + "..%2f..%2f..%2fapi%2fmemdash.py",
    BASE + "%252e%252e/index.html",
    BASE + "index%2ehtml",
    BASE + "%69ndex.html",
    BASE + "..\\..\\api\\memdash.py",
    BASE + "index.html\x00.js",
    BASE + "vendor//three.module.min.js",
    BASE + "vendor/",
    BASE,
    memdash_static.PREFIX,
    memdash_static.PREFIX + "index.html",
    memdash_static.PREFIX + "0.13.0-other/index.html",
    memdash_static.PREFIX + "0.14.0-a918e5e",
    BASE + "README.md",
    BASE + "server.py",
    BASE + "config.py",
    BASE + "fonts/inter.woff2",
    "/static/vendor/mnemosyne-dashboard/../../memory_dashboard.js",
])
def test_traversal_and_unlisted_files_answer_404(path):
    assert _get(path).status == 404


def test_path_parameters_are_refused():
    handler = H.Handler()
    assert memdash_static.serve(handler, H.parsed(BASE + "index.html;x=1")) is False
    assert memdash_static.serve(handler, None) is False
    assert handler.status is None


def test_only_the_pinned_directory_is_served(tmp_path, monkeypatch):
    # A symlink inside a copy of the pinned directory that points outside it
    # is never followed, even for a listed name.
    pinned = tmp_path / "pinned"
    pinned.mkdir()
    (pinned / "index.html").write_text("<p>ok</p>", encoding="utf-8")
    (tmp_path / "secret.js").write_text("secret", encoding="utf-8")
    (pinned / "app.js").symlink_to(tmp_path / "secret.js")
    monkeypatch.setattr(memdash_static, "root", lambda: pinned)
    memdash_static._CACHE.clear()
    try:
        assert _get(BASE + "index.html").status == 200
        assert _get(BASE + "app.js").status == 404
    finally:
        memdash_static._CACHE.clear()


def test_the_routes_seam_serves_the_document_with_its_csp_and_refuses_the_rest(monkeypatch):
    """``api/routes.py`` hands the vendored prefix to this module (E.7.5.1)."""
    import api.routes as routes

    generic = []
    monkeypatch.setattr(routes, "_serve_static", lambda handler, parsed: generic.append(parsed.path) or True)
    handler = H.Handler()
    routes._serve_memdash_vendor(handler, H.parsed(BASE + "index.html"))
    assert handler.status == 200
    assert "sandbox allow-scripts" in handler.header("Content-Security-Policy")
    assert handler.header("Set-Cookie") is None
    handler = H.Handler()
    routes._serve_memdash_vendor(handler, H.parsed(BASE + "%2e%2e/secret"))
    assert handler.status == 404
    assert generic == []


def test_the_served_document_loads_the_shim_before_the_app_and_only_relative_urls():
    html = _get(BASE + "index.html").raw.decode("utf-8")
    scripts = re.findall(r'<script src="([^"]+)"(?: crossorigin="anonymous")?></script>', html)
    assert [s.split("?")[0] for s in scripts] == ["memdash-shim.js", "app.js"]
    assert "/static/" not in html and 'src="/' not in html and 'href="/' not in html
