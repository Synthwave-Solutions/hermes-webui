"""Related governance approvals for one pending access request.

Reported 28 Aug 2026 ("Suggest related approvals so an access chain is resolved
in one review"): governance has two walls in front of every call. enforce.py
checks the route allowlist first and the permission second, so an administrator
who approves the address a person was stopped at often sends them straight into
the second wall on their next try, and the queue grows a follow-up request for
what was always the same problem.

This module answers one question, read-only: given a pending access request,
what else is this person going to be stopped by. It decides nothing, writes no
policy and grants nothing. Every row it returns is a proposal an administrator
approves, denies or ignores on its own.

Two properties this module exists to hold
-----------------------------------------
* A suggestion is never a one-click widening of access. ``actionable`` is False
  for everything outside api.grant_requests.GRANTABLE_PERMISSIONS (an allowlist
  of read-shaped permissions), and the decide handler refuses to approve a row
  that is not actionable. A write, restart or shell permission is reported as
  information and has to be granted by editing the access rules.
* CONFIRMED and HEURISTIC never blur. A confirmed row is a dependency replayed
  from the code that does the blocking (the route catalog, the two-wall order
  in enforce.py, and a hand-verified table of incidents). A heuristic row is a
  correlation: this person keeps being stopped elsewhere, or already has other
  requests waiting. The two are counted, labelled and rendered separately.

Known limitation, deliberate: the requester is resolved from their e-mail
alone, so grants that reach them through an SSO-claimed group are invisible
here (resolve_effective_access derives those from the live login's claims,
which an approvals row does not carry). The effect is over-suggesting: an
administrator may be offered something the person already has through such a
group. It never under-reports and it never widens anything by itself.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path

from .audit import _hash_identity, read_audit_events
from .catalog import ROUTE_CATALOG, route_permission
from .models import GovernanceSubject
from .resolver import resolve_effective_access

logger = logging.getLogger(__name__)

CONFIRMED = "confirmed"
HEURISTIC = "heuristic"

STATUS_OPEN = "open"
STATUS_APPROVED = "approved"
STATUS_DENIED = "denied"
STATUS_IGNORED = "ignored"

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

# read_audit_events reads the whole trail and slices the tail, and this runs
# once per opened review detail, so the scan is bounded. A failed or slow read
# degrades to no heuristics at all; the confirmed list still renders.
_AUDIT_SCAN_LIMIT = 2000
_AUDIT_WINDOW_SECONDS = 7 * 24 * 60 * 60
# Per signal, not overall: a long list stops being a review and starts being a
# checklist somebody clicks through.
_MAX_PER_SIGNAL = 3

_DECISIONS_NAME = "governance-suggestion-decisions.json"
_DECISIONS_LOCK = threading.Lock()

# Hand-verified dependencies between permissions, each one an incident.
#
# chat:use -> sessions:write (11 Aug 2026): the WebUI creates a session before
# the first turn when none is open (switchToWorkspace posts /api/session/new),
# and that call is scored against sessions:write while the chat itself needs
# chat:use. Somebody granted chat access alone and the assistant opened and
# then stopped on the very next step.
#
# terminal:use is deliberately NOT listed next to chat:use: the route catalog
# split the two apart on purpose so chat access stops implying shell access,
# and re-pairing them here would quietly undo that.
# Each entry carries its own copy so a second incident cannot be added by
# borrowing a sentence written for this one.
KNOWN_DEPENDENCIES: dict[str, dict] = {
    "chat:use": {
        "permissions": ("sessions:write",),
        "routes": ("/api/session",),
        "why": (
            "Starting a conversation quietly opens a workspace first. Without "
            "this, the assistant loads and then stops on the very next step, "
            "which reads to the person as it being broken."
        ),
        "route_why": (
            "The address a new workspace is opened at is still on this "
            "person's blocked list, so a conversation cannot be started for "
            "them at all."
        ),
        "evidence": "Seen in practice: reported once already and traced to this.",
    },
}


# ── Suggestability ──────────────────────────────────────────────────────────

def _permission_is_visible(permission: str) -> bool:
    """Whether a permission may be NAMED as a suggestion at all.

    Mirrors the route-denial guard: governance and admin capabilities are not
    offered on this surface in any form, not even as information. Whether a
    visible permission may also be APPROVED here is a separate and much
    narrower question, answered by the allowlist in api.grant_requests.
    """
    name = str(permission or "").strip()
    if not name:
        return False
    return not (name.startswith("governance:") or name.endswith(":admin"))


def _route_is_visible(path: str) -> bool:
    """Whether a route may be named as a suggestion (same rule as above)."""
    bare = str(path or "").strip().rstrip("*").rstrip("/")
    if not bare.startswith("/api/"):
        return False
    for method in ("GET", "POST"):
        if not _permission_is_visible(route_permission(bare, method) or "x"):
            return False
    return True


def _permission_is_actionable(permission: str) -> bool:
    try:
        from api.grant_requests import _permission_is_grantable

        return bool(_permission_is_grantable(permission))
    except Exception:
        return False


def _is_visible(gkind: str, value: str) -> bool:
    if gkind == "permission":
        return _permission_is_visible(value)
    if gkind == "route":
        return _route_is_visible(value)
    return bool(value)


def _is_actionable(gkind: str, value: str) -> bool:
    """Whether an administrator may grant this row straight from the review.

    Route grants confer no capability of their own (the permission wall stays
    up behind them), which is why they keep the requestability rule the denial
    spool already uses. Permissions are held to the allowlist. Everything else,
    model provider shapes included, is information only.
    """
    if gkind == "permission":
        return _permission_is_actionable(value)
    if gkind == "route":
        try:
            from api.grant_requests import _route_is_requestable

            bare = str(value or "").rstrip("*").rstrip("/") or str(value or "")
            return bool(_route_is_requestable(bare, "POST"))
        except Exception:
            return False
    return False


# ── Plain-language copy and risk ────────────────────────────────────────────
# Every sentence a reviewer reads comes from api/capability_risk.py, the single
# place these are written. Nothing here composes a path, a status code or a
# module name into copy.

def _permission_meta(permission: str) -> dict:
    try:
        from api.capability_risk import PERMISSION_RISKS

        return dict(PERMISSION_RISKS.get(permission) or {})
    except Exception:
        return {}


def _gkind_meta(gkind: str) -> dict:
    try:
        from api.capability_risk import GKIND_RISKS

        return dict(GKIND_RISKS.get(gkind) or {})
    except Exception:
        return {}


def _risk_for(gkind: str, value: str) -> str:
    """Risk band, anchored on the same predicate that decides actionability.

    Anything a one-click decision may not write is high by construction: it is
    exactly the set of write, restart, schedule and shell capabilities.
    """
    if gkind == "permission":
        if not _permission_is_actionable(value):
            return RISK_HIGH
        return RISK_MEDIUM if _permission_meta(value).get("risks") else RISK_LOW
    if gkind == "route":
        bare = str(value or "").rstrip("*").rstrip("/") or str(value or "")
        names = [route_permission(bare, m) for m in ("GET", "POST")]
        names = [n for n in names if n]
        if any(not _permission_is_actionable(n) for n in names):
            return RISK_MEDIUM
        return RISK_LOW
    return RISK_MEDIUM


def _risk_note(gkind: str, value: str) -> str:
    if gkind == "permission":
        meta = _permission_meta(value)
        capability = str(meta.get("capability") or "").strip()
        data = str(meta.get("data") or "").strip()
        if capability and data:
            return f"{capability} Data it reaches: {data}"
        return capability or "What this allows is not described here, so check it before deciding."
    if gkind == "route":
        return str(_gkind_meta("route").get("capability") or "").strip()
    if gkind == "model_provider":
        return (
            "The model access recorded for this person names something the "
            "assistant will not recognise when it runs, so every turn is refused."
        )
    return ""


def _capability_for(gkind: str, value: str) -> str:
    if gkind == "permission":
        return str(_permission_meta(value).get("capability") or "").strip()
    if gkind == "route":
        return str(_gkind_meta("route").get("capability") or "").strip()
    return _risk_note(gkind, value)


def _label_for(gkind: str, value: str) -> str:
    """Short heading for one row. Slugs are fine: this renders in the
    governance admin panel, which already shows permission chips verbatim."""
    if gkind == "permission":
        return f"Permission: {value}"
    if gkind == "route":
        return f"Address: {value}"
    if gkind == "model_provider":
        return f"Model access: {value}"
    return f"{gkind}: {value}"


# ── Suggestion construction ─────────────────────────────────────────────────

def _suggestion_id(origin_key: str, gkind: str, value: str) -> str:
    raw = f"{origin_key}|{gkind}|{value}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _make(origin_key: str, gkind: str, value: str, *, confidence: str, signal: str,
          why: str, evidence) -> dict:
    return {
        "id": _suggestion_id(origin_key, gkind, value),
        "origin_key": origin_key,
        "confidence": confidence,
        "signal": signal,
        "gkind": gkind,
        "value": value,
        "label": _label_for(gkind, value),
        "why": why,
        "capability": _capability_for(gkind, value),
        "risk": _risk_for(gkind, value),
        "risk_note": _risk_note(gkind, value),
        "evidence": [str(line) for line in (evidence or []) if str(line).strip()],
        "actionable": _is_actionable(gkind, value),
        "status": STATUS_OPEN,
        "decided_by": "",
        "decided_at": None,
        "reason": "",
    }


# ── Rules ───────────────────────────────────────────────────────────────────

def _route_candidate(pattern: str, exact: bool = False) -> str:
    """The route value that actually unblocks a catalog pattern for one person.

    is_route_allowed matches an exact path or a trailing wildcard, so a prefix
    pattern has to be suggested in its wildcard form: the bare prefix would
    open that one address and still block everything under it. An exact rule
    governs a single address and is opened by the address itself, so it is
    never widened into a wildcard here.
    """
    bare = str(pattern or "").rstrip("*").rstrip("/")
    return bare if exact else bare + "*"


def _route_already_open(access, pattern: str, exact: bool = False) -> bool:
    """True when this person can already reach what _route_candidate suggests.

    A plain membership test would report somebody who holds the wildcard as
    lacking the bare prefix, and hand an administrator a confirmed suggestion
    for access that person already has.
    """
    bare = str(pattern or "").rstrip("*").rstrip("/")
    if not bare:
        return False
    if exact:
        return access.is_route_allowed(bare)
    return access.is_route_allowed(bare) and access.is_route_allowed(bare + "/x")


def _route_permissions(path: str) -> list:
    """Both permissions a route can be scored against, read and write.

    The denial spool records no HTTP method, so picking one of the two would
    misreport half the rows; each is emitted separately with the kind of
    request that needs it named in its evidence.
    """
    out = []
    for method, human in (("GET", "opening it"), ("POST", "sending something to it")):
        name = route_permission(path, method)
        if name and not any(name == existing for existing, _ in out):
            out.append((name, human))
    return out


def _rule_route_needs_permission(origin_key, gkind, value, access) -> list:
    """The second wall behind an approved address.

    enforce.py admits a call only when the address is on the allowlist AND the
    permission is held. Approving the address on its own therefore leaves this
    person blocked one step later, which is the whole reason this screen exists.
    """
    if gkind != "route":
        return []
    rows = []
    for name, human in _route_permissions(value):
        if access.has_permission(name):
            continue
        rows.append(_make(
            origin_key, "permission", name,
            confidence=CONFIRMED,
            signal="route_needs_permission",
            why=(
                "Opening the address is only half of the check. This person "
                "still has to be allowed to do the thing behind it, and they "
                "are not, so approving the address alone leaves them stopped."
            ),
            evidence=[f"Needed for {human}.", "Checked on every request, not only the first."],
        ))
    return rows


def _rule_permission_depends_on(origin_key, wanted, access) -> list:
    """The smaller permissions a wanted one is useless without.

    Walked from the depends_on chain in api/capability_risk.py, which is keyed
    off the route catalog and the panel map rather than guessed here.
    """
    rows, seen = [], set()
    queue = list(wanted)
    while queue:
        name = queue.pop(0)
        for parent in _permission_meta(name).get("depends_on") or ():
            parent = str(parent).strip()
            if not parent or parent in seen or parent in wanted:
                continue
            seen.add(parent)
            queue.append(parent)
            if access.has_permission(parent):
                continue
            rows.append(_make(
                origin_key, "permission", parent,
                confidence=CONFIRMED,
                signal="permission_depends_on",
                why=(
                    "The access above is built on this one. Without it the "
                    "screen still opens and then refuses to show anything."
                ),
                evidence=["Recorded with the permission itself, not inferred from usage."],
            ))
    return rows


def _rule_known_dependencies(origin_key, held_or_asked, access) -> list:
    """The hand-verified incident table (see KNOWN_DEPENDENCIES)."""
    rows = []
    for source in held_or_asked:
        known = KNOWN_DEPENDENCIES.get(source)
        if not known:
            continue
        evidence = [str(known.get("evidence") or "")]
        for name in known.get("permissions") or ():
            if access.has_permission(name):
                continue
            rows.append(_make(
                origin_key, "permission", name,
                confidence=CONFIRMED, signal="known_dependency",
                why=str(known.get("why") or ""), evidence=evidence,
            ))
        for pattern in known.get("routes") or ():
            if _route_already_open(access, pattern):
                continue
            rows.append(_make(
                origin_key, "route", _route_candidate(pattern),
                confidence=CONFIRMED, signal="known_dependency",
                why=str(known.get("route_why") or known.get("why") or ""),
                evidence=evidence,
            ))
    return rows


def _rule_model_provider_shape(origin_key, access) -> list:
    """Two policy shapes that refuse every turn without ever being a denial.

    Neither can file its own request: the engine maps no model refusal into the
    request spool, so they surface from the shape of what this person already
    has. Both are reported as information: the fix is a correction to an entry
    that is already there, not an extra grant, so there is no button.
    """
    rows = []
    try:
        providers = [str(p) for p in (access.grants.model_providers or ())]
    except Exception:
        return []
    if "*" in providers:
        return []
    # An alias of the form custom:<name> is rewritten to plain custom before
    # the model check runs, so a list holding only the aliased form matches
    # nothing and every turn is refused.
    if any(p.startswith("custom:") for p in providers) and "custom" not in providers:
        rows.append(_make(
            origin_key, "model_provider", "custom",
            confidence=CONFIRMED,
            signal="provider_alias",
            why=(
                "This person's model access is written in a form the assistant "
                "rewrites before it checks it, so the check never matches and "
                "every message is refused."
            ),
            evidence=["Comes from what is recorded for this person, not from a blocked attempt."],
        ))
    for provider in providers:
        lowered = provider.lower()
        if provider == lowered or lowered in providers:
            continue
        rows.append(_make(
            origin_key, "model_provider", lowered,
            confidence=CONFIRMED,
            signal="provider_case",
            why=(
                "This entry is written with capital letters. The check lowers "
                "the incoming name but not the recorded one, so the two never "
                "match and every message is refused."
            ),
            evidence=["Comes from what is recorded for this person, not from a blocked attempt."],
        ))
    return rows


def _audit_ts(row) -> float:
    """Epoch seconds for an audit row, or 0.0.

    Audit rows store an ISO-8601 timestamp while approvals rows store an epoch
    float, so the two cannot be compared without this.
    """
    try:
        parsed = datetime.fromisoformat(str(row.get("ts") or ""))
        return parsed.timestamp()
    except Exception:
        return 0.0


def _rule_audit_co_denials(origin_key, email, requested_at, access, covered) -> list:
    """Everything else this person was stopped by around the same time.

    A correlation, never a dependency: being stopped somewhere else is not
    proof that this request needs it.
    """
    try:
        rows = read_audit_events(_AUDIT_SCAN_LIMIT)
    except Exception as exc:  # pragma: no cover: the detail must still render
        logger.debug("suggestion audit scan failed: %s", exc)
        return []
    wanted_hash = _hash_identity(email)
    if not wanted_hash:
        return []
    anchor = float(requested_at or 0.0) or time.time()
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("subject_email_hash") != wanted_hash:
            continue
        if str(row.get("event") or "") not in ("deny", "would_deny"):
            continue
        when = _audit_ts(row)
        if when and abs(when - anchor) > _AUDIT_WINDOW_SECONDS:
            continue
        reason = str(row.get("reason") or "")
        extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
        resource = str(extra.get("resource") or "").strip()
        path = str(row.get("path") or "").strip()
        if reason == "permission_not_allowed" and resource:
            pair = ("permission", resource)
        elif reason in ("route_not_allowed", "unknown_route") and path:
            pair = ("route", path)
        else:
            continue
        counts[pair] = counts.get(pair, 0) + 1
    out = []
    for (gkind, value), hits in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if (gkind, value) in covered:
            continue
        if gkind == "permission" and access.has_permission(value):
            continue
        if gkind == "route" and access.is_route_allowed(value):
            continue
        if not _is_visible(gkind, value):
            continue
        out.append(_make(
            origin_key, gkind, value,
            confidence=HEURISTIC,
            signal="audit_co_denial",
            why=(
                "This person keeps running into this as well, around the same "
                "time as the request you are looking at. It may be the same "
                "piece of work, or something unrelated."
            ),
            evidence=[f"Stopped here {hits} times in the last seven days."],
        ))
        if len(out) >= _MAX_PER_SIGNAL:
            break
    return out


def _rule_open_asks(origin_key, email, covered) -> list:
    """Other requests from the same person still waiting for a decision."""
    try:
        from api import approvals

        rows = approvals.list_all(kinds=[approvals.KIND_GRANT], owner_scope=email)
    except Exception as exc:  # pragma: no cover
        logger.debug("suggestion open-ask scan failed: %s", exc)
        return []
    out = []
    for entry in rows:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status") or "pending") != "pending":
            continue
        if str(entry.get("key") or "") == origin_key:
            continue
        payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
        gkind = str(payload.get("gkind") or "").strip()
        value = str(payload.get("value") or "").strip()
        if not gkind or not value or (gkind, value) in covered:
            continue
        if not _is_visible(gkind, value):
            continue
        out.append(_make(
            origin_key, gkind, value,
            confidence=HEURISTIC,
            signal="open_ask",
            why=(
                "The same person is already waiting on this one too. Deciding "
                "both now saves them a second round trip."
            ),
            evidence=["Already in this queue as a request of its own."],
        ))
        if len(out) >= _MAX_PER_SIGNAL:
            break
    return out


def _rule_shared_permission_routes(origin_key, gkind, value, access, covered) -> list:
    """Other addresses that answer to the permission this request is about.

    Sharing a permission is not proof the person needs the address, so this is
    heuristic on purpose.
    """
    if gkind != "route":
        return []
    wanted = {name for name, _ in _route_permissions(value)}
    if not wanted:
        return []
    out = []
    for rule in ROUTE_CATALOG:
        names = {rule.permission_for("GET"), rule.permission_for("POST")} - {None}
        if not names & wanted:
            continue
        if rule.matches(str(value or "").rstrip("*")):
            # The rule the request is already about: proposing it back would
            # read as a second, different suggestion for the same address.
            continue
        exact = rule.match == "exact"
        candidate = _route_candidate(rule.pattern, exact)
        if _route_already_open(access, rule.pattern, exact):
            continue
        if ("route", candidate) in covered or not _is_visible("route", candidate):
            continue
        out.append(_make(
            origin_key, "route", candidate,
            confidence=HEURISTIC,
            signal="shared_permission_route",
            why=(
                "This address is governed by the same permission as the "
                "request above. It is often part of the same job, but nothing "
                "here says this person needs it."
            ),
            evidence=["Grouped with the request under one permission."],
        ))
        if len(out) >= _MAX_PER_SIGNAL:
            break
    return out


# ── Public API ──────────────────────────────────────────────────────────────

def suggestions_for(entry, policy) -> list:
    """Related access proposals for one pending access request. Never raises.

    Read-only in every sense: it resolves what the requester already has and
    replays the checks that will stop them next. Nothing here writes, and
    nothing here is applied until an administrator decides it one row at a time.
    """
    try:
        if not isinstance(entry, dict) or str(entry.get("kind") or "") != "grant":
            return []
        if not policy or not policy.enabled:
            # An advisory list implying a block that is not happening would be
            # worse than no list at all.
            return []
        payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
        email = str(payload.get("email") or entry.get("owner_email") or "").strip().lower()
        gkind = str(payload.get("gkind") or "").strip()
        value = str(payload.get("value") or "").strip()
        origin_key = str(entry.get("key") or "").strip()
        if not email or not gkind or not value or not origin_key:
            return []
        if email in {str(a).strip().lower() for a in (policy.bootstrap_admins or ())}:
            return []
        access = resolve_effective_access(policy, GovernanceSubject(email=email))
        if "*" in access.permissions or "*" in access.routes:
            # Nothing to complete: this person is not walled in anywhere.
            return []

        confirmed = _rule_route_needs_permission(origin_key, gkind, value, access)
        asked = [row["value"] for row in confirmed]
        if gkind == "permission":
            asked.append(value)
        confirmed += _rule_known_dependencies(
            origin_key, sorted(set(asked) | set(access.permissions)), access
        )
        # Walked last, over everything named above, so the smaller permission a
        # dependency is itself built on is not left out of the same review.
        wanted = [row["value"] for row in confirmed if row["gkind"] == "permission"] + asked
        confirmed += _rule_permission_depends_on(origin_key, wanted, access)
        confirmed += _rule_model_provider_shape(origin_key, access)

        rows, seen = [], {(gkind, value)}
        for row in confirmed:
            pair = (row["gkind"], row["value"])
            if pair in seen or not _is_visible(*pair):
                continue
            seen.add(pair)
            rows.append(row)

        heuristic = _rule_audit_co_denials(
            origin_key, email, entry.get("requested_at"), access, seen
        )
        heuristic += _rule_open_asks(origin_key, email, seen | {
            (r["gkind"], r["value"]) for r in heuristic
        })
        heuristic += _rule_shared_permission_routes(origin_key, gkind, value, access, seen | {
            (r["gkind"], r["value"]) for r in heuristic
        })
        for row in heuristic:
            pair = (row["gkind"], row["value"])
            if pair in seen:
                continue
            seen.add(pair)
            rows.append(row)
        return rows
    except Exception as exc:  # pragma: no cover: the review detail must render
        logger.debug("related suggestions failed: %s", exc)
        return []


def find_suggestion(entry, policy, gkind: str, value: str):
    """The one suggestion this engine derives for (gkind, value), or None.

    The decide handler authorises against THIS, never against the body it was
    posted: the pair a client names is only ever used to look a derived row up.
    """
    for row in suggestions_for(entry, policy):
        if row["gkind"] == str(gkind or "") and row["value"] == str(value or ""):
            return row
    return None


def apply_decisions(rows, decisions) -> list:
    """Overlay stored deny/ignore decisions so a set-aside row stays visible.

    An administrator has to be able to see what was already decided on this
    request; a suggestion that simply disappeared would look like a bug.
    """
    stored = decisions if isinstance(decisions, dict) else {}
    out = []
    for row in rows:
        row = dict(row)
        found = stored.get(decision_key(row.get("origin_key") or "", row["gkind"], row["value"]))
        if isinstance(found, dict):
            row["status"] = str(found.get("status") or STATUS_OPEN)
            row["decided_by"] = str(found.get("decided_by") or "")
            row["decided_at"] = found.get("decided_at")
            row["reason"] = str(found.get("reason") or "")
        out.append(row)
    return out


# ── Decision store ──────────────────────────────────────────────────────────
# Deny and ignore live HERE and never in the approvals registry. api/
# grant_requests.ingest_spool skips a decided row, so writing a rejected
# registry row on deny would permanently silence a wall this person has not hit
# yet: a heuristic guess would pre-empt a genuine future request. Keyed per
# origin request so setting something aside in one review does not silence it
# in the next one, where it may well be a confirmed dependency.

def _decisions_path() -> Path:
    from api import config

    return Path(config.STATE_DIR) / _DECISIONS_NAME


def decision_key(origin_key: str, gkind: str, value: str) -> str:
    return f"{origin_key}|{gkind}|{value}"


def load_decisions() -> dict:
    """Every stored decision. Total: a corrupt or missing file reads as {}."""
    try:
        data = json.loads(_decisions_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def record_decision(origin_key: str, gkind: str, value: str, *, status: str,
                    decided_by: str = "", reason: str = "", confidence: str = "",
                    signal: str = "") -> dict:
    """Store one decision. Atomic same-directory replace under a module lock."""
    row = {
        "status": str(status or STATUS_OPEN),
        "decided_by": str(decided_by or "").strip().lower(),
        "decided_at": time.time(),
        "reason": str(reason or "").strip(),
        "origin_key": str(origin_key or ""),
        "gkind": str(gkind or ""),
        "value": str(value or ""),
        "confidence": str(confidence or ""),
        "signal": str(signal or ""),
    }
    with _DECISIONS_LOCK:
        store = load_decisions()
        store[decision_key(origin_key, gkind, value)] = row
        path = _decisions_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(store, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    return row
