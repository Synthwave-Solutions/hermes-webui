const assert=require('node:assert/strict');
const dock={hidden:true,innerHTML:''};
global.document={hidden:false,getElementById:()=>dock};
global.SynPulseFriendlyTools={text:k=>k,statusChipHtml:()=>'',lang:()=> 'en'};
global.api=async()=>({subagents:[{id:'bot:1',bot_title:'Proposal <Bot>',bot_profile:'proposals',task:'Draft proposal',status:'completed',child_session_id:'child123',steps:[]}]});
const ui=require('../static/subagent-threads.js');
ui._switchTo('parent');
setImmediate(()=>{
 assert.equal(dock.hidden,false);
 assert.match(dock.innerHTML,/Proposal &lt;Bot&gt;/);
 assert.match(dock.innerHTML,/data-sp-subagent-profile="proposals"/);
 assert.match(dock.innerHTML,/data-sp-subagent-open="child123"/);
 assert.match(dock.innerHTML,/Draft proposal/);
 assert.match(dock.innerHTML,/data-state="done"/);
 console.log('Named bot cards escape titles and preserve child profile navigation.');
});
