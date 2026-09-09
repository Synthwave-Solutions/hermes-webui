"""Synthetic provider events exercise trusted orchestration without real API keys."""
import json
import os
import threading
from types import SimpleNamespace

import pytest

from api import realtime_voice_runtime as runtime


class Socket:
    def __init__(self): self.events = []; self.closed = False
    def send(self, value): self.events.append(json.loads(value))
    def close(self): self.closed = True


class ImmediatePool:
    def submit(self, fn, *args): fn(*args)
    def shutdown(self, **kwargs): pass


class Bridge:
    actor = "alice@example.test"
    session_id = "parent"
    def __init__(self):
        self.valid = True
        self.dispatched = []
        self.reads = []
    def check(self):
        if not self.valid: raise PermissionError("revoked")
        return {"session_id": self.session_id}
    def dispatch(self, request, mode):
        self.check()
        self.dispatched.append((request, mode))
        return {"session_id": "child" + str(len(self.dispatched)), "mode": mode,
                "status": "running", "title": request, "result": "", "error": ""}
    def request(self, method, path, body=None):
        self.check(); self.reads.append(path); return {"session": {}}
    def task_status(self, sid):
        self.check()
        return {"status": "done", "result": "Actual task result", "error": "", "approval": None}


@pytest.fixture
def controller(tmp_path, monkeypatch):
    from api import realtime_voice
    monkeypatch.setattr(realtime_voice, "hangup_call", lambda *a: None)
    c = runtime.VoiceController(Bridge(), "rtc_internal", journal_dir=tmp_path)
    c.socket = Socket()
    c.pool.shutdown(wait=False)
    c.pool = ImmediatePool()
    yield c
    c.close()


def tool(call_id="call1", name="dispatch_work", **args):
    return {"type": "function_call", "call_id": call_id, "name": name,
            "arguments": json.dumps(args or {"request": "Create report", "mode": "background"})}


def completed(output, status="completed"):
    return {"type": "response.done", "response": {"status": status, "output": [output]}}


def test_completed_function_call_dispatches_once_and_correlates_output(controller):
    event = completed(tool())
    controller.event(event); controller.event(event)
    assert controller.bridge.dispatched == [("Create report", "background")]
    outputs = [e["item"] for e in controller.socket.events if e["type"] == "conversation.item.create"]
    assert len(outputs) == 1
    assert outputs[0]["type"] == "function_call_output"
    assert outputs[0]["call_id"] == "call1"
    result = json.loads(outputs[0]["output"])
    assert result["started"] is True and result["session_id"] == "child1"
    assert "confirmation" in result["note"]


@pytest.mark.parametrize("status", ["cancelled", "failed", "incomplete", None])
def test_incomplete_provider_responses_never_execute(controller, status):
    controller.event(completed(tool(), status))
    assert not controller.bridge.dispatched


@pytest.mark.parametrize("output", [tool(name="terminal", command="anything"),
    tool(request="x", mode="background", actor="admin"), tool(request="x", mode="unknown"),
    tool(request="x" * 8001, mode="chat"), {**tool(), "arguments": "[]"}])
def test_tool_schema_prevents_arbitrary_execution_or_identity(controller, output):
    controller.event(completed(output))
    assert not controller.bridge.dispatched
    result = json.loads(controller.socket.events[0]["item"]["output"])
    assert "error" in result


def test_expired_or_revoked_identity_cannot_dispatch_or_receive_result(controller):
    controller.bridge.valid = False
    controller.event(completed(tool()))
    assert not controller.bridge.dispatched and controller.closed.is_set()
    assert not controller.socket.events


def test_revocation_between_work_start_and_result_closes_without_disclosing(controller):
    original = controller.bridge.dispatch
    def dispatch(*args):
        task = original(*args); controller.bridge.valid = False; return task
    controller.bridge.dispatch = dispatch
    controller.event(completed(tool()))
    assert len(controller.bridge.dispatched) == 1
    assert not controller.socket.events
    assert controller.closed.is_set()


def test_deferred_response_waits_for_turn_generation_and_audible_playback(controller):
    controller.event({"type": "input_audio_buffer.speech_started"})
    controller._tool(tool())
    assert not any(e["type"] == "response.create" for e in controller.socket.events)
    controller.event({"type": "input_audio_buffer.speech_stopped"})
    assert not any(e["type"] == "response.create" for e in controller.socket.events)
    controller.event({"type": "response.created"})
    controller.event({"type": "output_audio_buffer.started"})
    controller.event({"type": "response.done", "response": {"status": "completed", "output": []}})
    assert not any(e["type"] == "response.create" for e in controller.socket.events)
    controller.event({"type": "output_audio_buffer.stopped"})
    assert sum(e["type"] == "response.create" for e in controller.socket.events) == 1


def test_transcripts_are_deduped_private_bounded_and_do_not_dispatch(controller):
    event = {"type": "conversation.item.input_audio_transcription.completed", "item_id": "u1", "transcript": "Hello"}
    controller.event(event); controller.event(event)
    assert controller.transcript == [{"id": "user:u1", "role": "user", "text": "Hello"}]
    assert not controller.bridge.dispatched
    journal = next(controller.journal_dir.rglob("*.json"))
    assert os.stat(journal).st_mode & 0o777 == 0o600
    assert "rtc_internal" not in journal.read_text()
    assert json.loads(journal.read_text())["transcript"] == controller.transcript


def test_snapshot_rechecks_child_visibility_before_cached_content(controller):
    controller.event(completed(tool()))
    controller.tasks[next(iter(controller.tasks))]["result"] = "private answer"
    def deny(*a, **kw): raise PermissionError("child membership revoked")
    controller.bridge.request = deny
    result = controller.snapshot()["tasks"][0]
    assert result["result"] == "" and result["status"] == "error"
    assert not controller.closed.is_set()


def test_status_cannot_enumerate_other_sessions(controller):
    controller.event(completed(tool(name="get_work_status", session_id="other-owner")))
    assert not controller.closed.is_set()
    assert "error" in json.loads(controller.socket.events[0]["item"]["output"])


def test_end_does_not_cancel_normal_engine_work(controller):
    controller.event(completed(tool()))
    controller.close()
    assert controller.socket.closed
    assert controller.tasks[next(iter(controller.tasks))]["status"] == "running"
    assert not any("cancel" in path or "stop" in path for path in controller.bridge.reads)


def test_multiple_dispatches_run_concurrently_while_native_events_continue(controller):
    from concurrent.futures import ThreadPoolExecutor
    controller.pool = ThreadPoolExecutor(max_workers=4)
    barrier = threading.Barrier(3)
    release = threading.Event()
    original = controller.bridge.dispatch
    def dispatch(*args):
        barrier.wait(timeout=3)
        assert release.wait(3)
        return original(*args)
    controller.bridge.dispatch = dispatch
    controller.event(completed(tool("first")))
    controller.event(completed(tool("second")))
    barrier.wait(timeout=3)
    controller.event({"type": "input_audio_buffer.speech_started"})
    assert controller.user_speaking
    release.set()
    controller.pool.shutdown(wait=True)
    assert len(controller.bridge.dispatched) == 2


def make_bridge():
    handler = SimpleNamespace(server=SimpleNamespace(server_address=("0.0.0.0", 9876)), headers={
        "Cookie": "private-cookie", "Host": "public.example", "Origin": "https://public.example",
        "X-Hermes-CSRF-Token": "private-csrf"})
    return runtime.LoopbackBridge(handler, "alice@example.test", "parent")


def test_bridge_derives_session_context_and_uses_normal_start(monkeypatch):
    bridge = make_bridge()
    parent = {"workspace": "/trusted", "model": "approved-model", "model_provider": "approved-provider",
              "profile": "permitted-bot", "bot_participants": ["permitted-bot"], "enabled_toolsets": ["delegate"]}
    bridge.check = lambda: parent
    requests = []
    def request(method, path, body=None):
        requests.append((method, path, body))
        return {"session": {"session_id": "child"}} if path.endswith("/new") else {"ok": True}
    bridge.request = request
    result = bridge.dispatch("Review the supplied report", "subagents")
    assert result["session_id"] == "child"
    assert requests[0] == ("POST", "/api/session/new", parent)
    assert requests[1][1] == "/api/chat/start"
    assert "delegate_task" in requests[1][2]["message"]
    assert requests[1][2]["model"] == "approved-model"
    assert bridge.base == "http://127.0.0.1:9876"
    assert bridge.headers["Origin"] == "https://public.example"


def test_shared_project_dispatch_preserves_project_membership_path():
    bridge = make_bridge()
    bridge.check = lambda: {"project_shared": True, "project_id": "project", "bot_participants": ["bot"]}
    calls = []
    def request(method, path, body=None):
        calls.append((path, body)); return {"session": {"session_id": "child"}}
    bridge.request = request
    bridge.dispatch("Do scoped work", "chat")
    assert calls[0][0] == "/api/projects/chat"
    assert calls[0][1]["project_id"] == "project"
    assert calls[0][1]["bot_participants"] == ["bot"]


def test_governance_voice_and_transcriber_models_must_both_be_allowed(monkeypatch):
    from api.governance import enforce, resource_scope
    from api import realtime_voice
    monkeypatch.setattr(realtime_voice, "configured", lambda: True)
    monkeypatch.setattr(enforce, "_request_identity", lambda h: {"email": "alice"})
    monkeypatch.setattr(enforce, "evaluate_request", lambda *a: SimpleNamespace(allow=True, mode="enforce"))
    monkeypatch.setattr(resource_scope, "access_for", lambda h: object())
    monkeypatch.setattr(resource_scope, "model_allowed", lambda access, model, provider: model != "gpt-4o-mini-transcribe")
    assert not runtime.voice_access(SimpleNamespace())


def test_missing_provider_location_cannot_start_uncontrollable_call(monkeypatch):
    from api import realtime_voice
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-key")
    with pytest.raises(RuntimeError):
        realtime_voice.create_call("v=0", "location-test", post=lambda *a, **k:
                                  SimpleNamespace(status_code=201, text="v=0", headers={}))


def test_denied_work_does_not_end_an_authorized_voice_conversation(controller):
    def deny(*args): raise PermissionError("tool not granted")
    controller.bridge.dispatch = deny
    controller.event(completed(tool()))
    assert not controller.closed.is_set()
    output = json.loads(controller.socket.events[0]["item"]["output"])
    assert "not allowed" in output["error"]
    assert not controller.bridge.dispatched


def test_sideband_deltas_do_not_trigger_session_http_reads(controller):
    events = iter([json.dumps({"type": "response.output_audio.delta", "delta": "large"})] * 100)
    calls = []
    def recv(**kwargs):
        try: return next(events)
        except StopIteration:
            controller.closed.set()
            raise TimeoutError() from None
    controller.socket.recv = recv
    controller.check = lambda: calls.append("checked")
    controller._listen()
    assert not calls


def test_bridge_start_timeout_preserves_child_without_retry():
    bridge = make_bridge()
    bridge.check = lambda: {}
    calls = []
    def request(method, path, body=None):
        calls.append(path)
        if path == "/api/session/new": return {"session": {"session_id": "created-child"}}
        raise RuntimeError("request timed out after possible acceptance")
    bridge.request = request
    result = bridge.dispatch("Do work", "chat")
    assert result["session_id"] == "created-child"
    assert result["status"] == "error" and "could not be confirmed" in result["error"]
    assert calls.count("/api/chat/start") == 1


@pytest.mark.parametrize("code", ["response_cancel_not_active", "output_audio_buffer_clear_not_active"])
def test_idle_interrupt_provider_error_keeps_sideband_and_conversation_live(controller, code):
    events = iter([json.dumps({"type": "error", "error": {"code": code}}),
                   json.dumps({"type": "input_audio_buffer.speech_started"})])
    def recv(**kwargs):
        try: return next(events)
        except StopIteration:
            assert not controller.closed.is_set()
            controller.closed.set()
            raise TimeoutError() from None
    controller.socket.recv = recv
    controller._listen()
    assert controller.user_speaking
    assert not controller.socket.closed
    # Let fixture teardown perform actual cleanup after the synthetic reader exit.
    controller.closed.clear()


def test_end_removes_live_registry_and_forgets_captured_auth(controller):
    controller.bridge.headers = {"Cookie": "private", "X-Hermes-CSRF-Token": "private"}
    runtime.register(controller)
    controller.close()
    assert controller.voice_id not in runtime._CALLS
    assert controller.bridge.headers == {}
    with pytest.raises(PermissionError): controller.snapshot()


def test_status_enforces_expiry_even_before_monitor_tick(controller):
    runtime.register(controller)
    controller.created -= controller.TTL + 1
    with pytest.raises(PermissionError): controller.snapshot()
    assert controller.closed.is_set()
    assert controller.voice_id not in runtime._CALLS


def test_failed_journal_releases_call_without_emitting_unpersisted_result(controller):
    runtime.register(controller)
    def fail(): raise OSError("state volume unavailable")
    controller.persist = fail
    controller.event(completed(tool()))
    assert controller.closed.is_set() and controller.socket.closed
    assert controller.voice_id not in runtime._CALLS
    assert not controller.socket.events


@pytest.mark.parametrize("pending,progress,expected", [
    (True, "completed", "running"), (False, "completed", "done"),
    (None, "completed", "error"), (False, "failed", "error"), (False, "canceled", "error")])
def test_task_completion_uses_durable_run_and_delegation_state(pending, progress, expected):
    bridge = make_bridge()
    bridge.check = lambda: {}
    read_results = []
    def request(method, path, body=None):
        if "/session/status?" in path:
            return {"agent_running": False, "progress": {"status": progress}, "delegation_pending": pending}
        if "/approval/pending?" in path: return {"pending": None}
        read_results.append(path)
        return {"session": {"messages": [{"role": "assistant", "content": "Actual completed answer"}]}}
    bridge.request = request
    result = bridge.task_status("child")
    assert result["status"] == expected
    assert bool(read_results) == (expected == "done")
    if expected != "done": assert result["result"] == ""
