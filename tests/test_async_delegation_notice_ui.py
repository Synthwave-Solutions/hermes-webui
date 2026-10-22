import subprocess
from tests.test_process_wakeup_card_rendering import _DRIVER, NODE, UI_JS_PATH


def test_delegation_notice_hides_internal_prompt_and_never_claims_success():
    driver = _DRIVER.split('const okBody =')[0] + r'''
const assert=require('assert');
for(const header of ['ASYNC DELEGATION BATCH COMPLETE','ASYNC DELEGATION COMPLETE']){
  const raw='['+header+' — deleg_test]\nA background fan-out unit you dispatched earlier — 5 subagent(s) — has finished; its consolidated results are below.\nTask index 0 transcript (may be incomplete): /private/cache/task-0.log\n--- ERROR ---\nThe batch did not complete successfully: Delegation owner exited before recording a terminal result; outcome unknown.';
  const info=_processWakeupInfo({_source:'process_wakeup'},raw);
  assert(info, 'delegation must have a safe display projection');
  const html=_processWakeupCardHtml(info,raw,{});
  assert(html.includes('process_wakeup_unknown'));
  for(const internal of ['fan-out','/private/','deleg_test','owner exited','process_wakeup_success']) assert(!html.includes(internal),internal);
}
const normal=_processWakeupInfo({},'[ASYNC DELEGATION BATCH COMPLETE — deleg_ok]\nResults: useful findings');
assert(_processWakeupCardHtml(normal,'',{}).includes('process_wakeup_delegation_received'));
assert.strictEqual(_parseProcessWakeupBody('An ordinary message about ASYNC DELEGATION'),null);
'''
    result = subprocess.run([NODE, '-e', driver, str(UI_JS_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
