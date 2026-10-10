"""The Memory explorer adapter routes (addendum 6.6.5, 6.6.6, 6.6.10; PLAN C and E.7.5.1).

Exact catalogue rules; an interactive session only; members only their own
stores; admins only stores in scope, 404 for a foreign, cross-organisation or
owner-private store (the same answer as a store that does not exist, audited
as ``memory.admin_denied``); the admin view only with
``HERMES_WEBUI_MNEMO_ADMIN_VIEW=1``; a policy error gives 503; changes to
another person's personal store only with ``memory_admin_edit_personal`` and a
reason; the actor only from the session; switched off, every route answers
like an unknown route.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlencode

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures" / "memdash"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _fake_mnemo_hub_dash as fake  # noqa: E402
import memdash_harness as H  # noqa: E402
from api import memdash_registry as registry  # noqa: E402
from api import memdash_scope as scope_mod  # noqa: E402

GET_ROUTES = ("/api/memdash/banks", "/api/memdash/v1/view", "/api/memdash/access-log")
POST_ROUTES = ("/api/memdash/v1/action", "/api/memdash/access-log/seen", "/api/memdash/notice")


@pytest.fixture
def env(monkeypatch, tmp_path):
    environment = H.Env(monkeypatch, tmp_path)
    yield environment
    environment.close()


@pytest.fixture
def hub_env(monkeypatch, tmp_path):
    key = os.urandom(32)
    token = "fake-webui-token-" + os.urandom(8).hex()
    minter = fake.FakeMinter(key, token)
    monkeypatch.setitem(sys.modules, "api.mnemo_actor", minter.module())
    server = fake.FakeHub(key=key, token=token)
    # A two-organisation registry; the hub lists everything, so every
    # boundary below is the adapter's own.
    server.visible = lambda bank, claims: True
    server.add_bank("acme-ada", kind="personal", owner_email=H.ADA, owner_display="Ada Lovelace", org="org_acme",
                    memories=[{"id": "m1", "content": "note"}])
    server.add_bank("acme-bob", kind="personal", owner_email=H.BOB, owner_display="Bob", org="org_acme",
                    memories=[{"id": "b1", "content": "bob note"}])
    server.add_bank("acme-ext", kind="personal", owner_email="ext@partner.test", owner_display="Ext", org="org_acme",
                    external=True)
    server.add_bank("beta-bea", kind="personal", owner_email="bea@beta.test", owner_display="Bea", org="org_beta")
    server.add_bank("noorg-nia", kind="personal", owner_email="nia@nowhere.test", owner_display="Nia", org="")
    server.add_bank("acme-team", kind="org", label="Acme team", org="org_acme")
    server.add_bank("acme-dept", kind="dept", label="Acme sales", org="org_acme")
    server.add_bank("acme-assistant", kind="assistant", label="Acme assistant", org="org_acme")
    server.add_bank("acme-shared", kind="shared", label="Mixed", org="org_acme", mixed=True)
    server.add_bank("beta-team", kind="org", label="Beta team", org="org_beta")
    server.add_bank("michael-default", kind="personal", owner_email=H.MICHAEL, owner_display="Michael",
                    owner_private=True)
    base = server.start()
    environment = H.Env(monkeypatch, tmp_path, backend="hub")
    monkeypatch.setenv("HERMES_WEBUI_MNEMO_URL", base)
    environment.hub = server
    yield environment
    environment.close()
    server.stop()


def _hub_ref(name: str) -> str:
    return registry.ref_for("hubapi:" + name)


def _inject_viewer(env, monkeypatch, kind: str, *, email: str = "olga@acme.test", org_id: str = "org_acme",
                   is_hq: bool = False, guest: bool = False):
    viewer = scope_mod.Viewer(email=email, email_hash=scope_mod.email_hash(email), display_name="Olga Org",
                              kind=kind, org_id=org_id, org_name="Acme", is_hq=is_hq, guest=guest)
    monkeypatch.setattr(env.scope, "resolve_viewer", lambda identity, config=None: viewer)
    env.as_user(email, "Olga Org")
    return viewer


def _denied(env) -> list[dict]:
    return [r for r in env.audit_rows() if r.get("event") == "memory.admin_denied"]


# ── Catalogue and route allowlist ────────────────────────────────────────────

def test_exact_catalogue_rules_and_no_prefix_rule():
    from api.governance.catalog import ROUTE_CATALOG, route_permission

    for path in GET_ROUTES + POST_ROUTES:
        assert route_permission(path, "GET") == "chat:use"
        assert route_permission(path, "POST") == "chat:use"
    rules = [r for r in ROUTE_CATALOG if str(getattr(r, "pattern", getattr(r, "path", ""))).startswith("/api/memdash")]
    assert rules and all(getattr(r, "match", "exact") == "exact" for r in rules)
    for path in ("/api/memdash/unknown", "/api/memdash", "/api/memdash/v1/view/x", "/api/memdash/v1/view;x"):
        assert route_permission(path, "GET") is None, path


@pytest.mark.parametrize("path", ["/api/memdash/unknown", "/api/memdash/v1", "/api/memdash/banks/x",
                                  "/api/memdash/v1/view/stats", "/api/memdash/v1/views"])
def test_unknown_children_are_not_handled(env, path):
    assert env.memdash.handle_get(H.Handler(), H.parsed(path)) is False
    assert env.memdash.handle_post(H.Handler(), H.parsed(path), {}) is False


def test_path_parameters_answer_404(env):
    env.as_user(H.ADA)
    handler = H.Handler()
    env.memdash.handle_get(handler, H.parsed("/api/memdash/v1/view;x?view=stats&bank=me"))
    # urlparse keeps ";x" in params for the last segment; the route is then
    # either unknown (False) or refused with 404, never answered.
    assert handler.status in (None, 404)
    assert env.get("/api/memdash/v1/view;x?view=stats").status == 404


@pytest.mark.parametrize("view", ["config", "diagnostics", "runtime/status", "realtime/events", "admin/backup",
                                  "auth/login", "admin/memory/invalidate", "../config", "stats/../config", ""])
def test_refused_app_paths_are_not_reachable(env, view):
    env.as_user(H.ADA)
    response = env.view("me", view)
    assert response.status == 404
    assert "config" not in response.body and "db_path" not in str(response.body)


def test_responses_are_never_cached(env):
    env.as_user(H.ADA)
    for response in (env.get("/api/memdash/banks"), env.view("me", "stats"), env.get("/api/memdash/access-log?scope=me"),
                     env.view("b_" + "0" * 32, "stats")):
        assert response.header("Cache-Control") == "no-store"


# ── Switched off ─────────────────────────────────────────────────────────────

def test_switched_off_every_route_answers_like_an_unknown_route(env):
    env.configure(enabled=False)
    for email in (H.ADA, H.MICHAEL):
        env.as_user(email)
        for path in GET_ROUTES:
            handler = H.Handler()
            assert env.memdash.handle_get(handler, H.parsed(path + "?view=stats&bank=me")) is False
            assert handler.status is None
        for path in POST_ROUTES:
            handler = H.Handler()
            assert env.memdash.handle_post(handler, H.parsed(path), {"version": "memdash-notice-1"}) is False
            assert handler.status is None
    assert not env.access_log.log_path().exists()


def test_the_default_config_is_off(monkeypatch):
    monkeypatch.delenv("HERMES_WEBUI_MEMDASH", raising=False)
    monkeypatch.delenv("HERMES_WEBUI_MNEMO_ADMIN_VIEW", raising=False)
    monkeypatch.setattr("api.config.load_settings", lambda: {})
    config = scope_mod.load_config()
    assert config.enabled is False and config.admin_view is False and config.edit_personal is False
    assert config.mask_secrets is True and config.retention_days == 730


# ── Interactive sessions only ────────────────────────────────────────────────

@pytest.mark.parametrize("case", ["api_token", "api_key", "gateway", "trusted_user", "profile_bound", "auth_disabled",
                                  "no_session", "no_csrf", "auth_off", "no_email"])
def test_only_an_interactive_session_reaches_the_explorer(env, monkeypatch, case):
    headers = {}
    identity = H.identity(H.MICHAEL, "Michael")
    if case == "api_token":
        headers["Authorization"] = "Bearer abc"
    elif case == "api_key":
        headers["X-Api-Key"] = "abc"
    elif case == "gateway":
        identity = dict(identity, auth_type="trusted_header")
    elif case == "trusted_user":
        identity = dict(identity, username="michael")
    elif case == "profile_bound":
        identity = dict(identity, bound_profile="engineering-ops")
    elif case == "auth_disabled":
        identity = dict(identity, method="auth_disabled")
    elif case == "no_session":
        identity = None
    elif case == "no_csrf":
        monkeypatch.setattr(env.memdash, "_csrf_ok", lambda handler: False)
    elif case == "auth_off":
        monkeypatch.setattr(env.memdash, "_auth_enabled", lambda handler: False)
    elif case == "no_email":
        identity = dict(identity, email="")
    env.identity = identity
    monkeypatch.setattr(env.memdash, "_session_identity", lambda handler: identity)
    for path in GET_ROUTES:
        response = env.get(path + "?view=stats&bank=me&scope=me", headers=headers)
        assert response.status == 403, (case, path)
    for path in POST_ROUTES:
        response = env.post(path, {"bank": "me", "action": "invalidate", "memory_id": "x", "until_id": 1,
                                   "version": "memdash-notice-1"}, headers=headers)
        assert response.status == 403, (case, path)
    assert env.access_log.rows_all() == []


def test_the_real_csrf_check_needs_the_sessions_token(env, monkeypatch):
    from api import auth

    monkeypatch.undo()
    handler = H.Handler({auth.CSRF_HEADER_NAME: "wrong"})
    monkeypatch.setattr(auth, "parse_cookie", lambda h: "cookie")
    monkeypatch.setattr(auth, "verify_csrf_token", lambda cookie, token: token == "right")
    assert env.memdash._csrf_ok(handler) is False
    handler = H.Handler({auth.CSRF_HEADER_NAME: "right"})
    assert env.memdash._csrf_ok(handler) is True
    monkeypatch.setattr(auth, "parse_cookie", lambda h: None)
    assert env.memdash._csrf_ok(handler) is False


def test_a_policy_error_answers_503_and_never_more(env):
    env.as_user(H.MICHAEL, "Michael")
    env.set_policy(None, error=RuntimeError("broken policy"))
    assert env.get("/api/memdash/banks").status == 503
    assert env.view("me", "stats").status == 503
    assert env.get("/api/memdash/access-log?scope=all").status == 503
    assert env.post("/api/memdash/v1/action", {"bank": "me", "action": "invalidate", "memory_id": "x"}).status == 503


# ── Members ──────────────────────────────────────────────────────────────────

def test_a_member_sees_only_their_own_stores_and_no_picker_for_others(env):
    env.as_user(H.ADA, "Ada Lovelace")
    banks = env.banks()
    assert banks["viewer"] == {"kind": "member", "display": "Ada Lovelace", "admin": False}
    assert banks["admin_view"] is False
    assert {s["group"] for s in banks["stores"]} == {"mine"}
    assert all(s["own"] for s in banks["stores"])
    assert sorted(s["label"] for s in banks["stores"]) == ["Ada Lovelace (ada) (legacy)", "Ada Lovelace (legacy)"]
    assert banks["me"] == env.ref_of(lambda s: s.store_id == "hub:u-ada")
    counts = env.view("me", "stats").body["counts"]
    assert counts["working_memory"] == 4


def test_a_member_with_a_foreign_or_forged_reference_gets_404_and_no_data(env):
    env.as_user(H.ADA, "Ada Lovelace")
    bob = env.ref_of(lambda s: s.store_id == "hub:u-bob")
    shared = env.ref_of(lambda s: s.store_id == "hub:team-shared")
    for ref in (bob, shared, "b_" + "f" * 32, "b_short", "../u-bob", "hub:u-bob", "/etc/passwd", "me\x00"):
        response = env.view(ref, "memories")
        assert response.status == 404, ref
        assert "items" not in response.body
    for ref in (bob, shared):
        response = env.post("/api/memdash/v1/action", {"bank": ref, "action": "invalidate", "memory_id": "bob-w0",
                                                       "reason_code": "support"})
        assert response.status == 404
        assert env.get("/api/memdash/access-log?" + urlencode({"scope": "store", "store": ref})).status == 404
        assert env.view(ref, "admin/audit").status == 404
    assert env.access_log.rows_all() == []


def test_the_actor_comes_only_from_the_session(env):
    env.as_user(H.ADA, "Ada Lovelace")
    response = env.get("/api/memdash/v1/view?" + urlencode({"bank": "me", "view": "stats", "email": H.BOB,
                                                           "user": H.BOB}))
    assert response.status == 200 and response.body["counts"]["working_memory"] == 4
    banks = env.get("/api/memdash/banks?email=" + H.MICHAEL).body
    assert banks["viewer"]["kind"] == "member"
    response = env.post("/api/memdash/access-log/seen", {"until_id": 5, "email": H.BOB})
    assert response.status == 200


def test_the_synthetic_answers(env):
    env.as_user(H.ADA, "Ada Lovelace")
    auth = env.view("me", "auth/status").body
    assert auth == {"auth_enabled": False, "authenticated": True, "has_password": False,
                    "config": {"host": "127.0.0.1", "memory_admin_enabled": False}}
    health = env.view("me", "health").body
    assert health["ok"] is True
    realtime = env.view("me", "realtime/status").body
    assert realtime["live_enabled"] is False and "db_path" not in realtime
    assert env.view("me", "admin/audit").body == {"items": []}


# ── Platform admins at HQ (interim) ──────────────────────────────────────────

def test_a_platform_admin_opens_another_persons_store_and_it_is_logged(env):
    env.as_user(H.YASER, "Yaser")
    ada = env.ref_of(lambda s: s.store_id == "hub:u-ada")
    banks = env.banks()
    assert banks["viewer"]["kind"] == "platform_admin" and banks["admin_view"] is True
    groups = {s["group"] for s in banks["stores"]}
    assert groups == {"mine", "people", "assistants", "shared"}
    mixed = [s for s in banks["stores"] if s["mixed"]]
    assert mixed and all(s["group"] == "shared" for s in mixed)
    response = env.view(ada, "stats", reason_code="asked")
    assert response.status == 200 and response.body["counts"]["working_memory"] == 4
    rows = env.access_log.rows_for_store(ada)
    assert [(r["action"], r["role"], r["reason_code"], r["viewer"]) for r in rows] == [
        ("open", "platform_admin", "asked", "Yaser")]
    # Ada sees it under Who viewed my memories.
    env.as_user(H.ADA, "Ada Lovelace")
    mine = env.get("/api/memdash/access-log?scope=me").body
    assert mine["unseen"] == 1 and mine["sessions"][0]["viewer"] == "Yaser"
    assert mine["sessions"][0]["role"] == "platform_admin" and mine["sessions"][0]["reason_code"] == "asked"


def test_the_admin_view_switch_off_hides_every_foreign_store_while_the_self_view_works(env):
    env.configure(admin_view=False)
    env.as_user(H.YASER, "Yaser")
    banks = env.banks()
    assert banks["admin_view"] is False and all(s["own"] for s in banks["stores"])
    for store in registry.interim_stores():
        if store.is_own(env.scope.resolve_viewer(H.identity(H.YASER), env.config)):
            continue
        assert env.view(store.ref, "stats").status == 404, store.store_id
    assert env.view("me", "stats").status == 200
    assert env.access_log.rows_all() == []


@pytest.mark.parametrize("admin", [H.YASER, H.ODIS, H.HRISHIKESH])
def test_michaels_owner_private_bank_is_refused_to_yaser_odis_and_hrishikesh(env, admin):
    env.as_user(admin)
    private = [s for s in registry.interim_stores() if s.private_owner_hash]
    assert {s.store_id for s in private} == {"hub:default", "profile:michael:default"}
    refs = {s["ref"] for s in env.banks()["stores"]}
    for store in private:
        assert store.ref not in refs
        response = env.view(store.ref, "memories", reason_code="support")
        assert response.status == 404 and "items" not in response.body
        assert env.get("/api/memdash/access-log?" + urlencode({"scope": "store", "store": store.ref})).status == 404
    assert env.access_log.rows_all() == []
    if admin != H.HRISHIKESH:
        assert len(_denied(env)) >= 2


def test_michael_opens_his_own_owner_private_banks_unlogged(env):
    env.as_user(H.MICHAEL, "Michael")
    banks = env.banks()
    own = [s for s in banks["stores"] if s["own"]]
    assert [s["label"] for s in own] == ["Michael (legacy)"]
    assert env.view(own[0]["ref"], "stats").status == 200
    assert env.access_log.rows_all() == []
    # His profile copy is fed by another identity too, so it is an assistant
    # store; it stays owner-private to him.
    copy = env.ref_of(lambda s: s.store_id == "profile:michael:default")
    listed = {s["ref"]: s for s in banks["stores"]}
    assert listed[copy]["group"] == "assistants" and not listed[copy]["own"]


def test_an_elevated_wildcard_account_and_delivery_roles_are_members(env):
    for email in (H.HRISHIKESH, H.DELIVERY, H.OWNERLESS):
        env.as_user(email)
        banks = env.banks()
        assert banks["viewer"]["kind"] == "member" and banks["admin_view"] is False
        ada = env.ref_of(lambda s: s.store_id == "hub:u-ada")
        assert env.view(ada, "stats").status == 404


# ── Changes (hub mode) ───────────────────────────────────────────────────────

def test_an_admin_change_on_a_personal_store_needs_the_flag_and_a_reason(hub_env):
    hub_env.as_user(H.YASER, "Yaser")
    ada = _hub_ref("acme-ada")
    hub_env.banks()
    body = {"bank": ada, "action": "supersede", "memory_id": "m1", "content": "fixed", "updated_at": "2026-09-01T00:00:00Z"}
    response = hub_env.post("/api/memdash/v1/action", dict(body, reason_code="support"))
    assert response.status == 403
    assert hub_env.view(ada, "auth/status").body["config"]["memory_admin_enabled"] is False
    hub_env.configure(edit_personal=True)
    assert hub_env.view(ada, "auth/status").body["config"]["memory_admin_enabled"] is True
    response = hub_env.post("/api/memdash/v1/action", body)
    assert response.status == 400 and "reason" in response.body["error"]
    response = hub_env.post("/api/memdash/v1/action", dict(body, reason_code="other", reason_text="Ada asked in a ticket"))
    assert response.status == 200
    rows = [r for r in hub_env.access_log.rows_for_store(ada) if r["action"] == "edit"]
    assert len(rows) == 1 and rows[0]["reason_text"] == "Ada asked in a ticket"
    change = hub_env.hub.banks["acme-ada"]["changes"][-1]
    assert change["op"] == "update" and change["claims"]["mem_admin"] == "platform"
    assert change["body"]["reason_code"] == "other"
    events = [r["event"] for r in hub_env.audit_rows()]
    assert "memory.admin_edit" in events
    # Ada sees the change.
    hub_env.as_user(H.ADA, "Ada Lovelace")
    session = hub_env.get("/api/memdash/access-log?scope=me").body["sessions"][0]
    assert session["changed"] == 1 and session["viewer"] == "Yaser"


def test_an_admin_forget_on_a_shared_store_needs_a_reason_but_no_personal_flag(hub_env):
    hub_env.as_user(H.YASER, "Yaser")
    team = _hub_ref("acme-team")
    hub_env.banks()
    response = hub_env.post("/api/memdash/v1/action", {"bank": team, "action": "invalidate", "memory_id": "t1"})
    assert response.status == 400
    response = hub_env.post("/api/memdash/v1/action", {"bank": team, "action": "invalidate", "memory_id": "t1",
                                                       "reason_code": "quality"})
    assert response.status == 200
    rows = hub_env.access_log.rows_for_store(team)
    assert rows[0]["action"] == "forget"
    assert "memory.admin_forget" in [r["event"] for r in hub_env.audit_rows()]
    assert hub_env.hub.banks["acme-team"]["changes"][-1]["op"] == "forget"


def test_change_validation(hub_env):
    hub_env.as_user(H.ADA, "Ada Lovelace")
    hub_env.banks()
    for body in ({"action": "explode", "memory_id": "m1"}, {"action": "invalidate"},
                 {"action": "supersede", "memory_id": "m1"}, {"action": "importance", "memory_id": "m1", "importance": 3},
                 {"action": "veracity", "memory_id": "m1", "veracity": "lies"},
                 {"action": "expiry", "memory_id": "m1", "valid_until": "tomorrow"}, {"action": "backup", "memory_id": "m1"}):
        response = hub_env.post("/api/memdash/v1/action", dict(body, bank="me"))
        assert response.status == 400, body
    assert hub_env.hub.banks["acme-ada"]["changes"] == []
    # The upstream backup flag is ignored.
    response = hub_env.post("/api/memdash/v1/action", {"bank": "me", "action": "invalidate", "memory_id": "m1", "backup": True})
    assert response.status == 200 and "backup" not in hub_env.hub.banks["acme-ada"]["changes"][-1]["body"]


def test_oversized_bodies_and_queries_are_refused(env):
    env.as_user(H.ADA, "Ada Lovelace")
    response = env.post("/api/memdash/v1/action", {"bank": "me", "action": "supersede", "memory_id": "x",
                                                   "content": "a" * (70 * 1024)})
    assert response.status == 413
    response = env.get("/api/memdash/v1/view?bank=me&view=search&q=" + "a" * 3000)
    assert response.status == 414
    assert env.post("/api/memdash/notice", ["not", "a", "dict"]).status == 400


# ── Organisation boundaries (injected scope, two-organisation registry) ──────

@pytest.mark.parametrize("bank, allowed", [
    ("acme-ada", True), ("acme-team", True), ("acme-dept", True), ("acme-assistant", True),
    ("beta-bea", False), ("beta-team", False), ("acme-ext", False), ("noorg-nia", False), ("acme-shared", False),
    ("michael-default", False),
])
def test_an_org_admin_sees_only_their_organisation(hub_env, monkeypatch, bank, allowed):
    _inject_viewer(hub_env, monkeypatch, scope_mod.ORG_ADMIN)
    listed = {s["ref"] for s in hub_env.banks()["stores"]}
    ref = _hub_ref(bank)
    response = hub_env.view(ref, "stats", reason_code="support")
    if allowed:
        assert ref in listed and response.status == 200
        rows = hub_env.access_log.rows_for_store(ref)
        assert rows and rows[0]["role"] == "org_admin"
    else:
        assert ref not in listed and response.status == 404 and "counts" not in response.body
        assert hub_env.access_log.rows_for_store(ref) == []
        denied = _denied(hub_env)
        assert denied and denied[-1]["extra"]["role"] == "org_admin"
        assert not hub_env.hub.calls("/v1/banks/" + bank + "/")


def test_an_org_admin_without_an_organisation_sees_nothing_foreign(hub_env, monkeypatch):
    _inject_viewer(hub_env, monkeypatch, scope_mod.ORG_ADMIN, org_id="")
    assert hub_env.banks()["stores"] == []
    assert hub_env.view(_hub_ref("acme-ada"), "stats").status == 404


def test_the_org_admin_switch_off_refuses_org_admins(hub_env, monkeypatch):
    hub_env.configure(view_org_admins=False)
    _inject_viewer(hub_env, monkeypatch, scope_mod.ORG_ADMIN)
    assert hub_env.view(_hub_ref("acme-ada"), "stats").status == 404


@pytest.mark.parametrize("bank", ["acme-ada", "beta-bea", "acme-ext", "noorg-nia", "acme-shared", "beta-team"])
def test_a_platform_admin_passes_every_organisation(hub_env, monkeypatch, bank):
    _inject_viewer(hub_env, monkeypatch, scope_mod.PLATFORM_ADMIN, email="staff@synthwave.test", org_id="", guest=True)
    assert hub_env.view(_hub_ref(bank), "stats", reason_code="safety").status == 200


def test_a_client_installation_platform_admin_needs_a_live_staff_guest_grant(hub_env, monkeypatch):
    hub_env.set_policy(H.hq_policy(installation={"kind": "managed"}, organization={"id": "org_acme", "name": "Acme"}))
    hub_env.as_user(H.MICHAEL, "Michael")
    ada = _hub_ref("acme-ada")
    banks = hub_env.banks()
    assert banks["viewer"]["kind"] == "member"
    assert hub_env.view(ada, "stats").status == 404
    monkeypatch.setattr(hub_env.scope, "_staff_guest_checker", lambda identity: True)
    assert hub_env.banks()["viewer"]["kind"] == "platform_admin"
    assert hub_env.view(ada, "stats", reason_code="support").status == 200


def test_the_interim_reader_is_refused_on_a_client_installation(env):
    env.set_policy(H.hq_policy(installation={"kind": "managed"}, organization={"id": "org_acme", "name": "Acme"}))
    env.as_user(H.ADA)
    assert env.banks()["available"] is False
    assert env.view("me", "stats").status == 503


# ── Access log routes ────────────────────────────────────────────────────────

def test_access_log_scopes(env):
    env.as_user(H.YASER, "Yaser")
    ada = env.ref_of(lambda s: s.store_id == "hub:u-ada")
    info = env.ref_of(lambda s: s.store_id == "hub:u-info")
    assert env.view(ada, "stats").status == 200
    assert env.view(info, "stats").status == 200
    everything = env.get("/api/memdash/access-log?scope=all").body["items"]
    assert {r["store"] for r in everything} == {ada, info}
    assert [r for r in everything if r["store"] == info][0]["mixed_or_shared"] is True
    assert len(env.get("/api/memdash/access-log?" + urlencode({"scope": "store", "store": ada})).body["items"]) == 1
    assert env.view(ada, "admin/audit").body["items"][0]["action"] == "open"
    assert env.get("/api/memdash/access-log?scope=nonsense").status == 404
    env.as_user(H.ADA, "Ada Lovelace")
    assert env.get("/api/memdash/access-log?scope=all").status == 404
    assert env.get("/api/memdash/access-log?" + urlencode({"scope": "store", "store": info})).status == 404
    mine = env.get("/api/memdash/access-log?scope=me").body
    assert len(mine["sessions"]) == 1 and mine["unseen"] == 1
    assert env.post("/api/memdash/access-log/seen", {"until_id": mine["last_id"]}).status == 200
    assert env.get("/api/memdash/access-log?scope=me").body["unseen"] == 0
    assert env.banks()["unseen"] == 0
    assert env.post("/api/memdash/access-log/seen", {}).status == 400


def test_own_only_mode_does_not_claim_administrator_access(env):
    env.configure(admin_view=False)
    env.as_user(H.ADA)
    assert env.banks()["notice"] == {"version": "memdash-notice-1", "variant": "", "required": False}


def test_the_notice_is_required_until_acknowledged(env):
    env.as_user(H.ADA, "Ada Lovelace")
    notice = env.banks()["notice"]
    assert notice == {"version": "memdash-notice-1", "variant": "platform_only", "required": True}
    assert env.post("/api/memdash/notice", {"version": "old"}).status == 400
    assert env.post("/api/memdash/notice", {"version": "memdash-notice-1"}).status == 200
    assert env.banks()["notice"]["required"] is False
    assert env.access_log.notice_acked(H.ADA, "memdash-notice-1")


def test_the_notice_names_the_administrators_that_apply_on_a_client_installation(hub_env):
    hub_env.set_policy(H.hq_policy(installation={"kind": "managed"}, organization={"id": "org_acme", "name": "Acme"}))
    hub_env.as_user(H.ADA)
    assert hub_env.banks()["notice"]["variant"] == "org_and_platform"
    hub_env.configure(view_platform_admins=False)
    assert hub_env.banks()["notice"]["variant"] == "org_only"
    hub_env.configure(view_platform_admins=True, view_org_admins=False)
    assert hub_env.banks()["notice"]["variant"] == "platform_only"


# ── Rate limits ──────────────────────────────────────────────────────────────

def test_view_rate_limit(env):
    env.as_user(H.ADA)
    statuses = [env.view("me", "stats").status for _ in range(25)]
    assert statuses[:20] == [200] * 20 and 429 in statuses[20:]


def test_opening_other_peoples_stores_is_limited_per_hour_with_a_security_event(env, monkeypatch):
    env.as_user(H.YASER, "Yaser")
    monkeypatch.setattr(env.memdash.OPEN_RATE, "limit", 2)
    refs = [env.ref_of(lambda s, i=i: s.store_id == i) for i in ("hub:u-ada", "hub:u-bob", "hub:u-odis")]
    assert env.view(refs[0], "stats").status == 200
    assert env.view(refs[1], "stats").status == 200
    response = env.view(refs[2], "stats")
    assert response.status == 429
    assert env.access_log.rows_for_store(refs[2]) == []
    assert any(r.get("event") == "memory.admin_rate_limited" for r in env.audit_rows())


def test_action_rate_limit(hub_env, monkeypatch):
    hub_env.as_user(H.ADA)
    hub_env.banks()
    monkeypatch.setattr(hub_env.memdash.ACTION_RATE, "limit", 3)
    statuses = [hub_env.post("/api/memdash/v1/action", {"bank": "me", "action": "importance", "memory_id": "m1",
                                                        "importance": 0.4}).status for _ in range(5)]
    assert statuses == [200, 200, 200, 429, 429]


# ── The result cache sits after authorisation and logging ────────────────────

def test_cached_results_are_still_authorised_and_logged(env):
    env.as_user(H.YASER, "Yaser")
    ada = env.ref_of(lambda s: s.store_id == "hub:u-ada")
    assert env.view(ada, "stats").status == 200
    assert env.view(ada, "stats").status == 200
    assert len(env.access_log.rows_for_store(ada)) == 2
    env.as_user(H.BOB, "Bob")
    assert env.view(ada, "stats").status == 404
