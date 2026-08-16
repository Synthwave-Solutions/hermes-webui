"""Frontend guards for the gateway-SSE reconnect loop on a 404 probe.

Server side, /api/sessions/gateway/stream?probe=1 used to skip the per-user
isolation gate that the stream itself applies, so a non-admin got a green probe
(200, watcher_running=true) and a 404 on the stream. The frontend read the probe
as healthy, opened the EventSource, took the 404, and re-probed from onerror.
Measured on the live server at ~23 requests per second per open tab: 10.8k
stream 404s plus 10.3k rate-limited client-event POSTs in 24 hours.

The server fix (probe and stream answer identically for every identity) is
covered by tests/test_gateway_sync.py. These are the client-side guards that
keep the loop from restarting even if a server ever disagrees again:

  1. probeGatewaySSEStatus() treats 404 like 403, a permanent answer that
     polling cannot fix, and arms the backoff instead of re-entering.
  2. startGatewaySSE() honours that backoff too. It has roughly a dozen direct
     callers (boot, workspace switch, settings, visibilitychange), so guarding
     only the probe would leave every one of them able to restart the loop.
  3. The Settings panel clears the backoff when it applies show_cli_sessions,
     so an admin who just enabled agent sessions does not sit out the window.

Source-grep checks: these paths live in static JS with no server round trip.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SESSIONS_JS = (REPO_ROOT / "static" / "sessions.js").read_text(encoding="utf-8")
PANELS_JS = (REPO_ROOT / "static" / "panels.js").read_text(encoding="utf-8")


def _block(src: str, marker: str, size: int) -> str:
    start = src.find(marker)
    assert start != -1, f"marker not found: {marker}"
    return src[start:start + size]


def test_probe_treats_404_like_403():
    """A 404 probe must arm the backoff, not fall through to the retry paths."""
    block = _block(SESSIONS_JS, "async function probeGatewaySSEStatus()", 1400)
    assert "resp.status === 403 || resp.status === 404" in block, (
        "404 (feature absent for this identity) must take the same permanent-"
        "answer path as 403, otherwise onerror re-probes in a tight loop"
    )


def test_probe_404_arms_backoff_before_the_watcher_branches():
    """The 403/404 branch must return before the watcher_running branches.

    An isolated probe reports watcher_running from the real watcher. If the 404
    fell through, `resp.ok && data.watcher_running` would reopen the stream and
    the loop would resume.
    """
    block = _block(SESSIONS_JS, "async function probeGatewaySSEStatus()", 2000)
    denied = block.find("resp.status === 403 || resp.status === 404")
    reopen = block.find("resp.ok && data.watcher_running")
    fallback = block.find("resp.status === 503")
    assert denied != -1 and reopen != -1 and fallback != -1
    assert denied < reopen < fallback, (
        "the denied branch must be evaluated first and return"
    )
    assert "_gatewayProbeForbiddenUntil = Date.now() + 300000;" in block
    assert "stopGatewaySSE();" in block


def test_start_gateway_sse_honours_the_backoff():
    """startGatewaySSE must not open a stream inside the backoff window."""
    block = _block(SESSIONS_JS, "function startGatewaySSE()", 1400)
    guard = block.find(
        "if(_gatewayProbeForbiddenUntil && Date.now() < _gatewayProbeForbiddenUntil) return;"
    )
    opened = block.find("new EventSource('api/sessions/gateway/stream')")
    assert guard != -1, (
        "startGatewaySSE has ~12 direct callers; without this guard a boot, "
        "workspace switch or tab focus restarts a denied stream"
    )
    assert opened != -1
    assert guard < opened, "the backoff guard must run before the EventSource opens"


def test_settings_clears_the_backoff_when_enabling_agent_sessions():
    """Turning the feature on in Settings must not wait out the 5 minute window."""
    assert "function resetGatewayProbeBackoff()" in SESSIONS_JS
    assert "window.resetGatewayProbeBackoff = resetGatewayProbeBackoff;" in SESSIONS_JS
    idx = PANELS_JS.find("if(typeof resetGatewayProbeBackoff==='function') resetGatewayProbeBackoff();")
    assert idx != -1, "the Settings apply path must clear the backoff"
    assert "startGatewaySSE();" in PANELS_JS[idx:idx + 200], (
        "the reset only makes sense immediately before the reconnect attempt"
    )
