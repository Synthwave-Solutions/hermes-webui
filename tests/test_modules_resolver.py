"""The module resolver and the module gate are fail safe (program plan 3.7,
Appendix E.4.2).

``SP_ENABLED_MODULES`` is the only source; unset, empty or unparsable gives
the Standard set; ``*`` counts only at HQ; unknown ids and modules with a
missing requirement are dropped; any exception while resolving gives the
Standard set, and then every Advanced route prefix answers 403 through the
``api/synthpulse_server.py`` wrapper and nothing answers 500 or passes. The
WebUI registry is pinned to the byte copy of the stack catalogue.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import modules  # noqa: E402
from api.governance import loader  # noqa: E402
from api.governance.catalog import _SELF_ROUTES, ROUTE_CATALOG  # noqa: E402
from api.governance.loader import parse_governance_policy  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures" / "managed_service"
CATALOG = json.loads((FIXTURES / "module_catalog.json").read_text(encoding="utf-8"))

STANDARD = ("workspace", "group_chat", "design_studio", "workflows")
ADVANCED_PREFIXES = {
    "knowledge_base": "/api/knowledge/",
    "notebook": "/api/notebook/",
    "e_signing": "/api/signing/",
    "dictation": "/api/dictation/",
    "meeting_notes": "/api/meetings/",
    "office_apps": "/api/office-apps/",
}
CLIENT_POLICY = {"version": 1, "mode": "off"}
HQ_POLICY = {"version": 1, "mode": "off", "installation": {"kind": "hq"}}
MEMBER = "member@example.test"
ENFORCE_POLICY = {
    "version": 1,
    "mode": "enforce",
    "default_effect": "deny",
    "bootstrap_admins": ["boot@example.test"],
    "roles": {"member": {"grants": {"permissions": ["chat:use", "sessions:read", "config:read"],
                                    "profiles": ["*"], "routes": ["*"]}}},
    "users": {MEMBER: {"roles": ["member"]}},
}


class _Handler:
    def __init__(self):
        self.status = None
        self.headers = {}
        self.response_headers = []
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.response_headers.append((key, value))

    def end_headers(self):
        pass

    @property
    def body(self):
        return json.loads(self.wfile.getvalue().decode("utf-8"))


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    monkeypatch.delenv("SP_ENABLED_MODULES", raising=False)
    modules.clear_cache()
    yield
    modules.clear_cache()
    loader.set_policy_loader(None)


def _use_policy(data):
    policy = parse_governance_policy(data)
    loader.set_policy_loader(lambda: policy)
    modules.clear_cache()
    return policy


def _state(value, policy=CLIENT_POLICY):
    env = {} if value is None else {"SP_ENABLED_MODULES": value}
    return modules.resolve(policy, env)


# ── The registry equals the pinned catalogue ─────────────────────────────────

def test_catalogue_fixture_matches_its_pin():
    data = (FIXTURES / "module_catalog.json").read_bytes()
    pin = (FIXTURES / "module_catalog.sha256").read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(data).hexdigest() == pin


def test_registry_ids_tiers_and_requirements_equal_the_catalogue():
    rows = CATALOG["modules"]
    assert len(rows) == 10 and len(modules.MODULE_IDS) == 10
    assert modules.MODULE_IDS == tuple(row["id"] for row in rows)
    for row in rows:
        spec = modules.REGISTRY[row["id"]]
        assert spec.tier == row["tier"], row["id"]
        assert spec.requires == tuple(row["requires"]), row["id"]
        assert spec.app_tile == row["app_link"], row["id"]
    assert modules.STANDARD_IDS == STANDARD
    assert modules.STANDARD_IDS == tuple(row["id"] for row in rows if row["tier"] == "standard")


def test_shared_lists_equal_the_catalogue():
    assert list(modules.DISPLAY_DENYLIST) == CATALOG["display_denylist"]
    assert list(modules.UNAVAILABLE_REASONS) == [r["code"] for r in CATALOG["unavailable_reasons"]]


def test_route_prefixes_panels_and_tiles_are_the_plan_names():
    for module_id, prefix in ADVANCED_PREFIXES.items():
        assert modules.REGISTRY[module_id].route_prefixes == (prefix,), module_id
    assert modules.REGISTRY["knowledge_base"].panels == ("knowledge",)
    assert modules.REGISTRY["meeting_notes"].panels == ("meetings",)
    for module_id in STANDARD:
        assert modules.REGISTRY[module_id].route_prefixes == (), module_id
    names = " ".join(str(v) for spec in modules.REGISTRY.values()
                     for v in (spec.panels, spec.route_prefixes, spec.app_tile, spec.settings_sections,
                               spec.composer_controls, spec.help_pages)).lower()
    for denied in modules.DISPLAY_DENYLIST:
        assert denied.lower() not in names, denied


# ── The fail-safe matrix ─────────────────────────────────────────────────────

@pytest.mark.parametrize("value,source", [
    (None, "default"),
    ("", "default"),
    ("   ", "default"),
    (" , ,", "default"),
])
def test_unset_or_empty_gives_the_standard_set(value, source):
    assert _state(value) == modules.ModuleState(STANDARD, source)


@pytest.mark.parametrize("value", [
    "Knowledge_Base", "knowledge-base", "knowledge_base;rm -rf", "kb", "workspace,Bad Id",
    "*x", "knowledge_base,,**", "été_module",
])
def test_garbage_gives_the_standard_set(value):
    assert _state(value) == modules.ModuleState(STANDARD, "invalid")


def test_one_advanced_module_adds_it_to_the_standard_set():
    assert _state("knowledge_base") == modules.ModuleState(STANDARD + ("knowledge_base",), "env")
    assert _state(" meeting_notes , notebook ,notebook") == modules.ModuleState(
        STANDARD + ("notebook", "meeting_notes"), "env")


def test_standard_is_always_present():
    assert _state("workspace").active == STANDARD
    assert _state("group_chat,e_signing").active == STANDARD + ("e_signing",)


def test_wildcard_on_a_client_gives_the_standard_set_only():
    for policy in (CLIENT_POLICY, {"installation": {"kind": "client"}}, {"installation": "hq"}, None, "junk"):
        assert _state("*", policy).active == STANDARD, policy
    assert _state("*,dictation").active == STANDARD + ("dictation",)


def test_wildcard_at_hq_gives_every_module():
    assert _state("*", HQ_POLICY) == modules.ModuleState(modules.MODULE_IDS, "hq")
    assert _state(" * ", {"installation": {"kind": " HQ "}}).source == "hq"


def test_unknown_ids_are_dropped_and_logged_once(caplog):
    caplog.set_level("WARNING", logger="api.modules")
    modules._LOGGED.discard("unknown:crm_suite")
    for _ in range(3):
        assert _state("crm_suite,notebook").active == STANDARD + ("notebook",)
    assert sum("crm_suite" in record.getMessage() for record in caplog.records) == 1


def test_a_module_whose_requirement_is_missing_is_dropped(monkeypatch):
    addon = modules.ModuleSpec("fake_addon", modules.ADVANCED, requires=("notebook",),
                               route_prefixes=("/api/fake-addon/",))
    registry = dict(modules.REGISTRY, fake_addon=addon)
    monkeypatch.setattr(modules, "REGISTRY", registry)
    monkeypatch.setattr(modules, "MODULE_IDS", tuple(registry))
    assert _state("fake_addon").active == STANDARD
    assert _state("fake_addon,notebook").active == STANDARD + ("notebook", "fake_addon")


def test_an_exception_inside_resolution_gives_the_standard_set(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("registry broken")

    monkeypatch.setattr(modules, "_parse_env", boom)
    assert _state("knowledge_base") == modules.ModuleState(STANDARD, "invalid")
    assert _state("*", HQ_POLICY) == modules.ModuleState(STANDARD, "invalid")


def test_the_source_is_the_env_only(monkeypatch):
    policy = dict(HQ_POLICY, modules=["knowledge_base"], enabled_modules=["notebook"])
    _use_policy(policy)
    assert modules.current_state().active == STANDARD
    monkeypatch.setenv("SP_ENABLED_MODULES", "e_signing")
    assert modules.current_state().active == STANDARD + ("e_signing",)


def test_current_state_follows_the_env_and_the_installation_kind(monkeypatch):
    _use_policy(CLIENT_POLICY)
    monkeypatch.setenv("SP_ENABLED_MODULES", "*")
    assert modules.current_state() == modules.ModuleState(STANDARD, "env")
    _use_policy(HQ_POLICY)
    assert modules.current_state() == modules.ModuleState(modules.MODULE_IDS, "hq")
    monkeypatch.setenv("SP_ENABLED_MODULES", "notebook")
    assert modules.current_state().active == STANDARD + ("notebook",)
    assert modules.module_active("notebook") and not modules.module_active("dictation")
    assert modules.module_active("workspace")


def test_an_unreadable_policy_gives_the_standard_set(monkeypatch):
    def broken():
        raise loader.GovernancePolicyError("invalid YAML")

    loader.set_policy_loader(broken)
    monkeypatch.setenv("SP_ENABLED_MODULES", "knowledge_base")
    assert modules.current_state() == modules.ModuleState(STANDARD, "invalid")


# ── Navigation view ──────────────────────────────────────────────────────────

def test_nav_view_hides_inactive_module_panels_and_offers_active_tiles():
    view = modules.nav_view(_state(None))
    assert view == {
        "hidden_panels": ["knowledge", "meetings"],
        "hidden_settings_sections": [],
        "hidden_composer_controls": [],
        "apps": [{"module": "design_studio", "app": "design"}, {"module": "workflows", "app": "workflows"}],
    }
    everything = modules.nav_view(_state("*", HQ_POLICY))
    assert everything["hidden_panels"] == []
    assert not any(tile["module"] == "office_apps" for tile in everything["apps"])
    assert [tile["app"] for tile in everything["apps"]] == ["design", "workflows", "notebook", "sign"]


# ── The gate ─────────────────────────────────────────────────────────────────

def _gate(path, method="GET"):
    import api.synthpulse_server as synthpulse_server

    handler = _Handler()
    proceed = synthpulse_server.enforce_request(handler, urlparse("http://localhost" + path), method)
    return proceed, handler


@pytest.mark.parametrize("module_id,prefix", sorted(ADVANCED_PREFIXES.items()))
def test_gate_answers_403_on_an_inactive_module_route(module_id, prefix):
    _use_policy(CLIENT_POLICY)
    for path in (prefix + "fake", prefix, prefix.rstrip("/")):
        for method in ("GET", "POST", "DELETE"):
            proceed, handler = _gate(path, method)
            assert proceed is False, (path, method)
            assert handler.status == 403 and handler.body == {"error": "module_inactive", "module": module_id}


def test_gate_lets_an_active_module_route_through(monkeypatch):
    _use_policy(CLIENT_POLICY)
    monkeypatch.setenv("SP_ENABLED_MODULES", "knowledge_base")
    proceed, handler = _gate("/api/knowledge/fake")
    assert proceed is True and handler.status is None
    proceed, handler = _gate("/api/notebook/fake")
    assert proceed is False and handler.body["module"] == "notebook"


@pytest.mark.parametrize("module_id,path", [("knowledge_base", "/api/knowledge/fake"),
                                             ("office_apps", "/api/office-apps/fake")])
def test_gate_through_a_fake_route_on_the_real_dispatcher(monkeypatch, module_id, path):
    """A route M1 or O4 would add is reached only once its module is active."""
    import api.routes as routes

    _use_policy(CLIENT_POLICY)
    real_get = routes.handle_get
    seen = []

    def with_fake_route(handler, parsed):
        if parsed.path == path:
            seen.append(parsed.path)
            handler.send_response(200)
            return True
        return real_get(handler, parsed)

    monkeypatch.setattr(routes, "handle_get", with_fake_route)

    def request():
        proceed, handler = _gate(path)
        if proceed:
            routes.handle_get(handler, urlparse("http://localhost" + path))
        return handler

    handler = request()
    assert handler.status == 403 and seen == []
    assert handler.body == {"error": "module_inactive", "module": module_id}
    monkeypatch.setenv("SP_ENABLED_MODULES", module_id)
    assert request().status == 200 and seen == [path]


def test_an_exception_inside_resolution_closes_every_advanced_prefix(monkeypatch):
    _use_policy(HQ_POLICY)
    monkeypatch.setenv("SP_ENABLED_MODULES", "*")

    def boom(*_args, **_kwargs):
        raise RuntimeError("registry broken")

    monkeypatch.setattr(modules, "_resolve", boom)
    for module_id, prefix in ADVANCED_PREFIXES.items():
        proceed, handler = _gate(prefix + "x")
        assert proceed is False and handler.status == 403, module_id
        assert handler.body == {"error": "module_inactive", "module": module_id}
    proceed, handler = _gate("/api/settings")
    assert proceed is True and handler.status is None


def test_a_failing_state_lookup_closes_every_advanced_prefix(monkeypatch):
    _use_policy(CLIENT_POLICY)
    monkeypatch.setenv("SP_ENABLED_MODULES", "knowledge_base")

    def broken_state(environ=None):
        raise RuntimeError("state unavailable")

    monkeypatch.setattr(modules, "current_state", broken_state)
    proceed, handler = _gate("/api/knowledge/x")
    assert proceed is False and handler.status == 403
    assert handler.body == {"error": "module_inactive", "module": "knowledge_base"}


def test_an_unreadable_policy_closes_every_advanced_prefix(monkeypatch):
    monkeypatch.setenv("SP_ENABLED_MODULES", "knowledge_base")

    def broken():
        raise loader.GovernancePolicyError("unreadable")

    loader.set_policy_loader(broken)
    modules.clear_cache()
    handler = _Handler()
    assert modules.gate(handler, SimpleNamespace(path="/api/knowledge/x")) is True
    assert handler.status == 403 and handler.body["error"] == "module_inactive"


def test_governance_denies_first_and_the_gate_is_not_consulted(monkeypatch):
    import api.governance.enforce as enforce

    _use_policy(ENFORCE_POLICY)
    monkeypatch.setattr(enforce, "_request_identity", lambda handler: None)
    calls = []
    monkeypatch.setattr(modules, "gate", lambda handler, parsed: calls.append(parsed.path) or False)
    proceed, handler = _gate("/api/knowledge/x")
    assert proceed is False and handler.status in (401, 403) and calls == []


def _existing_api_paths():
    src = (REPO / "api" / "routes.py").read_text(encoding="utf-8")
    literals = set(re.findall(r"""["'](/api/[A-Za-z0-9_./{}-]*)["']""", src))
    literals |= {rule.pattern for rule in ROUTE_CATALOG} | set(_SELF_ROUTES)
    return sorted(literals)


def test_gate_never_touches_an_existing_route():
    _use_policy(CLIENT_POLICY)
    paths = _existing_api_paths()
    assert len(paths) > 200
    for path in paths:
        assert modules.route_module(path) is None, path
        assert modules.gate(_Handler(), SimpleNamespace(path=path)) is False, path
    for path in ("/api/bots/knowledge", "/api/knowledgebase", "/api/meetingsx", "/static/knowledge/x", "/"):
        assert modules.route_module(path) is None, path
