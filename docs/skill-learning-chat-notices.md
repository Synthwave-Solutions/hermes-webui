# Automatic skill updates in chat

SynthPulse shows a small inline event when a native automatic background review
successfully creates, patches, or updates a skill. It appears in the original
conversation, is visible only to the human who initiated that turn, and survives
reload and server restart. It does not become a model message, shared transcript
entry, or fabricated tool call. Existing foreground tool activity stays unchanged.

The WebUI adapter observes structured `skill_manage` calls and matching successful
tool results in the native review summarizer. It supports flat and successful
atomic operations-array results. It ignores prior history, unmatched/duplicate
IDs, ambiguous results, explicit unchanged patches, failures, staged approvals,
and non-skill actions. Counts refer to confirmed operations, not distinct skills.
Names, paths, tool arguments, memory previews, and native summary text are never
stored or sent to the browser. Manual refine and foreground actions do not create
automatic notices. Absence of a notice does not prove a review ran with no changes.

An immutable actor, original session, profile home, and run context is captured
when the native review target is constructed. It does not consult mutable cached
agent callbacks after the user begins another turn. The wrapper installation is
idempotent, native return values/exceptions are preserved, and recording failures
cannot change the review result. No engine files, tool grants, or governance rules
change. This adapter depends on the native review target and summarizer contracts;
unsupported engines simply cannot produce these notices.

Storage contains only actor-hashed filenames, session/run hashes, timestamps, and
created/patched/updated counts. It stores at most 100 events per actor, shows only
the past 30 days, and prunes expired rows on each new append.
Private modes, regular-file checks, symlink/hardlink rejection, bounded file size,
bounded lock acquisition, atomic replacement, and fsync protect the store. Missing
platform primitives disable this optional storage without stopping chat.

`GET /api/skills/learning-activity?session_id=...` uses the signed request identity,
requires current conversation turn membership, and uses the narrow `chat:use`
permission for this metadata-only read. Skill file access and mutations retain
their existing permissions. It accepts no actor or profile filters, sends no-store
responses, and reports missing or unreadable storage truthfully. Administrators do
not acquire another person's activity by selecting their conversation.

The browser renders private cards directly among chat rows by event time. It
fetches only the current visible chat, at most once per ten seconds, with a
five-second request timeout and no automatic request retries. Session changes,
hidden tabs and page exit abort or stop polling. A generation check rejects late
responses after switching conversations. The real session loader invalidates
the activity view before its metadata await, so a previous chat's late response
cannot paint into the new conversation's loading or error placeholder.
Records never enter `S.messages`, local
storage, session exports, or the shared run journal. A temporary activity failure
has an inline Retry control and a normal subsequent refresh.

## Verification

Run `scripts/test.sh tests/test_skill_learning_activity.py` with both `PYTHONPATH`
and `HERMES_WEBUI_AGENT_DIR` set to the intended engine checkout. The regression
uses actual engine `07aad46435cf581ba2fe61edf6432ed491c17742`, real native skill
create/view/patch/batch operations in temporary directories, a failed patch, and an
unchanged patch. Only outbound skill-sync transport is stubbed. A separate real
native daemon-thread test overlaps A and B and verifies private attribution to A.
No provider call or production skill write is required or claimed.

The durable browser script is `tests/frontend/skill-learning-chat.cjs`. Its local
fixture uses the shipped renderer with synthetic count responses matching the
native test's create/patch outcomes. It checks chronological placement, rebuild
deduplication, retry, late-response rejection, reload, and desktop/mobile layouts.
Serve the repository on loopback and open
`tests/frontend/skill-learning-chat-fixture.html` for manual interaction.
