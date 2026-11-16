"""Browser gate for the backlog as a roadmap (the schedule view).

Boots the real server.py with isolated state (same seed as
browser_org_management.py), builds two departments with a team each and five
ideas, and drives Chromium through the schedule:

1. the backlog switches from list to schedule: months, week numbers, one bar
   per idea, a parked idea left out, proposals dashed and a set start solid;
2. grouping per person, per team, per department and as one list;
3. the lens narrows the schedule to the ideas of the viewer;
4. an idea is given a start, a duration and a colleague, and can be handed
   back to the proposal;
5. the choice of view survives a reload and the list shows who does an idea;
6. narrow layout: the chart scrolls sideways, the page does not.

    python tests/browser_roadmap.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_conversation_lifecycle import _terminate_process  # noqa: E402
from browser_org_management import ADMIN, LEAD, MEMBER, PASSWORD, hub, ok, seed, start_server  # noqa: E402


def main() -> int:
    from playwright.sync_api import sync_playwright

    state_tmp = tempfile.TemporaryDirectory(prefix="roadmap-gate-")
    state = Path(state_tmp.name)
    art = Path(os.environ.get("ST_ARTIFACT_DIR") or tempfile.mkdtemp(prefix="roadmap-artifacts-"))
    art.mkdir(parents=True, exist_ok=True)
    home = state / "hermes-home"
    home.mkdir()
    (state / "workspace").mkdir()
    seed(home)
    policy = state / "governance.yaml"
    policy.write_text(f"version: 1\nmode: report_only\ndefault_effect: deny\nbootstrap_admins:\n- {ADMIN}\ninstallation:\n  kind: hq\n",
                      encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    for key in ("API_SERVER_KEY", "HERMES_WEBUI_PASSWORD", "PYTHONPATH", "HERMES_WEBUI_GOVERNANCE_POLICY", "SP_INTAKE_OFFER"):
        env.pop(key, None)
    env.update({
        "HERMES_WEBUI_HOST": "127.0.0.1", "HERMES_WEBUI_STATE_DIR": str(state / "webui-state"),
        "HERMES_HOME": str(home), "HERMES_BASE_HOME": str(home), "HERMES_CONFIG_PATH": str(home / "config.yaml"),
        "HERMES_WEBUI_SKIP_ONBOARDING": "1",
        "HERMES_WEBUI_AGENT_DIR": str(Path(os.environ.get("HERMES_WEBUI_AGENT_DIR") or Path.home() / ".hermes/hermes-agent")),
        "HERMES_WEBUI_DEFAULT_WORKSPACE": str(state / "workspace"), "HERMES_WEBUI_GOVERNANCE_POLICY": str(policy),
        "HERMES_WEBUI_PASSWORD": PASSWORD, "HERMES_WEBUI_PASSWORD_IDENTITY": ADMIN, "HERMES_WEBUI_PREWARM": "0",
        "SP_VALUE_LABELER": "0", "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
    })
    proc = log = page = None
    console_errors = []
    code = 1
    try:
        proc, log, base_url = start_server(env, art)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(base_url=base_url, viewport={"width": 1440, "height": 1000}, locale="nl-NL")
            assert ctx.request.post("/api/auth/login", data={"password": PASSWORD}).ok

            def org(body):
                r = ctx.request.post("/api/org/structure", data=body)
                assert r.ok, r.text()

            def idea(body):
                r = ctx.request.post("/api/studio/backlog", data=body)
                assert r.ok, r.text()
                return r.json()

            org({"op": "department.save", "key": "finance", "name": "Finance"})
            org({"op": "department.save", "key": "sales", "name": "Sales"})
            org({"op": "team.save", "department": "finance", "name": "Debiteuren", "lead": LEAD, "members": [MEMBER]})
            org({"op": "team.save", "department": "sales", "name": "Inside", "members": [ADMIN]})
            monday = date.today() - timedelta(days=date.today().weekday())
            fixed = monday + timedelta(weeks=3)
            a = idea({"title": "Aanmaningen versturen", "team": "finance/debiteuren", "impact": 5, "effort": 2})
            idea({"id": a["id"], "assignee": MEMBER})
            b = idea({"title": "Weekrapport debiteuren", "team": "finance/debiteuren", "effort": 3})
            idea({"id": b["id"], "status": "design", "assignee": LEAD})
            c = idea({"title": "Leads opvolgen", "team": "sales/inside", "effort": 4, "start": (fixed + timedelta(days=2)).isoformat(), "weeks": 4})
            d = idea({"title": "Offertes opstellen", "effort": 1})
            idea({"id": d["id"], "status": "live"})
            e = idea({"title": "Geparkeerd idee", "team": "sales/inside"})
            idea({"id": e["id"], "status": "parked"})
            assert c["start"] == fixed.isoformat(), c

            page = ctx.new_page()
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda x: console_errors.append("pageerror: " + str(x)))
            page.goto("/", wait_until="domcontentloaded")
            page.wait_for_function("() => typeof switchPanel === 'function' && typeof _currentPanel === 'string'", timeout=20000)
            hub(page, "backlog")
            page.wait_for_selector("#mainStudio .bl-list", timeout=10000)

            # 1. from list to schedule
            page.locator("#mainStudio [data-bl-view=plan]").click()
            page.wait_for_selector("#mainStudio .rm-chart .rm-bar", timeout=10000)
            page.wait_for_selector("#mainStudio .rm .sp-lens", timeout=10000)
            bars = page.locator("#mainStudio .rm-chart .rm-bar")
            assert bars.count() == 4, bars.count()
            assert not page.locator("#mainStudio .rm-chart", has_text="Geparkeerd idee").count()
            assert page.locator(f'#mainStudio .rm-bar[data-rm-edit="{c["id"]}"]').get_attribute("class").find("auto") < 0
            assert "auto" in page.locator(f'#mainStudio .rm-bar[data-rm-edit="{a["id"]}"]').get_attribute("class")
            assert "s-design" in page.locator(f'#mainStudio .rm-bar[data-rm-edit="{b["id"]}"]').get_attribute("class")
            weeks = page.locator("#mainStudio .rm-weeks .rm-track span")
            assert weeks.count() >= 12 and page.locator("#mainStudio .rm-weeks .rm-track span.now").count() == 1
            assert page.locator("#mainStudio .rm-months span").first.inner_text().strip()
            tiles = dict(zip(page.locator("#mainStudio .rm-tile-label").all_inner_texts(), page.locator("#mainStudio .rm-tile-value").all_inner_texts()))
            assert tiles["Ideeën in beeld"] == "4" and tiles["In uitvoering"] == "1" and tiles["Live"] == "1" and tiles["Quick wins"] == "2", tiles
            page.screenshot(path=str(art / "01-per-person.png"), full_page=True)
            ok("the backlog switches to a schedule: months, week numbers, four bars, the parked idea left out, proposals dashed, the set start solid")

            # 2. grouping
            def heads():
                return [t.split("\n")[0].strip() for t in page.locator("#mainStudio .rm-group-head .rm-left strong").all_inner_texts()]

            people = heads()
            assert len(people) == 3, people
            page.locator("#mainStudio [data-rm-group=team]").click()
            assert set(heads()) == {"Debiteuren", "Inside", "Zonder team"}, heads()
            page.screenshot(path=str(art / "02-per-team.png"), full_page=True)
            page.locator("#mainStudio [data-rm-group=dept]").click()
            assert set(heads()) == {"Finance", "Sales", "Zonder afdeling"}, heads()
            page.locator("#mainStudio [data-rm-group=none]").click()
            assert not page.locator("#mainStudio .rm-group-head").count() and bars.count() == 4
            page.locator("#mainStudio [data-rm-group=person]").click()
            ok("the schedule groups per person, per team, per department and as one list: " + ", ".join(people))

            # 3. the lens
            page.locator('#mainStudio .rm [data-sp-lens="mine"]').click()
            page.wait_for_function("() => document.querySelectorAll('#mainStudio .rm-chart .rm-bar').length === 2", timeout=5000)
            assert set(page.locator("#mainStudio .rm-title").all_inner_texts()) == {"Leads opvolgen", "Offertes opstellen"}
            page.locator('#mainStudio .rm [data-sp-lens="org"]').click()
            page.wait_for_function("() => document.querySelectorAll('#mainStudio .rm-chart .rm-bar').length === 4", timeout=5000)
            ok("the lens narrows the schedule to the ideas the viewer does")

            # 4. schedule an idea and hand it back
            page.locator(f'#mainStudio .rm-title[data-rm-edit="{a["id"]}"]').click()
            form = page.locator(f'#mainStudio [data-rm-form="{a["id"]}"]')
            form.wait_for(timeout=5000)
            assert not form.locator("[data-rm-propose]").count()
            start = monday + timedelta(weeks=5)
            form.locator("input[name=start]").fill((start + timedelta(days=3)).isoformat())
            form.locator("input[name=weeks]").fill("4")
            form.locator("select[name=assignee]").select_option(LEAD)
            form.locator("button[type=submit]").click()
            page.wait_for_function(f"""() => {{ const b = document.querySelector('#mainStudio .rm-bar[data-rm-edit="{a["id"]}"]'); return b && !b.classList.contains('auto'); }}""", timeout=8000)
            saved = next(i for i in ctx.request.get("/api/studio/backlog").json()["items"] if i["id"] == a["id"])
            assert saved["start"] == start.isoformat() and saved["weeks"] == 4 and saved["assignee"] == LEAD, saved
            assert saved["plan"] == {"start": start.isoformat(), "weeks": 4, "end": (start + timedelta(weeks=4)).isoformat(), "auto": False}
            page.screenshot(path=str(art / "03-scheduled.png"), full_page=True)
            page.locator(f'#mainStudio .rm-bar[data-rm-edit="{a["id"]}"]').click()
            page.locator(f'#mainStudio [data-rm-form="{a["id"]}"]').wait_for(timeout=5000)
            page.screenshot(path=str(art / "04-editor.png"), full_page=True)
            page.locator(f'#mainStudio [data-rm-propose="{a["id"]}"]').click()
            page.wait_for_function(f"""() => {{ const b = document.querySelector('#mainStudio .rm-bar[data-rm-edit="{a["id"]}"]'); return b && b.classList.contains('auto'); }}""", timeout=8000)
            back = next(i for i in ctx.request.get("/api/studio/backlog").json()["items"] if i["id"] == a["id"])
            assert "start" not in back and "weeks" not in back and back["plan"]["auto"] and back["assignee"] == LEAD, back
            page.locator(f'#mainStudio .rm-title[data-rm-edit="{b["id"]}"]').click()
            page.locator(f'#mainStudio [data-rm-form="{b["id"]}"]').wait_for(timeout=5000)
            page.keyboard.press("Escape")
            page.wait_for_selector("#mainStudio [data-rm-panel]", state="detached", timeout=5000)
            ok("an idea gets a start week, a duration and a colleague; 'laat voorstellen' hands it back to the proposal; Escape closes the editor")

            # 5. the view is remembered, the list shows who does it
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function("() => typeof switchPanel === 'function' && typeof _currentPanel === 'string'", timeout=20000)
            hub(page, "backlog")
            page.wait_for_selector("#mainStudio .rm-chart .rm-bar", timeout=10000)
            page.locator("#mainStudio [data-bl-view=list]").click()
            page.wait_for_selector("#mainStudio .bl-list", timeout=5000)
            row = page.locator(f'#mainStudio .bl-item[data-bl="{a["id"]}"]').inner_text()
            assert "Doet:" in row, row
            ok("the schedule is remembered as the chosen view and the list shows who does an idea")

            # 6. narrow
            page.locator("#mainStudio [data-bl-view=plan]").click()
            page.wait_for_selector("#mainStudio .rm-chart .rm-bar", timeout=10000)
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(400)
            dims = page.evaluate("() => { const s = document.querySelector('#mainStudio .rm-scroll'); return [document.documentElement.scrollWidth, window.innerWidth, s.scrollWidth, s.clientWidth]; }")
            assert dims[0] <= dims[1] + 1 and dims[2] > dims[3], dims
            page.screenshot(path=str(art / "05-narrow.png"))
            ok("narrow layout: the chart scrolls sideways and the page does not")

            ours = [x for x in console_errors if "pageerror" in x or "roadmap" in x.lower()]
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
        print("artifacts:", art)
        state_tmp.cleanup()
    return code


if __name__ == "__main__":
    sys.exit(main())
