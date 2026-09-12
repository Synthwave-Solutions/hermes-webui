"""Run the actual lifecycle bridge against terminal and recoverable events."""
import ast
import inspect

import pytest

from api import streaming


def bridge():
    tree = ast.parse(inspect.getsource(streaming))
    node = next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == '_agent_status_callback')
    events, captured = [], [None]
    namespace = dict(vars(streaming), session_id='test-session',
                     put=lambda *args: events.append(args),
                     _captured_terminal_error=captured)
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<actual lifecycle bridge>', 'exec'), namespace)
    return namespace['_agent_status_callback'], events, captured


@pytest.mark.parametrize('message,expected', [
    ('❌ Non-retryable error (HTTP 400): invalid model', 'model_not_found'),
    ('❌ Non-retryable error (HTTP 401): invalid api key', 'auth_mismatch'),
    ('❌ Rate limited after 3 retries — HTTP 429', 'rate_limit'),
    ('❌ API failed after 3 retries — connection reset', 'error'),
])
def test_terminal_cause_survives_actual_bridge(message, expected):
    callback, events, captured = bridge()
    callback('lifecycle', message)
    assert captured[0] == message
    assert not events  # No raw error warning before final classification/redaction.
    assert streaming._classify_provider_error(captured[0])['type'] == expected


@pytest.mark.parametrize('kind,message', [
    ('lifecycle', '⚠️ Non-retryable error (HTTP 400) — trying fallback...'),
    ('lifecycle', 'API call started'),
    ('tool', '❌ Non-retryable error (HTTP 401): invalid api key'),
    ('lifecycle', 'Example text: ❌ Non-retryable error (HTTP 400): invalid model'),
])
def test_progress_or_tool_text_is_not_terminal(kind, message):
    callback, events, captured = bridge()
    callback(kind, message)
    assert captured == [None]


def test_unknown_empty_failure_does_not_invent_capacity_cause():
    result = streaming._classify_provider_error('', silent_failure=True)
    assert result['type'] == 'no_response'
    assert 'capacity' not in result['hint'].lower()
    assert 'cause' in result['hint'].lower()


def test_synthetic_failure_message_has_no_fabricated_provider_details():
    payload = streaming._provider_error_payload(
        'The run ended without a final answer.', 'no_response',
        provider_details=False,
    )
    assert payload['message'] == 'The run ended without a final answer.'
    assert 'details' not in payload


def test_terminal_capture_is_bounded_and_redacted(monkeypatch):
    monkeypatch.setattr(streaming, '_redact_text', lambda text: text.replace('SECRET', '[REDACTED]'))
    callback, events, captured = bridge()
    message = '❌ API failed after 3 retries — SECRET ' + 'x' * 20000
    callback('lifecycle', message)
    assert len(captured[0]) <= 4000
    assert 'SECRET' not in captured[0]
    assert '[REDACTED]' in captured[0]
