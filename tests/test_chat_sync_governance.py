"""Governance coverage for the non-streaming agent entry points.

MAJOR-1: the sync chat fallback (POST /api/chat, _handle_chat_sync) runs the
whole turn on the handler thread and used to construct AIAgent plus call
run_conversation with NO governance bind (ungoverned turn for any non-admin
under mode enforce). It must now bind governed_agent_turn around construction
plus the turn, and refuse with 403 when the bind fails closed.

MAJOR-2: /api/btw and /api/background create hidden child sessions; they used
to stay ownerless, so their streaming turns bound nothing. They must now carry
the request identity (fallback: the parent session's owner_email), keeping the
identity-less legacy case ownerless.

Idioms follow tests/test_workspace_ownership.py (mock handler + patched module
seams) and tests/test_governance_agent_context.py (agent_context seam).
"""
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.governance import agent_context  # noqa: E402
from api.governance.agent_context import GovernanceBindingError  # noqa: E402

STEVE = "steve@synthwave.solutions"
MICHAEL = "michael@synthwave.solutions"


def _make_handler():
    """Create a mock HTTP handler."""
    h = MagicMock()
    h.wfile = MagicMock()
    return h


def _handler_body(handler) -> bytes:
    return b"".join(
        call.args[0] for call in handler.wfile.write.call_args_list if call.args
    )


class _FakeSession:
    """Minimal concrete session double (MagicMock breaks JSON serialization
    of compact() in the response path)."""

    def __init__(self, session_id="sess-sync", owner_email=None):
        self.session_id = session_id
        self.workspace = "/tmp"
        self.model = "test-model"
        self.model_provider = None
        self.profile = None
        self.messages = []
        self.context_messages = []
        self.owner_email = owner_email
        self.title = "Untitled"
        self.input_tokens = 0
        self.output_tokens = 0
        self.estimated_cost = 0.0
        self.pending_user_source = None
        self.pending_user_message = None
        self.active_stream_id = None
        self.save_count = 0

    def save(self):
        self.save_count += 1

    def compact(self):
        return {"session_id": self.session_id, "title": self.title}


class _InlineThread:
    """Synchronous threading.Thread stand-in so the btw/background worker runs
    inside the test while the patches are still active (no daemon race)."""

    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        if self._target is not None:
            self._target(*self._args, **self._kwargs)


# ── MAJOR-1: sync chat fallback binds the governance turn ────────────────────

class TestChatSyncGovernanceBind:

    def _run_sync_chat(self, monkeypatch, events, *, bind_raises=False,
                       request_owner=STEVE, session_owner=None):
        import api.routes as routes
        import api.ownership as ownership

        s = _FakeSession(owner_email=session_owner)

        @contextmanager
        def _fake_turn(identity, **kw):
            if bind_raises:
                raise GovernanceBindingError()
            events.append(("bind", identity, kw.get("session_id")))
            try:
                yield
            finally:
                events.append("reset")

        class _FakeAgent:
            def __init__(self, **kw):
                events.append("construct")

            def run_conversation(self, **kw):
                events.append("run")
                return {"messages": [], "final_response": "ok", "completed": True}

        monkeypatch.setattr(agent_context, "governed_agent_turn", _fake_turn)
        monkeypatch.setitem(sys.modules, "run_agent", SimpleNamespace(AIAgent=_FakeAgent))
        monkeypatch.setattr(routes, "get_session", lambda sid: s)
        monkeypatch.setattr(routes, "_session_is_subagent_view_only", lambda sid: False)
        monkeypatch.setattr(routes, "resolve_trusted_workspace", lambda p: str(p))
        monkeypatch.setattr(routes, "_read_profile_model_config",
                            lambda s_, provider: (None, None, None))
        monkeypatch.setattr(routes, "_resolve_compatible_session_model_state",
                            lambda *a, **kw: ("test-model", None))
        monkeypatch.setattr(ownership, "request_owner_email", lambda h: request_owner)
        # Keep the runtime-provider key resolution inert (no oauth/config IO).
        import api.oauth as oauth
        monkeypatch.setattr(
            oauth, "resolve_runtime_provider_with_anthropic_env_lock",
            lambda *a, **kw: {"api_key": None, "provider": None, "base_url": None},
        )
        handler = _make_handler()
        routes._handle_chat_sync(handler, {"session_id": s.session_id, "message": "hi"})
        return handler, s

    def test_turn_binds_before_construction_and_covers_run(self, monkeypatch):
        events = []
        handler, s = self._run_sync_chat(monkeypatch, events)
        assert ("bind", STEVE, s.session_id) in events
        bind_at = events.index(("bind", STEVE, s.session_id))
        assert bind_at < events.index("construct") < events.index("run")
        assert events.index("run") < events.index("reset")
        handler.send_response.assert_called_with(200)
        assert b'"answer"' in _handler_body(handler)

    def test_bind_failure_refuses_with_403(self, monkeypatch):
        events = []
        handler, _s = self._run_sync_chat(monkeypatch, events, bind_raises=True)
        handler.send_response.assert_called_with(403)
        assert b"Access restricted: governance context unavailable" in _handler_body(handler)
        # Fail closed: neither the agent construction nor the turn ran.
        assert "construct" not in events
        assert "run" not in events

    def test_identity_falls_back_to_session_owner(self, monkeypatch):
        events = []
        _handler, s = self._run_sync_chat(
            monkeypatch, events, request_owner=None, session_owner=MICHAEL,
        )
        assert ("bind", MICHAEL, s.session_id) in events


# ── MAJOR-2: btw/background child sessions carry owner_email ─────────────────

class TestBtwBackgroundOwnerStamping:

    def _patch_common(self, monkeypatch, parent, child, request_owner):
        import threading
        import api.routes as routes
        import api.models as models
        import api.ownership as ownership

        monkeypatch.setattr(routes, "get_session", lambda sid: parent)
        monkeypatch.setattr(routes, "_session_is_subagent_view_only", lambda sid: False)
        monkeypatch.setattr(models, "new_session", lambda **kw: child)
        monkeypatch.setattr(ownership, "request_owner_email", lambda h: request_owner)
        monkeypatch.setattr(routes, "_run_agent_streaming", lambda *a, **kw: None)
        monkeypatch.setattr(threading, "Thread", _InlineThread)
        return routes

    def test_btw_stamps_request_identity(self, monkeypatch):
        parent = _FakeSession(session_id="parent", owner_email=MICHAEL)
        child = _FakeSession(session_id="btw-child")
        routes = self._patch_common(monkeypatch, parent, child, STEVE)
        routes._handle_btw(_make_handler(), {"session_id": "parent", "question": "quick q"})
        assert child.owner_email == STEVE

    def test_btw_falls_back_to_parent_owner(self, monkeypatch):
        parent = _FakeSession(session_id="parent", owner_email=MICHAEL)
        child = _FakeSession(session_id="btw-child")
        routes = self._patch_common(monkeypatch, parent, child, None)
        routes._handle_btw(_make_handler(), {"session_id": "parent", "question": "quick q"})
        assert child.owner_email == MICHAEL

    def test_btw_identity_less_stays_ownerless(self, monkeypatch):
        parent = _FakeSession(session_id="parent", owner_email=None)
        child = _FakeSession(session_id="btw-child")
        routes = self._patch_common(monkeypatch, parent, child, None)
        routes._handle_btw(_make_handler(), {"session_id": "parent", "question": "quick q"})
        assert child.owner_email is None

    def test_background_stamps_request_identity(self, monkeypatch):
        parent = _FakeSession(session_id="parent", owner_email=MICHAEL)
        child = _FakeSession(session_id="bg-child")
        routes = self._patch_common(monkeypatch, parent, child, STEVE)
        routes._handle_background(_make_handler(), {"session_id": "parent", "prompt": "do it"})
        assert child.owner_email == STEVE

    def test_background_falls_back_to_parent_owner(self, monkeypatch):
        parent = _FakeSession(session_id="parent", owner_email=MICHAEL)
        child = _FakeSession(session_id="bg-child")
        routes = self._patch_common(monkeypatch, parent, child, None)
        routes._handle_background(_make_handler(), {"session_id": "parent", "prompt": "do it"})
        assert child.owner_email == MICHAEL

    def test_background_identity_less_stays_ownerless(self, monkeypatch):
        parent = _FakeSession(session_id="parent", owner_email=None)
        child = _FakeSession(session_id="bg-child")
        routes = self._patch_common(monkeypatch, parent, child, None)
        routes._handle_background(_make_handler(), {"session_id": "parent", "prompt": "do it"})
        assert child.owner_email is None
