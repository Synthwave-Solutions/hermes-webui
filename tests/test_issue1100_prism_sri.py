"""Tests for #1100 — Prism.js SRI integrity check no longer blocks theme CSS.

SynthPulse loads Prism lazily on the first code block (ensurePrism in
static/ui.js) instead of from static/index.html. The same guarantees are
checked wherever the assets are declared.
"""
import re


def _index_prism_link():
    with open("static/index.html") as f:
        return re.search(r'<link[^>]*id="prism-theme"[^>]*>', f.read())


def _lazy_prism_loader():
    with open("static/ui.js") as f:
        src = f.read()
    start = src.find("function ensurePrism(")
    assert start != -1, "Prism must be declared in index.html or loaded by ensurePrism()"
    end = src.find("\nfunction ", start + 1)
    return src[start:end]


def test_prism_theme_link_has_no_integrity():
    """The prism-tomorrow.min.css link must not have an integrity attribute."""
    m = _index_prism_link()
    if m is None:
        loader = _lazy_prism_loader()
        assert "link.id='prism-theme'" in loader, "prism-theme link must exist"
        assert "integrity" not in loader.split("_prismLoadPromise=")[0], \
            "prism-theme link must not have integrity attribute (causes intermittent failures)"
        return
    link_tag = m.group(0)
    assert "integrity=" not in link_tag, \
        "prism-theme link must not have integrity attribute (causes intermittent failures)"


def test_prism_theme_link_has_crossorigin():
    """The prism-theme link should still have crossorigin for CORS."""
    m = _index_prism_link()
    if m is None:
        loader = _lazy_prism_loader()
        assert "link.id='prism-theme'" in loader, "prism-theme link must exist"
        assert "link.crossOrigin='anonymous'" in loader, \
            "prism-theme link should still have crossorigin attribute"
        return
    link_tag = m.group(0)
    assert "crossorigin" in link_tag, \
        "prism-theme link should still have crossorigin attribute"


def test_prism_theme_version_pinned():
    """The prism CSS URL must pin the version to prevent breaking changes."""
    with open("static/index.html") as f:
        src = f.read()
    m = re.search(
        r'<link[^>]*id="prism-theme"[^>]*href="([^"]*)"[^>]*>',
        src
    )
    if m is None:
        loader = _lazy_prism_loader()
        hrefs = re.findall(r"https://cdn\.jsdelivr\.net/npm/prismjs[^'\"]*/themes/[^'\"]+", loader)
        assert hrefs, "prism-theme link must have href"
        for href in hrefs:
            assert "@1.29.0" in href, f"Prism CSS version must be pinned, found href: {href}"
        # The lazy link must follow the current theme, like _setResolvedTheme.
        assert "classList.contains('dark')" in loader
        assert any(h.endswith("prism.min.css") for h in hrefs)
        assert any(h.endswith("prism-tomorrow.min.css") for h in hrefs)
        return
    href = m.group(1)
    assert "@1.29.0" in href, \
        f"Prism CSS version must be pinned, found href: {href}"


def test_prism_js_still_has_integrity():
    """Prism JS files should keep SRI — they are less affected by CDN edge issues."""
    with open("static/index.html") as f:
        src = f.read()
    if "prism-core.min.js" not in src:
        # Lazy loader: each script is loaded with its sha384 SRI hash.
        src = _lazy_prism_loader()
        assert re.search(r"prism-core\.min\.js'\s*,\s*'sha384-", src), \
            "prism-core.min.js should still have integrity attribute"
        assert re.search(r"prism-autoloader\.min\.js'\s*,\s*'sha384-", src), \
            "prism-autoloader.min.js should still have integrity attribute"
        return
    # prism-core.min.js
    assert re.search(r'prism-core\.min\.js[^>]*integrity=', src), \
        "prism-core.min.js should still have integrity attribute"
    # prism-autoloader.min.js
    assert re.search(r'prism-autoloader\.min\.js[^>]*integrity=', src), \
        "prism-autoloader.min.js should still have integrity attribute"


def test_boot_js_set_resolved_theme_no_integrity():
    """_setResolvedTheme in boot.js must not re-apply integrity on theme switch."""
    with open("static/boot.js") as f:
        src = f.read()
    # _setResolvedTheme function must exist
    assert "_setResolvedTheme" in src, "_setResolvedTheme function must exist"
    # Must NOT assign link.integrity with a hash value
    assert not re.search(r'link\.integrity\s*=\s*["\']sha', src), \
        "_setResolvedTheme must not set link.integrity to an SRI hash"
    # Must NOT have a wantIntegrity variable
    assert "wantIntegrity" not in src, \
        "wantIntegrity variable should be removed from _setResolvedTheme"
    # Should clear integrity (set to empty) when switching theme
    assert re.search(r"link\.integrity\s*=\s*['\"]", src), \
        "_setResolvedTheme should clear link.integrity on theme switch"
