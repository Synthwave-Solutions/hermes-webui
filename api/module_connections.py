"""Module connection resolver (program plan 3.9, Appendix E.5.2).

Connections are the rows K1 to K12, K14 and K15 of the stack's connection
registry (``modules/connections.json``); ``tests/fixtures/managed_service/
module_connections.json`` is its pinned byte copy, and
``tests/test_module_connections_resolver.py`` keeps the registry below equal
to it. The WebUI never reads the stack repository at runtime.

Which connections are active is rendered centrally into the WebUI env as
``SP_ENABLED_CONNECTIONS`` (from Wave 2; until then nothing is active). The
resolver is fail safe:

* the source is ``SP_ENABLED_CONNECTIONS`` only, never the governance policy,
  ``settings.json`` or a request; unset, empty or unparsable gives ``()``;
* a ``*`` entry counts only when the policy's ``installation.kind`` is ``hq``,
  and there it adds only the ``default: on`` connections whose modules are
  active;
* a connection with any consent class other than ``none`` is active only
  when its id is listed, at HQ as well;
* each listed id is kept only when ``requires`` and ``requires_any`` hold
  against the module resolver's active set (``api/modules.py``); unknown ids
  are dropped and logged once;
* any exception gives ``()``.

The render already enforced the ``render`` preconditions; every consumer
calls ``preconditions()`` before acting and checks the ``runtime`` ones
itself (X6 and the other WebUI consumers).
"""
from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Mapping

logger = logging.getLogger(__name__)

ENV_KEY = "SP_ENABLED_CONNECTIONS"
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,39}$")
CONSENT_CLASSES = ("none", "owner_confirm", "participants_notice", "admin_approve")

SOURCE_ENV = "env"
SOURCE_DEFAULT = "default"
SOURCE_HQ = "hq"
SOURCE_INVALID = "invalid"


@dataclass(frozen=True)
class Connection:
    """One registry row, in the fields the WebUI uses."""

    id: str
    requires: tuple[str, ...]
    requires_any: tuple[str, ...]
    default: str
    consent: tuple[str, ...]
    preconditions: tuple[str, ...]
    client_visible: bool
    name: Mapping[str, str] = field(compare=False)
    summary: Mapping[str, str] = field(compare=False)

    @property
    def modules(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(self.requires + self.requires_any))


_PRECONDITIONS: dict[str, dict] = {
    "meeting_dpia": {"kind": "render", "owner": "X5"},
    "consent_notice": {"kind": "render", "owner": "X5"},
    "memory_proposals_ready": {"kind": "render", "owner": "X5"},
    "chat_mapping": {"kind": "runtime", "owner": "X6"},
    "project_mapping": {"kind": "runtime", "owner": "X6"},
    "task_owner_mapped": {"kind": "runtime", "owner": "M5b"},
    "contracts_dataset": {"kind": "runtime", "owner": "M1"},
    "knowledge_key": {"kind": "runtime", "owner": "X2"},
}

_CONNECTION_ROWS: tuple[Connection, ...] = (
    Connection(
        id="assistant_knowledge",
        requires=("knowledge_base",),
        requires_any=(),
        default="on",
        consent=("none",),
        preconditions=("knowledge_key",),
        client_visible=True,
        name={"nl": "AI-medewerkers zoeken in je kennisbank", "en": "Assistants search your knowledge base"},
        summary={"nl": "AI-medewerkers antwoorden uit de kennisbank met bronnen, alleen uit documenten die jouw groepen mogen lezen.", "en": "Assistants answer from the knowledge base with sources, only from documents your groups may read."},
    ),
    Connection(
        id="shared_speech",
        requires=(),
        requires_any=("dictation", "meeting_notes"),
        default="on",
        consent=("none",),
        preconditions=(),
        client_visible=True,
        name={"nl": "Eén spraakdienst voor dicteren, spraak en opnames", "en": "One speech service for dictation, voice and recordings"},
        summary={"nl": "Dicteren, spraakgesprekken en geüploade opnames gebruiken allemaal de eigen spraakdienst van je organisatie.", "en": "Dictation, voice conversations and uploaded recordings all use your organisation's own speech service."},
    ),
    Connection(
        id="minutes_to_chat",
        requires=("meeting_notes", "group_chat"),
        requires_any=(),
        default="off",
        consent=("owner_confirm", "participants_notice"),
        preconditions=("meeting_dpia", "consent_notice", "chat_mapping"),
        client_visible=True,
        name={"nl": "Verslag naar het groepsgesprek", "en": "Minutes to the group chat"},
        summary={"nl": "Het verslag met besluiten en actiepunten verschijnt in het groepsgesprek van het project.", "en": "The minutes with decisions and action items appear in the project's group chat."},
    ),
    Connection(
        id="minutes_to_knowledge",
        requires=("meeting_notes", "knowledge_base"),
        requires_any=(),
        default="off",
        consent=("owner_confirm", "participants_notice"),
        preconditions=("meeting_dpia", "consent_notice"),
        client_visible=True,
        name={"nl": "Verslagen in de kennisbank", "en": "Minutes in the knowledge base"},
        summary={"nl": "Bevestigde verslagen worden doorzoekbare documenten in de kennisbank, met de toegangsrechten van de vergadering.", "en": "Confirmed minutes become searchable documents in the knowledge base, with the meeting's access rights."},
    ),
    Connection(
        id="actions_to_tasks",
        requires=("meeting_notes", "workflows"),
        requires_any=(),
        default="off",
        consent=("owner_confirm", "participants_notice"),
        preconditions=("meeting_dpia", "consent_notice", "task_owner_mapped"),
        client_visible=True,
        name={"nl": "Actiepunten worden taken", "en": "Action items become tasks"},
        summary={"nl": "Elk actiepunt wordt een concepttaak voor de eigenaar, totdat die het bevestigt.", "en": "Each action item becomes a draft task for its owner, until the owner confirms it."},
    ),
    Connection(
        id="decision_to_signing",
        requires=("meeting_notes", "e_signing"),
        requires_any=(),
        default="off",
        consent=("owner_confirm", "participants_notice"),
        preconditions=("meeting_dpia", "consent_notice"),
        client_visible=True,
        name={"nl": "Besluit klaarzetten voor ondertekening", "en": "Prepare a decision for signing"},
        summary={"nl": "Een besluit uit het verslag wordt na jouw goedkeuring klaargezet als concept voor een ondertekenverzoek.", "en": "A decision from the minutes is prepared as a draft signing request after your approval."},
    ),
    Connection(
        id="design_to_project",
        requires=("design_studio",),
        requires_any=(),
        default="off",
        consent=("none",),
        preconditions=("project_mapping",),
        client_visible=True,
        name={"nl": "Ontwerpen in het project", "en": "Designs in the project"},
        summary={"nl": "Ontwerpen die je uit de ontwerpstudio exporteert, komen in de bestanden van het project.", "en": "Designs you export from the design studio land in the project's files."},
    ),
    Connection(
        id="signed_archive",
        requires=("e_signing",),
        requires_any=(),
        default="off",
        consent=("none",),
        preconditions=("project_mapping",),
        client_visible=True,
        name={"nl": "Ondertekende documenten gearchiveerd", "en": "Signed documents archived"},
        summary={"nl": "Als iedereen heeft ondertekend, komen het ondertekende document en het ondertekeningsverslag in het project.", "en": "When everyone has signed, the signed document and its signing record land in the project."},
    ),
    Connection(
        id="notebook_from_knowledge",
        requires=("notebook", "knowledge_base"),
        requires_any=(),
        default="off",
        consent=("none",),
        preconditions=(),
        client_visible=True,
        name={"nl": "Notitieboek vanuit de kennisbank", "en": "Notebook from the knowledge base"},
        summary={"nl": "Start een onderzoeksnotitieboek vanuit documenten in de kennisbank die je mag lezen.", "en": "Start a research notebook from documents in the knowledge base that you may read."},
    ),
    Connection(
        id="decisions_to_memory",
        requires=("meeting_notes",),
        requires_any=(),
        default="off",
        consent=("owner_confirm", "participants_notice", "admin_approve"),
        preconditions=("meeting_dpia", "consent_notice", "memory_proposals_ready"),
        client_visible=True,
        name={"nl": "Besluiten in het organisatiegeheugen", "en": "Decisions in organisation memory"},
        summary={"nl": "Goedgekeurde besluiten uit vergaderingen worden organisatiegeheugen dat elke AI-medewerker kan gebruiken.", "en": "Approved decisions from meetings become organisation memory that every assistant can recall."},
    ),
    Connection(
        id="module_health",
        requires=("workspace",),
        requires_any=(),
        default="on",
        consent=("none",),
        preconditions=(),
        client_visible=False,
        name={"nl": "Bewaking van alle onderdelen", "en": "Monitoring of all components"},
        summary={"nl": "Fouten, status en gebruik van elke module en koppeling worden bewaakt.", "en": "Errors, health and usage of every module and connection are monitored."},
    ),
    Connection(
        id="module_map",
        requires=("workspace",),
        requires_any=(),
        default="on",
        consent=("none",),
        preconditions=(),
        client_visible=True,
        name={"nl": "Overzicht van koppelingen", "en": "Overview of connections"},
        summary={"nl": "Laat per module zien met welke andere modules deze samenwerkt.", "en": "Shows per module which other modules it works with."},
    ),
    Connection(
        id="design_to_signing",
        requires=("design_studio", "e_signing"),
        requires_any=(),
        default="off",
        consent=("owner_confirm",),
        preconditions=(),
        client_visible=True,
        name={"nl": "Ontwerp klaarzetten voor ondertekening", "en": "Prepare a design for signing"},
        summary={"nl": "Een ontwerp wordt na jouw bevestiging klaargezet als concept voor een ondertekenverzoek.", "en": "A design is prepared as a draft signing request after you confirm."},
    ),
    Connection(
        id="signed_to_knowledge",
        requires=("e_signing", "knowledge_base"),
        requires_any=(),
        default="off",
        consent=("owner_confirm",),
        preconditions=("contracts_dataset",),
        client_visible=True,
        name={"nl": "Ondertekende documenten in de kennisbank", "en": "Signed documents in the knowledge base"},
        summary={"nl": "Ondertekende contracten en hun ondertekeningsverslag komen ook in een afgeschermde dataset van de kennisbank.", "en": "Signed contracts and their signing records also land in a restricted dataset of the knowledge base."},
    ),
)

REGISTRY: dict[str, Connection] = {row.id: row for row in _CONNECTION_ROWS}
CONNECTION_IDS: tuple[str, ...] = tuple(REGISTRY)


@dataclass(frozen=True)
class ConnectionState:
    """The active connections in registry order and where they came from."""

    active: tuple[str, ...]
    source: str


_EMPTY = ConnectionState((), SOURCE_DEFAULT)
_INVALID = ConnectionState((), SOURCE_INVALID)

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
    """``(ids, wildcard)``, or None when the value cannot be parsed (an entry
    that is neither ``*`` nor a valid id; blank entries are ignored)."""
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


def _modules_hold(row: Connection, active_modules: set) -> bool:
    if any(module_id not in active_modules for module_id in row.requires):
        return False
    return not row.requires_any or any(module_id in active_modules for module_id in row.requires_any)


def _resolve(module_state: Any, environ: Mapping[str, str], policy_raw: Any) -> ConnectionState:
    raw = environ.get(ENV_KEY)
    if raw is None or not str(raw).strip():
        return _EMPTY
    parsed = _parse_env(str(raw))
    if parsed is None:
        _log_once(f"invalid:{raw}", "%s is not a comma list of connection ids; none is active", ENV_KEY)
        return _INVALID
    ids, wildcard = parsed
    if not ids and not wildcard:
        return _EMPTY
    active_modules = set(getattr(module_state, "active", ()) or ())
    hq = wildcard and _installation_kind(policy_raw) == "hq"
    if wildcard and not hq:
        _log_once("wildcard", "%s=* counts only at HQ (installation.kind hq); ignored", ENV_KEY)
    wanted: set[str] = set()
    for connection_id in ids:
        row = REGISTRY.get(connection_id)
        if row is None:
            _log_once(f"unknown:{connection_id}", "%s names an unknown connection %r; dropped",
                      ENV_KEY, connection_id)
        elif _modules_hold(row, active_modules):
            wanted.add(connection_id)
    if hq:
        wanted.update(row.id for row in _CONNECTION_ROWS
                      if row.default == "on" and row.consent == ("none",) and _modules_hold(row, active_modules))
    active = tuple(row.id for row in _CONNECTION_ROWS if row.id in wanted)
    return ConnectionState(active, SOURCE_HQ if hq else SOURCE_ENV)


def resolve(module_state: Any, environ: Mapping[str, str], policy_raw: Any) -> ConnectionState:
    """The active connections for a module state (``api.modules.ModuleState``),
    an env mapping and the policy's raw mapping. Never raises: any exception
    gives no active connection."""
    try:
        return _resolve(module_state, environ, policy_raw)
    except Exception:
        _log_once("resolve_error", "Connection resolution failed; none is active", exc_info=True)
        return _INVALID


def current_state(environ: Mapping[str, str] | None = None) -> ConnectionState:
    """The active connections of this installation (never raises)."""
    try:
        env = os.environ if environ is None else environ
        from api import modules
        from api.governance import loader

        policy_raw = getattr(loader.get_policy(), "raw", None)
        return resolve(modules.current_state(env), env, policy_raw)
    except Exception:
        _log_once("state_error", "Connection state unavailable; none is active", exc_info=True)
        return _INVALID


def preconditions(connection_id: str) -> list[dict]:
    """Every declared precondition of a connection with its kind and owner.

    Consumers check the ``runtime`` entries themselves before acting; the
    render already enforced the ``render`` ones. An unknown id has none.
    """
    row = REGISTRY.get(connection_id)
    if row is None:
        return []
    return [{"name": name, "kind": _PRECONDITIONS[name]["kind"], "owner": _PRECONDITIONS[name]["owner"]}
            for name in row.preconditions]


def works_with(module_id: str, module_state: Any, connection_state: Any) -> list[dict]:
    """The connections of one module for the Modules page (W12).

    One entry per client-visible connection that names ``module_id`` in
    ``requires`` or ``requires_any``: ``active`` when the connection is
    active, ``needs_module`` when another module it needs is not active,
    ``off`` otherwise; ``other_modules`` are the connection's other modules
    and ``consent`` its consent classes.
    """
    active_modules = set(getattr(module_state, "active", ()) or ())
    active_connections = set(getattr(connection_state, "active", ()) or ())
    out = []
    for row in _CONNECTION_ROWS:
        if not row.client_visible or module_id not in row.modules:
            continue
        others = [m for m in row.modules if m != module_id]
        if row.id in active_connections:
            status = "active"
        else:
            missing = [m for m in row.requires if m != module_id and m not in active_modules]
            any_ok = (not row.requires_any or module_id in row.requires_any
                      or any(m in active_modules for m in row.requires_any))
            status = "needs_module" if missing or not any_ok else "off"
        out.append({"connection": row.id, "status": status, "other_modules": others,
                    "consent": list(row.consent)})
    return out
