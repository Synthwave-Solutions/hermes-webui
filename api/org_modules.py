"""The Modules page routes (scaffold stub).

Plan 3.7 and Appendix E.4.2: package W12 fills ``GET /api/org/modules`` (what
the organisation has and can add, read-only from the local module resolver in
Wave 1, enforcing ``delegated_scope()`` in the handler) and
``POST /api/org/modules/request`` (the contact line in Wave 1; the central
request flow comes with W13 in Wave 2). Until then both answer 404, exactly
like an unknown route.
"""

from __future__ import annotations


def handle_get(handler, parsed) -> bool:
    """The organisation's modules. The stub answers 404 (False)."""
    return False


def handle_request(handler, body) -> bool:
    """Request a module. The stub answers 404 (False)."""
    return False
