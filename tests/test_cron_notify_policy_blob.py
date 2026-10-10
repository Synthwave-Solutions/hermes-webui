"""The WebUI's notify policy is a byte copy of the engine's (plan 3.1, Appendix A).

``cron/notify_policy.py`` in the engine is the only place that decides who is
notified about a scheduled run. The WebUI ships a byte-identical copy,
``api/_notify_policy_fallback.py``, for engines that do not have it yet, and
``api/cron_notifications.notify_policy()`` uses the engine module first and
the copy second. The sha256 in ``tests/fixtures/managed_service/
notify_policy.sha256`` pins both: the copy always, the engine module whenever
the configured agent directory has one (for example an integration run with
``HERMES_WEBUI_AGENT_DIR`` pointing at the engine branch).
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FALLBACK = REPO / "api" / "_notify_policy_fallback.py"
PIN_FILE = REPO / "tests" / "fixtures" / "managed_service" / "notify_policy.sha256"

POLICY_FUNCTIONS = (
    "normalize_notify",
    "resolve_notify",
    "default_notify_for_new_job",
    "should_deliver",
    "in_app_flags",
    "combine_flags",
    "legacy_toast_value",
    "normalize_managed_by",
)


def _pinned_digest() -> str:
    digest, name = PIN_FILE.read_text(encoding="utf-8").split()[:2]
    assert name == "cron/notify_policy.py"
    assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
    return digest


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _engine_policy_file() -> Path | None:
    from api import config

    agent_dir = getattr(config, "_AGENT_DIR", None)
    if not agent_dir:
        return None
    path = Path(agent_dir) / "cron" / "notify_policy.py"
    return path if path.is_file() else None


def _fake_policy_module(name="cron.notify_policy", *, missing=()):
    from api import _notify_policy_fallback as fallback

    module = types.ModuleType(name)
    for attr in POLICY_FUNCTIONS + ("LEVELS_IN_APP", "LEVELS_DELIVERY", "ALERT_KINDS", "OUTCOME_MUTED"):
        if attr not in missing:
            setattr(module, attr, getattr(fallback, attr))
    return module


def test_fallback_copy_matches_the_pinned_engine_hash():
    assert _sha256(FALLBACK) == _pinned_digest()


def test_engine_module_matches_the_pin_when_the_agent_dir_has_it():
    path = _engine_policy_file()
    if path is None:
        pytest.skip("the configured engine has no cron/notify_policy.py (engine before Z-ENGINE)")
    assert _sha256(path) == _pinned_digest()
    # And it loads on its own (standard library only) with the full surface.
    spec = importlib.util.spec_from_file_location("_w1_engine_notify_policy_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in POLICY_FUNCTIONS:
        assert callable(getattr(module, name)), name
    assert module.OUTCOME_MUTED == "suppressed_muted"


def test_fallback_exposes_the_appendix_a_contract():
    from api import _notify_policy_fallback as policy

    for name in POLICY_FUNCTIONS:
        assert callable(getattr(policy, name)), name
    assert policy.LEVELS_IN_APP == ("all", "failures", "quiet", "off")
    assert policy.LEVELS_DELIVERY == ("all", "failures", "off")
    assert policy.UI_IN_APP_CHOICES == ("all", "failures", "quiet")
    assert policy.ALERT_KINDS == ("failure", "blocked_config", "drift", "preflight")
    assert policy.OUTCOME_MUTED == "suppressed_muted"
    assert policy.MANAGED_BY == ("synthwave", "client")


def test_notify_policy_prefers_the_engine_module(monkeypatch):
    from api import cron_notifications as cn

    engine = _fake_policy_module()
    monkeypatch.setitem(sys.modules, "cron.notify_policy", engine)
    assert cn.notify_policy() is engine
    # The delivery bridge thread never imports the engine, but it uses an
    # engine module that is already loaded.
    assert cn.notify_policy(import_engine=False) is engine


def test_notify_policy_falls_back_when_the_engine_has_no_policy(monkeypatch):
    from api import _notify_policy_fallback as fallback
    from api import cron_notifications as cn

    cron_pkg = types.ModuleType("cron")
    cron_pkg.__path__ = []  # a package without notify_policy (the live engine today)
    monkeypatch.setitem(sys.modules, "cron", cron_pkg)
    monkeypatch.delitem(sys.modules, "cron.notify_policy", raising=False)
    assert cn.notify_policy() is fallback


def test_notify_policy_falls_back_when_the_engine_module_is_incomplete(monkeypatch):
    from api import _notify_policy_fallback as fallback
    from api import cron_notifications as cn

    monkeypatch.setitem(sys.modules, "cron.notify_policy", _fake_policy_module(missing=("should_deliver",)))
    assert cn.notify_policy() is fallback


def test_notify_policy_for_the_bridge_never_imports_the_engine(monkeypatch):
    import importlib

    from api import _notify_policy_fallback as fallback
    from api import cron_notifications as cn

    monkeypatch.delitem(sys.modules, "cron.notify_policy", raising=False)

    def _no_import(name, *args, **kwargs):
        raise AssertionError(f"imported {name}")

    monkeypatch.setattr(importlib, "import_module", _no_import)
    assert cn.notify_policy(import_engine=False) is fallback
