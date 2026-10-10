#!/usr/bin/env python3
"""Rebuild the vendored Memory explorer from the pinned upstream files.

Plan addendum 6.6.4. The single-page app of ``wysie/mnemosyne-dashboard`` at
a918e5e0841fdc85baad7ab582432b2b7499b2f2 (v0.14.0, MIT) is served by the WebUI
from ``static/vendor/mnemosyne-dashboard/0.14.0-a918e5e/``. Two of its files
are rewritten, from the pristine copies in
``tests/fixtures/memdash_upstream/a918e5e/``, by the rewrite table below:

* ``index.html``: no font or icon links, relative asset URLs with a content
  hash, our shim before ``app.js``, no footer credit links, neutral copy;
* ``app.js``: ``localStorage`` becomes the in-memory ``__mdStore``, the
  three.js import is relative, and the visible strings that name internal
  components or promise backups become neutral.

Every rule is an exact string with a pinned match count, so an upstream pin
bump fails loudly and needs a reviewed diff. ``fetch`` and ``EventSource`` stay
untouched in ``app.js``: ``memdash-shim.js`` turns every ``/api/`` call into a
message to the WebUI panel and removes ``EventSource``.

Usage::

    python3 scripts/memdash_vendor.py            # write index.html and app.js
    python3 scripts/memdash_vendor.py --check    # exit 1 on any drift
    python3 scripts/memdash_vendor.py --upstream DIR
        # refresh the pristine and unmodified copies from an upstream checkout
        # after checking every sha256 pin (a pin bump edits PINS first)
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
UPSTREAM_SHA = "a918e5e0841fdc85baad7ab582432b2b7499b2f2"
VERSION_DIR = "0.14.0-a918e5e"
PRISTINE = REPO / "tests" / "fixtures" / "memdash_upstream" / "a918e5e"
SERVED = REPO / "static" / "vendor" / "mnemosyne-dashboard" / VERSION_DIR
CORE = REPO / "api" / "third_party" / "mnemosyne_dashboard"

# sha256 of every upstream file taken (plan addendum 6.6.4, favicon added).
PINS = {
    "index.html": "e0960c649d97db0e78c0aec1f8300086a650d2e653baaaa6e94d3a4e004820b5",
    "app.js": "6be2877b01619d8f10f086a791e54a4d1897ae6ea2544291191eaa681e969dbb",
    "style.css": "db7f345589a048b6a11e6a92db3b0e6861cd95725887b5bce5ab5642c58f5db8",
    "favicon.svg": "2dbcbd5abf1b70bcfcaec92f641f40c7fad0da3112515ca6d8397fb1c248e4eb",
    "vendor/three.module.min.js": "3e690ac7d180b0aadf0891bea39eec643e29e2d3e75c99b18689518665f69ba6",
    "LICENSE": "d89209ee7aa7ceae54947726a9ab95d0e2fb679e975c52490394c2bf3e8c1f87",
    "dashboard_core.py": "836cd334bf7f26b45e886c92c60362092163ba0211cb0df553ba8d43c7e871b7",
}

# Where each upstream file lives here (relative to the repo root).
PRISTINE_FILES = {
    "index.html": PRISTINE / "index.html",
    "app.js": PRISTINE / "app.js",
}
UNMODIFIED_FILES = {
    "style.css": SERVED / "style.css",
    "favicon.svg": SERVED / "favicon.svg",
    "vendor/three.module.min.js": SERVED / "vendor" / "three.module.min.js",
    "LICENSE": SERVED / "LICENSE",
    "dashboard_core.py": CORE / "dashboard_core.py",
}
# Where each file comes from in an upstream checkout.
UPSTREAM_PATHS = {
    "index.html": "static/index.html",
    "app.js": "static/app.js",
    "style.css": "static/style.css",
    "favicon.svg": "static/favicon.svg",
    "vendor/three.module.min.js": "static/vendor/three.module.min.js",
    "LICENSE": "LICENSE",
    "dashboard_core.py": "dashboard_core.py",
}
# Our own files next to the vendored ones; the generated index.html carries
# their content hashes, so it must be rebuilt when they change.
OWN_FILES = ("memdash-shim.js", "memdash-overrides.css", "VENDOR.md")
# Files the static route serves (api/memdash_static.py keeps the same list).
SERVED_FILES = (
    "index.html", "app.js", "style.css", "favicon.svg", "vendor/three.module.min.js",
    "memdash-shim.js", "memdash-overrides.css", "LICENSE", "VENDOR.md",
)

FOOTER_OLD = (
    '      <footer class="app-footer">\n'
    '        Built by <a href="https://github.com/wysie" target="_blank" rel="noopener noreferrer">wysie</a>'
    ' with <a href="https://github.com/NousResearch/hermes-agent" target="_blank" rel="noopener noreferrer">Hermes Agent</a>'
    ' · Thanks to <a href="https://github.com/AxDSan" target="_blank" rel="noopener noreferrer">AxDSan</a>'
    ' for creating <a href="https://github.com/AxDSan/mnemosyne" target="_blank" rel="noopener noreferrer">Mnemosyne</a>\n'
    '      </footer>\n'
)

# (old, new, pinned number of matches before the replacement). "{name}"
# placeholders in ``new`` are filled with content hashes after the table ran.
INDEX_RULES: tuple[tuple[str, str, int], ...] = (
    ("<title>Mnemosyne Dashboard</title>", "<title>Memory explorer</title>", 1),
    ('  <link rel="icon" href="/static/favicon.svg" type="image/svg+xml" />\n', "", 1),
    ('  <link rel="stylesheet" href="/static/brand-fonts.css" />\n', "", 1),
    (
        '<link rel="stylesheet" href="/static/style.css?v=stream-v2" />',
        '<link rel="stylesheet" href="style.css?v={style.css}" />\n'
        '  <link rel="stylesheet" href="memdash-overrides.css?v={memdash-overrides.css}" />',
        1,
    ),
    (
        '<script src="/static/app.js?v=stream-v2"></script>',
        '<script src="memdash-shim.js?v={memdash-shim.js}"></script>'
        '<script src="app.js?v={app.js}"></script>',
        1,
    ),
    (FOOTER_OLD, '      <footer class="app-footer"></footer>\n', 1),
    ('<div class="brand-name">Mnemosyne</div>', '<div class="brand-name">Memory</div>', 3),
    ('<div class="brand-sub">Hermes Memory</div>', '<div class="brand-sub">Explorer</div>', 3),
    ("Mnemosyne Labyrinth", "Memory Labyrinth", 4),
    ('<span>MR</span>MEMORIA</button>', '<span>SM</span>Structured memory</button>', 1),
    ("<h2>MEMORIA</h2>", "<h2>Structured memory</h2>", 1),
    ("<h2>MEMORIA ", "<h2>", 5),
    ('<div class="eyebrow">Hermes memory console</div>', '<div class="eyebrow">Memory explorer</div>', 1),
    ("Powered by Mnemosyne PatternDetector", "Pattern detector", 1),
    ("which Mnemosyne SQLite database it reads", "which memory database it reads", 1),
    ('placeholder="~/.hermes/mnemosyne/data/mnemosyne.db"', 'placeholder="memory.db"', 1),
    ("the configured Mnemosyne SQLite database", "the configured memory database", 1),
    ("Mnemosyne 3.x sync diagnostics", "Sync diagnostics", 1),
    ("read-only Mnemosyne streaming", "read-only memory streaming", 1),
    ('>Expire selected</button>', '>Forget selected</button>', 2),
    # No em or en dash in served text (plan 0.4 rule 7).
    ("triage selected memories \u2014 confirm, correct, or expire only what you choose",
     "triage selected memories: confirm, correct, or forget only what you choose", 1),
    ("importance edits only \u2014 no lifecycle-tier edits", "importance edits only, no lifecycle-tier edits", 1),
)

APP_RULES: tuple[tuple[str, str, int], ...] = (
    ("localStorage", "__mdStore", 4),
    ("import('/static/vendor/three.module.min.js')", "import('./vendor/three.module.min.js')", 1),
    ("['Provider', data.provider ? 'Mnemosyne' : 'Dashboard']",
     "['Provider', data.provider ? 'Pattern detector' : 'Dashboard']", 1),
    ("No triples match this graph filter. Add facts with mnemosyne_triple_add or mnemosyne_remember(... extract=true).",
     "No connections match this graph filter.", 1),
    ("Mnemosyne Labyrinth", "Memory Labyrinth", 4),
    ("title:'Expire selected memories?'", "title:'Forget selected memories?'", 2),
    ("`Expire ${ids.length} selected active memories. Backups and audit entries will be created.`",
     "`Forget ${ids.length} selected active memories. This is recorded.`", 2),
    ("confirmText:'Expire selected'", "confirmText:'Forget selected'", 2),
    (">Expire now</button>", ">Forget now</button>", 1),
    ("title: 'Expire this memory?',", "title: 'Forget this memory?',", 1),
    ("confirmText: 'Expire memory',", "confirmText: 'Forget memory',", 1),
    ("`Expired. Backup: ${r.backup?.path || 'not created'}`", "'Forgotten.'", 1),
    ("Expire now remains the safer one-click option", "Forget now remains the safer one-click option", 1),
    ("'<span class=\"muted\">Enable Settings → Memory maintenance to modify memories.</span>'",
     "'<span class=\"muted\">You can view these memories but not change them.</span>'", 1),
    # No em or en dash in served text (plan 0.4 rule 7).
    ("value === '' ? '\u2014' : value;", "value === '' ? 'n/a' : value;", 1),
    ("'yes \u2014 repaired on restart/start'", "'yes, repaired on restart/start'", 1),
    ("</strong> \u2014 ${esc(t.predicate)}", "</strong> \u00b7 ${esc(t.predicate)}", 2),
    ("`Current access URLs \u2014 ${", "`Current access URLs: ${", 1),
    ("'walk forward \u2014 memories are grouped by domain'", "'walk forward, memories are grouped by domain'", 2),
    ("// Common hidden/internal fields \u2014 never shown", "// Common hidden/internal fields, never shown", 1),
    ("Number(item.confidence).toFixed(2) : '\u2014';", "Number(item.confidence).toFixed(2) : 'n/a';", 1),
)


class VendorError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def short_hash(data: bytes) -> str:
    return sha256_bytes(data)[:12]


def apply_rules(text: str, rules, label: str) -> str:
    for old, new, expected in rules:
        found = text.count(old)
        if found != expected:
            raise VendorError(f"{label}: rule {old[:60]!r} matched {found} times, pinned {expected}")
        text = text.replace(old, new)
    return text


def _pristine(name: str) -> bytes:
    data = PRISTINE_FILES[name].read_bytes()
    if sha256_bytes(data) != PINS[name]:
        raise VendorError(f"pristine {name} does not match its sha256 pin")
    return data


def build() -> dict[str, bytes]:
    """The generated files, in memory: ``app.js`` and ``index.html``."""
    app = apply_rules(_pristine("app.js").decode("utf-8"), APP_RULES, "app.js").encode("utf-8")
    index = apply_rules(_pristine("index.html").decode("utf-8"), INDEX_RULES, "index.html")
    hashes = {
        "app.js": short_hash(app),
        "style.css": short_hash(UNMODIFIED_FILES["style.css"].read_bytes()),
        "memdash-shim.js": short_hash((SERVED / "memdash-shim.js").read_bytes()),
        "memdash-overrides.css": short_hash((SERVED / "memdash-overrides.css").read_bytes()),
    }
    for name, value in hashes.items():
        index = index.replace("{" + name + "}", value)
    return {"app.js": app, "index.html": index.encode("utf-8")}


def check() -> list[str]:
    problems: list[str] = []
    for name, path in UNMODIFIED_FILES.items():
        if not path.is_file():
            problems.append(f"missing {path.relative_to(REPO)}")
        elif sha256_bytes(path.read_bytes()) != PINS[name]:
            problems.append(f"{path.relative_to(REPO)} does not match its sha256 pin")
    for name in OWN_FILES:
        if not (SERVED / name).is_file():
            problems.append(f"missing {name}")
    try:
        generated = build()
    except (VendorError, OSError) as exc:
        return problems + [str(exc)]
    for name, data in generated.items():
        target = SERVED / name
        if not target.is_file() or target.read_bytes() != data:
            problems.append(f"{target.relative_to(REPO)} differs from the rewrite of the pristine copy")
    extra = sorted(
        str(p.relative_to(SERVED)) for p in SERVED.rglob("*") if p.is_file()
        and str(p.relative_to(SERVED)) not in SERVED_FILES
    )
    if extra:
        problems.append("unexpected files in the vendored directory: " + ", ".join(extra))
    return problems


def refresh_from_upstream(upstream: Path) -> None:
    for name, rel in UPSTREAM_PATHS.items():
        source = upstream / rel
        data = source.read_bytes()
        if sha256_bytes(data) != PINS[name]:
            raise VendorError(f"upstream {rel} does not match its sha256 pin; update PINS in a reviewed change")
        target = PRISTINE_FILES.get(name) or UNMODIFIED_FILES[name]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def write() -> None:
    for name, data in build().items():
        (SERVED / name).write_bytes(data)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 when anything drifted")
    parser.add_argument("--upstream", type=Path, help="refresh the pinned copies from an upstream checkout")
    args = parser.parse_args(argv)
    try:
        if args.upstream:
            refresh_from_upstream(args.upstream)
        if args.check:
            problems = check()
            for problem in problems:
                print("memdash_vendor: " + problem, file=sys.stderr)
            return 1 if problems else 0
        write()
    except (VendorError, OSError) as exc:
        print("memdash_vendor: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
