"""Project creation retry contract through the real authenticated dispatcher."""
from tests import test_project_collaboration
from tests.test_project_collaboration import create, OWNER, MEMBER, OUTSIDER

# Reuse the isolated fixture without shadowing an imported name in test signatures.
client = test_project_collaboration.client

KEY = 'e478cb80-6744-40de-804c-3247a6a08a45'


def test_retry_reuses_persisted_chat_after_cache_loss_and_rechecks_membership(client):
    from api import models
    p = create(client)
    body = {'project_id': p['project_id'], 'request_id': KEY, 'bot_participants': ['writer']}
    status, first = client(MEMBER, '/api/projects/chat', body)
    assert status == 200, first
    sid = first['session']['session_id']
    chat = models.get_session(sid)
    chat.messages = [{'role': 'user', 'content': 'Already sent'}]
    chat.save()
    with models.LOCK:
        models.SESSIONS.pop(sid, None)
    status, second = client(MEMBER, '/api/projects/chat', body)
    assert status == 200, second
    assert second['session']['session_id'] == sid
    assert models.Session.load(sid).messages[0]['content'] == 'Already sent'
    assert client(OUTSIDER, '/api/projects/chat', body)[0] == 404
    assert client(OWNER, '/api/projects/team', {'project_id': p['project_id'], 'revision': p['revision'], 'members': []})[0] == 200
    assert client(MEMBER, '/api/projects/chat', body)[0] == 404


def test_key_is_actor_project_scoped_and_does_not_accept_conflicting_bot_selection(client):
    p = create(client)
    body = {'project_id': p['project_id'], 'request_id': KEY, 'bot_participants': ['writer']}
    a = client(OWNER, '/api/projects/chat', body)[1]['session']['session_id']
    b = client(MEMBER, '/api/projects/chat', body)[1]['session']['session_id']
    assert a != b
    assert client(OWNER, '/api/projects/chat', body)[1]['session']['session_id'] == a
    other = create(client)
    assert client(OWNER, '/api/projects/chat', {**body, 'project_id': other['project_id']})[1]['session']['session_id'] != a
    for key in ['../../oops', 123, 'x' * 200]:
        assert client(OWNER, '/api/projects/chat', {**body, 'request_id': key})[0] == 400


def test_retry_after_failed_first_save_does_not_create_second_session(client, monkeypatch):
    from api import models
    p = create(client)
    body = {'project_id': p['project_id'], 'request_id': KEY}
    original = models.Session.save
    failed_ids = []
    def fail_once(self, *args, **kwargs):
        if not failed_ids:
            failed_ids.append(self.session_id)
            raise OSError('isolated write failure')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(models.Session, 'save', fail_once)
    assert client(OWNER, '/api/projects/chat', body)[0] == 400
    status, result = client(OWNER, '/api/projects/chat', body)
    assert status == 200, result
    assert result['session']['session_id'] == failed_ids[0]
    assert models.Session.load(failed_ids[0]).project_shared is True


def test_replay_rejects_changed_persisted_ownership_and_does_not_overwrite(client):
    from api import models
    p = create(client)
    body = {'project_id': p['project_id'], 'request_id': KEY}
    _, first = client(OWNER, '/api/projects/chat', body)
    sid = first['session']['session_id']
    chat = models.get_session(sid)
    chat.owner_email = OUTSIDER
    chat.save()
    assert client(OWNER, '/api/projects/chat', body)[0] == 409
    assert models.Session.load(sid).owner_email == OUTSIDER


def test_sidebar_new_chat_uses_shared_project_flow():
    import json
    import shutil
    import pytest
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    # Reuse the neighboring newSession VM scene, executing the real function.
    source = (root / 'tests/test_4676_project_new_session_shortcuts.py').read_text()
    driver = source.split('_DRIVER = r"""', 1)[1].split('"""', 1)[0]
    driver = driver.replace("eval(newSessionSrc);", """
    globalThis._allProjects = [{project_id:'team', collaboration:true}];
    globalThis._projStartSharedConversation = async id => { calls.push({sharedProject:id}); };
    eval(newSessionSrc);
    """)
    node = shutil.which('node')
    if not node:
        pytest.skip('node is required for the frontend scene')
    result = subprocess.run([node, '-e', driver, str(root/'static/sessions.js'), json.dumps({'activeProject':'team','options':{},'session':{'session_id':'private-chat'}})], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)['body'] == {'sharedProject':'team'}


def test_concurrent_identical_requests_commit_one_session(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from types import SimpleNamespace
    from api import models, project_collaboration
    p = create(client)
    body = {'project_id': p['project_id'], 'request_id': KEY}
    handler = SimpleNamespace(headers={'Cookie': OWNER})
    started, release = Event(), Event()
    saved = []
    original = models.Session.save
    def delayed_save(self, *args, **kwargs):
        saved.append(self.session_id)
        started.set()
        assert release.wait(5)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(models.Session, 'save', delayed_save)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(project_collaboration.handle, handler, '/api/projects/chat', body)
        assert started.wait(5)
        b = pool.submit(project_collaboration.handle, handler, '/api/projects/chat', body)
        release.set()
        assert a.result(timeout=5)['session']['session_id'] == b.result(timeout=5)['session']['session_id']
    assert len(saved) == 1


def test_deleted_retry_never_resurrects_conversation(client):
    from api import models
    p = create(client)
    body = {'project_id': p['project_id'], 'request_id': KEY}
    sid = client(OWNER, '/api/projects/chat', body)[1]['session']['session_id']
    models._record_webui_deleted_session_tombstone(sid)
    models.get_session(sid).path.unlink()
    with models.LOCK:
        models.SESSIONS.pop(sid, None)
    assert client(OWNER, '/api/projects/chat', body)[0] == 409
    assert not (models.SESSION_DIR / (sid + '.json')).exists()


def test_failed_save_returns_safe_correlated_error(client, monkeypatch, caplog):
    from api import models
    p = create(client)
    def fail(*args, **kwargs):
        raise OSError('/private/path/to/credential-must-not-leak')
    monkeypatch.setattr(models.Session, 'save', fail)
    status, result = client(OWNER, '/api/projects/chat', {'project_id':p['project_id'], 'request_id':KEY})
    assert status == 400
    assert result['reference'] == KEY
    assert 'credential-must-not-leak' not in str(result) + caplog.text
    assert 'category=storage_failed' in caplog.text and 'reference=' + KEY in caplog.text


def test_delete_cannot_interleave_between_retry_snapshot_and_persistence(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, current_thread
    from types import SimpleNamespace
    from api import models, routes, project_collaboration
    p = create(client)
    body = {'project_id':p['project_id'], 'request_id':KEY}
    sid = client(OWNER, '/api/projects/chat', body)[1]['session']['session_id']
    with models.LOCK:
        models.SESSIONS.pop(sid, None)
    snapshot, release, delete_entered = Event(), Event(), Event()
    original = models._load_webui_deleted_session_tombstone
    def held_snapshot():
        found = original()
        if current_thread().name.startswith('retry'):
            snapshot.set()
            assert release.wait(5)
        return found
    monkeypatch.setattr(models, '_load_webui_deleted_session_tombstone', held_snapshot)
    monkeypatch.setattr(routes, 'SESSION_DIR', models.SESSION_DIR)
    original_cache = models.SESSIONS
    class ObservedCache(dict):
        def pop(self, *args, **kwargs):
            delete_entered.set()
            return original_cache.pop(*args, **kwargs)
    monkeypatch.setattr(routes, 'SESSIONS', ObservedCache(original_cache))
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix='retry') as retrier, ThreadPoolExecutor(max_workers=1) as deleter:
        pending = retrier.submit(project_collaboration.handle, SimpleNamespace(headers={'Cookie':OWNER}), '/api/projects/chat', body)
        assert snapshot.wait(5)
        deletion = deleter.submit(client, OWNER, '/api/session/delete', {'session_id':sid})
        try:
            assert not delete_entered.wait(0.2), 'Delete entered during the creation transaction'
        finally:
            release.set()
        pending.result(timeout=5)
        assert deletion.result(timeout=5)[0] == 200
    assert not (models.SESSION_DIR / (sid + '.json')).exists()


def test_uncertain_runtime_failure_keeps_retry_reference(client, monkeypatch):
    from api import models
    p = create(client)
    def failure(*args, **kwargs):
        raise RuntimeError('private-internal-state')
    monkeypatch.setattr(models.Session, 'save', failure)
    status, result = client(OWNER, '/api/projects/chat', {'project_id':p['project_id'], 'request_id':KEY})
    assert status == 409 and result['code'] != 'project_creation_conflict'
    assert result['reference'] == KEY
    assert 'private-internal-state' not in str(result)


def test_shared_creation_javascript_lifecycle():
    import shutil
    import subprocess
    from pathlib import Path
    import pytest
    node = shutil.which('node')
    if not node:
        pytest.skip('node is required for frontend behavior')
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([node, 'tests/project_conversation_logic.cjs'], cwd=root, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr


def test_explicit_session_registration_is_atomic(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from api import models
    original = models.Session
    ready = Barrier(2)
    def constructing(*args, **kwargs):
        session = original(*args, **kwargs)
        ready.wait(timeout=5)
        return session
    monkeypatch.setattr(models, 'Session', constructing)
    def reserve():
        try:
            return models.new_session(workspace=str(client.tmp), model='fixture', profile='writer', session_id='reserved-server-id')
        except FileExistsError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(lambda _:reserve(), range(2)))
    successes=[s for s in outcomes if s is not None]
    assert len(successes) == 1
    assert models.SESSIONS['reserved-server-id'] is successes[0]


def test_slow_agent_eviction_does_not_block_other_project_work(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from types import SimpleNamespace
    from api import config, models, routes, project_collaboration
    p=create(client)
    sid=client(OWNER, '/api/projects/chat', {'project_id':p['project_id'], 'request_id':KEY})[1]['session']['session_id']
    started, release=Event(), Event()
    def stalled_eviction(*args, **kwargs):
        started.set()
        assert release.wait(5)
    monkeypatch.setattr(config, '_evict_session_agent', stalled_eviction)
    monkeypatch.setattr(routes, 'SESSION_DIR', models.SESSION_DIR)
    with ThreadPoolExecutor(max_workers=2) as pool:
        deleting=pool.submit(client, OWNER, '/api/session/delete', {'session_id':sid})
        assert started.wait(5)
        reading=pool.submit(project_collaboration.handle, SimpleNamespace(headers={'Cookie':OWNER}), '/api/projects/files', None, {'project_id':[p['project_id']]})
        try:
            assert reading.result(timeout=1) == {'files':[]}
        finally:
            release.set()
        assert deleting.result(timeout=5)[0] == 200
    assert not (models.SESSION_DIR / (sid + '.json')).exists()
