import json
from pathlib import Path
from api.org_modules import CATALOG
from api.modules import DISPLAY_DENYLIST, UNAVAILABLE_REASONS

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'static/module-content.js').read_text().split(' = ',1)[1].strip().removesuffix(';'))
CAT=json.loads((ROOT/'tests/fixtures/managed_service/module_catalog.json').read_text())


def test_module_copy_matches_pinned_public_catalogue():
    for locale in ('en','nl'):
        assert set(DATA['locales'][locale]['modules'])=={r['id'] for r in CAT['modules']}
        for row in CAT['modules']:
            assert DATA['locales'][locale]['modules'][row['id']]=={k:row[k][locale] for k in ('name','summary')}
            assert CATALOG[row['id']]=={k:row[k] for k in CATALOG[row['id']]}
        assert set(DATA['locales'][locale]['ui']['reasons'])==set(UNAVAILABLE_REASONS)
        copy=json.dumps(DATA['locales'][locale],ensure_ascii=False)
        assert '\u2013' not in copy and '\u2014' not in copy
        assert all(word.lower() not in copy.lower() for word in DISPLAY_DENYLIST)
    assert DATA['locales']['nl']['ui'].keys()==DATA['locales']['en']['ui'].keys()
