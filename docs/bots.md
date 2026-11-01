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

Scout proactively reviews the person's open work and upcoming calendar, researches
preparation opportunities and posts useful briefings and proposals in Conversations.
Enable it with the sidebar radar button or the bot's Scout card. Each person chooses
their frequency, time and wishes; bot editors manage defaults, topics and followed
spaces. See **Proactive Scout schedules and conversations** below for the scheduling,
authorization and delivery contract.

## Responsibilities

The **Responsibilities** card on a bot's page records what the bot answers for: at most 12 items, each with a **title** (80 characters), an **objective** (300), **when** it acts (free text of 120 characters, such as daily 08:00 or on new mail), its **autonomy** (on its own, asks first, or report only; default asks first) and how it **reports** (120). They are stored as `responsibilities` in `ui_meta['hermes-bots']`, validated strictly and saved through `POST /api/profile/appearance` under the same revision as the rest of the bot; a damaged record reads as empty. Everyone who may see the bot reads the list; adding, editing and removing needs the right to edit the bot. People's own profiles have no card.

Chats whose active profile is the bot get a short "Jouw verantwoordelijkheden" block (at most 800 characters) in the WebUI runtime prompt, next to the knowledge index, one JSON object per responsibility under a line that says to treat them as data, not instructions. It is context only: it grants no tool, schedule or approval.

## Work of this bot

**Work of this bot** on the bot page lists the open Kanban tasks assigned to the bot (anything but done and archived) grouped by status, with blocked and review first; waiting for input and waiting for review are highlighted, and a task opens on the Kanban board. **Made** lists the latest 20 attachments of the bot's tasks with their task and date. The data comes from `GET /api/kanban/bot-work?profile=<bot>`, which keeps the board's gate (`sessions:read` on `/api/kanban`) and also needs a bot the viewer may use. Files download through `GET /api/kanban/attachment?id=<n>`: by attachment id only, from under the board's attachments folder (no symlinks, anchored open), always as a download, and a task assigned to a bot needs a bot the viewer may use.

With an explicit Bot Screen view grant, the section starts with a one-line **Bot screen** status from `GET /api/bot-screen/status?bot=<bot>`: no desktop yet, the bot is working on its screen, waiting for you with the bot's reason and, when the engine records when the bot asked (`help_since`), since what time and how long ago, or a person in control (named when the takeover went through this server) since a time. **Open screen** opens the existing Bot Screens viewer for that bot. The status call starts, takes and audits nothing and uses the same per-bot grants as the viewer; an unreadable lease reads as a person in control.

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

Choose **Talk to [bot name]** to target a bot using its stable ID. A message beginning with `@bot-id` does the same. With one bot, it can be selected automatically; with multiple bots, choose one explicitly. One selected bot responds per turn. Adding a bot does not itself start a turn. Explicit tool delegation can schedule a specialist or handoff as described below.

Responses show the selected bot's identity. The authenticated person who sent the message remains the authorization principal, even when another person owns the conversation. The selected bot supplies its runtime configuration and knowledge reference list; the conversation retains its workspace and shared history.

## Approval explanations

Approval cards show the capability and scope without requiring generated advice to load. New requests originating from a supported WebUI turn retain a redacted copy of the original human ask, capped at 400 characters. The first recorded ask is preserved when a capability request is repeated. Credential-shaped text is masked; this is a bounded summary, not a complete transcript.

Historical requests without this context are explicitly labelled as unavailable. Their original messages are not reconstructed or invented. Approving a request still requires reviewing its precise scope and current policy.

## Large capability selections

All catalog-backed options can be selected, up to the existing 10,000-entry request bound per capability list. Each entry must still be available under the editor's current grants. The former 100-entry sublimit blocked unchanged legacy bots with 154 CLI tools; it has been removed for existing and new bots. Narrowing a selection and later restoring permitted options works without a shrinking legacy quota.

### Proactive Scout schedules and conversations

Scout settings belong to a `(bot, person)` pair. Each person can override the
bot's `frequency` and `digest_time`, or inherit them. Supported frequencies are
`hourly`, `3h`, `6h`, `12h`, `daily` (the existing default), and `weekdays`.
Hourly schedules use the selected minute; multi-hour schedules use the selected
hour as their phase. Times use the cron scheduler's configured timezone.
Only bot editors can set `default_frequency` / `default_time` or another person's
settings. Changing a bot default reschedules existing subscribers; it does not
subscribe anyone new. Turning Scout off pauses only that person's job.

A scheduled round can now wake Scout without new news or task events. The
collector reads the job owner's primary calendar for the next seven days using
`gws-hermes --as <owner> calendar events list`, under the existing identity policy.
It never falls back to a shared account. Calendar reads are bounded (18 seconds,
40 events); missing access and truncation are reported as source limitations.
Personal memory, previous bot conversations, followed spaces and open work remain
scoped to the person. Immediate retries are debounced for 50 minutes.

Web research is available even without configured news topics. Scout prioritizes
preparation for the next 48 hours, connects available context, and provides up to
three researched briefings, drafts or proposals with sources. Private details
must not enter public searches. No email sending, calendar changes or external
execution is authorized. A round with nothing useful remains silent.

Scout result chats retain their `cron_job` provenance with `kind: scout` but appear
in **Conversations**. Other scheduled job chats stay under **Tasks**. Existing
Scout chats are upgraded on delivery; ownership and messages are preserved.
The tracked runner source lives in `scripts/scout/`; deploy it into the root
agent home's `scripts/scout/`, then synchronize enabled Scout profiles with
`scripts/scout_per_person_migrate.py --apply --sync`. Preserve custom prompt files.

Scout is an agent-backed Hermes background job (`no_agent: false`), with the
collector providing starting context. The skills toolset lets the agent discover
and read relevant available skills before research/preparation. Skill instructions
do not expand the owner's permissions or authorize outbound actions.
The collector also uses `gmail --as <owner> list/read` to include up to eight
recent inbox messages and three bodies, prioritizing unread messages. This bounded
selection excludes promotions/social mail, preserves unread state and reports
partial/unavailable reads. Email content is untrusted source data. Replies are
prepared as text in the conversation; nothing is sent or changed in Gmail.

Scout now inherits the bot's full configured CLI/WebUI tool surface, including
terminal/CLIs, skills, files, browser, delegation and enabled MCP servers; there
is no Scout-specific allowlist. Hermes resolves this selection on each Scout run,
so newly enabled or disabled bot tools take effect without recreating the job.
The stored list is a compatibility snapshot. Normal cron exclusions (interactive
clarification/messaging and recursive scheduling by default), disabled toolsets,
profile scope and the job owner's governance still apply. Tool access is distinct
from permission to send messages or perform irreversible external actions.

Scout also receives a rolling seven-day snapshot of the person's recent private
conversations with the same bot: up to eight chats, eight user/assistant messages
per chat, and 12,000 characters overall. This context is independent of the new-item
cursor, so an active topic remains visible after an earlier Scout round. It includes
prior answers to help identify decisions, unresolved questions and existing work;
an assistant's claim is not treated as proof of completion. Tool output, task chats,
shared chats and other people's conversations are excluded. Ownership, profile and
sharing are rechecked on the session file, not trusted solely from the cached index.

A person can additionally opt into `cross_bot_context` on each bot's Scout card.
This shares only that person's recent private conversations with other bots they
currently have access to, with the source bot attached to each excerpt. Explicit
managed-bot ACLs and the current governance policy are checked on every collection;
missing or invalid policy disables additional profiles. Other users are never
included, and source ownership/sharing/profile are rechecked on the session file.
The setting defaults to off and does not grant tools or access to another profile.

Scout's interface is integration-neutral: source selection belongs in the person's
instructions, using the skills and connections available to the bot. The Google
Chat space picker is no longer part of the UI; old stored source settings remain
readable for compatibility. Saving unrelated settings does not erase them.

Administrators open **Change person** in the Scout card to search eligible users,
see their saved on/off state and schedule, and select the person to configure.
The selected person's address stays visible above their instructions and schedule. Bot editors retain their existing management rights. The
picker loads on demand rather than slowing ordinary profile/sidebar requests.
The save revalidates the target person's current chat access to the bot; the job
continues to run and deliver as that person, never as the administrator.

### Personal conversation sections and task groups

The sidebar's **Conversations** view offers **New section**. Sections can contain
subsections without a fixed nesting depth. Use a section's `+` to add a child,
or its `…` to rename it or change its parent. The conversation `…` menu offers
**Move to section**, including the option to return to the top level. Removing
a section promotes its chats and subsections one level; it never deletes chats.
Pinned chats stay within their assigned section. Unassigned chats retain date groups.

**Tasks** groups scheduled-job chats by category and bot by default, with
category-only and bot-only options. Categories are suggested from job metadata
and titles; **Set task category** in a task chat's menu overrides the suggestion
for the current user. Clear the override to use the suggestion again. Search
reveals matching groups even when their sections were collapsed. Proactive
Scout conversations retain their existing Conversations classification.

Organization is stored per signed-in user on the server, separately from
projects, conversation content, task configuration, and access grants. Changing
the organization never shares a chat or changes a bot's permissions. Concurrent
edits use revisions and ask the losing editor to retry rather than overwrite
another tab's changes. There is no fixed nesting-depth limit; total stored
sections and assignments are bounded to protect service resources.

## Background specialists and group requests

Every authenticated bot turn can discover the user's accessible bots through
`delegate_to_bot(action="list")`. The default `action="delegate"` runs a bounded
task in the target's own profile, private sub-conversation and configured model.
Include necessary task context explicitly; the entire source history is not copied.
The coordinating bot is resumed with the specialist's result and synthesizes the
answer. The result notice links to the specialist conversation. Bots do not need
to be members of the same chat. Child conversations are view-only and owned by the
initiating human, including when that person is a guest in the originating group.

`mode="handoff"` retains direct replies by bots already in the conversation.
`action="request_join"` takes a reason in `task` and asks for human action using
the existing participant controls; it never changes membership. Prefer background
work unless ongoing shared participation is necessary.

Both source and target access are rechecked before dispatch and return. Target
restrictions and the originating permission ceiling remain enforced. One task can
be queued per turn and chains are bounded to four handoffs. Cancellation of the
originating turn cancels its pending task. An explicit busy response is retried;
ambiguous starts and work interrupted by restart are reported, never silently
replayed. Nested specialists must finish before an outer result is returned.

Bot Screens now shows the relevant primary action (start, take over or hand back).
Connection and administrator actions are in a separate disclosure, with a mode
badge indicating viewing, private control or an inactive screen. Privacy leases,
confirmation dialogs and access checks remain authoritative.

## Scheduled tasks and Scout in the bot editor

Existing bots have **Scout** and **Scheduled tasks** tabs in **Edit bot**.
Administrators and bot editors can open **Change person** to search the eligible
people list. Each row shows the saved enablement and schedule. Regular users see
only their own settings. If the directory is unavailable, own settings remain
usable and the directory offers a retry; missing users are never invented.

Start with **Prepare the day**, **Follow up on tasks**, or **Research opportunities**,
or write personal instructions. Suggestions append to existing text, never change
the schedule, and never enable extra conversation context. Use **Frequency** and
**Time** to set a personal schedule; **Follow bot time** makes inheritance explicit.
The preview uses the scheduler's configured timezone, not the browser's timezone.

**Save & activate Scout** starts the schedule; it does not immediately dispatch a
round. An existing active Scout offers **Save changes** and **Pause Scout**.
**Save without activating** saves an inactive setup. The delivery note explains
that useful results appear privately under this bot in **Conversations**. A round
with nothing useful can stay silent.

Personal drafts survive switching people and editor tabs in the current view.
They are held in memory on that view's profile object, not in browser storage;
leaving the bot editor or reloading releases them. Saving updates that person's
server state and revision in place, preserves other people's drafts and the bot
configuration draft, and never reloads the whole profiles screen. Failed saves
keep the draft with an inline error. Duplicate submissions are disabled, and a
late response cannot replace a different screen. A revision conflict still needs
a reload/review; the client never retries with a newer revision automatically.

**Shared bot defaults** is a separate disclosure and save action. It changes
shared topics and inherited timing, not personal enablement or explicit overrides.
Scout settings still save separately from the bot configuration draft.

Browser regression: `node tests/scout_person_setup_browser.cjs` (using the existing
Playwright installation via `PLAYWRIGHT_MODULE` and optionally `CHROMIUM_PATH`).
The fixture uses synthetic people and intercepted API responses; backend access,
revision and per-person isolation tests remain in `test_bot_scout_people.py`.
Desktop, laptop and phone evidence: [Scout setup comparison](scout-person-setup.md).

Scheduled tasks can be assigned from the existing editable task list. Assignment
uses the existing server access checks and preserves the task owner and schedule.
Managed Scout jobs are configured through Scout rather than reassigned here.
New scheduled tasks open the standard task form with the edited bot selected.
