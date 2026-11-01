"""Help content covers every page, in English and Dutch, safely (plan 6.1, 6.2).

``static/help-content.js`` assigns one JSON value to
``window.SynthPulseHelpContent``. These tests read that JSON directly and
check that:

* every ``data-panel`` of ``static/index.html`` and every virtual page of plan
  6.1 has a help page in ``en`` and in ``nl``, so a new panel (the
  organisation and support pages of W8 and W9) cannot land without help;
* both locales have the same structure and targets, and the Dutch text is
  really translated;
* every static target exists in ``index.html`` (dynamic ones are marked);
* no string holds an em or en dash, HTML, or a name from the internal-name
  denylist, read from the catalogue fixture and never copied here;
* every ``module`` or ``modules`` key names a catalogue id of the fixture.
"""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTENT_JS = ROOT / "static" / "help-content.js"
INDEX_HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
CATALOG = json.loads(
    (ROOT / "tests" / "fixtures" / "managed_service" / "module_catalog.json").read_text(encoding="utf-8")
)
LOCALES = ("en", "nl")
ASSIGN = "window.SynthPulseHelpContent = "
# Plan 6.1: pages that are not a data-panel of their own.
VIRTUAL_PAGES = {
    "group_chat", "voice_mode", "realtime_voice", "bot_builder", "profile_switching",
    "workspace_files", "plugins", "todos", "files", "logs",
}
# Structural keys: identical in every locale, never shown to a person.
PAGE_KEYS = {"title", "summary", "sections", "related", "parent", "audience", "module", "modules", "enabled_if"}
SECTION_KEYS = {"id", "title", "body", "target", "dynamic", "module", "modules", "audience", "position"}
STEP_KEYS = {"title", "body", "target", "nav", "page", "position", "dynamic", "module", "modules", "audience"}
STRUCTURAL = {"id", "target", "dynamic", "module", "modules", "audience", "position", "nav", "page",
              "parent", "enabled_if", "related"}
TARGET_RE = re.compile(r"^(?:\[data-tour='(?P<tour>[a-z0-9-]+)'\]|#(?P<id>[A-Za-z][A-Za-z0-9_-]*))$")
ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
DASHES = ("\u2013", "\u2014")


def _content():
    text = CONTENT_JS.read_text(encoding="utf-8")
    assert text.count(ASSIGN) == 1, "help-content.js must assign one JSON value"
    body = text.split(ASSIGN, 1)[1].rstrip()
    assert body.endswith(";")
    return json.loads(body[:-1])


CONTENT = _content()


class _Panels(HTMLParser):
    """The data-panel values and data-tour names of the static markup."""

    def __init__(self):
        super().__init__()
        self.panels, self.tours, self.ids = set(), set(), set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("data-panel"):
            self.panels.add(attrs["data-panel"])
        if attrs.get("data-tour"):
            self.tours.add(attrs["data-tour"])
        if attrs.get("id"):
            self.ids.add(attrs["id"])


MARKUP = _Panels()
MARKUP.feed(INDEX_HTML)
# The inline tab-order script builds '[data-panel="'+id+'"]' selectors; the
# parser never sees those as attributes, so only real panels are listed.
PANELS = {p for p in MARKUP.panels if ID_RE.fullmatch(p)}


def _strings(value, key=None):
    """Every person-facing string of the content, with its path."""
    if isinstance(value, dict):
        for k, v in value.items():
            if k in STRUCTURAL:
                continue
            yield from _strings(v, k)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item, key)
    elif isinstance(value, str):
        yield key, value


def _locale(code):
    return CONTENT["locales"][code]


def test_content_shape_and_locales():
    assert CONTENT["version"] == 1
    assert set(CONTENT["locales"]) == set(LOCALES)
    for code in LOCALES:
        assert set(_locale(code)) == {"ui", "pages", "tour_steps", "tours", "whats_new"}, code


def test_every_data_panel_and_virtual_page_has_a_help_page_in_both_locales():
    assert PANELS >= {"chat", "tasks", "settings", "governance"}
    expected = PANELS | VIRTUAL_PAGES
    for code in LOCALES:
        pages = set(_locale(code)["pages"])
        missing = expected - pages
        assert not missing, f"{code} has no help page for {sorted(missing)}"


FUTURE_PAGES = {"kanban", "modules", "apps", "memory_explorer"}

def test_every_page_id_is_a_panel_or_a_documented_virtual_page():
    for code in LOCALES:
        for page_id, page in _locale(code)["pages"].items():
            assert ID_RE.fullmatch(page_id), page_id
            if page_id in PANELS:
                assert "parent" not in page, page_id
            elif page_id not in FUTURE_PAGES:
                assert page_id in VIRTUAL_PAGES, f"{page_id} is neither a data-panel nor a virtual page"
                assert page.get("parent") in PANELS, page_id


def test_both_locales_share_ids_targets_and_gates():
    def skeleton(code):
        loc = _locale(code)
        pages = {
            pid: ({k: v for k, v in page.items() if k in STRUCTURAL},
                  [{k: v for k, v in s.items() if k in STRUCTURAL} for s in page["sections"]])
            for pid, page in loc["pages"].items()
        }
        steps = {sid: {k: v for k, v in s.items() if k in STRUCTURAL} for sid, s in loc["tour_steps"].items()}
        return pages, steps, loc["tours"], sorted(loc["whats_new"]), sorted(loc["ui"])

    assert skeleton("en") == skeleton("nl")
    for version in _locale("en")["whats_new"]:
        assert len(_locale("en")["whats_new"][version]) == len(_locale("nl")["whats_new"][version]), version


def test_dutch_is_translated_not_copied():
    en, nl = _locale("en"), _locale("nl")
    same = [pid for pid in en["pages"] if en["pages"][pid]["summary"] == nl["pages"][pid]["summary"]]
    assert not same, f"Dutch summaries equal to English: {same}"
    for sid, step in en["tour_steps"].items():
        assert step["body"] != nl["tour_steps"][sid]["body"], sid


def test_fields_have_the_documented_keys_and_types():
    for code in LOCALES:
        loc = _locale(code)
        for pid, page in loc["pages"].items():
            assert set(page) <= PAGE_KEYS, (code, pid, set(page) - PAGE_KEYS)
            assert isinstance(page["title"], str) and page["title"].strip(), (code, pid)
            assert isinstance(page["summary"], str) and page["summary"].strip(), (code, pid)
            assert isinstance(page["sections"], list), (code, pid)
            ids = [s["id"] for s in page["sections"]]
            assert len(ids) == len(set(ids)), (code, pid)
            for section in page["sections"]:
                assert set(section) <= SECTION_KEYS, (code, pid, section)
                assert ID_RE.fullmatch(section["id"]), (code, pid, section["id"])
                assert section["title"].strip() and section["body"].strip(), (code, pid, section["id"])
                assert section.get("dynamic", False) in (True, False)
            for rel in page.get("related", []):
                assert rel in loc["pages"] and rel != pid, (code, pid, rel)
            assert page.get("audience", "admin") in ("admin", "org"), (code, pid)
        for sid, step in loc["tour_steps"].items():
            assert ID_RE.fullmatch(sid), sid
            assert set(step) <= STEP_KEYS, (code, sid, set(step) - STEP_KEYS)
            assert step["title"].strip() and step["body"].strip(), (code, sid)
            assert ("target" in step) != ("nav" in step), f"{sid}: exactly one of target or nav"
            assert step.get("audience", "admin") in ("admin", "org"), (code, sid)
        for key in ("feedback_thanks", "sections_heading", "related_heading"):
            assert loc["ui"].get(key, "").strip(), (code, key)


def _targets():
    for code in LOCALES:
        loc = _locale(code)
        for pid, page in loc["pages"].items():
            if "enabled_if" in page:
                yield code, pid, page["enabled_if"], False
            for section in page["sections"]:
                if "target" in section:
                    yield code, f"{pid}.{section['id']}", section["target"], section.get("dynamic", False)
        for sid, step in loc["tour_steps"].items():
            if "target" in step:
                yield code, f"step.{sid}", step["target"], step.get("dynamic", False)


def test_every_target_uses_the_safe_selector_grammar():
    for code, where, target, _dynamic in _targets():
        assert TARGET_RE.fullmatch(target), (code, where, target)


def test_every_static_target_exists_in_index_html():
    for code, where, target, dynamic in _targets():
        match = TARGET_RE.fullmatch(target)
        if dynamic:
            continue
        if match.group("tour"):
            assert match.group("tour") in MARKUP.tours, (code, where, target)
        else:
            assert match.group("id") in MARKUP.ids, (code, where, target)


def test_every_static_nav_and_page_is_a_panel_of_index_html():
    for code in LOCALES:
        for sid, step in _locale(code)["tour_steps"].items():
            for key in ("nav", "page"):
                if key in step and not step.get("dynamic"):
                    assert step[key] in PANELS, (code, sid, key, step[key])


def test_data_tour_names_are_unique_in_the_markup():
    names = re.findall(r'data-tour="([^"]+)"', INDEX_HTML)
    assert len(names) == len(set(names)), sorted({n for n in names if names.count(n) > 1})


def test_tours_are_short_and_reference_known_steps():
    for code in LOCALES:
        loc = _locale(code)
        assert set(loc["tours"]) == {"first_run", "org_admin"}
        for tour, ids in loc["tours"].items():
            assert ids and len(ids) == len(set(ids)), tour
            assert all(sid in loc["tour_steps"] for sid in ids), tour
        # Getting started: 5 to 6 steps, all for every member.
        first = loc["tours"]["first_run"]
        assert 5 <= len(first) <= 6
        assert not any("audience" in loc["tour_steps"][sid] for sid in first)
        # The admin tour only ever shows to organisation admins.
        assert all(loc["tour_steps"][sid].get("audience") == "org" for sid in loc["tours"]["org_admin"])


def test_governance_help_is_for_admins_only():
    for code in LOCALES:
        assert _locale(code)["pages"]["governance"].get("audience") == "admin"


def test_realtime_voice_help_only_when_it_is_enabled():
    for code in LOCALES:
        assert _locale(code)["pages"]["realtime_voice"].get("enabled_if") == "[data-tour='chat-realtime-voice']"


def test_whats_new_is_keyed_by_version_with_cards():
    for code in LOCALES:
        whats_new = _locale(code)["whats_new"]
        assert whats_new, code
        for version, cards in whats_new.items():
            assert re.fullmatch(r"\d+\.\d+\.\d+", version), version
            assert cards and all(set(c) == {"title", "body"} for c in cards), (code, version)


@pytest.mark.parametrize("code", LOCALES)
def test_no_dashes_html_or_placeholders_in_any_string(code):
    for key, text in _strings(_locale(code)):
        for dash in DASHES:
            assert dash not in text, (code, key, text)
        assert "<" not in text and ">" not in text, (code, key, text)
        assert not re.search(r"&[a-zA-Z#][a-zA-Z0-9]*;", text), (code, key, text)
        assert text == text.strip() and "  " not in text, (code, key, text)


@pytest.mark.parametrize("code", LOCALES)
def test_no_internal_component_name_from_the_catalogue_denylist(code):
    denylist = CATALOG["display_denylist"]
    assert "n8n" in denylist and "Hermes" in denylist  # the fixture list, not a copy
    for key, text in _strings(_locale(code)):
        lowered = text.lower()
        hits = [name for name in denylist if name.lower() in lowered]
        assert not hits, (code, key, text, hits)


def test_module_keys_name_catalogue_ids():
    ids = {module["id"] for module in CATALOG["modules"]}
    seen = 0
    for code in LOCALES:
        loc = _locale(code)
        items = list(loc["pages"].values()) + list(loc["tour_steps"].values())
        items += [s for page in loc["pages"].values() for s in page["sections"]]
        for item in items:
            if "module" in item:
                seen += 1
                assert item["module"] in ids, item["module"]
            if "modules" in item:
                seen += 1
                assert isinstance(item["modules"], list) and item["modules"], item
                assert all(m in ids for m in item["modules"]), item["modules"]
    assert seen, "at least one help item is gated by a module"


def test_the_whole_file_has_no_dashes_or_remote_urls():
    text = CONTENT_JS.read_text(encoding="utf-8")
    assert not any(d in text for d in DASHES)
    assert "http://" not in text and "https://" not in text
