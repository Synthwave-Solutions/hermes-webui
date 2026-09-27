"""Personal memory self view routes under ``/api/mnemo/`` (scaffold stub).

Plan addendum Appendix AE (AE-7, AE-7b): package A6 fills these routes
(summary, list, edit, forget, export, erase and settings for the signed-in
person only). Until then every route answers 404, exactly like an unknown
route.
"""

from __future__ import annotations


def handle_get(handler, parsed) -> bool:
    """Read routes. The stub answers 404 (False)."""
    return False


def handle_post(handler, parsed, body) -> bool:
    """Write routes. The stub answers 404 (False)."""
    return False
