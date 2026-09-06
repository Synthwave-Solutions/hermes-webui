from api.grant_requests import _operation_payloads


def test_operation_passthrough_is_scoped_and_whitelisted():
    op = {"version": 1, "operation_id": "id", "actor_email": "u@example.test", "gkind": "skill", "value": "example", "binding_status": "bound", "session_id": "session", "request_id": "run", "tool_call_id": "call", "policy": {"token": "private"}}
    result = _operation_payloads({"operations": {"id": op}}, "u@example.test", "skill", "example")
    assert result["id"]["session_id"] == "session"
    assert "policy" not in result["id"]
    assert _operation_payloads({"operations": {"id": op}}, "other@example.test", "skill", "example") == {}
    assert _operation_payloads({}, "u@example.test", "skill", "example") == {}
