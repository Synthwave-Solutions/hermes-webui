from pathlib import Path
import subprocess


def test_directory_failure_is_retryable_not_a_cached_empty_success(monkeypatch):
    from api import routes
    from api.governance import loader
    def unavailable(): raise RuntimeError('fixture unavailable')
    monkeypatch.setattr(loader,'load_governance_policy',unavailable)
    monkeypatch.setattr(routes,'bad',lambda handler,message,status: (status,message))
    assert routes._handle_people_directory(object())[0]==503


def test_people_picker_retries_refreshes_and_folds_accents():
    root=Path(__file__).resolve().parents[1]
    source=(root/'static/ui.js').read_text()
    start=source.index('async function openGroupPeoplePicker()')
    end=source.index("if (typeof window !== 'undefined') window.openGroupPeoplePicker",start)
    search_start=source.find('function _groupSearchText(')
    search=source[search_start:source.index('function renderGroupPeopleList()',search_start)] if search_start>=0 else ''
    script=r'''
const assert=require('assert');
let calls=0, fail=false;
const nodes={groupPeopleModal:{},groupPeopleModalError:{},groupPeopleModalSubmit:{},groupPeopleFilter:{focus(){}}};
const $=id=>nodes[id]; const t=x=>x;
let _groupPeopleDirectory=[],_groupPeopleDraft=[];
const _currentParticipants=()=>[];
const _groupPeopleCanManage=()=>true;
const renderGroupPeopleList=()=>{};
const api=async(url)=>{if(url==='/api/profiles')return [];calls++;if(fail)throw Error('offline');return {me:' OTHER@example.test ',people:[{email:'other@example.test'},{email:'michael@example.test'}]};};
''' + source[start:end] + search + r'''
(async()=>{
 await openGroupPeoplePicker();assert.equal(calls,1);
 assert.deepEqual(_groupPeopleDirectory,[{email:'michael@example.test'}]);
 fail=true;await openGroupPeoplePicker();assert.equal(calls,2);assert.equal(_groupPeopleDirectory,null);
 fail=false;await openGroupPeoplePicker();assert.equal(calls,3);
 assert.equal(_groupSearchText(' Michaël '),'michael');
 assert.equal(_groupSearchText('Michae\u0308l').includes(_groupSearchText('Michael')),true);
})().catch(e=>{console.error(e);process.exit(1)});
'''
    result=subprocess.run(['node','-e',script],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
