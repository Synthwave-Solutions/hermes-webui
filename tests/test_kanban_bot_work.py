"""Bot page work views over the real Hermes Kanban store (kanban_db):
open tasks of one bot, its recent attachments and a contained download."""
from __future__ import annotations

import io
import os
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

kb = pytest.importorskip("hermes_cli.kanban_db")
from api import kanban_bridge


@pytest.fixture
def board(tmp_path, monkeypatch):
    for name in ("HERMES_KANBAN_DB", "HERMES_KANBAN_BOARD", "HERMES_KANBAN_ATTACHMENTS_ROOT",
                 "HERMES_KANBAN_WORKSPACES_ROOT", "HERMES_KANBAN_TASK"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path / "kh"))
    # Some engine builds keep connect/connect_closing in kanban_db_connect only.
    if not hasattr(kb, "connect_closing"):
        from hermes_cli import kanban_db_connect
        monkeypatch.setattr(kb, "connect_closing", kanban_db_connect.connect_closing, raising=False)
        monkeypatch.setattr(kb, "connect", kanban_db_connect.connect, raising=False)
    kb.init_db()
    with kb.connect_closing() as conn:
        ids = {}
        for key, title, assignee in (("open", "Open work", "cfo"), ("done", "Done work", "cfo"),
                                     ("other", "Other bot", "coo"), ("block", "Needs Michael", "cfo")):
            ids[key] = kb.create_task(conn, title=title, assignee=assignee, created_by="ada@example.test")
        kb.complete_task(conn, ids["done"], result="ok")
        kb.block_task(conn, ids["block"], reason="please log in", kind="needs_input")
        kb.store_attachment_bytes(conn, ids["done"], "report.md", b"# report")
        kb.store_attachment_bytes(conn, ids["other"], "secret.txt", b"not yours")
    return ids


def test_bot_work_lists_open_tasks_and_recent_attachments(board):
    data = kanban_bridge.bot_work_payload("cfo")
    assert {t["title"] for t in data["tasks"]} == {"Open work", "Needs Michael"}
    blocked = next(t for t in data["tasks"] if t["id"] == board["block"])
    assert blocked["status"] == "blocked" and blocked["block_kind"] == "needs_input"
    assert [(a["filename"], a["task_title"]) for a in data["attachments"]] == [("report.md", "Done work")]
    assert kanban_bridge.bot_work_payload("nobody") == {"profile": "nobody", "board": None, "tasks": [], "attachments": []}
    with pytest.raises(ValueError):
        kanban_bridge.bot_work_payload("")


def test_attachment_file_is_contained_to_the_attachments_root(board, tmp_path):
    att = kanban_bridge.bot_work_payload("cfo")["attachments"][0]
    target, root, name, _ctype, assignee = kanban_bridge.attachment_file(att["id"])
    assert target.read_bytes() == b"# report" and target.is_relative_to(root)
    assert (name, assignee) == ("report.md", "cfo")
    for bad in ("x", "0", "-1", "../1", None):
        with pytest.raises(ValueError):
            kanban_bridge.attachment_file(bad)
    with pytest.raises(LookupError):
        kanban_bridge.attachment_file(99999)
    # A row pointing outside the root, or through a symlink, is refused.
    outside = tmp_path / "outside.txt"; outside.write_text("x")
    link = kb.attachments_root() / board["open"] / "link.txt"
    link.parent.mkdir(parents=True, exist_ok=True); link.symlink_to(outside)
    with kb.connect_closing() as conn:
        far = kb.add_attachment(conn, board["open"], filename="outside.txt", stored_path=str(outside))
        via = kb.add_attachment(conn, board["open"], filename="link.txt", stored_path=str(link))
        gone = kb.add_attachment(conn, board["open"], filename="gone.txt",
                                 stored_path=str(kb.attachments_root() / board["open"] / "gone.txt"))
    for att_id in (far, via):
        with pytest.raises(ValueError):
            kanban_bridge.attachment_file(att_id)
    with pytest.raises(LookupError):
        kanban_bridge.attachment_file(gone)


class _Handler:
    def __init__(self, path):
        self.path = path
        self.headers = {}
        self.client_address = ("127.0.0.1", 1)
        self.wfile = io.BytesIO()
        self.status = None
        self.sent = {}

    def send_response(self, code, *a):
        self.status = code

    def send_header(self, k, v):
        self.sent[k] = v

    def end_headers(self):
        pass


def _routes(monkeypatch, allowed):
    from api import routes
    monkeypatch.setattr(routes, "_chat_profile_target_allowed", lambda handler, name: name in allowed)
    return routes


def test_routes_gate_on_the_bot_and_download_as_attachment(board, monkeypatch):
    routes = _routes(monkeypatch, {"cfo"})
    h = _Handler("/api/kanban/bot-work?profile=coo")
    routes._handle_kanban_bot_work(h, urlparse(h.path))
    assert h.status == 404
    h = _Handler("/api/kanban/bot-work?profile=cfo")
    routes._handle_kanban_bot_work(h, urlparse(h.path))
    assert h.status == 200 and b"Needs Michael" in h.wfile.getvalue()
    mine = kanban_bridge.bot_work_payload("cfo")["attachments"][0]["id"]
    h = _Handler(f"/api/kanban/attachment?id={mine}")
    routes._handle_kanban_attachment(h, urlparse(h.path))
    assert h.status == 200 and h.wfile.getvalue().endswith(b"# report")
    assert h.sent["Content-Disposition"].startswith("attachment;")
    theirs = kanban_bridge.bot_work_payload("coo")["attachments"][0]["id"]
    h = _Handler(f"/api/kanban/attachment?id={theirs}")
    routes._handle_kanban_attachment(h, urlparse(h.path))
    assert h.status == 404 and b"not yours" not in h.wfile.getvalue()
