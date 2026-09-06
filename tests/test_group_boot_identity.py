from pathlib import Path
import subprocess


def test_empty_structured_conversations_survive_boot_restore():
    source = (Path(__file__).resolve().parents[1] / 'static/boot.js').read_text()
    start = source.index('function _isRestoredPersonalScratchSession(')
    helper = source[start:source.index('\nasync function ', start)]
    script = helper + """
const assert = require('node:assert/strict');
assert.equal(_isRestoredPersonalScratchSession({message_count:0}, null), true);
for (const session of [
  {participants:['bob@example.test']},
  {bot_participants:['default','writer']},
  {project_id:'team-project'},
  {project_shared:true},
]) assert.equal(_isRestoredPersonalScratchSession(session,null),false);
assert.equal(_isRestoredPersonalScratchSession({message_count:0},'explicit-id'),false);
assert.equal(_isRestoredPersonalScratchSession(null,null),false);
"""
    subprocess.run(['node', '-e', script], check=True)
    assert 'if(_isRestoredPersonalScratchSession(S.session, urlSession) &&' in source
