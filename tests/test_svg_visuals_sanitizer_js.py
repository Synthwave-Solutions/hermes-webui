"""The browser sanitiser in headless Chromium (plan addendum 3.5, package A1).

``tests/svg_visuals_sanitizer.cjs`` loads ``static/svg_visuals.js`` into a
Chromium page that has no network (its origin is served from memory and every
other request is refused and recorded), runs ``sanitizeSvgSource`` over the
shared fixture corpus and hydrates every fixture as a chat placeholder.

The node ``playwright`` package is read from this checkout's
``node_modules``, from ``HERMES_WEBUI_PLAYWRIGHT_MODULE``, or from the main
checkout of this git worktree (read only). The test skips with a reason only
when node, that package or its Chromium is missing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest

from api import svg_inline
from tests.test_svg_inline_validator import (
    BAD_EXPECTED,
    HOSTILE_SHAPES,
    SHAPE_SECONDS,
    banned_tokens,
    number_sources,
    run_shape,
)

REPO = Path(__file__).resolve().parents[1]
DRIVER = REPO / "tests" / "svg_visuals_sanitizer.cjs"
FIXTURES = REPO / "tests" / "fixtures" / "svg"
NODE = shutil.which("node")
SANITIZE_SHAPES = {name: shape for name, shape in HOSTILE_SHAPES.items() if shape[0] == "sanitize"}


def _playwright_dir():
    candidates = []
    env = os.environ.get("HERMES_WEBUI_PLAYWRIGHT_MODULE")
    if env:
        candidates.append(Path(env))
    candidates.append(REPO / "node_modules" / "playwright")
    try:
        common = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
        if common:
            candidates.append(Path(common).parent / "node_modules" / "playwright")
    except (OSError, subprocess.SubprocessError):
        pass
    for candidate in candidates:
        if (candidate / "package.json").is_file():
            return candidate
    return None


@lru_cache(maxsize=1)
def _matrix():
    if NODE is None:
        pytest.skip("node is not on PATH")
    module = _playwright_dir()
    if module is None:
        pytest.skip("the node playwright package is not installed (node_modules/playwright)")
    extra = json.dumps({"sources": number_sources(), "shapes": SANITIZE_SHAPES})
    proc = subprocess.run([NODE, str(DRIVER), str(module), str(REPO), extra], capture_output=True,
                          text=True, timeout=240)
    if proc.returncode != 0:
        if "Executable doesn't exist" in proc.stderr or "browserType.launch" in proc.stderr:
            pytest.skip("Chromium for playwright is not installed: " + proc.stderr.strip()[:200])
        raise AssertionError(proc.stderr[-4000:])
    return json.loads(proc.stdout)


def _read(key: str) -> str:
    return (FIXTURES / key).read_text(encoding="utf-8")


def _keys(kind: str) -> list:
    return sorted(f"{kind}/{p.name}" for p in (FIXTURES / kind).glob("*.svg"))


def test_every_good_fixture_passes_and_matches_the_python_sanitiser():
    results = _matrix()["results"]
    good = _keys("good")
    assert len(good) >= 12
    for key in good:
        js = results[key]
        py = svg_inline.sanitize_svg(_read(key))
        assert js["ok"] is True and js["reasons"] == [], (key, js["reasons"])
        assert js["title"] == py.title, key
        assert js["paper"] is py.paper, key
        box = js["box"]
        assert (box["x"], box["y"], box["width"], box["height"]) == py.box, key
        assert js["svg"].startswith('<svg xmlns="http://www.w3.org/2000/svg"'), key
        assert not banned_tokens(js["svg"]), key


def test_every_hostile_fixture_is_rejected_or_neutralised_like_python():
    results = _matrix()["results"]
    bad = _keys("bad")
    assert len(bad) >= 20
    for key in bad:
        js = results[key]
        code = BAD_EXPECTED[key.split("/", 1)[1]]
        py = svg_inline.sanitize_svg(_read(key))
        assert js["reasons"] == list(py.reasons), (key, js["reasons"], py.reasons)
        assert code in js["reasons"], key
        if code in svg_inline.REJECT_CODES:
            assert js["ok"] is False and js["svg"] == "" and js["reasons"][0] == code, key
        else:
            assert js["ok"] is True, key
        assert not banned_tokens(js["svg"]), (key, banned_tokens(js["svg"]))


def test_hydrating_the_hostile_corpus_runs_nothing_and_loads_nothing():
    render = _matrix()["render"]
    assert render["pwned"] is False
    assert render["requests"] == []
    assert render["errors"] == []
    assert render["liveSvgNodes"] == 0  # model SVG never enters the live DOM
    assert render["scriptNodes"] == 0
    assert render["foreignObjects"] == 0
    assert render["handlerNodes"] == 0


def test_hydration_shows_a_picture_or_the_code_with_a_notice():
    matrix = _matrix()
    results, rows = matrix["results"], matrix["render"]["rows"]
    assert set(rows) == set(results)
    for key, row in rows.items():
        assert row["placeholders"] == 0, key
        if results[key]["ok"]:
            assert row["figure"] and not row["blocked"], key
            assert row["srcPrefix"] == "data:image/svg+xml;base64,", key
            assert row["naturalWidth"] > 0, key  # the browser decoded the sanitised copy
            title = results[key]["title"]
            assert row["alt"] == (title or "Visual"), key
            assert row["caption"] == title, key
        else:
            assert row["blocked"] and not row["figure"], key
            assert row["fallbackIsSource"], key
    assert matrix["render"]["imageCount"] == sum(1 for r in results.values() if r["ok"])
    assert matrix["render"]["lazyImages"] == matrix["render"]["imageCount"]


def test_sizes_follow_the_same_number_grammar_as_python():
    sources = _matrix()["sources"]
    expected = number_sources()
    assert set(sources) == set(expected)
    for key, source in expected.items():
        js, py = sources[key], svg_inline.sanitize_svg(source)
        assert js["ok"] is py.ok and js["reasons"] == list(py.reasons), (key, js["reasons"], py.reasons)
        assert js["paper"] is py.paper, key
        if key.startswith(("viewbox-", "width-")):
            assert js["reasons"] == ["no_viewbox"], key
        else:
            assert js["paper"] is True, key


def test_hostile_shapes_sanitise_at_once_and_match_python():
    timing = _matrix()["timing"]
    assert len(SANITIZE_SHAPES) >= 5
    for name in SANITIZE_SHAPES:
        got = timing.get(name)
        assert got and not got.get("timedOut"), (name, got)
        assert got["ms"] < SHAPE_SECONDS * 1000, (name, got["ms"])
        assert got["value"] == run_shape(name)["value"], name
