"""Module resolver and module gate (program plan 3.7, Appendix E.4.2).

The managed service is sold as the Standard package plus Advanced modules.
Which modules an installation runs is rendered centrally into the WebUI env
as ``SP_ENABLED_MODULES`` (a comma list of catalogue ids, or ``*``). This
module turns that value into the active module set, fail safe:

* the source is ``SP_ENABLED_MODULES`` only, never the governance policy,
  ``settings.json`` or a request;
* unset or empty gives the Standard set (source ``default``); a value that
  cannot be parsed gives the Standard set (source ``invalid``);
* unknown ids are dropped and logged once; a module whose ``requires`` is not
  active is dropped; the Standard set is always included;
* ``*`` counts only when the policy's ``installation.kind`` is ``hq`` (source
  ``hq``); on any other installation it adds nothing;
* any exception while resolving counts as the Standard set, so ``gate()``
  answers 403 on every Advanced route prefix and never a 500 or an open route.

Module ids never become permission strings and never enter the governance
access model: governance and the module gate are independent, and both must
allow a request (``api/synthpulse_server.py`` calls ``gate()`` after the
governance hook allowed it).

The registry below mirrors the technical catalogue (``modules/catalog.json``
in the stack repository); ``tests/fixtures/managed_service/module_catalog.json``
is its pinned byte copy, and ``tests/test_modules_resolver.py`` keeps the ids,
tiers, requirements, the display denylist and the reason codes equal to it.
The WebUI never reads the stack repository at runtime.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass
from typing import Any, Mapping

logger = logging.getLogger(__name__)

ENV_KEY = "SP_ENABLED_MODULES"
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,39}$")

STANDARD = "standard"
ADVANCED = "advanced"

SOURCE_ENV = "env"
SOURCE_DEFAULT = "default"
SOURCE_HQ = "hq"
SOURCE_INVALID = "invalid"


@dataclass(frozen=True)
class ModuleSpec:
    """What one catalogue module means inside the WebUI."""

    id: str
    tier: str
    requires: tuple[str, ...] = ()
    panels: tuple[str, ...] = ()
    settings_sections: tuple[str, ...] = ()
    composer_controls: tuple[str, ...] = ()
    route_prefixes: tuple[str, ...] = ()
    app_tile: str | None = None
    help_pages: tuple[str, ...] = ()


# Catalogue order. Standard modules are never gated. Route prefixes, panels
# and app tiles are the neutral names of 3.7 and E.4.2; the app tile is the
# catalogue's ``app_link`` host key (links come from SP_MODULE_LINKS, W12).
_REGISTRY_ROWS = (
    ModuleSpec("workspace", STANDARD),
    ModuleSpec("group_chat", STANDARD, requires=("workspace",)),
    ModuleSpec("design_studio", STANDARD, requires=("workspace",), app_tile="design"),
    ModuleSpec("workflows", STANDARD, requires=("workspace",), app_tile="workflows"),
    ModuleSpec("knowledge_base", ADVANCED, requires=("workspace",),
               panels=("knowledge",), route_prefixes=("/api/knowledge/",)),
    ModuleSpec("notebook", ADVANCED, requires=("workspace",),
               route_prefixes=("/api/notebook/",), app_tile="notebook"),
    ModuleSpec("e_signing", ADVANCED, requires=("workspace",),
               route_prefixes=("/api/signing/",), app_tile="sign"),
    ModuleSpec("dictation", ADVANCED, requires=("workspace",),
               route_prefixes=("/api/dictation/",)),
    ModuleSpec("meeting_notes", ADVANCED, requires=("workspace",),
               panels=("meetings",), route_prefixes=("/api/meetings/",)),
    # E.7.1: a desktop module with its key route; no panel and no app tile.
    ModuleSpec("office_apps", ADVANCED, requires=("workspace",),
               route_prefixes=("/api/office-apps/",)),
)
REGISTRY: dict[str, ModuleSpec] = {spec.id: spec for spec in _REGISTRY_ROWS}
MODULE_IDS: tuple[str, ...] = tuple(REGISTRY)
STANDARD_IDS: tuple[str, ...] = tuple(spec.id for spec in _REGISTRY_ROWS if spec.tier == STANDARD)

# E.4.3, equal to the catalogue's lists (the one internal-name denylist and
# the unavailable reason codes). For runtime use: W12's launcher host check
# and its reason mapping.
DISPLAY_DENYLIST: tuple[str, ...] = (
    "n8n", "OmniRoute", "LangGraph", "Hermes", "LiteLLM", "RAGFlow", "Langfuse",
    "OpenWebUI", "OpenDesign", "OpenNotebook", "DocuSeal", "OpenWhispr", "OpenWispr",
    "Fireflies", "Meetily", "Vexa", "OpenBot", "Nango", "SurrealDB", "Elasticsearch",
    "MinIO", "Valkey", "Mnemosyne", "mnemo-hub", "GenOffice", "Genspark",
)
UNAVAILABLE_REASONS: tuple[str, ...] = ("arch", "hosting_model", "requires", "not_confirmed", "placement")

# Every Advanced route prefix, fixed at import: the gate falls back to it if
# looking a path up ever fails, so such a failure closes the prefix.
_GATED_PREFIXES: tuple[tuple[str, str], ...] = tuple(
    (prefix, spec.id) for spec in _REGISTRY_ROWS if spec.tier != STANDARD for prefix in spec.route_prefixes
)


@dataclass(frozen=True)
class ModuleState:
    """The resolved module set: ``active`` in catalogue order and its source."""

    active: tuple[str, ...]
    source: str


_STANDARD_STATE = ModuleState(STANDARD_IDS, SOURCE_DEFAULT)
_INVALID_STATE = ModuleState(STANDARD_IDS, SOURCE_INVALID)

_LOG_LOCK = threading.Lock()
_LOGGED: set[str] = set()


def _log_once(key: str, message: str, *args: Any, exc_info: bool = False) -> None:
    with _LOG_LOCK:
        if key in _LOGGED:
            return
        _LOGGED.add(key)
    logger.warning(message, *args, exc_info=exc_info)


def _installation_kind(policy_raw: Any) -> str:
    installation = policy_raw.get("installation") if isinstance(policy_raw, Mapping) else None
    kind = installation.get("kind") if isinstance(installation, Mapping) else None
    return kind.strip().lower() if isinstance(kind, str) else ""


def _parse_env(value: str) -> tuple[tuple[str, ...], bool] | None:
    """``(ids, wildcard)`` from the env value, or None when it cannot be parsed.

    Entries are separated by commas; blank entries are ignored. Every other
    entry must be ``*`` or match the catalogue id pattern, else the whole
    value is unparsable.
    """
    ids: list[str] = []
    wildcard = False
    for item in value.split(","):
        entry = item.strip()
        if not entry:
            continue
        if entry == "*":
            wildcard = True
        elif ID_PATTERN.match(entry):
            if entry not in ids:
                ids.append(entry)
        else:
            return None
    return tuple(ids), wildcard


def _resolve(policy_raw: Any, environ: Mapping[str, str]) -> ModuleState:
    raw = environ.get(ENV_KEY)
    if raw is None or not str(raw).strip():
        return _STANDARD_STATE
    parsed = _parse_env(str(raw))
    if parsed is None:
        _log_once(f"invalid:{raw}", "%s is not a comma list of module ids; using the Standard set", ENV_KEY)
        return _INVALID_STATE
    ids, wildcard = parsed
    if not ids and not wildcard:
        return _STANDARD_STATE
    wanted = set(STANDARD_IDS)
    hq = wildcard and _installation_kind(policy_raw) == "hq"
    if hq:
        wanted.update(MODULE_IDS)
    elif wildcard:
        _log_once("wildcard", "%s=* counts only at HQ (installation.kind hq); ignored", ENV_KEY)
    for module_id in ids:
        if module_id in REGISTRY:
            wanted.add(module_id)
        else:
            _log_once(f"unknown:{module_id}", "%s names an unknown module %r; dropped", ENV_KEY, module_id)
    # Drop every module whose requirements are not active, until stable.
    changed = True
    while changed:
        changed = False
        for module_id in list(wanted):
            if module_id in STANDARD_IDS:
                continue
            missing = [req for req in REGISTRY[module_id].requires if req not in wanted]
            if missing:
                wanted.discard(module_id)
                changed = True
                _log_once(f"requires:{module_id}", "Module %r needs %s; dropped", module_id, ", ".join(missing))
    active = tuple(module_id for module_id in MODULE_IDS if module_id in wanted)
    return ModuleState(active, SOURCE_HQ if hq else SOURCE_ENV)


def resolve(policy_raw: Any, environ: Mapping[str, str]) -> ModuleState:
    """The active module set for a policy (its raw mapping) and an env mapping.

    Never raises: any exception gives the Standard set with source ``invalid``.
    """
    try:
        return _resolve(policy_raw, environ)
    except Exception:
        _log_once("resolve_error", "Module resolution failed; using the Standard set", exc_info=True)
        return _INVALID_STATE


_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {"key": None, "state": None}


def current_state(environ: Mapping[str, str] | None = None) -> ModuleState:
    """The active module set of this installation, cached per env value and
    installation kind (the policy loader re-reads its file when it changes).

    Never raises: an unreadable policy or any other failure gives the Standard
    set with source ``invalid``.
    """
    try:
        env = os.environ if environ is None else environ
        from api.governance import loader

        policy_raw = getattr(loader.get_policy(), "raw", None)
        key = (env.get(ENV_KEY), _installation_kind(policy_raw))
        with _CACHE_LOCK:
            if _CACHE["key"] == key and _CACHE["state"] is not None:
                return _CACHE["state"]
        state = resolve(policy_raw, env)
        with _CACHE_LOCK:
            _CACHE["key"], _CACHE["state"] = key, state
        return state
    except Exception:
        _log_once("state_error", "Module state unavailable; using the Standard set", exc_info=True)
        return _INVALID_STATE


def clear_cache() -> None:
    """Forget the cached state (tests, and a changed env in one process)."""
    with _CACHE_LOCK:
        _CACHE["key"], _CACHE["state"] = None, None


def module_active(key: str) -> bool:
    """Whether the module ``key`` is active on this installation."""
    return key in current_state().active


def route_module(path: str) -> str | None:
    """The Advanced module that owns ``path`` (a route prefix, or the prefix
    without its trailing slash), else None. Standard modules own no prefix."""
    path = str(path or "")
    for prefix, module_id in _GATED_PREFIXES:
        if path.startswith(prefix) or path == prefix.rstrip("/"):
            return module_id
    return None


def gate(handler, parsed) -> bool:
    """Answer 403 ``module_inactive`` for a route of an inactive module.

    Returns True when the request was answered (blocked), False when it may
    go on to dispatch. Called after governance allowed the request. Fails
    closed: when the state cannot be read, only the Standard set counts.
    """
    path = str(getattr(parsed, "path", "") or "")
    try:
        module_id = route_module(path)
    except Exception:
        _log_once("route_error", "Module route lookup failed; closing the Advanced prefixes", exc_info=True)
        module_id = next((mid for prefix, mid in _GATED_PREFIXES
                          if path.startswith(prefix) or path == prefix.rstrip("/")), None)
    if module_id is None:
        return False
    try:
        active = module_id in current_state().active
    except Exception:
        active = False
    if active:
        return False
    from api.helpers import j

    j(handler, {"error": "module_inactive", "module": module_id}, status=403)
    return True


def nav_view(state: ModuleState | None = None) -> dict:
    """What the browser hides and offers for a module state (``/api/settings``
    ``module_nav``): the panels, settings sections and composer controls of
    inactive modules, and the app tiles of active ones."""
    state = state if state is not None else current_state()
    active = set(state.active)
    hidden_panels: list[str] = []
    hidden_sections: list[str] = []
    hidden_controls: list[str] = []
    apps: list[dict] = []
    for spec in _REGISTRY_ROWS:
        if spec.id in active:
            if spec.app_tile:
                apps.append({"module": spec.id, "app": spec.app_tile})
            continue
        hidden_panels.extend(p for p in spec.panels if p not in hidden_panels)
        hidden_sections.extend(s for s in spec.settings_sections if s not in hidden_sections)
        hidden_controls.extend(c for c in spec.composer_controls if c not in hidden_controls)
    return {
        "hidden_panels": hidden_panels,
        "hidden_settings_sections": hidden_sections,
        "hidden_composer_controls": hidden_controls,
        "apps": apps,
    }
