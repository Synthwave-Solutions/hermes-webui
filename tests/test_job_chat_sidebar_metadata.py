"""Job provenance must survive the bounded API payload and the chat filter."""
import json
from pathlib import Path
import subprocess

from api import routes
from api.models import Session

ROOT = Path(__file__).resolve().parents[1]


def test_job_chat_survives_sidebar_serialization_and_filter(monkeypatch):
    monkeypatch.setattr(routes, '_session_attention_summary', lambda sid: {'kind': 'none'})
    # Same persisted shape as the reported VPS job; source is unset, not 'cron'.
    job = Session(session_id='job_chat', title='🗓️ vps · catch-up na reset · every 10 min',
                  cron_job={'job_id': '05bdbadc5bf0', 'profile': 'default'},
                  messages=[{'role': 'assistant', 'content': 'Result'}])
    ordinary = Session(session_id='human_chat', title=job.title,
                       messages=[{'role': 'user', 'content': 'Explain this job'}])
    rows = [routes._sidebar_session_response_item(s.compact(), redact_enabled=False)
            for s in [job, ordinary, Session(session_id="scout_chat", cron_job={"job_id":"s1","profile":"cfo","kind":"scout"})]]
    assert rows[0].get('cron_job') == {'job_id': '05bdbadc5bf0', 'profile': 'default'}
    assert 'cron_job' not in rows[1]
    js = (ROOT / 'static/sessions.js').read_text()
    helpers = js[js.index('function _isJobChatSession('):js.index('function setSessionKindFilter(')]
    result = subprocess.run(['node', '-e', helpers + '''
let _sessionKindFilter='chats';
const rows=JSON.parse(process.argv[1]);
const chats=rows.filter(s=>_sessionKindMatches(s,null)).map(s=>s.session_id);
_sessionKindFilter='jobs';
const jobs=rows.filter(s=>_sessionKindMatches(s,null)).map(s=>s.session_id);
_sessionKindFilter='all';
const all=rows.filter(s=>_sessionKindMatches(s,null)).map(s=>s.session_id);
console.log(JSON.stringify({chats,jobs,all}));
''', json.dumps(rows)], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {'chats': ['human_chat', 'scout_chat'], 'jobs': ['job_chat'],
                                        'all': ['job_chat', 'human_chat', 'scout_chat']}


def test_sidebar_job_link_is_bounded_and_invalid_link_is_omitted(monkeypatch):
    monkeypatch.setattr(routes, '_session_attention_summary', lambda sid: {'kind': 'none'})
    row = {'session_id': 'job_chat', 'cron_job': {'job_id': 'j1', 'profile': 'cfo',
                                               'prompt': 'private prompt'}}
    assert routes._sidebar_session_response_item(row)['cron_job'] == {'job_id': 'j1', 'profile': 'cfo'}
    row['cron_job'] = {'profile': 'cfo'}
    assert 'cron_job' not in routes._sidebar_session_response_item(row)
