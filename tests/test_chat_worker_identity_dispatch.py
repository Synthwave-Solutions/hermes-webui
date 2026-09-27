"""Execute the real worker-selection block with its complete call context."""
import ast
import inspect
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("gateway,group", [(True, False), (True, True), (False, False)])
@pytest.mark.parametrize("authenticated", [True, False, "auth_disabled"])
@pytest.mark.parametrize("managed", [True, False])
@pytest.mark.parametrize("continuation_ref", [None, "a" * 32], ids=["ordinary", "continuation"])
def test_actual_worker_dispatch_keywords_match_original_sender(
    gateway, group, authenticated, managed, continuation_ref,
):
    from api import gateway_chat, routes, streaming

    dispatch = routes._start_chat_stream_for_session
    tree = ast.parse(inspect.getsource(dispatch))
    body = tree.body[0].body

    def assign_index(name, after=0):
        return next(i for i, node in enumerate(body[after:], after) if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == name
                            for target in node.targets))

    # The backend is decided once, before the stale-runtime barrier and before
    # any pending state is registered, so the barrier and the dispatch act on
    # the same value. Execute the real statements in order: resolving the
    # gateway setting, the governed backend decision, and the worker dispatch.
    resolve = next(i for i, node in enumerate(body) if isinstance(node, ast.If)
                   and "external_runtime_owned is None" in ast.unparse(node.test))
    decision = assign_index("backend_is_gateway")
    start = assign_index("worker_target", decision)
    end = assign_index("thr", start)
    captured = {}

    def thread(**kwargs):
        # Keep validating both real worker signatures; no permissive stand-in
        # can accept a misspelled or unsupported security-context keyword.
        inspect.signature(kwargs["target"]).bind(*kwargs["args"], **kwargs["kwargs"])
        captured.update(kwargs)

    identity = {"email": "sender@example.test", "groups": ["original-sso-group"]}
    turn_identity = ({"email": "", "method": "auth_disabled"}
                     if authenticated == "auth_disabled" else identity if authenticated else None)
    session = SimpleNamespace(
        session_id="sid", owner_email="owner@example.test",
        participants=["sender@example.test"] if group else [],
        bot_participants=["writer"] if group else [],
    )
    # AST extraction bypasses Python's ordinary parameter binding. Restore the
    # actual signature/defaults, including continuation_ref, before supplying
    # the locals established by the preceding validated route code.
    call = inspect.signature(dispatch).bind(
        session, msg="hello", model="test", workspace="/tmp", attachments=[],
        sender_identity=turn_identity, sender_email=identity["email"],
        continuation_ref=continuation_ref,
    )
    call.apply_defaults()
    namespace = {
        **call.arguments,
        "_managed_bot_access": True if managed else None,
        "webui_gateway_chat_enabled": lambda config: gateway,
        "get_config": lambda: {},
        "_run_gateway_chat_streaming": gateway_chat._run_gateway_chat_streaming,
        "_run_agent_streaming": streaming._run_agent_streaming,
        "execution_profile": "writer" if group else None,
        "threading": SimpleNamespace(Thread=thread),
        "stream_id": "run",
    }
    statements = [body[resolve], body[decision], *body[start:end + 1]]
    exec(compile(ast.Module(body=statements, type_ignores=[]),
                 "<actual worker dispatch>", "exec"), namespace)

    assert captured["kwargs"]["sender_email"] == identity["email"]
    assert captured["kwargs"].get("execution_profile") == ("writer" if group else None)
    # Authenticated turns and every continuation require the governed local
    # worker. This tests dispatch defense even for a sentinel/absent sender;
    # authority resolution itself is covered by test_continuation_authority.
    if gateway and not group and authenticated is not True and not managed and not continuation_ref:
        assert captured["target"] is gateway_chat._run_gateway_chat_streaming
        assert "sender_identity" not in captured["kwargs"]
    else:
        assert captured["target"] is streaming._run_agent_streaming
        assert captured["kwargs"].get("sender_identity") is turn_identity
    if continuation_ref:
        assert captured["kwargs"]["continuation_ref"] == continuation_ref
    else:
        assert "continuation_ref" not in captured["kwargs"]
