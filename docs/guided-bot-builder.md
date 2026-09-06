# Guided bot builder

`GET /api/bots/builder` returns a sanitized caller-filtered catalog and defaults.
An optional profile loads editable bot configuration. `POST /api/bots/builder`
validates instructions, skill names, selected shared MCP definitions, declared CLI
commands, model defaults, and allowed users/groups before publishing a new
profile directory. Creation omits revision; edits require the returned revision.
Invalid selections or images never expose a partially created bot.

Creation requires profiles:admin and active governance. New bots are private to
the authenticated owner unless users or groups are explicitly selected. Sharing
grants access to that bot only; it does not grant the recipient additional CLI,
MCP, skill, model, file, or integration privileges. Managed ACL checks cover bot
lists, avatar/profile targets, group routing and the governed worker. The bot
owner edits its configuration. Legacy profiles preserve their prior access model
until explicitly edited through this builder.

Bot prompt is SOUL.md, distinct from personal Agent Soul preferences. New bots
do not clone a person's .env, mailbox, history, or personal memory. Selected
shared server connection definitions and routing config remain server-side.
Catalog availability is permission/configuration visibility, not a successful
integration connection or paid inference test.

A per-run engine capability ceiling limits skills, MCP servers and CLI commands
in addition to the human's current governance. Fresh approval policy resolution
retains this ceiling; adding a human grant cannot unlock a tool excluded from the
bot. Copied-context children retain the ceiling and fresh ACL callback. A
serialized child lacking that trusted callback fails closed until rebound by a
trusted adapter. Arbitrary privileged host terminal execution remains a separate
host capability; this feature is not an operating-system sandbox.
