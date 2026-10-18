"""Dutch language pack: complete, dash-free, selectable, Dutch by default for nl browsers."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_DRIVER = r"""
const fs=require('fs');const b={};global.window={__registerHermesLocale:(c,x)=>{b[c]=x;}};
const src=fs.readFileSync(process.argv[1]+'/static/i18n.js','utf8');
const helpers=src.slice(src.indexOf('function _i18nProcessedElapsed('),src.indexOf('window.__registerHermesLocale'));
eval(helpers.replace(/^const /gm,'var ')+';'+fs.readFileSync(process.argv[1]+'/static/i18n/en.js','utf8')+';'+fs.readFileSync(process.argv[1]+'/static/i18n/nl.js','utf8'));
const errs=[];for(const k in b.nl){if(typeof b.nl[k]==='function'){try{b.nl[k](2,3,'a','b','c','d','e');}catch(e){errs.push(k);}}}
process.stdout.write(JSON.stringify({en:Object.keys(b.en),nl:Object.keys(b.nl),errs,label:b.nl._label,sample:b.nl.processed_elapsed('4s')}));
"""


def test_nl_bundle_is_complete_and_valid():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required")
    out = subprocess.run([node, "-e", _DRIVER, str(ROOT)], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    assert set(data["en"]) <= set(data["nl"]), sorted(set(data["en"]) - set(data["nl"]))[:10]
    assert data["errs"] == []
    assert data["label"] == "Nederlands"
    assert data["sample"] == "Verwerkt 4s"


def test_nl_bundle_has_no_en_or_em_dashes_and_is_registered():
    text = (ROOT / "static" / "i18n" / "nl.js").read_text(encoding="utf-8")
    assert "–" not in text and "—" not in text
    i18n = (ROOT / "static" / "i18n.js").read_text(encoding="utf-8")
    assert "nl:['Nederlands','nl-NL']" in i18n
    assert "_spBrowserPrefersDutch()" in i18n and "sp-lang-explicit" in i18n
    panels = (ROOT / "static" / "panels.js").read_text(encoding="utf-8")
    assert "localStorage.setItem('sp-lang-explicit',this.value)" in panels
