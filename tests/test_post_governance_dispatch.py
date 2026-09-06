"""POST dispatch must reach the module governance gate for every browser route."""
from types import SimpleNamespace
from urllib.parse import urlparse
import pytest
from api import routes

@pytest.mark.parametrize('path',['/api/session/new','/api/profile/appearance','/api/profile/avatar'])
def test_post_dispatch_reaches_governance_gate(monkeypatch,path):
    seen=[]
    monkeypatch.setattr(routes.RequestDiagnostics,'maybe_start',lambda *a,**k:None)
    monkeypatch.setattr(routes,'_check_csrf',lambda handler:True)
    monkeypatch.setattr(routes.governance_api,'handle_governance_api',lambda handler,parsed,method:seen.append((parsed.path,method)) or True)
    assert routes.handle_post(SimpleNamespace(),urlparse(path)) is True
    assert seen==[(path,'POST')]
