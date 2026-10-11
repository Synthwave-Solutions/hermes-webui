"""Control-plane client: HMAC signing per plan Appendix B (W7).

The stub control-api in this file verifies requests with its own reading of
Appendix B (not with the client's code): the signature over method, path with
query, timestamp, nonce, the three acting headers and the body hash, a 300 s
timestamp window and a (kid, nonce) replay cache. The client must be accepted
by it, a replayed or altered request must be refused, and nothing may be sent
while the client is not configured.
"""
from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import logging
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import control_plane_client as cpc  # noqa: E402

KEY_ID = "0a1b2c3d4e5f6071"
SECRET_HEX = "5f" * 16 + "a0" * 16  # 64 hex, 32 bytes
INGEST_KEY_ID = "1122334455667788"
INGEST_SECRET_HEX = "c3" * 32
ACTING = {"user": "Ada@Acme.Example", "member_of": ["sales", "finance"], "admin_of": ["sales"]}


# ── Stub control-api (its own reading of Appendix B) ─────────────────────────

def _parse_authorization(value: str):
    scheme, _, rest = value.partition(" ")
    if scheme != "SP-HMAC-SHA256":
        return None
    fields = {}
    for part in rest.split(","):
        name, _, val = part.strip().partition("=")
        fields[name] = val
    return fields if set(fields) == {"kid", "ts", "nonce", "sig"} else None


class StubControlApi:
    """A tiny control-api: verifies signed requests, records what it saw."""

    def __init__(self, secrets_by_kid, *, window=300):
        self.secrets = dict(secrets_by_kid)
        self.window = window
        self.seen_nonces = {}
        self.requests = []
        self.raw = []
        self.response = None  # (status, headers, body bytes) override
        self.delay = 0.0
        self.closed = False
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _handle(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                headers = {k: v for k, v in self.headers.items()}
                stub.raw.append((self.command, self.path, headers, body))
                if stub.delay:
                    time.sleep(stub.delay)
                if stub.response is not None:
                    status, extra, payload = stub.response
                    self.send_response(status)
                    for key, value in extra.items():
                        self.send_header(key, value)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                status, payload = stub.verify(self.command, self.path, headers, body)
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _handle

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return "http://127.0.0.1:%d" % self.server.server_address[1]

    def verify(self, method, path, headers, body):
        lower = {k.lower(): v for k, v in headers.items()}
        fields = _parse_authorization(lower.get("authorization", ""))
        if fields is None:
            return 401, {"error": {"code": "unauthenticated", "message": "no signature"}}
        secret = self.secrets.get(fields["kid"])
        if secret is None:
            return 401, {"error": {"code": "unknown_key", "message": "unknown key"}}
        now = time.time()
        if not fields["ts"].isdigit() or abs(now - int(fields["ts"])) > self.window:
            return 401, {"error": {"code": "stale", "message": "timestamp outside the window"}}
        acting = [lower.get(name.lower(), "") for name in
                  ("X-SP-Acting-User", "X-SP-Acting-Member-Of", "X-SP-Acting-Admin-Of")]
        message = ("v1\n" + method + "\n" + path + "\n" + fields["ts"] + "\n" + fields["nonce"] + "\n"
                   + acting[0] + "\n" + acting[1] + "\n" + acting[2] + "\n"
                   + hashlib.sha256(body).hexdigest())
        expected = hmac.new(secret, message.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, fields["sig"]):
            return 401, {"error": {"code": "bad_signature", "message": "signature mismatch"}}
        key = (fields["kid"], fields["nonce"])
        seen = self.seen_nonces.get(key)
        if seen is not None and now - seen <= self.window:
            return 401, {"error": {"code": "replayed", "message": "nonce already used"}}
        self.seen_nonces[key] = now
        self.requests.append({"method": method, "path": path, "acting": acting,
                              "body": json.loads(body) if body else None})
        status = 201 if method == "POST" else 200
        return status, {"ok": True, "path": path, "acting": acting}

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def stub():
    server = StubControlApi({KEY_ID: bytes.fromhex(SECRET_HEX)})
    yield server
    server.close()


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated env: no control-plane variables and no proxies."""
    for name in ("SP_CONTROL_SOCKET", "SP_CONTROL_URL", "SP_CONTROL_KEY_FILE", "SP_INGEST_KEY_FILE",
                 "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    cpc.clear_cache()

    def write_key(name, content, mode=0o600):
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        path.chmod(mode)
        return path

    def configure(url, *, control=True, ingest=False):
        monkeypatch.setenv("SP_CONTROL_URL", url)
        if control:
            path = write_key("control.key", json.dumps(
                {"kind": "control", "key_id": KEY_ID, "secret": SECRET_HEX, "allowed_ingress": "tailnet"}))
            monkeypatch.setenv("SP_CONTROL_KEY_FILE", str(path))
        if ingest:
            path = write_key("ingest.key", json.dumps(
                {"kind": "ingest", "key_id": INGEST_KEY_ID, "secret": INGEST_SECRET_HEX, "allowed_ingress": "tailnet"}))
            monkeypatch.setenv("SP_INGEST_KEY_FILE", str(path))

    yield type("Env", (), {"configure": staticmethod(configure), "write_key": staticmethod(write_key),
                           "tmp": tmp_path})
    cpc.clear_cache()


# ── Configuration ────────────────────────────────────────────────────────────

def test_not_configured_without_env_and_sends_nothing(env, monkeypatch):
    sent = []
    monkeypatch.setattr(cpc, "_send", lambda *a, **k: sent.append(a) or (200, {}))
    assert cpc.configured() is False
    assert cpc.ingest_configured() is False
    status, body = cpc.call("GET", "/v1/whoami")
    assert status == 0 and body["error"]["code"] == "not_configured"
    status, body = cpc.post_events([{"kind": "error"}])
    assert status == 0 and body["error"]["code"] == "not_configured"
    assert sent == []


@pytest.mark.parametrize("url", [
    "", "ftp://control.example", "control.example", "https://user:pw@control.example",
    "https://control.example/?x=1", "https://control.example/#f", "https://control.example:99999",
    "https://control example", "https://",
])
def test_invalid_base_url_means_not_configured(env, monkeypatch, url):
    env.configure("https://control.example")
    monkeypatch.setenv("SP_CONTROL_URL", url)
    assert cpc.configured() is False


@pytest.mark.parametrize("content", [
    "", "   ", "{not json", "[1, 2]", json.dumps({"kind": "ingest", "key_id": KEY_ID, "secret": SECRET_HEX}),
    json.dumps({"kind": "control", "key_id": "XYZ", "secret": SECRET_HEX}),
    json.dumps({"kind": "control", "key_id": KEY_ID, "secret": "not-hex"}),
    json.dumps({"kind": "control", "key_id": KEY_ID, "secret": "ab"}),
    KEY_ID + SECRET_HEX, KEY_ID + ":" + SECRET_HEX + ":extra", "x" * 5000,
])
def test_unusable_control_key_file_means_not_configured(env, monkeypatch, content):
    env.configure("https://control.example")
    monkeypatch.setenv("SP_CONTROL_KEY_FILE", str(env.write_key("bad.key", content)))
    assert cpc.configured() is False


def test_missing_key_file_means_not_configured(env, monkeypatch):
    env.configure("https://control.example")
    monkeypatch.setenv("SP_CONTROL_KEY_FILE", str(env.tmp / "absent.key"))
    assert cpc.configured() is False


@pytest.mark.parametrize("content", [
    json.dumps({"kind": "control", "key_id": KEY_ID, "secret": SECRET_HEX, "allowed_ingress": "public"}),
    json.dumps({"key_id": KEY_ID.upper(), "secret": SECRET_HEX.upper()}),
    f"{KEY_ID}:{SECRET_HEX}\n",
])
def test_usable_control_key_formats(env, monkeypatch, content):
    env.configure("https://control.example/")
    monkeypatch.setenv("SP_CONTROL_KEY_FILE", str(env.write_key("ok.key", content)))
    assert cpc.configured() is True


# ── Signing ──────────────────────────────────────────────────────────────────

def test_known_answer_vectors():
    """Fixed vectors for C1's verifier to reuse (secret bytes = bytes.fromhex(secret))."""
    secret = bytes.fromhex("00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff")
    body = b'{"need":"question","title":"Printer"}'
    header = cpc.sign(secret, KEY_ID, "POST", "/v1/tickets", body=body,
                      acting_values=("ada@acme.example", "sales,finance", "sales"),
                      ts="1790000000", nonce="0123456789abcdef0123456789abcdef")
    assert header == ("SP-HMAC-SHA256 kid=0a1b2c3d4e5f6071, ts=1790000000, "
                      "nonce=0123456789abcdef0123456789abcdef, "
                      "sig=11e977a0f99ef0247b7a1a3ce51e38fab7b08db3b0d45c6225c521776946ddea")
    header = cpc.sign(secret, KEY_ID, "GET", "/v1/whoami", ts="1790000000",
                      nonce="ffffffffffffffffffffffffffffffff")
    assert header.endswith("sig=919e48e6029d7ecab3ef484da5c6ccef4ec6b9cb1d796d9d2f43cd24b2ddb7fb")


def test_stub_accepts_signed_requests_with_acting_headers(env, stub):
    env.configure(stub.url)
    assert cpc.configured() is True
    status, body = cpc.call("POST", "/v1/tickets", body={"need": "question", "title": "Printer"}, acting=ACTING)
    assert status == 201 and body["ok"] is True
    status, body = cpc.call("GET", "/v1/tickets?scope=mine&status=open",
                            acting={"X-SP-Acting-User": "ada@acme.example", "X-SP-Acting-Member-Of": "sales"})
    assert status == 200
    status, body = cpc.call("GET", "/v1/whoami")
    assert status == 200
    first, second, third = stub.requests
    assert first["acting"] == ["ada@acme.example", "sales,finance", "sales"]
    assert first["body"] == {"need": "question", "title": "Printer"}
    assert second["path"] == "/v1/tickets?scope=mine&status=open"
    assert second["acting"] == ["ada@acme.example", "sales", ""]
    assert third["acting"] == ["", "", ""]
    # Without acting the headers are not sent at all (signed as empty strings).
    assert not any(k.lower().startswith("x-sp-acting") for k in stub.raw[2][2])
    nonces = [_parse_authorization(raw[2]["Authorization"])["nonce"] for raw in stub.raw]
    assert len(set(nonces)) == 3 and all(len(n) == 32 for n in nonces)


def test_stub_rejects_a_replayed_request(env, stub):
    env.configure(stub.url)
    status, _ = cpc.call("POST", "/v1/tickets", body={"title": "x"}, acting=ACTING)
    assert status == 201
    method, path, headers, body = stub.raw[-1]
    conn = http.client.HTTPConnection("127.0.0.1", stub.server.server_address[1], timeout=5)
    replay_headers = {k: v for k, v in headers.items() if k.lower() not in ("host", "connection")}
    conn.request(method, path, body=body, headers=replay_headers)
    response = conn.getresponse()
    payload = json.loads(response.read())
    conn.close()
    assert response.status == 401 and payload["error"]["code"] == "replayed"
    assert len(stub.requests) == 1


def test_stub_rejects_an_altered_request(env, stub):
    env.configure(stub.url)
    cpc.call("POST", "/v1/tickets", body={"title": "x"}, acting=ACTING)
    method, path, headers, body = stub.raw[-1]
    for change in ("body", "acting", "path"):
        altered = {k: v for k, v in headers.items() if k.lower() not in ("host", "connection")}
        new_path, new_body = path, body
        if change == "body":
            new_body = body.replace(b'"x"', b'"y"')
        elif change == "acting":
            altered["X-SP-Acting-Admin-Of"] = "sales,finance"
        else:
            new_path = "/v1/tickets?scope=org"
        conn = http.client.HTTPConnection("127.0.0.1", stub.server.server_address[1], timeout=5)
        conn.request(method, new_path, body=new_body, headers=altered)
        response = conn.getresponse()
        payload = json.loads(response.read())
        conn.close()
        assert response.status == 401 and payload["error"]["code"] == "bad_signature", change


def test_stub_rejects_a_stale_timestamp(env, stub):
    header = cpc.sign(bytes.fromhex(SECRET_HEX), KEY_ID, "GET", "/v1/whoami", ts=str(int(time.time()) - 301))
    conn = http.client.HTTPConnection("127.0.0.1", stub.server.server_address[1], timeout=5)
    conn.request("GET", "/v1/whoami", headers={"Authorization": header})
    response = conn.getresponse()
    assert response.status == 401 and json.loads(response.read())["error"]["code"] == "stale"
    conn.close()


def test_a_base_path_prefix_is_signed_as_sent(env, stub):
    env.configure(stub.url + "/control/")
    status, _ = cpc.call("GET", "/v1/whoami")
    assert status == 200
    assert stub.raw[-1][1] == "/control/v1/whoami"


def test_rotated_key_file_is_picked_up(env, stub, monkeypatch):
    env.configure(stub.url)
    assert cpc.call("GET", "/v1/whoami")[0] == 200
    new_kid, new_secret = "fedcba9876543210", "11" * 32
    stub.secrets[new_kid] = bytes.fromhex(new_secret)
    time.sleep(0.01)
    env.write_key("control.key", json.dumps({"kind": "control", "key_id": new_kid, "secret": new_secret}))
    assert cpc.call("GET", "/v1/whoami")[0] == 200
    assert _parse_authorization(stub.raw[-1][2]["Authorization"])["kid"] == new_kid


# ── Refusals before anything is sent ─────────────────────────────────────────

@pytest.mark.parametrize("method,path,kwargs", [
    ("TRACE", "/v1/whoami", {}),
    ("GET", "v1/whoami", {}),
    ("GET", "/v2/whoami", {}),
    ("GET", "/sentry/api/1/envelope/", {}),
    ("GET", "https://evil.example/v1/whoami", {}),
    ("GET", "/v1/../admin", {}),
    ("GET", "/v1//tickets", {}),
    ("GET", "/v1/tickets\r\nX-Evil: 1", {}),
    ("GET", "/v1/tickets\n", {}),
    ("GET", "/v1/tick ets", {}),
    ("POST", "/v1/tickets", {"acting": {"user": "not an email"}}),
    ("POST", "/v1/tickets", {"acting": {"user": "a@b.example\r\nX-Evil: 1"}}),
    ("POST", "/v1/tickets", {"acting": {"user": "é@b.example"}}),
    ("POST", "/v1/tickets", {"acting": {"member_of": ["Sales"]}}),
    ("POST", "/v1/tickets", {"acting": {"member_of": ["sales,finance"]}}),
    ("POST", "/v1/tickets", {"acting": {"member_of": [f"d{i}" for i in range(65)]}}),
    ("POST", "/v1/tickets", {"acting": {"admin_of": 5}}),
    ("POST", "/v1/tickets", {"acting": {"department": "sales"}}),
    ("POST", "/v1/tickets", {"acting": ["ada@acme.example"]}),
    ("POST", "/v1/tickets", {"body": {"bad": float("nan")}}),
    ("POST", "/v1/tickets", {"body": {"blob": "x" * (300 * 1024)}}),
])
def test_invalid_requests_are_refused_locally(env, stub, method, path, kwargs):
    env.configure(stub.url)
    status, body = cpc.call(method, path, **kwargs)
    assert status == 0 and body["error"]["code"] == "invalid_request"
    assert stub.raw == []


def test_redirects_are_never_followed(env, stub):
    other = StubControlApi({KEY_ID: bytes.fromhex(SECRET_HEX)})
    try:
        env.configure(stub.url)
        stub.response = (302, {"Location": other.url + "/v1/whoami"}, b"")
        status, body = cpc.call("GET", "/v1/whoami")
        assert status == 0 and body["error"]["code"] == "redirect_refused"
        assert other.raw == []
    finally:
        other.close()


def test_http_errors_come_back_with_their_json(env, stub):
    env.configure(stub.url)
    stub.response = (403, {"Content-Type": "application/json"},
                     b'{"error": {"code": "forbidden", "message": "not an org admin"}}')
    assert cpc.call("GET", "/v1/org/summary", acting=ACTING) == (
        403, {"error": {"code": "forbidden", "message": "not an org admin"}})
    stub.response = (200, {}, b"<html>not json</html>")
    status, body = cpc.call("GET", "/v1/whoami")
    assert status == 200 and body["error"]["code"] == "invalid_response"
    stub.response = (204, {}, b"")
    assert cpc.call("DELETE", "/v1/tickets/t1") == (204, {})
    stub.response = (200, {}, b"x" * (cpc.MAX_RESPONSE_BYTES + 10))
    status, body = cpc.call("GET", "/v1/whoami")
    assert body["error"]["code"] == "invalid_response"


def test_timeout_and_unreachable_are_local_errors(env, stub):
    env.configure(stub.url)
    stub.delay = 1.5
    started = time.monotonic()
    status, body = cpc.call("GET", "/v1/whoami", timeout=0.3)
    assert status == 0 and body["error"]["code"] == "timeout"
    assert time.monotonic() - started < 1.4
    stub.delay = 0
    port = stub.server.server_address[1]
    stub.close()
    env.configure(f"http://127.0.0.1:{port}")
    status, body = cpc.call("GET", "/v1/whoami", timeout=1)
    assert status == 0 and body["error"]["code"] in ("unreachable", "timeout")


def test_call_never_raises(env, stub, monkeypatch):
    env.configure(stub.url)

    def broken(*_args, **_kwargs):
        raise RuntimeError("socket exploded")

    monkeypatch.setattr(cpc, "_opener", broken)
    status, body = cpc.call("GET", "/v1/whoami")
    assert status == 0 and body["error"]["code"] == "unreachable"
    monkeypatch.setattr(cpc, "_base_url", broken)
    assert cpc.call("GET", "/v1/whoami")[0] == 0
    assert cpc.configured() is False
    assert cpc.ingest_configured() is False


# ── Ingest key ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("content,expected", [
    (json.dumps({"kind": "ingest", "key_id": INGEST_KEY_ID, "secret": INGEST_SECRET_HEX}),
     INGEST_KEY_ID + INGEST_SECRET_HEX[:16]),
    (f"{INGEST_KEY_ID}:{INGEST_SECRET_HEX}", INGEST_KEY_ID + INGEST_SECRET_HEX[:16]),
    ("ABCDEF0123456789abcdef0123456789\n", "abcdef0123456789abcdef0123456789"),
    (json.dumps({"sentry_key": "abcdef0123456789abcdef0123456789"}), "abcdef0123456789abcdef0123456789"),
    (json.dumps({"kind": "ingest_public", "key_id": INGEST_KEY_ID, "secret": INGEST_SECRET_HEX}), None),
    (json.dumps({"kind": "control", "key_id": INGEST_KEY_ID, "secret": INGEST_SECRET_HEX}), None),
    ("abcdef0123456789", None),
])
def test_ingest_key_formats(env, stub, monkeypatch, content, expected):
    env.configure(stub.url, control=False)
    monkeypatch.setenv("SP_INGEST_KEY_FILE", str(env.write_key("ingest.key", content)))
    stub.response = (202, {"Content-Type": "application/json"}, b'{"accepted": 1, "dropped": 0}')
    status, body = cpc.post_events([{"kind": "error"}])
    if expected is None:
        assert cpc.ingest_configured() is False
        assert status == 0 and stub.raw == []
        return
    assert cpc.ingest_configured() is True
    assert (status, body) == (202, {"accepted": 1, "dropped": 0})
    method, path, headers, raw = stub.raw[-1]
    assert (method, path) == ("POST", "/v1/events")
    assert headers["Authorization"] == "SP-Ingest " + expected
    assert json.loads(raw) == {"events": [{"kind": "error"}]}


def test_post_events_bounds(env, stub):
    env.configure(stub.url, control=False, ingest=True)
    assert cpc.post_events([])[0] == 0
    assert cpc.post_events([{}] * 101)[0] == 0
    assert cpc.post_events("nope")[0] == 0
    assert cpc.post_events([{"x": "y" * (300 * 1024)}])[0] == 0
    assert stub.raw == []


# ── No key material anywhere else ────────────────────────────────────────────

def test_key_material_never_appears_in_results_or_logs(env, stub, caplog):
    env.configure(stub.url, ingest=True)
    caplog.set_level(logging.DEBUG)
    outputs = [
        cpc.call("GET", "/v1/whoami"),
        cpc.call("GET", "/v1/whoami", timeout=0.0001),
        cpc.post_events([{"kind": "error"}]),
    ]
    stub.response = (500, {}, b"boom")
    outputs.append(cpc.call("GET", "/v1/whoami"))
    stub.close()
    outputs.append(cpc.call("GET", "/v1/whoami", timeout=1))
    outputs.append(cpc.post_events([{"kind": "error"}], timeout=1))
    text = json.dumps(outputs) + caplog.text + repr(cpc.configured()) + repr(cpc.ingest_configured())
    for secret in (SECRET_HEX, INGEST_SECRET_HEX, INGEST_KEY_ID + INGEST_SECRET_HEX[:16]):
        assert secret not in text


def test_unix_socket_preserves_signed_identity_body_and_rejects_redirect(env,stub,monkeypatch,tmp_path):
    from socketserver import ThreadingUnixStreamServer
    path=str(tmp_path/'c.sock')
    # Permit only this private test socket; keep all other network guards.
    from tests.conftest import _REAL_SOCKET_CONNECT
    import socket
    guarded=socket.socket.connect
    def connect(sock,address):
        if sock.family==socket.AF_UNIX and address==path:return _REAL_SOCKET_CONNECT(sock,address)
        return guarded(sock,address)
    monkeypatch.setattr(socket.socket,'connect',connect)
    server=ThreadingUnixStreamServer(path,stub.server.RequestHandlerClass)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    env.configure('http://localhost')
    monkeypatch.delenv('SP_CONTROL_URL')
    monkeypatch.setenv('SP_CONTROL_SOCKET',path)
    try:
        assert cpc.configured()
        status,body=cpc.call('POST','/v1/customer/apps/opendesign/state',acting=ACTING,body={'enabled':False})
        assert status==201 and body['acting'][0]=='ada@acme.example', body
        assert stub.requests[-1]['body']=={'enabled':False}
        stub.response=(302,{'Location':'https://elsewhere.example'},b'')
        status,body=cpc.call('GET','/v1/customer/overview',acting=ACTING)
        assert status==0 and body['error']['code']=='redirect_refused'
    finally:
        server.shutdown();server.server_close();thread.join()
