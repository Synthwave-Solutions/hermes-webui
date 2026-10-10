"""Profile env and the model gateway (plan 3.12, package R3).

``_reload_dotenv`` and the runtime env path (``get_profile_runtime_env``, which
streaming and the profile-scoped workers apply) must:

* never take the installation's gateway posture (``SP_MODEL_GATEWAY_*``,
  ``SP_MANAGED``, ``SP_AUDIT_ORG_SALT_FILE``) from a profile ``.env``, so a
  profile cannot lift enforcement, repoint the gateway or borrow another
  profile's key file;
* under model gateway enforcement, skip provider key variables from a profile
  ``.env`` with one warning per profile (names only, never values), while the
  profile's own gateway key stays;
* give each profile its own gateway key file.

Without enforcement nothing changes.
"""

import logging
import os
from unittest import mock

import pytest
import yaml

import api.profiles as profiles


_GATEWAY = "http://gateway.test:4000/v1"


@pytest.fixture(autouse=True)
def gateway_env(tmp_path, monkeypatch):
    for name in (
        "SP_MODEL_GATEWAY_ENFORCE",
        "SP_MODEL_GATEWAY_URL",
        "SP_MODEL_GATEWAY_KEY_FILE",
        "SP_MODEL_GATEWAY_REALTIME",
        "SP_MODEL_GATEWAY_AUDIO",
        "SP_MANAGED",
        "SP_AUDIT_ORG_SALT_FILE",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(profiles, "_INITIAL_GATEWAY_ENFORCE", "", raising=False)
    monkeypatch.setattr(profiles, "_INITIAL_GATEWAY_KEY_FILE", "", raising=False)
    base = tmp_path / "base"
    base.mkdir()
    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", base)
    warned = getattr(profiles, "_GATEWAY_ENV_WARNED", None)
    if warned is not None:
        monkeypatch.setattr(profiles, "_GATEWAY_ENV_WARNED", set())
    monkeypatch.setattr(profiles, "_loaded_profile_env_keys", set())
    yield base


def _home(tmp_path, name, *, env="", config=None):
    home = tmp_path / "base" / "profiles" / name
    home.mkdir(parents=True)
    if env:
        (home / ".env").write_text(env, encoding="utf-8")
    if config is not None:
        (home / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    return home


_PROFILE_ENV = (
    "OPENAI_API_KEY=sk-openai-profile\n"
    "ELEVENLABS_API_KEY=el-profile\n"
    "ANTHROPIC_TOKEN=ant-profile\n"
    "OPENROUTER_API_KEY=or-profile\n"
    "OMNIROUTE_API_KEY=gw-profile\n"
    "NOTION_API_TOKEN=notion-profile\n"
    "GITHUB_TOKEN=gh-profile\n"
    "TERMINAL_TIMEOUT=60\n"
)


# ── Gateway posture is never taken from a profile .env ─────────────────────


def test_runtime_env_never_takes_gateway_posture_from_profile_env(tmp_path):
    home = _home(
        tmp_path,
        "alice",
        env=(
            "SP_MODEL_GATEWAY_ENFORCE=0\n"
            "SP_MODEL_GATEWAY_URL=https://attacker.example/v1\n"
            "SP_MODEL_GATEWAY_KEY_FILE=/run/other-profile.key\n"
            "SP_MODEL_GATEWAY_REALTIME=1\n"
            "SP_MANAGED=0\n"
            "SP_AUDIT_ORG_SALT_FILE=/tmp/salt\n"
            "MY_SETTING=kept\n"
        ),
    )
    env = profiles.get_profile_runtime_env(home)
    for name in (
        "SP_MODEL_GATEWAY_ENFORCE",
        "SP_MODEL_GATEWAY_URL",
        "SP_MODEL_GATEWAY_REALTIME",
        "SP_MANAGED",
        "SP_AUDIT_ORG_SALT_FILE",
    ):
        assert name not in env, name
    assert env.get("SP_MODEL_GATEWAY_KEY_FILE", "") != "/run/other-profile.key"
    assert env["MY_SETTING"] == "kept"


def test_reload_dotenv_never_lifts_enforcement_or_repoints_gateway(tmp_path, monkeypatch):
    home = _home(
        tmp_path,
        "alice",
        env=(
            "SP_MODEL_GATEWAY_ENFORCE=0\n"
            "SP_MODEL_GATEWAY_URL=https://attacker.example/v1\n"
            "SP_MODEL_GATEWAY_KEY_FILE=/run/other-profile.key\n"
            "SP_MANAGED=0\n"
            "MY_SETTING=kept\n"
        ),
    )
    with mock.patch.dict(os.environ, {
        "SP_MODEL_GATEWAY_ENFORCE": "1",
        "SP_MODEL_GATEWAY_URL": _GATEWAY,
        "SP_MODEL_GATEWAY_KEY_FILE": "/run/webui.key",
        "SP_MANAGED": "1",
    }):
        profiles._reload_dotenv(home)
        assert os.environ["SP_MODEL_GATEWAY_ENFORCE"] == "1"
        assert os.environ["SP_MODEL_GATEWAY_URL"] == _GATEWAY
        assert os.environ["SP_MODEL_GATEWAY_KEY_FILE"] == ""
        assert os.environ["SP_MANAGED"] == "1"
        assert os.environ["MY_SETTING"] == "kept"
        assert profiles.model_gateway_enforced(home) is True


# ── Without enforcement nothing changes ─────────────────────────────────────


def test_provider_keys_still_load_without_enforcement(tmp_path):
    home = _home(tmp_path, "alice", env=_PROFILE_ENV)
    assert profiles.model_gateway_enforced(home) is False
    env = profiles.get_profile_runtime_env(home)
    assert env["OPENAI_API_KEY"] == "sk-openai-profile"
    assert env["ELEVENLABS_API_KEY"] == "el-profile"
    assert env["ANTHROPIC_TOKEN"] == "ant-profile"
    assert "SP_MODEL_GATEWAY_KEY_FILE" not in env
    with mock.patch.dict(os.environ, {}):
        profiles._reload_dotenv(home)
        assert os.environ["OPENAI_API_KEY"] == "sk-openai-profile"
        assert os.environ["NOTION_API_TOKEN"] == "notion-profile"


# ── Under enforcement provider keys are skipped ─────────────────────────────


def test_runtime_env_skips_provider_keys_under_env_enforcement(tmp_path, monkeypatch):
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")
    home = _home(tmp_path, "alice", env=_PROFILE_ENV)
    env = profiles.get_profile_runtime_env(home)
    for name in ("OPENAI_API_KEY", "ELEVENLABS_API_KEY", "ANTHROPIC_TOKEN", "OPENROUTER_API_KEY"):
        assert name not in env, name
    # Not provider keys: the gateway key, tool tokens and shared credentials stay.
    assert env["OMNIROUTE_API_KEY"] == "gw-profile"
    assert env["NOTION_API_TOKEN"] == "notion-profile"
    assert env["GITHUB_TOKEN"] == "gh-profile"
    assert env["TERMINAL_TIMEOUT"] == "60"


def test_startup_enforcement_snapshot_cannot_be_cleared_later(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles, "_INITIAL_GATEWAY_ENFORCE", "1")
    home = _home(tmp_path, "alice", env=_PROFILE_ENV)
    assert profiles.model_gateway_enforced(home) is True
    assert "OPENAI_API_KEY" not in profiles.get_profile_runtime_env(home)


def test_runtime_env_skips_provider_keys_under_profile_config_enforcement(tmp_path):
    home = _home(tmp_path, "alice", env=_PROFILE_ENV,
                 config={"model_gateway": {"enforce": True, "base_url": _GATEWAY}})
    assert profiles.model_gateway_enforced(home) is True
    env = profiles.get_profile_runtime_env(home)
    assert "OPENAI_API_KEY" not in env
    assert env["OMNIROUTE_API_KEY"] == "gw-profile"


def test_root_config_enforcement_is_a_floor_for_every_profile(tmp_path, gateway_env):
    (gateway_env / "config.yaml").write_text(
        yaml.safe_dump({"model_gateway": {"enforce": True}}), encoding="utf-8")
    home = _home(tmp_path, "alice", env=_PROFILE_ENV,
                 config={"model_gateway": {"enforce": False}})
    assert profiles.model_gateway_enforced(home) is True
    assert "OPENAI_API_KEY" not in profiles.get_profile_runtime_env(home)


def test_reload_dotenv_skips_provider_keys_under_enforcement(tmp_path, monkeypatch):
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")
    home = _home(tmp_path, "alice", env=_PROFILE_ENV)
    with mock.patch.dict(os.environ, {}):
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("ELEVENLABS_API_KEY", None)
        profiles._reload_dotenv(home)
        assert "OPENAI_API_KEY" not in os.environ
        assert "ELEVENLABS_API_KEY" not in os.environ
        assert os.environ["OMNIROUTE_API_KEY"] == "gw-profile"
        assert os.environ["NOTION_API_TOKEN"] == "notion-profile"
        assert "OPENAI_API_KEY" not in profiles._loaded_profile_env_keys


def test_one_warning_per_profile_names_only(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")
    alice = _home(tmp_path, "alice", env=_PROFILE_ENV)
    bob = _home(tmp_path, "bob", env="OPENAI_API_KEY=sk-bob-secret\n")
    caplog.set_level(logging.WARNING, logger="api.profiles")
    with mock.patch.dict(os.environ, {}):
        profiles.get_profile_runtime_env(alice)
        profiles.get_profile_runtime_env(alice)
        profiles._reload_dotenv(alice)
        profiles.get_profile_runtime_env(bob)
        profiles.get_profile_runtime_env(bob)
    records = [r for r in caplog.records if "provider key" in r.getMessage()]
    assert len(records) == 2, [r.getMessage() for r in records]
    text = "\n".join(r.getMessage() for r in records)
    assert "OPENAI_API_KEY" in text and "ELEVENLABS_API_KEY" in text
    for secret in ("sk-openai-profile", "el-profile", "ant-profile", "sk-bob-secret"):
        assert secret not in text


def test_gateway_key_declared_by_profile_is_kept_even_with_provider_name(tmp_path, monkeypatch):
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")
    monkeypatch.setenv("SP_MODEL_GATEWAY_URL", _GATEWAY)
    home = _home(
        tmp_path,
        "alice",
        env="OPENAI_API_KEY=gw-key-for-gateway\nANTHROPIC_API_KEY=sk-ant-direct\n",
        config={"custom_providers": [
            {"name": "Gateway", "base_url": _GATEWAY, "key_env": "OPENAI_API_KEY"},
            {"name": "Direct", "base_url": "https://api.anthropic.com", "key_env": "ANTHROPIC_API_KEY"},
        ]},
    )
    env = profiles.get_profile_runtime_env(home)
    assert env["OPENAI_API_KEY"] == "gw-key-for-gateway"
    assert "ANTHROPIC_API_KEY" not in env


def test_provider_key_names_cover_model_keys_but_not_shared_credentials():
    names = profiles.provider_key_env_names()
    for name in (
        "OPENAI_API_KEY", "VOICE_TOOLS_OPENAI_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
        "ELEVENLABS_API_KEY", "FAL_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY", "XAI_API_KEY",
        "DEEPSEEK_API_KEY", "CORTECS_API_KEY", "AWS_BEARER_TOKEN_BEDROCK",
    ):
        assert name in names, name
    for name in (
        "OMNIROUTE_API_KEY", "GITHUB_TOKEN", "GH_TOKEN", "NOTION_API_TOKEN",
        "AWS_ACCESS_KEY_ID", "AZURE_CLIENT_SECRET", "CUSTOM_API_KEY", "LM_API_KEY",
        "SP_MODEL_GATEWAY_KEY_FILE",
    ):
        assert name not in names, name


# ── Each profile uses its own gateway key file ──────────────────────────────


def test_profile_key_file_becomes_the_runtime_key_file(tmp_path):
    home = _home(tmp_path, "alice",
                 config={"model_gateway": {"key_file": "secrets/gateway.key"}})
    env = profiles.get_profile_runtime_env(home)
    assert env["SP_MODEL_GATEWAY_KEY_FILE"] == str(home / "secrets" / "gateway.key")
    absolute = _home(tmp_path, "bob",
                     config={"model_gateway": {"key_file": "/run/synthpulse/secrets/gateway/bob.key"}})
    assert profiles.get_profile_runtime_env(absolute)["SP_MODEL_GATEWAY_KEY_FILE"] == (
        "/run/synthpulse/secrets/gateway/bob.key")


def test_profile_with_its_own_gateway_key_variable_does_not_inherit_the_installation_key(tmp_path, monkeypatch):
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")
    monkeypatch.setenv("SP_MODEL_GATEWAY_URL", _GATEWAY)
    monkeypatch.setenv("SP_MODEL_GATEWAY_KEY_FILE", "/run/webui.key")
    home = _home(tmp_path, "alice", env="OMNIROUTE_API_KEY=gw-alice\n", config={
        "custom_providers": [{"name": "OmniRoute", "base_url": _GATEWAY, "key_env": "OMNIROUTE_API_KEY"}]})
    env = profiles.get_profile_runtime_env(home)
    # Blank, so the engine's gateway key lookup falls through to the profile's key.
    assert env["SP_MODEL_GATEWAY_KEY_FILE"] == ""
    assert env["OMNIROUTE_API_KEY"] == "gw-alice"


def test_enforced_profile_without_its_own_key_cannot_inherit_installation_key_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")
    monkeypatch.setenv("SP_MODEL_GATEWAY_KEY_FILE", "/run/webui.key")
    home = _home(tmp_path, "alice", env="NOTION_API_TOKEN=n\n")
    assert profiles.get_profile_runtime_env(home)["SP_MODEL_GATEWAY_KEY_FILE"] == ""


def test_reload_dotenv_applies_then_restores_the_profile_key_file(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles, "_INITIAL_GATEWAY_KEY_FILE", "/run/webui.key")
    alice = _home(tmp_path, "alice", config={"model_gateway": {"key_file": "/keys/alice.key"}})
    bob = _home(tmp_path, "bob", env="NOTION_API_TOKEN=n\n")
    with mock.patch.dict(os.environ, {"SP_MODEL_GATEWAY_KEY_FILE": "/run/webui.key"}):
        profiles._reload_dotenv(alice)
        assert os.environ["SP_MODEL_GATEWAY_KEY_FILE"] == "/keys/alice.key"
        profiles._reload_dotenv(bob)
        assert os.environ["SP_MODEL_GATEWAY_KEY_FILE"] == "/run/webui.key"


def test_model_gateway_key_resolution_order(tmp_path, monkeypatch):
    install_key = tmp_path / "webui.key"
    install_key.write_text("gw-installation\n", encoding="utf-8")
    monkeypatch.setattr(profiles, "_INITIAL_GATEWAY_KEY_FILE", str(install_key))
    monkeypatch.setenv("SP_MODEL_GATEWAY_URL", _GATEWAY)

    own_file = tmp_path / "alice.key"
    own_file.write_text("gw-alice-file\n", encoding="utf-8")
    alice = _home(tmp_path, "alice", config={"model_gateway": {"key_file": str(own_file)}})
    assert profiles.model_gateway_key(alice) == "gw-alice-file"

    bob = _home(tmp_path, "bob", env="OMNIROUTE_API_KEY=gw-bob-env\n", config={
        "custom_providers": [{"name": "OmniRoute", "base_url": _GATEWAY, "key_env": "OMNIROUTE_API_KEY"}]})
    assert profiles.model_gateway_key(bob) == "gw-bob-env"

    carol = _home(tmp_path, "carol", env="NOTION_API_TOKEN=n\n")
    assert profiles.model_gateway_key(carol) == "gw-installation"

    # A named profile never borrows another profile's key through the live env.
    monkeypatch.setattr(profiles, "_INITIAL_GATEWAY_KEY_FILE", "")
    with mock.patch.dict(os.environ, {"SP_MODEL_GATEWAY_KEY_FILE": str(own_file)}):
        assert profiles.model_gateway_key(carol) == ""


def test_background_worker_scope_hides_process_provider_keys_under_enforcement(tmp_path, monkeypatch):
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")
    home = _home(tmp_path, "alice", env=_PROFILE_ENV)
    monkeypatch.setattr(profiles, "get_hermes_home_for_profile", lambda name: home)
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-process-root",
                                      "ELEVENLABS_API_KEY": "el-process-root"}):
        with profiles.profile_env_for_background_worker("alice", "test"):
            assert "OPENAI_API_KEY" not in os.environ
            assert "ELEVENLABS_API_KEY" not in os.environ
            assert os.environ["OMNIROUTE_API_KEY"] == "gw-profile"
        assert os.environ["OPENAI_API_KEY"] == "sk-process-root"
        assert os.environ["ELEVENLABS_API_KEY"] == "el-process-root"


def test_background_worker_scope_keeps_process_keys_without_enforcement(tmp_path, monkeypatch):
    home = _home(tmp_path, "alice", env="NOTION_API_TOKEN=n\n")
    monkeypatch.setattr(profiles, "get_hermes_home_for_profile", lambda name: home)
    with mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "el-process-root"}):
        with profiles.profile_env_for_background_worker("alice", "test"):
            assert os.environ["ELEVENLABS_API_KEY"] == "el-process-root"


def test_gateway_route_flags_and_base_url(tmp_path, monkeypatch):
    home = _home(tmp_path, "alice", config={"model_gateway": {"base_url": "http://cfg.test/v1/", "realtime": True}})
    assert profiles.model_gateway_base_url(home) == "http://cfg.test/v1"
    assert profiles.model_gateway_route_enabled("realtime", home) is True
    assert profiles.model_gateway_route_enabled("audio", home) is False
    monkeypatch.setenv("SP_MODEL_GATEWAY_URL", _GATEWAY)
    monkeypatch.setenv("SP_MODEL_GATEWAY_AUDIO", "1")
    # The installation env wins over a profile config.
    assert profiles.model_gateway_base_url(home) == _GATEWAY
    assert profiles.model_gateway_route_enabled("audio", home) is True
    assert profiles.model_gateway_route_enabled("anything", home) is False


def test_enforced_profile_cannot_borrow_startup_installation_key(tmp_path, monkeypatch):
    key = tmp_path / "install.key"
    key.write_text("installation-secret")
    monkeypatch.setattr(profiles, "_INITIAL_GATEWAY_KEY_FILE", str(key))
    home = _home(tmp_path, "alice")
    assert profiles.model_gateway_key(home) == "installation-secret"
    monkeypatch.setenv("SP_MODEL_GATEWAY_ENFORCE", "1")
    assert profiles.model_gateway_key(home) == ""
    assert profiles.model_gateway_key(profiles._DEFAULT_HERMES_HOME) == "installation-secret"
