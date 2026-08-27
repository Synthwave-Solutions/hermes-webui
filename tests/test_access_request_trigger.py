"""The ask behind an access request reaches the approver.

Reported 27 Aug 2026 ("Show administrators the initial user request behind each
governance request"): an approver saw the derived capability ("Skill:
vanzelf-gmail") but not what the person had actually asked for, which is the
context that makes the decision informed.

The chain: the WebUI exports the turn's user message in the agent env, the
engine redacts and truncates it before storing it on the request, the WebUI
carries it into the approvals payload, and the governance screen renders it as
escaped text.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

STREAMING = (REPO / "api" / "streaming.py").read_text(encoding="utf-8")
GRANTS = (REPO / "api" / "grant_requests.py").read_text(encoding="utf-8")
GOV_JS = (REPO / "static" / "governance.js").read_text(encoding="utf-8")


def test_webui_exports_the_turn_message_for_the_engine():
    assert "HERMES_SESSION_LAST_USER_MESSAGE" in STREAMING
    assert "user_message=msg_text if isinstance(msg_text, str) else None" in STREAMING


def test_export_is_bounded_so_a_huge_paste_cannot_bloat_the_env():
    assert "trigger[:2000]" in STREAMING


def test_ingest_carries_the_trigger_into_the_approvals_payload():
    assert '"trigger": str(item.get("trigger") or "")' in GRANTS


def test_absent_trigger_is_empty_never_invented():
    """No fallback text: an approver must be able to trust what they read."""
    assert 'item.get("trigger") or ""' in GRANTS
    assert "trigger.*unknown" not in GRANTS


def test_governance_screen_renders_the_trigger_as_escaped_text():
    assert "gov-trigger" in GOV_JS
    block = GOV_JS[GOV_JS.index("const trigger ="):][:700]
    assert "_govEsc(trigger)" in block, "the user's own words must never be raw HTML"
    assert "triggerHtml" in GOV_JS


def test_new_request_notifies_admins_out_of_band_but_carries_no_action():
    """A chat message is forwardable and replayable, so it announces the
    request and points at the WebUI; it never carries an approve link."""
    assert "_notify_admins_of_request" in GRANTS
    block = GRANTS[GRANTS.index("def _notify_admins_of_request"):][:2600]
    assert "Decide in the SynthPulse WebUI" in block
    for danger in ("approve?", "token=", "/decide", "action=approve"):
        assert danger not in block, f"remote decision surface leaked: {danger}"


def test_notification_is_off_until_a_destination_is_configured():
    block = GRANTS[GRANTS.index("def _notify_admins_of_request"):][:2600]
    assert "if not destination:" in block and "return False" in block
