"""Personal settings HTTP contract: encrypted storage, no secret responses."""
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from api import vault

ALICE = {"email": "alice@example.test"}
BOB = {"email": "bob@example.test"}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr("api.config.STATE_DIR", tmp_path / "state")
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "host"))


def call(identity, action, body=None):
    with patch("api.ownership._request_identity", return_value=identity), patch("api.routes.j", side_effect=lambda h, p, status=200: (status, p)):
        return vault.handle(object(), action, body)


def test_login_roundtrip_is_encrypted_and_identity_cannot_be_overridden(tmp_path):
    from api.personal_context import home
    password = "unique password <123>"
    code, result = call(ALICE, "add", {"label": "Work", "origin": "https://example.test/login",
        "email": BOB["email"], "profile": "other-bot", "secret": {"identifier_type": "email",
        "identifier": "account@example.test", "password": password}})
    assert code == 200
    item_id = result["id"]
    code, status = call(ALICE, "status")
    assert status["sources"][0]["enabled"] is True
    assert status["items"][0]["id"] == item_id
    assert password not in json.dumps(status)
    assert password.encode() not in (home(ALICE) / "vault/vault.json.enc").read_bytes()
    assert call(BOB, "status")[1]["items"] == []
    assert call(BOB, "remove", {"id": item_id}) == (200, {"removed": False})
    assert call(ALICE, "remove", {"id": item_id}) == (200, {"removed": True})


def test_manager_setup_uses_private_env_and_response_never_contains_tokens(tmp_path):
    from api.personal_context import home
    seen = []
    with patch("agent.vault_backends.base.is_installed", return_value=True), patch(
        "agent.vault_backends.onepassword.find_op", return_value=tmp_path / "op"
    ), patch.object(vault, "_cli", side_effect=lambda args, env: seen.append((args, env))):
        token = "service_account_private_token"
        assert call(ALICE, "configure", {"name": "onepassword", "service_account_token": token}) == (200, {"ok": True})
    assert token not in json.dumps(seen[0][0])
    assert seen[0][1]["OP_SERVICE_ACCOUNT_TOKEN"] == token
    assert seen[0][1]["HOME"].startswith(str(home(ALICE)))
    assert token.encode() not in (home(ALICE) / "vault/sources.json.enc").read_bytes()
    assert token not in json.dumps(call(ALICE, "status"))
    assert not call(BOB, "status")[1]["sources"][2]["configured"]
    assert call(ALICE, "disconnect", {"name": "onepassword"}) == (200, {"ok": True})
    with vault.vault_scope(ALICE):
        from agent.vault_store import get_vault_store
        assert "service_account_token" not in get_vault_store().read_source_settings()["onepassword"]


def test_bitwarden_api_secret_only_goes_to_isolated_child_environment(tmp_path):
    calls = []
    with patch("agent.vault_backends.base.is_installed", return_value=True), patch(
        "agent.vault_backends.bitwarden.shutil.which", return_value=str(tmp_path / "bw")
    ), patch.object(vault, "_cli", side_effect=lambda args, env: calls.append((args, dict(env)))):
        assert call(ALICE, "configure", {"name": "bitwarden", "client_id": "user.12345678-abcd",
            "client_secret": "private_client_secret", "server": "https://vault.bitwarden.eu"}) == (200, {"ok": True})
    assert calls[1][1]["BW_CLIENTSECRET"] == "private_client_secret"
    assert "private_client_secret" not in json.dumps([c[0] for c in calls])
    with vault.vault_scope(ALICE):
        from agent.vault_store import get_vault_store
        assert "private_client_secret" not in json.dumps(get_vault_store().read_source_settings())


@pytest.mark.parametrize("secret", ["short", "Authorization: Bearer hidden-token", "-----BEGIN PRIVATE KEY-----"])
def test_errors_never_echo_secret_values(secret, caplog):
    backend = SimpleNamespace(unlock=lambda password: (_ for _ in ()).throw(RuntimeError(password)))
    with patch.object(vault, "_manager", return_value=backend):
        code, response = call(ALICE, "unlock", {"name": "bitwarden", "password": secret})
    assert code == 400
    assert secret not in json.dumps(response)
    assert secret not in caplog.text


def test_unauthenticated_and_invalid_source_cannot_use_vault():
    assert call({}, "status")[0] == 403
    assert call(ALICE, "configure", {"name": "../../other", "enabled": True})[0] == 400
