const assert=require('node:assert/strict');
const ft=require('../static/tool-friendly.js');

for(const lang of ['nl','en']){
  ft.setLanguage(lang);
  const rows=[
    {name:'terminal',args:{command:'cd repo && python3 -m pytest -q'},done:true},
    {name:'read_file',args:{path:'/home/u/repo/README.md'},done:true},
    {name:'write_file',args:{path:'/srv/app/config.yaml',content:'secret: x'},done:true},
    {name:'search_files',args:{pattern:'TODO'},done:true},
    {name:'web_search',args:{query:'markdown tables'},done:true},
    {name:'browser_navigate',args:{url:'https://www.example.com/a?token=abc'},done:true},
    {name:'delegate_task',args:{tasks:"[{'goal': 'a'}, {'goal': 'b'}]"},done:true},
    {name:'opencode_task',args:{title:'Fix tests'},done:false},
    {name:'mcp__claude_ai_Gmail__search_threads',args:{},done:true},
    {name:'mcp__claude_ai_Google_Calendar__list_events',args:{},done:true},
    {name:'mcp__claude_ai_Google_Drive__read_file_content',args:{},done:true},
    {name:'memory',args:{action:'add'},done:true},
    {name:'skill_view',args:{name:'smart-scheduling'},done:true},
    {name:'process',args:{action:'poll'},done:true},
    {name:'execute_code',args:{code:'print(1)'},done:true},
    {name:'todo',args:{},done:true},
    {name:'image_generate',args:{prompt:'x'},done:true},
    {name:'some_new_tool',args:{},done:true},
  ];
  const fams=rows.map(r=>ft.describe(r).family);
  assert.deepEqual(fams,['shell','read','write','search','web','browser','delegate','opencode','mail','calendar','drive','memory','skill','process','code','todo','image','unknown']);
  const emoji=rows.map(r=>ft.describe(r).emoji);
  assert.deepEqual(emoji,['💻','📄','✏️','🔍','🌐','🧭','🤝','🧑‍💻','✉️','📅','📁','🧠','🧩','⏱️','🐍','✅','🖼️','🔧']);
  for(const r of rows){
    const d=ft.describe(r);
    // Never a raw command, a full path, a secret or file contents in the visible row.
    const visible=d.title+' '+d.target;
    assert.ok(!visible.includes('&&'),visible);
    assert.ok(!visible.includes('/home/u'),visible);
    assert.ok(!visible.includes('token=abc'),visible);
    assert.ok(!visible.includes('secret'),visible);
    assert.ok(!/[–—]/.test(visible),'no en/em dashes: '+visible);
  }
  assert.equal(ft.describe(rows[1]).target,'README.md');
  assert.equal(ft.describe(rows[5]).target,'example.com');
  assert.equal(ft.describe(rows[6]).target,'2 subagents');
}

ft.setLanguage('nl');
assert.equal(ft.describe({name:'terminal',args:{command:'git status --short'},done:true}).title,'Opdracht uitgevoerd');
assert.equal(ft.describe({name:'terminal',args:{command:'git status --short'},done:true}).target,'Wijzigingen in Git bekeken');
assert.equal(ft.describe({name:'terminal',args:{command:'ls'},done:false}).state,'running');
assert.equal(ft.describe({name:'terminal',args:{command:'x'},done:true,is_error:true}).title,'Opdracht mislukt');
assert.equal(ft.describe({name:'read_file',args:{path:'a/b.txt'},done:true}).title,'Bestand gelezen');
ft.setLanguage('en');
assert.equal(ft.describe({name:'terminal',args:{command:'git status'},done:true}).title,'Ran a command');

// Subagent rows: status from args, last seen when the turn settled mid-run.
const sa={name:'subagent_progress',args:{status:'running',task:'Review docs',task_index:0,task_count:2,tool_count:3},done:false};
assert.equal(ft.describe(sa).state,'running');
assert.equal(ft.describe({...sa,done:true}).state,'last_seen');
assert.equal(ft.describe({...sa,args:{...sa.args,status:'completed',duration_seconds:12}}).state,'done');
assert.equal(ft.describe({...sa,args:{...sa.args,status:'completed',duration_seconds:12}}).duration,12);
assert.equal(ft.describe(sa).target,'1/2: Review docs');

// Group summary: one line with counts per family and failures.
const g=ft.groupSummary([
  {name:'terminal',args:{},done:true},{name:'terminal',args:{},done:true},
  {name:'read_file',args:{},done:true},{name:'terminal',args:{},done:true,is_error:true},
]);
assert.equal(g.count,4);
assert.equal(g.failed,1);
assert.equal(g.text,'🛠️ Work steps (4) · 💻 3 · 📄 1 · ⚠️ 1');

assert.equal(ft.formatDuration(0.2),'<1s');
assert.equal(ft.formatDuration(42.4),'42s');
assert.equal(ft.formatDuration(125),'2m 5s');
const chip=ft.statusChipHtml({state:'failed',duration:3});
assert.match(chip,/⚠️/);
assert.match(chip,/3s/);
assert.match(ft.statusChipHtml({state:'running'}),/sp-spin/);
console.log('ok');
