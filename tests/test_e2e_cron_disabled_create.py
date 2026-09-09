"""Input validation for the duplicate-as-paused browser workflow."""
import pytest
from tests.test_cron_model_override import _JSONHandler, _payload


@pytest.mark.parametrize("value", ["false", 0, None, []])
def test_invalid_enabled_is_rejected_before_job_creation(monkeypatch, value):
    from api import routes
    from cron import jobs
    monkeypatch.setattr(jobs, "create_job", lambda **kw: pytest.fail("invalid input created a job"))
    handler = _JSONHandler()
    routes._handle_cron_create(handler, {"prompt": "Invalid duplicate", "schedule": "every 1h", "enabled": value})
    assert handler.status == 400
    assert "enabled must be a boolean" in _payload(handler)["error"]
