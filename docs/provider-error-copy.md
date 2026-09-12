# Provider errors in chat

Known service capacity, rate-limit, sign-in and unavailable-model failures show
plain language in the main chat text. The same formatter supplies the live
`apperror` event and the saved error turn, so reopening the conversation retains
the explanation. Existing user turns and partial assistant output stay in place.

For example, Lyceum's `HTTP 402: insufficient credits` and Cortecs's
`HTTP 401 AuthenticationError: Insufficient Balance` both represent exhausted
capacity. The latter must not trigger credential recovery merely because its
status is 401. A 401 without that explicit balance/credit cause remains an
authentication failure. Technical status text remains in the existing redacted
`details` / `provider_details` fields, with the existing 1,200-character limit.
No permissions or visibility rules for those fields change.

The original ticket's `HTTP 503 Service Unavailable` example gets neutral
temporary-unavailability guidance (`service_unavailable`). A 503 alone does not
identify the cause or create a capacity alert. An explicit `overloaded_error`
or a server/service/upstream reported as overloaded uses the existing
`overloaded` capacity kind and its incident flow. An arbitrary 500, a number 503
in an unrelated message, and unknown network/validation failures are not
reclassified as capacity failures.
Typed permission/governance exceptions retain their access-refusal copy and do
not create a capacity incident, even when their diagnostic text mentions an
unavailable or overloaded service.
The frontend's live error heading uses the same **Service busy** or
**Service unavailable** label as the saved transcript.

An unrecoverable sign-in failure points people who manage the connection to
**Settings > Providers**, otherwise to an administrator. The exception path uses
the same guidance as a returned error, without terminal commands or restart
instructions. Credential recovery itself is unchanged. Capacity messages claim
an administrator was notified only when the existing incident recorder confirms
that outcome.

Unknown failures, governance refusals, cancellation, tool limits and missing
responses keep their existing meaning. The formatter does not infer a capacity
cause for a network or validation error. Fully redacted text is never replaced
with the original unredacted input. No model, provider, route, reasoning,
configuration, account or access policy is changed by this copy fix.

## Verification

Use the repository runner:

```sh
./scripts/test.sh -q tests/test_provider_error_copy.py tests/test_issue5121_provider_auth_terminal_error.py tests/test_issue1765_codex_quota.py tests/test_provider_terminal_status_bridge.py tests/test_capacity_alerts.py tests/test_issue3929_error_preserves_partial.py tests/test_streaming_early_access_denial.py
```

The stream regressions use a synthetic agent, an isolated session store and a
stubbed incident recorder. They exercise returned and raised provider errors,
inspect live SSE, reload saved history, and verify partial-output retention,
stable error codes, redacted details and absence of a false notification claim.
They do not call a real provider or change credentials.

`test_issue5224_terminal_error_transcript_preserve.py` also executes the actual
frontend `apperror` handler and session-restore helper in the existing Node
fixture. The two new provider cases verify matching headings, body and details
before and after loading the saved backend payload. Rendering hooks are stubbed
there; this is event-handler coverage, not a browser layout test.

Browser acceptance remains a separate check: trigger each synthetic provider
failure in an isolated frontend fixture, verify main text and collapsed details,
reopen the chat, and confirm retry retains the conversation. Check desktop and
narrow viewports. This slice retains the backend's existing English copy;
locale coverage and a live authenticated browser run are not established by the
Python regressions.
