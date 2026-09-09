"""Exercise the real scheduler contract at its browser API/editor boundary."""
import io
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from api import routes


@pytest.mark.parametrize('value', ['not-a-cron', '2020-01-01T00:00:00+00:00'])
def test_invalid_editor_schedule_is_400_and_preserves_existing_job(tmp_path, monkeypatch, value):
    import cron.jobs as jobs

    monkeypatch.setattr(jobs, 'CRON_DIR', tmp_path / 'cron')
    monkeypatch.setattr(jobs, 'JOBS_FILE', tmp_path / 'cron' / 'jobs.json')
    monkeypatch.setattr(jobs, 'OUTPUT_DIR', tmp_path / 'cron' / 'output')
    monkeypatch.setattr(jobs, '_compute_provider_model_snapshots', lambda **k: ('qa', 'qa'))
    job = jobs.create_job(prompt='Synthetic editor validation', schedule='every 2h', deliver='local')
    before = jobs.JOBS_FILE.read_bytes()
    handler = SimpleNamespace(status=None, wfile=io.BytesIO())
    handler.send_response = lambda code: setattr(handler, 'status', code)
    handler.send_header = lambda *a: None
    handler.end_headers = lambda: None
    routes._handle_cron_update(handler, {'job_id': job['id'], 'schedule': value, 'name': 'must not persist'})
    assert handler.status == 400
    assert json.loads(handler.wfile.getvalue())['error']
    assert jobs.JOBS_FILE.read_bytes() == before
    assert jobs.get_job(job['id'])['name'] == job['name']


def test_editor_classification_matches_real_engine_and_oneshot_roundtrip_preserves_instant():
    import cron.jobs as jobs

    source = (Path(__file__).resolve().parents[1] / 'static/panels.js').read_text()
    functions = source[source.index('function _cronScheduleKindForInput'):source.index('function _syncCronScheduleWarning')]
    values = ['30m', '2h', 'every 2h', 'in 2h', '2036-05-11T08:30:00+02:00', '27 13 * * 0']
    parsed = [jobs.parse_schedule(value) for value in values]
    script = functions + '\nconst schedules=JSON.parse(process.argv[1]);const inputs=JSON.parse(process.argv[2]);' + \
        '\nconsole.log(JSON.stringify(schedules.map((schedule,i)=>({kind:_cronScheduleKindForInput(inputs[i]),editable:_cronEditableSchedule({schedule,schedule_display:schedule.display})}))));'
    result = subprocess.run(['node', '-e', script, json.dumps(parsed), json.dumps(values)], text=True, capture_output=True, check=True)
    for original, rendered in zip(parsed, json.loads(result.stdout), strict=True):
        assert rendered['kind'] == original['kind']
        reparsed = jobs.parse_schedule(rendered['editable'])
        assert reparsed['kind'] == original['kind']
        if original['kind'] == 'once':
            assert reparsed['run_at'] == original['run_at']
        elif original['kind'] == 'interval':
            assert reparsed['minutes'] == original['minutes']
        else:
            assert reparsed['expr'] == original['expr']
