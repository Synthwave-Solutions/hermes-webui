"""The queue must remain usable while the advisory model is unavailable."""
import json
import sys
from types import SimpleNamespace
from urllib.parse import urlparse
from unittest.mock import Mock

from api import approval_advice, approvals, governance_api, grant_requests


def entry(i=0):
    return {"kind": "grant", "key": f"user@example.test|cli|tool{i}",
            "owner_email": "user@example.test", "status": "pending",
            "payload": {"gkind": "cli", "value": f"tool{i}",
                        "trigger": "Run the project tests"}}


def test_queue_returns_all_requests_without_waiting_on_provider(monkeypatch):
    approval_advice.clear_cache()
    model = Mock(side_effect=RuntimeError("provider must not be called by queue"))
    monkeypatch.setattr(approval_advice, "_ask_model", model)
    monkeypatch.setattr(governance_api, "_require_governance_admin", lambda *args: True)
    monkeypatch.setattr(grant_requests, "ingest_spool", lambda: None)
    monkeypatch.setattr(approvals, "list_pending", lambda **kwargs: [entry(i) for i in range(50)])
    received = []
    monkeypatch.setattr(governance_api, "j", lambda handler, data: received.append(data))
    access = SimpleNamespace(has_permission=lambda _: False)
    governance_api._handle_approvals_get(None, urlparse('/api/governance/approvals'), None, None, access)
    assert len(received[0]["pending"]) == 50
    assert all(row["status"] == "pending" and row["advice"]["source"] == "rules"
               and row["explanation"]["capability"] for row in received[0]["pending"])
    model.assert_not_called()


def test_catalog_queue_fallback_does_not_prevent_later_model_advice(monkeypatch):
    approval_advice.clear_cache()
    model = Mock(return_value={"source": "model", "recommendation": "grant",
                             "recommendation_reason": "Allowed technical work"})
    monkeypatch.setattr(approval_advice, "_ask_model", model)
    monkeypatch.setattr(approval_advice, "advice_enabled", lambda: True)
    assert approval_advice.advise(entry(), allow_model=False)["source"] == "rules"
    model.assert_not_called()
    assert approval_advice.advise(entry())["source"] == "model"
    assert approval_advice.advise(entry(), allow_model=False)["source"] == "model"
    model.assert_called_once()
    approval_advice.clear_cache()


def test_queue_still_requires_governance_admin(monkeypatch):
    listing = Mock()
    monkeypatch.setattr(governance_api, "_require_governance_admin", lambda *args: False)
    monkeypatch.setattr(approvals, "list_pending", listing)
    assert governance_api._handle_approvals_get(None, urlparse('/api/governance/approvals'), None, None, None)
    listing.assert_not_called()


def test_detail_advice_uses_configured_approval_provider(monkeypatch):
    call = Mock(return_value={"choices": [{"message": {"content": json.dumps({
        "why": "Run the project tests", "risk": "Project files only",
        "recommendation": "grant", "recommendation_reason": "Technical work",
        "narrower_alternative": "",
    })}}]})
    monkeypatch.setitem(sys.modules, 'agent.auxiliary_client', SimpleNamespace(call_llm=call))
    assert approval_advice._ask_model(entry(), {})["source"] == "model"
    assert call.call_args.kwargs["task"] == "approval"
