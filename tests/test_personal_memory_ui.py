"""Actual memory loader rejects late responses from another conversation."""
import subprocess
from pathlib import Path


def test_memory_loader_discards_old_context_and_clears_detail():
    source = (Path(__file__).resolve().parents[1] / 'static/panels.js').read_text()
    loader = source[source.index('async function loadMemory(force)'):source.index('// Drag and drop', source.index('async function loadMemory(force)'))]
    context = source[source.index('function _memoryContext()'):source.index('let _notesSourcesData')]
    script = r'''
const assert=require('node:assert/strict');
let S={session:{session_id:'first'},activeProfile:'default'};
let _memoryData={memory:'old private'},_memoryRequestEpoch=0,_memoryLoadedContext=null,_memoryMode='read',_currentMemorySection=null;
const panel={innerHTML:'old',appendChild(){}},detail={innerHTML:'old private'};
const $=id=>id==='memoryPanel'?panel:id==='memoryDetailBody'?detail:null;
const _setMemoryHeaderButtons=()=>{},MEMORY_SECTIONS=[],esc=x=>x,t=x=>x;
let pending=[];const api=url=>new Promise(resolve=>pending.push({url,resolve}));
''' + context + loader + r'''
(async()=>{
const first=loadMemory();assert.equal(detail.innerHTML,'');
S.session={session_id:'second'};const second=loadMemory();
pending[1].resolve({memory:'second private'});await second;
pending[0].resolve({memory:'first private'});await first;
assert.equal(_memoryData.memory,'second private');
assert.equal(pending[1].url,'/api/memory?session_id=second');
})();
'''
    subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
