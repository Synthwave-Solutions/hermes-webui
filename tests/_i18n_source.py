"""The monolithic ``static/i18n.js`` source, rebuilt from the split layout.

SynthPulse moved every locale out of ``static/i18n.js`` into demand-loaded
bundles (``static/i18n/<code>.js``); the loader keeps only metadata and the
helpers. Upstream tests read ``static/i18n.js`` and expect each locale inline,
as ``const LOCALES = {\\n  en: {\\n    key: ...,\\n  },\\n\\n  it: {...}``. This
module returns that shape, built from the loader plus the bundles, so those
tests keep checking the real translations.

The rebuilt source is also executable: the loader's metadata-only ``LOCALES``
is replaced by the full literal, so every locale is present without loading
scripts, and the loader's browser globals are guarded for the node ``vm``
contexts some tests use.
"""

from __future__ import annotations

import re
import tempfile
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_IDENT = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
# The one comment upstream kept between locale blocks.
_BLOCK_PREFIX = {"zh-Hant": "  // Traditional Chinese (zh-Hant)\n"}


def _locale_codes(loader: str) -> list[str]:
    start = loader.index("const _I18N_LOCALE_META = {")
    end = loader.index("};", start)
    return [a or b for a, b in re.findall(r"(?:'([A-Za-z-]+)'|([A-Za-z-]+)):\[", loader[start:end])]


def _bundle_body(text: str, code: str) -> str:
    opener = f"window.__registerHermesLocale('{code}', {{\n"
    start = text.index(opener) + len(opener)
    end = re.search(r"\n[ \t]*\}\);\s*\Z", text).start()
    return text[start:end].rstrip("\n")


@lru_cache(maxsize=None)
def monolithic_i18n_source(root: str | None = None) -> str:
    base = Path(root) if root else ROOT
    loader = (base / "static" / "i18n.js").read_text(encoding="utf-8").lstrip("﻿")
    blocks = []
    for code in _locale_codes(loader):
        bundle = (base / "static" / "i18n" / f"{code}.js").read_text(encoding="utf-8")
        key = code if _IDENT.match(code) else f"'{code}'"
        blocks.append(_BLOCK_PREFIX.get(code, "") + f"  {key}: {{\n{_bundle_body(bundle, code)}\n  }},")
    literal = "const LOCALES = {\n" + "\n\n".join(blocks) + "\n};\n"
    # Upstream declared LOCALES first, before any helper; tests that look for
    # the first `en:` rely on that, so the literal goes right after the header
    # comment and the loader's metadata-only LOCALES statement is dropped.
    start = loader.index("const LOCALES = Object.fromEntries(")
    end = loader.index("]));", start) + len("]));")
    loader = loader[:start] + loader[end:].lstrip("\n")
    header_end = 0
    for line in loader.splitlines(keepends=True):
        if not line.startswith("//"):
            break
        header_end += len(line)
    src = loader[:header_end] + "\n" + literal + "\n" + loader[header_end:]
    globals_ = "(typeof window!=='undefined'?window:globalThis)"
    src = src.replace("window.__registerHermesLocale=", f"{globals_}.__registerHermesLocale=")
    src = src.replace("window.i18nReady=", f"{globals_}.i18nReady=")
    src = src.replace("(document.currentScript&&", "(typeof document!=='undefined'&&document.currentScript&&")
    return src


@lru_cache(maxsize=None)
def monolithic_i18n_path(root: str | None = None) -> str:
    """Path of a temporary file holding :func:`monolithic_i18n_source`, for
    tests that hand the file to node."""
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix="-i18n.js", prefix="monolithic-", delete=False
    )
    with handle:
        handle.write(monolithic_i18n_source(root))
    return handle.name


def monolithic_i18n_file(root: str | None = None) -> Path:
    """:func:`monolithic_i18n_path` as a :class:`~pathlib.Path`."""
    return Path(monolithic_i18n_path(root))
