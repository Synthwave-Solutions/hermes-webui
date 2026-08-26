"""
text-selection-highlight ticket (Aug 2026): selecting text inside your OWN
chat bubbles must show a clearly visible highlight in both light and dark
themes, across every skin.

Root cause of the report: the ::selection override rules existed but every
--user-selection-bg token used a low alpha (0.16 to 0.24 for most skins),
which rendered a highlight too faint to perceive on the tinted bubble
backgrounds. This suite pins:

  1. the bubble-scoped ::selection AND ::-moz-selection rules (direct text
     plus nested markdown nodes),
  2. a minimum alpha of 0.30 on every --user-selection-bg token so the
     highlight stays visibly distinct from the bubble fill,
  3. token definitions in both the light and the dark scope of the default
     theme, so no mode falls back to an invisible default.

Run:
    ./scripts/test.sh tests/test_user_selection_visibility.py -v
"""
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).parent.parent
STYLE_CSS = (REPO_ROOT / "static" / "style.css").read_text(encoding="utf-8")

MIN_SELECTION_ALPHA = 0.30


def _selection_bg_declarations():
    """All --user-selection-bg declarations as (value, alpha) tuples."""
    out = []
    for m in re.finditer(r"--user-selection-bg:\s*([^;]+);", STYLE_CSS):
        value = m.group(1).strip()
        alpha_m = re.search(
            r"rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*(0?\.\d+|[01](?:\.\d+)?)\s*\)",
            value,
        )
        out.append((value, float(alpha_m.group(1)) if alpha_m else None))
    return out


# ── Rules exist and are scoped to the user bubble ────────────────────────────

def test_user_bubble_selection_rule_covers_body_and_descendants():
    """Both the bubble body and nested markdown nodes need the override."""
    assert '.msg-row[data-role="user"] .msg-body::selection,' in STYLE_CSS
    assert '.msg-row[data-role="user"] .msg-body *::selection {' in STYLE_CSS


def test_user_bubble_selection_has_moz_variant():
    """Firefox needs ::-moz-selection in its own rule (a shared selector list
    with ::selection would invalidate the whole rule in other engines)."""
    assert '.msg-row[data-role="user"] .msg-body::-moz-selection,' in STYLE_CSS
    assert '.msg-row[data-role="user"] .msg-body *::-moz-selection {' in STYLE_CSS


def test_selection_rules_use_the_shared_tokens():
    """The rules must consume the theme tokens, not hardcoded colors."""
    block = re.search(
        r'\.msg-row\[data-role="user"\] \.msg-body::selection,\s*'
        r'\.msg-row\[data-role="user"\] \.msg-body \*::selection \{([^}]*)\}',
        STYLE_CSS,
    )
    assert block, "user bubble ::selection rule not found"
    assert "var(--user-selection-bg)" in block.group(1)
    assert "var(--user-selection-text)" in block.group(1)


# ── Tokens are visible and defined for both modes ────────────────────────────

def test_every_selection_bg_token_meets_minimum_alpha():
    """A highlight below ~0.30 alpha is imperceptible on tinted bubbles.

    This is the regression the ticket reported: tokens existed but sat at
    0.16 to 0.24 alpha, reading as \"no visible selection highlight\".
    """
    decls = _selection_bg_declarations()
    assert decls, "no --user-selection-bg declarations found"
    for value, alpha in decls:
        assert alpha is not None, f"--user-selection-bg not rgba(): {value}"
        assert alpha >= MIN_SELECTION_ALPHA, (
            f"--user-selection-bg alpha {alpha} below {MIN_SELECTION_ALPHA}: "
            f"{value} would render a near-invisible highlight"
        )


def test_default_theme_defines_tokens_in_light_and_dark_scope():
    """Skins without their own tokens inherit the defaults; both the bare
    :root block and the :root.dark block must define the pair so neither
    mode falls back to an unset (invisible) value."""
    root_blocks = re.findall(r":root \{([^}]*)\}", STYLE_CSS)
    assert any("--user-selection-bg" in b and "--user-selection-text" in b
               for b in root_blocks), "default :root block misses selection tokens"
    dark_blocks = re.findall(r":root\.dark \{([^}]*)\}", STYLE_CSS)
    assert any("--user-selection-bg" in b and "--user-selection-text" in b
               for b in dark_blocks), ":root.dark block misses selection tokens"


def test_skins_that_restyle_user_bubbles_keep_selection_tokens_paired():
    """Every scope that defines --user-selection-bg also defines the text
    token right beside it, so no skin gets a fill without readable text."""
    for m in re.finditer(r"--user-selection-bg:[^;]+;", STYLE_CSS):
        tail = STYLE_CSS[m.end():m.end() + 120]
        assert "--user-selection-text:" in tail, (
            "--user-selection-bg declared without an adjacent "
            "--user-selection-text: " + m.group(0)
        )
