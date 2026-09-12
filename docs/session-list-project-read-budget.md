# Project access while loading the SynthPulse sidebar

Related ticket: **Verbeter koude start: sessielijst, bots en providerdetectie**
(`3d3937f1-8d88-814b-8267-f9c2ca64cb59`). This is a bounded API repair;
the broader cold-start and frontend acceptance remains open.

## Problem and invariant

The session-list cache builder checked project membership separately for every
row during ownership and profile filtering. The final response did the same
work again on cache hits. Each check read and parsed the entire project store,
even for personal chats that merely had an organizational project ID.

The final check also ran after public row serialization. That allowlist does
not include the authoritative `project_shared` field, so a cached shared row
was treated as a legacy personal chat and could survive a membership revocation.

The changed state layer is the transient sidebar projection, not transcript,
ownership, membership, or saved project data. A shared row requires current
project membership; organizing a personal chat must not share its history.

## Implementation

`session_access_checker` lazily reads one project snapshot for a synchronous
projection. The builder reuses it across ownership and profile passes. After
cache lookup, the route creates a separate checker and filters internal rows
before producing the unchanged public response shape. Both visible rows and
sidebar reference rows use that fresh check.

The closure is never saved in a global, response, or cache. It holds no project
lock after the existing store read completes. Missing/deleted projects deny
shared rows. Unreadable project JSON follows the existing empty-store behavior
and cannot authorize shared rows. Duplicate project IDs retain the existing
first-record decision. Current group/personal visibility and admin policy
predicates are unchanged. No authorization TTL or background worker is added.

Existing aggregate counters retain their sidebar cache/invalidation lifecycle.
The final response guard protects row access independently, including an
out-of-band membership edit without an invalidation. This does not claim that
all cached aggregate counters become transactionally current at that boundary.

## Reproduction and verification

`tests/test_session_list_project_read_budget.py` uses actual dispatcher,
serialization, project-store reads and membership functions with synthetic
session metadata. It also exercises the real session-list cache, including
revocation and regrant without cache invalidation. Tests do not call providers
or read user transcripts.

Observed native project-store read counts:

| Isolated scenario | Before | After |
| --- | ---: | ---: |
| Cached 40 shared rows plus 4 reference rows | 44 | 1 |
| Cached 40 personal project rows plus 4 references | 44 | 0 |
| Builder: 40 shared rows in another profile plus 1 foreign personal row | 81 | 1 |

The five initial regressions fail on the unchanged base and pass with this
change. Additional cases cover current revocation, missing/corrupt stores,
missing IDs, duplicate IDs, builder-to-response revocation, preservation of
cached internal metadata and concurrent identities. These are deterministic
I/O-count and authorization assertions, not a production latency benchmark.

Run via `./scripts/test.sh tests/test_session_list_project_read_budget.py -q`.
Neighbor coverage includes project collaboration/creation, sidebar cache,
cache extraction and group-chat behavior. The existing native file-tool
governance-review fixture may fail with `governance_review_unavailable` on both
the unchanged base and candidate; report that separately from this repair.

## Frontend acceptance

Using an authorized existing account, reload the sidebar and reopen it while
its list cache is warm. Confirm stable row order, group/project visibility,
archived references and navigation to an owned conversation. Compare endpoint
timing on the same dataset without sending a provider turn. In an isolated
shared-project fixture, revoke a member after warming the cache and verify the
next refresh removes the shared row and its reference; personal chats remain
private. Repeat with another actor/profile and verify no cross-account rows.
Actual production timing and rendered frontend acceptance are separate gates.
