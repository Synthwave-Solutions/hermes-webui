"""Visual answers in chat: the prompt block and its switch (scaffold stub).

Plan addendum Appendix AE (AE-5): ``api/streaming.py`` appends
``prompt_block(config_data)`` to the WebUI runtime instructions when it is
not empty. Package A1 fills it behind the ``webui_inline_svg`` setting,
which stays off by default. The stub adds nothing.
"""

from __future__ import annotations


def visuals_enabled(config_data=None) -> bool:
    """Whether the visuals prompt is on. The stub says no."""
    return False


def prompt_block(config_data=None) -> str:
    """The visuals prompt block, or an empty string. The stub returns ""."""
    return ""
