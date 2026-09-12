"""The live row must use the latest deferred body when it is opened."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


@pytest.mark.skipif(not NODE, reason="node unavailable")
@pytest.mark.parametrize("mode", ["replacement", "clear", "null"])
@pytest.mark.parametrize("expanded", [True, False])
def test_rehydration_replaces_stale_deferred_snapshot_before_open(mode, expanded):
    source = (ROOT / "static/ui.js").read_text()
    begin = source.index("function _rehydrateTransparentLiveRow(")
    end = source.index("\nfunction ", begin + 1)
    script = r"""
const mode = MODE;
const expanded = EXPANDED;
const stale = {name:'terminal',snippet:'',done:false};
const finished = {name:'terminal',snippet:'fixture stdout',done:true};
const activeTabs={};
const tabs = ['full','output'].map(mode=>({getAttribute:()=>mode,classList:{toggle(_name,active){activeTabs[mode]=active;}}}));
const detail = {setAttribute(){},querySelectorAll:()=>tabs};
const card = {classList:{toggle(){}}};
const existing = {_deferredToolCall:stale,_tcData:stale,
  querySelector(selector){return selector==='.tool-card-detail'?detail:selector==='.tool-card,.thinking-card'?card:null;}};
const candidate = {_tcData:finished};
if(mode==='replacement') candidate._deferredToolCall=finished;
if(mode==='null') candidate._deferredToolCall=null;
let rendered;
function _setTransparentCardOpen(_card, expanded){
  if(expanded) rendered=(existing._deferredToolCall||finished).snippet;
}
FUNCTION
_rehydrateTransparentLiveRow(existing,candidate,{expanded,detailMode:'output'});
if(!expanded) _setTransparentCardOpen(card,true);
console.log(JSON.stringify({rendered,
  outputTabPreserved:activeTabs.output===true&&activeTabs.full===false,
  staleRetained:existing._deferredToolCall===stale,
  candidateRetainsSnapshot:Object.prototype.hasOwnProperty.call(candidate,'_deferredToolCall'),
  tcIsFinished:existing._tcData===finished}));
""".replace("MODE", json.dumps(mode)).replace("EXPANDED", json.dumps(expanded)).replace("FUNCTION", source[begin:end])
    result = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    outcome = json.loads(result.stdout)
    assert outcome["rendered"] == "fixture stdout"
    assert outcome["staleRetained"] is False
    assert outcome["candidateRetainsSnapshot"] is False
    assert outcome["tcIsFinished"] is True
    assert outcome["outputTabPreserved"] is True
