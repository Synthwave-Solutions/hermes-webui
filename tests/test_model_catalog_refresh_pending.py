"""The actual detached catalog producer exposes completion without caching the flag."""
import copy
import pytest
import api.config as cfg
from tests.test_issue3928_models_budget_fallback import gated_catalog_rebuild, isolate_models_catalog_state

@pytest.mark.parametrize("stale_disk", [False, True])
def test_pending_flag_until_detached_catalog_publishes(monkeypatch, gated_catalog_rebuild, stale_disk):
    pool, entered, release, published, calls, live, fallback = gated_catalog_rebuild
    monkeypatch.setattr(cfg, "_LIVE_REBUILD_BUDGET_SECONDS", 0.03)
    monkeypatch.setattr(cfg, "_load_models_cache_from_disk", lambda: None)
    monkeypatch.setattr(cfg, "_load_stale_models_cache_from_disk", lambda: copy.deepcopy(fallback) if stale_disk else None)
    leader = pool.submit(cfg.get_available_models)
    assert entered.wait(1)
    first = leader.result(timeout=0.5)
    assert first.get("refresh_pending") is True
    assert first["groups"] == fallback["groups"]
    follower = cfg.get_available_models()
    assert follower.get("refresh_pending") is True
    assert len(calls) == 1
    assert "refresh_pending" not in fallback
    release.set()
    assert published.wait(1)
    complete = cfg.get_available_models()
    assert complete == live
    assert not complete.get("refresh_pending")
    assert len(calls) == 1


def test_pending_metadata_keeps_fresh_governance_filtering(monkeypatch):
    from api.governance import resource_scope
    payload = {"refresh_pending": True, "active_provider": "allowed", "groups": [
        {"provider_id": "allowed", "models": [{"id": "permitted"}, {"id": "denied"}]},
        {"provider_id": "blocked", "models": [{"id": "permitted"}]}]}
    current = {"permitted": True}
    monkeypatch.setattr(resource_scope, "access_for", lambda handler: current)
    monkeypatch.setattr(resource_scope, "allowed", lambda access, kind, provider: provider == "allowed")
    monkeypatch.setattr(resource_scope, "model_allowed", lambda access, model, provider=None: bool(access.get(model)))
    first = resource_scope.filter_models(object(), payload)
    assert first["refresh_pending"] is True
    assert first["groups"] == [{"provider_id": "allowed", "models": [{"id": "permitted"}]}]
    current.clear()
    assert resource_scope.filter_models(object(), payload)["groups"] == []
    assert len(payload["groups"][0]["models"]) == 2
