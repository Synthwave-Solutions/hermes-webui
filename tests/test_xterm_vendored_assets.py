"""The terminal can initialize without access to third-party asset hosts."""
import base64
import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {
    "xterm/5.3.0/lib/xterm.js": "/nfmYPUzWMS6v2atn8hbljz7NE0EI1iGx34lJaNzyVjWGDzMv+ciUZUeJpKA3Glc",
    "xterm/5.3.0/css/xterm.css": "LJcOxlx9IMbNXDqJ2axpfEQKkAYbFjJfhXexLfiRJhjDU81mzgkiQq8rkV0j6dVh",
    "xterm-addon-fit/0.8.0/lib/xterm-addon-fit.js": "AQLWHRKAgdTxkolJcLOELg4E9rE89CPE2xMy3tIRFn08NcGKPTsELdvKomqji+DL",
    "xterm-addon-web-links/0.9.0/lib/xterm-addon-web-links.js": "U4fBROT3kCM582gaYiNaOSQiJbXPzd9SfR1598Y7yeGSYVBzikXrNg0XyuU+mOnl",
}


@pytest.mark.parametrize("asset, expected_sri", ASSETS.items())
def test_vendored_distribution_matches_existing_browser_integrity_pin(asset, expected_sri):
    body = (ROOT / "static/vendor" / asset).read_bytes()
    assert base64.b64encode(hashlib.sha384(body).digest()).decode() == expected_sri
    package = ROOT / "static/vendor" / "/".join(asset.split("/")[:2])
    assert "Permission is hereby granted" in (package / "LICENSE").read_text()
    assert "https://registry.npmjs.org/" in (package / "VENDOR.md").read_text()


def test_terminal_loader_uses_base_relative_local_assets_with_integrity():
    source = (ROOT / "static/terminal.js").read_text()
    assert "cdn.jsdelivr.net" not in source
    for asset, digest in ASSETS.items():
        # A leading slash would bypass the app's documented mounted base path.
        assert "'static/vendor/" + asset + "'" in source
        assert "sha384-" + digest in source
