import json
from pathlib import Path
import subprocess


def test_advanced_controls_default_quiet_and_persist_per_signed_in_person():
    source=(Path(__file__).resolve().parents[1]/'static/panels.js').read_text()
    source=source[source.index('function _advancedChatPreferenceKey('):source.index('function _applyNavigationAudience(')]
    script=r'''
const vm=require('vm');
const values=new Map(),checkbox={};
const ctx={document:{documentElement:{dataset:{}}},window:{__GOV_ME__:{email:'alice@example.test'}},
 $:()=>checkbox,localStorage:{setItem:(k,v)=>values.set(k,v),getItem:k=>values.get(k)}};
vm.createContext(ctx);vm.runInContext(SOURCE,ctx);
ctx.restoreAdvancedChatControls();
const fresh=ctx.document.documentElement.dataset.advancedChatControls;
ctx.setAdvancedChatControls(true);
ctx.restoreAdvancedChatControls();
const optedIn=ctx.document.documentElement.dataset.advancedChatControls;
ctx.window.__GOV_ME__.email='bob@example.test';ctx.restoreAdvancedChatControls();
const otherUser=ctx.document.documentElement.dataset.advancedChatControls;
ctx.window.__GOV_ME__.email='alice@example.test';ctx.restoreAdvancedChatControls();
console.log(JSON.stringify({fresh,optedIn,otherUser,restored:checkbox.checked}));
'''.replace('SOURCE',json.dumps(source))
    result=subprocess.run(['node','-e',script],check=True,capture_output=True,text=True)
    assert json.loads(result.stdout)=={'fresh':'0','optedIn':'1','otherUser':'0','restored':True}
