"""Boot restoration is independent of optional workspace metadata, never setup/auth."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(not NODE, reason='node unavailable')

def run(**scenario):
    result = subprocess.run([NODE, str(ROOT/'tests/boot_workspace_ready_driver.cjs'), os.environ.get('SOURCE_ROOT',str(ROOT)), json.dumps(scenario)], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)

@pytest.mark.parametrize('local', [False, True])
def test_saved_chat_ready_before_workspace_metadata(local):
    result = run(local=local)
    assert result['before']['ready'] is True
    assert result['before']['sid'] == 'saved'
    assert result['before']['messages'] == ['Authorized saved history']
    assert result['before']['calls']['loads'][0]['opts'] == {'preserveActiveInput':True,'draftInputGeneration':4}
    assert result['after']['draft'] == 'typed draft'
    assert result['after']['workspaces'] == [{'path':'available-root'}]

@pytest.mark.parametrize('case', ['fresh','prefill','scratch','pwa','onboarding'])
def test_fresh_and_setup_paths_retain_workspace_gate(case):
    result = run(**{case:True})
    assert result['before']['ready'] is False
    assert result['before']['calls']['binds'] == []
    assert result['before']['calls']['newSessions'] == 0
    if case == 'onboarding':
        assert result['before']['calls']['loads'] == []
    assert result['after']['ready'] is True
    if case in {'fresh','prefill','scratch'}:
        assert result['after']['calls']['binds'] == [['available-root']]

def test_denied_saved_session_never_reveals_history():
    result = run(denied=True)
    assert result['before']['messages'] == []
    assert result['after']['messages'] == []
    assert result['after']['sid'] is None

@pytest.mark.parametrize('archived', [False,True])
def test_sidebar_only_restore_retains_empty_composer_workspace_gate(archived):
    result=run(local=True,sidebarOnly=True,archived=archived)
    assert result['before']['ready'] is False
    assert result['before']['calls']['loads'] == []
    assert result['after']['ready'] is True
    assert result['after']['sid'] is None

def test_newer_navigation_during_sidebar_only_workspace_gate_wins():
    result=run(local=True,sidebarOnly=True,navigate=True)
    assert result['after']['sid'] == 'newer'
    assert result['after']['draft'] == 'newer typed draft'

def test_failed_workspace_fetch_does_not_break_existing_chat():
    result = run(failedWorkspace=True)
    assert result['before']['ready'] is True
    assert result['after']['sid'] == 'saved'
    assert result['after']['draft'] == 'typed draft'

@pytest.mark.parametrize('case', ['navigate','newPending'])
def test_newer_activation_survives_late_workspace_response(case):
    result = run(**{case:True})
    assert result['after']['sid'] == 'newer'
    if case == 'navigate':
        assert result['after']['draft'] == 'newer typed draft'

@pytest.mark.parametrize('case', ['fresh','prefill','scratch','pwa'])
def test_newer_chat_activation_while_fresh_workspace_gate_is_pending(case):
    result = run(navigate=True, **{case:True})
    assert result['after']['sid'] == 'newer'
    assert result['after']['draft'] == 'newer typed draft'
    assert result['after']['calls']['binds'] == []
    assert result['after']['calls']['newSessions'] == 0

@pytest.mark.parametrize('edit', ['clear','type'])
def test_native_draft_restore_preserves_edits_before_session_response(edit):
    result = run(editDuringLoad=edit)
    expected = '' if edit == 'clear' else 'New text while restoring'
    assert result['afterSession']['ready'] is True
    assert result['afterSession']['draft'] == expected
    assert result['after']['draft'] == expected

@pytest.mark.parametrize('scenario', [{'second':True},{'profileSwitch':True},{'profileSwitch':True,'roundTrip':True},{'profileSwitch':True,'second':True}])
def test_workspace_result_cannot_overwrite_newer_request_or_profile(scenario):
    result = run(loaderOnly=True, **scenario)
    expected = 'newer' if scenario.get('second') else ''
    assert result.get('backend') is (False if expected else None)
    assert result['workspaces'] == ([{'path':expected}] if expected else None)

@pytest.mark.parametrize('shape',['null','empty','array','backend','admin'])
def test_malformed_workspace_response_does_not_mark_backend_or_admin_ready(shape):
    result=run(loaderOnly=True,malformed=shape)
    assert result['workspaces'] is None
    assert result['admin'] is False
    assert result['backendKnown'] is False
    assert result['terminalDisabled'] is True

def test_workspace_loader_recovers_after_malformed_response():
    result=run(loaderOnly=True,malformed='null',recover=True)
    assert result['workspaces']==[{'path':'current'}]
    assert result['admin'] is False
    assert result['backendKnown'] is True
    assert result['backend'] is False


@pytest.mark.parametrize('switch_path', ['manual','automatic'])
@pytest.mark.parametrize('failure', [None,'forbidden','network'])
def test_actual_profile_switch_clears_old_privileges_and_waits_for_current_backend(switch_path, failure):
    result=run(switchPath=switch_path,workspaceFailure=failure)
    for key in ['pending','afterStale']:
        state=result[key]
        assert state['profile']=='beta'
        assert state['workspaces'] is None
        assert state['admin'] is False
        assert state['backendKnown'] is False
        assert state['terminalDisabled'] is True
        assert state['defaultWorkspace']==state['switchWorkspace']==''
        assert state['sid']=='origin'
        assert state['messages']==['Authorized origin']
        assert state['calls'].get('terminalStarts',0)==0
    assert result['after']['backendKnown'] is (not bool(failure))
    assert result['after']['terminalDisabled'] is bool(failure)
    assert result['after']['calls'].get('terminalStarts',0)==(0 if failure else 1)

@pytest.mark.parametrize('switch_path', ['manual','automatic'])
def test_actual_profile_round_trip_rejects_old_same_profile_workspace_response(switch_path):
    result=run(switchPath=switch_path,roundTrip=True)
    assert result['afterStale']['profile']=='alpha'
    assert result['afterStale']['workspaces'] is None
    assert result['afterStale']['admin'] is False
    assert result['after']['workspaces']==[{'path':'current'}]

@pytest.mark.parametrize('switch_path', ['manual','automatic'])
def test_actual_profile_switch_sets_current_nonempty_default(switch_path):
    result=run(switchPath=switch_path,newDefault=True)
    assert result['pending']['defaultWorkspace']==result['pending']['switchWorkspace']=='beta-default'
    assert result['pending']['sid']=='origin'

@pytest.mark.parametrize('switch_path', ['manual','automatic'])
def test_failed_profile_switch_does_not_clear_authorized_previous_snapshot(switch_path):
    result=run(switchPath=switch_path,failedSwitch=True)['failed']
    assert result['profile']=='alpha'
    assert result['workspaces']==[{'path':'alpha-private'}]
    assert result['admin'] is True
    assert result['backendKnown'] is True
    assert result['defaultWorkspace']=='alpha-default'


@pytest.mark.parametrize('old_failure',[False,True])
def test_late_automatic_switch_cannot_replace_newer_manual_profile_intent(old_failure):
    result=run(switchRace=True,oldFailure=old_failure)
    assert result['oldResult'] is False
    assert result['after']['profile']=='gamma'
    assert result['after']['defaultWorkspace']=='gamma-root'

@pytest.mark.parametrize('round_trip',[False,True])
def test_automatic_switch_superseded_during_sidebar_render_does_not_retry_old_session(round_trip):
    result=run(switchRenderRace=True,roundTrip=round_trip)
    assert result['oldResult'] is False
    assert result['after']['profile']==('alpha' if round_trip else 'gamma')
    assert result['after']['defaultWorkspace']=='current-root'

@pytest.mark.parametrize('auto_failure',[None,'post','setup'])
def test_automatic_switch_releases_controls_inherited_from_superseded_manual_switch(auto_failure):
    result=run(switchControlRace=True,autoFailure=auto_failure)
    assert result['controls']=={
        'profileChip':{'disabled':False,'switching':False},
        'titlebarProfileBtn':{'disabled':False,'switching':False},
    }
    assert result['label']==result['after']['profile']==('alpha' if auto_failure else 'gamma')

@pytest.mark.parametrize('old_failure',[False,True])
def test_stale_automatic_switch_does_not_release_newer_manual_controls(old_failure):
    result=run(switchRace=True,newerPending=True,oldFailure=old_failure)
    assert result['oldResult'] is False
    assert result['beforeNewer']=={'disabled':True,'switching':True}
    assert result['after']['profile']=='gamma'

@pytest.mark.parametrize('case',[{}, {'profileChange':True},{'sessionChange':True},{'workspaceFailure':True},{'remote':True}])
def test_terminal_command_uses_only_current_authorized_workspace_metadata(case):
    result=run(command=True,**case)
    assert result['calls'].get('toggles',0)==(0 if case else 1)
    if case.get('profileChange') or case.get('workspaceFailure'):
        assert result['backendKnown'] is False

@pytest.mark.parametrize('case',[{}, {'profileChange':True},{'profileChange':True,'roundTrip':True},{'sessionChange':True},{'workspaceFailure':True}])
def test_terminal_module_load_cannot_start_after_scope_or_backend_changes(case):
    result=run(terminalDelay=True,**case)
    assert result['calls'].get('posts',0)==(0 if case else 1)
