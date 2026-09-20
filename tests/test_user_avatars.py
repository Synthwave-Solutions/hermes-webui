"""Profile photos per person and the live group-chat fan-out (20 Sep 2026).

Michael: "group chats werken wel maar ik moet telkens refreshen voor dat ik
iets van een ander zie" and "idealiter kan elke gebruiker ook een profiel
foto voor zichzelf instellen".
"""
import base64
import io
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api.user_avatars as avatars  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MESSAGES_JS = (REPO / "static" / "messages.js").read_text(encoding="utf-8")
UI_JS = (REPO / "static" / "ui.js").read_text(encoding="utf-8")
ROUTES = (REPO / "api" / "routes.py").read_text(encoding="utf-8")


def _png(w=40, h=30, color=(200, 30, 30, 255)):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGBA", (w, h), color).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def state(monkeypatch, tmp_path):
    from api import config

    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    return tmp_path


def test_save_makes_a_square_png_and_url_carries_a_version(state):
    from PIL import Image

    url = avatars.save_avatar("Alice@Example.test", _png(400, 200))
    assert url.startswith("/api/people/avatar?email=alice%40example.test&v=")
    blob = avatars.read_avatar("alice@example.test")
    with Image.open(io.BytesIO(blob)) as img:
        assert img.size == (avatars.MAX_SIDE, avatars.MAX_SIDE)
    assert (state / "user-avatars").is_dir()


def test_no_photo_means_empty_url_and_none(state):
    assert avatars.avatar_url("nobody@example.test") == ""
    assert avatars.read_avatar("nobody@example.test") is None
    assert avatars.avatar_url("not an address") == ""


def test_delete_is_idempotent(state):
    avatars.save_avatar("bob@example.test", _png())
    assert avatars.avatar_url("bob@example.test")
    avatars.delete_avatar("bob@example.test")
    avatars.delete_avatar("bob@example.test")
    assert avatars.avatar_url("bob@example.test") == ""


def test_rejects_non_images_and_oversize(state):
    with pytest.raises(ValueError):
        avatars.save_avatar("a@example.test", "data:text/plain;base64,aGk=")
    with pytest.raises(ValueError):
        avatars.save_avatar("a@example.test", "x" * 2800001)
    with pytest.raises(PermissionError):
        avatars.save_avatar("", _png())


class _Handler:
    command = "GET"

    def __init__(self):
        self.status = None
        self.headers = {}
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, k, v):
        self.headers[k] = v

    def end_headers(self):
        pass


def test_me_avatar_targets_only_the_request_identity(state, monkeypatch):
    from api import ownership

    monkeypatch.setattr(ownership, "request_owner_email", lambda handler: "carol@example.test")
    seen = {}
    monkeypatch.setattr("api.helpers.j", lambda handler, payload, status=200, **kw: seen.update({"payload": payload, "status": status}))
    monkeypatch.setattr("api.helpers.bad", lambda handler, msg, status=400: seen.update({"error": msg, "status": status}))

    avatars.handle_me_avatar(object(), "POST", {"avatar": _png(), "email": "someone-else@example.test"})
    assert seen["payload"]["ok"] and seen["payload"]["email"] == "carol@example.test"
    assert avatars.avatar_url("carol@example.test") and not avatars.avatar_url("someone-else@example.test")

    avatars.handle_me_avatar(object(), "GET", None)
    assert seen["payload"]["avatar_url"].startswith("/api/people/avatar?email=carol")

    avatars.handle_me_avatar(object(), "POST", {"avatar": None})
    assert seen["payload"]["avatar_url"] == ""
    assert avatars.avatar_url("carol@example.test") == ""

    monkeypatch.setattr(ownership, "request_owner_email", lambda handler: None)
    avatars.handle_me_avatar(object(), "POST", {"avatar": _png()})
    assert seen["status"] == 401


def test_people_avatar_serves_png_or_404(state, monkeypatch):
    seen = {}
    monkeypatch.setattr("api.helpers.bad", lambda handler, msg, status=400: seen.update({"status": status}))
    avatars.save_avatar("dave@example.test", _png())
    h = _Handler()
    avatars.handle_people_avatar(h, {"email": ["dave@example.test"]})
    assert h.status == 200 and h.headers["Content-Type"] == "image/png"
    assert h.wfile.getvalue()[:8] == b"\x89PNG\r\n\x1a\n"
    avatars.handle_people_avatar(_Handler(), {"email": ["ghost@example.test"]})
    assert seen["status"] == 404


def test_people_directory_rows_carry_avatar_url(state, monkeypatch):
    from api import routes
    from api.governance import loader

    avatars.save_avatar("erin@example.test", _png())
    policy = SimpleNamespace(users={"erin@example.test": {}, "frank@example.test": {}}, bootstrap_admins=[])
    monkeypatch.setattr(loader, "get_policy", lambda: policy)
    monkeypatch.setattr("api.ownership.request_owner_email", lambda handler: "erin@example.test")
    out = {}
    monkeypatch.setattr(routes, "j", lambda handler, payload, **kw: out.update(payload))
    routes._handle_people_directory(object())
    rows = {p["email"]: p for p in out["people"]}
    assert rows["erin@example.test"]["avatar_url"].startswith("/api/people/avatar?email=erin")
    assert rows["frank@example.test"]["avatar_url"] == ""


def test_catalog_gates_avatar_routes_on_sessions_read():
    from api.governance.catalog import ROUTE_CATALOG as ROUTE_RULES

    rules = {r.pattern: r for r in ROUTE_RULES}
    assert rules["/api/people/avatar"].permission_for("GET") == "sessions:read"
    assert rules["/api/me/avatar"].permission_for("POST") == "sessions:read"


class _Channel:
    def __init__(self):
        self.events = []

    def emit(self, event, data):
        self.events.append((event, data))
        return 1


def test_group_turn_fans_out_to_the_other_tabs(monkeypatch):
    from api import routes, background_process

    ch = _Channel()
    monkeypatch.setattr(background_process, "get_session_channel", lambda sid: ch if sid == "s1" else None)
    s = SimpleNamespace(session_id="s1", participants=["bob@example.test"], bot_participants=[], pending_started_at=12.5)
    ok = routes._fan_out_peer_turn(s, {"stream_id": "st-9"}, "Alice@Example.test", "hello all",
                                   [{"name": "a/b/report.pdf"}, "notes.txt"])
    assert ok
    event, data = ch.events[0]
    assert event == "peer_turn_started"
    assert data == {"session_id": "s1", "stream_id": "st-9", "sender_email": "alice@example.test",
                    "message": "hello all", "attachments": ["report.pdf", "notes.txt"], "pending_started_at": 12.5}


def test_private_conversations_and_closed_tabs_emit_nothing(monkeypatch):
    from api import routes, background_process

    calls = []
    monkeypatch.setattr(background_process, "get_session_channel", lambda sid: calls.append(sid))
    private = SimpleNamespace(session_id="p1", participants=[], bot_participants=[], pending_started_at=None)
    assert routes._fan_out_peer_turn(private, {"stream_id": "st"}, "a@example.test", "hi", []) is False
    assert calls == []
    group = SimpleNamespace(session_id="g1", participants=["b@example.test"], bot_participants=[], pending_started_at=None)
    assert routes._fan_out_peer_turn(group, {"stream_id": "st"}, "a@example.test", "hi", []) is False  # no channel
    assert routes._fan_out_peer_turn(group, {}, "a@example.test", "hi", []) is False  # no stream


def test_chat_start_calls_the_fan_out_and_frontend_listens():
    assert "_fan_out_peer_turn(s, response, start_run_kwargs.get(\"sender_email\"), msg, attachments)" in ROUTES
    assert "es.addEventListener('peer_turn_started'" in MESSAGES_JS
    # The writer's own tab must not double-render its send.
    assert "if (sender && me && sender === me) return;" in MESSAGES_JS
    # Author lines carry a photo or initials.
    assert "_personAvatarHtml(author,label,22)" in UI_JS
