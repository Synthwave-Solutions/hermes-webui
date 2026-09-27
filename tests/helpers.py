"""Shared test helpers for static source assertions."""


def source_between(src: str, start_marker: str, end_marker: str) -> str:
    start = src.find(start_marker)
    assert start >= 0, f"{start_marker} not found"
    end = src.find(end_marker, start)
    assert end > start, f"{end_marker} not found after {start_marker}"
    return src[start:end]


# ── JavaScript block extraction ─────────────────────────────────────────────
#
# A plain brace counter miscounts as soon as a function body holds a brace or a
# quote inside a string, template literal or regex literal (for example the
# secret-redaction regexes in ui.js). js_block_end() skips those tokens.

_REGEX_PREFIX_CHARS = set("(,=:[!&|?{};+-*%~^<>")
_REGEX_PREFIX_WORDS = {
    "return", "typeof", "case", "do", "else", "in", "of", "new", "delete",
    "void", "throw", "instanceof", "yield", "await",
}


def _skip_js_string(src: str, i: int, quote: str) -> int:
    j = i + 1
    while j < len(src):
        c = src[j]
        if c == "\\":
            j += 2
            continue
        if c == quote or c == "\n":
            return j + 1
        j += 1
    return j


def _skip_js_template(src: str, i: int) -> int:
    j = i + 1
    while j < len(src):
        c = src[j]
        if c == "\\":
            j += 2
            continue
        if c == "`":
            return j + 1
        if c == "$" and j + 1 < len(src) and src[j + 1] == "{":
            j = js_block_end(src, j + 1)
            continue
        j += 1
    return j


def _skip_js_regex(src: str, i: int) -> int:
    j = i + 1
    in_class = False
    while j < len(src):
        c = src[j]
        if c == "\\":
            j += 2
            continue
        if c == "\n":
            return i + 1  # not a regex literal after all
        if c == "[":
            in_class = True
        elif c == "]":
            in_class = False
        elif c == "/" and not in_class:
            j += 1
            while j < len(src) and src[j].isalpha():
                j += 1
            return j
        j += 1
    return j


def js_block_end(src: str, open_brace: int) -> int:
    """Index just past the brace that closes the block opened at *open_brace*."""
    assert src[open_brace] == "{", "js_block_end must start on an opening brace"
    depth = 0
    prev = ""
    i = open_brace
    n = len(src)
    while i < n:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if ch in " \t\r\n":
            i += 1
            continue
        if ch == "/" and nxt == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if ch == "/" and nxt == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if ch in "'\"":
            i = _skip_js_string(src, i, ch)
            prev = "a"
            continue
        if ch == "`":
            i = _skip_js_template(src, i)
            prev = "a"
            continue
        if ch == "/":
            if prev == "" or prev in _REGEX_PREFIX_CHARS or prev in _REGEX_PREFIX_WORDS:
                i = _skip_js_regex(src, i)
                prev = "a"
                continue
            prev = "/"
            i += 1
            continue
        if ch.isalnum() or ch in "_$":
            j = i
            while j < n and (src[j].isalnum() or src[j] in "_$"):
                j += 1
            prev = src[i:j]
            i = j
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        prev = ch
        i += 1
    raise AssertionError("JavaScript block did not close")


def js_function_source(src: str, name: str) -> str:
    """Source of ``function <name>(...){...}``, from the keyword to its brace."""
    import re

    match = re.search(rf"function\s+{re.escape(name)}\s*\(", src)
    assert match, f"function {name} not found"
    brace = src.find("{", src.index(")", match.end() - 1))
    return src[match.start():js_block_end(src, brace)]


def live_sse_handler(src: str, event: str) -> str:
    """Source of the attachLiveStream listener for one SSE *event*.

    Upstream registers these inline (``source.addEventListener('tool',e=>{``).
    SynthPulse names the tool handlers (``function handleLiveToolEvent(e){``
    plus ``source.addEventListener('tool',handleLiveToolEvent);``) so sub-agent
    lifecycle events reuse them (53620edd). Both shapes are accepted.
    """
    import re

    inline = f"source.addEventListener('{event}',e=>{{"
    start = src.find(inline)
    if start >= 0:
        return src[start:js_block_end(src, start + len(inline) - 1)]
    named = re.search(
        rf"source\.addEventListener\('{re.escape(event)}',\s*([A-Za-z_$][\w$]*)\s*\)", src
    )
    assert named, f"no live SSE listener for {event!r}"
    return js_function_source(src, named.group(1))
