# SynthPulse interaction context

The shared interaction guidance asks the model to resolve the current request's
language before writing a question or choices, retain an explicit task language,
reuse prior answers and authorization for the same action/target/scope, and use
reasonable reversible defaults. It does not turn silence into consent or suppress
mandatory approval. Technical connection setup uses the supported secure entry
route; missing credentials and policy denial are distinct states.
Masked stored values are intentional redaction, not evidence of invalid keys;
the assistant must use the supported connection check for authentication status.

The authenticated human, selected assistant/profile and connected mailbox are
separate identities. A user's authorized Google account can have a different
email from their SynthPulse login. Resolve ownership and verify the connected
account, honor a previously selected account, and clarify only if multiple
authorized accounts remain plausible. A profile owner's mailbox is never a
fallback. Prompt guidance does not grant access or replace runtime enforcement.

## Assembly and state ownership

`api.interaction_context` contains fixed guidance and formats the server-selected
actor. `api.streaming._webui_ephemeral_system_prompt` appends it after personality
and recalled context, then adds authoritative actor identity. The local worker
rebuilds this prompt on every turn, including reused agents. The legacy gateway
worker calls the same builder and places the result in its system prefill.
Authenticated/project/group turns continue through the governed local worker.

Realtime voice now passes its authenticated actor to `session_config` before the
SDP exchange. The visible session is checked before its ID is used for the task
preference. The voice model receives the human identity and spoken-language
guidance; it does not automatically receive the full text-chat transcript.
`dispatch_work` carries relevant spoken task context to the existing authorized
chat route. Tool definitions, approval controls and runtime isolation are unchanged.

When `api.interaction_preferences.prompt_for(actor_email, session_id)` is installed,
the builder reads its fixed, scoped clarification guidance each turn; voice reads
it at call creation. The preference module owns storage, validation, membership
and unavailable-storage fallback. Without it, the balanced guidance applies.
No client-supplied preference text or actor metadata is accepted as a prompt.
Changing a preference during an open voice call takes effect in the next call;
this change does not silently rewrite an already displayed clarification.

Only ephemeral model context and the voice provider's call configuration change.
Profile instructions, saved transcript, language preference, governance policy,
credentials and connection ownership are not rewritten by these helpers.

## Verification and limits

Run `./scripts/test.sh tests/test_webui_interaction_context.py
tests/test_realtime_voice.py tests/test_webui_surface_context.py
tests/test_chat_worker_identity_dispatch.py` for builder, actual worker-assignment,
voice negotiation payload and request-spoof regressions. Provider requests in the
tests are captured locally; no actual mailbox, credential or voice call is used.

`tests/fixtures/interaction-prompt-scenarios.json` defines model acceptance cases.
Replay with the assembled system prompt and exact message roles on the intended
production model, inspect the visible answer and tool arguments against each
case's criteria, and record model ID and result. Simulate tool results; do not
execute the described external actions. For voice, additionally verify live
speech and the delegated task's account context in an authorized user session.

Builder tests prove payload assembly, not model obedience, account availability,
microphone operation or OAuth success. The language correction governs generated
question/choice/approval prose; existing fixed UI labels and errors still use the
UI locale. Full clarification-renderer language acceptance and Odis's actual
Gmail session therefore remain separate checks. No persistent 'never ask again'
approval or permission suppression is introduced.
