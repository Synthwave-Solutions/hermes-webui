"""Personal password vault settings. HTTP responses contain metadata only."""
from __future__ import annotations

from contextlib import contextmanager
import re
import subprocess
import threading

from api import personal_context

_SOURCE_LOCKS = tuple(threading.Lock() for _ in range(64))
_MANAGERS = {"onepassword", "bitwarden"}


@contextmanager
def vault_scope(identity):
    from agent.vault_scope import bind_personal_vault, reset_personal_vault
    token = bind_personal_vault(personal_context.ensure_home(identity))
    try:
        yield
    finally:
        reset_personal_vault(token)


def status():
    from agent.vault_backends.base import is_installed
    from agent.vault_backends.unlock import is_unlocked
    from agent.vault_store import get_vault_store
    cfg = get_vault_store().read_source_settings()
    sources = [{"name": "local", "display_name": "SynthPulse", "enabled": True,
                "installed": True, "configured": True, "unlocked": True}]
    for name, label in (("bitwarden", "Bitwarden"), ("onepassword", "1Password")):
        section = cfg.get(name) or {}
        installed = is_installed(name)
        enabled = installed and section.get("enabled") is not False
        configured = bool(section.get("connected"))
        sources.append({"name": name, "display_name": label, "installed": installed,
                        "enabled": enabled, "configured": configured,
                        "unlocked": enabled and (configured if name == "onepassword" else is_unlocked(name)),
                        "server": section.get("server", "https://vault.bitwarden.eu") if name == "bitwarden" else None})
    # Listing remote managers can take seconds. The initial settings load is
    # local-only; remote metadata is requested separately, on demand.
    return {"sources": sources, "items": [m.to_dict() for m in get_vault_store().list_items()]}


def _manager(name):
    from agent.vault_backends.base import enabled_backends
    backend = next((b for b in enabled_backends() if b.name == name), None)
    if backend is None:
        raise ValueError("This password manager is unavailable or disabled.")
    return backend


def _cli(args, env):
    result = subprocess.run(args, env=env, capture_output=True, text=True,
                            stdin=subprocess.DEVNULL, timeout=45, check=False)
    if result.returncode:
        # CLI stderr can contain tokens, passwords or account details.
        raise ValueError("Connection failed. Check your account details and try again.")


def _configure(name, body):
    from agent.vault_backends.base import is_installed
    from agent.vault_scope import vault_home
    if name not in _MANAGERS or not is_installed(name):
        raise ValueError("The password manager is not installed on this server.")
    with _SOURCE_LOCKS[hash((str(vault_home()), name)) % len(_SOURCE_LOCKS)]:
        return _configure_locked(name, body)


def _configure_locked(name, body):
    from agent.vault_backends.unlock import lock
    from agent.vault_store import get_vault_store
    store = get_vault_store()
    section = store.read_source_settings().get(name) or {}
    if "enabled" in body:
        if not isinstance(body["enabled"], bool):
            raise ValueError("Invalid setting.")
        section["enabled"] = body["enabled"]
        store.update_source_settings(name, section)
        if not body["enabled"]:
            lock(name)
        return {"ok": True}
    if name == "onepassword":
        from agent.vault_backends.onepassword import OnePasswordLoginBackend
        token = body.get("service_account_token")
        if not isinstance(token, str) or not 10 <= len(token) <= 8192 or any(c.isspace() for c in token):
            raise ValueError("Enter a valid service account token.")
        candidate = {"enabled": True, "connected": True, "service_account_token": token}
        backend = OnePasswordLoginBackend(candidate)
        _cli([str(backend._op()), "whoami", "--format", "json"], backend._env(None))
        store.update_source_settings(name, candidate)
    else:
        from agent.vault_backends.bitwarden import BitwardenLoginBackend
        client_id, secret = body.get("client_id"), body.get("client_secret")
        server = body.get("server", "https://vault.bitwarden.eu")
        if not isinstance(client_id, str) or not re.fullmatch(r"user\.[a-zA-Z0-9-]{8,100}", client_id):
            raise ValueError("Enter your personal Bitwarden client ID.")
        if not isinstance(secret, str) or not 8 <= len(secret) <= 4096:
            raise ValueError("Enter your personal Bitwarden API secret.")
        if server not in {"https://vault.bitwarden.eu", "https://vault.bitwarden.com"}:
            raise ValueError("Select a supported Bitwarden region.")
        if section.get("connected"):
            raise ValueError("Disconnect this account before connecting another.")
        backend = BitwardenLoginBackend()
        env = backend._env(None)
        _cli([str(backend._bw()), "config", "server", server], env)
        env.update(BW_CLIENTID=client_id, BW_CLIENTSECRET=secret)
        _cli([str(backend._bw()), "login", "--apikey", "--nointeraction"], env)
        store.update_source_settings(name, {"enabled": True, "connected": True, "server": server})
    return {"ok": True}


def _disconnect(name):
    from agent.vault_backends.unlock import lock
    from agent.vault_scope import vault_home
    from agent.vault_store import get_vault_store
    if name not in _MANAGERS:
        raise ValueError("Unknown password manager.")
    with _SOURCE_LOCKS[hash((str(vault_home()), name)) % len(_SOURCE_LOCKS)]:
        get_vault_store().update_source_settings(name, {"enabled": False, "connected": False})
        lock(name)
        if name == "bitwarden":
            from agent.vault_backends.bitwarden import BitwardenLoginBackend
            backend = BitwardenLoginBackend()
            try:
                _cli([str(backend._bw()), "logout", "--nointeraction"], backend._env(None))
            except (ValueError, RuntimeError, OSError, subprocess.SubprocessError):
                return {"ok": True, "remote_logout": False,
                        "message": "Local access is disabled. Bitwarden logout failed; retry Disconnect before connecting another account."}
            return {"ok": True, "remote_logout": True}
    return {"ok": True}


def _action(action, body):
    from agent.vault_backends.unlock import lock
    from agent.vault_store import get_vault_store
    if action == "status":
        return status()
    if action == "items":
        backend = _manager(body.get("name"))
        return {"items": [m.to_dict() for m in backend.list_items()]}
    if action == "configure":
        return _configure(body.get("name"), body)
    if action == "disconnect":
        return _disconnect(body.get("name"))
    if action == "unlock":
        from agent.vault_scope import vault_home
        password = body.get("password")
        if body.get("name") != "bitwarden" or not isinstance(password, str) or not 1 <= len(password) <= 4096:
            raise ValueError("Enter your Bitwarden master password.")
        try:
            with _SOURCE_LOCKS[hash((str(vault_home()), "bitwarden")) % len(_SOURCE_LOCKS)]:
                _manager("bitwarden").unlock(password)
        except Exception:
            raise ValueError("Unlock failed. Check your password and try again.") from None
        return {"ok": True}
    if action == "lock":
        if body.get("name") not in _MANAGERS:
            raise ValueError("Unknown password manager.")
        if body["name"] == "onepassword":
            raise ValueError("Disable or disconnect 1Password to revoke its service account access.")
        lock(body["name"])
        return {"ok": True}
    if action == "add":
        secret = body.get("secret")
        if not isinstance(secret, dict) or not isinstance(secret.get("password"), str):
            raise ValueError("Enter the login details.")
        meta = get_vault_store().add_item("login", str(body.get("label") or ""),
                                         secret=secret, origin=str(body.get("origin") or ""))
        return {"id": meta.id}
    if action == "remove":
        item_id = body.get("id")
        if not isinstance(item_id, str) or not re.fullmatch(r"vault_[a-f0-9]{12}", item_id):
            raise ValueError("Invalid login.")
        return {"removed": get_vault_store().remove_item(item_id)}
    raise ValueError("Unknown vault action.")


def handle(handler, action, body=None):
    from api.ownership import _request_identity
    from api.routes import j
    try:
        with vault_scope(_request_identity(handler)):
            result = _action(action, body or {})
        return j(handler, result)
    except PermissionError:
        return j(handler, {"error": "Sign in to access your personal vault."}, status=403)
    except Exception:
        # No arbitrary exception text: validation errors and manager failures
        # may contain user-supplied passwords, TOTP seeds or service tokens.
        return j(handler, {"error": "Vault request failed. Check the details and try again."}, status=400)
