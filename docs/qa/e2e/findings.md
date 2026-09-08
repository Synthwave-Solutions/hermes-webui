# Frontend QA findings

The tests drive real frontend controls against disposable application state. Fixed items below have focused browser or backend regression evidence; the final execution summary is the authority for the integrated run. Existing defects stay visible as failing acceptance tests.

| Finding | Observed behavior | Disposition |
|---|---|---|
| QA-001 | Settings POST failed through a locally shadowed `save_settings` import. | Fixed; actual preference save/reload covered. |
| QA-002 | Clear conversation appeared successful, but stored context or recovery could restore old messages. | Fixed with explicit clear generation, canonical truncation and stale-context reset; new-turn/reload regression. |
| QA-003 | Terminal stream read obsolete output storage rather than the terminal subscription API. | Fixed; real shell output/restart and sequenced reconnect covered. |
| QA-004 | Successful passkey login omitted response Content-Length, leaving the browser request unfinished. | Fixed; virtual WebAuthn registration/login/removal passes. |
| QA-005 | Activity hide-all option and event-timestamp preference were rejected or silently lost. | Fixed enum/default contract; saved values and reload covered. |
| QA-006 | Auto-title refresh UI submitted a number to a string enum. | Fixed; each actual option persists. |
| QA-007 | Settings controls could accept interaction before loading bound their handlers. | Fixed with a busy/inert initialization boundary. |
| QA-008 | Passive success toasts intercepted the next click and could remain hovered indefinitely. | Fixed; passive toasts no longer capture pointer events, error actions remain usable. |
| QA-009 | Mobile Chat/Governance/Connections/My approvals navigation left a drawer over the main controls. | Fixed; normal mobile clicks and governance form roundtrip tested. |
| QA-010 | Interrupt could consume a queued replacement as a steer into the cancelled run. | Fixed; durable queue entry retries a new turn after the old worker unwinds. |
| QA-011 | Unchanged group saves dropped command deny rules and flattened command metadata. | Fixed by preserving unexposed policy data; actual fail-before/pass-after browser regression. |
| QA-012 | Committed autocomplete suggestions could overlay Save; Escape did not dismiss the menu. | Fixed shared Enter/Escape handling; normal group save clicks pass. |
| QA-013 | Duplicate scheduled job requested disabled state but was created active. | Fixed atomically at engine creation and forwarded by WebUI; copy starts paused. |
| QA-014 | The visible Share action calls `/api/share/create`, which returns404; no public-share route is wired in this candidate. | OPEN. Unskipped share creation/read/revocation acceptance test fails at the real response. Restoring public sharing requires a scoped ownership/privacy contract decision. |
| QA-015 | Kanban displays Done for a Todo task, but its completion request returns404 although the task exists. | OPEN. Separate unskipped acceptance test records the mismatch; supported Ready→Done lifecycle is tested separately. |

Security findings addressed by the RBAC implementation are documented in the separate governance package: retained denials under wildcard access, final-dispatch enforcement, one-action approval scope, stable first-event approval IDs, current-policy revalidation, delegated manual-review enforcement and concrete resource bypasses.

Global repository CI is not green. Clean-baseline comparisons reproduce existing collection and catalog/locale/gateway failures. The report distinguishes those from new regressions and from the real frontend failures above.
