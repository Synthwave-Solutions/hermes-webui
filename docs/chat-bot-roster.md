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
