from pathlib import Path
from tests.helpers import live_sse_handler


ROOT = Path(__file__).resolve().parents[1]
MESSAGES_JS = (ROOT / "static" / "messages.js").read_text(encoding="utf-8")
STREAMING_PY = (ROOT / "api" / "streaming.py").read_text(encoding="utf-8")
CHANGELOG = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def _tool_complete_listener_block() -> str:
    return live_sse_handler(MESSAGES_JS, 'tool_complete')


def test_tool_complete_notifies_on_persistent_state_writes():
    assert "function _maybeNotifyPersistentStateSaved(tool)" in MESSAGES_JS
    block = _tool_complete_listener_block()

    assert "_maybeNotifyPersistentStateSaved(tc);" in block
    assert block.index("tc.is_error=!!d.is_error;") < block.index("_maybeNotifyPersistentStateSaved(tc);")
    assert block.index("if(!S.session||S.session.session_id!==activeSid) return;") < block.index("_maybeNotifyPersistentStateSaved(tc);")
    assert block.index("_maybeNotifyPersistentStateSaved(tc);") < block.index("refreshOpenPreviewIfMutated")


def test_persistent_state_toast_classifier_is_write_only_and_deduped():
    helper_start = MESSAGES_JS.index("function _persistentToastHasWriteIntent")
    helper_end = MESSAGES_JS.index("function _persistentToastSkillName", helper_start)
    helper = MESSAGES_JS[helper_start:helper_end]

    assert "read|list|view|search|lookup|get|fetch|load|usage|toggle|delete|remove" in helper
    assert "save|saved|write|wrote|written|update|updated|create|created|store|stored|persist|persisted|remember|remembered" in helper
    assert "_persistentStateToastSeen.has(dedupeKey)" in MESSAGES_JS
    assert "_persistentStateToastSeen.add(dedupeKey)" in MESSAGES_JS
    assert "_showPersistentStateToast(isSkill?'skill':'memory'" in MESSAGES_JS
    assert "if(isSkill&&!skillName)return;" in MESSAGES_JS


def test_persistent_state_toasts_use_existing_user_visible_labels():
    notify_start = MESSAGES_JS.index("function _maybeNotifyPersistentStateSaved")
    notify_end = MESSAGES_JS.index("function _selectedTextReplyT", notify_start)
    notify = MESSAGES_JS[notify_start:notify_end]

    assert "t('memory_saved')" in notify
    assert "t('skill_created')" in notify
    assert "t('skill_updated')" in notify
    assert "showToast(itemName?`${base}: ${itemName}`:base,4200,'success')" in notify
    assert "showToast(t('memory_saved'),3600,'success')" in notify


def test_backend_emits_state_saved_sse_from_file_snapshots():
    assert "def _persistent_state_snapshot" in STREAMING_PY
    assert "def _persistent_state_changes" in STREAMING_PY
    assert '_persistent_state_before = _persistent_state_snapshot(_profile_home, str(_personal_root))' in STREAMING_PY
    assert 'put("state_saved", {' in STREAMING_PY
    assert '"kind": "memory"' in STREAMING_PY
    assert '"kind": "skill"' in STREAMING_PY


def test_frontend_handles_state_saved_sse_and_reuses_dedupe():
    start = MESSAGES_JS.index("source.addEventListener('state_saved'")
    end = MESSAGES_JS.index("source.addEventListener('title'", start)
    block = MESSAGES_JS[start:end]

    assert "_showPersistentStateToast(d.kind, d.name||''" in block
    assert "String(d.action||'').toLowerCase()==='created'" in block
    assert "if((d.session_id||activeSid)!==activeSid) return;" in block
    assert "'state_saved'" in MESSAGES_JS


def test_issue_3340_changelog_entry_present():
    assert "#3340" in CHANGELOG
    assert "saved memory" in CHANGELOG
    assert "created/updated a skill" in CHANGELOG


def test_refused_or_staged_writes_do_not_report_a_save():
    """Reported by Michael on 20 Sep 2026: the toast said a skill was created
    while skill_manage had been blocked by governance, so it never showed up
    in the Skills library. A refusal or a staged, unapproved change saved
    nothing and must not produce a "saved" toast; a real save still does."""
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("node not on PATH")
    start = MESSAGES_JS.index("function _persistentToastHasWriteIntent(")
    body_start = MESSAGES_JS.index("{", MESSAGES_JS.index(")", start))
    depth = 0
    for end in range(body_start, len(MESSAGES_JS)):
        if MESSAGES_JS[end] == "{":
            depth += 1
        elif MESSAGES_JS[end] == "}":
            depth -= 1
            if depth == 0:
                break
    helper = MESSAGES_JS[start:end + 1]
    cases = [
        ["skill_manage", '{"success": false, "error": "not_allowed"} create skill'],
        ["skill_manage", '{"staged": true, "pending_id": "p1"} created'],
        ["memory", "Blocked by governance: requires approval before it is saved"],
        ["skill_manage", '{"success": true, "message": "Skill created"}'],
        ["memory", "Saved to memory"],
    ]
    driver = helper + "\nprocess.stdout.write(JSON.stringify(" + json.dumps(cases) + ".map(([n,t])=>_persistentToastHasWriteIntent(n,t))));"
    out = subprocess.run([node, "-e", driver], text=True, capture_output=True, timeout=30, check=False)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout) == [False, False, False, True, True]
