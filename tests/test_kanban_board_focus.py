"""Execute the board dialogs' focus lifecycle without a wall-clock race."""

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("mode, next_field", [("create", "SlugInput"), ("rename", "Desc")])
@pytest.mark.parametrize("close_before_timers", [False, True])
def test_board_modal_does_not_steal_focus_after_user_moves_or_closes(mode, next_field, close_before_timers):
    source = (Path(__file__).resolve().parents[1] / "static/panels.js").read_text()
    dialogs = source[source.index("function openKanbanCreateBoard(){"):source.index("async function submitKanbanBoardModal(){")]
    script = r"""
const assert = require('node:assert/strict');
const [mode, nextField, closeBeforeTimers] = JSON.parse(process.argv[1]);
const pending = [], elements = new Map();
const document = {
  activeElement: null,
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, {
      value: '', textContent: '', hidden: true, style: {},
      focus() { document.activeElement = this; },
      addEventListener() {}, removeEventListener() {},
    });
    return elements.get(id);
  },
  addEventListener() {}, removeEventListener() {},
};
const setTimeout = fn => pending.push(fn);
const t = key => key;
const _trapModalFocus = () => () => {};
let _kanbanBoardModalFocusCleanup = null;
const _kanbanCurrentBoard = 'qa-board';
const _kanbanBoardsList = [{slug: 'qa-board', name: 'Original'}];
""" + dialogs + r"""
if (mode === 'create') openKanbanCreateBoard(); else openKanbanRenameBoard();
const name = document.getElementById('kanbanBoardModalName');
const destination = document.getElementById('kanbanBoardModal' + nextField);
// Like a fast keyboard user, move to the next field before a delayed callback.
name.value = 'Exact board name';
destination.focus();
if (closeBeforeTimers) {
  closeKanbanBoardModal();
  document.getElementById('outside').focus();
}
const expectedFocus = document.activeElement;
while (pending.length) pending.shift()();
assert.equal(document.activeElement, expectedFocus, 'opening the dialog must not schedule a later focus steal');
if (!closeBeforeTimers) {
  document.activeElement.value += 'exact-new-value';
  assert.equal(name.value, 'Exact board name', 'typing in the next field must not corrupt the name');
  assert.ok(destination.value.endsWith('exact-new-value'));
}
// Opening a new dialog still gives keyboard users an immediate initial target.
if (mode === 'create') openKanbanCreateBoard(); else openKanbanRenameBoard();
assert.equal(document.activeElement, name, 'the visible dialog must focus its name before returning');
"""
    result = subprocess.run(
        ["node", "-e", script, json.dumps([mode, next_field, close_before_timers])],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
