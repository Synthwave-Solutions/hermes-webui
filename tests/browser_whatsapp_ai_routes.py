"""Browser gate for WhatsApp in the Super Agent and the chat tool for the AI model routes.

Boots the real server.py with isolated state, an enforcing policy, a fake
control plane on localhost (sign-in handoff and the signed AI routes), and a
fake model that answers by calling the ``ai_routes`` tool. The WhatsApp guard
of the stack is not part of the WebUI: Chromium answers /_synthpulse/whatsapp
itself, the way the guard would. Drives the screens as two people:

1. WhatsApp koppelen (organisation admin): status and business number, a code
   is requested and shown large with the instruction and the time left, the
   phone sends the code and the masked number appears, unlink;
2. WhatsApp van de afdeling: status, settings, the pairing window, linked
   people with revoke, recent refused messages; every POST carries the header
   the guard asks for;
3. a team member sees the personal block only; a guard that reports "not
   active" disables the request; a missing module hides everything;
4. AI routes in chat (organisation admin in a personal Cloud session): the
   overview as a compact card; a change shows the approval card with only
   "once" and "deny", nothing is sent before the approval and the call then
   carries ``confirmed: true`` and the personal session; a refusal sends
   nothing; a key is needed: the link to the secure page; a pasted key is
   refused and never reaches the control plane;
5. a team member is not offered the tool and nothing is sent;
6. narrow layout.

Set CHROMIUM_PATH to use a Chromium that Playwright did not install itself.

    python tests/browser_whatsapp_ai_routes.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_conversation_lifecycle import _terminate_process  # noqa: E402
from browser_org_management import ADMIN, MEMBER, PASSWORD, ok, start_server  # noqa: E402

KEY_ID = "0a1b2c3d4e5f6071"
SECRET_HEX = "5f" * 16 + "a0" * 16
PREFIX = "/v1/customer/ai-routes"
JOB = "job_" + "ab" * 16
PASTED = "sk-proj-" + "Zx9Qw7Er5Ty3Ui1Op" * 2          # a made up value in the shape of a provider key
GUARD = re.compile(r".*/_synthpulse/whatsapp/.*")
GRANTS = {"permissions": ["chat:use", "sessions:read", "sessions:write", "profiles:read", "skills:read", "config:read", "model:read",
                          "files:read", "integrations:read"],
          "routes": ["/api/*"], "profiles": ["default"], "models": {"providers": ["*"], "models": ["*"]},
          "tools": {"toolsets": ["*"], "builtins": ["*"]}, "workspaces": ["*"]}


class FakeControlPlane:
    """The sign-in handoff and the signed AI routes of the control plane."""

    def __init__(self):
        self.requests, self.codes, self.enabled = [], {}, True
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _handle(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                fake.requests.append({"method": self.command, "path": self.path, "body": body,
                                      "session": bool(self.headers.get("X-SP-Cloud-Session")), "acting": self.headers.get("X-SP-Acting-User")})
                status, payload = 404, {"detail": "Onbekende klantfunctie."}
                rest = self.path[len(PREFIX):] if self.path.startswith(PREFIX) else None
                if self.command == "POST" and self.path == "/v1/cloud-session" and (body or {}).get("code") in fake.codes:
                    status, payload = 200, {"email": fake.codes[body["code"]], "proof": "ab" * 32}
                elif self.command == "GET" and self.path == "/v1/customer/assignments":
                    status, payload = 200, {"assignments": []}
                elif self.command == "POST" and self.path == "/v1/customer/studio/summary":
                    status, payload = 200, {"ok": True}
                elif rest == "" and self.command == "GET":
                    status, payload = 200, {
                        "mode": "router", "stale": False, "checked_at": int(time.time()),
                        "active_route": [{"position": 1, "model": "regolo/model-a", "provider": "regolo", "provider_label": "Regolo", "available": True, "billing": "prepaid_ledger"},
                                         {"position": 2, "model": "mistral/model-b", "provider": "mistral", "provider_label": "Mistral", "available": fake.enabled, "billing": "customer_own_key"}],
                        "connections": [{"id": "conn-1", "provider": "mistral", "provider_label": "Mistral", "label": "Eigen Mistral", "owner": "customer",
                                         "enabled": fake.enabled, "status": "active", "billing": "customer_own_key", "editable": True}],
                        "billing": {"notice": "Gebruik op een eigen sleutel rekent de aanbieder met jullie af."},
                        "providers": [{"id": "mistral", "label": "Mistral", "region": "EU"}], "jobs": [],
                        "secure_form_url": "https://cloud.example/synthpulse-cloud/ai-routes?environment=sp_voorbeeld"}
                elif rest is not None and self.command == "POST" and (body or {}).get("confirmed") is not True:
                    status, payload = 422, {"detail": "Een wijziging vraagt je bevestiging."}
                elif rest == "/connection-requests" and self.command == "POST":
                    status, payload = 200, {"request_id": "cr_" + "1" * 24,
                                            "secure_form_url": "https://cloud.example/synthpulse-cloud/ai-routes?environment=sp_voorbeeld&request=cr_" + "1" * 24}
                elif rest == "/connections/conn-1/disable" and self.command == "POST":
                    fake.enabled = False
                    status, payload = 200, {"id": JOB, "action": "ai_routes_connection_enable", "status": "queued", "stage": "queued"}
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

    def code_for(self, email):
        code = hashlib.sha256(email.encode()).hexdigest()
        self.codes[code] = email
        return code

    def changes(self):
        return [r for r in self.requests if r["method"] == "POST" and r["path"].startswith(PREFIX)]


class FakeModel:
    """An OpenAI-compatible model that answers questions about the AI routes by calling the tool.

    The engine offers the tool through its tool bridge (``tool_call`` with a
    name and arguments). A person who is not offered the tool gets the
    engine's own "not a known tool".
    """

    def __init__(self):
        self.results = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def _json(self, payload):
                data = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._json({"object": "list", "data": [{"id": "gate-fake", "object": "model", "context_length": 128000}]})

            def _chunk(self, delta=None, finish=None):
                payload = {"id": "gate", "object": "chat.completion.chunk", "created": 0, "model": "gate-fake",
                           "choices": [{"index": 0, "delta": delta or {}, "finish_reason": finish}]}
                self.wfile.write(b"data: " + json.dumps(payload).encode() + b"\n\n")
                self.wfile.flush()

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                messages = body.get("messages") or []

                def text(content):
                    if isinstance(content, str):
                        return content
                    return " ".join(str(p.get("text", "")) for p in content if isinstance(p, dict)) if isinstance(content, list) else ""

                tools = [t.get("function", {}).get("name") for t in body.get("tools") or []]
                users = [text(m.get("content")) for m in messages if m.get("role") == "user"]
                last = re.sub(r"<memory-context>[\s\S]*?</memory-context>", "", users[-1] if users else "").lower()
                tail = messages[-1] if messages else {}
                call = reply = None
                if "tool_call" in tools and tail.get("role") == "tool":
                    raw = text(tail.get("content"))
                    owner.results.append(raw)
                    try:
                        result = json.loads(raw)
                    except ValueError:
                        result = {}
                    result = result if isinstance(result, dict) else {}
                    if result.get("card"):
                        reply = "Dit is de route van deze omgeving.\n\n" + result["card"] + "\n\nDe terugval loopt via jullie eigen sleutel."
                    elif result.get("link"):
                        reply = "De verbinding is voorbereid. " + result["link"]
                    elif result.get("ok"):
                        reply = "De wijziging is aangevraagd."
                    else:
                        reply = "Niet uitgevoerd. " + str(result.get("message") or result.get("error") or "")
                elif "tool_call" in tools and users:
                    if "sk-" in last:
                        # A careless model passes the pasted key on as the name of the connection.
                        call = {"action": "prepare_connection", "provider": "mistral", "label": "Sleutel " + re.search(r"sk-[A-Za-z0-9_-]+", users[-1]).group(0)}
                    elif "overzicht" in last:
                        call = {"action": "overview"}
                    elif "zet" in last and "uit" in last:
                        call = {"action": "disable", "connection_id": "conn-1"}
                    elif "eigen sleutel" in last:
                        call = {"action": "prepare_connection", "provider": "mistral", "label": "Mistral Finance", "route": "fallback", "model": "mistral/model-b"}
                if call is None and reply is None:
                    reply = "Titel"
                function = {"name": "tool_call", "arguments": json.dumps({"name": "ai_routes", "arguments": call})} if call else None
                if not body.get("stream"):
                    message = {"role": "assistant", "content": reply or ""}
                    if function:
                        message["tool_calls"] = [{"id": "call_1", "type": "function", "function": function}]
                    self._json({"id": "gate", "object": "chat.completion", "created": 0, "model": "gate-fake",
                                "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if function else "stop"}],
                                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    self._chunk({"role": "assistant", "content": ""})
                    if function:
                        self._chunk({"tool_calls": [{"index": 0, "id": "call_%d" % len(owner.results), "type": "function", "function": function}]})
                        self._chunk({}, "tool_calls")
                    else:
                        for start in range(0, len(reply), 160):
                            self._chunk({"content": reply[start:start + 160]})
                        self._chunk({}, "stop")
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                    self.close_connection = True
                except (BrokenPipeError, ConnectionResetError):
                    return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = "http://127.0.0.1:%d/v1" % self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


class FakeGuard:
    """The API of the WhatsApp guard, answered inside the browser."""

    def __init__(self, installed=True, active=True):
        self.installed, self.enabled, self.posts, self.pending = installed, active, [], {}
        self.unknown_reply = "Dit nummer is niet gekoppeld aan een account."
        self.links = [{"link_id": "wl_" + "a1" * 12, "email": "lisa@example.com", "name": "Lisa", "number": "+31•••••4410",
                       "department": "finance", "verified_at": int(time.time()) - 9 * 86400}]
        self.events = [{"ts": "2026-11-20T10:00:00+00:00", "event": "link_verified", "actor": "lisa@example.com"},
                       {"ts": "2026-11-21T09:00:00+00:00", "event": "refused_unknown", "number": "+31•••••0931"},
                       {"ts": "2026-11-21T11:00:00+00:00", "event": "refused_group"}]

    def phone_sends_code(self, email):
        self.pending.pop(email, None)
        self.links.append({"link_id": "wl_" + "c3" * 12, "email": email, "name": "Boss", "number": "+31•••••5678",
                           "department": "finance", "verified_at": int(time.time())})

    def status(self):
        return {"installed": True, "enabled": self.enabled, "key_set": True, "business_number": "+31201234567", "department": "finance",
                "department_name": "Finance", "unknown_reply": self.unknown_reply, "dry_run": False, "connection": "ready", "governance": "enforce",
                "pairing_open_until": None, "webhook_registered_at": int(time.time()) - 86400, "last_message_at": int(time.time()) - 600,
                "last_refused_at": int(time.time()) - 300, "linked_people": len(self.links), "links": self.links}

    def handler(self, email, admin):
        def handle(route):
            request = route.request
            path = re.sub(r"^.*?/_synthpulse/whatsapp", "", request.url.split("?")[0])

            def out(status, payload):
                route.fulfill(status=status, content_type="application/json", body=json.dumps(payload))

            if not self.installed:
                return out(404, {"detail": "Niet gevonden."})
            if request.method == "POST":
                self.posts.append((path, request.headers.get("x-synthpulse-whatsapp")))
                if request.headers.get("x-synthpulse-whatsapp") != "1":
                    return out(403, {"detail": "Ongeldige aanvraag."})
            body = json.loads(request.post_data or "{}") if request.method == "POST" else {}
            if path == "/api/me":
                return out(200, {"active": self.enabled, "business_number": "+31201234567", "department_name": "Finance",
                                 "links": [l for l in self.links if l["email"] == email], "pending": None, "is_admin": admin})
            if path == "/api/me/link":
                if not self.enabled:
                    return out(409, {"detail": "WhatsApp is voor deze afdeling nog niet actief."})
                return out(200, {"code": "4827 1593", "expires_at": int(time.time()) + 600, "send_to": "+31201234567",
                                 "instruction": "Stuur deze code vanaf je eigen WhatsApp naar het zakelijke nummer."})
            if path == "/api/me/unlink":
                self.links = [l for l in self.links if l["email"] != email]
                return out(200, {"removed": 1})
            if not admin:
                return out(403, {"detail": "Alleen voor beheerders."})
            if path == "/api/status":
                return out(200, self.status())
            if path == "/api/audit":
                return out(200, {"events": self.events})
            if path == "/api/settings":
                self.enabled = body.get("enabled", self.enabled)
                self.unknown_reply = body.get("unknown_reply", self.unknown_reply)
                return out(200, self.status())
            if path == "/api/pairing":
                return out(200, {"expires_at": int(time.time()) + 900, "page": "/_synthpulse/whatsapp/pairing"})
            match = re.fullmatch(r"/api/links/(wl_[a-f0-9]{24})/revoke", path)
            if match:
                self.links = [l for l in self.links if l["link_id"] != match.group(1)]
                return out(200, {"revoked": {"link_id": match.group(1)}})
            return out(404, {"detail": "Niet gevonden."})
        return handle


def main() -> int:
    from playwright.sync_api import sync_playwright

    state_tmp = tempfile.TemporaryDirectory(prefix="wa-routes-gate-")
    state = Path(state_tmp.name)
    art = Path(os.environ.get("ST_ARTIFACT_DIR") or tempfile.mkdtemp(prefix="wa-routes-artifacts-"))
    art.mkdir(parents=True, exist_ok=True)
    home = state / "hermes-home"
    home.mkdir()
    (state / "workspace").mkdir()
    plane, model = FakeControlPlane(), FakeModel()
    (home / "config.yaml").write_text(
        "model:\n  default: gate-fake\n  provider: custom\n" f"  base_url: {model.base_url}\n" "  api_key: gate-local-only\n"
        "custom_providers:\n- name: Fake\n" f"  base_url: {model.base_url}\n" "  api_key: gate-local-only\n  models:\n  - gate-fake\n"
        "toolsets: []\nwebui_map_geocoder: \"off\"\nmcp_servers: {}\nmemory:\n  memory_enabled: false\n  user_profile_enabled: false\n",
        encoding="utf-8")
    codes = {email: plane.code_for(email) for email in (ADMIN, MEMBER)}
    key = state / "control.key"
    key.write_text(f"{KEY_ID}:{SECRET_HEX}\n", encoding="utf-8")
    key.chmod(0o600)
    policy = state / "governance.yaml"
    policy.write_text(json.dumps({          # JSON is YAML
        "version": 1, "mode": "enforce", "default_effect": "deny", "bootstrap_admins": [ADMIN], "installation": {"kind": "hq"},
        "roles": {"member": {"grants": dict(GRANTS, files={"read_roots": [str(state / "workspace")], "write_roots": [str(state / "workspace")]})}},
        "users": {MEMBER: {"roles": ["member"]}}}), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    for name in ("API_SERVER_KEY", "HERMES_WEBUI_PASSWORD", "PYTHONPATH", "HERMES_WEBUI_GOVERNANCE_POLICY", "SP_INTAKE_OFFER", "SP_CONTROL_SOCKET",
                 "HERMES_WEBUI_EXTENSION_DIR", "HERMES_WEBUI_EXTENSION_MANIFEST", "HERMES_WEBUI_CHAT_BACKEND"):
        env.pop(name, None)
    env.update({
        "HERMES_WEBUI_HOST": "127.0.0.1", "HERMES_WEBUI_STATE_DIR": str(state / "webui-state"),
        "HERMES_HOME": str(home), "HERMES_BASE_HOME": str(home), "HERMES_CONFIG_PATH": str(home / "config.yaml"),
        "HERMES_WEBUI_SKIP_ONBOARDING": "1",
        "HERMES_WEBUI_AGENT_DIR": str(Path(os.environ.get("HERMES_WEBUI_AGENT_DIR") or Path.home() / ".hermes/hermes-agent")),
        "HERMES_WEBUI_DEFAULT_WORKSPACE": str(state / "workspace"), "HERMES_WEBUI_GOVERNANCE_POLICY": str(policy),
        "HERMES_WEBUI_PASSWORD": PASSWORD, "HERMES_WEBUI_PASSWORD_IDENTITY": ADMIN, "HERMES_WEBUI_PREWARM": "0",
        "SP_VALUE_LABELER": "0", "SP_CONTROL_URL": plane.url, "SP_CONTROL_KEY_FILE": str(key), "SP_CLOUD_PERSONAL_MSP": "1",
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
    })
    proc = log = page = None
    console_errors = []
    code = 1
    try:
        proc, log, base_url = start_server(env, art)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, executable_path=os.environ.get("CHROMIUM_PATH") or None,
                                         args=["--no-sandbox", "--disable-dev-shm-usage"])

            def sign_in(email, guard, admin, width=1440, height=1000):
                """A person who arrives through the personal Cloud handoff, with the guard answered in the browser."""
                ctx = browser.new_context(base_url=base_url, viewport={"width": width, "height": height}, locale="nl-NL")
                resp = ctx.request.post("/api/auth/cloud-session", data={"code": codes[email]},
                                        headers={"Origin": "https://" + base_url.split("//", 1)[1], "X-SynthPulse-Login": "1"})
                assert resp.ok, (email, resp.status, resp.text()[:200])
                ctx.route(GUARD, guard.handler(email, admin))
                tab = ctx.new_page()
                tab.on("pageerror", lambda e: console_errors.append("pageerror: " + str(e)))
                tab.on("dialog", lambda d: d.accept())
                tab.goto("/", wait_until="commit")
                tab.wait_for_function("() => typeof switchPanel === 'function' && typeof _currentPanel === 'string'", timeout=30000)
                return ctx, tab

            def channels(tab):
                tab.evaluate("async () => { await switchPanel('integrations'); await switchIntegrationTab('channels'); }")

            guard = FakeGuard()
            ctx, page = sign_in(ADMIN, guard, True)

            # 1. WhatsApp koppelen
            channels(page)
            page.wait_for_selector("#intgWhatsApp [data-wa-request]", timeout=20000)
            mine = page.locator("#intgWhatsApp").inner_text()
            assert "WhatsApp koppelen" in mine and "Actief" in mine and "+31201234567" in mine and "Je hebt nog geen nummer gekoppeld." in mine, mine
            page.locator("#intgWhatsApp [data-wa-request]").click()
            page.wait_for_selector("#intgWhatsApp [data-wa-code-value]", timeout=10000)
            code_box = page.locator("[data-wa-code]").inner_text()
            assert "4827 1593" in code_box and "eigen WhatsApp" in code_box and "+31201234567" in code_box, code_box
            assert page.evaluate("() => parseFloat(getComputedStyle(document.querySelector('[data-wa-code-value]')).fontSize)") >= 34
            first = page.locator("[data-wa-left]").inner_text()
            assert re.fullmatch(r"Nog \d{1,2}:\d\d geldig", first), first
            page.wait_for_function("(t) => document.querySelector('[data-wa-left]').textContent !== t", arg=first, timeout=5000)
            assert page.locator(".wa-open").get_attribute("href") == "https://wa.me/31201234567?text=48271593"
            page.screenshot(path=str(art / "01-whatsapp-code.png"))
            guard.phone_sends_code(ADMIN)
            page.wait_for_selector("#intgWhatsApp [data-wa-link]", timeout=15000)
            linked = page.locator("#intgWhatsApp .wa-links").inner_text()
            assert "+31•••••5678" in linked and "Ontkoppelen" in linked and page.locator("[data-wa-code]").count() == 0, linked
            ok("WhatsApp koppelen: status, a large code with instruction and countdown, the masked number once the phone sent it")

            # 2. WhatsApp van de afdeling
            page.wait_for_selector('#intgWhatsAppAdmin [data-wa-row="wl_' + "c3" * 12 + '"]', timeout=15000)
            admin = page.locator("#intgWhatsAppAdmin").inner_text()
            for part in ("WhatsApp van de afdeling", "Verbonden", "handhaven", "ingesteld", "Lisa", "+31•••••4410", "Recent geweigerd", "Onbekend nummer", "Groep of kanaal"):
                assert part in admin, part
            assert page.locator("[data-wa-refused] tbody tr").count() == 2          # the link event is not a refusal
            page.locator("[data-wa-pairing]").click()
            page.wait_for_selector("[data-wa-pairing-page]", timeout=10000)
            assert page.locator("[data-wa-pairing-page]").get_attribute("href") == "/_synthpulse/whatsapp/pairing"
            page.locator("[data-wa-settings] textarea").fill("Vraag je beheerder om toegang.")
            page.locator('[data-wa-settings] button[type="submit"]').click()
            page.wait_for_function("() => document.querySelector('[data-wa-settings] textarea').value === 'Vraag je beheerder om toegang.'", timeout=10000)
            assert guard.unknown_reply == "Vraag je beheerder om toegang."
            page.locator('[data-wa-revoke="wl_' + "a1" * 12 + '"]').click()
            page.wait_for_function("() => !document.querySelector('[data-wa-row=\"wl_" + "a1" * 12 + "\"]')", timeout=10000)
            page.screenshot(path=str(art / "02-whatsapp-admin.png"))
            page.locator("#intgWhatsApp [data-wa-unlink]").click()
            page.wait_for_selector("#intgWhatsApp [data-wa-none]", timeout=10000)
            assert [p for p, _h in guard.posts] == ["/api/me/link", "/api/pairing", "/api/settings", "/api/links/wl_" + "a1" * 12 + "/revoke", "/api/me/unlink"]
            assert all(header == "1" for _p, header in guard.posts)
            ok("WhatsApp van de afdeling: status, settings, pairing window, revoke and recent refusals; every POST carries the guard's header")

            # 3. a team member, a guard that is not active, a module that is not installed
            m_ctx, m_page = sign_in(MEMBER, guard, False)
            channels(m_page)
            m_page.wait_for_selector("#intgWhatsApp [data-wa-request]", timeout=20000)
            assert not m_page.locator("#intgWhatsAppAdmin").is_visible()
            m_ctx.close()
            i_ctx, i_page = sign_in(MEMBER, FakeGuard(active=False), False)
            channels(i_page)
            i_page.wait_for_selector("#intgWhatsApp [data-wa-request]", timeout=20000)
            assert i_page.locator("#intgWhatsApp [data-wa-request]").is_disabled() and "Nog niet actief" in i_page.locator("#intgWhatsApp").inner_text()
            i_ctx.close()
            n_ctx, n_page = sign_in(ADMIN, FakeGuard(installed=False), True)
            channels(n_page)
            n_page.wait_for_timeout(2500)
            assert not n_page.locator("#intgWhatsApp").is_visible() and not n_page.locator("#intgWhatsAppAdmin").is_visible()
            n_ctx.close()
            ok("a team member sees the personal block only, 'not active' disables the request, a missing module hides everything")

            # 4. AI routes in chat
            def say(tab, text):
                # The previous turn has settled (the chat re-renders it once more), else the message would queue behind it.
                tab.wait_for_function("() => !document.querySelector('#liveAssistantTurn')", timeout=60000)
                tab.wait_for_timeout(2000)
                tab.locator("#msg").fill(text)
                tab.locator("#btnSend").click()

            page.evaluate("async () => { await switchPanel('chat'); if (typeof newSession === 'function') await newSession(false); }")
            page.wait_for_selector("#msg", state="visible", timeout=20000)
            say(page, "Geef een overzicht van de AI-routes")
            page.wait_for_function("() => /De terugval loopt via jullie eigen sleutel/.test(document.body.innerText)", timeout=90000)
            overview = json.loads(model.results[-1])
            assert overview["ok"] and overview["card"].startswith("```table") and overview["connections"][0]["label"] == "Eigen Mistral"
            page.wait_for_function("() => /AI-routes van deze omgeving/.test(document.body.innerText)", timeout=20000)
            assert plane.changes() == []
            page.screenshot(path=str(art / "03-ai-routes-card.png"))
            ok("the overview of the AI routes shows as a compact card")
            say(page, "Zet de verbinding Eigen Mistral uit")
            page.wait_for_selector("#approvalCard:not([hidden])", timeout=90000)
            card = page.locator("#approvalCard").inner_text()
            assert '"Eigen Mistral" (conn-1)' in card and "uitzetten" in card, card
            assert page.locator("#approvalBtnOnce").is_visible() and page.locator("#approvalBtnDeny").is_visible()
            assert not page.locator("#approvalBtnSession").is_visible() and not page.locator("#approvalBtnAlways").is_visible()
            assert plane.changes() == [], "a change was sent before the approval"
            page.screenshot(path=str(art / "04-ai-routes-approval.png"))
            page.locator("#approvalBtnOnce").click()
            page.wait_for_function("() => /De wijziging is aangevraagd/.test(document.body.innerText)", timeout=90000)
            sent = plane.changes()
            assert len(sent) == 1 and sent[0]["path"] == PREFIX + "/connections/conn-1/disable", sent
            assert sent[0]["body"]["confirmed"] is True and sent[0]["session"] is True and sent[0]["acting"] == ADMIN
            say(page, "Zet de verbinding Eigen Mistral nog een keer uit")
            page.wait_for_selector("#approvalCard:not([hidden])", timeout=90000)
            page.locator("#approvalBtnDeny").click()
            page.wait_for_function("() => /Niet uitgevoerd/.test(document.body.innerText)", timeout=90000)
            assert len(plane.changes()) == 1, "a refused change was sent"
            say(page, "Bereid een eigen sleutel voor Mistral voor")
            page.wait_for_selector("#approvalCard:not([hidden])", timeout=90000)
            assert "beveiligde pagina" in page.locator("#approvalCard").inner_text()
            page.locator("#approvalBtnOnce").click()
            page.wait_for_function("() => /De verbinding is voorbereid/.test(document.body.innerText)", timeout=90000)
            link = page.locator('a[href^="https://cloud.example/synthpulse-cloud/ai-routes"]').last.get_attribute("href")
            assert link.endswith("request=cr_" + "1" * 24), link
            assert set(plane.changes()[-1]["body"]) == {"provider", "label", "route", "model", "confirmed"}
            before = len(plane.requests)
            say(page, "Gebruik deze sleutel: " + PASTED)
            page.wait_for_function("() => /Een sleutel hoort niet in de chat/.test(document.body.innerText)", timeout=90000)
            assert json.loads(model.results[-1])["error"] == "secret_refused" and PASTED not in model.results[-1]
            assert len(plane.requests) == before and page.locator("#approvalCard:not([hidden])").count() == 0
            assert "sk-proj" not in json.dumps([r["body"] for r in plane.requests])
            page.screenshot(path=str(art / "05-ai-routes-key-refused.png"))
            ok("a change waits for the approval card and then carries confirmed and the personal session; a refusal sends nothing; "
               "a key gets the secure link and a pasted key never reaches the control plane")

            # 5. a team member is not offered the tool
            t_ctx, t_page = sign_in(MEMBER, guard, False)
            t_page.evaluate("async () => { await switchPanel('chat'); if (typeof newSession === 'function') await newSession(false); }")
            t_page.wait_for_selector("#msg", state="visible", timeout=20000)
            before = len(plane.requests)
            say(t_page, "Geef een overzicht van de AI-routes")
            t_page.wait_for_function("() => /Niet uitgevoerd/.test(document.body.innerText)", timeout=90000)
            assert "not available in this session" in model.results[-1] or "not a known tool" in model.results[-1], model.results[-1]
            assert not any(r["path"].startswith(PREFIX) for r in plane.requests[before:])
            t_ctx.close()
            ok("a team member is not offered the tool and nothing is sent")

            # 6. narrow
            ctx.close()
            p_ctx, p_page = sign_in(ADMIN, FakeGuard(), True, width=390, height=844)
            channels(p_page)
            p_page.wait_for_selector("#intgWhatsAppAdmin [data-wa-row]", timeout=20000)
            p_page.locator("#intgWhatsApp [data-wa-request]").click()
            p_page.wait_for_selector("#intgWhatsApp [data-wa-code-value]", timeout=10000)
            dims = p_page.evaluate("""() => { const box = s => Math.round(document.querySelector(s).getBoundingClientRect().right);
              return [document.documentElement.scrollWidth, window.innerWidth, box('[data-wa-code]'), box('#intgWhatsAppAdmin [data-wa-revoke]')]; }""")
            assert dims[0] <= dims[1] + 1 and dims[2] <= dims[1] and dims[3] <= dims[1], dims
            p_page.screenshot(path=str(art / "06-narrow.png"))
            p_ctx.close()
            ok("narrow layout: the code and the revoke button fit, the page does not scroll sideways")

            assert not console_errors, console_errors
            ok("no page errors")
            browser.close()
        code = 0
    except Exception as exc:
        print("FAIL " + str(exc)[:1500], flush=True)
        if page is not None:
            try:
                page.screenshot(path=str(art / "failure.png"), full_page=True)
            except Exception:
                pass
        print("console errors:", console_errors[-8:])
        print("last tool result:", (model.results[-1] if model.results else "")[:400], "| changes:", [r["path"] for r in plane.changes()])
    finally:
        if proc is not None:
            _terminate_process(proc)
        if log is not None:
            log.close()
        for fake in (plane, model):
            fake.server.shutdown()
            fake.server.server_close()
        print("artifacts:", art)
        state_tmp.cleanup()
    return code


if __name__ == "__main__":
    sys.exit(main())
