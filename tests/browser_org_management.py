"""Browser gate for Organisation, Management and value per task or bot.

Boots the real server.py with isolated state: one bot (finbot) with three
scheduled tasks (one with a confirmed value, one failing without a value,
one with only an AI estimate), a run history in the bot's executions.db and
token counts in its state.db. Then drives Chromium as the organisation admin:

1. both navigation items are visible; Organisation shows the empty state;
2. build the structure in "Manage teams": a department, its hourly rate,
   a team with lead and members;
3. the org chart shows the team; unassigned tasks and the bot are placed in
   the team from the chart;
4. the team drawer shows savings, what runs and the people;
5. Management: headline numbers, decisions (failing, missing value,
   unconfirmed), a value filled in inline, an estimate confirmed, prices set
   so the AI cost appears, CSV export;
6. the task detail shows the value card with before, now and measured runs;
7. a bot responsibility gets minutes and shows the weekly saving;
8. narrow layout of Management.

Screenshots land in OM_ARTIFACT_DIR (default: a temp dir, printed at the end).

    python tests/browser_org_management.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_conversation_lifecycle import _terminate_process  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
PASSWORD = "om-e2e-local-only"
ADMIN = "boss@example.com"
LEAD = "lisa@example.com"
MEMBER = "tom@example.com"


def ok(msg):
    print("OK  " + msg, flush=True)


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def seed(home: Path) -> None:
    now = time.time()
    (home / "config.yaml").write_text(
        "model:\n  default: om-fake\n  provider: custom\n  base_url: http://127.0.0.1:9\n  api_key: x\n"
        "toolsets: []\nmcp_servers: {}\nmemory:\n  memory_enabled: false\n  user_profile_enabled: false\n",
        encoding="utf-8")
    bot = home / "profiles" / "finbot"
    (bot / "cron").mkdir(parents=True)
    (bot / "config.yaml").write_text((home / "config.yaml").read_text(), encoding="utf-8")
    (bot / "SOUL.md").write_text("Finance bot.\n", encoding="utf-8")
    (bot / "profile.yaml").write_text(
        "ui_meta:\n  hermes-bots:\n    title: Finance Bot\n    kind: bot\n    role: Debiteuren\n    color: '#0b7a75'\n"
        "    responsibilities:\n    - title: Aanmaningen opstellen\n      objective: Concept-aanmaningen voor facturen ouder dan 30 dagen\n"
        "      trigger: maandag 08:00\n      autonomy: ask\n      reporting: ''\n"
        "_ui_meta_revisions:\n  hermes-bots: 1\n", encoding="utf-8")
    base = {"prompt": "p", "owner_email": MEMBER, "enabled": True, "deliver": "local",
            "schedule": {"kind": "cron", "expr": "0 8 * * 1", "display": "0 8 * * 1"},
            "schedule_display": "Mondays 08:00", "origin": {"platform": "webui", "user_id": MEMBER},
            "created_at": _iso(now - 40 * 86400), "next_run_at": _iso(now + 86400), "last_run_at": _iso(now - 3500),
            "last_error": None, "last_delivery_error": None, "skills": [], "skill": None, "model": None,
            "provider": None, "base_url": None, "script": None, "no_agent": False, "context_from": None,
            "repeat": {"times": None, "completed": 0}, "state": "scheduled", "paused_at": None, "paused_reason": None}
    jobs = [
        dict(base, id="j1", name="Debiteurenlijst", last_status="ok",
             value={"task": "Debiteurenlijst samenstellen", "before_minutes": 45, "review_minutes": 5,
                    "source": "owner", "confidence": "confirmed"}),
        dict(base, id="j2", name="Bankmutaties boeken", last_status="error", failure_streak=4),
        dict(base, id="j3", name="Weekrapport cashflow", last_status="ok",
             value={"before_minutes": 60, "review_minutes": 10, "source": "ai_estimate", "confidence": "estimated",
                    "rationale": "Elke week handmatig bankoverzicht en openstaande posten"}),
    ]
    (bot / "cron" / "jobs.json").write_text(json.dumps({"jobs": jobs}), encoding="utf-8")
    conn = sqlite3.connect(bot / "cron" / "executions.db")
    conn.execute("CREATE TABLE executions (id TEXT PRIMARY KEY, job_id TEXT NOT NULL, source TEXT NOT NULL, process_id TEXT NOT NULL, "
                 "pid INTEGER NOT NULL, process_started_at INTEGER, status TEXT NOT NULL, claimed_at TEXT NOT NULL, started_at TEXT, "
                 "finished_at TEXT, error TEXT)")
    rows = []
    for i in range(6):
        t0 = now - (i + 1) * 86400
        rows.append((f"a{i}", "j1", "s", "p", 1, None, "completed", _iso(t0), _iso(t0), _iso(t0 + 90), None))
        rows.append((f"c{i}", "j3", "s", "p", 1, None, "completed", _iso(t0 + 600), _iso(t0 + 600), _iso(t0 + 700), None))
        rows.append((f"b{i}", "j2", "s", "p", 1, None, "failed", _iso(t0 + 300), _iso(t0 + 300), _iso(t0 + 310), "boom"))
    conn.executemany("INSERT INTO executions VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    conn = sqlite3.connect(bot / "state.db")
    conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT, user_id TEXT, model TEXT, started_at REAL, ended_at REAL, "
                 "last_activity_at REAL, message_count INT, input_tokens INT, output_tokens INT, cache_read_tokens INT, "
                 "cache_write_tokens INT, estimated_cost_usd REAL, actual_cost_usd REAL, cost_status TEXT, title TEXT)")
    srows = []
    for i in range(6):
        t0 = now - (i + 1) * 86400
        srows.append((f"cron{i}", "cron", "", "synthwave-auto", t0 + 5, t0 + 80, t0 + 80, 3, 120000, 9000, 50000, 0, 0, None, "unknown",
                      f"Debiteurenlijst · run {i}"))
    srows.append(("chat1", "webui", MEMBER, "synthwave-auto", now - 7200, None, now - 7000, 8, 60000, 6000, 0, 0, 0, None, "unknown",
                  "Aanmaning klant X"))
    conn.executemany("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", srows)
    conn.commit()
    conn.close()


def start_server(env, art):
    import socket
    import subprocess
    import urllib.request
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(env, HERMES_WEBUI_PORT=str(port))
    log = (art / "server.log").open("w", encoding="utf-8")
    engine_py = Path(env["HERMES_WEBUI_AGENT_DIR"]) / "venv" / "bin" / "python"
    proc = subprocess.Popen([str(engine_py), str(REPO / "scripts" / "with_agent_runtime.py"), str(REPO / "server.py")],
                            cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 60
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            with urllib.request.urlopen(base + "/health", timeout=2) as r:
                if r.status == 200:
                    return proc, log, base
        except OSError:
            pass
        time.sleep(0.3)
    raise RuntimeError("server did not start; see " + str(art / "server.log"))


def main() -> int:
    from playwright.sync_api import sync_playwright

    state_tmp = tempfile.TemporaryDirectory(prefix="om-gate-")
    state = Path(state_tmp.name)
    art = Path(os.environ.get("OM_ARTIFACT_DIR") or tempfile.mkdtemp(prefix="om-artifacts-"))
    art.mkdir(parents=True, exist_ok=True)
    home = state / "hermes-home"
    home.mkdir()
    (state / "workspace").mkdir()
    seed(home)
    policy = state / "governance.yaml"
    policy.write_text(
        "version: 1\nmode: report_only\ndefault_effect: deny\n"
        f"bootstrap_admins:\n- {ADMIN}\ninstallation:\n  kind: hq\n"
        f"users:\n  {LEAD}:\n    roles: []\n  {MEMBER}:\n    roles: []\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    for key in ("API_SERVER_KEY", "HERMES_WEBUI_PASSWORD", "HERMES_WEBUI_EXTENSION_DIR", "HERMES_WEBUI_EXTENSION_MANIFEST",
                "HERMES_WEBUI_CHAT_BACKEND", "PYTHONPATH", "HERMES_WEBUI_GOVERNANCE_POLICY"):
        env.pop(key, None)
    env.update({
        "HERMES_WEBUI_HOST": "127.0.0.1",
        "HERMES_WEBUI_STATE_DIR": str(state / "webui-state"),
        "HERMES_HOME": str(home), "HERMES_BASE_HOME": str(home), "HERMES_CONFIG_PATH": str(home / "config.yaml"),
        "HERMES_WEBUI_SKIP_ONBOARDING": "1",
        "HERMES_WEBUI_AGENT_DIR": str(Path(os.environ.get("HERMES_WEBUI_AGENT_DIR") or Path.home() / ".hermes/hermes-agent")),
        "HERMES_WEBUI_DEFAULT_WORKSPACE": str(state / "workspace"),
        "HERMES_WEBUI_GOVERNANCE_POLICY": str(policy),
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
        "HERMES_WEBUI_PASSWORD": PASSWORD,
        "HERMES_WEBUI_PASSWORD_IDENTITY": ADMIN,
        "SP_VALUE_COLLECT_INTERVAL": "0",
    })
    proc = log = None
    page = None
    console_errors = []
    code = 1
    try:
        proc, log, base_url = start_server(env, art)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(base_url=base_url, viewport={"width": 1440, "height": 960}, accept_downloads=True,
                                      locale="nl-NL")
            resp = ctx.request.post("/api/auth/login", data={"password": PASSWORD})
            assert resp.ok, f"login failed: {resp.status} {resp.text()[:200]}"
            me = ctx.request.get("/api/org/structure/me").json()
            assert me.get("scope") == "all", me
            page = ctx.new_page()
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: console_errors.append("pageerror: " + str(e)))
            page.goto("/", wait_until="domcontentloaded")
            page.wait_for_selector("#msg", state="visible", timeout=20000)
            page.wait_for_function("() => typeof S !== 'undefined' && S._bootReady !== false", timeout=30000)

            # 1. nav and empty state
            page.wait_for_selector('.rail [data-panel="organisation"]:not([hidden])', timeout=10000)
            assert page.locator('.rail [data-panel="management"]').is_visible()
            ok("navigation shows Organisatie and Management for the organisation admin")
            page.locator('.rail [data-panel="organisation"]').click()
            page.wait_for_selector("#mainOrganisation .om-empty", timeout=10000)
            assert "nog niet ingericht" in page.locator("#mainOrganisation .om-empty").inner_text()
            page.screenshot(path=str(art / "01-org-empty.png"))
            ok("Organisatie shows the empty state with two ways to start")

            # 2. build the structure
            page.locator('#mainOrganisation .om-empty [data-om-view="manage"]').click()
            page.locator('[data-om-dept-form] input[name=name]').fill("Finance")
            page.locator('[data-om-dept-form] button[type=submit]').click()
            page.wait_for_selector('.om-dept-block h3:text("Finance")', timeout=10000)
            rate = page.locator('[data-om-dept-rate="finance"]')
            rate.fill("60")
            rate.dispatch_event("change")
            page.wait_for_timeout(600)
            page.locator('.om-dept-block details summary').first.click()
            form = page.locator('.om-dept-block details [data-om-team-form]').first
            form.locator('input[name=name]').fill("Debiteuren")
            page.evaluate("""([lead, members]) => {
                const f = document.querySelector('.om-dept-block details [data-om-team-form]');
                f.querySelector('input[name=lead]').value = lead;
                f.querySelector('input[name=members]').value = members;
            }""", [LEAD, f"{LEAD},{MEMBER}"])
            form.locator('button[type=submit]').click()
            page.wait_for_function("() => document.querySelectorAll('[data-om-team-form][data-key=\"finance/debiteuren\"]').length === 1", timeout=10000)
            structure = ctx.request.get("/api/org/structure").json()
            team = structure["teams"]["finance/debiteuren"]
            assert team["lead"] == LEAD and set(team["members"]) == {LEAD, MEMBER}, team
            assert structure["departments"]["finance"]["hourly_rate"] == 60
            page.screenshot(path=str(art / "02-manage-teams.png"))
            ok("department with hourly rate and a team with lead and members saved through the UI")

            # 3. chart and placing unassigned work
            page.locator('[data-om-view="chart"]').click()
            page.wait_for_selector('.om-team-card[data-om-team="finance/debiteuren"]', timeout=10000)
            # j1/j2/j3 belong to MEMBER, who is now in the team: they follow the owner's team.
            card_text = page.locator('.om-team-card[data-om-team="finance/debiteuren"]').inner_text()
            assert "3" in card_text, card_text
            sel = page.locator('.om-unassigned [data-bot="finbot"] select[data-om-assign-bot]')
            sel.select_option("finance/debiteuren")
            page.wait_for_function("() => !document.querySelector('.om-unassigned [data-bot=\"finbot\"]')", timeout=10000)
            page.wait_for_function("() => (document.querySelector('.om-team-card[data-om-team=\"finance/debiteuren\"]')||{}).innerText?.includes('Finance Bot')", timeout=10000)
            page.screenshot(path=str(art / "03-org-chart.png"))
            ok("org chart shows the team with its tasks; the bot is placed in the team from the chart")

            # 4. drawer
            page.locator('.om-team-card[data-om-team="finance/debiteuren"]').click()
            page.wait_for_selector(".om-drawer", timeout=5000)
            drawer = page.locator(".om-drawer").inner_text()
            assert "Debiteurenlijst" in drawer and "Finance Bot" in drawer and MEMBER in drawer, drawer
            assert "Bankmutaties boeken" in drawer and "wacht op actie" in drawer.lower(), drawer
            page.screenshot(path=str(art / "04-team-drawer.png"))
            ok("team drawer shows savings, what needs action, what runs and the people")

            # 5. Management
            page.locator('.rail [data-panel="management"]').click()
            page.wait_for_selector("#mainManagement .om-kpis", timeout=15000)
            kpis = page.locator("#mainManagement .om-kpis").inner_text()
            # j1: 6 runs x 40 min + j3: 6 runs x 50 min = 540 min = 9 h
            assert "9 u" in kpis, kpis
            dec = page.locator("#mainManagement .om-decisions").inner_text()
            assert "Taken die herhaald falen" in dec and "Taken zonder waarde" in dec and "Schattingen niet bevestigd" in dec, dec
            page.screenshot(path=str(art / "05-management.png"), full_page=True)
            ok("Management shows measured hours and the decisions that need attention")

            missing = page.locator('.om-decision:has-text("Taken zonder waarde")')
            missing.locator("summary").click()
            row = missing.locator('[data-job="j2"]')
            row.locator('input[name=before]').fill("30")
            row.locator('input[name=now]').fill("5")
            row.locator('button[type=submit]').click()
            page.wait_for_function("() => !document.querySelector('.om-decision') || ![...document.querySelectorAll('.om-decision')].some(d => d.innerText.includes('Taken zonder waarde'))", timeout=10000)
            ok("a missing value is filled in inline and the decision disappears")

            unconf = page.locator('.om-decision:has-text("Schattingen niet bevestigd")')
            unconf.locator("summary").click()
            unconf.locator('[data-job="j3"] [data-om-confirm="yes"]').click()
            page.wait_for_function("() => ![...document.querySelectorAll('.om-decision')].some(d => d.innerText.includes('Schattingen niet bevestigd'))", timeout=10000)
            ok("an AI estimate is confirmed with one click")

            page.locator('#mainManagement [data-om-settings]').first.click()
            page.wait_for_selector("[data-om-pricing]", timeout=5000)
            prow = page.locator("[data-om-price-row]").first
            prow.locator("input[name=model]").fill("synthwave-auto")
            prow.locator("input[name=in]").fill("3")
            prow.locator("input[name=out]").fill("15")
            prow.locator("input[name=cache]").fill("0.3")
            page.locator("[data-om-pricing] button[type=submit]").click()
            page.wait_for_function("() => /API-equivalent/.test(document.querySelector('#mainManagement .om-kpis')?.innerText || '')", timeout=10000)
            kpis = page.locator("#mainManagement .om-kpis").inner_text()
            assert "Rendement" in kpis and "×" in kpis, kpis
            team_row = page.locator('tr[data-om-team-row="finance/debiteuren"]').inner_text()
            assert "€" in team_row, team_row
            page.screenshot(path=str(art / "06-management-priced.png"), full_page=True)
            ok("prices set: AI cost, net value and return appear")

            with page.expect_download() as dl:
                page.locator("[data-om-export]").click()
            csv_text = Path(dl.value.path()).read_text(encoding="utf-8-sig")
            assert "Debiteuren" in csv_text and "saved_hours" in csv_text, csv_text[:200]
            ok("CSV export contains the team rows")

            # 6. task detail value card
            top = page.locator('#mainManagement .om-section:has-text("Meeste waarde") [data-job="j1"] [data-om-open-job]')
            top.click()
            page.wait_for_selector("#omValueCard .om-value-figures", timeout=15000)
            card = page.locator("#omValueCard").inner_text()
            assert "45" in card and "40" in card and "geslaagde runs" in card and "bevestigd" in card.lower(), card
            page.locator("#omValueCard").screenshot(path=str(art / "07-task-value-card.png"))
            ok("task detail shows the value card: before, now, saving per run and measured runs")

            # 6b. a new task from the form carries its value
            created = ctx.request.post("/api/crons/create", data={
                "prompt": "Stel de crediteurenlijst op", "schedule": "0 9 * * 2", "name": "Crediteurenlijst",
                "deliver": "local", "enabled": False,
                "value": {"before_minutes": 35, "review_minutes": 5, "task": "Crediteurenlijst", "source": "owner",
                          "confidence": "confirmed"}})
            assert created.ok, created.text()[:300]
            job = created.json()["job"]
            assert job["value"]["before_minutes"] == 35 and job["value"]["confirmed_by"] == ADMIN, job.get("value")
            bad = ctx.request.post("/api/crons/create", data={"prompt": "x", "schedule": "0 9 * * 2",
                                                              "value": {"task": "geen minuten"}})
            assert bad.status == 400, bad.status
            ok("a new task created through the API carries its value; a value without minutes is refused")

            # 7. bot responsibility minutes
            page.evaluate("async () => { await switchPanel('profiles'); openProfileDetail('finbot'); }")
            page.wait_for_selector("#botDutiesCard .bot-duty", timeout=15000)
            page.locator("#botDutiesCard .bot-duty button").first.click()
            page.locator("#botDutyMinBefore").fill("30")
            page.locator("#botDutyMinNow").fill("5")
            page.locator("#botDutyTimes").fill("10")
            page.locator("#botDutyForm .sm-btn.primary").click()
            page.wait_for_selector("#botDutiesCard .bot-duty-value", timeout=10000)
            chip = page.locator("#botDutiesCard .bot-duty-value").inner_text()
            assert "4,2" in chip, chip  # (30 - 5) x 10 = 250 min
            assert page.locator("#botServesSelect").input_value() == "finance/debiteuren"
            page.locator("#botDutiesCard").screenshot(path=str(art / "08-bot-duty-value.png"))
            ok("bot responsibility with minutes shows the weekly saving; the bot's team is shown in its editor")

            overview = ctx.request.get("/api/management/overview?period=28").json()
            bot = next(b for b in overview["bots"] if b["name"] == "finbot")
            assert bot["estimate_minutes_per_week"] == 250 and bot["chats"] == 1, bot

            # 8. narrow layout
            page.set_viewport_size({"width": 390, "height": 844})
            page.evaluate("async () => { await switchPanel('management'); }")
            page.wait_for_selector("#mainManagement .om-kpis", timeout=10000)
            page.screenshot(path=str(art / "09-management-mobile.png"), full_page=True)
            overflow = page.evaluate("() => document.querySelector('#mainManagement .om-wrap').scrollWidth - document.querySelector('#mainManagement .om-wrap').clientWidth")
            assert overflow <= 2, f"horizontal overflow {overflow}px"
            ok("narrow layout without horizontal overflow")

            ours = [e for e in console_errors if "orgmgmt" in e or "om-" in e or "SPValue" in e or "SPOrg" in e]
            assert not ours, ours
            ok("no console errors from the new screens")
            browser.close()
        code = 0
    except Exception as exc:
        print("FAIL " + str(exc), flush=True)
        if page is not None:
            try:
                page.screenshot(path=str(art / "failure.png"), full_page=True)
            except Exception:
                pass
        print("console errors:", console_errors[-10:])
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
