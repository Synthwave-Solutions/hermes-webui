"""The frontend completion path opts into human work without masking refusals."""
from types import SimpleNamespace

import pytest

from api import kanban_bridge as bridge


def test_frontend_done_uses_structured_manual_completion(monkeypatch):
    calls = []
    task = SimpleNamespace(id="t_manual", status="todo")
    backend = SimpleNamespace(
        get_task=lambda *_: task,
        complete_task=lambda *args, **kwargs: calls.append((args, kwargs)) or True,
    )
    monkeypatch.setattr(bridge, "_kb", lambda: backend)
    conn = object()
    bridge._patch_task(conn, task.id, {"status": "done", "summary": "Human finished"})
    assert calls == [((conn, task.id), {"result": None, "summary": "Human finished", "allow_pending": True})]


def test_existing_dependency_refusal_is_validation_not_missing_task(monkeypatch):
    task = SimpleNamespace(id="t_blocked", status="todo")
    monkeypatch.setattr(bridge, "_kb", lambda: SimpleNamespace(
        get_task=lambda *_: task, complete_task=lambda *args, **kwargs: False,
    ))
    with pytest.raises(ValueError, match="finish its dependencies"):
        bridge._patch_task(object(), task.id, {"status": "done"})


def test_task_removed_during_completion_retains_not_found(monkeypatch):
    task = SimpleNamespace(id="t_removed", status="todo")
    states = iter([task, None])
    monkeypatch.setattr(bridge, "_kb", lambda: SimpleNamespace(
        get_task=lambda *_: next(states), complete_task=lambda *args, **kwargs: False,
    ))
    with pytest.raises(LookupError, match="task not found"):
        bridge._patch_task(object(), task.id, {"status": "done"})


@pytest.mark.parametrize('body, reason', [({'status': 'blocked'}, 'blocked from WebUI'), ({'status': 'blocked', 'block_reason': 'Needs a human'}, 'Needs a human')])
def test_frontend_block_uses_manual_opt_in_and_preserves_reason(monkeypatch, body, reason):
    calls = []
    task = SimpleNamespace(id='t_manual', status='todo')
    monkeypatch.setattr(bridge, '_kb', lambda: SimpleNamespace(
        get_task=lambda *_: task,
        block_task=lambda *args, **kwargs: calls.append(kwargs) or True,
    ))
    bridge._patch_task(object(), task.id, body)
    assert calls == [{'reason': reason, 'allow_todo': True}]


def test_existing_invalid_block_is_validation_not_missing_task(monkeypatch):
    task = SimpleNamespace(id='t_done', status='done')
    monkeypatch.setattr(bridge, '_kb', lambda: SimpleNamespace(
        get_task=lambda *_: task, block_task=lambda *args, **kwargs: False,
    ))
    with pytest.raises(ValueError, match='cannot be blocked'):
        bridge._patch_task(object(), task.id, {'status': 'blocked'})
