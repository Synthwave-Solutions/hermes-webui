import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from api import approval_advice, governance_api, capability_risk

ENTRY={'kind':'grant','key':'user@example.test|tool|read_file','label':'Tool: read_file','owner_email':'user@example.test','status':'pending','payload':{'gkind':'tool','value':'read_file'}}

def test_missing_original_request_is_explained_not_blank(monkeypatch):
    monkeypatch.setenv('HERMES_WEBUI_APPROVAL_ADVICE','off')
    approval_advice.clear_cache()
    advice=approval_advice.advise(ENTRY,{'capability':'Read a file','risks':['data_access']})
    assert 'not recorded' in advice['why']
    assert 'data_access' not in advice['risk']
    assert 'read' in advice['risk'].lower()

def test_catalog_and_advice_failure_still_explain_uncertainty(monkeypatch):
    monkeypatch.setattr(capability_risk,'explain_entry',lambda *a,**k:{})
    monkeypatch.setattr(approval_advice,'advise',lambda *a,**k:{})
    row=governance_api._approval_row(ENTRY,explain=True)
    assert row['explanation']['capability']
    assert row['advice']['why']
    assert row['advice']['recommendation']=='needs_more_information'
