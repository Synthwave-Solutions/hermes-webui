const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const context={window:{addEventListener(){}},document:{readyState:'loading',getElementById(){return null;},addEventListener(){}},S:{}};
vm.runInNewContext(fs.readFileSync('static/chat-bots.js','utf8'),context);
const {available,address}=context.window.chatBotRecipientRules;
const rows=[{name:'writer'},{name:'reviewer'},{name:'private',visible:false}];
assert.equal(available(rows,{bot_participants:['reviewer','unknown']}).map(x=>x.name).join(','),'reviewer');
assert.equal(available(rows,{}).map(x=>x.name).join(','),'writer,reviewer');
assert.equal(address('Review invoice','reviewer'),'@reviewer Review invoice');
assert.equal(address('@writer Review invoice','reviewer'),'@reviewer Review invoice');
assert.equal(address('Email a@b.test unchanged','reviewer'),'@reviewer Email a@b.test unchanged');
assert.equal(address('','reviewer'),'@reviewer ');
console.log('Recipient filtering and literal dispatch addressing passed');

const {mentions,fold,normalizeBotAddress}=context.window.chatBotRecipientRules;
const directory=[{kind:'user',id:'alex@example.test',label:'Alex'},
  {kind:'user',id:'michael@example.test',label:'Michaël'},
  {kind:'bot',id:'alex',label:'Alex'}, {kind:'bot',id:'research',label:'Research'}];
assert.equal(fold('Michaël'),'michael');
assert.equal(mentions('Email alex@example.test',directory).length,0);
assert.equal(mentions('@alex@example.test @michael@example.test @alex @research @alex',directory).length,4);
assert.equal(mentions('@alex@example.test @alex',directory).map(row=>row.kind).join(','),'user,bot');
assert.equal(mentions('@unknown @research-old',directory).length,0);
assert.equal(normalizeBotAddress('Compare @research-old then ask @research',directory),'@research Compare @research-old then ask ');
assert.equal(normalizeBotAddress('@alex@example.test ask @research and @alex',directory),'@research @alex@example.test ask  and @alex');
assert.equal(normalizeBotAddress('@research Keep  exact spacing',directory),'@research Keep  exact spacing');
assert.equal(normalizeBotAddress('No bot here',directory),'No bot here');
console.log('Unified mentions, same-name identities, first bot and prefix-safe normalization passed');

assert.equal(normalizeBotAddress('@RESEARCH Keep casing elsewhere',directory),'@research Keep casing elsewhere');

assert.equal(normalizeBotAddress('@research, please review',directory),'@research , please review');
assert.equal(normalizeBotAddress('@research. Please review',directory),'@research . Please review');
assert.equal(normalizeBotAddress('Ask @research. Please review',directory),'@research Ask . Please review');
