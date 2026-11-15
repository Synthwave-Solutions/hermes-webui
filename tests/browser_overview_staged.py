"""Browser gate for the Studio overview that paints in steps.

Boots the real server.py with isolated state (same seed as
browser_org_management.py) and holds the three slow answers back in the
browser: the bot list, the scheduled tasks and the organisation chart.

1. the overview is on screen while those three are still under way: the quick
   lists are counted, tasks and bots show as loading instead of zero;
2. the page asks for the fast bot list and never for the slow one;
3. when the slow answers arrive the counts fill in and nothing stays busy;
4. coming back to the overview paints the known numbers at once.

    python tests/browser_overview_staged.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_conversation_lifecycle import _terminate_process  # noqa: E402
from browser_org_management import ADMIN, PASSWORD, ok, seed, start_server  # noqa: E402

SLOW = {"/api/org/chart": 6.0, "/api/crons": 3.0, "/api/profiles": 4.5}


def main() -> int:
    from playwright.sync_api import sync_playwright

    state_tmp = tempfile.TemporaryDirectory(prefix="overview-gate-")
    state = Path(state_tmp.name)
    art = Path(os.environ.get("ST_ARTIFACT_DIR") or tempfile.mkdtemp(prefix="overview-artifacts-"))
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
    console_errors, asked = [], []
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
            # The delay lives in the page, so the three answers are late without blocking this script.
            page.add_init_script("""(() => {
              const slow = %s, real = window.fetch;
              window.__hold = true; window.__asked = [];
              window.fetch = function(input, init){
                const url = new URL(typeof input === 'string' ? input : input.url, location.href);
                window.__asked.push(url.pathname + url.search);
                const wait = window.__hold && !url.search.includes('agenda_start') ? (slow[url.pathname] || 0) : 0;
                return wait ? new Promise(done => setTimeout(done, wait * 1000)).then(() => real.call(this, input, init)) : real.call(this, input, init);
              };
            })()""" % json.dumps(SLOW))
            page.goto("/", wait_until="domcontentloaded")
            page.wait_for_function("() => typeof switchPanel === 'function' && typeof _currentPanel === 'string'", timeout=20000)
            page.evaluate("() => { switchPanel('studio'); }")
            started = time.time()

            # 1. on screen before the slow answers
            page.wait_for_selector("#mainStudio .wp-kpis", timeout=2500)
            first = time.time() - started
            busy = page.locator("#mainStudio .wp-kpi-value[aria-busy=true]").count()
            values = page.locator("#mainStudio .wp-kpi-value").all_inner_texts()
            assert busy == 2 and values.count("…") == 2, (busy, values)
            assert any(v.isdigit() for v in values), values
            assert not page.locator("#mainStudio .wp-kpi.zero .wp-kpi-value[aria-busy=true]").count()
            page.screenshot(path=str(art / "01-first-paint.png"))
            ok(f"the overview is on screen after {first:.1f} s while bots, tasks and the chart are still loading; those two counts show as loading")

            # 2. the fast bot list only
            page.wait_for_function("() => !document.querySelector('#mainStudio .wp-kpi-value[aria-busy=true]')", timeout=20000)
            asked[:] = page.evaluate("() => window.__asked")
            mine = [u for u in asked if u.split("?")[0] == "/api/profiles"]
            assert mine and all("fast=1" in u for u in mine), mine
            assert any("fast=1&counts=0" in u for u in mine), mine
            ok("the page asks for the fast bot list and never for the slow one")

            # 3. filled in afterwards
            values = page.locator("#mainStudio .wp-kpi-value").all_inner_texts()
            assert values and all(v.isdigit() for v in values), values
            page.wait_for_timeout(SLOW["/api/org/chart"] * 1000)
            assert page.locator("#mainStudio .wp-kpis").count() == 1 and not page.locator("#mainStudio .wp-skeleton").count()
            page.screenshot(path=str(art / "02-complete.png"))
            ok("the counts fill in when the slow answers arrive and nothing stays busy: " + ", ".join(values))

            # 4. back on the overview: the known numbers at once
            page.evaluate("() => { switchPanel('chat'); }")
            page.wait_for_timeout(300)
            page.evaluate("() => { switchPanel('studio'); }")
            page.wait_for_selector("#mainStudio .wp-kpis", timeout=1500)
            again = page.locator("#mainStudio .wp-kpi-value").all_inner_texts()
            assert again == values and not page.locator("#mainStudio .wp-kpi-value[aria-busy=true]").count(), (again, values)
            ok("coming back to the overview shows the known numbers at once")

            ours = [e for e in console_errors if "pageerror" in e or "workplace" in e.lower()]
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
        try:
            asked[:] = page.evaluate("() => window.__asked")
        except Exception:
            pass
        print("asked:", [u for u in asked if u.split("?")[0] in SLOW or "studio" in u][:30])
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
