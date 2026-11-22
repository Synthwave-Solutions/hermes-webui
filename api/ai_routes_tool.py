"""Chat tool for the AI model routes of a Cloud environment (``ai_routes``).

An organisation owner or admin can see and change the AI model routes of
their environment from the Super Agent chat. The control plane has signed
installation routes for it under ``/v1/customer/ai-routes`` (the installation
signature plus the person's own Cloud session); this tool is the only thing
in the WebUI that calls them.

What the tool guarantees, whatever the model asks for:

* **Who.** Only the person whose chat turn this is, and only when that turn
  was started from a personal Cloud session by somebody who is an organisation
  admin in the team structure. A partner, a department admin and a normal user
  are refused before anything is sent. The control plane checks the person's
  role in the Cloud once more.
* **Approval.** Every change shows the standard approval card of the chat
  first (one approval for one change, no session or permanent shortcut). Only
  after the person approved is the call sent, with ``confirmed: true``. The
  model cannot set that flag: it is not an argument.
* **No secret.** There is no argument for a key. Arguments are a closed set,
  and a value that looks like a key is refused without being used, stored or
  repeated. When a key is needed the answer holds ``secure_form_url``, a link
  to the account page where the person types the key themselves.
* **Bounded answers.** What comes back from the control plane is reduced to
  known fields before the model sees it.

The tool registers in its own toolset (``synthpulse_cloud``). A turn only gets
that toolset when the caller could use it (see ``toolsets_for``), so nobody
else is even offered the tool.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

TOOL_NAME = "ai_routes"
TOOLSET = "synthpulse_cloud"
PREFIX = "/v1/customer/ai-routes"

READS = ("overview", "job")
CHANGES = ("prepare_connection", "test", "enable", "disable", "delete", "place_in_route", "set_limits")
ACTIONS = READS + CHANGES
PROVIDERS = ("openai", "anthropic", "google", "azure-openai", "mistral", "openrouter", "scaleway", "nebius", "ovhcloud", "regolo", "melious")
ROUTE_PLACES = ("none", "primary", "fallback")

_CONNECTION_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
_JOB_ID = re.compile(r"^job_[a-f0-9]{32}$")
_MODEL = re.compile(r"^[A-Za-z0-9_.:/-]{1,140}$")
_LABEL = re.compile(r"^[^\x00-\x1f()]{2,80}$")
_NOTE = re.compile(r"^[^\x00-\x1f]{12,500}$")
_ARGUMENTS = {"action", "connection_id", "job_id", "provider", "label", "route", "model", "enabled",
              "monthly_limit_cents", "expected_revision", "note"}
# A value that looks like a credential: a well-known key prefix, a header, a
# private key, or one long unbroken token that mixes letters and digits.
_SECRET_PREFIX = re.compile(r"(?i)(?:\bsk-[a-z0-9_-]{8,}|\bsk_(?:live|test)_|\bpk_(?:live|test)_|\brk_live_|\bAKIA[0-9A-Z]{12,}|\bAIza[0-9A-Za-z_-]{20,}"
                            r"|\bgh[pousr]_[A-Za-z0-9]{20,}|\bxox[abprs]-|\bBearer\s+\S{8,}|-----BEGIN [A-Z ]*PRIVATE KEY|\bey[A-Za-z0-9_-]{10,}\.ey[A-Za-z0-9_-]{10,})")
_SECRET_TOKEN = re.compile(r"[A-Za-z0-9_+/=-]{28,}")
_SECRET_NAMES = re.compile(r"(?i)(secret|api[_-]?key|\bkey\b|token|password|passwd|authorization|credential)")

SECRET_REFUSED = ("Een sleutel hoort niet in de chat. Er is niets mee gedaan en hij is niet bewaard. Laat de persoon die sleutel nu "
                  "intrekken bij de aanbieder, omdat hij in een chat heeft gestaan, en een nieuwe maken. Bereid daarna de verbinding voor "
                  "(prepare_connection): het antwoord bevat een link naar de beveiligde pagina waar de nieuwe sleutel wordt ingevuld.")
NOT_ALLOWED = ("Alleen een eigenaar of beheerder van de organisatie beheert de AI-routes, aangemeld met het eigen Cloud-account. "
               "Vraag een eigenaar of beheerder van je organisatie.")
NEEDS_PERSONAL = "Open de werkplek vanuit je persoonlijke Cloud-account om de AI-routes te beheren."
NOT_APPROVED = "De wijziging is niet goedgekeurd en is niet uitgevoerd."

_REGISTERED = False
_REGISTER_LOCK = threading.Lock()


class Refused(Exception):
    """A refusal with a code and a text for the person. Never carries an argument value."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ── Who is asking ────────────────────────────────────────────────────────────

def _turn_identity() -> dict | None:
    """The authenticated sender of the chat turn this tool call belongs to, or None.

    Read from the turn's trusted authority, never from tool arguments, the
    session owner or a fallback.
    """
    try:
        from api.governance import continuation

        authority = continuation._CURRENT_REF.get()
        if authority is None:
            return None
        record = authority.pending
        if record is None:
            path = continuation._directory() / (authority.reference + ".json")
            if path.stat().st_size > 256000:
                return None
            record = json.loads(path.read_text(encoding="utf-8"))
        return continuation._identity(record.get("identity"))
    except Exception:
        return None


def caller(identity: dict | None = None) -> dict:
    """``{email, acting, proof}`` of an organisation admin in a personal Cloud session. Raises Refused."""
    from api import auth, control_plane_client, msp_service, org_structure
    from api.governance import loader
    from api.governance.enforce import subject_from_identity

    identity = identity if identity is not None else _turn_identity()
    email = str((identity or {}).get("email") or "").strip().lower()
    if not email:
        raise Refused("forbidden", NOT_ALLOWED)
    try:
        if not control_plane_client.configured():
            raise Refused("not_configured", "Deze omgeving is niet gekoppeld aan de Cloud. De AI-routes zijn hier niet te beheren.")
        policy = loader.get_policy()
        subject = subject_from_identity(identity, policy)
        if org_structure.partner_for(email) is not None:
            raise Refused("forbidden", NOT_ALLOWED)
        view = org_structure.scope_for(email, policy=policy, subject=subject)
        if view.scope != org_structure.SCOPE_ALL or view.is_partner:
            raise Refused("forbidden", NOT_ALLOWED)
        if str(identity.get("method") or "") != "synthpulse_cloud":
            raise Refused("personal_login_required", NEEDS_PERSONAL)
        proof = auth.cloud_msp_proof_for_email(email)
        if not proof:
            raise Refused("personal_login_required", NEEDS_PERSONAL)
        acting = msp_service.acting_for(policy, email, "synthpulse_cloud")
    except Refused:
        raise
    except PermissionError:
        raise Refused("forbidden", NOT_ALLOWED) from None
    except Exception:
        logger.warning("ai_routes: caller check failed", exc_info=True)
        raise Refused("unavailable", "De rechten voor de AI-routes zijn nu niet te controleren. Probeer het later opnieuw.") from None
    return {"email": email, "acting": acting, "proof": proof}


def eligible(identity: dict | None) -> bool:
    """Whether this sender could use the tool at all. Never raises."""
    try:
        caller(identity)
        return True
    except Exception:
        return False


def toolsets_for(toolsets, identity: dict | None):
    """The turn's toolsets, with this tool's toolset for somebody who can use it and for nobody else."""
    names = [name for name in (toolsets or []) if name != TOOLSET]
    if eligible(identity):
        register_tool()
        names.append(TOOLSET)
    return names


# ── Arguments: a closed set, and never a secret ──────────────────────────────

def _looks_secret(value: str, *, tokens: bool = True) -> bool:
    if _SECRET_PREFIX.search(value):
        return True
    if not tokens:
        return False
    return any(re.search(r"[A-Za-z]", token) and re.search(r"[0-9]", token) for token in _SECRET_TOKEN.findall(value))


def check_arguments(args) -> dict:
    """The validated arguments. Raises Refused; a refusal never repeats a value."""
    if not isinstance(args, dict):
        raise Refused("invalid", "Geef de actie op.")
    extra = set(args) - _ARGUMENTS
    if any(_SECRET_NAMES.search(str(name)) for name in extra):
        raise Refused("secret_refused", SECRET_REFUSED)
    if extra:
        raise Refused("invalid", "Onbekende velden. Gebruik alleen de velden van deze tool.")
    for name, value in args.items():
        if isinstance(value, (dict, list)):
            raise Refused("invalid", "Onbekende velden. Gebruik alleen de velden van deze tool.")
        # An id has its own strict shape below; everything free to type is checked for a key.
        if isinstance(value, str) and name not in ("job_id",) and _looks_secret(value, tokens=name in ("label", "note")):
            raise Refused("secret_refused", SECRET_REFUSED)
    action = args.get("action")
    if action not in ACTIONS:
        raise Refused("invalid", "Onbekende actie. Kies uit: " + ", ".join(ACTIONS) + ".")
    out = {"action": action}

    def text(name, pattern, message):
        value = args.get(name)
        if not isinstance(value, str) or not pattern.fullmatch(value.strip()):
            raise Refused("invalid", message)
        out[name] = value.strip()

    if action == "job":
        text("job_id", _JOB_ID, "Geef het id van de actie (job_id) zoals het eerdere antwoord het gaf.")
    if action in ("test", "enable", "disable", "delete", "place_in_route"):
        text("connection_id", _CONNECTION_ID, "Geef het id van de verbinding (connection_id) uit het overzicht.")
    if action in ("prepare_connection", "place_in_route"):
        if args.get("route", "none") not in ROUTE_PLACES:
            raise Refused("invalid", "Kies de plek in de route: none, primary of fallback.")
        out["route"] = args.get("route", "none")
        if out["route"] != "none" or args.get("model"):
            text("model", _MODEL, "Kies het model dat je in de route wilt opnemen.")
        if (out["route"] != "none") != bool(out.get("model")):
            raise Refused("invalid", "Kies het model dat je in de route wilt opnemen.")
    if action == "prepare_connection":
        if args.get("provider") not in PROVIDERS:
            raise Refused("invalid", "Kies een aanbieder uit het overzicht (providers).")
        out["provider"] = args["provider"]
        text("label", _LABEL, "Geef de verbinding een naam van 2 tot 80 tekens die de organisatie herkent.")
    if action == "set_limits":
        if not isinstance(args.get("enabled"), bool):
            raise Refused("invalid", "Geef aan of AI-gebruik aan staat (enabled: true of false).")
        limit = args.get("monthly_limit_cents")
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 10000000):
            raise Refused("invalid", "De maandlimiet is een bedrag in centen, of leeg voor geen limiet.")
        revision = args.get("expected_revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise Refused("invalid", "Lees eerst het overzicht en geef de huidige revisie mee (expected_revision).")
        text("note", _NOTE, "Vraag de persoon waarom de limiet verandert (note, minstens 12 tekens).")
        out.update(enabled=args["enabled"], monthly_limit_cents=limit, expected_revision=revision)
    return out


# ── What a change is, in words the person approves ───────────────────────────

def _euros(cents) -> str:
    return "€ " + f"{cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def describe(a: dict) -> tuple[str, str]:
    """``(target, reason)`` for the approval card: what changes, in Dutch, without a value that could be a key."""
    action = a["action"]
    if action == "prepare_connection":
        place = {"none": "nog niet in de route", "primary": "als eerste in de route", "fallback": "als terugval in de route"}[a["route"]]
        return (f"AI-routes: eigen verbinding voorbereiden ({a['provider']})",
                f"Een eigen verbinding met {a['provider']} voorbereiden onder de naam \"{a['label']}\", {place}"
                + (f" met model {a['model']}" if a.get("model") else "") + ". De sleutel wordt daarna op de beveiligde pagina ingevuld, niet in de chat. "
                "Gebruik op een eigen sleutel rekent de aanbieder af met de organisatie.")
    if action == "set_limits":
        limit = "geen maandlimiet" if a["monthly_limit_cents"] is None else "een maandlimiet van " + _euros(a["monthly_limit_cents"])
        return ("AI-routes: maandlimiet van deze omgeving",
                f"AI-gebruik van deze omgeving {'aan' if a['enabled'] else 'pauzeren'}, met {limit}. Reden: {a['note']}")
    what = {"test": "testen", "enable": "aanzetten", "disable": "uitzetten", "delete": "verwijderen",
            "place_in_route": "in de route plaatsen"}[action]
    name = f"\"{a['connection_label']}\" ({a['connection_id']})" if a.get("connection_label") else a["connection_id"]
    detail = ""
    if action == "place_in_route":
        detail = {"none": " (uit de route halen)", "primary": f" (als eerste, model {a.get('model')})",
                  "fallback": f" (als terugval, model {a.get('model')})"}[a["route"]]
    return (f"AI-routes: verbinding {a['connection_id']} {what}", f"De verbinding {name} van deze omgeving {what}{detail}.")


def request_approval(target: str, reason: str, operation_id: str) -> dict:
    """The standard approval card of the chat for one change. Fails closed without the engine."""
    try:
        from tools.approval import request_governance_action_approval
    except Exception:
        return {"approved": False, "message": "Goedkeuren is hier niet beschikbaar."}
    return request_governance_action_approval(TOOL_NAME, target, reason, operation_id)


# ── Answers: known fields only ───────────────────────────────────────────────

def _t(value, limit=200):
    return " ".join(str(value).split())[:limit] if isinstance(value, (str, int, float)) and not isinstance(value, bool) else ""


def _form_url(value) -> str:
    """The secure form link, only when it is an https address without credentials."""
    text = str(value or "")
    try:
        parts = urlsplit(text)
    except ValueError:
        return ""
    return text[:600] if parts.scheme == "https" and parts.hostname and "@" not in parts.netloc and len(text) <= 600 else ""


def _job(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    result = raw.get("result") if isinstance(raw.get("result"), dict) else {}
    out = {"job_id": _t(raw.get("id"), 80), "action": _t(raw.get("action"), 60), "status": _t(raw.get("status"), 30),
           "stage": _t(raw.get("stage"), 60), "error_code": _t(raw.get("error_code"), 80) or None}
    if isinstance(result.get("valid"), bool):
        out["valid"] = result["valid"]
    return out


def clean_overview(data) -> dict:
    data = data if isinstance(data, dict) else {}
    rows = lambda key: [r for r in (data.get(key) if isinstance(data.get(key), list) else [])[:60] if isinstance(r, dict)]
    billing = data.get("billing") if isinstance(data.get("billing"), dict) else {}
    limits = data.get("limits") if isinstance(data.get("limits"), dict) else {}
    out = {
        "mode": _t(data.get("mode"), 20), "stale": data.get("stale") is True, "checked_at": data.get("checked_at") if isinstance(data.get("checked_at"), (int, float)) else None,
        "active_route": [{"position": r.get("position") if isinstance(r.get("position"), int) else None, "model": _t(r.get("model"), 140),
                          "provider": _t(r.get("provider"), 40), "provider_label": _t(r.get("provider_label"), 60),
                          "available": r.get("available") is True, "billing": _t(r.get("billing"), 30) or None} for r in rows("active_route")],
        "connections": [{"id": _t(r.get("id"), 120), "provider": _t(r.get("provider"), 40), "provider_label": _t(r.get("provider_label"), 60),
                         "label": _t(r.get("label"), 80), "owner": _t(r.get("owner"), 20), "enabled": r.get("enabled") is True,
                         "status": _t(r.get("status"), 40), "billing": _t(r.get("billing"), 30) or None, "editable": r.get("editable") is True}
                        for r in rows("connections")],
        "connection_requests": [{"request_id": _t(r.get("request_id") or r.get("id"), 40), "provider": _t(r.get("provider"), 40),
                                 "label": _t(r.get("label"), 80), "route": _t(r.get("route"), 20), "model": _t(r.get("model"), 140) or None}
                                for r in rows("connection_requests")],
        "subscriptions": [{"provider": _t(r.get("provider"), 40), "account": _t(r.get("account") or r.get("email"), 120), "owner": _t(r.get("owner"), 20)}
                          for r in rows("subscriptions")],
        "providers": [{"id": _t(r.get("id"), 40), "label": _t(r.get("label"), 60), "region": _t(r.get("region"), 40)} for r in rows("providers")],
        "billing_notice": _t(billing.get("notice"), 600) or None,
        "limits": {"enabled": limits.get("enabled") if isinstance(limits.get("enabled"), bool) else None,
                   "monthly_limit_cents": limits.get("monthly_limit_cents") if isinstance(limits.get("monthly_limit_cents"), int) else None,
                   "revision": limits.get("revision") if isinstance(limits.get("revision"), int) else None} if limits else None,
        "jobs": [_job(r) for r in rows("jobs")[:10]],
        "secure_form_url": _form_url(data.get("secure_form_url")) or None,
    }
    out["card"] = overview_card(out)
    out["card_instruction"] = "Toon het blok uit 'card' ongewijzigd in je antwoord en vat daaronder in een of twee zinnen samen."
    return out


_BILLING_NL = {"prepaid_ledger": "AI-tegoed", "customer_own_key": "Eigen sleutel", "synthwave_contract": "Via Synthwave",
               "subscription": "Abonnement", "mixed": "Gemengd"}


def overview_card(view: dict) -> str:
    """The overview as one compact table block that the chat draws itself (no model code)."""
    rows = [[r["position"] or index, r["model"], r["provider_label"] or r["provider"],
             _BILLING_NL.get(r["billing"] or "", "Onbekend"), "Ja" if r["available"] else "Nee"]
            for index, r in enumerate(view["active_route"], 1)]
    own = sum(1 for c in view["connections"] if c["editable"])
    waiting = len(view["connection_requests"])
    parts = [("Via de modelrouter" if view["mode"] == "router" else "Rechtstreeks, nog niet via de modelrouter"),
             f"{own} eigen verbinding" + ("" if own == 1 else "en")]
    if waiting:
        parts.append(f"{waiting} wacht op een sleutel")
    if view["stale"]:
        parts.append("overzicht ouder dan tien minuten")
    spec = {"title": "AI-routes van deze omgeving", "subtitle": ", ".join(parts), "lang": "nl",
            "columns": ["Plek", "Model", "Aanbieder", "Afrekening", "Beschikbaar"], "rows": rows}
    return "```table\n" + json.dumps(spec, ensure_ascii=False) + "\n```"


def _error_text(status: int, data) -> str:
    detail = ""
    if isinstance(data, dict):
        raw = data.get("detail") if isinstance(data.get("detail"), str) else (data.get("error") or {}).get("message") if isinstance(data.get("error"), dict) else ""
        detail = _t(raw, 300)
    if detail and not _looks_secret(detail):
        return detail
    return {403: NOT_ALLOWED, 404: "Niet gevonden in deze omgeving.", 409: "Dit kan nu niet. Lees het overzicht opnieuw.",
            422: "Controleer de gegevens. Een sleutel hoort niet in de chat."}.get(status, "De Cloud is nu niet bereikbaar. Probeer het later opnieuw.")


# ── The call ────────────────────────────────────────────────────────────────

def run(args, identity: dict | None = None, approve=None) -> dict:
    """One tool call. Returns the answer for the model; never raises."""
    from api import control_plane_client

    try:
        a = check_arguments(args)
        who = caller(identity)
    except Refused as refusal:
        return {"ok": False, "error": refusal.code, "message": refusal.message}

    def send(method, path, body=None):
        return control_plane_client.call(method, PREFIX + path, body=body, acting=who["acting"], cloud_session=who["proof"])

    action = a["action"]
    try:
        if action == "overview":
            status, data = send("GET", "")
            return {"ok": True, **clean_overview(data)} if status == 200 else {"ok": False, "error": "refused", "message": _error_text(status, data)}
        if action == "job":
            status, data = send("GET", "/jobs/" + a["job_id"])
            return {"ok": True, **_job(data)} if status == 200 else {"ok": False, "error": "refused", "message": _error_text(status, data)}

        if a.get("connection_id"):
            # Read first: only an own connection of the organisation can be changed, and the card names it.
            status, data = send("GET", "")
            if status != 200:
                return {"ok": False, "error": "refused", "message": _error_text(status, data)}
            found = next((c for c in clean_overview(data)["connections"] if c["id"] == a["connection_id"]), None)
            if found is None:
                return {"ok": False, "error": "not_found", "message": "Deze verbinding staat niet in het overzicht van deze omgeving."}
            if not found["editable"]:
                return {"ok": False, "error": "not_editable", "message": "Deze verbinding wordt beheerd door Synthwave en is hier niet te wijzigen."}
            a["connection_label"] = found["label"]
        # A change: the person approves this one change on the approval card, and only then is it sent.
        target, reason = describe(a)
        decision = (approve or request_approval)(target, reason, uuid.uuid4().hex)
        if not (isinstance(decision, dict) and decision.get("approved") is True):
            return {"ok": False, "error": "not_approved", "message": NOT_APPROVED}
        request_key = str(uuid.uuid4())
        if action == "prepare_connection":
            body = {"provider": a["provider"], "label": a["label"], "route": a["route"], "confirmed": True}
            if a.get("model"):
                body["model"] = a["model"]
            status, data = send("POST", "/connection-requests", body)
            if status not in (200, 201) or not isinstance(data, dict):
                return {"ok": False, "error": "refused", "message": _error_text(status, data)}
            link = _form_url(data.get("secure_form_url"))
            return {"ok": True, "request_id": _t(data.get("request_id"), 40), "provider": a["provider"], "label": a["label"], "route": a["route"],
                    "model": a.get("model"), "secure_form_url": link or None,
                    "link": f"[Open de beveiligde pagina om de sleutel in te vullen]({link})" if link else None,
                    "billing_notice": _t(data.get("billing_notice"), 600) or None,
                    "next_step": "Geef de persoon de link. De sleutel wordt daar ingevuld en getest; typ of vraag de sleutel nooit in de chat."}
        if action == "set_limits":
            body = {"enabled": a["enabled"], "monthly_limit_cents": a["monthly_limit_cents"], "expected_revision": a["expected_revision"],
                    "note": a["note"], "confirmed": True}
            status, data = send("POST", "/limits", body)
            if status not in (200, 201) or not isinstance(data, dict):
                return {"ok": False, "error": "refused", "message": _error_text(status, data)}
            return {"ok": True, "enabled": data.get("enabled") if isinstance(data.get("enabled"), bool) else a["enabled"],
                    "monthly_limit_cents": data.get("monthly_limit_cents") if isinstance(data.get("monthly_limit_cents"), int) else a["monthly_limit_cents"],
                    "revision": data.get("revision") if isinstance(data.get("revision"), int) else None}
        body = {"request_key": request_key, "confirmed": True}
        if action == "place_in_route":
            body.update(route=a["route"], model=a.get("model"))
        suffix = {"place_in_route": "route"}.get(action, action)
        status, data = send("POST", f"/connections/{a['connection_id']}/{suffix}", body)
        if status not in (200, 201, 202) or not isinstance(data, dict):
            return {"ok": False, "error": "refused", "message": _error_text(status, data)}
        return {"ok": True, **_job(data), "next_step": "Volg de actie met action=job en dit job_id tot de status succeeded of failed is."}
    except Exception:
        logger.exception("ai_routes tool call failed")
        return {"ok": False, "error": "unavailable", "message": "De Cloud is nu niet bereikbaar. Probeer het later opnieuw."}


def handle(args, **_kwargs) -> str:
    return json.dumps(run(args), ensure_ascii=False)


SCHEMA = {
    "name": TOOL_NAME,
    "description": (
        "See and change the AI model routes of this SynthPulse Cloud environment, for an organisation owner or admin in their own "
        "Cloud session. action=overview shows the active route, the connections and the providers; show its 'card' block as is. "
        "Changes (prepare_connection, test, enable, disable, delete, place_in_route, set_limits) each show the approval card to the "
        "person first and are sent only after approval; never claim a change happened when the answer says not_approved. "
        "A provider key is never an argument and never belongs in the chat: prepare_connection returns a link to the secure page "
        "where the person types the key. After a change, follow it with action=job."),
    "parameters": {"type": "object", "additionalProperties": False, "required": ["action"], "properties": {
        "action": {"type": "string", "enum": list(ACTIONS)},
        "connection_id": {"type": "string", "description": "Id of an own (editable) connection from the overview"},
        "job_id": {"type": "string", "description": "Id of a change, to follow it"},
        "provider": {"type": "string", "enum": list(PROVIDERS)},
        "label": {"type": "string", "description": "Name the organisation recognises, 2 to 80 characters", "maxLength": 80},
        "route": {"type": "string", "enum": list(ROUTE_PLACES), "description": "Place in the route"},
        "model": {"type": "string", "description": "Model to place in the route when route is primary or fallback", "maxLength": 140},
        "enabled": {"type": "boolean", "description": "set_limits: AI use on (true) or paused (false)"},
        "monthly_limit_cents": {"type": ["integer", "null"], "description": "set_limits: monthly limit in cents, null for none"},
        "expected_revision": {"type": "integer", "description": "set_limits: the revision from the overview"},
        "note": {"type": "string", "description": "set_limits: why the limit changes, in the person's words (at least 12 characters)", "maxLength": 500}}},
}


def register_tool() -> bool:
    """Register the tool with the engine once. False when the engine is not there."""
    global _REGISTERED
    with _REGISTER_LOCK:
        if _REGISTERED:
            return True
        try:
            from tools.registry import registry
        except Exception:
            return False
        registry.register(name=TOOL_NAME, toolset=TOOLSET, emoji="🧭", check_fn=lambda: True,
                          description="See and change the AI model routes of this Cloud environment", schema=SCHEMA, handler=handle)
        _REGISTERED = True
        return True
