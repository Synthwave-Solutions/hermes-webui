"""Keep fresh skill change detection without repeatedly resolving every ancestor."""
import os

from api import streaming


def test_symlinked_snapshot_has_bounded_path_resolution(tmp_path, monkeypatch):
    profile = tmp_path / 'profile'
    skills = profile / 'skills'
    skills.mkdir(parents=True)
    external = tmp_path / 'external'
    expected = set()
    for i in range(30):
        folder = external / str(i) / 'nested' / 'skill'
        folder.mkdir(parents=True)
        (folder / 'SKILL.md').write_text(str(i))
        expected.add(f'linked/{i}/nested/skill/SKILL.md')
    (skills / 'linked').symlink_to(external, target_is_directory=True)
    (external / 'cycle').symlink_to(skills, target_is_directory=True)
    calls = 0
    original = os.lstat

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(os, 'lstat', counted)
    before = streaming._persistent_state_snapshot(str(profile))
    assert set(before['skills']) == expected
    # A scan must not resolve all ancestors again for every nested directory.
    assert calls < 200
    (external / '0' / 'nested' / 'skill' / 'SKILL.md').write_text('updated skill')
    after = streaming._persistent_state_snapshot(str(profile))
    assert after['skills']['linked/0/nested/skill/SKILL.md'] != before['skills']['linked/0/nested/skill/SKILL.md']


def test_snapshot_fallback_without_inode_keeps_distinct_directories(tmp_path, monkeypatch):
    from types import SimpleNamespace
    skills = tmp_path / 'skills'
    for name in ('a', 'b'):
        (skills / name).mkdir(parents=True)
        (skills / name / 'SKILL.md').write_text(name)
    original = os.stat

    def no_directory_inode(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        # Files retain real signatures; emulate a filesystem without directory IDs.
        import stat
        if stat.S_ISDIR(result.st_mode):
            return SimpleNamespace(st_ino=0, st_dev=result.st_dev, st_mode=result.st_mode)
        return result

    monkeypatch.setattr(os, 'stat', no_directory_inode)
    assert set(streaming._persistent_state_snapshot(str(tmp_path))['skills']) == {'a/SKILL.md', 'b/SKILL.md'}
