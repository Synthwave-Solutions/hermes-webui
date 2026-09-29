"""Concrete file paths and actual list/ZIP output respect retained denials."""
from io import BytesIO
from types import SimpleNamespace
from urllib.parse import urlparse
import zipfile

import pytest

from api import routes
from api.governance import loader
from api.governance.loader import parse_governance_policy
from api.governance.resource_access import ensure_file_access
from api.personal_file_guard import guard_request


@pytest.fixture
def files(tmp_path, monkeypatch):
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "secret.txt").write_text("private-content")
    (tmp_path / "allowed.txt").write_text("public-content")
    (tmp_path / "shortcut.txt").symlink_to(tmp_path / "private" / "secret.txt")
    who = {"email": "alice@example.test"}
    policy = parse_governance_policy({"mode": "enforce", "roles": {"member": {"grants": {
        "files": {"read_roots": [str(tmp_path)], "write_roots": [str(tmp_path)]}}}},
        "users": {who["email"]: {"roles": ["member"], "access_mode": "blacklist", "access_level": "user",
            "deny": {"files": {"read_roots": [str(tmp_path / "private")], "write_roots": [str(tmp_path / "private")]}}}}})
    monkeypatch.setattr(loader, "get_policy", lambda: policy)
    monkeypatch.setattr("api.governance.enforce._request_identity", lambda h: who)
    session = SimpleNamespace(workspace=str(tmp_path), owner_email=who["email"], participants=[], project_shared=False)
    monkeypatch.setattr(routes, "get_session", lambda sid: session)
    monkeypatch.setattr(routes, "get_session_for_file_ops", lambda sid: session)
    monkeypatch.setattr("api.personal_context.ensure_actor_path", lambda *a: None)
    return tmp_path, who


def test_direct_path_and_symlink_guards_deny_before_file_handlers(files):
    root, who = files
    ensure_file_access(who, root / "allowed.txt")
    for path in ("private/secret.txt", "shortcut.txt"):
        for route in ("/api/file", "/api/file/save", "/api/file/delete"):
            with pytest.raises(PermissionError):
                guard_request(object(), route, {"session_id": "s", "path": path})


def test_actual_list_hides_denied_children_and_symlinks(files, monkeypatch):
    monkeypatch.setattr(routes, "j", lambda h, data, status=200: data)
    result = routes._handle_list_dir(object(), urlparse("/api/list?session_id=s&path=."))
    assert [entry["name"] for entry in result["entries"]] == ["allowed.txt"]


def test_actual_zip_cannot_include_denied_descendant_or_symlink(files):
    class Handler:
        def __init__(self):
            self.wfile = BytesIO()
            self.headers = {}
        def send_response(self, status):
            self.status = status
        def send_header(self, key, value):
            self.headers[key] = value
        def end_headers(self):
            pass
    handler = Handler()
    routes._handle_folder_download(handler, urlparse("/api/folder/download?session_id=s&path=."))
    assert handler.status == 200
    with zipfile.ZipFile(BytesIO(handler.wfile.getvalue())) as archive:
        assert archive.namelist() == ["allowed.txt"]
        assert archive.read("allowed.txt") == b"public-content"
