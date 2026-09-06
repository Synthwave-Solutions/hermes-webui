from types import SimpleNamespace
import pytest
from api import run_journal, session_ops


@pytest.mark.parametrize('event,payload,status', [
    ('done', {}, 'completed'), ('apperror', {}, 'failed'),
    ('cancel', {}, 'canceled'), ('done', {'terminal_state':'tool_limit_reached'}, 'waiting'),
    ('stream_end', {}, 'failed'),
])
def test_durable_outcome_survives_transport_close(tmp_path, monkeypatch, event, payload, status):
    monkeypatch.setattr(run_journal, '_default_session_dir', lambda: tmp_path)
    run_journal.append_run_event('s', 'r', event, payload)
    run_journal.append_run_event('s', 'r', 'stream_end', {})
    s=SimpleNamespace(session_id='s', active_stream_id=None, pending_started_at=None)
    assert session_ops.session_progress(s)['status'] == status


def test_newest_started_run_wins_not_late_old_update(tmp_path, monkeypatch):
    monkeypatch.setattr(run_journal, '_default_session_dir', lambda: tmp_path)
    run_journal.append_run_event('s','old','done',{},created_at=1)
    run_journal.append_run_event('s','new','cancel',{},created_at=2)
    run_journal.append_run_event('s','old','stream_end',{},created_at=3)
    s=SimpleNamespace(session_id='s', active_stream_id=None, pending_started_at=None)
    assert session_ops.session_progress(s)['run_id'] == 'new'


def test_live_waiting_queued_and_lost_worker(tmp_path, monkeypatch):
    monkeypatch.setattr(run_journal, '_default_session_dir', lambda: tmp_path)
    s=SimpleNamespace(session_id='s', active_stream_id='r', pending_started_at=1)
    monkeypatch.setattr(session_ops, '_live_active_stream_id', lambda s: 'r')
    assert session_ops.session_progress(s)['status'] == 'running'
    assert session_ops.session_progress(s, attention={'kind':'approval'})['status'] == 'waiting'
    monkeypatch.setattr(session_ops, '_live_active_stream_id', lambda s: None)
    run_journal.append_run_event('s','r','token',{'text':'unfinished'})
    assert session_ops.session_progress(s)['status'] == 'failed'
    s.session_id='new'; s.active_stream_id=None
    assert session_ops.session_progress(s)['status'] == 'queued'


def test_frontend_projects_status_and_ignores_old_session_response():
    import pathlib, subprocess
    root=pathlib.Path(__file__).resolve().parents[1]
    source=(root/'static/ui.js').read_text()
    helper=source[source.index('let _progressPollTimer ='):source.index('function renderMessages(options)')]
    script=r'''
const assert=require('assert');
let row=null, response={progress:{status:'completed'}}, resolve;
const inner={parentNode:{insertBefore(e){row=e}}};
const $=id=>id==='msgInner'?inner:row;
const document={createElement(){return {style:{},dataset:{},setAttribute(){},removeAttribute(){}}}};
const S={session:{session_id:'first'}};
const t=x=>x;
let api=()=>Promise.resolve(response);
''' + helper + r'''
(async()=>{
 for(const status of ['queued','running','waiting','completed','failed','canceled']){
  response={progress:{status}}; _refreshSessionProgress();
  await new Promise(r=>setImmediate(r));
  assert.equal(row.dataset.progressState,status);
 }
 api=()=>new Promise(r=>resolve=r);
 _refreshSessionProgress(); S.session={session_id:'second'}; _refreshSessionProgress();
 resolve({progress:{status:'failed'}});
 await new Promise(r=>setImmediate(r));
 assert.equal(row.textContent,'');
})().catch(e=>{console.error(e);process.exit(1)});
'''
    result=subprocess.run(['node','-e',script],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
