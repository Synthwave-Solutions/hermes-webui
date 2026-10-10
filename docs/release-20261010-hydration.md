# Conversation and Memory startup readiness

Sending while a conversation is still restoring now keeps the draft and asks
the user to wait. It cannot create a separate default-mode chat in place of the
selected conversation. Both initial boot and subsequent session switches are
covered. After loading finishes, the draft sends to the original conversation
with its saved mode and bot roster.

If the active Memory panel's request becomes stale because chat restoration
changes its context, it starts a read for the latest context. Stale data remains
excluded, and a newer panel request retains ownership of rendering.

Delayed-response browser checks reproduce both original races and verify the
correct target, preserved draft/mode/bot roster and recovered Memory sections.
