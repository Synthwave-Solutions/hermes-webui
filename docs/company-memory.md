# Company memory

Admins open Personal memory → Company memory to search, edit and delete shared
company knowledge. All WebUI agents retrieve relevant company facts alongside
their existing person-scoped memory. Membership does not grant access to the
management API or company database through file APIs; admin checks fail closed.
Personal memories and project/shared-chat banks keep their existing isolation.

A separate user-systemd timer processes newly added or changed personal-memory
records from all people. It rotates between people, batches at most 20 records /
40,000 characters per model request, and processes ten batches per run. Two
minutes after a run ends the next pass starts. Existing historical records are
processed gradually through the same queue. No model calls run on the chat
response path. The company panel displays the remaining source count, last
successful consolidation and retry status. Queued counts are a snapshot of the
last scan; active conversations can add further sources.

The worker uses the configured custom provider and default model unless
COMPANY_MEMORY_PROVIDER / COMPANY_MEMORY_MODEL explicitly override them. Model
calls have no tools, a 180-second timeout and bounded output. Invalid, interrupted
or failed responses do not checkpoint their sources and retry next pass. Each
fact requires an exact supporting quote from the supplied input, an allowed
business category, company scope and confidence of at least 0.9. The extraction
prompt excludes private, client-specific, project-specific and sensitive data,
as well as isolated questions, proposed tasks and speculation. Repeated consistent
business requests can support a qualified observed practice only when at least
two different people or conversations supply supporting evidence. Such records
start with “Waargenomen werkwijze:” and are not represented as official policy. Additional code rejects
sensitive patterns and content altered by credential redaction. As with any
model-based summary, admins should correct any factual errors they notice.

Active facts live in a dedicated Mnemosyne BEAM bank, with FTS recall. Automatic
edits consolidate under stable topic keys. Source fingerprints support incremental
processing and provenance; changed/deleted sources retract unsupported automatic
facts on the next scan. Raw private messages are not duplicated in the company
management API. Admin edits pin a topic against automatic replacement. Deletion
retains a topic tombstone, and a renamed claim supported by the same blocked
source is also suppressed. The existing topic catalog, including tombstones, is
provided to subsequent extraction passes to discourage semantic duplicates.
Admin edits remain authoritative after their original source is removed.

The company database and lock files live under STATE_DIR/company_memory with
0700 directory / 0600 database permissions. Short file-locked transactions
serialize worker updates and admin changes. An audit records actor, operation,
topic and timestamp. Separate worker locking prevents concurrent consolidation
passes. A source-version recheck before publication and periodic pruning handle
edits made during model requests. Changes are eventually reflected at the next
successful pass, not retroactively removed from past agent answers.

Install the templates in deploy/company-memory.service and .timer as user units.
They assume the managed checkout and Hermes runtime below the user's home; adapt
those paths for another deployment. Enable company-memory.timer. Stop the timer
and service to pause consolidation; existing company recall remains available.
The timer does not restart the WebUI. Deploying the initial route/provider code
requires an ordinary WebUI restart after checking that no chats are active.

Validation: scripts/test.sh tests/test_company_memory.py exercises real SQLite,
real governance resolution, member denial, incremental processing, evidence
validation, editing conflicts, pinned edits, deletion suppression and source
retraction. tests/personal_memories_browser.cjs covers both memory views at
1440, 768 and 390 pixels, editing, error handling, XSS and stale responses.
