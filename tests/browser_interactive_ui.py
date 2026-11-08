"""Browser gate for interactive answers (static/interactive_ui.js).

Boots the real server.py with isolated state and a localhost Gateway fixture
that streams replies with ```interactive-ui blocks, then drives Chromium:

1. live card while the block streams (markup visible, raw source hidden);
2. settled card runs its scripts; controls work; height follows content;
3. source view, full screen (Escape from inside the frame), download, new tab;
4. a click inside the widget sends a follow-up that reaches the Gateway;
5. a theme switch reaches the frame;
6. the frame is isolated: no cookie, no same-origin fetch, no parent DOM;
7. a broken widget shows the error bar; repair sends a prompt;
8. after a hard reload the card renders again from the transcript;
9. narrow (mobile) layout.

Screenshots land in IUI_ARTIFACT_DIR (default: a temp dir, printed at the end).

    python tests/browser_interactive_ui.py
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
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_conversation_lifecycle import _terminate_process  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = Path(os.environ.get("IUI_TEMPLATES") or (Path.home() / ".hermes/skills/synthwave/interactive-ui/templates"))

CALCULATOR = (TEMPLATES / "calculator.html").read_text(encoding="utf-8") if (TEMPLATES / "calculator.html").exists() else """<!-- title: ROI van een AI-agent -->
<!-- height: 300 -->
<style>.x{color:var(--sw-accent)}</style>
<div class="card"><h3>Invoer</h3><label for="hours">Uren</label><input id="hours" type="range" min="1" max="80" value="20">
<p id="saving">EUR 0</p><button id="ask" type="button" class="primary">Vraag de agent dit scenario uit te werken</button></div>
<script>
const $=id=>document.getElementById(id);
function calc(){ $('saving').textContent='EUR '+(+$('hours').value*100); }
$('hours').addEventListener('input',calc);
$('ask').addEventListener('click',()=>synthwave.sendPrompt('Werk dit scenario uit: '+$('hours').value+' uur per week'));
calc();
</script>"""

BROKEN = """<!-- title: Kapotte weergave -->
<!-- height: 200 -->
<style>.b{color:var(--sw-bad)}</style>
<div class="card b">Deze weergave gooit een fout.</div>
<script src="https://evil.example/steal.js"></script>
<script>nietBestaandeFunctie();</script>"""

PROMPTS = [
    "Maak een ROI-calculator voor een AI-agent.",
    None,  # follow-up from the widget
    "Laat een kapotte weergave zien.",
    None,  # repair prompt
]
E2E_PASSWORD = "iui-e2e-local-only"
TAKEAWAY = "Bij deze aannames verdient de agent zichzelf binnen twee maanden terug."


class Gateway:
    """A fake OpenAI-compatible model server driven by the real Hermes engine.

    Main chat turns carry the WebUI system prompt (with the interactive answers
    block); their replies are scripted by turn number. Every other call (title,
    auxiliary) gets a short plain answer.
    """

    def __init__(self):
        self.runs = []          # user texts of main turns, in order
        self.system_prompts = []
        self.mid_stream = threading.Event()
        self.release = threading.Event()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self):
        host, port = self._server.server_address
        return f"http://{host}:{port}/v1"

    def script(self, index):
        if index == 0:
            chunks = ["Hier is een calculator om mee te spelen.\n\n```interactive-ui\n"]
            src = CALCULATOR
            step = 260
            chunks += [src[i:i + step] for i in range(0, len(src), step)]
            chunks += ["\n```\n\n" + TAKEAWAY]
            return chunks, int(len(chunks) * 0.55)
        if index == 2:
            return ["Deze is kapot:\n\n```interactive-ui\n", BROKEN, "\n```\n\nEinde."], None
        return [f"Antwoord op vervolgvraag {index}."], None

    @staticmethod
    def _text(content):
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
        return ""

    def _handler(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_a):
                return

            def _json(self, payload, status=200):
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if urlsplit(self.path).path.endswith("/models"):
                    self._json({"object": "list", "data": [{"id": "iui-fake", "object": "model", "context_length": 128000}]})
                    return
                self._json({"error": "not found"}, status=404)

            def _chunk(self, delta=None, finish=None):
                payload = {"id": "iui", "object": "chat.completion.chunk", "created": 0, "model": "iui-fake",
                           "choices": [{"index": 0, "delta": delta or {}, "finish_reason": finish}]}
                self.wfile.write(b"data: " + json.dumps(payload).encode() + b"\n\n")
                self.wfile.flush()

            def do_POST(self):
                if not urlsplit(self.path).path.endswith("/chat/completions"):
                    self._json({"error": "not found"}, status=404)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
                messages = body.get("messages") or []
                system = "\n".join(owner._text(m.get("content")) for m in messages if m.get("role") == "system")
                users = [owner._text(m.get("content")) for m in messages if m.get("role") == "user"]
                main = "WebUI interactive answers:" in system and bool(users)
                if main:
                    owner.runs.append("\n".join(users[-3:]))
                    owner.system_prompts.append(system)
                    chunks, gate = owner.script(len(owner.runs) - 1)
                else:
                    chunks, gate = ["Titel"], None
                if not body.get("stream"):
                    self._json({"id": "iui", "object": "chat.completion", "created": 0, "model": "iui-fake",
                                "choices": [{"index": 0, "message": {"role": "assistant", "content": "".join(chunks)},
                                             "finish_reason": "stop"}],
                                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    self._chunk({"role": "assistant", "content": ""})
                    for i, chunk in enumerate(chunks):
                        if gate is not None and i == gate:
                            owner.mid_stream.set()
                            if not owner.release.wait(timeout=90):
                                return
                        self._chunk({"content": chunk})
                        time.sleep(0.05)
                    self._chunk({}, "stop")
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                    self.close_connection = True
                except (BrokenPipeError, ConnectionResetError):
                    return

        return Handler

    def start(self):
        self._thread.start()

    def close(self):
        self.release.set()
        self._server.shutdown()
        self._server.server_close()


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


def ok(msg):
    print("OK  " + msg, flush=True)


def wait_runs(gateway, n, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if len(gateway.runs) >= n:
            return gateway.runs[n - 1]
        time.sleep(0.1)
    raise AssertionError(f"gateway saw {len(gateway.runs)} runs, expected {n}")


def iui_frames(page):
    return [f for f in page.frames if f.url.split("?")[0].endswith("/static/interactive-ui/frame.html")]


def last_frame(page, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        frames = iui_frames(page)
        if frames:
            return frames[-1]
        time.sleep(0.1)
    raise AssertionError("no interactive frame")


def wait_idle(page, timeout=30000):
    page.wait_for_function("() => !document.querySelector('#liveAssistantTurn')", timeout=timeout)


def main() -> int:
    from playwright.sync_api import sync_playwright

    state_tmp = tempfile.TemporaryDirectory(prefix="iui-gate-")
    state = Path(state_tmp.name)
    art = Path(os.environ.get("IUI_ARTIFACT_DIR") or tempfile.mkdtemp(prefix="iui-artifacts-"))
    art.mkdir(parents=True, exist_ok=True)
    gateway = Gateway()
    gateway.start()
    home = state / "hermes-home"
    home.mkdir()
    (state / "workspace").mkdir()
    (home / "config.yaml").write_text(
        "model:\n"
        "  default: iui-fake\n"
        "  provider: custom\n"
        f"  base_url: {gateway.base_url}\n"
        "  api_key: iui-local-only\n"
        "custom_providers:\n"
        "- name: Fake\n"
        f"  base_url: {gateway.base_url}\n"
        "  api_key: iui-local-only\n"
        "  models:\n"
        "  - iui-fake\n"
        "toolsets: []\n"
        "mcp_servers: {}\n"
        "memory:\n"
        "  memory_enabled: false\n"
        "  user_profile_enabled: false\n",
        encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    for key in ("API_SERVER_KEY", "HERMES_WEBUI_PASSWORD", "HERMES_WEBUI_EXTENSION_DIR", "HERMES_WEBUI_EXTENSION_MANIFEST",
                "HERMES_WEBUI_CHAT_BACKEND", "PYTHONPATH"):
        env.pop(key, None)
    env.update({
        "HERMES_WEBUI_HOST": "127.0.0.1",
        "HERMES_WEBUI_STATE_DIR": str(state / "webui-state"),
        "HERMES_HOME": str(home),
        "HERMES_BASE_HOME": str(home),
        "HERMES_CONFIG_PATH": str(home / "config.yaml"),
        "HERMES_WEBUI_SKIP_ONBOARDING": "1",
        "HERMES_WEBUI_AGENT_DIR": str(Path(os.environ.get("HERMES_WEBUI_AGENT_DIR") or Path.home() / ".hermes/hermes-agent")),
        "HERMES_WEBUI_DEFAULT_WORKSPACE": str(state / "workspace"),
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
        # This fork needs a signed-in identity for /api/me/*; a local password
        # login maps to the governance bootstrap admin in the isolated state.
        "HERMES_WEBUI_PASSWORD": E2E_PASSWORD,
    })
    proc = log = None
    page = None
    console_errors = []
    code = 1
    try:
        proc, log, base_url = start_server(env, art)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(base_url=base_url, viewport={"width": 1280, "height": 900}, accept_downloads=True)
            resp = ctx.request.post("/api/auth/login", data={"password": E2E_PASSWORD})
            assert resp.ok, f"login failed: {resp.status} {resp.text()[:200]}"
            page = ctx.new_page()
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: console_errors.append("pageerror: " + str(e)))
            page.goto("/", wait_until="domcontentloaded")
            page.wait_for_selector("#msg", state="visible", timeout=20000)
            page.wait_for_function("() => typeof S !== 'undefined' && S._bootReady !== false && (typeof _loadingSessionId === 'undefined' || !_loadingSessionId)", timeout=30000)
            time.sleep(1.5)

            # 0. the system prompt carries the block (checked on the first turn below)
            # 1. live card while streaming
            page.locator("#msg").fill(PROMPTS[0])
            page.locator("#btnSend").click()
            assert gateway.mid_stream.wait(timeout=60), "stream never reached the checkpoint"
            page.wait_for_function("""() => [...document.querySelectorAll('#liveAssistantTurn .iui-card.iui-live')]
                .some(c => c.offsetParent !== null)""", timeout=15000)
            live = page.locator("#liveAssistantTurn .iui-card.iui-live >> visible=true").first
            state_attr = live.get_attribute("data-state")
            assert state_attr == "building", state_attr
            raw_code_visible = page.evaluate("""() => [...document.querySelectorAll('#liveAssistantTurn pre code')]
                .some(c => /interactive-ui/.test(c.className) && c.offsetParent !== null)""")
            assert raw_code_visible is False, "raw interactive-ui source is visible while streaming"
            raw_visible = page.evaluate("""() => [...document.querySelectorAll('#liveAssistantTurn pre.iui-raw-hidden')]
                .some(p => getComputedStyle(p).display !== 'none')""")
            assert raw_visible is False, "raw source is visible while streaming"
            frame = last_frame(page)
            frame.wait_for_function("() => document.getElementById('iui-root').textContent.includes('Invoer')", timeout=10000)
            scripts_ran = frame.evaluate("() => !!document.querySelector('script[src*=chart], #iui-root script')")
            assert scripts_ran is False, "scripts must not run while streaming"
            status = live.locator(".iui-status").inner_text()
            page.screenshot(path=str(art / "01-live-streaming.png"))
            ok(f"live card while streaming (status: {status!r}), raw source hidden, no scripts yet")
            assert gateway.system_prompts and "interactive-ui" in gateway.system_prompts[0]
            ok("the engine sent the interactive answers block in the system prompt")

            # 2. settled card
            gateway.release.set()
            wait_idle(page)
            page.wait_for_selector(".msg-row .iui-card[data-state=ready]", timeout=20000)
            assert page.locator(".iui-card").count() == 1, "exactly one card after settling"
            assert TAKEAWAY in page.inner_text("#messages"), "takeaway text missing"
            frame = last_frame(page)
            frame.wait_for_selector("#saving", timeout=10000)
            before = frame.inner_text("#saving")
            frame.evaluate("() => { const h=document.getElementById('hours'); h.value='60'; h.dispatchEvent(new Event('input',{bubbles:true})); }")
            after = frame.inner_text("#saving")
            assert before != after, (before, after)
            stage_h = page.evaluate("() => document.querySelector('.iui-card .iui-stage').getBoundingClientRect().height")
            content_h = frame.evaluate("() => document.body.scrollHeight")
            assert stage_h >= 200 and abs(stage_h - min(content_h, 900 * 0.86)) < 40, (stage_h, content_h)
            title = page.inner_text(".iui-card .iui-title")
            page.locator(".iui-card").scroll_into_view_if_needed()
            page.locator(".iui-card").screenshot(path=str(art / "02-settled-card.png"))
            ok(f"settled card {title!r}: scripts ran, slider changed {before!r} to {after!r}, stage {stage_h:.0f}px for {content_h}px content")

            # 3a. source view
            page.locator(".iui-card .iui-actions button").nth(0).click()
            assert page.is_visible(".iui-card .iui-source"), "source view did not open"
            assert "interactive" not in page.inner_text(".iui-card .iui-source").lower()[:5]
            assert "<style>" in page.inner_text(".iui-card .iui-source")
            page.locator(".iui-card .iui-actions button").nth(0).click()
            ok("source view toggles")
            # 3b. full screen, closed with Escape pressed inside the frame
            page.locator(".iui-card .iui-actions button").nth(5).click()
            assert page.evaluate("() => document.querySelector('.iui-card').classList.contains('iui-full')")
            page.screenshot(path=str(art / "03-fullscreen.png"))
            last_frame(page).locator("#iui-root").click(position={"x": 5, "y": 5})
            page.keyboard.press("Escape")
            page.wait_for_function("() => !document.querySelector('.iui-card').classList.contains('iui-full')", timeout=5000)
            ok("full screen opens and closes with Escape from inside the frame")
            # 3c. download
            with page.expect_download() as dl:
                page.locator(".iui-card .iui-actions button").nth(3).click()
            html = Path(dl.value.path()).read_text(encoding="utf-8")
            assert 'id="iui-root"' in html and "Invoer" in html and "synthwave" in html, html[:300]
            ok(f"download gives a standalone HTML file ({dl.value.suggested_filename}, {len(html)} bytes)")
            # 3d. new tab
            with ctx.expect_page() as pop:
                page.locator(".iui-card .iui-actions button").nth(4).click()
            tab = pop.value
            tab.wait_for_selector("#saving", timeout=15000)
            tab_cookie = tab.evaluate("() => { try { return document.cookie; } catch (e) { return 'blocked:' + e.name; } }")
            assert tab_cookie in ("", "blocked:SecurityError"), tab_cookie
            tab.screenshot(path=str(art / "04-new-tab.png"))
            tab.close()
            ok(f"new tab renders the widget in an opaque origin (cookie: {tab_cookie!r})")

            # 4. follow-up from a click inside the widget
            frame = last_frame(page)
            frame.locator("#ask").click()
            body = wait_runs(gateway, 2)
            assert "Werk dit scenario uit" in body, body
            wait_idle(page)
            page.wait_for_function("() => document.getElementById('messages').innerText.includes('Antwoord op vervolgvraag 1')", timeout=20000)
            ok("a click in the widget sends the follow-up to the agent")

            # 4b. a script-triggered prompt without user interaction is refused.
            # The list re-rendered for the new turn; frames load lazily when on screen.
            page.locator(".iui-card").first.scroll_into_view_if_needed()
            page.wait_for_selector(".iui-card[data-state=ready]", timeout=15000)
            frame = last_frame(page)
            frame.wait_for_selector("#saving", timeout=10000)
            page.locator("#msg").click()
            time.sleep(5.2)  # outside the interaction window
            frame.evaluate("() => synthwave.sendPrompt('automatisch zonder klik')")
            time.sleep(1.0)
            assert len(gateway.runs) == 2, "an automatic prompt must not be sent"
            ok("a prompt without a user click is refused")

            # 5. theme switch reaches the frame
            page.evaluate("() => _applyTheme('light')")
            frame.wait_for_function("() => document.documentElement.getAttribute('data-theme') === 'light'", timeout=5000)
            page.locator(".iui-card").first.screenshot(path=str(art / "05-light-theme.png"))
            page.evaluate("() => _applyTheme('dark')")
            frame.wait_for_function("() => document.documentElement.getAttribute('data-theme') === 'dark'", timeout=5000)
            ok("theme switches follow into the frame (light and back to dark)")

            # 6. isolation
            iso = frame.evaluate("""async () => {
                const out = {cookie: null, fetch: null, parent: null, storage: null};
                try { out.cookie = document.cookie; } catch (e) { out.cookie = 'blocked:' + e.name; }
                try { await fetch('/api/sessions'); out.fetch = 'allowed'; } catch (e) { out.fetch = 'blocked'; }
                try { out.parent = String(window.parent.document.title); } catch (e) { out.parent = 'blocked'; }
                try { localStorage.setItem('x', '1'); out.storage = 'allowed'; } catch (e) { out.storage = 'blocked'; }
                return out;
            }""")
            assert iso["fetch"] == "blocked" and iso["parent"] == "blocked" and iso["storage"] == "blocked", iso
            assert iso["cookie"] in ("", "blocked:SecurityError"), iso
            ok(f"frame is isolated: {iso}")

            # 7. broken widget and repair
            page.locator("#msg").fill(PROMPTS[2])
            page.locator("#btnSend").click()
            wait_runs(gateway, 3)
            wait_idle(page)
            page.wait_for_selector(".iui-card[data-state=error] .iui-error:not([hidden])", timeout=20000)
            err_text = page.locator(".iui-card[data-state=error] .iui-error-text").last.inner_text()
            assert "nietBestaandeFunctie" in err_text or "toegestane" in err_text, err_text
            page.locator(".iui-card[data-state=error]").last.screenshot(path=str(art / "06-error-bar.png"))
            page.locator(".iui-card[data-state=error] .iui-error .iui-btn--text").last.click()
            body = wait_runs(gateway, 4)
            assert ("herstel" in body.lower() or "fix it" in body.lower()) and "nietBestaandeFunctie" in body, body
            wait_idle(page)
            ok(f"broken widget shows the error ({err_text[:80]!r}) and repair asks the agent")

            # 8. hard reload renders the cards again from the transcript
            page.reload(wait_until="domcontentloaded")
            try:
                page.wait_for_function("t => document.getElementById('messages') && document.getElementById('messages').innerText.includes(t)",
                                       arg=TAKEAWAY, timeout=20000)
            finally:
                page.screenshot(path=str(art / "08-after-reload.png"))
                info = page.evaluate("""() => ({blocks: document.querySelectorAll('.iui-block').length,
                    cards: document.querySelectorAll('.iui-card').length,
                    pre: [...document.querySelectorAll('#messages pre code')].map(c => c.className).slice(0, 5),
                    raw: (document.getElementById('messages')||{}).innerText ? document.getElementById('messages').innerText.slice(0, 300) : ''})""")
                print("reload state:", info, flush=True)
            page.wait_for_selector(".iui-card", timeout=20000)
            page.wait_for_function("() => document.querySelectorAll('.iui-card').length >= 2", timeout=20000)
            page.locator(".iui-card").first.scroll_into_view_if_needed()
            page.wait_for_selector(".iui-card[data-state=ready]", timeout=20000)
            ok(f"after reload {page.locator('.iui-card').count()} cards render again from the transcript")

            # 9. narrow layout
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator(".iui-card").first.scroll_into_view_if_needed()
            time.sleep(0.8)
            overflow = page.evaluate("() => { const c=document.querySelector('.iui-card'); return c.scrollWidth - c.clientWidth; }")
            assert overflow <= 1, f"card overflows horizontally by {overflow}px"
            page.screenshot(path=str(art / "07-mobile.png"))
            ok("narrow layout fits without horizontal overflow")

            unexpected = [e for e in console_errors if not any(s in e for s in (
                "nietBestaandeFunctie", "evil.example", "favicon", "manifest", "sw.js", "serviceworker", "Content Security Policy",
                "Failed to load resource"))]
            assert not unexpected, unexpected
            ok(f"no unexpected console errors ({len(console_errors)} expected widget errors filtered)")
            browser.close()
        code = 0
        print(f"PASS  screenshots in {art}")
    except Exception as exc:  # noqa: BLE001
        try:
            page.screenshot(path=str(art / "failure.png"))
        except Exception:
            pass
        print(f"FAIL  {exc}", file=sys.stderr)
        print(f"artifacts in {art}; console errors: {console_errors[-8:]}", file=sys.stderr)
    finally:
        gateway.close()
        _terminate_process(proc)
        if log:
            log.close()
        state_tmp.cleanup()
    return code


if __name__ == "__main__":
    sys.exit(main())
