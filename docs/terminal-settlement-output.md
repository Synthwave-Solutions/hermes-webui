# Completed tool output at turn settlement

SynthPulse's anchor registry keeps a tool's start and completion as separate
events. Final settlement previously kept the first same-ID row and discarded
the completion. A terminal card therefore lost its output at the end of a
successful turn, even though the backend journal and hydrated transcript had
the output. Reloading could restore the card. Refreshing the deferred DOM
snapshot alone did not repair this earlier loss.

The changed state layer is the browser's settled `activity_scene_v1`. Same-ID
completion events now replace the earlier tool payload while retaining its
chronological position, row identity and display mode. A true live completion
outranks an appended derived transcript duplicate; without one, persisted
completion metadata can supply the result. An ephemeral per-settlement rank
map separates payload provenance from the retained live row identity. Later
live completions replace output fields together, including explicitly empty
or sanitized output. A later start cannot regress the completion. Anonymous
rows never gain another tool's output through this merge, and the existing
subagent status merger remains in place.

The provider-free regression executes the real live callback upsert and anchor
adapter (including wire `preview` to `snippet`), anchor registry, per-message
tool-row builders, final settlement and `buildToolCard`. It covers actual
start/complete/done projection, persisted duplicates, failed and cancelled
completion, empty output, repeated events, two tools, chronological identity,
missing invocation metadata, escaped content and the existing long-output
control. Only cosmetic labels and minimal DOM element allocation are stubbed;
the generated result HTML comes from the native renderer. It is not a real
browser or production acceptance test.

The initial eight regression cases failed on the previous source. The prior
deferred-snapshot repair remains needed at the DOM reconciliation boundary,
but its production acceptance failed. A fresh real terminal run must show
stdout inside the expanded Output card **before any reload** before claiming
this follow-up resolves the observed production bug. No backend data,
governance, output limits, provider calls or tool permissions change here.

Contract routing: this is the existing live-to-final assistant reply and
stable assistant-turn-anchor presentation contract, not a new execution or
persistence protocol.
