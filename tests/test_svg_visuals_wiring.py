"""Source pins for the inline SVG visuals wiring (plan addendum 3.5, A1).

The seams AE-1 to AE-6 live in scaffold-owned files (``static/ui.js``,
``static/index.html``, ``static/sw.js``); A1 only reads them. These pins keep
the contract between those seams and ``static/svg_visuals.js`` honest.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
STATIC = REPO / "static"
UI = (STATIC / "ui.js").read_text(encoding="utf-8")
VISUALS = (STATIC / "svg_visuals.js").read_text(encoding="utf-8")
CSS = (STATIC / "svg_visuals.css").read_text(encoding="utf-8")
NODE = shutil.which("node")
LONG_DASHES = "[" + chr(0x2013) + chr(0x2014) + "]"
PUBLIC = ["svgVisualFenceAccepts", "svgVisualRawSpans", "sanitizeSvgSource",
          "renderSvgVisualBlocks", "enhanceSvgMediaCards", "retintSvgVisuals"]


def _function(src: str, name: str) -> str:
    start = src.index(f"function {name}(")
    depth, i = 0, src.index("{", start)
    while True:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1


RENDER_MD = _function(UI, "renderMd")


def test_ae1_fence_hook_is_guarded_and_runs_before_the_mermaid_branch():
    call = "if(_svgVisualFenceAccepts(lang,code)) return lead+_svgVisualPlaceholder(code);"
    assert RENDER_MD.count(call) == 1
    assert RENDER_MD.index(call) < RENDER_MD.index("if(lang==='mermaid'")
    helper = _function(RENDER_MD, "_svgVisualFenceAccepts")
    assert "typeof svgVisualFenceAccepts!=='function'" in helper
    assert "try{return svgVisualFenceAccepts(lang,code)===true;}catch(_){return false;}" in helper
    placeholder = _function(RENDER_MD, "_svgVisualPlaceholder")
    assert '<div class="svg-visual-block" data-svg-id="${id}">${esc(code.trim())}</div>' in placeholder


def test_ae2_raw_run_hook_is_guarded_and_sits_between_the_fence_and_backtick_passes():
    call = "  s=_svgVisualRawRuns(s);\n"
    assert RENDER_MD.count(call) == 1
    position = RENDER_MD.index(call)
    assert RENDER_MD.index("return lead+'\\x00P'+(_preBlock_stash.length-1)+'\\x00';") < position
    assert position < RENDER_MD.index("s=s.replace(/`([^`\\n]+)`/g")
    helper = _function(RENDER_MD, "_svgVisualRawRuns")
    assert "typeof svgVisualRawSpans!=='function'" in helper
    assert "try{spans=svgVisualRawSpans(s);}catch(_){return s;}" in helper
    assert "Number.isInteger(p[0])" in helper and "p[1]<=s.length" in helper


def test_ae3_pre_stash_keeps_the_old_literal_and_the_allowlist_is_unchanged():
    assert "|<div class=\"(mermaid-block|katex-block)\"[\\s\\S]*?<\\/div>|" in RENDER_MD
    assert '|<div class="svg-visual-block"[\\s\\S]*?<\\/div>/g' in RENDER_MD
    assert "_cls(a.class,['pre-header','mermaid-block','katex-block'])" in RENDER_MD
    assert "svg-visual" not in _function(RENDER_MD, "_cls")


def test_ae4_post_processing_calls_the_hooks_last_and_guarded():
    body = _function(UI, "postProcessRenderedMessages")
    lines = [line.strip() for line in body.splitlines()[1:-1] if line.strip() and not line.strip().startswith("//")]
    assert lines[-3] == "initTreeViews(container);"
    assert lines[-2] == ("if(typeof renderSvgVisualBlocks==='function'){try{renderSvgVisualBlocks(container);}"
                         "catch(e){console.warn('[svg] render failed',e);}}")
    assert lines[-1] == ("if(typeof enhanceSvgMediaCards==='function'){try{enhanceSvgMediaCards(container);}"
                         "catch(e){console.warn('[svg] render failed',e);}}")


def test_ae6_assets_load_before_ui_js_and_are_precached():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    css_tag = '<link rel="stylesheet" href="static/svg_visuals.css?v=__WEBUI_VERSION__">'
    js_tag = '<script src="static/svg_visuals.js?v=__WEBUI_VERSION__" defer></script>'
    ui_tag = '<script src="static/ui.js?v=__WEBUI_VERSION__" defer></script>'
    assert f"{css_tag}\n{js_tag}\n{ui_tag}" in html
    # The module calls t() and li() at render time; both load earlier.
    for dep in ("static/i18n.js", "static/icons.js"):
        assert html.index(dep) < html.index(js_tag)
    sw = (STATIC / "sw.js").read_text(encoding="utf-8")
    assert "'./static/svg_visuals.js' + VQ," in sw
    assert "'./static/svg_visuals.css' + VQ," in sw


def test_the_stylesheet_defines_every_class_the_module_uses():
    for selector in (".svg-visual{", ".svg-visual-toolbar", ".svg-visual-img", ".svg-visual-caption",
                     ".svg-visual--paper", ".svg-visual--media", ".svg-visual-blocked", ".svg-visual-notice",
                     "pre.svg-visual-source[hidden]", ".img-lightbox.svg-visual-lightbox",
                     '[data-live-assistant="1"] pre > code.language-svg',
                     "var(--svg-visual-drawing-label", "max-width:100%", "height:auto"):
        assert selector in CSS, selector
    for token in ("var(--border)", "var(--code-bg)", "var(--surface)", "var(--radius"):
        assert token in CSS, token
    used = set(re.findall(r"'((?:svg-visual)[a-z-]*)'", VISUALS)) | set(re.findall(r"svg-visual[a-z-]*", VISUALS))
    for cls in used - {"svg-visual-block"}:  # the placeholder is renderMd's
        assert cls in CSS, cls


def _en_values() -> dict:
    text = (STATIC / "i18n" / "en.js").read_text(encoding="utf-8")
    return dict(re.findall(r"^\s*(svg_[a-z_]+|copy_failed):\s*'((?:[^'\\]|\\.)*)'", text, re.M))


def test_the_module_uses_only_appendix_ag_keys_and_their_english_values():
    en = _en_values()
    calls = re.findall(r"tr\('([a-z_]+)','((?:[^'\\]|\\.)*)'\)", VISUALS)
    assert calls, "no translated strings found"
    keys = {key for key, _ in calls}
    assert keys <= set(en), keys - set(en)
    assert keys <= {k for k in en if k.startswith("svg_")} | {"copy_failed"}
    for key, fallback in calls:
        assert fallback in ("", en[key]), (key, fallback)
    assert "svg_drawing" in keys and "svg_blocked" in keys


def test_the_module_never_builds_html_from_model_text():
    assert VISUALS.count("innerHTML") == 1 and "b.innerHTML=iconHtml" in VISUALS
    for banned in ("insertAdjacentHTML", "outerHTML", "document.write", "eval(", "new Function",
                   "setAttribute('on", "window.open", "location.href=", "location.assign",
                   "srcdoc", "appendChild(svg", "importNode"):
        assert banned not in VISUALS, banned
    # Only toolbar icons from our own helpers reach innerHTML.
    calls = re.findall(r"button\('([a-z]+)',tr\([^)]*\),(full|icon\('(?:copy|download|braces)'\))\)", VISUALS)
    assert [action for action, _icon in calls] == ["view", "copy", "download", "source"]
    assert VISUALS.count("button('") == len(calls)
    assert VISUALS.count("URL.createObjectURL(") == 1 and "URL.revokeObjectURL(url)" in VISUALS
    assert "data:image/svg+xml;base64," in VISUALS


def test_the_module_text_has_no_long_dashes_and_no_internal_names():
    from api.modules import DISPLAY_DENYLIST
    for text in (VISUALS, CSS):
        assert not re.search(LONG_DASHES, text)
        for name in DISPLAY_DENYLIST:
            assert name.lower() not in text.lower(), name


@pytest.mark.skipif(NODE is None, reason="node not on PATH")
def test_the_module_defines_exactly_the_public_globals_and_loads_without_a_dom():
    script = r"""
const vm=require('vm');
let data='';process.stdin.on('data',c=>data+=c);process.stdin.on('end',()=>{
  const ctx={console};vm.createContext(ctx);
  const before=new Set(Object.getOwnPropertyNames(ctx));
  vm.runInContext(data,ctx);
  const added=Object.getOwnPropertyNames(ctx).filter(n=>!before.has(n));
  const kinds=added.map(n=>typeof ctx[n]);
  const internals=vm.runInContext('typeof _svgVisuals',ctx);
  process.stdout.write(JSON.stringify({added,kinds,internals}));
});
"""
    proc = subprocess.run([NODE, "-e", script], input=VISUALS, capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["added"] == PUBLIC
    assert set(out["kinds"]) == {"function"}
    assert out["internals"] == "object"
