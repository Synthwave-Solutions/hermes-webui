# Explicit custom provider routing

SynthPulse preserves a conversation's explicitly selected named custom gateway when its model identifier contains a slash. For example, selecting `custom:omniroute` with `codex/gpt-6-astra` must resolve through that configured gateway even when the global default is native `openai-codex`.

Previously, `model_with_provider_context()` retained named providers in the `providers` mapping but omitted those in `custom_providers`. Its generic slash-ID passthrough could therefore drop the explicit gateway hint. The native default then received the gateway's namespaced model. A provider rejection could activate an existing configured fallback and produce an answer from another model.

The repair uses the existing canonical named-provider slug helper before the generic slash passthrough. Unconfigured provider names receive no new authority. Native selection, already qualified identifiers, portal routing, and the existing active-default-provider behavior remain unchanged. No fallback configuration, credentials, model tiering, or persisted session fields change.

## Verification

`tests/test_explicit_custom_provider_context.py` exercises the real context wrapper and provider/connection resolvers with a list-based custom model catalog, two separate gateways, native/default selections, and malformed catalogs. Four cases failed before the repair; all ten pass afterward.

The relevant provider regression selection passes 111 cases. Six unrelated existing literal-source/locale assertions in `test_provider_mismatch.py` also fail on untouched base `590a85a9a46aa7f9e1e6da0d5693a96e999b98cb` and are excluded from that passing selection. Production acceptance still requires a real frontend turn that explicitly selects the gateway and verifies the actual model route. Local resolver tests do not establish live provider availability or latency.
