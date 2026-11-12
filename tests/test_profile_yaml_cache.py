"""The per-turn bot directory reuses a parsed profile.yaml only while it is unchanged."""
import os

import pytest

from api import bot_builder, bot_metadata, profile_yaml_cache, profiles


@pytest.fixture(autouse=True)
def _fresh_cache():
    profile_yaml_cache.clear()
    yield
    profile_yaml_cache.clear()


def _settled(monkeypatch):
    # ctime cannot be set from user space: treat every file as settled instead.
    monkeypatch.setattr(profile_yaml_cache, "_RACY_NS", -1)


def _counting(loader):
    calls = []

    def wrapped(path):
        calls.append(path)
        return loader(path)

    return wrapped, calls


def test_unchanged_file_is_parsed_once(tmp_path, monkeypatch):
    _settled(monkeypatch)
    path = tmp_path / "profile.yaml"
    path.write_text("a: 1\n")
    loader, calls = _counting(bot_builder._yaml)
    assert profile_yaml_cache.load(path, loader) == {"a": 1}
    assert profile_yaml_cache.load(path, loader) == {"a": 1}
    assert len(calls) == 1


def test_in_place_rewrite_and_replacement_are_seen(tmp_path, monkeypatch):
    _settled(monkeypatch)
    path = tmp_path / "profile.yaml"
    path.write_text("a: 1\n")
    loader, calls = _counting(bot_builder._yaml)
    assert profile_yaml_cache.load(path, loader) == {"a": 1}
    path.write_text("a: 22\n")
    assert profile_yaml_cache.load(path, loader) == {"a": 22}
    other = tmp_path / "next.yaml"
    other.write_text("a: 3\n")
    os.replace(other, path)
    assert profile_yaml_cache.load(path, loader) == {"a": 3}
    assert len(calls) == 3


def test_recently_written_file_is_never_kept(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text("a: 1\n")
    loader, calls = _counting(bot_builder._yaml)
    profile_yaml_cache.load(path, loader)
    profile_yaml_cache.load(path, loader)
    assert len(calls) == 2
    assert not profile_yaml_cache._ENTRIES


def test_missing_symlinked_and_invalid_files_go_to_the_loader_each_time(tmp_path, monkeypatch):
    _settled(monkeypatch)
    loader, calls = _counting(bot_builder._yaml)
    missing = tmp_path / "absent.yaml"
    assert profile_yaml_cache.load(missing, loader) == {}
    assert profile_yaml_cache.load(missing, loader) == {}
    assert len(calls) == 2

    real = tmp_path / "real.yaml"
    real.write_text("a: 1\n")
    link = tmp_path / "link.yaml"
    link.symlink_to(real)
    for _ in range(2):
        with pytest.raises(PermissionError):
            profile_yaml_cache.load(link, loader)

    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a list\n")
    for _ in range(2):
        with pytest.raises(ValueError):
            profile_yaml_cache.load(bad, loader)
    assert len(calls) == 6
    assert not profile_yaml_cache._ENTRIES


def test_loaders_do_not_share_entries(tmp_path, monkeypatch):
    _settled(monkeypatch)
    path = tmp_path / "profile.yaml"
    path.write_text("a: 1\n")
    assert profile_yaml_cache.load(path, lambda p: "one") == "one"
    assert profile_yaml_cache.load(path, bot_builder._yaml) == {"a": 1}


def _bot(tmp_path, monkeypatch, name="helper", extra=""):
    monkeypatch.setattr(profiles, "_DEFAULT_HERMES_HOME", tmp_path)
    home = tmp_path / "profiles" / name
    home.mkdir(parents=True)
    path = home / "profile.yaml"
    path.write_text(
        "synpulse_builder:\n  owner_email: a@example.com\n  skills: [one, two]\n" + extra
    )
    return path


def test_managed_returns_a_private_copy_and_validates_every_call(tmp_path, monkeypatch):
    _settled(monkeypatch)
    path = _bot(tmp_path, monkeypatch)
    first = bot_builder.managed("helper")
    first["skills"].append("injected")
    first["owner_email"] = "someone@else.example"
    second = bot_builder.managed("helper")
    assert second == {"owner_email": "a@example.com", "skills": ["one", "two"]}

    path.write_text("synpulse_builder:\n  owner_email: a@example.com\n  updating: true\n")
    with pytest.raises(PermissionError):
        bot_builder.managed("helper")
    with pytest.raises(PermissionError):
        bot_builder.managed("helper")

    path.write_text("synpulse_builder:\n  skills: []\n")
    with pytest.raises(PermissionError):
        bot_builder.managed("helper")

    path.write_text("other: 1\n")
    assert bot_builder.managed("helper") is None


def test_read_profile_hands_out_copies_and_follows_edits(tmp_path, monkeypatch):
    _settled(monkeypatch)
    path = _bot(
        tmp_path, monkeypatch,
        extra="ui_meta:\n  hermes-bots:\n    title: Helper\n    knowledge_sources:\n      - {name: handbook}\n",
    )
    monkeypatch.setattr(bot_metadata, "_path", lambda name: path)
    monkeypatch.setattr(bot_metadata, "configuration_summary", lambda home: {})
    first = bot_metadata.read_profile("helper")
    assert first["bot"]["title"] == "Helper"
    first["bot_knowledge_sources"].append({"name": "injected"})
    second = bot_metadata.read_profile("helper")
    assert second["bot_knowledge_sources"] == [{"name": "handbook"}]

    path.write_text(path.read_text().replace("title: Helper", "title: Renamed helper"))
    assert bot_metadata.read_profile("helper")["bot"]["title"] == "Renamed helper"
