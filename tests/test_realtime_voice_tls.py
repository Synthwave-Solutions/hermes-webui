"""Real native-TLS listener tests: fixed loopback and exact certificate trust."""
import datetime
import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler
from types import SimpleNamespace

import pytest
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from api.realtime_voice_runtime import LoopbackBridge


def certificate(tmp_path, name):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "voice.example.test")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("voice.example.test")]), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256()))
    cert_path, key_path = tmp_path / (name + ".pem"), tmp_path / (name + ".key")
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                         serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return cert_path, key_path


@pytest.mark.parametrize("wrong_pin", [False, True])
def test_real_native_tls_loopback_requires_configured_certificate_pin(tmp_path, monkeypatch, wrong_pin):
    from server import QuietHTTPServer
    from api import config
    cert_path, key_path = certificate(tmp_path, "actual")
    configured_cert = cert_path
    if wrong_pin:
        configured_cert, _ = certificate(tmp_path, "different")
        # Trust includes the real certificate, so CA verification alone would
        # succeed. The configured first-leaf pin must still reject this listener.
        configured_cert.write_bytes(configured_cert.read_bytes() + cert_path.read_bytes())
    monkeypatch.setattr(config, "TLS_CERT", str(configured_cert))
    received = []
    class Gate(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append((self.path, self.headers.get("Cookie"), self.headers.get("Origin"), data))
            payload = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers(); self.wfile.write(payload)
    server = QuietHTTPServer(("127.0.0.1", 0), Gate)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(cert_path), str(key_path))
    server.ssl_context = context
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        handler = SimpleNamespace(server=server, headers={"Cookie": "fixture-session",
            "Origin": "https://voice.example.test", "Host": "voice.example.test",
            "X-Hermes-CSRF-Token": "fixture-csrf"})
        bridge = LoopbackBridge(handler, "alice@example.test", "parent")
        assert bridge.base.startswith("https://127.0.0.1:")
        assert bridge.tls_context.verify_mode == ssl.CERT_REQUIRED
        if wrong_pin:
            with pytest.raises(requests.exceptions.SSLError, match="Fingerprints did not match"):
                bridge.request("POST", "/api/session/new", {"message": "private work"})
            assert received == []
        else:
            assert bridge.request("POST", "/api/session/new", {"message": "private work"}) == {"ok": True}
            assert received == [("/api/session/new", "fixture-session", "https://voice.example.test", {"message": "private work"})]
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
