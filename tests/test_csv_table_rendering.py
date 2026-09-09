"""Test: CSV table rendering (#485)"""
import re
import subprocess
from pathlib import Path

WORKSPACE_JS = Path("static/workspace.js").read_text(encoding="utf-8")


def test_csv_extension_regex():
    """Verify _CSV_EXTS regex is defined."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    assert '_CSV_EXTS' in src, "Missing _CSV_EXTS regex"
    assert '.csv' in src, "CSV regex should match .csv extension"


def test_csv_fence_block_handler():
    """Verify fenced ```csv blocks are handled."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    assert "lang==='csv'" in src, "Missing csv language detection in fence handler"
    assert 'csv-table' in src, "Missing csv-table class for fenced CSV rendering"
    assert 'csv-table-wrap' in src, "Missing csv-table-wrap class"


def test_csv_fence_renders_table_structure():
    """Verify fenced CSV blocks produce proper table HTML."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    # Should have thead, tbody, th, td
    assert '<thead>' in src, "CSV table should have <thead>"
    assert '<tbody>' in src, "CSV table should have <tbody>"
    # In the fence handler section
    fence_section = src[src.find("lang==='csv'"):src.find("lang==='csv'") + 800]
    assert '<th>' in fence_section, "CSV headers should use <th>"
    assert '<td>' in fence_section, "CSV body should use <td>"


def test_csv_fence_fallback_for_insufficient_rows():
    """Verify CSV with < 2 rows falls back to code block."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    fence_section = src[src.find("lang==='csv'"):src.find("lang==='csv'") + 800]
    assert 'rows.length>=2' in fence_section, "Should check for at least 2 rows"
    assert '<pre${preClass}><code${langAttr}>' in fence_section, (
        "Fallback should render via the shared preClass-aware code-block template"
    )


def test_csv_media_file_handler():
    """Verify MEDIA: CSV files trigger inline loading."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    assert 'csv-inline-load' in src, "Missing csv-inline-load class for MEDIA: CSV"
    assert 'csv_loading' in src, "Missing csv_loading i18n key usage"
    open_file = WORKSPACE_JS[WORKSPACE_JS.index("async function openFile(path, opts={}){"):WORKSPACE_JS.index("\nfunction downloadFile")]
    csv_pos = open_file.find("} else if(ext==='.csv'){")
    generic_pos = open_file.find("} else {\n    // Plain code / text -- but fall back to download if server signals binary")
    assert csv_pos != -1, "openFile() should handle .csv before the generic code branch"
    assert generic_pos != -1, "generic code branch missing from openFile()"
    assert csv_pos < generic_pos


def test_loadCsvInline_function():
    """Verify loadCsvInline lazy-load function exists."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    assert 'function loadCsvInline' in src, "Missing loadCsvInline function"
    assert 'function buildCsvTablePreview(path, text, downloadUrl' in src, "Missing shared CSV preview helper"
    assert 'function _csvMediaUrl(path, opts={})' in src, "Missing CSV media URL helper"


def test_csv_media_file_keeps_download_affordance():
    """MEDIA: CSV preview must keep a visible downloadable attachment link."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    csv_section = src[src.find('function buildCsvTablePreview'):src.find('function loadCsvInline') + 1600]
    assert 'csv-download-link msg-media-link' in csv_section
    assert '_csvMediaUrl(path,{download:true})' in src
    assert 'download="${esc(fname)}"' in csv_section
    assert 'buildCsvTablePreview(path, text, downloadUrl)' in src


def test_csv_inline_max_size():
    """Verify CSV inline rendering has a size cap."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    assert 'const CSV_MAX_SIZE=256*1024' in src, "Should have CSV_MAX_SIZE constant"
    helper_section = src[src.find('function buildCsvTablePreview'):src.find('function buildCsvTablePreview') + 2000]
    assert 'csv_too_large' in helper_section, "Should use csv_too_large i18n for oversized files"


def test_csv_auto_detect_separator():
    """Verify CSV handler auto-detects separator."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    csv_section = src[src.find('function buildCsvTablePreview'):src.find('function buildCsvTablePreview') + 2000]
    assert 'separators' in csv_section, "Should have separator detection"
    assert ';' in csv_section, "Should detect semicolon separator"
    assert 'tab' in csv_section.lower() or '\\t' in csv_section, "Should detect tab separator"


def test_csv_quote_stripping():
    """Execute the real preview parser for quoted records and malformed input."""
    script = r'''
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('static/ui.js', 'utf8');
const start = source.indexOf('function _parseCsvPreviewRows(');
const end = source.indexOf('function _csvPreviewErrorHtml(', start);
assert.ok(start >= 0 && end > start);
const context = {CSV_MAX_SIZE: 256 * 1024, t: key => key,
  esc: text => String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
const parse = text => JSON.parse(JSON.stringify(context._parseCsvPreviewRows(text, ',')));
assert.deepEqual(parse('name,note\n"café","comma, quoted ""value"""\n'),
  [['name', 'note'], ['café', 'comma, quoted "value"']]);
assert.deepEqual(parse('a,b\n"line1\nline2","  spaces  "\n'),
  [['a', 'b'], ['line1\nline2', '  spaces  ']]);
assert.deepEqual(parse('a,b\n,\n'), [['a', 'b'], ['', '']]);
assert.equal(parse('a,b\n"unterminated,value\n'), null);
assert.equal(parse('a,b\n"closed"unexpected,value\n'), null);
const cells = text => {
  const result = context.buildCsvTablePreview('fixture.csv', text);
  assert.equal(typeof result.html, 'string');
  return [...result.html.matchAll(/<(?:th|td)>([\s\S]*?)<\/(?:th|td)>/g)].map(match => match[1]);
};
assert.deepEqual(cells('\ufeff\r\n"comma, header";value\r\n"semi;colon";12\r\n'),
  ['comma, header', 'value', 'semi;colon', '12']);
assert.deepEqual(cells('name\tvalue\rplain\t"tab\tinside"\r'),
  ['name', 'value', 'plain', 'tab\tinside']);
// An empty TSV header is a real record. Data commas must not change its delimiter.
assert.deepEqual(cells('\t\n1,2\t3\n'), ['', '', '1,2', '3']);
assert.deepEqual(cells('\ufeff\r\n\t\r\n1,2\t3\r\n'), ['', '', '1,2', '3']);
assert.equal(context.buildCsvTablePreview('fixture.csv', 'a,b\n"unterminated').errorKey, 'csv_error');
assert.equal(context.buildCsvTablePreview('fixture.csv', 'a,b\n').errorKey, 'csv_no_data');
assert.equal(context.buildCsvTablePreview('fixture.csv', 'x'.repeat(256 * 1024 + 1)).errorKey, 'csv_too_large');
'''
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_csv_error_handling():
    """Verify CSV error and empty data handling."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    csv_section = src[src.find('function buildCsvTablePreview'):src.find('function loadCsvInline') + 1000]
    assert 'csv_error' in csv_section, "Should use csv_error i18n on fetch failure"
    assert 'csv_no_data' in csv_section, "Should use csv_no_data i18n for insufficient data"
    helper_start = WORKSPACE_JS.index("function renderCsvPreviewContent(path, content){")
    helper_end = WORKSPACE_JS.index("\nfunction forceRenderMarkdownPreview", helper_start)
    helper_body = WORKSPACE_JS[helper_start:helper_end]
    assert "if(preview.errorKey&&typeof _csvPreviewErrorHtml==='function'){" in helper_body
    assert "$('previewMd').innerHTML=_csvPreviewErrorHtml(path, preview.errorKey);" in helper_body


def test_csv_loadCsvInline_called_after_render():
    """Verify loadCsvInline is called by the consolidated post-render pass."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    # Behavior assertion (not a brittle rAF-literal match): the post-render pass
    # is scheduled a frame later, now routed through _postProcessWithAnchorSuppression
    # (which holds overflow-anchor suppression across the media/layout reflow, then
    # calls postProcessRenderedMessages). Assert the behavior chain, so a future
    # wrapper rename doesn't re-orphan this test. (#5338)
    assert 'requestAnimationFrame(()=>_postProcessWithAnchorSuppression(' in src
    wrap_idx = src.find('function _postProcessWithAnchorSuppression')
    assert wrap_idx != -1, "post-render should be wrapped by _postProcessWithAnchorSuppression"
    assert 'postProcessRenderedMessages(container)' in src[wrap_idx:wrap_idx + 500], \
        "the wrapper must still invoke postProcessRenderedMessages"
    idx = src.find('function postProcessRenderedMessages')
    body = src[idx:idx + 500]
    assert 'loadCsvInline(container)' in body, "post-process should call loadCsvInline once per render"
    load_section = src[src.find('function loadCsvInline'):src.find('function loadCsvInline') + 1200]
    assert 'buildCsvTablePreview(path, text, downloadUrl)' in load_section, "Inline loader should reuse the shared helper"
    open_file = WORKSPACE_JS[WORKSPACE_JS.index("async function openFile(path, opts={}){"):WORKSPACE_JS.index("\nfunction downloadFile")]
    csv_pos = open_file.find("} else if(ext==='.csv'){")
    generic_pos = open_file.find("} else {\n    // Plain code / text -- but fall back to download if server signals binary")
    branch = open_file[csv_pos:generic_pos]
    assert "if(renderCsvPreviewContent(path, data.content)) return;" in branch
    assert "renderCodePreviewContent(path, data.content);" in branch
    assert "showPreview('csv');" in WORKSPACE_JS
    assert "$('previewMd').innerHTML=preview.html;" in WORKSPACE_JS
    assert "(mode==='md'||mode==='csv')" in WORKSPACE_JS
    assert "mode==='csv'?'csv'" in WORKSPACE_JS
    # csv files keep the workspace Edit affordance (regression #4025: previously
    # csv fell through to the code preview which exposed the Edit button).
    assert "_previewCurrentMode==='md'||_previewCurrentMode==='csv'" in WORKSPACE_JS


def test_csv_line_ending_normalization():
    """Verify CSV handler normalizes line endings."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    csv_section = src[src.find('function buildCsvTablePreview'):src.find('function buildCsvTablePreview') + 2000]
    assert '\\r\\n' in csv_section, "Should handle \\r\\n line endings"
    assert '\\r' in csv_section, "Should handle \\r line endings"


def test_csv_i18n_keys():
    """Split bundles retain translations and the runtime's English fallback."""
    bundles = sorted(Path('static/i18n').glob('*.js'))
    sources = [bundle.read_text(encoding='utf-8') for bundle in bundles]
    for key in ['csv_loading', 'csv_too_large', 'csv_no_data', 'csv_error']:
        assert sum(bool(re.search(rf"\b{key}\s*:", source)) for source in sources) >= 8
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx={document:{currentScript:null}};ctx.window=ctx;vm.createContext(ctx);
vm.runInContext(fs.readFileSync('static/i18n.js','utf8').split('window.i18nReady=')[0],ctx);
for(const name of fs.readdirSync('static/i18n').filter(n=>n.endsWith('.js')))
  vm.runInContext(fs.readFileSync('static/i18n/'+name,'utf8'),ctx);
vm.runInContext(`for(const code of Object.keys(LOCALES)) {
  _locale=LOCALES[code];
  for(const key of ['csv_loading','csv_too_large','csv_no_data','csv_error']) {
    if(typeof t(key)!=='string'||!t(key).trim()||t(key)===key) throw new Error(code+': '+key);
  }
}`,ctx);
"""
    result = subprocess.run(['node', '-e', script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_csv_css_classes():
    """Verify CSV table CSS classes are defined."""
    with open('static/style.css', encoding="utf-8") as f:
        src = f.read()
    required_classes = ['csv-table-wrap', 'csv-table', 'csv-table th', 'csv-table td']
    for cls in required_classes:
        assert cls in src, f"Missing CSS: {cls}"
    # Check for hover effect
    assert 'csv-table tbody tr:hover' in src, "Missing hover effect for CSV rows"


def test_csv_not_matched_by_image_exts():
    """Verify .csv is NOT in _IMAGE_EXTS."""
    with open('static/ui.js', encoding="utf-8") as f:
        src = f.read()
    match = re.search(r"const _IMAGE_EXTS=/([^/]+)/i", src)
    assert match
    exts = match.group(1)
    assert 'csv' not in exts.lower(), ".csv should NOT be in _IMAGE_EXTS"


def test_csv_preview_preserves_edit_flow():
    """Regression (#4025 review): the CSV table preview must not strip the
    workspace Edit affordance that .csv had when it fell through to the code
    preview. csv mode must be editable, the preview must cache raw content for
    the textarea, and a save must re-render the table (not markdown)."""
    with open('static/workspace.js', encoding="utf-8") as f:
        src = f.read()
    # csv mode is editable
    assert "_previewCurrentMode==='csv'" in src, "csv mode should be editable / handled in workspace edit flow"
    edit_btn = src[src.find('function updateEditBtn'):src.find('function updateEditBtn') + 400]
    assert "==='csv'" in edit_btn, "updateEditBtn must allow editing csv mode"
    # renderCsvPreviewContent caches the raw text for the edit textarea
    csv_render = src[src.find('function renderCsvPreviewContent'):src.find('function renderCsvPreviewContent') + 700]
    assert '_previewRawContent = content' in csv_render or '_previewRawContent=content' in csv_render, \
        "renderCsvPreviewContent must cache raw CSV content for the edit flow"
    # save path re-renders the CSV table for csv mode
    save_section = src[src.find('async function toggleEditMode'):src.find('async function toggleEditMode') + 2200]
    assert "renderCsvPreviewContent(_previewCurrentPath, savedContent)" in save_section, \
        "saving an edited CSV must re-render the table, not markdown"
