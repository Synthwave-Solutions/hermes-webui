"""The Memory explorer's two backends (plan addendum 6.6.7).

* ``HubBackend`` (the target): mnemo-hub's ``/v1/banks/*`` routes (A13h, Wave
  2), with the ``webui`` bearer token and an ``X-Mnemo-Actor`` assertion
  minted by A6's ``api.mnemo_actor.hub_headers`` (``ctx: ui`` plus the
  ``mem_admin`` and ``guest`` claims of the viewer). The import is guarded;
  until A6 merges, the hub backend answers 503.
* ``InterimSqliteBackend`` (HQ only, until A11, decision D75): a read-only
  reader child (``python -m api.memdash_reader``) over a pipe, registry paths
  only. It needs ``HERMES_WEBUI_MEMDASH_BACKEND=sqlite_interim`` and is refused
  when ``HERMES_WEBUI_MNEMO_URL`` is set or the policy does not say
  ``installation.kind: hq``. Changes answer 503 "Changes are not available
  yet". The WebUI process never opens a store file, and heavy regular
  expression work never holds the WebUI's interpreter lock.

Errors: ``StoreNotFound`` (404), ``BackendUnavailable`` (503),
``ChangesUnavailable`` (503), ``StaleEdit`` (409), ``BackendRefused`` (403).
"""

from __future__ import annotations

import json
import logging
import os
import select
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from api import memdash_registry as registry
from api.memdash_scope import Viewer

logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parents[1]
READER_TIMEOUT = 8.0
HUB_TIMEOUT = 10.0
MAX_HUB_RESPONSE = 8 * 1024 * 1024


class BackendUnavailable(RuntimeError):
    pass


class ChangesUnavailable(RuntimeError):
    pass


class StoreNotFound(LookupError):
    pass


class StaleEdit(RuntimeError):
    pass


class BackendRefused(PermissionError):
    pass


# ── Reader child ─────────────────────────────────────────────────────────────

class ReaderProcess:
    """One long-lived reader child; requests are serialised.

    ``command`` is injectable for tests. A request that takes longer than
    ``timeout`` seconds kills the child; the next request starts a new one.
    """

    def __init__(self, command: list[str] | None = None, timeout: float = READER_TIMEOUT):
        self.command = command or [sys.executable, "-E", "-s", "-m", "api.memdash_reader"]
        self.timeout = float(timeout)
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._allow: tuple[str, ...] = ()
        self._buffer = b""
        self._next_id = 1
        self.spawn_count = 0

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc and self._proc.poll() is None else None

    def _spawn(self, allow: tuple[str, ...]) -> None:
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
        }
        self._proc = subprocess.Popen(
            self.command, cwd=str(REPO), env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True,
        )
        self.spawn_count += 1
        self._buffer = b""
        self._allow = allow
        reply = self._exchange({"op": "init", "allow": list(allow)})
        if not reply.get("ok"):
            self._kill()
            raise BackendUnavailable("the reader did not start")

    def _kill(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        for stream in (proc.stdin, proc.stdout):
            try:
                if stream:
                    stream.close()
            except OSError:
                pass

    def close(self) -> None:
        with self._lock:
            self._kill()

    def _exchange(self, payload: dict) -> dict:
        proc = self._proc
        if proc is None or proc.poll() is not None:
            raise BackendUnavailable("the reader is not running")
        line = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        try:
            proc.stdin.write(line)
            proc.stdin.flush()
        except (OSError, ValueError) as exc:
            self._kill()
            raise BackendUnavailable("the reader stopped") from exc
        deadline = time.monotonic() + self.timeout
        fd = proc.stdout.fileno()
        while b"\n" not in self._buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._kill()
                raise BackendUnavailable("the reader timed out")
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                continue
            chunk = os.read(fd, 65536)
            if not chunk:
                self._kill()
                raise BackendUnavailable("the reader stopped")
            self._buffer += chunk
            if len(self._buffer) > 64 * 1024 * 1024:
                self._kill()
                raise BackendUnavailable("the reader answer is too large")
        raw, _, self._buffer = self._buffer.partition(b"\n")
        try:
            reply = json.loads(raw.decode("utf-8"))
        except ValueError as exc:
            self._kill()
            raise BackendUnavailable("the reader answered garbage") from exc
        return reply if isinstance(reply, dict) else {}

    def request(self, allow: tuple[str, ...], path: str, view: str, params: dict) -> tuple[dict, int]:
        with self._lock:
            if self._proc is None or self._proc.poll() is not None or allow != self._allow:
                self._kill()
                self._spawn(allow)
            request_id = self._next_id
            self._next_id += 1
            reply = self._exchange({"id": request_id, "path": path, "view": view, "params": params})
            if reply.get("id") != request_id:
                self._kill()
                raise BackendUnavailable("the reader answered out of order")
        if reply.get("ok"):
            return reply.get("data"), int(reply.get("status") or 200)
        error = reply.get("error")
        if error == "not_found":
            raise StoreNotFound("store not found")
        if error == "bad_request":
            raise StoreNotFound("unknown view")
        raise BackendUnavailable(f"the reader failed: {error}")


# ── Backends ─────────────────────────────────────────────────────────────────

class InterimSqliteBackend:
    name = "sqlite_interim"
    changes_available = False

    _shared: "InterimSqliteBackend | None" = None
    _shared_lock = threading.Lock()

    def __init__(self, reader: ReaderProcess | None = None):
        self.reader = reader or ReaderProcess()

    @classmethod
    def shared(cls) -> "InterimSqliteBackend":
        with cls._shared_lock:
            if cls._shared is None:
                cls._shared = cls()
            return cls._shared

    def list_stores(self, viewer: Viewer, identity: dict | None = None) -> list[registry.Store]:
        try:
            from dataclasses import replace
            personal = registry.personal_stores(viewer)
            legacy = registry.interim_stores()
            # Legacy bot-derived stores lack the current person-owned semantics.
            # Keep them explicitly labelled; the current private bank is primary.
            legacy = [replace(store, label=store.label + " (legacy)",
                              primary=store.primary and not any(p.primary for p in personal))
                      for store in legacy]
            return personal + legacy
        except registry.RegistryUnavailable as exc:
            raise BackendUnavailable(str(exc)) from exc

    def data_version(self, store: registry.Store) -> str:
        return registry._last_write(Path(store.backend_ref))

    def view(self, store: registry.Store, view: str, params: dict, viewer: Viewer, identity: dict | None = None):
        stores = self.list_stores(viewer)
        allow = tuple(sorted(s.backend_ref for s in stores))
        if store.backend_ref not in allow:
            raise StoreNotFound("store not in the registry")
        return self.reader.request(allow, store.backend_ref, view, params)

    def action(self, store, change: dict, viewer: Viewer, identity: dict | None = None):
        raise ChangesUnavailable("Changes are not available yet.")


def _mint_headers(identity: dict, *, mem_admin, guest: bool) -> dict:
    """A6's minter, imported guarded (pinned signature, addendum 8.2)."""
    try:
        from api.mnemo_actor import hub_headers
    except Exception as exc:
        raise BackendUnavailable("the memory service identity is not available") from exc
    try:
        return hub_headers(identity, ctx="ui", mem_admin=mem_admin, guest=guest)
    except Exception as exc:
        raise BackendUnavailable("the memory service identity could not be minted") from exc


class HubBackend:
    name = "hub"
    changes_available = True

    def __init__(self, base_url: str | None = None, minter=None, timeout: float = HUB_TIMEOUT):
        raw = (base_url if base_url is not None else os.environ.get("HERMES_WEBUI_MNEMO_URL", "")).strip()
        parts = urllib.parse.urlsplit(raw) if raw else None
        if not parts or parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.query:
            raise BackendUnavailable("the memory service URL is not configured")
        self.base_url = raw.rstrip("/")
        self.minter = minter or _mint_headers
        self.timeout = timeout

    def _call(self, method: str, path: str, viewer: Viewer, identity: dict, *, query: dict | None = None,
              body: dict | None = None):
        headers = dict(self.minter(identity, mem_admin=viewer.mem_admin_claim, guest=viewer.guest))
        headers["Accept"] = "application/json"
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=self.timeout) as response:
                raw = response.read(MAX_HUB_RESPONSE + 1)
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
            try:
                raw = exc.read(64 * 1024)
            except Exception:
                raw = b""
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise BackendUnavailable("the memory service is not reachable") from exc
        if len(raw) > MAX_HUB_RESPONSE:
            raise BackendUnavailable("the memory service answer is too large")
        if status == 404:
            raise StoreNotFound("not found at the memory service")
        if status == 403:
            raise BackendRefused("refused by the memory service")
        if status == 409:
            raise StaleEdit("the memory changed in the meantime")
        if status >= 400 or status < 200:
            raise BackendUnavailable(f"the memory service answered {status}")
        try:
            return json.loads(raw.decode("utf-8") or "null"), status
        except ValueError as exc:
            raise BackendUnavailable("the memory service answered garbage") from exc

    def list_stores(self, viewer: Viewer, identity: dict | None = None) -> list[registry.Store]:
        data, _ = self._call("GET", "/v1/banks", viewer, identity or {})
        entries = data.get("banks") if isinstance(data, dict) else None
        return registry.from_hub_entries(entries, viewer)

    def data_version(self, store: registry.Store) -> str:
        return store.last_write

    def view(self, store: registry.Store, view: str, params: dict, viewer: Viewer, identity: dict | None = None):
        path = "/v1/banks/" + urllib.parse.quote(store.backend_ref, safe="") + "/dash/" + urllib.parse.quote(view, safe="/")
        data, status = self._call("GET", path, viewer, identity or {}, query=params)
        return data, status

    def action(self, store: registry.Store, change: dict, viewer: Viewer, identity: dict | None = None):
        action = change["action"]
        route = {"invalidate": "forget", "supersede": "update"}.get(action, "meta")
        body = {k: v for k, v in change.items() if k not in ("action", "memory_id")}
        body["reason_code"] = change.get("reason_code", "none")
        path = ("/v1/banks/" + urllib.parse.quote(store.backend_ref, safe="") + "/memories/"
                + urllib.parse.quote(change["memory_id"], safe="") + "/" + route)
        data, _ = self._call("POST", path, viewer, identity or {}, body=body)
        return data


class LocalPersonalBackend(InterimSqliteBackend):
    """Read-only explorer restricted to this authenticated person's local banks."""
    name = "local_personal"
    _shared = None
    _shared_lock = threading.Lock()

    def data_version(self, store: registry.Store) -> str:
        # The shared reader remains read-only. Use sub-second DB/WAL revisions
        # so a consolidation immediately invalidates the 30-second view cache.
        revisions = []
        for suffix in ("", "-wal"):
            try:
                stat = os.stat(store.backend_ref + suffix)
                revisions.append((stat.st_mtime_ns, stat.st_size, stat.st_ino))
            except OSError:
                revisions.append(None)
        return repr(revisions)

    def list_stores(self, viewer: Viewer, identity: dict | None = None) -> list[registry.Store]:
        if not viewer.email or not viewer.email_hash:
            raise BackendRefused("Authenticated person required")
        try:
            return [store for store in registry.personal_stores(viewer) if store.is_own(viewer)]
        except registry.RegistryUnavailable as exc:
            raise BackendUnavailable(str(exc)) from exc


def select_backend(*, is_hq: bool):
    """The configured backend, or ``BackendUnavailable`` (addendum 6.6.7)."""
    mode = os.environ.get("HERMES_WEBUI_MEMDASH_BACKEND", "").strip()
    hub_url = os.environ.get("HERMES_WEBUI_MNEMO_URL", "").strip()
    if mode == "local_personal":
        if hub_url:
            raise BackendUnavailable("Choose either the local personal explorer or the hub")
        return LocalPersonalBackend.shared()
    if mode == "sqlite_interim":
        if hub_url:
            raise BackendUnavailable("the interim reader is off while a hub URL is set")
        if not is_hq:
            raise BackendUnavailable("the interim reader runs only at HQ")
        return InterimSqliteBackend.shared()
    if mode in ("", "hub"):
        return HubBackend()
    raise BackendUnavailable("unknown memory explorer backend")
