# Saved-session boot readiness

When an existing conversation already has an explicit model and provider, its
composer can become ready after the conversation loads. It no longer waits for
the complete model catalog. Boot first inserts or selects that exact route using
the existing model picker helpers and verifies both fields. An unknown model,
missing provider, or unmatched result retains the existing catalog wait.

This changes only transient browser readiness and picker metadata. It does not
authorize a provider, alter the stored session, switch profiles, change reasoning
or tools, or cache access decisions. The backend still applies current policy.
The existing catalog promise coalesces the initial and restore requests; later
catalog reconciliation reads the current session rather than a captured old one.

## User scenarios

- Reopen a saved conversation while provider discovery is slow: the transcript,
  selected route, and composer controls become usable before the catalog returns.
- Two providers offer the same model name: the saved provider remains selected
  and the outgoing chat payload retains that provider.
- A catalog fails or omits the saved custom model: the exact saved route remains
  usable; normal catalog refresh behavior is unchanged.
- Pick another model or switch conversations while the catalog loads: the late
  result preserves the current conversation and explicit choice.
- Open a conversation whose model or provider is unresolved: wait for existing
  catalog reconciliation rather than exposing a guessed route as ready.

## Verification and limits

`tests/boot_saved_model_driver.cjs` executes the real saved-session boot branch,
the model reconciliation section of `syncTopbar`, catalog population/deduplication,
native picker helpers, model-change handler, and outgoing chat-model helpers.
Only metadata delivery, unrelated DOM, and network endpoints are fixtures.
Before the change, a pending catalog leaves readiness false, the model label
empty, and bot controls disabled despite loaded conversation metadata. After the
change, the explicit saved route is ready while that same single request is
still pending. This is deterministic dependency evidence, not a measured live
wall-clock improvement or a full browser boot test.

The fixture covers complete, missing-custom, and failed catalogs; duplicate model
names across providers; qualified model IDs; conversation changes; explicit
model changes; and unresolved metadata. It checks no implicit session update and
the actual outgoing model/provider pair. No provider request is made.

## Workspace metadata during restore

After onboarding is complete, restoring an existing conversation no longer waits
for the independent workspace picker request. The normal session loader still
authorizes and restores that conversation. Workspace metadata can arrive later;
a failed picker request does not clear the restored transcript or a typed draft.
New chats, PWA new-chat actions, prefilled fresh composers, restored personal
scratch sessions, and sidebar-only restores retain the workspace wait. First-run
onboarding retains both its setup and workspace gates. Every added wait checks
whether a newer chat activation superseded boot before continuing.

Workspace picker rows, the viewer's admin indicator, and terminal backend
readiness are transient browser state. Each workspace request is scoped to the
current profile generation and its own request generation. An older response is
discarded, including an A-to-B-to-A profile sequence. A successful manual or
automatic profile switch clears the old picker/admin/backend snapshot and sets
both workspace defaults from the new profile, including an empty default. The
terminal stays unavailable until the current backend metadata arrives. The loader
accepts only a workspace array and explicit backend/admin booleans; malformed
data remains unknown and a valid retry can recover. The terminal's slash command
uses the same guarded loader, and a delayed terminal module cannot start
after its profile, session, workspace, or backend changes. Automatic switches
claim the shared profile generation before their POST and recheck it after
sidebar rendering so an older switch cannot retry a session over newer intent.
An automatic switch that supersedes a manual switch owns the profile controls'
loading state; success, request failure, and setup failure release those controls
without clearing a newer switch's indicators.

`tests/boot_workspace_ready_driver.cjs` executes the real boot tail, workspace
loader/reset, manual and automatic profile switches, draft-restoration helper,
terminal command, and terminal startup with controlled metadata promises. Its
session response and unrelated rendering are fixtures: it does not prove real
server authentication or a full rendered browser journey. The tests preserve
typing and intentional draft clears while session restoration is pending, and
exercise denied/failed responses, newer chat activation, repeated requests,
profile round trips, and delayed terminal loading. Existing source assertions
for scratch restore, profile defaults, and terminal preflight follow these same
shared helpers; they supplement the behavioral cases.

This addresses the frontend catalog and workspace restore gates within ticket
`3d3937f1-8d88-814b-8267-f9c2ca64cb59`, “Verbeter koude start: sessielijst,
bots en providerdetectie”. Sidebar loading, new-chat/onboarding readiness, server
catalog generation, and any separately observed provider change after complete
hydration remain outside this correction. The tests measure dependency ordering,
not a live timing improvement. Production desktop/mobile timing and the actual
signed-in account's full reload require separate acceptance.
