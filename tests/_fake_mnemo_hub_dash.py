"""A fake memory hub for the Memory explorer's hub backend (A13, addendum 6.6.7).

It serves the A13h contract on an ephemeral 127.0.0.1 port and records every
request:

* ``GET /v1/banks``: the registry entries the assertion's claims may see;
* ``GET /v1/banks/{ref}/dash/{view}``: canned view data per bank (``ref`` may
  be ``me``);
* ``POST /v1/banks/{ref}/memories/{id}/update|forget|meta``: recorded changes.

Every call needs ``Authorization: Bearer <token>`` and an ``X-Mnemo-Actor``
assertion in A6's format (``v1.<kid>.<b64 claims>.<b64 mac>``, HMAC-SHA256
over ``v1.<kid>.<b64 claims>``) signed with the fake's throwaway key; a bad
token or assertion answers 401, a context other than ``ui`` 403. ``fail``
forces a status for a path prefix (404, 401, 403, 409, 500, ...).

``FakeMinter`` stands in for A6's ``api.mnemo_actor`` with exactly its pinned
public signature (``hub_headers(identity, *, ctx, mem_admin=None,
guest=False)``) until A6 merges. Nothing here listens anywhere but
127.0.0.1, and port 20142 is never used.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

DASH_VIEWS = {
    "stats", "digest/today", "review", "lifecycle", "profile/inferred", "patterns", "constellation", "search",
    "recall-debug", "timeline", "memories", "memory", "session", "triples", "graph", "consolidations",
    "memoria/stats", "memoria/facts", "memoria/timelines", "memoria/instructions", "memoria/kg",
    "memoria/preferences",
}
FORBIDDEN_PORT = 20142


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def email_hash(email: str) -> str:
    raw = str(email or "").strip().lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24] if raw else ""


def encode_assertion(claims: dict, key: bytes, kid: str = "k1") -> str:
    body = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii"))
    mac = hmac.new(key, f"v1.{kid}.{body}".encode("ascii"), hashlib.sha256).digest()
    return f"v1.{kid}.{body}.{_b64(mac)}"


def decode_assertion(value: str, key: bytes) -> dict | None:
    parts = str(value or "").split(".")
    if len(parts) != 4 or parts[0] != "v1":
        return None
    expected = hmac.new(key, f"v1.{parts[1]}.{parts[2]}".encode("ascii"), hashlib.sha256).digest()
    try:
        if not hmac.compare_digest(_unb64(parts[3]), expected):
            return None
        claims = json.loads(_unb64(parts[2]))
    except (ValueError, TypeError):
        return None
    return claims if isinstance(claims, dict) else None


class FakeMinter:
    """A6's minter shape (pinned signature), signing with the fake's key."""

    def __init__(self, key: bytes, token: str, kid: str = "k1"):
        self.key = key
        self.token = token
        self.kid = kid
        self.calls: list[dict] = []

    def mint_assertion(self, identity, *, ctx, mem_admin=None, guest=False) -> str:
        if ctx not in ("chat_private", "chat_shared", "ui"):
            raise ValueError("ctx")
        if mem_admin is not None and mem_admin not in ("org", "platform"):
            raise ValueError("mem_admin")
        if (mem_admin is not None or guest) and ctx != "ui":
            raise ValueError("mem_admin and guest only with ctx ui")
        email = str((identity or {}).get("email") or "").strip().lower()
        if "@" not in email:
            raise ValueError("no email")
        claims = {"iss": "hermes-webui", "aud": "mnemo-hub", "sub": email, "ctx": ctx, "iat": 0, "exp": 60,
                  "jti": os.urandom(8).hex()}
        if mem_admin is not None:
            claims["mem_admin"] = mem_admin
        if guest:
            claims["guest"] = True
        self.calls.append({"email": email, "ctx": ctx, "mem_admin": mem_admin, "guest": guest})
        return encode_assertion(claims, self.key, self.kid)

    def hub_headers(self, identity, *, ctx, mem_admin=None, guest=False) -> dict:
        return {"Authorization": "Bearer " + self.token,
                "X-Mnemo-Actor": self.mint_assertion(identity, ctx=ctx, mem_admin=mem_admin, guest=guest)}

    def module(self) -> types.ModuleType:
        """A stand-in ``api.mnemo_actor`` module exposing the two public names."""
        module = types.ModuleType("api.mnemo_actor")
        module.mint_assertion = self.mint_assertion
        module.hub_headers = self.hub_headers
        return module


class FakeHub:
    """The fake hub. ``add_bank`` registers a bank; ``start`` returns its base URL."""

    def __init__(self, *, key: bytes | None = None, token: str = "fake-webui-token-0123456789", org_id: str = ""):
        self.key = key or os.urandom(32)
        self.token = token
        self.org_id = org_id
        self.banks: dict[str, dict] = {}
        self.requests: list[dict] = []
        self.fail: dict[str, int] = {}
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ── Data ──────────────────────────────────────────────────────────────

    def add_bank(self, ref: str, *, kind: str, owner_email: str = "", owner_display: str = "", label: str = "",
                 org: str = "", external: bool = False, owner_private: bool = False, mixed: bool = False,
                 counts: dict | None = None, memories: list[dict] | None = None, stale: bool = False,
                 extra: dict | None = None) -> dict:
        counts = counts or {"working_memory": 3, "episodic_memory": 1, "triples": 1}
        memories = memories or []
        bank = {
            "ref": ref, "kind": kind, "owner_email": owner_email.lower(), "owner_display": owner_display,
            "label": label or owner_display or ref, "org": org, "external": external,
            "owner_private": owner_private, "mixed": mixed, "counts": counts, "memories": memories,
            "stale": stale, "extra": extra or {}, "changes": [],
        }
        self.banks[ref] = bank
        return bank

    def visible(self, bank: dict, claims: dict) -> bool:
        sub = str(claims.get("sub") or "")
        if bank["owner_email"] and bank["owner_email"] == sub:
            return True
        if bank["owner_private"]:
            return False
        admin = claims.get("mem_admin")
        if admin == "platform":
            return not self.org_id or claims.get("guest") is True
        if admin == "org":
            if not self.org_id or claims.get("org") != self.org_id or bank["org"] != self.org_id:
                return False
            if bank["kind"] == "personal":
                return not bank["external"]
            return bank["kind"] in ("org", "dept", "assistant")
        return False

    def entry(self, bank: dict, claims: dict) -> dict:
        own = bool(bank["owner_email"]) and bank["owner_email"] == claims.get("sub")
        out = {
            "ref": bank["ref"], "kind": bank["kind"], "label": bank["label"],
            "owner_hash": email_hash(bank["owner_email"]), "owner_display": bank["owner_display"],
            "org": bank["org"], "external": bank["external"], "mixed": bank["mixed"],
            "owner_private": bank["owner_private"], "last_write": "2026-09-27T10:00:00Z", "primary": own,
            "db_path": "/never/shown/" + bank["ref"] + ".db",
        }
        return out

    def view_data(self, bank: dict, view: str, query: dict) -> tuple[int, dict]:
        if view == "stats":
            return 200, {"counts": dict(bank["counts"]), "db_path": "/secret/path.db", "pid": 4242,
                         "blob_hint": "stats", **bank["extra"]}
        if view == "memories":
            return 200, {"items": list(bank["memories"]), "path": "/secret"}
        if view == "memory":
            wanted = (query.get("id") or [""])[-1]
            for item in bank["memories"]:
                if item.get("id") == wanted:
                    return 200, {"item": item}
            return 404, {"error": "not found"}
        if view == "search":
            return 200, {"items": [m for m in bank["memories"] if (query.get("q") or [""])[-1] in m.get("content", "")]}
        return 200, {"view": view, "items": []}

    # ── Server ────────────────────────────────────────────────────────────

    def start(self) -> str:
        hub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # quiet
                pass

            def _answer(self, status: int, payload) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _handle(self, method: str) -> None:
                parts = urlsplit(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw.decode("utf-8")) if raw else None
                except ValueError:
                    body = "<garbage>"
                auth = self.headers.get("Authorization") or ""
                claims = decode_assertion(self.headers.get("X-Mnemo-Actor") or "", hub.key)
                record = {"method": method, "path": parts.path, "query": parse_qs(parts.query),
                          "authorization": auth, "claims": claims, "body": body,
                          "headers": {k.lower(): v for k, v in self.headers.items()}}
                with hub._lock:
                    hub.requests.append(record)
                for prefix, status in hub.fail.items():
                    if parts.path.startswith(prefix):
                        self._answer(status, {"error": "forced"})
                        return
                if auth != "Bearer " + hub.token or claims is None:
                    self._answer(401, {"error": "unauthorized"})
                    return
                if claims.get("ctx") != "ui":
                    self._answer(403, {"error": "context"})
                    return
                segments = [unquote(s) for s in parts.path.split("/")[1:]]
                if method == "GET" and segments == ["v1", "banks"]:
                    self._answer(200, {"banks": [hub.entry(b, claims) for b in hub.banks.values() if hub.visible(b, claims)]})
                    return
                if len(segments) < 4 or segments[:2] != ["v1", "banks"]:
                    self._answer(404, {"error": "not found"})
                    return
                ref = segments[2]
                if ref == "me":
                    bank = next((b for b in hub.banks.values() if b["owner_email"] == claims.get("sub")), None)
                else:
                    bank = hub.banks.get(ref)
                if bank is None or not hub.visible(bank, claims):
                    self._answer(404, {"error": "not found"})
                    return
                if method == "GET" and segments[3] == "dash":
                    view = "/".join(segments[4:])
                    if view not in DASH_VIEWS:
                        self._answer(404, {"error": "unknown view"})
                        return
                    status, payload = hub.view_data(bank, view, record["query"])
                    self._answer(status, payload)
                    return
                if method == "POST" and segments[3] == "memories" and len(segments) == 6 and segments[5] in ("update", "forget", "meta"):
                    if bank["stale"]:
                        self._answer(409, {"error": "stale"})
                        return
                    change = {"id": segments[4], "op": segments[5], "body": body, "claims": claims}
                    bank["changes"].append(change)
                    self._answer(200, {"ok": True, "id": segments[4], "op": segments[5]})
                    return
                self._answer(404, {"error": "not found"})

            def do_GET(self):  # noqa: N802
                self._handle("GET")

            def do_POST(self):  # noqa: N802
                self._handle("POST")

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = self._server.server_address[1]
        assert port != FORBIDDEN_PORT
        server = self._server
        self._thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
        self._thread.start()
        return f"http://127.0.0.1:{port}"

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def calls(self, prefix: str = "") -> list[dict]:
        with self._lock:
            return [r for r in self.requests if r["path"].startswith(prefix)]
