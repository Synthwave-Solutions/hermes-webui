const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const src=fs.readFileSync(require('node:path').join(__dirname,'../static/bot-screens.js'),'utf8');
function paint(state,connected=false,busy=false){
  const nodes={};
  const context={state,connected,busy,bot:'reviewer',rfb:{viewOnly:true},
    $:id=>nodes[id]||(nodes[id]={dataset:{}}),
    w:()=>({controlMode:'control',privateMode:'private',viewMode:'view',idleMode:'idle'}),
    document:{body:{classList:{toggle(){}}}}};
  vm.runInNewContext(src.slice(src.indexOf('function paint(){'),src.indexOf('async function refresh()'))+'\npaint();',context);
  return {nodes,rfb:context.rfb};
}
test('stopped screen offers start, without unavailable takeover or admin controls',()=>{
  const {nodes}=paint({running:false,can_start:true,rights:{control:true}});
  assert.equal(nodes.start.hidden,false);assert.equal(nodes.start.disabled,false);
  assert.equal(nodes.takeover.hidden,true);assert.equal(nodes.release.hidden,true);
  assert.equal(nodes.stop.hidden,true);assert.equal(nodes.fullscreen.hidden,true);
});
test('viewers cannot take control and connected operators can',()=>{
  let view=paint({running:true,rights:{}},true);
  assert.equal(view.nodes.takeover.hidden,true);assert.equal(view.rfb.viewOnly,true);
  view=paint({running:true,rights:{control:true}},true);
  assert.equal(view.nodes.takeover.hidden,false);assert.equal(view.nodes.takeover.disabled,false);
  assert.equal(view.nodes.start.hidden,true);assert.equal(view.nodes.fullscreen.hidden,false);
});
test('private takeover makes hand-back primary and prevents changing bots',()=>{
  const {nodes,rfb}=paint({running:true,mine:true,holder:'human',rights:{control:true,admin:true}},true);
  assert.equal(nodes.release.hidden,false);assert.equal(nodes.release.disabled,false);
  assert.equal(nodes.takeover.hidden,true);assert.equal(nodes.bot.disabled,true);
  assert.equal(nodes.stop.disabled,true);assert.equal(rfb.viewOnly,false);
  assert.equal(nodes.modeBadge.dataset.mode,'control');
});
test('another private holder stays shielded, with recovery only for administrators',()=>{
  for(const admin of [false,true]){
    const {nodes,rfb}=paint({running:true,private:true,holder:'human',rights:{control:true,admin}});
    assert.equal(nodes.takeover.hidden,true);assert.equal(nodes.release.hidden,true);
    assert.equal(nodes.reconnect.disabled,true);assert.equal(nodes.recover.hidden,!admin);
    assert.equal(nodes.empty.hidden,false);assert.equal(rfb.viewOnly,true);
  }
});
test('busy action prevents duplicate starts',()=>{
  const {nodes}=paint({running:false,can_start:true,rights:{control:true}},false,true);
  assert.equal(nodes.start.disabled,true);assert.equal(nodes.bot.disabled,true);
});
