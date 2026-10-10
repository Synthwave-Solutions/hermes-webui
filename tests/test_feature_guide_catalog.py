"""Documentation contract: both locales, grounded controls and honest availability."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def catalog(name, assignment):
    return json.loads((ROOT / 'static' / name).read_text().split(assignment + ' = ', 1)[1].strip()[:-1])


WEB = catalog('help-features.js', 'window.SynthPulseFeatureCatalog')
MSP = catalog('help-msp-features.js', 'window.SynthPulseMspFeatureCatalog')


def test_bilingual_content_contract():
    for data in (WEB, MSP):
        assert data['schema_version'] == 1
        ids = [f['id'] for f in data['features']]
        assert len(ids) == len(set(ids))
        for feature in data['features']:
            assert feature['status'] in {'available', 'conditional', 'planned'}
            assert feature['source_refs'] and feature['anchors']
            assert set(feature['locales']) == {'en', 'nl'}
            for lang, text in feature['locales'].items():
                assert set(text) == {'title', 'purpose', 'when', 'steps', 'permissions', 'limits', 'example'}
                assert all(text.values()), (feature['id'], lang)
                assert isinstance(text['steps'], list) and text['steps']
                assert all(isinstance(step, str) and step.strip() for step in text['steps'])
            assert feature['locales']['en']['purpose'] != feature['locales']['nl']['purpose']
            assert all(related in ids for related in feature['related'])


def test_every_inventoried_control_has_a_grounded_feature():
    coverage = json.loads((ROOT / 'docs/feature-guide-coverage.json').read_text())
    ids = {f['id'] for f in WEB['features']}
    assert {f['id'] for f in coverage['features']} == ids
    assert len(coverage['controls']) >= 488
    mapped = {c['control']: c['feature_id'] for c in coverage['controls']}
    # Parse actual current controls, not just a fixed expected catalog count.
    for path in [ROOT / 'static/index.html', *sorted((ROOT / 'static').glob('*.js'))]:
        if path.name.startswith(('help-', 'i18n')):
            continue
        for tag in re.findall(r'<(?:button|input|select|textarea|a)\b[^>]*>', path.read_text()):
            attrs = dict(re.findall(r'([\w-]+)\s*=\s*[\"\']([^\"\']*)[\"\']', tag))
            control = attrs.get('id', '')
            if not re.fullmatch(r'[A-Za-z][\w-]*', control):
                handler = attrs.get('onclick') or attrs.get('onchange') or ''
                found = re.match(r'\s*([\w.]+)\(', handler)
                control = 'action:' + found[1] if found else ''
            # This literal is an example in the picker module's documentation comment.
            if path.name == 'sp-picker.js' and control == 'x':
                continue
            if control:
                assert control in mapped or control == 'helpCardGuide', (path.name, control)
                if control in mapped:
                    assert mapped[control] in ids
    for feature in WEB['features']:
        for ref in feature['source_refs']:
            assert (ROOT / ref.split(':')[0]).is_file(), (feature['id'], ref)
        for text in feature['locales'].values():
            values = [*text.values()]
            for value in values:
                for s in value if isinstance(value, list) else [value]:
                    assert not re.search(r'<[a-zA-Z/]|[\u2013\u2014]', s), feature['id']
                    assert '/home/' not in s and 'synthwavehq.tail' not in s


def test_sensitive_and_prepared_capabilities_do_not_claim_unconditional_access():
    entries = {f['id']: f for f in WEB['features']}
    for id_ in ('webui.memory.explorer', 'webui.memory.audit', 'webui.voice.realtime',
                'webui.planned.gateway', 'webui.planned.reporter'):
        assert entries[id_]['status'] == 'conditional'
        assert entries[id_]['conditions']
    assert entries['webui.planned.central_memory']['status'] == 'planned'
    for lang, required in [('en', 'owner-only'), ('nl', 'alleen voor de eigenaar')]:
        assert required in entries['webui.memory.explorer']['locales'][lang]['limits']
    assert 'does not stop execution' in entries['webui.tasks.notify']['locales']['en']['limits']


def test_all_current_composer_commands_are_documented():
    coverage = json.loads((ROOT / 'docs/feature-guide-coverage.json').read_text())
    source = (ROOT / 'static/commands.js').read_text().split('const SLASH_SUBARG_SOURCES', 1)[0]
    commands = set(re.findall(r"name:'([^']+)'", source))
    assert set(coverage['commands']) == commands
    entries = {f['id']: f for f in WEB['features']}
    for command, feature_id in coverage['commands'].items():
        for lang in ('en', 'nl'):
            assert any('/' + command + '.' in step for step in entries[feature_id]['locales'][lang]['steps'])
