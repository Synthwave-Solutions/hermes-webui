# Governance notification delivery

Access-request ingest persists a new pending approval before attempting the
configured administrator notification. Delivery runs outside the approval
registry lock, so a slow external destination does not prevent other requests
from reading or deciding approvals. Only the ingest that creates the row sends
the new-request notification; subsequent ingest of a pending or decided row
does not repeat it.

Delivery remains best effort. The authenticated approvals screen is the source
of truth. Retry/outbox delivery and opt-in continuation after a decision are
separate workflow changes; neither is implied by an approval notification.


## Complete after approval

Settings > Access requests offers explicit consent for the current owned
conversation. Consent lasts one hour and applies to subsequent runs. A denied
operation can then wait up to five minutes before it returns the normal denial.
The worker remains cancellable throughout the wait; administrator locks are not
held. Approval wakes the original in-memory invocation only. The engine reloads
current policy and checks both the tool and its exact arguments before executing.

The durable record binds the authenticated requester, conversation, original run,
tool call, original-input hash, requested capability, exact value and expiry.
Tool arguments and unredacted prompts are not persisted. Opt-in itself grants no
permissions. A decision must match the immutable operation record; cancellation,
changed input/workspace, an expired wait or a lost process handle fails closed.
No prompt or tool invocation is replayed after restart. Group conversations and
unbound legacy operations are unsupported and require input.

SQLite records the waiting, queued, resumed, completed, failed, cancelled,
expired and input-needed transitions. Completed means the original tool
invocation returned successfully, not independent verification of an external
business outcome. Run teardown without an observed tool return becomes
input-needed. Cancelling consent cancels outstanding waits; it cannot undo an
operation already released for execution. Normal chat Stop still cancels the run.
