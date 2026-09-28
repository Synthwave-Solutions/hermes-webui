"""The Apps launcher route (scaffold stub).

Plan 3.7 and Appendix E.4.2: package W12 fills ``GET /api/apps`` with the
tiles of active modules that have their own screen, linked from
``SP_MODULE_LINKS`` and never from a request. Until then it answers 404,
exactly like an unknown route.
"""

from __future__ import annotations


def handle_get(handler, parsed) -> bool:
    """The caller's app tiles. The stub answers 404 (False)."""
    return False
