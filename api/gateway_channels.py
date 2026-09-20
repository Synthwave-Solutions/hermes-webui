"""Messaging channels (gateway platforms) and who may use them.

Michael asked on 20 Sep 2026 for a place in the WebUI to connect Telegram,
WhatsApp, Slack, Microsoft Teams, Discord and Google Chat, and to map a
person on such a platform to a person on this workstation so governance
follows them there too.

Three things live here:

* The channel catalog: which environment variables each platform needs in
  the profile's .env (the gateway reads them at start), which ones are
  secrets, and the allowlist variables the gateway's authorization uses.
  Values are written through api.providers._write_env_file and never read
  back to the browser; the API only says whether a variable is set.
* Pairing: the engine's DM pairing store (gateway/pairing.py). Unknown users
  who message the bot get a code; the admin approves the request here and,
  in the same step, says which colleague that platform user is.
* The identity map: STATE_DIR/gateway-identities.json,
  {platform: {user_id: {email, name, added_by, added_at}}}. The WebUI uses it
  to show a person their own messaging sessions; the gateway hook
  (gateway/run.py, vendored) uses it to bind the dashboard governance context
  of that person to the turn, so the same policy applies on Telegram as in
  the browser.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from pathlib import Path

from api.helpers import bad, j

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_USER_ID_RE = re.compile(r"^[A-Za-z0-9@._:+\-]{1,120}$")
_PROFILE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

# Platforms that receive HTTP webhooks from the provider and therefore need a
# public HTTPS URL. The gateway listens on these loopback ports and paths; we
# publish them through Tailscale Funnel as a path on port 8443 (Funnel allows
# only 443, 8443 and 10000), so the public URL is https://<node>:8443/hooks/<p>.
PUBLIC_HOOKS = {
    "whatsapp_cloud": {"port": 8090, "path": "/whatsapp/webhook", "mount": "/hooks/whatsapp",
                       "host_env": "WHATSAPP_CLOUD_WEBHOOK_HOST", "label": "Meta webhook callback URL"},
    "teams": {"port": 3978, "path": "/api/messages", "mount": "/hooks/teams",
              "host_env": "TEAMS_HOST", "label": "Azure Bot messaging endpoint"},
}
FUNNEL_PORT = 8443

# One entry per supported platform. ``fields`` are written to the profile
# .env; ``required`` decides whether the platform counts as configured.
CATALOG = [
    {
        "key": "telegram", "label": "Telegram", "engine": "telegram",
        "summary": "Bot via @BotFather. People DM the bot or use it in a group; unknown users receive a pairing code.",
        "fields": [
            {"key": "TELEGRAM_BOT_TOKEN", "label": "Bot token", "secret": True, "required": True,
             "hint": "From @BotFather (/newbot). Looks like 123456:ABC-DEF."},
            {"key": "TELEGRAM_HOME_CHANNEL", "label": "Home chat id", "secret": False, "required": False,
             "hint": "Chat id that receives proactive messages and alerts. Optional."},
        ],
        "allow_env": "TELEGRAM_ALLOWED_USERS", "allow_all_env": "TELEGRAM_ALLOW_ALL_USERS",
        "user_id_hint": "Numeric Telegram user id (the bot logs it, or ask @userinfobot).",
    },
    {
        "key": "whatsapp_cloud", "label": "WhatsApp Business", "engine": "whatsapp_cloud",
        "summary": "Meta WhatsApp Cloud API. Needs a Meta app, a phone number id and a public webhook URL (Funnel or domain).",
        "fields": [
            {"key": "WHATSAPP_CLOUD_ACCESS_TOKEN", "label": "Access token", "secret": True, "required": True,
             "hint": "System user token from the Meta app (permanent token recommended)."},
            {"key": "WHATSAPP_CLOUD_PHONE_NUMBER_ID", "label": "Phone number id", "secret": False, "required": True,
             "hint": "From WhatsApp, API setup in the Meta app."},
            {"key": "WHATSAPP_CLOUD_APP_ID", "label": "App id", "secret": False, "required": False, "hint": "Meta app id."},
            {"key": "WHATSAPP_CLOUD_APP_SECRET", "label": "App secret", "secret": True, "required": False,
             "hint": "Used to verify webhook signatures."},
            {"key": "WHATSAPP_CLOUD_VERIFY_TOKEN", "label": "Webhook verify token", "secret": True, "required": False,
             "hint": "Any string; enter the same value in the Meta webhook settings."},
            {"key": "WHATSAPP_CLOUD_WEBHOOK_HOST", "label": "Webhook host", "secret": False, "required": False,
             "hint": "Public HTTPS host the webhook is reachable on."},
        ],
        "allow_env": "WHATSAPP_CLOUD_ALLOWED_USERS", "allow_all_env": "WHATSAPP_CLOUD_ALLOW_ALL_USERS",
        "user_id_hint": "Phone number in international format without plus, e.g. 31612345678.",
    },
    {
        "key": "slack", "label": "Slack", "engine": "slack",
        "summary": "Slack app in Socket Mode: bot token plus app-level token, no public URL needed.",
        "fields": [
            {"key": "SLACK_BOT_TOKEN", "label": "Bot token (xoxb-)", "secret": True, "required": True,
             "hint": "OAuth and Permissions, Bot User OAuth Token. Scopes: chat:write, app_mentions:read, im:history, channels:history."},
            {"key": "SLACK_APP_TOKEN", "label": "App-level token (xapp-)", "secret": True, "required": True,
             "hint": "Basic Information, App-Level Tokens, scope connections:write (Socket Mode)."},
            {"key": "SLACK_HOME_CHANNEL", "label": "Home channel id", "secret": False, "required": False,
             "hint": "Channel id (C0...) for proactive messages. Optional."},
        ],
        "allow_env": "SLACK_ALLOWED_USERS", "allow_all_env": "SLACK_ALLOW_ALL_USERS",
        "user_id_hint": "Slack member id (U0...), from the profile menu, Copy member ID.",
    },
    {
        "key": "teams", "label": "Microsoft Teams", "engine": "teams",
        "summary": "Azure Bot registration. Needs a public HTTPS endpoint for the Bot Framework messaging URL.",
        "fields": [
            {"key": "TEAMS_CLIENT_ID", "label": "App (client) id", "secret": False, "required": True,
             "hint": "Microsoft App ID of the Azure Bot."},
            {"key": "TEAMS_CLIENT_SECRET", "label": "Client secret", "secret": True, "required": True,
             "hint": "Client secret of the bot's app registration."},
            {"key": "TEAMS_TENANT_ID", "label": "Tenant id", "secret": False, "required": True,
             "hint": "Entra ID tenant of the organisation (single-tenant bot)."},
            {"key": "TEAMS_HOST", "label": "Public host", "secret": False, "required": False,
             "hint": "Public HTTPS host for the messaging endpoint."},
        ],
        "allow_env": "TEAMS_ALLOWED_USERS", "allow_all_env": "TEAMS_ALLOW_ALL_USERS",
        "user_id_hint": "Entra object id or UPN (e-mail) of the Teams user.",
    },
    {
        "key": "discord", "label": "Discord", "engine": "discord",
        "summary": "Discord bot with the Message Content intent enabled in the developer portal.",
        "fields": [
            {"key": "DISCORD_BOT_TOKEN", "label": "Bot token", "secret": True, "required": True,
             "hint": "Developer portal, Bot, Reset Token. Enable Message Content Intent."},
            {"key": "DISCORD_HOME_CHANNEL", "label": "Home channel id", "secret": False, "required": False,
             "hint": "Channel id for proactive messages. Optional."},
        ],
        "allow_env": "DISCORD_ALLOWED_USERS", "allow_all_env": "DISCORD_ALLOW_ALL_USERS",
        "user_id_hint": "Discord user id (enable Developer Mode, right click, Copy User ID).",
    },
    {
        "key": "google_chat", "label": "Google Chat", "engine": "google_chat",
        "summary": "Chat app in the Google Cloud project with a Pub/Sub subscription; people are identified by their Workspace e-mail.",
        "fields": [
            {"key": "GOOGLE_CHAT_PROJECT_ID", "label": "Google Cloud project id", "secret": False, "required": True,
             "hint": "Project that hosts the Chat app and the Pub/Sub topic."},
            {"key": "GOOGLE_CHAT_SUBSCRIPTION_NAME", "label": "Pub/Sub subscription", "secret": False, "required": True,
             "hint": "Full name: projects/<project>/subscriptions/<name>."},
            {"key": "GOOGLE_CHAT_SERVICE_ACCOUNT_JSON", "label": "Service account key path", "secret": True, "required": True,
             "hint": "Path on this workstation to the service account JSON with Chat and Pub/Sub roles."},
        ],
        "allow_env": "GOOGLE_CHAT_ALLOWED_USERS", "allow_all_env": "GOOGLE_CHAT_ALLOW_ALL_USERS",
        "user_id_hint": "Workspace e-mail address of the person.",
    },
]
_BY_KEY = {p["key"]: p for p in CATALOG}
_FIELD_KEYS = {p["key"]: {f["key"] for f in p["fields"]} for p in CATALOG}


def _env_path() -> Path:
    from api.providers import _get_hermes_home
    return Path(_get_hermes_home()) / ".env"


def _env_values() -> dict:
    from api.providers import _load_env_file
    try:
        return _load_env_file(_env_path())
    except Exception:
        logger.debug("channels: could not read env", exc_info=True)
        return {}


def _identities_path() -> Path:
    from api import config
    return Path(config.STATE_DIR) / "gateway-identities.json"


def load_identities() -> dict:
    try:
        data = json.loads(_identities_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return _seed_from_env()
    except (ValueError, OSError):
        return {}


def _seed_from_env() -> dict:
    """First boot at a client: client.yaml people[].channels arrives as
    SP_GATEWAY_IDENTITIES_JSON (rendered by client_render). Materialise it once
    so the UI can edit it from there on."""
    raw = os.getenv("SP_GATEWAY_IDENTITIES_JSON", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    clean = {}
    for platform, rows in data.items():
        if platform not in _BY_KEY or not isinstance(rows, dict):
            continue
        for uid, entry in rows.items():
            email = str((entry or {}).get("email") if isinstance(entry, dict) else entry or "").strip().lower()
            nuid = normalize_user_id(platform, uid)
            if nuid and email and "@" in email:
                clean.setdefault(platform, {})[nuid] = {
                    "email": email, "name": str((entry or {}).get("name") or "") if isinstance(entry, dict) else "",
                    "profile": _profile_for_email(email, (entry or {}).get("profile") if isinstance(entry, dict) else None),
                    "added_by": "client.yaml", "added_at": int(time.time())}
    if clean:
        try:
            with _LOCK:
                _save_identities(clean)
        except OSError:
            logger.debug("channels: could not materialise the identity seed", exc_info=True)
    return clean


def _profile_for_email(email: str, explicit=None) -> str:
    """The engine profile a mapped person runs under: an explicit value, else
    the single profile the governance policy grants them (e.g. andre -> andre),
    else '' (the gateway's own profile)."""
    value = str(explicit or "").strip().lower()
    if value:
        return value if _PROFILE_RE.match(value) else ""
    try:
        from api.governance.loader import get_policy
        user = (getattr(get_policy(), "users", None) or {}).get(str(email or "").lower())
        grants = getattr(user, "grants", None) if user is not None else None
        profiles = sorted(p for p in (getattr(grants, "profiles", None) or ()) if p and p != "*" and p != "default")
        return profiles[0] if len(profiles) == 1 and _PROFILE_RE.match(profiles[0]) else ""
    except Exception:
        logger.debug("channels: profile lookup failed for %s", email, exc_info=True)
        return ""


def _save_identities(data: dict) -> None:
    path = _identities_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def normalize_user_id(platform: str, user_id) -> str:
    value = str(user_id or "").strip()
    if platform == "google_chat" or "@" in value:
        value = value.lower()
    if platform == "whatsapp_cloud":
        value = value.lstrip("+").replace(" ", "")
    return value if _USER_ID_RE.match(value) else ""


def mapped_email(platform: str, user_id) -> str:
    platform = str(platform or "").strip().lower()
    uid = normalize_user_id(platform, user_id)
    if not platform or not uid:
        return ""
    entry = (load_identities().get(platform) or {}).get(uid)
    return str((entry or {}).get("email") or "").strip().lower() if isinstance(entry, dict) else ""


def _known_people() -> set[str]:
    try:
        from api.governance.loader import get_policy
        policy = get_policy()
        people = {str(e).strip().lower() for e in (getattr(policy, "users", None) or {})}
        people |= {str(e).strip().lower() for e in (getattr(policy, "bootstrap_admins", None) or ())}
        return people
    except Exception:
        logger.debug("channels: policy unavailable", exc_info=True)
        return set()


def _pairing_store():
    from gateway.pairing import PairingStore  # engine module, on sys.path via api.config
    return PairingStore()


def _pairing_snapshot() -> dict:
    """Pending and approved rows per platform, or empty when the engine is missing."""
    out = {"pending": [], "approved": [], "available": True}
    try:
        store = _pairing_store()
        out["pending"] = [r for r in store.list_pending() if isinstance(r, dict)]
        out["approved"] = [r for r in store.list_approved() if isinstance(r, dict)]
    except Exception:
        logger.debug("channels: pairing store unavailable", exc_info=True)
        out["available"] = False
    return out


def _allowlist(env: dict, var: str) -> list[str]:
    raw = str(env.get(var) or "")
    return [x.strip() for x in raw.split(",") if x.strip()]


def status_payload() -> dict:
    env = _env_values()
    identities = load_identities()
    pairing = _pairing_snapshot()
    platforms = []
    for p in CATALOG:
        fields = [{"key": f["key"], "label": f["label"], "secret": f["secret"], "required": f["required"],
                   "hint": f["hint"], "set": bool(str(env.get(f["key"]) or "").strip())} for f in p["fields"]]
        configured = all(f["set"] for f in fields if f["required"])
        allowed = _allowlist(env, p["allow_env"])
        mapped = identities.get(p["key"]) or {}
        platforms.append({
            "key": p["key"], "label": p["label"], "summary": p["summary"],
            "user_id_hint": p["user_id_hint"], "fields": fields, "configured": configured,
            "allow_all": str(env.get(p["allow_all_env"]) or "").strip().lower() in {"1", "true", "yes"},
            "allowed_count": len(allowed),
            "mapped_count": len(mapped),
            "pending_count": sum(1 for r in pairing["pending"] if r.get("platform") == p["engine"]),
            "approved_count": sum(1 for r in pairing["approved"] if r.get("platform") == p["engine"]),
        })
    people = []
    for platform, rows in identities.items():
        if not isinstance(rows, dict):
            continue
        for uid, entry in rows.items():
            if isinstance(entry, dict):
                people.append({"platform": platform, "user_id": uid, "email": entry.get("email", ""),
                               "name": entry.get("name", ""), "profile": entry.get("profile", ""),
                               "added_at": entry.get("added_at")})
    people.sort(key=lambda r: (r["platform"], str(r.get("email") or ""), r["user_id"]))
    hooks = public_hooks_status(env)
    for p in platforms:
        if p["key"] in hooks:
            p["public"] = hooks[p["key"]]
    return {
        "platforms": platforms,
        "people": people,
        "pairing": {"available": pairing["available"], "pending": pairing["pending"], "approved": pairing["approved"]},
        "env_file": str(_env_path()),
        "restart_required_hint": "Changes to tokens take effect after a gateway restart.",
    }


def configure(platform: str, values: dict) -> dict:
    p = _BY_KEY.get(str(platform or "").strip().lower())
    if not p:
        raise ValueError("Unknown channel")
    if not isinstance(values, dict):
        raise ValueError("values must be an object")
    allowed_keys = _FIELD_KEYS[p["key"]] | {p["allow_all_env"]}
    updates = {}
    for key, value in values.items():
        if key not in allowed_keys:
            raise ValueError(f"Unknown field {key}")
        if value is None or value == "":
            continue  # blank = keep what is stored
        text = str(value).strip()
        if "\n" in text or len(text) > 4000:
            raise ValueError(f"Invalid value for {key}")
        if key == p["allow_all_env"]:
            text = "true" if text.lower() in {"1", "true", "yes", "on"} else "false"
        updates[key] = text
    if not updates:
        raise ValueError("Nothing to save")
    from api.providers import _write_env_file
    _write_env_file(_env_path(), updates)
    return {"ok": True, "platform": p["key"], "saved": sorted(updates)}


def disable(platform: str) -> dict:
    p = _BY_KEY.get(str(platform or "").strip().lower())
    if not p:
        raise ValueError("Unknown channel")
    from api.providers import _write_env_file
    _write_env_file(_env_path(), {f["key"]: None for f in p["fields"] if f["secret"] or f["required"]})
    return {"ok": True, "platform": p["key"]}


def set_identity(platform: str, user_id, email: str, name: str = "", *, actor: str = "", profile=None) -> dict:
    p = _BY_KEY.get(str(platform or "").strip().lower())
    if not p:
        raise ValueError("Unknown channel")
    uid = normalize_user_id(p["key"], user_id)
    if not uid:
        raise ValueError("Invalid platform user id")
    email = str(email or "").strip().lower()
    if not email or "@" not in email:
        raise ValueError("Pick a person")
    known = _known_people()
    if known and email not in known:
        raise ValueError("This address is not known to the governance policy")
    name = str(name or "").strip()[:120]
    if profile is not None and str(profile).strip() and not _PROFILE_RE.match(str(profile).strip().lower()):
        raise ValueError("Invalid profile name")
    resolved_profile = _profile_for_email(email, profile)
    with _LOCK:
        data = load_identities()
        rows = data.setdefault(p["key"], {})
        rows[uid] = {"email": email, "name": name, "profile": resolved_profile,
                     "added_by": str(actor or "").lower(), "added_at": int(time.time())}
        _save_identities(data)
    return {"ok": True, "platform": p["key"], "user_id": uid, "email": email, "name": name, "profile": resolved_profile}


def remove_identity(platform: str, user_id) -> dict:
    p = _BY_KEY.get(str(platform or "").strip().lower())
    if not p:
        raise ValueError("Unknown channel")
    uid = normalize_user_id(p["key"], user_id)
    with _LOCK:
        data = load_identities()
        rows = data.get(p["key"]) or {}
        removed = rows.pop(uid, None) is not None
        if rows:
            data[p["key"]] = rows
        else:
            data.pop(p["key"], None)
        _save_identities(data)
    return {"ok": True, "removed": removed}


def approve_pairing(platform: str, request_id: str, email: str = "", *, actor: str = "") -> dict:
    p = _BY_KEY.get(str(platform or "").strip().lower())
    if not p:
        raise ValueError("Unknown channel")
    store = _pairing_store()
    granted = store.approve_request(p["engine"], str(request_id or ""))
    if not granted:
        raise LookupError("This pairing request expired or was already handled")
    result = {"ok": True, "platform": p["key"], "user_id": granted.get("user_id"), "user_name": granted.get("user_name", "")}
    if email:
        result["identity"] = set_identity(p["key"], granted.get("user_id"), email, granted.get("user_name", ""), actor=actor)
    return result


def revoke_pairing(platform: str, user_id) -> dict:
    p = _BY_KEY.get(str(platform or "").strip().lower())
    if not p:
        raise ValueError("Unknown channel")
    store = _pairing_store()
    revoked = bool(store.revoke(p["engine"], str(user_id or "")))
    remove_identity(p["key"], user_id)
    return {"ok": True, "revoked": revoked}


# ── Public webhook URLs through Tailscale Funnel ────────────────────────────

def _tailscale(*args, timeout=25):
    import shutil
    import subprocess
    exe = shutil.which("tailscale")
    if not exe:
        raise FileNotFoundError("tailscale CLI not available")
    return subprocess.run([exe, *args], capture_output=True, text=True, timeout=timeout)


def _tailnet_fqdn() -> str:
    try:
        proc = _tailscale("status", "--json", timeout=15)
        data = json.loads(proc.stdout or "{}")
        return str((data.get("Self") or {}).get("DNSName") or "").rstrip(".")
    except Exception:
        return ""


def public_hooks_status(env: dict | None = None) -> dict:
    """Per webhook platform: {state, url, mount}. state is published (Funnel
    serves the mount), unpublished (CLI present, not served), or unavailable
    (no CLI: a client container; the VM bootstrap owns Funnel there and hands
    the base URL in as SP_TS_HOOKS_BASE)."""
    env = env if env is not None else _env_values()
    out = {}
    base_hint = str(os.getenv("SP_TS_HOOKS_BASE") or env.get("SP_TS_HOOKS_BASE") or "").rstrip("/")
    served = None
    try:
        proc = _tailscale("serve", "status", "--json", timeout=15)
        data = json.loads(proc.stdout or "{}")
        served = {}
        fqdn = _tailnet_fqdn()
        for hostport, cfg in (data.get("Web") or {}).items():
            if not hostport.endswith(":" + str(FUNNEL_PORT)):
                continue
            funnel_on = bool((data.get("AllowFunnel") or {}).get(hostport))
            for mount, handler in (cfg.get("Handlers") or {}).items():
                served[mount] = {"proxy": handler.get("Proxy"), "funnel": funnel_on, "fqdn": fqdn}
    except FileNotFoundError:
        served = None
    except Exception:
        logger.debug("channels: tailscale serve status failed", exc_info=True)
        served = {}
    for key, spec in PUBLIC_HOOKS.items():
        if served is None:
            url = base_hint + spec["mount"].replace("/hooks", "", 1) if base_hint else ""
            out[key] = {"state": "published" if url else "unavailable", "url": url, "mount": spec["mount"],
                        "label": spec["label"], "managed_by": "bootstrap"}
            continue
        row = served.get(spec["mount"])
        if row and row.get("funnel") and row.get("fqdn"):
            out[key] = {"state": "published", "url": f"https://{row['fqdn']}:{FUNNEL_PORT}{spec['mount']}",
                        "mount": spec["mount"], "label": spec["label"], "managed_by": "webui"}
        else:
            out[key] = {"state": "unpublished", "url": "", "mount": spec["mount"], "label": spec["label"], "managed_by": "webui"}
    return out


def publish_hook(platform: str) -> dict:
    """Expose the platform's webhook on the tailnet node through Funnel and pin
    the gateway listener to loopback. Idempotent; requires the Funnel node
    attribute in the tailnet ACL (docs/TAILSCALE.md)."""
    spec = PUBLIC_HOOKS.get(str(platform or "").strip().lower())
    if not spec:
        raise ValueError("This channel has no public webhook")
    fqdn = _tailnet_fqdn()
    if not fqdn:
        raise RuntimeError("Tailscale is not available on this host; the deploy bootstrap publishes webhooks at a client")
    backend = f"http://127.0.0.1:{spec['port']}{spec['path']}"
    proc = _tailscale("funnel", "--bg", f"--https={FUNNEL_PORT}", "--set-path", spec["mount"], backend, timeout=40)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RuntimeError("tailscale funnel failed: " + (detail[-1] if detail else "unknown error"))
    from api.providers import _write_env_file
    _write_env_file(_env_path(), {spec["host_env"]: "127.0.0.1"})
    url = f"https://{fqdn}:{FUNNEL_PORT}{spec['mount']}"
    return {"ok": True, "platform": platform, "url": url, "mount": spec["mount"], "backend": backend}


def unpublish_hook(platform: str) -> dict:
    spec = PUBLIC_HOOKS.get(str(platform or "").strip().lower())
    if not spec:
        raise ValueError("This channel has no public webhook")
    proc = _tailscale("funnel", f"--https={FUNNEL_PORT}", "--set-path", spec["mount"], "off", timeout=40)
    return {"ok": proc.returncode == 0, "platform": platform}


def _audit(handler, action: str, extra: dict) -> None:
    try:
        from api.governance.audit import append_audit_event
        from api.ownership import request_owner_email
        append_audit_event("gateway_channels_" + action, subject_email=str(request_owner_email(handler) or ""),
                           path="/api/gateway/" + action, method="POST", reason=action, extra=extra)
    except Exception:
        logger.debug("channels: audit failed", exc_info=True)


def _actor(handler) -> str:
    try:
        from api.ownership import request_owner_email
        return str(request_owner_email(handler) or "").lower()
    except Exception:
        return ""


def handle_get(handler, path: str):
    if path == "/api/gateway/channels":
        return j(handler, status_payload(), extra_headers={"Cache-Control": "no-store"})
    return bad(handler, "Not found", 404)


def handle_post(handler, path: str, body):
    body = body if isinstance(body, dict) else {}
    try:
        if path == "/api/gateway/channels/configure":
            out = configure(body.get("platform"), body.get("values") or {})
            if out["platform"] in PUBLIC_HOOKS:
                # Webhook platforms need a public URL before the provider can
                # be configured; publish it in the same step when we can.
                try:
                    out["public"] = publish_hook(out["platform"])
                except Exception as exc:
                    out["public"] = {"ok": False, "error": str(exc)}
            _audit(handler, "configure", {"platform": out["platform"], "keys": out["saved"]})
            return j(handler, out)
        if path == "/api/gateway/channels/disable":
            out = disable(body.get("platform"))
            if out["platform"] in PUBLIC_HOOKS:
                try:
                    unpublish_hook(out["platform"])
                except Exception:
                    logger.debug("channels: unpublish after disable failed", exc_info=True)
            _audit(handler, "disable", {"platform": out["platform"]})
            return j(handler, out)
        if path == "/api/gateway/channels/publish":
            try:
                out = publish_hook(body.get("platform"))
            except RuntimeError as exc:
                return bad(handler, str(exc), 409)
            _audit(handler, "publish", {"platform": out["platform"], "url": out["url"]})
            return j(handler, out)
        if path == "/api/gateway/identities/set":
            out = set_identity(body.get("platform"), body.get("user_id"), body.get("email"), body.get("name", ""),
                               actor=_actor(handler), profile=body.get("profile"))
            _audit(handler, "identity_set", {k: out[k] for k in ("platform", "user_id", "email")})
            return j(handler, out)
        if path == "/api/gateway/identities/remove":
            out = remove_identity(body.get("platform"), body.get("user_id"))
            _audit(handler, "identity_remove", {"platform": body.get("platform"), "user_id": str(body.get("user_id") or "")})
            return j(handler, out)
        if path == "/api/gateway/pairing/approve":
            out = approve_pairing(body.get("platform"), body.get("request_id"), body.get("email", ""), actor=_actor(handler))
            _audit(handler, "pairing_approve", {"platform": out["platform"], "user_id": str(out.get("user_id") or ""), "email": body.get("email", "")})
            return j(handler, out)
        if path == "/api/gateway/pairing/revoke":
            out = revoke_pairing(body.get("platform"), body.get("user_id"))
            _audit(handler, "pairing_revoke", {"platform": body.get("platform"), "user_id": str(body.get("user_id") or "")})
            return j(handler, out)
    except LookupError as exc:
        return bad(handler, str(exc), 404)
    except ValueError as exc:
        return bad(handler, str(exc), 400)
    except Exception:
        logger.warning("channels: %s failed", path, exc_info=True)
        return bad(handler, "Channel action failed. Check the server log.", 500)
    return bad(handler, "Not found", 404)


# ── Self-service: my own bot and my platform ids ─────────────────────────────
# One bot per person: a person's engine profile owns its own Telegram bot
# (token in that profile's .env), served by the multiplex gateway under that
# profile. The person links their own platform id here; that adds them to
# their bot's allowlist and to the identity map (governance + profile).

SELF_SERVICE_PLATFORMS = ("telegram",)
_PEOPLE_GATEWAY_UNIT_ENV = "HERMES_WEBUI_PEOPLE_GATEWAY_UNIT"
_APPLY_MIN_INTERVAL = 600


def _me(handler) -> str:
    from api.ownership import request_owner_email
    return str(request_owner_email(handler) or "").strip().lower()


def _is_admin(handler) -> bool:
    try:
        from api.ownership import identity_is_admin
        from api.governance.enforce import _request_identity
        return bool(identity_is_admin(_request_identity(handler)))
    except Exception:
        return False


def my_profile(email: str) -> str:
    return _profile_for_email(email)


def _profile_env_path(profile: str) -> Path:
    from api.profiles import get_hermes_home_for_profile
    return Path(get_hermes_home_for_profile(profile or "default")) / ".env"


def _merge_allowlist(env_path: Path, var: str, user_id: str, *, remove: bool = False) -> None:
    from api.providers import _load_env_file, _write_env_file
    current = _allowlist(_load_env_file(env_path), var)
    if remove:
        current = [x for x in current if x != user_id]
    elif user_id not in current:
        current.append(user_id)
    _write_env_file(env_path, {var: ",".join(current) if current else None})


def _people_gateway_unit() -> str:
    return str(os.getenv(_PEOPLE_GATEWAY_UNIT_ENV) or "hermes-mux-gateway.service")


def _people_gateway_state() -> dict:
    import shutil
    import subprocess
    unit = _people_gateway_unit()
    exe = shutil.which("systemctl")
    if not exe:
        return {"unit": unit, "active": None, "available": False}
    try:
        proc = subprocess.run([exe, "--user", "is-active", unit], capture_output=True, text=True, timeout=10)
        return {"unit": unit, "active": proc.stdout.strip() == "active", "available": True}
    except Exception:
        return {"unit": unit, "active": None, "available": False}


def _apply_stamp_path() -> Path:
    from api import config
    return Path(config.STATE_DIR) / "gateway-people-apply.json"


def my_channels_payload(handler) -> dict:
    me = _me(handler)
    if not me:
        raise PermissionError("Sign in first")
    profile = my_profile(me)
    env = {}
    env_path = _profile_env_path(profile) if profile else None
    if env_path is not None:
        from api.providers import _load_env_file
        env = _load_env_file(env_path)
    own = {}
    for key in SELF_SERVICE_PLATFORMS:
        p = _BY_KEY[key]
        own[key] = {
            "label": p["label"],
            "token_set": bool(profile) and bool(str(env.get(p["fields"][0]["key"]) or "").strip()),
            "allowed_ids": _allowlist(env, p["allow_env"]) if profile else [],
            "user_id_hint": p["user_id_hint"],
        }
    links = [{"platform": platform, "user_id": uid, "name": entry.get("name", ""), "profile": entry.get("profile", "")}
             for platform, rows in load_identities().items() if isinstance(rows, dict)
             for uid, entry in rows.items()
             if isinstance(entry, dict) and str(entry.get("email") or "").lower() == me]
    links.sort(key=lambda r: (r["platform"], r["user_id"]))
    stamp = {}
    try:
        stamp = json.loads(_apply_stamp_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        stamp = {}
    return {
        "email": me, "profile": profile, "own_bot": own, "links": links,
        "shared_bot": not profile,
        "people_gateway": {**_people_gateway_state(), "last_apply_at": stamp.get("at"), "last_apply_by": stamp.get("by")},
        "platforms": [{"key": p["key"], "label": p["label"], "user_id_hint": p["user_id_hint"]} for p in CATALOG],
        "is_admin": _is_admin(handler),
    }


def set_my_bot(handler, platform: str, values: dict) -> dict:
    me = _me(handler)
    if not me:
        raise PermissionError("Sign in first")
    key = str(platform or "").strip().lower()
    if key not in SELF_SERVICE_PLATFORMS:
        raise ValueError("This platform is shared by the organisation; ask an admin under Messaging channels")
    profile = my_profile(me)
    if not profile:
        raise ValueError("Your account runs on the workstation's main bot; a personal bot needs your own engine profile")
    p = _BY_KEY[key]
    token_key = p["fields"][0]["key"]
    updates = {}
    for k, v in (values or {}).items():
        if k not in {f["key"] for f in p["fields"]}:
            raise ValueError(f"Unknown field {k}")
        text = str(v or "").strip()
        if text:
            if "\n" in text or len(text) > 4000:
                raise ValueError(f"Invalid value for {k}")
            updates[k] = text
    if not updates:
        raise ValueError("Nothing to save")
    from api.providers import _write_env_file
    env_path = _profile_env_path(profile)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    _write_env_file(env_path, updates)
    return {"ok": True, "platform": key, "profile": profile, "saved": sorted(updates), "token_set": token_key in updates}


def remove_my_bot(handler, platform: str) -> dict:
    me = _me(handler)
    key = str(platform or "").strip().lower()
    profile = my_profile(me) if me else ""
    if key not in SELF_SERVICE_PLATFORMS or not profile:
        raise ValueError("No personal bot to remove")
    p = _BY_KEY[key]
    from api.providers import _write_env_file
    _write_env_file(_profile_env_path(profile), {f["key"]: None for f in p["fields"]})
    return {"ok": True, "platform": key, "profile": profile}


def link_me(handler, platform: str, user_id, name: str = "") -> dict:
    me = _me(handler)
    if not me:
        raise PermissionError("Sign in first")
    p = _BY_KEY.get(str(platform or "").strip().lower())
    if not p:
        raise ValueError("Unknown channel")
    uid = normalize_user_id(p["key"], user_id)
    if not uid:
        raise ValueError("Invalid platform user id")
    existing = (load_identities().get(p["key"]) or {}).get(uid)
    if isinstance(existing, dict) and str(existing.get("email") or "").lower() not in ("", me):
        raise ValueError("This platform id is already linked to another person; ask an admin")
    profile = my_profile(me)
    out = set_identity(p["key"], uid, me, name or me.split("@")[0], actor=me, profile=profile or None)
    if profile and p["key"] in SELF_SERVICE_PLATFORMS:
        _merge_allowlist(_profile_env_path(profile), p["allow_env"], uid)
    return out


def unlink_me(handler, platform: str, user_id) -> dict:
    me = _me(handler)
    p = _BY_KEY.get(str(platform or "").strip().lower())
    if not me or not p:
        raise ValueError("Unknown channel")
    uid = normalize_user_id(p["key"], user_id)
    existing = (load_identities().get(p["key"]) or {}).get(uid)
    if not isinstance(existing, dict) or str(existing.get("email") or "").lower() != me:
        raise LookupError("Not your link")
    out = remove_identity(p["key"], uid)
    profile = my_profile(me)
    if profile and p["key"] in SELF_SERVICE_PLATFORMS:
        _merge_allowlist(_profile_env_path(profile), p["allow_env"], uid, remove=True)
    return out


def apply_people_gateway(handler) -> dict:
    """Restart the multiplex gateway so new bots and allowlists take effect.
    Admins always; others at most once per 10 minutes (shared service)."""
    import subprocess
    me = _me(handler)
    if not me:
        raise PermissionError("Sign in first")
    admin = _is_admin(handler)
    stamp_path = _apply_stamp_path()
    now = int(time.time())
    if not admin:
        try:
            last = int((json.loads(stamp_path.read_text(encoding="utf-8")) or {}).get("at") or 0)
        except (OSError, ValueError):
            last = 0
        if now - last < _APPLY_MIN_INTERVAL:
            raise RuntimeError(f"The bots were restarted {now - last} seconds ago; try again in {(_APPLY_MIN_INTERVAL - (now - last)) // 60 + 1} minutes")
    unit = _people_gateway_unit()
    state = _people_gateway_state()
    if not state.get("available"):
        raise RuntimeError("Cannot restart the bots from here (no systemctl); ask an operator")
    proc = subprocess.run(["systemctl", "--user", "restart", unit], capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError("restart failed: " + (proc.stderr or proc.stdout).strip()[-200:])
    stamp_path.parent.mkdir(parents=True, exist_ok=True)
    stamp_path.write_text(json.dumps({"at": now, "by": me}), encoding="utf-8")
    return {"ok": True, "unit": unit, "at": now}


def handle_me(handler, method: str, path: str, body):
    body = body if isinstance(body, dict) else {}
    try:
        if method == "GET" and path == "/api/me/channels":
            return j(handler, my_channels_payload(handler), extra_headers={"Cache-Control": "no-store"})
        if method == "POST" and path == "/api/me/channels/bot":
            if body.get("remove"):
                out = remove_my_bot(handler, body.get("platform"))
            else:
                out = set_my_bot(handler, body.get("platform"), body.get("values") or {})
            _audit(handler, "my_bot", {"platform": out["platform"], "profile": out["profile"], "removed": bool(body.get("remove"))})
            return j(handler, out)
        if method == "POST" and path == "/api/me/channels/link":
            out = link_me(handler, body.get("platform"), body.get("user_id"), body.get("name", ""))
            _audit(handler, "my_link", {"platform": out["platform"], "user_id": out["user_id"]})
            return j(handler, out)
        if method == "POST" and path == "/api/me/channels/unlink":
            out = unlink_me(handler, body.get("platform"), body.get("user_id"))
            _audit(handler, "my_unlink", {"platform": body.get("platform"), "user_id": str(body.get("user_id") or "")})
            return j(handler, out)
        if method == "POST" and path == "/api/me/channels/apply":
            out = apply_people_gateway(handler)
            _audit(handler, "people_gateway_apply", {"unit": out["unit"]})
            return j(handler, out)
    except PermissionError as exc:
        return bad(handler, str(exc), 401)
    except LookupError as exc:
        return bad(handler, str(exc), 404)
    except RuntimeError as exc:
        return bad(handler, str(exc), 409)
    except ValueError as exc:
        return bad(handler, str(exc), 400)
    except Exception:
        logger.warning("channels: %s failed", path, exc_info=True)
        return bad(handler, "Channel action failed. Check the server log.", 500)
    return bad(handler, "Not found", 404)
