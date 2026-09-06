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

Selecting a bot requires `chat:use`, not `profiles:admin`. The body-selected
profile still has to be permitted by the caller policy. Both member and admin
switches are per-client (`process_wide=False`), with a signed profile cookie;
they do not change another user’s active profile. Profile creation and editing
remain administrative actions. Rejected writes before body consumption close
the HTTP connection so unread JSON cannot become a subsequent request.
