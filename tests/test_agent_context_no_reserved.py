"""Agent turns never carry control-plane permissions (plan 3.6, 3.11; W3a).

api.governance.agent_context._translate_context serializes the caller's
EffectiveAccess for the engine. Organisation, billing, department, support
and bot screen permissions (org:, billing:, departments:, support:, screen:)
must not be in that payload, whether they come from an explicit grant or a
role; a2a: stays because the engine's own A2A gate needs it. Denies stay as
they are (they only narrow). The payload is inspected as serialized, with the
real engine serializer when the hermes-agent checkout is importable and with
a recording stand-in otherwise.
"""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.governance import agent_context  # noqa: E402
from api.governance import loader  # noqa: E402
from api.governance.loader import parse_governance_policy  # noqa: E402
from api.governance.models import GovernanceSubject  # noqa: E402
from api.governance.resolver import resolve_effective_access  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "managed_service" / "org_acme.yaml"
STRIPPED = ("org:", "billing:", "departments:", "support:", "screen:")
CONTROL_PLANE = [
    "org:read", "org:members:write", "billing:read", "departments:sales:write",
    "support:tickets", "screen:watch", "screen:takeover", "screen:admin",
]
A2A = "a2a:call:acme-inst_a/sales-bot"


def _policy_raw() -> dict:
    raw = copy.deepcopy(yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))["policy"])
    raw["roles"]["control"] = {"grants": {"permissions": ["chat:use", *CONTROL_PLANE, A2A]}}
    # A legacy account whose role names every control-plane permission.
    raw["users"]["granted@acme.example"] = {"roles": ["control"], "grants": {"permissions": ["org:*"]}}
    # A managed whitelist account: the role ceiling is serialized too.
    raw["users"]["managed@acme.example"] = {
        "access_level": "elevated", "access_mode": "whitelist", "roles": ["control"],
        "grants": {"permissions": ["chat:use", *CONTROL_PLANE, A2A]},
    }
    # The elevated blacklist regression subject also gets explicit names.
    raw["users"]["power.user@acme.example"]["grants"] = {"permissions": [*CONTROL_PLANE, A2A]}
    return raw


@pytest.fixture
def policy():
    parsed = parse_governance_policy(_policy_raw())
    loader.set_policy_loader(lambda: parsed)
    yield parsed
    loader.set_policy_loader(None)


@pytest.fixture(autouse=True)
def _no_managed_bot(monkeypatch):
    monkeypatch.setattr("api.bot_builder.access_ceiling", lambda *args: None)


def _recording_module(captured):
    """Stand-in for the engine context module: serializes what the shim
    exposes (the same fields the engine serializer reads) and records it."""

    def grants(value):
        return value.to_mapping() if value is not None else None

    def access_payload(access):
        return {
            "permissions": sorted(access.permissions),
            "grants": grants(access.grants),
            "deny": grants(access.deny),
            "role_ceiling": grants(access.role_ceiling),
            "subject": {"email": access.subject.email, "org_id": access.subject.org_id},
        }

    shims = []

    def serialize(shim):
        shims.append(shim)
        ceiling = getattr(shim, "bot_access_ceiling", None)
        access = access_payload(shim.access)
        access["policy_controls_version"] = 1
        payload = json.dumps({
            "access": access,
            "bot_access_ceiling": access_payload(ceiling) if ceiling is not None else None,
        })
        captured.append(payload)
        return payload

    def rebuild(payload):
        # The round-trip checks compare the rebuilt context with what was
        # serialized; hand back exactly the serialized access.
        return SimpleNamespace(access=shims[-1].access)

    return SimpleNamespace(
        DashboardGovernanceContext=SimpleNamespace(__dataclass_fields__={"bot_access_ceiling": None}),
        serialize_context_for_env=serialize,
        context_from_env_payload=rebuild,
    )


def _real_module_recording(monkeypatch, captured):
    try:
        module = agent_context._agent_governance_module()
    except Exception:
        pytest.skip("hermes_cli.dashboard_governance not importable in this environment")
    original = module.serialize_context_for_env

    def recording(ctx):
        payload = original(ctx)
        captured.append(payload)
        return payload

    monkeypatch.setattr(module, "serialize_context_for_env", recording)
    return module


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


def _granted(payload: dict) -> list[str]:
    """Every string in the serialized payload except the deny block."""
    trimmed = copy.deepcopy(payload)
    for section in (trimmed.get("access") or {}, trimmed.get("bot_access_ceiling") or {}):
        section.pop("deny", None)
    return list(_strings(trimmed))


def _assert_no_control_plane(payload_text: str):
    payload = json.loads(payload_text)
    leaked = sorted({s for s in _granted(payload) if s.lower().startswith(STRIPPED)})
    assert leaked == [], f"control-plane names in the agent payload: {leaked}"


@pytest.mark.parametrize("email", ["granted@acme.example", "managed@acme.example", "power.user@acme.example"])
def test_serialized_payload_holds_no_control_plane_names_stand_in(policy, email):
    # Precondition: the WebUI itself does resolve these names for the person.
    access = resolve_effective_access(policy, GovernanceSubject(email=email))
    assert access.has_permission("screen:watch") and access.has_permission("org:read")

    captured = []
    agent_context._translate_context(_recording_module(captured), policy, email, (), "default", "s", "r")
    assert len(captured) == 1
    _assert_no_control_plane(captured[0])
    payload = json.loads(captured[0])
    assert A2A in payload["access"]["permissions"] or A2A in payload["access"]["grants"]["permissions"]


@pytest.mark.parametrize("email", ["granted@acme.example", "managed@acme.example", "power.user@acme.example"])
def test_serialized_payload_holds_no_control_plane_names_real_engine(policy, email, monkeypatch):
    captured = []
    module = _real_module_recording(monkeypatch, captured)
    ctx = agent_context._translate_context(module, policy, email, (), "default", "s", "r")
    assert len(captured) == 1
    _assert_no_control_plane(captured[0])
    payload = json.loads(captured[0])
    assert A2A in payload["access"]["grants"]["permissions"], "a2a: is kept for the engine's A2A gate"
    assert payload["subject"]["org_id"] == "org_acme"
    engine_permissions = set(ctx.access.permissions) | set(ctx.access.grants.permissions)
    assert not any(p.startswith(STRIPPED) for p in engine_permissions)


def test_bot_ceiling_is_stripped_too(policy, monkeypatch):
    from dataclasses import replace

    def ceiling(identity, name, rights):
        return replace(rights, permissions=frozenset({"*", "screen:watch", "org:read"}))

    monkeypatch.setattr("api.bot_builder.access_ceiling", ceiling)
    captured = []
    agent_context._translate_context(_recording_module(captured), policy, "granted@acme.example",
                                     (), "sales-bot", "s", "r")
    payload = json.loads(captured[0])
    assert payload["bot_access_ceiling"] is not None
    _assert_no_control_plane(captured[0])


def test_denies_on_control_plane_names_are_kept(policy):
    raw = _policy_raw()
    raw["users"]["granted@acme.example"]["deny"] = {"permissions": ["screen:watch"]}
    parsed = parse_governance_policy(raw)
    captured = []
    agent_context._translate_context(_recording_module(captured), parsed, "granted@acme.example",
                                     (), "default", "s", "r")
    payload = json.loads(captured[0])
    assert payload["access"]["deny"]["permissions"] == ["screen:watch"]
    _assert_no_control_plane(captured[0])


def test_the_webui_view_of_the_person_is_unchanged(policy):
    # Stripping applies to the agent payload only; the WebUI's own resolution
    # (routes, handlers) still sees the explicit grants.
    captured = []
    agent_context._translate_context(_recording_module(captured), policy, "granted@acme.example",
                                     (), "default", "s", "r")
    access = resolve_effective_access(policy, GovernanceSubject(email="granted@acme.example"))
    assert {"org:read", "screen:watch"} <= set(access.permissions)
