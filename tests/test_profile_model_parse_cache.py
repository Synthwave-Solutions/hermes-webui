"""Profile picker reuses parsed configs while respecting edits and isolation."""
import sys
import types
import re
import yaml
from api import profiles


def test_profile_rows_parse_unchanged_config_once(monkeypatch, tmp_path):
    upstream = types.ModuleType('hermes_cli.profiles')
    upstream._get_default_hermes_home = lambda: tmp_path
    upstream._get_profiles_root = lambda: tmp_path / 'profiles'
    upstream._PROFILE_ID_RE = re.compile(r'.+')
    upstream._check_gateway_running = lambda home: False
    # Baseline upstream reader deliberately mirrors its uncached YAML behavior.
    def read_model(home):
        value = yaml.safe_load((home / 'config.yaml').read_text()).get('model', {})
        return value.get('default'), value.get('provider')
    upstream._read_config_model = read_model
    monkeypatch.setitem(sys.modules, 'hermes_cli.profiles', upstream)
    path = tmp_path / 'config.yaml'
    path.write_text('model:\n  default: first\n  provider: custom\n')
    loads = []
    original = yaml.safe_load
    def counted(value):
        loads.append(1)
        return original(value)
    monkeypatch.setattr(yaml, 'safe_load', counted)
    def row(home=tmp_path):
        return profiles._build_profile_rows_fast(
            isolated=(home, 'example'), include_skill_counts=False)[0]
    assert row()['model'] == 'first'
    assert row()['provider'] == 'custom'
    assert len(loads) == 1
    path.write_text('model:\n  default: changed-model\n  provider: other\n')
    assert row()['model'] == 'changed-model'
    assert len(loads) == 2
    other = tmp_path / 'other'
    other.mkdir()
    (other / 'config.yaml').write_text('model: string-model\n')
    assert row(other)['model'] == 'string-model'
    assert row(other)['provider'] is None
    assert row()['model'] == 'changed-model'
    path.unlink()
    assert row()['model'] is None
