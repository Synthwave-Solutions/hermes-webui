"""The module connection resolver is fail safe (program plan 3.9, Appendix E.5.2).

``SP_ENABLED_CONNECTIONS`` is the only source; unset, empty or unparsable
gives no connection; ``*`` counts only at HQ and adds only the ``default: on``
connections whose modules are active; a connection with a consent class other
than ``none`` is active only when listed by id, at HQ as well; listed ids are
kept only when their modules are active; any exception gives no connection.
The WebUI registry is pinned to the byte copy of the stack registry.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import module_connections as mc  # noqa: E402
from api import modules  # noqa: E402
from api.governance import loader  # noqa: E402
from api.governance.loader import parse_governance_policy  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures" / "managed_service"
REGISTRY = json.loads((FIXTURES / "module_connections.json").read_text(encoding="utf-8"))
CATALOG = json.loads((FIXTURES / "module_catalog.json").read_text(encoding="utf-8"))

CLIENT = {"version": 1, "mode": "off"}
HQ = {"version": 1, "mode": "off", "installation": {"kind": "hq"}}
DEFAULT_ON = ("assistant_knowledge", "shared_speech", "module_health", "module_map")


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.delenv("SP_ENABLED_CONNECTIONS", raising=False)
    monkeypatch.delenv("SP_ENABLED_MODULES", raising=False)
    modules.clear_cache()
    yield
    modules.clear_cache()
    loader.set_policy_loader(None)


def _modules(value=None, policy=CLIENT):
    return modules.resolve(policy, {} if value is None else {"SP_ENABLED_MODULES": value})


ALL_MODULES = modules.resolve(HQ, {"SP_ENABLED_MODULES": "*"})
STANDARD = _modules()


def _resolve(value, module_state=ALL_MODULES, policy=CLIENT):
    env = {} if value is None else {"SP_ENABLED_CONNECTIONS": value}
    return mc.resolve(module_state, env, policy)


# ── The registry equals the pinned fixture ───────────────────────────────────

def test_registry_fixture_matches_its_pin():
    data = (FIXTURES / "module_connections.json").read_bytes()
    pin = (FIXTURES / "module_connections.sha256").read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(data).hexdigest() == pin


def test_registry_equals_the_fixture():
    rows = REGISTRY["connections"]
    assert mc.CONNECTION_IDS == tuple(row["id"] for row in rows)
    for row in rows:
        conn = mc.REGISTRY[row["id"]]
        assert conn.requires == tuple(row["requires"]), row["id"]
        assert conn.requires_any == tuple(row["requires_any"]), row["id"]
        assert conn.default == row["default"], row["id"]
        assert conn.consent == tuple(row["consent"]), row["id"]
        assert conn.preconditions == tuple(row["preconditions"]), row["id"]
        assert conn.client_visible == row["client_visible"], row["id"]
        assert dict(conn.name) == row["name"] and dict(conn.summary) == row["summary"], row["id"]
    assert mc._PRECONDITIONS == {name: {"kind": p["kind"], "owner": p["owner"]}
                                 for name, p in REGISTRY["preconditions"].items()}
    assert list(mc.CONSENT_CLASSES) == REGISTRY["consent_classes"]
    catalogue_ids = {row["id"] for row in CATALOG["modules"]}
    for conn in mc.REGISTRY.values():
        assert set(conn.modules) <= catalogue_ids, conn.id
    assert "remote_knowledge" not in mc.REGISTRY


# ── The fail-safe matrix ─────────────────────────────────────────────────────

@pytest.mark.parametrize("value,source", [(None, "default"), ("", "default"), ("  ", "default"),
                                          (", ,", "default")])
def test_unset_or_empty_gives_nothing(value, source):
    assert _resolve(value) == mc.ConnectionState((), source)


@pytest.mark.parametrize("value", ["Module_Map", "module-map", "module_map;x", "ab", "**", "module_map,Bad Id"])
def test_garbage_gives_nothing(value):
    assert _resolve(value) == mc.ConnectionState((), "invalid")


def test_wildcard_on_a_client_gives_nothing():
    for policy in (CLIENT, {"installation": {"kind": "client"}}, None, "junk"):
        assert _resolve("*", policy=policy).active == (), policy


def test_wildcard_at_hq_gives_exactly_the_default_on_connections():
    state = _resolve("*", policy=HQ)
    assert state == mc.ConnectionState(DEFAULT_ON, "hq")
    expected = tuple(row["id"] for row in REGISTRY["connections"] if row["default"] == "on")
    assert state.active == expected
    for conn_id in state.active:
        assert mc.REGISTRY[conn_id].consent == ("none",)


def test_wildcard_at_hq_needs_the_modules_of_each_connection():
    assert _resolve("*", module_state=STANDARD, policy=HQ).active == ("module_health", "module_map")


def test_a_consent_connection_listed_at_hq_is_added():
    state = _resolve("*,minutes_to_chat", policy=HQ)
    assert state.active == ("assistant_knowledge", "shared_speech", "minutes_to_chat", "module_health",
                            "module_map")


def test_a_consent_connection_not_listed_stays_off_at_hq():
    active = _resolve("*", policy=HQ).active
    for row in REGISTRY["connections"]:
        if row["consent"] != ["none"]:
            assert row["id"] not in active, row["id"]


def test_listed_ids_are_active_when_their_modules_are():
    assert _resolve("design_to_project,signed_archive").active == ("design_to_project", "signed_archive")
    assert _resolve("minutes_to_chat").active == ("minutes_to_chat",)


def test_an_unknown_id_is_dropped_and_logged_once(caplog):
    caplog.set_level("WARNING", logger="api.module_connections")
    mc._LOGGED.discard("unknown:crm_sync")
    for _ in range(2):
        assert _resolve("crm_sync,module_map").active == ("module_map",)
    assert sum("crm_sync" in record.getMessage() for record in caplog.records) == 1


def test_a_missing_required_module_drops_the_connection():
    only_knowledge = _modules("knowledge_base")
    assert _resolve("minutes_to_knowledge,assistant_knowledge", module_state=only_knowledge).active == (
        "assistant_knowledge",)
    assert _resolve("assistant_knowledge", module_state=STANDARD).active == ()


def test_requires_any_needs_one_active_module():
    assert _resolve("shared_speech", module_state=STANDARD).active == ()
    assert _resolve("shared_speech", module_state=_modules("dictation")).active == ("shared_speech",)
    assert _resolve("shared_speech", module_state=_modules("meeting_notes")).active == ("shared_speech",)


def test_default_on_connections_are_not_active_unless_listed_or_wildcard():
    assert _resolve("module_map").active == ("module_map",)
    assert "module_health" not in _resolve("module_map").active


def test_an_exception_inside_resolution_gives_nothing(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("registry broken")

    monkeypatch.setattr(mc, "_parse_env", boom)
    assert _resolve("module_map") == mc.ConnectionState((), "invalid")
    assert _resolve("*", policy=HQ) == mc.ConnectionState((), "invalid")


def test_current_state_reads_only_the_env(monkeypatch):
    policy = parse_governance_policy(dict(HQ, connections=["module_map"], enabled_connections=["module_map"]))
    loader.set_policy_loader(lambda: policy)
    assert mc.current_state() == mc.ConnectionState((), "default")
    monkeypatch.setenv("SP_ENABLED_MODULES", "*")
    monkeypatch.setenv("SP_ENABLED_CONNECTIONS", "*")
    modules.clear_cache()
    assert mc.current_state() == mc.ConnectionState(DEFAULT_ON, "hq")

    def broken():
        raise loader.GovernancePolicyError("unreadable")

    loader.set_policy_loader(broken)
    assert mc.current_state() == mc.ConnectionState((), "invalid")


# ── Preconditions and works_with ─────────────────────────────────────────────

def test_preconditions_return_every_declared_precondition_with_kind_and_owner():
    declared = REGISTRY["preconditions"]
    for row in REGISTRY["connections"]:
        got = mc.preconditions(row["id"])
        assert [p["name"] for p in got] == row["preconditions"], row["id"]
        for item in got:
            assert item == {"name": item["name"], "kind": declared[item["name"]]["kind"],
                            "owner": declared[item["name"]]["owner"]}
    assert mc.preconditions("minutes_to_chat") == [
        {"name": "meeting_dpia", "kind": "render", "owner": "X5"},
        {"name": "consent_notice", "kind": "render", "owner": "X5"},
        {"name": "chat_mapping", "kind": "runtime", "owner": "X6"},
    ]
    assert mc.preconditions("unknown_row") == []


@pytest.mark.parametrize("module_id", [row["id"] for row in CATALOG["modules"]])
def test_works_with_lists_every_client_visible_connection_of_a_module(module_id):
    rows = [row for row in REGISTRY["connections"]
            if row["client_visible"] and module_id in row["requires"] + row["requires_any"]]
    nothing = mc.ConnectionState((), "default")
    for module_state in (STANDARD, ALL_MODULES):
        got = mc.works_with(module_id, module_state, nothing)
        assert [item["connection"] for item in got] == [row["id"] for row in rows]
        for item, row in zip(got, rows, strict=True):
            assert item["consent"] == row["consent"]
            assert module_id not in item["other_modules"]
            assert set(item["other_modules"]) == set(row["requires"] + row["requires_any"]) - {module_id}
            assert item["status"] in ("off", "needs_module")
            if module_state is ALL_MODULES:
                assert item["status"] == "off", item
    everything = mc.ConnectionState(tuple(mc.CONNECTION_IDS), "hq")
    for item in mc.works_with(module_id, ALL_MODULES, everything):
        assert item["status"] == "active", item


def test_works_with_statuses():
    only_notes = _modules("meeting_notes")
    listed = _resolve("minutes_to_chat", module_state=only_notes)
    by_id = {item["connection"]: item for item in mc.works_with("meeting_notes", only_notes, listed)}
    assert by_id["minutes_to_chat"]["status"] == "active"
    assert by_id["minutes_to_knowledge"] == {
        "connection": "minutes_to_knowledge", "status": "needs_module", "other_modules": ["knowledge_base"],
        "consent": ["owner_confirm", "participants_notice"]}
    assert by_id["actions_to_tasks"]["status"] == "off"
    assert by_id["shared_speech"]["status"] == "off"
    speech = {item["connection"]: item for item in mc.works_with("dictation", STANDARD, listed)}
    assert speech["shared_speech"]["status"] == "off"
    assert all(item["connection"] != "module_health" for item in mc.works_with("workspace", ALL_MODULES, listed))
