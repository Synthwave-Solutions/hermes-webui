"""Messaging channels in Connections (20 Sep 2026): platform catalog, env
writes, pairing approval with person mapping, identity map, visibility."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api.gateway_channels as ch  # noqa: E402

NET_ENV_KEYS = ("SP_NET_PROVIDER", "SP_PUBLIC_HOOKS_BASE", "SP_TS_HOOKS_BASE")


@pytest.fixture(autouse=True)
def _no_ambient_network_env(monkeypatch):
    """The publish and status paths read these; never inherit them from the runner."""
    for key in NET_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


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


# ── profile per person, env seed, public webhooks ───────────────────────────

def test_identity_carries_the_persons_profile(env, monkeypatch):
    class _Grants:
        profiles = frozenset({"andre"})
    class _User:
        grants = _Grants()
    class _Policy:
        users = {"andre@example.test": _User()}
        bootstrap_admins = ()
    monkeypatch.setattr("api.governance.loader.get_policy", lambda: _Policy())
    out = ch.set_identity("telegram", "555", "andre@example.test")
    assert out["profile"] == "andre"
    out = ch.set_identity("telegram", "556", "michael@example.test")  # no single profile: gateway profile
    assert out["profile"] == ""
    out = ch.set_identity("slack", "U1", "andre@example.test", profile="Custom-Profile")
    assert out["profile"] == "custom-profile"
    with pytest.raises(ValueError):
        ch.set_identity("slack", "U2", "andre@example.test", profile="bad/profile")
    rows = {(r["platform"], r["user_id"]): r for r in ch.status_payload()["people"]}
    assert rows[("telegram", "555")]["profile"] == "andre"


def test_seed_from_env_materialises_once(env, monkeypatch):
    seed = {"telegram": {"555": {"email": "andre@example.test", "name": "Andre"}}, "bogus": {"1": "x@example.test"},
            "slack": {"U9": "michael@example.test"}}
    monkeypatch.setenv("SP_GATEWAY_IDENTITIES_JSON", json.dumps(seed))
    assert ch.mapped_email("telegram", "555") == "andre@example.test"
    assert ch.mapped_email("slack", "U9") == "michael@example.test"
    stored = json.loads((Path(env).parent / "state" / "gateway-identities.json").read_text())
    assert "bogus" not in stored and stored["telegram"]["555"]["added_by"] == "client.yaml"
    monkeypatch.delenv("SP_GATEWAY_IDENTITIES_JSON")
    assert ch.mapped_email("telegram", "555") == "andre@example.test"  # file wins from now on


def test_public_hooks_status_reads_the_funnel_config(env, monkeypatch):
    class _Proc:
        def __init__(self, out):
            self.stdout, self.stderr, self.returncode = out, "", 0
    serve = {"AllowFunnel": {"node.tail.ts.net:8443": True},
             "Web": {"node.tail.ts.net:8443": {"Handlers": {"/hooks/whatsapp": {"Proxy": "http://127.0.0.1:8090/whatsapp/webhook"}}}}}
    def fake(*args, timeout=25):
        if args[:2] == ("serve", "status"):
            return _Proc(json.dumps(serve))
        if args[:2] == ("status", "--json"):
            return _Proc(json.dumps({"Self": {"DNSName": "node.tail.ts.net."}}))
        raise AssertionError(args)
    monkeypatch.setattr(ch, "_tailscale", fake)
    hooks = ch.public_hooks_status({})
    assert hooks["whatsapp_cloud"] == {"state": "published", "url": "https://node.tail.ts.net:8443/hooks/whatsapp",
                                       "mount": "/hooks/whatsapp", "label": "Meta webhook callback URL", "managed_by": "webui"}
    assert hooks["teams"]["state"] == "unpublished"
    tg = next(p for p in ch.status_payload()["platforms"] if p["key"] == "whatsapp_cloud")
    assert tg["public"]["state"] == "published"


def test_public_hooks_without_cli_use_the_bootstrap_base(env, monkeypatch):
    def missing(*args, timeout=25):
        raise FileNotFoundError("no tailscale")
    monkeypatch.setattr(ch, "_tailscale", missing)
    assert ch.public_hooks_status({})["teams"]["state"] == "unavailable"
    monkeypatch.setenv("SP_TS_HOOKS_BASE", "https://synthpulse-acme.tail.ts.net:8443/hooks")
    hooks = ch.public_hooks_status({})
    assert hooks["teams"] == {"state": "published", "url": "https://synthpulse-acme.tail.ts.net:8443/hooks/teams",
                              "mount": "/hooks/teams", "label": "Azure Bot messaging endpoint", "managed_by": "bootstrap"}
    with pytest.raises(RuntimeError):
        ch.publish_hook("teams")


def test_publish_hook_runs_funnel_and_pins_loopback(env, monkeypatch):
    calls = []
    class _Proc:
        stdout, stderr, returncode = "", "", 0
    def fake(*args, timeout=25):
        calls.append(args)
        if args[:2] == ("status", "--json"):
            p = _Proc(); p.stdout = json.dumps({"Self": {"DNSName": "node.tail.ts.net."}}); return p
        return _Proc()
    monkeypatch.setattr(ch, "_tailscale", fake)
    out = ch.publish_hook("whatsapp_cloud")
    assert out["url"] == "https://node.tail.ts.net:8443/hooks/whatsapp"
    assert ("funnel", "--bg", "--https=8443", "--set-path", "/hooks/whatsapp", "http://127.0.0.1:8090/whatsapp/webhook") in calls
    assert "WHATSAPP_CLOUD_WEBHOOK_HOST=127.0.0.1" in env.read_text()
    with pytest.raises(ValueError):
        ch.publish_hook("telegram")


# ── provider-neutral publish and status (PLAN 3.10, N3) ─────────────────────
# The tailscale CLI runs only when SP_NET_PROVIDER is unset or "tailscale" and
# SP_PUBLIC_HOOKS_BASE is unset (HQ today). Otherwise the URL comes from
# SP_PUBLIC_HOOKS_BASE (legacy alias SP_TS_HOOKS_BASE) and nothing is spawned.

PUBLIC_BASE = "https://hooks.acme.example/hooks"
NETWORK_PRODUCTS = ("Tailscale", "tailnet", "Funnel", "NetBird", "WireGuard", "Headscale")
DASHES = ("\u2013", "\u2014")


@pytest.fixture
def no_subprocess(monkeypatch):
    """Fail the test on any CLI lookup or process spawn, even a swallowed one."""
    import shutil
    import subprocess
    attempts = []

    def refuse(*args, **kwargs):
        attempts.append(args)
        raise AssertionError(f"no subprocess expected, got {args!r}")
    monkeypatch.setattr(ch, "_tailscale", refuse)
    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(shutil, "which", refuse)
    yield attempts
    assert attempts == [], "a CLI was looked up or spawned"


def _neutral(text: str) -> bool:
    return not any(p.lower() in text.lower() for p in NETWORK_PRODUCTS) and not any(d in text for d in DASHES)


@pytest.mark.parametrize("provider", ["netbird", "none", " NetBird "])
def test_non_tailscale_status_uses_the_public_base_without_subprocess(env, monkeypatch, no_subprocess, provider):
    monkeypatch.setenv("SP_NET_PROVIDER", provider)
    monkeypatch.setenv("SP_PUBLIC_HOOKS_BASE", PUBLIC_BASE + "/")
    hooks = ch.public_hooks_status({})
    assert hooks["whatsapp_cloud"] == {"state": "published", "url": "https://hooks.acme.example/hooks/whatsapp",
                                       "mount": "/hooks/whatsapp", "label": "Meta webhook callback URL",
                                       "managed_by": "platform"}
    assert hooks["teams"]["url"] == "https://hooks.acme.example/hooks/teams"
    assert hooks["teams"]["state"] == "published"
    wa = next(p for p in ch.status_payload()["platforms"] if p["key"] == "whatsapp_cloud")
    assert wa["public"]["url"] == "https://hooks.acme.example/hooks/whatsapp"


@pytest.mark.parametrize("provider", ["netbird", "none"])
def test_non_tailscale_without_a_base_is_unavailable_without_subprocess(env, monkeypatch, no_subprocess, provider):
    monkeypatch.setenv("SP_NET_PROVIDER", provider)
    hooks = ch.public_hooks_status({})
    for key in ch.PUBLIC_HOOKS:
        assert hooks[key]["state"] == "unavailable" and hooks[key]["url"] == ""
        assert hooks[key]["managed_by"] == "platform"


@pytest.mark.parametrize("provider", [None, "tailscale"])
def test_public_base_skips_the_cli_on_tailscale_too(env, monkeypatch, no_subprocess, provider):
    if provider:
        monkeypatch.setenv("SP_NET_PROVIDER", provider)
    monkeypatch.setenv("SP_PUBLIC_HOOKS_BASE", PUBLIC_BASE)
    hooks = ch.public_hooks_status({})
    assert hooks["teams"]["state"] == "published"
    assert hooks["teams"]["url"] == "https://hooks.acme.example/hooks/teams"
    out = ch.publish_hook("teams")
    assert out["url"] == "https://hooks.acme.example/hooks/teams" and out["managed_by"] == "platform"


def test_legacy_hooks_base_is_an_alias_and_the_public_base_wins(env, monkeypatch, no_subprocess):
    monkeypatch.setenv("SP_NET_PROVIDER", "netbird")
    monkeypatch.setenv("SP_TS_HOOKS_BASE", "https://legacy.acme.example/hooks")
    assert ch.public_hooks_status({})["teams"]["url"] == "https://legacy.acme.example/hooks/teams"
    # The profile .env counts the same way as the process env.
    monkeypatch.delenv("SP_TS_HOOKS_BASE")
    assert ch.public_hooks_status({"SP_TS_HOOKS_BASE": "https://legacy.acme.example/hooks"})["teams"]["state"] == "published"
    monkeypatch.setenv("SP_PUBLIC_HOOKS_BASE", PUBLIC_BASE)
    monkeypatch.setenv("SP_TS_HOOKS_BASE", "https://legacy.acme.example/hooks")
    assert ch.public_hooks_status({})["teams"]["url"] == "https://hooks.acme.example/hooks/teams"


def test_an_unknown_provider_fails_closed(env, monkeypatch, no_subprocess):
    monkeypatch.setenv("SP_NET_PROVIDER", "headscale")
    assert ch.public_hooks_status({})["teams"]["state"] == "unavailable"
    with pytest.raises(RuntimeError):
        ch.publish_hook("teams")


@pytest.mark.parametrize("base", ["javascript:alert(1)", "ftp://hooks.acme.example/hooks",
                                  "https://user:pw@hooks.acme.example/hooks", "https://", "hooks.acme.example"])
def test_an_unusable_public_base_fails_closed(env, monkeypatch, no_subprocess, base):
    monkeypatch.setenv("SP_PUBLIC_HOOKS_BASE", base)
    hooks = ch.public_hooks_status({})
    assert hooks["whatsapp_cloud"]["state"] == "unavailable" and hooks["whatsapp_cloud"]["url"] == ""
    with pytest.raises(RuntimeError):
        ch.publish_hook("whatsapp_cloud")


def test_publish_off_tailscale_reports_the_url_and_writes_nothing(env, monkeypatch, no_subprocess):
    monkeypatch.setenv("SP_NET_PROVIDER", "netbird")
    monkeypatch.setenv("SP_PUBLIC_HOOKS_BASE", PUBLIC_BASE)
    before = env.read_text()
    out = ch.publish_hook("whatsapp_cloud")
    assert out == {"ok": True, "platform": "whatsapp_cloud", "url": "https://hooks.acme.example/hooks/whatsapp",
                   "mount": "/hooks/whatsapp", "managed_by": "platform"}
    # The platform's reverse proxy reaches the listener; never pin it to loopback here.
    assert env.read_text() == before
    assert ch.unpublish_hook("whatsapp_cloud") == {"ok": True, "platform": "whatsapp_cloud", "managed_by": "platform"}
    with pytest.raises(ValueError):
        ch.publish_hook("telegram")


def test_publish_off_tailscale_without_a_base_refuses_in_neutral_words(env, monkeypatch, no_subprocess):
    monkeypatch.setenv("SP_NET_PROVIDER", "none")
    with pytest.raises(RuntimeError) as exc:
        ch.publish_hook("teams")
    assert _neutral(str(exc.value))


def test_configure_route_off_tailscale_spawns_nothing(env, monkeypatch, no_subprocess):
    import io
    monkeypatch.setenv("SP_NET_PROVIDER", "netbird")
    monkeypatch.setenv("SP_PUBLIC_HOOKS_BASE", PUBLIC_BASE)

    class _Handler:
        def __init__(self):
            self.status, self.headers, self.wfile = None, {}, io.BytesIO()

        def send_response(self, status):
            self.status = status

        def send_header(self, *a):
            pass

        def end_headers(self):
            pass

    handler = _Handler()
    ch.handle_post(handler, "/api/gateway/channels/configure",
                   {"platform": "teams", "values": {"TEAMS_CLIENT_ID": "id", "TEAMS_CLIENT_SECRET": "s", "TEAMS_TENANT_ID": "t"}})
    assert handler.status == 200
    body = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert body["public"]["url"] == "https://hooks.acme.example/hooks/teams"
    handler = _Handler()
    ch.handle_post(handler, "/api/gateway/channels/disable", {"platform": "teams"})
    assert handler.status == 200


@pytest.mark.parametrize("provider", [None, "tailscale", " Tailscale "])
def test_tailscale_path_runs_exactly_todays_commands(env, monkeypatch, provider):
    if provider:
        monkeypatch.setenv("SP_NET_PROVIDER", provider)
    calls = []

    class _Proc:
        def __init__(self, out=""):
            self.stdout, self.stderr, self.returncode = out, "", 0
    serve = {"AllowFunnel": {"node.tail.ts.net:8443": True},
             "Web": {"node.tail.ts.net:8443": {"Handlers": {"/hooks/teams": {"Proxy": "http://127.0.0.1:3978/api/messages"}}}}}

    def fake(*args, timeout=25):
        calls.append(args)
        if args[:2] == ("serve", "status"):
            return _Proc(json.dumps(serve))
        if args[:2] == ("status", "--json"):
            return _Proc(json.dumps({"Self": {"DNSName": "node.tail.ts.net."}}))
        return _Proc()
    monkeypatch.setattr(ch, "_tailscale", fake)
    hooks = ch.public_hooks_status({})
    assert calls == [("serve", "status", "--json"), ("status", "--json")]
    assert hooks["teams"] == {"state": "published", "url": "https://node.tail.ts.net:8443/hooks/teams",
                              "mount": "/hooks/teams", "label": "Azure Bot messaging endpoint", "managed_by": "webui"}
    assert hooks["whatsapp_cloud"]["state"] == "unpublished"
    calls.clear()
    out = ch.publish_hook("whatsapp_cloud")
    assert calls == [("status", "--json"),
                     ("funnel", "--bg", "--https=8443", "--set-path", "/hooks/whatsapp", "http://127.0.0.1:8090/whatsapp/webhook")]
    assert out["url"] == "https://node.tail.ts.net:8443/hooks/whatsapp"
    assert "WHATSAPP_CLOUD_WEBHOOK_HOST=127.0.0.1" in env.read_text()
    calls.clear()
    ch.unpublish_hook("whatsapp_cloud")
    assert calls == [("funnel", "--https=8443", "--set-path", "/hooks/whatsapp", "off")]


def test_tailscale_path_errors_are_worded_neutrally(env, monkeypatch):
    def missing(*args, timeout=25):
        raise FileNotFoundError("no cli")
    monkeypatch.setattr(ch, "_tailscale", missing)
    with pytest.raises(RuntimeError) as exc:
        ch.publish_hook("teams")
    assert _neutral(str(exc.value))

    class _Proc:
        def __init__(self, out="", rc=0):
            self.stdout, self.stderr, self.returncode = out, "", rc

    def failing(*args, timeout=25):
        if args[:2] == ("status", "--json"):
            return _Proc(json.dumps({"Self": {"DNSName": "node.tail.ts.net."}}))
        return _Proc("", 1)
    monkeypatch.setattr(ch, "_tailscale", failing)
    with pytest.raises(RuntimeError) as exc:
        ch.publish_hook("teams")
    assert _neutral(str(exc.value))


def test_channel_dialog_uses_the_neutral_hook_copy():
    root = Path(__file__).resolve().parent.parent
    js = (root / "static" / "integrations.js").read_text(encoding="utf-8")
    en = (root / "static" / "i18n" / "en.js").read_text(encoding="utf-8")
    neutral = ("On save the webhook is published on your platform's public address and the URL appears "
               "on the card. Enter that URL at the provider.")
    assert "channels_hook_on_save_neutral: '" + neutral.replace("'", "\\'") + "'" in en
    assert "_intgT('channels_hook_on_save_neutral', \"" + neutral + "\")" in js
    assert "_intgT('channels_hook_on_save'," not in js
    assert "through Tailscale Funnel" not in js
    assert _neutral(neutral)


# ── one bot per person (self-service) ───────────────────────────────────────

@pytest.fixture
def me(monkeypatch, tmp_path, env):
    monkeypatch.setattr("api.ownership.request_owner_email", lambda handler: "andre@example.test")
    monkeypatch.setattr(ch, "_is_admin", lambda handler: False)
    monkeypatch.setattr(ch, "_profile_for_email", lambda email, explicit=None: (explicit or "").lower() if explicit else ("andre" if email == "andre@example.test" else ""))
    pdir = tmp_path / "profiles" / "andre"
    pdir.mkdir(parents=True)
    monkeypatch.setattr(ch, "_profile_env_path", lambda profile: tmp_path / "profiles" / profile / ".env")
    monkeypatch.setattr(ch, "_people_gateway_state", lambda: {"unit": "hermes-mux-gateway.service", "active": True, "available": True})
    return pdir


def test_my_bot_token_lands_in_my_profile_env(me):
    out = ch.set_my_bot(object(), "telegram", {"TELEGRAM_BOT_TOKEN": "999:xyz"})
    assert out["profile"] == "andre" and out["token_set"] is True
    assert "TELEGRAM_BOT_TOKEN=999:xyz" in (me / ".env").read_text()
    with pytest.raises(ValueError):
        ch.set_my_bot(object(), "teams", {"TEAMS_CLIENT_ID": "x"})  # shared platform
    with pytest.raises(ValueError):
        ch.set_my_bot(object(), "telegram", {"OPENAI_API_KEY": "x"})
    payload = ch.my_channels_payload(object())
    assert payload["profile"] == "andre" and payload["own_bot"]["telegram"]["token_set"] is True and payload["shared_bot"] is False
    ch.remove_my_bot(object(), "telegram")
    assert "TELEGRAM_BOT_TOKEN" not in (me / ".env").read_text()


def test_linking_my_id_maps_me_and_allowlists_my_bot(me):
    out = ch.link_me(object(), "telegram", "4242")
    assert out["email"] == "andre@example.test" and out["profile"] == "andre"
    assert "TELEGRAM_ALLOWED_USERS=4242" in (me / ".env").read_text()
    assert ch.mapped_email("telegram", "4242") == "andre@example.test"
    links = ch.my_channels_payload(object())["links"]
    assert [(l["platform"], l["user_id"]) for l in links] == [("telegram", "4242")]
    ch.unlink_me(object(), "telegram", "4242")
    assert ch.mapped_email("telegram", "4242") == "" and "TELEGRAM_ALLOWED_USERS" not in (me / ".env").read_text()
    with pytest.raises(LookupError):
        ch.unlink_me(object(), "telegram", "4242")


def test_cannot_steal_someone_elses_link(me):
    ch.set_identity("telegram", "777", "michael@example.test")
    with pytest.raises(ValueError):
        ch.link_me(object(), "telegram", "777")


def test_shared_bot_account_cannot_create_a_personal_bot(me, monkeypatch):
    monkeypatch.setattr("api.ownership.request_owner_email", lambda handler: "michael@example.test")
    assert ch.my_channels_payload(object())["shared_bot"] is True
    with pytest.raises(ValueError):
        ch.set_my_bot(object(), "telegram", {"TELEGRAM_BOT_TOKEN": "1:a"})


def test_apply_restarts_the_people_gateway_with_a_rate_limit(me, monkeypatch):
    calls = []
    class _Proc:
        returncode, stdout, stderr = 0, "", ""
    monkeypatch.setattr("subprocess.run", lambda args, **kw: calls.append(args) or _Proc())
    out = ch.apply_people_gateway(object())
    assert out["ok"] and calls[0][:3] == ["systemctl", "--user", "restart"]
    with pytest.raises(RuntimeError):
        ch.apply_people_gateway(object())  # second time within ten minutes, non-admin
    monkeypatch.setattr(ch, "_is_admin", lambda handler: True)
    assert ch.apply_people_gateway(object())["ok"]


def test_self_service_routes_are_wired():
    root = Path(__file__).resolve().parent.parent
    routes = (root / "api" / "routes.py").read_text()
    assert 'parsed.path.startswith("/api/me/channels")' in routes and 'if parsed.path == "/api/me/channels":' in routes
    from api.governance.catalog import ROUTE_CATALOG
    rule = next(r for r in ROUTE_CATALOG if r.pattern == "/api/me/channels")
    assert rule.matches("/api/me/channels/link") and rule.permission_for("POST") == "sessions:read"
    js = (root / "static" / "integrations.js").read_text()
    for name in ("chLoadMine", "chSaveMyBot", "chLinkMe", "chApplyMine", "/api/me/channels/apply"):
        assert name in js


def test_discord_and_slack_are_own_bot_platforms_too(me):
    out = ch.set_my_bot(object(), "slack", {"SLACK_BOT_TOKEN": "xoxb-1", "SLACK_APP_TOKEN": "xapp-1"})
    assert out["token_set"] is True
    out = ch.set_my_bot(object(), "discord", {"DISCORD_HOME_CHANNEL": "42"})
    assert out["token_set"] is False  # token still missing
    own = ch.my_channels_payload(object())["own_bot"]
    assert own["slack"]["token_set"] and not own["discord"]["token_set"]
    assert [f["key"] for f in own["discord"]["fields"]] == ["DISCORD_BOT_TOKEN", "DISCORD_HOME_CHANNEL"]
    with pytest.raises(ValueError):
        ch.set_my_bot(object(), "teams", {"TEAMS_CLIENT_ID": "x"})
