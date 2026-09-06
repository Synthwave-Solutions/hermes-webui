from types import SimpleNamespace
from unittest.mock import patch
import pytest
from api import personal_context as pc

ALICE = {"email": "alice@example.test"}
BOB = {"email": "bob@example.test"}
ADMIN = {"email": "admin@example.test", "groups": ["admins"]}

@pytest.fixture(autouse=True)
def state(tmp_path, monkeypatch):
    monkeypatch.setattr("api.config.STATE_DIR", tmp_path)


def test_personal_files_never_share_by_bot_or_admin():
    for section in ("memory", "user", "soul", "project_context"):
        pc.write(ALICE, section, "ALICE_PRIVATE_" + section)
        assert pc.read(BOB)[section] == ""
        assert pc.read(ADMIN)[section] == ""
        assert pc.read(ALICE)[section] == "ALICE_PRIVATE_" + section


def test_actor_normalization_and_invalid_identity():
    assert pc.home(ALICE) == pc.home({"email":" ALICE@example.test "})
    for identity in (None, {}, {"email": "../alice"}):
        with pytest.raises(PermissionError):
            pc.read(identity)


def test_project_notes_are_actor_and_project_scoped():
    a = SimpleNamespace(project_id="a", workspace="/a")
    b = SimpleNamespace(project_id="b", workspace="/b")
    pc.write(ALICE, "project_context", "PROJECT_A_PRIVATE", a)
    assert pc.read(ALICE, b)["project_context"] == ""
    assert pc.read(BOB, a)["project_context"] == ""
    assert pc.read(ALICE)["project_context"] == ""
    assert "PROJECT_A_PRIVATE" in pc.prompt_overlay(ALICE, a)


def test_no_implicit_workspace_or_shared_legacy_import(tmp_path):
    (tmp_path / "SOUL.md").write_text("BOT_PRIVATE_LEGACY")
    assert pc.read(ALICE)["soul"] == ""
    assert pc.shared_project_context(ALICE, None)["content"] == ""


def test_file_and_parent_symlinks_fail_closed(tmp_path):
    outside = tmp_path / "outside"
    outside.write_text("SECRET")
    target = pc.paths(ALICE)["soul"]
    target.parent.mkdir(parents=True)
    target.symlink_to(outside)
    with pytest.raises(PermissionError):
        pc.read(ALICE)
    with pytest.raises(PermissionError):
        pc.write(ALICE, "soul", "OVERWRITE")
    assert outside.read_text() == "SECRET"
    target.unlink()
    target.parent.rmdir()
    target.parent.symlink_to(tmp_path)
    with pytest.raises(PermissionError):
        pc.read(ALICE)


def test_section_traversal_and_large_content_rejected():
    with pytest.raises(ValueError):
        pc.write(ALICE, "../../USER.md", "bad")
    with pytest.raises(ValueError):
        pc.write(ALICE, "memory", "x" * (128 * 1024 + 1))


def test_session_membership_checked_even_for_selected_foreign_session():
    foreign = SimpleNamespace(owner_email=BOB["email"], participants=[])
    with patch("api.models.get_session", return_value=foreign), patch(
        "api.group_chat.require_turn_membership", side_effect=PermissionError("foreign")
    ) as check:
        with pytest.raises(PermissionError):
            pc.session_for(ALICE, "foreign")
        check.assert_called_once_with(foreign, ALICE)


def test_routes_ignore_actor_profile_and_path_overrides():
    from api import routes
    response = {}
    def capture(handler, value):
        response.update(value)
    with patch("api.governance.enforce._request_identity", return_value=ALICE), patch.object(routes, "j", capture):
        routes._handle_memory_write(object(), {"section":"soul", "content":"ALICE",
            "email":BOB["email"], "profile":"../../bob", "path":"/tmp/foreign"})
    assert response["scope"] == "personal"
    assert pc.read(ALICE)["soul"] == "ALICE"
    assert pc.read(BOB)["soul"] == ""


def test_shared_scope_is_human_participation_not_bot_count():
    session = SimpleNamespace(owner_email=ALICE["email"], participants=[],
                              bot_participants=["a", "b"], project_shared=False)
    assert not pc.shared_conversation(session)
    session.participants = [BOB["email"]]
    assert pc.shared_conversation(session)
    session.participants = []
    session.project_shared = True
    assert pc.shared_conversation(session)


def test_shared_project_revocation_does_not_read_file(tmp_path):
    from api import project_collaboration as projects
    session = SimpleNamespace(project_shared=True, profile="bot", project_id="project")
    marker = tmp_path / "AGENTS.md"
    marker.write_text("SHARED_ONLY")
    with patch.object(projects, "runtime_file_scope", return_value=(str(tmp_path), lambda p: False)):
        assert pc.shared_project_context(ALICE, session)["content"] == ""
    with patch.object(projects, "runtime_file_scope", return_value=(str(tmp_path), lambda p: True)):
        assert pc.shared_project_context(ALICE, session)["content"] == "SHARED_ONLY"


def test_real_engine_memory_uses_same_api_actor_scope():
    from tools.memory_tool import MemoryStore, bind_personal_memory_dir, reset_personal_memory_dir
    pc.write(ALICE, "memory", "ALICE_PRIVATE")
    token = bind_personal_memory_dir(pc.home(ALICE) / "memories")
    try:
        store = MemoryStore()
        store.load_from_disk()
        assert "ALICE_PRIVATE" in store.format_for_system_prompt("memory")
        store.memory_entries = ["RUNTIME_SAVED"]
    finally:
        reset_personal_memory_dir(token)
    store.save_to_disk("memory")
    assert "RUNTIME_SAVED" in pc.read(ALICE)["memory"]
    assert pc.read(BOB)["memory"] == ""
