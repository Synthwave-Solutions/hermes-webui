"""renderMd with static/svg_visuals.js loaded (plan addendum 3.5, package A1).

The production ``renderMd`` from ``static/ui.js`` runs in node with the
production media helpers (the same harness shape as
``tests/test_data_uri_images.py``); ``static/svg_visuals.js`` is loaded first,
as ``static/index.html`` does. The hooks only say which fences and raw runs
are visuals; the renderer builds the escaped placeholder itself (AE-1, AE-2).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from api import svg_inline
from tests.test_svg_inline_validator import HOSTILE_SHAPES, SHAPE_SECONDS, run_shape

REPO = Path(__file__).resolve().parents[1]
UI_JS = REPO / "static" / "ui.js"
VISUALS_JS = REPO / "static" / "svg_visuals.js"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node not on PATH")

PLACEHOLDER_RE = re.compile(r'<div class="svg-visual-block" data-svg-id="svg-[a-z0-9]{1,8}">(.*?)</div>', re.S)

_DRIVER = r"""
const vm=require('vm');
let data='';process.stdin.on('data',c=>data+=c);process.stdin.on('end',()=>{
  const {ui,renderSource,visuals,corpus,calls}=JSON.parse(data);
  function extract(name){
    const start=ui.search(new RegExp('function\\s+'+name+'\\s*\\('));
    if(start<0) throw new Error(name+' not found');
    let i=ui.indexOf('{',start),depth=1;i++;
    while(depth>0&&i<ui.length){if(ui[i]==='{')depth++;else if(ui[i]==='}')depth--;i++;}
    return ui.slice(start,i);
  }
  const ctx={console,window:{},S:{},
    document:{createElement:()=>({innerHTML:'',textContent:''}),baseURI:'http://127.0.0.1:8787/'}};
  vm.createContext(ctx);
  vm.runInContext(`
    var esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    var _IMAGE_EXTS=/\\.(png|jpg|jpeg|gif|webp|bmp|ico|avif)$/i;
    var _SVG_EXTS=/\\.svg$/i;
    var _AUDIO_EXTS=/\\.(mp3|ogg|wav|m4a|aac|flac|wma|opus|webm)$/i;
    var _VIDEO_EXTS=/\\.(mp4|webm|mkv|mov|avi|ogv|m4v)$/i;
    var _PDF_EXTS=/\\.pdf$/i;
    var _HTML_EXTS=/\\.html?$/i;
    var _CSV_EXTS=/\\.(csv|tsv)$/i;
    var _EXCALIDRAW_EXTS=/\\.excalidraw$/i;
    var _mediaKindForName=(name='')=>{const c=String(name||'').split('?')[0].toLowerCase();
      if(_AUDIO_EXTS.test(c))return 'audio';if(_VIDEO_EXTS.test(c))return 'video';if(_IMAGE_EXTS.test(c))return 'image';return '';};
    var _mediaPlayerHtml=(k,s,n)=>'<'+k+' src="'+esc(s)+'"></'+k+'>';
    var t=k=>k;
    var __seed=0;Math.random=()=>((++__seed)*0.1234567)%1;
  `,ctx);
  for(const name of ['_DATA_IMAGE_RE','_DATA_IMAGE_SVG_RE','_DATA_IMAGE_MAX_LEN']){
    const m=ui.match(new RegExp('const '+name+'=([^\\n]*);'));
    vm.runInContext('var '+name+'='+m[1]+';',ctx);
  }
  for(const name of ['_isSafeDataImageUri','_dataImageHtml','_mdImageHtml','_inlineMediaHtmlForRef',
                     '_matchBacktickFenceLine','_isBacktickFenceClose']) vm.runInContext(extract(name),ctx);
  if(visuals) vm.runInContext(visuals,ctx);
  vm.runInContext(renderSource||extract('renderMd'),ctx);
  const out={html:corpus.map(c=>{vm.runInContext('__seed=0',ctx);return ctx.renderMd(c);})};
  out.calls=(calls||[]).map(([fn,args])=>{
    try{return {value:ctx[fn](...args)};}catch(e){return {error:String(e)};}
  });
  out.globals=['svgVisualFenceAccepts','svgVisualRawSpans','sanitizeSvgSource','renderSvgVisualBlocks',
               'enhanceSvgMediaCards','retintSvgVisuals'].filter(n=>typeof ctx[n]==='function');
  process.stdout.write(JSON.stringify(out));
});
"""


def _run(corpus, *, visuals=True, render_source=None, calls=None):
    payload = {
        "ui": UI_JS.read_text(encoding="utf-8"),
        "visuals": VISUALS_JS.read_text(encoding="utf-8") if visuals else "",
        "renderSource": render_source,
        "corpus": list(corpus),
        "calls": calls or [],
    }
    proc = subprocess.run([NODE, "-e", _DRIVER], input=json.dumps(payload), capture_output=True,
                          text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def render(text, **kwargs):
    return _run([text], **kwargs)["html"][0]


def _js_function(src: str, name: str) -> str:
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


# The scaffold seams (Z-WEBUI, addendum AE-1 to AE-3) as they stand in ui.js.
_AE1_CALL = "    if(_svgVisualFenceAccepts(lang,code)) return lead+_svgVisualPlaceholder(code);\n"
_AE2_CALL = "  s=_svgVisualRawRuns(s);\n"
_AE12_HELPERS_START = "\n  // ── Inline SVG visuals seams (plan addendum AE-1, AE-2)"
_AE3_COMMENT = ("  // The svg-visual-block alternation (plan addendum AE-3) only ever matches\n"
                "  // placeholders built above: _tag strips that class from raw HTML.\n")
_AE3_ALTERNATION = '|<div class="svg-visual-block"[\\s\\S]*?<\\/div>/g'


def _pre_scaffold_render_md() -> str:
    """renderMd with the AE-1 to AE-3 seams taken out again."""
    render_md = _js_function(UI_JS.read_text(encoding="utf-8"), "renderMd")
    for piece in (_AE1_CALL, _AE2_CALL, _AE3_COMMENT, _AE12_HELPERS_START, _AE3_ALTERNATION):
        assert render_md.count(piece) == 1, piece
    pre = render_md.replace(_AE1_CALL, "").replace(_AE2_CALL, "").replace(_AE3_COMMENT, "")
    pre = pre.replace(_AE3_ALTERNATION, "/g")
    start = pre.index(_AE12_HELPERS_START)
    pre = pre[:start] + "\n}"
    assert "svgVisual" not in pre and "svg-visual" not in pre
    return pre


ORDINARY_CORPUS = [
    "Plain **bold** and `code` with a [link](https://example.com).",
    "```js\nconst svg = '<svg></svg>';\n```",
    "```html\n<svg viewBox=\"0 0 1 1\"><rect/></svg>\n```",
    "```\n<svg viewBox=\"0 0 1 1\"></svg>\n```",
    "```mermaid\ngraph TD\nA-->B\n```",
    "Inline `<svg viewBox=\"0 0 1 1\"></svg>` stays code.",
    "| a | b |\n|---|---|\n| <svg viewBox=\"0 0 1 1\"></svg> | 2 |",
    "<SVG viewBox=\"0 0 1 1\"></SVG> upper case",
    "Empty <svg/> and <svg viewBox=\"0 0 1 1\"/> self closing",
    "Half <svg viewBox=\"0 0 1 1\"> never closed",
    "```xml\n<note><to>x</to></note>\n```",
    "```svg\n\n```",
    "~~~\n<svg viewBox=\"0 0 1 1\"></svg>\n~~~",
    "> quoted text\n\n- list <svgish> item",
    "MEDIA:/tmp/chart.svg",
    "",
]


# ── the hooks are defined and exact ─────────────────────────────────────────

def test_module_defines_the_six_globals():
    assert _run([""])["globals"] == [
        "svgVisualFenceAccepts", "svgVisualRawSpans", "sanitizeSvgSource",
        "renderSvgVisualBlocks", "enhanceSvgMediaCards", "retintSvgVisuals",
    ]


FENCE_CASES = [
    (["svg", "<svg viewBox=\"0 0 1 1\"/>"], True),
    (["svg", "not even xml"], True),
    (["svg", "   \n  "], False),
    (["xml", "<svg viewBox=\"0 0 1 1\"/>"], True),
    (["xml", "<?xml version=\"1.0\"?>\n<!-- drawn -->\n<svg viewBox=\"0 0 1 1\"/>"], True),
    (["xml", "<note><svg/></note>"], False),
    # Plan 3.1: only an XML declaration, then comments, may come before <svg.
    (["xml", "\ufeff<?xml version=\"1.0\"?><svg/>"], True),
    (["xml", "<?xml-stylesheet href=\"x.css\"?><svg/>"], False),
    (["xml", "<?php x ?><svg/>"], False),
    (["xml", "<!-- c --><?xml version=\"1.0\"?><svg/>"], False),
    (["xml", "<?xml version=\"1.0\"?><note>?><svg/>"], False),
    (["xml", "<!-- a <svg/>"], False),
    (["xml", "<svgfoo/>"], False),
    (["html", "<svg viewBox=\"0 0 1 1\"/>"], False),
    (["mermaid", "graph TD"], False),
    (["", "<svg/>"], False),
    ([None, "<svg/>"], False),
    (["svg", None], False),
]


def test_fence_accepts_answers_exactly_true_or_false_and_matches_python():
    out = _run([""], calls=[["svgVisualFenceAccepts", args] for args, _ in FENCE_CASES])
    got = [call.get("value") for call in out["calls"]]
    assert got == [expected for _, expected in FENCE_CASES]
    for (lang, code), expected in FENCE_CASES:
        assert svg_inline.fence_accepts(lang, code) is expected


RAW_CASES = [
    "Before <svg viewBox=\"0 0 1 1\"><rect/></svg> middle <svg viewBox=\"0 0 2 2\"></svg> end",
    "<svg viewBox=\"0 0 2 2\"><svg x=\"1\"><rect/></svg><svg/></svg> nested",
    "<svg viewBox=\"0 0 1 1\" data-x=\"a>b\"><text>1 > 0</text></svg> quoted angle",
    "Inline `<svg viewBox=\"0 0 1 1\"></svg>` and raw <svg viewBox=\"0 0 3 3\"></svg>",
    "| <svg viewBox=\"0 0 1 1\"></svg> | table |",
    "```svg\n<svg viewBox=\"0 0 1 1\"></svg>\n",
    "~~~\n<svg viewBox=\"0 0 1 1\"></svg>\n~~~\nafter <svg viewBox=\"0 0 4 4\"></svg>",
    "token \x00P0\x00 <svg viewBox=\"0 0 1 1\">\x00F1\x00</svg>",
    "<svgfoo></svgfoo> <svg-like> <SVG></SVG>",
    "<svg viewBox=\"0 0 1 1\"><rect/></svg >",
    "",
    "no svg here",
]


def test_raw_spans_are_valid_pairs_and_match_python():
    out = _run([""], calls=[["svgVisualRawSpans", [text]] for text in RAW_CASES])
    for text, call in zip(RAW_CASES, out["calls"], strict=True):
        spans = call["value"]
        assert spans == svg_inline.raw_svg_spans(text), text
        last = 0
        for start, end in spans:
            assert isinstance(start, int) and isinstance(end, int)
            assert last <= start < end <= len(text)
            assert text[start:end].startswith("<svg") and text[start:end].endswith("</svg>")
            last = end
    first = out["calls"][0]["value"]
    assert [RAW_CASES[0][a:b] for a, b in first] == [
        "<svg viewBox=\"0 0 1 1\"><rect/></svg>", "<svg viewBox=\"0 0 2 2\"></svg>"]
    assert len(out["calls"][1]["value"]) == 1  # the nested run is one visual
    assert [RAW_CASES[3][a:b] for a, b in out["calls"][3]["value"]] == ["<svg viewBox=\"0 0 3 3\"></svg>"]
    for index in (4, 5, 7, 8, 9, 10, 11):
        assert out["calls"][index]["value"] == [], RAW_CASES[index]
    tilde = out["calls"][6]["value"]
    assert [RAW_CASES[6][a:b] for a, b in tilde] == ["<svg viewBox=\"0 0 4 4\"></svg>"]


# renderMd calls the hooks on every render, streaming included, so hostile
# text must not stall the page. Each call runs under a vm time limit.
_TIMED_DRIVER = r"""
const vm=require('vm');
let data='';process.stdin.on('data',c=>data+=c);process.stdin.on('end',()=>{
  const {visuals,shapes,limitMs}=JSON.parse(data);
  const ctx={window:{}};ctx.self=ctx.window;vm.createContext(ctx);
  vm.runInContext(visuals,ctx);
  const out={};
  for(const [name,[entry,prefix,unit,count,suffix]] of Object.entries(shapes)){
    ctx.__text=prefix+unit.repeat(count)+suffix;
    const call=entry==='fence_xml'?"svgVisualFenceAccepts('xml',__text)":'svgVisualRawSpans(__text)';
    const began=Date.now();
    try{const value=vm.runInContext(call,ctx,{timeout:limitMs});out[name]={ms:Date.now()-began,value};}
    catch(e){out[name]={error:String(e)};}
  }
  process.stdout.write(JSON.stringify(out));
});
"""


def test_the_hooks_finish_at_once_on_hostile_text_and_match_python():
    shapes = {name: shape for name, shape in HOSTILE_SHAPES.items() if shape[0] in ("fence_xml", "raw_spans")}
    assert len(shapes) >= 3
    payload = {"visuals": VISUALS_JS.read_text(encoding="utf-8"), "shapes": shapes, "limitMs": 5000}
    proc = subprocess.run([NODE, "-e", _TIMED_DRIVER], input=json.dumps(payload), capture_output=True,
                          text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    for name in shapes:
        assert "error" not in out[name], (name, out[name])
        assert out[name]["ms"] < SHAPE_SECONDS * 1000, (name, out[name]["ms"])
        assert out[name]["value"] == run_shape(name)["value"], name


# ── renderMd output ──────────────────────────────────────────────────────────

def test_svg_fence_becomes_an_escaped_placeholder_without_a_paragraph():
    html = render("Intro\n\n```svg\n<svg viewBox=\"0 0 10 10\"><title>A & B</title>"
                  "<rect onclick=\"x()\"/></svg>\n```\n\nAfter")
    blocks = PLACEHOLDER_RE.findall(html)
    assert blocks == ["&lt;svg viewBox=&quot;0 0 10 10&quot;&gt;&lt;title&gt;A &amp; B&lt;/title&gt;"
                      "&lt;rect onclick=&quot;x()&quot;/&gt;&lt;/svg&gt;"]
    assert "<p>Intro</p>" in html and "<p>After</p>" in html
    assert "<p><div" not in html and "<br><div" not in html
    assert "<svg" not in html and "<rect" not in html


def test_upper_case_svg_fence_label_is_accepted():
    assert PLACEHOLDER_RE.search(render("```SVG\n<svg viewBox=\"0 0 1 1\"></svg>\n```"))


def test_xml_fence_that_starts_with_svg_behaves_the_same():
    html = render("```xml\n<?xml version=\"1.0\"?>\n<!-- sketch -->\n<svg viewBox=\"0 0 4 4\">"
                  "<circle r=\"2\"/></svg>\n```")
    (block,) = PLACEHOLDER_RE.findall(html)
    assert block.startswith("&lt;?xml version=&quot;1.0&quot;?&gt;")
    other = render("```xml\n<note><to>x</to></note>\n```")
    assert "svg-visual-block" not in other and 'class="language-xml"' in other


@pytest.mark.parametrize("text", [
    "```js\nconst s = '<svg viewBox=\"0 0 1 1\"></svg>';\n```",
    "```html\n<svg viewBox=\"0 0 1 1\"><rect/></svg>\n```",
    "```\n<svg viewBox=\"0 0 1 1\"></svg>\n```",
    "```json\n{\"svg\": \"<svg viewBox='0 0 1 1'></svg>\"}\n```",
])
def test_other_fences_stay_code(text):
    html = render(text)
    assert "svg-visual-block" not in html
    assert "<pre" in html or "code-tree-wrap" in html


def test_mermaid_fence_still_becomes_a_mermaid_block():
    html = render("```mermaid\ngraph TD\nA-->B\n```")
    assert 'class="mermaid-block"' in html and "svg-visual-block" not in html


def test_raw_svg_with_an_event_handler_becomes_an_inert_placeholder():
    html = render("Look: <svg onload=\"window.__pwned=1\" viewBox=\"0 0 4 4\"><circle r=\"2\"/></svg> done")
    (block,) = PLACEHOLDER_RE.findall(html)
    assert block == ("&lt;svg onload=&quot;window.__pwned=1&quot; viewBox=&quot;0 0 4 4&quot;&gt;"
                     "&lt;circle r=&quot;2&quot;/&gt;&lt;/svg&gt;")
    assert "<svg" not in html and "onload=\"" not in html
    assert "<p>Look:</p>" in html and "<p>done</p>" in html


def test_raw_svg_inside_backticks_stays_code():
    html = render("Use `<svg onload=\"x()\" viewBox=\"0 0 1 1\"></svg>` as the root.")
    assert "svg-visual-block" not in html
    assert "<code>&lt;svg onload=&quot;x()&quot; viewBox=&quot;0 0 1 1&quot;&gt;&lt;/svg&gt;</code>" in html


def test_fence_inside_a_blockquote_still_becomes_a_placeholder():
    html = render("> Quoted visual:\n> ```svg\n> <svg viewBox=\"0 0 1 1\"><rect/></svg>\n> ```\n\nplain")
    quote = html[html.index("<blockquote>"):html.index("</blockquote>")]
    assert PLACEHOLDER_RE.search(quote), html
    assert "<p>plain</p>" in html


@pytest.mark.parametrize("text", [
    "Here it comes:\n\n```svg\n<svg viewBox=\"0 0 1 1\"><rect/></svg>\n",
    "Here it comes:\n\n```svg\n<svg viewBox=\"0 0 1 1\"><rect/></svg>",
    "```svg\n<svg viewBox=\"0 0 1 1\"><re",
    "Partial raw <svg viewBox=\"0 0 1 1\"><rect/>",
])
def test_an_unclosed_fence_during_streaming_is_not_hydrated(text):
    html = render(text)
    assert "svg-visual-block" not in html
    assert html == render(text, visuals=False)


def test_two_raw_runs_and_a_nested_run():
    html = render("A <svg viewBox=\"0 0 1 1\"></svg> B <svg viewBox=\"0 0 2 2\"><svg x=\"1\"></svg></svg> C")
    blocks = PLACEHOLDER_RE.findall(html)
    assert blocks == ["&lt;svg viewBox=&quot;0 0 1 1&quot;&gt;&lt;/svg&gt;",
                      "&lt;svg viewBox=&quot;0 0 2 2&quot;&gt;&lt;svg x=&quot;1&quot;&gt;&lt;/svg&gt;&lt;/svg&gt;"]


def test_raw_html_cannot_mint_a_placeholder():
    html = render("<div class=\"svg-visual-block\" data-svg-id=\"svg-evil\">&lt;svg onload=alert(1)&gt;</div>")
    assert 'class="svg-visual-block"' not in html


def test_ordinary_markdown_is_unchanged_by_the_hooks():
    with_hooks = _run(ORDINARY_CORPUS)["html"]
    without = _run(ORDINARY_CORPUS, visuals=False)["html"]
    for case, new, old in zip(ORDINARY_CORPUS, with_hooks, without, strict=True):
        assert new == old, case


SEAM_CORPUS = ORDINARY_CORPUS + [
    "```svg\n<svg viewBox=\"0 0 10 10\"><rect/></svg>\n```",
    "Intro\n\n```xml\n<svg viewBox=\"0 0 4 4\"><circle r=\"2\"/></svg>\n```\n\nAfter",
    "Here is a picture: <svg viewBox=\"0 0 4 4\"><circle cx=\"2\" cy=\"2\" r=\"2\"/></svg> and text",
    "> quoted\n> ```svg\n> <svg></svg>\n> ```\n\nplain",
]


def test_without_svg_visuals_js_output_is_byte_identical_to_the_pre_scaffold_renderer():
    scaffold = _run(SEAM_CORPUS, visuals=False)["html"]
    pre = _run(SEAM_CORPUS, visuals=False, render_source=_pre_scaffold_render_md())["html"]
    for case, new, old in zip(SEAM_CORPUS, scaffold, pre, strict=True):
        assert new == old, case
