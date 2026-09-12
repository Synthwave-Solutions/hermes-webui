# Background skill review profile context

SynthPulse uses the same Hermes turn finalizer as the CLI. A review can outlive
the foreground WebUI worker. The engine copies ContextVars to the review thread;
WebUI thread-local environment values are not copied.

Previously the WebUI worker did not bind the engine's context-local home and
patched imported skill modules with a process-wide `SKILLS_DIR`. That override
takes precedence over the current engine's dynamic resolver. A synthetic test
using the real engine review-thread launcher reproduced profile A's delayed
review resolving profile B's skill directory after B started another turn.
The test reads temporary path metadata only; it does not call a provider or read
or write user skills.

The worker now binds the resolved execution profile before reading runtime
configuration and resets that context in its outer cleanup. Background threads
retain their copied context after foreground cleanup. Modern skill modules are
restored to their import baseline so their dynamic resolver uses the bound home.
This normalization also happens before detached-worker capability checks,
preventing a stale global override from being restored over another worker.
Legacy engines and static skill modules retain their existing fallback behavior;
this change does not promise concurrent isolation for those older engines.

The actor's personal-memory context and governance context remain separate and
are preserved by the engine's existing context propagation. No tool grants,
blacklist or whitelist rules, skill-review eligibility, or approval behavior
change. Engine review tool restrictions still apply.

## Verification

`tests/test_streaming_profile_context.py` launches the real engine background
review thread with a read-only synthetic target, overlaps two profiles, and
asserts the original home, both skill resolvers, actor context, and personal
memory directory. It also checks nested scope reset on normal and exceptional
exits and invokes the actual WebUI worker to verify binding before configuration
reads and cleanup on an early failure.

The modern-worker regression in
`tests/test_issue5567_profile_home_override.py` starts with a stale global skill
override and lists distinct synthetic skills concurrently in two profiles.
Existing static-module tests continue to cover the legacy serialized fallback.

Against engine `07aad46435cf581ba2fe61edf6432ed491c17742`, the focused profile,
memory, governance, and early-denial selection passes 39 tests. Four unrelated
baseline tests are excluded: three reference missing historical streaming
helpers and one expects a role-ceiling drift that the fixture does not create.

This verifies routing and lifecycle, not a production skill write or provider
decision. The WebUI still lacks the engine's background-review completion
callback. Its foreground persistent-state snapshot can miss a review that ends
later, so reliable late-review notification remains a separate task.
