#!/usr/bin/env python3
"""Visual QA fixture: a turn with many tool calls and two delegated workers.

Boots the real WebUI server from this checkout with isolated state on a free
port, feeds it a deterministic Gateway Runs stream (no model, no credentials)
and saves screenshots of the live turn, the settled turn and the turn after a
hard reload, in light and dark theme.

    python tests/browser_friendly_tools_screens.py --out .screens/after

Not collected by pytest (no ``test_`` prefix). It never touches a running
WebUI instance.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import browser_conversation_lifecycle as lifecycle  # noqa: E402

PROMPT = "Check the repo, fix the README and let two helpers review it."
FINAL_TEXT = "Done. The README is fixed and both reviews are in."

TOOLS = [
    ("terminal", {"command": "cd ~/repo && git status --short && git log --oneline -5"}, "M README.md\n?? notes.txt"),
    ("read_file", {"path": "/home/user/repo/README.md", "offset": 1, "limit": 80}, "# Project\nSetup steps..."),
    ("search_files", {"pattern": "TODO", "path": "/home/user/repo", "target": "content"}, "3 matches"),
    ("terminal", {"command": "python3 -m pytest -q tests/test_readme.py"}, "4 passed in 0.31s"),
    ("patch", {"path": "/home/user/repo/README.md", "old_string": "teh", "new_string": "the"}, "@@ -1 +1 @@\n-teh\n+the"),
    ("web_search", {"query": "markdown table syntax"}, "Top result: GitHub docs"),
    ("terminal", {"command": "npm run lint -- --fix"}, "error: 2 problems"),
    ("delegate_task", {"tasks": "[{'goal': 'Review the README wording'}, {'goal': 'Check links in the README'}]"}, "Dispatched 2 subagents"),
]
SUBAGENTS = [
    {"id": "sa-0-fixture01", "summary": "Review the README wording for clarity", "task_index": 0, "task_count": 2},
    {"id": "sa-1-fixture02", "summary": "Check every link in the README", "task_index": 1, "task_count": 2},
]
CHILD_TOOLS = [
    ("sa-0-fixture01", "read_file", "README.md"),
    ("sa-0-fixture01", "search_files", "TODO"),
    ("sa-1-fixture02", "web_extract", "https://example.com/docs"),
    ("sa-1-fixture02", "terminal", "curl -sI https://example.com"),
    ("sa-0-fixture01", "write_file", "review-notes.md"),
]


class FixtureGateway:
    def __init__(self) -> None:
        self.live_ready = threading.Event()
        self.release = threading.Event()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def _handler(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args):
                return

            def _json(self, payload, status=200):
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _event(self, payload):
                frame = f"event: {payload['event']}\ndata: {json.dumps(payload)}\n\n".encode()
                self.wfile.write(frame)
                self.wfile.flush()
                time.sleep(0.05)

            def do_GET(self):
                path = urlsplit(self.path).path
                if path == "/v1/capabilities":
                    self._json({"features": {"approval_events": True, "run_approval_response": True}})
                    return
                if path != "/v1/runs/friendly-run-1/events":
                    print("FIXTURE 404", self.command, self.path, file=sys.stderr)
                    self._json({"error": "not found"}, status=404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    self._event({"event": "reasoning.available", "text": "Looking at the repository first."})
                    for i, (name, args, out) in enumerate(TOOLS):
                        tid = f"fx-tool-{i}"
                        self._event({"event": "tool.started", "tool": name, "tool_call_id": tid, "status": "running", "args": args})
                        status = "error" if "error" in out else "completed"
                        self._event({"event": "tool.completed", "tool": name, "tool_call_id": tid, "status": status,
                                     "preview": out, "args": args})
                    for sa in SUBAGENTS:
                        self._event({"event": "subagent", **sa, "status": "queued", "tool_count": 0})
                        self._event({"event": "subagent", **sa, "status": "running", "tool_count": 0})
                    counts = {}
                    for sid, tool, preview in CHILD_TOOLS:
                        counts[sid] = counts.get(sid, 0) + 1
                        sa = next(s for s in SUBAGENTS if s["id"] == sid)
                        self._event({"event": "subagent", **sa, "status": "running", "tool_count": counts[sid],
                                     "last_tool": tool, "last_preview": preview})
                    # Hold a still-running terminal call so the live view has a spinner.
                    self._event({"event": "tool.started", "tool": "terminal", "tool_call_id": "fx-live",
                                 "status": "running", "args": {"command": "sleep 5 && echo ok"}})
                    owner.live_ready.set()
                    if not owner.release.wait(timeout=120):
                        return
                    self._event({"event": "tool.completed", "tool": "terminal", "tool_call_id": "fx-live",
                                 "status": "completed", "preview": "ok"})
                    self._event({"event": "subagent", **SUBAGENTS[0], "status": "completed",
                                 "tool_count": counts.get(SUBAGENTS[0]["id"], 0), "duration_seconds": 42.5})
                    self._event({"event": "subagent", **SUBAGENTS[1], "status": "failed",
                                 "tool_count": counts.get(SUBAGENTS[1]["id"], 0), "duration_seconds": 17.0})
                    self._event({"event": "message.delta", "delta": FINAL_TEXT})
                    self._event({"event": "run.completed", "usage": {"input_tokens": 10, "output_tokens": 9}})
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return

            def do_POST(self):
                if urlsplit(self.path).path != "/v1/runs":
                    print("FIXTURE 404", self.command, self.path, file=sys.stderr)
                    self._json({"error": "not found"}, status=404)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(length)
                self._json({"run_id": "friendly-run-1"})

        return Handler

    def start(self):
        self._thread.start()

    def close(self):
        self.release.set()
        self._server.shutdown()
        self._server.server_close()


def _expand_all(page):
    """Open collapsed activity like a user would: click each closed toggle."""
    for _ in range(3):
        page.evaluate("""() => {
          const closed = Array.from(document.querySelectorAll(
            '#messages button[aria-expanded="false"].activity-summary, '
            + '#messages button[aria-expanded="false"].tool-worklog-tool-group-head, '
            + '#messages button[aria-expanded="false"].sp-steps-head'));
          closed.forEach(btn => btn.click());
        }""")
        page.wait_for_timeout(300)


def _shot(page, out: Path, name: str):
    page.wait_for_timeout(400)
    target = page.locator("#messages")
    path = out / f"{name}.png"
    try:
        target.screenshot(path=str(path))
    except Exception:
        page.screenshot(path=str(path), full_page=False)
    print("saved", path)


def run(theme: str, out: Path, repo_root: Path, engine_tools: Path | None) -> int:
    gateway = FixtureGateway()
    gateway.start()
    state_tmp = tempfile.TemporaryDirectory(prefix="hermes-friendly-tools-")
    state_dir = Path(state_tmp.name)
    agent_dir = state_dir / "no-agent"
    (agent_dir / "tools").mkdir(parents=True)
    (agent_dir / "run_agent.py").write_text('"""stub"""\n')
    (agent_dir / "tools" / "__init__.py").write_text("")
    if engine_tools and (engine_tools / "delegation_progress.py").exists():
        shutil.copy(engine_tools / "delegation_progress.py", agent_dir / "tools" / "delegation_progress.py")
    workspace = state_dir / "workspace"
    workspace.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    for key in ("API_SERVER_KEY", "HERMES_WEBUI_PASSWORD", "HERMES_WEBUI_EXTENSION_DIR", "HERMES_WEBUI_EXTENSION_MANIFEST"):
        env.pop(key, None)
    env.update({
        "HERMES_WEBUI_HOST": "127.0.0.1",
        "HERMES_WEBUI_STATE_DIR": str(state_dir / "webui-state"),
        "HERMES_HOME": str(state_dir / "hermes-home"),
        "HERMES_BASE_HOME": str(state_dir / "hermes-home"),
        "HERMES_CONFIG_PATH": str(state_dir / "hermes-home" / "config.yaml"),
        "HERMES_WEBUI_SKIP_ONBOARDING": "1",
        "HERMES_WEBUI_AGENT_DIR": str(agent_dir),
        "HERMES_WEBUI_DEFAULT_WORKSPACE": str(workspace),
        "HERMES_WEBUI_CHAT_BACKEND": "gateway",
        "HERMES_WEBUI_GATEWAY_BASE_URL": gateway.base_url,
        "HERMES_WEBUI_GATEWAY_USE_RUNS_API": "1",
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
    })
    from playwright.sync_api import sync_playwright
    proc = log = None
    try:
        proc, log, log_path, base_url = lifecycle._start_webui_server(repo_root, env, state_dir)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            ctx = browser.new_context(base_url=base_url, viewport={"width": 1280, "height": 1500},
                                      locale="nl-NL", color_scheme=theme)
            ctx.add_init_script(f"try{{localStorage.setItem('hermes-theme','{theme}');}}catch(e){{}}")
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto("/", wait_until="domcontentloaded")
            page.wait_for_selector("#msg", state="visible", timeout=20000)
            page.locator("#msg").fill(PROMPT)
            page.locator("#btnSend").click()
            if not gateway.live_ready.wait(timeout=60):
                print("gateway never reached live state", file=sys.stderr)
                page.screenshot(path=str(out / f"{theme}-debug.png"))
                return 1
            page.wait_for_timeout(2500)
            _shot(page, out, f"{theme}-1-live")
            gateway.release.set()
            page.wait_for_function(f"() => document.body.innerText.includes({json.dumps(FINAL_TEXT)})", timeout=30000)
            page.wait_for_timeout(2500)
            _shot(page, out, f"{theme}-2-settled")
            _expand_all(page)
            _shot(page, out, f"{theme}-3-settled-expanded")
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function(f"() => document.body.innerText.includes({json.dumps(FINAL_TEXT)})", timeout=30000)
            page.wait_for_timeout(3000)
            _shot(page, out, f"{theme}-4-reloaded")
            _expand_all(page)
            _shot(page, out, f"{theme}-5-reloaded-expanded")
            page.evaluate("""() => document.querySelectorAll('[data-sp-subagent-toggle]').forEach(b => b.click())""")
            page.wait_for_timeout(300)
            dock = page.locator("#spSubagentDock")
            if dock.count() and dock.is_visible():
                dock.screenshot(path=str(out / f"{theme}-6-subagent-cards-open.png"))
                print("saved", out / f"{theme}-6-subagent-cards-open.png")
            if errors:
                print("page errors:", errors)
            browser.close()
        return 0
    finally:
        gateway.close()
        lifecycle._terminate_process(proc)
        if log:
            log.close()
            for lp in state_dir.glob("server*.log"):
                (out / f"{theme}-{lp.name}").write_text(lp.read_text(errors="replace")[-4000:])
        state_tmp.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=".screens")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--engine-tools", default=os.path.expanduser("~/.hermes/hermes-agent/tools"))
    parser.add_argument("--themes", default="light,dark")
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rc = 0
    for theme in args.themes.split(","):
        rc |= run(theme.strip(), out, Path(args.repo).resolve(), Path(args.engine_tools))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
