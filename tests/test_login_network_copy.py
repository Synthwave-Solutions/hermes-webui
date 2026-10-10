"""The login page's network error names no network product (PLAN 3.10, N3).

When the health probe cannot reach the server, the login page used to tell
every installation to check its Tailscale connection. The copy is now
provider-neutral and has no dash, so it is right on any mesh, on a client VPN
and on the public internet.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGIN_JS = (ROOT / "static" / "login.js").read_text(encoding="utf-8")
NETWORK_ERROR = "Cannot reach the server. Check your network or VPN connection."
NETWORK_PRODUCTS = ("Tailscale", "tailnet", "Funnel", "NetBird", "WireGuard", "Headscale", "ZeroTier")
DASHES = ("\u2013", "\u2014")


def _strip_comments(src: str) -> str:
    """Drop // and /* */ comments outside string literals (enough for login.js)."""
    out, i, n = [], 0, len(src)
    quote = None
    while i < n:
        c = src[i]
        if quote:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"`":
            quote = c
            out.append(c)
            i += 1
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _string_literals(src: str) -> list[str]:
    code = _strip_comments(src)
    return [m.group(2) for m in re.finditer(r"(['\"`])((?:\\.|(?!\1).)*)\1", code, re.S)]


def test_network_error_uses_the_neutral_literal():
    assert "showErr('" + NETWORK_ERROR + "');" in LOGIN_JS
    assert "Tailscale connection" not in LOGIN_JS
    assert "Cannot reach server" not in LOGIN_JS


def test_the_neutral_literal_has_no_product_and_no_dash():
    assert not any(p.lower() in NETWORK_ERROR.lower() for p in NETWORK_PRODUCTS)
    assert not any(d in NETWORK_ERROR for d in DASHES)


def test_no_login_copy_names_a_network_product_or_holds_a_dash():
    literals = _string_literals(LOGIN_JS)
    assert NETWORK_ERROR in literals
    offenders = [s for s in literals
                 if any(p.lower() in s.lower() for p in NETWORK_PRODUCTS) or any(d in s for d in DASHES)]
    assert offenders == []


def test_the_literal_extractor_sees_through_comments():
    sample = "/* 'Tailscale' \u2014 */ var a = 'x'; // 'NetBird'\nshowErr(\"y \\\" z\");"
    assert _string_literals(sample) == ["x", 'y \\" z']
