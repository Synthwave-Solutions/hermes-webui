import json
from pathlib import Path
import subprocess


def test_pending_view_uses_only_self_route_and_escapes_request_content():
    source = (Path(__file__).resolve().parents[1] / 'static/panels.js').read_text()
    start = source.index('async function loadMyAccessRequests(')
    end = source.index('window.loadMyAccessRequests=', start)
    script = r'''
const vm=require('vm');
const calls=[];
const box={innerHTML:''};
const button={disabled:false};
const ctx={
  $:id=>id==='myApprovalsList'?box:button,
  api:async path=>{calls.push(path);return {requests:[
    {status:'pending',label:'<script>owned</script>',kind:'tool',requested_at:1},
    {status:'approved',label:'Already approved',kind:'tool',requested_at:2}
  ]};},
  t:key=>key,
  esc:value=>String(value).replace(/</g,'&lt;').replace(/>/g,'&gt;'),
  _accessStatusPill:status=>status,
  _accessKindLabel:kind=>kind,
  _accessWhen:when=>String(when),
  _accessNextAction:status=>status,
  approvalResumeHtml:()=>{throw Error('pending list must not load a session control');}
};
vm.createContext(ctx);
vm.runInContext(SOURCE,ctx);
(async()=>{
 await ctx.loadMyAccessRequests(true,{pendingOnly:true});
 console.log(JSON.stringify({calls,html:box.innerHTML,disabled:button.disabled}));
})();
'''.replace('SOURCE', json.dumps(source[start:end]))
    result = subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    assert data['calls'] == ['/api/governance/approvals/mine']
    assert '&lt;script&gt;owned&lt;/script&gt;' in data['html']
    assert '<script>' not in data['html']
    assert 'Already approved' not in data['html']
    assert data['disabled'] is False


def test_background_diagnostics_wait_for_access_and_skip_denied_routes():
    source = (Path(__file__).resolve().parents[1] / 'static/ui.js').read_text()
    boundaries = [
        ('async function refreshDashboardStatus(', 'async function loadDashboardSettings('),
        ('async function loadDashboardSettings(', 'async function saveDashboardSettings('),
        ('async function pollAgentHealth(', 'function startAgentHealthMonitor('),
    ]
    functions = '\n'.join(source[source.index(start):source.index(end, source.index(start))]
                          for start, end in boundaries)
    script = r'''
const vm=require('vm');
const accesses=[];
let ready=false;
const ctx={
 loadGovernanceNavVisibility:async()=>{ready=true;},
 _canUseFeature:permission=>{if(!ready)throw Error('access not loaded');accesses.push(permission);return false;},
 api:()=>{throw Error('denied diagnostic must not call the API');}
};
vm.createContext(ctx);vm.runInContext(SOURCE,ctx);
(async()=>{await ctx.refreshDashboardStatus();await ctx.loadDashboardSettings();await ctx.pollAgentHealth();console.log(JSON.stringify(accesses));})();
'''.replace('SOURCE', json.dumps(functions))
    result = subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == ['dashboard:read', 'dashboard:read', 'status:read']
