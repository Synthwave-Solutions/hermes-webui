"""Browser gate for the personal intake as a conversation.

Boots the real server.py with isolated state (same seed as
browser_org_management.py), the automatic offer switched on and a local fake
OmniRoute. Drives Chromium through the whole flow:

1. first sign-in: the introduction opens by itself; "later" closes it and it
   is not offered a second time;
2. opened again on request: one question at a time, chips, a skipped question,
   tasks pulled from a described week and an answer that is changed afterwards;
3. saving writes the same intake as the Studio form plus what the person wants
   off their plate, and the agent proposes first tasks;
4. choosing a card puts the request ready in the chat without sending it;
5. the cards stay on the empty chat until the person hides them;
6. narrow layout, and the entry from the Studio form.

    python tests/browser_intake_chat.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_conversation_lifecycle import _terminate_process  # noqa: E402
from browser_org_management import ADMIN, PASSWORD, ok, seed, start_server  # noqa: E402

ANSWERS = {
    "terugkerende werk in kaart": {"tasks": [
        {"name": "Openstaande posten nabellen", "cadence": "weekly", "minutes": 120, "tools": ["Exact"]},
        {"name": "Weekrapport debiteuren maken", "cadence": "weekly", "minutes": 45, "tools": ["Excel"]}]},
    "drie eerste taken": {"intro": "Gebaseerd op je weekrapport, het nabellen en je mail.",
                          "tasks": [{"kind": "now", "title": "Maak een concept van het weekrapport debiteuren"},
                                    {"kind": "ongoing", "title": "Zet elke maandag de openstaande posten uit Exact klaar"},
                                    {"kind": "ongoing", "title": "Vat elke ochtend mijn nieuwe mail voor me samen"}]},
}


class FakeOmniRoute:
    def __init__(self):
        self.calls = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                system = (body.get("messages") or [{}])[0].get("content", "")
                key = next((k for k in ANSWERS if k in system), "?")
                owner.calls.append(key)
                data = json.dumps({"choices": [{"message": {"role": "assistant", "content": json.dumps(ANSWERS.get(key, {}))}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v1/chat/completions"

    def start(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


def ready(page):
    """The app has booted; the start screen is not always the chat."""
    page.wait_for_function("() => typeof switchPanel === 'function' && typeof _currentPanel === 'string' && !!document.getElementById('msg')", timeout=20000)


def main() -> int:
    from playwright.sync_api import sync_playwright

    state_tmp = tempfile.TemporaryDirectory(prefix="intake-chat-gate-")
    state = Path(state_tmp.name)
    art = Path(os.environ.get("ST_ARTIFACT_DIR") or tempfile.mkdtemp(prefix="intake-chat-artifacts-"))
    art.mkdir(parents=True, exist_ok=True)
    home = state / "hermes-home"
    home.mkdir()
    (state / "workspace").mkdir()
    seed(home)
    fake = FakeOmniRoute()
    fake.start()
    policy = state / "governance.yaml"
    policy.write_text(f"version: 1\nmode: report_only\ndefault_effect: deny\nbootstrap_admins:\n- {ADMIN}\ninstallation:\n  kind: hq\n",
                      encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    for key in ("API_SERVER_KEY", "HERMES_WEBUI_PASSWORD", "PYTHONPATH", "HERMES_WEBUI_GOVERNANCE_POLICY"):
        env.pop(key, None)
    env.update({
        "HERMES_WEBUI_HOST": "127.0.0.1", "HERMES_WEBUI_STATE_DIR": str(state / "webui-state"),
        "HERMES_HOME": str(home), "HERMES_BASE_HOME": str(home), "HERMES_CONFIG_PATH": str(home / "config.yaml"),
        "HERMES_WEBUI_SKIP_ONBOARDING": "1",
        "HERMES_WEBUI_AGENT_DIR": str(Path(os.environ.get("HERMES_WEBUI_AGENT_DIR") or Path.home() / ".hermes/hermes-agent")),
        "HERMES_WEBUI_DEFAULT_WORKSPACE": str(state / "workspace"), "HERMES_WEBUI_GOVERNANCE_POLICY": str(policy),
        "HERMES_WEBUI_PASSWORD": PASSWORD, "HERMES_WEBUI_PASSWORD_IDENTITY": ADMIN, "HERMES_WEBUI_PREWARM": "0",
        "OMNIROUTE_URL": fake.url, "OMNIROUTE_API_KEY": "fake", "SP_VALUE_LABELER": "0", "SP_INTAKE_OFFER": "1",
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
    })
    proc = log = page = None
    console_errors = []
    code = 1
    try:
        proc, log, base_url = start_server(env, art)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(base_url=base_url, viewport={"width": 1440, "height": 960}, locale="nl-NL")
            assert ctx.request.post("/api/auth/login", data={"password": PASSWORD}).ok
            page = ctx.new_page()
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: console_errors.append("pageerror: " + str(e)))
            page.goto("/", wait_until="domcontentloaded")
            ready(page)

            # 1. offered once at first sign-in
            page.wait_for_selector(".ic-overlay [data-ic-start]", timeout=15000)
            assert page.locator(".ic-agent").count() == 3 and "Super Agent" in page.locator(".ic-agent").first.inner_text()
            page.screenshot(path=str(art / "01-welcome.png"))
            page.keyboard.press("Escape")
            page.wait_for_selector(".ic-overlay", state="detached", timeout=5000)
            me = ctx.request.get("/api/studio/profile?who=me").json()
            assert me["onboarding"]["dismissed_at"] and me["offer_intake"] is False and not me.get("updated_at"), me
            page.reload(wait_until="domcontentloaded")
            ready(page)
            page.wait_for_timeout(2500)
            assert not page.locator(".ic-overlay").count()
            ok("the introduction opens by itself at first sign-in; 'later' closes it and it is not offered again")

            # 2. on request: the questions, one at a time
            page.evaluate("() => window.SPIntakeChat.open()")
            page.locator(".ic-overlay [data-ic-start]").click()
            page.wait_for_selector("[data-ic-input]", timeout=5000)
            assert page.locator(".ic-progress i").count() == 8 and page.locator(".ic-progress i.now").count() == 1
            page.locator("[data-ic-input]").fill("Debiteurenbeheerder")
            page.keyboard.press("Enter")
            page.wait_for_selector('[data-ic-chip="mail"]', timeout=5000)
            assert page.locator(".ic-me .ic-bubble").first.inner_text() == "Debiteurenbeheerder"
            page.locator('[data-ic-chip="mail"]').click()
            page.locator('[data-ic-chip="recurring"]').click()
            assert page.locator('[data-ic-chip="mail"]').get_attribute("aria-pressed") == "true"
            page.locator("[data-ic-other]").fill("Declaraties indienen")
            page.locator("[data-ic-form] button[type=submit]").click()
            page.wait_for_selector("textarea[data-ic-input]", timeout=5000)
            page.locator("textarea[data-ic-input]").fill("Elke maandag bel ik openstaande posten na en maak ik het weekrapport in Excel.")
            page.keyboard.press("Enter")
            page.wait_for_function("() => /Ik haal hier deze taken uit: Openstaande posten nabellen, Weekrapport debiteuren maken/.test(document.querySelector('.ic-log').innerText)", timeout=15000)
            page.wait_for_selector('[data-ic-chip="Exact"]', timeout=5000)
            page.locator('[data-ic-chip="Exact"]').click()
            page.locator("[data-ic-other]").fill("Twinfield")
            page.locator("[data-ic-form] button[type=submit]").click()
            page.wait_for_selector('[data-ic-chip="informal"]', timeout=5000)
            page.locator('[data-ic-chip="informal"]').click()
            page.wait_for_selector('[data-ic-chip="short"]', timeout=5000)
            page.screenshot(path=str(art / "02-questions.png"))
            # change an earlier answer: it asks that question again and then continues where it was
            page.locator('[data-ic-edit="0"]').click()
            page.wait_for_selector("input[data-ic-input]", timeout=5000)
            assert page.locator("input[data-ic-input]").input_value() == "Debiteurenbeheerder"
            page.locator("input[data-ic-input]").fill("Teamlead debiteuren")
            page.keyboard.press("Enter")
            page.wait_for_selector('[data-ic-chip="short"]', timeout=5000)
            assert page.locator(".ic-me .ic-bubble").first.inner_text() == "Teamlead debiteuren"
            page.locator("[data-ic-skip]").click()
            page.wait_for_selector('[data-ic-chip="n_send"]', timeout=5000)
            assert "Overgeslagen" in page.locator(".ic-log").inner_text()
            page.locator('[data-ic-chip="n_send"]').click()
            page.locator("[data-ic-form] button[type=submit]").click()
            page.wait_for_selector('[data-ic-chip="regular"]', timeout=5000)
            page.locator('[data-ic-chip="regular"]').click()
            ok("one question at a time with chips, a skipped question, tasks pulled from a described week and a changed answer")

            # 3. saved like the Studio form, plus first tasks
            page.wait_for_selector(".ic-overlay .ic-card", timeout=20000)
            text = page.locator(".ic-log").inner_text()
            assert "Dit onthoud ik over je" in text and "Rol: Teamlead debiteuren" in text and "Gebaseerd op je weekrapport" in text, text[-900:]
            assert page.locator(".ic-overlay .ic-card").count() == 6, page.locator(".ic-overlay .ic-card").count()
            assert page.locator(".ic-overlay .ic-badge-now").count() == 1 and page.locator(".ic-overlay .ic-badge-mail").count() == 1
            me = ctx.request.get("/api/studio/profile?who=me").json()
            assert me["role"]["title"] == "Teamlead debiteuren" and me["wishes"] == ["mail", "recurring"] and me["wish_other"] == "Declaraties indienen", me
            assert [t["name"] for t in me["tasks"]] == ["Openstaande posten nabellen", "Weekrapport debiteuren maken"], me["tasks"]
            assert "Exact" in me["tools"] and "Twinfield" in me["tools"] and me["prefs"]["tone"] == "informal" and me["prefs"]["length"] == ""
            assert me["prefs"]["never"] == "Mails of berichten versturen" and me["literacy"]["self"] == "regular" and me["prefs"]["language"] == "nl"
            assert "Wil als eerste uit handen geven: mail en chat bijhouden; terugkerende taken overnemen; Declaraties indienen." in me["note"], me["note"]
            assert me["first_tasks"]["personal"] is True and len(me["first_tasks"]["tasks"]) == 3
            assert fake.calls == ["terugkerende werk in kaart", "drie eerste taken"], fake.calls
            page.wait_for_timeout(900)
            page.screenshot(path=str(art / "03-first-tasks.png"))
            ok("saving writes the intake and what the person wants off their plate; the agent proposes first tasks")

            # 4. a card puts the request ready in the chat, nothing is sent
            page.locator(".ic-overlay .ic-card").first.click()
            page.wait_for_selector(".ic-overlay", state="detached", timeout=5000)
            page.wait_for_function("() => document.getElementById('msg').value === 'Maak een concept van het weekrapport debiteuren'", timeout=10000)
            assert page.evaluate("() => _currentPanel") == "chat"
            assert page.evaluate("() => (S.messages || []).length") == 0
            ok("choosing a card puts the request ready in the chat without sending it")

            # 5. the cards stay on the empty chat until hidden
            page.reload(wait_until="domcontentloaded")
            ready(page)
            page.evaluate("async () => { await switchPanel('chat'); }")
            page.wait_for_selector("#emptyState .ic-starters .ic-card", timeout=15000)
            assert page.locator("#emptyState .ic-starters .ic-card").count() == 3 and not page.locator(".ic-overlay").count()
            page.evaluate("() => { const b = document.getElementById('msg'); b.value = ''; b.dispatchEvent(new Event('input', {bubbles: true})); }")
            page.locator("#emptyState .ic-starters .ic-card").nth(1).click()
            assert page.locator("#msg").input_value() == "Zet elke maandag de openstaande posten uit Exact klaar"
            page.screenshot(path=str(art / "04-empty-chat.png"))
            page.locator("#emptyState [data-ic-hide]").click()
            assert not page.locator(".ic-starters").count()
            page.reload(wait_until="domcontentloaded")
            ready(page)
            page.wait_for_timeout(2500)
            assert not page.locator(".ic-starters").count() and not page.locator(".ic-overlay").count()
            ok("the first tasks stay on the empty chat until the person hides them")

            # 6. narrow, and the entry from Studio
            page.set_viewport_size({"width": 390, "height": 844})
            page.evaluate("() => window.SPIntakeChat.open()")
            page.locator(".ic-overlay [data-ic-start]").click()
            page.wait_for_selector("input[data-ic-input]", timeout=5000)
            assert page.locator("input[data-ic-input]").input_value() == "Teamlead debiteuren", "a second round starts from what is saved"
            overflow = page.evaluate("() => document.querySelector('.ic-panel').scrollWidth - document.querySelector('.ic-panel').clientWidth")
            assert overflow <= 2, overflow
            page.screenshot(path=str(art / "05-mobile.png"))
            page.locator(".ic-overlay [data-ic-close]").click()
            page.wait_for_selector(".ic-overlay", state="detached", timeout=5000)
            ok("narrow layout without horizontal overflow; a second round starts from what is saved")
            page.set_viewport_size({"width": 1440, "height": 960})
            page.evaluate("async () => { await switchPanel('studio'); }")
            page.wait_for_selector('#panelStudio [data-st-hub="me"]', state="visible", timeout=10000)
            page.locator('#panelStudio [data-st-hub="me"]').click()
            page.wait_for_selector("#mainStudio [data-intake-chat-open]", timeout=10000)
            page.locator("#mainStudio [data-intake-chat-open]").click()
            page.wait_for_selector(".ic-overlay [data-ic-start]", timeout=5000)
            page.keyboard.press("Escape")
            page.wait_for_selector(".ic-overlay", state="detached", timeout=5000)
            ok("the Studio form offers the same intake as a conversation")
            ours = [e for e in console_errors if "intake" in e.lower() or "SPIntake" in e or "pageerror" in e]
            assert not ours, ours
            ok("no console errors from the intake")
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
    finally:
        if proc is not None:
            _terminate_process(proc)
        if log is not None:
            log.close()
        print("artifacts:", art)
        state_tmp.cleanup()
    return code


if __name__ == "__main__":
    sys.exit(main())
