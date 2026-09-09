"""Task modal focus runs before the user can edit another field."""
import subprocess

import pytest


SCRIPT = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('static/panels.js','utf8');
function extract(name){const marker=(name==='openKanbanEdit'?'async ':'')+'function '+name+'(';
 const start=source.indexOf(marker),end=source.indexOf('\n}',start);assert.ok(start>=0&&end>start);return source.slice(start,end+2);}
function setup(){
 const timers=[],modal={hidden:true};
 const title={value:'Original',selected:false,focus(){ctx.document.activeElement=this;},select(){this.selected=true;}};
 const priority={value:'',focus(){ctx.document.activeElement=this;}};
 const ctx={document:{activeElement:{id:'edit-button'},getElementById:id=>id==='kanbanTaskModal'?modal:id==='kanbanTaskModalTitleInput'?title:null,addEventListener(){},removeEventListener(){}},
  _currentPanel:'kanban',_kanbanTaskModalMode:'create',_kanbanTaskModalEditingId:null,_kanbanTaskModalInitialDisplayedStatus:null,_kanbanTaskModalFocusCleanup:null,
  _kanbanTaskModalKey(){},_kanbanBoardQuery:()=>'',api:async()=>({task:{id:'task',title:'Original',status:'todo'}}),
  _kanbanEditableStatusFor:s=>s,_kanbanResetTaskModalFields:values=>{title.value=values.title||'';},
  _kanbanPopulateAssigneeSelect:async()=>{},_kanbanPopulateTenantDatalist(){},_kanbanPopulateWorkspacePathDatalist(){},_kanbanPopulateParentsDatalist(){},
  _kanbanSetTaskModalStatusHint(){},_kanbanSetTaskModalLabels(){},_trapModalFocus:()=>()=>{},
  setTimeout:fn=>timers.push(fn),console};
 vm.createContext(ctx);vm.runInContext(extract('openKanbanCreate')+extract('openKanbanEdit'),ctx);
 return {ctx,title,priority,modal,timers,open:mode=>mode==='edit'?ctx.openKanbanEdit('task'):ctx.openKanbanCreate()};
}
'''


def _run(body):
    result = subprocess.run(['node', '-e', SCRIPT + body], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mode', ['create', 'edit'])
def test_task_modal_initial_focus_is_complete_when_open_returns(mode):
    _run(r'''
(async()=>{const f=setup();await f.open(MODE);assert.equal(f.modal.hidden,false);
 assert.equal(f.ctx.document.activeElement,f.title,'initial focus belongs to modal opening');
 assert.equal(f.title.selected,MODE==='edit');assert.equal(f.timers.length,0,'no late focus callback');
})().catch(e=>{console.error(e);process.exitCode=1;});
'''.replace('MODE', repr(mode)))


@pytest.mark.parametrize('mode', ['create', 'edit'])
def test_task_modal_cannot_reclaim_focus_after_priority_input_or_close(mode):
    _run(r'''
(async()=>{for(const closed of [false,true]){const f=setup();await f.open(MODE);
 f.title.value='Edited title';f.title.selected=false;f.priority.focus();f.modal.hidden=closed;
 f.timers.forEach(callback=>callback());
 assert.equal(f.ctx.document.activeElement,f.priority,'late modal focus must not redirect typing');
 assert.equal(f.title.value,'Edited title');assert.equal(f.title.selected,false);
}})().catch(e=>{console.error(e);process.exitCode=1;});
'''.replace('MODE', repr(mode)))
