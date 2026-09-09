import copy
import json
from types import SimpleNamespace

import pytest

from api import shares, share_routes, profiles


@pytest.fixture
def scope(tmp_path, monkeypatch):
    from api import config, upload, workspace, bot_builder
    from api.governance import loader, enforce
    identity = {"email": "alice@example.test", "method": "sso", "groups": []}
    handler = SimpleNamespace(identity=identity)
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(shares, "SHARES_DIR", tmp_path / "shares")
    monkeypatch.setattr(upload, "_attachment_root", lambda: tmp_path / "attachments")
    monkeypatch.setattr(enforce, "_request_identity", lambda h: h.identity)
    monkeypatch.setattr(bot_builder, "allowed", lambda *args: None)
    policy = loader.parse_governance_policy({"version": 1, "mode": "enforce", "default_effect": "deny",
        "roles": {"member": {"grants": {"permissions": ["sessions:write"], "routes": ["*"],
             "profiles": ["default", "qa-research"], "workspaces": ["*"],
             "files": {"read_roots": ["*"]}}}},
        "users": {identity["email"]: {"roles": ["member"]}}})
    monkeypatch.setattr(loader, "get_policy", lambda: policy)
    registries = {name: tmp_path / (name + "-workspaces.json") for name in ("default", "qa-research")}
    for registry in registries.values():
        registry.write_text("[]")
    monkeypatch.setattr(workspace, "_workspaces_file", lambda: registries[profiles.get_active_profile_name() or "default"])
    session = SimpleNamespace(session_id="source-chat", title="Synthetic share", profile="default",
        workspace=str(tmp_path), owner_email=identity["email"], participants=[], project_shared=False,
        messages=[{"role": "user", "content": "Safe visible text"}], share_token=None, share_created_at=None)
    yield SimpleNamespace(root=tmp_path, handler=handler, session=session, registries=registries)
    profiles.clear_request_profile()


@pytest.mark.parametrize("method,path,expected", [
    ("GET", "/share/" + "a" * 24, True), ("GET", "/api/share/" + "a" * 24, True),
    ("POST", "/api/share/" + "a" * 24, False), ("GET", "/api/share/create", False),
    ("GET", "/api/share/revoke", False), ("GET", "/api/share/../create", False),
    ("GET", "/share/" + "a" * 25, False), ("GET", "/share/" + "a" * 24 + "/extra", False),
])
def test_only_exact_read_only_tokens_are_public(method, path, expected):
    assert share_routes.is_public_share_request(path, method) is expected


def test_foreign_imported_token_cannot_replace_or_revoke_snapshot(scope):
    meta = shares.create_or_refresh_share(scope.session)
    other = copy.copy(scope.session)
    other.session_id = "different-chat"
    other.share_token = meta["share_token"]
    other.messages = [{"role": "user", "content": "FOREIGN_REPLACEMENT"}]
    for action in (shares.create_or_refresh_share, shares.revoke_share):
        with pytest.raises(ValueError, match="does not belong"):
            action(other)
    assert "FOREIGN_REPLACEMENT" not in json.dumps(shares.load_share(meta["share_token"]))


def test_revoked_token_in_stale_metadata_never_becomes_public_again(scope):
    meta = shares.create_or_refresh_share(scope.session)
    scope.session.share_token = meta["share_token"]
    shares.revoke_share(scope.session)
    newer = shares.create_or_refresh_share(scope.session)
    assert newer["share_token"] != meta["share_token"]
    assert shares.load_share(meta["share_token"]) is None
    assert shares.load_share(newer["share_token"]) is not None


def test_foreign_attachments_and_personal_images_never_enter_public_payload(scope):
    from api.personal_context import home
    from api.upload import _session_attachment_dir
    own = _session_attachment_dir(scope.session.session_id) / "own.png"
    foreign_attachment = _session_attachment_dir("other-chat") / "foreign.png"
    foreign_personal = home({"email": "bob@example.test"}) / "private.png"
    data = b"\x89PNG\r\n\x1a\nSYNTHETIC_PRIVATE_IMAGE"
    for image in (own, foreign_attachment, foreign_personal):
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(data)
    scope.session.messages = [{"role": "user", "content": " ".join("MEDIA:" + str(p) for p in (own, foreign_attachment, foreign_personal))}]
    with share_routes._source_scope(scope.handler, scope.session):
        meta = shares.create_or_refresh_share(scope.session,
            media_access_check=lambda p: share_routes._check_media_access(scope.handler, scope.session, p))
    content = shares.load_share(meta["share_token"])["messages"][0]["content"]
    assert content.count("data:image/png;base64,") == 1  # Only source-session image.
    assert content.count(shares._PLACEHOLDER) == 2
    assert "foreign.png" not in content and "private.png" not in content


def test_source_profile_acl_applies_and_request_profile_is_restored(scope):
    scope.session.profile = "qa-research"
    scope.registries["qa-research"].write_text(json.dumps([
        {"path": scope.session.workspace, "owner_email": "bob@example.test", "members": []}]))
    profiles.set_request_profile("default")
    with pytest.raises(PermissionError, match="Workspace membership"):
        with share_routes._source_scope(scope.handler, scope.session):
            pytest.fail("Publishing must not reach the source snapshot")
    assert profiles.get_active_profile_name() == "default"
    assert not shares.SHARES_DIR.exists()


def test_failed_source_metadata_save_revokes_newly_published_snapshot(scope, monkeypatch):
    monkeypatch.setattr(share_routes, "_session_pair", lambda *args: (scope.session, scope.session))
    def fail(**kwargs):
        raise OSError("synthetic disk failure")
    scope.session.save = fail
    with pytest.raises(OSError, match="synthetic disk failure"):
        share_routes.handle_mutation(scope.handler, {"session_id": scope.session.session_id})
    assert scope.session.share_token is None
    for file in shares.SHARES_DIR.glob("*.json"):
        assert shares.load_share(file.stem) is None
