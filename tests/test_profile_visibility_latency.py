from pathlib import Path
from api import profiles


def test_visibility_reuses_yaml_parse_but_tracks_changes(tmp_path, monkeypatch):
    path = tmp_path / 'profile.yaml'
    path.write_text('visible: false\n')
    real = Path.read_text
    calls = []
    def load(self, *args, **kwargs):
        if self == path: calls.append(self)
        return real(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', load)
    assert profiles._profile_visible_from_meta(tmp_path) is False
    assert profiles._profile_visible_from_meta(tmp_path) is False
    assert len(calls) == 1
    path.write_text('visible: true\n')
    assert profiles._profile_visible_from_meta(tmp_path) is True
    assert len(calls) == 2
    path.unlink()
    assert profiles._profile_visible_from_meta(tmp_path) is True


def test_visibility_keeps_explicit_boolean_contract(tmp_path):
    path = tmp_path / 'profile.yaml'
    for value, expected in [('false', False), ('"false"', True), ('null', True), ('true', True)]:
        path.write_text('visible: ' + value + '\n')
        assert profiles._profile_visible_from_meta(tmp_path) is expected
    path.write_text('broken: [')
    assert profiles._profile_visible_from_meta(tmp_path) is True
