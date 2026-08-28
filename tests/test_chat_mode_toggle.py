"""Per-conversation chat mode: Normal chat vs Super agent.

Requested by Michael Ramirez on 28 Aug 2026. Every new conversation keeps
today's behaviour ("super") until a user flips the chip, the mode survives a
reload, and the narrowing can only ever subtract from what the user already had.
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import pytest

from api.config import (
    CHAT_MODES,
    DEFAULT_CHAT_MODE,
    NORMAL_CHAT_TOOLSETS,
    chat_mode_toolsets,
    normalize_chat_mode,
)
from api.governance.catalog import _ANON_ROUTES, _SELF_ROUTES, route_permission
from api.models import Session, new_session

REPO = Path(__file__).resolve().parents[1]
ROUTES = (REPO / "api" / "routes.py").read_text(encoding="utf-8")
STREAMING = (REPO / "api" / "streaming.py").read_text(encoding="utf-8")
UI_JS = (REPO / "static" / "ui.js").read_text(encoding="utf-8")
SESSIONS_JS = (REPO / "static" / "sessions.js").read_text(encoding="utf-8")
BOOT_JS = (REPO / "static" / "boot.js").read_text(encoding="utf-8")
STYLE_CSS = (REPO / "static" / "style.css").read_text(encoding="utf-8")
EN_JS = (REPO / "static" / "i18n" / "en.js").read_text(encoding="utf-8")
I18N_DIR = REPO / "static" / "i18n"

# The 40-name shape the live resolver produces on this box: profile toolsets
# plus every globally enabled MCP server under its BARE name (no "mcp-" prefix
# exists: hermes_cli.tools_config appends server names verbatim).
_PROFILE_LIKE_TOOLSETS = [
    "clarify", "file", "web", "todo", "memory", "skills", "terminal",
    "code_execution", "delegation", "browser", "cronjob", "session_search",
    "image_gen", "vision", "tts", "notion", "composio", "playwright",
    "fireflies", "lovable", "omniroute", "ragflow",
]


class _DummyHandler:
    """Minimal BaseHTTPRequestHandler stand-in (see tests/test_issue4490_presession_toolsets.py)."""

    command = "POST"

    def __init__(self, body: dict):
        raw = json.dumps(body).encode("utf-8")
        self.headers = {"Content-Length": str(len(raw))}
        self.rfile = tempfile.SpooledTemporaryFile()
        self.rfile.write(raw)
        self.rfile.seek(0)
        self.status = None
        self.response = {}
        self.wfile = tempfile.SpooledTemporaryFile()
        self.client_address = ("127.0.0.1", 12345)

    def send_response(self, code: int):
        self.status = code

    def send_header(self, key: str, value: str):
        self.response.setdefault("headers", {})[key] = value

    def end_headers(self):
        pass

    def payload(self) -> dict:
        self.wfile.seek(0)
        return json.loads(self.wfile.read().decode("utf-8"))


@pytest.fixture
def isolated_sessions(tmp_path, monkeypatch):
    """Point the session store at a temp dir so saves never touch the real one."""
    from collections import OrderedDict

    from api import models, routes

    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    monkeypatch.setattr(models, "SESSION_DIR", session_dir)
    monkeypatch.setattr(models, "SESSION_INDEX_FILE", session_dir / "_index.json")
    monkeypatch.setattr(models, "SESSIONS", OrderedDict())
    monkeypatch.setattr(routes, "SESSION_DIR", session_dir)
    monkeypatch.setattr(routes, "SESSIONS", models.SESSIONS)
    monkeypatch.setattr(routes, "_check_csrf", lambda handler: True)
    # Session write routes run behind the shared profile visibility guard.
    # Pin the request profile so these tests exercise chat-mode validation and
    # persistence rather than inheriting whichever profile a developer's live
    # WebUI process last selected.
    monkeypatch.setattr(routes, "_get_active_profile_name", lambda: "default")
    # Tests run without an authenticated request identity. In production that
    # means single-user/admin visibility, but a developer's live governance
    # policy can still make implicit owner resolution environment-specific.
    # Keep these persistence tests focused on the mode endpoint.
    monkeypatch.setattr(routes, "_session_owner_visible_to_request", lambda owner, handler=None: True)
    return session_dir


def _post(path: str, body: dict) -> tuple[_DummyHandler, dict]:
    """Drive a POST route directly. api.helpers.j/bad both return None, so the
    handler's recorded status is the signal, not handle_post's return value."""
    from api.routes import handle_post

    handler = _DummyHandler(body)
    handle_post(handler, urlparse(path))
    return handler, handler.payload()


# ── The mode vocabulary ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "value",
    ["", None, "lite", "garbage", "SUPER ", 42, [], {"mode": "normal"}, "Normal chat"],
)
def test_normalize_chat_mode_defaults_to_super(value):
    """Anything unreadable must resolve to the WIDE default.

    Defaulting the other way would silently hand a user a narrower surface than
    the one they picked, which is exactly the surprise the toggle must not cause.
    """
    assert normalize_chat_mode(value) == "super"
    assert normalize_chat_mode(value) == DEFAULT_CHAT_MODE


@pytest.mark.parametrize("value", ["normal", "NORMAL", " normal ", "Normal"])
def test_normalize_chat_mode_accepts_normal(value):
    assert normalize_chat_mode(value) == "normal"


def test_chat_modes_vocabulary_is_two_valued():
    assert set(CHAT_MODES) == {"super", "normal"}


# ── The narrowing resolver ───────────────────────────────────────────────────

def test_super_mode_returns_the_input_unchanged():
    assert chat_mode_toolsets(_PROFILE_LIKE_TOOLSETS, "super") == _PROFILE_LIKE_TOOLSETS


@pytest.mark.parametrize(
    "toolsets",
    [
        _PROFILE_LIKE_TOOLSETS,
        ["file", "web", "terminal"],
        ["notion", "composio", "playwright"],
        ["clarify"],
        [],
    ],
)
@pytest.mark.parametrize("mode", ["super", "normal", "garbage", None])
def test_chat_mode_toolsets_never_adds_a_toolset(toolsets, mode):
    """The subset property is what makes the mode incapable of widening access.

    ``chat_mode_toolsets`` is a pure filter over an already-resolved list, so no
    mode (including an unrecognised one) can introduce a name the caller did not
    already hold.
    """
    result = chat_mode_toolsets(toolsets, mode)
    assert set(result) <= set(toolsets)


def test_normal_mode_drops_the_wide_surface():
    result = chat_mode_toolsets(_PROFILE_LIKE_TOOLSETS, "normal")
    for dropped in (
        "skills", "terminal", "code_execution", "delegation", "browser",
        "cronjob", "session_search", "image_gen", "vision", "tts",
    ):
        assert dropped not in result, f"normal mode must drop {dropped}"
    assert set(result) == set(NORMAL_CHAT_TOOLSETS)


def test_normal_mode_drops_every_enabled_mcp_server_name():
    """MCP servers ride the toolset list under their bare server names.

    They carry no "mcp-" prefix, so the intersection (not a prefix filter) is
    what keeps them out of a normal-mode turn.
    """
    servers = {"notion", "composio", "playwright", "fireflies", "lovable", "omniroute", "ragflow"}
    result = set(chat_mode_toolsets(_PROFILE_LIKE_TOOLSETS, "normal"))
    assert result & servers == set()


def test_normal_mode_falls_back_rather_than_shipping_a_zero_tool_turn():
    pinned = ["terminal", "browser"]
    assert chat_mode_toolsets(pinned, "normal") == pinned


# ── Persistence ─────────────────────────────────────────────────────────────

def test_new_session_defaults_to_todays_behaviour():
    with tempfile.TemporaryDirectory() as tmp:
        assert new_session(workspace=tmp).chat_mode == "super"
        assert new_session(workspace=tmp, chat_mode="normal").chat_mode == "normal"


def test_mode_survives_a_reload(isolated_sessions):
    """load_metadata_only is the read the streaming worker performs.

    It parses only the JSON prefix before the ``messages`` array, so the field
    has to sit in METADATA_FIELDS or the mode would silently reset to super.
    """
    session = Session(session_id="chatmode0001", workspace="/tmp", chat_mode="normal")
    session.messages = [{"role": "user", "content": "hi"}]
    session.save(skip_index=True)

    assert Session.load_metadata_only("chatmode0001").chat_mode == "normal"


def test_compact_carries_chat_mode_for_the_browser():
    session = Session(session_id="chatmode0002", workspace="/tmp", chat_mode="normal")
    assert session.compact()["chat_mode"] == "normal"


# ── The write route ─────────────────────────────────────────────────────────

def test_post_mode_persists_normal(isolated_sessions):
    session = Session(session_id="chatmode0003", workspace="/tmp")
    session.save(skip_index=True)
    from api import routes

    routes.SESSIONS["chatmode0003"] = session

    handler, payload = _post("/api/session/mode", {"session_id": "chatmode0003", "mode": "normal"})
    assert payload == {"ok": True, "chat_mode": "normal"}
    assert Session.load_metadata_only("chatmode0003").chat_mode == "normal"


def test_post_mode_can_switch_back_to_super(isolated_sessions):
    session = Session(session_id="chatmode0004", workspace="/tmp", chat_mode="normal")
    session.save(skip_index=True)
    from api import routes

    routes.SESSIONS["chatmode0004"] = session

    _, payload = _post("/api/session/mode", {"session_id": "chatmode0004", "mode": "super"})
    assert payload == {"ok": True, "chat_mode": "super"}


@pytest.mark.parametrize("mode", ["", "lite", None, 123, ["normal"], "  "])
def test_post_mode_rejects_an_unknown_mode(isolated_sessions, mode):
    session = Session(session_id="chatmode0005", workspace="/tmp", chat_mode="normal")
    session.save(skip_index=True)
    from api import routes

    routes.SESSIONS["chatmode0005"] = session

    handler, _ = _post("/api/session/mode", {"session_id": "chatmode0005", "mode": mode})
    assert handler.status == 400
    assert Session.load_metadata_only("chatmode0005").chat_mode == "normal"


def test_post_mode_on_an_unknown_session_is_404(isolated_sessions):
    handler, _ = _post("/api/session/mode", {"session_id": "nosuchsession", "mode": "normal"})
    assert handler.status == 404


def test_post_new_session_accepts_and_defaults_the_mode(isolated_sessions):
    _, staged = _post("/api/session/new", {"chat_mode": "normal"})
    assert staged["session"]["chat_mode"] == "normal"

    _, default = _post("/api/session/new", {})
    assert default["session"]["chat_mode"] == "super"


def test_post_new_session_rejects_an_unknown_mode(isolated_sessions):
    handler, payload = _post("/api/session/new", {"chat_mode": "lite"})
    assert handler.status == 400
    assert payload["error"] == 'mode must be "normal" or "super"'


# ── Governance ──────────────────────────────────────────────────────────────

def test_mode_route_is_a_session_write():
    assert route_permission("/api/session/mode", "POST") == "sessions:write"
    assert route_permission("/api/session/mode", "GET") == "sessions:read"


def test_mode_route_is_neither_anonymous_nor_self_service():
    assert "/api/session/mode" not in _ANON_ROUTES
    assert "/api/session/mode" not in _SELF_ROUTES


def test_mode_route_inherits_the_shared_ownership_guard():
    """One handler, downstream of the body-level session visibility guard."""
    assert ROUTES.count('if parsed.path == "/api/session/mode":') == 1
    guard = ROUTES.index('_guard_request_session_visibility(handler, parsed, body=body, method="POST")')
    assert guard < ROUTES.index('if parsed.path == "/api/session/mode":')


def test_mode_route_is_not_exempt_from_the_visibility_guard():
    from api.routes import _request_session_visibility_exempt

    assert _request_session_visibility_exempt("POST", "/api/session/mode") is False


def test_mode_route_matches_its_sibling_session_route():
    block = ROUTES[ROUTES.index('if parsed.path == "/api/session/mode":'):]
    block = block[: block.index('if parsed.path == "/api/session/draft":')]
    assert "_session_is_subagent_view_only" in block
    assert "_get_session_agent_lock" in block


# ── The streaming worker ────────────────────────────────────────────────────

def test_narrowing_runs_after_the_per_session_override():
    """A session that pinned a narrow custom list must never be re-widened."""
    assert STREAMING.index("chat_mode_toolsets(") > STREAMING.index("_toolsets = _override")


def test_mode_is_part_of_the_agent_cache_signature():
    blob = STREAMING[STREAMING.index("_sig_blob = _json.dumps(["):]
    blob = blob[: blob.index("_agent_sig = ")]
    assert "_chat_mode," in blob


def test_mcp_discovery_is_guarded_on_the_mode():
    guard = STREAMING.index("if _chat_mode != 'normal':")
    assert guard < STREAMING.index("from tools.mcp_tool import discover_mcp_tools")


# ── The composer chip ───────────────────────────────────────────────────────

def _function_body(src: str, signature: str) -> str:
    start = src.index(signature)
    brace = src.index("{", start)
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start : i + 1]
    raise AssertionError(f"function body not found: {signature}")


def test_ui_defines_the_chip_functions():
    for signature in (
        "function toggleChatMode",
        "function _applyChatModeChip",
        "function _syncChatModeChip",
    ):
        assert _function_body(UI_JS, signature)
    assert "window.toggleChatMode = toggleChatMode;" in UI_JS


def test_sync_topbar_syncs_the_chip_in_both_branches():
    """The empty composer is exactly where a user picks the mode for the
    conversation they are about to start, so the no-session early return must
    sync too (unlike the toolsets chip, which deliberately does not)."""
    body = _function_body(UI_JS, "function syncTopbar")
    early = body[: body.index("const sessionTitle=")]
    late = body[body.index("const sessionTitle="):]
    assert "syncChatModeChip()" in early
    assert "syncChatModeChip()" in late


def test_staged_mode_is_forwarded_only_from_the_empty_composer():
    compact = SESSIONS_JS.replace(" ", "")
    before_post = compact[: compact.index("api('/api/session/new'")]
    after_assignment = compact[compact.index("S.session=data.session") :]
    assert "!S.session&&S._pendingChatMode)reqBody.chat_mode=S._pendingChatMode" in before_post
    assert "S._pendingChatMode=null" in after_assignment


def test_every_staged_toolsets_reset_also_clears_the_staged_mode():
    """A staged mode must not leak into a later conversation."""
    for src, name in (
        (UI_JS, "static/ui.js"),
        (SESSIONS_JS, "static/sessions.js"),
        ((REPO / "static" / "panels.js").read_text(encoding="utf-8"), "static/panels.js"),
    ):
        compact = src.replace(" ", "")
        toolset_resets = compact.count("S._pendingSessionToolsets=null")
        mode_resets = compact.count("S._pendingChatMode=null")
        assert mode_resets >= toolset_resets, name
    assert "_pendingChatMode:null" in UI_JS


def test_the_chip_label_is_owned_by_js_and_refreshed_on_a_locale_switch():
    """A static data-i18n key on the label would relabel a normal-mode chip as
    "Super agent" the moment applyLocaleToDOM() runs."""
    index_html = (REPO / "static" / "index.html").read_text(encoding="utf-8")
    label = index_html[index_html.index('id="composerChatModeLabel"') :][:120]
    assert "data-i18n" not in label

    i18n_js = (REPO / "static" / "i18n.js").read_text(encoding="utf-8")
    apply_dom = i18n_js[i18n_js.index("function applyLocaleToDOM()") :]
    assert "syncChatModeChip()" in apply_dom[: apply_dom.index("\n}")]


def test_chip_is_registered_in_the_composer_control_defs():
    defs = BOOT_JS[BOOT_JS.index("const _COMPOSER_CONTROL_TOGGLE_DEFS=["):]
    defs = defs[: defs.index("];")]
    assert "key:'hide_composer_chat_mode'" in defs
    assert "#composerChatModeWrap" in defs


def test_chip_is_not_width_gated_away():
    """The active mode has to stay visible at every composer width.

    The toolsets chip hides itself below a 1100px container query; the mode chip
    must degrade to an icon instead of disappearing.
    """
    gate = STYLE_CSS.index("@container composer-footer (min-width: 1100px)")
    block = STYLE_CSS[gate : STYLE_CSS.index("}", STYLE_CSS.index("{", gate)) + 1]
    assert "composer-chat-mode-wrap" not in block
    assert ".composer-chat-mode-wrap{display:block;}" in STYLE_CSS
    for stage in (
        ".composer-footer.cf-icons .composer-chat-mode-chip",
        ".composer-footer.cf-burger .composer-chat-mode-chip",
    ):
        assert stage in STYLE_CSS
    assert "display:none!important" not in STYLE_CSS[
        STYLE_CSS.index(".composer-footer.cf-burger .composer-chat-mode-chip") :
    ][:400]


# ── Copy ────────────────────────────────────────────────────────────────────

def _en_chat_mode_strings() -> dict[str, str]:
    return dict(re.findall(r"^\s*(chat_mode[a-z_]*|composer_control_chat_mode)\s*:\s*'([^']*)',", EN_JS, re.M))


def test_visible_copy_is_plain_business_language():
    strings = _en_chat_mode_strings()
    assert set(strings) >= {
        "chat_mode", "chat_mode_super", "chat_mode_normal",
        "chat_mode_super_title", "chat_mode_normal_title",
        "chat_mode_switched", "chat_mode_failed", "composer_control_chat_mode",
    }
    for key, value in strings.items():
        lowered = value.lower()
        for internal in ("toolset", "mcp", "token", "schema", "skills index", "api", "agent_init"):
            assert internal not in lowered, f"{key} leaks internal vocabulary: {value}"


def test_every_locale_carries_the_chat_mode_keys():
    """No test enforced i18n key parity across static/i18n/*.js before this one:
    the tests/test_*_locale.py suite reads the now-keyless static/i18n.js."""
    expected = set(_en_chat_mode_strings())
    for path in sorted(I18N_DIR.glob("*.js")):
        src = path.read_text(encoding="utf-8")
        present = {
            key
            for key in expected
            if re.search(rf"^\s*{re.escape(key)}\s*:", src, re.M)
        }
        assert present == expected, f"{path.name} is missing {sorted(expected - present)}"
