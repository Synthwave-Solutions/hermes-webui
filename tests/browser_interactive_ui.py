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
9. narrow (mobile) layout;
10. data blocks (```table, ```csv, ```chart, ```map, ```kpi, ```timeline) in
    the kit frame: sorting, search, "Toon alle", CSV export, the chart/table
    switch kept over a reload, map pins and route, the unresolved group, the
    status line without moving the chat, the note when tiles do not load, KPI
    tiles with delta colours and a target bar, a Gantt with status colours,
    milestones, the today line, click and keyboard details, and the stacked
    list at 390 px. Map tiles and Wikimedia are stubbed with page.route and the
    geocoder is off: no network.

Screenshots land in IUI_ARTIFACT_DIR (default: a temp dir, printed at the end).

    python tests/browser_interactive_ui.py
"""

from __future__ import annotations

import json
import os
import re
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

# ── Data block fixtures (step 10) ───────────────────────────────────────────
_NAMES = ["Jansen", "De Vries", "Bakker", "Visser", "Smit", "Meijer", "Mulder", "Bos", "Vos", "Peters",
          "Hendriks", "Dekker", "Brouwer", "Dijkstra", "Kok", "Jacobs"]
TABLE_ROWS = [[f"{_NAMES[i % len(_NAMES)]} {i + 1:02d} Bouw",
               1000 + (i * 7919) % 9000, round(((i * 37) % 41) - 12 + 0.5, 1),
               ["Actief", "Pauze", "Nieuw"][i % 3]] for i in range(60)]
TABLE_SPEC = {"title": "Omzet per klant", "subtitle": "Laatste twaalf maanden", "source": "Uit het CRM",
              "columns": ["Klant", {"label": "Omzet", "type": "currency"}, {"label": "Groei", "type": "percent"},
                          {"label": "Status", "type": "status"}],
              "rows": TABLE_ROWS, "total": True, "tones": {"Actief": "good", "Pauze": "warn", "Nieuw": "info"}}
CSV_BLOCK = 'Naam;Plaats;Bedrag\n"Jansen; Zonen";Utrecht;"1.234,50"\n"De ""Gouden"" Leeuw";Amsterdam;980\nVan Dijk;Den Haag;2.100\n'
CHART_SPEC = {"type": "bar", "title": "Omzet per maand", "labels": ["Jan", "Feb", "Mrt", "Apr", "Mei", "Jun"],
              "series": [{"name": "Omzet", "data": [42000, 45500, 61000, 48000, 51000, 53500]}],
              "format": "currency", "highlight": "Mrt", "target": {"value": 50000, "label": "Doel"}, "source": "Boekhouding"}
MAP_SPEC = {"title": "Bezoekroute Amsterdam", "kind": "route", "subtitle": "Vrijdag", "places": [
    {"name": "Rijksmuseum", "address": "Museumstraat 1, Amsterdam", "lat": 52.36, "lng": 4.8852, "time": "09:30", "note": "Start bij de ingang"},
    {"name": "Anne Frank Huis", "lat": 52.3752, "lng": 4.884, "time": "11:30"},
    {"name": "De Dam", "lat": 52.3731, "lng": 4.8926, "time": "13:00"},
    {"name": "Kantoor Haarlem", "address": "Stationsplein 1, Haarlem", "time": "15:00"},
]}
KPI_SPEC = {"title": "Kerncijfers oktober", "lang": "nl", "source": "Boekhouding", "items": [
    {"label": "MRR", "value": 18400, "format": "currency", "delta": 12.5, "target": 20000, "note": "t.o.v. september"},
    {"label": "Churn", "value": 2.1, "format": "percent", "delta": 0.4, "good": "down"},
    {"label": "Kosten", "value": 9100, "format": "currency", "delta": -800, "deltaFormat": "number", "good": "down"},
    {"label": "Conversie", "value": 3.4, "format": "percent", "delta": 0},
]}
TIMELINE_SPEC = {"title": "Uitrol Junior AI", "lang": "nl", "unit": "week", "start": "2026-11-09", "today": 3, "source": "Projectplan", "items": [
    {"label": "Kick-off", "start": 1, "milestone": True, "owner": "Michaël"},
    {"label": "Ontwerp", "start": 1, "end": 2, "status": "done", "owner": "Yaser"},
    {"label": "Bouw", "start": 2, "end": 5, "status": "doing", "owner": "Senna", "note": "Twee sprints"},
    {"label": "Acceptatietest", "start": 6, "end": 7, "status": "risk", "owner": "Klant"},
    {"label": "Training", "start": 7, "end": 7, "status": "todo"},
    {"label": "Live", "start": 8, "milestone": True, "status": "todo"},
]}
DATA_TURNS = {
    "[tabel]": ["Hier zijn de klanten.\n\n```table\n", json.dumps(TABLE_SPEC, ensure_ascii=False, indent=1), "\n```\n\nBos 08 groeit het hardst."],
    "[csv]": ["Als CSV:\n\n```csv\n", CSV_BLOCK, "```\n\nEn als code:\n\n```chart\nnew Chart(ctx, {type: 'bar'});\n```\n"],
    "[grafiek]": ["De omzet per maand:\n\n```chart\n", json.dumps(CHART_SPEC, ensure_ascii=False), "\n```\n\nMaart sprong eruit."],
    "[kaart]": ["Je route:\n\n```map\n", json.dumps(MAP_SPEC, ensure_ascii=False), "\n```\n\nDrie stops liggen dicht bij elkaar."],
    "[kpi]": ["De cijfers van oktober:\n\n```kpi\n", json.dumps(KPI_SPEC, ensure_ascii=False), "\n```\n\nDe MRR groeit, de churn loopt op."],
    "[planning]": ["De planning:\n\n```timeline\n", json.dumps(TIMELINE_SPEC, ensure_ascii=False, indent=1), "\n```\n\nDe acceptatietest is het risico."],
}

# A theme colour as the browser resolves it (for comparing computed colours).
PROBE = "v => { const e=document.createElement('span'); e.style.color='var('+v+')'; document.body.appendChild(e); const c=getComputedStyle(e).color; e.remove(); return c; }"


def _png(width=256, height=256, rgb=(226, 230, 236)):
    """A plain PNG for stubbed map tiles and photos."""
    import struct
    import zlib
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


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
        if index == 3:
            return [f"Antwoord op vervolgvraag {index}.\n\n```suggestions\n", "Toon het in een grafiek\nMaak het compacter\n```"], None
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
                    # The newest marker in the user's own words (recalled memory is left out).
                    last = re.sub(r"<memory-context>[\s\S]*?</memory-context>", "", users[-1] if users else "")
                    marker = max((m for m in DATA_TURNS if m in last), key=last.rfind, default=None)
                    chunks, gate = (list(DATA_TURNS[marker]), None) if marker else owner.script(len(owner.runs) - 1)
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


def menu_action(page, label_nl, label_en, card=".iui-card"):
    page.locator(card + " .iui-actions button[aria-haspopup=menu]").first.click()
    item = page.locator(card + " .iui-menu:not([hidden]) .iui-menu-item", has_text=label_nl)
    if item.count() == 0:
        item = page.locator(card + " .iui-menu:not([hidden]) .iui-menu-item", has_text=label_en)
    item.first.click()


def wait_idle(page, timeout=30000):
    page.wait_for_function("() => !document.querySelector('#liveAssistantTurn')", timeout=timeout)


# The newest card of a kind has drawn (older cards mount lazily when scrolled to).
LAST_READY = "k => { const c=[...document.querySelectorAll('.iui-card.iui-kit--'+k)].pop(); return !!c && c.dataset.state === 'ready'; }"


def bring_ready(page, kind, timeout=30, first=False):
    """Scroll the newest (or first) card of a kind into view until it has
    drawn (the chat may still be settling its scroll position after a reload)."""
    deadline = time.time() + timeout
    cards = page.locator(f".iui-card.iui-kit--{kind}")
    card = cards.first if first else cards.last
    check = ("k => { const c=document.querySelector('.iui-card.iui-kit--'+k); return !!c && c.dataset.state === 'ready'; }"
             if first else LAST_READY)
    while time.time() < deadline:
        try:
            card.scroll_into_view_if_needed(timeout=2000)
            if page.evaluate(check, kind):
                return card
        except Exception:
            pass
        time.sleep(0.4)
    raise AssertionError(f"the {kind} card did not draw")


def kit_frames(page):
    return [f for f in page.frames if f.url.split("?")[0].endswith("/static/interactive-ui/kit.html")]


def kit_frame_for(page, card, timeout=15):
    """The kit frame inside one card (matched through its iframe element)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        handle = card.locator("iframe.iui-frame").element_handle(timeout=2000)
        frame = handle.content_frame() if handle else None
        if frame and frame.url.split("?")[0].endswith("/static/interactive-ui/kit.html"):
            return frame
        time.sleep(0.1)
    raise AssertionError("no kit frame in the card")


def send_turn(page, gateway, text, n, done_text):
    page.locator("#msg").fill(text)
    page.locator("#btnSend").click()
    wait_runs(gateway, n)
    page.wait_for_function("t => { const m=document.getElementById('messages'); return !!m && m.innerText.includes(t) && !document.querySelector('#liveAssistantTurn'); }",
                           arg=done_text, timeout=30000)
    time.sleep(2.0)  # the chat re-renders the settled turn once more


def data_blocks(page, ctx, gateway, art, base_runs):
    """Step 10: data blocks drawn by the kit frame from JSON or CSV."""
    tile = _png()
    photo = _png(64, 64, (180, 190, 200))
    state = {"tiles": "stub"}

    def tiles(route):
        if state["tiles"] == "block":
            route.abort()
        else:
            route.fulfill(status=200, body=tile, headers={"Content-Type": "image/png", "Cache-Control": "no-store"})
    ctx.route("https://tile.openstreetmap.org/**", tiles)
    if os.environ.get("IUI_REAL_TILES") != "1":  # set it to look at the real map tiles
        ctx.route("**/static/interactive-ui/tiles/**", tiles)  # tiles come from this server now
    ctx.route("https://upload.wikimedia.org/**", lambda r: r.fulfill(status=200, body=photo, headers={"Content-Type": "image/png"}))
    page.set_viewport_size({"width": 1280, "height": 900})
    # Data blocks speak the chat's language; check the Dutch copy (saved, so it survives the reload).
    page.evaluate("""async () => {
        await api('/api/settings', {method: 'POST', body: JSON.stringify({language: 'nl'})});
        if (typeof setLocale === 'function') await setLocale('nl');
    }""")
    page.wait_for_function("() => (document.documentElement.lang || '').toLowerCase().startsWith('nl')", timeout=10000)
    runs = base_runs

    # 10a. table: 60 rows, first 50 shown, sort, search, CSV export
    runs += 1
    send_turn(page, gateway, "Laat de klanten zien als tabel [tabel]", runs, "Bos 08 groeit het hardst.")
    card = page.locator(".iui-card.iui-kit--table:visible").last
    card.wait_for(timeout=20000)
    page.wait_for_function(LAST_READY, arg="table", timeout=30000)
    assert card.locator(".iui-title").inner_text() == TABLE_SPEC["title"]
    frame = kit_frame_for(page, card)
    frame.wait_for_selector(".k-grid tbody tr", timeout=10000)
    assert frame.locator(".k-grid tbody tr").count() == 50
    more = frame.locator(".k-more")
    assert more.inner_text() == "Toon alle 60 rijen", more.inner_text()
    by_revenue = sorted(TABLE_ROWS, key=lambda r: r[1])
    frame.locator("th:nth-child(2) .k-sort").click()
    assert frame.locator("th:nth-child(2)").get_attribute("aria-sort") == "ascending"
    assert frame.locator(".k-grid tbody tr:first-child th").inner_text() == by_revenue[0][0]
    frame.locator("th:nth-child(2) .k-sort").click()
    assert frame.locator("th:nth-child(2)").get_attribute("aria-sort") == "descending"
    assert frame.locator(".k-grid tbody tr:first-child th").inner_text() == by_revenue[-1][0]
    first_num = frame.locator(".k-grid tbody tr:first-child td.num").first.inner_text()
    assert first_num.startswith("€") and "." in first_num, first_num
    more.click()
    assert frame.locator(".k-grid tbody tr").count() == 60 and frame.locator(".k-more").is_hidden()
    assert frame.locator(".k-grid tfoot th").inner_text() == "Totaal"
    page.locator(".iui-card.iui-kit--table:visible").last.scroll_into_view_if_needed()
    card.screenshot(path=str(art / "10-table-desktop-dark.png"))
    frame.locator(".k-search").fill("jansen")
    frame.wait_for_function("() => document.querySelectorAll('.k-grid tbody tr').length === 4", timeout=5000)
    names = frame.locator(".k-grid tbody tr th").all_inner_texts()
    assert all("Jansen" in n for n in names), names
    assert frame.locator(".k-count").inner_text() == "4 van 60 rijen"
    time.sleep(0.5)  # the view is saved after a short debounce
    with page.expect_download() as dl:
        menu_action(page, "Download als CSV", "Download as CSV", card=".iui-card.iui-kit--table")
    raw = Path(dl.value.path()).read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), raw[:10]
    lines = raw.decode("utf-8-sig").splitlines()
    assert lines[0] == "Klant;Omzet;Groei;Status", lines[0]
    assert len(lines) == 5 and all("Jansen" in line for line in lines[1:]), lines
    assert dl.value.suggested_filename == "omzet-per-klant.csv", dl.value.suggested_filename
    ok(f"table: 50 of 60 rows, sort up and down, 'Toon alle', search (4 van 60), CSV with BOM and ';' ({len(lines) - 1} rows as filtered)")

    # 10b. csv with quotes; a ```chart holding code stays a code block
    runs += 1
    send_turn(page, gateway, "En als CSV [csv]", runs, "En als code:")
    page.wait_for_function("() => document.querySelectorAll('.iui-card.iui-kit--table').length >= 2", timeout=20000)
    card = page.locator(".iui-card.iui-kit--table:visible").last
    card.scroll_into_view_if_needed()
    page.wait_for_function(LAST_READY, arg="table", timeout=30000)
    frame = kit_frame_for(page, card)
    frame.wait_for_selector(".k-grid tbody tr", timeout=10000)
    heads = [t.strip() for t in frame.locator(".k-grid thead th").all_inner_texts()]
    assert heads == ["Naam", "Plaats", "Bedrag"], heads
    first = frame.locator(".k-grid tbody tr").first.locator("th, td").all_inner_texts()
    second = frame.locator(".k-grid tbody tr").nth(1).locator("th, td").all_inner_texts()
    assert first[0] == "Jansen; Zonen" and first[2] == "1.234,5", first
    assert second[0] == 'De "Gouden" Leeuw', second
    code_block = page.locator(".msg-row pre code.language-chart:visible").last
    assert "new Chart" in code_block.inner_text()
    ok(f"csv: quoted ';' and doubled quotes parsed ({first[0]!r}, {second[0]!r}); a ```chart with code stays a code block")

    # 10c. chart with highlight; the table view is kept over a reload
    runs += 1
    send_turn(page, gateway, "Maak er een grafiek van [grafiek]", runs, "Maart sprong eruit.")
    page.wait_for_function(LAST_READY, arg="chart", timeout=30000)
    card = page.locator(".iui-card.iui-kit--chart:visible").last
    frame = kit_frame_for(page, card)
    frame.wait_for_function("() => { const c=document.querySelector('.k-canvas canvas'); return c && c.width > 100 && !document.querySelector('.k-canvas').hidden; }", timeout=10000)
    assert frame.locator(".k-seg button[aria-pressed=true]").inner_text() == "Grafiek"
    assert frame.locator(".k-note").is_hidden(), "the chart must draw without the fallback note"
    card.scroll_into_view_if_needed()
    time.sleep(0.7)  # let the bars settle
    card.screenshot(path=str(art / "11-chart-desktop-dark.png"))
    frame.locator(".k-seg button", has_text="Tabel").click()
    assert frame.locator(".k-chart-table").is_visible() and frame.locator(".k-canvas").is_hidden()
    assert "61.000" in frame.locator(".k-chart-table").inner_text()
    frame.locator(".k-seg button", has_text="Grafiek").click()
    assert frame.locator(".k-canvas").is_visible()
    frame.locator(".k-seg button", has_text="Tabel").click()
    time.sleep(0.6)
    ok("chart: drawn with highlight and target; 'Grafiek | Tabel' switches both ways")

    # 10d. map: three pins and a route from given coordinates, one address unresolved (geocoder off)
    runs += 1
    send_turn(page, gateway, "Zet de bezoeken op de kaart [kaart]", runs, "Drie stops liggen dicht bij elkaar.")
    page.wait_for_function(LAST_READY, arg="map", timeout=30000)
    card = page.locator(".iui-card.iui-kit--map:visible").last
    frame = kit_frame_for(page, card)
    frame.wait_for_function("() => document.querySelectorAll('.sw-pin').length === 3", timeout=10000)
    assert frame.locator("path.sw-route").count() == 1
    frame.wait_for_selector(".k-map.is-played", timeout=5000)
    missing = frame.locator(".k-missing").inner_text()
    assert "Niet op de kaart gevonden" in missing and "Kantoor Haarlem" in missing, missing
    assert frame.locator(".k-items li").count() == 3
    assert "De lijn toont alleen de volgorde" in frame.locator(".k-notes").inner_text()
    assert frame.locator(".k-chip").count() == 0, "the numbered list already shows how many places there are"
    assert frame.locator(".k-action", has_text="Opnieuw afspelen").count() == 0
    card.scroll_into_view_if_needed()
    time.sleep(2.8)  # the drop-in and the route draw once, then stand still
    card.screenshot(path=str(art / "12-map-desktop-dark.png"))
    before = page.evaluate("() => document.getElementById('messages').scrollTop")
    frame.locator(".k-items li").nth(1).locator("button").click()
    frame.wait_for_function("() => document.querySelector('.k-status').textContent.includes('Locatie 2 van 4: Anne Frank Huis')", timeout=5000)
    time.sleep(0.8)
    after = page.evaluate("() => document.getElementById('messages').scrollTop")
    assert abs(after - before) <= 1, (before, after)
    assert frame.locator(".sw-pin.is-active").inner_text() == "2"
    assert frame.locator(".leaflet-popup .k-pop-name").inner_text() == "Anne Frank Huis"
    ok(f"map: 3 pins, route line, 'Niet op de kaart gevonden' lists the address, list click sets the status line, chat stays at {after}")
    # Tiles that do not load leave the list and say so (only with stubbed tiles).
    if os.environ.get("IUI_REAL_TILES") != "1":
        state["tiles"] = "block"
        menu_action(page, "Opnieuw starten", "Restart", card=".iui-card.iui-kit--map")
        frame = kit_frame_for(page, page.locator(".iui-card.iui-kit--map:visible").last)
        frame.wait_for_selector(".k-tile-note:not([hidden])", timeout=12000)
        assert "De kaart laadt nu niet" in frame.locator(".k-tile-note").inner_text()
        time.sleep(1.0)
        assert frame.locator(".k-items li").count() == 3
        page.locator(".iui-card.iui-kit--map:visible").last.screenshot(path=str(art / "13-map-tiles-blocked.png"))
        state["tiles"] = "stub"
        ok("map without tiles: calm note, list still there")

    # 10g. kpi: tiles, delta pills coloured by which direction is good, a target bar
    runs += 1
    send_turn(page, gateway, "Laat de kerncijfers zien [kpi]", runs, "De MRR groeit, de churn loopt op.")
    page.wait_for_function(LAST_READY, arg="kpi", timeout=30000)
    card = page.locator(".iui-card.iui-kit--kpi:visible").last
    assert card.locator(".iui-title").inner_text() == KPI_SPEC["title"]
    frame = kit_frame_for(page, card)
    frame.wait_for_selector(".k-tile", timeout=10000)
    assert frame.locator(".k-tile").count() == 4
    labels = frame.locator(".k-tile-label").all_inner_texts()
    values = frame.locator(".k-tile-value").all_inner_texts()
    assert labels == ["MRR", "Churn", "Kosten", "Conversie"], labels
    assert values[0].replace("\u00a0", " ") == "€ 18.400" and values[1] == "2,1%", values
    tones = frame.evaluate("() => [...document.querySelectorAll('.k-delta')].map(p => p.className.replace('k-delta ', ''))")
    assert tones == ["is-good", "is-bad", "is-good", "is-flat"], tones
    deltas = [t.replace("\u00a0", " ") for t in frame.evaluate("() => [...document.querySelectorAll('.k-delta')].map(p => p.childNodes[1].textContent)")]
    assert deltas == ["+12,5%", "+0,4 procentpunt", "€ -800", "0 procentpunt"], deltas
    good, bad = frame.evaluate(PROBE, "--sw-good"), frame.evaluate(PROBE, "--sw-bad")
    colours = frame.evaluate("() => [...document.querySelectorAll('.k-delta')].map(p => getComputedStyle(p).color)")
    assert colours[0] == good and colours[1] == bad and colours[2] == good and colours[3] not in (good, bad), (colours, good, bad)
    assert frame.locator(".k-delta.is-bad .k-sr").text_content() == ", ongunstig"
    fill = frame.evaluate("() => { const f=document.querySelector('.k-target-fill'); return f.getBoundingClientRect().width / f.parentElement.getBoundingClientRect().width; }")
    assert abs(fill - 0.92) < 0.02, fill
    assert frame.locator(".k-target-text").inner_text().replace("\u00a0", " ") == "92% van het doel van € 20.000"
    assert frame.evaluate("() => getComputedStyle(document.querySelector('.k-tile-label')).textTransform") == "none"
    card.scroll_into_view_if_needed()
    time.sleep(0.5)
    card.screenshot(path=str(art / "15-kpi-desktop-dark.png"))
    ok(f"kpi: 4 tiles, values {values[:2]}, delta pills {tones} (good {good}, bad {bad}), target bar at {fill:.0%}")

    # 10h. timeline: Gantt bars by status, milestones, the today line, click and keyboard details
    runs += 1
    send_turn(page, gateway, "Maak een planning [planning]", runs, "De acceptatietest is het risico.")
    page.wait_for_function(LAST_READY, arg="timeline", timeout=30000)
    card = page.locator(".iui-card.iui-kit--timeline:visible").last
    assert card.locator(".iui-title").inner_text() == TIMELINE_SPEC["title"]
    frame = kit_frame_for(page, card)
    frame.wait_for_selector(".k-tl-bar", timeout=10000)
    assert frame.locator(".k-tl-bar").count() == 4 and frame.locator(".k-tl-ms").count() == 2
    ticks = frame.locator(".k-tl-tick").all_inner_texts()
    assert ticks[0] == "9 nov" and "28 dec" in ticks, ticks
    bar_colours = frame.evaluate("""() => Object.fromEntries(['done', 'doing', 'risk', 'todo'].map(s =>
        [s, getComputedStyle(document.querySelector('.k-tl-bar.is-' + s)).backgroundColor]))""")
    accent = frame.evaluate(PROBE, "--sw-accent")
    assert bar_colours["done"] == good and bar_colours["risk"] == bad and bar_colours["doing"] == accent, (bar_colours, good, bad, accent)
    assert bar_colours["todo"] not in (good, bad, accent), bar_colours
    today_x = frame.evaluate("""() => { const t=document.querySelector('.k-tl-today').getBoundingClientRect();
        const r=document.querySelector('.k-tl-track').getBoundingClientRect(); return (t.left + t.width / 2 - r.left) / r.width; }""")
    assert abs(today_x - 0.3125) < 0.02, today_x
    assert frame.locator(".k-tl-today-label").inner_text() == "Vandaag"
    ms = frame.evaluate("() => getComputedStyle(document.querySelector('.k-tl-ms')).transform")
    assert ms not in ("none", ""), "a milestone is a diamond"
    detail = frame.locator(".k-tl-detail")
    assert detail.get_attribute("role") == "status" and detail.inner_text().strip() == ""
    frame.locator(".k-tl-bar.is-doing").click()
    text = detail.inner_text()
    assert all(part in text for part in ("Bouw", "16 nov t/m 13 dec 2026", "Senna", "Bezig", "Twee sprints")), text
    assert frame.locator(".k-tl-bar.is-doing").get_attribute("aria-pressed") == "true"
    frame.locator(".k-tl-bar.is-doing").focus()
    page.keyboard.press("ArrowDown")
    assert frame.evaluate("() => document.activeElement.getAttribute('aria-label')").startswith("Acceptatietest")
    page.keyboard.press("Enter")
    assert "Acceptatietest" in detail.inner_text() and "Risico" in detail.inner_text(), detail.inner_text()
    card.scroll_into_view_if_needed()
    time.sleep(0.6)  # the selection is saved after a short debounce
    card.screenshot(path=str(art / "16-timeline-desktop-dark.png"))
    with page.expect_download() as dl:
        menu_action(page, "Download als CSV", "Download as CSV", card=".iui-card.iui-kit--timeline")
    lines = Path(dl.value.path()).read_bytes().decode("utf-8-sig").splitlines()
    assert lines[0] == "Onderdeel;Start;Einde;Eigenaar;Status;Mijlpaal;Notitie", lines[0]
    assert "Bouw;2026-11-16;2026-12-13;Senna;Bezig;;Twee sprints" in lines, lines
    ok(f"timeline: 4 bars and 2 diamonds, status colours {bar_colours}, today line at {today_x:.3f}, click and ArrowDown plus Enter show the detail, CSV export")

    # 10e. after a reload the chart comes back in the table view the user chose
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("t => document.getElementById('messages') && document.getElementById('messages').innerText.includes(t)",
                           arg="Drie stops liggen dicht bij elkaar.", timeout=45000)
    time.sleep(2.0)
    chart_card = bring_ready(page, "chart")
    frame = kit_frame_for(page, chart_card)
    frame.wait_for_selector(".k-chart-table:not([hidden])", timeout=10000)
    assert frame.locator(".k-seg button[aria-pressed=true]").inner_text() == "Tabel"
    assert frame.locator(".k-canvas").is_hidden()
    ok("after a reload the chart card opens in the table view the user chose")
    frame.locator(".k-seg button:nth-child(1)").click()  # back to the chart for the screenshots

    # 10f. screenshots: desktop and 390 px, dark and light
    shots = []
    for width, height in ((1280, 900), (390, 844)):
        page.set_viewport_size({"width": width, "height": height})
        for theme in ("dark", "light"):
            page.evaluate(f"() => _applyTheme('{theme}')")
            time.sleep(0.6)
            for kind in ("table", "chart", "map", "kpi", "timeline"):
                c = bring_ready(page, kind, first=kind == "table")
                f = kit_frame_for(page, c)
                f.wait_for_function(f"() => document.documentElement.getAttribute('data-theme') === '{theme}'", timeout=5000)
                time.sleep(2.8 if kind == "map" else 0.8)
                overflow = c.evaluate("c => c.scrollWidth - c.clientWidth")
                assert overflow <= 1, f"{kind} card overflows by {overflow}px at {width}px"
                name = f"14-{kind}-{'mobile' if width < 600 else 'desktop'}-{theme}.png"
                if width < 600 and kind == "timeline" and theme == "dark":
                    stack = f.evaluate("""() => { const l=document.querySelector('.k-tl-label').getBoundingClientRect();
                        const t=document.querySelector('.k-tl-track').getBoundingClientRect();
                        return {axis: getComputedStyle(document.querySelector('.k-tl-axis')).display,
                                when: getComputedStyle(document.querySelector('.k-tl-when')).display,
                                now: getComputedStyle(document.querySelector('.k-tl-now')).display,
                                below: t.top >= l.bottom - 1, wide: t.width >= document.querySelector('.k-tl').getBoundingClientRect().width - 2}; }""")
                    assert stack == {"axis": "none", "when": "block", "now": "block", "below": True, "wide": True}, stack
                    ok(f"timeline at {width}px: a stacked list (label, period, then a full-width bar with today marked)")
                if width < 600 and kind == "kpi" and theme == "dark":
                    tops = f.evaluate("() => [...document.querySelectorAll('.k-tile')].map(t => Math.round(t.getBoundingClientRect().top))")
                    assert tops[0] == tops[1] and tops[2] > tops[0], tops
                if width < 600:
                    # A phone shows the top of the card under the app bar.
                    c.evaluate("c => c.scrollIntoView({block: 'start'})")
                    time.sleep(0.4)
                    page.screenshot(path=str(art / name))
                else:
                    c.screenshot(path=str(art / name))
                shots.append(name)
    page.evaluate("() => _applyTheme('dark')")
    page.set_viewport_size({"width": 1280, "height": 900})
    ok(f"screenshots: {', '.join(shots)}")
    return runs


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
        "webui_map_geocoder: \"off\"\n"
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
            frame = None
            for _ in range(40):  # the live frame can be replaced while the text node is rebuilt
                try:
                    frame = last_frame(page)
                    if frame.evaluate("() => document.getElementById('iui-root').textContent.includes('Invoer')"):
                        break
                except Exception:
                    pass
                time.sleep(0.25)
            else:
                raise AssertionError("live frame never showed the streamed markup")
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
            time.sleep(2.0)  # the chat re-renders the settled turn once more
            page.wait_for_selector(".msg-row .iui-card[data-state=ready]", timeout=20000)
            assert TAKEAWAY in page.inner_text("#messages"), "takeaway text missing"
            frame = last_frame(page)
            frame.wait_for_selector("#saving", timeout=10000)
            before = frame.inner_text("#saving")
            frame.evaluate("() => { const h=document.getElementById('hours'); h.value='60'; h.dispatchEvent(new Event('input',{bubbles:true})); }")
            after = frame.inner_text("#saving")
            time.sleep(0.6)  # state is reported to the chat after a short debounce
            assert before != after, (before, after)
            stage_h = page.evaluate("() => [...document.querySelectorAll('.iui-card')].find(c=>c.offsetParent!==null||c.classList.contains('iui-full')).querySelector('.iui-stage').getBoundingClientRect().height")
            content_h = frame.evaluate("() => document.body.scrollHeight")
            assert stage_h >= 200 and abs(stage_h - min(content_h, 900 * 0.86)) < 40, (stage_h, content_h)
            cards = page.evaluate("""() => [...document.querySelectorAll('.iui-card')].map(c => ({
                live: c.classList.contains('iui-live'), state: c.dataset.state, visible: c.offsetParent !== null,
                parent: (c.closest('[id]')||{}).id || '', seg: (c.closest('.assistant-segment')||{}).className || ''}))""")
            print("cards:", cards, flush=True)
            visible_cards = [c for c in cards if c["visible"]]
            assert len(visible_cards) == 1, cards
            title = page.inner_text(".iui-card:visible .iui-title")
            page.locator(".iui-card:visible").scroll_into_view_if_needed()
            page.locator(".iui-card:visible").screenshot(path=str(art / "02-settled-card.png"))
            ok(f"settled card {title!r}: scripts ran, slider changed {before!r} to {after!r}, stage {stage_h:.0f}px for {content_h}px content")

            # 3a. source view
            # The header stays calm: one title, full screen and a menu; no technical footer.
            visible_buttons = page.locator(".iui-card:visible .iui-head .iui-actions > button:visible").count()
            assert visible_buttons == 2, visible_buttons
            assert page.locator(".iui-card:visible .iui-foot").count() == 0
            assert page.locator(".iui-card:visible .iui-status:visible").count() == 0, "no status label once ready"
            menu_action(page, "Code bekijken", "View code")
            assert page.is_visible(".iui-card:visible .iui-source"), "source view did not open"
            assert "<style>" in page.inner_text(".iui-card:visible .iui-source")
            menu_action(page, "Code verbergen", "Hide code")
            assert not page.is_visible(".iui-card:visible .iui-source")
            ok("calm header (title, full screen, menu); source view lives in the menu")
            # 3b. full screen, closed with Escape pressed inside the frame
            page.locator(".iui-card:visible .iui-actions > button:not([aria-haspopup])").first.click()
            assert page.evaluate("() => [...document.querySelectorAll('.iui-card')].find(c=>c.offsetParent!==null||c.classList.contains('iui-full')).classList.contains('iui-full')")
            on_top = page.evaluate("""() => { const c=[...document.querySelectorAll('.iui-card')].find(c=>c.offsetParent!==null||c.classList.contains('iui-full')); const r=c.getBoundingClientRect();
                const pts=[[r.left+20,r.top+12],[r.right-60,r.top+12],[r.left+20,r.bottom-12],[r.right-20,r.bottom-12]];
                return pts.every(([x,y]) => { const el=document.elementFromPoint(x,y); return !!el && c.contains(el); }); }""")
            assert on_top, "full screen card is covered by app chrome"
            page.screenshot(path=str(art / "03-fullscreen.png"))
            last_frame(page).locator("#iui-root").click(position={"x": 5, "y": 5})
            page.keyboard.press("Escape")
            page.wait_for_function("() => ![...document.querySelectorAll('.iui-card')].find(c=>c.offsetParent!==null||c.classList.contains('iui-full')).classList.contains('iui-full')", timeout=5000)
            ok("full screen opens and closes with Escape from inside the frame")
            # 3c. download
            with page.expect_download() as dl:
                menu_action(page, "Downloaden", "Download")
            html = Path(dl.value.path()).read_text(encoding="utf-8")
            assert 'id="iui-root"' in html and "Invoer" in html and "synthwave" in html, html[:300]
            ok(f"download gives a standalone HTML file ({dl.value.suggested_filename}, {len(html)} bytes)")
            # 3d. the frame opened on its own (outside the chat) renders nothing
            solo = ctx.new_page()
            solo.goto("/static/interactive-ui/frame.html", wait_until="domcontentloaded")
            solo.evaluate("() => window.postMessage({iui:1,type:'render',html:'<h1 id=phish>Log in</h1>',css:'',scripts:[],final:true}, '*')")
            time.sleep(0.4)
            assert solo.locator("#phish").count() == 0, "a top-level frame must not render posted content"
            solo.close()
            ok("the frame opened outside the chat ignores posted content")

            # 4. follow-up from a click inside the widget: shown in the card, sent by the host button
            frame = last_frame(page)
            frame.locator("#ask").click()
            page.wait_for_selector(".iui-card:visible .iui-ask:not([hidden])", timeout=5000)
            ask_text = page.inner_text(".iui-card:visible .iui-ask .iui-ask-text")
            assert "Werk dit scenario uit" in ask_text, ask_text
            time.sleep(0.8)
            assert len(gateway.runs) == 1, "nothing is sent before the user confirms"
            page.locator(".iui-card:visible .iui-ask").screenshot(path=str(art / "04-ask-bar.png"))
            # A draft in the composer is never overwritten.
            page.locator("#msg").fill("mijn eigen concept")
            page.locator(".iui-card:visible .iui-ask .iui-btn--primary").click()
            time.sleep(0.8)
            assert len(gateway.runs) == 1 and page.input_value("#msg") == "mijn eigen concept", "draft must be kept"
            page.locator("#msg").fill("")
            page.locator(".iui-card:visible .iui-ask .iui-btn--primary").click()
            body = wait_runs(gateway, 2)
            assert "Werk dit scenario uit" in body, body
            wait_idle(page)
            page.wait_for_function("() => document.getElementById('messages').innerText.includes('Antwoord op vervolgvraag 1')", timeout=20000)
            ok("a widget follow-up shows in the card, keeps the user's draft, and sends only on the host's Send button")

            # 4b. a script-triggered prompt without user interaction is refused.
            # The list re-rendered for the new turn; frames load lazily when on screen.
            page.locator(".iui-card:visible").first.scroll_into_view_if_needed()
            page.wait_for_selector(".iui-card[data-state=ready]:visible", timeout=15000)
            frame = last_frame(page)
            frame.wait_for_selector("#saving", timeout=10000)
            frame.wait_for_function("() => document.getElementById('hours').value === '60'", timeout=8000)
            ok("after the list re-rendered the widget kept the user's slider value (60)")
            page.locator("#msg").click()
            time.sleep(5.2)  # outside the interaction window
            frame.evaluate("() => { synthwave.sendPrompt('/yolo automatisch zonder klik'); }")
            page.wait_for_selector(".iui-card:visible .iui-ask:not([hidden])", timeout=5000)
            shown = page.inner_text(".iui-card:visible .iui-ask .iui-ask-text")
            assert not shown.startswith("/"), shown
            time.sleep(1.0)
            assert len(gateway.runs) == 2, "an automatic prompt must not be sent"
            page.locator(".iui-card:visible .iui-ask .iui-btn--quiet").first.click()
            assert not page.is_visible(".iui-card:visible .iui-ask")
            ok("an automatic prompt is only offered (slash stripped), never sent, and can be cancelled")

            # 5. theme switch reaches the frame
            page.evaluate("() => _applyTheme('light')")
            frame.wait_for_function("() => document.documentElement.getAttribute('data-theme') === 'light'", timeout=5000)
            page.locator(".iui-card:visible").first.screenshot(path=str(art / "05-light-theme.png"))
            page.evaluate("() => _applyTheme('dark')")
            frame.wait_for_function("() => document.documentElement.getAttribute('data-theme') === 'dark'", timeout=5000)
            ok("theme switches follow into the frame (light and back to dark)")

            # 6. isolation
            iso = frame.evaluate("""async () => {
                const out = {cookie: null, fetch: null, parent: null, storage: null};
                try { out.cookie = document.cookie; } catch (e) { out.cookie = 'blocked:' + e.name; }
                try { await fetch('/api/sessions'); out.fetch = 'allowed'; } catch (e) { out.fetch = 'blocked'; }
                try { out.parent = String(window.parent.document.title); } catch (e) { out.parent = 'blocked'; }
                // localStorage is an in-memory stand-in, never the browser's real storage.
                try { localStorage.setItem('x', '1'); out.storage = (typeof Storage !== 'undefined' && localStorage instanceof Storage) ? 'real' : 'memory-only'; } catch (e) { out.storage = 'blocked'; }
                return out;
            }""")
            assert iso["fetch"] == "blocked" and iso["parent"] == "blocked" and iso["storage"] in ("memory-only", "blocked"), iso
            assert iso["cookie"] in ("", "blocked:SecurityError"), iso
            ok(f"frame is isolated: {iso}")

            # 7. broken widget and repair
            page.locator("#msg").fill(PROMPTS[2])
            page.locator("#btnSend").click()
            wait_runs(gateway, 3)
            wait_idle(page)
            page.wait_for_selector(".iui-card[data-state=error]:visible .iui-error:not([hidden])", timeout=20000)
            lead = page.locator(".iui-card[data-state=error]:visible .iui-error-text").last.inner_text()
            assert "Uncaught" not in lead and "Error" not in lead, f"lead sentence must be plain: {lead!r}"
            page.locator(".iui-card[data-state=error]:visible .iui-error .iui-btn--quiet").last.click()
            err_text = page.locator(".iui-card[data-state=error]:visible .iui-error-details").last.inner_text()
            assert "nietBestaandeFunctie" in err_text and "evil.example" in err_text, err_text
            page.locator(".iui-card[data-state=error]:visible").last.screenshot(path=str(art / "06-error-bar.png"))
            page.locator(".iui-card[data-state=error]:visible .iui-error .iui-btn--text:not(.iui-btn--quiet)").last.click()
            body = wait_runs(gateway, 4)
            assert ("herstel" in body.lower() or "can you fix" in body.lower()) and "nietBestaandeFunctie" in body, body
            wait_idle(page)
            bubble = page.locator(".msg-row[data-role='user']:visible").last.inner_text()
            assert "View report" not in bubble and "nietBestaandeFunctie" not in bubble and "interactive-ui" not in bubble, f"repair bubble must stay plain: {bubble!r}"
            ok(f"broken widget: plain sentence {lead!r}, details on demand, repair asks the agent")

            # 7b. reply chips under the latest reply; a click sends the text, older unused chips disappear
            page.wait_for_selector(".iui-chips:visible", timeout=20000)
            chips = page.locator(".iui-chips:visible .iui-chip")
            assert chips.count() == 2, chips.count()
            assert page.locator("pre code.language-suggestions:visible, pre code.suggestions:visible").count() == 0
            page.locator(".iui-chips:visible").last.screenshot(path=str(art / "06b-reply-chips.png"))
            chips.first.click()
            body = wait_runs(gateway, 5)
            assert "Toon het in een grafiek" in body, body
            wait_idle(page)
            page.wait_for_function("() => document.getElementById('messages').innerText.includes('Antwoord op vervolgvraag 4')", timeout=20000)
            time.sleep(1.0)
            assert page.locator(".iui-chips:not(.is-used):visible").count() == 0, "old unused chips must hide"
            ok("reply chips show under the latest reply, a click sends that reply, unused chips hide afterwards")

            # 8. hard reload renders the cards again from the transcript
            page.reload(wait_until="domcontentloaded")
            try:
                page.wait_for_function("t => document.getElementById('messages') && document.getElementById('messages').innerText.includes(t)",
                                       arg=TAKEAWAY, timeout=45000)
            finally:
                page.screenshot(path=str(art / "08-after-reload.png"))
                info = page.evaluate("""() => ({blocks: document.querySelectorAll('.iui-block').length,
                    cards: document.querySelectorAll('.iui-card').length,
                    pre: [...document.querySelectorAll('#messages pre code')].map(c => c.className).slice(0, 5),
                    raw: (document.getElementById('messages')||{}).innerText ? document.getElementById('messages').innerText.slice(0, 300) : ''})""")
                print("reload state:", info, flush=True)
            page.wait_for_selector(".iui-card", timeout=45000)
            page.wait_for_function("() => document.querySelectorAll('.iui-card').length >= 2", timeout=45000)
            page.locator(".iui-card:visible").first.scroll_into_view_if_needed()
            page.wait_for_selector(".iui-card[data-state=ready]:visible", timeout=45000)
            ok(f"after reload {page.locator('.iui-card').count()} cards render again from the transcript")

            # 9. narrow layout
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator(".iui-card:visible").first.scroll_into_view_if_needed()
            time.sleep(0.8)
            overflow = page.evaluate("() => { const c=[...document.querySelectorAll('.iui-card')].find(c=>c.offsetParent!==null||c.classList.contains('iui-full')); return c.scrollWidth - c.clientWidth; }")
            assert overflow <= 1, f"card overflows horizontally by {overflow}px"
            page.screenshot(path=str(art / "07-mobile.png"))
            ok("narrow layout fits without horizontal overflow")

            # 10. data blocks
            data_blocks(page, ctx, gateway, art, len(gateway.runs))

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
