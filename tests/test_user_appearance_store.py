"""Per-user appearance store (27 Aug 2026 report: skin colour and text size
changes did not stick / could revert to another user's choice).

The three look-and-feel keys (theme, skin, font_size) are stored per identity
email under STATE_DIR/user-appearance and overlaid on GET /api/settings for
that identity; POST /api/settings routes them to the caller's own store so
one person's choice never changes the instance default for anyone else.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api.settings_scope as scope  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ROUTES = (REPO / "api" / "routes.py").read_text(encoding="utf-8")
STYLE = (REPO / "static" / "style.css").read_text(encoding="utf-8")
BOOT = (REPO / "static" / "boot.js").read_text(encoding="utf-8")


def _use_tmp_state(monkeypatch, tmp_path):
    from api import config

    monkeypatch.setattr(config, "STATE_DIR", tmp_path)


def _as(monkeypatch, email):
    monkeypatch.setattr(scope, "request_identity_email", lambda handler: email)


def test_split_routes_appearance_to_user_store_and_keeps_rest_global(monkeypatch, tmp_path):
    _use_tmp_state(monkeypatch, tmp_path)
    _as(monkeypatch, "alice@example.test")
    rest, stored = scope.split_user_appearance(SimpleNamespace(), {
        "theme": "light", "skin": "sienna", "font_size": "large", "session_jump_buttons": True,
    })
    assert rest == {"session_jump_buttons": True}
    assert stored == {"theme": "light", "skin": "sienna", "font_size": "large"}
    assert scope.load_user_appearance("alice@example.test") == stored
    assert scope.load_user_appearance("bob@example.test") == {}


def test_overlay_applies_only_the_callers_store(monkeypatch, tmp_path):
    _use_tmp_state(monkeypatch, tmp_path)
    scope.save_user_appearance("alice@example.test", {"theme": "light", "font_size": "xlarge"})
    scope.save_user_appearance("bob@example.test", {"theme": "dark", "skin": "ares"})
    _as(monkeypatch, "alice@example.test")
    settings = {"theme": "dark", "skin": "default", "font_size": "default", "other": 1}
    scope.overlay_user_appearance(SimpleNamespace(), settings)
    assert settings["theme"] == "light" and settings["font_size"] == "xlarge"
    assert settings["skin"] == "default"          # untouched: alice never chose a skin
    assert settings["appearance_scope"] == "user"
    assert settings["other"] == 1


def test_identity_less_caller_stays_on_instance_file(monkeypatch, tmp_path):
    _use_tmp_state(monkeypatch, tmp_path)
    _as(monkeypatch, "")
    body = {"theme": "light", "skin": "sienna"}
    rest, stored = scope.split_user_appearance(SimpleNamespace(), dict(body))
    assert rest == body and stored == {}
    settings = {"theme": "dark"}
    scope.overlay_user_appearance(SimpleNamespace(), settings)
    assert settings == {"theme": "dark"}


def test_invalid_values_are_dropped_not_stored(monkeypatch, tmp_path):
    _use_tmp_state(monkeypatch, tmp_path)
    stored = scope.save_user_appearance("alice@example.test", {
        "theme": "neon", "skin": "../../etc", "font_size": "huge",
    })
    assert stored == {}
    assert not list((tmp_path / "user-appearance").glob("*.json")) or \
        scope.load_user_appearance("alice@example.test") == {}


def test_routes_wire_overlay_and_split():
    assert "overlay_user_appearance(handler, settings)" in ROUTES
    assert "body, _user_appearance = split_user_appearance(handler, body)" in ROUTES


def test_brand_override_is_scoped_to_the_default_skin():
    """A chosen skin must keep its own palette: the SynthPulse brand block may
    only match :root when no data-skin is set."""
    assert ":root:not([data-skin]){" in STYLE
    assert ":root.dark:not([data-skin]){" in STYLE
    assert ":root:not(.dark)[data-skin]{" not in STYLE
    assert ":root.dark[data-skin]{" not in STYLE


def test_font_size_prefers_explicit_local_choice_on_boot():
    assert "_lsHasExplicitFont" in BOOT
    assert "const fontSize=_lsHasExplicitFont?_lsFont:(s.font_size||_lsFont||'default');" in BOOT
