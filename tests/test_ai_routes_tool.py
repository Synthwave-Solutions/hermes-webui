"""The chat tool for the AI model routes of a Cloud environment (api/ai_routes_tool.py).

A fake control plane (a real HTTP server on localhost) answers the signed
installation routes under /v1/customer/ai-routes and records every request.
Covered: only an organisation admin in a personal Cloud session gets through
(a partner, a department admin, a normal user, a password session and a
session without proof are refused before anything is sent), every change
waits for the approval and only then carries ``confirmed: true``, a secret is
never accepted, used or repeated, the overview becomes a compact card, and the
toolset is only offered to somebody who can use the tool.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api.ai_routes_tool as tool  # noqa: E402
import api.auth as auth  # noqa: E402
import api.org_structure as org  # noqa: E402
from api import control_plane_client as cpc  # noqa: E402
from api.governance import loader  # noqa: E402
from api.governance.models import GovernancePolicy, GovernanceUser  # noqa: E402

ADMIN = "boss@example.com"
MEMBER = "tom@example.com"
DEPT_ADMIN = "dana@example.com"
CONSULTANT = "carla@partner.example"
KEY_ID = "0a1b2c3d4e5f6071"
SECRET_HEX = "5f" * 16 + "a0" * 16
PROOF = "c3" * 32
JOB = "job_" + "ab" * 16
FAKE_KEY = "sk-proj-" + "Zx9Qw7Er5Ty3Ui1Op" * 2          # a made up value in the shape of a provider key

OVERVIEW = {
    "order_id": "sp_" + "0" * 32, "mode": "router", "checked_at": 1795000000, "stale": False, "default_combo": "standaard",
    "active_route": [{"position": 1, "model": "regolo/model-a", "provider": "regolo", "provider_label": "Regolo", "available": True, "billing": "prepaid_ledger"},
                     {"position": 2, "model": "mistral/model-b", "provider": "mistral", "provider_label": "Mistral", "available": True, "billing": "customer_own_key"}],
    "connections": [{"id": "conn-1", "provider": "mistral", "provider_label": "Mistral", "label": "Eigen Mistral", "owner": "customer", "priority": 1,
                     "enabled": True, "status": "active", "billing": "customer_own_key", "managed": False, "editable": True, "secret": "MUST-NOT-PASS"},
                    {"id": "conn-0", "provider": "synthpulse-cloud", "provider_label": "SynthPulse", "label": "Beheerd door Synthwave", "owner": "synthwave",
                     "enabled": True, "status": "active", "billing": "prepaid_ledger", "managed": True, "editable": False}],
    "billing": {"notice": "Gebruik op een eigen sleutel rekent de aanbieder met jullie af.", "customer_keys_billed_through_ledger": False},
    "providers": [{"id": "mistral", "label": "Mistral", "region": "EU", "requires_base_url": False, "managed": False}],
    "jobs": [], "secure_form_url": "https://cloud.example/synthpulse-cloud/ai-routes?environment=sp_x", "api_key": "MUST-NOT-PASS",
}


class FakeControlPlane:
    def __init__(self):
        self.requests = []
        self.status = 200
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _handle(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw) if raw else None
                fake.requests.append({"method": self.command, "path": self.path, "body": body,
                                      "headers": {k.lower(): v for k, v in self.headers.items()}})
                status = fake.status
                if status != 200:
                    payload = {"detail": "Alleen een eigenaar of beheerder van de organisatie beheert de AI-routes."}
                elif self.command == "POST" and (body or {}).get("confirmed") is not True:
                    status, payload = 422, {"detail": "Een wijziging vraagt je bevestiging."}
                elif self.command == "GET" and self.path == tool.PREFIX:
                    payload = OVERVIEW
                elif self.command == "GET" and self.path == tool.PREFIX + "/jobs/" + JOB:
                    payload = {"id": JOB, "action": "ai_routes_connection_test", "status": "succeeded", "stage": "done", "error_code": None,
                               "result": {"valid": True, "token": "MUST-NOT-PASS"}}
                elif self.command == "POST" and self.path == tool.PREFIX + "/connection-requests":
                    payload = {"request_id": "cr_" + "1" * 24, "provider": body["provider"], "label": body["label"], "route": body["route"],
                               "secure_form_url": "https://cloud.example/synthpulse-cloud/ai-routes?environment=sp_x&request=cr_" + "1" * 24,
                               "billing_notice": "Gebruik op een eigen sleutel rekent de aanbieder met jullie af."}
                elif self.command == "POST" and self.path == tool.PREFIX + "/limits":
                    payload = {"enabled": body["enabled"], "monthly_limit_cents": body["monthly_limit_cents"], "revision": body["expected_revision"] + 1}
                elif self.command == "POST" and re.fullmatch(re.escape(tool.PREFIX) + r"/connections/conn-1/(test|enable|disable|delete|route)", self.path):
                    payload = {"id": JOB, "action": "ai_routes_connection_" + self.path.rsplit("/", 1)[1], "status": "queued", "stage": "queued"}
                else:
                    status, payload = 404, {"detail": "Onbekende klantfunctie."}
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = _handle

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def ident(email, method="synthpulse_cloud"):
    return {"email": email, "groups": [], "method": method, "claims_subset": {}}


@pytest.fixture
def env(monkeypatch, tmp_path):
    import api.config as config

    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setattr(config, "STATE_DIR", state)
    for name in ("SP_CONTROL_SOCKET", "SP_CONTROL_URL", "SP_CONTROL_KEY_FILE", "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
                 "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SP_CLOUD_PERSONAL_MSP", "1")
    policy = GovernancePolicy(mode="enforce", bootstrap_admins=(ADMIN,), installation_kind="hq",
                              users={MEMBER: GovernanceUser(email=MEMBER), DEPT_ADMIN: GovernanceUser(email=DEPT_ADMIN)})
    monkeypatch.setattr(org, "_policy", lambda: policy)
    monkeypatch.setattr(loader, "get_policy", lambda: policy)
    admin = org.scope_for(ADMIN, policy=policy)
    org.apply(admin, {"op": "department.save", "key": "finance", "name": "Finance", "admins": [DEPT_ADMIN]})
    org.apply(admin, {"op": "team.save", "department": "finance", "name": "Debiteuren", "members": [MEMBER]})
    org.replace_cloud_partners([{"email": CONSULTANT, "name": "Carla", "role": "consultant"}])
    plane = FakeControlPlane()
    key = tmp_path / "control.key"
    key.write_text(f"{KEY_ID}:{SECRET_HEX}\n", encoding="utf-8")
    key.chmod(0o600)
    monkeypatch.setenv("SP_CONTROL_URL", plane.url)
    monkeypatch.setenv("SP_CONTROL_KEY_FILE", str(key))
    cpc.clear_cache()
    # Everybody here has a live personal Cloud session, so a refusal is about the person, not the session.
    sessions = {f"t{i}": {"email": email, "method": "synthpulse_cloud", "exp": time.time() + 600, "_cloud_msp_proof": PROOF}
                for i, email in enumerate((ADMIN, MEMBER, DEPT_ADMIN, CONSULTANT))}
    monkeypatch.setattr(auth, "_sessions", sessions)
    approvals = []

    def approve(decision):
        def ask(target, reason, operation_id):
            approvals.append({"target": target, "reason": reason, "operation_id": operation_id, "sent_before": sum(1 for r in plane.requests if r["method"] == "POST")})
            return {"approved": decision, "message": ""}
        return ask

    yield type("Env", (), {"plane": plane, "sessions": sessions, "approvals": approvals, "yes": approve(True), "no": approve(False)})
    plane.close()
    cpc.clear_cache()


def test_overview_for_an_organisation_admin_in_a_personal_session(env):
    got = tool.run({"action": "overview"}, ident(ADMIN), env.no)
    assert got["ok"] is True and env.approvals == []                     # reading asks no approval
    request = env.plane.requests[0]
    assert request["method"] == "GET" and request["path"] == "/v1/customer/ai-routes"
    assert request["headers"]["authorization"].startswith("SP-HMAC-SHA256 ")
    assert request["headers"]["x-sp-acting-user"] == ADMIN and request["headers"]["x-sp-cloud-session"] == PROOF
    assert [r["model"] for r in got["active_route"]] == ["regolo/model-a", "mistral/model-b"]
    assert got["connections"][0] == {"id": "conn-1", "provider": "mistral", "provider_label": "Mistral", "label": "Eigen Mistral", "owner": "customer",
                                     "enabled": True, "status": "active", "billing": "customer_own_key", "editable": True}
    assert got["secure_form_url"].startswith("https://cloud.example/") and got["billing_notice"].startswith("Gebruik op een eigen sleutel")
    # The compact card: one table block the chat draws itself.
    assert got["card"].startswith("```table\n") and got["card"].endswith("\n```")
    card = json.loads(got["card"].split("\n", 1)[1].rsplit("\n", 1)[0])
    assert card["columns"] == ["Plek", "Model", "Aanbieder", "Afrekening", "Beschikbaar"]
    assert card["rows"] == [[1, "regolo/model-a", "Regolo", "AI-tegoed", "Ja"], [2, "mistral/model-b", "Mistral", "Eigen sleutel", "Ja"]]
    assert "Via de modelrouter" in card["subtitle"] and "1 eigen verbinding" in card["subtitle"]
    text = json.dumps(got)
    assert "MUST-NOT-PASS" not in text and PROOF not in text and SECRET_HEX not in text
    for dash in (chr(0x2013), chr(0x2014)):
        assert dash not in text
    # Following a change is a read too.
    job = tool.run({"action": "job", "job_id": JOB}, ident(ADMIN), env.no)
    assert job == {"ok": True, "job_id": JOB, "action": "ai_routes_connection_test", "status": "succeeded", "stage": "done",
                   "error_code": None, "valid": True}


def test_every_change_waits_for_the_approval_and_only_then_confirms(env):
    changes = [
        ({"action": "test", "connection_id": "conn-1"}, "/connections/conn-1/test"),
        ({"action": "enable", "connection_id": "conn-1"}, "/connections/conn-1/enable"),
        ({"action": "disable", "connection_id": "conn-1"}, "/connections/conn-1/disable"),
        ({"action": "delete", "connection_id": "conn-1"}, "/connections/conn-1/delete"),
        ({"action": "place_in_route", "connection_id": "conn-1", "route": "primary", "model": "mistral/model-b"}, "/connections/conn-1/route"),
        ({"action": "prepare_connection", "provider": "mistral", "label": "Eigen Mistral", "route": "fallback", "model": "mistral/model-b"}, "/connection-requests"),
        ({"action": "set_limits", "enabled": True, "monthly_limit_cents": 25000, "expected_revision": 3, "note": "Budget voor het vierde kwartaal"}, "/limits"),
    ]
    # Refused on the card: nothing is sent at all.
    for args, _path in changes:
        got = tool.run(args, ident(ADMIN), env.no)
        assert got == {"ok": False, "error": "not_approved", "message": tool.NOT_APPROVED}, args
    posts = lambda: [r for r in env.plane.requests if r["method"] == "POST"]
    assert posts() == [] and len(env.approvals) == len(changes)
    # The model cannot bring its own confirmation.
    assert tool.run({"action": "test", "connection_id": "conn-1", "confirmed": True}, ident(ADMIN), env.yes)["error"] == "invalid"
    assert posts() == []
    # Approved: the approval came first, then one call with confirmed true.
    env.approvals.clear()
    env.plane.requests.clear()
    for index, (args, path) in enumerate(changes):
        got = tool.run(args, ident(ADMIN), env.yes)
        assert got["ok"] is True, (args, got)
        assert len(posts()) == index + 1
        assert env.approvals[index]["sent_before"] == index            # the card came before this change was sent
        request = env.plane.requests[-1]
        assert request["method"] == "POST" and request["path"] == tool.PREFIX + path
        assert request["body"]["confirmed"] is True and request["headers"]["x-sp-cloud-session"] == PROOF
    assert len({a["operation_id"] for a in env.approvals}) == len(changes)             # one approval for one change
    assert "Eigen Mistral" in env.approvals[5]["reason"] and "beveiligde pagina" in env.approvals[5]["reason"]
    assert "€ 250,00" in env.approvals[6]["reason"]
    assert posts()[4]["body"]["route"] == "primary" and posts()[4]["body"]["model"] == "mistral/model-b"
    assert re.fullmatch(r"[0-9a-f-]{36}", posts()[0]["body"]["request_key"])
    # The card names the connection, and a connection that is not the organisation's own gets no card at all.
    assert '"Eigen Mistral" (conn-1)' in env.approvals[0]["reason"]
    asked = len(env.approvals)
    assert tool.run({"action": "disable", "connection_id": "conn-0"}, ident(ADMIN), env.yes)["error"] == "not_editable"
    assert tool.run({"action": "disable", "connection_id": "conn-9"}, ident(ADMIN), env.yes)["error"] == "not_found"
    assert len(env.approvals) == asked and len(posts()) == len(changes)
    assert posts()[6]["body"] == {"enabled": True, "monthly_limit_cents": 25000, "expected_revision": 3,
                                             "note": "Budget voor het vierde kwartaal", "confirmed": True}
    # A key is needed: the answer is the link to the secure form, never a field for the key.
    prepared = tool.run(changes[5][0], ident(ADMIN), env.yes)
    assert prepared["secure_form_url"].startswith("https://cloud.example/") and prepared["link"].startswith("[Open de beveiligde pagina")
    assert set(env.plane.requests[-1]["body"]) == {"provider", "label", "route", "model", "confirmed"}


def test_without_the_approval_interface_a_change_fails_closed(env, monkeypatch):
    monkeypatch.setitem(sys.modules, "tools.approval", None)             # the engine is not there
    assert tool.request_approval("x", "y", "z")["approved"] is False
    got = tool.run({"action": "disable", "connection_id": "conn-1"}, ident(ADMIN))
    assert got["error"] == "not_approved" and not any(r["method"] == "POST" for r in env.plane.requests)


def test_a_secret_is_never_accepted_used_or_repeated(env):
    attempts = [
        {"action": "prepare_connection", "provider": "mistral", "label": "Eigen Mistral", "api_key": FAKE_KEY},
        {"action": "prepare_connection", "provider": "mistral", "label": "Eigen Mistral", "secret": "x"},
        {"action": "prepare_connection", "provider": "mistral", "label": FAKE_KEY},
        {"action": "prepare_connection", "provider": "mistral", "label": "Mijn sleutel is " + FAKE_KEY},
        {"action": "set_limits", "enabled": True, "monthly_limit_cents": None, "expected_revision": 1, "note": "Gebruik Bearer abcdefgh12345678 voor deze omgeving"},
        {"action": "place_in_route", "connection_id": "conn-1", "route": "primary", "model": FAKE_KEY},
        {"action": "test", "connection_id": FAKE_KEY},
        {"action": "prepare_connection", "provider": "mistral", "label": "Eigen Mistral", "token": FAKE_KEY, "password": "x"},
        {"action": "prepare_connection", "provider": "mistral", "label": "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6"},      # one long mixed token
    ]
    for args in attempts:
        got = tool.run(args, ident(ADMIN), env.yes)
        assert got["ok"] is False and got["error"] == "secret_refused", args
        assert got["message"] == tool.SECRET_REFUSED
        assert FAKE_KEY not in json.dumps(got) and "abcdefgh12345678" not in json.dumps(got)
    assert env.plane.requests == [] and env.approvals == []            # nothing sent, and no card that would show the value
    # The handler the engine calls gives the same refusal as text.
    assert json.loads(tool.handle(attempts[0]))["ok"] is False
    # An ordinary name and note pass.
    assert tool.check_arguments({"action": "prepare_connection", "provider": "mistral", "label": "Mistral Finance 2027"})["label"] == "Mistral Finance 2027"
    schema = tool.SCHEMA["parameters"]
    assert schema["additionalProperties"] is False and "confirmed" not in schema["properties"]
    assert not any(re.search(r"(?i)key|secret|token|password", name) for name in schema["properties"])


def test_partners_and_normal_users_are_refused_before_anything_is_sent(env):
    for email in (MEMBER, DEPT_ADMIN, CONSULTANT, "stranger@elsewhere.example", ""):
        for args in ({"action": "overview"}, {"action": "test", "connection_id": "conn-1"}):
            got = tool.run(args, ident(email), env.yes)
            assert got == {"ok": False, "error": "forbidden", "message": tool.NOT_ALLOWED}, (email, args)
        assert tool.eligible(ident(email)) is False
    # An organisation admin without a personal Cloud session: the password session, and a Cloud identity without proof.
    assert tool.run({"action": "overview"}, ident(ADMIN, "local"), env.yes)["error"] == "personal_login_required"
    env.sessions.clear()
    assert tool.run({"action": "overview"}, ident(ADMIN), env.yes)["error"] == "personal_login_required"
    env.sessions["t"] = {"email": ADMIN, "method": "synthpulse_cloud", "exp": time.time() - 5, "_cloud_msp_proof": PROOF}       # expired
    assert tool.run({"action": "overview"}, ident(ADMIN), env.yes)["error"] == "personal_login_required"
    env.sessions["t"] = {"email": MEMBER, "method": "synthpulse_cloud", "exp": time.time() + 600, "_cloud_msp_proof": PROOF}     # somebody else's
    assert tool.run({"action": "overview"}, ident(ADMIN), env.yes)["error"] == "personal_login_required"
    # No turn identity at all (a call outside a chat turn).
    assert tool.run({"action": "overview"})["error"] == "forbidden"
    assert env.plane.requests == [] and env.approvals == []
    # What the control plane refuses stays refused, in its own words.
    env.sessions["t"] = {"email": ADMIN, "method": "synthpulse_cloud", "exp": time.time() + 600, "_cloud_msp_proof": PROOF}
    env.plane.status = 403
    got = tool.run({"action": "overview"}, ident(ADMIN), env.yes)
    assert got["ok"] is False and "eigenaar of beheerder" in got["message"]


def test_the_toolset_is_only_offered_to_who_can_use_the_tool(env, monkeypatch):
    monkeypatch.setattr(tool, "register_tool", lambda: True)
    base = ["file", "web", tool.TOOLSET]                                  # a profile that names the toolset grants nothing by itself
    assert tool.toolsets_for(base, ident(ADMIN)) == ["file", "web", tool.TOOLSET]
    for who in (ident(MEMBER), ident(CONSULTANT), ident(DEPT_ADMIN), ident(ADMIN, "local"), None):
        assert tool.toolsets_for(base, who) == ["file", "web"], who
    from api.capability_risk import TOOLSET_RISKS
    assert tool.TOOLSET in TOOLSET_RISKS
