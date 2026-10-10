"""Inline SVG visuals: the server-side validator and sanitiser.

Plan addendum section 3.2. The browser sanitiser in ``static/svg_visuals.js``
(``sanitizeSvgSource``) is authoritative for what a chat shows. This module
implements the same rules in Python for tests, adoption metrics and export
parity, so one fixture corpus (``tests/fixtures/svg/``) drives both sides.

Public API:

- ``validate_svg(source)`` returns an :class:`SvgReport`: ``ok`` is true only
  when nothing in the source is rejected, dropped for safety or neutralised;
  ``errors`` and ``warnings`` carry stable codes (see ``ERROR_CODES`` and
  ``WARNING_CODES``).
- ``sanitize_svg(source)`` returns a :class:`SanitizeResult` shaped like the
  browser result ``{ok, svg, title, box, reasons, paper}``.
- ``fence_accepts(lang, code)``, ``raw_svg_spans(text)``,
  ``find_visual_blocks(text)`` and ``visual_stats(text)`` mirror the chat
  renderer hooks, so a reply can be counted without a browser.

Model output is untrusted. Every check fails closed: the size cap and the
DOCTYPE and ENTITY check run before any parser sees the text.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field
from typing import Iterable, Optional
from xml.etree import ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
XML_NS = "http://www.w3.org/XML/1998/namespace"

MAX_SOURCE_BYTES = 128 * 1024
WARN_SOURCE_BYTES = 16 * 1024
MAX_ELEMENTS = 4000
MAX_DEPTH = 48
MAX_STYLE_BYTES = 8 * 1024
MAX_TITLE_CHARS = 200
MAX_VIEWBOX_WIDTH = 720

# Codes that make a source unusable (the renderer shows it as code).
REJECT_CODES = (
    "empty",
    "too_large",
    "doctype",
    "parse_error",
    "not_svg",
    "too_many_elements",
    "too_deep",
    "no_viewbox",
)
# Codes for content the renderer removes or rewrites for safety.
NEUTRALISE_CODES = (
    "forbidden_element",
    "event_handler",
    "external_reference",
    "forbidden_css",
    "style_too_large",
    "processing_instruction",
)
ERROR_CODES = REJECT_CODES + NEUTRALISE_CODES
# Quality notes: the visual still renders as intended.
WARNING_CODES = (
    "large",
    "no_title",
    "wide",
    "fixed_size",
    "no_xmlns",
    "no_theme",
    "element_dropped",
    "attribute_dropped",
)

ALLOWED_ELEMENTS = frozenset(
    (
        "svg g defs symbol use title desc text tspan textPath "
        "path rect circle ellipse line polyline polygon "
        "linearGradient radialGradient stop pattern clipPath mask marker "
        "filter feGaussianBlur feOffset feBlend feColorMatrix feComposite feFlood "
        "feMerge feMergeNode feDropShadow feMorphology style"
    ).split()
)
# Dropped with their subtree and reported as an error (not just a warning).
FORBIDDEN_ELEMENTS = frozenset(
    (
        "script foreignobject iframe object embed image img a animate set "
        "animatemotion animatetransform animatecolor feimage audio video canvas "
        "html body head link meta base form input button textarea frame frameset "
        "discard handler listener"
    ).split()
)
UNWRAP_ELEMENTS = frozenset(("a",))
TEXT_ONLY_ELEMENTS = frozenset(("title", "desc", "style"))

GLOBAL_ATTRS = frozenset(
    (
        "id class role aria-label aria-hidden aria-labelledby aria-describedby "
        "lang xml:lang xml:space style"
    ).split()
)
PRESENTATION_ATTRS = frozenset(
    (
        "alignment-baseline baseline-shift clip-path clip-rule color "
        "color-interpolation color-interpolation-filters direction display "
        "dominant-baseline fill fill-opacity fill-rule filter flood-color "
        "flood-opacity font-family font-size font-size-adjust font-stretch "
        "font-style font-variant font-weight isolation letter-spacing "
        "lighting-color marker-end marker-mid marker-start mask mix-blend-mode "
        "opacity overflow paint-order pointer-events shape-rendering stop-color "
        "stop-opacity stroke stroke-dasharray stroke-dashoffset stroke-linecap "
        "stroke-linejoin stroke-miterlimit stroke-opacity stroke-width "
        "text-anchor text-decoration text-rendering transform transform-origin "
        "unicode-bidi vector-effect visibility word-spacing writing-mode"
    ).split()
)
_FE_COMMON = ("x", "y", "width", "height", "result")
ELEMENT_ATTRS = {
    "svg": ("viewBox", "preserveAspectRatio", "width", "height", "x", "y", "version"),
    "g": (),
    "defs": (),
    "symbol": ("viewBox", "preserveAspectRatio", "x", "y", "width", "height", "refX", "refY"),
    "use": ("href", "x", "y", "width", "height"),
    "title": (),
    "desc": (),
    "text": ("x", "y", "dx", "dy", "rotate", "textLength", "lengthAdjust"),
    "tspan": ("x", "y", "dx", "dy", "rotate", "textLength", "lengthAdjust"),
    "textPath": ("href", "startOffset", "method", "spacing", "side", "textLength", "lengthAdjust"),
    "path": ("d", "pathLength"),
    "rect": ("x", "y", "width", "height", "rx", "ry", "pathLength"),
    "circle": ("cx", "cy", "r", "pathLength"),
    "ellipse": ("cx", "cy", "rx", "ry", "pathLength"),
    "line": ("x1", "y1", "x2", "y2", "pathLength"),
    "polyline": ("points", "pathLength"),
    "polygon": ("points", "pathLength"),
    "linearGradient": ("x1", "y1", "x2", "y2", "gradientUnits", "gradientTransform", "spreadMethod", "href"),
    "radialGradient": ("cx", "cy", "r", "fx", "fy", "fr", "gradientUnits", "gradientTransform", "spreadMethod", "href"),
    "stop": ("offset",),
    "pattern": (
        "x", "y", "width", "height", "patternUnits", "patternContentUnits",
        "patternTransform", "viewBox", "preserveAspectRatio", "href",
    ),
    "clipPath": ("clipPathUnits",),
    "mask": ("x", "y", "width", "height", "maskUnits", "maskContentUnits", "mask-type"),
    "marker": (
        "viewBox", "preserveAspectRatio", "refX", "refY", "markerUnits",
        "markerWidth", "markerHeight", "orient",
    ),
    "filter": ("x", "y", "width", "height", "filterUnits", "primitiveUnits"),
    "feGaussianBlur": _FE_COMMON + ("in", "stdDeviation", "edgeMode"),
    "feOffset": _FE_COMMON + ("in", "dx", "dy"),
    "feBlend": _FE_COMMON + ("in", "in2", "mode"),
    "feColorMatrix": _FE_COMMON + ("in", "type", "values"),
    "feComposite": _FE_COMMON + ("in", "in2", "operator", "k1", "k2", "k3", "k4"),
    "feFlood": _FE_COMMON,
    "feMerge": _FE_COMMON,
    "feMergeNode": ("in",),
    "feDropShadow": _FE_COMMON + ("in", "dx", "dy", "stdDeviation"),
    "feMorphology": _FE_COMMON + ("in", "operator", "radius"),
    "style": ("type", "media"),
}

# Theme tokens for a standalone copy, a download and the paper card. The
# values match the fallbacks the visuals prompt asks the model to use.
LIGHT_TOKENS = (
    ("--sp-fg", "#1f2937"),
    ("--sp-muted", "#6b7280"),
    ("--sp-accent", "#f97316"),
    ("--sp-surface", "#f3f4f6"),
    ("--sp-border", "#d1d5db"),
    ("--sp-bg", "#ffffff"),
    ("--sp-ok", "#16a34a"),
    ("--sp-warn", "#d97706"),
    ("--sp-err", "#dc2626"),
)
_TOKEN_VALUE_RE = re.compile(r"^[#(),.%\w\s-]{1,64}$")

_DOCTYPE_RE = re.compile(r"<!(?:DOCTYPE|ENTITY)", re.IGNORECASE)
_BARE_AMP_RE = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);)")
_BARE_LT_RE = re.compile(r"<(?![A-Za-z_:/!?])")
_PI_RE = re.compile(r"<\?([^\s?>]+)")
_CSS_COMMENT_RE = re.compile(r"/\*[\s\S]*?(?:\*/|$)")
_COMPACT_RE = re.compile(r"[\s\x00-\x1f]+")
_CSS_FORBIDDEN_RE = re.compile(
    r"@import|@font-face|expression\(|-moz-binding|behavior:|image-set\(|image\(|"
    r"cross-fade\(|element\(|paint\("
)
_SCHEME_RE = re.compile(r"javascript:|vbscript:|livescript:|data:")
_STYLE_IMPORT_RE = re.compile(r"@import[^;]*;?", re.IGNORECASE)
_STYLE_FONT_FACE_RE = re.compile(r"@font-face\s*\{[^}]*\}?", re.IGNORECASE)
_CSS_SPACE = " \t\n\r\f"
_SVG_TAG_RE = re.compile(r"<(/?)svg(?=[ \t\r\n/>])")
# Numbers follow the browser grammar: ASCII digits only (re.ASCII), no digit
# separators, no nan or inf words, and no pattern that can backtrack on a
# long run of digits. The same patterns sit in static/svg_visuals.js.
_NUMBER_RE = re.compile(r"^((?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)(?:px)?$", re.ASCII)
_LENGTH_RE = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?:px)?$", re.ASCII)
_BOX_PART_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$", re.ASCII)
_XML_SPACE = " \t\r\n"
_BOM = chr(0xFEFF)
_FENCE_OPEN_RE = re.compile(r" {0,3}(`{3,})([^`]*)")
_FENCE_CLOSE_RE = re.compile(r" {0,3}(`{3,})[ \t]*")
_LANG_RE = re.compile(r"^(\w[\w+-]*)$", re.ASCII)


@dataclass(frozen=True)
class SvgIssue:
    code: str
    detail: str = ""


@dataclass(frozen=True)
class SvgReport:
    """Validator verdict. ``ok`` means no error; warnings never fail."""

    ok: bool
    errors: tuple = ()
    warnings: tuple = ()
    title: str = ""
    box: Optional[tuple] = None
    size: int = 0

    @property
    def error_codes(self) -> tuple:
        return tuple(dict.fromkeys(issue.code for issue in self.errors))

    @property
    def warning_codes(self) -> tuple:
        return tuple(dict.fromkeys(issue.code for issue in self.warnings))

    @property
    def code(self) -> str:
        """The first error code, or ``""`` when the source is valid."""
        return self.errors[0].code if self.errors else ""


@dataclass(frozen=True)
class SanitizeResult:
    """Same shape as the browser's ``sanitizeSvgSource`` result."""

    ok: bool
    svg: str = ""
    title: str = ""
    box: Optional[tuple] = None
    reasons: tuple = ()
    paper: bool = False


@dataclass(frozen=True)
class VisualBlock:
    kind: str  # "svg" or "mermaid"
    source: str
    origin: str  # "fence" or "raw"


@dataclass
class _Node:
    name: str
    attrs: list = field(default_factory=list)
    children: list = field(default_factory=list)  # _Node or str


class _Run:
    """One sanitiser pass: collects reasons, warnings and the clean tree."""

    def __init__(self) -> None:
        self.reasons: list = []
        self.warnings: list = []
        self.details: dict = {}

    def reason(self, code: str, detail: str = "") -> None:
        if code not in self.reasons:
            self.reasons.append(code)
            self.details[code] = detail

    def warn(self, code: str, detail: str = "") -> None:
        if code not in self.warnings:
            self.warnings.append(code)
            self.details.setdefault("w:" + code, detail)


def _utf8_len(text: str) -> int:
    return len(text.encode("utf-8", "surrogatepass"))


def _compact(value: str) -> str:
    return _COMPACT_RE.sub("", value).lower()


def _has_bad_url(compact: str) -> bool:
    index = compact.find("url(")
    while index != -1:
        rest = compact[index + 4:]
        if rest[:1] in ("'", '"'):
            rest = rest[1:]
        if not rest.startswith("#"):
            return True
        index = compact.find("url(", index + 4)
    return False


def _css_issue(text: str) -> Optional[str]:
    """Why a CSS value (a style attribute) must be dropped, or None."""
    if "\\" in text:
        return "forbidden_css"
    compact = _compact(_CSS_COMMENT_RE.sub("", text))
    if _CSS_FORBIDDEN_RE.search(compact):
        return "forbidden_css"
    if _SCHEME_RE.search(compact) or _has_bad_url(compact):
        return "external_reference"
    return None


def _value_issue(name: str, value: str) -> Optional[str]:
    """Why an attribute value must be dropped, or None (plan 3.2 rule 4)."""
    if name == "style":
        return _css_issue(value)
    compact = _compact(value)
    if _SCHEME_RE.search(compact):
        return "external_reference"
    if "expression(" in compact or "@import" in compact:
        return "forbidden_css"
    if _has_bad_url(compact):
        return "external_reference"
    if name != "aria-label":
        if "\\" in value:
            return "forbidden_css"
        if _CSS_FORBIDDEN_RE.search(compact):
            return "forbidden_css"
    return None


def _replace_remote_urls(css: str, on_remote) -> str:
    """Every well-formed url() whose target is not a #id becomes ``none``.

    A linear scan, where a regex can be made to backtrack. Anything malformed
    is left for the final check, which then drops the whole block. Mirrors
    ``replaceRemoteUrls`` in static/svg_visuals.js.
    """
    lower = css.lower()
    out = []
    index = 0
    while True:
        at = lower.find("url(", index)
        if at == -1:
            out.append(css[index:])
            break
        j = at + 4
        while j < len(css) and css[j] in _CSS_SPACE:
            j += 1
        target, end = None, -1
        if j < len(css) and css[j] in "\"'":
            close = css.find(css[j], j + 1)
            if close != -1:
                target, end = css[j + 1:close], close + 1
        else:
            k = j
            while k < len(css) and css[k] not in "'\")" and css[k] not in _CSS_SPACE:
                k += 1
            target, end = css[j:k], k
        if end != -1:
            k = end
            while k < len(css) and css[k] in _CSS_SPACE:
                k += 1
            if k < len(css) and css[k] == ")":
                if target.strip().startswith("#"):
                    out.append(css[index:k + 1])
                else:
                    on_remote()
                    out.append(css[index:at] + "none")
                index = k + 1
                continue
        out.append(css[index:at + 4])
        index = at + 4
    return "".join(out)


def _sanitize_style_text(text: str, run: _Run) -> Optional[str]:
    """Clean a ``<style>`` block, or None when it must be dropped (rule 5)."""
    if "\\" in text:
        run.reason("forbidden_css", "backslash in style block")
        return None
    css = _CSS_COMMENT_RE.sub("", text)

    def _drop_rule(match: re.Match) -> str:
        run.reason("forbidden_css", match.group(0)[:40])
        return ""

    css = _STYLE_IMPORT_RE.sub(_drop_rule, css)
    css = _STYLE_FONT_FACE_RE.sub(_drop_rule, css)

    css = _replace_remote_urls(css, lambda: run.reason("external_reference", "url()"))
    compact = _compact(css)
    if _CSS_FORBIDDEN_RE.search(compact):
        run.reason("forbidden_css", "style block")
        return None
    if _SCHEME_RE.search(compact) or _has_bad_url(compact):
        run.reason("external_reference", "style block")
        return None
    if _utf8_len(css) > MAX_STYLE_BYTES:
        run.reason("style_too_large", str(_utf8_len(css)))
        return None
    return css


def _start_tag_end(text: str, start: int) -> int:
    """Index of the ``>`` that closes the tag opening at ``start``, or -1."""
    quote = ""
    for index in range(start + 1, len(text)):
        char = text[index]
        if quote:
            if char == quote:
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
        elif char == ">":
            return index
        elif char == "<":
            return -1
    return -1


def _prolog_end(text: str) -> int:
    """Where the root element starts, after an optional byte order mark, XML
    declaration, comments and processing instructions (-1 when one is not
    closed). A linear scan, where a regex could backtrack exponentially."""
    index = 1 if text.startswith(_BOM) else 0
    while True:
        while index < len(text) and text[index] in _XML_SPACE:
            index += 1
        if text.startswith("<!--", index):
            end = text.find("-->", index + 4)
            if end == -1:
                return -1
            index = end + 3
        elif text.startswith("<?", index):
            end = text.find("?>", index + 2)
            if end == -1:
                return -1
            index = end + 2
        else:
            return index


def _fence_prolog_end(text: str) -> int:
    """Where ``<svg`` must start in an xml fence (plan 3.1): after an
    optional byte order mark, an optional XML declaration and then comments
    only; -1 when one is not closed."""
    index = 1 if text.startswith(_BOM) else 0
    if text.startswith("<?xml", index) and text[index + 5:index + 6] in (" ", "\t", "\r", "\n", "?"):
        end = text.find("?>", index + 5)
        if end == -1:
            return -1
        index = end + 2
    while True:
        while index < len(text) and text[index] in _XML_SPACE:
            index += 1
        if not text.startswith("<!--", index):
            return index
        end = text.find("-->", index + 4)
        if end == -1:
            return -1
        index = end + 3


def _starts_with_svg_tag(text: str, index: int) -> bool:
    return (index != -1 and text.startswith("<svg", index) and index + 4 < len(text)
            and text[index + 4] in " \t\r\n/>")


def _prepare(source: str, run: _Run) -> str:
    """Repair common model slips that XML parsers refuse, and add xmlns."""
    text = source.replace("&nbsp;", "&#160;")
    text = _BARE_AMP_RE.sub("&amp;", text)
    text = _BARE_LT_RE.sub("&lt;", text)
    tag_start = _prolog_end(text)
    if not _starts_with_svg_tag(text, tag_start):
        return text
    tag_end = _start_tag_end(text, tag_start)
    if tag_end == -1:
        return text
    tag = text[tag_start:tag_end]
    extra = ""
    if not re.search(r"\sxmlns\s*=", tag):
        extra += f' xmlns="{SVG_NS}"'
        run.warn("no_xmlns")
    if "xlink:" in text and not re.search(r"xmlns:xlink\s*=", text):
        extra += f' xmlns:xlink="{XLINK_NS}"'
    if extra:
        text = text[: tag_start + 4] + extra + text[tag_start + 4:]
    return text


def _split_tag(tag: str) -> tuple:
    if tag.startswith("{"):
        ns, _, local = tag[1:].partition("}")
        return ns, local
    return "", tag


def _attr_name(raw: str) -> Optional[str]:
    """Map an ElementTree attribute key to the allowlist spelling."""
    ns, local = _split_tag(raw)
    if not ns:
        return local
    if ns == XLINK_NS and local == "href":
        return "href"
    if ns == XML_NS:
        return "xml:" + local
    return None


def _parse_box(value: str) -> Optional[tuple]:
    parts = [p for p in re.split(r"[\s,]+", (value or "").strip()) if p]
    if len(parts) != 4 or not all(_BOX_PART_RE.match(p) for p in parts):
        return None
    try:
        numbers = tuple(float(p) for p in parts)
    except ValueError:
        return None
    if not all(n == n and abs(n) != float("inf") for n in numbers):
        return None
    if numbers[2] <= 0 or numbers[3] <= 0:
        return None
    return numbers


def _number(value: Optional[str]) -> Optional[float]:
    match = _NUMBER_RE.match((value or "").strip())
    if not match:
        return None
    number = float(match.group(1))
    return number if number > 0 else None


def _format_number(number: float) -> str:
    text = f"{number:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def _count_elements(root: ET.Element) -> tuple:
    count = 0
    depth = 0
    stack = [(root, 1)]
    while stack:
        element, level = stack.pop()
        count += 1
        depth = max(depth, level)
        if count > MAX_ELEMENTS or depth > MAX_DEPTH:
            break
        stack.extend((child, level + 1) for child in element)
    return count, depth


def _clean_element(element: ET.Element, run: _Run, name: str) -> _Node:
    node = _Node(name)
    allowed = ELEMENT_ATTRS.get(name, ())
    for raw_name, value in element.attrib.items():
        attr = _attr_name(raw_name)
        local = _split_tag(raw_name)[1]
        if local.lower().startswith("on"):
            run.reason("event_handler", local)
            continue
        if raw_name == "{%s}base" % XML_NS:
            run.reason("external_reference", "xml:base")
            continue
        if name in ("title", "desc"):
            permitted = attr in GLOBAL_ATTRS and attr != "style"
        elif name == "style":
            permitted = attr in allowed or (attr in GLOBAL_ATTRS and attr != "style")
        else:
            permitted = attr is not None and (
                attr in GLOBAL_ATTRS or attr in PRESENTATION_ATTRS or attr in allowed
            )
        if not permitted:
            issue = _value_issue(attr or local, value)
            if attr == "href" and not value.strip().startswith("#"):
                run.reason("external_reference", f"{local}={value[:60]}")
            elif issue:
                run.reason(issue, f"{local}={value[:60]}")
            else:
                run.warn("attribute_dropped", local)
            continue
        if attr == "href":
            target = value.strip()
            if not re.match(r"^#[^\s()'\"<>\\]+$", target):
                run.reason("external_reference", target[:60])
                continue
            node.attrs.append(("href", target))
            continue
        issue = _value_issue(attr, value)
        if issue:
            run.reason(issue, f"{attr}={value[:60]}")
            continue
        node.attrs.append((attr, value))
    return node


def _style_is_css(element: ET.Element) -> bool:
    kind = (element.get("type") or "").strip().lower()
    return kind in ("", "text/css")


def _build(element: ET.Element, run: _Run, parent: Optional[_Node]) -> Optional[_Node]:
    """Return the clean copy of ``element`` (None when it is dropped)."""
    ns, local = _split_tag(element.tag)
    lowered = local.lower()
    if ns == SVG_NS and local in UNWRAP_ELEMENTS:
        run.reason("forbidden_element", local)
        node = _clean_element(element, run, "g")
        node.attrs = [(k, v) for k, v in node.attrs if k != "href"]
    elif ns != SVG_NS or local not in ALLOWED_ELEMENTS:
        if lowered in FORBIDDEN_ELEMENTS:
            run.reason("forbidden_element", local)
        else:
            run.warn("element_dropped", local)
        return None
    else:
        node = _clean_element(element, run, local)
    if local == "style" and ns == SVG_NS:
        if not _style_is_css(element):
            run.reason("forbidden_css", "style type")
            return None
        css = _sanitize_style_text("".join(element.itertext()), run)
        if css is None:
            return None
        node.children.append(css)
        return node
    if local in TEXT_ONLY_ELEMENTS:
        node.children.append("".join(element.itertext()))
        return node
    if element.text:
        node.children.append(element.text)
    for child in element:
        clean = _build(child, run, node)
        if clean is not None:
            node.children.append(clean)
        if child.tail:
            node.children.append(child.tail)
    return node


def _escape_text(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(text: str) -> str:
    return (
        _escape_text(text)
        .replace('"', "&quot;")
        .replace("\t", "&#9;")
        .replace("\n", "&#10;")
        .replace("\r", "&#13;")
    )


def _serialize(node: _Node, root: bool = True) -> str:
    parts = ["<", node.name]
    if root:
        parts.append(f' xmlns="{SVG_NS}"')
    for name, value in node.attrs:
        parts.append(f' {name}="{_escape_attr(value)}"')
    if not node.children:
        parts.append("/>")
        return "".join(parts)
    parts.append(">")
    for child in node.children:
        parts.append(_escape_text(child) if isinstance(child, str) else _serialize(child, False))
    parts.append(f"</{node.name}>")
    return "".join(parts)


def _first_title(node: _Node) -> str:
    stack = [node]
    while stack:
        current = stack.pop(0)
        if current.name == "title":
            text = " ".join("".join(c for c in current.children if isinstance(c, str)).split())
            return text[:MAX_TITLE_CHARS]
        stack[0:0] = [c for c in current.children if isinstance(c, _Node)]
    return ""


def _attr(node: _Node, name: str) -> Optional[str]:
    for key, value in node.attrs:
        if key == name:
            return value
    return None


def _style_prop(node: _Node, prop: str) -> Optional[str]:
    style = _attr(node, "style") or ""
    for declaration in style.split(";"):
        key, _, value = declaration.partition(":")
        if key.strip().lower() == prop:
            return value.strip()
    return None


def _length(raw: str) -> Optional[float]:
    match = _LENGTH_RE.match(raw.strip())
    if not match:
        return None
    value = float(match.group(1))
    return value if abs(value) != float("inf") else None


def _is_background_rect(node: _Node, box: tuple) -> bool:
    """A filled rect that starts at the viewBox origin and covers it."""
    if node.name != "rect":
        return False
    fill = (_style_prop(node, "fill") or _attr(node, "fill") or "").strip().lower()
    if fill in ("none", "transparent"):
        return False
    for key, origin in (("x", box[0]), ("y", box[1])):
        raw = (_attr(node, key) or "0").strip()
        value = 0.0 if raw == "0%" else _length(raw)
        if value is None or value > origin:
            return False
    for key, size in (("width", box[2]), ("height", box[3])):
        raw = (_attr(node, key) or "").strip()
        if raw == "100%":
            continue
        value = _length(raw)
        if value is None or value < size:
            return False
    return True


def _is_paper(node: _Node, serialized: str, box: tuple) -> bool:
    """Plan 3.1: no ``--sp-*`` token and no full-size background rect."""
    if "--sp-" in serialized:
        return False
    for child in node.children:
        if not isinstance(child, _Node):
            continue
        if child.name in ("defs", "title", "desc", "style"):
            continue
        return not _is_background_rect(child, box)
    return True


def _run(source) -> tuple:
    """Shared pass for the validator and the sanitiser.

    Returns ``(run, fatal_code, fatal_detail, clean_root, box, serialized)``.
    """
    run = _Run()
    if not isinstance(source, str):
        return run, "empty", "not text", None, None, ""
    size = _utf8_len(source)
    if size > MAX_SOURCE_BYTES:
        return run, "too_large", str(size), None, None, ""
    if not source.strip():
        return run, "empty", "", None, None, ""
    if _DOCTYPE_RE.search(source):
        return run, "doctype", "", None, None, ""
    prepared = _prepare(source, run)
    for match in _PI_RE.finditer(prepared):
        if match.group(1).lower() != "xml":
            run.reason("processing_instruction", match.group(1)[:40])
    try:
        root = ET.fromstring(prepared)
    except ET.ParseError as exc:
        return run, "parse_error", str(exc)[:120], None, None, ""
    except Exception as exc:  # expat limits and similar: fail closed
        return run, "parse_error", type(exc).__name__, None, None, ""
    ns, local = _split_tag(root.tag)
    if ns != SVG_NS or local != "svg":
        return run, "not_svg", root.tag[:80], None, None, ""
    count, depth = _count_elements(root)
    if count > MAX_ELEMENTS:
        return run, "too_many_elements", str(count), None, None, ""
    if depth > MAX_DEPTH:
        return run, "too_deep", str(depth), None, None, ""
    clean = _build(root, run, None)
    box = _parse_box(_attr(clean, "viewBox") or "")
    width = _number(_attr(clean, "width"))
    height = _number(_attr(clean, "height"))
    if box is None:
        if width is None or height is None:
            return run, "no_viewbox", "", None, None, ""
        box = (0.0, 0.0, width, height)
        clean.attrs = [(k, v) for k, v in clean.attrs if k != "viewBox"]
        clean.attrs.insert(0, ("viewBox", "0 0 %s %s" % (_format_number(width), _format_number(height))))
    if _attr(clean, "width") is not None or _attr(clean, "height") is not None:
        run.warn("fixed_size")
        clean.attrs = [(k, v) for k, v in clean.attrs if k not in ("width", "height")]
    serialized = _serialize(clean)
    return run, "", "", clean, box, serialized


def validate_svg(source) -> SvgReport:
    """Validate a model-written SVG against the plan 3.2 rules."""
    run, fatal, fatal_detail, clean, box, serialized = _run(source)
    size = _utf8_len(source) if isinstance(source, str) else 0
    warnings = []
    if size > WARN_SOURCE_BYTES and fatal != "too_large":
        warnings.append(SvgIssue("large", str(size)))
    errors = [SvgIssue(fatal, fatal_detail)] if fatal else []
    errors.extend(SvgIssue(code, run.details.get(code, "")) for code in run.reasons)
    title = ""
    if clean is not None:
        title = _first_title(clean)
        if not title:
            warnings.append(SvgIssue("no_title"))
        if box and box[2] > MAX_VIEWBOX_WIDTH:
            warnings.append(SvgIssue("wide", _format_number(box[2])))
        if _is_paper(clean, serialized, box):
            warnings.append(SvgIssue("no_theme"))
    warnings.extend(SvgIssue(code, run.details.get("w:" + code, "")) for code in run.warnings)
    return SvgReport(
        ok=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        title=title,
        box=box if clean is not None else None,
        size=size,
    )


def sanitize_svg(source) -> SanitizeResult:
    """Return the sanitised SVG (the browser rules), or ``ok=False``."""
    run, fatal, _detail, clean, box, serialized = _run(source)
    drop_codes = tuple(c for c in run.warnings if c in ("element_dropped", "attribute_dropped"))
    if fatal:
        return SanitizeResult(ok=False, reasons=(fatal,) + tuple(run.reasons))
    return SanitizeResult(
        ok=True,
        svg=serialized,
        title=_first_title(clean),
        box=box,
        reasons=tuple(run.reasons) + drop_codes,
        paper=_is_paper(clean, serialized, box),
    )


def _theme_style(tokens: Iterable) -> str:
    fallback = dict(LIGHT_TOKENS)
    decls = []
    for name, _default in LIGHT_TOKENS:
        value = dict(tokens).get(name, fallback[name])
        if not isinstance(value, str) or not _TOKEN_VALUE_RE.match(value) or "url" in value.lower():
            value = fallback[name]
        decls.append(f"{name}:{value.strip()}")
    return "<style>:root{" + ";".join(decls) + ";color:var(--sp-fg)}</style>"


def with_theme(svg: str, tokens: Iterable = LIGHT_TOKENS) -> str:
    """Insert the theme ``<style>`` as the first child of the root element.

    Mirrors ``_svgVisuals.withTheme`` in ``static/svg_visuals.js``; with the
    default light tokens the result is what Copy SVG and Download SVG emit.
    """
    end = _start_tag_end(svg, 0) if svg.startswith("<svg") else -1
    if end == -1:
        return svg
    style = _theme_style(tokens)
    if svg[end - 1] == "/":
        return svg[: end - 1] + ">" + style + "</svg>" + svg[end + 1:]
    return svg[: end + 1] + style + svg[end + 1:]


def fence_accepts(lang, code) -> bool:
    """Mirror of ``svgVisualFenceAccepts``: which fences become visuals."""
    if not isinstance(lang, str) or not isinstance(code, str):
        return False
    body = code.strip()
    if not body:
        return False
    if lang == "svg":
        return True
    if lang == "xml":
        return _starts_with_svg_tag(body, _fence_prolog_end(body))
    return False


def _excluded_ranges(text: str) -> list:
    """Unclosed fences, tilde fences, table rows and inline code spans,
    merged and sorted."""
    ranges = []
    offset = 0
    open_fence = None
    for line in text.split("\n"):
        line_end = offset + len(line)
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if open_fence is None:
            if match:
                open_fence = (offset, match.group(1)[0], len(match.group(1)))
            elif re.match(r"^\s*\|", line):
                ranges.append((offset, line_end))
        elif match and match.group(1)[0] == open_fence[1] and len(match.group(1)) >= open_fence[2] \
                and re.match(r"^ {0,3}[`~]+\s*$", line):
            ranges.append((open_fence[0], line_end))
            open_fence = None
        offset = line_end + 1
    if open_fence is not None:
        ranges.append((open_fence[0], len(text)))
    for match in re.finditer(r"`[^`\n]+`", text):
        ranges.append(match.span())
    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def _overlaps(ranges: list, range_ends: list, start: int, end: int) -> bool:
    """Merged ranges are sorted by start and end: bisect the first one that
    ends after ``start``."""
    index = bisect.bisect_right(range_ends, start)
    return index < len(ranges) and ranges[index][0] < end


def _svg_run_ends(text: str) -> tuple:
    """One pass over the <svg and </svg tags: every open tag is matched with
    the first close tag that leaves the tags between them balanced. A tag
    that is not closed (no '>') breaks every run still open around it."""
    opens, ends, stack = [], {}, []
    position = 0
    while True:
        match = _SVG_TAG_RE.search(text, position)
        if not match:
            break
        start = match.start()
        if match.group(1):
            close = text.find(">", start)
            if close == -1:
                stack.clear()
                break
            if stack:
                ends[stack.pop()] = close + 1
            position = close + 1
        else:
            end = _start_tag_end(text, start)
            if end == -1:
                stack.clear()
                position = start + 4
                continue
            opens.append(start)
            if text[end - 1] != "/":
                stack.append(start)
            position = end + 1
    return opens, ends


def raw_svg_spans(text) -> list:
    """Mirror of ``svgVisualRawSpans``: ``[start, end]`` of raw svg runs."""
    if not isinstance(text, str) or "<svg" not in text:
        return []
    excluded = _excluded_ranges(text)
    excluded_ends = [end for _start, end in excluded]
    opens, ends = _svg_run_ends(text)
    spans = []
    last = 0
    for start in opens:
        if start < last or start not in ends:
            continue
        end = ends[start]
        chunk = text[start:end]
        if "\x00" not in chunk and chunk.endswith("</svg>") and not _overlaps(excluded, excluded_ends, start, end):
            spans.append([start, end])
        last = end
    return spans


def _fences(text: str):
    """The backtick fences renderMd (static/ui.js) turns into code blocks,
    as ``(start, end, lead, info, code)``: the matches its fence pattern
    gives, found by a linear line scan (the pattern rescans the rest of the
    text for every opener that has no closer). As in that pattern, the first
    closer two or more lines below the opener wins and the line right below
    it counts only when there is none; ``code`` is None when the fence has
    no content lines.
    """
    lines = text.split("\n")
    offsets = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line) + 1
    closers = []
    for line in lines:
        match = _FENCE_CLOSE_RE.fullmatch(line)
        closers.append(len(match.group(1)) if match else 0)
    widest_below = [0] * (len(lines) + 1)
    for index in range(len(lines) - 1, -1, -1):
        widest_below[index] = max(closers[index], widest_below[index + 1])
    index = 0
    while index < len(lines) - 1:  # an opener needs the newline after it
        match = _FENCE_OPEN_RE.fullmatch(lines[index])
        if not match:
            index += 1
            continue
        run = len(match.group(1))
        close = -1
        if index + 2 < len(lines) and widest_below[index + 2] >= run:
            close = index + 2
            while closers[close] < run:
                close += 1
            code = "\n".join(lines[index + 1:close])
        elif closers[index + 1] >= run:
            close, code = index + 1, None
        if close == -1:
            index += 1
            continue
        lead = "\n" if index else ""
        start = offsets[index] - len(lead)
        yield start, offsets[close] + len(lines[close]), lead, match.group(2), code
        index = close + 1


def find_visual_blocks(text) -> list:
    """Every svg or mermaid visual a reply would render, in order."""
    if not isinstance(text, str):
        return []
    blocks = []
    rest = []
    last = 0
    for start, end, lead, info, code in _fences(text):
        info = info.strip()
        lang_match = _LANG_RE.match(info)
        lang = lang_match.group(1).lower() if lang_match else ""
        code = code or ""
        if fence_accepts(lang, code):
            blocks.append((start, VisualBlock("svg", code.strip(), "fence")))
        elif lang == "mermaid" and code.strip():
            blocks.append((start, VisualBlock("mermaid", code.strip(), "fence")))
        rest.append(text[last:start])
        rest.append(lead + "\x00" * (end - start - len(lead)))
        last = end
    rest.append(text[last:])
    masked = "".join(rest)
    for start, end in raw_svg_spans(masked):
        blocks.append((start, VisualBlock("svg", text[start:end], "raw")))
    return [block for _pos, block in sorted(blocks, key=lambda item: item[0])]


def visual_stats(text) -> dict:
    """Counts for the adoption metric: svg and mermaid blocks and validity."""
    stats = {"svg": 0, "svg_valid": 0, "mermaid": 0}
    for block in find_visual_blocks(text):
        if block.kind == "svg":
            stats["svg"] += 1
            if validate_svg(block.source).ok:
                stats["svg_valid"] += 1
        else:
            stats["mermaid"] += 1
    return stats
