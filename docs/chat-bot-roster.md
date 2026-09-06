# Chat bot recipients

The avatar roster above the composer uses the authenticated profile list. In a
personal chat, selecting another bot uses the existing profile switch, preserving
profile history boundaries. In a group, only assigned bots visible to the sender
appear. Clicking one inserts or replaces a leading `@bot-id` in the message draft.
The literal recipient travels with the message through sending and queues; there
is no separate hidden recipient state.

The server remains authoritative: group membership, project assignments and bot
access are checked before dispatch and again in the execution worker. Adding a
name to a draft does not grant access or add a group participant. A profile lookup
failure displays an unavailable state and never exposes a cached global roster.
