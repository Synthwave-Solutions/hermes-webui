"""The Python SVG validator and sanitiser (plan addendum 3.2 and 4.4, A1).

One fixture corpus drives both sides: ``tests/fixtures/svg/good`` must pass
and every file in ``tests/fixtures/svg/bad`` must fail with a stable error
code. ``tests/test_svg_visuals_sanitizer_js.py`` runs the same corpus through
the browser sanitiser and compares it with this module.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from api import svg_inline
from api.svg_inline import sanitize_svg, validate_svg

REPO = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "svg"
GOOD = sorted((FIXTURES / "good").glob("*.svg"))
BAD = sorted((FIXTURES / "bad").glob("*.svg"))
SVG = 'xmlns="http://www.w3.org/2000/svg"'
LONG_DASHES = "[" + chr(0x2013) + chr(0x2014) + "]"
NBSP = chr(0xA0)
E_ACUTE = chr(0xE9)

# The first error code of every hostile fixture. Rejections come first, then
# the first thing the sanitiser removes in document order.
BAD_EXPECTED = {
    "a-href-link.svg": "forbidden_element",
    "animate-href.svg": "forbidden_element",
    "css-escape-url.svg": "forbidden_css",
    "css-expression.svg": "forbidden_css",
    "data-uri-fill.svg": "external_reference",
    "depth-60.svg": "too_deep",
    "doctype-entity-bomb.svg": "doctype",
    "feimage-http.svg": "forbidden_element",
    "font-face.svg": "forbidden_css",
    "foreign-object.svg": "forbidden_element",
    "html-script-namespace.svg": "forbidden_element",
    "iframe-embed-object.svg": "forbidden_element",
    "image-href-http.svg": "forbidden_element",
    "image-set-css.svg": "forbidden_css",
    "inline-style-url.svg": "external_reference",
    "javascript-entity-href.svg": "external_reference",
    "mouseover-handler.svg": "event_handler",
    "no-viewbox.svg": "no_viewbox",
    "onload-attribute.svg": "event_handler",
    "oversize.svg": "too_large",
    "parse-error.svg": "parse_error",
    "root-not-svg.svg": "not_svg",
    "script-element.svg": "forbidden_element",
    "set-attributename-href.svg": "forbidden_element",
    "style-import.svg": "forbidden_css",
    "style-too-large.svg": "style_too_large",
    "style-url-http.svg": "external_reference",
    "too-many-elements.svg": "too_many_elements",
    "use-href-http.svg": "external_reference",
    "wrong-namespace.svg": "not_svg",
    "xlink-href-javascript.svg": "external_reference",
    "xml-base.svg": "external_reference",
    "xml-stylesheet-pi.svg": "processing_instruction",
}

BANNED = (
    "<script", "onload", "onerror", "onmouseover", "foreignobject", "javascript:", "vbscript:",
    "data:", "@import", "@font-face", "<image", "<a ", "<a>", "<set", "<animate", "<iframe",
    "<embed", "<object", "feimage", "xml-stylesheet", "<!doctype", "<!entity", "image-set",
    "expression(", "xml:base", "\\", "evil.example", "<html", "<?",
)


def banned_tokens(svg: str) -> list:
    """Banned tokens in sanitised output; the SVG namespace URI is allowed."""
    text = svg.replace('xmlns="http://www.w3.org/2000/svg"', "").lower()
    found = [token for token in BANNED if token in text]
    if re.search(r"https?:", text):
        found.append("http")
    return found


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_corpus_is_complete():
    assert len(GOOD) >= 12
    assert len(BAD) >= 20
    assert {p.name for p in BAD} == set(BAD_EXPECTED)
    for path in GOOD + BAD:
        assert not re.search(LONG_DASHES, read(path)), path.name


@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.name)
def test_good_fixtures_pass(path):
    report = validate_svg(read(path))
    assert report.ok, report.errors
    assert report.errors == ()
    assert report.title
    assert report.box and report.box[2] > 0 and report.box[3] > 0
    assert set(report.warning_codes) <= set(svg_inline.WARNING_CODES)
    result = sanitize_svg(read(path))
    assert result.ok and result.reasons == ()
    assert result.title == report.title
    assert result.svg.startswith("<svg " + SVG)
    assert not banned_tokens(result.svg)


@pytest.mark.parametrize("path", BAD, ids=lambda p: p.name)
def test_bad_fixtures_fail_with_a_stable_code(path):
    report = validate_svg(read(path))
    assert not report.ok
    assert report.code == BAD_EXPECTED[path.name]
    assert set(report.error_codes) <= set(svg_inline.ERROR_CODES)
    result = sanitize_svg(read(path))
    if report.code in svg_inline.REJECT_CODES:
        assert not result.ok and result.svg == "" and result.reasons[0] == report.code
    else:
        # Neutralised: the sanitised copy keeps no trace of the hostile part.
        assert result.ok and report.code in result.reasons
        assert not banned_tokens(result.svg), banned_tokens(result.svg)


def test_codes_are_stable_strings():
    assert svg_inline.REJECT_CODES == (
        "empty", "too_large", "doctype", "parse_error", "not_svg",
        "too_many_elements", "too_deep", "no_viewbox",
    )
    assert svg_inline.NEUTRALISE_CODES == (
        "forbidden_element", "event_handler", "external_reference",
        "forbidden_css", "style_too_large", "processing_instruction",
    )


def _padded(size: int) -> str:
    head = f'<svg {SVG} viewBox="0 0 10 10"><title>Padded</title><desc>'
    tail = '</desc><rect width="10" height="10" fill="var(--sp-fg,#1f2937)"/></svg>'
    return head + "x" * (size - len(head) - len(tail)) + tail


def test_a_source_over_16_kb_passes_with_a_warning():
    assert "large" not in validate_svg(_padded(16 * 1024)).warning_codes
    report = validate_svg(_padded(16 * 1024 + 1))
    assert report.ok and "large" in report.warning_codes
    assert report.size == 16 * 1024 + 1


def test_the_size_cap_is_in_utf8_bytes_and_inclusive():
    assert validate_svg(_padded(128 * 1024)).ok
    assert validate_svg(_padded(128 * 1024 + 1)).code == "too_large"
    wide = _padded(128 * 1024 - 1).replace("x", E_ACUTE, 1)  # one char, two bytes
    assert len(wide) == 128 * 1024 - 1 and len(wide.encode()) == 128 * 1024
    assert validate_svg(wide).ok
    wider = _padded(128 * 1024).replace("x", E_ACUTE, 1)
    assert len(wider) == 128 * 1024
    assert validate_svg(wider).code == "too_large"


@pytest.mark.parametrize("source", [
    f'<!DOCTYPE svg><svg {SVG} viewBox="0 0 1 1"/>',
    f'<svg {SVG} viewBox="0 0 1 1"><!ENTITY x "y"></svg>',
    f'<?xml version="1.0"?>\n<!doctype svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://x/y.dtd"><svg {SVG} viewBox="0 0 1 1"/>',
])
def test_doctype_and_entity_are_rejected_before_any_parser_runs(monkeypatch, source):
    def boom(*_args, **_kwargs):
        raise AssertionError("the parser must not run")

    monkeypatch.setattr(svg_inline.ET, "fromstring", boom)
    assert validate_svg(source).code == "doctype"
    assert sanitize_svg(source).reasons == ("doctype",)


def test_oversize_is_rejected_before_any_parser_runs(monkeypatch):
    monkeypatch.setattr(svg_inline.ET, "fromstring", lambda *_a, **_k: pytest.fail("parsed"))
    assert validate_svg(read(FIXTURES / "bad" / "oversize.svg")).code == "too_large"


@pytest.mark.parametrize("value", [None, 42, b"<svg/>", "", "   \n"])
def test_non_text_or_empty_input_is_rejected(value):
    assert validate_svg(value).code == "empty"
    assert not sanitize_svg(value).ok


def test_viewbox_is_derived_from_width_and_height_and_the_size_removed():
    result = sanitize_svg(read(FIXTURES / "good" / "width-height-only.svg"))
    assert result.box == (0.0, 0.0, 300.0, 120.0)
    root = result.svg[: result.svg.index(">")]
    assert 'viewBox="0 0 300 120"' in root
    assert "width=" not in root and "height=" not in root
    assert "fixed_size" in validate_svg(read(FIXTURES / "good" / "width-height-only.svg")).warning_codes


@pytest.mark.parametrize("attrs", ['width="50%" height="20"', 'viewBox="0 0 0 10"', 'viewBox="a b c d"', ""])
def test_without_a_usable_size_the_visual_is_rejected(attrs):
    assert validate_svg(f'<svg {SVG} {attrs}><rect/></svg>').code == "no_viewbox"


def test_missing_xmlns_is_added_and_reported_as_a_warning():
    report = validate_svg(read(FIXTURES / "good" / "no-xmlns.svg"))
    assert report.ok and "no_xmlns" in report.warning_codes
    assert sanitize_svg('<svg viewBox="0 0 1 1"><use xlink:href="#a"/><g id="a"/></svg>').ok


def test_bare_ampersand_and_less_than_from_the_markdown_decoder_are_repaired():
    source = f'<svg {SVG} viewBox="0 0 10 10"><title>R&D &nbsp;&amp; 1 < 2</title></svg>'
    result = sanitize_svg(source)
    assert result.ok
    assert result.title == "R&D & 1 < 2"  # whitespace, the no-break space too, collapses
    assert "<title>R&amp;D " + NBSP + "&amp; 1 &lt; 2</title>" in result.svg


def test_title_is_text_only_whitespace_collapsed_and_capped():
    long_title = "  Word\n  " * 60
    result = sanitize_svg(f'<svg {SVG} viewBox="0 0 1 1"><title>{long_title}</title></svg>')
    assert len(result.title) == svg_inline.MAX_TITLE_CHARS
    assert result.title.startswith("Word Word")
    assert "no_title" in validate_svg(f'<svg {SVG} viewBox="0 0 1 1"/>').warning_codes


def test_wide_viewbox_is_a_warning_only():
    report = validate_svg(f'<svg {SVG} viewBox="0 0 1200 400"><title>t</title></svg>')
    assert report.ok and "wide" in report.warning_codes


def test_unknown_elements_and_attributes_are_dropped_as_warnings():
    source = (f'<svg {SVG} xmlns:i="http://ns.example/inkscape" viewBox="0 0 1 1" i:label="x">'
              '<title>t</title><metadata>m</metadata><rect data-note="x" width="1" height="1"/></svg>')
    report = validate_svg(source)
    assert report.ok
    assert {"element_dropped", "attribute_dropped"} <= set(report.warning_codes)
    result = sanitize_svg(source)
    assert "metadata" not in result.svg and "data-note" not in result.svg and "label" not in result.svg
    assert result.reasons == ("attribute_dropped", "element_dropped")


def test_style_blocks_keep_media_queries_and_lose_remote_parts():
    source = (f'<svg {SVG} viewBox="0 0 1 1"><style>@import "x.css"; .a{{fill:url(#g)}} '
              '.b{fill:url("https://evil.example/p")} @media (prefers-color-scheme: dark){.a{fill:#fff}}'
              '</style><rect class="a" width="1" height="1"/></svg>')
    result = sanitize_svg(source)
    assert result.ok and result.reasons == ("forbidden_css", "external_reference")
    assert "@media (prefers-color-scheme: dark)" in result.svg
    assert "url(#g)" in result.svg and "evil.example" not in result.svg and "@import" not in result.svg


def test_a_non_css_style_type_is_dropped():
    result = sanitize_svg(f'<svg {SVG} viewBox="0 0 1 1"><style type="text/ecmascript">x</style></svg>')
    assert result.ok and "forbidden_css" in result.reasons and "<style" not in result.svg


def test_links_are_unwrapped_and_local_hrefs_kept():
    result = sanitize_svg(f'<svg {SVG} viewBox="0 0 1 1"><a href="#x"><rect id="x"/></a><use href=" #x "/></svg>')
    assert '<g><rect id="x"/></g>' in result.svg
    assert '<use href="#x"/>' in result.svg
    assert result.reasons == ("forbidden_element", "attribute_dropped")


@pytest.mark.parametrize("value", ["#a b", "#", "#x)", "http://e/#x", "/local#x"])
def test_href_must_be_a_plain_local_reference(value):
    result = sanitize_svg(f'<svg {SVG} viewBox="0 0 1 1"><use href="{value}"/></svg>')
    assert "href" not in result.svg and "external_reference" in result.reasons


def test_sanitising_is_idempotent_on_the_good_corpus():
    for path in GOOD:
        once = sanitize_svg(read(path))
        twice = sanitize_svg(once.svg)
        assert twice.ok and twice.svg == once.svg and twice.reasons == (), path.name
        assert twice.paper == once.paper and twice.title == once.title


def test_paper_fallback_follows_theme_tokens_and_background_rects():
    paper = {p.name: sanitize_svg(read(p)).paper for p in GOOD}
    assert paper["paper-dark-strokes.svg"] is True
    assert paper["background-rect.svg"] is False
    assert paper["layer-stack.svg"] is False
    rect = f'<svg {SVG} viewBox="-5 -5 20 20"><rect x="-5" y="-5" width="20" height="20" fill="#000"/></svg>'
    assert sanitize_svg(rect).paper is False
    small = f'<svg {SVG} viewBox="0 0 20 20"><rect width="19" height="20"/></svg>'
    assert sanitize_svg(small).paper is True
    none = f'<svg {SVG} viewBox="0 0 20 20"><rect width="100%" height="100%" style="fill: none"/></svg>'
    assert sanitize_svg(none).paper is True


def test_theme_style_is_inserted_as_the_first_child():
    svg = sanitize_svg(read(FIXTURES / "good" / "layer-stack.svg")).svg
    themed = svg_inline.with_theme(svg)
    root_end = svg.index(">") + 1
    assert themed[:root_end] == svg[:root_end]
    assert themed[root_end:].startswith("<style>:root{--sp-fg:#1f2937;")
    assert themed.endswith(svg[root_end:])
    assert svg_inline.with_theme(f'<svg {SVG} viewBox="0 0 1 1"/>').endswith("</style></svg>")
    hostile = svg_inline.with_theme(svg, [("--sp-fg", "url(https://evil.example)"), ("--sp-accent", "red}*{x")])
    assert "--sp-fg:#1f2937" in hostile and "--sp-accent:#f97316" in hostile and "evil" not in hostile
    assert svg_inline.with_theme(svg, [("--sp-fg", "#eeeeee")]).count("--sp-fg:#eeeeee") == 1


def test_visual_blocks_and_stats_mirror_the_renderer():
    reply = (
        "Intro\n\n```svg\n" + read(FIXTURES / "good" / "layer-stack.svg") + "```\n\n"
        "Raw <svg viewBox=\"0 0 1 1\"><title>x</title></svg> and `<svg viewBox=\"0 0 1 1\"></svg>` code.\n\n"
        "```mermaid\ngraph TD\nA-->B\n```\n\n"
        "```html\n<svg viewBox=\"0 0 1 1\"></svg>\n```\n\n"
        "```svg\n<svg><script>x</script></svg>\n```\n\n"
        "```svg\n<svg viewBox=\"0 0 1 1\"><rect/></svg>\n"
    )
    blocks = svg_inline.find_visual_blocks(reply)
    assert [(b.kind, b.origin) for b in blocks] == [
        ("svg", "fence"), ("svg", "raw"), ("mermaid", "fence"), ("svg", "fence")]
    assert svg_inline.visual_stats(reply) == {"svg": 3, "svg_valid": 2, "mermaid": 1}
    assert svg_inline.visual_stats("") == {"svg": 0, "svg_valid": 0, "mermaid": 0}
    assert svg_inline.visual_stats(None) == {"svg": 0, "svg_valid": 0, "mermaid": 0}


# ── linear time on hostile shapes ────────────────────────────────────────────
# Model text reaches these scanners on every render and every counted reply.
# Each shape below made an earlier regular expression backtrack exponentially
# or rescan the rest of the text quadratically. Every shape runs in a child
# process, so a regression fails on the time limit instead of hanging the
# suite. The browser runs the same table: the hooks in
# tests/test_svg_visuals_renderer.py, sanitizeSvgSource in
# tests/test_svg_visuals_sanitizer_js.py.

# name: (entry point, prefix, repeated unit, count, suffix)
HOSTILE_SHAPES = {
    "xml-fence-behind-comments": ("fence_xml", "", "<!--a-->", 40, "<p/>"),
    "unclosed-svg-tags": ("raw_spans", "", "<svg>", 20000, ""),
    "svg-runs-between-code-spans": ("raw_spans", "", "`c` <svg></svg> ", 20000, ""),
    "prolog-of-instructions": ("sanitize", "", "<?a?>", 40, "<p/>"),
    "prolog-of-comments": ("sanitize", "", "<!--a-->", 40, "<p/>"),
    "digit-run-in-width": ("sanitize", f'<svg {SVG} width="', "1", 60000, 'x" height="10"><rect/></svg>'),
    "digit-run-in-viewbox": ("sanitize", f'<svg {SVG} viewBox="0 0 1 ', "1", 60000, 'x"><rect/></svg>'),
    "digit-run-in-rect-width": (
        "sanitize", f'<svg {SVG} viewBox="0 0 1 1"><rect width="', "1", 60000, 'x" height="1"/></svg>'),
    "unclosed-url-in-style": (
        "sanitize", f'<svg {SVG} viewBox="0 0 1 1"><style>a{{fill:url(', " ", 7000, "</style></svg>"),
    "unclosed-fences": ("stats", "", "```a\n", 30000, ""),
}
SHAPE_SECONDS = 1.5  # the linear scans take a few milliseconds
SHAPE_TIMEOUT = 15

_SHAPE_CHILD = """
import json, sys, time
from api import svg_inline
entry, prefix, unit, count, suffix = json.loads(sys.argv[1])
text = prefix + unit * count + suffix
began = time.perf_counter()
if entry == "fence_xml":
    value = svg_inline.fence_accepts("xml", text)
elif entry == "raw_spans":
    value = svg_inline.raw_svg_spans(text)
elif entry == "stats":
    value = svg_inline.visual_stats(text)
else:
    result = svg_inline.sanitize_svg(text)
    value = {"ok": result.ok, "reasons": list(result.reasons)}
print(json.dumps({"seconds": time.perf_counter() - began, "value": value}))
"""


@lru_cache(maxsize=None)
def run_shape(name: str) -> dict:
    """``{"seconds", "value"}`` for one hostile shape, from a child process
    that imports this checkout's ``api.svg_inline``."""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _SHAPE_CHILD, json.dumps(HOSTILE_SHAPES[name])],
            cwd=REPO, capture_output=True, text=True, timeout=SHAPE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"{name}: still running after {SHAPE_TIMEOUT} s")
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout)


@pytest.mark.parametrize("name", sorted(HOSTILE_SHAPES))
def test_hostile_shapes_finish_at_once(name):
    seconds = run_shape(name)["seconds"]
    assert seconds < SHAPE_SECONDS, (name, seconds)


def test_hostile_shapes_still_get_the_right_answer():
    value = {name: run_shape(name)["value"] for name in HOSTILE_SHAPES}
    assert value["xml-fence-behind-comments"] is False
    assert value["unclosed-svg-tags"] == []
    spans = value["svg-runs-between-code-spans"]
    assert len(spans) == 20000 and spans[0] == [4, 15]
    for name in ("prolog-of-instructions", "prolog-of-comments"):
        assert value[name]["ok"] is False and value[name]["reasons"][0] == "not_svg", name
    assert value["digit-run-in-width"] == {"ok": False, "reasons": ["no_viewbox"]}
    assert value["digit-run-in-viewbox"] == {"ok": False, "reasons": ["no_viewbox"]}
    assert value["digit-run-in-rect-width"] == {"ok": True, "reasons": []}
    # A url( that never closes cannot be read, so the whole block goes.
    assert value["unclosed-url-in-style"] == {"ok": True, "reasons": ["external_reference"]}
    assert value["unclosed-fences"] == {"svg": 0, "svg_valid": 0, "mermaid": 0}


# The fence pattern of renderMd in static/ui.js, which find_visual_blocks
# mirrors with a linear line scan.
UI_FENCE_RE = re.compile(r"(^|\n)[ ]{0,3}(`{3,})([^\n`]*)\n(?:([\s\S]*?)\n)?[ ]{0,3}\2`*[ \t]*(?=\n|$)")


def test_the_fence_pattern_is_the_one_in_the_renderer():
    ui = (REPO / "static" / "ui.js").read_text(encoding="utf-8")
    assert "s=s.replace(/" + UI_FENCE_RE.pattern.replace("/", "\\/") + "/g," in ui


def test_the_fence_scan_finds_what_the_renderer_pattern_finds():
    import random

    pieces = ["```", "````", "```svg", "```xml", " ```", "   ````mermaid", "    ```", "x", "", "``` \t",
              "```\t", "~~~", "`", "``", "```a`b", "`````", "```\r", '<svg viewBox="0 0 1 1"></svg>', " "]
    rng = random.Random(20260928)
    for _ in range(4000):
        text = "\n".join(rng.choice(pieces) for _ in range(rng.randint(0, 9)))
        text = ("\n" if rng.random() < 0.1 else "") + text + ("\n" if rng.random() < 0.2 else "")
        expected = [(m.start(), m.end(), m.group(1), m.group(3), m.group(4)) for m in UI_FENCE_RE.finditer(text)]
        assert list(svg_inline._fences(text)) == expected, repr(text)


# Values float() takes and the browser number grammar does not: digit
# separators, other scripts' digits, words, hex.
NOT_BROWSER_NUMBERS = ["1_0", chr(0xFF11) + chr(0xFF10), chr(0x0661) + chr(0x0660), "nan", "Infinity", "0x10"]


def number_sources() -> dict:
    """Sources whose sizes only the Python float() would accept; the browser
    test runs them through sanitizeSvgSource too."""
    sources = {}
    for index, value in enumerate(NOT_BROWSER_NUMBERS):
        sources[f"viewbox-{index}"] = f'<svg {SVG} viewBox="0 0 {value} 10"><rect/></svg>'
        sources[f"width-{index}"] = f'<svg {SVG} width="{value}" height="10"><rect/></svg>'
        sources[f"rect-{index}"] = (f'<svg {SVG} viewBox="0 0 10 10"><rect width="{value}" height="10" '
                                    'fill="#fff"/></svg>')
    return sources


@pytest.mark.parametrize("index", range(len(NOT_BROWSER_NUMBERS)),
                         ids=lambda i: NOT_BROWSER_NUMBERS[i].encode("unicode_escape").decode())
def test_sizes_follow_the_browser_number_grammar(index):
    sources = number_sources()
    assert validate_svg(sources[f"viewbox-{index}"]).code == "no_viewbox"
    assert validate_svg(sources[f"width-{index}"]).code == "no_viewbox"
    # Not a length, so not a full-size background: the paper card applies.
    assert sanitize_svg(sources[f"rect-{index}"]).paper is True


def test_module_text_has_no_long_dashes():
    source = Path(svg_inline.__file__).read_text(encoding="utf-8")
    assert not re.search(LONG_DASHES, source)
