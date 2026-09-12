"""Actual project-store read budgets and fresh authorization for sidebar lists."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

from api import models, project_collaboration, routes


ALICE = "alice@example.test"
BOB = "bob@example.test"
REAL_CACHE_GET = routes._get_cached_session_list_payload


@pytest.fixture
def project_store(tmp_path, monkeypatch):
    path = tmp_path / "projects.json"
    monkeypatch.setattr(models, "PROJECTS_FILE", path)
    monkeypatch.setattr(project_collaboration, "administrative", lambda identity: False)
    calls = []
    original = Path.read_text

    def read_text(target, *args, **kwargs):
        if target == path:
            calls.append(target)
        return original(target, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)

    def save(members=(ALICE,), deleted=False):
        path.write_text(json.dumps([
            {"project_id": "team", "owner_email": "owner@example.test", "members": list(members), "deleted": deleted},
            {"project_id": "elsewhere", "owner_email": BOB, "members": []},
        ]))

    save()
    return path, calls, save


def rows(count=40, *, shared=True, profile="default"):
    return [{"session_id": f"session-{i}", "project_id": "team", "project_shared": shared,
             "owner_email": ALICE, "participants": [], "profile": profile,
             "message_count": 2, "updated_at": 100 + i, "title": f"Synthetic {i}"}
            for i in range(count)]


def test_personal_organization_does_not_read_project_membership(project_store):
    _, calls, _ = project_store
    assert project_collaboration.session_access(rows(1, shared=False)[0], BOB) is None
    assert calls == []


@pytest.fixture
def sidebar_request(monkeypatch):
    """Real dispatcher/response projection, synthetic completed cache payload only."""
    from api import ownership, profiles
    from api.governance import enforce
    holder = {"rows": rows()}
    monkeypatch.setattr(routes, "load_settings", lambda: {"show_cli_sessions": False, "api_redact_enabled": False})
    monkeypatch.setattr(profiles, "get_active_profile_name", lambda: "default")
    monkeypatch.setattr(routes, "_is_isolated_profile_mode", lambda: False)
    monkeypatch.setattr(ownership, "request_owner_scope", lambda handler: handler.identity["email"])
    monkeypatch.setattr(enforce, "_request_identity", lambda handler: handler.identity)
    monkeypatch.setattr(routes, "_get_cached_session_list_payload", lambda **kw: copy.deepcopy({
        "sessions": holder["rows"], "sidebar_reference_sessions": holder["rows"][:4],
        "active_profile": "default", "all_profiles": False,
    }))
    monkeypatch.setattr(routes, "_session_list_cache_overlay_runtime_rows", lambda value: value)
    captured = []
    monkeypatch.setattr(routes, "j", lambda handler, payload, **kw: captured.append(payload))

    def request(actor=ALICE):
        handler = SimpleNamespace(identity={"email": actor}, headers={}, command="GET")
        routes.handle_get(handler, urlparse("/api/sessions"))
        return captured[-1]

    return holder, request


def test_cached_sidebar_reads_project_store_once_for_both_row_lists(project_store, sidebar_request):
    _, calls, _ = project_store
    _, request = sidebar_request
    payload = request()
    assert len(payload["sessions"]) == 40
    assert len(payload["sidebar_reference_sessions"]) == 4
    assert len(calls) == 1


def test_cached_sidebar_rechecks_revocation_and_does_not_leak_between_actors(project_store, sidebar_request):
    _, calls, save = project_store
    _, request = sidebar_request
    assert len(request()["sessions"]) == 40
    assert request(BOB)["sessions"] == []
    save(members=(BOB,))
    assert request()["sessions"] == []
    assert len(request(BOB)["sessions"]) == 40
    save(members=(BOB,), deleted=True)
    deleted = request(BOB)
    assert deleted["sessions"] == deleted["sidebar_reference_sessions"] == []
    assert len(calls) == 5


def test_cached_personal_project_rows_never_read_membership(project_store, sidebar_request):
    _, calls, _ = project_store
    holder, request = sidebar_request
    holder["rows"] = rows(shared=False)
    assert len(request()["sessions"]) == 40
    assert calls == []


def test_sidebar_builder_reads_once_across_owner_and_other_profile_passes(project_store, monkeypatch):
    _, calls, _ = project_store
    source = rows(profile="writer") + [{**rows(1, shared=False)[0], "session_id": "foreign", "owner_email": BOB}]
    monkeypatch.setattr(routes, "all_sessions", lambda **kw: copy.deepcopy(source))
    monkeypatch.setattr(routes, "_reconcile_stale_stream_state_for_session_rows", lambda value: False)
    monkeypatch.setattr(routes, "_prune_orphaned_webui_zero_message_sessions", lambda value, **kw: value)
    monkeypatch.setattr(routes, "_is_isolated_profile_mode", lambda: False)
    payload = routes._build_session_list_cache_payload(
        active_profile="default", all_profiles=False, show_cli_sessions=False,
        show_previous_messaging_sessions=False, show_cron_sessions=False, owner_scope=ALICE,
    )
    assert {row["session_id"] for row in payload["sessions"]} == {row["session_id"] for row in source[:40]}
    assert payload["other_profile_count"] == 0
    assert len(calls) == 1


def test_real_warm_cache_retains_internal_scope_but_rechecks_current_store(project_store, sidebar_request, monkeypatch):
    _, calls, save = project_store
    holder, request = sidebar_request
    builds = []

    def build(**kwargs):
        builds.append(kwargs["owner_scope"])
        return {"sessions": copy.deepcopy(holder["rows"]), "sidebar_reference_sessions": copy.deepcopy(holder["rows"][:4])}

    monkeypatch.setattr(routes, "_get_cached_session_list_payload", REAL_CACHE_GET)
    monkeypatch.setattr(routes, "_build_session_list_cache_payload", build)
    monkeypatch.setattr(routes, "_session_list_cache_source_stamp", lambda key: ("unchanged-sidebar",))
    routes._session_list_cache_clear()
    try:
        before = request()
        assert len(before["sessions"]) == 40
        assert all("project_shared" not in row for row in before["sessions"])
        # Simulates an out-of-band project edit without a sidebar invalidation.
        save(members=())
        revoked = request()
        assert revoked["sessions"] == revoked["sidebar_reference_sessions"] == []
        # Response filtering must not poison the immutable cache for a later grant.
        save()
        assert len(request()["sessions"]) == 40
        assert builds == [ALICE]
        assert len(calls) == 3
    finally:
        routes._session_list_cache_clear()


@pytest.mark.parametrize("contents", [None, "{broken", "[]"])
def test_missing_or_unreadable_current_project_store_hides_shared_rows(project_store, sidebar_request, contents):
    path, _, _ = project_store
    holder, request = sidebar_request
    holder["rows"].append({**rows(1, shared=False)[0], "session_id": "personal"})
    if contents is None:
        path.unlink()
    else:
        path.write_text(contents)
    result = request()
    assert [row["session_id"] for row in result["sessions"]] == ["personal"]
    assert result["sidebar_reference_sessions"] == []


def test_missing_project_id_denies_without_reading_unrelated_project_store(project_store, sidebar_request):
    _, calls, _ = project_store
    holder, request = sidebar_request
    holder["rows"] = [{**row, "project_id": None} for row in holder["rows"]]
    result = request()
    assert result["sessions"] == result["sidebar_reference_sessions"] == []
    assert calls == []


def test_duplicate_project_ids_preserve_first_record_authority(project_store, sidebar_request):
    path, calls, _ = project_store
    _, request = sidebar_request
    path.write_text(json.dumps([
        {"project_id": "team", "owner_email": BOB, "members": []},
        {"project_id": "team", "owner_email": ALICE, "members": [ALICE]},
    ]))
    result = request()
    assert result["sessions"] == result["sidebar_reference_sessions"] == []
    assert len(calls) == 1


def test_builder_snapshot_cannot_authorize_final_response_after_revocation(project_store, sidebar_request, monkeypatch):
    _, calls, save = project_store
    holder, request = sidebar_request
    monkeypatch.setattr(routes, "all_sessions", lambda **kw: copy.deepcopy(holder["rows"]))
    monkeypatch.setattr(routes, "_reconcile_stale_stream_state_for_session_rows", lambda value: False)
    monkeypatch.setattr(routes, "_prune_orphaned_webui_zero_message_sessions", lambda value, **kw: value)

    def cache_build_then_revoke(**kwargs):
        built = kwargs["builder"]()
        assert len(built["sessions"]) == 40
        save(members=())
        return built

    monkeypatch.setattr(routes, "_get_cached_session_list_payload", cache_build_then_revoke)
    result = request()
    assert result["sessions"] == result["sidebar_reference_sessions"] == []
    assert len(calls) == 2  # Independent builder and final-response snapshots.


def test_concurrent_checkers_do_not_share_identity_or_hold_project_lock(project_store):
    from concurrent.futures import ThreadPoolExecutor
    import threading

    _, calls, _ = project_store
    alice_loaded = threading.Event()
    release_alice = threading.Event()
    session = rows(1)[0]

    def alice():
        check = project_collaboration.session_access_checker(ALICE)
        assert check(session) is True
        alice_loaded.set()
        release_alice.wait()
        return check(session)

    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(alice)
        try:
            assert alice_loaded.wait(3)
            # Alice's retained projection must not retain the global store lock.
            other = pool.submit(lambda: project_collaboration.session_access_checker(BOB)(session))
            assert other.result(timeout=3) is False
        finally:
            release_alice.set()
        assert pending.result(timeout=3) is True
    assert len(calls) == 2
