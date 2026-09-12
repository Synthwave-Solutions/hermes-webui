"""Provider docs must stay safe across setup-guide and ordinary Docs fallbacks."""
import pathlib
import subprocess

import pytest

from api import integrations


@pytest.mark.parametrize("unsafe", [
    "javascript:alert(1)", "data:text/html,fixture", "file:///tmp/guide",
    "//example.test/guide", "https://user:password@example.test/guide",
    "https://user@example.test/guide", "http://example.test:bad/guide",
])
def test_catalog_filters_unsafe_docs_and_setup_guides(unsafe):
    item = integrations._catalog_item("fixture-mcp", {
        "auth_mode": "MCP_OAUTH2", "docs": unsafe, "setup_guide_url": unsafe,
    })
    assert item["docs"] == ""
    assert item["setup_guide_url"] == ""


def test_rendered_docs_fallback_and_setup_links_validate_urls_for_admin_and_member():
    root = pathlib.Path(__file__).resolve().parents[1]
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const grid={innerHTML:''};
const context=vm.createContext({URL,console,document:{addEventListener(){}},window:{addEventListener(){}},
  $:id=>id==='intgGrid'?grid:null});
vm.runInContext(fs.readFileSync('static/integrations.js','utf8'),context);
vm.runInContext('_intgConnections=[];_intgRequests=[];',context);
function render(role,overrides){
 context.provider={key:'fixture-mcp',display_name:'Fixture provider',auth_mode:'MCP_OAUTH2',
  configured:false,approval:'none',setup_required:true,...overrides};
 context.role=role;
 vm.runInContext('_intgMe={roles:[role]};_intgCatalog={providers:[provider]};_intgRenderGrid();',context);
 return [...grid.innerHTML.matchAll(/<a\b[^>]*href="([^"]*)"[^>]*>([^<]*)<\/a>/g)].map(m=>({href:m[1],label:m[2]}));
}
for(const unsafe of ['javascript:alert(1)','data:text/html,fixture','file:///tmp/guide','//example.test/guide',
 'https://user:password@example.test/guide','https://user@example.test/guide','http://example.test:bad/guide']){
 for(const role of ['admin','member']){
  assert.deepEqual(render(role,{docs:unsafe,setup_guide_url:''}),[],`unsafe Docs fallback for ${role}`);
  assert.deepEqual(render(role,{docs:unsafe,setup_guide_url:unsafe}),[],`unsafe setup guide for ${role}`);
  assert.deepEqual(render(role,{configured:true,unique_key:'fixture-work',docs:unsafe,setup_guide_url:unsafe}),[]);
 }
}
const docs='https://example.test/docs?view=oauth',guide='http://example.test/setup';
assert.deepEqual(render('admin',{docs,setup_guide_url:guide}),[{href:guide,label:'Setup guide'}]);
assert.deepEqual(render('member',{docs,setup_guide_url:guide}),[{href:docs,label:'Docs'}]);
assert.deepEqual(render('admin',{docs,setup_guide_url:'javascript:alert(1)'}),[{href:docs,label:'Docs'}]);
assert.deepEqual(render('admin',{configured:true,unique_key:'fixture-work',docs,setup_guide_url:guide}),[{href:guide,label:'Setup guide'}]);
assert.deepEqual(render('member',{configured:true,unique_key:'fixture-work',docs,setup_guide_url:guide}),[]);
"""
    result = subprocess.run(["node", "-e", script], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
