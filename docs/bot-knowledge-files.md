# Bot knowledge files

Open an existing bot and choose **Knowledge files**. Use **Upload documents from your computer**, tick the files the bot should use, then choose **Save knowledge**. Uploading a file alone does not select it. The selection is saved independently of **Save bot**; unfinished checkbox changes remain while switching editor tabs, and the editor requires saving the selection before saving the bot configuration.

Documents are stored with the selected bot, so the saved document index is available in that bot's future chats. They are shared with users who have access to that bot, rather than being copied from someone's personal memory or private chat. Existing workspace-relative knowledge references are displayed separately and preserved. To make those documents available across bot chats, upload the source documents using the picker.

Supported files: PDF, DOCX, Markdown, text, CSV and JSON; 10 MB per document, up to 100 stored documents and 30 selected documents. The picker lists documents previously uploaded to this bot, not arbitrary server files or other users' workspaces. Unsupported names or formats produce an error. Uploads with the same filename and content are deduplicated; different content receives a separate identifier.

The runtime provides a document index, not vector search or automatic extraction. The agent reads relevant documents through governed tools under the original authenticated sender. Existing tool permissions, read roots and approval requirements still apply; selecting a document does not grant permission to bypass them. File-format support during reading depends on the configured tools. Deselecting a document removes it from the index, but does not delete the stored file.

## State and authorization

`GET /api/bots/knowledge?profile=ID` and `POST /api/bots/knowledge` require `profiles:admin` and the same exact bot-owner edit guard as the guided builder. The POST actions are `upload` (filename and base64 bytes) and `select` (identifiers and metadata revision). Selection uses the independent `hermes-bots` metadata revision; builder and knowledge operations share the builder/metadata locks, so saving configuration preserves document selection.

Uploads are bound to the validated profile home, use directory handles with `O_NOFOLLOW` and exclusive file creation, and cannot import arbitrary paths. Document content is never returned by the picker API. The runtime rechecks the actor's bot access while holding the same lock before emitting selected references. Missing identity, revoked bot access, invalid targets and symlinks fail closed.

Verification: `tests/test_bot_knowledge.py` covers persisted selection, preservation through builder save, cross-bot isolation, owner-only management, revocation, traversal/symlinks, malformed targets/revisions and the real engine's read-root allow/deny policy.
