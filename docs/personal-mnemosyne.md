# Personal Mnemosyne memory

Personal memory → Saved memories lists the signed-in person's automatically
saved messages. It supports search, pagination, editing and deletion. Saving a
change requires the revision originally read; stale edits receive HTTP 409.
Existing My notes, User profile and personal instructions remain available.

WebUI agents attach a person-scoped Mnemosyne provider at construction, including
recovery agents. Cached agents refresh the raw user text for each turn. Hermes'
existing memory-manager lifecycle recalls relevant records before the tool loop
and asynchronously saves the person's message after a completed response.
Interrupted/failed turns and assistant/tool conclusions are not saved as facts.
Messages are capped at 16,000 characters and credential patterns are redacted.
Images and attachments are not copied into memory. Existing chat history is not
backfilled; legacy bot banks are left untouched because their human ownership is
unknown. Edits affect subsequent recall, not already generated chat transcripts.

Banks live under the existing hashed authenticated actor's personal_context
folder. Private chats share one bank across bots and projects. Each shared chat
gets a separate bank per person: private memories are never recalled into a
shared chat, nor can one shared chat recall another's bank. Administrators do not
inherit another person's bank. The existing session membership and chat:use
checks protect the API; a client cannot choose its actor or filesystem path.

The Hermes runtime requires `mnemosyne-memory==3.15.1` (already supplied by the
Mnemosyne plugin in the managed stack). This adapter uses BEAM's working store
and FTS index, without legacy graph/canonical recall or automatic consolidation.
Working-memory expiry is disabled for these dedicated banks: owners delete their
own records. Recall is local FTS and capped at six records/6,000 characters; it
does not invoke an embedding service or a model. BEAM may compute embeddings on
background writes according to the existing deployment configuration.

Each operation owns and closes its SQLite connection. Writes use a per-bank
process/file lock; edits compare revisions under that same lock. Person-owned
DBs use mode 0600 beneath directories with mode 0700. Symlink paths are rejected.

Validation: `./scripts/test.sh -q tests/test_personal_mnemosyne.py
 tests/test_personal_context.py tests/test_personal_memory_ui.py` and
`node tests/personal_memories_browser.cjs`. The real SQLite test uses the installed
Hermes interpreter (`HERMES_WEBUI_PYTHON` override), isolated state, and disables
embeddings so no provider request occurs. Browser fixtures exercise desktop,
tablet and mobile layouts, editing, deletion, conflicts, XSS and late responses.
