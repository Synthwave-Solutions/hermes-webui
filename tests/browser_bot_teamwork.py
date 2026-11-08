"""Browser gate for bot teamwork in the chat (plan section 6).

Boots the real server.py with isolated state (the same launcher as
tests/browser_interactive_ui.py, signed in with a local password), creates
three bots with display names, imports a transcript the way
tests/browser_historical_transcript_hydration.py does and drives Chromium:

1. the coordinating turn shows one handoff line ("Sanne heeft Linus gevraagd")
   with the task behind "Bekijk de opdracht";
2. the specialist's report is a "Linus is klaar" card that links to its work;
3. the reply after it carries the "met hulp van Linus" chip;
4. a handoff-mode task row reads "Opdracht van Sanne aan Grace" with the
   bot-written task folded away;
5. the dock under the chat is "Teamwerk" with photos and plain statuses, folds
   when everything is done and opens while someone is working;
6. no profile IDs, no envelope text and no robot emoji anywhere in the chat;
7. the same after a hard reload, at 390 px, in dark and light.

Screenshots land in TEAMWORK_ARTIFACT_DIR (default: a temp dir).

    python tests/browser_bot_teamwork.py
"""

from __future__ import annotations

import os
import sqlite3
import struct
import sys
import tempfile
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_conversation_lifecycle import _terminate_process  # noqa: E402
from browser_interactive_ui import E2E_PASSWORD, ok, start_server  # noqa: E402

BOTS = {"sanne-sales": "Sanne", "linus-research": "Linus", "grace-ops": "Grace"}
CHILD = "abcdef123456"
TASK = "Vergelijk de drie offertes van de leveranciers en noem de goedkoopste met de totale prijs."
HANDOFF_TASK = "Write the customer reply about the delivery date in plain Dutch."
FINAL = "Linus heeft de offertes vergeleken: leverancier B is het voordeligst."
GRACE_REPLY = "Hier is het concept voor de klant over de leverdatum."
ENVELOPE = ("[ASYNC DELEGATION COMPLETE \u2014 job-linus]\nSpecialist: linus-research; conversation " + CHILD
            + "\nTask: " + TASK + "\n\nResult data:\nLeverancier B: 12.400 euro totaal.\n\n"
            "Use these findings to continue the user's task and give a clear response.")
FORBIDDEN_TEXT = ["sanne-sales", "linus-research", "grace-ops", "ASYNC DELEGATION", "Result data",
                  "Use these findings", "Bot delegation", "\u2192"]


def _png(rgb):
    """A tiny solid square as a real PNG, so the avatar path is exercised."""
    w = h = 16
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _make_bots(home: Path):
    for name, title in BOTS.items():
        folder = home / "profiles" / name
        (folder / "assets").mkdir(parents=True)
        (folder / "config.yaml").write_text("toolsets: []\nmcp_servers: {}\n", encoding="utf-8")
        (folder / "profile.yaml").write_text(
            f"ui_meta:\n  hermes-bots:\n    title: {title}\n    description: {title} helpt het team.\n    kind: bot\n",
            encoding="utf-8")
    # Sanne and Linus have a photo, Grace keeps her initial.
    (home / "profiles" / "sanne-sales" / "assets" / "avatar.png").write_bytes(_png((184, 134, 11)))
    (home / "profiles" / "linus-research" / "assets" / "avatar.png").write_bytes(_png((2, 136, 168)))


def _transcript():
    sanne = {"bot_profile": "sanne-sales", "bot_name": "Sanne"}
    return [
        {"role": "user", "content": "Kun je de offertes van de drie leveranciers vergelijken?"},
        {"role": "assistant", "content": "Ik vraag Linus om de cijfers na te lopen.", **sanne, "tool_calls": [
            {"id": "call-list", "type": "function", "function": {"name": "delegate_to_bot", "arguments": '{"action":"list"}'}},
            {"id": "call-linus", "type": "function", "function": {"name": "delegate_to_bot", "arguments":
                '{"action":"delegate","bot":"linus-research","task":"' + TASK + '"}'}},
        ]},
        {"role": "tool", "tool_call_id": "call-list", "content": '{"bots":["linus-research","grace-ops"],"remaining_handoffs":4}'},
        {"role": "tool", "tool_call_id": "call-linus", "content":
            '{"status":"queued","mode":"background","delegation_id":"job-linus","bot":"linus-research","session_id":"' + CHILD + '"}'},
        {"role": "assistant", "content": "Linus kijkt het na. Ik meld me zodra er een antwoord is.", **sanne},
        {"role": "user", "_source": "process_wakeup", "content": ENVELOPE, "bot_delegation": {
            "id": "job-linus", "from": "linus-research", "to": "sanne-sales", "task": "Specialist result: " + TASK,
            "session_id": CHILD, "mode": "background", "result": True}},
        {"role": "assistant", "content": FINAL, **sanne},
        {"role": "user", "content": "Kan Grace de klant antwoorden?"},
        {"role": "assistant", "content": "Grace neemt dit over.", **sanne, "tool_calls": [
            {"id": "call-grace", "type": "function", "function": {"name": "delegate_to_bot", "arguments":
                '{"action":"delegate","mode":"handoff","bot":"grace-ops","task":"' + HANDOFF_TASK + '"}'}}]},
        {"role": "tool", "tool_call_id": "call-grace", "content": '{"status":"queued","delegation_id":"job-grace","bot":"grace-ops"}'},
        {"role": "user", "content": "@grace-ops\n[Bot delegation: sanne-sales to grace-ops]\n" + HANDOFF_TASK
            + "\n\nExecute the delegated task and report your result in this same chat.",
         "bot_delegation": {"id": "job-grace", "from": "sanne-sales", "to": "grace-ops", "task": HANDOFF_TASK}},
        {"role": "assistant", "content": GRACE_REPLY, "bot_profile": "grace-ops", "bot_name": "Grace"},
    ]


def _seed_queue(state_dir: Path, sid: str, running: bool = False):
    """Teamwork records as api/bot_delegation.py and api/bot_specialists.py store them."""
    folder = state_dir / "bot-delegations"
    folder.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(folder / "queue.sqlite3", timeout=10)
    try:
        db.execute('''CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY, session_id TEXT NOT NULL, origin_stream TEXT UNIQUE NOT NULL,
          source_bot TEXT NOT NULL, target_bot TEXT NOT NULL, task TEXT NOT NULL,
          authority TEXT NOT NULL, ceiling TEXT NOT NULL, depth INTEGER NOT NULL, state TEXT NOT NULL,
          target_stream TEXT, target_authority TEXT, detail TEXT, created REAL NOT NULL, updated REAL NOT NULL)''')
        db.execute('''CREATE TABLE IF NOT EXISTS specialists (
            id TEXT PRIMARY KEY, session_id TEXT NOT NULL, origin_stream TEXT UNIQUE NOT NULL,
            source_bot TEXT NOT NULL, target_bot TEXT NOT NULL, task TEXT NOT NULL,
            authority TEXT NOT NULL, ceiling TEXT NOT NULL, depth INTEGER NOT NULL,
            state TEXT NOT NULL, child_id TEXT NOT NULL, target_authority TEXT,
            target_stream TEXT, result_authority TEXT, result_stream TEXT,
            detail TEXT, created REAL NOT NULL, updated REAL NOT NULL)''')
        now = time.time()
        with db:
            if running:
                db.execute("INSERT OR REPLACE INTO specialists VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           ("job-more", sid, "stream-more", "sanne-sales", "linus-research", "Zoek de levertijden van leverancier B op",
                            "x", "x", 1, "started", "fedcba654321", None, "t", None, None, None, now - 20, now - 5))
            else:
                db.execute("INSERT OR REPLACE INTO specialists VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           ("job-linus", sid, "stream-linus", "sanne-sales", "linus-research", TASK,
                            "x", "x", 1, "delivered", CHILD, None, None, None, None, None, now - 300, now - 240))
                db.execute("INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           ("job-grace", sid, "stream-grace", "sanne-sales", "grace-ops", HANDOFF_TASK,
                            "x", "x", 1, "completed", "t2", None, None, now - 120, now - 60))
    finally:
        db.close()


def _chat_text(page) -> str:
    return page.evaluate("() => (document.querySelector('#msgInner') || {}).innerText || ''")


def _assert_clean(page, where):
    text = _chat_text(page)
    html = page.evaluate("() => (document.querySelector('#msgInner') || {}).innerHTML || ''")
    for bad in FORBIDDEN_TEXT:
        assert bad not in text, f"{where}: {bad!r} is visible in the chat"
    assert "\U0001F916" not in html, f"{where}: robot emoji in the chat"
    dock_text = page.evaluate("() => (document.getElementById('spSubagentDock') || {}).innerText || ''")
    dock_html = page.evaluate("() => (document.getElementById('spSubagentDock') || {}).innerHTML || ''")
    for bad in ("sanne-sales", "linus-research", "grace-ops"):
        assert bad not in dock_text, f"{where}: {bad!r} is visible in the dock"
    assert "\U0001F916" not in dock_html, f"{where}: robot emoji in the dock"


def _wait_rendered(page):
    page.wait_for_function("t => ((document.querySelector('#msgInner') || {}).innerText || '').includes(t)",
                           arg=GRACE_REPLY, timeout=15000)
    page.wait_for_function("() => document.querySelectorAll('#msgInner .sp-handoff-line').length >= 1", timeout=10000)
    # The bot catalog arrives after boot; names repaint once it is in.
    page.wait_for_function("() => !!(window.groupRouting && groupRouting.botInfo('linus-research'))", timeout=15000)
    page.wait_for_function(
        "() => ((document.querySelector('#msgInner') || {}).innerText || '').includes('Linus is klaar')",
        timeout=10000)


def _assert_story(page, where):
    text = _chat_text(page)
    for want in ("Bekijk de opdracht",
                 "Linus is klaar", "Antwoord gaat naar Sanne", "Bekijk het werk van Linus",
                 "Grace neemt het hierna over in dit gesprek", "Opdracht van Sanne aan Grace", FINAL, GRACE_REPLY):
        assert want in text, f"{where}: missing {want!r}"
    # The list call alone is a work step, not a line in the conversation.
    assert "Sanne keek wie kan helpen" not in text, where
    # Once a helper reported back, its result card tells the story: the
    # handoff line and the helper chip step back. A handoff without a report
    # yet (Grace taking over) still shows as its own line.
    assert "Sanne heeft Linus gevraagd" not in text and "met hulp van Linus" not in text, where
    shown = page.evaluate("""() => {
        const visible = el => el.getClientRects().length > 0;
        const lines = [...document.querySelectorAll('#msgInner .sp-handoff-line')].filter(visible).map(el => ({
          where: 'line', kind: el.dataset.kind, text: el.querySelector('.sp-handoff-text').textContent,
          avatars: el.querySelectorAll('.sp-bot-avatar').length, photo: !!el.querySelector('.sp-bot-avatar-from img'),
          height: el.querySelector('.sp-handoff-summary').getBoundingClientRect().height, font: getComputedStyle(el).fontSize}));
        const rows = [...document.querySelectorAll('#msgInner .tool-card-row[data-tool-family="handoff"]')].filter(visible).map(el => ({
          where: 'row', text: el.dataset.toolActionLabel, avatars: el.querySelectorAll('.sp-bot-avatar').length,
          photo: !!el.querySelector('.sp-bot-avatar-from img')}));
        return lines.concat(rows);
    }""")
    asked = [item for item in shown if item["text"].startswith("Sanne heeft Linus gevraagd")]
    takeover = [item for item in shown if item["text"] == "Grace neemt het hierna over in dit gesprek"]
    assert len(asked) == 0 and len(takeover) == 1, shown
    assert len(shown) == 1, shown
    assert all(item["avatars"] == 2 and item["photo"] for item in shown), shown
    assert all(item["font"] == "13px" and item["height"] < 34 for item in shown if item["where"] == "line"), shown
    # The helper chip exists for assistive tech and tooltips but is not shown
    # next to a reply that directly follows the result card.
    chips = page.evaluate("""() => [...document.querySelectorAll('#msgInner .sp-assisted-chip')].filter(c => c.getClientRects().length > 0).map(c => c.textContent)""")
    assert chips == [], chips
    # The bot-written task is folded; the human-readable author line is visible.
    task_open = page.evaluate("() => document.querySelector('#msgInner details.sp-handoff-task').open")
    assert task_open is False, "the bot-written task should start folded"
    assert page.is_visible("#msgInner .sp-bot-result [data-sp-specialist-open='" + CHILD + "']")
    _assert_clean(page, where)


def main() -> int:
    from playwright.sync_api import sync_playwright

    state_tmp = tempfile.TemporaryDirectory(prefix="teamwork-gate-")
    state = Path(state_tmp.name)
    art = Path(os.environ.get("TEAMWORK_ARTIFACT_DIR") or tempfile.mkdtemp(prefix="teamwork-artifacts-"))
    art.mkdir(parents=True, exist_ok=True)
    home = state / "hermes-home"
    home.mkdir()
    (state / "workspace").mkdir()
    (home / "config.yaml").write_text("toolsets: []\nmcp_servers: {}\nmemory:\n  memory_enabled: false\n"
                                      "  user_profile_enabled: false\n", encoding="utf-8")
    _make_bots(home)
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    for key in ("API_SERVER_KEY", "HERMES_WEBUI_PASSWORD", "HERMES_WEBUI_EXTENSION_DIR", "HERMES_WEBUI_EXTENSION_MANIFEST",
                "HERMES_WEBUI_CHAT_BACKEND", "PYTHONPATH"):
        env.pop(key, None)
    webui_state = state / "webui-state"
    env.update({
        "HERMES_WEBUI_HOST": "127.0.0.1",
        "HERMES_WEBUI_STATE_DIR": str(webui_state),
        "HERMES_HOME": str(home),
        "HERMES_BASE_HOME": str(home),
        "HERMES_CONFIG_PATH": str(home / "config.yaml"),
        "HERMES_WEBUI_SKIP_ONBOARDING": "1",
        "HERMES_WEBUI_AGENT_DIR": str(Path(os.environ.get("HERMES_WEBUI_AGENT_DIR") or Path.home() / ".hermes/hermes-agent")),
        "HERMES_WEBUI_DEFAULT_WORKSPACE": str(state / "workspace"),
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
        # A local password login maps to the governance bootstrap admin in the isolated state.
        "HERMES_WEBUI_PASSWORD": E2E_PASSWORD,
    })
    proc = log = page = None
    errors: list[str] = []
    code = 1
    try:
        proc, log, base_url = start_server(env, art)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(base_url=base_url, viewport={"width": 1280, "height": 900}, locale="nl-NL")
            ctx.add_init_script("try{localStorage.setItem('hermes-lang','nl');localStorage.setItem('sp-lang-explicit','nl');}catch(_){}")
            resp = ctx.request.post("/api/auth/login", data={"password": E2E_PASSWORD})
            assert resp.ok, f"login failed: {resp.status} {resp.text()[:200]}"
            page = ctx.new_page()
            # Unrelated boot features answer 403/503 in this bare state; only
            # script errors and failed teamwork requests count here.
            page.on("console", lambda m: errors.append(m.text)
                    if m.type == "error" and not m.text.startswith("Failed to load resource") else None)
            page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
            page.on("response", lambda r: errors.append(f"{r.status} {r.url}")
                    if r.status >= 400 and any(p in r.url for p in ("/api/profile/avatar", "/api/session/subagents",
                                                                        "/api/session/import", "/api/profiles")) else None)
            try:
                _drive(page, art, webui_state, errors)
            except Exception:
                try:
                    page.screenshot(path=str(art / "failure.png"), full_page=True)
                    (art / "failure-chat.txt").write_text(_chat_text(page), encoding="utf-8")
                except Exception:
                    pass
                raise
            browser.close()
        print(f"PASS  screenshots in {art}")
        code = 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL  {exc}", file=sys.stderr)
        print(f"Artifacts: {art}", file=sys.stderr)
    finally:
        _terminate_process(proc)
        if log is not None:
            log.close()
        state_tmp.cleanup()
    return code


def _drive(page, art, webui_state, errors):
    page.goto("/", wait_until="domcontentloaded")
    page.wait_for_selector("#msg", state="visible", timeout=20000)
    page.wait_for_function("() => typeof S !== 'undefined' && S._bootReady !== false && (typeof _loadingSessionId === 'undefined' || !_loadingSessionId)", timeout=30000)

    sid = page.evaluate("""async (messages) => {
        const data = await api('/api/session/import', {method: 'POST', body: JSON.stringify({
          title: 'Offertes vergelijken', messages})});
        if (!data || !data.session || !data.session.session_id) throw new Error('import failed ' + JSON.stringify(data));
        return data.session.session_id;
    }""", _transcript())
    _seed_queue(webui_state, sid)
    page.evaluate("sid => loadSession(sid)", sid)
    _wait_rendered(page)
    page.evaluate("() => _applyTheme('dark')")
    _assert_story(page, "first load")
    ok("handoff line, result card, helper chip and task row read as plain Dutch")

    # The dock: everything done, so it is folded with a calm summary.
    page.wait_for_function("() => !document.getElementById('spSubagentDock').hidden", timeout=15000)
    head = page.locator("#spSubagentDock .sp-subagent-dock-head")
    assert "Teamwerk (2)" in head.inner_text(), head.inner_text()
    assert "2 klaar" in head.inner_text(), head.inner_text()
    assert head.get_attribute("aria-expanded") == "false"
    ok("Teamwerk strip is folded once everything is done")

    # Expand the brief behind "Bekijk de opdracht".
    # The handoff that is still open (Grace takes over) keeps its line and brief.
    line = page.locator("#msgInner details.sp-handoff-task").first
    line.locator("summary").click()
    assert line.locator(".msg-body").is_visible()
    assert "customer reply" in line.locator(".msg-body").inner_text()
    line.scroll_into_view_if_needed()
    page.screenshot(path=str(art / "01-desktop-dark.png"), full_page=False)
    line.locator("summary").click()
    ok("the task opens behind 'Bekijk de opdracht'")

    # Someone starts working: the strip opens with photo and plain status.
    _seed_queue(webui_state, sid, running=True)
    page.evaluate("() => SynPulseSubagentThreads.refresh()")
    page.wait_for_function("() => document.querySelector('#spSubagentDock .sp-subagent-dock-head').getAttribute('aria-expanded') === 'true'", timeout=10000)
    dock = page.locator("#spSubagentDock")
    dock_text = dock.inner_text()
    for want in ("Teamwerk (3)", "1 aan het werk", "2 klaar", "Aan het werk", "Klaar", "Linus", "Grace"):
        assert want.lower() in dock_text.lower(), f"dock is missing {want!r}: {dock_text!r}"
    photos = page.evaluate("() => document.querySelectorAll('#spSubagentDock .sp-subagent-avatar img').length")
    assert photos == 2, photos  # both Linus rows; Grace keeps her initial
    dock.scroll_into_view_if_needed()
    dock.screenshot(path=str(art / "02-teamwerk-dark.png"))
    ok("Teamwerk strip opens while someone works, with photos and plain statuses")

    page.evaluate("() => _applyTheme('light')")
    time.sleep(0.3)
    page.locator("#msgInner .sp-bot-result").scroll_into_view_if_needed()
    page.screenshot(path=str(art / "03-desktop-light.png"), full_page=False)
    dock.screenshot(path=str(art / "04-teamwerk-light.png"))
    ok("light theme")

    # Hard reload: the same story from the stored transcript.
    page.reload(wait_until="domcontentloaded")
    page.wait_for_selector("#msg", state="visible", timeout=20000)
    if page.evaluate("() => !(S.session && S.session.session_id)"):
        page.evaluate("sid => loadSession(sid)", sid)
    _wait_rendered(page)
    _assert_story(page, "after reload")
    ok("after a hard reload the teamwork reads the same")

    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("() => _applyTheme('light')")
    time.sleep(0.6)
    _assert_story(page, "390 px")
    overflow = page.evaluate("""() => [...document.querySelectorAll('#msgInner .sp-handoff-line, #msgInner .sp-bot-result, #msgInner .sp-handoff-author')]
        .some(el => el.getBoundingClientRect().right > window.innerWidth + 1)""")
    assert overflow is False, "teamwork rows overflow at 390 px"
    page.locator("#msgInner .sp-bot-result").scroll_into_view_if_needed()
    page.screenshot(path=str(art / "05-mobile-light.png"), full_page=False)
    page.evaluate("() => _applyTheme('dark')")
    time.sleep(0.3)
    page.locator("#msgInner details.sp-handoff-task").first.scroll_into_view_if_needed()
    page.screenshot(path=str(art / "06-mobile-dark.png"), full_page=False)
    page.locator("#msgInner .msg-row:has(.sp-handoff-author)").screenshot(path=str(art / "07-mobile-dark-task.png"))
    page.locator("#spSubagentDock").scroll_into_view_if_needed()
    page.screenshot(path=str(art / "08-mobile-dark-teamwerk.png"), full_page=False)
    ok("390 px wide: no overflow, same copy")

    # Grace has no photo: the reply header (ui.js) still asks once and falls
    # back to her initial, which is expected; every other failure counts.
    unexpected = [e for e in errors if "favicon" not in e and not e.endswith("/api/profile/avatar?profile=grace-ops")]
    assert not unexpected, unexpected


if __name__ == "__main__":
    raise SystemExit(main())
