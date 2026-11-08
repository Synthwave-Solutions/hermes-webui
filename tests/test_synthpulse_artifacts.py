"""SynthPulse Artifacts card backend (api/artifacts.py): ownership, frame headers, share."""
import io
import json
import urllib.parse

import pytest

from api import artifacts

AID = "c9776c52-3e35-41cb-b425-e12d592cd7c8"


class FakeHandler:
    def __init__(self, path, command="GET"):
        self.path, self.command = path, command
        self.status, self.headers_out, self.wfile = None, {}, io.BytesIO()
        self.headers = {}

    def send_response(self, status):
        self.status = status

    def send_header(self, k, v):
        self.headers_out[k] = v

    def end_headers(self):
        pass


@pytest.fixture
def service(monkeypatch, tmp_path):
    admins = tmp_path / "admins"
    admins.write_text("# admins\nmichael@synthwave.solutions\n")
    monkeypatch.setattr(artifacts, "ADMINS_FILE", admins)
    calls = []
    detail = {"artifact": {"id": AID, "slug": "plan", "title": "Plan", "kind": "html",
                           "source_profile": "hrishikesh_at_synthwave.solutions"},
              "shares": [{"id": "s1", "status": "active"}]}

    def fake_request(method, path, *, params=None, body=None):
        calls.append((method, path, params, body))
        if path.endswith("/render"):
            return 200, {"x-artifact-frame-policy": "default-src 'none'"}, b"<html>ok</html>"
        if path.endswith("/download"):
            return 200, {}, b"<html>src</html>"
        if path.endswith("/shares"):
            return 200, {}, json.dumps({"url": "https://share/x", "share": {"id": "s2", "expires_at": 1}}).encode()
        return 200, {}, json.dumps(detail).encode()

    monkeypatch.setattr(artifacts, "_request", fake_request)
    sent = {}

    def fake_json(handler, payload, status=200):
        sent["status"], sent["payload"] = status, payload
        return True

    monkeypatch.setattr(artifacts, "_send_json", fake_json)
    return calls, sent


def _as(monkeypatch, email):
    monkeypatch.setattr(artifacts, "_identity_email", lambda handler: email)


def _get(path):
    h = FakeHandler(path)
    artifacts.handle_get(h, urllib.parse.urlparse(path))
    return h


def test_owner_key_matches_plugin_rule():
    assert artifacts.owner_key("Hrishikesh@Synthwave.Solutions") == "hrishikesh_at_synthwave.solutions"
    assert artifacts.owner_key("12345") == "user_12345"


def test_owner_sees_metadata(service, monkeypatch):
    _calls, sent = service
    _as(monkeypatch, "hrishikesh@synthwave.solutions")
    _get(f"/api/artifacts/{AID}")
    assert sent["status"] == 200 and sent["payload"]["artifact"]["title"] == "Plan"
    assert sent["payload"]["artifact"]["active_shares"] == 1
    assert "source_profile" not in sent["payload"]["artifact"]


def test_other_person_gets_not_found(service, monkeypatch):
    calls, sent = service
    _as(monkeypatch, "marcel@synthwave.solutions")
    h = _get(f"/api/artifacts/{AID}/frame")
    assert sent["status"] == 404 and h.status is None
    assert not any(c[1].endswith("/render") for c in calls)


def test_signed_out_is_refused(service, monkeypatch):
    _calls, sent = service
    _as(monkeypatch, None)
    _get(f"/api/artifacts/{AID}")
    assert sent["status"] == 401


def test_admin_sees_everything(service, monkeypatch):
    _calls, sent = service
    _as(monkeypatch, "michael@synthwave.solutions")
    _get(f"/api/artifacts/{AID}")
    assert sent["status"] == 200


def test_frame_is_sandboxed_without_same_origin(service, monkeypatch):
    _as(monkeypatch, "hrishikesh@synthwave.solutions")
    h = _get(f"/api/artifacts/{AID}/frame?theme=dark")
    csp = h.headers_out["Content-Security-Policy"]
    assert h.status == 200 and "sandbox allow-scripts" in csp and "allow-same-origin" not in csp
    assert "frame-ancestors 'self'" in csp
    assert h.headers_out["X-Content-Type-Options"] == "nosniff"
    assert h.wfile.getvalue() == b"<html>ok</html>"


def test_download_is_an_attachment(service, monkeypatch):
    _as(monkeypatch, "hrishikesh@synthwave.solutions")
    h = _get(f"/api/artifacts/{AID}/download")
    assert h.headers_out["Content-Disposition"] == 'attachment; filename="plan.html"'
    assert h.headers_out["Content-Type"] == "application/octet-stream"


def test_share_only_for_owner_and_bounded(service, monkeypatch):
    calls, sent = service
    path = f"/api/artifacts/{AID}/share"
    _as(monkeypatch, "marcel@synthwave.solutions")
    artifacts.handle_post(FakeHandler(path, "POST"), urllib.parse.urlparse(path), {"expires_in_hours": 24})
    assert sent["status"] == 404
    _as(monkeypatch, "hrishikesh@synthwave.solutions")
    artifacts.handle_post(FakeHandler(path, "POST"), urllib.parse.urlparse(path), {"expires_in_hours": 99999})
    assert sent["status"] == 400
    artifacts.handle_post(FakeHandler(path, "POST"), urllib.parse.urlparse(path), {"expires_in_hours": 24})
    assert sent["status"] == 200 and sent["payload"]["url"] == "https://share/x"
    assert ("POST", f"/artifacts/{AID}/shares", None, {"expires_in_seconds": 86400}) in calls


def test_bad_ids_never_reach_the_service(service, monkeypatch):
    calls, sent = service
    _as(monkeypatch, "michael@synthwave.solutions")
    _get("/api/artifacts/../../internal/v1/artifacts")
    _get("/api/artifacts/not-a-uuid/frame")
    assert calls == [] and sent["status"] == 404


def test_prompt_block_only_when_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(artifacts, "TOKEN_FILE", tmp_path / "missing")
    assert artifacts.prompt_block() == ""
    token = tmp_path / "token"
    token.write_text("x" * 40)
    monkeypatch.setattr(artifacts, "TOKEN_FILE", token)
    assert "artifact_publish" in artifacts.prompt_block()
