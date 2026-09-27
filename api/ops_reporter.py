"""Operational error reporting to the control plane (scaffold stub).

Plan Appendix E.1: package W7 fills ``POST /api/client-errors`` (size and
rate limits, allowlist and redaction before anything is spooled) and the
``support_telemetry`` flag that ``GET /api/settings`` returns. The stub keeps
browser reporting off and stores nothing.
"""

from __future__ import annotations


def browser_reporting_enabled() -> bool:
    """Whether the browser may send error reports. The stub says no."""
    return False


def handle_client_error(handler, body) -> bool:
    """``POST /api/client-errors``. The stub answers 204 and stores nothing."""
    handler.send_response(204)
    handler.send_header("Content-Length", "0")
    handler.end_headers()
    return True
