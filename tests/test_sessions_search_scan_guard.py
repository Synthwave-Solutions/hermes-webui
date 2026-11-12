"""Content search must stay bounded: it parses every transcript under the GIL,
and the sidebar fires one request per typing pause without cancelling the
previous one. On 12 Nov 2026 fourteen overlapping scans stalled the chat list
and chat start for minutes. These tests pin the three guards: a cap on
concurrent scans, a time budget per scan, and newest-query-wins per requester.
Title matches must survive all three.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlparse

META = [
    {"session_id": "s1", "title": "Untitled", "profile": "default"},
    {"session_id": "s2", "title": "needle in the title", "profile": "default"},
    {"session_id": "s3", "title": "Untitled", "profile": "default"},
]


def _session(sid):
    return SimpleNamespace(session_id=sid, messages=[{"role": "user", "content": "a NEEDLE here"}])


def _search(get_scan, handler=None):
    import api.routes as routes

    captured = {}

    def fake_j(_handler, payload, status=200, extra_headers=None):
        captured["payload"] = payload

    with patch("api.routes.all_sessions", return_value=[dict(m) for m in META]), patch(
        "api.routes.get_session_for_scan", side_effect=get_scan
    ), patch("api.profiles.get_active_profile_name", return_value="default"), patch(
        "api.routes.j", side_effect=fake_j
    ):
        routes._handle_sessions_search(
            handler or SimpleNamespace(), urlparse("/api/sessions/search?q=needle&content=1")
        )
    return captured["payload"]


def _match_types(payload):
    return {s["session_id"]: s["match_type"] for s in payload["sessions"]}


def test_unbounded_case_is_unchanged():
    payload = _search(_session)
    assert _match_types(payload) == {"s1": "content", "s2": "title", "s3": "content"}
    assert "content_search" not in payload


def test_busy_when_every_slot_is_taken_keeps_title_matches():
    import api.routes as routes

    slots = threading.BoundedSemaphore(1)
    slots.acquire()
    calls = []
    with patch.object(routes, "_CONTENT_SEARCH_SLOTS", slots), patch.object(
        routes, "_CONTENT_SEARCH_SLOT_WAIT_SECONDS", 0.01
    ):
        payload = _search(lambda sid: calls.append(sid) or _session(sid))
    assert payload["content_search"] == "busy"
    assert _match_types(payload) == {"s2": "title"}
    assert calls == []  # no transcript was read


def test_slot_is_released_after_a_scan_even_when_loading_raises():
    import api.routes as routes

    slots = threading.BoundedSemaphore(1)

    def boom(_sid):
        raise RuntimeError("corrupt sidecar")

    with patch.object(routes, "_CONTENT_SEARCH_SLOTS", slots):
        _search(boom)
        payload = _search(_session)
    assert "content_search" not in payload
    assert slots.acquire(blocking=False)


def test_budget_truncates_content_scan_but_not_title_matches():
    import api.routes as routes

    clock = {"now": 0.0}

    def slow_load(sid):
        clock["now"] += 10.0  # every transcript costs ten seconds
        return _session(sid)

    with patch.object(routes, "_CONTENT_SEARCH_BUDGET_SECONDS", 5.0), patch.object(
        routes.time, "monotonic", side_effect=lambda: clock["now"]
    ):
        payload = _search(slow_load)
    assert payload["content_search"] == "truncated"
    # s1 was read inside the budget, s3 was not; the title match is kept.
    assert _match_types(payload) == {"s1": "content", "s2": "title"}


def test_newer_query_from_same_requester_supersedes_the_running_scan():
    import api.routes as routes

    handler = SimpleNamespace(client_address=("100.64.0.1", 1))
    calls = []

    def load_then_new_query(sid):
        calls.append(sid)
        # Simulate the same requester starting a newer search mid-scan.
        routes._CONTENT_SEARCH_LATEST["addr:100.64.0.1"] = object()
        return _session(sid)

    try:
        payload = _search(load_then_new_query, handler=handler)
    finally:
        routes._CONTENT_SEARCH_LATEST.pop("addr:100.64.0.1", None)
    assert payload["content_search"] == "superseded"
    assert calls == ["s1"]
    assert _match_types(payload) == {"s1": "content", "s2": "title"}


def test_requester_registry_is_cleaned_up():
    import api.routes as routes

    _search(_session, handler=SimpleNamespace(client_address=("100.64.0.2", 1)))
    assert "addr:100.64.0.2" not in routes._CONTENT_SEARCH_LATEST
