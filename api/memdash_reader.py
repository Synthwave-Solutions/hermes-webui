"""The Memory explorer's read-only reader child (plan addendum 6.6.7, D75).

Interim backend at HQ only, until A11 switches the explorer to the hub. The
WebUI starts one long-lived child with ``python -m api.memdash_reader`` and
talks to it over stdin and stdout (no socket), one JSON line per message:

* first line from the parent: ``{"op": "init", "allow": [paths]}``, the
  registry-path allowlist; the child answers ``{"ok": true, "init": n}``;
* then ``{"id": n, "path": p, "view": name, "params": {...}}`` per request,
  answered by ``{"id": n, "ok": true, "status": 200, "data": ...}`` or
  ``{"id": n, "ok": false, "error": "not_found" | "refused" | "timeout" |
  "bad_request" | "failed"}``.

Hardening: the child opens only allowlisted paths, ``file:<path>?mode=ro``
(never ``immutable``), with ``query_only`` on; memory is capped at 1 GiB
(``RLIMIT_AS``); SQLite work stops at a 6 second deadline; the parent kills
and respawns the child after 8 seconds. The child never writes to a store and
imports nothing from the WebUI but the vendored dashboard and the view table.
"""

from __future__ import annotations

import json
import sys

MEMORY_LIMIT_BYTES = 1 << 30
QUERY_DEADLINE_SECONDS = 6.0
MAX_LINE_BYTES = 256 * 1024


def _limit_memory() -> None:
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
    except (ImportError, ValueError, OSError):
        pass


def _write(out, payload: dict) -> None:
    out.write(json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":")) + "\n")
    out.flush()


def serve(stdin=None, stdout=None) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    from api import memdash_views as views
    from api.third_party import mnemosyne_dashboard as md

    initialised = False
    for raw in stdin:
        if len(raw) > MAX_LINE_BYTES:
            _write(stdout, {"id": None, "ok": False, "error": "bad_request"})
            continue
        try:
            msg = json.loads(raw)
        except ValueError:
            _write(stdout, {"id": None, "ok": False, "error": "bad_request"})
            continue
        if not isinstance(msg, dict):
            _write(stdout, {"id": None, "ok": False, "error": "bad_request"})
            continue
        if msg.get("op") == "init" and not initialised:
            allowed = md.allow_paths(p for p in (msg.get("allow") or []) if isinstance(p, str))
            initialised = True
            _write(stdout, {"ok": True, "init": len(allowed)})
            continue
        request_id = msg.get("id")
        if not initialised:
            _write(stdout, {"id": request_id, "ok": False, "error": "refused"})
            continue
        view = msg.get("view")
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
        try:
            kwargs = views.normalize(str(view or ""), params)
            store = md.DashboardStore(msg.get("path"))
            md.set_deadline(QUERY_DEADLINE_SECONDS)
            try:
                data, status = views.call(store, str(view), kwargs)
            finally:
                md.set_deadline(None)
            _write(stdout, {"id": request_id, "ok": True, "status": status, "data": data})
        except views.ViewError:
            _write(stdout, {"id": request_id, "ok": False, "error": "bad_request"})
        except FileNotFoundError:
            _write(stdout, {"id": request_id, "ok": False, "error": "not_found"})
        except PermissionError:
            _write(stdout, {"id": request_id, "ok": False, "error": "refused"})
        except Exception as exc:  # sqlite3.OperationalError('interrupted') and the rest
            error = "timeout" if "interrupt" in str(exc).lower() else "failed"
            _write(stdout, {"id": request_id, "ok": False, "error": error})
    return 0


def main() -> int:
    _limit_memory()
    return serve()


if __name__ == "__main__":
    sys.exit(main())
