# Bots

A bot is a Hermes profile with a friendly name and visual identity. Its stable profile ID still identifies its runtime configuration, instructions, skills, credentials and history. Changing its display name or photo does not rename that ID or change its permissions.

## Name and photo

Open **Bots**, select a bot and edit its name, description, avatar shape or colour. Choose **Save** to persist these fields. Upload your own PNG, JPEG or WebP image of at most 10 MB; the browser resizes it before the server validates and stores a PNG thumbnail of at most 512 pixels. Avatar images are served from this application, not an external tracking URL. Editing requires bot administration permission and access to the selected bot.

If another editor saved first, reload before saving again. Appearance uses the existing Hermes `ui_meta['hermes-bots']` metadata and revision contract. Concurrent editors in separate server processes are not covered by a shared cross-process lock.

## Org chart

In the same editor, **Reports to** links a bot to the bot it reports to, or to nobody (top level). **Department or role** is an optional short label of at most 80 characters. Both are stored as `reports_to` and `role` in `ui_meta['hermes-bots']` and follow the same revision contract. The server only accepts an existing bot, never the bot itself and never a choice that would create a reporting cycle; a new manager must also be a bot the editor can see. An unchanged value is kept even if that manager was removed later, so other fields stay editable.

Choose **Org chart** at the top of the Bots list to see the tree. Each leading bot (a bot without a manager, with bots below it) heads a grid of columns, one per direct report, with everyone below as compact one-line chips; the grid wraps to the screen width, so there is no sideways scrolling. Bots without a place are listed apart, and people and partners without bots below them sit in a collapsed **People and partners** strip. A search field narrows the chart. Click a bot to open it. Reports to describes structure only: it grants no permissions and does not route work between bots.

## Bot or person

**Kind** marks a profile as a bot or as a person's own profile (team member, partner), stored as `kind` in `ui_meta['hermes-bots']`. Unset, an unmanaged profile in the category Team or Partners counts as a person and everything else, SynthPulse and guided bots included, as a bot. `/api/profiles` returns the effective `bot_kind`. People get no Scout and appear in the org chart's people strip.

The editor's **Kind** select starts with **Automatic**, which stores no explicit kind so the default rule decides; while nothing is stored it shows what the rule decides now, for example Automatic (Person). Choosing Bot or Person stores that kind; choosing Automatic again clears it.

## Scout

Scout lets a bot look around once a day for news on its topics. Turn it on with the radar button next to the bot in the sidebar or on the bot's **Scout** card, where you also set up to 12 topics (at most 80 characters each) and the digest time (default 07:30). Settings live in `ui_meta['hermes-bots'].scout` as `{enabled, topics, digest_time}` and are saved through `POST /api/bots/scout`, which needs the same rights as editing the bot.

Turning Scout on copies the Scout runner files from the root profile's `scripts/scout/` into the bot's own `scripts/scout/` (the scheduler only runs scripts inside the job's own Hermes home) and creates or resumes one scheduled job in the bot's own task store, marked `managed_by: scout`. The job runs `scout/scout_collect.py` first and only wakes the agent when there is something new; the agent works read-only, files actionable items as triage tasks and writes at most one digest in the bot's task chat. In-app notifications for the job are off. Turning Scout off pauses the job; it is never deleted.

## Responsibilities

The **Responsibilities** card on a bot's page records what the bot answers for: at most 12 items, each with a **title** (80 characters), an **objective** (300), **when** it acts (free text of 120 characters, such as daily 08:00 or on new mail), its **autonomy** (on its own, asks first, or report only; default asks first) and how it **reports** (120). They are stored as `responsibilities` in `ui_meta['hermes-bots']`, validated strictly and saved through `POST /api/profile/appearance` under the same revision as the rest of the bot; a damaged record reads as empty. Everyone who may see the bot reads the list; adding, editing and removing needs the right to edit the bot. People's own profiles have no card.

Chats whose active profile is the bot get a short "Jouw verantwoordelijkheden" block (at most 800 characters) in the WebUI runtime prompt, next to the knowledge index, one JSON object per responsibility under a line that says to treat them as data, not instructions. It is context only: it grants no tool, schedule or approval.

## Work of this bot

**Work of this bot** on the bot page lists the open Kanban tasks assigned to the bot (anything but done and archived) grouped by status, with blocked and review first; waiting for input and waiting for review are highlighted, and a task opens on the Kanban board. **Made** lists the latest 20 attachments of the bot's tasks with their task and date. The data comes from `GET /api/kanban/bot-work?profile=<bot>`, which keeps the board's gate (`sessions:read` on `/api/kanban`) and also needs a bot the viewer may use. Files download through `GET /api/kanban/attachment?id=<n>`: by attachment id only, from under the board's attachments folder (no symlinks, anchored open), always as a download, and a task assigned to a bot needs a bot the viewer may use.

With an explicit Bot Screen view grant, the section starts with a one-line **Bot screen** status from `GET /api/bot-screen/status?bot=<bot>`: no desktop yet, the bot is working on its screen, waiting for you with the bot's reason, or a person in control (named when the takeover went through this server) since a time. **Open screen** opens the existing Bot Screens viewer for that bot. The status call starts, takes and audits nothing and uses the same per-bot grants as the viewer; an unreadable lease reads as a person in control.

## Waiting for you

**My approvals** starts with **Waiting for you**. It lists Kanban tasks in review or blocked for input (`block_kind` `needs_input`) of bots the viewer may use or that the viewer created (`GET /api/kanban/waiting`). Pending tool approvals in chats are not listed: they expire within a minute and are answered in the chat itself. A task opens on the board, takes a reply as a comment, or is unblocked through the existing Kanban routes. The viewer's own access requests stay listed below.

Bot screens that wait for a person (the agent asked for a takeover with a reason and nobody holds the screen) come first, only for viewers with the Bot Screens right to control that screen; **Open screen** opens the existing viewer for that bot, where the takeover itself is confirmed.
A task blocked for input whose bot's screen waits like that carries a **Take over screen** link on its own card as well.

In the sidebar, a bot whose screen waits for a person has a small dot next to its name (the reason is in its tooltip). The state is read from the same status call when the bot list loads, never on a faster timer, and only for screens the viewer may watch.

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

## Large capability selections

All catalog-backed options can be selected, up to the existing 10,000-entry request bound per capability list. Each entry must still be available under the editor's current grants. The former 100-entry sublimit blocked unchanged legacy bots with 154 CLI tools; it has been removed for existing and new bots. Narrowing a selection and later restoring permitted options works without a shrinking legacy quota.
