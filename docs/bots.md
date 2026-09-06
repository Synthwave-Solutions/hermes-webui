# Bots

A bot is a Hermes profile with a friendly name and visual identity. Its stable profile ID still identifies its runtime configuration, instructions, skills, credentials and history. Changing its display name or photo does not rename that ID or change its permissions.

## Name and photo

Open **Bots**, select a bot and edit its name, description, avatar shape or colour. Choose **Save** to persist these fields. Upload your own PNG, JPEG or WebP image of at most 10 MB; the browser resizes it before the server validates and stores a PNG thumbnail of at most 512 pixels. Avatar images are served from this application, not an external tracking URL. Editing requires bot administration permission and access to the selected bot.

If another editor saved first, reload before saving again. Appearance uses the existing Hermes `ui_meta['hermes-bots']` metadata and revision contract. Concurrent editors in separate server processes are not covered by a shared cross-process lock.

## Instructions, tools and knowledge

Open **Bots**, select an existing bot and choose **Edit bot**, or choose a section shortcut. The editor has directly selectable **Identity & photo**, **Instructions**, **Memory & knowledge**, **Skills**, **Connections & tools**, and **Access** tabs. Keyboard users can move through tabs with Left/Right or Home/End. Each shortcut opens the requested section. Draft instructions and other configuration changes are retained when switching tabs. Choose **Save bot** to save configuration; editing does not switch the active chat profile.

**Bot memory** is explicitly shared reference context for users of that bot. It is stored in the bot's dedicated `BOT_MEMORY.md`, with the bot configuration revision and rollback transaction. It never reads or replaces legacy `memories/MEMORY.md`, My Notes, User Profile or another person's memory. Runtime adds these shared notes only after checking the current authenticated sender's bot access.

**Knowledge files** uses a file selector. Upload documents from your computer, choose the uploaded documents in the list, then choose **Save knowledge**. Knowledge selections are saved separately from **Save bot**. An upload alone does not select a document for the bot. Supported formats are PDF, DOCX, Markdown, text, CSV and JSON, at most 10 MB per document and 30 selected documents. Files are stored under the selected bot, so the selection is available across that bot's chats. Previously configured workspace-relative references are preserved and remain dependent on each conversation's workspace.

The runtime supplies an index of selected, existing bot documents. The agent must read relevant documents through the governed file tool under the original authenticated human sender. Bot access and file/tool permissions are separate checks: a selected document does not bypass a denial or approval. File contents are reference data, not instructions or an access grant. Reader support determines whether a format can be extracted. This is a document reference library, not a vector database or automatic full-document prompt attachment.

MCP connections and CLI tools are selected from capabilities available to the editor; credentials stay on the server. Existing selections that are no longer available are shown explicitly rather than silently removed. Editing and selecting knowledge requires bot administration permission and, for managed bots, ownership. Access tab changes do not expand the human sender's underlying tool grants.

## People and bots in a group

Use the conversation's participant picker to add people and up to six bots. Available bots are constrained by access, and bot access is checked again when a turn starts. Human membership and bot selection do not grant additional tool or data permissions.

Choose **Talk to [bot name]** to target a bot using its stable ID. A message beginning with `@bot-id` does the same. With one bot, it can be selected automatically; with multiple bots, choose one explicitly. One selected bot responds per turn. This does not start an automatic multi-bot discussion or chain of handoffs.

Responses show the selected bot's identity. The authenticated person who sent the message remains the authorization principal, even when another person owns the conversation. The selected bot supplies its runtime configuration and knowledge reference list; the conversation retains its workspace and shared history.

## Approval explanations

Approval cards show the capability and scope without requiring generated advice to load. New requests originating from a supported WebUI turn retain a redacted copy of the original human ask, capped at 400 characters. The first recorded ask is preserved when a capability request is repeated. Credential-shaped text is masked; this is a bounded summary, not a complete transcript.

Historical requests without this context are explicitly labelled as unavailable. Their original messages are not reconstructed or invented. Approving a request still requires reviewing its precise scope and current policy.
