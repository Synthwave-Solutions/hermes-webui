"""Cron skill picker callbacks retain only their own blur intent."""
import subprocess


SCRIPT = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('static/panels.js','utf8');
function extract(name){const a=source.indexOf('function '+name+'('),b=source.indexOf('\n}',a);assert.ok(a>=0&&b>a);return source.slice(a,b+2);}
function setup(){
 const timers=[],cleared=[];
 const dropdown={style:{display:'none'},children:[],set innerHTML(value){this.children=[];},appendChild(n){this.children.push(n);}};
 const search={value:'qa-skill',disabled:false};const els={cronFormSkillSearch:search,cronFormSkillDropdown:dropdown};
 const ctx={_cronSelectedSkills:[],_cronSkillsCache:[{name:'qa-skill'}],_cronSkillPickerCleanup:null,
  $:id=>els[id],document:{activeElement:search,createElement:()=>({})},_renderCronSkillTags(){},
  setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:id=>cleared.push(id)};
 vm.createContext(ctx);
 if(source.includes('function _disposeCronSkillPicker('))vm.runInContext(extract('_disposeCronSkillPicker'),ctx);
 vm.runInContext(extract('_bindCronSkillPicker'),ctx);ctx._bindCronSkillPicker();
 return{ctx,search,dropdown,els,timers,cleared,focus(){ctx.document.activeElement=search;if(search.onfocus)search.onfocus();},
  blur(){ctx.document.activeElement={};search.onblur();},input(){search.oninput();}};
}
'''


def _run(body):
    result=subprocess.run(['node','-e',SCRIPT+body],text=True,capture_output=True,check=False)
    assert result.returncode==0,result.stdout+result.stderr


def test_old_blur_cannot_close_a_new_input_or_refocus():
    _run(r'''
for(const kind of ['input','focus']){const f=setup();f.input();f.blur();
 f.ctx.document.activeElement=f.search;if(kind==='input')f.input();else f.focus();f.timers[0]();
 assert.equal(f.dropdown.style.display,'',kind);assert.equal(f.search.value,'qa-skill');}
''')


def test_old_blur_cannot_consume_a_later_distinct_outside_blur():
    _run(r'''
const f=setup();f.input();f.blur();f.focus();f.input();f.blur();
f.timers[0]();assert.equal(f.dropdown.style.display,'','old blur cannot hide a newly opened query');
f.timers[1]();assert.equal(f.dropdown.style.display,'none','current outside blur still closes');
''')


def test_selection_removal_and_focus_reopen_use_current_selected_skills():
    _run(r'''
const f=setup();f.input();f.dropdown.children[0].onclick();
assert.equal(f.ctx._cronSelectedSkills.length,1);assert.equal(f.search.value,'');assert.equal(f.dropdown.style.display,'none');
f.ctx._cronSelectedSkills=[];f.search.value='qa-skill';f.focus();
assert.equal(f.dropdown.style.display,'');assert.equal(f.dropdown.children.length,1);
f.dropdown.children[0].onclick();assert.equal(f.ctx._cronSelectedSkills.length,1);
''')


def test_rebinding_or_disposal_invalidates_already_queued_callbacks():
    _run(r'''
for(const mode of ['rebind','dispose','replace']){const f=setup();f.input();f.blur();
 if(mode==='rebind'){f.ctx._bindCronSkillPicker();f.focus();f.input();f.blur();}
 if(mode==='dispose'){assert.equal(typeof f.ctx._disposeCronSkillPicker,'function');f.ctx._disposeCronSkillPicker();}
 if(mode==='replace')f.els.cronFormSkillSearch={};
 f.timers[0]();assert.equal(f.dropdown.style.display,'',mode+' must not mutate from old callback');}
''')
