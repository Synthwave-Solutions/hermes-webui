"""Trusted realtime sideband. Voice tools enter the ordinary authenticated API.

The browser owns audio; this module owns provider tool calls and a bounded voice
journal. Normal engine sessions own dispatched work, even after a call ends.
"""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from urllib.parse import urlencode

import requests

TOOLS = [
    {"type": "function", "name": "dispatch_work",
     "description": "Start requested work in a visible SynPulse chat without ending voice. Use subagents only when the user wants delegated parallel work. Starting a chat does not prove any subagent or action executed; inspect its status/result.",
     "parameters": {"type": "object", "properties": {
         "request": {"type": "string", "description": "The user's concrete requested work, including relevant context from this conversation."},
         "mode": {"type": "string", "enum": ["chat", "background", "subagents"]}},
         "required": ["request", "mode"], "additionalProperties": False}},
    {"type": "function", "name": "get_work_status",
     "description": "Inspect work dispatched during this voice call. Omit session_id for all work.",
     "parameters": {"type": "object", "properties": {"session_id": {"type": "string"}},
                    "additionalProperties": False}},
]


def actor_for(handler):
    from api.governance.enforce import _request_identity
    identity = _request_identity(handler) or {}
    return str(identity.get("email") or identity.get("sub") or "").strip().lower()


def voice_access(handler):
    from api.governance.enforce import _request_identity, evaluate_request
    from api.governance.resource_scope import access_for, model_allowed
    from api.realtime_voice import MODEL, configured
    decision = evaluate_request(_request_identity(handler), "POST", "/api/voice/realtime/call")
    access = access_for(handler)
    return (configured() and (decision.allow or decision.mode == "report_only")
            and model_allowed(access, MODEL, "openai")
            and model_allowed(access, "gpt-4o-mini-transcribe", "openai"))


class _PinnedLoopbackTLSAdapter(requests.adapters.HTTPAdapter):
    """Authenticate native TLS by the listener's configured leaf certificate.

    The fixed loopback IP need not be in a public certificate's DNS names.
    Exact SHA256 certificate pinning replaces DNS matching; certificate chain
    verification remains CERT_REQUIRED with only the configured cert trusted.
    """
    def __init__(self, context, fingerprint):
        self.context, self.fingerprint = context, fingerprint
        super().__init__()

    def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
        kwargs.update(ssl_context=self.context, assert_fingerprint=self.fingerprint)
        super().init_poolmanager(connections, maxsize, block=block, **kwargs)


class LoopbackBridge:
    """Fixed-origin HTTP with the original cookie and CSRF provenance.

    Do not substitute internal route helpers: their owner/profile context is
    established by server.Handler. Never accept a URL, headers, actor, workspace,
    project or bot roster from the speech model.
    """
    def __init__(self, handler, actor, session_id):
        port = int(handler.server.server_address[1])
        self.tls_cert = self.tls_context = self.tls_fingerprint = None
        native_tls = getattr(handler.server, "ssl_context", None) is not None
        self.base = ("https" if native_tls else "http") + "://127.0.0.1:" + str(port)
        if native_tls:
            from pathlib import Path
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes
            from api.config import TLS_CERT
            # Read the trusted listener configuration, never request Host or a
            # model-supplied trust file. A missing/rotated cert fails closed.
            self.tls_cert = str(Path(TLS_CERT).resolve())
            certificate = x509.load_pem_x509_certificate(Path(self.tls_cert).read_bytes())
            self.tls_fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
            self.tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            self.tls_context.minimum_version = ssl.TLSVersion.TLSv1_2
            self.tls_context.check_hostname = False  # Exact leaf pin verified by urllib3.
            self.tls_context.verify_mode = ssl.CERT_REQUIRED
            self.tls_context.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
            self.tls_context.load_verify_locations(cafile=self.tls_cert)
        self.actor, self.session_id = actor, session_id
        names = ("Cookie", "Host", "Origin", "Referer", "Sec-Fetch-Site",
                 "X-Hermes-CSRF-Token", "X-CSRF-Token", "X-Forwarded-Host", "X-Real-Host")
        self.headers = {name: handler.headers[name] for name in names if handler.headers.get(name)}
        self.identity_handler = SimpleNamespace(headers=self.headers)

    def request(self, method, path, body=None):
        # Call sites are fixed below; this is not a general-purpose model tool.
        if not path.startswith("/api/") or "://" in path:
            raise ValueError("Invalid voice bridge route")
        with requests.Session() as client:
            client.trust_env = False
            if self.tls_cert:
                client.mount(self.base + "/", _PinnedLoopbackTLSAdapter(self.tls_context, self.tls_fingerprint))
            response = client.request(method, self.base + path, headers=self.headers,
                                      json=body, timeout=20, allow_redirects=False,
                                      verify=self.tls_cert or True)
        if response.status_code in {401, 403, 404}:
            raise PermissionError("Work is no longer accessible")
        if response.status_code != 200:
            raise RuntimeError("The requested work could not be started or inspected")
        result = response.json()
        if not isinstance(result, dict) or result.get("error") or result.get("ok") is False:
            raise RuntimeError("The requested work could not be started or inspected")
        return result

    def check(self):
        if actor_for(self.identity_handler) != self.actor or not voice_access(self.identity_handler):
            raise PermissionError("Voice access expired or was revoked")
        # Actual GET reinstates fresh profile, group, project, owner and route checks.
        return self.request("GET", "/api/session?" + urlencode({
            "session_id": self.session_id, "messages": "0"}))["session"]

    def dispatch(self, request, mode):
        parent = self.check()
        if parent.get("read_only") or parent.get("is_cli_session"):
            raise PermissionError("This conversation cannot dispatch work")
        title = "Voice: " + request[:70]
        if parent.get("project_shared"):
            created = self.request("POST", "/api/projects/chat", {
                "project_id": parent.get("project_id"), "bot_participants": parent.get("bot_participants") or [],
                "title": title})
        else:
            body = {key: parent[key] for key in (
                "workspace", "model", "model_provider", "profile", "project_id", "bot_participants",
                "enabled_toolsets", "chat_mode") if parent.get(key) is not None}
            created = self.request("POST", "/api/session/new", body)
        sid = created["session"]["session_id"]
        self.check()  # Revocation during session creation must prevent execution.
        prompt = request
        if mode == "subagents":
            prompt = ("The user requested delegated parallel work. Use the available delegate_task tool for "
                      "independent subtasks when permitted. Do not claim a subagent started unless the tool "
                      "actually confirms it. If unavailable or denied, report that limitation.\n\n" + request)
        try:
            self.request("POST", "/api/chat/start", {"session_id": sid, "message": prompt,
                         "model": parent.get("model"), "model_provider": parent.get("model_provider")})
        except PermissionError:
            raise
        except Exception:
            # A timeout may occur after the engine accepted the request. Preserve
            # the visible chat and never automatically repeat a possible action.
            return {"session_id": sid, "mode": mode, "status": "error", "title": title,
                    "result": "", "error": "Work start could not be confirmed; inspect the chat"}
        return {"session_id": sid, "mode": mode, "status": "running", "title": title,
                "result": "", "error": ""}

    def task_status(self, sid):
        self.check()
        query = urlencode({"session_id": sid})
        status = self.request("GET", "/api/session/status?" + query)
        approval = self.request("GET", "/api/approval/pending?" + query).get("pending")
        if approval:
            safe = {key: approval[key] for key in (
                "approval_id", "request_id", "command", "description", "governance_action", "required_approver",
                "allow_session", "allow_permanent", "reason") if key in approval}
            return {"status": "waiting_approval", "approval": safe, "result": "", "error": ""}
        progress = (status.get("progress") or {}).get("status")
        if status.get("agent_running") or progress in {"running", "queued"} or status.get("delegation_pending") is True:
            return {"status": "running", "approval": None, "result": "", "error": ""}
        if status.get("delegation_pending") is None:
            return {"status": "error", "approval": None, "result": "",
                    "error": "Delegated work status could not be verified; inspect the chat"}
        if progress != "completed":
            return {"status": "error", "approval": None, "result": "",
                    "error": "Work ended without a confirmed completed run; inspect the chat"}
        session = self.request("GET", "/api/session?" + query + "&msg_limit=12")["session"]
        result = ""
        for message in reversed(session.get("messages") or []):
            if message.get("role") == "assistant" and message.get("content"):
                content = message["content"]
                result = content if isinstance(content, str) else "\n".join(
                    str(part.get("text", "")) for part in content if isinstance(part, dict))
                break
        return {"status": "done" if result else "error", "approval": None,
                "result": result[:12000], "error": "" if result else "Work ended without a final answer"}


class VoiceController:
    MAX_TASKS = 16
    TTL = 15 * 60

    def __init__(self, bridge, call_id, *, connector=None, journal_dir=None):
        self.bridge, self.call_id = bridge, call_id
        self.voice_id = uuid.uuid4().hex
        self.actor, self.session_id = bridge.actor, bridge.session_id
        self.created = time.monotonic()
        self.state, self.error = "connecting", ""
        self.transcript, self.tasks, self.seen = [], {}, set()
        self.lock, self.send_lock = threading.RLock(), threading.Lock()
        self.closed = threading.Event()
        self.user_speaking = self.response_active = self.audio_playing = self.awaiting_turn = False
        self.pending_response = False
        self.socket = None
        self.connector = connector
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="voice-work")
        if journal_dir is None:
            from api.config import STATE_DIR
            journal_dir = STATE_DIR / "voice"
        self.journal_dir = journal_dir

    def check(self):
        if self.closed.is_set() or time.monotonic() - self.created >= self.TTL:
            raise PermissionError("Voice connection ended")
        return self.bridge.check()

    def persist(self):
        # This journal contains no cookies, provider IDs, SDP, tokens or raw audio.
        from pathlib import Path
        directory = Path(self.journal_dir) / hashlib.sha256(self.actor.encode()).hexdigest()
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / (self.voice_id + ".json")
        with self.lock:
            data = json.dumps(self._snapshot(), ensure_ascii=False)
            temp = path.with_suffix(".tmp")
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as output:
                output.write(data)
            os.replace(temp, path)
        for old in sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[100:]:
            old.unlink(missing_ok=True)

    def _snapshot(self):
        return {"voice_id": self.voice_id, "session_id": self.session_id, "state": self.state,
                "error": self.error, "transcript": list(self.transcript), "tasks": list(self.tasks.values())}

    def snapshot(self):
        if time.monotonic() - self.created >= self.TTL:
            self.close()
            raise PermissionError("Voice connection ended")
        if self.closed.is_set():
            raise PermissionError("Voice connection ended")
        self.bridge.check()
        with self.lock:
            # Recheck child ACL before returning cached content after a membership change.
            for task in self.tasks.values():
                if task.get("session_id"):
                    try:
                        self.bridge.request("GET", "/api/session?" + urlencode({"session_id": task["session_id"], "messages": 0}))
                    except PermissionError:
                        self.bridge.check()
                        task.update(status="error", result="", approval=None, error="Work is no longer accessible")
            self.bridge.check()
            return self._snapshot()

    def start(self):
        self.check()
        if self.connector is None:
            from websockets.sync.client import connect
            self.connector = connect
        self.socket = self.connector(
            "wss://api.openai.com/v1/realtime?" + urlencode({"call_id": self.call_id}),
            additional_headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
            proxy=None, open_timeout=10, max_size=1024 * 1024)
        self.check()
        self.state = "listening"
        self.persist()
        threading.Thread(target=self._listen, name="voice-sideband", daemon=True).start()
        threading.Thread(target=self._monitor, name="voice-monitor", daemon=True).start()

    def send(self, event):
        if self.closed.is_set():
            return
        with self.send_lock:
            self.socket.send(json.dumps(event))

    def respond_when_idle(self):
        with self.lock:
            if self.pending_response and not (self.user_speaking or self.awaiting_turn or self.response_active or self.audio_playing or self.closed.is_set()):
                self.pending_response = False
                self.response_active = True
                self.send({"type": "response.create"})

    def event(self, event):
        kind = event.get("type")
        if kind == "input_audio_buffer.speech_started":
            self.user_speaking = True
            self.awaiting_turn = True
        elif kind == "input_audio_buffer.speech_stopped":
            self.user_speaking = False
        elif kind == "response.created":
            self.response_active = True
            self.awaiting_turn = False
        elif kind == "output_audio_buffer.started":
            self.audio_playing = True
            self.state = "speaking"
        elif kind in {"output_audio_buffer.stopped", "output_audio_buffer.cleared"}:
            self.audio_playing = False
            self.state = "listening"
        elif kind == "response.done":
            self.response_active = False
            response = event.get("response") or {}
            if response.get("status") == "completed":
                for output in response.get("output") or []:
                    if output.get("type") == "function_call":
                        call_id = output.get("call_id")
                        with self.lock:
                            if not isinstance(call_id, str) or not call_id or call_id in self.seen:
                                continue
                            if len(self.seen) >= 128:
                                self.close("Voice request limit reached")
                                return
                            self.seen.add(call_id)
                        self.pool.submit(self._tool, output)
        elif kind in {"conversation.item.input_audio_transcription.completed", "response.output_audio_transcript.done", "response.audio_transcript.done", "response.output_text.done"}:
            role = "user" if kind.startswith("conversation.") else "assistant"
            item_id = str(event.get("item_id") or event.get("response_id") or "")
            text = event.get("transcript") or event.get("text") or ""
            if isinstance(text, str) and text and item_id:
                with self.lock:
                    key = role + ":" + item_id
                    if not any(item["id"] == key for item in self.transcript):
                        self.transcript.append({"id": key, "role": role, "text": text[:12000]})
                        self.transcript = self.transcript[-200:]
                self.persist()
        self.respond_when_idle()

    def _tool(self, output):
        try:
            self.check()
            args = json.loads(output.get("arguments") or "{}")
            if not isinstance(args, dict):
                raise ValueError("Invalid voice tool arguments")
            if output.get("name") == "dispatch_work":
                if set(args) != {"request", "mode"} or args["mode"] not in {"chat", "background", "subagents"}:
                    raise ValueError("Invalid voice work request")
                request = args["request"]
                if not isinstance(request, str) or not request.strip() or len(request) > 8000:
                    raise ValueError("Work request must contain 1 to 8000 characters")
                with self.lock:
                    if len(self.tasks) >= self.MAX_TASKS:
                        raise ValueError("Voice task limit reached")
                    task_id = uuid.uuid4().hex
                    self.tasks[task_id] = {"task_id": task_id, "session_id": "", "mode": args["mode"],
                                           "status": "starting", "title": request[:70], "result": "", "error": ""}
                try:
                    task = self.bridge.dispatch(request.strip(), args["mode"])
                    with self.lock:
                        self.tasks[task_id].update(task)
                    result = {"started": task["status"] == "running", "task_id": task_id, "session_id": task["session_id"],
                              "status": task["status"], "mode": args["mode"], "error": task["error"],
                              "note": "Chat started. Actual actions and subagent creation require engine confirmation."}
                except Exception:
                    with self.lock:
                        self.tasks[task_id].update(status="error", error="Work could not be started")
                    raise
            elif output.get("name") == "get_work_status":
                if set(args) - {"session_id"}:
                    raise ValueError("Invalid status request")
                tasks = self.snapshot()["tasks"]
                if args.get("session_id"):
                    tasks = [t for t in tasks if t["session_id"] == args["session_id"]]
                    if not tasks:
                        raise PermissionError("Work not found in this call")
                result = {"tasks": tasks}
            else:
                raise ValueError("Unknown voice tool")
            self.check()  # Never deliver cached results after revocation.
        except PermissionError:
            try:
                self.check()
            except Exception:
                self.close("Voice access expired or was revoked")
                return
            result = {"error": "This work is not allowed or is not accessible in this call. No permission was granted."}
        except Exception:
            result = {"error": "The requested work was not started or could not be inspected. Check the task panel."}
        try:
            self.check()
        except Exception:
            self.close("Voice access expired or was revoked")
            return
        try:
            self.persist()
        except Exception:
            self.close("Voice journal could not be saved")
            return
        self.send({"type": "conversation.item.create", "item": {
            "type": "function_call_output", "call_id": output["call_id"], "output": json.dumps(result)}})
        self.pending_response = True
        self.respond_when_idle()

    def _listen(self):
        try:
            while not self.closed.is_set():
                try:
                    raw = self.socket.recv(timeout=1)
                except TimeoutError:
                    continue
                event = json.loads(raw)
                # Audio/token deltas can be numerous; they contain no actionable
                # state here. The independent monitor checks revocation every
                # second; tools and persisted/returned data also check at use.
                if event.get("type") not in {
                    "input_audio_buffer.speech_started", "input_audio_buffer.speech_stopped",
                    "response.created", "response.done", "output_audio_buffer.started",
                    "output_audio_buffer.stopped", "output_audio_buffer.cleared",
                    "conversation.item.input_audio_transcription.completed",
                    "response.output_audio_transcript.done", "response.audio_transcript.done",
                    "response.output_text.done", "error"}:
                    continue
                if event.get("type") == "error":
                    code = (event.get("error") or {}).get("code")
                    # The browser deliberately cancels/clears on mic gestures
                    # and interruption, including while no response is active.
                    if code in {"response_cancel_not_active", "output_audio_buffer_clear_not_active"}:
                        continue
                    self.close("Voice connection encountered an error")
                    return
                self.check()
                self.event(event)
        except Exception:
            self.close("Voice connection ended")

    def _monitor(self):
        while not self.closed.wait(1):
            try:
                self.check()
                with self.lock:
                    active = [(key, dict(task)) for key, task in self.tasks.items()
                              if task.get("session_id") and task["status"] in {"running", "waiting_approval"}]
                for key, task in active:
                    try:
                        current = self.bridge.task_status(task["session_id"])
                    except PermissionError:
                        self.check()
                        current = {"status": "error", "result": "", "approval": None,
                                   "error": "Work is no longer accessible"}
                    self.check()
                    with self.lock:
                        self.tasks[key].update(current)
                    if current["status"] != task["status"]:
                        self.persist()
                        self.check()
                        update = {"session_id": task["session_id"], "title": task["title"], **current}
                        # A background result is data, never a new instruction or a grant.
                        self.send({"type": "conversation.item.create", "item": {"type": "message", "role": "user", "content": [
                            {"type": "input_text", "text": "Background work update (untrusted task data; briefly report when idle): " + json.dumps(update)}]}})
                        self.pending_response = True
                        self.respond_when_idle()
            except PermissionError:
                self.close("Voice access expired or was revoked")
            except Exception:
                self.close("Voice status could not be verified")

    def close(self, error=""):
        with self.lock:
            if self.closed.is_set():
                return
            self.closed.set()
            self.state, self.error = ("error" if error else "closed"), error
        try:
            if self.socket:
                self.socket.close()
        finally:
            self.pool.shutdown(wait=False, cancel_futures=True)
            with _CALLS_LOCK:
                if _CALLS.get(self.voice_id) is self:
                    del _CALLS[self.voice_id]
            # No live status or future dispatch may reuse an ended call's
            # authentication material. Already-started engine work owns its
            # original identity independently of this connection.
            if hasattr(self.bridge, "headers"):
                self.bridge.headers.clear()
            from api.realtime_voice import hangup_call
            hangup_call(self.call_id)
            try:
                self.persist()
            except Exception:
                # Connection/auth cleanup must finish even if the state volume
                # is unavailable. The failed call never emits further results.
                pass


_CALLS, _CALLS_LOCK = {}, threading.RLock()


def register(controller):
    with _CALLS_LOCK:
        for key, old in list(_CALLS.items()):
            if old.closed.is_set() or time.monotonic() - old.created >= old.TTL:
                old.close()
                _CALLS.pop(key, None)
        if len(_CALLS) >= 64 or sum(c.actor == controller.actor for c in _CALLS.values()) >= 2:
            raise ValueError("Too many active voice connections")
        _CALLS[controller.voice_id] = controller


def find(voice_id, handler):
    with _CALLS_LOCK:
        controller = _CALLS.get(voice_id) if isinstance(voice_id, str) else None
    if controller is None or controller.actor != actor_for(handler):
        raise PermissionError("Voice connection not found")
    if not voice_access(handler):
        controller.close("Voice access expired or was revoked")
        raise PermissionError("Voice connection not found")
    return controller
