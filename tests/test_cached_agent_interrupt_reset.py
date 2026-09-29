"""Cached initialization cancellation must not become a successor's Stop."""
import ast
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from api.streaming import _clear_cached_agent_interrupt


def test_cached_reset_uses_complete_engine_contract():
    from run_agent import AIAgent

    # The real engine methods also clear redirect, hard-stop, and tool-thread
    # signals. Build only their required state, without contacting a provider.
    agent = object.__new__(AIAgent)
    agent._execution_thread_id = None
    agent._interrupt_requested = True
    agent._interrupt_message = 'old turn'
    agent._tool_interrupt_reason = 'old tool'
    agent._interrupt_thread_signal_pending = True
    agent._hard_interrupt_requested = threading.Event()
    agent._hard_interrupt_requested.set()
    agent._pending_redirect = {'text': 'old redirect'}
    agent._pending_steer = []
    agent._pending_steer_lock = threading.Lock()
    assert _clear_cached_agent_interrupt(agent) is True
    assert agent._interrupt_requested is False
    assert agent._interrupt_message is None
    assert agent._tool_interrupt_reason is None
    assert agent._interrupt_thread_signal_pending is False
    assert not agent._hard_interrupt_requested.is_set()
    assert agent._pending_redirect is None


@pytest.mark.parametrize('clear', [None, False, Mock(return_value=False),
                                 Mock(side_effect=RuntimeError('broken reset'))])
def test_cached_agent_without_working_reset_is_rebuilt(clear):
    assert _clear_cached_agent_interrupt(SimpleNamespace(clear_interrupt=clear)) is False


@pytest.mark.parametrize('cancelled', [False, True])
def test_registration_uses_retained_event_after_eager_map_removal(cancelled):
    """Execute the actual worker registration block with an already-popped map."""
    source = Path(__file__).resolve().parents[1] / 'api' / 'streaming.py'
    tree = ast.parse(source.read_text())
    block = next(node for node in ast.walk(tree) if isinstance(node, ast.With)
                 and any(isinstance(child, ast.Assign)
                         and any(isinstance(target, ast.Subscript)
                                 and isinstance(target.value, ast.Name)
                                 and target.value.id == 'AGENT_INSTANCES'
                                 for target in child.targets)
                         for child in node.body)
                 and any(isinstance(child, ast.If) for child in node.body))
    function = ast.FunctionDef(name='register', args=ast.arguments(
        posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=[block, ast.Return(value=ast.Constant('admitted'))], decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    event = threading.Event()
    if cancelled:
        event.set()
    agent = SimpleNamespace(interrupt=Mock())
    finalize = Mock()
    put = Mock()
    namespace = dict(STREAMS_LOCK=threading.Lock(), AGENT_INSTANCES={}, CANCEL_FLAGS={},
                     stream_id='new', agent=agent, cancel_event=event, _agent_lock=threading.Lock(),
                     _finalize_cancelled_turn=finalize, s=object(), ephemeral=False,
                     put=put, _cancel_event_payload=lambda value: value, logger=Mock())
    exec(compile(module, str(source), 'exec'), namespace)
    result = namespace['register']()
    if cancelled:
        assert result is None
        agent.interrupt.assert_called_once_with('Cancelled before start')
        finalize.assert_called_once()
        put.assert_called_once_with('cancel', 'Cancelled by user')
    else:
        assert result == 'admitted'
        agent.interrupt.assert_not_called()
        finalize.assert_not_called()
        put.assert_not_called()
