"""Bot teamwork presentation: handoff line, helper credit, result card and dock.

Runs the real browser modules in Node (static/tool-friendly.js and
static/subagent-threads.js) and the result-card branch extracted from
static/ui.js, the same way tests/test_process_wakeup_card_rendering.py does.
"""
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from tests.test_process_wakeup_card_rendering import _DRIVER

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not on PATH")
LONG_DASH = re.compile("[\u2013\u2014]")


def _run(args):
    result = subprocess.run([NODE, *args], capture_output=True, text=True, timeout=30, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_friendly_handoff_copy_names_and_credit():
    assert "ok" in _run([str(ROOT / "tests" / "test_bot_teamwork_friendly.cjs")])


def test_teamwork_dock_and_handoff_lines():
    assert "ok" in _run([str(ROOT / "tests" / "test_bot_teamwork_dock.cjs")])


def test_result_card_names_the_helper_and_hides_the_envelope():
    driver = _DRIVER.split("const okBody =")[0] + r"""
const assert=require('assert');
global.window={SynPulseFriendlyTools:require(process.cwd()+'/static/tool-friendly.js')};
window.SynPulseFriendlyTools.setLanguage('nl');
global.window.groupRouting={botInfo:id=>({'linus-research':{known:true,title:'Linus',avatar_url:''},
  'sanne-sales':{known:true,title:'Sanne',avatar_url:''}})[id]||null};
globalThis.groupRouting=global.window.groupRouting;
const raw='[ASYNC DELEGATION COMPLETE \u2014 job1]\nSpecialist: linus-research; conversation abcdef123456\nTask: secret task\n\nResult data:\nPrivate findings';
const info=_processWakeupInfo({_source:'process_wakeup'},raw);
const card=_processWakeupCardHtml(info,raw,{timeHtml:'<span class="msg-time">10:00</span>',
  botDelegation:{from:'linus-research',to:'sanne-sales',session_id:'abcdef123456',mode:'background',result:true}});
assert(card.includes('class="sp-bot-result"'),card);
assert(card.includes('bot_team_result_done:Linus'),card);
assert(card.includes('bot_team_result_to:Sanne'),card);
assert(card.includes('data-sp-specialist-open="abcdef123456"'),card);
assert(card.includes('bot_team_result_open:Linus'),card);
for(const hidden of ['Private findings','secret task','Specialist:','ASYNC DELEGATION']) assert(!card.includes(hidden),hidden);
const text=card.replace(/<[^>]*>/g,'');
assert(!text.includes('linus-research')&&!text.includes('sanne-sales'),text);
const bad=raw+'\n--- ERROR ---\nboom';
assert(_processWakeupCardHtml(info,bad,{botDelegation:{from:'linus-research',to:'sanne-sales',result:true}}).includes('bot_team_result_partial:Linus'));
const unresolved=raw+'\nUnresolved delegated work:\nBot delegation failed';
assert(_processWakeupCardHtml(info,unresolved,{botDelegation:{from:'linus-research',to:'sanne-sales',result:true}}).includes('data-state="partial"'));
// No child id that looks real: no button, never a broken link.
assert(!_processWakeupCardHtml(info,raw,{botDelegation:{from:'linus-research',to:'sanne-sales',session_id:'../x',result:true}}).includes('data-sp-specialist-open'));
// Not a bot result: the existing background card is unchanged.
assert(_processWakeupCardHtml(info,raw,{}).includes('process_wakeup_delegation_received'));
assert(_processWakeupCardHtml(info,raw,{botDelegation:{from:'a',to:'b',result:false}}).includes('process-wakeup-card'));
console.log('ok');
"""
    result = subprocess.run([NODE, "-e", driver, str(ROOT / "static" / "ui.js")],
                            capture_output=True, text=True, timeout=30, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_i18n_keys_exist_in_dutch_and_english_without_long_dashes():
    keys = ["bot_team_task_from_to", "bot_team_answer_from_to", "bot_team_view_task",
            "bot_team_result_done", "bot_team_result_partial", "bot_team_result_to",
            "bot_team_result_open", "bot_team_assisted_by"]
    for name in ("nl", "en"):
        text = (ROOT / "static" / "i18n" / f"{name}.js").read_text(encoding="utf-8")
        for key in keys:
            line = next((ln for ln in text.splitlines() if ln.strip().startswith(key + ":")), None)
            assert line, (name, key)
            assert not LONG_DASH.search(line), line
    nl = (ROOT / "static" / "i18n" / "nl.js").read_text(encoding="utf-8")
    assert "bot_team_result_done: '{0} is klaar'" in nl
    assert "bot_team_assisted_by: 'met hulp van {0}'" in nl


def test_ui_hooks_are_guarded():
    ui = (ROOT / "static" / "ui.js").read_text(encoding="utf-8")
    assert "window.SynPulseSubagentThreads&&typeof window.SynPulseSubagentThreads.decorate==='function'" in ui
    assert "window.SynPulseFriendlyTools&&window.SynPulseFriendlyTools.bots" in ui
    for name in ("tool-friendly.js", "subagent-threads.js"):
        assert "\U0001F916" not in (ROOT / "static" / name).read_text(encoding="utf-8"), name
