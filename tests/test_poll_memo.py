"""Polled read-only answers are replayed per browser session and dropped on writes."""
import io
from types import SimpleNamespace as NS
from urllib.parse import urlparse

from api import poll_memo
from api.helpers import j


class Handler:
    def __init__(self, path, cookie="sid=a", command="GET"):
        self.path = path
        self.command = command
        self.headers = {"Cookie": cookie} if cookie else {}
        self.wfile = io.BytesIO()
        self.sent = []

    def send_response(self, status):
        self.sent.append(status)

    def send_header(self, *a):
        pass

    def end_headers(self):
        pass


def _get(path, cookie="sid=a", build=lambda: {"n": 1}):
    h = Handler(path, cookie)
    if poll_memo.serve(h, urlparse(path)):
        return h, True
    j(h, build())
    return h, False


def setup_function(_):
    poll_memo.invalidate("/api/anything")


def test_second_poll_is_replayed_for_same_session_only():
    path = "/api/kanban/waiting?board=x"
    first, hit = _get(path)
    assert not hit
    again, hit = _get(path, build=lambda: {"n": 2})
    assert hit and again.wfile.getvalue() == first.wfile.getvalue()
    _, hit = _get(path, cookie="sid=b")
    assert not hit
    _, hit = _get("/api/kanban/waiting?board=y")
    assert not hit


def test_other_paths_and_anonymous_requests_are_never_memoized():
    assert _get("/api/sessions")[1] is False and _get("/api/sessions")[1] is False
    path = "/api/governance/approvals"
    assert _get(path, cookie="")[1] is False and _get(path, cookie="")[1] is False


def test_write_drops_answers_but_quiet_writes_do_not():
    path = "/api/governance/approvals"
    _get(path)
    poll_memo.invalidate("/api/session/draft")
    assert _get(path)[1] is True
    poll_memo.invalidate("/api/approval/respond")
    assert _get(path)[1] is False


def test_answer_built_across_a_write_is_not_kept():
    path = "/api/governance/approvals"
    h = Handler(path)
    assert poll_memo.serve(h, urlparse(path)) is False
    poll_memo.invalidate("/api/approval/respond")
    j(h, {"n": 1})
    assert _get(path)[1] is False


def test_errors_and_reused_connections_are_not_captured():
    path = "/api/governance/approvals"
    h = Handler(path)
    poll_memo.serve(h, urlparse(path))
    j(h, {"error": "x"}, status=500)
    assert _get(path)[1] is False
    poll_memo.invalidate("/x")
    h = Handler(path)
    poll_memo.serve(h, urlparse(path))
    h.command, h.path = "POST", "/api/other"
    j(h, {"n": 9})
    assert _get(path, build=lambda: {"n": 1})[1] is False
