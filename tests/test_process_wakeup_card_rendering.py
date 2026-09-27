"""#6345 — collapsed summary-card rendering for process-wakeup messages.

Behavioral coverage for the three ui.js helpers behind the card:
``_parseProcessWakeupBody`` (client inverse of ``format_wakeup_prompt``),
``_processWakeupInfo`` (server ``_wakeup_meta`` merged over the client parse),
and ``_processWakeupCardHtml`` (the ``<details>`` card markup). Structural
integration with the render loop is pinned by
tests/test_process_wakeup_rendering.py.

Reworked 27 Sep 2026: the collapsed row now says "Background task complete"
(or failed, stopped, update) plus the result in plain words
(``_processWakeupOutcome``, ``_processWakeupTestSummary``); the command, exit
code and output live only in the expanded detail.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
UI_JS_PATH = ROOT / "static" / "ui.js"
STYLE_CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node not on PATH")


_DRIVER = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');
function extractFunc(name){
  const start = src.indexOf('function ' + name);
  if(start === -1) throw new Error(name + ' not found');
  const params = src.indexOf('(', start);
  let depth = 0, close = -1;
  for(let i=params; i<src.length; i++){
    if(src[i] === '(') depth++;
    else if(src[i] === ')'){
      depth--;
      if(depth === 0){ close = i; break; }
    }
  }
  const brace = src.indexOf('{', close);
  depth = 0;
  for(let i=brace; i<src.length; i++){
    if(src[i] === '{') depth++;
    else if(src[i] === '}'){
      depth--;
      if(depth === 0) return src.slice(start, i + 1);
    }
  }
  throw new Error(name + ' body did not close');
}
function esc(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function li(name, size){ return '<svg data-icon="' + name + '"></svg>'; }
function t(key, ...args){
  let out = key;
  if(args.length) out += ':' + args.join(',');
  return out;
}

eval(extractFunc('_parseProcessWakeupBody'));
eval(extractFunc('_processWakeupInfo'));
eval(extractFunc('_processWakeupTestSummary'));
eval(extractFunc('_processWakeupOutcome'));
eval(extractFunc('_processWakeupCardHtml'));

const okBody = '[IMPORTANT: Background process proc_1 completed (exit_code=0).\nCommand: npm run build\nOutput:\nall good]';
const failBody = '[IMPORTANT: Background process proc_2 completed (exit_code=3).\nCommand: pytest -q\nOutput:\n1 failed]';
const signalBody = '[IMPORTANT: Background process proc_3 completed (exit_code=-9).\nCommand: sleep 999\nOutput:\n]';
const watchBody = '[IMPORTANT: Background process w1 matched watch pattern "ERROR.*timeout".\nCommand: tail -f app.log\nMatched output:\nERROR request timeout\n(3 earlier matches were suppressed by rate limit)]';
const htmlBody = '[IMPORTANT: Background process p completed (exit_code=0).\nCommand: echo "<script>alert(1)</script>"\nOutput:\n<b>bold</b>]';
// Finding 1: leading indentation + trailing blank lines must survive.
const wsBody = '[IMPORTANT: Background process p completed (exit_code=0).\nCommand: build\nOutput:\n    indented line\n\n]';
// Finding 2: output that legitimately ends with the suppression phrasing must
// be preserved intact (not lifted into a suppression field and dropped).
const supLikeBody = '[IMPORTANT: Background process w9 matched watch pattern "ERR".\nCommand: tail\nMatched output:\nreal log\n(3 earlier matches were suppressed by rate limit)]';

const pytestPassBody = '[IMPORTANT: Background process p4 completed (exit_code=0).\nCommand: pytest -q\nOutput:\n........\n45 passed, 2 warnings in 3.21s]';
const pytestFailBody = '[IMPORTANT: Background process p5 completed (exit_code=1).\nCommand: pytest -q\nOutput:\nFAILED tests/test_a.py::test_x\n=========== 2 failed, 43 passed in 4.10s ===========]';
const pytestErrorBody = '[IMPORTANT: Background process p6 completed (exit_code=1).\nCommand: pytest -q\nOutput:\n1 failed, 1 error in 0.52s]';
// A summary that disagrees with the exit code is not trusted.
const disagreeBody = '[IMPORTANT: Background process p7 completed (exit_code=1).\nCommand: pytest -q\nOutput:\n45 passed in 3.00s\nTraceback: teardown crashed]';
const playwrightBody = '[IMPORTANT: Background process p8 completed (exit_code=1).\nCommand: npx playwright test\nOutput:\n  2 failed\n    [chromium] › login.spec.ts:12:5 › logs in\n  40 passed (1.2m)]';
const jestBody = '[IMPORTANT: Background process p9 completed (exit_code=0).\nCommand: npm test\nOutput:\nTests:       12 passed, 12 total]';
const sigtermBody = '[IMPORTANT: Background process p10 completed (exit_code=143).\nCommand: node server.js\nOutput:\n]';
const unknownDone = '[ASYNC DELEGATION BATCH COMPLETE: d1]\nA background fan-out of 2 subagent(s) finished.';
const unknownUpdate = '[IMPORTANT: Watch patterns disabled for process w2 after too many matches]';

const okInfo = _processWakeupInfo({}, okBody);
const failInfo = _processWakeupInfo({}, failBody);
const signalInfo = _processWakeupInfo({}, signalBody);
const watchInfo = _processWakeupInfo({}, watchBody);
const htmlInfo = _processWakeupInfo({}, htmlBody);
const wsInfo = _processWakeupInfo({}, wsBody);
const supLikeInfo = _processWakeupInfo({}, supLikeBody);
const metaOnlyInfo = _processWakeupInfo(
  {_wakeup_meta: {type: 'completion', task_id: 'srv_1', command: 'cargo test', exit_code: 1}},
  'some future format the client parser does not know'
);
const metaOverParse = _processWakeupInfo(
  {_wakeup_meta: {type: 'completion', task_id: 'authoritative', command: 'npm run build', exit_code: 0}},
  okBody
);

const extras = {timeHtml: '<span class="msg-time">14:32</span>', filesHtml: '', footHtml: '<div class="msg-foot"></div>'};

const outcome = (body) => _processWakeupOutcome(_processWakeupInfo({}, body), body);

process.stdout.write(JSON.stringify({
  okOutcome: outcome(okBody),
  failOutcome: outcome(failBody),
  signalOutcome: outcome(signalBody),
  sigtermOutcome: outcome(sigtermBody),
  watchOutcome: outcome(watchBody),
  pytestPassOutcome: outcome(pytestPassBody),
  pytestFailOutcome: outcome(pytestFailBody),
  pytestErrorOutcome: outcome(pytestErrorBody),
  disagreeOutcome: outcome(disagreeBody),
  playwrightOutcome: outcome(playwrightBody),
  jestOutcome: outcome(jestBody),
  unknownDoneOutcome: outcome(unknownDone),
  unknownUpdateOutcome: outcome(unknownUpdate),
  unknownCard: _processWakeupCardHtml(null, unknownDone, extras),
  okInfo, failInfo, watchInfo, metaOnlyInfo,
  metaOverParseTaskId: metaOverParse.taskId,
  unparseableIsNull: _processWakeupInfo({}, 'plain text') === null,
  emptyIsNull: _processWakeupInfo({content: ''}, '') === null,
  wsInfoOutput: wsInfo.output,
  supLikeInfo,
  okCard: _processWakeupCardHtml(okInfo, okBody, extras),
  failCard: _processWakeupCardHtml(failInfo, failBody, extras),
  signalCard: _processWakeupCardHtml(signalInfo, signalBody, extras),
  watchCard: _processWakeupCardHtml(watchInfo, watchBody, extras),
  htmlCard: _processWakeupCardHtml(htmlInfo, htmlBody, extras),
  wsCard: _processWakeupCardHtml(wsInfo, wsBody, extras),
  supLikeCard: _processWakeupCardHtml(supLikeInfo, supLikeBody, extras),
  metaOnlyCard: _processWakeupCardHtml(metaOnlyInfo, 'some future format the client parser does not know', extras),
}));
"""


def _run_driver():
    assert NODE is not None
    proc = subprocess.run(
        [NODE, "-e", _DRIVER, str(UI_JS_PATH)],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_client_parser_mirrors_the_two_structured_wakeup_shapes():
    result = _run_driver()

    ok = result["okInfo"]
    assert ok["type"] == "completion"
    assert ok["taskId"] == "proc_1"
    assert ok["command"] == "npm run build"
    assert ok["exitCode"] == "0"
    assert ok["output"] == "all good"

    watch = result["watchInfo"]
    assert watch["type"] == "watch_match"
    assert watch["pattern"] == "ERROR.*timeout"
    assert watch["command"] == "tail -f app.log"
    # The suppression note is part of the output tail, never a separate field.
    assert watch["output"] == "ERROR request timeout\n(3 earlier matches were suppressed by rate limit)"
    assert "suppressed" not in watch

    assert result["unparseableIsNull"] is True
    assert result["emptyIsNull"] is True


def test_output_whitespace_is_preserved_byte_for_byte():
    # #6350 finding 1: leading indentation and trailing blank lines must not be
    # trimmed away in the rendered <pre>.
    result = _run_driver()
    assert result["wsInfoOutput"] == "    indented line\n\n"
    ws_card = result["wsCard"]
    assert "<pre class=\"process-wakeup-text\">    indented line\n\n</pre>" in ws_card


def test_output_that_looks_like_suppression_metadata_is_kept_in_full():
    # #6350 finding 2: adversarial output ending with the suppression phrasing
    # is preserved verbatim, with no suppression field inferred/deleted.
    result = _run_driver()
    sup = result["supLikeInfo"]
    assert sup["output"] == "real log\n(3 earlier matches were suppressed by rate limit)"
    assert "suppressed" not in sup
    assert "(3 earlier matches were suppressed by rate limit)" in result["supLikeCard"]


def test_server_meta_is_authoritative_and_covers_unparseable_bodies():
    result = _run_driver()

    meta_only = result["metaOnlyInfo"]
    assert meta_only["taskId"] == "srv_1"
    assert meta_only["command"] == "cargo test"
    assert meta_only["exitCode"] == 1
    assert meta_only["output"] is None

    assert result["metaOverParseTaskId"] == "authoritative"

    # With no parsable output section the detail falls back to the raw body.
    assert "some future format" in result["metaOnlyCard"]


def _summary(card):
    return card.split("</summary>", 1)[0]


def _detail(card):
    return card.split("</summary>", 1)[1]


def test_card_is_a_collapsed_plain_language_row():
    result = _run_driver()

    ok_card = result["okCard"]
    assert ok_card.startswith('<details class="process-wakeup-card">')
    assert "open" not in ok_card.split(">", 1)[0]
    summary = _summary(ok_card)
    # What happened, in words: a title and the result. No command, no exit
    # chip, no terminal icon in the collapsed row.
    assert "process_wakeup_title_complete" in summary
    assert "process_wakeup_result_ok" in summary
    assert 'class="process-wakeup-status ok"' in summary
    assert 'data-icon="check"' in summary
    assert "npm run build" not in summary
    assert "exit 0" not in summary
    assert "process-wakeup-chip" not in ok_card
    assert 'data-icon="terminal"' not in ok_card
    assert "[IMPORTANT" not in ok_card
    assert "process_wakeup_details" in summary
    assert 'data-icon="chevron-right"' in summary
    assert '<span class="msg-time">14:32</span>' in summary
    # The technical detail is one click away.
    detail = _detail(ok_card)
    assert "process_wakeup_command" in detail and "npm run build" in detail
    assert "process_wakeup_exit_code" in detail and "<code>0</code>" in detail
    assert "all good" in detail

    fail_summary = _summary(result["failCard"])
    assert 'class="process-wakeup-status fail"' in fail_summary
    assert "process_wakeup_title_failed" in fail_summary
    assert "<code>3</code>" in _detail(result["failCard"])

    # Signal-killed processes report negative returncodes: stopped, not failed.
    signal_summary = _summary(result["signalCard"])
    assert 'class="process-wakeup-status fail"' in signal_summary
    assert "process_wakeup_title_stopped" in signal_summary

    watch_card = result["watchCard"]
    assert 'class="process-wakeup-status watch"' in _summary(watch_card)
    assert "process_wakeup_title_update" in _summary(watch_card)
    assert "ERROR.*timeout" not in _summary(watch_card)
    # Finding 4: the full pattern is readable in the expanded detail row.
    assert "process-wakeup-pattern-row" in _detail(watch_card)
    assert "ERROR.*timeout" in _detail(watch_card)
    assert "process_wakeup_suppressed" not in watch_card
    # A watch match has no exit code row.
    assert "process-wakeup-exit-row" not in watch_card


def test_outcome_reads_the_result_in_plain_words():
    result = _run_driver()

    assert result["okOutcome"] == {"state": "ok", "title": "process_wakeup_title_complete", "result": "process_wakeup_result_ok"}
    assert result["failOutcome"]["state"] == "fail"
    assert result["failOutcome"]["result"] == "process_wakeup_result_failed"
    assert result["signalOutcome"]["title"] == "process_wakeup_title_stopped"
    assert result["sigtermOutcome"]["title"] == "process_wakeup_title_stopped"
    assert result["watchOutcome"] == {"state": "watch", "title": "process_wakeup_title_update", "result": "process_wakeup_result_watch"}

    # A test run's own summary is the result.
    assert result["pytestPassOutcome"]["result"] == "process_wakeup_result_tests_passed:45"
    assert result["pytestPassOutcome"]["state"] == "ok"
    assert result["pytestFailOutcome"]["result"] == "process_wakeup_result_tests_failed:2,43"
    assert result["pytestFailOutcome"]["title"] == "process_wakeup_title_failed"
    assert result["pytestErrorOutcome"]["result"] == "process_wakeup_result_tests_failed:2,0"
    assert result["jestOutcome"]["result"] == "process_wakeup_result_tests_passed:12"
    # Playwright prints failures on their own line; they must be counted.
    assert result["playwrightOutcome"]["result"] == "process_wakeup_result_tests_failed:2,40"
    # A summary that disagrees with the exit code is never trusted.
    assert result["disagreeOutcome"]["result"] == "process_wakeup_result_failed"

    # Unknown notices get a plain title and keep their text under Details.
    assert result["unknownDoneOutcome"] == {"state": "neutral", "title": "process_wakeup_title_complete", "result": ""}
    assert result["unknownUpdateOutcome"]["title"] == "process_wakeup_title_update"
    unknown_card = result["unknownCard"]
    assert "ASYNC DELEGATION BATCH COMPLETE" not in _summary(unknown_card)
    assert "ASYNC DELEGATION BATCH COMPLETE" in _detail(unknown_card)
    assert 'data-icon="clock"' in _summary(unknown_card)


def test_card_escapes_command_and_output():
    result = _run_driver()

    html_card = result["htmlCard"]
    assert "<script>" not in html_card
    assert "&lt;script&gt;" in html_card
    assert "<b>bold</b>" not in html_card
    assert "&lt;b&gt;bold&lt;/b&gt;" in html_card


def test_render_branch_and_css_wire_the_card_variant():
    ui = UI_JS_PATH.read_text(encoding="utf-8")
    branch_start = ui.find("if(isProcessWakeup){")
    branch_end = ui.find("if(isUser){", branch_start)
    assert branch_start != -1 and branch_end != -1
    branch = ui[branch_start:branch_end]

    assert "_processWakeupInfo(m, processText)" in branch
    assert "_processWakeupOutcome(wakeupInfo, processText)" in branch
    assert "process-wakeup-notice-card process-wakeup-${wakeupState}" in branch
    # Every wakeup, parseable or not, renders through the one card; the raw
    # notice is never dumped into the conversation any more.
    assert "_processWakeupCardHtml(wakeupInfo, processText" in branch
    assert "<pre class=\"process-wakeup-text\">" not in branch

    assert ".process-wakeup-card{" in STYLE_CSS
    assert ".process-wakeup-status.ok{" in STYLE_CSS
    assert ".process-wakeup-status.fail{" in STYLE_CSS
    assert ".process-wakeup-notice.process-wakeup-fail{" in STYLE_CSS
    assert ".process-wakeup-detail pre.process-wakeup-text{max-height" in STYLE_CSS
    # #6350 finding 3: summary wraps, mobile gets a 44px target.
    base_summary = re.search(r"\.process-wakeup-card>summary\{[^}]*\}", STYLE_CSS)
    assert base_summary and "flex-wrap:wrap" in base_summary.group(0)
    assert "@media(max-width:700px){.process-wakeup-card>summary{min-height:44px;}}" in STYLE_CSS
    assert ".process-wakeup-pattern-row" in STYLE_CSS
