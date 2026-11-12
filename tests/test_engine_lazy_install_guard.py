"""The WebUI refuses a policy-forbidden lazy extra install without the engine worker."""
import sys
import types

import pytest


class InstallError(RuntimeError):
    def __init__(self, package, cause, remedy=""):
        self.package, self.cause, self.remedy = package, cause, remedy
        super().__init__(f"{package}: {cause} — {remedy}")


@pytest.fixture
def engine(monkeypatch):
    """A stand-in for the engine's pm package with a recording sync_venv."""
    state = types.SimpleNamespace(installed=set(), allowed=False, calls=[])

    def original_sync_venv(extras=None, *, explicit=False, plugins=None, repair=False, project_root=None):
        state.calls.append((list(extras or []), explicit, repair))

    pm = types.ModuleType("pm")
    pm.__path__ = []
    client = types.ModuleType("pm.client")
    client.sync_venv = original_sync_venv
    extras = types.ModuleType("pm.extras")
    extras.available = lambda extra: extra in state.installed
    install = types.ModuleType("pm.install")
    install.lazy_installs_allowed = lambda: state.allowed
    package = types.ModuleType("pm.package")
    package.InstallError = InstallError
    pm.client, pm.extras, pm.install, pm.package = client, extras, install, package
    for name, module in (("pm", pm), ("pm.client", client), ("pm.extras", extras),
                         ("pm.install", install), ("pm.package", package)):
        monkeypatch.setitem(sys.modules, name, module)
    from api import engine_lazy_install_guard as guard

    monkeypatch.setattr(guard, "_reported", set())
    assert guard.install() is True
    state.client = client
    state.guard = guard
    return state


def test_missing_extra_with_policy_off_is_refused_without_the_worker(engine):
    with pytest.raises(InstallError) as caught:
        engine.client.sync_venv(["fal"])
    assert engine.calls == []
    assert "lazy installs are disabled" in str(caught.value)
    assert "['fal']" in str(caught.value)


def test_policy_on_reaches_the_engine(engine):
    engine.allowed = True
    engine.client.sync_venv(["fal"])
    assert engine.calls == [(["fal"], False, False)]


def test_installed_extra_reaches_the_engine(engine):
    engine.installed.add("fal")
    engine.client.sync_venv(["fal"])
    assert engine.calls == [(["fal"], False, False)]


@pytest.mark.parametrize("kwargs", [{"explicit": True}, {"repair": True}, {"plugins": object()},
                                    {"project_root": "/somewhere"}])
def test_explicit_paths_are_never_short_circuited(engine, kwargs):
    engine.client.sync_venv(["fal"], **kwargs)
    assert len(engine.calls) == 1


def test_sync_without_extras_is_untouched(engine):
    engine.client.sync_venv()
    assert engine.calls == [([], False, False)]


def test_install_is_idempotent(engine):
    wrapped = engine.client.sync_venv
    assert engine.guard.install() is True
    assert engine.client.sync_venv is wrapped


def test_unknown_engine_layout_falls_through(engine, monkeypatch):
    def boom(extra):
        raise RuntimeError("layout changed")

    monkeypatch.setattr(sys.modules["pm.extras"], "available", boom)
    engine.client.sync_venv(["fal"])
    assert engine.calls == [(["fal"], False, False)]


def test_guard_reports_inactive_without_an_engine(monkeypatch):
    from api import engine_lazy_install_guard as guard

    monkeypatch.setitem(sys.modules, "pm", None)
    monkeypatch.setitem(sys.modules, "pm.client", None)
    assert guard.install() is False
