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
Confirmed changes now include a short skill display name and action, with a count
for repeated changes to that name. Names come only from the matched successful
operation, not its prose summary. File paths, tool arguments, memory previews and
native summary text are never sent to the browser. Older count-only events remain
readable and explicitly say that the skill name was not recorded; names are not
reconstructed from unrelated later history. Manual refine and foreground actions do not create
automatic notices. Absence of a notice does not prove a review ran with no changes.

An immutable actor, original session, profile home, and run context is captured
when the native review target is constructed. It does not consult mutable cached
agent callbacks after the user begins another turn. The wrapper installation is
idempotent, native return values/exceptions are preserved, and recording failures
cannot change the review result. No engine files or access grants change; the
new exact read-route alias keeps the existing metadata permission. This adapter depends on the native review target and summarizer contracts;
unsupported engines simply cannot produce these notices.

Storage contains only actor-hashed filenames, session/run hashes, timestamps, and
created/patched/updated counts and bounded skill metadata. A validated logical
skill identifier (at most two slug segments) is retained only on the server for
current authorization; it is never included in the response. At most 50 short names
(up to 64 characters) are retained per event. Oldest events are pruned before an
atomic write would exceed the 128 KiB read limit; total counts are not fabricated
when a name is unavailable or the detail limit is reached. It stores at most
100 events per actor, shows only
the past 30 days, and prunes expired rows on each new append.
Private modes, regular-file checks, symlink/hardlink rejection, bounded file size,
bounded lock acquisition, atomic replacement, and fsync protect the store. Missing
platform primitives disable this optional storage without stopping chat.

`GET /api/session/skill-updates?session_id=...` uses the signed request identity,
requires current conversation turn membership, and uses the narrow `chat:use`
permission for this metadata-only read. Skill file access and mutations retain
their existing permissions. It accepts no actor or profile filters, sends no-store
responses, and reports missing or unreadable storage truthfully. Administrators do
not acquire another person's activity by selecting their conversation.
Each read also applies the current skill visibility policy to the logical ID and
short name. A known denied operation is removed together with its count; a fully
denied named event disappears. Older unknown-name counts remain generic. Policy
errors return 503 without any stored names; the client shows its retry state.
No skill file is read to produce the notice.
For native creation the separate category and returned relative path establish
the logical identifier. A bare-name patch can resolve to any category, so a
review-local observer records the result of the native lookup that already
happened. It does not repeat lookup or read skill content. Captures are bounded,
thread-safe and reset when the review exits. Multiple candidates, external roots
or unavailable resolution suppress the name and retain only generic confirmed
counts; the adapter never guesses a category from a short name.
The previous `/api/skills/learning-activity` route remains an exact alias. The
frontend uses the session route to mitigate an observed client-side block of the
old URL. No specific browser filter rule has been established, and no browser
protection is disabled. Server 401/404/503 behavior is not hidden.

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
uses actual engine `ab106d5786e9817560016f0b289d1fb11857bb76`, real native skill
create/view/patch/batch operations in temporary directories, a failed patch, and an
unchanged patch. Only outbound skill-sync transport is stubbed. A separate real
native daemon-thread test overlaps A and B and verifies private attribution to A.
No provider call or production skill write is required or claimed.

The durable browser script is `tests/frontend/skill-learning-chat.cjs`. Its local
fixture `tests/skill_notice_names_fixture.py` uses the shipped renderer, actual
private store and HTTP handler, with explicitly synthetic identities, conversation
membership and confirmed result inputs. It performs no provider or real skill
write. Run it with the intended engine on `PYTHONPATH` and open its printed
loopback URL. New creates and patches appear through normal ten-second polling;
failed changes create no new notice. It checks chronological placement, rebuild
deduplication, retry, late-response rejection, reload, and desktop/mobile layouts.
The older standalone HTML fixture remains useful for deterministic delayed
response and loading-placeholder checks. The CI browser script exercises the
HTTP fixture; the Node/pytest behavior harness adds deterministic polling and
malformed-name checks without browser automation.
