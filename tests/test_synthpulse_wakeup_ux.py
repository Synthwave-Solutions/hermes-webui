"""Presentation-only wakeup UX; never execute the displayed shell command."""
import json
import subprocess

from tests.test_process_wakeup_card_rendering import NODE, UI_JS_PATH, _run_driver


def test_summary_keeps_shell_commands_in_details():
    result = _run_driver()
    for key, command in [('okCard', 'npm run build'), ('failCard', 'pytest -q')]:
        summary, detail = result[key].split('</summary>', 1)
        assert command not in summary
        assert command in detail
    assert 'process_wakeup_success' in result['okCard'].split('</summary>')[0]
    assert 'process_wakeup_failed' in result['failCard'].split('</summary>')[0]
    assert 'process_wakeup_unknown' in result['unknownCard'].split('</summary>')[0]
    assert 'process_wakeup_success' not in result['unknownCard']


def test_wakeup_skips_unused_markdown_work_but_normal_messages_keep_it():
    # Execute the actual renderer statement with a spy at the markdown boundary.
    script = r"""
const src=require('fs').readFileSync(process.argv[1],'utf8');
const statement=src.slice(src.indexOf('    let bodyHtml ='),src.indexOf('    if(!isUser&&m.provider_details)'));
let calls=0;
function _getCachedRender(text){calls++; return 'rendered:'+text;}
function run(isProcessWakeup){const isUser=true, displayContent='log '.repeat(100000); eval(statement);}
run(true); const backgroundCalls=calls;
run(false);
console.log(JSON.stringify({backgroundCalls,normalCalls:calls-backgroundCalls}));
"""
    proc = subprocess.run([NODE, '-e', script, str(UI_JS_PATH)], text=True, capture_output=True, check=True)
    assert json.loads(proc.stdout) == {'backgroundCalls': 0, 'normalCalls': 1}


def test_legacy_default_brand_names_are_normalized_without_renaming_custom_bots():
    script = r"""
const src=require('fs').readFileSync(process.argv[1],'utf8');
eval(src.slice(src.indexOf('function defaultAssistantDisplayName('),src.indexOf('function assistantDisplayName(')));
console.log(JSON.stringify(['Hermes','Hermes Agent','Hermes WebUI','Hermes Control','Scout','Hermes specialist'].map(defaultAssistantDisplayName)));
"""
    proc = subprocess.run([NODE, '-e', script, str(UI_JS_PATH)], text=True, capture_output=True, check=True)
    assert json.loads(proc.stdout) == ['SynthPulse'] * 4 + ['Scout', 'Hermes specialist']
