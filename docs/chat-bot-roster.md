# Chat recipients and mentions

The bot roster above the composer can be collapsed and expanded. Its disclosure
preference belongs to the signed-in account in that browser. Collapsing it does
not change the selected bot or remove any group members.

Type `@` in the composer to search available bots and people. Results distinguish
bots from human accounts, including when their names are identical. Pick a result
with the keyboard or touch. A selected bot is the recipient for the next agent
response; multiple human mentions can join the same conversation.

Recipients are prepared when you send. Adding a human to a private conversation
starts a fresh group, without copying previous messages, files, personal memory,
or the private workspace. The existing private conversation remains available.
Add any intended shared attachments explicitly in the new group. Existing groups
keep their history; only their owner or an authorized administrator can add new
recipients. Project membership is managed through project controls.

The server is authoritative for known people, bot permissions, project membership
and dispatch. Mentioning someone never grants access to a bot or project. Failed
recipient preparation leaves the draft available. Recipient changes wait until
the current response is finished instead of silently becoming a steer or queue
entry for the previous audience.

Selecting a bot requires `chat:use`, not `profiles:admin`. Profile creation and
editing retain their administrative controls. Bot switches are per-client and do
not change another user's selected bot.

Assistant messages retain their server-selected bot name and avatar identity when
stored history is reconciled and reloaded. The client never infers the author
from response text.

Group uploads use the same authenticated session visibility check as opening the
chat and recheck current membership. A different process-wide active bot does
not prevent an authorized participant from attaching a file.

## Chats belong to a bot and a project

Selecting a bot restores the sidebar to that bot's conversations, including when
“All profiles” was previously enabled. Selecting the already active bot also
restores that filter. The project chips narrow this bot's list further. A
project filter is retained when the selected bot can use that project; otherwise
it is cleared. Existing unassigned chats stay unassigned.

Sharing a conversation or project grants access but does not place that chat in
every bot's list. The explicit all-profiles view and project hub remain ways to
browse across bots. Opening a specific chat from that aggregate view retains the
aggregate browsing context. Group recipient mentions still select who answers
inside the current group; they do not move that conversation to another bot.

New project conversations persist the selected bot as their primary profile and
the selected project ID. The sidebar's New Chat flow validates the selected bot
against the project's currently available bots. Project creation retries are
separate for each project/bot choice, so retrying does not silently adopt a chat
created for a different bot.

Older shared project conversations sometimes stored the project's general
presentation profile instead of a participating bot. Outside isolated-profile
mode, their sidebar projection uses the first participating bot when the stored
profile is not a participant. This is a read-only projection, not a migration of
history, workspace, project membership, or permissions. Isolated-profile mode
retains the original stored-profile boundary.

Verification: `tests/test_selected_bot_chat_scope.py`,
`tests/test_project_conversation_creation.py`, and the existing project/scope
suites exercise server filtering, persisted bot/project identity, current
membership and retry behavior. `node tests/selected_bot_scope_browser.cjs`
exercises the actual roster, profile switch and project partitioner against an
isolated API fixture at 1360px and 390px; it covers selected/already-selected
bots, failed switches and project retention/clearing. The new regressions fail
against the previous implementation.

Baseline limitations: the neighboring profile-filter suite has five existing
failures (default-alias and 404/409 expectations). The old session-new fixture
has two missing-save failures, and the engine file-scope integration test is
blocked by `governance_review_unavailable`. These reproduce unchanged before
this patch; no authorization rule is weakened to make those tests pass.
