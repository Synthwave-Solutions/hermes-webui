"""The Memory explorer's hub backend against a fake hub (addendum 6.6.7, 6.6.10).

The hub gets the ``webui`` bearer token and an ``X-Mnemo-Actor`` assertion
with ``ctx: ui`` and the viewer's ``mem_admin`` and ``guest`` claims; a hub
404 gives 404, a hub 401 or 5xx gives 503, a hub 403 gives 404 with a
``memory.admin_denied`` audit event, a hub 409 gives 409.

Until A6 merges, the tests stand in A6's minter with a fake of exactly its
pinned signature. With ``MEMDASH_HUB_TEST_REAL_MINTER=1`` they use the real
``api.mnemo_actor`` with a throwaway key and token written under the pytest
temporary directory (the orchestrator's run after A6 merges).
"""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures" / "memdash"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _fake_mnemo_hub_dash as fake  # noqa: E402
import memdash_harness as H  # noqa: E402
from api import memdash_backend as backends  # noqa: E402
from api import memdash_registry as registry  # noqa: E402

REAL_MINTER = os.environ.get("MEMDASH_HUB_TEST_REAL_MINTER") == "1"


@pytest.fixture
def hub(monkeypatch, tmp_path):
    key = os.urandom(32)
    token = "fake-webui-token-" + os.urandom(8).hex()
    server = fake.FakeHub(key=key, token=token)
    if REAL_MINTER:
        key_file = tmp_path / "actor.key"
        token_file = tmp_path / "webui.token"
        for path, text in ((key_file, "k1:" + key.hex() + "\n"), (token_file, token + "\n")):
            path.write_text(text, encoding="ascii")
            path.chmod(0o600)
        monkeypatch.setenv("HERMES_WEBUI_MNEMO_ACTOR_KEY_FILE", str(key_file))
        monkeypatch.setenv("HERMES_WEBUI_MNEMO_TOKEN_FILE", str(token_file))
    else:
        minter = fake.FakeMinter(key, token)
        monkeypatch.setitem(sys.modules, "api.mnemo_actor", minter.module())
    server.add_bank("bank-ada", kind="personal", owner_email=H.ADA, owner_display="Ada Lovelace",
                    counts={"working_memory": 7, "episodic_memory": 2, "triples": 4},
                    memories=[{"id": "m1", "content": "Ada likes " + H.CANARY + " api_key=sk-live-1234567890abcdef",
                               "metadata_json": "{\"token\": \"ghp_abcdefghijklmnopqrstuvwxyz0123456789\"}",
                               "db_path": "/x", "importance": 0.5}])
    server.add_bank("bank-bob", kind="personal", owner_email=H.BOB, owner_display="Bob",
                    counts={"working_memory": 2, "episodic_memory": 0, "triples": 0})
    server.add_bank("bank-michael", kind="personal", owner_email=H.MICHAEL, owner_display="Michael",
                    owner_private=True, counts={"working_memory": 11, "episodic_memory": 5, "triples": 9})
    server.add_bank("bank-yaser", kind="personal", owner_email=H.YASER, owner_display="Yaser")
    server.add_bank("bank-odis", kind="personal", owner_email=H.ODIS, owner_display="Odis")
    server.add_bank("bank-hrishikesh", kind="personal", owner_email=H.HRISHIKESH, owner_display="Hrishikesh")
    server.add_bank("team-shared", kind="shared", label="Team")
    server.add_bank("sales-ops", kind="assistant", label="Sales")
    base = server.start()
    yield server, base
    server.stop()


@pytest.fixture
def env(monkeypatch, tmp_path, hub):
    server, base = hub
    environment = H.Env(monkeypatch, tmp_path, backend="hub")
    monkeypatch.setenv("HERMES_WEBUI_MNEMO_URL", base)
    environment.hub = server
    yield environment
    environment.close()


def _ref(hub_ref: str) -> str:
    return registry.ref_for("hubapi:" + hub_ref)


def _viewer(env, email):
    return env.scope.resolve_viewer(H.identity(email), env.config)


def test_a_member_lists_only_their_own_store_and_sends_no_admin_claim(env):
    env.as_user(H.ADA, "Ada Lovelace")
    banks = env.banks()
    assert banks["available"] is True and banks["changes_available"] is True
    assert [s["ref"] for s in banks["stores"]] == [_ref("bank-ada")]
    assert banks["me"] == _ref("bank-ada") and banks["viewer"]["admin"] is False
    call = env.hub.calls("/v1/banks")[-1]
    assert call["authorization"] == "Bearer " + env.hub.token
    assert call["claims"]["sub"] == H.ADA and call["claims"]["ctx"] == "ui"
    assert "mem_admin" not in call["claims"] and "guest" not in call["claims"]


def test_the_members_counts_equal_the_hubs_counts(env):
    env.as_user(H.ADA, "Ada Lovelace")
    response = env.view("me", "stats")
    assert response.status == 200
    assert response.body["counts"] == {"working_memory": 7, "episodic_memory": 2, "triples": 4}
    # Paths and pids never leave the adapter.
    assert "db_path" not in response.body and "pid" not in response.body
    assert env.hub.calls("/v1/banks/bank-ada/dash/stats")
    # The member's own view is never logged.
    assert env.access_log.rows_all() == []


def test_a_platform_admin_sends_the_platform_claim_and_is_logged_before_data(env):
    env.as_user(H.YASER, "Yaser")
    banks = env.banks()
    refs = {s["ref"] for s in banks["stores"]}
    assert _ref("bank-ada") in refs and _ref("bank-michael") not in refs
    response = env.view(_ref("bank-ada"), "stats", reason_code="support")
    assert response.status == 200 and response.body["counts"]["working_memory"] == 7
    claims = env.hub.calls("/v1/banks/bank-ada/dash/stats")[-1]["claims"]
    assert claims["sub"] == H.YASER and claims["mem_admin"] == "platform" and "guest" not in claims
    rows = env.access_log.rows_for_store(_ref("bank-ada"))
    assert [(r["action"], r["role"], r["reason_code"]) for r in rows] == [("open", "platform_admin", "support")]


def test_secrets_are_masked_in_another_persons_store_but_not_in_ones_own(env):
    env.as_user(H.YASER, "Yaser")
    other = env.view(_ref("bank-ada"), "memories").body["items"][0]
    assert "sk-live-1234567890abcdef" not in other["content"]
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in other["metadata_json"]
    assert "db_path" not in other and other["id"] == "m1"
    env.as_user(H.ADA, "Ada Lovelace")
    own = env.view("me", "memories").body["items"][0]
    assert "sk-live-1234567890abcdef" in own["content"]


@pytest.mark.parametrize("admin", [H.YASER, H.ODIS, H.HRISHIKESH])
def test_owner_private_banks_are_refused_to_every_other_admin(env, admin):
    # Even when a hub lists the owner-private bank, the adapter refuses it.
    env.hub.visible = lambda bank, claims: True
    env.as_user(admin)
    banks = env.banks()
    assert _ref("bank-michael") not in {s["ref"] for s in banks["stores"]}
    response = env.view(_ref("bank-michael"), "stats", reason_code="support")
    assert response.status == 404 and "counts" not in response.body
    assert not env.hub.calls("/v1/banks/bank-michael/")
    assert env.access_log.rows_for_store(_ref("bank-michael")) == []
    assert any(r.get("event") == "memory.admin_denied" for r in env.audit_rows())


def test_the_owner_opens_their_owner_private_bank(env):
    env.as_user(H.MICHAEL, "Michael")
    response = env.view("me", "stats")
    assert response.status == 200 and response.body["counts"]["working_memory"] == 11
    assert env.access_log.rows_all() == []


@pytest.mark.parametrize("status, expected", [(404, 404), (401, 503), (500, 503), (502, 503), (503, 503)])
def test_hub_errors_map_to_404_or_503(env, status, expected):
    env.as_user(H.YASER, "Yaser")
    ref = _ref("bank-ada")
    env.banks()
    env.hub.fail["/v1/banks/bank-ada/dash/"] = status
    response = env.view(ref, "graph", reason_code="support")
    assert response.status == expected
    assert "counts" not in response.body


def test_a_hub_403_is_a_404_and_an_audited_denial(env):
    env.as_user(H.YASER, "Yaser")
    env.banks()
    env.hub.fail["/v1/banks/bank-bob/dash/"] = 403
    response = env.view(_ref("bank-bob"), "stats", reason_code="support")
    assert response.status == 404
    events = [r for r in env.audit_rows() if r.get("event") == "memory.admin_denied"]
    assert events and events[-1]["extra"]["outcome"] == "hub_refused"


@pytest.mark.parametrize("status", [401, 500])
def test_a_hub_failure_on_the_registry_makes_the_explorer_unavailable(env, status):
    env.as_user(H.ADA, "Ada Lovelace")
    env.hub.fail["/v1/banks"] = status
    banks = env.banks()
    assert banks["available"] is False and banks["stores"] == []
    assert env.view("me", "stats").status == 503


def test_an_unreachable_hub_gives_503(env, monkeypatch):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    monkeypatch.setenv("HERMES_WEBUI_MNEMO_URL", f"http://127.0.0.1:{port}")
    env.as_user(H.ADA, "Ada Lovelace")
    assert env.banks()["available"] is False
    assert env.view("me", "stats").status == 503


@pytest.mark.skipif(REAL_MINTER, reason="checks the guarded import itself")
def test_without_the_minter_the_hub_backend_answers_503(env, monkeypatch):
    monkeypatch.setitem(sys.modules, "api.mnemo_actor", None)
    env.as_user(H.ADA, "Ada Lovelace")
    assert env.banks()["available"] is False
    assert env.view("me", "stats").status == 503
    assert env.hub.requests == []


@pytest.mark.parametrize("url", ["", "ftp://127.0.0.1/", "http://user:pw@127.0.0.1:1/", "http://127.0.0.1:1/?x=1", "notaurl"])
def test_an_unusable_hub_url_is_refused(url):
    with pytest.raises(backends.BackendUnavailable):
        backends.HubBackend(base_url=url)


def test_the_hub_backend_ignores_proxy_settings(env, monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
    env.as_user(H.ADA, "Ada Lovelace")
    assert env.view("me", "stats").status == 200


def test_changes_go_to_the_hub_routes(env):
    env.as_user(H.ADA, "Ada Lovelace")
    env.banks()
    for action, op, extra in (("invalidate", "forget", {}), ("supersede", "update", {"content": "new text", "updated_at": "2026-09-27T10:00:00Z"}),
                              ("importance", "meta", {"importance": 0.9}), ("veracity", "meta", {"veracity": "stated"}),
                              ("expiry", "meta", {"valid_until": "2026-12-31"})):
        body = {"bank": "me", "action": action, "memory_id": "m1", "email": H.BOB, "user": H.BOB, **extra}
        response = env.post("/api/memdash/v1/action", body)
        assert response.status == 200, (action, response.raw)
        assert response.body["op"] == op
    changes = env.hub.banks["bank-ada"]["changes"]
    assert [c["op"] for c in changes] == ["forget", "update", "meta", "meta", "meta"]
    assert all(c["claims"]["sub"] == H.ADA and "mem_admin" not in c["claims"] for c in changes)
    # The actor comes only from the session: body email and user are dropped.
    assert all("email" not in c["body"] and "user" not in c["body"] for c in changes)
    assert changes[1]["body"]["content"] == "new text"
    assert env.access_log.rows_all() == []


def test_a_stale_edit_gives_409(env):
    env.hub.banks["bank-ada"]["stale"] = True
    env.as_user(H.ADA, "Ada Lovelace")
    response = env.post("/api/memdash/v1/action", {"bank": "me", "action": "supersede", "memory_id": "m1",
                                                   "content": "x", "updated_at": "2026-09-01T00:00:00Z"})
    assert response.status == 409


def test_a_staff_guest_on_a_client_installation_sends_the_guest_claim(env, monkeypatch):
    env.set_policy(H.hq_policy(installation={"kind": "managed"}, organization={"id": "org_acme", "name": "Acme"}))
    monkeypatch.setattr(env.scope, "_staff_guest_checker", lambda identity: identity.get("email") == H.MICHAEL)
    env.hub.visible = lambda bank, claims: claims.get("guest") is True or bank["owner_email"] == claims.get("sub")
    env.as_user(H.MICHAEL, "Michael")
    viewer = _viewer(env, H.MICHAEL)
    assert viewer.kind == "platform_admin" and viewer.guest is True
    response = env.view(_ref("bank-ada"), "stats", reason_code="support")
    assert response.status == 200
    claims = env.hub.calls("/v1/banks/bank-ada/dash/stats")[-1]["claims"]
    assert claims["mem_admin"] == "platform" and claims["guest"] is True


def test_view_paths_are_quoted_and_only_allowlisted_views_reach_the_hub(env):
    env.as_user(H.ADA, "Ada Lovelace")
    assert env.view("me", "config").status == 404
    assert env.view("me", "../../v1/admin").status == 404
    assert env.view("me", "memoria/facts", q="x").status == 200
    paths = [r["path"] for r in env.hub.requests if "/dash/" in r["path"]]
    assert paths == ["/v1/banks/bank-ada/dash/memoria/facts"]
