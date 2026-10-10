# Scheduled tasks and organization operations

Scheduled tasks now expose independent in-app and delivery notification levels.
People can choose Every run, Only failures, or Never for in-app notifications;
chat delivery can be limited to failed runs. A task's shared viewers may lower
only their own in-app notification level. That preference cannot change delivery,
other viewers, or the task owner's notification setting. Administrators alone
can set or lift the API-only `off` levels. Task output remains available even
when notifications are muted. New Monitoring tasks default to failures only.

Task edits, run/pause/resume/delete, delivery targets, skills and model choices
are authorized before mutation. Sharing grants read access, not the right to
edit or run somebody else's task. Task identity is assigned at creation and
remains immutable; legacy ownerless agent tasks need the engine's audited
administrator migration. Manual runs bind the task owner's governance and use
the same notification delivery policy as scheduled runs. The selected execution
profile controls the run configuration; results remain in the owning cron store.
This requires the matching engine notification policy and ownership changes.

Organization views are read-only at `/api/org/overview`, `/departments`,
`/people`, `/approvals` and `/usage`. Exact policy designations define the
organization, billing and department scopes. Broad wildcard grants do not
confer these scopes or reserved control-plane permissions. HQ installations
have no client organization views. No organization mutation UI is activated.

The operational reporter is disabled unless `SP_OPERATIONAL_TELEMETRY=1`,
`SP_CONTROL_URL` and `SP_INGEST_KEY_FILE` are configured. Reports are sanitized
before entering a bounded queue or private retry spool. Production deployment
keeps `SP_DIAGNOSTIC_PAYLOADS` unset: no diagnostic message/context payloads and
no browser error collection. Browser collection requires that separate flag;
the authenticated endpoint limits reports to 16 KB and 30 per user per minute.
Reporter transport uses the signed control API protocol; a UDS-only deployment
needs a compatible local HTTP transport before activation. This release does
not implicitly enable it or create keys.

Validation covers owner/shared-viewer isolation, notification policy parity,
manual and scheduled delivery suppression, read-only organization scoping,
reserved permissions, control client signing, reporter redaction and recovery.
Real browser scenarios cover notification settings on desktop/mobile, per-viewer
mutes, denied shared-user edits, and complete Tasks lifecycle with a loopback
model and local-only delivery. Optional help offers dismiss during form input.
