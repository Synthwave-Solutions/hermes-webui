# Bots

A bot is a Hermes profile with a friendly name and visual identity. Its stable profile ID still identifies its runtime configuration, instructions, skills, credentials and history. Changing its display name or photo does not rename that ID or change its permissions.

## Name and photo

Open **Bots**, select a bot and edit its name, description, avatar shape or colour. Choose **Save** to persist these fields. Upload your own PNG, JPEG or WebP image of at most 2 MB; the server validates and converts it to a PNG thumbnail of at most 512 pixels. Avatar images are served from this application, not an external tracking URL. Editing requires bot administration permission and access to the selected bot.

If another editor saved first, reload before saving again. Appearance uses the existing Hermes `ui_meta['hermes-bots']` metadata and revision contract. Concurrent editors in separate server processes are not covered by a shared cross-process lock.

## Instructions, tools and knowledge

The bot detail card shows its prompt file, explicitly configured toolsets and MCP server names, memory and skills locations. Its configuration buttons select that bot before opening the existing instructions, memory, skills, tools/settings or workspace editor. These entry points use the existing profile configuration; they do not install a new CLI or create a separate credential system. Default or inherited tool configuration is labelled accordingly. The human sender's governance policy still limits execution.

**Knowledge source files** stores an explicit list of workspace-relative document paths, one per line, such as `docs/product.md`. Upload the documents into the conversation's workspace first. Up to 30 references can be saved; supported extensions are `.md`, `.txt`, `.csv`, `.json`, `.pdf` and `.docx`.

At each turn, the selected bot receives an index of existing, contained file references for the current conversation workspace. It must read relevant documents through the governed file tool under the original human sender. Missing files and paths escaping the workspace are omitted. File content is source data, not instructions or an access grant. Reader support determines whether a document format can be extracted. This is a reference list, not a vector database, indexing service or automatic full-document prompt attachment.

## People and bots in a group

Use the conversation's participant picker to add people and up to six bots. Available bots are constrained by access, and bot access is checked again when a turn starts. Human membership and bot selection do not grant additional tool or data permissions.

Choose **Talk to [bot name]** to target a bot using its stable ID. A message beginning with `@bot-id` does the same. With one bot, it can be selected automatically; with multiple bots, choose one explicitly. One selected bot responds per turn. This does not start an automatic multi-bot discussion or chain of handoffs.

Responses show the selected bot's identity. The authenticated person who sent the message remains the authorization principal, even when another person owns the conversation. The selected bot supplies its runtime configuration and knowledge reference list; the conversation retains its workspace and shared history.

## Approval explanations

Approval cards show the capability and scope without requiring generated advice to load. New requests originating from a supported WebUI turn retain a redacted copy of the original human ask, capped at 400 characters. The first recorded ask is preserved when a capability request is repeated. Credential-shaped text is masked; this is a bounded summary, not a complete transcript.

Historical requests without this context are explicitly labelled as unavailable. Their original messages are not reconstructed or invented. Approving a request still requires reviewing its precise scope and current policy.
