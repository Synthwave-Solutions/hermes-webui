"""Personal inline counts do not grant access to the skill catalogue."""
import pytest

from api.governance.catalog import route_permission


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_personal_skill_activity_requires_only_existing_chat_access(method):
    assert route_permission("/api/skills/learning-activity", method) == "chat:use"


@pytest.mark.parametrize("path", [
    "/api/skills", "/api/skills/learning-activity/export", "/api/skills/save",
])
def test_personal_activity_exception_does_not_open_other_skill_routes(path):
    assert route_permission(path, "GET") == "skills:read"
    assert route_permission(path, "POST") == "skills:write"


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_personal_activity_exception_does_not_grant_skill_write_access(method):
    assert route_permission("/api/skills/learning-activity", method) == "skills:write"
