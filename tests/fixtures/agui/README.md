# AG-UI projection fixtures

Shared fixtures for the AG-UI 1.0 projection (program plan 5.1): the Python
projector in `api/agui.py` (package W5) and its browser port
`static/agui-projector.js` (package W10) are both checked against them. The
mapping is specified in `docs/rfcs/agui-projection-v1.md`.

## Files

| File | What it is |
|------|------------|
| `index.json` | The case list: name, journal, expected events and what the case covers. |
| `<case>.jsonl` | A recorded run journal, one row per line, in the exact format of `api/run_journal.py` (`version`, `event_id`, `seq`, `run_id`, `session_id`, `event`, `type`, `created_at`, `terminal`, `terminal_state`, `payload`). The rows were written with `append_run_event` itself; the payloads follow the shapes emitted by `api/streaming.py`, `api/todo_state.py`, `api/subagent_progress.py`, `api/route_approvals.py` and `api/clarify.py`. |
| `<case>.agui.json` | The AG-UI events `project_journal(rows)` must return for that journal, in order. |
| `ag-ui-1.0.schema.json` | The vendored AG-UI 1.0 JSON Schema (see below). |
| `ag-ui-1.0.schema.LICENSE` | The MIT license of the AG-UI project, which covers the schema. |

A port reproduces a case by feeding every row in order as
`feed(row.event, row.payload, seq=row.seq, timestamp=row.created_at)` and then
calling `finish(timestamp=<created_at of the last row>)`. `timestamp` is the
journal's `created_at` in seconds; events carry it as integer milliseconds.
Tool call argument text is compact JSON with sorted keys.

The redaction of `MESSAGES_SNAPSHOT` does not change these fixtures: they
contain no credential-shaped text.

## The vendored schema

- Source: `docs/spec/1.0/schema.json` of https://github.com/ag-ui-protocol/ag-ui
  at the release tag `ag-ui-protocol@1.0.0` (commit
  `f08ccf853497914ef70a5f0197af45bb74915bc2`), identical to the file served at
  its `$id`, `https://ag-ui.com/spec/1.0/schema.json`, on 28 September 2026.
- Upstream sha256: `4b5c93226838a0e72d88e6c5df20633c686c49fcb75d9be2815c6cbf9e48e71a`.
- One change: every U+2014 character (all 16 are inside `description`
  annotations) is replaced by an ASCII hyphen, because this repository's
  program rules forbid that character in added lines. No validation keyword is
  touched; the change is a plain text replacement that keeps the formatting:

  ```
  python3 -c "import sys; d = open(sys.argv[1], encoding='utf-8').read(); open(sys.argv[2], 'w', encoding='utf-8', newline='').write(d.replace(chr(0x2014), '-'))" schema.json ag-ui-1.0.schema.json
  ```

- Vendored sha256: `d6972043f6f2d7adaf59242ea89561825b2690bd06ede48064aac80a803cf168`,
  pinned in `tests/test_agui_projection.py` and `index.json`.

The schema is a test asset only. Nothing at runtime imports an AG-UI package
or validates against it.

## Updating

After a deliberate mapping change, rewrite the expected files with
`AGUI_UPDATE_GOLDEN=1` set while running `tests/test_agui_projection.py`,
review the diff, and update the RFC in the same change.
