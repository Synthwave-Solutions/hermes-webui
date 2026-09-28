"""Memory explorer routes under ``/api/memdash/`` (scaffold stub).

Plan Appendix E.7.5.1 (revision 6.1) and addendum 6.6: package A13 fills the
exact routes ``GET /api/memdash/banks``, ``GET /api/memdash/v1/view``,
``GET /api/memdash/access-log``, ``POST /api/memdash/v1/action``,
``POST /api/memdash/access-log/seen`` and ``POST /api/memdash/notice``. Until
then every route answers 404, exactly like an unknown route.
"""

from __future__ import annotations


def handle_get(handler, parsed) -> bool:
    """Read routes. The stub answers 404 (False)."""
    return False


def handle_post(handler, parsed, body) -> bool:
    """Write routes (behind the CSRF gate). The stub answers 404 (False)."""
    return False
