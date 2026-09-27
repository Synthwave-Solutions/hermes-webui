"""Organisation routes under ``/api/org/`` (scaffold stub).

Plan 3.6 and Appendix E.1: package W3a fills the read-only routes
(``/api/org/overview``, ``/departments``, ``/people``, ``/approvals`` and
``/usage``), each enforcing ``delegated_scope()`` in the handler; W3b adds
the mutations in Wave 2. Until then every read answers 404 and every write
answers 405.
"""

from __future__ import annotations


def handle_get(handler, parsed) -> bool:
    """Read-only organisation routes. The stub answers 404 (False)."""
    return False


def handle_post(handler, parsed, body) -> bool:
    """Organisation mutations. The stub answers 405."""
    from api.helpers import j

    j(handler, {"error": "Method not allowed"}, status=405)
    return True
