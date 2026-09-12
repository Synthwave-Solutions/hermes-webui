# Provider failure diagnostics and preparation timing

SynthPulse keeps terminal Hermes lifecycle failures through WebUI settlement.
Previously, an engine that emitted its error only through `status_callback`
could reach an empty result with neither `error` nor `_last_error`. The user
then saw a generic no-response message that incorrectly suggested capacity.

The bridge accepts the engine's specific terminal lifecycle prefixes, retains
a redacted and bounded cause, and applies the existing error classifier. A
recoverable fallback notice remains a warning. A captured-only authentication
failure does not trigger the WebUI credential self-heal replay: prior tool work
must not be repeated merely because a previously discarded error is visible.
Unknown failures make no capacity claim and do not invent provider details.

Run journals also record six content-free preparation milestones: identity,
MCP readiness, provider configuration, toolsets, agent readiness, and the
conversation call. Each contains only a phase name and elapsed milliseconds.
They distinguish application setup from the provider request; the conversation
milestone is not a provider-dispatch timestamp.

Validation includes the real WebUI worker with a synthetic engine: a terminal
401 produces one persisted error, one engine run and no credential self-heal;
a recovered fallback completes normally. The lifecycle bridge also has focused
classification, redaction, bounded-message and recoverable-notice regressions.
These tests do not establish the cause of a particular historical production
failure. Provider service availability and real chat latency need live checks.
