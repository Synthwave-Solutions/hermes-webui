"""Browser gate for the quickscan roadmap, the assigned partners and the hours of the month.

Boots the real server.py with isolated state (the seed of
browser_org_management.py plus one task that never ran and one skill), an
enforcing policy with a member role and the partner role, and a fake control
plane on localhost that answers the assignments, the hours, the summary and
the sign-in handoff. Drives Chromium as four people:

1. organisation admin: the team block (Agentic Consultant, Agentic Developer)
   and "Uren deze maand" on the overview (monthly hours with extra blocks,
   rows per person, hour cards, "Nog niet bekend", "Bijgewerkt tot");
2. the roadmap is loaded from JSON through the screen; the chart has months,
   weeks, steering stars, dashed foundation bars and the marker for today;
3. a row is linked to a task, a skill and a use case with the pickers: built;
   a completed run appears: the row runs and the roll-up follows; a status
   set by hand that claims more than the evidence gets the mark; the block
   card takes its own link; a linked task opens on that task;
4. the tabs for systems and process diagrams;
5. a consultant is chosen on a use case: badge on the card, name in Voortgang;
6. the consultant (partner role) changes the roadmap and reaches no
   Management, rates or admin route, and files no access request;
7. an address the Cloud does not assign (qa is no longer a resource) gets
   nothing; a team member views the roadmap and cannot change it;
8. narrow layout: the chart scrolls sideways, the page does not;
9. payments and invoices in Support for the organisation admin, with the
   download where a document exists; never for a partner or a team member.

Set CHROMIUM_PATH to use a Chromium that Playwright did not install itself.

    python tests/browser_studio_roadmap.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import threading
import time
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_conversation_lifecycle import _terminate_process  # noqa: E402
from browser_org_management import ADMIN, LEAD, MEMBER, PASSWORD, _iso, hub, ok, seed, start_server  # noqa: E402

CONSULTANT = "carla@partner.example"
DEVELOPER = "daan@partner.example"
QA = "quinn@partner.example"
KEY_ID = "0a1b2c3d4e5f6071"
SECRET_HEX = "5f" * 16 + "a0" * 16

# What a signed-in person of the customer gets here. The partner role carries the same grants: the
# resolver subtracts the admin and money routes from it and caps it at user level.
GRANTS = {"permissions": ["chat:use", "sessions:read", "sessions:write", "profiles:read", "skills:read", "config:read",
                          "model:read", "files:read", "integrations:read", "cron:read"],
          "routes": ["/api/*"], "profiles": ["default"]}

NOW = int(time.time())
HOURS = {"usage_as_of": NOW - 86400, "departments": [
    {"department_id": "dep_1", "name": "Finance", "tier": "t2", "tier_name": "Pakket twee", "term_ends_at": "2027-03-31",
     "roles": [{"role": "consultant", "label": "Consultant", "base_minutes": 720, "increment_minutes": 240, "allocated_minutes": 960,
                "used_minutes": 425, "remaining_minutes": 535, "card_minutes_used": 0, "uncovered_minutes": 0, "late_minutes": 0, "closed": False,
                "people": [{"name": "Carla Jansen", "used_minutes": 305}, {"name": "Noor de Wit", "used_minutes": 120}]},
               {"role": "developer", "label": "Developer", "base_minutes": 600, "increment_minutes": 0, "allocated_minutes": 600,
                "used_minutes": 780, "remaining_minutes": 0, "card_minutes_used": 120, "uncovered_minutes": 60, "late_minutes": 0, "closed": False,
                "people": [{"name": "Daan Visser", "used_minutes": 780}]}],
     "increments": {"consultant": {"count": 2, "minutes": 120, "cents": 90000}},
     "cards": [{"id": "hc_1", "resource": "developer", "label": "Developer", "purchased_minutes": 1200, "used_minutes": 480,
                "remaining_minutes": 720, "starts_at": NOW - 40 * 86400, "expires_at": 1805000000, "status": "active"}],
     "team": [{"role": "consultant", "label": "Consultant", "name": "Carla Jansen", "hours_per_week": 4}]},
    {"department_id": "dep_2", "name": "Sales", "tier": "t1", "tier_name": "Pakket een", "term_ends_at": "2027-01-31",
     "roles": [{"role": "consultant", "label": "Consultant", "base_minutes": 480, "increment_minutes": 0, "allocated_minutes": 480,
                "used_minutes": None, "remaining_minutes": None, "card_minutes_used": None, "uncovered_minutes": None, "people": []}],
     "increments": {}, "cards": [], "team": []}]}

OVERVIEW = {"org": {"name": "Voorbeeld organisatie"}, "permissions": {"billing": True}, "billing_requests": [], "apps": [],
            "support_access": {"can_submit": True, "available_minutes": 0}}
INVOICES = {"title": "Betalingen en facturatie", "currency": "EUR", "invoices_complete": False, "notice": "Nog niet elke betaling heeft hier een factuur.",
            "invoices": [{"id": "br_voorbeeld1", "number": "F-2026-0012", "date": "2026-11-03T09:00:00+00:00", "period": "2026", "status": "paid",
                          "description": "Jaarsupport", "lines": [{"kind": "annual_support", "description": "Jaarsupport", "department": None,
                                                                   "quantity": 1, "amount_ex_vat_cents": 120000}],
                          "amount_ex_vat_cents": 120000, "vat_cents": 25200, "total_cents": 145200, "pdf_available": True},
                         {"id": "br_voorbeeld2", "number": "F-2026-0015", "date": "2026-11-18T09:00:00+00:00", "status": "open",
                          "description": "Strippenkaart 20 uur", "lines": [], "amount_ex_vat_cents": 240000, "vat_cents": 50400,
                          "total_cents": 290400, "pdf_available": False}],
            "payments": [{"id": "tr_1", "date": "2026-11-01T08:00:00+00:00", "period": "2026-11", "service_from": "2026-11-01",
                          "service_until": "2026-12-01", "kind": "subscription", "description": "Pakket twee", "department_name": "Finance",
                          "lines": [{"kind": "package", "description": "Afdelingsabonnement Pakket twee", "department": "Finance", "quantity": 1,
                                     "amount_ex_vat_cents": 500000}],
                          "amount_ex_vat_cents": 500000, "vat_cents": 105000, "total_cents": 605000, "status": "paid", "pdf_available": False}]}
PDF = base64.b64encode(b"%PDF-1.4\n% voorbeeld\n").decode()


def roadmap_doc() -> dict:
    """A made up roadmap of sixteen weeks that started four weeks ago, so today falls inside it."""
    monday = date.today() - timedelta(days=date.today().weekday(), weeks=4)
    return {
        "report_version": "1.2", "title": "Roadmap voorbeeld", "start_date": monday.isoformat(), "weeks": 16, "steering_weeks": [1, 5, 9, 13],
        "planning_note": "Deze planning is indicatief: een voorstel, geen offerte en geen toezegging.",
        "groups": [
            {"id": "start", "name": "Start", "rows": [
                {"id": "kickoff", "name": "Kick-off en verkenning", "kind": "werksessie", "start_week": 1, "weeks": 2}]},
            {"id": "blok1", "name": "Blok 1: debiteuren", "phase": "p1", "rows": [
                {"id": "b1-fundament", "name": "Koppeling en toegang", "kind": "fundament", "start_week": 2, "weeks": 3},
                {"id": "b1-agent", "name": "Aanmaningen voorbereiden", "kind": "agent", "start_week": 4, "weeks": 4}]},
            {"id": "blok2", "name": "Blok 2: offertes", "phase": "p2", "rows": [
                {"id": "b2-fundament", "name": "Sjablonen verzamelen", "kind": "fundament", "start_week": 8, "weeks": 2},
                {"id": "b2-agent", "name": "Offertes opstellen", "kind": "agent", "start_week": 10, "weeks": 4, "status": "in_progress"}]}],
        "safeguarding": {"name": "Borging en overdracht", "start_week": 14, "weeks": 3},
        "phases": [
            {"id": "p1", "name": "Debiteuren", "summary": "Aanmaningen als concept.", "steps": ["Lijst ophalen", "Concepten maken", "Nakijken"],
             "ready_when": "Elke maandag liggen de concepten klaar."},
            {"id": "p2", "name": "Offertes", "ready_when": "Een offerte staat binnen een dag klaar."}],
        "systems": [{"name": "Boekhouding", "status": "te_valideren", "note": "Export bevestigen"}, {"name": "CRM", "status": "bevestigd"}],
        "diagrams": [{"id": "d1", "title": "Aanmaning", "phase": "p1",
                      "source": "flowchart LR\n  A[Lijst ophalen] --> B[Concept maken]\n  B --> C[Medewerker beslist]"}],
    }


class FakeControlPlane:
    """The customer routes of the control plane, and the handoff that signs a person in."""

    def __init__(self):
        self.requests = []
        self.codes = {}
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _handle(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                fake.requests.append((self.command, self.path, body))
                status = 200
                if self.command == "GET" and self.path == "/v1/customer/assignments":
                    # qa is no longer a resource of the Cloud: the installation skips such a row.
                    payload = {"assignments": [{"email": CONSULTANT, "name": "Carla Jansen", "role": "consultant"},
                                               {"email": DEVELOPER, "name": "Daan Visser", "role": "developer"},
                                               {"email": QA, "name": "Quinn Bakker", "role": "qa"}]}
                elif self.command == "POST" and self.path == "/v1/customer/studio/summary":
                    payload = {"ok": True}
                elif self.command == "GET" and re.fullmatch(r"/v1/customer/hours\?period=\d{4}-\d{2}", self.path):
                    payload = dict(HOURS, period=self.path.rsplit("=", 1)[1])
                elif self.command == "GET" and self.path == "/v1/customer/overview":
                    payload = OVERVIEW
                elif self.command == "GET" and self.path.startswith("/v1/tickets"):
                    payload = {"tickets": []}
                elif self.command == "GET" and self.path == "/v1/customer/invoices":
                    payload = INVOICES
                elif self.command == "POST" and self.path == "/v1/customer/invoices/br_voorbeeld1/download":
                    payload = {"content_type": "application/pdf", "pdf_base64": PDF, "filename": "factuur-invoice_voorbeeld1.pdf"}
                elif self.command == "POST" and self.path == "/v1/cloud-session" and (body or {}).get("code") in fake.codes:
                    payload = {"email": fake.codes[body["code"]], "proof": "ab" * 32}
                else:
                    status, payload = 404, {"error": {"code": "not_found", "message": "unknown"}}
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

    def code_for(self, email: str) -> str:
        code = hashlib.sha256(email.encode()).hexdigest()
        self.codes[code] = email
        return code


def pick(page, target, name, value):
    """Choose one option in a link picker of the row form or the block form."""
    wrap = page.locator(f'[data-pl-form][data-pl-target="{target}"] .sp-picker').filter(has=page.locator(f'[name="{name}"]'))
    wrap.locator(".sp-picker-control").click()
    page.locator(f'.sp-picker-option[data-value="{value}"]').click()
    page.keyboard.press("Escape")


def open_row(page, row_id):
    if page.locator(f'[data-pl-row="{row_id}"].open').count() == 0:
        page.locator(f'[data-pl-row="{row_id}"] .rm-title').click()
    page.wait_for_selector("[data-pl-panel]", timeout=8000)


def save_row(page):
    page.locator('[data-pl-form][data-pl-target="row"] button[type="submit"]').click()
    page.wait_for_selector("[data-pl-panel] .pl-ev", timeout=8000)
    page.wait_for_timeout(300)


def main() -> int:
    from playwright.sync_api import sync_playwright

    state_tmp = tempfile.TemporaryDirectory(prefix="plan-gate-")
    state = Path(state_tmp.name)
    art = Path(os.environ.get("ST_ARTIFACT_DIR") or tempfile.mkdtemp(prefix="plan-artifacts-"))
    art.mkdir(parents=True, exist_ok=True)
    home = state / "hermes-home"
    home.mkdir()
    (state / "workspace").mkdir()
    seed(home)
    jobs_path = home / "profiles" / "finbot" / "cron" / "jobs.json"
    jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
    never = dict(jobs["jobs"][0], id="j4", name="Offertes voorbereiden", last_status=None, last_run_at=None)
    never.pop("value", None)
    jobs["jobs"].append(never)
    jobs_path.write_text(json.dumps(jobs), encoding="utf-8")
    skill = home / "skills" / "aanmaning-opstellen"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: aanmaning-opstellen\ndescription: Aanmaning in drie niveaus\n---\n\n# Aanmaning opstellen\n",
                                    encoding="utf-8")
    plane = FakeControlPlane()
    codes = {email: plane.code_for(email) for email in (ADMIN, MEMBER, CONSULTANT, QA)}
    key = state / "control.key"
    key.write_text(f"{KEY_ID}:{SECRET_HEX}\n", encoding="utf-8")
    key.chmod(0o600)
    policy = state / "governance.yaml"
    policy.write_text(json.dumps({          # JSON is YAML
        "version": 1, "mode": "enforce", "default_effect": "deny", "bootstrap_admins": [ADMIN], "installation": {"kind": "hq"},
        "roles": {"member": {"grants": GRANTS}, "synthwave_partner": {"grants": GRANTS}},
        "users": {LEAD: {"roles": ["member"]}, MEMBER: {"roles": ["member"]}}}), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    for name in ("API_SERVER_KEY", "HERMES_WEBUI_PASSWORD", "PYTHONPATH", "HERMES_WEBUI_GOVERNANCE_POLICY", "SP_INTAKE_OFFER", "SP_CONTROL_SOCKET"):
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

            def sign_in(email=None):
                """A context for the admin (password) or for a person who arrives through the Cloud handoff."""
                ctx = browser.new_context(base_url=base_url, viewport={"width": 1440, "height": 1000}, locale="nl-NL", accept_downloads=True)
                if email is None:
                    resp = ctx.request.post("/api/auth/login", data={"password": PASSWORD})
                else:
                    resp = ctx.request.post("/api/auth/cloud-session", data={"code": codes[email]},
                                            headers={"Origin": "https://" + base_url.split("//", 1)[1], "X-SynthPulse-Login": "1"})
                assert resp.ok, (email, resp.status, resp.text()[:200])
                tab = ctx.new_page()
                tab.on("pageerror", lambda e: console_errors.append("pageerror: " + str(e)))
                tab.on("console", lambda m: console_errors.append(m.text + " @ " + (m.location or {}).get("url", ""))
                       if m.type == "error" else None)
                tab.goto("/", wait_until="commit")
                tab.wait_for_function("() => typeof switchPanel === 'function' && typeof _currentPanel === 'string'", timeout=30000)
                return ctx, tab

            # The assignments are pulled on a timer and at a partner's first sign-in: sign the consultant in once,
            # so the installation knows its team before the admin looks.
            warm = browser.new_context(base_url=base_url)
            assert warm.request.post("/api/auth/cloud-session", data={"code": codes[CONSULTANT]},
                                     headers={"Origin": "https://" + base_url.split("//", 1)[1], "X-SynthPulse-Login": "1"}).ok
            warm.close()
            ctx, page = sign_in()
            for body in ({"op": "department.save", "key": "finance", "name": "Finance", "hourly_rate": 60},
                         {"op": "team.save", "department": "finance", "name": "Debiteuren", "lead": LEAD, "members": [MEMBER]}):
                assert ctx.request.post("/api/org/structure", data=body).ok
            uc = ctx.request.post("/api/studio/usecase", data={"title": "Debiteurenopvolging", "team": "finance/debiteuren"}).json()["id"]

            # 1. the assigned team and the hours of the month on the overview
            hub(page, "home")
            page.wait_for_selector("#mainStudio .sp-hours .sp-hours-person", timeout=20000)
            hours = page.locator("#mainStudio .sp-hours").inner_text()
            assert "Uren deze maand" in hours and "Bijgewerkt tot" in hours and "Nog niet bekend" in hours and "Maanduren" in hours, hours
            assert "Carla Jansen" in hours and "Noor de Wit" in hours and "Pakket twee" in hours and "Sales" in hours, hours
            assert "Agentic Consultant" in hours and "Agentic Developer" in hours and "QA" not in hours, hours
            assert "7,1 uur" in hours and "31 maart 2027" in hours and "€" not in hours, hours
            assert "Basis 12 uur, extra blokken 4 uur" in hours and "Uit strippenkaart gebruikt: 2 uur" in hours, hours
            assert "1 uur valt buiten de maanduren en de strippenkaarten." in hours, hours
            assert "Strippenkaarten" in hours and "Agentic Developer: 12 van 20 uur over" in hours and "geldig tot" in hours, hours
            team = page.locator("#mainStudio .sp-partners").inner_text()
            assert "Team van Synthwave" in team and "Carla Jansen" in team and "Synthwave Agentic Consultant" in team, team
            assert "Synthwave Agentic Developer" in team and "Quinn" not in team and "QA" not in team, team
            assert "Agentic Consultant: brengt de processen in kaart, kiest en prioriteert de use cases, traint en draagt over." in team, team
            assert "Agentic Developer: bouwt en onderhoudt de automations in dit platform." in team, team
            assert page.locator("#panelStudio .sp-partner-list.compact .sp-partner-row").count() == 2
            page.screenshot(path=str(art / "01-overview-team-hours.png"))
            ok("the overview shows the assigned team and the hours of the month per role and per person")

            # 2. load the roadmap through the screen
            hub(page, "plan")
            page.wait_for_selector("#mainStudio [data-pl-import-open]", timeout=10000)
            page.locator("#mainStudio [data-pl-import-open]").first.click()
            page.locator("[data-pl-json]").fill("{nope")
            page.locator("[data-pl-import-go]").click()
            page.wait_for_selector(".pl-import-error", timeout=5000)
            page.locator("[data-pl-json]").fill(json.dumps(roadmap_doc()))
            page.locator("[data-pl-import-go]").click()
            page.wait_for_selector("#mainStudio .pl-chart .pl-bar", timeout=10000)
            chart = page.evaluate("""() => ({
              months: [...document.querySelectorAll('.pl-chart .rm-months span')].map(s => s.textContent).filter(Boolean).length,
              weeks: document.querySelectorAll('.pl-chart .rm-weeks .rm-track span').length,
              now: (document.querySelector('.pl-chart .rm-weeks .now') || {}).textContent,
              stars: [...document.querySelectorAll('.pl-steering .pl-star')].map(s => s.style.gridColumn),
              dashed: [...document.querySelectorAll('.pl-chart .pl-bar.k-fundament')].map(b => getComputedStyle(b).borderTopStyle),
              today: getComputedStyle(document.querySelector('.pl-chart .rm-item .rm-track')).getPropertyValue('--rm-today'),
              rows: document.querySelectorAll('.pl-chart .rm-item').length})""")
            assert chart["months"] >= 3 and chart["weeks"] == 16 and chart["now"] == "5", chart
            assert chart["stars"] == ["1", "5", "9", "13"] and chart["dashed"] == ["dashed", "dashed"] and chart["rows"] == 6, chart
            assert chart["today"].endswith("%") and 20 < float(chart["today"].rstrip("%")) < 35, chart
            assert "0 van 6" in page.locator(".pl-strip").inner_text()
            page.screenshot(path=str(art / "02-roadmap-gantt.png"))
            ok("the roadmap is loaded from JSON: months, weeks, steering stars, dashed foundation rows and the marker for today")

            # 3. links, evidence and the derived status
            open_row(page, "b2-fundament")
            page.wait_for_selector('[data-pl-form][data-pl-target="row"] .sp-picker', timeout=8000)
            pick(page, "row", "link_job", "finbot:j4")
            pick(page, "row", "link_skill", "aanmaning-opstellen")
            pick(page, "row", "link_use_case", uc)
            save_row(page)
            assert "s-built" in page.locator('[data-pl-row="b2-fundament"] .pl-bar').get_attribute("class")
            head = page.locator(".pl-panel-head").inner_text()
            assert "Gebouwd" in head and "Afgeleid uit wat er draait" in head and "Handmatig stond dit op gepland" in head, head
            evidence = page.locator("[data-pl-panel] > .pl-panel-grid > section:first-child .pl-ev").all_inner_texts()
            assert len(evidence) == 3 and "Nog niet gedraaid" in evidence[0] and "Geïnstalleerd" in evidence[1] and "Ontdekken" in evidence[2], evidence
            assert "3 koppelingen" in page.locator('[data-pl-row="b2-fundament"] .rm-sub').inner_text()
            assert page.locator(".pl-chart .pl-differs").count() == 0          # moving past "planned" by itself is no warning
            assert "1 gebouwd" in page.locator(".pl-strip").inner_text()
            page.screenshot(path=str(art / "03-row-built.png"))
            # a completed run of the linked task appears
            now = time.time()
            jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
            for job in jobs["jobs"]:
                if job["id"] == "j4":
                    job.update(last_run_at=_iso(now - 120), last_status="ok")
            jobs_path.write_text(json.dumps(jobs), encoding="utf-8")
            conn = sqlite3.connect(home / "profiles" / "finbot" / "cron" / "executions.db")
            conn.execute("INSERT INTO executions (id, job_id, source, process_id, pid, process_started_at, status, claimed_at, started_at, finished_at, error) "
                         "VALUES (?,?,?,?,?,?,?,?,?,?,?)", ("z1", "j4", "s", "p", 1, None, "completed", _iso(now - 200), _iso(now - 200), _iso(now - 120), None))
            conn.commit()
            conn.close()
            hub(page, "usecases")
            hub(page, "plan")
            page.wait_for_function("() => document.querySelector('[data-pl-row=\"b2-fundament\"] .pl-bar.s-live')", timeout=15000)
            strip = page.locator(".pl-strip").inner_text()
            assert "1 van 6 onderdelen draaien" in strip and "0 gebouwd" in strip, strip
            assert "1 van 2 onderdelen draaien" in page.locator(".pl-chart .rm-group-head").nth(2).inner_text()
            open_row(page, "b2-fundament")
            assert "gelukt" in page.locator("[data-pl-panel] .pl-ev").first.inner_text()
            ok("a linked row is built, and runs once a linked task completed a run; the roll-up follows")
            # set by hand to "runs" with only a skill behind it: the mark
            open_row(page, "b1-fundament")
            page.wait_for_selector('[data-pl-form][data-pl-target="row"] .sp-picker', timeout=8000)
            pick(page, "row", "link_skill", "aanmaning-opstellen")
            page.locator('[data-pl-form][data-pl-target="row"] select[name="status"]').select_option("live")
            page.locator('[data-pl-form][data-pl-target="row"] input[name="delivered_at"]').fill("2026-11-20")
            save_row(page)
            mark = page.locator('[data-pl-row="b1-fundament"] .pl-differs')
            assert mark.count() == 1 and "Handmatig staat dit op draait" in mark.get_attribute("title")
            assert page.locator(".pl-chart .pl-differs").count() == 1
            assert "Handmatig stond dit op draait" in page.locator(".pl-panel-head").inner_text()
            assert "opgeleverd op 20 nov 2026" in page.locator("[data-pl-panel] .rm-edit-facts").inner_text()
            # the block card takes its own link
            page.locator("[data-pl-phase-links] summary").click()
            page.wait_for_selector('[data-pl-form][data-pl-target="phase"] .sp-picker', timeout=8000)
            pick(page, "phase", "link_bot", "finbot")
            page.locator('[data-pl-form][data-pl-target="phase"] button[type="submit"]').click()
            page.wait_for_selector("[data-pl-phase-evidence] .pl-ev", timeout=8000)
            assert "Draait" in page.locator(".pl-card h4").inner_text() and "Actief" in page.locator("[data-pl-phase-evidence]").inner_text()
            page.screenshot(path=str(art / "04-row-mark-and-block-card.png"))
            ok("a hand-set status that claims more than the evidence is marked, and the block card links a bot")
            # a linked task opens on that task
            open_row(page, "b2-fundament")
            page.locator("[data-pl-panel] [data-pl-job]").first.click()
            page.wait_for_function("() => _currentPanel === 'tasks' && _currentCronDetail && _currentCronDetail.id === 'j4'", timeout=15000)
            ok("a linked task opens the Tasks screen on that task")

            # 4. systems and process diagrams
            hub(page, "plan")
            page.wait_for_selector("#mainStudio .pl-chart", timeout=10000)
            page.locator('[data-pl-tab="systems"]').click()
            systems = page.locator(".pl-systems").inner_text()
            assert "Boekhouding" in systems and "Te valideren" in systems and "Bevestigd" in systems, systems
            page.locator('[data-pl-tab="diagrams"]').click()
            page.wait_for_selector(".pl-diagram .mermaid-viewer", timeout=20000)
            page.wait_for_function("""() => { const v = document.querySelector('.pl-diagram .mermaid-viewer'), s = v && v._mermaidViewer;
              return s && v.dataset.plFitted && s.box.width * s.scale <= s.viewport.clientWidth + 1; }""", timeout=10000)
            page.screenshot(path=str(art / "05-diagrams.png"))
            ok("the tabs show the systems and a process diagram that fits its frame")

            # 5. a consultant on a use case
            page.evaluate("(id) => window.SPStudio.openUseCase(id)", uc)
            page.wait_for_selector("[data-st-consultant]", timeout=10000)
            options = page.locator("[data-st-consultant] option").all_inner_texts()
            assert options == ["Nog niemand", "Carla Jansen (Agentic Consultant)", "Daan Visser (Agentic Developer)"], options
            page.locator("[data-st-consultant]").select_option(CONSULTANT)
            page.wait_for_function("() => document.querySelector('[data-st-consultant]') && document.querySelector('[data-st-consultant]').value.includes('@')", timeout=10000)
            hub(page, "usecases")
            page.wait_for_selector("#mainStudio .st-card .sp-partner", timeout=10000)
            assert "Synthwave Agentic Consultant · Carla Jansen" in page.locator("#mainStudio .st-card").first.inner_text()
            hub(page, "progress")
            page.wait_for_selector("#mainStudio .st-progress tbody tr", timeout=10000)
            assert "Carla Jansen" in page.locator("#mainStudio .st-progress tbody tr").first.inner_text()
            page.screenshot(path=str(art / "06-progress.png"))
            ok("the consultant is chosen on the use case and shows on the card and in Voortgang")

            # 6. the consultant: partner role, edits the roadmap, no Management, rates or admin
            c_ctx, c_page = sign_in(CONSULTANT)
            me = c_ctx.request.get("/api/org/structure/me").json()
            assert me["partner"] == {"role": "consultant", "org": "synthwave"} and me["scope"] == "none" and not me["can_manage"], me
            for path in ("/api/management/overview", "/api/management/pricing", "/api/value/job", "/api/org/overview", "/api/org/people",
                         "/api/governance/policy", "/api/governance/users", "/api/msp/overview"):
                assert c_ctx.request.get(path).status == 403, path
            structure = c_ctx.request.get("/api/org/structure").json()
            assert "hourly_rate" not in json.dumps(structure["departments"]) or all(
                d.get("hourly_rate") is None for d in (structure["departments"].values() if isinstance(structure["departments"], dict) else structure["departments"]))
            assert c_ctx.request.post("/api/org/structure", data={"op": "department.save", "key": "x", "name": "X"}).status == 403
            hub(c_page, "home")
            c_page.wait_for_selector("#mainStudio .sp-hours", timeout=20000)
            assert "Synthwave Agentic Consultant" in c_page.locator("#mainStudio .wp-role").first.inner_text()
            nav = c_page.locator("#panelStudio [data-st-hub]").evaluate_all("els => els.map(e => e.dataset.stHub)")
            assert "plan" in nav and "progress" in nav and not {"mgmt", "teams", "chart"} & set(nav), nav
            hub(c_page, "plan")
            c_page.wait_for_selector("#mainStudio .pl-chart", timeout=10000)
            open_row(c_page, "kickoff")
            c_page.locator('[data-pl-form][data-pl-target="row"] input[name="note"]').fill("Kick-off gepland met het team")
            c_page.locator('[data-pl-form][data-pl-target="row"] button[type="submit"]').click()
            c_page.wait_for_function("() => /Kick-off gepland met het team/.test((document.querySelector('[data-pl-panel] .rm-edit-facts') || {}).textContent || '')", timeout=8000)
            c_page.evaluate("(id) => window.SPStudio.openUseCase(id)", uc)
            c_page.wait_for_selector("[data-st-consultant]", timeout=10000)
            assert c_page.locator("[data-st-delete]").count() == 0 and c_page.locator("[data-st-send]").count() == 1
            assert c_ctx.request.get("/api/msp/invoices").status == 403
            c_page.screenshot(path=str(art / "07-consultant.png"))
            # nothing a partner was refused lands in the customer's approval queue
            pending = ctx.request.get("/api/governance/approvals").json()
            assert CONSULTANT not in json.dumps(pending), "a partner denial became an access request"
            c_ctx.close()
            ok("the consultant changes the roadmap, reaches no Management, rates or admin route, and files no access request")

            # 7. an address that is not (or no longer) assigned gets nothing; a team member views and cannot change
            q_ctx = browser.new_context(base_url=base_url)
            assert q_ctx.request.post("/api/auth/cloud-session", data={"code": codes[QA]},
                                      headers={"Origin": "https://" + base_url.split("//", 1)[1], "X-SynthPulse-Login": "1"}).ok
            for path in ("/api/studio/roadmap", "/api/studio/usecases", "/api/studio/hours", "/api/org/structure"):
                assert q_ctx.request.get(path).status == 403, path
            q_ctx.close()
            m_ctx, m_page = sign_in(MEMBER)
            assert m_ctx.request.post("/api/studio/roadmap", data={"op": "import", "roadmap": roadmap_doc()}).status == 403
            assert m_ctx.request.get("/api/studio/hours").status == 403 and m_ctx.request.get("/api/studio/summary").status == 403
            hub(m_page, "plan")
            m_page.wait_for_selector("#mainStudio .pl-chart", timeout=10000)
            open_row(m_page, "b2-fundament")
            assert m_page.locator("[data-pl-form]").count() == 0 and m_page.locator(".pl-actions").count() == 0
            texts = m_page.locator("[data-pl-panel] .pl-ev").all_inner_texts()
            assert any("Niet zichtbaar voor jou" in t for t in texts) and "s-live" in m_page.locator('[data-pl-row="b2-fundament"] .pl-bar').get_attribute("class"), texts
            hub(m_page, "home")
            m_page.wait_for_selector("#mainStudio .sp-partners", timeout=20000)
            assert m_page.locator("#mainStudio .sp-hours").count() == 0
            assert m_ctx.request.get("/api/msp/invoices").status == 403
            m_page.screenshot(path=str(art / "09-member.png"))
            m_ctx.close()
            ok("somebody the Cloud does not assign gets nothing, and a team member views the roadmap without what they may not see")

            # 8. narrow (the page remembers the tab that was open)
            hub(page, "plan")
            page.wait_for_selector("#mainStudio .pl-tabs", timeout=10000)
            page.locator('[data-pl-tab="plan"]').click()
            page.wait_for_selector("#mainStudio .pl-chart", timeout=10000)
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(400)
            open_row(page, "b2-fundament")
            dims = page.evaluate("""() => { const s = document.querySelector('#mainStudio .rm-scroll'), p = document.querySelector('[data-pl-panel]').getBoundingClientRect(),
              t = document.querySelector('.pl-tabs').getBoundingClientRect();
              return [document.documentElement.scrollWidth, window.innerWidth, s.scrollWidth, s.clientWidth, Math.round(p.right), Math.round(s.getBoundingClientRect().right), Math.round(t.right)]; }""")
            assert dims[0] <= dims[1] + 1 and dims[2] > dims[3] and dims[4] <= dims[5] + 1 and dims[6] <= dims[1], dims
            page.screenshot(path=str(art / "10-narrow.png"))
            ok("narrow layout: the chart scrolls sideways, the panel and the tabs fit, the page does not scroll")

            # 9. payments and invoices: the organisation admin, signed in through the personal Cloud link
            assert ctx.request.get("/api/msp/invoices").status == 403          # the shared password session carries no personal proof
            a_ctx, a_page = sign_in(ADMIN)
            a_page.wait_for_selector("#btnMsp:not([hidden])", state="attached", timeout=20000)
            a_page.evaluate("() => switchPanel('msp', {fromRailClick: true})")
            a_page.wait_for_selector("#mspBillingTab", timeout=20000)
            a_page.locator("#mspBillingTab").click()
            a_page.wait_for_selector("#mspLedger [data-ledger-invoice]", timeout=15000)
            ledger = a_page.locator("#mspLedger").inner_text()
            assert "Betalingen en facturatie" in ledger and "Nog niet elke betaling" in ledger and "Facturen (2)" in ledger and "Betalingen (1)" in ledger, ledger
            assert "F-2026-0012" in ledger and "1.452,00" in ledger and "Betaald" in ledger and "Openstaand" in ledger and "6.050,00" in ledger, ledger
            assert a_page.locator('[data-ledger-invoice="br_voorbeeld1"] button').count() == 1
            assert a_page.locator('[data-ledger-invoice="br_voorbeeld2"] button').count() == 0          # no document: no download
            with a_page.expect_download(timeout=15000) as download:
                a_page.locator('[data-ledger-invoice="br_voorbeeld1"] button').click()
            assert download.value.suggested_filename == "factuur-invoice_voorbeeld1.pdf"
            a_page.screenshot(path=str(art / "11-payments-invoices.png"))
            a_ctx.close()
            ok("the organisation admin sees payments and invoices and downloads the invoice that has a document")

            assert any(method == "POST" and path == "/v1/cloud-session" for method, path, _b in plane.requests)
            ours = [x for x in console_errors if "pageerror" in x or "studio" in x.lower() or "roadmap" in x.lower()]
            assert not ours, ours
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
    finally:
        if proc is not None:
            _terminate_process(proc)
        if log is not None:
            log.close()
        plane.server.shutdown()
        plane.server.server_close()
        print("artifacts:", art)
        state_tmp.cleanup()
    return code


if __name__ == "__main__":
    sys.exit(main())
