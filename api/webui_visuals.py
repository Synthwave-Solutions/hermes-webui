"""Visual answers in chat: the prompt block and its switch.

Plan addendum 4.1 and 4.2. ``api/streaming.py`` (seam AE-5) appends
``prompt_block(config_data)`` to the WebUI runtime instructions right after
the artifact delivery block, and only when it is not empty. The same builder
serves Gateway-routed WebUI chats (``api/gateway_chat.py``), so every
browser turn gets the same text. Messaging platforms and realtime voice build
their own prompts and never see it.

The switch is ``webui_inline_svg`` in the config. The environment variable
``HERMES_WEBUI_INLINE_SVG`` (``1`` or ``0``) overrides it. The default is off
(decision D27); a later release turns it on once the adoption targets are met.
"""

from __future__ import annotations

import os

CONFIG_KEY = "webui_inline_svg"
ENV_VAR = "HERMES_WEBUI_INLINE_SVG"
DEFAULT_ENABLED = False

_TRUE = frozenset(("1", "true", "yes", "on"))
_FALSE = frozenset(("0", "false", "no", "off"))

# Exact text of plan addendum 4.2. It is re-sent on every call and holds no
# example SVG; the visual-explainer skill carries the templates.
WEBUI_VISUALS_PROMPT = """
WebUI visuals:
- This chat renders ```svg and ```mermaid fenced blocks as pictures. Draw one when a picture explains faster than prose: a process or flow, an architecture or layer stack, a comparison, a timeline, a cycle, a 2x2 matrix, proportions or a before and after.
- Do not draw for short factual answers, for drafts of emails or chat messages, or for text the user will paste elsewhere. Use at most one visual per reply unless the user asks for more.
- Use ```mermaid for flowcharts, sequence, state and gantt diagrams. Use ```svg for custom explainers.
- SVG rules: one <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H" role="img"> with W at most 720 and no width or height attributes; start with <title>; no script, event handlers, foreignObject, image, links, url() other than #ids, @import or web fonts; text at least 12px; about 12 labels at most; under 8 KB.
- Colours: use currentColor and var(--sp-fg,#1f2937), var(--sp-muted,#6b7280), var(--sp-accent,#f97316), var(--sp-surface,#f3f4f6), var(--sp-border,#d1d5db) so the visual follows the light or dark theme. Never hardcode black or white text.
- Write labels in the user's language and always add one sentence that states the takeaway, so the answer still works without the picture.
- A saved .svg file is delivered with MEDIA: as described above. For richer patterns, load the skill visual-explainer when it is available.
""".strip()


def _parse_flag(value):
    """Return True or False for a recognised switch value, else None."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0 if value in (0, 1) else None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE:
            return True
        if normalized in _FALSE:
            return False
    return None


def visuals_enabled(config_data=None) -> bool:
    """Whether the visuals prompt is on for this turn.

    The environment override wins over the config key; anything that is not
    a recognised yes or no value falls through to the next source and, in the
    end, to the default (off).
    """
    env_value = _parse_flag(os.environ.get(ENV_VAR))
    if env_value is not None:
        return env_value
    if isinstance(config_data, dict):
        config_value = _parse_flag(config_data.get(CONFIG_KEY))
        if config_value is not None:
            return config_value
    return DEFAULT_ENABLED


def prompt_block(config_data=None) -> str:
    """The visuals prompt block when the switch is on, else ``""``."""
    return WEBUI_VISUALS_PROMPT if visuals_enabled(config_data) else ""
