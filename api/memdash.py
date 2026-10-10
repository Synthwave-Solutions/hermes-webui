"""Memory explorer routes under ``/api/memdash/`` (plan addendum 6.6.5).

Exact routes (catalogue ``chat:use``, no prefix rule, PLAN E.7.5.1):

* ``GET /api/memdash/banks``: the enabled flag, the notice state and the store
  picker (members: their own stores; admins: the stores in their scope);
* ``GET /api/memdash/v1/view?bank=<ref|me>&view=<name>&...``: read views;
* ``POST /api/memdash/v1/action``: changes (hub mode only);
* ``GET /api/memdash/access-log?scope=me|all|store&store=<ref>``;
* ``POST /api/memdash/access-log/seen`` and ``POST /api/memdash/notice``.

Handler order (fail closed at every step):

1. an authenticated, interactive WebUI session with an email and the CSRF
   token; API tokens, trusted-header and profile-bound sessions and auth
   disabled get 403;
2. ``memdash_enabled``; for a store that is not the viewer's own person
   store also the admin-view switch ``HERMES_WEBUI_MNEMO_ADMIN_VIEW=1``
   (otherwise 404);
3. scope (a policy error gives 503, never a wider scope);
4. registry resolve (an unknown reference gives 404);
5. authorize (a foreign or cross-organisation store gives 404, the same
   answer as a store that does not exist, audited as ``memory.admin_denied``);
6. rate limits (views 20 per second, changes 30 per minute, opening other
   people's stores 60 per hour, with a security event above that);
7. for another person's store, the access-log row first (a failed write
   gives 503 and no data);
8. the backend call (a 30-second result cache sits after 5 to 7);
9. the response filter;
10. ``Cache-Control: no-store``.

While ``memdash_enabled`` is off (the default) every route answers exactly
like an unknown route (the handlers return ``False``, a 404), whoever asks, so
the switched-off explorer is indistinguishable from the E.7.5.1 stubs.

The actor comes only from the session; ``email`` or ``user`` fields in a body
or query are ignored.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import OrderedDict, deque
from urllib.parse import parse_qs

from api import memdash_access_log as access_log
from api import memdash_backend as backends
from api import memdash_registry as registry
from api import memdash_scope as scope
from api import memdash_views as views

logger = logging.getLogger(__name__)

GET_ROUTES = ("/api/memdash/banks", "/api/memdash/v1/view", "/api/memdash/access-log")
POST_ROUTES = ("/api/memdash/v1/action", "/api/memdash/access-log/seen", "/api/memdash/notice")
NOTICE_VERSION = "memdash-notice-1"
MAX_BODY_BYTES = 64 * 1024
MAX_QUERY_BYTES = 2048
CACHE_TTL = 30.0
CACHE_MAX = 256
_EMAIL_RE = re.compile(r"^[^@\s\x00-\x1f\x7f]{1,128}@[^@\s\x00-\x1f\x7f]{1,125}$")


# ── Responses ────────────────────────────────────────────────────────────────

def _send(handler, payload, status: int = 200) -> bool:
    from api.helpers import j

    # j() sends Cache-Control: no-store, nosniff and the security headers.
    j(handler, payload, status=status)
    return True


def _forbidden(handler) -> bool:
    return _send(handler, {"error": "forbidden"}, 403)


def _not_found(handler) -> bool:
    return _send(handler, {"error": "not found"}, 404)


def _unavailable(handler, message: str = "Memory explorer is not available right now. Try again later.") -> bool:
    return _send(handler, {"error": "unavailable", "message": message}, 503)


# ── Step 1: an interactive session ───────────────────────────────────────────

def _auth_enabled(handler) -> bool:
    from api import auth

    return bool(auth.is_auth_enabled())


def _session_identity(handler):
    from api.governance.enforce import _request_identity

    return _request_identity(handler)


def _csrf_ok(handler) -> bool:
    from api import auth

    cookie = auth.parse_cookie(handler) or ""
    token = handler.headers.get(auth.CSRF_HEADER_NAME) or ""
    return bool(cookie and token and auth.verify_csrf_token(cookie, token))


def interactive_identity(handler) -> dict | None:
    """The session identity of an interactive browser request, or None."""
    try:
        if not _auth_enabled(handler):
            return None
        headers = getattr(handler, "headers", None) or {}
        if headers.get("Authorization") or headers.get("X-Api-Key"):
            return None  # API tokens never reach the explorer
        identity = _session_identity(handler)
        if not isinstance(identity, dict):
            return None
        if identity.get("method") == "auth_disabled":
            return None
        if any(identity.get(k) is not None for k in ("auth_type", "username", "bound_profile")):
            return None  # trusted-header (gateway) and profile-bound sessions
        email = str(identity.get("email") or "").strip().lower()
        if not _EMAIL_RE.match(email):
            return None
        if not _csrf_ok(handler):
            return None
        return identity
    except Exception:
        logger.warning("memdash identity check failed", exc_info=True)
        return None


# ── Rate limits and the result cache ─────────────────────────────────────────

class _Window:
    def __init__(self, limit: int, seconds: float):
        self.limit = limit
        self.seconds = seconds
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > self.seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            if len(self._hits) > 4096:
                for stale in [k for k, v in self._hits.items() if not v]:
                    self._hits.pop(stale, None)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


VIEW_RATE = _Window(20, 1.0)
ACTION_RATE = _Window(30, 60.0)
OPEN_RATE = _Window(60, 3600.0)
_CACHE: "OrderedDict[tuple, tuple[float, object, int]]" = OrderedDict()
_CACHE_LOCK = threading.Lock()


def reset_state() -> None:
    """Clear rate windows and the cache (tests)."""
    for window in (VIEW_RATE, ACTION_RATE, OPEN_RATE):
        window.reset()
    with _CACHE_LOCK:
        _CACHE.clear()


def _cache_get(key: tuple):
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if not entry:
            return None
        if time.monotonic() - entry[0] > CACHE_TTL:
            _CACHE.pop(key, None)
            return None
        _CACHE.move_to_end(key)
        return entry[1], entry[2]


def _cache_put(key: tuple, data, status: int) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), data, status)
        _CACHE.move_to_end(key)
        while len(_CACHE) > CACHE_MAX:
            _CACHE.popitem(last=False)


# ── Audit (governance mirror, never content) ─────────────────────────────────

def _audit(event: str, viewer: scope.Viewer, store: registry.Store | None, *, path: str, method: str,
           outcome: str, extra: dict | None = None) -> None:
    try:
        from api.governance.audit import append_audit_event

        data = {
            "scope": ("store:" + store.ref) if store else "",
            "store_kind": store.kind if store else "",
            "owner_hash": store.owner_hash if store else "",
            "role": viewer.kind,
            "outcome": outcome,
        }
        data.update(extra or {})
        append_audit_event(event, subject_email=viewer.email, path=path, method=method, reason=outcome, extra=data)
    except Exception:
        logger.warning("memdash governance audit mirror failed", exc_info=True)


# ── Shared steps 3 to 5 ──────────────────────────────────────────────────────

class _Stop(Exception):
    def __init__(self, status: int, payload: dict | None = None):
        super().__init__(status)
        self.status = status
        self.payload = payload or {}


def _viewer(identity, config) -> scope.Viewer:
    try:
        return scope.resolve_viewer(identity, config)
    except scope.ScopeUnavailable:
        raise _Stop(503) from None


def _backend(viewer):
    try:
        return backends.select_backend(is_hq=viewer.is_hq)
    except backends.BackendUnavailable:
        raise _Stop(503) from None


def _stores(backend, viewer, identity) -> list[registry.Store]:
    try:
        return backend.list_stores(viewer, identity)
    except (backends.BackendUnavailable, backends.BackendRefused, registry.RegistryUnavailable):
        raise _Stop(503) from None
    except backends.StoreNotFound:
        return []


def _resolve(ref: str, viewer, stores) -> registry.Store:
    ref = str(ref or "me").strip()
    if ref == "me":
        store = registry.primary_for(viewer, stores)
    elif registry.valid_ref(ref):
        store = next((s for s in stores if s.ref == ref), None)
    else:
        store = None
    if store is None:
        raise _Stop(404)
    return store


def _authorized(viewer, store, config, *, path: str, method: str) -> None:
    if not registry.authorize(viewer, store, config):
        # Audited for the actor, never shown to the store's owner (6.6.8).
        _audit("memory.admin_denied", viewer, store, path=path, method=method, outcome="denied")
        raise _Stop(404)
    if not store.is_own(viewer) and not config.admin_view:
        raise _Stop(404)


def _one(qs: dict, name: str, default: str = "") -> str:
    values = qs.get(name)
    if not values:
        return default
    return str(values[-1])


def _can_edit(viewer, store, config, backend) -> bool:
    if not getattr(backend, "changes_available", False):
        return False
    if store.is_own(viewer):
        return True
    if not viewer.is_admin:
        return False
    if store.kind == "personal":
        return config.edit_personal
    return True


def _notice(viewer: scope.Viewer, config: scope.Config) -> dict:
    if not config.admin_view:
        variant = ""
    elif viewer.is_hq:
        variant = "platform_only"
    elif config.view_org_admins and config.view_platform_admins:
        variant = "org_and_platform"
    elif config.view_org_admins:
        variant = "org_only"
    elif config.view_platform_admins:
        variant = "platform_only"
    else:
        variant = ""
    try:
        acked = access_log.notice_acked(viewer.email, NOTICE_VERSION)
    except access_log.AccessLogError:
        acked = False
    return {"version": NOTICE_VERSION, "variant": variant, "required": bool(variant) and not acked}


# ── Routes ───────────────────────────────────────────────────────────────────

def handle_get(handler, parsed) -> bool:
    if parsed is None or parsed.path not in GET_ROUTES:
        return False
    config = scope.load_config()
    if not config.enabled:
        return False  # switched off: an unknown route
    if getattr(parsed, "params", ""):
        return _not_found(handler)  # ";" path parameters never reach a route
    identity = interactive_identity(handler)
    if identity is None:
        return _forbidden(handler)
    query = getattr(parsed, "query", "") or ""
    if len(query.encode("utf-8")) > MAX_QUERY_BYTES:
        return _send(handler, {"error": "query too long"}, 414)
    try:
        qs = parse_qs(query, keep_blank_values=True, max_num_fields=64)
    except ValueError:
        return _send(handler, {"error": "bad request"}, 400)
    try:
        if parsed.path == "/api/memdash/banks":
            return _banks(handler, identity, config)
        if parsed.path == "/api/memdash/v1/view":
            return _view(handler, identity, config, qs)
        return _access_log(handler, identity, config, qs)
    except _Stop as stop:
        if stop.status == 503:
            return _unavailable(handler)
        return _send(handler, stop.payload or {"error": "not found" if stop.status == 404 else "refused"}, stop.status)


def handle_post(handler, parsed, body) -> bool:
    if parsed is None or parsed.path not in POST_ROUTES:
        return False
    config = scope.load_config()
    if not config.enabled:
        return False  # switched off: an unknown route
    if getattr(parsed, "params", ""):
        return _not_found(handler)
    identity = interactive_identity(handler)
    if identity is None:
        return _forbidden(handler)
    if not isinstance(body, dict):
        return _send(handler, {"error": "bad request"}, 400)
    try:
        size = len(json.dumps(body, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError):
        return _send(handler, {"error": "bad request"}, 400)
    if size > MAX_BODY_BYTES:
        return _send(handler, {"error": "request too large"}, 413)
    try:
        if parsed.path == "/api/memdash/v1/action":
            return _action(handler, identity, config, body)
        viewer = _viewer(identity, config)
        if parsed.path == "/api/memdash/access-log/seen":
            try:
                until = int(body.get("until_id"))
            except (TypeError, ValueError):
                return _send(handler, {"error": "until_id is required"}, 400)
            try:
                value = access_log.mark_seen(viewer.email, until)
            except access_log.AccessLogError:
                raise _Stop(503) from None
            return _send(handler, {"ok": True, "seen_until_id": value})
        if str(body.get("version") or "") != NOTICE_VERSION:
            return _send(handler, {"error": "unknown notice version"}, 400)
        try:
            access_log.ack_notice(viewer.email, NOTICE_VERSION)
        except access_log.AccessLogError:
            raise _Stop(503) from None
        return _send(handler, {"ok": True, "version": NOTICE_VERSION})
    except _Stop as stop:
        if stop.status == 503:
            return _unavailable(handler)
        return _send(handler, stop.payload or {"error": "not found" if stop.status == 404 else "refused"}, stop.status)


def _banks(handler, identity, config) -> bool:
    viewer = _viewer(identity, config)
    notice = _notice(viewer, config)
    try:
        unseen = access_log.unseen_count(viewer.email)
    except access_log.AccessLogError:
        unseen = 0
    payload = {
        "enabled": True,
        "available": False,
        "viewer": {"kind": viewer.kind, "display": viewer.display_name, "admin": viewer.is_admin},
        "admin_view": bool(config.admin_view and viewer.is_admin),
        "notice": notice,
        "unseen": unseen,
        "stores": [],
        "me": None,
        "changes_available": False,
    }
    try:
        backend = backends.select_backend(is_hq=viewer.is_hq)
        stores = backend.list_stores(viewer, identity)
    except (backends.BackendUnavailable, backends.BackendRefused, backends.StoreNotFound, registry.RegistryUnavailable):
        return _send(handler, payload)
    visible = [s for s in stores if registry.authorize(viewer, s, config) and (s.is_own(viewer) or config.admin_view)]
    group_rank = {"mine": 0, "people": 1, "assistants": 2, "shared": 3}
    entries = []
    for store in visible:
        group = registry.group_of(viewer, store)
        entries.append({
            "ref": store.ref,
            "label": store.label,
            "kind": store.kind,
            "group": group,
            "owner": store.owner_display,
            "org_label": store.org_name or viewer.org_name,
            "last_write": store.last_write,
            "mixed": store.mixed,
            "own": store.is_own(viewer),
            "primary": store.primary and store.is_own(viewer),
        })
    entries.sort(key=lambda e: (group_rank.get(e["group"], 9), not e["primary"], e["org_label"].lower(),
                                e["label"].lower(), e["ref"]))
    primary = registry.primary_for(viewer, stores)
    payload.update({
        "available": True,
        "stores": entries,
        "me": primary.ref if primary else None,
        "changes_available": bool(getattr(backend, "changes_available", False)),
    })
    return _send(handler, payload)


def _view(handler, identity, config, qs) -> bool:
    view = _one(qs, "view")
    if view in views.REFUSED or view not in views.VIEWS:
        return _not_found(handler)
    viewer = _viewer(identity, config)
    backend = _backend(viewer)
    stores = _stores(backend, viewer, identity)
    store = _resolve(_one(qs, "bank", "me"), viewer, stores)
    path = "/api/memdash/v1/view"
    _authorized(viewer, store, config, path=path, method="GET")
    own = store.is_own(viewer)
    if not VIEW_RATE.allow(viewer.email_hash):
        return _send(handler, {"error": "too many requests"}, 429)
    raw = {k: v for k, v in qs.items() if k not in views.CONTROL_PARAMS}
    try:
        kwargs = views.normalize(view, raw)
    except views.ViewError:
        return _send(handler, {"error": "bad request"}, 400)
    spec = views.VIEWS[view]
    if spec.synthetic:
        return _synthetic(handler, view, kwargs, viewer, store, config, backend)
    if not own:
        _log_view(viewer, store, view, kwargs, qs, config)
    try:
        version = backend.data_version(store)
    except Exception:
        version = ""
    cache_key = (store.ref, view, json.dumps(kwargs, sort_keys=True, default=str), version)
    cached = _cache_get(cache_key)
    if cached is not None:
        data, status = cached
    else:
        try:
            data, status = backend.view(store, view, views.to_query(view, kwargs), viewer, identity)
        except backends.StoreNotFound:
            return _not_found(handler)
        except backends.BackendRefused:
            _audit("memory.admin_denied", viewer, store, path=path, method="GET", outcome="hub_refused")
            return _not_found(handler)
        except backends.BackendUnavailable:
            raise _Stop(503) from None
        if status == 200:
            _cache_put(cache_key, data, status)
    mask = (not own) and config.mask_secrets
    return _send(handler, views.filter_response(data, mask=mask), status if status in (200, 404) else 200)


def _log_view(viewer, store, view, kwargs, qs, config) -> None:
    code, text = access_log.clean_reason(_one(qs, "reason_code", "none"), _one(qs, "reason_text"))
    try:
        new_session = access_log.is_new_session(viewer.email, store.ref)
    except access_log.AccessLogError:
        raise _Stop(503) from None
    if new_session:
        if not OPEN_RATE.allow(viewer.email_hash):
            _audit("memory.admin_rate_limited", viewer, store, path="/api/memdash/v1/view", method="GET",
                   outcome="refused", extra={"limit": "open_per_hour"})
            raise _Stop(429, {"error": "too many requests"})
        action = "open"
    else:
        action = views.log_action(view, kwargs)
    entry = access_log.Entry(
        viewer_email=viewer.email, viewer_display=viewer.display_name, viewer_role=viewer.kind,
        subject_email="", store_ref=store.ref, store_kind=store.kind, org_id=store.org_id,
        action=action, reason_code=code, reason_text=text, item_id=views.item_id(view, kwargs),
    )
    try:
        access_log.append(entry, subject_hash=store.owner_hash if store.is_person_store else "")
    except access_log.AccessLogError:
        raise _Stop(503) from None
    access_log.purge_if_due(config.retention_days)
    if new_session:
        _audit("memory.admin_read", viewer, store, path="/api/memdash/v1/view", method="GET", outcome="allowed",
               extra={"mixed": store.mixed, "reason_code": code})


def _synthetic(handler, view, kwargs, viewer, store, config, backend) -> bool:
    can_edit = _can_edit(viewer, store, config, backend)
    if view == "auth/status":
        return _send(handler, {
            "auth_enabled": False, "authenticated": True, "has_password": False,
            "config": {"host": "127.0.0.1", "memory_admin_enabled": can_edit},
        })
    if view == "health":
        return _send(handler, {"ok": True, "read_only": not can_edit})
    if view == "realtime/status":
        return _send(handler, {
            "live_enabled": False, "streaming_supported": False, "deltasync_supported": False,
            "event_types": [], "snapshot_event_count": 0,
        })
    try:
        rows = access_log.rows_for_store(store.ref, limit=kwargs.get("limit", 100))
    except access_log.AccessLogError:
        raise _Stop(503) from None
    return _send(handler, {"items": rows})


def _action(handler, identity, config, body) -> bool:
    viewer = _viewer(identity, config)
    backend = _backend(viewer)
    stores = _stores(backend, viewer, identity)
    store = _resolve(str(body.get("bank") or "me"), viewer, stores)
    path = "/api/memdash/v1/action"
    _authorized(viewer, store, config, path=path, method="POST")
    own = store.is_own(viewer)
    if not ACTION_RATE.allow(viewer.email_hash):
        return _send(handler, {"error": "too many requests"}, 429)
    if not getattr(backend, "changes_available", False):
        return _send(handler, {"error": "changes_unavailable", "message": "Changes are not available yet."}, 503)
    try:
        change = views.normalize_action(body)
    except views.ViewError as exc:
        return _send(handler, {"error": str(exc)}, 400)
    code, text = access_log.clean_reason(body.get("reason_code"), body.get("reason_text"))
    if not own:
        if not viewer.is_admin:
            raise _Stop(404)
        if store.kind == "personal" and not config.edit_personal:
            return _send(handler, {"error": "changes to another person's memories are off"}, 403)
        if code == "none":
            return _send(handler, {"error": "a reason is required"}, 400)
        log_action = views.ACTION_LOG[change["action"]]
        entry = access_log.Entry(
            viewer_email=viewer.email, viewer_display=viewer.display_name, viewer_role=viewer.kind,
            subject_email="", store_ref=store.ref, store_kind=store.kind, org_id=store.org_id,
            action=log_action, reason_code=code, reason_text=text, item_id=change["memory_id"],
        )
        try:
            access_log.append(entry, subject_hash=store.owner_hash if store.is_person_store else "")
        except access_log.AccessLogError:
            raise _Stop(503) from None
        _audit("memory.admin_forget" if log_action == "forget" else "memory.admin_edit", viewer, store,
               path=path, method="POST", outcome="allowed", extra={"reason_code": code})
    change["reason_code"] = code
    change["reason_text"] = text
    try:
        result = backend.action(store, change, viewer, identity)
    except backends.ChangesUnavailable:
        return _send(handler, {"error": "changes_unavailable", "message": "Changes are not available yet."}, 503)
    except backends.StaleEdit:
        return _send(handler, {"error": "This memory changed in the meantime."}, 409)
    except backends.StoreNotFound:
        return _not_found(handler)
    except backends.BackendRefused:
        _audit("memory.admin_denied", viewer, store, path=path, method="POST", outcome="hub_refused")
        return _not_found(handler)
    except backends.BackendUnavailable:
        raise _Stop(503) from None
    with _CACHE_LOCK:
        for key in [k for k in _CACHE if k[0] == store.ref]:
            _CACHE.pop(key, None)
    payload = views.filter_response(result if isinstance(result, dict) else {}, mask=not own and config.mask_secrets)
    payload.setdefault("ok", True)
    return _send(handler, payload)


def _access_log(handler, identity, config, qs) -> bool:
    viewer = _viewer(identity, config)
    which = _one(qs, "scope", "me")
    try:
        if which == "me":
            return _send(handler, access_log.subject_view(viewer.email))
        if which == "all":
            if viewer.kind != scope.PLATFORM_ADMIN:
                return _not_found(handler)
            return _send(handler, {"items": access_log.rows_all()})
        if which == "store":
            backend = _backend(viewer)
            stores = _stores(backend, viewer, identity)
            store = _resolve(_one(qs, "store"), viewer, stores)
            _authorized(viewer, store, config, path="/api/memdash/access-log", method="GET")
            return _send(handler, {"items": access_log.rows_for_store(store.ref)})
    except access_log.AccessLogError:
        raise _Stop(503) from None
    return _not_found(handler)
