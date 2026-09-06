import pathlib
import subprocess


def test_both_enable_entrypoints_collect_credentials_and_cancel():
    root = pathlib.Path(__file__).resolve().parent.parent
    script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const ctx = { console, setTimeout, clearTimeout, setInterval, clearInterval,
  document: {addEventListener() {}}, window: {addEventListener() {}} };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('static/integrations.js', 'utf8'), ctx);
vm.runInContext(fs.readFileSync('static/governance.js', 'utf8'), ctx);
vm.runInContext(`
let posts = [], prompts = 0, cancel = false, configured = false;
api = async (url, options) => {
  if (url.endsWith('/catalog')) return {providers:[{key:'notion', unique_key:configured ? 'notion' : null, configured, credential_fields:['client_id','client_secret']}]};
  posts.push(JSON.parse(options.body)); return {status:'enabled'};
};
_intgCredentialDialog = async () => { prompts++; return cancel ? null : {client_id:'test',client_secret:'fixture'}; };
loadIntegrations = () => {};
_govLoadIntegrations = async () => {};
_govRefreshApprovalsBadge = () => {};
_govPost = async (url, body) => { posts.push(body); };
_govHandleConflict = () => false;
`, ctx);
(async () => {
  await vm.runInContext('_intgEnable("notion")', ctx);
  await vm.runInContext('_govIntgAction("enable", "notion")', ctx);
  assert.equal(vm.runInContext('posts.length',ctx),2);
  assert.equal(vm.runInContext('posts.every(p => p.credentials.client_secret === "fixture")',ctx),true);
  vm.runInContext('cancel = true',ctx);
  await vm.runInContext('_intgEnable("notion")',ctx);
  await vm.runInContext('_govIntgAction("enable", "notion")',ctx);
  assert.equal(vm.runInContext('posts.length',ctx),2);
  vm.runInContext('configured = true',ctx);
  await vm.runInContext('_intgEnable("notion")',ctx);
  assert.equal(vm.runInContext('posts.length',ctx),3);
  assert.equal(vm.runInContext('posts[2].credentials',ctx),undefined);
})().catch(e => { console.error(e); process.exit(1); });
'''
    result = subprocess.run(['node', '-e', script], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
