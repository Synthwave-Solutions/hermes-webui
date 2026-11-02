# Personal memory consolidation

Each authenticated person has independent Mnemosyne banks per bot. Each bank
stores original user statements and separate evidence-backed consolidated facts.
Private chats with the same bot share its private bank; shared conversations have
a separate bank for that person, bot and conversation. No bot-owned legacy memory is promoted across people.

The bounded `personal-memory` worker sends at most 60 statements / 48,000 characters
from ONE bank to the configured custom gateway, with no tools. Its prompt extracts
explicit lasting preferences, context and workflows; one-off tasks, quoted text,
credentials and inferred sensitive traits are excluded. Structured proposals must
have exact source quotations and confidence >= 0.9. Source fingerprints are checked
again under the bank lock after the network call. Invalid or interrupted responses
remain pending. Least-recently-attempted banks run first to avoid starving small accounts.

Consolidated facts are visible/editable/deletable in the existing personal memory
panel. Manual edits pin facts; deletion retains a tombstone and supporting-source
block so automatic rewordings cannot resurrect them. Edited/deleted original
sources invalidate automatic facts at recall time and are cleaned up by the worker.
A newer explicit correction can replace a topic; old batches cannot overwrite newer
facts. The original statements are retained for provenance and user management.

Recall prioritizes consolidated preferences/profile facts plus relevant consolidated
workflow/project facts. As-yet unprocessed original statements remain searchable.
Processed originals are not re-injected alongside their corrected facts. Company
consolidation reads only original statements, never these derived personal facts.
Personal API responses include per-bank pending, last_success and last_error state.

Install `deploy/personal-memory.service` and `.timer`. Both personal and company
workers use `scripts/with_agent_runtime.py`, resolving the PM-selected dependency
environment instead of a frozen release venv. Declare `mnemosyne-memory` in the
existing plugin's Python dependency manifest so PM retains it across updates.
`memory.consolidation.provider` and `.model` configure their shared extraction route.
All requests stay on that custom gateway; there is no direct-provider fallback.

Verification: `scripts/test.sh tests/test_personal_consolidation.py
 tests/test_company_memory.py tests/test_personal_memory_backfill.py` with
`HERMES_WEBUI_PYTHON` pointing to the selected Hermes environment. The tests use
isolated state, real SQLite/BEAM and the agent memory provider prefetch path.

For a historical backlog, `scripts/consolidate_personal_memory.py --drain
--workers 3 --max-batches 50` keeps processing until no pending sources remain.
Workers process different banks concurrently, never two batches from one bank.
A failed bank retains its sources and does not block other banks; draining exits
with an error if an entire round cannot progress. The normal timer remains the
ongoing incremental path. Duplicate evidence quotes are collapsed by source ID;
derived memories never reuse an original statement's ID through BEAM deduplication.

`deploy/hermes-gateway-runtime.conf` can also be installed as a gateway service
drop-in. It pins the checkout path explicitly because multiplex profiles may
have a different HOME. Use the gateway's graceful SIGUSR1 restart to drain turns.

Backfills can opt into `--batch-chars 96000 --batch-size 120` (the normal
service retains 48,000 characters / 60 statements). An incomplete or malformed
model response keeps the checkpoint unchanged and halves that bank's next
character budget, down to 24,000, rather than repeatedly submitting an oversized
batch. No batch ever combines identities or changes the source ordering.

Historical skill-loader messages and encoded image payloads are reference material,
not personal statements. The shared `memory_statements` selector excludes skill
messages (including continuation chunks) and strips long binary encodings while
retaining surrounding human text. Imported reference provenance is tagged so
removing the first chunk cannot resurrect its continuations. An explicit owner
edit can turn an individual retained row into a statement. Source contents and
import receipts are preserved; personal and company facts lose invalid reference
evidence through their existing retraction paths. The importer uses the same
filter and keeps receipt hashes based on the original chunk, preserving edits
and deletions across re-imports.

The Memory dashboard's existing consolidation views also read current personal
facts from the selected bank. Its counter, Activity / Consolidations, Today,
session detail and search include these results with their evidence count and
`result_kind=current_personal_fact`. They are current results, not a historical
run log. Deleted or missing facts disappear immediately. The adapter stays in
the read-only reader process and retains the registry and owner checks; it does
not write synthetic log entries or combine private conversation banks. Company
facts remain in the separate Company knowledge section for authorized admins.

Episodic processing runs independently through `personal-episodes.timer` and
`scripts/consolidate_personal_episodes.py`. It groups eligible original statements
by owner bank, conversation and recording day, bounded to 40 messages / 24k
characters per segment. Several independent segments can share an extraction
request, but each result has its own key and checked source quotes. It uses the
configured consolidation model through the same gateway as fact extraction.

Summaries are stored through the native episodic writer (including its FTS
indexes), with all original source IDs and fingerprints retained. They describe
the user's reported context, requests, decisions and outcomes, not independently
verified execution. They never turn private conversation details into company
knowledge. The original working memories are retained. Fact consolidation still
extracts enduring knowledge separately; episodes do not become fact evidence.

Personal recall combines durable facts, relevant episodes and original statements
that have not been represented by a fact. Episode evidence is rechecked during
recall. Source edits/deletions immediately retract automatic episodes. The owner
can edit/pin or delete episodes in the existing personal memory list; a tombstone
prevents recreation of that segment. The dashboard reads the native episodic table.
The per-bank `episode_state` records pending work, attempts, successes and errors.
Failed/truncated model output remains pending for retry with smaller batches.
Segments with failed attempts move behind untouched segments, so one bad response
does not starve the rest of that person's history. Transient provider errors use
the configured extraction route first, then `synthpulse-luna` through the same
OmniRoute connection. Authentication/permission errors are not silently retried
on a different model. The optional `personal-episodes-backfill.service` drains
history independently of the normal periodic worker, sharing its exclusive lock.

`personal-lifecycle.timer` maintains the owner-scoped graph and episodic aging
every five minutes. New episodes enter tier 1 (hot, weight 1). At 30 days after
episode creation they enter tier 2 (warm, weight 0.5); at 180 days tier 3 (cold,
weight 0.25). These match the dashboard's default lifecycle thresholds. Age uses
the stored episode creation time, not an inferred date of the described event.
The earlier unconditional cold insertion is migrated once to hot unless a real
degradation timestamp already exists. Manual owner edits pin the episode.

Long episodes are compressed through the configured model/gateway before a tier
transition; already concise ones retain their content. The original summary is
retained in `personal_lifecycle` for provenance, and original working messages are
never removed by aging. The native FTS triggers keep text search current; optional
stale dense indexes are invalidated. Tier weights are applied to episode and graph
recall, not merely displayed. A failed compression retains the previous content
and tier, remains pending, and does not prevent graph processing.

The knowledge graph uses the native `triples` table consumed by the dashboard.
Prompt-based extraction reads only currently valid consolidated facts and episodes
inside that owner's bank. Every relation has its parent ID, content fingerprint
and literal supporting quote in `personal_graph_edges`. Graph checkpoints include
empty extraction results; failed requests retain pending sources and rotate behind
untouched ones. Source edits, deletions and automatic retractions prune obsolete
relations; recall independently revalidates parents. No private graph is promoted
to company knowledge. The graph and lifecycle worker exposes counts and retry
status through the personal memory API's per-bank lifecycle state.

For initial graph indexing, `personal-graph-backfill.service` runs the lifecycle
worker with `--drain --max-banks 64`. It waits for the existing lifecycle lock,
then processes repeated fair passes without the normal timer interval. Normal
timer invocations skip while this exclusive backfill owns the lock. Completed
empty relation extractions count as processed too. A pass with no progress exits
with an error while retaining checkpoints and pending work for the periodic retry.

`personal-graph-backfill.timer` starts `personal-memory-nightly.service` every night at 03:00
Europe/Amsterdam (including daylight-saving changes). It discovers all owner
directories and conversation banks under the configured personal-context root;
there is no selected-user filter, and new users with saved memory are included
automatically. The service unit prevents overlapping nightly runs, while the
lifecycle lock also coordinates with the short daytime worker. A missed calendar
run is caught up when the timer becomes available. The nightly service drains
personal facts, episodes, company facts, then the graph and lifecycle in that
order, across all owner banks. Each phase waits for an already-running worker's
lock rather than incorrectly treating a skipped pass as complete. Phase failure
is reported but does not prevent independent later phases from running. The
existing personal-facts, episode and company-memory timers continue their daytime
updates. Its service result succeeds only when all four phases succeed.

Backlog passes extract independent episode segments and independent graph banks
with at most eight concurrent episode requests and four graph requests. Bank writes remain locked and
source fingerprints are rechecked after extraction. Short supplemental episode
quotes are accepted only alongside substantive literal evidence; unknown or
fabricated quotes remain invalid. If a model splits a segment into multiple
summaries, each must pass validation and their combined content must fit the
1800-character episode limit before one native episode is written.
Valid segments and graph parents commit independently; an invalid sibling remains
pending without discarding the successful items or hiding their progress.

## Bot isolation (contract change)

Previously, all private chats of one person used `private.db`, regardless of bot.
New turns use `bot-<profile>--private.db`, or
`bot-<profile>--<conversation hash>.db` for shared conversations, under the same
authenticated owner directory. The selected execution bot is captured before
background sync, including group recipients and provider-recovery paths; it also
participates in the cached agent identity. No other bot bank is used as a recall
fallback. Explicit personal notes and company knowledge keep their existing scopes.

The Memory explorer lists the current banks by bot, still owner-only even for
other administrators. Saved-memory cards show the bot too. All consolidation and
lifecycle workers discover these active banks, including the full 03:00 nightly run.

`scripts/split_bot_memory.py` previews the migration; `--apply` is an offline
operation with WebUI, its watchdog and memory workers stopped. Original databases
are retained as rollback archives and marked complete only after all bot banks
exist. Statements are assigned using recorded bot metadata. Derived facts,
episodes and graph relations are retained only with same-bot source provenance;
mixed automatic facts are requeued for extraction within each bot. Owner deletion
and correction blocks, import receipts, IDs, timestamps, lifecycle tiers and
company-source references survive the split. Old archived banks are excluded from
normal reads, mutations and scheduling. Retrying a completed migration does not
overwrite subsequent owner edits. Unknown legacy graph assertions are not copied
without source provenance. Historical imports use a uniquely recorded responding
bot when available and retain old deletion receipts.

Regression coverage: `test_bot_memory_split.py`, `test_personal_mnemosyne.py`,
`test_memdash_personal_banks.py`, and the existing consolidation/lifecycle tests.
