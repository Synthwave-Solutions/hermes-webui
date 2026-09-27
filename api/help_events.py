"""Help and tour usage counts ``POST /api/help/events`` (scaffold stub).

Plan section 6 and Appendix E.1: package W4 records counts only. The stub
answers 204 and stores nothing.
"""

from __future__ import annotations


def handle_post(handler, body) -> bool:
    """Record one help event. The stub answers 204 and stores nothing."""
    handler.send_response(204)
    handler.send_header("Content-Length", "0")
    handler.end_headers()
    return True
