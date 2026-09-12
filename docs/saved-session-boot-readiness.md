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

This addresses the frontend catalog gate within ticket
`3d3937f1-8d88-814b-8267-f9c2ca64cb59`, “Verbeter koude start: sessielijst,
bots en providerdetectie”. Earlier workspace/sidebar/onboarding waits, server
catalog generation, and any separately observed provider change after complete
hydration remain outside this correction. Production desktop/mobile timing and
the actual signed-in account's full reload require separate acceptance.
