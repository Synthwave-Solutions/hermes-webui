"""WebUI ops reporter (plan 3.3, W7).

What these tests pin:

* disabled cleanly: without ``SP_OPERATIONAL_TELEMETRY=1`` plus a control URL
  and an ingest key nothing is queued, spooled or sent, no thread starts, and
  ``POST /api/client-errors`` answers 204 exactly like the scaffold stub;
* no request reaches a (stub) control-api while the flag is off, from any
  entry point: the crash hooks, capacity incidents and browser errors;
* allowlist and redaction before anything is queued or spooled; without
  diagnostic payloads no message, exception value or context leaves the
  process, and a canary never reaches the wire or the spool;
* the bounded queue, the background sender, the 0600 spool with backoff and
  the drain after recovery; reporting never raises and never blocks;
* ``POST /api/client-errors``: off unless support telemetry is on, at most
  16 KB, 30 a minute per user, ``public_origin`` events only;
* no key material in any browser response (``/api/settings`` and the route);
* the browser side (``static/error-reporter.js``) through tests/error_reporter.cjs.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from api import control_plane_client as cpc  # noqa: E402
from api import ops_reporter  # noqa: E402

INGEST_KEY_ID = "99887766554433aa"
INGEST_SECRET_HEX = "d4" * 32
SENTRY_KEY = INGEST_KEY_ID + INGEST_SECRET_HEX[:16]
CONTROL_KEY_ID = "0a1b2c3d4e5f6071"
CONTROL_SECRET_HEX = "7e" * 32
CANARY = "CANARY-7f3c9e"
CANARY_TOKEN = "sk-canary0123456789abcdef"
MEMBER = "member@example.test"
OTHER = "other@example.test"
NODE = shutil.which("node")

SP_ENV = ("SP_OPERATIONAL_TELEMETRY", "SP_DIAGNOSTIC_PAYLOADS", "SP_CONTROL_URL",
          "SP_CONTROL_KEY_FILE", "SP_INGEST_KEY_FILE", "HTTP_PROXY", "HTTPS_PROXY",
          "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy")


# ── A recording stub for POST /v1/events ─────────────────────────────────────

class EventsStub:
    def __init__(self):
        self.requests = []
        self.statuses = []  # consumed one per request; default 202
        self.hold = threading.Event()
        self.hold.set()
        self.closed = False
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                stub.hold.wait(10)
                stub.requests.append({"path": self.path, "headers": dict(self.headers.items()), "body": body})
                status = stub.statuses.pop(0) if stub.statuses else 202
                data = json.dumps({"accepted": 1, "dropped": 0}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_PUT = do_DELETE = do_POST

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self):
        return "http://127.0.0.1:%d" % self.server.server_address[1]

    def events(self):
        out = []
        for request in self.requests:
            out.extend(json.loads(request["body"])["events"])
        return out

    def raw_text(self):
        return "".join(r["body"].decode("utf-8", "replace") + json.dumps(r["headers"]) for r in self.requests)

    def close(self):
        if not self.closed:
            self.closed = True
            self.hold.set()
            self.server.shutdown()
            self.server.server_close()


def _wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def _sender_threads():
    return [t for t in threading.enumerate() if t.name == ops_reporter.SENDER_THREAD_NAME and t.is_alive()]


@pytest.fixture
def stub():
    server = EventsStub()
    yield server
    server.close()


@pytest.fixture
def rep(tmp_path, monkeypatch):
    """A fresh reporter with its own state dir and no control-plane env."""
    from api import config

    for name in SP_ENV:
        monkeypatch.delenv(name, raising=False)
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setattr(config, "STATE_DIR", state)
    ops_reporter._reset_for_tests()
    monkeypatch.setattr(ops_reporter, "BATCH_DELAY_S", 0.0)
    monkeypatch.setattr(ops_reporter, "IDLE_WAIT_S", 0.2)

    def configure(url, *, telemetry="1", diagnostic=None, control=False):
        key = tmp_path / "ingest.key"
        key.write_text(json.dumps({"kind": "ingest", "key_id": INGEST_KEY_ID, "secret": INGEST_SECRET_HEX,
                                   "allowed_ingress": "tailnet"}), encoding="utf-8")
        key.chmod(0o600)
        monkeypatch.setenv("SP_CONTROL_URL", url)
        monkeypatch.setenv("SP_INGEST_KEY_FILE", str(key))
        if control:
            ckey = tmp_path / "control.key"
            ckey.write_text(json.dumps({"kind": "control", "key_id": CONTROL_KEY_ID,
                                        "secret": CONTROL_SECRET_HEX}), encoding="utf-8")
            monkeypatch.setenv("SP_CONTROL_KEY_FILE", str(ckey))
        if telemetry is not None:
            monkeypatch.setenv("SP_OPERATIONAL_TELEMETRY", telemetry)
        if diagnostic is not None:
            monkeypatch.setenv("SP_DIAGNOSTIC_PAYLOADS", diagnostic)
        cpc.clear_cache()

    spool = state / "ops-reporter" / "spool"
    yield SimpleNamespace(configure=configure, state=state, spool=spool, tmp=tmp_path)
    ops_reporter._reset_for_tests()


def _exc_info(message=f"{CANARY} {CANARY_TOKEN} for ada@acme.example"):
    def _inner_boom():
        raise ValueError(message)

    def _outer_call():
        _inner_boom()

    try:
        _outer_call()
    except ValueError:
        return sys.exc_info()


class _Handler:
    """Records one response the way BaseHTTPRequestHandler would send it."""

    def __init__(self, headers=None, body=b"", address=("127.0.0.1", 5000)):
        self.status = None
        self.headers = headers if headers is not None else {}
        self.response_headers = []
        self.wfile = io.BytesIO()
        self.rfile = io.BytesIO(body)
        self.client_address = address

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass

    def header(self, name):
        return next((v for k, v in self.response_headers if k.lower() == name.lower()), None)

    @property
    def raw(self):
        return self.wfile.getvalue()


def _client_body(**extra):
    body = {
        "kind": "error",
        "type": "TypeError",
        "message": f"x is undefined ({CANARY_TOKEN}) for ada@acme.example",
        "frames": [
            {"function": "outer", "file": "static/boot.js"},
            {"function": "evil", "file": "https://cdn.evil.example/lib.js"},
            {"function": "renderMessages", "file": "/session/static/ui.js"},
            {"function": "sneaky", "file": "static/../../etc/passwd.js"},
        ],
        "url_path": "/session/abc?token=secret#frag",
    }
    body.update(extra)
    return body


def _post_client_error(body, *, email=MEMBER, length=None, monkeypatch=None):
    raw = json.dumps(body).encode("utf-8")
    handler = _Handler(headers={"Content-Length": str(len(raw) if length is None else length)})
    if monkeypatch is not None:
        import api.governance.enforce as enforce

        monkeypatch.setattr(enforce, "_request_identity",
                            lambda _h: {"email": email, "groups": [], "claims_subset": {}, "method": "oidc"})
    ops_reporter.handle_client_error(handler, copy.deepcopy(body))
    return handler


# ── Disabled cleanly ─────────────────────────────────────────────────────────

def test_disabled_without_env_does_nothing(rep):
    assert ops_reporter.enabled() is False
    assert ops_reporter.browser_reporting_enabled() is False
    assert ops_reporter.report_exception(*_exc_info()) is False
    assert ops_reporter.report_exception(*_exc_info(), sync=True) is False
    assert ops_reporter.report_capacity("quota_exhausted", "anthropic") is False
    assert ops_reporter.start() is False
    handler = _Handler(headers={"Content-Length": "20"})
    assert ops_reporter.handle_client_error(handler, {"message": "x"}) is True
    assert handler.status == 204 and handler.raw == b"" and handler.header("Content-Length") == "0"
    assert _sender_threads() == []
    assert not (rep.state / "ops-reporter").exists()
    assert ops_reporter.stats()["queued"] == 0


@pytest.mark.parametrize("telemetry", [None, "0", "", "no", "false"])
def test_no_request_is_made_while_the_flag_is_off(rep, stub, monkeypatch, telemetry):
    """Everything else is configured; only the switch is off."""
    from api import capacity_alerts, crash_visibility

    rep.configure(stub.url, telemetry=telemetry, diagnostic="1", control=True)
    assert cpc.ingest_configured() is True  # the switch is the only thing missing
    assert ops_reporter.enabled() is False
    assert ops_reporter.browser_reporting_enabled() is False

    exc_type, exc_value, exc_tb = _exc_info()
    crash_visibility.thread_excepthook(SimpleNamespace(exc_type=exc_type, exc_value=exc_value,
                                                       exc_traceback=exc_tb, thread=threading.current_thread()))
    crash_visibility.main_excepthook(exc_type, exc_value, exc_tb)
    monkeypatch.setattr(capacity_alerts, "effective_config", lambda: dict(capacity_alerts.DEFAULT_CONFIG))
    monkeypatch.setattr(capacity_alerts, "_dispatch_external", lambda event: (False, ""))
    capacity_alerts.record_capacity_event("quota_exhausted", "anthropic", source="test")
    ops_reporter.report_capacity("rate_limit", "openai")
    handler = _post_client_error(_client_body(), monkeypatch=monkeypatch)
    assert handler.status == 204 and handler.raw == b""
    assert ops_reporter.start() is False
    time.sleep(0.3)
    assert stub.requests == []
    assert _sender_threads() == []
    assert not (rep.state / "ops-reporter").exists()


def test_browser_reporting_also_needs_diagnostic_payloads(rep, stub, monkeypatch):
    rep.configure(stub.url, telemetry="1", diagnostic=None)
    assert ops_reporter.enabled() is True
    assert ops_reporter.browser_reporting_enabled() is False
    handler = _post_client_error(_client_body(), monkeypatch=monkeypatch)
    assert handler.status == 204
    assert ops_reporter.stats()["queued"] == 0
    monkeypatch.setenv("SP_DIAGNOSTIC_PAYLOADS", "1")
    assert ops_reporter.browser_reporting_enabled() is True


def test_missing_or_bad_ingest_key_keeps_it_off(rep, stub, monkeypatch):
    rep.configure(stub.url)
    monkeypatch.setenv("SP_INGEST_KEY_FILE", str(rep.tmp / "absent.key"))
    cpc.clear_cache()
    assert ops_reporter.enabled() is False
    monkeypatch.setenv("SP_CONTROL_URL", "not a url")
    assert ops_reporter.enabled() is False
    assert ops_reporter.report_exception(*_exc_info()) is False
    assert stub.requests == []


# ── Sending ──────────────────────────────────────────────────────────────────

def test_exception_report_reaches_events_with_the_ingest_key_and_no_payload(rep, stub):
    rep.configure(stub.url)
    assert ops_reporter.report_exception(*_exc_info(), logger_name="crash_visibility",
                                         message=f"boom {CANARY}", context={"thread": "worker"}) is True
    assert ops_reporter.flush(5)
    assert _wait_for(lambda: stub.requests)
    request = stub.requests[0]
    assert request["path"] == "/v1/events"
    assert request["headers"]["Authorization"] == "SP-Ingest " + SENTRY_KEY
    (event,) = stub.events()
    assert set(event) <= {"ts", "service", "kind", "level", "logger", "exception", "release"}
    assert event["service"] == "webui" and event["kind"] == "error" and event["level"] == "error"
    assert event["logger"] == "crash_visibility"
    assert event["exception"]["type"] == "ValueError"
    assert "value" not in event["exception"]
    frames = event["exception"]["frames"]
    assert [f["function"] for f in frames][-2:] == ["_exc_info.<locals>._outer_call", "_exc_info.<locals>._inner_boom"]
    assert all(f == {"function": f["function"], "module": "tests.test_ops_reporter", "in_app": True} for f in frames)
    text = stub.raw_text()
    for secret in (CANARY, CANARY_TOKEN, "ada@acme.example", INGEST_SECRET_HEX):
        assert secret not in text


def test_diagnostic_payloads_are_redacted(rep, stub):
    rep.configure(stub.url, diagnostic="1")
    ops_reporter.report_exception(*_exc_info(), logger_name="crash_visibility",
                                  message="Uncaught exception for ada@acme.example",
                                  context={"thread": "worker", "unknown_key": CANARY, "provider": 5})
    assert ops_reporter.flush(5) and _wait_for(lambda: stub.requests)
    (event,) = stub.events()
    assert event["message"] == "Uncaught exception for [email]"
    assert event["exception"]["value"] == f"{CANARY} [redacted] for [email]"
    assert event["context"] == {"thread": "worker"}
    assert CANARY_TOKEN not in stub.raw_text()


def test_non_in_app_frames_and_foreign_modules_are_left_out(rep, stub):
    rep.configure(stub.url)
    try:
        json.loads("{not json")
    except ValueError:
        info = sys.exc_info()
    ops_reporter.report_exception(*info)
    assert ops_reporter.flush(5) and _wait_for(lambda: stub.requests)
    (event,) = stub.events()
    assert event["exception"]["type"] == "json.decoder.JSONDecodeError"
    modules = {f["module"] for f in event["exception"].get("frames", [])}
    assert modules <= {"tests.test_ops_reporter"}


def test_capacity_incident_is_a_health_event_with_a_stable_fingerprint(rep, stub, monkeypatch):
    from api import capacity_alerts, config

    monkeypatch.setattr(config, "STATE_DIR", rep.state)
    monkeypatch.setattr(capacity_alerts, "effective_config", lambda: dict(capacity_alerts.DEFAULT_CONFIG))
    monkeypatch.setattr(capacity_alerts, "_dispatch_external", lambda event: (False, ""))
    monkeypatch.setattr(capacity_alerts, "_DISPATCH_STATES", type(capacity_alerts._DISPATCH_STATES)())
    rep.configure(stub.url)
    first = capacity_alerts.record_capacity_event("quota_exhausted", "Anthropic", source="streaming")
    repeat = capacity_alerts.record_capacity_event("quota_exhausted", "anthropic", source="streaming")
    assert first["deduplicated"] is False and repeat["deduplicated"] is True
    assert ops_reporter.flush(5) and _wait_for(lambda: stub.requests)
    time.sleep(0.2)
    (event,) = stub.events()  # the deduplicated repeat is not reported again
    assert event["kind"] == "health" and event["level"] == "warning"
    assert event["logger"] == "capacity.quota_exhausted"
    assert event["fingerprint"] == hashlib.sha1(b"webui|capacity|quota_exhausted|anthropic").hexdigest()
    assert "message" not in event and "context" not in event and "anthropic" not in stub.raw_text()


def test_capacity_hook_reports_fresh_incidents_only(tmp_path, monkeypatch):
    from api import capacity_alerts, config

    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(capacity_alerts, "effective_config", lambda: dict(capacity_alerts.DEFAULT_CONFIG))
    monkeypatch.setattr(capacity_alerts, "_dispatch_external", lambda event: (False, ""))
    monkeypatch.setattr(capacity_alerts, "_DISPATCH_STATES", type(capacity_alerts._DISPATCH_STATES)())
    calls = []
    monkeypatch.setattr(ops_reporter, "report_capacity", lambda *a, **k: calls.append((a, k)) or True)
    capacity_alerts.record_capacity_event("rate_limit", "openai", source="streaming")
    capacity_alerts.record_capacity_event("rate_limit", "openai", source="streaming")
    capacity_alerts.record_capacity_event("overloaded", "openai", source="cron")
    capacity_alerts.record_capacity_event("model_not_found", "openai")
    assert calls == [(("rate_limit", "openai"), {"source": "streaming"}),
                     (("overloaded", "openai"), {"source": "cron"})]

    def broken(*_a, **_k):
        raise RuntimeError("reporter exploded")

    monkeypatch.setattr(ops_reporter, "report_capacity", broken)
    result = capacity_alerts.record_capacity_event("quota_exhausted", "mistral")
    assert result["recorded"] is True and result["notified"] is True


def test_crash_hooks_hand_crashes_to_the_reporter(rep, stub):
    from api import crash_visibility

    rep.configure(stub.url)
    exc_type, exc_value, exc_tb = _exc_info()
    crash_visibility.thread_excepthook(SimpleNamespace(exc_type=exc_type, exc_value=exc_value,
                                                       exc_traceback=exc_tb, thread=threading.current_thread()))
    assert ops_reporter.flush(5) and _wait_for(lambda: stub.requests)
    (event,) = stub.events()
    assert event["level"] == "error" and event["logger"] == "crash_visibility"
    # The main thread is about to die: its crash goes straight to the spool.
    crash_visibility.main_excepthook(exc_type, exc_value, exc_tb)
    files = sorted(rep.spool.glob("*.json"))
    assert len(files) == 1
    (spooled,) = json.loads(files[0].read_text())["events"]
    assert spooled["level"] == "fatal" and spooled["kind"] == "error"
    # SystemExit in a thread and KeyboardInterrupt on the main thread are not crashes.
    crash_visibility.thread_excepthook(SimpleNamespace(exc_type=SystemExit, exc_value=SystemExit(0),
                                                       exc_traceback=None, thread=threading.current_thread()))
    crash_visibility.main_excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
    assert len(list(rep.spool.glob("*.json"))) == 1
    assert ops_reporter.stats()["queued"] == 1


def test_the_sender_thread_never_reports_itself(rep, stub):
    from api import crash_visibility

    rep.configure(stub.url)
    exc_type, exc_value, exc_tb = _exc_info()
    fake_sender = SimpleNamespace(name=ops_reporter.SENDER_THREAD_NAME, ident=1, daemon=True)
    crash_visibility.thread_excepthook(SimpleNamespace(exc_type=exc_type, exc_value=exc_value,
                                                       exc_traceback=exc_tb, thread=fake_sender))
    result = []
    thread = threading.Thread(target=lambda: result.append(ops_reporter.report_exception(exc_type, exc_value, exc_tb)),
                              name=ops_reporter.SENDER_THREAD_NAME)
    thread.start()
    thread.join()
    assert result == [False]
    assert ops_reporter.stats()["queued"] == 0


def test_install_starts_the_sender_only_for_a_waiting_spool(rep, stub, monkeypatch):
    from api import crash_visibility

    rep.configure(stub.url)
    for name in ("_INSTALLED", "_FAULT_STREAM", "_PREV_THREAD_HOOK", "_PREV_SYS_HOOK"):
        monkeypatch.setattr(crash_visibility, name, getattr(crash_visibility, name))
    monkeypatch.setattr(crash_visibility, "_INSTALLED", False)
    monkeypatch.setattr(crash_visibility.atexit, "register", lambda _fn: None)
    started = []
    monkeypatch.setattr(ops_reporter, "start", lambda: started.append(True) or False)
    prev_thread, prev_sys = threading.excepthook, sys.excepthook
    try:
        assert crash_visibility.install_crash_visibility(stream=io.StringIO(), enable_faulthandler=False,
                                                         register_sigusr1_dump=False) is True
    finally:
        threading.excepthook, sys.excepthook = prev_thread, prev_sys
    assert started == [True]


# ── Spool, backoff and recovery ──────────────────────────────────────────────

def test_failed_sends_are_spooled_redacted_and_drained_after_recovery(rep, stub, monkeypatch):
    rep.configure(stub.url)
    stub.statuses = [503]
    ops_reporter.report_exception(*_exc_info())
    assert ops_reporter.flush(5)
    assert _wait_for(lambda: list(rep.spool.glob("*.json")))
    files = list(rep.spool.glob("*.json"))
    assert len(files) == 1
    assert stat.S_IMODE(files[0].stat().st_mode) == 0o600
    assert stat.S_IMODE(rep.spool.stat().st_mode) == 0o700
    text = files[0].read_text()
    for secret in (CANARY, CANARY_TOKEN, "ada@acme.example"):
        assert secret not in text
    assert ops_reporter.stats()["spooled"] == 1
    # Backoff keeps the sender quiet; once it passes the spool drains.
    assert len(stub.requests) == 1
    monkeypatch.setattr(ops_reporter._S, "backoff_until", 0.0)
    with ops_reporter._S.cond:
        ops_reporter._S.cond.notify_all()
    assert _wait_for(lambda: not list(rep.spool.glob("*.json")), timeout=5)
    assert len(stub.requests) == 2
    assert stub.events()[0] == stub.events()[1]


def test_rejected_batches_are_dropped_not_spooled(rep, stub):
    rep.configure(stub.url)
    stub.statuses = [400]
    ops_reporter.report_exception(*_exc_info())
    assert ops_reporter.flush(5) and _wait_for(lambda: stub.requests)
    time.sleep(0.2)
    assert not list(rep.spool.glob("*.json")) if rep.spool.exists() else True
    assert ops_reporter.stats()["rejected"] == 1


def test_start_sends_what_a_previous_run_spooled(rep, stub):
    rep.configure(stub.url)
    exc = _exc_info()
    assert ops_reporter.report_exception(*exc, sync=True) is True
    assert _sender_threads() == []
    assert stub.requests == []
    assert ops_reporter.start() is True
    assert _wait_for(lambda: stub.requests and not list(rep.spool.glob("*.json")))
    assert stub.events()[0]["exception"]["type"] == "ValueError"


def test_a_spool_file_that_cannot_be_removed_is_sent_once(rep, stub, monkeypatch):
    rep.configure(stub.url)
    monkeypatch.setattr(ops_reporter, "IDLE_EXIT_S", 0.3)
    assert ops_reporter.report_exception(*_exc_info(), sync=True) is True
    rep.spool.chmod(0o500)  # the file can be read but not removed
    try:
        assert ops_reporter.start() is True
        assert _wait_for(lambda: stub.requests)
        assert _wait_for(lambda: not _sender_threads(), timeout=5)
        assert len(stub.requests) == 1
        assert len(list(rep.spool.glob("*.json"))) == 1
    finally:
        rep.spool.chmod(0o700)


def test_spool_files_are_re_sanitized_when_read_back(rep, stub):
    rep.configure(stub.url)
    rep.spool.mkdir(parents=True)
    tampered = {"v": 1, "events": [
        {"ts": "2026-09-28T07:00:00.000Z", "service": "evil", "kind": "error", "level": "error",
         "message": f"{CANARY} ada@acme.example", "context": {"thread": "t"}, "extra": "dropped",
         "exception": {"type": "ValueError", "value": CANARY, "frames": [
             {"function": "f", "module": "api.routes", "in_app": True, "vars": {"password": "x"}},
             {"function": "g", "module": "json.decoder", "in_app": False}]}},
        {"ts": "yesterday", "kind": "error", "level": "error"},
        "not an event",
    ]}
    (rep.spool / "00000000000000000001-aaaaaaaa.json").write_text(json.dumps(tampered))
    assert ops_reporter.start() is True
    assert _wait_for(lambda: stub.requests)
    (event,) = stub.events()
    assert event == {"ts": "2026-09-28T07:00:00.000Z", "service": "webui", "kind": "error", "level": "error",
                     "exception": {"type": "ValueError",
                                   "frames": [{"function": "f", "module": "api.routes", "in_app": True}]}}


def test_spool_is_bounded(rep, monkeypatch):
    rep.configure("http://127.0.0.1:9")
    monkeypatch.setattr(ops_reporter, "SPOOL_MAX_FILES", 3)
    for _ in range(6):
        assert ops_reporter.report_exception(*_exc_info(), sync=True) is True
    assert len(list(rep.spool.glob("*.json"))) == 3
    monkeypatch.setattr(ops_reporter, "SPOOL_MAX_FILES", 100)
    monkeypatch.setattr(ops_reporter, "SPOOL_MAX_BYTES", 1)
    ops_reporter.report_exception(*_exc_info(), sync=True)
    assert list(rep.spool.glob("*.json")) == []
    old = rep.spool / "00000000000000000001-bbbbbbbb.json"
    monkeypatch.setattr(ops_reporter, "SPOOL_MAX_BYTES", 10**6)
    old.write_text(json.dumps({"v": 1, "events": []}))
    os.utime(old, (time.time() - ops_reporter.SPOOL_MAX_AGE_S - 10,) * 2)
    ops_reporter.report_exception(*_exc_info(), sync=True)
    assert not old.exists()


def test_atexit_keeps_queued_events_in_the_spool(rep, stub):
    rep.configure(stub.url)
    stub.hold.clear()  # the first send blocks, so later events stay queued
    ops_reporter.report_exception(*_exc_info())
    assert _wait_for(lambda: ops_reporter.stats()["pending"] == 0)
    ops_reporter.report_exception(*_exc_info())
    ops_reporter.report_exception(*_exc_info())
    assert ops_reporter.stats()["pending"] == 2
    ops_reporter._shutdown()
    files = list(rep.spool.glob("*.json"))
    assert len(files) == 1 and len(json.loads(files[0].read_text())["events"]) == 2
    # After shutdown a report goes to the spool directly.
    assert ops_reporter.report_exception(*_exc_info()) is True
    assert len(list(rep.spool.glob("*.json"))) == 2
    stub.hold.set()


# ── Bounded, non-blocking, never raising ─────────────────────────────────────

def test_queue_is_bounded_and_reporting_never_blocks(rep, stub, monkeypatch):
    rep.configure(stub.url)
    monkeypatch.setattr(ops_reporter, "MAX_QUEUE", 5)
    stub.hold.clear()  # control-api hangs
    started = time.monotonic()
    results = [ops_reporter.report_exception(*_exc_info()) for _ in range(20)]
    elapsed = time.monotonic() - started
    assert elapsed < 1.0
    stats = ops_reporter.stats()
    # The queue holds at most MAX_QUEUE; the sender holds one batch in flight.
    assert stats["pending"] <= 5 and False in results
    assert stats["dropped"] == results.count(False) >= 10
    stub.hold.set()


def test_reporting_never_raises(rep, stub, monkeypatch):
    rep.configure(stub.url, diagnostic="1")

    def broken(*_a, **_k):
        raise RuntimeError("exploded")

    class Unprintable(Exception):
        def __str__(self):
            raise RuntimeError("no str")

    try:
        raise Unprintable()
    except Unprintable:
        info = sys.exc_info()
    assert ops_reporter.report_exception(*info) is True
    assert ops_reporter.report_exception(None, None, None) is False
    assert ops_reporter.report_exception(ValueError, ValueError("x"), None, level="bogus", context="nope") is True
    monkeypatch.setattr(cpc, "post_events", broken)
    assert ops_reporter.report_exception(*_exc_info()) is True
    ops_reporter.flush(2)
    monkeypatch.setattr(ops_reporter, "_python_frames", broken)
    assert ops_reporter.report_exception(*_exc_info()) is False
    monkeypatch.setattr(ops_reporter, "enabled", broken)
    assert ops_reporter.browser_reporting_enabled() is False
    assert ops_reporter.report_capacity("rate_limit", "x") is False
    handler = _Handler(headers={"Content-Length": "2"})
    assert ops_reporter.handle_client_error(handler, {}) is True and handler.status == 204


def test_redaction_patterns():
    cases = {
        "mail ada@acme.example now": "mail [email] now",
        "Authorization: Bearer abc.def.ghi": "Authorization: [redacted]",
        "SP-HMAC-SHA256 kid=0a1b2c3d4e5f6071, ts=1, nonce=aa, sig=bb end": "[redacted] end",
        "SP-Ingest 0123456789abcdef0123456789abcdef": "[redacted]",
        "https://user:pw@host.example/p?token=abc#frag x": "https://host.example/p x",
        "call +31 6 12345678": "call [number]",
        "IBAN NL91ABNA0417164300": "IBAN [iban]",
        "key sk-abcdefghijklmnop and ghp_abcdefghijk and xoxb-12345678901 and live_abcdefghij": (
            "key [redacted] and [redacted] and [redacted] and [redacted]"),
        "jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijk": "jwt [jwt]",
        "id 3f2a9c1e-1111-2222-3333-444455556666": "id [id]",
        "hex 0123456789abcdef0123456789abcdef": "hex [id]",
        "password=hunter2&x=1": "password=[redacted]&x=1",
        "line 12345 col 7": "line 12345 col 7",
        "tab\there\nnewline": "tab here newline",
    }
    for raw, expected in cases.items():
        assert ops_reporter.redact(raw) == expected, raw
    assert ops_reporter.redact(None) is None
    assert ops_reporter.redact("") is None
    assert len(ops_reporter.redact("x" * 10000)) == ops_reporter.MAX_MESSAGE
    started = time.monotonic()
    ops_reporter.redact("1 " * 3000)
    ops_reporter.redact("a@" * 3000)
    assert time.monotonic() - started < 0.5


# ── POST /api/client-errors ──────────────────────────────────────────────────

def test_client_error_is_allowlisted_redacted_and_public_origin(rep, stub, monkeypatch):
    rep.configure(stub.url, diagnostic="1")
    handler = _post_client_error(_client_body(), monkeypatch=monkeypatch)
    assert handler.status == 204 and handler.raw == b""
    assert ops_reporter.flush(5) and _wait_for(lambda: stub.requests)
    (event,) = stub.events()
    assert event["kind"] == "client_error" and event["public_origin"] is True
    assert event["logger"] == "browser" and event["level"] == "error"
    assert event["exception"]["type"] == "TypeError"
    assert event["exception"]["frames"] == [
        {"function": "outer", "module": "static/boot.js", "in_app": True},
        {"function": "renderMessages", "module": "static/ui.js", "in_app": True},
    ]
    assert event["exception"]["value"] == "x is undefined ([redacted]) for [email]"
    assert event["context"] == {"url_path": "/session/abc", "event": "error"}
    assert CANARY_TOKEN not in stub.raw_text() and "ada@acme.example" not in stub.raw_text()
    assert "secret" not in json.dumps(event["context"])


def test_client_error_size_limit(rep, stub, monkeypatch):
    rep.configure(stub.url, diagnostic="1")
    handler = _post_client_error(_client_body(), length=16 * 1024 + 1, monkeypatch=monkeypatch)
    assert handler.status == 413
    big = _client_body(message="m" * (17 * 1024))
    handler = _post_client_error(big, length=100, monkeypatch=monkeypatch)
    assert handler.status == 413
    handler = _post_client_error(_client_body(), length="abc", monkeypatch=monkeypatch)
    assert handler.status == 400
    assert ops_reporter.stats()["queued"] == 0


def test_client_error_rate_limit_is_per_user(rep, stub, monkeypatch):
    rep.configure(stub.url, diagnostic="1")
    monkeypatch.setattr(ops_reporter, "MAX_QUEUE", 1000)
    stub.hold.clear()
    statuses = [_post_client_error(_client_body(message=f"m{i}"), monkeypatch=monkeypatch).status for i in range(31)]
    assert statuses[:30] == [204] * 30 and statuses[30] == 429
    limited = _post_client_error(_client_body(), monkeypatch=monkeypatch)
    assert limited.status == 429 and limited.header("Retry-After") == "60"
    assert _post_client_error(_client_body(), email=OTHER, monkeypatch=monkeypatch).status == 204
    # A minute later the first user may report again.
    assert ops_reporter._client_error_rate_limited("user:" + MEMBER, now=time.time() + 61) is False
    stub.hold.set()


def test_client_error_rejects_bad_reports(rep, stub, monkeypatch):
    rep.configure(stub.url, diagnostic="1")
    for body in ([1, 2], "text", {}, {"frames": "nope"}, {"url_path": "/x"}):
        handler = _Handler(headers={"Content-Length": "10"})
        ops_reporter.handle_client_error(handler, body)
        assert handler.status == 400, body
        assert json.loads(handler.raw) == {"error": "invalid_report"}
    assert ops_reporter.stats()["queued"] == 0


def test_client_error_reads_its_own_body_with_the_cap(rep, stub, monkeypatch):
    rep.configure(stub.url, diagnostic="1")
    raw = json.dumps(_client_body()).encode()
    handler = _Handler(headers={"Content-Length": str(len(raw))}, body=raw)
    assert ops_reporter.handle_client_error(handler, None) is True and handler.status == 204
    big = _Handler(headers={"Content-Length": str(20 * 1024)}, body=b"{" + b" " * 20 * 1024)
    ops_reporter.handle_client_error(big, None)
    assert big.status == 413 and big.rfile.tell() == 0  # never read past the cap
    assert ops_reporter.flush(5) and _wait_for(lambda: stub.requests)
    assert len(stub.events()) == 1


def test_client_error_closes_the_connection_when_it_leaves_the_body_unread(rep, stub, monkeypatch):
    raw = json.dumps(_client_body()).encode()
    # Off: 204 without reading the body, so the connection must not be reused.
    off = _Handler(headers={"Content-Length": str(len(raw))}, body=raw)
    assert ops_reporter.handle_client_error(off, None) is True and off.status == 204
    assert off.rfile.tell() == 0 and off.close_connection is True
    empty = _Handler(headers={"Content-Length": "0"})
    ops_reporter.handle_client_error(empty, None)
    assert empty.status == 204 and getattr(empty, "close_connection", False) is False

    rep.configure(stub.url, diagnostic="1")
    monkeypatch.setattr(ops_reporter, "_client_error_rate_limited", lambda *_a, **_k: True)
    limited = _Handler(headers={"Content-Length": str(len(raw))}, body=raw)
    ops_reporter.handle_client_error(limited, None)
    assert limited.status == 429 and limited.rfile.tell() == 0 and limited.close_connection is True
    bad = _Handler(headers={"Content-Length": "abc"}, body=raw)
    ops_reporter.handle_client_error(bad, None)
    assert bad.status == 400 and bad.close_connection is True
    # A body the caller already read leaves the connection alone.
    kept = _Handler(headers={"Content-Length": str(len(raw))})
    ops_reporter.handle_client_error(kept, _client_body())
    assert kept.status == 429 and getattr(kept, "close_connection", False) is False


# ── The browser never sees key material ──────────────────────────────────────

POLICY = {
    "version": 1,
    "mode": "enforce",
    "default_effect": "deny",
    "bootstrap_admins": ["boot@example.test"],
    "roles": {"member": {"grants": {"permissions": ["chat:use", "sessions:read", "sessions:write"],
                                    "profiles": ["*"], "routes": ["*"]}}},
    "users": {MEMBER: {"roles": ["member"]}},
}


@pytest.fixture
def dispatch(monkeypatch):
    import api.governance.enforce as enforce
    import api.routes as routes
    from api.governance import loader
    from api.governance.loader import parse_governance_policy

    policy = parse_governance_policy(POLICY)
    loader.set_policy_loader(lambda: policy)
    monkeypatch.setattr(enforce, "_request_identity",
                        lambda _h: {"email": MEMBER, "groups": [], "claims_subset": {}, "method": "oidc"})
    monkeypatch.setattr(routes, "_check_csrf", lambda _handler: True)
    monkeypatch.setattr(routes, "_guard_request_session_visibility",
                        lambda handler, parsed, body=None, method="GET": True)

    def get(path):
        handler = _Handler()
        routes.handle_get(handler, urlparse("http://localhost" + path))
        return handler

    def post(path, body):
        monkeypatch.setattr(routes, "read_body", lambda _handler: copy.deepcopy(body))
        raw = json.dumps(body).encode()
        handler = _Handler(headers={"Content-Length": str(len(raw))})
        handler.rfile = io.BytesIO(raw)
        routes.handle_post(handler, SimpleNamespace(path=path, query=""))
        return handler

    yield SimpleNamespace(get=get, post=post)
    loader.set_policy_loader(None)


def test_settings_flag_and_no_key_material_in_browser_responses(rep, stub, dispatch, monkeypatch):
    handler = dispatch.get("/api/settings")
    assert handler.status == 200 and json.loads(handler.raw)["support_telemetry"] is False

    rep.configure(stub.url, telemetry="1", diagnostic=None, control=True)
    assert json.loads(dispatch.get("/api/settings").raw)["support_telemetry"] is False
    monkeypatch.setenv("SP_DIAGNOSTIC_PAYLOADS", "1")
    responses = [dispatch.get("/api/settings")]
    assert json.loads(responses[0].raw)["support_telemetry"] is True
    responses.append(dispatch.post("/api/client-errors", _client_body()))
    responses.append(dispatch.post("/api/client-errors", {"bad": True}))
    assert [r.status for r in responses] == [200, 204, 400]
    ops_reporter.flush(5)
    browser_bytes = b"".join(r.raw + json.dumps(r.response_headers).encode() for r in responses)
    for material in (INGEST_KEY_ID, INGEST_SECRET_HEX, SENTRY_KEY, CONTROL_KEY_ID, CONTROL_SECRET_HEX,
                     str(rep.tmp / "ingest.key"), str(rep.tmp / "control.key"), stub.url, "SP-Ingest"):
        assert material.encode() not in browser_bytes, material
    script = (REPO / "static" / "error-reporter.js").read_text(encoding="utf-8")
    for word in ("SP-Ingest", "sentry", "dsn", "SP_CONTROL", "/v1/", "control.key", "ingest.key"):
        assert word.lower() not in script.lower(), word


# ── Browser side ─────────────────────────────────────────────────────────────

@pytest.mark.skipif(NODE is None, reason="node not on PATH")
def test_error_reporter_js_behaviour():
    done = subprocess.run([NODE, str(REPO / "tests" / "error_reporter.cjs")], cwd=str(REPO),
                          capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "all error-reporter checks passed" in done.stdout


def test_error_reporter_js_copy_has_no_dashes_or_internal_names():
    script = (REPO / "static" / "error-reporter.js").read_text(encoding="utf-8")
    assert chr(0x2013) not in script and chr(0x2014) not in script
    for name in ("n8n", "OmniRoute", "LangGraph", "Hermes", "LiteLLM"):
        assert name.lower() not in script.lower(), name
