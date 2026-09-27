"""Regression test for the memory-write symlinked-target guard (#4242).

`_handle_memory_write` refuses to write through a symlinked target file so a
symlink planted at MEMORY.md / USER.md / SOUL.md (e.g. via a restored or imported
workspace) cannot redirect a memory write to clobber an arbitrary file. This
mirrors the symlink-rejection hardening shipped for skills/plugins
(#4217/#4234/#4240).

SynthPulse (073713d1, 6 Sep 2026, docs/personal-context.md): memory writes go to
the caller's own private directory under STATE_DIR/personal_context, and that
API rejects symlinked target files AND symlinked parent directories. So unlike
upstream, a symlinked memories directory is refused too. A read-only file or
volume still returns an actionable 403 (#4480).
"""

import errno
import os

import pytest

import api.routes as routes
from api import personal_context

IDENTITY = {"email": "writer@example.test"}


class _FakeHandler:
    pass


def _patch_memory_routes(monkeypatch, tmp_path):
    cap = {}
    monkeypatch.setattr("api.config.STATE_DIR", tmp_path / "state")
    monkeypatch.setattr("api.governance.enforce._request_identity", lambda _h: IDENTITY)
    monkeypatch.setattr(routes, "j", lambda h, o: (cap.__setitem__("ok", o), True)[1])
    monkeypatch.setattr(
        routes,
        "bad",
        lambda h, m, c=400: (cap.__setitem__("bad", (m, c)), True)[1],
    )
    return cap


def _target(section):
    return personal_context.paths(IDENTITY)[section]


def test_memory_write_rejects_symlinked_memory_file(tmp_path, monkeypatch):
    cap = _patch_memory_routes(monkeypatch, tmp_path)
    link = _target("memory")
    link.parent.mkdir(parents=True)
    outside = tmp_path / "outside-memory.md"
    outside.write_text("important", encoding="utf-8")
    try:
        os.symlink(str(outside), str(link))
    except (OSError, NotImplementedError):
        pytest.skip("platform does not support symlinks")

    routes._handle_memory_write(
        _FakeHandler(),
        {"section": "memory", "content": "changed"},
    )

    assert "bad" in cap, f"expected a refusal, got {cap}"
    assert cap["bad"][1] == 403
    assert "symlink" in cap["bad"][0]
    # The symlink target outside the memories dir must be untouched.
    assert outside.read_text(encoding="utf-8") == "important"


def _fail_replace_for(monkeypatch, target, exc):
    original_replace = personal_context.os.replace

    def fake_replace(src, dst, *args, **kwargs):
        if str(dst) == str(target):
            raise exc
        return original_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(personal_context.os, "replace", fake_replace)


def test_memory_write_read_only_soul_returns_403(tmp_path, monkeypatch):
    """A read-only SOUL.md write must return an actionable 403, not bubble as 500."""
    cap = _patch_memory_routes(monkeypatch, tmp_path)
    _fail_replace_for(monkeypatch, _target("soul"), PermissionError(errno.EACCES, "read-only test file"))

    routes._handle_memory_write(
        _FakeHandler(),
        {"section": "soul", "content": "# Soul\n"},
    )

    assert "bad" in cap, f"expected 403, got {cap}"
    assert cap["bad"][1] == 403
    assert "SOUL.md" in cap["bad"][0]
    assert "writable" in cap["bad"][0].lower()
    assert "chmod 644" in cap["bad"][0]


def test_memory_write_read_only_filesystem_returns_403(tmp_path, monkeypatch):
    """Docker read-only volume writes can raise EROFS instead of PermissionError."""
    cap = _patch_memory_routes(monkeypatch, tmp_path)
    _fail_replace_for(monkeypatch, _target("soul"), OSError(errno.EROFS, "read-only file system"))

    routes._handle_memory_write(
        _FakeHandler(),
        {"section": "soul", "content": "# Soul\n"},
    )

    assert "bad" in cap, f"expected 403, got {cap}"
    assert cap["bad"][1] == 403
    assert "SOUL.md" in cap["bad"][0]
    assert "chmod 644" in cap["bad"][0]


def test_memory_write_rejects_symlinked_memories_directory(tmp_path, monkeypatch):
    """Upstream allowed a symlinked parent memories directory; the private
    personal-context API refuses it (docs/personal-context.md), so a write can
    never land outside the caller's own directory."""
    cap = _patch_memory_routes(monkeypatch, tmp_path)
    memories = _target("user").parent
    memories.parent.mkdir(parents=True)
    real_dir = tmp_path / "real-memories"
    real_dir.mkdir()
    try:
        os.symlink(str(real_dir), str(memories), target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("platform does not support symlinks")

    routes._handle_memory_write(
        _FakeHandler(),
        {"section": "user", "content": "# User\n"},
    )

    assert "bad" in cap, f"expected a refusal, got {cap}"
    assert cap["bad"][1] == 403
    assert not (real_dir / "USER.md").exists()


def test_memory_write_real_file_still_works(tmp_path, monkeypatch):
    cap = _patch_memory_routes(monkeypatch, tmp_path)
    routes._handle_memory_write(
        _FakeHandler(),
        {"section": "memory", "content": "# Memory\n"},
    )

    target = _target("memory")
    assert "ok" in cap, f"expected success, got {cap}"
    assert cap["ok"]["ok"] is True
    assert cap["ok"]["section"] == "memory"
    assert target.read_text(encoding="utf-8") == "# Memory\n"
