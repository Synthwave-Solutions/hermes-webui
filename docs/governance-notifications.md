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
