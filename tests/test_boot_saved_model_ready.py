"""A delayed catalog must not gate a restored, explicitly routed conversation."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(not NODE, reason='node unavailable')


def run(**scenario):
    result = subprocess.run([NODE, str(ROOT/'tests/boot_saved_model_driver.cjs'),
                             str(ROOT), json.dumps(scenario)],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_saved_explicit_route_is_usable_before_catalog_resolves():
    result = run()
    first = result['beforeCatalog']
    assert first['visible']['transcript'] == 'Saved conversation'
    assert first['ready'] is True
    assert first['visible']['botsDisabled'] is False
    assert first['visible']['label']
    assert first['selected'] == {'model':'codex/gpt-6-astra','model_provider':'custom:omniroute'}
    assert first['outgoing'] == first['selected']
    assert first['calls']['models'] == 1
    assert result['afterCatalog']['selected'] == first['selected']
    assert result['afterCatalog']['outgoing'] == first['outgoing']
    assert result['afterCatalog']['calls']['mutation'] == 0


def test_catalog_failure_keeps_ready_conversation_and_exact_model():
    result = run(failure=True)
    assert result['beforeCatalog']['ready'] is True
    assert result['afterCatalog']['selected'] == {'model':'codex/gpt-6-astra','model_provider':'custom:omniroute'}
    assert result['afterCatalog']['visible']['transcript'] == 'Saved conversation'


def test_partial_catalog_cannot_replace_explicit_route_with_native_suffix():
    result = run(omitCustom=True)
    for phase in ['beforeCatalog', 'afterCatalog']:
        assert result[phase]['selected'] == {'model':'codex/gpt-6-astra','model_provider':'custom:omniroute'}
        assert result[phase]['outgoing'] == result[phase]['selected']
        assert result[phase]['calls']['mutation'] == 0


def test_same_model_value_in_two_providers_keeps_custom_provider():
    result = run(session={'model':'gpt-6-astra'}, catalogModel='gpt-6-astra')
    for phase in ['beforeCatalog', 'afterCatalog']:
        assert result[phase]['selected'] == {'model':'gpt-6-astra','model_provider':'custom:omniroute'}
        assert result[phase]['outgoing'] == result[phase]['selected']


def test_provider_qualified_saved_model_is_primed_without_losing_route():
    result = run(session={'model':'@custom:omniroute:codex/gpt-6-astra'})
    assert result['beforeCatalog']['ready'] is True
    assert result['beforeCatalog']['selected'] == {'model':'codex/gpt-6-astra','model_provider':'custom:omniroute'}
    assert result['afterCatalog']['selected'] == result['beforeCatalog']['selected']
    for phase in ['beforeCatalog', 'afterCatalog']:
        assert result[phase]['outgoing'] == {'model':'@custom:omniroute:codex/gpt-6-astra','model_provider':'custom:omniroute'}


def test_explicit_same_session_pick_survives_late_catalog_in_send_payload():
    result = run(pick=True)
    assert result['beforeCatalog']['ready'] is True
    latest=result['afterCatalog']
    assert latest['session']['session_id'] == 'saved'
    assert latest['selected'] == {'model':'chosen-model','model_provider':'custom:chosen'}
    assert latest['outgoing'] == latest['selected']
    assert latest['calls']['explicitUpdates'] == 1
    assert latest['calls']['mutation'] == 0


def test_late_catalog_applies_newer_conversation_not_old_saved_route():
    result = run(navigate='another-profile')
    assert result['beforeCatalog']['ready'] is True
    assert result['afterCatalog']['session']['session_id'] == 'newer'
    assert result['afterCatalog']['selected'] == {'model':'another-model','model_provider':'custom:second'}
    assert result['afterCatalog']['outgoing'] == result['afterCatalog']['selected']


@pytest.mark.parametrize('session', [{'model':''}, {'model':'unknown'}, {'model_provider':None}])
def test_unresolved_session_keeps_existing_catalog_gate(session):
    result = run(session=session)
    assert result['beforeCatalog']['ready'] is False
    assert result['afterCatalog']['ready'] is True
