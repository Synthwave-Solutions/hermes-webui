"""The remembered skill tree walk must give exactly what a fresh walk gives."""
import os
import time
from pathlib import Path

import pytest

from api import streaming


def _reference_skills(profile_home):
    """The skill scan as it was before the walk was remembered."""
    skills = {}
    skills_dir = Path(profile_home) / "skills"
    seen_dirs = set()
    budget = streaming._PERSISTENT_SKILL_SCAN_CAP
    for current, dirs, files in os.walk(skills_dir, followlinks=True):
        try:
            st = os.stat(current)
            real = (st.st_dev, st.st_ino) if st.st_ino else os.path.realpath(current)
        except OSError:
            dirs[:] = []
            continue
        if real in seen_dirs:
            dirs[:] = []
            continue
        seen_dirs.add(real)
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        budget -= 1
        if budget <= 0:
            break
        if "SKILL.md" not in files:
            continue
        skill_md = Path(current) / "SKILL.md"
        rel = os.path.relpath(skill_md, skills_dir).replace("\\", "/")
        sig = streaming._file_signature(skill_md)
        if sig is not None:
            skills[rel] = sig
    return skills


def _tick():
    # Directory timestamps come from a coarse kernel clock: keep two steps apart.
    time.sleep(0.05)


def _skill(folder, text="skill"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(text)


@pytest.fixture
def tree(tmp_path, monkeypatch):
    streaming._SKILL_WALK_MEMO.clear()
    monkeypatch.delenv("HERMES_WEBUI_SKILL_WALK_MEMO", raising=False)
    # Fresh test trees are younger than the racy window: remember them anyway.
    monkeypatch.setattr(streaming, "_SKILL_WALK_RACY_NS", -10**15)
    profile = tmp_path / "profile"
    skills = profile / "skills"
    _skill(skills / "writing" / "blog")
    _skill(skills / "writing" / "mail")
    _skill(skills / "ops" / "deploy" / "rollback")
    (skills / "ops" / "notes").mkdir()
    (skills / "ops" / "notes" / "README.md").write_text("no skill here")
    _skill(skills / ".hidden" / "secret")
    external = tmp_path / "external"
    _skill(external / "shared" / "one")
    _skill(external / "shared" / "two")
    (skills / "linked").symlink_to(external, target_is_directory=True)
    (external / "cycle").symlink_to(skills, target_is_directory=True)
    _tick()
    yield profile, skills, external
    streaming._SKILL_WALK_MEMO.clear()


@pytest.fixture
def walks(monkeypatch):
    counter = {"n": 0}
    original = os.walk

    def counted(*args, **kwargs):
        counter["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(os, "walk", counted)
    return counter


def _snapshot(profile):
    return streaming._persistent_state_snapshot(str(profile))["skills"]


def _same_as_reference(profile):
    got = _snapshot(profile)
    expected = _reference_skills(profile)
    assert got == expected
    assert list(got) == list(expected)  # same order
    return got


def test_first_and_repeated_snapshot_match_a_fresh_walk(tree):
    profile, _skills, _external = tree
    first = _same_as_reference(profile)
    assert set(first) == {
        "writing/blog/SKILL.md", "writing/mail/SKILL.md", "ops/deploy/rollback/SKILL.md",
        "linked/shared/one/SKILL.md", "linked/shared/two/SKILL.md",
    }
    assert _same_as_reference(profile) == first


def test_unchanged_tree_is_not_walked_again(tree, walks):
    profile, _skills, _external = tree
    first = _snapshot(profile)
    assert walks["n"] == 1
    assert _snapshot(profile) == first
    assert _snapshot(profile) == first
    assert walks["n"] == 1


def test_every_kind_of_change_is_seen(tree, walks):
    profile, skills, external = tree
    _same_as_reference(profile)

    steps = [
        lambda: _skill(skills / "writing" / "report"),                           # new skill
        lambda: (skills / "writing" / "mail" / "SKILL.md").unlink(),             # skill file removed
        lambda: _skill(skills / "new-category" / "deep" / "deeper" / "skill"),   # new nested category
        lambda: (skills / "writing" / "blog").rename(skills / "writing" / "blogging"),  # renamed
        lambda: _skill(external / "shared" / "three"),                           # behind a symlink
        lambda: (skills / "ops" / "notes" / "SKILL.md").write_text("now a skill"),  # existing directory
        lambda: _skill(skills / ".hidden" / "another"),                          # hidden: stays invisible
        lambda: (skills / "linked").unlink(),                                    # symlink removed
        lambda: (skills / "again").symlink_to(external / "shared", target_is_directory=True),
    ]
    for step in steps:
        _tick()
        step()
        _same_as_reference(profile)
        _same_as_reference(profile)  # and once more from memory


def test_edited_skill_file_is_seen_without_a_new_walk(tree, walks):
    profile, skills, _external = tree
    before = _snapshot(profile)
    assert walks["n"] == 1
    (skills / "writing" / "blog" / "SKILL.md").write_text("a much longer skill text")
    after = _snapshot(profile)
    assert walks["n"] == 1
    assert after["writing/blog/SKILL.md"] != before["writing/blog/SKILL.md"]
    assert after == _reference_skills(profile)


def test_fresh_tree_is_not_remembered_with_the_default_window(tree, walks, monkeypatch):
    profile, _skills, _external = tree
    monkeypatch.setattr(streaming, "_SKILL_WALK_RACY_NS", 2_000_000_000)
    _snapshot(profile)
    _snapshot(profile)
    assert walks["n"] == 2
    assert not streaming._SKILL_WALK_MEMO


def test_change_during_the_window_drops_what_was_remembered(tree, walks, monkeypatch):
    profile, skills, _external = tree
    _snapshot(profile)
    assert len(streaming._SKILL_WALK_MEMO) == 1
    monkeypatch.setattr(streaming, "_SKILL_WALK_RACY_NS", 2_000_000_000)
    _tick()
    _skill(skills / "writing" / "fresh")
    assert "writing/fresh/SKILL.md" in _snapshot(profile)
    assert not streaming._SKILL_WALK_MEMO


def test_switch_off(tree, walks, monkeypatch):
    profile, _skills, _external = tree
    monkeypatch.setenv("HERMES_WEBUI_SKILL_WALK_MEMO", "0")
    _same_as_reference(profile)
    _same_as_reference(profile)
    assert not streaming._SKILL_WALK_MEMO


def test_capped_walk_is_not_remembered(tree, walks, monkeypatch):
    profile, _skills, _external = tree
    monkeypatch.setattr(streaming, "_PERSISTENT_SKILL_SCAN_CAP", 3)
    _same_as_reference(profile)
    _same_as_reference(profile)
    assert not streaming._SKILL_WALK_MEMO


def test_old_memory_is_walked_again(tree, walks, monkeypatch):
    profile, _skills, _external = tree
    monkeypatch.setattr(streaming, "_SKILL_WALK_MEMO_MAX_AGE_SECONDS", 0.0)
    _snapshot(profile)
    _snapshot(profile)
    assert walks["n"] == 2


def test_number_of_remembered_trees_is_bounded(tmp_path, monkeypatch):
    streaming._SKILL_WALK_MEMO.clear()
    monkeypatch.setattr(streaming, "_SKILL_WALK_RACY_NS", -10**15)
    monkeypatch.setattr(streaming, "_SKILL_WALK_MEMO_MAX_TREES", 2)
    profiles = []
    for name in ("a", "b", "c"):
        _skill(tmp_path / name / "skills" / "one")
        profiles.append(tmp_path / name)
    for profile in profiles:
        assert set(_snapshot(profile)) == {"one/SKILL.md"}
    assert len(streaming._SKILL_WALK_MEMO) == 2
    for profile in profiles:
        assert _snapshot(profile) == _reference_skills(profile)
    streaming._SKILL_WALK_MEMO.clear()


def test_profiles_do_not_share_a_tree(tmp_path, monkeypatch):
    streaming._SKILL_WALK_MEMO.clear()
    monkeypatch.setattr(streaming, "_SKILL_WALK_RACY_NS", -10**15)
    _skill(tmp_path / "a" / "skills" / "alpha")
    _skill(tmp_path / "b" / "skills" / "beta")
    assert set(_snapshot(tmp_path / "a")) == {"alpha/SKILL.md"}
    assert set(_snapshot(tmp_path / "b")) == {"beta/SKILL.md"}
    assert set(_snapshot(tmp_path / "a")) == {"alpha/SKILL.md"}
    streaming._SKILL_WALK_MEMO.clear()


def test_removed_and_recreated_tree(tree, walks):
    profile, skills, _external = tree
    _snapshot(profile)
    import shutil

    _tick()
    shutil.rmtree(skills)
    assert _snapshot(profile) == {}
    _tick()
    _skill(skills / "only")
    assert _same_as_reference(profile) == _snapshot(profile)
    assert set(_snapshot(profile)) == {"only/SKILL.md"}


def test_missing_profile_and_missing_skills_directory(tmp_path):
    streaming._SKILL_WALK_MEMO.clear()
    assert streaming._persistent_state_snapshot(None) == {"memory": {}, "skills": {}}
    assert streaming._persistent_state_snapshot(str(tmp_path / "nowhere"))["skills"] == {}
    assert not streaming._SKILL_WALK_MEMO
