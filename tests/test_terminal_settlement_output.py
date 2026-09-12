"""Actual anchor event projection must retain completed output at settlement."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(not NODE, reason='node unavailable')


def event(kind, tid='call-1', **fields):
    return dict(source_event_type=kind, tid=tid, name='terminal',
                args={'command': 'printf fixture'}, **fields)


def run(events, **kwargs):
    payload = dict(events=[dict(e, local_id=f'live-event-{i}', created_at=i+1)
                           for i, e in enumerate(events)], **kwargs)
    result = subprocess.run([NODE, str(ROOT / 'tests/terminal_settlement_driver.cjs')],
                            input=json.dumps(payload), text=True, capture_output=True,
                            timeout=20, check=True)
    return json.loads(result.stdout)


@pytest.mark.parametrize('persisted', [False, True])
@pytest.mark.parametrize('mode', ['transparent_stream', 'compact_worklog'])
def test_actual_registry_start_complete_done_keeps_rendered_output(persisted, mode):
    finished = event('tool_complete', snippet='fixture stdout', preview='fixture stdout', done=True)
    kwargs = {}
    if persisted:
        kwargs['messages'] = [{'role':'user', 'content':'Run fixture'},
                              {'role':'assistant', 'content':'Final answer',
                               'tool_calls':[dict(finished, id='call-1')]}]
    result = run([event('tool', snippet='', done=False), finished, event('done')], mode=mode, **kwargs)
    projected_tools = [r for r in result['projected']['activity_rows'] if r['role'] == 'tool']
    assert [r['tool']['snippet'] for r in projected_tools] == ['', 'fixture stdout']
    assert len(result['cards']) == 1
    card = result['cards'][0]
    assert 'class="tool-card-result"' in card['html']
    assert '<pre>fixture stdout</pre>' in card['html']
    assert card['tc']['snippet'] == 'fixture stdout'
    assert card['row']['row_id'] == projected_tools[0]['row_id']
    assert card['row']['order_index'] == 0
    assert result['projectionUnchanged']


def test_completed_error_survives_stale_start_and_persisted_duplicate():
    output = '<img src=x onerror="bad()"> fixture error'
    failed = event('tool_complete', snippet=output, preview=output, done=True, is_error=True)
    result = run([event('tool', snippet='', done=False), failed,
                  event('tool', snippet='stale output', done=False), event('done')],
                 messages=[{'role':'user','content':'Run fixture'},
                           {'role':'assistant','content':'Final answer',
                            'tool_calls':[dict(failed, id='call-1')]}])
    assert len(result['cards']) == 1
    card = result['cards'][0]
    assert card['tc']['is_error'] is True
    assert card['tc']['snippet'] == output
    assert '&lt;img' in card['html'] and '<img' not in card['html']


def test_terminal_empty_result_clears_prior_preview_instead_of_resurrecting_it():
    result = run([event('tool', snippet='stale output', preview='stale output', done=False),
                  event('tool_complete', snippet='', preview='', done=True), event('done')])
    card = result['cards'][0]
    assert card['tc']['snippet'] == ''
    assert card['tc']['preview'] == ''
    assert 'class="tool-card-result"' not in card['html']


def test_two_calls_with_equal_output_keep_distinct_identity_and_chronology():
    result = run([event('tool', tid='one', snippet='', done=False),
                  event('tool', tid='two', snippet='', done=False),
                  event('tool_complete', tid='two', snippet='same stdout', done=True),
                  event('tool_complete', tid='one', snippet='same stdout', done=True), event('done')])
    assert [c['tc']['id'] for c in result['cards']] == ['one', 'two']
    assert [c['tc']['snippet'] for c in result['cards']] == ['same stdout', 'same stdout']


def test_repeated_terminal_event_is_idempotent_and_retains_result():
    complete = event('tool_complete', snippet='fixture stdout', done=True)
    result = run([event('tool', snippet='', done=False), complete, complete, event('done')])
    assert len(result['cards']) == 1
    assert result['cards'][0]['tc']['snippet'] == 'fixture stdout'


@pytest.mark.parametrize('is_error', [False, True])
def test_persisted_completion_supplies_body_and_error_when_live_completion_missing(is_error):
    result = run([event('tool', snippet='', done=False), event('done')],
                 messages=[{'role':'user','content':'Run fixture'},
                           {'role':'assistant','content':'Final answer',
                            'tool_calls':[{'id':'call-1','name':'terminal',
                                           'args':{'command':'printf fixture'},
                                           'snippet':'saved output','is_error':is_error}]}])
    assert result['cards'][0]['tc']['snippet'] == 'saved output'
    assert result['cards'][0]['tc']['is_error'] is is_error
    assert result['cards'][0]['tc']['args'] == {'command':'printf fixture'}


def test_later_empty_completion_replaces_all_prior_output_aliases():
    result = run([event('tool_complete', snippet='stale', preview='stale',
                       result='stale', output='stale', done=True),
                  event('tool_complete', snippet='', preview='', done=True), event('done')],
                 messages=[{'role':'user','content':'Run fixture'},
                           {'role':'assistant','content':'Final answer',
                            'tool_calls':[{'id':'call-1','name':'terminal','snippet':'stale'}]}])
    card = result['cards'][0]
    assert card['tc']['snippet'] == ''
    assert card['tc']['preview'] == ''
    assert 'stale' not in card['html']


def test_cancelled_completion_retains_observed_status():
    result = run([event('tool', done=False),
                  event('tool_complete', snippet='Cancelled by user', status='cancelled', done=True),
                  event('done')])
    card = result['cards'][0]
    assert card['row']['status'] == 'cancelled'
    assert card['tc']['snippet'] == 'Cancelled by user'


def test_empty_anonymous_duplicate_does_not_borrow_another_tools_result():
    extra = [dict(role='tool', row_id='anonymous-same', kind='tool_started', status='running',
                  tool={'name':'terminal','args':{'command':'first'},'snippet':''}),
             dict(role='tool', row_id='anonymous-same', kind='tool_completed', status='completed',
                  tool={'name':'terminal','args':{'command':'second'},'snippet':'foreign output'})]
    result = run([event('done')], extraRows=extra)
    assert len(result['cards']) == 1
    assert result['cards'][0]['tc']['snippet'] == ''


def test_long_completion_uses_existing_bounded_preview_and_full_output_control():
    output = 'fixture line\n' * 500
    result = run([event('tool', done=False), event('tool_complete', snippet=output, done=True), event('done')])
    card = result['cards'][0]
    assert card['tc']['snippet'] == output
    assert 'class="tool-card-more"' in card['html']
    assert 'data-full="' + output in card['html']


def test_live_completion_without_invocation_metadata_keeps_original_input():
    result = run([event('tool', done=False),
                  {'source_event_type':'tool_complete','tid':'call-1','name':'terminal',
                   'snippet':'fixture stdout','done':True}, event('done')])
    assert result['cards'][0]['tc']['args'] == {'command':'printf fixture'}


def test_derived_completion_rank_does_not_change_with_preserved_live_row_identity():
    # This recovery shape carries two derived snapshots for one explicit call.
    # Both rank below a real live completion despite retaining the live row ID.
    def derived(text):
        return dict(role='tool', row_id='settled:call-1', tool_call_id='call-1',
                    kind='tool_completed', source_event_type='tool_complete', status='completed',
                    group={'assistant_msg_idx':1},
                    tool={'id':'call-1','name':'terminal','snippet':text,'done':True})
    result = run([event('tool', done=False), event('done')],
                 extraRows=[derived('older'), derived('newer')])
    assert len(result['cards']) == 1
    assert result['cards'][0]['tc']['snippet'] == 'newer'
    assert result['cards'][0]['row']['row_id'].startswith('live-event-0')


def test_observed_live_wire_preview_passes_actual_callback_adapter_and_settlement():
    # Production tool_complete has preview:str, args:dict, tid:str,
    # is_error:bool, but no snippet/done. The actual upsert and anchor adapter
    # must provide those fields before the registry, exactly as live handlers do.
    result = run([event('tool', preview=None),
                  event('tool_complete', preview='fixture stdout', is_error=False),
                  event('done')], wire=True)
    assert len(result['cards']) == 1
    assert result['cards'][0]['tc']['snippet'] == 'fixture stdout'
    assert 'class="tool-card-result"' in result['cards'][0]['html']
    assert result['cards'][0]['row']['row_id'].startswith('fixture-stream:1')
    assert [r['tool']['done'] for r in result['projected']['activity_rows'] if r['role']=='tool'] == [False, True]
