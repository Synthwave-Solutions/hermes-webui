# Background title request isolation

SynthPulse can generate a title after a chat answer completes, while the next
turn uses the same cached agent. Title generation must not temporarily disable
that agent's reasoning or restore a stale setting over a newer user choice.

`generate_title_raw_via_agent` builds Chat Completions and Codex request kwargs
on a shallow, request-only agent view. The view owns its disabled reasoning
setting, empty tool list, and fresh transport cache. This also isolates the
native builder's consumption of an ephemeral output-token override and reset
of transport-local tool aliases. The original agent remains the dispatch
owner; its client, model, provider route, and request methods are unchanged.
This is builder and reasoning isolation, not general transport concurrency
isolation or a new agent/client lifecycle.

The Anthropic branch already accepts explicit request reasoning. It now uses
the engine's supported `AnthropicTransport.normalize_response` API through
`get_transport`, replacing the removed `normalize_anthropic_response` adapter
export. Its normalized content is read without changing the live agent.

Copy, provider, and normalization errors retain the existing `llm_error` title
fallback. This change adds no provider retries or serialization, changes no
title budgets, and does not claim to remove provider latency or post-answer
title time. Native Codex output-cap behavior and older engines without the
transport API are outside this change.

## Verification

`tests/test_title_agent_request_isolation.py` runs the actual WebUI title
orchestration. Explicit event gates hold a synthetic provider request while
the test reads foreground reasoning, tool metadata, and output-token state,
or changes the foreground reasoning selection. Success and provider errors
must preserve the newer selection. The gate is always released in `finally`;
the tests do not infer ordering from sleeps or negative timing windows.

The native wire matrix runs real engine kwargs builders, transports, and
provider profiles for custom gateways, OpenAI, Nous, OpenRouter, and native
Codex. Anthropic tests use the real adapter and normalizer with an SDK-shaped message
fixture. External provider calls and agent construction are synthetic; these
tests do not prove live provider acceptance, microphone behavior, or frontend
follow-up latency.

Run with the configured engine checkout and supported test interpreter:

```sh
HERMES_WEBUI_AGENT_DIR=/path/to/hermes-agent \
PYTHONPATH=/path/to/hermes-agent \
./scripts/test.sh tests/test_title_agent_request_isolation.py \
  tests/test_title_aux_routing.py tests/test_title_gen_reasoning_extra_gate.py \
  tests/test_2235_initial_aux_title.py tests/test_1058_adaptive_title_refresh.py \
  tests/test_3230_preserve_manual_session_title.py \
  tests/test_manual_title_regenerate_timeout.py -q
```

The original shared-state implementation fails the seven deterministic
Chat/Codex isolation cases. The removed Anthropic import fails both real
adapter route cases before provider dispatch. The corrected implementation
must pass those cases and the neighboring routing/lifecycle tests.
