"""Exercise real detail/load and Add handlers across deferred network results."""

import json
import subprocess
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / 'static/panels.js'


def run_node(script, mode):
    result = subprocess.run(['node', '-e', script, json.dumps(mode)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('mode', ['typed', 'clear', 'task', 'board', 'board_change'])
def test_detail_refresh_preserves_only_current_editor(mode):
    source = SOURCE.read_text()
    handler = source[source.index('async function loadKanbanTask('):source.index('// Phase 2: Single-source-of-truth render.')]
    script = r'''
const assert=require('node:assert/strict'), mode=JSON.parse(process.argv[1]);
let _kanbanCurrentTaskId=null,_kanbanTaskDetailRequestId=0,_kanbanCurrentBoard='first';
const _kanbanSelectedIds=new Set();
let input=null, pending=null, hold=false;
const document={activeElement:null};
function makeInput(){return {value:'',dataset:{},selectionStart:0,selectionEnd:0,selectionDirection:'forward',
 addEventListener(name,fn){this[name]=fn;},focus(){document.activeElement=this;},
 setSelectionRange(a,b,d){this.selectionStart=a;this.selectionEnd=b;this.selectionDirection=d;},
 replaceWith(prior){input=prior;},
 edit(value){this.value=value;if(this.input)this.input();}};}
const preview={dataset:{},style:{},renders:0,querySelector(){return input;},
 set innerHTML(value){this.renders++;input=makeInput();document.activeElement=null;}};
const $=id=>id==='kanbanTaskPreview'?preview:null;
const _kanbanBoardQuery=()=>'?board='+_kanbanCurrentBoard;
const _kanbanTaskTitle=task=>task.title, _kanbanRenderTaskDetail=data=>data.task.title;
const _closeMobileSidebarAfterPanelSelection=()=>{},showToast=()=>{},t=x=>x;
async function api(path){if(hold && path.includes('/log')){hold=false;return new Promise(r=>pending=r);}return {task:{title:'Task'}};}
''' + handler + r'''
(async()=>{
 await loadKanbanTask('child');input.edit('first draft');input.focus();input.setSelectionRange(2,5,'backward');
 const original=input;hold=true;const refresh=loadKanbanTask('child',{preserveSelection:true});
 while(!pending)await Promise.resolve();
 if(mode==='task')await loadKanbanTask('other');
 else if(mode==='board'){_kanbanCurrentBoard='second';await loadKanbanTask('child');}
 else if(mode==='board_change'){_kanbanCurrentBoard='second';}
 else input.edit(mode==='clear'?'':'new draft');
 const newer=input;
 pending({});await refresh;
 if(mode==='typed'||mode==='clear'){
  assert.equal(input,original,'same editor node must survive refresh');
  assert.equal(input.value,mode==='clear'?'':'new draft');
  assert.equal(document.activeElement,input);assert.equal(input.selectionStart,2);assert.equal(input.selectionEnd,5);assert.equal(input.selectionDirection,'backward');
 }else if(mode==='board_change'){
  assert.equal(preview.renders,1,'board identity changes fence old I/O even without a newer detail request');
  assert.equal(input,original);
 }else{assert.notEqual(input,original);assert.equal(input,newer);assert.equal(input.value,'');}
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
    run_node(script, mode)


@pytest.mark.parametrize('mode', ['unchanged', 'changed', 'clear_retype', 'task', 'board', 'reopened'])
def test_add_response_clears_only_submitted_editor_revision(mode):
    source = SOURCE.read_text()
    handler = source[source.index('async function addKanbanDependency('):source.index('async function removeKanbanDependency(')]
    script = r'''
const assert=require('node:assert/strict'),mode=JSON.parse(process.argv[1]);
let _kanbanCurrentTaskId='child',_kanbanCurrentBoard='board';
const original={value:' parent ',dataset:{draftRevision:'1'}};let current=original,resolve;
const document={getElementById:()=>current},_kanbanBoardQuery=()=>'?board='+_kanbanCurrentBoard;
const calls=[],loads=[];async function api(path,options){calls.push({path,body:JSON.parse(options.body)});return new Promise(r=>resolve=r);}
async function loadKanbanTask(id,options){loads.push({id,options});}
const showToast=()=>{},t=x=>x;
''' + handler + r'''
(async()=>{
 const action=addKanbanDependency('child');assert.equal(calls.length,1);
 assert.deepEqual(calls[0].body,{parent_id:'parent',child_id:'child'});
 if(mode==='changed'){current.value='next';current.dataset.draftRevision='2';}
 if(mode==='clear_retype'){current.value=' parent ';current.dataset.draftRevision='3';}
 if(mode==='task'){_kanbanCurrentTaskId='other';current={value:'other draft',dataset:{}};}
 if(mode==='board'){_kanbanCurrentBoard='other';current={value:'other board draft',dataset:{}};}
 if(mode==='reopened'){current={value:'reopened draft',dataset:{}};}
 const expected=current.value;resolve({});await action;
 assert.equal(current.value,mode==='unchanged'?'':expected);
 assert.equal(loads.length,['task','board','reopened'].includes(mode)?0:1);
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
    run_node(script, mode)
