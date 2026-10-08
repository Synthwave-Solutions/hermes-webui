"""Large router catalogs preserve defaults and declaration order when deduplicated."""
import pytest
import api.config as cfg
from tests.test_issue3928_models_budget_fallback import isolate_models_catalog_state


@pytest.mark.parametrize('shape', ['strings', 'objects', 'mapping'])
def test_large_static_custom_catalog_order(monkeypatch, isolate_models_catalog_state, shape):
    ids = [f'vendor/model-{i}' for i in range(6000)]
    if shape == 'strings':
        models = ids + ids
    elif shape == 'objects':
        models = [{'id': value} for value in ids] + [{'name': value} for value in ids]
    else:
        models = dict.fromkeys(ids, {})
    monkeypatch.setattr(cfg, 'cfg', {
        'model': {'provider': 'custom:local', 'default': ids[0]},
        'custom_providers': [{'name': 'Local', 'model': ids[0], 'models': models}],
    })
    result = cfg._static_models_catalog_without_live_probes()
    group = next(g for g in result['groups'] if g['provider_id'] == 'custom:local')
    actual = [m['id'].removeprefix('@custom:local:') for m in group['models']]
    assert actual == ids
