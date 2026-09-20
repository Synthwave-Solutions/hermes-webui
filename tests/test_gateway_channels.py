"""Messaging channels in Connections (20 Sep 2026): platform catalog, env
writes, pairing approval with person mapping, identity map, visibility."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api.gateway_channels as ch  # noqa: E402


@pytest.fixture
def env(monkeypatch, tmp_path):
    from api import config
    monkeypatch.setattr(config, "STATE_DIR", tmp_path / "state")
    env_path = tmp_path / ".env"
    env_path.write_text("EXISTING=1\nTELEGRAM_BOT_TOKEN=123:abc\nTELEGRAM_ALLOWED_USERS=1,2\n")
    monkeypatch.setattr(ch, "_env_path", lambda: env_path)
    monkeypatch.setattr(ch, "_known_people", lambda: {"andre@example.test", "michael@example.test"})
    return env_path


class _Store:
    def __init__(self):
        self.pending = [{"platform": "telegram", "request_id": "req1", "user_id": "555", "user_name": "Andre", "age_minutes": 3}]
        self.approved = [{"platform": "telegram", "user_id": "1", "user_name": "Michael"}]
        self.revoked = []

    def list_pending(self, platform=None):
        return list(self.pending)

    def list_approved(self, platform=None):
        return list(self.approved)

    def approve_request(self, platform, request_id):
        if request_id != "req1":
            return None
        self.pending = []
        self.approved.append({"platform": platform, "user_id": "555", "user_name": "Andre"})
        return {"user_id": "555", "user_name": "Andre"}

    def revoke(self, platform, user_id):
        self.revoked.append((platform, user_id))
        return True


def test_status_reports_configured_without_leaking_values(env):
    out = ch.status_payload()
    tg = next(p for p in out["platforms"] if p["key"] == "telegram")
    assert tg["configured"] is True and tg["allowed_count"] == 2
    token = next(f for f in tg["fields"] if f["key"] == "TELEGRAM_BOT_TOKEN")
    assert token["set"] is True and "123:abc" not in json.dumps(out)
    slack = next(p for p in out["platforms"] if p["key"] == "slack")
    assert slack["configured"] is False


def test_configure_writes_only_catalog_keys_and_keeps_blanks(env):
    ch.configure("slack", {"SLACK_BOT_TOKEN": "xoxb-1", "SLACK_APP_TOKEN": "xapp-1", "SLACK_ALLOW_ALL_USERS": "on", "SLACK_HOME_CHANNEL": ""})
    text = env.read_text()
    assert "SLACK_BOT_TOKEN=xoxb-1" in text and "SLACK_APP_TOKEN=xapp-1" in text and "SLACK_ALLOW_ALL_USERS=true" in text
    assert "EXISTING=1" in text and "SLACK_HOME_CHANNEL" not in text
    with pytest.raises(ValueError):
        ch.configure("slack", {"OPENAI_API_KEY": "nope"})
    with pytest.raises(ValueError):
        ch.configure("nosuch", {"X": "1"})
    with pytest.raises(ValueError):
        ch.configure("slack", {})


def test_disable_removes_secrets(env):
    ch.disable("telegram")
    assert "TELEGRAM_BOT_TOKEN" not in env.read_text()
    assert next(p for p in ch.status_payload()["platforms"] if p["key"] == "telegram")["configured"] is False


def test_identity_map_round_trip_and_validation(env):
    out = ch.set_identity("telegram", " 555 ", "Andre@Example.test", "Andre", actor="michael@example.test")
    assert out["user_id"] == "555" and out["email"] == "andre@example.test"
    assert ch.mapped_email("telegram", "555") == "andre@example.test"
    assert ch.mapped_email("telegram", "556") == ""
    assert ch.set_identity("whatsapp_cloud", "+31 6 1234 5678", "andre@example.test")["user_id"] == "31612345678"
    with pytest.raises(ValueError):
        ch.set_identity("telegram", "555", "stranger@example.test")
    with pytest.raises(ValueError):
        ch.set_identity("telegram", "", "andre@example.test")
    people = ch.status_payload()["people"]
    assert [(r["platform"], r["user_id"], r["email"]) for r in people] == [
        ("telegram", "555", "andre@example.test"), ("whatsapp_cloud", "31612345678", "andre@example.test")]
    assert ch.remove_identity("telegram", "555")["removed"] is True
    assert ch.mapped_email("telegram", "555") == ""
    stored = json.loads((Path(env).parent / "state" / "gateway-identities.json").read_text())
    assert "telegram" not in stored and "whatsapp_cloud" in stored


def test_approve_pairing_maps_the_person_in_one_step(env, monkeypatch):
    store = _Store()
    monkeypatch.setattr(ch, "_pairing_store", lambda: store)
    before = ch.status_payload()
    assert next(p for p in before["platforms"] if p["key"] == "telegram")["pending_count"] == 1
    out = ch.approve_pairing("telegram", "req1", "andre@example.test", actor="michael@example.test")
    assert out["user_id"] == "555" and out["identity"]["email"] == "andre@example.test"
    assert ch.mapped_email("telegram", "555") == "andre@example.test"
    with pytest.raises(LookupError):
        ch.approve_pairing("telegram", "stale", "andre@example.test")
    ch.revoke_pairing("telegram", "555")
    assert store.revoked == [("telegram", "555")] and ch.mapped_email("telegram", "555") == ""


def test_pairing_store_missing_degrades_gracefully(env, monkeypatch):
    def boom():
        raise ImportError("no engine")
    monkeypatch.setattr(ch, "_pairing_store", boom)
    out = ch.status_payload()
    assert out["pairing"]["available"] is False and out["pairing"]["pending"] == []


def test_mapped_person_sees_their_messaging_session(env, monkeypatch):
    from api import routes
    ch.set_identity("telegram", "555", "andre@example.test")
    monkeypatch.setattr(routes, "_load_gateway_session_identity_map",
                        lambda: {"tg-1": {"platform": "telegram", "user_id": "555"}, "tg-2": {"platform": "telegram", "user_id": "777"}})
    monkeypatch.setattr("api.ownership.request_owner_email", lambda handler: "andre@example.test")
    session = SimpleNamespace(session_id="tg-1", owner_email=None)
    assert routes._messaging_session_visible_to_mapped_person(session, object()) is True
    assert routes._messaging_session_visible_to_mapped_person(SimpleNamespace(session_id="tg-2", owner_email=None), object()) is False
    assert routes._messaging_session_visible_to_mapped_person(SimpleNamespace(session_id="tg-1", owner_email="x@example.test"), object()) is False


def test_routes_and_ui_are_wired():
    root = Path(__file__).resolve().parent.parent
    routes = (root / "api" / "routes.py").read_text()
    assert 'if parsed.path == "/api/gateway/channels":' in routes
    assert 'parsed.path.startswith("/api/gateway/identities/")' in routes
    js = (root / "static" / "integrations.js").read_text()
    for name in ("chLoadChannels", "chOpenConfigure", "chApprove", "chAddPerson", "/api/gateway/pairing/approve"):
        assert name in js
    html = (root / "static" / "index.html").read_text()
    assert 'id="intgChannels"' in html and 'id="intgChannelPeople"' in html
