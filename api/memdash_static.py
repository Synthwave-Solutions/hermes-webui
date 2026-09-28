"""The vendored Memory explorer document under
``/static/vendor/mnemosyne-dashboard/`` (scaffold stub).

Plan Appendix E.7.5.1 (revision 6.1): package A13 fills ``serve()``, which
serves only the pinned directory, refuses traversal (encoded included) and
sends the frame document with its own Content-Security-Policy. The route in
``api/routes.py`` never lets such a path fall through to the generic static
handler, so until A13 every such path answers 404.
"""

from __future__ import annotations


def serve(handler, parsed) -> bool:
    """Serve one vendored file. The stub serves nothing (False: 404)."""
    return False
