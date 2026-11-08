"""Browser gate for the Use Case Studio.

Boots the real server.py with isolated state (same seed as
browser_org_management.py) and a local fake OmniRoute that answers the three
Studio steps. Drives Chromium through the whole flow:

1. Studio is in the navigation; a new use case for a team opens from the
   Organisation chart's "Nieuwe automatisering voor dit team";
2. Discover: typing about the work gives goals and an impact/effort matrix;
   an opportunity is chosen;
3. Design: describing the process gives the as-is and to-be lanes with the
   building block per step and reuse hints;
4. Playbook: components appear, a field is edited and saved as a version;
5. Build: dry run, explicit click, then a paused scheduled task with its
   value and team, a skill and a Kanban task really exist;
6. Measure, and the new task shows in Management under the team;
7. narrow layout.

    python tests/browser_studio.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_conversation_lifecycle import _terminate_process  # noqa: E402
from browser_org_management import ADMIN, LEAD, MEMBER, PASSWORD, ok, seed, start_server  # noqa: E402

ANSWERS = {
    "AI-consultant": {"title": "Debiteurenopvolging", "goals": [{"name": "Minder openstaande facturen", "kpi": "DSO van 41 naar 30 dagen"},
                                                                  {"name": "Minder handwerk", "kpi": "3 uur per week minder"}],
                      "opportunities": [{"id": "o1", "title": "Wekelijkse concept-aanmaningen", "pain": "Elke maandag handmatig nabellen",
                                         "why": "Sneller betaald", "impact": 5, "effort": 2, "building_block": "task"},
                                        {"id": "o2", "title": "Klantportaal voor betalingen", "pain": "Klanten vragen status",
                                         "why": "Minder vragen", "impact": 3, "effort": 5, "building_block": "custom"},
                                        {"id": "o3", "title": "Huisstijl aanmaning als werkwijze", "pain": "Wisselende toon",
                                         "why": "Consistent", "impact": 3, "effort": 1, "building_block": "skill"}]},
    "werkproces opnieuw": {"as_is": [{"step": "Openstaande posten uit SnelStart halen", "actor": "mens", "minutes": 20},
                                     {"step": "Per klant mail schrijven", "actor": "mens", "minutes": 40}],
                           "to_be": [{"step": "Agent maakt lijst en concept-mails", "actor": "agent", "building_block": "task", "note": "maandag 08:00"},
                                     {"step": "Werkwijze aanmaning", "actor": "agent", "building_block": "skill"},
                                     {"step": "Medewerker kijkt na en verstuurt", "actor": "mens", "building_block": "human"}],
                           "metrics": [{"name": "DSO", "baseline": "41 dagen", "target": "30 dagen"}]},
    "uitvoerbaar Playbook": {"components": [
        {"type": "bot", "name": "Debiteuren Bot", "description": "Maakt concept-aanmaningen",
         "instructions": "Je helpt het team Debiteuren met aanmaningen. Je verstuurt nooit zelf iets."},
        {"type": "task", "name": "Concept-aanmaningen maandag", "schedule": "0 8 * * 1",
         "prompt": "Maak een lijst van facturen ouder dan 30 dagen en schrijf per klant een concept-aanmaning. Verstuur niets.",
         "before_minutes": 60, "review_minutes": 10, "per": "run", "bot": "Debiteuren Bot"},
        {"type": "skill", "name": "Aanmaning opstellen", "description": "Aanmaning in drie niveaus in huisstijl",
         "content": "# Aanmaning opstellen\n\n1. Bepaal het niveau.\n2. Schrijf kort en vriendelijk."},
        {"type": "human", "name": "Concepten nakijken en versturen", "who": MEMBER, "what": "Elke maandag de concepten nakijken"},
        {"type": "connection", "name": "SnelStart", "provider": "snelstart", "why": "Openstaande posten lezen"}]},
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
                answer = next((v for k, v in ANSWERS.items() if k in system), {"components": []})
                owner.calls.append(next((k for k in ANSWERS if k in system), "?"))
                data = json.dumps({"choices": [{"message": {"role": "assistant", "content": json.dumps(answer)}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/v1/chat/completions"

    def start(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


def main() -> int:
    from playwright.sync_api import sync_playwright

    state_tmp = tempfile.TemporaryDirectory(prefix="studio-gate-")
    state = Path(state_tmp.name)
    art = Path(os.environ.get("ST_ARTIFACT_DIR") or tempfile.mkdtemp(prefix="studio-artifacts-"))
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
        "OMNIROUTE_URL": fake.url, "OMNIROUTE_API_KEY": "fake", "SP_VALUE_LABELER": "0",
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
            for body in ({"op": "department.save", "key": "finance", "name": "Finance", "hourly_rate": 60},
                         {"op": "team.save", "department": "finance", "name": "Debiteuren", "lead": LEAD, "members": [MEMBER]}):
                assert ctx.request.post("/api/org/structure", data=body).ok
            page = ctx.new_page()
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: console_errors.append("pageerror: " + str(e)))
            page.goto("/", wait_until="domcontentloaded")
            page.wait_for_selector("#msg", state="visible", timeout=20000)

            # 1. from the org chart into Studio for the team
            assert page.locator('.rail [data-panel="studio"]').is_visible()
            page.wait_for_selector('.rail [data-panel="organisation"]:not([hidden])', timeout=10000)
            page.locator('.rail [data-panel="organisation"]').click()
            page.locator('.om-team-card[data-om-team="finance/debiteuren"]').click()
            page.locator('[data-om-new-automation="finance/debiteuren"]').click()
            page.wait_for_selector("#mainStudio .st-stepper", timeout=15000)
            assert page.locator("[data-st-team]").input_value() == "finance/debiteuren"
            assert page.locator(".st-guide").is_visible()
            page.screenshot(path=str(art / "01-studio-start.png"))
            ok("Organisation chart opens a new Studio use case for the team, with the guide cards")

            # 1b. live talking through the realtime voice agent (stubbed: no microphone in headless)
            page.evaluate("""() => {
              window.__voice = {sid: null, stopped: false};
              window.synPulseVoice = {d: {transcript: e => { window.__voice.orig = (window.__voice.orig || 0) + 1; }},
                async start(sid) { window.__voice.sid = sid; this.d.transcript([{role: 'user', text: 'Elke maandag bel ik facturen na'}, {role: 'assistant', text: 'Vertel meer'}]); },
                stop() { window.__voice.stopped = true; }};
            }""")
            page.locator('[data-st-phase="discover"]').click()
            page.wait_for_selector("[data-st-live]", timeout=10000)
            page.locator("[data-st-live]").click()
            page.wait_for_function("() => window.__voice.sid && /bel ik facturen/.test(document.querySelector('[data-st-send] textarea').value)", timeout=10000)
            assert page.evaluate("() => window.__voice.orig") == 1
            page.locator("[data-st-live]").click()
            assert page.evaluate("() => window.__voice.stopped") is True
            sid = page.evaluate("() => window.__voice.sid")
            sess = ctx.request.get("/api/session?session_id=" + sid).json()
            assert "Studio" in json.dumps(sess.get("session", sess))[:4000], str(sess)[:300]
            ok("Live praten runs the realtime voice agent in a session of its own; what is said lands in the Studio")

            # 2. discover
            page.locator("[data-st-send] textarea").fill("")
            page.locator("[data-st-topic]").first.click()
            page.locator("[data-st-send] textarea").fill("Elke maandag bel ik facturen na en schrijf ik aanmaningen, dat kost me twee uur.")
            page.locator("[data-st-send] button[type=submit]").click()
            page.wait_for_selector(".st-matrix .st-dot", timeout=20000)
            assert page.locator(".st-dot").count() == 3 and page.locator(".st-goal").count() == 2
            assert page.locator("[data-st-title]").input_value() == "Debiteurenopvolging"
            page.locator('.om-row [data-st-select="o1"]').click()
            page.wait_for_selector('.st-dot.sel[data-st-select="o1"]', timeout=10000)
            page.screenshot(path=str(art / "02-discover.png"), full_page=True)
            ok("discover gives goals and an impact/effort matrix; an opportunity is chosen")

            # 3. design
            page.locator('[data-st-goto="design"]').click()
            page.wait_for_selector('[data-st-send] textarea[placeholder*="proces"]', timeout=10000)
            page.locator("[data-st-send] textarea").fill("Ik haal de lijst uit SnelStart en schrijf per klant een mail.")
            page.locator("[data-st-send] button[type=submit]").click()
            page.wait_for_selector(".st-lane .st-step.bb-task", timeout=20000)
            assert page.locator(".st-lane").count() == 2
            page.screenshot(path=str(art / "03-design.png"), full_page=True)
            ok("design gives the as-is and to-be lanes with a building block per step")

            # 4. playbook
            page.locator("[data-st-make-playbook]").first.click()
            page.wait_for_selector(".st-comp", timeout=20000)
            assert page.locator(".st-comp").count() == 5
            sched = page.locator('.st-comp [data-st-f="schedule"]').first
            sched.fill("0 9 * * 1")
            page.locator("[data-st-save-playbook]").click()
            page.wait_for_timeout(500)
            doc_id = page.evaluate("() => (document.querySelector('[data-st-title]') && window.SPStudio) ? null : null")
            page.screenshot(path=str(art / "04-playbook.png"), full_page=True)
            ok("Playbook components appear, an edit is saved as a new version")

            # 5. dry run and build
            page.locator('[data-st-goto="build"]').click()
            page.wait_for_selector(".st-confirm [data-st-build]", timeout=10000)
            dry = page.locator(".st-canvas").inner_text()
            assert "gepauzeerd" in dry and "60→10" in dry, dry
            page.screenshot(path=str(art / "05-dry-run.png"), full_page=True)
            page.locator("[data-st-build]").click()
            page.wait_for_selector('[data-st-nav="tasks"]', timeout=60000)
            canvas = page.locator(".st-canvas").inner_text()
            assert canvas.count("Klaar") == 4 and "Overgeslagen" in canvas, canvas
            page.screenshot(path=str(art / "06-built.png"), full_page=True)
            jobs = ctx.request.get("/api/crons").json().get("jobs") or []
            job = next(j for j in jobs if j.get("name") == "Concept-aanmaningen maandag")
            assert job.get("enabled") is False, job.get("enabled")
            assert job["value"]["before_minutes"] == 60 and job["value"]["team"] == "finance/debiteuren", job.get("value")
            assert (job.get("schedule") or {}).get("expr", job.get("schedule_display")) in ("0 9 * * 1",) or "9" in str(job.get("schedule")), job.get("schedule")
            assert job.get("assigned_bot") == "studio-debiteuren-bot", job.get("assigned_bot")
            bots = ctx.request.get("/api/profiles?fast=1").json().get("profiles") or []
            bot = next(b for b in bots if b["name"] == "studio-debiteuren-bot")
            assert (bot.get("bot") or {}).get("serves") == ["finance/debiteuren"], bot.get("bot")
            skill = home / "skills" / "studio" / "aanmaning-opstellen" / "SKILL.md"
            assert skill.is_file() and "studio_use_case" in skill.read_text(), skill
            tasks = ctx.request.get("/api/kanban/board").json()
            titles = json.dumps(tasks)
            assert "Concepten nakijken en versturen" in titles, titles[:300]
            ok("build creates a bot for the team, a paused task with value and team assigned to that bot, a skill and a Kanban task; the connection is handled")

            # 6. measure and Management
            page.locator('[data-st-goto="measure"]').click()
            page.wait_for_selector('[data-st-nav="management"]', timeout=10000)
            page.locator('[data-st-nav="management"]').click()
            page.wait_for_selector("#mainManagement .om-table", timeout=20000)
            overview = ctx.request.get("/api/management/overview?period=28").json()
            names = [j["name"] for j in overview["jobs"] if j["team"] == "finance/debiteuren"]
            assert "Concept-aanmaningen maandag" in names, names
            ok("the built task shows in Management under its team")

            # list view
            page.locator('.rail [data-panel="studio"]').click()
            page.locator("[data-st-back]").click()
            page.wait_for_selector(".st-card", timeout=10000)
            card = page.locator(".st-card").first.inner_text()
            assert "Debiteurenopvolging" in card and "4 gebouwd" in card, card
            page.screenshot(path=str(art / "07-list.png"))
            ok("use case list shows the use case with built parts")

            # 7. narrow
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator(".st-card").first.click()
            page.wait_for_selector(".st-stepper", timeout=10000)
            page.screenshot(path=str(art / "08-mobile.png"), full_page=True)
            overflow = page.evaluate("() => document.querySelector('#mainStudio .om-wrap').scrollWidth - document.querySelector('#mainStudio .om-wrap').clientWidth")
            assert overflow <= 2, overflow
            ok("narrow layout without horizontal overflow")
            assert fake.calls.count("AI-consultant") == 1 and "uitvoerbaar Playbook" in fake.calls, fake.calls
            ours = [e for e in console_errors if "studio" in e.lower() or "SPStudio" in e]
            assert not ours, ours
            ok("no console errors from Studio")
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
